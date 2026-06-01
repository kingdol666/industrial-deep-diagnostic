# RAG Knowledge Builder

A pluggable RAG engine for industrial diagnostic scenarios. Retrieves domain knowledge from local vector DB and web search, scores relevance with 5-dimensional metrics, and builds structured ontology drafts for downstream diagnostic agents.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Initialize knowledge base (one-time)
python scripts/kb_build.py --init --skill-path ../industrial-deep-diagnostic

# 3. Retrieve knowledge for a diagnostic scenario
python scripts/kb_retrieve.py \
  --scenario "CNC machining" \
  --target-cols "surface_roughness_Ra_um,thermal_deviation_mm" \
  --param-cols "spindle_vibration_mm_s,spindle_temp_C,tool_age_parts" \
  --mode hybrid \
  --output /tmp/results.json

# 4. Score relevance
python scripts/kb_score.py \
  --input /tmp/results.json \
  --context /tmp/context.json \
  --output /tmp/scored.json

# 5. Build ontology draft
python scripts/kb_inject.py \
  --scored /tmp/scored.json \
  --manifest input_manifest.json \
  --output ontology_draft.json
```

## Architecture

```
Knowledge Sources         Retrieval          Scoring          Output
─────────────────     ──────────────     ─────────────     ─────────────
Local references  ──┐
(static KB)         │   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
                     ├──►│ kb_retrieve  │──►│  kb_score    │──►│  kb_inject   │
Web search       ───┘   │ 4-perspective│   │ 5-dimension  │   │ Schema-driven│
(open-websearch)       │ multi-query  │   │ scoring      │   │ ontology     │
                     │               │   │ gate: ≥0.65  │   │ injection    │
Verified past       ──►│               │   │               │   │               │
diagnoses (high      │               │   │               │   │               │
confidence only)     └──────────────┘   └──────────────┘   └──────────────┘
```

## Scoring Metrics

| Dimension | Weight | What It Measures |
|-----------|:------:|------------------|
| D1 Semantic Relevance | 30% | Content-to-context embedding similarity |
| D2 Parameter Match | 25% | Column names appearing in knowledge chunk |
| D3 Scenario Consistency | 20% | Process type tag matching |
| D4 Source Credibility | 15% | local_reference(10) > web_authoritative(6) > web_general(3) |
| D5 Cross-Reference Count | 10% | Independent source confirmations |

## Integration

Designed to plug into `industrial-deep-diagnostic` Step 2 — inject `ontology_draft.json` before context-builder runs. See `resources/integration_guide.md` for details.

## License

MIT
