# CLAUDE.md — Industrial Deep Diagnostic Skill

Developer reference for contributors. For the skill's behavior and workflow, see `SKILL.md`.

## Architecture

- **Orchestration**: `SKILL.md` defines the workflow. The main agent only orchestrates — never holds domain context.
- **Agent decoupling**: Agents communicate exclusively through workspace files (`RUN_DIR/` subdirectories).
- **Script philosophy**: Node.js for fixed operations (zero-dep). Python as adaptive toolkit (agents select primitives by data dimension).
- **Statistical validation layer**: `stats.mjs` + `stats_validate.mjs` run before diagnosis. Includes mutual information, Granger causality, interaction effects, change point detection.
- **Clarification gate** (Step 2.5): Context Builder uses AskUserQuestion when parameter physical meanings are unknown.

## File Organization

```
SKILL.md              — Skill definition, workflow, commands (authoritative entry point)
CLAUDE.md             — This file: developer notes, conventions, gotchas
pipeline-execution.md — Detailed per-step pipeline protocol
agents/               — Sub-agent prompt files (6 agents)
scripts/              — Node.js utils + Python toolkit
resources/            — Reference docs loaded by agents
schemas/              — JSON Schema draft-07 for all pipeline outputs
templates/            — Output templates (report, diagnosis, judge, etc.)
tests/                — Checklists + fixtures (sample CSV, config)
examples/             — Domain-specific sample ontologies (reactor, BOPET, heat exchanger)
```

## Script Reference

### Statistical Engines

**stats.mjs** — Enhanced statistical engine:
```
node stats.mjs <data.json> --time-col T --target-cols A,B --group-col G --max-lag 20 --alpha 0.05
```
Outputs: Pearson + Spearman correlations, detrended correlations, full CCF at all lags, stratified correlations, sorting validation, multiple testing correction, mutual information (k-NN estimator), Granger causality (F-test on VAR models), interaction effects.

**stats_validate.mjs** — Statistical validation engine:
```
node stats_validate.mjs <feature_summary.json> <data.json> --group-col G --time-col T
```
Outputs: Simpson's Paradox detection, time-trend confounding, outlier sensitivity (IQR-based), distribution analysis, confounder partial correlation, Pearson-Spearman divergence, change point detection (PELT algorithm).

### Data Tools

| Script | Purpose |
|--------|---------|
| `inspect.mjs` | Auto-detect columns, types, time column. Routes CSV/JSON natively, Excel/Parquet to `file_inspect.py` |
| `convert.mjs` | Safely convert CSV/Excel to JSON for stats.mjs |
| `setup.mjs` | Create `RUN_DIR/` with numbered subdirectories |
| `validate.mjs` | JSON Schema validation for pipeline outputs |
| `artifact-check.mjs` | Verify all pipeline artifacts exist at completion |

### Python Toolkit

**template_visualize.py** — ~27 composable visualization primitives covering 5 data dimension patterns. Includes `classify_process_quality_columns()` and `compute_ccf_lag()` for time-matched process-quality analysis. Dependencies: matplotlib, pandas, numpy only (no scipy).

**template_preprocess.py** — Data preprocessing pipeline.

**file_inspect.py** — Excel/Parquet/Feather inspection (called by inspect.mjs).

### Execution Conventions

- Always try `python3` first, fall back to `python3.11`
- If matplotlib missing: `pip3 install -r scripts/requirements.txt`
- `stats.mjs` requires JSON input — use `convert.mjs` first for CSV/Excel
- `inspect.mjs` auto-detects time columns by keyword + type inference; verify and override if needed
- All paths must be absolute when running in worktree isolation

## Gotchas

- **Sorting is the #1 fatal error**: If data is NOT time-sorted, all lag correlation results are invalid. `stats.mjs` auto-validates this — always check `sorting_validation.time_sorted` before any lag claim.
- **Simpson's Paradox**: Always check if correlations hold within product/grade subgroups. Aggregate correlation may come from between-group differences, not within-group physics.
- **Parameter physical meaning**: Unknown parameter meanings trigger the clarification gate (Step 2.5). Never silently guess. Unresolved parameters carry `[PARAM_AMBIGUITY]` marker.
- **Granger causality** requires time-sorted data — results are invalid if sorting validation failed.
- **Change points**: Correlations computed across regime boundaries may be spurious. Check before drawing conclusions.
- **Interaction effects**: Weak individual correlations + strong interaction = synergistic failure mode. Don't dismiss parameters just because |r| is low.
- **Python execution in Step 7** (Report Reviewer): Reviewer should run `pip3 install -r <skill_path>/scripts/requirements.txt` before independent verification code.
- **Pipeline event log**: Each agent writes to `RUN_DIR/.pipeline_events.jsonl` at start and completion. Enables post-pipeline debugging.
