# T1_result.md — data-preprocessor 目录模式

**Brief 要求**：用 `industrial-data-preprocessor` 目录模式对混合格式 inbox（8 文件：CSV/TSV/JSON/XLSX/MD 表/HTML 表，含 GBK 中文导出与分号分隔）做自适应归一化，产出逐文件格式识别、行/列数、数据质量排查（重复/缺失/离群，带位置）、统一视图说明与中文报告。

**执行**：`data_preprocessor.py --data-path cases/T1_preprocessor_mixed_inbox/inbox --output results/T1 --name fieldtest_T1` → exit 0（1 条 pandas UserWarning，data_preprocessor.py:425）。随后按 brief 用 venv pandas 逐文件自查（qa_audit.py 因 venv 缺 lxml 在 read_html 处 exit 1，改用 stdlib HTMLParser 的 qa_audit_part2.py exit 0 完成 — 预处理器自身不受影响，它内置 regex HTML 抽取器，data_preprocessor.py:372）。

**系统产出（关键数字）**：tables_found=8，context=0，skipped=0；选中 sensor_log.csv（301×7，score 5.701）；统一视图 preprocessed_data.csv **301 行 × 18 列**（缺失 27.41%），outer_merge_on_time，key=timestamp，参与合并 4 文件（sensor_log / process_log.tsv / batch_records.json / dcs_export_gbk.csv），heater_export.csv（零时间重叠）、qa_lab.xlsx（无时间列）、downtime.html（零重叠）、operator_notes.md（重叠约 13%<30%）未合并。质量排查：sensor_log 重复时间戳+整行重复（行 152/302，10:30:00）；batch_records B0058 moisture_pct=null；qa_lab 3 处缺失（行 39/90/123）；dcs 两处不可能离群（行 53 温度=999.9、行 123 转速=-3.2）。**999.9 与 -3.2 原样透传进统一视图，重复行也未去重**（report quality 段只声明缺失留 NaN）。

**判定**：PASS（主流程与格式识别全部正确）。粗糙点 4 个：① report 中 `selected_table.n_cols=18`（合并视图）与 `tables[]` 中同文件 `n_cols=7`（原始表）同名异义；② stdout 摘要与 report tables 的列数不一致；③ 未合并文件的排除原因不写进 report（只有 ≥30% 规则一句话，需自行推断）；④ 离群值/重复行不做任何标记或处理（属"下游清理"契约，但 999.9 这类明显哨兵值值得警示）。

**产物**：results/T1/{preprocessing_report.json, preprocessed_data.csv, preprocessed_data.json, T1_report.md, commands.log, qa_audit.py, qa_audit_part2.py}
