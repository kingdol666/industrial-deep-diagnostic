---
name: industrial-html-reviewer
description: "Industrial diagnostic pipeline Step 8.5 — independent review of the diagnostic visualization page per the diagnostic-html-visualizer reviewer protocol v3. Audits six objectives (readability, evidence completeness, logic chain, 3D/chart coverage, three-layer evidence chain, data-page consistency), cross-checks the page against render_manifest.json and html_selfcheck.json, and enforces the 15-item red-line blacklist. Outputs html_review.json (pass/warn/fail). The reviewer NEVER trusts the builder's self-declared quality — every check needs page evidence. Trigger: HTML review, review HTML, page review, html reviewer, audit HTML, HTML audit."
---

# Industrial HTML Reviewer

Diagnostic visualization review engine (Step 8.5). Independently reviews whether `diagnostic-report.html` lets users without an algorithm background understand the conclusion, the evidence, and the exclusion logic — **and whether the page is a faithful, manifest-aligned rendering of THIS run's artifacts**. You are the independent gate between the builder and delivery: a page that reads like a "wall of charts" or a "wall of jargon" must not pass even if it technically renders; a page that contradicts its own `render_manifest.json` must not pass even if it is beautiful.

**Independence rules**:
- You review the page, the manifest, and the selfcheck **against the run_dir artifacts yourself** — the builder's `html_selfcheck.json` is an audit INPUT, never an evidence substitute
- `05_review/html_review.json` is written **only by you**. A pass written by any other party (builder, script, main agent) is invalid — flag it as a blocking issue
- Any red-line blacklist hit → verdict `fail` (no discretionary downgrades)

## Inputs / Outputs

### Inputs (in `RUN_DIR`)

| File | Description |
|------|-------------|
| `diagnostic-report.html` | HTML visualization page (review target) |
| `render_manifest.json` | Builder's data-driven page model (**CP-8A audit input**) |
| `html_selfcheck.json` | Builder's 8-item self-check (**CP-8B audit input — cross-check, never trust blindly**) |
| `report.md` | Final diagnostic report (conclusion reference) |
| `04_diagnostics/diagnosis.json` | Diagnostic conclusion |
| `04_diagnostics/evidence.json` | Evidence list |
| `04_diagnostics/reasoning_chain.json` | Reasoning chain |
| `01_ontology/ontology.json` | Domain ontology |
| `03_figures/plot_manifest.json` | Plot manifest |
| `03_figures/visual_analysis.json` | VLM visual analysis |
| `03_figures/image_captions.json` | Image captions |
| `3d_model_data.json` | 3D model data |
| `02_processed/data_analysis_conclusion.json` | Data analysis conclusion (data governance) |
| `02_processed/feature_summary.json` | Feature summary |
| `02_processed/validate_report.json` | Statistical validation report |

### Outputs

| File | Description |
|------|-------------|
| `05_review/html_review.json` | verdict + overall_score + blocking_issues + warnings + checks (schema-validated) |

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

## Dispatch

Launch the `html-reviewer` subagent:

```javascript
Agent({
  subagent_type: "html-reviewer",
  prompt: `RUN_DIR=<run-dir-path>
SKILL_PATH=<path-to-.claude/skills/industrial-html-reviewer>
DVSKILL_PATH=<path-to-.claude/skills/diagnostic-html-visualizer>
SHARED_PATH=<path-to-.claude/shared>
OUTPUT_HTML=$RUN_DIR/diagnostic-report.html
AUDIENCE=mixed

Read "$SKILL_PATH/references/agent-protocol.md" and execute the complete review protocol.

Key constraints:
- Review the page against run_dir artifacts YOURSELF; html_selfcheck.json is an input to cross-check, not evidence
- Audit render_manifest.json ↔ page alignment item by item (sections / cards / charts / evidence layers)
- Enforce the 15-item red-line blacklist (single authoritative source: $DVSKILL_PATH/SKILL.md) — any hit = fail
- The first screen must lead with the conclusion — never make the user guess
- Charts must "state the conclusion" — not merely say "as shown in Figure X"
- The logic chain must not break — observation→verification→exclusion→conclusion→action
- If the page reads like a "wall of charts" or a "wall of jargon", it must not pass even if it technically renders
- Output prose in Chinese; keep enums in English
`,
  effort: "hi"
})
```

## Review Objectives (reviewer protocol v3)

| # | Dimension | Check points |
|---|-----------|--------------|
| 1 | Readability | Conclusion above the fold? 10s (conclusion/location/action) / 1min (strongest evidence/exclusions) / 2min (how concluded) tiers met? Hero has all 8 mandatory elements with concrete values? |
| 2 | Evidence completeness | Main conclusion has BOTH visual + reasoning evidence? Key charts render? No chart wall? No text-image disconnect? |
| 3 | Logic chain | observation→verification→exclusion→conclusion→action explicit? Other candidate causes excluded with grounds? Statistical jargon translated? |
| 4 | 3D and chart coverage | At least one ECharts chart genuinely initialized? 3D scene (if present) matches real process order + anomaly locations? No unexplained placeholders? |
| 5 | Three-layer evidence chain | Ⅰ statistics / Ⅱ physics / Ⅲ exclusion each closed and backed by real images/data/reasoning — not a flat card pile? Missing layers honestly marked `.evidence-missing` (not faked)? |
| 6 | **Data-page consistency (core)** | Every page number/equipment/hypothesis traceable to THIS run's artifacts? Page counts match `render_manifest.json`? Selfcheck claims hold under independent verification? No cross-run contamination (red line 15)? |

## Red-Line Blacklist Audit

The **single authoritative source** is `skill://diagnostic-html-visualizer` §Red-Line Blacklist (15 items: flat card pile, no real PNGs, statistics without physics, no exclusion grounds, generic-factory 3D, charts without text, no first-screen conclusion, untranslated jargon, 404 images, section count contradicting the scene, fabricated data, reviewer not run, dark industrial style, manifest not produced / page↔manifest mismatch, cross-run contamination).

Audit procedure: for each red line, find affirmative page evidence it is NOT violated (quote the section/chart/value). A red line you cannot affirmatively clear → `fail` with the item number in `blocking_issues`.

## Pass Standard

All must hold to award `pass`:
1. A user without an algorithm background can quickly understand the conclusion (6-question comprehension test: final conclusion / where / strongest evidence / why not another cause / how concluded / next step — at most 1 may be hard to answer)
2. Every main conclusion has sufficient chart+text evidence in the three closed layers
3. Charts and the 3D module serve understanding, not decoration
4. The logic chain is clear; readers do not have to fill in gaps themselves
5. Page ↔ `render_manifest.json` alignment verified item by item
6. `html_selfcheck.json` independently re-verified (at minimum: manifest alignment, chart init, local images)
7. Zero red-line hits; zero cross-run contamination

## Decision Rule

- `pass`: the page is deliverable
- `warn`: the page is usable but has optimizable items (no red-line hit, all checks pass, minor improvements listed)
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
    {"name": "evidence_layer_1_statistical", "status": "pass", "evidence": "..."},
    {"name": "evidence_layer_2_physics", "status": "pass", "evidence": "..."},
    {"name": "evidence_layer_3_exclusion", "status": "pass", "evidence": "..."},
    {"name": "image_usage_from_03_figures", "status": "pass", "evidence": "..."},
    {"name": "three_d_fidelity", "status": "pass", "evidence": "..."},
    {"name": "chart_initialization", "status": "pass", "evidence": "..."},
    {"name": "dual_evidence_per_conclusion", "status": "pass", "evidence": "..."},
    {"name": "plain_language_translation", "status": "pass", "evidence": "..."},
    {"name": "action_and_limitations", "status": "pass", "evidence": "..."},
    {"name": "render_manifest_produced", "status": "pass", "evidence": "..."},
    {"name": "manifest_page_consistency", "status": "pass", "evidence": "..."},
    {"name": "no_cross_run_pollution", "status": "pass", "evidence": "..."},
    {"name": "selfcheck_audit", "status": "pass", "evidence": "..."}
  ]
}
```

`blocking_issues` MUST be an array of strings (not objects). Every `fail` check must have a corresponding blocking issue string citing the red-line number or check name.

## Data Truth Mandate

**Every number written to JSON must be recomputable from the raw data.**

| Rule | Requirement |
|------|------|
| Numeric traceability | Every number must state its data source (cleaned/raw), row range, and computation method |
| Derived value marking | Inferred/derived values must be explicitly marked `"derived": true` or `"inferred": true` |
| Cleaning audit trail | cleaning_integrity records all cleaning operations |
| Visualization traceability | Every data point in every chart must be traceable to specific rows of the dataset |
| Unavailable marking | Values that cannot be computed from the data → write NOT_APPLICABLE + reason |

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

- `references/agent-protocol.md` — full HTML review protocol (persona, reading order, six-objective audit, red-line procedure, output validation)
- `schemas/html_review_schema.json` — JSON Schema for html_review.json

External authority (read, never modify): `skill://diagnostic-html-visualizer` — §Red-Line Blacklist (single source) + `references/html-reviewer-protocol.md` (v3 review objectives).

## Failure Recovery

| Scenario | Recovery |
|----------|----------|
| `render_manifest.json` missing | Red line 14 → `fail`; blocking issue "render_manifest_produced" |
| Page↔manifest count mismatch | Red line 14 → `fail`; list the mismatched counts in blocking_issues |
| `html_selfcheck.json` missing or claims disproven | `selfcheck_audit` check `fail` → `fail` verdict with evidence |
| Schema validation fail | Fix the JSON → rewrite html_review.json → re-validate |
| HTML missing | Mark HTML_DELIVERY_FAILED → deliver report.md only |
| Review verdict fail | Trigger the revision loop (max 3) → if still failing, mark [NEEDS_MANUAL_REVIEW] |
| Agent stall | Inspect existing artifacts → if partially usable, downgrade to warn |
