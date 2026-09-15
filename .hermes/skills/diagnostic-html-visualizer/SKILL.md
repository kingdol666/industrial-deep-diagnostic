---
name: diagnostic-html-visualizer
description: "Generate a human-friendly HTML explanation page from a diagnostic run folder. Use whenever the user asks to visualize diagnosis results, create an HTML report/page/dashboard/front-end explainer, render diagnostic conclusions with ECharts or Three.js, or turn a run directory into a page that operators, managers, and engineers can understand at a glance. Strongly prefer this skill after the industrial diagnostic pipeline (industrial-analysis-auto) finishes, especially when a folder contains report.md, ontology.json, diagnosis.json, evidence.json, reasoning_chain.json, plot_manifest.json, or 3d_model_data.json. Do NOT use for doing the diagnosis itself, generic marketing landing pages, or cases where no diagnostic artifacts are available. Trigger: diagnostic results visualization, HTML report generation, frontend explainer page, visualize evidence chain, diagnostic webpage, dashboard, html explain page, render diagnosis to html, visualize run folder."
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

## Language Default

Default output language is Chinese. Page copy, chart captions, evidence-chain explanations, and action recommendations are all written in Chinese. Structured field names, code variable names, and JSON enum values remain in English.

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

### Iron Rule 1: The page must be faithful to the diagnostic artifacts

- Use only the diagnostic conclusions, evidence, images, statistical results, and ontology information that really exist in the run directory
- Fabricating "nicer looking" conclusions is not allowed
- If a piece of evidence is missing, explicitly mark "this evidence layer is currently missing" instead of pretending it exists
- **All page data comes from real JSON files** — every field of `render_manifest.json` must be traceable to real run_dir artifacts; inventing numbers or hypotheses is forbidden

### Iron Rule 2: Every main conclusion needs dual support + a plain-language version

Every main conclusion must include structured evidence cards:

1. **Visual evidence**: at least one of charts, time-aligned plots, profile plots, 3D anomaly localization, or flow diagrams
2. **Reasoning evidence**: at least one of statistical conclusions, physical mechanisms, exclusion logic, or competing-hypothesis comparison
3. **Plain-language version**: a one-sentence Chinese explanation free of statistical jargon (so that non-algorithm users can retell it)

### Iron Rule 3: Page delivery = data-driven assembly + visual grammar inheritance

**Build the model first, then render.** The builder agent must first scan the real run_dir JSONs and produce `render_manifest.json` (the page model; schema in `references/html-builder-protocol.md`), then assemble the page according to the manifest. `references/report-template.html` is the visual grammar baseline, not a fill-in skeleton — it provides CSS variables, typography, component classes, the loader, and the ECharts/Three.js loading patterns.

The builder agent's job is:
1. **Understand** — scan all diagnostic JSONs + report.md + plot_manifest in run_dir
2. **Model** — produce `render_manifest.json`: this run's conclusion type, hypothesis list, three-layer evidence availability, chart list, process flow, anomaly placement (counts vary with the real data)
3. **Assemble** — select components per the manifest: Hero is always present; 3D only when the process flow is recoverable; chart count = real signal count; evidence article count = real hypothesis count; evidence layers rendered per availability or honestly marked `.evidence-missing`
4. **Inherit grammar** — take CSS/component classes/loader wiring from the design system reference (keep `<style>`, Loader, importmap, loading logic, `@media`)
5. **Bind** — all numbers/copy/paths come from the manifest (sourced from real run_dir JSONs)

**Not allowed**: modifying CSS token values, deleting the Loader panel, changing the four-part order, replacing the `.evidence-layer` structure with `<div>`s, hardcoding device/hypothesis/chart counts, or carrying residual data from other runs into this report.

### Iron Rule 4: 3D modeling = real-scene simplification × geometry may simplify × process must not err

- First recover the real sections → equipment order → material flow from `ontology.json`, `report.md`, `diagnosis.json`, `3d_model_data.json`
- Geometry may be simplified (boxes/cylinders instead of real equipment), but the process logic (section order / temperature-zone coloring / anomaly placement) must not be broken
- **Geometry is chosen by the equipment's physical role, not a default "roll/cylinder"** (BOPET roll groups are a special case, not the default): rolls/winders → cylinder; vessel-like equipment (headbox/reactor/mixing tank) → box; planar continua (forming wire/conveyor belt/film web) → thin plate; pipes/flow direction → tube. Equipment types are inferred from the equipment `role`/`type` in ontology/3d_model_data; assuming the shape of equipment in some domain is forbidden
- 🚫 Generic factory decoration / wrong equipment count / out-of-order sections / anomaly highlighted on the wrong equipment

### Iron Rule 5: User comprehension acceptance — three time thresholds

| Time | Should be able to answer | Corresponding page block |
|------|---------|------------|
| 5-15 seconds | What is the conclusion / where is it / what to do next | Hero |
| 1-2 minutes | Why not something else / strongest evidence / how the conclusion was reached | Section 02 |
| On drill-down | Detailed charts / hypothesis comparison / limitations | Section 03 |

### Iron Rule 6: Runtime load detection is a quality concern, not a delivery afterthought

- ECharts and Three.js must use multi-source loading (jsdelivr → unpkg) + a runtime status panel (5 indicators) + static fallback content on failure
- The page must not go blank or fail silently because a CDN is unavailable
- The Loader status strip faithfully reflects: ECharts / Three.js / OrbitControls / chart initialization / 3D scene initialization

## Input Contract

### Required

- `run_dir`: absolute path pointing to a diagnostic results directory

### Optional

- `output_html`: output HTML path; default `<run_dir>/diagnostic-report.html`
- `audience`: `operator` / `engineer` / `manager` / `mixed`; default `mixed`
- `visual_mode`: `executive` / `engineering` / `story`; default `story`
- `force_single_file`: `true` / `false`; default `true`

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

## Output Contract

Default outputs:

- `<run_dir>/diagnostic-report.html`
- `<run_dir>/render_manifest.json` (data-driven page model, including the `_meta.protocol_ack` protocol acknowledgement; mandatory intermediate artifact for the builder, audit baseline for the reviewer)
- `<run_dir>/html_selfcheck.json` (Step 5 self-check, 8 items PASS/FAIL + evidence; mandatory audit input for the reviewer)

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

## Invocation Protocol

### Standalone

When the user explicitly provides a diagnostic directory and requests front-end visualization, invoke this skill directly.

Example:

```text
/diagnostic-html-visualizer build run_dir="<absolute-path-to-your-run-dir>"
```

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

## Execution Flow

### Step 1: Read the builder protocol

First read `references/html-builder-protocol.md` and treat it as the execution protocol.

🔴 **CHECKPOINT 1 · Protocol acknowledgement**: after reading html-builder.md, the builder agent confirms three things: (a) it understands the four-part narrative architecture; (b) it understands the data-driven rendering protocol + render_manifest modeling flow; (c) it understands the branch logic of the 8 fallbacks. **The confirmation is recorded in the `_meta.protocol_ack` field of the `render_manifest.json` produced in Step 3** (three booleans, all true). The reviewer uses this to audit whether the builder really passed the protocol gate. Do not proceed to Step 2 without confirmation.

### Step 2: Load the design system reference

Next read `references/report-template.html`. This is the **visual grammar baseline** (CSS variables + typography + component classes + loader + ECharts/Three.js multi-source loading pattern), not a fill-in template. Understand its component contract and composition rules — HTML comments in the body mark which manifest field drives each block and how counts vary with the data.

🛑 **CHECKPOINT 2 · Design system readable**: confirm the file exists and can be read in full. If unavailable, execute the Fallback 1 branch. Do not skip this step and hand-write HTML directly.

### Step 3: Build render_manifest (data-driven modeling)

Per phases 1-2 of §Data-Driven Rendering Protocol in `references/html-builder-protocol.md`: scan all JSONs in run_dir and produce `run_dir/render_manifest.json`. The manifest must faithfully reflect this run's structure:

- Conclusion type (DETERMINED / COMPETING_SET / NEEDS_DATA) + main conclusion + confidence ceiling
- `hypotheses[]` real hypothesis list (count follows the data, not fixed)
- `evidence_layers` real `available` status of each of the three layers (missing layers marked false)
- `charts[]` real presentable signal list (count follows the data, not fixed at 5)
- `process_flow` (sections / equipment count / anomaly placement, only when recoverable)
- `available_pngs[]` with the `suggested_layer` of each PNG

🔴 **CHECKPOINT 3 · Manifest modeling**: all manifest fields come from real JSONs (nothing fabricated). Hypothesis/chart/evidence-layer counts faithfully reflect the data; hardcoding fixed values is forbidden. If all P0 files are missing, execute the Fallback 3 branch. Step 4 may start only after the manifest is produced.

### Step 4: Write the page — Data-Driven Rendering Protocol

**Assemble the page from the manifest, dressed in the design system reference's visual grammar.** See phase 3 of §Data-Driven Rendering Protocol in `references/html-builder-protocol.md` for details.

**Reuse directly (copied verbatim from the design system reference)**:
- The entire `<style>` block (CSS variables + typography system + component styles + @media)
- Loader status strip structure (`#loaderStrip` + 5 `.ls-dot` elements)
- Three.js importmap + scene initialization scaffolding (scene/camera/renderer/controls/lights/grid)
- ECharts loader logic (primary source → backup source → failure reporting)

**Select components per the manifest (counts determined by data, not fixed values)**:
| Block | Render condition | manifest driving field |
|------|---------|-----------------|
| Hero | Always present | `conclusion` + `scope` (8 elements; `.hero-meta` field count follows real scope availability)|
| 3D module | `process_flow.recoverable=true` | `process_flow` (sections / equipment count / anomaly placement follow real data)|
| Statistics table | Detrended statistics available | `hypotheses[].stats` |
| Charts | One per item in `charts[]` | `charts[]` (count follows real signals, not fixed at 5)|
| Evidence layers Ⅰ/Ⅱ/Ⅲ | Each layer `available=true` | `evidence_layers.*` (missing layer → honest `.evidence-missing` marker)|
| Evidence articles | One per item in `hypotheses[]` | `hypotheses[]` (count follows real hypotheses, not fixed at 3)|
| Action recommendations | One line per item in `actions[]` | `actions[]` |

**Conclusion-type branching**:
- `DETERMINED` → Hero asserts a single root cause
- `COMPETING_SET` → Hero explicitly presents uncertainty + confidence ceiling
- `NEEDS_DATA` → Hero states the conclusion has not yet converged + what data is missing

**Data-driven assembly checklist (confirm item by item before writing the page)**:
- [ ] Page section/card/chart/evidence-layer counts match `render_manifest.json`
- [ ] No hardcoded device counts (e.g. "18 rolls"), hypothesis counts, or chart counts
- [ ] All numbers/copy/paths come from the manifest (sourced from real run_dir JSONs)
- [ ] Missing evidence layers carry an honest `.evidence-missing` marker; do not pretend they exist
- [ ] `<style>` / Loader / importmap / loading logic / @media reused verbatim, no invented tokens
- [ ] `img src` relative paths + `onerror` degradation
- [ ] Every chart has a `.chart-reading` three-line reading (what is seen / what it means / why it matters)

**Fallback when the design system reference is unavailable**: execute the Fallback 1 branch (see §Fallback Rules), falling back to `templates/page_blueprint.md` + `templates/render_prompt_template.md` to build from scratch (still selecting components per the manifest).

### Step 5: Validate the page

Check at minimum:

- Whether the HTML opens
- Whether ECharts / Three.js / OrbitControls each have a primary source + backup source + success detection
- Whether at least one chart really initialized (`echarts.getInstanceByDom`)
- Whether at least one Three.js scene really rendered (canvas element exists)
- Whether local image paths are accessible relative to the output file
- **Whether the evidence chain is complete in all three layers, each supported by real images/data/reasoning**
- Whether main conclusion, key evidence, exclusion logic, action recommendations, and limitations are all present
- Whether the user can understand "why this conclusion was reached" without statistical jargon

🔴 **CHECKPOINT 4 · Self-check validation**: run the 8 checks above and produce `<run_dir>/html_selfcheck.json` (each item `{name, status: "PASS"|"FAIL", evidence}`). Any FAIL item must be fixed and the selfcheck rewritten. More than 3 fixes → return to Step 4 and re-examine the page structure. This JSON is a mandatory audit input for the reviewer.

If the environment allows previewing the page, actually open the page to verify the load status; do not judge success by statically reading the HTML source alone.

### Step 6: Run html-reviewer

Submit the generated page to the `html-reviewer` agent for independent review.

🛑 **CHECKPOINT 5 · Review passed**: the page may be delivered only when `html-reviewer` outputs `verdict: pass`. If `warn` — fix the warnings and resubmit for review. If `fail` — feed the blocker list back to the builder agent for revision, up to 3 revision loops; if it still fails after 3 → abort and report the blocker list to the caller.

## Visual Standards

### Required information layers

The first screen must directly provide:

- The main conclusion in one sentence
- 3-4 sentences of plain-language explanation (no statistical jargon)
- Diagnosis type / Judge score / confidence ceiling / focus product / sample size / anomalous section
- 4-cell key findings (strongest evidence + excluded factors + recommended action + evidence gap)
- A very short "how to read this page" guide

### Four-part narrative structure

#### 0. Hero — Conclusion first (8 mandatory elements, no omissions allowed)

All 8 of the following elements must appear in the Hero area:

1. `.hero-bar` — 36px×3px ink hairline
2. `.display` — serif display headline, `<em>` emphasizes keywords
3. `.hero-lede` — 3-4 sentences of plain-language explanation, ≤640px wide
4. `.hero-meta` — diagnosis type / Judge score / confidence / focus product / sample size / anomalous section (minimum 5 items)
5. `.key-findings` — 4-cell key findings grid (1px split border): strongest evidence / excluded / recommended action / evidence gap
6. Each cell contains `.kl` (label) + `.kv` (value) + optional `.kd` (supplementary note)
7. Reading-guide caption — one sentence explaining the page's top-to-bottom browsing order
8. Every one of the 4 cells must contain a concrete value; empty strings or Lorem placeholders are not allowed

#### 1. Background and production-line modeling

- Scenario description + anomaly localization
- 3D production-line model: section platforms + roll groups (radii scaled from real data) + three-zone coloring + anomaly highlighting + numbered labels + flow direction
- Legend + data source annotation

#### 2. Diagnostic reasoning process

- Key statistics table (before/after detrending comparison: parameter / ρ / p / decay rate / verdict)
- 3-5 ECharts charts, each with a three-line reading
- Embedded real PNG screenshots (time-aligned plots, Simpson's paradox visualizations, etc.)
- Plain-language explanations of key methods (detrending, stratified analysis, competing hypotheses)

#### 3. Evidence chain — three-layer closed architecture

**This is the page's core persuasion block. It must contain real production-line diagnostic images, data analysis, and physical logic reasoning.**

**Layer 1 · Statistical evidence (Ⅰ):**
- Reuse scatter/correlation PNGs + ECharts detrended scatter plot
- Statistical evidence strength score bar
- Evidence article: complete statistics of the strongest surviving signal

**Layer 2 · Physical mechanism (Ⅱ):**
- HTML/CSS physical causal-chain flow diagram
- Reuse temperature/torque zone profile PNGs
- Per-step physical magnitude estimation
- Physical evidence strength score bar

**Layer 3 · Exclusion logic (Ⅲ):**
- Reuse causal evidence map PNG
- Per-hypothesis evidence articles (including visual explanation blocks for exclusion reasons)
- Comprehensive verdict matrix table
- Action recommendations + limitations

### Technical implementation advice

- Prefer ECharts for charts
- Prefer Three.js + OrbitControls for the 3D production line
- Prefer single-file HTML with data inlined as much as possible
- Script loading needs primary CDN + backup CDN + runtime status panel + fallback copy

### 3D Scene Fidelity Rules

When building the 3D scene, use the following priority order:

1. If `3d_model_data.json` exists, treat it as the scene skeleton first
2. Then use `ontology.json` to validate section names, equipment order, material flow
3. Use `report.md` / `diagnosis.json` / `evidence.json` to mark anomalous sections, anomalous roll positions, and key evidence locations

Minimum requirements:

- Section order correct
- Each section's physical role correct
- Anomaly points placed correctly
- Material flow direction correct
- Temperature-zone or functional-zone differences visually distinguished

Simplification allowed:

- No pursuit of CAD-level precision
- Basic geometric primitives instead of real equipment shapes

But the following are not allowed:

- Reversed section order
- Mixing up the quench, stretch, and preheat sections
- Anomaly highlight on the wrong equipment
- Replacing the current scene with a completely generic factory decoration

### Explainability Design Rules

To make the page easy for users to understand, enforce:

1. **Conclusion first**
   - The first screen tells the user "what the conclusion is" before unfolding the process
2. **One screen, one task**
   - Each major block answers only one core question; avoid one block explaining too many things at once
3. **Terms grounded**
   - Every statistical or methodological term is followed by a plain-language explanation
4. **Text-image binding**
   - Every chart is explained directly beside it; "chart up top, explanation far below" is not allowed
5. **Evidence layering**
   - Primary evidence first; secondary and extended evidence afterwards
6. **Exclusion logic made explicit**
   - Not only "what is most likely", but also "why the other candidates are ruled out"
7. **Action loop closure**
   - By the end of the page the user must know how to verify next, how to act, and how to keep collecting evidence

### Comprehension Acceptance Test

After generating the page, self-check whether a user without an algorithm background can answer these 6 questions:

1. What is the final conclusion this time?
2. Where in the production line did the problem occur?
3. What is the strongest evidence?
4. Why not another cause that also looks correlated?
5. How was this conclusion reached step by step?
6. What is the most important next step?

If 2 or more questions are not quickly answerable from the page, the page fails and the information structure must be redone.

### Recommended Library Loading Strategy

For every library use the order "primary source → backup source → failure report".

Recommended order:

- ECharts
  - `https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js`
  - `https://unpkg.com/echarts@5/dist/echarts.min.js`
- Three.js (via importmap ES module, not the legacy global script)
  - `importmap`: `"three": "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js"`
  - `importmap`: `"three/addons/": "https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"`
  - Backup importmap source: replace jsdelivr with unpkg
- OrbitControls (ES module import, not the examples-directory global script)
  - `import('three/addons/controls/OrbitControls.js')`
  - After Three.js r152 the `examples/js/` directory was removed; OrbitControls must be loaded via the ES module path under `examples/jsm/`

The page must embed a loader status area showing:

- `ECharts: loaded / fallback / failed`
- `Three.js: loaded / fallback / failed`
- `OrbitControls: loaded / optional-missing / failed`
- `Charts initialized: yes / no`
- `3D scene initialized: yes / no`

## Fallback Rules

The following covers the complete fallback chain for 8 common failure scenarios. Each rule's format: **trigger condition → first-line fix → last-resort fallback**. The builder agent must execute the corresponding branch when a scenario occurs; silently continuing is not allowed.

### Fallback 1: `references/report-template.html` (design system reference) unavailable

**Trigger condition**: the builder agent cannot read the design system reference file in Step 2
**First-line fix**: fall back to the four-part narrative structure of `templates/page_blueprint.md` + the build conventions of `templates/render_prompt_template.md`, **still selecting components per `render_manifest.json`**, and hand-write the HTML from scratch (inlining key CSS variables and typography rules)
**Last-resort fallback**: abort generation and report to the caller: "Both the design system reference and the fallback blueprint are unavailable; a high-quality report cannot be generated. Please check whether the skill installation is complete."

### Fallback 2: `run_dir` path invalid or nonexistent

**Trigger condition**: `run_dir` is not a valid absolute path, or contains no diagnostic artifacts
**First-line fix**: check whether the path string is correct, whether a leading `/` is missing, or whether a relative path was used. Try searching the current working directory and `workspace/diagnostic-runs/`
**Last-resort fallback**: abort generation and report a clear path error to the caller, listing the alternative paths already tried

### Fallback 3: Key JSON (diagnosis.json) empty or malformed

**Trigger condition**: `04_diagnostics/diagnosis.json` exists but `JSON.parse` fails, or the `primary_finding` field is an empty string
**First-line fix**: degrade to reading the "Executive Summary" section of `report.md` and extract the main conclusion text; skip hypothesis scoring and confidence details
**Last-resort fallback**: mark the page Hero with "[Diagnostic conclusion data missing; the following is a summary extracted from report.md]"; mark the three evidence-chain layers "[JSON data unparseable]"; do not fabricate statistics

### Fallback 4: `03_figures/` directory empty or all PNGs 404

**Trigger condition**: all PNGs listed in `plot_manifest.json` are missing or fail to load
**First-line fix**: read array data from `viz_compact.json` / `diagnosis.json` / `evidence.json` and rebuild the key charts with ECharts (detrended scatter, robustness comparison, temperature-torque profile)
**Last-resort fallback**: replace all "real PNGs" in the three evidence-chain layers with ECharts rebuilds (marked "ECharts rebuild · original image unavailable"); the physical causal-chain flow diagram remains HTML/CSS

### Fallback 5: Both primary and backup sources fail for ECharts or Three.js

**Trigger condition**: the status of both `document.getElementById('dotEcharts')` and `document.getElementById('dotThree')` is fail
**First-line fix**: keep summary cards, text explanations, all local PNGs (`<img>` tags are unaffected), and the static evidence-chain modules; all loader status strip indicators turn red
**Last-resort fallback**: the first screen explicitly notes "the current browsing environment cannot load interactive charts/3D modules; the page is in static degraded mode"; keep Hero + background + statistics table + evidence article text + action recommendations (no loss of key information)

### Fallback 6: ECharts `echarts.init()` returns null (DOM not mounted)

**Trigger condition**: `echarts.getInstanceByDom(dom)` verification returns undefined
**First-line fix**: check whether the corresponding `<div id="chartN">` exists in the DOM and whether it is hidden by `display:none`; if the DOM is fine but init returns null, retry once (setTimeout 200ms)
**Last-resort fallback**: the chart's position shows the static fallback text "[Chart failed to load]" + the chart title + the text of the three-line reading; loader status strip "Charts initialized" turns red

### Fallback 7: Three.js `WebGLRenderer` creation fails (WebGL unavailable)

**Trigger condition**: `new THREE.WebGLRenderer()` throws an exception or returns null
**First-line fix**: try `THREE.WebGLRenderer({ failIfMajorPerformanceCaveat: true })` detection; if that fails try `THREE.CSS2DRenderer` pure-DOM rendering of simplified annotations; if that still fails degrade to a 2D SVG/Canvas section flow diagram
**Last-resort fallback**: the 3D container shows static fallback content "[WebGL 3D module unavailable · line structure: Preheat section (rolls 1-5) → Stretch section (rolls 6-11) → Quench & setting section (rolls 12-18)]"; keep the section text description + anomalous roll position text

### Fallback 8: both `3d_model_data.json` and `ontology.json` missing

**Trigger condition**: neither file exists
**First-line fix**: extract the production-line description text from `report.md` and `diagnosis.json` and draw a 2D section flow diagram in HTML/CSS (divs + arrow characters + color coding)
**Last-resort fallback**: replace the 3D container with "[Production-line structure data missing; the following is a text description of the sections extracted from the diagnostic conclusions]" + a text version of the section order + anomaly location text; does not affect the Hero / diagnostic reasoning / evidence chain blocks

### General degradation principles

- **No silent failure**: whenever a fallback triggers, the page must show a degraded status label at the corresponding location
- **No information loss**: after degradation the user can still obtain the Hero conclusion, key statistics, exclusion logic, and action recommendations
- **No fake success**: the loader status strip faithfully reflects each module's load status

## Style Direction & Visual Grammar

> **The builder agent must read this section before writing the page.** What is defined here is not "suggestions for reference" but the mandatory visual grammar of the page design. Fallback rules are in the next section; consult them when something breaks.

### Default: Light Minimal Narrative

**`references/report-template.html` is this Skill's sole style baseline.** What the page conveys is not a "technical system feel" but "clear diagnostic persuasiveness".

### Design principles

1. **Warm white background** — `#fafaf8` + `#f4f3f0` secondary background
2. **Single ink color throughout** — `#1e3a54` as the only accent color (ink blue)
3. **Serif headings + sans-serif body** — typographic hierarchy instead of decoration
4. **Generous whitespace + hairlines** — 1px dividers instead of card shadows
5. **Body ≤640px** — controls the reading rhythm
6. **Warm orange marks anomalies** — `#c2673a` used only for warnings/anomalies/physical mechanisms

### Color system (CSS variables — from report-template.html)

```
--bg: #fafaf8        primary background — warm white
--bg-alt: #f4f3f0    secondary background
--bg-card: #ffffff   card background
--hairline: rgba(0,0,0,0.06)  finest divider
--rule: rgba(0,0,0,0.10)      section divider
--t1: #111           body black
--t2: #4a4a4a        secondary text
--t3: #888           auxiliary text
--ink: #1e3a54       ink blue — primary accent
--warm: #c2673a      warm orange — anomalies
--green: #2d7d4f     deep green — pass
--red: #c4433b       dark red — excluded
--gold: #8a6d3b      dark gold — medium
```

### Typographic hierarchy

| Class | Font | Size | Purpose |
|------|------|------|------|
| `.display` | serif | 2.8rem/600/-0.025em | Hero conclusion |
| `h1` | serif | 1.9rem/600 | Main title |
| `h2` | serif | 1.45rem/600 | Section title |
| `.body-l` | sans | 1.08rem | Lead paragraph |
| `.body` | sans | 0.9rem | Body text |
| `.caption` | sans | 0.76rem | Figure caption |
| `.mono` | mono | 0.78rem | Statistical values |

### Hero area specification

- Top 36px × 3px hairline decoration (`--ink`)
- Serif display headline with `<em>` tags emphasizing keywords (`--warm` italic)
- Lede paragraph max-width: 640px
- Metadata row: flex-wrap + gap: 32px
- 4-cell key findings: `grid-template-columns: repeat(4, 1fr)`, 1px split border frame
- Bottom caption reading guide

### Section title specification

- Section numbers in monospace + `--t3` color + `letter-spacing: 0.1em`
- h2 headings in serif

### Evidence chain three-layer visual identity

- Each layer gets its own `.evidence-layer` container
- Layer titles carry circular numbered icons (Ⅰ/Ⅱ/Ⅲ) with color coding: statistics = ink / physics = warm orange / exclusion = dark red
- Evidence articles within a layer separated by hairline bottom borders

### Evidence strength score bar

```html
<!-- Statistical evidence strength: 85/100 -->
<div class="evidence-score">
  <div class="es-bar fill" style="width:85px"></div>
  <div class="es-bar empty" style="width:15px"></div>
  <span class="es-label">Statistical evidence strength: 85/100</span>
</div>
```

### Physical causal chain

```html
<div class="physics-chain">
  <div class="pc-step"><div class="pc-title">① Non-uniform roll surface μ</div><div class="pc-detail">Oligomer deposition<br>μ_s > μ_k</div></div>
  <div class="pc-arrow">→</div>
  <!-- ... more steps ... -->
</div>
```

### Statistical emphasis label

```html
<span class="stat-callout">ρ=+0.554, p=0.014</span>
<!-- Rendered as: monospace + ink color + light ink background -->
```

### 3D container specification

- Height: 500px (desktop) / 340px (tablet) / 260px (mobile)
- Background: `#ecebe6` (warm gray, matching the white background)
- Hover: `cursor: grab` / `cursor: grabbing`
- Overlay: top-left monospace + translucent white background
- Legend: bottom-right + 5 color swatches (preheat/stretch/quench/anomaly/flow direction)

### Chart container specification

- ECharts chart height: 380px (desktop) / 280px (tablet)
- Chart titles use `.chart-panel-header` + monospace numbering
- Three-line readings use `.chart-reading` (grid: 90px + 1fr)
- The three reading labels ("What is seen / What it means / Why it matters") in monospace + ink color
- Global ECharts palette: `['#1e3a54', '#2d7d4f', '#c2673a', '#c4433b', '#8a6d3b']`

### Statistics table specification

```css
.stat-table { width:100%; border-collapse:collapse; }
.stat-table thead th { text-transform:uppercase; letter-spacing:0.08em; color:var(--t3); border-bottom:1px solid var(--rule); }
.stat-table tbody td { border-bottom:1px solid var(--hairline); }
.stat-table .num { font-family:var(--mono); text-align:right; }
.stat-table .hi { color:var(--ink); font-weight:600; }
.stat-table .lo { color:var(--t3); }
```

### Mobile adaptation (mandatory)

```css
@media (max-width: 768px) {
  .page { padding: 0 18px; }
  .hero .display { font-size: 1.7rem; }
  .key-findings { grid-template-columns: repeat(2, 1fr); }
  .threejs-stage { height: 340px; }
  .chart-canvas { height: 280px; }
  .chart-reading { grid-template-columns: 1fr; }
  .section { margin: 56px 0; }
  .reading-nav { display: none; }
  .physics-chain { flex-wrap: wrap; }
}
@media (max-width: 480px) {
  .key-findings { grid-template-columns: 1fr; }
  .threejs-stage { height: 260px; }
  .hero-meta { gap: 18px; }
}
```

### Styles to avoid

| Forbidden | Why |
|------|------|
| Dark industrial style (080d14 deep background) | Incompatible with the current template, unless the user explicitly requests it |
| Piled-up card shadows | White background uses hairline dividers; hierarchy is not built on shadows |
| Colored top decoration lines | Use a single ink color; do not invent colors |
| Purple gradients / neon glow | AI slop carrying zero brand information |
| A screen full of jumping KPI numbers | Users come to understand a conclusion, not to monitor |
| Image-wall tiling | Every chart must have a three-line reading, no exceptions |

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

**Every number written into JSON/reports must be recomputable from the raw data.**
|Rule|Requirement|
|---|---|
|Number traceability|Every number must state the data source (cleaned/raw), row range, and computation method|
|Derived value marking|Inferred/derived values must be explicitly `"derived": true` or `"inferred": true`|
|Cleaning audit trail|cleaning_integrity records all cleaning operations|
|Visualization traceability|Every data point in every chart is traceable to a specific row of the dataset|
|Unavailable marking|What cannot be computed from the data → write NOT_APPLICABLE + reason|

## Counterfactual Reasoning — Exclusion Constraints

|Constraint|Description|
|---|---|
|Four conditions|Temporal precedence + statistical significance + physical mechanism + no contradiction|
|Exclusion standard|Any condition unmet → mark as an excluded candidate and provide quantitative grounds|
|Physical boundary|Exclusions must be supported by first principles or governing equations|
|Confidence threshold|Exclusion confidence <80 is marked `[WEAK_EXCLUSION]`|

## Assumptions & Limitations

|Category|Requirement|
|---|---|
|Data limitations|Sampling rate / noise / missing extremes / range limits|
|Model assumptions|Linear approximation / steady-state assumption / distribution assumptions|
|Uncontrolled confounders|Explicitly list potential confounding variables that cannot be controlled|
|Conclusion confidence interval|Each conclusion annotated with confidence ± error margin|

## Efficiency — Parallel Execution

- When there is no data dependency with upstream/downstream agents → parallelize proactively
- Use deterministic scripts instead of LLM reasoning for predictable results
- Large-file sampling strategy: systematic sampling when >100K rows
- Agent stall >600s → check existing artifacts; continue with partially available results

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

## Pipeline Event Logging

```bash
node "$SHARED_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" \
  --event agent_complete --agent html-visualizer --step present \
  --files diagnostic-report.html
```

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

## References Directory

The `references/` directory contains the following files:

| File | Purpose |
|------|------|
| `report-template.html` | **Design system reference + loader scaffolding** (not a fill-in template). Provides CSS variables, typographic hierarchy, all component classes, the loader status strip, the ECharts/Three.js multi-source loading pattern, and @media breakpoints. The HTML comments in the body are the component composition contract, marking which `render_manifest.json` field drives each block and how counts vary with the data. The builder produces the manifest first, then assembles the page by taking components from here according to the manifest. |
