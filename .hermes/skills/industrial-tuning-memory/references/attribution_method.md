# Attribution Method（动作→效果归因，确定性方法说明）

适用脚本：`scripts/segment_selector.py`（分段）+ `scripts/tune_stats.py`（统计与状态机）。
所有公式零 LLM、零新依赖；共享数值函数**复用** `industrial-doe-analyzer` 的
`doestats/_stats_util.py`（welch_delta_ci / lag1_autocorr / effective_n），经 sys.path 注入
import，绝不重实现。

## 1. 时间约定

- Δt = 采样步长 = 数据的 1 行；所有时间量（dead_time / tau / settle）以步为单位。
- 动作时刻 `t_action` = action_log `ts` 在时间列上的最近行；时间列缺失时回退
  `context.steady_segment_ref.row_range[0]`。

## 2. 分段契约（冻结）

| 段 | 定义 | 默认 | 退化 |
|----|------|------|------|
| 基线段 | `[t_action − dead_time − N, t_action − dead_time)` | N=30 | NaN 剔除后有效点 ≥10，否则 `not_estimable/min_points` |
| 效果段 | `[t_action + tau, min(下一动作事件行, t_action + settle))` | tau=5·Δt, settle=200·Δt | 有效点 ≥2 才可 welch，否则 `min_points` |

- **dead_time 缺省 0 并降级标注**：调用方未提供时按 0 计算，且 `segment_selector` 输出
  `dead_time_assumed=true`（内部工件）；经验条目的 `applicability_note` 固定携带
  「死区时间按 0 步缺省处理（若实际死区非零，基线段可能混入动作后影响）」。
  调用方显式 `--dead-time unknown` = 拒绝假设 → `not_estimable/dead_time_unknown`。
- **截断**：效果段终点早于 `t_action+settle` 即为截断——截断源 = 下一动作事件行
  （`action_log[j]@row<i>`）或数据尽头（`data_end`），记入
  `segments.effect.truncated_by`，status=`truncated`（E0：未观察到完全整定）。

## 3. Welch 前后差 + 有效样本量进检验

复用 `lag1_autocorr` 求两段各自的 lag-1 自相关 ρ，`effective_n(n, ρ) = n(1−ρ)/(1+ρ)`（下限 2）。
n_eff 进入检验（AR(1) 伪重复校正）：

```
v_hi = s²_hi / n_eff_hi ;  v_lo = s²_lo / n_eff_lo
se   = sqrt(v_hi + v_lo)
df   = (v_hi+v_lo)² / ( v_hi²/(n_eff_hi−1) + v_lo²/(n_eff_lo−1) )
CI95 = Δ ± t_{0.975}(df) · se ,   Δ = mean(effect) − mean(baseline)
```

`n_eff == n`（ρ 缺失或 |ρ|≥0.99）时与 `doestats.welch_delta_ci` **逐位一致**（测试 B2，1e-9）。

## 4. 分层归因 stratified_before_after_delta

存在 `context.group_key` / `--group-key` 时逐层 welch。公式与 doe-analyzer
`windows.py::_stratified_tercile_delta`（L474-500）逐式对齐：

- 层内样本量 `n_layer = n_before + n_after`；`n_layer < 20` 的层**跳过并计数**
  （`stratified[].skipped=true`，delta/ci95=null）；单侧缺失的组同样按 n_layer 计入跳过；
- **层内 welch 沿用母段 lag-1 ρ**（分层不重估自相关——同一噪声过程，仅均值位移；
  交插分组的层内 lag-1 是 2Δt 量程，不具代表性）；
- 权重 `w_i = n_layer_i / n_tot`；`delta = Σ w_i·delta_i`；
- `se = sqrt( Σ w_i² · ((ci_hi−ci_lo)/(2·1.96))² )`（0 时取 1e-12）；
- `ci = delta ± 1.96·se`。

分层方向冲突（总体 delta 与分层加权 delta 符号相反，且总体 CI 已排除 0）→
`direction_uncertain`（Simpson 型方向不可信）。

## 5. 轻量 anti-spurious 链

| 检查 | 方法 | 判定 |
|------|------|------|
| 趋势混杂 | 基线+效果行合并做一次 OLS 去趋势（~row index），重算残差段均值差 Δ_dt | 收缩率 `1−|Δ_dt|/|Δ| ≥ 0.3` → `CAUTION`；Δ_dt 符号翻转 → `FAIL`（→ `direction_uncertain`） |
| 极值杠杆 | 对两段逐点留一（leave-one-out）重算 Δ，取影响最大点 | 去掉该点后 Δ 符号翻转 → `FAIL` → `not_estimable/outlier_driven`，effect=null |

## 6. 混杂与重叠

- **同参数重叠动作**：另一 action_log 在本效果窗内改变了同一参数 →
  `attribution_compromised=true`，reason_code=`overlapping_action`（仍计算效应但只产 E0）。
- **其他混杂**：效果窗内出现不同参数的其他动作事件，或 action_log 的
  `attribution_confounds` 非空 → `confound_detected=true` → 降档 E0。

## 7. 诚实状态机（判定顺序，先到先得）

1. 指标列缺失 → `not_estimable / metric_missing`（effect=null）
2. `--dead-time unknown` → `not_estimable / dead_time_unknown`
3. 基线 <10 或效果段 <2 有效点 → `not_estimable / min_points`（若已 compromised → reason 保留 overlapping_action）
4. 留一极值符号翻转 → `not_estimable / outlier_driven`
5. 趋势/分层方向冲突 → `direction_uncertain`（E0）
6. 效果窗截断 → `truncated`（E0）
7. 否则 `estimable`（direction_established = CI95 不跨 0）

**证据等级（advisory strength only — dispatch policy is AWS-side）**：
`E0 = truncated ∨ confound_detected ∨ compromised ∨ direction_uncertain ∨ retro`；
`E1 = 单次 estimable（CI 可跨 0）`。单次归因报告只产 E0/E1；E2/E3 只能由本地经验库的
佐证计数 + 统计门派生（见 `resources/evidence_grades.md`）。
