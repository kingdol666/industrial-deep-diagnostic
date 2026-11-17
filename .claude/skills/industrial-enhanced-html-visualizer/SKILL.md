---
name: industrial-enhanced-html-visualizer
description: >
  Enhanced HTML Visualizer — generates the interactive ECharts page (enhanced-analysis.html)
  from enhanced_knowledge.json. Produces 5 chart types (network graph, heatmap, radar,
  operability matrix, physics verification), CDN multi-source loading (jsdelivr + unpkg + cdnjs)
  with runtime fallback, hero section, data governance card, and a build-time self-check marker.
  Trigger: enhanced html, enhanced visualization, enhanced HTML,
  enhanced-analysis.html, enhanced html builder.
  Use after industrial-analysis-enhance-auto or when enhanced_knowledge.json is available —
  choose THIS skill only for the enhancement page; for the standard diagnostic-report.html use
  industrial-html-visualizer. Do NOT use for reviewing the page (→ industrial-enhanced-html-reviewer),
  plain statistics/chart work on raw data (→ industrial-data-processor), the enhancement fusion
  itself (→ industrial-analysis-enhance-auto), or root-cause analysis (→ industrial-diagnostician).
---

# Industrial Enhanced HTML Visualizer

Converts `enhanced_knowledge.json` (the E0–E8 enhancement fusion output) into a standalone interactive ECharts
HTML page. **Enhanced mode**: this page is not the four-part narrative report — it is the 5-chart knowledge-graph
overview. For the standard pipeline page see `family-routing.md` in the authority's references.

## Shared protocol & checklists (read these; do not restate)

- Mode-specific execution checklist (reading order, chart-data rules, fallback rules, colors):
  `references/agent-protocol.md`
- Mode matrix / when to choose enhanced vs plain: `.claude/skills/diagnostic-html-visualizer/references/family-routing.md`
- Shared format rules (language, Data Truth Mandate, artifact minimums): `.claude/skills/diagnostic-html-visualizer/references/format-rules.md`

## Inputs / Outputs

| Required | Path | Description |
|----------|------|-------------|
| P0 | `<RUN_DIR>/enhancement/enhanced_knowledge.json` | Enhanced knowledge fusion output (sole data source) |

| File | Description |
|------|-------------|
| `<RUN_DIR>/enhancement/enhanced-analysis.html` | Standalone HTML visualization page (≥ 5120 bytes) |
| `<RUN_DIR>/enhancement/html_selfcheck.json` | Build-time self-check marker written by the builder script |

## Usage

```bash
uv run --project "$SHARED_PATH/scripts" python .claude/skills/industrial-enhanced-html-visualizer/scripts/html_builder.py \
  --knowledge <RUN_DIR>/enhancement/enhanced_knowledge.json \
  --output <RUN_DIR>/enhancement/enhanced-analysis.html
```

The builder script is the single implementation (build-time only; do not hand-write the page). It writes both the
HTML and the `html_selfcheck.json` marker in one run.

## Chart Types (all 5 always emitted)

1. **Parameter Relationship Network Graph** — nodes = parameters, edges = relationships, colored by operability
2. **Conditional Dependency Heatmap** — global_r vs detrended_r vs lag_aligned_r
3. **Multi-target Tradeoff Radar** — one radar per parameter (max 6 displayed)
4. **Operability Matrix** — parameter × target effect strength + operability class
5. **Physics Verification Traffic Light** — 5 dimensions: direction / form / time-lag / magnitude / state dependence

## CDN Multi-Source + Runtime Self-Check

ECharts loads from three CDN sources in order; if all fail the page degrades to static tables:

1. `https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js`
2. `https://unpkg.com/echarts@5/dist/echarts.min.js`
3. `https://cdnjs.cloudflare.com/ajax/libs/echarts/5.5.0/echarts.min.js`

The page embeds a runtime self-check script reporting `echarts_available`, `charts_rendered`, `degraded_mode`,
`chart_statuses`; the build-time marker `html_selfcheck.json` records `builder`, `charts_built`,
`size_requirement_met`, `echarts_cdn_sources`, `fallback_mode`.

## Quality Gate

```bash
node .claude/skills/industrial-enhanced-html-visualizer/scripts/quality_gate.mjs --run-dir <RUN_DIR>
# exit 0 = enhancement/enhanced-analysis.html valid (title, structure, >= 5120B) AND
#          enhancement/html_selfcheck.json is a well-formed builder marker (charts_built=5,
#          size_requirement_met=true, 3 CDN sources listed)
# exit 2 = page or marker absent (the enhanced build has not run)  |  exit 3 = corrupt artifact
# exit 1 = hard error.  Tests: python .claude/skills/industrial-enhanced-html-visualizer/tests/run_tests.py
```

## Verification

```bash
# Build
uv run --project "$SHARED_PATH/scripts" python .claude/skills/industrial-enhanced-html-visualizer/scripts/html_builder.py \
  --knowledge <enhanced_knowledge.json> --output <enhanced-analysis.html>

# Gate (replaces the manual selfcheck assertions)
node .claude/skills/industrial-enhanced-html-visualizer/scripts/quality_gate.mjs --run-dir <RUN_DIR>

# Run reviewer (script-authored, deterministic)
uv run --project "$SHARED_PATH/scripts" python .claude/skills/industrial-enhanced-html-reviewer/scripts/html_reviewer.py \
  --knowledge <enhanced_knowledge.json> \
  --html <enhanced-analysis.html> \
  --output <DIR>/enhancement_html_review.json
```
