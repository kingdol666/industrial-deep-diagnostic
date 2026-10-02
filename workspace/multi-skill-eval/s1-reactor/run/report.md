# 数据分析报告 — s1-reactor（multi-skill-eval）

> 由 industrial-doe-analyzer 生成 · 分析模式 observational · 设计类型 observational ·
> 证据等级 B · 下游合同 recommendations.json v1.0

---

## 一、10 秒结论卡

| 项 | 值 |
|---|---|
| 关键因子（按效应强度） | reactor_temp_C（ΔR²=0.1661）> reactor_pressure_bar（0.0712）> h2_partial_pressure_bar（0.0490）；feed_rate_kg_hr 与 feed_sulfur_ppm 贡献≈0（q=0.535–0.877） |
| 推荐操作窗口数 | 2（其中 2 条均需先做确认试验——共用 1 套确认计划 CF-001，共 6 run） |
| 预期收益（最优窗口） | OW-001：reactor_temp_C∈[183.9, 186.6] °C → quality_index 三分位均值差 +0.7082（CI95 [0.1026, 1.3139]，n=170） |
| 证据等级 | B（观察性数据：随机化/纯误差自由度/分辨率/平衡性均不适用，仅防伪校验 anti_spurious_ok=true；全部结论为相关级，非因果） |
| 最重要的限制 | 共享时间趋势混杂 + 过程变点（quality_index 行 305；conversion_pct 行 301/598）：两个窗口的取材段全部位于变点前高稳态平台，窗口能否外推到变点后工况必须由确认试验裁决 |

**一句话结论**：加氢反应器 1440 行观测数据显示温度/压力/氢分压与 quality_index、conversion_pct 全部显著相关（唯一通过全部防伪校验的配对为 reactor_temp_C→conversion_pct，r=-0.7349），首选动作是将反应温度自基线 187.2 °C 下调入窗 [183.9, 186.6] °C（预期 quality_index +0.71）；证据等级 B（相关级），6-run 确认试验通过前不得闭环执行。

---

## 二、1 分钟证据层

### 2.1 效应/相关排序

10 组配对（2 响应 × 5 因子，n=1440，BH 校正共 6 组 q<0.05 显著）：

| 响应 | 因子 | r | 最优滞后（滞后 r） | 滞后窗口一致 | 去趋势 r | ΔR² | 防伪裁决 | 证据级 | q(BH) |
|---|---|---|---|---|---|---|---|---|---|
| conversion_pct | reactor_temp_C | **-0.7349** | 2（-0.7360） | 是 | -0.4582 | 0.1661 | **PASS** | L3 | 0.0 |
| quality_index | reactor_temp_C | -0.7025 | 1（-0.7199） | 是 | -0.3879 | 0.1661 | CAUTION | L4 | 0.0 |
| conversion_pct | reactor_pressure_bar | -0.6031 | 0（-0.6031） | 否 | -0.3447 | 0.0712 | CAUTION | L4 | 0.0 |
| quality_index | reactor_pressure_bar | -0.5824 | 3（-0.5929） | 是 | -0.3048 | 0.0712 | CAUTION | L4 | 0.0 |
| conversion_pct | h2_partial_pressure_bar | +0.5245 | 1（+0.5247） | 是 | +0.3049 | 0.0490 | CAUTION | L4 | 0.0 |
| quality_index | h2_partial_pressure_bar | +0.5065 | 2（+0.5111） | 是 | +0.2700 | 0.0490 | CAUTION | L4 | 0.0 |
| quality_index | feed_rate_kg_hr | -0.0041 | 12（-0.0230） | 否 | -0.0882 | 0.0010 | CAUTION（趋势混杂） | L4 | 0.8764 |
| quality_index | feed_sulfur_ppm | -0.0116 | 3（-0.0268） | 否 | +0.0138 | 0.0001 | CAUTION（趋势混杂） | L4 | 0.8268 |
| conversion_pct | feed_rate_kg_hr | +0.0209 | 0（+0.0209） | 否 | -0.0489 | 0.0010 | CAUTION（趋势混杂） | L4 | 0.5351 |
| conversion_pct | feed_sulfur_ppm | -0.0070 | -7（-0.0325） | 否 | +0.0244 | 0.0001 | CAUTION（趋势混杂） | L4 | 0.7910 |

解读要点：

- 方向（按 maximize 目标）：温度、压力与两响应负相关——低温度/低压力区间对应更优响应；氢分压与两响应正相关。
- 唯一 PASS 配对为 reactor_temp_C→conversion_pct（去趋势后 r=-0.4582 仍中等强度）；其余显著配对均因原始相关含共享时间趋势成分降为 CAUTION。
- 注意：脚本 key_findings 基线列出 5 条（KF-001~005）；quality_index↔h2_partial_pressure_bar（r=+0.5065，q=0.0）同为显著配对，见上表第 6 行。

### 2.2 关键图

| 图 | 文件 | 说明 |
|---|---|---|
| 校验后相关矩阵 | 03_figures/correlation_heatmap.png | 10 组配对的相关结构（墨水比 51.4%，ink_ok） |
| ΔR² 贡献排序 | 03_figures/contribution_bar.png | quality_index 的因子贡献排序（墨水比 17.9%） |
| 稳定性时间线 | 03_figures/timeline_quality_index.png | quality_index 全程走势 + 变点（墨水比 60.1%） |
| 稳定性时间线 | 03_figures/timeline_conversion_pct.png | conversion_pct 全程走势 + 变点（墨水比 59.3%） |
| 稳态段对比 | 03_figures/segments_quality_index.png | 12 个稳态段均值对比（墨水比 41.3%） |

5 图全部通过墨水门（G5）。

### 2.3 稳定性/能力（观察档适用）

**过程能力（无规格限，has_specs=false，Cp/Cpk 不适用）**：

| 响应 | 均值 | 总体 std | 组内 σ(MR) | lag-1 自相关 | 有效样本 n_eff | 正态性 |
|---|---|---|---|---|---|---|
| quality_index | 81.454 | 6.958 | 2.057 | 0.911 | 67 | 非正态（AD=32.58 ≫ 0.752） |
| conversion_pct | 81.534 | 6.868 | 0.807 | 0.984 | 11 | 非正态（AD=54.65 ≫ 0.752） |

两响应自相关极高（尤其 conversion_pct，n_eff≈11），显著性判断以 q(BH) 与去趋势稳健性为准，名义 n=1440 不可直接当独立样本数。

**稳态分段与变点**：检出 12 个稳态段，稳态占比 77.85%（1121/1440 行）。质量最高的 3 段全部位于运行初期（行 0–15/45–130/160–294，quality_index 段均值 92.68/92.89/92.73，conversion_pct 93.20/93.08/93.06），远高于全程均值 81.45/81.53；此后逐级下行至末段 77.50/77.87（行 1198–1239 段部分回升至 79.48/79.16）。变点检测：quality_index 在行 305（1 个变点）、conversion_pct 在行 301、598（2 个变点）。**两个操作窗口的取材段全部取自变点前高平台**——下行漂移（催化剂工况演变等）与因子变化共享时间趋势，是多数配对防伪降级为 CAUTION 的主因。

---

## 三、深读审计层

### 3.1 模型与检验细节

- **设计判定**：observational——因子为连续/混合类型，LHS 占用率仅 0.06（<0.85），未匹配任何设计实验签名；分辨率/生成元/别名链不适用。
- **多重检验**：BH 法，2 个响应族 × 5 因子 = 10 次检验，q<0.05 显著 6 组（见 2.1 表）。
- **防伪汇总**：overall_validity = MODERATE_CONCERNS——趋势混杂相关 5 组（serious 2、moderate 5，无 fatal），Simpson 悖论 0，离群点驱动相关 0，偏度受损列 0，变点 2 个；|r|≥0.3 的配对全部携带防伪裁决与 verdicts（G2 通过）。
- **OW-002 一致性警示（重要）**：feed_sulfur_ppm∈[5.4, 7.7]→conversion_pct 窗口（三分位均值差 +0.4068，CI95 [0.1532, 0.6603]，n=162）是稳态段内的描述性差异；该配对的全局相关不显著（r=-0.007，q=0.791）。窗口效应与全局证据不一致，使用前必须由确认试验裁决，不得凭窗口直接操作。
- **OW-001 依据链**：reactor_temp_C∈[183.9, 186.6] 取自 3 个最优稳态段温度的 P10-P90；窗内上三分位 vs 下三分位的 quality_index 均值差 +0.7082（方向已按 maximize 目标校正）；当前基线 187.2 °C 高于窗上沿 0.6 °C，move 优先级 1。
- **时间排序校验**：timestamp 1440 个唯一值、时间升序，滞后相关有效。

### 3.2 披露与限制（全部保留，不得删除）

- 观察性数据：全部结论为相关级（evidence B），执行任何操作窗口前必须完成 confirmations。
- 检出过程变点 — 结论仅适用于 applicability_domain 所限工况。
- 5 组配对原始相关含共享时间趋势成分（去趋势后普遍衰减 40–50%），因果强度有限。
- 两响应非正态且自相关极高（n_eff=67/11），效应区间宽度受有效样本限制。
- OW-002 与全局相关不一致（见 3.1），confidence=low。

### 3.3 确认试验计划

**CF-001**（覆盖 OW-001 与 OW-002，共 6 run）：

- 原因：全部窗口来自观察性数据（相关级证据）— 闭环执行前必须确认（reason_code=observational）。
- 设计提示：在窗口中点附近做确认试验（每因子 ±半窗宽两点 + 中心点，2 次重复）。
  - OW-001（reactor_temp_C，窗 [183.9, 186.6] °C）：建议点 ≈184.1 / 185.25 / 186.4 °C；
  - OW-002（feed_sulfur_ppm，窗 [5.4, 7.7] ppm）：建议点 ≈5.65 / 6.55 / 7.45 ppm。
- 判定：确认结果须落入 expected_effect 的 CI95（OW-001 [0.1026, 1.3139]；OW-002 [0.1532, 0.6603]），否则触发失效条件并回退。

### 3.4 下游使用规则

1. observational 窗口在闭环执行前必须先跑 confirmations。
2. confidence=low 的窗口仅可用于人工参考与试验设计，不得直接下发控制。

- 适用域：n=1440，时间跨度 2026-04-01 00:00 .. 2026-05-30 23:00，工况限定 steady-state segments（因子观测域：reactor_temp_C 182.7–190.5 °C；feed_sulfur_ppm 5.0–8.0 ppm）。
- 失效条件：① 任一因子越出 applicability_domain.factor_observed_ranges 的 ±20%；② stability_report 变点检测触发新 regime（漂移/换产）；③ 确认试验结果与 expected_effect 的 CI95 不相交。

---

## 附：工件索引

| 工件 | 路径 |
|---|---|
| 分析上下文 | 00_input/analysis_context.json |
| 数据画像 | 01_profile/data_profile.json（1440 行 × 16 列，质量项全零缺陷） |
| 相关报告 | 02_analysis/correlation_report.json |
| 稳定性报告 | 02_analysis/stability_report.json |
| 图清单 | 03_figures/plot_manifest.json（5 图，全部 ink_ok） |
| 主结论 | conclusions/doe_conclusion.json（authored_by=agent） |
| 下游合同 | conclusions/recommendations.json（authored_by=agent，contract v1.0） |
| 运行清单 | run_manifest.json |
| 输入数据 | 00_input/data.csv（sha256 前缀 86a5f2af…） |

质量门：G1–G6 共 14 项检查 ALL PASS（exit 0）。
