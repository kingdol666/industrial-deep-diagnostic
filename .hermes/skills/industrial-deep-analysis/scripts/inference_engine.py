#!/usr/bin/env python3
"""inference_engine.py — E3.5: data-driven association inference layer.

Deterministic inference primitives that turn raw cleaned data into *reasoned*
association evidence: which variables move together, in which temporal order,
through which intermediate channels, and how stable that evidence is.

Every function is pure numpy/pandas, robust to degenerate input, and returns
explicit status fields instead of raising. Nothing here invents physics — the
ontology remains the only source of physical priors; this layer only reports
what the data itself supports.

Public API
----------
* ``safe_p_value``            — erfc-based two-sided p with scientific floor
* ``pearson_r``               — degenerate-safe Pearson helper
* ``pairwise_scan``           — full all-pairs association scan (r, p, BH q)
* ``temporal_causality``      — lag-CCF precedence test (who leads whom)
* ``change_point_co_movement``— CUSUM change points + cross-series alignment
* ``conditional_independence``— full-order (ridge) / stepwise partial correlation
* ``leverage_stability``      — vectorized leave-one-out r stability
* ``moderator_check``         — per-partition sign/magnitude divergence
* ``mediation_scan``          — indirect-association channel detection
* ``causality_ceiling``       — evidence-level synthesis per pair
* ``build_association_graph`` — final graph assembly (nodes + edges)
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from stat_utils import (  # noqa: E402
    benjamini_hochberg,
    _finite_mask,
    _pearson_r,
    safe_p_value,
    P_VALUE_FLOOR,
)

# Tunable defaults (deterministic; no data-dependent randomness)
MIN_PAIR_N = 10            # minimum finite rows for any association statistic
MIN_ABS_R = 0.3            # |r| threshold for an edge to enter the graph
Q_THRESHOLD = 0.05         # BH-corrected significance threshold
CCF_MAX_LAG_FRACTION = 0.1 # max lag steps as a fraction of n (capped)
CCF_MAX_LAG_ABS = 60       # absolute cap on searched lag steps
CP_MIN_SEG = 20            # minimum segment length for change-point splits
CP_CUSUM_THRESHOLD = 1.5   # CUSUM |S_max| > c * sqrt(n) to accept a split
CP_ALIGN_WINDOW_FRACTION = 0.02  # alignment tolerance as fraction of n
LOO_FLAG_RANGE = 0.15      # |loo range| beyond which influence is flagged
MEDIATOR_MIN_R = 0.3       # |r| required for a mediator candidate channel
DIRECT_MIN_PARTIAL = 0.15  # |partial| above which an edge counts as direct
INDIRECT_MAX_PARTIAL = 0.15  # |partial| below which an indirect edge is flagged

_CAUSALITY_LEVELS = [
    "insufficient_evidence",
    "contemporaneous_correlation",
    "temporal_precedence",
    "conditional_independence_supported",
    "ontology_consistent",
]


# ---------------------------------------------------------------------------
# 1. Full pairwise scan
# ---------------------------------------------------------------------------

def pairwise_scan(
    df: pd.DataFrame,
    columns: Sequence[str],
    min_n: int = MIN_PAIR_N,
) -> List[dict]:
    """Exhaustive all-pairs association scan over numeric ``columns``.

    Returns records sorted by descending |r|::

        {predictor, target, r, p_value, p_floor_hit, q_value, n}

    ``predictor``/``target`` are ordered so that ``predictor < target``
    lexicographically (scan is over unordered pairs; direction is resolved
    later by the temporal test).
    """
    out: List[dict] = []
    n_rows = len(df)
    p_values: List[float] = []
    meta: List[dict] = []

    cols = [c for c in columns if c in df.columns]
    for i, a in enumerate(cols):
        x = pd.to_numeric(df[a], errors="coerce").to_numpy(dtype=float)
        for b in cols[i + 1:]:
            y = pd.to_numeric(df[b], errors="coerce").to_numpy(dtype=float)
            mask = _finite_mask(x, y)
            n = int(mask.sum())
            if n < min_n:
                continue
            r = _pearson_r(x[mask], y[mask])
            if r is None:
                continue
            t_stat = r * math.sqrt((n - 2) / max(1.0 - r * r, 1e-12)) if abs(r) < 1.0 else float("inf")
            p, floor_hit = safe_p_value(t_stat)
            meta.append({"predictor": a, "target": b, "r": float(r),
                         "p_value": p, "p_floor_hit": floor_hit, "n": n})
            p_values.append(p)

    q_values = benjamini_hochberg(p_values) if p_values else []
    for rec, qv in zip(meta, q_values):
        rec["q_value"] = float(qv)
    out = meta

    out.sort(key=lambda d: abs(d["r"]), reverse=True)
    return out


# ---------------------------------------------------------------------------
# 2. Temporal causality (lag-CCF precedence test)
# ---------------------------------------------------------------------------

def _detrend_series(x: np.ndarray) -> np.ndarray:
    """Remove linear trend and mean; returns standardized first differences
    when the series is monotone in time, else centered residual."""
    x = x - np.nanmean(x)
    # linear detrend via least squares
    t = np.arange(len(x), dtype=float)
    denom = float(t @ t - (t.sum() ** 2) / len(t))
    if denom > 0:
        beta = float(t @ x) / denom
        x = x - beta * t
    sd = float(np.std(x))
    if sd == 0.0 or not math.isfinite(sd):
        return x
    return x / sd


def temporal_causality(
    x_raw: np.ndarray,
    y_raw: np.ndarray,
    t_vals: np.ndarray,
    max_lag: Optional[int] = None,
    min_n: int = MIN_PAIR_N,
) -> dict:
    """Cross-correlation-function precedence test for a (x, y) time pair.

    Returns::

        {valid, direction, optimal_lag_steps, ccf_peak_r, p_value,
         p_floor_hit, lag_aligned_r, n_used}

    ``direction`` ∈ {``x_leads_y``, ``y_leads_x``, ``concurrent``,
    ``insufficient``}. A positive ``optimal_lag_steps`` means x shifted back by
    that many steps best predicts y (x leads y). The test only claims
    precedence when the peak is meaningful *and* materially stronger than the
    concurrent correlation.
    """
    n = len(x_raw)
    if n < min_n or len(y_raw) != n or len(t_vals) != n:
        return {"valid": False, "direction": "insufficient", "optimal_lag_steps": 0,
                "ccf_peak_r": 0.0, "p_value": 1.0, "p_floor_hit": False,
                "lag_aligned_r": 0.0, "n_used": 0}

    order = np.argsort(t_vals, kind="mergesort")
    xs = _detrend_series(np.asarray(x_raw, dtype=float)[order])
    ys = _detrend_series(np.asarray(y_raw, dtype=float)[order])
    fm = np.isfinite(xs) & np.isfinite(ys)
    if int(fm.sum()) < min_n:
        return {"valid": False, "direction": "insufficient", "optimal_lag_steps": 0,
                "ccf_peak_r": 0.0, "p_value": 1.0, "p_floor_hit": False,
                "lag_aligned_r": 0.0, "n_used": 0}
    xs = xs[fm]
    ys = ys[fm]
    n_eff = len(xs)

    if max_lag is None:
        max_lag = min(CCF_MAX_LAG_ABS, max(1, int(n_eff * CCF_MAX_LAG_FRACTION)))
    max_lag = max(1, int(max_lag))

    # Cross-correlation at each signed lag: lag k>0 → x leads y.
    best_k, best_r = 0, _pearson_r(xs, ys) or 0.0
    for k in range(1, max_lag + 1):
        # x[t-k] vs y[t]
        if n_eff - k >= min_n:
            rk = _pearson_r(xs[:-k], ys[k:])
            if rk is not None and abs(rk) > abs(best_r):
                best_k, best_r = k, rk
        # y[t-k] vs x[t]  → x lags y by k (k negative)
        if n_eff - k >= min_n:
            rk = _pearson_r(xs[k:], ys[:-k])
            if rk is not None and abs(rk) > abs(best_r):
                best_k, best_r = -k, rk

    concurrent_r = _pearson_r(xs, ys) or 0.0
    t_stat = abs(best_r) * math.sqrt((n_eff - 2) / max(1.0 - best_r * best_r, 1e-12)) if abs(best_r) < 1.0 else float("inf")
    p, floor_hit = safe_p_value(t_stat)

    direction = "concurrent"
    if best_k != 0:
        # Only claim precedence when the lagged peak beats the concurrent r by
        # a material margin; otherwise the pair moves together synchronously.
        margin = abs(best_r) - abs(concurrent_r)
        if margin >= 0.05 and p <= Q_THRESHOLD:
            direction = "x_leads_y" if best_k > 0 else "y_leads_x"
        else:
            best_k = 0
            best_r = concurrent_r

    # lag-aligned correlation for reporting (use best lag on raw first-diff data)
    lag_aligned_r = concurrent_r
    if best_k != 0:
        dfx = np.diff(xs)
        dfy = np.diff(ys)
        if best_k > 0:
            lag_aligned_r = _pearson_r(dfx[:-best_k], dfy[best_k:]) or concurrent_r
        else:
            k = -best_k
            lag_aligned_r = _pearson_r(dfx[k:], dfy[:-k]) or concurrent_r

    return {
        "valid": True,
        "direction": direction,
        "optimal_lag_steps": int(best_k),
        "ccf_peak_r": round(float(best_r), 6),
        "p_value": float(p),
        "p_floor_hit": bool(floor_hit),
        "lag_aligned_r": round(float(lag_aligned_r), 6),
        "n_used": int(n_eff),
    }


# ---------------------------------------------------------------------------
# 3. Change-point co-movement
# ---------------------------------------------------------------------------

def _cusum_change_points(series: np.ndarray, min_seg: int = CP_MIN_SEG,
                         max_cp: int = 8) -> List[int]:
    """Binary-segmentation CUSUM change points.

    Recursively finds the index t maximizing |CUSUM|, accepts the split when
    the normalized statistic exceeds ``CP_CUSUM_THRESHOLD * sqrt(n)`` and both
    resulting segments are at least ``min_seg`` long. Cap at ``max_cp`` splits.
    Returns sorted integer positions (indices into ``series``).
    """
    n = len(series)
    if n < 2 * min_seg:
        return []
    out: List[int] = []

    def _scan(lo: int, hi: int, depth: int) -> None:
        if depth >= max_cp or hi - lo < 2 * min_seg:
            return
        seg = series[lo:hi]
        seg = seg - np.nanmean(seg)
        sd = float(np.std(seg))
        if sd == 0.0 or not math.isfinite(sd) or math.isnan(sd):
            return
        z = seg / sd
        cusum = np.cumsum(z)
        k = int(np.argmax(np.abs(cusum)))
        stat = float(abs(cusum[k])) / math.sqrt(len(seg))
        if stat <= CP_CUSUM_THRESHOLD:
            return
        idx = lo + k
        if idx - lo < min_seg or hi - idx < min_seg:
            return
        # Only accept if the split actually reduces within-segment variance
        left, right = seg[:k], seg[k:]
        pooled = float(np.var(left)) + float(np.var(right))
        if pooled >= float(np.var(seg)) * 0.99:  # <1% variance reduction → noise
            return
        out.append(idx)
        _scan(lo, idx, depth + 1)
        _scan(idx, hi, depth + 1)

    _scan(0, n, 0)
    return sorted(out)


def change_point_co_movement(
    df: pd.DataFrame,
    col_a: str,
    col_b: str,
    min_seg: int = CP_MIN_SEG,
) -> dict:
    """Align change-point sets of two columns and score co-movement.

    Returns::

        {valid, cp_a, cp_b, matched, score, flagged, window_steps}

    ``score`` = matched / min(|cp_a|, |cp_b|) (0 when either set is empty).
    ``flagged`` when score ≥ 0.5 and ≥ 2 aligned change points — both series
    shift together in real operating time.
    """
    n = len(df)
    if n < 2 * min_seg:
        return {"valid": False, "cp_a": [], "cp_b": [], "matched": 0,
                "score": 0.0, "flagged": False, "window_steps": 0}

    def _series(col: str) -> np.ndarray:
        return pd.to_numeric(df[col], errors="coerce").to_numpy(dtype=float)

    x, y = _series(col_a), _series(col_b)
    mask = _finite_mask(x, y)
    if int(mask.sum()) < 2 * min_seg:
        return {"valid": False, "cp_a": [], "cp_b": [], "matched": 0,
                "score": 0.0, "flagged": False, "window_steps": 0}
    # Work on the finite mask positions to keep indices meaningful
    idx = np.where(mask)[0]
    cpa = [int(idx[p]) for p in _cusum_change_points(x[mask], min_seg=min_seg)]
    cpb = [int(idx[p]) for p in _cusum_change_points(y[mask], min_seg=min_seg)]

    if not cpa or not cpb:
        return {"valid": True, "cp_a": cpa, "cp_b": cpb, "matched": 0,
                "score": 0.0, "flagged": False, "window_steps": 0}

    window = max(3, int(n * CP_ALIGN_WINDOW_FRACTION))
    smaller, larger = (cpa, cpb) if len(cpa) <= len(cpb) else (cpb, cpa)
    matched = 0
    used: List[int] = []
    for p in smaller:
        for q in larger:
            if q in used:
                continue
            if abs(p - q) <= window:
                matched += 1
                used.append(q)
                break
    score = matched / min(len(cpa), len(cpb))
    # Flag when: (a) ≥2 change points align, or (b) both series have exactly one
    # change point and it aligns perfectly — a single joint regime shift is
    # meaningful co-movement, while a lone chance alignment among many points is not.
    single_shift = matched == 1 and score == 1.0 and len(cpa) == 1 and len(cpb) == 1
    flagged = bool((score >= 0.5 and matched >= 2) or single_shift)
    return {"valid": True, "cp_a": cpa, "cp_b": cpb, "matched": matched,
            "score": round(float(score), 4), "flagged": flagged,
            "window_steps": window}


# ---------------------------------------------------------------------------
# 4. Conditional independence (direct vs indirect)
# ---------------------------------------------------------------------------

def conditional_independence(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    others: Sequence[str],
    min_n: int = MIN_PAIR_N,
) -> dict:
    """Partial correlation of x,y controlling for ``others``.

    * n > p + 2 and p ≤ 40 → full-order ridge precision-matrix estimate.
    * otherwise → stepwise: top-|r| confounders (max 10) residualized in order.

    Returns::

        {partial_r, valid, method, n_controls, n_used}
    """
    cols = [c for c in others if c != x_col and c != y_col and c in df.columns]
    if not cols:
        return {"partial_r": 0.0, "valid": False, "method": "no_controls",
                "n_controls": 0, "n_used": 0}

    X = df[[x_col, y_col] + cols].apply(pd.to_numeric, errors="coerce").to_numpy(dtype=float)
    fm = _finite_mask(X)
    n = int(fm.sum())
    if n < min_n:
        return {"partial_r": 0.0, "valid": False, "method": "insufficient",
                "n_controls": 0, "n_used": 0}
    X = X[fm]
    n_used = n
    p = X.shape[1]

    if n > p + 2 and p <= 42:
        # Standardize
        mu = X.mean(axis=0)
        sd = X.std(axis=0)
        sd[sd == 0] = 1.0
        Z = (X - mu) / sd
        C = np.corrcoef(Z, rowvar=False)
        C = np.nan_to_num(C, nan=0.0)
        lam = 0.01 if n > 10 * p else 0.05
        R = (1.0 - lam) * C + lam * np.eye(p)
        try:
            P = np.linalg.inv(R)
        except np.linalg.LinAlgError:
            P = np.linalg.pinv(R)
        num = -P[0, 1]
        den = math.sqrt(float(P[0, 0]) * float(P[1, 1]))
        if den == 0.0:
            return {"partial_r": 0.0, "valid": False, "method": "full_order_ridge",
                    "n_controls": p - 2, "n_used": n_used}
        return {"partial_r": round(float(num / den), 6), "valid": True,
                "method": "full_order_ridge", "n_controls": p - 2, "n_used": n_used}

    # Stepwise fallback: residualize on the strongest k confounders
    k = min(10, max(1, (n - 5) // 2))
    z = (X - X.mean(axis=0)) / np.maximum(X.std(axis=0), 1e-12)
    rx = np.corrcoef(z, rowvar=False)[0, 2:]
    ry = np.corrcoef(z, rowvar=False)[1, 2:]
    scores = np.maximum(np.abs(rx), np.abs(ry))
    top = np.argsort(scores)[::-1][:k]

    cx = z[:, 0].copy()
    cy = z[:, 1].copy()
    for j in top:
        c = z[:, 2 + j]
        c = c - c.mean()
        var_c = float(c @ c)
        if var_c <= 1e-12:
            continue
        bx = float(cx @ c) / var_c
        by = float(cy @ c) / var_c
        cx = cx - bx * c
        cy = cy - by * c
    partial_r = _pearson_r(cx, cy)
    if partial_r is None:
        return {"partial_r": 0.0, "valid": False, "method": "stepwise_topk",
                "n_controls": len(top), "n_used": n_used}
    return {"partial_r": round(float(partial_r), 6), "valid": True,
            "method": "stepwise_topk", "n_controls": int(len(top)), "n_used": n_used}


# ---------------------------------------------------------------------------
# 5. Leverage / outlier stability
# ---------------------------------------------------------------------------

def leverage_stability(x: np.ndarray, y: np.ndarray) -> dict:
    """Vectorized leave-one-out Pearson stability.

    Returns::

        {valid, loo_min, loo_max, stability, sign_flip, max_influence_index,
         flagged, n}

    ``stability = 1 - (loo_max - loo_min) / 2``. Flagged when the LOO range
    exceeds ``LOO_FLAG_RANGE`` or dropping a single row flips the sign.
    """
    n = len(x)
    if n < 10:
        return {"valid": False, "loo_min": 0.0, "loo_max": 0.0, "stability": 0.0,
                "sign_flip": False, "max_influence_index": -1, "flagged": False, "n": n}
    Sx = float(x.sum())
    Sy = float(y.sum())
    Sxx = float(x @ x)
    Syy = float(y @ y)
    Sxy = float(x @ y)

    # Leave-one-out sums (vectorized)
    n1 = n - 1
    sx_i = Sx - x
    sy_i = Sy - y
    sxy_i = Sxy - x * y
    sxx_i = Sxx - x * x
    syy_i = Syy - y * y

    num = sxy_i - sx_i * sy_i / n1
    den = np.sqrt(np.maximum(sxx_i - sx_i ** 2 / n1, 0.0) *
                  np.maximum(syy_i - sy_i ** 2 / n1, 0.0))
    with np.errstate(divide="ignore", invalid="ignore"):
        r_loo = np.where(den > 1e-12, num / np.maximum(den, 1e-12), np.nan)
    finite = np.isfinite(r_loo)
    if not finite.any():
        return {"valid": False, "loo_min": 0.0, "loo_max": 0.0, "stability": 0.0,
                "sign_flip": False, "max_influence_index": -1, "flagged": False, "n": n}
    loo_min = float(np.min(r_loo[finite]))
    loo_max = float(np.max(r_loo[finite]))
    stability = 1.0 - (loo_max - loo_min) / 2.0
    base_r = _pearson_r(x, y) or 0.0
    sign_flip = bool(loo_min < 0 < loo_max and abs(base_r) > 0.05)
    flagged = bool((loo_max - loo_min) > LOO_FLAG_RANGE or sign_flip)
    idx = int(np.argmax(np.abs(r_loo - base_r))) if finite.any() else -1
    return {"valid": True, "loo_min": round(loo_min, 6), "loo_max": round(loo_max, 6),
            "stability": round(stability, 6), "sign_flip": sign_flip,
            "max_influence_index": int(idx), "flagged": flagged, "n": int(n)}


# ---------------------------------------------------------------------------
# 6. Moderator / interaction check
# ---------------------------------------------------------------------------

def moderator_check(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    partition_col: Optional[str],
    per_partition_r: Sequence[float],
    partition_name: str = "",
) -> dict:
    """Detect interaction between the x→y association and a partition.

    Returns::

        {moderator, n_partitions, per_partition_r, sign_divergence,
         magnitude_divergence, flagged, valid}

    Flagged when ≥2 partitions with usable r disagree in sign, or diverge in
    magnitude by more than ``MIN_ABS_R`` (0.3).
    """
    rs = [float(v) for v in per_partition_r if v is not None]
    if len(rs) < 2 or not partition_col:
        return {"moderator": partition_col or "", "n_partitions": len(rs),
                "per_partition_r": [round(v, 6) for v in rs],
                "sign_divergence": False, "magnitude_divergence": False,
                "flagged": False, "valid": False}
    signs = {1 if v > 0 else -1 for v in rs if abs(v) > 1e-9}
    sign_div = len(signs) > 1
    mag_div = (max(rs) - min(rs)) > MIN_ABS_R
    return {"moderator": partition_col, "n_partitions": len(rs),
            "per_partition_r": [round(v, 6) for v in rs],
            "sign_divergence": bool(sign_div),
            "magnitude_divergence": bool(mag_div),
            "flagged": bool(sign_div or mag_div), "valid": True}


# ---------------------------------------------------------------------------
# 7. Mediation scan
# ---------------------------------------------------------------------------

def mediation_scan(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    all_cols: Sequence[str],
    global_r: float,
    partial_full: float,
    partial_full_valid: bool,
    min_n: int = MIN_PAIR_N,
) -> dict:
    """Screen for mediator channels X → M → Y.

    Only meaningful when the global association is strong but conditioning on
    everything collapses it (|partial_full| small). Returns the top candidate
    channel and its conditioning evidence::

        {valid, candidates: [{mediator, r_xm, r_my, product, partial_xy_given_m}]}
    """
    if abs(global_r) < MIN_ABS_R:
        return {"valid": False, "candidates": []}
    indirect_evidence = partial_full_valid and abs(partial_full) < INDIRECT_MAX_PARTIAL
    if not indirect_evidence:
        return {"valid": False, "candidates": []}

    x = pd.to_numeric(df[x_col], errors="coerce").to_numpy(dtype=float)
    y = pd.to_numeric(df[y_col], errors="coerce").to_numpy(dtype=float)
    cands: List[dict] = []
    for m in all_cols:
        if m in (x_col, y_col):
            continue
        mvals = pd.to_numeric(df[m], errors="coerce").to_numpy(dtype=float)
        mask = _finite_mask(x, y, mvals)
        if int(mask.sum()) < min_n:
            continue
        r_xm = _pearson_r(x[mask], mvals[mask])
        r_my = _pearson_r(mvals[mask], y[mask])
        if r_xm is None or r_my is None:
            continue
        if abs(r_xm) < MEDIATOR_MIN_R or abs(r_my) < MEDIATOR_MIN_R:
            continue
        # Partial x,y given m alone — does conditioning on m kill the link?
        z = np.column_stack([x[mask], y[mask], mvals[mask]])
        z = (z - z.mean(axis=0)) / np.maximum(z.std(axis=0), 1e-12)
        m_c = z[:, 2] - z[:, 2].mean()
        var_m = float(m_c @ m_c)
        if var_m <= 1e-12:
            continue
        cx = z[:, 0] - (float(z[:, 0] @ m_c) / var_m) * m_c
        cy = z[:, 1] - (float(z[:, 1] @ m_c) / var_m) * m_c
        pr = _pearson_r(cx, cy)
        if pr is None:
            continue
        cands.append({
            "mediator": m,
            "r_xm": round(float(r_xm), 6),
            "r_my": round(float(r_my), 6),
            "product": round(float(r_xm * r_my), 6),
            "partial_x_y_given_m": round(float(pr), 6),
        })
    cands.sort(key=lambda d: abs(d["product"]), reverse=True)
    return {"valid": bool(cands), "candidates": cands[:3]}


# ---------------------------------------------------------------------------
# 8. Causality ceiling synthesis
# ---------------------------------------------------------------------------

def causality_ceiling(
    temporal: dict,
    partial_full: dict,
    ontology_rel: Optional[dict],
    global_r: float,
    n_eff: int,
) -> dict:
    """Synthesize the strongest defensible causal claim for a pair.

    Returns::

        {ceiling, ontology_contradiction, rationale}

    Levels (weakest → strongest): insufficient_evidence, contemporaneous_
    correlation, temporal_precedence, conditional_independence_supported,
    ontology_consistent.
    """
    n_ok = n_eff >= MIN_PAIR_N
    sig_r = abs(global_r) >= MIN_ABS_R

    if not n_ok or not sig_r:
        return {"ceiling": "insufficient_evidence", "ontology_contradiction": False,
                "rationale": f"n={n_eff}, |r|={abs(global_r):.3f} below evidence thresholds"}

    ceiling = "contemporaneous_correlation"
    rationale = "contemporaneous correlation with significant |r|; no temporal or structural evidence"

    if temporal.get("valid") and temporal.get("direction") in ("x_leads_y", "y_leads_x") \
            and temporal.get("p_value", 1.0) <= Q_THRESHOLD:
        ceiling = "temporal_precedence"
        rationale = (f"lag-CCF precedence ({temporal['direction']}, lag="
                     f"{temporal['optimal_lag_steps']}, p={temporal['p_value']:.2e})")

    if partial_full.get("valid") and abs(partial_full.get("partial_r", 0.0)) >= DIRECT_MIN_PARTIAL \
            and (partial_full["partial_r"] > 0) == (global_r > 0):
        ceiling = "conditional_independence_supported"
        rationale = (f"association survives conditioning on all other variables "
                     f"(partial_r={partial_full['partial_r']:.3f})" +
                     (f"; {rationale}" if ceiling != "contemporaneous_correlation" else ""))

    onto_contradiction = False
    if ontology_rel is not None and ontology_rel.get("data_direction_validated") == "true":
        pred_sign = 1 if float(ontology_rel.get("predicted_direction_sign", 0) or 0) >= 0 else -1
        # Only when ontology explicitly states a sign can we test contradiction
        if "predicted_direction_sign" in ontology_rel:
            data_sign = 1 if global_r >= 0 else -1
            onto_contradiction = pred_sign != data_sign
        if not onto_contradiction:
            ceiling = "ontology_consistent"
            rationale = (f"consistent with ontology-validated direction; {rationale}")

    return {"ceiling": ceiling, "ontology_contradiction": onto_contradiction,
            "rationale": rationale}


# ---------------------------------------------------------------------------
# 9. Association graph assembly
# ---------------------------------------------------------------------------

def build_association_graph(
    df: pd.DataFrame,
    numeric_cols: Sequence[str],
    ontology: dict,
    selection: dict,
    relationships: Sequence[dict],
    pairwise: Optional[Sequence[dict]] = None,
    time_col: Optional[str] = None,
) -> dict:
    """Assemble the final association network.

    Nodes = every analyzed numeric column (role/unit from ontology).
    Edges = significant associations (|r| ≥ MIN_ABS_R and q ≤ Q_THRESHOLD and
    n ≥ MIN_PAIR_N) with full inference evidence. When the same unordered pair
    appears in ``relationships`` (ontology/tier-driven), its richer per-pair
    record (partial, temporal, etc.) is merged; otherwise the pair's evidence
    comes from the exhaustive ``pairwise`` scan plus freshly computed temporal
    and partial tests.
    """
    tvals = None
    if time_col and time_col in df.columns:
        try:
            tvals = pd.to_datetime(df[time_col]).astype("int64").to_numpy(dtype=float)
        except Exception:
            tvals = df[time_col].to_numpy(dtype=float)

    # Node metadata
    signal_idx: Dict[str, dict] = {}
    for section in ["inspection_signals", "process_parameters", "control_variables"]:
        for sig in ontology.get("signals", {}).get(section, []):
            signal_idx[sig.get("column", "")] = sig
    onto_units = ontology.get("metadata", {}).get("units", {})
    roles = {}
    for c in numeric_cols:
        sig = signal_idx.get(c, {})
        roles[c] = sig.get("role", "")

    # Rich records from conditional_analysis (predictor→target oriented)
    rich: Dict[Tuple[str, str], dict] = {}
    for rel in relationships:
        rich[(rel.get("predictor", ""), rel.get("target", ""))] = rel

    pair_records: List[dict] = []
    if pairwise:
        for rec in pairwise:
            a, b = rec["predictor"], rec["target"]
            for (p, t) in ((a, b), (b, a)):
                if (p, t) in rich:
                    rec = {**rec, **rich[(p, t)]}
                    break
            pair_records.append(rec)
    else:
        for (p, t), rel in rich.items():
            pair_records.append({"predictor": p, "target": t, "r": rel.get("global", 0.0),
                                 "q_value": rel.get("q_value", 1.0), "n": rel.get("n_effective", 0),
                                 **rel})

    onto_rel_idx: Dict[Tuple[str, str], dict] = {}
    for r in ontology.get("relationships", []):
        onto_rel_idx[(r.get("from", ""), r.get("to", ""))] = r
        onto_rel_idx[(r.get("to", ""), r.get("from", ""))] = r

    nodes: List[dict] = []
    edges: List[dict] = []
    seen_nodes: Dict[str, bool] = {}

    for rec in pair_records:
        p = rec.get("predictor", "")
        t = rec.get("target", "")
        r_val = float(rec.get("r", rec.get("global", 0.0)))
        q_val = float(rec.get("q_value", 1.0))
        n_val = int(rec.get("n", rec.get("n_effective", 0)))
        if abs(r_val) < MIN_ABS_R or q_val > Q_THRESHOLD or n_val < MIN_PAIR_N:
            continue

        # Orientation: prefer temporal precedence when available
        tc = rec.get("temporal", {})
        direction = tc.get("direction", "concurrent") if tc else "concurrent"
        if direction == "y_leads_x":
            p, t = t, p
            r_val = -r_val  # keep the edge sign consistent with (p→t) orientation
            tc_dir = "x_leads_y"
        elif direction == "x_leads_y":
            tc_dir = "x_leads_y"
        else:
            tc_dir = "concurrent"

        for col in (p, t):
            if col not in seen_nodes:
                seen_nodes[col] = True
                sig = signal_idx.get(col, {})
                nodes.append({
                    "id": col,
                    "label": sig.get("label", col),
                    "role": roles.get(col, sig.get("role", "unknown")),
                    "unit": onto_units.get(col, sig.get("unit", "")),
                    "controlled_by": sig.get("controlled_by", ""),
                })

        onto_rel = onto_rel_idx.get((p, t))
        ceiling_info = rec.get("causality_ceiling")
        if isinstance(ceiling_info, str):
            # Rich relationship record stores the ceiling level as a plain string
            # plus a separate contradiction flag — normalize to the dict shape.
            ceiling_info = {
                "ceiling": ceiling_info,
                "ontology_contradiction": bool(rec.get("ontology_contradiction", False)),
                "rationale": "",
            }
        if not ceiling_info:
            ceiling_info = causality_ceiling(
                tc, rec.get("partial_full", {}), onto_rel, r_val, n_val)

        relationship = "supports" if r_val >= 0 else "inhibits"
        if ceiling_info.get("ontology_contradiction"):
            relationship = "contradicts"

        edges.append({
            "source": p,
            "target": t,
            "relationship": relationship,
            "strength": round(r_val, 6),
            "sign": 1 if r_val >= 0 else -1,
            "confidence": round(float(rec.get("confidence",
                                               _edge_confidence(rec))), 4),
            "causal_ceiling": ceiling_info.get("ceiling", "contemporaneous_correlation"),
            "ontology_contradiction": bool(ceiling_info.get("ontology_contradiction", False)),
            "statistical_evidence": {
                "global_r": round(r_val, 6),
                "p_value": float(rec.get("p_value", 1.0)),
                "p_floor_hit": bool(rec.get("p_floor_hit", False)),
                "q_value": round(q_val, 6),
                "n_effective": n_val,
                "partial_r": float((rec.get("partial_full") or {}).get("partial_r", 0.0)),
                "partial_method": (rec.get("partial_full") or {}).get("method", ""),
                "temporal_direction": tc_dir,
                "optimal_lag_steps": int(tc.get("optimal_lag_steps", 0)),
                "ccf_peak_r": float(tc.get("ccf_peak_r", 0.0)),
                "lag_aligned_r": float(rec.get("lag_aligned", 0.0)),
                "direct_association": bool(rec.get("direct_association", False)),
                "indirect_association": bool(rec.get("indirect_association", False)),
                "mediator_candidates": [
                    m.get("mediator", "") for m in rec.get("mediator_candidates", [])
                ],
                "change_point_co_movement": float((rec.get("change_point_co_movement") or {}).get("score", 0.0)),
                "loo_stability": float((rec.get("loo_stability") or {}).get("stability", 0.0)),
                "interaction_flagged": bool((rec.get("interaction") or {}).get("flagged", False)),
            },
            "evidence_ref": [
                f"deep_data_analysis.json#{p}->{t}",
                f"association_graph.json#{p}->{t}",
            ],
        })

    return {
        "run_id": "enhancement-association-graph",
        "n_nodes": len(nodes),
        "n_edges": len(edges),
        "nodes": nodes,
        "edges": edges,
        "metadata": {
            "min_abs_r": MIN_ABS_R,
            "q_threshold": Q_THRESHOLD,
            "min_pair_n": MIN_PAIR_N,
            "ccf_max_lag_abs": CCF_MAX_LAG_ABS,
            "cp_min_seg": CP_MIN_SEG,
            "generated_at": None,  # filled by caller if needed
        },
    }


def _edge_confidence(rec: dict) -> float:
    """0..1 confidence = combination of significance, LOO stability and
    conditional-independence consistency."""
    q = float(rec.get("q_value", 1.0))
    stability = float((rec.get("loo_stability") or {}).get("stability", 0.0))
    partial_full = (rec.get("partial_full") or {}).get("valid", False)
    score = 0.3
    if q <= Q_THRESHOLD:
        score += 0.3
    if stability > 0.8:
        score += 0.2
    elif stability > 0.5:
        score += 0.1
    if partial_full:
        score += 0.2
    return min(score, 1.0)


# ---------------------------------------------------------------------------
# CLI (used by E3.5 stage of the enhancement pipeline)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    import json
    import sys
    from pathlib import Path

    ap = argparse.ArgumentParser(description="E3.5: Association graph builder")
    ap.add_argument("--run-dir", required=True, help="Path to diagnostic RUN_DIR")
    ap.add_argument("--output", default=None, help="Output JSON path")
    args = ap.parse_args()

    run_dir = Path(args.run_dir)
    if not run_dir.is_dir():
        print(f"ERROR: run-dir does not exist: {run_dir}", file=sys.stderr)
        sys.exit(1)

    out_path = Path(args.output) if args.output else run_dir / "enhancement" / "association_graph.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    def _load(p: Path) -> dict:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)

    ontology = _load(run_dir / "01_ontology" / "ontology.json")
    selection = _load(run_dir / "02_processed" / "analysis_parameter_selection.json")
    deep_path = run_dir / "enhancement" / "deep_data_analysis.json"
    relationships = _load(deep_path).get("relationships", []) if deep_path.is_file() else []

    csv = run_dir / "enhancement" / "derived_data.csv"
    if not csv.is_file():
        csv = run_dir / "02_processed" / "cleaned_data.csv"
    df = pd.read_csv(csv)

    # Numeric columns: exclude metadata/stratification/one-hot/derived-deviation noise
    meta = set(selection.get("metadata_cols", []) or [])
    exclude = {c for c in df.columns if c.lower() in
               ("timestamp", "time", "datetime", "date", "time_hours") or c.lower().startswith("ts_")}
    exclude |= meta
    exclude |= {c for c in df.columns if c.endswith("_dev") or c.startswith("regime_")}
    numeric_cols = [c for c in df.columns
                    if c not in exclude and pd.to_numeric(df[c], errors="coerce").nunique(dropna=True) > 1]

    pairwise = pairwise_scan(df, numeric_cols)
    graph = build_association_graph(df, numeric_cols, ontology, selection,
                                    relationships, pairwise)
    graph["metadata"]["generated_at"] = ""

    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(graph, fh, indent=2, ensure_ascii=False, default=str)
    print(f"[association_graph_builder] {len(graph['nodes'])} nodes, "
          f"{len(graph['edges'])} edges → {out_path}")
