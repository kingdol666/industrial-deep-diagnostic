# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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

## Commands

### CLI (`ind-diag`)
```bash
ind-diag start --all --detach     # start everything (backend 3210 + frontend 5180 + RAG 8764)
ind-diag start --backend --detach # http://localhost:3210
ind-diag start --frontend --detach # http://localhost:5180
ind-diag start --rag --detach     # http://localhost:8764
ind-diag stop --all               # stop everything
ind-diag restart --all --detach   # restart everything
ind-diag build                    # production build
ind-diag init                     # environment check
ind-diag status                   # status
ind-diag webfrp                   # Cloudflare Tunnel
```

> `--detach` = background daemon mode (recommended): the command returns immediately and logs go to `.runtime/*.log`. If omitted, the CLI waits and eventually reports `FATAL: Service manager timeout` (the service does still start).

### npm scripts
```bash
npm start             # = ind-diag start --all --detach
npm run start:backend # = ind-diag start --backend --detach
npm run start:frontend # = ind-diag start --frontend --detach
npm run start:rag     # = ind-diag start --rag --detach
npm stop              # = ind-diag stop --all
```

### Python Environment
```bash
# All Python scripts must use the shared venv (managed by uv_env_setup.mjs)
node .claude/shared/scripts/uv_env_setup.mjs
# Resolves to: .claude/shared/scripts/.venv/Scripts/python.exe (Windows)
#              .claude/shared/scripts/.venv/bin/python (POSIX)
```

### RAG Retrieval Engine
```bash
python server.py      # FastAPI → http://localhost:8764
```

## Architecture

### Diagnostic Pipeline (Step 0–9)

| Steps | Agent | Skill | Model | Output |
|-------|-------|-------|:-----:|------|
| Step 0: Setup | main-agent | `industrial-analysis-auto` | — | run_manifest, pipeline_events |
| Step 1: Inspect | main-agent | — | — | input_manifest, user_context |
| Step 2: Context | **context-builder** | `industrial-ontology-builder` | default | ontology.json, rag_deep_understanding |
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

**Repair loop**: Judge score < 90 → rerun the Diagnostician (at most 3 times); Reviewer not passed → D→J→R→R (at most 2 rounds); **global cap: at most 5 rediagnoses in total**. Anti-oscillation: a third attempt at the same problem → COMPETING_SET, confidence ≤50.

**Step 5a/5b run in parallel**: the Judge and the pre-audit are the only two parallel steps in the pipeline. Step 3.5 VLM is delegated internally by data-processor.

### Checkpoint Gates (CP-1 ~ CP-9)

| CP | Validates | On failure → |
|:--|------|-------|
| CP-1 | input_manifest + user_context | back to Step 0 |
| CP-2 | ontology.json ≥1KB + schema-valid | rerun ontology |
| CP-3 | clarification AUTO_RESOLVED | resolve |
| CP-4 | data_analysis_conclusion + plots>0 | rerun processor |
| CP-5 | 4 diagnostic outputs schema-valid | repair |
| CP-6 | judge_repair_summary | best-of-3 |
| CP-7 | report.md + run_summary.json | rerun reporter |
| CP-8 | optimizer.md ENDORSED | repair loop |
| CP-9 | diagnostic-report.html ≥5KB + review pass | rerun visualizer |

### Four Independent Numbering Schemes
| Scheme | Scope | Example |
|------|------|------|
| Pipeline Step 0-9 | Orchestration layer | "Step 4: Diagnostician" |
| Agent Phase 0-7 | Internal agent flow | "Phase 1: Data Probing" |
| Reasoning Segment R1-R8 | reasoning_chain.json | "R4: Hypothesis Generation" |
| Method Stage 1-6 | diagnosis_method.md | "Stage 3: Temporal Analysis" |

### Diagnostic Methodology: Core
- **Competing-hypotheses protocol**: hypothesis → data discriminability → elimination → conclusion. Outputs: DETERMINED / COMPETING_SET / NEEDS_DATA
- **Dual-driver analysis**: pure process fluctuation + combined process-and-inspection dual driver
- **Evidence levels L1-L7**: a conclusion is bounded by its lowest evidence level
- **Four conditions**: temporal precedence + statistical significance + physical mechanism + no contradiction
- **Confidence caps**: COMPETING_SET INDISTINGUISHABLE ≤65, oscillation ≤50
- **Anti-spurious-correlation v6.4-v6.7**: lag CCF · steady-state filtering · batch integrity · leave-one-out
- **Automatic HTML build**: after CP-8 ENDORSED, Steps 8→8.5→9 run automatically

### Skill Directory Conventions
| Directory | Purpose |
|------|------|
| `.claude/skills/<name>/SKILL.md` | the single skill entry point (OMP claude provider + Claude Code discovery) |
| `.claude/skills/<name>/{scripts,schemas,references,resources,templates}/` | complete resources |
| `.omp/agents/<name>.md` | OMP task-agent definition (model + tools + thinkingLevel + protocol ref) — the single source for task creation |
| `.claude/agents/<name>.md` | Claude Code format agent definition (not loaded by OMP, used only by native Claude Code) |

### Diagnostic Output Directory
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
- **Backend** (`app/backend/`): Express.js + SQLite (WAL) + WebSocket
- **Frontend** (`app/frontend/`): Vue 3 + Vite + SSE live stream

### RAG Retrieval Engine
- FastAPI + ChromaDB vector retrieval + web search
- Endpoints: `/retrieve`, `/score`, `/inject`, `/pipeline/full`
- Automatic degradation when unavailable: `parameter_to_physics.json` + web search

### Key Scripts
- `setup.mjs` — creates the run directory + pipeline_events
- `inspect.mjs` — data file inspection
- `stats.mjs` / `stats_validate.mjs` — statistical analysis + robustness validation
- `validate.mjs` — JSON Schema runtime validation
- `artifact-check.mjs` — pipeline artifact completeness validation
- `pipeline-log-check.mjs` — pipeline event log audit
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
| `DATA_DIR` | `data.dir` |
| `DIAGNOSIS_DEFAULT_LANGUAGE` | `diagnosis.default_language` |

## Language Default

The default output language is **Chinese**. Reports, diagnostic conclusions and audit documents are written in Chinese. JSON enum fields remain English.

## Key Gotchas

- **Dual harness**: `.omp/` is the entry point, `.claude/` is the resources. `SKILL_PATH` is redirected via `<this-skill-directory>/../../../.claude/skills/<name>`
- **Python path**: you must use the shared venv resolved by `uv_env_setup.mjs` (Windows: `.claude/shared/scripts/.venv/Scripts/python.exe`, POSIX: `.claude/shared/scripts/.venv/bin/python`)
- **Repair counter**: `diag_iters` is persisted by `repair_spawn` in `.pipeline_events.jsonl`
- **Execution proof**: a run counts as fully executed only once `.pipeline_events.jsonl` passes `pipeline-log-check.mjs`
- **Handoff file**: `data_analysis_conclusion.json` is the mandatory data-processor→diagnostician handoff
- **Image fallback**: `image_captions.json` is the fallback when PNG rendering fails
- **Automatic HTML build**: after CP-8 ENDORSED, Steps 8→8.5→9 run automatically; `00_input/html_opt_out` can skip it
- **VLM Agent**: the only agent that uses `model: vision`; it needs a vision-capable model to read charts
- **Agent self-reference fixed**: every agent initializes by reading `references/agent-protocol.md`, not `agents/<self>.md`
- **The four numbering schemes must not be mixed**
