#!/usr/bin/env python3
"""
Build Causal Evidence Map from validated statistics.
Filters out Simpson's Paradox and trend-confounded (>30% attenuation) correlations.
Identifies root cause candidates (parameters connecting to multiple quality targets).
"""

import json
import os

RUN_DIR = "/Volumes/laxer/codes/skills/ industrial-deep-diagnostic/.claude/workspace/diagnostic-runs/202605291347083_paper_machine_headbox"
FEATURE_FILE = os.path.join(RUN_DIR, "02_processed", "feature_summary.json")
VALIDATE_FILE = os.path.join(RUN_DIR, "02_processed", "validate_report.json")
OUT_FILE = os.path.join(RUN_DIR, "02_processed", "causal_evidence_map.json")

with open(FEATURE_FILE) as f:
    features = json.load(f)

with open(VALIDATE_FILE) as f:
    validation = json.load(f)

target_analysis = features.get('target_analysis', {})
stratified = features.get('stratified_analysis', []) or []
target_cols = features['data_summary']['target_columns']
group_values = features['data_summary'].get('group_values', [])

# ─── Build Simpson exclusion set (only true paradox = direction reversal) ──
simpson_exclude = set()
for s in stratified:
    if s.get('simpson_paradox'):
        simpson_exclude.add(f"{s['target']}::{s['parameter']}")

# ─── Build trend-confounded exclusion set (>30% attenuation in detrended) ──
trend_exclude = set()
# From validate_report's trend_confounding_analysis
trend_analysis = validation.get('trend_confounding_analysis', [])
if trend_analysis:
    for tc in trend_analysis:
        if tc.get('attenuation_pct', 0) > 30:
            trend_exclude.add(f"{tc.get('target', '')}::{tc.get('parameter', '')}")
# Also check per-target detrended correlations in feature_summary
for target in target_cols:
    ta = target_analysis.get(target, {})
    detrended = ta.get('detrended_correlations', {})
    for param, det in detrended.items():
        if det.get('attenuation_pct', 0) is not None and det['attenuation_pct'] > 30:
            trend_exclude.add(f"{target}::{param}")

# ─── Build stratified attenuation list (informational, not excluded) ──
stratified_info = {}
for s in stratified:
    key = f"{s['target']}::{s['parameter']}"
    stratified_info[key] = {
        "severity": s.get('severity'),
        "max_attenuation_pct": s.get('max_attenuation_pct'),
        "simpson_paradox": s.get('simpson_paradox'),
        "full_r": s.get('full_r')
    }

# ─── Build validated edge list ──────────────────────────
edges = []
process_vars = [
    'headbox_pressure_kPa', 'approach_flow_lpm', 'fan_pump_speed_rpm',
    'white_water_consistency_pct', 'retention_aid_dosage_ppm',
    'slice_opening_mm', 'machine_speed_mmin', 'stock_temp_C',
    'jet_to_wire_ratio', 'vacuum_pump1_kPa', 'vacuum_pump2_kPa'
]

for target in target_cols:
    if target not in target_analysis:
        continue
    ta = target_analysis[target]
    pearson = ta.get('pearson_correlations', {})
    spearman = ta.get('spearman_correlations', {})
    detrended = ta.get('detrended_correlations', {})
    best_lags = ta.get('best_lags', {})

    for param in process_vars:
        if param not in pearson:
            continue
        pair_key = f"{target}::{param}"

        # Skip excluded
        if pair_key in simpson_exclude or pair_key in trend_exclude:
            continue

        r = pearson[param].get('r', 0)
        rho = spearman[param].get('r', 0)
        p = pearson[param].get('p', 0)

        det = detrended.get(param, {})
        det_r = det.get('detrended_r', 0)
        attenuation = det.get('attenuation_pct', 0)

        bl = best_lags.get(param, {})
        best_lag_val = bl.get('lag', 0)
        best_lag_r = bl.get('r', 0)

        spearman_div = abs(r - rho)

        att_val = attenuation if attenuation is not None else 0
        is_simpson = pair_key in simpson_exclude
        is_trend = pair_key in trend_exclude
        is_valid = p < 0.05 and not is_simpson and not is_trend

        si = stratified_info.get(pair_key, {})
        edge = {
            "parameter": param,
            "target": target,
            "pearson_r": round(r, 4),
            "spearman_rho": round(rho, 4),
            "pearson_p": round(p, 6),
            "detrended_r": round(det_r, 4) if det_r is not None else None,
            "attenuation_pct": round(att_val, 2),
            "abs_r": round(abs(r), 4),
            "spearman_divergence": round(spearman_div, 4),
            "best_lag": best_lag_val,
            "best_lag_r": round(best_lag_r, 4),
            "_validated": is_valid,
            "_excluded_simpson": is_simpson,
            "_excluded_trend": is_trend,
            "_stratified_severity": si.get('severity'),
            "_stratified_attenuation_pct": si.get('max_attenuation_pct')
        }
        edges.append(edge)

# Sort by |r| descending
edges.sort(key=lambda e: e['abs_r'], reverse=True)

# Separate validated vs excluded edges
validated_edges = [e for e in edges if e['_validated']]

# ─── Root Cause Candidates ──────────────────────────────
# Parameters that have |r| > 0.2 with 2+ quality targets
param_connections = {}
for edge in validated_edges:
    if edge['abs_r'] >= 0.2:
        param = edge['parameter']
        if param not in param_connections:
            param_connections[param] = []
        param_connections[param].append({
            "target": edge['target'],
            "abs_r": edge['abs_r'],
            "pearson_r": edge['pearson_r']
        })

root_cause_candidates = []
for param, connections in param_connections.items():
    if len(connections) >= 2:
        root_cause_candidates.append({
            "parameter": param,
            "n_targets_connected": len(connections),
            "mean_abs_r": round(sum(c['abs_r'] for c in connections) / len(connections), 4),
            "connections": sorted(connections, key=lambda c: c['abs_r'], reverse=True)
        })

# Sort by number of connections, then by mean_abs_r
root_cause_candidates.sort(key=lambda r: (r['n_targets_connected'], r['mean_abs_r']), reverse=True)

# ─── Colinear Groups ────────────────────────────────────
# Identify groups of process variables that are highly correlated with each other
pearson_matrix = features.get('correlation_matrices', {}).get('pearson', {})
colinear_groups = []
processed = set()
for p1 in process_vars:
    if p1 in processed:
        continue
    group = [p1]
    for p2 in process_vars:
        if p2 == p1 or p2 in processed:
            continue
        r12 = pearson_matrix.get(p1, {}).get(p2, 0)
        if abs(r12) > 0.7:
            group.append(p2)
            processed.add(p2)
    if len(group) > 1:
        colinear_groups.append(group)
        processed.add(p1)

# ─── Change Points Impact ───────────────────────────────
change_points = validation.get('change_point_analysis', {}).get('change_points_detected', 0)

# ─── Build Final Map ────────────────────────────────────
causal_map = {
    "run_id": "202605291347083_paper_machine_headbox",
    "build_info": {
        "total_edges_evaluated": len(edges),
        "simpson_excluded": len(simpson_exclude),
        "trend_confounded_excluded": len(trend_exclude),
        "validated_edges": sum(1 for e in edges if e['_validated']),
        "significance_threshold": 0.05,
        "attenuation_threshold_pct": 30
    },
    "all_edges": edges,
    "validated_edges": validated_edges,
    "root_cause_candidates": root_cause_candidates,
    "colinear_groups": colinear_groups,
    "change_points_detected": change_points,
    "group_stratification": {
        "group_column": "grade_running",
        "group_values": group_values,
        "simpson_paradox_detected": len(simpson_exclude) > 0
    },
    "quality_target_direction": {
        "cd_basis_weight_cv_pct": "lower_better",
        "formation_index": "higher_better",
        "strength_rel_pct": "higher_better",
        "defect_grade_numeric": "higher_better"
    }
}

with open(OUT_FILE, 'w', encoding='utf-8') as f:
    json.dump(causal_map, f, indent=2, ensure_ascii=False)

# ─── Print Summary ──────────────────────────────────────
print(f"Causal Evidence Map saved to {OUT_FILE}")
print(f"\nSummary:")
print(f"  Total edges: {causal_map['build_info']['total_edges_evaluated']}")
print(f"  Validated edges: {causal_map['build_info']['validated_edges']}")
print(f"  Simpson excluded: {causal_map['build_info']['simpson_excluded']}")
print(f"  Trend confounded excluded: {causal_map['build_info']['trend_confounded_excluded']}")
print(f"  Root cause candidates: {len(root_cause_candidates)}")
for rc in root_cause_candidates[:5]:
    print(f"    {rc['parameter']}: {rc['n_targets_connected']} targets, mean |r|={rc['mean_abs_r']}")
print(f"  Colinear groups: {len(colinear_groups)}")
for cg in colinear_groups:
    print(f"    {cg}")
