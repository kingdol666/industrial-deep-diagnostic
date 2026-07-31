"""Focused numpy/pandas statistical utilities for industrial deep-analysis.

Pure numerical helpers used by later deep-analysis tasks. Only depends on the
Python standard library plus numpy and pandas (already declared by the
processor). No scipy / statsmodels / sklearn / external services.

All public functions are robust to empty / constant / degenerate input and
return explicit status fields / ``None`` markers instead of propagating NaN.

Conventions
-----------
* Predictors are centered for numerical conditioning; ``ols_centered`` reports
  the intercept at the predictor-mean origin (centered intercept) and the slopes
  are invariant to centering.
* Two-sided p-values use the standard-normal approximation via ``math.erf``.
* The block bootstrap resamples whole group blocks (never iid rows).
"""

from __future__ import annotations

import math
from typing import Any, Callable, Iterable, List, Optional, Sequence, Union

import numpy as np
import pandas as pd

__all__ = [
    "ols_centered",
    "slope_at_current",
    "partial_correlation",
    "block_bootstrap_ci",
    "benjamini_hochberg",
    "durbin_watson",
    "stationarity_check",
    "support_domain",
]


# --------------------------------------------------------------------------- #
# Internal helpers
# --------------------------------------------------------------------------- #
def _to_float_array(x: Any) -> np.ndarray:
    """Coerce any 1-D compatible input to a 1-D float64 numpy array.

    pandas objects pass through ``pd.to_numeric`` so that parseable strings are
    converted and genuinely un-parseable entries become NaN (later dropped).
    """
    if isinstance(x, pd.Series):
        arr = pd.to_numeric(x, errors="coerce").to_numpy(dtype=float)
    elif isinstance(x, pd.DataFrame):
        arr = x.to_numpy(dtype=float).reshape(-1)
    else:
        arr = np.asarray(x, dtype=float).reshape(-1)
    return np.asarray(arr, dtype=float)


def _to_matrix(X: Any) -> "tuple[np.ndarray, List[str]]":
    """Coerce predictors to a 2-D float64 matrix and remember caller column order."""
    if isinstance(X, pd.DataFrame):
        cols = [str(c) for c in X.columns]
        mat = X.to_numpy(dtype=float)
        if mat.ndim == 1:
            mat = mat.reshape(-1, 1)
        return np.asarray(mat, dtype=float), cols
    if isinstance(X, pd.Series):
        name = X.name if X.name is not None else "x1"
        return X.to_numpy(dtype=float).reshape(-1, 1), [str(name)]
    arr = np.asarray(X, dtype=float)
    if arr.ndim == 1:
        return arr.reshape(-1, 1), ["x1"]
    if arr.ndim != 2:
        raise ValueError("X must be 1-D or 2-D")
    return arr, [f"x{i + 1}" for i in range(arr.shape[1])]


def _finite_mask(*arrays: np.ndarray) -> np.ndarray:
    """Row-wise finite mask across all arrays of equal first-dimension length."""
    n = arrays[0].shape[0]
    mask = np.ones(n, dtype=bool)
    for a in arrays:
        if a.ndim == 1:
            mask &= np.isfinite(a)
        else:
            mask &= np.all(np.isfinite(a), axis=1)
    return mask


def _normal_cdf(z: float) -> float:
    """Standard normal CDF via ``math.erf``."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def _two_sided_normal_p(z: float) -> float:
    """Two-sided tail probability of a standard-normal statistic."""
    if not math.isfinite(z):
        return 0.0 if math.isinf(z) else float("nan")
    return 2.0 * (1.0 - _normal_cdf(abs(z)))


def _pearson_r(a: np.ndarray, b: np.ndarray) -> Optional[float]:
    """Pearson correlation between two centered finite arrays, or ``None`` if degenerate."""
    am = a - a.mean()
    bm = b - b.mean()
    denom = math.sqrt(float(am @ am) * float(bm @ bm))
    if denom == 0.0:
        return None
    return float((am @ bm) / denom)


# --------------------------------------------------------------------------- #
# 1. OLS (centered design, pinv-based, robust to collinearity)
# --------------------------------------------------------------------------- #
def ols_centered(X, y):
    """Ordinary least squares with an intercept on a centered design matrix.

    Parameters
    ----------
    X : array-like, pandas.DataFrame or pandas.Series
        Predictors. A 1-D array / Series is treated as a single predictor.
        Caller column order is preserved.
    y : array-like or pandas.Series
        Response, 1-D.

    Returns
    -------
    dict with keys ``beta``, ``se``, ``t``, ``p``, ``r2``, ``resid``, ``n``,
    ``rank``, ``columns`` (plus an informative ``status``). ``beta[0]`` is the
    centered intercept (prediction at the predictor means); the remaining
    entries are slopes. P-values use a two-sided normal approximation
    (``math.erf``). ``se`` / ``t`` / ``p`` are ``None`` for degenerate input
    (empty, constant response, or insufficient residual degrees of freedom).
    """
    Xmat, cols = _to_matrix(X)
    yvec = _to_float_array(y)
    col_labels = ["intercept"] + cols

    if Xmat.shape[0] != yvec.shape[0]:
        raise ValueError("X and y have mismatched row counts")

    mask = _finite_mask(Xmat, yvec)
    Xmat = Xmat[mask]
    yvec = yvec[mask]
    n = int(Xmat.shape[0])

    if n == 0:
        return {
            "beta": np.array([]),
            "se": None,
            "t": None,
            "p": None,
            "r2": None,
            "resid": np.array([]),
            "n": 0,
            "rank": 0,
            "columns": col_labels,
            "status": "empty",
        }

    # Center predictors for conditioning; intercept absorbs the means.
    means = Xmat.mean(axis=0)
    Xc = Xmat - means
    D = np.column_stack([np.ones(n), Xc])

    pinv_D = np.linalg.pinv(D)
    beta = pinv_D @ yvec
    rank = int(np.linalg.matrix_rank(D))
    fitted = D @ beta
    resid = yvec - fitted
    ssr = float(resid @ resid)
    ybar = float(yvec.mean())
    sst = float((yvec - ybar) @ (yvec - ybar))

    if sst == 0.0:
        # Constant response: slopes collapse to zero, no variance to explain.
        return {
            "beta": beta,
            "se": None,
            "t": None,
            "p": None,
            "r2": None,
            "resid": resid,
            "n": n,
            "rank": rank,
            "columns": col_labels,
            "status": "constant_response",
        }

    r2 = 1.0 - ssr / sst
    df = n - rank
    if df <= 0:
        return {
            "beta": beta,
            "se": None,
            "t": None,
            "p": None,
            "r2": r2,
            "resid": resid,
            "n": n,
            "rank": rank,
            "columns": col_labels,
            "status": "insufficient_dof",
        }
    # ---- Rank-deficiency gate: individual coefficients not uniquely identifiable.
    n_cols = len(col_labels)
    if rank < n_cols:
        return {
            "beta": beta,
            "se": None,
            "t": None,
            "p": None,
            "r2": r2,
            "resid": resid,
            "n": n,
            "rank": rank,
            "columns": col_labels,
            "status": "rank_deficient",
        }

    # ---- Well-conditioned: compute se / t / p.
    sigma2 = ssr / df
    # Covariance via pinv(X'X): stable under (near) collinearity.
    cov = sigma2 * np.linalg.pinv(D.T @ D)
    var_diag = np.maximum(np.diag(cov), 0.0)
    se = np.sqrt(var_diag)
    with np.errstate(divide="ignore", invalid="ignore"):
        t_stat = np.where(se > 0, beta / se, np.nan)
    p_vals = np.array([_two_sided_normal_p(float(t)) if math.isfinite(float(t)) else None
                       for t in t_stat])

    return {
        "beta": beta,
        "se": se,
        "t": t_stat,
        "p": p_vals,
        "r2": r2,
        "resid": resid,
        "n": n,
        "rank": rank,
        "columns": col_labels,
        "status": "ok",
    }


# --------------------------------------------------------------------------- #
# 2. Current-point derivative from a centered quadratic fit
# --------------------------------------------------------------------------- #
def slope_at_current(x, y, x0):
    """Local linear slope evaluated at ``x0`` via a centered quadratic fit.

    Fits ``y ~ 1 + (x - x_mean) + (x - x_mean)^2`` and returns the derivative
    at ``x0`` as ``beta_linear + 2 * beta_quadratic * (x0 - x_mean)`` — i.e. the
    tangent of the quadratic, not the raw linear coefficient.

    Returns ``status="insufficient_data"`` when fewer than 3 valid rows remain.
    """
    xvec = _to_float_array(x)
    yvec = _to_float_array(y)
    if xvec.shape[0] != yvec.shape[0]:
        raise ValueError("x and y have mismatched lengths")

    mask = _finite_mask(xvec.reshape(-1, 1), yvec.reshape(-1, 1))
    xvec = xvec[mask]
    yvec = yvec[mask]
    n = int(xvec.shape[0])

    # Coerce x0 before any branch so None / non-numeric is handled uniformly.
    try:
        x0f = float(x0)
        if not math.isfinite(x0f):
            x0f = None
    except (TypeError, ValueError):
        x0f = None

    if n < 3:
        return {
            "linear": None,
            "quadratic": None,
            "slope_at_current": None,
            "curvature": None,
            "x_mean": None,
            "x0": x0f,
            "n": n,
            "status": "insufficient_data",
        }

    if x0f is None:
        return {
            "linear": None,
            "quadratic": None,
            "slope_at_current": None,
            "curvature": None,
            "x_mean": None,
            "x0": None,
            "n": n,
            "status": "invalid_x0",
        }

    x_mean = float(xvec.mean())
    dx = xvec - x_mean
    D = np.column_stack([np.ones(n), dx, dx * dx])
    pinv_D = np.linalg.pinv(D)
    beta = pinv_D @ yvec
    b0, b1, b2 = float(beta[0]), float(beta[1]), float(beta[2])
    slope = b1 + 2.0 * b2 * (x0f - x_mean)

    return {
        "linear": b1,
        "quadratic": b2,
        "slope_at_current": slope,
        "curvature": 2.0 * b2,
        "x_mean": x_mean,
        "x0": x0f,
        "n": n,
        "status": "ok",
    }


# --------------------------------------------------------------------------- #
# 3. Partial correlation residualizing against controls (+ intercept)
# --------------------------------------------------------------------------- #
def partial_correlation(df, x, y, controls):
    """Pearson correlation of ``x`` and ``y`` after residualizing on ``controls``.

    Rows with any non-finite value across ``x``, ``y`` and ``controls`` are
    dropped. Residuals are obtained by OLS regression on an intercept plus the
    control columns. The p-value uses the Fisher-z normal approximation with
    effective sample size ``n - k - 3`` (``k`` = number of controls).

    ``controls`` may be a single column name or an iterable of column names;
    caller order is preserved in the returned ``controls`` list.
    """
    if isinstance(controls, str):
        controls_list = [controls]
    else:
        controls_list = list(controls)
    cols_needed = [x, y] + controls_list

    sub = df.loc[:, cols_needed].apply(pd.to_numeric, errors="coerce")
    sub = sub.replace([np.inf, -np.inf], np.nan).dropna()
    n = int(sub.shape[0])
    k = len(controls_list)

    result = {
        "r": None,
        "p": None,
        "n": n,
        "controls": controls_list,
        "status": "insufficient_data",
    }

    # Need at least k + 3 rows to residualize and test.
    if n < k + 3:
        return result

    xv = sub[x].to_numpy(dtype=float)
    yv = sub[y].to_numpy(dtype=float)
    if len(controls_list) > 0:
        C = sub[controls_list].to_numpy(dtype=float)
        Cc = C - C.mean(axis=0)
        D = np.column_stack([np.ones(n), Cc])
        pinv_D = np.linalg.pinv(D)
        xv = xv - D @ (pinv_D @ xv)
        yv = yv - D @ (pinv_D @ yv)

    r = _pearson_r(xv, yv)
    if r is None:
        result["status"] = "constant_residuals"
        return result

    # Fisher-z normal approximation (effective df adjusted for k controls).
    eff = n - k - 3
    if eff <= 0:
        result.update({"r": r, "p": None, "status": "insufficient_dof"})
        return result
    if abs(r) >= 1.0:
        p = 0.0
    else:
        z = 0.5 * math.log((1.0 + r) / (1.0 - r)) * math.sqrt(eff)
        p = _two_sided_normal_p(z)

    result.update({"r": r, "p": p, "status": "ok"})
    return result


# --------------------------------------------------------------------------- #
# 4. Deterministic block bootstrap confidence interval
# --------------------------------------------------------------------------- #
def _resolve_statistic(statistic):
    """Return a callable mapping a 1-D array to a scalar."""
    if callable(statistic):
        return statistic
    if statistic == "mean":
        return lambda a: float(np.mean(a)) if a.size else float("nan")
    if statistic == "median":
        return lambda a: float(np.median(a)) if a.size else float("nan")
    raise ValueError("statistic must be 'mean', 'median', or a callable")


def block_bootstrap_ci(values, groups, statistic="mean", B=1000, seed=0, alpha=0.05):
    """Block-bootstrap CI that resamples whole group blocks with replacement.

    ``groups`` carries the block label for each row and is never coerced to
    numeric — labels may be strings or any hashable. For each of ``B``
    iterations all rows belonging to ``n_blocks`` resampled labels are gathered
    and ``statistic`` (``"mean"`` / ``"median"`` / callable taking a 1-D array)
    is evaluated. The CI is the empirical ``alpha/2`` and ``1 - alpha/2``
    quantile of the bootstrap distribution. The RNG is
    ``numpy.random.default_rng(seed)`` so repeated calls with the same seed are
    identical.

    Returns ``status="insufficient_blocks"`` (with ``ci=None``) when fewer than
    2 distinct blocks are present.
    """
    values_arr = _to_float_array(values)
    if isinstance(groups, pd.Series):
        groups_arr = groups.to_numpy()
    else:
        groups_arr = np.asarray(groups)
    if groups_arr.shape[0] != values_arr.shape[0]:
        raise ValueError("values and groups must have equal length")

    # Work on finite values only; keep label alignment.
    finite = np.isfinite(values_arr)
    v = values_arr[finite]
    g = groups_arr[finite]
    n_rows = int(v.shape[0])

    stat_fn = _resolve_statistic(statistic)

    # Unique block labels in order of first appearance (labels stay hashable).
    seen = {}
    order = []
    for label in g:
        key = label.item() if isinstance(label, np.generic) else label
        if key not in seen:
            seen[key] = True
            order.append(key)
    blocks = order
    n_blocks = len(blocks)

    base = {
        "estimate": None,
        "ci": None,
        "n_rows": n_rows,
        "n_blocks": n_blocks,
        "B": int(B),
        "seed": seed,
        "statistic": statistic if isinstance(statistic, str) else getattr(statistic, "__name__", "custom"),
        "status": "insufficient_blocks",
    }

    if n_blocks < 2 or n_rows == 0:
        return base

    # Map each label to its member values once.
    members = {key: [] for key in blocks}
    for label, val in zip(g, v):
        key = label.item() if isinstance(label, np.generic) else label
        members[key].append(val)
    members = {key: np.asarray(vals, dtype=float) for key, vals in members.items()}

    estimate = stat_fn(v)
    rng = np.random.default_rng(seed)
    idx_pool = np.arange(n_blocks)

    boot = np.empty(int(B), dtype=float)
    for b in range(int(B)):
        chosen = idx_pool[rng.integers(0, n_blocks, size=n_blocks)]
        pooled = np.concatenate([members[blocks[i]] for i in chosen])
        boot[b] = stat_fn(pooled)

    lo = float(np.quantile(boot, alpha / 2.0))
    hi = float(np.quantile(boot, 1.0 - alpha / 2.0))

    base.update({"estimate": estimate, "ci": (lo, hi), "status": "ok"})
    return base


# --------------------------------------------------------------------------- #
# 5. Benjamini-Hochberg q-value correction
# --------------------------------------------------------------------------- #
def benjamini_hochberg(p_values):
    """Benjamini-Hochberg adjusted q-values preserving original order.

    Finite p-values in ``[0, 1]`` are corrected using ``m`` equal to the number
    of valid entries; invalid entries (``None``, non-finite, outside ``[0, 1]``)
    become ``None`` in the output and are excluded from the correction.
    Monotonicity is enforced (stepping from the largest p downward) and results
    are clipped to ``[0, 1]``. An empty input returns an empty list.
    """
    out: List[Optional[float]] = [None] * len(p_values)

    valid_idx = []
    valid_p = []
    for i, pv in enumerate(p_values):
        if pv is None:
            continue
        try:
            pfloat = float(pv)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(pfloat) or pfloat < 0.0 or pfloat > 1.0:
            continue
        valid_idx.append(i)
        valid_p.append(pfloat)

    m = len(valid_p)
    if m == 0:
        return out

    order = np.argsort(valid_p, kind="mergesort")
    ranked_p = np.array([valid_p[i] for i in order], dtype=float)
    ranks = np.arange(1, m + 1, dtype=float)
    adjusted = ranked_p * m / ranks

    # Enforce monotonicity from the largest p downward.
    for j in range(m - 2, -1, -1):
        if adjusted[j] > adjusted[j + 1]:
            adjusted[j] = adjusted[j + 1]
    adjusted = np.clip(adjusted, 0.0, 1.0)

    for slot, orig_pos in enumerate(order):
        out[valid_idx[orig_pos]] = float(adjusted[slot])
    return out


# --------------------------------------------------------------------------- #
# 6. Durbin-Watson statistic
# --------------------------------------------------------------------------- #
def durbin_watson(resid):
    """Durbin-Watson autocorrelation statistic, or ``None`` if undefined.

    Returns ``None`` when fewer than 2 finite residuals are provided or when the
    residual sum of squares is zero (denominator would vanish).
    """
    r = _to_float_array(resid)
    r = r[np.isfinite(r)]
    if r.shape[0] < 2:
        return None
    denom = float(r @ r)
    if denom == 0.0:
        return None
    diff = np.diff(r)
    return float((diff @ diff) / denom)


# --------------------------------------------------------------------------- #
# 7. Transparent first-difference variance-ratio stationarity heuristic
# --------------------------------------------------------------------------- #
def stationarity_check(series):
    """First-difference variance-ratio heuristic. NOT a formal unit-root test.

    Computes ``ratio = var(diff(series)) / var(series)``. Differencing a
    stationary series tends to inflate variance (ratio > 1) whereas a
    random-walk-like series is dominated by its level variance (ratio < 1). The
    reported ``is_stationary`` flag uses the transparent threshold
    ``ratio >= 1``. Highly persistent but stationary AR series can be flagged
    non-stationary by this heuristic — it is a quick screen, never a test.
    """
    s = _to_float_array(series)
    s = s[np.isfinite(s)]
    n = int(s.shape[0])

    if n < 3:
        return {
            "is_stationary": None,
            "n": n,
            "variance_level": None,
            "variance_diff": None,
            "ratio": None,
            "status": "insufficient_data",
        }

    var_level = float(np.var(s, ddof=1))
    if var_level == 0.0:
        return {
            "is_stationary": True,
            "n": n,
            "variance_level": 0.0,
            "variance_diff": 0.0,
            "ratio": None,
            "status": "constant_series",
        }

    d = np.diff(s)
    var_diff = float(np.var(d, ddof=1)) if d.shape[0] >= 2 else 0.0
    ratio = var_diff / var_level
    return {
        "is_stationary": bool(ratio >= 1.0),
        "n": n,
        "variance_level": var_level,
        "variance_diff": var_diff,
        "ratio": ratio,
        "status": "ok",
    }


# --------------------------------------------------------------------------- #
# 8. Support-domain percentile summary
# --------------------------------------------------------------------------- #
def support_domain(series):
    """Percentile summary of the finite numeric support of ``series``.

    Returns exactly ``p5``, ``p25``, ``p50``, ``p75``, ``p95``, ``n``,
    ``current_median`` plus a ``status`` field. ``current_median`` is the median
    of the finite values (equal to ``p50``). Non-finite / empty input yields
    ``status="empty"`` with ``None`` percentiles.
    """
    s = _to_float_array(series)
    s = s[np.isfinite(s)]
    n = int(s.shape[0])

    if n == 0:
        return {
            "p5": None,
            "p25": None,
            "p50": None,
            "p75": None,
            "p95": None,
            "n": 0,
            "current_median": None,
            "status": "empty",
        }

    qs = np.percentile(s, [5, 25, 50, 75, 95])
    median = float(qs[2])
    return {
        "p5": float(qs[0]),
        "p25": float(qs[1]),
        "p50": median,
        "p75": float(qs[3]),
        "p95": float(qs[4]),
        "n": n,
        "current_median": median,
        "status": "ok",
    }


# --------------------------------------------------------------------------- #
# Optional smoke path — no production side effects on import.
# --------------------------------------------------------------------------- #
if __name__ == "__main__":  # pragma: no cover
    rng = np.random.default_rng(0)
    _x = np.linspace(0, 10, 60)
    _y = 2.0 + 1.5 * _x - 0.05 * _x ** 2 + rng.normal(0, 0.5, size=_x.size)
    print("ols_centered:", {k: v for k, v in ols_centered(_x, _y).items()
                            if k in ("beta", "r2", "rank", "status")})
    print("slope_at_current:", slope_at_current(_x, _y, 8.0)["slope_at_current"])
    print("bh:", benjamini_hochberg([0.01, 0.04, 0.2, 0.6]))
    print("dw:", durbin_watson(np.array([1.0, 1.1, 0.9, 1.2])))
