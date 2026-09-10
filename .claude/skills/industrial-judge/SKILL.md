---
name: industrial-judge
description: "Industrial diagnostic pipeline — quality gate review. Scores 10 criteria to verify the integrity of diagnostic reasoning and statistical foundations, and performs cross-file cross-validation audits. Trigger: quality gate, quality review, judge, diagnosis review, quality gate review, cross validation, audit, quality review, diagnosis audit, verdict check, blocking issues."
---

# Industrial Judge

Quality gate review engine. Scores against 10 criteria, verifies the integrity of diagnostic reasoning and statistical foundations, and performs cross-file cross-validation audits. Outputs `judge_feedback.json` containing a pass/needs_repair/major_issues/fail verdict.

## Inputs / Outputs

### Inputs (in `RUN_DIR`)

| File | Description |
|------|-------------|
| `04_diagnostics/diagnosis.json` | Diagnostic conclusion + COMPETING_SET |
| `04_diagnostics/evidence.json` | Evidence list |
| `04_diagnostics/confidence.json` | Confidence assessment |
| `04_diagnostics/reasoning_chain.json` | R1-R8 reasoning chain |
| `02_processed/validate_report.json` | Statistical validation report (Simpson/detrending/change-point/outlier) |
| `02_processed/data_analysis_conclusion.json` | Data analysis conclusion |
| `03_figures/visual_analysis.json` | VLM visual analysis |
| `01_ontology/ontology.json` | Domain ontology |
| `02_processed/feature_summary.json` | Feature summary |

### Outputs

| File | Description |
|------|-------------|
| `05_review/judge_feedback.json` | verdict + overall_score + dimension_scores[0-10] + blocking_issues + repair_instructions |

## 10-Point Gate

| # | Gate | 1-Line Check |
|---|------|-------------|
| 1 | Physical traceability | Does every causal claim trace back to a governing equation? |
| 2 | Evidence sufficiency | Does every conclusion carry ≥L3 evidence with a closed chain? |
| 3 | Reasoning chain completeness | R1→R8 with no jumps, `[INFERENCE_GAP]` annotated? |
| 4 | Anti-spurious correlation | Simpson/detrending/time-lag/leave-one-out validated? |
| 5 | No selective omission | Counter-evidence and competing hypotheses complete? |
| 6 | No over-claiming | COMPETING_SET honest; confidence reasonable? |
| 7 | Anti-speculation four conditions | Temporal precedence + significance + mechanism + no contradiction? |
| 8 | Red-light checklist | All 10 forbidden actions observed? |
| 9 | Schema compliance | All diagnostic artifacts schema-valid? |
| 10 | Evidence rank annotation | Every conclusion labeled with Evidence Rank L1-L7? |

## Verdict

| Verdict | Score | Meaning | Next |
|---------|-------|---------|------|
| `pass` | ≥90 | Zero blocking | Reporter |
| `needs_repair` | 70-89 | Non-blocking issues | Diagnostician with REPAIR_INSTRUCTIONS |
| `major_issues` | 50-69 | Moderate | Fix (best-of-3 loop) |
| `fail` | <50 | Blocking | Must fix |



## Pipeline Event Logging

**MANDATORY** — log lifecycle events for pipeline-finalize.mjs execution proof verification:

```bash
# On start (before any work)
node "$SHARED_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" \
  --event agent_start --agent judge --step judge

# On completion (after ALL outputs written)
node "$SHARED_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" \
  --event agent_complete --agent judge --step judge \
  --files 05_review/judge_feedback.json
```

These events are required by `pipeline-log-check.mjs` and `pipeline-finalize.mjs` to prove disciplined sequential execution.

## Dispatch

Launch the `judge` subagent:

```javascript
// Claude Code dispatch via Agent tool:
Agent({
  agent: "judge",
  task: `RUN_DIR=<run-dir-path>
SKILL_PATH=<path-to-.claude/skills/industrial-judge>
SHARED_PATH=<path-to-.claude/shared>
DATA_PATH=<data-file-path>

Read the agent protocol at <SKILL_PATH>/references/agent-protocol.md and execute the full quality gate review.

Key constraints:
- validate_report.json is the primary validation tool — it must be read before scoring
- Every BLOCKING finding must carry a repair instruction
- reasoning_chain with fewer than 8 segments → blocking issue
- empty diagnosis.hypotheses.surviving → blocking issue
- conclusion missing falsification_conditions → blocking issue
- empty evidence.validation_evidence → warning
- Output prose in Chinese; keep enums in English
`,
  effort: "hi"
})
```

## Execution Flow

Full protocol in `references/agent-protocol.md`. On-demand references at `resources/evidence_rules.md` and `resources/execution_reference.md`.

| Step | Purpose |
|------|---------|
| 0 | Read all diagnostic artifacts (diagnosis/evidence/confidence/reasoning_chain/validate_report/data_analysis_conclusion/visual_analysis/ontology/feature_summary) |
| 0.5 | Cross-validation: consistency audit between validate_report findings and diagnosis |
| 0.6 | Reasoning chain quality audit (R1-R8 completeness/evidence basis/counterfactuals/falsifiability/hallucination audit) |
| 0.65 | Physical provenance quality audit (pre_cached/rag_extracted/first_principles provenance) |
| 0.7 | Independent data sampling: spot-verify key correlation claims |
| 0.8 | Stability/reproducibility audit |
| 1 | 10-point scoring (0-10 each) — synthesizing all findings from Steps 0.5-0.8 |
| 2 | Cross-Reference Audit (5 cross-file cross-validation checks) |
| 3 | Output judge_feedback.json |

## Data Truth Mandate

**Every number written to JSON/reports must be recomputable from the raw data.**

| Rule | Requirement |
|------|------|
| Numeric traceability | Every number must state its data source (cleaned/raw), row range, and computation method |
| Derived value marking | Inferred/derived values must be explicitly marked `"derived": true` or `"inferred": true` |
| Cleaning audit trail | cleaning_integrity records all cleaning operations |
| Visualization traceability | Every data point in every chart must be traceable to specific rows of the dataset |
| Unavailable marking | Values that cannot be computed from the data → write NOT_APPLICABLE + reason |

## Counterfactual Reasoning — Exclusion Constraints

| Constraint | Description |
|------|------|
| Four conditions | Temporal precedence + statistical significance + physical mechanism + no contradiction |
| Exclusion standard | If any condition is not met → mark as an excluded candidate and provide quantitative justification |
| Physical boundary | Exclusions must be supported by first principles or governing equations |
| Confidence threshold | When exclusion confidence <80, mark `[WEAK_EXCLUSION]` |

## Assumptions & Limitations

| Category | Requirement |
|------|------|
| Data limitations | Sampling rate/noise/missing extremes/range restrictions |
| Model assumptions | Linear approximation/steady-state assumption/distribution assumptions |
| Uncontrolled confounders | Explicitly list potential confounding variables that cannot be controlled |
| Conclusion confidence intervals | Label every conclusion with confidence ± error margin |

## Efficiency — Parallel Execution

- When there is no data dependency with upstream/downstream agents → parallelize proactively
- Use deterministic scripts instead of LLM reasoning for predictable outcomes
- Large-file sampling strategy: systematic sampling when >100K rows
- Agent stall >600s → inspect existing artifacts; if partially usable, continue forward

## Verification

```bash
SKILL_PATH="<path-to-.claude/skills/industrial-judge>"
SHARED_PATH="<path-to-.claude/shared>"

node "$SHARED_PATH/scripts/validate.mjs" \
  "$SHARED_PATH/schemas/judge_feedback_schema.json" \
  "$RUN_DIR/05_review/judge_feedback.json"

node "$SKILL_PATH/scripts/judge-gate-check.mjs" "$RUN_DIR" --skip-summary
```

## Failure Recovery

| Scenario | Recovery |
|----------|----------|
| Schema validation fail | Fix the JSON → rewrite → re-validate |
| Missing input files | Report what is missing → verdict=fail, score=0, blocking issues listed |
| Gate check fail | Use repair instructions from blocking_issues → fall back to the Diagnostician for repair |
| Judge timeout | Inspect partial artifacts → continue if usable |

## Structured Repair Scope (Targeted Repair Contract)

feedback must contain a `repair_scope` array so the Step 4 repair round can recompute in a targeted way (avoiding recomputation of all 4 diagnostic JSON files):

```json
{
  "repair_scope": [
    { "dimension": "statistical_evidence", "files": ["04_diagnostics/evidence.json"], "instructions": "..." }
  ]
}
```

- Rounds 2/3 of the review only re-examine dimensions inside the scope + recheck the previous round's blocking items; dimensions that already passed reference the previous round's conclusions (marked carried_over).
- An empty scope array = no repair needed (when verdict=pass).
