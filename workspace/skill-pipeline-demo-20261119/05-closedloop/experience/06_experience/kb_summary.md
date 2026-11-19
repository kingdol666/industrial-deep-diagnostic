# 调优经验库 KB 交接摘要（kb-ready）

> 生成：industrial-tuning-memory experience_build.mjs · 2026-11-18T19:45:22.259Z · RUN_DIR: experience
> 交接路径：供 AWS Agent 经 rag-bridge kb_agent 场景化入库（按 regime_key 分库检索）；IDD 不直连任何知识库/外部服务。
> 证据分级为建议强度（advisory）——是否下发、如何下发（dispatch policy）由 AWS 侧决定。
> 隐私：本文档仅含人员别名（eng_NN），不含原始人员 ID。

## 场景：产品 PP-Cup-330ml · 机台 IMM-07 · 工况 high_output（regime_key: `PP-Cup-330ml|IMM-07|high_output`）

### [E0/observation] 调参动作 — back_pressure_bar: 13.5 → 10.5 (bar)
- 效应：Δ = -0.0021（metric: energy_kwh_per_kg），CI95 = [-0.0120, 0.0079]，n_eff = 22，方向未确立
- 归因状态：direction_uncertain · 混杂：无
- 佐证/反证：1 / 0 · 本地经验 ID：`exp_tuning_action_effect_PP-Cup-3_4f79992e0c678566`
- 适用注记：死区时间按 0 步缺省处理（若实际死区非零，基线段可能混入动作后影响）
- 失效条件：CI95 跨 0——效应方向未确立，仅作观察记录；超出该 regime_key 工况范围的应用未经本经验支持，不得直接外推

### [E1/observation] 调参动作 — back_pressure_bar: 12 → 13.5 (bar)
- 效应：Δ = 0.0069（metric: energy_kwh_per_kg），CI95 = [-0.0005, 0.0143]，n_eff = 49，方向未确立
- 归因状态：estimable · 混杂：无
- 佐证/反证：3 / 0 · 本地经验 ID：`exp_tuning_action_effect_PP-Cup-3_5aa2c025a9f17bc1`
- 适用注记：死区时间按 0 步缺省处理（若实际死区非零，基线段可能混入动作后影响）
- 失效条件：CI95 跨 0——效应方向未确立，仅作观察记录；超出该 regime_key 工况范围的应用未经本经验支持，不得直接外推

### [E1/observation] 调参动作 — barrel_temp_c: 180 → 190 (degC)
- 效应：Δ = 0.1739（metric: energy_kwh_per_kg），CI95 = [0.1655, 0.1823]，n_eff = 30，方向已确立
- 归因状态：estimable · 混杂：无
- 佐证/反证：1 / 0 · 本地经验 ID：`exp_tuning_action_effect_PP-Cup-3_941cbf7a6bc8def0`
- 适用注记：死区时间按 0 步缺省处理（若实际死区非零，基线段可能混入动作后影响）
- 失效条件：超出该 regime_key 工况范围的应用未经本经验支持，不得直接外推

### [E1/observation] 调参动作 — barrel_temp_c: 185 → 180 (degC)
- 效应：Δ = -0.0922（metric: energy_kwh_per_kg），CI95 = [-0.1040, -0.0804]，n_eff = 18，方向已确立
- 归因状态：estimable · 混杂：无
- 佐证/反证：1 / 0 · 本地经验 ID：`exp_tuning_action_effect_PP-Cup-3_9b4523b6f1b251ec`
- 适用注记：死区时间按 0 步缺省处理（若实际死区非零，基线段可能混入动作后影响）
- 失效条件：超出该 regime_key 工况范围的应用未经本经验支持，不得直接外推

### [E3/verified] 调参动作 — barrel_temp_c: 190 → 185 (degC)
- 效应：Δ = -0.0903（metric: energy_kwh_per_kg），CI95 = [-0.0973, -0.0833]，n_eff = 45，方向已确立
- 归因状态：estimable · 混杂：无
- 佐证/反证：2 / 0 · 本地经验 ID：`exp_tuning_action_effect_PP-Cup-3_b4ef215abaf60964`
- 适用注记：死区时间按 0 步缺省处理（若实际死区非零，基线段可能混入动作后影响）
- 失效条件：超出该 regime_key 工况范围的应用未经本经验支持，不得直接外推

## 场景：产品 PP-Cup-330ml · 机台 IMM-07 · 工况 normal（regime_key: `PP-Cup-330ml|IMM-07|normal`）

### [E2/verified] 调参动作 — barrel_temp_c: 195 → 190 (degC)
- 效应：Δ = -0.0895（metric: energy_kwh_per_kg），CI95 = [-0.0974, -0.0817]，n_eff = 25，方向已确立
- 归因状态：estimable · 混杂：无
- 佐证/反证：3 / 0 · 本地经验 ID：`exp_tuning_action_effect_PP-Cup-3_33cb431d2d5b8b58`
- 适用注记：死区时间按 0 步缺省处理（若实际死区非零，基线段可能混入动作后影响）
- 失效条件：超出该 regime_key 工况范围的应用未经本经验支持，不得直接外推

### [E2/verified] 调参动作 — cooling_time_s: 26 → 24 (s)
- 效应：Δ = -0.0270（metric: energy_kwh_per_kg），CI95 = [-0.0347, -0.0193]，n_eff = 31，方向已确立
- 归因状态：estimable · 混杂：无
- 佐证/反证：2 / 0 · 本地经验 ID：`exp_tuning_action_effect_PP-Cup-3_5295e1acfc85c4ab`
- 适用注记：死区时间按 0 步缺省处理（若实际死区非零，基线段可能混入动作后影响）
- 失效条件：超出该 regime_key 工况范围的应用未经本经验支持，不得直接外推

### [E2/verified] 调参动作 — cooling_time_s: 28 → 26 (s)
- 效应：Δ = -0.0242（metric: energy_kwh_per_kg），CI95 = [-0.0311, -0.0174]，n_eff = 46，方向已确立
- 归因状态：estimable · 混杂：无
- 佐证/反证：3 / 0 · 本地经验 ID：`exp_tuning_action_effect_PP-Cup-3_54d356cda929e27e`
- 适用注记：死区时间按 0 步缺省处理（若实际死区非零，基线段可能混入动作后影响）
- 失效条件：超出该 regime_key 工况范围的应用未经本经验支持，不得直接外推

### [E1/observation] 调参动作 — cooling_time_s: 24 → 30 (s)
- 效应：Δ = 0.0588（metric: energy_kwh_per_kg），CI95 = [0.0511, 0.0665]，n_eff = 28，方向已确立
- 归因状态：estimable · 混杂：无
- 佐证/反证：1 / 0 · 本地经验 ID：`exp_tuning_action_effect_PP-Cup-3_589900675f77b1f0`
- 适用注记：死区时间按 0 步缺省处理（若实际死区非零，基线段可能混入动作后影响）
- 失效条件：超出该 regime_key 工况范围的应用未经本经验支持，不得直接外推

### [E1/observation] 调参动作 — back_pressure_bar: 12 → 14 (bar)
- 效应：Δ = 0.0000（metric: energy_kwh_per_kg），CI95 = [-0.0057, 0.0057]，n_eff = 37，方向未确立
- 归因状态：estimable · 混杂：无
- 佐证/反证：1 / 0 · 本地经验 ID：`exp_tuning_action_effect_PP-Cup-3_59ef31e242d0ac31`
- 适用注记：死区时间按 0 步缺省处理（若实际死区非零，基线段可能混入动作后影响）
- 失效条件：CI95 跨 0——效应方向未确立，仅作观察记录；超出该 regime_key 工况范围的应用未经本经验支持，不得直接外推

### [E3/verified] 调参动作 — barrel_temp_c: 190 → 185 (degC)
- 效应：Δ = -0.0904（metric: energy_kwh_per_kg），CI95 = [-0.0986, -0.0822]，n_eff = 38，方向已确立
- 归因状态：estimable · 混杂：无
- 佐证/反证：2 / 0 · 本地经验 ID：`exp_tuning_action_effect_PP-Cup-3_79cd9594557b3acb`
- 适用注记：死区时间按 0 步缺省处理（若实际死区非零，基线段可能混入动作后影响）
- 失效条件：超出该 regime_key 工况范围的应用未经本经验支持，不得直接外推

### [E1/observation] 调参动作 — barrel_temp_c: 185 → 199 (degC)
- 效应：Δ = 0.2545（metric: energy_kwh_per_kg），CI95 = [0.2468, 0.2621]，n_eff = 43，方向已确立
- 归因状态：estimable · 混杂：无
- 佐证/反证：1 / 0 · 本地经验 ID：`exp_tuning_action_effect_PP-Cup-3_7d193ae114b758e3`
- 适用注记：死区时间按 0 步缺省处理（若实际死区非零，基线段可能混入动作后影响）
- 失效条件：超出该 regime_key 工况范围的应用未经本经验支持，不得直接外推

### [E0/observation] 调参动作 — back_pressure_bar: 12 → 13.5 (bar)
- 效应：Δ = 0.0000（metric: energy_kwh_per_kg），CI95 = [-0.0059, 0.0059]，n_eff = 41，方向未确立
- 归因状态：direction_uncertain · 混杂：无
- 佐证/反证：1 / 0 · 本地经验 ID：`exp_tuning_action_effect_PP-Cup-3_9135d3fbd0d10e5a`
- 适用注记：死区时间按 0 步缺省处理（若实际死区非零，基线段可能混入动作后影响）
- 失效条件：CI95 跨 0——效应方向未确立，仅作观察记录；超出该 regime_key 工况范围的应用未经本经验支持，不得直接外推

### [E1/observation] 调参动作 — cooling_time_s: 24 → 28 (s)
- 效应：Δ = 0.0374（metric: energy_kwh_per_kg），CI95 = [0.0280, 0.0468]，n_eff = 25，方向已确立
- 归因状态：estimable · 混杂：无
- 佐证/反证：1 / 0 · 本地经验 ID：`exp_tuning_action_effect_PP-Cup-3_9a881ed6729a8c8e`
- 适用注记：死区时间按 0 步缺省处理（若实际死区非零，基线段可能混入动作后影响）
- 失效条件：超出该 regime_key 工况范围的应用未经本经验支持，不得直接外推

### [E2/verified] 调参动作 — barrel_temp_c: 200 → 195 (degC)
- 效应：Δ = -0.0871（metric: energy_kwh_per_kg），CI95 = [-0.0965, -0.0777]，n_eff = 18，方向已确立
- 归因状态：estimable · 混杂：无
- 佐证/反证：3 / 0 · 本地经验 ID：`exp_tuning_action_effect_PP-Cup-3_a59fd6e77409398f`
- 适用注记：死区时间按 0 步缺省处理（若实际死区非零，基线段可能混入动作后影响）
- 失效条件：超出该 regime_key 工况范围的应用未经本经验支持，不得直接外推

### [E1/observation] 调参动作 — injection_pressure_bar: 118 → 115 (bar)
- 效应：Δ = -0.0022（metric: energy_kwh_per_kg），CI95 = [-0.0089, 0.0045]，n_eff = 21，方向未确立
- 归因状态：estimable · 混杂：无
- 佐证/反证：2 / 0 · 本地经验 ID：`exp_tuning_action_effect_PP-Cup-3_d1bf3ab8918869f5`
- 适用注记：死区时间按 0 步缺省处理（若实际死区非零，基线段可能混入动作后影响）
- 失效条件：CI95 跨 0——效应方向未确立，仅作观察记录；超出该 regime_key 工况范围的应用未经本经验支持，不得直接外推

### [E0/observation] 调参动作 — back_pressure_bar: 13.5 → 12 (bar)
- 效应：Δ = 0.0033（metric: energy_kwh_per_kg），CI95 = [-0.0058, 0.0124]，n_eff = 34，方向未确立
- 归因状态：direction_uncertain · 混杂：无
- 佐证/反证：3 / 0 · 本地经验 ID：`exp_tuning_action_effect_PP-Cup-3_daa729956ec798b0`
- 适用注记：死区时间按 0 步缺省处理（若实际死区非零，基线段可能混入动作后影响）
- 失效条件：CI95 跨 0——效应方向未确立，仅作观察记录；超出该 regime_key 工况范围的应用未经本经验支持，不得直接外推

### [E1/observation] 调参动作 — barrel_temp_c: 185 → 200 (degC)
- 效应：Δ = 0.2702（metric: energy_kwh_per_kg），CI95 = [0.2628, 0.2775]，n_eff = 33，方向已确立
- 归因状态：estimable · 混杂：无
- 佐证/反证：1 / 0 · 本地经验 ID：`exp_tuning_action_effect_PP-Cup-3_e0381778f1bf04bc`
- 适用注记：死区时间按 0 步缺省处理（若实际死区非零，基线段可能混入动作后影响）
- 失效条件：超出该 regime_key 工况范围的应用未经本经验支持，不得直接外推

### [E0/observation] 调参动作 — injection_pressure_bar: 115 → 118 (bar)
- 效应：Δ = 0.0009（metric: energy_kwh_per_kg），CI95 = [-0.0094, 0.0112]，n_eff = 19，方向未确立
- 归因状态：direction_uncertain · 混杂：无
- 佐证/反证：3 / 0 · 本地经验 ID：`exp_tuning_action_effect_PP-Cup-3_f9540c278e3b26cf`
- 适用注记：死区时间按 0 步缺省处理（若实际死区非零，基线段可能混入动作后影响）
- 失效条件：CI95 跨 0——效应方向未确立，仅作观察记录；超出该 regime_key 工况范围的应用未经本经验支持，不得直接外推

## 汇总
- 条目总数 19（tuning_action_effect 19 / fault_control_recipe 0 / optimization_recipe 0）
- 本文件由脚本确定性投影生成；效应数值全部来自 attribution_report（零 LLM）。
