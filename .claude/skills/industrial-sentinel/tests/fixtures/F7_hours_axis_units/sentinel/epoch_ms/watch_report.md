# 产线哨兵巡检报告（watch 模式）

- **生成时间**：2026-10-05T07:49:44.828575+00:00
- **总体状态**：**warn** · 告警数 **10**
- **数据**：`D:\codes\industrial-deep-diagnostic\.claude\skills\industrial-sentinel\tests\fixtures\F7_hours_axis_units\watch_epoch_ms.csv`（600 行；时间列 timestamp；分组列 -）
- **基线**：模式：prior（v1.0.0），路径：D:\codes\industrial-deep-diagnostic\.claude\skills\industrial-sentinel\tests\fixtures\F7_hours_axis_units\watch_baseline.json
- **耗时**：21 ms（零 LLM / 零网络，全部统计由确定性脚本计算）


## 一、告警清单

| # | 级别 | 规则 | 参数/指标 | 分组 | 位置 | 观测值 | 建议 |
|---|------|------|-----------|------|------|--------|------|
| 1 | warn | NELSON_R2 | press | __ALL__ | 33 | 10.06 | press 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 2 | warn | NELSON_R2 | press | __ALL__ | 208 | 10.02 | press 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3 | warn | NELSON_R2 | press | __ALL__ | 390 | 10.04 | press 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4 | warn | NELSON_R2 | press | __ALL__ | 522 | 10.03 | press 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 5 | warn | NELSON_R2 | temp | __ALL__ | 8 | 49.56 | temp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 6 | warn | NELSON_R2 | temp | __ALL__ | 243 | 49.8 | temp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 7 | warn | NELSON_R2 | temp | __ALL__ | 435 | 49.82 | temp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 8 | warn | NELSON_R2 | temp | __ALL__ | 564 | 50.07 | temp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 9 | warn | NELSON_R3 | press | __ALL__ | 484 | 10.01 | press 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 10 | warn | WINDOW_DRIFT_PROJECTION | temp | __ALL__ | - | 50 | temp 按当前漂移速率预计 10.7 小时后触及窗口边界 [49.5, 50.5]，请提前安排核查 |


> 级别语义：`info` 记录级 / `warn` 趋势与待确认趋势 / `high` 统计异常 / `critical` 越规格。
> 本系统为纯分析系统：所有告警仅为建议核查项，不下发任何参数，动作决策由产线（AWS 侧）做出。

## 二、稳态映射（C3）

- **__ALL__**：steady=600

## 三、操作窗口投影（C2）

- **temp**：当前 50，斜率 0.04714/h，距边界 10.663340733434113 h（级别 warn）

## 四、防风暴抑制

合并触发 2 组同 key 重复；静默期 30 行；同类抑制窗口 60 分钟；迟滞 5 点

## 五、告警事件摘要（incidents）

| 事件 | 参数 | 类别 | 峰值级别 | 跨度(行) | 告警数 | 规则 |
|------|------|------|----------|----------|--------|------|
| EVT-20261005074944-006 | press | spc | warn | 132 | 3 | NELSON_R2、NELSON_R3 |
| EVT-20261005074944-001 | temp | window_projection | warn | 0 | 1 | WINDOW_DRIFT_PROJECTION |
| EVT-20261005074944-002 | temp | spc | warn | 0 | 1 | NELSON_R2 |
| EVT-20261005074944-003 | press | spc | warn | 0 | 1 | NELSON_R2 |
| EVT-20261005074944-004 | press | spc | warn | 0 | 1 | NELSON_R2 |
| EVT-20261005074944-005 | temp | spc | warn | 0 | 1 | NELSON_R2 |
| EVT-20261005074944-007 | temp | spc | warn | 0 | 1 | NELSON_R2 |
| EVT-20261005074944-008 | temp | spc | warn | 0 | 1 | NELSON_R2 |

## 六、建议后续动作

- 有 `high`/`critical` 告警：按告警中的 `suggested_check` 现场核查；需要根因分析时转 `industrial-diagnostician`，需要参数窗口/工况数据分析时转 `industrial-doe-analyzer`。
- 事件摘要按峰值级别与告警数排序；完整逐段告警在 alert.json 的 `alerts` 数组（契约不变），事件视图在 `events` 数组。
- 本报告由脚本生成（`authored_by: script`）；代理只允许追加中文 `interpretation` 注记，禁止改动任何数值字段。
