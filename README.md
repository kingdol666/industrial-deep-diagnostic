<p align="center">
  <img src="docs/logo.svg" width="140" alt="Industrial Deep Diagnostic">
</p>

<h1 align="center">Industrial Deep Diagnostic</h1>

<p align="center">
  <strong>End-to-end industrial deep-diagnosis system · 9-step fully automated root-cause pipeline</strong><br>
  <sub>From sensor time-series to root-cause report — zero human intervention</sub>
</p>

<p align="center">
  <a href="#-quick-start"><img src="https://img.shields.io/badge/Quick%20Start-2%20Steps-brightgreen?style=flat-square" alt="Quick Start"></a>
  <a href="#-system-architecture"><img src="https://img.shields.io/badge/Pipeline-9%20Steps-blue?style=flat-square" alt="Pipeline"></a>
  <a href="#-use-cases"><img src="https://img.shields.io/badge/Platform-Win%20%7C%20Linux%20%7C%20Mac-lightgrey?style=flat-square" alt="Platform"></a>
  <a href="https://nodejs.org/"><img src="https://img.shields.io/badge/Node-%E2%89%A518-339933?style=flat-square&logo=nodedotjs&logoColor=white" alt="Node"></a>
  <a href="#-docker-deployment"><img src="https://img.shields.io/badge/Docker-Ready-2496ED?style=flat-square&logo=docker&logoColor=white" alt="Docker"></a>
  <a href="https://github.com/kingdol666/industrial-deep-diagnostic"><img src="https://img.shields.io/badge/Version-6.7-blueviolet?style=flat-square" alt="Version"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-success?style=flat-square" alt="License"></a>
</p>

<p align="center">
  <b>English</b> · <a href="#-english-overview">Overview</a>
</p>

---

> 💡 **Core idea**: diagnosis = **elimination**, not confirmation. Every conclusion must satisfy **physical mechanism + statistical validation + temporal alignment + no counter-evidence** — all four, no exceptions. The system never fabricates a conclusion to please the user: it will honestly tell you `DETERMINED` (settled), `COMPETING_SET` (competing hypotheses are indistinguishable) or `NEEDS_DATA` (insufficient data).

## ✨ Core Capabilities

<table>
<tr>
<td width="50%" valign="top">

### 🧠 Intelligent Diagnostic Engine
- **9-step fully automated pipeline** — zero intervention from raw data to Chinese report
- **18 specialized skills** × **14 dedicated agents** working in concert
- **Competing-hypotheses protocol** — elimination instead of confirmation bias
- **9 quality gates** (CP-1 ~ CP-9) enforced stage by stage
- **Anti-spurious-correlation statistics** v6.4–v6.7 (lag CCF / steady-state filtering / batch integrity / leave-one-out)

</td>
<td width="50%" valign="top">

### 🛡 Industrial-Grade Reliability
- **Evidence levels L1–L7** — a conclusion is bounded by its lowest evidence level
- **Dual-driver analysis** — pure process fluctuation + combined process-and-inspection drivers
- **VLM visual verification** — a vision model independently reads the charts
- **Physical-truth audit** — dual mode (pre-audit + final audit) with an ENDORSED gate
- **Repair anti-oscillation** — the third attempt at the same problem is downgraded automatically; global cap of 5 rediagnoses

</td>
</tr>
<tr>
<td width="50%" valign="top">

### ⚙ Dual-Engine Harness (new in v6.8)
- **Genuinely swappable execution engines** — native bridges to the Claude Code SDK and OMP RPC, switched with one click in the frontend
- **Isomorphic event streams across both engines** — tool calls / thinking / subagent orchestration stay visible in real time throughout
- **Session continuity** — both engines support resuming a conversation across processes and carrying diagnostic context forward
- **Per-run routing** — every diagnosis records its execution engine, and the History page shows an `OMP` badge for traceability

</td>
<td width="50%" valign="top">

### 🗺 Ontology Assetization + Deep Enhancement (new in v6.8)
- **Ontology asset library** — data-schema fingerprint matching; same-scenario reuse hits in seconds and **cuts a single diagnosis by ~70%**
- **Incremental extension** — newly added columns trigger only an incremental build and merge, versioned over time (`provenance` traceable end to end)
- **Intent-driven deep enhancement** — saying "deep diagnosis" automatically chains the deterministic E0-E8 enhancement pipeline (zero LLM cost, +3–5 minutes)
- **Knowledge flywheel** — enhancement artifacts feed back into the RAG knowledge base, so it gets more accurate the more you use it

</td>
</tr>
</table>

---

## ⚡ Performance Design (optimization plan v4 shipped)

| Mechanism | Trigger | Effect |
|------|---------|------|
| **Ontology reuse** | data-column schema fingerprint hits the asset library (on by default in `auto` mode) | ontology build 15.6 min → **≤0.5 min** |
| **Incremental ontology extension** | same-scenario schema evolution (new columns) | only the diff columns are retrieved and built, saving 60%+ |
| **Subagent stop-loss** | the ontology subagent produces nothing for 8 minutes | the main agent falls back locally, avoiding a 12-minute idle spin |
| **Targeted repair** | a Judge score of 70-89 triggers a repair round | only the affected dimensions are recomputed, saving 40-60% |
| **Parallel profiling** | data profiling and ontology building have no semantic dependency | serial becomes parallel, saving another 2-4 min |
| **RAG fast-fail** | the 3s health pre-check fails | falls straight back to local physical priors, zero idle spin |

> See [docs/skill-optimization-plan-v4.md](docs/skill-optimization-plan-v4.md) for measured timeline evidence and the acceptance gate of each optimization.

---

## 📑 Table of Contents

- [✨ Core Capabilities](#-core-capabilities)
- [🎯 Use Cases](#-use-cases)
- [🚀 Quick Start](#-quick-start)
- [🖥 System Architecture](#-system-architecture)
- [📦 Installation](#-installation)
- [⌨️ CLI Reference](#️-cli-reference)
- [📊 Usage](#-usage)
- [🔧 Configuration](#-configuration)
- [🔌 API Reference](#-api-reference)
- [🐳 Docker Deployment](#-docker-deployment)
- [🗂 Project Structure](#-project-structure)
- [🐛 Troubleshooting](#-troubleshooting)
- [🤝 Contributing](#-contributing)
- [📄 English Overview](#-english-overview)

---

## 🎯 Use Cases

> Applies to any industrial analysis scenario where you **have data and need the root cause**. As long as you can supply sensor time series or process-parameter records, the system will produce a traceable diagnostic conclusion.

<table>
<tr>
<td width="33%" valign="top" align="center">

#### 🏭 Manufacturing Process Anomalies

<b>Quality defects / yield loss</b><br>
<sub>Film thickness drift · steel plate defects · paper basis-weight fluctuation</sub>

</td>
<td width="33%" valign="top" align="center">

#### ⚙️ Equipment Condition Diagnosis

<b>Performance degradation / progressive faults</b><br>
<sub>CNC spindle wear · heat-exchanger fouling · catalyst deactivation</sub>

</td>
<td width="33%" valign="top" align="center">

#### 📈 Process Parameter Optimization

<b>SPC excursion / correlation analysis</b><br>
<sub>pressure-thickness association · temperature-viscosity causality · multivariate tradeoffs</sub>

</td>
</tr>
</table>

### Bundled Sample Data (works out of the box)

| Scenario | Path | Notes |
|------|------|------|
| 🔄 **Paper machine headbox** | `data/paper_machine_headbox/` | full diagnostic report already generated (76-point confidence) |
| ⚙️ **CNC spindle wear** | `data/eval_cnc_spindle_wear/` | includes ground-truth labels |
| 🔥 **Heat-exchanger fouling** | `data/eval_heat_exchanger_scaling/` | classic progressive-degradation case |
| 🎞 **BOPET film drift** | `data/eval_bopet_film_drift/` | multivariate thickness analysis |
| ⚗️ **Reactor catalyst deactivation** | `data/eval_reactor_catalyst/` | chemical-process diagnosis |
| 🥶 **Cold-rolled steel defects** | `data/eval_steel_cold_rolling/` | metallurgical quality analysis |
| 📊 **Simulated process data** | `data/simulateData/merged_process_inspection.csv` | composite process dataset |

---

## 🚀 Quick Start

> The same steps apply on any Windows / Linux / macOS host; no platform-specific configuration is required.
> Dependencies are fully automatic: the service checks and installs them at startup — if backend/frontend lack `node_modules` it runs `npm install`, and the RAG engine creates its own Python virtual environment (`uv sync`, falling back to pip when uv is absent).
>
> **Prerequisites** (startup fails if they are missing, so verify first):

| Dependency | Version | Verification command |
|------|:----:|----------|
| [Node.js](https://nodejs.org/) | ≥ 18 (22+ recommended) | `node --version` |
| [npm](https://www.npmjs.com/) | ≥ 9 | `npm --version` |
| [Python](https://www.python.org/) | ≥ 3.10 | `python --version` (Linux/macOS: `python3 --version`) |
| [uv](https://docs.astral.sh/uv/) | recommended | `uv --version` (falls back to system pip when not installed) |


### Three Steps to Take Off 🛫

```bash
# 1️⃣ Clone & install
git clone https://github.com/kingdol666/industrial-deep-diagnostic.git
cd industrial-deep-diagnostic
npm install
npm link                    # register the global ind-diag command (optional; without privileges use node commands/cli.mjs)

# 2️⃣ Start all services (backend 3210 + frontend 5180 + RAG engine 8764)
ind-diag start --all --detach
#    --detach = background daemon mode, the command returns immediately; logs go to .runtime/*.log
#    The first start installs dependencies automatically (backend/frontend npm install + RAG venv), about 1-3 minutes

# 3️⃣ Verify service health
ind-diag status                                          # all three services should be running and healthy
curl http://localhost:3210/api/health                    # should return 200
```

Open **http://localhost:5180** → upload data → automatic diagnosis → download the report ✅

> ⚠️ Do not omit `--detach`: in foreground mode (no `--detach`) the CLI blocks and after 120 seconds reports `FATAL: Service manager timeout` (the services have actually started, but the command never returns, which is easily mistaken for a failure).
>
> Stop the services: `ind-diag stop --all` · logs: `.runtime/backend.log`, `.runtime/frontend.log`, `.runtime/rag.log`
>
> Starting a diagnosis additionally requires the [Claude Code CLI](https://docs.anthropic.com/) to be logged in or `ANTHROPIC_API_KEY` to be configured (see `.env.example`) — merely starting the services does not.


### Service Ports at a Glance

| Service | Port | Stack | Purpose |
|:----:|:----:|--------|------|
| 🟢 **Backend** | `3210` | Express.js + SQLite (WAL) + WebSocket | REST API · diagnosis orchestration · real-time push |
| 🟢 **Frontend** | `5180` | Vue 3 + Vite + SSE | Web UI · data upload · live monitoring |
| 🟢 **RAG Engine** | `8764` | FastAPI + ChromaDB | vector retrieval · domain knowledge augmentation |

<details>
<summary><b>🔍 Verify that the services started successfully</b></summary>

```bash
# check service status
ind-diag status

# backend health check (should return 200)
curl http://localhost:3210/api/health

# frontend is reachable
curl -I http://localhost:5180

# RAG engine docs
curl -I http://localhost:8764/docs
```

</details>

<details>
<summary><b>⚡ Run one diagnosis from the command line, without starting the frontend</b></summary>

```bash
# drive the industrial-analysis-auto orchestrator fully automatically
node .claude/skills/industrial-analysis-auto/scripts/setup.mjs \
  --name my-diagnosis --base-dir ./workspace/diagnostic-runs

# output location: workspace/diagnostic-runs/<timestamp>_my-diagnosis/
# ├── report.md                    ← Chinese diagnostic report
# ├── diagnostic-report.html       ← HTML visualization page
# └── optimizer.md                 ← physical audit verdict
```

</details>

---

## 🖥 System Architecture

### The 9-Step Diagnostic Pipeline at a Glance

```
                         ┌─────────────────────────────────────┐
                         │  Raw industrial data (CSV/XLSX/...) │
                         └──────────────────┬──────────────────┘
                                            │
                         ┌──────────────────▼──────────────────┐
                Step 0–1 │  Setup & Inspect · probe & manifest │  ◄── CP-1
                         └──────────────────┬──────────────────┘
                                            │
                         ┌──────────────────▼──────────────────┐
                  Step 2 │  context-builder · ontology + RAG   │  ◄── CP-2, CP-3
                         └──────────────────┬──────────────────┘
                                            │
                         ┌──────────────────▼──────────────────┐
                  Step 3 │  data-processor · stats + charts    │  ◄── CP-4
                         │   └─ Step 3.5: VLM visual analysis  │
                         └──────────────────┬──────────────────┘
                                            │
                         ┌──────────────────▼──────────────────┐
                  Step 4 │  diagnostician · competing causes   │  ◄── CP-5
                         └──────────────────┬──────────────────┘
                                            │
                ┌───────────────────────────┴───────────────────────────┐
                │  Step 5a: judge (score)   │   Step 5b: pre-audit      │  ◄── CP-6
                │      ↑ repair loop ↓      │        (parallel)         │
                └───────────────────────────┬───────────────────────────┘
                                            │
                         ┌──────────────────▼──────────────────┐
                  Step 6 │  reporter · 20-section zh report    │  ◄── CP-7
                         └──────────────────┬──────────────────┘
                                            │
                         ┌──────────────────▼──────────────────┐
                  Step 7 │  report-reviewer · physical audit   │  ◄── CP-8
                         │      ↑ repair loop ↓ (ENDORSED?)    │
                         └──────────────────┬──────────────────┘
                                            │
                         ┌──────────────────▼──────────────────┐
                Step 8–9 │  html-visualizer → html-reviewer    │  ◄── CP-9
                         │  → Finalize · deliver report + HTML │
                         └─────────────────────────────────────┘
```

### How a Real Diagnosis Was Derived

Taking the **paper machine headbox section** as an example ([view the full report](workspace/diagnostic-runs/202607271128116_paper_machine_headbox/report.md)):

| Step | Finding |
|:----:|------|
| 1️⃣ **Data discovery** | headbox pressure went from 15kPa → 29kPa over 90 days (**+93%**); CD basis-weight CV went from 0.5% → 2.8% (**+460%**) |
| 2️⃣ **Statistical validation** | pressure~cdcv Pearson r=0.87, r=0.57 after detrending; leave-one-out passed; r=0.92~0.93 within each of the three paper grades |
| 3️⃣ **Physical mechanism** | fan pump speed rose only +4.1%, while the pump affinity laws predict +8.4% — actual +93% → **11× excess → increased flow resistance** |
| 4️⃣ **Eliminating competitors** | ❌ temperature hypothesis (98.6% decayed) · ❌ vacuum system (r<0.03) · ❌ speed-driven (11× excess) |
| 5️⃣ **Root-cause conclusion** | progressive scaling/blockage inside the headbox — `DETERMINED`, confidence **76/100** |
| 6️⃣ **Action plan** | P0 acid cleaning during shutdown · P1 verify the sensor · P2 install CD pressure-profile sensors |

> Every conclusion carries an **evidence level (L1–L7)**, and the reasoning chain is traceable back to individual data rows.

### 18 Specialized Skills

<details>
<summary><b>Expand the full skill list</b></summary>

| Skill | Owning Agent | Core output | Gate |
|-------|------------|----------|:----:|
| **industrial-analysis-auto** | main-agent | fully automated orchestrator | all CPs |
| **industrial-data-preprocessor** | — | adaptive multi-format preprocessing | — |
| **industrial-ontology-builder** | context-builder | `ontology.json`, RAG deep understanding | CP-2, CP-3 |
| **industrial-data-processor** | data-processor | `data_analysis_conclusion.json`, 9+ PNG | CP-4 |
| **industrial-diagnostician** | diagnostician | 4× diagnostic JSON (diagnosis/evidence/confidence/reasoning chain) | CP-5 |
| **industrial-judge** | judge | `judge_feedback.json` (10-criterion score) | CP-6 |
| **industrial-physical-auditor** | report-reviewer | `optimizer.md` (dual-mode audit) | CP-6, CP-8 |
| **industrial-reporter** | reporter | `report.md`, `run_summary.json` | CP-7 |
| **industrial-html-visualizer** | html-visualizer | `diagnostic-report.html` (ECharts+Three.js) | CP-9 |
| **industrial-html-reviewer** | html-reviewer | `html_review.json` | — |
| **industrial-physics-bridge** | physics-bridge | physics-data bridge | — |
| **industrial-deep-analysis** | deep-analyst | E1–E4 deep coverage matrix | — |
| **industrial-analysis-enhance-auto** | enhance-orchestrator | enhancement pipeline orchestration | — |
| **industrial-enhanced-html-visualizer** | enhanced-visualizer | enhanced HTML | — |
| **industrial-enhanced-html-reviewer** | enhanced-html-reviewer | enhanced HTML review | — |
| **rag-knowledge-builder** | — | domain knowledge graph | — |
| **diagnostic-html-visualizer** | — | HTML design system | — |
| **darwin-skill** | — | skill evolution assessment | — |

</details>

### 9 Checkpoint Gates

| CP | Position | Validation | Failure handling |
|:--:|:----:|----------|:--------:|
| **1** | 1→2 | `input_manifest` + `user_context` exist | back to Step 0 |
| **2** | 2→2.5 | `ontology.json` ≥1KB + schema validation passed | rerun ontology |
| **3** | 2.5→3 | `clarification_status: AUTO_RESOLVED` | guide to resolution |
| **4** | 3→4 | `data_analysis_conclusion.json` + plots > 0 | rerun processor |
| **5** | 4→5 | all 4 diagnostic JSONs pass schema | rerun diagnostician (≤3) |
| **6** | 5→6 | Judge ≥90 + pre-audit has no FATAL | repair loop (best-of-3) |
| **7** | 6→7 | `report.md` + `run_summary.json` | rerun reporter |
| **8** | 7→8 | `optimizer.md` contains `ENDORSED` | audit repair loop |
| **9** | 8→8.5 | HTML ≥5KB + review verdict=pass | rerun visualizer |

### Evidence Grading System

| Level | Source | Confidence weight |
|:----:|------|:----------:|
| **L1** | direct measurements | 🟢 highest |
| **L2** | user documents (SOP / manuals) | 🟢 high |
| **L3** | statistical analysis (including validation reports) | 🟡 medium-high |
| **L4** | chart-based visual evidence (VLM) | 🟡 medium |
| **L5** | domain knowledge / process logic | 🟡 medium |
| **L6** | external web references | 🔴 low |
| **L7** | unsupported assumptions | ⚫ lowest |

### Anti-Spurious-Correlation Statistical Pipeline

| Version | Detection capability | Method |
|:----:|----------|------|
| **v6.4** | lag-compensated CCF | cross-correlation finds the optimal lag and avoids spurious synchrony |
| **v6.5** | steady-state filtering | three fused algorithms detect steady-state / transition / startup-shutdown segments |
| **v6.6** | batch integrity | `batch_id` uniqueness validation prevents cross-batch confusion |
| **v6.7** | leave-one-out leverage check | any \|r\|≥0.3 must pass leave-one-out |

---

## 📦 Installation

### Requirements

| Dependency | Version | Verification command |
|------|:----:|----------|
| [Node.js](https://nodejs.org/) | ≥ 18 (22+ recommended) | `node --version` |
| [npm](https://www.npmjs.com/) | ≥ 9 | `npm --version` |
| [Python](https://www.python.org/) | ≥ 3.10 | `python --version` |
| [uv](https://docs.astral.sh/uv/) (optional) | ≥ 0.4 | `uv --version` |

### Windows Installation

```powershell
# clone and install
git clone https://github.com/kingdol666/industrial-deep-diagnostic.git
cd industrial-deep-diagnostic
npm install
npm link                    # register the global ind-diag command

# environment check + initialization
ind-diag init

# start
ind-diag start --all --detach
```

You can also double-click the batch scripts (legacy; they cover only the backend + frontend and **exclude the RAG engine** — use the CLI command above for a complete start):
- `commands\start-backend.bat` — start the backend
- `commands\start-frontend.bat` — start the frontend
- `commands\start-all.bat` — start both at once

### Linux / macOS Installation

```bash
# clone and install
git clone https://github.com/kingdol666/industrial-deep-diagnostic.git
cd industrial-deep-diagnostic
npm install
npm link                    # register the global ind-diag command (optional; without privileges use node commands/cli.mjs)

# environment check
ind-diag init

# start
ind-diag start --all --detach

# or use the shell script
bash commands/start-all.sh
```

### Python Dependencies (RAG engine + statistical analysis)

**No manual installation needed** — `ind-diag start` automatically: checks the system Python → creates `rag-retrieval-engine/.venv` if it does not exist → installs every dependency with `uv sync` (falling back to system pip when uv is absent).

You only need one of the following to exist (verify with `python --version`):
- Python ≥ 3.10 (required to run the RAG engine)
- **uv** (recommended; RAG dependencies are installed in isolation automatically, falling back to pip when absent)

When a manual install really is needed (optional, e.g. for a faster mirror):

```bash
# option 1: uv (recommended — isolated install + mirror acceleration)
export UV_INDEX_URL=https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple
uv sync --directory rag-retrieval-engine

# option 2: pip + mirror
pip install -r rag-retrieval-engine/requirements.txt \
  -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple
```

---

## ⌨️ CLI Reference

Use the global `ind-diag` command (once linked) or `node commands/cli.mjs`.

### Service Management

| Command | Purpose | Example |
|------|------|------|
| `start --all` | start all services (background daemon) | `ind-diag start --all --detach` |
| `start --backend` | start only the backend (3210) | `ind-diag start --backend --detach` |
| `start --frontend` | start only the frontend (5180) | `ind-diag start --frontend --detach` |
| `start --rag` | start the RAG engine (8764) | `ind-diag start --rag --detach` |
| `stop --all` | stop all services | `ind-diag stop --all` |
| `restart --all` | restart all services | `ind-diag restart --all --detach` |
| `status` | show service status | `ind-diag status` |
| `init` | environment check (Node/npm/Python/ports) | `ind-diag init` |
| `build` | frontend production build | `ind-diag build` |
| `webfrp` | expose publicly through Cloudflare Tunnel | `ind-diag webfrp` |

> **`--detach` is the recommended form** (background daemon): the command returns immediately and service logs go to `.runtime/*.log`. Without `--detach` the CLI keeps streaming in the foreground and eventually reports `FATAL: Service manager timeout` — the services are unaffected, but the command never finishes cleanly.

### npm Shortcuts

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

### Diagnostic Pipeline Scripts (advanced)

<details>
<summary><b>🔧 Drive individual pipeline stages by hand</b></summary>

```bash
# 1. create the run directory
node .claude/skills/industrial-analysis-auto/scripts/setup.mjs \
  --name <scenario-name> --base-dir ./workspace/diagnostic-runs

# 2. data inspection
node .claude/skills/industrial-analysis-auto/scripts/inspect.mjs \
  <data-file> --rows 10

# 3. pipeline event log (called automatically during a diagnosis)
node .claude/shared/scripts/append-pipeline-event.mjs \
  <run-directory> --event agent_start --agent <agent-name>

# 4. pipeline log validation
node .claude/skills/industrial-analysis-auto/scripts/pipeline-log-check.mjs \
  <run-directory>

# 5. JSON Schema validation
node .claude/shared/scripts/validate.mjs \
  .claude/shared/schemas/diagnosis_schema.json \
  workspace/diagnostic-runs/<run>/04_diagnostics/diagnosis.json

# 6. Python venv initialization
node .claude/shared/scripts/uv_env_setup.mjs \
  --skill-path .claude/skills/industrial-data-processor
```

</details>

---

## 📊 Usage

### Option 1: Web UI (recommended) 🌐

1. Start the services: `ind-diag start --all --detach`
2. Open **http://localhost:5180**
3. Upload a data file (CSV / XLSX / Parquet)
4. Fill in the scenario name and the analysis question
5. Watch the 9-step pipeline progress in real time
6. Download `report.md` + open `diagnostic-report.html`

### Option 2: Fully Automated Command Line 🖥

```bash
# create the run directory and start the orchestration
node .claude/skills/industrial-analysis-auto/scripts/setup.mjs \
  --name cnc-test --base-dir ./workspace/diagnostic-runs

# the main agent dispatches subagents through Steps 0-9 automatically
# output lands in workspace/diagnostic-runs/<timestamp>_cnc-test/
```

### Option 3: Interactive Mode 💬

Three interaction modes are supported (`config/default.yaml` → `diagnosis.interaction_mode`):

| Mode | Behaviour | Best for |
|------|------|----------|
| `auto` | fully automatic, zero intervention | batch analysis, production |
| `interactive` | waits for user confirmation at key decision points | fine-grained control, research analysis |
| `minimal` | only essential questions | quick validation |

### Browsing Past Diagnoses

```bash
# list all runs
ls workspace/diagnostic-runs/

# view a report
cat workspace/diagnostic-runs/<run>/report.md

# open the HTML on Windows
start workspace/diagnostic-runs/<run>/diagnostic-report.html

# open the HTML on macOS
open workspace/diagnostic-runs/<run>/diagnostic-report.html
```

---

## 🔧 Configuration

Configuration precedence: `environment variables` > `config/local.yaml` > `config/default.yaml`

<details>
<summary><b>📄 Key settings in config/default.yaml</b></summary>

```yaml
server:
  port: 3210                       # backend port
  body_limit: "10mb"

frontend:
  port: 5180                       # frontend port
  backend_url: "http://localhost:3210"
  ws_url: "ws://localhost:3210"

database:
  path: "data/diagnostic.db"
  journal_mode: "WAL"              # WAL mode improves concurrency

claude:
  model: "claude-opus-4-7"         # core model
  max_turns: 200                   # max turns per diagnosis
  timeout_minutes: 120

diagnosis:
  default_language: "zh"           # zh | en
  interaction_mode: "auto"         # auto | interactive | minimal

data:
  upload:
    max_file_size_mb: 500          # per-file limit
    max_files: 50

pipeline:
  max_judge_repair: 3              # Judge repair limit
  max_reviewer_cycles: 2           # audit cycle limit
  global_rediagnosis_cap: 5        # global rediagnosis limit
```

</details>

### Environment Variable Overrides

| Variable | Maps to config | Notes |
|------|---------|------|
| `SERVER_PORT` | `server.port` | backend port |
| `CLAUDE_MODEL` | `claude.model` | Claude model ID |
| `DATA_DIR` | `data.dir` | data directory |
| `DIAGNOSIS_DEFAULT_LANGUAGE` | `diagnosis.default_language` | output language |
| `DIAGNOSIS_INTERACTION_MODE` | `diagnosis.interaction_mode` | interaction mode |
| `ANTHROPIC_API_KEY` | — | Claude API key |
| `ANTHROPIC_BASE_URL` | — | API base URL (third-party proxy) |

---

## 🔌 API Reference

All APIs are served by the Express backend (port 3210); the frontend calls them through the Vite `/api` proxy.

### Health Check

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

### Core Endpoints

| Category | Endpoint | Method | Purpose |
|------|------|:----:|------|
| **Files** | `/api/files/data` | GET | list data files |
| | `/api/files/data/folder` | POST | create a folder |
| | `/api/files/data/file/:path` | GET | read file contents |
| | `/api/files/workspace` | GET | list diagnostic runs |
| | `/api/files/workspace/report/:name` | GET | fetch a diagnostic report |
| **Diagnosis** | `/api/diagnosis/start` | POST | start a new diagnosis (`harness` / `ontologyMode` / `enhancement` optional) |
| | `/api/diagnosis/execute/:runId` | POST | execute the diagnosis |
| | `/api/diagnosis/status/:runId` | GET | query run status |
| | `/api/diagnosis/snapshot/:runId` | GET | fetch a snapshot |
| | `/api/diagnosis/stop/:runId` | POST | stop a run |
| | `/api/diagnosis/list` | GET | list all runs |
| | `/api/diagnosis/stream/:runId` | GET | SSE event stream |
| | `/api/diagnosis/enhance/:runId` | POST | **one-click deep enhancement (E0-E8)** |
| **Ontology assets** | `/api/ontology/store` | GET | ontology asset library registry (scenario / version / fingerprint) |
| **Chat** | `/api/diagnosis/chat/:runId` | POST | diagnostic conversation |
| | `/api/diagnosis/hitl/:hitlId` | POST | human approval |
| | `/api/chat/start` | POST | start a chat session (`harness` optional) |
| | `/api/chat/stream/:chatId` | GET | SSE chat stream |
| **Harness** | `/api/harness` | GET | engine registry (claude / omp) |
| | `/api/harness/omp/health` | GET | OMP engine health probe (binary executability) |

### WebSocket Real-Time Push

```
ws://localhost:3210/ws
```

Streams diagnostic progress, logs and events in real time (30s heartbeat, 60s timeout).

---

## 🐳 Docker Deployment

```bash
# build and start in the background
docker compose up -d

# view logs
docker compose logs -f

# stop
docker compose down
```

### Data Persistence (Docker Volumes)

```yaml
volumes:
  - ./data:/app/data                       # data files
  - ./workspace:/app/workspace             # diagnostic output
  - ./config/local.yaml:/app/config/local.yaml:ro  # local config
```

### Multi-Architecture Support

| Architecture | Status | Notes |
|------|:----:|------|
| `linux/amd64` | ✅ | standard x86_64 servers |
| `linux/arm64` | ✅ | Apple Silicon / ARM servers |
| `windows/amd64` | ✅ | WSL2 environments |

> The Dockerfile is based on `node:22-alpine`, uses a multi-stage build and keeps the image size small.

---

## 🗂 Project Structure

```
industrial-deep-diagnostic/
├── commands/                       # CLI and service management
│   ├── cli.mjs                    # unified CLI entry point (ind-diag)
│   ├── service-manager.mjs        # service lifecycle management
│   ├── cross-platform.mjs         # cross-platform utility library
│   └── start-*.bat/.sh            # platform-specific start scripts
│
├── app/
│   ├── backend/                   # Express.js backend (port 3210)
│   │   └── src/
│   │       ├── index.mjs          # service entry point
│   │       ├── routes/            # REST API routes
│   │       ├── services/          # business logic
│   │       ├── engine/            # diagnostic engine
│   │       ├── transport/         # WebSocket
│   │       └── db/                # SQLite (WAL)
│   │
│   └── frontend/                  # Vue 3 + Vite frontend (port 5180)
│       └── src/
│           ├── App.vue            # main view
│           ├── api/               # API client
│           ├── components/        # UI components
│           └── stores/            # state management
│
├── .claude/skills/                # 18 skill implementations (single source)
│   ├── industrial-analysis-auto/  # fully automated orchestrator
│   ├── industrial-data-processor/ # statistical analysis
│   ├── industrial-diagnostician/  # competing-hypothesis diagnosis
│   └── ...                        # scripts/schemas/resources
│
├── .omp/agents/                   # 14 OMP agent definitions
│   ├── context-builder.md
│   ├── diagnostician.md
│   └── ...
│
├── rag-retrieval-engine/          # RAG retrieval microservice (port 8764)
│   ├── server.py                  # FastAPI entry point
│   └── engine/                    # retrieval/scoring/injection engines
│
├── config/
│   ├── default.yaml               # default configuration
│   ├── loader.mjs                 # configuration loader
│   └── local.yaml                 # user overrides (gitignored)
│
├── data/                          # sample data & simulated data
├── workspace/diagnostic-runs/     # diagnostic run output
│   └── <timestamp>_<name>/
│       ├── 00_input/              # input & configuration
│       ├── 01_ontology/           # domain ontology
│       ├── 02_processed/          # statistics & cleaning
│       ├── 03_figures/            # charts & VLM
│       ├── 04_diagnostics/        # diagnostic conclusions
│       ├── 05_review/             # review & audit
│       ├── report.md              # Chinese diagnostic report
│       ├── diagnostic-report.html # HTML visualization
│       └── .pipeline_events.jsonl # event log
│
├── docs/                          # documentation & architecture diagrams
├── Dockerfile                     # multi-stage build
├── docker-compose.yml             # Docker Compose
└── package.json
```

---

## 🐛 Troubleshooting

<details>
<summary><b>❌ "ind-diag: command not found"</b></summary>

```bash
# use the full path
node commands/cli.mjs status

# or re-register the global command
npm link
```

</details>

<details>
<summary><b>❌ Port already in use (EADDRINUSE :3210 / :5180 / :8764)</b></summary>

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
<summary><b>❌ The command hangs after startup / reports "FATAL: Service manager timeout"</b></summary>

Cause: foreground mode was used (`--detach` omitted). The services may already be running (confirm with `ind-diag status`), but the CLI times out waiting in the foreground.

```bash
# switch to background daemon mode
ind-diag stop --all
ind-diag start --all --detach
```
</details>

<details>
<summary><b>❌ RAG engine fails to start (Python / venv)</b></summary>

RAG engine dependencies are managed automatically by `rag-retrieval-engine/start.mjs`: detect the system Python → create `.venv` → `uv sync` (or pip) → start.

Diagnose in this order:
```bash
# 1. confirm Python ≥ 3.10
python --version        # Linux/macOS: python3 --version

# 2. confirm uv or pip exists (either one is enough)
uv --version || pip --version

# 3. slow network → install manually from a mirror, then restart
export UV_INDEX_URL=https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple
uv sync --directory rag-retrieval-engine
ind-diag restart --all --detach
```

If it still fails, check the log: `.runtime/rag.log`
</details>

<details>
<summary><b>❌ Services are up but a diagnosis cannot be started (Claude-related errors)</b></summary>

The diagnostic pipeline is driven by the Claude Code CLI and requires:

```bash
# 1. confirm Claude Code is installed
claude --version

# 2. confirm you are logged in or an API key is configured (optionally in .env)
cp .env.example .env   # then edit ANTHROPIC_API_KEY

# 3. see config/default.yaml → the claude section (model and binary name are configurable)
```
</details>

<details>
<summary><b>❌ The frontend page is blank</b></summary>

```bash
# 1. confirm the backend is running
curl http://localhost:3210/api/health

# 2. rebuild the frontend
cd app/frontend && npx vite build

# 3. clear the Vite cache
rm -rf app/frontend/node_modules/.vite
```

</details>

<details>
<summary><b>❌ No diagnostic report is produced / the pipeline is stuck</b></summary>

```bash
# inspect the pipeline event log
cat workspace/diagnostic-runs/<run>/.pipeline_events.jsonl

# validate pipeline integrity
node .claude/skills/industrial-analysis-auto/scripts/pipeline-log-check.mjs \
  workspace/diagnostic-runs/<run>

# inspect the artifact of each step
ls -la workspace/diagnostic-runs/<run>/
```

</details>

<details>
<summary><b>❌ RAG engine dependency download is slow</b></summary>

```bash
# use the Tsinghua mirror
export UV_INDEX_URL=https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple
uv sync --directory rag-retrieval-engine

# or the pip mirror
pip install -r rag-retrieval-engine/requirements.txt \
  -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple
```

</details>

---

## 🤝 Contributing

### Development Workflow

1. Fork this repository
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Commit your changes (following Conventional Commits)
4. Push and open a Pull Request

### Commit Convention

```
feat:     new feature       fix:      bug fix
docs:     documentation     refactor: refactor
test:     tests             chore:    build/tooling
style:    formatting        perf:     performance
```

### Extending the Diagnostic Pipeline (adding a new skill)

1. Define the skill entry point in `.claude/skills/<name>/SKILL.md` (scripts + Schema + protocol)
2. Define the agent in `.omp/agents/<name>.md` (OMP contract: name + description + tools + model)
3. Register the step in `industrial-analysis-auto/SKILL.md`
4. Add the matching JSON Schema under `.claude/shared/schemas/`

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
npm link                    # register the global ind-diag command (optional; without privileges use node commands/cli.mjs)
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
