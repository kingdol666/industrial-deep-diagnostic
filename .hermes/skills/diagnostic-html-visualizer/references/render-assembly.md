# Render Assembly — Steps 3-5 detail (moved verbatim from SKILL.md)

> The slim `SKILL.md` §Execution Flow keeps the six steps and CHECKPOINTs 1-5; this file carries the
> step bodies (manifest field checklist, component assembly/reuse table, conclusion-type branching,
> pre-render checklist, validation checks).

## Step 3 detail — render_manifest field checklist

- Conclusion type (DETERMINED / COMPETING_SET / NEEDS_DATA) + main conclusion + confidence ceiling
- `hypotheses[]` real hypothesis list (count follows the data, not fixed)
- `evidence_layers` real `available` status of each of the three layers (missing layers marked false)
- `charts[]` real presentable signal list (count follows the data, not fixed at 5)
- `process_flow` (sections / equipment count / anomaly placement, only when recoverable)
- `available_pngs[]` with the `suggested_layer` of each PNG

---

## Step 4 detail — assemble the page from the manifest

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

---

## Step 5 detail — validation checks

Check at minimum:

- Whether the HTML opens
- Whether ECharts / Three.js / OrbitControls each have a primary source + backup source + success detection
- Whether at least one chart really initialized (`echarts.getInstanceByDom`)
- Whether at least one Three.js scene really rendered (canvas element exists)
- Whether local image paths are accessible relative to the output file
- **Whether the evidence chain is complete in all three layers, each supported by real images/data/reasoning**
- Whether main conclusion, key evidence, exclusion logic, action recommendations, and limitations are all present
- Whether the user can understand "why this conclusion was reached" without statistical jargon
