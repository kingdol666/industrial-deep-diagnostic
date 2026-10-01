---
name: industrial-doe-analyzer
description: "Standalone industrial/experiment data analysis engine (NOT part of the 9-stage diagnosis pipeline). Dual mode: (a) designed-experiment analysis — DOE design auto-detection (full/fractional factorial with generator recovery and alias-chain disclosure, RSM CCD/BBD, orthogonal array, Latin hypercube), effect/deviation coding, extra-SS ANOVA, BH-FDR, response surface with stationary-point/Hessian classification, Derringer-Suich desirability, operating windows; (b) observational production-condition analysis — core_stats-caliber validated correlations with the full anti-spurious suite (lag-compensated CCF, detrending, Simpson stratification, leave-one-out), leave-one-factor contribution decomposition, Cp/Cpk or Pp/Ppk capability, steady-state windows, drift flags. ALL statistics are computed by deterministic numpy/scipy scripts (zero-LLM); the agent only interprets. Outputs up to 9 schema-validated artifacts (7 per run, mode-dependent), the key one being conclusions/recommendations.json — a machine-readable contract (operating windows with CI, conflicts resolution, confirmations, applicability domain, invalidation conditions) for downstream process-tuning / optimization-control agents. High-throughput: multi-response × multi-factor batch analysis with per-family BH-FDR and effect-size gates. Trigger: DOE, design of experiments, trial data analysis, factorial design, response surface, ANOVA, factor effect, main effect, interaction, desirability, operating window, 工况分析, 试验数据分析, 因子效应, 响应面, 参数相关性, 操作窗口, 高通量数据分析, 工艺优化参考, process tuning reference. Do NOT use for fault root-cause diagnosis (use industrial-diagnostician pipeline), as Step 3 inside the diagnosis pipeline (use industrial-data-processor), or for full 9-stage pipeline orchestration (use industrial-analysis-auto)."
---

# Industrial DOE Analyzer

Standalone high-throughput data analysis engine for **DOE designed experiments** and **production condition (工况) records**. Discipline inherited from the diagnosis pipeline: **deterministic scripts compute every number, the agent only interprets, a deterministic gate blocks bad outputs.** Observational-mode conclusions are correlation-grade (evidence ≤ B) and are hard-gated to `confirmation_needed: true` — correlation must never be executed as causation by a downstream agent.

## Mode Dispatch (Phase 1, automatic)

| Signal | Mode | Statistics path |
|--------|------|-----------------|
| Discrete levels, balanced/orthogonal, generator recovery succeeds | `designed` | effect coding → extra-SS ANOVA → (RSM if curvature) → desirability → windows W1-W5 |
| Axial + center points | `designed` (rsm_ccd) | quadratic model → stationary point → desirability |
| Continuous drifting records, no balance structure | `observational` | anti-spurious correlations → contribution decomposition → steady segments → windows W6-W8 |

User may override via `analysis_context.json` (`mode_override`) — **override changes the mode, never the evidence grade** (grade is checklist-computed; overrides are recorded `overridden_by: "user"`).

## Inputs / Outputs

### Inputs (in `RUN_DIR`)

| File | Description |
|------|-------------|
| `00_input/<data file>` | CSV/Excel/Parquet/Feather/JSON/TSV data table |
| `00_input/analysis_context.json` | *(optional, schema-validated)* objective, responses with spec limits/goals, factors, blocks, covariates, time/group/run-order columns, constraints. If absent, Phase 0 auto-infers it with `assigned_by: "auto"` on every inferred field |

### Outputs (9 schemas cover both modes; a single run produces 7 per mode — designed has no correlation/stability, observational has no effect_table/model; gate = `scripts/quality_gate.mjs`)

| File | Gate |
|------|:----:|
| `run_manifest.json` | created by Phase 0 (required by append-pipeline-event.mjs) |
| `01_profile/data_profile.json` | columns/roles/design detection (resolution + alias chains)/quality/caveats |
| `02_analysis/effect_table.json` | designed: effects, extra-SS ANOVA, η², BH q, Pareto rank, MDE |
| `02_analysis/model.json` | designed: coded coefficients, R²/adj-R²/Q², lack-of-fit, saturation/pooling disclosure |
| `02_analysis/correlation_report.json` | observational: validated pairs (r, lag, anti-spurious verdicts, ΔR² contribution) |
| `02_analysis/stability_report.json` | capability (honest Cp/Cpk vs Pp/Ppk labels), steady segments, change points, drift flags |
| `03_figures/plot_manifest.json` | per-figure ink-gate results |
| `conclusions/doe_conclusion.json` | master conclusion, evidence grade A/A−/B, limitations, `authored_by` |
| `conclusions/recommendations.json` | **downstream contract v1.0** — operating windows, conflicts resolution, confirmations, applicability domain, invalidation conditions |
| `report.html` | G7: interactive analysis report deterministically rendered by `analyze.py report` from the run's artifact JSONs (agent never hand-edits it) |

## Pipeline Event Logging

**MANDATORY** when dispatched as an agent (headless script runs write `run_manifest.json` only).
Timing: run the first `analyze.py profile` BEFORE logging `agent_start` — profile creates
`run_manifest.json`, and append-pipeline-event.mjs exits 1 without it:

```bash
node "$SHARED_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" \
  --event agent_start --agent doe-analyst --step doe_analysis
node "$SHARED_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" \
  --event agent_complete --agent doe-analyst --step doe_analysis \
  --files conclusions/doe_conclusion.json,conclusions/recommendations.json
```

## Dispatch

Launch the `doe-analyst` subagent:

```javascript
Agent({
  agent: "doe-analyst",
  task: `RUN_DIR=<run-dir-path>
SKILL_PATH=<path-to-.claude/skills/industrial-doe-analyzer>
SHARED_PATH=<path-to-.claude/shared>

Read "$SKILL_PATH/references/agent-protocol.md" and execute Phase 0-6.

Key constraints:
- Phase 2 statistics are 100% deterministic scripts — never hand-compute or override numbers
- If analysis_context.json is missing, infer it, mark every inferred field assigned_by:"auto"
- conclusions authored in Phase 3-4 are ENRICHMENTS of the script-generated baseline
  (flip authored_by "script"→"agent" only; never change computed numbers)
- Phase 5 gate (quality_gate.mjs) must pass before reporting done; fix loop max 3
- Phase 6: run `analyze.py report` to render report.html — the HTML is script-generated; never hand-edit it
- Observational windows keep confirmation_needed:true — never flip it off
- Output report.md in Chinese; keep JSON enums in English
`,
  effort: "hi"
})
```

## Downstream Contract (why this skill exists)

`conclusions/recommendations.json` is written for **another agent** doing process tuning / optimization control. It contains: operating windows with units + expected effect + CI95 + confidence enum + FDR q + sample size; the current baseline working point and move instructions; window-conflict resolution; confirmation-experiment designs (when conclusions are observational, aliased, or saturated); an applicability domain (observed factor ranges, n, time span) and invalidation conditions. `contract_version` is `"1.0"`. Honest disclosure: contract v1.0 currently has no implemented consumer agent in this repository — it is a forward contract; downstream usage rules are embedded in the file itself.

## Verification

```bash
SKILL_PATH="<path-to-.claude/skills/industrial-doe-analyzer>"
SHARED_PATH="<path-to-.claude/shared>"

# G1-G7: per-mode artifacts schema-valid + strict key check + report.html gate
node "$SKILL_PATH/scripts/quality_gate.mjs" "$RUN_DIR" \
  --skill-path "$SKILL_PATH" --shared-path "$SHARED_PATH"
```

## Failure Recovery

| Scenario | Recovery |
|----------|----------|
| Unreadable data file | Refuse to run; report which formats were tried |
| No numeric columns / all zero-variance | Abort with `zero_variance` report; request usable data |
| Mode ambiguous (half-designed data) | Choose `observational` (conservative) via `mode_override` (Phase 1) + re-run profile; record caveat |
| RSM requested but model linear-only | W4 downgrade: directional advice + generated confirmation design |
| Regime detector finds no steady rows | Windows from best contiguous segments + `confirmation_needed:true`; caveat |
| Gate FAIL | Fix the flagged artifact (script-side rerun, not hand-edit), max 3 rounds |
| validate.mjs unavailable | G6 FAILS by design (no degraded path); report the environment blocker (validator missing at `<shared>/scripts/validate.mjs`) to the main agent — it does not consume fix rounds |
| industrial-data-processor stats package missing | Observational mode is unavailable (`analyze.py` hard-depends on its `core_stats`/`anti_spurious`/`production_regime_detector`); designed mode is unaffected |
