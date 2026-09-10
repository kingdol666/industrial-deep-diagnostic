# Universal Render Prompt Template v3

When the task needs to be handed off to another implementation agent, the block below can serve as the base prompt (replace the `{RUN_DIR}` / `{OUTPUT_HTML}` placeholders with real paths):

```text
Read the diagnostic artifacts under the diagnostic working directory `{RUN_DIR}` and generate a complete HTML visualization explainer page, output to `{OUTPUT_HTML}`.

The goal is that industrial users without an algorithm background can grasp the diagnostic conclusion, the anomaly location, the reasoning path, and the evidence chain at a glance.

## Execution flow (data-driven, three phases)

1. **Understand** — scan all diagnostic JSON under `{RUN_DIR}` + report.md + plot_manifest.json
2. **Model** — first produce `{RUN_DIR}/render_manifest.json` (the page model; schema in references/html-builder-protocol.md).
   The manifest must faithfully reflect this run: conclusion type, hypothesis list (count follows the data),
   availability of the three evidence layers, chart inventory (count follows the data), process flow,
   anomaly placement. Every field must be traceable to real JSON; nothing fabricated.
3. **Render** — assemble the page by selecting components per the manifest, dressed in the visual grammar of the design system reference.

## Design system reference

`references/report-template.html` is the **visual grammar baseline** (CSS variables + typography + component classes + loader +
ECharts/Three.js multi-source loading pattern), not a fill-in-the-blank template. The HTML comments inside the body mark which
manifest field drives each block and how the counts vary with the data. After reading it:

1. **Reuse verbatim** — the entire `<style>` CSS, the loader status strip, the importmap, the ECharts/Three.js loading logic, the @media breakpoints
2. **Select components per the manifest** (counts are decided by the data, not fixed):
   - Hero always present (fill its 8 elements from conclusion + scope; the number of meta fields follows the real available scope items)
   - 3D only when `process_flow.recoverable=true` (sections / equipment count / anomaly placement follow the real data)
   - Chart count = `charts[]` count (not a fixed 5)
   - Evidence article count = `hypotheses[]` count (not a fixed 3)
   - Render evidence layers per `evidence_layers.*.available`; missing layers get `.evidence-missing`
3. **Bind real data** — every value / piece of copy / path comes from the manifest (sourced from the real run_dir JSON)
4. **Image src uses relative paths + onerror degradation**

## Four mandatory parts

### 0. Hero — conclusion first
- The main conclusion in one sentence (serif display, em emphasizing the keywords)
- A 3-4 sentence plain-language explanation
- Metadata tag row: diagnosis type / Judge score / confidence ceiling / focus product / sample size / anomalous section
- Four-cell key-findings grid: strongest evidence / excluded factors / recommended action / evidence gap
- Reading guide

### 1. Background and production-line modeling
- Scenario description + anomaly localization
- Three.js 3D production-line model (section platforms + roll groups + anomaly highlight + material flow + three-zone colors + legend)
- The 3D scene must recover the real structure from ontology.json + 3d_model_data.json + viz_model_data.json
- Annotate the data source below the 3D container

### 2. Diagnostic reasoning process
- Key statistics table (before/after detrending comparison: parameter / Spearman ρ / p value / decay rate / verdict)
- 3-5 ECharts charts, each with a three-line reading (what is seen / what it means / why it matters)
- Chart data must come from real JSON files (viz_compact.json, diagnosis.json, etc.)
- Plain-language explanation of the key methods

### 3. Evidence chain (three-layer architecture) ⚠️ This is the core block where user trust is built

**Figure-embedding iron rules**: every embedded PNG must be the "figure + data + reading" trio — (1) a real PNG from `03_figures/`, matched to an evidence layer via `plot_manifest.json.suggested_layer`; (2) the real statistical/physical value + source file labeled beside the figure; (3) a three-line plain-language reading. Missing any one of the three makes the reviewer return fail. If a statistical/physical conclusion has no matching figure or traceable value → mark `.evidence-missing`; do not pretend.

#### Layer 1 · Statistical evidence (Ⅰ)
- Embed `fig_vlm_simpson_*.png` + `fig_vlm_synchronization.png` (from `03_figures/`, selected by suggested_layer=statistical)
- Annotate the real values below the figures: Spearman ρ / p / n (source `feature_summary.json`) + detrended r + Simpson detection result (source `validate_report.json`)
- At least 1 ECharts rebuilt analysis chart (detrended scatter / correlation-robustness comparison)
- Statistical evidence strength score bar
- Evidence article: state explicitly the **strongest surviving signal after detrending**, with the complete ρ + p + decay rate + source

#### Layer 2 · Physical mechanism (Ⅱ)
- Embed `fig_vlm_temporal_overlay_focus_*.png` (parameter → quality temporal alignment) + `fig_vlm_event_response.png`
- Annotate below the figures: time lag N minutes (source `time_lag_analysis.json`) + the temporal-precedence evidence that the parameter changes first and the quality follows
- HTML/CSS physical causal-chain flow diagram (each step from `diagnosis.json.physical_logic_chain`)
- Each step carries a **real physical equation or order-of-magnitude estimate** (source `physics_check.json`, e.g. Arrhenius k=A·exp(-Ea/RT), ΔT → % change in rate)
- Explain the spatial consistency between the anomaly location and the physical mechanism
- Physical evidence strength score bar

#### Layer 3 · Exclusion logic (Ⅲ)
- Embed `fig_causal_map.png` (surviving edges vs excluded edges, each labeled with r)
- Write one article per excluded or weakened hypothesis (hypothesis count = the `render_manifest.json` hypothesis count, not hardcoded):
  - Hypothesis name + exclusion/weakening confidence
  - **Raw evidence vs post-detrending truth** comparison (the specific change in r, source `validate_report.json`)
  - Physical contradiction or internal inconsistency (source `physics_check.json` / `diagnosis.json`)
  - A "why it was excluded" explanation block
- Evidence-chain comprehensive verdict matrix table (all hypotheses × three evidence layers)
- Action-recommendation priority table (P0/P1/P2)
- Limitations note

## Read these files first (use them where they exist)

- `report.md`
- `04_diagnostics/diagnosis.json`
- `04_diagnostics/evidence.json`
- `04_diagnostics/confidence.json`
- `04_diagnostics/reasoning_chain.json`
- `01_ontology/ontology.json`
- `02_processed/data_analysis_conclusion.json`
- `02_processed/causal_evidence_map.json`
- `02_processed/feature_summary.json`
- `02_processed/validate_report.json`
- `02_processed/anomaly_report.json`
- `03_figures/plot_manifest.json` (to obtain the chart inventory and each chart's purpose)
- `03_figures/visual_analysis.json` (to obtain the VLM-inferred chart observations)
- `03_figures/image_captions.json`
- `03_figures/*.png` / `*.jpg` (local image evidence — reuse these first!)
- `3d_model_data.json`
- `viz_model_data.json`
- `viz_data.json` / `viz_compact.json`
- `diagnostic_data.json`

## Priority order for using charts and images

1. **Reuse the existing PNGs under 03_figures/ first** — these are the original visual evidence produced by the diagnostic pipeline
2. **Redraw with ECharts when no matching PNG exists** — read the array data directly from viz_compact.json or diagnosis.json
3. **Mark an honest placeholder when data is missing** — write "[当前缺少该层证据]" rather than fabricating

## Page requirements

- Chinese-language explanation (each statistical term followed immediately by a plain-language gloss)
- Single-file HTML (CSS/JS inlined)
- ECharts primary source + backup source + runtime detection + status display + failure degradation
- Three.js importmap ES module + dynamic OrbitControls import + backup source
- Key conclusions must have "visual evidence + reasoning evidence"
- The anomalous section or anomalous roll position must be highlighted in the 3D module
- 3D modeling must match the real process flow of the current diagnostic scenario
- The page's load-status panel shows 5 status indicators
- Mobile dual-breakpoint adaptation (768px / 480px)

## Before starting 3D modeling, follow this reinforcement prompt

"I am not creating a generic industrial schematic, but a simplified industrial scene model that genuinely matches the operating logic of the current diagnostic workflow. First recover the real production-line structure, section order, material flow, key equipment, and anomaly locations from the ontology, the diagnostic conclusion, the evidence chain, 3d_model_data, and the report; then express those entities with accurate but simplified geometry. No visual simplification may break the real process logic, and every anomaly marker must land on the position this diagnosis actually points to."

## Closing report

- Which key files you read
- Where the page was output
- Which figures reuse 03_figures PNGs and which were redrawn with ECharts
- Which files the 3D scene relied on to recover the real process order
- How the anomaly locations were mapped to specific equipment / roll positions / zones
- Which data sources each of the three evidence-chain layers used
```
