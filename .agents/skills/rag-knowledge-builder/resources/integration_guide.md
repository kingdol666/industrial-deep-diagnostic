# RAG Knowledge Builder — Integration Guide

> How a consumer skill calls this skill to obtain a domain ontology.

## Integration Pattern: Skill-to-Skill Invocation

The context-builder of a consumer skill calls:

```
Skill({
  skill: "rag-knowledge-builder",
  args: "domain='<free-text>' target_concepts='<csv>' related_concepts='<csv>' context_dimensions='<csv>' run_dir='<path>' interaction_mode='auto'"
})
```

| Parameter | Required | Source in consumer skill | Example |
|-----------|:--------:|-------------------------|---------|
| `domain` | Yes | Domain description, or built automatically from column-name patterns | `biaxial PET film stretching with thickness control` |
| `target_concepts` | Yes | Quality target columns | `thickness_um,haze_pct` |
| `related_concepts` | Yes | All numeric predictor variables | `mdo_temp_C,tdo_temp_C,line_speed_m_min` |
| `context_dimensions` | Yes | Categorical columns used for stratification | `product_grade,material_batch` |
| `run_dir` | Yes | Pipeline run directory | `/path/to/runs/20260602_xxx` |
| `interaction_mode` | No | Defaults to `auto` | `auto` |

## Files Exchanged

| From RAG Builder (write) | → | To Consumer Skill (read) | Purpose |
|--------------------------|---|--------------------------|---------|
| `rag_ontology_draft.json` | → | `00_input/rag_ontology_draft.json` | **Structured ontology** — concept definitions, hierarchy, relationships, constraints, terminology |
| `rag_ontology_nl_spec.md` | → | `00_input/rag_ontology_nl_spec.md` | **Natural-language specification** — human-readable ontology design document |
| `rag_structured_data.json` | → | `00_input/rag_structured_data.json` | Machine-consumable template — examples, validation rules, query templates |
| `rag_scored_chunks.json` | → | `00_input/rag_scored_chunks.json` | Knowledge chunks (5-dimension scoring + classification) |
| `rag_clarification_needed.json` | → | `00_input/clarification_needed.json` | Concepts that need user clarification |
| `rag_audit_log.json` | → | `00_input/rag_audit_log.json` | Quality verification results |

## Ontology Output Format v4 (Ontology-First)

### Structured JSON Output

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
└── rag_construction_metadata: { ... }
```

### Key New Fields (vs v3)

| Field | Description |
|------|------|
| `definition` | Precise natural-language definition (new in v4, replaces `semantic_meaning` from v3) |
| `broader_concept` | IS-A parent concept (hierarchy completeness) |
| `sibling_concepts` | Sibling concepts (disambiguation) |
| `distinguish_from` | How it differs from similar concepts |
| `terminology{}` | Terminology mapping: synonyms, abbreviations, cross-language, contextual aliases |
| `abnormal_indicates` | What problem an abnormal value indicates |
| `conditions` | Preconditions under which the relationship holds |
| `exceptions` | Exception cases in which the relationship does not hold |
| `constraints[]` | Domain constraints and rules (new top-level field) |

### Natural-Language Specification (NL Spec)

`rag_ontology_nl_spec.md` contains:
1. Domain overview (definition, boundaries)
2. Core entities (roles, lifecycle, interactions)
3. Concept dictionary (definition, hierarchy, disambiguation, terminology mapping for every concept)
4. Relationship map (mechanism, conditions, exceptions, time lag)
5. Axioms and constraints
6. Confounders
7. Process / logical stages
8. Knowledge gaps
9. Construction metadata

> **Output language**: The rendered `rag_ontology_nl_spec.md` must be written in the configured output language (default: Chinese — see the Language Default section of `SKILL.md`); the section titles above are listed in English here for reference only.

## How the Consumer Skill Consumes the Output

### Context Builder: Loading and Mapping

1. Read `rag_ontology_draft.json` → map `definition` to parameter descriptions, `expected_value_range` to ranges, and `constraints` to validation rules
2. Read `rag_ontology_nl_spec.md` → gives downstream LLM agents the domain context
3. Read `rag_structured_data.json` → extract validation rules and query templates
4. Merge `rag_clarification_needed.json` into its own unknowns

### Using Terminology Mapping

Every concept in the ontology has a `terminology` field. A consumer agent can:
- Look up a concept by any alias (data column name, abbreviation, Chinese name)
- Reference concepts across languages
- Use different names in different contexts

### Fallback Chain

```
1. Try: Skill("rag-knowledge-builder", ...)
   ↓ FAILED
2. Try: Pre-generated rag_ontology_draft.json in 00_input/
   ↓ NOT FOUND
3. Fallback: Build ontology from scratch (context-builder steps)
```

RAG is an accelerator, not a hard dependency.

## First-Time Setup

```bash
# Terminal 1: Start RAG engine
cd rag-retrieval-engine && uv sync && uv run python server.py &
# → http://localhost:8764

# One-time: Build initial knowledge index
curl -X POST http://localhost:8764/index -H "Content-Type: application/json" -d '{"rebuild": false}'

# Verify
curl -s http://localhost:8764/health
```
