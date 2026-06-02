# RAG Knowledge Builder — 自动领域本体构建引擎

从搜索收集到的知识自动构建高质量的领域本体模型。同时输出结构化 JSON（给机器消费）和自然语言 Markdown 规范（给人类审阅）。

## 核心特性

- **本体优先**：不是检索引擎+附赠本体，而是本体构建引擎+检索基础设施
- **自然语言设计**：每个概念有精确定义、层次分类、消歧义、术语映射
- **关系语义丰富**：每条关系有机制描述、条件、例外、时滞
- **双输出格式**：JSON（机器消费）+ Markdown（人类审阅）
- **领域无关**：适用于任何知识领域——工业、医学、法律、金融、科研、教育等

## Quick Start

```bash
# Start the RAG engine
cd rag-retrieval-engine && uv sync && uv run python server.py &

# Build knowledge index
curl -X POST http://localhost:8765/index -H "Content-Type: application/json" -d '{}'

# Run full pipeline (retrieve + ontology + structured data + verify)
uv run python scripts/rag_client.py build-ontology \
  --domain "BOPET biaxial film production with thickness and haze control" \
  --target-concepts "thickness_um,haze_pct" \
  --related-concepts "melt_temp_C,MDO_temp_C,TDO_temp_C,line_speed_m_min" \
  --output-dir /tmp/output
# → /tmp/output/00_input/rag_ontology_draft.json (结构化本体)
# → /tmp/output/00_input/rag_ontology_nl_spec.md (自然语言规范)
```

## Architecture

```
Consumer Skill ──Skill()──►  rag-knowledge-builder
                                │
                                ├── Phase 1: Knowledge Collection (engine)
                                │     4-perspective retrieval × (ChromaDB + Web)
                                │     5-dim scoring + LLM triaging
                                │
                                ├── Phase 2: Ontology Construction ★ CORE ★ (LLM)
                                │     Concept definitions + hierarchy
                                │     Relationship semantics + conditions
                                │     Entity roles + lifecycle
                                │     Constraints + terminology mapping
                                │     → JSON + Markdown (NL Spec)
                                │
                                ├── Phase 3: Structured Data Generation (LLM)
                                │     Sample data + validation rules
                                │     Causal queries + prompt templates
                                │
                                └── Phase 4: Quality Verification (LLM)
                                      8-dim quality gate
                                      → audit log with verdict
```

## 本体质量标准

一个"好的本体"必须满足（详见 `resources/ontology-design-principles.md`）：

| 原则 | 要求 |
|------|------|
| 概念精确性 | 每个概念有无歧义的定义，说"是什么"不是"叫什么" |
| 层次完整性 | IS-A / PART-OF 层次覆盖所有核心概念 |
| 关系语义丰富 | 每条关系有机制、条件、例外、时滞 |
| 术语映射 | 每个概念关联同义词、缩写、跨语言术语 |
| 公理与约束 | 领域规则用自然语言明确表达 |
| 可追溯性 | 每个声明追溯到知识源 |

## Commands

| Command | Action |
|---------|--------|
| `rag_client.py build-ontology` | Full pipeline: retrieve → ontology → data → verify |
| `rag_client.py retrieve-score` | Phase 1 only: retrieve + score |
| `rag_client.py web-search` | Standalone web search |
| `rag_client.py start` | Auto-start RAG engine |
| `rag_client.py health` | Check engine status |

## License

MIT
