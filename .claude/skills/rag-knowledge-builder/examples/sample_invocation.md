# Sample Invocation (v4.0)

Example of how `industrial-deep-diagnostic` or any consumer skill calls this skill:

```
Skill({
  skill: "rag-knowledge-builder",
  args: "domain='CNC machining spindle bearing degradation' target_concepts='surface_roughness_Ra_um,thermal_deviation_mm' related_concepts='spindle_vibration_mm_s,spindle_temp_C,tool_age_parts,spindle_speed_rpm,feed_rate_mm_min' context_dimensions='material,tool_id' run_dir='/workspace/diagnostic-runs/2026_cnc_demo' interaction_mode='auto'"
})
```

This produces in `$run_dir/00_input/`:

| File | Content |
|------|---------|
| `rag_ontology_draft.json` | Structured ontology — entities, concept dictionary (with precise definitions, hierarchy, terminology mapping), relationship graph, constraint rules, confounders |
| `rag_ontology_nl_spec.md` | Natural-language ontology specification — domain overview + concept dictionary + relationship graph (human-readable) |
| `rag_structured_data.json` | Machine-consumable templates — example data, validation rules, query templates, terminology index |
| `rag_scored_chunks.json` | Knowledge chunks (5-dimension scoring + LLM classification) |
| `rag_audit_log.json` | 8-dimension quality verification results |
| `rag_clarification_needed.json` | Concepts whose semantics are undetermined (if any) |

Typical results:
- 7-12 relationships with mechanism descriptions and conditions
- 5-9 concept definitions with hierarchy and terminology mapping
- 3-6 constraints (hard/soft/rules)
- 2-4 confounders with reasoning
- Match rate typically 60-100% for domains covered in the KB
