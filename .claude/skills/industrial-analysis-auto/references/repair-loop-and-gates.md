# Repair Loop and Gate Discipline (moved verbatim from SKILL.md)

> The Repair Governance table and the CP quick-reference table (with the exact gate invocations) stay in
> `SKILL.md`. Repair-scope mechanics (`REPAIR_INSTRUCTIONS` / `REPAIR_SCOPE`, targeted recomputation, Judge
> re-review of in-scope dimensions only) are specified in `references/orchestration-steps.md` §Step 4 / §Step 5a.

### Repair Loop (Best-of-3)

```
best_score = -1; best_round = 0
for iter in 1..3:
  invoke industrial-diagnostician (iter 1 fresh; iter 2-3 with REPAIR_INSTRUCTIONS)
  invoke industrial-judge → score, verdict
  if score > best_score: best_score = score; best_round = iter
    snapshot 04_diagnostics/* → best_round_{iter}/
  if score >= 90: break
  if diag_iters >= 5: break (GLOBAL_CAP)
  diag_iters++; log repair_spawn event
# after loop: restore best_round_{best_round}/*
write 05_review/judge_repair_summary.json
if best_score < 90: mark [BEST_EFFORT] + confidence ≤70
write the report draft for diagnosis transparency, but finalizer keeps run status FAILED until Judge verdict=pass and all critical gates pass; never write run_completed for a best-effort draft
```

**Anti-Oscillation**: >70% issue-type overlap vs previous round → oscillation. 3rd oscillation → `COMPETING_SET`, confidence ≤50.