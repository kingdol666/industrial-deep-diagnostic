#!/usr/bin/env python3
"""
制药旋转压片机 — 3号站冲头尖端磨损（工业级仿真）

模拟真实制药生产的数据特征：
  - Batch record（每批1行）+ 片剂检测结果（每批多行）— 不同时间粒度
  - 检测并非每片都做（抽样检测，约 30-50% 覆盖率）
  - 硬度仪存在零漂（标定问题）
  - 有 2 个干扰信号（考验分析系统能否排除）
  - 批次记录包含操作员、环境数据等元信息
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta

np.random.seed(42)
N_BATCH = 80       # 80 batches over ~27 days (3 shifts/day)
SAMP_PER_BATCH = 40  # 40 tablets sampled per batch
# But only ~50% actually tested (rest have missing test data)

# ============================================================
# PART 1: Timestamps
# ============================================================
start = datetime(2025, 11, 1, 6, 0, 0)
batch_times = []
for b in range(N_BATCH):
    # 3 batches per day, ~8h intervals (shift-based)
    batch_times.append(start + timedelta(hours=b * 8 + int(np.random.exponential(0.3))))

# Batch records (one per batch)
batch_ids = [f'B{b+1:04d}' for b in range(N_BATCH)]

# ============================================================
# PART 2: Physical root cause
# ============================================================
t_norm = np.linspace(0, 1, N_BATCH)

# ROOT CAUSE: Station 3 punch tip radius degradation
# R10.0 → R8.2 mm, with a slight recovery at batch ~40 (punch was dressed/re-ground)
punch_radius = np.zeros(N_BATCH)
for b in range(N_BATCH):
    tb = t_norm[b]
    if tb < 0.45:
        punch_radius[b] = 10.0 - 1.2 * (tb / 0.45) ** 1.3
    elif tb < 0.55:
        # Punch dressing at batch ~40 - partial recovery
        dress_pos = (tb - 0.45) / 0.10
        punch_radius[b] = 9.2 - 0.8 * dress_pos  # 9.2 → 8.8 (re-ground, not full recovery)
    else:
        punch_radius[b] = 8.8 - 1.0 * ((tb - 0.55) / 0.45) ** 1.3

# Compression efficiency loss: ~30% at worst for station 3
# Efficiency = (R_flat / R_spherical)²  — flattened tip distributes force over larger area
eff_loss = 1.0 - (punch_radius / 10.0) ** 2  # roughly 0 → 0.30
station3_eff = 1.0 - 0.85 * eff_loss  # 1.0 → 0.75 (at worst)

# ============================================================
# PART 3: Batch process parameters
# ============================================================

# Station assignment (3 stations, rotated each batch)
# In real production, each station has dedicated punch/die sets
# For this simulation: station assignment is random but persistent across batches
# (i.e., station 3 ALWAYS has the worn punch)
stations = np.tile([1, 2, 3], N_BATCH)[:N_BATCH]

# Main compression force - operator increases to compensate
# Starts at 18 kN, increases to ~26 kN over campaign
comp_force = 18.0 + 10 * t_norm + np.random.normal(0, 0.4, N_BATCH)
comp_force = np.clip(comp_force, 16, 30)

# Pre-compression force
pre_comp = 6.0 + 3.0 * t_norm + np.random.normal(0, 0.2, N_BATCH)

# Turret speed (rpm) - slight variation
turret_speed = 28 + np.random.normal(0, 1.5, N_BATCH)

# Fill depth (mm) - operator increases to maintain weight
fill_depth = 10.0 + 0.6 * t_norm + np.random.normal(0, 0.04, N_BATCH)

# Dwell time (ms)
dwell_time = 25 + np.random.normal(0, 2, N_BATCH)

# === INTERFERING SIGNAL #1: Blend moisture ===
# Random variation, NOT trending with batch number
# Higher moisture → more plastic deformation → temporarily higher hardness
# This creates a confound: some batches look good on hardness due to moisture,
# masking the punch wear effect
blend_moisture = 2.5 + 0.8 * np.random.randn(N_BATCH)
blend_moisture = np.clip(blend_moisture, 0.8, 4.5)

# === INTERFERING SIGNAL #2: Lubricant level ===
# Operator adjusts lubricant sporadically
# Low lubricant → higher friction → harder to eject → higher apparent hardness
lubricant = 0.8 + 0.5 * np.random.randn(N_BATCH)
lubricant = np.clip(lubricant, 0.1, 2.0)

# Blend uniformity index (0-100, higher = better)
blend_uniformity = 92 + 3 * np.random.randn(N_BATCH)
blend_uniformity = np.clip(blend_uniformity, 80, 100)

# Compression zone temperature
# *** INTERFERING SIGNAL #3 ***
# Temperature has a slow sensor response (thermal mass) - creates a lag artifact
# that makes temp look like it "causes" quality changes when it's really the other way
cz_temp = 32 + 5 * np.random.randn(N_BATCH)
# Add thermal drift from friction (slight, correlated with compression force)
cz_temp += 0.08 * (comp_force - 18)

# Operator ID (3 operators rotating)
operators = ['OP_A', 'OP_B', 'OP_C']
operator = np.random.choice(operators, N_BATCH)

# Ambient conditions
ambient_temp = 22 + 2 * np.random.randn(N_BATCH)
ambient_humidity = 45 + 10 * np.random.randn(N_BATCH)

# Punch serial numbers (for tracking)
punch_sn_station = {}
for st in [1, 2]:
    punch_sn_station[st] = f'P{100+st}-{np.random.randint(1000,9999)}'
punch_sn_station[3] = f'P{103}-{np.random.randint(1000,9999)}'  # worn punch

# ============================================================
# PART 4: Tablet test results (per tablet, ~80 batches × 40 samples = 3200)
# BUT only ~60% actually tested (rest missing = real lab practice)
# ============================================================
n_total = 0
recs = []
for b in range(N_BATCH):
    st = stations[b]
    eff = 1.0 if st != 3 else station3_eff[b]

    for s in range(SAMP_PER_BATCH):
        tested = np.random.random() < 0.60  # ~60% tested
        if not tested:
            continue

        # Base quality
        weight = 500.0
        hardness = 100.0
        friability = 0.3
        disintegration = 8.0
        thickness = 5.0

        if st == 3:
            # Worn punch effect
            loss = 1.0 - eff
            w_var = 28 * loss + 1.5 * np.random.randn()
            h_var = -90 * loss + 4 * np.random.randn()
            f_var = 5.5 * loss + 0.15 * np.random.randn()
            d_var = -6.0 * loss + 0.5 * np.random.randn()
            t_var = 0.4 * loss + 0.03 * np.random.randn()
        else:
            w_var = 0.5 * np.random.randn()
            h_var = 2.0 * np.random.randn()
            f_var = 0.04 * np.random.randn()
            d_var = 0.5 * np.random.randn()
            t_var = 0.02 * np.random.randn()

        # Moisture effect (interfering!)
        moist_eff = (blend_moisture[b] - 2.5)
        h_var += 5 * moist_eff  # higher moisture = higher apparent hardness

        # Measurement noise / instrument drift
        # Hardness tester has zero drift over campaign (~2N)
        h_var -= 0.03 * b

        weight += w_var
        hardness += h_var
        friability = max(0.1, friability + f_var)
        disintegration = max(2, disintegration + d_var)
        thickness += t_var

        # Defect grade
        score = 0
        if abs(weight - 500) > 10:
            score += 1
        if abs(weight - 500) > 18:
            score += 2
        if hardness < 85:
            score += 1
        if hardness < 72:
            score += 2
        if friability > 0.8:
            score += 1
        if friability > 1.2:
            score += 2
        if thickness > 5.25:
            score += 1

        if score >= 3:
            dg = 'C'
        elif score >= 1:
            dg = 'B'
        else:
            dg = 'A'

        recs.append({
            'batch_id': batch_ids[b],
            'batch_seq': b + 1,
            'tablet_seq': s + 1,
            'station': st,
            'tablet_weight_mg': np.round(weight, 2),
            'hardness_N': np.round(hardness, 2),
            'friability_pct': np.round(friability, 3),
            'disintegration_time_min': np.round(disintegration, 2),
            'thickness_mm': np.round(thickness, 3),
            'blend_moisture_pct': np.round(blend_moisture[b], 2),
            'defect_grade': dg,
        })
        n_total += 1

df_results = pd.DataFrame(recs)

# ============================================================
# PART 5: Batch record (one per batch)
# ============================================================
br_recs = []
for b in range(N_BATCH):
    st = stations[b]
    br_recs.append({
        'batch_id': batch_ids[b],
        'ts_start': batch_times[b].strftime('%Y-%m-%d %H:%M:%S'),
        'batch_day': b // 3 + 1,
        'station': st,
        'punch_serial': punch_sn_station[st],
        'operator_id': operator[b],
        'compression_force_kN': np.round(comp_force[b], 2),
        'pre_compression_force_kN': np.round(pre_comp[b], 2),
        'turret_speed_rpm': np.round(turret_speed[b], 1),
        'fill_depth_mm': np.round(fill_depth[b], 2),
        'dwell_time_ms': np.round(dwell_time[b], 1),
        'blend_moisture_pct': np.round(blend_moisture[b], 2),
        'lubricant_level_pct': np.round(lubricant[b], 2),
        'blend_uniformity_index': np.round(blend_uniformity[b], 1),
        'compression_zone_temp_C': np.round(cz_temp[b], 1),
        'ambient_temp_C': np.round(ambient_temp[b], 1),
        'ambient_humidity_pct': np.round(ambient_humidity[b], 1),
    })

df_batch = pd.DataFrame(br_recs)

# ============================================================
# PART 6: Event/activity log
# ============================================================
events = []
# Punch re-greening (dressing) event at batch ~40
events.append({
    'ts_event': batch_times[40].strftime('%Y-%m-%d %H:%M:%S'),
    'event_type': 'PUNCH_DRESSING',
    'description': 'Station 3 upper punch re-ground (routine maintenance). Radius restored from R9.0 to R8.8.',
})

# Hardness tester calibration
events.append({
    'ts_event': batch_times[5].strftime('%Y-%m-%d %H:%M:%S'),
    'event_type': 'CALIBRATION',
    'description': 'Hardness tester calibrated at shift start',
})

# Lubricant change
events.append({
    'ts_event': batch_times[50].strftime('%Y-%m-%d %H:%M:%S'),
    'event_type': 'LUBRICANT_CHANGE',
    'description': 'Changed to new batch of magnesium stearate lubricant',
})

# Blend moisture incident
events.append({
    'ts_event': batch_times[23].strftime('%Y-%m-%d %H:%M:%S'),
    'event_type': 'MATERIAL_INCIDENT',
    'description': 'Granulation moisture out of spec (3.8%) - blend adjusted with extra drying step',
})

df_events = pd.DataFrame(events)
df_events = df_events.sort_values('ts_event')

# ============================================================
# PART 7: SAVE
# ============================================================
base = "/Volumes/laxer/codes/skills/ industrial-deep-diagnostic/data/tablet_press"

df_batch.to_csv(f'{base}/batch_record_2025Q4.csv', index=False)
df_results.to_csv(f'{base}/tablet_test_results_2025Q4.csv', index=False)
df_events.to_csv(f'{base}/production_event_log_2025Q4.csv', index=False)

# Summary by station
print(f"=== Tablet Press - 3-file Pharmaceutical Export ===")
print(f"Batch records:     {len(df_batch)} batches")
print(f"Tablet test recs:  {len(df_results)} individual tablet tests (~60% coverage)")
print(f"Event log:         {len(df_events)} events")
print(f"\nOverall defect: A={sum(df_results['defect_grade']=='A')}, "
      f"B={sum(df_results['defect_grade']=='B')}, C={sum(df_results['defect_grade']=='C')}")

for st, grp in df_results.groupby('station'):
    g = grp['defect_grade']
    print(f"  Station {st}:")
    print(f"    Tests: {len(grp)}, A={sum(g=='A')}, B={sum(g=='B')}, C={sum(g=='C')}")
    print(f"    Hardness: {grp['hardness_N'].mean():.1f}±{grp['hardness_N'].std():.1f} N")
    print(f"    Weight:   {grp['tablet_weight_mg'].mean():.1f}±{grp['tablet_weight_mg'].std():.1f} mg")
    print(f"    Friability: {grp['friability_pct'].mean():.3f}±{grp['friability_pct'].std():.3f}%")
    print(f"    Thickness:  {grp['thickness_mm'].mean():.3f}±{grp['thickness_mm'].std():.3f} mm")

print(f"\nInterfering signals:")
print(f"  - Blend moisture (random, affects ALL stations equally)")
print(f"  - Hardness tester drift (-0.03N/batch over campaign)")
print(f"  - Compression zone temp (slow sensor response, creates lag artifact)")
print(f"Key challenge: Overall data shows WEAK correlation (stations 1+2 mask station 3)")
print(f"Must stratify by station column to see punch wear signal")
