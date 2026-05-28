# CLAUDE.md — Industrial Deep Diagnostic Skill

## Project Overview

Claude Code Skill for evidence-first industrial time-series analysis and root cause diagnostic.
Lives in `.claude/skills/industrial-deep-diagnostic/`.

## Language Default

**默认中文输出。** 所有报告、诊断结论、审计文档使用中文。Schema enum字段保持英文。

## Architecture Notes

- **Orchestration**: `SKILL.md` defines the workflow. Main agent only orchestrates — never holds domain context.
- **Agent prompts**: `agents/*.md` — each defines one sub-agent's instructions and output contract.
- **Agent decoupling**: Agents communicate exclusively through workspace files (see SKILL.md for the file chain).
- **Script philosophy**: Node.js for fixed operations (zero-dep, always works). Python as adaptive toolkit (agent selects primitives by data dimension).
- **Statistical validation layer**: `stats.mjs` + `stats_validate.mjs` run BEFORE diagnosis. Diagnostician MUST read `validate_report.json` before forming hypotheses.
- **Clarification gate** (v4.3): Context Builder uses AskUserQuestion when parameter physical meanings are unknown. Pipeline Step 2.5.
- **Competing Hypotheses Protocol** (v6.0): Single Diagnostician follows a structured 5-step protocol (Steps A-E, within the agent's Phase 4). The Diagnostician agent uses its own internal numbering (Phase 0-7), distinct from pipeline Steps (0-8).
- **Numbering disambiguation** (v6.0+): Four separate numbering systems — Pipeline Steps (0-8), Diagnostician Phases (0-7), Reasoning Chain Segments (R1-R8), Method Stages (1-6 in diagnosis_method.md). See `pipeline-execution.md` §Numbering Systems.
- **Data Discriminability Assessment** (v6.0): The key innovation. Before assigning confidence to any hypothesis, the Diagnostician checks whether available data CAN distinguish between competing hypotheses. When multiple hypotheses predict identical observables → output as COMPETING_SET, not a guess.
- **Repair loop global cap** (v6.0+): Total re-diagnosis iterations across Judge + Reviewer repair loops capped at 5. See `pipeline-execution.md` §Repair Loop Protocol.

## File Organization

```
SKILL.md              — Skill definition, workflow, commands (authoritative entry point)
CLAUDE.md             — This file: developer notes, conventions, gotchas
pipeline-execution.md — Detailed per-step pipeline protocol (extracted from SKILL.md for maintainability)
agents/               — Sub-agent prompt files (context-builder, data-processor, diagnostician, judge, reporter, report-reviewer)
scripts/              — Node.js utils (inspect.mjs, stats.mjs, stats_validate.mjs, setup.mjs,
                        convert.mjs, validate.mjs, artifact-check.mjs)
                        + Python toolkit (template_visualize.py, template_preprocess.py, file_inspect.py)
resources/            — Reference docs loaded by agents (evidence_rules, diagnosis_method, process_knowledge_base, script_and_toolkit_reference)
schemas/              — JSON Schema draft-07 for ontology, signals, analysis, diagnosis, evidence, confidence, report, reasoning_chain
templates/            — Output templates (report, diagnosis, judge, input_manifest, run_summary)
tests/                — Checklists (per-agent QA) + fixtures (sample CSV, config)
examples/             — Domain-specific sample ontologies (reactor, BOPET film, heat exchanger)
```

## Key Conventions

- **Evidence hierarchy**: 7 ranks (1=direct data → 7=hypothesis). Every conclusion cites its rank.
- **Anti-speculation**: 4 criteria required for causation (temporal precedence, statistical evidence, physical mechanism, no contradictions). Missing any → [HYPOTHESIS].
- **Competing hypotheses protocol** (v6.0): 5-step structured reasoning within a single Diagnostician agent. Step C (Data Discriminability) is the critical new step that prevents the #1 failure mode — confidently picking the wrong root cause when alternatives predict identical observables.
- **Three output categories** (v6.0): DETERMINED (single survivor), COMPETING_SET (multiple indistinguishable, with discrimination conditions), NEEDS_DATA (insufficient evidence).
- **Statistical validation**: `stats_validate.mjs` runs BEFORE diagnosis. Diagnostician MUST read `validate_report.json` before forming hypotheses.
- **Sorting validation**: `stats.mjs` automatically detects if data is time-sorted. If NOT, lag correlations are invalid and confidence ceilings apply.
- **Judge quality gate**: Score >= 90 required before report generation. Max 3 repair iterations. Score ceiling of 85 when lag correlations used on unsorted data.
- **Workspace persistence**: All outputs go to `workspace/diagnostic-runs/<timestamp>_<name>/` (relative to project root, sibling of `.claude/`). Compute project root from SKILL_PATH: `SKILL_PATH/../../..`.
- **Numbered subdirectories**: All agent outputs use numbered prefixes (`00_input/`, `01_ontology/`, `02_processed/`, `03_figures/`, `04_diagnostics/`, `05_review/`, `06_scripts/`).

## Statistical Scripts

### stats.mjs — Enhanced Statistical Engine
- **Pearson + Spearman** correlations (Spearman for skew-robust comparison)
- **Detrended correlations** (linear detrending, attenuation percentage)
- **Full lag CCF** (ALL lags, not just best — enables lag window consistency check)
- **Stratified correlations** (per group, Simpson's Paradox detection)
- **Sorting validation** (checks if data is sorted by time column)
- **Multiple testing** (Bonferroni correction, expected false positives)
- **Mutual Information** (k-NN estimator for non-linear dependency)
- **Granger Causality** (F-test on VAR models for temporal causality)
- **Interaction Effects** (synergistic parameter pair detection)
- Usage: `node stats.mjs <data.json> --time-col T --target-cols A,B --group-col G --max-lag 20 --alpha 0.05`

### stats_validate.mjs — Statistical Validation Engine
- **Simpson's Paradox deep detection** (subgroup direction reversal)
- **Time-trend confounding** (detrended vs raw r comparison)
- **Outlier sensitivity** (IQR-based removal + recalculation)
- **Distribution analysis** (skewness, Pearson vs Spearman recommendation)
- **Confounder partial correlation** (controls for suspected confounders)
- **Pearson-Spearman divergence detection**
- **Change Point Detection** (PELT algorithm for regime shift identification)
- Usage: `node stats_validate.mjs <feature_summary.json> <data.json> --group-col G --time-col T`

### Pipeline Contract (v6.0)
1. `stats.mjs` → `feature_summary.json` (raw statistics + MI, Granger, interactions)
2. `stats_validate.mjs` → `validate_report.json` (validation findings + change points)
3. Context Builder outputs `clarification_needed.json` for unknown parameters
4. Main agent runs clarification gate (Step 2.5) before proceeding
5. **Diagnostician** reads ALL inputs → 5-step protocol → `diagnosis.json` + `reasoning_chain.json`
6. Judge cross-references diagnosis against validate_report.json + discriminability matrix
7. Reporter includes statistical validation section + competing hypotheses disclosure
8. Report Reviewer checks physical mechanisms + discriminability quality + parameter meaning confidence

## Visualization Toolkit (`scripts/template_visualize.py`)

- NOT a fixed script. A library of composable primitives covering 5 data dimension patterns.
- Agent calls `detect_data_pattern()` to classify data, then selects primitives by pattern.
- Each primitive returns generation metadata → feeds `plot_manifest.json`.
- Dependencies: matplotlib, pandas, numpy only (NO scipy — STFT is numpy-only implementation).

## Gotchas

- **CLAUDE.md vs SKILL.md**: SKILL.md is authoritative. This file is developer reference only. If they conflict, trust SKILL.md.
- **Pipeline reference**: `pipeline-execution.md` contains the detailed step protocol, artifact chain, and validation framework. SKILL.md delegates to it.
- **Agent output paths**: Each agent uses numbered subdirectories under `RUN_DIR/`.
- **Python execution**: Always try `python3` first, fall back to `python3.11`. If matplotlib missing: `pip3 install -r scripts/requirements.txt`.
- **time_col detection**: `inspect.mjs` auto-detects time columns by keyword + type inference. Can fail on non-standard column names — verify and override.
- **stats.mjs requires JSON input**: Use `convert.mjs` to safely convert CSV to JSON.
- **Excel/Parquet/Feather**: `inspect.mjs` auto-routes to `file_inspect.py`.
- **Worktree isolation**: If the skill runs in a worktree, all paths must be absolute.
- **CRITICAL — Sorting**: If data is NOT time-sorted (sorted by batch_id or product), ALL lag correlation results are invalid. This is the #1 fatal error in industrial diagnostics. `stats.mjs` now automatically validates this.
- **Simpson's Paradox**: Always check if correlations hold within product/grade subgroups. The aggregate correlation may be driven by between-group differences, not within-group physics.
- **Parameter physical meaning**: Unknown parameter meanings → clarification gate (Step 2.5). Never silently guess. Use [PARAM_AMBIGUITY] marker when unresolved.
- **Granger causality** requires time-sorted data. Results are invalid if sorting validation failed.
- **Change points**: Correlations computed across regime boundaries may be spurious. Diagnostician Phase 0.5 mandates per-segment re-verification of core correlations when change points are detected. If a correlation is REGIME_SPURIOUS (collapses in ≥80% of segments), it is excluded from hypothesis generation.
- **Image captions fallback**: `image_captions.json` is generated alongside `plot_manifest.json` by the Data Processor. The Reporter uses it as fallback when PNG rendering is unavailable — never write "*Image unavailable*" if structured captions exist.
- **Repair counter persistence**: The global `diag_iters` counter is tracked in `.pipeline_events.jsonl` via `repair_spawn` events. At the start of any repair loop, count existing `repair_spawn` entries to restore the current counter — do not rely on in-memory state that may be lost during context compaction.
- **Interaction effects**: Weak individual correlations + strong interaction = synergistic failure mode. Don't dismiss parameters just because |r| is low.
- **CRITICAL — Data Discriminability** (v6.0): The #1 failure mode is confidently diagnosing H1 when H2 predicts identical observables. Step C of the Diagnostician protocol MUST check whether available data can distinguish between competing hypotheses. When indistinguishable → COMPETING_SET with discrimination conditions, NOT a guess.
- **Confidence ceiling** (v6.0): INDISTINGUISHABLE competing hypotheses capped at 65 confidence, regardless of correlation strength. No single hypothesis can exceed 65 when alternatives predict the same observables.
- **Physical exclusions need quantitative justification**: "Temperature is too low for degradation" is not an exclusion. "Arrhenius calculation: k(84°C)/k(280°C) ≈ 10^-15, meaning degradation rate is effectively zero at MD temperatures" IS an exclusion.
- **CRITICAL — Product-Stratified Analysis** (v6.0+): Diagnostician MUST run Phase 2 (Product-Stratified Analysis) before generating hypotheses when product column exists. BETWEEN-PRODUCT ONLY correlations must be removed — they represent baseline differences, not causal mechanisms. This catches the common confound where "Product A runs hotter AND has more defects" is mistaken for "heat causes defects."
- **Physical Logic Chain** (v6.0+): Every hypothesis must trace a complete physical logic chain (parameter → physical variable → process state → intermediate effect → defect). >50% [INFERRED] links = RESEARCH QUESTION, not diagnosis. Quantitative feasibility checks (Arrhenius, residence time, energy balance) are mandatory before accepting any causal claim.
- **Cross-Product Discriminability** (v6.0+): Product stratification can sometimes break time-colinearity between competing hypotheses. Check if hypotheses behave differently across products — this is an additional discriminability dimension.

## Validation & Integrity Scripts

| Script | Purpose | When to Run |
|--------|---------|-------------|
| `validate.mjs` | JSON Schema run-time validation | After each agent produces JSON output |
| `artifact-check.mjs` | Verify all pipeline artifacts exist | At pipeline completion (Step 8) |

Both are zero-dependency Node.js scripts. `validate.mjs` checks: required fields, types, min/max, enum values, pattern, date-time format. Exits non-zero on error.

## Pipeline Event Log

Each agent writes to `RUN_DIR/.pipeline_events.jsonl` at start and completion. Format:
```jsonl
{"event": "agent_start", "agent": "diagnostician", "timestamp": "2026-05-25T10:00:00Z"}
{"event": "agent_complete", "agent": "diagnostician", "timestamp": "2026-05-25T10:05:00Z", "files_written": ["04_diagnostics/diagnosis.json"], "errors": null}
```
Enables post-pipeline debugging without reading every agent's output files.
