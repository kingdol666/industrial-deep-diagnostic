# Report Checklist

Use this checklist to validate the final diagnostic report.

## Structure (v6.0 — 20 sections + header + 6 appendices)

- [ ] All 20 sections are present
- [ ] Sections are in the correct order (1-20)
- [ ] Executive summary is concise (2-3 paragraphs)
- [ ] All 6 appendices present (A-F)
- [ ] Report header has scene, batch, date, run ID
- [ ] Section 2 (Reasoning Overview) populated from reasoning_chain.json with all 7 subsections (2.1-2.7)
- [ ] **Section 14 (Statistical Validation) is MANDATORY** — data sorting, Simpson's Paradox, trend confounding, adjusted confidence
- [ ] **Section 15 (Competing Hypotheses) is MANDATORY** — conditional rendering based on diagnosis_type

## Content Quality

### Executive Summary
- [ ] States what was investigated
- [ ] States what was found
- [ ] States what is recommended
- [ ] Includes overall confidence level

### Data Description
- [ ] Data source documented
- [ ] Dimensions listed (rows x columns)
- [ ] Time range specified
- [ ] Sampling rate stated
- [ ] Signal inventory table complete

### Variable Classification
- [ ] All variables classified
- [ ] Classification method described
- [ ] Uncertain classifications noted

### Preprocessing
- [ ] Missing value handling documented
- [ ] Outlier treatment described
- [ ] All transformations listed

### Visualization Interpretation
- [ ] Each key plot is described
- [ ] Visual evidence supports findings
- [ ] Plot references use specific filenames

### Visualization Evidence (Section 11)
- [ ] ALL figures from plot_manifest.json are embedded using `![title](path)` markdown
- [ ] Each embedded figure has: description, visual findings, diagnostic implication
- [ ] Every claim cites which reasoning chain link supports it ([Chain Link N])

### Diagnostic Findings
- [ ] Findings are organized by abnormal interval
- [ ] Observations, inferences, and hypotheses are separated
- [ ] [OBSERVED] and [INFERRED] clearly distinguished throughout
- [ ] Confidence levels are assigned
- [ ] Evidence citations are present

### Statistical Validation & Confidence (Section 14 — v6.0 mandatory)
- [ ] Data sorting validation — time-sorted or not, impact on lag claims
- [ ] Subgroup analysis — Simpson's Paradox checked for key correlations
- [ ] Time-trend confounding — detrended r reported for key relationships
- [ ] Adjusted confidence assessment table

### Competing Hypotheses Disclosure (Section 15 — v6.0 mandatory)
- [ ] Conditional rendering based on diagnosis_type (DETERMINED/COMPETING_SET/NEEDS_DATA)
- [ ] If COMPETING_SET: all hypotheses listed, discriminability matrix in Appendix F
- [ ] If DETERMINED: brief list of eliminated alternatives and why distinguishable

### Root Cause Analysis
- [ ] Primary hypothesis with evidence
- [ ] Alternative hypotheses listed
- [ ] Evidence gaps acknowledged
- [ ] Validation steps recommended

### Recommendations
- [ ] Prioritized action table
- [ ] Each action has rationale
- [ ] Each action has evidence reference

### Limitations (Sections 17 + 19)
- [ ] Aleatory uncertainty (irreducible) and epistemic uncertainty (reducible) properly separated
- [ ] What would change our conclusions — specific, actionable evidence
- [ ] Reasoning chain weaknesses identified
- [ ] Data limitations disclosed
- [ ] Assumptions listed
- [ ] Caveats about methodology

## Writing Quality

- [ ] Technically rigorous
- [ ] Evidence cited throughout
- [ ] Facts vs hypotheses clearly distinguished
- [ ] Uncertainty statements included
- [ ] No filler or repetition
- [ ] Units included everywhere
- [ ] Tables used for structured data
- [ ] Precise language (percentages, not "a lot")

## Anti-Speculation Compliance

- [ ] No unsupported causal claims
- [ ] All hypotheses marked as [HYPOTHESIS]
- [ ] External knowledge marked as [EXTERNAL]
- [ ] No over-claiming
- [ ] Confidence levels match evidence strength

## Completeness

- [ ] Report is self-contained
- [ ] All referenced plots exist
- [ ] All referenced data is in run directory
- [ ] Run summary is consistent with report
