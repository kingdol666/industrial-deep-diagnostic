# Physics-Based Inference Framework

> **Reference file for SKILL.md §Physics-Based Inference.** Load this when the diagnostician (Step 4) needs the full Physics Inference Ladder (L1-L5) for any parameter not in the pre-built library, or when the context-builder (Step 2) encounters unknown parameters.

## Physics-Based Inference Framework

> **For truly universal diagnosis, physics reasoning must work for ANY parameter, not just those in a pre-built library.** The `parameter_to_physics.json` file is a PATTERN LIBRARY — a collection of EXAMPLES showing the structure of physical reasoning. For parameters NOT in the library, DERIVE physics from first principles.

### The Physics Inference Ladder

For ANY parameter (known or unknown domain), climb this ladder:

#### Level 1: Physical Quantity Identification

From column name, value range, unit, and statistical signature:

| Clue | Inference |
|------|-----------|
| Column name contains: temp/TH/T, values 0-1500 | Temperature (°C or °F) |
| Column name contains: press/PS/P/PR, values 0-500 | Pressure (bar, kPa, psi) |
| Column name contains: flow/FR/FL/Q, positive values | Flow rate (volumetric or mass) |
| Column name contains: speed/RPM/SP/V, values 0-10000 | Rotational or linear speed |
| Column name contains: vib/VIB/ACC/VEL, values 0-100 | Vibration (mm/s, g, or μm) |
| Column name contains: power/PW/KW/W, positive values | Power or energy |
| Column name contains: pos/disp/gap/L, values with ± range | Position, displacement, gap |
| Column name contains: wt/mass/weight, positive values | Mass or weight |
| Column name contains: ph/COND/conc/pct/% | Chemical property (pH, conductivity, concentration) |
| Column name contains: thick/gauge/gsm/μm/mil | Dimensional (thickness, coating weight) |

If column name is opaque (e.g., "W1C88"):
- Look at value range: 0-100 → percentage? 0-10 → pressure (bar)? 20-200 → temperature?
- Look at statistical signature: step changes → setpoint? gradual drift → degradation? high-frequency noise → vibration?
- Look at correlations with known parameters: if strongly correlated with known temperature sensors → likely temperature

#### Level 2: Governing Law Selection

Once the physical quantity is identified, select the governing physical law:

| Physical Quantity | Governing Law(s) |
|-------------------|------------------|
| Temperature (any) | Energy conservation: m·Cp·dT/dt = Q̇_in − Q̇_out; Newton's law of cooling: Q̇ = h·A·ΔT; Fourier heat conduction: q̇ = −k·∇T |
| Pressure (fluid) | Bernoulli: P + ½ρv² + ρgh = constant; Darcy-Weisbach: ΔP = f·(L/D)·(ρv²/2); Ideal gas: PV = nRT |
| Flow rate | Continuity: Q = A·v; Pump affinity: Q ∝ N, ΔP ∝ N², P ∝ N³ |
| Vibration | Newton's 2nd for forced oscillator: mẍ + cẋ + kx = F(t); ISO 10816 severity zones |
| Force/Torque | Newton's 2nd: F = m·a; τ = I·α; Cutting: F = k_s·a_p·f |
| Speed (rotational) | v = π·D·N/60; Power: P = τ·ω |
| Position/Displacement | Thermal expansion: ΔL = α·L₀·ΔT; Elastic deformation: ΔL = F·L/(A·E) |
| Power/Current | P = V·I·cosφ·η (motor); P = τ·ω (mechanical) |
| Concentration/pH | Reaction rate: r = k·Cⁿ; Arrhenius: k = A·exp(−Ea/RT); pH = −log[H⁺] |
| Dimension (thickness, etc.) | Mass balance; Preston (CMP): RR = K_p·P·v; Taylor tool life: VTⁿ = C |

#### Level 3: Causal Chain Construction

Build a directed chain from parameter change → intermediate effects → quality impact:

```
Parameter deviation → [Physical mechanism 1] → Intermediate effect → [Physical mechanism 2] → Quality impact
```

Each arrow must cite a governing law from Level 2. Each mechanism must have a quantitative estimate (order-of-magnitude).

**Example — for a novel parameter "X" measuring pneumatic pressure**:
```
X↓ → [Bernoulli: reduced pressure → reduced flow velocity] → cooling air velocity↓ → [Newton's cooling: Q̇ = h·A·ΔT, h ∝ v^0.8] → heat transfer coefficient↓ → cooling rate↓ → product temperature↑ → [Arrhenius: degradation rate doubles per 10°C] → quality↓
```

#### Level 4: Magnitude Estimation

Before claiming causation, estimate whether the effect magnitude is physically plausible:

1. **Dimensional analysis**: Do the units work out? If claiming pressure (Pa) causes dimensional change (μm), what is the compliance (μm/Pa)?
2. **Order-of-magnitude check**: If the parameter changed by ΔX, what ΔY does the governing equation predict? Is the predicted ΔY within an order of magnitude of the observed ΔY?
3. **Time constant check**: The causal mechanism has a characteristic time (thermal time constant, diffusion time, wear rate). Is the observed lag consistent with this time constant?

#### Level 5: Competing Mechanism Analysis

For each causal hypothesis, identify alternative physical mechanisms that could produce the SAME data pattern:

- **Common-cause alternatives**: Could a third variable Z drive both X and Y?
- **Reverse-causation alternatives**: Could Y cause X instead of X causing Y?
- **Measurement-artifact alternatives**: Could the correlation be a sensor artifact (cross-talk, shared power supply, environmental sensitivity)?
- **Control-system alternatives**: Could the correlation be due to a control loop responding to Y by adjusting X?

### Physics Inference Documentation

When deriving physics from first principles (parameter NOT in `parameter_to_physics.json`), document as:

```json
{
  "parameter": "novel_column_name",
  "physics_source": "first_principles_inference",
  "physical_quantity": "Identified physical quantity + reasoning",
  "governing_law": "Governing equation + why it applies",
  "causal_chain": "Full chain from deviation to quality impact",
  "magnitude_check": "Order-of-magnitude calculation",
  "competing_mechanisms": ["Alternative 1", "Alternative 2"],
  "confidence": "INFERRED_PHYSICS — not pre-verified"
}
```
