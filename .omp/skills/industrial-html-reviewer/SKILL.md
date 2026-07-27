---
name: industrial-html-reviewer
description: "工业诊断管线 — 审核 HTML 可视化页面的可读性、证据完整性和逻辑链。输出 html_review.json。Trigger: HTML审校, review HTML, HTML review, 页面审核, html reviewer, audit HTML. Do NOT use without diagnostic-report.html."
---

# Industrial HTML Reviewer

审核 HTML 可视化页面的可读性、证据完整性、逻辑链正确性。产出 `html_review.json`，判定 pass/needs_revision。不通过则触发回退到 html-visualizer 修复。

## Inputs (expected in `RUN_DIR`)

| File | Description |
|------|-------------|
| `diagnostic-report.html` | HTML 可视化页面（≥5120B） |
| `04_diagnostics/diagnosis.json` | 诊断结论（交叉验证） |
| `report.md` | 诊断报告（交叉验证） |

## Outputs

| File | Description |
|------|-------------|
| `05_review/html_review.json` | 审核反馈（verdict + score + issues） |

## Execution

启动 `html-reviewer` 子Agent：

```javascript
Agent({
  subagent_type: "html-reviewer",
  description: "审核 HTML 可视化页面",
  permissionMode: "bypassPermissions",
  prompt: `RUN_DIR=<run-dir-path>
SKILL_PATH=<this-skill-directory>/../../../.claude/skills/industrial-html-reviewer
OUTPUT_HTML=<run-dir-path>/diagnostic-report.html

Read "<this-skill-directory>/../../../.claude/skills/industrial-html-reviewer/references/agent-protocol.md" and execute the complete review protocol.`,
  run_in_background: true
})
```

### Review Dimensions

| 维度 | 检查要点 |
|------|----------|
| 可读性 | 页面布局是否清晰？颜色/字体是否可读？移动端是否可用？ |
| 证据完整性 | 关键图表是否全部渲染？3D 场景是否可用？CDN 是否 fallback？ |
| 逻辑链 | 页面叙述是否与 report.md 一致？推理链是否可追溯？ |
| 技术质量 | ECharts/Three.js 是否成功初始化？性能是否可接受？ |

### Runtime Readiness Checks

页面必须通过以下检测：
- `window.echarts` 可用
- `window.THREE` 可用（如使用 3D）
- 至少一个图表成功初始化
- CDN 加载失败时有降级静态内容
- 可见的 degraded-mode 提示（库加载失败时）

## Verification

```bash
SKILL_PATH="<this-skill-directory>/../../../.claude/skills/industrial-html-reviewer"

# Schema validation
node "$SKILL_PATH/scripts/validate.mjs" \
  "$SKILL_PATH/schemas/html_review_schema.json" \
  "$RUN_DIR/05_review/html_review.json"

# Size check
test "$(wc -c < "$RUN_DIR/diagnostic-report.html")" -ge 5120
```

## References

- `references/agent-protocol.md` — 完整的 HTML 审核协议
- `schemas/html_review_schema.json` — html_review.json Schema
