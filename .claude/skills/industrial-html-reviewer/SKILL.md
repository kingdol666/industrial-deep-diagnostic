---
name: industrial-html-reviewer
description: "工业诊断管线 — 审核 HTML 可视化页面的可读性、证据完整性和逻辑链。输出 html_review.json。Trigger: HTML审校, review HTML, HTML review, 页面审核, html reviewer, audit HTML. Do NOT use without diagnostic-report.html."
---

# Industrial HTML Reviewer

审核 `diagnostic-report.html` 可读性、证据完整性、逻辑链、技术质量。
产出 `05_review/html_review.json`(verdict+overall_score+blocking_issues+warnings+checks)。

## I/O

| | Path |
|--|------|
| Input | `diagnostic-report.html`, `04_diagnostics/diagnosis.json`, `report.md` |
| Output | `05_review/html_review.json` |

## Execution

```javascript
Agent({subagent_type:"html-reviewer",description:"审核HTML可视化页面",
  permissionMode:"bypassPermissions",
  prompt:`RUN_DIR=<path>\nSKILL_PATH=<this>\nOUTPUT_HTML=${RUN_DIR}/diagnostic-report.html\n\nRead "${SKILL_PATH}/references/agent-protocol.md" and execute the complete review protocol.`,
  run_in_background:true})
```

## Review Dimensions

| 维度 | 检查要点 |
|------|----------|
| 可读性 | 首屏结论先行？10s/1min/2min目标达成？ |
| 证据完整性 | 主结论有图文证据？关键图表渲染？无图表墙？ |
| 逻辑链 | 观测→验证→排除→结论→动作？排除其他原因？ |
| 技术质量 | ECharts/Three.js初始化？CDN fallback+degraded提示？ |

## Verification

```bash
SKILL_PATH="<this-skill-directory>"
node "$SHARED_PATH/scripts/validate.mjs" \
  "$SHARED_PATH/schemas/html_review_schema.json" \
  "$RUN_DIR/05_review/html_review.json"
test "$(wc -c < "$RUN_DIR/diagnostic-report.html")" -ge 5120
```

## References

- `references/agent-protocol.md` — 完整 HTML 审核协议
- `schemas/html_review_schema.json` — html_review.json Schema
