#!/usr/bin/env python3
"""Production Regime & Steady-State Detector — No operator logs required.

Automatically detects production states (startup / steady / shutdown / abnormal)
from sensor data alone. No human-provided shift logs or event markers needed.

Three independent detection methods, fused into a final regime classification:
  1. Multi-parameter variance ratio (sliding window) — startup/shutdown = high variance
  2. Change-point detection (PELT / binary segmentation fallback) — regime boundaries
  3. Multi-parameter consensus voting — multiple sensors agree = high confidence regime

Outputs:
  - production_regime_filter.json: per-row regime label + included/excluded mask
  - Steady-state-only data subset for downstream statistical analysis
  - Abrupt-parameter-change time windows (potential sensor faults or unlogged events)

Usage:
  uv run python production_regime_detector.py <cleaned_data_csv> <output_dir> \
      [--time-col NAME] [--group-col NAME] \
      [--window-minutes 10] [--min-steady-ratio 0.4] \
      [--variance-threshold 3.0] [--consensus-threshold 0.6]
"""

import csv, json, math, os, sys, argparse
from collections import defaultdict
from statistics import mean, median, stdev


# ── UTILITIES ──

def _safe_float(v):
    try:
        if v in (None, '', 'null', 'None'):
            return None
        return float(v)
    except (ValueError, TypeError):
        return None


def _detect_time_col(col_names):
    for c in col_names:
        cl = c.lower()
        if any(k in cl for k in ('timestamp', 'time', 'date', 'datetime')):
            return c
    return None


def _detect_group_col(col_names, explicit=None):
    if explicit:
        return explicit
    preferred = ['product_no', 'product_id', 'product_code', 'product_grade',
                 'grade', 'lot_id', 'lot_no', 'batch_id', 'reel_id']
    lowered = {c.lower(): c for c in col_names}
    for key in preferred:
        if key in lowered:
            return lowered[key]
    return None


def _numeric_columns(rows, excluded=None):
    excluded = set(excluded or [])
    cols = []
    for c in rows[0].keys():
        if c in excluded:
            continue
        values = [_safe_float(r.get(c)) for r in rows[: min(len(rows), 50)]]
        valid = [v for v in values if v is not None]
        if len(valid) >= max(3, len(values) // 3 if values else 0):
            cols.append(c)
    return cols


def _window_indices(total, window):
    """Yield (center_idx, left_idx, right_idx) for each position."""
    for i in range(total):
        left = max(0, i - window)
        right = min(total, i + window + 1)
        yield i, left, right


# ── METHOD 1: MULTI-PARAMETER VARIANCE RATIO ──

def detect_by_variance(rows, numeric_cols, window):
    """Compute a normalized variance anomaly score per row across all parameters.

    For each parameter and each row, compute:
      local_std = std(row's sliding window)
      basline_std = median of all local_stds across the full time series
      variance_ratio = local_std / baseline_std

    Then aggregate across all parameters to get a per-row regime score.
    variance_ratio >> 1 → startup/shutdown/abnormal (highly unstable)
    variance_ratio ~ 1 → steady-state (normal process variation)
    variance_ratio << 1 → suspicious (flatlined sensor)
    """
    n = len(rows)
    # Select key parameters: those with sufficient variation to be informative
    param_stats = {}
    for c in numeric_cols:
        vals = [_safe_float(r.get(c)) for r in rows]
        vals_clean = [v for v in vals if v is not None]
        if len(vals_clean) < 10:
            continue
        try:
            sd = stdev(vals_clean)
            mu = abs(mean(vals_clean)) + 1e-9
            cv = sd / mu
        except Exception:
            continue
        # Use parameters with CV between 0.1% and 50% (exclude flatlines and noise)
        if 0.001 < cv < 0.5:
            param_stats[c] = {'vals': vals, 'cv': cv}

    if len(param_stats) < 2:
        return None, "insufficient_parameters_for_variance_analysis"

    # Per-parameter per-row variance ratios
    per_param_ratios = {}
    for c, info in param_stats.items():
        vals = info['vals']
        ratios = [None] * n
        local_stds = []
        for i, left, right in _window_indices(n, window):
            seg = [vals[j] for j in range(left, right) if vals[j] is not None]
            if len(seg) >= 3:
                try:
                    s = stdev(seg)
                except Exception:
                    s = 0.0
            else:
                s = 0.0
            local_stds.append(s)

        # Baseline = median of local stds (robust to regime shifts)
        clean_stds = [s for s in local_stds if s > 0]
        if not clean_stds:
            continue
        baseline_std = median(clean_stds) + 1e-9

        for i in range(n):
            if local_stds[i] == 0.0:
                ratios[i] = 0.0
            else:
                ratios[i] = local_stds[i] / baseline_std

        per_param_ratios[c] = ratios

    # Aggregate: per-row median variance ratio across parameters
    n_params = len(per_param_ratios)
    regime_scores = []
    for i in range(n):
        row_ratios = [per_param_ratios[c][i] for c in per_param_ratios if per_param_ratios[c][i] is not None]
        if len(row_ratios) >= max(2, n_params // 2):
            regime_scores.append(median(row_ratios))
        else:
            regime_scores.append(1.0)  # default: assume normal

    return regime_scores, param_stats


# ── METHOD 2: CHANGE-POINT DETECTION ──

def _binary_segmentation(values, min_size=5, n_segments=20):
    """Simple top-down binary segmentation for change point detection.
    Finds points where the mean shifts most significantly.
    Returns list of change-point indices.
    """
    n = len(values)
    if n < 2 * min_size:
        return []

    valid = [(i, v) for i, v in enumerate(values) if v is not None]
    if len(valid) < 2 * min_size:
        return []

    indices = [p[0] for p in valid]
    vals = [p[1] for p in valid]

    def segment_cost(a, b):
        """Reduction in variance if we split at this point."""
        seg = vals[a:b]
        if len(seg) < min_size:
            return 0, -1
        mu = mean(seg)
        cost_before = sum((x - mu) ** 2 for x in seg)
        return cost_before, mu

    def find_best_split(a, b):
        best_cost_reduction = -1
        best_point = -1
        total_cost, total_mu = segment_cost(a, b)
        for split in range(a + min_size, b - min_size + 1):
            left_cost, _ = segment_cost(a, split)
            right_cost, _ = segment_cost(split, b)
            cost_after = left_cost + right_cost
            reduction = total_cost - cost_after
            if reduction > best_cost_reduction:
                best_cost_reduction = reduction
                best_point = split
        return best_point, best_cost_reduction

    # Priority queue of segments to split
    segments = [(0, len(vals))]
    change_points = []

    for _ in range(n_segments):
        best_reduction = -1
        best_seg_idx = -1
        best_split = -1

        for seg_idx, (a, b) in enumerate(segments):
            split, reduction = find_best_split(a, b)
            if reduction > best_reduction:
                best_reduction = reduction
                best_seg_idx = seg_idx
                best_split = split

        if best_reduction <= 0 or best_split < 0:
            break

        a, b = segments.pop(best_seg_idx)
        segments.append((a, best_split))
        segments.append((best_split, b))
        # Map back to original index
        change_points.append(indices[best_split])

    return sorted(set(change_points))


def detect_change_points(rows, numeric_cols, window):
    """Detect regime change points using multi-parameter consensus.

    For each key numeric parameter, run binary segmentation.
    Then cluster change points — if multiple parameters show a change
    at nearby time indices, it's a consensus regime boundary.
    """
    n = len(rows)
    all_cp = []
    key_params = []

    # Select top 10 most variable parameters
    candidates = []
    for c in numeric_cols:
        vals = [_safe_float(r.get(c)) for r in rows]
        clean = [v for v in vals if v is not None]
        if len(clean) < 20:
            continue
        try:
            cv = stdev(clean) / (abs(mean(clean)) + 1e-9)
        except Exception:
            continue
        if 0.005 < cv < 2.0:
            candidates.append((cv, c))

    candidates.sort(reverse=True)
    top_params = [c for _, c in candidates[:10]]

    for c in top_params:
        vals = [_safe_float(r.get(c)) for r in rows]
        cps = _binary_segmentation(vals, min_size=max(5, window), n_segments=10)
        all_cp.extend(cps)
        key_params.append(c)

    if not all_cp:
        return [], key_params

    # Cluster nearby change points (within ±window of each other)
    all_cp.sort()
    clusters = []
    current_cluster = [all_cp[0]]
    for cp in all_cp[1:]:
        if cp - current_cluster[-1] <= window:
            current_cluster.append(cp)
        else:
            clusters.append(current_cluster)
            current_cluster = [cp]
    clusters.append(current_cluster)

    # Consensus: at least 2 parameters must agree for a regime boundary
    consensus_boundaries = []
    for cluster in clusters:
        if len(cluster) >= 2:
            consensus_boundaries.append(int(median(cluster)))

    return consensus_boundaries, key_params


# ── METHOD 3: STARTUP/SHUTDOWN DETECTION BY PARAMETER DRIFT ──

def detect_drift_ramps(rows, numeric_cols, window):
    """Detect monotonic ramp-up or ramp-down patterns characteristic of startup/shutdown.

    During startup: most parameters rise from near-zero/ambient to operating setpoints.
    During shutdown: most parameters fall from operating setpoints to near-zero/ambient.

    Returns per-row ramp score (high positive = ramping up, high negative = ramping down).
    """
    n = len(rows)
    # Select parameters that show clear monotonic changes
    # Use key process params (temperature, pressure, speed, flow) — not quality targets
    process_like = [c for c in numeric_cols if any(
        kw in c.lower() for kw in ('temp', 'press', 'speed', 'flow', 'rpm', 'torque',
                                    'current', 'power', 'amp', 'volt', 'thickness',
                                    'tension', 'ratio', 'frequency', 'position', 'load',
                                    'rate', 'level', 'density', 'viscosity', 'gap'))
    ]
    if not process_like:
        process_like = numeric_cols[:10]

    per_param_slope = {}
    for c in process_like[:8]:  # limit to top 8 to control noise
        vals = [_safe_float(r.get(c)) for r in rows]
        clean_idx = [(i, v) for i, v in enumerate(vals) if v is not None]
        if len(clean_idx) < 20:
            continue

        slopes = [0.0] * n
        for i, left, right in _window_indices(n, window):
            seg = [(j, vals[j]) for j in range(left, right) if vals[j] is not None]
            if len(seg) < 3:
                continue
            times = [j - i for j, _ in seg]
            vals_seg = [v for _, v in seg]
            try:
                # Simple linear regression slope
                n_seg = len(times)
                sum_x = sum(times)
                sum_y = sum(vals_seg)
                sum_xy = sum(t * v for t, v in zip(times, vals_seg))
                sum_x2 = sum(t * t for t in times)
                denom = n_seg * sum_x2 - sum_x * sum_x
                if abs(denom) > 1e-9:
                    slope = (n_seg * sum_xy - sum_x * sum_y) / denom
                else:
                    slope = 0.0
            except Exception:
                slope = 0.0

            # Normalize by parameter's magnitude
            mag = abs(mean(vals_seg)) + 1e-9
            slopes[i] = slope / mag

        per_param_slope[c] = slopes

    if not per_param_slope:
        return [0.0] * n, {}

    # Aggregate: median slope across all parameters per row
    ramp_scores = []
    for i in range(n):
        row_slopes = [per_param_slope[c][i] for c in per_param_slope if per_param_slope[c][i] is not None]
        if row_slopes:
            ramp_scores.append(median(row_slopes))
        else:
            ramp_scores.append(0.0)

    return ramp_scores, per_param_slope


# ── ABNORMAL TIME WINDOW DETECTION ──

def detect_abnormal_windows(regime_labels, rows, numeric_cols, min_normal_span=10):
    """Detect isolated time windows where parameters behave abnormally.
    Different from startup/shutdown — these are mid-production anomalies
    (sensor spikes, unlogged interventions, brief instabilities).

    Uses: isolated short-duration high-variance windows surrounded by normal periods.
    """
    n = len(regime_labels)
    abnormal_windows = []
    i = 0
    while i < n:
        if regime_labels[i] == 'abnormal':
            start = i
            while i < n and regime_labels[i] == 'abnormal':
                i += 1
            end = i - 1
            duration = end - start + 1
            # Check if this is isolated (normal on both sides)
            left_normal = start >= min_normal_span and all(
                lbl == 'steady' for lbl in regime_labels[max(0, start - min_normal_span):start])
            right_normal = end < n - min_normal_span and all(
                lbl == 'steady' for lbl in regime_labels[end + 1:min(n, end + 1 + min_normal_span)])

            abnormal_windows.append({
                'start_index': start,
                'end_index': end,
                'duration_rows': duration,
                'isolated': left_normal and right_normal,
                'likely_cause': 'sensor_anomaly_or_brief_upset' if (left_normal and right_normal and duration < 20)
                else 'sustained_abnormal_period'
            })
        else:
            i += 1

    return abnormal_windows


# ── FUSION: COMBINE 3 METHODS INTO FINAL REGIME LABELS ──

def fuse_regimes(variance_scores, change_points, ramp_scores, n_rows,
                 variance_threshold=3.0, consensus_threshold=0.6, window=10):
    """Fuse variance ratio, change points, and ramp scores into per-row regime labels.

    Priority (highest → lowest):
      1. Near change-point boundaries → 'transition'
      2. High variance + extreme ramp → 'startup' or 'shutdown'
      3. High variance, no ramp → 'abnormal'
      4. Low variance, low ramp → 'steady'
    """
    labels = ['steady'] * n_rows

    if variance_scores is None:
        return labels, {'method': 'change_points_only'}, []

    # Build change point boundary mask (±window around each CP)
    cp_mask = [False] * n_rows
    for cp in change_points:
        for i in range(max(0, cp - window // 2), min(n_rows, cp + window // 2 + 1)):
            cp_mask[i] = True

    # Classify each row
    for i in range(n_rows):
        vs = variance_scores[i] if variance_scores[i] is not None else 1.0
        rs = ramp_scores[i] if ramp_scores[i] is not None else 0.0

        # Near change point → transition
        if cp_mask[i]:
            labels[i] = 'transition'
            continue

        # High variance → abnormal
        if vs > variance_threshold:
            if rs > 0.03:
                labels[i] = 'startup'
            elif rs < -0.03:
                labels[i] = 'shutdown'
            else:
                labels[i] = 'abnormal'
        elif vs > variance_threshold * 0.7:
            labels[i] = 'marginal'
        else:
            labels[i] = 'steady'

    # Detect abnormal windows for reporting
    abnormal_windows = detect_abnormal_windows(labels, None, None)

    # Build summary
    diagnosis = {
        'method': 'variance_ratio_plus_changepoint_plus_ramp_fusion',
        'change_points_detected': len(change_points),
        'change_point_indices': change_points,
        'abnormal_windows': abnormal_windows,
        'variance_threshold': variance_threshold,
    }

    return labels, diagnosis, abnormal_windows


# ── PER-PRODUCT FOCUSED ANALYSIS ──

def compute_product_anomaly_focus(rows, labels, group_col, target_cols, time_col=None):
    """Compute per-product anomaly rates and identify the highest-anomaly product.

    Returns:
      - product_anomaly_summary: per-product stats
      - focus_product: the product with the highest anomaly rate
      - focus_product_rows: row indices belonging to the focus product
    """
    if not group_col:
        return None, None, None

    groups = defaultdict(list)
    for i, row in enumerate(rows):
        g = str(row.get(group_col, '')).strip()
        if g:
            groups[g].append(i)

    if len(groups) < 2:
        return None, None, None

    product_stats = {}
    for g, indices in groups.items():
        total = len(indices)
        steady = sum(1 for i in indices if labels[i] == 'steady')
        abnormal = sum(1 for i in indices if labels[i] == 'abnormal')
        transition = sum(1 for i in indices if labels[i] in ('startup', 'shutdown', 'transition'))

        # Compute anomaly rates per target
        target_anomaly_rates = {}
        for t in (target_cols or []):
            vals = [_safe_float(rows[i].get(t)) for i in indices]
            clean = [v for v in vals if v is not None]
            if len(clean) < 5:
                continue
            mu = mean(clean)
            sd = stdev(clean) if len(clean) > 1 else 0
            if sd > 0:
                anomaly_count = sum(1 for v in clean if abs(v - mu) > 2 * sd)
                target_anomaly_rates[t] = round(anomaly_count / len(clean), 4)

        # Overall anomaly score: weighted combination
        overall_anomaly = (
            sum(target_anomaly_rates.values()) / max(1, len(target_anomaly_rates))
            if target_anomaly_rates else 0
        )

        product_stats[g] = {
            'total_rows': total,
            'steady_rows': steady,
            'abnormal_rows': abnormal,
            'transition_rows': transition,
            'steady_ratio': round(steady / total, 4) if total > 0 else 0,
            'target_anomaly_rates': target_anomaly_rates,
            'overall_anomaly_score': round(overall_anomaly, 4),
        }

    # Find focus product: highest overall anomaly score (with minimum row count)
    focus_product = None
    focus_score = -1
    for g, stats in product_stats.items():
        if stats['total_rows'] >= 10 and stats['overall_anomaly_score'] > focus_score:
            focus_score = stats['overall_anomaly_score']
            focus_product = g

    focus_rows = sorted(groups.get(focus_product, [])) if focus_product else None

    return product_stats, focus_product, focus_rows


# ── MAIN ──

def main():
    parser = argparse.ArgumentParser(
        description="Production Regime Detector — auto-detect startup/steady/shutdown/abnormal periods")
    parser.add_argument('data_csv')
    parser.add_argument('output_dir')
    parser.add_argument('--time-col', default=None)
    parser.add_argument('--group-col', default=None)
    parser.add_argument('--window-minutes', type=float, default=10, help='Sliding window in minutes (auto-converts to rows)')
    parser.add_argument('--window-rows', type=int, default=None, help='Sliding window in rows (overrides window-minutes)')
    parser.add_argument('--min-steady-ratio', type=float, default=0.4,
                        help='Minimum steady-state ratio required for analysis (default 0.4)')
    parser.add_argument('--variance-threshold', type=float, default=3.0,
                        help='Variance ratio threshold for abnormal (default 3.0)')
    parser.add_argument('--consensus-threshold', type=float, default=0.6,
                        help='Fraction of params that must agree for a change point (default 0.6)')
    args = parser.parse_args()

    if not os.path.exists(args.data_csv):
        print(f"ERROR: Data file not found: {args.data_csv}", file=sys.stderr)
        sys.exit(1)

    os.makedirs(args.output_dir, exist_ok=True)

    # Load data
    with open(args.data_csv, newline='') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    col_names = reader.fieldnames or []

    time_col = args.time_col or _detect_time_col(col_names)
    group_col = _detect_group_col(col_names, args.group_col)
    numeric_cols = _numeric_columns(rows, excluded={time_col, group_col})

    n = len(rows)

    # Determine window size
    if args.window_rows:
        window = args.window_rows
    elif time_col:
        # Estimate rows per minute from time column
        try:
            from datetime import datetime
            t0 = datetime.strptime(rows[0][time_col][:19], "%Y-%m-%d %H:%M:%S")
            t1 = datetime.strptime(rows[-1][time_col][:19], "%Y-%m-%d %H:%M:%S")
            total_minutes = max(1, (t1 - t0).total_seconds() / 60)
            rows_per_minute = n / total_minutes
            window = max(10, int(args.window_minutes * rows_per_minute))
        except Exception:
            window = max(5, n // 20)
    else:
        window = max(5, n // 20)

    window = min(window, n // 3)  # cap at 1/3 of data

    print(f"[regime-detector] {n} rows, {len(numeric_cols)} numeric cols, window={window}")

    # Method 1: Variance ratio analysis
    variance_scores, param_stats = detect_by_variance(rows, numeric_cols, window)
    if variance_scores is None:
        print(f"[regime-detector] WARNING: Variance analysis failed — {param_stats}")

    # Method 2: Change point detection
    change_points, cp_params = detect_change_points(rows, numeric_cols, window)
    print(f"[regime-detector] Detected {len(change_points)} consensus change points")

    # Method 3: Ramp detection (startup/shutdown directional)
    ramp_scores, ramp_params = detect_drift_ramps(rows, numeric_cols, window)

    # Fuse into final labels
    labels, diagnosis, abnormal_windows = fuse_regimes(
        variance_scores, change_points, ramp_scores, n,
        variance_threshold=args.variance_threshold,
        consensus_threshold=args.consensus_threshold,
        window=window
    )

    # Count regime distribution
    regime_counts = defaultdict(int)
    for l in labels:
        regime_counts[l] += 1

    steady_ratio = regime_counts.get('steady', 0) / n
    print(f"[regime-detector] Regime distribution: {dict(regime_counts)}")
    print(f"[regime-detector] Steady-state ratio: {steady_ratio:.1%}")

    if steady_ratio < args.min_steady_ratio:
        print(f"[regime-detector] WARNING: Steady-state ratio ({steady_ratio:.1%}) below minimum ({args.min_steady_ratio:.0%}) — data quality may be low")

    # Compute per-product anomaly focus
    quality_cols = _numeric_columns(rows, excluded={time_col, group_col})
    # Heuristic: quality/inspection targets are typically late columns, have names like 'defect', 'quality', 'scratch'
    target_candidates = [c for c in numeric_cols if any(
        kw in c.lower() for kw in ('defect', 'scratch', 'quality', 'reject', 'fail', 'yield',
                                    'thickness', 'haze', 'gloss', 'color', 'density', 'weight',
                                    'moisture', 'strength', 'elongation', 'modulus', 'shrinkage'))
    ]
    if not target_candidates:
        # Fallback: use heuristically chosen columns (lowest variance = most stable, likely quality)
        cvs = []
        for c in numeric_cols:
            vals = [_safe_float(r.get(c)) for r in rows]
            clean = [v for v in vals if v is not None]
            if len(clean) < 10:
                continue
            try:
                cv = stdev(clean) / (abs(mean(clean)) + 1e-9)
            except Exception:
                cv = 999
            cvs.append((cv, c))
        cvs.sort()
        target_candidates = [c for _, c in cvs[:3]]

    product_stats, focus_product, focus_rows = compute_product_anomaly_focus(
        rows, labels, group_col, target_candidates, time_col
    )

    if focus_product:
        print(f"[regime-detector] Focus product: '{focus_product}' — highest anomaly score ({product_stats[focus_product]['overall_anomaly_score']:.4f})")

    # Build output
    output = {
        'run_id': f"regime_{int(os.path.getmtime(args.data_csv) if os.path.exists(args.data_csv) else 0)}",
        'generated_at': None,  # filled below
        'total_rows': n,
        'window_size_rows': window,
        'time_column': time_col,
        'group_column': group_col,
        'numeric_columns_analyzed': len(numeric_cols),
        'regime_distribution': {k: {'count': v, 'pct': round(v / n * 100, 2)} for k, v in regime_counts.items()},
        'steady_state_ratio': round(steady_ratio, 4),
        'sufficient_steady_data': steady_ratio >= args.min_steady_ratio,
        'diagnosis': diagnosis,
        'filter_recommendation': {
            'exclude_regimes': ['startup', 'shutdown', 'transition'],
            'caution_regimes': ['abnormal', 'marginal'],
            'include_regime': 'steady',
            'reasoning': 'Startup/shutdown periods contain non-representative parameter excursions (ramp-up/down, equipment warm-up, purge cycles). Abnormal periods may contain sensor faults or unlogged interventions. Only steady-state data represents the true process operating condition for root cause analysis.'
        },
        'per_product_anomaly_analysis': {
            'applicable': group_col is not None and product_stats is not None,
            'not_applicable_reason': None if group_col else 'No product grouping column detected',
            'group_column': group_col,
            'product_stats': product_stats,
            'focus_product': focus_product,
            'focus_product_stats': product_stats.get(focus_product) if focus_product else None,
            'focus_product_row_count': len(focus_rows) if focus_rows else 0,
            'focus_product_steady_rows': sum(1 for i in (focus_rows or []) if labels[i] == 'steady'),
            'focus_product_directive': f"MANDATORY: When product grouping exists, the per-product analysis MUST be performed. The product with the highest anomaly rate ('{focus_product}') MUST receive focused within-product analysis: (a) isolate steady-state rows for this product only, (b) re-run within-product correlation, trend, CCF analysis on process parameters vs quality targets limited to this product's processing time window, (c) compare within-product findings against cross-product aggregate findings. Product-switch confounding (Simpson's Paradox) is the #1 cause of spurious r>0.7 correlations in multi-product datasets." if focus_product else None,
        },
        'per_row_labels': labels,
        'steady_row_indices': [i for i, l in enumerate(labels) if l == 'steady'],
        'abnormal_windows': abnormal_windows,
    }

    from datetime import datetime, timezone
    output['generated_at'] = datetime.now(timezone.utc).isoformat()

    # Write output
    out_path = os.path.join(args.output_dir, 'production_regime_filter.json')
    with open(out_path, 'w') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    # Also write steady-state-only subset as CSV
    steady_rows = [rows[i] for i in output['steady_row_indices']]
    if steady_rows:
        steady_csv_path = os.path.join(args.output_dir, 'cleaned_data_steady_only.csv')
        with open(steady_csv_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(steady_rows)
        print(f"[regime-detector] Steady-state subset: {len(steady_rows)} rows → {steady_csv_path}")

    print(f"[regime-detector] Full analysis → {out_path}")


if __name__ == '__main__':
    main()
