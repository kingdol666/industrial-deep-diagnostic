"""suppress.py — anti-alert-storm layer (frozen three-piece set).

1. Same-key suppression   all raw triggers sharing one suppression_key inside
                          one run merge into a single alert with
                          repeat_count = number of merged triggers; across
                          fast-screen runs the same key inside
                          suppress_window_minutes (default 60) increments the
                          stored count instead of opening a new alert.
2. Hysteresis             a persisted condition only steps DOWN one severity
                          level after hysteresis_points (default 5)
                          consecutive in-band observations — carried in
                          fast_state.consecutive_in_band.
3. Quiet zone             after a NEW change point, SPC alerts inside the
                          next post_changepoint_quiet_rows (default 30) rows
                          are suppressed and the center line is re-estimated
                          from the post-change segment (watch mode).

Defaults come from closedloop_enums.json sentinel.suppression — the numbers
are contract, not taste (see method_notes.md §5 for the rationale).
"""

import datetime

from sentinelcore._constants import SUPPRESSION_DEFAULTS


def make_suppression_key(group, check_type, rule_name, target):
    """group|check_type|rule|target — target is parameter or indicator name."""
    return f"{group or '_'}|{check_type}|{rule_name}|{target or '_'}"


def merge_by_key(alerts, max_gap_rows=None):
    """Merge raw alert dicts sharing a suppression_key.

    Two same-key triggers belong to the SAME episode (and merge into one
    alert, repeat_count+1) only when their observed.index gap is within
    max_gap_rows — the row-space image of suppress_window_minutes at the
    canonical 1 sample/minute cadence (frozen convention; the gate checks
    the same row-space proxy). Triggers farther apart stay separate alerts:
    a persistent condition re-alerts per suppression window instead of being
    silently swallowed by one lifelong entry.

    Each merged episode keeps the earliest observed.index, the highest
    severity of the episode, and the merged repeat_count. Ordering follows
    first appearance."""
    if max_gap_rows is None:
        max_gap_rows = SUPPRESSION_DEFAULTS["suppress_window_minutes"]

    def _idx(a):
        idx = (a.get("observed") or {}).get("index")
        return idx if isinstance(idx, (int, float)) else None

    episodes = []  # [key, last_idx, entry]
    out = []
    for a in alerts:
        key = a["suppression_key"]
        idx = _idx(a)
        target = None
        for ep in reversed(episodes):
            if ep[0] != key:
                continue
            last_idx = ep[1]
            if last_idx is not None and idx is not None \
                    and abs(idx - last_idx) <= max_gap_rows:
                target = ep
            break  # only the most recent episode of this key can chain
        if target is None:
            entry = dict(a)
            episodes.append([key, idx, entry])
            out.append(entry)
            continue
        entry = target[2]
        entry["repeat_count"] = int(entry.get("repeat_count", 1)) + 1
        target[1] = idx if idx is not None else target[1]
        old_idx = (entry.get("observed") or {}).get("index")
        if old_idx is None or (idx is not None and idx < old_idx):
            entry["observed"] = dict(a.get("observed") or {})
        if _rank(a.get("severity")) > _rank(entry.get("severity")):
            entry["severity"] = a["severity"]
            entry["urgency"] = a.get("urgency", entry.get("urgency"))
    return out


def _rank(sev):
    order = {s: i for i, s in enumerate(["info", "warn", "high", "critical"])}
    return order.get(sev, -1)


def downgrade_severity(sev):
    """One step down the severity ladder; info stays info."""
    ladder = ["critical", "high", "warn", "info"]
    if sev not in ladder:
        return sev
    i = ladder.index(sev)
    return ladder[min(i + 1, len(ladder) - 1)]


def quiet_mask(n_rows, change_points, quiet_rows):
    """Boolean mask: True inside any [cp, cp + quiet_rows) zone."""
    mask = [False] * n_rows
    for cp in change_points or []:
        for i in range(int(cp), min(n_rows, int(cp) + int(quiet_rows))):
            mask[i] = True
    return mask


def parse_ts(value):
    if not value:
        return None
    try:
        return datetime.datetime.fromisoformat(str(value))
    except ValueError:
        return None


def suppression_table_update(table, keys_now, now_iso, window_minutes=None,
                             max_age_hours=24):
    """fast-screen suppression table: {key: {since, count}}.

    Returns (table, prior_counts) — prior_counts[key] is the stored count for
    keys re-observed inside the window (0 when new/expired). Entries older
    than max_age_hours are dropped to keep the state file bounded."""
    cfg_window = window_minutes or SUPPRESSION_DEFAULTS["suppress_window_minutes"]
    now = parse_ts(now_iso)
    prior = {}
    cleaned = {}
    for key, entry in (table or {}).items():
        since = parse_ts((entry or {}).get("since"))
        if now is not None and since is not None:
            age_h = (now - since).total_seconds() / 3600.0
            if age_h > max_age_hours:
                continue
        cleaned[key] = {"since": (entry or {}).get("since") or now_iso,
                        "count": int((entry or {}).get("count", 1))}
    for key in keys_now:
        entry = cleaned.get(key)
        if entry is not None and now is not None:
            since = parse_ts(entry["since"])
            if since is not None and (now - since).total_seconds() <= cfg_window * 60:
                prior[key] = int(entry["count"])
                entry["count"] = int(entry["count"]) + 1
                continue
        cleaned[key] = {"since": now_iso, "count": 1}
        prior[key] = 0
    return cleaned, prior


def hysteresis_update(counters, violating_keys, n_new_rows, hysteresis_points=None):
    """Update consecutive in-band counters.

    counters: {key: consecutive in-band rows seen since last violation}.
    violating_keys: keys whose condition fires on the newest rows.
    Returns the updated counters dict (mutated copy semantics: input mutated
    in place and returned)."""
    pts = hysteresis_points or SUPPRESSION_DEFAULTS["hysteresis_points"]
    out = dict(counters or {})
    for key in list(out.keys()):
        out[key] = int(out[key]) + int(n_new_rows)
    for key in violating_keys:
        out[key] = 0
    # bound growth: keep only keys that recently mattered
    return {k: v for k, v in out.items() if v <= max(pts * 50, 300)}


def hysteresis_downgrade(alerts, counters, hysteresis_points=None):
    """Downgrade one severity level for alerts whose key had >= N consecutive
    in-band observations before this new violation (re-trigger after
    recovery, not a fresh condition)."""
    pts = hysteresis_points or SUPPRESSION_DEFAULTS["hysteresis_points"]
    out = []
    for a in alerts:
        key = a.get("suppression_key")
        if key is not None and int((counters or {}).get(key, 0) or 0) >= pts:
            a = dict(a)
            a["severity"] = downgrade_severity(a.get("severity"))
            a["advisory"] = True
            a["evidence"] = dict(a.get("evidence") or {})
            a["evidence"]["hysteresis_downgraded"] = True
        out.append(a)
    return out
