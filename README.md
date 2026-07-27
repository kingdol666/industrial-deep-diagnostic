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
  <sub>端到端工业深度诊断系统 · 12 Skills · 9 Agents · OMP + Claude Code 双 Harness</sub>
</p>

<p align="center">
  <a href="#"><img src="https://img.shields.io/badge/Windows-0078D6?style=flat-square&logo=windows&logoColor=white" alt="Windows"></a>
  <a href="#"><img src="https://img.shields.io/badge/macOS-000000?style=flat-square&logo=apple&logoColor=white" alt="macOS"></a>
  <a href="#"><img src="https://img.shields.io/badge/Linux-FCC624?style=flat-square&logo=linux&logoColor=black" alt="Linux"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-ISC-blue.svg?style=flat-square" alt="License"></a>
  <a href="#"><img src="https://img.shields.io/badge/node-%3E%3D18-brightgreen?style=flat-square&logo=node.js" alt="Node.js"></a>
  <a href="#"><img src="https://img.shields.io/badge/python-%3E%3D3.9-blue?style=flat-square&logo=python" alt="Python"></a>
  <img src="https://img.shields.io/badge/OMP-Multi--Skill%20Pipeline-8A2BE2?style=flat-square" alt="OMP">
  <img src="https://img.shields.io/badge/Claude%20Code-Compatible-58a6ff?style=flat-square" alt="Claude Code">
  <img src="https://img.shields.io/badge/output-中文%20%7C%20English-58a6ff?style=flat-square" alt="Language">
</p>

---

## 目录

- [项目简介](#项目简介)
- [核心能力](#核心能力)
- [快速开始](#快速开始)
- [使用指南](#使用指南)
- [诊断管线架构](#诊断管线架构)
- [Skill 与 Agent 体系](#skill-与-agent-体系)
- [系统架构](#系统架构)
- [项目结构](#项目结构)
- [配置管理](#配置管理)
- [Docker 部署](#docker-部署)
- [示例数据集](#示例数据集)

---

## 项目简介

**Industrial Deep Diagnostic** 是一个端到端的工业深度诊断系统，对传感器/工艺数据执行全自动根因分析。融合**多智能体编排**、**统计反假相关验证**、**物理第一性原理推理**和 **RAG 知识检索**，交付生产级诊断报告。

> **把它当作一个 24/7 在线的诊断工程师**——输入原始传感器数据（CSV/XLSX/Parquet），输出完整分析：数据质量检查、领域本体构建、统计验证、基于物理的根因假设、质量门审查、中文报告以及交互式 HTML 可视化。

系统基于 **12 个标准化 Skill** 和 **9 个专用 Agent**，通过 `industrial-analysis-auto` 编排器实现零人工干预的全自动管线。核心是**竞争假设协议**（Competing Hypotheses Protocol）——诊断不是确认单一原因，而是通过统计证据和物理推理逐一排除可能性。

**双 Harness 支持**：同时适配 OMP (Oh My Pi) 和 Claude Code，通过 `.omp/` 入口 + `.claude/` 资源的分层架构确保两套系统无缝运行。

---

## 核心能力

<table>
<tr>
<td width="50%">

### 科学诊断推理

- **竞争假设协议** — 至少 3 个竞争假设并行测试，用数据区分性消除
- **双驱动分析** — 纯工艺波动 + 工艺-检测双驱动，两种视角缺一不可
- **四条件因果判定** — 时间先后 + 统计显著 + 物理机制 + 无矛盾
- **七级证据体系 L1–L7** — 结论可信度受最低证据等级约束
- **Schema-First 输出** — 所有 JSON 产物 schema-valid，写前读 schema

### 反假相关统计引擎 (v6.4–v6.7)

- **Simpson 悖论检测** — 分层相关分析防聚合方向反转
- **时滞补偿 CCF** — 工艺→质量物理延迟的最优滞后相关
- **留一法杠杆检测** — |r|≥0.3 必须通过 leave-one-out（|Δr|>0.2 → EXCLUDE）
- **批次标识完整性** — batch_id 唯一性验证
- **生产稳态过滤** — 三算法融合排除启停过渡期

</td>
<td width="50%">

### 12-Skill 体系

| Skill | 角色 | 模型 |
|-------|------|:----:|
| `industrial-analysis-auto` | 全自动编排器 (Step 0–9) | default |
| `industrial-ontology-builder` | 领域本体构建 | default |
| `industrial-data-processor` | 统计+可视化+交接 | default |
| `industrial-vlm-analyzer` | VLM 图表视觉分析 | **vision** |
| `industrial-diagnostician` | 竞争假说根因诊断 | default |
| `industrial-judge` | 10 项质量门审查 | default |
| `industrial-physical-auditor` | 物理真相独立审计 | default |
| `industrial-reporter` | 9 节金字塔中文报告 | default |
| `industrial-html-visualizer` | ECharts+Three.js 可视化 | default |
| `industrial-html-reviewer` | HTML 可读性审校 | default |
| `rag-knowledge-builder` | RAG 本体自动构建 | default |
| `diagnostic-html-visualizer` | HTML 设计系统+模板 | — |

### 自修复管线

- **Judge best-of-3** — 最多 3 轮修复，追最高分，永不 halt
- **Reviewer 修复循环** — 完整 D→J→R→R，最多 2 轮
- **全局上限** — 总重诊断 ≤5，`.pipeline_events.jsonl` 持久化
- **反振荡保护** — 同问题第 3 次 → COMPETING_SET，置信度≤50

</td>
</tr>
</table>

---

## 快速开始

### 前置依赖

| 依赖 | 版本 | 必须 | 说明 |
|------|:----:|:----:|------|
| [Node.js](https://nodejs.org/) | ≥ 18 | ✅ | CLI、后端、管线脚本 |
| [Python](https://www.python.org/) | ≥ 3.9 | ⚠️ 仅诊断 | 统计分析+可视化 |
| [uv](https://docs.astral.sh/uv/) | latest | 🟡 推荐 | Python 包管理，自动安装 |

### 1. 安装

```bash
git clone https://github.com/kingdol666/industrial-deep-diagnostic.git
cd industrial-deep-diagnostic
npm install        # js-yaml 配置加载器等
npm link           # 可选：启用 ind-diag 全局命令
```

### 2. 启动

```bash
ind-diag init      # 初始化配置 + 数据库
ind-diag all       # 后端 (3210) + 前端 (5180) 一起启动
```

浏览器打开 `http://localhost:5180`，API 健康检查：`http://localhost:3210/api/health`

---

## 使用指南

### 运行诊断

**方式 A：对话触发（推荐）**

在 Claude Code / OMP 对话中直接说"诊断这个数据"或触发词（工业诊断、根因分析、故障诊断等），`industrial-analysis-auto` 编排器自动执行全管线。

产出：`report.md` + `diagnostic-report.html` + `optimizer.md` + `evidence_closure_report.json`

**方式 B：Web UI**

`http://localhost:5180` → Data 标签上传 → Diagnose 标签启动 → SSE 实时流 → Reports 标签查看

### CLI 命令

```bash
ind-diag <command>
```

| 命令 | 说明 |
|------|------|
| `init` | 初始化 — 校验配置、创建数据库 |
| `all` | 启动后端 + 前端 |
| `backend` / `frontend` | 单独启动服务 |
| `build` | 生产构建前端 |
| `status` | 项目状态 — 配置、数据、依赖 |
| `webfrp` | Cloudflare Tunnel 公网暴露 |
| `config get/set/reset` | 配置管理 |

### RAG 检索引擎（可选）

```bash
cd rag-retrieval-engine
uv run python server.py    # FastAPI → http://localhost:8765
```

不可用时管线自动降级：使用内置 `parameter_to_physics.json` + 网络搜索。

---

## 诊断管线架构

### 9 步执行流程

```
STEP 0:  SETUP        ── 创建运行目录、Python venv
STEP 1:  INSPECT      ── 数据探测、schema 提取
STEP 2:  CONTEXT      ── context-builder → ontology + RAG 深度理解
STEP 2.5: CLARIFY     ── 自动推断参数物理含义
STEP 3:  PROCESS      ── data-processor → 统计验证 + 可视化
STEP 3.5: VLM         ── vlm-visual-analyzer → 图表视觉证据 [vision model]
STEP 4:  DIAGNOSE     ── diagnostician → 竞争假说 + 4 个 JSON
STEP 5a: JUDGE   ┐    ← 唯一并行步骤
STEP 5b: PRE-AUDIT ┘    (物理审计预检)
STEP 6:  REPORT       ── reporter → 9 节金字塔中文报告
STEP 7:  FINAL AUDIT  ── report-reviewer → optimizer.md (ENDORSED)
STEP 8:  HTML VIZ     ── html-visualizer → ECharts+Three.js 页面
STEP 8.5: HTML REVIEW ── html-reviewer → 可读性审校
STEP 9:  FINALIZE     ── 证据闭环 + artifact 权威门禁
```

### 修复循环

| 规则 | 限制 |
|------|------|
| Judge best-of-3 | 最多 3 轮重诊断 |
| Reviewer 修复 | 最多 2 轮 D→J→R→R |
| 全局上限 | 总重诊断 ≤ 5 |
| 反振荡 | 同问题第 3 次 → COMPETING_SET |
| 永不 halt | 任何分数都产出报告 |

### 检查点门禁 (CP-1 ~ CP-9)

| CP | 位置 | 验证 | 失败→ |
|:--|------|------|-------|
| CP-1 | 1→2 | input_manifest + user_context | 回 Step 0 |
| CP-2 | 2→2.5 | ontology.json ≥1KB + schema-valid | 重跑 ontology |
| CP-3 | 2.5→3 | clarification AUTO_RESOLVED | 解决 |
| CP-4 | 3→4 | data_analysis_conclusion + plots>0 | 重跑 processor |
| CP-5 | 4→5 | 4 诊断输出 schema-valid | 修复 |
| CP-6 | 5→6 | judge_repair_summary + pre-audit | best-of-3 |
| CP-7 | 6→7 | report.md + run_summary.json | 重跑 reporter |
| CP-8 | 7→8 | optimizer.md ENDORSED | 修复循环 |
| CP-9 | 8.5 | diagnostic-report.html ≥5KB + review pass | 重跑 visualizer |

---

## Skill 与 Agent 体系

### 架构分层

```
.omp/skills/<name>/SKILL.md    ← OMP 发现入口 (thin wrapper)
    ↓ SKILL_PATH 重定向
.claude/skills/<name>/         ← 资源存储 (scripts/ schemas/ references/ resources/)
    ↓ 启动
.omp/agents/<name>.md          ← Agent 定义 (model + tools + protocol)
    ↓ 读取
references/agent-protocol.md   ← 完整执行协议 (Phase 0-N)
```

### Agent 映射表

| Agent | Skill | Model | 人格 |
|-------|-------|:-----:|------|
| `context-builder` | `industrial-ontology-builder` | default | 王教授 · 失效分析 |
| `data-processor` | `industrial-data-processor` | default | 张工 · 流程分析 |
| `vlm-visual-analyzer` | `industrial-vlm-analyzer` | **vision** | 老孙 · 目视巡检 |
| `diagnostician` | `industrial-diagnostician` | default | 刘总工 · 根因诊断 |
| `judge` | `industrial-judge` | default | 陈主任 · 质量审计 |
| `report-reviewer` | `industrial-physical-auditor` | default | 孙审计 · 物理审计 |
| `reporter` | `industrial-reporter` | default | 周工 · 技术报告 |
| `html-visualizer` | `industrial-html-visualizer` | default | 林工 · HMI 可视化 |
| `html-reviewer` | `industrial-html-reviewer` | default | 赵审阅 · 页面审校 |

### 关键约定

- **路径约定**: `SKILL_PATH` 始终解析到 `.claude/skills/<name>/`，通过 `<this-skill-directory>/../../../.claude/skills/<name>` 实现
- **Agent 解耦**: 子 Agent 仅通过 workspace 文件通信，不依赖主 Agent 上下文
- **Schema-First**: 所有 JSON 写前读 schema，写后立即 `validate.mjs`
- **Python venv**: 所有脚本使用 `$SKILL_PATH/scripts/.venv/bin/python`

---

## 系统架构

### 三层系统

```
┌─────────────────────────────────────────────────┐
│  Skill Layer (.omp/skills/ + .claude/skills/)   │
│  12 Skills × 9 Agents × 自动编排                │
│  RAG 知识检索 · 统计验证 · 物理推理 · 报告生成   │
├─────────────────────────────────────────────────┤
│  Web Application                                │
│  Express.js (3210) + Vue 3/Vite (5180)          │
│  SQLite (WAL) · WebSocket · SSE 实时流          │
├─────────────────────────────────────────────────┤
│  RAG Retrieval Engine (port 8765)               │
│  FastAPI + ChromaDB · 向量+关键词混合检索       │
│  5 维评分 · 本体注入 · 降级路径                 │
└─────────────────────────────────────────────────┘
```

### 诊断产出目录

```
workspace/diagnostic-runs/<timestamp>_<scene>/
├── 00_input/              # 输入数据 + 用户上下文
├── 01_ontology/           # 领域本体 + RAG 深度理解
├── 02_processed/          # 清洗/验证/特征/异常报告
├── 03_figures/            # 可视化图表 + VLM 分析
├── 04_diagnostics/        # 诊断/证据/置信度/推理链
├── 05_review/             # Judge 评审 + HTML 审校
├── report.md              # 9 节金字塔中文报告
├── diagnostic-report.html # 交互式可视化页面
├── optimizer.md           # 物理审计优化建议
└── .pipeline_events.jsonl # 执行证明日志
```

---

## 项目结构

```
industrial-deep-diagnostic/
├── .omp/                       # OMP Harness 入口
│   ├── agents/                 # 9 个 Agent 定义 (model + protocol ref)
│   ├── skills/                 # 12 个 Skill 发现入口 (SKILL.md)
│   └── AGENTS.md               # OMP 项目上下文
├── .claude/                    # Claude Code Harness + 资源存储
│   ├── agents/                 # Agent 定义 (.claude 格式)
│   └── skills/                 # 完整 Skill 资源 (scripts/schemas/references/...)
├── .hermes/                    # Hermes 编排配置
│   ├── agents.yaml             # Agent 模型+工具集配置
│   └── config.yaml             # Delegation + Vision 辅助模型
├── app/
│   ├── backend/                # Express.js API 服务
│   └── frontend/               # Vue 3 + Vite SPA
├── commands/                   # CLI 实现 (start.mjs, cli.mjs)
├── config/                     # 配置管理 (default.yaml + loader)
├── rag-retrieval-engine/       # RAG 微服务 (FastAPI + ChromaDB)
├── data/                       # 数据集 + 诊断运行
├── workspace/diagnostic-runs/  # 诊断产出目录
├── docs/                       # 文档 + logo
├── CLAUDE.md                   # Claude Code 项目上下文
├── AGENTS.md                   # 通用 Agent 项目上下文
└── README.md                   # 本文件
```

---

## 配置管理

配置优先级：`default.yaml` → `local.yaml` → 环境变量

```bash
ind-diag config list              # 查看合并配置
ind-diag config set server.port 8080
ind-diag config reset server.port
```

关键环境变量：`SERVER_PORT`, `CLAUDE_MODEL`, `DATA_DIR`, `DIAGNOSIS_DEFAULT_LANGUAGE`

---

## Docker 部署

```bash
docker-compose up -d              # 后端 + 前端 + Nginx
```

详见 `docker-compose.yml` 和 `nginx.conf`。

---

## 示例数据集

| 数据集 | 路径 | 工艺类型 |
|--------|------|---------|
| BOPET 薄膜划痕 | `data/bopet_scratch_lekai/` | 双向拉伸聚酯薄膜 |
| 水泥球磨机 | `data/cement_ball_mill/` | 水泥粉磨 |
| 流浆箱工艺 | `data/paper_machine_headbox/` | 造纸流浆箱 |
| 冷轧钢评估 | `data/eval_steel_cold_rolling/` | 钢铁冷轧 |
| 反应器催化剂 | `data/eval_reactor_catalyst/` | 化工催化反应 |
