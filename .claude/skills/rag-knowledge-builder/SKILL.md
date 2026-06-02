---
name: rag-knowledge-builder
description: "Universal RAG-powered knowledge retrieval and LLM-driven ontology/structured-data construction engine. Retrieves domain knowledge from local vector DB (ChromaDB) and web search, scores with 5-dimensional metrics, then uses an LLM agent to construct domain-specific ontology models and structured data templates. Works for ANY knowledge domain — science, engineering, medicine, law, finance, education, business, humanities, manufacturing, software, agriculture, etc. The LLM dynamically identifies domain concepts, entities, relationships, and constraints from knowledge content rather than relying on hardcoded mappings. Triggers on: 知识库构建, 知识检索, 本体构建, 从文档提取知识, RAG search, knowledge retrieval, ontology construction, build ontology, retrieve knowledge, build knowledge base, 构建本体模型, 结构化数据生成, 知识图谱, 领域知识, 通用知识库. Use as a pre-step for any skill that needs domain-aware structured knowledge. Do NOT trigger for: simple file search, generic web Q&A that doesn't need knowledge base construction."
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

# RAG Knowledge Builder — Universal Knowledge → Ontology → Structured Data

## Core Principle

**Every structured knowledge claim MUST be traceable to a source, scored for relevance, and validated by an LLM for domain applicability before being injected.** This skill does three things in sequence, and only three things:

1. **Retrieve** — multi-perspective query against local ChromaDB + optional web search
2. **Construct Ontology (LLM-driven)** — LLM agent reads every chunk, validates applicability, builds domain-specific ontology
3. **Generate Structured Data (LLM-driven)** — LLM agent converts ontology into machine-consumable data templates (sample data, query templates, prompt templates, validation rules)

**There is no keyword-matching fallback.** The LLM agent is the only path from chunks to ontology. Any chunk that is not validated by the LLM as APPLICABLE to the target domain is rejected and documented.

**This skill is domain-agnostic by design.** It works for ANY knowledge domain — industrial, scientific, medical, legal, financial, educational, agricultural, environmental, software, humanities, and beyond. The LLM dynamically identifies domain concepts, entities, relationships, causal chains, confounders, and constraints based on the user's domain description and accepted knowledge chunks. There are **no hardcoded domain-specific mappings** in this skill.

---

## Invocation Protocol — How Other Skills Call This Skill

Any skill that needs domain-aware structured knowledge can call this one. Use one of two commands:

### A. End-to-end: `build-ontology` (recommended)

Runs all three phases in one call. Use this when you want the full pipeline.

```
Skill({
  skill: "rag-knowledge-builder",
  args: "domain='<description>' target_concepts='<csv>' related_concepts='<csv>' context_dimensions='<csv>' run_dir='<path>'"
})
```

**Parameters:**

| Parameter | Required | Format | Example |
|-----------|:--------:|--------|---------|
| `domain` | Yes | Free-text description of the target knowledge domain | `Type 2 diabetes patient risk stratification with HbA1c and comorbidity factors` |
| `target_concepts` | Yes | Comma-separated field/concept names to be explained | `hba1c_pct,egfr_ml_min,cardiovascular_event_risk` |
| `related_concepts` | Yes | Comma-separated candidate explanatory concepts | `fasting_glucose_mg_dl,bmi_kg_m2,age_years,medication_dose_mg,exercise_min_week` |
| `context_dimensions` | Yes | Comma-separated grouping/categorical fields | `patient_cohort,study_site,ethnicity,measurement_batch` |
| `run_dir` | Yes | Absolute path | `/path/to/workspace/runs/xxx` |
| `interaction_mode` | No | `auto` / `interactive` / `minimal` | `auto` |
| `use_web` | No | `true` / `false` | `true` |

> **Legacy parameter names** (`scenario`, `target_cols`, `param_cols`, `group_cols`) remain accepted as aliases for backwards compatibility.

**Output contracts (all written to `$run_dir/00_input/`):**

| File | Content | Phase |
|------|---------|-------|
| `rag_scored_chunks.json` | Chunks after retrieve + 5-dim score | Phase 1 |
| `rag_ontology_draft.json` | LLM-validated domain-specific ontology | Phase 2 |
| `rag_structured_data.json` | Machine-consumable data templates (sample rows, query templates, validation rules) | Phase 3 |
| `rag_audit_log.json` | Provenance + rejection reasons + LLM confidence | All phases |
| `rag_clarification_needed.json` | Concepts whose semantic meaning is UNKNOWN | Phase 2 |

### B. Step-by-step: `retrieve-score` + manual LLM invocation

Use this when you want fine-grained control or to inspect chunks before LLM construction.

```
Skill({
  skill: "rag-knowledge-builder",
  args: "retrieve-score domain='...' target_concepts='...' ..."
})
```

Then read the LLM agent prompt and execute it manually:
1. Read `agents/ontology-construction-agent.md`
2. Read `agents/structured-data-generator.md`
3. Read scored chunks from `rag_scored_chunks.json`
4. Execute LLM agents in sequence
5. Write outputs

---

## Execution Flow

### Phase 0: Engine Startup (automatic)

```
rag_client.py start
└── Checks GET /health; if down, auto-starts `uv run python server.py` from rag-retrieval-engine
└── Waits up to 30s for readiness
└── If engine fails: continue in offline mode (chunks-only, no scoring, no web)
```

### Phase 1: Retrieve + Score (engine)

Multi-perspective query (4 angles × local ChromaDB + optional web), 5-dim score, quality gates. Produces `rag_scored_chunks.json`.

```
rag_client.py retrieve-score \
  --domain "..." \
  --target-concepts "..." \
  --related-concepts "..." \
  --context-dimensions "..." \
  --output-dir "$run_dir"
```

The chunk content remains in scored chunks for the LLM to read.

### Phase 2: LLM-Driven Ontology Construction (CORE)

The LLM (Claude, GPT, etc.) reads `agents/ontology-construction-agent.md` and **performs the construction itself**, treating the engine's output as raw input material only.

**Critical design decision:** Phase 2 is NOT executed by the Python engine. The engine's legacy `injector.py` (template-based injection with hardcoded equipment/process mappings) has been **decommissioned** — it produced incorrect results whenever chunks came from a different domain than the hardcoded one. The LLM agent is now the only valid construction path, and is the only mechanism that can correctly handle arbitrary domains.

**LLM agent's 7-step protocol (read `agents/ontology-construction-agent.md` for full details):**
1. **Domain Understanding** — what is the domain? what concepts/entities/relationships are involved? what are the key outcomes?
2. **Chunk-by-chunk Content Review** — read full content, judge applicability, reject with reason if not applicable
3. **Concept Classification (LLM)** — classify by semantic meaning, not keyword
4. **Relationship Extraction** — extract mechanism/dependency, map to actual concept names, validate
5. **Entity / Component Identification** — domain-specific entities (not hardcoded)
6. **Confounder / Context Dimension Identification** — explain WHY each context dimension matters
7. **Metadata Assembly** — provenance, match rate, knowledge gaps

**Anti-hallucination rules:**
- Never invent semantic meanings — mark `UNKNOWN` if no chunk discusses it
- Never force-fit relationships from wrong-domain chunks
- Never use generic entity names — always identify domain-specific entities
- Always cite the source chunk
- Always explain rejection reasons

### Phase 3: LLM-Driven Structured Data Generation

After the ontology is built, a second LLM agent (`agents/structured-data-generator.md`) consumes the ontology and produces **structured data templates** that downstream agents can consume directly:

1. **Sample data templates** — for each role (target/related/context/metadata), generate a sample row showing expected format
2. **Validation rules** — semantic plausibility bounds (e.g., HbA1c ∈ [3, 15]% for clinical, BMI ∈ [10, 60] kg/m²)
3. **Causal/Relational query templates** — SQL/JSON-Path queries for testing the inferred relationships
4. **LLM prompt templates** — for downstream agents to reference the ontology
5. **Test scenarios** — concrete test cases with expected behavior

### Phase 4: Quality Verification (final gate)

The quality verification agent (`agents/quality-verification-agent.md`) validates the ontology + structured data across 5 dimensions:
1. Schema compliance
2. Content plausibility (domain reasoning)
3. Logical consistency (no contradictions)
4. Cross-source consistency (chunks agree)
5. Downstream consumability (any consumer skill can directly use)

Verdict: PASS / CONDITIONAL / FAIL. FAIL triggers re-construction with feedback.

---

## Loading Guide

This skill uses progressive loading. Read only what each step needs:

| When | Read | Why |
|------|------|-----|
| Invoked | This file (SKILL.md) | Invocation contract + execution flow |
| Phase 1 | `agents/retrieval-agent.md` | 4-perspective queries + content filtering |
| Phase 1 | `agents/scoring-agent.md` | 5-dim scoring rubric + quality gates |
| Phase 2 | `agents/ontology-construction-agent.md` | **LLM-driven ontology construction (PRIMARY PATH)** |
| Phase 3 | `agents/structured-data-generator.md` | **LLM-driven structured data generation** |
| Phase 4 | `agents/quality-verification-agent.md` | 5-dim quality check |
| Integration | `resources/integration_guide.md` | How to connect to any consumer skill |
| KB expansion | `resources/kb_taxonomy_guide.md` | How to add new domains to the KB |
| Pattern library | `resources/concept_pattern_library.md` | Domain-generic concept patterns (entity, property, event, relationship, classification, ...) |

**Do NOT load everything upfront.** Each agent prompt is self-contained.

---

## Pipeline Overview

```
┌──────────────────────────────────────────────────────────┐
│          RAG KNOWLEDGE BUILDER — Universal Pipeline      │
│  3 stages: Retrieve+Score → LLM Ontology → LLM Data     │
└──────────────────────────────────────────────────────────┘

Phase 0: Engine Startup
  ├── rag_client.py start      ← Auto-start rag-retrieval-engine (uv run)
  └── Health check + KB ready

Phase 1: Retrieve + Score (engine, deterministic)
  ┌─────────────────────────────────────────────────────┐
  │  ① 4-perspective query × (ChromaDB + Web)          │
  │  ② 5-dim score (D1 semantic, D2 concept, D3 domain,│
  │     D4 source, D5 crossref)                         │
  │  ③ Quality gates: CRITICAL/ACCEPTED/CONDITIONAL/REJECTED │
  └─────────────────────────────────────────────────────┘
  Output: rag_scored_chunks.json

Phase 2: LLM Ontology Construction (CORE)
  ┌─────────────────────────────────────────────────────┐
  │  Read agents/ontology-construction-agent.md         │
  │  ① Domain understanding                            │
  │  ② Chunk-by-chunk applicability check               │
  │  ③ Concept classification (LLM, not keyword)       │
  │  ④ Relationship extraction + validation            │
  │  ⑤ Entity identification (domain-specific)         │
  │  ⑥ Confounder / context identification             │
  │  ⑦ Metadata assembly                               │
  └─────────────────────────────────────────────────────┘
  Output: rag_ontology_draft.json (schema-compliant)

Phase 3: LLM Structured Data Generation
  ┌─────────────────────────────────────────────────────┐
  │  Read agents/structured-data-generator.md          │
  │  ① Sample data templates (target/related/...)      │
  │  ② Validation rules (semantic plausibility bounds) │
  │  ③ Relational query templates (SQL/JSON-Path)      │
  │  ④ LLM prompt templates (for downstream agents)    │
  │ ⑤ Test scenarios (concrete test cases)            │
  └─────────────────────────────────────────────────────┘
  Output: rag_structured_data.json

Phase 4: Quality Verification (gate)
  ┌─────────────────────────────────────────────────────┐
  │  Read agents/quality-verification-agent.md         │
  │  5-dim: schema, plausibility, consistency,          │
  │  cross-source, downstream-consumability             │
  └─────────────────────────────────────────────────────┘
  Output: rag_audit_log.json (with verdict)
```

---

## Architecture Decisions

**Why LLM is the only construction path (no fallback to template injection):**
- Template injection (`injector.py` with hardcoded equipment/process keywords) was tested across multiple domains: it injected irrelevant entities, mapped concepts to wrong meanings, and added false causal chains whenever the input domain differed from the templated one.
- LLM correctly rejected wrong-domain chunks and reconstructed the ontology from the actual domain knowledge.
- Conclusion: keyword matching cannot scale across knowledge domains. LLM content understanding is mandatory.

**Why structured data generation is a separate phase:**
- Ontology describes WHAT each concept means; structured data templates describe HOW downstream agents should USE them.
- Consumer agents need: (a) sample rows to test their pipelines, (b) validation bounds to detect outliers, (c) relational query templates to test hypotheses, (d) prompt templates to reference the ontology consistently.
- Without structured data, the ontology is "descriptive but not consumable".

**Why the pattern library is organized by generic concept type, not by domain:**
- A previous version organized patterns by physical quantity (temperature, vibration, flow, pressure, etc.), which only worked for engineering/manufacturing domains.
- The new version is organized by **generic concept type** (entity, property, event, relationship, classification, measurement, time-series, etc.) — applicable to any domain.
- LLM uses the pattern library to infer the meaning of any concept name, in any domain.

---

## When to Use This Skill

Use this skill **whenever you need to build a domain-specific structured knowledge base from documents or web content**, including but not limited to:

- **Before any domain-analysis pipeline** that needs grounded, evidence-backed concept definitions
- **Standalone** — to index, retrieve, and structure a domain knowledge base
- **As a modular RAG plugin** — any skill can call this skill
- **Across many domains**: science, engineering, medicine, law, finance, education, business, humanities, manufacturing, software, agriculture, environmental science, etc.

**Domain coverage (LLM-driven, extensible on demand):**
- ✅ Industrial / manufacturing / process engineering
- ✅ Medicine / clinical / biomedical
- ✅ Legal / regulatory / compliance
- ✅ Finance / economics / risk
- ✅ Software / IT / cybersecurity
- ✅ Education / pedagogy
- ✅ Agriculture / environmental science
- ✅ Scientific research (physics, chemistry, biology, materials)
- ✅ Humanities (history, linguistics, philosophy)
- ✅ Business / marketing / operations
- ✅ Any other domain with retrievable knowledge

**The skill is domain-agnostic by design.** New domains are supported as long as the LLM can find applicable knowledge (local KB or web). If knowledge gaps exist, the skill reports them in `rag_clarification_needed.json` for the user to fill in.

---

## Integration with Consumer Skills

### Files exchanged

| From RAG Builder | → | To Consumer Skill | Purpose |
|------------------|---|---------------------|---------|
| `rag_ontology_draft.json` | → | `<consumer>/01_ontology/ontology.json` | Pre-fill ontology for LLM review |
| `rag_structured_data.json` | → | `<consumer>/01_ontology/structured_data.json` | Templates for downstream agents |
| `rag_scored_chunks.json` | → | `<consumer>/02_processed/scored_chunks.json` | Mechanisms for evidence fusion |
| `rag_clarification_needed.json` | → | `<consumer>/00_input/clarification_needed.json` | Concepts requiring user clarification |
| `rag_audit_log.json` | → | `<consumer>/00_input/audit_log.json` | Provenance + LLM confidence |

### Calling pattern

Any consumer skill's context-builder agent can invoke this skill at the start of its pipeline:

```
Skill({
  skill: "rag-knowledge-builder",
  args: "domain='<free-text domain description>' target_concepts='<csv>' related_concepts='<csv>' context_dimensions='<csv>' run_dir='<RUN_DIR>' interaction_mode='auto'"
})
```

The skill returns once the ontology draft and structured data are written. The consumer's context-builder then proceeds with its own subsequent phases.

**No domain-specific assumptions in the calling protocol.** The `domain`, `target_concepts`, `related_concepts`, and `context_dimensions` parameters are all free-form, defined per use case.

---

## Reference Files

| File | When to Read | Content |
|------|-------------|---------|
| `agents/retrieval-agent.md` | Phase 1 | Multi-query retrieval + LLM content triaging (domain-agnostic) |
| `agents/scoring-agent.md` | Phase 1 | 5-dimension scoring rubric + quality gates (domain-agnostic) |
| `agents/ontology-construction-agent.md` | **Phase 2 (PRIMARY)** | **LLM-driven ontology construction with content understanding** |
| `agents/structured-data-generator.md` | **Phase 3** | **LLM-driven structured data generation** |
| `agents/quality-verification-agent.md` | **Phase 4 (GATE)** | **5-dim quality check (domain-neutral)** |
| `resources/concept_pattern_library.md` | Phase 2 | Generic concept patterns (entity/property/event/relationship/...) |
| `resources/kb_taxonomy_guide.md` | KB expansion | How to add new domains to the KB |
| `resources/integration_guide.md` | Integration | How to connect to any consumer skill |
| `resources/scoring_rubric.md` | Phase 1 | Detailed scoring examples + edge cases (multi-domain) |

**Removed / Deprecated:**
- `agents/ontology-builder.md` — legacy template-based injection with hardcoded domain mappings. **Removed.** Replaced by `agents/ontology-construction-agent.md`.
- `engine/injector.py` — hardcoded entity identification. **Removed.** `rag_client.py` no longer calls it.

---

## Anti-Patterns (DO NOT)

- ❌ **DO NOT** rely on keyword matching for concept classification. The LLM must read content.
- ❌ **DO NOT** hardcode entities by domain. The LLM identifies domain-specific entities.
- ❌ **DO NOT** inject relationships without validating they apply to the target domain.
- ❌ **DO NOT** skip Phase 2 LLM construction. The engine's output is RAW INPUT only.
- ❌ **DO NOT** add LLM calls into the Python engine. The LLM runs at the skill layer (Claude/GPT), not in the retrieval engine.
- ❌ **DO NOT** treat `domain_type="generic"` as acceptable. The LLM must always identify a specific domain.
- ❌ **DO NOT** ignore rejected chunks. Every rejection must be documented with a reason.
- ❌ **DO NOT** assume the domain is industrial, scientific, medical, or any other specific field. The LLM must infer the domain from the input.
- ❌ **DO NOT** apply domain-specific filters (e.g., "reject medical content for a CNC query"). Domain filtering is data-driven from the user's stated domain.
