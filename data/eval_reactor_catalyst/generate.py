"""
Scenario: Continuous Stirred Tank Reactor — Catalyst Selective Poisoning
Process Type: Batch chemical / continuous reaction
Root Cause: Feedstock trace thiophene poisoning Pd/Al2O3 hydrogenation catalyst
           → active sites blocked → conversion drops → byproduct rises
Discriminability: Catalyst regeneration at t=1200 restores activity temporarily
                  → proves poisoning is reversible and catalyst-related
Confounders: Feed rate variation (production scheduling), H2 partial pressure drift,
             Reactor temperature control response (compensation)
Duration: 60 days, 1440 samples at 1-hour intervals
"""
import numpy as np, pandas as pd

np.random.seed(303)
n = 1440
time = pd.date_range('2026-04-01 00:00:00', periods=n, freq='h')
t = np.arange(n)

# ---- Hidden root cause: thiophene poisoning ----
# Poison accumulation: linear with occasional step-changes (feedstock lot changes)
base_poison = np.zeros(n)
lot_changes = [0, 300, 600, 900, 1200]
lot_quality = [0.02, 0.08, 0.15, 0.05, 0.12]  # thiophene ppm in each lot
for i in range(n):
    lot_idx = sum(1 for lc in lot_changes if lc <= i) - 1
    if lot_idx < 0:
        lot_idx = 0
    base_poison[i] = lot_quality[lot_idx]

poison_level = np.zeros(n)
poison_level[0] = 0.02
for i in range(1, n):
    acc_rate = 0.0008 * base_poison[i]
    poison_level[i] = poison_level[i-1] + acc_rate + np.random.normal(0, 0.0002)
    # Step-change at lot boundaries
    if i in lot_changes[1:]:
        poison_level[i] += 0.12 * np.random.random()

# Smooth poison_level for realistic catalyst deactivation
from scipy.ndimage import uniform_filter1d
poison_level = uniform_filter1d(poison_level, size=20)
poison_level = np.clip(poison_level, 0.01, 0.85)

# ---- Catalyst active fraction ----
catalyst_activity = 1.0 - poison_level
# Regeneration at t=1200 (hot hydrogen strip) — restores ~60% of lost activity
regeneration_idx = 1200
lost_activity = 1.0 - catalyst_activity[regeneration_idx - 1]
catalyst_activity[regeneration_idx:] = np.minimum(1.0, catalyst_activity[regeneration_idx:] + lost_activity * 0.65)
# Post-regen: slow re-poisoning continues (same mechanism)

# ---- Reaction parameters ----
reactor_temp_C = 185 + 15 * (1 - catalyst_activity) + np.random.normal(0, 1.0, n)
h2_partial_pressure_bar = 25 - 5 * (1 - catalyst_activity) + np.random.normal(0, 0.5, n)
feed_rate_kg_hr = 500 + 50 * np.sin(2*np.pi*t/336) + np.random.normal(0, 8, n)

# ---- Quality: conversion and selectivity ----
conversion_pct = 95 * catalyst_activity + np.random.normal(0, 0.8, n)
conversion_pct = np.clip(conversion_pct, 25, 99)
byproduct_ppm = 80 + 400 * (1 - catalyst_activity) + np.random.normal(0, 15, n)
selectivity_pct = 98 - 12 * (1 - catalyst_activity) + np.random.normal(0, 0.8, n)

# ---- Reactor pressure ----
reactor_pressure_bar = 30 + 5 * (1 - catalyst_activity) + np.random.normal(0, 0.5, n)

# ---- Heat balance ----
cooling_duty_kW = 850 - 200 * catalyst_activity + np.random.normal(0, 15, n)
delta_T_reactor_C = reactor_temp_C - (25 + 5*np.sin(2*np.pi*t/720 + 1.0) + np.random.normal(0, 1, n))

# ---- Confounders ----
# Feedstock sulfur analyzer reading (online, but thiophene not detected by this method)
feed_sulfur_ppm = 5 + 3*np.random.random(n)  # total S looks normal

# Cooling water temp seasonal (confounds with reactor temp trend)
cooling_water_temp_C = 22 + 8*np.sin(2*np.pi*t/1440 + 0.7) + np.random.normal(0, 1.0, n)

# Product quality index (composite score 0-100)
quality_index = 95*catalyst_activity + np.random.normal(0, 2, n)
quality_index = np.clip(quality_index, 30, 100)

# ---- Distractor events ----
# Feed pump trip at t=750-754 (4 hours)
trip = slice(750, 754)
feed_rate_kg_hr[trip] *= 0.3
conversion_pct[trip] -= 8
byproduct_ppm[trip] += 80

# H2 compressor maintenance at t=550-560
h2_mt = slice(550, 560)
h2_partial_pressure_bar[h2_mt] -= 3

df = pd.DataFrame({
    'timestamp': time,
    'reactor_temp_C': np.round(reactor_temp_C, 1),
    'reactor_pressure_bar': np.round(reactor_pressure_bar, 2),
    'h2_partial_pressure_bar': np.round(h2_partial_pressure_bar, 2),
    'feed_rate_kg_hr': np.round(feed_rate_kg_hr, 1),
    'feed_sulfur_ppm': np.round(feed_sulfur_ppm, 1),
    'conversion_pct': np.round(conversion_pct, 1),
    'byproduct_ppm': np.round(byproduct_ppm, 1),
    'selectivity_pct': np.round(selectivity_pct, 1),
    'quality_index': np.round(quality_index, 1),
    'cooling_duty_kW': np.round(cooling_duty_kW, 1),
    'delta_T_reactor_C': np.round(delta_T_reactor_C, 1),
    'cooling_water_temp_C': np.round(cooling_water_temp_C, 1),
    'product_lot': [f'LOT-{i//72+1:04d}' for i in range(n)],
    'catalyst_bed_id': np.where(t < 1200, 'CAT-A', 'CAT-A-regenerated'),
    'shift': np.where((t//8)%3==0,'Day',np.where((t//8)%3==1,'Afternoon','Night')),
})

fp = '/Volumes/laxer/codes/skills/ industrial-deep-diagnostic/data/eval_reactor_catalyst/data.csv'
df.to_csv(fp, index=False)
print(f"reactor_catalyst: {len(df)} rows x {len(df.columns)} cols")
print(f"  Conversion range: {conversion_pct.min():.1f}-{conversion_pct.max():.1f}%")
print(f"  Byproduct range: {byproduct_ppm.min():.0f}-{byproduct_ppm.max():.0f} ppm")
print(f"  Pre-regeneration activity: {catalyst_activity[1190:1200].mean():.2f}")
print(f"  Post-regeneration activity: {catalyst_activity[1210:1220].mean():.2f}  -> recovery confirmed")
print(f"  Conversion vs byproduct r = {np.corrcoef(conversion_pct, byproduct_ppm)[0,1]:.3f}")
