> Moved verbatim from `SKILL.md` §Visual Standards. Read in full before Step 4 (page assembly).

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
