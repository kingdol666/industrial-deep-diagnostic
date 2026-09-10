# RAG Knowledge Builder Skill

This is an **ontology-first** knowledge-construction skill. Its goal is not simple retrieval, but organizing retrieved knowledge into a **domain ontology model that downstream skills can consume directly**.

## What This Skill Is For

Use this skill when the task requires:

- Building a domain ontology
- Forming a concept hierarchy and a relationship map
- Distilling structured knowledge from RAG retrieval results
- Providing domain-semantic support for downstream diagnostic/analysis skills

That is when you should use this skill.

## What This Skill Outputs

It emits a set of ontology-related artifacts:

- `rag_ontology_draft.json`: the structured ontology
- `rag_ontology_nl_spec.md`: the human-readable natural-language specification
- `rag_structured_data.json`: machine-consumption templates
- `rag_scored_chunks.json`: retrieved chunks and their scores
- `rag_audit_log.json`: the quality audit log
- `rag_clarification_needed.json`: concepts awaiting clarification

## Standard Execution Flow

### Phase 0: Engine Startup
- Start or health-check `rag-retrieval-engine`

### Phase 1: Knowledge Collection
- Local knowledge-base retrieval
- Optional web retrieval
- Scoring and triage of retrieved chunks

### Phase 2: Ontology Construction
- Domain understanding
- Concept definition
- Hierarchy construction
- Constraints and terminology mapping
- Output both the JSON and the Markdown version of the ontology

### Phase 3: Structured Data Generation
- Generate query templates, validation rules, and structured templates

### Phase 4: Quality Verification
- Check ontology completeness, consistency, traceability, and downstream usability

## Relationship to the Diagnostic Skills

This skill usually serves as:

- an upstream knowledge-construction module for `industrial-deep-diagnostic`
- or a standalone domain-knowledge preparation module

The relationship is:

```text
RAG Engine -> RAG Knowledge Builder Skill -> Industrial Deep Diagnostic Skill
```

## Advantages

- Ontology-first, rather than a "pile of search results"
- Outputs aimed at both machines and humans
- Serves as semantic infrastructure for multiple downstream skills
- Domain-agnostic; reusable across industrial, medical, legal, scientific-research, and other scenarios

## Typical Uses

- Building a domain ontology for industrial diagnosis
- Building terminology and relationship maps for complex question-answering systems
- Providing a concept dictionary and causal-semantic support for data-analysis systems

## Key Entry Points

- Main protocol: `SKILL.md`
- Output directory: usually written into `run_dir/00_input/`
- Engine service: see `rag-retrieval-engine/README.md`
