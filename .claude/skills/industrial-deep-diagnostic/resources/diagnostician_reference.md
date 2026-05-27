# Diagnostician Reference — Examples & Templates

> Reference file for the Diagnostician agent (`agents/diagnostician.md`).
> Contains full worked examples, JSON output templates, and calculation illustrations.
> The Diagnostician reads this file when instructed to "see reference" for a specific step.

---

## 1. Physical Logic Chain Example (Step A.1)

Full worked example for the filter pressure → oligomer → melt_spots hypothesis:

| Link | Step | Physical Description | Evidence | Quantification |
|------|------|--------------------|----------|:-------------:|
| 1 | F_PS002@PV1 ↑ | Filter pressure rises as screen pack accumulates contaminants | [OBSERVED] r=0.55 | 2.3→4.1 bar over run |
| 2 | ΔP ↑ → flow restriction | Higher back-pressure reduces effective melt flow rate | [KNOWN_PHYSICS] Darcy's law: Q = k·A·ΔP/η | Q reduced ~18% at max ΔP |
| 3 | Flow ↓ → residence time ↑ | Slower melt flow means longer exposure to thermal history in extruder | [KNOWN_PHYSICS] τ = V/Q | τ: 4.2→5.1 min (+21%) |
| 4 | Extended heating → chain scission | PET chains undergo thermal scission; chain length ↓ → oligomer ↑ | [KNOWN_PHYSICS] Arrhenius chain scission | k(280°C) = 2.3×10⁻⁴ s⁻¹ |
| 5 | Oligomer → melt_spots | Degraded low-MW polymer forms gel spots visible in film | [OBSERVED] defect co-occurs | 0.3%→2.1% defect rate |
| 6 | Temporal direction | Granger: F_PS002 causes oligomer at lag=-2 (if time-sorted) | [INFERRED] needs verification | p=0.03 |

**Chain quality scoring**: ≥70% [OBSERVED]+[KNOWN_PHYSICS] → ACTIONABLE; 50-70% → PLAUSIBLE; >50% [INFERRED] → RESEARCH QUESTION.

---

## 2. Structured Hypothesis JSON Example (Step A.4)

```json
{
  "id": "H1",
  "name": "Filter clogging → oligomer accumulation → melt_spots",
  "mechanism_class": "WEAR",
  "root_physical_cause": "Progressive screen pack clogging at filter (F_PS002@PV1)",
  "physical_logic_chain": [
    {"link": "Filter pressure rises as contaminants accumulate", "evidence_status": "OBSERVED", "quantification": "2.3→4.1 bar"},
    {"link": "Higher ΔP reduces melt flow via Darcy's law", "evidence_status": "KNOWN_PHYSICS", "quantification": "Q reduced ~18%"},
    {"link": "Reduced flow extends residence time (τ=V/Q)", "evidence_status": "KNOWN_PHYSICS", "quantification": "4.2→5.1 min"},
    {"link": "Extended thermal exposure → PET chain scission → oligomers", "evidence_status": "KNOWN_PHYSICS", "quantification": "k(280°C)=2.3e-4 s⁻¹"},
    {"link": "Oligomers manifest as melt_spots in film", "evidence_status": "OBSERVED", "quantification": "0.3%→2.1% defect rate"}
  ],
  "chain_quality": "ACTIONABLE_HYPOTHESIS (83% OBSERVED+KNOWN_PHYSICS)",
  "quantitative_check": {
    "check_type": "ResidenceTime",
    "calculation": "τ=V/Q, V=0.12m³, Q=1.7→1.4 kg/min, τ=4.2→5.1 min",
    "result": "feasible",
    "note": "21% residence time increase is physically significant for thermal degradation"
  },
  "predicted_observables": [
    "Defect rate should correlate with cumulative filter runtime",
    "Melt_spots should decrease after filter change",
    "Oligomer concentration should correlate with filter pressure",
    "Should NOT see melt_spots in products with clean filters (low pressure)"
  ],
  "falsification_conditions": [
    "If defect rate does not decrease after filter change → hypothesis is wrong",
    "If oligomer concentration is independent of filter pressure within same filter cycle → wrong"
  ],
  "consistency_across_products": "UNIVERSAL — effect holds in PG31DS (r=0.49) and PG12 (r=0.51)",
  "product_specific_notes": {}
}
```

---

## 3. Predicted-Observable Cross-Check Example (Step B.1)

```
Hypothesis H1: Filter clogging → oligomer → melt_spots

Predicted Observable              | Data Pattern          | Result | Note
----------------------------------|-----------------------|--------|------
Defect rate correlates with       | r=0.55 overall,       | ✓      | CONFIRMED — strong, universal
filter pressure                   | r=0.49/0.51 per-product|        | across all products
                                  |                       |        |
Melt_spots decrease after         | No filter-change event| ?      | CANNOT VERIFY — no event data
filter change                     | in data window        |        | Flag: needs maintenance log
                                  |                       |        |
Oligomer correlates with          | r=0.55, CCF lag=-2    | ✓      | CONFIRMED — temporal precedence
filter pressure within lag window | (if time-sorted)      |   *    | (*) depends on sort validation
                                  |                       |        |
Should NOT see melt_spots         | MD_TH012 r_subgroup=  | ✓      | CONFIRMED — between-product only
with low filter pressure          | 0.02 (BETWEEN-PRODUCT)|        | supports mechanism
```

---

## 4. Indistinguishability Example — CNC Diagnosis (Step C.3)

**Classic failure mode**: Two root causes produce identical sensor patterns.

- **Bearing wear** → increased friction → higher temperature + higher vibration → thermal expansion + roughness
- **Tool wear** → increased cutting force → higher temperature + higher vibration → thermal expansion + roughness
- **Both produce**: temp↑, vib↑, dim_error↑, roughness↑ — ALL correlated, ALL synchronous
- **Result**: INDISTINGUISHABLE with vibration-only sensors. No amount of correlation can tell them apart.
- **Discriminating signal needed**: Vibration FFT spectrum — bearing fault frequencies (~2-10 kHz) vs tool passing frequencies (~50-200 Hz).

---

## 5. Arrhenius Physical Exclusion Example (Step D.1)

**Claim**: "MD roller temperature at 84°C causes PET thermal degradation."

```
Arrhenius: Ea = 250 kJ/mol
k(84°C) / k(280°C) = exp(-250000/8.314 × (1/357 - 1/553))
                     = 8.5 × 10^-10
At 280°C: degradation half-life ~hours
At 84°C: degradation half-life ~20,000 years
Conclusion: PHYSICALLY IMPOSSIBLE. Eliminate regardless of correlation.
```

---

## 6. Product-Stratified Exclusion JSON Example (Step D.4)

```json
{
  "hypothesis_id": "H3",
  "exclusion_type": "STATISTICAL",
  "subtype": "BETWEEN_PRODUCT_ONLY",
  "specific_evidence": "MD_TH012 overall r=0.42, per-product r=[0.02(PG31), 0.38(PG12)]. Between-product baseline difference, not causal.",
  "exclusion_confidence": 92,
  "revival_condition": "Would need within-product correlation |r|>0.3 in at least one product after controlled experiment"
}
```

---

## 7. Output File Templates (Step 6)

### 7.1 diagnosis.json

```json
{
  "run_id": "<run_id>",
  "diagnosis_type": "DETERMINED|COMPETING_SET|NEEDS_DATA",
  "primary_finding": "One-sentence summary of the primary finding",
  "product_stratified_analysis": {
    "has_product_column": true,
    "products_found": ["PG31DS", "PG12"],
    "overall_vs_per_product_comparison": [
      {
        "parameter": "MD_TH012",
        "overall_r": 0.42,
        "per_product_r": {"PG31DS": 0.02, "PG12": 0.38},
        "consistency_class": "BETWEEN-PRODUCT ONLY",
        "conclusion": "REMOVED — aggregate correlation is between-product baseline difference, not causation"
      }
    ],
    "analysis_scope": "overall_and_per_product"
  },
  "hypotheses": {
    "surviving": [],
    "competing_sets": [
      {
        "set_id": "CS1",
        "hypotheses": ["H2", "H3"],
        "discriminability": "INDISTINGUISHABLE",
        "cross_product_discriminability": "REMAINS_INDISTINGUISHABLE",
        "reason": "Both produce identical observable patterns: temp↑, vib↑, error↑.",
        "discriminating_data_needed": "Vibration FFT spectrum to distinguish mechanisms",
        "confidence_ceiling": 65
      }
    ],
    "eliminated": []
  },
  "evidence_summary": {},
  "data_gaps": [],
  "discriminability_matrix": []
}
```

### 7.2 evidence.json

```json
{
  "visual_evidence": [
    {"source": "fig_01_defect_timeseries", "finding": "Defect rate increased from 0.3% to 2.1% over the run", "rank": 4}
  ],
  "numerical_evidence": [
    {"source": "feature_summary.json", "finding": "F_PS002@PV1 vs oligomer: r=0.55, p<0.001, ρ=0.52", "rank": 3}
  ],
  "physical_evidence": [
    {"source": "Arrhenius calculation", "finding": "k(84°C)/k(280°C)=8.5e-10", "rank": 5}
  ],
  "validation_evidence": [
    {"source": "validate_report.json", "finding": "MD_TH012: BETWEEN-PRODUCT ONLY confound confirmed", "affected_hypotheses": ["H3"]}
  ]
}
```

### 7.3 confidence.json

5-factor breakdown per hypothesis:
1. **Statistical strength** (0-25): Correlation magnitude, consistency across products, validation checks passed
2. **Physical plausibility** (0-25): Quantitative mechanism check, Arrhenius/residence-time/energy-balance feasibility
3. **Temporal evidence** (0-20): Temporal precedence, CCF lag window, Granger causality
4. **Absence of confounds** (0-20): No Simpson's Paradox, no trend confounding, not outlier-driven
5. **Symptom completeness** (0-10): All predicted observables match data, no unexplained contradictions

Include an `adjustment_log` array documenting each +/- applied.
