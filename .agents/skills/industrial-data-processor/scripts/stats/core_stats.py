"""Core statistical analysis: Pearson, Spearman, detrended, CCF, multi-testing, MI, Granger.

Ported from stats.mjs (JS) and stats_analysis.py (Python fallback).
Uses scipy.stats when available for p-values and distributions;
falls back to pure-Python implementations.
"""

import json
import math
import sys
from collections import OrderedDict
from pathlib import Path

# --- Try scipy for distribution functions; fall back to pure Python ---
try:
    from scipy.stats import t as scipy_t, f as scipy_f
    _HAS_SCIPY = True
except ImportError:
    _HAS_SCIPY = False


# ═══════════════════════════════════════════════
#  PURE-PYTHON T-DISTRIBUTION (fallback when scipy unavailable)
# ═══════════════════════════════════════════════

def _ln_gamma(z):
    """Lanczos approximation for ln(Gamma(z))."""
    if z < 0.5:
        return math.log(math.pi / math.sin(math.pi * z)) - _ln_gamma(1 - z)
    z -= 1
    g = 7
    c = [
        0.99999999999980993, 676.5203681218851, -1259.1392167224028,
        771.32342877765313, -176.61502916214059, 12.507343278686905,
        -0.13857109526572012, 9.9843695780195716e-6, 1.5056327351493116e-7
    ]
    x = c[0]
    for i in range(1, g + 2):
        x += c[i] / (z + i)
    t = z + g + 0.5
    return 0.5 * math.log(2 * math.pi) + (z + 0.5) * math.log(t) - t + math.log(x)


def _beta_cf(x, a, b):
    """Continued fraction for regularized incomplete beta."""
    max_iter = 200
    epsilon = 1e-10
    qab = a + b
    qap = a + 1
    qam = a - 1
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < 1e-30:
        d = 1e-30
    d = 1.0 / d
    h = d

    for m in range(1, max_iter + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < epsilon:
            break

    return (math.exp(a * math.log(x) + b * math.log(1 - x) +
                     _ln_gamma(a + b) - _ln_gamma(a) - _ln_gamma(b)) *
            h / a)


def _reg_beta(x, a, b):
    """Regularized incomplete beta function."""
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    return _beta_cf(x, a, b)


def _t_dist_2tailed(t_val, df):
    """Two-tailed p-value from t-distribution."""
    if df <= 0:
        return 1.0
    x = df / (df + t_val * t_val)
    p1 = _reg_beta(x, df / 2.0, 0.5)
    return min(1.0, p1)


def _f_test_p_value(f_val, df1, df2):
    """F-test p-value via regularized incomplete beta."""
    if f_val <= 0:
        return 1.0
    x = df2 / (df2 + df1 * f_val)
    return _reg_beta(x, df2 / 2.0, df1 / 2.0)


def _t_pvalue(t_val, df):
    """Two-tailed t-test p-value, scipy if available."""
    if _HAS_SCIPY:
        return float(scipy_t.sf(abs(t_val), df) * 2)
    return _t_dist_2tailed(t_val, df)


def _f_pvalue(f_val, df1, df2):
    if _HAS_SCIPY:
        return float(scipy_f.sf(f_val, df1, df2))
    return _f_test_p_value(f_val, df1, df2)


# ═══════════════════════════════════════════════
#  RANKING
# ═══════════════════════════════════════════════

def _rank_array(arr):
    """Returns ranks (1-based) with average ranks for ties."""
    indexed = sorted(enumerate(arr), key=lambda x: x[1])
    n = len(indexed)
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j < n and indexed[j][1] == indexed[i][1]:
            j += 1
        avg_rank = (i + j + 2) / 2.0  # 1-based average
        for k in range(i, j):
            ranks[indexed[k][0]] = avg_rank
        i = j
    return ranks


# ═══════════════════════════════════════════════
#  CORRELATION FUNCTIONS
# ═══════════════════════════════════════════════

def _safe_float(v):
    """Coerce value to float, returning None on failure."""
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        if math.isnan(v) or math.isinf(v):
            return None
        return float(v)
    if isinstance(v, str):
        try:
            return float(v)
        except (ValueError, TypeError):
            return None
    return None


def pearson(x, y):
    """Pearson correlation with two-tailed p-value.

    Returns: dict with r, n, p
    """
    n = min(len(x), len(y))
    count = 0
    sx = sy = sxy = sx2 = sy2 = 0.0
    for i in range(n):
        xi = _safe_float(x[i])
        yi = _safe_float(y[i])
        if xi is None or yi is None:
            continue
        sx += xi
        sy += yi
        sxy += xi * yi
        sx2 += xi * xi
        sy2 += yi * yi
        count += 1

    if count < 3:
        return {'r': 0.0, 'n': count, 'p': 1.0}

    num = count * sxy - sx * sy
    den = math.sqrt((count * sx2 - sx * sx) * (count * sy2 - sy * sy))
    r = num / den if den != 0 else 0.0

    # Two-tailed p-value
    try:
        t_val = r * math.sqrt((count - 2) / (1 - r * r + 1e-12))
        p = _t_pvalue(abs(t_val), count - 2)
    except (ValueError, ZeroDivisionError):
        p = 1.0

    return {'r': round(r, 4), 'n': count, 'p': round(p, 4)}


def spearman(x, y):
    """Spearman rank correlation (returns same dict format as pearson)."""
    # Remove null/NaN pairs
    valid_x, valid_y = [], []
    for i in range(len(x)):
        xi = _safe_float(x[i])
        yi = _safe_float(y[i])
        if xi is not None and yi is not None:
            valid_x.append(xi)
            valid_y.append(yi)

    if len(valid_x) < 3:
        return {'r': 0.0, 'n': len(valid_x), 'p': 1.0}

    rank_x = _rank_array(valid_x)
    rank_y = _rank_array(valid_y)
    return pearson(rank_x, rank_y)


# ═══════════════════════════════════════════════
#  LINEAR DETRENDING
# ═══════════════════════════════════════════════

def _linear_detrend(arr):
    """Remove linear trend from array. Returns detrended copy."""
    n = len(arr)
    valid = [(i, v) for i, v in enumerate(arr)
             if v is not None and not (isinstance(v, float) and (math.isnan(v) or math.isinf(v)))]
    if len(valid) < 3:
        return arr[:]

    sx = sy = sxy = sx2 = 0.0
    for idx, val in valid:
        sx += idx
        sy += val
        sxy += idx * val
        sx2 += idx * idx

    m = len(valid)
    slope = (m * sxy - sx * sy) / (m * sx2 - sx * sx + 1e-12)
    intercept = (sy - slope * sx) / m

    detrended = arr[:]
    for i in range(n):
        v = _safe_float(arr[i])
        if v is not None:
            detrended[i] = v - (slope * i + intercept)
    return detrended


def detrended_correlation(x, y):
    """Correlation after removing linear trends from both variables.

    Returns: raw_r, raw_p, detrended_r, detrended_p, attenuation_pct, trend_confounded, n
    """
    x_detrended = _linear_detrend(x)
    y_detrended = _linear_detrend(y)
    raw = pearson(x, y)
    det = pearson(x_detrended, y_detrended)
    attenuation = (raw['r'] - det['r']) / abs(raw['r']) if raw['r'] != 0 else 0.0
    return {
        'raw_r': raw['r'],
        'raw_p': raw['p'],
        'detrended_r': det['r'],
        'detrended_p': det['p'],
        'attenuation_pct': round(attenuation * 100, 1),
        'trend_confounded': abs(attenuation) > 0.5,
        'n': raw['n'],
    }


# ═══════════════════════════════════════════════
#  CROSS-CORRELATION FUNCTION (CCF)
# ═══════════════════════════════════════════════

def full_lag_ccf(x, y, max_lag):
    """Compute cross-correlation for all lags [-max_lag, max_lag]."""
    x_clean = [_safe_float(v) for v in x]
    y_clean = [_safe_float(v) for v in y]
    ccf = []
    for lag in range(-max_lag, max_lag + 1):
        x_slice, y_slice = [], []
        for i in range(len(x_clean)):
            j = i + lag
            if j < 0 or j >= len(y_clean):
                continue
            if x_clean[i] is not None and y_clean[j] is not None:
                x_slice.append(x_clean[i])
                y_slice.append(y_clean[j])
        result = pearson(x_slice, y_slice)
        ccf.append({'lag': lag, 'r': result['r'], 'n': result['n']})
    return ccf


def find_best_lag(ccf):
    """Find the lag with the highest absolute correlation."""
    best = ccf[0]
    for entry in ccf:
        if abs(entry['r']) > abs(best['r']):
            best = entry
    return best


def lag_window_consistency(ccf, best_lag, max_lag, window_size=3):
    """Check if adjacent lags show consistent correlation pattern."""
    center = best_lag + max_lag  # convert to array index (offset by max_lag)
    result = {
        'best_lag': best_lag,
        'best_r': ccf[center]['r'] if 0 <= center < len(ccf) else 0.0,
        'adjacent_r': [],
        'consistent': True,
    }

    for d in range(-window_size, window_size + 1):
        if d == 0:
            continue
        idx = center + d
        if 0 <= idx < len(ccf):
            result['adjacent_r'].append({'lag': ccf[idx]['lag'], 'r': ccf[idx]['r']})

    best_sign = 1 if result['best_r'] > 0 else -1
    consistent_count = 0
    for adj in result['adjacent_r']:
        adj_sign = 1 if adj['r'] > 0 else -1
        if adj_sign == best_sign and abs(adj['r']) > 0.3 * abs(result['best_r']):
            consistent_count += 1

    result['consistent'] = consistent_count >= 2
    result['isolated_spike'] = not result['consistent'] and abs(result['best_r']) > 0.5
    result['consistent_count'] = consistent_count
    return result


# ═══════════════════════════════════════════════
#  TIME SORTING VALIDATION
# ═══════════════════════════════════════════════

def _validate_time_sorting(rows, time_col):
    """Check if rows are sorted by time column."""
    if not time_col or time_col not in (rows[0] if rows else {}):
        return {'time_sorted': None, 'time_column': time_col,
                'message': 'No time column specified or found.'}

    indices = []
    for i, row in enumerate(rows):
        v = row.get(time_col)
        if v is not None:
            indices.append((i, str(v)))

    if len(indices) < 2:
        return {'time_sorted': None, 'time_column': time_col,
                'message': 'Insufficient time values to check.'}

    is_sorted = True
    for k in range(1, len(indices)):
        if indices[k][1] < indices[k - 1][1]:
            is_sorted = False
            break

    return {
        'time_sorted': is_sorted,
        'time_column': time_col,
        'n_rows': len(rows),
        'n_time_values': len(indices),
        'message': 'Time-sorted' if is_sorted else 'NOT sorted by time — lag analysis may produce artifacts.',
    }


# ═══════════════════════════════════════════════
#  MULTIPLE TESTING CORRECTION
# ═══════════════════════════════════════════════

def _bonferroni_threshold(alpha, n_comparisons):
    return alpha / max(n_comparisons, 1)


def _multiple_testing_report(correlations_by_target, alpha=0.05):
    """Bonferroni correction report."""
    total_tests = 0
    significant_nominal = 0
    for target, corrs in correlations_by_target.items():
        if not corrs:
            continue
        total_tests += len(corrs)
        for v in corrs.values():
            p = v.get('p', 1.0) if isinstance(v, dict) else 1.0
            if p < alpha:
                significant_nominal += 1

    if total_tests == 0:
        return {
            'total_tests': 0,
            'nominally_significant_p0_05': 0,
            'expected_false_positives': 0,
            'bonferroni_threshold': alpha,
            'bonferroni_significant': 0,
        }

    expected_fp = total_tests * alpha
    corrected_threshold = _bonferroni_threshold(alpha, total_tests)

    significant_corrected = 0
    for target, corrs in correlations_by_target.items():
        if not corrs:
            continue
        for v in corrs.values():
            p = v.get('p', 1.0) if isinstance(v, dict) else 1.0
            if p < corrected_threshold:
                significant_corrected += 1

    return {
        'total_tests': total_tests,
        'nominally_significant_p0_05': significant_nominal,
        'expected_false_positives': round(expected_fp, 1),
        'bonferroni_threshold': round(corrected_threshold, 6),
        'bonferroni_significant': significant_corrected,
    }


# ═══════════════════════════════════════════════
#  STRATIFIED ANALYSIS (Simpson's Paradox)
# ═══════════════════════════════════════════════

def _stratified_analysis(col_data, target_cols, group_col_data, group_values):
    """Per-group correlation analysis to detect Simpson's Paradox."""
    results = []
    for target in target_cols:
        if target not in col_data:
            continue
        for param_name, param_values in col_data.items():
            if param_name == target:
                continue
            full_corr = pearson(col_data[target], param_values)

            strata = {}
            reversal = False
            max_attenuation = 0.0

            for g_val in group_values:
                indices = [i for i, g in enumerate(group_col_data) if str(g) == str(g_val)]
                if len(indices) < 10:
                    continue

                x_sub = [col_data[target][i] for i in indices]
                y_sub = [param_values[i] for i in indices]
                sub_corr = pearson(x_sub, y_sub)
                strata[g_val] = {'r': sub_corr['r'], 'p': sub_corr['p'], 'n': len(indices)}

                if full_corr['r'] != 0 and sub_corr['r'] != 0 and (full_corr['r'] > 0) != (sub_corr['r'] > 0):
                    reversal = True

                att = abs((full_corr['r'] - sub_corr['r']) / full_corr['r']) if full_corr['r'] != 0 else 0.0
                max_attenuation = max(max_attenuation, att)

            if strata:
                severity = ('CRITICAL' if reversal else
                            'SERIOUS' if max_attenuation > 0.5 else
                            'MODERATE' if max_attenuation > 0.3 else 'MILD')
                results.append({
                    'target': target,
                    'parameter': param_name,
                    'full_r': full_corr['r'],
                    'full_p': full_corr['p'],
                    'strata': strata,
                    'simpson_paradox': reversal,
                    'max_attenuation_pct': round(max_attenuation * 100, 1),
                    'severity': severity,
                })

    severity_order = {'CRITICAL': 0, 'SERIOUS': 1, 'MODERATE': 2, 'MILD': 3}
    results.sort(key=lambda x: severity_order.get(x['severity'], 4))
    return results


# ═══════════════════════════════════════════════
#  MUTUAL INFORMATION (k-NN estimator)
# ═══════════════════════════════════════════════

def _digamma(x):
    """Digamma function Ψ(x) = Γ'(x)/Γ(x) — asymptotic expansion."""
    if x < 6:
        return _digamma(x + 1) - 1.0 / x
    inv_x = 1.0 / x
    inv_x2 = inv_x * inv_x
    return math.log(x) - 0.5 * inv_x - inv_x2 / 12.0 + inv_x2 * inv_x2 / 120.0 - inv_x2 * inv_x2 * inv_x2 / 252.0


def _mutual_information(x, y, k=3):
    """k-NN estimator of mutual information (Kraskov estimator)."""
    valid = [(xi, yi) for xi, yi in zip(x, y)
             if xi is not None and yi is not None and
             not (isinstance(xi, float) and (math.isnan(xi) or math.isinf(xi))) and
             not (isinstance(yi, float) and (math.isnan(yi) or math.isinf(yi)))]
    n = len(valid)
    if n < k + 2:
        return {'mi': 0.0, 'n': n, 'warning': 'insufficient data'}

    xs = [v[0] for v in valid]
    ys = [v[1] for v in valid]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    x_range = x_max - x_min or 1.0
    y_range = y_max - y_min or 1.0

    points = [{'xn': (v[0] - x_min) / x_range, 'yn': (v[1] - y_min) / y_range} for v in valid]

    sum_digamma_nx = 0.0
    sum_digamma_ny = 0.0
    digamma_n = _digamma(n)

    for i in range(n):
        dists = []
        for j in range(n):
            if i == j:
                continue
            dx = abs(points[i]['xn'] - points[j]['xn'])
            dy = abs(points[i]['yn'] - points[j]['yn'])
            dists.append({'dx': dx, 'dy': dy, 'dist': max(dx, dy)})

        dists.sort(key=lambda d: d['dist'])
        eps = dists[k - 1]['dist']

        nx = sum(1 for d in dists if d['dx'] < eps)
        ny = sum(1 for d in dists if d['dy'] < eps)
        sum_digamma_nx += _digamma(nx + 1)
        sum_digamma_ny += _digamma(ny + 1)

    mi = max(0.0, digamma_n + _digamma(k) - sum_digamma_nx / n - sum_digamma_ny / n)
    max_mi = 0.5 * math.log2(n)
    mi_normalized = min(1.0, mi / max_mi) if max_mi > 0 else 0.0

    return {'mi': round(mi, 4), 'mi_normalized': round(mi_normalized, 4), 'n': n, 'k': k}


# ═══════════════════════════════════════════════
#  GRANGER CAUSALITY
# ═══════════════════════════════════════════════

def _ols_ssr(y, X):
    """Ordinary Least Squares — sum of squared residuals via Gaussian elimination."""
    n = len(X)
    p = len(X[0])
    if n <= p:
        return -1.0

    # Build X'X and X'y
    XtX = [[0.0] * p for _ in range(p)]
    Xty = [0.0] * p
    for i in range(n):
        for j in range(p):
            Xty[j] += X[i][j] * y[i]
            for k in range(p):
                XtX[j][k] += X[i][j] * X[i][k]

    # Gaussian elimination with partial pivoting
    aug = [XtX[i] + [Xty[i]] for i in range(p)]
    for col in range(p):
        max_row = col
        for row in range(col + 1, p):
            if abs(aug[row][col]) > abs(aug[max_row][col]):
                max_row = row
        aug[col], aug[max_row] = aug[max_row], aug[col]
        if abs(aug[col][col]) < 1e-12:
            continue
        for row in range(col + 1, p):
            factor = aug[row][col] / aug[col][col]
            for j in range(col, p + 1):
                aug[row][j] -= factor * aug[col][j]

    # Back substitution
    beta = [0.0] * p
    for i in range(p - 1, -1, -1):
        s = aug[i][p]
        for j in range(i + 1, p):
            s -= aug[i][j] * beta[j]
        beta[i] = s / aug[i][i] if abs(aug[i][i]) >= 1e-12 else 0.0

    # Compute SSR
    ssr = 0.0
    for i in range(n):
        pred = sum(X[i][j] * beta[j] for j in range(p))
        ssr += (y[i] - pred) ** 2
    return ssr


def _granger_causality(x, y, max_lag=5):
    """Granger causality test: do past values of X help predict Y?"""
    valid = [(xi, yi) for xi, yi in zip(x, y)
             if xi is not None and yi is not None and
             not (isinstance(xi, float) and (math.isnan(xi) or math.isinf(xi))) and
             not (isinstance(yi, float) and (math.isnan(yi) or math.isinf(yi)))]
    n = len(valid)
    if n < max_lag + 10:
        return {'f_stat': 0.0, 'p_value': 1.0, 'significant': False, 'warning': 'insufficient data'}

    results = []
    for lag in range(1, max_lag + 1):
        T = n - lag
        if T < 10:
            continue

        # Y vector (dependent)
        Y_vec = [valid[t][1] for t in range(lag, n)]

        # Restricted model: Y_t = α + Σ β_i Y_{t-i}
        X_restricted = []
        for t in range(lag, n):
            row = [1.0]  # intercept
            for i in range(1, lag + 1):
                row.append(valid[t - i][1])
            X_restricted.append(row)

        # Unrestricted model: Y_t = α + Σ β_i Y_{t-i} + Σ γ_i X_{t-i}
        X_unrestricted = []
        for t in range(lag, n):
            row = [1.0]
            for i in range(1, lag + 1):
                row.append(valid[t - i][1])
            for i in range(1, lag + 1):
                row.append(valid[t - i][0])
            X_unrestricted.append(row)

        ssr_r = _ols_ssr(Y_vec, X_restricted)
        ssr_u = _ols_ssr(Y_vec, X_unrestricted)

        if ssr_r < 0 or ssr_u < 0:
            continue

        p_restricted = lag + 1
        p_unrestricted = 2 * lag + 1
        df_num = p_unrestricted - p_restricted
        df_den = T - p_unrestricted
        if df_den <= 0:
            continue

        f_stat = ((ssr_r - ssr_u) / df_num) / (ssr_u / df_den) if ssr_u > 1e-12 else 0.0
        f_stat = max(0.0, f_stat)
        p_val = _f_pvalue(f_stat, df_num, df_den)

        results.append({
            'lag': lag,
            'f_stat': round(f_stat, 4),
            'p_value': round(p_val, 4),
            'significant': p_val < 0.05,
            'ssr_restricted': round(ssr_r, 4),
            'ssr_unrestricted': round(ssr_u, 4),
        })

    best = None
    for r in results:
        if best is None or r['p_value'] < best['p_value']:
            best = r

    return {
        'best_lag': best['lag'] if best else 0,
        'best_f_stat': best['f_stat'] if best else 0.0,
        'best_p_value': best['p_value'] if best else 1.0,
        'significant': best['significant'] if best else False,
        'all_lags': results,
        'direction': 'X → Y (Granger-causes)' if (best and best['significant']) else 'no evidence of Granger causality',
        'warning': None,
    }


# ═══════════════════════════════════════════════
#  INTERACTION EFFECT ANALYSIS
# ═══════════════════════════════════════════════

def _interaction_analysis(col_data, target_cols, numeric_cols):
    """Detect synergistic parameter pairs via interaction terms."""
    results = []
    for target in target_cols:
        if target not in col_data:
            continue
        y = col_data[target]

        individual_r = {}
        for col in numeric_cols:
            if col == target:
                continue
            r = pearson(y, col_data[col])['r']
            individual_r[col] = r

        candidates = [c for c in numeric_cols
                      if c != target and abs(individual_r.get(c, 0)) < 0.3]
        candidates.sort(key=lambda c: abs(individual_r.get(c, 0)), reverse=True)
        candidates = candidates[:min(len(candidates), 15)]

        for i in range(len(candidates)):
            for j in range(i + 1, len(candidates)):
                c1, c2 = candidates[i], candidates[j]
                x1, x2 = col_data[c1], col_data[c2]

                interaction = []
                valid_count = 0
                for k in range(len(y)):
                    v1 = _safe_float(x1[k])
                    v2 = _safe_float(x2[k])
                    vk = _safe_float(y[k])
                    if v1 is not None and v2 is not None and vk is not None:
                        interaction.append(v1 * v2)
                        valid_count += 1
                    else:
                        interaction.append(None)

                if valid_count < 20:
                    continue

                r_interaction = pearson(y, interaction)
                r1 = individual_r[c1]
                r2 = individual_r[c2]
                synergy_gain = abs(r_interaction['r']) - max(abs(r1), abs(r2))
                is_synergistic = synergy_gain > 0.2 and abs(r_interaction['r']) > 0.4

                if is_synergistic or abs(r_interaction['r']) > 0.3:
                    results.append({
                        'target': target,
                        'param_1': c1, 'param_2': c2,
                        'r_p1': round(r1, 4), 'r_p2': round(r2, 4),
                        'r_interaction': r_interaction['r'],
                        'p_interaction': r_interaction['p'],
                        'synergy_gain': round(synergy_gain, 4),
                        'synergistic': is_synergistic,
                        'interpretation': (
                            f"{c1} and {c2} individually have weak effects, but their "
                            f"interaction shows a strong relationship with {target}. "
                            f"This suggests a synergistic failure mode where both "
                            f"conditions must co-occur."
                            if is_synergistic else
                            f"Interaction effect detected but not definitively synergistic."
                        ),
                    })

    results.sort(key=lambda x: x['synergy_gain'], reverse=True)
    return results


# ═══════════════════════════════════════════════
#  MAIN ENTRY POINT
# ═══════════════════════════════════════════════

def run_correlation_analysis(rows, run_dir, *,
                             target_cols=None, predictor_cols=None,
                             exclude_cols=None, time_col=None,
                             group_col=None, max_lag=20, alpha=0.05,
                             data_view_mode='unknown'):
    """Full correlation analysis pipeline.

    Returns a dict suitable for merging into validate_report.json.
    """
    if target_cols is None:
        target_cols = []
    if predictor_cols is None:
        predictor_cols = []
    if exclude_cols is None:
        exclude_cols = set()

    # --- Detect numeric columns ---
    all_keys = list(rows[0].keys()) if rows else []
    numeric_cols = []
    for key in all_keys:
        if key == time_col:
            continue
        if key in exclude_cols:
            continue
        vals = [_safe_float(r.get(key)) for r in rows]
        valid_count = sum(1 for v in vals if v is not None)
        if valid_count > len(rows) * 0.5:
            numeric_cols.append(key)

    # --- Extract column data ---
    col_data = {}
    for col in numeric_cols:
        col_data[col] = [_safe_float(r.get(col)) for r in rows]

    # --- Validate time sorting ---
    sorting_validation = _validate_time_sorting(rows, time_col)

    # --- Determine effective targets and predictors ---
    effective_targets = []
    if data_view_mode == 'process_only':
        effective_targets = []
    elif target_cols:
        effective_targets = [t for t in target_cols if t in col_data]
    else:
        effective_targets = numeric_cols[:5]

    effective_predictors = [p for p in predictor_cols if p in col_data] if predictor_cols else None
    analysis_predictors = effective_predictors or [c for c in numeric_cols if c not in effective_targets]

    # --- Pearson Matrix ---
    pearson_matrix = {}
    for c1 in numeric_cols:
        pearson_matrix[c1] = {}
        for c2 in numeric_cols:
            pearson_matrix[c1][c2] = pearson(col_data[c1], col_data[c2])['r']

    # --- Spearman Matrix ---
    spearman_matrix = {}
    for c1 in numeric_cols:
        spearman_matrix[c1] = {}
        for c2 in numeric_cols:
            spearman_matrix[c1][c2] = spearman(col_data[c1], col_data[c2])['r']

    # --- Per-target detailed analysis ---
    target_analysis = {}
    for target in effective_targets:
        if target not in col_data:
            continue
        analysis = {
            'pearson_correlations': {},
            'spearman_correlations': {},
            'detrended_correlations': {},
            'lagged_ccf': {},
            'best_lags': {},
            'lag_window_consistency': {},
        }
        for col in analysis_predictors:
            if col == target:
                continue

            analysis['pearson_correlations'][col] = pearson(col_data[target], col_data[col])
            analysis['spearman_correlations'][col] = spearman(col_data[target], col_data[col])
            analysis['detrended_correlations'][col] = detrended_correlation(col_data[target], col_data[col])

            ccf = full_lag_ccf(col_data[target], col_data[col], max_lag)
            analysis['lagged_ccf'][col] = ccf

            best = find_best_lag(ccf)
            analysis['best_lags'][col] = best

            if best['lag'] != 0 and abs(best['r']) > 0.3:
                analysis['lag_window_consistency'][col] = lag_window_consistency(ccf, best['lag'], max_lag)

        target_analysis[target] = analysis

    # --- Multiple testing report ---
    pearson_corrs_by_target = {}
    for t in effective_targets:
        pearson_corrs_by_target[t] = target_analysis.get(t, {}).get('pearson_correlations', {})
    multi_test_report = _multiple_testing_report(pearson_corrs_by_target, alpha)

    # --- Stratified analysis ---
    stratified_results = None
    group_values = []
    if group_col and group_col in all_keys:
        group_data = [str(r.get(group_col, '')).strip() for r in rows]
        group_values = sorted(set(v for v in group_data if v))
        if len(group_values) >= 2:
            stratified_results = _stratified_analysis(col_data, effective_targets, group_data, group_values)

    # --- Mutual Information ---
    mi_matrix = {}
    if len(numeric_cols) <= 50:
        for c1 in numeric_cols:
            mi_matrix[c1] = {}
            for c2 in numeric_cols:
                if c1 == c2:
                    mi_matrix[c1][c2] = {'mi': 1.0, 'mi_normalized': 1.0}
                elif c1 < c2:
                    mi = _mutual_information(col_data[c1], col_data[c2])
                    mi_matrix[c1][c2] = mi
                    if c2 not in mi_matrix:
                        mi_matrix[c2] = {}
                    mi_matrix[c2][c1] = mi

    # --- Granger causality ---
    granger_results = None
    if sorting_validation.get('time_sorted') and time_col:
        granger_results = {}
        for target in effective_targets:
            if target not in col_data:
                continue
            granger_results[target] = {}
            for col in analysis_predictors:
                if col == target:
                    continue
                granger_results[target][col] = _granger_causality(
                    col_data[col], col_data[target], min(max_lag, 5))

    # --- Interaction effects ---
    interaction_results = _interaction_analysis(col_data, effective_targets, analysis_predictors)

    return {
        'data_summary': {
            'data_view_mode': data_view_mode,
            'total_rows': len(rows),
            'numeric_columns_total': len(numeric_cols),
            'numeric_columns_analyzed': len(numeric_cols),
            'excluded_columns': list(exclude_cols),
            'target_columns': effective_targets,
            'predictor_columns': analysis_predictors,
            'time_column': time_col,
            'group_column': group_col,
            'group_values': group_values,
            'max_lag': max_lag,
            'alpha': alpha,
        },
        'sorting_validation': sorting_validation,
        'correlation_matrices': {
            'pearson': pearson_matrix,
            'spearman': spearman_matrix,
        },
        'mutual_information': mi_matrix,
        'target_analysis': target_analysis,
        'granger_causality': granger_results,
        'interaction_effects': interaction_results,
        'multiple_testing': multi_test_report,
        'stratified_analysis': stratified_results,
    }
