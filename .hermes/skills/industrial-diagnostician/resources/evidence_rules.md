# Evidence Rules for Industrial Diagnosis

## Evidence Hierarchy

| Rank | Source | Confidence | Label |
|------|--------|------------|-------|
| 1 | Direct measurements in provided data | Highest | [Evidence Rank 1] |
| 2 | User-provided documentation (SOPs, manuals) | High | [Evidence Rank 2] |
| 3 | Statistical analysis of the data (incl. validation report) | Medium-High | [Evidence Rank 3] |
| 4 | Visual evidence from charts | Medium | [Evidence Rank 4] |
| 5 | Established process logic / domain knowledge | Medium | [Evidence Rank 5] |
| 6 | External web references | Low | [Evidence Rank 6] [EXTERNAL] |
| 7 | Hypotheses (unsupported) | Lowest | [Evidence Rank 7] |

Every non-observation statement must cite its evidence rank. Conclusions drawing from multiple ranks are limited by the weakest rank.

**Statistical evidence (Rank 3) now includes validation status.** A correlation that fails validation checks (sorting, stratification, detrending) carries less weight than one that passes all checks.

---

## Anti-Speculation Rules

### Forbidden (NEVER do these)
- State "X caused Y" without ALL 5 criteria (temporal precedence + statistical evidence + lag window consistency + physical mechanism + no contradictions including within subgroups)
- Assume behavior of variables that were not measured
- Confuse correlation with causation
- Present hypotheses as established facts
- Overstate confidence beyond what evidence supports
- **Use lag correlations as causal evidence when data is NOT time-sorted** ← NEW
- **Claim an aggregate correlation is meaningful when it reverses in the dominant subgroup** ← NEW
- **Cite raw correlation without checking detrended correlation when time trends exist** ← NEW

### Required (ALWAYS do these)
- Disclose confidence level for every conclusion
- Indicate when evidence is missing or insufficient
- Separate data-derived conclusions from domain-knowledge inferences
- Recommend further validation when evidence is insufficient
- Present multiple hypotheses when root cause is uncertain
- **Report validation findings alongside statistical evidence** ← NEW
- **Acknowledge sorting/stratification/trend caveats on all key correlations** ← NEW

---

## Language Templates

| Type | Marker | Template | Example |
|------|--------|----------|---------|
| Observation | [OBSERVATION] | "[Variable] [changed] by [X%] from [T1] to [T2]." | "Transmittance decreased by 8% from 08:42 to 09:14." |
| Inference | [INFERENCE] | "This coincides with [event/measurement]." | "This coincides with a rise in oven Z2 temperature." |
| Hypothesis | [HYPOTHESIS] | "This suggests [mechanism] may have contributed." | "This suggests SSR failure may have contributed." |
| Uncertainty | [UNCERTAINTY] | "Evidence is [level] to [conclude X]." | "Evidence is insufficient to confirm the recovery mechanism." |
| Validation Finding | [VALIDATION] | "Statistical validation found [X]. Confidence adjusted from [A] to [B]." | "Stratified analysis found direction reversal in PG31DS subgroup. Confidence reduced from 75 to 50." |

---

## Confidence Scoring

| Score | Level | Criteria |
|-------|-------|----------|
| 80-100 | HIGH | Strong direct evidence (Rank 1-2), consistent stats, no contradictions, passes all validation checks |
| 50-79 | MEDIUM | Some direct evidence, supporting stats, minor gaps, minor validation concerns |
| 20-49 | LOW | Limited evidence, mostly inference, significant gaps, failed some validation checks |
| 0-19 | VERY LOW | Speculative, little to no direct evidence, major validation failures |

**Validation-adjusted confidence**: When validation checks reveal issues (Simpson's Paradox, trend confounding, sorting artifacts), confidence must be reduced from the raw evidence-based score per the adjustment rules in diagnosis_method.md.

---

## Causation Criteria (Strengthened v4.2)

To state "X caused Y" you need ALL FIVE:

1. **Temporal precedence**: X changed BEFORE Y (with measured lag AND data confirmed time-sorted by `stats.mjs` sorting validation)
2. **Statistical significance**: Strong correlation (|r| > 0.7 Pearson or Spearman) with correct lag
3. **Lag window consistency**: The correlation persists across adjacent lags (≥ 2 adjacent same-sign lags with |r| > 0.3×|best_r|), not an isolated spike
4. **Physical mechanism**: A plausible explanation from process physics/chemistry. For the claimed mechanism to be valid, the magnitude of the effect must be physically possible given the magnitude of the cause (quantitative check required)
5. **No contradictions**: No evidence that contradicts the causal claim, INCLUDING within subgroups (no Simpson's Paradox — the correlation must hold within the dominant product/grade subgroup)

If any criterion is missing, use [HYPOTHESIS] language instead of causal language.

**Note on Criterion 3**: An isolated spike at a single lag with near-zero correlations at adjacent lags is a red flag, especially when data is NOT time-sorted. In such cases, the "lag correlation" is likely a data sorting artifact (rows sorted by batch_id, not by time), not a genuine temporal relationship.

**Note on Criterion 4**: "Physical mechanism is plausible" is not enough. The mechanism must be quantitative. For example, "1-2°C temperature difference at 75-80°C causes PET thermal degradation" fails the quantitative check because PET degradation half-life at 75-80°C is months (Arrhenius extrapolation from 280°C), making the degradation rate change from 1-2°C negligible over a 9-day observation window.
