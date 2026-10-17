# DOE 分析流程优化 · 验收 Traceability Matrix

- 日期：2026-10-17（Phase 0 填写）
- 对应计划：`doe-analysis-flow-optimization-plan-2026-10-17.md`
- 契约：`contracts/README.md`（字段/路径/枚举的单一权威源）
- 状态图例：`未验证` → `进行中` → **PASS** / **FAIL** / `延期（附理由）`

> 规则：每条验收 ID 必须有 test case + fixture + 命令 + 证据文件。没有映射 = 未验证。
> 证据落 `workspace/acceptance/doe-2026-10-17/`（命令输出摘要、JSON、hash）。
> 命令简写：
> ```
> $A = uv run --project .claude/shared/scripts python
> $T = $A .claude/skills/industrial-doe-analyzer/tests/run_tests.py
> $G = node .claude/skills/industrial-doe-analyzer/scripts/quality_gate.mjs <RUN_DIR> \
>        --skill-path .claude/skills/industrial-doe-analyzer --shared-path .claude/shared
> ```

## 1. 本体（OD）

| 验收 ID | 条件 | 测试 case | Fixture | 命令 | 证据 | 状态 |
|---|---|---|---|---|---|---|
| OD-01 | DOE 使用 ontology-builder（profile=doe）；非另起引擎 | `F13.ontology_profile_doe`、`F13.not_separate_engine` | `design_only` | `$T F13` | `01_ontology/ontology.json` + brief；provenance.engine==`industrial-ontology-builder` | 未验证 |
| OD-02 | 先查 store；exact reuse ≤60s，无 RAG/web | `ont-store.exact_reuse_fast`、`ont-store.reuse_no_rag` | `ontology_reuse` | `$T ont-store` | store index 条目 `profile`/`context_fp`；pipeline event 无 rag/web | 未验证 |
| OD-03 | design-only 先验构建；响应空可建；`observed_data_behavior=NOT_APPLICABLE`；不跑统计 | `F13.design_only_builds`、`F13.obs_behavior_na`、`F13.stats_blocked` | `design_only` | `$T F13` | ontology.json；`DESIGN_ONLY_NO_RESPONSE` 阻断记录 | 未验证 |
| OD-04 | Agent 理解门：无 brief / 无 `analysis_plan.md` → 阻断 | `ont-gate.missing_brief_blocks`、`ont-gate.missing_plan_blocks` | `design_only` | `$T ont-gate` | `ONTOLOGY_BRIEF_REQUIRED` / `ANALYSIS_PLAN_REQUIRED` 退出码 | 未验证 |
| OD-05 | 本体后再分析：brief 存在才统计；顺序可证 | `ont-gate.order_proven`、`F1.analyze_exit0`（mode!=off 回归） | `design_only`、`F1` | `$T ont-gate`、`$T F1` | 事件时间序 brief→plan→effect_table | 未验证 |
| OD-06 | 一致性：仅 causal/physical + 可归一化 sign；checked/matched/not_estimable/contradictions | `F22.consistency_keys`、`F22.contradiction_advisory` | `ontology_contradiction` | `$T F22` | `01_ontology/ontology_feedback.json` | 未验证 |
| OD-07 | 版本钉住：experiment 记录 ontology version/hash；context 变化 → extend/新版本 | `ont-store.version_pinned`、`ont-store.context_change_extends` | `ontology_reuse` | `$T ont-store` | brief 的 `ontology_version`/`ontology_sha256`；store 新版本条目 | 未验证 |
| OD-08 | 诊断回归：默认 diagnosis profile 的 ontology 行为/CP-2/输出不变 | `ont-store.diagnosis_profile_unchanged`（单测）＋ 诊断 E2E | 既有 store | `$T ont-store`；诊断 E2E 路径 | store index 中 diagnosis 条目结构未变 | 未验证 |
| OD-09 | 映射覆盖：factor/response 100% matched 或 inferred+reason；0 静默 | `F13.coverage_complete`、`F13.coverage_reasons` | `design_only` | `$T F13` | `ontology_coverage.json` / brief `column_mapping` | 未验证 |
| OD-10 | 报告引用：引用 id 存在；允许 `no_ontology_basis+reason`；无编造 | `F22.report_refs_exist`、`F22.no_ontology_basis_allowed` | `ontology_contradiction` | `$T F22` | report.html 引用 id ⊆ ontology/effect ids | 未验证 |
| OD-11 | handoff：每个 joint_setpoint/next_design 因子有 platform_ref；可生成 recipe_patch/node_setpoints | `artifacts.guidance_platform_ref`、`F19.patch_within_limits` | `ccd_constraints` | `$T artifacts`、`$T F19` | `conclusions/optimization_guidance.json` | 未验证 |

## 2. 统计（DS）

| 验收 ID | 条件 | 测试 case | Fixture | 命令 | 证据 | 状态 |
|---|---|---|---|---|---|---|
| DS-01 | 设计识别 full/fractional/CCD/BBD/OA/LHS 6/6 | `F20.detect_6of6`（design_build 生成→detect 回读） | `design_build` 六型 | `$T F20` | `data_profile.design.design_type` 6/6 命中 | 未验证 |
| DS-02 | 效应恢复：1000 次 MC；≥2×MDE 符号 ≥99%、power ≥80%；FWER ≤10% | `mc-effect-recovery.*`（独立脚本；结果文件被 case 断言） | 合成 2^4 设计 | `$A .claude/skills/industrial-doe-analyzer/tests/mc_effect_recovery.py` | `tests/results/mc_effect_recovery.json` | 未验证 |
| DS-03 | factor×response 覆盖：每格 window 或 `not_estimable+reason`；0 静默 | `F15.matrix_complete`、`gate-v11.G11_coverage` | `bbd_multi_response` | `$T F15`、`$T gate-v11` | `recommendations.factor_response_matrix` | 未验证 |
| DS-04 | 多响应：每格 window/no_window_reason；joint setpoint；不按跨单位 delta 选赢家 | `F15.joint_feasible`、`F15.no_cross_unit_winner` | `bbd_multi_response` | `$T F15` | `joint_setpoints[]`、`interval_disclosure.joint_coverage` | 未验证 |
| DS-05 | 约束：绑定约束测试；hard 0 违例（1e-9）；不可行→no window；全阶段执行 | `F14.binding_constraint_active`、`F14.hard_zero_violations`、`F14.infeasible_no_window` | `constraints_binding` | `$T F14` | `constraints_applied`、`constraint_violations`、`no_window_reason=CONSTRAINTS_INFEASIBLE` | 未验证 |
| DS-06 | 单位：unit 或 missing+reason；mm/µm、°C/K 冲突负例；阻断 actionable | `F16.unit_missing_blocks`、`F16.unit_conflict_blocks` | `units_missing` | `$T F16` | `actionable=false` + `actionable_blockers`；`units.conflicts` | 未验证 |
| DS-07 | 预测区间：n≥2000；点覆盖 93.5–96.5%；PI 宽>均值 CI；多响应联合覆盖披露 | `mc-pi-coverage.*`、`gate-v11.G9_pi_gt_ci` | 合成 2^3 | `$A .../tests/mc_pi_coverage.py`、`$T gate-v11` | `tests/results/mc_pi_coverage.json`（含 n 与覆盖率） | 未验证 |
| DS-08 | 联合窗口：逐因子窗口只作诊断；joint_setpoint 多响应可行 | `F15.role_marginal_diagnostic`、`F14.joint_multi_response` | `bbd_multi_response`、`constraints_binding` | `$T F15`、`$T F14` | `window_role=="marginal_diagnostic"`；joint 全响应满足 | 未验证 |
| DS-09 | active/grid：top_k + 连续优化/profile；8/10/20 active 有界；性能分档 | `F21.bounded_grid_8`、`F21.continuous_20`、`F21.no_silent_drop` | `active_scale` | `$T F21` | `grid_plan` 字段；`deferred_factors` 披露 | 未验证 |
| DS-10 | association screen：设计调整/边际/held_constant/unmodeled；`causal_claim:none`；G8 | `F18.kinds_present`、`F18.causal_claim_none`、`gate-v11.G8_assoc_not_in_windows` | `association_confounder` | `$T F18`、`$T gate-v11` | `02_analysis/association_screen.json` | 未验证 |
| DS-11 | 确认/下一轮：fold-over/augment/space-filling/confirm 可执行；setpoints 在约束内 | `F19.foldover_rule`、`F19.augment_rule`、`F19.confirm_rule`、`F19.setpoints_in_constraints` | `next_design` 三型 | `$T F19` | `conclusions/next_design.json` | 未验证 |
| DS-12 | 初始设计：design_build 或明确 import-only；分辨率/别名/随机化/power | `F20.build_full`、`F20.build_fractional_res4`、`F20.build_ccd`、`F20.properties_complete` | `design_build` | `$T F20` | design_build 输出 properties | 未验证 |
| DS-13 | 向后兼容：136 断言逐条不变；v1.1 加法；contract_status 独立 | `T-REG-01`（全套）＋ `F1..F12` 逐条 | 既有 F1–F12 | `$T all` | 136/136 绿 | 未验证 |

## 3. 工件 / 回归（AR / RG）

| 验收 ID | 条件 | 测试 case | Fixture | 命令 | 证据 | 状态 |
|---|---|---|---|---|---|---|
| AR-01 | artifact manifest：tasks+external 同源；12 类工件；path/url/sha256/schema_version | `artifacts.manifest_12_kinds`、`artifacts.sha256_matches`、`artifacts.missing_explicit` | `ccd_constraints` | `$T artifacts`；`$G` | manifest JSON（tasks 与 external 同源比对） | 未验证 |
| AR-02 | report：report.md/html 含 brief/effect/window/joint/next design；hash 可溯 | `report-WV.sections_present`、`report-WV.meta_sha256` | `ccd_constraints` | `$T report-WV` | report.html `sec-*` 区块 + `report-meta` sha256 | 未验证 |
| AR-03 | gate：G1–G11 全绿；tamper 负例 FAIL；无 NaN/Inf | `gate-v11.*`、`tamper.*` | `tamper_g1`、`tamper_g34` | `$T gate-v11`、`$T tamper` | gate 输出 `[GATE] n/m checks passed` | 未验证 |
| RG-01 | 既有测试 18 组/136 断言仍绿 | 全套 | F1–F12 | `$T all` | `[TESTS] 136/136 passed` | **PASS**（Phase 0 基线） |
| RG-02 | 新增测试 F13–F22 + fixtures 全绿 | 全套 | 新增 fixtures | `$T all` | 新增断言计数 | 未验证 |
| RG-03 | 确定性：同输入两次数值一致（时间戳除外） | `det-v11.two_runs_identical` | `ccd_constraints` | `$T det-v11` | 两次 run 的 artifact 数值域 diff | 未验证 |
| RG-04 | 诊断回归：诊断管线 E2E / ontology 语义不变 | `ont-store.diagnosis_profile_unchanged` + 诊断 E2E | 既有 store / 诊断夹具 | `$T ont-store`；诊断 E2E | 诊断路径产物结构对比 | 延期（需真实诊断 harness 运行；IDD 侧以 store 结构单测覆盖） |
| RG-05 | 性能：100×8×3 ≤60s；1000×10×3 ≤120s；8 active 窗口 ≤60s；内存 <2GB | `perf-v11.*` | 合成规模夹具 | `$T perf-v11` | 计时输出 + 峰值内存 | 未验证 |
| RG-06 | 可复现：双仓库 SHA、版本、硬件、命令、输出摘要 | 本文件 §5 + `doe-baseline-2026-10-17.md` | — | 人工核对 | baseline 文档 + acceptance 摘要 | 未验证 |

## 4. 跨仓库（XR，平台侧）

| 验收 ID | 条件 | 测试 case | Fixture | 命令 | 证据 | 状态 |
|---|---|---|---|---|---|---|
| XR-01 | `doe_context → analysis_context` 一致；**无 auto-infer 兜底** | `rt.design_only_*`、`rt.collected_*`、`rt.assigned_by_user_for_declared` | `contracts/examples` | `$A docs/plans/contracts/roundtrip_test.py` | 28/28 绿 | **PASS**（IDD 侧） |
| XR-02 | artifact 回流：平台拿到 12 类工件；幂等/重试/坏 schema 显式失败 | `artifacts.manifest_12_kinds`（IDD 侧）＋平台侧 E2E | `ccd_constraints` | `$T artifacts` | manifest + `missing[]` | 延期（平台侧 E2E 属 Phase 6；IDD 侧 manifest 已备） |
| XR-03 | 优化 handoff：`optimization_guidance` 进入 campaign/optimization channel；parent/round 谱系 | `artifacts.guidance_lineage`（IDD 侧）＋平台侧 | `ccd_constraints` | `$T artifacts` | guidance 的 `lineage` 块 | 延期（同 XR-02） |
| XR-04 | 执行：run 窗口内样本 100% 关联 recipe_run_id；HITL/硬限/审计 | 平台侧 | — | — | — | 延期（Phase 6，平台 owner） |

## 5. 基线记录（Phase 0 填写）

```
IDD 主工作树 SHA:        1ff3d6c80c681edff382979c69b416fe4b5f58dd
IDD 主工作树分支:        v4-AgentWorkShopIntegrate
IDD 主工作树状态:        421 条未提交变更（并行会话；未被本计划触碰）
IDD 计划工作树:          D:/codes/myskills/idd-doe-impl
IDD 计划分支:            feat/doe-ontology-first（自 1ff3d6c）
AgentWorkShop SHA:       1e0cf1d72afabf694bc9bd87817c4c21d49a365a
Node / npm / pnpm:       v24.19.0 / 11.17.0 / 11.23.0
Python / uv:             3.12.7 / 0.11.29
Hardware:                AMD Ryzen 7 9700X 8-Core / 31.1 GB RAM / Windows 10.0.26200 x64
Date:                    2026-10-17
Runner:                  zcode agent session (AGENTS.md 工作区)
基线测试:                DOE run_tests.py = 136/136 绿；contracts roundtrip = 28/28 绿
```

## 6. Phase 0 必填 case 对照

| 建议 case | 落位 | 状态 |
|---|---|---|
| `T-DATA-01`：`00_input` 含 run_table/doe_context/exclusions 时选 run_table | `rt.aux_not_treated_as_data`、`rt.declared_table_missing_rejected`（P0-4 已实现） | **PASS**（28/28 内含） |
| `T-ONT-01`：design-only 建 ontology + brief，不跑统计 | `F13.*` | 未验证 |
| `T-ONT-02`：同 profile/scene/context_fp → reuse ≤60s；context 变化 → extend | `ont-store.*` | 未验证 |
| `T-ONT-03`：未读 brief → 阻断；读后写 analysis_plan 才继续 | `ont-gate.*` | 未验证 |
| `T-STAT-01`：PI 覆盖率 n≥2000；CI 不冒充 PI | `mc-pi-coverage.*` | 未验证 |
| `T-STAT-02`：约束绑定（无约束最优点在约束外） | `F14.*` | 未验证 |
| `T-STAT-03`：多响应 joint_setpoint 同时可行 | `F15.*` | 未验证 |
| `T-STAT-04`：单位缺失/冲突阻断 actionable window | `F16.*` | 未验证 |
| `T-NEXT-01`：aliased → fold-over；linear → augment star；non-randomized → confirm | `F19.*` | 未验证 |
| `T-ART-01`：tasks+external 均返回 12 类 artifact；缺失/坏 schema 显式失败 | `artifacts.*` | 未验证 |
| `T-REG-01`：既有 136 断言仍绿 | `$T all` | **PASS**（Phase 0 基线） |
