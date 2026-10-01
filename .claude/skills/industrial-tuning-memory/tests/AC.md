# AC（验收标准）— industrial-tuning-memory 测试电池 B1-B14

- 运行：`uv run --project .claude/shared/scripts python .claude/skills/industrial-tuning-memory/tests/run_tests.py all` → `ALL GREEN`（exit 0）
- 夹具全部为固定 seed 合成时序（numpy default_rng）；AC 定义以本文件为准，`run_tests.py` 逐条实现。
- 术语：`report` = `06_experience/attribution/{action_log_id}.json`；`store` = `06_experience/tuning_experience.jsonl`；
  `rec` = `conclusions/recommendation.json`；`gate` = `scripts/quality_gate.mjs`（T1-T8，exit 0/1）。

| AC | 定义（冻结判据） | 实现要点 |
|----|------------------|----------|
| **B1** | 非法 action_log（缺 `to` / 非法 actor_type 枚举）→ 批量拒绝：`experience_build` exit 3 且**不落库**（store 不存在/不变）；gate T2 同步判 FAIL。合法日志**重放同 id**：derived id = ts8+sha256(canonical)[..8]，二次 build → `idempotent_noop`，条目数与 corroboration_count 不变 | case_b1 |
| **B2** | 合成时序上 `tune_stats` 的 welch 前后差与**手工 `doestats.welch_delta_ci`** 一致（delta 与 CI95 双双 ≤1e-9；前置：平滑斜坡夹具 lag1 ρ≥0.99 → effective_n 返回 n，n_eff 调整路径精确退化为朴素 welch）。互补断言：AR(1) φ=0.5 夹具上 n_eff<n **确实进检验**（CI 严格宽于朴素 welch，delta 恒等）；趋势混杂夹具（共享上升斜坡）去趋势后收缩 ≥0.3 → `trend_check=CAUTION` 且状态保持 estimable/E1 | case_b2 |
| **B3** | 基线有效点 <10 → `attribution_status=not_estimable`、`reason_code=min_points`、`effect=null`（诚实空值）；store 准入拒绝（admission rule），gate 仍全绿。补充：单点极值杠杆（LOO 去点符号翻转）→ `outlier_check=FAIL` → `not_estimable/outlier_driven` 且 effect=null | case_b3 |
| **B4** | 经验条目按 **regime_key 分槽**：同动作签名跨工况 → 不同 chunk_id（`exp_{etype}_{regime_key[:8]}_{hash16}`）；**同工况二次提交（不同 action_log_id）→ 佐证 +1**，E1→E2/verified；alert 触发 + fault_signature → `fault_control_recipe` 条目（action_sequence step_order + expected_effect + fault_signature）；chunk2 佐证后与 chunk1 同向 → `cross_regime_consistent=true` → 双双 E3；kb_summary.md 场景化标题含两个 regime_key；隐私别名 eng_03 入 store | case_b4 |
| **B5** | recommend 返回 playbook：`playbook_hit` + `match_scope=regime` + score≥0.55 + evidence_grade∈{E1,E2,E3}（advisory）+ provenance_alias + recommendation_id 形如 `REC-XXXXXXXX-XXXXXX-NNN`；rec 无 `autonomy_level`；gate 全绿 | case_b5 |
| **B6** | 分层归因与**同式手算一致**（逐层 n_eff-adjusted welch + windows.py L474-500 加权/SE 方差合成，均 1e-9）；**层 <20 跳过并计数**（skipped=true, delta=null, n=12）；总体 estimable | case_b6 |
| **B7** | `attribution_confounds` 非空 → `confound_detected=true` → 归因 E0（状态仍 estimable）→ store 条目 E0 + 注记「混杂」→ **rec playbook evidence_grade=E0**（降档贯通到 recommendation） | case_b7 |
| **B8** | bundle（同 log 双参数）= 归因单元：单 report `bundle_scope=true`、单条经验（action_sequence=2）；效果窗内**同参数重叠动作** → `attribution_compromised=true` + `reason_code=overlapping_action` + truncated_by=action_log[..] + E0；后续无重叠动作 estimable | case_b8 |
| **B9** | feedback 计数升降级（纯计数驱动）：effective×2 → corroboration=3 → E2/verified；harmful×1 → 封顶 E1；harmful×2 → verified 降 observation；台账 state.history 记 4 条 | case_b9 |
| **B10** | step_detector 注入 3 个阶跃（4σ/−4σ/5σ，白噪声）：**召回 ≥90%**（定位偏差 ≤40 行）且恰好 3 条（无误报）；全部 `actor_type=unknown_retro_informed`…（实为 `unknown_retro_inferred`）+ `source=retro_mined` + advisory「仅参考」注记；入 store 后**全部 E0 锁定**，effective feedback 也不晋升 | case_b10 |
| **B11** | 隐私别名 grep 审计：别名映射后，`06_experience/**` 与 `conclusions/**` 任何 .json/.jsonl/.md 中不含原始人员 ID（grep 级断言）；store 仅含 `eng_03`；gate T8（--alias-map）通过 | case_b11 |
| **B12** | 篡改电池，gate 必须逐项 FAIL（exit 1 + 命名检查 ID）：(a) not_estimable 带 effect→T4；(b) not_estimable 缺 reason_code→T4；(c) attribution report 多余键→T3；(d) 非法枚举字面值 `maybe`→T5（对照 closedloop_enums.json）；(e) store E2 但 corroboration=1→T6；(f) retro 条目 E2→T6；(g) store 收录 not_estimable→T6；(h) rec 含 `autonomy_level`→T7 | case_b12 |
| **B13** | recommendation→执行回写关联：aws_executor 动作**缺 recommendation_ref** → 条目 `confirm_status=unconfirmed`，effective×2 佐证 3 仍封顶 E1（不晋升）；**有 recommendation_ref + executed ack** → ack 写入 rec（status=executed）→ 条目 confirmed → effective×1（佐证 2）→ E2 晋升 | case_b13 |
| **B14** | retro 兜底：无动作日志冷启动 → step_detector 反推 → store E0 条目 + kb_summary 含「仅参考」→ recommend 命中 E0 advisory playbook（或诚实降级），gate 全绿 | case_b14 |

## 附加常驻判据（蕴含于每个正向用例的 `gate_exit0`）

- gate T1-T8 全部通过：5 个冻结 schema（validate.mjs）× 全部工件、严格 extra-keys
  （store 信封字段仅 `chunk_id`/`action_signature`/`retro_mined`）、诚实性断言
  （not_estimable ⇒ reason_code ∧ effect=null；effect≠null ⇒ 状态非 not_estimable；
  truncated ⇒ truncated_by；compromised ⇒ reason_code；单次归因只产 E0/E1）、
  枚举字面值全部来自 `closedloop_enums.json`、store 一致性、rec 一致性、隐私 grep。
- 零新 Python 依赖（numpy/scipy/pandas + 复用 doestats）；归因统计零 LLM
  （所有工件 `authored_by=script`）。
