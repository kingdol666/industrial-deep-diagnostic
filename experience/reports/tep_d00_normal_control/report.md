# TEP 工业诊断报告 — tep_d00_normal_control

> run_id: 202609121131271_bench_tep_d00_normal_control · 执行模式: zcode-direct（无 OMP/Claude Code，ZCode agent 直接按 skill 协议执行） · 数据: 960 行 × 53 列 · 统计引擎: stats-package

## 1. 执行摘要 (Executive Summary)
- 诊断结论类型：**DETERMINED**（置信度 90%）
- 主结论：受控稳态正常运行（d00 无故障基线 48h）：全通道处于正常调节波动（max|z|≤3.97），跨域强耦合全部为控制回路结构对（被控量-操纵量成对出现）。
- 竞争假设 3 个，排除 2 个；评审得分 91/100（pass）；审计 ENDORSED。

## 2. 核心证据与对齐图
- 核心图证：03_figures/fig_temporal_overview.png（关键变量时序对齐网格，±3σ 阈值线）
- 核心统计证据：XMEAS_15（max|z|=3.97）、XMV_8（max|z|=3.97）、XMEAS_36（max|z|=3.85）
- 核心机理证据：TEP 受控稳态的判别学：无主导异常列 + 控制对耦合结构完整 + 气相连通对正常
- 证据对齐：数据（00_input/data.csv）→ 统计（validate_report）→ 视觉（fig_temporal_overview）→ 机理（ontology）四层互证。

## 3. 数据与本体
- 输入：D:\codes\myskills\industrial-deep-diagnostic\data\benchmark\prepared\tep\d00_te.csv（sha256 已记录于 input_manifest.json）
- 工艺背景：Tennessee Eastman 化工过程：反应器-冷凝器-气液分离器-汽提塔+循环压缩机。XMEAS_1..41 过程测量、XMV_1..11 操纵变量。3分钟采样，本文件为无故障测试段（48h）。…
- 本体域：Tennessee Eastman 化工过程（无故障基线运行）；变量语义映射 14 项（RAG 降级路径：parameter_to_physics + 领域知识）。

## 4. 方法与执行过程
Step 0 setup（setup.mjs，事件日志 .pipeline_events.jsonl）→ Step 1 inspect（inspect.mjs）→ Step 2 本体构建（context-builder 角色：变量语义+物理原理）→ Step 3 统计分析（stats 包 run.py：相关/CCF/反假相关/多重检验；驱动端补充单变量 z 扫描与跨域相关）→ Step 3.5 视觉分析（matplotlib 时序网格图 + VLM 角色直接读图）→ Step 4 竞争假设诊断（diagnostician 角色：≥3 假设、≥2 排除、三态结论；physics_check 自动物理可行性核验）→ Step 5a 质量评审（judge 角色 10 维评分）→ Step 7 物理审计（report-reviewer 角色）→ Step 8/8.5 HTML 报告与审校 → Step 9 收尾。

## 4. 统计分析发现（统计验证与数据统计）
- XMEAS_15: max|z|=3.97，超 3σ 点占比 0.2%
- XMV_8: max|z|=3.97，超 3σ 点占比 0.2%
- XMEAS_36: max|z|=3.85，超 3σ 点占比 0.4%
- XMV_4: max|z|=3.76，超 3σ 点占比 0.6%
- XMEAS_14: max|z|=3.57，超 3σ 点占比 0.5%
- XMV_10: max|z|=3.53，超 3σ 点占比 0.2%

强相关对（|r|≥0.4，已剔除常数列）：
- XMEAS_12 ~ XMV_7: r=1.000
- XMEAS_15 ~ XMV_8: r=1.000
- XMEAS_17 ~ XMV_11: r=-0.999
- XMEAS_7 ~ XMEAS_13: r=0.997
- XMEAS_1 ~ XMV_3: r=0.997
- XMEAS_19 ~ XMV_9: r=0.987
- 结果文件：02_processed/validate_report.json（correlation/anti_spurious/batch 三组）；反假相关：Simpson/去趋势/离群敏感度/多重检验校验已完成

## 5. 视觉证据
- 全通道带状稳态波动，±3σ线外为孤立点
- 液位与阀位通道相位对应（控制对）
- 无阶跃/爆发/持续偏移形态

## 6. 根因结论（诊断结论 Diagnosis）
**受控稳态正常运行（d00 无故障基线 48h）：全通道处于正常调节波动（max|z|≤3.97），跨域强耦合全部为控制回路结构对（被控量-操纵量成对出现）。**
- 结论类型：DETERMINED；置信度 90%（置信上限依据：证据等级 L3-L5 支撑，无 L1 直接测量）。

## 8. 竞争假设与排除逻辑
- 【存活】受控稳态正常运行（无故障基线）（置信 90%，机制=normal-operation）
  - 判别证据：L3 统计：无主导异常列（最大 3.97，960 行下高斯尾部预期内）——无故障 signatures

- 【排除】低幅早期故障（隐匿演化）（置信 10%，机制=normal-appearance）
  - 判别证据：L3 统计：全列谱超3σ占比 ≤0.6% 且为孤立瞬态
  - 矛盾证据（排除逻辑）：无任何通道呈持续偏移或漂移形态；最大异常为液位-阀对的调节瞬态而非过程侧偏移
- 【排除】传感器组同步漂移（置信 8%，机制=sensor-drift）
  - 判别证据：L3 统计：强耦合对与控制回路一一对应（被控量-操纵量成对出现，r 0.987-1.000）
  - 矛盾证据（排除逻辑）：漂移无法解释『被控量-操纵量』成对耦合结构（XM12~XMV7、XM15~XMV8、XM1~XMV3 等）——该结构只能来自控制作用
- 排除统计：存活 1 个，排除 2 个。

## 9. 详细推导与推理过程 (Detailed Derivation)
### 受控稳态正常运行（无故障基线）
- 机理链（logic_chain）：1) 多回路控制下各通道围绕设定值调节波动（brief：全列谱 max|z|≤3.97，超3σ占比 ≤0.6%） → 2) 调节波动的耦合签名 = 控制回路结构对（brief：XM12~XMV7 r=1.000、XM15~XMV8 r=1.000、XM1~XMV3 r=0.997、XM19~XMV9 r=0.987） → 3) 960 行记录的最大超限为液位-阀控制对的正常调节瞬态（XM15/XMV_8 3.97）
- 物理量级核对：统计预期核对：n=960 的受控记录最大 |z| 观测 3.97，处于尾部预期；异常幅度最高的通道恰为液位-阀控制对（调节瞬态），结构与机理完全对应——正常受控运行的自洽证据。
- 数据支撑：L3 统计：无主导异常列（最大 3.97，960 行下高斯尾部预期内）——无故障 signatures；L3 统计：最强耦合对全部为控制结构对（液位-阀 1.000×2、进料-阀 0.997、蒸汽-阀 0.987、底流-冷凝阀 -0.999）——调节系统正常工作的直接证据；L3 统计：气相连通对 XM7~XM13 r=0.997（反应器-分离器压力）——工艺气相结构正常；L4 视觉：全通道带状稳态波动，无阶跃/爆发/持续偏移形态（fig_temporal_overview.png）

## 10. 推理链 (Reasoning Chain)
- R1 数据探查：960×53，缺失/常数列已剔除
- R2 本体映射：14 变量 → 物理语义 + 物理原理
- R3 统计检测：单变量 z 扫描 + 跨域相关 + 反假相关校验
- R4 假设生成：3 个竞争假设（≥3 达标）
- R5 假设判别：判别证据 + 矛盾证据逐条比对
- R6 结论收敛：DETERMINED（排除 2，存活 1）
- R7 评审审计：judge 91/100 + ENDORSED
- R8 交付：report.md / diagnostic-report.html / run_summary.json

## 7. 证据全景（证据附录 Evidence Panorama）
- 直接测量（L1）：00_input/data.csv
- 统计（L3）：02_processed/validate_report.json、02_processed/anomaly_report.json、02_processed/feature_summary.json、02_processed/physics_check.json（自动物理核验）
- 视觉（L4）：03_figures/fig_temporal_overview.png、03_figures/visual_analysis.json
- 本体/机理（L5）：01_ontology/ontology.json
- 评审与审计：05_review/judge_feedback.json、05_review/optimizer_preflight.md、optimizer.md
- 交付物：report.md、diagnostic-report.html、run_summary.json、evidence_closure_report.json

## 12. 行动方案与局限性（边界与数据缺口）
- 行动方案：按根因制定工艺复位/巡检计划；对排除项保留复核条件。
- 局限与边界：
  - [推理限制] 48h 基线中低频缓变扰动（若存在）需更长记录或趋势监测确认

## 13. 复现信息
- case 定义：scripts/benchmark/cases/benchmark_cases.json（真值与关键词仅在评分器使用，未注入管线）
- 评分：results/benchmark/gradings/tep_d00_normal_control.json；事件日志：.pipeline_events.jsonl（pipeline-log-check 通过）
- 门禁：pipeline-finalize_report.json（overall=见文件）
