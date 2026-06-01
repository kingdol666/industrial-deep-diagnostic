# RAG Knowledge Builder — Integration Guide

> 如何将 `rag-knowledge-builder` 连接到 `industrial-deep-diagnostic` 技能

## 连接模式

### 模式 A: Skill 委托（推荐 — 适用于任何工业场景）

context-builder agent 在执行时通过 `Skill` 工具调用本 skill：

```
Skill({skill: "rag-knowledge-builder", args: "scenario='...' target_cols='...' param_cols='...' group_cols='...' run_dir='<RUN_DIR>' interaction_mode='auto'"})
```

本 skill 内部自动：
1. 检测 RAG 引擎是否在运行（`curl localhost:8765/health`）
2. 若引擎在线：调用 `uv run python scripts/rag_client.py pipeline --output-dir "$run_dir"`
3. 若引擎离线：回退到本地 ChromaDB 直连
4. 写入 `$run_dir/00_input/rag_ontology_draft.json`

### 模式 B: 手动预填充

在诊断运行之前手动执行 RAG：

```bash
# Step 1: 启动 RAG 引擎
cd rag-retrieval-engine && uv sync && uv run python server.py &

# Step 2: 运行 RAG 检索
cd rag-knowledge-builder
uv run python scripts/rag_client.py pipeline \
  --scenario "your process description here" \
  --target-cols "quality_column_1,quality_column_2" \
  --param-cols "param_col_1,param_col_2,..." \
  --output-dir $RUN_DIR

# Step 3: 运行诊断 skill
/industrial-deep-diagnostic analyze --data-path ./data.csv
```

### 模式 C: 仅本地（离线运行）

```bash
# 引擎必须已运行（本地 ChromaDB）
uv run python scripts/rag_client.py pipeline \
  --scenario "CNC machining" --mode local_only ...
```

## 首次设置

```bash
# 1. 安装依赖（uv 自动管理 venv）
cd rag-retrieval-engine && uv sync

# 2. 构建初始知识索引  
curl -X POST http://localhost:8765/index -H "Content-Type: application/json" -d '{}'

# 3. 验证
curl -s http://localhost:8765/health
# → {"status":"healthy","kb_ready":true,"total_chunks":63}
```
