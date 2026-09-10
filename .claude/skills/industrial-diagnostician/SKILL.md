---
name: industrial-diagnostician
description: "Industrial diagnostic pipeline — physics-constrained competing-hypotheses root-cause diagnostic engine. Fuses the data analysis conclusion, domain ontology, physical mechanisms, VLM visual evidence, and time-lag analysis, and outputs conclusions by elimination rather than confirmation. Use in pipeline Step 4 once upstream data processing is complete. Trigger: diagnosis, diagnoze, root cause, competing hypotheses, physics diagnosis, physical inference, diagnostician, root cause diagnosis, hypothesis elimination, causal inference, physics-constrained diagnosis, competing hypothesis analysis. Do NOT use without upstream data_analysis_conclusion.json."
---

# Industrial Diagnostician

Physics-constrained competing-hypotheses root-cause diagnostic engine. Fuses the data analysis conclusion, the domain ontology, physical first principles, VLM visual evidence, and time-lag analysis, and outputs conclusions by elimination rather than confirmation.

Core rule: **diagnosis = elimination**. Every conclusion satisfies the four conditions — temporal precedence + statistical significance + physical mechanism + no contradiction. At least 3 competing hypotheses, at least 2 of them eliminated.

## Inputs / Outputs

### Inputs (in `RUN_DIR`)

| File | Role |
|------|------|
| `02_processed/data_analysis_conclusion.json` | Mandatory handoff file — statistical analysis conclusion |
| `01_ontology/ontology.json` | Physical-semantic ontology |
| `03_figures/visual_analysis.json` | VLM visual evidence |
| `02_processed/time_lag_analysis.json` | Time-lag analysis (must be read if present) |
| `02_processed/anomaly_report.json` | Anomaly report |
| `02_processed/validate_report.json` | Statistical validation report |
| `02_processed/feature_summary.json` | Feature summary |
| `02_processed/scenario_classification.json` | Scenario/product stratification classification |

### Outputs

| File | Description |
|------|-------------|
| `04_diagnostics/diagnosis.json` | Conclusion (process_fluctuation + integrated_dual_drive) |
| `04_diagnostics/evidence.json` | Evidence inventory (L1-L7 levels, incl. ontology_data_physics_proof) |
| `04_diagnostics/confidence.json` | 5-factor confidence assessment + adjustment_log |
| `04_diagnostics/reasoning_chain.json` | R1-R8 complete reasoning chain |

## Pipeline Event Logging

**MANDATORY** — log lifecycle events for pipeline-finalize.mjs execution proof verification:

```bash
# On start (before any work)
node "$SHARED_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" \
  --event agent_start --agent diagnostician --step diagnostician

# On completion (after ALL outputs written)
node "$SHARED_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" \
  --event agent_complete --agent diagnostician --step diagnostician \
  --files 04_diagnostics/diagnosis.json,04_diagnostics/evidence.json,04_diagnostics/confidence.json,04_diagnostics/reasoning_chain.json
```

These events are required by `pipeline-log-check.mjs` and `pipeline-finalize.mjs` to prove disciplined sequential execution.

## Dispatch

Launch the `diagnostician` sub-agent:

```javascript
// Claude Code dispatch via Agent tool:
Agent({
  agent: "diagnostician",
  task: `DATA_PATH=<data-file-path>
RUN_DIR=<run-dir-path>
SKILL_PATH=<path-to-.claude/skills/industrial-diagnostician>
SHARED_PATH=<path-to-.claude/shared>
${REPAIR_INSTRUCTIONS ? 'REPAIR_INSTRUCTIONS=' + REPAIR_INSTRUCTIONS : ''}

Read "<SKILL_PATH>/references/agent-protocol.md"
and execute Phase 0-7. Fuse data+ontology+physics+VLM+time-lag.

Key constraints:
- Three drivers: physics-led + data-verified + visually-supplemented
- Every hypothesis must have a physical mechanism — governing equation and causal chain
- At least 3 competing hypotheses (H1, H2, H3), at least 2 eliminated
- A COMPETING_SET must not contain only one hypothesis
- The reasoning chain must be complete R1-R8
- If time_lag_analysis.json exists, it must be read
- Every hypothesis includes ontology_data_physics_proof, physical_logic_chain, and falsification_conditions
- Output in Chinese; keep enums in English
`,
  effort: "hi"
})
```

## Execution Flow

Full protocol in `references/agent-protocol.md`. On-demand references at `resources/physics_inference_framework.md`, `resources/evidence_rules.md`, `resources/diagnosis_method.md`.

| Phase | Purpose |
|-------|---------|
| 0 | Data probing — read all input files + the 4 output schemas |
| 1 | Statistical foundation — verify validate_report (Simpson/detrending/leave-one-out/CCF); record correlations that pass validation |
| 2 | Product stratification — read scenario_classification, determine focus_product, detect Simpson inversions |
| 3 | Hypothesis generation — 3+ competing hypotheses, each with a physical chain (governing equation) + supporting evidence + opposing evidence + falsification conditions |
| 4 | Data discriminability — evaluate the discriminability_matrix pairwise; INDISTINGUISHABLE → confidence_ceiling ≤ 65 |
| 5 | Hypothesis elimination — eliminate at least 2, exclusion_confidence ≥ 90, record revival_condition |
| 6 | Confidence assessment — 5-factor decomposition (statistical/physical/temporal/confounds/symptom) + adjustment_log + ceilings |
| 7 | Write outputs + Schema validation — 4 JSON files, each validated by validate.mjs; done only when all pass |

## Core Rules

- **3+ hypotheses** — each with falsification conditions + causal chain (governing equation)
- **2+ EXCLUDED** — via NO_RESET, IMPOSSIBLE physics, IMPLAUSIBLE magnitude, CONTRADICTED ontology
- **Conclusion types**: `DETERMINED` / `COMPETING_SET` / `NEEDS_DATA`
- **COMPETING_SET honesty**: never force to DETERMINED; ambiguity is truth
- **Anti-spurious**: every |r|≥0.3 reference passes Simpson/detrend/lag/leave-one-out
- **Confidence ceilings**: INDISTINGUISHABLE ≤ 65, COMPETING_SET ≤ 70, [PARAM_AMBIGUITY] ≤ 50
- **Schema-First**: read schema → construct → write → validate, one shot per file
- **Physics chain format**: measured value Y of parameter X → passes through physical law Z → affects quality indicator W (three-part form)

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

## Verification

```bash
SKILL_PATH="<path-to-.claude/skills/industrial-diagnostician>"
SHARED_PATH="<path-to-.claude/shared>"

for f in diagnosis evidence confidence reasoning_chain; do
  node "$SHARED_PATH/scripts/validate.mjs" \
    "$SKILL_PATH/schemas/${f}_schema.json" \
    "$RUN_DIR/04_diagnostics/${f}.json" || exit 1
done

node "$SKILL_PATH/scripts/diagnostic-quality-check.mjs" "$RUN_DIR"
node "$SKILL_PATH/scripts/schema-validation-loop.mjs" "$RUN_DIR" "$SKILL_PATH" diagnostician
```

## Failure Recovery

| Scenario | Recovery |
|----------|----------|
| Schema validation fail | Fix JSON → rewrite → re-validate (schema-validation-loop) |
| Missing data_analysis_conclusion.json | Cannot proceed — upstream incomplete |
| Missing time_lag_analysis.json | Not mandatory — mark no time-lag evidence, degrade temporal_evidence |
| No hypothesis resolvable | COMPETING_SET + honest disclosure of ambiguity |
| Correlation confounded (Simpson/detrend) | Degrade evidence level, mark confound_detected: true |
| VLM visual analysis unavailable | Degrade temporal_evidence, do not block diagnosis |

## References

- `references/agent-protocol.md` — Phase 0-7 execution protocol (hypothesis comparison / physical inference / evidence fusion / write-and-validate)
- `resources/execution_reference.md` — file inventory / filtering rules / governing equations / hallucination prevention
- `resources/evidence_rules.md` — evidence level system / causal five conditions / anti-speculation
- `resources/physics_inference_framework.md` — L1-L5 physical inference ladder
- `resources/diagnosis_method.md` — confidence ceilings / diagnostic methodology
- `resources/diagnostician_dual_drive_reference.md` — View A/B dual-drive analysis
- `resources/parameter_to_physics.json` — parameter-to-physics-quantity mapping
- `schemas/` — 5 output JSON Schemas (diagnosis/evidence/confidence/reasoning_chain/causal_evidence_map)
- `scripts/` — schema-validation-loop.mjs, diagnostic-quality-check.mjs, physics_check.py, confidence-completeness-check.mjs
- `templates/` — diagnosis_template.json

## REPAIR_SCOPE — Targeted Repair Protocol

A repair-round dispatch (2nd/3rd round) may carry `REPAIR_SCOPE=<files>` (from judge_feedback.json repair_scope):

- Recompute only the diagnostic files within scope; files outside scope are restored verbatim from the best_round snapshot, and the corresponding segments in reasoning_chain.json are annotated `"carried_over": true, "carried_from": "best_round_N"`.
- When recomputing, repair_scope.instructions from the previous round's judge_feedback.json must be read and applied as repair constraints.
- Full recomputation is performed only when REPAIR_SCOPE is absent (backward compatible).