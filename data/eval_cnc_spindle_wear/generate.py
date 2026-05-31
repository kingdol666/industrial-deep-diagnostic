"""
Scenario: CNC Precision Machining — Spindle Bearing Inner Race Spalling
Process Type: CNC machining
Root Cause: Spindle drive-end bearing inner race spalling (BPFI defect)
            due to inadequate lubrication film during cold starts
Discriminability: Tool changes DO NOT reset quality (proves bearing, not tool wear)
Confounders: Material type (AL7075/SS304), coolant temperature seasonal drift,
             night-shift operator compensation (feed overrides)
Duration: ~17.5 production hours, 1050 parts, 1 sample/part
"""
import numpy as np, pandas as pd

np.random.seed(101)
n = 1050
time = pd.date_range('2026-06-10 06:00:00', periods=n, freq='min')
t = np.arange(n)

# ---- Hidden root cause: bearing spalling (S-curve, accelerates mid-life) ----
spalling = 1.0 / (1.0 + np.exp(-0.015 * (t - 450)))
spalling = spalling * 0.95 + 0.05 * np.random.random(n)

# ---- Consequence: vibration ----
vibration_mm_s = 0.6 + 5.0 * spalling + np.random.normal(0, 0.15, n)
spike_mask = np.random.random(n) < 0.05
vibration_mm_s += spike_mask * np.random.exponential(2.0, n)
vibration_mm_s = np.clip(vibration_mm_s, 0.2, 8.0)

# ---- Consequence: spindle temperature ----
spindle_temp_C = 33 + 20 * spalling + 0.02 * vibration_mm_s + np.random.normal(0, 1.0, n)

# ---- Consequence: surface roughness (quality target) ----
material = np.random.choice(['AL7075', 'AL6061', 'SS304'], n, p=[0.45, 0.30, 0.25])
base_ra = {'AL7075': 0.35, 'AL6061': 0.45, 'SS304': 0.75}
roughness_Ra_um = np.array([
    base_ra[m] + 0.30 * vibration_mm_s[i] + 0.10 * spalling[i] * 3 + np.random.normal(0, 0.06)
    for i, m in enumerate(material)
])
roughness_Ra_um = np.clip(roughness_Ra_um, 0.15, 4.5)

# ---- Tools & discriminability ----
tool_changes = [0, 150, 380, 650, 900]
tool_id = np.zeros(n, dtype=object)
tool_age = np.zeros(n, dtype=int)
for idx in range(len(tool_changes)):
    start = tool_changes[idx]
    end = tool_changes[idx+1] if idx+1 < len(tool_changes) else n
    tool_id[start:end] = f'T00{idx+1}'
    tool_age[start:end] = np.arange(end - start)

# ---- Process params ----
spindle_speed_rpm = (12000 - 3500 * spalling + np.random.normal(0, 180, n)).astype(int)
feed_rate_mm_min = np.round(750 - 180 * spalling + np.random.normal(0, 25, n), 1)
cut_depth_mm = np.round(0.45 + 0.06 * np.random.random(n), 2)

# ---- Confounders ----
coolant_temp_C = 20 + 5 * np.sin(2*np.pi*t/800 + 1.5) + np.random.normal(0, 0.8, n)
operator = np.random.choice(['OP-A','OP-B','OP-C'], n, p=[0.45,0.30,0.25])
shift = np.where((t//480) % 3 == 0, 'Day',
         np.where((t//480) % 3 == 1, 'Afternoon', 'Night'))
thermal_dev_mm = np.round(0.001 + 0.0025 * (spindle_temp_C - 33) + np.random.normal(0, 0.003, n), 4)

# ---- Distractor: T005 is a defective tool ----
roughness_Ra_um[t >= 900] += 0.25

df = pd.DataFrame({
    'timestamp': time,
    'spindle_speed_rpm': spindle_speed_rpm,
    'feed_rate_mm_min': feed_rate_mm_min,
    'cut_depth_mm': cut_depth_mm,
    'spindle_vibration_mm_s': np.round(vibration_mm_s, 3),
    'spindle_temp_C': np.round(spindle_temp_C, 1),
    'coolant_temp_C': np.round(coolant_temp_C, 1),
    'surface_roughness_Ra_um': np.round(roughness_Ra_um, 3),
    'thermal_deviation_mm': thermal_dev_mm,
    'tool_age_parts': tool_age,
    'tool_id': tool_id,
    'material': material,
    'operator_id': operator,
    'shift': shift,
})

fp = '/Volumes/laxer/codes/skills/ industrial-deep-diagnostic/data/eval_cnc_spindle_wear/data.csv'
df.to_csv(fp, index=False)
print(f"cnc_spindle_wear: {len(df)} rows x {len(df.columns)} cols")
print(f"  Ra range: {roughness_Ra_um.min():.3f} - {roughness_Ra_um.max():.3f}")
print(f"  Vibration x Roughness r = {np.corrcoef(vibration_mm_s, roughness_Ra_um)[0,1]:.3f}")
for tc in tool_changes[1:]:
    before = roughness_Ra_um[max(0,tc-15):tc].mean()
    after = roughness_Ra_um[tc:min(n,tc+15)].mean()
    print(f"  Tool change @ {tc}: Ra before={before:.3f}, after={after:.3f} | reset={(before-after)/max(before,0.001)*100:.1f}%")
