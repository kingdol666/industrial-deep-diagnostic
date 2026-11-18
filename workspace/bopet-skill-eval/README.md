# BOPET 全流程技能评测夹具（workspace/bopet-skill-eval）

一套面向 BOPET 双向拉伸薄膜产线的 6 个示例题，分别驱动 6 个工业分析 skill。
数据全部为**确定性合成**（固定种子、小数据量 20–240 行、utf-8、中文表头），
物理真值写在各夹具 `ground_truth.md`（出题人参考，评测时勿投喂给分析 agent）。
共享本体 [`bopet_line_ontology.json`](bopet_line_ontology.json)：14 信号 × 6 参数组、
11 条 causal 机制边、4 个混杂因子，工艺窗口取自乐凯 FW3 快照典型值。

| # | 文件夹 | 题目 | 目标 skill | 实测结果（2026-10-14 全部实跑） | 判据 |
|---|---|---|---|---|---|
| S1 | `S1_stability_winding/` | 收卷工段一周稳定性体检 | industrial-line-stability-report | 83.9 分/B 级；`condition.ontology.mode=ontology`；张力↔厚度相关性机制=**known**（F009，置信度 70，附控制方程 ε=F/(E·A)）；用户规格限下 Cpk=1.24 触发"工序能力不足"；gate 11 项 PASS | ✅ 全过 |
| S2 | `S2_doe_mdo_ccd/` | 纵拉工艺 CCD 试验分析 | industrial-doe-analyzer (designed) | 自动识别 `rsm_ccd`；RSM 推荐配方 (78.40℃, 52.68, 3.212) 期望函数 **D=0.996**，贴真值驻点 (78.2, 53.0, 3.26)；2 操作窗带 FDR q 值；watchlist 如实报"可行域不连通/鞍点"；report.html 28 图 | ✅ 全过 |
| S3 | `S3_sentinel_tdo_watch/` | TDO 工段哨兵基线+5 天批筛 | industrial-sentinel | build_baseline exit 0（240 稳态行）；watch 25 条告警：CX6 爬升被 robust z=4.2 + Nelson R1/R2/R5/R6 交叉命中（末端 197.8℃ vs 真值 198.1），熔体压力尖峰命中 R1@row54；无 doe 先验 → C2 漂移投影**降级如实写入 checks_skipped**；中文 watch_report.md | ✅ 过（C2 缺先验降级=预期行为） |
| S4 | `S4_tuning_traction/` | 两次调参的动作效果归因 | industrial-tuning-memory | 动作1（提产）：**estimable/E1，Δ=−0.117μm，CI95[−0.143,−0.092]**（真值 −0.12）；动作2（CX4+2℃）：真值 +0.035 小于噪声底且基线被动作1污染 → 脚本**拒绝给方向结论**（direction_uncertain/E0）——防编造设计生效 | ✅ 过（A2 拒判=预期诚实行为） |
| S5 | `S5_optimizer_recipe/` | TDO 配方闭环寻优 | industrial-optimizer-loop | init 过 O-G1；LHS 布点→GP-EI→确认轮（3 重复）→ **converged**（12/15 设计点，4 轮）；最终配方 (CX4=243.2, v=53.1, CX6=190.9) 实测优品率 **98.92%**（真值面 98.94，全局峰 99.2，tolerance 0.3 内）；recipe.json 带 guardrails 包络，verification=verified；全程零参数下发 | ✅ 全过 |
| S6 | `S6_diagnosis_thickness/` | 厚度超差根因诊断（9 阶段） | industrial-analysis-auto | setup.mjs 脚手架 OK（18 项交付契约）；inspect 通过：240 行×15 列、时间列=时间、14 数值列零缺失；本体与 user_context 就位。**完整诊断需多 agent 编排**，按 analysis-auto SKILL.md Step 0-9 执行（重量级，未在本轮实跑） | ✅ 摄入验证过；全管线待跑 |

## 两个可复用的踩坑经验（已写进对应题目）

1. **S4 时区**：action_log 的 `ts` 带时区语义，数据列是本地朴素时间——`Z` 会被平移 8 行（UTC+8），
   务必写 `+08:00` 或让两边口径一致。
2. **S5 预算语义**：`trials_per_round` 只影响首批；GP 阶段每轮 1 点顺序推进；
   确认轮要求重复数 ≥3（`CONFIRM_MIN_REPLICATES`），`noise.replicates_for_sigma` 至少给 3。

## 复跑方式

```bash
cd workspace/bopet-skill-eval
uv run --project ../../.claude/shared/scripts python make_fixtures.py   # 重建全部 CSV
# 各题目命令见各夹具 题目.md
```

## 边界提醒

- 全部脚本要求输入位于**仓库根目录内**（路径白名单），且共享 `.claude/shared` 与兄弟 skill 脚本；
- 除 analysis-auto 预处理器与本评测外，doe/sentinel/tuning 只认 utf-8（GBK 需先转码）；
- 本套夹具数据为合成演示，工艺窗口参考乐凯 FW3 典型值，结论不构成任何真实产线的工艺依据。
