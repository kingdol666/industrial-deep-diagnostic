# T2 任务简报 — 产线常驻监控（industrial-sentinel）

## 场景

L7 产线（产品 PVC-M）有一段 720 分钟的历史数据。产线此前做过一次线速
操作窗口的 DOE 研究，结论放在 `cases/T2_sentinel_stream/doe_prior/`（标准
doe-analyzer 产物布局，`conclusions/recommendations.json` 里带操作窗口）。
现在要在哨兵系统里建档，并对最近到达的几个数据窗口做巡检与增量快筛。

窗口数据的时间戳是 DCS 高分辨率导出格式（纳秒分辨率，形如
`2026-10-01 00:00:00.000000000`）。产线工艺卡（健康状态基准，供理解数据用）：

| 变量 | 设定值 | 正常波动幅度 |
|---|---|---|
| temp_c | 85.0 degC | ±0.08 |
| pressure_mpa | 2.40 MPa | ±0.005 |
| speed_rpm | 1250 rpm | ±0.6 |
| flow_lpm | 42.0 L/min | ±0.12 |

## 输入（只读）

- `cases/T2_sentinel_stream/history.csv`（720 行历史）
- `cases/T2_sentinel_stream/doe_prior/`（DOE 先验：操作窗口研究产物）
- `cases/T2_sentinel_stream/window_normal.csv`（240 行）
- `cases/T2_sentinel_stream/window_drift.csv`（240 行）
- `cases/T2_sentinel_stream/window_changepoint.csv`（240 行）
- `cases/T2_sentinel_stream/window_orphan.csv`（60 行）

## 环境（已验证的入口）

- 工作目录：`workspace/field-tests/fieldtest-20261004/`
- venv Python：
  `D:\codes\industrial-deep-diagnostic\.claude\shared\scripts\.venv\Scripts\python.exe`
  （下称 `$PY`）
- Sentinel 脚本目录：
  `D:\codes\industrial-deep-diagnostic\.claude\skills\industrial-sentinel\scripts\`
  - `build_baseline.py`：`--history-csv`（必填）、`--doe-run-dir`（可选，
    逐字段搬运其中的 recommendations/stability 工件）、`--out`
  - `sentinel.py`：子命令 `watch`，参数 `--data --baseline --out-dir`
  - `sentinel_fast.py`：参数 `--data --state --baseline --out`（`--baseline`
    与 `--state` 为必填项）
  - `quality_gate.mjs`：`node quality_gate.mjs <alert.json> --baseline
    <watch_baseline.json> --skill-path <skill目录> --shared-path
    <D:\codes\industrial-deep-diagnostic\.claude\shared>`

## 要求（输出统一放 `results/T2/`，每条命令与退出码记入
`results/T2/commands.log`）

1. **建档**：用 `build_baseline.py` 从 `history.csv` 建基线，注册 DOE 先验
   （传 `--doe-run-dir cases/T2_sentinel_stream/doe_prior`），
   `--out results/T2/baseline/watch_baseline.json`。

2. **快筛正常窗**：`sentinel_fast.py`，`--data window_normal.csv`，
   `--state results/T2/screen_normal/fast_state.json`，
   `--baseline results/T2/baseline/watch_baseline.json`，
   `--out results/T2/screen_normal/fast_alert.json`。

3. **快筛漂移窗**：同上，但 state 与 out 放 `results/T2/screen_drift/`，
   `--data window_drift.csv`。

4. **批筛变点窗**：`sentinel.py watch`，`--data window_changepoint.csv`，
   `--baseline results/T2/baseline/watch_baseline.json`，
   `--out-dir results/T2/watch_changepoint`。

5. **批筛漂移窗**：`sentinel.py watch`，`--data window_drift.csv`，
   `--baseline results/T2/baseline/watch_baseline.json`，
   `--out-dir results/T2/watch_drift`。

6. **无基线快筛**：`sentinel_fast.py`，`--data window_orphan.csv`，state 与
   out 放 `results/T2/orphan_out/`；**不提供任何已存在的基线文件**（--baseline
   指向一个不存在的路径，例如 `results/T2/orphan_out/watch_baseline.json`）。

7. **门禁**：对第 4、5 步产出的 `alert.json` 各跑一次 `quality_gate.mjs`。

8. 写中文报告 `results/T2/T2_report.md`：
   - 每一步的**退出码逐字记录**（0/1/2/3，按实际打印，不要翻译或修饰）；
   - 每个 `alert.json`（含 fast 与 watch）里的**告警清单**：check_type、
     rule_name、parameter、severity、关键 evidence（如 hours_to_edge、
     slope_per_hour、cp_position、ratio）；
   - 第 6 步的完整 stderr/stdout 文本与退出码，以及按 sentinel 契约该退出码
     的语义和恢复路径（查 SKILL.md / 脚本 docstring，引用原文）；
   - 第 4/5 步 watch 产物里的 `projection_summary`（如有）逐字段转述。

不得手改任何脚本产出的 JSON 数值；所有数字必须来自命令产物。
