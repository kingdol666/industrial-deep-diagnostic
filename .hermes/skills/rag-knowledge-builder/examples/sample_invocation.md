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
| `rag_ontology_draft.json` | 结构化本体 — 实体、概念字典（含精确定义、层次、术语映射）、关系图谱、约束规则、混杂因子 |
| `rag_ontology_nl_spec.md` | 自然语言本体规范 — 领域概述 + 概念字典 + 关系图谱（人类可读） |
| `rag_structured_data.json` | 机器消费模板 — 示例数据、验证规则、查询模板、术语索引 |
| `rag_scored_chunks.json` | 知识块（5 维评分 + LLM 分类） |
| `rag_audit_log.json` | 8 维质量验证结果 |
| `rag_clarification_needed.json` | 语义未确定的概念（如有） |

Typical results:
- 7-12 relationships with mechanism descriptions and conditions
- 5-9 concept definitions with hierarchy and terminology mapping
- 3-6 constraints (hard/soft/rules)
- 2-4 confounders with reasoning
- Match rate typically 60-100% for domains covered in the KB
