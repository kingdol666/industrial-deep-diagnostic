---
name: industrial-deep-diagnostic
description: >
  Evidence-first industrial time-series analysis and root cause diagnostic.
  Analyzes process data, searches local references, performs statistical analysis,
  generates engineering visualizations, diagnoses anomalies with traceable evidence,
  and produces rigorous engineering reports.
  Use this skill whenever the user provides industrial/process/manufacturing data
  (CSV, XLSX, Parquet) and asks about anomalies, root causes, quality issues,
  equipment faults, or process diagnostics. Also use when the user mentions:
  industrial diagnosis, process analysis, anomaly detection, root cause analysis,
  time-series analysis, quality investigation, fault diagnosis, production issue,
  sensor data analysis, equipment health, SPC, statistical process control,
  工业诊断, 过程分析, 异常检测, 根因分析, 质量分析, 故障诊断, 传感器数据.
  Do NOT use for: simple data visualization, general statistics homework,
  financial time-series, or non-industrial data analysis.
commands:
  - industrial-deep-diagnostic
  - industrial-deep-diagnostic analyze
  - industrial-deep-diagnostic review
  - industrial-deep-diagnostic report
version: 4.0.0
---

# Industrial Deep Diagnostic

## Core Principle

**Evidence first. Reasoning second. Conclusions last.**

Every conclusion must cite its evidence source and rank (1=direct data, 2=user docs, 3=statistics, 4=visual, 5=process logic, 6=web, 7=hypothesis). No unsupported assumptions. No exaggerated causal claims.

## Architecture

```
MAIN AGENT (you — orchestrator only, keep context clean)
│
├── inspect.mjs (Node, zero-dep) ──► inspect data, get schema & stats
├── setup.mjs  (Node, zero-dep) ──► create workspace directory
│
├── spawn agents/context-builder.md   ──► ontology + references
│                                         writes: 01_ontology/*
├── spawn agents/data-processor.md    ──► adaptive visualization
│                                         reads:  00_input/*
│                                         writes: 02_processed/*, 03_figures/*, 06_scripts/*
├── spawn agents/diagnostician.md     ──► diagnosis with evidence
│                                         reads:  01_ontology/*, 02_processed/*, 03_figures/plot_manifest.json
│                                         writes: 04_diagnostics/*
├── spawn agents/judge.md             ──► verify + score
│                                         reads:  04_diagnostics/*
│                                         writes: 05_review/*
├── spawn agents/reporter.md          ──► generate report
│                                         reads:  ALL previous outputs
│                                         writes: report.md, run_summary.json
│
└── present results to user
```

### Agent Decoupling via Workspace Files

Agents do NOT share context through the main agent. They communicate exclusively through files in the workspace directory:

```
Context Builder ──► 01_ontology/ontology.json, schema.json
                        ↓
Data Processor  ──► 02_processed/feature_summary.json
                 ──► 03_figures/*.png
                 ──► 03_figures/plot_manifest.json  ← INTERFACE CONTRACT
                        ↓
Diagnostician   ──► 04_diagnostics/diagnosis.json, evidence.json, confidence.json
                        ↓
Judge           ──► 05_review/judge_feedback.json
                        ↓
Reporter        ──► report.md, run_summary.json
```

**Key interface: `plot_manifest.json`** — the data-processor writes it to tell the diagnostician exactly what plots exist, why each was generated, and HOW (time alignment, normalization, function used).

**Script philosophy**: Node.js for fixed operations (zero dependency, always works). Python as adaptive toolkit — the agent reads data first, then selects visualization primitives based on data dimensions.

## Execution Steps

### Step 0: Setup Workspace

```bash
node <skill_path>/scripts/setup.mjs --name <scene_name> --base-dir ./workspace/diagnostic-runs
```

This creates a structured workspace:
```
workspace/diagnostic-runs/<timestamp>_<name>/
├── 00_input/          ← data manifest, user context
├── 01_ontology/       ← ontology.json, schema.json
├── 02_processed/      ← cleaned data, feature summary
├── 03_figures/        ← plots (PNG) + plot_manifest.json
├── 04_diagnostics/    ← diagnosis, evidence, confidence
├── 05_review/         ← judge feedback
├── 06_scripts/        ← custom Python scripts written by agent
├── report.md          ← final report
└── run_summary.json   ← run metadata
```

### Step 1: Inspect Data (MAIN)

```bash
node <skill_path>/scripts/inspect.mjs <data_path>
```

This outputs JSON with column names, types, stats, time column detection, and preview. **Read this output carefully** — it tells you exactly what the data looks like.

Then ask the user clarification questions (max 5 at a time). Only ask what you cannot infer from the inspection results.

Save `input_manifest.json` and `user_context.json` to `00_input/`.

### Step 2: Context Building (SUB-AGENT)

Read `agents/context-builder.md` and spawn a sub-agent. Pass: DATA_PATH, RUN_DIR, REFERENCE_DIR, PROCESS_DESCRIPTION, SKILL_PATH.

### Step 3: Data Processing + Adaptive Visualization (SUB-AGENT)

Read `agents/data-processor.md` and spawn a sub-agent. This agent follows a structured decision protocol:

1. **Inspect data** (node inspect.mjs) → understand structure
2. **Compute statistics** (node stats.mjs) → correlations, anomalies
3. **Classify data pattern** using `detect_data_pattern()`:
   - 1D scalar, multi-axis, 2D profile, batch/event, spectral, or mixed
4. **Select visualization primitives** from the toolkit based on pattern
5. **Apply time alignment** if sampling is irregular (via `align_timeindex()`)
6. **Compose and run** custom visualization script
7. **Write `03_figures/plot_manifest.json`** — tells the diagnostician:
   - What plots exist, what each shows
   - HOW each was generated (function, alignment, normalization)
   - What to look for (interpretation hints)

The visualization toolkit (`scripts/template_visualize.py`) provides composable primitives for ALL dimension types — the Agent selects which ones to use based on the actual data.

### Step 4: Diagnosis (SUB-AGENT)

Read `agents/diagnostician.md` and spawn. The diagnostician:
1. Reads `plot_manifest.json` FIRST — the interface contract from data-processor
2. Uses `generation_method` fields to understand HOW each plot was created
3. Reads each plot image via VLM
4. Combines visual (Rank 4) + statistical (Rank 3) + direct (Rank 1) evidence

### Step 5: Judge Review (SUB-AGENT)

Read `agents/judge.md` and spawn. The judge scores 10 criteria (weighted). If score < 90, the judge writes `repair_instruction` fields in `judge_feedback.json`.

**Automated repair loop:**
1. If verdict is PASS (score >= 90) → proceed to Step 6
2. If verdict is NEEDS_REPAIR (70-89) → read `judge_feedback.json`, extract the `repair_instruction` from each blocking_issue, and re-spawn the diagnostician with these instructions appended to the prompt. Max 3 iterations.
3. If verdict is FAIL (< 70) → the issues are too severe for automated repair. Report to user with the judge feedback and ask for guidance.
4. If max iterations (3) reached without PASS → proceed with warning, the reporter will note the limitation.

**Judge feedback format** (in `05_review/judge_feedback.json`):
```json
{
  "verdict": "pass|needs_repair|major_issues|fail",
  "overall_score": 85,
  "blocking_issues": [
    {"description": "...", "repair_instruction": "Re-analyze X with Y data...", "affected_steps": ["step_4"]}
  ]
}
```

The `repair_instruction` field is the key to automation — it tells the diagnostician exactly what to fix.

### Step 6: Report (SUB-AGENT)

Read `agents/reporter.md` and spawn.

### Step 7: Present Results (MAIN)

Show the user: executive summary, key findings, primary diagnosis, top recommendations, workspace path.

## Parallel Execution

Steps 2 and 3 can run **in parallel**. Steps 4→5→6 must be **sequential**.

## Commands

| Command | Action |
|---------|--------|
| `/industrial-deep-diagnostic` | Full pipeline |
| `/industrial-deep-diagnostic analyze` | Skip intake, run from Step 2 |
| `/industrial-deep-diagnostic review` | Re-run judge on existing results |
| `/industrial-deep-diagnostic report` | Regenerate report from existing artifacts |

## Script Reference

### Node.js (fixed, zero-dependency, always works)

| Script | Purpose | Usage |
|--------|---------|-------|
| `inspect.mjs` | Inspect data file, output schema & stats | `node inspect.mjs <file> [--rows N]` |
| `stats.mjs` | Correlations, z-scores, abnormal intervals | `node stats.mjs <data.json> --time-col X --target-cols A,B` |
| `setup.mjs` | Create workspace directory structure | `node setup.mjs --name X [--base-dir D]` |

### Python Toolkit (agent selects primitives based on data dimensions)

| Section | Primitives | When |
|---------|-----------|------|
| Data Utilities | `load_data`, `align_timeindex`, `detect_data_pattern`, `normalize_01` | Always available |
| 1D Scalar | `plot_multi_panel_timeseries`, `plot_normalized_overlay`, `plot_anomaly_zoom`, `plot_coupling_scatter`, `plot_correlation_heatmap` | Scalar time-series (default) |
| 2D Profile | `plot_profile_evolution`, `plot_position_time_heatmap`, `plot_deviation_from_target` | Spatial/position data |
| Multi-Axis | `plot_orbit`, `plot_axis_ratio` | Multi-direction measurements |
| Batch/Event | `plot_box_by_group`, `plot_event_timeline` | Categorical grouping columns |
| Spectral | `plot_spectrogram`, `plot_dominant_frequency` | Frequency-domain data |
| Manifest | `write_plot_manifest` | Always — generates the interface contract |

The agent reads the toolkit, classifies data dimensions, selects relevant primitives, and composes a custom script. NOT a fixed template — adapts to what the data actually looks like.

### Python Templates (agent customizes per dataset)

| Template | Purpose |
|----------|---------|
| `template_preprocess.py` | Missing values, outlier detection, resampling |

## Schema Reference

JSON Schema draft-07 schemas for validating all artifacts:

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

Agents should read their relevant schema files to ensure output validity. Schemas are normative — agent prompts are explanatory.

## Diagnosis Language

| Type | Marker | Template |
|------|--------|----------|
| Observation | [OBSERVATION] | "[Variable] [changed] by [X%] from [T1] to [T2]." |
| Inference | [INFERENCE] | "This coincides with [event/measurement]." |
| Hypothesis | [HYPOTHESIS] | "This suggests [mechanism] may have contributed." |
| Uncertainty | [UNCERTAINTY] | "Evidence is [level] to [conclude X]." |

## Anti-Speculation

NEVER state root cause without: (1) temporal precedence, (2) statistical evidence, (3) physical mechanism, (4) no contradicting evidence. If ANY missing, use [HYPOTHESIS].

ALWAYS disclose confidence, evidence gaps, and assumptions.
