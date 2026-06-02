# Parameter Pattern Library v3.0

**v3.0 restructuring:** Previous version was organized by equipment (spindle_*, tool_*, bearing_*), which only worked for CNC. The new version is organized by **physical quantity** (temperature, vibration, flow, pressure, etc.), which works for ANY industrial scenario.

The LLM uses this library as PATTERNS to infer physics for any parameter name, not just those listed. When a parameter is not found here, apply the same structure from first principles:
1. Identify the physical quantity (temperature? vibration? flow?)
2. Find the governing law (Arrhenius? Fourier? Newton's? Bernoulli?)
3. Construct a causal chain (cause → mechanism → effect)
4. Define competing hypotheses (H1, H2, H3)

---

## Temperature (K, °C, °F, °R)

**Physical meaning:** A measure of the average kinetic energy of particles. Affects reaction rates (Arrhenius), phase transitions, dimensional stability, viscosity.

**Governing laws:**
- Arrhenius: k = A·exp(-Ea/RT) — reaction rate doubles per 10°C
- Heat conduction (Fourier): q = -k·dT/dx
- Heat convection (Newton's cooling): q = h·A·(T_s - T_∞)
- Thermal expansion: ΔL = α·L₀·ΔT
- Blackbody radiation: q = ε·σ·T⁴

**Synonyms to detect:** temp, temperature, T_, _T, _degC, _C, °C, K, degF, _temp

**Typical ranges (any scenario):**
| Context | Typical Range | Critical Threshold |
|---------|--------------|-------------------|
| Polymer melt (PET) | 270-290°C | >300°C → thermal degradation |
| Polymer melt (PP) | 200-280°C | >300°C → degradation |
| Polymer melt (PC) | 280-320°C | >340°C → yellowing |
| Bearing operating | 20-80°C | >90°C → accelerated wear |
| Reactor (exothermic) | 50-200°C | >ΔT_ad → runaway |
| Mold surface | 20-120°C | varies by polymer |
| Furnace | 200-1200°C | material-dependent |
| Cryogenic | -196 to 25°C | varies |
| Wafer (semiconductor) | 20-200°C | particle contamination risk at high T |
| Battery (cell) | 15-45°C | >60°C → SEI breakdown |

**Causal chain template:** T↑ → k doubles → reaction rate↑ → side product↑ → selectivity↓

**Competing hypotheses (H1/H2/H3):**
- H1: Heat source (e.g., friction, reaction) — correlates with workload
- H2: Cooling failure — T↑ but workload constant
- H3: Sensor drift — T constant in physical reality but reading drifts

---

## Vibration (mm/s, m/s², g, Hz)

**Physical meaning:** Oscillatory motion of a structure or component. Indicates imbalance, misalignment, wear, looseness, resonance, or external excitation.

**Governing laws:**
- ISO 10816-1 (vibration severity for rotating machines)
- Newton's 2nd law (F = m·a → vibration from imbalance)
- Beam vibration theory (resonance frequencies)
- Modal analysis (mode shapes)

**Synonyms to detect:** vibration, vib, accel, acc, _g, _mm_s, _ips, _Hz, _hz, oscillation, _amplitude

**Typical ranges (any scenario):**
| Context | Good | Acceptable | Unsatisfactory | Unacceptable |
|---------|------|------------|----------------|--------------|
| Rotating machine (ISO 10816) | <1.8 mm/s | 1.8-4.5 | 4.5-11.2 | >11.2 |
| Bearing housing | <2.0 mm/s RMS | 2-5 | 5-10 | >10 |
| Structural | <0.1 g | 0.1-0.5 g | 0.5-1.0 g | >1.0 g |
| Wafer handling | <0.01 g | 0.01-0.05 | 0.05-0.1 | >0.1 (particle risk) |
| Tablet/film transport | <0.5 g | 0.5-2.0 | 2.0-5.0 | >5.0 (slip/jam risk) |

**Causal chain template:** imbalance/wear → vibration↑ → tip displacement → roughness/quality↓

**Competing hypotheses:**
- H1: Bearing wear — broad-spectrum vibration↑ across frequencies
- H2: Imbalance — 1x RPM peak dominant
- H3: Misalignment — 2x RPM peak dominant
- H4: Resonance — peak at structural natural frequency
- H5: Looseness — harmonics + broadband

---

## Flow (m³/s, L/min, m³/h, GPM, kg/s)

**Physical meaning:** Volumetric or mass flow rate of a fluid (liquid, gas, slurry, powder).

**Governing laws:**
- Bernoulli: P + ½ρv² + ρgz = const (inviscid, incompressible)
- Continuity: ρ₁A₁v₁ = ρ₂A₂v₂
- Hagen-Poiseuille: ΔP = 8μLQ/(πr⁴) (laminar pipe flow)
- Darcy-Weisbach: ΔP = f·(L/D)·(ρv²/2) (turbulent pipe flow)
- Orifice: Q = Cd·A·√(2ΔP/ρ)

**Synonyms to detect:** flow, _flow, _lpm, _gpm, m3_h, _kg_s, _feed_rate, _throughput

**Typical ranges (any scenario):**
| Context | Typical Range |
|---------|---------------|
| Cooling water (industrial) | 10-500 m³/h |
| Reactor feed | 1-1000 L/min |
| Slurry (coating) | 100-300 mL/min |
| Gas feed (semiconductor) | 10-1000 sccm |
| Polymer melt (extruder) | 50-2000 kg/h |
| Oil (hydraulic) | 10-100 L/min |

**Causal chain template:** flow↑ → residence time↓ → conversion↓ OR flow↑ → heat transfer↑ → cooling↑

**Competing hypotheses:**
- H1: Pump/ compressor degradation — flow↓ with stable ΔP
- H2: Line blockage — flow↓ with ΔP↑
- H3: Sensor drift — flow constant but reading changes
- H4: Control loop off — setpoint changed

---

## Pressure (Pa, kPa, MPa, bar, psi, mbar, Torr)

**Physical meaning:** Force per unit area exerted by a fluid on its container or flow boundary.

**Governing laws:**
- Ideal gas: PV = nRT
- Hydrostatic: P = P₀ + ρgh
- Pascal's principle: pressure transmitted equally in enclosed fluid

**Synonyms to detect:** pressure, _press, _pa, _kpa, _mpa, _bar, _psi, _mbar, _torr, _vacuum, _hg

**Typical ranges (any scenario):**
| Context | Typical Range | Critical |
|---------|---------------|----------|
| Atmospheric | 101.325 kPa | n/a |
| Vacuum (PET degassing) | 20-50 mbar | >100 mbar → moisture |
| Vacuum (semiconductor) | 1e-6 to 1e-3 Pa | varies by process |
| Hydraulic | 10-35 MPa | >40 MPa → seal failure |
| Pipeline (gas) | 1-100 bar | varies |
| Reactor | 1-100 bar | safety relief threshold |
| Tire/ bladder | 0.1-1 MPa | n/a |
| Slot-die coating | 0.1-5 bar | >10 bar → die swell |

**Causal chain template:** P↑ → flow↑ (per Bernoulli) → ... OR P↑ → concentration↑ (gas) → reaction rate↑

**Competing hypotheses:**
- H1: Blockage downstream — P↑ upstream, flow↓
- H2: Pump/ compressor issue — P↓ with normal demand
- H3: Setpoint change — P↑ matches new setpoint
- H4: Sensor drift — reading vs redundant sensor

---

## Position / Displacement (mm, μm, mil)

**Physical meaning:** Linear or angular position of a moving component.

**Governing laws:**
- Kinematics: v = dx/dt, a = dv/dt
- Mechanical compliance: Δx = F/k

**Synonyms to detect:** position, _pos, _mm, _um, _mil, _gap, _offset, _clearance, _travel, _stroke, _displacement

**Typical ranges:** context-dependent; check vs. design specification

**Causal chain template:** position↑ → dimension↑ (mechanical coupling) OR position↑ → flow area↑ → flow↑

**Competing hypotheses:**
- H1: Actuator wear — position error↑ under load
- H2: Backlash — position hysteresis
- H3: Thermal expansion — position drift with T
- H4: Calibration drift — systematic offset

---

## Speed (m/s, RPM, mm/min, m/min, Hz)

**Physical meaning:** Rotational speed (RPM) or linear speed of a moving element.

**Governing laws:**
- v = ω·r (linear = angular × radius)
- Centrifugal force: F = m·ω²·r

**Synonyms to detect:** speed, _rpm, _rps, _mpm, _m_min, _m_s, _mm_min, _line_speed, _spindle_speed, _draw_speed

**Typical ranges:**
| Context | Typical Range |
|---------|---------------|
| CNC spindle | 1000-30000 RPM |
| Extruder screw | 30-300 RPM |
| Winder | 100-500 m/min |
| Film line | 100-600 m/min |
| Agitator | 50-500 RPM |
| Pump | 1000-3600 RPM |
| Compressor | 3000-15000 RPM |
| Centrifuge | 1000-15000 RPM |
| Fan | 500-3000 RPM |
| Conveyor | 1-100 m/min |

**Causal chain template:** speed↑ → centrifugal force↑ → vibration↑ OR speed↑ → residence time↓ → conversion↓

**Competing hypotheses:**
- H1: Drive/ motor issue — speed↓ under load
- H2: Load change — speed↓ matches torque↑
- H3: Setpoint change — speed follows new setpoint
- H4: Sensor (encoder) issue — reading vs tachometer

---

## Composition / Concentration (%, ppm, ppb, mol/L)

**Physical meaning:** Fraction of a component in a mixture.

**Governing laws:**
- Mass balance: dC/dt = (in - out + generation)/V
- Raoult's law: P_partial = x·P_sat
- Henry's law: P = k_H·C (gas dissolution)

**Synonyms to detect:** concentration, _conc, _ppm, _ppb, _pct, _wt, _mol, _molar, _iv, _viscosity, _moisture, _humidity, _purity, _conversion, _selectivity, _yield

**Typical ranges (any scenario):**
| Context | Typical Range |
|---------|---------------|
| PET IV (intrinsic viscosity) | 0.55-0.85 dL/g |
| Slurry solids (battery) | 50-70% |
| Moisture (dry film) | <100 ppm |
| Conversion (reactor) | 60-99% |
| Selectivity | 80-99% |
| Impurity | 1-1000 ppm |
| Purity (semiconductor chemicals) | 99.99%+ |

**Causal chain template:** concentration↑ → reaction rate↑ (per rate law) → conversion↑ OR concentration↑ → viscosity↑ → flow↓

**Competing hypotheses:**
- H1: Feed variation — concentration tracks feed lot
- H2: Reaction selectivity shift — concentration changes with T or residence time
- H3: Sensor calibration — concentration constant but reading drifts
- H4: Sampling issue — concentration varies with sampling location

---

## Electrical (V, A, W, Hz, Ω)

**Physical meaning:** Voltage, current, power, frequency, resistance in electrical systems.

**Governing laws:**
- Ohm's law: V = I·R
- Power: P = V·I = I²R
- AC: V(t) = V_peak·sin(ωt)

**Synonyms to detect:** voltage, _V, _volt, current, _A, _amp, _I, power, _W, _watt, _kW, frequency, _Hz, _hz, resistance, _ohm, _Ω, _power_factor, _pf

**Typical ranges:**
| Context | Typical Range |
|---------|---------------|
| Industrial AC | 380-480 V, 50/60 Hz |
| DC control | 5-24 V |
| Motor (large) | 100-1000 kW |
| Heater | 1-100 kW |
| Semiconductor equipment | 208 V, 60 Hz |

**Causal chain template:** V↓ → motor torque↓ → speed↓ → flow↓ OR I↑ → P_loss↑ → T↑ → thermal stress

**Competing hypotheses:**
- H1: Load change — I↑ matches mechanical demand
- H2: Supply instability — V fluctuates
- H3: Component failure (winding short) — I↑, V↓
- H4: Sensor (CT/PT) calibration

---

## How to Use This Library (LLM instructions)

1. **Detect physical quantity from column name** using the synonym patterns above.
2. **Apply the governing law** to construct a causal chain.
3. **Identify competing hypotheses** from the typical H1/H2/H3/H4 patterns.
4. **Use typical ranges** for validation rule generation.
5. **Combine with scenario-specific knowledge** from `process_knowledge_base.md` to refine the chain.

**Anti-pattern:** Do NOT use this library to inject a specific scenario's equipment. This library describes **generic physics patterns** that apply to any scenario. Equipment identification is done by the LLM in the ontology-construction-agent.
