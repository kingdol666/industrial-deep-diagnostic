# Industrial Diagnostic Report

**Scene**: {{scene_name}}
**Batch**: {{batch_id}}
**Date**: {{date}}
**Run ID**: {{run_id}}

---

## 1. Executive Summary

{{executive_summary}}

## 2. Reasoning Overview

{{reasoning_overview}}

This section provides the step-by-step reasoning trace that led to the diagnosis.

### 2.1 Data Characterization
{{reasoning_data_char}}

### 2.2 Statistical Discovery
{{reasoning_stat_discovery}}

### 2.3 Validation Filter
{{reasoning_validation_filter}}

### 2.4 Hypothesis Evolution
{{reasoning_hypothesis_evolution}}

### 2.5 Key Inferences vs Observations
{{reasoning_inference_vs_observation}}

### 2.6 What We Ruled Out
{{reasoning_ruled_out}}

### 2.7 Uncertainty Boundaries
{{reasoning_uncertainty_bounds}}

## 3. Analysis Objective

{{analysis_objective}}

## 4. User Context and Constraints

{{user_context}}

## 5. Industrial Context and Ontology

### 5.1 Process Description
{{process_description}}

### 5.2 Equipment Overview
{{equipment_overview}}

### 5.3 Process Stages
{{process_stages}}

## 6. Reference Documents Used

{{references_used}}

## 7. External Research Used

> **Note**: All findings in this section are labeled as EXTERNAL KNOWLEDGE and are not data-derived.

{{external_research}}

## 8. Data Description

### 8.1 Data Summary

| Column | Type | Unit | Category | Missing % | Outlier % |
|--------|------|------|----------|-----------|-----------|
{{data_summary_table}}

### 8.2 Sampling Characteristics
{{sampling_characteristics}}

### 8.3 Data Quality Assessment
{{data_quality_assessment}}

## 9. Variable Classification

{{variable_classification}}

## 10. Preprocessing & Alignment

{{preprocessing_methods}}

{{time_alignment}}

## 11. Visualization Evidence — Per-Figure Analysis

> **Every figure from 03_figures/ is embedded here. Each figure includes visual findings and diagnostic implications.**

### 11.1 {{figure_1_title}}
![{{figure_1_title}}](03_figures/{{figure_1_filename}})

**What this figure shows**: {{figure_1_description}}

**Visual findings ([OBSERVATION], Rank 4)**: {{figure_1_visual_findings}}

**Diagnostic implication**: {{figure_1_implication}}

---

### 11.2 {{figure_2_title}}
![{{figure_2_title}}](03_figures/{{figure_2_filename}})

**What this figure shows**: {{figure_2_description}}

**Visual findings ([OBSERVATION], Rank 4)**: {{figure_2_visual_findings}}

**Diagnostic implication**: {{figure_2_implication}}

---

### 11.N {{figure_N_title}}
![{{figure_N_title}}](03_figures/{{figure_N_filename}})

**What this figure shows**: {{figure_N_description}}

**Visual findings ([OBSERVATION], Rank 4)**: {{figure_N_visual_findings}}

**Diagnostic implication**: {{figure_N_implication}}

---

*(Repeat for every plot in plot_manifest.json. Do not skip any figure.)*

## 12. Diagnostic Findings

### 12.1 Evidence-Eliminated Hypotheses
{{eliminated_hypotheses}}

### 12.2 Surviving Hypotheses with Reasoning
{{surviving_hypotheses}}

### 12.3 Causal Chain Models
{{causal_chain_models}}

## 13. Root Cause Conclusion

> **This section presents the SINGLE most probable root cause, determined by converging data evidence, physical principles, and logical reasoning. It is NOT a list of possibilities — it is the definitive diagnosis.**

### 13.1 Root Cause Statement

**Root Cause**: {{root_cause_statement}}

{{root_cause_narrative}} — a single coherent paragraph connecting: which parameter deviated, when, by how much, through what physical mechanism, producing which defect.

### 13.2 Integrated Evidence Chain

#### Data Evidence
| Evidence | Value | Source |
|----------|-------|--------|
| Time-matched correlation (optimal lag) | r = X.XX at lag +N | feature_summary.json CCF |
| Correlation survives detrending | detrended r = X.XX (attenuation X%) | validate_report.json |
| Correlation holds within dominant subgroup | r = X.XX in [subgroup name] | validate_report.json |
| Granger causality direction | [X] → [D], p = X.XX | feature_summary.json |
| Temporal precedence confirmed | [Parameter] changes [N] rows before [defect] | CCF lag analysis |
| Outlier check | Correlation NOT outlier-driven | validate_report.json |

#### Physical Mechanism
- **Mechanism**: {{physical_mechanism_description}}
- **Causal chain**: [Parameter deviation] [OBSERVED/INFERRED] → [Intermediate change] [OBSERVED/INFERRED] → [Defect manifestation] [OBSERVED/INFERRED]
- **Magnitude verification**: {{quantitative_magnitude_check}}

#### Logical Chain
- **[OBSERVED] links**: {{count}} / {{total}} — directly supported by data
- **[INFERRED] links**: {{count}} / {{total}} — logically inferred from evidence
- **Alternatives ruled out**: {{list_with_specific_evidence}}
- **Falsification condition**: {{what_would_disprove_this_conclusion}}

### 13.3 Contributing Factors (if any)

{{contributing_factors}} — secondary factors that amplify or enable the primary root cause, clearly distinguished from the primary diagnosis.

### 13.4 Confidence Assessment

| Dimension | Score | Max |
|-----------|:---:|:---:|
| Data Strength | XX | 35 |
| Physical Mechanism | XX | 35 |
| Logical Coherence | XX | 30 |
| **Total Confidence** | **XX** | **100** |

**Key uncertainties**: {{uncertainty_summary}}

## 14. Recommended Actions

| Priority | Action | Parameter | Current | Target | Expected Effect | Verification |
|----------|--------|:---:|:---:|:---:|---|------|
| P0 | {{immediate_action}} | ... | ... | ... | ... | ... |
| P1 | {{short_term_action}} | ... | ... | ... | ... | ... |

## 15. Limitations & Uncertainty

### 15.1 Aleatory Uncertainty (Irreducible)
{{aleatory_uncertainty}}

### 15.2 Epistemic Uncertainty (Reducible)
{{epistemic_uncertainty}}

### 15.3 What Would Change Our Conclusions
{{what_would_change_conclusions}}

## 16. Limitations

{{limitations}}

## 17. Appendix

### A. Run Configuration
{{run_configuration}}

### B. Statistical Summary
{{feature_summary}}

### C. Change Point Log
{{change_point_log}}

### D. File Inventory
{{file_inventory}}

### E. Hallucination Audit Log
{{hallucination_audit_log}}
