---
name: industrial-html-visualizer
description: "Industrial diagnostic pipeline Step 8 — builds an explanatory ECharts+Three.js HTML visualization page from diagnostic artifacts. Reuses the templates, design system, and Fallback rules of the diagnostic-html-visualizer skill. The conclusion must be above the fold, charts are evidence rather than decoration, and the 3D model must tell the truth. Do NOT use without CP-8 ENDORSED optimizer.md. Trigger: HTML visualization, generate HTML, frontend page, visualization report, html visualization, diagnostic HTML, 3D scene, ECharts."
---

# Industrial HTML Visualizer

Frontend visualization build engine for diagnostic results. Reuses the ECharts/Three.js templates, design system, CSS variables, visual grammar, and Fallback rules of the `diagnostic-html-visualizer` skill to generate a single-file explanatory HTML page from diagnostic artifacts.

**Hard prerequisite**: the CP-8 ENDORSED audit verdict (`optimizer.md`). Without optimizer.md → refuse to execute and report "missing CP-8 ENDORSED audit verdict" to the main agent.

## Inputs / Outputs

### Inputs (in `RUN_DIR`)

| File | Description |
|------|-------------|
| `optimizer.md` | **CP-8 ENDORSED** audit verdict (hard prerequisite) |
| `report.md` | Diagnostic report |
| `04_diagnostics/diagnosis.json` | Diagnostic conclusion |
| `04_diagnostics/evidence.json` | Evidence list |
| `04_diagnostics/reasoning_chain.json` | Reasoning chain |
| `04_diagnostics/confidence.json` | Confidence assessment |
| `01_ontology/ontology.json` | Domain ontology (3D section recovery) |
| `02_processed/data_analysis_conclusion.json` | Data analysis conclusion (data governance audit trail) |
| `03_figures/plot_manifest.json` | Plot manifest |
| `03_figures/visual_analysis.json` | VLM visual analysis |
| `03_figures/image_captions.json` | Image captions |
| `03_figures/*.png` | Ready-made visual evidence |
| `3d_model_data.json` | 3D model data (if present) |

When P0 files are missing, execute the corresponding branch of the `skill://diagnostic-html-visualizer` §Fallback Rules.

### Outputs

| File | Description |
|------|-------------|
| `diagnostic-report.html` | Single-file HTML ≥5120B, including ECharts + Three.js + data governance card |



## Pipeline Event Logging

**MANDATORY** — log lifecycle events for pipeline-finalize.mjs execution proof verification:

```bash
# On start (before any work)
node "$SHARED_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" \
  --event agent_start --agent html-visualizer --step present

# On completion (after ALL outputs written)
node "$SHARED_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" \
  --event agent_complete --agent html-visualizer --step present \
  --files diagnostic-report.html
```

These events are required by `pipeline-log-check.mjs` and `pipeline-finalize.mjs` to prove disciplined sequential execution.

## Dispatch

Launch the `html-visualizer` subagent (persona: Lin Gong — industrial frontend visualization engineer):

```javascript
Agent({
  subagent_type: "html-visualizer",
  prompt: `RUN_DIR=<run-dir-path>
SKILL_PATH=<path-to-.claude/skills/industrial-html-visualizer>
SHARED_PATH=<path-to-.claude/shared>
OUTPUT_HTML=<run-dir-path>/diagnostic-report.html
AUDIENCE=mixed
VISUAL_MODE=story

## Protocol

1. First read "skill://diagnostic-html-visualizer" — load the ECharts/Three.js templates, design system, Fallback rules, and visual standards
2. Then read "$SKILL_PATH/references/agent-protocol.md" — execute the complete checklist
3. Execute the checklist Phases 1-4 in order

## Key requirements
- ECharts for statistical charts (correlation, time series, anomaly overlays)
- Three.js for 3D process flow (recover real stages from ontology, NOT generic factory)
- Runtime readiness: window.echarts, window.THREE, OrbitControls — multi-source CDN with degraded static fallback
- Interactive evidence chain navigation (three-layer closure: statistics→physics→exclusion)
- Chinese language interface
- Data governance card from data_analysis_conclusion.json
- On completion, report the 11-item output contract to the main agent`,
  effort: "hi"
})
```

## Execution Flow

Full protocol in `references/agent-protocol.md`. On-demand references at `skill://diagnostic-html-visualizer`.

| Phase | Purpose |
|-------|---------|
| 1 — Data Governance | Read `data_analysis_conclusion.json` → render the data governance audit-trail card (what was cleaned, rows affected, reasons, data sources) |
| 2 — Build Page | Hero above the fold (answer conclusion/location/cause/action within 10 seconds) → core evidence area (3-5 charts, each answering what is seen / what it indicates / why it matters) → 3D scene (recover real process sections/equipment/material flows from the ontology) → Runtime Readiness (multi-source CDN + degradation detection) |
| 3 — CP-8 Gate | `html-reviewer` review. verdict must be `pass` to complete; `warn`/`fail` falls back to Phase 2 (max 3 attempts) |
| 4 — Output Contract | Report 11 items to the main agent: source files, output path, chart/3D status, degradation mode, 3D modeling basis, anomaly mapping, 10s/1min/2min readability tiers, core evidence selection, reviewer status, data governance audit trail |

### Runtime Readiness (mandatory)

The page must self-check and report:
- `window.echarts` available → at least one chart initialized successfully
- `window.THREE` available → at least one 3D scene initialized (if applicable)
- CDN load failure → degraded static content + visible degraded-mode notice
- At least one chart must render successfully → otherwise show an error placeholder

### Output Contract (11 items)

After completion, the subagent must report:
1. Which key source files were read
2. The page output path
3. Whether interactive charts initialized successfully
4. Whether the 3D module initialized successfully
5. Whether degraded mode was entered
6. Which real process documents the 3D modeling was based on
7. How anomaly locations map to specific equipment
8. What the user can understand within 10 seconds, 1 minute, and 2 minutes respectively
9. What the 3-5 core evidence items in the main content area are
10. Whether the page passed html-reviewer quality checks
11. Whether the data governance card was rendered

## Data Truth Mandate

**Every number written to JSON/reports must be recomputable from the raw data.**

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
# CP-9: file exists + minimum size
test -f "$RUN_DIR/diagnostic-report.html" && \
  test "$(wc -c < "$RUN_DIR/diagnostic-report.html")" -ge 5120

# html-reviewer must pass
# Read .claude/skills/industrial-html-reviewer/references/agent-protocol.md and execute the review
```

## Failure Recovery

| Scenario | Recovery |
|----------|----------|
| Missing optimizer.md | Refuse to execute; report "missing CP-8 ENDORSED audit verdict" |
| Missing P0 diagnostic files | Execute the `skill://diagnostic-html-visualizer` §Fallback Rules |
| All CDNs fail | Degraded static content + visible degraded-mode notice; page remains usable |
| ECharts initialization failure | Replace the chart area with an error placeholder; the rest of the page renders normally |
| Three.js initialization failure | Skip the 3D scene and substitute a static process flow diagram |
| html-reviewer warn/fail | Read reviewer feedback → fall back to Phase 2 for fixes (max 3 attempts) → resubmit for review |
| Still failing after 3 reviews | Report pass-with-warnings and annotate known issues on the page |
| Page < 5120B | Check that all key sections rendered, then regenerate |
