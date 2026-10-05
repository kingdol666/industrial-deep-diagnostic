# T4_result.md — industrial-optimizer-loop × 黑箱产线（闭环小试寻优）

**Brief 要求**：init（objective.json）→ ≤6 轮 design → plant_sim.py 黑箱执行 → ingest → status 循环至终态 → converge → optimizer_gate 逐项 → 中文报告（每轮 method/trials/phase 逐字、incumbent、confirm 重复测量、dual_gate 与 D/D_max、final_setpoints、gate 逐项）。

**执行与退出码**：init **0**；3 轮 design/plant/ingest 各 **0**；converge **0**；gate **0**。预算消耗 **3/6 轮、17/24 trials（19 replicates）** — 有界约束满足。

**系统产出（关键数字，逐字）**：
- R1 `[design] R001 method=lhs_fill trials=8 dup_ratio=0.0`，ingest 后 `phase exploring -> exploiting (continue_exploit); stall=0, max_EI=0.010106231806914667, best_D=1.0`；
- R2 `method=rsm_augment trials=8`，`exploiting -> confirming (enter_confirm); stall=1, max_EI=1.6327504243424482e-06`（< eps_EI 0.003191）；
- R3 `method=confirm_replicates trials=1`（1 trial × replicates=3 @ incumbent），`confirming -> converged (stop)`，next_action reasons=["dual gate satisfied"]；
- **incumbent**：Temperature=**72.039091 degC**、Concentration=**0.28382 mass_frac**，measured impurity_pct mean=0.408538（n=1，R001），in_target=true；
- **confirm 重复测量**（R003-T01）=[0.480971, 0.460278, 0.440862] → recipe.json achieved mean=**0.4607036666666667**, sd=0.020057887833302226, n=3, ci95_one_sided=[0.4268889869877244, 0.494518346345609]，verification_status=**verified**；
- **dual_gate**：replicates_in_window=true、ci_in_limits=true、desirability_gate=true、**D=1、D_max=1**；
- recipe.json `final_setpoints` = {"Concentration": 0.28382, "Temperature": 72.039091}（附 guardrails 包络与 advisory 声明）；
- **optimizer_gate 16/16 ALL PASS**（FILE_*×6 + OG1-OG8）。

**判定**：PASS。exploring→exploiting→confirming→converged 的自动迁移由 EI 塌缩与 stall 驱动，confirm 轮自动 3 重复，dual gate 三项全过，配方与包络齐备。无阻塞，无文档/CLI 冲突。

**产物**：results/T4/campaign/{run_manifest.json, 01_state/, 02_rounds/R001-R003/, conclusions/optimization_conclusion.json, conclusions/recipe.json, report.md, 06_experience/} + results/T4/{T4_report.md, commands.log}
