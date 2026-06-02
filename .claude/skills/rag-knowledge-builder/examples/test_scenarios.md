# Test Scenarios — Multi-Domain Validation Suite

This document contains **end-to-end test scenarios** designed to validate that the `rag-knowledge-builder` skill works correctly across **multiple knowledge domains** — not just the original industrial/CNC use case.

Each scenario tests:
1. **Domain detection** — does the LLM correctly identify the domain from the free-text description?
2. **Cross-domain rejection** — are wrong-domain chunks (from KB pollution) correctly rejected?
3. **Ontology construction** — does the LLM build domain-specific entities, not hardcoded ones?
4. **Structured data generation** — are sample rows, validation bounds, and queries domain-appropriate?
5. **Quality gate** — does the final ontology pass schema + plausibility checks?

> **No industrial-only assumptions are tested here.** A scenario is successful if a domain-agnostic LLM correctly interprets it without seeing any prior context.

---

## How to Run

For each scenario below, the calling skill should issue:

```python
Skill({
  skill: "rag-knowledge-builder",
  args: "domain='<DOMAIN>' target_concepts='<csv>' related_concepts='<csv>' context_dimensions='<csv>' run_dir='<RUN_DIR>' use_web='false'"
})
```

Then check the outputs in `<RUN_DIR>/00_input/`:
- `rag_scored_chunks.json` — chunks after 5-dim scoring
- `rag_ontology_draft.json` — LLM-built ontology
- `rag_structured_data.json` — generated templates
- `rag_audit_log.json` — provenance + verdict
- `rag_clarification_needed.json` (if any) — knowledge gaps

> **Note:** Set `use_web='false'` for deterministic offline tests. The KB must be pre-seeded with the relevant domain chunks (see `evals/seed_data/` for fixtures).

---

## Scenario 1: Clinical Medicine — Type 2 Diabetes Risk Stratification

**Domain:** Type 2 diabetes risk stratification in adult patients (target: HbA1c and 5-year cardiovascular event risk).

**Concept set:**

```
target_concepts  = "hba1c_pct,cardiovascular_event_risk_5yr"
related_concepts = "fasting_glucose_mg_dl,bmi_kg_m2,age_years,medication_dose_mg,exercise_min_week,blood_pressure_mmhg"
context_dimensions = "patient_cohort,study_site,ethnicity,measurement_batch"
```

**Expected behavior:**

| Check | Expected Result |
|-------|-----------------|
| Domain detection | `domain_type = "clinical_risk_stratification"` (NOT "industrial_process" or "generic") |
| Entity list | `pancreatic_beta_cell`, `liver`, `skeletal_muscle`, `cardiovascular_system`, `medication_metabolizer` |
| Anti-pattern entity | `spindle_assembly` MUST NOT appear |
| Target concept | `hba1c_pct.semantic_meaning = "glycated hemoglobin — 3-month average blood glucose"` |
| Validation bound | `hba1c_pct ∈ [3, 15]%` |
| Relationship | `fasting_glucose_mg_dl → glycemic_burden → hba1c_pct` (lag: weeks) |
| Confounder | `ethnicity` — different populations have different baseline HbA1c |
| Cross-domain rejection | A chunk about "CNC spindle vibration" should be REJECTED with reason "wrong domain" |

**Sample invocation:**

```python
Skill({
  skill: "rag-knowledge-builder",
  args: "domain='Type 2 diabetes risk stratification in adult patients'"
        "target_concepts='hba1c_pct,cardiovascular_event_risk_5yr'"
        "related_concepts='fasting_glucose_mg_dl,bmi_kg_m2,age_years,medication_dose_mg,exercise_min_week,blood_pressure_mmhg'"
        "context_dimensions='patient_cohort,study_site,ethnicity,measurement_batch'"
        "run_dir='/workspace/runs/test_clinical_diabetes'"
        "use_web='false'"
        "interaction_mode='auto'"
})
```

**Success criteria:**

- `domain_type = "clinical_risk_stratification"` in `rag_ontology_draft.json`
- ≥ 4 relationships in `relationships[]` with `validated_against_domain = true`
- `chunks_rejected_reasons` includes at least one entry tagged "wrong domain: industrial/CNC"
- `match_rate ≥ 0.6` (clinical KB has good coverage)
- `rag_audit_log.json` verdict: `PASS`

---

## Scenario 2: Legal — SaaS M&A Contract Review

**Domain:** M&A due diligence for SaaS targets — change-of-control and IP-assignment risk.

**Concept set:**

```
target_concepts  = "change_of_control_risk_score,ip_assignment_completeness_score"
related_concepts = "contract_type,governing_law_state,counterparty,effective_date_years,amendment_count,data_processing_clause_present"
context_dimensions = "contract_family,deal_value_band,target_subsidiary,language"
```

**Expected behavior:**

| Check | Expected Result |
|-------|-----------------|
| Domain detection | `domain_type = "legal_contract_due_diligence"` |
| Entity list | `target_company`, `counterparty`, `governing_law`, `contract_clause`, `amendment`, `signatory` |
| Anti-pattern entity | `MDO_oven` or `cnc_spindle` MUST NOT appear |
| Target concept | `change_of_control_risk_score.semantic_meaning = "probability that acquirer triggers contract change-of-control provisions"` |
| Validation bound | `change_of_control_risk_score ∈ [0, 1]` |
| Relationship | `amendment_count → carve_out_risk → change_of_control_risk_score` (lag: n/a, definitional) |
| Confounder | `governing_law_state` — Delaware vs. California changes enforceability |
| Cross-domain rejection | A chunk about "polymer crystallization" should be REJECTED |

**Sample invocation:**

```python
Skill({
  skill: "rag-knowledge-builder",
  args: "domain='M&A due diligence for SaaS target — change-of-control and IP-assignment risk assessment'"
        "target_concepts='change_of_control_risk_score,ip_assignment_completeness_score'"
        "related_concepts='contract_type,governing_law_state,counterparty,effective_date_years,amendment_count,data_processing_clause_present'"
        "context_dimensions='contract_family,deal_value_band,target_subsidiary,language'"
        "run_dir='/workspace/runs/test_legal_ma'"
        "use_web='false'"
        "interaction_mode='auto'"
})
```

**Success criteria:**

- `domain_type = "legal_contract_due_diligence"`
- ≥ 3 relationships in `relationships[]` with at least one `type = "legal"`
- `confounders[]` includes `governing_law_state` with `expected_impact = "high"`
- Verdict: `PASS`

---

## Scenario 3: Finance — Consumer Credit Risk Scoring

**Domain:** Personal loan default prediction with 12-month default probability.

**Concept set:**

```
target_concepts  = "default_probability_12m,loss_given_default_pct"
related_concepts = "fico_score,debt_to_income_ratio,annual_income_usd,employment_tenure_months,prior_defaults_count,loan_amount_usd,loan_term_months"
context_dimensions = "loan_product,underwriting_channel,origination_quarter,geography_state"
```

**Expected behavior:**

| Check | Expected Result |
|-------|-----------------|
| Domain detection | `domain_type = "consumer_credit_scoring"` |
| Entity list | `applicant`, `lender`, `credit_bureau`, `loan_product`, `underwriting_system` |
| Anti-pattern entity | `pancreatic_beta_cell` MUST NOT appear |
| Target concept | `default_probability_12m.semantic_meaning = "modeled probability of 90+ days past due within 12 months of origination"` |
| Validation bound | `default_probability_12m ∈ [0, 1]`, `loss_given_default_pct ∈ [0, 100]%` |
| Relationship | `debt_to_income_ratio → affordability_stress → default_probability_12m` (type: correlative, lag: months) |
| Confounder | `origination_quarter` — macro conditions (unemployment, rates) shift applicant pool + default base rate |
| Fairness check | If any concept is a protected class (race, gender, age-band), it MUST appear in `known_constraints` and be flagged |

**Sample invocation:**

```python
Skill({
  skill: "rag-knowledge-builder",
  args: "domain='Personal loan default prediction for US consumer credit — 12-month default probability and LGD modeling'"
        "target_concepts='default_probability_12m,loss_given_default_pct'"
        "related_concepts='fico_score,debt_to_income_ratio,annual_income_usd,employment_tenure_months,prior_defaults_count,loan_amount_usd,loan_term_months'"
        "context_dimensions='loan_product,underwriting_channel,origination_quarter,geography_state'"
        "run_dir='/workspace/runs/test_finance_credit'"
        "use_web='false'"
        "interaction_mode='auto'"
})
```

**Success criteria:**

- `domain_type = "consumer_credit_scoring"`
- ≥ 5 relationships, mostly `type = "correlative"` or `"statistical"`
- `confounders[]` includes `origination_quarter` and `geography_state`
- No protected-class concepts (race, religion, gender, etc.) in `related_concepts` — should be flagged in `clarification_needed.json` if present
- Verdict: `PASS`

---

## Scenario 4: Industrial — BOPET Film Production (Regression Test)

**Domain:** BOPET biaxially oriented film production with thickness and haze control.

**Concept set:**

```
target_concepts  = "film_thickness_um,film_haze_pct,surface_roughness_Ra_um"
related_concepts = "melt_temp_C,mdo_temp_C,tdo_temp_C,draw_ratio_mdo,draw_ratio_tdo,line_speed_m_min,pet_iv_dl_g,quench_roll_temp_C"
context_dimensions = "raw_material_batch_id,production_line_id,shift_id,operator_id"
```

**Expected behavior:**

| Check | Expected Result |
|-------|-----------------|
| Domain detection | `domain_type = "biaxial_film_stretching"` |
| Entity list | `extruder`, `mdo_oven`, `tdo_oven`, `winder`, `quench_roll` |
| Anti-pattern entity | `cardiovascular_system` or `governing_law` MUST NOT appear |
| Target concept | `film_thickness_um.semantic_meaning = "average film caliper after biaxial orientation, measured in-line by beta gauge or off-line by micrometer"` |
| Validation bound | `film_thickness_um ∈ [1, 500]`, `film_haze_pct ∈ [0, 100]%` |
| Relationship | `melt_temp_C → melt_viscosity → draw_stability → film_thickness_um` (lag: seconds) |
| Confounder | `raw_material_batch_id` — PET IV varies by batch, affects crystallinity → affects haze |

**Sample invocation:**

```python
Skill({
  skill: "rag-knowledge-builder",
  args: "domain='BOPET biaxially oriented film production — thickness and haze control with multi-stage MDO/TDO stretching'"
        "target_concepts='film_thickness_um,film_haze_pct,surface_roughness_Ra_um'"
        "related_concepts='melt_temp_C,mdo_temp_C,tdo_temp_C,draw_ratio_mdo,draw_ratio_tdo,line_speed_m_min,pet_iv_dl_g,quench_roll_temp_C'"
        "context_dimensions='raw_material_batch_id,production_line_id,shift_id,operator_id'"
        "run_dir='/workspace/runs/test_industrial_bopet'"
        "use_web='false'"
        "interaction_mode='auto'"
})
```

**Success criteria:**

- `domain_type = "biaxial_film_stretching"`
- ≥ 6 relationships with `type = "causal"` or `"physical"`
- Verdict: `PASS` (regression: still works for original industrial use case)

---

## Cross-Domain Pollution Test

This is **the most important test** — it validates that the skill does NOT leak cross-domain knowledge.

**Setup:** Seed the local ChromaDB with chunks from **multiple domains mixed together**:
- 8 chunks about clinical medicine
- 8 chunks about legal contracts
- 8 chunks about industrial polymer film
- 4 chunks about finance/credit
- 2 generic chunks (statistics, causality)

**Test 1: Clinical run with mixed KB**

Invoke Scenario 1 (clinical). Expected:

- 8 clinical chunks → ACCEPTED
- 2 generic chunks → ACCEPTED (PARTIALLY_APPLICABLE)
- 8 legal chunks → REJECTED with reason "wrong domain"
- 8 industrial chunks → REJECTED with reason "wrong domain"
- 4 finance chunks → REJECTED with reason "wrong domain"

`match_rate ≈ 0.33` (10 of 30). This is acceptable because the KB is intentionally polluted. The test passes if ALL industrial and legal chunks are rejected, NOT accepted with a fudged mapping.

**Test 2: Industrial run with mixed KB**

Invoke Scenario 4 (industrial). Expected:

- 8 industrial chunks → ACCEPTED
- 2 generic chunks → ACCEPTED
- 8 clinical chunks → REJECTED
- 8 legal chunks → REJECTED
- 4 finance chunks → REJECTED

`match_rate ≈ 0.33`.

**Test 3: Cross-domain leakage check**

After Test 1 and Test 2, compare the two `rag_ontology_draft.json` files. They should have:

| Field | Clinical run | Industrial run |
|-------|--------------|----------------|
| `scene.domain_type` | `clinical_risk_stratification` | `biaxial_film_stretching` |
| `entities[].name` | `pancreatic_beta_cell` | `mdo_oven` |
| `entities[].name` | `cardiovascular_system` | `extruder` |
| `relationships[].type` | mostly `correlative`, `regulatory` | mostly `causal`, `physical` |
| `confounders[].name` | `ethnicity`, `measurement_batch` | `raw_material_batch_id` |

If any entity from the wrong domain leaked into the ontology (e.g., `mdo_oven` appearing in the clinical run, or `pancreatic_beta_cell` appearing in the industrial run), the test FAILS.

---

## Knowledge Gap Test

**Setup:** Run Scenario 1 (clinical) with a KB that has **only industrial chunks** (no clinical content).

**Expected behavior:**

- All 10 industrial chunks → REJECTED with reason "wrong domain"
- `match_rate = 0.0`
- `rag_clarification_needed.json` written with at least one entry per target concept
- `rag_audit_log.json` verdict: `FAIL` (knowledge gap, request user to seed clinical KB or enable web search)

The skill MUST NOT invent clinical entities from industrial chunks (e.g., "if spindle is clinical, the patient is the spindle"). It must clearly report the knowledge gap.

---

## Performance / Scale Test

**Setup:** Seed KB with 1000+ chunks across 5 domains (200 each). Run all 4 scenarios in sequence.

**Expected behavior:**

- Each run completes in <60s for retrieval + LLM construction
- Memory usage stays bounded
- `match_rate` is consistent run-to-run (deterministic given same input)
- No KB pollution from previous runs (each scenario's chunks are isolated)

---

## How to Interpret Verdict

| Verdict | Meaning | Action |
|---------|---------|--------|
| `PASS` | All 5 quality dimensions pass; ontology is consumable | Proceed to consumer skill |
| `CONDITIONAL` | Minor issues; ontology is consumable with caveats | Proceed + log warnings |
| `FAIL` | Major issues; ontology NOT consumable | Re-run with feedback or escalate to human |

The verdict comes from `rag_audit_log.json → verdict` field, written by `agents/quality-verification-agent.md`.

---

## Test Result Recording

For each scenario, record:

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
  "confounders_count": 3,
  "verdict": "PASS",
  "issues": []
}
```

If any scenario fails, root-cause it: was it retrieval (Phase 1), LLM construction (Phase 2), or quality gate (Phase 4)? Each phase has its own agent prompt to debug.
