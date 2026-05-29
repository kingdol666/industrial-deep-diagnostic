#!/usr/bin/env python3
"""
造纸机 — 流浆箱上浆系统 PCC/纤维沉积（工业级仿真）

模拟真实工厂 SCADA 导出数据的特征：
  - 2 个测控系统导出（DCS + QCS）时间戳不完全对齐
  - 传感器间歇性离线（通信中断→NaN）、标定漂移、死值
  - 参数采样频率不同（过程参数 2min，质量参数每卷 ~30min）
  - 操作日志（纸种切换、清洗事件、断纸记录）独立文件
  - 包含 2 个与根因无关的有趣「干扰信号」—— 考验分析系统
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta

np.random.seed(42)
N_DAYS = 90
MIN_INTERVAL = 2  # DCS scans every 2 minutes
BASE_POINTS = N_DAYS * 24 * 60 // MIN_INTERVAL

# ============================================================
# PART 1: Generate underlying physical process
# ============================================================
t_sim = np.linspace(0, 1, BASE_POINTS)
day_sim = (t_sim * N_DAYS) + 1

# --- ROOT CAUSE: Accumulation Index ---
# Gradual deposition in approach piping, ~15% diameter loss over 90 days
# Includes a "wash-out" event around day 60 (operator tried acid wash, partial recovery)
acc_idx = np.zeros(BASE_POINTS)
for i in range(BASE_POINTS):
    d = day_sim[i]
    if d < 5:
        acc_idx[i] = 0.01
    elif d < 55:
        acc_idx[i] = ((d - 5) / 55) ** 1.4 * 0.85
    elif d < 62:
        acid_effect = (d - 55) / 7  # wash-out starts at day 55
        acc_idx[i] = 0.85 * (1 - 0.5 * acid_effect)  # drops ~50%
    elif d < 67:
        # Wash complete, re-deposition starts from lower baseline
        re_start = (d - 62) / 5
        acc_idx[i] = 0.43 + re_start * 0.15
    else:
        acc_idx[i] = 0.58 + ((d - 67) / 23) ** 1.3 * 0.35
    acc_idx[i] = np.clip(acc_idx[i], 0, 1)

# Diameter reduction: ~15% at peak
diam_ratio = 1.0 - 0.14 * acc_idx

# Pressure drop ∝ 1/D^5 (Darcy-Weisbach, full turbulent)
pd_factor = (1.0 / diam_ratio) ** 5  # roughly 1.0 → 2.0 at peak

# --- Grade schedule ---
# 3 grades, ~3 day cycles, 30 cycles over 90 days
grades = np.empty(BASE_POINTS, dtype=object)
grade_cycle = ['GSM80', 'GSM100', 'GSM120']
cycle_ptr = 0
run_end = 0
for i in range(BASE_POINTS):
    if i >= run_end:
        g = grade_cycle[cycle_ptr % 3]
        run_len = int(np.random.uniform(60, 150))  # ~2-5 days in 2-min intervals
        run_end = i + run_len
        cycle_ptr += 1
    grades[i] = g

# Grade-specific base pressures
gsm_base_p = {'GSM80': 14.5, 'GSM100': 16.8, 'GSM120': 19.5}

# ============================================================
# PART 2: Add industrial artifacts to underlying signal
# ============================================================

def add_artifact_noise(signal, noise_std=0.15, spike_rate=0.002,
                       deadzone_frac=0.0, deadzone_val=None, t_dist_df=3):
    """Add realistic industrial sensor artifacts."""
    n = len(signal)
    out = signal.copy()

    # Heavy-tailed noise (t-distribution, simulates occasional spike)
    noise = np.random.standard_t(t_dist_df, n) * noise_std
    out += noise

    # Sensor stuck / dead zone (e.g., failed sensor reads constant)
    if deadzone_frac > 0:
        dz_start = np.random.randint(0, int(n * (1 - deadzone_frac)))
        dz_end = dz_start + int(n * deadzone_frac)
        val = deadzone_val if deadzone_val is not None else out[dz_start]
        out[dz_start:dz_end] = val

    # Communication dropout → NaN
    if spike_rate > 0:
        drop_mask = np.random.random(n) < spike_rate
        out[drop_mask] = np.nan

    return out


# ============================================================
# PART 3: DCS Process Parameters (2-min interval, ~64800 rows)
# ============================================================
n_dcs = BASE_POINTS

# Headbox pressure (with grade setpoints)
pressure_setpoint = np.array([gsm_base_p[g] for g in grades])
# Measured pressure rises due to deposition
headbox_p = pressure_setpoint * pd_factor
headbox_p += 0.3 * np.sin(2 * np.pi * day_sim / 7)  # weekly pattern
headbox_p = add_artifact_noise(headbox_p, noise_std=0.2, spike_rate=0.003)
# Add a calibration drift mid-campaign (day 40, instrument re-zero)
cal_shift_mask = day_sim > 40
headbox_p[cal_shift_mask] += 0.35
# Sensor froze for 6 hours on day 33 (comm failure)
freeze_start = int(33 / N_DAYS * n_dcs)
freeze_end = freeze_start + 180  # 6 hours = 180 intervals
headbox_p[freeze_start:freeze_end] = np.nan

# Approach flow
approach_flow = np.array([3900 + 500 * (g == 'GSM100') + 1100 * (g == 'GSM120')
                          for g in grades], dtype=float)
approach_flow += 200 * (pd_factor - 1)  # pump curve shift with backpressure
approach_flow = add_artifact_noise(approach_flow, noise_std=35, spike_rate=0.001)

# Fan pump speed (rpm) - operator adjusts to maintain flow
fan_pump_speed = 880 + 60 * (pd_factor - 1) + np.random.normal(0, 5, n_dcs)

# White water consistency - drifts as fines build up
ww_consistency = 0.85 + 0.4 * acc_idx + np.random.standard_t(3, n_dcs) * 0.05
ww_consistency = np.clip(ww_consistency, 0.3, 2.0)

# *** INTERFERING SIGNAL #1 ***
# Vacuum pump #2 belt slippage (completely unrelated to deposition)
# Day 22-26: vacuum drops then recovers when belt is tightened
vacuum_pump1 = 52 + 5 * np.random.randn(n_dcs)  # normal
vacuum_pump2 = 48 + 4 * np.random.randn(n_dcs)
slip_idx = (day_sim >= 22) & (day_sim <= 26)
vacuum_pump2[slip_idx] = 38 + 8 * np.random.randn(sum(slip_idx))
vacuum_pump2 = add_artifact_noise(vacuum_pump2, noise_std=3, spike_rate=0.002)

# Retention aid dosage (ppm)
ret_aid = 180 + 100 * acc_idx + np.random.normal(0, 10, n_dcs)
ret_aid = np.clip(ret_aid, 140, 350)

# Slice opening (mm)
slice_open = np.array([8.4 + 1.3 * (g == 'GSM100') + 2.8 * (g == 'GSM120')
                       for g in grades])
slice_open += 0.5 * np.random.randn(n_dcs)

# Machine speed (m/min)
mach_speed = np.array([1320 + 190 * (g == 'GSM100') + 380 * (g == 'GSM120')
                       for g in grades], dtype=float)
mach_speed += add_artifact_noise(np.zeros(n_dcs), noise_std=8, spike_rate=0.001)

# Stock temperature (C) - seasonal + daily variation +/- process heat
# *** INTERFERING SIGNAL #2 ***
# Stock temperature has a natural seasonal drift upward (summer approaching)
# that ALSO correlates with defect rate - this tests confounder detection
stock_temp = 42 + 6 * np.sin(2 * np.pi * day_sim / 90) + 2 * np.sin(2 * np.pi * day_sim / 365)
stock_temp += 3 * np.sin(2 * np.pi * (day_sim % 1))  # daily cycle
stock_temp = add_artifact_noise(stock_temp, noise_std=0.5, spike_rate=0.001)

# Jet to wire ratio
jw_ratio = 1.02 + 0.03 * np.random.randn(n_dcs)

# ============================================================
# PART 4: Build DCS timestamps (realistic - some irregularity)
# ============================================================
dcs_times = []
t = datetime(2025, 10, 1, 6, 0, 0)
for i in range(n_dcs):
    dcs_times.append(t)
    # Normal interval is 2 min, but occasionally 1-4 min (SCADA jitter)
    jitter = int(np.random.choice([-30, -15, 0, 0, 15, 30, 60, 120],
                                  p=[0.02, 0.05, 0.6, 0.1, 0.1, 0.08, 0.03, 0.02]))
    t += timedelta(seconds=120 + jitter)

timestamps_str = [ts.strftime('%Y-%m-%d %H:%M:%S') for ts in dcs_times]

# ============================================================
# PART 5: DCS Data Frame
# ============================================================
df_dcs = pd.DataFrame({
    'ts_dcs': timestamps_str,
    'day': np.round(day_sim, 1),
    'shift': np.random.choice([1, 2], n_dcs),
    'grade_running': grades,
    'headbox_pressure_kPa': np.round(headbox_p, 2),
    'approach_flow_lpm': np.round(approach_flow, 0),
    'fan_pump_speed_rpm': np.round(fan_pump_speed, 1),
    'white_water_consistency_pct': np.round(ww_consistency, 3),
    'retention_aid_dosage_ppm': np.round(ret_aid, 1),
    'slice_opening_mm': np.round(slice_open, 2),
    'machine_speed_mmin': np.round(mach_speed, 1),
    'stock_temp_C': np.round(stock_temp, 1),
    'jet_to_wire_ratio': np.round(jw_ratio, 3),
    'vacuum_pump1_kPa': np.round(vacuum_pump1, 1),
    'vacuum_pump2_kPa': np.round(vacuum_pump2, 1),
})

# ============================================================
# PART 6: QCS Quality Data (per reel, ~every 30-50 min, ~3000 rows)
# ============================================================
n_qcs = int(n_dcs * 0.05)  # ~3240 quality samples

qcs_indices = np.sort(np.random.choice(n_dcs, n_qcs, replace=False))

# Quality metrics derived from underlying physical process
# CD basis weight variation (primary deposition effect)
cd_bw_cv = 0.35 + 2.8 * acc_idx[qcs_indices]
cd_bw_cv += 0.2 * np.random.standard_t(3, n_qcs)
# Grade effect
grade_at_qcs = grades[qcs_indices]
cd_bw_cv += np.array([0, 0.15, 0.35])[np.array([['GSM80','GSM100','GSM120'].index(g)
                                                   for g in grade_at_qcs])]
cd_bw_cv = np.clip(cd_bw_cv, 0.15, 4.5)

# Formation index (1-10, higher = better)
formation = 8.5 - 5.0 * acc_idx[qcs_indices]
formation += 0.4 * (ret_aid[qcs_indices] - 180) / 200
formation += 0.2 * np.random.standard_t(3, n_qcs)  # t-noise
formation = np.clip(formation, 1.5, 9.5)

# Ash content
ash = 24 + 2 * np.random.randn(n_qcs) + 4 * acc_idx[qcs_indices] * np.random.rand(n_qcs)
ash = np.clip(ash, 18, 32)

# Moisture - affected by stock temp (interfering signal) and vacuum
moisture = 5.2 + 0.3 * (stock_temp[qcs_indices] - 42) / 42
moisture -= 0.08 * vacuum_pump1[qcs_indices]
moisture += 0.4 * np.random.randn(n_qcs)
moisture = np.clip(moisture, 3.0, 8.0)

# Paper strength (relative) - degrades as formation worsens
strength_rel = 100 - 8 * acc_idx[qcs_indices] + np.random.randn(n_qcs) * 2
strength_rel = np.clip(strength_rel, 70, 105)

# ============================================================
# PART 7: Defect Grade
# ============================================================
defect = np.full(n_qcs, 'A', dtype=object)
for i in range(n_qcs):
    s = 0
    if cd_bw_cv[i] > 2.0:
        s += 2
    elif cd_bw_cv[i] > 1.2:
        s += 1
    if formation[i] < 3.5:
        s += 2
    elif formation[i] < 5.5:
        s += 1
    if moisture[i] > 6.5:
        s += 1
    if s >= 3:
        defect[i] = 'C'
    elif s >= 1:
        defect[i] = 'B'

# ============================================================
# PART 8: QCS Data Frame
# ============================================================
df_qcs = pd.DataFrame({
    'ts_qcs': [timestamps_str[idx] for idx in qcs_indices],
    'day': np.round(day_sim[qcs_indices], 1),
    'grade': grade_at_qcs,
    'cd_basis_weight_cv_pct': np.round(cd_bw_cv, 3),
    'formation_index': np.round(formation, 2),
    'ash_content_pct': np.round(ash, 2),
    'moisture_pct': np.round(moisture, 2),
    'strength_rel_pct': np.round(strength_rel, 1),
    'defect_grade': list(defect),
})

# ============================================================
# PART 9: Event Log (independent CSV - like operator shift log)
# ============================================================
events = []
# Grade changes
prev_g = None
for i in range(0, n_dcs, 60):  # scan every ~2 hours
    g = grades[i]
    if g != prev_g and prev_g is not None:
        events.append({
            'ts_event': timestamps_str[i],
            'event_type': 'GRADE_CHANGE',
            'description': f'{prev_g} → {g}',
        })
    prev_g = g

# Machine breaks (paper breaks) - common in real mills
break_count = int(np.random.poisson(0.5 * N_DAYS / 30))  # ~1.5 breaks
for _ in range(break_count):
    bi = np.random.randint(1000, n_dcs - 500)
    events.append({
        'ts_event': timestamps_str[bi],
        'event_type': 'BREAK',
        'description': 'Paper break at press section' if np.random.random() > 0.5 else 'Break at reel',
    })

# Scheduled maintenance (acid wash / boil-out)
events.append({
    'ts_event': timestamps_str[int(55 / N_DAYS * n_dcs)],
    'event_type': 'BOIL_OUT',
    'description': 'Approach system boil-out (acid wash)',
})

# Vacuum belt tightening event
events.append({
    'ts_event': timestamps_str[int(25 / N_DAYS * n_dcs)],
    'event_type': 'MAINTENANCE',
    'description': 'Vacuum pump #2 belt replaced',
})

# Calibration event
events.append({
    'ts_event': timestamps_str[int(40 / N_DAYS * n_dcs)],
    'event_type': 'CALIBRATION',
    'description': 'Headbox pressure transmitter recalibrated (offset +0.35 kPa)',
})

df_events = pd.DataFrame(events)
df_events = df_events.sort_values('ts_event')

# ============================================================
# PART 10: SAVE - realistic multi-file format
# ============================================================
base = "/Volumes/laxer/codes/skills/ industrial-deep-diagnostic/data/paper_machine_headbox"

df_dcs.to_csv(f'{base}/DCS_export_20251001_20251229.csv', index=False)
df_qcs.to_csv(f'{base}/QCS_quality_export_20251001_20251229.csv', index=False)
df_events.to_csv(f'{base}/operator_event_log_2025Q4.csv', index=False)

# Also create merged version (closest DCS to each QCS point)
merged_rows = []
for idx in qcs_indices:
    row = {**dict(df_dcs.iloc[idx]), **dict(df_qcs.iloc[len(merged_rows)])}
    merged_rows.append(row)
df_merged = pd.DataFrame(merged_rows)
df_merged.to_csv(f'{base}/merged_dcs_qcs_20251001_20251229.csv', index=False)

print(f"=== Paper Machine Headbox - 3-file Industrial Export ===")
print(f"DCS data:      {len(df_dcs):>6} rows (2-min interval, 90 days)")
print(f"QCS quality:   {len(df_qcs):>6} rows (per-reel samples)")
print(f"Event log:     {len(df_events):>3} events")
print(f"Merged:        {len(df_merged):>6} rows")
print(f"\nDefect: A={sum(d=='A' for d in defect)}, B={sum(d=='B' for d in defect)}, C={sum(d=='C' for d in defect)}")
print(f"Missing DCS:   {df_dcs['headbox_pressure_kPa'].isna().sum()} NaN values (sensor dropout)")
print(f"Grade changes: {sum(1 for e in events if e['event_type']=='GRADE_CHANGE')} events")
print(f"Machine breaks: {sum(1 for e in events if e['event_type']=='BREAK')} events")
print(f"Interfering signals: Vacuum belt slip (d22-26), Stock temp seasonal drift (tests confounder detection)")
print(f"Wash-out event: Day ~55-62 (partial recovery, tests trend modeling)")
