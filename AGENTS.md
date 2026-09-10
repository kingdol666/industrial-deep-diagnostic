# AGENTS.md

This file provides guidance to AI coding agents working with code in this repository.

## Project Overview

Industrial Deep Diagnostic — an end-to-end industrial deep-diagnosis system that runs 9-stage root-cause analysis plus an E0-E8 enhancement pipeline over sensor and process data. Core architecture:

1. **Skills** (`.claude/skills/`) — 18 standardized skills (discovered by OMP through the `claude` provider) × 14 dedicated agents, with JSON Schema validation + a script toolchain
2. **Web application** — Express.js backend (port 3210) + Vue 3 / Vite frontend (port 5180)
3. **RAG Retrieval Engine** (`rag-retrieval-engine/`) — ChromaDB + FastAPI microservice (port 8764)

### Harness Discovery Architecture

```
.claude/skills/<name>/         ← the single skill source (OMP discovery via the `claude` provider at priority 80 + native Claude Code discovery)
    │  scripts/ schemas/ references/ resources/ templates/ all live here
    ↓ skill://<name> resolves here; agent dispatch passes SKILL_PATH pointing here
.omp/agents/<name>.md          ← the single OMP task-agent discovery source (OMP skips .claude/agents)
    │  OMP frontmatter: name + description + tools + spawns + model + thinkingLevel
    ↓ reads the protocol
.claude/skills/<name>/references/agent-protocol.md  ← complete Phase 0-N execution checklist
```

> **Architectural note**: skill resources live together under `.claude/skills/` (shared by OMP and Claude Code); agent definitions live under `.omp/agents/` (they satisfy the OMP task-agent contract and are the single source for task creation).

### Multi-Harness Execution Engines (14 engines)

A diagnostic job can be driven by any one of 14 execution engines (selected in the frontend sidebar → `POST /api/diagnosis/start { harness }`):
`claude` / `omp` / `mock` / `codex` / `dsh` / `opencode` / `gemini` / `copilot` / `cursor` / `crush` / `goose` / `qwen` / `pi` / `hermes`.

- **Single source of truth**: `HARNESS_DEFS` in `app/backend/src/harness/engines.mjs` (capability surface / probing / metadata) + the `ENGINES` dispatch table in `app/backend/src/services/diagnosis.service.mjs` (unified contract: startDiagnosis/startSessionChat/parseStreamEvent/registerChild/closeQuery). Adding an engine touches only these two files plus one engine client.
- **Strict pre-flight validation**: unknown engine → 400 `HARNESS_UNKNOWN`; registered but unavailable → 409 `HARNESS_UNAVAILABLE`. Probing and the real spawn share one code path (`engine/cli-common.mjs resolveCliBinary`); command override chain: `harness.engines.<id>.binary` → env `HARNESS_<ID>_COMMAND` → PATH.
- **Standard event stream**: every engine client emits Claude-SDK-compatible events (system init / assistant / user tool_result / result), so the consumption loop is engine-agnostic.
- See `docs/multi-harness.md` (engine integration cards, engineering discipline, test matrix). Backend tests: `cd app/backend && npm test` (45 cases, including a real-subprocess fake CLI / fake ACP / fake codex app-server / mock-engine HTTP e2e).

## Commands

```bash
# Start project (backend + frontend)
ind-diag all
ind-diag backend      # http://localhost:3210
ind-diag frontend     # http://localhost:5180
ind-diag build        # Production build
ind-diag init         # Initialize (check DB / config)
ind-diag status       # Status
```

### Python venv
```bash
# All Python scripts MUST use the shared venv via uv_env_setup.mjs
node .claude/shared/scripts/uv_env_setup.mjs
# Resolves to: .claude/shared/scripts/.venv/Scripts/python.exe (Windows)
#              .claude/shared/scripts/.venv/bin/python (POSIX)
```

### RAG Engine
```bash
cd rag-retrieval-engine
python server.py      # → http://localhost:8764
```

## Architecture

### Pipeline (Step 0–9)

| Steps | Agent | Skill | Model | Output |
|-------|-------|-------|:-----:|------|
| Step 0: Setup | main-agent | `industrial-analysis-auto` | — | run_manifest, pipeline_events |
| Step 1: Inspect | main-agent | — | — | input_manifest, user_context |
| Step 2: Context | **context-builder** | `industrial-ontology-builder` | default | ontology.json |
| Step 3: Process | **data-processor** | `industrial-data-processor` | default | data_analysis_conclusion, plots |
| Step 3.5: VLM | **vlm-visual-analyzer** | *(data-processor Phase 5.5)* | **vision** | visual_analysis.json |
| Step 4: Diagnose | **diagnostician** | `industrial-diagnostician` | default | diagnosis, evidence, confidence, reasoning_chain |
| Step 5a: Judge | **judge** | `industrial-judge` | default | judge_feedback.json |
| Step 5b: Pre-Audit | **report-reviewer** | `industrial-physical-auditor` | default | optimizer_preflight.md |
| Step 6: Report | **reporter** | `industrial-reporter` | default | report.md, run_summary.json |
| Step 7: Final Audit | **report-reviewer** | `industrial-physical-auditor` | default | optimizer.md (ENDORSED) |
| Step 8: HTML Viz | **html-visualizer** | `industrial-html-visualizer` | default | diagnostic-report.html |
| Step 8.5: HTML Review | **html-reviewer** | `industrial-html-reviewer` | default | html_review.json |
| Step 9: Finalize | main-agent | — | — | evidence_closure_report |

**Repair loop**: Judge score < 90 → rerun the Diagnostician (at most 3 times); Reviewer not passed → full rerun of D→J→R→R (at most 2 rounds); **global cap: at most 5 rediagnoses in total** (counted persistently from `repair_spawn` events in `.pipeline_events.jsonl`). Anti-oscillation: a third rediagnosis of the same problem → stop, mark `COMPETING_SET`, confidence capped at ≤50.

**Checkpoints 🛑 CP-1 ~ CP-9**: every checkpoint has an exact bash verification command; if it is not satisfied, the pipeline blocks or rolls back. See the orchestrator SKILL.md.

**Step 5a/5b run in parallel**: the Judge and the report-reviewer pre-audit are the **only two parallel** steps in the pipeline.

### Four Independent Numbering Schemes
| Scheme | Scope | Example |
|------|------|------|
| Pipeline Step 0-9 | Orchestration layer | "Step 4: Diagnostician" |
| Agent Phase 0-7 | Internal agent flow | "Phase 1: Data Probing" |
| Reasoning Segment R1-R8 | reasoning_chain.json | "R4: Hypothesis Generation" |
| Method Stage 1-6 | diagnosis_method.md | "Stage 3: Temporal Analysis" |

### Diagnostic Methodology: Core
- **Competing-hypotheses protocol**: hypothesis → data-based discriminability assessment → elimination → conclusion. Three output types: `DETERMINED` / `COMPETING_SET` / `NEEDS_DATA`
- **Dual-driver analysis**: pure process-fluctuation diagnosis + combined process-and-inspection dual-driver diagnosis
- **Evidence levels 1-7**: a conclusion is bounded by its lowest evidence level
- **Four anti-speculation conditions**: temporal precedence + statistical significance + physical mechanism + no contradiction
- **Confidence caps**: COMPETING_SET INDISTINGUISHABLE ≤65, oscillation ≤50
- **Mandatory anti-spurious-correlation (v6.4–v6.7)**: lag-compensated CCF · production-state detection + steady-state filtering · batch identifier integrity · outlier leverage leave-one-out
- **Automatic HTML build (non-interactive)**: after CP-8 `ENDORSED`, Steps 8→8.5→9 run back to back automatically by default, with no user prompt

### Skill System (18 skills)

| Skill | Trigger conditions | Model |
|-------|---------|:----:|
| `industrial-analysis-auto` | industrial diagnosis, root cause analysis, fault diagnosis... | default |
| `industrial-data-preprocessor` | data preprocessing, preprocessing, multi-format data... | default |
| `industrial-ontology-builder` | ontology building, ontology, RAG retrieval... | default |
| `industrial-data-processor` | statistical analysis, data cleaning, data visualization... | default |
| `industrial-diagnostician` | diagnosis, root cause, competing hypotheses... | default |
| `industrial-judge` | quality gate, quality review... | default |
| `industrial-physical-auditor` | physical audit, physical auditing... | default |
| `industrial-reporter` | write report, diagnostic report... | default |
| `industrial-html-visualizer` | HTML visualization, generate HTML... | default |
| `industrial-html-reviewer` | HTML review, review HTML... | default |
| `industrial-deep-analysis` | deep analysis, deep-layer analysis, coverage builder... | default |
| `industrial-physics-bridge` | physics bridge, physics bridging, physics verification... | default |
| `industrial-analysis-enhance-auto` | enhance auto, automatic enhancement, enhancement orchestration... | default |
| `industrial-enhanced-html-visualizer` | enhanced html, enhanced visualization... | default |
| `industrial-enhanced-html-reviewer` | enhanced html review, enhanced review... | default |
| `rag-knowledge-builder` | knowledge base construction, ontology construction... | default |
| `diagnostic-html-visualizer` | diagnosis result visualization, dashboard... | — |
| `darwin-skill` | skill fitness, skill evaluation... | — |

### Agent Roles (14 agents)

| Agent | Persona | Core output |
|-------|------|---------|
| context-builder | Professor Wang · Failure Analysis | Ontology + physical principles |
| data-processor | Engineer Zhang · Process Analysis | Statistics + charts + handoff |
| vlm-visual-analyzer | Veteran Sun · Visual Inspection | Chart-based visual evidence |
| diagnostician | Chief Engineer Liu · Root-Cause Diagnosis | Competing hypotheses + reasoning chain |
| judge | Director Chen · Quality Audit | 10-criterion scoring gate |
| report-reviewer | Auditor Sun · Physical Audit | Physical-truth audit |
| reporter | Engineer Zhou · Technical Reporting | Pyramid report |
| html-visualizer | Engineer Lin · HMI Visualization | ECharts + Three.js |
| html-reviewer | Reviewer Zhao · Page Review | HTML usability review |
| deep-analyst | Deep Analysis Engine | E1-E4 coverage + conditions + tradeoffs |
| physics-bridge | Physics Mechanism Bridge | Five physical verifications + mechanism chain |
| enhance-orchestrator | Enhancement Pipeline Orchestration | Fully automated E0-E8 enhancement |
| enhanced-visualizer | Enhanced Frontend | Enhanced ECharts HTML |
| enhanced-html-reviewer | Enhanced Review | Enhanced HTML review |

### Diagnostic Output Directory Structure
```
workspace/diagnostic-runs/<timestamp>_<scene>/
├── 00_input/          # input data + user context
├── 01_ontology/       # ontology (including RAG deep understanding)
├── 02_processed/      # cleaning / validation / features / anomaly reports
├── 03_figures/        # visualization charts + VLM analysis
├── 04_diagnostics/    # diagnosis / evidence / confidence / reasoning chain
├── 05_review/         # Judge review + HTML review
├── report.md          # final report
├── diagnostic-report.html
├── optimizer.md
└── .pipeline_events.jsonl
```

### Web Application
- **Backend** (`app/backend/`): Express.js + SQLite (WAL mode) + WebSocket, event-bus architecture
- **Frontend** (`app/frontend/`): Vue 3 + Vite + tabbed layout (Data / Diagnose / Reports / History), SSE live stream + WebSocket

### RAG Retrieval Engine (`rag-retrieval-engine/`)
- FastAPI + ChromaDB vector retrieval + web search
- Endpoints: `/retrieve`, `/score` (5-dimensional scoring), `/inject` (ontology injection), `/pipeline/full`
- Automatic degradation when unavailable: `parameter_to_physics.json` + web search

### Skill Directory Conventions
| Directory | Purpose |
|------|------|
| `.claude/skills/<name>/SKILL.md` | the single skill entry point (OMP claude provider + Claude Code discovery) |
| `.claude/skills/<name>/{scripts,schemas,references,resources,templates}/` | complete resources |
| `.omp/agents/<name>.md` | OMP task-agent definition (model + tools + thinkingLevel + protocol ref) — the single source for task creation |
| `.claude/agents/<name>.md` | Claude Code format agent definition (not loaded by OMP, used only by native Claude Code) |

### Key Scripts
- `setup.mjs` — creates the run directory structure
- `inspect.mjs` — data file inspection (streaming CSV/JSON/TSV parsing)
- `stats.mjs` — advanced statistical analysis engine (Pearson/Spearman/stratification/lagged CCF/multiple testing)
- `stats_validate.mjs` — statistical validation and robustness engine
- `validate.mjs` — JSON Schema runtime validation (zero dependencies)
- `artifact-check.mjs` — pipeline artifact completeness validation
- `pipeline-log-check.mjs` — pipeline event log audit
- `physics_check.py` / `dp_toolkit.py` — physical constraint validation
- `visual_analysis.py` — VLM visual analysis
- `uv_env_setup.mjs` — Python venv manager

### Evidence System
| Level | Source | Confidence |
|------|------|--------|
| L1 | direct measurements | highest |
| L2 | user documents (SOP/manuals) | high |
| L3 | statistical analysis (including validation reports) | medium-high |
| L4 | chart-based visual evidence (VLM) | medium |
| L5 | domain knowledge / process logic | medium |
| L6 | external web references | low |
| L7 | unsupported assumptions | lowest |

## Configuration

Configuration precedence: `config/default.yaml` → `config/local.yaml` + environment variables

| Environment variable | Maps to config |
|----------|----------|
| `SERVER_PORT` | `server.port` |
| `CLAUDE_MODEL` | `claude.model` |
| `CLAUDE_MAX_TURNS` | `claude.max_turns` |
| `DATA_DIR` | `data.dir` |
| `DIAGNOSIS_DEFAULT_LANGUAGE` | `diagnosis.default_language` |

## Language Default

The default output language is **Chinese**. Reports, diagnostic conclusions and audit documents are written in Chinese. JSON enum fields remain English.

## Key Gotchas

- **Dual harness**: `.omp/` is the entry point, `.claude/` is the resources. `SKILL_PATH` is redirected via `<this-skill-directory>/../../../.claude/skills/<name>`
- **Python path**: every Python script must use `scripts/.venv/bin/python`, never the system `python3`
- **Repair counter**: `diag_iters` is maintained persistently by `repair_spawn` events in `.pipeline_events.jsonl`
- **Execution proof**: a run counts as fully executed only once `.pipeline_events.jsonl` passes `pipeline-log-check.mjs`
- **Expert handoff**: `data_analysis_conclusion.json` is the mandatory handoff file from data-processor → diagnostician
- **Image fallback**: `image_captions.json` is the fallback when PNG rendering is unavailable
- **Automatic HTML build**: after CP-8 ENDORSED, `diagnostic-report.html` is produced automatically and non-interactively by default (Step 8→8.5→9); only a pre-existing `00_input/html_opt_out` can skip it
- **VLM Agent**: the only agent that uses `model: vision`; it needs a vision-capable model to read chart PNGs
- **Agent initialization**: every agent reads `references/agent-protocol.md`, not `agents/<self>.md` (self-reference bug fixed)
- **Four numbering schemes**: Pipeline Step / Agent Phase / Reasoning Segment / Method Stage are each independent and must not be mixed
