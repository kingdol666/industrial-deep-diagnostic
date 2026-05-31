"""
Scenario: BOPET Film Production — MD Zone 3 Heater Degradation + Die Gap Thermal Asymmetry
Process Type: Continuous process (film extrusion/biaxial stretching)
Root Cause 1: MD_TH003 heating band oxidation → actual temp drops ~8°C below setpoint
Root Cause 2: Die bolt thermal drift → right-side gap widens (thermal expansion asymmetry)
Discriminability: Screen pack change (t=1200) resets filter pressure but NOT quality
Confounders: Ambient humidity seasonal, material IV batch variation, product grade changes
Duration: ~42 hours, 2500 samples at 1-min intervals
"""
import numpy as np, pandas as pd

np.random.seed(202)
n = 2500
time = pd.date_range('2026-07-01 00:00:00', periods=n, freq='min')
t = np.arange(n)

# ---- Root cause 1: MD_TH003 heater degradation (S-curve) ----
heater_degrade = 1.0 / (1.0 + np.exp(-0.005 * (t - 800)))
heater_degrade = heater_degrade * 0.88

# MD temperature zones (12 zones, only TH003 degrades)
md_temps = {}
for i in range(1, 13):
    if i == 3:
        md_temps[f'md_th{i:03d}'] = 95 - 9 * heater_degrade + np.random.normal(0, 0.7, n)
    else:
        base_list = [82, 88, 98, 100, 95, 85, 75, 72, 70, 70, 68]
        idx = i - 1 if i < 3 else i - 2
        md_temps[f'md_th{i:03d}'] = base_list[idx] + np.random.normal(0, 0.4, n)

# ---- Root cause 2: Die gap asymmetry (TD, right side drifts) ----
td_temps = {}
td_bases = [60, 62, 64, 62, 60, 58]
for i, b in enumerate(td_bases, 1):
    if i >= 4:
        td_temps[f'td_th{i:03d}'] = b + 2.5 * heater_degrade * (i - 3) + np.random.normal(0, 0.5, n)
    else:
        td_temps[f'td_th{i:03d}'] = b + np.random.normal(0, 0.4, n)

die_gaps = {}
for i, b in enumerate([850, 855, 860, 865, 870], 1):
    if i >= 4:
        die_gaps[f'die_gap_pos{i}'] = b + 8 * heater_degrade * (i - 3) + np.random.normal(0, 3, n)
    else:
        die_gaps[f'die_gap_pos{i}'] = b + np.random.normal(0, 2, n)

# ---- Process ----
extruder_speed = 45 + np.random.normal(0, 0.4, n)
melt_temp_C = 282 + 0.5 * heater_degrade + np.random.normal(0, 0.6, n)
melt_pressure_bar = 85 + 4 * heater_degrade + np.random.normal(0, 1.2, n)
filter_pressure_bar = 12 + 0.015 * t[:n] + 3 * heater_degrade + np.random.normal(0, 0.4, n)

# ---- Quality: film thickness ----
thickness_base = 50.0 + 2.5 * heater_degrade + np.random.normal(0, 0.4, n)
td_band_um = 0.3 + 3.5 * heater_degrade + np.random.normal(0, 0.15, n)

# ---- Quality: defects ----
melt_spots = 0.15 + 3.5 * np.maximum(0, (95 - md_temps['md_th003']) / 7) + np.random.exponential(0.2, n)
melt_spots = np.clip(melt_spots, 0, 10)
film_points = np.random.poisson(2 + 7 * heater_degrade, n)
scratch_rate = 0.05 + 0.4 * np.maximum(0, td_band_um - 1.5) + np.random.exponential(0.08, n)

# ---- Winding (secondary effect of thickness variation) ----
winding_tension = 120 + 3 * (thickness_base - 50) + np.random.normal(0, 2, n)

# ---- Confounders ----
humidity_pct = 45 + 15 * np.sin(2*np.pi*t/700 + 0.8) + np.random.normal(0, 2, n)
material_IV = 0.62 + 0.03 * np.sin(2*np.pi*t/900) + np.random.normal(0, 0.008, n)

# ---- Distractor events ----
# Screen pack change at t=1200: filter pressure resets, quality does NOT
filter_pressure_bar[1200:] -= 6

# Web break at t=1900-1910
melt_spots[1900:1910] += np.random.exponential(3, 10)
thickness_base[1900:1910] += np.random.normal(0, 3, 10)

# Product grades
grades = np.where(t < 800, 'Grade-A',
          np.where(t < 1600, 'Grade-B',
          np.where(t < 2000, 'Grade-A', 'Grade-C')))

df = pd.DataFrame({
    'timestamp': time,
    **{f'{k}_C': np.round(v, 1) for k, v in md_temps.items()},
    **{f'{k}_C': np.round(v, 1) for k, v in td_temps.items()},
    **{f'{k}_um': np.round(v, 1) for k, v in die_gaps.items()},
    'extruder_speed_rpm': np.round(extruder_speed, 1),
    'melt_temp_C': np.round(melt_temp_C, 1),
    'melt_pressure_bar': np.round(melt_pressure_bar, 1),
    'filter_pressure_bar': np.round(filter_pressure_bar, 1),
    'film_thickness_um': np.round(thickness_base, 2),
    'td_thickness_band_um': np.round(td_band_um, 2),
    'melt_spot_rate': np.round(melt_spots, 2),
    'film_point_count': film_points,
    'scratch_rate': np.round(scratch_rate, 2),
    'winding_tension_N': np.round(winding_tension, 1),
    'ambient_humidity_pct': np.round(humidity_pct, 1),
    'material_intrinsic_viscosity': np.round(material_IV, 3),
    'product_grade': grades,
    'reel_id': [f'REEL-{i//200+1:04d}' for i in range(n)],
    'batch_id': [f'LOT-{i//500+1:04d}' for i in range(n)],
})

fp = '/Volumes/laxer/codes/skills/ industrial-deep-diagnostic/data/eval_bopet_film_drift/data.csv'
df.to_csv(fp, index=False)
print(f"bopet_film_drift: {len(df)} rows x {len(df.columns)} cols")
print(f"  MD_TH003 range: {md_temps['md_th003'].min():.1f}-{md_temps['md_th003'].max():.1f} C")
print(f"  Melt spots vs MD_TH003 r = {np.corrcoef(md_temps['md_th003'], melt_spots)[0,1]:.3f}")
print(f"  Thickness band range: {td_band_um.min():.2f}-{td_band_um.max():.2f} um")
print(f"  Die gap pos5 range: {die_gaps['die_gap_pos5'].min():.1f}-{die_gaps['die_gap_pos5'].max():.1f} um")
print(f"  Filter pressure pre/post change: {filter_pressure_bar[1190:1200].mean():.1f} -> {filter_pressure_bar[1210:1220].mean():.1f} bar")
