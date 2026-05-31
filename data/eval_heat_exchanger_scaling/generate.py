"""
Scenario: Shell-and-Tube Heat Exchanger — Cooling Water CaCO₃ Scaling
Process Type: Heat exchange / thermal system
Root Cause: Calcium carbonate precipitation on tube interior due to LSI > 1.5
           at operating temperature; scale thickness grows ~linearly with time
Discriminability: Acid cleaning at t=1300 removes ~50% scale → HTC partially recovers
Confounders: Process load daily cycle, cooling tower fan cycling, pump VFD adjustment
Duration: 45 days, 2160 samples at 30-min intervals
"""
import numpy as np, pandas as pd

np.random.seed(404)
n = 2160
time = pd.date_range('2026-08-01 00:00:00', periods=n, freq='30min')
t = np.arange(n)

# ---- Hidden root cause: CaCO3 scale growth (linear = 0 at day 1, 1 at day 45) ----
scale_thickness = np.clip(t / 2160, 0, 1.0)
scale_thickness += 0.05 * np.sin(scale_thickness * np.pi)  # slight non-linearity

# ---- Thermal consequence: heat transfer coefficient ----
htc_clean = 1150  # W/m²K
fouling_factor = 0.00005 + 0.0005 * scale_thickness  # m²K/W
htc_W_m2K = 1.0 / (1.0/htc_clean + fouling_factor) + np.random.normal(0, 10, n)

# ---- Process fluid temperatures ----
hot_inlet_C = 88 + np.random.normal(0, 0.4, n)
hot_outlet_C = hot_inlet_C - 22 * (htc_W_m2K/htc_clean) + np.random.normal(0, 0.3, n)

# Cold side temperatures
cold_inlet_C = 20 + 6*np.sin(2*np.pi*t/1440 + 0.5) + np.random.normal(0, 0.4, n)
cold_outlet_C = cold_inlet_C + 18 * (htc_W_m2K/htc_clean) + np.random.normal(0, 0.4, n)

# ---- Thermal metrics ----
approach_temp_C = hot_outlet_C - cold_inlet_C  # widens with fouling
efficiency_pct = np.clip(88 - 25*scale_thickness + np.random.normal(0, 0.8, n), 55, 92)
lmtd_C = np.where(
    (hot_inlet_C - cold_outlet_C) > 0.1,
    ((hot_inlet_C - cold_outlet_C) - approach_temp_C) /
    np.log(np.maximum(0.5, (hot_inlet_C - cold_outlet_C)/np.maximum(0.5, approach_temp_C))),
    30
)

# ---- Hydraulic consequence: pressure drop ----
pressure_drop_bar = 0.7 + 2.0*scale_thickness + np.random.normal(0, 0.03, n)

# ---- Flow & pump ----
pump_speed_pct = np.clip(62 + 28*scale_thickness + np.random.normal(0, 0.8, n), 58, 95)
flow_rate_m3_hr = 200 + 30*(pump_speed_pct-62)/33 - 12*scale_thickness + np.random.normal(0, 1.5, n)

# ---- Process load (daily production cycle) ----
process_load_MW = 5.5 + 1.5*np.sin(2*np.pi*t/48) + np.random.normal(0, 0.15, n)

# ---- Confounder: cooling tower performance ----
ct_approach_C = 5 + 2*np.sin(2*np.pi*t/2000) + np.random.normal(0, 0.3, n)

# ---- Distractor events ----
# Acid cleaning at t=1300 (removes ~50% of scale)
clean_idx = 1300
htc_W_m2K[clean_idx:] = 1.0 / (1.0/htc_clean + fouling_factor[clean_idx:]*0.5) + np.random.normal(0, 10, n-clean_idx)
hot_outlet_C[clean_idx:] = hot_inlet_C[clean_idx:] - 22*(htc_W_m2K[clean_idx:]/htc_clean) + np.random.normal(0, 0.3, n-clean_idx)
efficiency_pct[clean_idx:] = np.clip(88 - 13*scale_thickness[clean_idx:] + np.random.normal(0, 0.8, n-clean_idx), 55, 92)

# Pump maintenance at t=650-654 (2 hours)
pump_mt = slice(650, 654)
flow_rate_m3_hr[pump_mt] = 5 + np.random.exponential(3, 4)
pump_speed_pct[pump_mt] = 0

# Cooling tower fan failure at t=1800-1900 (50 hours)
fan_fail = slice(1800, 1900)
cold_inlet_C[fan_fail] += 3.5 + np.random.normal(0, 0.4, 100)
ct_approach_C[fan_fail] += 3

df = pd.DataFrame({
    'timestamp': time,
    'hot_inlet_temp_C': np.round(hot_inlet_C, 1),
    'hot_outlet_temp_C': np.round(hot_outlet_C, 1),
    'cold_inlet_temp_C': np.round(cold_inlet_C, 1),
    'cold_outlet_temp_C': np.round(cold_outlet_C, 1),
    'approach_temp_C': np.round(approach_temp_C, 1),
    'lmtd_C': np.round(lmtd_C, 1),
    'heat_transfer_coeff_W_m2K': np.round(htc_W_m2K, 0).astype(int),
    'thermal_efficiency_pct': np.round(efficiency_pct, 1),
    'pressure_drop_bar': np.round(pressure_drop_bar, 3),
    'flow_rate_m3_hr': np.round(flow_rate_m3_hr, 1),
    'pump_speed_pct': np.round(pump_speed_pct, 1),
    'process_load_MW': np.round(process_load_MW, 2),
    'ct_approach_temp_C': np.round(ct_approach_C, 1),
    'unit_id': [f'HX-{i//432+1:02d}' for i in range(n)],  # ~9 day batches
    'shift': np.where((t//48)%3==0, 'Day',
              np.where((t//48)%3==1, 'Afternoon', 'Night')),
})

fp = '/Volumes/laxer/codes/skills/ industrial-deep-diagnostic/data/eval_heat_exchanger_scaling/data.csv'
df.to_csv(fp, index=False)
print(f"heat_exchanger_scaling: {len(df)} rows x {len(df.columns)} cols")
print(f"  HTC range: {htc_W_m2K.min():.0f}-{htc_W_m2K.max():.0f} W/m²K")
print(f"  Efficiency range: {efficiency_pct.min():.0f}-{efficiency_pct.max():.0f}%")
print(f"  Pressure drop range: {pressure_drop_bar.min():.3f}-{pressure_drop_bar.max():.3f} bar")
print(f"  Pre-cleaning HTC: {htc_W_m2K[1280:1300].mean():.0f}")
print(f"  Post-cleaning HTC: {htc_W_m2K[1310:1330].mean():.0f}  -> recovery confirmed")
print(f"  Pre-cleaning efficiency: {efficiency_pct[1280:1300].mean():.0f}%")
print(f"  Post-cleaning efficiency: {efficiency_pct[1310:1330].mean():.0f}%")
