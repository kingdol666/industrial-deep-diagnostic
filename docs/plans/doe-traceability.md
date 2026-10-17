# DOE 分析流程优化 · 验收 Traceability Matrix

- 日期：2026-10-17（Phase 0 填写，Phase 5 回填结果）
- 对应计划：`doe-analysis-flow-optimization-plan-2026-10-17.md`
- 契约：`contracts/README.md`（字段/路径/枚举的单一权威源）
- 执行摘要：`evidence/doe-2026-10-17/summary.md`（命令输出原文 + 实测数字）
- 状态图例：**PASS** / **FAIL** / `延期（附理由）` / `部分`

> 规则：每条验收 ID 必须有 test case + fixture + 命令 + 证据文件。没有映射 = 未验证。
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
| OD-01 | DOE 使用 ontology-builder（profile=doe）；非另起引擎 | `F13.brief_profile_doe`、`F13.brief_fields` | `design_only` | `$T F13` | brief `profile="doe"`；ontology 由 `doe_ontology_prepare` 调 builder 契约生成 | **PASS** |
| OD-02 | 先查 store；exact reuse，无 RAG/web | `ont-store.exact_reuse_fast`、`ont-store.reuse_no_rag` | `ontology_reuse`（单测内构造） | `$A .../test_ontology_phase1.py all` | 68/68 绿；store 索引 `profile`/`context_fp`；reuse 路径 `rag_used=false` | **PASS** |
| OD-03 | design-only 先验构建；响应空可建；`observed_data_behavior=NOT_APPLICABLE`；不跑统计 | `F13.obs_behavior_na`、`F13.stats_blocked` | `design_only` | `$T F13` | ontology.json 7 处 `NOT_APPLICABLE`；`DESIGN_ONLY_NO_RESPONSE` 阻断 | **PASS** |
| OD-04 | 无 brief / 无 `analysis_plan.md` → 阻断 | `F13.brief_required`、`F13.plan_required` | `design_only` | `$T F13` | `ONTOLOGY_BRIEF_REQUIRED` / `ANALYSIS_PLAN_REQUIRED` 退出 | **PASS** |
| OD-05 | 本体后再分析；顺序可证；mode=off 时既有行为不变 | `F13.profile_with_plan`、`F13.stats_blocked`、`F1.analyze_exit0` | `design_only`、`F1` | `$T F13`、`$T all` | 199/199：mode=off 夹具零变化；gate 仅在 mode≠off 生效 | **PASS** |
| OD-06 | 一致性：causal/physical + 可归一化 sign；checked/matched/not_estimable/contradictions | `F22.*`（10 条） | 单测构造 | `$A .../test_ontology_phase1.py all` | 68/68；`ontology_feedback.json` advisory | **PASS** |
| OD-07 | 版本钉住；context 变化 → extend/新版本 | `ont-store.version_pinned`、`ont-store.context_change_extends` | 单测构造 | 同上 | store 条目含 version/context_fp；变更走 extend | **PASS** |
| OD-08 | 诊断 profile ontology 行为/CP-2/输出不变 | `ont-store.diagnosis_profile_unchanged` | 既有 store 结构 | 同上 | diagnosis 条目读作 `diagnosis`，跨 profile 不复用 | **PASS**（结构层）；真实诊断 E2E 见 RG-04 |
| OD-09 | 映射覆盖 100% matched 或 inferred+reason；0 静默 | `F13.coverage_complete` | `design_only` | `$T F13` | `n_unmatched=0`、`ratio=1.0`（3/3 因子、2/2 响应） | **PASS** |
| OD-10 | 报告引用 id 存在；允许 `no_ontology_basis+reason`；无编造 | `F22.report_refs_exist`、`F22.no_ontology_basis_allowed`；report §11 | `design_only` / 真跑 | `$A .../test_ontology_phase1.py all`；`$T artifacts` | §11 渲染 brief 覆盖率与 sha256 τ；无 brief 时显式披露 | **PASS** |
| OD-11 | 每 joint_setpoint/next_design 因子有 platform_ref；可生成 recipe_patch/node_setpoints | `artifacts.guidance_fields`、`next/guidance.*` | `ccd_constraints` | `$T artifacts`、`$A .../test_phase3_design.py all` | guidance 含 `platform_ref_missing[]`；缺 ref 的因子被移除 | **PASS** |

## 2. 统计（DS）

| 验收 ID | 条件 | 测试 case | Fixture | 命令 | 证据 | 状态 |
|---|---|---|---|---|---|---|
| DS-01 | 设计识别 full/fractional/CCD/BBD/OA/LHS 6/6 | `build.roundtrip.*` | 六型 build→detect | `$A .../test_phase3_design.py all` | 82/82；六型 6/6（BBD 判据与生成元崩溃已修） | **PASS** |
| DS-02 | 1000 次 MC；≥2×MDE 符号 ≥99%、power ≥80%；FWER ≤10% | `mc-effect-recovery.*` | 2^4（16 runs） | `$A .../tests/mc_effect_recovery.py --reps 1000` | sign 1.0000 / power 1.0000 / FWER Bonferroni 0.0160（BH 0.1020，已披露） | **PASS** |
| DS-03 | factor×response 覆盖；每格 window 或 `not_estimable+reason`；0 静默 | `F15.matrix_complete`、`F15.matrix_zero_silent`、`G11` | `bbd_multi_response` | `$T F15` | 6/6 格；G11 绿 | **PASS** |
| DS-04 | 多响应；joint setpoint；不按跨单位 delta 选赢家 | `F15.joint_spec_satisfied`、`F15.joint_actionable_implies_spec`、`F15.selection_scale_disclosed` | `bbd_multi_response` | `$T F15` | a=1.0：thickness 49.32∈[48,52]、haze 1.668≤1.8；`selection_scale=desirability` | **PASS** |
| DS-05 | 约束绑定；hard 0 违例；不可行→no window | `F14.*`（10 条） | `ccd_constraints` | `$T F14` | `constraints_applied` 含 hard temp；`constraint_violations=0`；约束最优 220 = 上界 | **PASS** |
| DS-06 | 单位：missing+reason；mm/µm 冲突负例；阻断 actionable | `F16.*`、`F16.missing_units_block` | `units_conflict`、`F3` | `$T F16` | 冲突记录 + `actionable=false`/`unit_conflict`；F3 无单位 → `unit_missing` | **PASS** |
| DS-07 | PI：n≥2000；点覆盖 93.5–96.5%；PI 宽>均值 CI；联合覆盖披露 | `mc-pi-coverage.*`、`G9` | 2^3 | `$A .../tests/mc_pi_coverage.py` | 0.950000 @ n=2000（6000 点）；PI>CI 100%；mean-CI 对新观测仅 0.569 | **PASS** |
| DS-08 | 逐因子窗口只作诊断；joint_setpoint 多响应可行 | `F15.role_marginal`、`F14.joint_within_bound` | 两夹具 | `$T F14`、`$T F15` | `window_role=marginal_diagnostic`；joint 点在硬约束内 | **PASS** |
| DS-09 | top_k + 连续优化；8/10/20 active 有界；性能分档 | `perf.8_active_windows`、`perf.1000x10x3`、`grid_plan` | 合成 | `$A .../tests/perf_probe.py` | 8 active：8.74 s / 8 窗；10 因子 13.09 s；`grid_plan.top_k=8`、`MAX_GRID_FACTORS=8` | **部分**（20-active 未单独计时，走 `continuous_optimization` 并披露） |
| DS-10 | association screen 四类；`causal_claim:none`；G8 | `F18.*`（10 条）、`G8` | `association_confounder` | `$T F18` | `ambient_temp` 边际强/调整后不显著；未进窗口；G8 绿 | **PASS** |
| DS-11 | fold-over/augment/space-filling/confirm 可执行；setpoints 在约束内 | `next.*`（四规则） | 单测构造 | `$A .../test_phase3_design.py all` | 82/82；硬约束裁剪 + `alpha_limited_by` | **PASS** |
| DS-12 | 初始设计：design_build 或 import-only；分辨率/别名/随机化/power | `build.*` | 六型 + d_optimal | 同上 | 分辨率/别名/VIF/power/MDE/D-eff + 随机化 + 区组 | **PASS** |
| DS-13 | 136 断言逐条不变；v1.1 加法；contract_status 独立 | `$T all` 全量 | F1–F12 | `$T all` | **199/199**（136 既有 + 63 新增） | **PASS** |

## 3. 工件 / 回归（AR / RG）

| 验收 ID | 条件 | 测试 case | Fixture | 命令 | 证据 | 状态 |
|---|---|---|---|---|---|---|
| AR-01 | tasks+external 同源；12 类工件；path/sha256/schema_version | `artifacts.*`（8 条）+ `getDiagTaskView` 单点注入 | `ccd_constraints` | `$T artifacts`；`npm test` | manifest 9 类实存 + `missing=[]`；sha256 全匹配；两个 API 读同一 `view.result.artifacts` | **PASS** |
| AR-02 | report 含 brief/effect/window/joint/next design；hash 可溯 | `G7b`（meta sha256）、`G7c`、§11 | `ccd_constraints` | `$G`；`$T artifacts` | `[GATE] 25/25`；`sec-11` 渲染 brief 覆盖/joint_setpoints/next_design；`REPORT_PATHS` 已扩含两新工件 | **PASS** |
| AR-03 | G1–G11 全绿；tamper 负例 FAIL；无 NaN/Inf | `G8–G11` 正负例、`tamper.*` | `gate_v11`、`tamper_*` | `node .../test_gate_v11.mjs`；`$T tamper` | 44/44（含 4×G8/4×G9/4×G10/3×G11 单缺陷负例；缺工件=n/a） | **PASS** |
| RG-01 | 既有 18 组/136 断言仍绿 | 全量 | F1–F12 | `$T all` | 136/136 包含在 199/199 中 | **PASS** |
| RG-02 | 新增 F13–F18 + artifacts + det-v11 全绿 | 全量 | 5 个新夹具 | `$T all` | 63 条新断言全绿 | **PASS** |
| RG-03 | 同输入两次数值一致（时间戳除外） | `det.recommendations_identical`、`det.effect_table_identical` | `ccd_constraints` | `$T det-v11` | 两次 run 的 recommendations/effect_table 完全一致（screen/next_design 已去除时钟） | **PASS** |
| RG-04 | 诊断管线 E2E / ontology 语义不变 | `ont-store.diagnosis_profile_unchanged` | 既有 store | `$A .../test_ontology_phase1.py all` | store 语义层通过 | **延期**（真实诊断 harness E2E 需长时间运行，未在本次执行） |
| RG-05 | 100×8×3 ≤60s；1000×10×3 ≤120s；8 active ≤60s；内存<2GB | `perf.*` | 合成 | `$A .../tests/perf_probe.py` | 11.38 s / 13.09 s / 8.74 s；峰值 57.5 / 18.4 / 100.3 MB | **PASS** |
| RG-06 | 可复现：双仓库 SHA、版本、硬件、命令、输出摘要 | 基线文档 + 证据摘要 | — | 人工核对 | `doe-baseline-2026-10-17.md` §1/§2 + `evidence/…/summary.md` §5 | **PASS** |

## 4. 跨仓库（XR，平台侧）

| 验收 ID | 条件 | 测试 case | Fixture | 命令 | 证据 | 状态 |
|---|---|---|---|---|---|---|
| XR-01 | `doe_context → analysis_context` 一致；无 auto-infer 兜底 | `rt.*`（28 条） | `contracts/examples` | `$A docs/plans/contracts/roundtrip_test.py` | 28/28；`MISSING_COLUMN`/`DUPLICATE_RUN_ID`/`MISSING_RUN_TABLE` 显式失败 | **PASS**（IDD 侧） |
| XR-02 | artifact 回流；幂等/重试/坏 schema 显式失败 | `artifacts.*`（IDD 侧） | `ccd_constraints` | `$T artifacts` | manifest + `missing[]`；后端 `npm test` 135/135 | **延期**（平台侧 E2E 属 Phase 6） |
| XR-03 | `optimization_guidance` 进 campaign；parent/round 谱系 | `artifacts.guidance_fields` | `ccd_constraints` | `$T artifacts` | guidance `lineage` 块就绪 | **延期**（同 XR-02） |
| XR-04 | 执行期关联 / HITL / 硬限 / 审计 | 平台侧 | — | — | — | **延期**（Phase 6，平台 owner） |

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
终态测试:                run_tests.py = 199/199；phase1 68/68；phase2 130/130；
                         phase3 82/82；gate-v11 44/44；roundtrip 28/28；backend 135/135
```

## 6. Phase 0 必填 case 对照

| 建议 case | 落位 | 状态 |
|---|---|---|
| `T-DATA-01`：`00_input` 含 run_table/doe_context/exclusions 时选 run_table | `rt.aux_not_treated_as_data`、`rt.declared_table_missing_rejected` | **PASS** |
| `T-ONT-01`：design-only 建 ontology + brief，不跑统计 | `F13.*` | **PASS** |
| `T-ONT-02`：同 profile/scene/context_fp → reuse；context 变化 → extend | `ont-store.*` | **PASS** |
| `T-ONT-03`：未读 brief/未写 plan → 阻断 | `F13.brief_required`、`F13.plan_required` | **PASS** |
| `T-STAT-01`：PI 覆盖率 n≥2000；CI 不冒充 PI | `mc-pi-coverage.*` | **PASS** |
| `T-STAT-02`：约束绑定 | `F14.*` | **PASS** |
| `T-STAT-03`：多响应 joint_setpoint 同时可行 | `F15.*` | **PASS** |
| `T-STAT-04`：单位缺失/冲突阻断 actionable | `F16.*` | **PASS** |
| `T-NEXT-01`：aliased → fold-over；linear → augment star；non-randomized → confirm | `next.*` | **PASS** |
| `T-ART-01`：12 类 artifact；缺失/坏 schema 显式失败 | `artifacts.*` | **PASS** |
| `T-REG-01`：既有 136 断言仍绿 | `$T all` | **PASS** |
