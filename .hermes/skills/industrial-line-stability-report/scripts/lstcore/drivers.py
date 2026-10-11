"""Cross-parameter driver analysis: lag-compensated correlation + contribution."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

DEFAULT_MAX_LAG = 10
MIN_OVERLAP = 20


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
    best = {"best_abs_r": 0.0, "best_lag_rows": 0, "leader": "none"}
    pearson_at_best = spearman_at_best = None
    for lag in range(0, cap + 1):
        if lag == 0:
            oriented = [("none", a, b)]
        elif both_directions:
            oriented = [("a", a[:-lag], b[lag:]),   # a leads b by `lag` rows
                        ("b", b[:-lag], a[lag:])]   # b leads a by `lag` rows
        else:
            oriented = [("a", a[:-lag], b[lag:])]
        for leader, x, y in oriented:
            mask = ~(np.isnan(x) | np.isnan(y))
            xs, ys = x[mask], y[mask]
            if len(xs) < MIN_OVERLAP:
                continue
            r_sp = float(stats.spearmanr(xs, ys).statistic)
            if not np.isfinite(r_sp):
                continue
            if abs(r_sp) > abs(best["best_abs_r"]):
                r_pe = (float(stats.pearsonr(xs, ys).statistic)
                        if np.std(xs) > 0 and np.std(ys) > 0 else None)
                best = {"best_abs_r": round(abs(r_sp), 6),
                        "best_lag_rows": lag, "leader": leader}
                spearman_at_best = round(r_sp, 6)
                pearson_at_best = (round(r_pe, 6)
                                   if r_pe is not None and np.isfinite(r_pe) else None)
    lag0 = _lag0(a, b)
    return {
        "pearson": lag0["pearson"],
        "spearman": lag0["spearman"],
        "best_abs_r": best["best_abs_r"],
        "best_lag_rows": best["best_lag_rows"],
        "leader": best["leader"],
        **({"pearson_at_best": pearson_at_best, "spearman_at_best": spearman_at_best}),
    }


def _lag0(a: np.ndarray, b: np.ndarray) -> dict:
    mask = ~(np.isnan(a) | np.isnan(b))
    x, y = a[mask], b[mask]
    if len(x) < MIN_OVERLAP or np.std(x) == 0 or np.std(y) == 0:
        return {"pearson": None, "spearman": None}
    r_pe = float(stats.pearsonr(x, y).statistic)
    r_sp = float(stats.spearmanr(x, y).statistic)
    return {
        "pearson": round(r_pe, 6) if np.isfinite(r_pe) else None,
        "spearman": round(r_sp, 6) if np.isfinite(r_sp) else None,
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
