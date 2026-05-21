#!/usr/bin/env python3
"""Generate synthetic industrial test data for PVA optical film coating line.

Scenario: Transmittance anomaly caused by oven zone 2 temperature drift.
The causal chain: oven_z2 temp drifts up → surface skins too fast →
solvent trapped → transmittance drops, haze increases.

Timeline (120 minutes, 10s interval = 720 rows):
  0-40 min:   Normal operation
  40-60 min:  Oven Z2 temperature begins drifting up (PID controller degradation)
  60-80 min:  Peak anomaly — transmittance drops significantly
  80-100 min: Operator intervention, temperature recovering
  100-120 min: Back to normal
"""

import numpy as np
import pandas as pd

np.random.seed(42)

# Time axis: 120 minutes at 10-second intervals
n_points = 720  # 120 min * 60s / 10s
start = pd.Timestamp("2024-06-15 08:00:00")
timestamps = pd.date_range(start=start, periods=n_points, freq="10s")
t_minutes = np.arange(n_points) * 10 / 60  # minutes from start

# --- Process Parameters (normal operation values) ---
coater_speed = 20.0 + np.random.normal(0, 0.3, n_points)          # m/min
pump_speed = 150.0 + np.random.normal(0, 1.0, n_points)          # RPM
oven_z1_temp = 110.0 + np.random.normal(0, 0.5, n_points)        # °C
oven_z3_temp = 100.0 + np.random.normal(0, 0.4, n_points)        # °C
drying_air_flow = 500.0 + np.random.normal(0, 5.0, n_points)     # m³/h
solution_viscosity = 15.0 + np.random.normal(0, 0.3, n_points)   # mPa·s

# --- Oven Z2 Temperature: the root cause signal ---
oven_z2_temp = np.copy(120.0 + np.random.normal(0, 0.5, n_points))

# Phase 1: normal (0-40 min)
# Phase 2: gradual drift up (40-60 min) — PID controller degradation
drift_mask = (t_minutes >= 40) & (t_minutes < 60)
drift_progress = (t_minutes[drift_mask] - 40) / 20  # 0→1
oven_z2_temp[drift_mask] += drift_progress * 15  # drift +15°C

# Phase 3: peak anomaly (60-80 min)
peak_mask = (t_minutes >= 60) & (t_minutes < 80)
oven_z2_temp[peak_mask] += 15 + np.random.normal(0, 0.8, peak_mask.sum())  # stuck at ~135°C

# Phase 4: recovery (80-100 min)
recovery_mask = (t_minutes >= 80) & (t_minutes < 100)
recovery_progress = (t_minutes[recovery_mask] - 80) / 20  # 0→1
oven_z2_temp[recovery_mask] += 15 * (1 - recovery_progress)  # 135→120

# Phase 5: post-recovery (100-120 min) — back to normal
# (already at baseline noise level)

# --- Heater power (control variable, responds to temperature error) ---
heater_z2_power = 50.0 + np.random.normal(0, 1.0, n_points)
# When temperature drifts up, PID tries to reduce power
temp_error = oven_z2_temp - 120.0
heater_z2_power -= temp_error * 0.8  # PID response (but failing during anomaly)

# --- Inspection/Quality Signals ---
# Coating thickness: affected slightly by temperature (thermal expansion)
coating_thickness = 25.0 + np.random.normal(0, 0.15, n_points)
coating_thickness += (oven_z2_temp - 120) * 0.02  # slight thermal effect

# Transmittance: the primary quality issue
# Normal ~92%, drops when oven is too hot (surface skins, traps solvent)
transmittance = 92.0 + np.random.normal(0, 0.3, n_points)
# The anomaly effect — delayed by ~2 minutes (process lag)
lag_indices = np.clip(np.arange(n_points) - 12, 0, n_points - 1)  # 2-min lag
lagged_temp_error = oven_z2_temp[lag_indices] - 120.0
transmittance -= lagged_temp_error * 0.45  # ~0.45% transmittance loss per °C

# Haze: increases with overheating
haze = 1.2 + np.random.normal(0, 0.1, n_points)
haze += lagged_temp_error * 0.08  # haze increase per °C

# Surface resistance: slight increase with trapped solvent
surface_resistance = 100.0 + np.random.normal(0, 2.0, n_points)
surface_resistance += lagged_temp_error * 0.5

# --- Add a few missing values (realistic) ---
missing_indices = np.random.choice(n_points, size=8, replace=False)
for idx in missing_indices:
    col_choice = np.random.choice(['haze_pct', 'surface_resistance_ohm', 'solution_viscosity_mpas'])
    # We'll set these to NaN after building the DataFrame

# --- Add one event: batch change ---
batch_id = np.full(n_points, 'PVA-2024-0615-A', dtype=object)
batch_change_idx = int(90 * 60 / 10)  # at 90 minutes
batch_id[batch_change_idx:] = 'PVA-2024-0615-B'
product_code = np.full(n_points, 'PVA-OPT-25', dtype=object)

# --- Build DataFrame ---
df = pd.DataFrame({
    'timestamp': timestamps,
    'coater_speed_mpm': np.round(coater_speed, 2),
    'pump_speed_rpm': np.round(pump_speed, 1),
    'oven_z1_temp_c': np.round(oven_z1_temp, 2),
    'oven_z2_temp_c': np.round(oven_z2_temp, 2),
    'oven_z3_temp_c': np.round(oven_z3_temp, 2),
    'heater_z2_power_pct': np.round(heater_z2_power, 1),
    'drying_air_flow_m3h': np.round(drying_air_flow, 1),
    'solution_viscosity_mpas': np.round(solution_viscosity, 2),
    'coating_thickness_um': np.round(coating_thickness, 3),
    'transmittance_pct': np.round(transmittance, 2),
    'haze_pct': np.round(haze, 3),
    'surface_resistance_ohm': np.round(surface_resistance, 1),
    'batch_id': batch_id,
    'product_code': product_code,
})

# Insert missing values
for idx in missing_indices[:3]:
    df.loc[idx, 'haze_pct'] = np.nan
for idx in missing_indices[3:5]:
    df.loc[idx, 'surface_resistance_ohm'] = np.nan
for idx in missing_indices[5:]:
    df.loc[idx, 'solution_viscosity_mpas'] = np.nan

# Save
output_path = "pva_coating_line_data.csv"
df.to_csv(output_path, index=False)
print(f"Generated {len(df)} rows x {len(df.columns)} columns")
print(f"Time range: {df['timestamp'].iloc[0]} to {df['timestamp'].iloc[-1]}")
print(f"\nColumn summary:")
for col in df.columns:
    dtype = df[col].dtype
    missing = df[col].isna().sum()
    if pd.api.types.is_numeric_dtype(df[col]):
        print(f"  {col}: mean={df[col].mean():.2f}, std={df[col].std():.2f}, missing={missing}")
    else:
        print(f"  {col}: dtype={dtype}, unique={df[col].nunique()}, missing={missing}")

print(f"\nSaved to: {output_path}")

# Print anomaly summary
print(f"\n--- Anomaly Summary ---")
print(f"Normal period (0-40 min):")
mask1 = (t_minutes >= 0) & (t_minutes < 40)
print(f"  oven_z2_temp: {oven_z2_temp[mask1].mean():.1f} °C")
print(f"  transmittance: {transmittance[mask1].mean():.1f} %")
print(f"  haze: {haze[mask1].mean():.2f} %")
print(f"\nAnomaly period (60-80 min):")
mask2 = (t_minutes >= 60) & (t_minutes < 80)
print(f"  oven_z2_temp: {oven_z2_temp[mask2].mean():.1f} °C")
print(f"  transmittance: {transmittance[mask2].mean():.1f} %")
print(f"  haze: {haze[mask2].mean():.2f} %")
