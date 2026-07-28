# Script & Toolkit Reference

## Node.js Scripts (zero-dependency, always works)

| Script | Purpose | Usage |
|--------|---------|-------|
| `inspect.mjs` | Inspect data file, output schema & stats. Routes Excel/Parquet/Feather to `file_inspect.py` | `node inspect.mjs <file> [--rows N] [--sample-size N]` |
| `stats.mjs` | Correlations, z-scores, abnormal intervals, Simpson's Paradox, trend confounding, Granger causality, mutual information, interaction effects, change-point detection | `node stats.mjs <data.json> --time-col X --target-cols A,B [--group-col G] [--max-lag L] [--alpha 0.05] [--data-view-mode MODE]` |
| `stats_validate.mjs` | Statistical validation: Simpson's Paradox cross-check, outlier sensitivity, detrending verification, change-point analysis | `node stats_validate.mjs <feature_summary.json> <data.json> [--group-col G] [--output out.json]` |
| `setup.mjs` | Create workspace directory structure (00_input-06_scripts) | `node setup.mjs --name X [--base-dir D]` |
| `convert.mjs` | Safe CSV/TSV → JSON conversion (handles quoted fields, large files via sampling) | `node convert.mjs <file> --output out.json [--sample N]` |
| `validate.mjs` | Schema-validate any JSON file against a JSON Schema | `node validate.mjs <schema.json> <data.json>` |
| `artifact-check.mjs` | Verify required artifacts exist and validate key JSON outputs against schemas for a completed pipeline run | `node artifact-check.mjs <RUN_DIR> <SKILL_PATH>` |
| `pipeline-log-check.mjs` | Validate `.pipeline_events.jsonl` to prove step-by-step execution and repair-loop integrity | `node pipeline-log-check.mjs <RUN_DIR>` |
| `eval-assertions.mjs` | Execute eval `assertions[]` against a completed run and optionally emit skill-creator-compatible `grading.json` | `node eval-assertions.mjs <evals.json> <eval-id-or-name> <RUN_DIR> [--write-grading]` |
| `append-pipeline-event.mjs` | Append a structured `agent_start` / `agent_complete` event to `.pipeline_events.jsonl` | `node append-pipeline-event.mjs <RUN_DIR> --event agent_start --agent data-processor` |
| `evidence-closure-check.mjs` | Verify the evidence loop is closed from process fluctuation evidence → dual-drive evidence → ontology/physics interpretation → diagnosis → final report | `node evidence-closure-check.mjs <RUN_DIR> --write` |
| `data-processor-finalize.mjs` | Normalize `anomaly_report.json` + synthesize `data_analysis_conclusion.json` from processed artifacts | `node data-processor-finalize.mjs <RUN_DIR>` |
| `synthesize-run-summary.mjs` | Generate schema-aligned `run_summary.json` from run artifacts | `node synthesize-run-summary.mjs <RUN_DIR>` |
| `finalize-run-artifacts.mjs` | Run the anomaly normalization + data-analysis conclusion synthesis + run summary synthesis + evidence closure refresh sequence before final validation | `node finalize-run-artifacts.mjs <RUN_DIR> <SKILL_PATH>` |
| `generate_captions.mjs` | Generate `image_captions.json` from existing figures and plot manifest | `node generate_captions.mjs <RUN_DIR>` |
| `uv_env_setup.mjs` | Auto-install `uv`, create Python venv, install dependencies; outputs JSON with `.python` path | `node uv_env_setup.mjs` |

## Python Scripts

**IMPORTANT**: All Python scripts MUST run via the uv-managed venv, not system python3.

| Script | Purpose | Usage |
|--------|---------|-------|
| `file_inspect.py` | Inspect Excel/Parquet/Feather data (pandas-based) | `$PYTHON file_inspect.py <file> [--rows N]` |
| `dp_toolkit.py` | Data Processor deterministic toolkit: preprocess CSV, detect process/inspection anomalies, and generate adaptive diagnostic plots | `$PYTHON dp_toolkit.py preprocess|anomaly|visualize ... [--data-view-mode MODE]` |
| `stats_analysis.py` | Lightweight Python statistical analysis for wide datasets; respects process-only mode without inferring pseudo targets | `$PYTHON stats_analysis.py <data.json> <output_dir> [--target-cols ...] [--data-view-mode MODE]` |
| `physics_check.py` | **Dual-Drive engine**: automatic thermal expansion, Arrhenius kinetics, vibration thresholds, energy balance, force balance, quality reset analysis, anomaly-onset coincidence | `$PYTHON physics_check.py <RUN_DIR> <ontology.json> <feature_summary.json> <anomaly_report.json> [--output out.json] [--cleaned-data data.json]` |
| `visual_analysis.py` | Pre-VLM visual-analysis skeleton from plot metadata, statistics, anomaly report, and ontology context; must be overwritten/enriched by `vlm-visual-analyzer` | `$PYTHON visual_analysis.py <RUN_DIR> [--target-cols ...] [--key-params ...] [--group-col G]` |

## Expert Custom Scripts

The Data Processor may write focused custom scripts under `RUN_DIR/06_scripts/` when fixed scripts do not answer the scenario-specific diagnostic question.

| Script Pattern | Purpose | Expected Outputs |
|----------------|---------|------------------|
| `06_scripts/expert_analysis.py` | Scenario-specific data analysis such as product-group trends, multi-zone profile metrics, threshold checks, cascade timing, event windows, or ontology-predicted behavior validation | `02_processed/*_analysis.json`, numeric findings for `data_analysis_conclusion.json` |
| `06_scripts/scenario_plots.py` | Scenario-specific plots not covered by fixed visualization scripts | `03_figures/*.png`, entries in `plot_manifest.json` |
| `06_scripts/ontology_validation.py` | Tests whether ontology or RAG-predicted physical behavior appears in the data | `02_processed/ontology_validation.json` or merged findings in `data_analysis_conclusion.json` |

Custom scripts are evidence producers, not free-form notebooks. They should read cleaned data and ontology, write deterministic JSON/PNG outputs, and be summarized in `02_processed/data_analysis_conclusion.json`.

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

## JSON Schema Files (14 active schemas)

Schemas are validated via `node validate.mjs <schema.json> <data.json>` in the step-by-step protocol.

| Schema | Validates | Used By |
|--------|-----------|---------|
| `schemas/ontology_schema.json` | Process ontology structure | context-builder |
| `schemas/run_config_schema.json` | Run configuration | setup |
| `schemas/scenario_classification_schema.json` | Scenario classification | data-processor |
| `schemas/anomaly_report_schema.json` | Anomaly intervals, transitions, quality reset analysis | data-processor |
| `schemas/causal_evidence_map_schema.json` | Validated causal graph with root cause candidates | data-processor |
| `schemas/data_analysis_conclusion_schema.json` | Expert Data Processor handoff: fixed scripts, custom scripts, ontology/industry interpretation, and data-supported conclusions | data-processor, diagnostician |
| `schemas/visual_analysis_schema.json` | VLM visual observations, ontology grounding, chart inventory, and temporal/process-health visual synthesis | vlm-visual-analyzer, diagnostician |
| `schemas/image_captions_schema.json` | Figure captions and diagnostic implications, including fallback metadata-backed descriptions | vlm-visual-analyzer, data-processor |
| `schemas/diagnosis_schema.json` | Diagnosis output (causal chain, hypotheses) | diagnostician |
| `schemas/evidence_schema.json` | Structured evidence (visual, numerical, domain) | diagnostician |
| `schemas/confidence_schema.json` | Confidence scoring and uncertainty disclosure | diagnostician, judge |
| `schemas/reasoning_chain_schema.json` | 8-segment Chain-of-Thought reasoning trace (R1-R8) | diagnostician, judge |
| `schemas/judge_feedback_schema.json` | Judge quality gate feedback with repair instructions | judge |
| `schemas/run_summary_schema.json` | Run metadata, validation summary, artifacts inventory | reporter |
