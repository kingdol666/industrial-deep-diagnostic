<p align="center">
  <img src="docs/logo.svg" width="120" alt="Industrial Deep Diagnostic">
</p>
<h1 align="center">Industrial Deep Diagnostic</h1>
<p align="center">
  <em>端到端工业深度诊断系统 — 9 步全自动根因分析管线</em>
</p>

<p align="center">
  <a href="#quick-start"><img src="https://img.shields.io/badge/quick--start-2%20steps-brightgreen" alt="Quick Start"></a>
  <a href="#installation"><img src="https://img.shields.io/badge/platform-win%20%7C%20linux%20%7C%20mac-blue" alt="Platform"></a>
  <a href="https://github.com/kingdol666/industrial-deep-diagnostic"><img src="https://img.shields.io/badge/version-6.7-blue" alt="Version"></a>
  <a href="https://nodejs.org/"><img src="https://img.shields.io/badge/node-%3E%3D18-339933" alt="Node"></a>
  <a href="#-docker"><img src="https://img.shields.io/badge/docker-ready-2496ED" alt="Docker"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green" alt="License"></a>
</p>

<p align="center">
  <b>中文</b> · <a href="#quick-start">English</a>
</p>

---

工业数据（传感器/工艺参数）上传后，系统通过 **9 步全自动诊断管线** 生成中文诊断报告 + HTML 可视化页面。

**核心原则：诊断 = 排除而非确认**。每个结论必须满足物理机制 + 统计验证 + 时序对齐 + 无反证，缺一不可。

**示例产出**：[造纸机流浆箱诊断报告](workspace/diagnostic-runs/202607271128116_paper_machine_headbox/report.md)（11.5KB · 76 分置信度 · 5 竞争假说 · 3 排除）

---

## Table of Contents

- [Quick Start](#quick-start)
- [How It Works](#how-it-works)
- [Installation](#installation)
- [CLI Reference](#cli-reference)
- [Usage Examples](#usage-examples)
- [Pipeline Architecture](#pipeline-architecture)
- [API Documentation](#api-documentation)
- [Docker](#-docker)
- [Configuration](#configuration)
- [Project Structure](#project-structure)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## Quick Start

```bash
# 1. 克隆 & 安装
git clone https://github.com/kingdol666/industrial-deep-diagnostic.git
cd industrial-deep-diagnostic
npm install
npm link                    # 注册 ind-diag 命令

# 2. 启动服务（后端 + 前端）
ind-diag start --all

# 3. 打开浏览器 http://localhost:5180
#    上传数据 → 自动诊断 → 下载报告
```

**一键运行诊断**（无需前端，命令行直接出报告）:
```bash
# 使用内置样本数据运行完整诊断
node .claude/skills/industrial-analysis-auto/scripts/setup.mjs \
  --name my-diagnosis --base-dir ./workspace/diagnostic-runs

# 产出的报告在 workspace/diagnostic-runs/<timestamp>_my-diagnosis/
```

---

## How It Works

传感器时序数据输入后，系统自动执行以下管线：

```
原始数据 ──→ 领域本体构建 ──→ 统计分析 ──→ 竞争假说诊断 ──→ 质量门审查
    │                                                          │
    └─── 物理审计 ←── 报告生成 ←── HTML 可视化 ←── 终审交付
```

### 一个真实诊断的推导过程

以 **造纸机流浆箱工段** 为例（[完整报告](workspace/diagnostic-runs/202607271128116_paper_machine_headbox/report.md)）：

1. **数据发现**：流浆箱压力 90 天从 15kPa → 29kPa（+93%），CD 定量 CV 从 0.5% → 2.8%（+460%）
2. **统计验证**：pressure~cdcv Pearson r=0.87，去趋势后 r=0.57，留一法通过，三个纸种内 r=0.92~0.93
3. **物理机制**：风扇泵转速仅 +4.1%，根据泵相似定律预期压力 +8.4%，实际 +93% → 11 倍超额 → 流阻增大
4. **排除竞争**：排除温度假说（98.6% 衰减）、真空系统异常（r<0.03）、转速驱动（11 倍超额）
5. **根因结论**：流浆箱内部渐进性结垢/堵塞（DETERMINED，置信度 76/100）
6. **行动方案**：P0 停机酸洗，P1 校验传感器，P2 安装 CD 压力分布传感器

每个结论均标注证据等级（L1-L7），推理链可追溯至具体数据行。

---

## Installation

### Prerequisites

| 依赖 | 版本要求 | 验证命令 |
|------|---------|---------|
| [Node.js](https://nodejs.org/) | ≥ 18 (推荐 22+) | `node --version` |
| [npm](https://www.npmjs.com/) | ≥ 9 | `npm --version` |
| [Python](https://www.python.org/) | ≥ 3.10 | `python --version` |
| [uv](https://docs.astral.sh/uv/) (可选) | ≥ 0.4 | `uv --version` |

Python 依赖（统计分析用）：
```bash
pip install numpy pandas scipy matplotlib seaborn
```

### Windows 用户

```powershell
# 以管理员身份运行 PowerShell
npm install -g windows-build-tools  # 如需编译原生模块

# 克隆并安装
git clone https://github.com/kingdol666/industrial-deep-diagnostic.git
cd industrial-deep-diagnostic
npm install
npm link

# 检查环境
ind-diag init

# 启动
ind-diag start --all
```

也可双击运行：
- `commands\start-backend.bat` — 启动后端
- `commands\start-frontend.bat` — 启动前端
- `commands\start-all.bat` — 同时启动

### Linux / macOS

```bash
# 克隆并安装
git clone https://github.com/kingdol666/industrial-deep-diagnostic.git
cd industrial-deep-diagnostic
npm install
npm link

# 检查环境
ind-diag init

# 启动
ind-diag start --all

# 或使用 Shell 脚本
bash commands/start-all.sh
```

### Docker

```bash
# 构建并启动
docker compose up -d

# 查看日志
docker compose logs -f

# 停止
docker compose down
```

详见 [Docker 部署](#-docker)。

### 验证安装

```bash
# 确认所有服务可启动
ind-diag init
ind-diag status
ind-diag start --backend --frontend
ind-diag status  # 应显示 running

# 后端健康检查
curl http://localhost:3210/api/health

# 测试数据解析
node .claude/skills/industrial-analysis-auto/scripts/inspect.mjs \
  data/simulateData/merged_process_inspection.csv --rows 5
```

---

## CLI Reference

全局命令通过 `ind-diag`（注册后）或 `node commands/cli.mjs` 使用：

| 命令 | 用途 | 示例 |
|------|------|------|
| `start --all` | 启动全部服务 | `ind-diag start --all` |
| `start --backend` | 启动后端 (port 3210) | `ind-diag start --backend` |
| `start --frontend` | 启动前端 (port 5180) | `ind-diag start --frontend` |
| `start --rag` | 启动 RAG 引擎 (port 8765) | `ind-diag start --rag` |
| `stop --all` | 停止全部服务 | `ind-diag stop --all` |
| `status` | 查看服务状态 | `ind-diag status` |
| `init` | 环境检查+初始化 | `ind-diag init` |
| `build` | 前端生产构建 | `ind-diag build` |

### 诊断管线命令

诊断管线由各 Skill 脚本驱动，非直接 CLI：

```bash
# 1. 创建运行目录
node .claude/skills/industrial-analysis-auto/scripts/setup.mjs \
  --name <场景名> --base-dir ./workspace/diagnostic-runs

# 2. 数据探查
node .claude/skills/industrial-analysis-auto/scripts/inspect.mjs \
  <数据文件路径> --rows 10

# 3. 管道事件日志（诊断过程中自动调用）
node .claude/shared/scripts/append-pipeline-event.mjs \
  <运行目录> --event agent_start --agent <agent名称>

# 4. 管道日志验证
node .claude/skills/industrial-analysis-auto/scripts/pipeline-log-check.mjs \
  <运行目录>

# 5. 管道最终化验证
node .claude/skills/industrial-analysis-auto/scripts/pipeline-finalize.mjs \
  <运行目录> <.claude/skills/industrial-analysis-auto>
```

### 共享工具

```bash
# JSON Schema 验证
node .claude/shared/scripts/validate.mjs \
  .claude/shared/schemas/diagnosis_schema.json \
  workspace/diagnostic-runs/<run>/04_diagnostics/diagnosis.json

# Python venv 初始化
node .claude/shared/scripts/uv_env_setup.mjs \
  --skill-path .claude/skills/industrial-data-processor

# 管道事件归档
node .claude/shared/scripts/log-agent-event.mjs \
  <运行目录> <agent名称> start|complete [--files f1,f2]
```

---

## Usage Examples

### 使用内置样本数据

项目预置多组工业场景样本数据：

```bash
# CNC 主轴磨损评估
data/eval_cnc_spindle_wear/data.csv
data/eval_cnc_spindle_wear/ground_truth.md

# 换热器结垢诊断
data/eval_heat_exchanger_scaling/data.csv

# BOPET 薄膜厚度漂移
data/eval_bopet_film_drift/data.csv

# 反应器催化剂失活
data/eval_reactor_catalyst/data.csv

# 冷轧钢板缺陷分析
data/eval_steel_cold_rolling/data.csv

# 模拟过程数据
data/simulateData/merged_process_inspection.csv

# 造纸机流浆箱数据（已产生完整诊断报告）
data/paper_machine_headbox/
```

### 命令行运行完整诊断

```bash
# 1. 创建运行目录
RUN_DIR=$(node .claude/skills/industrial-analysis-auto/scripts/setup.mjs \
  --name cnc-test --base-dir ./workspace/diagnostic-runs \
  | node -e "process.stdin.on('data',d=>console.log(JSON.parse(d).run_dir))")

# 2. 探查数据
node .claude/skills/industrial-analysis-auto/scripts/inspect.mjs \
  data/eval_cnc_spindle_wear/data.csv --rows 10 > "$RUN_DIR/00_input/input_manifest.json"

# 3. 执行诊断（启动子 Agent）
# 主 Agent 按 Step 0-9 顺序调用子 Agent：
# Step 2 → context-builder → ontology.json
# Step 3 → data-processor → data_analysis_conclusion.json
# Step 4 → diagnostician → diagnosis.json + evidence.json + ...
# Step 5 → judge + report-reviewer → judge_feedback.json
# Step 6 → reporter → report.md
# Step 7 → report-reviewer → optimizer.md
# Step 8 → html-visualizer → diagnostic-report.html
```

### 查看已完成的诊断

```bash
# 列表所有运行
ls workspace/diagnostic-runs/

# 查看诊断报告
cat workspace/diagnostic-runs/*/report.md | head -50

# 打开 HTML 可视化
start workspace/diagnostic-runs/*/diagnostic-report.html  # Windows
open workspace/diagnostic-runs/*/diagnostic-report.html   # macOS
```

---

## Pipeline Architecture

### 9 步诊断管线

```
Step 0: Setup ──► Step 1: Inspect
                         │
                         ▼
              Step 2: context-builder (Ontology + RAG)
                         │
                         ▼
              Step 2.5: Clarification Gate
                         │
                         ▼
              Step 3: data-processor (Statistics + Plots)
                         │
                         ▼
              Step 4: diagnostician (Competing Hypotheses)
                         │
              ┌──────────┴──────────┐
              │ Step 5a: judge       │◄── repair ──┐
              │ Step 5b: pre-audit   │             │
              │ (parallel)           │             │
              └──────────┬──────────┘             │
                         │ pass                    │
                         ▼                        │
                   Step 6: reporter               │
                         │                        │
                         ▼                        │
              Step 7: report-reviewer ────────────┘
                         │ ENDORSED
                         ▼
              Step 8: html-visualizer
                         │
                         ▼
              Step 8.5: html-reviewer
                         │ PASS
                         ▼
                   Step 9: Finalize
```

### 12 个子 Skill

| Skill | Agent | 产出 | 门控 |
|-------|-------|------|:----:|
| **industrial-ontology-builder** | context-builder | `ontology.json`, `rag_deep_understanding.json` | CP-2, CP-3 |
| **industrial-data-processor** | data-processor | `data_analysis_conclusion.json`, 9+ PNG | CP-4 |
| **industrial-diagnostician** | diagnostician | 4× 诊断 JSON (diagnosis/evidence/confidence/reasoning_chain) | CP-5 |
| **industrial-judge** | judge | `judge_feedback.json` (10项评分) | CP-6 |
| **industrial-physical-auditor** | report-reviewer | `optimizer.md` (双模式审计) | CP-6, CP-8 |
| **industrial-reporter** | reporter | `report.md`, `run_summary.json` | CP-7 |
| **industrial-html-visualizer** | html-visualizer | `diagnostic-report.html` (ECharts+Three.js) | CP-9 |
| **industrial-html-reviewer** | html-reviewer | `html_review.json` | — |
| **rag-knowledge-builder** | — | 领域知识图谱 | — |
| **diagnostic-html-visualizer** | — | HTML 设计系统 | — |
| **industrial-analysis-auto** | — | **全自动编排器** | 所有 CP |

### 9 道质量门控 (Checkpoint Gates)

| CP | 位置 | 验证 | 失败处理 |
|:--:|:----:|------|:--------:|
| 1 | 1→2 | `input_manifest` + `user_context` 存在 | 重回 Step 0 |
| 2 | 2→2.5 | `ontology.json` ≥1KB + schema 校验通过 | 重跑 ontology-builder |
| 3 | 2.5→3 | `clarification_status: AUTO_RESOLVED\|USER_CONFIRMED` | 自动推断 |
| 4 | 3→4 | `data_analysis_conclusion.json` + plots > 0 | 重跑 data-processor |
| 5 | 4→5 | 4个诊断 JSON schema 校验全部通过 | 重跑 diagnostician (≤3) |
| 6 | 5→6 | Judge score ≥90 + pre-audit 无 FATAL | 修复循环 (best-of-3) |
| 7 | 6→7 | `report.md` + `run_summary.json` 存在 | 重跑 reporter |
| 8 | 7→8 | `optimizer.md` 含 `ENDORSED` | 审计修复循环 |
| 9 | 8→8.5 | HTML ≥5KB + review verdict=pass | 重跑 html-visualizer |

### 反假相关统计管线 (v6.4-v6.7)

| 版本 | 检测 | 方法 |
|:----:|------|------|
| v6.4 | 时滞补偿 CCF | 互相关函数计算最优迟滞 |
| v6.5 | 稳态过滤 | 三算法融合检测稳态/过渡/启停 |
| v6.6 | 批次完整性 | batch_id 唯一性验证 |
| v6.7 | 留一法杠杆检查 | \|r\|≥0.3 必须通过留一法 |

---

## API Documentation

所有 API 通过 Express 后端（port 3210）提供，前端通过 Vite 代理 `/api` 调用。

### 健康检查

```http
GET /api/health
```

响应：
```json
{
  "status": "ok",
  "timestamp": "2026-07-28T15:42:42.258Z",
  "uptime": 841.89,
  "memory": { "rss": "66MB", "heapUsed": "13MB", "heapTotal": "16MB" },
  "checks": {
    "database": { "status": "ok" },
    "activeRuns": 0
  }
}
```

### 文件管理

| 端点 | 方法 | 用途 |
|------|------|------|
| `/api/files/data` | GET | 列出数据文件 |
| `/api/files/data/folder` | POST | 创建数据文件夹 |
| `/api/files/data/folder/:name` | DELETE | 删除文件夹 |
| `/api/files/data/file/:path` | GET | 读取文件内容 |
| `/api/files/workspace` | GET | 列出诊断运行 |
| `/api/files/workspace/report/:name` | GET | 获取诊断报告 |
| `/api/files/workspace/optimizer/:name` | GET | 获取审计结果 |

### 诊断执行

| 端点 | 方法 | 用途 |
|------|------|------|
| `/api/diagnosis/start` | POST | 启动新诊断 |
| `/api/diagnosis/execute/:runId` | POST | 执行诊断 |
| `/api/diagnosis/status/:runId` | GET | 查询运行状态 |
| `/api/diagnosis/snapshot/:runId` | GET | 获取快照 |
| `/api/diagnosis/stop/:runId` | POST | 停止运行 |
| `/api/diagnosis/list` | GET | 列出所有运行 |
| `/api/diagnosis/stream/:runId` | GET | SSE 事件流 |

### 聊天 & HITL

| 端点 | 方法 | 用途 |
|------|------|------|
| `/api/diagnosis/chat/:runId` | POST | 诊断对话 |
| `/api/diagnosis/hitl/:hitlId` | POST | 人工审批 |
| `/api/chat/start` | POST | 启动聊天会话 |
| `/api/chat/send/:chatId` | POST | 发送消息 |
| `/api/chat/stream/:chatId` | GET | SSE 聊天流 |

### WebSocket

```
ws://localhost:3210/ws
```

实时推送诊断进度、日志和事件。

---

## 🐳 Docker

### 构建 & 启动

```bash
# 构建镜像
docker compose build

# 启动服务（后台）
docker compose up -d

# 查看日志
docker compose logs -f

# 停止
docker compose down
```

### 配置

通过 `docker-compose.yml` 环境变量配置：

```yaml
environment:
  - CLAUDE_API_KEY=${CLAUDE_API_KEY:-}      # Claude API 密钥（可选）
  - CLAUDE_API_BASE_URL=${CLAUDE_API_BASE_URL:-}
  - LOGGING_FORMAT=json
  - LOGGING_LEVEL=info
```

### 数据持久化

```bash
# Docker volumes 映射
volumes:
  - ./data:/app/data                       # 数据文件
  - ./workspace:/app/workspace             # 诊断产出
  - ./config/local.yaml:/app/config/local.yaml:ro  # 本地配置
```

### 多架构

Dockerfile 使用 `node:22-alpine`，支持：

| 架构 | 支持 |
|------|:----:|
| linux/amd64 | ✅ |
| linux/arm64 | ✅ (Apple Silicon) |
| windows/amd64 | ✅ (WSL2) |

---

## Configuration

配置文件为 `config/default.yaml`，用户覆盖写入 `config/local.yaml`：

```yaml
# config/default.yaml (项目默认)
server:
  port: 3210
  body_limit: 100mb

frontend:
  port: 5180
  backend_url: http://localhost:3210
  ws_url: http://localhost:3210

database:
  path: ./data/diagnostic.db

diagnosis:
  default_language: zh-CN
  interaction_mode: auto  # auto | interactive | minimal

claude:
  model: claude-sonnet-4-20250514
  max_tokens: 8192

pipeline:
  max_judge_repair: 3
  max_reviewer_cycles: 2
  global_rediagnosis_cap: 5

data:
  upload_dir: .uploads
  upload:
    max_file_size_mb: 100
  folder_name_pattern: "^[a-zA-Z0-9_\\-\\u4e00-\\u9fff]{1,64}$"

security:
  cors_origin: "*"

websocket:
  max_message_size: 1048576
```

环境变量覆盖（优先级高于 local.yaml）：

| 变量 | 配置路径 |
|------|---------|
| `SERVER_PORT` | `server.port` |
| `CLAUDE_MODEL` | `claude.model` |
| `DIAGNOSIS_DEFAULT_LANGUAGE` | `diagnosis.default_language` |
| `DIAGNOSIS_INTERACTION_MODE` | `diagnosis.interaction_mode` |

---

## Project Structure

```
industrial-deep-diagnostic/
├── commands/                       # CLI 与服务管理
│   ├── cli.mjs                    # 统一 CLI 入口 (ind-diag)
│   ├── service-manager.mjs        # 服务生命周期管理
│   ├── cross-platform.mjs         # 交叉平台工具库
│   ├── start.mjs                  # 跨平台服务启动器
│   ├── start-all.bat/.sh          # 平台专用启动脚本
│   └── ...
│
├── app/
│   ├── backend/                   # Express.js 后端 (port 3210)
│   │   └── src/
│   │       ├── index.mjs          # 服务入口
│   │       ├── routes/            # REST API 路由
│   │       ├── services/          # 业务逻辑
│   │       ├── engine/            # 诊断引擎
│   │       └── db/                # SQLite 数据库
│   │
│   └── frontend/                  # Vue 3 + Vite 前端 (port 5180)
│       └── src/
│           ├── App.vue            # 主视图
│           ├── api/               # API 客户端
│           ├── components/        # UI 组件
│           └── stores/            # 状态管理
│
├── .omp/                          # OMP 技能系统
│   ├── skills/                    # 12 个 Skill 定义
│   │   ├── industrial-analysis-auto/
│   │   ├── industrial-ontology-builder/
│   │   ├── industrial-data-processor/
│   │   └── ...
│   └── agents/                    # 9 个 Agent 定义
│
├── .claude/
│   ├── skills/                    # Skill 实现 (scripts/schemas/resources)
│   │   ├── industrial-analysis-auto/scripts/
│   │   ├── industrial-data-processor/scripts/stats/
│   │   └── ...
│   ├── agents/                    # 完整 Agent 协议
│   ├── shared/                    # 共享脚本 & Schema
│   │   ├── scripts/
│   │   └── schemas/              # 15 个 JSON Schema
│   └── ...
│
├── rag-retrieval-engine/          # RAG 检索微服务 (FastAPI, port 8765)
│   ├── server.py                  # FastAPI 服务
│   ├── start.mjs                  # 跨平台启动器
│   └── engine/                    # 检索/评分/本体注入引擎
│
├── config/
│   ├── default.yaml               # 默认配置
│   ├── loader.mjs                 # 配置加载器
│   └── local.yaml                 # 用户覆盖（gitignored）
│
├── data/                          # 样本数据 & 仿真数据
│   ├── simulateData/
│   ├── paper_machine_headbox/
│   ├── eval_cnc_spindle_wear/
│   ├── eval_reactor_catalyst/
│   ├── eval_bopet_film_drift/
│   └── ...
│
├── workspace/diagnostic-runs/     # 诊断运行产出
│   └── <timestamp>_<name>/
│       ├── 00_input/              # 输入 & 配置
│       ├── 01_ontology/           # 领域本体
│       ├── 02_processed/          # 统计 & 清洗
│       ├── 03_figures/            # 图表 & VLM
│       ├── 04_diagnostics/        # 诊断结论
│       ├── 05_review/             # 评审 & 审计
│       ├── report.md              # 中文诊断报告
│       ├── diagnostic-report.html # HTML 可视化
│       └── .pipeline_events.jsonl # 事件日志
│
├── docs/                          # 文档 & 架构图
├── Dockerfile                     # 多阶段构建
├── docker-compose.yml             # Docker Compose
├── nginx.conf                     # Nginx 反向代理配置
└── package.json                   # 项目元数据
```

---

## Troubleshooting

### "ind-diag: command not found"

```bash
# 使用完整路径
node commands/cli.mjs status

# 或重新注册
npm link
```

### 后端启动失败 (EADDRINUSE)

```bash
# 端口 3210 已被占用，终止旧进程
# Windows
netstat -ano | findstr :3210
taskkill /F /PID <PID>

# Linux/macOS
lsof -ti :3210 | xargs kill -9
```

### Python 模块缺失

```bash
# 安装 Python 依赖
pip install numpy pandas scipy matplotlib seaborn pyyaml

# 或使用 uv（推荐）
uv sync --directory rag-retrieval-engine
```

### 前端页面白屏

```bash
# 1. 检查后端是否运行
curl http://localhost:3210/api/health

# 2. 检查前端构建
cd app/frontend && npx vite build

# 3. 清除缓存
rm -rf app/frontend/node_modules/.vite
```

### 诊断报告不生成 / 管道卡住

```bash
# 检查管道事件日志
cat workspace/diagnostic-runs/<run>/.pipeline_events.jsonl

# 验证管道完整性
node .claude/skills/industrial-analysis-auto/scripts/pipeline-log-check.mjs \
  workspace/diagnostic-runs/<run>

# 检查各步骤产物
ls -la workspace/diagnostic-runs/<run>/
```

### RAG 引擎依赖下载慢

```bash
# 设置镜像源
export UV_INDEX_URL=https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple
uv sync --directory rag-retrieval-engine

# 或使用 pip
pip install -r rag-retrieval-engine/requirements.txt -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple
```

### Windows 脚本执行问题

```powershell
# 使用 PowerShell 运行
node commands\cli.mjs start --all

# 或使用 .bat 脚本
.\commands\start-all.bat
```

---

## Contributing

### 开发流程

1. Fork 本仓库
2. 创建特性分支: `git checkout -b feat/my-feature`
3. 提交变更: `git commit -am 'feat: add my feature'`
4. 推送分支: `git push origin feat/my-feature`
5. 提交 Pull Request

### 提交规范

使用 Conventional Commits:

```
feat: 新功能
fix: 缺陷修复
docs: 文档变更
refactor: 重构
test: 测试
chore: 构建/工具
```

### 本地开发

```bash
# 安装依赖
npm install

# 前后端同时开发
# 终端 1: 后端
node commands/start.mjs backend

# 终端 2: 前端
cd app/frontend && npx vite

# 运行测试
node .claude/skills/industrial-analysis-auto/scripts/setup.mjs \
  --name dev-test --base-dir ./workspace/diagnostic-runs
```

### 项目扩展

添加新的诊断 Skill：

1. 在 `.omp/skills/<name>/SKILL.md` 定义技能入口
2. 在 `.omp/agents/<name>.md` 定义 Agent
3. 在 `.claude/skills/<name>/` 实现脚本 + Schema
4. 在 `industrial-analysis-auto/SKILL.md` 注册步骤

---

## License

[MIT](LICENSE) © kingdol666

---

<p align="center">
  <sub>Built with ❤️ for the industrial AI community</sub>
</p>
