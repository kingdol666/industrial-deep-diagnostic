# T3 结果报告 — industrial-tuning-memory（归因 / 入库 / 检索 / 佐证回填 / 门禁）

## 逐条命令与退出码

| # | 命令 | 退出码 | 关键输出 |
|---|---|---|---|
| 1 | `mkdir -p results/T3/run/{00_input,06_experience}` + 拷入 data.csv / action_log.json / fault_signature.json / playbook_seed 的 tuning_experience.jsonl | 0 | RUN_DIR 契约布局就绪 |
| 2 | `tune_stats.py attribute --run-dir results/T3/run --data 00_input/data.csv --time-col t --metric yield_pct --action-log 00_input/action_log.json --settle-steps 30` | **0** | 3 条归因报告写入 `06_experience/attribution/`；`1 not_estimable (honest nulls)` |
| 3 | `experience_build.mjs build --run-dir results/T3/run` | **0** | created ×2、SKIP ×1、`store=4 entries` |
| 4 | `match_playbook.mjs recommend --run-dir results/T3/run --signature 00_input/fault_signature.json --out conclusions/recommendation.json --top 3` | **0** | `playbook_hit @regime playbooks=1` |
| 5 | `experience_build.mjs feedback --run-dir results/T3/run --chunk-id exp_fault_control_recipe_PVC-M\|ca_2adda6ae0dd13c21 --result effective` | **0** | `corroboration=2 refutation=0 grade=E2 label=verified` |
| 6 | 重跑 `match_playbook.mjs recommend ...` | **0** | 刷新后 grade=E2 / corroboration=2 已反映 |
| 7 | `quality_gate.mjs results/T3/run --skill-path ... --shared-path ...` | **0** | 8/8 ALL PASS |

## 第 2 步：归因（逐字读取 attribution JSON）

| action_log_id | 动作 | attribution_status | reason_code | effect.delta | effect.ci95 | direction_established | evidence_grade |
|---|---|---|---|---|---|---|---|
| 202610041d4e2b1b | temp_c 85→77 @01:40 | **estimable** | null | **1.9928553333333525** | [1.430640409110767, 2.555070257555938]（n_eff=15） | **true** | **E1** |
| 20261004a1309c2f | pressure_mpa 2.4→2.6 @02:30 | **estimable** | null | **0.154487999999958** | [-0.21925685660480254, 0.5282328566047185]（n_eff 24/35） | **false**（CI 跨 0） | **E1** |
| 20261004451edd06 | speed_rpm 1250→1255 @03:17 | **not_estimable** | **min_points** | null | null | — | **E0** |

解读：第 3 条动作发生在 200 行数据的第 197 分钟附近，动作后剩余采样点不足（min_points），系统给出诚实空值（E0）而不是硬估。stdout 原话：`[tune_stats] 3 report(s) written, 1 not_estimable (honest nulls)`。

## 第 3 步：入库（build）

- `created 202610041d4e2b1b -> exp_tuning_action_effect_PVC-M|ca_6d7959d486594335`
- `created 20261004a1309c2f -> exp_tuning_action_effect_PVC-M|ca_ede263eec22a6f4f`
- `SKIP 20261004451edd06: attribution_status=not_estimable (admission rule)` — not_estimable 不入库（准入规则）
- `store=4 entries; kb_summary.md written`（= 2 条种子 + 2 条新建）

## 第 4 步：检索（recommend，回填前）

- `recommendation_status` = **playbook_hit**
- `match_scope` = **regime**
- 命中 playbook：`experience_id` = **exp_fault_control_recipe_PVC-M|ca_2adda6ae0dd13c21**（种子库中 PVC-M|calender-03|night_shift 的故障处置处方：temp_c 85→77 + speed_rpm 1250→1238）
- `match_score` = **1**（degradation_path: `["regime: best 1.0000 (exp_fault_control_recipe_PVC-M|ca_2adda6ae0dd13c21)", "-> playbook_hit @regime"]`）
- `evidence_grade` = **E1**（corroboration_count=1, refutation_count=0）
- 回填前 corroboration/refutation：1 / 0
- stdout 附注（原文）：`evidence grades are advisory strength only — dispatch policy is AWS-side`

## 第 5 步：佐证回填（feedback --result effective）

命令打印（逐字）：`[experience_build] feedback effective applied to exp_fault_control_recipe_PVC-M|ca_2adda6ae0dd13c21: corroboration=2 refutation=0 grade=E2 label=verified`

变化：corroboration 1→**2**、refutation 0→0、evidence_grade **E1→E2**、confidence_label **observation→verified**。

产物字段引用：
- `06_experience/tuning_experience.jsonl`（4 条，命中条目）：`{"chunk_id":"exp_fault_control_recipe_PVC-M|ca_2adda6ae0dd13c21","evidence_grade":"E2","confidence_label":"verified","corroboration_count":2,"refutation_count":0}`
- `06_experience/accumulated/state.json`：counters 中该 chunk_id `{"corroboration": 2, "refutation": 0}`；history 追加 `{"ts":"2026-10-04T06:39:01.777Z","chunk_id":"exp_fault_control_recipe_PVC-M|ca_2adda6ae0dd13c21","result":"effective","note":null}`（此前两条 build 事件也在 history 中，各计 corroboration=1）

## 第 6 步：复检 + 门禁

- 回填后重跑 recommend：仍 `playbook_hit @regime`，命中同一 experience_id，match_score=1，但 **evidence_grade 升为 E2、corroboration_count=2**，与经验库一致。
- `quality_gate.mjs` 逐项：T1_something_to_gate / T2_schema_validation (7 artifact(s), 12 element(s)) / T3_strict_extra_keys / T4_honesty_attribution / T5_enum_literals_from_closedloop_enums / T6_store_consistency / T7_recommendation_consistency / T8_privacy_no_raw_ids — **8/8 ALL PASS，exit 0**。

## 结论

- 闭环链路完整可用：3 条动作日志 → 2 estimable（E1，其中 temp_c 85→77 的 +1.99 收率效应 CI 不跨 0、方向确立；pressure 2.4→2.6 的 +0.15 CI 跨 0、方向不确立）+ 1 not_estimable（min_points 诚实空值）→ 2 条入库（not_estimable 被准入规则拒绝）→ 故障签名命中 regime 级处方（match_score=1.0）→ effective 回填后 E1→E2、label→verified → 复检一致 → 门禁 8/8。
- 无阻塞；未发现文档与 CLI 行为冲突。
