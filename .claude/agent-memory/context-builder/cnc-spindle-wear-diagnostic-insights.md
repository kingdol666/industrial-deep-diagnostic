---
name: cnc-spindle-wear-diagnostic-insights
description: Key discrepancy patterns discovered in CNC spindle wear diagnosis across multiple runs: tool_age not dominant, vibration is, thermal no-equilibrium, Simpson's paradox candidates, confirmed S-curve defect progression
metadata:
  type: reference
---

## CNC Spindle Wear Diagnostic Insights

### Confirmed Across Runs: 202606031625563, 202606041451221, 202606081402243

### Key Discrepancy Signals Found

1. **VIBRATION_DOMINANCE** — `spindle_vibration_mm_s` vs `surface_roughness_Ra_um` r=0.99+, almost perfectly linear across ALL materials and tools. Grade A parts all have vibration <1.5mm/s, Grade C all >4.0mm/s. Vibration is the single causal bottleneck — all quality degradation passes through it.

2. **TOOL_AGE_WEAK** — Global `tool_age_parts` → quality metrics r<0.22. Vibration correlates with time index at r=0.88 but with tool_age_parts at only r=0.08. The tool sequence (T001→T019) IS a time sequence, not an independent categorical variable.

3. **NO_THERMAL_EQUILIBRIUM** — `spindle_temp_C` never plateaus: 37C day1 to 72C day30. Normal CNC spindles achieve thermal equilibrium within 1-2 hours. The continuous rise indicates thermal runaway: vibration → more friction → more heat → lubrication degradation → more friction.

4. **NEW_TOOLS_DONT_FIX** — T013-T019 start at age=0 but produce 100% Grade C parts immediately. The root cause is NOT the cutting tools but progressive spindle/cooling system degradation.

5. **S-CURVE DEFECT PROGRESSION** — Tools T001-T011: 0% defect C, T012: 11%, T013: 46%, T014: 90%, T015-T019: 100%. This S-shaped transition (no defects → rapid acceleration → saturation) is classic failure progression.

6. **COOLANT_SYSTEM_DEGRADATION** — `coolant_temp_C` rose from 22C to 32.5C. Delta T between spindle and coolant expands from 12C to 44C over the run — spindle is generating far more heat than the cooling system can remove.

7. **CUTTING_PARAMS_MATERIAL_CONFOUNDED** — spindle_speed, feed_rate have r>0.99 with material (AL7075=12000rpm/3000mm_min, SS304=8000/2000, TI6AL4V=6000/1500). All cross-material correlations with quality are Simpson's paradox candidates — material acts as the dominant confounder.

### Vibration Thresholds (mm/s)
- <1.5: A grade (all parts pass)
- 1.5-4.0: B grade (transition zone, some chatter marks appear >4mm/s)
- >4.0: C grade (100% failure, chatter marks frequent, severe dimensional deviation)

### Causal Chain Hypothesis
```
Spindle bearing/system degradation
  → continuous vibration increase (729% over dataset, no tool-change reset)
  → surface roughness directly determined by vibration (r=0.99)
  → dimensional deviation follows vibration (r=0.98)
  → when vibration exceeds ~4 mm/s threshold → regenerative chatter
  → all quality metrics fail → Grade C
```

### Material Confound Structure
Each of the 19 tools processes all 3 materials in rotation (~25 parts/material/tool):
- Material AL7075 → 12000 RPM, 3000 mm/min → 155 HV (soft)
- Material SS304 → 8000 RPM, 2000 mm/min → 208 HV (medium)
- Material TI6AL4V → 6000 RPM, 1500 mm/min → 398 HV (hard)
- depth_of_cut_mm has 4 discrete values (0.5/1.0/1.5/2.0) uniformly distributed

### Stage 2 Validation Queue
- Stratified analysis by tool_id (Simpson's paradox confirmation for tool_age)
- Change-point detection on spindle_temp and vibration (when does the acceleration start?)
- Detrended analysis to extract tool_age effect after removing time trend
- Stratified correlation by material to de-confound material effects on all process-quality relationships
- Verify if hardness_HV is 100% determined by material (perfect confound)
