#!/usr/bin/env python3
"""
Anomaly Detection for tablet_press data.
Batch pharmaceutical compression scenario.
Adaptive threshold anomaly detection on quality targets with transition event analysis.
"""
import json
import os
import sys
from collections import defaultdict, OrderedDict

RUN_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Load cleaned data
with open(os.path.join(RUN_DIR, '02_processed', 'cleaned_data.json')) as f:
    data = json.load(f)

# Load feature summary for reference
try:
    with open(os.path.join(RUN_DIR, '02_processed', 'feature_summary.json')) as f:
        feature_summary = json.load(f)
except:
    feature_summary = {}

# Load production events
events = []
events_path = os.path.join(RUN_DIR, '00_input', 'production_event_log_2025Q4.csv')
with open(events_path) as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith('ts_event'):
            continue
        parts = line.replace('\r', '').split(',')
        if len(parts) >= 2:
            events.append({
                'ts': parts[0].strip(),
                'type': parts[1].strip(),
                'description': parts[2].strip() if len(parts) > 2 else ''
            })

# Sort data by batch_seq then tablet_seq
data_sorted = sorted(data, key=lambda x: (x.get('batch_seq', 0), x.get('tablet_seq', 0)))

quality_targets = ['hardness_N', 'friability_pct', 'disintegration_time_min', 'tablet_weight_mg', 'thickness_mm']

anomaly_report = {
    "targets": OrderedDict(),
    "transition_events": [],
    "summary": {}
}

# ── Step 1: Anomaly Detection per quality target ──

window_size = max(5, int(len(data_sorted) * 0.05))  # 5% of data length

for target in quality_targets:
    vals = [row.get(target) for row in data_sorted if row.get(target) is not None]
    if not vals:
        continue

    n = len(vals)
    window = window_size
    if window < 3:
        window = 3

    # Rolling statistics
    rolling_mean = []
    rolling_std = []
    for i in range(n):
        start = max(0, i - window // 2)
        end = min(n, i + window // 2 + 1)
        segment = vals[start:end]
        seg_mean = sum(segment) / len(segment)
        seg_var = sum((v - seg_mean) ** 2 for v in segment) / len(segment)
        seg_std = seg_var ** 0.5
        rolling_mean.append(seg_mean)
        rolling_std.append(seg_std if seg_std > 0 else 0.001)

    # Adaptively flag anomalies: ±2σ from rolling mean
    flags = []
    for i in range(n):
        if rolling_std[i] > 0:
            z = abs(vals[i] - rolling_mean[i]) / rolling_std[i]
            flags.append(z > 2.0)
        else:
            flags.append(False)

    # Detect sudden shifts: |rolling_mean(t) - rolling_mean(t-1)| > 2 * rolling_std(t-1)
    shift_flags = [False] * n
    for i in range(1, n):
        if rolling_std[i - 1] > 0:
            shift = abs(rolling_mean[i] - rolling_mean[i - 1])
            shift_flags[i] = shift > 2.0 * rolling_std[i - 1]

    # Combine flags
    combined_flags = [f or s for f, s in zip(flags, shift_flags)]

    # Merge consecutive flags into intervals
    intervals = []
    i = 0
    while i < n:
        if combined_flags[i]:
            start_idx = i
            while i < n and combined_flags[i]:
                i += 1
            end_idx = i - 1

            # Calculate severity
            segment_deviations = [abs(vals[j] - rolling_mean[j]) / rolling_std[j] if rolling_std[j] > 0 else 0
                                  for j in range(start_idx, end_idx + 1)]
            max_dev = max(segment_deviations) if segment_deviations else 0

            severity = "low"
            if max_dev > 4.0:
                severity = "critical"
            elif max_dev > 3.0:
                severity = "high"
            elif max_dev > 2.5:
                severity = "medium"

            # Get concurrent parameter info for this interval
            concurrent = {}
            if start_idx < len(data_sorted):
                row = data_sorted[start_idx]
                for param in ['compression_force_kN', 'blend_moisture_pct', 'lubricant_level_pct',
                              'compression_zone_temp_C', 'turret_speed_rpm', 'dwell_time_ms']:
                    if param in row and row[param] is not None:
                        concurrent[param] = f"{row[param]:.2f}"

            intervals.append({
                "start_index": start_idx,
                "end_index": end_idx,
                "start_batch": data_sorted[start_idx].get('batch_id', ''),
                "end_batch": data_sorted[end_idx].get('batch_id', ''),
                "severity": severity,
                "max_deviation_sigma": round(max_dev, 2),
                "interval_length": end_idx - start_idx + 1,
                "concurrent_params": concurrent
            })
        else:
            i += 1

    # Threshold analysis
    q1 = sorted(vals)[int(n * 0.25)]
    q3 = sorted(vals)[int(n * 0.75)]
    iqr = q3 - q1
    lower_threshold = q1 - 1.5 * iqr
    upper_threshold = q3 + 1.5 * iqr

    anomaly_report["targets"][target] = {
        "anomaly_intervals": intervals,
        "total_anomalous_points": sum(combined_flags),
        "anomaly_rate_pct": round(sum(combined_flags) / n * 100, 2),
        "threshold_analysis": {
            "iqr_lower": round(lower_threshold, 3),
            "iqr_upper": round(upper_threshold, 3),
            "vals_below_lower": sum(1 for v in vals if v < lower_threshold),
            "vals_above_upper": sum(1 for v in vals if v > upper_threshold),
            "threshold_crossing_rate_pct": round(
                (sum(1 for v in vals if v < lower_threshold) + sum(1 for v in vals if v > upper_threshold)) / n * 100, 2)
        }
    }

# ── Step 2: Transition Event Analysis ──

# Detect station transitions
current_station = None
station_transitions = []
for i, row in enumerate(data_sorted):
    station = row.get('station')
    if station is not None and station != current_station:
        if current_station is not None:
            station_transitions.append({
                'index': i,
                'type': 'station_change',
                'column': 'station',
                'from': current_station,
                'to': station
            })
        current_station = station

# Detect punch_serial transitions
current_punch = None
punch_transitions = []
for i, row in enumerate(data_sorted):
    punch = row.get('punch_serial')
    if punch is not None and punch != current_punch:
        if current_punch is not None:
            punch_transitions.append({
                'index': i,
                'type': 'punch_change',
                'column': 'punch_serial',
                'from': current_punch,
                'to': punch
            })
        current_punch = punch

all_transitions = station_transitions + punch_transitions

# For each transition, compute quality before/after
for trans in all_transitions:
    idx = trans['index']
    before_start = max(0, idx - 20)
    before_end = idx
    after_start = idx
    after_end = min(len(data_sorted), idx + 20)

    quality_before = {}
    quality_after = {}

    for target in quality_targets:
        before_vals = [data_sorted[j].get(target) for j in range(before_start, before_end)
                       if data_sorted[j].get(target) is not None]
        after_vals = [data_sorted[j].get(target) for j in range(after_start, after_end)
                      if data_sorted[j].get(target) is not None]

        if before_vals and after_vals:
            b_mean = sum(before_vals) / len(before_vals)
            a_mean = sum(after_vals) / len(after_vals)
            b_std = (sum((v - b_mean) ** 2 for v in before_vals) / len(before_vals)) ** 0.5 if len(before_vals) > 1 else 0.001
            a_std = (sum((v - a_mean) ** 2 for v in after_vals) / len(after_vals)) ** 0.5 if len(after_vals) > 1 else 0.001
            pooled_std = ((b_std ** 2 + a_std ** 2) / 2) ** 0.5

            quality_before[target] = round(b_mean, 3)
            quality_after[target] = round(a_mean, 3)

            if pooled_std > 0:
                quality_jump = abs(a_mean - b_mean) / pooled_std
            else:
                quality_jump = 0

            trans[f'{target}_jump'] = round(quality_jump, 3)

    trans['quality_before'] = quality_before
    trans['quality_after'] = quality_after

    # Calculate max quality jump
    jumps = [v for k, v in trans.items() if k.endswith('_jump')]
    trans['max_quality_jump'] = round(max(jumps), 3) if jumps else 0

anomaly_report["transition_events"] = all_transitions

# ── Step 3: Summary ──
total_anomalies = sum(
    anomaly_report["targets"][t]["total_anomalous_points"]
    for t in quality_targets if t in anomaly_report["targets"]
)

anomaly_report["summary"] = {
    "total_quality_targets": len(quality_targets),
    "total_anomalous_points_all_targets": total_anomalies,
    "total_transition_events": len(all_transitions),
    "key_findings": [
        f"Detected {sum(len(anomaly_report['targets'][t]['anomaly_intervals']) for t in quality_targets if t in anomaly_report['targets'])} anomaly intervals across {len(quality_targets)} quality targets",
        f"Identified {len(all_transitions)} transition events (station changes and punch changes)",
        "Anomaly intervals overlap with production events should be cross-referenced"
    ]
}

# Save anomaly report
output_path = os.path.join(RUN_DIR, '02_processed', 'anomaly_report.json')
with open(output_path, 'w') as f:
    json.dump(anomaly_report, f, indent=2, ensure_ascii=False)

print(f"Anomaly report saved to {output_path}")
print(f"Total anomaly intervals: {sum(len(anomaly_report['targets'][t]['anomaly_intervals']) for t in quality_targets if t in anomaly_report['targets'])}")
print(f"Total transition events: {len(all_transitions)}")

# Print summary per target
for target in quality_targets:
    if target in anomaly_report['targets']:
        t = anomaly_report['targets'][target]
        print(f"  {target}: {t['total_anomalous_points']} anomalous points ({t['anomaly_rate_pct']}%), {len(t['anomaly_intervals'])} intervals")
