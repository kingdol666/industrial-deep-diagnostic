# 数据分析报告 — multi-skill-eval/s4-cement/run

> 由 industrial-doe-analyzer 生成 · 分析模式 observational · 设计类型 observational ·
> 证据等级 B · 下游合同 recommendations.json v1.0

---

## 一、10 秒结论卡

| 项 | 值 |
|---|---|
| 关键因子（按效应强度 ΔR²） | separator_speed_rpm（0.042534）＞ mill_power_kW（0.014649）＞ feed_moisture_pct（0.00254）＞ separator_current_A（0.001478）＞ mill_sound_dB（0.001342） |
| 推荐操作窗口数 | 12（其中 12 条需先做确认试验） |
| 预期收益（最优窗口） | OW-001：mill_power_kW 调至 [3297.47, 3594.63] → blaine_fineness_cm2g Δ=+98.004518 cm²/g（CI95 [70.299985, 125.709051]） |
| 证据等级 | B（观察档：grade_checklist 仅 anti_spurious_ok=true，无随机化/纯误差自由度/分辨率/平衡性，全部结论为相关级） |
| 最重要的限制 | 熟料来源（clinker_source）切换与慢漂移共线：16 起趋势混杂，top 相关去趋势后大幅衰减（mill_power_kW×blaine 0.8293→-0.0108），效应量为时代条件相关 |

**一句话结论**：在熟料来源切换混杂下，12 条观测窗口的方向经 clinker_source 分层 Simpson（0 起反转）、离群驱动（0 起）与留一杠杆核验未被推翻，但量级随 16 起趋势混杂与 6 个稳态段均值单调下行（strength 42.99→35.595417 MPa）塌缩为时代条件相关——全部 12 条窗口 confidence=low，闭环前必须先完成 CF-001 确认试验（限定单一熟料来源）。

---

## 二、1 分钟证据层

### 2.1 效应/相关排序

观察档无效应表，以下为通过 BH 多重检验校正的validated 相关排序（n=777，时间列 ts_lab，group_col=clinker_source；|r|≥0.3 的 top 对）：

| 响应 | 因子 | r | best_lag | 滞后窗一致 | 去趋势 r | ΔR² | q(BH) | 裁决 |
|---|---|---:|---:|:--:|---:|---:|---:|:--:|
| strength_28d_MPa | separator_speed_rpm | -0.9242 | 0 | 否 | -0.3559 | 0.042534 | 0.0 | CAUTION |
| strength_28d_MPa | reject_rate_pct | -0.8782 | 9 | 是 | -0.1290 | 0.000618 | 0.0 | CAUTION |
| strength_28d_MPa | mill_sound_dB | 0.8722 | -4 | 是 | 0.0704 | 0.001342 | 0.0 | CAUTION |
| strength_28d_MPa | separator_current_A | -0.8530 | 6 | 是 | -0.1754 | 0.001478 | 0.0 | CAUTION |
| strength_28d_MPa | mill_vibration_mm_s | -0.8297 | 4 | 是 | -0.0585 | 0.000074 | 0.0 | CAUTION |
| strength_28d_MPa | mill_power_kW | 0.8593 | 8 | 是 | -0.1834 | 0.014649 | 0.0 | CAUTION |
| strength_28d_MPa | mill_outlet_temp_C | 0.6654 | 1 | 是 | 0.0954 | 0.001201 | 0.0 | CAUTION |
| blaine_fineness_cm2g | separator_speed_rpm | -0.8682 | 2 | 是 | -0.2202 | 0.042534 | 0.0 | CAUTION |
| blaine_fineness_cm2g | reject_rate_pct | -0.8337 | 4 | 是 | -0.1217 | 0.000618 | 0.0 | CAUTION |
| blaine_fineness_cm2g | mill_power_kW | 0.8293 | 5 | 是 | -0.0108 | 0.014649 | 0.0 | CAUTION |
| blaine_fineness_cm2g | mill_sound_dB | 0.8224 | 8 | 是 | 0.0440 | 0.001342 | 0.0 | CAUTION |
| blaine_fineness_cm2g | separator_current_A | -0.7999 | 4 | 是 | -0.1062 | 0.001478 | 0.0 | CAUTION |
| blaine_fineness_cm2g | mill_vibration_mm_s | -0.7958 | 9 | 是 | -0.0981 | 0.000074 | 0.0 | CAUTION |
| blaine_fineness_cm2g | mill_outlet_temp_C | 0.6357 | 5 | 是 | 0.0921 | 0.001201 | 0.0 | CAUTION |

多重检验：BH 法，2 族 × 12 因子 = 24 次检验，q<0.05 显著 20 次；不显著 4 次为 feed_moisture_pct（q=0.145/0.802）与 gypsum_dosage_pct（q=0.972/0.995）。24 对的逐对 trend_confounded 标记均为 true；防伪汇总判定趋势混杂 16 起（moderate_count=16）、离群驱动 0 起、Simpson 悖论 0 起、Spearman 分歧 0 起、fatal/serious 均 0，overall_validity=MODERATE_CONCERNS。

### 2.2 关键图

| 图 | 内容 | 墨水门 |
|---|---|:--:|
| `03_figures/correlation_heatmap.png` | 校正后相关矩阵（四象限墨水比 55.8%） | PASS |
| `03_figures/contribution_bar.png` | strength_28d_MPa 的 ΔR² 因子贡献排序（11.2%） | PASS |
| `03_figures/timeline_strength_28d_MPa.png` | strength 稳定性时间线（64.3%） | PASS |
| `03_figures/timeline_blaine_fineness_cm2g.png` | blaine 稳定性时间线（63.2%） | PASS |
| `03_figures/segments_strength_28d_MPa.png` | strength 稳态段对比（40.6%） | PASS |

### 2.3 稳定性/能力（观察档适用）

**过程能力**（specs 仅 blaine 有：LSL 3400 / Target 3600 / USL 3800）：

| 响应 | 均值 | 总体σ | 组内σ(MR) | Cp | Cpk | Pp | Ppk | Cnp | 正态 | lag1 自相关 | n_eff |
|---|---:|---:|---:|---:|---:|---:|---:|---:|:--:|---:|---:|
| strength_28d_MPa（maximize） | 38.73982 | 2.475487 | 0.727876 | — | — | — | — | — | 否（AD=3.9646>0.751） | 0.9006 | 40/777 |
| blaine_fineness_cm2g（target 3600） | 3522.875 | 161.1117 | 62.89185 | 1.0600 | 0.6513* | 0.4138 | 0.2542 | 0.3109 | 否（AD=2.1905>0.751） | 0.7760 | 98/777 |

\* Cpk 为非正态指示值；blaine 当前均值 3522.875 低于目标 3600，Ppk=0.254 / Cnp=0.311 显示实际过程能力不足。两响应强正自相关，有效样本量远小于表面 n。

**稳态分段与漂移**（regime 检出：steady 672 行 86.49%，transition 105 行 13.51%）：

| 段（行区间） | n | strength 均值 | blaine 均值 | 得分 | 入选窗口 |
|---|---:|---:|---:|---:|:--:|
| 0–55 | 56 | 42.99 | 3768.196 | 21.607 | 是 |
| 77–194 | 118 | 41.360 | 3682.110 | 20.920 | 是 |
| 216–265 | 50 | 40.309 | 3622.540 | 20.446 | 是 |
| 287–531 | 245 | 38.111 | 3488.310 | 19.218 | 否 |
| 553–731 | 179 | 36.273 | 3378.028 | 18.095 | 否 |
| 753–776 | 24 | 35.595 | 3306.958 | 17.660 | 否 |

6 个稳态段两响应均值沿时间单调下行；strength_28d_MPa 检出 3 个变点（行 186/298/565，4 段 3 变）；drift_flags 为空。

---

## 三、深读审计层

### 3.1 模型与检验细节

- **模式判定**：observational——因子为连续量（LHS 占位率仅 0.13 < 0.85）、无设计实验签名；main_bearing_temp_C 缺失 2 行（n=775 生效），无重复行/常数列。
- **时间结构**：ts_lab 排序校验通过（777 唯一时间值）；滞后搜索窗 ±10 步，5 条 top 对中 4 对滞后窗一致（separator×strength 为 best_lag=0 且滞后窗不一致）。
- **熟料来源混杂下的窗口可信度（专项核验）**：
  - **分层/Simpson**：group_col=clinker_source（2 个水平）已纳入逐对防伪检验——simpson_paradox_findings=0，全部 24 对 simpson 裁决未触发，即分层后未出现任何"组内方向与合并方向相反"的悖论，top 相关的**方向**不是来源切换的分层伪象；
  - **离群/杠杆**：outlier_driven_correlations=0，|r|≥0.3 的核验对中离群敏感=OK、留一杠杆=false（无单点杠杆驱动）——相关**不是**少数异常批次制造的；
  - **趋势混杂**：判定 16 起（moderate_count=16，overall_validity=MODERATE_CONCERNS），且 24 对逐对 trend_confounded=true——去趋势后 top 对普遍塌缩：mill_power_kW×blaine 0.8293→-0.0108、mill_sound×strength 0.8722→0.0704、mill_power×strength 0.8593→-0.1834，仅 separator_speed×strength 保留 -0.3559（24 对中去趋势后 |r| 最高）；
  - **与漂移证据互证**：6 个稳态段均值单调下行（strength 42.99→35.595417 MPa，blaine 3768.196→3306.958 cm²/g）+ strength 3 个变点（186/298/565），与"熟料来源切换构成慢移动混杂、抬高原始相关"的机理一致；
  - **top 窗口 OW-001 防伪结论**：底层相关 r=0.8293（q=0.0，best_lag=5 且滞后窗一致）通过离群/杠杆/Simpson 三道防伪，但趋势项失败（去趋势 r=-0.0108），且窗口取自行 0-265 的 3 个最优**早期**稳态段（n=224），当前基线 mill_power_kW=3090.9 距窗口下沿 206.57 kW——**方向可作试验设计线索，量级属熟料来源时代条件相关**，confidence=low 与 confirmation_needed=true 维持不变；
  - **总判定**：12 条窗口在熟料来源混杂下"方向存疑度低、量级可信度低"——任何窗口的 Δ 效应量未经 CF-001 单源确认前不得用于闭环。

### 3.2 披露与限制（全部保留，不得删除）

1. 观察性数据：全部结论为相关级（evidence B），执行任何操作窗口前必须完成 confirmations
2. 检出过程变点 — 结论仅适用于 applicability_domain 所限工况
3. group_col=clinker_source（熟料来源，2 个水平，用户标注 switching trap）为已知混杂：分层 Simpson 核验 0 起反转、离群驱动判定 0 起、fatal/serious 均 0，但趋势混杂判定 16 起（overall_validity=MODERATE_CONCERNS）；6 个稳态段均值随时间单调下行（strength 42.99→35.595417 MPa，blaine 3768.196429→3306.958333 cm²/g）并检出 3 个 strength 变点（行 186/298/565），原始相关与熟料来源切换/慢漂移共线，去趋势后 top 相关大幅衰减（mill_power_kW×blaine 由 0.8293 降至 -0.0108）
4. 12 条窗口全部取自 3 个最优早期稳态段（数据行 0-55/77-194/216-265，合计 n=224），代表早期熟料来源时代工况；当前基线（mill_power_kW=3090.9）距 OW-001/OW-008 窗口下沿 206.57 kW、separator_speed_rpm 基线（1072.4）距 OW-003/OW-007 上沿 75.57——跨时代调整可信度最低，必须先完成 CF-001 确认
5. 两响应均非正态且强正自相关（strength_28d_MPa：AD=3.9646>0.751，lag1=0.9006，n_eff=40/777；blaine：AD=2.1905>0.751，lag1=0.776，n_eff=98/777），有效样本量远小于表面 n=777；blaine 的 Cpk=0.651 为非正态指示值（Ppk=0.254、Cnp=0.311 更保守），当前均值 3522.875 低于目标 3600 且过程能力不足

### 3.3 确认试验计划

| ID | 原因 | reason_code | 设计提示 | 运行数 |
|---|---|---|---|---:|
| CF-001 | 全部窗口来自观察性数据（相关级证据）— 闭环执行前必须确认 | observational | 在窗口中点附近做确认试验（每因子 ±半窗宽两点 + 中心点，2 次重复） | 12 |

执行约束（来自 watchlist）：确认须**限定单一熟料来源**内完成，或按来源分层各做一轮；OW-001 的确认均值差须落入 CI95 [70.299985, 125.709051] cm²/g 方可闭环。

### 3.4 下游使用规则

- 观察性窗口在闭环执行前必须先跑 confirmations
- confidence=low 的窗口仅可用于人工参考与试验设计，不得直接下发控制
- 确认试验须限定单一熟料来源（clinker_source）内完成，或按来源分层各执行一轮后再合并判定；跨来源切换点执行无效
- 窗口效应量为去趋势前观测值：执行前核对 stability_report 无新增变点、稳态段均值未延续历史单调漂移，否则按 invalidation_conditions 第 2 条停用合同

- 适用域：n=777，时间跨度 2025-10-01 01:44:50 .. 2025-12-31 15:22:50，工况限定 steady-state segments
  - 因子观测域：mill_power_kW [2601.8, 3654.0] · reject_rate_pct [8.0, 40.11] · separator_speed_rpm [874.9, 1258.6] · mill_vibration_mm_s [1.0, 6.959] · mill_outlet_temp_C [88.1, 119.7] · main_bearing_temp_C [50.8, 76.8]
- 失效条件：
  1. 任一因子越出 applicability_domain.factor_observed_ranges 的 ±20%
  2. stability_report 变点检测触发新 regime（漂移/换产）
  3. 确认试验结果与 expected_effect 的 CI95 不相交

---

## 附：工件索引

| 工件 | 说明 |
|---|---|
| `00_input/analysis_context.json` | 用户上下文（2 响应/12 因子/group_col=clinker_source） |
| `01_profile/data_profile.json` | 数据画像：777 行 × 23 列，observational 判定（LHS 占位 0.13） |
| `02_analysis/correlation_report.json` | 24 对校验相关 + 防伪裁决 + BH 校正 |
| `02_analysis/stability_report.json` | 过程能力/稳态段/变点/regime |
| `03_figures/plot_manifest.json` | 5 图索引（全部 ink_ok） |
| `conclusions/doe_conclusion.json` | 主结论（evidence B，authored_by=agent） |
| `conclusions/recommendations.json` | 下游合同 v1.0：12 窗口/1 确认/4 watchlist（authored_by=agent） |
| `run_manifest.json` | 运行清单（script_version 1.0.0） |
| `report.md` | 本报告 |

质量门：G1–G6 共 14/14 PASS（exit 0）。
