# RAG Knowledge Builder

A pluggable RAG skill for industrial diagnostic scenarios. Called via `Skill()` tool from `industrial-deep-diagnostic` context-builder agent, or used standalone to build knowledge ontology from ChromaDB + web search.

## Quick Start

```bash
# Start the RAG engine
cd rag-retrieval-engine && uv sync && uv run python server.py &

# Build knowledge index
curl -X POST http://localhost:8765/index -H "Content-Type: application/json" -d '{}'

# Run full pipeline (retrieve + score + inject)
uv run python scripts/rag_client.py pipeline \
  --scenario "CNC machining" \
  --target-cols "surface_roughness_Ra_um,thermal_deviation_mm" \
  --param-cols "spindle_vibration_mm_s,spindle_temp_C,tool_age_parts" \
  --output-dir /tmp/output
# → /tmp/output/00_input/rag_ontology_draft.json
```

## Architecture

```
Calling skill ──Skill()──►  rag-knowledge-builder skill (this skill)
                                │
                                ├── rag_client.py start    (auto-start engine)
                                └── rag_client.py pipeline  (POST /pipeline/full)
                                                              │
                                        rag-retrieval-engine  │
                                          ├── /retrieve  → ChromaDB + DuckDuckGo
                                          ├── /score     → 5-dimension quality gates
                                          └── /inject    → Schema-driven ontology build
```

## Commands

| Command | Action |
|---------|--------|
| `rag_client.py start` | Auto-start RAG engine (if not running) |
| `rag_client.py health` | Check engine status |
| `rag_client.py pipeline` | Full retrieve + score + inject |
| `rag_client.py web-search` | Standalone web search (DuckDuckGo) |

## Scoring Metrics

| Dimension | Weight | What It Measures |
|-----------|:------:|------------------|
| D1 Semantic Relevance | 30% | Content-to-context embedding similarity |
| D2 Parameter Match | 25% | Column names appearing in knowledge chunk |
| D3 Scenario Consistency | 20% | Process type tag matching (word-overlap based) |
| D4 Source Credibility | 15% | local_reference(10) > web_authoritative(6) > web_general(3) |
| D5 Cross-Reference Count | 10% | Independent source confirmations |

## Integration

Designed to be called by `industrial-deep-diagnostic` context-builder via `Skill({skill: "rag-knowledge-builder", args: "..."})`. Writes ontology draft to `$RUN_DIR/00_input/rag_ontology_draft.json`.

## License

MIT
