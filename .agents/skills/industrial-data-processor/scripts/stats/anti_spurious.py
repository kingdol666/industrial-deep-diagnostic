"""Anti-spurious correlation validation.

Ported from stats_validate.mjs (JS).
Detects: Simpson's Paradox, outlier sensitivity, trend confounding,
         change-point detection, Pearson-Spearman divergence,
         distribution skewness, multiple testing warnings.

Usage: Typically called from stats/run.py, not directly.
"""

import json
import math
from pathlib import Path


# ═══════════════════════════════════════════════
#  BASIC STATISTICS (self-contained)
# ═══════════════════════════════════════════════

def _safe_float(v):
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


def _pearson_simple(x, y):
    """Pearson r only (no p-value) — fast version for validation loops."""
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
        return 0.0
    num = count * sxy - sx * sy
    den = math.sqrt((count * sx2 - sx * sx) * (count * sy2 - sy * sy))
    return num / den if den != 0 else 0.0


def _median(arr):
    clean = sorted(v for v in arr if v is not None and not (isinstance(v, float) and (math.isnan(v) or math.isinf(v))))
    if not clean:
        return float('nan')
    mid = len(clean) // 2
    if len(clean) % 2:
        return clean[mid]
    return (clean[mid - 1] + clean[mid]) / 2.0


def _iqr(arr):
    clean = sorted(v for v in arr if v is not None and not (isinstance(v, float) and (math.isnan(v) or math.isinf(v))))
    if len(clean) < 4:
        return {'q1': clean[0] if clean else 0, 'q3': clean[-1] if clean else 0,
                'iqr': (clean[-1] - clean[0]) if clean else 0}
    q1_idx = len(clean) // 4
    q3_idx = 3 * len(clean) // 4
    q1 = clean[q1_idx]
    q3 = clean[q3_idx]
    return {'q1': q1, 'q3': q3, 'iqr': q3 - q1}


def _skewness(arr):
    valid = [v for v in arr if v is not None and not (isinstance(v, float) and (math.isnan(v) or math.isinf(v)))]
    n = len(valid)
    if n < 3:
        return 0.0
    mean = sum(valid) / n
    variance = sum((v - mean) ** 2 for v in valid) / n
    std = math.sqrt(variance)
    if std == 0:
        return 0.0
    m3 = sum(((v - mean) / std) ** 3 for v in valid) / n
    return m3


def _compute_slope(t, vals):
    """Simple linear regression slope."""
    count = 0
    sx = sy = sxy = sx2 = 0.0
    for i, v in enumerate(vals):
        fv = _safe_float(v)
        if fv is None:
            continue
        sx += t[i]
        sy += fv
        sxy += t[i] * fv
        sx2 += t[i] * t[i]
        count += 1
    if count < 2:
        return 0.0
    return (count * sxy - sx * sy) / (count * sx2 - sx * sx + 1e-12)


# ═══════════════════════════════════════════════
#  OUTLIER SENSITIVITY
# ═══════════════════════════════════════════════

def _outlier_sensitivity(x, y, method='iqr'):
    """Remove outliers and recalculate correlation to check sensitivity."""
    valid_pairs = []
    for i in range(len(x)):
        xi = _safe_float(x[i])
        yi = _safe_float(y[i])
        if xi is not None and yi is not None:
            valid_pairs.append({'x': xi, 'y': yi})

    if len(valid_pairs) < 10:
        return None

    x_vals = [p['x'] for p in valid_pairs]
    y_vals = [p['y'] for p in valid_pairs]

    if method == 'iqr':
        iqr_x = _iqr(x_vals)
        iqr_y = _iqr(y_vals)
        low_x = iqr_x['q1'] - 1.5 * iqr_x['iqr']
        high_x = iqr_x['q3'] + 1.5 * iqr_x['iqr']
        low_y = iqr_y['q1'] - 1.5 * iqr_y['iqr']
        high_y = iqr_y['q3'] + 1.5 * iqr_y['iqr']
        outlier_mask = [p['x'] < low_x or p['x'] > high_x or p['y'] < low_y or p['y'] > high_y
                        for p in valid_pairs]
    else:
        n = len(valid_pairs)
        trim_n = n // 20  # 5%
        outlier_mask = [False] * n
        sorted_x = sorted(enumerate(x_vals), key=lambda iv: iv[1])
        for k in range(trim_n):
            outlier_mask[sorted_x[k][0]] = True
            outlier_mask[sorted_x[n - 1 - k][0]] = True
        sorted_y = sorted(enumerate(y_vals), key=lambda iv: iv[1])
        for k in range(trim_n):
            outlier_mask[sorted_y[k][0]] = True
            outlier_mask[sorted_y[n - 1 - k][0]] = True

    clean_x = [p['x'] for i, p in enumerate(valid_pairs) if not outlier_mask[i]]
    clean_y = [p['y'] for i, p in enumerate(valid_pairs) if not outlier_mask[i]]
    n_removed = len(valid_pairs) - len(clean_x)

    full_r = _pearson_simple(x_vals, y_vals)
    clean_r = _pearson_simple(clean_x, clean_y) if clean_x else 0.0

    return {
        'full_r': round(full_r, 4),
        'clean_r': round(clean_r, 4),
        'r_change': round(clean_r - full_r, 4),
        'r_change_pct': round(((clean_r - full_r) / abs(full_r)) * 100, 1) if full_r != 0 else 0.0,
        'outliers_removed': n_removed,
        'outlier_pct': round((n_removed / len(valid_pairs)) * 100, 1),
        'outlier_driven': abs(clean_r - full_r) / (abs(full_r) + 1e-12) > 0.5,
    }


# ═══════════════════════════════════════════════
#  LEAVE-ONE-OUT LEVERAGE CHECK
# ═══════════════════════════════════════════════

def _leave_one_out_leverage(x, y, threshold=0.3):
    """Check correlation stability by removing each point one at a time.

    For |r| >= threshold: ensure no single point shifts r by more than 0.15.
    """
    valid_pairs = []
    for i in range(len(x)):
        xi = _safe_float(x[i])
        yi = _safe_float(y[i])
        if xi is not None and yi is not None:
            valid_pairs.append({'x': xi, 'y': yi})

    if len(valid_pairs) < 10:
        return None

    x_vals = [p['x'] for p in valid_pairs]
    y_vals = [p['y'] for p in valid_pairs]
    n = len(x_vals)

    full_r = _pearson_simple(x_vals, y_vals)

    if abs(full_r) < threshold:
        return {'full_r': round(full_r, 4), 'leveraged': False,
                'max_shift': 0.0, 'message': 'Below threshold, no leverage check needed.'}

    max_shift = 0.0
    max_shift_idx = -1
    for i in range(n):
        loo_x = x_vals[:i] + x_vals[i + 1:]
        loo_y = y_vals[:i] + y_vals[i + 1:]
        loo_r = _pearson_simple(loo_x, loo_y)
        shift = abs(loo_r - full_r)
        if shift > max_shift:
            max_shift = shift
            max_shift_idx = i

    leveraged = max_shift > 0.15

    return {
        'full_r': round(full_r, 4),
        'leveraged': leveraged,
        'max_shift': round(max_shift, 4),
        'max_shift_idx': max_shift_idx,
        'message': (
            f'Correlation is leveraged by a single point (max shift={max_shift:.3f}). '
            f'Report should use Spearman or flagged as outlier-sensitive.'
            if leveraged else
            'Leave-one-out check passed: correlation is robust to single-point removal.'
        ),
    }


# ═══════════════════════════════════════════════
#  DISTRIBUTION ANALYSIS
# ═══════════════════════════════════════════════

def _distribution_check(col_data):
    """Check skewness and recommend Pearson vs Spearman per column."""
    results = {}
    for name, values in col_data.items():
        valid = [v for v in values if v is not None and not (isinstance(v, float) and (math.isnan(v) or math.isinf(v)))]
        if len(valid) < 3:
            continue
        sk = _skewness(valid)
        med = _median(valid)
        mean = sum(valid) / len(valid)
        mm_ratio = mean / med if med != 0 else (1.0 if mean == 0 else float('inf'))

        abs_sk = abs(sk)
        if abs_sk > 2:
            rec = 'SPEARMAN_RECOMMENDED: Heavy skew. Spearman correlation is more reliable than Pearson.'
        elif abs_sk > 1:
            rec = 'MODERATE_SKEW: Consider Spearman as robustness check alongside Pearson.'
        else:
            rec = 'NORMAL_ENOUGH: Pearson correlation is appropriate.'

        results[name] = {
            'skewness': round(sk, 3),
            'mean_median_ratio': round(mm_ratio, 3),
            'is_heavily_skewed': abs_sk > 2 or mm_ratio > 3 or mm_ratio < 0.33,
            'pearson_appropriate': abs_sk < 1.5 and 0.5 < mm_ratio < 2,
            'recommendation': rec,
        }
    return results


# ═══════════════════════════════════════════════
#  PARTIAL CORRELATION (confounder check)
# ═══════════════════════════════════════════════

def _partial_correlation(x, y, z):
    """Partial correlation r_xy.z — controls for variable z."""
    valid = []
    for i in range(len(x)):
        xi = _safe_float(x[i])
        yi = _safe_float(y[i])
        zi = _safe_float(z[i])
        if xi is not None and yi is not None and zi is not None:
            valid.append({'x': xi, 'y': yi, 'z': zi})
    if len(valid) < 5:
        return None

    rxy = _pearson_simple([p['x'] for p in valid], [p['y'] for p in valid])
    rxz = _pearson_simple([p['x'] for p in valid], [p['z'] for p in valid])
    ryz = _pearson_simple([p['y'] for p in valid], [p['z'] for p in valid])

    denom = math.sqrt((1 - rxz * rxz) * (1 - ryz * ryz))
    if denom < 1e-12:
        return None

    r_partial = (rxy - rxz * ryz) / denom
    return {
        'r_partial': round(r_partial, 4),
        'r_original': round(rxy, 4),
        'r_change': round(r_partial - rxy, 4),
        'confound_suspect': abs(r_partial - rxy) / (abs(rxy) + 1e-12) > 0.4,
    }


# ═══════════════════════════════════════════════
#  TIME TREND CONFOUNDING
# ═══════════════════════════════════════════════

def _time_trend_confounding(x, y):
    """Check if two variables share a common time trend."""
    n = len(x)
    t = list(range(n))

    x_trend = _pearson_simple(t, x)
    y_trend = _pearson_simple(t, y)
    raw_r = _pearson_simple(x, y)

    # Linear detrend
    x_slope = _compute_slope(t, x)
    y_slope = _compute_slope(t, y)

    x_valid = [v for v in x if _safe_float(v) is not None]
    y_valid = [v for v in y if _safe_float(v) is not None]
    x_mean = sum(x_valid) / len(x_valid) if x_valid else 0.0
    y_mean = sum(y_valid) / len(y_valid) if y_valid else 0.0

    x_detrended = []
    y_detrended = []
    for i in range(n):
        xv = _safe_float(x[i])
        yv = _safe_float(y[i])
        x_detrended.append(xv - (x_slope * i + x_mean - x_slope * (n / 2)) if xv is not None else None)
        y_detrended.append(yv - (y_slope * i + y_mean - y_slope * (n / 2)) if yv is not None else None)

    detrended_r = _pearson_simple(x_detrended, y_detrended)

    attenuation_pct = ((raw_r - detrended_r) / abs(raw_r)) * 100 if raw_r != 0 else 0.0

    return {
        'raw_r': round(raw_r, 4),
        'detrended_r': round(detrended_r, 4),
        'x_time_trend_r': round(x_trend, 4),
        'y_time_trend_r': round(y_trend, 4),
        'attenuation_pct': round(attenuation_pct, 1),
        'trend_confounded': abs(raw_r - detrended_r) / (abs(raw_r) + 1e-12) > 0.4,
    }


# ═══════════════════════════════════════════════
#  SIMPSON'S PARADOX DEEP CHECK
# ═══════════════════════════════════════════════

def _simpson_paradox_check(target_data, param_data, group_data, group_values):
    """Deep Simpson's Paradox check per target-parameter pair."""
    full_r = _pearson_simple(target_data, param_data)
    strata = []

    for g_val in group_values:
        indices = [i for i, g in enumerate(group_data) if str(g) == str(g_val)]
        if len(indices) < 10:
            continue

        x_sub = [target_data[i] for i in indices if _safe_float(target_data[i]) is not None]
        y_sub = [param_data[i] for i in indices if _safe_float(param_data[i]) is not None]
        min_n = min(len(x_sub), len(y_sub))
        if min_n < 3:
            continue
        r = _pearson_simple(x_sub[:min_n], y_sub[:min_n])

        direction = 'positive' if r > 0.1 else ('negative' if r < -0.1 else 'neutral')
        strata.append({
            'group': g_val,
            'r': round(r, 4),
            'n': len(indices),
            'direction': direction,
        })

    if len(strata) < 2:
        return None

    directions = [s['direction'] for s in strata]
    has_positive = 'positive' in directions
    has_negative = 'negative' in directions
    direction_reversal = has_positive and has_negative

    total_n = sum(s['n'] for s in strata)
    weighted_r = sum(s['r'] * s['n'] for s in strata) / total_n if total_n > 0 else 0.0

    if direction_reversal:
        paradox_type = 'DIRECTION_REVERSAL'
    elif abs(weighted_r - full_r) / (abs(full_r) + 1e-12) > 0.5:
        paradox_type = 'STRONG_ATTENUATION'
    elif abs(weighted_r - full_r) / (abs(full_r) + 1e-12) > 0.3:
        paradox_type = 'MODERATE_ATTENUATION'
    else:
        paradox_type = 'CONSISTENT'

    return {
        'full_r': round(full_r, 4),
        'weighted_strata_r': round(weighted_r, 4),
        'direction_reversal': direction_reversal,
        'paradox_type': paradox_type,
        'strata': strata,
    }


# ═══════════════════════════════════════════════
#  CHANGE-POINT DETECTION (PELT algorithm)
# ═══════════════════════════════════════════════

def _detect_change_points(values, min_segment_length=10, penalty=None):
    """PELT (Pruned Exact Linear Time) for mean shift detection."""
    valid = []
    for i, v in enumerate(values):
        fv = _safe_float(v)
        if fv is not None:
            valid.append({'idx': i, 'v': fv})

    n = len(valid)
    if n < min_segment_length * 2:
        return {'change_points': [], 'n_segments': 1, 'warning': 'insufficient data'}

    y = [v['v'] for v in valid]
    mean = sum(y) / n
    variance = sum((v - mean) ** 2 for v in y) / n
    pen = penalty if penalty is not None else 2 * math.log(n) * max(variance, 1e-10)

    # Precompute cumulative sums for O(1) segment cost
    cum_sum = [0.0]
    cum_sum_sq = [0.0]
    for v in y:
        cum_sum.append(cum_sum[-1] + v)
        cum_sum_sq.append(cum_sum_sq[-1] + v * v)

    def segment_cost(start, end):
        length = end - start
        if length < 2:
            return 0.0
        s = cum_sum[end] - cum_sum[start]
        sq = cum_sum_sq[end] - cum_sum_sq[start]
        seg_mean = s / length
        seg_var = max(sq / length - seg_mean * seg_mean, 1e-10)
        return length * math.log(seg_var) / 2.0

    # PELT dynamic programming
    F = [float('inf')] * (n + 1)
    F[0] = -pen
    cp = [0] * (n + 1)
    R = [0]

    for t in range(min_segment_length, n + 1):
        best_cost = float('inf')
        best_tau = 0
        for tau in R:
            if t - tau < min_segment_length:
                continue
            cost = F[tau] + segment_cost(tau, t) + pen
            if cost < best_cost:
                best_cost = cost
                best_tau = tau
        F[t] = best_cost
        cp[t] = best_tau
        R = [tau for tau in R if t - tau < min_segment_length or
             F[tau] + segment_cost(tau, t) < F[t]]
        R.append(t)

    # Backtrack
    change_points = []
    t = n
    while t > 0:
        prev = cp[t]
        if prev > 0:
            change_points.insert(0, valid[prev]['idx'])
        t = prev

    # Build segments
    segments = []
    prev_idx = valid[0]['idx']
    all_breaks = change_points + [valid[-1]['idx'] + 1]
    for break_idx in all_breaks:
        seg_vals = [v for v in valid if prev_idx <= v['idx'] < break_idx]
        if len(seg_vals) >= min_segment_length:
            seg_mean = sum(v['v'] for v in seg_vals) / len(seg_vals)
            segments.append({
                'start_idx': seg_vals[0]['idx'],
                'end_idx': seg_vals[-1]['idx'],
                'length': len(seg_vals),
                'mean': round(seg_mean, 4),
            })
        prev_idx = break_idx

    # Analyze regime shifts
    regime_shifts = []
    for i in range(1, len(segments)):
        prev = segments[i - 1]
        curr = segments[i]
        mean_shift = abs(curr['mean'] - prev['mean']) / (abs(prev['mean']) + 1e-12)
        regime_shifts.append({
            'position': curr['start_idx'],
            'from_mean': prev['mean'],
            'to_mean': curr['mean'],
            'relative_change_pct': round(mean_shift * 100, 1),
            'significant': mean_shift > 0.1,
        })

    sig_shifts = [r for r in regime_shifts if r['significant']]
    return {
        'change_points': change_points,
        'n_segments': len(segments),
        'n_changes': len(change_points),
        'segments': segments,
        'regime_shifts': regime_shifts,
        'has_regime_change': len(sig_shifts) > 0,
        'warning': (
            f"Detected {len(sig_shifts)} significant regime shifts. "
            f"Correlations computed across regime boundaries may be spurious. "
            f"Consider analyzing each segment separately."
            if sig_shifts else None
        ),
    }


# ═══════════════════════════════════════════════
#  MAIN VALIDATION ENTRY POINT
# ═══════════════════════════════════════════════

def run_anti_spurious_checks(rows, run_dir, *,
                             correlation_result=None,
                             target_cols=None, group_col=None, time_col=None):
    """Full anti-spurious validation pipeline.

    Args:
        rows: list of dicts (cleaned data)
        run_dir: Path to run directory
        correlation_result: output from core_stats.run_correlation_analysis
        target_cols: explicit target columns
        group_col: grouping column
        time_col: time column

    Returns: validate_report dict.
    """
    if target_cols is None:
        target_cols = []

    # --- Extract numeric columns ---
    all_keys = list(rows[0].keys()) if rows else []
    numeric_cols = []
    for key in all_keys:
        if key == time_col:
            continue
        vals = [_safe_float(r.get(key)) for r in rows]
        valid_count = sum(1 for v in vals if v is not None)
        if valid_count > len(rows) * 0.5:
            numeric_cols.append(key)

    col_data = {}
    for col in numeric_cols:
        col_data[col] = [_safe_float(r.get(col)) for r in rows]

    # Determine effective targets
    if correlation_result:
        targets = correlation_result.get('data_summary', {}).get('target_columns', numeric_cols[:5])
    else:
        targets = target_cols if target_cols else numeric_cols[:5]
    targets = [t for t in targets if t in col_data]

    # --- 1. Distribution Check ---
    distributions = _distribution_check(col_data)

    # --- 2. Outlier Sensitivity for Key Correlations ---
    outlier_checks = []
    for target in targets:
        analysis = correlation_result.get('target_analysis', {}).get(target, {}) if correlation_result else {}
        pearson_corrs = analysis.get('pearson_correlations', {})
        corr_entries = [(k, v) for k, v in pearson_corrs.items()
                        if isinstance(v, dict) and abs(v.get('r', 0)) > 0.2]
        corr_entries.sort(key=lambda x: abs(x[1].get('r', 0)), reverse=True)
        for param, corr_info in corr_entries[:5]:
            if param not in col_data:
                continue
            sensitivity = _outlier_sensitivity(col_data[target], col_data[param], 'iqr')
            if sensitivity:
                outlier_checks.append({
                    'target': target, 'parameter': param,
                    'full_r': sensitivity['full_r'], 'clean_r': sensitivity['clean_r'],
                    'r_change_pct': sensitivity['r_change_pct'],
                    'outliers_removed': sensitivity['outliers_removed'],
                    'outlier_driven': sensitivity['outlier_driven'],
                    'severity': 'SERIOUS' if sensitivity['outlier_driven'] else 'OK',
                })

    # --- 2b. Leave-One-Out Leverage for |r| >= 0.3 ---
    loo_results = []
    for target in targets:
        analysis = correlation_result.get('target_analysis', {}).get(target, {}) if correlation_result else {}
        pearson_corrs = analysis.get('pearson_correlations', {})
        for param, corr_info in pearson_corrs.items():
            if not isinstance(corr_info, dict):
                continue
            if abs(corr_info.get('r', 0)) < 0.3:
                continue
            if param not in col_data:
                continue
            loo = _leave_one_out_leverage(col_data[target], col_data[param])
            if loo:
                loo_results.append({
                    'target': target, 'parameter': param,
                    'full_r': loo['full_r'], 'leveraged': loo['leveraged'],
                    'max_shift': loo['max_shift'], 'message': loo['message'],
                    'severity': 'SERIOUS' if loo['leveraged'] else 'OK',
                })

    # --- 3. Time Trend Confounding ---
    trend_checks = []
    for target in targets:
        analysis = correlation_result.get('target_analysis', {}).get(target, {}) if correlation_result else {}
        pearson_corrs = analysis.get('pearson_correlations', {})
        corr_entries = [(k, v) for k, v in pearson_corrs.items()
                        if isinstance(v, dict) and abs(v.get('r', 0)) > 0.25]
        corr_entries.sort(key=lambda x: abs(x[1].get('r', 0)), reverse=True)
        for param, _ in corr_entries[:8]:
            if param not in col_data:
                continue
            trend = _time_trend_confounding(col_data[target], col_data[param])
            if trend and trend['trend_confounded']:
                trend_checks.append({
                    'target': target, 'parameter': param,
                    'raw_r': trend['raw_r'], 'detrended_r': trend['detrended_r'],
                    'attenuation_pct': trend['attenuation_pct'],
                    'x_time_trend_r': trend['x_time_trend_r'],
                    'y_time_trend_r': trend['y_time_trend_r'],
                })

    # --- 4. Simpson's Paradox via Group Column ---
    simpson_results = []
    if group_col and group_col in all_keys:
        group_data = [str(r.get(group_col, '')).strip() for r in rows]
        group_values = sorted(set(v for v in group_data if v))

        dominant = max(group_values, key=lambda g: group_data.count(g)) if group_values else None
        dominant_count = group_data.count(dominant) if dominant else 0

        for target in targets:
            analysis = correlation_result.get('target_analysis', {}).get(target, {}) if correlation_result else {}
            pearson_corrs = analysis.get('pearson_correlations', {})
            top_params = [(k, v) for k, v in pearson_corrs.items()
                          if isinstance(v, dict) and abs(v.get('r', 0)) > 0.2]
            top_params.sort(key=lambda x: abs(x[1].get('r', 0)), reverse=True)

            for param, _ in top_params[:6]:
                if param not in col_data:
                    continue
                # Check if stats already computed stratified analysis
                from_stats = None
                if correlation_result and correlation_result.get('stratified_analysis'):
                    from_stats = next((s for s in correlation_result['stratified_analysis']
                                       if s.get('target') == target and s.get('parameter') == param), None)

                if from_stats:
                    simpson_results.append(from_stats)
                else:
                    check = _simpson_paradox_check(col_data[target], col_data[param], group_data, group_values)
                    if check and check['paradox_type'] != 'CONSISTENT':
                        simpson_results.append({
                            'target': target, 'parameter': param,
                            'full_r': check['full_r'],
                            'weighted_strata_r': check['weighted_strata_r'],
                            'paradox_type': check['paradox_type'],
                            'direction_reversal': check['direction_reversal'],
                            'strata': check['strata'],
                        })

        if simpson_results:
            simpson_results.append({
                '_meta': {
                    'group_column': group_col,
                    'n_groups': len(group_values),
                    'dominant_group': dominant,
                    'dominant_pct': round((dominant_count / len(rows)) * 100, 1) if rows else 0,
                }
            })

    # --- 5. Lag Analysis Sorting Warning ---
    sorting_validation = (correlation_result.get('sorting_validation', {})
                          if correlation_result else {'time_sorted': None})
    lag_warning = None
    if sorting_validation.get('time_sorted') is False:
        lag_warning = {
            'severity': 'FATAL',
            'message': 'Data is NOT sorted by time. All lag correlation results are likely sorting artifacts, not genuine temporal relationships.',
            'action': 'Re-sort data by time column and re-run lag analysis.',
            'affected_claims': 'Any hypothesis relying on lagged correlations (especially negative lags) must be re-evaluated after re-sorting.',
        }

    # --- 6. Multiple Testing Warning ---
    multi_test = correlation_result.get('multiple_testing', {}) if correlation_result else {}
    multi_test_warning = None
    if multi_test.get('nominally_significant_p0_05', 0) and multi_test.get('expected_false_positives', 0):
        ratio = multi_test['nominally_significant_p0_05'] / max(multi_test['expected_false_positives'], 1)
        if ratio < 2:
            multi_test_warning = {
                'severity': 'MODERATE',
                'message': (
                    f"Only {multi_test['nominally_significant_p0_05']} significant results vs "
                    f"{multi_test['expected_false_positives']:.1f} expected false positives. "
                    f"Many 'significant' correlations may be chance findings."
                ),
                'action': 'Focus interpretation on correlations that survive Bonferroni correction or have |r| > 0.5 with p < 0.001.',
            }

    # --- 7. Change-Point Detection ---
    change_point_results = {}
    if time_col:
        for target in targets:
            if target not in col_data:
                continue
            cp = _detect_change_points(col_data[target])
            if cp and cp['n_changes'] > 0:
                change_point_results[target] = cp

        # Also check top predictor params
        analysis = correlation_result.get('target_analysis', {}).get(targets[0], {}) if targets and correlation_result else {}
        if analysis:
            pearson_corrs = analysis.get('pearson_correlations', {})
            top_params = [(k, v) for k, v in pearson_corrs.items()
                          if isinstance(v, dict) and abs(v.get('r', 0)) > 0.3]
            top_params.sort(key=lambda x: abs(x[1].get('r', 0)), reverse=True)
            for param, _ in top_params[:5]:
                if param not in col_data or param in change_point_results:
                    continue
                cp = _detect_change_points(col_data[param])
                if cp and cp['n_changes'] > 0:
                    change_point_results[param] = cp

    # --- 8. Pearson vs Spearman Divergence ---
    spearman_warnings = []
    for target in targets:
        analysis = correlation_result.get('target_analysis', {}).get(target, {}) if correlation_result else {}
        for param, p_corr in analysis.get('pearson_correlations', {}).items():
            s_corr = analysis.get('spearman_correlations', {}).get(param, {})
            if not isinstance(p_corr, dict) or not isinstance(s_corr, dict):
                continue
            if abs(p_corr.get('r', 0)) < 0.2:
                continue
            divergence = abs(p_corr['r'] - s_corr['r'])
            if divergence > 0.15:
                spearman_warnings.append({
                    'target': target, 'parameter': param,
                    'pearson_r': p_corr['r'],
                    'spearman_r': s_corr['r'],
                    'divergence': round(divergence, 3),
                    'severity': 'SERIOUS' if divergence > 0.3 else 'MODERATE',
                    'interpretation': (
                        'Large Pearson-Spearman divergence indicates outliers dominate the Pearson correlation. Use Spearman for interpretation.'
                        if divergence > 0.3 else
                        'Moderate divergence. Consider checking scatter plot for nonlinearity or outlier influence.'
                    ),
                })

    # --- Assemble Report ---
    fatal_count = 1 if lag_warning else 0
    # Count simpson CRITICAL entries (exclude _meta)
    simpson_critical = sum(
        1 for s in simpson_results
        if isinstance(s, dict) and not s.get('_meta') and
        (s.get('simpson_paradox') or s.get('direction_reversal') or s.get('severity') == 'CRITICAL')
    )
    serious_count = (
        simpson_critical +
        sum(1 for c in outlier_checks if c.get('outlier_driven')) +
        sum(1 for w in spearman_warnings if w.get('severity') == 'SERIOUS') +
        sum(1 for v in change_point_results.values() if v.get('has_regime_change'))
    )
    # Count simpson SERIOUS but not CRITICAL
    simpson_serious_non_critical = sum(
        1 for s in simpson_results
        if isinstance(s, dict) and not s.get('_meta') and
        s.get('severity') == 'SERIOUS' and
        not s.get('simpson_paradox') and not s.get('direction_reversal')
    )
    moderate_count = len(trend_checks) + simpson_serious_non_critical

    if fatal_count > 0:
        overall_validity = 'FATAL_ISSUES \u2014 Fundamental data problems must be fixed before diagnosis can be trusted.'
    elif serious_count > 2:
        overall_validity = 'SERIOUS_CONCERNS \u2014 Multiple statistical robustness issues detected. Key correlations should be re-verified before drawing causal conclusions.'
    elif serious_count > 0 or moderate_count > 3:
        overall_validity = 'MODERATE_CONCERNS \u2014 Some statistical issues found. Flag them in the report and adjust confidence scores accordingly.'
    elif moderate_count > 0:
        overall_validity = 'MINOR_CONCERNS \u2014 Minor statistical caveats. Report should mention them but overall diagnosis direction is supported.'
    else:
        overall_validity = 'ROBUST \u2014 Statistical evidence passes robustness checks. Correlation findings are stable.'

    import datetime
    validate_report = {
        'generated_at': datetime.datetime.now().isoformat(),
        'summary': {
            'total_targets': len(targets),
            'total_parameters': len(numeric_cols) - len(targets),
            'skew_affected_columns': sum(1 for d in distributions.values() if d.get('is_heavily_skewed')),
            'outlier_driven_correlations': sum(1 for c in outlier_checks if c.get('outlier_driven')),
            'trend_confounded_correlations': len(trend_checks),
            'simpson_paradox_findings': sum(
                1 for s in simpson_results
                if isinstance(s, dict) and not s.get('_meta') and
                (s.get('simpson_paradox') or s.get('direction_reversal'))
            ),
            'spearman_divergence_findings': sum(1 for w in spearman_warnings if w.get('severity') == 'SERIOUS'),
            'change_points_detected': sum(1 for v in change_point_results.values() if v.get('has_regime_change')),
            'fatal_issues': fatal_count,
            'serious_count': serious_count,
            'moderate_count': moderate_count,
        },
        'sorting_validation': sorting_validation,
        'lag_warning': lag_warning,
        'distribution_analysis': distributions,
        'outlier_sensitivity': outlier_checks,
        'leave_one_out_leverage': loo_results,
        'time_trend_confounding': trend_checks,
        'simpson_paradox': simpson_results,
        'spearman_divergence': spearman_warnings,
        'change_point_detection': change_point_results,
        'multiple_testing_warning': multi_test_warning,
        'overall_validity': overall_validity,
    }

    return validate_report
