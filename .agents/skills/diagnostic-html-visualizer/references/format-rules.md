# Format Rules — shared by the whole HTML skill family

> **Single canonical copy.** Builder skills (`industrial-html-visualizer`, `industrial-enhanced-html-visualizer`) and
> reviewer skills (`industrial-html-reviewer`, `industrial-enhanced-html-reviewer`) point here instead of restating
> these tables. The visual grammar itself (colors, typography, components, styles-to-avoid) lives only in the
> authority's `visual-standards.md` §Visual Standards + `style-grammar.md` §Style Direction & Visual Grammar — do not copy it into a wrapper.

## 1. Language Default

Default output language is **Chinese**. Page copy, chart captions, evidence-chain explanations, and action
recommendations are written in Chinese. Structured field names, code variable names, and JSON enum values remain
in English.

## 2. Data Truth Mandate

**Every number written into JSON/reports must be recomputable from the raw data.**

| Rule | Requirement |
|------|-------------|
| Number traceability | Every number must state the data source (cleaned/raw), row range, and computation method |
| Derived value marking | Inferred/derived values must be explicitly `"derived": true` or `"inferred": true` |
| Cleaning audit trail | cleaning_integrity records all cleaning operations |
| Visualization traceability | Every data point in every chart is traceable to a specific row of the dataset |
| Unavailable marking | What cannot be computed from the data → write NOT_APPLICABLE + reason |
| No cross-run contamination | Every number/equipment/hypothesis on the page must be explainable by THIS run's data (authority red line 15) |

## 3. Counterfactual Reasoning — Exclusion Constraints

| Constraint | Description |
|------|------|
| Four conditions | Temporal precedence + statistical significance + physical mechanism + no contradiction |
| Exclusion standard | Any condition unmet → mark as an excluded candidate and provide quantitative grounds |
| Physical boundary | Exclusions must be supported by first principles or governing equations |
| Confidence threshold | Exclusion confidence <80 is marked `[WEAK_EXCLUSION]` |

## 4. Runtime Readiness (mandatory for every built page)

- ECharts / Three.js / OrbitControls use multi-source loading (primary CDN → backup CDN → failure report) plus
  init-success detection; silently failing pages are not deliverables.
- The page renders a loader status strip (5 indicators): ECharts / Three.js / OrbitControls / charts initialized /
  3D scene initialized — each `loaded | fallback | failed` (or `optional-missing`).
- CDN failure → static degraded content + visible degraded-mode notice; no blank page, no fake success.
- Every chart carries a `.chart-reading` three-line reading: what is seen / what it means / why it matters.

## 5. Artifact Minimums

| Artifact | Minimum | Checked by |
|----------|---------|-----------|
| `<run_dir>/diagnostic-report.html` | ≥ 5120 bytes, real `<title>`, parses as HTML | `industrial-html-visualizer/scripts/quality_gate.mjs` |
| `<run_dir>/enhancement/enhanced-analysis.html` | ≥ 5120 bytes, real `<title>`, parses as HTML | `industrial-enhanced-html-visualizer/scripts/quality_gate.mjs` |
| `<run_dir>/enhancement/html_selfcheck.json` | builder marker (`enhanced_html_builder`, `charts_built: 5`) | `industrial-enhanced-html-visualizer/scripts/quality_gate.mjs` |
| `<run_dir>/05_review/html_review.json` | parses + required fields (see `review-checklist.md` §7) | `industrial-html-reviewer/scripts/quality_gate.mjs` |
| `<run_dir>/enhancement/enhancement_html_review.json` | produced by `html_reviewer.py`, verdict mapped | `industrial-enhanced-html-reviewer/scripts/quality_gate.mjs` |
