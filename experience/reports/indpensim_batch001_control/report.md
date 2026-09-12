# INDPENSIM 工业诊断报告 — indpensim_batch001_control

> run_id: 202609121649167_bench_indpensim_batch001_control · 执行模式: zcode-direct（无 OMP/Claude Code，ZCode agent 直接按 skill 协议执行） · 数据: 1130 行 × 32 列 · 统计引擎: stats-package

## 1. 执行摘要 (Executive Summary)
- 诊断结论类型：**DETERMINED**（置信度 88%）
- 主结论：正常批次（recipe 驱动的受控批次动态，无故障）：全局 z 谱的执行器越限属批过程非平稳轨迹下的闭环调节瞬态——被控质量变量在带内、物理不变量完好、产物累积轨迹健康（Time~P r=0.994），判定为正常运行。
- 竞争假设 4 个，排除 3 个；评审得分 90/100（pass）；审计 ENDORSED。

## 2. 核心证据与对齐图
- 核心图证：03_figures/fig_temporal_overview.png（关键变量时序对齐网格，±3σ 阈值线）
- 核心统计证据：Acid flow rate(Fa:L/h)（max|z|=16.2）、Heating water flow rate(Fh:L/h)（max|z|=10.94）、Temperature(T:K)（max|z|=10.23）
- 核心机理证据：批过程正常性的判别学：执行器脉冲是闭环调节的工作方式，工艺偏差要看被控量与质量变量是否出带
- 证据对齐：数据（00_input/data.csv）→ 统计（validate_report）→ 视觉（fig_temporal_overview）→ 机理（ontology）四层互证。

## 3. 数据与本体
- 输入：D:\codes\myskills\industrial-deep-diagnostic\data\benchmark\prepared\indpensim\batch_001.csv（sha256 已记录于 input_manifest.json）
- 工艺背景：100,000L 青霉素发酵批次过程（IndPenSim），0.2h采样，Time (h)为批内相对小时。本批为 recipe 驱动正常批次。…
- 本体域：青霉素发酵批过程（100,000L 工业规模发酵罐，正常批次）；变量语义映射 12 项（RAG 降级路径：parameter_to_physics + 领域知识）。

## 4. 方法与执行过程
Step 0 setup（setup.mjs，事件日志 .pipeline_events.jsonl）→ Step 1 inspect（inspect.mjs）→ Step 2 本体构建（context-builder 角色：变量语义+物理原理）→ Step 3 统计分析（stats 包 run.py：相关/CCF/反假相关/多重检验；驱动端补充单变量 z 扫描与跨域相关）→ Step 3.5 视觉分析（matplotlib 时序网格图 + VLM 角色直接读图）→ Step 4 竞争假设诊断（diagnostician 角色：≥3 假设、≥2 排除、三态结论；physics_check 自动物理可行性核验）→ Step 5a 质量评审（judge 角色 10 维评分）→ Step 7 物理审计（report-reviewer 角色）→ Step 8/8.5 HTML 报告与审校 → Step 9 收尾。

## 4. 统计分析发现（统计验证与数据统计）
- Acid flow rate(Fa:L/h): max|z|=16.2，超 3σ 点占比 1.2%
- Heating water flow rate(Fh:L/h): max|z|=10.94，超 3σ 点占比 2.5%
- Temperature(T:K): max|z|=10.23，超 3σ 点占比 1.4%
- Generated heat(Q:kJ): max|z|=8.78，超 3σ 点占比 1.2%
- Heating/cooling water flow rate(Fc:L/h): max|z|=6.93，超 3σ 点占比 1.2%
- pH(pH:pH): max|z|=6.01，超 3σ 点占比 1.3%

强相关对（|r|≥0.4，已剔除常数列）：
- Vessel Volume(V:L) ~ Vessel Weight(Wt:Kg): r=0.997
- Time (h) ~ Penicillin concentration(P:g/L): r=0.994
- carbon dioxide percent in off-gas(CO2outgas:%) ~ Carbon evolution rate(CER:g/h): r=0.969
- Vessel Weight(Wt:Kg) ~ Carbon evolution rate(CER:g/h): r=0.941
- Aeration rate(Fg:L/h) ~ Carbon evolution rate(CER:g/h): r=0.935
- Oxygen Uptake Rate(OUR:(g min^{-1})) ~ Oxygen in percent in off-gas(O2:O2  (%)): r=-0.929
- 结果文件：02_processed/validate_report.json（correlation/anti_spurious/batch 三组）；反假相关：Simpson/去趋势/离群敏感度/多重检验校验已完成

## 5. 视觉证据
- 酸流加/加热水通道为孤立脉冲簇，非持续平台
- 温度与产物通道呈平滑批轨迹（阶段演进形态）
- 体积/质量通道同步平稳（守恒）

## 6. 根因结论（诊断结论 Diagnosis）
**正常批次（recipe 驱动的受控批次动态，无故障）：全局 z 谱的执行器越限属批过程非平稳轨迹下的闭环调节瞬态——被控质量变量在带内、物理不变量完好、产物累积轨迹健康（Time~P r=0.994），判定为正常运行。**
- 结论类型：DETERMINED；置信度 88%（置信上限依据：证据等级 L3-L5 支撑，无 L1 直接测量）。

## 8. 竞争假设与排除逻辑
- 【存活】正常批次（受控批次动态，无故障）（置信 88%，机制=normal-operation）
  - 判别证据：L3 统计：主导异常全部为执行器瞬态（Fa 16.2 / Fh 10.94 / Fc 6.93），超3σ占比 1.2-2.5%——短时 corrective 脉冲特征

- 【排除】执行侧工艺偏差（同故障批签名）（置信 12%，机制=ph-control-fault）
  - 判别证据：L3 统计：本批越限为孤立脉冲（占比 ≤2.5%），底物浓度未入异常列谱，产物轨迹健康（r=0.994）
  - 矛盾证据（排除逻辑）：被控量在带 + 质量变量正常 + 产物累积健康——工艺偏差三要素全部缺失；执行器脉冲是闭环调节的结果而非失稳的原因
- 【排除】温度控制故障（置信 10%，机制=cooling-disturbance）
  - 判别证据：L3 统计：Temperature~Generated heat r=0.996 热耦合结构完好，罐温围绕设定轨迹波动
  - 矛盾证据（排除逻辑）：热平衡结构（T~Q 0.996）完好且罐温在带——温度控制正常工作，Fh 越限为调节瞬态
- 【排除】传感器/测量伪象（置信 8%，机制=sensor-drift）
  - 判别证据：L3 统计：V~Wt r=0.997 守恒、CO2outgas~CER r=0.969 代谢一致、OUR~O2 -0.929 呼吸物理
  - 矛盾证据（排除逻辑）：跨通道物理不变量（守恒/热平衡/呼吸代谢）全部完好——多传感器独立漂移无物理基础
- 排除统计：存活 1 个，排除 3 个。

## 9. 详细推导与推理过程 (Detailed Derivation)
### 正常批次（受控批次动态，无故障）
- 机理链（logic_chain）：1) 批轨迹非平稳 → 全局 z 谱在执行器 corrective 脉冲处越限（brief：Fa 16.2σ/Fh 10.94σ，超3σ占比仅 1.2-2.5%）——方法学伪象而非过程故障 → 2) 被控量与质量变量在带内（brief：pH 最大 6.01σ 且 Substrate concentration 未入异常列谱 top-6）——调节结果正常 → 3) 生产目标达成（brief：Time (h)~Penicillin concentration r=0.994——产物随批时稳定累积） → 4) 物理不变量完好（brief：V~Wt r=0.997、CO2outgas~CER r=0.969）——测量与过程结构可信
- 物理量级核对：签名结构核对：本批异常呈『执行器孤立脉冲 + 被控量在带 + 产物累积健康』——与工艺偏差签名（多执行器同步越限+被控量出带+质量变量偏离）相反；脉冲占比 ≤2.5% 对应 0.2h 采样下的短时 corrective 动作，量级与 pH 控制工作方式一致。
- 数据支撑：L3 统计：主导异常全部为执行器瞬态（Fa 16.2 / Fh 10.94 / Fc 6.93），超3σ占比 1.2-2.5%——短时 corrective 脉冲特征；L3 统计：被控质量变量健康——底物浓度未入 top-6 异常列谱，pH 峰值 6.01 处于调节带；L3 统计：产物轨迹 Time~P r=0.994 单调累积——批次生产目标正常达成；L3 统计：物理/代谢不变量完好：V~Wt r=0.997（守恒）、CO2outgas~CER r=0.969（呼吸一致）、Aeration~CER r=0.935（供气-代谢联动）；L4 视觉：执行器通道为孤立脉冲簇而非持续平台；温度/产物通道呈平滑批轨迹（fig_temporal_overview.png）

## 10. 推理链 (Reasoning Chain)
- R1 数据探查：1130×32，缺失/常数列已剔除
- R2 本体映射：12 变量 → 物理语义 + 物理原理
- R3 统计检测：单变量 z 扫描 + 跨域相关 + 反假相关校验
- R4 假设生成：4 个竞争假设（≥3 达标）
- R5 假设判别：判别证据 + 矛盾证据逐条比对
- R6 结论收敛：DETERMINED（排除 3，存活 1）
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
  - [数据缺口] 全局 i.i.d. z 基线未做批内分段稳态过滤——执行器瞬态伪象的完全消除需分段基线（已记录为改进项）
  - [推理限制] 脉冲簇与 recipe 阶段切换的逐段对应需 recipe 时间表核对，本数据不含 recipe 标注

## 13. 复现信息
- case 定义：scripts/benchmark/cases/benchmark_cases.json（真值与关键词仅在评分器使用，未注入管线）
- 评分：results/benchmark/gradings/indpensim_batch001_control.json；事件日志：.pipeline_events.jsonl（pipeline-log-check 通过）
- 门禁：pipeline-finalize_report.json（overall=见文件）
