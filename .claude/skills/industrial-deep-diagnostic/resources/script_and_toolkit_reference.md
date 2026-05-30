# Script & Toolkit Reference

## Node.js Scripts (zero-dependency, always works)

| Script | Purpose | Usage |
|--------|---------|-------|
| `inspect.mjs` | Inspect data file, output schema & stats. Routes Excel/Parquet/Feather to `file_inspect.py` | `node inspect.mjs <file> [--rows N] [--sample-size N]` |
| `stats.mjs` | Correlations, z-scores, abnormal intervals | `node stats.mjs <data.json> --time-col X --target-cols A,B` |
| `setup.mjs` | Create workspace directory structure | `node setup.mjs --name X [--base-dir D]` |
| `convert.mjs` | Safe CSV/TSV → JSON conversion (handles quoted fields, large files via sampling) | `node convert.mjs <file> --output out.json [--sample N]` |

## Python Scripts

**IMPORTANT**: All Python scripts MUST run via the uv-managed venv, not system python3.

| Script | Purpose | Usage |
|--------|---------|-------|
| `file_inspect.py` | Inspect Excel/Parquet/Feather data (pandas-based) | `$PYTHON file_inspect.py <file> [--rows N]` |
| `template_visualize.py` | Adaptive visualization toolkit (~16 composable primitives) | Agent composes into custom script |
| `template_preprocess.py` | Missing values, outlier detection, resampling | Agent customizes per dataset |

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

## Visualization Toolkit (agent selects primitives by data dimension)

| Section | Primitives | When |
|---------|-----------|------|
| Data Utilities | `load_data`, `align_timeindex`, `detect_data_pattern`, `normalize_01` | Always available |
| 1D Scalar | `plot_multi_panel_timeseries`, `plot_normalized_overlay`, `plot_anomaly_zoom`, `plot_coupling_scatter`, `plot_correlation_heatmap` | Scalar time-series (default) |
| 2D Profile | `plot_profile_evolution`, `plot_position_time_heatmap`, `plot_deviation_from_target` | Spatial/position data |
| Multi-Axis | `plot_orbit`, `plot_axis_ratio` | Multi-direction measurements |
| Batch/Event | `plot_box_by_group`, `plot_event_timeline` | Categorical grouping columns |
| Spectral | `plot_spectrogram`, `plot_dominant_frequency` | Frequency-domain data |
| Manifest | `write_plot_manifest` | Always — generates the interface contract |

## JSON Schema Files

| Schema | Validates | Used By |
|--------|-----------|---------|
| `schemas/ontology_schema.json` | Process ontology structure | context-builder |
| `schemas/signal_schema.json` | Signal classification and mapping | context-builder |
| `schemas/run_config_schema.json` | Run configuration | setup |
| `schemas/analysis_schema.json` | Statistical analysis output | data-processor |
| `schemas/report_schema.json` | Report structure validation | reporter |
| `schemas/diagnosis_schema.json` | Diagnosis output (causal chain, hypotheses) | diagnostician |
| `schemas/evidence_schema.json` | Structured evidence (visual, numerical, domain) | diagnostician |
| `schemas/confidence_schema.json` | Confidence scoring and uncertainty disclosure | diagnostician, judge |
