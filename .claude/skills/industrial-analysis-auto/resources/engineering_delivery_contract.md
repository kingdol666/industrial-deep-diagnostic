# Engineering Delivery Contract

The engineering delivery standard for this Skill is as follows:

## 1. Strict Pipeline

The following order must be executed, and each step must leave an audit trail:
- setup
- inspect
- context_builder
- clarification_gate
- data_processor
- diagnostician
- judge
- reporter
- audit
- present

No step may be skipped silently. If a step does not apply, `not_applicable_reason` must be recorded in the corresponding artifact.

## 2. Minimum Delivery Artifacts

A valid run must deliver at least:
- `00_input/run_config.json`
- `00_input/input_manifest.json`
- `01_ontology/ontology.json`
- `02_processed/scenario_classification.json`
- `02_processed/anomaly_report.json`
- `02_processed/data_analysis_conclusion.json`
- `03_figures/plot_manifest.json`
- `03_figures/visual_analysis.json`
- `03_figures/image_captions.json`
- `04_diagnostics/diagnosis.json`
- `04_diagnostics/evidence.json`
- `04_diagnostics/confidence.json`
- `04_diagnostics/reasoning_chain.json`
- `05_review/judge_feedback.json`
- `report.md`
- `run_summary.json`
- `optimizer.md`
- `evidence_closure_report.json`

If a valid time column exists, it must additionally deliver:
- At least one temporal / aligned / timeline / process-health figure recorded in `03_figures/plot_manifest.json`, and that figure file must actually exist

## 3. Evidence Closure

All of the following must be present at the same time:
- Process-only fluctuation analysis
- Process + inspection dual-drive analysis
- Ontology / industry-knowledge interpretation
- Diagnosis conclusion and review hand-off

## 4. Sub-Agent Delivery Accountability

- `context-builder`: accountable for domain knowledge, the ontology, and clarification requirements
- `data-processor`: accountable for data analysis, figures, VLM visual evidence, and the expert data conclusion
- `diagnostician`: accountable for competing hypotheses, physical reasoning, and the final diagnosis structure
- `judge`: accountable for the quality-gate review
- `reporter`: accountable for the final report and run_summary
- `report-reviewer`: accountable for the physical-truth audit and for the standard optimization deliverable `optimizer.md`

## 5. Standard Delivery Requirements for optimizer.md

`optimizer.md` must be an optimization plan grounded in the current data and the specific scenario — it cannot be merely audit opinions or generic advice. It must contain:
- Scenario-specific optimization plan: state which process, maintenance, inspection, control, sampling, or process-window improvements the current data supports
- Problems and improvement opportunities in the current scenario: list abnormal behaviour, quality chains, measurement gaps, confounders, physical-model gaps, and image-evidence gaps
- Next-step diagnostic confirmation plan: state what additional data must be collected, what controlled trials must be run, and what physical verification must be added before diagnostic accuracy and certainty can be improved further
- Action classification: distinguish immediate containment, low-risk optimization, controlled experiments, measurement/data improvement, and deferred or unsafe actions

## 6. Final Pass Conditions

A run counts as engineering-complete only when all of the following conditions are satisfied:
- `pipeline-log-check.mjs` passes
- `pipeline-finalize.mjs` passes
- `optimizer.md` exists and passes the standard section-completeness check
- The `present` step in `run_manifest.json` is complete
- A final `run_completed` event exists in `.pipeline_events.jsonl`
