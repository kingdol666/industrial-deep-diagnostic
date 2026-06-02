# Test Scenarios — Multi-Domain Validation Suite (v4.0)

本文件包含**端到端测试场景**，验证 rag-knowledge-builder skill 在**多个知识领域**中正确工作。

每个场景测试：
1. **领域识别** — LLM 是否正确识别了领域？
2. **跨域拒绝** — 错误域的知识块是否被正确拒绝？
3. **本体构建** — 是否构建了领域特定的实体（而非硬编码的）？
4. **自然语言定义** — 每个概念是否有精确的中文定义？
5. **约束发现** — 是否发现了至少 3 条领域约束？
6. **质量门** — 最终本体是否通过 8 维质量验证？

---

## How to Run

```python
Skill({
  skill: "rag-knowledge-builder",
  args: "domain='<DOMAIN>' target_concepts='<csv>' related_concepts='<csv>' context_dimensions='<csv>' run_dir='<RUN_DIR>' use_web='false'"
})
```

检查 `<RUN_DIR>/00_input/` 下的输出：
- `rag_ontology_draft.json` — 结构化本体
- `rag_ontology_nl_spec.md` — 自然语言规范
- `rag_structured_data.json` — 生成的模板
- `rag_audit_log.json` — 质量验证结果
- `rag_clarification_needed.json` — 知识缺口

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
| Target concept | `hba1c_pct.definition = "糖化血红蛋白占血红蛋白总量的百分比，反映过去2-3个月平均血糖水平..."` |
| Definition quality | Has `broader_concept` (如 "血糖相关生物标志物"), `distinguish_from`, `terminology` |
| Constraint | 至少 3 条（如 HbA1c ≥6.5% 诊断阈值） |
| Relationship | `fasting_glucose_mg_dl →(causal)→ hba1c_pct` (lag: weeks) |
| Confounder | `ethnicity` — different populations have different baseline HbA1c |
| Cross-domain rejection | CNC spindle chunk → REJECTED with reason "wrong domain" |
| NL Spec | 包含完整的领域概述、概念字典、关系图谱 |

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
| Target concept | `change_of_control_risk_score.definition` 包含精确定义和消歧义 |
| Constraint | 如 "非竞争条款在加州通常不可执行" |
| Relationship | `amendment_count →(legal)→ change_of_control_risk_score` |
| Confounder | `governing_law_state` — Delaware vs California |
| NL Spec | 关系图谱有条件/例外列 |

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
| Target concept | `default_probability_12m.definition` 含精确建模定义 |
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
| Target concept | `film_thickness_um.definition` 含精确物理含义 |
| Constraint | 如 "PET 熔体温度 >300°C 导致热降解" |
| Relationship | `melt_temp_C →(causal)→ film_thickness_um` (lag: seconds) |
| Confounder | `raw_material_batch_id` — PET IV varies |

**Success criteria:**

- `domain_type = "biaxial_film_stretching"`
- ≥ 6 relationships with `type = "causal"` or `"physical"`
- Verdict: `PASS` (regression test)

---

## Cross-Domain Pollution Test

**最重要的测试** — 验证不发生跨域知识泄漏。

**Setup:** ChromaDB 中混合多领域知识块：
- 8 clinical, 8 legal, 8 industrial, 4 finance, 2 generic

**Test 1:** 临床场景 → 临床 chunk ACCEPTED，其他域 REJECTED
**Test 2:** 工业场景 → 工业 chunk ACCEPTED，其他域 REJECTED
**Test 3:** 比较两次 `rag_ontology_draft.json` — 无跨域泄漏

如果错误域的实体出现在本体中（如 `mdo_oven` 出现在临床本体中），测试 FAIL。

---

## Knowledge Gap Test

**Setup:** 运行临床场景但 KB 中只有工业 chunk。

**Expected:**
- `match_rate = 0.0`
- `rag_clarification_needed.json` 至少一个条目
- `rag_audit_log.json` verdict: `FAIL`
- 不捏造临床实体

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
