---
name: industrial-html-reviewer
description: "Industrial diagnostic pipeline Step 8.5 — review of the diagnostic visualization page. Independently reviews the HTML visualization page for readability, evidence completeness, logic chain, and 3D/chart coverage. Outputs html_review.json (pass/warn/fail). Trigger: HTML review, review HTML, page review, html reviewer, audit HTML, HTML audit."
---

# Industrial HTML Reviewer

Diagnostic visualization review engine. Independently reviews whether `diagnostic-report.html` lets users without an algorithm background understand the conclusion, the evidence, and the exclusion logic. Reviews four dimensions: readability, evidence completeness, logic chain, and 3D/chart coverage. Outputs `html_review.json` containing a pass/warn/fail verdict; a failing verdict triggers html-visualizer fallback revision (max 3 attempts).

## Inputs / Outputs

### Inputs (in `RUN_DIR`)

| File | Description |
|------|-------------|
| `diagnostic-report.html` | HTML visualization page (review target) |
| `report.md` | Final diagnostic report (conclusion reference) |
| `04_diagnostics/diagnosis.json` | Diagnostic conclusion |
| `04_diagnostics/evidence.json` | Evidence list |
| `04_diagnostics/reasoning_chain.json` | Reasoning chain |
| `01_ontology/ontology.json` | Domain ontology |
| `03_figures/plot_manifest.json` | Plot manifest |
| `03_figures/visual_analysis.json` | VLM visual analysis |
| `03_figures/image_captions.json` | Image captions |
| `3d_model_data.json` | 3D model data |
| `02_processed/data_analysis_conclusion.json` | Data analysis conclusion |
| `02_processed/feature_summary.json` | Feature summary |
| `02_processed/validate_report.json` | Statistical validation report |

### Outputs

| File | Description |
|------|-------------|
| `05_review/html_review.json` | verdict + overall_score + blocking_issues + warnings + checks |



## Pipeline Event Logging

**MANDATORY** — log lifecycle events for pipeline-finalize.mjs execution proof verification:

```bash
# On start (before any work)
node "$SHARED_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" \
  --event agent_start --agent html-reviewer --step present

# On completion (after ALL outputs written)
node "$SHARED_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" \
  --event agent_complete --agent html-reviewer --step present \
  --files 05_review/html_review.json
```

These events are required by `pipeline-log-check.mjs` and `pipeline-finalize.mjs` to prove disciplined sequential execution.

## Dispatch

Launch the `html-reviewer` subagent:

```javascript
// Claude Code dispatch via Agent tool:
Agent({
  agent: "html-reviewer",
  task: `RUN_DIR=<run-dir-path>
SKILL_PATH=<path-to-.claude/skills/industrial-html-reviewer>
SHARED_PATH=.claude/shared
OUTPUT_HTML=$RUN_DIR/diagnostic-report.html
AUDIENCE=mixed

Read the agent protocol at <SKILL_PATH>/references/agent-protocol.md and execute the complete review protocol.

Key constraints:
- The first screen must lead with the conclusion — never make the user guess
- Charts must "state the conclusion" — not merely say "as shown in Figure X"
- The logic chain must not break — observation→verification→exclusion→conclusion→action
- If the page reads like a "wall of charts" or a "wall of jargon", it must not pass even if it technically renders
- Output prose in Chinese; keep enums in English
`,
  effort: "hi"
})
```

## Review Dimensions

| Dimension | Check points |
|------|----------|
| Readability | Does the first screen lead with the conclusion? Are the 10s/1min/2min goals met? |
| Evidence completeness | Does the main conclusion have chart+text evidence? Do key charts render? No chart wall? No text-image disconnect? |
| Logic chain | Observation→verification→exclusion→conclusion→action? Other causes excluded? Statistical jargon translated into plain language? |
| 3D and chart coverage | Is ECharts usable? Is Three.js usable? Does the 3D match the real process? No placeholder-only-without-explanation? |

## Pass Standard

All must hold to award `pass`:
1. A user without an algorithm background can quickly understand the conclusion
2. Every main conclusion has sufficient chart+text evidence
3. Charts and the 3D module serve understanding, not decoration
4. The logic chain is clear; readers do not have to fill in gaps themselves
5. No obvious evidence gaps or text-image disconnects

## Decision Rule

- `pass`: the page is deliverable
- `warn`: the page is usable but has optimizable items
- `fail`: the page is unacceptable and must return to html-visualizer for revision (max 3 attempts)

**If the page reads like a "wall of charts" or a "wall of jargon", it must not pass even if it technically renders.**

## Output Contract

```json
{
  "verdict": "pass",
  "overall_score": 92,
  "blocking_issues": [],
  "warnings": [],
  "checks": [
    {"name": "hero_clarity", "status": "pass", "evidence": "..."},
    {"name": "evidence_completeness", "status": "pass", "evidence": "..."},
    {"name": "logic_chain", "status": "pass", "evidence": "..."},
    {"name": "chart_init", "status": "pass", "evidence": "..."},
    {"name": "threejs_init", "status": "pass", "evidence": "..."}
  ]
}
```

## Data Truth Mandate

**Every number written to JSON must be recomputable from the raw data.**

| Rule | Requirement |
|------|------|
| Numeric traceability | Every number must state its data source (cleaned/raw), row range, and computation method |
| Derived value marking | Inferred/derived values must be explicitly marked `"derived": true` or `"inferred": true` |
| Cleaning audit trail | cleaning_integrity records all cleaning operations |
| Visualization traceability | Every data point in every chart must be traceable to specific rows of the dataset |
| Unavailable marking | Values that cannot be computed from the data → write NOT_APPLICABLE + reason |

## Counterfactual Reasoning — Exclusion Constraints

| Constraint | Description |
|------|------|
| Four conditions | Temporal precedence + statistical significance + physical mechanism + no contradiction |
| Exclusion standard | If any condition is not met → mark as an excluded candidate and provide quantitative justification |
| Physical boundary | Exclusions must be supported by first principles or governing equations |
| Confidence threshold | When exclusion confidence <80, mark `[WEAK_EXCLUSION]` |

## Assumptions & Limitations

| Category | Requirement |
|------|------|
| Data limitations | Sampling rate/noise/missing extremes/range restrictions |
| Model assumptions | Linear approximation/steady-state assumption/distribution assumptions |
| Uncontrolled confounders | Explicitly list potential confounding variables that cannot be controlled |
| Conclusion confidence intervals | Label every conclusion with confidence ± error margin |

## Efficiency — Parallel Execution

- When there is no data dependency with upstream/downstream agents → parallelize proactively
- Use deterministic scripts instead of LLM reasoning for predictable outcomes
- Large-file sampling strategy: systematic sampling when >100K rows
- Agent stall >600s → inspect existing artifacts; if partially usable, continue forward


## Verification

```bash
SKILL_PATH="<path-to-.claude/skills/industrial-html-reviewer>"
SHARED_PATH=".claude/shared"

node "$SHARED_PATH/scripts/validate.mjs" \
  "$SHARED_PATH/schemas/html_review_schema.json" \
  "$RUN_DIR/05_review/html_review.json"

test "$(wc -c < "$RUN_DIR/diagnostic-report.html")" -ge 5120
```

## Resources

All resources co-located under `.claude/skills/industrial-html-reviewer/`:

- `references/agent-protocol.md` — full HTML review protocol (persona, checklists, output validation)
- `schemas/html_review_schema.json` — JSON Schema for html_review.json


## Failure Recovery

| Scenario | Recovery |
|----------|----------|
| Schema validation fail | Fix the JSON → rewrite html_review.json → re-validate |
| HTML missing | Mark HTML_DELIVERY_FAILED → deliver report.md only |
| Review verdict fail | Trigger the revision loop (max 3) → if still failing, mark [NEEDS_MANUAL_REVIEW] |
| Agent stall | Inspect existing artifacts → if partially usable, downgrade to warn |
