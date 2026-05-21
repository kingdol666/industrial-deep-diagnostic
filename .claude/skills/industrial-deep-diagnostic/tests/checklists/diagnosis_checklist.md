# Diagnosis Checklist

Use this checklist to validate the diagnostic analysis output.

## Abnormal Interval Detection

- [ ] All abnormal intervals have start and end timestamps
- [ ] Severity is assigned (low/medium/high/critical)
- [ ] Each interval has at least one observation
- [ ] Observations cite exact values and timestamps
- [ ] Duration of each interval is reasonable

## Evidence Quality

- [ ] Every observation has an evidence source
- [ ] Evidence types are correctly classified (data/stats/visual/reference/web)
- [ ] Evidence hierarchy is respected (rank 1-7)
- [ ] Web findings are labeled as EXTERNAL KNOWLEDGE
- [ ] No conclusions without supporting evidence

## Language Standards

- [ ] Observations use [OBSERVATION] language template
- [ ] Inferences use [INFERENCE] language template
- [ ] Hypotheses use [HYPOTHESIS] language template
- [ ] Uncertainties are explicitly stated
- [ ] No definitive causal claims without full evidence

## Correlation Analysis

- [ ] Temporal ordering is analyzed (cause before effect)
- [ ] Lagged correlations are computed where relevant
- [ ] Correlation is not confused with causation
- [ ] Alternative explanations are considered

## Confidence Assessment

- [ ] Confidence level assigned to every conclusion (high/medium/low)
- [ ] Confidence scores are numeric (0-100)
- [ ] Supporting evidence is listed for each conclusion
- [ ] Contradictory evidence is disclosed
- [ ] Evidence gaps are identified

## Root Cause Analysis

- [ ] Multiple hypotheses are considered
- [ ] Primary hypothesis is identified with reasoning
- [ ] Alternative hypotheses are documented
- [ ] Validation steps are recommended
- [ ] Root cause probability is estimated

## Recommendations

- [ ] Actions are prioritized (high/medium/low)
- [ ] Each action cites supporting evidence
- [ ] Actions are realistic and actionable
- [ ] No recommendations without evidence basis

## Anti-Speculation Compliance

- [ ] No unsupported root cause claims
- [ ] No assumptions about unmeasured variables
- [ ] No overstatement of confidence
- [ ] No fabrication of process behavior
- [ ] All external knowledge is labeled
