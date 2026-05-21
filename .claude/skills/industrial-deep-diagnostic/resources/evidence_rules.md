# Evidence Rules for Industrial Diagnosis

## Evidence Hierarchy

| Rank | Source | Confidence | Label |
|------|--------|------------|-------|
| 1 | Direct measurements in provided data | Highest | [Evidence Rank 1] |
| 2 | User-provided documentation (SOPs, manuals) | High | [Evidence Rank 2] |
| 3 | Statistical analysis of the data | Medium-High | [Evidence Rank 3] |
| 4 | Visual evidence from charts | Medium | [Evidence Rank 4] |
| 5 | Established process logic / domain knowledge | Medium | [Evidence Rank 5] |
| 6 | External web references | Low | [Evidence Rank 6] [EXTERNAL] |
| 7 | Hypotheses (unsupported) | Lowest | [Evidence Rank 7] |

Every non-observation statement must cite its evidence rank. Conclusions drawing from multiple ranks are limited by the weakest rank.

## Anti-Speculation Rules

### Forbidden (NEVER do these)
- State "X caused Y" without temporal precedence + statistical evidence + physical mechanism + no contradictions
- Assume behavior of variables that were not measured
- Confuse correlation with causation
- Present hypotheses as established facts
- Overstate confidence beyond what evidence supports

### Required (ALWAYS do these)
- Disclose confidence level for every conclusion
- Indicate when evidence is missing or insufficient
- Separate data-derived conclusions from domain-knowledge inferences
- Recommend further validation when evidence is insufficient
- Present multiple hypotheses when root cause is uncertain

## Language Templates

| Type | Marker | Template | Example |
|------|--------|----------|---------|
| Observation | [OBSERVATION] | "[Variable] [changed] by [X%] from [T1] to [T2]." | "Transmittance decreased by 8% from 08:42 to 09:14." |
| Inference | [INFERENCE] | "This coincides with [event/measurement]." | "This coincides with a rise in oven Z2 temperature." |
| Hypothesis | [HYPOTHESIS] | "This suggests [mechanism] may have contributed." | "This suggests SSR failure may have contributed." |
| Uncertainty | [UNCERTAINTY] | "Evidence is [level] to [conclude X]." | "Evidence is insufficient to confirm the recovery mechanism." |

## Confidence Scoring

| Score | Level | Criteria |
|-------|-------|----------|
| 80-100 | HIGH | Strong direct evidence (Rank 1-2), consistent stats, no contradictions |
| 50-79 | MEDIUM | Some direct evidence, supporting stats, minor gaps |
| 20-49 | LOW | Limited evidence, mostly inference, significant gaps |
| 0-19 | VERY LOW | Speculative, little to no direct evidence |

## Causation Criteria

To state "X caused Y" you need ALL four:
1. **Temporal precedence**: X changed BEFORE Y (with measured lag)
2. **Statistical significance**: Strong correlation (|r| > 0.7) with correct lag
3. **Physical mechanism**: A plausible explanation from process logic
4. **No contradictions**: No evidence that contradicts the causal claim

If any criterion is missing, use [HYPOTHESIS] language instead of causal language.
