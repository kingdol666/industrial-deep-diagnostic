# 调优经验库 KB 交接摘要（kb-ready）

> 生成：industrial-tuning-memory experience_build.mjs · 2026-10-01T14:24:28.085Z · RUN_DIR: tune_run
> 交接路径：供 AWS Agent 经 rag-bridge kb_agent 场景化入库（按 regime_key 分库检索）；IDD 不直连任何知识库/外部服务。
> 证据分级为建议强度（advisory）——是否下发、如何下发（dispatch policy）由 AWS 侧决定。
> 隐私：本文档仅含人员别名（eng_NN），不含原始人员 ID。

## 场景：产品 PA · 机台 L1 · 工况 S1（regime_key: `PA|L1|S1`）

### [E2/verified] 故障处置处方 — 故障处置处方：temp: 85 → 88 (degC)（触发源 ALT-20261001-142408-000）
- 效应：Δ = -3.5483（metric: yield_pct），CI95 = [-3.8022, -3.2945]，n_eff = 20，方向已确立
- 归因状态：estimable · 混杂：无
- 佐证/反证：2 / 0 · 本地经验 ID：`exp_fault_control_recipe_PA|L1|S1_9150a86409f94269`
- 适用注记：死区时间按 0 步缺省处理（若实际死区非零，基线段可能混入动作后影响）
- 失效条件：超出该 regime_key 工况范围的应用未经本经验支持，不得直接外推

### [E1/observation] 调参动作 — temp: 85 → 88 (degC)
- 效应：Δ = -3.5483（metric: yield_pct），CI95 = [-3.8022, -3.2945]，n_eff = 20，方向已确立
- 归因状态：estimable · 混杂：无
- 佐证/反证：1 / 0 · 本地经验 ID：`exp_tuning_action_effect_PA|L1|S1_aff312e4d8d9ab9b`
- 适用注记：死区时间按 0 步缺省处理（若实际死区非零，基线段可能混入动作后影响）
- 失效条件：超出该 regime_key 工况范围的应用未经本经验支持，不得直接外推

### [E1/observation] 调参动作 — temp: 88 → 84 (degC)
- 效应：Δ = 3.9920（metric: yield_pct），CI95 = [3.7752, 4.2087]，n_eff = 26，方向已确立
- 归因状态：estimable · 混杂：无
- 佐证/反证：1 / 0 · 本地经验 ID：`exp_tuning_action_effect_PA|L1|S1_bec898521d097f26`
- 适用注记：死区时间按 0 步缺省处理（若实际死区非零，基线段可能混入动作后影响）
- 失效条件：超出该 regime_key 工况范围的应用未经本经验支持，不得直接外推

## 汇总
- 条目总数 3（tuning_action_effect 2 / fault_control_recipe 1 / optimization_recipe 0）
- 本文件由脚本确定性投影生成；效应数值全部来自 attribution_report（零 LLM）。
