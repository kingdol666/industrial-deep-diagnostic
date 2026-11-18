# Round 32 — Figure Overhaul & Final AEI Review (2026-09-22)

对象：`paper/main.tex`（AEI 投稿版，blind-loop round31 已达成 3/3 publishable 共识）。
本轮任务（作者指令）：①对论文做 AEI 发表口径的审查与编排复核；②确认前部叙述
（背景/设计思路/执行过程/功能）完整；③实验部分对齐真实 benchmark 报告；④全部配图
按 Nature 级标准逐一重绘（HTML+SVG），流程图改用 draw.io 并交付 `.drawio` 源文件。

## A. 审查结论（文字部分）

- **前部叙述**：Introduction 三障碍 → 贡献四条 → §3 架构（执行架构/层/管线/引擎/审计面）
  → §3.3 "Why nine stages"（设计哲学：确定性/语义分层、工件通信、capped honesty）
  → §4 方法。设计思路、执行过程、功能、背景四要素齐备，本轮**不改写正文**
  （round31 盲审共识基于当前文本，churn 风险大于收益）。
- **实验数字口径**：全部头条数字对 `results/benchmark/` 20260917 canonical 批次复核一致
  （Top-1 4/9 CI[18.9,73.3]、top-k 9/9、对照 3/3（1 blind）、rubric 94.6、judge 94.7、
  bare-LLM 9/9、45/45 DETERMINISTIC、REPRODUCIBLE）。中断批次（202609181728xxx）未被引用 ✓。
- **发现的缺陷（已修）**：
  1. fig_benchmark 面板 (b)：SKAB cavitation 与 IDV3 的 judge 空心点因 x 比例错置
     （cx=607.5 > viewBox 524）被整体裁掉——两点的 judge 分（90/90）在旧版 PNG 中不可见。
  2. `highlights.md` 第 3 条 93 字符，超 Elsevier 85 字符上限 → 缩至 84。
  3. figures-html/README.md 的 DEPRECATED 注记与实况相反 → 改写为现行管线说明。
  4. round27 P3 遗留（图内大段 prose 与 caption 重复）→ 在重绘中一并裁剪为紧凑图例/chips。

## B. 配图重绘（10/10）

风格系统：Okabe-Ito 色盲安全调色板（与正文 LaTeX 色一致）、Arial、1500px 画布 =
\textwidth 印刷（29px 刻度 ≈ 6.6pt、31px 轴标签 ≈ 7.1pt）、直接数值标注、克制网格、
面板标签 (a)/(b)。数据一律沿用 round31 盲审核过的已验证数值（仅修显示缺陷，不改口径）。

| 图 | 处理 | 源文件 |
|---|---|---|
| Fig. 1 架构 | 重绘为 **draw.io** 源（五层平面、14 引擎、诊断路径蛇形、审计面） | `fig_architecture.drawio` |
| Fig. 2 管线 | 重绘为 **draw.io** 源（双行蛇形、CP 门禁 chips、琥珀虚线修复环、绿色硬门） | `fig_pipeline.drawio` |
| Fig. 3 执行解剖 | 保留已验证文字，字号升级（印刷 ≥6pt） | `fig_trace.html` |
| Fig. 4 基准结果 | 重绘：(a) 堆叠条+6 chips；(b) rubric/judge 点图（**修复裁剪点**，12 行全显） | `fig_benchmark.html` |
| Fig. 5 置信度 | 重绘：12 条两行标签、协议线标注错层、越界并入数值标签 | `fig_calibration.html` |
| Fig. 6 SKAB 案例 | 重绘：信号图 + 证据链 chips；压力注释框收窄 | `fig_casestudy.html` |
| Fig. 7 TEP 矩阵 | 重绘：色彩语义与全文统一（CS=天蓝斜纹，弃旧琥珀） | `fig_tep_perfault.html` |
| Fig. 8 森林图 | 重绘：字号提至 6.6pt+、图例两行 | `fig_forest.html` |
| Fig. 9 套件矩阵 | 重绘：PCA 热度格连续标度、4 stat chips、组标签 IPS | `fig_suite_matrix.html` |
| Fig. 10 一致性 | 重绘：散点 + 卡片；11 行重复表格压缩为脚注一句 | `fig_consistency.html` |

**draw.io 渲染链**：`drawio_render.py`（自研，mxGraph 子集 → SVG，两遍渲染+贪心换行），
保证论文 PNG 与 `.drawio` 源逐像素同源；作者可在 draw.io 桌面版直接二次编辑后
`bash render_all.sh` 重出图。两图已交付 `paper/figures-html/*.drawio`。

## C. main.tex 变更（最小手术）

- Fig.1/Fig.2 图注：渲染源措辞 → "diagram authored in draw.io; the .drawio source and
  the export script are released with the paper"。
- Fig.7 图注配色句与新配色对齐（amber → hatched sky blue）。
- Fig.8 图注："interval labels extend past the axis" → "open markers mark the two
  readings bounded at 100%"。
- Fig.9 图注：补热度标度说明、对照格 "grey no" → "green no"。
- `highlights.md` 第 3 条压缩至 84 字符。

## D. 验证

- 编译：pdflatex ×2，**0 错误、0 未定义引用**，54 页（图幅变化 +1 页），
  唯一 Overfull 0.52pt（表 6 内，不可见）。`main.pdf` 已替换为终版。
- 视觉门禁（visual-judge，三轮）：R1 暴露 9 类裁切/叠印 → R2 修 5 处 → R3 修 3 处 →
  终验 10/10 页 **全部 pass**（含 4x 裁剪级复核）。页面快照存 `paper/_pagepng_r32/`。
- 数字一致性：所有图内数字可溯源至 `results/benchmark/{metrics,rubric,consistency_audit,
  baselines}.json` 与 gradings/，未引入新口径。

## E. 遗留（不阻断投稿）

- fig_consistency 面板 (a) 相邻旋转标签（batch093/batch001*）间距略紧（可读，judge 放行）。
- `make_figures.py`（matplotlib 备份线）保留为 provenance，与现行管线不再同步。
- Neutralised-identifier re-run 等预注册实验仍待执行（正文已披露，不属本轮范围）。
