---
name: parameter-to-physics-cnc-coverage
description: The parameter_to_physics.json pattern library covers CNC spindle/machining parameters — spindle_vibration, spindle_temp, tool_age, feed_rate, surface_roughness, dimensional_deviation
metadata:
  type: reference
---

The built-in `parameter_to_physics.json` at `SKILL_PATH/resources/parameter_to_physics.json` covers CNC milling/machining parameters directly:
- `spindle_vibration_mm_s` — ISO 10816-1 severity zones, bearing wear/imbalance/resonance hypotheses, quantitative tool_tip_deflection check
- `spindle_temp_C` — energy balance governing law, bearing wear vs cooling failure vs overload hypotheses
- `tool_age_parts` — Taylor tool life VT^n=C, progressive wear vs chipping vs BUE hypotheses
- `feed_rate_mm_min` — Ra=f²/(32*r_epsilon), confounding warning about Ra vs parameter adjustments
- `surface_roughness_Ra_um` — Ra formula + vibration contribution, confounding warning about feed rate variation
- `dimensional_deviation_mm` — thermal expansion ΔL=αLΔT + force deflection F/k_system

**Why:** This library eliminates the need for RAG retrieval for these specific parameters. The CNC spindle wear scenario is well-covered.

**How to apply:** When facing CNC/machining data, check parameter_to_physics.json first. Map column names by synonym matching before building ontology from scratch.
