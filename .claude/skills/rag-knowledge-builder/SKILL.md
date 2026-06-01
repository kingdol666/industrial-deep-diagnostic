---
name: rag-knowledge-builder
description: "RAG-powered knowledge retrieval and ontology construction engine for industrial diagnostic scenarios. Retrieves domain knowledge from local vector DB (ChromaDB) and web search, scores relevance with 5-dimensional metrics, and builds structured ontology drafts consumable by downstream diagnostic agents. Triggers on: 构建知识图谱, 知识检索, 本体构建, 从文档提取参数, RAG search, knowledge retrieval, ontology construction. Use as a pre-step before industrial-deep-diagnostic. Do NOT trigger for: simple file search, generic web questions, non-industrial contexts."
compatibility: |
  Requires Python 3.10+ with uv venv for ChromaDB + sentence-transformers embeddings.
  Network access required for web retrieval mode. Can run offline with local KB only.
  Node.js 18+ for schema validation (optional — Python fallback available).
---

# RAG Knowledge Builder — Industrial Ontology Engine

## Core Principle

**Every structured knowledge claim MUST be traceable to a source, scored for relevance, and cross-referenced against at least one other dimension.** This skill does not retrieve blindly — it retrieves → scores → filters → constructs. Only knowledge chunks that pass all quality gates are used to build the ontology.

## Invocation Protocol — How Other Skills Call This Skill

This skill is designed to be invoked by the `context-builder` agent of `industrial-deep-diagnostic`, but can be called by any skill. The calling skill uses the `Skill` tool:

```
Skill({
  skill: "rag-knowledge-builder",
  args: "scenario='<description>' target_cols='<csv>' param_cols='<csv>' group_cols='<csv>' run_dir='<path>' interaction_mode='auto'"
})
```

**Parameters accepted in `args` string:**

| Parameter | Required | Format | Example |
|-----------|:--------:|--------|---------|
| `scenario` | Yes | Free-text description | `CNC machining spindle bearing degradation` |
| `target_cols` | Yes | Comma-separated column names | `surface_roughness_Ra_um,thermal_deviation_mm` |
| `param_cols` | Yes | Comma-separated column names | `spindle_vibration_mm_s,spindle_temp_C,tool_age_parts` |
| `group_cols` | Yes | Comma-separated column names | `material,tool_id` |
| `run_dir` | Yes | Absolute path | `/path/to/workspace/diagnostic-runs/xxx` |
| `interaction_mode` | No | `auto` (default) / `interactive` / `minimal` | `auto` |

**Output contract:**
- On success: writes `$run_dir/00_input/rag_ontology_draft.json`
- The ontology draft contains: `scene`, `signals` (classified by role), `relationships` (causal chains), `confounders`, `equipment`, `rag_injection_metadata` (match rate, confidence scores, gaps)
- On failure: logs errors; calling skill falls back to building ontology from scratch

**Execution flow (internal to this skill):**
1. Parse args → extract scenario, column lists, run_dir
2. Map `run_dir` → `--output-dir` for rag_client.py
3. **Auto-start engine**: call `python scripts/rag_client.py start`
   - Checks `GET /health` — if engine is running, returns immediately
   - If not running, auto-starts `rag-retrieval-engine` via `uv run python server.py` and waits up to 30s for readiness
   - If startup succeeded: proceed to Step 4
   - If startup failed (timeout or error): log warning, proceed to Step 5 (fallback)
4. If engine up: call `python scripts/rag_client.py pipeline --scenario "$scenario" --target-cols "$target_cols" --param-cols "$param_cols" --output-dir "$run_dir"` → HTTP API → retrieve+score+inject in one call
5. If engine down or auto-start failed: fall back directly — create a minimal ontology draft from column name heuristics and known parameter-to-physics patterns, then save to `$run_dir/00_input/rag_ontology_draft.json`
6. Verify `$run_dir/00_input/rag_ontology_draft.json` was created
7. Return success/failure status

## When to Use This Skill

Use before any industrial diagnostic pipeline execution, specifically:
- **Before Step 2 (Context Builder)** of `industrial-deep-diagnostic` — the context-builder agent invokes this skill to pre-fill ontology with retrieved knowledge
- **Standalone** — to index and query a domain knowledge base without running a full diagnosis
- **As a modular RAG plugin** — any skill can call this skill via the `Skill` tool with the parameters listed above

## Loading Guide

This skill uses progressive loading. Read only what each step needs:

| When | Read | Why |
|------|------|-----|
| Invoked by another skill | This file (SKILL.md) §Invocation Protocol | Parameter contract + execution flow |
| Retrieving knowledge | `agents/retrieval-agent.md` | Multi-query construction + result ranking |
| Scoring relevance | `agents/scoring-agent.md` | 5-dimension scoring rubric |
| Building ontology | `agents/ontology-builder.md` | Schema-driven extraction + knowledge injection |
| Integration setup | `resources/integration_guide.md` | How to connect to diagnostic skill |
| Building KB index | `resources/indexing_guide.md` | Chunking strategy + metadata design |
| Scoring examples | `resources/scoring_rubric.md` | Detailed scoring examples + edge cases |
| Ontology templates | `resources/ontology_templates.md` | Per-scenario extraction schemas |

**Do NOT load everything upfront.** Each agent prompt is self-contained — read it only when that pipeline phase begins. The diagnostic skill's schema definitions (`industrial-deep-diagnostic/schemas/*.json`) are the authoritative schema reference for ontology structure validation.

---

## Pipeline Overview

```
                  ┌──────────────────────────────────────────┐
                  │     RAG KNOWLEDGE BUILDER PIPELINE       │
                  └──────────────────────────────────────────┘

Phase 0: Preparation
  ├── kb_build.py --init          ← One-time: index static resources
  └── kb_build.py --verify        ← Verify KB integrity

Phase 1: Retrieval (parallel)
  ├── kb_retrieve.py --local      ← ChromaDB semantic search
  └── kb_retrieve.py --web        ← open-websearch + structured extraction

Phase 2: Scoring & Filtering
  └── kb_score.py                 ← 5-dimension scoring + gate

Phase 3: Ontology Construction
  └── kb_inject.py                ← Schema-driven knowledge → ontology draft

Phase 4: Quality Verification
  └── Quality Gate                ← Score threshold + cross-reference check
```

---

## Phase 0: Initialize Knowledge Base

### One-time setup (run before first use)

```bash
# Prerequisite: uv is auto-installed by diagnostic skill's uv_env_setup.mjs.
# If running standalone, install uv first: curl -LsSf https://astral.sh/uv/install.sh | sh

# --- RAG Engine ---
cd rag-retrieval-engine
uv sync                              # One-time: install all deps in uv venv
uv run python server.py &            # Start the engine (background)

# --- Knowledge Index ---
# Build the initial knowledge index (via engine API)
curl -X POST http://localhost:8765/index -H "Content-Type: application/json" -d '{}'

# --- Verify ---
curl -s http://localhost:8765/health
```

**What gets indexed (initially):**
- Diagnostic skill's `resources/process_knowledge_base.md` → chunked by process type
- Diagnostic skill's `resources/parameter_to_physics.json` → each causal_chain as one hyperedge chunk
- Diagnostic skill's `resources/evidence_rules.md` → evidence hierarchy rules
- Diagnostic skill's `resources/diagnosis_method.md` → diagnostic methodology

**After the first diagnostic run:** The engine accumulates verified findings automatically when `POST /accumulate` is called with a high-confidence diagnostic run directory.

---

## Phase 1-3: Retrieval + Scoring + Injection (via Engine API)

The Skill calls `scripts/rag_client.py pipeline` which sends a single HTTP request to the RAG engine. The engine handles retrieval (4-perspective multi-query → ChromaDB), scoring (5-dimension gate), and injection (schema-driven ontology builder) as one atomic pipeline call.

**For standalone use (not invoked by another skill):**

```bash
uv run python scripts/rag_client.py pipeline \
  --scenario "your process description" \
  --target-cols "quality_col_1,quality_col_2" \
  --param-cols "param_col_1,param_col_2,..." \
  --output-dir /path/to/output
```

**Key design principles** (detailed in agent files):
- **Retrieval**: 4-perspective queries auto-generated from column names. Local ChromaDB + Web (via open-websearch daemon)
- **Scoring**: 5-dimension relevance evaluation with quality gates (≥8.5 CRITICAL, ≥7.0 ACCEPTED, ≥6.5 CONDITIONAL, rest REJECTED)
- **Injection**: Schema-driven mapping of scored chunks to ontology fields

### Scoring & Quality Gate Details

The 5-dimension scoring rubric and quality gate logic lives in `agents/scoring-agent.md` and is executed by the RAG engine (rag-retrieval-engine). Key metrics:
- Composite: `D1×0.30 + D2×0.25 + D3×0.20 + D4×0.15 + D5×0.10`
- Tiers: ≥8.5 CRITICAL / ≥7.0 ACCEPTED / ≥6.5 CONDITIONAL / <6.5 REJECTED
- Auto-reject: D1<3.0 / D4<3.0 / (D2<4.0 AND D3<5.0) / web singleton

### Ontology Injection

The engine's `engine/injector.py` maps scored chunks to the diagnostic skill's `ontology_schema.json` v6.2. Each injection is traceable to its source chunk via `knowledge_source` and `injected_from_chunk` fields. See `agents/ontology-builder.md` for the full mapping specification.

---

## Commands

| Command | Action |
|---------|--------|
| `/rag-knowledge-builder init` | Initialize KB: index all static resources via engine API |
| `/rag-knowledge-builder retrieve` | Retrieval + Scoring + Injection (full pipeline) |
| `/rag-knowledge-builder search <query>` | Ad-hoc semantic search via engine API |
| `/rag-knowledge-builder verify` | Verify KB integrity and knowledge coverage |
| `/rag-knowledge-builder inject <run_dir>` | Inject knowledge into an existing diagnostic run |

---

## Integration with industrial-deep-diagnostic

### How the diagnostic skill calls this skill

The context-builder agent uses `Skill({skill: "rag-knowledge-builder", args: "..."})`. Internally this skill calls `uv run python scripts/rag_client.py pipeline` which sends a single HTTP POST to the RAG engine. The engine handles all backend logic and writes `rag_ontology_draft.json` to the diagnostic workspace.

### Files exchanged between skills

| From RAG Builder | → | To Diagnostic Skill | Purpose |
|------------------|---|---------------------|---------|
| `ontology_draft.json` | → | `01_ontology/` | Pre-fill ontology for LLM review |
| `scored_chunks.json` | → | `Diagnostician Phase 0` | Physical mechanisms for evidence fusion |
| `knowledge_gaps.json` | → | `context-builder Step 2.5` | Parameters requiring clarification |
| `retrieval_results.json` | → | `Report Section 6` | External knowledge provenance |

---

## Commands

| Command | Action |
|---------|--------|
| `/rag-knowledge-builder init` | Initialize KB: index all static resources |
| `/rag-knowledge-builder retrieve` | Retrieval + Scoring + Injection (full pipeline) |
| `/rag-knowledge-builder web-search <keywords>` | **Search the web** for knowledge (DuckDuckGo HTML, no API key) |
| `/rag-knowledge-builder verify` | Verify KB integrity and knowledge coverage |
| `/rag-knowledge-builder inject <run_dir>` | Inject knowledge into an existing diagnostic run |

---

## Web Search

The skill supports **live web search** via the `rag-retrieval-engine` (DuckDuckGo HTML fallback, no API key needed). When invoked with `--use-web` or with `mode: "hybrid"`, the retriever searches both the local ChromaDB KB and the live web.

**How web results are handled:**
1. Web results are normalized into the same KnowledgeChunk format as local results
2. They pass through the same 5-dimension scoring pipeline (D1 semantic relevance, D2 parameter match, etc.)
3. Because web results lack pre-computed embeddings and have lower source credibility, they score lower than local KB results — only genuinely relevant, authoritative web chunks pass the quality gates
4. Web chunks from authoritative domains (.edu, .gov, wikipedia, iso.org) receive D4 (source credibility) boost

**Trigger methods:**
- `uv run python scripts/rag_client.py pipeline --use-web ...` — hybrid local+web
- `uv run python scripts/rag_client.py web-search --keywords "cement kiln temperature free lime"` — standalone web search
- Pipeline mode="web_only" in the engine API — web-only retrieval

## Reference Files

| File | When to Read | Content |
|------|-------------|---------|
| `agents/retrieval-agent.md` | Phase 1 | Multi-query retrieval instructions |
| `agents/scoring-agent.md` | Phase 2 | 5-dimension scoring rubric |
| `agents/ontology-builder.md` | Phase 3 | Schema-driven knowledge injection |
| `resources/scoring_rubric.md` | Phase 2 | Detailed scoring examples + edge cases |
| `resources/ontology_templates.md` | Phase 3 | Pre-defined extraction templates per scenario |
| `resources/indexing_guide.md` | Phase 0 | Chunking strategy + metadata design |
| `resources/integration_guide.md` | Before diagnosing | How to connect to diagnostic skill |
| `resources/scoring_rubric.md` | Phase 2 | Detailed scoring examples + edge cases |
| `resources/ontology_templates.md` | Phase 3 | Pre-defined extraction templates per scenario |
