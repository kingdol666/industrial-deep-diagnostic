# RAG Knowledge Builder — Integration Guide

> 消费者 skill 如何调用本 skill 获取领域本体。

## Integration Pattern: Skill-to-Skill Invocation

消费者 skill 的 context-builder 调用：

```
Skill({
  skill: "rag-knowledge-builder",
  args: "domain='<free-text>' target_concepts='<csv>' related_concepts='<csv>' context_dimensions='<csv>' run_dir='<path>' interaction_mode='auto'"
})
```

| Parameter | Required | Source in consumer skill | Example |
|-----------|:--------:|-------------------------|---------|
| `domain` | Yes | 领域描述或从列名模式自动构建 | `biaxial PET film stretching with thickness control` |
| `target_concepts` | Yes | 质量目标列 | `thickness_um,haze_pct` |
| `related_concepts` | Yes | 所有数值预测变量 | `mdo_temp_C,tdo_temp_C,line_speed_m_min` |
| `context_dimensions` | Yes | 分层的分类列 | `product_grade,material_batch` |
| `run_dir` | Yes | Pipeline 运行目录 | `/path/to/runs/20260602_xxx` |
| `interaction_mode` | No | 默认 `auto` | `auto` |

## Files Exchanged

| From RAG Builder (write) | → | To Consumer Skill (read) | Purpose |
|--------------------------|---|--------------------------|---------|
| `rag_ontology_draft.json` | → | `00_input/rag_ontology_draft.json` | **结构化本体** — 概念定义、层次、关系、约束、术语 |
| `rag_ontology_nl_spec.md` | → | `00_input/rag_ontology_nl_spec.md` | **自然语言规范** — 人类可读的本体设计文档 |
| `rag_structured_data.json` | → | `00_input/rag_structured_data.json` | 机器消费模板 — 示例、验证规则、查询模板 |
| `rag_scored_chunks.json` | → | `00_input/rag_scored_chunks.json` | 知识块（5 维评分 + 分类） |
| `rag_clarification_needed.json` | → | `00_input/clarification_needed.json` | 需要用户澄清的概念 |
| `rag_audit_log.json` | → | `00_input/rag_audit_log.json` | 质量验证结果 |

## 本体输出格式 v4 (Ontology-First)

### 结构化 JSON 输出

```
rag_ontology_draft.json
├── scene: { name, domain_type, domain_summary, primary_outcomes[] }
├── entities[]: { id, name, type, definition, lifecycle, interacts_with, owns_concepts }
├── concepts:
│   ├── target_concepts[]: { name, definition, broader_concept, sibling_concepts,
│   │     distinguish_from, terminology{...}, unit, expected_value_range,
│   │     abnormal_indicates, definition_confidence }
│   ├── related_concepts[]: { ... }
│   └── context_dimensions[]: { ... }
├── relationships[]: { id, name, from, to, type, mechanism, direction,
│     conditions, exceptions, expected_lag, knowledge_confidence }
├── constraints[]: { name, type, description, applies_to }
├── confounders[]: { name, type, reasoning, expected_impact }
└── rag_injection_metadata: { ... }
```

### 关键新增字段（vs v3）

| 字段 | 说明 |
|------|------|
| `definition` | 精确的自然语言定义（替代旧的 `semantic_meaning`） |
| `broader_concept` | IS-A 父概念（层次完整性） |
| `sibling_concepts` | 兄弟概念（消歧义） |
| `distinguish_from` | 与相似概念的区别 |
| `terminology{}` | 术语映射：同义词、缩写、跨语言、上下文别名 |
| `abnormal_indicates` | 异常值指示什么问题 |
| `conditions` | 关系成立的前提条件 |
| `exceptions` | 关系不成立的例外情况 |
| `constraints[]` | 领域约束和规则（新增顶级字段） |

### 自然语言规范 (NL Spec)

`rag_ontology_nl_spec.md` 包含：
1. 领域概述（定义、边界）
2. 核心实体（角色、生命周期、交互）
3. 概念字典（每个概念的定义、层次、消歧义、术语映射）
4. 关系图谱（机制、条件、例外、时滞）
5. 公理与约束
6. 混杂因子
7. 过程/逻辑阶段
8. 知识缺口
9. 构建元数据

## Consumer 消费方式

### Context Builder: 加载和映射

1. 读取 `rag_ontology_draft.json` → 映射 `definition` 到参数描述，`expected_value_range` 到范围，`constraints` 到验证规则
2. 读取 `rag_ontology_nl_spec.md` → 供下游 LLM agent 理解领域上下文
3. 读取 `rag_structured_data.json` → 提取验证规则和查询模板
4. 合并 `rag_clarification_needed.json` 到自己的 unknowns

### 术语映射使用

本体中每个概念都有 `terminology` 字段。消费者 agent 可以：
- 用任何别名（数据列名、缩写、中文名）查找概念
- 跨语言引用概念
- 在不同上下文中使用不同的名称

### Fallback Chain

```
1. Try: Skill("rag-knowledge-builder", ...)
   ↓ FAILED
2. Try: Pre-generated rag_ontology_draft.json in 00_input/
   ↓ NOT FOUND
3. Fallback: Build ontology from scratch (context-builder steps)
```

RAG 是加速器，不是硬依赖。

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
