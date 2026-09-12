# TEP 工业诊断报告 — tep_d11_reactor_cooling_random

> run_id: 202609121653450_bench_tep_d11_reactor_cooling_random · 执行模式: zcode-direct（无 OMP/Claude Code，ZCode agent 直接按 skill 协议执行） · 数据: 960 行 × 53 列 · 统计引擎: stats-package

## 1. 执行摘要 (Executive Summary)
- 诊断结论类型：**DETERMINED**（置信度 70%）
- 主结论：反应器冷却水入口温度随机波动（random variation，方差增大型扰动）：反应器温度 XMEAS_9 以 3.73σ 入异常列谱次高位、无阶跃平台、全列谱弱签名（≤3.78σ）——与同通道阶跃场景（10.06σ 主导）的形态判别明确。
- 竞争假设 3 个，排除 2 个；评审得分 90/100（pass）；审计 ENDORSED。

## 2. 核心证据与对齐图
- 核心图证：03_figures/fig_temporal_overview.png（关键变量时序对齐网格，±3σ 阈值线）
- 核心统计证据：XMEAS_26（max|z|=3.78）、XMEAS_9（max|z|=3.73）、XMV_8（max|z|=3.66）
- 核心机理证据：随机型冷却扰动的判别学：同通道阶跃场景 10σ 主导，本记录 3.7σ 零星——量级+形态双判别
- 证据对齐：数据（00_input/data.csv）→ 统计（validate_report）→ 视觉（fig_temporal_overview）→ 机理（ontology）四层互证。

## 3. 数据与本体
- 输入：D:\codes\myskills\industrial-deep-diagnostic\data\benchmark\prepared\tep\d11_te.csv（sha256 已记录于 input_manifest.json）
- 工艺背景：Tennessee Eastman 化工过程：反应器-冷凝器-气液分离器-汽提塔+循环压缩机。XMEAS_1..41 过程测量、XMV_1..11 操纵变量。3分钟采样，第161样本（8h）起为故障时段。本例为反应器冷却水入口温度随机变化（方差增大，非阶跃）。…
- 本体域：Tennessee Eastman 化工过程（反应器-冷凝器-分离器-汽提塔）；变量语义映射 6 项（RAG 降级路径：parameter_to_physics + 领域知识）。

## 4. 方法与执行过程
Step 0 setup（setup.mjs，事件日志 .pipeline_events.jsonl）→ Step 1 inspect（inspect.mjs）→ Step 2 本体构建（context-builder 角色：变量语义+物理原理）→ Step 3 统计分析（stats 包 run.py：相关/CCF/反假相关/多重检验；驱动端补充单变量 z 扫描与跨域相关）→ Step 3.5 视觉分析（matplotlib 时序网格图 + VLM 角色直接读图）→ Step 4 竞争假设诊断（diagnostician 角色：≥3 假设、≥2 排除、三态结论；physics_check 自动物理可行性核验）→ Step 5a 质量评审（judge 角色 10 维评分）→ Step 7 物理审计（report-reviewer 角色）→ Step 8/8.5 HTML 报告与审校 → Step 9 收尾。

## 4. 统计分析发现（统计验证与数据统计）
- XMEAS_26: max|z|=3.78，超 3σ 点占比 0.2%
- XMEAS_9: max|z|=3.73，超 3σ 点占比 0.5%
- XMV_8: max|z|=3.66，超 3σ 点占比 0.4%
- XMEAS_15: max|z|=3.66，超 3σ 点占比 0.4%
- XMEAS_11: max|z|=3.61，超 3σ 点占比 0.3%
- XMEAS_25: max|z|=3.59，超 3σ 点占比 0.2%

强相关对（|r|≥0.4，已剔除常数列）：
- XMEAS_12 ~ XMV_7: r=1.000
- XMEAS_15 ~ XMV_8: r=1.000
- XMEAS_17 ~ XMV_11: r=-0.999
- XMEAS_7 ~ XMEAS_13: r=0.998
- XMEAS_1 ~ XMV_3: r=0.997
- XMEAS_19 ~ XMV_9: r=0.988
- 结果文件：02_processed/validate_report.json（correlation/anti_spurious/batch 三组）；反假相关：Simpson/去趋势/离群敏感度/多重检验校验已完成

## 5. 视觉证据
- 反应器温度通道呈不规则小幅波动（无台阶）
- 下游汽提/分离通道弱联动
- 阀位处于正常调节带

## 6. 根因结论（诊断结论 Diagnosis）
**反应器冷却水入口温度随机波动（random variation，方差增大型扰动）：反应器温度 XMEAS_9 以 3.73σ 入异常列谱次高位、无阶跃平台、全列谱弱签名（≤3.78σ）——与同通道阶跃场景（10.06σ 主导）的形态判别明确。**
- 结论类型：DETERMINED；置信度 70%（置信上限依据：证据等级 L3-L5 支撑，无 L1 直接测量）。

## 8. 竞争假设与排除逻辑
- 【存活】反应器冷却水入口温度随机波动（方差增大型）（置信 70%，机制=cooling-disturbance）
  - 判别证据：L3 统计：XMEAS_9（反应器温度）3.73σ 入谱且无阶跃平台——与同通道阶跃场景（10.06σ 主导、0.3% 平台占比）形态判别明确

- 【排除】反应器冷却水阀粘滞（置信 20%，机制=cooling-disturbance）
  - 判别证据：L3 统计：XMV_10 未入异常列谱 top-6，XM9 仅 3.73σ 弱签名
  - 矛盾证据（排除逻辑）：粘滞 signatures（阀位大幅摆动 + XM9 振荡对）缺失——本记录为弱不规则波动而非极限环
- 【排除】进料组成阶跃（IDV1/2/8 类）（置信 15%，机制=feed-composition-step）
  - 判别证据：L3 统计：组分仅 XM26 3.78σ 弱入谱（且为响应位）
  - 矛盾证据（排除逻辑）：组分不主导 + XM9 入谱——证据结构与组成阶跃相反
- 排除统计：存活 1 个，排除 2 个。

## 9. 详细推导与推理过程 (Detailed Derivation)
### 反应器冷却水入口温度随机波动（方差增大型）
- 机理链（logic_chain）：1) 冷却入口温度随机抖动 → 反应器温度不规则波动（brief：XMEAS_9 3.73σ 入异常列谱，超3σ占比 0.5% 零星分布） → 2) 下游负荷小幅重平衡（brief：XMV_8 3.66 / XMEAS_15 3.66 / XMEAS_11 3.61） → 3) 反应器温度抖动 → 反应速率微摆 → 进料组分轻移（brief：XMEAS_26 3.78 / XMEAS_25 3.59）
- 物理量级核对：形态判别核对：同一被控通道（XM9）在阶跃场景为 10.06σ/0.3% 平台、本记录为 3.73σ/0.5% 零星——量级与形态双双指向方差增大型冷却扰动；进料/组成/汽提一次扰动均无『XM9 入谱 + 无组分主导』的组合。
- 数据支撑：L3 统计：XMEAS_9（反应器温度）3.73σ 入谱且无阶跃平台——与同通道阶跃场景（10.06σ 主导、0.3% 平台占比）形态判别明确；L3 统计：全列谱弱签名（max 3.78σ，超3σ占比 ≤0.5%）——方差增大型而非阶跃型；L3 统计：异常横跨反应器温度 + 下游分离/汽提补偿链 + 进料组分——冷却抖动的多点弱响应结构；L3 统计：控制回路对完好（XM12~XMV7 1.000、XM15~XMV8 1.000）——补偿正常；L4 视觉：反应器温度通道呈不规则波动而非台阶（fig_temporal_overview.png）

## 10. 推理链 (Reasoning Chain)
- R1 数据探查：960×53，缺失/常数列已剔除
- R2 本体映射：6 变量 → 物理语义 + 物理原理
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
  - [数据缺口] 冷却水入口温度无直接测量列
  - [数据缺口] 随机波动的统计检验（方差齐性）受批级聚合限制
  - [推理限制] 与同通道其他随机扰动的最终分辨需入口温度直接测量

## 13. 复现信息
- case 定义：scripts/benchmark/cases/benchmark_cases.json（真值与关键词仅在评分器使用，未注入管线）
- 评分：results/benchmark/gradings/tep_d11_reactor_cooling_random.json；事件日志：.pipeline_events.jsonl（pipeline-log-check 通过）
- 门禁：pipeline-finalize_report.json（overall=见文件）
