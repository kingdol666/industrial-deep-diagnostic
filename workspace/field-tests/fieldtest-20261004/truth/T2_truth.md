# T2 真值（批改依据 — 测试者禁读）

生成器：`cases/_generators/gen_T2_sentinel.py`（seed 20261002）。
Examiner 已按 brief 的 7 步命令真实跑通全链（build → fast×3 → watch×2 →
gate×2），以下退出码与告警清单均为实测值。数据确定性生成，相同命令应
复现相同结果（alert_id 里的时间戳除外）。

## 0. 被测契约（先核对 tester 引用的语义是否正确）

- `sentinelcore._constants`：EXIT_OK=0（status=ok）、EXIT_FINDINGS=1（有
  warn/high/critical 告警）、EXIT_UNDETERMINED=2（无基线/输入不合规）、
  EXIT_GATE_FAIL=3（self-check 失败）。
- fast-screen 只做 C1（SPC，ring buffer）+ C4（robust z）；**C2 投影与
  C3 变点检测是 watch 模式专属**（sentinel_fast.py docstring 明示）。
- watch 的 C2 投影只对基线里 `operating_windows` 登记过的因子生效——
  该窗口来自 `build_baseline.py --doe-run-dir` 对 doe-analyzer 工件的
  逐字段搬运。doe_prior 给出 speed_rpm 窗口 **[1225.0, 1275.0]**、
  confirmation_needed=false。

## 1. 数据注入真值

- history.csv（720 行）与 window_normal.csv（240 行）：紧受控交替抖动
  （industrial-sentinel 自家 F1 参考夹具模式，确定性 SPC 静默），围绕
  工艺卡设定值（85.0 / 2.40 / 1250 / 42.0）。
- window_drift.csv（240 行）：speed_rpm 以 **+0.06 rpm/min** 线性爬升
  （末 25% 均值 ≈ 1262.6 rpm），其余 3 变量正常。设计意图：向 1275 窗口
  上界的投影 hours_to_edge ≈ 3.4 h（落 2–5 h 区间）。
- window_changepoint.csv（240 行）：temp_c 在数据行 idx 120 处阶跃
  **+3.2 degC**（= 4 倍工艺卡波动幅度），其余正常。
- window_orphan.csv（60 行）：正常数据，专用于"无基线"路径。
- 时间戳：纳秒分辨率 ISO（`2026-10-01 00:00:00.000000000` 格式）。

## 2. 期望的退出码矩阵（examiner 实测）

| 步骤 | 命令 | 期望退出码 | 期望 status |
|---|---|---|---|
| (1) 建档 | build_baseline.py --history-csv … --doe-run-dir … | **0** | 打印 `wrote … (groups: __ALL__)`；基线 `groups.__ALL__.operating_windows[0]` = `{factor: speed_rpm, range: [1225.0, 1275.0], confirmation_needed: false}`（逐字段来自 doe_prior） |
| (2) fast 正常窗 | sentinel_fast.py window_normal.csv | **0** | `status=ok`，alerts=0 |
| (3) fast 漂移窗 | sentinel_fast.py window_drift.csv | **1** | `status=alert`；告警只落在 speed_rpm：C4 ROBUST_Z_OUTLIER/high、C1 NELSON_R1/high、NELSON_R5/high、NELSON_R6/high、NELSON_R2/warn（合计 7 条） |
| (4) watch 变点窗 | sentinel.py watch window_changepoint.csv | **1** | `status=alert`，3 条告警：C3 **REGIME_CHANGE_NEW/warn**（evidence.cp_position ≈ 121）、C4 **ROBUST_Z_OUTLIER/high** on temp_c、C3 族 **VARIANCE_RATIO_HIGH/warn** on temp_c（ratio ≈ 34.8）；speed_rpm 的投影仅为 projection_summary 里的 info 级（slope ≈ -0.005/h，hours_to_edge ≈ 5228 h），不产生告警 |
| (5) watch 漂移窗 | sentinel.py watch window_drift.csv | **1** | `status=alert`，9 条告警，关键是 C2 **WINDOW_DRIFT_PROJECTION/high** on speed_rpm：`slope_per_hour ≈ 3.61`，`hours_to_edge ≈ 3.44`（**显著为正**，设计区间 2–5 h），`current ≈ 1262.58`，window [1225, 1275]，direction=up；另有 C1 R1/R5/R6 high、C4 ROBUST_Z high ×2、VARIANCE_RATIO_HIGH/warn（ratio ≈ 11.9）、NELSON_R2/warn |
| (6) 无基线 fast | sentinel_fast.py window_orphan.csv（--baseline 指向不存在文件） | **2** | stdout/stderr 原文：`[sentinel_fast] no baseline ([Errno 2] No such file or directory: '…watch_baseline.json') — refusing to run (exit 2)`；不写 fast_alert.json |
| (7) 门禁 ×2 | quality_gate.mjs（watch_drift、watch_cp 的 alert.json） | **0 ×2** | 6/6 checks ALL PASS |

## 3. 语义核对点（批改时逐条确认 tester 的解读）

1. 正常窗 → 0/无告警：符合 EXIT_OK 语义（不是"碰巧没告警"，数据是
   F1 式确定性静默模式）。
2. 漂移窗的 C2 语义：severity=high（hours_to_edge ≤ 8h 且窗口未越界、
   非 confirmation_needed）、urgency=same_shift、
   suggested_next_skill 指向窗口/工况侧（doe-analyzer）。tester 若只报
   "exit 1" 而漏报 C2/hours_to_edge，扣分。
3. 变点窗：+4σ 单参数阶跃由 **C4 robust z（high）+ C3 REGIME_CHANGE_NEW
   （warn，cp_position≈121）+ VARIANCE_RATIO_HIGH（warn）** 捕获；不要
   期望 temp_c 的 NELSON_R1——变点静默区与"稳态行"过滤使 C1 不在该参数上
   触发，这是脚本契约行为（z_mean 取多参数中位数，单参数尖峰由 R1/C4
   负责；本数据下 C1 在 temp 上无 episode）。tester 若断言"应该有 R1"
   属于契约误读。
4. 孤儿窗：exit 2 的契约语义 = undetermined/拒跑；恢复路径按 SKILL.md
   Failure Recovery："无基线（fast）→ exit 2 拒跑——先建基线"
   （build_baseline.py 建档后再筛）。
5. 门禁：两个 watch 产物必须 PASS（若 tester 报 FAIL，先核对其命令是否
   按 brief 传参）。

## 4. 环境发现（examiner 记录，非 tester 过错）

- 本仓库 venv 为 pandas 3.0.5：`_io.hours_axis` 对 ISO 字符串（解析为
  datetime64[us]）与 epoch 秒整数（解析后 astype('int64') 保留秒）都会
  产生 **1000×/1e9× 的小时轴单位误差**，使 slope_per_hour 虚大、
  hours_to_edge 虚小。本夹具用**纳秒分数位时间戳**（`…SS.000000000`）
  规避，使 hours_axis 返回正确小时数。若 tester 在报告中另用自造时间戳
  出现 hours_to_edge≈0.003 之类结果，属已知环境 bug，不算 tester 错误，
  但应作为发现记录。

## 5. 批改清单

- [ ] 7 个退出码逐字记录且与上表一致
- [ ] (3)(5) 告警清单含 parameter=speed_rpm 的 C1+C4 告警
- [ ] (5) 报出 C2 WINDOW_DRIFT_PROJECTION + hours_to_edge ≈ 3.44 h（±0.5 h
      容差）+ slope ≈ 3.6 rpm/h
- [ ] (4) 报出 REGIME_CHANGE_NEW（cp_position ≈ 121）与 ROBUST_Z_OUTLIER
      on temp_c
- [ ] (6) 报出完整 stderr 原文与"先建基线"的恢复语义
- [ ] (7) 两次 gate PASS
- [ ] 台账完整（每条命令 + 退出码）
