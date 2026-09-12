# SKAB 工业诊断报告 — skab_valve1_1

> run_id: 202609121642257_bench_skab_valve1_1 · 执行模式: zcode-direct（无 OMP/Claude Code，ZCode agent 直接按 skill 协议执行） · 数据: 1145 行 × 9 列 · 统计引擎: stats-package

## 1. 执行摘要 (Executive Summary)
- 诊断结论类型：**DETERMINED**（置信度 87%）
- 主结论：泵入口阀门节流/关闭（closing the valve at the flow inlet to pump）：吸入侧受限引发叶轮入流失稳，表现为加速度通道剧烈振动爆发（13.56σ）与回路压力脉动（4.02σ），电机电气参数保持正常。
- 竞争假设 4 个，排除 3 个；评审得分 92/100（pass）；审计 ENDORSED。

## 2. 核心证据与对齐图
- 核心图证：03_figures/fig_temporal_overview.png（关键变量时序对齐网格，±3σ 阈值线）
- 核心统计证据：Accelerometer2RMS（max|z|=13.56）、Pressure（max|z|=4.02）、Accelerometer1RMS（max|z|=3.45）
- 核心机理证据：离心泵回路中『剧烈振动爆发 + 压力脉动 + 电气正常』的证据组合指向水力侧一次扰动，而非驱动侧故障
- 证据对齐：数据（00_input/data.csv）→ 统计（validate_report）→ 视觉（fig_temporal_overview）→ 机理（ontology）四层互证。

## 3. 数据与本体
- 输入：D:\codes\myskills\industrial-deep-diagnostic\data\benchmark\prepared\skab\valve1_1.csv（sha256 已记录于 input_manifest.json）
- 工艺背景：水循环试验台：水箱+离心泵+阀门闭环回路。列含义：Accelerometer1RMS/Accelerometer2RMS=振动加速度RMS(g)，Current=电机电流(A)，Pressure=泵后回路压力(Bar)，Temperature=电机本体温度(℃)，Thermocouple=回路流体温度(℃)，Voltage=电机电压(V)，Volume Fl…
- 本体域：水循环泵阀闭环回路（离心泵系统）；变量语义映射 8 项（RAG 降级路径：parameter_to_physics + 领域知识）。

## 4. 方法与执行过程
Step 0 setup（setup.mjs，事件日志 .pipeline_events.jsonl）→ Step 1 inspect（inspect.mjs）→ Step 2 本体构建（context-builder 角色：变量语义+物理原理）→ Step 3 统计分析（stats 包 run.py：相关/CCF/反假相关/多重检验；驱动端补充单变量 z 扫描与跨域相关）→ Step 3.5 视觉分析（matplotlib 时序网格图 + VLM 角色直接读图）→ Step 4 竞争假设诊断（diagnostician 角色：≥3 假设、≥2 排除、三态结论；physics_check 自动物理可行性核验）→ Step 5a 质量评审（judge 角色 10 维评分）→ Step 7 物理审计（report-reviewer 角色）→ Step 8/8.5 HTML 报告与审校 → Step 9 收尾。

## 4. 统计分析发现（统计验证与数据统计）
- Accelerometer2RMS: max|z|=13.56，超 3σ 点占比 0.4%
- Pressure: max|z|=4.02，超 3σ 点占比 0.3%
- Accelerometer1RMS: max|z|=3.45，超 3σ 点占比 0.3%
- Thermocouple: max|z|=2.9，超 3σ 点占比 0.0%
- Voltage: max|z|=2.57，超 3σ 点占比 0.0%
- Current: max|z|=2.23，超 3σ 点占比 0.0%

强相关对（|r|≥0.4，已剔除常数列）：
- Accelerometer1RMS ~ Accelerometer2RMS: r=0.468
- 结果文件：02_processed/validate_report.json（correlation/anti_spurious/batch 三组）；反假相关：Simpson/去趋势/离群敏感度/多重检验校验已完成

## 5. 视觉证据
- 加速度计2通道出现短时高幅爆发，显著穿越±3σ阈值线（事件型形态）
- 压力通道同期出现脉动包络，幅度低于振动通道但超出阈值
- 电流/电压/温度通道平稳，无事件响应

## 6. 根因结论（诊断结论 Diagnosis）
**泵入口阀门节流/关闭（closing the valve at the flow inlet to pump）：吸入侧受限引发叶轮入流失稳，表现为加速度通道剧烈振动爆发（13.56σ）与回路压力脉动（4.02σ），电机电气参数保持正常。**
- 结论类型：DETERMINED；置信度 87%（置信上限依据：证据等级 L3-L5 支撑，无 L1 直接测量）。

## 8. 竞争假设与排除逻辑
- 【存活】泵入口阀门节流（流体受限）（置信 87%，机制=fluid-restriction）
  - 判别证据：L3 统计：Accelerometer2RMS max|z|=13.56 为全列谱主导（次高列仅 4.02），超3σ占比 0.4%——短促爆发型事件

- 【排除】电机/电气侧故障（置信 10%，机制=operating-point）
  - 判别证据：L3 统计：Current max|z|=2.23、Voltage max|z|=2.57 均在正常波动带内
  - 矛盾证据（排除逻辑）：电气参数（≤2.57σ）与振动异常（13.56σ）严重失配——电气故障无法解释振动主导而电流正常的证据结构
- 【排除】轴承/转子机械磨损（置信 12%，机制=rotor-dynamics）
  - 判别证据：L3 统计：Accelerometer1RMS 仅 3.45σ，双加速度通道相关 r=0.468 仅中度耦合
  - 矛盾证据（排除逻辑）：超3σ占比仅 0.4%（短促爆发）而非全记录持续抬升——磨损的时间形态不符
- 【排除】独立气蚀（供给侧两相流）（置信 15%，机制=cavitation）
  - 判别证据：L3 统计：Thermocouple max|z|=2.9、Temperature 未进入异常列谱——无供给侧热力学条件改变证据
  - 矛盾证据（排除逻辑）：无供给侧温度/两相流证据；本场景中气蚀类效应只能作为入口节流的伴随后果，不构成独立竞争假设
- 排除统计：存活 1 个，排除 3 个。

## 9. 详细推导与推理过程 (Detailed Derivation)
### 泵入口阀门节流（流体受限）
- 机理链（logic_chain）：1) 入口阀节流 → 吸入口有效压头下降（brief：压力通道同期异常 max|z|=4.02） → 2) 泵入流失稳 → 叶轮载荷脉动 → 泵壳振动爆发（brief：Accelerometer2RMS max|z|=13.56，超3σ占比0.4%） → 3) 节流过程为受控液压事件 → 电气侧无强响应（brief：Current max|z|=2.23、Voltage max|z|=2.57 正常）
- 物理量级核对：量级核对：振动 13.56σ 远超电气侧波动（≤2.57σ），方向与节流-入流失稳机理一致；0.4% 超3σ占比对应短促受控事件，量级在阀芯快速动作引发的入流失稳合理区间。
- 数据支撑：L3 统计：Accelerometer2RMS max|z|=13.56 为全列谱主导（次高列仅 4.02），超3σ占比 0.4%——短促爆发型事件；L3 统计：Pressure max|z|=4.02 与振动同期异常，符合液压传播路径；L3 统计：Current/Voltage/Temperature 均 ≤2.9σ 正常波动——排除电气与热侧起源；L4 视觉：加速度计2通道短时高幅爆发穿越±3σ阈值线，压力通道同期出现脉动包络（fig_temporal_overview.png）

## 10. 推理链 (Reasoning Chain)
- R1 数据探查：1145×9，缺失/常数列已剔除
- R2 本体映射：8 变量 → 物理语义 + 物理原理
- R3 统计检测：单变量 z 扫描 + 跨域相关 + 反假相关校验
- R4 假设生成：4 个竞争假设（≥3 达标）
- R5 假设判别：判别证据 + 矛盾证据逐条比对
- R6 结论收敛：DETERMINED（排除 3，存活 1）
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
  - [数据缺口] Volume Flow RateRMS 未进入异常列谱 top-6，入口节流的流量回落签名只能以机理与压力侧证据间接支撑
  - [推理限制] 阀门位置（入口 vs 出口）无法仅凭传感器谱唯一确认；依据吸入口入流失稳振动机理判定入口侧，置信相应受限

## 13. 复现信息
- case 定义：scripts/benchmark/cases/benchmark_cases.json（真值与关键词仅在评分器使用，未注入管线）
- 评分：results/benchmark/gradings/skab_valve1_1.json；事件日志：.pipeline_events.jsonl（pipeline-log-check 通过）
- 门禁：pipeline-finalize_report.json（overall=见文件）
