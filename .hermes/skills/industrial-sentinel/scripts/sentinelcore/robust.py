"""robust.py — check C4: robust z + Mahalanobis distance (four-level ladder).

Robust z:        z_rob = 0.6745 * (x - median) / MAD, outlier when |z| > 3.5.
                 MAD == 0 -> fall back to sigma_overall scale; no scale ->
                 parameter skipped (recorded, never guessed).

Mahalanobis:     d2 = z' R^-1 z with R the baseline correlation matrix,
                 z_i = 0.6745 * (x_i - median_i) / MAD_i. R = L L' (Cholesky
                 lower, pre-stored in the baseline) -> online cost is ONE
                 forward substitution per row (triangular solve), then
                 d2 = y . y. Threshold = chi-square quantile at q (default
                 0.999) via Wilson-Hilferty:
                 chi2_q(k) ~ k * (1 - 2/(9k) + z_q * sqrt(2/(9k)))^3.

Degradation ladder (applied in order, each level recorded verbatim in the
alert/report provenance):
  L1  correlation condition number > 1e10 or any |r| > 0.98
      -> iteratively drop the offending column(s), rebuild Cholesky;
  L2  more than 30 candidate parameters -> keep variance top-20;
  L3  fewer than 50 steady rows (or Cholesky missing / failed)
      -> skip Mahalanobis entirely, robust z only;
  L4  rows with NaN in the kept columns are excluded from d2 and counted
      (rows_skipped), never imputed.
"""

import numpy as np

from sentinelcore._constants import RULE

DEFAULTS = {
    "robust_z_limit": 3.5,
    "mahalanobis_q": 0.999,
    "mahalanobis_min_steady_rows": 50,
    "mahalanobis_max_params": 30,
    "mahalanobis_top_k": 20,
    "cond_max": 1e10,
    "r_max": 0.98,
}


def chi2_quantile(q, k):
    """Wilson-Hilferty approximation of the chi-square quantile."""
    from scipy.stats import norm  # numpy/scipy only — allowed dependency set

    kk = float(k)
    zq = float(norm.ppf(float(q)))
    term = 1.0 - 2.0 / (9.0 * kk) + zq * np.sqrt(2.0 / (9.0 * kk))
    return float(kk * term ** 3)


def robust_z(x, median, mad, sigma_overall=None):
    """0.6745 * (x - median) / MAD with graceful scale fallback."""
    v = np.asarray(x, dtype=float)
    scale = None
    if mad is not None and np.isfinite(mad) and mad > 0:
        scale = float(mad) / 0.6745
    elif sigma_overall is not None and np.isfinite(sigma_overall) and sigma_overall > 0:
        scale = float(sigma_overall)
    if scale is None or median is None or not np.isfinite(median):
        return np.full(v.shape, np.nan)
    return 0.6745 * (v - float(median)) / scale


def robust_outliers(z, limit=3.5):
    """Episode list [{index, run_length, statistic}] of |z| > limit runs."""
    zz = np.asarray(z, dtype=float)
    mask = np.isfinite(zz) & (np.abs(zz) > limit)
    episodes = []
    start = None
    for i, flag in enumerate(mask):
        if flag and start is None:
            start = i
        elif not flag and start is not None:
            j = int(np.nanargmax(np.abs(zz[start:i])))
            episodes.append({"index": start + int(j), "run_length": i - start,
                             "statistic": float(zz[start + j])})
            start = None
    if start is not None:
        i = mask.size
        j = int(np.nanargmax(np.abs(zz[start:i])))
        episodes.append({"index": start + int(j), "run_length": i - start,
                         "statistic": float(zz[start + j])})
    return episodes


def _drop_most_correlated(corr):
    """Return the column index to drop (highest count of |r|>0.98 partners)."""
    n = corr.shape[0]
    counts = np.zeros(n, dtype=int)
    for i in range(n):
        for j in range(n):
            if i != j and abs(corr[i, j]) > DEFAULTS["r_max"]:
                counts[i] += 1
    worst = int(np.argmax(counts))
    # tie-break: larger sum of |r|
    sums = np.nansum(np.abs(corr), axis=1)
    for i in range(n):
        if counts[i] == counts[worst] and sums[i] > sums[worst]:
            worst = i
    return worst


def prepare_mahalanobis(cols, corr_flat, cholesky_lower, variances=None,
                        n_steady=0, thresholds=None):
    """Degradation ladder levels 1-3. Returns (L, kept_cols, degradations)
    where L is the lower-triangular Cholesky factor or None (skip)."""
    cfg = dict(DEFAULTS)
    if thresholds:
        cfg.update({k: thresholds[k] for k in
                    ("mahalanobis_min_steady_rows", "mahalanobis_max_params",
                     "mahalanobis_top_k", "cond_max", "r_max")
                    if thresholds.get(k) is not None})
    degradations = []
    corr = np.asarray(corr_flat, dtype=float).reshape(len(cols), len(cols))
    kept = list(range(len(cols)))

    if n_steady < int(cfg["mahalanobis_min_steady_rows"]):
        degradations.append("L3_steady_rows_below_50_mahalanobis_skipped")
        return None, [cols[i] for i in kept], degradations
    if cholesky_lower is None:
        degradations.append("L3_cholesky_missing_mahalanobis_skipped")
        return None, [cols[i] for i in kept], degradations

    # L2 — parameter count cap
    if len(kept) > int(cfg["mahalanobis_max_params"]):
        if variances is not None and len(variances) == len(cols):
            order = sorted(kept, key=lambda i: -(variances[i] if np.isfinite(variances[i]) else 0))
            kept = sorted(order[:int(cfg["mahalanobis_top_k"])])
            degradations.append(f"L2_params_capped_to_top_{cfg['mahalanobis_top_k']}")

    # L1 — ill-conditioning: iteratively drop worst-correlated columns
    for _ in range(len(kept)):
        sub = corr[np.ix_(kept, kept)]
        max_r = np.nanmax(np.abs(sub - np.eye(sub.shape[0]) * 10)) if sub.shape[0] > 1 else 0.0
        cond = np.linalg.cond(sub) if sub.shape[0] > 1 else 1.0
        if cond <= cfg["cond_max"] and max_r <= cfg["r_max"]:
            break
        if len(kept) <= 2:
            degradations.append("L1_unfixable_ill_conditioning_mahalanobis_skipped")
            return None, [cols[i] for i in kept], degradations
        drop = _drop_most_correlated(sub)
        dropped_col = kept[drop]
        kept = [i for i in kept if i != dropped_col]
        degradations.append(f"L1_dropped_{cols[dropped_col]}")
    else:
        pass

    if len(kept) < 2:
        degradations.append("L3_too_few_columns_mahalanobis_skipped")
        return None, [cols[i] for i in kept], degradations

    chol_full = np.asarray(cholesky_lower, dtype=float).reshape(len(cols), len(cols))
    L = chol_full[np.ix_(kept, kept)]
    try:
        np.linalg.cholesky(L @ L.T)
    except np.linalg.LinAlgError:
        degradations.append("L3_cholesky_rebuild_failed_mahalanobis_skipped")
        return None, [cols[i] for i in kept], degradations
    return L, [cols[i] for i in kept], degradations


def mahalanobis_d2(matrix, L):
    """Squared Mahalanobis distances for every row of `matrix` (may contain
    NaN -> those rows return NaN). One forward substitution per row."""
    X = np.asarray(matrix, dtype=float)
    Lc = np.asarray(L, dtype=float)
    n, k = X.shape
    d2 = np.full(n, np.nan)
    ok = np.isfinite(X).all(axis=1)
    if not ok.any():
        return d2
    Z = X[ok]
    # forward substitution for all rows at once (L is lower-triangular)
    Y = np.zeros_like(Z)
    for j in range(k):
        Y[:, j] = (Z[:, j] - Y[:, :j] @ Lc[j, :j]) / Lc[j, j]
    d2[ok] = np.einsum("ij,ij->i", Y, Y)
    return d2


def mahalanobis_outlier_episodes(d2, q=0.999, k=None):
    """Episodes of consecutive rows with d2 > chi2_q(k). Returns list of
    {index, run_length, statistic} with statistic = peak d2."""
    dd = np.asarray(d2, dtype=float)
    if k is None:
        k = int(np.sum(np.isfinite(dd)))
    if k < 2 or not np.isfinite(dd).any():
        return []
    limit = chi2_quantile(q, k)
    mask = np.isfinite(dd) & (dd > limit)
    episodes = []
    start = None
    for i, flag in enumerate(mask):
        if flag and start is None:
            start = i
        elif not flag and start is not None:
            j = int(np.nanargmax(dd[start:i]))
            episodes.append({"index": start + j, "run_length": i - start,
                             "statistic": float(dd[start + j]),
                             "d2_limit": limit})
            start = None
    if start is not None:
        i = mask.size
        j = int(np.nanargmax(dd[start:i]))
        episodes.append({"index": start + j, "run_length": i - start,
                         "statistic": float(dd[start + j]), "d2_limit": limit})
    return episodes


def rule_robust():
    return RULE["ROBUST_Z_OUTLIER"]


def rule_mahalanobis():
    return RULE["MAHALANOBIS_OUTLIER"]
