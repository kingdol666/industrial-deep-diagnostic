# RAG Knowledge Builder — Integration Guide

> How consumer skills (like `industrial-deep-diagnostic`) invoke this skill to get structured domain knowledge.

## Integration Pattern: Skill-to-Skill Invocation

Consumer skills invoke this skill via the `Skill` tool. The context-builder agent calls:

```
Skill({
  skill: "rag-knowledge-builder",
  args: "domain='<free-text>' target_concepts='<csv>' related_concepts='<csv>' context_dimensions='<csv>' run_dir='<path>' interaction_mode='auto'"
})
```

| Parameter | Required | Source in diagnostic skill | Example |
|-----------|:--------:|---------------------------|---------|
| `domain` | Yes | `PROCESS_DESCRIPTION` or auto-constructed from column name patterns | `domain='biaxial PET film stretching with thickness control'` |
| `target_concepts` | Yes | Quality target columns from data inspection | `target_concepts='thickness_um,haze_pct'` |
| `related_concepts` | Yes | All numeric predictors minus targets and metadata | `related_concepts='mdo_temp_C,tdo_temp_C,line_speed_m_min'` |
| `context_dimensions` | Yes | Categorical columns for stratification | `context_dimensions='product_grade,material_batch'` |
| `run_dir` | Yes | Pipeline run directory (writes to `$run_dir/00_input/`) | `run_dir='/path/to/workspace/runs/20260602_xxx'` |
| `interaction_mode` | No | Default `auto` — matches diagnostic's interaction mode | `interaction_mode='auto'` |

## Files Exchanged

| From RAG Builder (write) | → | To Diagnostic Skill (read) | Purpose |
|--------------------------|---|---------------------------|---------|
| `rag_ontology_draft.json` | → | `00_input/rag_ontology_draft.json` | Structured domain ontology — entities, concepts with semantic meanings, causal relationships, confounders |
| `rag_structured_data.json` | → | `00_input/rag_structured_data.json` | Machine-consumable templates — sample data rows, validation bounds, query templates, prompt templates |
| `rag_scored_chunks.json` | → | `00_input/rag_scored_chunks.json` | Raw scored knowledge chunks — for evidence tracing and provenance |
| `rag_clarification_needed.json` | → | **MERGED INTO** `00_input/clarification_needed.json` | Concepts with UNKNOWN semantic meaning — merged with diagnostic's own unknowns |
| `rag_audit_log.json` | → | `00_input/rag_audit_log.json` | Quality verdict + provenance + rejection reasons — consumed by Judge for knowledge quality awareness |

**Critical**: RAG writes `rag_clarification_needed.json`. The diagnostic context-builder MUST merge any unresolved concepts from this file into the diagnostic's own `clarification_needed.json` before proceeding to Step 2.5.

## Output Format (v3 Universal)

The RAG builder produces a **domain-agnostic** ontology. Field names are generic — they describe roles that apply to any domain:

```
rag_ontology_draft.json
├── scene: { name, domain_type, domain_summary, primary_outcomes[] }
├── entities[]: { id, name, type, function, role_in_domain, key_attributes[] }
├── concepts:
│   ├── target_concepts[]: { name, semantic_meaning, confidence, concept_type, unit, expected_value_range }
│   ├── related_concepts[]: { name, semantic_meaning, confidence, concept_type, unit, expected_value_range }
│   └── context_dimensions[]: { name, semantic_meaning, confidence, cardinality }
├── process_or_logic_stages[]: { id, name, order, function, key_entity_ids, key_concept_ids }
├── relationships[]: { from, to, type, mechanism, direction, expected_lag, knowledge_confidence }
├── confounders[]: { name, type, reasoning, expected_impact }
└── rag_injection_metadata: { chunks reviewed, accepted, rejected, match_rate, knowledge_gaps[] }
```

**For backward compatibility**, the schema also accepts legacy field names:
- `signals.inspection_signals[]` → alias for `concepts.target_concepts[]`
- `signals.process_parameters[]` → alias for `concepts.related_concepts[]`
- `equipment[]` → alias for `entities[]`

**Consumer skills should use the new universal field names.** The diagnostic skill's field mapping in `context-builder.md` Step 2.1 handles both formats.

## How the Diagnostic Skill Consumes the Output

### Step 2.1 (Context Builder): Load and Map

1. Read `rag_ontology_draft.json` → extract `concepts.target_concepts[]` and `concepts.related_concepts[]` → map `semantic_meaning` to parameter `physical_meaning`, `expected_value_range` to `normal_range`, `semantic_meaning_confidence` to `physical_meaning_confidence`
2. Read `rag_structured_data.json` → extract `validation_rules[]` → use as plausibility bounds for parameter range checks; extract `sample_data_templates[]` → populate initial ontology `expected_data_behavior` fields
3. Read `rag_scored_chunks.json` → extract HIGH-scored chunks → cross-reference with `extracted_knowledge.json`
4. Read `rag_audit_log.json` → note `match_rate` (low = knowledge sparse), document `chunks_rejected_reasons`, record LLM confidence
5. Merge `rag_clarification_needed.json` into diagnostic's `clarification_needed.json`

### Step 5 (Judge): Knowledge Quality Awareness

The Judge reads `rag_audit_log.json` to understand:
- How many chunks were reviewed vs accepted vs rejected
- What the LLM's confidence in its ontology construction was
- Whether knowledge coverage was sparse (`match_rate < 0.3`)

This informs the "Evidence-Based Conclusions" scoring criterion — conclusions based on low-match-rate RAG knowledge get reduced confidence.

### Step 7 (Report Reviewer): RAG Knowledge Cross-Check

The Reviewer reads `rag_deep_understanding.json` (which incorporates RAG knowledge) to cross-check the diagnosis against extracted physics principles and validated RAG claims.

## Fallback Chain

```
1. Try: Skill("rag-knowledge-builder", ...)
   ↓ FAILED (skill not available / engine unreachable / error)
2. Try: Pre-generated rag_ontology_draft.json in 00_input/
   ↓ NOT FOUND
3. Fallback: Build ontology from scratch (context-builder steps)
```

RAG is an acceleration, not a hard dependency.

## First-Time Setup

```bash
# Terminal 1: Start RAG engine (keep running)
cd rag-retrieval-engine && uv sync && uv run python server.py &
# → http://localhost:8765 (API docs at /docs)

# One-time: Build initial knowledge index
curl -X POST http://localhost:8765/index -H "Content-Type: application/json" -d '{"rebuild": false}'

# Verify
curl -s http://localhost:8765/health
# → {"status":"healthy","kb_ready":true,"total_chunks":63}
```
