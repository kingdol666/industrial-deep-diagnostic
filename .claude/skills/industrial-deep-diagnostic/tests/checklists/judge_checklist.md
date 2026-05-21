# Judge Review Checklist

Use this checklist to validate the judge review process.

## Review Completeness

- [ ] All 10 criteria are evaluated
- [ ] Each criterion has a score (0-10)
- [ ] Each criterion has notes explaining the score
- [ ] Overall score is calculated with correct weights
- [ ] Verdict matches score threshold (>=90 pass, <90 repair)

## Blocking Issues

- [ ] Each blocking issue identifies the specific criterion
- [ ] Description is clear and specific
- [ ] Evidence for the issue is cited
- [ ] Repair instruction is actionable
- [ ] Affected steps are identified

## Warnings

- [ ] Each warning identifies the specific criterion
- [ ] Description is clear
- [ ] Suggestion for improvement is provided

## Evidence Gaps

- [ ] Each gap is clearly described
- [ ] Affected conclusions are listed
- [ ] Recommended action to fill the gap is provided

## Score Calculation

- [ ] Weighted sum is correct:
  - data_quality: 15%
  - variable_classification: 10%
  - time_alignment: 10%
  - visualization_quality: 10%
  - evidence_based_conclusions: 25%
  - correlation_vs_causation: 10%
  - uncertainty_disclosure: 10%
  - report_quality: 10%
  - completeness: 5%
  - (no_over_claiming: blocking, -20 if failed)

- [ ] Blocking deductions applied correctly
- [ ] Warning deductions applied correctly (-5 each)
- [ ] Final score is clamped to 0-100

## Anti-Speculation Verification

- [ ] Every conclusion has cited evidence
- [ ] No confusion between correlation and causation
- [ ] No unsupported root cause claims
- [ ] All hypotheses are clearly labeled
- [ ] All external knowledge is labeled
- [ ] Confidence levels match evidence strength
- [ ] No claims about unmeasured variables

## Iteration Tracking

- [ ] Iteration number is recorded
- [ ] Previous issues are checked for resolution
- [ ] New issues are identified if introduced by repairs
- [ ] Max iteration limit is respected
- [ ] Final iteration notes what remains unresolved (if any)

## Output Format

- [ ] `judge_feedback.json` follows the template schema
- [ ] All required fields are present
- [ ] Timestamp is included
- [ ] Score is numeric
- [ ] Verdict matches score
