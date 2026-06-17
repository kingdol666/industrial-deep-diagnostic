---
name: bonferroni-multiple-testing-in-small-samples
description: In BOPET scratch audit, 176 params tested, H6 p=0.014 and H7 p=0.032 both fail Bonferroni (α_corrected=0.000284). Physical consistency partially compensates but must be disclosed.
metadata:
  type: feedback
---

When auditing a diagnosis with many parameters tested (~176) against a single target, the expected false positive count is ~8.8 at α=0.05. A finding of 2 "significant" correlations (p<0.05) is precisely at chance expectation. The diagnosis must disclose this. In the BOPET scratch repair audit, H6 (p=0.014) and H7 (p=0.032) were the only two signals with p<0.05 among ~176 parameters — exactly matching the expected false positive rate. The physical consistency argument (spatial adjacency + shared mechanism) provides genuine mitigation but does NOT eliminate the multiple-testing concern.

**Why:** In high-dimensional industrial datasets (hundreds of parameters), multiple testing is the dominant source of false discovery. p=0.014 sounds convincing in isolation but is expected by pure chance when testing 176 parameters. The standard for claiming "discovery" should be higher — either Bonferroni survival or strong physical prior (not post-hoc physical rationalization).

**How to apply:** Count approximate N_tests in any diagnosis. If N_tests > 20 and the top signal's p > 0.05/N_tests, flag as MODERATE. If the diagnosis does not mention multiple testing at all, flag as SERIOUS. Require disclosure of expected false positives at minimum.

Related: [[partial-correlation-independence-check]]
