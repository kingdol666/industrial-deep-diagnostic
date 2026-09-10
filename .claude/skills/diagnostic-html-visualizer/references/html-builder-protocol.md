# HTML Builder Agent Protocol v3

You are the execution sub-agent of this skill. Your job is not to restate the diagnostic results, and not to fill in a template by rote; it is to **read the real data structure of this run and assemble an HTML explainer page that can be understood at a glance**.

## Primary Objective

Input a `run_dir`, output something that opens directly:

- `<run_dir>/diagnostic-report.html`

The page must help the user answer four questions quickly:

1. Which production line / which problem / which object is this?
2. How did this diagnosis arrive at its conclusion, step by step?
3. What do the data charts actually show?
4. Why should this conclusion be believed rather than another one?

## Data-Driven Rendering Protocol (core, v3)

**Page structure is decided by the data, not by the template.** Different runs have different hypothesis counts, evidence-layer counts, chart counts, and section structures — the page must faithfully reflect that structure instead of cramming the data into a fixed number of cards.

### Three-phase flow

```
[Phase 1: Understand]  scan all run_dir JSON + report.md + plot_manifest
     ↓
[Phase 2: Model]       produce render_manifest.json (page model, intermediate artifact)
     ↓
[Phase 3: Render]      pick components per manifest + apply visual grammar + bind real data → HTML
```

### Phase 1 · Understand (Required Reading Order)

Read in the order below; use what exists, degrade for what does not — do not error out and exit:

1. `run_dir/report.md`
2. `run_dir/04_diagnostics/diagnosis.json` (main conclusion / hypotheses / confidence)
3. `run_dir/04_diagnostics/evidence.json` (evidence stratification)
4. `run_dir/04_diagnostics/reasoning_chain.json` (convergence path)
5. `run_dir/01_ontology/ontology.json` (production-line objects / sections / material flow)
6. `run_dir/03_figures/plot_manifest.json` (which charts exist, what each one is for)
7. `run_dir/03_figures/visual_analysis.json` (VLM observations on each chart)
8. `run_dir/03_figures/image_captions.json`
9. `run_dir/3d_model_data.json` + `run_dir/viz_model_data.json` (if present)
10. `run_dir/viz_data.json` / `viz_compact.json` / `diagnostic_data.json`
11. `run_dir/02_processed/data_analysis_conclusion.json` / `feature_summary.json` / `validate_report.json` / `anomaly_report.json` / `causal_evidence_map.json`

### Phase 2 · Model (render_manifest.json — mandatory intermediate artifact)

After reading the data, **produce `run_dir/render_manifest.json` first**, then write any HTML. The manifest is the structured page model of this run; it defines "what the page should look like". It is also the baseline against which `html-reviewer` checks whether "the page is faithful to the data".

manifest schema (fill fields according to what actually exists in this run; mark missing fields `null` or omit them — **do not fabricate**):

```json
{
  "run_id": "<timestamp>_<scene>",
  "generated_from": ["report.md", "diagnosis.json", "..."],
  "_meta": {
    "protocol_ack": {"narrative_arch": true, "data_driven_protocol": true, "fallbacks": true}
  },
  "conclusion": {
    "type": "DETERMINED | COMPETING_SET | NEEDS_DATA",
    "primary_finding": "one-sentence main conclusion (carry the keywords so the Hero display can wrap them in em)",
    "plain_language": "3-4 sentences of plain-language explanation (no statistical jargon; a non-algorithm user can retell it)",
    "judge_score": 94,
    "confidence_ceiling": 55,
    "confidence_ceiling_reason": "why this ceiling (sample size / temporal granularity / unverified steps)"
  },
  "scope": {
    "line": "production line name",
    "product": "focus product",
    "defect": "target defect",
    "sample_size": 19,
    "anomaly_stage": "anomalous section",
    "anomaly_locations": ["specific equipment / roll position / zone"]
  },
  "hypotheses": [
    {
      "id": "H6",
      "name": "hypothesis name",
      "status": "surviving | weakened | excluded",
      "confidence": 45,
      "stats": {"metric": "...", "spearman_rho": 0.554, "p_value": 0.014, "decay_rate": "15.2%", "raw_correlation": "+0.58"},
      "exclusion_reason": "why it was excluded/weakened (null when surviving)",
      "physics_chain": ["causal step string or {title, detail, equation} object (matching the original diagnosis.json structure)"]
    }
  ],
  "evidence_layers": {
    "statistical": {
      "available": true,
      "strongest_signal": {"metric": "...", "rho": 0.554, "p": 0.014, "n": 19, "decay": "15.2%"},
      "score": 85,
      "pngs": ["03_figures/fig_xxx.png"],
      "echarts_rebuilds": [{"id": "chartN", "type": "detrend_scatter", "data_ref": "viz_compact.json#field"}]
    },
    "physics": {
      "available": true,
      "chain_steps": [{"title": "...", "detail": "...", "equation": "..."}],
      "score": 80,
      "pngs": ["03_figures/fig_profile.png"],
      "spatial_consistency": "note on the spatial consistency between the anomaly location and the physical mechanism"
    },
    "exclusion": {
      "available": true,
      "excluded_or_weakened": ["H1", "H2"],
      "synthesis_matrix": true
    }
  },
  "charts": [
    {"id": "chart1", "type": "detrend_compare | profile | radar | robustness | scatter | ...", "title": "...", "data_source": "viz_compact.json / diagnosis.json", "reading": ["看到什么", "说明什么", "为什么重要"]}
  ],
  "process_flow": {
    "recoverable": true,
    "stages": [{"name": "section name", "equipment_range": "rolls 1-5", "zone_color": "#8ca8c0"}],
    "equipment_count": 18,
    "anomaly_indices": [13, 15],
    "data_source_files": ["ontology.json", "3d_model_data.json"]
  },
  "available_pngs": [
    {"path": "03_figures/fig_xxx.png", "purpose": "what the figure is for", "suggested_layer": "statistical | physics | exclusion"}
  ],
  "actions": [
    {"priority": "P0 | P1 | P2", "action": "...", "expected": "expected effect"}
  ],
  "limitations": "limitations text (including the reason for the ceiling)",
  "fallbacks_triggered": ["Fallback 4: PNG 重建", "..."]
}
```

**manifest modeling iron rules:**
- All three `_meta.protocol_ack` entries must be true (proof that the builder passed the protocol gate in Step 1; any false → equivalent to not having read the protocol, and the reviewer returns fail)
- `hypotheses[]` count = the real hypothesis count of this run (maybe 2, maybe 6), not a fixed 4
- `charts[]` count = the real number of presentable signals (maybe 1, maybe 6), not a fixed 5
- `evidence_layers.*.available` reflects the truth: if a layer's evidence is missing, mark it `false`, and the page renders the matching `.evidence-missing` marker
- `conclusion.type` drives the Hero tone: `DETERMINED` asserts a root cause; `COMPETING_SET` explicitly presents the uncertainty + ceiling; `NEEDS_DATA` states that the conclusion has not yet converged
- `process_flow.recoverable=false` → do not render 3D; take Fallback 7/8

### Phase 3 · Render (component assembly + visual grammar)

**Visual grammar baseline: `references/report-template.html`.** It is not a fill-in-the-blank template but a **design system reference** — it provides the CSS variables, typographic hierarchy, every component class, the loader wiring, and the ECharts/Three.js multi-source loading pattern.

Read that file, understand the CSS variable system, the component-class contract, and the loader wiring, then assemble the page according to the manifest:

1. **Reuse directly (carry over verbatim)**: the whole `<style>` block, the loader-strip DOM, the ECharts/Three.js loading infrastructure, the importmap, the @media breakpoints
2. **Select components per the manifest**:
   - Hero always present → fill its 8 elements from `conclusion` + `scope`
   - 3D only when `process_flow.recoverable=true` → build the scene from `process_flow`
   - Render one chart per entry in `charts[]` (each `.chart-panel` + a three-line `.chart-reading`)
   - Render evidence layers per `evidence_layers.*.available` (missing layers get `.evidence-missing`)
   - Render one evidence article per entry in `hypotheses[]` (each `.evidence-article`)
3. **Apply the visual grammar**: take every style class name from the design system reference; inventing new colors or components is forbidden
4. **Bind real data**: every value / piece of copy / path comes from the manifest (whose source is the real run_dir JSON); fabrication is forbidden

**Forbidden**: hardcoding the equipment count (e.g. "18 rolls"), hardcoding the hypothesis count, hardcoding the chart count, or carrying residual BOPET data into a new run.

## Pre-flight Questions

Before writing the manifest, write down your internal answers to the following questions:

**Before 3D modeling:**
1. Which production line, which process, which defect is the current diagnostic object
2. What the real section order is
3. How material flows from upstream to downstream
4. Which section, which equipment, which roll position or zone the anomaly location corresponds to

**Before page planning:**
1. What the user should see within 10 seconds (the main conclusion in one sentence)
2. What the user should understand within 1 minute (location + strongest evidence)
3. Which evidence most deserves the main content area (ordered by `hypotheses[]` and `available_pngs[]`)
4. Which information should be deferred so that it does not interfere with comprehension

If you cannot answer clearly, do not enter the rendering phase.

## Hard Requirements

### 1. Page structure = an honest mapping of the manifest (v3)

The page's section count, card count, chart count, and evidence-layer count must match `render_manifest.json`. If the manifest says there are 3 hypotheses, the page carries 3 evidence articles; if the manifest says the statistical layer is `available:false`, the page puts `.evidence-missing` in that layer. **A page structure that disagrees with the manifest is not allowed.**

### 2. Visual grammar is inherited from the design system reference

`references/report-template.html` is the only style baseline. Keep its CSS variables, typography, component classes, loader, and @media. Adding new color tokens, deleting the loader, and disturbing the four-part order are forbidden.

### 3. Four-part narrative (retained from v2)

The page must strictly contain: **0. Hero — conclusion first / 1. Background and production-line modeling / 2. Diagnostic reasoning process / 3. Evidence chain three-layer architecture**. See `templates/page_blueprint.md` for details.

### 4. Every main conclusion dual-supported + plain-language version + real figures in the evidence chain

Every main conclusion must contain: (a) visual evidence (a real PNG or an ECharts chart); (b) reasoning evidence (statistics / physics / exclusion); (c) one plain-language sentence free of statistical jargon. Missing evidence must be explicitly marked, never pretended to exist.

**Embedding a figure in each of the three evidence-chain layers (statistics / physics / exclusion) is mandatory** (detailed in page_blueprint.md §3):
- Each evidence-chain layer **must embed at least one real PNG** (selected from `03_figures/` by `plot_manifest.json.suggested_layer`); ECharts cards or text alone may not be substituted for it. Statistical layer → `fig_vlm_simpson_*.png` / `fig_vlm_synchronization.png`; physical layer → `fig_vlm_temporal_overlay_*` / `fig_vlm_event_response.png`; exclusion layer → `fig_causal_map.png`.
- Every embedded PNG is a "figure + data + reading" trio: annotate beside the figure the **real statistic or physical quantity + the source file** (r/ρ/p/n from `feature_summary.json`, equations/orders of magnitude from `physics_check.json`, Simpson/detrending results from `validate_report.json`), together with a three-line plain-language reading.
- **Forbidden**: embedding a figure without labeling its data, labeling data without naming its source, or substituting vague phrases such as "significantly correlated" for a concrete r value. A conclusion with no matching figure or traceable value → mark `.evidence-missing`; never fabricate. Violating any one of these makes `html-reviewer` return fail.

### 5. Single-file priority

Inline the CSS/JS, embed the data, and use relative paths + graceful `onerror` degradation for local images.

### 6. Script loading resilience

ECharts/Three.js must use multi-source loading (primary CDN + backup CDN) + load-success detection + init-success detection + a 5-item loader status strip + static degradation when neither library loads. Reuse the loading infrastructure directly from the design system reference.

### 7. The 3D scene stays faithful to the process

3D is not "drawing a good-looking industrial scene" but "drawing a truthful simplified scene that matches the operating logic of this diagnosis". Section order / temperature zones / anomaly placement must come from `process_flow` (sourced from ontology + 3d_model_data); geometry may be simplified, but the process logic must not be wrong.

### 8. User comprehension is a hard metric

Know the conclusion / location / action within 10 seconds; know the strongest evidence and the exclusion logic within 1 minute; know how the conclusion was reached within 2 minutes.

## Evidence Architecture (three closed layers, not a flat pile)

The evidence chain has three layers, not a wall of cards:

```
Layer 1 · Statistical evidence (Ⅰ)        proves "correlation"
├── real PNG scatter/correlation plots (already in 03_figures)
├── ECharts rebuilds (rendered per charts[], count follows the data)
├── statistical evidence strength score bar
└── evidence article: the strongest surviving signal + complete statistics

Layer 2 · Physical mechanism (Ⅱ)           proves "causation"
├── HTML/CSS physical causal chain (rendered per physics.chain_steps)
├── real PNG profile plots
├── per-step physical equation / order-of-magnitude estimate
├── spatial consistency note
└── physical evidence strength score bar

Layer 3 · Exclusion logic (Ⅲ)              proves "uniqueness"
├── real PNG causal evidence map
├── per-hypothesis evidence articles (per hypotheses[] count, each with its exclusion reason)
├── comprehensive verdict matrix table
├── action-recommendation priority table (per actions[])
└── limitations note
```

**Each layer must have at least two of the three: real figure / data / reasoning; a missing layer → honest `.evidence-missing` marker.**

## Evidence Selection Rules

Main-conclusion ranking priority:

1. Executive summary and main conclusion in `report.md`
2. surviving hypotheses / primary finding in `diagnosis.json`
3. rank 3-5 values and physical support in `evidence.json`
4. explicable convergence path in `reasoning_chain.json`

When different files do not phrase things identically: follow the final conclusion of `diagnosis.json` + `report.md`, and keep one consistent wording across the page.

## Image Integration Rules (v2)

For the PNGs under `03_figures/`:

1. **Reuse first** — these are the original visual evidence produced by the diagnostic pipeline, not decoration
2. **Look up each chart's purpose with `plot_manifest.json`** and match it to the correct evidence layer (scatter → statistics / profile → physics / causal → exclusion)
3. **Use relative paths for `img src`** (from the output HTML to the run_dir `03_figures/`)
4. **Give every `img` an `onerror`** for graceful degradation (`onerror="this.parentElement.style.display='none'"`)
5. **Give every figure a caption below it**: figure number + content + diagnostic meaning

Record the matching in `manifest.available_pngs[].suggested_layer`.

## Visual Quality Bar

Do not produce: a generic admin dashboard / a hastily stitched-together dashboard / cards with no reasoning / charts with no explanation / an evidence chain with no real figures.

Do produce: minimal white background + serif headings with sans-serif body / high content density but low reading strain / a top-to-bottom build of "conclusion → location → reasoning → evidence" / three evidence-chain layers unfolded independently, each with its own visual identity.

## Output Checklist

Confirm item by item before finishing the HTML:

- [ ] `render_manifest.json` produced and its fields come from real JSON (nothing fabricated)
- [ ] Page section/card/chart/evidence-layer counts match the manifest
- [ ] All four parts present (Hero / background / reasoning / three-layer evidence chain)
- [ ] The three evidence-chain layers rendered truthfully per `evidence_layers.*.available`, with `.evidence-missing` for missing layers
- [ ] Evidence article count = `hypotheses[]` count (not a fixed value)
- [ ] Chart count = `charts[]` count (not a fixed 5)
- [ ] 3D only when `process_flow.recoverable`, otherwise degrade; 3D section order / anomaly placement come from real data
- [ ] Visual grammar comes from the design system reference (no invented tokens/components)
- [ ] 5-item loader status strip + ECharts/Three.js multi-source + failure degradation
- [ ] Every main conclusion dual-evidenced + a plain-language version (**Grandmother Test**: the first occurrence of every statistical/physical term is immediately followed by a jargon-free plain-language sentence, e.g. "Spearman ρ=0.55 (the two parameters rise and fall together, moderate strength)")
- [ ] Every chart carries a three-line reading (**figure + data + reading trio**: data labels with the real r/ρ/p/magnitude + source file; vague wording such as "significantly correlated" is banned)
- [ ] **Every key finding is followed by a "so what?" business impact** (translated into yield / downtime / cost / quality risk — numbers without business meaning = unfinished)
- [ ] **The four-part narrative has transition sentences** (Hero→background→reasoning→evidence chain→action; each part ends with a sentence that leads into the next part's core question, forming a causal chain rather than scattered cards)
- [ ] All values/paths come from real run_dir artifacts
- [ ] The 10-second / 1-minute / 2-minute comprehension thresholds are met
- [ ] Action recommendations + limitations complete
- [ ] `render_manifest.json` contains `_meta.protocol_ack` with all three true
- [ ] Output to `<run_dir>/diagnostic-report.html`
- [ ] Output `<run_dir>/html_selfcheck.json` (8 PASS/FAIL items + evidence, the Step 5 CHECKPOINT 4 artifact)
