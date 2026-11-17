---
name: industrial-html-reviewer
description: "Industrial diagnostic pipeline Step 8.5 — independent review of the diagnostic visualization page per the diagnostic-html-visualizer reviewer protocol v3. Audits six objectives (readability, evidence completeness, logic chain, 3D/chart coverage, three-layer evidence chain, data-page consistency), cross-checks the page against render_manifest.json and html_selfcheck.json, and enforces the 15-item red-line blacklist. Outputs html_review.json (pass/warn/fail). The reviewer NEVER trusts the builder's self-declared quality — every check needs page evidence. Review-only: it never builds or edits the page, never reviews the enhanced page (→ industrial-enhanced-html-reviewer), and never performs the diagnosis itself (→ industrial-diagnostician). Trigger: HTML review, review HTML, page review, html reviewer, audit HTML, HTML audit."
---

# Industrial HTML Reviewer

Diagnostic visualization review engine (pipeline **Step 8.5**). Independently reviews whether
`diagnostic-report.html` lets users without an algorithm background understand the conclusion, the evidence, and
the exclusion logic — **and whether the page is a faithful, manifest-aligned rendering of THIS run's artifacts**.
The independent gate between the builder and delivery: a "wall of charts", a "wall of jargon", or a page that
contradicts its own `render_manifest.json` must not pass even if it renders.

**Reviewer independence rules** (canonical: `.claude/skills/diagnostic-html-visualizer/references/review-checklist.md` §1):
- Review the page, the manifest, and the selfcheck **against the run_dir artifacts yourself** — the builder's
  `html_selfcheck.json` is an audit INPUT, never an evidence substitute.
- `05_review/html_review.json` is written **only by you**; a pass written by any other party is invalid → flag it.
- Any red-line blacklist hit → verdict `fail` (no discretionary downgrades).

## Shared protocol & checklists (read these; do not restate)

- **Reviewer checklist (objectives, red-line audit procedure, pass standard, decision rule, output contract —
  the canonical single copy)**: `.claude/skills/diagnostic-html-visualizer/references/review-checklist.md`
- Red-line table (single authoritative source, 15 items): `.claude/skills/diagnostic-html-visualizer/SKILL.md` §Red-Line Blacklist
- Reviewer protocol v3 (required reading, manifest-faithfulness audit): `.claude/skills/diagnostic-html-visualizer/references/html-reviewer-protocol.md`
- Manifest schema (what the builder promised): `.claude/skills/diagnostic-html-visualizer/references/html-builder-protocol.md`
- Shared format rules (Data Truth Mandate, artifact minimums): `.claude/skills/diagnostic-html-visualizer/references/format-rules.md`
- Mode-specific execution checklist (persona, steps, output validation): `references/agent-protocol.md`
- Output schema: `schemas/html_review_schema.json`

## Inputs / Outputs

### Inputs (in `RUN_DIR`)

| File | Description |
|------|-------------|
| `diagnostic-report.html` | HTML visualization page (review target) |
| `render_manifest.json` | Builder's data-driven page model (**CP-8A audit input**; missing → fail) |
| `html_selfcheck.json` | Builder's 8-item self-check (**CP-8B audit input — cross-check, never trust blindly**) |
| `report.md`, `04_diagnostics/{diagnosis,evidence,reasoning_chain}.json` | Conclusion / evidence / reasoning ground truth |
| `01_ontology/ontology.json`, `03_figures/*.json`, `3d_model_data.json` | Section order / chart inventory / 3D ground truth |
| `02_processed/{data_analysis_conclusion,feature_summary,validate_report}.json` | Data governance + statistics for the data-page spot check |

### Outputs

| File | Description |
|------|-------------|
| `05_review/html_review.json` | verdict + overall_score + blocking_issues + warnings + checks (schema-validated) |

## Quality Gate

```bash
node .claude/skills/industrial-html-reviewer/scripts/quality_gate.mjs --run-dir <RUN_DIR>
# exit 0 = html_review.json present + structurally valid (verdict enum, score 0-100, checks[] enum, string
#          blocking_issues; pass must not carry blockers, fail must carry a blocker or a failed check)
# exit 2 = review artifact absent (Step 8.5 has not run)  |  exit 3 = corrupt/field violation
# exit 1 = hard error.  Tests: python .claude/skills/industrial-html-reviewer/tests/run_tests.py
```

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

Launch the `html-reviewer` subagent (persona: Reviewer Zhao):

```javascript
Agent({
  subagent_type: "html-reviewer",
  prompt: `RUN_DIR=<run-dir-path>
SKILL_PATH=<path-to-.claude/skills/industrial-html-reviewer>
DVSKILL_PATH=<path-to-.claude/skills/diagnostic-html-visualizer>
SHARED_PATH=<path-to-.claude/shared>
OUTPUT_HTML=$RUN_DIR/diagnostic-report.html
AUDIENCE=mixed

Read "$SKILL_PATH/references/agent-protocol.md" and execute the complete review protocol
(objectives + red-line procedure: "$DVSKILL_PATH/references/review-checklist.md";
red-line table: "$DVSKILL_PATH/SKILL.md" §Red-Line Blacklist).

Key constraints:
- Review the page against run_dir artifacts YOURSELF; html_selfcheck.json is an input to cross-check, not evidence
- Audit render_manifest.json <-> page alignment item by item; any mismatch -> fail (red line 14)
- Any of the 15 red lines hit -> fail; a red line you cannot affirmatively clear -> fail
- The first screen must lead with the conclusion; charts must state the conclusion; the logic chain must not break
- Output prose in Chinese; keep enums in English; write 05_review/html_review.json yourself`,
  effort: "hi"
})
```

## Gate Verification (shared, run after the review)

```bash
node "$SHARED_PATH/scripts/validate.mjs" \
  "$SHARED_PATH/schemas/html_review_schema.json" \
  "$RUN_DIR/05_review/html_review.json"
```

## Failure Recovery

Canonical table: `.claude/skills/diagnostic-html-visualizer/references/review-checklist.md` §9
(manifest missing → red line 14 fail; page↔manifest mismatch → fail; selfcheck missing/disproven → fail;
schema fail → fix and re-validate; HTML missing → HTML_DELIVERY_FAILED; fail verdict → revision loop max 3 →
[NEEDS_MANUAL_REVIEW]; agent stall → downgrade to warn if partially usable).
