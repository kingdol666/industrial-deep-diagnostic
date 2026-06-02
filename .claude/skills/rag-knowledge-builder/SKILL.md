---
name: rag-knowledge-builder
description: "Automatic ontology model construction engine — collects knowledge from local KB (ChromaDB) and web search, then uses LLM to build domain-specific ontology models with rich natural language design. Focuses on concept hierarchy, precise semantic definitions, relationship semantics, axioms, constraints, and terminology mapping. Works for ANY knowledge domain. Triggers on: 知识库构建, 本体构建, 构建本体模型, 结构化数据生成, 领域知识库, 本体模型设计, ontology construction, build ontology, knowledge retrieval, build knowledge base, RAG search. Use as a pre-step for any skill that needs domain-aware structured knowledge. Do NOT trigger for: simple file search, generic web Q&A that doesn't need ontology construction."
commands:
  - rag-knowledge-builder
  - rag-knowledge-builder start
  - rag-knowledge-builder build-ontology
  - rag-knowledge-builder retrieve-score
  - rag-knowledge-builder web-search
compatibility: |
  Requires Python 3.10+ with uv venv for ChromaDB + sentence-transformers embeddings.
  Network access required for web retrieval mode. Can run offline with local KB only.
  Node.js 18+ for schema validation (optional — Python fallback available).
---

# RAG Knowledge Builder — 自动领域本体构建引擎

## Language Default

默认输出语言为中文。本体中的自然语言定义、关系机制、实体角色描述均使用中文。结构化字段名和 enum 值保持英文。

## Core Mission

**本 skill 的唯一使命：从搜索收集到的知识，自动构建高质量的领域本体模型。**

一个好的本体必须满足 **自然语言本体设计原则**（详见 `resources/ontology-design-principles.md`）：

1. **清晰性** — 每个概念有精确、无歧义的自然语言定义，说"它是什么"而非"它叫什么"
2. **一致性** — 概念和关系之间逻辑自洽，不存在循环因果链或矛盾定义
3. **层次化** — 概念按 IS-A / PART-OF 关系组织，有明确的父概念和兄弟概念
4. **粒度适当** — 不过度泛化（"参数"），也不过度具体（每个传感器编号）
5. **可追溯** — 每个声明追溯到知识源，UNKNOWN 诚实标注

本 skill 执行四个阶段：

1. **Retrieve + Score** — 从本地 ChromaDB + 可选 web 搜索多视角检索知识，5 维评分
2. **Construct Ontology** — LLM 逐块阅读知识、验证适用性、构建符合本体工程原则的领域本体
3. **Generate Structured Data** — 从本体生成机器消费模板（示例数据、验证规则、查询模板）
4. **Validate** — 多维质量验证，输出审核日志

**没有关键词映射的回退路径。** LLM agent 是从知识块到本体的唯一通道。任何未被 LLM 验证为适用于目标领域的知识块都会被拒绝并记录。

**领域无关。** 适用于任何知识领域。LLM 动态识别领域概念、实体、关系和约束。

---

## Commands

| Command | Action |
|---------|--------|
| `/rag-knowledge-builder` | Full pipeline (Phase 0-4) |
| `/rag-knowledge-builder start` | Start/health-check the RAG retrieval engine |
| `/rag-knowledge-builder build-ontology` | End-to-end: retrieve → ontology → structured data → verify |
| `/rag-knowledge-builder retrieve-score` | Phase 1 only: retrieve + score + triage |
| `/rag-knowledge-builder web-search` | Web-only retrieval (no local KB) |

---

## Workspace Convention

### Path Resolution

```
SKILL_PATH   = <skill 部署位置>
PROJECT_ROOT = cd $SKILL_PATH/../../.. && pwd
```

### Mode A: Consumer-Call (被其他 Skill 调用)

消费者 skill 通过 `run_dir` 参数指定输出目录。直接写入 `$run_dir/00_input/`。

### Mode B: Standalone (独立使用)

```bash
SKILL_PATH="<path-to-this-skill>"
PROJECT_ROOT="$(cd "$SKILL_PATH/../../.." && pwd)"
WORKSPACE="$PROJECT_ROOT/workspace/rag-outputs"
RUN_DIR="$WORKSPACE/$(date +%Y%m%d%H%M%S)_$(echo "$domain" | tr ' ' '_' | tr -cd '[:alnum:]_-' | cut -c1-40)"
mkdir -p "$RUN_DIR/00_input"
```

---

## Invocation Protocol

### A. End-to-end: `build-ontology` (recommended)

```
Skill({
  skill: "rag-knowledge-builder",
  args: "domain='<description>' target_concepts='<csv>' related_concepts='<csv>' context_dimensions='<csv>' run_dir='<path>'"
})
```

**Parameters:**

| Parameter | Required | Format | Example |
|-----------|:--------:|--------|---------|
| `domain` | Yes | Free-text domain description | `Type 2 diabetes patient risk stratification with HbA1c and comorbidity factors` |
| `target_concepts` | Yes | Comma-separated core concepts to be defined | `hba1c_pct,egfr_ml_min,cardiovascular_event_risk` |
| `related_concepts` | Yes | Comma-separated candidate related concepts | `fasting_glucose_mg_dl,bmi_kg_m2,age_years` |
| `context_dimensions` | Yes | Comma-separated grouping/categorical fields | `patient_cohort,study_site,ethnicity` |
| `run_dir` | No | Absolute path (required for consumer-call mode) | `/path/to/runs/<timestamp>_<name>` |
| `interaction_mode` | No | `auto` / `interactive` / `minimal` | `auto` |
| `use_web` | No | `true` / `false` | `true` |

> **Legacy parameter names** (`scenario`, `target_cols`, `param_cols`, `group_cols`) remain accepted as aliases.

**Output contracts (all written to `$run_dir/00_input/`):**

| File | Content | Phase |
|------|---------|-------|
| `rag_ontology_draft.json` | **结构化本体** — 实体、概念字典、关系图谱、约束规则、混杂因子 | Phase 2 |
| `rag_ontology_nl_spec.md` | **自然语言本体规范** — 领域概述 + 概念字典 + 关系图谱（人类可读） | Phase 2 |
| `rag_structured_data.json` | 机器消费模板 — 示例数据、验证规则、查询模板 | Phase 3 |
| `rag_scored_chunks.json` | 知识块（5 维评分 + LLM 分类） | Phase 1 |
| `rag_audit_log.json` | 质量验证结果 + 知识源追溯 + 置信度 | Phase 4 |
| `rag_clarification_needed.json` | 语义未确定的概念列表 | Phase 2 |

> **关键：** Phase 2 同时输出 JSON 和 Markdown。JSON 给机器消费，Markdown 给人类审阅。两者共同构成完整的本体模型。

### B. Step-by-step

```
Skill({
  skill: "rag-knowledge-builder",
  args: "retrieve-score domain='...' target_concepts='...' ..."
})
```

然后手动执行 Phase 2-4。

---

## Execution Flow

```
┌──────────────────────────────────────────────────────────────────────┐
│       RAG KNOWLEDGE BUILDER — 自动领域本体构建引擎                   │
│  知识收集 → 本体构建（结构化 + 自然语言规范）→ 数据模板 → 质量验证  │
└──────────────────────────────────────────────────────────────────────┘

Phase 0: Engine Startup
  ├── rag_client.py start      ← Auto-start rag-retrieval-engine
  └── Health check + KB ready

Phase 1: Knowledge Collection (engine + LLM triage)
  ┌─────────────────────────────────────────────────────────────────┐
  │  Read: agents/retrieval-agent.md + agents/scoring-agent.md     │
  │  ① 4-perspective query × (ChromaDB + Web)                     │
  │  ② 5-dim score (D1 semantic, D2 concept, D3 domain,           │
  │     D4 source, D5 crossref) + quality gates                    │
  │  ③ LLM content triaging: APPLICABLE / PARTIALLY / REJECTED    │
  │  ④ Dedup + source ranking                                      │
  └─────────────────────────────────────────────────────────────────┘
  Output: rag_scored_chunks.json

Phase 2: Ontology Construction ★★★ CORE ★★★
  ┌─────────────────────────────────────────────────────────────────┐
  │  Read: agents/ontology-construction-agent.md                    │
  │  Read: resources/ontology-design-principles.md                  │
  │                                                                 │
  │  ① 领域理解 → 领域定义 + 边界 + 核心实体                       │
  │  ② 逐块审阅 → APPLICABLE / PARTIALLY / REJECTED (带原因)     │
  │  ③ 概念建模 → 精确定义 + 层次分类 + 消歧义                    │
  │  ④ 关系抽取 → 机制描述 + 方向 + 条件 + 例外 + 时序            │
  │  ⑤ 实体识别 → 角色描述 + 生命周期 + 交互关系                  │
  │  ⑥ 约束发现 → 硬约束 / 软约束 / 领域规则                      │
  │  ⑦ 混杂识别 → 上下文维度分析 + 效应修饰                       │
  │  ⑧ 自然语言规范 → rag_ontology_nl_spec.md                      │
  └─────────────────────────────────────────────────────────────────┘
  Output: rag_ontology_draft.json + rag_ontology_nl_spec.md

Phase 3: Structured Data Generation
  ┌─────────────────────────────────────────────────────────────────┐
  │  Read: agents/structured-data-generator.md                     │
  │  示例数据 / 验证规则（来自约束）/ 查询模板 / 测试场景          │
  └─────────────────────────────────────────────────────────────────┘
  Output: rag_structured_data.json

Phase 4: Quality Verification (gate)
  ┌─────────────────────────────────────────────────────────────────┐
  │  Read: agents/quality-verification-agent.md                    │
  │  6-dim: schema + NL quality + semantic completeness            │
  │  + logical consistency + cross-source + downstream             │
  └─────────────────────────────────────────────────────────────────┘
  Output: rag_audit_log.json (with verdict)
```

---

## What Makes a Good Ontology — 设计原则摘要

> 完整规范见 `resources/ontology-design-principles.md`

### 1. 清晰性 (Clarity)
每个概念必须有一个**无歧义的自然语言定义**。

| ❌ 差的定义 | ✅ 好的定义 |
|------------|-----------|
| "HbA1c 的百分比值" | "糖化血红蛋白占血红蛋白总量的百分比，反映过去 2-3 个月的平均血糖水平" |
| "主轴温度" | "数控机床主轴前轴承外圈的实时温度，表征轴承摩擦热积累程度" |
| "压力参数" | "反应釜顶部的表压读数（bar），受温度和反应进度共同影响" |

### 2. 一致性 (Coherence)
- 不存在循环因果链
- 同一概念在不同上下文中定义一致
- 关系方向不矛盾

### 3. 层次化 (Hierarchical)
- 每个概念有明确的 `broader_concept`（IS-A 关系）
- 区分 IS-A（是一种）和 PART-OF（是一部分）
- 层次深度 2-5 层

### 4. 粒度适当 (Appropriate Granularity)
- 不用 "参数" 这种过度泛化的概念
- 不为每个传感器编号创建单独概念
- 粒度匹配分析目标

### 5. 可追溯 (Traceability)
- 每个概念、关系、实体都标注 `knowledge_source`
- UNKNOWN 诚实标注，不猜测
- 拒绝的知识块有明确原因

### 6. 关系语义丰富 (Rich Relationship Semantics)
- 每条关系有 2-3 句机制描述（为什么 A 影响 B）
- 明确方向（A↑ 时 B 如何变化）
- 标注条件（关系成立的前提）和例外（关系不成立的情况）

---

## Loading Guide

| When | Read | Why |
|------|------|-----|
| Invoked | This file (SKILL.md) | Invocation contract + execution flow |
| Phase 1 | `agents/retrieval-agent.md` | 4-perspective queries + LLM triaging |
| Phase 1 | `agents/scoring-agent.md` | 5-dim scoring rubric + quality gates |
| Phase 2 | **`agents/ontology-construction-agent.md`** | **本体构建方法论（核心 agent）** |
| Phase 2 | **`resources/ontology-design-principles.md`** | **本体设计原则（必读）** |
| Phase 3 | `agents/structured-data-generator.md` | 本体 → 结构化数据 |
| Phase 4 | `agents/quality-verification-agent.md` | 6-dim 质量验证 |
| Integration | `resources/integration_guide.md` | 消费者 skill 集成方式 |
| Pattern library | `resources/parameter_pattern_library.md` | 物理量通用模式 |
| Scoring detail | `resources/scoring_rubric.md` | 评分详细示例 |

**Do NOT load everything upfront.** 每个 agent prompt 是自包含的。

---

## Integration with Consumer Skills

### Files exchanged

| From RAG Builder | → | To Consumer Skill | Purpose |
|------------------|---|---------------------|---------|
| `rag_ontology_draft.json` | → | `<consumer>/01_ontology/ontology.json` | 结构化本体数据 |
| `rag_ontology_nl_spec.md` | → | `<consumer>/01_ontology/ontology_nl_spec.md` | 自然语言本体规范（人类可读） |
| `rag_structured_data.json` | → | `<consumer>/01_ontology/structured_data.json` | 机器消费模板 |
| `rag_scored_chunks.json` | → | `<consumer>/02_processed/scored_chunks.json` | 知识块证据 |
| `rag_clarification_needed.json` | → | `<consumer>/00_input/clarification_needed.json` | 需要用户澄清的概念 |
| `rag_audit_log.json` | → | `<consumer>/00_input/audit_log.json` | 质量验证结果 |

### Calling pattern

```
Skill({
  skill: "rag-knowledge-builder",
  args: "domain='<free-text>' target_concepts='<csv>' related_concepts='<csv>' context_dimensions='<csv>' run_dir='<RUN_DIR>' interaction_mode='auto'"
})
```

---

## When to Use This Skill

当需要**从知识源自动构建领域本体模型**时使用：

- **任何领域分析流水线**的前置步骤——提供有理论基础的、可追溯的概念定义
- **知识库构建**——将非结构化知识转化为结构化本体
- **领域理解**——快速建立对陌生领域概念体系的理解
- **跨域复用**——本体结构可被其他 skill 消费

**领域覆盖（LLM 动态识别，可扩展）：**
工业/制造 · 医学/临床 · 法律/合规 · 金融/风险 · 科学研究 · 农业/环境 · 软件/IT · 教育 · 人文社科 · 半导体/微电子 · 任何有可检索知识的领域

---

## Architecture Decisions

**为什么本体构建是核心（而非检索）：**
- 检索是手段，本体是目的。下游 agent 消费的是本体模型。
- 一个好的本体需要概念层次、精确定义、约束规则——这些不是检索能直接提供的。
- LLM 的领域理解能力是关键瓶颈——它必须综合判断，而非简单提取。

**为什么需要自然语言规范（NL Spec）：**
- JSON 给机器消费，但不是人类可读的。领域专家需要审阅和验证本体。
- NL Spec 让本体"自文档化"——阅读规范就能理解整个领域模型。
- 丰富的自然语言定义让下游 LLM agent 更好地理解概念语义。

**为什么结构化数据生成是独立阶段：**
- 本体描述概念"是什么"；结构化数据描述下游 agent "怎么用"。
- 没有结构化数据，本体是"描述性的但不可消费的"。

---

## Reference Files

| File | When to Read | Content |
|------|-------------|---------|
| `agents/retrieval-agent.md` | Phase 1 | 多视角检索 + LLM 内容分类 |
| `agents/scoring-agent.md` | Phase 1 | 5 维评分 + 质量门 |
| **`agents/ontology-construction-agent.md`** | **Phase 2** | **LLM 本体构建方法论** |
| **`resources/ontology-design-principles.md`** | **Phase 2** | **本体设计原则** |
| `agents/structured-data-generator.md` | Phase 3 | 本体 → 结构化数据 |
| `agents/quality-verification-agent.md` | Phase 4 | 6 维质量验证 |
| `resources/parameter_pattern_library.md` | Phase 2 | 物理量通用模式 |
| `resources/ontology_templates.md` | Phase 2 | 本体输出模板 |
| `resources/integration_guide.md` | Integration | 消费者 skill 集成 |
| `resources/scoring_rubric.md` | Phase 1 | 评分详细示例 |
| `resources/indexing_guide.md` | KB expansion | KB 扩展指南 |

---

## Anti-Patterns (DO NOT)

- ❌ **DO NOT** 关键词匹配分类概念。LLM 必须阅读完整内容。
- ❌ **DO NOT** 硬编码领域实体。LLM 动态识别领域实体。
- ❌ **DO NOT** 使用模糊定义。"温度就是温度值"不是定义。
- ❌ **DO NOT** 跳过概念层次构建。每个概念必须有 `broader_concept`。
- ❌ **DO NOT** 跳过自然语言规范。NL Spec 是本体的核心输出之一。
- ❌ **DO NOT** 忽略被拒绝的知识块。每个拒绝必须有原因。
- ❌ **DO NOT** 使用 `domain_type="generic"`。LLM 必须识别具体领域。
- ❌ **DO NOT** 为 UNKNOWN 概念捏造定义。诚实标注 UNKNOWN。
- ❌ **DO NOT** 在 Python 引擎中添加 LLM 调用。LLM 运行在 skill 层。
