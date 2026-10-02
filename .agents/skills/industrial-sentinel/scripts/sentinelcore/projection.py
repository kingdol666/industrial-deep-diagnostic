"""projection.py — window drift projection (check C2).

For each operating window copied verbatim from doe-analyzer
recommendations (factor + numeric range [lo, hi] + confirmation_needed):

  1. restrict to the steady rows of the window (regime labels from C3);
  2. slope = (mean(last 25%) - mean(first 25%)) / hours between the two
     segment centers  ->  slope_per_hour, direction-aware;
  3. current = mean(last 25%); drift edge = hi when slope > 0 else lo;
     hours_to_edge = (edge - current) / |slope|  (0 when already past edge);
  4. severity: confirmation_needed=true window -> capped at warn with
     advisory=true (contract twin of doe-analyzer G4 — a confirmation-pending
     window must never escalate past warn); otherwise hours_to_edge <=
     hours_alarm (default 8h) -> high, <= hours_warn (default 24h) -> warn,
     else info.
  5. current already outside [lo, hi] -> WINDOW_OUT_OF_RANGE (critical,
     immediate; still capped by confirmation_needed).

Pure numpy, zero LLM, zero network.
"""

import numpy as np

from sentinelcore._constants import CHECK, RULE, SEV, URG

DEFAULTS = {
    "hours_warn": 24.0,
    "hours_alarm": 8.0,
    "min_points": 8,       # fewer steady rows -> no projection possible
    "min_slope": 1e-12,    # |slope| below this counts as flat
    "quarter_frac": 0.25,
}


def project(values, hours, lo, hi, confirmation_needed, thresholds=None):
    """Compute one projection. Returns dict with
    {slope_per_hour, current, direction, hours_to_edge, level, out_of_range}
    or None when the projection is not computable."""
    cfg = dict(DEFAULTS)
    if thresholds:
        cfg.update({k: float(thresholds[k]) for k in ("hours_warn", "hours_alarm")
                    if thresholds.get(k) is not None})
    v = np.asarray(values, dtype=float)
    h = np.asarray(hours, dtype=float)
    ok = np.isfinite(v) & np.isfinite(h)
    v, h = v[ok], h[ok]
    n = v.size
    if n < cfg["min_points"] or (lo is None and hi is None):
        return None
    order = np.argsort(h, kind="stable")
    v, h = v[order], h[order]

    q = max(3, int(round(n * cfg["quarter_frac"])))
    v1, h1 = v[:q], h[:q]
    v2, h2 = v[-q:], h[-q:]
    dt = float(np.mean(h2) - np.mean(h1))
    if not np.isfinite(dt) or dt <= 0:
        return None
    slope = (float(np.mean(v2)) - float(np.mean(v1))) / dt
    current = float(np.mean(v2))

    out_of_range = (hi is not None and current > hi) or (lo is not None and current < lo)
    direction = "none"
    if slope > cfg["min_slope"]:
        direction = "up"
    elif slope < -cfg["min_slope"]:
        direction = "down"

    hours_to_edge = None
    if direction == "up" and hi is not None:
        hours_to_edge = max(0.0, (hi - current) / slope)
    elif direction == "down" and lo is not None:
        hours_to_edge = max(0.0, (current - lo) / (-slope))

    if out_of_range:
        level = SEV["critical"]
    elif hours_to_edge is None:
        level = SEV["info"]
    elif hours_to_edge <= cfg["hours_alarm"]:
        level = SEV["high"]
    elif hours_to_edge <= cfg["hours_warn"]:
        level = SEV["warn"]
    else:
        level = SEV["info"]

    if confirmation_needed and level in (SEV["high"], SEV["critical"]):
        level = SEV["warn"]  # frozen cap — see module docstring

    return {
        "slope_per_hour": slope,
        "current": current,
        "direction": direction,
        "hours_to_edge": hours_to_edge,
        "level": level,
        "out_of_range": bool(out_of_range),
        "n_points": int(n),
    }


def hours_to_edge_severity(hours_to_edge, confirmation_needed, thresholds=None):
    """Severity for a projected edge arrival time (used by fast-screen with a
    cached slope)."""
    cfg = dict(DEFAULTS)
    if thresholds:
        cfg.update({k: float(thresholds[k]) for k in ("hours_warn", "hours_alarm")
                    if thresholds.get(k) is not None})
    if hours_to_edge is None:
        return SEV["info"]
    if hours_to_edge <= cfg["hours_alarm"]:
        level = SEV["high"]
    elif hours_to_edge <= cfg["hours_warn"]:
        level = SEV["warn"]
    else:
        return SEV["info"]
    if confirmation_needed:
        return SEV["warn"]
    return level


def urgency_for(level):
    if level == SEV["critical"]:
        return URG["immediate"]
    if level == SEV["high"]:
        return URG["same_shift"]
    return URG["routine"]


def alert_fields(level):
    """(check_type, rule_name) pair for projection alerts."""
    return CHECK["window_projection"], RULE["WINDOW_DRIFT_PROJECTION"]


def out_of_range_fields():
    return CHECK["window_projection"], RULE["WINDOW_OUT_OF_RANGE"]
