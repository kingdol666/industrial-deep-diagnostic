# Indexing Guide — Chunking Strategy & Metadata Design

> 本文件指导 `kb_build.py` 如何将源文档分割为语义块，以及如何设计元数据以便检索过滤。

## Chunking 策略

### 1. Markdown 文档 (`*.md`)

```
算法: RecursiveCharacterTextSplitter
块大小: 512 tokens
重叠: 64 tokens
```

**按节分割**: 每个 `## Section` 是一个独立的语义单元。如果一个节超过 512 tokens，进一步在段落边界处分割。

**概念保留**: 确保每个块保留任何概念名、公式和阈值。如果一个概念跨越两个块，在重叠中复制关键行。

### 2. JSON 文件（知识库）

```
算法: 超边分块 (OG-RAG pattern)
```

每个 `causal_chain` / `concept_definition` / `quantitative_rule` 条目成为一个完整的语义块 — 整个因果弧或定义保存在一个块中。

```json
{
  "chunk_id": "kb_<domain>_<concept>_<index>",
  "content": "概念名: <name>\n定义: <definition>\n因果链: <chain>\n公式: <equation>\n阈值: <threshold>",
  "mechanism_type": "causal_chain|concept_definition|quantitative_rule|risk_pattern|confounder",
  "concept_tags": ["concept_name_1", "concept_name_2"],
  "domain_tags": ["domain_type_1", "domain_type_2"]
}
```

### 3. 网页搜索结果

```
算法: 逐片段块
每个搜索结果片段 = 1 个块
```

网页片段是临时性的 — 它们只在当前检索会话中存在。如果它们通过了评分门槛并被用于本体构建，它们将被标记为与源 URL 一起。

## Metadata 模式

每个块在 ChromaDB 中携带以下元数据：

```python
metadatas = {
    "source_type": "local_reference|web_authoritative|web_general|user_documentation|accumulated_verified",
    "source_path": "path/to/source/file",
    "domain_tags": "domain_1,domain_2",           # 逗号分隔（用于 D3 过滤）
    "mechanism_type": "causal_chain|concept_definition|quantitative_rule|...",
    "concept_tags": "concept_1,concept_2,concept_3", # 逗号分隔（用于 D2 匹配）
}
```

**字段说明：**
- `domain_tags` — 该知识块涉及的领域（用于 D3 领域一致性评分）
- `concept_tags` — 该知识块讨论的概念（用于 D2 概念匹配）
- `mechanism_type` — 知识类型（用于检索时的过滤）
- `source_type` — 来源类型（用于 D4 来源信誉评分）

## 索引更新策略

| 操作 | 命令 | 频率 | 说明 |
|------|------|------|------|
| 完全重建 | `--rebuild` | 仅当源文件变更时 | 删除并重新创建所有内容 |
| 增量添加 | `--add-source <file>` | 按需 | 索引一个新的参考文件 |
| 从运行累积 | `--accumulate <RUN_DIR>` | 每次高置信度运行后 | 仅在 audit=PASS 且 match_rate≥0.6 时 |
| 移除过时知识 | `--prune` | 每月 | 移除超过 6 个月未使用的块 |
