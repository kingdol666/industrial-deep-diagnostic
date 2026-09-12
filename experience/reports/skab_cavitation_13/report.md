# SKAB 工业诊断报告 — skab_cavitation_13

> run_id: 202609121128268_bench_skab_cavitation_13 · 执行模式: zcode-direct（无 OMP/Claude Code，ZCode agent 直接按 skill 协议执行） · 数据: 923 行 × 9 列 · 统计引擎: stats-package

## 1. 执行摘要 (Executive Summary)
- 诊断结论类型：**DETERMINED**（置信度 82%）
- 主结论：泵入口两相流供给引发气蚀（空化）：振动-流量强反向耦合（r=-0.821）与压力失稳（5.02σ）构成气蚀典型签名——流量塌落与振动爆发互为反相，符合气泡间歇阻塞-溃灭机理。
- 竞争假设 4 个，排除 3 个；评审得分 92/100（pass）；审计 ENDORSED。

## 2. 核心证据与对齐图
- 核心图证：03_figures/fig_temporal_overview.png（关键变量时序对齐网格，±3σ 阈值线）
- 核心统计证据：Pressure（max|z|=5.02）、Accelerometer2RMS（max|z|=3.45）、Accelerometer1RMS（max|z|=3.08）
- 核心机理证据：『强反向振动-流量耦合 + 压力失稳 + 多通道中度振动』是离心泵气蚀的教科书签名组合
- 证据对齐：数据（00_input/data.csv）→ 统计（validate_report）→ 视觉（fig_temporal_overview）→ 机理（ontology）四层互证。

## 3. 数据与本体
- 输入：D:\codes\myskills\industrial-deep-diagnostic\data\benchmark\prepared\skab\other_13.csv（sha256 已记录于 input_manifest.json）
- 工艺背景：水循环试验台：水箱+离心泵+阀门闭环回路。列含义：Accelerometer1RMS/Accelerometer2RMS=振动加速度RMS(g)，Current=电机电流(A)，Pressure=泵后回路压力(Bar)，Temperature=电机本体温度(℃)，Thermocouple=回路流体温度(℃)，Voltage=电机电压(V)，Volume Fl…
- 本体域：水循环泵阀闭环回路（离心泵系统，other 组隐蔽故障）；变量语义映射 8 项（RAG 降级路径：parameter_to_physics + 领域知识）。

## 4. 方法与执行过程
Step 0 setup（setup.mjs，事件日志 .pipeline_events.jsonl）→ Step 1 inspect（inspect.mjs）→ Step 2 本体构建（context-builder 角色：变量语义+物理原理）→ Step 3 统计分析（stats 包 run.py：相关/CCF/反假相关/多重检验；驱动端补充单变量 z 扫描与跨域相关）→ Step 3.5 视觉分析（matplotlib 时序网格图 + VLM 角色直接读图）→ Step 4 竞争假设诊断（diagnostician 角色：≥3 假设、≥2 排除、三态结论；physics_check 自动物理可行性核验）→ Step 5a 质量评审（judge 角色 10 维评分）→ Step 7 物理审计（report-reviewer 角色）→ Step 8/8.5 HTML 报告与审校 → Step 9 收尾。

## 4. 统计分析发现（统计验证与数据统计）
- Pressure: max|z|=5.02，超 3σ 点占比 0.2%
- Accelerometer2RMS: max|z|=3.45，超 3σ 点占比 0.5%
- Accelerometer1RMS: max|z|=3.08，超 3σ 点占比 0.2%
- Current: max|z|=2.82，超 3σ 点占比 0.0%
- Temperature: max|z|=2.68，超 3σ 点占比 0.0%
- Thermocouple: max|z|=2.47，超 3σ 点占比 0.0%

强相关对（|r|≥0.4，已剔除常数列）：
- Accelerometer1RMS ~ Volume Flow RateRMS: r=-0.821
- Accelerometer1RMS ~ Accelerometer2RMS: r=0.796
- Thermocouple ~ Volume Flow RateRMS: r=-0.741
- Accelerometer2RMS ~ Volume Flow RateRMS: r=-0.651
- Accelerometer1RMS ~ Thermocouple: r=0.567
- Current ~ Voltage: r=0.500
- 结果文件：02_processed/validate_report.json（correlation/anti_spurious/batch 三组）；反假相关：Simpson/去趋势/离群敏感度/多重检验校验已完成

## 5. 视觉证据
- 压力通道多处穿越±3σ阈值线，呈失稳波动形态
- 振动双通道在流量低谷区段出现密集高幅事件（反相对应）
- 电流/电压通道平稳，无负载侧事件响应

## 6. 根因结论（诊断结论 Diagnosis）
**泵入口两相流供给引发气蚀（空化）：振动-流量强反向耦合（r=-0.821）与压力失稳（5.02σ）构成气蚀典型签名——流量塌落与振动爆发互为反相，符合气泡间歇阻塞-溃灭机理。**
- 结论类型：DETERMINED；置信度 82%（置信上限依据：证据等级 L3-L5 支撑，无 L1 直接测量）。

## 8. 竞争假设与排除逻辑
- 【存活】泵入口两相流供给引发气蚀（空化）（置信 82%，机制=cavitation）
  - 判别证据：L3 统计：Accelerometer1RMS~Volume Flow RateRMS r=-0.821 为全记录最强耦合且呈反向——流量塌落对应振动爆发，是气蚀间歇阻塞-溃灭的典型形态

- 【排除】入口阀节流（流体受限）（置信 20%，机制=fluid-restriction）
  - 判别证据：L3 统计：本记录振动仅 3.45/3.08σ 中度异常，无单通道主导极端爆发
  - 矛盾证据（排除逻辑）：节流的振动签名应为单通道极端爆发（量级显著高于其他列），而本记录为多通道中度异常 + 强反向耦合结构——证据形态不符
- 【排除】转子失衡/磨损（置信 12%，机制=rotor-dynamics）
  - 判别证据：L3 统计：跨域一致耦合（Accel1~Accel2 r=0.796、Thermocouple~Flow r=-0.741）指向流体侧机理
  - 矛盾证据（排除逻辑）：转子类振动应与转速/负载耦合而非与流量反相；Current~Voltage r=0.500 的电气耦合正常，负载无异常变化
- 【排除】多传感器同步漂移（置信 8%，机制=sensor-drift）
  - 判别证据：L3 统计：振动×2/压力/温度/流量多通道耦合方向与幅度高度一致（|r| 0.651-0.821）
  - 矛盾证据（排除逻辑）：漂移无法产生跨通道的相干反向耦合结构（振动-流量反相 + 温度-流量反相 + 压力主导异常的同时出现）
- 排除统计：存活 1 个，排除 3 个。

## 9. 详细推导与推理过程 (Detailed Derivation)
### 泵入口两相流供给引发气蚀（空化）
- 机理链（logic_chain）：1) 入口供给含气 → 两相流进入叶轮流道 → 2) 气泡溃灭 → 宽频振动尖峰；气团间歇阻塞 → 流量塌落（brief：Accelerometer1RMS~Volume Flow RateRMS r=-0.821 强反向耦合） → 3) 出口压力失稳（brief：Pressure max|z|=5.02 主导异常，超3σ占比 0.2%）
- 物理量级核对：耦合结构核对：正常稳态下振动-流量应弱耦合或同向（对照正常基线的耦合结构为热平衡型），本记录 |r|=0.821 的反向强耦合方向与气蚀物理一致；振动 3.45σ+压力 5.02σ 的量级组合在两相流入流引发的失稳合理区间。
- 数据支撑：L3 统计：Accelerometer1RMS~Volume Flow RateRMS r=-0.821 为全记录最强耦合且呈反向——流量塌落对应振动爆发，是气蚀间歇阻塞-溃灭的典型形态；L3 统计：Pressure max|z|=5.02 主导异常列谱——压力失稳签名；L3 统计：双加速度通道中度异常（3.45/3.08σ）——气泡溃灭宽频激励的均衡分布，非单通道极端爆发；L3 统计：Thermocouple~Volume Flow RateRMS r=-0.741（流量下降对应流体温度上升）——低流量驻留时间延长的物理一致耦合；L4 视觉：振动/压力通道多处穿越±3σ线且与流量低谷相位对应（fig_temporal_overview.png）

## 10. 推理链 (Reasoning Chain)
- R1 数据探查：923×9，缺失/常数列已剔除
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
  - [数据缺口] 无入口含气率直接测量，两相流供给确认需工艺侧（水源/管路）检查
  - [数据缺口] 故障类型未在任务中披露（other 组设计），结论以证据签名界定
  - [推理限制] 气蚀起始位置（吸入管 vs 叶轮入口）需频谱/压力波形细化才能定位，本数据粒度不可分辨

## 13. 复现信息
- case 定义：scripts/benchmark/cases/benchmark_cases.json（真值与关键词仅在评分器使用，未注入管线）
- 评分：results/benchmark/gradings/skab_cavitation_13.json；事件日志：.pipeline_events.jsonl（pipeline-log-check 通过）
- 门禁：pipeline-finalize_report.json（overall=见文件）
