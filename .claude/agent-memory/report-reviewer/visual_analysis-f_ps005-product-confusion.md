---
name: visual_analysis-f_ps005-product-confusion
description: VLM metadata_backed_inference模式将跨产品F_PS005异常值(12.5bar)错误分配给PG31DS，导致H3假说基于事实错误
metadata:
  type: reference
---

F_PS005 product attribution error in visual_analysis.json and diagnosis.json: VLM using metadata_backed_inference mode confused cross-product F_PS005 values (PG32B=11.6, PG32M=11.5, FP41=11.6) as PG31DS within-product values. Actual PG31DS F_PS005 range is only 7.4-8.0 bar, W1C01 is constant at 7.12 RPM. This fed into diagnosis.json H3 as "step_change +63%" — a factual error. Impact: H3 must be downgraded or eliminated.

**Why**: visual_analysis.json's `observation_mode: metadata_backed_inference` cannot distinguish which product's data points belong to which subgroup when processing aggregate visual metadata. Cross-product max values were attributed to the focus product.

**How to apply**: Any pre-audit or report audit for BOPET scratch must independently verify F_PS005 product-level values. When visual_analysis.json uses metadata_backed_inference, cross-reference all "step change" claims against actual per-product min/max ranges.
