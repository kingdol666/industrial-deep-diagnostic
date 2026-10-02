---
name: industrial-optimizer-loop
description: "Target-driven closed-loop optimization (DMTA round state machine) for industrial small-trial campaigns. PURE ANALYSIS SYSTEM (v1.4 ruling): produces machine-executable trial DESIGN artifacts and statistical analysis only — NEVER dispatches parameters or makes control decisions; trial execution is done by AWS/人工 and fed back as trial_result.json. Session-based rounds (no resident process; all memory in optimizer_state.json): init → design (deterministic method decision tree: window_seed from doe-analyzer prior / lhs_fill / rsm_augment / gp_ei / poly_refine / confirm_replicates / screen_first) → ingest (noise-into-model + phase transition) → converge (dual gate: m≥3 confirm replicates in target window AND one-sided 95% CI in limits AND D≥0.8·D_max) → recipe + experience writeback (local files only). Zero-new-dependency numpy ARD-RBF GP (heteroscedastic nugget from replicate s²/n, L-BFGS-B log-hyperparameter fit, closed-form EI + desirability-MC-EI seed=42/1024-LHS), RSM quadratic reuse of doe-analyzer doestats (combined_desirability / refine_optimum / ols_fit). Guardrails O-G1..O-G8 with deterministic exit-code gate. Trigger: optimization loop, closed-loop optimization, target tuning, DMTA, small-trial optimization, parameter optimization campaign, converge to target, 寻优, 闭环寻优, 参数寻优, 小试优化, 目标调优, 收敛试验, optimization_recipe. Do NOT use for one-shot DOE data analysis (use industrial-doe-analyzer), fault root-cause diagnosis (use industrial-diagnostician), or 9-stage pipeline orchestration (use industrial-analysis-auto)."
---

# Industrial Optimizer Loop（目标闭环寻优）

会话式 DMTA 轮次状态机：**进程不驻留，全部记忆在 `optimizer_state.json`**。
每一轮 = `design`（布点）→ AWS/人工执行试验 → `ingest`（结果入模 + 状态转移）；
双门槛收敛后 `converge` 产出配方与经验工件。

**纯分析系统（v1.4 裁决）**：本 skill 只产布点设计与分析工件（advisory 强度），
**绝不下发参数、绝不直连知识库/RAG**；试验执行与控制决策完全由 AWS 侧负责。

## 会话轮次（Phase R）

```bash
uv run --project "$SHARED_PATH/scripts" python "$SKILL_PATH/scripts/optimizer.py" init     --run-dir "$RUN_DIR"
uv run --project "$SHARED_PATH/scripts" python "$SKILL_PATH/scripts/optimizer.py" design   --run-dir "$RUN_DIR"
#   → 02_rounds/R00n/trial_design.json 交 AWS/人工执行（ IDD 不执行）
#   → 结果写 02_rounds/R00n/trial_result.json（AWS 回投或手工录入）
uv run --project "$SHARED_PATH/scripts" python "$SKILL_PATH/scripts/optimizer.py" ingest   --run-dir "$RUN_DIR"
uv run --project "$SHARED_PATH/scripts" python "$SKILL_PATH/scripts/optimizer.py" status   --run-dir "$RUN_DIR"
uv run --project "$SHARED_PATH/scripts" python "$SKILL_PATH/scripts/optimizer.py" converge --run-dir "$RUN_DIR"   # 仅终态
```

## 方法决策树（确定性，零 LLM）

confirm→`confirm_replicates`；R1∧先验有窗→`window_seed`（W2 最优点+窗中心+baseline
三类种子）；R1 无先验→`lhs_fill`；k>8→`screen_first`（委托 doe-analyzer 筛选）；
假顶点回退→`lhs_fill` 注入；批量≥2k+4∧曲率证据→`rsm_augment`；GP 健康→`gp_ei`；
GP 病态→`poly_refine`。常量与转移条件全部钉死在 `references/method_notes.md`，
字面值来自 `.claude/shared/schemas/closedloop_enums.json`（单一枚举源）。

## 状态机

`initialized → exploring → exploiting（n_data≥max(2k+3,8) ∧ 方差>0）→ confirming
（候选落窗 ∧ EI<ε_EI 或 stall≥2）→ converged（双门槛）`；
confirming→exploiting（假顶点回退）；任意活跃态→`paused`（连续 2 轮全失败/deadline）/
`exhausted`（预算尽 ∨ duplication>0.5）/`aborted`（safety_aborted，人工关闭）。

**双门槛收敛（用户拍板）**：confirm 段 m≥3 重复全落 target_range ∧ 单侧 95% CI 在限
∧ D(x)≥0.8·D_max。

## 输入 / 输出（RUN_DIR 契约）

| 文件 | 说明 |
|------|------|
| `run_manifest.json` | init 创建 |
| `00_input/objective.json` | 目标契约（4 schema 之一；O-G1 校验） |
| `01_state/optimizer_state.json` | 会话记忆（phase/预算/incumbent/belief） |
| `02_rounds/R00n/trial_design.json` | 每轮布点（机器可执行建议，`authored_by=script`） |
| `02_rounds/R00n/trial_result.json` | AWS/人工回报（status=completed/failed/partial/safety_aborted/late） |
| `conclusions/optimization_conclusion.json` | converge 产出：双门槛细节 + 轮次史 |
| `conclusions/recipe.json` | 收敛配方（final_setpoints + guardrails 包络 + usage_rules） |
| `report.md` | 中文报告 |
| `06_experience/experience_candidates.jsonl` + `kb_summary.md` | 经验回写（**仅本地文件**；kb 摘要由 AWS agent 经 rag-bridge kb_agent 入库） |

## GP / RSM 口径

numpy 手写 ARD-RBF + 异方差 nugget（重复 s²/n 进对角）；L-BFGS-B 拟 log 超参
（bounds log0.05..log2，3 初值多点启动）；cond>1e10 → nugget×10 重试≤3 后降级
poly_refine；闭式 EI（单指标 min/max 排序）+ desirability-MC-EI（seed=42，
1024 LHS，D 复用 doe-analyzer `combined_desirability`）。RSM/多项式路径直接
`import doestats`（`sys.path` 注入 doe-analyzer scripts，与 correlation.py 复用
core_stats 同一先例）。

## 护栏（optimizer_gate.mjs，exit code 语义）

O-G1 objective 一致性（含 O-G1a 条件式）；O-G2 越域 FAIL；O-G3 越数据支撑
（编码距离>0.8 或触界）无 extrapolation 标记 FAIL；O-G4 <3 重复或任一出窗仍
converged FAIL；O-G5 安全限布点 FAIL / safety_aborted 必须 aborted+needs_human；
O-G6 失败试验必须带 failure_reason；O-G7 机器工件 `authored_by=script`；O-G8
4 schema 双验 + 严格 extra-keys + 枚举字面值（读 closedloop_enums.json）。

```bash
node "$SKILL_PATH/scripts/optimizer_gate.mjs" "$RUN_DIR" \
  --skill-path "$SKILL_PATH" --shared-path "$SHARED_PATH"
```

## Dispatch

Launch the `optimizer-pilot` subagent (`.omp/agents/optimizer-pilot.md`,
骆工 · 小试闭环寻优驾驶员)：agent 只解读脚本产出与撰写中文报告，绝不改写
`authored_by=script` 的数值、绝不代执行试验；`optimizer_state.json` 的 phase/reason
是轮次推进的唯一依据。

## Verification

```bash
uv run --project .claude/shared/scripts python \
  .claude/skills/industrial-optimizer-loop/tests/run_tests.py all
```

## Failure Recovery

| 场景 | 处置 |
|------|------|
| objective 未过 O-G1 | `init` exit 1 并列出逐条错误；修 objective 后重跑，绝不放宽校验 |
| design 报 "no trial_result" | EXECUTION CONTRACT：先执行上一轮布点并回投结果 |
| GP 病态（GPDegenerateError） | 自动切 `poly_refine`（state.model.fallback_active 披露） |
| 连续 2 轮全失败 | 自动 `paused` + needs_human；人工排除原因后从断点续跑 |
| safety_aborted | 自动 `aborted`，gate 强制 needs_human，人工关闭 |
| gate FAIL | 修脚本侧产物（禁止手改数值），最多 3 轮修复 |
