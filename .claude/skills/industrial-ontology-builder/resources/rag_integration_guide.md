# RAG Integration Guide — Runtime Knowledge Retrieval

> How the diagnostic skill calls the RAG engine at runtime to get structured domain knowledge.

## Quick Start (one-time setup)

```bash
# Terminal 1: Start the RAG engine (keep running)
cd rag-retrieval-engine
uv sync                            # One-time: install all deps into uv venv
uv run python server.py            # Start the engine
# → http://localhost:8764 (API docs at /docs)

# Build initial knowledge index (one-time)
curl -X POST http://localhost:8764/index -H "Content-Type: application/json" -d '{"rebuild": false}'
```

## How the diagnostic skill uses it

In Step 2 (context-builder), the agent automatically calls the RAG engine API:

```
Step 1:  Inspect data → know the column names + types
   ↓
Step 2:  context-builder agent
   ├── Step 2.0: Delegate to rag-knowledge-builder skill
   │   Uses: Skill({skill: "rag-knowledge-builder", args: "..."})
   │   Skill internally calls RAG engine or falls back to local scripts
   │   Output: rag_ontology_draft.json written to $RUN_DIR/00_input/
   │
   ├── Step 2.1: Load RAG ontology draft
   │   Merge with extracted_knowledge.json
   │
   └── Step 3: Build/validate final ontology.json
```

## Verification

```bash
# Check if engine is running
curl -s http://localhost:8764/health | uv run --project "$SHARED_PATH/scripts" python -m json.tool

# Expected output:
# {
#   "status": "healthy",
#   "version": "1.0.0",
#   "kb_ready": true,
#   "total_chunks": 63,
#   ...
# }
```

## Fallback Behavior

If the RAG engine is not running when the diagnostic skill runs:
- The skill logs a warning: "RAG engine unavailable — building ontology from scratch"
- context-builder falls back to its original behavior (user docs + web search + auto-inference)
- The diagnostic pipeline continues normally — RAG is an acceleration, not a hard dependency

## Supported Scenarios

The RAG engine works for ANY industrial process — the `scenario` parameter is a free-form text description, not a fixed enum. Examples:
- "CNC machining with spindle vibration"
- "cement rotary kiln clinker production"
- "paper machine wet end chemistry control"
- "semiconductor etch chamber plasma process"
- "food spray drying with thermal degradation"
