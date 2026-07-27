---
name: industrial-html-visualizer
description: "工业诊断管线 — 从诊断产物构建 ECharts+Three.js 讲解式 HTML 可视化页面。Trigger: HTML可视化, 生成HTML, 前端页面, 可视化报告, html visualization, diagnostic HTML, 3D scene, ECharts. Do NOT use without CP-8 ENDORSED optimizer.md."
---

# Industrial HTML Visualizer

从诊断产物（diagnosis + report + ontology + figures）构建 ECharts + Three.js 讲解式 HTML 可视化页面 `diagnostic-report.html`。

**红灯动作**: 主 agent 禁止自行编写 HTML——必须通过本 skill 的 html-visualizer 子Agent 生成。

## Inputs (expected in `RUN_DIR`)

| File | Description |
|------|-------------|
| `optimizer.md` | CP-8 ENDORSED 审计结论 |
| `report.md` | 诊断报告 |
| `04_diagnostics/diagnosis.json` | 诊断结论 |
| `04_diagnostics/evidence.json` | 证据清单 |
| `01_ontology/ontology.json` | 领域本体（3D 场景工段恢复） |
| `03_figures/plot_manifest.json` | 图表清单 |
| `03_figures/*.png` | 图表 |

## Outputs

| File | Description |
|------|-------------|
| `diagnostic-report.html` | ECharts + Three.js 讲解式 HTML 页面（≥5120B） |

## Execution

**仅在 CP-8 ENDORSED 后执行。** 无条件自动构建，除非用户前置了 `00_input/html_opt_out`。

```javascript
Agent({
  subagent_type: "html-visualizer",
  description: "生成诊断结果的前端 HTML 可视化讲解页面",
  permissionMode: "bypassPermissions",
  prompt: `RUN_DIR=<run-dir-path>
SKILL_PATH=<this-skill-directory>
OUTPUT_HTML=<run-dir-path>/diagnostic-report.html
AUDIENCE=mixed
VISUAL_MODE=story

Read "<this-skill-directory>/references/agent-protocol.md" and execute the complete protocol.

Key requirements:
- ECharts for statistical charts (correlation matrices, time series, anomaly overlays)
- Three.js for 3D process flow visualization (recover real process stages from ontology, NOT generic factory)
- Runtime readiness checks: window.echarts, window.THREE, OrbitControls
- Multi-source CDN loading with fallback to degraded static content
- Interactive evidence chain navigation
- Chinese language interface`,
  run_in_background: true
})
```

### Runtime Readiness (mandatory)

页面必须包含以下检测：
- `window.echarts` 可用 → 至少一个 chart 成功初始化
- `window.THREE` 可用 → 至少一个 3D scene 成功初始化（如适用）
- CDN 加载失败 → 降级静态内容 + visible degraded-mode notice
- 所有图表至少渲染一次 → 否则显示 error placeholder

### HTML Opt-Out

用户显式声明不要 HTML 时，主 agent 在 Step 8 前运行：
```bash
touch "$RUN_DIR/00_input/html_opt_out"
```
有此标记则跳过 HTML 构建和 CP-9。

## Verification

```bash
# CP-9: HTML Delivery
test -f "$RUN_DIR/diagnostic-report.html" && \
  test "$(wc -c < "$RUN_DIR/diagnostic-report.html")" -ge 5120
```

## References

- `references/agent-protocol.md` — 完整的 HTML 可视化执行协议
- 复用 `diagnostic-html-visualizer` skill 的 ECharts/Three.js 模板和设计规范
