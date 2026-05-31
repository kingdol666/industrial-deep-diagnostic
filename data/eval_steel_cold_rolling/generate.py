"""
Scenario: Steel Cold Rolling Mill — Work Roll Eccentricity + Surface Wear
Process Type: Quality inspection / continuous rolling
Root Cause: Work roll bearing eccentricity (0.12mm runout developing after bearing
           cage fracture) → cyclic thickness variation + surface chatter marks
Discriminability: Work roll change at coil #35 resets thickness variation completely
                  → proves roll is the root cause (not mill housing or tension control)
Confounders: Entry strip thickness variation (hot mill), tension fluctuation,
             emulsion temperature, rolling speed changes per product spec
Duration: 50 coils, ~2500 samples at 0.5-sec intervals within-coil + coil averages
"""
import numpy as np, pandas as pd

np.random.seed(505)
n = 2500
time = pd.date_range('2026-05-10 06:00:00', periods=n, freq='5s')
t = np.arange(n)

# ---- Coil tracking ----
coils = []
coil_start = 0
coil_lengths = np.random.randint(40, 65, 50)  # 50 coils, 40-65 samples each
for ci, cl in enumerate(coil_lengths):
    coils.extend([ci + 1] * cl)

coil_num = np.array(coils[:n])
coil_starts = np.concatenate([[0], np.cumsum(coil_lengths)[:-1]])[:len(coil_num)]

# ---- Hidden root cause: Work roll eccentricity ----
# Roll change at coil #35
roll_change_coil = 35
# Calculate start index of coil 35 by summing lengths of coils 1-34
roll_change_idx = int(np.sum(coil_lengths[:roll_change_coil - 1]))

# Before roll change: eccentricity grows (bearing cage fracture propagates)
# After roll change: eccentricity resets to near-zero (new roll + bearing)
sample_in_coil = t - coil_starts[np.searchsorted(np.unique(coil_num, return_index=True)[1], range(len(t)), side='right') - 1]
sample_in_coil = np.array([t[i] - coil_starts[np.searchsorted(np.unique(coil_num), coil_num[i], side='right') - 1] if i < len(coil_starts) else 0 for i in range(n)])

# Eccentricity amplitude (mm) — grows with bearing wear, resets on roll change
eccentricity_base = np.zeros(n)
for i in range(1, n):
    if coil_num[i] < roll_change_coil:
        growth_rate = 0.00004 * (1 + 0.5 * max(0, coil_num[i] - 20))
        eccentricity_base[i] = np.clip(eccentricity_base[i-1] + growth_rate + np.random.normal(0, 0.00001), 0, 0.18)
    elif coil_num[i] == roll_change_coil:
        eccentricity_base[i] = np.random.normal(0, 0.005)  # reset
    else:
        # New roll also wears but much slower
        eccentricity_base[i] = min(0.035, eccentricity_base[i-1] + 0.00002 + np.random.normal(0, 0.000005))

eccentricity = eccentricity_base + 0.01 * np.random.normal(0, 1, n)

# ---- Process parameters ----
# Rolling force (kN) — varies with eccentricity (cyclic at ~2Hz = roll rotation freq)
roll_force_kN = 8500 + 1200*np.sin(2*np.pi*t*2.0 + 0.3) * eccentricity * 5 + np.random.normal(0, 80, n)

# Strip tension entry/exit (kN)
entry_tension_kN = 120 + 15*np.sin(2*np.pi*t*2.0) * eccentricity * 3 + np.random.normal(0, 3, n)
exit_tension_kN = 105 + 10*np.sin(2*np.pi*t*2.0 + 0.5) * eccentricity * 3 + np.random.normal(0, 2, n)

# Rolling speed (m/min) — varies by product spec
roll_speed_m_min = 800 + 200*(coil_num % 3 == 0).astype(float) + np.random.normal(0, 15, n)

# Gap position (mm) — AGC response to thickness variation
gap_position_mm = 0.85 - 0.03*eccentricity + 0.002*(roll_force_kN - 8500)/1200 + np.random.normal(0, 0.005, n)

# ---- Quality: strip thickness ----
target_thickness = 0.80  # mm
thickness_mm = (target_thickness +
                0.10*np.sin(2*np.pi*t*2.0) * eccentricity * 6 +  # eccentricity ripple
                0.08*np.sin(2*np.pi*t*0.5) * (1 - np.clip(coil_num/50, 0, 1)) +  # backup roll (stable)
                np.random.normal(0, 0.012, n))
thickness_deviation_um = (thickness_mm - target_thickness) * 1000  # microns

# ---- Quality: surface finish ----
surface_roughness_Ra_um = 0.6 + 0.35*eccentricity*10 + np.random.normal(0, 0.04, n)
chatter_mark_severity = np.where(eccentricity > 0.08,
    np.random.choice([0,1,2], n, p=[0.3, 0.4, 0.3]), 0)

# ---- Quality: flatness (I-unit) ----
flatness_I_unit = 5 + 20*eccentricity*5 + np.random.normal(0, 2, n)

# ---- Confounders ----
# Entry thickness variation (from hot mill — upstream process)
entry_thickness_mm = 2.50 + 0.06*np.sin(2*np.pi*t/300) + np.random.normal(0, 0.02, n)

# Emulsion temperature
emulsion_temp_C = 52 + 6*np.sin(2*np.pi*t/2000 + 1.0) + np.random.normal(0, 0.8, n)

# Emulsion concentration
emulsion_conc_pct = 3.5 + 0.5*np.random.random(n)

# ---- Distractor events ----
# Coil #28: incoming hot mill strip is thicker (upstream issue, not mill)
thick_entry_start = np.where(coil_num == 28)[0][0] if 28 in coil_num else 2000
thick_entry_end = min(thick_entry_start + 50, n)
entry_thickness_mm[thick_entry_start:thick_entry_end] += 0.15

# Speed change for product grade at coil #40
speed_change = np.where(coil_num == 40)[0][0] if 40 in coil_num else 2200
roll_speed_m_min[speed_change:] += 150

# ---- Product grades ----
product_spec = np.where(coil_num <= 15, 'DQSK',
               np.where(coil_num <= 30, 'HSLA340',
               np.where(coil_num <= 45, 'DQSK', 'HSLA340')))

df = pd.DataFrame({
    'timestamp': time,
    'coil_number': coil_num,
    'samples_in_coil': np.clip(sample_in_coil, 0, 70),
    'roll_force_kN': np.round(roll_force_kN, 0).astype(int),
    'gap_position_mm': np.round(gap_position_mm, 4),
    'entry_tension_kN': np.round(entry_tension_kN, 1),
    'exit_tension_kN': np.round(exit_tension_kN, 1),
    'roll_speed_m_min': np.round(roll_speed_m_min, 0).astype(int),
    'entry_thickness_mm': np.round(entry_thickness_mm, 3),
    'exit_thickness_mm': np.round(thickness_mm, 4),
    'thickness_deviation_um': np.round(thickness_deviation_um, 1),
    'surface_roughness_Ra_um': np.round(surface_roughness_Ra_um, 3),
    'chatter_mark_severity': chatter_mark_severity,
    'flatness_I_unit': np.round(flatness_I_unit, 1),
    'emulsion_temp_C': np.round(emulsion_temp_C, 1),
    'emulsion_conc_pct': np.round(emulsion_conc_pct, 2),
    'product_spec': product_spec,
    'shift': np.where((t//1200)%3==0,'Day',
              np.where((t//1200)%3==1,'Afternoon','Night')),
})

fp = '/Volumes/laxer/codes/skills/ industrial-deep-diagnostic/data/eval_steel_cold_rolling/data.csv'
df.to_csv(fp, index=False)
print(f"steel_cold_rolling: {len(df)} rows x {len(df.columns)} cols")
print(f"  50 coils, roll change at coil #{roll_change_coil} (idx ~{roll_change_idx})")
before_slice = eccentricity_base[max(0,roll_change_idx-200):roll_change_idx]
after_slice = eccentricity_base[roll_change_idx:min(n,roll_change_idx+500)]
print(f"  Eccentricity before roll change: max={before_slice.max():.3f}mm" if len(before_slice)>0 else "  (no data before)")
print(f"  Eccentricity after roll change: max={after_slice.max():.3f}mm" if len(after_slice)>0 else "  (no data after)")
print(f"  Thickness deviation range: {thickness_deviation_um.min():.0f}-{thickness_deviation_um.max():.0f} um")
print(f"  Flatness range: {flatness_I_unit.min():.0f}-{flatness_I_unit.max():.0f} I-unit")
print(f"  Chatter marks (before roll change): {np.mean(chatter_mark_severity[:roll_change_idx] > 0)*100:.0f}%")
print(f"  Chatter marks (after roll change): {np.mean(chatter_mark_severity[roll_change_idx:] > 0)*100:.0f}%")
