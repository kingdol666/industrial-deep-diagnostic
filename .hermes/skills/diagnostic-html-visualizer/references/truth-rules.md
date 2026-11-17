# Truth Rules — the 6 Iron Rules (moved verbatim from SKILL.md)

> The builder agent must read this file in full before Step 3 (manifest modeling) and Step 4 (page assembly).

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