---
name: industrial-enhanced-html-visualizer
description: >
  Enhanced HTML Visualizer — generates interactive ECharts visualization page
  from enhanced_knowledge.json. Produces enhanced-analysis.html with 5 chart types
  (network graph, heatmap, radar, operability matrix, physics verification),
  CDN multi-source loading (jsdelivr + unpkg + cdnjs) with runtime fallback,
  hero section, data governance card, and runtime self-check.
  Trigger: enhanced html, enhanced visualization, 增强可视化, 增强HTML,
  enhanced-analysis.html, enhanced html builder.
  Use after industrial-analysis-enhance-auto or when enhanced_knowledge.json is available.
---
# Industrial Enhanced HTML Visualizer

将 `enhanced_knowledge.json` 转成交互式 ECharts 可视化 HTML 页面。

## Inputs

| Required | Path | Description |
|----------|------|-------------|
| P0 | `RUN_DIR/enhancement/enhanced_knowledge.json` | 增强知识融合输出 |

## Outputs

| File | Description |
|------|-------------|
| `RUN_DIR/enhancement/enhanced-analysis.html` | 独立 HTML 可视化页面 |
| `RUN_DIR/enhancement/html_selfcheck.json` | 构建时自检产物 |

## Usage

```bash
python .claude/skills/industrial-enhanced-html-visualizer/scripts/html_builder.py \
  --knowledge <RUN_DIR>/enhancement/enhanced_knowledge.json \
  --output <RUN_DIR>/enhancement/enhanced-analysis.html
```

## Chart Types

1. **Parameter Relationship Network Graph** — 参数关系网络（节点=参数，边=关系，按可操作性着色）
2. **Conditional Dependency Heatmap** — 条件依赖热力图（global_r vs detrended_r vs lag_aligned_r）
3. **Multi-target Tradeoff Radar** — 多目标权衡雷达图
4. **Operability Matrix** — 可操作性矩阵（参数×目标效应强度+置信度）
5. **Physics Verification Traffic Light** — 物理验证状态卡（5维：方向/形式/时滞/量级/状态依赖）

## CDN Multi-Source

ECharts 从三个 CDN 源依次尝试加载，任一个可用即渲染交互式图表；全部不可用则降级为静态表格模式：

1. `https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js`
2. `https://unpkg.com/echarts@5/dist/echarts.min.js`
3. `https://cdnjs.cloudflare.com/ajax/libs/echarts/5.5.0/echarts.min.js`

## Runtime Self-Check

页面内嵌运行时自检脚本，检测并报告：
- `echarts_available`: CDN 是否加载成功
- `charts_rendered`: 成功渲染的图表数量
- `degraded_mode`: 是否降级为静态模式
- `chart_statuses`: 各图表的渲染状态

## Verification

```bash
# Build
python .claude/skills/industrial-enhanced-html-visualizer/scripts/html_builder.py \
  --knowledge <enhanced_knowledge.json> --output <enhanced-analysis.html>

# Verify selfcheck
python -c "import json; sc=json.load(open('<DIR>/html_selfcheck.json')); \
  assert sc['size_requirement_met']; assert sc['charts_built']==5; \
  print('OK:', sc['html_size_bytes'], 'bytes')"

# Run reviewer
python .claude/skills/industrial-enhanced-html-reviewer/scripts/html_reviewer.py \
  --knowledge <enhanced_knowledge.json> \
  --html <enhanced-analysis.html> \
  --output <DIR>/enhancement_html_review.json
```

## References

- `references/agent-protocol.md` — Builder agent execution protocol
