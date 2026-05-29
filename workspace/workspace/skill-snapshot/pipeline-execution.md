# Pipeline Execution Reference

> Detailed execution flow for the Industrial Deep Diagnostic pipeline.
> **Authoritative reference for sub-agent orchestration.** SKILL.md is the entry point; this file contains the detailed per-step protocol.

## Contents

- [Execution Flow](#execution-flow) — Pipeline DAG and parallelism rules
- [File Artifact Chain](#file-artifact-chain) — Agent output file paths
- [Pipeline Event Log](#pipeline-event-log) — Event logging format
- [Step-by-Step Protocol](#step-by-step-protocol) — Steps 0-8 with commands
- [Statistical Validation Framework](#statistical-validation-framework) — All validation checks and confidence adjustment rules
- [New Statistical Methods (v4.3)](#new-statistical-methods-v43) — MI, Granger, change points, interactions
- [Clarification Gate Protocol](#clarification-gate-protocol-new--step-25) — Step 2.5 user interaction flow
- [Diagnosis Language](#diagnosis-language) — Marker templates
- [Common Mistakes](#common-mistakes) — Pitfalls and fixes

## Execution Flow

```dot
digraph diagnostic_flow {
  rankdir=TB;
  node [shape=box];

  setup [label="Step 0: Setup\nnode setup.mjs"];
  inspect [label="Step 1: Inspect Data\nnode inspect.mjs\n(ask user questions)"];
  context [label="Step 2: Context Build\nspawn context-builder"];
  clarify [label="Step 2.5: Clarification Gate\nAskUserQuestion\n(unknown parameters)" shape=diamond];
  dataproc [label="Step 3: Data + Viz + Validate\nspawn data-processor\n(includes stats_validate.mjs)"];
  diag [label="Step 4: Diagnose\nspawn diagnostician\n(reads validate_report.json)"];
  judge [label="Step 5: Judge\nspawn judge\n(cross-refs validate_report.json)"];
  report [label="Step 6: Report\nspawn reporter\n(includes validation section)"];
  review [label="Step 7: Physical Audit\nspawn report-reviewer\n(independent verification)"];
  repair [label="Step 7.5: Review Repair\nfix issues found by reviewer" shape=diamond];
  present [label="Step 8: Present\n(main agent)"];

  setup -> inspect;
  inspect -> context;
  inspect -> dataproc [style=dashed label="parallel"];
  context -> clarify;
  clarify -> dataproc [label="ontology\nenriched"];
  clarify -> diag [style=dashed label="enriched\ncontext"];
  dataproc -> diag;
  diag -> judge;
  judge -> diag [label="repair (max 3)" style=dashed];
  judge -> report [label="pass/warn"];
  report -> review;
  review -> repair [label="CONDITIONAL/\nREJECTED"];
  repair -> diag [label="re-diagnose\nwith fixes" style=dashed];
  review -> present [label="ENDORSED"];
}
```

**Parallelism**: Steps 2 and 3 run in parallel. Steps 4→5→6→7 are sequential (each depends on previous output). Step 2.5 is a synchronization gate — Step 3 and Step 4 both depend on enriched ontology from the clarification step.

## File Artifact Chain

```
Context Builder ──► 01_ontology/ontology.json, schema.json
                ──► 00_input/clarification_needed.json   (NEW)
                ──► 00_input/extracted_knowledge.json
User Clarification ──► Updated ontology.json, schema.json (enriched)
Data Processor  ──► 02_processed/feature_summary.json (enhanced stats)
                ──► 02_processed/validate_report.json   (statistical validation)
                ──► 03_figures/*.png + plot_manifest.json
Diagnostician   ──► 04_diagnostics/diagnosis.json, evidence.json, confidence.json
Judge           ──► 05_review/judge_feedback.json
Reporter        ──► report.md, run_summary.json
Report Reviewer ──► optimizer.md
```

## Pipeline Event Log

Each agent MUST append a JSON line to `RUN_DIR/.pipeline_events.jsonl` at start and completion:

```jsonl
{"event": "agent_start", "agent": "context-builder", "timestamp": "2026-05-25T10:00:00Z", "pid": 12345}
{"event": "agent_complete", "agent": "context-builder", "timestamp": "2026-05-25T10:02:30Z", "files_written": ["01_ontology/ontology.json", "01_ontology/schema.json", "00_input/clarification_needed.json"], "clarifications_requested": 3, "clarifications_resolved": 2, "errors": null}
{"event": "clarification_gate", "agent": "main", "timestamp": "2026-05-25T10:03:00Z", "parameters_asked": 3, "parameters_resolved": 2, "rounds": 1}
```

The main agent should verify this file exists and log its own events at Step 8.

## Step-by-Step Protocol

### Step 0: Setup Workspace

```bash
node <skill_path>/scripts/setup.mjs --name <scene_name> --base-dir ./workspace/diagnostic-runs
```

Creates `workspace/diagnostic-runs/<timestamp>_<name>/` with subdirs: `00_input/`, `01_ontology/`, `02_processed/`, `03_figures/`, `04_diagnostics/`, `05_review/`, `06_scripts/`.

### Step 1: Inspect Data (MAIN)

```bash
node <skill_path>/scripts/inspect.mjs <data_path>
```

Auto-routes: CSV/TSV/JSON → Node.js native; Excel/Parquet/Feather → `file_inspect.py`. Files >100K rows get sampled. Output: column names, types, stats, time column detection, preview.

Then ask user clarification questions (max 5). Save `input_manifest.json` and `user_context.json` to `00_input/`.

**Key questions to ask:**
1. What is the process type and what are the main production stages?
2. What are the known quality issues or defect types?
3. Are there product grade/recipe changes in the data? Which column identifies them?
4. What parameters have known physical meanings? Which are proprietary/unknown?
5. What key intermediate variables are NOT measured (known data gaps)?

### Step 2: Context Building (SUB-AGENT)

Read `agents/context-builder.md` and spawn. Pass: DATA_PATH, RUN_DIR, REFERENCE_DIR, PROCESS_DESCRIPTION, USER_OBJECTIVE, SKILL_PATH. Writes to `01_ontology/`.

The Context Builder now:
- Searches references and web for parameter meanings
- Infers physical meanings from column name patterns and value ranges
- Identifies parameters with unknown physical meanings
- Scores their importance (CRITICAL/HIGH/MEDIUM/LOW)
- Outputs `00_input/clarification_needed.json`
- Uses AskUserQuestion for CRITICAL and HIGH importance unknowns
- Updates ontology with user-provided physical meanings

### Step 2.5: Clarification Gate (MAIN — NEW)

**This is a new synchronization gate.** After the Context Builder completes, the main agent checks `00_input/clarification_needed.json`.

**If CRITICAL or HIGH importance parameters need clarification:**

1. Read `clarification_needed.json` to understand what's unknown
2. Use AskUserQuestion to present unknown parameters to the user
3. Group related parameters into single questions (max 4 questions per round)
4. Provide the Context Builder's best guesses — the user can confirm or correct
5. After receiving answers, update the ontology files:
   - Update `01_ontology/ontology.json` with confirmed physical meanings
   - Update `01_ontology/schema.json` with confirmed units and roles
   - Mark parameters as resolved in `clarification_needed.json`
6. If HIGH-importance parameters remain, consider a second round
7. Log the clarification event to `.pipeline_events.jsonl`

**If no critical unknowns exist**, proceed directly to Step 3/4.

**Protocol for AskUserQuestion in clarification gate:**

```
For each group of related unknown parameters:
  - State the column name and our best guess at physical meaning
  - Show the value range observed in the data
  - Ask: what does this parameter physically represent?
  - Ask: what is its unit?
  - Ask: is it a setpoint or measured value?
  
Use the "Other" option to allow free-text detailed explanations.
```

**After clarification:**
- The enriched ontology now flows to BOTH the Data Processor (Step 3) and Diagnostician (Step 4)
- Parameters that remain unknown after clarification are marked with `"physical_meaning_confidence": "unknown"`
- The Diagnostician and Report Reviewer will apply confidence penalties to conclusions based on unknown parameters

### Step 3: Data Processing + Visualization + Statistical Validation (SUB-AGENT)

Read `agents/data-processor.md` and spawn.

**Workflow:**
1. Inspect data, classify pattern
2. Preprocess + validate data sorting
3. Run enhanced `stats.mjs` (Pearson, Spearman, detrended, full CCF, stratified, mutual information)
4. Run `stats_validate.mjs` (Simpson's Paradox, confounders, outlier sensitivity, change point detection)
5. Select visualization primitives (including statistical validation plots)
6. Compose and run visualization script
7. Write `plot_manifest.json`

**Mandatory outputs:**
- `02_processed/feature_summary.json` — Raw statistics (now includes mutual information + Granger causality)
- `02_processed/validate_report.json` — Statistical validation report (now includes change point detection)
- Statistical validation plots when issues detected
- `03_figures/plot_manifest.json` — Interface contract for diagnostician

### Step 4: Diagnosis (SUB-AGENT)

Read `agents/diagnostician.md` and spawn.

**Critical sequence — Data-Driven, Parameter-Matched Diagnosis:**

The Diagnostician does NOT use a preset checklist. It adapts its analysis to the actual data:

1. **Classify parameters first**: Separate process parameters (cause candidates) from quality metrics (effect targets) using column name heuristics. Only parameters classified as "process" can be root cause candidates for quality problems.

2. **Match by time offset**: For each process-quality pair, compute CCF to find the optimal lag. A process change at time T affects quality at time T+lag. The Diagnostician uses the lag-shifted correlation — not the concurrent (lag=0) correlation — as the basis for causal claims.

3. **Read validation report BEFORE forming hypotheses**: Statistical issues (Simpson's Paradox, trend confounding, outlier sensitivity, change points) must be identified and confidence-adjusted BEFORE hypothesis construction begins.

4. **Select analysis methods adaptively**: Based on data dimensionality, column classification, and statistical triggers:
   - 1D scalar data → timeseries panels, correlation heatmaps, normalized overlays, lag sensitivity curves
   - Multi-axis data → add orbit plots, axis ratios
   - 2D profile data → add profile evolution heatmaps, deviation maps
   - Batch/event data → add per-batch box plots, event timelines
   - Time-matched P→Q data → add dual timelines, multi-lag heatmaps, lag-shifted overlays, rolling correlations

5. **Every causal claim must cite**: (a) which process parameter, (b) which quality metric, (c) the time offset (lag), (d) the correlation strength at that lag, (e) the statistical validation status, (f) the evidence rank.

**Prohibited:**
- "Parameter X is correlated with defects" — too vague. Must specify: which defect, at what lag, with what r value.
- "The data shows..." without citing specific columns and values.
- Drawing conclusions from concurrent (lag=0) correlation when CCF shows the peak at a different lag.
- **Ending with a list of hypotheses.** The pipeline converges to a SINGLE most probable root cause. Hypotheses that survive elimination are synthesized — not listed as a menu of options.

**After completion, the Diagnostician produces:**
- `04_diagnostics/reasoning_chain.json` — 8-step reasoning trace + convergence analysis
- `04_diagnostics/diagnosis.json` — Single root cause conclusion with integrated data+physics+logic chain
- `04_diagnostics/evidence.json` — All evidence cited with ranks and validation status
- `04_diagnostics/confidence.json` — 3-dimension confidence breakdown (Data 35 + Physics 35 + Logic 30)

**After completion, run schema validation:**
```bash
node <skill_path>/scripts/validate.mjs \
  <skill_path>/schemas/diagnosis_schema.json \
  RUN_DIR/04_diagnostics/diagnosis.json
node <skill_path>/scripts/validate.mjs \
  <skill_path>/schemas/evidence_schema.json \
  RUN_DIR/04_diagnostics/evidence.json
node <skill_path>/scripts/validate.mjs \
  <skill_path>/schemas/confidence_schema.json \
  RUN_DIR/04_diagnostics/confidence.json
```

### Step 5: Judge Review (SUB-AGENT)

Read `agents/judge.md` and spawn. Scores 10 criteria (weighted).

**Repair loop:**
1. PASS (score >= 90) → proceed to Step 6
2. NEEDS_REPAIR (70-89) → Re-spawn diagnostician with REPAIR_INSTRUCTIONS. Max 3 iterations.
3. FAIL (< 70) → report to user with feedback

**Score ceiling**: Score cannot exceed 85 if data is not time-sorted AND lag correlations are used as primary evidence.

### Step 6: Report (SUB-AGENT)

Read `agents/reporter.md` and spawn.

**Mandatory Section 13**: Statistical Validation & Confidence Assessment — transparent disclosure of sorting validation, Simpson's Paradox findings, trend confounding, and adjusted confidence table.

### Step 7: Physical Truth Audit (SUB-AGENT)

Read `agents/report-reviewer.md` and spawn.

Independent verification with actual Python code execution. Quantitative physical mechanism checks (Arrhenius kinetics, mass transfer rates, etc.). Direct data inspection — distrusts pipeline summaries.

Output: `optimizer.md` with verdict ENDORSED / CONDITIONAL / REJECTED.

### Step 7.5: Review Repair Loop (NEW)

**If the Report Reviewer returns CONDITIONAL or REJECTED verdict:**

The issues found by the reviewer are different from the Judge's issues:
- Judge checks: internal consistency, statistical rigor, evidence usage
- Reviewer checks: physical plausibility, real-world truth, quantitative mechanism verification

**Repair protocol:**
1. Read `optimizer.md` for specific concerns and correction requirements
2. For each FATAL or SERIOUS concern:
   - If it's a physical mechanism error → re-spawn Diagnostician with REPAIR_INSTRUCTIONS containing the reviewer's physical critique
   - If it's a missing confounder → re-spawn Data Processor with additional stratification instructions
   - If it's a parameter meaning issue → return to clarification gate (Step 2.5) if parameter meanings are still unknown
3. After re-diagnosis, re-run Judge (Step 5), Reporter (Step 6), and Reviewer (Step 7)
4. Maximum 2 review repair iterations

### Step 8: Present Results (MAIN)

Before presenting, run the artifact integrity check:

```bash
node <skill_path>/scripts/artifact-check.mjs <run_dir> <skill_path>
```

Review the check output. If any critical artifacts are missing, note them to the user.

Show user: executive summary, key findings, diagnosis, recommendations, workspace path. Verify report.md has embedded images. If `optimizer.md` verdict is CONDITIONAL or REJECTED, highlight concerns prominently and present the validation findings.

---

## Statistical Validation Framework

The pipeline includes a comprehensive statistical validation layer that runs BEFORE diagnosis:

| Check | Tool | What It Catches |
|-------|------|----------------|
| Data sorting validation | `stats.mjs` | Lag analysis on batch-sorted data → spurious lag correlations |
| Simpson's Paradox | `stats.mjs` + `stats_validate.mjs` | Aggregate correlations that reverse within subgroups |
| Time-trend confounding | `stats.mjs` | Correlations driven by shared time drifts, not direct coupling |
| Outlier sensitivity | `stats_validate.mjs` | Correlations dominated by a few extreme batches |
| Spearman-Pearson divergence | `stats.mjs` | Outlier or non-linear influence on Pearson correlations |
| Lag window consistency | `stats.mjs` | Isolated spikes in CCF (artifact indicators) |
| Multiple testing correction | `stats.mjs` | Chance "significant" results from many comparisons |
| **Mutual Information** | `stats.mjs` (NEW) | Non-linear dependencies that Pearson/Spearman miss |
| **Granger Causality** | `stats.mjs` (NEW) | Temporal predictive causality (requires time-sorted data) |
| **Change Point Detection** | `stats_validate.mjs` (NEW) | Regime shifts that invalidate stationarity assumptions |
| **Interaction Effects** | `stats.mjs` (NEW) | Parameter combinations with synergistic effects on quality |

### Confidence Adjustment Rules

| Validation Finding | Confidence Impact |
|--------------------|:---:|
| Data NOT time-sorted + lag used as evidence | -25 to -40 points |
| Simpson's Paradox (direction reversal) | -20 to -30 points |
| Simpson's Paradox (moderate attenuation) | -10 to -15 points |
| Trend confounding (attenuation > 50%) | -15 to -20 points |
| Outlier-driven correlation | -10 to -15 points |
| Spearman-Pearson divergence > 0.15 | -5 to -10 points |
| Isolated lag spike (not consistent window) | Treat as concurrent only |
| **Parameter physical meaning unknown** (NEW) | **-15 to -25 points** |
| **Change point detected in analysis window** (NEW) | **-10 to -20 points** |
| **Granger causality contradicts correlation direction** (NEW) | **-20 to -30 points** |

---

## New Statistical Methods (v4.3)

### Mutual Information

Measures non-linear dependency between parameter pairs. Computed via k-nearest neighbor estimation. Catches relationships that Pearson (linear) and Spearman (monotonic) miss entirely.

Usage: `node stats.mjs ...` — included automatically in feature_summary.json.

### Granger Causality

Tests whether past values of parameter X help predict parameter Y beyond what past values of Y alone can predict. Uses F-test on restricted vs unrestricted VAR models.

**Critical**: Only valid when data IS time-sorted. The sorting validation check MUST pass before Granger results are used.

### Change Point Detection

Identifies structural breaks in the time series using PELT (Pruned Exact Linear Time) algorithm. Detects regime shifts that may explain apparent correlations as artifacts of operating mode changes.

### Interaction Effects

For parameter pairs with weak individual correlations but strong combined effects: computes interaction terms (X1 × X2) and tests against quality metrics. Catches synergistic failure modes.

---

## Clarification Gate Protocol (NEW — Step 2.5)

The physical meaning of parameters is foundational to valid diagnosis. An incorrect assumption about what a parameter measures can invalidate the entire analysis.

### When to Ask

Ask the user when:
1. Parameter has CRITICAL or HIGH importance (high variance, strong correlations, part of key parameter group)
2. Physical meaning could not be determined from references, web, or column name inference
3. The parameter appears in multiple causal hypotheses

### How to Ask

1. **Group related parameters** — ask about a group of casting parameters together rather than one at a time
2. **Provide your best guess** — the user can confirm or correct, which is faster than explaining from scratch
3. **Show the data** — include value ranges and units guess so the user can verify against their knowledge
4. **Be specific** — ask about physical quantity, unit, setpoint vs measured, and normal range
5. **Respect the user's time** — maximum 4 questions per round, 2 rounds maximum

### What to Do With Answers

1. Immediately update ontology.json and schema.json
2. Re-save files so downstream agents use enriched context
3. Log the clarification event for traceability

### When to Proceed Without Answers

If the user cannot or will not provide clarification after 2 rounds:
- Mark parameters as `"physical_meaning_confidence": "unknown"`
- Proceed with the pipeline
- The Diagnostician and Report Reviewer will apply appropriate confidence penalties

---

## Diagnosis Language

| Type | Marker | Template |
|------|--------|----------|
| Observation | [OBSERVATION] | "[Variable] [changed] by [X%] from [T1] to [T2]." |
| Inference | [INFERENCE] | "This coincides with [event/measurement]." |
| Hypothesis | [HYPOTHESIS] | "This suggests [mechanism] may have contributed." |
| Uncertainty | [UNCERTAINTY] | "Evidence is [level] to [conclude X]." |
| Validation Finding | [VALIDATION] | "Statistical validation check [X] found [Y]. Confidence adjusted from [A] to [B]." |
| **Parameter Ambiguity** (NEW) | [PARAM_AMBIGUITY] | "Parameter [X] physical meaning is [unknown/uncertain]. Conclusions based on this parameter are [confidence level]." |

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Using lag correlations on non-time-sorted data | `stats.mjs` now validates sorting; check `sorting_validation.time_sorted` before any lag claim |
| Missing Simpson's Paradox | `stats.mjs` stratified analysis + `stats_validate.mjs` automatically detect subgroup reversals |
| Confusing trend correlation with causal coupling | Detrended correlations now computed automatically; check `attenuation_pct` |
| Trusting Pearson for heavily skewed defect data | Spearman now computed alongside Pearson; check divergence |
| Stating "X caused Y" without all 4 criteria | Use [HYPOTHESIS] marker instead |
| Skipping `plot_manifest.json` | Data-processor MUST write it — diagnostician depends on it |
| Main agent holding domain context | Spawn sub-agents; main agent only orchestrates |
| Skipping Step 7 (physical audit) | Always run — catches spurious correlations the Judge misses |
| Not validating parameter physical meaning | **Context Builder now uses AskUserQuestion for unknown parameters** |
| Python dependency missing in Step 7 | Reviewer should run `pip3 install -r <skill_path>/scripts/requirements.txt` before independent verification |
| **Proceeding with unknown parameter meanings** (NEW) | **Use the clarification gate (Step 2.5). Unknown parameters → lower confidence, potentially wrong diagnosis** |
| **Ignoring Reviewer's physical concerns** (NEW) | **Step 7.5 repair loop: re-diagnose with reviewer's corrections, not just Judge's** |

## Reference Files

- **Script & toolkit details**: `resources/script_and_toolkit_reference.md`
- **Evidence rules**: `resources/evidence_rules.md`
- **Diagnosis methodology**: `resources/diagnosis_method.md`
- **Process knowledge base**: `resources/process_knowledge_base.md`
- **Agent prompts**: `agents/*.md` (read when spawning each agent)
- **Schemas**: `schemas/*.json` (normative — agents validate against these)
- **Templates**: `templates/*.md`, `templates/*.json`
- **Examples**: `examples/{reactor_temperature,heat_exchanger_fouling,bopet_film_thickness}/`
