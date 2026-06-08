---
name: tool-age-effect-masked-by-dominant-vibration
description: In CNC diagnosis, tool_age showed Spearman-Pearson divergence (0.150) and strong correlation in low-vibration quartiles (r=0.57-0.61) despite global r=0.145, revealing that tool wear effect is real but masked by dominant vibration signal.
metadata:
  type: reference
---

When the dominant process parameter (e.g., vibration at r=0.993) completely overpowers a known physical effect (e.g., tool wear), simple global correlations underestimate the weaker effect. In the 202606081402243 CNC diagnosis:

- Global tool_age-roughness: Pearson r=0.145, Spearman rho=0.295
- Low-vibration quartile (0.10-0.66 mm/s): r=0.574
- High-vibration quartile (1.07-2.52 mm/s): r=-0.063

The effect is **not absent** -- it is **masked by range restriction** in one dimension. After the dominant cause is fixed (bearing replacement, vibration drops to <1mm/s), the previously hidden secondary effect (tool wear) will become detectable again.

**How to apply**: When any process parameter shows r > 0.9 with quality, always check whether weaker-but-known-physical effects (tool wear, coolant flow, depth of cut) are genuinely absent or merely masked. Use **stratified correlation by quartiles of the dominant parameter**, not just by product/material. This is especially important for exclusion claims about well-established physical mechanisms.
