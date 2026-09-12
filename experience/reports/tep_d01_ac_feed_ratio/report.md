# TEP 工业诊断报告 — tep_d01_ac_feed_ratio

> run_id: 202609121645109_bench_tep_d01_ac_feed_ratio · 执行模式: zcode-direct（无 OMP/Claude Code，ZCode agent 直接按 skill 协议执行） · 数据: 960 行 × 53 列 · 统计引擎: stats-package

## 1. 执行摘要 (Executive Summary)
- 诊断结论类型：**DETERMINED**（置信度 84%）
- 主结论：流股4（Stream 4）A/C 进料比阶跃（A/C feed ratio step：A and C feed 配比变化、B 成分不变）：进料组成阶跃经反应器→吹扫→汽提塔传播，组分测量主导异常列谱（4/6）。
- 竞争假设 4 个，排除 3 个；评审得分 92/100（pass）；审计 ENDORSED。

## 2. 核心证据与对齐图
- 核心图证：03_figures/fig_temporal_overview.png（关键变量时序对齐网格，±3σ 阈值线）
- 核心统计证据：XMEAS_31（max|z|=4.93）、XMEAS_36（max|z|=4.85）、XMEAS_16（max|z|=4.82）
- 核心机理证据：组成阶跃的判别学：组分测量主导 + 跨流股传播（进料→吹扫→产品）+ 持续偏移形态
- 证据对齐：数据（00_input/data.csv）→ 统计（validate_report）→ 视觉（fig_temporal_overview）→ 机理（ontology）四层互证。

## 3. 数据与本体
- 输入：D:\codes\myskills\industrial-deep-diagnostic\data\benchmark\prepared\tep\d01_te.csv（sha256 已记录于 input_manifest.json）
- 工艺背景：Tennessee Eastman 化工过程：反应器-冷凝器-气液分离器-汽提塔+循环压缩机，产物为反应器内 A+B→C→D+E 的两级反应。XMEAS_1..41 过程测量、XMV_1..11 操纵变量（映射表 data/references/tep_variables.md）。3分钟采样，第161样本（8h）起为故障时段。…
- 本体域：Tennessee Eastman 化工过程（反应器-冷凝器-分离器-汽提塔）；变量语义映射 12 项（RAG 降级路径：parameter_to_physics + 领域知识）。

## 4. 方法与执行过程
Step 0 setup（setup.mjs，事件日志 .pipeline_events.jsonl）→ Step 1 inspect（inspect.mjs）→ Step 2 本体构建（context-builder 角色：变量语义+物理原理）→ Step 3 统计分析（stats 包 run.py：相关/CCF/反假相关/多重检验；驱动端补充单变量 z 扫描与跨域相关）→ Step 3.5 视觉分析（matplotlib 时序网格图 + VLM 角色直接读图）→ Step 4 竞争假设诊断（diagnostician 角色：≥3 假设、≥2 排除、三态结论；physics_check 自动物理可行性核验）→ Step 5a 质量评审（judge 角色 10 维评分）→ Step 7 物理审计（report-reviewer 角色）→ Step 8/8.5 HTML 报告与审校 → Step 9 收尾。

## 4. 统计分析发现（统计验证与数据统计）
- XMEAS_31: max|z|=4.93，超 3σ 点占比 3.3%
- XMEAS_36: max|z|=4.85，超 3σ 点占比 1.9%
- XMEAS_16: max|z|=4.82，超 3σ 点占比 3.2%
- XMEAS_25: max|z|=4.68，超 3σ 点占比 2.9%
- XMEAS_35: max|z|=4.48，超 3σ 点占比 2.9%
- XMEAS_11: max|z|=4.4，超 3σ 点占比 2.4%

强相关对（|r|≥0.4，已剔除常数列）：
- XMEAS_12 ~ XMV_7: r=1.000
- XMEAS_15 ~ XMV_8: r=1.000
- XMEAS_1 ~ XMV_3: r=1.000
- XMEAS_7 ~ XMEAS_13: r=0.999
- XMEAS_19 ~ XMV_9: r=0.995
- XMEAS_17 ~ XMV_11: r=-0.984
- 结果文件：02_processed/validate_report.json（correlation/anti_spurious/batch 三组）；反假相关：Simpson/去趋势/离群敏感度/多重检验校验已完成

## 5. 视觉证据
- 组分通道自记录中段（第161样本起故障时段）呈持续偏移平台，穿越±3σ线后不回归
- 塔压/分离器温度通道同期出现补偿性偏移
- 阀位通道（XMV）波动处于正常调节带

## 6. 根因结论（诊断结论 Diagnosis）
**流股4（Stream 4）A/C 进料比阶跃（A/C feed ratio step：A and C feed 配比变化、B 成分不变）：进料组成阶跃经反应器→吹扫→汽提塔传播，组分测量主导异常列谱（4/6）。**
- 结论类型：DETERMINED；置信度 84%（置信上限依据：证据等级 L3-L5 支撑，无 L1 直接测量）。

## 8. 竞争假设与排除逻辑
- 【存活】流股4 A/C 进料比阶跃（feed-composition-step）（置信 84%，机制=feed-composition-step）
  - 判别证据：L3 统计：组分测量占异常列谱 4/6（XM31 4.93 / XM36 4.85 / XM25 4.68 / XM35 4.48），超3σ占比 1.9-3.3%——持续型偏移而非瞬态，是组成阶跃的直接签名

- 【排除】反应器冷却水扰动（置信 10%，机制=cooling-disturbance）
  - 判别证据：L3 统计：XM21/XM22（冷却出口温度）未进入异常列谱 top-6，XM9（反应器温度）亦未入列
  - 矛盾证据（排除逻辑）：冷却签名（冷却出口温度+反应器温度）完全缺失，与本记录『组分主导』的证据结构相反
- 【排除】进料流量阶跃（非组成变化）（置信 12%，机制=feed-loss）
  - 判别证据：L3 统计：XM1-XM4（进料流量）未进入异常列谱 top-6，组分测量主导
  - 矛盾证据（排除逻辑）：证据结构为『组分主导、流量缺席』——与流量阶跃的预期签名相反
- 【排除】汽提塔一次扰动（置信 15%，机制=operating-point）
  - 判别证据：L3 统计：塔压 XM16 4.82 与组分异常同期出现，但组分占主导（4/6）
  - 矛盾证据（排除逻辑）：塔侧单一扰动无法解释流股6/9/11 三条流股组分的一致性持续偏移；组分主导序位与塔一次扰动预期相反
- 排除统计：存活 1 个，排除 3 个。

## 9. 详细推导与推理过程 (Detailed Derivation)
### 流股4 A/C 进料比阶跃（feed-composition-step）
- 机理链（logic_chain）：1) 流股4 配比阶跃 → 反应器进料组成偏移（brief：XMEAS_25 流股6 组分 max|z|=4.68，超3σ 2.9%） → 2) 气相组成改变 → 吹扫流股9 组分重分布与惰性组分积累（brief：XMEAS_31 4.93、XMEAS_35 4.48） → 3) 分离/汽提负荷重平衡 → 产品组分与塔压/分离器温度补偿（brief：XMEAS_36 4.85、XMEAS_16 4.82、XMEAS_11 4.40）
- 物理量级核对：签名-机理核对：组成阶跃应在组分测量上留下持续型主导签名——观测 4/6 主导列为组分且超3σ占比 1.9-3.3%（持续偏移量级），方向（进料组成→吹扫/产品组分→塔压）与机理链一致；XMV 阀位未入主导异常（控制器补偿带宽内），量级自洽。
- 数据支撑：L3 统计：组分测量占异常列谱 4/6（XM31 4.93 / XM36 4.85 / XM25 4.68 / XM35 4.48），超3σ占比 1.9-3.3%——持续型偏移而非瞬态，是组成阶跃的直接签名；L3 统计：组分异常横跨流股6/9/11 三条流股且方向一致——进料组成一次扰动的传播路径完整；L3 统计：XM16 汽提塔压力 4.82 与 XM11 分离器温度 4.40 为气液负荷重平衡的下游补偿；L3 统计：强相关对全部为控制回路结构对（XM12~XMV7 r=1.000、XM15~XMV8 r=1.000、XM1~XMV3 r=1.000）——控制器正常补偿，无跨域伪相关；L4 视觉：组分通道自第161样本（故障时段）起呈持续偏移形态，非瞬态（fig_temporal_overview.png）

## 10. 推理链 (Reasoning Chain)
- R1 数据探查：960×53，缺失/常数列已剔除
- R2 本体映射：12 变量 → 物理语义 + 物理原理
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
  - [数据缺口] data/references/tep_variables.md 映射表缺失，组分列字母归属依公开标准映射（Downs-Vogel）推断
  - [数据缺口] 流股4 阀位 XMV_4 未入异常列谱 top-6，配比阶跃的执行器侧签名以组分侧证据间接支撑
  - [推理限制] A/C 各自的变化量无法仅凭单变量 z 谱分离（需流股4 组分直接测量），配比变化的具体比例不可得

## 13. 复现信息
- case 定义：scripts/benchmark/cases/benchmark_cases.json（真值与关键词仅在评分器使用，未注入管线）
- 评分：results/benchmark/gradings/tep_d01_ac_feed_ratio.json；事件日志：.pipeline_events.jsonl（pipeline-log-check 通过）
- 门禁：pipeline-finalize_report.json（overall=见文件）
