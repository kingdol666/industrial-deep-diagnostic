# 数据分析报告 — s2-hex/run（换热器结垢工况观测数据）

> 由 industrial-doe-analyzer 生成 · 分析模式 observational · 设计类型 observational ·
> 证据等级 B · 下游合同 recommendations.json v1.0

---

## 一、10 秒结论卡

| 项 | 值 |
|---|---|
| 关键因子（按效应强度） | 与热效率 \|r\|：heat_transfer_coeff_W_m2K (0.9543) > hot_outlet_temp_C (0.8873) > approach_temp_C (0.8212) > lmtd_C (0.8081) > cold_outlet_temp_C (0.7944)；ΔR² 前两位：heat_transfer_coeff_W_m2K (0.0267)、cold_inlet_temp_C (0.0181) |
| 推荐操作窗口数 | 6（其中 6 条需先做确认试验，confidence 均为 low） |
| 预期收益（最优窗口） | OW-001：heat_transfer_coeff_W_m2K → [980, 1081] W/m²K，热效率预期 +3.706 pct（95% CI 3.446–3.966），同时压降预期 -0.303 bar（OW-004，CI95 -0.316–-0.291） |
| 证据等级 | B（观察性数据：随机化/纯误差自由度/分辨率/均衡四项清单均不适用，防伪检验通过但 overall_validity=SERIOUS_CONCERNS，等级由清单确定性计算） |
| 最重要的限制 | 6 个窗口全部派生自漂移早期轻垢工况（稳态段行 0-401，约 08-01 至 08-09），当前工况已沿结垢漂移显著偏离，闭环执行前必须完成 CF-001 确认试验 |

**一句话结论**：结垢缓变漂移主导全程——热效率稳态段均值由 87.13 总体漂移下行至 75.28、压降由 0.765 单调爬升至 2.671 bar，最强伴随因子是传热系数（r=0.9543，去趋势 0.9373）；6 个推荐窗口均为漂移前的相关级（B 级）结论，且传热系数是状态变量而非可下发操作变量，确认试验前不得闭环。

---

## 二、1 分钟证据层

### 2.1 效应/相关排序

热效率 thermal_efficiency_pct（目标 maximize，全程均值 78.674）：

| 参数 | r（原始） | r（去趋势） | 最优滞后（行） | q(BH) | 防伪裁决 | 证据级 |
|---|---:|---:|---:|---:|---|:--:|
| heat_transfer_coeff_W_m2K | +0.9543 | +0.9373 | 0 | 0.000 | PASS | L3 |
| hot_outlet_temp_C | -0.8873 | -0.8357 | 0 | 0.000 | PASS | L3 |
| approach_temp_C | -0.8212 | -0.7935 | -13（≈6.5 h） | 0.000 | PASS | L3 |
| lmtd_C | -0.8081 | -0.7936 | -13 | 0.000 | PASS | L3 |
| cold_outlet_temp_C | +0.7944 | +0.7956 | -12 | 0.000 | PASS | L3 |
| cold_inlet_temp_C | +0.5307 | +0.7651 | -12 | 0.000 | CAUTION | L4 |
| hot_inlet_temp_C | -0.0034 | +0.0018 | — | 0.876 | CAUTION（趋势混杂） | L4 |

压降 pressure_drop_bar（目标 minimize，全程均值 1.763）：

| 参数 | r（原始） | r（去趋势） | 最优滞后（行） | q(BH) | 防伪裁决 | 证据级 |
|---|---:|---:|---:|---:|---|:--:|
| heat_transfer_coeff_W_m2K | -0.6430 | -0.5232 | -1 | 0.000 | PASS | L3 |
| hot_outlet_temp_C | +0.6024 | +0.4851 | -6 | 0.000 | PASS | L3 |
| approach_temp_C | +0.4948 | +0.4439 | 0 | 0.000 | PASS | L3 |
| lmtd_C | +0.4661 | +0.4421 | 0 | 0.000 | PASS | L3 |
| cold_outlet_temp_C | -0.4345 | -0.4351 | 0 | 0.000 | PASS | L3 |
| cold_inlet_temp_C | -0.0375 | -0.4030 | 0 | 0.095 | CAUTION（趋势混杂） | L4 |
| hot_inlet_temp_C | +0.0108 | +0.0592 | — | 0.617 | CAUTION（趋势混杂） | L4 |

- 多重检验：BH，2 族 × 14 检验，11 项 q<0.05；3 项不显著（热效率~热进口温度、压降~热进口温度、压降~冷进口温度）。
- ΔR² 贡献（热效率）：heat_transfer_coeff_W_m2K 0.026708 > cold_inlet_temp_C 0.018103，其余因子 ≈0——但全模型 r=0.9359，说明 7 因子高度共线，单一因子 ΔR² 不代表独立效应。
- 冷进口温度两行 CAUTION：原始 r 与去趋势 r 差距大（0.531→0.765；-0.038→-0.403），共线时间趋势扭曲了原始相关，使用时须以去趋势值为参考。

### 2.2 关键图

| 图 | 文件 | 说明 |
|---|---|---|
| 相关矩阵（防伪校验后） | `03_figures/correlation_heatmap.png` | 14 对相关的 PASS/CAUTION 分布 |
| ΔR² 贡献排序 | `03_figures/contribution_bar.png` | 热效率：传热系数、冷进口温度两位领先 |
| 热效率稳定 timeline | `03_figures/timeline_thermal_efficiency_pct.png` | 全程下行漂移 + 5 个变点 |
| 压降稳定 timeline | `03_figures/timeline_pressure_drop_bar.png` | 全程连续爬升（55 变点） |
| 稳态段对比 | `03_figures/segments_thermal_efficiency_pct.png` | 17 段均值阶梯下行 |

全部 5 图通过 ink gate（ink_ok=true）。

### 2.3 稳定性/能力（观察档适用）

**漂移判定（结垢特征三联征齐备）**

- 热效率随时间衰减：是。17 个稳态段均值 87.13 → 85.37 → 83.66 → … → 72.29（行 1216-1291 段最低）→ 回升 79.11（行 1335-1418）→ 再下行至 75.28（行 2085-2159），总降幅约 11.85 pct（起点到终点 87.13→75.28）。
- 变点位置：热效率 5 个变点，行 374 / 651 / 993 / 1300 / 1768（数据 30 min/行，约 08-08 19:00、08-14 13:30、08-21 16:30、08-28 02:00、09-06 20:00），6 段；压降 55 个变点（56 段）遍布全程，呈连续漂移而非台阶突变——典型的缓变结垢漂移形态。
- 压降单调爬升：17 段均值 0.765 → 2.671 bar 单调不减，与热效率下行互为印证。
- `drift_flags` 为空：脚本的旗标器未触发，但段均值轨迹即漂移证据（已在 limitations 披露），使用窗口前须自行核对漂移时效。

**窗口与漂移后工况的关系**

- 6 个窗口全部取自前 3 个最优稳态段（行 0-119 / 163-224 / 268-401，约 08-01 至 08-09，热效率段均值 83.66–87.13、压降 0.77–1.05），即**漂移前轻垢工况，不是漂移后工况**；首个变点（行 374）已落在第三个窗口段内。
- 当前基线（全程均值口径）：热效率 78.67 已低于窗口段水平，压降 1.76 已高于窗口段水平——窗口若直接套用于当前重垢工况属工况失配，必须先确认。

**过程能力**

- 两响应均无规格限（has_specs=false），**Cp/Cpk/Pp/Ppk 全部为 null，不可计算**。
- 替代稳定性证据：热效率整体标准差 3.967 vs 组内 MR 标准差 0.789（lag-1 自相关 0.960，n_eff=44）；压降 0.579 vs 0.031（自相关 0.997）——整体散布远大于组内散布，漂移主导总方差，过程不处于单一统计受控状态；两响应均未通过正态检验（AD 统计量 34.774 / 25.654 > 临界 0.752）。
- 工况分割：稳态行占比 68.15%（1472/2160），过渡行 31.85%（688），稳态窗 43 行。

---

## 三、深读审计层

### 3.1 模型与检验细节

- 模式判定：observational（LHS 占用率 0.03 < 0.85，无设计实验签名；连续因子，离散设计规则跳过）。数据 2160 行 × 16 列，无重复行、无缺失目标；7 因子 / 2 响应 / 6 列 ignore（含真实操作变量 flow_rate_m3_hr、pump_speed_pct，见 3.2 限制）。
- 时间排序校验通过（timestamp 唯一且有序，2026-08-01 00:00 至 2026-09-14 23:30，30 min/行）。
- 滞后补偿 CCF（max_lag=15）：approach_temp_C / lmtd_C 最优滞后 -13 行、cold_outlet_temp_C -12 行且滞后窗一致，去趋势后相关仍 ≥0.79，排除纯趋势伴随；heat_transfer_coeff_W_m2K 滞后 0（热效率）/ -1（压降）。
- 防伪汇总（脚本原文，不得删除）：**overall_validity = "SERIOUS_CONCERNS — Multiple statistical robustness issues detected. Key correlations should be re-verified before drawing causal conclusions."**（serious 3 项、moderate 1 项、fatal 0；outlier-driven 0、Simpson 0、Spearman 分歧 0；趋势混杂相关 3 对：热效率~热进口温度、压降~热进口温度、压降~冷进口温度）。全部结论仅到相关级，非因果。
- 6 窗口效应均为"窗内上三分位 vs 下三分位"的均值差（方向已按目标校正），n=210/224，CI95 均不含 0；因三分位分组仍受共线因子影响，delta 是窗口内的伴随差异而非独立效应。

### 3.2 披露与限制（全部保留，不得删除）

1. 观察性数据：全部结论为相关级（evidence B），执行任何操作窗口前必须完成 confirmations
2. 检出过程变点 — 结论仅适用于 applicability_domain 所限工况
3. [agent 补充·漂移轨迹] 热效率呈缓变下行漂移（结垢特征）：17 个稳态段均值由 87.13（行 0-119 段）总体降至 75.28（行 2085-2159 段），行 1216-1291 段触及最低 72.29 后于行 1335-1418 回升至 79.11 再继续下行；热效率检出 5 个变点（行 374/651/993/1300/1768，按 30 min/行折算约 08-08 19:00 至 09-06 20:00）；压降 17 段均值全程单调爬升 0.765→2.671 bar，检出 55 个变点（56 段）呈连续漂移而非台阶突变。stability_report.drift_flags 为空，漂移证据来自段均值轨迹，使用时须自行核对漂移时效
4. [agent 补充·能力指数] 两响应均未提供规格限（has_specs=false），Cp/Cpk/Pp/Ppk 全部为 null（不可计算）；替代证据显示漂移主导总方差：热效率整体标准差 3.967 vs 组内 MR 标准差 0.789（lag-1 自相关 0.960，n_eff=44），压降 0.579 vs 0.031（自相关 0.997），整体散布远大于组内散布，过程不处于单一统计受控状态；两响应均未通过正态检验（AD 统计量 34.774 / 25.654，临界 0.752）
5. [agent 补充·窗口时效] 6 个操作窗口全部派生自前 3 个最优稳态段（行 0-401，约 08-01 至 08-09 的轻垢工况），位于主要漂移发生之前而非漂移后工况；当前基线热效率 78.67（全程均值）已低于窗口段水平 83.66–87.13，压降 1.76 已高于窗口段 0.77–1.05；窗口外推至当前重垢工况前必须完成 CF-001 确认试验
6. [agent 补充·物理可操作性] heat_transfer_coeff_W_m2K 是结垢状态变量而非可直接设定的操作变量：达到 OW-001/OW-004 窗口（980–1081 W/m²K，当前 910，距下限 70）需依赖清洗/在线防垢等维护措施；实际操作变量 flow_rate_m3_hr、pump_speed_pct 在本次分析中被列为 ignore，未纳入因子

### 3.3 确认试验计划

- **CF-001**（runs=8，reason_code=observational）：全部窗口来自观察性数据（相关级证据），闭环执行前必须确认。
- 设计提示：在窗口中点附近做确认试验（每因子 ±半窗宽两点 + 中心点，2 次重复）。
- 优先次序（按 priority）：OW-001 传热系数→热效率（+3.706）→ OW-002 热出口温度→热效率（-2.926）→ OW-003 冷进口温度→热效率（-1.999）→ OW-004/005/006（压降三窗口，delta -0.303 / +0.248 / +0.163）。
- 当前基线与窗口距离：传热系数 910 → OW 下限 980（距离 70）；热出口温度 70.6 °C → OW 上限 69.45（距离 1.15）；冷进口温度 22.1 °C → OW 下限 23.6（距离 1.5）。
- 判定准则：确认结果与 expected_effect 的 CI95 相交则窗口成立，不相交则按失效条件作废。

### 3.4 下游使用规则

1. observational 窗口在闭环执行前必须先跑 confirmations
2. confidence=low 的窗口仅可用于人工参考与试验设计，不得直接下发控制
3. [agent 补充] 窗口源自漂移早期轻垢工况（稳态段行 0-401，约 08-01 至 08-09）：结垢缓变漂移持续发展，窗口时效有限；执行前须以当前稳态段均值复核，若热效率段均值较 78.67 继续下行或压降段均值较 1.76 继续上行且与窗口段水平（83.66–87.13 / 0.77–1.05）偏离超过窗口效应量级，按 invalidation_conditions 判定工况失配并重新生成窗口

- 适用域：n=2160，时间跨度 2026-08-01 00:00:00 .. 2026-09-14 23:30:00，工况限定 steady-state segments（稳态段）
- 观测因子范围：heat_transfer_coeff_W_m2K 791–1101 W/m²K；hot_outlet_temp_C 65.8–73.7 °C；cold_inlet_temp_C 12.9–30.3 °C
- 失效条件：任一因子越出 applicability_domain.factor_observed_ranges 的 ±20%；stability_report 变点检测触发新 regime（漂移/换产）；确认试验结果与 expected_effect 的 CI95 不相交
- 备注：doe_conclusion.downstream_usage_card 中 n_watchlist=1 为脚本生成时点的快照计数；Phase 4 agent 补录后 recommendations.json.watchlist 实际为 2 条（新增 HTC_IS_STATE_VARIABLE），以下游合同实际内容为准。

---

## 附：工件索引

| 工件 | 路径 |
|---|---|
| 分析上下文 | `00_input/analysis_context.json` |
| 数据画像 | `01_profile/data_profile.json` |
| 相关报告 | `02_analysis/correlation_report.json` |
| 稳定性报告 | `02_analysis/stability_report.json` |
| 图件清单 | `03_figures/plot_manifest.json`（5 图全部 ink_ok） |
| 主结论 | `conclusions/doe_conclusion.json`（authored_by=agent） |
| 下游合同 | `conclusions/recommendations.json` v1.0（authored_by=agent，6 窗口 / 1 确认 / 2 watchlist） |
| 质量门 | G1–G6 全部 PASS（14/14，exit 0） |

*报告生成：doe-analyst agent（秦工），Phase 3–6，2026-10-01。*
