# method_notes.md — industrial-sentinel 方法注记

定位：**纯分析产线哨兵**。只产告警/报告工件，绝不下发参数（v1.4 用户裁决，见
`.claude/shared/references/evidence-autonomy-alignment.md`）。本文记录每个统计决策的
定义、公式与默认值依据；枚举字面值的唯一来源是
`.claude/shared/schemas/closedloop_enums.json`（Python 侧经
`closedloop_common/enums.py` 镜像引用，脚本逻辑禁止手写字面量）。

## 1. σ 估计与 Nelson 规则（C1）

- **σ_within = MR̄ / d2，d2 = 1.128**（移动极差 MR(2) 的均值除以无偏常数），与
  doe-analyzer `stability_report.capability[].sigma_within_mr` 同源同口径。
  基线存储 `sigma_within_mr`，watch 直接引用，不在窗口内重估（避免把漂移吃进 σ）。
- z = (x − center) / σ_within，center/σ 均来自基线；NaN 行不参与。
- 规则（个体值图，标准定义）：

| 规则 | 触发条件 | severity（冻结语义） |
|------|----------|----------------------|
| R1 | 单点 \|z\| > 3 | high（统计异常） |
| R2 | 连续 9 点同侧 | warn（趋势） |
| R3 | 连续 6 点单调升/降 | warn（趋势） |
| R5 | 3 点中 2 点同侧超 2σ | high |
| R6 | 5 点中 4 点同侧超 1σ | high |

- **物性下限（materiality floor，可配置，默认 0 = 教科书 Nelson）**：
  `r2_materiality_z` 要求 R2 触发段前 9 点的中位同侧 z ≥ 阈值；`r3_materiality_z`
  要求 R6 点总位移 ≥ 阈值。默认 0.0 是 M0 冻结行为； tightly-controlled 回路
  （自相关、小幅振荡）在个体值图上 R2/R3 会以 ~1/256、~1/350 每点的受控误报率
  触发（组合 ARL0 ≈ 90 点），生产上可用该阈值换取误报下降（§7 有权衡说明）。
- **episode 合并**：相邻/重叠触发合并为一个 episode（首个触发点为 observed.index），
  避免一段持续偏移产生数百条告警。
- **重估中心线**：检出新变点后，静默期（§6）结束起的其余行用该段自身均值重估中心
  （σ 仍用基线值），再跑一遍五规则；两段评估行集互不重叠。

## 2. 窗口漂移投影（C2）

对每条从 doe-analyzer `recommendations.operating_windows` 逐值搬运的操作窗
（factor + range [lo, hi] + confirmation_needed），取稳态行：

```
slope_per_hour = (mean(last 25%) − mean(first 25%)) / Δt(两段中心)   # 方向感知
current        = mean(last 25%)
edge           = hi  (slope>0) | lo  (slope<0)
hours_to_edge  = (edge − current) / |slope|     # 已越界记 0 并转 WINDOW_OUT_OF_RANGE
```

- severity：`hours_to_edge ≤ 8h → high`；`≤ 24h → warn`；其余 info（阈值
  `hours_alarm`/`hours_warn` 可配置）。**confirmation_needed=true 的窗一律封顶
  warn 且 advisory=true**——与 doe-analyzer G4 硬门构成"契约一致"声明（同一语义
  在两个 skill 强制对齐，见 evidence-autonomy-alignment.md）。
- 当前值已越出 [lo, hi] → `WINDOW_OUT_OF_RANGE`（critical / immediate；同样受
  confirmation_needed 封顶约束）。
- 指标规格界（基线 indicators 的 lsl/usl）：任一行越界 →
  `WINDOW_OUT_OF_RANGE`（critical）。doe 窗≠硬规格，但越窗是必须立即知晓的事实。
- 时间轴换算：datetime 列 → 相对小时；数值列 >1e8 视为 epoch 秒；其余数值视为
  已是小时（文档化约定）。无时间列时跳过投影（报告中注明，不猜测）。

## 3. 稳态/变点映射（C3）

- **复用 data-processor 的 production_regime_detector（进程内 import，绝不
  subprocess）**：`detect_by_variance_fast`（滑窗方差比）+ `detect_drift_ramps_fast`
  （滚动回归斜率）→ `fuse_regimes` 得逐行标签
  （steady/marginal/transition/abnormal/startup/shutdown）。
- **变点改在 z_mean 序列上做二元分割**：detector 的 `detect_change_points_fast`
  要求 ≥2 参数在 window 行内聚类一致，单一漂移参数永远无法满足；故哨兵对
  （基线标准化的）逐行平均 z 序列复用其 `_binary_segmentation_fast`
  （前缀和 SSE 分割，进程内），并加显著性过滤。
- **显著性过滤（冻结依据）**：保留满足
  `|mean(z[cp:cp+L]) − mean(z[cp−L:cp])| ≥ cp_min_shift_z`（默认 0.5σ）的变点，
  对称窗 L = clamp(n/4, 50, 4000) 行。对线性漂移，段均差 = slope·L 与 cp 位置
  无关（F2：0.0008·2500 = 2.0σ ✓）；纯噪声变点给出 ~√(2/L)σ（L=2500 时 0.028σ），
  两侧分离约一个数量级。聚类容差 = window_rows。
- **REGIME_CHANGE_NEW**：过滤后变点与 `baseline.regime.known_change_points`
  差集（±0 行精确差集；fast 流式场景索引空间连续）。severity warn。
- **REGIME_ABNORMAL**：labels == `abnormal` 的行占比 >0.15 → high、>0.3 →
  critical（阈值 `abnormal_ratio_warn/critical` 可配置）；startup/shutdown/
  transition 属物理状态，进 regime_summary 不告警。
- **VARIANCE_RATIO_HIGH**：稳态段标准差 / 基线 `variance_ratio_baseline_std`
  > 2.0 → warn（离散度膨胀）。

## 4. 稳健 z 与马氏距离（C4）

- **稳健 z**：`0.6745·(x − median)/MAD > 3.5`（Gauss 比例：MAD/0.6745 ≈ σ，
  正态一致）。MAD=0 时回退 `sigma_overall`；两者皆无则跳过该参数（记录，不猜）。
- **马氏**：d2 = zᵀ R⁻¹ z，z_i = 0.6745(x_i − median_i)/MAD_i，R 为基线相关阵
  （仅稳态行估计），Cholesky 下三角 **预存于基线** → 在线每行仅一次前代
  （triangular forward-substitution，numpy 向量化），d2 = ‖L⁻¹z‖²。
  阈值 χ²(kept, q)，q 默认 0.999，用 **Wilson–Hilferty** 近似：
  `χ²_q(k) ≈ k·(1 − 2/(9k) + z_q·√(2/(9k)))³`（z_q = Φ⁻¹(q)，scipy.stats.norm）。
- **四级退化（按序，逐级留痕于报告）**：
  1. 相关阵条件数 > 1e10 或任一 |r| > 0.98 → 迭代剔除最高相关列并重建 Cholesky；
  2. 候选参数 > 30 → 取方差 top-20；
  3. 稳态行 < 50（或基线无 Cholesky/重建失败）→ 跳过马氏，仅稳健 z；
  4. NaN 行不插补，剔除并计入 `checks_summary.rows_skipped`。
- 建基线时即做一次同规则降级，保证存储的 `cholesky_lower` 可分解。

## 5. 防告警风暴三件套（冻结参数来自 enums sentinel.suppression）

| 机制 | 参数（默认） | 语义 |
|------|--------------|------|
| 同类抑制 | suppress_window_minutes = 60 | 同 key 触发在 60（行/分钟，见下）内合并 repeat_count+1；超窗=新 episode，重新告警 |
| 迟滞 | hysteresis_points = 5 | 持续告警条件需连续 5 点回带才降一级 severity（fast-screen 状态机） |
| 静默期 | post_changepoint_quiet_rows = 30 | 新变点后 30 行不出 SPC 告警并重估中心线 |

- **行/分钟对偶（冻结约定）**：watch 批内无状态，抑制窗按行数计（60 行 = 标称
  1 样本/分钟节奏下的 60 分钟）；fast-screen 跨运行用墙钟时间戳（state.suppression
  的 since）。gate S4 用同一行空间代理校验（60 行），因此哨兵按两判据中更严者
  分割 episode，保证 gate 永不误报。
- suppression_key = `group|check_type|rule_name|parameter/indicator`；
  变点类 key 额外携带 cp 位置（不同变点是不同事实）。
- repeat_count 记账：`suppression.applied` 存每 key 合计，gate S4 与 alerts[] 求和
  互查。

## 6. 冷启动（self 基线）

watch 无基线 → 用窗口内前 ≥100 稳态行/组自建基线（regime 过滤后取稳态行；
不足 100 → exit 2 拒跑）。self 基线：**跳过马氏**（样本太少，协方差结构不可信），
全部告警伴随 `SELF_BASELINE` 告警 + 48h TTL 固化提示
（`validity.self_baseline_ttl_hours = 48`，enums sentinel.baseline）。
fast-screen 无基线 → exit 2 直接拒跑（增量没有自建基线的统计条件）。

## 7. 误报率与 materiality 权衡（工程注记）

个体值图全规则组合的受控 ARL0 ≈ 90 点：1 万行纯噪声窗口期望约 100+ episode
（合并后约几十条告警）。三个治理层次：
1. 60 行同类抑制（把持续条件压成每窗一条）；
2. `r2/r3_materiality_z`（默认 0；调到 0.5 可消掉 |z|<0.5 的噪声 run，
   代价是 R2 检出延迟 ~0.5σ/slope 行）；
3. severity 语义分级让 info/warn 不触发应急动作。
基线 σ 与窗口噪声差距大时（新窗口明显更稳），R1/R5/R6 天然静默，
R2/R3 仍按符号率触发——这是教科书 Nelson 的固有属性，不是实现缺陷。
F1 fixture 用"交替抖动 + 设定值"形态给出确定性静默的稳态窗口。

## 8. fast-screen 与 state

- 环形缓冲 ≤300 行（fast_state.schema 硬顶），列 = 基线 global.numeric_columns
  （跨运行稳定）；每次增量 1–500 行，>500 或不可读 → exit 2。
- 快筛只做 C1（缓冲上）+ C4（最新行）+ 静默期/抑制/迟滞状态机；
  C2 投影与 C3 变点检测是 watch 的职责（缓冲太短，投影无时间轴无意义）——
  `projection_cache`/`known_change_points` 由 watch 侧维护、fast 侧消费。
- state 文件唯一写入者是 sentinel_fast.py（schema 声明 sole writer）；
  基线文件的 `state` 键恒为 null。

## 9. 零 LLM / 零网络

热路径（watch/fast_screen/build_baseline）仅 numpy/scipy/pandas + 标准库；
无 subprocess（detector 进程内 import）、无网络库、无 LLM 调用。
gate S5 对 Python 面做静态模式扫描（requests/urllib/httpx/socket/openai/...
及 URL 字面量），`provenance.zero_llm` 恒为 true（schema const）。
