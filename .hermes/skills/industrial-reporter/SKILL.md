---
name: industrial-reporter
description: "Industrial diagnostic pipeline Step 6 — generates the 9-section pyramid-structure Chinese diagnostic report (report.md) and the structured summary (run_summary.json) from diagnostic artifacts. Judge-gated: may start only after the Judge verdict is pass with score >= 90 (or all 3 rounds exhausted). Trigger: write report, diagnostic report, report generation, generate report, report writing."
---

# Industrial Reporter

Generates the 9-section pyramid-structure Chinese diagnostic report `report.md` and the structured summary `run_summary.json` from diagnostic artifacts. Judge-gated: may start only after the Judge verdict is pass with score ≥ 90 (or all 3 rounds exhausted).

## Inputs / Outputs

### Inputs (in `RUN_DIR`)

| File | Description |
|------|-------------|
| `04_diagnostics/diagnosis.json` | Root-cause diagnosis conclusion |
| `04_diagnostics/evidence.json` | Evidence inventory |
| `04_diagnostics/confidence.json` | Confidence assessment |
| `04_diagnostics/reasoning_chain.json` | Reasoning chain |
| `03_figures/visual_analysis.json` | VLM visual analysis (primary source of figure evidence) |
| `03_figures/plot_manifest.json` | Figure manifest |
| `01_ontology/ontology.json` | Domain ontology |
| `02_processed/data_analysis_conclusion.json` | Data analysis conclusion |
| `05_review/judge_feedback.json` | Judge quality-gate feedback |

### Outputs

| File | Description |
|------|-------------|
| `report.md` | 9-section pyramid-structure Chinese diagnostic report |
| `run_summary.json` | Structured summary (schema-valid) |

## 9-Section Report Structure

| # | Section | Content |
|---|---------|---------|
| 1 | Executive Summary | Diagnosis type, confidence, key findings (≤300 characters) |
| 2 | Diagnostic Background | Process/equipment description, data overview, user question |
| 3 | Data Quality Assessment | Completeness, outliers, production state, batch integrity |
| 4 | Statistical Analysis Findings | Key correlations, anomaly patterns, Simpson/trend/time-lag (mandatory section, not an appendix) |
| 5 | Hypothesis Testing | Competing-hypotheses table, evidence for/against, exclusion rationale |
| 6 | Root-Cause Conclusion | Physical logic chain, causal path, confidence |
| 7 | Evidence Appendix | Evidence level overview, key figure citations |
| 8 | Recommendations & Follow-up | Actionable recommendations + concrete falsification conditions |
| 9 | Methodology Notes | Analysis methods, limitations, data scope |

## Pipeline Event Logging

**MANDATORY** — log lifecycle events for pipeline-finalize.mjs execution proof verification:

```bash
# On start (before any work)
node "$SHARED_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" \
  --event agent_start --agent reporter --step reporter

# On completion (after ALL outputs written)
node "$SHARED_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" \
  --event agent_complete --agent reporter --step reporter \
  --files report.md,run_summary.json
```

These events are required by `pipeline-log-check.mjs` and `pipeline-finalize.mjs` to prove disciplined sequential execution.

## Dispatch

Launch the `reporter` sub-agent:

```javascript
// Claude Code dispatch via Agent tool:
Agent({
  agent: "reporter",
  task: `RUN_DIR=<run-dir-path>
SKILL_PATH=<path-to-.claude/skills/industrial-reporter>
SHARED_PATH=.claude/shared

Read the agent protocol at $SKILL_PATH/references/agent-protocol.md and execute the complete report generation protocol.

Step 0: Read all diagnostic products from RUN_DIR:
- RUN_DIR/04_diagnostics/diagnosis.json
- RUN_DIR/04_diagnostics/evidence.json
- RUN_DIR/04_diagnostics/confidence.json
- RUN_DIR/04_diagnostics/reasoning_chain.json
- RUN_DIR/03_figures/visual_analysis.json
- RUN_DIR/03_figures/plot_manifest.json
- RUN_DIR/01_ontology/ontology.json
- RUN_DIR/02_processed/data_analysis_conclusion.json
- RUN_DIR/05_review/judge_feedback.json

Step 1: Generate 9-section pyramid report. Use $SKILL_PATH/templates/report_template.md as structure guide.
- Every chart must be embedded: ![title](03_figures/filename.png)
- visual_analysis.json is the primary source for VLM visual insights
- Section 4 (Statistical Analysis Findings) is mandatory, not an appendix
- All web/external knowledge marked [EXTERNAL KNOWLEDGE]
- Report in Chinese; technical terms may be in English
- Write to RUN_DIR/report.md

Step 2: Generate structured summary. Use $SKILL_PATH/schemas/run_summary_schema.json schema and $SKILL_PATH/templates/run_summary_template.json template. Write to RUN_DIR/run_summary.json.

Step 3: Post-processing:
- node "$SKILL_PATH/scripts/synthesize-run-summary.mjs" "$RUN_DIR"
- node "$SKILL_PATH/scripts/report-section-check.mjs" "$RUN_DIR"

Step 4: Validate:
- node "$SHARED_PATH/scripts/validate.mjs" "$SKILL_PATH/schemas/run_summary_schema.json" "$RUN_DIR/run_summary.json"
- Verify both RUN_DIR/report.md and RUN_DIR/run_summary.json exist.
`,
  effort: "hi"
})
```

## Execution Flow

Full protocol in `references/agent-protocol.md`. On-demand references at `resources/evidence_rules.md`.

| Step | Purpose |
|------|---------|
| 0 | Read all diagnostic artifacts (diagnosis/evidence/confidence/reasoning_chain/visual_analysis/plot_manifest/ontology/data_analysis_conclusion/judge_feedback) |
| 1 | Generate report.md following the 9-section pyramid structure, embedding all figures |
| 2 | Generate the run_summary.json structured summary according to the schema |
| 3 | Post-processing: summary synthesis + section completeness check |
| 4 | Validation: schema validation + file existence check |

## Core Rules

- **Every figure must be embedded**: `![title](03_figures/filename.png)`
- **visual_analysis.json is the primary source of VLM visual insights**
- **Section 4 statistical validation is a mandatory section**, not an appendix
- All web/external knowledge marked `[EXTERNAL KNOWLEDGE]`
- Report written in Chinese; technical terms may be in English
- Chinese double quotes must be escaped

## Data Truth Mandate

**Every number written into JSON/reports must be recomputable from the raw data.**

| Rule | Requirement |
|------|------|
| Number traceability | Every number must state its data source (cleaned/raw), row range, and computation method |
| Derived-value marking | Inferred/derived values must be explicitly marked `"derived": true` or `"inferred": true` |
| Cleaning audit trail | cleaning_integrity records all cleaning operations |
| Visualization traceability | Every data point in every figure must be traceable to specific dataset rows |
| Unavailable marking | Values that cannot be computed from the data → write NOT_APPLICABLE + reason |

## Counterfactual Reasoning — Exclusion Constraints

| Constraint | Description |
|------|------|
| Four conditions | Temporal precedence + statistical significance + physical mechanism + no contradiction |
| Exclusion criterion | Any unmet condition → mark as an exclusion candidate with quantitative justification |
| Physics boundary | Exclusions must be supported by first principles or governing equations |
| Confidence threshold | Exclusion confidence < 80 → mark `[WEAK_EXCLUSION]` |

## Assumptions & Limitations

| Category | Requirement |
|------|------|
| Data limitations | Sampling rate / noise / missing extremes / range limits |
| Model assumptions | Linear approximation / steady-state assumption / distribution assumptions |
| Uncontrolled confounders | Explicitly list potential confounding variables that cannot be controlled |
| Conclusion confidence intervals | Each conclusion annotated with confidence ± error margin |

## Efficiency — Parallel Execution

- No data dependency with upstream/downstream agents → parallelize proactively
- Use deterministic scripts instead of LLM reasoning for predictable results
- Large-file sampling strategy: systematic sampling for >100K rows
- Agent stall >600s → inspect existing artifacts; proceed with partially usable outputs

## Failure Recovery

| Scenario | Recovery |
|----------|----------|
| Schema validation fail | Fix JSON → rewrite artifacts → re-validate |
| Missing input artifacts | Report missing files → mark [PARTIAL_RUN] |
| Agent stall >600s | Inspect existing artifacts → continue if partially usable |
| Script execution error | Log the error → degrade to manual LLM production |

## Verification

```bash
SKILL_PATH="<path-to-.claude/skills/industrial-reporter>"
SHARED_PATH=".claude/shared"

# Schema validation
node "$SHARED_PATH/scripts/validate.mjs" \
  "$SKILL_PATH/schemas/run_summary_schema.json" \
  "$RUN_DIR/run_summary.json"

# Post-processing checks
node "$SKILL_PATH/scripts/synthesize-run-summary.mjs" "$RUN_DIR"
node "$SKILL_PATH/scripts/report-section-check.mjs" "$RUN_DIR"

# File existence
test -f "$RUN_DIR/report.md" && test -f "$RUN_DIR/run_summary.json"
```