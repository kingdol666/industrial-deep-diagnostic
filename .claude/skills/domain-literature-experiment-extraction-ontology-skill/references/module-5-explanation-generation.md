# Module 5: Explanation Generation

> **Load this file when Module 5 is invoked.**
> Purpose: Generate human-readable scientific explanations for extracted experiment records, describing what was tested, what the results mean, and what caveats apply.

## Explanation Principles

1. **Factual, not speculative**: Every explanation must be grounded in the extracted data. If the paper doesn't explain WHY a result occurred, the explanation says "the paper does not provide a mechanism" — don't invent one.
2. **Concise, not verbose**: Each explanation targets 2-4 sentences per experiment. Scientists reading these explanations want clarity, not prose.
3. **Evidence-anchored**: Every claim in an explanation should be traceable to a specific extracted field.
4. **Caveat-aware**: If the data has limitations (low confidence, missing controls, small sample size), the explanation must acknowledge them.

## Explanation Structure

For each experiment record, generate:

```json
{
  "experiment_id": "SRC_001_E001",
  "what_was_tested": "The effect of cellulose nanocrystal (CNC) content (1-7 wt%) on the optical transparency and mechanical strength of PVA 1799 composite films prepared by solution casting.",
  "parameter_meaning": "CNC acts as a reinforcing nanofiller. At low loadings (<5 wt%), nanocellulose disperses uniformly in the PVA matrix due to hydrogen bonding between CNC hydroxyl groups and PVA hydroxyl groups, enhancing load transfer without significant light scattering. At higher loadings (>5 wt%), CNC aggregation causes light scattering (increased haze) and stress concentration points (reduced strength).",
  "result_interpretation": "Light transmittance increased from 89.2% (pure PVA) to 90.5% at 5 wt% CNC — a small but measurable improvement attributed to reduced PVA crystallite size improving optical homogeneity. Tensile strength improved 42% (45.8 → 65.3 MPa), consistent with effective stress transfer through the CNC-PVA hydrogen bond network.",
  "trend_or_pattern": "Across CNC loadings of 1, 3, 5, 7 wt%: transmittance peaks at 5 wt% then declines; tensile strength shows monotonic increase up to 5 wt% then plateaus. The optimal formulation appears to be 5 wt% CNC.",
  "hypothesis_support": "Supports the hypothesis that moderate CNC loading improves both optical and mechanical properties — contrary to the common trade-off where nanofillers improve mechanics at the expense of transparency.",
  "caveats": "1) Film thickness varied ±5 μm across samples, which may affect transmittance values. 2) CNC aspect ratio was not characterized — dispersion quality depends strongly on aspect ratio. 3) Only one PVA grade (1799, 99% hydrolysis) was tested; results may differ for partially hydrolyzed grades (1788, 0588). 4) Humidity during testing was not controlled; PVA mechanical properties are humidity-sensitive.",
  "explanation_confidence": 0.8
}
```

## Explanation Generation Rules

### what_was_tested

Construct from extracted fields:
- Material system + additive + concentration range
- Preparation method
- Properties measured

Template: "The effect of [additive] ([concentration range]) on [key properties] of [material] films prepared by [method]."

### parameter_meaning

Explain the physical/chemical role of each key parameter:
- Why does this additive matter?
- What is the mechanism of action?
- What is the expected structure-property relationship?

**Grounding rule**: If the paper explicitly states a mechanism, reference it. If the paper does not, use domain knowledge from `assets/pva_bopet_vocabulary.json` but mark it as `[domain knowledge]` in the explanation. Never claim the paper said something it didn't.

### result_interpretation

Translate numbers into meaning:
- "65.3 MPa" → "42% improvement over pure PVA"
- "90.5% transmittance" → "exceeds the 90% threshold for optical-grade films"
- "haze 2.1%" → "within acceptable range for display applications (<3%)"

**Contextualize**: A tensile strength of 65 MPa means different things for different applications. Provide application context:
- Optical display films: transmittance > 90%, haze < 2%
- Food packaging: WVTR < 10 g/(m²·day), OTR < 100 cc/(m²·day·atm)
- Agricultural films: UV stability, tensile > 20 MPa

### trend_or_pattern

Look across related records (same paper, similar formulations):
- Does the property increase, decrease, peak, plateau?
- Is the trend linear or non-linear?
- Is there an optimal formulation window?

If only a single data point exists (no comparison across formulations), state: "Single data point; no trend can be established."

### hypothesis_support

Assess whether the results align with the paper's stated hypothesis:
- **supports**: Results match the hypothesis direction and magnitude
- **partially_supports**: Results match direction but magnitude is smaller/larger than expected
- **contradicts**: Results go against the hypothesis
- **inconclusive**: Insufficient data to evaluate
- **no_hypothesis_stated**: The paper does not explicitly state a hypothesis

### caveats

Flag limitations that affect interpretation. Standard categories:

| Category | Example |
|----------|---------|
| Sample uniformity | "Film thickness varied ±5 μm; transmittance is thickness-dependent" |
| Missing characterization | "CNC dispersion quality was not verified by TEM/SEM" |
| Environmental factors | "Humidity during mechanical testing not reported; PVA is moisture-sensitive" |
| Single data point | "Only one measurement reported; no error bars to assess variability" |
| Narrow conditions | "Only tested at 25°C; behavior at elevated temperature unknown" |
| Scale limitations | "Lab-scale solution casting; industrial-scale extrusion behavior may differ" |
| Aging/stability | "Properties measured immediately after preparation; long-term stability unknown" |
| Substrate dependence | "Film measured as free-standing; properties on substrate may differ" |
| Method limitations | "Tensile tested at single strain rate; rate-dependent behavior unknown" |

### explanation_confidence

How confident is the explanation itself (separate from data confidence)?
- **0.9-1.0**: Mechanism explicitly explained in the paper; all caveats are minor
- **0.7-0.8**: Mechanism discussed but not proven; moderate caveats
- **0.5-0.6**: Mechanism inferred from related literature; significant caveats
- **0.3-0.4**: Highly speculative interpretation; major data gaps

## Multi-Experiment Synthesis

When multiple related experiments exist (e.g., same additive at different concentrations across papers), generate a **synthesis explanation** that compares across papers:

```json
{
  "synthesis_id": "SYN_CNC_loading_effect",
  "related_experiments": ["SRC_001_E001", "SRC_001_E002", "SRC_005_E010", "SRC_012_E030"],
  "property": "tensile_strength",
  "synthesis": "Across 4 papers studying CNC loading in PVA films: tensile strength consistently improves up to 5-7 wt% CNC, with gains ranging from 30-50% over pure PVA. Beyond 7 wt%, results diverge — two papers report plateauing, one reports decline, one reports continued improvement to 10 wt%. The divergence likely reflects differences in CNC source (wood vs cotton vs tunicate), aspect ratio, and dispersion method (ultrasonication vs high-shear mixing).",
  "synthesis_confidence": 0.7
}
```

## Output Formats

### Markdown Report (explanations.md)

Structured as:

```markdown
# Experiment Data Explanations
## Domain: PVA/BOPET Optical Films
## Generated: 2026-05-30

### 1. CNC-Reinforced PVA Films

#### SRC_001: Enhanced Optical and Mechanical Properties of PVA/CNC Composite Films (Zhang et al., 2023)

**Experiment SRC_001_E001 — PVA/CNC-5%**
- **What was tested**: ...
- **Parameter meaning**: ...
- **Result**: ...
- **Caveats**: ...

...

### 2. Crosslinked PVA Films
...
```

### Structured JSON (explanations.json)

Array of explanation objects, as shown above.

## Script Execution

```bash
python scripts/generate_explanations.py \
  --input 03_normalized/experiments_normalized.json \
  --output 05_explanations/explanations.json \
  --language zh
```

The LLM generates the explanation content; the script handles formatting, file output, and cross-referencing.

## Edge Cases

| Scenario | Action |
|----------|--------|
| Paper is in Chinese | Generate explanations in Chinese (default). Translation quality affects confidence. |
| Paper reports ONLY properties, no discussion/conclusion | Generate factual interpretation but set `explanation_confidence: 0.5` and note "no author interpretation available" |
| Paper has contradictory claims (text says one thing, conclusion says another) | Note the contradiction in caveats; prioritize the data section over the conclusion section |
| Two papers report conflicting trends for the same system | Generate separate explanations; in synthesis, highlight the conflict with both citations |
| Record has low data confidence (<0.5) | Still generate explanation, but prefix with "⚠️ Low data confidence:" and reduce explanation_confidence proportionally |