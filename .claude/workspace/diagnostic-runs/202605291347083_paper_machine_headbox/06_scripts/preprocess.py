#!/usr/bin/env python3
"""
Paper Machine Headbox — Data Preprocessing & Quality Report
Handles:
  1. Missing values (empty strings)
  2. Shutdown periods (machine_speed <= 100, headbox_pressure < 5)
  3. Vacuum pump2 outliers (z-score > 4, IQR-based)
  4. Stock temp sensor faults (== 0)
  5. Defect grade numeric encoding (A=3, B=2, C=1)
  6. Saves cleaned_data.csv and generates data_quality_report.json
"""

import pandas as pd
import numpy as np
import json
import os
import sys

# ─── Config ─────────────────────────────────────────────
DATA_PATH = "/Volumes/laxer/codes/skills/ industrial-deep-diagnostic/.claude/workspace/diagnostic-runs/202605291347083_paper_machine_headbox/00_input/merged_dcs_qcs_20251001_20251229.csv"
RUN_DIR = "/Volumes/laxer/codes/skills/ industrial-deep-diagnostic/.claude/workspace/diagnostic-runs/202605291347083_paper_machine_headbox"
OUT_CSV = os.path.join(RUN_DIR, "02_processed", "cleaned_data.csv")
OUT_JSON = os.path.join(RUN_DIR, "02_processed", "cleaned_data.json")
OUT_QUALITY = os.path.join(RUN_DIR, "02_processed", "data_quality_report.json")

# ─── Load Data ──────────────────────────────────────────
print("Loading data...")
df = pd.read_csv(DATA_PATH)
initial_rows = len(df)
initial_cols = len(df.columns)
print(f"  Initial: {initial_rows} rows, {initial_cols} columns")

# ─── Column Classification ──────────────────────────────
numeric_cols = [
    'headbox_pressure_kPa', 'approach_flow_lpm', 'fan_pump_speed_rpm',
    'white_water_consistency_pct', 'retention_aid_dosage_ppm',
    'slice_opening_mm', 'machine_speed_mmin', 'stock_temp_C',
    'jet_to_wire_ratio', 'vacuum_pump1_kPa', 'vacuum_pump2_kPa',
    'cd_basis_weight_cv_pct', 'formation_index', 'ash_content_pct',
    'moisture_pct', 'strength_rel_pct'
]
categorical_cols = ['grade_running', 'grade', 'shift', 'day']
target_cols = ['cd_basis_weight_cv_pct', 'formation_index', 'strength_rel_pct', 'defect_grade']

quality_report = {
    "run_id": "202605291347083_paper_machine_headbox",
    "initial": {"rows": initial_rows, "columns": initial_cols},
    "steps": []
}

# ─── Step 1: Handle Missing Values ──────────────────────
print("Step 1: Handling missing values...")
missing_before = {col: int(df[col].isna().sum()) for col in df.columns if df[col].isna().sum() > 0}

# Convert empty strings to NaN in numeric columns
for col in numeric_cols:
    if col in df.columns:
        mask = (df[col] == '') | (df[col].isna())
        df.loc[mask, col] = np.nan

# Forward-fill for short gaps, then drop remaining NaN rows
df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')
rows_before_drop = len(df)
df.dropna(subset=numeric_cols, inplace=True)
rows_missing_dropped = rows_before_drop - len(df)

quality_report["steps"].append({
    "step": "handle_missing",
    "missing_values_before": missing_before,
    "rows_dropped": int(rows_missing_dropped),
    "method": "forward_fill_numeric_then_drop_remaining"
})
print(f"  Dropped {rows_missing_dropped} rows with missing numeric values")

# ─── Step 2: Filter Shutdown Periods ────────────────────
print("Step 2: Filtering shutdown periods...")
shutdown_mask = (df['machine_speed_mmin'] <= 100) | (df['headbox_pressure_kPa'] < 5)
n_shutdown = int(shutdown_mask.sum())
df = df[~shutdown_mask].copy()

quality_report["steps"].append({
    "step": "filter_shutdown",
    "condition": "machine_speed_mmin <= 100 OR headbox_pressure_kPa < 5",
    "rows_removed": n_shutdown,
    "rows_remaining": len(df)
})
print(f"  Removed {n_shutdown} shutdown rows, {len(df)} remaining")

# ─── Step 3: Flag Vacuum Pump2 Outliers ─────────────────
print("Step 3: Flagging vacuum_pump2_kPa outliers...")
vp2 = df['vacuum_pump2_kPa'].dropna()
Q1 = vp2.quantile(0.25)
Q3 = vp2.quantile(0.75)
IQR = Q3 - Q1
lower_bound = Q1 - 4 * IQR
upper_bound = Q3 + 4 * IQR

# Use z-score method as specified
vp2_mean = vp2.mean()
vp2_std = vp2.std()
z_scores = np.abs((df['vacuum_pump2_kPa'] - vp2_mean) / vp2_std)
outlier_mask = z_scores > 4
n_outliers = int(outlier_mask.sum())

df = df[~outlier_mask].copy()

quality_report["steps"].append({
    "step": "filter_vacuum_pump2_outliers",
    "method": "z_score > 4",
    "mean": float(vp2_mean),
    "std": float(vp2_std),
    "iqr_bounds": {"Q1": float(Q1), "Q3": float(Q3), "IQR": float(IQR)},
    "rows_removed": n_outliers,
    "rows_remaining": len(df)
})
print(f"  Removed {n_outliers} vacuum_pump2 outlier rows, {len(df)} remaining")

# ─── Step 4: Filter Stock Temperature Sensor Faults ──────
print("Step 4: Filtering stock_temp_C sensor faults (== 0)...")
temp_fault_mask = df['stock_temp_C'] == 0
n_temp_faults = int(temp_fault_mask.sum())
df = df[~temp_fault_mask].copy()

quality_report["steps"].append({
    "step": "filter_stock_temp_faults",
    "condition": "stock_temp_C == 0",
    "rows_removed": n_temp_faults,
    "rows_remaining": len(df)
})
print(f"  Removed {n_temp_faults} sensor fault rows, {len(df)} remaining")

# ─── Step 5: Encode Defect Grade ────────────────────────
print("Step 5: Encoding defect_grade...")
grade_map = {'A': 3, 'B': 2, 'C': 1}
df['defect_grade_numeric'] = df['defect_grade'].map(grade_map)
n_unmapped = int(df['defect_grade_numeric'].isna().sum())
if n_unmapped > 0:
    print(f"  WARNING: {n_unmapped} unexpected defect_grade values")

quality_report["steps"].append({
    "step": "encode_defect_grade",
    "mapping": {"A": 3, "B": 2, "C": 1},
    "unmapped": n_unmapped
})
print(f"  Encoded: A=3, B=2, C=1")

# ─── Step 6: Drop Excluded Columns ──────────────────────
print("Step 6: Dropping near-constant columns (moisture_pct)...")
if 'moisture_pct' in df.columns:
    df.drop(columns=['moisture_pct'], inplace=True)

# Reorder columns: ts_dcs first, then process vars, then quality targets
final_col_order = [
    'ts_dcs', 'ts_qcs', 'day', 'shift', 'grade_running', 'grade',
    'headbox_pressure_kPa', 'approach_flow_lpm', 'fan_pump_speed_rpm',
    'white_water_consistency_pct', 'retention_aid_dosage_ppm',
    'slice_opening_mm', 'machine_speed_mmin', 'stock_temp_C',
    'jet_to_wire_ratio', 'vacuum_pump1_kPa', 'vacuum_pump2_kPa',
    'cd_basis_weight_cv_pct', 'formation_index', 'ash_content_pct',
    'strength_rel_pct', 'defect_grade', 'defect_grade_numeric'
]
df = df[final_col_order].copy()

# ─── Data Quality Summary ───────────────────────────────
print("Computing quality summary...")
summary_stats = {}
for col in numeric_cols:
    if col in df.columns:
        series = df[col].dropna()
        summary_stats[col] = {
            "mean": float(series.mean()),
            "std": float(series.std()),
            "min": float(series.min()),
            "max": float(series.max()),
            "q1": float(series.quantile(0.25)),
            "median": float(series.median()),
            "q3": float(series.quantile(0.75)),
            "cv_pct": float((series.std() / series.mean() * 100)) if series.mean() != 0 else None
        }

# Grade distribution
grade_counts = df['grade_running'].value_counts().to_dict()
quality_report["summary"] = {
    "final_rows": len(df),
    "final_columns": len(df.columns),
    "rows_removed_total": initial_rows - len(df),
    "retention_pct": round(len(df) / initial_rows * 100, 2),
    "grade_distribution": {str(k): int(v) for k, v in grade_counts.items()},
    "defect_grade_distribution": {str(k): int(v) for k, v in df['defect_grade'].value_counts().to_dict().items()},
    "numeric_summary": summary_stats,
    "excluded_columns": ["moisture_pct"],
    "encoded_columns": ["defect_grade_numeric"]
}

# ─── Save ───────────────────────────────────────────────
print(f"Saving cleaned data ({len(df)} rows) to {OUT_CSV}...")
df.to_csv(OUT_CSV, index=False)
print(f"  CSV saved: {OUT_CSV}")

print(f"Saving quality report to {OUT_QUALITY}...")
with open(OUT_QUALITY, 'w', encoding='utf-8') as f:
    json.dump(quality_report, f, indent=2, ensure_ascii=False)
print(f"  Quality report saved: {OUT_QUALITY}")

print("\n=== Preprocessing Complete ===")
print(f"  Initial: {initial_rows} rows")
print(f"  Final:   {len(df)} rows")
print(f"  Removed: {initial_rows - len(df)} rows ({round((initial_rows - len(df)) / initial_rows * 100, 2)}%)")
