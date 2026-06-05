"""
VLM-friendly visualization and visual analysis engine.

Design principles:
1. Time-aligned overlay: All parameters normalized, direction-aligned, on shared time axis
2. Event markers clearly visible (red dashed lines with text)
3. Anomaly regions shaded
4. Large fonts, high contrast, clean layout
5. Generates both PNG images AND structured visual_analysis.json

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

def load_data(run_dir):
    """Load cleaned data and all analysis artifacts."""
    cleaned_csv = os.path.join(run_dir, '02_processed', 'cleaned_data.csv')
    df = pd.read_csv(cleaned_csv)
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Load feature summary for correlation info
    feature_path = os.path.join(run_dir, '02_processed', 'feature_summary.json')
    features = json.load(open(feature_path)) if os.path.exists(feature_path) else {}

    # Load validate report
    validate_path = os.path.join(run_dir, '02_processed', 'validate_report.json')
    validate = json.load(open(validate_path)) if os.path.exists(validate_path) else {}

    # Load ontology
    ontology_path = os.path.join(run_dir, '01_ontology', 'ontology.json')
    ontology = json.load(open(ontology_path)) if os.path.exists(ontology_path) else {}

    return df, features, validate, ontology


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


def generate_temporal_overlay(df, targets, key_params, events, fig_dir, features=None):
    """
    THE KEY VLM CHART: Time-aligned overlay with all parameters normalized and direction-aligned.

    Design for VLM readability:
    - z-score normalization so different units are comparable
    - Reverse negative-correlation params so ALL lines move in same direction when process is healthy
    - Clear event markers with text labels
    - Large legend, high contrast
    """
    primary_target = targets[0] if targets else None
    all_params = targets + [p for p in key_params if p not in targets]

    fig, ax = plt.subplots(figsize=(20, 10))
    colors = plt.cm.tab10(np.linspace(0, 1, len(all_params)))
    line_styles = ['-', '--', '-.', ':', '-', '--', '-.', ':', '-', '--']

    legend_entries = []

    for idx, col in enumerate(all_params):
        if col not in df.columns:
            continue
        values = df[col].dropna()
        if values.std() == 0:
            continue

        # z-score normalize
        z_values = (df[col] - df[col].mean()) / df[col].std()

        # Reverse direction if negatively correlated with primary target
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

    # Event markers
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

    # Normalize primary target
    values = (df[primary_target] - df[primary_target].mean()) / df[primary_target].std()

    # Find transition point
    if len(event_values) >= 2:
        transition_idx = df[df[event_col] == event_values[1]].index[0] if event_values[1] in df[event_col].values else len(df) // 2
    else:
        transition_idx = len(df) // 2

    # Before and after
    before = df.iloc[:transition_idx]
    after = df.iloc[transition_idx:]

    ax.scatter(before['timestamp'], (before[primary_target] - df[primary_target].mean()) / df[primary_target].std(),
               s=8, alpha=0.5, color=colors['before'], label=f'{event_values[0]} (before)')
    ax.scatter(after['timestamp'], (after[primary_target] - df[primary_target].mean()) / df[primary_target].std(),
               s=8, alpha=0.5, color=colors['after'], label=f'{event_values[1]} (after)')

    # Transition line
    transition_time = df['timestamp'].iloc[transition_idx]
    ax.axvline(transition_time, color='red', linestyle='--', linewidth=2.5, alpha=0.9)
    ax.text(transition_time, ax.get_ylim()[1] * 0.95, '  EVENT TRANSITION',
            rotation=90, va='top', ha='left', fontsize=13, color='red', fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8, edgecolor='red'))

    # Mean lines
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

        # Regression line
        if grp[param].std() > 0:
            z = np.polyfit(grp[param].dropna(), grp[target].dropna(), 1)
            x_range = np.linspace(grp[param].min(), grp[param].max(), 100)
            ax.plot(x_range, np.polyval(z, x_range), color=color, linewidth=3, alpha=0.8)

        direction_text = "↗ POSITIVE" if r >= 0 else "↘ NEGATIVE"
        ax.set_title(f'{grp_name}\nr = {r:.3f}  {direction_text}',
                     fontsize=14, fontweight='bold', color=color)
        ax.set_xlabel(param, fontsize=12)
        ax.set_ylabel(target, fontsize=12)
        ax.tick_params(axis='both', labelsize=11)
        ax.grid(True, alpha=0.3)

    # Check for reversal
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

    # Compute rolling correlation with primary target
    primary = targets[0]
    window = min(72, len(df) // 4)  # 72h or 1/4 of data

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
    """
    Compute cross-parameter temporal alignment statistics for visual_analysis.json.
    Returns structured data about which parameters are synchronized.
    """
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

    # Group by correlation strength with primary target
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
    df, features, validate, ontology = load_data(run_dir)

    # --- Dynamic defaults from ontology / scenario_classification ---
    targets = []
    key_params = []
    group_col = None

    # Try reading scenario_classification.json for target/predictor info
    scenario_path = os.path.join(run_dir, '02_processed', 'scenario_classification.json')
    if os.path.exists(scenario_path):
        try:
            scenario = json.load(open(scenario_path))
            # No-op: scenario_classification doesn't have explicit target/predictor lists
        except Exception:
            pass

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

    # Fallback: if ontology didn't provide targets, infer from column names
    if not targets:
        target_keywords = ['quality', 'defect', 'yield', 'conversion', 'selectivity', 'thickness',
                          'roughness', 'purity', 'grade', 'score', 'index']
        for col in df.columns:
            if any(kw in col.lower() for kw in target_keywords):
                targets.append(col)
    if not targets:
        # Last resort: use first numeric column
        for col in df.columns:
            if df[col].dtype in ('float64', 'int64') and col != 'timestamp':
                targets.append(col)
                break

    # Fallback: if ontology didn't provide key_params, use top correlated columns
    if not key_params:
        exclude = set(targets) | {'timestamp', 'time', 'index'}
        for col in df.columns:
            if col not in exclude and df[col].dtype in ('float64', 'int64'):
                key_params.append(col)
        key_params = key_params[:8]  # cap at 8 for readability

    # Detect group column: first categorical column with 2-20 unique values
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

    # Parse CLI args (override dynamic defaults)
    for i, arg in enumerate(sys.argv[2:], 2):
        if arg.startswith('--target-cols'):
            targets = sys.argv[i+1].split(',')
        elif arg.startswith('--key-params'):
            key_params = sys.argv[i+1].split(',')
        elif arg.startswith('--group-col'):
            group_col = sys.argv[i+1]

    print(f"\nGenerating VLM-friendly visualizations for {len(df)} rows, {len(targets)} targets, {len(key_params)} params")
    print(f"  Targets: {targets}")
    print(f"  Key params: {key_params}")
    print(f"  Group col: {group_col}")

    # --- Dynamic event detection ---
    events = []
    if group_col and group_col in df.columns and df[group_col].nunique() > 1:
        # Detect transitions in group_col
        transitions = df[group_col] != df[group_col].shift(1)
        transition_indices = df[transitions].index.tolist()
        for idx in transition_indices[1:]:  # skip first row
            label = str(df[group_col].iloc[idx])
            events.append((idx, f'{group_col} → {label}'))
    # Also check ontology for explicit events
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

    # === Generate VLM-specific charts ===

    print("\n1. Temporal overlay (VLM key chart)...")
    overlay_path = generate_temporal_overlay(df, targets, key_params, events, fig_dir, features)

    print("\n2. Event response overlay...")
    event_values = df[group_col].unique().tolist() if group_col in df.columns else []
    event_path = generate_event_response_overlay(df, targets, group_col, event_values, fig_dir)

    print("\n3. Simpson Paradox visualizations...")
    simpson_paths = []
    if group_col in df.columns:
        for param in key_params:
            if param in df.columns:
                sp = generate_simpson_visual(df, targets[0], param, group_col, fig_dir)
                if sp:
                    simpson_paths.append(sp)

    print("\n4. Synchronization heatmap...")
    sync_path = generate_synchronization_heatmap(df, targets, key_params, fig_dir)

    # === Compute structured visual analysis ===

    print("\n5. Computing temporal synchronization analysis...")
    sync_analysis = analyze_temporal_synchronization(df, targets, key_params)

    # === Write visual_analysis.json ===

    visual_analysis = {
        "generated_at": pd.Timestamp.now().isoformat(),
        "vlm_chart_count": 1 + (1 if event_path else 0) + len(simpson_paths) + (1 if sync_path else 0),
        "observation_mode": "skeleton_pre_vlm",
        "chart_design_purpose": "VLM-readable charts with time-aligned overlays, event markers, and direction-reversed parameters",
        "time_alignment_applicable": "timestamp" in df.columns,
        "analysis_provenance": {
            "source_agent": "visual_analysis.py",
            "stage": "skeleton_pre_vlm",
            "skeleton_overwritten": False,
            "context_files_read": [
                "02_processed/cleaned_data.csv",
                "02_processed/feature_summary.json",
                "02_processed/validate_report.json",
                "01_ontology/ontology.json"
            ],
            "figure_inputs_attempted": [],
            "figure_inputs_read_successfully": [],
            "grounding_summary": "Pre-VLM skeleton generated from statistical outputs and chart design intent only. This file MUST be enriched or replaced by vlm-visual-analyzer before Step 3 can be considered complete.",
            "grounding_sources": [
                "02_processed/feature_summary.json",
                "02_processed/validate_report.json",
                "01_ontology/ontology.json"
            ]
        },
        "cross_parameter_temporal_alignment": sync_analysis,
        "chart_inventory": [
            {
                "figure": "fig_vlm_temporal_overlay.png",
                "read_status": "READ_FAILED",
                "read_failure_reason": "Pre-VLM skeleton only; no image-reading agent has inspected this figure yet",
                "purpose": "PRIMARY VLM INPUT — All parameters normalized and direction-aligned on shared time axis",
                "visual_questions": [
                    "Which parameters move together? (synchronous groups)",
                    "At event markers, which parameters jump? Which don't respond?",
                    "Is the degradation linear or accelerating?",
                    "Do any parameters show independent (random) behavior?"
                ],
                "read_order": 1,
                "diagnostic_weight": "CRITICAL"
            },
            {
                "figure": "fig_vlm_event_response.png",
                "read_status": "READ_FAILED" if event_path else "NOT_GENERATED",
                "read_failure_reason": "Pre-VLM skeleton only; no image-reading agent has inspected this figure yet" if event_path else "Figure not generated for this dataset",
                "purpose": "Event impact visualization — quality before/after event transition",
                "visual_questions": [
                    "Is there a visible quality change at the transition line?",
                    "How big is the jump compared to normal variation?",
                    "Does quality recover to initial levels or only partially?"
                ],
                "read_order": 2,
                "diagnostic_weight": "STRONG"
            },
            {
                "figure": "fig_vlm_synchronization.png",
                "read_status": "READ_FAILED" if sync_path else "NOT_GENERATED",
                "read_failure_reason": "Pre-VLM skeleton only; no image-reading agent has inspected this figure yet" if sync_path else "Figure not generated for this dataset",
                "purpose": "Rolling correlation stability — which correlations are consistent over time",
                "visual_questions": [
                    "Which parameters maintain stable correlation with quality?",
                    "Are there periods where correlations break down?",
                    "Does any parameter switch from positive to negative correlation?"
                ],
                "read_order": 3,
                "diagnostic_weight": "MODERATE"
            }
        ],
        "visual_observations": [
            {
                "figure": "fig_vlm_temporal_overlay.png",
                "observations": [
                    {
                        "type": "trend_morphology",
                        "description": "Placeholder only — script-generated skeleton. No direct image observation has been made yet.",
                        "parameters_involved": [p for p in (targets + key_params) if p in df.columns][:4],
                        "estimated_lag": "unclear",
                        "confidence": "low",
                        "diagnostic_implication": "Do not treat this as final visual evidence until vlm-visual-analyzer overwrites the skeleton with grounded observations.",
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
        "synthesis": "Pre-VLM scaffold only. Statistical synchronization structures and VLM-targeted chart inventory are prepared, but no grounded image interpretation has been completed yet.",
        "reading_guide": [
            {
                "for_agent": "diagnostician",
                "primary_sections_to_read": ["analysis_provenance"],
                "key_insights": ["This file is a pre-VLM skeleton and must not be treated as final visual evidence."]
            }
        ]
    }

    output_path = os.path.join(fig_dir, 'visual_analysis.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(visual_analysis, f, ensure_ascii=False, indent=2)
    print(f"\n  → {output_path}")
    print(f"\nDone. Generated {visual_analysis['vlm_chart_count']} VLM-specific charts + visual_analysis.json")


if __name__ == '__main__':
    main()
