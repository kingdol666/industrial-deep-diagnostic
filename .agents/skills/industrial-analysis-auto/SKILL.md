---
name: industrial-analysis-auto
description: "Fully automated orchestrator for industrial deep diagnosis — integrates 8 standardized sub-skills into an end-to-end diagnostic pipeline, from raw sensor/process data to a Chinese-language diagnostic report plus an HTML visualization page, with zero human intervention. 3 modes: auto/interactive/minimal. Outputs: report.md + diagnostic-report.html. Trigger: industrial diagnosis, root cause analysis, fault diagnosis, production process anomaly, quality defect analysis, sensor data analysis, process parameter optimization, SPC excursion, manufacturing diagnostics, automatically run the full 8-step diagnostic pipeline after uploading CSV/XLSX/Parquet data"
---

# Industrial Analysis Auto — Full Pipeline Orchestrator

End-to-end industrial deep diagnosis auto-orchestrator. Upload sensor/process data → 8 fully automated diagnosis steps → `report.md` + `diagnostic-report.html`.

## Inputs / Outputs

### Inputs
| Input | Required | Description |
|-------|----------|-------------|
| CSV/XLSX/Parquet data file | ✓ | Industrial sensor/process data (CSV, XLSX, Parquet) |
| run_config.json (auto-generated) | ✓ | Run configuration (interaction_mode etc.) |
| Reference docs (optional) | - | Process reference documents under data/references/ |

### Outputs
| Output | File | Gate |
|--------|------|:----:|
| Diagnostic ontology | 01_ontology/ontology.json | CP-2 |
| Data analysis conclusion | 02_processed/data_analysis_conclusion.json | CP-4 |
| Diagnosis conclusion | 04_diagnostics/diagnosis.json | CP-5 |
| Quality gate result | 05_review/judge_feedback.json | CP-6 |
| Final report | report.md / run_summary.json | CP-7 |
| Physical audit | optimizer.md | CP-8 |
| HTML report | diagnostic-report.html / 05_review/html_review.json | CP-9 |

## TL;DR

```
Input : CSV/XLSX/Parquet industrial sensor/process data
Output: Chinese-language diagnostic report (report.md) + HTML visualization walkthrough page (diagnostic-report.html)
Core  : ontology construction → detrending/stratification/Simpson detection → competing hypotheses → physics verification → Judge review → HTML visualization
Default: FULL-AUTO — 8 steps run continuously, zero human intervention
```

## Core Principle

Diagnosis = exclusion, not confirmation. Every conclusion requires four conditions: temporal precedence + statistical significance + physical mechanism + no contradiction.

| Pillar | Principle |
|--------|-----------|
| Scenario-Adaptive | Drive the analysis flow from data characteristics — no hardcoded process types |
| RAG Deep Understanding | Semantic understanding via RAG knowledge, not mechanical mapping |
| Data↔Ontology Bidirectional | Ontology predicts → data confirms; data reveals → ontology explains |
| Physics-Based | Every correlation must be traceable to governing equations |

## Pipeline Flow

```
Step 0-1: Setup + Inspect (main agent)
    ↓
Step 2+2.5: [industrial-ontology-builder] → CP-2, CP-3
    ↓
Step 3+3.3: [industrial-data-processor] → CP-4 (includes VLM visual analysis)
    ↓       ┌── repair max 3 ──┐
    ├───────┤                  │
    ↓       ↓                  │
Step 5a:   Step 5b:            │
[judge]    [physical-auditor]  │
   │     (pre-report, parallel)│
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

## Dispatch

Each sub-step dispatches its corresponding sub-agent via the Claude Code `Agent` tool:

```javascript
// Step 2+2.5: Ontology Builder
Agent({
  subagent_type: "context-builder",
  prompt: `DATA_PATH=<data-path>
RUN_DIR=<run-dir>
SKILL_PATH=<path-to-.claude/skills/industrial-ontology-builder>
SHARED_PATH=<path-to-.claude/shared>
INTERACTION_MODE=auto

Read skill://industrial-ontology-builder and execute the ontology construction protocol.
`
})

// Step 3+3.3: Data Processor
Agent({
  subagent_type: "data-processor",
  prompt: `DATA_PATH=<data-path>
RUN_DIR=<run-dir>
SKILL_PATH=<path-to-.claude/skills/industrial-data-processor>
SHARED_PATH=<path-to-.claude/shared>

Read skill://industrial-data-processor and execute. ontology_first — read ontology before any statistical work.
`
})

// Step 4: Diagnostician
Agent({
  subagent_type: "diagnostician",
  prompt: `DATA_PATH=<data-path>
RUN_DIR=<run-dir>
SKILL_PATH=<path-to-.claude/skills/industrial-diagnostician>
SHARED_PATH=<path-to-.claude/shared>

Read skill://industrial-diagnostician and execute. Fuses data + ontology + physics + VLM + time-lag.
For repair loops, pass REPAIR_INSTRUCTIONS=<instructions>.
`
})

// Step 5a: Judge + Step 5b: Physical Auditor (parallel)
Agent({
  subagent_type: "judge",
  prompt: `RUN_DIR=<run-dir>
SKILL_PATH=<path-to-.claude/skills/industrial-judge>
SHARED_PATH=<path-to-.claude/shared>

Read skill://industrial-judge and execute. 10-item quality gate → judge_feedback.json.
`
})
Agent({
  subagent_type: "report-reviewer",
  prompt: `RUN_DIR=<run-dir>
SKILL_PATH=<path-to-.claude/skills/industrial-physical-auditor>
SHARED_PATH=<path-to-.claude/shared>
PRE_REPORT_AUDIT=true

Read skill://industrial-physical-auditor and execute pre-report audit.
`
})

// Step 6: Reporter
Agent({
  subagent_type: "reporter",
  prompt: `RUN_DIR=<run-dir>
SKILL_PATH=<path-to-.claude/skills/industrial-reporter>
SHARED_PATH=<path-to-.claude/shared>

Read skill://industrial-reporter and execute. Judge-gated.
`
})

// Step 7: Physical Auditor (Final)
Agent({
  subagent_type: "report-reviewer",
  prompt: `RUN_DIR=<run-dir>
SKILL_PATH=<path-to-.claude/skills/industrial-physical-auditor>
SHARED_PATH=<path-to-.claude/shared>

Read skill://industrial-physical-auditor (final mode). Audit report.md → optimizer.md.
`
})

// Step 8: HTML Visualizer (AUTO)
Agent({
  subagent_type: "html-visualizer",
  prompt: `RUN_DIR=<run-dir>
SKILL_PATH=<path-to-.claude/skills/industrial-html-visualizer>
SHARED_PATH=<path-to-.claude/shared>

Read skill://industrial-html-visualizer and execute. Non-interactive — after CP-8 ENDORSED, immediately launch.
`
})

// Step 8.5: HTML Reviewer
Agent({
  subagent_type: "html-reviewer",
  prompt: `RUN_DIR=<run-dir>
SKILL_PATH=<path-to-.claude/skills/industrial-html-reviewer>
SHARED_PATH=<path-to-.claude/shared>

Read skill://industrial-html-reviewer and execute. Review → pass/needs_revision.
`
})
```

Sub-agents communicate through the filesystem, never through the main-agent context.

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

**Shell compatibility convention (mandatory)**: all bash commands must not use cmd built-in syntax (`cd /d`, `dir`, backslash paths).
For cross-drive/directory switching, invoke directly with absolute paths (`node "D:/.../setup.mjs"`) or use `cd "D:/path" && cmd`.
(Verified in practice: `cd /d D:\...` fails and retries under POSIX bash, wasting ~1 minute.)

**RAG availability pre-check (3s fast-fail)**: execute once at the end of Step 0 and record in run_config:
```bash
curl -m 3 -s http://localhost:8764/health >/dev/null 2>&1 && RAG_AVAILABLE=true || RAG_AVAILABLE=false
```
`RAG_AVAILABLE=false` → ontology-builder goes straight to the `parameter_to_physics.json` fallback path and skips Phase 2/3
(avoids repeated runtime probing and idle web-search spinning under uncontrollable networks).

### Step 0.5: Adaptive Data Preprocessing (data-source agnosticism gate)

Before inspecting, normalize ANY user data source into the canonical pipeline
input. Run the E-1 stage when the data is a directory, an Excel workbook
(xlsx/xlsm with multiple sheets), a JSON dump, Markdown/HTML tables, or a
mix of formats:

```bash
uv run --project "$SHARED_PATH/scripts" python "$SKILL_PATH/../../industrial-data-preprocessor/scripts/data_preprocessor.py" \
  --data-path <data_file_or_dir> --output "$RUN_DIR/00_input" --name <scene_name>
```

It writes `00_input/preprocessed_data.csv` (canonical table), a
`preprocessing_report.json` audit (per-source disposition, encoding/delimiter/
sheet adaptation, merge keys), and preserves non-tabular docs in
`00_input/context/`. `DATA_PATH` for all downstream steps = the canonical
`preprocessed_data.csv`; `raw_data_path` + the preprocessing block remain in
`input_manifest.json` for provenance. If the report says `no_tabular_data`,
stop and report the audit to the user instead of proceeding.

Read `skill://industrial-data-preprocessor` for the full adaptation matrix.

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

### Step 2-F: Ontology Deterministic Fast Path (reuse hit ≤60s, plan v5 F1)

**Before** dispatching Step 2, attempt the deterministic fast path (pure script asset copy + validation, no semantic judgment; outside the scope of Blacklist #2 "main agent executes the sub-agent protocol"):

```bash
node "$SHARED_PATH/scripts/ontology_store.mjs" fast-reuse \
  --data <DATA_PATH> --run-dir "$RUN_DIR" [--scene <scene_key>]
```

- Output `fastPath:true` → write an event recording the skip reason (satisfies the strictly-sequential `not_applicable` convention):

```bash
node "$SHARED_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" \
  --event step_complete --agent main-agent --step context_builder \
  --data '{"fastpath":true,"reason":"store reuse — deterministic fast path"}'
```

  Then write a `clarification_auto_inferred` event (the fast path has already generated `00_input/clarification_needed.json` AUTO_RESOLVED), and **jump directly to Step 3** — do not dispatch the context-builder sub-agent, do not enter hub wait. CP-2 (schema validation + ≥1KB) is already enforced inside fast-reuse; on failure it automatically rolls back and returns fastPath:false.
- Output `fastPath:false` → proceed with the Step 2 sub-agent dispatch below (extend/miss still require LLM semantic judgment; the Phase -1 instructions remain in effect).
- When `run_config.ontology.mode` is `full`, skip Step 2-F (user forces a rebuild).

### Step 2 + 2.5: Ontology Builder

Read `skill://industrial-ontology-builder` and dispatch via `Agent({subagent_type: "context-builder", ...})`. Key:
- `DATA_PATH`, `RUN_DIR`, `SKILL_PATH`, `SHARED_PATH` must be absolute paths
- `SKILL_PATH` = path to `industrial-ontology-builder` skill directory
- `INTERACTION_MODE` = `auto` (default for FULL-AUTO)
- **Forward the `## Ontology Directive` (ONTOLOGY_MODE / ONTOLOGY_SOURCE) from the runtime prompt** into the dispatch task — the agent executes the Phase -1 mode dispatch based on it:
  - `reuse` hit: the agent copies the asset ontology and completes this step with CP-2 validation within 30 seconds (the largest time win in this pipeline; rebuilding is forbidden)
  - `extend`: incrementally build only the new columns, then merge
  - `full`: standard full flow
- **Sub-agent stop-loss cap**: if cumulative waiting for `ontology.json` exceeds **8 minutes** without completion → abort the sub-agent task; the main agent builds a minimal valid ontology locally per the fallback protocol using `parameter_to_physics.json` (≤3 minutes). Three consecutive serial long waits are forbidden (180s+240s+300s=12 minutes of idle spinning was the largest measured waste).
- All file writes after dispatch must use absolute paths (sub-agent relative-path writes are a historical root cause of failures).

**CP-2**: `ontology.json` ≥1KB + schema-valid. **Immediately after CP-2 passes, publish to the ontology asset store (mandatory in all modes; this is the prerequisite for future reuse hits)**:
```bash
node "$SHARED_PATH/scripts/ontology_store.mjs" publish --run-dir "$RUN_DIR"
```
**CP-3**: `clarification_needed.json` contains `AUTO_RESOLVED` or `USER_CONFIRMED`

### Step 2P (parallel with Step 2, optional): Data Profiling Pre-Pass

After Step 1 completes, data format/quality/production-state profiling **does not depend on ontology semantics**; the Phase 0-1 pre-pass of `data-processor` (producing `02_processed/pre_profile.json`) can be dispatched in parallel with Step 2. Once the ontology is ready, data-processor resumes from Phase 2 and consumes pre_profile.json, skipping duplicate probing. Semantic analysis (discrepancy / R2 validation) **must wait for the ontology** — the semantic part of the ontology_first contract is unchanged. If the current harness does not support parallel sub-agents, remain serial (backward compatible).

### Step 3 + 3.3: Data Processor

Read `skill://industrial-data-processor` and dispatch via `Agent({subagent_type: "data-processor", ...})`. **ontology_first** — read ontology before any statistical work. If `02_processed/pre_profile.json` exists (Step 2P artifact), resume from its conclusions and skip duplicate probing.

Post-processing after agent completes:
```bash
SKILL_PATH_DATA_PROCESSOR="$PROJECT_ROOT/.claude/skills/industrial-data-processor"
node "$SKILL_PATH_DATA_PROCESSOR/scripts/data-processor-finalize.mjs" "$RUN_DIR"
```

Event proof (deterministic remediation to guard against OMP sub-agents omitting execution events — idempotent and harmless if the sub-agent already emitted them):
```bash
node "$SHARED_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" \
  --event agent_complete --agent data-processor --step data_processor \
  --files 02_processed/data_analysis_conclusion.json,03_figures/plot_manifest.json
node "$SHARED_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" \
  --event step_complete --agent main-agent --step data_processor
```

**CP-4**: `data_analysis_conclusion.json` exists + `plot_manifest.json` has plots > 0

### Step 4: Diagnostician

Read `skill://industrial-diagnostician` and dispatch via `Agent({subagent_type: "diagnostician", ...})`. Fuses data + ontology + physics + VLM + time-lag → diagnosis/evidence/confidence/reasoning_chain.

For repair loops, pass `REPAIR_INSTRUCTIONS=<instructions>`; for rounds 2/3 also pass `REPAIR_SCOPE=<files>` (from the repair_scope mapping in judge_feedback.json, see Step 5a). Files outside the scope are restored from the best_round snapshot and marked `carried_over: true` — **not recomputed**.

**CP-5**: All 4 diagnosis outputs schema-valid + quality-check passes

### Step 5a: Judge

Read `skill://industrial-judge` and dispatch via `Agent({subagent_type: "judge", ...})`. 10-item quality gate → `judge_feedback.json`. The feedback must contain a **structured repair scope** `repair_scope: [{dimension, files, instructions}]` (Step 4 repair rounds recompute in a targeted way based on it, avoiding full recomputation of the 4 diagnosis JSONs). In rounds 2/3 the Judge re-reviews only in-scope dimensions plus previous-round blocking re-checks; already-pass dimensions reference previous-round conclusions.

### Step 5b: Physical Auditor (Pre-Report)

Read `skill://industrial-physical-auditor` with `PRE_REPORT_AUDIT=true`. Dispatch via `Agent({subagent_type: "report-reviewer", ...})`. Runs **parallel** with Judge. Outputs `optimizer_preflight.md`.

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

Read `skill://industrial-reporter` and dispatch via `Agent({subagent_type: "reporter", ...})`. **Judge-gated**: only proceed if verdict==pass ∧ score≥90 OR `judge_repair_summary` proves 3 rounds exhausted.

**CP-7**: `report.md` + `run_summary.json` exist

### Step 7: Physical Auditor (Final)

Read `skill://industrial-physical-auditor` (final mode) and dispatch via `Agent({subagent_type: "report-reviewer", ...})`. Audits `report.md` → `optimizer.md`.

**CP-8**: `optimizer.md` contains `ENDORSED`

### Step 8: HTML Visualizer (AUTO)

Read `skill://industrial-html-visualizer` and dispatch via `Agent({subagent_type: "html-visualizer", ...})`. **Non-interactive** — after CP-8 ENDORSED, immediately launch without asking. Only skip if `00_input/html_opt_out` exists.

### Step 8.5: HTML Reviewer

Read `skill://industrial-html-reviewer` and dispatch via `Agent({subagent_type: "html-reviewer", ...})`. Review → pass/needs_revision.

**CP-9**: `diagnostic-report.html` ≥5120B + `html_review.json` verdict=pass

### Step 9: Finalize

```bash
SKILL_PATH="<this-skill-directory>"
node "$SKILL_PATH/scripts/pipeline-finalize.mjs" "$RUN_DIR" "$SKILL_PATH"
```

Present: executive summary + key findings + diagnosis type + confidence + recommendations + optimizer highlights + workspace/HTML paths.

### Step 10: Enhanced Diagnosis (conditional step — deep enhancement E0-E8)

Read the `## Enhancement Directive` (ENHANCEMENT_POLICY / ENHANCEMENT_INTENT_HIT) from the runtime prompt:

| ENHANCEMENT_POLICY | Action |
|--------------------|--------|
| `on` (explicit user request or intent hit) | After baseline Step 9 completes, execute the enhancement chain in the **same run directory**: `node "$PROJECT_ROOT/.claude/skills/industrial-analysis-enhance-auto/scripts/enhance_orchestrator.mjs" --run-dir "$RUN_DIR"`. E0-E1-E6 are all deterministic scripts with zero LLM; reuse the ontology, **never rebuild the baseline**. If E0 reports BLOCKED (baseline artifacts incomplete) → write enhancement_status.json{status:blocked} and close out gracefully, **do not mark the run as failed**. On completion, append-pipeline-event `--event step_complete --step enhance`, and append one line to the end of report.md: "Deep enhancement analysis generated: enhancement/enhanced_analysis.md" |
| `off` | Skip. append-pipeline-event `--event enhance_skipped --data '{"reason":"policy_off"}'` |
| `auto` no intent hit | Skip. `--event enhance_skipped --data '{"reason":"no_intent"}'`; at the end of the summary, tell the user: "If you need deep enhanced diagnosis (conditional analysis / physics bridging / correlation graph), it can be launched for this run with one click" |

Enhancement artifacts land in `RUN_DIR/enhancement/` (enhanced_analysis.md / enhanced-analysis.html / enhancement_status.json),
fully isolated from baseline artifacts; the E1-E6 mtime skip mechanism makes repeated execution incremental and cheap.

---

## Step Turn Budgets (advisory governance, not hard truncation)

| Step | Suggested turn cap | Action when exceeded |
|------|--------------------|----------------------|
| Step 0-1 setup/inspect | 4 | Check script invocation style (mostly path/syntax retries) |
| Step 2 ontology (reuse hit) | 2 | Main agent performs local validation directly |
| Step 2 ontology (full) | 6 | Triggers the 8-minute stop-loss cap |
| Step 3 data processing | 10 | Check whether pre_profile was consumed |
| Step 4 diagnosis | 12 | Check input artifact integrity |
| Step 5a/5b review | 6 | Reference previous-round conclusions |
| Step 6-7 report+audit | 8 | Streamline sections |
| Step 8-9 HTML+finalize | 6 | Degrade to static mode |
| Step 10 enhancement | 3 | Script chain is zero-LLM; exceeding the cap = anomaly |

If the same Step exceeds its budget by 2x twice in a row → record the `step_overbudget` pipeline event and summarize in run_summary.

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
- **Ontology first**: Step 2 complete before Step 3. Pre-ontology work limited to data conversion/preprocessing.
- **Step 5a + 5b** are the ONLY parallel steps. Everything else is serial.
- **HTML auto-build**: CP-8 ENDORSED → immediately launch Steps 8→8.5→9, no user prompts.

### Token & Wait Discipline (plan v5 F2/F3 — execution efficiency discipline)

- **hub wait governance (F2)**: while a sub-agent runs, **each iteration** of the hub wait loop first checks `test -f <key artifact>` — the moment the artifact is ready, break and move downstream; **do not wait the full 300s before checking**. The wait target must be **an artifact written by the sub-agent** (Step 2: `01_ontology/ontology.json`; Step 3: `02_processed/feature_summary.json` or `03_figures/plot_manifest.json` — `data_analysis_conclusion.json` is written by the main-agent finalize and must not be used as a wait target).
- **SKILL.md single-read (F3.1)**: read the full SKILL.md text only once, on first access; read the corresponding reference file for subsequent protocol details; re-reading the full text is forbidden (the claude engine already injects the first 8K chars into the system prompt, so a second read is pure waste).
- **Directory probing discipline (F3.2)**: use `ls <dir>` single-level for directory probing; `ls -R` / recursive glob across the whole tree is forbidden (any probing command taking >2s counts as waste).
- **todo discipline (F3.3)**: at most 1 todo operation per phase (merge sub-item completions into that phase's done update); updating the todo separately for each completed sub-item is forbidden.

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
| Python path | Use shared venv via `uv_env_setup.mjs`: `$SHARED_PATH/scripts/.venv/Scripts/python.exe` (Win) or `$SHARED_PATH/scripts/.venv/bin/python` (POSIX) |
| Artifact consistency | Sub-agents use the exact same `RUN_DIR` as the orchestrator |

## Agent Decoupling

Sub-agents communicate ONLY through workspace files, never through main-agent context:

```
Ontology Builder  → 01_ontology/ontology.json, clarification_needed.json, rag_deep_understanding.json
Data Processor    → 02_processed/*, data_analysis_conclusion.json, 03_figures/* (includes visual_analysis.json)
Diagnostician     → 04_diagnostics/diagnosis.json, evidence.json, confidence.json, reasoning_chain.json
Judge             → 05_review/judge_feedback.json
Pre-Audit         → 05_review/optimizer_preflight.md
Reporter          → report.md, run_summary.json
Report Reviewer   → optimizer.md
HTML Visualizer   → diagnostic-report.html
HTML Reviewer     → 05_review/html_review.json
```

## Data Truth Mandate

**Every number written into JSON/reports must be recomputable from the raw data.**

| Rule | Requirement |
|------|------|
| Numeric traceability | Every number must be annotated with data source (cleaned/raw), row range, and computation method |
| Derived value marking | Inferred/derived values must be explicitly marked `"derived": true` or `"inferred": true` |
| Cleaning audit trail | cleaning_integrity records all cleaning operations |
| Visualization traceability | Every data point in every plot must be traceable to specific dataset rows |
| Unavailable marking | Values that cannot be computed from data → write NOT_APPLICABLE + reason |

---

## Counterfactual Reasoning — Exclusion Constraints

| Constraint | Description |
|------|------|
| Four conditions | Temporal precedence + statistical significance + physical mechanism + no contradiction |
| Exclusion criterion | Any unmet condition → mark as an excluded candidate and provide quantitative justification |
| Physics boundary | Exclusions must be supported by first principles or governing equations |
| Confidence threshold | When exclusion confidence <80, mark `[WEAK_EXCLUSION]` |

---

## Assumptions & Limitations

| Category | Requirement |
|------|------|
| Data limitations | Sampling rate / noise / missing extremes / range limits |
| Model assumptions | Linear approximation / steady-state assumptions / distribution assumptions |
| Uncontrolled confounders | Explicitly list potential confounding variables that cannot be controlled |
| Conclusion confidence intervals | Annotate each conclusion with confidence ± error margin |

---

## Efficiency — Parallel Execution

- No data dependency with upstream/downstream agents → parallelize proactively
- Use deterministic scripts instead of LLM reasoning for predictable results
- Large-file sampling strategy: systematic sampling when >100K rows
- Agent stall >600s → check existing artifacts; if partially usable, keep moving forward

---

## Verification

```bash
SKILL_PATH="<path-to-.claude/skills/industrial-analysis-auto>"
SHARED_PATH="<path-to-.claude/shared>"

# Step 0 setup validation
node "$SKILL_PATH/scripts/setup.mjs" --name <scene_name> --base-dir "$PROJECT_ROOT/workspace/diagnostic-runs"
node "$SHARED_PATH/scripts/uv_env_setup.mjs"

# Step 1 inspect
node "$SKILL_PATH/scripts/inspect.mjs" <data_path>

# Step 9 finalize
node "$SKILL_PATH/scripts/pipeline-finalize.mjs" "$RUN_DIR" "$SKILL_PATH"
```

## Failure Recovery

| Trigger | Detection | Recovery |
|---------|-----------|----------|
| RAG engine down | `localhost:8764` unresponsive | Continue — ontology-builder uses `parameter_to_physics.json` + web search |
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
| 2 | Main agent reads sub-agent protocol then executes itself | Use `Agent({subagent_type: "...", prompt: `...`})` |
| 3 | Skip data analysis, go straight to diagnosis | Step 3 → Step 4 strict `ontology_first` |
| 4 | Launch Reporter before Judge gate passes | Check verdict+score; only legal action is repair |
| 5 | Force-pick one from COMPETING_SET | Output competing hypotheses table, confidence ≤65 |
| 6 | Use global correlation as causal evidence | Per-product stratification + detrend + Simpson + leave-one-out |
| 7 | HTML with CDN-only, no init detection | Multi-source loading + runtime detection + degraded static content |
| 8 | 3D model as generic factory | Recover real process stages from ontology+report+diagnosis |
| 9 | Conclusion without evidence rank | Every conclusion tagged `[Evidence Rank L1-L7]` |
| 10 | Vague language to avoid judgment | Give specific numbers + confidence, or explicitly state insufficient evidence |
