# RAG Knowledge Builder — 自动领域本体构建引擎

从搜索收集到的知识自动构建高质量的领域本体模型。同时输出结构化 JSON（给机器消费）和自然语言 Markdown 规范（给人类审阅）。

## Quick Start

```bash
# Start the RAG engine
cd rag-retrieval-engine && uv sync && uv run python server.py &

# Build knowledge index
curl -X POST http://localhost:8765/index -H "Content-Type: application/json" -d '{}'

# Run full pipeline
uv run python scripts/rag_client.py build-ontology \
  --domain "BOPET biaxial film production" \
  --target-concepts "film_thickness_um,film_haze_pct" \
  --related-concepts "melt_temp_C,mdo_temp_C,tdo_temp_C,line_speed_m_min" \
  --output-dir /tmp/output
# → /tmp/output/00_input/rag_ontology_draft.json
# → /tmp/output/00_input/rag_ontology_nl_spec.md
```

## Architecture

```
Calling skill ──Skill()──►  rag-knowledge-builder (this skill)
                                │
                                ├── rag_client.py start    (auto-start engine)
                                └── rag_client.py build-ontology
                                            │
                              rag-retrieval-engine
                                ├── /retrieve  → ChromaDB + Web
                                ├── /score     → 5-dim quality gates
                                └── output → LLM-driven ontology construction
                                            │
                                            ├── rag_ontology_draft.json (structured)
                                            ├── rag_ontology_nl_spec.md (human-readable)
                                            ├── rag_structured_data.json (machine templates)
                                            └── rag_audit_log.json (quality verdict)
```

## Ontology Design Principles

The ontology produced by this skill must satisfy 6 natural language quality criteria:

| Principle | Description |
|-----------|-------------|
| 概念精确性 | 每个概念有精确、消歧义的自然语言定义 |
| 层次完整性 | IS-A 和 PART-OF 层次结构覆盖所有核心概念 |
| 关系语义丰富 | 关系有机制描述、方向、条件、例外、时滞 |
| 术语映射 | 每个概念关联同义词、缩写、跨语言术语 |
| 公理与约束 | 领域规则用自然语言明确表达 |
| 可追溯性 | 每个声明追溯到知识源，带置信度 |

See `resources/ontology-design-principles.md` for the full specification.

## Commands

| Command | Action |
|---------|--------|
| `rag_client.py start` | Auto-start RAG engine |
| `rag_client.py health` | Check engine status |
| `rag_client.py build-ontology` | Full collect → ontology → structured data |
| `rag_client.py retrieve-score` | Knowledge collection only |
| `rag_client.py web-search` | Standalone web search |

## Integration

Called by other skills via `Skill({skill: "rag-knowledge-builder", args: "..."})`.

Writes ontology draft + NL spec to `$RUN_DIR/00_input/`:
- `rag_ontology_draft.json` — structured ontology (for agents)
- `rag_ontology_nl_spec.md` — natural language spec (for humans)
- `rag_structured_data.json` — machine-consumable templates
- `rag_audit_log.json` — quality verification verdict

## License

MIT
