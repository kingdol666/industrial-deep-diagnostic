# Family Routing — which HTML skill for which job

> The five HTML skills are one protocol in five modes. Before dispatching, pick the row that matches the
> artifact at hand; the frontmatter `Do NOT use for ...` clauses of each skill encode the same routing.

## Mode matrix

| Skill | Mode | Required input | Output | Gate |
|-------|------|----------------|--------|------|
| `diagnostic-html-visualizer` | protocol **authority** (design system + iron rules + red lines + fallbacks) | a diagnostic run dir | (defines the protocol; also buildable standalone) | — |
| `industrial-html-visualizer` | pipeline **Step 8 build** (plain page) | run dir with CP-8 ENDORSED `optimizer.md` | `<run>/diagnostic-report.html`, `render_manifest.json`, `html_selfcheck.json` | `industrial-html-visualizer/scripts/quality_gate.mjs` |
| `industrial-html-reviewer` | pipeline **Step 8.5 review** (plain page) | the built page + manifest + selfcheck | `<run>/05_review/html_review.json` | `industrial-html-reviewer/scripts/quality_gate.mjs` |
| `industrial-enhanced-html-visualizer` | **E0–E8 enhancement build** | `<run>/enhancement/enhanced_knowledge.json` | `<run>/enhancement/enhanced-analysis.html`, `html_selfcheck.json` | `industrial-enhanced-html-visualizer/scripts/quality_gate.mjs` |
| `industrial-enhanced-html-reviewer` | **enhanced page review** | `enhanced_knowledge.json` + `enhanced-analysis.html` | `<run>/enhancement/enhancement_html_review.json` | `industrial-enhanced-html-reviewer/scripts/quality_gate.mjs` |

## Choosing plain vs enhanced

- `RUN_DIR/enhancement/enhanced_knowledge.json` exists (industrial-analysis-enhance-auto ran) → **enhanced** pair.
- Otherwise, a completed diagnostic run dir with `report.md` + `04_diagnostics/*` → **plain** pair.
- The two pairs are not interchangeable: the plain page is the four-part narrative built from run_dir JSONs with
  a manifest; the enhanced page is the 5-chart ECharts overview built from the fused knowledge graph.
- Both plain artifacts may legitimately coexist in one run dir (pipeline page + enhancement page).

## Negative boundaries (route elsewhere)

| Request | Route to |
|---------|----------|
| Plain statistics / chart work on raw data (no diagnosis) | `industrial-data-processor` |
| Root-cause analysis / diagnosis itself | `industrial-diagnostician` (or the `industrial-analysis-auto` pipeline) |
| Judge scoring / physical audit of the diagnosis text | `industrial-judge` / `industrial-physical-auditor` |
| Enhancement fusion itself (producing `enhanced_knowledge.json`) | `industrial-analysis-enhance-auto` |
| Building the page | visualizer skills only (reviewers never build) |
| Reviewing the page | reviewer skills only (builders never self-certify a review) |
