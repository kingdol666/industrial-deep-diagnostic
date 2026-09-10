# Test Scenarios — Multi-Domain Validation Suite (v4.0)

This file contains **end-to-end test scenarios** that verify that the rag-knowledge-builder skill works correctly across **multiple knowledge domains**.

Each scenario tests:
1. **Domain identification** — did the LLM correctly identify the domain?
2. **Cross-domain rejection** — are knowledge chunks from the wrong domain correctly rejected?
3. **Ontology construction** — were domain-specific entities built (rather than hard-coded ones)?
4. **Natural-language definitions** — does every concept have a precise definition, written in the configured output language (default: Chinese)?
5. **Constraint discovery** — were at least 3 domain constraints discovered?
6. **Quality gate** — does the final ontology pass the 8-dimension quality verification?

---

## How to Run

```python
Skill({
  skill: "rag-knowledge-builder",
  args: "domain='<DOMAIN>' target_concepts='<csv>' related_concepts='<csv>' context_dimensions='<csv>' run_dir='<RUN_DIR>' use_web='false'"
})
```

Inspect the outputs under `<RUN_DIR>/00_input/`:
- `rag_ontology_draft.json` — structured ontology
- `rag_ontology_nl_spec.md` — natural-language specification
- `rag_structured_data.json` — generated templates
- `rag_audit_log.json` — quality verification results
- `rag_clarification_needed.json` — knowledge gaps

---

## Scenario 1: Clinical Medicine — Type 2 Diabetes Risk Stratification

**Domain:** Type 2 diabetes risk stratification in adult patients.

```
target_concepts  = "hba1c_pct,cardiovascular_event_risk_5yr"
related_concepts = "fasting_glucose_mg_dl,bmi_kg_m2,age_years,medication_dose_mg,exercise_min_week,blood_pressure_mmhg"
context_dimensions = "patient_cohort,study_site,ethnicity,measurement_batch"
```

**Expected behavior:**

| Check | Expected Result |
|-------|-----------------|
| Domain detection | `domain_type = "clinical_risk_stratification"` |
| Entity list | `pancreatic_beta_cell`, `liver`, `skeletal_muscle`, `cardiovascular_system` |
| Anti-pattern entity | `spindle_assembly` MUST NOT appear |
| Target concept | `hba1c_pct.definition = "糖化血红蛋白占血红蛋白总量的百分比，反映过去2-3个月平均血糖水平..."` (the produced definition is written in the configured output language; default: Chinese) |
| Definition quality | Has `broader_concept` (e.g. "血糖相关生物标志物"), `distinguish_from`, `terminology` |
| Constraint | At least 3 (e.g. HbA1c ≥6.5% 诊断阈值) |
| Relationship | `fasting_glucose_mg_dl →(causal)→ hba1c_pct` (lag: weeks) |
| Confounder | `ethnicity` — different populations have different baseline HbA1c |
| Cross-domain rejection | CNC spindle chunk → REJECTED with reason "wrong domain" |
| NL Spec | Contains the complete domain overview, concept dictionary, and relationship graph |

**Success criteria:**

- `domain_type = "clinical_risk_stratification"` in `rag_ontology_draft.json`
- ≥ 4 relationships with `validated_against_domain = true`
- `chunks_rejected_reasons` includes at least one "wrong domain" entry
- `match_rate ≥ 0.6`
- `rag_audit_log.json` verdict: `PASS`
- `rag_ontology_nl_spec.md` contains all 9 sections

---

## Scenario 2: Legal — SaaS M&A Contract Review

**Domain:** M&A due diligence for SaaS targets.

```
target_concepts  = "change_of_control_risk_score,ip_assignment_completeness_score"
related_concepts = "contract_type,governing_law_state,counterparty,effective_date_years,amendment_count,data_processing_clause_present"
context_dimensions = "contract_family,deal_value_band,target_subsidiary,language"
```

**Expected behavior:**

| Check | Expected Result |
|-------|-----------------|
| Domain detection | `domain_type = "legal_contract_due_diligence"` |
| Entity list | `target_company`, `counterparty`, `governing_law`, `contract_clause` |
| Anti-pattern entity | `MDO_oven` MUST NOT appear |
| Target concept | `change_of_control_risk_score.definition` contains a precise definition and disambiguation |
| Constraint | e.g. "非竞争条款在加州通常不可执行" |
| Relationship | `amendment_count →(legal)→ change_of_control_risk_score` |
| Confounder | `governing_law_state` — Delaware vs California |
| NL Spec | The relationship graph has conditions/exceptions columns |

**Success criteria:**

- `domain_type = "legal_contract_due_diligence"`
- ≥ 3 relationships with at least one `type = "legal"`
- `confounders[]` includes `governing_law_state`
- Verdict: `PASS`

---

## Scenario 3: Finance — Consumer Credit Risk Scoring

**Domain:** Personal loan default prediction.

```
target_concepts  = "default_probability_12m,loss_given_default_pct"
related_concepts = "fico_score,debt_to_income_ratio,annual_income_usd,employment_tenure_months,prior_defaults_count,loan_amount_usd,loan_term_months"
context_dimensions = "loan_product,underwriting_channel,origination_quarter,geography_state"
```

**Expected behavior:**

| Check | Expected Result |
|-------|-----------------|
| Domain detection | `domain_type = "consumer_credit_scoring"` |
| Entity list | `applicant`, `lender`, `credit_bureau`, `loan_product` |
| Target concept | `default_probability_12m.definition` contains a precise modelling definition |
| Constraint | "模型不得使用受保护特征" (ECOA) |
| Relationship | `debt_to_income_ratio →(correlative)→ default_probability_12m` |
| Confounder | `origination_quarter` — macro conditions shift applicant pool |

**Success criteria:**

- `domain_type = "consumer_credit_scoring"`
- ≥ 5 relationships, mostly `type = "correlative"` or `"statistical"`
- Verdict: `PASS`

---

## Scenario 4: Industrial — BOPET Film Production (Regression Test)

**Domain:** BOPET biaxially oriented film production.

```
target_concepts  = "film_thickness_um,film_haze_pct,surface_roughness_Ra_um"
related_concepts = "melt_temp_C,mdo_temp_C,tdo_temp_C,draw_ratio_mdo,draw_ratio_tdo,line_speed_m_min,pet_iv_dl_g,quench_roll_temp_C"
context_dimensions = "raw_material_batch_id,production_line_id,shift_id,operator_id"
```

**Expected behavior:**

| Check | Expected Result |
|-------|-----------------|
| Domain detection | `domain_type = "biaxial_film_stretching"` |
| Entity list | `extruder`, `mdo_oven`, `tdo_oven`, `winder` |
| Anti-pattern entity | `cardiovascular_system` MUST NOT appear |
| Target concept | `film_thickness_um.definition` contains the precise physical meaning |
| Constraint | e.g. "PET 熔体温度 >300°C 导致热降解" |
| Relationship | `melt_temp_C →(causal)→ film_thickness_um` (lag: seconds) |
| Confounder | `raw_material_batch_id` — PET IV varies |

**Success criteria:**

- `domain_type = "biaxial_film_stretching"`
- ≥ 6 relationships with `type = "causal"` or `"physical"`
- Verdict: `PASS` (regression test)

---

## Cross-Domain Pollution Test

**The most important test** — verifies that no cross-domain knowledge leakage occurs.

**Setup:** Multi-domain knowledge chunks mixed in ChromaDB:
- 8 clinical, 8 legal, 8 industrial, 4 finance, 2 generic

**Test 1:** Clinical scenario → clinical chunks ACCEPTED, other domains REJECTED
**Test 2:** Industrial scenario → industrial chunks ACCEPTED, other domains REJECTED
**Test 3:** Compare the two `rag_ontology_draft.json` files — no cross-domain leakage

If an entity from the wrong domain appears in the ontology (e.g. `mdo_oven` appearing in a clinical ontology), the test FAILS.

---

## Knowledge Gap Test

**Setup:** Run the clinical scenario while the KB contains only industrial chunks.

**Expected:**
- `match_rate = 0.0`
- `rag_clarification_needed.json` contains at least one entry
- `rag_audit_log.json` verdict: `FAIL`
- No fabricated clinical entities

---

## Test Result Recording

```json
{
  "scenario_id": "scenario_1_clinical_diabetes",
  "run_dir": "/workspace/runs/test_clinical_diabetes",
  "timestamp": "2026-06-02T10:00:00Z",
  "match_rate": 0.67,
  "domain_type_detected": "clinical_risk_stratification",
  "chunks_accepted": 10,
  "chunks_rejected": 5,
  "wrong_domain_rejections": 5,
  "relationships_count": 8,
  "constraints_count": 5,
  "nl_spec_sections": 9,
  "verdict": "PASS",
  "issues": []
}
```
