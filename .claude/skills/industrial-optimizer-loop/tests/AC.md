# AC — industrial-optimizer-loop 验收标准（C1–C11 逐条）

生效：2026-10-01 · 对应 plan `industrial-closedloop-skills-v1.md` §5.3（C 组）+ v1.1 增补。
全部断言由 `tests/run_tests.py`（固定 seed）机器判定；运行：

```bash
uv run --project .claude/shared/scripts python \
  .claude/skills/industrial-optimizer-loop/tests/run_tests.py all
```

| # | 验收标准（机器判定） | 测试锚点 |
|---|---|---|
| **C1** | objective 契约篡改被加载拒绝：goal=target 缺 target_range、target 带 tolerance、min/max 缺失、非法 goal → `init` exit 1 且逐条错误可读（O-G1/O-G1a） | `case_c1_objective_tamper` |
| **C2** | C4 夹具（canned recommendations.json 先验）→ R001 `method=window_seed`，三类种子逐点断言：W2_optimum = setpoints[MULTI].expected_response.raw 精确相等；window_center = 各因子 top-priority 窗口中点复合向量；current_baseline = point 原值（域内）；越域先验种子被裁剪进 O-G2 域并出 guardrail | `case_c2_window_seed` |
| **C3** | C1 号夹具（3 因子二次真值 y=60+2a−3b+c−2a²−1.5b²−c²+σ0.25noise，rsm 路径）：≤ budget/2 轮收敛（max_rounds=14 → ≤7）；incumbent 编码差逐维 ≤0.1（=编码量程 2 的 5%）；Hessian 分类 = "max"（真值二次型负定）；全程 O-G gate PASS | `case_c3_rsm_converge` |
| **C4** | C2 号夹具（2 因子 gp_ei 路径，goal=target，小预算钉死 gp_ei 分支）：converged 经 confirm_replicates；best_D（轮末累计最优）单调不降；EI 衰减（prefix 最大 EI 点被 gp_ei 采样后，其 EI 严格下降——经典 EI 消耗性质）；state.target_status.ci_in_limits=true；全程 gate PASS | `case_c4_gp_ei` |
| **C5** | 噪声校准：手写 ARD-RBF GP 在 σ=0.3 真值上 95% 预测区间对 200 个新点覆盖率 ≥90%；`d_vectorized` 与 doe-analyzer `combined_desirability` 在 target/minimize/maximize/截断四类 spec 上逐点相等（≤1e-12）；策略纯函数单测（决策树 8 行 + 转移分支） | `case_c5_noise_calibration` |
| **C6** | C3 号夹具全失败轮：全 failed 轮不推进（n_data/incumbent/best_D 不变，history.failures=n）；连续 2 轮全失败 → paused + needs_human | `case_c6_all_fail_paused` |
| **C7** | 篡改电池四连，gate 全 FAIL exit 1 且命中具体检查：①越域布点 → OG2_domain_wall FAIL；②越数据支撑（编码距离>0.8）无 extrapolation 标记 → OG3_support_flagged FAIL；③confirm 仅 2 重复仍 converged → OG4_converged_dual_gate FAIL；④违反 hard 安全限布点 → OG5_safety_absolute FAIL | `case_c7_tamper_battery` |
| **C8** | 4 schema 双验：objective / optimizer_state / trial_design / trial_result 全部过 `.claude/shared/scripts/validate.mjs` + gate 严格 extra-keys + 枚举字面值 == closedloop_enums.json（单一枚举源） | gate OG8_*（e2e 内断言） |
| **C9** | recipe envelope 与 B 组接口逐字段一致：`experience_type=optimization_recipe` + `payload{final_setpoints, achieved, guardrails, verification_status}` + `applicability{regime_key}` + `provenance{run_id, scene_key, built_from, evidence_grade, authored_by}` + `confidence_label` + `corroboration_count/refutation_count`（对齐 experience_distill.mjs 信封） | `case_c9_experience_envelope` |
| **C10** | headless E2E 全流程无 LLM：init→design→ingest×N→converged→converge 产 6 件（optimization_conclusion.json / recipe.json / report.md / experience_candidates.jsonl / kb_summary.md / optimizer_state.json），gate 16 项 ALL PASS，所有机器工件 authored_by=script；skill 脚本静态扫描无网络/LLM 依赖（requests/urllib/httpx/socket/openai/anthropic 零命中） | `case_c10_e2e_headless` |
| **C11** | trial_result 手工 CSV 模板 + 转换校验脚本：合法 CSV → trial_result.json 可被 ingest；非法输入（未设计 trial_id、failed 无 failure_reason、非数值测量）→ 生成 `<out>.error.json` 中文可读错误 + 修复指引，exit 1，不产出半成品 JSON | `case_c11_csv_converter` |

## 遗留口径声明

- GP 为 numpy 手写（零新依赖），C4/C5 直接实测（M2 前允许 SKIP 的条款因 GP 已
  完整实现而不适用——若环境缺 scipy 导致 SKIP，不算失败）。
- 编码坐标：数值因子按 objective.factors 顺序映射 x0..x(k−1) ∈ [−1,1]。
- "incumbent 编码差 ≤5%" 精确定义：逐维 |incumbent_coded − 真值最优 coded| ≤ 0.1
  （编码量程 2.0 的 5%）。
