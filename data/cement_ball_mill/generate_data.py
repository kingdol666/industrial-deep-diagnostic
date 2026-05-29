#!/usr/bin/env python3
"""
水泥厂 — 球磨机研磨体/衬板磨损（工业级仿真）

模拟工厂过程控制系统 + 实验室数据导出的真实特征：
  - 过程参数来自 DCS（每2min采样），质量数据来自化验室（每2-4h人工取样）
  - 传感器漂移、通信丢失、尖峰噪声、死值
  - 独立的事件日志（维护、停机、加球）
  - 包含 2 个干扰信号（需分辨是否为根因）
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta

np.random.seed(42)
NT = 90 * 24 * 60 // 2  # DCS: 2-min intervals, 90 days = 64800

# ============================================================
# PART 1: Physical process
# ============================================================
t_sim = np.linspace(0, 1, NT)
day_sim = (t_sim * 90) + 1

# --- ROOT CAUSE: Media Wear Index ---
# Ball wear rate is steady, but operational events (ball addition) create resets
# Ball addition events at approximately days 30, 60
wear_idx = np.zeros(NT)
ball_addition_events = []
for i in range(NT):
    d = day_sim[i]
    base_wear = d / 90.0
    # Ball additions partially restore
    if d < 30:
        wear_idx[i] = base_wear * 0.9
    elif d < 32:
        # Ball addition at day 30 - partial recovery
        recovery = (d - 30) / 2
        wear_idx[i] = 0.3 * (1 - recovery) + 0.35 * recovery
    elif d < 60:
        wear_idx[i] = 0.35 + 0.4 * (d - 32) / 28
    elif d < 62:
        recovery = (d - 60) / 2
        wear_idx[i] = 0.55 * (1 - recovery) + 0.6 * recovery
    else:
        wear_idx[i] = 0.6 + 0.4 * (d - 62) / 28
    wear_idx[i] = np.clip(wear_idx[i], 0.01, 1.0)

ball_diameter = 80.0 - 8.0 * wear_idx
surface_area_ratio = (ball_diameter / 80.0) ** 2
power_factor = (ball_diameter / 80.0) ** 3

# --- Clinker source (alternating A/B with some random extension) ---
clinker_src = np.full(NT, 'A', dtype=object)
for i in range(NT):
    d = day_sim[i]
    # Source A: day 1-8, 15-24, 31-37, 44-52, 59-66, 73-80, 87-90
    # Source B: day 9-14, 25-30, 38-43, 53-58, 67-72, 81-86
    in_a = False
    for start, end in [(1, 8.5), (15, 24.5), (31, 37.5), (44, 52.5),
                       (59, 66.5), (73, 80.5), (87, 91)]:
        if start <= d < end:
            in_a = True
            break
    clinker_src[i] = 'A' if in_a else 'B'

hardness_idx = np.where(clinker_src == 'A', 46 + 2 * np.random.rand(NT),
                        53 + 2.5 * np.random.rand(NT))

# ============================================================
# PART 2: Sensor artifact helper
# ============================================================
def add_artifacts(signal, noise_std=0.1, spike_p=0.002, deadzone_p=0.0,
                  t_df=3, dropout_p=0.001):
    out = signal.copy()
    n = len(out)

    # Heavy-tailed noise (t-dist)
    out += np.random.standard_t(t_df, n) * noise_std

    # Sensor dead zone (freeze)
    if deadzone_p > 0:
        dz_len = int(n * deadzone_p)
        dz_start = np.random.randint(0, n - dz_len)
        out[dz_start:dz_start + dz_len] = out[dz_start]

    # Dropouts (NaN)
    if dropout_p > 0:
        out[np.random.random(n) < dropout_p] = np.nan

    return out

# ============================================================
# PART 3: DCS process parameters
# ============================================================
# Mill feed - operator reduces when grinding is poor
mill_feed = 140 + 3 * np.random.randn(NT)
mill_feed -= 10 * np.maximum(0, wear_idx - 0.45)
mill_feed = add_artifacts(mill_feed, noise_std=2.5, spike_p=0.0015, dropout_p=0.0005)
mill_feed = np.clip(mill_feed, 100, 155)

# Mill power
mill_power = 3600 * power_factor + 150 * (hardness_idx - 46) / 10
mill_power = add_artifacts(mill_power, noise_std=20, spike_p=0.001)
# On day 45, power meter recalibration (step change of +18 kW)
mill_power[day_sim > 45] += 18
mill_power = np.clip(mill_power, 2200, 3900)

# Mill vibration (liner wear indicator)
mill_vib = 2.0 + 4.0 * wear_idx + 0.5 * np.random.randn(NT)
mill_vib = np.clip(mill_vib, 1.0, 7.5)

# Separator speed - operator compensation
sep_speed = 880 + 350 * wear_idx + np.random.normal(0, 12, NT)

# Reject rate
reject_rate = 15 + 22 * wear_idx + np.random.standard_t(3, NT) * 1.2
reject_rate = np.clip(reject_rate, 8, 42)

# Feed moisture (weather-driven, 14-day cycle)
feed_moist = 1.2 + 0.8 * np.sin(2 * np.pi * day_sim / 14) + np.random.standard_t(3, NT) * 0.15
feed_moist = np.clip(feed_moist, 0.4, 3.5)

# Mill outlet temperature
mill_temp = 110 - 12 * wear_idx + 3 * np.sin(2 * np.pi * day_sim / 7)
mill_temp = add_artifacts(mill_temp, noise_std=1.5, deadzone_p=0.01)  # occasional sensor freeze

# Main bearing temperature - independent of root cause
# *** INTERFERING SIGNAL #1 ***
# Bearing temp has a gradual rise trend (ambient warming) that COULD be confused with mill degradation
bearing_temp = 62 + 5 * np.sin(2 * np.pi * day_sim / 90)  # seasonal
bearing_temp += 3 * np.sin(2 * np.pi * day_sim / 7)  # weekly
# Plus a bearing issue on day 72-74 (unrelated spike)
spike_mask = (day_sim >= 72) & (day_sim <= 74)
bearing_temp[spike_mask] += 12 + 3 * np.random.randn(sum(spike_mask))
bearing_temp = add_artifacts(bearing_temp, noise_std=1.2, spike_p=0.001)
bearing_temp = np.clip(bearing_temp, 50, 82)

# Mill sound level (ear) - desensitizes over time (sensor fault!)
# *** INTERFERING SIGNAL #2 ***
mill_sound = 82 + 6 * np.random.randn(NT)
mill_sound -= 15 * wear_idx  # less sound when less grinding
# Sensor microphone gradually gets clogged with dust - attenuates signal
dust_factor = 1.0 - 0.5 * np.minimum(1, day_sim / 90)
mill_sound *= dust_factor
mill_sound = np.clip(mill_sound, 40, 95)

# Separator current
sep_current = 180 + 40 * wear_idx + np.random.normal(0, 5, NT)

# Gypsum dosage
gypsum = 4.5 + 0.8 * np.random.randn(NT)

# Baghouse DP (differential pressure)
baghouse_dp = 1.8 + 0.3 * np.random.randn(NT)
baghouse_dp += 0.4 * np.sin(2 * np.pi * day_sim / 30)  # cleaning cycle

# ============================================================
# PART 4: Timestamps
# ============================================================
dcs_times = []
t = datetime(2025, 10, 1, 0, 0, 0)
for i in range(NT):
    dcs_times.append(t)
    j = int(np.random.choice([-20, -10, 0, 0, 10, 20, 40],
                             p=[0.03, 0.07, 0.6, 0.1, 0.1, 0.07, 0.03]))
    t += timedelta(seconds=120 + j)

ts_str = [ts.strftime('%Y-%m-%d %H:%M:%S') for ts in dcs_times]

# ============================================================
# PART 5: DCS DataFrame
# ============================================================
df_dcs = pd.DataFrame({
    'ts_dcs': ts_str,
    'day': np.round(day_sim, 1),
    'shift': np.random.choice([1, 2, 3], NT),
    'clinker_source': list(clinker_src),
    'mill_feed_tph': np.round(mill_feed, 1),
    'mill_power_kW': np.round(mill_power, 1),
    'mill_vibration_mm_s': np.round(mill_vib, 3),
    'separator_speed_rpm': np.round(sep_speed, 1),
    'reject_rate_pct': np.round(reject_rate, 2),
    'feed_moisture_pct': np.round(feed_moist, 2),
    'mill_outlet_temp_C': np.round(mill_temp, 1),
    'main_bearing_temp_C': np.round(bearing_temp, 1),
    'mill_sound_dB': np.round(mill_sound, 1),
    'separator_current_A': np.round(sep_current, 1),
    'gypsum_dosage_pct': np.round(gypsum, 2),
    'baghouse_dp_kPa': np.round(baghouse_dp, 3),
})

# Ball addition events in DCS
ball_additions = []
for add_day in [30, 60]:
    idx = int(add_day / 90 * NT)
    ball_additions.append({'ts_event': ts_str[idx], 'event_type': 'MEDIA_ADDITION',
                           'description': f'Added 5 tons of Ø80mm grinding balls'})

# ============================================================
# PART 6: Quality data (lab, every 2-4 hours, ~720 rows)
# ============================================================
n_qual = int(NT * 0.012)  # ~777 = roughly every 80 min
qual_idx = np.sort(np.random.choice(NT, n_qual, replace=False))

blaine = 3800 - 550 * wear_idx[qual_idx]
blaine += 0.15 * (sep_speed[qual_idx] - 880)
blaine -= 50 * (hardness_idx[qual_idx] - 46) / 10
blaine = add_artifacts(blaine, noise_std=35, spike_p=0.005, t_df=2)
blaine = np.clip(blaine, 2900, 4200)

residue = 3.8 + 12 * wear_idx[qual_idx]
residue += 1.2 * (hardness_idx[qual_idx] - 46) / 10
residue = add_artifacts(residue, noise_std=0.4, spike_p=0.003, t_df=3)
residue = np.clip(residue, 1.8, 20)

strength_3d = 19.0 - 5 * wear_idx[qual_idx] - 1.0 * (hardness_idx[qual_idx] - 46) / 10
strength_3d = add_artifacts(strength_3d, noise_std=0.3, spike_p=0.002)
strength_3d = np.clip(strength_3d, 11, 22)

strength_28d = 43.5 - 8 * wear_idx[qual_idx] - 1.5 * (hardness_idx[qual_idx] - 46) / 10
strength_28d = add_artifacts(strength_28d, noise_std=0.5, spike_p=0.002)
strength_28d = np.clip(strength_28d, 30, 48)

cement_temp = mill_temp[qual_idx] + 6 + np.random.standard_t(3, n_qual) * 1.5
cement_temp = np.clip(cement_temp, 75, 125)

# Defect grade
defect = np.full(n_qual, 'A', dtype=object)
for i in range(n_qual):
    s = 0
    if blaine[i] < 3200:
        s += 2
    elif blaine[i] < 3500:
        s += 1
    if residue[i] > 12:
        s += 2
    elif residue[i] > 8:
        s += 1
    if strength_28d[i] < 36:
        s += 1
    if mill_vib[qual_idx[i]] > 4.5:
        s += 1
    if s >= 4:
        defect[i] = 'C'
    elif s >= 2:
        defect[i] = 'B'

# ============================================================
# PART 7: Quality DataFrame
# ============================================================
df_qual = pd.DataFrame({
    'ts_lab': [ts_str[idx] for idx in qual_idx],
    'day': np.round(day_sim[qual_idx], 1),
    'clinker_source': list(clinker_src[qual_idx]),
    'blaine_fineness_cm2g': np.round(blaine, 0),
    'residue_45um_pct': np.round(residue, 2),
    'strength_3d_MPa': np.round(strength_3d, 2),
    'strength_28d_MPa': np.round(strength_28d, 2),
    'cement_temperature_C': np.round(cement_temp, 1),
    'defect_grade': list(defect),
})

# ============================================================
# PART 8: Event log
# ============================================================
events = []
# Clinker source changes
prev_src = None
for i in range(0, NT, 180):  # every 6 hours
    s = clinker_src[i]
    if s != prev_src and prev_src is not None:
        events.append({'ts_event': ts_str[i], 'event_type': 'SOURCE_CHANGE',
                       'description': f'Clinker source change: {prev_src} → {s}'})
    prev_src = s

events.extend(ball_additions)

# Mill stop for liner inspection
events.append({'ts_event': ts_str[int(45 / 90 * NT)],
               'event_type': 'INSPECTION',
               'description': 'Mill stopped for liner inspection - no significant wear found'})

# Bearing inspection after spike
events.append({'ts_event': ts_str[int(73.5 / 90 * NT)],
               'event_type': 'BEARING_CHECK',
               'description': 'Main bearing temperature spike investigated - grease relubricated, normal operation resumed'})

# Spurious event: power meter replaced
events.append({'ts_event': ts_str[int(45 / 90 * NT + 10)],
               'event_type': 'INSTRUMENT',
               'description': 'Mill power meter recalibrated (offset correction +18 kW)'})

df_events = pd.DataFrame(events)
df_events = df_events.sort_values('ts_event')

# ============================================================
# PART 9: SAVE
# ============================================================
base = "/Volumes/laxer/codes/skills/ industrial-deep-diagnostic/data/cement_ball_mill"

df_dcs.to_csv(f'{base}/DCS_export_20251001_20251229.csv', index=False)
df_qual.to_csv(f'{base}/lab_quality_export_20251001_20251229.csv', index=False)
df_events.to_csv(f'{base}/maintenance_event_log_2025Q4.csv', index=False)

# Also merged
merged_rows = []
for idx in qual_idx:
    r = {**dict(df_dcs.iloc[idx]), **dict(df_qual.iloc[len(merged_rows)])}
    merged_rows.append(r)
df_merged = pd.DataFrame(merged_rows)
df_merged.to_csv(f'{base}/merged_dcs_lab_20251001_20251229.csv', index=False)

print(f"=== Cement Ball Mill - 3-file Industrial Export ===")
print(f"DCS data:          {len(df_dcs):>6} rows (2-min interval, 90 days)")
print(f"Lab quality:       {len(df_qual):>6} rows")
print(f"Event log:         {len(df_events):>3} events")
print(f"Ball diameter:     Ø{ball_diameter[0]:.1f} → Ø{ball_diameter[-1]:.1f} mm")
print(f"Defect:            A={sum(d=='A' for d in defect)}, B={sum(d=='B' for d in defect)}, C={sum(d=='C' for d in defect)}")
print(f"\nInterfering signals:")
print(f"  - Main bearing temp spike (d72-74, unrelated bearing issue)")
print(f"  - Mill sound sensor dust clog (attenuates, not root cause)")
print(f"  - Clinker source switching (creates between-group confound)")
print(f"Events:            Ball additions d30/d60, power meter recal d45, bearing check d73")
