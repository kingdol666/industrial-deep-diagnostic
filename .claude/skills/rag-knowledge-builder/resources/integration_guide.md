# RAG Knowledge Builder — Integration Guide

> 消费者 skill 如何调用本 skill 获取领域本体。

## Integration Pattern: Skill-to-Skill Invocation

```
Skill({
  skill: "rag-knowledge-builder",
  args: "domain='<free-text>' target_concepts='<csv>' related_concepts='<csv>' context_dimensions='<csv>' run_dir='<path>' interaction_mode='auto'"
})
```

| Parameter | Required | Source in consumer skill | Example |
|-----------|:--------:|--------------------------|---------|
| `domain` | Yes | Domain description or auto-constructed from column names | `domain='biaxial PET film stretching with thickness control'` |
| `target_concepts` | Yes | Quality target columns | `target_concepts='thickness_um,haze_pct'` |
| `related_concepts` | Yes | Numeric predictors minus targets | `related_concepts='mdo_temp_C,tdo_temp_C,line_speed_m_min'` |
| `context_dimensions` | Yes | Categorical columns | `context_dimensions='product_grade,material_batch'` |
| `run_dir` | No | Pipeline run directory | `run_dir='/path/to/workspace/runs/20260602_xxx'` |
| `interaction_mode` | No | Default `auto` | `interaction_mode='auto'` |

## Files Exchanged

| From RAG Builder (write) | → | To Consumer Skill (read) | Purpose |
|--------------------------|---|--------------------------|---------|
| `rag_ontology_draft.json` | → | `00_input/rag_ontology_draft.json` | **结构化本体** — 实体、概念字典（含精确定义、层次、术语映射）、关系图谱、约束规则、混杂因子 |
| `rag_ontology_nl_spec.md` | → | `00_input/rag_ontology_nl_spec.md` | **自然语言本体规范** — 人类可读的领域本体文档 |
| `rag_structured_data.json` | → | `00_input/rag_structured_data.json` | 机器消费模板 — 示例数据、验证规则、查询模板 |
| `rag_scored_chunks.json` | → | `00_input/rag_scored_chunks.json` | 知识块（5 维评分 + LLM 分类） |
| `rag_clarification_needed.json` | → | **MERGE INTO** `00_input/clarification_needed.json` | 语义未确定的概念 — 与消费者自己的 unknowns 合并 |
| `rag_audit_log.json` | → | `00_input/rag_audit_log.json` | 质量验证结果 + 知识追溯 |

**Critical:** RAG 写入 `rag_clarification_needed.json`。消费者 skill 必须在进入下一步前将未解决概念合并到自己的 `clarification_needed.json`。

## Ontology Output Format (v4.0)

### JSON 结构

```
rag_ontology_draft.json
├── scene: { name, domain_type, domain_summary, primary_outcomes }
├── entities[]: {
│     id, name, type, definition, role_in_domain,
│     lifecycle, interacts_with[], owns_concepts[]
│   }
├── concepts:
│   ├── target_concepts[]: {
│   │     name, definition, definition_confidence,
│   │     concept_type, broader_concept, sibling_concepts[],
│   │     distinguish_from, unit, expected_value_range,
│   │     abnormal_indicates, terminology{}
│   │   }
│   ├── related_concepts[]: { ...同上... }
│   └── context_dimensions[]: { name, definition, cardinality }
├── process_or_logic_stages[]: { id, name, order, function }
├── relationships[]: {
│     id, name, from, to, type, mechanism,
│     direction, conditions, exceptions, expected_lag,
│     knowledge_confidence
│   }
├── constraints[]: {
│     name, type, description, applies_to[]
│   }
├── confounders[]: {
│     name, type, reasoning, expected_impact
│   }
└── rag_injection_metadata: {
      chunks reviewed/accepted/rejected, match_rate,
      knowledge_gaps[], ontology_version
    }
```

### Markdown 结构

`rag_ontology_nl_spec.md` 是本体的**人类可读面**，包含：
1. 领域概述（边界、覆盖范围）
2. 核心实体（角色、生命周期、交互）
3. 概念字典（定义、层次、消歧义、术语映射）
4. 关系图谱（机制、方向、条件、例外）
5. 公理与约束
6. 混杂因子
7. 过程/逻辑阶段
8. 知识缺口
9. 构建元数据

## How Consumer Skills Use the Output

### Context Builder: Load and Map

1. Read `rag_ontology_draft.json` → 提取 `concepts.target_concepts[]` 和 `concepts.related_concepts[]`
   - `definition` → parameter 的自然语言语义
   - `expected_value_range` → plausibility bounds
   - `abnormal_indicates` → 异常诊断指引
   - `terminology` → 列名到概念名的映射
2. Read `rag_ontology_nl_spec.md` → 给 diagnostician agent 作为领域背景
3. Read `rag_structured_data.json` → validation rules + sample data + query templates
4. Read `rag_scored_chunks.json` → 交叉验证 evidence
5. Merge `rag_clarification_needed.json` into consumer's own `clarification_needed.json`

### Diagnostician: Use Ontology for Reasoning

- `relationships[]` → 因果假设库
- `constraints[]` → 物理可行性检查
- `confounders[]` → Simpson's Paradox 风险
- `terminology` → 理解数据列名

### Judge: Knowledge Quality Awareness

Read `rag_audit_log.json` to understand:
- match_rate（低 = 知识稀疏）
- LLM confidence
- Rejected chunks + reasons

### Reporter: Use NL Spec for Reports

Read `rag_ontology_nl_spec.md` for human-readable concept definitions and relationship mechanisms.

## Fallback Chain

```
1. Try: Skill("rag-knowledge-builder", ...)
   ↓ FAILED
2. Try: Pre-generated rag_ontology_draft.json in 00_input/
   ↓ NOT FOUND
3. Fallback: Build ontology from scratch (consumer's own steps)
```

RAG is an acceleration, not a hard dependency.

## First-Time Setup

```bash
# Terminal 1: Start RAG engine
cd rag-retrieval-engine && uv sync && uv run python server.py &
# → http://localhost:8765

# One-time: Build initial knowledge index
curl -X POST http://localhost:8765/index -H "Content-Type: application/json" -d '{"rebuild": false}'

# Verify
curl -s http://localhost:8765/health
```
