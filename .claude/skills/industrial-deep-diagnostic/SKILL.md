---
name: industrial-deep-diagnostic
description: "Use when the user provides industrial, process, or manufacturing time-series data (CSV, XLSX, Parquet) and asks about anomalies, root causes, quality issues, equipment faults, or process diagnostics. Also triggers on: anomaly detection, root cause analysis, fault diagnosis, sensor data analysis, equipment health, SPC, statistical process control, 工业诊断, 过程分析, 异常检测, 根因分析, 质量分析, 故障诊断, 传感器数据. Do NOT trigger for: simple data visualization, general statistics homework, financial time-series, or non-industrial data."
commands:
  - industrial-deep-diagnostic
  - industrial-deep-diagnostic analyze
  - industrial-deep-diagnostic review
  - industrial-deep-diagnostic report
  - industrial-deep-diagnostic audit
version: 6.1.0
---

# Industrial Deep Diagnostic

## Language Default

**默认输出语言为中文。** 报告、诊断结论、审计文档使用中文。JSON enum字段保持英文。

## Core Principle

Diagnosis is elimination, not confirmation. Every conclusion needs: (1) temporal precedence, (2) statistical evidence, (3) physical mechanism, (4) no contradictions. Missing any → label as [HYPOTHESIS]. When data cannot discriminate between competing hypotheses → output COMPETING_SET, not a guess.

## Loading Guide — What to Read and When

This skill uses progressive loading. Read only what each step needs:

| When | Read | Why |
|------|------|-----|
| Pipeline start | This file (SKILL.md) | Orchestration protocol, step sequence |
| Before Step 2 | `agents/context-builder.md` | Instructions for the context-building sub-agent |
| Before Step 3 | `agents/data-processor.md` | Instructions for data processing + visualization |
| Before Step 4 | `agents/diagnostician.md` | Instructions for competing hypotheses diagnosis |
| Before Step 5 | `agents/judge.md` | Instructions for quality gate review |
| Before Step 6 | `agents/reporter.md` | Instructions for report generation |
| Before Step 7 | `agents/report-reviewer.md` | Instructions for physical truth audit |
| During repair loops | `pipeline-execution.md` §Repair Loop Protocol | Detailed repair counter rules |
| During diagnosis | `resources/evidence_rules.md` | Evidence rank definitions |
| During diagnosis | `resources/diagnosis_method.md` | Diagnostic methodology reference |
| During diagnosis | `resources/process_knowledge_base.md` | Domain knowledge by process type |
| After each agent | `schemas/*.json` matching output | Validate JSON outputs |

**Do NOT load everything upfront.** Each agent prompt is self-contained — read it only when that step begins.

---

## Execution Flow

```
Step 0: Setup ──► Step 1: Inspect ──► Step 2: Context ──[clarify?]──┐
                                     └──► Step 3: Data+Viz+Validate ──┤
                                                                       ▼
                                                                 Step 4: Diagnostician
                                                                       │
                                                                 ┌─────▼─────┐
                                                                 │ Step 5:   │◄── repair max 3 ─┐
                                                                 │ Judge     │                    │
                                                                 └─────┬─────┘                    │
                                                                       │ pass/warn               │
                                                                       ▼                         │
                                                                 Step 6: Report                │
                                                                       │                         │
                                                                       ▼                         │
                                                                 ┌─────▼──────┐                  │
                                                                 │ Step 7:    │── re-diagnose ───┘
                                                                 │ Audit      │
                                                                 └─────┬──────┘
                                                                       │ ENDORSED
                                                                       ▼
                                                                 Step 8: Present
```

**Parallelism**: Steps 2 and 3 can run in parallel. Step 2.5 (clarification gate) synchronizes before Step 3. Steps 4→5→6→7 are sequential.

**Repair loops**: Judge→Diagnostician repair max 3 iterations. Reviewer repair (Step 7.5) max 2 cycles. **Global cap: total re-diagnosis ≤ 5**. See `pipeline-execution.md` §Repair Loop Protocol for counter persistence rules.

---

## Step-by-Step Protocol

### Step 0: Setup Workspace + Python Environment

```bash
SKILL_PATH="<path-to-this-skill>"
PROJECT_ROOT="$(cd "$SKILL_PATH/../.." && pwd)"

# Step 0a: Create run directory structure
node "$SKILL_PATH/scripts/setup.mjs" --name <scene_name> --base-dir "$PROJECT_ROOT/workspace/diagnostic-runs"

# Step 0b: Ensure Python venv is ready (auto-installs uv + deps)
node "$SKILL_PATH/scripts/uv_env_setup.mjs"
```

Creates `<timestamp>_<name>/` with subdirs `00_input/` through `06_scripts/`. Also ensures the uv-managed Python venv exists with all dependencies (matplotlib, numpy, pandas, seaborn, scipy, openpyxl, pyarrow). Copy input data files into `00_input/`.

**Python execution rule (ZERO TOLERANCE)**: All subsequent Python script invocations MUST use the venv Python at `scripts/.venv/bin/python`. NEVER use system `python3`, `python3.11`, or `pip3`. Get the path: `node scripts/uv_env_setup.mjs` → parse JSON `.python` field. Violating this rule causes dependency pollution and version conflicts.

### Step 1: Inspect Data (Main Agent)

```bash
node "$SKILL_PATH/scripts/inspect.mjs" <data_path>
```

Inspect all input files. Ask user up to 5 clarification questions about process type, quality issues, known parameters. Save `input_manifest.json` and `user_context.json` to `00_input/`.

### Step 2: Context Build (Sub-Agent)

**Read first**: `agents/context-builder.md`

Pass: `DATA_PATH`, `RUN_DIR`, `REFERENCE_DIR`, `PROCESS_DESCRIPTION`, `USER_OBJECTIVE`, `SKILL_PATH`.

The agent builds ontology from data + references, identifies unknown parameters, and outputs to `01_ontology/`. If CRITICAL parameters have unknown physical meanings, it creates `00_input/clarification_needed.json`.

### Step 2.5: Clarification Gate (Main Agent)

Check `00_input/clarification_needed.json`. If CRITICAL/HIGH unknowns exist, ask the user. Update ontology with confirmed meanings. If no unknowns, proceed.

### Step 3: Data Processing + Visualization + Validation (Sub-Agent)

**Read first**: `agents/data-processor.md`

Pass: `DATA_PATH`, `RUN_DIR`, `SKILL_PATH`.

> **Python Execution (MANDATORY)**: All Python scripts in this step (stats_validate.mjs internal calls, `file_inspect.py`, `template_visualize.py`, `template_preprocess.py`, and the generated `RUN_DIR/06_scripts/visualize.py`) MUST use the uv venv Python at `scripts/.venv/bin/python`. Never `python3`. See §Python Execution Protocol in CLAUDE.md.

The agent runs the full analysis pipeline:
1. Classify process scenario (CNC / continuous / batch / heat exchange / generic)
2. Run `stats.mjs` → `feature_summary.json`
3. Run `stats_validate.mjs` → `validate_report.json`
4. Run anomaly detection → `anomaly_report.json`
5. Build causal evidence map → `causal_evidence_map.json`
6. Generate scenario-adaptive visualizations → `03_figures/*.png`

Key outputs consumed by Step 4:
- `02_processed/feature_summary.json` — validated correlations
- `02_processed/validate_report.json` — Simpson's Paradox, trend confounding, outlier flags
- `02_processed/anomaly_report.json` — anomaly intervals, thresholds, transition events
- `02_processed/causal_evidence_map.json` — validated causal graph with root cause candidates
- `03_figures/plot_manifest.json` + `image_captions.json` — figure descriptions with diagnostic implications

### Step 4: Diagnostician — Competing Hypotheses (Sub-Agent)

**Read first**: `agents/diagnostician.md`

Pass: `RUN_DIR`, `SKILL_PATH`, `DATA_PATH`, optional `REPAIR_INSTRUCTIONS`.

The Diagnostician follows three phases then a 5-step protocol:
1. **Phase 1: Data Probing** — Probe raw data at transition points (tool changes, material switches). Check: does quality reset when a component is replaced?
2. **Phase 2: Product-Stratified Analysis** — Verify correlations hold within each product group. Remove BETWEEN_PRODUCT_ONLY correlations.
3. **Phase 3: 5-Step Protocol**:
   - **Step A**: Generate hypotheses with quantitative physical logic chains + visual evidence
   - **Step B**: Cross-check with data probes, anomaly intervals, causal evidence map
   - **Step C**: Discriminability assessment (enhanced with transition analysis)
   - **Step D**: Exclusion using physical impossibility + data probe contradictions
   - **Step E**: DETERMINED / COMPETING_SET / NEEDS_DATA

Schema-validate outputs:
```bash
node "$SKILL_PATH/scripts/validate.mjs" "$SKILL_PATH/schemas/diagnosis_schema.json" "$RUN_DIR/04_diagnostics/diagnosis.json"
node "$SKILL_PATH/scripts/validate.mjs" "$SKILL_PATH/schemas/evidence_schema.json" "$RUN_DIR/04_diagnostics/evidence.json"
node "$SKILL_PATH/scripts/validate.mjs" "$SKILL_PATH/schemas/confidence_schema.json" "$RUN_DIR/04_diagnostics/confidence.json"
```

### Step 5: Judge Review (Sub-Agent)

**Read first**: `agents/judge.md`

Scores 10 criteria. Cross-references diagnosis against `validate_report.json`.
- **PASS** (≥90) → proceed to Step 6
- **NEEDS_REPAIR** (70-89) → re-spawn Diagnostician with REPAIR_INSTRUCTIONS. Max 3 iterations.
- **FAIL** (<70) → report to user

### Step 6: Report Generation (Sub-Agent)

**Read first**: `agents/reporter.md`

Generates `report.md` with mandatory sections: Executive Summary, Statistical Findings, Diagnostic Findings, Competing Hypotheses Disclosure, Confidence Assessment, Limitations, Recommendations.

### Step 7: Physical Truth Audit (Sub-Agent)

**Read first**: `agents/report-reviewer.md`

Independent verification with quantitative physical checks. Output: `optimizer.md` with verdict ENDORSED / CONDITIONAL / REJECTED.

If CONDITIONAL or REJECTED → repair loop (max 2 cycles, each re-runs Steps 4→5→6→7).

### Step 8: Present Results (Main Agent)

```bash
node "$SKILL_PATH/scripts/artifact-check.mjs" "$RUN_DIR" "$SKILL_PATH"
```

Show user: executive summary, key findings, diagnosis type, confidence, recommendations, workspace path. Highlight any CONDITIONAL/REJECTED concerns from reviewer.

---

## Agent Decoupling

Agents communicate ONLY through workspace files — never through the main agent's context:

```
Context Builder ──► 01_ontology/ontology.json, schema.json
                ──► 00_input/clarification_needed.json
User Clarification ──► Updated ontology.json, schema.json
Data Processor  ──► 02_processed/feature_summary.json, validate_report.json
                ──► 02_processed/scenario_classification.json, anomaly_report.json, causal_evidence_map.json
                ──► 03_figures/*.png + plot_manifest.json + image_captions.json
Diagnostician   ──► 04_diagnostics/diagnosis.json, evidence.json, confidence.json, reasoning_chain.json
Judge           ──► 05_review/judge_feedback.json
Reporter        ──► report.md, run_summary.json
Report Reviewer ──► optimizer.md
```

---

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

Every conclusion limited by its weakest evidence rank.

---

## Anti-Speculation Rules

- NEVER claim lag correlation as causal if data is not time-sorted
- NEVER claim aggregate correlation if it reverses in the dominant subgroup (Simpson's Paradox)
- NEVER cite raw correlation without checking detrended when both variables trend with time
- NEVER assume parameter physical meaning — if unknown, use clarification gate
- NEVER assign high confidence without checking if alternatives predict the same observables
- ALWAYS output COMPETING_SET when data cannot discriminate between hypotheses
- ALWAYS specify what discriminating data would resolve ambiguity
- **Confidence ceiling 65 for INDISTINGUISHABLE competing hypotheses**
- ALWAYS disclose confidence, evidence gaps, and assumptions

---

## Commands

| Command | Action |
|---------|--------|
| `/industrial-deep-diagnostic` | Full pipeline (Steps 0-8) |
| `/industrial-deep-diagnostic analyze` | Skip intake, run from Step 2 |
| `/industrial-deep-diagnostic review` | Re-run judge on existing results |
| `/industrial-deep-diagnostic report` | Regenerate report from existing artifacts |
| `/industrial-deep-diagnostic audit` | Run report-reviewer only (generates optimizer.md) |

---

## Reference Files

| File | When to Load | Content |
|------|-------------|---------|
| `pipeline-execution.md` | During repair loops | Detailed repair protocol, validation framework, change-point verification |
| `agents/context-builder.md` | Before Step 2 | Context-building agent instructions |
| `agents/data-processor.md` | Before Step 3 | Data processing + visualization agent instructions |
| `agents/diagnostician.md` | Before Step 4 | Competing hypotheses diagnosis instructions |
| `agents/judge.md` | Before Step 5 | Judge quality gate instructions |
| `agents/reporter.md` | Before Step 6 | Report generation instructions |
| `agents/report-reviewer.md` | Before Step 7 | Physical truth audit instructions |
| `resources/evidence_rules.md` | During Step 4 | Evidence hierarchy details |
| `resources/diagnosis_method.md` | During Step 4 | Diagnostic methodology |
| `resources/process_knowledge_base.md` | During Step 4 | Domain knowledge by process type |
| `schemas/*.json` | After each agent output | JSON Schema validation |
| `templates/*.md`, `templates/*.json` | During Steps 4, 5, 6 | Output templates |
| `examples/` | When building context for similar process types | Sample ontologies |
