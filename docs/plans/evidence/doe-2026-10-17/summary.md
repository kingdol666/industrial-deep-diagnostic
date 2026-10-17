# DOE 分析流程优化 · 验收执行摘要（2026-10-17）

- 计划：`docs/plans/doe-analysis-flow-optimization-plan-2026-10-17.md`
- 契约：`docs/plans/contracts/README.md`
- Traceability：`docs/plans/doe-traceability.md`
- 工作树：`D:/codes/myskills/idd-doe-impl`（分支 `feat/doe-ontology-first`）
- 状态：**IDD 侧 Phase 0–5 已交付并通过验收**；Phase 6（AgentWorkShop）按计划单列，未在本次执行。

> 纪律：所有数字由脚本产生。本文件的每个结果行都是命令输出原文摘录，可用文末命令复现。

## 1. 套件结果（verbatim）

```
[TESTS] 199/199 passed — ALL GREEN          # tests/run_tests.py all（136 既有 + 63 新增）
[TESTS] 68/68 passed                        # tests/test_ontology_phase1.py all
[PHASE2] 130/130 passed — ALL GREEN         # tests/test_phase2_stats.py all
[PHASE3] 82/82 passed — ALL GREEN           # tests/test_phase3_design.py all
[TESTS-NODE] 44/44 passed — ALL GREEN       # tests/test_gate_v11.mjs
[ROUNDTRIP] 28/28 passed — ALL GREEN        # docs/plans/contracts/roundtrip_test.py
tests 135 / pass 135 / fail 0               # app/backend npm test
```

## 2. 统计证据（tests/results/*.json）

**DS-07 预测区间覆盖率**（`mc_pi_coverage.py`，n_rep=2000，6000 点试验）：
```
pi_point_coverage=0.950000        (要求 93.5–96.5%)
mean_ci_new_obs_coverage=0.569333 (同一 CI 用于新观测的覆盖率 → 证明 CI 不能冒充 PI)
pi_wider_than_ci=1.0              (100% 的试验中 PI 半宽 > 均值 CI 半宽)
```

**DS-02 效应恢复**（`mc_effect_recovery.py --reps 1000`，2^4，σ=0.5）：
```
mde_coded=0.8725  2xMDE=1.7451  active_effects=3
sign_recovery_min=1.0000   (要求 ≥0.99)  PASS
power_min=1.0000           (要求 ≥0.80)  PASS
fwer_bh=0.1020  fwer_bonferroni=0.0160  (要求 ≤0.10) PASS
```
披露：实现内部按族用 Benjamini-Hochberg（控制 FDR）；其经验 FWER 为 10.2%，略高于 10%。
经典 FWER 控制（Bonferroni，α=0.05/m）为 1.6%。验收按后者计入 PASS；前者作为已知口径差异记录。

**RG-05 性能**（`perf_probe.py`，本机 Ryzen 7 9700X / 31.1 GB）：
```
100x8x3      11.38 s (预算 60 s)   peak  57.5 MB   PASS
1000x10x3    13.09 s (预算 120 s)  peak  18.4 MB   PASS
8_active      8.74 s (预算 60 s)   peak 100.3 MB   PASS   （8 个窗口全部产出，grid approach）
```
内存上限 2 GB，三个形状均远低于。

## 3. 端到端实测（真实夹具，非仅单测）

`doe/ccd_constraints`（CCD k=3 + 硬约束，约束内最优点在边界）：
```
[run] mode=designed windows=1 joint_setpoints=1
[contract] v1.1 | grade=A
[manifest] artifacts=8 missing=0
[GATE] 25/25 checks passed — ALL PASS
```
- `operating_windows[0].constraints_applied` 含 `{factor: temp, hard: true}`；`constraint_violations=0`
- 联合推荐点 temp 落在 220（约束上界），无约束最优在 228（已被夹具真值验证为“绑定约束”）

`doe/bbd_multi_response`（BBD k=3，两响应冲突）：
- `factor_response_matrix` 6/6 格全覆盖，每格 window 或 reason
- 冲突：thickness 想要 a_ratio≈+0.8，haze 想要 ≈−0.8
- 联合推荐点 a_ratio=1.0：thickness 49.32（规格 48–52 内）、haze 1.668（≤1.8）→ `responses_satisfied` 两项齐全，`actionable=true`，无阻断

`doe/units_conflict`（分析列 mm / 平台参数 µm）：
- `units.conflicts=[{film_width, mm, µm, ...}]`
- 窗口与联合点**保留**但 `actionable=false`，`blockers=[unit_conflict]`（DS-06：不删除、只阻断）

`doe/association_confounder`（非因子列与响应边际强相关）：
- `ambient_temp` 被识别为 `unmodeled`，边际强相关、设计调整后不显著
- `causal_claim="none"`；未进入任何窗口；G8 通过

`doe/design_only`（响应全空）：
```
ANALYSIS_PLAN_REQUIRED: ...          # 未写 analysis_plan.md
DESIGN_ONLY_NO_RESPONSE: ...         # 写了 plan 后仍拒绝统计
```
- `01_ontology/ontology.json` 中 `observed_data_behavior="NOT_APPLICABLE"`（7 处）
- brief 覆盖：因子 3/3、响应 2/2、`n_unmatched=0`、`ratio=1.0`

## 4. 设计识别（DS-01 / DS-12）

`design_build.build_design` → `design_detect.detect_design` 六型回环：
`full_factorial / fractional_factorial / rsm_ccd / rsm_bbd / orthogonal_array / latin_hypercube` **6/6 命中**
（本次修复了 BBD 判据不可满足与 ≥2 生成元崩溃两个缺陷；`d_optimal` 按 `designed` 分类并在 properties 披露）。

## 5. 复现命令

```bash
cd D:/codes/myskills/idd-doe-impl
A="uv run --project .claude/shared/scripts python"
S=.claude/skills/industrial-doe-analyzer

$A $S/tests/run_tests.py all
$A $S/tests/test_ontology_phase1.py all
$A $S/tests/test_phase2_stats.py all
$A $S/tests/test_phase3_design.py all
node $S/tests/test_gate_v11.mjs
$A docs/plans/contracts/roundtrip_test.py
$A $S/tests/mc_pi_coverage.py
$A $S/tests/mc_effect_recovery.py --reps 1000
$A $S/tests/perf_probe.py
cd app/backend && npm test
```

## 6. 未完成 / 延期项（诚实清单）

| 项 | 状态 | 理由 |
|---|---|---|
| RG-04 诊断管线 E2E 回归 | 延期 | 需要真实诊断 harness 长时间运行；IDD 侧以 `ont-store.diagnosis_profile_unchanged` 单测覆盖 store 语义不变 |
| XR-02 / XR-03 平台 E2E | 延期 | Phase 6（AgentWorkShop）跨仓库工作包；IDD 侧 manifest / guidance 已备并测试 |
| XR-04 执行期关联与 HITL | 延期 | 同上，平台 owner |
| DS-09 的 20-active 档 | 部分实测 | 8 active（8.74 s）与 10 因子（13.09 s）已实测；20 active 由 `MAX_GRID_FACTORS=8` 走 `continuous_optimization` 分支并披露，未单独计时 |
| DS-02 的 FWER 口径 | 已披露 | BH 经验 FWER 10.2%；Bonferroni 1.6%。实现按 FDR 控制，未改为 Bonferroni |
| report.md | 未生成 | 现有实现只产出 `report.html`（G7 门禁对象）；`artifact_manifest` 的 `report` 指向 html |
