# T4 结果报告 — industrial-optimizer-loop × 黑箱产线（闭环小试寻优）

## 逐条命令与退出码

| 轮次 | 命令序列 | 退出码 | 关键输出（逐字） |
|---|---|---|---|
| init | `optimizer.py init --run-dir results/T4/campaign --objective cases/T4_optimizer_plant/objective.json` | **0** | campaign OPT-20261004-001；domain Temperature[60,95] / Concentration[0.1,0.9] |
| R1 design | `optimizer.py design --run-dir results/T4/campaign` | **0** | `[design] R001 method=lhs_fill trials=8 dup_ratio=0.0` |
| R1 plant | `plant_sim.py --design .../R001/trial_design.json --out .../R001/trial_result.json` | **0** | `[plant] ran 8 trial(s)` |
| R1 ingest | `optimizer.py ingest --run-dir results/T4/campaign` | **0** | `[ingest] R001: phase exploring -> exploiting (continue_exploit); stall=0, max_EI=0.010106231806914667, best_D=1.0` |
| R2 design | 同上 | **0** | `[design] R002 method=rsm_augment trials=8 dup_ratio=0.0` |
| R2 plant | 同上 | **0** | `[plant] ran 8 trial(s)` |
| R2 ingest | 同上 | **0** | `[ingest] R002: phase exploiting -> confirming (enter_confirm); stall=1, max_EI=1.6327504243424482e-06, best_D=1.0` |
| R3 design | 同上 | **0** | `[design] R003 method=confirm_replicates trials=1 dup_ratio=0.0`（1 trial × replicates=3 @ incumbent） |
| R3 plant | 同上 | **0** | `[plant] ran 1 trial(s)` |
| R3 ingest | 同上 | **0** | `[ingest] R003: phase confirming -> converged (stop); stall=1, max_EI=1.122384551009962e-07, best_D=1.0` |
| converge | `optimizer.py converge --run-dir results/T4/campaign` | **0** | `wrote conclusions/optimization_conclusion.json, conclusions/recipe.json, report.md, 2 experience file(s)` |
| gate | `optimizer_gate.mjs results/T4/campaign --skill-path ... --shared-path ...` | **0** | `16/16 passed — ALL PASS` |

循环停止原因：R3 ingest 后 phase 进入终态 **converged**（next_action.reasons=["dual gate satisfied"]），按简报停止循环。预算消耗：**3 轮（≤6）、17 trials / 19 replicates（≤24）**。

## phase 迁移链

exploring →（R1，lhs_fill 8 点，domain_coverage 0.96）→ exploiting →（R2，rsm_augment 8 点，EI 塌缩至 1.63e-6 < eps_EI 0.003191，stall=1）→ confirming →（R3，confirm_replicates 1×3 @ incumbent）→ **converged (stop)**

## incumbent 与 confirm 重复测量

- **incumbent**（来自 R001）：setpoints `Temperature=72.039091 degC, Concentration=0.28382 mass_frac`；measured `impurity_pct mean=0.408538, sd=0, n=1`；in_target=true；predicted_D=1
- **confirm 轮重复测量（R003-T01，replicates=3）**：`[0.480971, 0.460278, 0.440862]`；recipe.json 汇总 `mean=0.4607036666666667, sd=0.020057887833302226, n=3, ci95_one_sided=[0.4268889869877244, 0.494518346345609]`；verification_status=**verified**

## dual_gate 与最终配方

`conclusions/optimization_conclusion.json` 的 `dual_gate`：
- `replicates_in_window` = **true**
- `ci_in_limits` = **true**
- `desirability_gate` = **true**
- `D` = **1**，`D_max` = **1**

`conclusions/recipe.json`：
- `final_setpoints` = `{"Concentration": 0.28382, "Temperature": 72.039091}`
- guardrails 包络：Temperature [71.164091, 72.914091]、Concentration [0.26382, 0.30382]
- usage_rules 注明纯分析建议（advisory），IDD 不下发参数

## gate 逐项（16/16 ALL PASS，exit 0）

FILE_manifest / FILE_objective / FILE_state / FILE_conclusions_optimization_conclusion_json / FILE_conclusions_recipe_json / FILE_report_md / OG1_objective_contract / OG2_domain_wall / OG3_support_flagged / OG4_converged_dual_gate / OG5_safety_absolute / OG6_result_integrity / OG7_provenance_script / OG8_schema_valid / OG8_strict_keys / OG8_enum_literals — 全部 PASS。

## 结论

闭环寻优按契约完整走通：init → 2 轮探索/开发（16 点 lhs+rsm）→ EI 塌缩自动进入 confirm（1 点 ×3 重复）→ dual gate 三项全过（D=1=D_max）→ 第 3 轮收敛，预算 3/6 轮、17/24 trials。最优配方 Temperature≈72.04 degC / Concentration≈0.284 mass_frac，确认批均值 impurity_pct 0.4607 ± 0.020（单侧 95% CI [0.4269, 0.4945]），达标（in_target=true）。无阻塞，无文档/CLI 冲突。
