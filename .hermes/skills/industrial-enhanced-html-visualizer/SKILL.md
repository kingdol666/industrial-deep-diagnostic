---
name: industrial-enhanced-html-visualizer
description: >
  Enhanced HTML Visualizer — generates interactive ECharts visualization page
  from enhanced_knowledge.json. Produces enhanced-analysis.html with 5 chart types
  (network graph, heatmap, radar, operability matrix, physics verification),
  CDN multi-source loading (jsdelivr + unpkg + cdnjs) with runtime fallback,
  hero section, data governance card, and runtime self-check.
  Trigger: enhanced html, enhanced visualization, enhanced HTML,
  enhanced-analysis.html, enhanced html builder.
  Use after industrial-analysis-enhance-auto or when enhanced_knowledge.json is available.
---
# Industrial Enhanced HTML Visualizer

Converts `enhanced_knowledge.json` into an interactive ECharts visualization HTML page.

## Inputs

| Required | Path | Description |
|----------|------|-------------|
| P0 | `RUN_DIR/enhancement/enhanced_knowledge.json` | Enhanced knowledge fusion output |

## Outputs

| File | Description |
|------|-------------|
| `RUN_DIR/enhancement/enhanced-analysis.html` | Standalone HTML visualization page |
| `RUN_DIR/enhancement/html_selfcheck.json` | Build-time self-check artifact |

## Usage

```bash
uv run --project "$SHARED_PATH/scripts" python .claude/skills/industrial-enhanced-html-visualizer/scripts/html_builder.py \
  --knowledge <RUN_DIR>/enhancement/enhanced_knowledge.json \
  --output <RUN_DIR>/enhancement/enhanced-analysis.html
```

## Chart Types

1. **Parameter Relationship Network Graph** — parameter relationship network (nodes = parameters, edges = relationships, colored by operability)
2. **Conditional Dependency Heatmap** — conditional dependency heatmap (global_r vs detrended_r vs lag_aligned_r)
3. **Multi-target Tradeoff Radar** — multi-target tradeoff radar chart
4. **Operability Matrix** — operability matrix (parameter × target effect strength + confidence)
5. **Physics Verification Traffic Light** — physics verification status card (5 dimensions: direction/form/time-lag/magnitude/state dependence)

## CDN Multi-Source

ECharts is loaded from three CDN sources in order; if any one is available, interactive charts render; if all fail, the page degrades to static table mode:

1. `https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js`
2. `https://unpkg.com/echarts@5/dist/echarts.min.js`
3. `https://cdnjs.cloudflare.com/ajax/libs/echarts/5.5.0/echarts.min.js`

## Runtime Self-Check

The page embeds a runtime self-check script that detects and reports:
- `echarts_available`: whether a CDN loaded successfully
- `charts_rendered`: number of charts rendered successfully
- `degraded_mode`: whether the page degraded to static mode
- `chart_statuses`: render status of each chart

## Verification

```bash
# Build
uv run --project "$SHARED_PATH/scripts" python .claude/skills/industrial-enhanced-html-visualizer/scripts/html_builder.py \
  --knowledge <enhanced_knowledge.json> --output <enhanced-analysis.html>

# Verify selfcheck
uv run --project "$SHARED_PATH/scripts" python -c "import json; sc=json.load(open('<DIR>/html_selfcheck.json')); \
  assert sc['size_requirement_met']; assert sc['charts_built']==5; \
  print('OK:', sc['html_size_bytes'], 'bytes')"

# Run reviewer
uv run --project "$SHARED_PATH/scripts" python .claude/skills/industrial-enhanced-html-reviewer/scripts/html_reviewer.py \
  --knowledge <enhanced_knowledge.json> \
  --html <enhanced-analysis.html> \
  --output <DIR>/enhancement_html_review.json
```

## References

- `references/agent-protocol.md` — Builder agent execution protocol