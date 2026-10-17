---
name: industrial-doe-orchestrator
description: "Thin orchestration contract for a designed-experiment (DOE) analysis run — it introduces no new engine and no new statistics: it fixes the ORDER of the ontology-first flow and the hard gates between the stages. Order: (1) doe_ontology_prepare (context_fp → store lookup → reuse/extend/prior-build → ontology.json + ontology_brief.json/.md + ontology_coverage.json), (2) the analysis agent reads the brief and writes 01_profile/analysis_plan.md, (3) industrial-doe-analyzer (profile → statistics → report) with the ontology consistency check, (4) conclusions/next_design for the next round. Use it when a run is an experiment/DOE analysis: run_table + doe_context/analysis_context, factor/response declarations, designed or observational-conditions trial data, design_only (responses not measured yet), operating window / 工艺优化参考 / 下一轮布点 requests. Do NOT use for root-cause diagnosis of a fault (use industrial-analysis-auto / industrial-diagnostician), for pure monitoring or SPC alerting (use industrial-sentinel), for building a tuning-experience base (use industrial-tuning-memory), for a closed-loop optimizer campaign (use industrial-optimizer-loop), or for a single-factor screening with no design context (raw correlation asks belong to industrial-doe-analyzer's observational mode). Trigger: DOE analysis, experiment analysis, designed experiment, ontology-first analysis, design_only analysis, 试验分析流程, 本体优先分析, DOE 编排, 分析顺序, run_table 分析, 下一轮布点流程."
---

# Industrial DOE Orchestrator (thin)

This skill adds **no engine, no script and no statistics of its own**. It fixes the *order* of an ontology-first DOE
analysis and the *gates* between stages:

```
prepare ──► brief ──► analyzer ──► consistency ──► next_design
(ontology)  (agent   (deterministic  (advisory)    (next round
            plan)     statistics)                  design)
```

Everything is executed by existing components:

| Stage | Executor | Owner skill |
|-------|----------|-------------|
| prepare | `doe_ontology_prepare.py` (deterministic) | `industrial-doe-analyzer` scripts / `industrial-ontology-builder` (profile=doe) |
| brief | `doe_ontology_prepare.py` writes it; the **agent reads** it | `industrial-ontology-builder` semantics → `ontology_brief` contract (contracts §7.1) |
| analyzer | `analyze.py` + `quality_gate.mjs` | `industrial-doe-analyzer` |
| consistency | `ontology_consistency.py` (advisory) | `industrial-doe-analyzer` scripts (contracts §7.2) |
| next_design | `doestats/design_next.py` (Phase-3 deliverable) | `industrial-doe-analyzer` |

**Iron rules**

1. Deterministic scripts compute every number; the agent interprets and never hand-edits JSON/HTML.
2. The gate order is not negotiable: **no statistics before the brief + `analysis_plan.md`**.
3. `design_only` (responses not measured yet) runs only prepare/brief/profile/build — never statistics.
4. Consistency findings are **advisory**: they never rewrite an effect, a window or a conclusion.
5. Correlation is never promoted to causation; a design-adjusted association stays a screen.

## Inputs / Outputs

### Inputs (in `RUN_DIR/00_input/`)

| File | Description |
|------|-------------|
| `run_table.csv` | one row = one execution (`run_id` unique; duplicate runs = new `run_id`) |
| `doe_context.json` | platform/user DOE declaration (`col` naming, specs, constraints, `platform_ref`) |
| `analysis_context.json` | the single resolved context (adapter output); authoritative column list |

Missing `analysis_context.json`: run the adapter/analyzer profile first (it writes one with `assigned_by:"auto"`),
then re-run prepare so the brief is built from the resolved context.

### Outputs (all inside `RUN_DIR`)

| Stage | Artifact |
|-------|----------|
| prepare | `01_ontology/ontology.json`, `01_ontology/ontology_brief.json` + `.md`, `01_ontology/ontology_coverage.json` |
| brief | `01_profile/analysis_plan.md` (agent-authored; the only hand-written stage artifact) |
| analyzer | `run_manifest.json`, `01_profile/data_profile.json`, `02_analysis/{effect_table,model,correlation_report,stability_report,association_screen}.json`, `03_figures/plot_manifest.json`, `conclusions/{doe_conclusion,recommendations}.json`, `report.md`, `report.html` |
| consistency | `01_ontology/ontology_feedback.json` (+ `02_analysis/ontology_consistency.json`) |
| next_design | `conclusions/next_design.json`, `conclusions/optimization_guidance.json` |

## Stage 0 — run dir + intent

```bash
# create/reuse the run workspace (main agent only)
node .claude/skills/industrial-analysis-auto/scripts/setup.mjs \
  --name "<scene>" --mode fast --base-dir "$PROJECT_ROOT/workspace/diagnostic-runs"
```

`RUN_DIR` must already contain `00_input/run_table.csv` (+ the two context files). Everything below writes **inside**
`RUN_DIR`; never write to a sibling run.

## Stage 1 — prepare (ontology stage, HARD GATE)

```bash
uv run --project .claude/shared/scripts python \
  .claude/skills/industrial-doe-analyzer/scripts/doe_ontology_prepare.py \
  --run-dir "$RUN_DIR" --mode auto [--data "$RUN_DIR/00_input/run_table.csv"] \
  [--scene "<scene_key>"] [--json]
```

| `action` | Meaning | What the agent does next |
|----------|---------|--------------------------|
| `reused` | exact `profile+scene_key+context_fp` store hit | nothing to build — read the brief (must be ≤60s, `rag_used=false`, `web_used=false`) |
| `extended` | same scene, changed context (columns/ranges/units/specs) | review the brief's new/changed entries and the coverage ledger |
| `built` | no store match (`design_only` → prior-knowledge build) | read the brief; the ontology is a **prior**, behaviour fields are `NOT_APPLICABLE` |
| `skipped` | mode off (dev override only) | do **not** run the DOE analysis; report why |

Checkpoint **CP-1** (must pass before Stage 2):

```bash
test -s "$RUN_DIR/01_ontology/ontology.json" \
  && test -s "$RUN_DIR/01_ontology/ontology_brief.json" \
  && test -s "$RUN_DIR/01_ontology/ontology_brief.md" \
  && test -s "$RUN_DIR/01_ontology/ontology_coverage.json" \
  && node .claude/shared/scripts/validate.mjs \
       .claude/skills/industrial-ontology-builder/schemas/ontology_schema.json \
       "$RUN_DIR/01_ontology/ontology.json"
```

Coverage gate **CP-2**: `ontology_coverage.json` → `coverage.ratio == 1.0` and every `inferred`/`unmatched` entry
carries a non-empty `reason` (0 silent columns, OD-09). An `unmatched` entry must be answered in
`analysis_plan.md` (drop the column or say why it cannot be used) — never silently ignore it.

## Stage 2 — brief → `analysis_plan.md` (Agent understanding, HARD GATE)

1. **Read `01_ontology/ontology_brief.json` and `01_ontology/ontology_brief.md` in full.** They carry scene, factors
   (col/unit/range/expected sign/physical meaning/confidence), responses (col/unit/goal/lsl/usl/target), relationships,
   confounders, limitations, column mapping and coverage.
2. Write `01_profile/analysis_plan.md` **in Chinese** containing at least:

   | Section | Content |
   |---------|---------|
   | 场景理解 | process/product/line, objective, design type, data stage, what the current operating point is |
   | 因子 | each factor: what it physically does, its range/unit, expected direction and confidence |
   | 响应 | each response: goal, spec limits, unit, and the failure mode if it drifts |
   | 混杂与局限 | confounders, uncontrolled variables, design-hull/extrapolation risk, missing units/specs |
   | 分析模式 | designed vs observational, planned statistics, what would falsify the expectation |
   | 未解决项 | every `inferred`/`unmatched` mapping row and how it is handled |

3. Then call the gate (the same function `analyze.py` wires at Phase 0):

```bash
uv run --project .claude/shared/scripts python - <<'PY'
import json, sys
sys.path.insert(0, ".claude/skills/industrial-doe-analyzer/scripts")
from doe_ontology_prepare import enforce_gate
ctx = json.load(open("RUN_DIR/00_input/analysis_context.json", encoding="utf-8"))
enforce_gate("RUN_DIR", ctx, subcommand="profile")   # ONTOLOGY_BRIEF_REQUIRED / ANALYSIS_PLAN_REQUIRED
PY
```

Checkpoint **CP-3**: `analysis_plan.md` exists and is newer than `ontology_brief.json`
(`find "$RUN_DIR/01_profile/analysis_plan.md" -newer "$RUN_DIR/01_ontology/ontology_brief.json"` → non-empty).
Append the pipeline event that proves the order (see below).

## Stage 3 — analyzer (deterministic statistics)

```bash
uv run --project .claude/shared/scripts python \
  .claude/skills/industrial-doe-analyzer/scripts/analyze.py profile \
  --run-dir "$RUN_DIR" --data "$RUN_DIR/00_input/run_table.csv" \
  --context "$RUN_DIR/00_input/analysis_context.json"

uv run --project .claude/shared/scripts python \
  .claude/skills/industrial-doe-analyzer/scripts/analyze.py run --run-dir "$RUN_DIR"

node .claude/skills/industrial-doe-analyzer/scripts/quality_gate.mjs "$RUN_DIR" \
  --skill-path .claude/skills/industrial-doe-analyzer --shared-path .claude/shared

uv run --project .claude/shared/scripts python \
  .claude/skills/industrial-doe-analyzer/scripts/analyze.py report --run-dir "$RUN_DIR"
```

* `design_only` (all response cells empty): **stop after `profile`** — statistics raise
  `DESIGN_ONLY_NO_RESPONSE` (`enforce_gate(..., subcommand="run")`). Record the blocked state and finish.
* The gate must pass (G1–G7 in the current revision); fix flagged artifacts by re-running the script, never by
  editing JSON by hand. Max 3 fix rounds.

## Stage 4 — consistency (advisory)

```bash
uv run --project .claude/shared/scripts python \
  .claude/skills/industrial-doe-analyzer/scripts/ontology_consistency.py \
  --run-dir "$RUN_DIR" --consistency-json
```

* Only `causal`/`physical` relationships with a normalisable expected sign participate; everything else is counted
  in `not_estimable` with a reason.
* `contradictions[]` default to `severity:"advisory"` — they go into the report and the watchlist, and **never**
  change a computed effect/window. A contradiction is a question ("is a confounder at work?"), not a conclusion.
* The report must mention `checked/matched/not_estimable/contradictions` and cite
  `01_ontology/ontology_feedback.json`.

## Stage 5 — next_design

```bash
# Phase-3 deliverable — if design_next.py is absent in this revision, record
# stage_status:"deferred" in report.md and finish; do not invent recommendations.
uv run --project .claude/shared/scripts python \
  .claude/skills/industrial-doe-analyzer/scripts/doestats/design_next.py --run-dir "$RUN_DIR"
```

`conclusions/next_design.json` answers "what do we run next": fold-over (aliased resolution), star augmentation
(linear model, curvature missing), space-filling (observed/extrapolated region), confirm-replicate (non-randomised).
Every proposed setpoint must satisfy the hard constraints.

## Pipeline event logging (order evidence)

```bash
node "$SHARED_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" \
  --event ontology_prepare_complete --agent doe-orchestrator --step doe_ontology_stage \
  --files 01_ontology/ontology.json,01_ontology/ontology_brief.json,01_ontology/ontology_coverage.json
node "$SHARED_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" \
  --event analysis_plan_written --agent doe-orchestrator --step doe_understanding \
  --files 01_profile/analysis_plan.md
node "$SHARED_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" \
  --event doe_analysis_complete --agent doe-analyst --step doe_analysis \
  --files conclusions/doe_conclusion.json,conclusions/recommendations.json
```

The events (with their timestamps) are the sequence proof: brief → plan → statistics.

## Negative triggers (stay out of this flow)

| Ask | Correct route |
|-----|---------------|
| Why did this batch fail / root-cause a fault | `industrial-analysis-auto` (9-stage diagnosis) |
| Watch a line, SPC alerts, drift projection | `industrial-sentinel` |
| Mine past tuning actions / fault signatures | `industrial-tuning-memory` |
| Run a closed-loop parameter campaign | `industrial-optimizer-loop` |
| Score a production line's stability | `industrial-line-stability-report` |
| Only clean/preprocess files | `industrial-data-processor` / `industrial-data-preprocessor` |
| "Is the ontology stage worth it" / skill evaluation | `darwin-skill` |

Do not use this skill to execute a designed experiment, to write to a PLC/recipe, or to convert a correlation into a
causal claim.

## Failure Recovery

| Scenario | Recovery |
|----------|----------|
| Store lookup errors / unreachable | `prepare` falls back to a prior-knowledge build and reports `store.published=false` — continue, do not block |
| `ontology_coverage.ratio < 1.0` | Answer every `inferred`/`unmatched` row in `analysis_plan.md`; if a declared column truly does not exist, say so explicitly |
| `ONTOLOGY_BRIEF_REQUIRED` | The ontology stage never ran: run Stage 1 |
| `ANALYSIS_PLAN_REQUIRED` | The brief was not turned into `analysis_plan.md`: do Stage 2 before any statistics |
| `DESIGN_ONLY_NO_RESPONSE` | Expected — the responses are unmeasured. Finish at the profile stage and report the design-only status |
| Gate FAIL (G1–G7) | Re-run the script stage that owns the artifact; 3 rounds max, then report the failure honestly |
| `design_next.py` missing | Record `stage_status:"deferred"`; do not hand-write next-round designs |
| Agent has no time to read the brief | Not acceptable — the brief is the compact scene+data model; a blind statistics run is a contract violation |
