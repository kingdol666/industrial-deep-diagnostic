# IDD 报告设计系统（单一视觉权威）

`report.css` 是四个报告渲染器共用的唯一样式源：

- `industrial-line-stability-report/scripts/report_builder.py`
- `industrial-improvement-advisor/scripts/imacore/render.py`
- `industrial-doe-analyzer/scripts/doestats/report_html.py`（+ `templates/doe-report.css` 组件层）
- `diagnostic-html-visualizer/references/report-template.html`（builder 需把本文件内联进单文件报告）

## 不变量

1. **A 骨架**：左章节导轨 + 编号章节 + 三栏正文（编号 / 内容 / 页边批注）+ 印章式评分。
2. **单文件**：生成报告必须把本 CSS 内联进 `<style>`，不得外链。
3. **色彩语义**：等级色只用于等级（A `#2d7d4f` / B `#8a6d3b` / C `#7a6a52`）；暖橙 `#c2673a` 只用于异常/警示。
4. **诚实性 UI**：缺失值 `—` 并给原因码；空态必须明说；处方区与建议区不可混淆。
5. **可读性**：正文 ≥14px、标签 ≥12px、表格用 tabular-nums、支持 `@media print`。

## 修改流程

改 `report.css` → 重跑三个 skill 的测试与真实数据构建 → 检查报告 HTML 的 `rpt-` 类与
自检/门禁（stability S1–S6、advisory S1–S6、DOE G1–G11）。禁止在单个 skill 里复制颜色变量。

`report_design.py` 提供 `css_text()` / `inline_style()` / `css_sha256()` 给 Python 渲染器加载。
