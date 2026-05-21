# Report Checklist

Use this checklist to validate the final diagnostic report.

## Structure

- [ ] All 17 sections are present
- [ ] Sections are in the correct order
- [ ] Executive summary is concise (2-3 paragraphs)
- [ ] Appendix contains supplementary data
- [ ] Report header has scene, batch, date, run ID

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

### Diagnostic Findings
- [ ] Findings are organized by abnormal interval
- [ ] Observations, inferences, and hypotheses are separated
- [ ] Confidence levels are assigned
- [ ] Evidence citations are present

### Root Cause Analysis
- [ ] Primary hypothesis with evidence
- [ ] Alternative hypotheses listed
- [ ] Evidence gaps acknowledged
- [ ] Validation steps recommended

### Recommendations
- [ ] Prioritized action table
- [ ] Each action has rationale
- [ ] Each action has evidence reference

### Limitations
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
