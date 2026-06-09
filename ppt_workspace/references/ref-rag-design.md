---
name: rag-engine-design
description: RAG 检索引擎设计评估 — FastAPI + ChromaDB 微服务
metadata: 
  node_type: memory
  type: project
  originSessionId: a048abac-a95d-468f-b017-6840248bcbae
---

# RAG 检索引擎评估

## 总体评分: ⭐⭐⭐⭐ (4/5) — 功能完备，独立可部署

## 架构

```
server.py (FastAPI, ~960 行)
├── engine/
│   ├── retriever.py    — ChromaDB 向量检索 + Web 搜索
│   ├── scorer.py       — 5 维相关度评分
│   ├── injector.py     — 本体注入
│   ├── storage.py      — SQLite 持久化
│   ├── models.py       — Pydantic 模型
│   └── web_search.py   — 网络搜索集成
├── config.yaml         — 配置
└── storage/            — 运行结果持久化
```

## 设计亮点

### 1. 三阶段管线: Retrieve → Score → Inject — ⭐⭐⭐⭐⭐
- `/retrieve`: ChromaDB 语义检索 + 可选 Web 搜索
- `/score`: 5 维相关度评分 + 质量门控 + Tier 分级
- `/inject`: 本体草稿生成，兼容诊断 skill
- 便捷端点 `/pipeline/retrieve-score` 一步到位
- **评价**: 三阶段解耦设计让每个阶段都可以独立调用和调优。

### 2. 多源知识索引 — ⭐⭐⭐⭐
- 本地 Markdown (按 `##` 分段)
- JSON 参数库 (`parameter_to_physics.json` 的 causal_chain)
- 用户上传文档 (PDF/TXT/MD/CSV/JSON)
- 目录批量索引
- Web 搜索结果注入
- **评价**: 灵活的多源索引策略，支持持续知识积累。

### 3. 安全设计 — ⭐⭐⭐⭐
- 路径遍历防护 (`_validate_path`)
- 可选 API Key 认证 (admin 端点)
- 文件名清洗
- **评价**: 安全意识好，路径校验实现规范。

### 4. 运行持久化 — ⭐⭐⭐⭐
- 每次检索运行记录到 SQLite
- 状态跟踪: created → retrieved → scored → injected
- 可查询历史运行 (`/runs`, `/runs/{run_id}`)
- **评价**: 可审计、可追溯。

## 可改进之处

### 1. 评分引擎 — 静态规则
- 5 维评分是预定义的静态规则
- **建议**: 考虑引入 LLM 辅助评分以提高领域适应性

### 2. 文档解析 — 基础
- PDF 解析是基础的文本提取
- **建议**: 集成 `unstructured` 或 `docling` 提升复杂文档解析质量

### 3. Embedding 模型 — 固定
- 默认 `all-MiniLM-L6-v2`，中文支持有限
- **建议**: 支持可配置的 embedding 模型，中文场景可用 `bge-large-zh`

### 4. 缓存机制 — 缺失
- 相同查询没有缓存
- **建议**: 对高频相似查询添加语义缓存

## 端点一览

| 端点 | 方法 | 功能 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/retrieve` | POST | 知识检索 |
| `/score` | POST | 5维评分 |
| `/inject` | POST | 本体注入 |
| `/pipeline/retrieve-score` | POST | 检索+评分 |
| `/pipeline/full` | POST | 完整管线 (deprecated) |
| `/index` | POST | 构建索引 |
| `/index/upload` | POST | 上传并索引文档 |
| `/index/dir` | POST | 索引目录 |
| `/index/files` | GET | 列出已索引文件 |
| `/accumulate` | POST | 积累诊断发现 |
| `/web/inject` | POST | 注入 Web 搜索结果 |
| `/query/enhance` | POST | AI 查询增强 |
| `/runs` | GET | 列出运行 |
| `/runs/{run_id}` | GET | 运行详情 |
| `/stats` | GET | 统计信息 |

## 关联记忆
- [[project-overview]]
- [[skill-design-assessment]]
