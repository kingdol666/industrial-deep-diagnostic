# Industrial Diagnostic Report

**Scene**: {{scene_name}}
**Batch**: {{batch_id}}
**Date**: {{date}}
**Run ID**: {{run_id}}

---

## 1. Executive Summary

{{executive_summary}}

## 2. Analysis Objective

{{analysis_objective}}

## 3. User Context and Constraints

{{user_context}}

## 4. Industrial Context and Ontology

### 4.1 Process Description
{{process_description}}

### 4.2 Equipment Overview
{{equipment_overview}}

### 4.3 Process Stages
{{process_stages}}

## 5. Reference Documents Used

{{references_used}}

## 6. External Research Used

> **Note**: All findings in this section are labeled as EXTERNAL KNOWLEDGE and are not data-derived.

{{external_research}}

## 7. Data Description

### 7.1 Data Summary

| Column | Type | Unit | Category | Missing % | Outlier % |
|--------|------|------|----------|-----------|-----------|
{{data_summary_table}}

### 7.2 Sampling Characteristics
{{sampling_characteristics}}

### 7.3 Data Quality Assessment
{{data_quality_assessment}}

## 8. Variable Classification

{{variable_classification}}

## 9. Preprocessing Methods

{{preprocessing_methods}}

## 10. Time Alignment Strategy

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

{{diagnostic_findings}}

## 13. Root Cause Analysis

{{root_cause_analysis}}

## 14. Confidence and Uncertainty

{{confidence_and_uncertainty}}

## 15. Recommended Actions

| Priority | Action | Rationale | Evidence |
|----------|--------|-----------|----------|
{{recommendations_table}}

## 16. Limitations

{{limitations}}

## 17. Appendix

### A. Run Configuration
{{run_configuration}}

### B. Feature Summary Statistics
{{feature_summary}}

### C. Change Point Log
{{change_point_log}}

### D. Full Correlation Matrix
{{correlation_matrix}}

### E. File Inventory
{{file_inventory}}
