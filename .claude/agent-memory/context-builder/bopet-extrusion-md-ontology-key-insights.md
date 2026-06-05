---
name: bopet-extrusion-md-ontology-key-insights
description: Key findings from context-builder for BOPET extrusion-MD stretch diagnostic run 202606050347392
metadata:
  type: reference
---

# BOPET Extrusion-MD Stretch Ontology Key Insights

## Critical Findings for Downstream Agents

1. **Product model is the STRONGEST confounder** — 63x difference in film_points baseline between FG22 and PG31DS. All parameter-defect correlations MUST be stratified by model (Simpson's Paradox candidate).

2. **Temperature-defect correlations are surprisingly weak** (r ≈ 0.12-0.17 for preheat/stretch, r ≈ -0.17 for quench) — temperature stability is NOT the primary defect driver in this dataset.

3. **Torque-defect correlations are unexpectedly significant** — especially quench zone torque (W1C88, r=0.37 with melt_spots) and preheat zone torque (W1C7D, r=0.34 with melt_spots). This shifts diagnostic focus from temperature to film tension.

4. **Five discrepancy signals documented** in ontology for Data Processor to investigate: (a) F_PS002 CV=0.039 exceeding 0.03 threshold, (b) Quench zone temperature volatility 10x higher than preheat/stretch (std 3.5 vs 0.3-0.4), (c) Quench temp-film_points negative correlation possibly Simpson's Paradox, (d) Torque-defect correlation stronger than temperature-defect, (e) W1C01 CV=0.185 vs W1C00 CV=0.009.

5. **RAG skill still running** — its output should be merged when available. Current knowledge based on verified parameter_mapping.json, BOPET reference docs, and web research.

6. **Validation queue** (8 items) tells Data Processor exactly which statistical validations to run.

## Files
- ontology.json (52KB) — validated against schema v6.2, 0 errors
- rag_deep_understanding.json — R2 pre-checks + validation queue
- extracted_knowledge.json — reference doc synthesis
- clarification_needed.json — auto-resolved items
- web_findings.md — external knowledge from web research