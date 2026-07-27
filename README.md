# Industrial Deep Diagnostic

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/logo.svg">
    <source media="(prefers-color-scheme: light)" srcset="docs/logo.svg">
    <img alt="Industrial Deep Diagnostic" src="docs/logo.svg" width="600">
  </picture>
  <br>
  <strong>Multi-Agent Root Cause Analysis Engine for Industrial Manufacturing</strong>
  <br>
  <sub>端到端工业深度诊断系统 · 9 子智能体协作 · 竞争假说协议 · 物理驱动推理</sub>
</p>

<p align="center">
  <a href="#"><img src="https://img.shields.io/badge/Windows-0078D6?style=flat-square&logo=windows&logoColor=white" alt="Windows"></a>
  <a href="#"><img src="https://img.shields.io/badge/macOS-000000?style=flat-square&logo=apple&logoColor=white" alt="macOS"></a>
  <a href="#"><img src="https://img.shields.io/badge/Linux-FCC624?style=flat-square&logo=linux&logoColor=black" alt="Linux"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-ISC-blue.svg?style=flat-square" alt="License"></a>
  <a href="#"><img src="https://img.shields.io/badge/node-%3E%3D18-brightgreen?style=flat-square&logo=node.js" alt="Node.js"></a>
  <a href="#"><img src="https://img.shields.io/badge/python-%3E%3D3.9-blue?style=flat-square&logo=python" alt="Python"></a>
  <img src="https://img.shields.io/badge/Claude%20Code-Multi--Agent%20Pipeline-8A2BE2?style=flat-square" alt="Claude Code">
  <img src="https://img.shields.io/badge/output-%E4%B8%AD%E6%96%87%20%7C%20English-58a6ff?style=flat-square" alt="Language">
</p>

---

## 目录

- [项目简介](#项目简介)
- [核心能力](#核心能力)
- [快速开始](#快速开始)
- [使用指南](#使用指南)
  - [CLI 命令](#cli-命令)
  - [运行诊断](#运行诊断)
  - [Web UI](#web-ui)
  - [RAG 检索引擎](#rag-检索引擎)
- [诊断管线架构](#诊断管线架构)
  - [9 步执行流程](#9-步执行流程)
  - [9 个子智能体](#9-个子智能体)
  - [修复循环](#修复循环)
  - [证据体系](#证据体系)
  - [诊断结论类型](#诊断结论类型)
- [系统架构](#系统架构)
- [项目结构](#项目结构)
- [配置管理](#配置管理)
- [Docker 部署](#docker-部署)
- [示例数据集](#示例数据集)
- [文档索引](#文档索引)

---

## 项目简介

**Industrial Deep Diagnostic** 是一个端到端的工业深度诊断系统，用于对工业传感器/工艺数据进行全自动根因分析。它通过**多智能体编排**、**统计严谨性**、**物理推理**和**知识检索**的有机结合，交付生产级的诊断报告。

> **把它当作一个 24/7 在线的诊断工程师**——你输入原始传感器数据（CSV/XLSX/Parquet），它返回完整的分析结果：数据质量检查、领域本体构建、统计验证、基于物理的根因假设、质量门审查、报告以及交互式可视化。

这套系统背后运行在 **Claude Code** 之上，通过 9 个专用子 Agent 协作完成从数据摄入到最终报告交付的完整闭环。管线核心是一个**竞争假设协议**（Competing Hypotheses Protocol）——诊断不是确认单一原因，而是通过统计证据和物理推理逐一排除可能性，直到数据能区分的极限。

---

## 核心能力

<table>
<tr>
<td width="50%">

### 🔬 科学严谨的诊断推理

- **竞争假设协议** — 从不确认单一原因；多重假设并行测试，用数据区分性消除，直到证据无法区分为止
- **双驱动分析** — 纯工艺波动诊断 + 工艺-检测双驱动诊断，两种视角缺一不可
- **四条件因果判定** — 时间先后 + 统计显著 + 物理机制 + 无矛盾，缺一不可
- **七级证据体系 L1–L7** — 每条结论标注来源质量等级，结论可信度受最低等级约束

### 🧪 反假相关统计引擎

- **Simpson 悖论检测** — 分层相关分析防止聚合相关方向反转
- **时滞补偿 CCF** — 工艺→质量有物理延迟时计算最优滞后相关
- **留一法杠杆检测** — |r|≥0.3 的相关必须通过单点/单批次移除验证（|Δr|>0.2 → EXCLUDE）
- **批次标识完整性** — batch_id 唯一性验证，防止同批次拆分记录被误诊为孤立事件
- **变点检测 + 生产稳态过滤** — 排除启停过渡期的非稳态数据

</td>
<td width="50%">

### 🤖 9 子智能体协作管线

| 智能体 | 角色 | 核心产出 |
|--------|------|---------|
| context-builder | 王教授 · 25年失效分析 | 本体+物理原理 |
| data-processor | 张工 · 16年流程分析 | 统计+图表+交接 |
| vlm-visual-analyzer | 老孙 · 20年目视巡检 | 图表的视觉证据 |
| diagnostician | 刘总工 · 28年诊断 | 竞争假说+推理链 |
| judge | 陈主任 · 15年质量审计 | 10项评分门禁 |
| reporter | 周工 · 15年技术报告 | 金字塔结构报告 |
| report-reviewer | 孙审计 · 32年审计 | 物理真相审计 |
| html-visualizer | 林工 · 14年HMI可视化 | ECharts+Three.js |
| html-reviewer | 赵审阅 · 15年审校 | HTML 可用性审核 |

### 🔄 自修复管线

- **Judge best-of-3** — 最多 3 轮修复，追最高分，**永不 halt**（任何分数都产出报告）
- **Reviewer 修复循环** — 完整 D→J→R→R 循环，最多 2 轮
- **全局上限** — 总重诊断次数 ≤5，`pipeline_events.jsonl` 持久化
- **反振荡保护** — 同问题第 3 次修复 → 停止，设 COMPETING_SET，置信度≤50

</td>
</tr>
</table>

---

## 快速开始

### 前置依赖

| 依赖 | 版本 | 必须 | 说明 |
|------|:----:|:----:|------|
| [Node.js](https://nodejs.org/) | ≥ 18 | ✅ | CLI、后端、管线脚本运行环境 |
| [Python](https://www.python.org/) | ≥ 3.9 | ⚠️ 仅诊断管线 | 统计分析与可视化脚本 |
| [uv](https://docs.astral.sh/uv/) | latest | 🟡 推荐 | Python 包管理器；自动安装，降级 pip |
| [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) | latest | ⚠️ 仅诊断运行 | 驱动多智能体管线 |

### 1. 安装

```bash
# 克隆仓库
git clone https://github.com/kingdol666/industrial-deep-diagnostic.git
cd industrial-deep-diagnostic

# 安装依赖（js-yaml 配置加载器等）
npm install

# 全局安装 CLI（可选，启用 ind-diag 命令）
npm link
```

### 2. 初始化

```bash
ind-diag init
```

预期输出：
```
  [OK] Config: .../config/default.yaml
  [OK] Database initialized successfully.
  Initialization complete. Run: ind-diag all
```

### 3. 启动应用

```bash
# 方式一：CLI（推荐）
ind-diag all                          # 后端 + 前端一起启动
ind-diag backend                      # 仅后端 (port 3210)
ind-diag frontend                     # 仅前端 (port 5180)

# 方式二：npm scripts（等价）
npm start                             # = ind-diag all
npm run backend                       # = ind-diag backend
npm run frontend                      # = ind-diag frontend

# 方式三：直接 Node.js（无需 npm link）
node commands/start.mjs all
node commands/start.mjs backend
node commands/start.mjs frontend
```

### 4. 打开浏览器

```
前端界面:  http://localhost:5180
后端 API:  http://localhost:3210
API 健康:  http://localhost:3210/api/health
```

---

## 使用指南

### CLI 命令

```bash
ind-diag <command> [options]
```

| 命令 | 说明 |
|------|------|
| `init` | 初始化项目 — 校验配置、创建数据库 |
| `all` | 启动后端 + 前端 |
| `backend` | 仅启动 Express API 服务（端口 3210） |
| `frontend` | 仅启动 Vue 开发服务器（端口 5180） |
| `build` | 生产构建前端 |
| `status` | 显示项目状态 — 配置、数据、依赖 |
| `webfrp` | 通过 Cloudflare Tunnel 暴露到公网 |
| `config list` | 显示合并后的配置（default + local + env） |
| `config get <key>` | 获取特定配置项 |
| `config set <key> <value>` | 设置并持久化配置 |
| `config reset <key>` | 重置为默认值 |
| `help` | 帮助信息 |

### 运行诊断

**准备工作**：将传感器/工艺数据（CSV/XLSX/Parquet）放入 `data/` 目录。

**方式 A：通过 Claude Code 对话（推荐，完整管线）**

在 Claude Code 对话中调用 skill 命令：

| 命令 | 执行内容 |
|------|---------|
| `/industrial-deep-diagnostic` | 全管线 Step 0–9，自动执行 |
| `/industrial-deep-diagnostic analyze` | 跳过导入，从 Step 2（本体构建）开始 |
| `/industrial-deep-diagnostic review` | 重新评审已有结果 |
| `/industrial-deep-diagnostic report` | 重新生成报告 |
| `/industrial-deep-diagnostic audit` | 仅运行报告评审 |

管线全自动运行（full-auto 模式），中间零人工干预，产出：
- `report.md` — 中文诊断报告
- `diagnostic-report.html` — 交互式可视化页面
- `optimizer.md` — 优化方案建议
- `evidence_closure_report.json` — 证据闭环验证

**方式 B：通过 Web UI**

1. 打开 `http://localhost:5180` → **Data** 标签上传数据
2. 切换到 **Diagnose** 标签 → 选择数据 → 配置场景参数
3. 点击 **Start Diagnosis** → SSE 实时流查看进展
4. 完成后在 **Reports** 标签查看报告

### Web UI

前端运行在 `http://localhost:5180`，包含 4 个标签页：

| 标签页 | 功能 |
|--------|------|
| **Data** | 浏览上传的数据集、检查文件内容、管理数据目录 |
| **Diagnose** | 启动新诊断、实时 SSE 流查看进展、任务状态监控 |
| **Reports** | 查看完成的诊断报告，含嵌入图表和证据链 |
| **History** | 浏览历史运行记录、查看事件回放、导出结果 |

### RAG 检索引擎

RAG 引擎提供运行时领域知识检索，增强本体构建的物理深度：

```bash
# 启动 RAG 微服务
cd rag-retrieval-engine
uv sync
uv run python server.py
# 或跨平台方式
node start.mjs
```

服务运行在 `http://localhost:8765`，端点：

| 端点 | 功能 |
|------|------|
| `/retrieve` | 向量 + 关键词混合检索 |
| `/score` | 5 维相关性评分 |
| `/inject` | 本体引导的知识注入 |
| `/pipeline/full` | 端到端检索管线 |

> RAG 引擎为**可选组件**。不可用时管线自动降级，使用内置 `parameter_to_physics.json` + 网络搜索构建本体。

---

## 诊断管线架构

这是整个系统的核心——**9 步多智能体管线**，从原始数据到最终交付的端到端闭环。

### 9 步执行流程

```
STEP 0:  SETUP        ── 创建运行目录、配置环境、Python venv
    │
STEP 1:  INSPECT      ── 文件检测、schema 提取、数据类型推断
    │
STEP 2:  CONTEXT      ── context-builder 子 Agent
    │                    RAG 检索 + 本体构建 + 物理原理提取
    │
STEP 2.5: CLARIFY     ── 自动推断参数物理含义（auto 模式）
    │
STEP 3:  PROCESS      ── data-processor 子 Agent
    │                    统计分析 + 可视化 + 稳态过滤 + VLM 视觉
    │                    └── 内部委托 vlm-visual-analyzer
    │
STEP 4:  DIAGNOSE     ── diagnostician 子 Agent
    │                    竞争假设协议 + 物理推理 + 证据融合
    │                    产出 4 个 JSON: diagnosis / evidence / confidence / reasoning_chain
    │
    ┌──────┴───────┐
    ▼              ▼
STEP 5a: JUDGE     STEP 5b: PRE-AUDIT     ← 唯一并行步骤
(10项质量门评分)    (预报告物理审计)
    │              │
    └──────┬───────┘
           ▼
STEP 6:  REPORT       ── reporter 子 Agent: 9 节金字塔报告
    │
STEP 7:  REVIEW       ── report-reviewer 子 Agent: 物理真相审计
    │                    ENDORSED / CONDITIONAL / REJECTED
    │
STEP 8:  HTML VIZ     ── html-visualizer 子 Agent: ECharts + Three.js
    │
STEP 8.5: HTML REVIEW ── html-reviewer 子 Agent: 可用性审核
    │
STEP 9:  FINALIZE     ── 证据闭环验证 + artifact-check 权威门禁
```

### 严格顺序与并行规则

| 规则 | 详情 |
|------|------|
| **Step 2, 3 串行** | Ontology-First：本体构建完成前不启动数据统计 |
| **Step 5a, 5b 并行** | Judge 和 Pre-Audit 消费同一份 Step 4 产物 |
| **Judge → Reporter** | Judge gate 通过（score≥90 或 3 轮耗尽）才允许启动 Reporter |
| **Reporter → Reviewer** | 报告生成后再做物理审计 |
| **HTML 自动构建** | ENDORSED 后无缝执行 Step 8→8.5→9，不询问用户 |

### 9 个子智能体

| # | 智能体 | 角色人格 | 负责产出 | Schema 约束 |
|:-:|--------|---------|---------|:----------:|
| 2 | **context-builder** | 王教授 · 25年失效分析经验 | `ontology.json`、`rag_deep_understanding.json`、`extracted_knowledge.json` | `ontology_schema.json` |
| 3 | **data-processor** | 张工 · 16年流程制造数据科学家 | 统计分析报告、图表 PNG、`data_analysis_conclusion.json`、`plot_manifest.json` | `data_analysis_conclusion_schema.json` |
| 3.5 | **vlm-visual-analyzer** | 老孙 · 20年目视巡检 | `visual_analysis.json`、`image_captions.json` | `visual_analysis_schema.json`、`image_captions_schema.json` |
| 4 | **diagnostician** | 刘总工 · 28年产线根因分析 | `diagnosis.json`、`evidence.json`、`confidence.json`、`reasoning_chain.json` | 4 个独立 schema |
| 5a | **judge** | 陈主任 · 15年质量审计 | `judge_feedback.json`（10项评分+阻断问题） | `judge_feedback_schema.json` |
| 6 | **reporter** | 周工 · 15年技术报告撰写 | `report.md`（9节金字塔）、`run_summary.json` | 模板驱动 |
| 7 | **report-reviewer** | 孙审计 · 32年跨国审计 | `optimizer.md` + ENDORSED/CONDITIONAL/REJECTED | — |
| 8 | **html-visualizer** | 林工 · 14年HMI/SCADA+Web | `diagnostic-report.html`（ECharts + Three.js） | — |
| 8.5 | **html-reviewer** | 赵审阅 · 15年技术文档审校 | `html_review.json` | `html_review_schema.json` |

### 修复循环

```python
# Judge Best-of-3（保证交付，永不 halt）
for round in 1..3:
    spawn Diagnostician
    spawn Judge → score
    if score > best_score:
        snapshot → best_round_{round}/
    if score >= 90: break           # 通过
    if diag_iters >= 5: break       # 全局上限
restore best_round_{best_round}/ → canonical
proceed to Report + HTML           # 任何分数都产出交付物

# Reviewer 修复（完整重跑循环）
if verdict == CONDITIONAL or REJECTED:
    for cycle in 1..2:
        if diag_iters >= 5: break   # 全局上限
        full re-run: D → J → R → R
```

**全局修复上限**：`diag_iters ≤ 5`，在 `.pipeline_events.jsonl` 中通过 `repair_spawn` 事件持久化计数。超过上限后标记 `[REPAIR_CAP_REACHED]` 并以当前结果交付。

### 证据体系

| 等级 | 来源 | 置信度 | 标签 |
|:----:|------|:------:|------|
| 1 | 直接测量值（传感器、化验结果） | 最高 | `[Evidence Rank 1]` |
| 2 | 用户文档（SOP、维护手册） | 高 | `[Evidence Rank 2]` |
| 3 | 统计分析（含验证报告） | 中高 | `[Evidence Rank 3]` |
| 4 | 图表视觉证据（VLM 分析） | 中 | `[Evidence Rank 4]` |
| 5 | 领域知识/工艺逻辑 | 中低 | `[Evidence Rank 5]` |
| 6 | 外部网络引用 | 低 | `[Evidence Rank 6] [EXTERNAL]` |
| 7 | 无支持假设 | 最低 | `[Evidence Rank 7]` |

> **反假相关强制检查**：引用任何 |r|≥0.3 的相关时，必须先通过 Simpson 悖论检测、去趋势验证、留一法杠杆检验。否则 Judge 判 fail。

### 诊断结论类型

| 类型 | 含义 | 置信度上限 |
|:----:|------|:----------:|
| `DETERMINED` | 单一根因确定，统计+物理双重验证通过 | ≤95 |
| `COMPETING_SET` | 多个竞争假设无法区分 — 证据不足以辨别 | ≤50（INDISTINGUISHABLE），≤65（其他） |
| `NEEDS_DATA` | 数据不足以做出任何结论 | ≤30 |

---

## 系统架构

### 整体架构图

```
┌──────────────────────────────────────────────────────────────────┐
│                       用户界面层                                    │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌──────────────┐  │
│  │ ind-diag  │  │  Vue 3 UI │  │ REST API  │  │ Claude Code  │  │
│  │    CLI    │  │   :5180   │  │   :3210   │  │  Conversation │  │
│  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └──────┬───────┘  │
└────────┼──────────────┼──────────────┼────────────────┼──────────┘
         │              │              │                │
         ▼              ▼              ▼                ▼
┌──────────────────────────────────────────────────────────────────┐
│                       编排层                                      │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │                诊断引擎 (Event Bus)                         │   │
│  │     SSE 实时流 · WebSocket · 人工在环 · Claude SDK 集成    │   │
│  │     会话管理 · 工具监控 · 流式解析 · AskUserQuestion       │   │
│  └───────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────────────┐
│                     9 子智能体诊断管线 (Claude Code)                │
│                                                                  │
│  Step 0    Step 1     Step 2       Step 3     Step 4   Step 5   │
│  ┌─────┐  ┌──────┐  ┌─────────┐  ┌────────┐ ┌──────┐ ┌─────┐  │
│  │Setup│→│Inspect│→│Context  │→│Process │→│Diag  │→│Judge│  │
│  │     │  │      │  │Builder  │  │ (VLM)  │  │nost  │ │     │  │
│  └─────┘  └──────┘  └─────────┘  └────────┘ └──────┘ └──┬──┘  │
│                                                          │      │
│  Step 6    Step 7      Step 8     Step 8.5   Step 9     │      │
│  ┌──────┐ ┌────────┐ ┌─────────┐ ┌─────────┐ ┌──────┐  │      │
│  │Report│→│Reviewer│→│HTML Viz │→│HTML Rev │→│Final │◄─┘      │
│  │      │ │        │ │         │ │         │ │ize   │          │
│  └──────┘ └────────┘ └─────────┘ └─────────┘ └──────┘          │
└──────────────────────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────────────┐
│                    微服务层 (可选)                                  │
│  ┌─────────────────────────────┐  ┌──────────────────────────┐  │
│  │  RAG 检索引擎 (FastAPI)      │  │  SQLite 数据库           │  │
│  │  ChromaDB · 向量检索 · 评分  │  │  运行历史 · 事件回放      │  │
│  │  :8765                      │  │  聊天会话 · 数据目录     │  │
│  └─────────────────────────────┘  └──────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

### 组件栈

| 层级 | 技术栈 | 用途 |
|------|--------|------|
| **前端** | Vue 3 + Vite + ECharts 6 | 数据浏览器、实时诊断流、报告查看 |
| **后端 API** | Express.js 4 + WebSocket (ws) | REST 端点、SSE 流、诊断编排 |
| **数据库** | SQLite (better-sqlite3, WAL 模式) | 运行历史、事件流、聊天会话 |
| **CLI** | Node.js (ESM) | `ind-diag` 命令、配置管理、服务控制 |
| **诊断管线** | Claude Code + 9 子 Agent | 本体→统计→诊断→审查→报告→HTML 可视化 |
| **RAG 引擎** | FastAPI + ChromaDB | 向量检索、知识注入、语义评分 |
| **配置** | YAML (js-yaml) | 层级配置 + 环境变量覆盖 + local.yaml 合并 |

### 产出目录结构

每次诊断运行产出位于 `workspace/diagnostic-runs/<timestamp>_<scene>/`：

```
workspace/diagnostic-runs/
└── 20260619_142318_bopet_drift/
    ├── 00_input/             # 输入数据 + 用户上下文
    │   ├── input_manifest.json
    │   ├── user_context.json
    │   ├── run_config.json
    │   └── raw_data.csv
    ├── 01_ontology/          # 领域本体
    │   ├── ontology.json
    │   ├── clarification_needed.json
    │   └── rag_deep_understanding.json
    ├── 02_processed/         # 数据处理产物
    │   ├── data_analysis_conclusion.json   # → 传给 diagnostician 的核心交接文件
    │   ├── validate_report.json            # Simpson/去趋势/留一法验证
    │   ├── anomaly_report.json
    │   ├── feature_summary.json
    │   ├── scenario_classification.json
    │   ├── production_regime_filter.json   # v6.5 稳态过滤
    │   └── time_lag_analysis.json          # v6.4 时滞分析
    ├── 03_figures/           # 可视化图表 + VLM 分析
    │   ├── plot_manifest.json
    │   ├── visual_analysis.json            # VLM 视觉证据
    │   ├── image_captions.json
    │   └── *.png                           # 10+ 张分析图
    ├── 04_diagnostics/       # 诊断核心产出
    │   ├── diagnosis.json                  # 竞争假设诊断
    │   ├── evidence.json                   # 证据清单
    │   ├── confidence.json                 # 置信度调整
    │   └── reasoning_chain.json            # R1→R8 推理链
    ├── 05_review/            # 质量门审查
    │   ├── judge_feedback.json             # 10 项评分
    │   ├── html_review.json
    │   └── judge_repair_summary.json
    ├── 06_scripts/           # 自定义分析脚本
    ├── report.md             # 9 节中文诊断报告
    ├── diagnostic-report.html  # 交互式 HTML 可视化
    ├── optimizer.md          # 优化方案建议
    ├── evidence_closure_report.json  # 证据闭环
    └── .pipeline_events.jsonl         # 管线事件日志
```

---

## 项目结构

```
industrial-deep-diagnostic/
│
├── commands/                       # 🖥️ CLI & 跨平台工具
│   ├── cli.mjs                     #   ind-diag 命令入口
│   ├── start.mjs                   #   跨平台服务启动器
│   └── cross-platform.mjs          #   OS 无关工具函数
│
├── app/
│   ├── backend/                    # 🔧 Express.js API (:3210)
│   │   └── src/
│   │       ├── index.mjs           #   服务器入口
│   │       ├── db/database.mjs     #   SQLite schema + 迁移
│   │       ├── engine/             #   Claude SDK 集成
│   │       ├── routes/             #   files, diagnosis, history, analysis, chat
│   │       ├── services/           #   业务逻辑层
│   │       └── transport/ws-server.mjs  # WebSocket
│   └── frontend/                   # 🎨 Vue 3 + Vite (:5180)
│       └── src/
│           ├── App.vue             #   标签页布局
│           ├── components/         #   charts/, chat/, data/, diagnosis/, reports/
│           ├── stores/             #   Pinia 状态管理
│           └── utils/              #   markdown, 时间格式化
│
├── .claude/
│   ├── skills/industrial-deep-diagnostic/  # 🤖 9-Agent 诊断管线
│   │   ├── SKILL.md                        #   管线入口 & 完整协议
│   │   ├── agents/                         #   9 个子 Agent 定义
│   │   ├── schemas/                        #   16 个 JSON Schema
│   │   ├── scripts/                        #   28 个脚本 (Node.js + Python)
│   │   │   ├── stats.mjs                   #   统计分析引擎
│   │   │   ├── stats_validate.mjs          #   统计验证引擎
│   │   │   ├── artifact-check.mjs          #   64 项权威门禁
│   │   │   ├── physics_check.py            #   物理约束验证
│   │   │   └── ...
│   │   ├── resources/                      #   14 个领域知识文档
│   │   │   ├── evidence_rules.md           #   证据等级 & 因果关系
│   │   │   ├── physics_inference_framework.md  # L1-L5 物理推断
│   │   │   ├── process_knowledge_base.md   #   16 个普适物理原理
│   │   │   └── ...
│   │   ├── templates/                      #   5 个输出模板
│   │   ├── examples/                       #   3 个场景示例
│   │   │   ├── bopet_film_thickness/
│   │   │   ├── heat_exchanger_fouling/
│   │   │   └── reactor_temperature/
│   │   ├── tests/checklists/               #   4 个质量检查清单
│   │   ├── pipeline-execution.md           #   修复循环 & 验证参考
│   │   ├── QUICKSTART.md
│   │   └── CHANGELOG.md
│   ├── agents/                      # 子 Agent 定义
│   └── agent-memory/                # Agent 持久化记忆
│
├── rag-retrieval-engine/            # 🔍 RAG 微服务 (:8765)
│   ├── server.py                    #   FastAPI 服务
│   ├── engine/                      #   retriever, scorer, injector, web_search
│   └── knowledge_base/chroma_db/    #   ChromaDB 向量存储
│
├── config/                          # 🎛️ 配置
│   ├── default.yaml                 #   全部可配置项
│   ├── loader.mjs                   #   YAML 加载器 + 环境变量
│   └── local.yaml                   #   本地覆盖 (gitignored)
│
├── data/                            # 📊 示例 & 评估数据集
│   ├── eval_bopet_film_drift/       #   BOPET 薄膜厚度漂移
│   ├── eval_cnc_spindle_wear/       #   CNC 主轴轴承磨损
│   ├── eval_heat_exchanger_scaling/ #   热交换器结垢
│   ├── eval_reactor_catalyst/       #   反应器催化剂失活
│   ├── eval_steel_cold_rolling/     #   钢材冷轧
│   ├── paper_machine_headbox/       #   造纸机流浆箱
│   ├── cement_ball_mill/            #   水泥球磨机
│   └── references/                  #   工艺文档 & 标准答案
│
├── workspace/                       # 💾 运行产出
│   ├── diagnostic-runs/             #   诊断运行产物
│   └── rag-outputs/                 #   RAG 本体构建产物
│
├── docs/                            # 📖 文档
│   ├── logo.svg                     #   项目 Logo
│   ├── architecture/                #   系统架构、数据流
│   └── guides/                      #   用户指南
│
├── docker-compose.yml               # 🐳 Docker
├── Dockerfile
├── nginx.conf
├── package.json
└── README.md                        # 👈 当前文件
```

---

## 配置管理

配置文件采用层级合并机制：`default.yaml` ← `local.yaml` ← 环境变量。

### 关键配置项

```yaml
server:
  port: 3210                    # 后端 API 端口

frontend:
  port: 5180                    # Vite 开发服务器端口

claude:
  model: "claude-opus-4-7"      # 诊断用模型
  max_turns: 200                # 最大对话轮次
  timeout_minutes: 120          # 诊断超时

diagnosis:
  default_language: "zh"        # 输出语言 (zh/en)
  run_id_length: 8              # 运行 ID 长度

data:
  upload:
    max_file_size_mb: 500       # 上传最大文件大小
    max_files: 50               # 最大并发上传数
```

### 环境变量覆盖

```bash
SERVER_PORT=9090 npm run start:backend
CLAUDE_MODEL=claude-sonnet-5 ind-diag all
DIAGNOSIS_DEFAULT_LANGUAGE=en npm run start:all
```

---

## Docker 部署

```bash
# 构建并启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止
docker-compose down
```

Docker 部署包含：
- Node.js 应用（后端 + 构建好的前端）
- nginx 反向代理
- 持久化 volumes（`data/` + `workspace/`）

---

## 示例数据集

项目内置 7 个工业场景的评估数据集，每个包含原始数据、生成脚本和标准答案：

| 数据集 | 领域 | 规模 | 关键特征 | 真实根因 |
|--------|------|:----:|----------|:--------:|
| BOPET 薄膜漂移 | 塑料薄膜挤出 | ~2,000 行 | 温度区、熔压、膜厚 | 淬火温度渐进漂移 |
| CNC 主轴磨损 | 精密加工 | ~5,000 行 | 速度、进给、振动 | 轴承退化 |
| 热交换器结垢 | 化工过程 | ~3,000 行 | 流量、温度、压差 | 渐进式结垢 |
| 反应器催化剂 | 化学反应 | ~4,000 行 | 温度、压力、转化率 | 催化剂失活 |
| 钢材冷轧 | 金属成型 | ~3,500 行 | 轧制力、张力、厚度 | 轧辊偏心 |
| 造纸机 | 制浆造纸 | ~5,000 行 | 流浆箱、干燥、QCS | 一致性变异 |
| 水泥球磨机 | 水泥制造 | ~3,000 行 | 电流、振动、细度 | 衬板磨损 |

每个数据集包含：
- `data.csv` — 工艺 + 质量传感器读数
- `generate.py` — 数据生成脚本（可复现）
- `ground_truth.md` — 已知根因（用于评估）

---

## 文档索引

| 文档 | 位置 | 最适合谁 |
|------|------|---------|
| **本文件** | `README.md` | 所有人 — 项目概览和入门 |
| **项目 CLAUDE.md** | `CLAUDE.md` | 开发者和贡献者 |
| **SKILL.md — 管线完整协议** | `.claude/skills/industrial-deep-diagnostic/SKILL.md` | 使用诊断管线的用户 |
| **执行参考** | `.claude/skills/industrial-deep-diagnostic/pipeline-execution.md` | 修复循环和验证命令 |
| **工程交付契约** | `resources/engineering_delivery_contract.md` | 了解交付标准的用户 |
| **证据规则** | `resources/evidence_rules.md` | L1-L7 证据等级和反推测 |
| **诊断方法论** | `resources/diagnosis_method.md` | Method Stage 1-6 底层方法 |
| **物理推断框架** | `resources/physics_inference_framework.md` | L1-L5 物理推断阶梯 |
| **领域知识库** | `resources/process_knowledge_base.md` | 16 个普适物理原理 |
| **快速入门** | `QUICKSTART.md` | 想快速上手的用户 |
| **故障排查** | `TROUBLESHOOTING.md` | 遇到问题的用户 |
| **术语表** | `GLOSSARY.md` | 理解专业术语 |
| **架构文档** | `docs/architecture/system-overview.md` | 系统设计细节 |
| **数据流图** | `docs/architecture/data-flow.md` | 数据流动路线 |
| **安全策略** | `SECURITY.md` | 安全实践 |
| **变更日志** | `CHANGELOG.md` | 版本历史 |
| **性能指标** | `PERFORMANCE.md` | 性能基准 |

---

## 贡献

欢迎贡献！详见 [CONTRIBUTING.md](.claude/skills/industrial-deep-diagnostic/CONTRIBUTING.md)。

快速开始：
```bash
git clone https://github.com/kingdol666/industrial-deep-diagnostic.git
cd industrial-deep-diagnostic
npm install
npm link
ind-diag init
ind-diag all
```

---

## 许可证

本项目基于 **ISC License**。详见 [package.json](package.json)。

---

<p align="center">
  <sub>Built for industrial engineers, data scientists, and manufacturing operators.</sub>
  <br>
  <sub>© 2025–2026 Industrial Deep Diagnostic Contributors</sub>
</p>
