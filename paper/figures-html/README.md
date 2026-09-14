# AEI 论文插图模板（单一风格源）

本目录是论文全部插图的 **HTML 源 + 共享模板**。论文 `figures/*.png` 一律由本目录的
HTML 经 Edge headless 高分辨率导出——图可复现、可改数重绘，禁止手改 PNG。

## 模板约束

- `aei_template.css`：唯一风格源（Elsevier/AEI 制图规范）
  - 字体 Arial/Helvetica；Okabe-Ito 色盲友好调色板（`--blue/--sky/--orange/--green/--vermilion/--gray`）
  - 轴线 1.5px、浅网格 `--grid`、直接数值标注；**图内不嵌大标题**（题注由 LaTeX caption 承担）
  - 面板标签 (a)/(b)；表格样式 `table.aei`
- 每个 `<name>.html` 仅负责数据与结构，样式一律引用 `aei_template.css`

## 图清单（与论文 Figure 1–5 一一对应）

| HTML | 论文图 | 内容 |
|---|---|---|
| `fig_pipeline.html` | Fig. 1 | 9 阶段管线 + 质量门 + 修复环 |
| `fig_benchmark.html` | Fig. 2 | 基准构成 + 头条指标 + 逐场景决定性签名 |
| `fig_calibration.html` | Fig. 3 | 逐场景置信度（0.70 协议线，弱签名琥珀色） |
| `fig_tep_perfault.html` | Fig. 4 | TEP 逐故障验证矩阵（vs FaultExplainer + PCA 可检性） |
| `fig_forest.html` | Fig. 5 | Wilson 95% CI forest（Register A 聚合对比） |

## 重绘命令（改数据后执行）

```bash
EDGE="C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"
cd paper/figures-html
"$EDGE" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=3 \
  --window-size=1500,<H> \
  --screenshot="D:\codes\myskills\industrial-deep-diagnostic\paper\figures\<name>.png" \
  "file:///D:/codes/myskills/industrial-deep-diagnostic/paper/figures-html/<name>.html"
```

- `<H>`：fig_pipeline 640 / fig_benchmark 640 / fig_tep_perfault 680 / fig_forest 600 / fig_calibration 640
- `--force-device-scale-factor=3`：3x 输出（1500→4500px，190mm 双栏宽下 ≈ 600 dpi，满足 Elsevier 线图要求）

## 数据更新流程

论文数字变更时：改对应 HTML 中的数字 → 重导出 PNG → `pdflatex×2` 重编译。
数字来源一律以 `results/benchmark/metrics.json` 与 `results/benchmark/rubric.json` 为准（禁止手填）。
