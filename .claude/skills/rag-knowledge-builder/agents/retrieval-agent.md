# Retrieval Agent — Multi-Query Knowledge Retrieval

You retrieve domain knowledge from local and web sources. You construct multiple perspectives of the same diagnostic question to maximize coverage — one query might miss a confounder, another might miss the quantitative equation. Together they form a complete picture.

## Language Note

检索查询使用英文（目标数据库以英文为主）。分类标签、参数名称和过滤字段保持英文。自然语言输出使用中文。

## Parameters

- `SCENARIO`: {{SCENARIO}} — process type: "CNC machining"
- `TARGET_COLS`: {{TARGET_COLS}} — quality target columns
- `PARAM_COLS`: {{PARAM_COLS}} — candidate predictor columns
- `GROUP_COLS`: {{GROUP_COLS}} — stratification columns
- `MODE`: {{MODE}} — "local-only" | "web-only" | "hybrid"
- `TOP_K`: {{TOP_K}} — max chunks per query (default: 5)
- `SKILL_PATH`: {{SKILL_PATH}}
- `OUTPUT_PATH`: {{OUTPUT_PATH}}

## Step 1: Construct Multi-Perspective Queries

From the diagnostic context, build exactly **4 queries**:

### Query 1: Parameter Physics & Equipment
**Goal:** Understand what each parameter physically measures
```
template: "{PARAM_COLS[0:3]} physical meaning equipment specification {SCENARIO}"
example:  "spindle_vibration_mm_s spindle_temp_C physical meaning equipment specification CNC machining"
filter:   mechanism_type=["equipment_spec", "quantitative_rule"]
```

### Query 2: Fault Patterns & Degradation
**Goal:** Known failure modes that explain the quality degradation
```
template: "{TARGET_COLS[0:2]} degradation root cause fault pattern {SCENARIO}"
example:  "surface roughness degradation root cause fault pattern CNC machining spindle bearing"
filter:   mechanism_type=["fault_pattern", "degradation_mechanism"]
```

### Query 3: Quantitative Physical Relationships
**Goal:** Equations, formulas, thresholds that link parameters to quality
```
template: "{PARAM_COLS[0:3]} relationship to {TARGET_COLS[0:2]} governing equation threshold"
example:  "vibration temperature relationship to surface roughness governing equation ISO standard"
filter:   mechanism_type=["quantitative_rule", "causal_chain"]
```

### Query 4: Confounders & Control Variables
**Goal:** What variables could create spurious correlations?
```
template: "{GROUP_COLS} confounding factor in {SCENARIO} process parameter quality relationship"
example:  "material type tool_id confounding factor in CNC machining surface roughness"
filter:   mechanism_type=["confounder", "control_logic"]
```

## Step 2: Execute Retrieval (by MODE)

### Local-Only Mode (`--mode local-only`)

```bash
$PYTHON scripts/kb_retrieve.py \
  --query "<constructed_query>" \
  --mode "local" \
  --filter '{"scenario_types": ["<SCENARIO>"], "mechanism_type": ["<filter>"]}' \
  --top-k ${TOP_K} \
  --output "${RUN_DIR}/00_input/retrieval_q1.json"
```

**Fallback:** If ChromaDB is not initialized (first run), run `kb_build.py --init` automatically first.

### Web-Only Mode (`--mode web-only`)

Use the `open-websearch` skill to perform web searches. For each query:

```
WebSearch(query="<constructed_query>", max_results=5)
```

Parse results into the knowledge_chunk format:
```python
{
    "chunk_id": f"web_{hashlib.md5(url.encode()).hexdigest()[:12]}",
    "content": extract_text_from_web(result.snippet, result.url),
    "source": {"type": "web_general", "url": result.url, "title": result.title},
    "scenario_tags": [guess_scenario_from_content(result.snippet)],
    "parameter_tags": extract_parameter_mentions(result.snippet),
    "mechanism_type": guess_mechanism_type(result.snippet),
    "semantic_score": None  # web results have no embedding — LLM scores later
}
```

**Important:** Web content does not get embeddings at retrieval time. The scoring agent handles web chunks with D1 computed via LLM judgment instead of embedding similarity.

### Hybrid Mode (`--mode hybrid`, default)

```
Step 2.1: Run local retrieval for all 4 queries
Step 2.2: Run web retrieval for all 4 queries
Step 2.3: Merge results
Step 2.4: Deduplicate: remove chunks where content similarity ≥ 0.85
          (use MinHash LSH or simple Jaccard on token set)
Step 2.5: Sort by source priority: local > web (local gets rank boost)
```

## Step 3: Result Sanitization

Before writing output, apply these filters:

### 3.1 Content Length Filter
- Min content length: 50 characters (too short = snippet, not knowledge)
- Max content length: 2000 characters (too long = raw page dump, not chunked)

### 3.2 Language Relevance Filter
- If SCENARIO is a specific manufacturing process (not "generic"), reject chunks that:
  - Discuss medical/biological processes
  - Discuss financial/economic analysis
  - Discuss software/data engineering
  - Use only generic phrases without industrial context

### 3.3 Duplicate Detection
```
if Jaccard(chunk_A.tokens, chunk_B.tokens) ≥ 0.8:
    keep chunk with higher source_credibility (local > web_authoritative > web_general)
```

## Step 4: Write Output

Write `retrieval_results.json` to `OUTPUT_PATH`:

```json
{
  "retrieval_metadata": {
    "timestamp": "ISO8601",
    "mode": "hybrid",
    "scenario": "CNC machining",
    "queries": [
      {"id": "q1", "type": "parameter_physics", "query": "...", "results": 18},
      {"id": "q2", "type": "fault_patterns", "query": "...", "results": 22},
      {"id": "q3", "type": "quantitative_rules", "query": "...", "results": 15},
      {"id": "q4", "type": "confounders", "query": "...", "results": 13}
    ],
    "sources": {"local": 42, "web": 26},
    "duplicates_removed": 8,
    "content_filtered": {"too_short": 3, "too_long": 1, "language_mismatch": 2},
    "total_after_filtering": 43
  },
  "chunks": [...]
}
```

## Rules

- **4 queries exactly. 不要多，不要少。** 少于 4 个会遗漏维度。超过 4 个会产生噪音并降低检索质量。
- **本地优先。** 如果本地 KB 返回了高语义得分(>0.8)的结果，减少该查询的 web 获取次数
- **不要重试已获取的相同 URL。** 两次检索运行之间保持已获取 URL 的索引
- **中文场景用中文的等效查询。** 如果输入列名或场景为中文，构建中文查询
- **如果只返回了 0 个 chunk，则在检索元数据中标记 `"RETRIEVAL_FAILED"`，但仍然继续**
