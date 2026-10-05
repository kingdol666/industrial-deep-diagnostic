# T1 结果报告 — data-preprocessor 目录模式（混合格式接驳箱）

## 执行命令

```bash
"$PY" "D:\codes\industrial-deep-diagnostic\.claude\skills\industrial-data-preprocessor\scripts\data_preprocessor.py" \
  --data-path cases/T1_preprocessor_mixed_inbox/inbox \
  --output results/T1 --name fieldtest_T1
```

退出码 **0**。stdout 摘要：`status=ok`，`tables_found=8`，`context_files=0`，`skipped_files=0`，
selected = `sensor_log.csv`（delimited，301×7，time=timestamp，score 5.701，why=highest table score），
report → `results/T1/preprocessing_report.json`。
运行中打印 1 条 UserWarning（`data_preprocessor.py:425`：to_datetime 无法推断格式、回退 dateutil 逐元素解析）。

## 一、逐文件格式识别（以 preprocessing_report.json `tables` 为准）

| 文件 | 识别格式 | 行×列 | 时间列 | score | 备注 |
|---|---|---|---|---|---|
| sensor_log.csv | delimited（逗号，ASCII） | 301×7 | timestamp | 5.701 | 被选为主表 |
| process_log.tsv | delimited（TAB） | 200×5 | process_time | 4.2 | |
| dcs_export_gbk.csv | delimited（逗号，**GBK 中文导出**） | 180×4 | 时间 | 3.48 | 列名 温度/压力/转速 解码正确 |
| heater_export.csv | delimited（**分号分隔**） | 90×4 | stamp | 3.39 | |
| batch_records.json | json | 120×5 | batch_time | 3.12 | JSON 数组 |
| downtime.html | html（HTML 表） | 25×5 | start_time | 2.525 | 脚本内置 regex HTML 表抽取器（`data_preprocessor.py:372`，不依赖 lxml） |
| qa_lab.xlsx | excel（sheet=`quality`） | 150×4 | （无） | 2.45 | 无时间列 |
| operator_notes.md | markdown（管道表） | 40×4 | shift_time | 1.84 | 表前有标题与说明文字，被正确跳过 |

8 个文件全部被识别为 table；没有文件被归为 context / skip / no_tabular / error。
注：`operator_notes.md` 含中文正文，本可作 context，但脚本只按"表"处理（判定为 table）。

## 二、数据质量问题排查（pandas 逐文件核对，位置=文件行号，1=表头）

### 重复时间戳 / 重复行
- **sensor_log.csv**：2026-09-28 10:30:00 出现 2 次 — 第 **152 行** 与第 **302 行**（末行）整行完全相同（temp_c=84.957, pressure_mpa=2.3922, speed_rpm=1260.64, flow_lpm=43.007, vibration_mms=2.934, motor_amp=34.88）。唯一重复对。
- process_log.tsv / batch_records.json / dcs_export_gbk.csv / heater_export.csv / downtime.html / operator_notes.md：重复时间戳 0、重复行 0。

### 缺失单元格（共 4 处）
- **batch_records.json**：1 处 — 记录 **B0058**（batch_time=2026-09-28T10:01:00）`moisture_pct=null`。
- **qa_lab.xlsx**（sheet quality）：3 处 — 第 39 行 `thickness_um`、第 90 行 `gloss_gu`、第 123 行 `tensile_mpa`（数据行 37/88/121）。
- 其余 6 个文件缺失单元格 0。

### 明显不可能的离群值（共 2 处，均在 dcs_export_gbk.csv）
- 第 **53 行**（08:51:00）：`温度=999.9`（正常范围 83-87）— 典型 DCS 坏值哨兵。
- 第 **123 行**（10:01:00）：`转速=-3.2`（转速不可能为负）。

## 三、统一视图 preprocessed_data.csv

- **301 行 × 18 列**，时间列 `batch_time`（合并键为 `timestamp`，输出时列名取自主表合并后的命名），范围 2026-09-28 08:00:00 → 12:59:00（1 分钟粒度）。表头带 UTF-8 BOM。
- **多表合并**：`merge.strategy=outer_merge_on_time_column`，note="sheets matched by time-axis overlap >=30%；values normalized to ISO before join"。
- **参与合并（4 个）**：sensor_log.csv、process_log.tsv、batch_records.json、dcs_export_gbk.csv（`merge.merged_files` 逐字）。
- **未参与（4 个）及原因**：
  - `heater_export.csv`：时间范围 2026-09-30 06:00–07:29，与主时间轴（09-28 08:00–12:59）零重叠 → 不满足 ≥30% 重叠；
  - `qa_lab.xlsx`：无时间列（report 中 time_column=null），无法上时间轴；
  - `downtime.html`：start_time 全部为 09-29，与主时间轴零重叠；
  - `operator_notes.md`：40 行、10 分钟粒度，可对齐时刻仅约 40/301 ≈ 13% < 30%。
  - 注：report **未逐文件给出排除原因**，以上后三条为依据 merge note 的 ≥30% 规则与各文件时间范围的推断；report 里只有 merged_files 白名单。
- **列构成**：record_id/batch_no/moisture_pct/viscosity_cp（batch_records.json）＋ 温度/压力/转速（dcs）＋ reactor_pv/jacket_sp/feed_rate_kgh/ph_value（process_log.tsv）＋ temp_c/pressure_mpa/speed_rpm/flow_lpm/vibration_mms/motor_amp（sensor_log.csv，唯一 301/301 满列）。

### 缺失率与成因
- 整体缺失 **27.41%**（report `quality.missing_cell_pct`；核验：1485/5418 = 27.41%，一致）。
- 逐列非空：温度/压力/转速 181/301（dcs 只覆盖 08:00–10:59 共 180 分钟）；reactor_pv 等 4 列 201/301（process_log 只覆盖 08:00–11:19）；record_id/batch_no 120/301、viscosity_cp 120/301、moisture_pct 119/301（batch_records 仅 120 条、2–3 分钟粒度）。
- **结构性稀疏（占绝大多数）**：上述缺口全部源于各源表的覆盖窗/采样粒度不同（传感器 1 分钟 × 全程，dcs 180 分钟窗，process_log 200 分钟窗，batch 120 条离散记录），合并到 1 分钟统一轴后必然稀疏 —— 是"多表合并的几何结果"，不是数据缺陷。
- **真实缺陷（4 处）**：moisture_pct 在 10:01 行的 null（源自 B0058 的 null）；sensor_log 10:30 重复行导致统一视图 **batch_time=10:30:00 出现 2 行（第 152/153 行）未被去重**；999.9 与 -3.2 两个坏值**原样透传**进统一视图（report 的 quality 段未做离群值标记，note 只声明 missing cells 留 NaN 交给下游）。

## 四、观测到的文档/CLI 粗糙点

1. `preprocessing_report.json` 中 `selected_table.n_cols=18`（合并后视图的列数）而 `tables[]` 里 sensor_log.csv 的 `n_cols=7`（原始表）— 同名字段两种语义，易误读。
2. stdout 摘要与 report 不一致：stdout 说 sensor_log.csv `n_cols: 18`，report tables 说 7 — 实为合并视图 vs 原始表，未标注。
3. 未合并文件的排除原因未写入 report（只有 merged_files 列表 + 一句 ≥30% 规则）。
4. `results/T1/context/` 目录被创建但 `context_files=[]` 为空目录。
5. 运行时 pandas UserWarning（data_preprocessor.py:425）无碍结果但暴露时间解析未指定 format。

## 产物清单

- results/T1/preprocessing_report.json（技能输出）
- results/T1/preprocessed_data.csv / preprocessed_data.json（统一视图）
- results/T1/qa_audit.py、qa_audit_part2.py（自查脚本）+ 本次运行输出
- results/T1/commands.log（逐条命令台账）
