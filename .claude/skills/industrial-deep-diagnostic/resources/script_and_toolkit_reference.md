# Script & Toolkit Reference

## Node.js Scripts (zero-dependency, always works)

| Script | Purpose | Usage |
|--------|---------|-------|
| `inspect.mjs` | Inspect data file, output schema & stats. Routes Excel/Parquet/Feather to `file_inspect.py` | `node inspect.mjs <file> [--rows N] [--sample-size N]` |
| `stats.mjs` | Correlations, z-scores, abnormal intervals, Simpson's Paradox, trend confounding, Granger causality, mutual information, interaction effects, change-point detection | `node stats.mjs <data.json> --time-col X --target-cols A,B [--group-col G] [--max-lag L] [--alpha 0.05]` |
| `stats_validate.mjs` | Statistical validation: Simpson's Paradox cross-check, outlier sensitivity, detrending verification, change-point analysis | `node stats_validate.mjs <feature_summary.json> <data.json> [--group-col G] [--output out.json]` |
| `setup.mjs` | Create workspace directory structure (00_input-06_scripts) | `node setup.mjs --name X [--base-dir D]` |
| `convert.mjs` | Safe CSV/TSV → JSON conversion (handles quoted fields, large files via sampling) | `node convert.mjs <file> --output out.json [--sample N]` |
| `validate.mjs` | Schema-validate any JSON file against a JSON Schema | `node validate.mjs <schema.json> <data.json>` |
| `artifact-check.mjs` | Verify all required artifacts exist for a completed pipeline run | `node artifact-check.mjs <RUN_DIR> <SKILL_PATH>` |
| `generate_captions.mjs` | Generate `image_captions.json` from existing figures and plot manifest | `node generate_captions.mjs <RUN_DIR>` |
| `uv_env_setup.mjs` | Auto-install `uv`, create Python venv, install dependencies; outputs JSON with `.python` path | `node uv_env_setup.mjs` |

## Python Scripts

**IMPORTANT**: All Python scripts MUST run via the uv-managed venv, not system python3.

| Script | Purpose | Usage |
|--------|---------|-------|
| `file_inspect.py` | Inspect Excel/Parquet/Feather data (pandas-based) | `$PYTHON file_inspect.py <file> [--rows N]` |
| `physics_check.py` | **Dual-Drive engine**: automatic thermal expansion, Arrhenius kinetics, vibration thresholds, energy balance, force balance, quality reset analysis, anomaly-onset coincidence | `$PYTHON physics_check.py <RUN_DIR> <ontology.json> <feature_summary.json> <anomaly_report.json> [--output out.json] [--cleaned-data data.json]` |

**Get $PYTHON path**: `node scripts/uv_env_setup.mjs` → parse JSON output → use `python` field.

## Python Environment (uv-managed)

```bash
# One-time setup (auto-installs uv + creates venv + installs deps)
node scripts/uv_env_setup.mjs

# Get Python path for all subsequent invocations
PYTHON=$(node scripts/uv_env_setup.mjs | tail -1 | sed 's/.*"python":"\([^"]*\)".*/\1/')
$PYTHON <script.py> [args]
```

| Package | Required For |
|---------|-------------|
| matplotlib, numpy, pandas | Core visualization (required) |
| seaborn | Enhanced heatmaps (optional) |
| openpyxl | Excel .xlsx reading (optional) |
| pyarrow | Parquet / Feather reading (optional) |

## JSON Schema Files (11 active schemas)

Schemas are validated via `node validate.mjs <schema.json> <data.json>` in the step-by-step protocol.

| Schema | Validates | Used By |
|--------|-----------|---------|
| `schemas/ontology_schema.json` | Process ontology structure | context-builder |
| `schemas/run_config_schema.json` | Run configuration | setup |
| `schemas/scenario_classification_schema.json` | Scenario classification | data-processor |
| `schemas/anomaly_report_schema.json` | Anomaly intervals, transitions, quality reset analysis | data-processor |
| `schemas/causal_evidence_map_schema.json` | Validated causal graph with root cause candidates | data-processor |
| `schemas/diagnosis_schema.json` | Diagnosis output (causal chain, hypotheses) | diagnostician |
| `schemas/evidence_schema.json` | Structured evidence (visual, numerical, domain) | diagnostician |
| `schemas/confidence_schema.json` | Confidence scoring and uncertainty disclosure | diagnostician, judge |
| `schemas/reasoning_chain_schema.json` | 8-segment Chain-of-Thought reasoning trace (R1-R8) | diagnostician, judge |
| `schemas/judge_feedback_schema.json` | Judge quality gate feedback with repair instructions | judge |
| `schemas/run_summary_schema.json` | Run metadata, validation summary, artifacts inventory | reporter |
