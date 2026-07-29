---
name: industrial-html-reviewer
description: "工业诊断管线 Step 8.5 — 诊断可视化页面审校。独立审核 HTML 可视化页面的可读性、证据完整性、逻辑链、3D 与图表覆盖。输出 html_review.json(pass/warn/fail)。Trigger: HTML审校, review HTML, HTML review, 页面审核, html reviewer, audit HTML。"
---

# Industrial HTML Reviewer

诊断可视化审校引擎。独立审核 `diagnostic-report.html` 是否能让非算法背景用户看懂结论、证据与排除逻辑。审核四大维度：可读性、证据完整性、逻辑链、3D 与图表覆盖。输出 `html_review.json` 含 pass/warn/fail 判定，不通过则触发 html-visualizer 回退修订（最多 3 次）。

## Inputs / Outputs

### Inputs (in `RUN_DIR`)

| File | Description |
|------|-------------|
| `diagnostic-report.html` | HTML 可视化页面（审核目标） |
| `report.md` | 最终诊断报告（结论参考） |
| `04_diagnostics/diagnosis.json` | 诊断结论 |
| `04_diagnostics/evidence.json` | 证据清单 |
| `04_diagnostics/reasoning_chain.json` | 推理链 |
| `01_ontology/ontology.json` | 领域本体 |
| `03_figures/plot_manifest.json` | 图表清单 |
| `03_figures/visual_analysis.json` | VLM 视觉分析 |
| `03_figures/image_captions.json` | 图像标注 |
| `3d_model_data.json` | 3D 模型数据 |
| `02_processed/data_analysis_conclusion.json` | 数据分析结论 |
| `02_processed/feature_summary.json` | 特征摘要 |
| `02_processed/validate_report.json` | 统计验证报告 |

### Outputs

| File | Description |
|------|-------------|
| `05_review/html_review.json` | verdict + overall_score + blocking_issues + warnings + checks |

## Dispatch

启动 `html-reviewer` 子Agent：

```javascript
// OMP dispatch via task tool:
task({
  agent: "html-reviewer",
  task: `RUN_DIR=<run-dir-path>
SKILL_PATH=.omp/skills/industrial-html-reviewer
SHARED_PATH=.omp/shared
OUTPUT_HTML=$RUN_DIR/diagnostic-report.html
AUDIENCE=mixed

Read the agent protocol at <SKILL_PATH>/references/agent-protocol.md and execute the complete review protocol.

Key constraints:
- 首屏必须结论先行 — 不能让人猜
- 图表必须"讲结论" — 不是说"如图X所示"
- 逻辑链不能断 — 观测→验证→排除→结论→动作
- 如果页面更像"图表墙"或"术语墙"，即使技术上渲染成功也不能 pass
- 输出中文，enum 保持英文
`,
  effort: "hi"
})
```

## Review Dimensions

| 维度 | 检查要点 |
|------|----------|
| 可读性 | 首屏结论先行？10s/1min/2min 目标达成？ |
| 证据完整性 | 主结论有图文证据？关键图表渲染？无图表墙？无图文脱节？ |
| 逻辑链 | 观测→验证→排除→结论→动作？排除其他原因？统计术语翻译成白话？ |
| 3D 与图表覆盖 | ECharts 是否可用？Three.js 是否可用？3D 贴合真实工艺？无仅占位不解释？ |

## Pass Standard

全部满足才给 `pass`：
1. 非算法背景用户能快速理解结论
2. 主结论都有充分图文证据
3. 图表和 3D 模块服务于理解，不是装饰
4. 逻辑链清楚，不需要读者自己补脑
5. 没有明显证据缺口或图文脱节

## Decision Rule

- `pass`: 页面可以交付
- `warn`: 页面可用但存在可优化项
- `fail`: 页面不合格，必须回到 html-visualizer 修订（最多 3 次）

**如果页面更像"图表墙"或"术语墙"，即使技术上渲染成功，也不能 pass。**

## Output Contract

```json
{
  "verdict": "pass",
  "overall_score": 92,
  "blocking_issues": [],
  "warnings": [],
  "checks": [
    {"name": "hero_clarity", "status": "pass", "evidence": "..."},
    {"name": "evidence_completeness", "status": "pass", "evidence": "..."},
    {"name": "logic_chain", "status": "pass", "evidence": "..."},
    {"name": "chart_init", "status": "pass", "evidence": "..."},
    {"name": "threejs_init", "status": "pass", "evidence": "..."}
  ]
}
```

## Verification

```bash
SKILL_PATH=".omp/skills/industrial-html-reviewer"
SHARED_PATH=".omp/shared"

node "$SHARED_PATH/scripts/validate.mjs" \
  "$SHARED_PATH/schemas/html_review_schema.json" \
  "$RUN_DIR/05_review/html_review.json"

test "$(wc -c < "$RUN_DIR/diagnostic-report.html")" -ge 5120
```

## Resources

All resources co-located under `.omp/skills/industrial-html-reviewer/`:

- `references/agent-protocol.md` — 完整 HTML 审核协议（人格、检查清单、输出验证）
- `schemas/html_review_schema.json` — html_review.json JSON Schema
