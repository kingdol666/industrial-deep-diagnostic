---
name: partial-correlation-independence-check
description: Two correlated predictor hypotheses (W1C8B_std and W1C89_std) claimed as independent corroboration — partial correlation showed both become non-significant when controlling for the other
metadata:
  type: feedback
---

When multiple hypotheses use correlated predictor variables (detrended r > 0.5 between them), NEVER accept "independent corroboration" claims without computing partial correlations (each ~ target | the other). In BOPET scratch repair round #1, H6 and H7 were presented as "two independent signals" for stick-slip at adjacent quenching rolls (#14 and #16). Independent verification found detrended W1C8B_std vs W1C89_std r=0.615 (37.8% shared variance), and **both partial correlations were non-significant**: W1C8B~scratch|W1C89 rho=0.325(p=0.175), W1C89~scratch|W1C8B rho=0.184(p=0.450). The joint R^2=0.273 vs W1C8B alone R^2=0.243 — W1C89 adds only ΔR^2=0.030. This means H7 is a corroborating measurement of the same underlying drive-system dynamics, NOT an independent hypothesis.

**Why:** Correlated predictors in a small sample (n=19) can create the illusion of two independent discoveries when they are in fact two noisy measurements of one underlying phenomenon. The pipeline must compute partial correlations before allowing "independent corroboration" as a confidence boost.

**How to apply:** In any audit where N>=2 hypotheses use correlated predictors (|r|>0.5), run partial correlation analysis. If both partial correlations are non-significant, flag as OVERCLAIMING (SERIOUS). The hypotheses should be merged or one downgraded to corroborating measurement.

Related: [[within-product-trend-confounding]], [[cross-model-consistency-is-not-causal]]
