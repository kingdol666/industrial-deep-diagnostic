# Industrial Process Knowledge Base Reference

This document provides quantitative domain knowledge for common industrial diagnostic scenarios. It is NOT a substitute for domain-specific research — always verify with user-provided references and actual data.

---

## Common Industrial Process Types

### Film Production (BOPET, BOPP, etc.)

**Signals**: thickness, optical properties, temperature profile, speed, tension, defects
**Common issues**: thickness variation, haze, optical defects, wrinkles, scratches, gel spots, bubbles

**Quantitative Physics:**

| Relationship | Formula/Rule of Thumb | Source |
|-------------|----------------------|--------|
| PET extrusion temperature | 270-290°C (melt), Tg ≈ 75°C | Polymer physics |
| PET thermal degradation rate | ~doubles per 10°C (Arrhenius), Ea ≈ 150-200 kJ/mol | Polymer chemistry |
| PET degradation half-life at 280°C | Minutes | Extrusion engineering |
| PET degradation half-life at 75-80°C | Months | Arrhenius extrapolation |
| MD stretching temperature (BOPET) | Tg+0-5°C (75-83°C) for high-temp zones | Film process engineering |
| MD cooling zone temperature | 31-37°C (well below Tg to freeze orientation) | Film process engineering |
| Oligomer (cyclic trimer) formation | Requires T > 200°C for significant rates; concentration in film typically 0.5-2% wt | PET chemistry |
| Temperature-thickness coupling | ±2°C MD temp fluctuation → 1-3% thickness variation | Stress-strain curve at stretching T |
| Die gap effect on thickness | 1 μm die gap change → measurable thickness change | Extrusion die physics |
| Vacuum degassing target | 20-50 mbar absolute at vent port; residual moisture > 50 ppm → bubbles | Extrusion engineering |
| PET hydrolysis threshold | Moisture > 50 ppm in melt → significant IV drop + bubble formation | PET processing |
| Winding tension effect | Tension variation > ±10% → layer-to-layer slip → scratches | Winding mechanics |
| MD draw ratio (BOPET) | Typically 3.0-3.8:1 | Film process |
| TD draw ratio (BOPET) | Typically 3.5-4.5:1 | Film process |

**Key Relationships:**
- Melt temperature → viscosity → thickness uniformity
- MD zone temperature profile → stretching ratio uniformity → thickness profile
- Die gap ↔ thickness; line speed ↔ cooling rate ↔ crystallinity
- Extruder screw speed ↔ melt pressure ↔ throughput
- MD temperature stability → dimensional consistency → winding quality

**Common Defect Physics:**
- **Film points / gel spots**: Thermal degradation products (cross-linked gel, oligomer crystals), contaminants, or unmelted resin
- **Oligomer spots**: Cyclic trimer migration to surface during stretching. Rate increases with temperature and residence time
- **Bubbles**: Moisture vaporization in melt (>260°C water → steam expansion). Insufficient vacuum degassing or wet raw material
- **Melt spots / flow marks**: Non-uniform melt temperature at die exit, uneven cooling at casting roll
- **Scratches**: Layer-to-layer relative motion during winding. Driven by tension variation from thickness non-uniformity
- **Dust/particulates**: Multi-source — thermal degradation residue, equipment wear particles, environmental contamination

**Diagnostic Considerations:**
- PET degradation at MD temperatures (75-83°C) is NEGLIGIBLE over 9-day observation windows. The Arrhenius factor between 280°C (extrusion) and 80°C (MD stretching) is enormous (~10^20 difference in rate)
- Claims that 1-2°C MD temperature variation causes detectable thermal degradation within days are physically implausible
- Temperature fluctuations affect film MECHANICALLY (via stretching ratio), not CHEMICALLY (via degradation), at MD temperatures
- Oligomer and film_points co-occurrence (high r) can indicate shared origin at the EXTRUDER (280°C), not at the MD section (80°C)
- Product grade changes are the #1 confounder in film production — different products have different temperature setpoints AND different defect baselines

### Extrusion Processes (General)

**Signals**: melt temperature, melt pressure, screw speed, line speed, thickness/width
**Common issues**: die buildup, screw wear, temperature instability, moisture contamination

**Quantitative Physics:**

| Relationship | Rule of Thumb |
|-------------|---------------|
| Melt viscosity vs temperature | ~2-3% decrease per °C for most thermoplastics |
| Screw wear effect | 0.1mm clearance increase → 5-10% throughput loss |
| Die pressure vs throughput | Approximately linear for a given die gap |
| Moisture effect | 0.01% moisture → visible surface defects in most polymers |

**Key Relationships:**
- melt temp ↔ viscosity ↔ thickness
- screw speed ↔ throughput ↔ pressure

### Coating Processes

**Signals**: coating weight, line speed, bath temperature, viscosity, gap
**Common issues**: streaking, uneven coating, drying defects
**Key Relationships:**
- line speed ↔ coating weight (inverse, ~1/speed for knife coating)
- viscosity ↔ temperature (exponential, ~2-3% per °C)

### Reactor Processes

**Signals**: temperature, pressure, flow rates, concentration, agitation
**Common issues**: temperature runaway, pressure excursions, contamination
**Key Relationships:**
- feed rate ↔ temperature; cooling ↔ reaction rate; pressure ↔ conversion
- Reaction rate doubles per 10°C (typical Arrhenius)

### Combustion Processes

**Signals**: temperature, O2, CO, NOx, fuel flow, air flow, pressure
**Common issues**: incomplete combustion, flame instability, emissions exceedance
**Key Relationships:**
- air/fuel ratio ↔ combustion efficiency; temperature ↔ NOx (exponential, thermal NOx)

### Rotary Equipment (pumps, compressors, fans)

**Signals**: vibration, temperature, speed, load, current
**Common issues**: bearing wear, imbalance, misalignment, resonance

**Quantitative Physics:**

| Relationship | Formula/Rule |
|-------------|-------------|
| Bearing fault frequencies | BPFO = (N/2) × RPM/60 × (1 - Bd/Pd × cos(φ)); BPFI = (N/2) × RPM/60 × (1 + Bd/Pd × cos(φ)) |
| Vibration severity (ISO 10816) | Class I (small) < 1.4 mm/s; Class II (medium) < 2.8 mm/s; Class III (large) < 4.5 mm/s RMS |
| Imbalance frequency | 1× running speed |
| Misalignment | 2× running speed dominant |
| Bearing wear trend | Exponential growth after initiation, ~2-5× over weeks |

---

## Common Variable Classification Patterns

### Inspection/Quality Signals
- Thickness, weight, width, dimensional measurements
- Optical properties (haze, clarity, gloss)
- Surface quality measurements (roughness, defect count)
- Chemical composition, IV (intrinsic viscosity)
- Mechanical properties (tensile strength, elongation)

### Process Parameters
- Temperature (zone, ambient, product, melt)
- Pressure (absolute, differential, vacuum)
- Flow rate (mass, volumetric)
- Speed (line, motor, pump, screw)
- Position (die gap, roll gap)
- Power/current (heater, motor)

### Control Variables
- Valve positions / openings
- Heater power / duty cycle
- Pump speed / frequency
- Setpoint values
- PID output (OP) values

### Critical Confounders (ALWAYS check)
- Product grade / recipe changes (different setpoints + different defect baselines)
- Shift / operator changes
- Raw material batch changes (moisture content, IV, particle size)
- Ambient conditions (temperature, humidity — especially for hygroscopic materials)
- Maintenance events (cleaning, part replacement)
- Equipment warm-up / start-up transients

---

## Common Diagnostic Patterns

### Sudden Step Change
- **Likely causes**: Control action, setpoint change, equipment switching, grade change
- **Check**: Control variables, event logs, product grade column
- **Physics**: Step changes are almost always OPERATIONAL, not physical degradation

### Gradual Drift
- **Likely causes**: Fouling, wear, slow degradation, environmental change
- **Check**: Trends, correlated slow variables, maintenance history
- **Physics**: Physical degradation (wear, fouling) produces monotonic drifts over days-to-months

### Oscillation
- **Likely causes**: Controller tuning, mechanical looseness, flow instability
- **Check**: Control loop performance, frequency analysis, PID parameters
- **Physics**: Oscillation frequency matches the controller integral time or mechanical resonance

### Spike
- **Likely causes**: Transient disturbance, measurement noise, valve cycling, grade change transition
- **Check**: Duration, recovery pattern, simultaneous events
- **Physics**: Spikes lasting < 3× sampling interval may be measurement artifacts

### Multi-Variable Cascade
- **Pattern**: One variable deviates → others follow in sequence
- **Analysis**: Identify the leader (earliest change), map the cascade
- **Key**: Temporal ordering is critical — and data MUST be time-sorted to determine ordering

---

## Statistical Thresholds Reference

| Metric | Typical Threshold | Notes |
|--------|------------------|-------|
| Z-score anomaly | \|z\| > 3 | Single variable |
| IQR outlier | 1.5 × IQR from Q1/Q3 | Robust to distribution |
| Pearson correlation | \|r\| > 0.7 strong, 0.3-0.7 moderate | Assumes linearity, sensitive to outliers |
| Spearman correlation | \|ρ\| > 0.7 strong, 0.3-0.7 moderate | Robust to outliers, captures monotonic |
| Detrended r attenuation | > 50% → trend-confounded | Always detrend key correlations |
| Subgroup r reversal | Different sign from full r → Simpson's Paradox | Always stratify by product/grade |
| Pearson-Spearman divergence | > 0.15 → outlier influence | Prefer Spearman for skewed data |
| CCF isolated spike | Single high lag with zero neighbors → artifact | Check data sorting immediately |
| Bonferroni threshold | α / N_tests | Controls family-wise error rate |
| Expected false positives | N_tests × α | At α=0.05, ~5% of tests "significant" by chance |
| Sample size for stratification | n > 20 per subgroup | Below this, stratified analysis unreliable |
| Lag window consistency | ≥ 2 adjacent lags with same-sign r > 0.3×\|best_r\| | Single-spike lags are red flags |

---

## Statistical Pitfalls Reference

### Pitfall 1: Sorting Artifacts in Lag Analysis
**Symptom**: Strong lag correlation (r > 0.7) at a specific non-zero lag
**Root cause**: Data sorted by batch_id or product, not by time. Adjacent rows share similar values for reasons unrelated to time
**Detection**: Verify `time_sorted == true`. Re-compute CCF after sorting by time. Check for isolated spike pattern
**Impact**: ALL lag-based causal claims are invalid. This is the most common fatal error in industrial diagnostics.

### Pitfall 2: Simpson's Paradox
**Symptom**: Correlation holds in aggregate but reverses or disappears within subgroups
**Root cause**: Product/grade switching. Different products have different setpoints AND different defect baselines
**Detection**: Stratified correlation analysis. Flag when dominant subgroup r has opposite sign from full r
**Impact**: The aggregate correlation is not causal. Confidence must be reduced by 20-30 points.

### Pitfall 3: Time-Trend Confounding
**Symptom**: Moderate correlation (r ≈ 0.3-0.5) between two variables that both drift over time
**Root cause**: Both variables share a common time trend (e.g., equipment slowly degrading, season changing)
**Detection**: Linear detrending. If detrended r << raw r, the correlation is trend-driven
**Impact**: The variables are correlated because they share a clock, not because they share physics

### Pitfall 4: Outlier-Driven Correlation
**Symptom**: Pearson r is high, but Spearman r is much lower
**Root cause**: A few extreme batches dominate the Pearson calculation
**Detection**: Spearman vs Pearson comparison. IQR-based outlier removal and recalculation
**Impact**: The correlation may not generalize to normal operating conditions

### Pitfall 5: Multiple Testing (Look-Elsewhere Effect)
**Symptom**: Several "significant" correlations at p < 0.05 among many tests
**Root cause**: With 44 parameters × 6 defects = 264 tests, ~13 "significant" results expected by chance at α=0.05
**Detection**: Bonferroni correction. Count nominally significant vs expected false positives
**Impact**: The 5th-strongest "significant" correlation may be pure chance

### Pitfall 6: Parameter Physical Meaning Unknown
**Symptom**: Statistical evidence for parameter-defect relationship but parameter's physical role is unknown
**Root cause**: Proprietary parameter names (W1C88, F_PS002) without documentation
**Detection**: Check if ontology contains physical_meaning field for the parameter
**Impact**: The mechanism interpretation is speculative regardless of statistical evidence strength

---

## Units Reference

| Quantity | SI Unit | Common Alternatives |
|----------|---------|-------------------|
| Temperature | K | °C, °F |
| Pressure | Pa | kPa, MPa, bar, psi, mbar |
| Flow | m³/s | L/min, m³/h, GPM |
| Speed | m/s | RPM, mm/min, m/min |
| Thickness | m | μm, mm, mil |
| Weight/Area | kg/m² | g/m², gsm |
| Force | N | kN, kgf, lbf |
| Vibration | m/s² | mm/s, g |
| Current | A | mA, kA |
| Power | W | kW, MW |
| Viscosity | Pa·s | Poise, cP |
