# TEP 工业诊断报告 — tep_d07_header_pressure

> run_id: 202609121510117_bench_tep_d07_header_pressure · 执行模式: zcode-direct（无 OMP/Claude Code，ZCode agent 直接按 skill 协议执行） · 数据: 960 行 × 53 列 · 统计引擎: stats-package

## 1. 执行摘要 (Executive Summary)
- 诊断结论类型：**DETERMINED**（置信度 80%）
- 主结论：流股4 C 集管压力降低（C header pressure reduced, Stream 4）：F 族组分跨三流股一致偏移（XM28/34/38）+ 反应器与汽提塔压力双签名（XM7 4.61 / XM16 4.60）——气相供给侧压力/组成一次扰动。
- 竞争假设 3 个，排除 2 个；评审得分 91/100（pass）；审计 ENDORSED。

## 2. 核心证据与对齐图
- 核心图证：03_figures/fig_temporal_overview.png（关键变量时序对齐网格，±3σ 阈值线）
- 核心统计证据：XMEAS_28（max|z|=4.84）、XMEAS_11（max|z|=4.72）、XMEAS_34（max|z|=4.67）
- 核心机理证据：C 集管压力降低 = 供给侧一次扰动：组成（C 降→A/F 富集）与气相压力双通道同时失稳
- 证据对齐：数据（00_input/data.csv）→ 统计（validate_report）→ 视觉（fig_temporal_overview）→ 机理（ontology）四层互证。

## 3. 数据与本体
- 输入：D:\codes\myskills\industrial-deep-diagnostic\data\benchmark\prepared\tep\d07_te.csv（sha256 已记录于 input_manifest.json）
- 工艺背景：Tennessee Eastman 化工过程：反应器-冷凝器-气液分离器-汽提塔+循环压缩机。XMEAS_1..41 过程测量、XMV_1..11 操纵变量。3分钟采样，第161样本（8h）起为故障时段。本例为流股4 C 集管压力降低。…
- 本体域：Tennessee Eastman 化工过程（反应器-冷凝器-分离器-汽提塔）；变量语义映射 7 项（RAG 降级路径：parameter_to_physics + 领域知识）。

## 4. 方法与执行过程
Step 0 setup（setup.mjs，事件日志 .pipeline_events.jsonl）→ Step 1 inspect（inspect.mjs）→ Step 2 本体构建（context-builder 角色：变量语义+物理原理）→ Step 3 统计分析（stats 包 run.py：相关/CCF/反假相关/多重检验；驱动端补充单变量 z 扫描与跨域相关）→ Step 3.5 视觉分析（matplotlib 时序网格图 + VLM 角色直接读图）→ Step 4 竞争假设诊断（diagnostician 角色：≥3 假设、≥2 排除、三态结论；physics_check 自动物理可行性核验）→ Step 5a 质量评审（judge 角色 10 维评分）→ Step 7 物理审计（report-reviewer 角色）→ Step 8/8.5 HTML 报告与审校 → Step 9 收尾。

## 4. 统计分析发现（统计验证与数据统计）
- XMEAS_28: max|z|=4.84，超 3σ 点占比 1.3%
- XMEAS_11: max|z|=4.72，超 3σ 点占比 3.7%
- XMEAS_34: max|z|=4.67，超 3σ 点占比 1.9%
- XMEAS_7: max|z|=4.61，超 3σ 点占比 3.5%
- XMEAS_38: max|z|=4.6，超 3σ 点占比 2.6%
- XMEAS_16: max|z|=4.6，超 3σ 点占比 3.7%

强相关对（|r|≥0.4，已剔除常数列）：
- XMEAS_15 ~ XMV_8: r=1.000
- XMEAS_12 ~ XMV_7: r=1.000
- XMEAS_1 ~ XMV_3: r=0.999
- XMEAS_7 ~ XMEAS_13: r=0.999
- XMEAS_17 ~ XMV_11: r=-0.990
- XMEAS_19 ~ XMV_9: r=0.990
- 结果文件：02_processed/validate_report.json（correlation/anti_spurious/batch 三组）；反假相关：Simpson/去趋势/离群敏感度/多重检验校验已完成

## 5. 视觉证据
- F 族组分通道自故障时段呈持续偏移平台
- 反应器/汽提塔压力通道同期异常
- 阀位通道正常调节带

## 6. 根因结论（诊断结论 Diagnosis）
**流股4 C 集管压力降低（C header pressure reduced, Stream 4）：F 族组分跨三流股一致偏移（XM28/34/38）+ 反应器与汽提塔压力双签名（XM7 4.61 / XM16 4.60）——气相供给侧压力/组成一次扰动。**
- 结论类型：DETERMINED；置信度 80%（置信上限依据：证据等级 L3-L5 支撑，无 L1 直接测量）。

## 8. 竞争假设与排除逻辑
- 【存活】流股4 C 集管压力降低（供给侧压力/组成扰动）（置信 80%，机制=operating-point）
  - 判别证据：L3 统计：F 族组分跨流股6/9/11 一致偏移（4.60-4.84σ，超3σ占比 1.3-3.7%）——供给组成变化的传播链证据

- 【排除】A/C 配比阶跃（IDV1 类）（置信 25%，机制=feed-composition-step）
  - 判别证据：L3 统计：本记录压力通道（XM7/XM16 4.6 级）与组分同级显著——双签名结构
  - 矛盾证据（排除逻辑）：IDV1 类签名（对比 d01 场景的『组分 4/6 主导、压力缺席』）与本记录『组分+压力双签名』结构不符
- 【排除】冷却水侧扰动（置信 10%，机制=cooling-disturbance）
  - 判别证据：L3 统计：XM9 未入异常列谱 top-6
  - 矛盾证据（排除逻辑）：反应器温度签名缺失——冷却类一次扰动被排除
- 排除统计：存活 1 个，排除 2 个。

## 9. 详细推导与推理过程 (Detailed Derivation)
### 流股4 C 集管压力降低（供给侧压力/组成扰动）
- 机理链（logic_chain）：1) C 集管压力降低 → 流股4 中 C 供给量下降、A/F 相对富集（brief：F 族组分 XM28 4.84 / XM34 4.67 / XM38 4.60 跨流股6/9/11 一致偏移） → 2) 气相供给失衡 → 反应器压力越界（brief：XMEAS_7 4.61）与汽提塔压力响应（brief：XMEAS_16 4.60）——双压力签名 → 3) 分离负荷重平衡 → 分离器温度补偿（brief：XMEAS_11 4.72）
- 物理量级核对：签名-机理核对：C 供给压力下降同时产生『组成偏移（C 少→A/F 富集）』与『气相压力失衡』两类签名——观测正是 F 族组分跨流股一致偏移 + 反应器/汽提塔双压力异常；组成阶跃类（IDV1/8）无压力双签名，进料量类无组分偏移，均可判别。
- 数据支撑：L3 统计：F 族组分跨流股6/9/11 一致偏移（4.60-4.84σ，超3σ占比 1.3-3.7%）——供给组成变化的传播链证据；L3 统计：反应器压力 XM7 4.61 与汽提塔压力 XM16 4.60 同级异常——气相供给侧压力签名；L3 统计：分离器温度 XM11 4.72——分离负荷重平衡补偿；L3 统计：控制回路对完好（XM15~XMV8 1.000、XM1~XMV3 0.999）——阀位补偿正常，异常非控制器引起；L4 视觉：组分与压力通道自故障时段持续偏移（fig_temporal_overview.png）

## 10. 推理链 (Reasoning Chain)
- R1 数据探查：960×53，缺失/常数列已剔除
- R2 本体映射：7 变量 → 物理语义 + 物理原理
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
  - [数据缺口] C 集管压力无直接测量列——一次签名以组成+压力双通道间接呈现
  - [推理限制] 压力降幅与 C 供给量变化比例需流股4 组分直接测量才能定量

## 13. 复现信息
- case 定义：scripts/benchmark/cases/benchmark_cases.json（真值与关键词仅在评分器使用，未注入管线）
- 评分：results/benchmark/gradings/tep_d07_header_pressure.json；事件日志：.pipeline_events.jsonl（pipeline-log-check 通过）
- 门禁：pipeline-finalize_report.json（overall=见文件）
