#!/usr/bin/env python3
"""
Paper Machine Headbox — Anomaly Detection
For each quality target:
  1. Adaptive threshold: rolling mean +- 2*sigma (window ~5% of data)
  2. Identify anomaly intervals
  3. Grade transition quality before/after analysis
  4. Save anomaly_report.json
"""

import pandas as pd
import numpy as np
import json
import os

# ─── Config ─────────────────────────────────────────────
DATA_PATH = "/Volumes/laxer/codes/skills/ industrial-deep-diagnostic/.claude/workspace/diagnostic-runs/202605291347083_paper_machine_headbox/02_processed/cleaned_data.csv"
RUN_DIR = "/Volumes/laxer/codes/skills/ industrial-deep-diagnostic/.claude/workspace/diagnostic-runs/202605291347083_paper_machine_headbox"
OUT_PATH = os.path.join(RUN_DIR, "02_processed", "anomaly_report.json")

# ─── Load Data ──────────────────────────────────────────
print("Loading cleaned data...")
df = pd.read_csv(DATA_PATH)
df['ts_dcs'] = pd.to_datetime(df['ts_dcs'])
df.sort_values('ts_dcs', inplace=True)
df.reset_index(drop=True, inplace=True)

target_cols = ['cd_basis_weight_cv_pct', 'formation_index', 'strength_rel_pct', 'defect_grade_numeric']
n = len(df)
window = max(5, int(n * 0.05))  # ~5% of data, min 5
print(f"  Rows: {n}, Adaptive window: {window}")

# ─── Anomaly Detection per Target ───────────────────────
anomaly_results = {}

for target in target_cols:
    print(f"\nAnalyzing {target}...")
    series = df[target].values

    # Rolling mean and std
    rolling_mean = pd.Series(series).rolling(window=window, center=True, min_periods=window//2).mean()
    rolling_std = pd.Series(series).rolling(window=window, center=True, min_periods=window//2).std()

    upper_bound = rolling_mean + 2 * rolling_std
    lower_bound = rolling_mean - 2 * rolling_std

    # Detect anomalies
    anomaly_mask = (series > upper_bound) | (series < lower_bound)
    n_anomalies = int(anomaly_mask.sum())

    # Find anomaly intervals (consecutive anomalous points)
    anomaly_intervals = []
    in_anomaly = False
    start_idx = None
    for i, is_anom in enumerate(anomaly_mask):
        if is_anom and not in_anomaly:
            start_idx = i
            in_anomaly = True
        elif not is_anom and in_anomaly:
            anomaly_intervals.append({
                "start_index": int(start_idx),
                "end_index": int(i - 1),
                "start_time": str(df.loc[start_idx, 'ts_dcs']),
                "end_time": str(df.loc[i - 1, 'ts_dcs']),
                "length": int(i - start_idx),
                "grade": str(df.loc[start_idx, 'grade_running'])
            })
            in_anomaly = False
    if in_anomaly:
        anomaly_intervals.append({
            "start_index": int(start_idx),
            "end_index": int(n - 1),
            "start_time": str(df.loc[start_idx, 'ts_dcs']),
            "end_time": str(df.loc[n - 1, 'ts_dcs']),
            "length": int(n - start_idx),
            "grade": str(df.loc[start_idx, 'grade_running'])
        })

    anomaly_pct = round(n_anomalies / n * 100, 2)

    anomaly_results[target] = {
        "n_anomalies": int(n_anomalies),
        "anomaly_pct": anomaly_pct,
        "window_size": window,
        "threshold": "rolling_mean +- 2*sigma",
        "n_intervals": len(anomaly_intervals),
        "intervals": anomaly_intervals[:30],  # Limit to top 30 intervals
        "summary_stats": {
            "mean": float(np.mean(series)),
            "std": float(np.std(series)),
            "min": float(np.min(series)),
            "max": float(np.max(series)),
            "q1": float(np.percentile(series, 25)),
            "median": float(np.percentile(series, 50)),
            "q3": float(np.percentile(series, 75))
        }
    }
    print(f"  {n_anomalies} anomalies ({anomaly_pct}%), {len(anomaly_intervals)} intervals")

# ─── Grade Transition Analysis ──────────────────────────
print("\nAnalyzing grade transitions...")
transitions = []
prev_grade = None
prev_idx = None
for i, (idx, row) in enumerate(df.iterrows()):
    curr_grade = row['grade_running']
    if prev_grade is not None and curr_grade != prev_grade:
        transitions.append({
            "from_grade": str(prev_grade),
            "to_grade": str(curr_grade),
            "index": int(i),
            "time": str(row['ts_dcs'])
        })
    prev_grade = curr_grade

print(f"  Found {len(transitions)} grade transitions")

# For each transition, compute quality before/after (window of 5 rows)
transition_analysis = []
for t in transitions[:50]:  # Limit to 50
    idx = t['index']
    before_start = max(0, idx - 5)
    after_end = min(n, idx + 5)

    before = df.iloc[before_start:idx]
    after = df.iloc[idx:after_end]

    quality_changes = {}
    for target in target_cols:
        if len(before) > 0 and len(after) > 0:
            before_mean = float(before[target].mean())
            after_mean = float(after[target].mean())
            delta = after_mean - before_mean
            quality_changes[target] = {
                "before_mean": round(before_mean, 4),
                "after_mean": round(after_mean, 4),
                "delta": round(delta, 4),
                "delta_pct": round(delta / abs(before_mean) * 100, 2) if before_mean != 0 else None
            }

    transition_analysis.append({
        "from_grade": t['from_grade'],
        "to_grade": t['to_grade'],
        "time": t['time'],
        "quality_changes": quality_changes
    })

# ─── Aggregate Transition Stats ─────────────────────────
transition_summary = {}
for target in target_cols:
    deltas = []
    for ta in transition_analysis:
        if target in ta['quality_changes'] and ta['quality_changes'][target]['delta_pct'] is not None:
            deltas.append(ta['quality_changes'][target]['delta_pct'])
    if deltas:
        transition_summary[target] = {
            "n_transitions": len(deltas),
            "mean_delta_pct": round(float(np.mean(deltas)), 2),
            "max_abs_delta_pct": round(float(np.max(np.abs(deltas))), 2),
            "std_delta_pct": round(float(np.std(deltas)), 2)
        }

# ─── Overall Stability Assessment ───────────────────────
stability = {}
for target in target_cols:
    series = df[target].values
    half = n // 2
    first_half = series[:half]
    second_half = series[half:]
    stability[target] = {
        "first_half_mean": round(float(np.mean(first_half)), 4),
        "second_half_mean": round(float(np.mean(second_half)), 4),
        "drift_pct": round((float(np.mean(second_half)) - float(np.mean(first_half))) / abs(float(np.mean(first_half))) * 100, 2) if float(np.mean(first_half)) != 0 else None,
        "first_half_std": round(float(np.std(first_half)), 4),
        "second_half_std": round(float(np.std(second_half)), 4),
        "variability_change_pct": round((float(np.std(second_half)) - float(np.std(first_half))) / float(np.std(first_half)) * 100, 2) if float(np.std(first_half)) != 0 else None
    }

# ─── Build Report ───────────────────────────────────────
report = {
    "run_id": "202605291347083_paper_machine_headbox",
    "analysis_type": "anomaly_detection",
    "total_rows": n,
    "adaptive_window": window,
    "target_results": anomaly_results,
    "grade_transitions": {
        "total_transitions": len(transitions),
        "sample_transitions_analyzed": len(transition_analysis),
        "details": transition_analysis[:20],
        "summary": transition_summary
    },
    "stability_assessment": stability
}

with open(OUT_PATH, 'w', encoding='utf-8') as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

print(f"\nAnomaly report saved to {OUT_PATH}")
print("Done.")
