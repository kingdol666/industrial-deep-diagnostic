# [Scenario Name] Industrial Diagnostic Report

**Scenario**: {{scene_name}} | **Product/Batch**: {{batch_id}} | **Date**: {{date}} | **Run ID**: {{run_id}}
**Diagnostic Rating**: {{judge_score}}/100 — {{judge_verdict}}

> **Output language (binding)**: the generated `report.md` is written in **Chinese** — section headings, table headers, and reader-facing prose included. The section-heading contract is enforced against the Chinese heading strings by `industrial-reporter/scripts/report-section-check.mjs` and `scripts/pipeline-finalize.mjs`; the authoritative Chinese scaffold is `industrial-reporter/templates/report_template.md`. Emit the report in Chinese even though this structural reference is in English. Only this template's `[WRITING]` notes are English, and they are never carried into the report.

> **Reading guide**: Section 1 is the one-page summary for decision makers. Section 2 is the core — it presents the alignment charts and fluctuation interpretation of every product's process parameters against its inspection metrics. Sections 3-4 explain the diagnostic result and the evidence. Sections 5-6 hold the detailed reasoning and data (for the technical team). Section 7 is the executable action plan.

> **Statement of factual honesty**: every conclusion in this report derives from actual measured data, statistical validation, physical-mechanism derivation, and VLM image observation. Each conclusion carries an evidence grade (L1 = highest, L7 = lowest). Statements tagged `[HYPOTHESIS]` are not yet fully verified. Reasoning steps tagged `[INFERENCE_GAP]` contain an evidential leap. Where the evidence is insufficient to support a definite conclusion, this report will honestly present competing hypotheses rather than fabricate a single root cause.

---

## 1. Executive Summary

> **This page is written for the plant director and the general manager. It reads in 2 minutes.**

### What happened?

{{what_happened}}

**[WRITING]**: Which production line, which product, what time window, and what anomaly occurred? How severe is it? Speak with concrete numbers.

---

### Why did it happen?

**Most likely cause: {{root_cause_one_liner}}**

{{why_it_happened}}

**[WRITING]**: Explain the root cause in the plainest possible language. If you can explain the physical mechanism with an everyday analogy, do (for example, "just like ice cream melting faster in summer"). Do not use jargon.

---

### How large is the impact?

{{business_impact}}

**[WRITING]**:
- Scope of impact: how much output is affected? Which products?
- Severity: the defect rate rose from X% to Y% — what does that mean?
- If the boss reads only one page, this is the number they need most.

---

### Recommended Actions

| Priority | Action | Expected Effect | Timeframe | Rough Cost |
|:------:|------|---------|------|:------:|
| **P0** | {{action_p0}} | {{effect_p0}} | {{time_p0}} | {{cost_p0}} |
| **P1** | {{action_p1}} | {{effect_p1}} | {{time_p1}} | {{cost_p1}} |
| P2 | {{action_p2}} | {{effect_p2}} | {{time_p2}} | — |

**[WRITING]**: P0 = must be executed within this week, with no production stop or only a brief stop. P1 = planned within this month. P2 = once conditions mature.

---

### How confident are we?

**Overall confidence: {{confidence_score}}/100 ({{confidence_level}})**

In plain words: {{confidence_plain_language}}

**[WRITING]**: Translate the confidence score into plain language. For example: "Out of 100 similar diagnoses, our judgement was correct roughly 78 times. The biggest uncertainty is that we have no measured temperature for Zone Z3, only its setpoint."

---

## 2. Time-Aligned Analysis of Process Parameters and Inspection Metrics (Core Evidence / Alignment Charts)

> **This is the single most important evidence section in the whole report.** Every alignment chart places ALL process parameters and inspection metrics on one shared time axis, so the reader can see directly "who changed first, who changed later, who changed together". This is the decisive evidence for the direction of causation.

**[WRITING]**:
- If there are several products, show the alignment chart for the key product (highest defect rate) first, then the others
- Each product's alignment chart needs its own subsection covering: what the chart shows → what the statistics say → does it hold up physically
- If the alignment charts reveal no clear association between any process parameter and any inspection metric, say so explicitly — do not fabricate

---

{{#each product_alignment_sections}}

### 2.{{index}} {{product_label}} — Time Alignment of Process Parameters and Inspection Metrics

![Time-alignment chart](03_figures/{{overlay_figure}})

#### What the chart shows (VLM visual observation)

{{vlm_observation}}

**[WRITING]**:
- Describe the synchronously fluctuating parameter groups the VLM observed in the chart
- Point out which parameters changed first and which inspection metrics changed later
- Mark the evident anomaly windows (time interval + parameter name + magnitude of change)
- If no clear alignment pattern is visible, write: "In the time-alignment chart for {{product_label}}, no clear synchronous fluctuation pattern was observed between any process parameter and any inspection metric"

#### What the statistics say

{{statistical_story}}

**[WRITING]**:
- Cite the statistical correlation figures for the synchronised parameter groups the VLM observed (r / ρ / p-value / CCF lag)
- Cite the statistical validation results (does significance survive detrending? is it consistent within product subgroups?)
- If the VLM observation and the statistics disagree, disclose that explicitly

#### Does it hold up physically?

{{physical_story}}

**[WRITING]**:
- Draw on the physical meaning and process-stage attribution of that parameter in ontology.json
- Explain why fluctuation in this process parameter would (or would not) cause a change in the inspection metric
- If the ontology contains no physical mechanism for that parameter, tag it `[PHYSICS_UNVERIFIED]`
- If it does not hold up physically but is statistically significant, tag it `[STATISTICAL_WITHOUT_PHYSICS]`

#### Key diagnostic finding for this product

{{product_key_finding}}

**[WRITING]**: State in one sentence the core finding of this product's alignment-chart analysis, and what that finding contributes to the overall diagnosis.

---

{{/each}}

### 2.X Cross-Product Comparison

{{cross_product_comparison}}

**[WRITING]**:
- Is the behaviour of the same process parameter consistent across products?
- If a parameter fluctuates only in the key product and is stable elsewhere → product-level problem
- If a parameter fluctuates in all products at once → process-level problem
- Is there an obvious parameter step when products are switched?

---

### 2.Y Overall Conclusion of the Alignment-Chart Analysis

{{alignment_overall_conclusion}}

**[WRITING]**:
- The core finding distilled from all alignment charts: which process parameters are candidate drivers of the quality anomaly
- Which process parameters are visually excluded (no synchronous relationship with any other parameter or quality metric)
- If no clear process-parameter-to-inspection-metric association was found in any alignment chart, write: "The time-alignment analysis found no clear association pattern between any process parameter and any inspection metric. The current data does not support determining a causal driver from temporal precedence."

---

## 3. Diagnosis

> **This section expands the conclusion from Section 1 — written for the technical lead, but still intelligible to non-technical readers.**

### 3.1 What went wrong

{{problem_description}}

**[WRITING]**: Describe the anomaly. Include the most critical trend overlay chart (process and defect on the same chart).

![Key trend](03_figures/{{key_trend_figure}})

**What this chart tells us**: {{figure_key_message}}

---

### 3.2 Why it happened this way

{{mechanism_explanation}}

**[WRITING]**:
- Explain the physical mechanism in plain language. Give the conclusion first, then the explanation.
- Must include an everyday analogy: "just like ______"
- Highlight key numbers in bold
- Where the physics is uncertain, state that honestly

---

### 3.3 What we ruled out

| Ruled-Out Possible Cause | Why It Was Ruled Out | Evidence Strength |
|--------------|-----------|:------:|
| {{eliminated_1}} | {{eliminated_1_reason}} | ★★★☆☆ |
| {{eliminated_2}} | {{eliminated_2_reason}} | ★★★★☆ |

**[WRITING]**: Let the reader know we did not fixate on a single answer, but systematically worked through several possibilities. This adds persuasiveness.

---

### 3.4 Diagnostic Conclusion Summary

- **Diagnosis type**: {{diagnosis_type_display}}
- **Overall confidence**: {{confidence_score}}/100 ({{confidence_level}})
- **If this conclusion is wrong, the most likely reason is**: {{falsification_condition_plain}}
- **To improve our confidence we need**: {{next_evidence_needed_plain}}

---

## 4. Evidence Panorama

> **One chart tells it all: how reliable is our conclusion?** — lets the technical lead assess diagnostic quality quickly.

### 4.1 Key Evidence Chain

```
Data observation        Statistical analysis         Physical verification        Conclusion
────────────────        ────────────────────         ─────────────────────        ──────────
{{obs_1}}        →      {{stat_1}}            →      {{phys_1}}            →      main conclusion
{{obs_2}}        →      {{stat_2}}            →      (insufficient data)   →      secondary finding
```

**[WRITING]**: Use the simplest possible flow diagram to show "how the evidence walked step by step to the conclusion". One sentence per node.

### 4.2 Conclusion Reliability Overview

| Conclusion | Statistical | Physical | Temporal | Confounder-Free | Overall | Confidence |
|------|:---:|:---:|:---:|:---:|:---:|------|
| {{h1_name}} | ★★★★☆ | ★★★☆☆ | ★★★★☆ | ★★★★☆ | **{{h1_score}}** | {{h1_level}} |
| {{h2_name}} | ☆☆☆☆☆ | ★★☆☆☆ | ☆☆☆☆☆ | — | **Ruled out** | — |

**[WRITING]**: ★ = weak, ★★★★★ = strong. This is the technical lead's quick reference for "how much of this should I believe".

---

## 5. Key Findings in Detail

> **Each important finding gets its own section, fully unfolding the six-step derivation "observation → statistics → physics → image → exclusion → judgement".**

{{#each key_findings}}

### 5.{{index}} {{finding_title}}

#### What we saw

{{observations}}

**[WRITING]**:
- Write the concrete time points, parameter names, and magnitudes of change
- "Z3 temperature rose from 82 °C to 89 °C (+7 °C), during 3–9 January"
- "Over the same period, the temperature changes in Z1, Z2 and Z4 were all below 1 °C" (comparison reference)
- Include the key time-series chart

![Time-series comparison](03_figures/{{fig_timeline}})

**Visible in the chart**: {{fig_timeline_observation}}

---

#### What the data says

{{statistical_story}}

**[WRITING]**: Key rule — every statistical term gets a plain-language translation.

| Statistical Metric | Value | Plain-Language Translation |
|---------|------|---------|
| Spearman correlation coefficient | ρ = {{r_value}} | "Temperature and defects have a {{r_strength}} positive correlation" |
| p-value | {{p_value}} | "The chance that this association is coincidence is below {{p_chance}}" |
| CCF lag analysis | lag = {{best_lag}} | "The temperature change appears roughly {{lag_time}} before the defect" |
| Within-product-group check | ρ = {{within_prod_r}} | "Looking at each product separately, the association is still there" |
| Detrend check | ρ = {{detrended_r}} | "After removing the time trend the association is still {{detrend_strength}}" |

**Supporting charts**: scatter plot or CCF plot

![Correlation analysis](03_figures/{{fig_correlation}})

---

#### Does it hold up physically?

{{physical_story}}

**[WRITING]**:
- **Analogy**: "Z3 temperature rises → PET molecular chains crystallise more readily during stretching → the film surface becomes uneven → the inspection equipment flags it as a defect. This is just like ______."
- **Quantitative calculation** (if available): "A 7 °C temperature rise increases the crystallisation rate by roughly 23% — a magnitude sufficient to produce a detectable change on the film surface."
- **Honest statement of uncertainty**: "This calculation uses a typical activation energy for PET (about 150 kJ/mol); we do not have the precise activation energy for this batch of raw material."

---

#### Why it is not something else

{{alternatives_excluded}}

- **Raw-material batch problem**: {{why_not_raw_material}}
- **Temperature in other zones**: {{why_not_other_zones}}
- **Environmental factors**: {{why_not_environment}}

---

#### How much confidence do we have in this finding?

**Individual finding confidence: {{finding_confidence}}/100**

| Assessment Dimension | Score | Plain-Language Note |
|---------|:---:|---------|
| Statistical evidence | {{stat_score}}/25 | "The association between the data and the defects is solid — it survived all 4 checks" |
| Physical plausibility | {{phys_score}}/25 | "It holds up physically, but we lack the precise value of one key parameter" |
| Temporal precedence | {{temp_score}}/20 | "The temperature really did change before the defects, consistent with 'cause before effect'" |
| Exclusivity | {{conf_score}}/20 | "The main alternative explanations are ruled out, but one secondary factor still has no data" |
| Symptom completeness | {{symp_score}}/10 | "It explains the main defect type, but not the spatial distribution pattern" |

**If this finding is wrong**: {{falsification_condition}}

{{/each}}

---

## 6. How We Reached the Conclusion — Detailed Derivation of the Reasoning Process

> **This section is for anyone who wants the complete reasoning logic.** It tells the story of "how we narrowed the suspect pool step by step".

### 6.1 Step one: what alarms did the data raise?

{{reasoning_step1}}

**[WRITING]**: Extract from `reasoning_chain.json` R1-R2. Which anomalies were found first? Which parameters triggered alarms? Rank by degree of anomaly.

### 6.2 Step two: which misleading signals did validation rule out?

{{reasoning_step2}}

**[WRITING]**: Extract from R2-R3. Which signals that initially looked important were ruled out by validation?
- Is the data sorted by time? (If not, lag analysis is unreliable)
- Does mixing products together produce spurious associations? (Simpson's Paradox check)
- Are the parameters merely "moving along with time"? (Detrend check)

### 6.3 Step three: what did the physical laws screen out for us?

{{reasoning_step3}}

**[WRITING]**: Extract from R5-R6. Which statistical correlations stand up physically? Which do not?

### 6.4 Final judgement: why is this the most likely answer?

{{reasoning_final}}

**[WRITING]**: Summarise the logic that selected the final answer out of several hypotheses. If no single root cause can be determined, present the competing hypotheses honestly.

---

## 7. Data and Statistical Support

> **This section is for the technical team to verify against.** All raw statistical data and the validation process are here.

### 7.1 Data Overview

| Item | Detail |
|------|------|
| Data source | {{data_source}} |
| Time range | {{time_range}} |
| Data volume | {{row_count}} rows × {{col_count}} columns |
| Data quality | {{data_quality_summary}} |
| Steady-state data | {{steady_state_info}} |

### 7.2 Core Statistical Results

| Parameter Pair | Pearson r | Spearman ρ | p-value | Best Lag | Lagged CCF | Within-subgroup ρ | Detrended ρ | Decay Rate |
|--------|:--------:|:--------:|:---:|:------:|:-----:|:------:|:------:|:-----:|
{{correlation_table}}

### 7.3 Statistical Validation Details

#### Simpson's Paradox check

| Parameter Pair | Full-data r | Key-product-group r | Same Direction? | Conclusion |
|--------|:-----:|:-------:|:--------:|------|
{{simpson_table}}

#### Trend-confounding check

| Parameter Pair | Raw r | Detrended r | Decay Rate | Conclusion |
|--------|:---:|:-----:|:-----:|------|
{{detrend_table}}

#### Correlation robustness

| Parameter Pair | Pearson | Spearman | Difference | Outlier-driven? |
|--------|:------:|:------:|:---:|:----------:|
{{robustness_table}}

### 7.4 Confidence Breakdown

{{#each confidence_breakdowns}}

**{{hypothesis_name}}** — {{total_score}}/100 ({{level}})

| Factor | Score | Max | Why This Score |
|------|:---:|:---:|-------------|
| Statistical strength | {{s1}} | 25 | {{n1}} |
| Physical plausibility | {{s2}} | 25 | {{n2}} |
| Temporal evidence | {{s3}} | 20 | {{n3}} |
| Confounder-free | {{s4}} | 20 | {{n4}} |
| Symptom completeness | {{s5}} | 10 | {{n5}} |

**Confidence adjustment log**:
{{#each adjustments}}
- {{adjust_reason}} → {{adjust_amount}} points (source: {{adjust_source}})
{{/each}}

{{/each}}

### 7.5 Visual Evidence Index

| No. | Figure | One-line Finding | Conclusion Supported | Diagnostic Implication |
|:---:|------|----------|:----------:|---------|
{{figure_index}}

---

## 8. Action Plan

> **This section is for the execution team.** Every action is concrete, verifiable, and costed.

### 8.1 P0 — Immediate Action (within this week)

| Action | Concrete Steps | Expected Effect | How to Verify | Timeframe | Rough Cost |
|------|---------|---------|---------|:--:|:------:|
{{p0_actions}}

**[WRITING]**: P0 = affects safety or causes major loss; it cannot wait. Each item must state the concrete steps, the quantified target, the verification method, the time required, and the cost.

### 8.2 P1 — Short-Term Plan (within this month)

| Action | Concrete Steps | Expected Effect | How to Verify | Timeframe |
|------|---------|---------|---------|:--:|
{{p1_actions}}

### 8.3 P2 — Medium-Term Plan (once conditions mature)

| Action | Concrete Steps | Preconditions |
|------|---------|---------|
{{p2_actions}}

### 8.4 Action-Effect Monitoring

| Monitoring Metric | Current Baseline | Target Value | Monitoring Frequency | Alarm Threshold |
|---------|:------:|:----:|:------:|:------:|
{{monitoring_table}}

---

## 9. What We Still Do Not Know — Limitations and Follow-Up Work

> **Honesty is the best way to build trust.** This section tells the reader where our blind spots are.

### 9.1 Limitations of the current diagnosis

| Type | Specific Limitation | Impact on the Conclusion |
|------|---------|:----------:|
| Data blind spot | {{data_blind_spot}} | {{data_blind_impact}} |
| Method limitation | {{method_limit}} | {{method_impact}} |
| Physical uncertainty | {{physics_uncertainty}} | {{physics_impact}} |

### 9.2 What new evidence would overturn our conclusion?

{{what_would_change}}

**[WRITING]**: Extract from each hypothesis's `falsification_conditions`. Must be concrete and actionable. Do not write "more data"; write "if in the next batch the Z3 temperature returns to 82 °C but the defect density does not fall".

### 9.3 Recommended follow-up diagnostic steps

{{next_steps}}

**[WRITING]**: State what additional data must be collected, what controlled tests must be run, and what physical verification must be added in order to further improve the accuracy and confidence of the diagnosis.

---

## Appendix

### A. Run Configuration
{{run_config}}

### B. Statistical Summary
{{statistical_summary}}

### C. Competing-Hypothesis Discriminability Matrix
{{discriminability_matrix}}

### D. File Inventory
{{file_inventory}}

### E. Detailed Data Quality Report
{{data_quality_detail}}
