# Indexing Guide — Chunking Strategy & Metadata Design

> This file tells `kb_build.py` how to split source documents into semantic chunks, and how to design metadata so that retrieval can filter on it.

## Chunking Strategy

### 1. Markdown documents (`*.md`)

```
Algorithm: RecursiveCharacterTextSplitter
Chunk size: 512 tokens
Overlap: 64 tokens
```

**Split by section**: each `## Section` is an independent semantic unit. If a section exceeds 512 tokens, split it further at paragraph boundaries.

**Concept retention**: make sure every chunk retains any concept names, formulas, and thresholds. If a concept spans two chunks, duplicate the key lines in the overlap.

### 2. JSON files (knowledge base)

```
Algorithm: hyperedge chunking (OG-RAG pattern)
```

Each `causal_chain` / `concept_definition` / `quantitative_rule` entry becomes one complete semantic chunk — the whole causal arc or definition is kept inside a single chunk.

```json
{
  "chunk_id": "kb_<domain>_<concept>_<index>",
  "content": "概念名: <name>\n定义: <definition>\n因果链: <chain>\n公式: <equation>\n阈值: <threshold>",
  "mechanism_type": "causal_chain|concept_definition|quantitative_rule|risk_pattern|confounder",
  "concept_tags": ["concept_name_1", "concept_name_2"],
  "domain_tags": ["domain_type_1", "domain_type_2"]
}
```

> **Note**: the `content` field above is the emitted-output template for chunk content; the rendered text is written in the configured output language (default: Chinese), which is why its field labels stay in Chinese.

### 3. Web search results

```
Algorithm: per-snippet chunking
Each web search result snippet = 1 chunk
```

Web snippets are ephemeral — they exist only within the current retrieval session. If they pass the scoring threshold and are used for ontology construction, they are tagged together with their source URL.

## Metadata Schema

Every chunk carries the following metadata in ChromaDB:

```python
metadatas = {
    "source_type": "local_reference|web_authoritative|web_general|user_documentation|accumulated_verified",
    "source_path": "path/to/source/file",
    "domain_tags": "domain_1,domain_2",           # comma-separated (used for D3 filtering)
    "mechanism_type": "causal_chain|concept_definition|quantitative_rule|...",
    "concept_tags": "concept_1,concept_2,concept_3", # comma-separated (used for D2 matching)
}
```

**Field descriptions:**
- `domain_tags` — the domain(s) this knowledge chunk touches (used for D3 domain-consistency scoring)
- `concept_tags` — the concepts this knowledge chunk discusses (used for D2 concept matching)
- `mechanism_type` — knowledge type (used for filtering during retrieval)
- `source_type` — source type (used for D4 source-credibility scoring)

## Index Update Strategy

| Operation | Command | Frequency | Description |
|------|------|------|------|
| Full rebuild | `--rebuild` | Only when source files change | Delete and recreate everything |
| Incremental add | `--add-source <file>` | On demand | Index one new reference file |
| Accumulate from runs | `--accumulate <RUN_DIR>` | After every high-confidence run | Only when audit=PASS and match_rate≥0.6 |
| Remove stale knowledge | `--prune` | Monthly | Remove chunks unused for more than 6 months |
