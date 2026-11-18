"""robust.py — shared deterministic math for E-1H feature extraction.

numpy/pandas/scipy only. Every function ignores non-finite values and returns
NaN (never raises) on insufficient input, so callers can mark
insufficient_data instead of inventing numbers.
"""
from __future__ import annotations

import math

import numpy as np


def finite(x) -> np.ndarray:
    arr = np.asarray(x, dtype=float)
    return arr[np.isfinite(arr)]


def n_finite(x) -> int:
    return int(finite(x).size)


def pctl(x, q: float) -> float:
    v = finite(x)
    return float(np.percentile(v, q)) if v.size else float("nan")


def mean(x) -> float:
    v = finite(x)
    return float(v.mean()) if v.size else float("nan")


def std(x) -> float:
    v = finite(x)
    return float(v.std(ddof=1)) if v.size >= 2 else float("nan")


def vmin(x) -> float:
    v = finite(x)
    return float(v.min()) if v.size else float("nan")


def vmax(x) -> float:
    v = finite(x)
    return float(v.max()) if v.size else float("nan")


def median(x) -> float:
    v = finite(x)
    return float(np.median(v)) if v.size else float("nan")


def mad(x) -> float:
    """Median absolute deviation (scale-free, no 1.4826 factor — raw MAD)."""
    v = finite(x)
    if not v.size:
        return float("nan")
    med = np.median(v)
    return float(np.median(np.abs(v - med)))


def iqr(x) -> float:
    return pctl(x, 75) - pctl(x, 25)


def lsq_slope_curv(y, per_n: float = 100.0) -> tuple[float, float]:
    """Least-squares slope (per `per_n` x-units) and quadratic coefficient of y
    over x = 0..n-1. Returns (nan, nan) when <3 finite points."""
    v = finite(y)
    if v.size < 3:
        return float("nan"), float("nan")
    x = np.arange(v.size, dtype=float)
    slope = float(np.polyfit(x, v, 1)[0]) * (per_n / max(v.size - 1, 1))
    curv = float(np.polyfit(x, v, 2)[0]) if v.size >= 4 else float("nan")
    return slope, curv


def argmax_pos(x) -> int:
    """0-based index of the max over finite values; -1 when none."""
    arr = np.asarray(x, dtype=float)
    mask = np.isfinite(arr)
    if not mask.any():
        return -1
    idx = np.where(mask)[0]
    return int(idx[np.argmax(arr[idx])])


def neighbour_deviation(x, i: int) -> float:
    """x[i] - mean(neighbours of i) over finite neighbours; NaN when undefined."""
    arr = np.asarray(x, dtype=float)
    if i < 0 or i >= arr.size or not np.isfinite(arr[i]):
        return float("nan")
    lo, hi = max(i - 1, 0), min(i + 2, arr.size)
    nbrs = [arr[j] for j in range(lo, hi) if j != i and np.isfinite(arr[j])]
    if not nbrs:
        return float("nan")
    return float(arr[i] - float(np.mean(nbrs)))


def max_abs_neighbour_deviation(x) -> tuple[float, int]:
    """(max |x[i]-mean(nbrs)|, argmax index) over finite entries; (nan,-1) if none."""
    arr = np.asarray(x, dtype=float)
    best, best_i = float("nan"), -1
    for i in range(arr.size):
        d = neighbour_deviation(arr, i)
        if math.isnan(d):
            continue
        if math.isnan(best) or abs(d) > abs(best):
            best, best_i = d, i
    return best, best_i


def edge_band_deviation(x, band_frac: float = 0.10) -> dict:
    """Mean of each outer `band_frac` band minus centre-band mean.
    Requires >=3 distinct bands; NaN otherwise."""
    v = finite(x)
    if v.size < 6:
        return {"edge_l": float("nan"), "edge_r": float("nan")}
    k = max(1, int(round(v.size * band_frac)))
    centre = v[k : v.size - k]
    if centre.size == 0:
        return {"edge_l": float("nan"), "edge_r": float("nan")}
    cm = float(centre.mean())
    return {"edge_l": float(v[:k].mean()) - cm, "edge_r": float(v[-k:].mean()) - cm}


def zone_means(x, n_zones: int = 3) -> list[float]:
    v = finite(x)
    if v.size < n_zones:
        return [float("nan")] * n_zones
    edges = np.linspace(0, v.size, n_zones + 1).astype(int)
    return [float(v[edges[i] : edges[i + 1]].mean()) if edges[i + 1] > edges[i] else float("nan") for i in range(n_zones)]


def cross_correlation_shift(profile, baseline, max_shift: int | None = None) -> int:
    """Integer lateral shift of `profile` vs `baseline` maximizing correlation
    (positive = shifted right). Partial-overlap correlation; 0 when undefined."""
    a = np.asarray(profile, dtype=float)
    b = np.asarray(baseline, dtype=float)
    if a.size == 0 or b.size != a.size:
        return 0
    max_shift = max_shift or max(1, a.size // 4)
    best_r, best_s = -2.0, 0
    for s in range(-max_shift, max_shift + 1):
        if s == 0:
            lo, hi = 0, a.size
        elif s > 0:
            lo, hi = s, a.size
        else:
            lo, hi = 0, a.size + s
        if hi - lo < max(3, a.size // 3):
            continue
        xa, xb = a[lo:hi], b[lo - s : hi - s]
        xa, xb = finite(xa), finite(xb)
        if xa.size < 3:
            continue
        if xa.std() < 1e-12 or xb.std() < 1e-12:
            continue
        r = float(np.corrcoef(xa, xb)[0, 1])
        if r > best_r:
            best_r, best_s = r, s
    return int(best_s) if best_r > -2.0 else 0
