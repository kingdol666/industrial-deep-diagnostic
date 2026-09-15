---
name: rag-knowledge-builder
description: "Automatic domain-ontology construction engine — collects knowledge from a local knowledge base (ChromaDB) and web search, then uses an LLM to build domain-specific ontology models with rich natural-language design. Focuses on concept hierarchy, precise semantic definitions, relationship semantics, axioms, constraints, and terminology mapping. Works for ANY knowledge domain. Use this skill whenever the user wants to build, design, generate, or extend a domain ontology or a structured domain knowledge base — including phrasings such as: build an ontology, construct an ontology model, design a domain ontology, build a knowledge base, construct a knowledge base from documents, generate ontology JSON, turn my documents into a knowledge graph, structure domain knowledge, extract concepts and relationships from documents, index my documents into a knowledge base, prepare domain knowledge for a diagnostic or reporting pipeline, ontology-first knowledge construction, or build a domain knowledge model for RAG. Also use it as a pre-step for any skill that needs domain-aware structured knowledge. Do NOT trigger for simple file search, plain document lookup, or generic web Q&A that does not need ontology construction. Trigger: knowledge base construction, ontology construction, build ontology model, structured data generation, domain knowledge base, ontology model design, build ontology, ontology design, concept hierarchy, terminology mapping, knowledge retrieval, build knowledge base, RAG search, domain model."
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

# RAG Knowledge Builder — Automatic Domain Ontology Construction Engine

## Language Default

Default output language is Chinese. Natural-language definitions, relationship mechanisms, and entity role descriptions within the ontology are written in Chinese. Structured field names and enum values remain in English.

## Core Mission

**This skill's sole mission: automatically build high-quality domain ontology models from knowledge collected via search.**

A good ontology must satisfy the **natural-language ontology design principles** (see `resources/ontology-design-principles.md` for details):

1. **Clarity** — every concept has a precise, unambiguous natural-language definition that states "what it is" rather than "what it is called"
2. **Coherence** — concepts and relations are logically self-consistent; no circular causal chains or contradictory definitions
3. **Hierarchy** — concepts are organized by IS-A / PART-OF relations, with explicit parent and sibling concepts
4. **Appropriate granularity** — neither over-generalized ("parameter") nor over-specific (each individual sensor ID)
5. **Traceability** — every claim traceable to its knowledge sources; UNKNOWN honestly marked

This skill executes four phases:

1. **Retrieve + Score** — multi-perspective knowledge retrieval from local ChromaDB + optional web search, with 5-dimension scoring
2. **Construct Ontology** — the LLM reads knowledge chunk by chunk, validates applicability, and builds a domain ontology conforming to ontology engineering principles
3. **Generate Structured Data** — generate machine-consumption templates from the ontology (example data, validation rules, query templates)
4. **Validate** — multi-dimensional quality verification, outputting an audit log

**No keyword-mapping fallback path.** The LLM agent is the only channel from knowledge chunks to ontology. Any knowledge chunk not validated by the LLM as applicable to the target domain is rejected and logged.

**Domain-agnostic.** Works for any knowledge domain. The LLM dynamically identifies domain concepts, entities, relations, and constraints.

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

When loaded from OMP harness (`.claude/skills/rag-knowledge-builder/`), resources resolve via:
```
SKILL_PATH   = <this-skill-directory>/../../../.claude/skills/rag-knowledge-builder
SHARED_PATH  = <this-skill-directory>/../../../.claude/shared
PROJECT_ROOT = cd $SKILL_PATH/../../.. && pwd
```
In standalone/Claude harness mode, SKILL_PATH is the deployment directory directly.

### Mode A: Consumer-Call (invoked by other skills)

The consumer skill specifies the output directory via the `run_dir` parameter. Write directly into `$run_dir/00_input/`.

### Mode B: Standalone

```bash
SKILL_PATH="<path-to-this-skill>"
SHARED_PATH="<path-to-this-skill>/shared"
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
| `rag_ontology_draft.json` | **Structured ontology** — entities, concept dictionary, relationship graph, constraint rules, confounders | Phase 2 |
| `rag_ontology_nl_spec.md` | **Natural-language ontology spec** — domain overview + concept dictionary + relationship graph (human-readable) | Phase 2 |
| `rag_structured_data.json` | Machine-consumption templates — example data, validation rules, query templates | Phase 3 |
| `rag_scored_chunks.json` | Knowledge chunks (5-dim scoring + LLM classification) | Phase 1 |
| `rag_audit_log.json` | Quality verification results + knowledge-source traceability + confidence | Phase 4 |
| `rag_clarification_needed.json` | List of concepts with undetermined semantics | Phase 2 |

> **Key:** Phase 2 outputs both JSON and Markdown. JSON is for machine consumption, Markdown for human review. Together they constitute the complete ontology model.

### B. Step-by-step

```
Skill({
  skill: "rag-knowledge-builder",
  args: "retrieve-score domain='...' target_concepts='...' ..."
})
```

Then execute Phases 2-4 manually.

---

## Execution Flow

```
┌────────────────────────────────────────────────────────────────────────┐
│       RAG KNOWLEDGE BUILDER — Automatic Domain Ontology Builder        │
│  Knowledge collection → Ontology construction (structured + NL spec)   │
│  → Data templates → Quality verification                               │
└────────────────────────────────────────────────────────────────────────┘

Phase 0: Engine Startup
  ├── rag_client.py start      ← Auto-start rag-retrieval-engine
  └── Health check + KB ready

Phase 1: Knowledge Collection (engine + LLM triage)
  ┌────────────────────────────────────────────────────────────────────────┐
  │  Read: references/retrieval-agent.md + references/scoring-agent.md     │
  │  ① 4-perspective query × (ChromaDB + Web)                              │
  │  ② 5-dim score (D1 semantic, D2 concept, D3 domain,                    │
  │     D4 source, D5 crossref) + quality gates                            │
  │  ③ LLM content triaging: APPLICABLE / PARTIALLY / REJECTED             │
  │  ④ Dedup + source ranking                                              │
  └────────────────────────────────────────────────────────────────────────┘
  Output: rag_scored_chunks.json

Phase 2: Ontology Construction ★★★ CORE ★★★
  ┌────────────────────────────────────────────────────────────────────────┐
  │  Read: references/ontology-construction-agent.md                       │
  │  Read: resources/ontology-design-principles.md                         │
  │                                                                        │
  │  ① Domain understanding → definition + boundary + core entities        │
  │  ② Chunk-by-chunk review → APPLICABLE / PARTIALLY / REJECTED + reasons │
  │  ③ Concept modeling → precise definition + hierarchy + disambiguation  │
  │  ④ Relations → mechanism + direction + conditions + exceptions + timing│
  │  ⑤ Entities → role description + lifecycle + interactions              │
  │  ⑥ Constraints → hard / soft / domain rules                            │
  │  ⑦ Confounders → context dimensions + effect modifiers                 │
  │  ⑧ Natural-language spec → rag_ontology_nl_spec.md                     │
  └────────────────────────────────────────────────────────────────────────┘
  Output: rag_ontology_draft.json + rag_ontology_nl_spec.md

Phase 3: Structured Data Generation
  ┌────────────────────────────────────────────────────────────────────────┐
  │  Read: references/structured-data-generator.md                         │
  │  Example data / validation rules (from constraints) /                  │
  │  query templates / test scenarios                                      │
  └────────────────────────────────────────────────────────────────────────┘
  Output: rag_structured_data.json

Phase 4: Quality Verification (gate)
  ┌────────────────────────────────────────────────────────────────────────┐
  │  Read: references/quality-verification-agent.md                        │
  │  6-dim: schema + NL quality + semantic completeness                    │
  │  + logical consistency + cross-source + downstream                     │
  └────────────────────────────────────────────────────────────────────────┘
  Output: rag_audit_log.json (with verdict)
```

---

## What Makes a Good Ontology — Design Principles Summary

> Full specification in `resources/ontology-design-principles.md`

### 1. Clarity
Every concept must have an **unambiguous natural-language definition**.

| ❌ Poor definition | ✅ Good definition |
|------------|-----------|
| "The percentage value of HbA1c" | "Glycated hemoglobin as a percentage of total hemoglobin, reflecting the average blood glucose level over the past 2-3 months" |
| "Spindle temperature" | "Real-time temperature of the front-bearing outer ring of a CNC machine spindle, characterizing the degree of bearing friction heat accumulation" |
| "Pressure parameter" | "Gauge pressure reading (bar) at the top of a reactor, jointly influenced by temperature and reaction progress" |

### 2. Coherence
- No circular causal chains
- The same concept is defined consistently across different contexts
- Relation directions are not contradictory

### 3. Hierarchy
- Every concept has an explicit `broader_concept` (IS-A relation)
- Distinguish IS-A ("is a kind of") from PART-OF ("is a part of")
- Hierarchy depth 2-5 levels

### 4. Appropriate Granularity
- Do not use over-generalized concepts like "parameter"
- Do not create a separate concept for each individual sensor ID
- Granularity matches the analysis goal

### 5. Traceability
- Every concept, relation, and entity is annotated with `knowledge_source`
- UNKNOWN is honestly marked, not guessed
- Rejected knowledge chunks carry an explicit reason

### 6. Rich Relationship Semantics
- Every relation has a 2-3 sentence mechanism description (why A affects B)
- Explicit direction (how B changes when A↑)
- Annotate conditions (preconditions for the relation to hold) and exceptions (cases where the relation does not hold)

---

## Loading Guide

| When | Read | Why |
|------|------|-----|
| Invoked | This file (SKILL.md) | Invocation contract + execution flow |
| Phase 1 | `references/retrieval-agent.md` | 4-perspective queries + LLM triaging |
| Phase 1 | `references/scoring-agent.md` | 5-dim scoring rubric + quality gates |
| Phase 2 | **`references/ontology-construction-agent.md`** | **Ontology construction methodology (core agent)** |
| Phase 2 | **`resources/ontology-design-principles.md`** | **Ontology design principles (required reading)** |
| Phase 3 | `references/structured-data-generator.md` | Ontology → structured data |
| Phase 4 | `references/quality-verification-agent.md` | 6-dim quality verification |
| Integration | `resources/integration_guide.md` | How consumer skills integrate |
| Pattern library | `resources/parameter_pattern_library.md` | Generic patterns for physical quantities |
| Scoring detail | `resources/scoring_rubric.md` | Detailed scoring examples |

**Do NOT load everything upfront.** Each agent prompt is self-contained.

---

## Integration with Consumer Skills

### Files exchanged

| From RAG Builder | → | To Consumer Skill | Purpose |
|------------------|---|---------------------|---------|
| `rag_ontology_draft.json` | → | `<consumer>/01_ontology/ontology.json` | Structured ontology data |
| `rag_ontology_nl_spec.md` | → | `<consumer>/01_ontology/ontology_nl_spec.md` | Natural-language ontology spec (human-readable) |
| `rag_structured_data.json` | → | `<consumer>/01_ontology/structured_data.json` | Machine-consumption templates |
| `rag_scored_chunks.json` | → | `<consumer>/02_processed/scored_chunks.json` | Knowledge chunk evidence |
| `rag_clarification_needed.json` | → | `<consumer>/00_input/clarification_needed.json` | Concepts requiring user clarification |
| `rag_audit_log.json` | → | `<consumer>/00_input/audit_log.json` | Quality verification results |

### Calling pattern

```
Skill({
  skill: "rag-knowledge-builder",
  args: "domain='<free-text>' target_concepts='<csv>' related_concepts='<csv>' context_dimensions='<csv>' run_dir='<RUN_DIR>' interaction_mode='auto'"
})
```

---

## When to Use This Skill

Use when you need to **automatically build a domain ontology model from knowledge sources**:

- A pre-step for **any domain analysis pipeline** — provides theoretically grounded, traceable concept definitions
- **Knowledge base construction** — turns unstructured knowledge into a structured ontology
- **Domain understanding** — quickly build an understanding of an unfamiliar domain's concept system
- **Cross-domain reuse** — the ontology structure can be consumed by other skills

**Domain coverage (dynamically identified by the LLM, extensible):**
Industrial/manufacturing · Medical/clinical · Legal/compliance · Finance/risk · Scientific research · Agriculture/environment · Software/IT · Education · Humanities/social sciences · Semiconductors/microelectronics · Any domain with retrievable knowledge

---

## Architecture Decisions

**Why ontology construction is the core (not retrieval):**
- Retrieval is the means; the ontology is the end. What downstream agents consume is the ontology model.
- A good ontology requires concept hierarchy, precise definitions, and constraint rules — none of which retrieval alone can directly provide.
- The LLM's domain understanding capability is the key bottleneck — it must synthesize and judge, not simply extract.

**Why a natural-language spec (NL Spec) is needed:**
- JSON is for machine consumption and not human-readable. Domain experts need to review and validate the ontology.
- The NL Spec makes the ontology "self-documenting" — reading the spec alone conveys the entire domain model.
- Rich natural-language definitions help downstream LLM agents better grasp concept semantics.

**Why structured data generation is a separate phase:**
- The ontology describes what concepts "are"; structured data describes how downstream agents "use" them.
- Without structured data, the ontology is "descriptive but not consumable".

---

## Reference Files

| File | When to Read | Content |
|------|-------------|---------|
| `references/retrieval-agent.md` | Phase 1 | Multi-perspective retrieval + LLM content classification |
| `references/scoring-agent.md` | Phase 1 | 5-dim scoring + quality gates |
| **`references/ontology-construction-agent.md`** | **Phase 2** | **LLM ontology construction methodology** |
| **`resources/ontology-design-principles.md`** | **Phase 2** | **Ontology design principles** |
| `references/structured-data-generator.md` | Phase 3 | Ontology → structured data |
| `references/quality-verification-agent.md` | Phase 4 | 6-dim quality verification |
| `resources/parameter_pattern_library.md` | Phase 2 | Generic patterns for physical quantities |
| `resources/ontology_templates.md` | Phase 2 | Ontology output templates |
| `resources/integration_guide.md` | Integration | Consumer skill integration |
| `resources/scoring_rubric.md` | Phase 1 | Detailed scoring examples |
| `resources/indexing_guide.md` | KB expansion | KB expansion guide |

---


## Inputs / Outputs

### Inputs

| Input | Required | Description |
|------|----------|-------------|
| Domain query / keywords | ✓ | Domain query terms that drive retrieval |
| run_dir (consumer mode) | - | Output directory of the consumer skill |
| Reference documents | - | Local reference documents |
| RAG engine (localhost:8764) | - | ChromaDB retrieval engine |

### Outputs

| Output | Description |
|--------|-------------|
| 00_input/rag_ontology_draft.json | RAG ontology draft |
| 00_input/rag_ontology_nl_spec.md | Natural-language ontology spec |
| 00_input/rag_structured_data.json | Structured knowledge data |
| 00_input/rag_scored_chunks.json | Scored knowledge chunks |
| 00_input/rag_audit_log.json | RAG retrieval audit log |
| 00_input/rag_clarification_needed.json | Clarification requests |
| 00_input/rag_deep_understanding.json | RAG deep understanding result (consumed by context-builder) |

---

## Dispatch

Invoked by context-builder or standalone:

```bash
SKILL_PATH="<path-to-.claude/skills/rag-knowledge-builder>"
SHARED_PATH="<path-to-.claude/shared>"
uv run --project "$SHARED_PATH/scripts" python "$SKILL_PATH/scripts/rag_client.py" --query "<domain>" --run-dir "$RUN_DIR"
```

---

## Verification

```bash
# Check ontology output exists
test -f "$RUN_DIR/ontology.json"
# RAG engine health (optional)
uv run --project "$SHARED_PATH/scripts" python "$SKILL_PATH/scripts/rag_client.py" health || echo "RAG offline — fallback used"
```

## Pipeline Event Logging

```bash
node "$SHARED_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" \
  --event agent_complete --agent context-builder --step context_builder \
  --files 00_input/rag_deep_understanding.json
```

---

## Failure Recovery

| Scenario | Recovery |
|----------|----------|
| RAG engine down | Degrade to web_search + physics_inference_framework |
| No results from KB | Mark evidence_gap → use web research + LLM inference |
| Ontology build fail | Retry 1x → if still failing, output minimal ontology + warning |

---
## Data Truth Mandate

**Every number written into JSON/reports must be recomputable from the raw data.**
|Rule|Requirement|
|---|---|
|Number traceability|Every number must state the data source (cleaned/raw), row range, and computation method|
|Derived value marking|Inferred/derived values must be explicitly `"derived": true` or `"inferred": true`|
|Cleaning audit trail|cleaning_integrity records all cleaning operations|
|Visualization traceability|Every data point in every chart is traceable to a specific row of the dataset|
|Unavailable marking|What cannot be computed from the data → write NOT_APPLICABLE + reason|

## Counterfactual Reasoning — Exclusion Constraints

|Constraint|Description|
|---|---|
|Four conditions|Temporal precedence + statistical significance + physical mechanism + no contradiction|
|Exclusion standard|Any condition unmet → mark as an excluded candidate and provide quantitative grounds|
|Physical boundary|Exclusions must be supported by first principles or governing equations|
|Confidence threshold|Exclusion confidence <80 is marked `[WEAK_EXCLUSION]`|

## Assumptions & Limitations

|Category|Requirement|
|---|---|
|Data limitations|Sampling rate / noise / missing extremes / range limits|
|Model assumptions|Linear approximation / steady-state assumption / distribution assumptions|
|Uncontrolled confounders|Explicitly list potential confounding variables that cannot be controlled|
|Conclusion confidence interval|Each conclusion annotated with confidence ± error margin|

## Efficiency — Parallel Execution

- When there is no data dependency with upstream/downstream agents → parallelize proactively
- Use deterministic scripts instead of LLM reasoning for predictable results
- Large-file sampling strategy: systematic sampling when >100K rows
- Agent stall >600s → check existing artifacts; continue with partially available results

---

## Anti-Patterns (DO NOT)

- ❌ **DO NOT** classify concepts by keyword matching. The LLM must read the full content.
- ❌ **DO NOT** hardcode domain entities. The LLM dynamically identifies domain entities.
- ❌ **DO NOT** use vague definitions. "Temperature is the temperature value" is not a definition.
- ❌ **DO NOT** skip concept hierarchy construction. Every concept must have a `broader_concept`.
- ❌ **DO NOT** skip the natural-language spec. The NL Spec is one of the ontology's core outputs.
- ❌ **DO NOT** ignore rejected knowledge chunks. Every rejection must have a reason.
- ❌ **DO NOT** use `domain_type="generic"`. The LLM must identify the concrete domain.
- ❌ **DO NOT** fabricate definitions for UNKNOWN concepts. Honestly mark UNKNOWN.
- ❌ **DO NOT** add LLM calls in the Python engine. The LLM runs at the skill layer.
