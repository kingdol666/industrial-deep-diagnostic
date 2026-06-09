---
name: project-overview
description: 项目整体架构、技术栈、文件结构和核心模块概览
metadata: 
  node_type: memory
  type: project
  originSessionId: a048abac-a95d-468f-b017-6840248bcbae
---

# Industrial Deep Diagnostic — 项目架构总览

## 项目定位
端到端工业深度诊断系统，对传感器/工艺数据进行 8 阶段根因分析。核心价值：**场景自适应** — 不绑定特定工业场景，通过数据自描述 + RAG + 物理第一性原理实现通用诊断。

## 技术栈

| 模块 | 技术 | 端口 |
|------|------|------|
| Claude Code Skill | 多智能体管线 (.claude/skills/) | N/A |
| Backend | Express.js + SQLite (WAL) + WebSocket | 3210 |
| Frontend | Vue 3 + Vite + ECharts | 5180 |
| RAG Engine | FastAPI + ChromaDB + sentence-transformers | 8765 |
| CLI | Node.js (`ind-diag`) | N/A |
| Python 环境 | uv 管理 venv (scripts/.venv) | N/A |
| 部署 | Docker + nginx + Cloudflare Tunnel | - |

## 文件结构 (核心源码 ~5000 行)

```
industrial-deep-diagnostic/
├── .claude/                        # Skill 主体
│   ├── skills/industrial-deep-diagnostic/  # 主诊断 skill
│   │   ├── SKILL.md               # 权威入口 (~470 行)
│   │   ├── CLAUDE.md              # 开发者笔记
│   │   ├── pipeline-execution.md  # 修复循环协议
│   │   ├── agents/ (7个)          # 子智能体定义
│   │   ├── scripts/ (22个)        # 管线脚本 (mjs + py)
│   │   ├── schemas/ (14个)        # JSON Schema 校验
│   │   ├── templates/ (5个)       # 输出模板
│   │   ├── resources/ (13个)      # 领域知识按需加载
│   │   ├── examples/ (3场景)      # BOPET/换热器/反应器
│   │   └── tests/checklists/ (4个)
│   ├── skills/rag-knowledge-builder/  # RAG 本体构建 skill
│   ├── agents/ (7个)              # 与 .claude/skills 对齐的 agent 注册
│   └── agent-memory/ (4个agent)   # 子智能体跨会话记忆
├── app/
│   ├── backend/src/               # Express 后端
│   │   ├── index.mjs              # 入口 (HTTP+WS)
│   │   ├── engine/                # 事件总线 + Claude CLI 客户端
│   │   ├── transport/             # WebSocket 服务端
│   │   ├── routes/ (5个)          # files/diagnosis/history/analysis/chat
│   │   ├── services/ (5个)        # 业务逻辑层
│   │   ├── db/database.mjs        # SQLite WAL + prepared statements
│   │   └── utils/logger.mjs       # Winston 日志
│   └── frontend/src/              # Vue 3 SPA
│       ├── App.vue                # 5-tab 布局
│       ├── api/index.js           # HTTP + WS 客户端
│       ├── components/
│       │   ├── data/              # DataBrowser
│       │   ├── diagnosis/         # DiagnosisView + MessageStream + TaskList
│       │   ├── chat/              # ChatView
│       │   ├── reports/           # ReportViewer
│       │   ├── history/           # HistoryList
│       │   └── charts/ (4种)      # Line/Scatter/Heatmap/Gauge
│       ├── stores/                # diagnosisRealtimeStore
│       └── utils/                 # markdown/time/diagnosisRun
├── rag-retrieval-engine/          # FastAPI 微服务
│   ├── server.py                  # 12+ 端点
│   └── engine/                    # retriever/scorer/injector/storage
├── config/                        # YAML 配置 (default + local)
├── commands/cli.mjs               # CLI 入口
├── data/                          # 测试数据集 (8个场景)
├── workspace/                     # 诊断运行输出
└── docs/                          # 架构文档
```

## 关键架构决策

1. **事件总线** (`diagnosis-engine.mjs`): EventEmitter 解耦 Claude CLI 进程与 WS/SSE 传输
2. **Agent 解耦**: 子智能体仅通过 workspace 文件通信，不共享主 agent context
3. **Schema-First**: 写入前读 schema → 一次写入 → 立即验证 (防重写浪费 token)
4. **三重执行证明**: `.pipeline_events.jsonl` + 产物文件 + `artifact-check.mjs` 校验
5. **四套编号体系**: Pipeline Step / Agent Phase / Reasoning Segment / Method Stage 各自独立

## 关联记忆
- [[skill-design-assessment]] — Skill 设计评估
- [[backend-architecture]] — 后端架构评估
- [[rag-engine-design]] — RAG 引擎评估
