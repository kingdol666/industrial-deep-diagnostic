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

**参数保留**: 确保每个块保留任何参数名、物理公式和阈值。如果一个参数跨越两个块，在重叠中复制参数行。

### 2. JSON 文件 (`parameter_to_physics.json`)

```
算法: 超边分块 (OG-RAG pattern)
```

每个 `causal_chain` 条目成为一个完整的超边块 — "轴承磨损 → 振动↑ → 粗糙度↑" 的整个因果弧保存在一个块中。

```json
{
  "chunk_id": "kb_parameter_to_physics_spindle_vibration_0",
  "content": "Parameter: spindle_vibration_mm_s\nPhysical Quantity: 振动速度 RMS (mm/s)\nGoverning Law: ISO 10816-1\nCausal Chain: 轴承磨损 → 旋转不平衡 → 振动↑ → 刀尖位移 → 表面波纹 → Ra↑\nQuantitative Check: vibration_amplitude × inverse_tool_stiffness = tool_tip_deflection\nThreshold: ISO 10816 Zone C (>4.5mm/s)",
  "mechanism_type": "causal_chain",
  "parameter_tags": ["spindle_vibration_mm_s", "vibration", "spindle_vibration"],
  "scenario_types": ["CNC_machining"]
}
```

### 3. 网页搜索结果

```
算法: 逐片段块
每个搜索结果片段 = 1 个块
```

网页片段是临时性的 — 它们只在当前检索会话中存在。如果它们通过了评分门槛并被注入本体，它们将被标记为与源 URL 一起注入。

## Metadata 模式

每个块在 ChromaDB 中携带以下元数据：

```python
metadatas = {
    "source_type": "local_reference",          # 来源类型(用于 D4 评分)
    "source_path": "parameter_to_physics.json", # 回溯到源
    "scenario_types": "CNC_machining,metal_forming",  # 逗号分隔(用于 D3 过滤)
    "mechanism_type": "causal_chain",         # 知识类型(用于查询过滤)
    "parameter_tags": "spindle_vibration_mm_s,vibration",  # 逗号分隔(用于 D2 匹配)
}
```

## 索引更新策略

| 操作 | 命令 | 频率 | 说明 |
|------|------|------|------|
| 完全重建 | `--rebuild` | 仅当源文件变更时 | 删除并重新创建所有内容 |
| 增量添加静态文件 | `--add-source <file>` | 按需 | 索引一个新的参考文件 |
| 从诊断累积 | `--accumulate <RUN_DIR>` | 每次高置信度诊断后 | 仅在 Judge≥90 + audit=ENDORSED 时 |
| 移除过时知识 | `--prune` | 每月 | 移除超过 6 个月未使用的块 |
