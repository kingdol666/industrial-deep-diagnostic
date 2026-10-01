"""regime_map.py — check C3: regime / steady-state mapping + change points.

Reuses the data-processor's production_regime_detector **in-process** (never
via subprocess): detect_by_variance_fast + detect_change_points_fast +
detect_drift_ramps_fast -> fuse_regimes. The raw binary-segmentation output
fires on every noise wiggle (it splits until n_segments are exhausted), so
sentinel adds a significance filter:

  keep cp  iff  |mean(z after cp) - mean(z before cp)| >= cp_min_shift_z
  with a symmetric look L = clamp(n // 4, 50, 4000) rows on each side and
  z standardized by the caller (baseline center/sigma in watch mode,
  overall mean/std during baseline construction).

Rationale: for a linear drift the segment-mean difference equals slope * L
regardless of where the change point sits, while pure-noise change points
give ~sqrt(2/L) sigma. With defaults (0.5 sigma, L ~ n/4) the separation is
roughly an order of magnitude on both sides — see method_notes.md.

Only change points that survive the filter AND are absent from
baseline.regime.known_change_points are reported as REGIME_CHANGE_NEW; each
new change point opens a quiet zone (post_changepoint_quiet_rows) during
which SPC alerts are suppressed and the center line is re-estimated.

A pure-Python fallback (variance-ratio only, no change points, no ramps)
keeps the skill runnable when the in-process import is impossible.
"""

import numpy as np

from sentinelcore._constants import DP_SCRIPTS, RULE, SEV

import sys

ABNORMAL_LABEL = "abnormal"
DEFAULTS = {
    "window_rows": 10,
    "variance_threshold": 3.0,
    "ramp_threshold": 0.03,
    "cp_min_shift_z": 0.5,
    "min_rows": 60,          # below this: label everything steady, no detection
}


def _load_detector():
    """In-process import of the data-processor fast detector. Returns the
    module or None (fallback path)."""
    try:
        if str(DP_SCRIPTS) not in sys.path:
            sys.path.insert(0, str(DP_SCRIPTS))
        import production_regime_detector as prd  # noqa: PLC0415

        if not hasattr(prd, "detect_by_variance_fast"):
            return None
        return prd
    except Exception:
        return None


def _variance_scores_py(col_arrays, window):
    """Pure-Python variance-ratio scores (fallback; O(n * window))."""
    per_param = {}
    for c, vals in col_arrays.items():
        clean = [v for v in vals if v is not None and np.isfinite(v)]
        if len(clean) < 10:
            continue
        mu = abs(sum(clean) / len(clean)) + 1e-9
        var_all = sum((v - sum(clean) / len(clean)) ** 2 for v in clean) / (len(clean) - 1)
        cv = (var_all ** 0.5) / mu
        if not (0.001 < cv < 0.5):
            continue
        n = len(vals)
        local = []
        for i in range(n):
            seg = [vals[j] for j in range(max(0, i - window), min(n, i + window + 1))
                   if vals[j] is not None and np.isfinite(vals[j])]
            if len(seg) < 3:
                local.append(0.0)
                continue
            m = sum(seg) / len(seg)
            var = sum((v - m) ** 2 for v in seg) / (len(seg) - 1)
            local.append(var ** 0.5)
        pos = [s for s in local if s > 0]
        if not pos:
            continue
        pos_sorted = sorted(pos)
        m = len(pos_sorted)
        baseline = (pos_sorted[m // 2] if m % 2 else
                    (pos_sorted[m // 2 - 1] + pos_sorted[m // 2]) / 2.0) + 1e-9
        per_param[c] = [s / baseline for s in local]
    if len(per_param) < 2:
        return None
    n = len(next(iter(col_arrays.values())))
    scores = []
    for i in range(n):
        row = [per_param[c][i] for c in per_param
               if per_param[c][i] is not None and np.isfinite(per_param[c][i])]
        row_sorted = sorted(row or [1.0])
        m = len(row_sorted)
        med = row_sorted[m // 2] if m % 2 else (row_sorted[m // 2 - 1] + row_sorted[m // 2]) / 2
        scores.append(float(med))
    return scores


def _fuse_py(variance_scores, change_points, n_rows, window, variance_threshold,
             ramp_threshold):
    """Pure-Python replica of fuse_regimes priority ladder (fallback path)."""
    labels = ["steady"] * n_rows
    if variance_scores is None:
        return labels
    cp_mask = [False] * n_rows
    for cp in change_points:
        for i in range(max(0, cp - window // 2), min(n_rows, cp + window // 2 + 1)):
            cp_mask[i] = True
    for i in range(n_rows):
        vs = variance_scores[i] if variance_scores[i] is not None else 1.0
        if cp_mask[i]:
            labels[i] = "transition"
        elif vs > variance_threshold:
            labels[i] = ABNORMAL_LABEL  # no ramps in fallback: no startup/shutdown
        elif vs > variance_threshold * 0.7:
            labels[i] = "marginal"
    return labels


def _segmentation(z_mean, min_size, n_segments=12):
    """Binary segmentation on the standardized mean series. Prefers the
    data-processor's vectorized implementation (in-process); pure-Python
    prefix-sum replica as fallback."""
    prd = _load_detector()
    seg = getattr(prd, "_binary_segmentation_fast", None) if prd else None
    if seg is not None:
        try:
            return [int(c) for c in
                    seg(np.asarray(z_mean, dtype=float),
                        min_size=int(min_size), n_segments=int(n_segments))]
        except Exception:  # noqa: BLE001 — fall through to the replica
            pass
    return _binary_segmentation_py(z_mean, min_size, n_segments)


def _binary_segmentation_py(values, min_size, n_segments):
    """Prefix-sum binary segmentation (pure Python fallback, same algebra as
    the data-processor fast path: between-segment SSE reduction)."""
    v = np.asarray(values, dtype=float)
    valid = np.flatnonzero(np.isfinite(v))
    if valid.size < 2 * min_size:
        return []
    vv = v[valid]
    m = vv.size
    c1 = np.concatenate(([0.0], np.cumsum(vv)))
    segments = [(0, m)]
    change_points = []
    for _ in range(int(n_segments)):
        best_red, best_seg_idx, best_split = -1.0, -1, -1
        for si, (a, b) in enumerate(segments):
            if b - a < 2 * min_size:
                continue
            k = np.arange(a + min_size, b - min_size + 1)
            if k.size == 0:
                continue
            cnt_l = (k - a).astype(float)
            cnt_r = (b - k).astype(float)
            s_l = c1[k] - c1[a]
            s_r = c1[b] - c1[k]
            s_t = c1[b] - c1[a]
            red = s_l * s_l / cnt_l + s_r * s_r / cnt_r - s_t * s_t / (b - a)
            imax = int(np.argmax(red))
            if float(red[imax]) > best_red:
                best_red, best_seg_idx, best_split = float(red[imax]), si, int(k[imax])
        if best_red <= 0 or best_split < 0:
            break
        a, b = segments.pop(best_seg_idx)
        segments.append((a, best_split))
        segments.append((best_split, b))
        change_points.append(int(valid[best_split]))
    return sorted(set(change_points))


def _cluster(cps, tol):
    """Merge change points closer than tol rows (median of each cluster)."""
    if not cps:
        return []
    out = []
    current = [cps[0]]
    for cp in cps[1:]:
        if cp - current[-1] <= tol:
            current.append(cp)
        else:
            out.append(int(np.median(current)))
            current = [cp]
    out.append(int(np.median(current)))
    return out


def detect(col_arrays, z_mean=None, thresholds=None):
    """Run the C3 pipeline on one group.

    col_arrays: {col: float ndarray}; z_mean: per-row mean z (NaN allowed);
    thresholds: config overrides.

    Labels come from the data-processor fast detector (variance ratio +
    drift ramps fused); change points come from binary segmentation of the
    standardized mean series followed by the significance filter — the
    detector's own detect_change_points_fast requires >= 2 parameters to
    agree within `window` rows, which a single drifting parameter never
    satisfies, so sentinel segments z_mean directly instead (documented in
    method_notes.md §4).

    Returns dict:
      labels            list[str] per row
      change_points     filtered, significant change points (sorted ints)
      abnormal_ratio    float
      method            str (fast | fallback)
    """
    cfg = dict(DEFAULTS)
    if thresholds:
        cfg.update({k: thresholds[k] for k in
                    ("window_rows", "variance_threshold", "ramp_threshold",
                     "cp_min_shift_z") if thresholds.get(k) is not None})
    n = len(next(iter(col_arrays.values()))) if col_arrays else 0
    window = int(cfg["window_rows"])
    if n < cfg["min_rows"]:
        return {"labels": ["steady"] * n, "change_points": [],
                "abnormal_ratio": 0.0, "method": "skipped_too_few_rows"}

    prd = _load_detector()
    change_points = []
    if prd is not None:
        variance_scores, _stats = prd.detect_by_variance_fast(col_arrays, window)
        ramp_scores, _detail = prd.detect_drift_ramps_fast(col_arrays, window, n)
        if z_mean is not None:
            raw_cps = _segmentation(z_mean, min_size=max(5, window))
            change_points = _cluster(
                filter_change_points(z_mean, raw_cps, n,
                                     min_shift_z=float(cfg["cp_min_shift_z"])),
                tol=window)
        # transition labels are laid around the SIGNIFICANT cps only, so the
        # steady mask and the reported change points tell the same story
        labels, _diag, _abw = prd.fuse_regimes(
            variance_scores, change_points, ramp_scores, n,
            variance_threshold=float(cfg["variance_threshold"]),
            window=window, ramp_threshold=float(cfg["ramp_threshold"]))
        method = "fast"
    else:
        variance_scores = _variance_scores_py(col_arrays, window)
        labels = _fuse_py(variance_scores, [], n, window,
                          float(cfg["variance_threshold"]),
                          float(cfg["ramp_threshold"]))
        method = "fallback_python"

    abnormal = sum(1 for lab in labels if lab == ABNORMAL_LABEL)
    return {
        "labels": list(labels),
        "change_points": sorted(int(c) for c in change_points),
        "abnormal_ratio": (abnormal / n) if n else 0.0,
        "method": method,
    }


def filter_change_points(z_mean, raw_cps, n, min_shift_z=0.5):
    """Significance filter — see module docstring for the frozen rationale.

    Before/after segment summaries use the MEDIAN (not the mean): a
    single-point spike shifts segment means enough to masquerade as a level
    change (R1's job), but never moves medians — while a linear drift still
    shifts medians by exactly slope * L."""
    z = np.asarray(z_mean, dtype=float)
    look = int(min(max(n // 4, 50), 4000))
    kept = []
    for cp in sorted(int(c) for c in raw_cps):
        left = min(look, cp)
        right = min(look, n - cp)
        if left < 50 or right < 50:
            continue
        before = z[cp - left:cp]
        after = z[cp:cp + right]
        before = before[np.isfinite(before)]
        after = after[np.isfinite(after)]
        if before.size < 30 or after.size < 30:
            continue
        if abs(float(np.median(after)) - float(np.median(before))) >= min_shift_z:
            kept.append(cp)
    return kept


def new_change_points(detected, known, tolerance=0):
    """Set difference of detected vs baseline-known change points (indices
    within +/- tolerance of a known point count as known)."""
    out = []
    for cp in detected:
        if not any(abs(cp - int(k)) <= tolerance for k in (known or [])):
            out.append(cp)
    return sorted(out)


def abnormal_severity(ratio, thresholds=None):
    """abnormal share: >0.15 -> high, >0.3 -> critical, else None (recorded
    in regime_summary only)."""
    cfg = {"abnormal_ratio_warn": 0.15, "abnormal_ratio_critical": 0.3}
    if thresholds:
        cfg.update({k: float(thresholds[k]) for k in
                    ("abnormal_ratio_warn", "abnormal_ratio_critical")
                    if thresholds.get(k) is not None})
    if ratio > cfg["abnormal_ratio_critical"]:
        return SEV["critical"]
    if ratio > cfg["abnormal_ratio_warn"]:
        return SEV["high"]
    return None


def rule_change_new():
    return RULE["REGIME_CHANGE_NEW"]


def rule_abnormal():
    return RULE["REGIME_ABNORMAL"]


def label_counts(labels):
    counts = {}
    for lab in labels:
        counts[lab] = counts.get(lab, 0) + 1
    return dict(sorted(counts.items()))
