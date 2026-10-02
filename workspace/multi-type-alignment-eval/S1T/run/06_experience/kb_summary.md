# 调优经验库 KB 交接摘要（kb-ready）

> 生成：industrial-tuning-memory experience_build.mjs · 2026-10-01T13:08:05.997Z · RUN_DIR: run
> 交接路径：供 AWS Agent 经 rag-bridge kb_agent 场景化入库（按 regime_key 分库检索）；IDD 不直连任何知识库/外部服务。
> 证据分级为建议强度（advisory）——是否下发、如何下发（dispatch policy）由 AWS 侧决定。
> 隐私：本文档仅含人员别名（eng_NN），不含原始人员 ID。

## 场景：产品 P1 · 机台 M1 · 工况 R1（regime_key: `P1|M1|R1`）

### [E1/observation] 调参动作 — x1: 50 → 51 (unit)
- 效应：Δ = 0.2046（metric: y），CI95 = [-0.2024, 0.6116]，n_eff = 13，方向未确立
- 归因状态：estimable · 混杂：无
- 佐证/反证：1 / 0 · 本地经验 ID：`exp_tuning_action_effect_P1|M1|R1_74c0976334906008`
- 适用注记：死区时间 4 步
- 失效条件：CI95 跨 0——效应方向未确立，仅作观察记录；超出该 regime_key 工况范围的应用未经本经验支持，不得直接外推

## 汇总
- 条目总数 1（tuning_action_effect 1 / fault_control_recipe 0 / optimization_recipe 0）
- 本文件由脚本确定性投影生成；效应数值全部来自 attribution_report（零 LLM）。
