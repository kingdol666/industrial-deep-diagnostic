# 调优经验库 KB 交接摘要（kb-ready）

> 生成：industrial-tuning-memory experience_build.mjs · 2026-10-04T06:39:01.784Z · RUN_DIR: run
> 交接路径：供 AWS Agent 经 rag-bridge kb_agent 场景化入库（按 regime_key 分库检索）；IDD 不直连任何知识库/外部服务。
> 证据分级为建议强度（advisory）——是否下发、如何下发（dispatch policy）由 AWS 侧决定。
> 隐私：本文档仅含人员别名（eng_NN），不含原始人员 ID。

## 场景：产品 PVC-M · 机台 calender-03 · 工况 night_shift（regime_key: `PVC-M|calender-03|night_shift`）

### [E2/verified] 故障处置处方 — 故障处置处方：temp_c: 85.0 → 77.0 (degC); speed_rpm: 1250.0 → 1238.0 (rpm)（触发源 ALT-20251102-0144-006）
- 效应：Δ = 1.5800（metric: yield_pct），CI95 = [1.0200, 2.1400]，n_eff = 19，方向已确立
- 归因状态：estimable · 混杂：无
- 佐证/反证：2 / 0 · 本地经验 ID：`exp_fault_control_recipe_PVC-M|ca_2adda6ae0dd13c21`
- 经验教训：历史处置：熔温/线速双高导致收率下降，按配方降设定后恢复。
- 失效条件：超出该 regime_key 工况范围的应用未经本经验支持，不得直接外推

### [E1/observation] 调参动作 — temp_c: 85 → 77 (degC)
- 效应：Δ = 1.9929（metric: yield_pct），CI95 = [1.4306, 2.5551]，n_eff = 15，方向已确立
- 归因状态：estimable · 混杂：无
- 佐证/反证：1 / 0 · 本地经验 ID：`exp_tuning_action_effect_PVC-M|ca_6d7959d486594335`
- 适用注记：死区时间按 0 步缺省处理（若实际死区非零，基线段可能混入动作后影响）
- 失效条件：超出该 regime_key 工况范围的应用未经本经验支持，不得直接外推

### [E1/observation] 调参动作 — pressure_mpa: 2.4 → 2.6 (bar)
- 效应：Δ = 0.1545（metric: yield_pct），CI95 = [-0.2193, 0.5282]，n_eff = 24，方向未确立
- 归因状态：estimable · 混杂：无
- 佐证/反证：1 / 0 · 本地经验 ID：`exp_tuning_action_effect_PVC-M|ca_ede263eec22a6f4f`
- 适用注记：死区时间按 0 步缺省处理（若实际死区非零，基线段可能混入动作后影响）
- 失效条件：CI95 跨 0——效应方向未确立，仅作观察记录；超出该 regime_key 工况范围的应用未经本经验支持，不得直接外推

## 场景：产品 PVC-R · 机台 calender-05 · 工况 day_shift（regime_key: `PVC-R|calender-05|day_shift`）

### [E1/observation] 故障处置处方 — 故障处置处方：viscosity_cp: 2180.0 → 2105.0 (cP)（触发源 ALT-20250918-0312-002）
- 效应：Δ = -0.9000（metric: gloss_gu），CI95 = [-1.6000, -0.2000]，n_eff = 22，方向已确立
- 归因状态：estimable · 混杂：无
- 佐证/反证：1 / 0 · 本地经验 ID：`exp_fault_control_recipe_PVC-R|ca_ac2f32426b0290ea`
- 经验教训：历史处置：熔温/线速双高导致收率下降，按配方降设定后恢复。
- 失效条件：超出该 regime_key 工况范围的应用未经本经验支持，不得直接外推

## 汇总
- 条目总数 4（tuning_action_effect 2 / fault_control_recipe 2 / optimization_recipe 0）
- 本文件由脚本确定性投影生成；效应数值全部来自 attribution_report（零 LLM）。
