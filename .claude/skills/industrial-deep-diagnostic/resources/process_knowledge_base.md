# Industrial Process Knowledge Base Reference

This document provides a quick-reference knowledge base for common industrial diagnostic scenarios. It is NOT a substitute for domain-specific research — always verify with user-provided references and actual data.

## Common Industrial Process Types

### Extrusion Processes
- **Signals**: melt temperature, melt pressure, screw speed, line speed, thickness/width
- **Common issues**: die buildup, screw wear, temperature instability, moisture contamination
- **Key relationships**: melt temp ↔ viscosity ↔ thickness; screw speed ↔ throughput ↔ pressure

### Coating Processes
- **Signals**: coating weight, line speed, bath temperature, viscosity, gap
- **Common issues**: streaking, uneven coating, drying defects
- **Key relationships**: line speed ↔ coating weight; viscosity ↔ temperature

### Film Production (BOPET, BOPP, etc.)
- **Signals**: thickness, optical properties, temperature profile, speed, tension
- **Common issues**: thickness variation, haze, optical defects, wrinkles
- **Key relationships**: die gap ↔ thickness; line speed ↔ cooling rate ↔ crystallinity

### Reactor Processes
- **Signals**: temperature, pressure, flow rates, concentration, agitation
- **Common issues**: temperature runaway, pressure excursions, contamination
- **Key relationships**: feed rate ↔ temperature; cooling ↔ reaction rate; pressure ↔ conversion

### Combustion Processes
- **Signals**: temperature, O2, CO, NOx, fuel flow, air flow, pressure
- **Common issues**: incomplete combustion, flame instability, emissions exceedance
- **Key relationships**: air/fuel ratio ↔ combustion efficiency; temperature ↔ NOx

### Rotary Equipment
- **Signals**: vibration, temperature, speed, load, current
- **Common issues**: bearing wear, imbalance, misalignment, resonance
- **Key relationships**: vibration amplitude ↔ wear; temperature ↔ friction; load ↔ current

## Common Variable Classification Patterns

### Inspection/Quality Signals
- Thickness, weight, width, dimensional measurements
- Optical properties (haze, clarity, gloss)
- Surface quality measurements
- Chemical composition
- Mechanical properties

### Process Parameters
- Temperature (zone, ambient, product)
- Pressure (absolute, differential)
- Flow rate (mass, volumetric)
- Speed (line, motor, pump)
- Level (tank, reactor)
- Concentration / pH / conductivity

### Control Variables
- Valve positions / openings
- Heater power / duty cycle
- Pump speed / frequency
- Setpoint values
- Mode selectors

### Events
- Batch start/stop
- Product changes
- Equipment on/off
- Alarm triggers
- Manual interventions

## Common Diagnostic Patterns

### Sudden Step Change
- Likely causes: control action, setpoint change, equipment switching
- Check: control variable changes, event logs, mode changes

### Gradual Drift
- Likely causes: fouling, wear, slow degradation, environmental change
- Check: trends, correlated slow variables, maintenance history

### Oscillation
- Likely causes: controller tuning, mechanical looseness, flow instability
- Check: control loop performance, frequency analysis

### Spike
- Likely causes: transient disturbance, measurement noise, valve cycling
- Check: duration, recovery pattern, simultaneous events

### Multi-Variable Cascade
- Pattern: one variable deviates → others follow
- Analysis: identify the leader (earliest change), map the cascade
- Key: temporal ordering is critical

## Statistical Thresholds Reference

| Metric | Typical Threshold | Notes |
|--------|------------------|-------|
| Z-score anomaly | \|z\| > 3 | Single variable |
| IQR outlier | 1.5 × IQR from Q1/Q3 | Robust to distribution |
| Correlation strength | \|r\| > 0.7 strong, 0.3-0.7 moderate | Pearson |
| Change point | p < 0.05 | Depends on algorithm |
| Granger causality | p < 0.05 | Requires sufficient data |

## Units Reference

| Quantity | SI Unit | Common Alternatives |
|----------|---------|-------------------|
| Temperature | K | °C, °F |
| Pressure | Pa | kPa, MPa, bar, psi |
| Flow | m³/s | L/min, m³/h, GPM |
| Speed | m/s | RPM, mm/min |
| Thickness | m | μm, mm, mil |
| Weight/Area | kg/m² | g/m², gsm |
| Force | N | kN, kgf, lbf |
| Vibration | m/s² | mm/s, g |
| Current | A | mA, kA |
| Power | W | kW, MW |
