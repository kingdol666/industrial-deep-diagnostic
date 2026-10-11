"""Per-parameter stability metrics: capability + Theil-Sen drift.

SPC convention matches industrial-sentinel: sigma_within = MRbar / 1.128.
Nelson judging lives in spc_adapter (sentinelcore reuse) — this module keeps
capability and drift only.
"""
from __future__ import annotations

import numpy as np
from scipy import stats

SECONDS_PER_DAY = 86400.0


def mrbar_sigma(x: np.ndarray) -> float | None:
    """sigma estimate from mean moving range (sentinel-compatible)."""
    x = x[~np.isnan(x)]
    if len(x) < 2:
        return None
    mr = np.abs(np.diff(x))
    return float(np.mean(mr) / 1.128)


def capability(x: np.ndarray, lsl: float | None, usl: float | None) -> dict:
    """Cp/Cpk (within, MRbar sigma) and Pp/Ppk (overall sigma). None when undefined."""
    clean = x[~np.isnan(x)]
    if len(clean) < 8 or (lsl is None and usl is None):
        return {"cp": None, "cpk": None, "pp": None, "ppk": None}
    mu = float(np.mean(clean))
    s_within = mrbar_sigma(clean)
    s_overall = float(np.std(clean, ddof=1))
    if not s_within or not s_overall:
        return {"cp": None, "cpk": None, "pp": None, "ppk": None}
    cp = cpk = pp = ppk = None
    if lsl is not None and usl is not None and usl > lsl:
        cp = (usl - lsl) / (6 * s_within)
        pp = (usl - lsl) / (6 * s_overall)
    cpu = (usl - mu) / (3 * s_within) if usl is not None else None
    cpl = (mu - lsl) / (3 * s_within) if lsl is not None else None
    ppu = (usl - mu) / (3 * s_overall) if usl is not None else None
    ppl = (mu - lsl) / (3 * s_overall) if lsl is not None else None
    mins = [v for v in (cpu, cpl) if v is not None]
    minp = [v for v in (ppu, ppl) if v is not None]
    cpk = min(mins) if mins else None
    ppk = min(minp) if minp else None
    return {"cp": _r(cp), "cpk": _r(cpk), "pp": _r(pp), "ppk": _r(ppk)}


def drift(x: np.ndarray, interval_seconds: float | None) -> dict:
    """Theil-Sen slope + Mann-Kendall significance, expressed relative per day.

    Honesty gates: drift counts as significant only when BOTH
    mk_p < 0.01 AND relative drift >= 0.1%/day. A pure-noise series routinely
    passes p<0.05 on ~1000 points, and extrapolating its tiny slope to a full
    day produces absurd percentages — the materiality gate prevents that.
    """
    clean = x[~np.isnan(x)]
    res = {"slope_per_second": None, "per_day_relative": None,
           "mk_p": None, "significant": False}
    if len(clean) < 20:
        return res
    t = np.arange(len(clean), dtype=float)
    try:
        slope = stats.theilslopes(clean, t)[0]
        mk_p = float(stats.kendalltau(t, clean).pvalue)
    except Exception:
        return res
    if not np.isfinite(slope) or not np.isfinite(mk_p):
        return res
    scale = float(np.median(clean))
    if abs(scale) < 1e-12:
        scale = float(np.std(clean, ddof=1) * 4.0)
    # slope is [unit]/row; one row spans `interval_seconds`, so [unit]/s = slope/interval
    per_sec = float(slope) / (interval_seconds or 1.0)
    res["slope_per_second"] = _r(per_sec)
    res["mk_p"] = round(mk_p, 6)
    per_day_rel = None
    if scale and np.isfinite(scale) and abs(scale) > 1e-12:
        per_day_rel = _r(abs(per_sec) * SECONDS_PER_DAY / abs(scale))
        res["per_day_relative"] = per_day_rel
    res["significant"] = bool(mk_p < 0.01 and per_day_rel is not None
                              and per_day_rel >= 0.001)
    return res


def _r(v):
    return round(float(v), 6) if v is not None and np.isfinite(v) else None
