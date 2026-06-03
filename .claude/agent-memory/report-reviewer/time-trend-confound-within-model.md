---
name: time-trend-confound-within-model
description: Even when time_sorted=null, within-model time trends can reveal complete confounds — PG31DS W1C8C r=-0.964 time trend killed the H2 causal claim
metadata:
  type: project
---

**Pattern discovered**: A hypothesis (H2) survived cross-model sign consistency check and appeared to have within-model support (PG31DS r=-0.389), but the within-model correlation was 100% driven by a time trend (W1C8C r=-0.964 time trend, partial r=0.013 after controlling time).

**Why this matters**: The pipeline skipped time analysis because `time_sorted=null`. But **within each model**, data IS time-ordered (batches within the same model run sequentially). The report never checked within-model detrending.

**How to apply**: 
- Even when `time_sorted=null` globally, always check time trends within each model/group
- Variables with |r_time| > 0.7 within any model are candidates for pure time-trend confound
- For H2-type survivors (weak global signal, cross-model sign consistency), always do within-model time partialling
- `scratch_density` normalization (target / meters) can reveal meters-driven confounds — use it automatically when meters column exists

**Detection heuristic**: If a parameter shows |r_time| > 0.8 AND |r_target| > 0.3 within the same model, and partial r drops below 0.05 → time trend confound
