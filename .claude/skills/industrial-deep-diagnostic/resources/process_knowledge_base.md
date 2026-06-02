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

---

## Additional Process Types (v3.0 expansion)

### Injection Molding

**Signals**: melt_temp, mold_temp, injection_pressure, hold_pressure, cooling_time, cycle_time, part_weight, dimension
**Common issues**: short shot, flash, sink marks, warpage, weld lines, voids, birefringence, dimensional drift

**Quantitative Physics:**

| Relationship | Formula/Rule of Thumb | Source |
|-------------|----------------------|--------|
| Polymer melt temp (PP) | 200-280°C | Injection molding handbook |
| Polymer melt temp (ABS) | 220-260°C | Injection molding handbook |
| Polymer melt temp (PC) | 280-320°C | Injection molding handbook |
| Mold surface temp (PP) | 20-80°C | Cooling physics |
| Mold surface temp (PC) | 80-120°C | Cooling physics |
| Mold surface temp (PMMA) | 60-90°C | Cooling physics |
| Injection pressure | 50-150 MPa typical | Molding machinery |
| Hold-to-injection pressure ratio | 0.4-0.8 | PVT behavior |
| Cooling time (1mm wall, PP) | ~5-10s | Heat diffusion |
| Cooling time scaling | t_cool ∝ (wall_thickness)² / thermal_diffusivity | Fourier heat conduction |
| Shear rate at gate | 10³-10⁵ s⁻¹ | Rheology |
| Shear thinning (PP) | Viscosity drops 1-2 decades over shear rate range | Carreau model |
| Crystallinity vs mold temp | Higher mold temp → higher crystallinity → more shrinkage | Polymer physics |
| Part shrinkage (semi-crystalline) | 1-3% typical | PVT data |
| Part shrinkage (amorphous) | 0.3-0.7% typical | PVT data |
| Weld line strength reduction | 30-80% of bulk strength | Knit-line mechanics |
| Birefringence indicator | Frozen-in orientation from flow; correlates with residual stress | Polymer optics |
| Cycle time breakdown | Injection (5%) + Hold (20%) + Cooling (60%) + Ejection (15%) | Industry standard |

**Confounders**: material_grade (different MFI → different fill behavior), masterbatch_lot (color/additive concentration affects MFI), machine_id (screw wear → shear history differs), ambient_humidity (PA6 hydrolysis)

**Equipment**: injection_molding_machine (clamp unit, injection unit, mold), mold (cavities, runners, gates, cooling_channels), hopper/dryer, granulator, temperature_control_unit (TCU), robot_arm

**Common Defect Causal Chains:**
- `mold_temp_C ↓ → cooling_rate ↑ → crystallinity ↓ → warpage ↓` (good for tight tolerance)
- `mold_temp_C ↓ → skin_layer cools too fast → frozen orientation high → birefringence ↑ → optical distortion`
- `melt_temp_C ↑ → viscosity ↓ → fill easier → short_shot risk ↓` BUT `→ IV degradation ↑ → mechanical strength ↓`
- `hold_pressure ↓ → cavity packing insufficient → sink_marks ↑ + voids ↑`
- `cooling_time ↓ → ejection temp too high → part warpage ↑`

---

### Chemical Reactor (CSTR/PFR)

**Signals**: reactor_temp, jacket_temp, feed_flow, product_flow, agitator_RPM, agitator_torque, agitator_power, pressure, conversion, selectivity, MW_dist_moments
**Common issues**: conversion drift, selectivity loss, runaway reaction, fouling, catalyst deactivation, off-spec product

**Quantitative Physics:**

| Relationship | Formula/Rule of Thumb | Source |
|-------------|----------------------|--------|
| Arrhenius rate constant | k = A·exp(-Ea/RT) | Reaction kinetics |
| Typical Ea (chemical reactions) | 50-200 kJ/mol | Reaction engineering |
| Reaction rate temperature sensitivity | 10°C increase → 2-3x rate (for typical Ea) | Arrhenius |
| CSTR steady-state design eqn | τ = (C_A0 - C_A) / (-r_A) | Levenspiel |
| PFR design eqn | τ = ∫ dX / (-r_A / C_A0) | Levenspiel |
| Damköhler number | Da = reaction_rate / flow_rate | Reaction engineering |
| Adiabatic temperature rise | ΔT_ad = -ΔH_rxn · C_A0 / (ρ·Cp) | Energy balance |
| Heat removal limit (CSTR) | Q_max = UA · (T_jacket - T_reactor) | Energy balance |
| Runaway criterion (Semenov) | Heat generation > heat removal at T_onset | Thermal safety |
| Mass transfer (gas-liquid) | k_L · a · (C* - C_L) | Two-film theory |
| Mixing time (Rushton turbine) | t_mix ∝ (D/T)^(-2) · N^(-1) | Mixing literature |
| Power number (Rushton) | Np ≈ 5-6 in turbulent regime | Mixing literature |
| Catalyst deactivation models | 1st order, 2nd order, exponential, S-shaped | Catalyst engineering |
| Selectivity vs conversion | S = k2·C_B / (k1·C_A) for parallel reactions | Kinetics |
| Fouling resistance growth | R_f(t) = R_f0 · (1 + α·t) for linear | Heat exchanger fouling |
| Cooling water ΔT | ΔT_CW = Q / (m_dot · Cp_water) | Energy balance |
| Jacket response time | τ_jacket = m_jacket · Cp_jacket / (UA + m_dot·Cp) | Control dynamics |

**Confounders**: catalyst_batch_id (activity varies ±10%), feed_composition (impurities affect kinetics), ambient_temp (affects cooling water inlet), operator (different loading procedures)

**Equipment**: reactor_vessel (CSTR or PFR), agitator/mixer (Rushton, helical, pitched-blade), jacket (for heat transfer), condenser, feed_tank, product_tank, pump, heat_exchanger, instrumentation (T, P, pH, level)

**Common Defect Causal Chains:**
- `reactor_temp ↑ 5°C → k doubles → conversion ↑ 50%` (for typical Ea) BUT `→ selectivity ↓ → side product ↑`
- `agitator_RPM ↓ → mixing time ↑ → hot spots → runaway risk ↑`
- `catalyst_age ↑ → activity ↓ → conversion ↓ at same conditions`
- `feed_flow ↑ → residence time ↓ → conversion ↓`
- `fouling ↑ (R_f) → heat_transfer_coeff ↓ → temperature control degrades → conversion drift`

---

### Lithium-Ion Battery Manufacturing (Electrode Coating)

**Signals**: slurry_solids_pct, coating_thickness_um, coating_weight_gsm, oven_temp_zones, line_speed, calendaring_pressure, electrode_density_gcc, moisture_ppm, NMP_ppm
**Common issues**: coating defects (streaks, pinholes, agglomerates), thickness variation, density variation, adhesion failure, calendar defects, moisture-induced capacity loss

**Quantitative Physics:**

| Relationship | Formula/Rule of Thumb | Source |
|-------------|----------------------|--------|
| Slurry solids (NMC cathode) | 50-70% | Slurry rheology |
| Slurry viscosity target | 1000-10000 cP (Brookfield) | Coating rheology |
| Coating speed (slot-die) | 10-100 m/min | Coating engineering |
| Wet film thickness to dry | t_dry = t_wet · solids_pct / (1 - solvent_pct) | Mass balance |
| Coating weight (NMC single side) | 100-250 gsm | Cell design |
| Electrode density (NMC) | 3.4-3.7 g/cc (calendared) | Cell design |
| Porosity target | 20-35% | Cell design |
| Active material:binder:carbon (NMC) | 90-95 : 3-7 : 2-5 | Cathode formulation |
| Drying oven zones | 3-5 zones; gradient T profile (60→120°C) | Drying kinetics |
| NMP evaporation rate | Function of T, airflow, vapor pressure | Evaporation physics |
| Moisture spec (dry room) | < -40°C dew point (≈100 ppm) | Battery safety |
| Calendar pressure | 50-200 tons | Electrode calendering |
| Electrode compression (porosity reduction) | porosity = 1 - (ρ_electrode / ρ_true) | Composite physics |
| Adhesion strength (peel test) | > 30 N/m (cathode) | Cell design |
| Thickness uniformity | ±2-3% (good), ±5% (poor) | Coating physics |
| Edge bead control | Bead width < 5 mm typical | Coating engineering |
| Vacuum drying (after coating) | 120°C × 24h, < 100 Pa | Drying standard |
| Electrolyte filling (cell assembly) | 1.0-1.5x pore volume | Cell design |

**Confounders**: active_material_lot (different surface area → different binder demand), binder_lot (different MW → different viscosity), solvent_batch (NMP water content affects drying), ambient_humidity (slurry pickup moisture), operator (coating head alignment)

**Equipment**: slurry_mixer (planetary, centrifugal), coating_machine (slot-die, comma, doctor-blade), drying_oven (3-5 zones, IR + convection), calendar (roll press), slitter, vacuum_dryer, dry_room (NMP-recovery, dehumidification)

**Common Defect Causal Chains:**
- `slurry_solids_pct ↑ → viscosity ↑ → coating defects ↑ (streaks, pinholes)`
- `oven_temp ↑ → solvent_evaporation_rate ↑ → skin formation → trapped solvent → blistering`
- `calendaring_pressure ↑ → porosity ↓ → energy_density ↑ BUT → particle cracking → cycle_life ↓`
- `coating_speed ↑ → wet film uniformity ↓ → thickness variation ↑`
- `moisture ↑ → Li-proton exchange → capacity_loss ↑ + gassing`
- `NMP_residual ↑ → SEI instability → cycle_life ↓`

---

### Semiconductor (CMP — Chemical Mechanical Polishing)

**Signals**: slurry_flow, platen_RPM, carrier_RPM, down_force, back-pressure, polishing_time, removal_rate_nm_min, wafer_temperature, defect_count, non-uniformity_pct
**Common issues**: dishing, erosion, microscratches, residue, non-uniform removal, endpoint detection failure, slurry starvation

**Quantitative Physics:**

| Relationship | Formula/Rule of Thumb | Source |
|-------------|----------------------|--------|
| Preston's equation | RR = K_p · P · v (P=pressure, v=relative velocity) | CMP physics |
| Preston's coefficient (Cu/SiO2) | K_p ≈ 7e-14 to 5e-13 (units dependent) | CMP literature |
| Typical removal rate (Cu) | 2000-5000 Å/min | CMP engineering |
| Typical removal rate (SiO2) | 1500-3000 Å/min | CMP engineering |
| Typical removal rate (W) | 2000-4000 Å/min | CMP engineering |
| Platen speed | 30-120 RPM | CMP engineering |
| Carrier speed | 30-120 RPM (independent of platen) | CMP engineering |
| Down force | 2-8 psi | CMP engineering |
| Slurry flow rate | 100-300 mL/min | CMP engineering |
| Wafer-to-pad relative velocity | v = π · (R_platen + R_carrier) · (RPM_platen + RPM_carrier) / 60 | Kinematics |
| Dishing (Cu over SiO2) | Function of pattern density; 100-500 Å typical | CMP literature |
| Erosion (dielectric) | Function of pattern density | CMP literature |
| Selectivity Cu:SiO2 | 1:1 to 4:1 depending on slurry | Slurry chemistry |
| Selectivity W:SiO2 | High (tungsten-selective slurries exist) | Slurry chemistry |
| Defect adders | Particles from slurry, pad glazing, handling | CMP literature |
| Pad conditioning | Diamond disc; 5-20 RPM; restores pad asperities | CMP engineering |
| Slurry temperature effect | 1°C → 1-2% RR change | Chemical kinetics |
| Slurry pH (Cu slurry) | 6-10 (oxidizer + complexing agent) | Slurry chemistry |
| Endpoint detection (optical) | Interference signal at fixed wavelength | Metrology |

**Confounders**: slurry_lot (particle size distribution varies), pad_age (asperity density changes), wafer_lot (film thickness variations), tool_id (chuck flatness differs), ambient_temp (slurry temp drift)

**Equipment**: polisher (platen, carrier, slurry delivery), pad (polyurethane, with conditioner), slurry_system (mixing, distribution, filtration), cleaner (post-CMP brush scrubber + chemistry), metrology (in-situ optical, ex-situ profilometer)

**Common Defect Causal Chains:**
- `down_force ↑ → RR ↑ BUT → dishing ↑ + erosion ↑ + microscratch risk ↑`
- `platen_RPM ↑ → v ↑ → RR ↑ BUT → non_uniformity ↑ at high speeds`
- `slurry_flow ↓ → pad starvation → local RR ↓ → non_uniformity ↑`
- `pad_conditioning ↓ → pad glazing → RR ↓ + defect_count ↑`
- `slurry_temp ↑ → chemical activity ↑ → RR ↑ BUT selectivity shifts → dishing worse`
- `wafer_pressure_asymmetry → edge_fast → edge RR higher → non_uniformity ↑`

---

### Cross-Scenario Universal Physics (apply to ANY process)

| Principle | Effect | Applicable to |
|-----------|--------|---------------|
| Arrhenius | k doubles per 10°C (typical Ea) | All chemical reactions |
| Heat conduction (Fourier) | q = -k·dT/dx | All thermal processes |
| Mass conservation | Accumulation = In - Out + Generation | All processes |
| Momentum conservation | F = m·a (Newton 2nd) | All mechanical systems |
| Shear thinning | Viscosity ↓ with shear rate ↑ | All polymer processes |
| Crystallinity ↔ cooling rate | Fast cooling → low crystallinity | All semi-crystalline polymers |
| Defect propagation | Local disturbance → propagates downstream | All continuous processes |
| Mixing time vs Reynolds | Re > 10⁴ → turbulent → fast mixing | All mixing operations |
| Catalyst deactivation | Activity decays with time-on-stream | All catalytic reactions |
| Sensor drift | Reading drift over weeks/months | All processes with sensors |
