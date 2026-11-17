---
name: industrial-analysis-auto
description: "Fully automated orchestrator for industrial deep diagnosis — integrates 8 standardized sub-skills into an end-to-end diagnostic pipeline, from raw sensor/process data to a Chinese-language diagnostic report plus an HTML visualization page, with zero human intervention. 3 modes: auto/interactive/minimal. Outputs: report.md + diagnostic-report.html. Trigger: industrial diagnosis, root cause analysis, fault diagnosis, production process anomaly, quality defect analysis, prediction, failure prediction, predictive maintenance, sensor data analysis, process parameter optimization, SPC excursion, manufacturing diagnostics, automatically run the full 8-step diagnostic pipeline after uploading CSV/XLSX/Parquet data. Do NOT use for a single-purpose diagnosis when upstream artifacts already exist and only the diagnostic engine is needed (use industrial-diagnostician); do NOT use to run only the post-run E0-E8 enhancement stages on a completed run (use industrial-analysis-enhance-auto); do NOT use for format adaptation / multi-format ingestion alone (use industrial-data-preprocessor); do NOT use for standalone DOE analysis (use industrial-doe-analyzer), watch/alert screening (use industrial-sentinel), stability reporting (use industrial-line-stability-report), or closed-loop tuning campaigns (use industrial-optimizer-loop)."
---

# Industrial Analysis Auto — Full Pipeline Orchestrator

End-to-end industrial deep diagnosis auto-orchestrator. Upload sensor/process data → 8 fully automated diagnosis steps → `report.md` + `diagnostic-report.html`.

**Scheduling view** — mode authority = `run_config.run_mode`; runtime directives honored per the referenced step sections.

## Pipeline Flow

```
Step 0-1: Setup + Inspect (main agent)
    ↓
Step 2+2.5: [industrial-ontology-builder] → CP-2, CP-3
    ↓
Step 3+3.3: [industrial-data-processor] → CP-4
    ├─ fast: ≤8 plots; VLM ≤4 CRITICAL plots or caption fallback; no separate 2P agent
    └─ full: profile pre-pass eligible >20K rows; full plot/VLM policy
    ↓
Step 4: [diagnostician] → CP-5
    ├─ fast: reuse upstream statistics; ≤16 tool-call advisory
    └─ full: exhaustive competing-hypothesis protocol
    ↓
Step 5a: [judge] → CP-6
    ├─ full only: Step 5b pre-report physical audit
    └─ fast: record 5b skip reason; CP-8 remains mandatory
    ↓ CP-6 pass
Step 6: [industrial-reporter] → CP-7 + CP-7L
    ↓
Step 7: [industrial-physical-auditor] (final) → CP-8 ENDORSED
    ↓
Step 8: [industrial-html-visualizer] (unless explicit opt-out)
    ↓
Step 8.5: [industrial-html-reviewer] → CP-9
    ↓ PASS
Step 9: Finalize; only then record run_completed
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

## Execution Discipline

- **fast mode (default)**: `run_mode=fast` — steps 0→1→2→3(+3.5 capped VLM)→4→5a→6→7→8→8.5→9→9.5→10 continuous, Step 2P and 5b not dispatched (see Run Modes).
- **Strictly sequential** — never skip, reorder, or silently drop a step. A step that does not apply must record `not_applicable_reason` (e.g. `fast_mode`, `no_vision_model`, `serial_harness`).
- **Ontology first**: Step 2 completes before Step 3. Pre-ontology work is limited to data conversion/preprocessing.
- **Step 5a + 5b** are the only parallel pair (5b runs in full mode only). Everything else is serial.
- **HTML auto-build**: CP-8 ENDORSED → immediately launch Steps 8→8.5→9 with no user prompt.

## Dispatch

Each sub-step dispatches its corresponding sub-agent via the Claude Code `Agent` tool.

**Before dispatch, read the schema-validated `00_input/run_config.json` and use `run_mode` as the mode authority.** For each conditional stage that is skipped, append a matching `artifact_check_complete` event with `--data '{"skipped_stage":"<stage>","reason":"<reason>"}'` and append the same `{stage, reason, event:"artifact_check_complete"}` record to `run_manifest.execution_policy.audit.skipped_stages`. The finalizer rejects a declared skip without a matching log event. Do not add skip records for stages that actually ran.

**Every dispatch prompt SHOULD carry these four audit lines**. The Agent tool has no hard per-call tool-count limiter; `HARD_BUDGET` is an instruction, not mechanical enforcement. The machine-enforced controls are schema-validated `run_mode`, final artifact gates, and recording of conditional-stage skips:

```
HARD_BUDGET: ≤N tool calls for this task; when reached, finalize with what exists and report gaps (N = budget-table cap ×2)
MODE: fast | full
SINGLE_READ: the essentials are already inlined here — read SKILL.md at most once, never re-read after work starts
REUSE_MANDATE: statistics already in 02_processed/* are cited as [reused], never recomputed
```

**Enforcement (not advisory)**: the cap is passed INTO each dispatch prompt as a hard tool-call budget — `HARD_BUDGET: ≤N tool calls for this task; when reached, finalize with what you have and report gaps`. Reading the full SKILL.md again counts against the budget (single-read rule below). Measured waste when budgets were not passed: data-processor 98 tool calls / 28 min on 80 rows (2026-10-13 fieldtest) — the single largest wall-clock cost of the whole pipeline.

Sub-agents communicate through the filesystem, never through the main-agent context.

Templates per step: `references/dispatch-prompts.md` (read before dispatching).

## Checkpoint Gates (Quick Reference)

| CP | Position | Verify | Fail → |
|:--|---------|--------|--------|
| CP-1 | 1→2 | `input_manifest.json` + `user_context.json` + schema-valid `run_config.json` (`run_mode` = fast/full); when the Step 0.5 chain ran, both `quality_gate.mjs` (E-1 then E-1H) exit 0 — an E-1 exit 2 = no tabular data / single-file passthrough (report and stop, not a failure) | Back to Step 0 |
| CP-2 | 2→2.5 | `ontology.json` ≥1KB + schema-valid | Re-run ontology-builder |
| CP-3 | 2.5→3 | `clarification_status: AUTO_RESOLVED\|USER_CONFIRMED` | Resolve |
| CP-4 | 3→4 | `data_analysis_conclusion.json` + plot count within mode budget + plot path/ink validation | Re-run data-processor |
| CP-5 | 4→5 | 4 diagnosis outputs schema-valid + quality-check | Repair diagnosis |
| CP-6 | 5→6 | Judge pass + no blocking issues; full mode additionally requires pre-audit no FATAL; fast mode requires a recorded 5b skip and CP-8 final audit | Keep report draft as FAILED; repair/mark best-effort, never mark completed |
| CP-7 | 6→7 | `report.md` + `run_summary.json` + section/lint checks | Re-run reporter |
| CP-8 | 7→8 | `optimizer.md` contains `ENDORSED` | Final audit repair; no success status until endorsed |
| CP-9 | 8.5 | `diagnostic-report.html` ≥5120B + review pass, unless explicit HTML opt-out is recorded | Re-run html-visualizer |

**CP-2**: `ontology.json` ≥1KB + schema-valid — deterministic gate (exit 0 ok | 2 stage absent | 3 fail):
```bash
node "$SHARED_PATH/../../.claude/skills/industrial-ontology-builder/scripts/quality_gate.mjs" --run-dir "$RUN_DIR"
```

CP-7L (pre-audit lint gate — mandatory before Step 7):

```bash
node "$SHARED_PATH/../../.claude/skills/industrial-analysis-auto/scripts/pre_audit_lint.mjs" "$RUN_DIR"
```

**CP-8**: `optimizer.md` contains `ENDORSED` — deterministic gate (exit 0 ok | 2 audit not run | 3 fail):
```bash
node "$SHARED_PATH/../../.claude/skills/industrial-physical-auditor/scripts/quality_gate.mjs" --run-dir "$RUN_DIR"
```

Exact invocations above; per-step context, skip-event recipes and event logging: `references/orchestration-steps.md` — read the matching step section in full before executing that step.

## Run Modes (run_config.run_mode)

| Mode | Purpose | Trigger |
|------|---------|---------|
| **fast** | Quick root-cause + correlation answer, same reasoning core | explicitly set by caller with `--mode fast` / run_config.run_mode=fast |
| **full** (default) | Benchmark/paper-grade full evidence chain | default from setup.mjs; benchmark pipeline; user asks for 完整/详尽 |

**Directive handling (binding)**: honor the runtime-prompt directives — `## Ontology Directive` (reuse|extend|full), `## Enhancement Directive` (ENHANCEMENT_POLICY on|off|auto), and the analysis-intent routing in the frontmatter Do-NOT clause; step recipes: `references/orchestration-steps.md` §Step 2 + 2.5 / §Step 2-F / §Step 10. Fast/full cuts: `references/run-modes-and-efficiency.md`.

## TL;DR

```
Input : CSV/XLSX/Parquet industrial sensor/process data
Output: Chinese-language diagnostic report (report.md) + HTML visualization walkthrough page (diagnostic-report.html)
Core  : ontology construction → detrending/stratification/Simpson detection → competing hypotheses → physics verification → Judge review → HTML visualization
Default: FULL-AUTO — baseline Steps 0-9 run continuously; optional deep enhancement is Step 10
```

## Repair Governance

| Rule | Limit |
|------|-------|
| Judge best-of-3 | max 3 re-diagnosis rounds per Judge cycle |
| Reviewer repair | max 2 full D→J→R→R cycles |
| Global re-diagnosis cap | 5 total (tracked by `repair_spawn` in `.pipeline_events.jsonl`) |
| Best-effort delivery | Always proceed to report+HTML — never halt on score alone |
| Anti-oscillation | 3rd same-issue oscillation → `COMPETING_SET`, confidence ≤50 |

Best-of-3 repair-loop pseudo-code, snapshots and anti-oscillation: `references/repair-loop-and-gates.md` — read in full before any repair round (Judge < 90 or auditor fail).

### Token & Wait Discipline (plan v5 F2/F3 — execution efficiency discipline)

- **hub wait governance (F2)**: while a sub-agent runs, **each iteration** of the hub wait loop first checks `test -f <key artifact>` — the moment the artifact is ready, break and move downstream; **do not wait the full 300s before checking**. The wait target must be **an artifact written by the sub-agent** (Step 2: `01_ontology/ontology.json`; Step 3: `02_processed/feature_summary.json` or `03_figures/plot_manifest.json` — `data_analysis_conclusion.json` is written by the main-agent finalize and must not be used as a wait target).
- **dispatch latency budget (F2b)**: checkpoint passed → dispatch the next agent immediately in the same turn; never idle a full wait cycle after an artifact is ready. Measured orchestration idle totaled ~65 min in run 202609300452274 — budget <30 s per dispatch gap.
- **parallel dispatch (F2c)**: Step 5a (judge) + Step 5b (pre-audit) go out as **two Agent calls in one message**; so do Step 2 + Step 2P. Serial dispatch of known-parallel steps is a discipline violation.
- **SKILL.md single-read (F3.1)**: read the full SKILL.md text only once, on first access; read the corresponding reference file for subsequent protocol details; re-reading the full text is forbidden (the claude engine already injects the first 8K chars into the system prompt, so a second read is pure waste).
- **Directory probing discipline (F3.2)**: use `ls <dir>` single-level for directory probing; `ls -R` / recursive glob across the whole tree is forbidden (any probing command taking >2s counts as waste).
- **todo discipline (F3.3)**: at most 1 todo operation per phase (merge sub-item completions into that phase's done update); updating the todo separately for each completed sub-item is forbidden.

## Core Principle

Diagnosis = exclusion, not confirmation. Every conclusion requires four conditions: temporal precedence + statistical significance + physical mechanism + no contradiction.

The four pillars (Scenario-Adaptive / RAG Deep Understanding / Data↔Ontology Bidirectional / Physics-Based) and the standing rule tables (Core Principle, Counterfactual exclusion constraints, Path Stability) are in `references/orchestration-steps.md`.

## Data Truth Mandate

**Every number written into JSON/reports must be recomputable from the raw data.**

| Rule | Requirement |
|------|------|
| Numeric traceability | Every number must be annotated with data source (cleaned/raw), row range, and computation method |
| Derived value marking | Inferred/derived values must be explicitly marked `"derived": true` or `"inferred": true` |
| Cleaning audit trail | cleaning_integrity records all cleaning operations |
| Visualization traceability | Every data point in every plot must be traceable to specific dataset rows |
| Unavailable marking | Values that cannot be computed from data → write NOT_APPLICABLE + reason |

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

## Mandatory Reading Map (full protocol detail in references/)

- Before Step 0 / Step 0.5 read `references/orchestration-steps.md` §Step 0 … §Step 0.5 (setup, shell convention, RAG pre-check, E-1&&E-1H chain semantics) and `references/run-modes-and-efficiency.md`.
- Before Step 2 / 2-F / 2P / 3 / 4 / 5a / 5b read the matching section of `references/orchestration-steps.md`; before any `Agent(...)` dispatch read `references/dispatch-prompts.md`.
- Before any repair round read `references/repair-loop-and-gates.md`.
- Before Step 6 → Step 10 (reporter, final audit, HTML, experience distill §Step 9.5, enhancement) read `references/orchestration-steps.md` §Step 6 … §Step 10.
- Standing rules (Core Principle pillars, Counterfactual exclusion constraints, Path Stability, Step Turn Budgets, Verification, Failure Recovery) live in `references/orchestration-steps.md`.