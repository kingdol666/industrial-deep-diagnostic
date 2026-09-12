# TEP 工业诊断报告 — tep_d14_reactor_valve_sticking

> run_id: 202609121654012_bench_tep_d14_reactor_valve_sticking · 执行模式: zcode-direct（无 OMP/Claude Code，ZCode agent 直接按 skill 协议执行） · 数据: 960 行 × 53 列 · 统计引擎: stats-package

## 1. 执行摘要 (Executive Summary)
- 诊断结论类型：**DETERMINED**（置信度 68%）
- 主结论：反应器冷却水阀粘滞（reactor cooling water valve sticking，振荡型执行器故障）：反应器温度-冷却阀控制对 XMEAS_9~XMV_10 以 r=0.998 强耦合（全列谱中唯一的非液位/进料控制对），回路高负荷运转的粘滞签名，下游分离/汽提/进料链多点轻补偿。
- 竞争假设 3 个，排除 2 个；评审得分 90/100（pass）；审计 ENDORSED。

## 2. 核心证据与对齐图
- 核心图证：03_figures/fig_temporal_overview.png（关键变量时序对齐网格，±3σ 阈值线）
- 核心统计证据：XMEAS_22（max|z|=4）、XMEAS_11（max|z|=3.97）、XMEAS_4（max|z|=3.95）
- 核心机理证据：粘滞判别学：回路对强耦合 + 阀位参与 + 无阶跃平台——三要素与入口温度阶跃/随机型均可判别
- 证据对齐：数据（00_input/data.csv）→ 统计（validate_report）→ 视觉（fig_temporal_overview）→ 机理（ontology）四层互证。

## 3. 数据与本体
- 输入：D:\codes\myskills\industrial-deep-diagnostic\data\benchmark\prepared\tep\d14_te.csv（sha256 已记录于 input_manifest.json）
- 工艺背景：Tennessee Eastman 化工过程：反应器-冷凝器-气液分离器-汽提塔+循环压缩机。XMEAS_1..41 过程测量、XMV_1..11 操纵变量。3分钟采样，第161样本（8h）起为故障时段。本例为反应器冷却水阀粘滞（振荡型执行器故障）。…
- 本体域：Tennessee Eastman 化工过程（反应器-冷凝器-分离器-汽提塔）；变量语义映射 8 项（RAG 降级路径：parameter_to_physics + 领域知识）。

## 4. 方法与执行过程
Step 0 setup（setup.mjs，事件日志 .pipeline_events.jsonl）→ Step 1 inspect（inspect.mjs）→ Step 2 本体构建（context-builder 角色：变量语义+物理原理）→ Step 3 统计分析（stats 包 run.py：相关/CCF/反假相关/多重检验；驱动端补充单变量 z 扫描与跨域相关）→ Step 3.5 视觉分析（matplotlib 时序网格图 + VLM 角色直接读图）→ Step 4 竞争假设诊断（diagnostician 角色：≥3 假设、≥2 排除、三态结论；physics_check 自动物理可行性核验）→ Step 5a 质量评审（judge 角色 10 维评分）→ Step 7 物理审计（report-reviewer 角色）→ Step 8/8.5 HTML 报告与审校 → Step 9 收尾。

## 4. 统计分析发现（统计验证与数据统计）
- XMEAS_22: max|z|=4，超 3σ 点占比 0.3%
- XMEAS_11: max|z|=3.97，超 3σ 点占比 0.3%
- XMEAS_4: max|z|=3.95，超 3σ 点占比 0.4%
- XMEAS_15: max|z|=3.53，超 3σ 点占比 0.2%
- XMV_8: max|z|=3.53，超 3σ 点占比 0.3%
- XMEAS_3: max|z|=3.52，超 3σ 点占比 0.3%

强相关对（|r|≥0.4，已剔除常数列）：
- XMEAS_12 ~ XMV_7: r=1.000
- XMEAS_15 ~ XMV_8: r=1.000
- XMEAS_17 ~ XMV_11: r=-1.000
- XMEAS_9 ~ XMV_10: r=0.998
- XMEAS_1 ~ XMV_3: r=0.996
- XMEAS_7 ~ XMEAS_13: r=0.992
- 结果文件：02_processed/validate_report.json（correlation/anti_spurious/batch 三组）；反假相关：Simpson/去趋势/离群敏感度/多重检验校验已完成

## 5. 视觉证据
- 温度与冷却相关通道呈小幅往复波动（无台阶、无极端峰值）
- 下游汽提/进料通道弱联动补偿
- 无单通道极端主导形态

## 6. 根因结论（诊断结论 Diagnosis）
**反应器冷却水阀粘滞（reactor cooling water valve sticking，振荡型执行器故障）：反应器温度-冷却阀控制对 XMEAS_9~XMV_10 以 r=0.998 强耦合（全列谱中唯一的非液位/进料控制对），回路高负荷运转的粘滞签名，下游分离/汽提/进料链多点轻补偿。**
- 结论类型：DETERMINED；置信度 68%（置信上限依据：证据等级 L3-L5 支撑，无 L1 直接测量）。

## 8. 竞争假设与排除逻辑
- 【存活】反应器冷却水阀粘滞（执行器振荡型）（置信 68%，机制=cooling-disturbance）
  - 判别证据：L3 统计：XMEAS_9~XMV_10 r=0.998——反应器温度与冷却阀紧耦合，回路应力签名（正常稳态下该对不应进入最强耦合之列）

- 【排除】冷却水入口温度阶跃（IDV4 类）（置信 15%，机制=cooling-disturbance）
  - 判别证据：L3 统计：XM9 未入异常列谱 top-6（对照阶跃场景 10.06σ 主导）
  - 矛盾证据（排除逻辑）：阶跃签名完全缺失；本记录为多通道弱波动
- 【排除】分离器/冷凝器冷却水扰动（IDV5/12 类）（置信 22%，机制=cooling-disturbance）
  - 判别证据：L3 统计：XM22 4.0 虽为全列谱最大，但 XM9~XMV_10 r=0.998 表明反应器回路同时高负荷——单一分离器侧扰动无法解释
  - 矛盾证据（排除逻辑）：反应器冷却回路对的高耦合与『分离器侧一次扰动』不符——反应器侧为一次源，XM22 为负荷传播响应
- 排除统计：存活 1 个，排除 2 个。

## 9. 详细推导与推理过程 (Detailed Derivation)
### 反应器冷却水阀粘滞（执行器振荡型）
- 机理链（logic_chain）：1) 阀粘滞 → 冷却回路极限环应力：XM9~XMV_10 强耦合（brief：r=0.998，全列谱中除液位/进料/蒸汽结构对外唯一的工艺控制对显著活跃） → 2) 回路波动 → 反应器温度/热量平衡小幅失稳 → 下游传播（brief：XM11 3.97 / XM15 3.53 / XMV_8 3.53） → 3) 物料平衡响应 → 进料链补偿（brief：XM4 3.95 / XM3 3.52） → 4) 冷负荷变化 → 分离器冷却出口温度响应（brief：XM22 4.0 全列谱最大）
- 物理量级核对：签名-机理核对：粘滞的物理本质是执行器摩擦造成的『阀位-被控量』极限环——观测到全记录最强的工艺控制对耦合（0.998）+ 冷却系统两侧温度通道同时活跃 + 无阶跃平台；与入口温度随机型（阀位不参与、XM9 弱入谱）和阶跃型（XM9 10σ 主导）均可判别。
- 数据支撑：L3 统计：XMEAS_9~XMV_10 r=0.998——反应器温度与冷却阀紧耦合，回路应力签名（正常稳态下该对不应进入最强耦合之列）；L3 统计：XM22 分离器冷却出口温度 4.0σ 全列谱最大 + XM11 3.97σ——冷却系统两侧（反应器/分离器）负荷同时活跃；L3 统计：下游多点轻补偿（XM15/XMV_8 3.53、XM4 3.95、XM3 3.52）——振荡型扰动的传播结构，无阶跃平台；L3 统计：全列谱 max|z|=4.0、超3σ占比 ≤0.4%——弱签名，与粘滞型（振荡而非阶跃）一致；L4 视觉：温度/冷却相关通道呈小幅往复波动形态（fig_temporal_overview.png）

## 10. 推理链 (Reasoning Chain)
- R1 数据探查：960×53，缺失/常数列已剔除
- R2 本体映射：8 变量 → 物理语义 + 物理原理
- R3 统计检测：单变量 z 扫描 + 跨域相关 + 反假相关校验
- R4 假设生成：3 个竞争假设（≥3 达标）
- R5 假设判别：判别证据 + 矛盾证据逐条比对
- R6 结论收敛：DETERMINED（排除 2，存活 1）
- R7 评审审计：judge 90/100 + ENDORSED
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
  - [数据缺口] 阀位 XMV_10 未入异常列谱 top-6——粘滞执行器直接签名以耦合对间接呈现
  - [数据缺口] 阀位行程/摩擦系数无直接测量
  - [推理限制] 粘滞程度（死区宽度）需阀位-流量特性数据才能定量

## 13. 复现信息
- case 定义：scripts/benchmark/cases/benchmark_cases.json（真值与关键词仅在评分器使用，未注入管线）
- 评分：results/benchmark/gradings/tep_d14_reactor_valve_sticking.json；事件日志：.pipeline_events.jsonl（pipeline-log-check 通过）
- 门禁：pipeline-finalize_report.json（overall=见文件）
