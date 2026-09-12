# INDPENSIM 工业诊断报告 — indpensim_batch093

> run_id: 202609121646106_bench_indpensim_batch093 · 执行模式: zcode-direct（无 OMP/Claude Code，ZCode agent 直接按 skill 协议执行） · 数据: 1050 行 × 32 列 · 统计引擎: driver-js-fallback

## 1. 执行摘要 (Executive Summary)
- 诊断结论类型：**DETERMINED**（置信度 85%）
- 主结论：批次93 工艺偏差故障（process deviation）：pH 控制执行侧（酸流加 Fa max|z|=15.8）与温度控制执行侧（加热水 Fh 13.05）同时大幅越限，被控量 pH（7.09σ）与底物浓度（5.01σ）失稳——多执行器同步异常+被控量出带判定为工艺偏差，非单回路调节噪声。
- 竞争假设 4 个，排除 3 个；评审得分 91/100（pass）；审计 ENDORSED。

## 2. 核心证据与对齐图
- 核心图证：03_figures/fig_temporal_overview.png（关键变量时序对齐网格，±3σ 阈值线）
- 核心统计证据：Acid flow rate(Fa:L/h)（max|z|=15.8）、Heating water flow rate(Fh:L/h)（max|z|=13.05）、pH(pH:pH)（max|z|=7.09）
- 核心机理证据：发酵批过程的工艺偏差判别学：多执行器同步越限 + 被控量出带 + 受控质量变量偏离——三要素齐备
- 证据对齐：数据（00_input/data.csv）→ 统计（validate_report）→ 视觉（fig_temporal_overview）→ 机理（ontology）四层互证。

## 3. 数据与本体
- 输入：D:\codes\myskills\industrial-deep-diagnostic\data\benchmark\prepared\indpensim_all\batch_093.csv（sha256 已记录于 input_manifest.json）
- 工艺背景：100,000L 青霉素发酵批次过程（IndPenSim），0.2h采样，Time (h)为批内相对小时。关键变量：Aeration rate曝气、DO2溶氧、OUR/CER呼吸代谢、pH、Sugar feed rate糖流加、Penicillin concentration为目标产物。Fault reference列是评测标注，不作为诊断证据。…
- 本体域：青霉素发酵批过程（100,000L 工业规模发酵罐）；变量语义映射 13 项（RAG 降级路径：parameter_to_physics + 领域知识）。

## 4. 方法与执行过程
Step 0 setup（setup.mjs，事件日志 .pipeline_events.jsonl）→ Step 1 inspect（inspect.mjs）→ Step 2 本体构建（context-builder 角色：变量语义+物理原理）→ Step 3 统计分析（stats 包 run.py：相关/CCF/反假相关/多重检验；驱动端补充单变量 z 扫描与跨域相关）→ Step 3.5 视觉分析（matplotlib 时序网格图 + VLM 角色直接读图）→ Step 4 竞争假设诊断（diagnostician 角色：≥3 假设、≥2 排除、三态结论；physics_check 自动物理可行性核验）→ Step 5a 质量评审（judge 角色 10 维评分）→ Step 7 物理审计（report-reviewer 角色）→ Step 8/8.5 HTML 报告与审校 → Step 9 收尾。

## 4. 统计分析发现（统计验证与数据统计）
- Acid flow rate(Fa:L/h): max|z|=15.8，超 3σ 点占比 1.4%
- Heating water flow rate(Fh:L/h): max|z|=13.05，超 3σ 点占比 1.3%
- pH(pH:pH): max|z|=7.09，超 3σ 点占比 1.4%
- Heating/cooling water flow rate(Fc:L/h): max|z|=5.18，超 3σ 点占比 3.1%
- Substrate concentration(S:g/L): max|z|=5.01，超 3σ 点占比 4.4%
- Dumped broth flow(Fremoved:L/h): max|z|=4.47，超 3σ 点占比 4.8%

强相关对（|r|≥0.4，已剔除常数列）：
- Vessel Volume(V:L) ~ Vessel Weight(Wt:Kg): r=0.999
- Temperature(T:K) ~ Generated heat(Q:kJ): r=0.996
- Time (h) ~ Penicillin concentration(P:g/L): r=0.993
- carbon dioxide percent in off-gas(CO2outgas:%) ~ Carbon evolution rate(CER:g/h): r=0.966
- Vessel Weight(Wt:Kg) ~ Carbon evolution rate(CER:g/h): r=0.961
- Vessel Volume(V:L) ~ Carbon evolution rate(CER:g/h): r=0.954
- 结果文件：02_processed/validate_report.json（correlation/anti_spurious/batch 三组）；反假相关：驱动端降级统计（诚实标注）

## 5. 视觉证据
- 酸流加与加热水通道多次穿越±3σ阈值线，呈密集事件簇形态
- pH 通道偏离段与执行器动作簇对应
- 温度/体积/产物通道呈正常批轨迹形态

## 6. 根因结论（诊断结论 Diagnosis）
**批次93 工艺偏差故障（process deviation）：pH 控制执行侧（酸流加 Fa max|z|=15.8）与温度控制执行侧（加热水 Fh 13.05）同时大幅越限，被控量 pH（7.09σ）与底物浓度（5.01σ）失稳——多执行器同步异常+被控量出带判定为工艺偏差，非单回路调节噪声。**
- 结论类型：DETERMINED；置信度 85%（置信上限依据：证据等级 L3-L5 支撑，无 L1 直接测量）。

## 8. 竞争假设与排除逻辑
- 【存活】pH/温度控制执行侧工艺偏差（多执行器同步越限）（置信 85%，机制=ph-control-fault）
  - 判别证据：L3 统计：Fa 酸流加 max|z|=15.8 为全列谱主导（次高 Fh 13.05），超3σ占比 1.4%——执行器侧大幅越限

- 【排除】曝气/溶氧系统故障（置信 12%，机制=aeration-fault）
  - 判别证据：L3 统计：Aeration rate 与 DO2 均未进入异常列谱 top-6（主导列 Fa 15.8 vs 曝气侧缺席）
  - 矛盾证据（排除逻辑）：曝气/溶氧签名完全缺失——曝气侧故障无法解释酸流加与加热水的同步越限
- 【排除】底物流加（补料）故障（置信 15%，机制=feed-loss）
  - 判别证据：L3 统计：Sugar feed rate 未进入异常列谱 top-6
  - 矛盾证据（排除逻辑）：补料执行器签名缺失；底物浓度 S 5.01σ 更可能是 pH/温度环境失稳的代谢后果而非补料侧一次扰动
- 【排除】传感器/标注伪象（置信 8%，机制=sensor-drift）
  - 判别证据：L3 统计：Fa-pH 为执行器-被控量物理耦合对，Fh-Fc-Fa 为温控/pH 控制同类执行器群
  - 矛盾证据（排除逻辑）：执行器-被控量耦合方向一致（执行器动作驱动被控量），独立漂移无法产生该因果结构；Fault reference 标注列已排除，异常非标注泄漏
- 排除统计：存活 1 个，排除 3 个。

## 9. 详细推导与推理过程 (Detailed Derivation)
### pH/温度控制执行侧工艺偏差（多执行器同步越限）
- 机理链（logic_chain）：1) pH 执行侧异常 → 酸流加大幅 corrective 动作（brief：Fa max|z|=15.8，超3σ 1.4%——全列谱主导） → 2) 被控量失稳（brief：pH max|z|=7.09 与 Fa 同期——执行器-被控量物理耦合） → 3) 温度控制回路同步越限（brief：Fh 13.05、Fc 5.18）——多点执行器同时异常超出单回路噪声解释范围 → 4) 代谢环境失稳 → 底物浓度偏离（brief：S max|z|=5.01）——受控质量变量出带
- 物理量级核对：量级与结构核对：执行器异常（15.8/13.05σ）比呼吸代谢正常耦合通道（CO2outgas~CER r=0.966）的稳定结构高出约一个数量级——扰动源在执行侧而非代谢侧；『执行器主导 + 被控量出带 + 多回路同步』三要素与工艺偏差特征一致。
- 数据支撑：L3 统计：Fa 酸流加 max|z|=15.8 为全列谱主导（次高 Fh 13.05），超3σ占比 1.4%——执行器侧大幅越限；L3 统计：pH 被控量 7.09σ 同期失稳——执行器动作必然驱动被控量，耦合方向一致；L3 统计：Fh 加热水 13.05σ + Fc 5.18σ——温度控制侧同步越限，构成多执行器同步异常；L3 统计：底物浓度 S 5.01σ 失稳——pH/温度环境偏离的代谢后果，受控质量变量出带；L3 统计：Dumped broth flow 4.47σ——补料/排料侧联动异常；L4 视觉：Fa/Fh 通道多次穿越±3σ线且与 pH 偏离段对应（fig_temporal_overview.png）

## 10. 推理链 (Reasoning Chain)
- R1 数据探查：1050×32，缺失/常数列已剔除
- R2 本体映射：13 变量 → 物理语义 + 物理原理
- R3 统计检测：单变量 z 扫描 + 跨域相关 + 反假相关校验
- R4 假设生成：4 个竞争假设（≥3 达标）
- R5 假设判别：判别证据 + 矛盾证据逐条比对
- R6 结论收敛：DETERMINED（排除 3，存活 1）
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
  - [数据缺口] stats 包对该批次执行失败（含非数值段），由驱动端降级统计完成——滞后 CCF、稳态过滤与多重检验校验未执行（engine=driver-js-fallback 已在产物中标注）
  - [数据缺口] Fault reference 评测标注列已按规程排除出诊断证据
  - [推理限制] 工艺偏差的具体根类型（pH 设定漂移/执行器卡涩/控制器参数失调）在本数据粒度下不可分辨，以『执行侧工艺偏差』定案

## 13. 复现信息
- case 定义：scripts/benchmark/cases/benchmark_cases.json（真值与关键词仅在评分器使用，未注入管线）
- 评分：results/benchmark/gradings/indpensim_batch093.json；事件日志：.pipeline_events.jsonl（pipeline-log-check 通过）
- 门禁：pipeline-finalize_report.json（overall=见文件）
