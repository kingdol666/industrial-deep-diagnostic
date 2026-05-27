# CLAUDE.md — Industrial Deep Diagnostic Skill

## Project Overview

Claude Code Skill for evidence-first industrial time-series analysis and root cause diagnostic.
Lives in `.claude/skills/industrial-deep-diagnostic/`.

## Architecture Notes

- **Orchestration**: `SKILL.md` defines the workflow. Main agent only orchestrates — never holds domain context.
- **Agent prompts**: `agents/*.md` — each defines one sub-agent's instructions and output contract.
- **Agent decoupling**: Agents communicate exclusively through workspace files (see SKILL.md for the file chain).
- **Script philosophy**: Node.js for fixed operations (zero-dep, always works). Python as adaptive toolkit (agent selects primitives by data dimension).
- **Statistical validation layer** (v4.3): `stats.mjs` + `stats_validate.mjs` run BEFORE diagnosis. New in v4.3: mutual information, Granger causality, interaction effects, change point detection.
- **Clarification gate** (v4.3): Context Builder uses AskUserQuestion when parameter physical meanings are unknown. Step 2.5 in the pipeline.
- **Dual-Drive Architecture** (v5.0): Diagnosis is split into three agents — Statistical Engine (pure data patterns, blind to physics), Physical Engine (pure physics, blind to statistics), and Fusion Diagnostician (cross-validates both). Two independent engines using completely different methodologies reach independent conclusions, then cross-validate. Where they agree → high confidence. Where they disagree → diagnostic signal.
- **Information firewall** (v5.0): Statistical Engine reads feature_summary.json + validate_report.json, NEVER ontology.json. Physical Engine reads ontology.json + cleaned_data.json, NEVER feature_summary.json. Strict separation enforced by agent prompts and input file segregation.

## File Organization

```
SKILL.md              — Skill definition, workflow, commands (authoritative entry point)
CLAUDE.md             — This file: developer notes, conventions, gotchas
pipeline-execution.md — Detailed per-step pipeline protocol (extracted from SKILL.md for maintainability)
agents/               — Sub-agent prompt files (context-builder, data-processor, statistical-engine, physical-engine, fusion-diagnostician, judge, reporter, report-reviewer)
scripts/              — Node.js utils (inspect.mjs, stats.mjs, stats_validate.mjs, setup.mjs,
                        convert.mjs, validate.mjs, artifact-check.mjs)
                        + Python toolkit (template_visualize.py, template_preprocess.py, file_inspect.py)
resources/            — Reference docs loaded by agents (evidence_rules, diagnosis_method, process_knowledge_base, script_and_toolkit_reference)
schemas/              — JSON Schema draft-07 for ontology, signals, analysis, diagnosis, evidence, confidence, report, statistical_findings, physical_findings, fusion_cross_validation
templates/            — Output templates (report, diagnosis, judge, input_manifest, run_summary)
tests/                — Checklists (per-agent QA) + fixtures (sample CSV, config)
examples/             — Domain-specific sample ontologies (reactor, BOPET film, heat exchanger)
```

## Key Conventions

- **Evidence hierarchy**: 7 ranks (1=direct data → 7=hypothesis). Every conclusion cites its rank.
- **Anti-speculation**: 4 criteria required for causation (temporal precedence, statistical evidence, physical mechanism, no contradictions). Missing any → [HYPOTHESIS].
- **Dual-blind validation** (v5.0): Statistical Engine and Physical Engine run independently with strict information separation. Neither engine sees the other's input data. Fusion Diagnostician cross-validates both outputs.
- **Physics wins conflicts** (v5.0): When a statistical correlation contradicts a definitive physical exclusion (quantitative Arrhenius, energy balance, conservation law), physics wins. Physical laws are universal and don't depend on sample size.
- **Statistical validation** (v4.2): `stats_validate.mjs` runs BEFORE diagnosis. Fusion Diagnostician MUST read `validate_report.json` before forming hypotheses.
- **Sorting validation**: `stats.mjs` automatically detects if data is time-sorted. If NOT, lag correlations are invalid and confidence ceilings apply.
- **Judge quality gate**: Score >= 90 required before report generation. Max 3 repair iterations. Score ceiling of 85 when lag correlations used on unsorted data.
- **Workspace persistence**: All outputs go to `./workspace/diagnostic-runs/<timestamp>_<name>/`.
- **Numbered subdirectories**: All agent outputs use numbered prefixes (`00_input/`, `01_ontology/`, `02_processed/`, `03_figures/`, `04_diagnostics/`, `05_review/`, `06_scripts/`).
- **Cross-validation confidence** (v5.0): fusion_confidence = min(stat_confidence, phys_confidence) + cross_validation_bonus - uncertainty_penalty. Both engines must agree for high confidence.

## Statistical Scripts (v4.3)

### stats.mjs — Enhanced Statistical Engine
- **Pearson + Spearman** correlations (Spearman for skew-robust comparison)
- **Detrended correlations** (linear detrending, attenuation percentage)
- **Full lag CCF** (ALL lags, not just best — enables lag window consistency check)
- **Stratified correlations** (per group, Simpson's Paradox detection)
- **Sorting validation** (checks if data is sorted by time column)
- **Multiple testing** (Bonferroni correction, expected false positives)
- **Mutual Information** (NEW v4.3 — k-NN estimator for non-linear dependency)
- **Granger Causality** (NEW v4.3 — F-test on VAR models for temporal causality)
- **Interaction Effects** (NEW v4.3 — synergistic parameter pair detection)
- Usage: `node stats.mjs <data.json> --time-col T --target-cols A,B --group-col G --max-lag 20 --alpha 0.05`

### stats_validate.mjs — Statistical Validation Engine
- **Simpson's Paradox deep detection** (subgroup direction reversal)
- **Time-trend confounding** (detrended vs raw r comparison)
- **Outlier sensitivity** (IQR-based removal + recalculation)
- **Distribution analysis** (skewness, Pearson vs Spearman recommendation)
- **Confounder partial correlation** (controls for suspected confounders)
- **Pearson-Spearman divergence detection**
- **Change Point Detection** (NEW v4.3 — PELT algorithm for regime shift identification)
- Usage: `node stats_validate.mjs <feature_summary.json> <data.json> --group-col G --time-col T`

### Validation Report Pipeline Contract (v5.0)
1. `stats.mjs` → `feature_summary.json` (raw statistics + MI, Granger, interactions)
2. `stats_validate.mjs` → `validate_report.json` (validation findings + change points)
3. Context Builder outputs `clarification_needed.json` for unknown parameters
4. Main agent runs clarification gate (Step 2.5) before proceeding
5. **Statistical Engine** reads feature_summary.json + validate_report.json → `statistical_findings.json` (pure patterns)
6. **Physical Engine** reads ontology.json + cleaned_data.json → `physical_findings.json` (pure physics)
7. **Fusion Diagnostician** reads BOTH engine outputs → cross-validates → `diagnosis.json` + `fusion_cross_validation.json`
8. Judge cross-references diagnosis against validate_report.json + cross-validation matrix
9. Reporter includes Section 13 (Statistical Validation) + Section 14 (Dual-Engine Cross-Validation)
10. Report Reviewer checks physical mechanisms + cross-validation quality + parameter meaning confidence

## Visualization Toolkit (`scripts/template_visualize.py`)

- NOT a fixed script. A library of ~21 composable primitives covering 5 data dimension patterns.
- **v4.2 additions**: 5 new statistical validation primitives:
  - `plot_ccf_lag_window` — Full CCF with isolated spike detection
  - `plot_stratified_correlation` — Subgroup comparison (Simpson's Paradox visual)
  - `plot_detrended_comparison` — Raw vs detrended bar chart
  - `plot_spearman_vs_pearson` — Robustness scatter
  - `plot_outlier_sensitivity` — Full vs cleaned correlation comparison
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
- **Script & toolkit details**: Moved to `resources/script_and_toolkit_reference.md`.
- **CRITICAL — Sorting**: If data is NOT time-sorted (sorted by batch_id or product), ALL lag correlation results are invalid. This is the #1 fatal error in industrial diagnostics. `stats.mjs` now automatically validates this.
- **Simpson's Paradox**: Always check if correlations hold within product/grade subgroups. The aggregate correlation may be driven by between-group differences, not within-group physics.
- **Parameter physical meaning** (v4.3): Unknown parameter meanings → clarification gate (Step 2.5). Never silently guess. Use [PARAM_AMBIGUITY] marker when unresolved.
- **Granger causality** requires time-sorted data. Results are invalid if sorting validation failed.
- **Change points**: Correlations computed across regime boundaries may be spurious. Check before drawing conclusions.
- **Interaction effects**: Weak individual correlations + strong interaction = synergistic failure mode. Don't dismiss parameters just because |r| is low.
- **CRITICAL — Information firewall** (v5.0): Statistical Engine MUST NOT read ontology.json or process_knowledge_base.md. Physical Engine MUST NOT read feature_summary.json or validate_report.json. Breaking this firewall invalidates the cross-validation — two engines with the same information aren't independent.
- **Fusion Diagnostician is an arbiter, not an analyst** (v5.0): It cross-validates the two engines' outputs. It does NOT redo statistics or redo physics. If an engine's output is incomplete, re-spawn that engine — don't have the Fusion Diagnostician fill gaps.
- **Physical exclusions need quantitative justification** (v5.0): "Temperature is too low for degradation" is not an exclusion. "Arrhenius calculation: k(84°C)/k(280°C) ≈ 10^-15, meaning degradation rate is effectively zero at MD temperatures" IS an exclusion.

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
