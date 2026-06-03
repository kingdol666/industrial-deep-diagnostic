# RAG Retrieval Engine

独立运行的 HTTP 检索服务，为本项目的 `rag-knowledge-builder` Skill 提供知识检索、评分、知识注入和运行管理能力。

## 服务定位

这个服务不是最终用户直接使用的“知识问答产品”，而是一个**面向 Skill 的后端知识基础设施**：
- 接收领域描述与概念列表
- 从本地知识库与可选 Web 中检索候选知识
- 对知识块进行打分
- 将知识结果注入到本体构建流程
- 保存检索运行记录

## 服务在项目中的位置

```text
Industrial Deep Diagnostic Skill
        │
        └── calls
                │
                ▼
        RAG Knowledge Builder Skill
                │
                └── HTTP
                        ▼
                 RAG Retrieval Engine
```

## 功能概览

- `/health`：健康检查与知识库状态
- `/index`：构建或重建知识索引
- `/retrieve`：多视角知识检索
- `/score`：知识块评分
- `/inject`：知识注入 / 本体构建辅助
- `/pipeline/full`：一站式检索流水线
- `/runs`：运行记录查询
- `/stats`：知识库与存储统计

## 目录结构

```text
rag-retrieval-engine/
├── README.md
├── server.py
├── engine/                    # 检索、评分、存储等核心逻辑
├── knowledge_base/
│   ├── chroma_db/             # 向量索引
│   └── user_docs/             # 用户知识源
├── storage/
│   └── retrieval_runs/        # 检索运行记录
└── tests/
```

## 快速开始

### 1. 安装依赖

推荐使用 `uv`：

```bash
cd rag-retrieval-engine
uv sync
```

如果你不使用 `uv`，再退回 `pip`。

### 2. 启动服务

```bash
uv run python server.py
```

默认监听：`http://0.0.0.0:8765`

### 3. 健康检查

```bash
curl http://localhost:8765/health
```

### 4. 首次建立索引

```bash
curl -X POST http://localhost:8765/index \
  -H "Content-Type: application/json" \
  -d '{}'
```

### 5. 通过 Skill 使用

通常不建议直接手写 HTTP 请求，而是通过：
- `rag-knowledge-builder` Skill
- 或其客户端脚本

## 适用场景

适用：
- 作为 Skill 的检索后端
- 领域知识块检索与评分
- 本地知识库 + 可选 Web 混合检索

不适用：
- 直接替代最终分析 Skill
- 直接产出完整诊断报告
- 作为独立前端产品使用

## 与其他模块的关系

- 它不负责最终诊断
- 它不负责最终工业报告
- 它不负责多子代理编排
- 它负责为上层 Skill 提供稳定、可调用的知识检索能力

## 配套文档

- 上游 Skill：`.`claude/skills/rag-knowledge-builder/README.md:1`
- 最终消费者之一：`.`claude/skills/industrial-deep-diagnostic/README.md:1`
