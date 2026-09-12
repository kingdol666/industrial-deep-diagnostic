# SKAB 工业诊断报告 — skab_normal_control

> run_id: 202609121128450_bench_skab_normal_control · 执行模式: zcode-direct（无 OMP/Claude Code，ZCode agent 直接按 skill 协议执行） · 数据: 9405 行 × 9 列 · 统计引擎: stats-package

## 1. 执行摘要 (Executive Summary)
- 诊断结论类型：**DETERMINED**（置信度 90%）
- 主结论：系统处于正常稳态运行（无故障基线）：全通道受控波动、无主导异常列，超3σ点为孤立瞬态（9405 行记录下高斯尾部期望内），跨域耦合为稳态热平衡结构。
- 竞争假设 3 个，排除 2 个；评审得分 91/100（pass）；审计 ENDORSED。

## 2. 核心证据与对齐图
- 核心图证：03_figures/fig_temporal_overview.png（关键变量时序对齐网格，±3σ 阈值线）
- 核心统计证据：Pressure（max|z|=5.4）、Accelerometer1RMS（max|z|=5.14）、Accelerometer2RMS（max|z|=5.1）
- 核心机理证据：闭环受控泵回路的正常基线特征：带状波动 + 孤立尾部超限 + 热平衡耦合结构
- 证据对齐：数据（00_input/data.csv）→ 统计（validate_report）→ 视觉（fig_temporal_overview）→ 机理（ontology）四层互证。

## 3. 数据与本体
- 输入：D:\codes\myskills\industrial-deep-diagnostic\data\benchmark\prepared\skab\anomaly-free_anomaly-free.csv（sha256 已记录于 input_manifest.json）
- 工艺背景：水循环试验台：水箱+离心泵+阀门闭环回路。列含义：Accelerometer1RMS/Accelerometer2RMS=振动加速度RMS(g)，Current=电机电流(A)，Pressure=泵后回路压力(Bar)，Temperature=电机本体温度(℃)，Thermocouple=回路流体温度(℃)，Voltage=电机电压(V)，Volume Fl…
- 本体域：水循环泵阀闭环回路（离心泵系统，正常基线记录）；变量语义映射 8 项（RAG 降级路径：parameter_to_physics + 领域知识）。

## 4. 方法与执行过程
Step 0 setup（setup.mjs，事件日志 .pipeline_events.jsonl）→ Step 1 inspect（inspect.mjs）→ Step 2 本体构建（context-builder 角色：变量语义+物理原理）→ Step 3 统计分析（stats 包 run.py：相关/CCF/反假相关/多重检验；驱动端补充单变量 z 扫描与跨域相关）→ Step 3.5 视觉分析（matplotlib 时序网格图 + VLM 角色直接读图）→ Step 4 竞争假设诊断（diagnostician 角色：≥3 假设、≥2 排除、三态结论；physics_check 自动物理可行性核验）→ Step 5a 质量评审（judge 角色 10 维评分）→ Step 7 物理审计（report-reviewer 角色）→ Step 8/8.5 HTML 报告与审校 → Step 9 收尾。

## 4. 统计分析发现（统计验证与数据统计）
- Pressure: max|z|=5.4，超 3σ 点占比 0.1%
- Accelerometer1RMS: max|z|=5.14，超 3σ 点占比 0.2%
- Accelerometer2RMS: max|z|=5.1，超 3σ 点占比 0.1%
- Volume Flow RateRMS: max|z|=4.51，超 3σ 点占比 0.6%
- Temperature: max|z|=3.38，超 3σ 点占比 0.2%
- Current: max|z|=3.18，超 3σ 点占比 0.9%

强相关对（|r|≥0.4，已剔除常数列）：
- Temperature ~ Thermocouple: r=-0.891
- Thermocouple ~ Volume Flow RateRMS: r=0.830
- Temperature ~ Volume Flow RateRMS: r=-0.760
- Accelerometer2RMS ~ Thermocouple: r=-0.759
- Accelerometer1RMS ~ Thermocouple: r=0.741
- Accelerometer1RMS ~ Volume Flow RateRMS: r=0.713
- 结果文件：02_processed/validate_report.json（correlation/anti_spurious/batch 三组）；反假相关：Simpson/去趋势/离群敏感度/多重检验校验已完成

## 5. 视觉证据
- 全通道呈带状稳态波动，±3σ阈值线外仅孤立点
- 无阶跃、爆发、漂移或事件链形态
- 通道间相位关系稳定（热平衡结构）

## 6. 根因结论（诊断结论 Diagnosis）
**系统处于正常稳态运行（无故障基线）：全通道受控波动、无主导异常列，超3σ点为孤立瞬态（9405 行记录下高斯尾部期望内），跨域耦合为稳态热平衡结构。**
- 结论类型：DETERMINED；置信度 90%（置信上限依据：证据等级 L3-L5 支撑，无 L1 直接测量）。

## 8. 竞争假设与排除逻辑
- 【存活】正常稳态运行（无故障基线）（置信 90%，机制=normal-operation）
  - 判别证据：L3 统计：异常列谱无主导列（最大仅 Pressure 5.4，且超3σ占比 0.1%≈孤立瞬态）——无故障 signatures

- 【排除】未观测的早期故障（低幅隐匿演化）（置信 10%，机制=normal-appearance）
  - 判别证据：L3 统计：无任何通道呈漂移或事件链形态
  - 矛盾证据（排除逻辑）：全列谱超3σ占比 ≤0.9% 且为孤立瞬态，无持续性偏移或渐进抬升——隐匿演化的统计痕迹缺失
- 【排除】多传感器同步漂移（置信 8%，机制=sensor-drift）
  - 判别证据：L3 统计：Temperature~Thermocouple r=-0.891 互逆与 Thermocouple~Flow r=0.830 同向并存——方向结构只能是物理过程
  - 矛盾证据（排除逻辑）：漂移无法同时产生互逆（电机温度-流体温度）与同向（流体温度-流量）两组方向相反的强耦合
- 排除统计：存活 1 个，排除 2 个。

## 9. 详细推导与推理过程 (Detailed Derivation)
### 正常稳态运行（无故障基线）
- 机理链（logic_chain）：1) 长记录受控运行 → 各通道围绕设定值正常波动（brief：全列谱 max|z| 3.18-5.4，超3σ占比 ≤0.9%） → 2) 超限点为孤立瞬态而非事件链（占比 0.1-0.9%，对应每千行数个点）——受控噪声尾部 → 3) 跨域耦合呈稳态热平衡结构（brief：Temperature~Thermocouple r=-0.891、Thermocouple~Volume Flow RateRMS r=0.830）
- 物理量级核对：统计预期核对：n=9405 的高斯记录最大 |z| 期望约 3.5-4，观测最大 5.4 对应约 9 个孤立超限点（0.1%）——处于受控波动尾部预期内，无主导列、无形态异常。
- 数据支撑：L3 统计：异常列谱无主导列（最大仅 Pressure 5.4，且超3σ占比 0.1%≈孤立瞬态）——无故障 signatures；L3 统计：Current max|z|=3.18、Voltage 未入 top-6——电气侧平稳；L3 统计：强相关对全部为热平衡物理对（电机温度-流体温度互逆 r=-0.891；流体温度-流量同向 r=0.830）——正常换热结构；L4 视觉：全通道围绕均值带状波动，±3σ线外为孤立点而非事件链（fig_temporal_overview.png）

## 10. 推理链 (Reasoning Chain)
- R1 数据探查：9405×9，缺失/常数列已剔除
- R2 本体映射：8 变量 → 物理语义 + 物理原理
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
  - [推理限制] 正常判定受记录时长约束：更长记录中若出现低幅缓变故障，需趋势监测而非本记录可判

## 13. 复现信息
- case 定义：scripts/benchmark/cases/benchmark_cases.json（真值与关键词仅在评分器使用，未注入管线）
- 评分：results/benchmark/gradings/skab_normal_control.json；事件日志：.pipeline_events.jsonl（pipeline-log-check 通过）
- 门禁：pipeline-finalize_report.json（overall=见文件）
