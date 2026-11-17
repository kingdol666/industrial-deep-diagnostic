> Moved verbatim from `SKILL.md` §Fallback Rules. Consult when a Step 2/3/4/5 branch breaks; the CHECKPOINT lines in `SKILL.md` §Execution Flow name which fallback each branch takes.

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