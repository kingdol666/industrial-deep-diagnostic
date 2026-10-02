"""spc.py — Nelson rules R1/R2/R3/R5/R6 on individuals charts (vectorized).

Convention (frozen at M0, see references/method_notes.md):
  sigma_within = mean(|x_i - x_{i-1}|) / 1.128   (MRbar / d2, d2 = 1.128)
  z = (x - center) / sigma_within                (center + sigma from baseline)

Rules evaluated per (group, parameter) over the steady rows of the window:
  R1  1 point beyond 3 sigma                     -> severity high
  R2  9 consecutive points on one side of center -> severity warn
  R3  6 consecutive points steadily inc/dec      -> severity warn
  R5  2 of 3 consecutive points beyond 2 sigma
      on the same side                           -> severity high
  R6  4 of 5 consecutive points beyond 1 sigma
      on the same side                           -> severity high

Each rule returns trigger EPISODES (adjacent/overlapping violations merged),
so a sustained excursion yields one episode instead of hundreds of alerts.
The anti-storm layer (suppress.merge_by_key) collapses episodes per
suppression_key afterwards.
"""

import numpy as np

from sentinelcore._constants import D2, RULE, SEV

DEFAULTS = {
    "run_length_r2": 9,
    "run_length_r3": 6,
    "r5_count": 2,
    "r5_of": 3,
    "r6_count": 4,
    "r6_of": 5,
    "min_points": 5,
    # Materiality floors (sigma). 0.0 = textbook Nelson (frozen default for
    # M0). Raising them suppresses sub-half-sigma noise runs on tightly
    # controlled loops at the cost of later onset detection — see
    # method_notes.md §3 for the ARL trade-off.
    "r2_materiality_z": 0.0,
    "r3_materiality_z": 0.0,
}


def sigma_within_mr(x):
    """MRbar / d2 sigma estimate, NaN-skipping; None when not estimable."""
    v = np.asarray(x, dtype=float)
    v = v[np.isfinite(v)]
    if v.size < 2:
        return None
    mr = np.abs(np.diff(v))
    mr = mr[np.isfinite(mr)]
    if mr.size == 0:
        return None
    sigma = float(np.mean(mr)) / D2
    return sigma if sigma > 0 else None


def _runs(mask):
    """(start, length) of consecutive True runs in a boolean array."""
    m = np.asarray(mask, dtype=bool)
    if m.size == 0:
        return []
    padded = np.concatenate(([False], m, [False]))
    edges = np.flatnonzero(np.diff(padded.astype(np.int8)))
    return [(int(edges[i]), int(edges[i + 1] - edges[i])) for i in range(0, edges.size, 2)]


def _merge_positions(idxs, gap):
    """Merge trigger positions whose gap <= gap into episodes (first index)."""
    if len(idxs) == 0:
        return []
    episodes = []
    start = prev = int(idxs[0])
    for i in idxs[1:]:
        i = int(i)
        if i - prev <= gap:
            prev = i
        else:
            episodes.append((start, prev))
            start = prev = i
    episodes.append((start, prev))
    return episodes


def _slide_count(mask, w):
    """Count of True in each window [i, i+w); NaN handled by caller."""
    c = np.concatenate(([0], np.cumsum(mask.astype(np.int64))))
    return c[w:] - c[:-w]


def _episodes_from_runs(runs, min_len, extra=0):
    """Runs of length >= min_len become episodes; violation index = the point
    where the rule first becomes true (start + min_len - 1 + extra)."""
    out = []
    for start, ln in runs:
        if ln >= min_len:
            out.append({"index": start + min_len - 1 + extra,
                        "run_start": start,
                        "run_length": ln})
    return out


def _episodes_from_slide(mask_valid, hit, w, k, gap=None):
    """k-of-w sliding rule: returns episodes at the first window-end index."""
    n = hit.size
    if n < w:
        return []
    cnt = _slide_count(hit & mask_valid, w)
    full = _slide_count(mask_valid, w) == w
    pos = np.flatnonzero((cnt >= k) & full)
    if pos.size == 0:
        return []
    merged = _merge_positions(pos, gap if gap is not None else max(1, w - 1))
    return [{"index": int(end) + w - 1, "run_start": int(start),
             "run_length": int(end - start + w)}
            for start, end in merged]


def evaluate(z, params=None):
    """Run all five rules on a z-array. Returns list of episode dicts:
    {rule_name, index, run_length, statistic} — index is the observation
    position where the rule first fires (0-based into the passed array)."""
    cfg = dict(DEFAULTS)
    if params:
        cfg.update({k: float(v) if k.endswith("materiality_z") else int(v)
                    for k, v in params.items() if k in DEFAULTS})
    z = np.asarray(z, dtype=float)
    n = z.size
    if n < cfg["min_points"]:
        return []

    valid = np.isfinite(z)
    episodes = []

    # R1 — single point beyond 3 sigma
    for start, ln in _runs(valid & (np.abs(np.where(valid, z, 0.0)) > 3.0)):
        idx = start + ln - 1
        episodes.append({"rule_name": RULE["NELSON_R1"], "index": idx,
                         "run_length": ln, "statistic": float(z[idx])})

    # R2 — run-length on one side of center (+ materiality floor)
    side = np.where(valid, np.sign(z), 0).astype(np.int8)
    for sgn in (1, -1):
        for e in _episodes_from_runs(_runs(side == sgn), cfg["run_length_r2"]):
            idx = e["index"]
            if not valid[idx]:
                continue
            win = z[e["run_start"]:e["run_start"] + cfg["run_length_r2"]]
            median_side_z = float(np.nanmedian(win)) * sgn
            if median_side_z < cfg["r2_materiality_z"]:
                continue
            episodes.append({"rule_name": RULE["NELSON_R2"], **e,
                             "statistic": float(z[idx])})

    # R3 — six consecutive steadily increasing / decreasing points
    dz = np.diff(np.where(valid, z, np.nan))
    for sgn in (1, -1):
        mask = valid[:-1] & valid[1:] & (np.sign(dz) == sgn)
        for e in _episodes_from_runs(_runs(mask), cfg["run_length_r3"] - 1):
            idx = e["index"] + 1  # point after the last qualifying diff
            if idx >= n or not valid[idx]:
                continue
            total_move = (z[idx] - z[e["run_start"]]) * sgn
            if not np.isfinite(total_move) or total_move < cfg["r3_materiality_z"]:
                continue
            e2 = dict(e)
            e2["index"] = idx
            episodes.append({"rule_name": RULE["NELSON_R3"], **e2,
                             "statistic": float(z[idx])})

    # R5 — 2 of 3 beyond 2 sigma on the same side
    for sgn in (1, -1):
        hit = valid & (z * sgn > 2.0)
        for e in _episodes_from_slide(valid, hit, cfg["r5_of"], cfg["r5_count"]):
            idx = e["index"]
            if valid[idx]:
                episodes.append({"rule_name": RULE["NELSON_R5"], **e,
                                 "statistic": float(z[idx])})

    # R6 — 4 of 5 beyond 1 sigma on the same side
    for sgn in (1, -1):
        hit = valid & (z * sgn > 1.0)
        for e in _episodes_from_slide(valid, hit, cfg["r6_of"], cfg["r6_count"]):
            idx = e["index"]
            if valid[idx]:
                episodes.append({"rule_name": RULE["NELSON_R6"], **e,
                                 "statistic": float(z[idx])})

    episodes.sort(key=lambda e: (e["index"], e["rule_name"]))
    return episodes


def evaluate_segments(segments, params=None):
    """Evaluate z-arrays on consecutive segments (post-change-point
    re-centering). Segments: list of (offset, z_array). Episode indices are
    mapped back to absolute positions via the offset."""
    out = []
    for offset, z in segments:
        for e in evaluate(z, params):
            e = dict(e)
            e["index"] = e["index"] + int(offset)
            out.append(e)
    return out


def severity_for(rule_name):
    """Frozen severity semantics:
    warn = trend (R2/R3) · high = statistical anomaly (R1/R5/R6)."""
    if rule_name in (RULE["NELSON_R2"], RULE["NELSON_R3"]):
        return SEV["warn"]
    return SEV["high"]
