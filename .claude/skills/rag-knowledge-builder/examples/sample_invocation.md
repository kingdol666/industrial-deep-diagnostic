# Sample Invocation

Example of how `industrial-deep-diagnostic` calls this skill:

```
Skill({
  skill: "rag-knowledge-builder",
  args: "scenario='CNC machining spindle bearing degradation' target_cols='surface_roughness_Ra_um,thermal_deviation_mm' param_cols='spindle_vibration_mm_s,spindle_temp_C,tool_age_parts,spindle_speed_rpm,feed_rate_mm_min' group_cols='material,tool_id' run_dir='/workspace/diagnostic-runs/2026_cnc_demo' interaction_mode='auto'"
})
```

This produces `$run_dir/00_input/rag_ontology_draft.json` with:
- 7-9 causal relationships with governing equations
- 5-7 parameter meanings (classified as target/predictor/control)
- 2-4 known confounders
- Match rate typically 85-100% for columns present in the KB
