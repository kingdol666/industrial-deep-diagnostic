# Pipeline Coherence & Step Synergy

> **Reference file for SKILL.md §Pipeline Coherence.** Load this when debugging pipeline integration issues, or when verifying that all steps are properly feeding each other.

## Pipeline Coherence & Step Synergy

> **This section ensures every step feeds the next with maximal effectiveness.** Each step doesn't just produce artifacts — it produces artifacts DESIGNED for the next step to consume optimally.

### Data Flow Architecture

The pipeline is designed as a **progressive enrichment chain**: each step adds a layer of understanding that the next step builds upon.



### Step Synergy Rules

These rules ensure each step maximizes the value of upstream artifacts:

| Rule | From → To | Description |
|------|-----------|-------------|
| **R2 Split** | Context Builder → Data Processor | RAG claim validation is split: context-builder does PRE-CHECKS (range, basic direction), data-processor does THOROUGH validation (lag, stratification, detrending) |
| **Physics Feeding** | Context Builder → Data Processor → Diagnostician | Physics principles extracted by context-builder guide data-processor's analysis; data-processor's physics checks feed diagnostician's hypothesis validation |
| **Expert Data Analysis Handoff** | Data Processor → Diagnostician → Judge → Reporter | Data-processor runs fixed baseline scripts, writes custom expert scripts when needed, and summarizes the evidence in `data_analysis_conclusion.json`; downstream agents consume it as the data-supported evidence package, not as a final root-cause answer |
| **VLM Visual Bridge** | Data Processor → Diagnostician → Judge → Reporter | Data-processor generates VLM-readable charts + visual_analysis.json; diagnostician fuses VLM visual insights with statistical evidence; judge verifies visual-statistical consistency; reporter presents both visual and statistical evidence per figure |
| **Bidirectional Ontology** | Context Builder ↔ Data Processor | Context-builder builds initial ontology with predicted→observed mapping; data-processor REFINES it with full-statistical insights and newly discovered discrepancy signals |
| **Discrepancy Escalation** | All → Diagnostician | Discrepancy signals (prediction≠observation) discovered at ANY step are collected in ontology.json.discrepancy_signals[] and treated as PRIMARY diagnostic inputs |
| **Physics Source Tracking** | Diagnostician → Judge → Reviewer | Physics source (pre_cached/rag_extracted/first_principles) propagates through all quality gates; confidence adjustments are verified at each stage |
| **RAG Knowledge Flow** | Context Builder → All Downstream | rag_deep_understanding.json (extracted physics, validated claims, confounders, failure modes) is consumed by data-processor, diagnostician, judge, AND report-reviewer |

### Cross-Step Verification Checklist

Before presenting results to the user, verify pipeline coherence:

- [ ] Do context-builder's predicted behaviors match data-processor's observed behaviors? If not → discrepancy signals are documented
- [ ] Does the scenario classification from data-processor align with the ontology from context-builder? If not → ontology may need updating
- [ ] Does `data_analysis_conclusion.json` exist and summarize fixed scripts, custom scripts, ontology/industry interpretation, data-supported conclusions, and handoff priorities?
- [ ] Did the diagnostician consume `data_analysis_conclusion.json` without treating its data-supported conclusions as final root-cause claims?
- [ ] Does the diagnostician use rag_deep_understanding.json extracted physics for novel parameters? If not → physics inference may be incomplete
- [ ] Does the judge verify that physics sources are properly tracked and confidence-adjusted? If not → overconfidence risk
- [ ] Does the report-reviewer cross-check the diagnosis against rag_deep_understanding.json? If not → RAG-contradicted claims may survive
- [ ] Are ontology discrepancy signals from ALL steps visible in the final diagnosis? If not → diagnostic signals were lost
- [ ] Does visual_analysis.json exist with structured VLM observations? If not → Step 3.5 VLM visual analysis was skipped
- [ ] Does the diagnostician reference visual_analysis.json observations in evidence.json? If not → visual insights were ignored
- [ ] Does the report Section 11 include VLM visual insights per figure? If not → reporter didn't consume visual_analysis.json
- [ ] Are visual observations (from VLM) and statistical correlations consistent? If not → flag as discrepancy for investigation

### RAG Knowledge Validation: Two-Stage Protocol

The R2 step (Knowledge-Data Alignment Validation) operates in TWO stages across two pipeline steps:

**Stage 1 — Pre-Checks (Context Builder, Step 2):**
- Value range validation: Are actual values within RAG-claimed normal ranges?
- Basic direction check: Does a quick correlation match RAG-claimed sign?
- Statistical signature check: Does the parameter's behavior (trending/cyclic/stationary) match expectations?
- Output:  with 

**Stage 2 — Thorough Validation (Data Processor, Step 3):**
- Temporal validation: Does X change BEFORE Y? (requires lag analysis on time-sorted data)
- Stratified validation: Does the relationship hold within product/material groups? (Simpson's Paradox check)
- Detrended validation: Does the relationship survive trend removal? (confounding check)
- Functional form validation: Does the data follow the claimed governing equation?
- Output:  with full statistical validation of every RAG claim

**The Diagnostician consumes BOTH**: pre-checks for quick signal, thorough validation for confidence.

### Artifact Completeness Requirements

Every artifact produced by each step must contain the enrichment fields needed by the next step:

| Artifact | Must Include For Downstream |
|----------|---------------------------|
| `ontology.json` (from Step 2) | , , , ,  |
| `ontology.json` (from Step 2) | , , , ,  (claims needing Stage 2) |
| `visual_analysis.json` (from Step 3) | `visual_observations[]`, `cross_parameter_temporal_alignment` (synchronous_groups, precedence_signals, independent_parameters), `synthesis` — consumed by diagnostician Phase 2.4, judge Step 0.5.9, reporter Section 11 |
| `rag_validation_report.json` (from Step 3) | Thorough validation of every RAG claim from Stage 2: temporal, stratified, detrended, functional form results |
| `rag_validation_report.json` (from Step 3) | , ,  (merged from physics_check.json) |
| `rag_validation_report.json` (from Step 3) | Data-driven scenario label (free-form, not template-matched), ,  |
|  (from Step 4) |  with source annotation, , physics source tracking per hypothesis |
|  (from Step 5) |  (NEW),  |
|  (from Step 7) | Cross-check against rag_deep_understanding.json physics principles, RAG claim validation status |

