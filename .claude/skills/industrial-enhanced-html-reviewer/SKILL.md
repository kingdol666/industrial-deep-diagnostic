---
name: industrial-enhanced-html-reviewer
description: >
  Enhanced HTML Reviewer — reviews enhanced-analysis.html against
  enhanced_knowledge.json. Checks hero clarity, evidence completeness,
  logic chain, chart initialization, data governance card, and runtime
  fallback mechanisms. Outputs enhancement_html_review.json with
  verdict (pass/warn/fail) and overall_score (0-100).
  Trigger: enhanced html review, enhanced review, 增强审校,
  增强HTML审校, enhancement_html_review.
  Use after industrial-enhanced-html-visualizer generates enhanced-analysis.html.
---
# Industrial Enhanced HTML Reviewer

审核 `enhanced-analysis.html` 是否满足可视化质量标准。

## Inputs

| Required | Path | Description |
|----------|------|-------------|
| P0 | `RUN_DIR/enhancement/enhanced_knowledge.json` | 增强知识融合输出 |
| P0 | `RUN_DIR/enhancement/enhanced-analysis.html` | 待审校的 HTML 页面 |
| P1 | `RUN_DIR/enhancement/html_selfcheck.json` | 构建时自检（可选） |

## Outputs

`RUN_DIR/enhancement/enhancement_html_review.json`:

```json
{
  "verdict": "pass",
  "overall_score": 92,
  "blocking_issues": [],
  "warnings": ["Consider adding mechanism-chain drill-down"],
  "checks": [
    {"name": "hero_clarity", "status": "pass", "evidence": "..."},
    {"name": "evidence_layer_1_statistical", "status": "pass", "evidence": "..."},
    {"name": "evidence_layer_2_physics", "status": "pass", "evidence": "..."},
    {"name": "chart_initialization", "status": "pass", "evidence": "..."},
    {"name": "three_d_fidelity", "status": "pass", "evidence": "..."},
    {"name": "data_governance", "status": "pass", "evidence": "..."},
    {"name": "degraded_mode_fallback", "status": "pass", "evidence": "..."},
    {"name": "size_requirement", "status": "pass", "evidence": "..."},
    {"name": "data_fidelity", "status": "pass", "evidence": "..."}
  ]
}
```

## Review Dimensions

1. **Hero clarity** — 首屏是否有状态徽章、标题、关键发现、可操作性摘要
2. **Evidence completeness** — 5 种图表容器是否全部存在
3. **Chart initialization** — CDN 多源加载 (jsdelivr + unpkg + cdnjs) 是否配置完整
4. **Runtime self-check** — 页面是否包含 echarts_available / degraded_mode 自检逻辑
5. **Data governance** — 数据溯源卡片是否包含 SHA256，行数，来源 artifacts
6. **Degraded mode** — 静态表格降级是否就绪
7. **Size requirement** — HTML ≥ 5120 bytes
8. **Data fidelity** — HTML 内容是否引用 enhanced_knowledge.json 数据

## Decision Rule

- `pass`: score ≥ 75, no blocking issues
- `warn`: score ≥ 50 but < 75, or non-blocking warnings
- `fail`: blocking issues exist or score < 50

## Usage

```bash
uv run --project .claude/shared/scripts python .claude/skills/industrial-enhanced-html-reviewer/scripts/html_reviewer.py \
  --knowledge <enhanced_knowledge.json> \
  --html <enhanced-analysis.html> \
  --output <DIR>/enhancement_html_review.json
```

## References

- `references/agent-protocol.md` — Reviewer agent execution protocol
