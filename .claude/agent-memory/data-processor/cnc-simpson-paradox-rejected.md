---
name: cnc-spindle-wear-simpson-paradox-rejected
description: CNC spindle wear analysis revealed material-based Simpson Paradox hypothesis was NOT confirmed — time confounding was the true mechanism
metadata:
  type: project
---

In the CNC spindle wear evaluation run (2026-06-03), the Context Builder predicted that material differences (AL6061/AL7075/SS304) caused a Simpson's Paradox for the spindle_speed→Ra and feed_rate→Ra negative correlations. My stratified analysis conclusively showed **NO Simpson reversal**: within each material, the negative direction was maintained (r=-0.90 to -0.97). The true confounder was **time** — as the day progressed, operators reduced speed/feed for SS304 while simultaneously vibration and temperature (and thus Ra) rose from bearing degradation.

**Why this matters:** Ontology-based Simpson Paradox predictions must be tested, not accepted. The material-stratified analysis showed that the ontology's confounder hypothesis was wrong. The correct confounder (time) was not listed as the primary candidate.

**How to apply:** In future multi-material runs with strong time trends, check time confounding as the primary candidate before accepting material-confounding hypotheses. Validate by: (1) per-material correlation direction, (2) detrending, (3) examining temporal ordering of material runs vs parameter drift.
