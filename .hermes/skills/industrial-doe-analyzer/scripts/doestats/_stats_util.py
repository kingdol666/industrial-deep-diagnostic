"""Shared numeric utilities (BH-FDR, Welch CI, autocorrelation, OLS)."""

import math

import numpy as np
from scipy import stats as sps


def bh_adjust(pvals):
    """Benjamini-Hochberg adjusted q-values.

    NaN/None p-values are passed through as None (they must never enter the
    family — plan C5). Returns a list aligned with the input.
    """
    idx = [i for i, p in enumerate(pvals) if p is not None and not (isinstance(p, float) and math.isnan(p))]
    clean = [float(pvals[i]) for i in idx]
    m = len(clean)
    out = [None] * len(pvals)
    if m == 0:
        return out
    order = np.argsort(clean)
    ranked = np.asarray(clean, dtype=float)[order]
    q = ranked * m / np.arange(1, m + 1)
    q = np.minimum.accumulate(q[::-1])[::-1]
    q = np.clip(q, 0.0, 1.0)
    for pos, orig_idx in enumerate(order):
        out[idx[orig_idx]] = float(q[pos])
    return out


def welch_delta_ci(x_hi, x_lo, conf=0.95):
    """Delta = mean(x_hi) - mean(x_lo) with Welch t CI. x_* are 1-D arrays.

    Returns (delta, lo, hi, n_hi, n_lo) or None when a group is too small.
    """
    x_hi = np.asarray(x_hi, dtype=float)
    x_lo = np.asarray(x_lo, dtype=float)
    x_hi = x_hi[~np.isnan(x_hi)]
    x_lo = x_lo[~np.isnan(x_lo)]
    if x_hi.size < 2 or x_lo.size < 2:
        return None
    v_hi = x_hi.var(ddof=1) / x_hi.size
    v_lo = x_lo.var(ddof=1) / x_lo.size
    se = math.sqrt(v_hi + v_lo)
    if se <= 0:
        return None
    delta = float(x_hi.mean() - x_lo.mean())
    df = (v_hi + v_lo) ** 2 / max(
        (v_hi ** 2) / (x_hi.size - 1) + (v_lo ** 2) / (x_lo.size - 1), 1e-300
    )
    t_crit = sps.t.ppf(0.5 + conf / 2.0, df)
    return delta, delta - t_crit * se, delta + t_crit * se, int(x_hi.size), int(x_lo.size)


def lag1_autocorr(x):
    """Lag-1 autocorrelation of a finite float series (NaN-tolerant)."""
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    if x.size < 4:
        return None
    x0 = x[:-1] - x[:-1].mean()
    x1 = x[1:] - x[1:].mean()
    denom = math.sqrt(float((x0 * x0).sum()) * float((x1 * x1).sum()))
    if denom <= 0:
        return None
    return float((x0 * x1).sum() / denom)


def effective_n(n, rho):
    """Effective sample size under AR(1): n(1-rho)/(1+rho), floored at 2."""
    if n is None or rho is None or not (-0.99 < rho < 0.99):
        return n
    return max(2, int(n * (1.0 - rho) / (1.0 + rho)))


def ols_fit(X, y):
    """OLS via lstsq. Returns (beta, rank, rss, xtx_inv or None).

    X: (n, p) array without intercept column handling — caller decides.
    """
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    n, p = X.shape
    Xa = np.column_stack([np.ones(n), X])
    beta, _, rank, _ = np.linalg.lstsq(Xa, y, rcond=None)
    resid = y - Xa @ beta
    rss = float(resid @ resid)
    xtx_inv = None
    if rank == Xa.shape[1]:
        try:
            xtx_inv = np.linalg.inv(Xa.T @ Xa)
        except np.linalg.LinAlgError:
            xtx_inv = None
    return beta, rank, rss, xtx_inv, Xa


def sha256_file(path):
    import hashlib

    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()
