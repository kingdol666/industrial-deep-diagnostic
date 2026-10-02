# 数据分析报告 — lekai/run-PG31DS（单型号对照 run）

> 由 industrial-doe-analyzer 生成 · 分析模式 observational · 设计类型 observational ·
> 证据等级 B · 下游合同 recommendations.json v1.0

---

## 一、10 秒结论卡

| 项 | 值 |
|---|---|
| 关键因子（按效应强度） | 无显著因子。total_defects 按 ΔR²：MD_TH009(0.0506)、W1C8D(0.0490)、W1C8A(0.0382)、MD_TH013(0.0364)、W1C86(0.0338)；oligomer 候选 F_PS006(r=-0.2458)、W1C8D(r=+0.2440)，均 q≥0.2092 |
| 推荐操作窗口数 | 0（其中 0 条需先做确认试验） |
| 预期收益（最优窗口） | 不适用（无窗口，0/88 检验通过 FDR） |
| 证据等级 | B（观察档：随机化/纯误差 df/分辨度/平衡四项均 n/a，仅 anti_spurious_ok=true；全部结论为相关级） |
| 最重要的限制 | 双响应重尾（total_defects 偏度 3.16、oligomer 偏度 3.95）+ 0/88 检验过 BH 校正——分层到单型号后仍无可执行窗口 |

**一句话结论**：单型号（PG31DS，67 批）分层去掉了型号间混杂，但信号并未更干净——88 项相关检验 0 项过 FDR、oligomer 的 5 条最强相关全部为离群驱动 FAIL、双响应重尾令置信区间过宽，当前观测数据不足以产出任何可执行操作窗口；下一步应对 top 候选做小规模有意扰动确认 DOE，而非继续累积观测批次。

---

## 二、1 分钟证据层

### 2.1 效应/相关排序

**total_defects（minimize，weight 1.5）— 相关 |r| 前 5（n=67，全部不显著）**

| 参数 | r | p | q(BH) | 防伪判定 | lag 一致 |
|---|---|---|---|---|---|
| W1C8C@PV1_mean | -0.155 | 0.2103 | 0.9571 | PASS | 是 |
| W1C7D@PV1_mean | -0.1437 | 0.246 | 0.9571 | PASS | 否 |
| W1C89@PV1_mean | -0.1376 | 0.267 | 0.9571 | PASS | 否 |
| MD_TH018@PV_mean | -0.1347 | 0.277 | 0.9571 | CAUTION（趋势混杂） | 否 |
| MD_TH002@PV_mean | -0.1332 | 0.2826 | 0.9571 | PASS | 否 |

**oligomer（minimize，weight 1.0）— 通过防伪（PASS）的候选（按 |r| 排序，全部未达 FDR 显著）**

| 参数 | r | p | q(BH) | 防伪判定 | lag 一致 |
|---|---|---|---|---|---|
| F_PS006@PV1_mean | -0.2458 | 0.0449 | 0.2092 | PASS | 是 |
| W1C8D@PV1_mean | +0.2440 | 0.0466 | 0.2092 | PASS | 是 |
| W1C4B@PV1_mean | +0.2397 | 0.0507 | 0.2092 | PASS | 是 |
| W1C40@PV1_mean | +0.2395 | 0.0509 | 0.2092 | PASS | 是 |
| W1C86@PV1_mean | +0.2388 | 0.0517 | 0.2092 | PASS | 是 |
| W1C85@PV1_mean | +0.2335 | 0.0572 | 0.2092 | PASS | 是 |
| W1C87@PV1_mean | -0.2298 | 0.0614 | 0.2092 | PASS | 是 |
| MD_TH018@PV_mean | -0.2294 | 0.0618 | 0.2092 | PASS | 否 |

**离群驱动 FAIL（禁止引用）**：oligomer 的 5 条最强相关——W1C7D(r=-0.2885)、W1C8C(r=-0.2616)、W1C01(r=+0.2567)、W1C82(r=-0.2545)、W1C88(r=-0.2542)，outlier_sensitivity 全部 SERIOUS。

**ΔR² 贡献排序（total_defects，44 参数联合模型 r_full_model=0.7594）**：MD_TH009(0.0506)、W1C8D(0.0490)、W1C8A(0.0382)、MD_TH013(0.0364)、W1C86(0.0338)、F_PS006(0.0336)、MD_TH005(0.0334)、MD_TH014(0.0315)、F_PS005(0.0246)、W1C7C(0.0200)——单参数贡献均 ≤5.1%，效应高度分散。

### 2.2 关键图

| 图 | 文件 | 读图要点 |
|---|---|---|
| 校正相关矩阵 | 03_figures/correlation_heatmap.png | 无任何深色格（|r|≥0.3 为空）；oligomer 列的多条中等相关均被防伪判 FAIL/CAUTION |
| ΔR² 贡献排名 | 03_figures/contribution_bar.png | 条形平坦，top1 仅 0.0506，无主导杠杆 |
| 稳定性时间线 — total_defects | 03_figures/timeline_total_defects.png | mean 89.46、std 87.69：波动与均值同量级，右侧尖峰主导 |
| 稳定性时间线 — oligomer | 03_figures/timeline_oligomer.png | mean 20.0、std 39.63（≈2×均值），尖峰更极端 |
| 稳态段对比 — total_defects | 03_figures/segments_total_defects.png | 仅 2 个稳态段（15 批 / 24 批），段均值 94.93 vs 96.58，差异远小于段内波动 |

### 2.3 稳定性/能力（观察档适用）

| 响应 | n | mean | std_overall | sigma_within(MR) | 偏度 | 超额峰度 | AD 统计量 | 正态 |
|---|---|---|---|---|---|---|---|---|
| total_defects | 67 | 89.462687 | 87.686482 | 63.789491 | 3.1612 | 10.6886 | 7.8171 | 否 |
| oligomer | 67 | 20.0 | 39.633549 | 21.101977 | 3.9496 | 14.7922 | 15.6221 | 否 |

（无规格限，Cp/Cpk 不适用；AD 5% 临界值 0.743，两响应均严重偏离正态——重尾。lag-1 自相关：total_defects -0.1266、oligomer -0.0182，批间无明显惯性。）

**工况/稳态**：regime 检测 window_rows=20，steady 39 批（58.21%）、transition 21 批（31.34%）、marginal 7 批（10.45%）；选中 2 个稳态段——rows 7–21（15 批，total_defects 均值 94.93、oligomer 18.73）与 rows 43–66（24 批，96.58 / 19.0）。无变点、无漂移旗标。

---

## 三、深读审计层

### 3.1 模型与检验细节

- **多重检验**：BH 校正，2 个检验族（响应），共 88 项检验，q<0.05 显著项 = **0**。total_defects 族最小 q=0.9571；oligomer 族最小 q=0.2092。
- **防伪汇总**（脚本警告，载荷性内容，全文保留）：`SERIOUS_CONCERNS — Multiple statistical robustness issues detected. Key correlations should be re-verified before drawing causal conclusions.`——serious_count=7（离群驱动 5 + Spearman 分歧 2）、偏斜受影响列 24/46、Simpson 检验发现 0、变点 0、fatal 0。
- **趋势混杂**：22 对被判 time_trend=CONFOUNDED（CAUTION），其中 total_defects 15 对、oligomer 7 对——共享时间趋势抬高原始 r，去趋势后（detrended_r）普遍衰减。
- **滞后搜索边界**：21/88 对（≈23.9%）的 best_lag 落在 ±5 搜索边界（total_defects 18 对于 -5，oligomer 3 对（MD_TH013/014/015）于 +5）——CCF 峰不具内部稳定性，滞后结构不可信（lag_warning 字段为 null，此为分析师对工件数字的复核）。
- **过拟合风险**：n=67 对 44 个预测元（自由度比 0.66），联合模型 r_full_model=0.7594 应视为上界；单参数 ΔR²≤5.1% 才是可信的单变量效应量级。
- **参数激励不足**：设计检测注记"LHS occupancy only 0.15 (<0.85)"；W1C40 全程仅 10 个取值——多数参数在生产波动带宽内变化，不足以激励出可辨识窗口。

### 3.2 披露与限制（全部保留，不得删除）

1. 观察性数据：全部结论为相关级（evidence B），执行任何操作窗口前必须完成 confirmations
2. 响应重尾由少数缺陷尖峰批次主导（total_defects std=87.69 ≈ mean 89.46；oligomer std=39.63 ≈ 2×mean 20.0）：建任何窗口前应先核查尖峰批次成因并做稳健复检（分析师补充）
3. n=67 批对 44 个过程量，时间跨度仅约 8.6 天（2026-05-04 14:42 至 2026-05-13 05:51），覆盖单一生产窗口，结论外推需谨慎（分析师补充）
4. 观测路径按当前效应量粗估需 150–250 批才可能通过 FDR；更快路径是对 top 候选做有意扰动的确认 DOE（分析师估算，非脚本计算）

### 3.3 确认试验计划

本 run 无窗口，故 recommendations.json 中 confirmations=[]（0 条）。若推进验证，建议（分析师建议，非合同条目）：

- 对 **F_PS006@PV1_mean**（r=-0.2458，唯一 PASS 且 lag 一致的负向候选）与 **W1C8D@PV1_mean**（r=+0.2440）做 2 水平小规模扰动试验（建议每水平 ≥5 批），以 oligomer 为主响应、total_defects 为副响应；
- 试验前先完成**尖峰批次成因核查**（oligomer std≈2×mean 提示零散尖峰），必要时改用稳健统计或变换后指标重算；
- MD_TH009/W1C8A 等 ΔR² 高但单变量 r 极低的参数属联合模型残差贡献，不宜单变量扰动验证。

### 3.4 下游使用规则

- 适用域：n=67，时间跨度 2026-05-04 14:42:00 .. 2026-05-13 05:51:00，工况限定 steady-state segments
- 失效条件：
  1. 任一因子越出 applicability_domain.factor_observed_ranges 的 ±20%
  2. stability_report 变点检测触发新 regime（漂移/换产）
  3. 确认试验结果与 expected_effect 的 CI95 不相交

- 使用规则（contract v1.0）：
  1. observational 窗口在闭环执行前必须先跑 confirmations
  2. confidence=low 的窗口仅可用于人工参考与试验设计，不得直接下发控制
  3. 本合同 operating_windows 为空（n=67 批、0/88 检验通过 FDR）：下游不得引用任何推荐区间，仅可引用 watchlist 候选自行设计确认试验

---

## 附：工件索引

| 工件 | 说明 |
|---|---|
| 00_input/analysis_context.json | 响应/因子角色定义（user 推断，无 group 列，observational 档） |
| 00_input/batches.csv | PG31DS 67 批 × 51 列（2 响应 + 44 过程量批次均值） |
| 01_profile/data_profile.json | 数据画像：observational 模式，LHS occupancy 0.15，无恒定列/高缺失列 |
| 02_analysis/correlation_report.json | 88 项相关 + 防伪判定 + ΔR² 贡献 + BH 多重检验 |
| 02_analysis/stability_report.json | 能力/正态性/稳态段/regime 分布（无变点、无漂移） |
| 03_figures/plot_manifest.json | 5 图清单（ink gate 全过） |
| conclusions/doe_conclusion.json | 主结论（authored_by=agent，KF-01~KF-06） |
| conclusions/recommendations.json | 下游合同 v1.0（0 窗口、4 条 watchlist，authored_by=agent） |
| run_manifest.json | run 元数据（script_version 1.0.0） |

图（03_figures/）：correlation_heatmap.png · contribution_bar.png · timeline_total_defects.png · timeline_oligomer.png · segments_total_defects.png

质量门：G1–G6 共 14 项检查全部 PASS（quality_gate.mjs exit 0，2026-10-01）。
