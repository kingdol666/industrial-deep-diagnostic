# Judge — Detailed Execution Reference

## Step 0: Load All Artifacts

Read from RUN_DIR:
- `01_ontology/ontology.json` — Process ontology (with behavior_match and discrepancy_signals)
- `01_ontology/schema.json` — Normalized schema
- `00_input/rag_deep_understanding.json` — Physics principles, validated RAG claims, confounders
- `02_processed/rag_validation_report.json` — Stage 2 thorough RAG validation (if exists)
- `02_processed/feature_summary.json` — Enhanced statistical features
- `02_processed/validate_report.json` — Statistical validation report (load BEFORE judging)
- `02_processed/data_quality_report.json` — Data quality
- `02_processed/scenario_classification.json` — Scenario type and data shape
- `02_processed/analysis_plan.md` — Data-processor's analysis rationale (if exists)
- `02_processed/analysis_parameter_selection.json` — Ontology-guided tier assignments
- `02_processed/data_analysis_conclusion.json` — Data Processor expert handoff
- `02_processed/zone_analysis.json` — Per-zone drift localization (if multi-zone)
- `02_processed/event_analysis.json` — Quality reset classifications (if event markers)
- `02_processed/anomaly_report.json` — Inspect `process_parameter_fluctuation` and `dual_drive_analysis`
- `04_diagnostics/diagnosis.json` — The diagnosis to review
- `04_diagnostics/evidence.json` — Evidence chains
- `04_diagnostics/confidence.json` — Confidence breakdown
- `04_diagnostics/reasoning_chain.json` — Structured CoT reasoning trace
- `03_figures/visual_analysis.json` — VLM visual insights
- `03_figures/plot_manifest.json` — Plot inventory
- `03_figures/image_captions.json` — Per-figure descriptions

Read from SKILL_PATH:
- `resources/evidence_rules.md` — Evidence hierarchy and anti-speculation rules
- `schemas/judge_feedback_schema.json` — Schema validation target
- `templates/judge_template.json` — Output structure reference

## Step 0.5: Cross-Reference Validate Report Against Diagnosis

**1. Sorting Issues**
- If `validate_report.json.sorting_validation.time_sorted == false` AND diagnosis uses lag correlations as primary evidence WITHOUT caveat → **BLOCKING**

**2. Lag-Compensated Correlations (v6.4)**
- If `time_lag_analysis.json` exists and diagnosis doesn't reference key findings → **WARNING**
- If raw correlations used without checking lag-compensated values → **WARNING**

**2.5 Steady-State Filtered Data (v6.5)**
- If `production_regime_filter.json` exists but diagnosis doesn't acknowledge steady-state ratio → **WARNING**
- If multi-product dataset but per-product analysis missing → **WARNING** (Simpson risk)
- If steady-state ratio < 0.4 and correlations treated as reliable without caveats → **WARNING**

**3. Simpson's Paradox**
- For each CRITICAL/SERIOUS finding in `validate_report.json.simpson_paradox[]`: is direction reversal/attenuation mentioned? Confidence adjusted? → If ignored: **BLOCKING**

**4. Trend Confounding**
- For correlations with attenuation > 50%: does diagnosis report detrended r alongside raw r? → If used as primary evidence without adjustment: **BLOCKING**

**5. Spearman Robustness**
- For heavily skewed defect data: does diagnosis mention Spearman correlations? → If not: **WARNING**

**6. Outlier-Driven Correlations**
- For correlations flagged `outlier_driven: true`: does diagnosis mention caveat? → If not: **WARNING**

**7. Parameter Physical Meaning Gaps**
- If `clarification_needed.json` has unresolved CRITICAL parameters used as primary evidence WITHOUT [PARAM_AMBIGUITY] → **BLOCKING**

**8. New Statistical Methods**
- Granger causality, interaction effects, mutual information, change points — are they referenced when data supports them? → If all missing: **WARNING**

**9. Data Discriminability (v6.0)**
- Does diagnosis check whether competing hypotheses predict DIFFERENT observable patterns?
- Are indistinguishable pairs output as COMPETING_SET?
- If >65 confidence assigned without checking alternative observables → **BLOCKING**
- If time-colinear mechanisms treated as independently confirmed → **BLOCKING**

**10. VLM Visual Evidence Consistency (v6.4)**
- Does diagnosis reference visual_analysis.json?
- Visual direction consistent with statistical direction?
- If visual_analysis ignored entirely → **WARNING**

## Step 0.6: Audit Reasoning Chain Quality

**Check 1: Completeness** — R1-R8 all present? Each has inputs/reasoning/outputs/alternatives/uncertainty/falsification? Missing required fields → **BLOCKING**

**Check 2: Evidence Grounding** — Specific evidence sources cited? Ranks correct? [OBSERVED] backed by Rank 1-4? [INFERRED] flagged? Lacks grounding → **BLOCKING**

**Check 3: Counterfactual Adequacy** — Each surviving hypothesis has at least ONE alternative? Actually possible (not strawman)? Elimination specific and data-backed? Missing → **WARNING**

**Check 4: Falsifiability** — `falsification_condition` specifies REAL, TESTABLE evidence? Vague ("would need more data") → **WARNING**

**Check 5: Hallucination Audit** — Spot-check 3 conclusions: specific data backing, evidence rank, [OBSERVED]/[INFERRED] marker. Unsupported → **BLOCKING**

**Check 6: Uncertainty Decomposition** — Aleatory vs epistemic properly separated? Confidence ceiling justified? Actionable next steps? Handwaved → **WARNING**

## Step 0.65: Physics Source Quality Audit

### Audit 1: Physics Source Tracking

| Physics Source | Expected Label | Confidence Rule | Audit Check |
|---------------|---------------|-----------------|-------------|
| Pre-cached | `pre_cached` | Baseline | Actually in parameter_to_physics.json? |
| RAG extracted | `rag_extracted` | −5 | Documented in rag_deep_understanding.json? |
| First principles | `first_principles` | −10 (PLAUSIBLE) / −15 (BORDERLINE) | ALL 5 Ladder levels documented? |

**BLOCKING if**: pre_cached but parameter NOT in file / first_principles with incomplete L1-L5 / NO source annotation / confidence not matching source

### Audit 2: RAG Knowledge Usage

From `rag_deep_understanding.json`:
- Validated claims properly cited → +5
- CONTRADICTED claims used → **BLOCKING** if without acknowledgement
- Extracted principles applied → check for missed opportunities
- Known confounders addressed?

### Audit 3: RAG Thorough Validation Cross-Check

If `rag_validation_report.json` exists:
- FULLY_VALIDATED → high confidence OK
- PARTIALLY_VALIDATED → MUST acknowledge partial validation
- CONTRADICTED → MUST NOT use as primary evidence
- Claims not validated → should note lack of validation

### Audit 4: Ontology Discrepancy Signal Resolution

- CONTRADICTED parameters used as evidence → MUST explain why
- Discrepancy signals addressed?
- New discrepancies from data-processor reflected?

**BLOCKING if** conclusion relies on parameter with `behavior_match: CONTRADICTED` without explanation.

## Step 0.7: Independent Data Sampling

For each key correlation claim (|r| > 0.5 or primary evidence):
1. Extract claim from diagnosis.json
2. Sample 10-20 rows from cleaned_data.json
3. Visually verify direction matches
4. Check for extreme values driving relationship
5. Check for monotonic trends

Document in `judge_feedback.json` under `spot_check_findings`. Any failure → **WARNING**.

## Step 0.8: Stability / Reproducibility Audit

1. **Canonical traceability**: Primary finding and confidence traceable to data_analysis_conclusion/diagnosis/evidence/confidence/reasoning_chain. Confidence reconstructable from adjustment_log. → If not: **BLOCKING**
2. **Repeat-run comparison**: If prior comparable run exists, compare primary finding and confidence. Different finding or confidence shift >10 without concrete evidence delta → **BLOCKING**
3. **No forced high confidence**: COMPETING_SET/NEEDS_DATA may have honest lower diagnostic confidence. Don't require ≥90 when data is ambiguous.

## Step 1: 10-Point Quality Gate Scoring

Score each of the 10 dimensions 0-10, compute overall. Each check with BLOCKING issues in Steps 0.5-0.8 automatically reduces the relevant dimension score.

## Output

Write `judge_feedback.json` with:
- `verdict`: pass | needs_repair | major_issues | fail
- `overall_score`: 0-100
- `dimension_scores`: per-dimension scoring
- `blocking_issues`: each with repair_instruction
- `warnings`: non-blocking issues
- `physics_source_audit`: from Step 0.65
- `spot_check_findings`: from Step 0.7
- `stability_reproducibility_audit`: from Step 0.8
