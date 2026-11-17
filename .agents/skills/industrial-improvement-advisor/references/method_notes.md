# Method Notes — industrial-improvement-advisor（钉死常量与判定规则表）

> 本文件是 imacore 与 quality_gate.mjs 的共同逐字值来源。改任何字面量 = 破坏性变更（须同步 closedloop_enums.json 的 improvement_advisor 域并 bump 契约版本）。
> 枚举唯一源：`.claude/shared/schemas/closedloop_enums.json` → `improvement_advisor.*`；python 镜像 `closedloop_common/enums.py`。

## 1. 分级规则（grade，frozen v1）

输入快照（写入每条 action 的 `grade_inputs`，gate 重算比对）：

```
gates.data: {
  lever_variance_ok: bool,          # CV>0 且非时间不变量
  samples_ok: bool,                 # n_used>=50（分析级）; 基线>=10 有效点（关系级）
  temporal_ok: bool|null,           # null = not_assessable（dead_time 缺省）
  fdr_ok: bool,                     # bh_adjust 后 p<0.05
  confound_ok: bool,                # 分层 + LOO 后效应仍在
  regime_stable_ok: bool            # C3 分段后方向不翻转
}
gates.physics.status: known|same_domain|unknown
gates.attribution: {status: estimable|direction_uncertain|truncated|not_estimable|absent, ci_excludes_zero: bool|null}
context_flags: {objective_inferred: bool, conflict: bool, extrapolated: bool, dead_time_missing: bool, tradeoff_declared: bool}
```

等级判定（自上而下，命中即定）：

| 等级 | 条件 |
|---|---|
| **A** | 门 A 全过（temporal_ok=true 且其余五项 true）∧ physics=known ∧ attribution ∈ {estimable∧ci_excludes_zero} ∪ {designed_window=true} ∧ ¬objective_inferred ∧ ¬conflict ∧ ¬extrapolated ∧ ¬dead_time_missing |
| **B** | 门 A 全过或仅 temporal_ok=null（dead_time_missing）∧ (physics ∈ {known, same_domain}) ∧ ¬conflict ∧ ¬objective_inferred∧收益 CI 不跨 0 ∧ 非 A |
| **C** | 门 A 过（允许 temporal_ok=null / fdr 边缘）但：physics=unknown ∨ attribution 降级（direction_uncertain/truncated/not_estimable/absent）∨ 收益 CI 跨 0 ∨ objective_inferred ∨ conflict ∨ extrapolated |
| **处方区** | 触发清单任一命中（见 §4）→ 不产 action，产 prescription |

补充硬规则：
- `objective_inferred=true` → 全部 action ≤ B；且若已因其他原因 ≤ C 则保持 C。
- `conflict=true`（目标冲突涉及的杠杆）→ 该 action 封顶 C + tradeoff 标签。
- `extrapolated=true` → 封顶 C 且 `expected_gain.verified=false`。
- `tradeoff_declared=true`（其他 KPI 显著恶化）→ 封顶 B。
- **A 级 >3 条 → gate FAIL**（门禁 bug 哨兵，不是业务规则）。
- `time_invariant` 杠杆（CV=0）→ excluded_levers[reason=no_variance]。

## 2. 三重门细则

### 门 A · 数据门
- 杠杆变异：`CV = std/|mean| > 0`（容差 1e-12）且不同值个数 >2；否则 no_variance。
- 样本：分析级 n_used ≥ 50；AR(1) 有效 n（`doestats.lag1_autocorr` + `effective_n`）如实披露于证据记录 `n_eff/rho_lag1`，有效 n < 关系级下限时 samples_ok=false。
- 时间先后：`core_stats.full_lag_ccf(x, y, max_lag)`，max_lag = dead_time 给定时 `max(1, ceil(dead_time))`；峰 `find_best_lag` 须落在 [0, max_lag] 内且 |r| ≥ 0.2（P20 最小效应门槛，可被 fixture 覆盖）。dead_time 缺省 → `null`（not_assessable）。
- 统计显著：对每个 KPI 的 (杠杆×滞后) 全部检验 p 值跑 `doestats._stats_util.bh_adjust`（族内 q=0.05），峰值检验 q<0.05 才过。p 值由 `core_stats.pearson` 的 t 检验等价式（`_t_pvalue`，双尾）取得（复用，不新写）。
- 混杂免疫：若存在分组列（group_col/context）→ `core_stats.pearson` 子组方向一致；否则 `stats.anti_spurious._leave_one_out_leverage`（家族规范实现：单点移位 >0.15 即 leveraged → 不过）。
- 方向稳健：按时间三等分或 C3 变点分段（若 regime 模块可用）后各段 r 符号一致；否则用三等分兜底并披露。

### 门 B · 物理门
- 本体 `signals.*` 中杠杆的 physical_meaning_confidence：KNOWN → known；INFERRED/词典命中 → same_domain；缺失 → unknown。
- 有 `relationships[]` 边 lever→kpi：`expected_sign` 语义 = **dKPI/dlever**（DOE 约定），与本次数据斜率符号（`sign(slope)`）一致 → known；无方向边/同族先验 → same_domain；矛盾 → unknown（mechanism_contradicted，不晋级）。
- 与 line-memory 共识（≥3 独立观测）**反方向** → 不得晋级（记 C，grade_reasons 含 `memory_conflict_strong`）。

### 门 C · 归因门
- 调用 `tune_stats.py attribute`；读 attribution_report 的 `attribution_status` 与 `ci95`/`effect`。
- 无 action_log → `absent`：观察数据最高 B（A 需要 designed_window 路径）。
- estimable ∧ CI95 不跨 0 → 可冲 A；否则封顶 C。

### 设计窗判定（A 的窗路径）
- doe recommendations 的 operating_window 可用且 run_manifest/`confirmation_needed` 表明来自**设计试验**（`design_type ∈ {full_factorial, fractional_factorial, rsm, box_behnken, ccd, doe}` 且 `confirmation_needed=false`）→ `designed_window=true`。
- 观测窗（confirmation_needed=true 或 design_type 缺失/observational）→ 只算窗对照证据腿，不构成 A 路径。

## 3. 预期收益算法（frozen v1，全部带 95% CI）

优先序（腿 1 → 3；前腿 not_estimable 才落到后腿）：
1. **dose_response**：等频分箱箱数 `k = min(8, n//8)`，k≥5 且每箱 n≥8 才启用。箱(杠杆中位, KPI 中位) 点拟合：`doestats.ols_fit(X, y)` 斜率 b 与 CI95；Theil-Sen 用 lstcore 同款实现交叉核对（斜率符号一致才采信）；单调性 `Mann-Kendall`（lstcore）p<0.05 才有外推资格。收益点值 = b × 建议 delta；CI95 = b_ci × delta；KPI 方向按目标 direction 决定符号（min：下降为收益；max：上升为收益）。**单调性不成立 → 本腿仍可出点值但 `verified=false`（未验证）且禁止外推**。
2. **window_contrast**：doe 操作窗 [lsl, usl]；当前中位在窗内 → 无收益语义（skipped）；在窗外 → 用窗内样本 vs 窗外样本 `welch_delta_ci(x_hi, x_lo)`（复用）得 KPI 差 CI；收益 = 回到窗边（最近边界）方向的 |delta| 折算。
3. **attribution_delta**：tune_stats effect + ci95 直接搬运（幅度归一化到本建议 delta 与历史动作幅度的比值）。
4. 全 unavailable → `point=null, ci95=null, method="none", not_estimable_reason` ∈ {`lever_no_variance`, `no_significant_relation`, `window_truncated`, `confound_unresolvable`, `reuse_leg_unavailable`}；**action 仍可存在（C 级定性方向）但 verified=false**（用户裁决：C 级定性允许展示 + 强制未验证标注）。

外推护栏（O-G3 同款）：建议目标值对数据包络编码距离 >0.8 或触界 ±1e-9 → `extrapolated=true`；编码距离 = |to − mean| / (range/2)。

**目标方向与收益符号基准**：`direction=target` 的当前值基准是 **KPI 自身在数据窗的中位数**（写入 `expected_gain.current`），绝不是杠杆值；`want` 与 `required_lever_sign` 都以它为基准。gate 重算必须用 `expected_gain.current`（缺失时回退 `magnitude.from` 仅用于旧产物）。

## 4. 处方优先触发清单（→ prescription，不进建议区）

① 杠杆无变异（全部候选 CV=0 / 时间不变量）
② 有效样本不足（n_used<50 或关系级有效点 <max(10,2×dead_time+2)）
③ BH-FDR 后与全部可操作参数无显著相关，或反向因果排除后杠杆集为空（处方：设计试验分离因果）
④ 建议点越数据包络（extrapolated）且无剂量响应单调性
⑤ 与 line-memory ≥3 独立观测反方向共识冲突且己方证据更弱
⑥ 机制 unknown 且无归因（处方：建/补本体，或先做小试验证）
⑦ 结论依赖未记录外生事件（检修/换料/批次切换——数据中无法识别时以 limitations 明示，不自动判定）
⑧ 越安全限/规格限方向（constraints[type=safety, hard=true] 越界方向）

prescription.kind 映射：①→data（补变异数据/换数据窗）②→data ③→experiment ④→experiment ⑤→data ⑥→ontology 或 experiment ⑦→data ⑧→data（不可执行，需工程变更评审）。

## 5. 目标推断（模糊模式，frozen v1）

- 候选 KPI 资格：numeric 列 ∧ 非时间/非分组 ∧ ¬被声明为杠杆（context/ontology control）∧ （本体 role ∈ {target, inspection} 或列在 `kpis` 显式声明）∧ 当前中位偏离规格/操作窗/稳健基线之一。
- 禁止：无显著相关可操作参数（全部 |r|<0.2 或 FDR 后不显著）的 KPI 当目标；反向因果参数作杠杆。
- 排序 = 偏离度（相对规格带） × 传导强度（显著杠杆中最强 |r|） × 数据充分度（log10 有效点数）。
- 输出 `objective_resolved.json {inferred:true, targets:[top1], candidates:[...], rationale}`；HTML 首卡标注"系统推断目标"；全建议 cap B。用户显式声明目标重跑即解锁 A 路径。

## 6. 数值口径与容差

- gate 重算比对容差：`max(1e-9, 1e-6·|declared|)`。
- 收益 CI 一律 95%（`welch_delta_ci` conf=0.95；OLS t 双尾 0.05）。
- 小数展示：报告层保留 3 位有效数字；JSON 全精度。
- 相关性最小效应 |r|≥0.2（P20 门槛）；"无显著相关"判定 = FDR 后无 q<0.05 且 |r|<0.2。

## 7. 复用降级链

- `doestats`/`tune_stats`/`lstcore`/`core_stats` 任一不可 import：
  - 对应证据腿记 `degradations[{leg, status:"failed", reason}]`；
  - 该腿产出 `method:"none"` + `not_estimable_reason:"reuse_leg_unavailable"`；
  - action 降为 C 级定性方向 + `verified=false` + "未验证"标注（用户裁决 2026-11-16）；
  - 全证据腿 + 生成本体均不可用 → exit 2（not_actionable），只出处方。
- 绝不因复用缺席而编造数值。

## 8. 输出上限与排序

- actions ≤ 12 条（priority_score 降序截断）；HTML 展示 A/B 全量 + C 前 6。
- priority_score = grade_weight × gain_ratio × evidence_strength × feasibility：
  - grade_weight：A=1.0 / B=0.6 / C=0.25
  - gain_ratio：|point| / max(|point|)（无 point → 0.3 基值）
  - evidence_strength：|r|（或窗效应 Cohen's d 归一）∈[0,1]
  - feasibility：约束余量（到边界距离/幅度，封顶 1.0）
