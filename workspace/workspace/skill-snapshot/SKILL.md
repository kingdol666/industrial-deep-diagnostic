---
name: industrial-deep-diagnostic
description: "Industrial time-series root cause diagnostic. Use whenever a user provides sensor, process, or manufacturing data (CSV, XLSX, Parquet) and wants to know why a quality deviation, equipment fault, or process anomaly occurred. Triggers on: anomaly detection, root cause analysis, fault diagnosis, sensor data analysis, equipment health monitoring, SPC/statistical process control, 工业诊断, 过程分析, 异常检测, 根因分析, 质量分析, 故障诊断, 传感器数据. Also trigger when the user mentions production line issues, manufacturing defects, process parameter drift, or wants to understand what caused a quality problem — even if they don't use the word 'diagnostic.' Not for: simple charting requests, general statistics homework, financial time-series, or non-industrial data."
commands:
  - industrial-deep-diagnostic
  - industrial-deep-diagnostic analyze
  - industrial-deep-diagnostic review
  - industrial-deep-diagnostic report
  - industrial-deep-diagnostic audit
---

# Industrial Deep Diagnostic

## Overview

Evidence-first industrial time-series analysis and root cause diagnostic. Multi-agent pipeline: inspect data → build context → clarify unknown parameters with user → visualize + validate → diagnose → judge → report → physical truth audit → review repair loop.

**Core principle: Evidence first. Reasoning second. Conclusions last.**

Every conclusion cites its evidence rank (1-7). Unsupported assumptions are prohibited. Unknown parameter meanings trigger interactive clarification — the pipeline asks rather than guesses.

## Data-Driven Diagnosis Principles

### 1. Parameters Match Targets by Time

Process parameters and quality metrics are linked by time offset. A process change at time T propagates through the production line and manifests in quality at time T+ΔT. The diagnosis:
- Classifies columns as process parameters (cause candidates) vs quality metrics (effect targets)
- Computes the optimal time lag between each process-quality pair via cross-correlation
- Matches process data at time T to quality data at time T+lag before drawing conclusions
- Treats concurrent (lag=0) correlation as suggestive only — temporal ordering must be verified

### 2. Multi-Dimensional Analysis

A single correlation number is not a diagnosis. Every diagnostic conclusion draws from multiple evidence dimensions:

| Dimension | Source | What it reveals |
|-----------|--------|-----------------|
| Time-domain alignment | Multi-panel timeseries, lag-shifted overlays | Temporal ordering, lead-lag relationships |
| Correlation structure | Heatmaps, CCF curves, lag sensitivity | Linear/non-linear coupling strength |
| Distribution analysis | Box plots, stratified correlations | Subgroup stability, Simpson's Paradox |
| Process→Quality mapping | Dual timelines, lag scatter plots | Causal chain from process to quality |
| Temporal stability | Rolling window correlations | Whether relationships hold across time windows |
| Interaction effects | Interaction heatmaps | Synergistic parameter combinations |

### 3. Visualization Selection is Data-Driven

The Data Processor agent does not use a fixed plot list. It:
1. Classifies data dimensions (1D scalar, multi-axis, 2D profile, batch/event, spectral, mixed)
2. Classifies columns as process/cause or quality/effect by keyword heuristics
3. Selects visualization primitives based on the classified pattern and statistical triggers
4. Composes a custom `visualize.py` script for each diagnostic run

The skill provides the primitives library and selection protocol. The agent decides which primitives to use based on data characteristics.

### 4. Every Report Claim is Traceable to Data

The reasoning chain (`reasoning_chain.json`) records the complete path: raw observation → statistical evidence → hypothesis → conclusion. Every claim in the final report cites which link in this chain supports it. The Reporter views every figure independently and describes what it sees — not what the Diagnostician claimed was there.

## Root Cause Convergence: Data + Physics + Logic

The pipeline converges to a single most probable root cause through an integrated reasoning framework — it does not end with a list of hypotheses:

```
RAW DATA (CSV columns, timestamps, values)
    ↓ statistical analysis
STATISTICAL EVIDENCE (correlations, CCF lags, MI, Granger, interactions)
    ↓ validation filtering
ROBUST EVIDENCE (survives Simpson, trend, outlier, sorting checks)
    ↓ physical mechanism mapping
CAUSAL CHAIN (parameter → intermediate state → defect, each link [OBSERVED] or [INFERRED])
    ↓ counterfactual elimination
SURVIVING HYPOTHESES (those that pass all elimination tests)
    ↓ convergence synthesis
ROOT CAUSE CONCLUSION (the single most probable cause, with integrated evidence chain)
```

**The convergence is driven by three integrated dimensions:**

1. **Data** (0-35 points) — Which parameter has the strongest, most robust statistical relationship with the defect? CCF lag, correlation magnitude, consistency across subgroups, detrending survival.
2. **Physics** (0-35 points) — Which parameter's deviation can physically produce all observed symptoms through an established mechanism? Includes quantitative magnitude check: can X°C really cause Y% defect increase?
3. **Logic** (0-30 points) — Which causal chain has the fewest [INFERRED] links, the most [OBSERVED] links, and survives counterfactual testing?

The final root cause conclusion states: "Parameter [X] at time [T] deviated by [Δ], which caused [intermediate change Y] through [physical mechanism Z], resulting in [defect D] observed at time [T+lag]. Supported by [evidence summary with ranks], survives [validation checks passed]."

## Commands

| Command | Action |
|---------|--------|
| `/industrial-deep-diagnostic` | Full pipeline (Steps 0-8) |
| `/industrial-deep-diagnostic analyze` | Skip intake, run from Step 2 |
| `/industrial-deep-diagnostic review` | Re-run judge on existing results |
| `/industrial-deep-diagnostic report` | Regenerate report from existing artifacts |
| `/industrial-deep-diagnostic audit` | Run report-reviewer only (generates optimizer.md) |

## Execution Flow

The full step-by-step protocol lives in `pipeline-execution.md` — read it when executing the pipeline. It covers per-step instructions, artifact chains, repair loops, and the statistical validation framework.

```
digraph diagnostic_flow {
  rankdir=TB;
  node [shape=box];

  setup [label="Step 0: Setup"];
  inspect [label="Step 1: Inspect"];
  context [label="Step 2: Context"];
  clarify [label="Step 2.5: Clarify\nParameters" shape=diamond];
  dataproc [label="Step 3: Data+Viz"];
  diag [label="Step 4: Diagnose"];
  judge [label="Step 5: Judge"];
  report [label="Step 6: Report"];
  review [label="Step 7: Audit"];
  repair [label="Step 7.5: Review\nRepair" shape=diamond];
  present [label="Step 8: Present"];

  setup -> inspect;
  inspect -> context;
  inspect -> dataproc [style=dashed];
  context -> clarify;
  clarify -> dataproc;
  clarify -> diag [style=dashed];
  dataproc -> diag;
  diag -> judge;
  judge -> diag [label="⟳ max3" style=dashed];
  judge -> report;
  report -> review;
  review -> repair [label="CONDITIONAL/\nREJECTED"];
  repair -> diag [label="re-diagnose" style=dashed];
  review -> present [label="ENDORSED"];
}
```

Steps 2-3 run in parallel. Step 2.5 synchronizes. Steps 4→5→6→7 run sequentially. Step 7.5 repair loop (max 2 iterations).

## Agent Decoupling

Agents communicate only through workspace files — never through the main agent's context:

```
Context Builder ──► 01_ontology/ontology.json, schema.json
                ──► 00_input/clarification_needed.json
User Clarification ──► Updated ontology.json, schema.json
Data Processor  ──► 02_processed/feature_summary.json
                ──► 02_processed/validate_report.json
                ──► 03_figures/*.png + plot_manifest.json
Diagnostician   ──► 04_diagnostics/diagnosis.json, evidence.json, confidence.json
                ──► 04_diagnostics/reasoning_chain.json
Judge           ──► 05_review/judge_feedback.json
Reporter        ──► report.md, run_summary.json
Report Reviewer ──► optimizer.md
```

## Evidence Hierarchy

| Rank | Source | Label |
|------|--------|-------|
| 1 | Direct measurements in data | [Evidence Rank 1] |
| 2 | User-provided documentation | [Evidence Rank 2] |
| 3 | Statistical analysis (incl. validation report) | [Evidence Rank 3] |
| 4 | Visual evidence from charts | [Evidence Rank 4] |
| 5 | Established process logic / domain knowledge | [Evidence Rank 5] |
| 6 | External web references | [Evidence Rank 6] [EXTERNAL] |
| 7 | Hypotheses (unsupported) | [Evidence Rank 7] |

Every conclusion is limited by its weakest evidence rank. Statistical evidence (Rank 3) includes validation status — a correlation that fails validation checks carries less weight than one that passes.

## Anti-Speculation Rules

To claim "X caused Y", all five criteria must be met:
1. **Temporal precedence** — X changed before Y, with measured lag and verified time-sorting
2. **Statistical significance** — strong correlation (|r| > 0.7) at the correct lag
3. **Lag window consistency** — correlation persists across adjacent lags, not an isolated spike
4. **Physical mechanism** — a quantitative explanation from process physics/chemistry, with magnitude check
5. **No contradictions** — no contradicting evidence, including within subgroups (no Simpson's Paradox)

If any criterion is missing, use [HYPOTHESIS] language instead of causal language.

Additional constraints:
- Lag correlations require verified time-sorted data — if sorting is unconfirmed, this must be disclosed as a limitation
- Aggregate correlations must be checked within subgroups — a correlation that reverses direction in the dominant subgroup is not reliable
- Raw correlations with time trends must be compared against detrended correlations — attenuation above 50% indicates trend confounding
- Parameter physical meanings must be confirmed — unknown meanings must go through the clarification gate, and unresolved parameters carry a [PARAM_AMBIGUITY] marker
- Granger causality results are only valid when sorting validation passes

Always disclose confidence level, evidence gaps, and assumptions. Present the single best-supported conclusion, not a menu of possibilities.

## Reference Files

Read these files when their domain knowledge is needed — they are not loaded automatically:

### Pipeline & Methods (load during execution)
- **`pipeline-execution.md`** — Step-by-step protocol, artifact chain, validation framework, repair loops, and common mistakes. Read before starting any pipeline step.
- **`resources/diagnosis_method.md`** — Diagnostic process phases 0-5, statistical thresholds, confidence adjustment protocol. Read when forming diagnostic hypotheses.
- **`resources/evidence_rules.md`** — Evidence hierarchy (ranks 1-7), causation criteria, language templates, confidence scoring. Read when evaluating evidence quality.

### Domain Knowledge (load when needed)
- **`resources/process_knowledge_base.md`** — Common industrial processes, failure modes, physical mechanisms. Read when researching potential mechanisms for a hypothesis.
- **`resources/script_and_toolkit_reference.md`** — Script usage, CLI flags, input/output formats for all tools in `scripts/`. Read when invoking pipeline scripts.

### Agents (spawn as sub-agents)
- **`agents/context-builder.md`** — Build process ontology from data + user input
- **`agents/data-processor.md`** — Statistical analysis + visualization generation
- **`agents/diagnostician.md`** — Hypothesis formation + root cause convergence
- **`agents/judge.md`** — Quality gate: cross-reference diagnosis against validation report
- **`agents/reporter.md`** — Generate the final diagnostic report
- **`agents/report-reviewer.md`** — Physical truth audit of the final report

### Schemas & Templates (validate against these)
- **`schemas/*.json`** — JSON Schema draft-07 for all pipeline outputs. Validate outputs with `validate.mjs` before marking steps complete.
- **`templates/report_template.md`** — Final report structure with Root Cause Convergence sections.
- **`templates/*.json`** — Output templates for diagnosis, evidence, confidence, and judge feedback.

### Examples (reference for first-time setup)
- **`examples/{reactor_temperature,heat_exchanger_fouling,bopet_film_thickness}/`** — Domain-specific sample ontologies and configs. Read when setting up a new diagnostic domain.
