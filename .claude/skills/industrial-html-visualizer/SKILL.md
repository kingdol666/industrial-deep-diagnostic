---
name: industrial-html-visualizer
description: "工业诊断管线 — 从诊断产物构建 ECharts+Three.js 讲解式 HTML 可视化页面。Trigger: HTML可视化, 生成HTML, 前端页面, 可视化报告, html visualization, diagnostic HTML, 3D scene, ECharts. Do NOT use without CP-8 ENDORSED optimizer.md."
---

# Industrial HTML Visualizer

CP-8 ENDORSED 审计结论 (`optimizer.md`) 是执行此技能的唯一前提。无 optimizer.md → 拒绝执行，向主 agent 报告"缺少 CP-8 ENDORSED 审计结论"。

复用 `diagnostic-html-visualizer` skill 的 ECharts/Three.js 模板、设计系统和 Fallback 规则。

## Inputs

| File | Description |
|------|-------------|
| `optimizer.md` | **CP-8 ENDORSED** 审计结论（硬前提） |
| `report.md` | 诊断报告 |
| `04_diagnostics/diagnosis.json` | 诊断结论 |
| `04_diagnostics/evidence.json` | 证据清单 |
| `04_diagnostics/reasoning_chain.json` | 推理链 |
| `01_ontology/ontology.json` | 领域本体（3D 工段恢复） |
| `03_figures/plot_manifest.json` | 图表清单 |
| `03_figures/*.png` | 现成视觉证据 |

缺少 P0 文件时执行 `skill://diagnostic-html-visualizer` §Fallback Rules 对应分支。

## Outputs

| File | Description |
|------|-------------|
| `diagnostic-report.html` | 单文件 HTML ≥5120B |

## Agent Dispatch

```javascript
Agent({
  subagent_type: "html-visualizer",
  description: "从诊断产物构建 ECharts+Three.js 讲解式 HTML 页面",
  permissionMode: "bypassPermissions",
  prompt: `RUN_DIR=<run-dir-path>
SKILL_PATH=<this-skill-directory>
OUTPUT_HTML=<run-dir-path>/diagnostic-report.html
AUDIENCE=mixed
VISUAL_MODE=story

## Protocol

1. 首先读取 "skill://diagnostic-html-visualizer" — 加载 ECharts/Three.js 模板、设计系统、Fallback 规则、visual standards
2. 再读取 "$SKILL_PATH/references/agent-protocol.md" — 执行完整 checklist
3. 按 checklist Phase 1-4 顺序执行

## Key requirements
- ECharts for statistical charts (correlation, time series, anomaly overlays)
- Three.js for 3D process flow (recover real stages from ontology, NOT generic factory)
- Runtime readiness: window.echarts, window.THREE, OrbitControls — multi-source CDN with degraded static fallback
- Interactive evidence chain navigation (三层闭合: 统计→物理→排除)
- Chinese language interface
- Data governance card from data_analysis_conclusion.json`,
  run_in_background: true
})
```

### Runtime Readiness (mandatory)

页面必须检测：
- `window.echarts` 可用 → 至少一个 chart 成功初始化
- `window.THREE` 可用 → 至少一个 3D scene 初始化（如适用）
- CDN 加载失败 → 降级静态内容 + visible degraded-mode notice
- 至少一个图表渲染成功 → 否则显示 error placeholder

## Verification (CP-9)

```bash
test -f "$RUN_DIR/diagnostic-report.html" && \
  test "$(wc -c < "$RUN_DIR/diagnostic-report.html")" -ge 5120
```

## References

- `references/agent-protocol.md` — html-visualizer 子 Agent 执行 checklist
- `skill://diagnostic-html-visualizer` — ECharts/Three.js 模板、设计系统、CSS 变量、视觉语法、Fallback 规则
