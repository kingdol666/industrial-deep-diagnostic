---
name: industrial-data-processor
description: "Industrial diagnosis pipeline stage — ontologically-guided statistical analysis + visualization charts + artifact integrity recovery. Runs Simpson detection, detrending, change-point analysis, time-lag CCF, batch uniqueness, outlier leverage and related validations. Do NOT use for general data analysis or statistics homework. Trigger: statistical analysis, data processing, data cleaning, data visualization, chart generation, statistics, Simpson, correlation, CCF, batch analysis, data processor"
---

# Industrial Data Processor

Performs full-chain statistical analysis on industrial sensor/process data under ontology guidance — scenario classification, data cleaning, production-state identification, multi-dimensional statistical validation, and visualization chart generation. Produces `data_analysis_conclusion.json` as the mandatory handoff artifact for the diagnostician.

## Inputs / Outputs

### Inputs (in `RUN_DIR`)

| File | Description |
|------|-------------|
| `01_ontology/ontology.json` | Domain ontology (CP-2 passed) |
| `00_input/input_manifest.json` | Data source information |
| `00_input/run_config.json` | Run configuration |
| `00_input/rag_deep_understanding.json` | RAG validation queue (if any) |
| Raw data file | CSV/TSV/delimited text/XLSX/XLSM/JSON/Parquet, or the E-1-preprocessed `00_input/preprocessed_data.csv` (DATA_PATH points to it) |

### Outputs

| File | Description |
|------|-------------|
| `02_processed/scenario_classification.json` | Scenario classification |
| `02_processed/anomaly_report.json` | Anomaly report |
| `02_processed/data_analysis_conclusion.json` | Data analysis conclusion (mandatory handoff artifact) |
| `02_processed/validate_report.json` | Statistical validation report |
| `02_processed/feature_summary.json` | Feature summary — must include the three top-level fields columns(object)/dataset_profile(object)/metadata(object) (feature_summary_schema required) |
| `02_processed/production_regime_filter.json` | Production regime filter (when applicable) |
| `02_processed/time_lag_analysis.json` | Time-lag analysis results (when applicable) |
| `02_processed/duplicate_batch_report.json` | Duplicate batch report (when applicable) |
| `02_processed/analysis_plan.md` | Analysis plan |
| `03_figures/plot_manifest.json` | Plot manifest |
| `03_figures/image_captions.json` | Plot captions |
| `03_figures/visual_analysis.json` | VLM visual analysis output |
| `03_figures/*.png` | Visualization charts |



## Pipeline Event Logging

**MANDATORY** — log lifecycle events for pipeline-finalize.mjs execution proof verification:

```bash
# On start (before any work)
node "$SHARED_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" \
  --event agent_start --agent data-processor --step data_processor

# On completion (after ALL outputs written)
node "$SHARED_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" \
  --event agent_complete --agent data-processor --step data_processor \
  --files 02_processed/data_analysis_conclusion.json,02_processed/validate_report.json,03_figures/plot_manifest.json,03_figures/visual_analysis.json,03_figures/image_captions.json
```

These events are required by `pipeline-log-check.mjs` and `pipeline-finalize.mjs` to prove disciplined sequential execution.

## Dispatch

Launch the `data-processor` sub-agent (**ontology_first** mode — read the ontology before any statistics):

```javascript
Agent({
  subagent_type: "data-processor",
  prompt: `DATA_PATH=<data-file-path>
RUN_DIR=<run-dir-path>
SKILL_PATH=<path-to-.claude/skills/industrial-data-processor>

Read "$SKILL_PATH/references/agent-protocol.md" and execute Phase 0-6.

Key constraints:
- Phase 0.4 gates all analysis — read ontology before any statistical work
- **Phase 1.2 is the adaptive decision hub: distill hypotheses first, then select the minimal discriminative method set for each from the analysis_methods_catalog; methods follow hypotheses — never run the full battery without plan selection**
- v6.5: Production regime detection (three-algorithm fusion) runs BEFORE stats; filter to steady-state only
- v6.4: Time-lag compensation (CCF-based optimal lag per parameter pair) — only when the method plan selects M6 and the data shape meets the prerequisites
- v6.5: Per-product mandatory analysis — worst product by anomaly rate, steady-state compare, Simpson detection — only when multi-product grouping exists
- VLM visual analysis is dispatched via a separate Agent() call to the vlm-visual-analyzer Agent — see the VLM Visual Analysis Dispatch section below
`
})
```

### VLM Visual Analysis Dispatch (Phase 5.5)

#### Step 0: Generate VLM-Specialized Temporal Overlay Charts

Before dispatching VLM, generate VLM-optimized temporal overlay charts following `visual_analysis_framework.md` design specs:

```bash
# Generate fig_vlm_temporal_overlay.png (all parameters, z-score normalized, direction-aligned)
# Generate fig_vlm_per_product_overlay.png (per-group temporal alignment)
uv run --project "$SHARED_PATH/scripts" python "$SKILL_PATH/scripts/generate_vlm_charts.py" "$RUN_DIR" \
  --target-cols <quality_cols> \
  --key-params <process_params> \
  --group-col <group_col> \
  --time-col <time_col> \
  --events <events_json>
```

Key design specs for VLM chart (see `resources/visual_analysis_framework.md` §Design Principles):
- All parameters z-score normalized onto the same scale
- Negatively correlated parameters direction-reversed (so all lines move in the same direction)
- Shared x-axis (time) — only when a valid time column exists
- Events marked with red dashed lines + text annotations
- Fonts >= 12pt, high contrast
- Titles in English (for matplotlib rendering compatibility)

#### Step 1: Build VLM Input Filter Manifest

**Not all images go to VLM.** Only images with true spatio-temporal alignment carry diagnostic value for VLM. Generate `vlm_input_manifest.json` to filter:

| Priority | Image Type | VLM Value | Example |
|----------|-----------|-----------|---------|
| **MANDATORY** | Temporal overlay (multi-param, shared time axis, normalized) | VLM reads synchrony, precedence, event response, trend morphology | `fig_vlm_temporal_overlay.png` |
| **MANDATORY** | Per-product temporal overlay | VLM reads group-specific degradation patterns | `fig_vlm_per_product_overlay.png` |
| **SUPPLEMENTARY** | Scatter with confounder coloring | VLM checks Simpson Paradox (cluster separation) | `separator_vs_residue.png` |
| **NOT_FOR_VLM** | Single-param trend, bar chart, basic plot | No cross-parameter insight for VLM | `correlation_robustness.png`, `mill_power_trend.png` |

```bash
# Generate vlm_input_manifest.json (selects which images VLM reads)
uv run --project "$SHARED_PATH/scripts" python "$SKILL_PATH/scripts/generate_vlm_manifest.py" "$RUN_DIR" --plot-manifest "$RUN_DIR/03_figures/plot_manifest.json"
```

#### Step 2: Write Skeleton (Fallback Base)

```bash
node "$SKILL_PATH/scripts/generate_captions.mjs" "$RUN_DIR"
# Write visual_analysis.json with observation_mode: "skeleton_pre_vlm"
```

#### Step 3: Dispatch vlm-visual-analyzer Agent

**Only images in `vlm_input_manifest.json` are sent to VLM.** VLM MUST read `vlm_input_manifest.json` first to know which images to read and in what order.

```javascript
Agent({
  subagent_type: "vlm-visual-analyzer",
  prompt: `RUN_DIR=<run-dir-path>
SKILL_PATH=<path-to-.claude/skills/industrial-data-processor>
SHARED_PATH=.claude/shared/
DATA_PATH=<data-file-path>

Read ".claude/agents/vlm-visual-analyzer.md" and follow the complete VLM visual analysis protocol.

## IMAGE SELECTION (MANDATORY — DO NOT READ ALL PNGs)
- FIRST read "vlm_input_manifest.json" from RUN_DIR/03_figures/
- ONLY read images listed in vlm_input_manifest.json with priority MANDATORY or SUPPLEMENTARY
- DO NOT read images excluded from vlm_input_manifest — they have no cross-parameter temporal alignment
- Read MANDATORY images first (temporal overlays), then SUPPLEMENTARY (scatter for Simpson check)
- MANDATORY images have z-score normalization + direction reversal — understand this before interpretation

Key constraints:
- Read ontology.json BEFORE reading any image — blind image reading is prohibited
- Read vlm_input_manifest.json for image priority ordering (NOT plot_manifest.json directly)
- Read data_analysis_conclusion.json and validate_report.json for statistical context
- Read each selected PNG in priority order, extracting structured visual observations
- Focus on: temporal synchrony, precedence signals, event response, trend morphology, group separation
- Overwrite skeleton_pre_vlm if present — final output MUST have analysis_provenance.source_agent = "vlm-visual-analyzer"
- Output visual_analysis.json and image_captions.json to RUN_DIR/03_figures/
- At least 2 key visual observations MUST contain non-empty ontology_context
- Fallback: if VLM_ENABLED=false or API unavailable, write metadata-only skeleton with observation_mode: "metadata_fallback"
`
})
```

Anti-forgery verification after VLM analysis completes:

```bash
# Verify source_agent, skeleton_overwritten, and that only vlm_input_manifest images were read
node "$SKILL_PATH/scripts/vlm-verification-check.mjs" "$RUN_DIR"
# Verify that excluded images were NOT read
uv run --project "$SHARED_PATH/scripts" python -c "import json; v=json.load(open('$RUN_DIR/03_figures/visual_analysis.json')); m=json.load(open('$RUN_DIR/03_figures/vlm_input_manifest.json')); vlm_files=[i['filename'] for i in m['vlm_images']]; read=[i['filename'] for i in v.get('chart_inventory',[]) if i.get('filename') in vlm_files]; excluded_read=[i['filename'] for i in v.get('chart_inventory',[]) if i.get('filename') not in vlm_files]; print(f'VLM read {len(read)}/{len(vlm_files)} selected images, excluded reads: {excluded_read if excluded_read else "NONE (clean)"}')"
```

### Post-Processing (after both agents complete)

```bash
SKILL_PATH="<path-to-.claude/skills/industrial-data-processor>"

# Normalize anomaly report + synthesize data analysis conclusion
node "$SKILL_PATH/scripts/data-processor-finalize.mjs" "$RUN_DIR"
```


## Execution Flow (Phase 0-6)

Full protocol in `references/agent-protocol.md` (Phase 0-6 checklist, persona, data truth mandate, gates). On-demand references at `resources/execution_reference.md` (bash commands), `resources/anti_spurious_rules.md` (v6 rules), `resources/scenario_patterns.md` (scenario-specific analysis patterns), and `resources/visual_analysis_framework.md` (chart design).

| Phase | Purpose | Gate |
|-------|---------|------|
| 0 | Data exploration + ontology-first analysis plan | `analysis_parameter_selection.json` + plan section |
| 1 | Scenario classification + production state detection | Schema-valid `scenario_classification.json`; stats input source determined |
| 1.2 | **Hypothesis decomposition + adaptive method plan** — the skill only provides direction: distill 3-6 hypotheses from ontology + scenario + problem, and for each hypothesis select the minimal discriminative method set from `resources/analysis_methods_catalog.md` | `analysis_method_plan.json`: ≥2 hypotheses, ≥1 method per hypothesis, skips leave an audit trail |
| 1.5 | Production regime detection (three-algorithm fusion) | Stats input source determined |
| 2 | **Plan-driven** universal analysis (execute the stats modes selected by the plan, not the full battery) + anomaly + time-lag (when applicable) + batch integrity (when applicable) | `feature_summary.json` + `validate_report.json` exist; `data_source` set |
| 3 | Plan-mapped scenario deep analysis + dual-drive + **hypothesis sufficiency check** | Schema-valid `data_analysis_conclusion.json`; every hypothesis has a supported/refuted/indeterminate verdict |
| 4 | RAG knowledge validation | All claims validated or marked untestable |
| 5 | Visualization — per-product time-aligned overlays | `plot_manifest.json` has ≥1 verified real plot |
| 5.5 | VLM visual analysis (optional, auto-degrade) | `visual_analysis.json` exists (metadata or VLM-enriched) |
| 6 | Stabilize + verify output contract | All mandatory files exist and non-empty |

## Data Truth Mandate

**Every number written into JSON/reports must be recomputable from the raw data.**

| Rule | Requirement |
|------|------|
| Numeric traceability | Every number must be annotated with data source (cleaned/raw), row range, and computation method |
| Derived value marking | Inferred/derived values must be explicitly marked `"derived": true` or `"inferred": true` |
| Cleaning audit trail | cleaning_integrity records all cleaning operations |
| Visualization traceability | Every data point in every plot must be traceable to specific dataset rows |
| Unavailable marking | Values that cannot be computed from data → write NOT_APPLICABLE + reason |

## Counterfactual Reasoning — Exclusion Constraints

| Constraint | Description |
|------|------|
| Four conditions | Temporal precedence + statistical significance + physical mechanism + no contradiction |
| Exclusion criterion | Any unmet condition → mark as an excluded candidate and provide quantitative justification |
| Physics boundary | Exclusions must be supported by first principles or governing equations |
| Confidence threshold | When exclusion confidence <80, mark `[WEAK_EXCLUSION]` |

## Assumptions & Limitations

| Category | Requirement |
|------|------|
| Data limitations | Sampling rate / noise / missing extremes / range limits |
| Model assumptions | Linear approximation / steady-state assumptions / distribution assumptions |
| Uncontrolled confounders | Explicitly list potential confounding variables that cannot be controlled |
| Conclusion confidence intervals | Annotate each conclusion with confidence ± error margin |

## Efficiency — Parallel Execution

- No data dependency with upstream/downstream agents → parallelize proactively
- Use deterministic scripts instead of LLM reasoning for predictable results
- Large-file sampling strategy: systematic sampling when >100K rows
- Agent stall >600s → check existing artifacts; if partially usable, keep moving forward

## Verification

```bash
SKILL_PATH="<path-to-.claude/skills/industrial-data-processor>"
SHARED_PATH=".claude/shared/"

# Schema validations
node "$SHARED_PATH/scripts/validate.mjs" \
  "$SHARED_PATH/schemas/scenario_classification_schema.json" \
  "$RUN_DIR/02_processed/scenario_classification.json"

# Feature summary schema compliance (MUST include columns/dataset_profile/metadata)
node "$SHARED_PATH/scripts/validate.mjs" "$SHARED_PATH/schemas/feature_summary_schema.json" "$RUN_DIR/02_processed/feature_summary.json"

node "$SHARED_PATH/scripts/validate.mjs" \
  "$SHARED_PATH/schemas/anomaly_report_schema.json" \
  "$RUN_DIR/02_processed/anomaly_report.json"

node "$SHARED_PATH/scripts/validate.mjs" \
  "$SHARED_PATH/schemas/data_analysis_conclusion_schema.json" \
  "$RUN_DIR/02_processed/data_analysis_conclusion.json"

node "$SHARED_PATH/scripts/validate.mjs" \
  "$SHARED_PATH/schemas/image_captions_schema.json" \
  "$RUN_DIR/03_figures/image_captions.json"

# CP-4 Handoff: verify plot_manifest has plots
test -f "$RUN_DIR/02_processed/data_analysis_conclusion.json" && \
  node -e "var p=JSON.parse(require('fs').readFileSync('$RUN_DIR/03_figures/plot_manifest.json','utf8')); process.exit(p.plots&&p.plots.length>0?0:1)"
```

## Artifact Integrity Recovery

Missing outputs auto-restored by scripts in `.claude/skills/industrial-data-processor/scripts/`:

| Missing | Recovery |
|---------|----------|
| `scenario_classification.json` | Infer from ontology.json + feature_summary.json |
| `anomaly_report.json` | Infer from validate_report + data_analysis_conclusion |
| `plot_manifest.json` | Reverse from 03_figures/*.png |
| `image_captions.json` | Generate fallback from plot_manifest |

## Failure Recovery

| Scenario | Recovery |
|----------|----------|
| Python venv missing | `node .claude/shared/scripts/uv_env_setup.mjs` |
| Files >500MB | `uv run --project "$SHARED_PATH/scripts" python .claude/skills/industrial-data-processor/scripts/file_inspect.py --sample 50000` |
| Plot generation fails | Fix data and rerun; else L4 text fallback in `image_captions.json` |
| No time column | Document in `analysis_plan.md` + `data_analysis_conclusion.json` |

## Pre-Profile Handoff (Step 2P parallel artifact)

If `02_processed/pre_profile.json` (data format/quality/production-state profiling, independent of ontology semantics) exists, Phase 0-1 consumes its conclusions directly and skips duplicate probing; semantic analysis from Phase 2 onward still follows the ontology (the ontology_first semantic contract is unchanged).
