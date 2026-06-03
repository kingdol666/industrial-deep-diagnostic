---
name: cnc-spindle-wear-diagnostic-insights
description: Key diagnostic patterns from CNC spindle wear evaluation — tool_age vs vibration dominance, thermal expansion confirmation, Simpson's paradox in feed/speed
metadata:
  type: project
---

# CNC Spindle Wear Evaluation — Key Diagnostic Patterns

**Run:** `202606031625563_eval_cnc_spindle_wear`
**Date analyzed:** 2026-06-04

## Five Discrepancy Signals Found

1. **TOOL_AGE_WEAK** — tool_age_parts correlates weakly with surface roughness (r=0.216 vs expected >0.7). Vibration is the dominant driver (r=0.969). T001 vs T005 at same tool_age (0-149) yield 3.5x Ra difference (0.78 vs 2.70 um). This is the most counterintuitive and diagnostically valuable finding.

2. **VIBRATION_DOMINANCE** — Spindle vibration (not tool wear) is the primary driver of surface roughness degradation. Second-half mean vibration 5.36 mm/s is in ISO 10816 Zone C (unsatisfactory).

3. **NO_THERMAL_EQUILIBRIUM** — Spindle temperature rises monotonically 31->55 degC over the day with no thermal plateau. Bearing friction heat exceeds cooling capacity.

4. **SIMPSONS_PARADOX_CANDIDATE** — Both spindle_speed_rpm and feed_rate_mm_min show strong negative correlations with Ra (r=-0.94, r=-0.90), contradicting physics predictions. Likely reversed by material confounding (SS304 low speed/feed + high Ra vs Al alloys high speed/feed + low Ra).

5. **OBSERVED_SLOPE_BIAS** — Measured Delta_thermal_deviation / Delta_temp = 0.0017 mm/degC vs theoretical 0.00345 mm/degC (assuming 300mm steel spindle). Possible spindle length mismatch or partial thermal compensation.

## Stage 2 Validation Queue (9 items for Data Processor)

Priority HIGH items: tool_age stratified by tool_id, Simpson's paradox test for feed/speed, vibration-temperature Granger causality, thermal expansion slope verification, T001 vs T005 root cause, time confound detrending.

**Why:** tool_age effects are real but MASKED by vibration. Stratification by tool_id will reveal the within-tool wear trend. The vibration-temperature co-variation (r=0.954) needs directional testing.

## Ontology Reference

- Ontology file: `01_ontology/ontology.json` (schema-validated, 0 errors)
- Knowledge extracted from: `parameter_to_physics.json` (CNC/rotating machinery coverage) + 5 web searches
- RAG was unavailable (engine not running) — fallback to first-principles + built-in pattern library
