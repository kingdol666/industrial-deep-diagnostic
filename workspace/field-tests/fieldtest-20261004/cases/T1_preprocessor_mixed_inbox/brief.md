# T1 任务简报 — 在线数据接驳箱（data-preprocessor 目录模式）

## 场景

一条产线的上游系统会分批把不同格式的数据文件投放到同一个接驳箱文件夹
（inbox）。目前箱内累积了 3 个批次、8 个文件：CSV / TSV / JSON / XLSX /
Markdown 表 / HTML 表，其中包含一个 GBK 编码的中文 DCS 导出和一个分号分隔
的加热器导出。

你的任务：用 `industrial-data-preprocessor` 的**目录模式**对整个 inbox 做
自适应归一化与分析。

## 输入（只读，禁止修改源文件）

- `cases/T1_preprocessor_mixed_inbox/inbox/`（8 个文件）

## 环境（已验证的入口，照抄即可）

- 工作目录：`workspace/field-tests/fieldtest-20261004/`（下述相对路径以此为准）
- venv Python（所有 Python 脚本必须用它）：
  `D:\codes\industrial-deep-diagnostic\.claude\shared\scripts\.venv\Scripts\python.exe`
- 被测脚本：
  `D:\codes\industrial-deep-diagnostic\.claude\skills\industrial-data-preprocessor\scripts\data_preprocessor.py`
  （CLI：`--data-path`（文件或目录）、`--output`（输出目录）、`--name`（可选））

## 要求

1. 先建输出目录 `results/T1/`，然后执行目录模式预处理：

```bash
"$PY" "D:\codes\industrial-deep-diagnostic\.claude\skills\industrial-data-preprocessor\scripts\data_preprocessor.py" \
  --data-path cases/T1_preprocessor_mixed_inbox/inbox \
  --output results/T1 \
  --name fieldtest_T1
```

2. 逐条命令与退出码记入台账（`results/T1/commands.log`）。

3. 输出一份中文报告 `results/T1/T1_report.md`，内容必须包含：
   - **逐文件格式识别**：每个文件被识别成什么格式/角色（table / context /
     skip / no_tabular / error），分隔符或编码方面的判定（如 GBK、分号、TAB、
     Markdown 管道表、HTML 表）；
   - **逐文件行数与列数**：以 `results/T1/preprocessing_report.json` 的
     `tables` 记录为准转述；
   - **数据质量问题排查**：对每个源文件自行检查并报告——重复时间戳 /
     重复行、缺失单元格（数量与所在文件）、明显不可能的离群值。要给出具体
     位置（哪一行/哪个字段），不要只写"有缺失"；
   - **统一视图**：说明 `results/T1/preprocessed_data.csv` 的行数、列数、
     时间列，以及它是怎么来的（单表胜出还是多表合并、合并键、哪些文件参与
     了合并、哪些没有参与、为什么）；说明统一视图里缺失单元格的比例及其
     成因（结构性稀疏 vs 真实缺陷要区分开）。

4. 把你在第 3 步自行排查时用到的任何辅助命令（例如用 pandas 抽查重复行）
   也记入台账。除 `results/T1/` 外不得写任何其它位置；不得改动 inbox 下的
   任何文件。
