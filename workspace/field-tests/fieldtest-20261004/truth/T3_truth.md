# T3 真值（批改依据 — 测试者禁读）

生成器：`cases/_generators/gen_T3_tuning.py`（seed 20261003）。
Examiner 已按 brief 全链实测（attribute → build → recommend → feedback →
re-recommend → gate），以下全部为实测值。

## 1. 注入真值（数据设计）

| 动作 | 时间（ts） | 动作内容 | 注入的真实效应 |
|---|---|---|---|
| A1 | 2026-10-04T01:40:00Z（数据行 idx 100） | temp_c 85.0 → 77.0 degC | **真实效应**：yield_pct 在 idx 100 起整体抬升 +1.6（≈+2σ，σ≈0.8），与降温对齐 |
| A2 | 2026-10-04T02:30:00Z（idx 150） | pressure_mpa 2.40 → 2.60 bar | **无真实效应**（yield 只是噪声，期望 Δ=0） |
| A3 | 2026-10-04T03:17:00Z（idx 197） | speed_rpm 1250 → 1255 rpm | **动作后数据不足**：200 行记录在 idx 199 结束，τ=5 后效果窗落在数据外 |

## 2. 期望的归因结论（--settle-steps 30，examiner 实测）

action_log_id（由 ts8+sha256(canonical) 派生，确定性）：

| 动作 | action_log_id | attribution_status（逐字） | reason_code | effect.delta | effect.ci95 | direction_established | evidence_grade | anti_spurious |
|---|---|---|---|---|---|---|---|---|
| A1 temp | `202610041d4e2b1b` | **estimable** | null | **+1.9929** | [1.4306, 2.5551]（不含 0） | **true** | E1 | trend=CAUTION, outlier=PASS |
| A2 pressure | `20261004a1309c2f` | **estimable** | null | +0.1545 | [−0.2193, 0.5282]（**跨 0**） | **false** | E1 | trend=CAUTION, outlier=PASS |
| A3 speed | `20261004451edd06` | **not_estimable** | **min_points** | **null**（诚实空值） | null | null | E0 | null |

要点：
- A2 的正确预期是 `estimable + direction_established=false（CI 跨 0）`，
  不是 `direction_uncertain`——状态机里 direction_uncertain 只在趋势/
  分层符号冲突时给出；tester 若把"CI 跨 0"误读成状态机枚举，属于契约
  误读（应按 schema 与实测纠正）。
- A1 的 trend_check=CAUTION 是阶梯信号上线性去趋势的正常结果（去趋势
  收缩 ≥0.3），不改变 estimable/E1 判定。
- A3 是诚实的 not_estimable：效果窗不足（MIN_EFFECT_POINTS=2 不满足），
  effect=null，**这不是失败**。
- 默认 --settle-steps（200）会把 A1/A2 的效果窗截断成 truncated——brief
  已钉死 30，tester 若自行改动参数得到不同状态，按未按简报执行扣分并
  如实记录。

## 3. 经验入库（experience_build build，实测）

- created ×2：
  - `exp_tuning_action_effect_PVC-M|ca_6d7959d486594335`（A1）
  - `exp_tuning_action_effect_PVC-M|ca_ede263eec22a6f4f`（A2）
- **SKIP** A3：`attribution_status=not_estimable (admission rule)`
  （诚实空值不入库是 v1.4 准入规则）。
- store 总数 = **4**（2 条种子 + 2 条新建）。

## 4. 检索（match_playbook recommend，实测）

- `recommendation_status = playbook_hit`，`match_scope = regime`（首级
  命中，无降级）。
- 命中条目（种子 S1，PVC-M|calender-03|night_shift）：
  chunk_id = **`exp_fault_control_recipe_PVC-M|ca_2adda6ae0dd13c21`**，
  match_score = **1.0**（dir=1.0 + jac=1.0 + regime=1.0），E1，
  corroboration_count=1。
- 种子 S2（PVC-R|calender-05，干扰项）不出现。
- degradation_path：`regime: best 1.0000 (…)` → `-> playbook_hit @regime`。

## 5. 佐证回填（feedback --result effective，实测）

- stdout：`corroboration=2 refutation=0 grade=E2 label=verified`。
- 回填后 tuning_experience.jsonl 中该 chunk：corroboration_count **1→2**，
  evidence_grade **E1→E2**，confidence_label **observation→verified**。
- `06_experience/accumulated/state.json`：counters 该 chunk
  `{corroboration: 2, refutation: 0}`，history 追加一条 result=effective。

## 6. 门禁（回填后须先重跑 recommend 再跑 gate，实测）

- 重跑 recommend：仍 playbook_hit @regime，playbook 的 evidence_grade
  已是 E2（与库一致）。
- `quality_gate.mjs`：**8/8 ALL PASS，exit 0**。
- 若 tester 回填后直接跑 gate：T7 会报
  `playbook … grade E1 != store E2`——这不是工具缺陷，是产物新鲜度问题；
  brief 已要求先重跑 recommend。批改时按 tester 实际执行顺序判定。

## 7. 批改清单

- [ ] 3 条归因的 status/reason/delta/CI/grade 与第 2 节一致（数值允许
      尾数舍入差异，枚举必须逐字）
- [ ] 正确解读 A2 的 CI 跨 0 语义、A3 的诚实空值语义
- [ ] build 事件（created×2 + SKIP×1）与 store=4
- [ ] playbook_hit @regime、命中 chunk_id 与 score=1.0
- [ ] 回填计数 1→2 与 E1→E2/verified（JSON + state 双证）
- [ ] 重跑 recommend 后 gate 8/8 PASS
