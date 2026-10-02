# 调优经验库 KB 交接摘要（kb-ready）

> 生成：industrial-tuning-memory experience_build.mjs · 2026-10-01T17:51:04.165Z · RUN_DIR: library
> 交接路径：供 AWS Agent 经 rag-bridge kb_agent 场景化入库（按 regime_key 分库检索）；IDD 不直连任何知识库/外部服务。
> 证据分级为建议强度（advisory）——是否下发、如何下发（dispatch policy）由 AWS 侧决定。
> 隐私：本文档仅含人员别名（eng_NN），不含原始人员 ID。

## 场景：产品 PA · 机台 L1 · 工况 S1（regime_key: `PA|L1|S1`）

### [E0/observation] 调参动作 — temp: 85 → 88 (degC)
- 效应：Δ = 0.0495（metric: yield_pct），CI95 = [-0.3042, 0.4032]，n_eff = 14，方向未确立
- 归因状态：truncated · 混杂：无
- 佐证/反证：3 / 0 · 本地经验 ID：`exp_tuning_action_effect_PA|L1|S1_aff312e4d8d9ab9b`
- 适用注记：死区时间按 0 步缺省处理（若实际死区非零，基线段可能混入动作后影响） 效果窗被 action_log[1]@row67 截断（未观察到完全整定）
- 失效条件：CI95 跨 0——效应方向未确立，仅作观察记录；效果窗被截断，未观察到完全整定，效应量可能被低估；超出该 regime_key 工况范围的应用未经本经验支持，不得直接外推

### [E1/observation] 调参动作 — temp: 88 → 84 (degC)
- 效应：Δ = -0.0779（metric: yield_pct），CI95 = [-0.3250, 0.1693]，n_eff = 15，方向未确立
- 归因状态：estimable · 混杂：无
- 佐证/反证：1 / 0 · 本地经验 ID：`exp_tuning_action_effect_PA|L1|S1_bec898521d097f26`
- 适用注记：死区时间按 0 步缺省处理（若实际死区非零，基线段可能混入动作后影响）
- 失效条件：CI95 跨 0——效应方向未确立，仅作观察记录；超出该 regime_key 工况范围的应用未经本经验支持，不得直接外推

## 汇总
- 条目总数 2（tuning_action_effect 2 / fault_control_recipe 0 / optimization_recipe 0）
- 本文件由脚本确定性投影生成；效应数值全部来自 attribution_report（零 LLM）。
