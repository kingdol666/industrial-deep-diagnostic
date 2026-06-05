---
name: cnc-spindle-wear-diagnostic-insights
description: Key discrepancy patterns discovered in CNC spindle wear diagnosis: tool_age not dominant, vibration is, thermal no-equilibrium, Simpson's paradox candidates
metadata:
  type: reference
---

## CNC Spindle Wear Diagnostic Insights

### Run: 202606041451221_simulateData_full (2026-06-04)

### Key Discrepancy Signals Found

1. **VIBRATION_DOMINANCE** — `spindle_vibration_mm_s` vs `surface_roughness_Ra_um` r=0.993, almost perfectly linear. Grade A parts all have vibration <1.34mm/s, Grade C all >2.52mm/s. This is by far the strongest signal in the data.

2. **TOOL_AGE_WEAK (Simpson's paradox candidate)** — Global `tool_age_parts` → `roughness` r=0.14 (weak), but within-tool r=0.63-0.88 (strong). The contradiction is caused by time/tool_id confounding: later tools operate with a degraded spindle, masking the within-tool wear effect.

3. **NO_THERMAL_EQUILIBRIUM** — `spindle_temp_C` never plateaus: 36.8 C day1 to 71.3 C day30. Normal CNC spindles achieve thermal equilibrium within 1-2 hours. The continuous rise indicates a thermal runaway cycle (coolant temp up -> less heat removal -> bearing temp up -> lubrication degradation -> friction up -> more heat).

4. **NEW_TOOLS_DONT_FIX** — T013-T019 start at age=0 but produce Grade C parts immediately. This is the most important diagnostic signal: the root cause is NOT the cutting tools but the spindle/cooling system degradation.

5. **COOLANT_SYSTEM_DEGRADATION** — `coolant_temp_C` rose from 24.5 C to 29.6 C over 30 days (r=0.851 with day), uncorrelated with ambient temp. System-level degradation, not environmental.

6. **CUTTING_PARAMS_IRRELEVANT** — spindle_speed, feed_rate, depth_of_cut all show near-zero correlation with roughness (|r|<0.05). In a degraded spindle state, parameter adjustments cannot compensate.

### Causal Chain Hypothesis
```
Cooling system degradation → coolant temp ↑ → spindle temp ↑ (no equilibrium)
→ bearing lubrication failure → bearing wear progress → vibration ↑↑
→ surface_roughness ↑ (r=0.993) → defect grade B/C
```

### Stage 2 Validation Queue
- Stratified analysis by tool_id (Simpson's paradox confirmation)
- Change-point detection on spindle_temp (Day15 acceleration threshold)
- Detrended analysis to extract tool_age effect after removing time trend
- Lag analysis on coolant_temp to spindle_temp coupling

### Previous Run Comparison (202606031625563_eval_cnc_spindle_wear)
Consistent pattern: vibration dominance (prev r=0.969, current r=0.993), no thermal equilibrium, Simpson's paradox candidates. New finding: explicit defect grade thresholds (Grade A vib<1.3, Grade C vib>2.5 mm/s) and confirmation that new tools cannot restore quality under degraded spindle.
