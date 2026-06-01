# RAG Retrieval Engine

Standalone HTTP microservice for industrial knowledge retrieval, scoring, and ontology injection.

```
Skill (rag_client.py)  ──HTTP──►  RAG Engine (FastAPI)
                                  ├── /retrieve   ChromaDB + web
                                  ├── /score      5-dim scoring
                                  ├── /inject     Ontology builder
                                  ├── /health
                                  └── /pipeline/full (one-shot)
```

## Quick Start

```bash
# 1. Install
cd rag-retrieval-engine
pip install -r requirements.txt

# 2. Start server
python server.py
# → Uvicorn running on http://0.0.0.0:8765

# 3. Check health
curl http://localhost:8765/health
# → {"status":"healthy","kb_ready":false,...}

# 4. Index knowledge (first time)
curl -X POST http://localhost:8765/index \
  -H "Content-Type: application/json" \
  -d '{}'

# 5. Run full pipeline
curl -X POST http://localhost:8765/pipeline/full \
  -H "Content-Type: application/json" \
  -d '{
    "scenario": "CNC machining",
    "target_columns": ["surface_roughness_Ra_um", "thermal_deviation_mm"],
    "parameter_columns": ["spindle_vibration_mm_s", "spindle_temp_C", "tool_age_parts"],
    "group_columns": ["material", "tool_id"],
    "mode": "hybrid",
    "top_k": 5
  }'

# 6. Or use the client from the skill
cd ../.claude/skills/rag-knowledge-builder
python scripts/rag_client.py pipeline \
  --scenario "CNC machining" \
  --target-cols "surface_roughness_Ra_um,thermal_deviation_mm" \
  --param-cols "spindle_vibration_mm_s,spindle_temp_C,tool_age_parts" \
  --output-dir /tmp/rag_output
```

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Service health + KB status |
| POST | `/retrieve` | Multi-query knowledge retrieval |
| POST | `/score` | 5-dimension relevance scoring |
| POST | `/inject` | Ontology draft construction |
| POST | `/pipeline/full` | Retrieve→Score→Inject in one call |
| POST | `/index` | Build/rebuild knowledge index |
| POST | `/accumulate` | Add verified diagnosis to KB |
| GET | `/runs` | List retrieval runs |
| GET | `/runs/{id}` | Get run metadata |
| GET | `/runs/{id}/result/{type}` | Get run result |
| GET | `/stats` | Storage + KB statistics |

## Architecture

```
┌─────────────────────────────────────────────────┐
│                  FastAPI Server                 │
│                   (server.py)                   │
├─────────────────────────────────────────────────┤
│  POST /retrieve    POST /score   POST /inject   │
│       │                │              │          │
│       ▼                ▼              ▼          │
│  ┌──────────┐   ┌───────────┐  ┌──────────┐    │
│  │Retriever │   │  Scorer   │  │Injector  │    │
│  │ChromaDB  │   │5-dim gate │  │Schema    │    │
│  │+ web     │   │≥0.65 pass│  │Injection │    │
│  └────┬─────┘   └─────┬─────┘  └────┬─────┘    │
│       │               │              │          │
│       └───────────────┴──────────────┘          │
│                       │                         │
│                       ▼                         │
│              ┌─────────────────┐                │
│              │  StorageManager │                │
│              │  SQLite + JSON  │                │
│              └─────────────────┘                │
└─────────────────────────────────────────────────┘
```

## Configuration

Edit `config.yaml` to customize:
- `server.port` — HTTP port (default: 8765)
- `knowledge_base.index_sources` — source documents to index
- `scoring.weights` — D1-D5 dimension weights
- `scoring.pass_threshold` — minimum composite score
- `storage.retention_days` — auto-cleanup old runs

## License

MIT
