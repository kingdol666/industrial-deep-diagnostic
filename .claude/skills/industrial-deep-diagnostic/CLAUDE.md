# CLAUDE.md — Industrial Deep Diagnostic Skill

## Project Overview

Claude Code Skill for evidence-first industrial time-series analysis and root cause diagnostic.
Lives in `.claude/skills/industrial-deep-diagnostic/`.

## Architecture Notes

- **Orchestration**: `SKILL.md` defines the workflow. Main agent only orchestrates — never holds domain context.
- **Agent prompts**: `agents/*.md` — each defines one sub-agent's instructions and output contract.
- **Agent decoupling**: Agents communicate exclusively through workspace files (see SKILL.md for the file chain).
- **Script philosophy**: Node.js for fixed operations (zero-dep, always works). Python as adaptive toolkit (agent selects primitives by data dimension).
- **Statistical validation layer** (v4.2): `stats.mjs` + `stats_validate.mjs` run BEFORE diagnosis to detect sorting artifacts, Simpson's Paradox, trend confounding, and outlier-driven correlations.

## File Organization

```
SKILL.md              — Skill definition, workflow, commands (authoritative source)
CLAUDE.md             — This file: developer notes, conventions, gotchas
agents/               — Sub-agent prompt files (context-builder, data-processor, diagnostician, judge, reporter, report-reviewer)
scripts/              — Node.js utils (inspect.mjs, stats.mjs, stats_validate.mjs, setup.mjs, convert.mjs) + Python toolkit (template_visualize.py, template_preprocess.py, file_inspect.py)
resources/            — Reference docs loaded by agents (evidence_rules, diagnosis_method, process_knowledge_base, script_and_toolkit_reference)
schemas/              — JSON Schema draft-07 for ontology, signals, analysis, run_config, report
templates/            — Output templates (report, diagnosis, judge, input_manifest, run_summary)
tests/                — Checklists (per-agent QA) + fixtures (sample CSV, config)
examples/             — Domain-specific sample ontologies (reactor, BOPET film, heat exchanger)
```

## Key Conventions

- **Evidence hierarchy**: 7 ranks (1=direct data → 7=hypothesis). Every conclusion cites its rank.
- **Anti-speculation**: 4 criteria required for causation (temporal precedence, statistical evidence, physical mechanism, no contradictions). Missing any → [HYPOTHESIS].
- **Statistical validation** (v4.2): `stats_validate.mjs` runs BEFORE diagnosis. Diagnostician MUST read `validate_report.json` before forming hypotheses.
- **Sorting validation**: `stats.mjs` automatically detects if data is time-sorted. If NOT, lag correlations are invalid and confidence ceilings apply.
- **Judge quality gate**: Score >= 90 required before report generation. Max 3 repair iterations. Score ceiling of 85 when lag correlations used on unsorted data.
- **Workspace persistence**: All outputs go to `./workspace/diagnostic-runs/<timestamp>_<name>/`.
- **Numbered subdirectories**: All agent outputs use numbered prefixes (`00_input/`, `01_ontology/`, `02_processed/`, `03_figures/`, `04_diagnostics/`, `05_review/`, `06_scripts/`).

## Statistical Scripts (v4.2)

### stats.mjs — Enhanced Statistical Engine
- **Pearson + Spearman** correlations (Spearman for skew-robust comparison)
- **Detrended correlations** (linear detrending, attenuation percentage)
- **Full lag CCF** (ALL lags, not just best — enables lag window consistency check)
- **Stratified correlations** (per group, Simpson's Paradox detection)
- **Sorting validation** (checks if data is sorted by time column)
- **Multiple testing** (Bonferroni correction, expected false positives)
- Usage: `node stats.mjs <data.json> --time-col T --target-cols A,B --group-col G --max-lag 20 --alpha 0.05`

### stats_validate.mjs — Statistical Validation Engine
- **Simpson's Paradox deep detection** (subgroup direction reversal)
- **Time-trend confounding** (detrended vs raw r comparison)
- **Outlier sensitivity** (IQR-based removal + recalculation)
- **Distribution analysis** (skewness, Pearson vs Spearman recommendation)
- **Confounder partial correlation** (controls for suspected confounders)
- **Pearson-Spearman divergence detection**
- Usage: `node stats_validate.mjs <feature_summary.json> <data.json> --group-col G --time-col T`

### Validation Report Pipeline Contract
1. `stats.mjs` → `feature_summary.json` (raw statistics)
2. `stats_validate.mjs` → `validate_report.json` (validation findings)
3. Diagnostician reads BOTH before forming hypotheses
4. Judge cross-references diagnosis against validate_report.json
5. Reporter includes Section 13: Statistical Validation in report

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
- **Agent output paths**: Each agent uses numbered subdirectories under `RUN_DIR/`.
- **Python execution**: Always try `python3` first, fall back to `python3.11`. If matplotlib missing: `pip3 install -r scripts/requirements.txt`.
- **time_col detection**: `inspect.mjs` auto-detects time columns by keyword + type inference. Can fail on non-standard column names — verify and override.
- **stats.mjs requires JSON input**: Use `convert.mjs` to safely convert CSV to JSON.
- **Excel/Parquet/Feather**: `inspect.mjs` auto-routes to `file_inspect.py`.
- **Worktree isolation**: If the skill runs in a worktree, all paths must be absolute.
- **Script & toolkit details**: Moved to `resources/script_and_toolkit_reference.md`.
- **CRITICAL — Sorting**: If data is NOT time-sorted (sorted by batch_id or product), ALL lag correlation results are invalid. This is the #1 fatal error in industrial diagnostics. `stats.mjs` now automatically validates this.
- **Simpson's Paradox**: Always check if correlations hold within product/grade subgroups. The aggregate correlation may be driven by between-group differences, not within-group physics.
