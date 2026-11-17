---
name: industrial-html-visualizer
description: "Industrial diagnostic pipeline Step 8 — builds the explanatory HTML visualization page from diagnostic artifacts STRICTLY via the diagnostic-html-visualizer design system: render_manifest.json is produced first (data-driven page model), the page is assembled from the design system reference per the manifest, html_selfcheck.json validates 8 items, and html-reviewer must pass. Reuses the templates, design system, and Fallback rules of the diagnostic-html-visualizer skill. The conclusion must be above the fold, charts are evidence rather than decoration, and the 3D model must tell the truth. Hard prerequisite: CP-8 ENDORSED optimizer.md. Do NOT use without it; do NOT use for plain statistics/chart work on raw data (→ industrial-data-processor), root-cause analysis (→ industrial-diagnostician / industrial-analysis-auto), the enhanced-knowledge page (→ industrial-enhanced-html-visualizer), or reviewing a page (→ industrial-html-reviewer). Trigger: HTML visualization, generate HTML, frontend page, visualization report, html visualization, diagnostic HTML, 3D scene, ECharts."
---

# Industrial HTML Visualizer

Frontend visualization build engine for diagnostic results (pipeline **Step 8**). **The page is built through the `diagnostic-html-visualizer` skill's full protocol — not a free-hand HTML write.** Fixed build order: **understand run_dir artifacts → model `render_manifest.json` → assemble the page from the design system reference per the manifest → validate `html_selfcheck.json` → pass `html-reviewer`**. Writing HTML directly without a manifest is a red-line violation (the reviewer must fail it).

**Hard prerequisite**: the CP-8 ENDORSED audit verdict (`optimizer.md`). Without optimizer.md → refuse to execute and report "missing CP-8 ENDORSED audit verdict" to the main agent.

## Shared protocol & checklists (read these; do not restate)

- Design system, iron rules, visual grammar, **red-line blacklist (single source)**, 8 fallback chains:
  `.claude/skills/diagnostic-html-visualizer/SKILL.md`
- Builder protocol v3 (Understand → Model → Render, manifest schema): `.claude/skills/diagnostic-html-visualizer/references/html-builder-protocol.md`
- Design system reference (CSS variables, components, loader strip, importmap, @media): `.claude/skills/diagnostic-html-visualizer/references/report-template.html`
- Shared format rules — language, Data Truth Mandate, exclusion constraints, runtime readiness, artifact minimums: `.claude/skills/diagnostic-html-visualizer/references/format-rules.md`
- What the reviewer will audit + mode matrix / routing: `.claude/skills/diagnostic-html-visualizer/references/review-checklist.md`, `.../references/family-routing.md`
- Mode-specific execution checklist (persona, phases, checklists): `references/agent-protocol.md`

## Inputs (in `RUN_DIR`)

| File | Description |
|------|-------------|
| `optimizer.md` | **CP-8 ENDORSED** audit verdict (hard prerequisite) |
| `report.md` | Diagnostic report |
| `04_diagnostics/{diagnosis,evidence,reasoning_chain,confidence}.json` | Conclusion / evidence / reasoning chain / confidence |
| `01_ontology/ontology.json` | Domain ontology (3D section recovery) |
| `02_processed/data_analysis_conclusion.json` | Data analysis conclusion (data governance audit trail) |
| `03_figures/{plot_manifest,visual_analysis,image_captions}.json` + `*.png` | Charts — ready-made visual evidence, reused first |
| `3d_model_data.json` | 3D model data (if present) |

When P0 files are missing or malformed, execute the corresponding branch of the authority §Fallback Rules (8 chains; no silent failure).

## Outputs

| File | Description | Gate |
|------|-------------|:----:|
| `render_manifest.json` | **Data-driven page model, produced FIRST** — conclusion type, `hypotheses[]`, three-layer evidence availability, `charts[]`, `process_flow`, `available_pngs[]`, `_meta.protocol_ack` | CP-8A |
| `diagnostic-report.html` | Single-file HTML ≥5120B assembled from the design system per the manifest | CP-9 |
| `html_selfcheck.json` | 8-item self-check (each `{name, status: "PASS"\|"FAIL", evidence}`) | CP-8B |
| `05_review/html_review.json` | html-reviewer independent verdict (produced by the reviewer, never by this agent) | CP-8C |

**Ordering is enforced**: no `diagnostic-report.html` may exist before `render_manifest.json`; a page whose section/card/chart/evidence-layer counts do not match the manifest is a red-line fail (the reviewer audits this).

## Quality Gate

```bash
node .claude/skills/industrial-html-visualizer/scripts/quality_gate.mjs --run-dir <RUN_DIR>
# exit 0 = diagnostic-report.html exists, parses as HTML (title + structure), size >= 5120B
# exit 2 = page absent (Step 8 has not run)  |  exit 3 = corrupt/undersized/unparseable page
# exit 1 = hard error (bad --run-dir).  Tests: python .claude/skills/industrial-html-visualizer/tests/run_tests.py
```

The gate is additive: it does not replace the CP-8A/8B/8C checkpoints or the reviewer.

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
5. Execute: Understand -> Model render_manifest.json (CP-8A) -> Render per manifest -> html_selfcheck.json (CP-8B) -> html-reviewer pass (CP-8C) -> report the 11-item output contract`,
  effort: "hi"
})
```

## Execution Flow

| Phase | Purpose | Gate |
|-------|---------|:----:|
| 1 — Understand | Read builder protocol + design system + all run_dir artifacts (P0→P2 priority) | protocol_ack |
| 2 — Model | Produce `render_manifest.json` (counts = real data; `_meta.protocol_ack` = 3× true) | **CP-8A** |
| 3 — Render | Assemble per manifest: Hero (8 elements) → background + 3D (only if `process_flow.recoverable`) → reasoning → evidence-chain three layers → actions | — |
| 4 — Self-check | `html_selfcheck.json` (8 items + evidence); any FAIL → fix and rewrite (max 3 rounds) | **CP-8B** |
| 5 — Review | `html-reviewer`: `pass` → done; `warn` → fix and resubmit; `fail` → back to Phase 3 (max 3) | **CP-8C** |
| 6 — Contract | Report 11 items to the main agent | — |

## Failure Recovery

| Scenario | Recovery |
|----------|----------|
| Missing optimizer.md | Refuse to execute; report "missing CP-8 ENDORSED audit verdict" |
| Design system reference unreadable | Fallback 1: build from `templates/page_blueprint.md` + `templates/render_prompt_template.md`, still manifest-driven; both unavailable → abort with skill-installation error |
| Missing P0 diagnostic files | Fallback 3: degrade to report.md summary; mark missing layers honestly; never fabricate |
| `03_figures/` PNGs all missing | Fallback 4: rebuild key charts from JSON via ECharts, marked "ECharts rebuild · original image unavailable" |
| All CDNs fail / ECharts init null / WebGL unavailable | Fallbacks 5-7: static degraded mode + loader strip all red + first-screen notice; placeholders carry the three-line reading text |
| `3d_model_data.json` + `ontology.json` missing | Fallback 8: 2D HTML/CSS section flow from report.md/diagnosis.json text |
| html-reviewer warn/fail | Feed blocker list back → Phase 3 (max 3) → still failing → report blocker list, do NOT self-write a pass |
| Page < 5120B | Check all key sections rendered, then regenerate per the manifest |
