# Optimizer Pilot — Agent Protocol (Phase 0-4)

Execution checklist for the `optimizer-pilot` agent (骆工 · 小试闭环寻优驾驶员).
All numbers are computed by `scripts/optimizer.py` + `scripts/optcore/*`; you
never hand-compute, never edit computed numbers, and never raise the evidence
grade. Python always runs through uv from the repo root:

```bash
uv run --project "$SHARED_PATH/scripts" python "$SKILL_PATH/scripts/optimizer.py" <init|design|ingest|status|converge> --run-dir "$RUN_DIR"
```

**红线（v1.4 三系统裁决）**：IDD = 纯分析系统。你产出布点设计与分析工件，
绝不代执行试验、绝不下发参数、绝不直连知识库。试验由 AWS/人工执行。

## Phase 0 — Campaign Bootstrap

1. Confirm `RUN_DIR/00_input/objective.json` exists and satisfies O-G1
   (goal=target ⟺ target_range；tolerance 互斥；因子域完整；budget 完整)。
2. `optimizer.py init --run-dir "$RUN_DIR"` — 校验 + 建骨架 + 初始状态。
   校验失败会 exit 1 并逐条列出错误；修 objective，绝不放宽校验。
3. If the user supplied a prior doe-analyzer run, point
   `objective.prior.doe_analyzer_run_dir` at it (its
   `conclusions/recommendations.json` becomes the window prior).

## Phase 1 — Round Loop (repeat until terminal phase)

1. `optimizer.py design` → read `02_rounds/R00n/trial_design.json`.
   - `method` / `phase` / 每个 trial 的 `selection_reason` 是脚本决策的披露，
     原样转述，不得改写。
   - `extrapolation: true` 的布点在转交 AWS 时必须显著标注（越数据支撑）。
2. Hand the design to AWS/人工 (outbox / 文件协议 / 人工录入)。等待回投的
   `trial_result.json`（status: completed|failed|partial|safety_aborted|late;
   failed/safety_aborted 必带 failure_reason）。
3. `optimizer.py ingest` → read the state transition:
   - phase 变化与 `next_action.reasons` 是唯一推进依据；
   - `paused` → 报告原因（连续全失败/deadline），等人工处置；
   - `aborted` → 安全事件，立即上报 needs_human，campaign 关闭；
   - `exhausted` → 预算/重复度耗尽，转 `converge` 收尾；
   - `converged` → 转 Phase 2。
4. `optimizer.py status` 可随时查看会话摘要（JSON）。

## Phase 2 — Converge & Report (terminal phase only)

1. `optimizer.py converge` → produces
   `conclusions/optimization_conclusion.json`, `conclusions/recipe.json`,
   `report.md`, `06_experience/experience_candidates.jsonl`,
   `06_experience/kb_summary.md`.
2. `report.md` is script-generated Chinese; you may append an
   interpretation/建议 section — enrich, never rewrite computed numbers
   (`authored_by` stays "script" on all machine artifacts).
3. Run the gate (must pass before reporting done):

```bash
node "$SKILL_PATH/scripts/optimizer_gate.mjs" "$RUN_DIR" \
  --skill-path "$SKILL_PATH" --shared-path "$SHARED_PATH"
```

4. kb_summary.md 交 AWS agent 经 rag-bridge kb_agent 场景化入库
   （regime_key 为场景标题）；IDD 自己不连 KB。

## Phase 3 — Interpretation discipline

- 每个 phase 转移用一句话中文解释（引用 reasons 里的常量：ε_EI、stall、δ_confirm）。
- 双门槛结论必须逐项复述：m≥3 全落窗 / 单侧 95% CI 在限 / D≥0.8·D_max。
- recipe 仅 advisory：明确告诉用户"是否执行由 AWS/人工决定"。

## Phase 4 — Failure Recovery

| 场景 | 处置 |
|------|------|
| init/design/ingest exit 1 | 读 CONTRACT ERROR 与 EXECUTION CONTRACT，补 named 步骤 |
| GP fallback (poly_refine) | 如实披露 state.model.fallback_active，说明置信度下降 |
| 连续 2 轮全失败 (paused) | 检查 trial_result 的 failure_reason，人工排查后继续 |
| gate FAIL | 脚本侧修复重跑对应子命令，禁止手改 JSON，最多 3 轮 |
