"""Cross-parameter driver analysis: lag-compensated correlation + contribution.

Performance contract (identical outputs to the scipy reference): Spearman per
lag is Pearson of average ranks computed ON THAT LAG'S SLICE (subset ranks
must be recomputed — dropping rows shifts other members' ranks, so global
ranks cannot be reused across lags). Compared with calling scipy.spearmanr
per slice (~510µs of per-call overhead, 39k calls dominated a 61-param run at
~24 s), the pandas-rank + centered-Pearson form computes the same values at a
fraction of the cost.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

DEFAULT_MAX_LAG = 10
MIN_OVERLAP = 20


def _pearson(xs: np.ndarray, ys: np.ndarray) -> float | None:
    """Centered Pearson correlation; None when undefined (< overlap / zero var)."""
    n = xs.size
    if n < MIN_OVERLAP:
        return None
    xm = xs - xs.mean()
    ym = ys - ys.mean()
    denom = float(np.sqrt((xm @ xm) * (ym @ ym)))
    if not np.isfinite(denom) or denom <= 0:
        return None
    r = float((xm @ ym) / denom)
    return r if np.isfinite(r) else None


def _avg_ranks(v: np.ndarray) -> np.ndarray:
    """Average-tie ranks on the given values (equals scipy rankdata('average'))."""
    return pd.Series(v).rank(method="average").to_numpy(dtype=float)


def _pair_corr(a: np.ndarray, b: np.ndarray, max_lag: int,
               both_directions: bool = True) -> dict:
    """Best |Spearman| over lags 0..max_lag.

    both_directions=True (pair discovery): search a-leads-b AND b-leads-a so
    the reported leader never depends on column order. False (contribution
    analysis): only the driver-leads-target orientation counts, otherwise a
    target that drives the "driver" would inflate the driver's variance share.
    lag0 is direction-symmetric; leader token is "a" | "b" | "none".
    """
    n = len(a)
    cap = min(max_lag, max(0, n - MIN_OVERLAP))
    a_nan = bool(np.isnan(a).any())
    b_nan = bool(np.isnan(b).any())
    best = {"best_abs_r": 0.0, "best_lag_rows": 0, "leader": "none"}
    best_at = (None, None)  # raw values at the best slice, for pearson_at_best
    spearman_at_best = None

    def consider(token, lag, xs, ys):
        nonlocal best, best_at, spearman_at_best
        if xs.size < MIN_OVERLAP:
            return
        r = _pearson(_avg_ranks(xs), _avg_ranks(ys))
        if r is None:
            return
        if abs(r) > abs(best["best_abs_r"]):
            best = {"best_abs_r": round(abs(r), 6),
                    "best_lag_rows": lag, "leader": token}
            spearman_at_best = round(r, 6)
            best_at = (xs, ys)

    def valid(x_raw, y_raw):
        if a_nan or b_nan:
            m = ~(np.isnan(x_raw) | np.isnan(y_raw))
            return x_raw[m], y_raw[m]
        return x_raw, y_raw

    # lag0（方向对称；完整重叠）
    xs, ys = valid(a, b)
    consider("none", 0, xs, ys)
    for lag in range(1, cap + 1):
        oriented = [("a", a[:-lag], b[lag:])]
        if both_directions:
            oriented.append(("b", b[:-lag], a[lag:]))
        for token, xa, ya in oriented:
            xs, ys = valid(xa, ya)
            consider(token, lag, xs, ys)

    lag0 = _lag0(a, b)
    pearson_at_best = (_pearson(*best_at) if best_at[0] is not None else None)
    return {
        "pearson": lag0["pearson"],
        "spearman": lag0["spearman"],
        "best_abs_r": best["best_abs_r"],
        "best_lag_rows": best["best_lag_rows"],
        "leader": best["leader"],
        "pearson_at_best": (round(pearson_at_best, 6)
                            if pearson_at_best is not None
                            and np.isfinite(pearson_at_best) else None),
        "spearman_at_best": spearman_at_best,
    }


def _lag0(a: np.ndarray, b: np.ndarray) -> dict:
    mask = ~(np.isnan(a) | np.isnan(b))
    x, y = a[mask], b[mask]
    if len(x) < MIN_OVERLAP:
        return {"pearson": None, "spearman": None}
    r_pe = _pearson(x, y)
    r_sp = _pearson(_avg_ranks(x), _avg_ranks(y))
    return {
        "pearson": round(r_pe, 6) if r_pe is not None and np.isfinite(r_pe) else None,
        "spearman": round(r_sp, 6) if r_sp is not None and np.isfinite(r_sp) else None,
    }


def pair_analysis(df: pd.DataFrame, cols: list[str], max_lag: int = DEFAULT_MAX_LAG,
                  top_k: int = 10) -> list[dict]:
    """Correlate all column pairs; return the top_k pairs by |best_abs_r|."""
    arrays = {c: pd.to_numeric(df[c], errors="coerce").to_numpy(dtype=float) for c in cols}
    pairs = []
    for i, a in enumerate(cols):
        for b in cols[i + 1:]:
            res = _pair_corr(arrays[a], arrays[b], max_lag, both_directions=True)
            if res["best_abs_r"] is None:
                continue
            res["a"], res["b"], res["n"] = a, b, int(len(arrays[a]))
            res["leader"] = {"a": a, "b": b}.get(res["leader"])  # None ⇒ lag0 best
            pairs.append(res)
    pairs.sort(key=lambda p: abs(p["best_abs_r"]), reverse=True)
    return pairs[:top_k]


def contribution_analysis(df: pd.DataFrame, drivers: list[str], targets: list[str],
                          min_abs_r: float = 0.3) -> list[dict]:
    """Variance share of each driver per target from lag-compensated |r|².

    Uses the same lag-compensated Spearman as pair_analysis (house principle:
    lag-compensated CCF), so a driver that leads the target by k rows still
    gets credited; shares are normalized within each target.
    """
    arrays = {c: pd.to_numeric(df[c], errors="coerce").to_numpy(dtype=float)
              for c in set(drivers) | set(targets)}
    out = []
    for target in targets:
        if target not in arrays:
            continue
        rows = []
        for d in drivers:
            if d == target or d not in arrays:
                continue
            res = _pair_corr(arrays[d], arrays[target], DEFAULT_MAX_LAG,
                             both_directions=False)
            if res["best_abs_r"] >= min_abs_r:
                rows.append({"driver": d, "target": target,
                             "abs_r": res["best_abs_r"],
                             "best_lag_rows": res["best_lag_rows"],
                             "share_raw": res["best_abs_r"] ** 2})
        total = sum(r["share_raw"] for r in rows)
        if total > 0:
            for r in rows:
                r["share"] = round(r["share_raw"] / total, 6)
                del r["share_raw"]
            rows.sort(key=lambda r: r["share"], reverse=True)
            out.extend(rows)
    return out
