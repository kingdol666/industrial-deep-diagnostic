---
name: diagnostic-html-visualizer
description: "Generate a human-friendly HTML explanation page from a diagnostic run folder. Use whenever the user asks to visualize diagnosis results, create an HTML report/page/dashboard/front-end explainer, render diagnostic conclusions with ECharts or Three.js, or turn a run directory into a page that operators, managers, and engineers can understand at a glance. Strongly prefer this skill after the industrial diagnostic pipeline (industrial-analysis-auto) finishes, especially when a folder contains report.md, ontology.json, diagnosis.json, evidence.json, reasoning_chain.json, plot_manifest.json, or 3d_model_data.json. Do NOT use for doing the diagnosis itself, generic marketing landing pages, or cases where no diagnostic artifacts are available; do NOT use for plain statistics/chart work on raw data (use industrial-data-processor), root-cause analysis (use industrial-diagnostician / industrial-analysis-auto), or enhanced-knowledge pages (use industrial-enhanced-html-visualizer). Trigger: diagnostic results visualization, HTML report generation, frontend explainer page, visualize evidence chain, diagnostic webpage, dashboard, html explain page, render diagnosis to html, visualize run folder."
commands:
  - diagnostic-html-visualizer
  - diagnostic-html-visualizer build
  - diagnostic-html-visualizer refresh
compatibility: |
  Works with plain HTML/CSS/JS and does not require a bundler.
  Prefer single-file HTML output with inline CSS/JS plus relative links to local PNG/JPG assets in the run directory.
  Remote CDN loading is allowed for ECharts and Three.js, but the page must implement multi-source loading, runtime readiness checks, and explicit fallback behavior if scripts fail to load.
  Can be called standalone by the user or as a post-diagnosis consumer skill from the industrial diagnostic pipeline (industrial-analysis-auto).
---

# Diagnostic HTML Visualizer

> **Family hub.** This skill is the single protocol authority for five HTML skills. Pick the mode with
> `references/family-routing.md`; the reviewer-side protocol (objectives, pass standard, output contract) lives
> once in `references/review-checklist.md`; the shared format rules (language, data truth, exclusion constraints,
> runtime readiness, artifact minimums) live once in `references/format-rules.md`.

## Language Default

**Language default**: Chinese output copy, English structured fields/enums (canonical: `references/format-rules.md` §1; full text: `references/io-and-delivery.md`).

## Core Mission

Turn a **completed diagnostic run directory** into an **HTML visual explainer page that a human can understand at a glance**.

The point of this skill is not "laying the JSON on a page", but translating diagnostic results into a front-end explanation that follows the human order of understanding. Page design philosophy:

1. First the conclusion (Hero first screen): the user knows the answer within 10 seconds
2. Then the location (3D production-line model): the user knows where the problem is within 30 seconds
3. Then the process (diagnostic reasoning): the user knows how the conclusion was reached within 1 minute
4. Finally the evidence (three-layer closed chain): the user builds trust within 2 minutes — **statistics prove correlation + physics proves causation + exclusion logic proves uniqueness**

If the directory already contains images, charts, 3D data, or visualization summaries, reuse them first; if not, reorganize the most critical ECharts charts from the real diagnostic JSONs and, when necessary, draw a simplified 3D production-line model with Three.js.

**Design system reference**: `references/report-template.html` is the visual grammar baseline (CSS variables + typography + component classes + loader wiring + ECharts/Three.js multi-source loading pattern). It is **not a fill-in-the-blank template** — the builder agent first scans real run_dir data to produce `render_manifest.json` (a data-driven page model), then assembles the page by taking components from the design system reference according to the manifest. The page structure (number of hypotheses / charts / evidence layers / section structure) is determined by the real data of this run, not by a fixed template.

## Truth Rules (6 Iron Rules + Data-Driven Assembly Rules)

The builder agent must obey the following 6 iron rules. Iron rules 3-5 already have precise structured implementations in §Style Direction (Hero 8 elements + evidence-chain three-layer visual identity + data-driven rendering protocol) and are not repeated here.

- Iron Rule 1: The page must be faithful to the diagnostic artifacts
- Iron Rule 2: Every main conclusion needs dual support + a plain-language version
- Iron Rule 3: Page delivery = data-driven assembly + visual grammar inheritance
- Iron Rule 4: 3D modeling = real-scene simplification × geometry may simplify × process must not err
- Iron Rule 5: User comprehension acceptance — three time thresholds
- Iron Rule 6: Runtime load detection is a quality concern, not a delivery afterthought

**Before Step 3 read `references/truth-rules.md` in full** (full text + sub-rules of all 6 iron rules; the structured implementations of Iron Rules 3-5 live in the visual grammar — see `references/style-grammar.md`).

## Input Contract

### Required

- `run_dir`: absolute path pointing to a diagnostic results directory

### Optional

- `output_html`: output HTML path; default `<run_dir>/diagnostic-report.html`
- `audience`: `operator` / `engineer` / `manager` / `mixed`; default `mixed`
- `visual_mode`: `executive` / `engineering` / `story`; default `story`
- `force_single_file`: `true` / `false`; default `true`

Artifact read-priority table (P0/P1/P2 `Expected Artifacts`): `references/io-and-delivery.md` §Expected Artifacts.

## Output Contract

Default outputs:

- `<run_dir>/diagnostic-report.html`
- `<run_dir>/render_manifest.json` (data-driven page model, including the `_meta.protocol_ack` protocol acknowledgement; mandatory intermediate artifact for the builder, audit baseline for the reviewer)
- `<run_dir>/html_selfcheck.json` (Step 5 self-check, 8 items PASS/FAIL + evidence; mandatory audit input for the reviewer)

The 12 page requirements, the consumer-call invocation example, the efficiency rules and the delivery closeout live in `references/io-and-delivery.md`.

## Invocation Protocol

### Standalone

When the user explicitly provides a diagnostic directory and requests front-end visualization, invoke this skill directly.

Standalone build example (incl. the full `Example:` block): `references/io-and-delivery.md`. Consumer-call form (pipeline Step 8): `references/io-and-delivery.md`.

## Execution Flow

### Step 1: Read the builder protocol

First read `references/html-builder-protocol.md` and treat it as the execution protocol.

🔴 **CHECKPOINT 1 · Protocol acknowledgement**: after reading html-builder.md, the builder agent confirms three things: (a) it understands the four-part narrative architecture; (b) it understands the data-driven rendering protocol + render_manifest modeling flow; (c) it understands the branch logic of the 8 fallbacks. **The confirmation is recorded in the `_meta.protocol_ack` field of the `render_manifest.json` produced in Step 3** (three booleans, all true). The reviewer uses this to audit whether the builder really passed the protocol gate. Do not proceed to Step 2 without confirmation.

### Step 2: Load the design system reference

Next read `references/report-template.html`. This is the **visual grammar baseline** (CSS variables + typography + component classes + loader + ECharts/Three.js multi-source loading pattern), not a fill-in template. Understand its component contract and composition rules — HTML comments in the body mark which manifest field drives each block and how counts vary with the data.

🛑 **CHECKPOINT 2 · Design system readable**: confirm the file exists and can be read in full. If unavailable, execute the Fallback 1 branch. Do not skip this step and hand-write HTML directly.

### Step 3: Build render_manifest (data-driven modeling)

Per phases 1-2 of §Data-Driven Rendering Protocol in `references/html-builder-protocol.md`: scan all JSONs in run_dir and produce `run_dir/render_manifest.json`. The manifest must faithfully reflect this run's structure:

Step 3 body (manifest field checklist): `references/render-assembly.md` §Step 3 detail.

🔴 **CHECKPOINT 3 · Manifest modeling**: all manifest fields come from real JSONs (nothing fabricated). Hypothesis/chart/evidence-layer counts faithfully reflect the data; hardcoding fixed values is forbidden. If all P0 files are missing, execute the Fallback 3 branch. Step 4 may start only after the manifest is produced.

### Step 4: Write the page — Data-Driven Rendering Protocol

**Assemble the page from the manifest, dressed in the design system reference's visual grammar.** See phase 3 of §Data-Driven Rendering Protocol in `references/html-builder-protocol.md` for details.

Step 4 body (reuse/assembly table, conclusion-type branching, data-driven checklist, fallback): `references/render-assembly.md` §Step 4 detail.

### Step 5: Validate the page

Step 5 checks (the 8 validation items): `references/render-assembly.md` §Step 5 detail.

🔴 **CHECKPOINT 4 · Self-check validation**: run the 8 checks above and produce `<run_dir>/html_selfcheck.json` (each item `{name, status: "PASS"|"FAIL", evidence}`). Any FAIL item must be fixed and the selfcheck rewritten. More than 3 fixes → return to Step 4 and re-examine the page structure. This JSON is a mandatory audit input for the reviewer.

If the environment allows previewing the page, actually open the page to verify the load status; do not judge success by statically reading the HTML source alone.

### Step 6: Run html-reviewer

Submit the generated page to the `html-reviewer` agent for independent review.

🛑 **CHECKPOINT 5 · Review passed**: the page may be delivered only when `html-reviewer` outputs `verdict: pass`. If `warn` — fix the warnings and resubmit for review. If `fail` — feed the blocker list back to the builder agent for revision, up to 3 revision loops; if it still fails after 3 → abort and report the blocker list to the caller.

## Visual Protocol References (mandatory reads)

- **Read `references/visual-standards.md` in full before Step 4** — four-part narrative structure, 3D scene fidelity rules, explainability design rules, comprehension acceptance test, recommended library loading strategy.
- **Read `references/style-grammar.md` in full before Step 4** — design principles, color system, typographic hierarchy, component specs (Hero/3D/chart/stat-table), mobile adaptation, styles to avoid.
- **Consult `references/fallback-rules.md` §Fallback Rules** when a Step 2/3/4/5 branch breaks (8 fallback scenarios + general degradation principles).

## 🔴 Red-Line Blacklist (hitting any item → html-reviewer verdict is fail)

> **This table is the single authoritative source for red lines.** `references/html-reviewer-protocol.md` references this table (it is not duplicated there, to avoid cross-document drift); red-line additions/removals are made only here, with the reviewer mapping table kept in sync.

| # | 🚫 Forbidden | Why | Correct |
|---|--------|--------|------|
| 1 | **Evidence chain as a flat card pile** | Users cannot tell correlation from causation | Statistics → physics → exclusion unfolded as three independent layers |
| 2 | **Evidence chain without real PNGs** | 03_figures is the primary output | Look up charts via plot_manifest.json → match to evidence layers → embed |
| 3 | **Statistics only, no physics** | ρ proves only correlation | Causal chain + an equation at every step |
| 4 | **Says A but not why not B/C/D** | Trust not closed | Per-hypothesis exclusion reasons + raw vs. detrended |
| 5 | **3D draws a generic factory** | Decoration garbage | Recover sections from ontology → real temperature zones → anomaly placement |
| 6 | **No text beside charts** | Incomprehensible | Three lines per chart: what is seen / what it means / why it matters |
| 7 | **No conclusion on the first screen** | The answer requires scrolling | Hero area conclusion at the very top |
| 8 | **Jargon untranslated** | Non-algorithm users cannot understand | ρ=0.73 → "directions nearly agree" |
| 9 | **Images 404** | Visual evidence lost | Relative paths + onerror |
| 10 | **Section count contradicts the scene** | The 3D overturns the conclusion | Recover ground truth from ontology + 3d_model_data |
| 11 | **Fabricated data** | Falsification | Use only real run_dir JSONs |
| 12 | **Reviewer not run** | Broken logic chain | 3-revision-loop cap |
| 13 | **Dark industrial style** | Incompatible with the v2 template | Light minimal on white; dark only if the user explicitly requests it |
| 14 | **render_manifest not produced / page structure mismatches the manifest** | Structure cannot be audited | Manifest produced first and aligned item by item with page section/card/chart/evidence-layer counts |
| 15 | **Cross-run contamination** (residual signature data from other runs such as stick-slip/quench/specific ρ values) | Data falsification | All numbers/equipment/hypotheses explainable by this run's data |

## Data Truth Mandate

**Every number written into JSON/reports must be recomputable from the raw data.** The full rule table (+ no-cross-run-contamination) lives in `references/format-rules.md` §2 (moved pointer text: `references/io-and-delivery.md`).

## Counterfactual Reasoning — Exclusion Constraints

The four exclusion conditions, the quantitative exclusion standard, the physical-boundary rule, and the `[WEAK_EXCLUSION]` threshold (<80) live in `references/format-rules.md` §3 (moved pointer text: `references/io-and-delivery.md`).

## Assumptions & Limitations

Report-content table (data limitations / model assumptions / confounders / confidence intervals): `references/io-and-delivery.md`.

## Verification

```bash
SHARED_PATH="<path-to-.claude/shared>"

# Check output exists and minimum size
test "$(wc -c < "$RUN_DIR/diagnostic-report.html")" -ge 5120

# Validate html_review.json if present
test -f "$RUN_DIR/05_review/html_review.json" && \
  node "$SHARED_PATH/scripts/validate.mjs" \
    "$SHARED_PATH/schemas/html_review_schema.json" \
    "$RUN_DIR/05_review/html_review.json"
```

Pipeline event logging + deliverable closeout: `references/io-and-delivery.md`.

## References Directory

The `references/` directory contains the following files:

| File | Purpose |
|------|---------|
| `report-template.html` | **Design system reference + loader scaffolding** (not a fill-in template). Provides CSS variables, typographic hierarchy, all component classes, the loader status strip, the ECharts/Three.js multi-source loading pattern, and @media breakpoints. The HTML comments in the body are the component composition contract, marking which `render_manifest.json` field drives each block and how counts vary with the data. The builder produces the manifest first, then assembles the page by taking components from here according to the manifest. |
| `html-builder-protocol.md` | Builder execution protocol v3 (Understand → Model → Render, manifest schema, hard requirements, evidence architecture, checklists). |
| `html-reviewer-protocol.md` | Reviewer execution protocol v3 (required reading, manifest-faithfulness audit; points to `review-checklist.md` for the six objectives + output contract). |
| `review-checklist.md` | **Canonical reviewer-side checklist** (single copy): independence rules, six review objectives, red-line audit procedure + check↔red-line mapping, comprehension test, pass standard, decision rule, `html_review.json` output contract, failure recovery. Shared by both reviewer skills. |
| `format-rules.md` | **Canonical shared format rules** (single copy): language default, Data Truth Mandate, exclusion constraints, runtime readiness requirements, artifact minimums + gate matrix. Shared by all five family skills. |
| `family-routing.md` | Mode matrix for the five HTML skills (authority / plain build / plain review / enhanced build / enhanced review) + negative-boundary routing to neighbouring skills. |
| `truth-rules.md` | The 6 iron rules in full (moved from §Truth Rules). Mandatory read before Step 3. |
| `render-assembly.md` | Steps 3-5 execution detail: manifest field checklist, component assembly/reuse table, conclusion-type branching, data-driven checklist, the 8 validation checks. |
| `visual-standards.md` | Four-part narrative structure, required information layers, 3D scene fidelity rules, explainability design rules, comprehension acceptance test, library loading strategy. Mandatory read before Step 4. |
| `style-grammar.md` | Style direction & visual grammar: design principles, CSS-variable color system, typography, Hero/section/evidence-chain/3D/chart/stat-table specs, mobile adaptation, styles to avoid. Mandatory read before Step 4. |
| `fallback-rules.md` | The 8 fallback scenarios + general degradation principles. |
| `io-and-delivery.md` | Expected-artifacts read-priority table, the 12 page requirements, standalone + consumer-call invocation, efficiency rules, Assumptions & Limitations table, Data Truth / exclusion pointer text, pipeline event logging, deliverable closeout. |