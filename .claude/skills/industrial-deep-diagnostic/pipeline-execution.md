# Pipeline Execution Reference

> **Load this file only during repair loops or when detailed validation rules are needed.**
> SKILL.md contains the main step-by-step protocol. This file covers: numbering systems, step command reference, repair loop protocol, pipeline event logging, statistical validation framework, and common mistakes.

## Numbering Systems — Four Separate Schemes

This skill uses FOUR distinct numbering systems. Do not conflate them.

| System | Scope | Used In | Example |
|--------|-------|---------|---------|
| **Pipeline Step 0-9** | Orchestration-level workflow | SKILL.md | "Step 4: Diagnostician" |
| **Agent Phase 0-7** | Diagnostician's internal workflow | agents/diagnostician.md | "Phase 1: Data Probing" |
| **Reasoning Segment R1-R8** | Structured reasoning trace output | reasoning_chain.json | "R4: Hypothesis Generation" |
| **Method Stage 1-6** | Generic diagnostic methodology | resources/diagnosis_method.md | "Stage 3: Temporal Analysis" |

---

## Step Command Reference

Full validation and event-logging commands for each pipeline step.

### Step 0: Setup

```bash
SKILL_PATH="<path-to-this-skill>"
PROJECT_ROOT="$(cd "$SKILL_PATH/../../.." && pwd)"
node "$SKILL_PATH/scripts/setup.mjs" --name <scene_name> --base-dir "$PROJECT_ROOT/workspace/diagnostic-runs"
node "$SKILL_PATH/scripts/uv_env_setup.mjs"
```

`setup.mjs` bootstraps both `run_manifest.json` and `.pipeline_events.jsonl` with a `run_initialized` event.

### Step 1: Inspect

```bash
node "$SKILL_PATH/scripts/inspect.mjs" <data_path>
```

Recommended event logging:
```bash
node "$SKILL_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" --event step_start --agent main-agent --step inspect --data '{"data_path":"<data_path>"}'
node "$SKILL_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" --event step_complete --agent main-agent --step inspect --files 00_input/input_manifest.json,00_input/user_context.json
```

### Step 2: Context Build (context-builder agent)

```javascript
Agent({
  subagent_type: "context-builder",
  description: "Step 2: 构建领域本体 — RAG检索+网络搜索+本体构建",
  permissionMode: "bypassPermissions",
  prompt: `DATA_PATH=${DATA_PATH}
RUN_DIR=${RUN_DIR}
REFERENCE_DIR=${REFERENCE_DIR}
PROCESS_DESCRIPTION=${PROCESS_DESCRIPTION}
USER_OBJECTIVE=${USER_OBJECTIVE}
SKILL_PATH=${SKILL_PATH}
INTERACTION_MODE=auto

Read "$SKILL_PATH/agents/context-builder.md" and execute the complete protocol. Validate ontology_schema before completion.`,
  run_in_background: true
})
```

Validate ontology:
```bash
node "$SKILL_PATH/scripts/validate.mjs" "$SKILL_PATH/schemas/ontology_schema.json" "$RUN_DIR/01_ontology/ontology.json"
```

### Step 2.5: Clarification Gate

Record the gate outcome:
```bash
node "$SKILL_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" --event clarification_auto_inferred --agent main-agent --step clarification_gate
```

### Step 3: Data Processing (data-processor agent)

Launch with `RUN_DIR`, `SKILL_PATH`, `DATA_PATH`. Tell it to read `agents/data-processor.md`, execute Phase 0-6, use the uv-managed Python path, and VLM visual analysis is handled by Step 3.5 (independent agent), not by data-processor.

Stabilization before Step 4:
```bash
node "$SKILL_PATH/scripts/normalize-anomaly-report.mjs" "$RUN_DIR"
node "$SKILL_PATH/scripts/synthesize-data-analysis-conclusion.mjs" "$RUN_DIR"
```

Key validation commands:
```bash
node "$SKILL_PATH/scripts/validate.mjs" "$SKILL_PATH/schemas/scenario_classification_schema.json" "$RUN_DIR/02_processed/scenario_classification.json"
node "$SKILL_PATH/scripts/validate.mjs" "$SKILL_PATH/schemas/anomaly_report_schema.json" "$RUN_DIR/02_processed/anomaly_report.json"
node "$SKILL_PATH/scripts/validate.mjs" "$SKILL_PATH/schemas/data_analysis_conclusion_schema.json" "$RUN_DIR/02_processed/data_analysis_conclusion.json"
node "$SKILL_PATH/scripts/validate.mjs" "$SKILL_PATH/schemas/visual_analysis_schema.json" "$RUN_DIR/03_figures/visual_analysis.json"
node "$SKILL_PATH/scripts/validate.mjs" "$SKILL_PATH/schemas/image_captions_schema.json" "$RUN_DIR/03_figures/image_captions.json"
```

### Step 4: Diagnostician

Launch with `RUN_DIR`, `SKILL_PATH`, `DATA_PATH`, and optional `REPAIR_INSTRUCTIONS`. Tell it to read `agents/diagnostician.md`, execute Phase 0-7.

Validate all four outputs:
```bash
node "$SKILL_PATH/scripts/validate.mjs" "$SKILL_PATH/schemas/diagnosis_schema.json" "$RUN_DIR/04_diagnostics/diagnosis.json"
node "$SKILL_PATH/scripts/validate.mjs" "$SKILL_PATH/schemas/evidence_schema.json" "$RUN_DIR/04_diagnostics/evidence.json"
node "$SKILL_PATH/scripts/validate.mjs" "$SKILL_PATH/schemas/confidence_schema.json" "$RUN_DIR/04_diagnostics/confidence.json"
node "$SKILL_PATH/scripts/validate.mjs" "$SKILL_PATH/schemas/reasoning_chain_schema.json" "$RUN_DIR/04_diagnostics/reasoning_chain.json"
node "$SKILL_PATH/scripts/diagnostic-quality-check.mjs" "$RUN_DIR"
```

### Step 5: Judge

Launch with `RUN_DIR`, `SKILL_PATH`, `DATA_PATH`. Tell it to read `agents/judge.md`, run full quality gate, use lowercase enum values only.

Validate + gate check:
```bash
node "$SKILL_PATH/scripts/validate.mjs" "$SKILL_PATH/schemas/judge_feedback_schema.json" "$RUN_DIR/05_review/judge_feedback.json"
node "$SKILL_PATH/scripts/judge-gate-check.mjs" "$RUN_DIR" --skip-summary
```

### Step 6: Reporter

Launch with `RUN_DIR`, `SKILL_PATH`. Tell it to read `agents/reporter.md`, use `visual_analysis.json` as primary figure evidence.

### Step 7: Report Reviewer

Launch with `RUN_DIR`, `SKILL_PATH`, `DATA_PATH`. Tell it to read `agents/report-reviewer.md`.

### Step 8: HTML Visualizer

```javascript
Agent({
  subagent_type: "html-visualizer",
  description: "Step 8: 生成诊断结果的前端 HTML 可视化讲解页面",
  permissionMode: "bypassPermissions",
  prompt: `RUN_DIR=${RUN_DIR}
SKILL_PATH=${SKILL_PATH}
OUTPUT_HTML=${RUN_DIR}/diagnostic-report.html
AUDIENCE=mixed
VISUAL_MODE=story

Read "${SKILL_PATH}/agents/html-visualizer.md" and execute the complete protocol.`,
  run_in_background: true
})
```

**HTML Opt-Out** (align with SKILL.md §Step 8): if the user explicitly declines HTML ("不要 HTML 页面" / "只要 report.md" / "跳过可视化"), the main agent MUST run `touch "$RUN_DIR/00_input/html_opt_out"` **before** Step 8. `finalize-run-artifacts.mjs` checks this marker and skips the HTML-delivery gate so opt-out runs aren't blocked. Without this marker, HTML delivery is mandatory (CP-9).

### Step 8.5: HTML Reviewer

```javascript
Agent({
  subagent_type: "html-reviewer",
  description: "Step 8.5: 审核 HTML 可视化页面是否清楚、完整、能支撑结论",
  permissionMode: "bypassPermissions",
  prompt: `RUN_DIR=${RUN_DIR}
SKILL_PATH=${SKILL_PATH}
OUTPUT_HTML=${RUN_DIR}/diagnostic-report.html
AUDIENCE=mixed

Read "${SKILL_PATH}/agents/html-reviewer.md" and execute the complete review protocol.`,
  run_in_background: true
})
```

只有审核通过（`verdict: "pass"`），页面才算最终交付。如果 `html-reviewer` 给出 blocking issues，必须回到 `html-visualizer` 修订页面，再次审核。

### Step 9: Finalize

```bash
node "$SKILL_PATH/scripts/finalize-run-artifacts.mjs" "$RUN_DIR" "$SKILL_PATH"
node "$SKILL_PATH/scripts/artifact-check.mjs" "$RUN_DIR" "$SKILL_PATH"
node "$SKILL_PATH/scripts/evidence-closure-check.mjs" "$RUN_DIR" --write
```

After Step 7 returns `ENDORSED`, the default next action is to launch the html-visualizer subagent (Step 8), then html-reviewer on the output (Step 8.5).

Treat this HTML generation as part of the normal completion path unless the user explicitly opts out. **This step is non-interactive and automatic** — after CP-8 `ENDORSED`, do NOT pause to ask the user "shall I continue to build the HTML?"; immediately launch `html-visualizer` → `html-reviewer` → Step 9 finalize in sequence.
The main agent may summarize the result, but it must not directly produce the HTML in the main context. See `agents/html-visualizer.md` and `agents/html-reviewer.md` for the full agent definition and protocol.

The generated page must include runtime readiness checks for:

- `window.echarts`
- `window.THREE`
- `OrbitControls` when used
- at least one successfully initialized chart
- at least one successfully initialized 3D scene

If interactive libraries fail to load, the page must surface a visible degraded-mode notice and keep the static explanation usable.

---

---

## Pipeline Event Log

Each agent MUST append a JSON line to `RUN_DIR/.pipeline_events.jsonl` at start and completion:

```jsonl
{"event": "agent_start", "agent": "context-builder", "timestamp": "2026-05-25T10:00:00Z"}
{"event": "agent_complete", "agent": "context-builder", "timestamp": "2026-05-25T10:02:30Z", "files_written": ["01_ontology/ontology.json"], "errors": null}
```

The main agent logs repair-loop events:

```jsonl
{"event": "repair_spawn", "iteration": 1, "source": "judge", "diag_iters_total": 1, "timestamp": "..."}
{"event": "repair_cap_reached", "diag_iters_total": 5, "reason": "Global re-diagnosis cap exceeded", "timestamp": "..."}
```

**At the start of any repair loop, count `repair_spawn` entries to restore `diag_iters`.** Do not rely on in-memory state.

**Recommended implementation**: use `scripts/append-pipeline-event.mjs` rather than handwritten JSONL appends. This reduces malformed logs and missing agent lifecycle entries.

### Main-Agent Events

The main agent must also leave machine-verifiable breadcrumbs for non-subagent steps:

```jsonl
{"event":"run_initialized","step":"setup","agent":"main-agent","timestamp":"..."}
{"event":"step_start","step":"inspect","agent":"main-agent","timestamp":"..."}
{"event":"step_complete","step":"inspect","agent":"main-agent","timestamp":"...","files_written":["00_input/input_manifest.json","00_input/user_context.json"]}
{"event":"clarification_auto_inferred","step":"clarification_gate","agent":"main-agent","timestamp":"..."}
{"event":"artifact_finalize_complete","step":"present","agent":"main-agent","timestamp":"...","files_written":["run_summary.json","evidence_closure_report.json"]}
{"event":"artifact_check_complete","step":"present","agent":"main-agent","timestamp":"...","status":"PASS"}
```

The helper now also synchronizes `run_manifest.json`, enforces prerequisite order for step/agent starts, and verifies declared outputs exist before recording successful completion.

---

## Repair Loop Protocol

### Judge Repair (Step 5) — Best-of-3 with Guaranteed Delivery

```
best_score = -1; best_round = 0
for iter in 1..3:
  spawn Diagnostician (iter 1 fresh; iter 2-3 with REPAIR_INSTRUCTIONS from prev judge_feedback.json)
  spawn Judge → score, verdict
  if score > best_score:
    best_score = score; best_round = iter
    snapshot 04_diagnostics/{diagnosis,evidence,confidence,reasoning_chain}.json → best_round_{iter}/
  if score >= 90: break                  # PASS — use this round directly
  if diag_iters >= 5: break              # GLOBAL_CAP
  diag_iters++; log repair_spawn event
# after loop: restore best_round_{best_round}/* → 04_diagnostics/ (canonical)
write 05_review/judge_repair_summary.json {rounds_attempted: iter, scores[], selected_round: best_round, selected_score: best_score, converged: best_score>=90}
if best_score < 90: mark [BEST_EFFORT] in report + confidence ceiling ≤70
proceed to Step 6 → Step 7 → Step 8 regardless   # NEVER halt — always deliver report + HTML
```

**Invariant**: the pipeline always converges to report.md + diagnostic-report.html. No Judge score triggers a halt; `<90` after 3 rounds yields best-effort delivery with a `[BEST_EFFORT]` caveat. The `append-pipeline-event.mjs` reporter/completion gate honors `judge_repair_summary.json {converged:false, rounds_attempted>=3}` as a valid pass.

### Reviewer Repair (Step 7.5)

```
for iter in 1..2:
  if verdict == ENDORSED → break
  if diag_iters >= 5 → break (GLOBAL_CAP)
  diag_iters++
  log repair_spawn event
  re-spawn Diagnostician with physical critique from optimizer.md
  re-run Judge (fresh counter) → Reporter → Reviewer
```

### Global Rules

- The agent MUST execute the pipeline in order and must not skip, reorder, compress, or silently omit pipeline steps unless a step has an explicit documented skip condition in the skill protocol.
- "Not applicable" is different from "skipped": if a step does not apply to the current data (for example, no valid time column for temporal alignment), the agent must record that explicitly in the relevant artifact and then continue to the next defined pipeline step.
- Each re-diagnosis spawn increments `diag_iters`. When `diag_iters >= 5`, stop ALL repair loops.
- Reviewer repair triggers full re-run: Diagnostician → Judge → Reporter → Reviewer.
- Judge iteration counter resets when Reviewer triggers re-diagnosis (no carryover).
- When global cap hit: present results with `[REPAIR_CAP_REACHED]` caveat.

### Counter Persistence

The `diag_iters` counter is file-persisted in `.pipeline_events.jsonl`:
1. Before Step 5: count existing `repair_spawn` entries to restore counter
2. After each re-diagnosis: append `repair_spawn` event with current total
3. On reconnection/context compaction: re-count from file

---

## Step 2.5: Clarification Gate Protocol

After Context Builder completes, check `00_input/clarification_needed.json`. Behavior depends on `interaction_mode` from `00_input/run_config.json` (defaults to `auto` if the file does not exist or the field is missing):

### `auto` mode:
1. Read `clarification_needed.json` to understand unknown parameters
2. **Do NOT ask the user.** Apply auto-inference (resources/physics_inference_framework.md L1-L5) to assign best-guess physical meanings
3. Update `01_ontology/ontology.json` and `schema.json` with inferred meanings
4. Mark all parameters with `"physical_meaning_confidence": "INFERRED"` (uppercase, matches ontology schema enum `KNOWN | INFERRED | UNKNOWN`) and `"auto_inferred": true`. Also write `"clarification_status": "AUTO_RESOLVED"` (or `USER_CONFIRMED` after interactive answers) — CP-3 greps this field.
5. Log auto-inference event to `.pipeline_events.jsonl`
6. Proceed directly to Step 3

### `interactive` mode:
1. Read the file to understand unknown parameters
2. Group related parameters into single questions (max 4 per round)
3. Present the Context Builder's best guesses for user to confirm/correct
4. After answers: update `01_ontology/ontology.json` and `schema.json`
5. Mark resolved parameters in `clarification_needed.json`
6. Log clarification event to `.pipeline_events.jsonl`

### `minimal` mode:
1. Read `clarification_needed.json` — focus ONLY on `critical_unknowns`
2. Ask user about CRITICAL parameters only (max 2 questions)
3. For HIGH/MEDIUM unknowns: use auto-inference (resources/physics_inference_framework.md L1-L5)
4. Update ontology with confirmed + inferred meanings
5. Log events to `.pipeline_events.jsonl`

**Skip condition**: If no CRITICAL/HIGH unknowns (or in auto mode), skip directly to Step 3.

---

## RAG Knowledge Validation — Two-Stage Protocol

RAG validation occurs in TWO stages across two pipeline steps. See `resources/pipeline_coherence_and_synergy.md` for the full protocol.

**Stage 1 (Context Builder, Step 2)**: Pre-checks on raw data — value range, basic direction sign, trend slope, confound presence. Outputs `rag_deep_understanding.json.validation_queue[]` with claims needing thorough validation.

**Stage 2 (Data Processor, Step 3)**: Thorough validation using full statistical pipeline — temporal (CCF lag), stratified (Simpson's), detrended, functional form. Outputs `rag_validation_report.json`.

The Diagnostician (Step 4), Judge (Step 5), and Report Reviewer (Step 7) all consume both Stage 1 and Stage 2 results.

---

## Evidence Closure Gate

At the end of a run, the pipeline must pass not only artifact existence checks but also **evidence closure**:

1. `anomaly_report.json` must expose both:
   - `process_parameter_fluctuation`
   - `dual_drive_analysis`
2. `data_analysis_conclusion.json` must summarize:
   - baseline scripts
   - custom expert scripts or explicit no-custom justification
   - ontology / industry interpretation
   - data-supported conclusions
3. `diagnosis.json` must contain both:
   - `process_fluctuation_analysis`
   - `integrated_dual_drive_analysis`
4. `evidence.json` / `judge_feedback.json` must carry forward validation constraints from `validate_report.json`
5. `report.md` must explicitly disclose the pure-process view, dual-drive view, and expert data-analysis conclusion

Use:
```bash
node "$SKILL_PATH/scripts/evidence-closure-check.mjs" "$RUN_DIR" --write
```

If this check fails, the run is not diagnostically closed even if all files exist.

---

## Change-Point Segment Verification (Phase 0.5)

When `validate_report.json` detects change points with severity CRITICAL or segment_count > 5:

### Per-Segment Correlation Re-Verification

For each candidate parameter-defect pair, re-verify within regime segments:

| Pattern | |r| > 0.2 in ≥X% segments | Classification |
|---------|:-----------------------:|---------------|
| ALL_PRESENT | ≥80% | REGIME_UNIVERSAL — robust |
| MOST_PRESENT | 50-80% | REGIME_CONSISTENT — mostly preserved |
| PARTIAL | 20-50% | REGIME_SPECIFIC — specific regimes only |
| ABSENT | <20% | REGIME_SPURIOUS — aggregate artifact |

### Segment-Aware Adjustments

- REGIME_SPECIFIC: confidence -10 to -15
- REGIME_SPURIOUS: exclude from hypothesis generation
- REGIME_UNIVERSAL: confidence +5

### Cross-Reference with Product Stratification

If regime boundaries align with product transitions → stratify by product instead.
If NOT → both types of segmentation should be checked.

---

## Statistical Validation Framework

### What Each Check Catches

| Check | Tool | What It Catches |
|-------|------|----------------|
| Data sorting validation | `stats.mjs` | Lag analysis on batch-sorted data → spurious correlations |
| Simpson's Paradox | `stats.mjs` + `stats_validate.mjs` | Aggregate correlations that reverse within subgroups |
| Time-trend confounding | `stats.mjs` | Correlations driven by shared time drifts |
| Outlier sensitivity / leave-one-out | `stats_validate.mjs` | Correlations dominated by few extreme points; recomputes r dropping each observation/batch, flags `leverage_driven` when |Δr|>0.2 (v6.7 explicit contract) |
| Spearman-Pearson divergence | `stats.mjs` | Outlier or non-linear influence |
| Lag window consistency | `stats.mjs` | Isolated spikes in CCF (artifact indicators) |
| Multiple testing correction | `stats.mjs` | Chance "significant" results from many comparisons |
| Mutual Information | `stats.mjs` | Non-linear dependencies that Pearson/Spearman miss |
| Granger Causality | `stats.mjs` | Temporal predictive causality (requires time-sorted data) |
| Change Point Detection | `stats_validate.mjs` | Regime shifts invalidating stationarity |
| Interaction Effects | `stats.mjs` | Parameter combinations with synergistic effects |

### Confidence Adjustment Rules

| Validation Finding | Impact |
|--------------------|:------:|
| Data NOT time-sorted + lag used as evidence | -25 to -40 |
| Simpson's Paradox (direction reversal) | -20 to -30 |
| Simpson's Paradox (moderate attenuation) | -10 to -15 |
| Trend confounding (attenuation > 50%) | -15 to -20 |
| Outlier-driven correlation (|Δr|>0.2 on leave-one-out) | -10 to -15; EXCLUDE if direction reverses (e.g. r=+0.40 → -0.128) |
| Spearman-Pearson divergence > 0.15 | -5 to -10 |
| Isolated lag spike | Treat as concurrent only |
| Parameter physical meaning unknown | -15 to -25 |
| Change point detected | -10 to -20 |
| Granger contradicts correlation direction | -20 to -30 |
| INDISTINGUISHABLE competing hypotheses | Ceiling: 65 |
| No discriminating sensor | -15 to -30 |

---

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Lag correlations on non-time-sorted data | Check `sorting_validation.time_sorted` before any lag claim |
| Missing Simpson's Paradox | Stratified analysis + `stats_validate.mjs` detect reversals |
| Confusing trend correlation with causal coupling | Check detrended correlations |
| Trusting Pearson for skewed defect data | Compare Spearman alongside |
| Stating "X caused Y" without all 4 criteria | Use [HYPOTHESIS] marker |
| Skipping `plot_manifest.json` | Data Processor MUST write it |
| Main agent holding domain context | Spawn sub-agents; main agent only orchestrates |
| Skipping physical audit (Step 7) | Always run — catches spurious correlations |
| Not validating parameter physical meaning | Use clarification gate (Step 2.5) |
| Ignoring reviewer's physical concerns | Step 7.5 repair loop |
| Picking one root cause when alternatives predict identical observables | Step C: Data Discriminability → COMPETING_SET |
| High confidence on time-colinear mechanisms | Both progress with time → ceiling 65 |
| Not checking if quality resets on component replacement | Phase 1 data probing — use transition events |
