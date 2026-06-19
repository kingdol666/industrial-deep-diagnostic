"""
VLM-friendly visualization and visual analysis engine.

Design principles:
1. PER-PRODUCT SPLITTING FIRST: If multiple products exist, split by product, focus on
   the highest-anomaly-rate product. ALL process params + quality metrics on shared time axis.
2. Time-aligned overlay: All parameters normalized, direction-aligned, on shared time axis
3. When too many params for one chart: split into logical groups (by process stage) while
   keeping quality metrics in every sub-chart
4. Event markers clearly visible (red dashed lines with text)
5. Large fonts, high contrast, clean layout
6. Generates both PNG images AND structured visual_analysis.json

Usage:
  python visual_analysis.py <run_dir> [--target-cols col1,col2] [--key-params p1,p2] [--group-col col]
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
import json
import os
import sys

MAX_SERIES_PER_CHART = 12  # split into sub-charts when more than this


def load_data(run_dir):
    """Load cleaned data and all analysis artifacts."""
    cleaned_csv = os.path.join(run_dir, '02_processed', 'cleaned_data.csv')
    df = pd.read_csv(cleaned_csv)
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Coerce candidate numeric columns: cleaned_data.csv stores numbers as
    # strings (CSV→JSON conversion does no type coercion — the string-type-gotcha).
    # A single stray token in a column (<0.05, N/A, "89.5°C", 100±2, 缺失) makes
    # pandas infer object/string dtype, after which the strict dtype filters
    # below silently drop that parameter from EVERY plot → no PNG → VLM gate
    # fails → metadata_backed_inference fallback. pd.to_numeric turns stray
    # tokens into NaN (already handled by downstream .dropna()) instead of
    # forcing the whole column to string. A column is only adopted as numeric
    # when ≥50% of its non-null values parse as numbers, so genuine categorical
    # columns (product_id, machine_id) stay object and remain usable as groups.
    _time_cols = {'timestamp', 'time', 'index'}
    for col in df.columns:
        if col in _time_cols:
            continue
        if df[col].dtype not in ('object', 'string'):
            continue
        coerced = pd.to_numeric(df[col], errors='coerce')
        non_null = df[col].notna().sum()
        if non_null == 0:
            continue
        if coerced.notna().sum() >= non_null / 2:
            df[col] = coerced

    feature_path = os.path.join(run_dir, '02_processed', 'feature_summary.json')
    features = json.load(open(feature_path)) if os.path.exists(feature_path) else {}

    validate_path = os.path.join(run_dir, '02_processed', 'validate_report.json')
    validate = json.load(open(validate_path)) if os.path.exists(validate_path) else {}

    ontology_path = os.path.join(run_dir, '01_ontology', 'ontology.json')
    ontology = json.load(open(ontology_path)) if os.path.exists(ontology_path) else {}

    # Load production regime filter for focus_product
    regime_path = os.path.join(run_dir, '02_processed', 'production_regime_filter.json')
    regime = json.load(open(regime_path)) if os.path.exists(regime_path) else {}

    # Load anomaly report for per-product anomaly rates
    anomaly_path = os.path.join(run_dir, '02_processed', 'anomaly_report.json')
    anomaly = json.load(open(anomaly_path)) if os.path.exists(anomaly_path) else {}

    return df, features, validate, ontology, regime, anomaly


def get_correlation_sign(features, col, target_col):
    """Get correlation sign between col and target from feature_summary."""
    try:
        if isinstance(features, dict):
            correlations = features.get('correlations', features.get('cross_correlations', {}))
            if isinstance(correlations, dict):
                for key, val in correlations.items():
                    if isinstance(val, dict):
                        pair = val.get('pair', val.get('parameter', ''))
                        if (col in str(pair) and target_col in str(pair)) or \
                           (val.get('parameter') == col and val.get('target') == target_col):
                            r = val.get('pearson_r', val.get('r', 0))
                            return 1 if r >= 0 else -1
            elif isinstance(correlations, list):
                for item in correlations:
                    if item.get('parameter') == col and item.get('target') == target_col:
                        r = item.get('pearson_r', item.get('r', 0))
                        return 1 if r >= 0 else -1
    except Exception:
        pass
    return 1


def get_param_display_name(col, ontology):
    """Get human-readable display name from ontology, falling back to raw column name."""
    if ontology and isinstance(ontology, dict):
        for p in ontology.get('parameters', []):
            if isinstance(p, dict) and p.get('name', p.get('column', '')) == col:
                label = p.get('label', p.get('physical_meaning', ''))
                units = p.get('unit', p.get('units', ''))
                if label:
                    return f"{label} ({units})" if units else label
    return col


def get_param_stage(col, ontology):
    """Get the process stage a parameter belongs to, for logical grouping."""
    if ontology and isinstance(ontology, dict):
        for p in ontology.get('parameters', []):
            if isinstance(p, dict) and p.get('name', p.get('column', '')) == col:
                return p.get('stage_ref', p.get('stage', 'unknown'))
    return 'unknown'


def group_params_by_stage(params, ontology):
    """Group parameters by process stage for logical sub-chart splitting."""
    stages = {}
    for p in params:
        stage = get_param_stage(p, ontology)
        if stage not in stages:
            stages[stage] = []
        stages[stage].append(p)
    return stages


def generate_per_product_overlays(df, targets, key_params, group_col, fig_dir,
                                  features=None, ontology=None, regime=None, anomaly=None):
    """
    THE CORE VLM CHARTS: Per-product time-aligned overlays.

    If multiple products exist:
      - Split by product
      - Focus on the product with the highest anomaly rate first (from regime filter
        or anomaly report)
      - Generate one overlay per product: ALL process params + quality metrics on
        shared time axis within that product's time window
      - If too many params (>MAX_SERIES_PER_CHART), split into sub-charts by process
        stage, keeping quality metrics in every sub-chart

    If single product or no group column:
      - Generate one overlay with ALL process params + quality metrics
    """
    has_timestamp = 'timestamp' in df.columns
    time_col = 'timestamp' if has_timestamp else None

    paths = []

    # --- Determine products and focus product ---
    if group_col and group_col in df.columns:
        product_values = sorted(df[group_col].dropna().unique())
    else:
        product_values = []

    # Single-product case: no group column or only one product
    if len(product_values) <= 1:
        label = str(product_values[0]) if product_values else 'all_data'
        paths = _generate_one_product_overlay(
            df, targets, key_params, label, fig_dir, time_col,
            features, ontology, suffix='single_product'
        )
        return paths

    # Multi-product case: determine focus product (highest anomaly rate)
    focus_product = None
    if regime and isinstance(regime, dict):
        ppa = regime.get('per_product_anomaly_analysis', {})
        focus_product = ppa.get('focus_product')
    if not focus_product and anomaly and isinstance(anomaly, dict):
        # fallback: compute anomaly rates from dual_drive_analysis
        dda = anomaly.get('dual_drive_analysis', {})
        ppa = dda.get('per_product_analysis', {})
        max_rate = -1
        for prod, info in ppa.items():
            rate = info.get('anomaly_rate', info.get('defect_rate', 0))
            if rate > max_rate:
                max_rate = rate
                focus_product = prod
    if not focus_product:
        focus_product = product_values[0]

    # Sort products: focus_product first, then the rest
    ordered_products = [focus_product] + [p for p in product_values if p != focus_product]

    for prod in ordered_products:
        prod_df = df[df[group_col] == prod].copy()
        if len(prod_df) < 5:
            print(f"  [SKIP] Product '{prod}' has only {len(prod_df)} rows — skipping overlay")
            continue

        # Sort by time within product
        if time_col and time_col in prod_df.columns:
            prod_df = prod_df.sort_values(time_col)

        is_focus = (prod == focus_product)
        suffix = f"focus_{prod}" if is_focus else f"prod_{prod}"
        prod_paths = _generate_one_product_overlay(
            prod_df, targets, key_params, str(prod), fig_dir, time_col,
            features, ontology,
            suffix=suffix,
            is_focus_product=is_focus
        )
        paths.extend(prod_paths)

    return paths


def _generate_one_product_overlay(df, targets, key_params, product_label, fig_dir,
                                   time_col, features, ontology,
                                   suffix='', is_focus_product=False):
    """
    Generate time-aligned overlay(s) for a single product's data.

    Strategy:
    - If total params (targets + key_params) <= MAX_SERIES_PER_CHART: one chart
    - Otherwise: split by process stage. Quality targets appear in EVERY sub-chart.
      Process params assigned to sub-charts by stage.
    """
    has_time = time_col and time_col in df.columns
    if not has_time:
        return []

    all_process = [p for p in key_params if p in df.columns and p not in targets]
    all_targets = [t for t in targets if t in df.columns]
    all_params = all_targets + all_process

    if len(all_params) == 0:
        return []

    # Determine if splitting is needed
    if len(all_params) <= MAX_SERIES_PER_CHART:
        path = _plot_time_aligned_overlay(
            df, all_targets, all_process, product_label, fig_dir,
            time_col, features, ontology, suffix=suffix,
            is_focus=is_focus_product
        )
        return [path] if path else []

    # Too many params — split by process stage
    stages = group_params_by_stage(all_process, ontology)
    # Flatten stages into groups of at most MAX_SERIES_PER_CHART - len(targets)
    max_process_per_chart = max(1, MAX_SERIES_PER_CHART - len(all_targets))
    process_groups = []
    current_group = []
    for stage, params in stages.items():
        for p in params:
            current_group.append(p)
            if len(current_group) >= max_process_per_chart:
                process_groups.append(list(current_group))
                current_group = []
    if current_group:
        process_groups.append(list(current_group))

    paths = []
    for gi, pg in enumerate(process_groups):
        group_suffix = f"{suffix}_g{gi+1}" if len(process_groups) > 1 else suffix
        path = _plot_time_aligned_overlay(
            df, all_targets, pg, product_label, fig_dir,
            time_col, features, ontology, suffix=group_suffix,
            is_focus=is_focus_product
        )
        if path:
            paths.append(path)
    return paths


def _plot_time_aligned_overlay(df, targets, process_params, product_label, fig_dir,
                                time_col, features, ontology,
                                suffix='', is_focus=False):
    """Plot a single time-aligned overlay chart."""
    primary_target = targets[0] if targets else None
    all_to_plot = targets + [p for p in process_params if p not in targets]

    n_params = len(all_to_plot)
    if n_params == 0:
        return None

    # Dynamic figure sizing
    fig_height = max(8, n_params * 0.5 + 6)
    fig, ax = plt.subplots(figsize=(22, fig_height))

    # Use viridis for better color-blind accessibility and more colors
    colors = plt.cm.tab20(np.linspace(0, 1, max(20, n_params)))
    if n_params > 20:
        colors = plt.cm.viridis(np.linspace(0, 1, n_params))

    line_styles = ['-', '--', '-.', ':']
    target_markers = ['s', 'D', '^', 'v', 'p', 'h']

    legend_entries = []

    for idx, col in enumerate(all_to_plot):
        if col not in df.columns:
            continue
        series = df[col].dropna()
        if series.std() == 0 or len(series) < 2:
            continue

        # z-score normalize
        z_values = (df[col] - df[col].mean()) / df[col].std()

        # Reverse negatively-correlated params so VLM sees all lines moving together
        sign = 1
        if primary_target and col != primary_target:
            sign = get_correlation_sign(features or {}, col, primary_target)
        reversed_label = ""
        if sign < 0:
            z_values = -z_values
            reversed_label = " (↺)"

        is_target = col in targets
        display_name = get_param_display_name(col, ontology)
        full_label = f"{display_name}{reversed_label}"

        if is_target:
            # Quality targets: thicker, more prominent, with markers
            ax.plot(df[time_col], z_values,
                    linewidth=2.5, color='black' if len(targets) <= 2 else colors[idx],
                    linestyle='-', alpha=1.0, marker=target_markers[idx % len(target_markers)],
                    markersize=5, markevery=max(1, len(df) // 30),
                    label=f"★ {full_label}", zorder=10)
        else:
            ax.plot(df[time_col], z_values,
                    linewidth=1.0, color=colors[idx % len(colors)],
                    linestyle=line_styles[idx % len(line_styles)],
                    alpha=0.75, label=full_label, zorder=5)

    # Focus product banner
    focus_tag = "【重点分析】" if is_focus else ""

    # Event markers from product transitions (if df is a product subset, detect
    # time gaps or regime transitions)
    events = _detect_events_in_subset(df, time_col)
    for event_time, event_name in events:
        ax.axvline(event_time, color='red', linestyle='--', linewidth=2.5, alpha=0.9, zorder=10)
        ax.text(event_time, ax.get_ylim()[1] if ax.get_ylim()[1] != 0 else 2,
                f'  {event_name}', rotation=90, va='top', ha='left',
                fontsize=12, color='red', fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8, edgecolor='red'))

    # Anomaly interval shading (from anomaly_report if available)
    _add_anomaly_shading(ax, df, fig_dir)

    stage_info = ""
    stage_set = set()
    for p in process_params:
        s = get_param_stage(p, ontology)
        if s and s != 'unknown':
            stage_set.add(s)
    if stage_set:
        stage_info = f" | Stages: {', '.join(sorted(stage_set))}"

    ax.set_xlabel('Time', fontsize=14)
    ax.set_ylabel('z-score (negatively-correlated params reversed ↺)', fontsize=12)
    ax.set_title(f'{focus_tag}Product: {product_label} — ALL Parameters Time-Aligned Overlay{stage_info}\n'
                 f'({n_params} params: ★ = Quality Target | Lines moving together = correlated | '
                 f'Read LEFT→RIGHT for temporal sequence)',
                 fontsize=14, fontweight='bold')
    ax.legend(fontsize=10, loc='upper left', framealpha=0.9, edgecolor='black',
              ncol=min(3, max(1, n_params // 10)))
    ax.grid(True, alpha=0.3, linestyle='-')
    ax.tick_params(axis='both', labelsize=11)

    fig.tight_layout()
    filename = f'fig_vlm_temporal_overlay_{suffix}.png'
    path = os.path.join(fig_dir, filename)
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  → {path}")
    return path


def _detect_events_in_subset(df, time_col):
    """Detect significant time gaps or state transitions in a product subset."""
    events = []
    if time_col not in df.columns:
        return events
    times = pd.to_datetime(df[time_col])
    gaps = times.diff().dt.total_seconds()
    median_gap = gaps.median()
    gap_threshold = median_gap * 5 if median_gap > 0 else 3600
    for i in gaps[gaps > gap_threshold].index:
        if i > 0 and i < len(df):
            events.append((times.iloc[i], f'Gap {gaps.iloc[i]/3600:.1f}h'))
    return events[:6]  # max 6 event markers


def _add_anomaly_shading(ax, df, fig_dir):
    """Add semi-transparent red shading for anomaly intervals if known."""
    # Try reading anomaly_report for anomaly intervals
    run_dir = os.path.dirname(fig_dir)
    anomaly_path = os.path.join(run_dir, 'anomaly_report.json')
    if not os.path.exists(anomaly_path):
        return
    try:
        anomaly = json.load(open(anomaly_path))
        intervals = anomaly.get('anomaly_intervals', [])
        for interval in intervals:
            start = interval.get('start_time') or interval.get('start_index')
            end = interval.get('end_time') or interval.get('end_index')
            if start is not None and end is not None:
                ax.axvspan(start, end, alpha=0.1, color='red')
    except Exception:
        pass


# --- Legacy global overlay (kept for backward compatibility) ---

def generate_temporal_overlay(df, targets, key_params, events, fig_dir, features=None):
    """
    Global time-aligned overlay chart (legacy — per-product overlays are preferred).
    Kept for backward compatibility when no product grouping exists.
    """
    primary_target = targets[0] if targets else None
    all_params = targets + [p for p in key_params if p not in targets]

    fig, ax = plt.subplots(figsize=(20, 10))
    colors = plt.cm.tab10(np.linspace(0, 1, len(all_params)))
    line_styles = ['-', '--', '-.', ':', '-', '--', '-.', ':', '-', '--']

    for idx, col in enumerate(all_params):
        if col not in df.columns:
            continue
        values = df[col].dropna()
        if values.std() == 0:
            continue
        z_values = (df[col] - df[col].mean()) / df[col].std()
        sign = get_correlation_sign(features or {}, col, primary_target) if primary_target else 1
        reversed_label = ""
        if sign < 0:
            z_values = -z_values
            reversed_label = " (↺reversed)"

        ax.plot(df['timestamp'], z_values,
                linewidth=1.2 if col in targets else 0.9,
                color=colors[idx],
                linestyle=line_styles[idx % len(line_styles)],
                alpha=0.85 if col in targets else 0.7,
                label=f"{col}{reversed_label}")

    for event_time, event_name in events:
        if isinstance(event_time, int):
            if event_time < len(df):
                event_time = df['timestamp'].iloc[event_time]
            else:
                continue
        ax.axvline(event_time, color='red', linestyle='--', linewidth=2.5, alpha=0.9, zorder=10)
        ax.text(event_time, ax.get_ylim()[1] if ax.get_ylim()[1] != 0 else 2,
                f'  {event_name}', rotation=90, va='top', ha='left',
                fontsize=12, color='red', fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8, edgecolor='red'))

    ax.set_xlabel('Time', fontsize=14)
    ax.set_ylabel('Normalized Value (z-score; negatively-correlated params reversed)', fontsize=12)
    ax.set_title('TEMPORAL ALIGNMENT — All Parameters Normalized & Direction-Aligned\n'
                 '(Lines moving together = correlated; Lines diverging = different mechanisms)',
                 fontsize=14, fontweight='bold')
    ax.legend(fontsize=11, loc='upper right', framealpha=0.9, edgecolor='black')
    ax.grid(True, alpha=0.3, linestyle='-')
    ax.tick_params(axis='both', labelsize=11)

    fig.tight_layout()
    path = os.path.join(fig_dir, 'fig_vlm_temporal_overlay.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  → {path}")
    return path


def generate_event_response_overlay(df, targets, event_col, event_values, fig_dir):
    """
    VLM chart: Quality parameters overlaid, colored by event phase.
    Shows visual evidence of whether quality resets at events.
    """
    if event_col not in df.columns:
        return None

    fig, ax = plt.subplots(figsize=(18, 8))
    primary_target = targets[0]
    colors = {'before': '#2196F3', 'after': '#F44336'}

    if len(event_values) >= 2:
        transition_idx = df[df[event_col] == event_values[1]].index[0] if event_values[1] in df[event_col].values else len(df) // 2
    else:
        transition_idx = len(df) // 2

    before = df.iloc[:transition_idx]
    after = df.iloc[transition_idx:]

    ax.scatter(before['timestamp'], (before[primary_target] - df[primary_target].mean()) / df[primary_target].std(),
               s=8, alpha=0.5, color=colors['before'], label=f'{event_values[0]} (before)')
    ax.scatter(after['timestamp'], (after[primary_target] - df[primary_target].mean()) / df[primary_target].std(),
               s=8, alpha=0.5, color=colors['after'], label=f'{event_values[1]} (after)')

    transition_time = df['timestamp'].iloc[transition_idx]
    ax.axvline(transition_time, color='red', linestyle='--', linewidth=2.5, alpha=0.9)
    ax.text(transition_time, ax.get_ylim()[1] * 0.95, '  EVENT TRANSITION',
            rotation=90, va='top', ha='left', fontsize=13, color='red', fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8, edgecolor='red'))

    before_mean = (before[primary_target].mean() - df[primary_target].mean()) / df[primary_target].std()
    after_mean = (after[primary_target].mean() - df[primary_target].mean()) / df[primary_target].std()
    ax.axhline(before_mean, color=colors['before'], linestyle='-', linewidth=2, alpha=0.7)
    ax.axhline(after_mean, color=colors['after'], linestyle='-', linewidth=2, alpha=0.7)
    ax.text(df['timestamp'].iloc[5], before_mean + 0.1, f'Before μ = {before[primary_target].mean():.1f}',
            fontsize=12, color=colors['before'], fontweight='bold')
    ax.text(df['timestamp'].iloc[-5], after_mean + 0.1, f'After μ = {after[primary_target].mean():.1f}',
            fontsize=12, color=colors['after'], fontweight='bold', ha='right')

    ax.set_xlabel('Time', fontsize=14)
    ax.set_ylabel(f'{primary_target} (normalized)', fontsize=13)
    ax.set_title(f'EVENT RESPONSE ANALYSIS — {primary_target}\n'
                 f'Visual question: Does quality change at the event transition?',
                 fontsize=14, fontweight='bold')
    ax.legend(fontsize=12, loc='upper right')
    ax.grid(True, alpha=0.3)
    ax.tick_params(axis='both', labelsize=11)

    fig.tight_layout()
    path = os.path.join(fig_dir, 'fig_vlm_event_response.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  → {path}")
    return path


def generate_simpson_visual(df, target, param, group_col, fig_dir):
    """
    VLM chart: Simpson Paradox visualization with regression lines per stratum.
    Designed so VLM can see direction reversal.
    """
    if group_col not in df.columns or target not in df.columns or param not in df.columns:
        return None

    groups = df[group_col].unique()
    if len(groups) < 2:
        return None

    fig, axes = plt.subplots(1, len(groups), figsize=(8 * len(groups), 7))
    if len(groups) == 1:
        axes = [axes]

    overall_r = df[target].corr(df[param])
    directions = []

    for idx, grp_name in enumerate(groups):
        ax = axes[idx]
        grp = df[df[group_col] == grp_name]
        r = grp[target].corr(grp[param])
        directions.append(r)
        color = '#2196F3' if r >= 0 else '#F44336'

        ax.scatter(grp[param], grp[target], s=10, alpha=0.5, color=color)

        if grp[param].std() > 0:
            # Joint dropna on the pair so x and y stay aligned + same length.
            # Independent .dropna() breaks when one column has NaN (stray tokens
            # coerced to NaN) and the other doesn't → mismatched lengths crash polyfit.
            pair = grp[[param, target]].dropna()
            if len(pair) >= 2:
                z = np.polyfit(pair[param], pair[target], 1)
                x_range = np.linspace(pair[param].min(), pair[param].max(), 100)
                ax.plot(x_range, np.polyval(z, x_range), color=color, linewidth=3, alpha=0.8)

        direction_text = "↗ POSITIVE" if r >= 0 else "↘ NEGATIVE"
        ax.set_title(f'{grp_name}\nr = {r:.3f}  {direction_text}',
                     fontsize=14, fontweight='bold', color=color)
        ax.set_xlabel(param, fontsize=12)
        ax.set_ylabel(target, fontsize=12)
        ax.tick_params(axis='both', labelsize=11)
        ax.grid(True, alpha=0.3)

    has_reversal = any(d1 * d2 < 0 for d1 in directions for d2 in directions)
    verdict = "⚠️ SIMPSON PARADOX — Direction REVERSED across strata" if has_reversal else "✅ Direction consistent across strata"

    fig.suptitle(f'SIMPSON PARADOX CHECK: {target} vs {param} (by {group_col})\n'
                 f'Overall r = {overall_r:.3f}  |  {verdict}',
                 fontsize=15, fontweight='bold',
                 color='red' if has_reversal else 'green')
    fig.tight_layout(rect=[0, 0, 1, 0.92])

    path = os.path.join(fig_dir, f'fig_vlm_simpson_{param}.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  → {path}")
    return path


def generate_synchronization_heatmap(df, targets, key_params, fig_dir):
    """
    VLM chart: Parameter synchronization matrix.
    Shows which parameters move together over time (rolling window correlation).
    """
    all_cols = targets + [p for p in key_params if p not in targets]
    numeric_cols = [c for c in all_cols if c in df.columns and df[c].dtype in ('float64', 'int64')]

    if len(numeric_cols) < 3:
        return None

    primary = targets[0]
    window = min(72, len(df) // 4)

    fig, ax = plt.subplots(figsize=(16, 8))

    for col in numeric_cols:
        if col == primary or df[col].std() == 0:
            continue
        rolling_r = df[primary].rolling(window).corr(df[col])
        ax.plot(df['timestamp'], rolling_r, linewidth=1.0, label=col, alpha=0.8)

    ax.axhline(0, color='black', linestyle='-', linewidth=0.5, alpha=0.5)
    ax.axhline(0.5, color='green', linestyle=':', linewidth=1, alpha=0.5, label='r=0.5 threshold')
    ax.axhline(-0.5, color='red', linestyle=':', linewidth=1, alpha=0.5, label='r=-0.5 threshold')

    ax.set_xlabel('Time', fontsize=13)
    ax.set_ylabel(f'Rolling Correlation with {primary} (window={window})', fontsize=12)
    ax.set_title(f'PARAMETER SYNCHRONIZATION — Rolling Correlation with {primary}\n'
                 f'Visual question: Which parameters are consistently correlated? Which drift apart?',
                 fontsize=14, fontweight='bold')
    ax.legend(fontsize=10, loc='upper right')
    ax.grid(True, alpha=0.3)
    ax.tick_params(axis='both', labelsize=11)

    fig.tight_layout()
    path = os.path.join(fig_dir, 'fig_vlm_synchronization.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  → {path}")
    return path


def analyze_temporal_synchronization(df, targets, key_params):
    """Compute cross-parameter temporal alignment statistics."""
    primary = targets[0] if targets else None
    all_cols = targets + [p for p in key_params if p not in targets]
    numeric_cols = [c for c in all_cols if c in df.columns and df[c].dtype in ('float64', 'int64')]

    result = {
        "synchronous_groups": [],
        "precedence_signals": [],
        "independent_parameters": []
    }

    if not primary or primary not in df.columns:
        return result

    strong_positive = []
    strong_negative = []
    weak = []

    for col in numeric_cols:
        if col == primary:
            continue
        r = df[primary].corr(df[col])
        if abs(r) > 0.7:
            if r > 0:
                strong_positive.append({"parameter": col, "r": round(r, 3), "direction": "same"})
            else:
                strong_negative.append({"parameter": col, "r": round(r, 3), "direction": "opposite"})
        elif abs(r) < 0.2:
            weak.append({"parameter": col, "r": round(r, 3), "reason": "near-zero correlation"})

    if strong_positive:
        result["synchronous_groups"].append({
            "parameters": [primary] + [p["parameter"] for p in strong_positive],
            "description": f"Strong positive correlation group (r>0.7): moves together with {primary}",
            "estimated_group_lag": "0 (high correlation suggests synchronous)"
        })

    if strong_negative:
        result["synchronous_groups"].append({
            "parameters": [p["parameter"] for p in strong_negative],
            "description": f"Strong negative correlation group (r<-0.7): moves opposite to {primary}",
            "estimated_group_lag": "0 (high correlation suggests synchronous, but reversed)"
        })

    for w in weak:
        result["independent_parameters"].append({
            "parameters": [w["parameter"]],
            "description": f"Weak correlation (|r|<0.2) with {primary} — visually independent"
        })

    return result


def main():
    if len(sys.argv) < 2:
        print("Usage: python visual_analysis.py <run_dir> [--target-cols col1,col2] [--key-params p1,p2] [--group-col col]")
        sys.exit(1)

    run_dir = sys.argv[1]
    fig_dir = os.path.join(run_dir, '03_figures')
    os.makedirs(fig_dir, exist_ok=True)

    print("Loading data...")
    df, features, validate, ontology, regime, anomaly = load_data(run_dir)

    # Loud-failure guard: if after coercion NO numeric column survived, plotting
    # would silently emit zero PNGs and a metadata_backed_inference skeleton,
    # leaving the VLM with nothing to read (the failure mode this guard exists
    # to prevent). Abort loudly instead.
    _numeric_cols = [c for c in df.columns if df[c].dtype in ('float64', 'int64')]
    if not _numeric_cols:
        sys.exit(
            "[visual_analysis] ABORT: zero numeric columns after type coercion of "
            f"{run_dir}/02_processed/cleaned_data.csv. Columns seen: {list(df.columns)}. "
            "This means cleaned_data.csv is entirely string/object-typed "
            "(string-type-gotcha: CSV→JSON conversion emitted no numeric typing, "
            "and no column reached the ≥50% numeric-parse threshold). Fix the "
            "preprocess step (dp_toolkit.py) or verify the source CSV is not corrupted."
        )

    # --- Dynamic defaults from ontology / scenario_classification ---
    targets = []
    key_params = []
    group_col = None

    # Try reading ontology for quality targets and candidate parameters
    if ontology and isinstance(ontology, dict):
        params = ontology.get('parameters', [])
        for p in params:
            role = ''
            if isinstance(p, dict):
                role = p.get('role', p.get('parameter_role', ''))
            if role in ('quality_target', 'target', 'dependent'):
                name = p['name'] if isinstance(p, dict) else str(p)
                if name in df.columns:
                    targets.append(name)
            elif role in ('process_parameter', 'predictor', 'independent'):
                name = p['name'] if isinstance(p, dict) else str(p)
                if name in df.columns:
                    key_params.append(name)

    # Fallback: if ontology didn't provide targets, infer from data behavior
    if not targets:
        scored = []
        for col in df.columns:
            if col in ('timestamp', 'time', 'index') or df[col].dtype not in ('float64', 'int64'):
                continue
            values = df[col].dropna().astype(float).to_numpy()
            if len(values) < 5:
                continue
            baseline = abs(np.mean(values[: min(10, len(values))])) + 1e-9
            trend = abs(values[-1] - values[0]) / baseline
            cv = float(np.std(values)) / (abs(float(np.mean(values))) + 1e-9)
            q1, q3 = np.percentile(values, [25, 75])
            iqr = q3 - q1
            outlier_ratio = 0 if iqr == 0 else float(np.mean((values < q1 - 1.5 * iqr) | (values > q3 + 1.5 * iqr)))
            scored.append((trend * 0.45 + cv * 0.35 + outlier_ratio * 0.20, col))
        targets = [col for _, col in sorted(scored, reverse=True)[:2]]
    if not targets:
        for col in df.columns:
            if df[col].dtype in ('float64', 'int64') and col != 'timestamp':
                targets.append(col)
                break

    # Fallback: ALL process params (not capped at 8)
    if not key_params:
        exclude = set(targets) | {'timestamp', 'time', 'index'}
        for col in df.columns:
            if col not in exclude and df[col].dtype in ('float64', 'int64'):
                key_params.append(col)

    # Detect group column
    if group_col is None:
        input_manifest_path = os.path.join(run_dir, '00_input', 'input_manifest.json')
        if os.path.exists(input_manifest_path):
            try:
                manifest = json.load(open(input_manifest_path))
                group_col = manifest.get('group_column', manifest.get('categorical_columns', [None])[0] if manifest.get('categorical_columns') else None)
            except Exception:
                pass
    if group_col is None:
        for col in df.columns:
            if col not in targets and df[col].dtype == 'object' and 2 <= df[col].nunique() <= 20:
                group_col = col
                break

    # Parse CLI args
    for i, arg in enumerate(sys.argv[2:], 2):
        if arg.startswith('--target-cols'):
            targets = sys.argv[i+1].split(',')
        elif arg.startswith('--key-params'):
            key_params = sys.argv[i+1].split(',')
        elif arg.startswith('--group-col'):
            group_col = sys.argv[i+1]

    n_products = df[group_col].nunique() if group_col and group_col in df.columns else 1
    print(f"\nGenerating VLM-friendly visualizations for {len(df)} rows, {len(targets)} targets, {len(key_params)} params")
    print(f"  Targets: {targets}")
    print(f"  Key params ({len(key_params)} total): {key_params[:5]}..." if len(key_params) > 5 else f"  Key params: {key_params}")
    print(f"  Group col: {group_col} ({n_products} products)")
    has_time = 'timestamp' in df.columns
    print(f"  Time column: {'timestamp' if has_time else 'NONE — temporal alignment not applicable'}")

    # --- Dynamic event detection (for legacy global overlay) ---
    events = []
    if group_col and group_col in df.columns and df[group_col].nunique() > 1:
        transitions = df[group_col] != df[group_col].shift(1)
        transition_indices = df[transitions].index.tolist()
        for idx in transition_indices[1:]:
            label = str(df[group_col].iloc[idx])
            events.append((idx, f'{group_col} → {label}'))
    if ontology and isinstance(ontology, dict):
        ont_events = ontology.get('events', [])
        for ev in ont_events:
            if isinstance(ev, dict) and 'column' in ev and 'name' in ev:
                col = ev['column']
                if col in df.columns:
                    transitions = df[col] != df[col].shift(1)
                    for idx in df[transitions].index.tolist()[1:]:
                        label = ev['name'] if 'value' not in ev else f"{ev['name']}={df[col].iloc[idx]}"
                        events.append((idx, label))

    # === 1. PER-PRODUCT TIME-ALIGNED OVERLAYS (THE CORE) ===
    print("\n=== Phase 1: Per-Product Time-Aligned Overlays (ALL process params + quality metrics) ===")
    per_product_paths = []
    if has_time:
        per_product_paths = generate_per_product_overlays(
            df, targets, key_params, group_col, fig_dir,
            features, ontology, regime, anomaly
        )
        print(f"  Generated {len(per_product_paths)} per-product overlay chart(s)")
    else:
        print("  SKIPPED — no time column available")

    # === 2. Legacy global temporal overlay (for backward compat) ===
    print("\n=== Phase 2: Global Temporal Overlay (legacy) ===")
    overlay_path = None
    if has_time:
        overlay_path = generate_temporal_overlay(df, targets, key_params, events, fig_dir, features)

    # === 3. Event response overlay ===
    print("\n=== Phase 3: Event Response Overlay ===")
    event_values = df[group_col].unique().tolist() if group_col in df.columns else []
    event_path = generate_event_response_overlay(df, targets, group_col, event_values, fig_dir)

    # === 4. Simpson Paradox visualizations ===
    print("\n=== Phase 4: Simpson Paradox Visualizations ===")
    simpson_paths = []
    if group_col in df.columns:
        for param in key_params[:10]:  # top 10 by relevance
            if param in df.columns:
                sp = generate_simpson_visual(df, targets[0], param, group_col, fig_dir)
                if sp:
                    simpson_paths.append(sp)

    # === 5. Synchronization heatmap ===
    print("\n=== Phase 5: Synchronization Heatmap ===")
    sync_path = generate_synchronization_heatmap(df, targets, key_params, fig_dir)

    # === Compute structured visual analysis ===
    print("\n=== Phase 6: Computing temporal synchronization analysis ===")
    sync_analysis = analyze_temporal_synchronization(df, targets, key_params)

    # === Build chart inventory ===
    chart_inventory = []

    # Per-product overlays are the PRIMARY VLM inputs
    for pi, pp in enumerate(per_product_paths):
        fname = os.path.basename(pp)
        is_focus = 'focus' in fname
        chart_inventory.append({
            "figure": fname,
            "read_status": "READ_FAILED",
            "read_failure_reason": "Pre-VLM skeleton only; awaiting vlm-visual-analyzer",
            "purpose": f"{'【重点产品】' if is_focus else ''}Per-product time-aligned overlay — ALL process parameters + quality metrics on shared time axis for ONE product. VLM reads this to identify: synchronous groups, temporal precedence, event responses, drift patterns within a single homogeneous product.",
            "visual_questions": [
                "Which process parameters move together with quality targets?",
                "Which parameters change FIRST (precedence signals)?",
                "Are there visible anomaly windows where process+quality diverge?",
                "Is degradation linear or accelerating?",
                "Do any parameters show sudden jumps (event response)?"
            ],
            "read_order": pi + 1,
            "diagnostic_weight": "CRITICAL"
        })

    # Legacy global overlay
    if overlay_path:
        chart_inventory.append({
            "figure": "fig_vlm_temporal_overlay.png",
            "read_status": "READ_FAILED",
            "read_failure_reason": "Pre-VLM skeleton only; awaiting vlm-visual-analyzer",
            "purpose": "Global all-data overlay (for cross-product comparison reference). Prefer per-product overlays for detailed analysis.",
            "visual_questions": [
                "Which parameters move together? (synchronous groups)",
                "At event markers, which parameters jump? Which don't respond?",
                "Is the degradation linear or accelerating?"
            ],
            "read_order": len(per_product_paths) + 1,
            "diagnostic_weight": "STRONG"
        })

    if event_path:
        chart_inventory.append({
            "figure": "fig_vlm_event_response.png",
            "read_status": "READ_FAILED",
            "read_failure_reason": "Pre-VLM skeleton only",
            "purpose": "Event impact visualization — quality before/after transition",
            "visual_questions": [
                "Is there a visible quality change at the transition line?",
                "How big is the jump compared to normal variation?",
                "Does quality recover or only partially?"
            ],
            "read_order": len(per_product_paths) + 2,
            "diagnostic_weight": "STRONG"
        })

    if sync_path:
        chart_inventory.append({
            "figure": "fig_vlm_synchronization.png",
            "read_status": "READ_FAILED",
            "read_failure_reason": "Pre-VLM skeleton only",
            "purpose": "Rolling correlation stability over time",
            "visual_questions": [
                "Which parameters maintain stable correlation with quality?",
                "Are there periods where correlations break down?",
                "Does any parameter switch from positive to negative correlation?"
            ],
            "read_order": len(per_product_paths) + 3,
            "diagnostic_weight": "MODERATE"
        })

    for sp in simpson_paths:
        fname = os.path.basename(sp)
        chart_inventory.append({
            "figure": fname,
            "read_status": "READ_FAILED",
            "read_failure_reason": "Pre-VLM skeleton only",
            "purpose": "Simpson's Paradox check — correlation direction per stratum",
            "visual_questions": [
                "Does correlation direction reverse across strata?",
                "Are within-stratum correlations consistent?"
            ],
            "read_order": len(per_product_paths) + 4,
            "diagnostic_weight": "MODERATE"
        })

    # === Write visual_analysis.json ===
    total_charts = len(per_product_paths) + (1 if overlay_path else 0) + (1 if event_path else 0) + len(simpson_paths) + (1 if sync_path else 0)

    visual_analysis = {
        "generated_at": pd.Timestamp.now().isoformat(),
        "vlm_chart_count": total_charts,
        "observation_mode": "skeleton_pre_vlm",
        "chart_design_purpose": "Per-product time-aligned overlays with ALL process parameters + quality metrics on shared time axis. When multiple products exist, each product gets its own overlay; focus product (highest anomaly rate) is analyzed first.",
        "time_alignment_applicable": has_time,
        "primary_grouping_dimension": group_col,
        "n_products": n_products,
        "n_per_product_overlays": len(per_product_paths),
        "analysis_provenance": {
            "source_agent": "visual_analysis.py",
            "stage": "skeleton_pre_vlm",
            "skeleton_overwritten": False,
            "context_files_read": [
                "02_processed/cleaned_data.csv",
                "02_processed/feature_summary.json",
                "02_processed/validate_report.json",
                "01_ontology/ontology.json",
                "02_processed/production_regime_filter.json",
                "02_processed/anomaly_report.json"
            ],
            "figure_inputs_attempted": [],
            "figure_inputs_read_successfully": [],
            "grounding_summary": "Pre-VLM skeleton. Per-product time-aligned overlays generated with ALL process parameters. MUST be enhanced by vlm-visual-analyzer with ontology-grounded observations.",
            "grounding_sources": [
                "02_processed/feature_summary.json",
                "02_processed/validate_report.json",
                "01_ontology/ontology.json"
            ]
        },
        "cross_parameter_temporal_alignment": sync_analysis,
        "chart_inventory": chart_inventory,
        "visual_observations": [
            {
                "figure": chart_inventory[0]["figure"] if chart_inventory else "N/A",
                "observations": [
                    {
                        "type": "trend_morphology",
                        "description": "Placeholder — script-generated skeleton only. vlm-visual-analyzer MUST replace with grounded observations from actual image reading.",
                        "parameters_involved": [p for p in (targets + key_params) if p in df.columns][:5],
                        "estimated_lag": "unclear",
                        "confidence": "low",
                        "diagnostic_implication": "Do not treat as final visual evidence until vlm-visual-analyzer overwrites this skeleton.",
                        "statistical_cross_reference": {
                            "source_file": "02_processed/feature_summary.json",
                            "validation_note": "Skeleton placeholder — VLM sub-agent must replace"
                        },
                        "ontology_context": {
                            "parameter_physical_meanings": {},
                            "process_stage": "unknown"
                        }
                    }
                ]
            }
        ],
        "synthesis": "Pre-VLM scaffold. Per-product time-aligned overlays generated. Structured observations are placeholders only — vlm-visual-analyzer must provide grounded visual evidence.",
        "reading_guide": [
            {
                "for_agent": "diagnostician",
                "primary_sections_to_read": ["analysis_provenance"],
                "key_insights": ["This file is pre-VLM skeleton. Trust only final_vlm_output from vlm-visual-analyzer."]
            }
        ]
    }

    output_path = os.path.join(fig_dir, 'visual_analysis.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(visual_analysis, f, ensure_ascii=False, indent=2)
    print(f"\n  → {output_path}")
    print(f"\nDone. Generated {total_charts} VLM-specific charts + visual_analysis.json")
    print(f"  Per-product overlays: {len(per_product_paths)}")
    print(f"  Legacy overlays: {1 if overlay_path else 0}")
    print(f"  Event response: {1 if event_path else 0}")
    print(f"  Simpson checks: {len(simpson_paths)}")
    print(f"  Sync heatmap: {1 if sync_path else 0}")


if __name__ == '__main__':
    main()
