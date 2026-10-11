# 产线哨兵巡检报告（watch 模式）

- **生成时间**：2026-10-06T16:38:02.214758+00:00
- **总体状态**：**alert** · 告警数 **18**
- **数据**：`D:\codes\industrial-deep-diagnostic\workspace\aw-exchange\demo1-melt-gel-clean-20261007T003154.csv`（1340 行；时间列 ts_iso；分组列 -）
- **基线**：模式：prior（v1.0.0），路径：D:\codes\industrial-deep-diagnostic\workspace\closedloop\sentinel\baselines\演示线1\watch_baseline.json
- **耗时**：21 ms（零 LLM / 零网络，全部统计由确定性脚本计算）


## 一、告警清单

| # | 级别 | 规则 | 参数/指标 | 分组 | 位置 | 观测值 | 建议 |
|---|------|------|-----------|------|------|--------|------|
| 1 | high | ROBUST_Z_OUTLIER | gel_count | __ALL__ | 1317 | 1 | gel_count 稳健 z 分数 \|-11.12\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 2 | high | NELSON_R1 | gel_count | __ALL__ | 1 | 3 | gel_count 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 3 | high | NELSON_R1 | gel_count | __ALL__ | 1320 | 4 | gel_count 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 4 | high | NELSON_R1 | melt_temp | __ALL__ | 16 | 201.5 | melt_temp 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 5 | high | NELSON_R1 | melt_temp | __ALL__ | 135 | 201.3 | melt_temp 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 6 | high | NELSON_R1 | melt_temp | __ALL__ | 948 | 198.6 | melt_temp 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 7 | high | NELSON_R5 | gel_count | __ALL__ | 2 | 5 | gel_count 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 8 | high | NELSON_R5 | gel_count | __ALL__ | 1324 | 4 | gel_count 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 9 | high | NELSON_R5 | melt_temp | __ALL__ | 3 | 208.5 | melt_temp 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 10 | high | NELSON_R5 | melt_temp | __ALL__ | 1150 | 200.1 | melt_temp 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 11 | high | NELSON_R5 | melt_temp | __ALL__ | 1228 | 200.9 | melt_temp 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 12 | high | NELSON_R6 | gel_count | __ALL__ | 1322 | 4 | gel_count 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 13 | high | NELSON_R6 | melt_temp | __ALL__ | 20 | 200.1 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 14 | high | NELSON_R6 | melt_temp | __ALL__ | 1084 | 199.8 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 15 | warn | NELSON_R2 | gel_count | __ALL__ | 10 | 5 | gel_count 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 16 | warn | NELSON_R2 | melt_temp | __ALL__ | 11 | 203.8 | melt_temp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 17 | warn | NELSON_R2 | melt_temp | __ALL__ | 330 | 200 | melt_temp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 18 | warn | NELSON_R2 | melt_temp | __ALL__ | 1186 | 200 | melt_temp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |


> 级别语义：`info` 记录级 / `warn` 趋势与待确认趋势 / `high` 统计异常 / `critical` 越规格。
> 本系统为纯分析系统：所有告警仅为建议核查项，不下发任何参数，动作决策由产线（AWS 侧）做出。

## 二、稳态映射（C3）

- **__ALL__**：abnormal=8、marginal=4、startup=6、steady=1322

## 三、操作窗口投影（C2）

- **C2 漂移投影未启用**：基线中无 operating_windows —— 构建基线时传入 --doe-run-dir 注册 DOE 先验操作窗即可启用（C2 drift projection disabled: no operating_windows in baseline (build with --doe-run-dir to enable)）

## 四、防风暴抑制

合并触发 8 组同 key 重复；静默期 30 行；同类抑制窗口 60 分钟；迟滞 5 点

## 五、告警事件摘要（incidents）

| 事件 | 参数 | 类别 | 峰值级别 | 跨度(行) | 告警数 | 规则 |
|------|------|------|----------|----------|--------|------|
| EVT-20261006163802-002 | melt_temp | spc | high | 132 | 5 | NELSON_R5、NELSON_R2、NELSON_R1… |
| EVT-20261006163802-005 | melt_temp | spc | high | 144 | 4 | NELSON_R6、NELSON_R5、NELSON_R2 |
| EVT-20261006163802-001 | gel_count | spc | high | 9 | 3 | NELSON_R1、NELSON_R5、NELSON_R2 |
| EVT-20261006163802-007 | gel_count | spc | high | 4 | 3 | NELSON_R1、NELSON_R6、NELSON_R5 |
| EVT-20261006163802-004 | melt_temp | spc | high | 0 | 1 | NELSON_R1 |
| EVT-20261006163802-006 | gel_count | multivariate | high | 0 | 1 | ROBUST_Z_OUTLIER |
| EVT-20261006163802-003 | melt_temp | spc | warn | 0 | 1 | NELSON_R2 |

## 六、建议后续动作

- 有 `high`/`critical` 告警：按告警中的 `suggested_check` 现场核查；需要根因分析时转 `industrial-diagnostician`，需要参数窗口/工况数据分析时转 `industrial-doe-analyzer`。
- 事件摘要按峰值级别与告警数排序；完整逐段告警在 alert.json 的 `alerts` 数组（契约不变），事件视图在 `events` 数组。
- 本报告由脚本生成（`authored_by: script`）；代理只允许追加中文 `interpretation` 注记，禁止改动任何数值字段。
