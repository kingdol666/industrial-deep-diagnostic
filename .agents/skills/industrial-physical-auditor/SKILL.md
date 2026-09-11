---
name: industrial-physical-auditor
description: "Industrial diagnostic pipeline Step 5b/7 — independent physical-truth audit. In PRE_REPORT_AUDIT mode it runs in parallel with the Judge and outputs optimizer_preflight.md; in FINAL_AUDIT mode it performs the final review of report.md and outputs optimizer.md (ENDORSED/CONDITIONAL/REJECTED). Independently verifies physical mechanisms, statistical foundations, and logical consistency. Trigger: physical audit, physics audit, pre-report audit, pre-audit, optimizer, review, physical truth, independent audit, report-reviewer."
---

# Industrial Physical Auditor

Independent physical-truth audit engine. Two modes share the `report-reviewer` Agent, switched via the `PRE_REPORT_AUDIT` parameter: the pre-report audit (parallel with the Judge) validates the physical plausibility of diagnostic artifacts; the final audit reviews report.md and traces every causal chain back to its governing equation. Outputs `optimizer.md` containing an ENDORSED / CONDITIONAL / REJECTED verdict.

## Inputs / Outputs

### Inputs (in `RUN_DIR`)

| File | Description |
|------|-------------|
| `04_diagnostics/diagnosis.json` | Diagnostic conclusion |
| `04_diagnostics/evidence.json` | Evidence list |
| `04_diagnostics/reasoning_chain.json` | Reasoning chain |
| `01_ontology/ontology.json` | Domain ontology |
| `02_processed/data_analysis_conclusion.json` | Statistical analysis conclusion |
| Raw/cleaned data | For direct statistical verification |
| `report.md` *(FINAL only)* | Diagnostic report |
| `05_review/optimizer_preflight.md` *(FINAL, optional)* | Pre-report audit result (reuse already-verified findings) |

### Outputs

| Mode | File | Verdict |
|------|------|---------|
| PRE_REPORT | `05_review/optimizer_preflight.md` | PREFLIGHT_PASS / PREFLIGHT_NEEDS_REPAIR / PREFLIGHT_BLOCKED |
| FINAL | `optimizer.md` | ENDORSED / CONDITIONAL / REJECTED |



## Pipeline Event Logging

**MANDATORY** — log lifecycle events for pipeline-finalize.mjs execution proof verification:

```bash
# On start (before any work)
node "$SHARED_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" \
  --event agent_start --agent report-reviewer --step audit

# On completion (after ALL outputs written)
node "$SHARED_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" \
  --event agent_complete --agent report-reviewer --step audit \
  --files 05_review/optimizer_preflight.md,optimizer.md
```

These events are required by `pipeline-log-check.mjs` and `pipeline-finalize.mjs` to prove disciplined sequential execution.

## Dispatch

Launch the `report-reviewer` Agent:

```javascript
// PRE_REPORT_AUDIT mode (Step 5b) — in parallel with the Judge
Agent({
  subagent_type: "report-reviewer",
  task: `RUN_DIR=<run-dir-path>
SKILL_PATH=<path-to-.claude/skills/industrial-physical-auditor>
SHARED_PATH=<path-to-.claude/shared>
DATA_PATH=<data-file-path>
PRE_REPORT_AUDIT=true

Read the agent protocol at $SKILL_PATH/references/agent-protocol.md and execute the PRE_REPORT_AUDIT protocol.

Pre-report audit scope:
- Physical plausibility: can every causal chain be traced back to a governing equation?
- Falsifiability: is falsification_condition concrete and executable?
- Competing hypotheses: is the exclusion logic grounded in physics rather than pure statistics?
- Confidence: are the ceiling constraints reasonable?
- Confounding variables: independent statistical verification

Output: optimizer_preflight.md with PREFLIGHT_PASS / PREFLIGHT_NEEDS_REPAIR / PREFLIGHT_BLOCKED verdict.
`,
  effort: "hi"
})

// FINAL_AUDIT mode (Step 7) — final review after report generation
Agent({
  subagent_type: "report-reviewer",
  task: `RUN_DIR=<run-dir-path>
SKILL_PATH=<path-to-.claude/skills/industrial-physical-auditor>
SHARED_PATH=<path-to-.claude/shared>
DATA_PATH=<data-file-path>
PRE_REPORT_AUDIT=false

Read the agent protocol at $SKILL_PATH/references/agent-protocol.md and execute the FINAL_AUDIT protocol.

Final audit scope:
- Physical truthfulness: every causal chain in report.md traced back to its governing equation
- No over-claiming: confidence reasonable, evidence ranks assigned correctly
- Evidence completeness: evidence ranks assigned correctly
- Falsifiability: falsification conditions concrete and executable
- Statistical foundation: correlations passed the full anti-spurious-correlation validation

Output: optimizer.md with ENDORSED / CONDITIONAL / REJECTED verdict.
`,
  effort: "hi"
})
```

## Audit Scopes

Full protocol in `references/agent-protocol.md`. On-demand references at `resources/evidence_rules.md`, `resources/process_knowledge_base.md`.

| Scope | PRE_REPORT_AUDIT | FINAL_AUDIT |
|-------|-----------------|-------------|
| Physical mechanism chain verification | Physical explainability + quantitative estimation | Every causal chain in report.md traced to governing equations |
| RAG knowledge cross-check | Physical principles + failure modes + confounder coverage | Same + audit of verified claims |
| Reasoning chain audit (hallucination detection) | 8 red-flag pattern checks | Spot-check protocol |
| Confounding variable detection | Independent statistical verification | — |
| Competing hypothesis completeness | ≥3 competing hypotheses | Same |
| Confidence assessment audit | Confidence decomposition | Over-claiming check |
| Over-claiming check | — | Confidence reasonable, evidence ranks correct |
| Falsifiability check | Is falsification_condition concrete and executable | Same |

## Verdict

| Mode | Verdict | Meaning | Next |
|------|---------|------|--------|
| PRE | `PREFLIGHT_PASS` | Pre-report passed | Continue to Step 6 (Reporter) |
| PRE | `PREFLIGHT_NEEDS_REPAIR` | Repairable issues | Repair the diagnosis with repair_instruction |
| PRE | `PREFLIGHT_BLOCKED` | Physical logic defect | Trigger the repair loop |
| FINAL | `ENDORSED` | Physical logic solid | Proceed to Step 8 (HTML) |
| FINAL | `CONDITIONAL` | Repairable issues exist | Fix, then proceed to Step 8 |
| FINAL | `REJECTED` | Fundamental defect | Trigger the repair loop (D→J→R→R) |

## Data Truth Mandate

**Every number written to JSON/reports must be recomputable from the raw data.**
|Rule|Requirement|
|---|---|
|Numeric traceability|Every number must state its data source (cleaned/raw), row range, and computation method|
|Derived value marking|Inferred/derived values must be explicitly marked `"derived": true` or `"inferred": true`|
|Cleaning audit trail|cleaning_integrity records all cleaning operations|
|Visualization traceability|Every data point in every chart must be traceable to specific rows of the dataset|
|Unavailable marking|Values that cannot be computed from the data → write NOT_APPLICABLE + reason|

## Counterfactual Reasoning — Exclusion Constraints

|Constraint|Description|
|---|---|
|Four conditions|Temporal precedence + statistical significance + physical mechanism + no contradiction|
|Exclusion standard|If any condition is not met → mark as an excluded candidate and provide quantitative justification|
|Physical boundary|Exclusions must be supported by first principles or governing equations|
|Confidence threshold|When exclusion confidence <80, mark `[WEAK_EXCLUSION]`|

## Assumptions & Limitations

|Category|Requirement|
|---|---|
|Data limitations|Sampling rate/noise/missing extremes/range restrictions|
|Model assumptions|Linear approximation/steady-state assumption/distribution assumptions|
|Uncontrolled confounders|Explicitly list potential confounding variables that cannot be controlled|
|Conclusion confidence intervals|Label every conclusion with confidence ± error margin|

## Efficiency — Parallel Execution

- When there is no data dependency with upstream/downstream agents → parallelize proactively
- Use deterministic scripts instead of LLM reasoning for predictable outcomes
- Large-file sampling strategy: systematic sampling when >100K rows
- Agent stall >600s → inspect existing artifacts; if partially usable, continue forward

## Verification

```bash
SKILL_PATH="<path-to-.claude/skills/industrial-physical-auditor>"
SHARED_PATH="<path-to-.claude/shared>"

# PRE_REPORT_AUDIT
test -f "$RUN_DIR/05_review/optimizer_preflight.md"
grep -Eq "PREFLIGHT_PASS|PREFLIGHT_NEEDS_REPAIR|PREFLIGHT_BLOCKED" "$RUN_DIR/05_review/optimizer_preflight.md"

# FINAL_AUDIT
test -f "$RUN_DIR/optimizer.md"
grep -Eq "ENDORSED|CONDITIONAL|REJECTED" "$RUN_DIR/optimizer.md"
```

## Failure Recovery

| Scenario | Recovery |
|----------|----------|
| Missing diagnosis artifacts | Report what is missing → mark PREFLIGHT_BLOCKED / REJECTED |
| report.md does not exist (FINAL) | Wait for the Reporter to finish → re-trigger FINAL_AUDIT |
| Physical mechanism cannot be verified | Lower confidence → mark CONDITIONAL with limitation notes |
| Statistical verification contradicts claims | Mark REJECTED → trigger the D→J→R→R repair loop |
| Auditor timeout | Inspect partial artifacts → continue if usable, otherwise retry |
