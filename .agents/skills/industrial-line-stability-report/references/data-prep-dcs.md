# DCS 多级表头宽表预处理指南（产线稳定性 skill 输入准备）

产线稳定性 skill 只吃 **tidy 表**（每行一个时刻、每列一个通道、首行即列名）。
DCS/历史站导出的 Excel 常常是"多级表头 + 每时刻多行"的宽表——**先按下述配方整理，
再调 `stability_analyzer.py analyze`**。清洗属 `industrial-data-preprocessor` 职责；
本文件只是把 FW3 真实案例（`workspace/diagnostic-runs/20261010_lekai_fw3_bopet/parse_fw3.py`）
验证过的最小配方固化下来，避免每个 agent 现场重推。

## 常见源表结构（以 FW3 主控工艺参数查询表为例）

```
row1   单元（熔融挤出机/模头单元/纵拉单元/横拉单元/...，跨列合并）
row2   子单元（辊/位置，跨列合并）
row3   参数名（机筒温度/辊速/...，跨列合并）
row4   通道位号（IF/Z1../CX4/...，逐列）
row5   物理单位（℃/bar/m/min/...，逐列）
row6+  数据：每个时刻两行——列1=设定值/实际值，列0=时间（只在设定值行）
```

## 配方（确定性 pandas，无 LLM）

1. `pd.read_excel(path, header=None)`，**ffill** 跨列合并的单元/参数名列。
2. 列名 = `单元-子单元-参数名-位号` 去空白拼接，重复名追加 `.2/.3`（skill 的本体
   匹配对空白/全角差异有归一化兜底，但 tidy 列名本身要稳定可复算）。
3. 时间列 `ffill` 后**只保留 `实际值` 行**（设定值行另存一份备查，不入评分）。
4. 全列 `pd.to_numeric(errors="coerce")`；
   - 全 NaN 列 → 剔除并记录；
   - **时间不变量列保留**（它们是"快照导出/死点"的证据，skill 会自动剔除评分并声明），
     在 parse_summary 里给每列标 `time_invariant: true/false`。
5. 写 `parse_summary.json`：源文件 sha256、行/列范围、列映射、剔除清单、保留通道的
   min/max/mean/nunique —— 数据真值溯源要求，报告里 `context.preprocessing` 引用它。
6. 产物放进 `<run_dir>/00_input/`，`report_context.json` 加：

```json
{
  "time_col": "时间",
  "preprocessing": {
    "source_file": "data/lekai-test/FW3-....xlsx",
    "source_sha256": "<xlsx sha256>",
    "script": "parse_fw3.py",
    "summary": "00_input/parse_summary.json",
    "note": "仅保留实际值行；时间不变量通道保留待 skill 剔除"
  }
}
```

## ⚠️ 冻结快照检测（先于分析做）

导出后立刻校验：`df.drop(columns=[时间,值类型]).drop_duplicates()` 的行版本数。
若 **只有 1 个版本**（所有时刻数值完全相同），这是一份单时刻快照——
**无法评估时段稳定性**，skill 会诚实输出 exit 2；不要试图用时间标签数"凑行数"。
正确做法：回到 DCS/历史站改用**历史趋势/归档查询**导出逐时刻存档值
（每时刻一行、数值随时间变化），而不是"实时值 + 按时间分页"的查询表。
