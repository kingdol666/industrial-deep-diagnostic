# 数据分析报告 — e2e-designed/run

> 由 industrial-doe-analyzer 生成 · 分析模式 designed · 设计类型 full_factorial ·
> 证据等级 A · 下游合同 recommendations.json v1.0

---

## 一、10 秒结论卡

| 项 | 值 |
|---|---|
| 关键因子（按效应强度） | media_fill（两响应 Pareto rank 1）＞ sep_speed（两响应 rank 2）＞ 助磨剂（两响应 rank 3）＞ batch（区组，rank 5）；moisture 两响应均不显著（fineness q=0.7724167618376946） |
| 推荐操作窗口数 | 2（其中 0 条需先做确认试验；但 OW-001/OW-002 均 extrapolation=true，端点执行前须工艺确认） |
| 预期收益（最优窗口） | OW-001：media_fill ∈ [24.0, 29.0]，每提高 1 个原始单位 specific_energy 约 −0.387455（confidence=high）（来源：conclusions/recommendations.json OW-001） |
| 证据等级 | A（randomization_ok / pure_error_df_gt0 / resolution_ok / balanced 全 true；来源：conclusions/doe_conclusion.json grade_checklist） |
| 最重要的限制 | 细度与能耗的调节方向相反（KF-002 vs KF-004）；两响应驻点均为鞍点且在设计域外，窗口端点属外推（来源：doe_conclusion.json key_findings / watchlist） |

**一句话结论**：在 68 行全因子试验（4 因子、16 水平组合全平衡、含 4 中心点、重复 4，来源：01_profile/data_profile.json design）中，media_fill 与 sep_speed 是细度与比能耗的共同主导因子且作用方向相反：上调 media_fill（窗内 [24.0, 29.0]）降比能耗（−0.387455/原始单位）但细度读数上升，上调 sep_speed 细度下降（−0.016089/原始单位）但能耗上升；当前比能耗 42.119944 高于目标 40（usl 44），建议优先按 OW-001 上调 media_fill、类别因子助磨剂取「高」，并联合校核细度 [36.0, 40.0]（目标 38.0）后执行。

---

## 二、1 分钟证据层

### 2.1 效应/相关排序

**fineness（细度）**（来源：02_analysis/effect_table.json families[fineness].tests；n=68，df_resid=55，R²=0.975219）：

| Pareto rank | 项 | 编码系数 | q(BH) | partial η² | 显著(q<0.05) |
|:--:|---|---:|---:|---:|:--:|
| 1 | media_fill | 1.197273 | 3.0145137089351637e-38 | 0.957213 | 是 |
| 2 | sep_speed | −0.804445 | 1.2072035614813869e-29 | 0.909906 | 是 |
| 3 | 助磨剂 | −0.498911 | 5.453172651774099e-20 | 0.795278 | 是 |
| 4 | media_fill:sep_speed | 0.412414 | 1.2469933484815257e-16 | 0.726362 | 是 |
| 5 | batch（区组） | −0.121634 | 0.0013046948219187582 | 0.196999 | 是 |
| 6 | media_fill^2 | −0.430909 | 0.008675039000127624 | 0.138669 | 是 |
| 12 | moisture | 0.00992 | 0.7724167618376946 | 0.001534 | 否 |

**specific_energy（比能耗）**（来源：02_analysis/effect_table.json families[specific_energy].tests；n=68，df_resid=55，R²=0.971868）：

| Pareto rank | 项 | 编码系数 | q(BH) | partial η² | 显著(q<0.05) |
|:--:|---|---:|---:|---:|:--:|
| 1 | media_fill | −1.549819 | 1.8980082523044825e-38 | 0.957926 | 是 |
| 2 | sep_speed | 0.920088 | 3.6173973518543346e-27 | 0.88919 | 是 |
| 3 | 助磨剂 | 0.589869 | 1.8700681364464242e-18 | 0.767341 | 是 |
| 4 | media_fill^2 | 0.723737 | 0.0008050867754345189 | 0.216199 | 是 |
| 5 | batch（区组） | −0.153026 | 0.0016322542829272902 | 0.190835 | 是 |
| 6 | sep_speed:助磨剂 | 0.091162 | 0.08411156248878567 | 0.073023 | 否 |
| 10 | moisture | −0.029113 | 0.6108072876623798 | 0.00797 | 否 |

多重检验：BH 法，2 个响应族，共 24 项检验，q<0.05 显著 11 项（来源：effect_table.json multiple_testing）。

**类别因子设定点**：助磨剂 → 「高」（编码主效应对 fineness −0.498911、对 specific_energy +0.589869，confidence=high；来源：recommendations.json setpoints）。注意其方向权衡：取「高」有利细度但推高能耗。

**操作窗口**（来源：recommendations.json operating_windows，数值一律以合同为准）：

| id | 因子 | 响应 | 窗口 | 每原始单位预期效应 | confidence | extrapolation |
|---|---|---|---|---|:--:|:--:|
| OW-001 | media_fill | specific_energy | [24.0, 29.0] | delta=−0.387455 | high | true |
| OW-002 | sep_speed | fineness | [912.5, 1000.0] | delta=−0.016089 | high | true |

当前基线点 media_fill=28.0、sep_speed=950.0，两窗口距离均为 0.0（已在窗内）（来源：recommendations.json current_baseline）。

### 2.2 关键图

6 张图全部通过 ink 门禁（来源：03_figures/plot_manifest.json，全部 ink_ok=true）：

| 图 | 类型 | 要点 |
|---|---|---|
| pareto_fineness.png | pareto | fineness 标准化效应排序：media_fill ≫ sep_speed ＞ 助磨剂 ＞ media_fill×sep_speed |
| pareto_specific_energy.png | pareto | specific_energy 效应排序：media_fill ≫ sep_speed ＞ 助磨剂 ＞ media_fill² |
| main_effects_fineness.png | main_effects | 主效应方向图（media_fill 正、sep_speed/助磨剂 负） |
| contour_fineness.png | contour | fineness 预测等高线（media_fill×sep_speed 交互可见） |
| residuals_fineness.png | residual_diagnostics | 残差诊断（1 行残差绝对值>3σ） |
| residuals_specific_energy.png | residual_diagnostics | 残差诊断（0 行>3σ） |

### 2.3 稳定性/能力（观察档适用）

designed 模式不产出稳态段/漂移分析。RUN_DIR 内存留此前 observational 通道的
02_analysis/stability_report.json（generated_at 2026-10-01T05:02:10，早于本次 designed 产物 2026-10-01T05:06:40），
其中过程能力仅作背景参考（该文件 cp/cpk 为 null：无时间列，组内 σ 不可估，仅 Pp/Ppk 口径）：

- fineness：mean=38.196701，std_overall=1.571593，Pp=0.424198，Ppk=0.382478，正态性检验未通过（normal=false）（来源：stability_report.json capability[fineness]）
- specific_energy：mean=42.119944，std_overall=1.892647，Ppk=0.331116（单边规格 Pp=null），正态（normal=true）（来源：stability_report.json capability[specific_energy]）

两均值与 recommendations.json response_specs.current 一致。**调参请以 designed 通道结论为准；同目录 correlation_report.json 及 correlation_heatmap/timeline 两图属旧通道遗留，不作为本报告依据。**

---

## 三、深读审计层

### 3.1 模型与检验细节

（来源：02_analysis/model.json、02_analysis/effect_table.json）

- 模型规范：4 主效应 + 11 交互项（含全部三阶、四阶）+ 3 个二次项（media_fill²、sep_speed²、moisture²）+ 区组 batch；协变量无；pooled_terms=[]（无池化），saturated=false（两响应均非饱和）。
- 编码：deviation 编码，数值因子 (x−mean)/half_range 映射到 [−1, 1]；media_fill 半极差 4.0（中心 28.0），sep_speed 半极差 50.0（中心 950.0）（来源：model.json coding + recommendations.json direction_semantics）。
- 自由度（两响应相同）：df_resid=55，df_pure_error=34（中心点+重复提供纯误差），df_lack_of_fit=21。
- fineness：MSE=0.07456，sigma_pure_error=0.27919，R²=0.975219，adj-R²=0.969812，Q²(LOO)=0.961443（重复行可能泄漏，乐观上界），MDE=0.195324（编码 2 水平主效应 α=0.05、power=0.8）；失拟 F=0.886198、p=0.6073162398842268（不显著，模型充分）；残差 1 行 |·|>3σ；skew=0.566753，excess_kurtosis=1.069445。
- specific_energy：MSE=0.122761，sigma_pure_error=0.302468，R²=0.971868，adj-R²=0.96573，Q²(LOO)=0.957139，MDE=0.21161；**失拟 F=1.895287、p=0.04720208908028563（<0.05 边际显著，模型可能缺高阶结构）**；残差 0 行>3σ；skew=0.187365，excess_kurtosis=−0.681651。
- 驻点（两响应同警示）：fineness 驻点 raw(34.842139, 986.993716, 0.985498) 分类=saddle、inside_design_region=false，特征值 [−1.027985, −0.005503, 0.17167]；specific_energy 驻点 raw(35.058034, 878.278475, −14.667081) 分类=saddle、域外，特征值 [−0.050896, 0.048576, 1.449796]；脚本警告：优化须在盒约束内进行（W3/W5）。
- 响应规格（来源：recommendations.json response_specs）：fineness lsl=36.0 / usl=40.0 / target=38.0 / goal=target / current=38.196701；specific_energy lsl=null / usl=44.0 / target=40.0 / goal=minimize / current=42.119944。

### 3.2 披露与限制（全部保留，不得删除）

脚本 caveats 为空（01_profile/data_profile.json caveats=[]）；以下为 agent 增补的业务上下文限制，全文与 conclusions/doe_conclusion.json limitations 一致：

1. 细度 fineness 为双向目标规格（target=38.0，规格限 [36.0, 40.0]），当前 38.196701 略高于目标：media_fill（正向）与 sep_speed（负向）是一对方向相反的细度调节手段，应围绕目标 38 做小幅对中调整，而非追求单侧极值。
2. 比能耗 specific_energy 目标为最小化（target 40.0、usl 44.0），当前 42.119944 仍高于目标：提 media_fill 降耗（OW-001）与压 sep_speed 保能耗须联合核算，避免细度对中合格而比能耗越过 usl 44.0。
3. specific_energy 的失拟检验 p=0.04720208908028563（<0.05，边际显著）：二阶模型可能未完全刻画高阶结构，按窗口端点执行前建议以确认试验复核。
4. 两个响应的驻点均为鞍点且落在设计域外（model.json stationary_point.warning）：理论最优点不可直接使用，优化须在盒约束内进行；OW-001/OW-002 均 extrapolation=true，其端点按合同 usage_rules 需工艺确认后方可执行。
5. 区组 batch 对两响应均显著但效应量小（fineness q=0.0013046948219187582、η²=0.006079；specific_energy q=0.0016322542829272902、η²=0.006635）：批次间存在系统性小差异，落地窗口设定值时应固定或配平批次来源。
6. 所有因子列的工程单位未登记（factor_unit 为空）：窗口端点为数据原始单位，执行前须由工艺人员确认单位换算口径。
7. Q²(LOO)（fineness 0.961443、specific_energy 0.957139）按 hat-matrix 计算，重复（twin）行可能泄漏，只能视为乐观上界（model.json q_squared_note）。

### 3.3 确认试验计划

recommendations.json confirmations=[]（designed 满秩设计、无混淆链、纯误差 df=34>0，G4 通过，无强制确认项）。但按合同使用规则与上述限制，建议执行前：

- OW-001/OW-002 端点（extrapolation=true）先做小规模工艺确认，再放量执行（usage_rules 第 1 条）；
- specific_energy 失拟边际显著（p=0.04720208908028563），在 OW-001 端点附近补 3–5 序确认批，核验降耗幅度是否偏离 −0.387455/单位（watchlist LACK_OF_FIT_MARGIN）。

### 3.4 下游使用规则

合同 conclusions/recommendations.json（contract_version 1.0，audience downstream_agent）内嵌规则：

- usage_rules：「窗口外推端点（extrapolation=true）需工艺确认后方可执行」「多响应窗口冲突以 conflicts[].chosen 为准」（本次 conflicts=[]）。
- 适用域：n=68，时间跨度 null（数据未带时间戳），工况限定 designed region；factor_observed_ranges：media_fill [24.0, 32.0]、sep_speed [900.0, 1000.0]（moisture 与 助磨剂 未列入观测域登记）。
- 失效条件：任一因子越出 applicability_domain.factor_observed_ranges 的 ±20%；stability_report 变点检测触发新 regime（漂移/换产）；确认试验结果与 expected_effect 的 CI95 不相交。
- watchlist 共 5 条：脚本 2 条 STATIONARY_POINT_WARNING（fineness / specific_energy）+ agent 增补 3 条（LACK_OF_FIT_MARGIN / BLOCK_EFFECT / RESPONSE_TRADEOFF）。

---

## 附：工件索引

| 工件 | 说明 |
|---|---|
| run_manifest.json | 运行清单（Phase 0 生成） |
| 00_input/analysis_context.json | 分析上下文（响应规格、因子/区组指派） |
| 00_input/grinding_doe.csv | 原始数据（68 行 × 7 列） |
| 01_profile/data_profile.json | 设计检测：full_factorial、balanced=1.0、4 中心点、caveats=[] |
| 02_analysis/effect_table.json | 效应 + Type-II ANOVA + BH-FDR + Pareto + MDE |
| 02_analysis/model.json | 编码系数 + R²/adj-R²/Q² + 失拟 + 驻点分类 |
| 02_analysis/correlation_report.json | （旧 observational 通道遗留，非本报告依据） |
| 02_analysis/stability_report.json | （旧 observational 通道遗留；能力数字仅作 2.3 节背景参考） |
| 03_figures/plot_manifest.json | 6 张图 ink 门禁全过 |
| conclusions/doe_conclusion.json | 主结论（evidence_grade=A，authored_by=agent） |
| conclusions/recommendations.json | 下游合同 v1.0（2 窗口、0 强制确认、watchlist 5 条，authored_by=agent） |
| report.md | 本报告 |

质量门禁：quality_gate.mjs 15/15 PASS（G1–G6 全过）。
