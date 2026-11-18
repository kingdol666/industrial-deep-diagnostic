# 产线稳定性报告 · 员工培训套件（workspace/lst-teaching-kit）

面向 `industrial-line-stability-report`（产线稳定性报告）的 7 道教学题：
**7 种行业场景 × 7 种数据形态**，从"零配置出报告"到"数据不足被诚实拒评"全覆盖。
数据全部为确定性合成（固定种子），每题配套 `题目.md`（场景+命令+报告看点）；
`line_report/` 内已附**参考答案**（报告 JSON + HTML，门禁 11 项全过）——培训时删除该目录即可让学员重练。

## 课程表（建议顺序）

| # | 文件夹 | 场景 | 数据形态 | 学员要学会什么 | 参考答案 |
|---|---|---|---|---|---|
| T1 | `T1_cement_mill/` | 水泥球磨机轴承温度爬升 | **XLSX** + 手写本体 + report_context | 完整路径：本体放入 `00_input/` 即被消费（相关性机制升级 known）；规格限/权重/质检列全量用法 | 83.8 分 B，10 发现 |
| T2 | `T2_wastewater_aeration/` | 污水曝气池 DO 走低 | **TSV**，无 context | 最简路径：只放数据文件也能出报告；漂移检出阈值（0.1%/天）；`regime` 工况切换发现的解读；无 context 时中文质检列不会被自动识别 | 55.0 分 C，10 发现 |
| T3 | `T3_injection_molding/` | 注塑机逐模重量波动 | **JSON**（行对象数组）+ report_context | JSON 读取约定；`time_col` 列名不叫"时间"时显式指定；无本体时相关性只能是"统计共变、待机理确认"（[MECHANISM_UNKNOWN]，置信度封顶 45） | 82.2 分 B，7 发现 |
| T4 | `T4_food_dryer/` | 食品烘干线健康周 | **Parquet**，无 context | 什么是"健康的报告"（98.2 分 A、零漂移、零星低密度 SPC）；规格缺失会被如实声明而非遗漏；别把"有发现"等同于"有问题" | 98.2 分 A，5 发现 |
| T5 | `T5_air_compressor/` | 空压机站（含死点传感器） | **GBK 编码 CSV** | 编码自动回退（utf-8→gb18030）；时间不变量通道被剔除并发 data_quality 发现——**"无波动 ≠ 稳定"** | 79.4 分 B，死点 1/6 通道被剔除 |
| T6 | `T6_reheating_furnace/` | 冶金加热炉夜班偏移 | **CSV，Unix 秒时间戳 + 英文表头** | 数值时间列自动按秒解析（采样间隔 1800s 自动推断）；SPC 同侧 runs 抓班次性偏移；表头语言无差别但报告参数名=列名 | 83.6 分 B，夜班平台被 runs 规则命中 |
| T7 | `T7_coating_too_few_rows/` | 涂装线仅 30 行 | **CSV，行数不足** | **exit 2 不是失败**：数据不足系统拒绝评分并说明原因，绝不硬凑结论；正确做法是放宽导出时段（≥50 行，建议 ≥100）或改用 sentinel fast-screen | 无报告（by design） |

## 学员运行前检查（三条铁律）

1. **数据必须在仓库目录内**（脚本有路径白名单，仓库外直接拒绝）；
2. 用 venv 运行：`uv run --project .claude/shared/scripts python <脚本> ...`（不要用系统 python）；
3. 退出码语义：0=无发现 / **1=有发现（报告完整，正常交付）** / 2=数据不足诚实降级 / 3=输入或门禁失败。

## 通用命令模板

```bash
cd <仓库根目录>
# ① 分析
uv run --project .claude/shared/scripts python \
  .claude/skills/industrial-line-stability-report/scripts/stability_analyzer.py analyze \
  --run-dir workspace/lst-teaching-kit/<题目文件夹>
# ② 出 HTML
uv run --project .claude/shared/scripts python \
  .claude/skills/industrial-line-stability-report/scripts/report_builder.py \
  --report <题目文件夹>/line_report/stability_report.json \
  --charts <题目文件夹>/line_report/charts.json \
  --out <题目文件夹>/line_report/line_stability_report.html
# ③ 门禁（必须 PASS 才算交付）
node .claude/skills/industrial-line-stability-report/scripts/quality_gate.mjs \
  <题目文件夹>/line_report/stability_report.json <题目文件夹>/line_report
```

## 复跑与重置

```bash
cd workspace/lst-teaching-kit
uv run --project ../../.claude/shared/scripts python make_teaching_fixtures.py   # 重建全部数据（确定性，同种子同结果）
# 删除某题 line_report/ 即可让学员从零重练
```

## 给讲师的话

- 每题的"报告看点"就是考核点：让学员先跑、再看 HTML、最后对照看点复述——能讲清楚"为什么这条发现扣分/为什么这条只是统计共变"即为过关；
- T1 vs T3 是一组对照（有本体 vs 无本体），T2 vs T4 是一组对照（异常线 vs 健康线），T7 单独讲诚实降级；
- 注入故障真值在各题数据生成逻辑里（`make_teaching_fixtures.py`，固定种子），讲师备课时先看脚本再上课。

## 修过的 skill 契约问题（2026-10-14）

教学套件实测暴露出 `stability_report.schema.json` 的 category 枚举漏了分析器会发出的
`regime`（工况切换）类发现，导致 T2/T5 门禁 FAIL——已在 skill schema 补上该枚举值并同步
`.agents/.hermes` 镜像（`node scripts/sync-harness-skills.mjs`），T2/T5 复验 PASS。
