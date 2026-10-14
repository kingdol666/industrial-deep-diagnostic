# BOPET 加工过程分析决策题目集（bopet_cases）

5 个按真实场景设计的 BOPET（双向拉伸聚酯薄膜）产线分析决策题目。每个题目 = 独立文件夹 =
**题目.md（工单式任务书）+ 多源运行数据 CSV + ground_truth.md（出题人评分参考）+ 可复现生成脚本 + 生成清单**。

工艺窗口取自乐凯 FW3 真实快照（`data/lekai-test`）的典型运行值，与 `data/bopet_demo` 同基准。

## 题目一览

| 编号 | 文件夹 | 场景 | 考察点 | 难度 |
|---|---|---|---|---|
| BC1 | `bc1_dryer_dewpoint` | 雾度/晶点超标 → 干燥再生加热器老化 | 时滞因果链（露点→含水→雾度）、多假设排除 | ★★☆ |
| BC2 | `bc2_filter_dp_cycles` | 过滤器压差锯齿 + 新原料速率加倍 | 周期模式识别、趋势外推、48h 检修窗口决策 | ★★★ |
| BC3 | `bc3_tdo_asymmetry` | TDO 南北风温不对称 → 宽度收窄、操作侧破膜 | 空间不对称诊断、位置证据、反补偿决策 | ★★★ |
| BC4 | `bc4_regrind_confounded` | 回料比例提升 + 季节升温混淆力学性能 | 竞争假设、混杂因素、干预（剂量-响应）证据 | ★★★★ |
| BC5 | `bc5_gauge_thermal_drift` | 厚度"漂移"实为测厚仪温漂 | 测量系统 vs 工艺真值、反事实推算、驳回误调整 | ★★★★ |

数据规模：BC1 14d/10min+4h；BC2 21d/10min+8h；BC3 12d/10min+8h；BC4 30d/1h+12h；BC5 10d/10min+8h。
全部确定性生成（固定 seed），`generation_manifest.json` 记录 seed、行数、sha256 与注入事件。

## 数据格式约定（已通过流水线格式门禁验证）

- CSV 编码 **UTF-8 with BOM**（utf-8-sig），逗号分隔，无空值/无重复行；
- 首列为 `时间`（`%Y-%m-%d %H:%M:%S`），inspect.mjs 自动识别为 datetime 时间列；
- 列名中文并内嵌单位，如 `干燥塔露点温度(℃)`、`过滤器压差(bar)`；
- 多采样率文件不合并（DCS 高频表为主表，化验/校准/事件表独立供交叉验证，与 `cement_ball_mill` 双表约定一致）；
- 事件型记录（`maintenance_log.csv` / `recipe_change_log.csv`）为「时间 + 事件类型 + 内容」三列。

已验证：`industrial-analysis-auto/scripts/inspect.mjs` 逐文件识别正常；`industrial-data-preprocessor`（流水线正式入口）对 5 个文件夹全部 `status: ok`，DCS 表自动选为主表，`题目.md` 归入 context。

## 使用方法

```bash
# 直接把场景文件夹喂给流水线（题目.md 会作为 context 进入本体/上下文构建）
node .claude/shared/scripts/uv_env_setup.mjs
uv run --project .claude/shared/scripts python .claude/skills/industrial-data-preprocessor/scripts/data_preprocessor.py \
  --data-path data/bopet_cases/bc1_dryer_dewpoint --output <RUN_DIR>/00_input --name bc1

# 数据再生成（确定性，可复现）
.claude/shared/scripts/.venv/Scripts/python.exe data/bopet_cases/bc1_dryer_dewpoint/generate_data.py
```

## 作答与评分纪律

- 作答方只读 `题目.md` 与数据 CSV；**不得阅读** `ground_truth.md` 与 `generation_manifest.json`（后者含答案锚点）。
- 结论按 DETERMINED / COMPETING_SET / NEEDS_DATA 三态给出，附证据等级（L1–L7）与置信度；
- 决策类小题（BC2 检修窗口、BC3 反补偿、BC4 回料上限、BC5 驳回/批准）必须给出量化依据。
