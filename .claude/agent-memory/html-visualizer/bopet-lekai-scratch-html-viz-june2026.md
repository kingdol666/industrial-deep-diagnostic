---
name: bopet-lekai-scratch-html-viz-june2026
description: "BOPET MD scratch COMPETING_SET (45/100) HTML visualization: 18-roll 3-zone 3D model with anomalies on Roll 16 (W1C8B torque std) and Roll 17 (W1C8C torque mean); 3 surviving + 3 eliminated hypotheses; LOESS detrend compare, profile, robustness ECharts; all 5 PNGs reused across 3 evidence layers"
metadata:
  type: project
---

BOPET MD拉伸段划伤(scratch) COMPETING_SET 诊断的HTML可视化报告，于2026-06-22构建。

**Why:** 用户要求为lekai-scratch运行生成诊断结果可视化页面，AUDIENCE=mixed, VISUAL_MODE=story。这是工业现场操作工、质量工程师、生产主管三方共同需要理解的一个"没有唯一答案"的诊断结果。

**Key structural details:**
- 诊断类型 COMPETING_SET (45/100, 上限65%), Judge 76/100, 0个阻断问题
- 55批次, 7产品型号, 44参数×4统计量, 3天窗口 (2026-05-07至05-10)
- 3个存活假说 (H1扭矩均值 rho=-0.271, H2 PG31DS内扭矩std rho=0.581, H3产品混杂60/100)
- 3个排除假说 (E1过滤器 E2挤出机 E3急冷温度, 全部|r|<0.15)
- 5张真实PNG全部复用 (fig1分布/fig2箱线/fig3散点→统计层; fig4温度剖面/fig5扭矩剖面→物理层)
- 3个ECharts图表 (去趋势对比/剖面/偏差全景)
- Three.js 3D场景: 18辊3段温区真实顺序, 异常17号辊+16号辊红色高亮
- 1轴对齐的展台设计 (非默认辊/圆柱简化, 但BOPET辊组是圆柱特例)
- 物理链4步 (接触压力→冷却效率→残余应力→划伤敏感), Arrhenius量级验证

**How to apply:** 当需要为BOPET MD产线的COMPETING_SET诊断生成HTML可视化时参考此页面结构。核心要义: Hero诚实呈现不确定性而非假装有答案, 3D场景按ontology三段温区18辊恢复真实产线, 证据链三层全部使用真实PNG+统计数据+物理推理。

**Related memories:** [[diagnostic-html-visualizer-integration]]
