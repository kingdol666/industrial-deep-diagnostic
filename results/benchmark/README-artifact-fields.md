# Artifact Field Semantics — README for Auditors

This note reconciles the released artifact field names with the metric taxonomy
used in the manuscript (Section 6.2 "Metrics", Table `tab:overall`). Raised by
the round-19 data audit (findings 11/62) and method review (minor 3).

## `metrics.json` → `calibrated` flag

The released `calibrated` boolean **folds two separate checks together**:

1. confidence within the applicable ceiling (calibration proper), and
2. verdict type within the scenario's allowed set (verdict-type compliance).

Example: `skab_valve1_1` is `calibrated: false` because its COMPETING_SET verdict
is outside the scenario's allowed set (`["DETERMINED"]`), even though its
reported confidence (0.60) is within the 0.70 COMPETING_SET ceiling. Conversely
`tep_d01_ac_feed_ratio` is `calibrated: true` although its confidence (0.91)
exceeds the machine grading gate's flat 0.90 non-CS ceiling — that gate is a
grading flag, not part of the `calibrated` field.

The manuscript therefore reports **ceiling compliance** and **verdict-type
compliance** as two separate Table rows (8/9 for type compliance; 5/5 capped /
5/7 non-CS for ceiling), and states the two cap-set exceedances explicitly.

## `rubric.json` → R4 check key

The SKAB inlet-valve throttling rubric deduction (−15) is recorded under the
check key `R4_calibration`. Its failing payload is the **allowed-set violation**
(the COMPETING_SET verdict against the scenario's `["DETERMINED"]` expectation),
which the manuscript describes as an "R4 verdict-type compliance" deduction.
Substance identical; label differs. The rubric's R4 check evaluates both
confidence-ceiling arithmetic and allowed-set membership under one key.

## Superseded run directories

Run directories dated before `20260914` are v1-era (pre anti-oscillation /
confidence-cap discipline). The canonical batch for every number in the
manuscript is the `20260917 16:30–16:45 UTC` batch plus the drawn re-execution
`202609172247007`. A later, **interrupted** second-round batch
(`202609181728xxx`–`202609181738xxx`) exists on disk: 4 of 12 runs reached the
final-audit stage (an `optimizer.md` was produced) and 2 closed all gates
(`pipeline_finalize_report.json` PASS + `evidence_closure_report.json`); it was
never graded or consistency-audited, and `tier_state.json`
has been restored to point at the canonical batch (`run-tier.mjs import-state`).
Do not cite the interrupted batch as evidence.
