#!/usr/bin/env python3
"""
Preprocess tablet_press data: merge, clean, derive features, quality report.
Batch pharmaceutical compression scenario.
"""
import json
import csv
import os
import sys
from collections import defaultdict, Counter

SKILL_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../.claude/skills/industrial-deep-diagnostic'))
RUN_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_PATH = os.path.join(RUN_DIR, '00_input')

# Load converted JSONs
with open('/tmp/batch_record.json') as f:
    batch_records = json.load(f)
with open('/tmp/tablet_test_results.json') as f:
    tablet_results = json.load(f)

# Build batch lookup
batch_lookup = {}
for rec in batch_records:
    batch_lookup[rec['batch_id']] = rec

# Merge datasets: add batch-level process params to each tablet record
process_param_cols = [
    'compression_force_kN', 'pre_compression_force_kN', 'turret_speed_rpm',
    'fill_depth_mm', 'dwell_time_ms', 'blend_moisture_pct', 'lubricant_level_pct',
    'blend_uniformity_index', 'compression_zone_temp_C', 'ambient_temp_C',
    'ambient_humidity_pct', 'ts_start', 'batch_day', 'punch_serial', 'operator_id'
]

merged = []
for t in tablet_results:
    bid = t['batch_id']
    if bid in batch_lookup:
        rec = batch_lookup[bid]
        merged_row = dict(t)
        for col in process_param_cols:
            if col in rec:
                merged_row[col] = rec[col]
        merged.append(merged_row)

print(f"Merged records: {len(merged)} (tablet_test had {len(tablet_results)}, batch_record had {len(batch_records)})")

# Convert numeric fields
numeric_fields = [
    'tablet_weight_mg', 'hardness_N', 'friability_pct', 'disintegration_time_min',
    'thickness_mm', 'compression_force_kN', 'pre_compression_force_kN',
    'turret_speed_rpm', 'fill_depth_mm', 'dwell_time_ms', 'blend_moisture_pct',
    'lubricant_level_pct', 'blend_uniformity_index', 'compression_zone_temp_C',
    'ambient_temp_C', 'ambient_humidity_pct', 'batch_seq', 'tablet_seq', 'batch_day', 'station'
]

for row in merged:
    for field in numeric_fields:
        if field in row and row[field] is not None:
            try:
                row[field] = float(row[field])
            except (ValueError, TypeError):
                pass

# --- Data Quality Report ---
quality_report = {
    "source_files": ["batch_record_2025Q4.csv", "tablet_test_results_2025Q4.csv"],
    "total_tablet_records": len(merged),
    "total_batches": len(batch_records),
    "missing_value_analysis": {},
    "outlier_flagging": {},
    "sorting_validation": {},
    "scenario_specific": {},
    "data_quality_summary": {}
}

# 1. Missing values
missing_counts = {}
for field in numeric_fields + ['batch_id', 'defect_grade', 'punch_serial', 'operator_id']:
    missing = sum(1 for row in merged if field not in row or row[field] is None or row[field] == '')
    if missing > 0:
        missing_counts[field] = {"missing_count": missing, "missing_pct": round(missing/len(merged)*100, 2)}

quality_report["missing_value_analysis"] = {
    "has_missing": len(missing_counts) > 0,
    "missing_fields": missing_counts if missing_counts else "None found"
}

# 2. Outlier flagging (IQR method)
outlier_report = {}
for field in ['hardness_N', 'friability_pct', 'disintegration_time_min', 'tablet_weight_mg', 'thickness_mm']:
    vals = [row[field] for row in merged if field in row and row[field] is not None]
    vals_sorted = sorted(vals)
    n = len(vals_sorted)
    q1 = vals_sorted[int(n * 0.25)]
    q3 = vals_sorted[int(n * 0.75)]
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    outliers = [v for v in vals if v < lower or v > upper]
    outlier_report[field] = {
        "q1": round(q1, 3),
        "q3": round(q3, 3),
        "iqr": round(iqr, 3),
        "lower_fence": round(lower, 3),
        "upper_fence": round(upper, 3),
        "outlier_count": len(outliers),
        "outlier_pct": round(len(outliers)/len(vals)*100, 2),
        "outlier_range": [round(min(outliers), 3), round(max(outliers), 3)] if outliers else None
    }
quality_report["outlier_flagging"] = outlier_report

# 3. Sorting validation - check if batch_seq is sequential (batch-sorted, not time-sorted for tablets)
seq_vals = [row['batch_seq'] for row in merged]
is_sorted = all(seq_vals[i] <= seq_vals[i+1] for i in range(len(seq_vals)-1))
# Also check within-batch tablet_seq
within_batch_ok = True
current_batch = None
last_tablet_seq = 0
for row in merged:
    if row['batch_id'] != current_batch:
        current_batch = row['batch_id']
        last_tablet_seq = row['tablet_seq']
    else:
        if row['tablet_seq'] < last_tablet_seq:
            within_batch_ok = False
            break
        last_tablet_seq = row['tablet_seq']

quality_report["sorting_validation"] = {
    "is_batch_seq_sorted_ascending": is_sorted,
    "is_within_batch_tablet_seq_sorted": within_batch_ok,
    "note": "Data is sorted by batch_seq then tablet_seq. Time series info from batch_record.ts_start join. Data is NOT raw time-sorted (tablet-level has no timestamp) - batch_grouped sorting is appropriate for this hierarchical batch structure.",
    "appropriate_for_analysis": True,
    "warning": "Lag correlations across tablet_seq within a batch are not temporal - use batch_seq-level time axis for temporal analysis."
}

# 4. Scenario-specific derived features
for row in merged:
    # Compression ratio (main/pre)
    if row.get('pre_compression_force_kN', 0) and row['pre_compression_force_kN'] > 0:
        row['compression_ratio'] = round(row.get('compression_force_kN', 0) / row['pre_compression_force_kN'], 3)
    else:
        row['compression_ratio'] = None

    # Hardness-friability index: higher hardness + lower friability = better quality
    if row.get('hardness_N') and row.get('friability_pct'):
        if row['friability_pct'] > 0:
            row['hardness_friability_ratio'] = round(row['hardness_N'] / row['friability_pct'], 2)
        else:
            row['hardness_friability_ratio'] = None
    else:
        row['hardness_friability_ratio'] = None

    # Weight deviation from target
    if row.get('tablet_weight_mg'):
        row['weight_deviation_pct'] = round((row['tablet_weight_mg'] - 500) / 500 * 100, 3)
    else:
        row['weight_deviation_pct'] = None

    # Defect binary (for classification)
    row['defect_flag'] = 1 if row.get('defect_grade', 'A') in ('B', 'C') else 0

quality_report["scenario_specific"] = {
    "derived_features": [
        "compression_ratio = compression_force_kN / pre_compression_force_kN",
        "hardness_friability_ratio = hardness_N / friability_pct",
        "weight_deviation_pct = (tablet_weight_mg - 500) / 500 * 100",
        "defect_flag = 1 if defect_grade in (B, C) else 0"
    ]
}

# 5. Defect rate summary
defect_counts = Counter(row['defect_grade'] for row in merged)
quality_report["data_quality_summary"] = {
    "total_records": len(merged),
    "defect_distribution": dict(defect_counts),
    "defect_rate_pct": round(defect_counts.get('B', 0) / len(merged) * 100, 1),
    "failure_rate_pct": round(defect_counts.get('C', 0) / len(merged) * 100, 1),
    "total_defect_rate_pct": round((defect_counts.get('B', 0) + defect_counts.get('C', 0)) / len(merged) * 100, 1)
}

# Save data quality report
quality_path = os.path.join(RUN_DIR, '02_processed', 'data_quality_report.json')
with open(quality_path, 'w') as f:
    json.dump(quality_report, f, indent=2, ensure_ascii=False)
print(f"Data quality report saved to {quality_path}")

# Save cleaned CSV
cleaned_csv_path = os.path.join(RUN_DIR, '02_processed', 'cleaned_data.csv')
all_fields = list(merged[0].keys())
with open(cleaned_csv_path, 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=all_fields)
    writer.writeheader()
    writer.writerows(merged)
print(f"Cleaned data saved to {cleaned_csv_path} ({len(merged)} rows, {len(all_fields)} columns)")

# Save cleaned JSON
cleaned_json_path = os.path.join(RUN_DIR, '02_processed', 'cleaned_data.json')
with open(cleaned_json_path, 'w') as f:
    json.dump(merged, f, indent=2, ensure_ascii=False)
print(f"Cleaned data JSON saved to {cleaned_json_path}")

# Also save the data.json (merged, but without derived features for stats.mjs compatibility)
data_json_path = os.path.join(RUN_DIR, '02_processed', 'data.json')
# Remove derived features for stats.mjs compatibility
simple_merged = []
for row in merged:
    r = {k: v for k, v in row.items() if k not in ('compression_ratio', 'hardness_friability_ratio', 'weight_deviation_pct', 'defect_flag')}
    simple_merged.append(r)
with open(data_json_path, 'w') as f:
    json.dump(simple_merged, f, indent=2, ensure_ascii=False)
print(f"Data JSON saved to {data_json_path}")

print("\nPreprocessing complete!")
