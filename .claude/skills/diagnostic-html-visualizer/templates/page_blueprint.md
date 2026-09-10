# Page Blueprint v2

This template prescribes the page structure, not the specific copy.

## Page Architecture

The page uses a **four-part narrative**, each part answering one core question:

1. Hero — conclusion first: "What is the conclusion?"
2. Background and location — spatial localization: "Where on the production line did the problem occur?"
3. Diagnostic reasoning — method explanation: "How was this conclusion reached?"
4. Evidence chain — three-layer closed evidence loop: "Why believe this conclusion? What do we do next?"

### Narrative design principles (binding — they decide whether the page is "compelling and comprehensible")

**A. Story spine + paragraph transitions (coherence)**: the four parts are not independent cards but one causal chain. **Each part must close with a one-sentence transition** that leads the reader naturally into the next part's core question:
- End of Hero → "We have the conclusion, but where on the production line did the anomaly actually occur?" → leads into the background
- End of background → "The location is pinned down, but on what grounds?" → leads into the diagnostic reasoning
- End of reasoning → "The reasoning chain holds, but is the evidence hard enough? Why not another cause?" → leads into the evidence chain
- End of evidence chain → "The evidence loop is closed, so what should the shop floor do next?" → action recommendations

**B. Grandmother Test (plain language mandatory)**: at the first occurrence of every statistical/physical term, **immediately follow it with a jargon-free plain-language sentence**. E.g. "Spearman ρ=0.55" → "(these two parameters rise and fall together, of moderate strength)". A term without its plain-language gloss = the reviewer returns fail.

**C. So what? (business impact mandatory)**: every key finding must be followed by a sentence about "what this means for production" — translating the data into business language (yield / downtime / cost / quality risk). Numbers with no business meaning = unfinished.

**D. Use question sentences for section headings**: "Where on the production line did the problem occur?" rather than "Background and modeling". Each block answers only one core question.

**E. Top-down information hierarchy**: conclusion → location → method → evidence. No section may move a detailed conclusion ahead of the Hero.

**F. Real data is the only source (zero fabrication)**: every value, parameter name, equipment name, and hypothesis on the page must come from the real JSON in `run_dir` (ontology / diagnosis / feature_summary / visual_analysis / physics_check, etc.), routed through `render_manifest.json`. **Forbidden**: inventing numbers, using "representative" example values, or carrying residue from a previous run into this one. A conclusion without data support → mark `.evidence-missing`; do not pretend it exists.

## Recommended File Output

- Default: `<run_dir>/diagnostic-report.html`

## Runtime Readiness Banner

A lightweight status strip fixed at the top of the page, showing:

- ECharts load status
- Three.js load status
- OrbitControls load status
- Chart initialization status
- 3D scene initialization status

On failure, keep the static text, summary cards, and local images, and explicitly label the degraded mode.

## Page Outline

### 0. Hero / Executive Snapshot

The first screen answers "what is the conclusion" within 10 seconds:

- Industrial diagnostic report eyebrow label
- The main conclusion in one sentence (serif display, with a gradient emphasizing the key phrases)
- A 3-4 sentence plain-language explanation of the main conclusion (readable by non-technical users)
- Key metadata tag row: diagnosis type / Judge score / confidence ceiling / focus product / sample size / anomalous section
- Four-cell key-findings grid (1px split border frame):
  1. Strongest evidence (statistic + a summary of the physical chain)
  2. Excluded factors (the exclusions + the grounds for excluding them)
  3. Recommended action (P0/P1 priority)
  4. Evidence gap (the key evidence currently missing)
- A one-sentence "reading guide" explaining the page's top-to-bottom reading order

### 1. Background and production-line modeling

Goal: the user knows "where on the production line the problem occurred" within 30 seconds.

Must contain:

- A concise scenario description: production line, product, target defect, sample structure
- 3D production-line model:
  - Recover the real section order from ontology.json
  - Drive visual differences from real data (temperature / torque / standard deviation)
  - Anomaly locations highlighted in red + numbered labels
  - Three-zone color coding (preheat / stretch / quench)
  - Material flow shown as a blue pipe
  - Legend: normal / anomaly / flow direction
- Annotate the data source files below the 3D container
- **Data governance card (audit trail, must be present)**: generate a compact disclosure card from `data_analysis_conclusion.json.data_cleaning_provenance` so the user can see at a glance "which clean dataset the conclusion is based on":
  - **Data-source badge**: `cleaned` (green) or `raw_fallback` (orange, with the reason) — the unified data source for every chart on the page
  - **Cleaning-operation table** (collapsible / compact): one row per operation → target → rows affected → rationale (dedupe / sort / type repair / missing / outlier / derived)
  - **Integrity reconciliation**: raw row count vs cleaned row count, discard rate; the columns with type repairs and examples of stray tokens (e.g. `<0.05` / `N/A`)
  - Design it to match the existing "state the facts, data-driven" tone — it is transparent disclosure, not decoration; place it in the background section so readers build data trust before reading the conclusion

### 2. Diagnostic reasoning process

Goal: the user understands within 1 minute that "the conclusion was not obvious at a glance".

Must contain:

- Key statistics table (before/after detrending comparison: ρ / p value / decay rate / verdict)
- 3-5 ECharts charts, ordered from most critical to next most critical:
  1. Before/after detrending comparison (split left/right)
  2. Per-zone parameter profile plot (annotating the anomaly locations)
  3. Hypothesis-evidence radar chart
  4. Correlation robustness comparison
  5. Detrended scatter plot (annotating the key data points)
- A three-line reading for every chart: what is seen / what it means / why it matters
- Plain-language explanation of the key methods (detrending, stratified analysis, competing hypotheses)
- Reuse existing PNG screenshots (Simpson's paradox visualizations, etc.)

### 3. Evidence chain (three-layer architecture)

Goal: the user understands within 2 minutes "why this conclusion should be believed" and "why it is not another cause".

**This is the page's core persuasion block; it must contain real production-line diagnostic images, data analysis, and physical-logic reasoning.**

#### Figure-embedding iron rules (common to all three layers)

Every embedded PNG must be the **"figure + data + reading" trio**; missing any one of the three makes the reviewer return fail:

1. **Figure**: embed the real PNG from `03_figures/` (`<img src>` with a relative path), matched to the correct evidence layer via the `suggested_layer` field of `plot_manifest.json`; substituting a placeholder image or ECharts for a real PNG that should exist is **forbidden**
2. **Data**: beside or below the figure, annotate the **real statistic or physical quantity** (r / Spearman ρ / p / n / ΔT / order-of-magnitude estimate), with every number labeled with its source file (`feature_summary.json` / `validate_report.json` / `physics_check.json` / `diagnosis.json`)
3. **Reading**: three lines of plain language — "what the chart shows → what the statistics/physics say → how it supports or contradicts the conclusion"

**Forbidden**: embedding a figure without labeling its data / labeling data without naming its source / a figure with no reading / substituting vague wording such as "significantly correlated" for a concrete r value. If a statistical or physical conclusion has no matching figure or concretely traced value, it must be explicitly marked `.evidence-missing`; do not pretend it exists.

#### figure → evidence-layer mapping (data-driven; read from `suggested_layer` in plot_manifest.json)

| Evidence layer | Real PNG that should be embedded (plot_manifest role) | Data source (must be labeled beside the figure) |
|--------|--------------------------------------|---------------------|
| **Statistical evidence** | `fig_vlm_simpson_*.png` (stratified correlation direction), `fig_vlm_synchronization.png` (rolling-correlation stability), scatter / correlation-robustness plots | `feature_summary.json` (r / ρ / p / n), `validate_report.json` (Simpson / outlier / trend-confound detection results) |
| **Physical mechanism** | `fig_vlm_temporal_overlay_focus_*.png` / `fig_vlm_temporal_overlay_prod_*.png` (parameter → quality temporal alignment), `fig_vlm_event_response.png` (event response) | `diagnosis.json` (physical_logic_chain), `physics_check.json` (equations + orders of magnitude), `time_lag_analysis.json` (time lag) |
| **Exclusion logic** | `fig_causal_map.png` (causal evidence map: surviving edges vs excluded edges) | `causal_evidence_map.json`, `evidence.json` (evidence grade), `diagnosis.json` (falsification_conditions) |

#### Layer 1 · Statistical evidence

- Embed `fig_vlm_simpson_*.png`: annotate below the figure "Spearman ρ=X.XX, p<X.XX, n=X (source: feature_summary.json); detrended r=X.XX; Simpson detection: not reversed / reversed (source: validate_report.json)"
- Embed `fig_vlm_synchronization.png`: annotate "rolling-correlation stability, |r|>0.5 in X% of the time window"
- At least 1 ECharts rebuilt analysis chart (detrended scatter / correlation-robustness comparison, raw r vs detrended r)
- Statistical evidence strength score bar
- Evidence article: state explicitly which parameter is the **strongest surviving signal after detrending**, with the complete statistics + source files

#### Layer 2 · Physical mechanism

- Embed `fig_vlm_temporal_overlay_focus_<focus product>.png`: annotate "parameter X and quality Y share a time axis, time lag ≈ N minutes (source: time_lag_analysis.json) — the parameter changes first and the quality follows, satisfying causal temporal precedence"
- Embed `fig_vlm_event_response.png`: annotate whether the quality recovers after the event, and by how much
- Physical causal-chain visualization (HTML/CSS step chain, each step from `diagnosis.json.physical_logic_chain`)
- Each step carries a **real physical equation or order-of-magnitude estimate** (source: `physics_check.json`, e.g. Arrhenius `k = A·exp(-Ea/RT)`, ΔT=7°C → crystallization rate ↑~23%)
- Explain the spatial consistency between the anomaly location and the physical mechanism
- Physical evidence strength score bar

#### Layer 3 · Exclusion logic

- Embed `fig_causal_map.png`: annotate surviving edges (green) and excluded edges (red/gray), labeling each edge with its r value
- Per-hypothesis evidence articles (hypothesis count = the hypothesis count in `render_manifest.json`, **must not be hardcoded**), each containing:
  - Hypothesis name + exclusion/weakening confidence
  - **Raw evidence vs post-detrending truth** comparison (the specific change in r, source: `validate_report.json`)
  - Physical boundary test or internal contradiction (source: `physics_check.json` / `diagnosis.json`)
  - A "why it was excluded" explanation block with a blue left border

#### Evidence-chain comprehensive verdict

- Comprehensive scoring matrix table (statistics / physics / exclusion logic / overall confidence)
- 3-5 action recommendations (P0/P1/P2 priority table)
- Limitations note (sample size, data granularity, unverified steps)

## Tone

- Professional but accessible — every statistical term is followed immediately by a plain-language sentence
- State the facts, no dramatization — data-driven, physically supported
- After reading, the user should be able to retell "what the conclusion is, why, and what to do next"
- The three evidence-chain layers unfold independently, letting the user build confidence layer by layer

## Acceptance Lens (binding — every reading pace must be able to answer its corresponding question)

The page must be designed in layers that follow the human reading pace — whenever the user leaves, they should walk away with the understanding of that tier:

1. **10 seconds (Hero)**: What is the conclusion? Diagnosis type + the root cause in one sentence + confidence. The Hero must be readable on its own, not dependent on what follows.
2. **30 seconds (+ background)**: Where is the problem? Which section/equipment on the line is anomalous (3D highlight + the data governance card has already disclosed the data source).
3. **1 minute (+ reasoning)**: What is the strongest evidence? Which reasoning chain supports the conclusion (parameter → physical mechanism → quality).
4. **2 minutes (+ evidence chain)**: Why is it not another cause? Three layers of evidence + why the competing hypotheses were excluded.
5. **2 minutes (+ action)**: What happens next? P0/P1/P2 actions + falsification conditions.

If any pace cannot answer its corresponding question → rewrite that part. This is `html-reviewer`'s core criterion.
