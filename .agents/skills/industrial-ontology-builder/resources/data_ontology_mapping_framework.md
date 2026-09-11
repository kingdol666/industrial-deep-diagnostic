# Data ↔ Ontology Deep Mapping Framework

> **Reference file for SKILL.md §Data↔Ontology Mapping.** Load this when the context-builder agent (Step 2) builds the ontology, or when the data-processor (Step 3) updates it with new statistical discoveries.

## Data ↔ Ontology Deep Mapping Framework

> **The ontology is not a static document — it's a living model that co-evolves with data understanding.**

### Mapping Direction 1: Ontology → Data (Prediction & Validation)

The ontology makes TESTABLE PREDICTIONS about what the data should show:

| Ontology Claim | Testable Prediction | Validation Method |
|---------------|-------------------|-------------------|
| "X is a temperature sensor" | Values should be positive, within physically plausible range for the process, with characteristic thermal time constants | Check value range, autocorrelation structure, rate of change |
| "X causes Y via mechanism M" | Changes in X should precede changes in Y by time lag τ; the functional form should match M's governing equation | Cross-correlation at lag τ; curve fitting to governing equation form |
| "X is a setpoint, not a measurement" | X should change in discrete steps; variance should be lower than measurements; X should lead its corresponding measurement | Step detection; variance comparison; lead-lag analysis |
| "X and Y are confounded by Z" | Within each level of Z, the X-Y correlation should change (weaken, reverse, or disappear) | Stratified correlation by Z |

**When ontology predictions are CONFIRMED by data**: Increase confidence in both the ontology and the diagnosis.

**When ontology predictions are CONTRADICTED by data**: This is a VALUABLE DIAGNOSTIC SIGNAL. It means either:
- The ontology is wrong (wrong domain, wrong assumptions)
- The process is operating abnormally (the anomaly IS the story)
- The parameter measures something different from what we think

### Mapping Direction 2: Data → Ontology (Discovery & Refinement)

Statistical patterns in the data SUGGEST ontology refinements:

| Data Pattern | Ontology Implication |
|-------------|---------------------|
| Two parameters have near-identical time series (|r| > 0.95) | They likely measure the same physical quantity, or one is a setpoint and the other is its measurement |
| A parameter has a bimodal distribution | It's likely a discrete state (on/off, product A/B) or a parameter with two operating regimes |
| A parameter shows step changes coinciding with categorical column changes | It's likely a setpoint that varies by product grade |
| A parameter has a monotonic trend over the entire time range | It's a degradation indicator (wear, fouling, aging) — mark as degradation_candidate |
| A parameter's variance changes at specific times | Regime shift — may indicate maintenance event, grade change, or failure onset |

### Mapping Direction 3: Discrepancy as Diagnostic Signal

When ontology expectations and data observations MISMATCH, extract diagnostic value:

| Discrepancy | Diagnostic Meaning |
|-------------|-------------------|
| Parameter supposed to be stable but shows trend | Degradation in progress |
| Parameter supposed to correlate but doesn't | Control system compensating effectively, or physics model wrong |
| Quality supposed to reset on maintenance but doesn't | Root cause is upstream of the maintained component |
| Two parameters supposed to be independent but correlate | Hidden confounder or unexpected physical coupling |

### The Deep Mapping Checklist

Before the Diagnostician runs, for EVERY parameter in the analysis:

- [ ] What PHYSICAL QUANTITY does this parameter measure? (not just column name)
- [ ] What GOVERNING EQUATION controls its behavior?
- [ ] What is its expected RELATIONSHIP to quality targets? (predicted by ontology + physics)
- [ ] What does the DATA actually show? (observed relationship)
- [ ] If expected ≠ observed: WHY? (this is the diagnostic insight)
