# method_notes — industrial-optimizer-loop 口径钉死

生效：2026-10-01 · 依据：`.omc/plans/industrial-closedloop-skills-v1.md` §5（C 线）
+ `.claude/shared/schemas/closedloop_enums.json`（单一枚举源）
+ `.claude/shared/references/evidence-autonomy-alignment.md`（v1.4 纯分析裁决）。
**改这里的任何一个常量 = 破坏性契约变更**（须同步 closedloop_enums.json 并升
contract_version）。

## 1. 常量（全部从 closedloop_enums.json optimizer.constants 读取）

| 常量 | 值 | 含义 | 代码锚点 |
|------|-----|------|---------|
| `epsilon_ei_frac` | 0.005 | ε_EI = 0.005·D_span（D_span = 当前观测 D 的 max−min；退化时取 1.0） | `strategy.eps_ei` |
| `stall_rounds` | 2 | 连续 2 轮无更优点（incumbent 点恒等）或 EI<ε 触发 confirming；连续 2 轮全失败 → paused | `strategy` |
| `delta_confirm_coded` | 0.05 | 编码距离判重半径（duplication）；confirm 邻域 | `acquisition.greedy_batch` |
| `domain_coverage_duplication_ratio_max` | 0.5 | 一轮布点 dup 占比 > 0.5 → exhausted | `strategy.transition` |
| `neighborhood_coded` | 0.8 | 数据支撑半径：编码距离 > 0.8（或触域边界）→ extrapolation=true（O-G3） | `acquisition` |
| MC seed / samples | 42 / 1024 | desirability-MC-EI 的 LHS 抽样 | `gp.mc_ei_desirability` |
| GP bounds | log 0.05 .. log 2 | log 超参（ℓ_i, σ_f, σ_n；y 标准化 + 编码空间，量纲无关） | `gp.GPFit.fit` |
| GP multi-start | 3 | ℓ 初值 {0.2, 0.6, 1.2}，σ_f=1.0, σ_n=0.1 | 同上 |
| GP 病态阈值 | cond(K_y) > 1e10 | nugget×10 重试 ≤3 次，仍病态 → `GPDegenerateError` → poly_refine | 同上 |
| exploring→exploiting | n_data ≥ max(2k+3, 8) ∧ 方差>0 | 状态机转移 | `strategy.explore_target_n` |
| 双门槛 | m≥3 全落窗 ∧ 单侧95%CI 在限 ∧ D≥0.8·D_max | USER DECISION 2026-10-01 | `strategy.evaluate_confirm_gate` |
| 曲率证据 | 编码二次/交互项 |t| ≥ 2.0（OLS se=sqrt(σ²·diag([X'X]⁻¹))，与 effects_anova 同源口径） | `rsm_model.fit_quadratic` |
| rsm_augment 批量 | 2k+4 | 中心 + 2k 轴点(±0.6) + 角点补足 | `rsm_model.propose_rsm_augment` |

## 2. 状态机转移（精确条件）

```
initialized --design R1--> exploring
exploring   --n_data≥max(2k+3,8) ∧ y方差>0--> exploiting
exploiting  --候选落窗 ∧ (max_EI<ε_EI ∨ stall≥2)--> confirming
confirming  --confirm 轮 m≥3 全落窗 ∧ CI 在限 ∧ D≥0.8·D_max--> converged
confirming  --双门槛未过--> exploiting (fake-summit; 下轮注入 LHS 点)
任意活跃态  --safety_aborted--> aborted (needs_human, 人工关闭)
任意活跃态  --连续 2 轮全失败 ∨ deadline 已过--> paused (needs_human)
任意活跃态  --轮/试验预算尽 ∨ dup_ratio>0.5--> exhausted
```

- **stall 定义**：stall = 连续轮数，其中"无更优"判定为 incumbent setpoint 恒等
  （按 6 位小数取整比较）。不用 D 增量判停滞——D 的 grid 随观测范围每轮重标定，
  跨轮 D 差不带符号，不可比。
- **confirm 透支 1 个设计点**：transition 中 confirm 判定/进入优先于预算耗尽；
  进入 confirming 后 design 允许在 max_trials 用尽时超额布 1 个 confirm 点
  （否则 campaign 会永远卡在 confirming 无法闭合）。confirm 失败 ∧ 预算尽 →
  直接 exhausted（无回退空间）。
- **confirm 轮不计 dup**：confirm 的目的就是复测 incumbent，dup_ratio 钉 0.0；
  transition 中 confirm 判定优先于预算耗尽（结论不被预算吞掉）。
- **in_window 定义**：goal=target → incumbent 均值 ∈ target_range；
  goal=min/max → incumbent.predicted_D ≥ 0.8·D_max（同一次 ingest 内计算，自洽）。
- **D_max**：max(观测点 D, GP 后验均值在 256 候选网格上的最大 D)。D 为
  doe-analyzer `combined_desirability`（goal=target → 三角型 lsl/usl/target）。
- **单侧 95% CI**：mean ± t_{0.95, m−1}·s/√m；goal=target 双侧限均须在内，
  maximize 只查下限（lsl/tolerance），minimize 只查上限。

## 3. 方法决策树（先命中先执行）

```
1. phase==confirming                     → confirm_replicates
2. R1 ∧ prior 有有效窗                   → window_seed（W2_optimum / window_center /
                                           current_baseline 三类种子）
3. R1（无先验）                          → lhs_fill
4. k > 8                                 → screen_first（筛选后委托 doe-analyzer）
5. 假顶点回退挂起                        → lhs_fill（注入点）
6. 批量≥2k+4 ∧ 曲率证据                 → rsm_augment（doestats 同语义）
7. GP 健康                               → gp_ei
8. GP 病态                               → poly_refine（二阶多项式 + L-BFGS-B 盒内细搜）
```
"批量≥2k+4" 的机器含义：预算剩余 ≥ 2k+4（`affordable_rsm`）。

## 3b. EI 判据尺度（钉死，双轨）

- **goal=target 或存在 secondary_metrics** → D 尺度 desirability-MC-EI
  （seed=42 / 1024 LHS），ε_EI = 0.005·D_span（观测 D 的 max−min）。
- **单指标 minimize/maximize 且无 target 锚** → 闭式 EI（y 尺度；此时 D 是 y 的
  网格相对单调线性变换，D_best≡1 会让 EI 退化，禁用），ε_EI = 0.005·y_span
  （观测 y 值域）。trial_design 的 `ei` 字段记录当轮所用尺度的 EI。
- 两轨的选择由 `acquisition._single_linear` 判定，全链一致（排序、ε 判据、
  belief.max_ei_last 同尺度）。

## 3c. 曲率证据探测（降级口径）

全二次 (1+x+x²+x:x) 参数数 = 1+2k+k(k−1)/2；探索批 (max(2k+3,8)) 的 n 不足以
估计全二次时，**曲率证据退化用降级模型 1+x+x²**（t 检验同式，|t|≥2.0），
保证 rsm_augment 分支从最小探索批起可达；rsm_augment 的驻点定位同样按
n 自动选全/降级模型。

## 4. GP 口径（零新依赖，numpy 手写）

- ARD-RBF：k(x,x′)=σ_f²·exp(−½Σᵢ(xᵢ−x′ᵢ)²/ℓᵢ²)；X 一律编码 [−1,1]（x0..x{k−1}，
  数值因子按 objective.factors 顺序）；y 内部标准化。
- **异方差 nugget**：对角 = σ_n² + s²_j/n_j（第 j 点重复样本方差/计数）；
  noise_source ∈ {replicates, known_sigma(保留), residual_pool}。
- 拟合：负 log 边缘似然，L-BFGS-B，θ=[log ℓ₁..log ℓ_k, log σ_f, log σ_n]，
  bounds [log 0.05, log 2]，3 初值取最优 log_ml。
- 预测：μ* = k*ᵀK_y⁻¹y；σ*² = k** − k*ᵀK_y⁻¹k*（+σ_n² 预观测）。
- EI：单指标 minimize/maximize 用闭式 EI 做候选排序与 ε 判据（y 尺度，锚
  0.005·y_span——见 §3b 双轨）；target/多目标用 D 尺度 MC-EI（seed=42，1024
  LHS 逆正态抽样，E[max(D(y*)−D_best,0)]，真 Expected Improvement 语义，
  在确认点衰减到噪声底）。trial_design 的 `ei` 字段 = 当轮尺度的 EI 值。

## 5. 借鉴登记（外部设计来源 → 本实现映射）

| 来源 | 借鉴点 | 落点 |
|------|--------|------|
| jkitchin/skillz design-of-experiments | BO/RSM 决策树、EI 停止、确认试验 | §3 决策树 + confirming/converged |
| Seifrid 2022 (DMTA closed loop) | 会话式轮次（design→execute→learn） | RUN_DIR 契约 + optimizer_state.json |
| RSOS 2025 self-driving labs review | stall/预算/exhausted 终止语义 | strategy.transition |
| doe-analyzer rsm.py | combined_desirability / refine_optimum / 驻点-Hessian 分类 | rsm_model.py 直接 import |
| doe-analyzer effects_anova | OLS t 检验曲率证据（se 同式） | rsm_model.fit_quadratic |
| doe-analyzer correlation.py 复用 core_stats 先例 | sys.path 注入跨 skill 复用 | rsm_model.py 头部 |
| experience_distill.mjs 信封 | experience_type/payload/applicability/provenance/confidence_label | experience.build_envelope（C9 对齐） |

## 6. v1 范围声明（诚实披露）

- **分类因子**：v1 全程固定在 campaign level（baseline level 或首水平），
  只记录不建模；GP/RSM 只作用于数值因子。升级路径：one-hot + ARD。
- **多指标**：secondary_metrics 进 D（desirability 加权几何平均），每个指标
  独立 GP；MC-EI 自动多目标化。
- **迟到达**（late_results）：并入 assigned_round 历史池重新拟合，不回滚任何
  已出判定（trial_result schema 注释契约）。
- **经验回写只落本地文件**（`06_experience/`），kb 入库由 AWS agent 经
  rag-bridge kb_agent 完成；IDD 不连外部服务（v1.4 三系统分权）。
- converged=verified（E2 级）、paused|exhausted=observation（E1 级）、
  aborted 不产配方。
