---
name: industrial-html-visualizer
description: "Industrial diagnostic pipeline Step 8 — builds the explanatory HTML visualization page from diagnostic artifacts STRICTLY via the diagnostic-html-visualizer design system: render_manifest.json is produced first (data-driven page model), the page is assembled from the design system reference per the manifest, html_selfcheck.json validates 8 items, and html-reviewer must pass. Reuses the templates, design system, and Fallback rules of the diagnostic-html-visualizer skill. The conclusion must be above the fold, charts are evidence rather than decoration, and the 3D model must tell the truth. Do NOT use without CP-8 ENDORSED optimizer.md. Trigger: HTML visualization, generate HTML, frontend page, visualization report, html visualization, diagnostic HTML, 3D scene, ECharts."
---

# Industrial HTML Visualizer

Frontend visualization build engine for diagnostic results. **The page is built through the `diagnostic-html-visualizer` skill's full protocol — not a free-hand HTML write.** The build order is fixed: **understand run_dir artifacts → model `render_manifest.json` → assemble the page from the design system reference per the manifest → validate `html_selfcheck.json` → pass `html-reviewer`**. Writing HTML directly without a manifest is a red-line violation (reviewer must fail it).

**Hard prerequisite**: the CP-8 ENDORSED audit verdict (`optimizer.md`). Without optimizer.md → refuse to execute and report "missing CP-8 ENDORSED audit verdict" to the main agent.

## Style Authority (single source)

`skill://diagnostic-html-visualizer` is the **sole style and protocol authority** for this step:

| Authority file | Role |
|----------------|------|
| `diagnostic-html-visualizer/SKILL.md` | 6 iron rules + visual grammar (color/typography/components) + **red-line blacklist (15 items, single authoritative source)** + 8 fallback chains |
| `references/html-builder-protocol.md` | Builder protocol v3 — data-driven rendering protocol (Understand → Model → Render), manifest schema, hard requirements, evidence architecture |
| `references/report-template.html` | Design system reference — CSS variables, typography, component classes, loader status strip, ECharts/Three.js multi-source loading pattern. **Visual grammar baseline, not a fill-in template** |
| `references/html-reviewer-protocol.md` | What the reviewer will audit (build accordingly) |

The visual identity is non-negotiable: warm-white background `#fafaf8`, single ink accent `#1e3a54`, warm orange `#c2673a` for anomalies only, serif headings + sans body, hairline dividers (no card-shadow piles), ECharts palette `['#1e3a54','#2d7d4f','#c2673a','#c4433b','#8a6d3b']`. Dark industrial style, purple gradients, neon glow, KPI-number walls, and image-wall tiling are **forbidden** (red lines 13 and the §Styles-to-avoid table).

## Inputs / Outputs

### Inputs (in `RUN_DIR`)

| File | Description |
|------|-------------|
| `optimizer.md` | **CP-8 ENDORSED** audit verdict (hard prerequisite) |
| `report.md` | Diagnostic report |
| `04_diagnostics/diagnosis.json` | Diagnostic conclusion (conclusion type / hypotheses / confidence) |
| `04_diagnostics/evidence.json` | Evidence list |
| `04_diagnostics/reasoning_chain.json` | Reasoning chain |
| `04_diagnostics/confidence.json` | Confidence assessment |
| `01_ontology/ontology.json` | Domain ontology (3D section recovery) |
| `02_processed/data_analysis_conclusion.json` | Data analysis conclusion (data governance audit trail) |
| `03_figures/plot_manifest.json` | Plot manifest |
| `03_figures/visual_analysis.json` | VLM visual analysis |
| `03_figures/image_captions.json` | Image captions |
| `03_figures/*.png` | Ready-made visual evidence — reused first by the evidence-chain blocks |
| `3d_model_data.json` | 3D model data (if present) |

When P0 files are missing or malformed, execute the corresponding branch of the `skill://diagnostic-html-visualizer` §Fallback Rules (8 chains; no silent failure).

### Outputs

| File | Description | Gate |
|------|-------------|:----:|
| `render_manifest.json` | **Data-driven page model, produced FIRST** — conclusion type, hypotheses[], three-layer evidence availability, charts[], process_flow, available_pngs[], `_meta.protocol_ack` | CP-8A |
| `diagnostic-report.html` | Single-file HTML ≥5120B assembled from the design system per the manifest | CP-9 |
| `html_selfcheck.json` | 8-item self-check (each `{name, status: "PASS"\|"FAIL", evidence}`) | CP-8B |
| `05_review/html_review.json` | html-reviewer independent verdict (produced by the reviewer, never by this agent) | CP-8C |

**Ordering is enforced**: no `diagnostic-report.html` may exist before `render_manifest.json`; a page whose section/card/chart/evidence-layer counts do not match the manifest is a red-line fail (reviewer audits this).

## Pipeline Event Logging

**MANDATORY** — log lifecycle events for pipeline-finalize.mjs execution proof verification:

```bash
# On start (before any work)
node "$SHARED_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" \
  --event agent_start --agent html-visualizer --step present

# On completion (after ALL outputs written)
node "$SHARED_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" \
  --event agent_complete --agent html-visualizer --step present \
  --files diagnostic-report.html,render_manifest.json,html_selfcheck.json
```

## Dispatch

Launch the `html-visualizer` subagent (persona: Lin Gong — industrial frontend visualization engineer):

```javascript
Agent({
  subagent_type: "html-visualizer",
  prompt: `RUN_DIR=<run-dir-path>
SKILL_PATH=<path-to-.claude/skills/industrial-html-visualizer>
DVSKILL_PATH=<path-to-.claude/skills/diagnostic-html-visualizer>
SHARED_PATH=<path-to-.claude/shared>
OUTPUT_HTML=<run-dir-path>/diagnostic-report.html
AUDIENCE=mixed
VISUAL_MODE=story

## Protocol (fixed order — checkpoints are gates, not suggestions)

1. Read "$SKILL_PATH/references/agent-protocol.md" — your execution checklist
2. Read "$DVSKILL_PATH/SKILL.md" — iron rules, visual grammar, red-line blacklist
3. Read "$DVSKILL_PATH/references/html-builder-protocol.md" — data-driven rendering protocol (v3)
4. Read "$DVSKILL_PATH/references/report-template.html" — design system reference
5. Execute: Understand → Model render_manifest.json (CP-8A) → Render per manifest → html_selfcheck.json (CP-8B) → html-reviewer pass (CP-8C)

## Key requirements
- render_manifest.json BEFORE any HTML; page counts must match the manifest exactly
- Assemble components verbatim from the design system reference (style block, loader strip, importmap, loading logic, @media)
- Evidence chain = three closed layers (statistics Ⅰ → physics Ⅱ → exclusion Ⅲ), each backed by real 03_figures PNGs / data / physical reasoning
- Runtime readiness: ECharts + Three.js multi-source CDN, loader status strip (5 indicators), static fallback
- Chinese language interface; all numbers traceable to this run_dir (no cross-run contamination)
- On completion, report the 11-item output contract to the main agent`,
  effort: "hi"
})
```

## Execution Flow

| Phase | Purpose | Gate |
|-------|---------|:----:|
| 1 — Understand | Read builder protocol + design system + all run_dir artifacts (P0→P2 priority) | protocol_ack |
| 2 — Model | Produce `render_manifest.json`: conclusion type, `hypotheses[]` (count = real data), `evidence_layers` availability, `charts[]` (count = real signals), `process_flow`, `available_pngs[]`, `_meta.protocol_ack` = 3× true | **CP-8A** |
| 3 — Render | Assemble the page from the manifest wearing the design system's visual grammar: Hero (8 mandatory elements) → background + 3D (only if `process_flow.recoverable`) → reasoning (statistics table + charts with three-line readings) → evidence chain three layers → actions; conclusion-type branching (DETERMINED / COMPETING_SET / NEEDS_DATA) | — |
| 4 — Self-check | Write `html_selfcheck.json` (8 items, each with evidence); any FAIL → fix and rewrite (max 3 fix rounds) | **CP-8B** |
| 5 — Review | `html-reviewer` independent review. `pass` to complete; `warn` → fix warnings and resubmit; `fail` → return to Phase 3 with blocker list (max 3 attempts) | **CP-8C** |
| 6 — Contract | Report 11 items to the main agent | — |

### Runtime Readiness (mandatory, red line 6)

The page must self-check and report via the loader status strip:
- `window.echarts` available → at least one chart initialized (`echarts.getInstanceByDom`)
- `window.THREE` available → at least one 3D scene initialized (canvas exists), when a 3D module is present
- CDN load failure → degraded static content + visible degraded-mode notice; no blank page, no silent failure
- Every chart carries a `.chart-reading` three-line reading (what is seen / what it means / why it matters)

### Output Contract (11 items)

After completion, the subagent must report:
1. Which key source files were read
2. The page output path (+ `render_manifest.json` + `html_selfcheck.json` paths)
3. Whether interactive charts initialized successfully
4. Whether the 3D module initialized successfully
5. Whether degraded mode was entered
6. Which real process documents the 3D modeling was based on
7. How anomaly locations map to specific equipment
8. What the user can understand within 10 seconds, 1 minute, and 2 minutes respectively
9. What the 3-5 core evidence items in the main content area are
10. Whether the page passed html-reviewer quality checks (verdict + score)
11. Whether the data governance card was rendered (from `data_cleaning_provenance`)

## Data Truth Mandate

**Every number written to JSON/reports must be recomputable from the raw data.**

| Rule | Requirement |
|------|------|
| Numeric traceability | Every number must state its data source (cleaned/raw), row range, and computation method |
| Derived value marking | Inferred/derived values must be explicitly marked `"derived": true` or `"inferred": true` |
| Cleaning audit trail | cleaning_integrity records all cleaning operations |
| Visualization traceability | Every data point in every chart must be traceable to specific rows of the dataset |
| Unavailable marking | Values that cannot be computed from the data → write NOT_APPLICABLE + reason |
| No cross-run contamination | Every number/equipment/hypothesis on the page must be explainable by THIS run's data (red line 15) |

## Counterfactual Reasoning — Exclusion Constraints

| Constraint | Description |
|------|------|
| Four conditions | Temporal precedence + statistical significance + physical mechanism + no contradiction |
| Exclusion standard | If any condition is not met → mark as an excluded candidate and provide quantitative justification |
| Physical boundary | Exclusions must be supported by first principles or governing equations |
| Confidence threshold | When exclusion confidence <80, mark `[WEAK_EXCLUSION]` |

## Verification

```bash
# CP-8A: manifest exists before the page and carries protocol_ack
test -f "$RUN_DIR/render_manifest.json"

# CP-8B: self-check all PASS
node -e "const s=require('$RUN_DIR/html_selfcheck.json'); process.exit(Object.values(s).flat().some(x=>x&&x.status==='FAIL')?1:0)"

# CP-8C/CP-9: reviewer pass + minimum size
node -e "const r=require('$RUN_DIR/05_review/html_review.json'); process.exit(r.verdict==='pass'?0:1)"
test "$(wc -c < "$RUN_DIR/diagnostic-report.html")" -ge 5120
```

## Failure Recovery

| Scenario | Recovery |
|----------|----------|
| Missing optimizer.md | Refuse to execute; report "missing CP-8 ENDORSED audit verdict" |
| Design system reference unreadable | Fallback 1: `templates/page_blueprint.md` + `templates/render_prompt_template.md`, still manifest-driven; both unavailable → abort with skill-installation error |
| Missing P0 diagnostic files | Fallback 3: degrade to report.md summary; mark missing layers honestly; never fabricate |
| `03_figures/` PNGs all missing | Fallback 4: rebuild key charts from JSON via ECharts, marked "ECharts rebuild · original image unavailable" |
| All CDNs fail | Fallback 5: static degraded mode + loader strip all red + first-screen notice; key information retained |
| ECharts init null | Fallback 6: retry once (200ms) → static placeholder + three-line reading text |
| WebGL unavailable | Fallback 7: CSS2DRenderer → 2D SVG/Canvas section flow diagram |
| `3d_model_data.json` + `ontology.json` missing | Fallback 8: 2D HTML/CSS section flow from report.md/diagnosis.json text |
| html-reviewer warn/fail | Feed blocker list back → return to Phase 3 (max 3 attempts) → still failing → report blocker list, do NOT self-write a pass |
| Page < 5120B | Check that all key sections rendered, then regenerate per the manifest |
