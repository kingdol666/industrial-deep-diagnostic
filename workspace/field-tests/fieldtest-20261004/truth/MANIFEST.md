# MANIFEST — fieldtest-20261004 测试资产清单（出题人维护）

生成日期：2026-10-04。全部数据由 `cases/_generators/` 下脚本确定性生成
（固定 seed），并经出题人按 brief 逐条真实 CLI 验证（dry-run，产物已销毁）。
行数纪律：所有数据文件 ≤500 行；T4 预算 ≤6 轮（实测 3 轮收敛）。

## cases/（测试者可见）

| 文件 | 用途 |
|---|---|
| `T1_preprocessor_mixed_inbox/brief.md` | T1 任务简报（不含真值）：data-preprocessor 目录模式 |
| `T1_preprocessor_mixed_inbox/inbox/sensor_log.csv` | 批次1：300 行 UTF-8 传感器 CSV（含 1 条重复行） |
| `T1_preprocessor_mixed_inbox/inbox/qa_lab.xlsx` | 批次1：150 行质检 Excel（sheet=quality，3 个缺失格） |
| `T1_preprocessor_mixed_inbox/inbox/batch_records.json` | 批次2：120 条 JSON 记录（1 个 null） |
| `T1_preprocessor_mixed_inbox/inbox/process_log.tsv` | 批次2：200 行 TAB 分隔（干净） |
| `T1_preprocessor_mixed_inbox/inbox/operator_notes.md` | 批次3：Markdown 管道表 40 行 + 散文 |
| `T1_preprocessor_mixed_inbox/inbox/downtime.html` | 批次3：HTML 表 25 行 |
| `T1_preprocessor_mixed_inbox/inbox/dcs_export_gbk.csv` | 批次3：GBK 中文 DCS 导出 180 行（2 个离群值） |
| `T1_preprocessor_mixed_inbox/inbox/heater_export.csv` | 批次3：分号分隔 90 行 |
| `T2_sentinel_stream/brief.md` | T2 任务简报（不含真值）：sentinel 建档/快筛/批筛/无基线 |
| `T2_sentinel_stream/history.csv` | 720 行历史（紧受控交替抖动，工艺卡设定值） |
| `T2_sentinel_stream/window_normal.csv` | 240 行正常窗 |
| `T2_sentinel_stream/window_drift.csv` | 240 行漂移窗（speed_rpm +0.06 rpm/min） |
| `T2_sentinel_stream/window_changepoint.csv` | 240 行阶跃窗（temp_c +3.2 @行120） |
| `T2_sentinel_stream/window_orphan.csv` | 60 行（无基线路径专用） |
| `T2_sentinel_stream/doe_prior/conclusions/recommendations.json` | DOE 先验（speed_rpm 操作窗 [1225,1275]，build_baseline 逐字段搬运） |
| `T2_sentinel_stream/doe_prior/02_analysis/stability_report.json` | DOE 先验稳定性工件（无变点） |
| `T3_tuning_memory/brief.md` | T3 任务简报（不含真值）：归因→入库→检索→佐证 |
| `T3_tuning_memory/data.csv` | 200 行时序（行100 温度-8℃且 yield +2σ；行150 压力+0.2；行197 速度+5 且数据即止） |
| `T3_tuning_memory/action_log.json` | 3 条动作日志（action_log schema v1.0，trigger=manual） |
| `T3_tuning_memory/fault_signature.json` | 故障签名（temp_c/speed_rpm high，PVC-M\|calender-03\|night_shift） |
| `T3_tuning_memory/playbook_seed/tuning_experience.jsonl` | 2 条种子经验（S1 命中配方 + S2 干扰项，标准信封字段） |
| `T4_optimizer_plant/brief.md` | T4 任务简报（不含真值；objective JSON 内联） |
| `T4_optimizer_plant/objective.json` | 目标契约（OPT-20261004-001，minimize impurity，tolerance 0.55，≤6 轮/24 点） |
| `T4_optimizer_plant/plant_sim.py` | 确定性 2 因子黑箱产线（trial_design.json → trial_result.json 契约；参数对测试者保密使用） |
| `T5_doe_designed/brief.md` | T5 任务简报（不含真值）：designed 模式全链 |
| `T5_doe_designed/doe_table.csv` | 2^3 全因子 + 4 中心点 = 12 行（随机 run order） |
| `T5_doe_designed/analysis_context.json` | 分析上下文（designed 模式、响应/因子角色、α=0.05） |

## cases/_generators/（测试资产的一部分）

| 文件 | 用途 |
|---|---|
| `gen_T1_inbox.py` | T1 数据生成器（seed 20261001，注入缺陷见 truth/T1_truth.md §1） |
| `gen_T2_sentinel.py` | T2 数据生成器（seed 20261002；含 ns 分数位时间戳说明） |
| `gen_T3_tuning.py` | T3 数据生成器（seed 20261003；含 experience_build 同构 sha16/chunk_id 派生） |
| `gen_T5_doe.py` | T5 数据生成器（seed 20261005） |
| （T4 无生成器） | plant_sim.py 本身即确定性资产（seed 42 置于文件内） |

## truth/（测试者禁读）

| 文件 | 用途 |
|---|---|
| `T1_truth.md` | 逐文件格式/行数/编码/分隔符真值 + 注入缺陷位置 + 预处理预期行为 + 批改清单 |
| `T2_truth.md` | 退出码矩阵 + 期望告警清单（含 C2 hours_to_edge≈3.44h）+ 契约语义 + pandas 3.0 hours_axis 单位 bug 记录 + 批改清单 |
| `T3_truth.md` | 3 条动作的归因真值（estimable/estimable+CI跨0/not_estimable）+ 入库/检索/回填/门禁实测值 + 批改清单 |
| `T4_truth.json` | 黑箱产线真值（T*=78.5, C*=0.42, impurity_min 0.35）+ 双门槛语义 + 实测 3 轮收敛轨迹 + 批改要点 |
| `T5_truth.json` | 注入效应真值（A +4.2 / B −3.1 / C 0 / A×B +1.8 / σ0.4）+ 显著性期望 + 实测系数与 q 值 + 批改要点 |
| `MANIFEST.md` | 本清单 |

## 其余（运行期产生，当前不存在）

- `results/T1..T5/` — 测试者产物（结果 + 命令台账），由测试者按 brief 创建
- `scorecard.md` — 批改人成绩单

## 出题人验证记录（CLI surface 核验结论）

- `data_preprocessor.py`：`--data-path/--output/--name`，目录模式实测
  status=ok（301×18 合并视图）。
- `build_baseline.py`：`--history-csv/--doe-run-dir/--out/…`，exit 0/2。
- `sentinel.py watch`：`--data/--baseline/--out-dir`（产物写在
  `<out-dir>/alert.json`+`watch_report.md`；仅 `--run-dir` 用法才带
  `sentinel/` 子目录）。
- `sentinel_fast.py`：`--data/--state/--baseline/--out`（state/baseline
  必填；无基线 → exit 2）。
- `tune_stats.py attribute`：子命令式，`--settle-steps` 显式传 30。
- `experience_build.mjs build|feedback`、`match_playbook.mjs recommend`：
  参数为松散 `--key value` 解析；feedback 的 result 枚举
  effective|ineffective|harmful|confirmed。
- `optimizer.py init|design|ingest|status|converge`：`--run-dir` +
  `init --objective`；ingest 缺省取当前轮 trial_result.json。
- `analyze.py profile|run|report|all`：`--run-dir`（+可选 `--data/--context`）。
- 各 skill 的 quality_gate.mjs / optimizer_gate.mjs 用法见 brief，
  实测分别 6/6（sentinel×2）、8/8（tuning-memory）、16/16（optimizer）、
  21/21（doe-analyzer）ALL PASS。
