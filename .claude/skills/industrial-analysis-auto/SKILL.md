---
name: industrial-analysis-auto
description: "工业深度诊断全自动编排器 — 集成 8 个标准化子 skill 实现端到端诊断管线。从原始传感器/工艺数据到中文诊断报告+HTML可视化页面，零人工干预。Trigger: 工业诊断, 根因分析, 故障诊断, 生产过程异常, 质量缺陷分析, 传感器数据分析, 工艺参数优化, industrial diagnosis, root cause analysis, SPC excursion, manufacturing diagnostics. 3 modes: auto/interactive/minimal."
---

# Industrial Analysis Auto — Full Pipeline Orchestrator

端到端工业深度诊断自动编排器。上传传感器/工艺数据 → 8 步全自动诊断 → `report.md` + `diagnostic-report.html`。

## TL;DR

```
输入: CSV/XLSX/Parquet 工业传感器/工艺数据
输出: 中文诊断报告 (report.md) + HTML 可视化讲解页 (diagnostic-report.html)
核心: 本体构建 → 去趋势/分层/Simpson检测 → 竞争假说 → 物理验证 → Judge审查 → HTML可视化
默认: FULL-AUTO — 8 步连续跑完、零人工干预
```

## Core Principle

诊断 = 排除而非确认。每条结论要求四条件：时间先后 + 统计显著 + 物理机制 + 无矛盾。

| Pillar | Principle |
|--------|-----------|
| Scenario-Adaptive | 从数据特征驱动分析流 — 无硬编码工艺类型 |
| RAG Deep Understanding | RAG 知识语义理解，非机械映射 |
| Data↔Ontology Bidirectional | 本体预测→数据确认；数据揭示→本体解释 |
| Physics-Based | 每条相关性必须追溯到控制方程 |

## Pipeline Flow

```
Step 0-1: Setup + Inspect (main agent)
    ↓
Step 2+2.5: [industrial-ontology-builder] → CP-2, CP-3
    ↓
Step 3+3.3: [industrial-data-processor] → CP-4（含 VLM 视觉分析）
    ↓
Step 4: [industrial-diagnostician] → CP-5
    ↓       ┌── repair max 3 ──┐
    ├───────┤                  │
    ↓       ↓                  │
Step 5a:   Step 5b:            │
[judge]    [physical-auditor]  │
   │     (pre-report,并行)      │
   └───────┬───────────────────┘
           ↓ pass
     Step 6: [industrial-reporter] → CP-7
           ↓
     Step 7: [industrial-physical-auditor](final)
           ↓ ENDORSED
     Step 8: [industrial-html-visualizer]  ← AUTO
           ↓
     Step 8.5: [industrial-html-reviewer] → CP-9
           ↓ PASS
     Step 9: Finalize (main agent)
```

## Sub-Skill Map

| Step | Sub-Skill | Agent | CP Gate |
|:----:|-----------|-------|:-------:|
| 2+2.5 | `industrial-ontology-builder` | context-builder | CP-2, CP-3 |
| 3+3.3 | `industrial-data-processor` | data-processor | CP-4 |
| 4 | `industrial-diagnostician` | diagnostician | CP-5 |
| 5a | `industrial-judge` | judge | CP-6 |
| 5b | `industrial-physical-auditor` (PRE_REPORT_AUDIT=true) | report-reviewer | CP-6 |
| 6 | `industrial-reporter` | reporter | CP-7 |
| 7 | `industrial-physical-auditor` (final) | report-reviewer | CP-8 |
| 8 | `industrial-html-visualizer` | html-visualizer | — |
| 8.5 | `industrial-html-reviewer` | html-reviewer | CP-9 |

---

## Main-Agent Steps

### Step 0: Setup

```bash
SKILL_PATH="<this-skill-directory>"
PROJECT_ROOT="$(cd "$SKILL_PATH/../../.." && pwd)"

# Create run directory
node "$SKILL_PATH/scripts/setup.mjs" --name <scene_name> --base-dir "$PROJECT_ROOT/workspace/diagnostic-runs"

# Setup Python venv
node "$SHARED_PATH/scripts/uv_env_setup.mjs"
```

`setup.mjs` bootstraps `run_manifest.json` + `.pipeline_events.jsonl` with `run_initialized` event.

### Step 1: Inspect

```bash
node "$SKILL_PATH/scripts/inspect.mjs" <data_path>
```

Log pipeline events:
```bash
node "$SHARED_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" \
  --event step_start --agent main-agent --step inspect \
  --data '{"data_path":"<data_path>"}'

node "$SHARED_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" \
  --event step_complete --agent main-agent --step inspect \
  --files 00_input/input_manifest.json,00_input/user_context.json
```

### Step 2 + 2.5: Ontology Builder

Read `skill://industrial-ontology-builder` and execute the dispatch protocol. Key:
- `DATA_PATH`, `RUN_DIR`, `REFERENCE_DIR`, `PROCESS_DESCRIPTION`, `USER_OBJECTIVE` must be absolute paths
- `SKILL_PATH` = path to `industrial-ontology-builder` skill directory
- `INTERACTION_MODE` = `auto` (default for FULL-AUTO)

**CP-2**: `ontology.json` ≥1KB + schema-valid
**CP-3**: `clarification_needed.json` contains `AUTO_RESOLVED` or `USER_CONFIRMED`

### Step 3 + 3.3: Data Processor

Read `skill://industrial-data-processor` and execute. **ontology_first** — read ontology before any statistical work.

Post-processing after agent completes:
```bash
SKILL_PATH_DATA_PROCESSOR="$PROJECT_ROOT/.claude/skills/industrial-data-processor"
node "$SKILL_PATH_DATA_PROCESSOR/scripts/data-processor-finalize.mjs" "$RUN_DIR"

**CP-4**: `data_analysis_conclusion.json` exists + `plot_manifest.json` has plots > 0


### Step 4: Diagnostician

Read `skill://industrial-diagnostician` and execute. Fuses data + ontology + physics + VLM + time-lag → diagnosis/evidence/confidence/reasoning_chain.

For repair loops, pass `REPAIR_INSTRUCTIONS=<instructions>`.

**CP-5**: All 4 diagnosis outputs schema-valid + quality-check passes

### Step 5a: Judge

Read `skill://industrial-judge` and execute. 10-item quality gate → `judge_feedback.json`.

### Step 5b: Physical Auditor (Pre-Report)

Read `skill://industrial-physical-auditor` with `PRE_REPORT_AUDIT=true`. Runs **parallel** with Judge. Outputs `optimizer_preflight.md`.

### Repair Loop (Best-of-3)

```
best_score = -1; best_round = 0
for iter in 1..3:
  invoke industrial-diagnostician (iter 1 fresh; iter 2-3 with REPAIR_INSTRUCTIONS)
  invoke industrial-judge → score, verdict
  if score > best_score: best_score = score; best_round = iter
    snapshot 04_diagnostics/* → best_round_{iter}/
  if score >= 90: break
  if diag_iters >= 5: break (GLOBAL_CAP)
  diag_iters++; log repair_spawn event
# after loop: restore best_round_{best_round}/*
write 05_review/judge_repair_summary.json
if best_score < 90: mark [BEST_EFFORT] + confidence ≤70
proceed to Step 6 regardless  # NEVER halt
```

**Anti-Oscillation**: >70% issue-type overlap vs previous round → oscillation. 3rd oscillation → `COMPETING_SET`, confidence ≤50.

### Step 6: Reporter

Read `skill://industrial-reporter` and execute. **Judge-gated**: only proceed if verdict==pass ∧ score≥90 OR `judge_repair_summary` proves 3 rounds exhausted.

**CP-7**: `report.md` + `run_summary.json` exist

### Step 7: Physical Auditor (Final)

Read `skill://industrial-physical-auditor` (final mode). Audits `report.md` → `optimizer.md`.

**CP-8**: `optimizer.md` contains `ENDORSED`

### Step 8: HTML Visualizer (AUTO)

Read `skill://industrial-html-visualizer` and execute. **Non-interactive** — after CP-8 ENDORSED, immediately launch without asking. Only skip if `00_input/html_opt_out` exists.

### Step 8.5: HTML Reviewer

Read `skill://industrial-html-reviewer` and execute. Review → pass/needs_revision.

**CP-9**: `diagnostic-report.html` ≥5120B + `html_review.json` verdict=pass

### Step 9: Finalize

```bash
SKILL_PATH="<this-skill-directory>"
node "$SKILL_PATH/scripts/pipeline-finalize.mjs" "$RUN_DIR" "$SKILL_PATH"
```

Present: executive summary + key findings + diagnosis type + confidence + recommendations + optimizer highlights + workspace/HTML paths.

---

## Checkpoint Gates (Quick Reference)

| CP | Position | Verify | Fail → |
|:--|---------|--------|--------|
| CP-1 | 1→2 | `input_manifest.json` + `user_context.json` + `run_config.json` | Back to Step 0 |
| CP-2 | 2→2.5 | `ontology.json` ≥1KB + schema-valid | Re-run ontology-builder |
| CP-3 | 2.5→3 | `clarification_status: AUTO_RESOLVED\|USER_CONFIRMED` | Resolve |
| CP-4 | 3→4 | `data_analysis_conclusion.json` + plots>0 | Re-run data-processor |
| CP-5 | 4→5 | 4 diagnosis outputs schema-valid + quality-check | Repair diagnosis |
| CP-6 | 5→6 | `judge_repair_summary.json` + pre-audit no FATAL | Repair (best-of-3) |
| CP-7 | 6→7 | `report.md` + `run_summary.json` | Re-run reporter |
| CP-8 | 7→8 | `optimizer.md` contains `ENDORSED` | Repair loop |
| CP-9 | 8.5 | `diagnostic-report.html` ≥5120B + review pass | Re-run html-visualizer |

---

## Execution Discipline

- **Default FULL-AUTO**: `interaction_mode=auto`, 8 steps continuous, zero human intervention. CP gates are machine-validated.
- **Strictly sequential** — never skip, reorder, or silently omit steps. If not applicable, record `not_applicable_reason`.
- **Ontology first**: Step 2 complete before Step 3 Phase 0.4. Pre-ontology work limited to data conversion/preprocessing.
- **Step 5a + 5b** are the ONLY parallel steps. Everything else is serial.
- **HTML auto-build**: CP-8 ENDORSED → immediately launch Steps 8→8.5→9, no user prompts.

## Repair Governance

| Rule | Limit |
|------|-------|
| Judge best-of-3 | max 3 re-diagnosis rounds per Judge cycle |
| Reviewer repair | max 2 full D→J→R→R cycles |
| Global re-diagnosis cap | 5 total (tracked by `repair_spawn` in `.pipeline_events.jsonl`) |
| Best-effort delivery | Always proceed to report+HTML — never halt on score alone |
| Anti-oscillation | 3rd same-issue oscillation → `COMPETING_SET`, confidence ≤50 |

## Path Stability

| Rule | Requirement |
|------|-------------|
| Absolute paths | `SKILL_PATH`, `RUN_DIR`, `DATA_PATH` must be absolute |
| Path quoting | All path variables quoted in bash: `"$SKILL_PATH/..."` |
| Python path | Use uv-managed venv: `"$SKILL_PATH/scripts/.venv/bin/python"` |
| Artifact consistency | Sub-agents use the exact same `RUN_DIR` as the orchestrator |

## Agent Decoupling

Sub-agents communicate ONLY through workspace files, never through main-agent context:

```
Ontology Builder  → 01_ontology/ontology.json, clarification_needed.json, rag_deep_understanding.json
Data Processor    → 02_processed/*, data_analysis_conclusion.json, 03_figures/* (含 visual_analysis.json)
Diagnostician     → 04_diagnostics/diagnosis.json, evidence.json, confidence.json, reasoning_chain.json
Judge             → 05_review/judge_feedback.json
Pre-Audit         → 05_review/optimizer_preflight.md
Reporter          → report.md, run_summary.json
Report Reviewer   → optimizer.md
HTML Visualizer   → diagnostic-report.html
HTML Reviewer     → 05_review/html_review.json
```

## Failure Recovery (Quick Reference)

| Trigger | Detection | Recovery |
|---------|-----------|----------|
| RAG engine down | `localhost:8765` unresponsive | Continue — ontology-builder uses `parameter_to_physics.json` + web search |
| uv venv creation fails | `uv_env_setup.mjs` non-zero exit | Install uv → retry; still fail → system Python + pip |
| Input data oversized | inspect timeout >300s | `file_inspect.py --sample 50000` |
| Agent timeout/stall | >600s no output | Check partial outputs → continue if usable; retry 1x → mark `[AGENT_TIMEOUT]` |
| API disconnect | System API error | Wait 30s → restart agent; 2x fail → `[API_ERROR]` + degrade to local scripts |
| Artifact missing | File not found after step | ontology missing → `parameter_to_physics.json` minimal ontology; diagnosis missing → `[DIAGNOSIS_FAILED]` |
| Schema validation fail | validate.mjs returns errors | Append error list to prompt → restart 1x; still fail → `[SCHEMA_FAIL]` |
| Plot generation fail | plot_manifest empty/missing | Repair data → redraw; still fail → `image_captions.json` L4 text fallback |
| HTML build fail | diagnostic-report.html missing or review fail | Re-run html-visualizer → 2x fail → deliver report.md only + `HTML_DELIVERY_FAILED` |

## Pipeline Event Logging

Every step logs to `RUN_DIR/.pipeline_events.jsonl`:

```bash
node "$SHARED_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" \
  --event <event_type> --agent <agent_name> --step <step_name> \
  [--files <comma,separated,paths>] [--data '<json>']
```

Key events: `run_initialized`, `step_start`, `step_complete`, `agent_start`, `agent_complete`, `repair_spawn`, `repair_cap_reached`, `artifact_finalize_complete`, `artifact_check_complete`.

## Red-Light Blacklist

Any agent that violates these → Judge must flag:

| # | Forbidden | Alternative |
|---|-----------|-------------|
| 1 | Main agent writes HTML directly | Launch html-visualizer sub-agent (Step 8) |
| 2 | Main agent reads sub-agent protocol then executes itself | Use `Agent({subagent_type: ...})` |
| 3 | Skip data analysis, go straight to diagnosis | Step 3 → Step 4 strict `ontology_first` |
| 4 | Launch Reporter before Judge gate passes | Check verdict+score; only legal action is repair |
| 5 | Force-pick one from COMPETING_SET | Output competing hypotheses table, confidence ≤65 |
| 6 | Use global correlation as causal evidence | Per-product stratification + detrend + Simpson + leave-one-out |
| 7 | HTML with CDN-only, no init detection | Multi-source loading + runtime detection + degraded static content |
| 8 | 3D model as generic factory | Recover real process stages from ontology+report+diagnosis |
| 9 | Conclusion without evidence rank | Every conclusion tagged `[Evidence Rank L1-L7]` |
| 10 | Vague language to avoid judgment | Give specific numbers + confidence, or explicitly state insufficient evidence |

## References

- `resources/pipeline_coherence_and_synergy.md` — Pipeline coherence and synergy rules
- `resources/engineering_delivery_contract.md` — Engineering delivery standards
- `resources/scenario_patterns.md` — Common scenario patterns
- `scripts/` — Pipeline orchestration scripts (setup, inspect, validate, event logging, verification)
- `schemas/` — All JSON Schemas (reference copy)
- `examples/` — Example configurations for reactor, BOPET film, heat exchanger
