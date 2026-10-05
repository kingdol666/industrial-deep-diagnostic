# T4 任务简报 — 闭环小试寻优（industrial-optimizer-loop × 黑箱产线）

## 场景

小试装置上一个双因子体系（反应温度 Temperature、料液浓度 Concentration）
需要降低杂质率 `impurity_pct`。真实试验由黑箱产线完成：你把优化器产出的
布点交给产线模拟器 `plant_sim.py` 执行，它按 trial_result 契约回报测量值。
IDD 侧绝不执行试验——你只负责 init → design →（调 plant）→ ingest 的轮次
推进，直到收敛或预算用尽。

## 目标契约（objective.json，与 `cases/T4_optimizer_plant/objective.json`
内容一致，init 时直接传该文件路径）

```json
{
  "contract_version": "1.0",
  "campaign_id": "OPT-20261004-001",
  "target_metric": "impurity_pct",
  "goal": "minimize",
  "tolerance": 0.55,
  "factors": [
    {"name": "Temperature", "type": "numeric", "min": 60.0, "max": 95.0, "unit": "degC"},
    {"name": "Concentration", "type": "numeric", "min": 0.1, "max": 0.9, "unit": "mass_frac"}
  ],
  "budget": {"max_rounds": 6, "max_trials": 24},
  "noise": {"replicates_for_sigma": 3},
  "seed": 42
}
```

## 黑箱产线接口（已验证）

```bash
"$PY" cases/T4_optimizer_plant/plant_sim.py \
  --design <RUN_DIR>/02_rounds/R00N/trial_design.json \
  --out    <RUN_DIR>/02_rounds/R00N/trial_result.json
```

- `--design` 接受优化器 `design` 产出的 `trial_design.json`（推荐；campaign/
  round/trial id 与 replicates 自动继承），也接受每行一个试验的
  `design.csv`（列：Temperature,Concentration；此时需补 `--campaign-id
  --round-id`）。
- 产线是确定性黑箱：相同输入永远给出相同测量；重复试验（replicates）各自
  独立测量。Plant 的内部参数对你不可见——不要试图从源码反推，按接口查询。

## 环境（已验证的入口）

- 工作目录：`workspace/field-tests/fieldtest-20261004/`
- venv Python：
  `D:\codes\industrial-deep-diagnostic\.claude\shared\scripts\.venv\Scripts\python.exe`
  （下称 `$PY`）
- 优化器脚本：
  `D:\codes\industrial-deep-diagnostic\.claude\skills\industrial-optimizer-loop\scripts\optimizer.py`
  （子命令 `init --run-dir --objective` / `design --run-dir` / `ingest
  --run-dir [--result …]` / `status --run-dir` / `converge --run-dir`）
- 收敛门禁：
  `D:\codes\industrial-deep-diagnostic\.claude\skills\industrial-optimizer-loop\scripts\optimizer_gate.mjs`
  （`node optimizer_gate.mjs <RUN_DIR> --skill-path <skill目录> --shared-path
  D:\codes\industrial-deep-diagnostic\.claude\shared`）

## 要求（RUN_DIR = `results/T4/campaign`，全部命令与退出码记入
`results/T4/commands.log`）

1. `init`（--objective 用 `cases/T4_optimizer_plant/objective.json`）。
2. 轮次循环（≤6 轮）：`design` → 按"黑箱产线接口"把该轮
   `trial_design.json` 交给 `plant_sim.py` 产出该轮 `trial_result.json` →
   `ingest` → `status` 查看 phase。phase 进入终态（converged/paused/
   exhausted/aborted）或 design 拒绝继续时停止循环，如实记录停止原因。
3. 终态后运行 `converge`，然后对整个 RUN_DIR 运行 `optimizer_gate.mjs`，
   逐项记录 PASS/FAIL 与退出码。
4. 写中文报告 `results/T4/T4_report.md`：
   - 每轮的 method、trials 数、phase 迁移（ingest 打印行逐字摘录）；
   - 最终 phase、incumbent（setpoints + measured）、confirm 轮的重复测量值；
   - `conclusions/optimization_conclusion.json` 的 `dual_gate` 各子项与
     `D`/`D_max`；`conclusions/recipe.json` 的 `final_setpoints`；
   - gate 每一项的结果。
5. 除 `results/T4/` 外不得写任何位置；不得手改脚本产出的 JSON 数值。
