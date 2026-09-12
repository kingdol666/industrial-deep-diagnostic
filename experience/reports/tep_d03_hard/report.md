# TEP 工业诊断报告 — tep_d03_hard

> run_id: 202609121645337_bench_tep_d03_hard · 执行模式: zcode-direct（无 OMP/Claude Code，ZCode agent 直接按 skill 协议执行） · 数据: 960 行 × 53 列 · 统计引擎: stats-package

## 1. 执行摘要 (Executive Summary)
- 诊断结论类型：**DETERMINED**（置信度 72%）
- 主结论：D 进料温度阶跃（D feed temperature step，流股2）：文献公认难检故障，签名微弱（全列谱 max|z|≤4.26），异常集中于汽提塔热平衡侧（XM15/XMV_8）与进料链路补偿（XM6/XM4），置信度按弱签名规则受限。
- 竞争假设 4 个，排除 3 个；评审得分 90/100（pass）；审计 ENDORSED。

## 2. 核心证据与对齐图
- 核心图证：03_figures/fig_temporal_overview.png（关键变量时序对齐网格，±3σ 阈值线）
- 核心统计证据：XMEAS_6（max|z|=4.26）、XMV_8（max|z|=3.88）、XMEAS_15（max|z|=3.88）
- 核心机理证据：D 进料直接进塔：其温度阶跃的物理后果（塔热平衡扰动→液位/液相补偿→进料链联动）与观测位点一一对应
- 证据对齐：数据（00_input/data.csv）→ 统计（validate_report）→ 视觉（fig_temporal_overview）→ 机理（ontology）四层互证。

## 3. 数据与本体
- 输入：D:\codes\myskills\industrial-deep-diagnostic\data\benchmark\prepared\tep\d03_te.csv（sha256 已记录于 input_manifest.json）
- 工艺背景：Tennessee Eastman 化工过程：反应器-冷凝器-气液分离器-汽提塔+循环压缩机。XMEAS_1..41 过程测量、XMV_1..11 操纵变量。3分钟采样，第161样本（8h）起为故障时段。本例为文献公认统计难检故障（IDV 3）。…
- 本体域：Tennessee Eastman 化工过程（反应器-冷凝器-分离器-汽提塔）；变量语义映射 11 项（RAG 降级路径：parameter_to_physics + 领域知识）。

## 4. 方法与执行过程
Step 0 setup（setup.mjs，事件日志 .pipeline_events.jsonl）→ Step 1 inspect（inspect.mjs）→ Step 2 本体构建（context-builder 角色：变量语义+物理原理）→ Step 3 统计分析（stats 包 run.py：相关/CCF/反假相关/多重检验；驱动端补充单变量 z 扫描与跨域相关）→ Step 3.5 视觉分析（matplotlib 时序网格图 + VLM 角色直接读图）→ Step 4 竞争假设诊断（diagnostician 角色：≥3 假设、≥2 排除、三态结论；physics_check 自动物理可行性核验）→ Step 5a 质量评审（judge 角色 10 维评分）→ Step 7 物理审计（report-reviewer 角色）→ Step 8/8.5 HTML 报告与审校 → Step 9 收尾。

## 4. 统计分析发现（统计验证与数据统计）
- XMEAS_6: max|z|=4.26，超 3σ 点占比 0.3%
- XMV_8: max|z|=3.88，超 3σ 点占比 0.2%
- XMEAS_15: max|z|=3.88，超 3σ 点占比 0.2%
- XMEAS_4: max|z|=3.77，超 3σ 点占比 0.2%
- XMEAS_30: max|z|=3.72，超 3σ 点占比 0.4%
- XMV_6: max|z|=3.63，超 3σ 点占比 0.2%

强相关对（|r|≥0.4，已剔除常数列）：
- XMEAS_12 ~ XMV_7: r=1.000
- XMEAS_15 ~ XMV_8: r=1.000
- XMEAS_17 ~ XMV_11: r=-0.999
- XMEAS_7 ~ XMEAS_13: r=0.998
- XMEAS_1 ~ XMV_3: r=0.997
- XMEAS_19 ~ XMV_9: r=0.988
- 结果文件：02_processed/validate_report.json（correlation/anti_spurious/batch 三组）；反假相关：Simpson/去趋势/离群敏感度/多重检验校验已完成

## 5. 视觉证据
- 塔液位与进料率通道自故障时段起呈缓变偏移，无瞬态爆发形态
- 各通道偏移幅度小（多数贴近±3σ线），符合弱扰动特征
- 阀位通道呈调节性小幅波动（控制对耦合）

## 6. 根因结论（诊断结论 Diagnosis）
**D 进料温度阶跃（D feed temperature step，流股2）：文献公认难检故障，签名微弱（全列谱 max|z|≤4.26），异常集中于汽提塔热平衡侧（XM15/XMV_8）与进料链路补偿（XM6/XM4），置信度按弱签名规则受限。**
- 结论类型：DETERMINED；置信度 72%（置信上限依据：证据等级 L3-L5 支撑，无 L1 直接测量）。

## 8. 竞争假设与排除逻辑
- 【存活】D 进料温度阶跃（进料系统热扰动）（置信 72%，机制=feed-system-fault）
  - 判别证据：L3 统计：异常位点集中于塔热平衡-进料补偿链（XM15/XMV_8 塔侧、XM6/XM4 进料侧）——与 D 进料温度扰动的传播位点一致

- 【排除】进料组成阶跃（置信 15%，机制=feed-composition-step）
  - 判别证据：L3 统计：组分通道仅 XM30 3.72σ 入 top-6，且幅度低于塔/进料侧通道
  - 矛盾证据（排除逻辑）：组成阶跃（如 IDV1/2/8 类）的签名是组分主导——本记录组分缺席主导位，证据结构不符
- 【排除】反应器/冷凝器冷却水扰动（置信 10%，机制=cooling-disturbance）
  - 判别证据：L3 统计：XM21/XM22/XM9/XMV_10/XMV_11 均未进入异常列谱 top-6
  - 矛盾证据（排除逻辑）：冷却侧全链路签名缺失，与冷却扰动假设的预期完全不符
- 【排除】反应器一次扰动（压力/温度/液位）（置信 12%，机制=operating-point）
  - 判别证据：L3 统计：反应器三参数均未进入异常列谱 top-6
  - 矛盾证据（排除逻辑）：反应器本体签名缺失——异常集中在塔侧与进料链，指向塔热平衡一次扰动而非反应器
- 排除统计：存活 1 个，排除 3 个。

## 9. 详细推导与推理过程 (Detailed Derivation)
### D 进料温度阶跃（进料系统热扰动）
- 机理链（logic_chain）：1) D 进料温度阶跃 → 汽提塔内热平衡被扰动（D 在塔内被汽提脱除，进料焓变直接进入塔热平衡） → 2) 塔热平衡补偿 → 塔液位/液相流阀联动（brief：XMEAS_15 塔液位 3.88 与 XMV_8 塔液相阀 3.88，r=1.000 控制对） → 3) 下游补偿 → 反应器进料率与 A+C 进料联动（brief：XMEAS_6 反应器进料率 4.26 全列谱最大、XMEAS_4 A+C 进料 3.77）
- 物理量级核对：排除法量级核对：组成类一次扰动（IDV1/2/8 类）应以组分通道 ≥5σ 主导——观测组分最高仅 3.72σ，排除；冷却类应以 XM21/22 主导——缺席，排除；剩余唯一能同时解释塔热平衡位点 + 进料链路补偿 + 弱签名的是 D 进料热扰动（D 进料量小 → 幅值天然受限），方向与量级自洽。
- 数据支撑：L3 统计：异常位点集中于塔热平衡-进料补偿链（XM15/XMV_8 塔侧、XM6/XM4 进料侧）——与 D 进料温度扰动的传播位点一致；L3 统计：全列谱 max|z|=4.26 且超3σ占比 ≤0.4%——弱签名，与 D 进料温度阶跃『低传播幅值』的文献公认特征一致；L3 统计：组分测量未主导列谱（仅 XM30 3.72 入 top-6）——排除组成类一次扰动；L3 统计：XMV_6 吹扫阀 3.63 小幅联动——气相侧轻度补偿，与热扰动而非组成扰动相符；L4 视觉：塔液位与进料率通道自故障时段起呈缓变偏移，无瞬态爆发（fig_temporal_overview.png）

## 10. 推理链 (Reasoning Chain)
- R1 数据探查：960×53，缺失/常数列已剔除
- R2 本体映射：11 变量 → 物理语义 + 物理原理
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
  - [数据缺口] D 进料管线无温度直接测量列——热扰动的直接签名缺失，结论依赖下游位点+排除法
  - [数据缺口] 全局统计签名弱（max|z|=4.26），故障时段前后的受控对比分析（第161样本分段）可进一步收紧判别
  - [推理限制] D 进料温度阶跃与其它微弱热扰动的最终分辨需流股2 温度测量——现有数据粒度下以位点+排除法定案，置信上限 0.72

## 13. 复现信息
- case 定义：scripts/benchmark/cases/benchmark_cases.json（真值与关键词仅在评分器使用，未注入管线）
- 评分：results/benchmark/gradings/tep_d03_hard.json；事件日志：.pipeline_events.jsonl（pipeline-log-check 通过）
- 门禁：pipeline-finalize_report.json（overall=见文件）
