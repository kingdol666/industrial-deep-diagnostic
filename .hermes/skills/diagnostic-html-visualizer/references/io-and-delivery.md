# IO Contracts, Delivery & Closeout (moved verbatim from SKILL.md)

> The slim `SKILL.md` keeps the required/optional inputs, the default outputs and the invocation protocol;
> this file carries the artifact read-priority table, the 12 page requirements, the consumer-call invocation
> example, the efficiency rules, pipeline event logging and the deliverable closeout.

## Language Default

Default output language is Chinese: page copy, chart captions, evidence-chain explanations, and action
recommendations are written in Chinese; structured field names, code variable names, and JSON enum values remain
in English. Canonical statement: `references/format-rules.md` §1.

---

### Expected Artifacts

Read the following files with priority; use what exists, degrade for what does not:

| Priority | File | Purpose |
|----------|------|---------|
| P0 | `report.md` | Final conclusions, action recommendations, limitations |
| P0 | `04_diagnostics/diagnosis.json` | Main conclusion, competing hypotheses, confidence, exclusions |
| P0 | `04_diagnostics/evidence.json` | Evidence stratification and supporting details |
| P0 | `04_diagnostics/reasoning_chain.json` | How the conclusion converged step by step |
| P1 | `01_ontology/ontology.json` | Production-line objects, ontology relations, section structure |
| P1 | `02_processed/data_analysis_conclusion.json` | Data-analysis conclusions and interpretation bridge |
| P1 | `02_processed/causal_evidence_map.json` | Structured input for the causal chain |
| P1 | `03_figures/plot_manifest.json` | Inventory and titles of existing charts |
| P1 | `03_figures/*.png` / `*.jpg` | Ready-made visual evidence — reused first by the evidence-chain blocks |
| P1 | `03_figures/visual_analysis.json` | VLM-inferred chart observations and diagnostic meaning |
| P1 | `03_figures/image_captions.json` | Chart caption fallback |
| P1 | `3d_model_data.json` | 3D scene entities, temperature zones, roll positions, anomaly points |
| P1 | `viz_model_data.json` | Optimized visualization model data (if present) |
| P2 | `viz_data.json` / `viz_compact.json` / `diagnostic_data.json` | Data summaries the page can reuse directly |
| P2 | `02_processed/feature_summary.json` / `validate_report.json` / `anomaly_report.json` | Supplementary statistics and robustness information |
| P2 | `.pipeline_events.jsonl` | Optional process execution narrative and timeline |

---

## Output Contract — the 12 page requirements

The page must satisfy:

1. Single-file HTML that opens directly
2. All four narrative sections present
3. At least one ECharts chart module
4. At least one simplified Three.js 3D module if section structure is obtainable
5. ECharts and Three.js must be loaded through a multi-source loader, and the page must render a 5-item loader status strip
6. If remote scripts fail to load, the page must still retain static text, summary cards, and local image evidence
7. Unless the user explicitly allows it, a page whose components failed to load must not be treated as a finished deliverable
8. The page must include a conclusion-first first-screen summary and a concise "how I arrived at this conclusion" path
9. The page must control information density, prioritizing the 3-5 most critical pieces of evidence; dumping all charts flat as the main content is not allowed
10. After generation, the page must be reviewed by the `html-reviewer` QA sub-agent; on failure it returns for revision (up to 3 revision loops)
11. The evidence chain must be complete in all three layers, each supported by real images/data/physical reasoning; missing any one layer → page fails
12. `render_manifest.json` must be produced first; page section/card/chart/evidence-layer counts must align with the manifest one by one, and manifest values must be traceable to run_dir (no cross-run contamination)

---

## Invocation Protocol

### Standalone

When the user explicitly provides a diagnostic directory and requests front-end visualization, invoke this skill directly.

Example:

```text
/diagnostic-html-visualizer build run_dir="<absolute-path-to-your-run-dir>"
```


---

### Consumer-Call from industrial-deep-diagnostic

When the main diagnostic skill has finished and the user asks for "an HTML visual explainer page / front-end report / dashboard / visualized evidence chain":

1. The main agent must not improvise a page by itself
2. Invoke this skill directly
3. This skill spawns its own sub-agent to generate the page

Recommended invocation form:

```text
Skill({
  skill: "diagnostic-html-visualizer",
  args: "build run_dir='<current_run_dir>' output_html='<current_run_dir>/diagnostic-report.html' audience='mixed' visual_mode='story'"
})
```

---

## Efficiency — Parallel Execution

- When there is no data dependency with upstream/downstream agents → parallelize proactively
- Use deterministic scripts instead of LLM reasoning for predictable results
- Large-file sampling strategy: systematic sampling when >100K rows
- Agent stall >600s → check existing artifacts; continue with partially available results

---

## Assumptions & Limitations

|Category|Requirement|
|---|---|
|Data limitations|Sampling rate / noise / missing extremes / range limits|
|Model assumptions|Linear approximation / steady-state assumption / distribution assumptions|
|Uncontrolled confounders|Explicitly list potential confounding variables that cannot be controlled|
|Conclusion confidence interval|Each conclusion annotated with confidence ± error margin|

---

## Data Truth Mandate

**Every number written into JSON/reports must be recomputable from the raw data.** The full rule table (number
traceability, derived-value marking, cleaning audit trail, visualization traceability, unavailable marking,
no-cross-run-contamination) lives once in `references/format-rules.md` §2 — the builder and reviewer skills point
there instead of restating it.

---

## Counterfactual Reasoning — Exclusion Constraints

The four exclusion conditions (temporal precedence + statistical significance + physical mechanism + no
contradiction), the quantitative exclusion standard, the physical-boundary rule, and the `[WEAK_EXCLUSION]`
threshold (<80) live once in `references/format-rules.md` §3.

---

## Pipeline Event Logging

```bash
node "$SHARED_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" \
  --event agent_complete --agent html-visualizer --step present \
  --files diagnostic-report.html
```

---

## Deliverable Closeout

When done, you must tell the caller:

1. Which key files were read
2. Where the HTML was written
3. Which content reused existing images directly and which charts were regenerated
4. Which data sources each of the three evidence-chain layers used (which came from 03_figures PNGs, which were redrawn from JSON)
5. If further optimization is desired, which evidence layer or interaction is most worth strengthening

Before delivery also confirm:

- Whether `html-reviewer` passed
- If it did not pass, whether the blockers were fed back to `html-visualizer` for revision