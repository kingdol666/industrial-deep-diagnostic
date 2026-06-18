---
name: pg32d-w1c81-regime-shift-hidden-from-torque-collapse-narrative
description: PG32D W1C81 (R6 torque) narrative of "15-20 to 5.85 collapse" was false — actual range 9.73-50.20 pre-5/12, regime-shifted to -5.30 mean from 5/12 onwards; H2652721 5.85 was first batch of new regime, not a single-batch anomaly
metadata:
  type: reference
---

The BOPET scratch diagnosis report claimed PG32D extreme batch H2652721 had "R6 torque collapsed from 15-20 to 5.85 (drop >50%)" as a key supporting evidence for H1 (mechanical scraping). **Independent verification found this claim is factually wrong:**

- PG32D W1C81 before 2026-05-12 (7 batches, all normal scratch): range [9.73, 50.20], mean=32.12
- PG32D W1C81 from 2026-05-12 onwards (9 batches): range [-9.57, 5.85], mean=-5.30
- H2652721 W1C81=5.85 is the **first batch of the new regime**, at the upper end of the new regime
- Subsequent batches (H2652722: -3.84, H2652723: -9.07) have even lower W1C81 but normal scratch rates
- The "normal 15-20" cited in the report does not exist in any batch

**Why:** This was missed by both pre-flight audit (which focused on PG31DS torque z-scores) and all intermediate checks. The pre-flight audit looked at PG31DS and FP21 torque but never systematically verified PG32D W1C81 range claims. The regime shift (positive to negative mean on 5/12) was not detected.

**Impact on diagnosis:** Does not overturn H1 (isolated event pattern and short meter count still hold), but significantly weakens the "R6 torque collapse" evidence. The torque behavior is more likely a systematic setpoint change coinciding in time with a mechanical scraping event, not a direct mechanical event signal.

**Recommendation:** During audit, always verify ALL torque/parameter "normal range" claims against actual data distributions, not just the subset the report highlights. Interval-switch detection (mean shift >2sigma sustained >3 batches) should be automated in preprocessing.

Related memories: [[partial-correlation-independence-check]], [[fp21-double-detrend-pearson-spearman-divergence]]
