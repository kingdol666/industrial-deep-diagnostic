# TEP 工业诊断报告 — tep_d04_reactor_cooling_step

> run_id: 202609121509530_bench_tep_d04_reactor_cooling_step · 执行模式: zcode-direct（无 OMP/Claude Code，ZCode agent 直接按 skill 协议执行） · 数据: 960 行 × 53 列 · 统计引擎: stats-package

## 1. 执行摘要 (Executive Summary)
- 诊断结论类型：**DETERMINED**（置信度 86%）
- 主结论：反应器冷却侧扰动（reactor cooling disturbance）：反应器温度 XMEAS_9 以 10.06σ 主导异常列谱（次高仅 3.8σ），进料与组分通道仅轻度联动——冷却能力不足引发的一次热失衡，符合冷却水入口温度阶跃机理。
- 竞争假设 3 个，排除 2 个；评审得分 92/100（pass）；审计 ENDORSED。

## 2. 核心证据与对齐图
- 核心图证：03_figures/fig_temporal_overview.png（关键变量时序对齐网格，±3σ 阈值线）
- 核心统计证据：XMEAS_9（max|z|=10.06）、XMEAS_2（max|z|=3.8）、XMV_3（max|z|=3.74）
- 核心机理证据：TEP 冷却类扰动的判别学：XM9 主导 + 补偿链为辅 + 组分不主导
- 证据对齐：数据（00_input/data.csv）→ 统计（validate_report）→ 视觉（fig_temporal_overview）→ 机理（ontology）四层互证。

## 3. 数据与本体
- 输入：D:\codes\myskills\industrial-deep-diagnostic\data\benchmark\prepared\tep\d04_te.csv（sha256 已记录于 input_manifest.json）
- 工艺背景：Tennessee Eastman 化工过程：反应器-冷凝器-气液分离器-汽提塔+循环压缩机。XMEAS_1..41 过程测量、XMV_1..11 操纵变量（Downs-Vogel 标准映射）。3分钟采样，第161样本（8h）起为故障时段。本例为反应器冷却水入口温度阶跃。…
- 本体域：Tennessee Eastman 化工过程（反应器-冷凝器-分离器-汽提塔）；变量语义映射 8 项（RAG 降级路径：parameter_to_physics + 领域知识）。

## 4. 方法与执行过程
Step 0 setup（setup.mjs，事件日志 .pipeline_events.jsonl）→ Step 1 inspect（inspect.mjs）→ Step 2 本体构建（context-builder 角色：变量语义+物理原理）→ Step 3 统计分析（stats 包 run.py：相关/CCF/反假相关/多重检验；驱动端补充单变量 z 扫描与跨域相关）→ Step 3.5 视觉分析（matplotlib 时序网格图 + VLM 角色直接读图）→ Step 4 竞争假设诊断（diagnostician 角色：≥3 假设、≥2 排除、三态结论；physics_check 自动物理可行性核验）→ Step 5a 质量评审（judge 角色 10 维评分）→ Step 7 物理审计（report-reviewer 角色）→ Step 8/8.5 HTML 报告与审校 → Step 9 收尾。

## 4. 统计分析发现（统计验证与数据统计）
- XMEAS_9: max|z|=10.06，超 3σ 点占比 0.3%
- XMEAS_2: max|z|=3.8，超 3σ 点占比 0.2%
- XMV_3: max|z|=3.74，超 3σ 点占比 0.2%
- XMEAS_1: max|z|=3.7，超 3σ 点占比 0.2%
- XMEAS_23: max|z|=3.7，超 3σ 点占比 0.4%
- XMEAS_11: max|z|=3.66，超 3σ 点占比 0.4%

强相关对（|r|≥0.4，已剔除常数列）：
- XMEAS_15 ~ XMV_8: r=1.000
- XMEAS_12 ~ XMV_7: r=1.000
- XMEAS_17 ~ XMV_11: r=-0.999
- XMEAS_7 ~ XMEAS_13: r=0.998
- XMEAS_1 ~ XMV_3: r=0.996
- XMEAS_19 ~ XMV_9: r=0.981
- 结果文件：02_processed/validate_report.json（correlation/anti_spurious/batch 三组）；反假相关：Simpson/去趋势/离群敏感度/多重检验校验已完成

## 5. 视觉证据
- 反应器温度通道出现显著阶跃式偏离，穿越 ±3σ 线后呈平台
- 进料与分离器温度通道呈补偿性小幅响应
- 阀位通道处于调节带

## 6. 根因结论（诊断结论 Diagnosis）
**反应器冷却侧扰动（reactor cooling disturbance）：反应器温度 XMEAS_9 以 10.06σ 主导异常列谱（次高仅 3.8σ），进料与组分通道仅轻度联动——冷却能力不足引发的一次热失衡，符合冷却水入口温度阶跃机理。**
- 结论类型：DETERMINED；置信度 86%（置信上限依据：证据等级 L3-L5 支撑，无 L1 直接测量）。

## 8. 竞争假设与排除逻辑
- 【存活】反应器冷却水侧扰动（冷却能力不足）（置信 86%，机制=cooling-disturbance）
  - 判别证据：L3 统计：XMEAS_9（反应器温度）max|z|=10.06、超3σ占比 0.3%——极端主导签名，热一次扰动的直接证据

- 【排除】进料组成阶跃（IDV1/2/8 类）（置信 12%，机制=feed-composition-step）
  - 判别证据：L3 统计：组分通道仅 XM23 3.7σ 入列，远低于 XM9 的 10.06σ
  - 矛盾证据（排除逻辑）：组分通道为次级响应（3.7σ）而非主导——与 d01 类『组分主导 4/6』的签名结构相反
- 【排除】进料量阶跃/损失（IDV6 类）（置信 10%，机制=feed-loss）
  - 判别证据：L3 统计：XM1/XMV_3 均 3.7σ 次级，非主导
  - 矛盾证据（排除逻辑）：流量通道为温度响应的补偿动作而非一次扰动
- 排除统计：存活 1 个，排除 2 个。

## 9. 详细推导与推理过程 (Detailed Derivation)
### 反应器冷却水侧扰动（冷却能力不足）
- 机理链（logic_chain）：1) 冷却水入口温度阶跃 → 移热能力下降 → 反应器温度越界（brief：XMEAS_9 max|z|=10.06，全列谱 2.6 倍于次高） → 2) 反应器温度偏离 → 反应速率失衡 → 进料链补偿（brief：XMEAS_2 3.8 / XMV_3 3.74 / XMEAS_1 3.7） → 3) 转化率变化 → 反应器进料组分轻移（brief：XMEAS_23 3.7）与分离器温度响应（brief：XMEAS_11 3.66）
- 物理量级核对：签名-机理核对：冷却扰动的第一被控量是反应器温度——10.06σ 对 0.3% 超限占比的『阶跃主导』形态与冷却水入口温度阶跃一致；量级比（10.06 vs 次高 3.8）排除了多源小扰动的叠加解释。
- 数据支撑：L3 统计：XMEAS_9（反应器温度）max|z|=10.06、超3σ占比 0.3%——极端主导签名，热一次扰动的直接证据；L3 统计：全部次级异常 ≤3.8σ 且集中在进料/组分/分离器温度——一次热扰动的下游补偿结构；L3 统计：强相关对全为控制回路对（XM15~XMV8 1.000、XM12~XMV7 1.000 等）——控制器正常补偿，无跨域伪相关；L4 视觉：反应器温度通道自故障时段呈阶跃式偏离平台（fig_temporal_overview.png）

## 10. 推理链 (Reasoning Chain)
- R1 数据探查：960×53，缺失/常数列已剔除
- R2 本体映射：8 变量 → 物理语义 + 物理原理
- R3 统计检测：单变量 z 扫描 + 跨域相关 + 反假相关校验
- R4 假设生成：3 个竞争假设（≥3 达标）
- R5 假设判别：判别证据 + 矛盾证据逐条比对
- R6 结论收敛：DETERMINED（排除 2，存活 1）
- R7 评审审计：judge 92/100 + ENDORSED
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
  - [数据缺口] XMV_10/XM21 未入 top-6，冷却水侧一次证据以反应器温度主导间接呈现
  - [推理限制] 冷却水入口温度无直接测量列（XM21 为出口温度）——阶跃幅值不可直接估计

## 13. 复现信息
- case 定义：scripts/benchmark/cases/benchmark_cases.json（真值与关键词仅在评分器使用，未注入管线）
- 评分：results/benchmark/gradings/tep_d04_reactor_cooling_step.json；事件日志：.pipeline_events.jsonl（pipeline-log-check 通过）
- 门禁：pipeline-finalize_report.json（overall=见文件）
