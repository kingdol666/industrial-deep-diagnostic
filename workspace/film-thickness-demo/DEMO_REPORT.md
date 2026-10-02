# 薄膜厚度 MD/TD 数据 — IDD 体系演示报告

- 工作目录：`workspace/film-thickness-demo/`
- 随机种子：`seed=7`（数据生成、全部统计均确定性可复现）
- 运行日期：2026-10-01
- 演示链路：**造数据 → 滞后反推对齐 → industrial-sentinel 快速筛查 → industrial-doe-analyzer 成因统计甄别 → 集成联动验证**

---

## 1. 数据构成

### 1.1 工艺参数表 `process.csv`（2400 行，1 分钟/行，2026-09-30T00:00 起 ≈40h）

| 列 | 基线 | 噪声 σ | 植入事件（工艺时刻） |
|----|------|--------|----------------------|
| `die_bolt_T3_pct` | 50.0 | 0.25 | **T1**：第 800 分钟起线性缓升 +6.0 pct（模拟该区积料/螺栓松动），至 2399 分钟升满 |
| `melt_temp_C` | 285.0 | 0.15 | **T2**：第 1400 分钟起线性缓升 +2.5 °C（加热失控） |
| `lip_gap_mm` | 0.850 | 0.0006 | **T3**：第 1900 分钟阶跃 −0.02 mm（人工调模） |
| `pull_speed_mpm` | 120.0 | 0.20 | — |
| `pump_rpm` | 25.0 | 0.12 | — |

### 1.2 测厚扫描表 `thickness_scans.csv`（1200 行 × 21 幅宽位置 `pos_01..pos_21`，μm，2 分钟/次）

- 基线剖面：目标 50 μm + 抛物线边缘减薄（边缘 −1.2 μm，`50 − 1.2·((j−11)/10)²`）+ 噪声 σ=0.15
- 植入（工艺→膜厚滞后 5 min，均为**膜厚显现时刻**）：
  1. 第 **805** 分钟起 pos_07 条纹：+2.5 μm 用 400 分钟渐增后进入平台（积料生长后趋稳）；
  2. 第 **1405** 分钟起全幅均值线性缓降至 −0.8 μm（至换班末）；
  3. 第 **1905** 分钟起 pos_06/07/08（pos_07±1）阶跃 −1.5 μm（调模直接效果）。

### 1.3 对齐产物 `aligned.csv`（1200 行）

`timestamp, mean_thk, td_std, zone_L, zone_C, zone_R, dev_pos07, die_bolt_T3_pct, melt_temp_C, pull_speed_mpm, lip_gap_mm`
- `zone_L/C/R` = pos_01-07 / 08-14 / 15-21 分区均值；`dev_pos07 = pos_07 − (pos_06+pos_08)/2`（邻域取 ±1 位置，故 T3 的三位置同降在 dev 中自然抵消——这是"条纹检测量应免于调模阶跃污染"的设计点）
- 真值行号（扫描行，2 min/行）：**T1→403，T2→703，T3→953**

## 2. 检测点采样时刻反推对齐（`01_align.py`）

- 方法：扫描时间戳 t → 目标工艺时刻 **t−5 min** → `pandas.merge_asof(direction='nearest')` 就近匹配工艺行（无容差钳位）。
- 结果：1200/1200 行对齐成功，回溯间隔中位数 = 5.0 min（与设计一致）；仅开头 3 行（扫描 0/2/4 分钟）反推越过工艺起点，钳位到首条工艺行（产线开车的物理边界，报告中如实披露）。
- 若不反推（直接对齐 t 时刻工艺），条纹/均值漂移会与工艺变化错位 2.5 行，滞后 CCF 峰将偏移——反推是本演示 lag-compensated CCF 命中的前提。

## 3. 厚度云图

`03_figures/thickness_cloud.png`（matplotlib pcolormesh，x=时间 h，y=位置 1..21，色=厚度；三条白色竖虚线标注 T1/T2/T3（含 +5 min 滞后），白色横点线标注条纹位置 pos_07；全英文标注避免字体缺字）。图中可见：13.4h 起 pos_07 红色条纹、23.4h 起全幅变暗（MD 漂移）、31.8h 起 pos_06-08 阶跃变暗。

## 4. industrial-sentinel 快速筛查（任务二）

### 4.1 实际命令

```bash
# 历史基线 = aligned.csv 前 400 行（纯稳态段）
uv run --project .claude/shared/scripts python \
  .claude/skills/industrial-sentinel/scripts/build_baseline.py \
  --history-csv workspace/film-thickness-demo/sentinel_history.csv \
  --time-col timestamp \
  --parameters zone_L,zone_R,dev_pos07,mean_thk \
  --indicators td_std \
  --out workspace/film-thickness-demo/watch_baseline.json

# watch 全量 1200 行
uv run --project .claude/shared/scripts python \
  .claude/skills/industrial-sentinel/scripts/sentinel.py watch \
  --data workspace/film-thickness-demo/aligned.csv \
  --baseline workspace/film-thickness-demo/watch_baseline.json \
  --time-col timestamp \
  --out-dir workspace/film-thickness-demo/sentinel-out

# 质量门
node .claude/skills/industrial-sentinel/scripts/quality_gate.mjs \
  workspace/film-thickness-demo/sentinel-out/alert.json \
  --baseline workspace/film-thickness-demo/watch_baseline.json \
  --skill-path .claude/skills/industrial-sentinel --shared-path .claude/shared
```

结果：**status=alert，89 条告警，exit=1（findings），质量门 6/6 PASS**，耗时 23 ms（零 LLM/零网络）。产物：`sentinel-out/alert.json`、`sentinel-out/watch_report.md`（中文巡检报告）。

> 注：`--indicators td_std` 被接受，但该列在无 `--doe-run-dir` 时不会写入基线 indicators（`build_baseline.py` 的 indicators 仅从 doe `response_specs` 逐值搬运），故本轮 td_std 未产生规格类告警——属契约内行为，非失败。

### 4.2 告警 vs 真值（±200 行容差）

| 真值事件（行号） | 期望规则 | 实际触发（规则 / 参数 / 行号 / Δ行） | 判定 |
|---|---|---|---|
| **T1 条纹起点（403）** | REGIME_CHANGE_NEW 或 ROBUST_Z_OUTLIER（dev_pos07） | REGIME_CHANGE_NEW @420（+17）；NELSON_R1 dev_pos07 @451（+48）；**ROBUST_Z_OUTLIER dev_pos07 @464（+61，rep=6 持续段）**；同事件附近另有变点 477/547 | **命中** |
| **T2 MD 漂移起点（703）** | NELSON_R2/R3 或窗口投影（mean_thk） | **NELSON_R3 mean_thk @707（+4，漂移起始的单调连降）**；REGIME_CHANGE_NEW @732（+29）；ROBUST_Z_OUTLIER mean_thk @868（+165，rep=7）；R2/R1 尾段 @822/1104/1097 | **命中**（本轮无 doe 操作窗，投影通道按预期未启用，由 R3/C3/C4 兜住） |
| **T3 调模阶跃（953）** | （附加真值）阶跃类检出 | **REGIME_CHANGE_NEW @953（Δ=0，精确命中）**；NELSON_R2 zone_L @944（−9）；NELSON_R5 zone_L @939（−14） | **命中** |

- 11 个新变点全部落在三个真值事件 ±200 行内（420/477/547→T1；732/771/831/860→T2；905/953/1005/1066→T3），长坡道被分段器拆成多个变点属正常行为。
- VARIANCE_RATIO_HIGH dev_pos07（1.196×）→ 条纹推高稳态段离散度，辅助命中。

### 4.3 假阳说明（如实报告）

- 89 条中 22 条位于纯基线区（行号<403）：规则为教科书 Nelson 默认（`r2/r3_materiality_z=0`），iid 噪声下 4 参数×1200 行的 R1/R2/R3/R5/R6 噪声底。SKILL.md 的既定处置是调 materiality 而非逐条解释；演示保持默认以展示真实噪声底。
- 其余约 7 条为漂移中后段同 key 链式合并的迟触发片段（如 dev_pos07 平台期 R3 @823）。60/89 条告警位置落在某真值事件 ±200 行内。

### 4.4 集成联动验证（加分项）：doe 产物回灌 sentinel

```bash
build_baseline.py --history-csv sentinel_history.csv \
  --parameters zone_L,zone_R,dev_pos07,mean_thk,die_bolt_T3_pct,melt_temp_C \
  --doe-run-dir workspace/film-thickness-demo/doe-run \
  --out watch_baseline_integrated.json
sentinel.py watch --data aligned.csv --baseline watch_baseline_integrated.json \
  --time-col timestamp --out-dir sentinel-out-integrated
```

- doe 的 `operating_windows`（3 条）+ `response_specs` + 稳定性变点**逐值搬运**入基线（AC A7）。
- C2 窗口投影通道激活：`die_bolt_T3_pct` 当前 54.95 vs 窗口 [50.47, 52.40]、`melt_temp_C` 当前 286.8 vs [284.82, 285.22] → 双双 **WINDOW_OUT_OF_RANGE（warn+advisory）**——与 T1/T2 植入真值一致（confirmation_needed=true 按契约封顶 warn）。
- REGIME_CHANGE_NEW 由 11→7：doe 稳定性变点成为已知变点后被按设计抑制。质量门 6/6 PASS。
- **修复了一个真实潜伏 bug**：`sentinel.py` 的 C2 通道在基线携带 doe 操作窗时首次被执行路径覆盖，`projection.alert_fields()` 缺 `level` 实参直接 TypeError（官方测试未覆盖"有操作窗"场景）。已按最小修复改为 `alert_fields(level)`（该形参本就未使用），修复后 sentinel 技能测试 **55/55 ALL GREEN**，两次 watch 的质量门均 PASS。改动仅 1 行：`.claude/skills/industrial-sentinel/scripts/sentinel.py:357`。

## 5. industrial-doe-analyzer 观测档分析（任务三）

### 5.1 实际命令

```bash
# 00_input/aligned.csv + 00_input/analysis_context.json（mode_override=observational,
# responses=[dev_pos07 target 0, mean_thk maximize 50], factors=4 个工艺列, time_col=timestamp）
uv run --project .claude/shared/scripts python \
  .claude/skills/industrial-doe-analyzer/scripts/analyze.py all \
  --run-dir workspace/film-thickness-demo/doe-run
```

结果：`mode=observational`，3 操作窗 + 1 确认项 + 5 图，grade=B，exit=0。关键产物：`doe-run/02_analysis/correlation_report.json`（8 配对）、`stability_report.json`、`conclusions/recommendations.json`、`report.html`。

### 5.2 相关甄别 vs 真值（`correlation_report.json` 8 配对全表）

| 响应 | 因子 | r | q(BH) | best_lag(行) | 去趋势 r | ΔR² | 防伪判定 | 对照真值 |
|------|------|---|-------|----------|---------|-----|----------|----------|
| **dev_pos07** | **die_bolt_T3_pct** | **+0.838** | ≈0 | +20（窗内一致） | −0.069 | 0.498 | **CAUTION**（共享时间趋势混杂） | **真值驱动 ✓ 显著且 PASS/CAUTION 达标** |
| dev_pos07 | melt_temp_C | +0.585 | ≈0 | +20 | −0.576 | 0.061 | CAUTION（时间趋势） | 假耦合被降级 ✓ |
| dev_pos07 | pull_speed_mpm | −0.055 | 0.058 | −2 | −0.043 | 0.000 | PASS | 无关 ✓ |
| dev_pos07 | lip_gap_mm | −0.457 | ≈0 | +20 | +0.503 | 0.004 | FAIL（离群驱动+趋势混杂） | 单一阶跃事件驱动被识别 ✓ |
| mean_thk | die_bolt_T3_pct | −0.822 | ≈0 | −20 | −0.617 | 0.004 | CAUTION | 交叉耦合（经 T1→条纹影响均值? 实为共趋势）被审慎降级 ✓ |
| **mean_thk** | **melt_temp_C** | **−0.953** | ≈0 | −17 | **−0.910（去趋势后仍强）** | 0.053 | **PASS（L3）** | **真值驱动 ✓ 显著且最干净** |
| mean_thk | pull_speed_mpm | −0.013 | 0.65 | −19 | −0.061 | 0.000 | CAUTION | 无关 ✓ |
| mean_thk | lip_gap_mm | +0.940 | ≈0 | 0 | +0.878 | 0.042 | FAIL（离群驱动） | 真实效应（T3 阶跃）但为单事件高杠杆，判 FAIL 提示"勿当稳态关系引用"，语义正确 ✓ |

要点：
- 两条**真值驱动**配对全部显著（q≈0），且防伪判定均落在任务期望的 PASS/CAUTION 区间：`dev_pos07↔die_bolt_T3_pct` CAUTION（二者同随时间爬升，共享趋势被如实标出——单次观测运行的本质限制）；`mean_thk↔melt_temp_C` PASS 且去趋势后 r=−0.910，是全表最强的干净信号。
- 防伪层的行为与植入设计逐条对应：melt_temp 与条纹的假耦合→CAUTION；pull_speed 无辜→PASS/不显著；lip_gap 的真实但单事件效应→FAIL（离群/高杠杆识别）。总体有效性 `SERIOUS_CONCERNS`（4 serious + 3 moderate）——观测档证据等级 B 与"需确认试验后才能下发"的下游使用卡一致，未被越过。

## 6. 产物清单

| 文件 | 说明 |
|------|------|
| `workspace/film-thickness-demo/process.csv` | 工艺参数 2400 行（植入 T1/T2/T3） |
| `workspace/film-thickness-demo/thickness_scans.csv` | 21 位置测厚扫描 1200 行 |
| `workspace/film-thickness-demo/01_align.py` | 5 min 滞后反推对齐脚本 |
| `workspace/film-thickness-demo/00_generate_data.py` / `02_plot_cloud.py` | 造数 / 云图脚本 |
| `workspace/film-thickness-demo/aligned.csv` | 对齐产物（sentinel 与 doe 的共同输入） |
| `workspace/film-thickness-demo/03_figures/thickness_cloud.png` | 厚度云图（TD×时间+真值标注） |
| `workspace/film-thickness-demo/watch_baseline.json` / `watch_baseline_integrated.json` | sentinel 基线 / doe 回灌集成基线 |
| `workspace/film-thickness-demo/sentinel-out/{alert.json,watch_report.md}` | watch 主结果（89 告警，gate 6/6） |
| `workspace/film-thickness-demo/sentinel-out-integrated/{alert.json,watch_report.md}` | 集成联动结果（141 告警，含 2 条 WINDOW_OUT_OF_RANGE） |
| `workspace/film-thickness-demo/doe-run/` | doe-analyzer 完整 run（profile/analysis/conclusions/report.html） |

## 7. 结论（可行性判定）

1. **可行，且分层协作成立**：确定性造数（seed=7）→ 5 min 滞后反推对齐 → sentinel 快速筛查在 ±200 行容差下 **3/3 真值事件全部命中**（条纹=稳健 z@+61 行、MD 漂移=NELSON_R3@+4 行、调模阶跃=REGIME_CHANGE_NEW@0 行），doe-analyzer 观测档把两条真值因果（`dev_pos07↔die_bolt_T3_pct` CAUTION、`mean_thk↔melt_temp_C` PASS）从 8 个候选配对中显著甄别出，同时把假耦合与单事件高杠杆如实降级——"筛查定位、统计定因"的分工与 IDD 架构一致。
2. **工程成本极低**：两技能均为零 LLM/零网络确定性脚本（watch 23 ms / 1200 行），CLI 与文档一致，唯一需要适配处是 sentinel C2 通道的一个潜伏 TypeError（已最小修复并通过 55/55 技能测试与 6/6 质量门）；doe 产物可逐值回灌 sentinel 基线，形成"操作窗投影→越窗告警"的跨技能闭环。
3. **限制如实**：教科书 Nelson 默认阈值在洁净基线上有 ~22 条噪声假阳（SKILL 预期行为，应收 materiality 而非逐条解释）；单次观测运行使真值配对只能到 CAUTION/L4，需确认试验才能升级——这正是 doe-analyzer `confirmations` 契约的设计用途。
