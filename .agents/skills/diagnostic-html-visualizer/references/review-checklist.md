# Review Checklist — canonical reviewer-side protocol (v3)

> **Single canonical copy** for the whole family. `industrial-html-reviewer/SKILL.md`,
> `industrial-enhanced-html-reviewer/SKILL.md`, `references/html-reviewer-protocol.md`, and every reviewer
> agent protocol point here instead of restating these objectives. The **red-line table itself** lives only in
> `../SKILL.md` §Red-Line Blacklist (single authoritative source — never re-copy or re-number it elsewhere).

## 1. Reviewer independence rules

- Review the page, the manifest, and the selfcheck **against the run_dir artifacts yourself** — the builder's
  `html_selfcheck.json` is an audit INPUT, never an evidence substitute.
- `05_review/html_review.json` is written **only by the reviewer**. A pass written by any other party (builder,
  script, main agent) is invalid — flag it as a blocking issue and overwrite with your independent verdict.
- Any red-line blacklist hit → verdict `fail` (no discretionary downgrades).
- The builder's claims are what you try to disprove: every check needs quoted page evidence.
- Prose in Chinese; enums in English.

## 2. Review inputs

| File | Role |
|------|------|
| `diagnostic-report.html` | review target |
| `render_manifest.json` | builder's page model (CP-8A audit input; missing → fail, red line 14) |
| `html_selfcheck.json` | builder's 8-item self-check (CP-8B audit input — cross-check, never trust) |
| `report.md` / `04_diagnostics/*.json` / `01_ontology/ontology.json` / `03_figures/*` / `3d_model_data.json` / `02_processed/*` | ground truth for data-page consistency |
| authority `references/report-template.html` | visual grammar baseline (is the styling compliant?) |

## 3. Structural pre-check (fast fail)

1. `render_manifest.json` exists? Missing → red line 14 → `fail`, blocking issue `render_manifest_produced`.
2. `html_selfcheck.json` exists and all PASS? Missing/FAIL → `fail`, blocking issue `selfcheck_audit`.
3. `05_review/html_review.json` already exists but was NOT written by this review session (e.g. script-stamped)?
   Invalid — overwrite with the independent verdict and add a warning.

## 4. Review objectives (six dimensions)

### 1. Readability

- Does the first screen lead with the conclusion?
- Can conclusion / location / action be known within 10 seconds?
- Can the strongest evidence and the exclusion logic be known within 1 minute?
- Can how the conclusion was reached be known within 2 minutes?
- Hero has all 8 mandatory elements (`.hero-bar`, `.display`, `.hero-lede`, `.hero-meta` ≥5 items,
  `.key-findings` 4 cells with concrete values, reading-guide caption); no empty value or placeholder.
- Is every statistical term followed immediately by a plain-language translation?

### 2. Evidence completeness

- Does each main conclusion have visual evidence + reasoning evidence?
- Is the evidence chain unfolded as a three-layer architecture (statistics → physics → exclusion)?
- Does each layer have corresponding real diagnostic images (03_figures PNGs)?
- Key charts render? No chart wall? No text-image disconnect (chart up top, explanation far below)?
- Is any key evidence missing?

### 3. Logic chain

- Is "observation → verification → exclusion → conclusion → action" clearly presented?
- Is it explicitly explained why it is not another candidate cause?
- Is there a competing-hypothesis comparison (why A is retained while B/C/D are excluded or weakened)?
- Is there a physical causal-chain derivation (not only statistical correlation)?
- Is statistical jargon translated?

### 4. 3D and chart coverage

- Is at least one ECharts chart genuinely usable (verified with `echarts.getInstanceByDom`)?
- Is at least one 3D scene genuinely usable (canvas element exists)?
- Does the 3D match the real process order and anomaly locations? Is it scaled/colored from real data
  (not a generic model)?
- Anywhere showing only a placeholder without explanation?

### 5. Three-layer evidence-chain completeness

- **Layer 1 (statistical)**: Spearman ρ + p of the key parameter after detrending; ≥1 real scatter/correlation
  plot; ≥1 ECharts-rebuilt detrended scatter; a statistical evidence strength assessment.
- **Layer 2 (physical mechanism)**: a physical causal-chain visualization (HTML/CSS step chain); a physical
  equation or order-of-magnitude statement per step; a real temperature/torque per-zone profile plot; a note on
  the spatial consistency between anomaly location and mechanism; a physical evidence strength assessment.
- **Layer 3 (exclusion logic)**: independent evidence articles for ≥2 excluded/weakened hypotheses; "raw vs
  post-detrending" comparison per hypothesis; an explicit "why it was excluded" per hypothesis; a comprehensive
  verdict matrix table; action recommendations + limitations.
- Missing layers honestly marked `.evidence-missing` (never faked).

### 6. Data-page consistency (v3 core)

**manifest ↔ page consistency:**
- Page evidence-article count = `manifest.hypotheses[]` count (no fixed value, no skipped rendering).
- Page chart count = `manifest.charts[]` count.
- Page evidence-layer count = layers with `available:true` in `manifest.evidence_layers`; `available:false` layers
  must carry the `.evidence-missing` marker.
- Hero `.hero-meta` field count = genuinely available fields in `manifest.scope`.
- 3D exists only when `manifest.process_flow.recoverable=true`; its section order / equipment count / anomaly
  placement = the `process_flow` fields.
- Action-recommendation count = `manifest.actions[]` count.
- Every manifest field value that appears on the page (conclusion, confidence, ceiling, chart titles) matches.

**data ↔ manifest consistency (anti-fabrication):**
- Manifest statistics (ρ / p / decay rate) traceable to `diagnosis.json` / `evidence.json` / `validate_report.json`.
- Manifest `primary_finding` agrees with the main conclusion of `report.md` / `diagnosis.json`.
- Manifest section order agrees with `ontology.json`.
- The manifest contains **no** value or hypothesis that does not exist in run_dir.

**Data-page spot check:** sample ≥5 concrete page numbers (z-scores, ρ, p, percentages, equipment counts) and
trace each to `validate_report.json` / `anomaly_report.json` / `diagnosis.json` / `feature_summary.json`. Any
number that exists nowhere in run_dir → red line 11 (fabricated) or 15 (cross-run contamination) → `fail`.

**Cross-run contamination detection:**
- The page and the manifest must not contain concrete values, equipment IDs, or hypothesis names this run's data
  cannot explain (e.g. residual stick-slip / quench / specific ρ values from another run).

## 5. Red-line audit procedure (15 items)

The **single authoritative source** is `../SKILL.md` §🔴 Red-Line Blacklist (15 items: flat card pile, no real
PNGs, statistics without physics, no exclusion grounds, generic-factory 3D, charts without text, no first-screen
conclusion, untranslated jargon, 404 images, section count contradicting the scene, fabricated data, reviewer not
run, dark industrial style, manifest not produced / page↔manifest mismatch, cross-run contamination).

Procedure: for each of the 15 red lines, record **affirmative page evidence that it is NOT violated** (quote the
section / chart / value). A red line you cannot affirmatively clear → `fail` with the item number in
`blocking_issues`. The mapping below shows where each red line is covered by the `checks` array:

| reviewer check | Corresponding SKILL.md red line |
|---|---|
| `evidence_layer_1/2/3` | #1 #2 #3 (three-layer architecture + real PNGs + physical derivation) |
| `image_usage_from_03_figures` | #2 #9 (real PNGs + paths that do not 404) |
| `three_d_fidelity` | #5 (3D faithful to the process, not hardcoded) |
| `chart_initialization` + three-line reading beside each chart | #6 (three-line reading per chart) |
| `hero_clarity` | #7 #8 (first-screen conclusion + term translation) |
| `dual_evidence_per_conclusion` | #4 (dual evidence + exclusion logic) |
| `render_manifest_produced` | #11 (manifest produced + traceable) |
| `manifest_page_consistency` | #12 (page ↔ manifest consistency) |
| `no_cross_run_pollution` | #13 (cross-run contamination) |
| `action_and_limitations` | action recommendations + limitations (action-closure class) |

> If a SKILL.md red line is added or adjusted, update this mapping table; **do not rebuild an independent
> red-line table inside the reviewer** (that is the drift source this file exists to prevent).

## 6. Comprehension acceptance test (6 questions)

1. What is the final conclusion this time?
2. Where in the production line did the problem occur?
3. What is the strongest evidence?
4. Why not another cause that also looks correlated?
5. How was this conclusion reached step by step?
6. What is the most important next step?

≥2 questions not quickly answerable from the page → `fail` (the information structure must be redone).

## 7. Pass standard & decision rule

All must hold to award `pass`:

1. A user without an algorithm background can quickly understand the conclusion (comprehension test: at most 1
   question hard to answer).
2. Every main conclusion has sufficient chart + text evidence.
3. The three-layer evidence-chain architecture is complete (statistics + physics + exclusion), each closed.
4. The evidence chain uses PNG images genuinely produced by the diagnosis (no stock/beside-the-point images).
5. Charts and the 3D module serve understanding, not decoration.
6. The logic chain is clear; readers do not have to fill in gaps.
7. No obvious evidence gaps or text-image disconnects.
8. Page ↔ `render_manifest.json` alignment verified item by item; manifest values traceable to run_dir (no
   cross-run contamination).
9. `html_selfcheck.json` independently re-verified (at minimum: manifest alignment, chart init, local images).
10. Zero red-line hits.

Decision:

- `pass`: the page is deliverable.
- `warn`: usable but optimizable (no red-line hit, all checks pass, minor improvements listed) — the builder
  fixes the warnings and resubmits.
- `fail`: unacceptable; returns to the builder for revision (**max 3 revision attempts**, then abort with the
  blocker list — `[NEEDS_MANUAL_REVIEW]`).

**If the page reads like a "wall of charts" or a "wall of jargon", or a "flat pile of cards with no three-layer
reasoning", it must not pass even if it technically renders.**

## 8. Output contract — `05_review/html_review.json`

Schema: `industrial-html-reviewer/schemas/html_review_schema.json` (validated with
`node .claude/shared/scripts/validate.mjs`).

```json
{
  "verdict": "pass",
  "overall_score": 92,
  "blocking_issues": [],
  "warnings": [],
  "checks": [
    {"name": "hero_clarity", "status": "pass", "evidence": "..."}
  ]
}
```

- `blocking_issues` / `warnings` MUST be arrays of **strings** (never objects). Every `fail` check must have a
  corresponding blocking-issue string citing the red-line number or check name.
- `checks[]` required names (closed enum, schema-enforced): `hero_clarity`,
  `evidence_layer_1_statistical`, `evidence_layer_2_physics`, `evidence_layer_3_exclusion`,
  `image_usage_from_03_figures`, `three_d_fidelity`, `chart_initialization`, `dual_evidence_per_conclusion`,
  `plain_language_translation`, `action_and_limitations`, `render_manifest_produced`,
  `manifest_page_consistency`, `no_cross_run_pollution`, `selfcheck_audit`; each `{name, status: pass|fail,
  evidence}` with quoted page evidence.
- Gate: `node .claude/skills/industrial-html-reviewer/scripts/quality_gate.mjs --run-dir <RUN_DIR>`
  (exit 0 = artifact present + structurally valid; 2 = review artifact absent; 3 = corrupt/field violation).

## 9. Reviewer failure recovery

| Scenario | Recovery |
|----------|----------|
| `render_manifest.json` missing | Red line 14 → `fail`; blocking issue `render_manifest_produced` |
| Page↔manifest count mismatch | Red line 14 → `fail`; list the mismatched counts in blocking_issues |
| `html_selfcheck.json` missing or claims disproven | `selfcheck_audit` check `fail` → `fail` verdict with evidence |
| Schema validation fail | Fix the JSON → rewrite html_review.json → re-validate |
| HTML missing | Mark HTML_DELIVERY_FAILED → deliver report.md only |
| Review verdict fail | Trigger the revision loop (max 3) → if still failing, mark [NEEDS_MANUAL_REVIEW] |
| Agent stall | Inspect existing artifacts → if partially usable, downgrade to warn |
