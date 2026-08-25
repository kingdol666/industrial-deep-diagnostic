<p align="center">
  <img src="docs/logo.svg" width="140" alt="Industrial Deep Diagnostic">
</p>

<h1 align="center">Industrial Deep Diagnostic</h1>

<p align="center">
  <strong>端到端工业深度诊断系统 · 9 步全自动根因分析管线</strong><br>
  <sub>From sensor time-series to root-cause report — zero human intervention</sub>
</p>

<p align="center">
  <a href="#-快速开始"><img src="https://img.shields.io/badge/Quick%20Start-2%20Steps-brightgreen?style=flat-square" alt="Quick Start"></a>
  <a href="#-系统架构"><img src="https://img.shields.io/badge/Pipeline-9%20Steps-blue?style=flat-square" alt="Pipeline"></a>
  <a href="#-使用场景"><img src="https://img.shields.io/badge/Platform-Win%20%7C%20Linux%20%7C%20Mac-lightgrey?style=flat-square" alt="Platform"></a>
  <a href="https://nodejs.org/"><img src="https://img.shields.io/badge/Node-%E2%89%A518-339933?style=flat-square&logo=nodedotjs&logoColor=white" alt="Node"></a>
  <a href="#-docker-部署"><img src="https://img.shields.io/badge/Docker-Ready-2496ED?style=flat-square&logo=docker&logoColor=white" alt="Docker"></a>
  <a href="https://github.com/kingdol666/industrial-deep-diagnostic"><img src="https://img.shields.io/badge/Version-6.7-blueviolet?style=flat-square" alt="Version"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-success?style=flat-square" alt="License"></a>
</p>

<p align="center">
  <b>中文</b> · <a href="#-english-overview">English</a>
</p>

---

> 💡 **核心思想**: 诊断 = **排除** 而非确认。每个结论必须同时满足 **物理机制 + 统计验证 + 时序对齐 + 无反证**，缺一不可。系统不为取悦用户而编造结论 —— 它会诚实地告诉你 `DETERMINED`（已定论）、`COMPETING_SET`（竞争假说不可区分）或 `NEEDS_DATA`（数据不足）。

## ✨ 核心能力

<table>
<tr>
<td width="50%" valign="top">

### 🧠 智能诊断引擎
- **9 步全自动管线** — 从原始数据到中文报告零干预
- **18 个专业 Skill** × **14 个专用 Agent** 协同
- **竞争假设协议** — 排除法而非确认偏误
- **9 道质量门控** (CP-1 ~ CP-9) 逐级把关
- **反假相关统计** v6.4–v6.7（时滞 CCF / 稳态过滤 / 批次完整性 / 留一法）

</td>
<td width="50%" valign="top">

### 🛡 工业级可靠性
- **证据等级 L1–L7** — 结论受限最低证据等级
- **双驱动分析** — 纯工艺波动 + 工艺-检测双驱动
- **VLM 视觉验证** — Vision 模型独立审读图表
- **物理真实审计** — 双模式（预审 + 终审）ENDORSED 门禁
- **修复反振荡** — 同问题第 3 次自动降级，全局上限 5 次重诊断

</td>
</tr>
</table>

---

## 📑 目录

- [✨ 核心能力](#-核心能力)
- [🎯 使用场景](#-使用场景)
- [🚀 快速开始](#-快速开始)
- [🖥 系统架构](#-系统架构)
- [📦 安装](#-安装)
- [⌨️ CLI 命令手册](#️-cli-命令手册)
- [📊 使用方式](#-使用方式)
- [🔧 配置](#-配置)
- [🔌 API 文档](#-api-文档)
- [🐳 Docker 部署](#-docker-部署)
- [🗂 项目结构](#-项目结构)
- [🐛 故障排查](#-故障排查)
- [🤝 贡献](#-贡献)
- [📄 English Overview](#-english-overview)

---

## 🎯 使用场景

> 适用于任何 **"有数据、找根因"** 的工业分析场景。只要你能提供传感器时序数据或工艺参数记录，系统就能给出可追溯的诊断结论。

<table>
<tr>
<td width="33%" valign="top" align="center">

#### 🏭 制造过程异常

<b>质量缺陷 / 良率下降</b><br>
<sub>薄膜厚度漂移 · 钢板缺陷 · 纸张定量波动</sub>

</td>
<td width="33%" valign="top" align="center">

#### ⚙️ 设备状态诊断

<b>性能衰退 / 渐进故障</b><br>
<sub>CNC 主轴磨损 · 换热器结垢 · 催化剂失活</sub>

</td>
<td width="33%" valign="top" align="center">

#### 📈 工艺参数优化

<b>SPC Excursion / 相关性分析</b><br>
<sub>压力-厚度关联 · 温度-粘度因果 · 多变量权衡</sub>

</td>
</tr>
</table>

### 内置样本数据（开箱即用）

| 场景 | 路径 | 说明 |
|------|------|------|
| 🔄 **造纸机流浆箱** | `data/paper_machine_headbox/` | 已生成完整诊断报告（76 分置信度） |
| ⚙️ **CNC 主轴磨损** | `data/eval_cnc_spindle_wear/` | 含 ground truth 标注 |
| 🔥 **换热器结垢** | `data/eval_heat_exchanger_scaling/` | 渐进性退化经典案例 |
| 🎞 **BOPET 薄膜漂移** | `data/eval_bopet_film_drift/` | 多变量厚度分析 |
| ⚗️ **反应器催化剂失活** | `data/eval_reactor_catalyst/` | 化工过程诊断 |
| 🥶 **冷轧钢板缺陷** | `data/eval_steel_cold_rolling/` | 冶金质量分析 |
| 📊 **模拟过程数据** | `data/simulateData/merged_process_inspection.csv` | 综合工艺数据集 |

---

## 🚀 快速开始

> 通用步骤：Windows / Linux / macOS 任意主机均按此流程，无需平台特定配置。
> 依赖全自动：服务启动时自动检查并安装——backend/frontend 缺 `node_modules` 自动执行 `npm install`，RAG 引擎自动创建 Python 虚拟环境（`uv sync`，无 uv 时回退 pip）。
>
> **前置条件**（缺失时启动阶段会报错，先验证）：

| 依赖 | 版本 | 验证命令 |
|------|:----:|----------|
| [Node.js](https://nodejs.org/) | ≥ 18（推荐 22+） | `node --version` |
| [npm](https://www.npmjs.com/) | ≥ 9 | `npm --version` |
| [Python](https://www.python.org/) | ≥ 3.10 | `python --version`（Linux/macOS：`python3 --version`） |
| [uv](https://docs.astral.sh/uv/) | 推荐 | `uv --version`（未安装时自动回退系统 pip） |


### 三步起飞 🛫

```bash
# 1️⃣ 克隆 & 安装
git clone https://github.com/kingdol666/industrial-deep-diagnostic.git
cd industrial-deep-diagnostic
npm install
npm link                    # 注册全局 ind-diag 命令（可选；无权限时改用 node commands/cli.mjs）

# 2️⃣ 启动全套服务（后端 3210 + 前端 5180 + RAG 引擎 8764）
ind-diag start --all --detach
#    --detach = 后台守护模式，命令立即返回；日志写入 .runtime/*.log
#    首次启动自动安装依赖（backend/frontend npm install + RAG venv），约 1-3 分钟

# 3️⃣ 验证服务健康
ind-diag status                                          # 三服务均应运行且 healthy
curl http://localhost:3210/api/health                    # 应返回 200
```

打开 **http://localhost:5180** → 上传数据 → 自动诊断 → 下载报告 ✅

> ⚠️ 不要省略 `--detach`：前台模式（无 `--detach`）下 CLI 会阻塞并在 120 秒后报 `FATAL: Service manager timeout`（服务其实已启动，但命令不返回，易误判为失败）。
>
> 停止服务：`ind-diag stop --all` · 查看日志：`.runtime/backend.log`、`.runtime/frontend.log`、`.runtime/rag.log`
>
> 发起诊断还需要 [Claude Code CLI](https://docs.anthropic.com/) 且已登录或配置 `ANTHROPIC_API_KEY`（参考 `.env.example`）——仅启动服务不需要。


### 服务端口一览

| 服务 | 端口 | 技术栈 | 用途 |
|:----:|:----:|--------|------|
| 🟢 **Backend** | `3210` | Express.js + SQLite (WAL) + WebSocket | REST API · 诊断编排 · 实时推送 |
| 🟢 **Frontend** | `5180` | Vue 3 + Vite + SSE | Web UI · 数据上传 · 实时监控 |
| 🟢 **RAG Engine** | `8764` | FastAPI + ChromaDB | 向量检索 · 领域知识增强 |

<details>
<summary><b>🔍 验证服务是否启动成功</b></summary>

```bash
# 查看服务状态
ind-diag status

# 后端健康检查（应返回 200）
curl http://localhost:3210/api/health

# 前端可访问
curl -I http://localhost:5180

# RAG 引擎文档
curl -I http://localhost:8764/docs
```

</details>

<details>
<summary><b>⚡ 不启动前端，纯命令行跑一次诊断</b></summary>

```bash
# 使用 industrial-analysis-auto 编排器全自动执行
node .claude/skills/industrial-analysis-auto/scripts/setup.mjs \
  --name my-diagnosis --base-dir ./workspace/diagnostic-runs

# 产出位置：workspace/diagnostic-runs/<timestamp>_my-diagnosis/
# ├── report.md                    ← 中文诊断报告
# ├── diagnostic-report.html       ← HTML 可视化页面
# └── optimizer.md                 ← 物理审计结论
```

</details>

---

## 🖥 系统架构

### 9 步诊断管线全景

```
                         ┌─────────────────────────────────────┐
                         │        原始工业数据 (CSV/XLSX/...)     │
                         └──────────────────┬──────────────────┘
                                            │
                         ┌──────────────────▼──────────────────┐
                Step 0–1 │  Setup & Inspect  ·  数据探查 + 清单   │  ◄── CP-1
                         └──────────────────┬──────────────────┘
                                            │
                         ┌──────────────────▼──────────────────┐
                  Step 2 │  context-builder  ·  本体构建 + RAG    │  ◄── CP-2, CP-3
                         └──────────────────┬──────────────────┘
                                            │
                         ┌──────────────────▼──────────────────┐
                  Step 3 │  data-processor  ·  统计分析 + 图表    │  ◄── CP-4
                         │   └─ Step 3.5: VLM 视觉分析            │
                         └──────────────────┬──────────────────┘
                                            │
                         ┌──────────────────▼──────────────────┐
                  Step 4 │  diagnostician  ·  竞争假设根因分析    │  ◄── CP-5
                         └──────────────────┬──────────────────┘
                                            │
                ┌───────────────────────────┴───────────────────────────┐
                │  Step 5a: judge (质量评分)   │   Step 5b: pre-audit     │  ◄── CP-6
                │           ↑ 修复循环 ↓                    (并行)        │
                └───────────────────────────┬───────────────────────────┘
                                            │
                         ┌──────────────────▼──────────────────┐
                  Step 6 │  reporter  ·  生成 20 节中文报告       │  ◄── CP-7
                         └──────────────────┬──────────────────┘
                                            │
                         ┌──────────────────▼──────────────────┐
                  Step 7 │  report-reviewer  ·  物理终审         │  ◄── CP-8
                         │           ↑ 修复循环 ↓ (ENDORSED?)    │
                         └──────────────────┬──────────────────┘
                                            │
                         ┌──────────────────▼──────────────────┐
                Step 8–9 │  html-visualizer → html-reviewer     │  ◄── CP-9
                         │  → Finalize  ·  交付诊断报告 + HTML    │
                         └─────────────────────────────────────┘
```

### 一个真实诊断的推导过程

以 **造纸机流浆箱工段** 为例（[查看完整报告](workspace/diagnostic-runs/202607271128116_paper_machine_headbox/report.md)）:

| 步骤 | 发现 |
|:----:|------|
| 1️⃣ **数据发现** | 流浆箱压力 90 天从 15kPa → 29kPa（**+93%**）；CD 定量 CV 从 0.5% → 2.8%（**+460%**） |
| 2️⃣ **统计验证** | pressure~cdcv Pearson r=0.87，去趋势后 r=0.57；留一法通过；三个纸种内 r=0.92~0.93 |
| 3️⃣ **物理机制** | 风扇泵转速仅 +4.1%，按泵相似定律预期 +8.4%，实际 +93% → **11 倍超额 → 流阻增大** |
| 4️⃣ **排除竞争** | ❌ 温度假说（98.6% 衰减）· ❌ 真空系统（r<0.03）· ❌ 转速驱动（11 倍超额） |
| 5️⃣ **根因结论** | 流浆箱内部渐进性结垢/堵塞 — `DETERMINED`，置信度 **76/100** |
| 6️⃣ **行动方案** | P0 停机酸洗 · P1 校验传感器 · P2 安装 CD 压力分布传感器 |

> 每个结论均标注 **证据等级（L1–L7）**，推理链可追溯至具体数据行。

### 18 个专业 Skill

<details>
<summary><b>展开查看完整 Skill 清单</b></summary>

| Skill | 所属 Agent | 核心产出 | 门控 |
|-------|------------|----------|:----:|
| **industrial-analysis-auto** | main-agent | 全自动编排器 | 所有 CP |
| **industrial-data-preprocessor** | — | 自适应多格式前处理 | — |
| **industrial-ontology-builder** | context-builder | `ontology.json`, RAG 深度理解 | CP-2, CP-3 |
| **industrial-data-processor** | data-processor | `data_analysis_conclusion.json`, 9+ PNG | CP-4 |
| **industrial-diagnostician** | diagnostician | 4× 诊断 JSON（诊断/证据/置信度/推理链） | CP-5 |
| **industrial-judge** | judge | `judge_feedback.json`（10 项评分） | CP-6 |
| **industrial-physical-auditor** | report-reviewer | `optimizer.md`（双模式审计） | CP-6, CP-8 |
| **industrial-reporter** | reporter | `report.md`, `run_summary.json` | CP-7 |
| **industrial-html-visualizer** | html-visualizer | `diagnostic-report.html`（ECharts+Three.js） | CP-9 |
| **industrial-html-reviewer** | html-reviewer | `html_review.json` | — |
| **industrial-physics-bridge** | physics-bridge | 物理-数据桥接 | — |
| **industrial-deep-analysis** | deep-analyst | E1–E4 深层覆盖矩阵 | — |
| **industrial-analysis-enhance-auto** | enhance-orchestrator | 增强管线编排 | — |
| **industrial-enhanced-html-visualizer** | enhanced-visualizer | 增强版 HTML | — |
| **industrial-enhanced-html-reviewer** | enhanced-html-reviewer | 增强版 HTML 审校 | — |
| **rag-knowledge-builder** | — | 领域知识图谱 | — |
| **diagnostic-html-visualizer** | — | HTML 设计系统 | — |
| **darwin-skill** | — | Skill 进化评估 | — |

</details>

### 9 道质量门控 (Checkpoint Gates)

| CP | 位置 | 验证内容 | 失败处理 |
|:--:|:----:|----------|:--------:|
| **1** | 1→2 | `input_manifest` + `user_context` 存在 | 回 Step 0 |
| **2** | 2→2.5 | `ontology.json` ≥1KB + schema 校验通过 | 重跑 ontology |
| **3** | 2.5→3 | `clarification_status: AUTO_RESOLVED` | 引导解决 |
| **4** | 3→4 | `data_analysis_conclusion.json` + plots > 0 | 重跑 processor |
| **5** | 4→5 | 4 个诊断 JSON schema 全部通过 | 重跑 diagnostician (≤3) |
| **6** | 5→6 | Judge ≥90 + pre-audit 无 FATAL | 修复循环 (best-of-3) |
| **7** | 6→7 | `report.md` + `run_summary.json` | 重跑 reporter |
| **8** | 7→8 | `optimizer.md` 含 `ENDORSED` | 审计修复循环 |
| **9** | 8→8.5 | HTML ≥5KB + review verdict=pass | 重跑 visualizer |

### 证据等级体系

| 等级 | 来源 | 置信度权重 |
|:----:|------|:----------:|
| **L1** | 直接测量值 | 🟢 最高 |
| **L2** | 用户文档（SOP / 手册） | 🟢 高 |
| **L3** | 统计分析（含验证报告） | 🟡 中高 |
| **L4** | 图表视觉证据（VLM） | 🟡 中 |
| **L5** | 领域知识 / 工艺逻辑 | 🟡 中 |
| **L6** | 外部网络引用 | 🔴 低 |
| **L7** | 无支持假设 | ⚫ 最低 |

### 反假相关统计管线

| 版本 | 检测能力 | 方法 |
|:----:|----------|------|
| **v6.4** | 时滞补偿 CCF | 互相关函数计算最优迟滞，避免虚假同步 |
| **v6.5** | 稳态过滤 | 三算法融合检测稳态/过渡/启停段 |
| **v6.6** | 批次完整性 | `batch_id` 唯一性验证，防止跨批次混淆 |
| **v6.7** | 留一法杠杆检查 | \|r\|≥0.3 必须通过 leave-one-out |

---

## 📦 安装

### 环境依赖

| 依赖 | 版本 | 验证命令 |
|------|:----:|----------|
| [Node.js](https://nodejs.org/) | ≥ 18（推荐 22+） | `node --version` |
| [npm](https://www.npmjs.com/) | ≥ 9 | `npm --version` |
| [Python](https://www.python.org/) | ≥ 3.10 | `python --version` |
| [uv](https://docs.astral.sh/uv/)（可选） | ≥ 0.4 | `uv --version` |

### Windows 安装

```powershell
# 克隆并安装
git clone https://github.com/kingdol666/industrial-deep-diagnostic.git
cd industrial-deep-diagnostic
npm install
npm link                    # 注册 ind-diag 全局命令

# 环境检查 + 初始化
ind-diag init

# 启动
ind-diag start --all --detach
```

也可双击运行批处理脚本（旧版，仅覆盖后端 + 前端，**不含 RAG 引擎**；完整启动请用上方 CLI 命令）：
- `commands\start-backend.bat` — 启动后端
- `commands\start-frontend.bat` — 启动前端
- `commands\start-all.bat` — 同时启动

### Linux / macOS 安装

```bash
# 克隆并安装
git clone https://github.com/kingdol666/industrial-deep-diagnostic.git
cd industrial-deep-diagnostic
npm install
npm link                    # 注册全局 ind-diag 命令（可选；无权限时改用 node commands/cli.mjs）

# 环境检查
ind-diag init

# 启动
ind-diag start --all --detach

# 或使用 Shell 脚本
bash commands/start-all.sh
```

### Python 依赖（RAG 引擎 + 统计分析）

**无需手动安装** —— `ind-diag start` 会自动：检查系统 Python → 若 `rag-retrieval-engine/.venv` 不存在则创建 → `uv sync`（无 uv 时回退系统 pip）安装全部依赖。

只需保证存在以下任一（`python --version` 验证）：
- Python ≥ 3.10（RAG 运行必需）
- **uv**（推荐，RAG 依赖自动隔离安装；未安装时自动回退 pip）

需要手动安装时（可选，例如国内网络加速）：

```bash
# 方式一：uv（推荐，自动隔离 + 镜像加速）
export UV_INDEX_URL=https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple
uv sync --directory rag-retrieval-engine

# 方式二：pip + 镜像
pip install -r rag-retrieval-engine/requirements.txt \
  -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple
```

---

## ⌨️ CLI 命令手册

全局命令通过 `ind-diag`（注册后）或 `node commands/cli.mjs` 使用。

### 服务管理

| 命令 | 用途 | 示例 |
|------|------|------|
| `start --all` | 启动全部服务（后台守护） | `ind-diag start --all --detach` |
| `start --backend` | 仅启动后端 (3210) | `ind-diag start --backend --detach` |
| `start --frontend` | 仅启动前端 (5180) | `ind-diag start --frontend --detach` |
| `start --rag` | 启动 RAG 引擎 (8764) | `ind-diag start --rag --detach` |
| `stop --all` | 停止全部服务 | `ind-diag stop --all` |
| `restart --all` | 重启全部服务 | `ind-diag restart --all --detach` |
| `status` | 查看服务状态 | `ind-diag status` |
| `init` | 环境检查（Node/npm/Python/端口） | `ind-diag init` |
| `build` | 前端生产构建 | `ind-diag build` |
| `webfrp` | Cloudflare Tunnel 公网暴露 | `ind-diag webfrp` |

> **`--detach` 为推荐用法**（后台守护）：命令立即返回，服务日志写入 `.runtime/*.log`。省略 `--detach` 时 CLI 会保持前台输出并最终报 `FATAL: Service manager timeout`——服务不受影响，但命令不会正常结束。

### npm 快捷脚本

```bash
npm start              # = ind-diag start --all --detach
npm run start:backend  # = ind-diag start --backend --detach
npm run start:frontend # = ind-diag start --frontend --detach
npm run start:rag      # = ind-diag start --rag --detach
npm stop               # = ind-diag stop --all
npm run status         # = ind-diag status
npm run restart        # = ind-diag restart --all --detach
npm run build          # = ind-diag build
npm run init           # = ind-diag init
```

### 诊断管线脚本（高级）

<details>
<summary><b>🔧 手动驱动诊断管线各阶段</b></summary>

```bash
# 1. 创建运行目录
node .claude/skills/industrial-analysis-auto/scripts/setup.mjs \
  --name <场景名> --base-dir ./workspace/diagnostic-runs

# 2. 数据探查
node .claude/skills/industrial-analysis-auto/scripts/inspect.mjs \
  <数据文件> --rows 10

# 3. 管道事件日志（诊断中自动调用）
node .claude/shared/scripts/append-pipeline-event.mjs \
  <运行目录> --event agent_start --agent <agent名>

# 4. 管道日志验证
node .claude/skills/industrial-analysis-auto/scripts/pipeline-log-check.mjs \
  <运行目录>

# 5. JSON Schema 验证
node .claude/shared/scripts/validate.mjs \
  .claude/shared/schemas/diagnosis_schema.json \
  workspace/diagnostic-runs/<run>/04_diagnostics/diagnosis.json

# 6. Python venv 初始化
node .claude/shared/scripts/uv_env_setup.mjs \
  --skill-path .claude/skills/industrial-data-processor
```

</details>

---

## 📊 使用方式

### 方式一：Web UI（推荐）🌐

1. 启动服务：`ind-diag start --all --detach`
2. 打开 **http://localhost:5180**
3. 上传数据文件（CSV / XLSX / Parquet）
4. 填写场景名称与分析问题
5. 实时观察 9 步管线进度
6. 下载 `report.md` + 打开 `diagnostic-report.html`

### 方式二：命令行全自动 🖥

```bash
# 创建运行目录并启动编排
node .claude/skills/industrial-analysis-auto/scripts/setup.mjs \
  --name cnc-test --base-dir ./workspace/diagnostic-runs

# 主 Agent 自动按 Step 0-9 顺序调度子 Agent
# 产出在 workspace/diagnostic-runs/<timestamp>_cnc-test/
```

### 方式三：交互模式 💬

支持三种交互模式（`config/default.yaml` → `diagnosis.interaction_mode`）：

| 模式 | 行为 | 适用场景 |
|------|------|----------|
| `auto` | 全自动，零干预 | 批量分析、生产环境 |
| `interactive` | 关键决策点等待用户确认 | 精细控制、研究分析 |
| `minimal` | 仅必要问题 | 快速验证 |

### 查看历史诊断

```bash
# 列出所有运行
ls workspace/diagnostic-runs/

# 查看报告
cat workspace/diagnostic-runs/<run>/report.md

# Windows 打开 HTML
start workspace/diagnostic-runs/<run>/diagnostic-report.html

# macOS 打开 HTML
open workspace/diagnostic-runs/<run>/diagnostic-report.html
```

---

## 🔧 配置

配置优先级：`环境变量` > `config/local.yaml` > `config/default.yaml`

<details>
<summary><b>📄 config/default.yaml 关键配置</b></summary>

```yaml
server:
  port: 3210                       # 后端端口
  body_limit: "10mb"

frontend:
  port: 5180                       # 前端端口
  backend_url: "http://localhost:3210"
  ws_url: "ws://localhost:3210"

database:
  path: "data/diagnostic.db"
  journal_mode: "WAL"              # WAL 模式提升并发

claude:
  model: "claude-opus-4-7"         # 核心模型
  max_turns: 200                   # 单次诊断最大轮次
  timeout_minutes: 120

diagnosis:
  default_language: "zh"           # zh | en
  interaction_mode: "auto"         # auto | interactive | minimal

data:
  upload:
    max_file_size_mb: 500          # 单文件上限
    max_files: 50

pipeline:
  max_judge_repair: 3              # Judge 修复上限
  max_reviewer_cycles: 2           # 审计循环上限
  global_rediagnosis_cap: 5        # 全局重诊断上限
```

</details>

### 环境变量覆盖

| 变量 | 对应配置 | 说明 |
|------|---------|------|
| `SERVER_PORT` | `server.port` | 后端端口 |
| `CLAUDE_MODEL` | `claude.model` | Claude 模型 ID |
| `DATA_DIR` | `data.dir` | 数据目录 |
| `DIAGNOSIS_DEFAULT_LANGUAGE` | `diagnosis.default_language` | 输出语言 |
| `DIAGNOSIS_INTERACTION_MODE` | `diagnosis.interaction_mode` | 交互模式 |
| `ANTHROPIC_API_KEY` | — | Claude API 密钥 |
| `ANTHROPIC_BASE_URL` | — | API 基础 URL（第三方代理） |

---

## 🔌 API 文档

所有 API 通过 Express 后端（port 3210）提供，前端通过 Vite 代理 `/api` 调用。

### 健康检查

```http
GET /api/health
```

```json
{
  "status": "ok",
  "timestamp": "2026-07-28T15:42:42.258Z",
  "uptime": 841.89,
  "memory": { "rss": "66MB", "heapUsed": "13MB", "heapTotal": "16MB" },
  "checks": { "database": { "status": "ok" }, "activeRuns": 0 }
}
```

### 核心端点

| 分类 | 端点 | 方法 | 用途 |
|------|------|:----:|------|
| **文件** | `/api/files/data` | GET | 列出数据文件 |
| | `/api/files/data/folder` | POST | 创建文件夹 |
| | `/api/files/data/file/:path` | GET | 读取文件内容 |
| | `/api/files/workspace` | GET | 列出诊断运行 |
| | `/api/files/workspace/report/:name` | GET | 获取诊断报告 |
| **诊断** | `/api/diagnosis/start` | POST | 启动新诊断 |
| | `/api/diagnosis/execute/:runId` | POST | 执行诊断 |
| | `/api/diagnosis/status/:runId` | GET | 查询运行状态 |
| | `/api/diagnosis/snapshot/:runId` | GET | 获取快照 |
| | `/api/diagnosis/stop/:runId` | POST | 停止运行 |
| | `/api/diagnosis/list` | GET | 列出所有运行 |
| | `/api/diagnosis/stream/:runId` | GET | SSE 事件流 |
| **聊天** | `/api/diagnosis/chat/:runId` | POST | 诊断对话 |
| | `/api/diagnosis/hitl/:hitlId` | POST | 人工审批 |
| | `/api/chat/start` | POST | 启动聊天会话 |
| | `/api/chat/stream/:chatId` | GET | SSE 聊天流 |

### WebSocket 实时推送

```
ws://localhost:3210/ws
```

实时推送诊断进度、日志和事件（心跳 30s，超时 60s）。

---

## 🐳 Docker 部署

```bash
# 构建并后台启动
docker compose up -d

# 查看日志
docker compose logs -f

# 停止
docker compose down
```

### 数据持久化（Docker Volumes）

```yaml
volumes:
  - ./data:/app/data                       # 数据文件
  - ./workspace:/app/workspace             # 诊断产出
  - ./config/local.yaml:/app/config/local.yaml:ro  # 本地配置
```

### 多架构支持

| 架构 | 状态 | 说明 |
|------|:----:|------|
| `linux/amd64` | ✅ | 标准 x86_64 服务器 |
| `linux/arm64` | ✅ | Apple Silicon / ARM 服务器 |
| `windows/amd64` | ✅ | WSL2 环境 |

> Dockerfile 基于 `node:22-alpine`，多阶段构建，镜像体积优化。

---

## 🗂 项目结构

```
industrial-deep-diagnostic/
├── commands/                       # CLI 与服务管理
│   ├── cli.mjs                    # 统一 CLI 入口 (ind-diag)
│   ├── service-manager.mjs        # 服务生命周期管理
│   ├── cross-platform.mjs         # 交叉平台工具库
│   └── start-*.bat/.sh            # 平台专用启动脚本
│
├── app/
│   ├── backend/                   # Express.js 后端 (port 3210)
│   │   └── src/
│   │       ├── index.mjs          # 服务入口
│   │       ├── routes/            # REST API 路由
│   │       ├── services/          # 业务逻辑
│   │       ├── engine/            # 诊断引擎
│   │       ├── transport/         # WebSocket
│   │       └── db/                # SQLite (WAL)
│   │
│   └── frontend/                  # Vue 3 + Vite 前端 (port 5180)
│       └── src/
│           ├── App.vue            # 主视图
│           ├── api/               # API 客户端
│           ├── components/        # UI 组件
│           └── stores/            # 状态管理
│
├── .claude/skills/                # 18 个 Skill 实现（唯一源）
│   ├── industrial-analysis-auto/  # 全自动编排器
│   ├── industrial-data-processor/ # 统计分析
│   ├── industrial-diagnostician/  # 竞争假设诊断
│   └── ...                        # scripts/schemas/resources
│
├── .omp/agents/                   # 14 个 OMP Agent 定义
│   ├── context-builder.md
│   ├── diagnostician.md
│   └── ...
│
├── rag-retrieval-engine/          # RAG 检索微服务 (port 8764)
│   ├── server.py                  # FastAPI 入口
│   └── engine/                    # 检索/评分/注入引擎
│
├── config/
│   ├── default.yaml               # 默认配置
│   ├── loader.mjs                 # 配置加载器
│   └── local.yaml                 # 用户覆盖（gitignored）
│
├── data/                          # 样本数据 & 仿真数据
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
└── package.json
```

---

## 🐛 故障排查

<details>
<summary><b>❌ "ind-diag: command not found"</b></summary>

```bash
# 使用完整路径
node commands/cli.mjs status

# 或重新注册全局命令
npm link
```

</details>

<details>
<summary><b>❌ 端口被占用 (EADDRINUSE :3210 / :5180 / :8764)</b></summary>

```powershell
# Windows
netstat -ano | findstr :3210
taskkill /F /PID <PID>
```

```bash
# Linux / macOS
lsof -ti :3210 | xargs kill -9
```

</details>

<details>
<summary><b>❌ 启动后命令卡住 / 报 "FATAL: Service manager timeout"</b></summary>

原因：使用了前台模式（省略了 `--detach`）。服务可能已经启动（`ind-diag status` 可确认），但 CLI 因前台等待而超时。

```bash
# 改为后台守护模式启动
ind-diag stop --all
ind-diag start --all --detach
```
</details>

<details>
<summary><b>❌ RAG 引擎启动失败（Python / venv）</b></summary>

RAG 引擎依赖由一个 `rag-retrieval-engine/start.mjs` 自动管理：检测系统 Python → 创建 `.venv` → `uv sync`（或 pip）→ 启动。

排查顺序：
```bash
# 1. 确认 Python ≥ 3.10
python --version        # Linux/macOS: python3 --version

# 2. 确认系统有 uv 或 pip（二选一即可）
uv --version || pip --version

# 3. 国内网络慢 → 用镜像手动安装后重启
export UV_INDEX_URL=https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple
uv sync --directory rag-retrieval-engine
ind-diag restart --all --detach
```

如仍失败，查看日志：`.runtime/rag.log`
</details>

<details>
<summary><b>❌ 服务已启动但无法发起诊断（报 Claude 相关错误）</b></summary>

诊断管线由 Claude Code CLI 驱动，需要：

```bash
# 1. 确认已安装 Claude Code
claude --version

# 2. 确认已登录或配置 API Key（可选：写入 .env）
cp .env.example .env   # 然后编辑 ANTHROPIC_API_KEY

# 3. 参考 config/default.yaml → claude 段（模型、binary 名可配置）
```
</details>

<details>
<summary><b>❌ 前端页面白屏</b></summary>

```bash
# 1. 确认后端运行
curl http://localhost:3210/api/health

# 2. 重新构建前端
cd app/frontend && npx vite build

# 3. 清除 Vite 缓存
rm -rf app/frontend/node_modules/.vite
```

</details>

<details>
<summary><b>❌ 诊断报告不生成 / 管道卡住</b></summary>

```bash
# 检查管道事件日志
cat workspace/diagnostic-runs/<run>/.pipeline_events.jsonl

# 验证管道完整性
node .claude/skills/industrial-analysis-auto/scripts/pipeline-log-check.mjs \
  workspace/diagnostic-runs/<run>

# 检查各步骤产物
ls -la workspace/diagnostic-runs/<run>/
```

</details>

<details>
<summary><b>❌ RAG 引擎依赖下载慢（国内网络）</b></summary>

```bash
# 使用清华镜像
export UV_INDEX_URL=https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple
uv sync --directory rag-retrieval-engine

# 或 pip 镜像
pip install -r rag-retrieval-engine/requirements.txt \
  -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple
```

</details>

---

## 🤝 贡献

### 开发流程

1. Fork 本仓库
2. 创建特性分支：`git checkout -b feat/my-feature`
3. 提交变更（遵循 Conventional Commits）
4. 推送并提交 Pull Request

### 提交规范

```
feat:     新功能          fix:      缺陷修复
docs:     文档变更        refactor: 重构
test:     测试            chore:    构建/工具
style:    格式            perf:     性能优化
```

### 扩展诊断管线（添加新 Skill）

1. 在 `.claude/skills/<name>/SKILL.md` 定义技能入口（含脚本 + Schema + 协议）
2. 在 `.omp/agents/<name>.md` 定义 Agent（OMP 契约：name + description + tools + model）
3. 在 `industrial-analysis-auto/SKILL.md` 注册步骤
4. 添加对应的 JSON Schema 到 `.claude/shared/schemas/`

---

## 📄 English Overview

**Industrial Deep Diagnostic** is an end-to-end automated root-cause analysis system for industrial sensor and process data. It runs a **9-step diagnostic pipeline** powered by **18 specialized skills** and **14 dedicated agents**, producing Chinese-language diagnostic reports and interactive HTML visualizations.

**Key principles:**
- **Diagnosis = Elimination, not confirmation.** Every conclusion must satisfy physical mechanism + statistical validation + temporal alignment + no counter-evidence.
- **Evidence-graded conclusions** (L1–L7) with full traceability to source data rows.
- **Anti-spurious-correlation** statistical pipeline (v6.4–v6.7): lag-CCF, steady-state filtering, batch integrity, leave-one-out leverage check.
- **9 checkpoint gates** (CP-1 ~ CP-9) ensure quality at every pipeline stage.
- **Honest uncertainty:** outputs `DETERMINED`, `COMPETING_SET`, or `NEEDS_DATA` — never fabricates conclusions.

**Quick start:**
```bash
git clone https://github.com/kingdol666/industrial-deep-diagnostic.git
cd industrial-deep-diagnostic
npm install
npm link                    # 注册全局 ind-diag 命令（可选；无权限时改用 node commands/cli.mjs）
ind-diag start --all --detach     # → http://localhost:5180
```

---

## 📜 License

[MIT](LICENSE) © kingdol666

---

<p align="center">
  <sub>Built with ❤️ for the industrial AI community</sub><br>
  <sub>If this project helps you, please consider giving it a ⭐ on GitHub</sub>
</p>
