# Engineering Delivery Contract

The engineering delivery standard for this Skill is as follows:

## 1. Strict Pipeline

The following order must be executed and logged:
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

No step may be skipped silently. If a step does not apply, a `not_applicable_reason` must be recorded in the corresponding artifact.

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

If a valid time column exists, the following must also be delivered:
- at least one temporal / aligned / timeline / process-health chart recorded in `03_figures/plot_manifest.json`, and the chart file must actually exist

## 3. Evidence Closure

All of the following must be present:
- pure process-fluctuation analysis
- process + inspection dual-driver analysis
- ontology / industry-knowledge explanation
- diagnostic conclusion and review handover

## 4. Sub-Agent Delivery Responsibility

- `context-builder`: responsible for domain knowledge, ontology, and clarification requirements
- `data-processor`: responsible for data analysis, figures, VLM visual evidence, and the expert data conclusion
- `diagnostician`: responsible for competing hypotheses, physical reasoning, and the final diagnostic structure
- `judge`: responsible for the quality-gate review
- `reporter`: responsible for the final report and run_summary
- `report-reviewer`: responsible for the physical-truth audit and for the standard `optimizer.md` optimization deliverable

## 5. Standard Delivery Requirements for optimizer.md

`optimizer.md` must be an optimization plan grounded in the current data and the specific scenario; it cannot be merely an audit opinion or generic advice. It must contain:
- Scenario-specific optimization plan: state which process, maintenance, inspection, control, sampling, or process-window improvements the current data supports
- Problems and improvement opportunities in the current scenario: list anomalous behaviour, quality chains, measurement gaps, confounders, physical-model gaps, and image-evidence gaps
- Next-step diagnostic confirmation plan: state what additional data must be collected, what controlled trials must be run, and what physical verification must be added before diagnostic accuracy and certainty can be raised further
- Action classification: distinguish immediate containment, low-risk optimization, controlled experiments, measurement/data improvement, and deferred or unsafe actions

## 6. Final Pass Conditions

A run counts as engineering-complete only when all of the following hold:
- `pipeline-log-check.mjs` passes
- `pipeline-finalize.mjs` passes
- `optimizer.md` exists and passes the standard section-completeness check
- the `present` step in `run_manifest.json` is complete
- a final `run_completed` event exists in `.pipeline_events.jsonl`
