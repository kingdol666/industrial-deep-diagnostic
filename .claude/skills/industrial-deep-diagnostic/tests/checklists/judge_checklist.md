# Judge Review Checklist

Use this checklist to validate the judge review process.

## Review Completeness (v6.0 — 10 weighted criteria + 1 blocking criterion)

- [ ] All 10 weighted criteria are evaluated (1-8, 10) + reasoning_chain_quality (5.5)
- [ ] No over-claiming (criterion 9) checked for blocking issues
- [ ] Each criterion has a score (0-10)
- [ ] Each criterion has notes explaining the score
- [ ] Overall score is calculated with correct weights
- [ ] Score ceilings applied (85 for sorting issues, 65 for indistinguishable hypotheses)
- [ ] Verdict matches score threshold (>=90 pass, 70-89 needs_repair, 50-69 major_issues, <50 fail)

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

## Score Calculation (v6.0 weights — MUST match judge.md)

- [ ] Weighted sum is correct:
  - data_quality_awareness: 10%
  - variable_classification: 10%
  - time_alignment_and_sorting: 10%
  - visualization_quality: 5%
  - evidence_based_conclusions: 20%
  - reasoning_chain_quality: 15%  (NEW v6.0 — Chain-of-Thought audit)
  - correlation_vs_causation: 10%
  - uncertainty_disclosure: 10%
  - report_quality: 5%
  - completeness: 5%
  - (no_over_claiming: blocking, -20 per violation)

- [ ] Blocking deductions applied correctly (-20 per violation)
- [ ] Warning deductions applied correctly (-5 per warning)
- [ ] Score ceilings checked:
  - Score ≤ 85 if `sorting_validation.time_sorted == false` AND lag used as primary evidence
  - Score ≤ 65 if diagnosis assigns >65 to single indistinguishable hypothesis
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
