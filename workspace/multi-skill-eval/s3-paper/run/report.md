# 数据分析报告 — s3-paper/run

> 由 industrial-doe-analyzer 生成 · 分析模式 observational · 设计类型 observational ·
> 证据等级 B · 下游合同 recommendations.json v1.0

---

## 一、10 秒结论卡

| 项 | 值 |
|---|---|
| 关键因子（按效应强度） | 头箱压力 headbox_pressure_kPa（对 cd_cv：r=0.8688，唯一 L3/PASS）＞ 风泵转速 fan_pump_speed_rpm（r=0.8755，CAUTION）＞ 助留剂加入量 retention_aid_dosage_ppm（r=0.8595，CAUTION）＞ 白水浓度 white_water_consistency_pct（r=0.7509，CAUTION）；strength 侧最强为 fan_pump_speed_rpm（r=-0.7306，CAUTION） |
| 推荐操作窗口数 | 7（其中 7 条全部需先做确认试验；对应 1 条确认计划 CF-001，12 runs） |
| 预期收益（最优窗口） | OW-001：headbox_pressure_kPa ∈ [14.836, 20.86] kPa，窗内上三分位 vs 下三分位 strength_rel_pct 均值差 -2.676（CI95 [-4.166, -1.186]，方向已按目标校正；confidence=low） |
| 证据等级 | B（观察档：无随机化/纯误差自由度/分辨率/平衡可评，checklist 仅 anti_spurious_ok=true——0 FAIL、16 CAUTION、6 PASS） |
| 最重要的限制 | 全部为相关级证据且 16/22 对受共同时间趋势混杂；效应幅度为三牌号（GSM80/GSM100/GSM120）混线 pooled 估计——闭环前必须完成 CF-001 确认试验，且确认试验必须单牌号内执行 |

**一句话结论**：纸机流浆箱 11 个 DCS 参数与 cd 横幅 CV、相对强度的观测相关中，头箱压力是唯一通过全部防伪核验的强信号（L3），但整批数据处于 cd_cv 单调上行（段均值 0.577→3.067）、强度下行的慢漂移中，原始相关普遍被共同趋势放大；混线分层核验未发现任何跨牌号辛普森反转（方向稳健），故 7 个操作窗口可作为确认试验的设计蓝本，但任何窗口都不得在单牌号确认试验完成前闭环下发。

---

## 二、1 分钟证据层

### 2.1 效应/相关排序

|r|≥0.3 的 10 对相关（共 22 对；ΔR² 为因子级增量贡献，按 cd_basis_weight_cv_pct 全模型 r=0.8515 计算）：

| 响应 | 因子 | r | 去趋势 r | 最优滞后 | 滞后窗口一致 | 防伪裁决 | q(BH) | ΔR² |
|---|---|---:|---:|---:|:--:|:--:|---:|---:|
| cd_basis_weight_cv_pct | headbox_pressure_kPa | 0.8688 | 0.5725 | 0 | 否 | PASS（L3） | 0.0 | 0.022501 |
| cd_basis_weight_cv_pct | fan_pump_speed_rpm | 0.8755 | 0.4288 | -5 | 是 | CAUTION | 0.0 | 0.001834 |
| cd_basis_weight_cv_pct | retention_aid_dosage_ppm | 0.8595 | 0.3776 | +6 | 是 | CAUTION | 0.0 | 0.002376 |
| cd_basis_weight_cv_pct | white_water_consistency_pct | 0.7509 | 0.2476 | +1 | 是 | CAUTION | 0.0 | 0.000748 |
| cd_basis_weight_cv_pct | stock_temp_C | -0.5253 | 0.0073 | +8 | 是 | CAUTION | 0.0 | 0.000332 |
| strength_rel_pct | fan_pump_speed_rpm | -0.7306 | -0.2371 | +1 | 是 | CAUTION | 0.0 | 0.001834 |
| strength_rel_pct | retention_aid_dosage_ppm | -0.7183 | -0.2107 | -2 | 是 | CAUTION | 0.0 | 0.002376 |
| strength_rel_pct | headbox_pressure_kPa | -0.6484 | -0.1422 | -7 | 是 | CAUTION | 0.0 | 0.022501 |
| strength_rel_pct | white_water_consistency_pct | -0.6238 | -0.1305 | -6 | 是 | CAUTION | 0.0 | 0.000748 |
| strength_rel_pct | stock_temp_C | +0.4332 | -0.0230 | +10 | 是 | CAUTION | 0.0 | 0.000332 |

要点：
- 唯一 L3 级证据是 headbox_pressure_kPa × cd_cv（PASS 且 |r|≥0.3，去趋势后仍剩 0.5725）；其余强相关均为 CAUTION——共同时间趋势承载了原始相关的过半强度。
- stock_temp_C 是典型趋势伪相关：与 cd_cv 原始 -0.5253 去趋势后归零（0.0073）；与 strength 原始 +0.4332 去趋势后反号（-0.023）。不得据其操作浆温。
- 近零相关（|r|<0.3 的 12 对）：jet_to_wire_ratio、vacuum_pump1_kPa 两响应均无有效关联（q=0.209~0.663）；vacuum_pump2、slice_opening、machine_speed、approach_flow 的原始弱相关多被判定趋势混杂（CAUTION）或无实际效应（ΔR²≤0.0008）。

推荐操作窗口（7 条，全部 confidence=low、confirmation_needed=true）：

| 窗口 | 因子 | 范围 | 响应 | 预期均值差（方向已按目标校正） | CI95 | 样本量 |
|---|---|---|---|---:|---|---:|
| OW-001 | headbox_pressure_kPa | [14.836, 20.86] kPa | strength_rel_pct | -2.676 | [-4.166, -1.186] | 207 |
| OW-002 | fan_pump_speed_rpm | [875.4, 889.6] rpm | strength_rel_pct | -0.613 | [-0.984, -0.241] | 601 |
| OW-003 | stock_temp_C | [41.9, 50.6] °C | strength_rel_pct | -0.611 | [-0.997, -0.225] | 600 |
| OW-004 | stock_temp_C | [41.9, 50.6] °C | cd_basis_weight_cv_pct | -0.115 | [0.058, 0.173]（改善方向） | 600 |
| OW-005 | white_water_consistency_pct | [0.784, 0.963] % | cd_basis_weight_cv_pct | -0.099 | [0.044, 0.154]（改善方向） | 601 |
| OW-006 | fan_pump_speed_rpm | [875.4, 889.6] rpm | cd_basis_weight_cv_pct | -0.097 | [0.035, 0.160]（改善方向） | 601 |
| OW-007 | retention_aid_dosage_ppm | [172.0, 198.6] ppm | cd_basis_weight_cv_pct | -0.078 | [0.015, 0.140]（改善方向） | 601 |

当前基线（headbox_pressure 23.74 kPa、fan_pump 905.6 rpm、stock_temp 43.25 °C、white_water 1.043 %、retention 228.7 ppm）距 OW-001 上限 2.88 kPa，脚本建议优先将头箱压力下调进入 OW-001；OW-002/OW-006 距窗 16.0 rpm、OW-007 距窗 30.1 ppm。

### 2.2 关键图

| 图 | 内容 |
|---|---|
| `03_figures/correlation_heatmap.png` | 校正后相关矩阵（Validated correlation matrix） |
| `03_figures/contribution_bar.png` | cd_cv 的 ΔR² 因子贡献排序 |
| `03_figures/timeline_cd_basis_weight_cv_pct.png` | cd_cv 稳定性时间线（含变点） |
| `03_figures/timeline_strength_rel_pct.png` | strength 稳定性时间线（含变点） |
| `03_figures/segments_cd_basis_weight_cv_pct.png` | cd_cv 稳态段横向对比 |

全部 5 图通过 ink gate（ink_ok=true，最小 35,452 B）。

### 2.3 稳定性/能力（观察档适用）

- 过程能力：cd_cv 均值 1.776、整体 std 0.847、组内 σ(MR) 0.296；strength 均值 96.396、整体 std 3.036、组内 σ(MR) 1.960。两响应均无规格限（lsl/usl/target 未提供），Cp/Cpk 不可算。
- 分布：两响应均非正态（AD 统计量 24.04 与 2.74，均大于 5% 临界值 0.752）。
- 自相关：cd_cv lag-1 = 0.854（有效样本量 n_eff 仅 254）；strength lag-1 = 0.580（n_eff 862）——均值差区间须按强自相关口径解读。
- 工况regime：稳态占比 77.93%（steady 2525 行 / transition 715 行，窗宽 64 行）；共检出 12 个稳态段，其中 3 个最优段（n=244/86/271，合计 601）被选为窗口来源，段均值 cd_cv 0.577/0.641/0.811、strength 100.111/99.949/99.284。
- 变点与漂移：cd_cv 检出 16 个变点（17 段）、strength 检出 2 个变点（3 段）；drift_flags 为空（无显式漂移告警）。cd_cv 段均值沿时间单调上行（0.577→3.067）、strength 段均值下行（100.11→92.67），数据整体处于慢漂移之中。

---

## 三、深读审计层

### 3.1 模型与检验细节

- 多重检验：BH 程序，2 个族（两响应各 11 因子），共 22 次检验，q<0.05 显著 15 对。
- 防伪核验机制（group_col=grade 分层执行）：FAIL = 相关被离群驱动 / leave-one-out 杠杆不稳 / 跨层 Simpson 反转或方向翻转；CAUTION = 离群敏感 r 变化≥15% 或与共同时间趋势混杂；其余 PASS。证据分级：PASS 且 |r|≥0.3 记 L3，否则 L4。
- 判定分布：22 对中 **0 FAIL、16 CAUTION、6 PASS**；总体有效性判定 **SERIOUS_CONCERNS**（fatal_issues=0、serious_count=4、moderate_count=10；离群驱动 0、Simpson 反转 0、Spearman 分歧 0、偏度受扰列 1、反趋势检出变点 4）。
- 共线性警示：全模型 r=0.8515，但任一单因子 ΔR²≤0.0225——11 个 DCS 参数高度共线并随时间共同漂移，单因子"显著相关"不等于可单独操纵的杠杆。
- **多牌号混线结论可信度（本报告核心审计项）**：
  - 分层核验：以 grade 为分层变量运行防伪核验，**simpson_paradox_findings=0、spearman_divergence_findings=0**——三个牌号层内相关方向与合并方向一致，无跨牌号辛普森反转；亦无离群驱动与 LOU 不稳定（0 FAIL）。16 例 CAUTION 全部源于共同时间趋势，与牌号混合无关。
  - 各牌号层样本量（按输入数据计数）：GSM80=1053、GSM100=1091、GSM120=1096，各约占 1/3，层间均衡。
  - 窗口分层稳健性：7 个窗口的来源 3 个最优稳态段（n=601）内牌号配比 GSM80=184、GSM100=208、GSM120=209，同样均衡——窗口不是单一牌号段落的伪影；强相关对均通过跨滞后窗口一致性检验（lag_window_consistent=true）。
  - 残余风险：窗口 expected_effect 的**幅度**是跨牌号 pooled 估计，未按牌号拆分；且数据慢漂移与牌号排产在时间上纠缠（stock_temp 原始相关去趋势后消失/反号即为明证）。因此混线下结论"方向可信、幅度待确认"——CF-001 确认试验必须单牌号内执行。

### 3.2 披露与限制（全部保留，不得删除）

1. 观察性数据：全部结论为相关级（evidence B），执行任何操作窗口前必须完成 confirmations
2. 检出过程变点 — 结论仅适用于 applicability_domain 所限工况
3. 业务上下文：expected_effect 幅度为混线（grade 三层）pooled 估计，未按牌号分别建模；GSM80/GSM100/GSM120 定量与浆料配比不同，cd CV 与强度基线天然不同，确认试验与调优验证必须单牌号内执行
4. 业务上下文：12 个稳态段的 cd_cv 段均值沿时间单调上行（0.577→3.067）、strength 段均值下行（100.11→92.67，2025-10-01 至 2026-01-04），窗口取自最优（最早）3 段；当前基线（cd_cv=1.776、strength=96.40）已偏离窗口源工况，越晚执行确认试验失效风险越高
5. 业务上下文：全模型 r=0.8515 但任一单因子 ΔR²≤0.0225，11 个 DCS 参数高度共线且随时间共同漂移——单因子『显著相关』不等于可单独操纵的杠杆；两响应均非正态（AD 检验不过）且强自相关（lag-1 0.854/0.580，n_eff 仅 254/862），无规格限（lsl/usl/target）故 Cp/Cpk 不可算

### 3.3 确认试验计划

- CF-001（reason_code=observational，runs=12）：全部窗口来自观察性数据（相关级证据）— 闭环执行前必须确认。设计提示：在窗口中点附近做确认试验（每因子 ±半窗宽两点 + 中心点，2 次重复）。**执行约束：每个牌号内独立完成上述设计，确认结果与 expected_effect 的 CI95 不相交即触发失效条件。**

### 3.4 下游使用规则

1. observational 窗口在闭环执行前必须先跑 confirmations
2. confidence=low 的窗口仅可用于人工参考与试验设计，不得直接下发控制
3. 多牌号混线：expected_effect 为跨牌号 pooled 估计，确认试验与调优验证必须在同一牌号（grade）内执行，禁止跨牌号合并评估
4. stock_temp_C 与两响应的原始相关在去趋势后消失或反号（cd_cv：-0.5253→0.0073；strength：+0.4332→-0.023），不得以浆温作为调节手段，仅作监测项

- 适用域：n=3240，时间跨度 2025-10-01 07:24:30 .. 2026-01-04 05:57:30，工况限定 steady-state segments
- 观测因子范围：headbox_pressure_kPa [13.51, 39.84]、fan_pump_speed_rpm [864.4, 956.3]、stock_temp_C [31.9, 62.4]、white_water_consistency_pct [0.3, 2.0]、retention_aid_dosage_ppm [153.9, 298.5]
- 失效条件：任一因子越出观测范围 ±20%；stability_report 变点检测触发新 regime（漂移/换产）；确认试验结果与 expected_effect 的 CI95 不相交
- 监视清单（watchlist，4 条）：OBSERVATIONAL_EVIDENCE、TREND_CONFOUNDED_R、STOCK_TEMP_SIGN_FLIP、MIXED_GRADE_POOLED_ESTIMATE

---

## 附：工件索引

| 工件 | 说明 |
|---|---|
| `00_input/analysis_context.json` | 用户口径（group_col=grade，响应目标 min/max，权重 1.5/1.0） |
| `00_input/data.csv` | DCS+QCS 合并观测，3240 行 × 23 列 |
| `01_profile/data_profile.json` | 设计识别（observational，LHS 占用 0.08）、列角色、质量 |
| `02_analysis/correlation_report.json` | 22 对相关 + 滞后/去趋势/防伪核验 + BH + ΔR² |
| `02_analysis/stability_report.json` | 能力、12 稳态段、变点、regime 分布 |
| `03_figures/plot_manifest.json` | 5 图索引与 ink gate 结果 |
| `conclusions/doe_conclusion.json` | 主结论（KF-001~006，authored_by=agent） |
| `conclusions/recommendations.json` | 下游合同 v1.0（7 窗口 / 1 确认 / 4 监视项，authored_by=agent） |
| 质量门 | quality_gate.mjs：14/14 PASS（G2/G3/G4/G5/G6 含 strict key check），exit 0 |
