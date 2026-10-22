# DOE 分析流程优化 · 契约冻结（Phase 0）

- Date: 2026-10-17
- Plan: `../doe-analysis-flow-optimization-plan-2026-10-17.md`
- Status: **FROZEN**（P0-2 交付物）。实现阶段不得单方面更改本文件定义的字段名/路径/枚举；如需更改先改本文件并同步 traceability。
- Scope: IDD 侧数据入口契约 + 全部 artifact 契约 + 新模块函数签名 + 质量门规格 + 兼容性红线。

> 实现纪律：所有数值由确定性脚本计算；Agent 只解释，禁止手改 JSON/HTML。
> 单一权威源：本文件是字段级契约的**唯一**权威源；各 skill `schemas/*.json` 是它的可执行投影。

---

## 0. 版本策略与兼容性红线

| 项 | 决策 |
|---|---|
| schema 版本 | 加法式 `1.0 → 1.1`。`recommendations.contract_version` 由 `"1.0"` 改为发出 `"1.1"`；schema 改为 `enum: ["1.0","1.1"]`（**不是** 新 const），保证既有手写 `"1.0"` 负例夹具仍然通过 G6 |
| 新字段 | 一律**可选**，缺省不得导致已有断言变化；读取方必须容忍缺省（`.get()` / `??`） |
| `ci95` 语义 | **冻结**：继续表示“均值响应 95% 置信区间”。新增 `mean_ci95` 显式别名；新增 `pi95` 预测区间。**禁止**把 PI 写进 `ci95` |
| 质量门白名单 | `quality_gate.mjs` 的 `REC_KEYS`/`WIN_KEYS`/`CONC_KEYS` 必须与本文件 §5/§6 字段表逐字同步（否则新增字段即 FAIL） |
| 既有断言 | `tests/run_tests.py` 136 条断言逐条不变（RG-01/DS-13）。任何会改变既有夹具数值或既有字段存在性的改动 = 违规 |
| 门禁默认关 | 本体门禁（§7.3）仅当 `analysis_context.ontology.mode != "off"` 时生效；**键缺失 = off**。既有 F1–F12 不带 `ontology` 键 → 行为不变 |
| 确定性 | 所有随机路径必须显式传入 `seed`；同输入两次数值一致（时间戳除外）（RG-03） |
| 单位阻断 | 单位缺失/冲突**不删除** window（保数值断言），而是置 `actionable=false` + `actionable_blockers`，由下游拒绝执行（DS-06） |
| 路径 | 所有 artifact 落在 run_dir 内；数据发现目录 `00_input/` 只允许出现 §1/§3 的数据文件与 `exclusions/` 子目录 |

---

## 1. `00_input/run_table.csv` 契约

一行 = 一次执行（一次 run_id）。重复执行 = 新 run_id。**缺列拒绝**（不是丢弃）。

| 列 | 必填 | 类型 | 语义 |
|---|---|---|---|
| `run_id` | ✅ | str，唯一 | 单次执行标识 |
| `design_point_id` | ○ | str | 同一因子组合分组（重复点共享） |
| `replicate_group` | ○ | str | 独立重复分组（纯误差用），同 block 内 |
| `replicate_kind` | ○ | enum `repeat\|replicate\|center` | 重复性质 |
| `run_order` | ○ | int | 执行顺序（随机化检验 / 顺序效应） |
| `block` | ○ | str/int | 区组 |
| `<factor…>` | ✅≥2 | num/cat | 因子列，列名 = `analysis_context.factors[].col` |
| `<response…>` | ✅≥1 | num | 响应列；单元格**允许空**（未测/失败），空值按缺失处理并计数披露 |

- 禁止把 `doe_context.json` / `analysis_context.json` / `exclusions/*` / `*_manifest.json` / `README*` 当数据表（P0-4）。
- 排除表放 `00_input/exclusions/`（子目录，不进数据发现的候选集）。
- 完整示例：`examples/run_table.csv`。

## 2. `00_input/doe_context.json`（平台/用户输入，col 命名）

Schema：`doe_context.schema.json`。示例：`examples/doe_context.json`。
要点：`factors[].col` / `responses[].col` 指向 run_table 列名；`constraints[]` 带 `hard`；`platform_ref` 承载 RecipeWorkShop 回写所需信息；`ontology{profile,mode,scene_key,data_stage}`。
`data_stage`：`design_only`（响应未测，可先验建本体）| `collected`。

## 3. `00_input/analysis_context.json`（唯一解析后上下文）

Schema：`analysis_context.schema.json`（skill 内同名文件为投影）。
- 由 `doe_context_adapter`（或 `analyze.py --context`）生成；**合并结果直接写本文件**，不产生 `analysis_context.merged.json` 之类的第二份。
- 每字段带 `assigned_by: user|ontology|auto`（§3.1）。
- 新增可选块：`units`、`ontology`、`design_region`、`platform_ref` 透传。

### 3.1 `assigned_by` 溯源

`analysis_context.provenance.assigned_by` = `{ "<field.path>": "user"|"ontology"|"auto" }`。
最小必填路径：`data_path`、`factors[i].col`、`factors[i].unit`、`responses[i].col`、`responses[i].unit`、`responses[i].lsl|usl|target`、`constraints`、`ontology.scene_key`、`ontology.data_stage`、`blocks`、`replicates_col`、`time_col`。
**XR-01 禁止 auto-infer 兜底**：`doe_context` 提供了就必须标 `user`；只有 `analyze.py` 自动推断出来的才标 `auto`。

## 4. Artifact 清单（12 类，tasks / external 同源）

| # | kind | path（相对 run_dir） | schema | 何时产出 |
|---|---|---|---|---|
| 1 | `ontology` | `01_ontology/ontology.json` | `ontology_builder` 本体 schema | 本体 stage |
| 2 | `ontology_brief` | `01_ontology/ontology_brief.json` (+`.md`) | `ontology_brief.schema.json` | 本体 stage |
| 3 | `ontology_coverage` | `01_ontology/ontology_coverage.json` | `ontology_coverage.schema.json` | 本体 stage |
| 4 | `data_profile` | `01_profile/data_profile.json` | `data_profile.schema.json` | profile |
| 5 | `analysis_plan` | `01_profile/analysis_plan.md` | —（markdown） | profile（Agent 写） |
| 6 | `effect_table` | `02_analysis/effect_table.json` | `effect_table.schema.json` | designed |
| 7 | `model` | `02_analysis/model.json` | `model.schema.json` | designed |
| 8 | `association_screen` | `02_analysis/association_screen.json` | `association_screen.schema.json` | 两种模式 |
| 9 | `doe_conclusion` | `conclusions/doe_conclusion.json` | `doe_conclusion.schema.json` | 两种模式 |
| 10 | `recommendations` | `conclusions/recommendations.json` | `recommendations.schema.json` | 两种模式 |
| 11 | `next_design` | `conclusions/next_design.json` | `next_design.schema.json` | 两种模式 |
| 12 | `optimization_guidance` | `conclusions/optimization_guidance.json` | `optimization_guidance.schema.json` | 两种模式 |
| 附 | `report` | `report.md` / `report.html` | —（G7 门禁） | report |
| 附 | `ontology_feedback` | `01_ontology/ontology_feedback.json` | `ontology_feedback.schema.json` | 一致性回写 |
| 附 | `ontology_consistency` | `02_analysis/ontology_consistency.json` | `ontology_consistency.schema.json` | designed |

**Manifest 条目**（schema：`artifact_manifest.schema.json`）：
`{kind, path（run_dir 相对，POSIX 分隔）, url（可选）, sha256, schema_version, bytes, produced_by, ontology_version?}`。
`sha256` = 文件字节 sha256（小写 hex）。`schema_version` 取该 artifact 的 `contract_version`（无则为 `null`）。
缺失/坏 schema **显式失败**（不得静默跳过）。

## 5. `recommendations.json` v1.1 — 新增字段（冻结）

### 5.1 顶层新增

| key | 类型 | 语义 |
|---|---|---|
| `units` | object | `{factors:{<f>:{canonical,display,unit_status,source}}, responses:{…}, conflicts:[{factor_or_response, from, to, reason}]}`；`unit_status ∈ valid\|missing\|conflict` |
| `design_region` | object | `{type, hull, coded_bounds:{…}, axial_alpha, max_leverage, leverage_threshold, mean_leverage, extrapolation_risk, evaluated_points, design_hull_confidence}`；`hull ∈ box\|ccd_star\|convex_hull\|unbounded`；`design_hull_confidence ∈ high\|medium\|low`（LHS 最高 `medium`） |
| `joint_windows` | array | 多响应**同时**可行的联合域：`{id, responses:[...], factors:{<f>:[lo,hi]}, feasible, constraint_violations, predicted:{<resp>:{mean,pi95,d}}, desirability, method, evidence_level}` |
| `joint_setpoints` | array | 可执行推荐（**唯一** actionable 载体）：见 §5.3 |
| `factor_response_matrix` | array | 每 factor × response 一格：`{factor, response, window_id\|null, no_window_reason\|null, delta, effect_size, direction, fdr_q, evidence_level, confidence}`；**0 静默**（要么有 window，要么有 reason） |
| `actionable_summary` | object | `{n_actionable, n_blocked, blocked:[{window_id\|setpoint_id, reasons:[…]}]}` |
| `interval_disclosure` | object | `{pi_method, ci_method, effect_ci_method, tolerance_method, note, joint_coverage, coverage_check:{n, pi_point_coverage}}` |
| `association_screen_ref` | object | `{path:"02_analysis/association_screen.json", sha256, n_pairs, causal_claim:"none"}` —— **只放指针**，禁止内联进 window |
| `next_design_ref` | object | `{path:"conclusions/next_design.json", sha256, recommended_action, primary_action_id}` |
| `grid_plan` | object | `{n_active, top_k, grid_n, n_grid_points, approach:grid\|continuous_optimization, max_grid_points, deferred_factors:[…], truncated}` |

### 5.2 `operating_windows[]` 新增（既有 15 键不变）

| key | 类型 | 语义 |
|---|---|---|
| `window_role` | `"marginal_diagnostic"` | **冻结**：逐因子边际窗口只作诊断，不得单独当作可执行推荐 |
| `actionable` | bool | 是否可作为执行依据（须有单位有效 + 无硬约束违例 + 非外推 + `confirmation_needed=false` 或已确认） |
| `actionable_blockers` | array enum | `unit_missing\|unit_conflict\|constraint_infeasible\|extrapolation\|design_hull_low_confidence\|trend_confounded\|non_randomized_confirmation_pending\|no_prediction_interval` |
| `in_design_hull` | bool | 是否在已运行设计域/凸包内（P2-3） |
| `constraints_applied` | array | `[{factor,type,min,max,hard,source}]` 实际参与计算的约束（不再是纯回显） |
| `constraint_violations` | int | 该窗口候选点上的硬约束违例数（必须 0） |
| `predicted_at_center` | object | `{mean, mean_ci95, pi95, ti95_95}`（在窗口中心/推荐点的响应预测） |

`expected_effect` 新增：`mean_ci95`、`pi95`、`pi95_method`、`effect_ci95`、`unit_status`、`response_unit`、`tolerance_interval_95_95`。
字段语义（**四类区间必须分离**，DS-07）：

| 区间 | 字段 | 公式 |
|---|---|---|
| 均值 CI | `mean_ci95`（= 既有 `ci95`） | `ŷ ± t_{0.975,df} · sqrt(x0'(X'X)⁻¹x0 · MSE)` |
| 预测区间 PI | `pi95` | `ŷ ± t_{0.975,df} · sqrt((1 + x0'(X'X)⁻¹x0) · MSE)` ← 必须有 `1 +` |
| 效应 CI | `effect_ci95`（在 `effect_table` 行） | `β̂ ± t_{0.975,df} · se(β̂)` |
| 容差区间 | `tolerance_interval_95_95` | 正态容差因子 `k(n,df,p)` · s（覆盖 95% 总体 @95% 置信） |

红线：PI 宽度必须 > 同点均值 CI 宽度（`pi95` 半宽 > `mean_ci95` 半宽），且**禁止**任何字段把 PI 冒充合格率。

### 5.3 `joint_setpoints[]` 结构（冻结）

```
{id, method: "desirability_lbfgsb"|"grid_search"|"constraint_projection",
 factors: {<f>: <raw value>},          # 在硬约束内、在设计域内
 predicted: {<resp>: {mean, mean_ci95, pi95, d, unit_status}},
 responses_satisfied: [<resp>...],      # 满足各自 goal/lsl/usl/target
 feasible: bool, hard_constraint_violations: int, constraint_slack: {<f>: <num>},
 desirability: num|null, joint_coverage: num|null,
 evidence_level: str, confidence: enum(high|medium|low),
 window_ids: [<operating_windows[].id>...],
 unit_status: valid|missing|conflict, actionable: bool, blockers: [...]}
```

选优规则（DS-04）：**禁止**按跨单位 `delta` 绝对值选赢家；必须在**标准化效应 / desirability** 空间比较，并披露所用标度。

### 5.4 `no_window_reason` 枚举（冻结）

`NO_SIGNIFICANT_FACTOR` · `GRID_EMPTY` · `NO_FEASIBLE_POINT` · `DISCONNECTED_WINDOW` · `DIRECTION_ONLY` · `CONSTRAINTS_INFEASIBLE` · `UNIT_MISSING` · `UNIT_CONFLICT` · `EXTRAPOLATION_ONLY` · `HULL_UNSUPPORTED` · `NOT_ESTIMABLE` · `TREND_CONFOUNDED_NO_WINDOW` · `DESIGN_NOT_INFORMATIVE` · `RESPONSE_ALL_MISSING`

## 6. `effect_table.json` / `model.json` v1.1 新增

- 行新增：`effect_ci95`（见 §5.2）、`std_effect`（标准化效应，用于跨单位比较）、`term_unit`。
- 表级新增：`interval_semantics`（人类可读的方法说明）、`response_units`（`{resp: unit|"missing"}`）。
- `model.json` 新增：`design_hull`（同 §5.1 `design_region` 的 `hull/coded_bounds/max_leverage/leverage_threshold`）、`leverage`（`{max, mean, threshold, n_exceed}`）。
- **`factor_unit` 不得再恒为 null**：来源链 = `factors[].unit` → `ontology_brief.factors[].unit` → `analysis_context.units.factors[].canonical`；全缺 → `unit_status:"missing"` 且 `factor_unit:null`（**显式**披露，不再假回退 `"response units"`）。

## 7. 本体契约（Phase 1）

### 7.1 `ontology_brief.json`

必含：`contract_version`、`scene_key`、`profile:"doe"`、`data_stage`、`ontology_version`、`ontology_sha256`、`context_fp`、`factors[]`（`name/col/type/unit/expected_sign/physical_meaning/ontology_signal/confidence`）、`responses[]`（`name/col/unit/goal/lsl/usl/target/ontology_signal/confidence`）、`relationships[]`（`{from,to,relation,mechanism,confidence,evidence_level}`）、`confounders[]`、`limitations[]`、`column_mapping{matched[],inferred[],unmatched[]}`、`coverage{n_factors_matched,n_responses_matched,ratio}`、`provenance{build_mode,build_seconds,rag_used,web_used,physics_prior_used}`。

`coverage`（OD-09）：`matched`（列名/本体信号直配） / `inferred`（带 `reason`） / `unmatched`（带 `reason`）；**0 静默**。

### 7.2 `ontology_feedback.json`

`{contract_version, ontology_version, ontology_sha256, checked, matched, not_estimable, contradictions[], checked_at}`；`contradictions[]`：`{factor, response, expected_sign, observed_sign, severity: advisory|blocking, note}`。**advisory** 语义：只进报告与 watchlist，不改写统计结论。

### 7.3 本体门禁（analyze.py）

1. `analysis_context.ontology.mode ∈ {off, auto, full}`；**键缺失或 off → 门禁关闭**（既有夹具行为不变）。
2. `mode != off` 时 `profile` 阶段（`profile`/`all`）必须先存在 `01_ontology/ontology_brief.json`，否则 `SystemExit("ONTOLOGY_BRIEF_REQUIRED: …")`（OD-04/OD-05）。
3. `mode != off` 且 `01_profile/analysis_plan.md` 缺失 → 阻断（`ANALYSIS_PLAN_REQUIRED`）。
4. `design_only` 且响应列全空 → 只允许 `ontology`/`profile`/`build` 子命令；执行统计 → `SystemExit("DESIGN_ONLY_NO_RESPONSE")`（OD-03）。
5. 顺序证据：`analysis_plan` 的 `mtime`/pipeline event 必须晚于 `ontology_brief`（OD-05）。

## 8. Phase 3 artifact 契约

### 8.1 `association_screen.json`

`{contract_version, causal_claim:"none", n_rows, n_pairs, design_adjusted: bool, pairs:[{factor, response, kind: designed_factor|non_factor|held_constant|unmodeled, marginal:{r, p, n, method}, design_adjusted:{coef, p, n, method, strata}, verdict, note}]}`。
分类（DS-10）：`design_adjusted`（含设计列回归）/ `marginal` / `held_constant`（方差≈0 或与设计列共线）/ `unmodeled`（未进模型）。
**红线**：`causal_claim` 恒为 `"none"`；不得进入任何 window（质量门 G8 检查）。

### 8.2 `next_design.json`

`{contract_version, recommended_action, rationale, primary_action_id, actions:[{id, action: fold_over|augment_star|augment_axial|space_filling|confirm_replicate|none, settings:[{factor, value}|{factor, low, high}], n_runs, block_policy, replicate_policy, expected_information:{d_efficiency?, alias_break?, power_at_2mde?, coverage_gain?}, constraints_ok: bool, source_evidence:[...]}]}`。
规则（DS-11/T-NEXT-01）：`resolution<=4` 且存在别名链 → `fold_over`；线性模型且缺曲率 → `augment_star`；非随机化 → `confirm_replicate`；观测/外推区 → `space_filling`；全部 setpoints 必须在硬约束内。

### 8.3 `optimization_guidance.json`（OD-11 / XR-03）

`{contract_version, schema_version, run_id, experiment_id, ontology_basis:{profile, scene_key, version, sha256, reused, brief_ref}, objective, recipe_patch:[{factor, from, to, unit, platform_ref:{recipe_param, node_id, plc_tag, unit_conversion, rounding}, hard_limits, within_limits}], node_setpoints:[{node_id, metric, value, unit, aggregation}], constraints, next_design:{ref, primary_action_id, n_runs}, lineage:{parent_run_id, round, campaign_id}, provenance}`。
**每个** `recipe_patch`/`node_setpoints` 因子必须有 `platform_ref`（否则该因子标记 `platform_ref_missing` 并从 patch 移除，OD-11）。

## 9. 新模块接口签名（冻结）

```python
# scripts/doe_ontology_prepare.py
prepare(run_dir, *, data=None, context=None, mode="auto", scene_key=None,
        store_dir=None, seed=None) -> dict
#   -> {action:"reused"|"extended"|"built"|"skipped", ontology_path, brief_json, brief_md,
#       coverage_path, version, context_fp, scene_key, data_stage, elapsed_ms, rag_used, web_used}
enforce_gate(run_dir, ctx) -> None      # P1-5/P1-6 Phase 0 门禁（analyze.py 调用）
#   键缺失或 ctx["ontology"]["mode"] in (None,"off") -> 直接返回（门禁关闭）
#   mode != off 且缺 brief  -> SystemExit("ONTOLOGY_BRIEF_REQUIRED: ...")
#   mode != off 且缺 analysis_plan.md -> SystemExit("ANALYSIS_PLAN_REQUIRED: ...")
#   data_stage == design_only 且响应全空（统计子命令下）-> SystemExit("DESIGN_ONLY_NO_RESPONSE: ...")
# CLI: --run-dir --data --context [--mode] [--scene] [--store-dir] [--json]

# scripts/ontology_brief.py
build_brief(ontology: dict, ctx: dict, *, context_fp: str|None = None) -> dict
write_brief(run_dir, brief: dict) -> tuple[str, str]        # (json_path, md_path)
# CLI: --run-dir --ontology PATH [--context PATH]

# scripts/ontology_consistency.py
check(effect_table: dict, ctx: dict, brief: dict) -> dict    # 见 §7.2
write_feedback(run_dir, ontology_meta: dict, result: dict) -> str

# scripts/doestats/association_screen.py
screen(df, factor_info: dict, ctx: dict, profile: dict, responses: list[str]) -> dict   # §8.1

# scripts/doestats/design_build.py
build_design(spec: dict, *, seed: int|None = None) -> dict
#   spec: {design_type, factors:[{name,type,levels|low,high,unit}], model:"linear"|"quadratic",
#          resolution, n_center, n_axial, alpha, runs, criterion, blocks, replicates}
#   -> {contract_version, design_type, seed, run_table:[{run_id, run_order, block, <factor>...}],
#       coded:[...], properties:{resolution, defining_relation, alias_chains, vif, power, mde, d_efficiency},
#       randomization:{randomized, seed, block_policy}, notes:[]}
# CLI: --spec FILE [--out FILE] [--seed N]

# scripts/doestats/design_next.py
propose(profile: dict, effect_table: dict|None, model: dict|None, recs: dict, ctx: dict,
        *, seed=None) -> dict                                  # §8.2
# CLI: --run-dir

# scripts/optimization_guidance.py
build(run_dir) -> dict                                        # §8.3
# CLI: --run-dir

# .claude/shared/scripts/ontology_store.mjs（P1-2 增量）
#   addVersion({..., profile = "diagnosis", contextFp = null})
#   findMatch(dataPath, {scene, profile = null, contextFp = null})
#   索引条目新增：profile, context_fp, data_stage, scene_key（旧条目 profile 缺省按 "diagnosis"）
#   recommendReuse({dataPath, scene, profile, contextFp}) -> {status:"exact"|"scene_only"|"miss", ...}
```

`doestats/windows.py` 增量（签名冻结，供 analyze.py 接线）：

```python
# 既有（行为/签名不变，保持 136 断言绿）：
designed_windows(models, effect_table, profile, ctx, df) -> 5-tuple
observational_windows(stability, profile, ctx, df, correlation=None) -> tuple

# 新增 v1.1 入口（返回完整 dict，供 analyze.py 接线）：
designed_windows_v11(models, effect_table, profile, ctx, df, *, brief=None, seed=None) -> dict
#   {windows, interactions, confirmations, watchlist, setpoints,
#    joint_windows, joint_setpoints, factor_response_matrix, grid_plan, units,
#    design_region, interval_disclosure, actionable_summary, association_screen_ref, next_design_ref}
observational_windows_v11(stability, profile, ctx, df, correlation=None, *, brief=None, seed=None) -> dict
#   同键集合（无 designed 专属键时置 null / []）
windows_seed_export(recs: dict) -> dict   # optimizer-loop 兼容视图（见 §10）
```
> **铁律**：`designed_windows` / `observational_windows` 的既有返回值与数值语义**一字不改**
> （既有 136 断言直接消费它们）。所有 v1.1 行为只出现在 `*_v11` 入口里；共用内部实现可以重构，
> 但必须证明既有入口输出逐字段不变。

## 10. optimizer-loop 兼容（P3-4）

`industrial-optimizer-loop/scripts/optcore/windows_seed.py` 只消费：`window_role=="marginal_diagnostic"` 且 `actionable==true` 的窗口、以及 `joint_setpoints[].actionable==true` 且 `confidence>=medium` 且 `evidence_level` 满足其门槛的项。
被拒的种子必须进 `rejected_prior[]`：`{source, window_id|setpoint_id, reason}`，可追踪。

## 11. 质量门 G8–G11 规格（P4-4）

| Gate | 检查 | 缺 artifact 时 |
|---|---|---|
| G8 `G8_association_not_in_windows` | `association_screen.json` 的 pair 名不得出现在任何 window 的 `evidence_refs`/`factor`，且 `recommendations.association_screen_ref` 存在时其 `sha256` 必须与实际文件一致；`causal_claim=="none"` | n/a（skip，不 FAIL） |
| G9 `G9_interval_semantics` | 每个 window 的 `pi95` 半宽 > `mean_ci95` 半宽（同点）；`pi95_method` 含 `1 +`；不存在把 `pi95` 当合格率的字段 | n/a |
| G10 `G10_joint_actionable` | 每个 `joint_setpoints[].actionable==true` 的项：`hard_constraint_violations==0`、`unit_status=="valid"`、`constraints_ok`、在 `design_region` 内；被阻断项必须在 `actionable_summary.blocked` 中有原因 | n/a |
| G11 `G11_factor_response_coverage` | `factor_response_matrix` 覆盖全部 (factor×response)；每格 `window_id` 或 `no_window_reason` 至少其一；`no_window_reason` ∈ §5.4 枚举 | n/a |

G1–G7 语义不变；新增字段必须同步 `REC_KEYS`/`WIN_KEYS`/`CONC_KEYS`。

## 12. Phase 0 必填 case（traceability 映射）

见 `../doe-traceability.md`：`T-DATA-01`、`T-ONT-01..03`、`T-STAT-01..04`、`T-NEXT-01`、`T-ART-01`、`T-REG-01`。

## 13. Round-trip 校验

`roundtrip_test.py`：`examples/doe_context.json` → adapter → `analysis_context.json` → 断言 §3 必填路径全部带 `assigned_by`，且回读 run_table 列名一致。
运行：`uv run --project .claude/shared/scripts python docs/plans/contracts/roundtrip_test.py`

## 14. Watch 家族声明契约（stability / sentinel profiles，2026-10-22）

Schema：`watch_context.schema.json`。watch-context-v1 语义指纹的输入契约（列
col|role|unit|lsl|usl 五元组 + 窗口 factor|lo|hi 三元组，排序后 sha256）。

- **双侧同源**：`ontology_store.mjs computeWatchContextFingerprint()` 与
  `ontology_prepare_common.compute_watch_context_fp()` 1:1 镜像，跨语言对拍测试
  见 `.claude/shared/scripts/test_ontology_prepare_common.py`。
- **声明先验纪律**：`lsl/usl` 是 `normal_range` 的唯一词典外来源；词典
  `typical_ranges` 只作参考区间展示，永不入 spec/Cpk；声明的操作窗口经
  `build_baseline --ontology` 落地时一律 `window_source="ontology_declared"` +
  `confirmation_needed=true`（严重度封顶 ≤warn，`indicators` 永远 DOE-only）。
- **store 隔离**：stability / sentinel profile 的资产落
  `<scene>/<profile>/vN/`，版本号与裁剪按 (profile, scene) 作用域。
