# T1 真值（批改依据 — 测试者禁读）

生成器：`cases/_generators/gen_T1_inbox.py`（numpy seed 20261001）。
 Examiner 已按 brief 的命令真实执行过一遍 data_preprocessor（exit 0），
 以下数值全部来自该次运行与生成器注入记录。

## 1. 逐文件真值（行数=数据行，不含表头）

| # | 文件 | 格式/编码 | 分隔符 | 数据行数 | 列 | 注入的缺陷（出题人故意埋入） |
|---|------|-----------|--------|---------|----|------------------------------|
| 1 | sensor_log.csv | UTF-8 文本 CSV | 逗号 | 300 | 7（timestamp + 6 数值列） | **1 条完全重复行**：数据行 idx 150 与 idx 299（文件末行）逐字节相同，时间戳 `2026-09-28 10:30:00` 重复出现 2 次（即重复时间戳对） |
| 2 | qa_lab.xlsx | xlsx（openpyxl 可读），工作表名 `quality` | — | 150 | 4（sample_id, thickness_um, gloss_gu, tensile_mpa） | **3 个缺失单元格**：thickness_um @数据行 idx 37、gloss_gu @idx 88、tensile_mpa @idx 121（0 基） |
| 3 | batch_records.json | JSON 记录数组（120 个对象） | — | 120 | 5 | **1 个空值**：record_id=`B0058`（数组 idx 57）的 `moisture_pct` = null |
| 4 | process_log.tsv | UTF-8 文本 | TAB | 200 | 5 | 无缺陷 |
| 5 | operator_notes.md | Markdown（含 1 张管道表 + 前后散文） | 管道 | 表 40 行 | 4 | 无缺陷（散文部分非表格） |
| 6 | downtime.html | HTML `<table>`（UTF-8，含中文） | — | 表 25 行 | 5 | 无缺陷 |
| 7 | dcs_export_gbk.csv | **GBK** 编码（utf-8 解码必失败，gb18030 兼容），中文列名 时间/温度/压力/转速 | 逗号 | 180 | 4 | **2 个离群值**：`温度`=999.9 @数据行 idx 51（正常 ~85）；`转速`=-3.2 @idx 121（正常 ~1250，物理不可能的负值） |
| 8 | heater_export.csv | UTF-8 文本 | **分号 `;`** | 90 | 4 | 无缺陷 |

时间栅格：sensor/process/dcs 三表共用 `2026-09-28 08:00:00` 起、1 分钟一格
的时间轴（300 个唯一时刻 08:00–12:59）；batch_records 为 2 分钟格（08:07 起）。

## 2. data-preprocessor（目录模式）预期行为（examiner 实测）

- 退出码 0，`status=ok`；识别出 **8 张候选表**，无 skip、无 context 文件、
  无 no_tabular。
- **合并**：`merge.strategy = outer_merge_on_time_column`，参与文件 =
  `batch_records.json + dcs_export_gbk.csv + process_log.tsv + sensor_log.csv`
  （≥100 行且时间轴重叠 ≥30% 的全部候选）。实际 join 键 = `batch_time`
  （合并基表是候选顺序里的第一个 ≥100 行文件 batch_records；report 里
  `merge.key` 写的是 primary 的时间列名 `timestamp`——两处不一致是脚本
  已知的展示细节，批改时以 merged_files 与最终行数为准）。
- **统一视图**：`preprocessed_data.csv` = 301 行 × 18 列，时间列
  `batch_time`，`selected_table.file = sensor_log.csv`，why =
  `highest table score`。301 行 = 300 个唯一时刻 + 1 行（sensor_log 的重复
  时间戳 10:30:00 在 join 时扩展成 2 行）。
- **未参与合并**：qa_lab.xlsx（无时间列）、operator_notes.md（40 行）、
  downtime.html（25 行）、heater_export.csv（90 行）——后三者低于 100 行
  合并门槛。
- **quality 块**：`missing_cell_pct = 27.41`、rows=301、cols=18。这个缺失
  率是**结构性稀疏**（batch/dcs/process 的列只覆盖各自时间段），不是数据
  缺陷；批改时要与第 1 节注入的 4 处真实缺陷区分开。
- 源文件必须保持只读：批改时校验 inbox 下 8 个文件的 mtime/内容未被改动
  （可用 sha256 对比生成器重跑结果）。

## 3. 批改清单（tester 报告必须命中）

1. sensor_log.csv：重复行/重复时间戳 `2026-09-28 10:30:00`（给出行位置或
   时间戳均可）。
2. qa_lab.xlsx：3 个缺失单元格（给出列名与行号；行号 1 基/0 基均可接受，
   需自洽）。
3. batch_records.json：1 个空值（moisture_pct，B0058）。
4. dcs_export_gbk.csv：GBK 编码判定 + 2 个离群值（温度 999.9、转速 -3.2，
   含位置）。
5. heater_export.csv：分号分隔判定。
6. 逐文件行数与上表一致（40/25 行两表允许表述为"表 40/25 行"）。
7. 统一视图：301×18、键=时间列、参与合并的 4 个文件、结构性稀疏 27.41%
   的正确归因。
8. 全部结论来自 preprocessing_report.json / 对源文件的脚本化检查；台账
   包含命令与退出码。
