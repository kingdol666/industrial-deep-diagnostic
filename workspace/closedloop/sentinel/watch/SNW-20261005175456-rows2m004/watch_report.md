# 产线哨兵巡检报告（watch 模式）

- **生成时间**：2026-10-05T17:54:57.492676+00:00
- **总体状态**：**alert** · 告警数 **41**
- **数据**：`D:\codes\industrial-deep-diagnostic\workspace\aw-exchange\line1-merged.csv`（1734 行；时间列 time；分组列 -）
- **基线**：模式：prior（v1.0.0），路径：D:\codes\industrial-deep-diagnostic\workspace\closedloop\sentinel\baselines\演示线1\watch_baseline.json
- **耗时**：26 ms（零 LLM / 零网络，全部统计由确定性脚本计算）


## 一、告警清单

| # | 级别 | 规则 | 参数/指标 | 分组 | 位置 | 观测值 | 建议 |
|---|------|------|-----------|------|------|--------|------|
| 1 | high | NELSON_R1 | melt_temp | __ALL__ | 229 | 203.9 | melt_temp 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 2 | high | NELSON_R1 | melt_temp | __ALL__ | 554 | 203.7 | melt_temp 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 3 | high | NELSON_R1 | melt_temp | __ALL__ | 687 | 206.4 | melt_temp 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 4 | high | NELSON_R1 | melt_temp | __ALL__ | 1504 | 206.4 | melt_temp 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 5 | high | NELSON_R1 | melt_temp | __ALL__ | 1627 | 203.8 | melt_temp 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 6 | high | NELSON_R1 | zone2_sp | __ALL__ | 313 | 9 | zone2_sp 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 7 | high | NELSON_R1 | zone2_sp | __ALL__ | 1578 | 9 | zone2_sp 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 8 | high | NELSON_R1 | zone2_sp | __ALL__ | 1670 | 9 | zone2_sp 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 9 | high | NELSON_R5 | melt_temp | __ALL__ | 367 | 205.4 | melt_temp 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 10 | high | NELSON_R5 | melt_temp | __ALL__ | 1478 | 204.9 | melt_temp 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 11 | high | NELSON_R5 | zone2_sp | __ALL__ | 14 | 4 | zone2_sp 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 12 | high | NELSON_R5 | zone2_sp | __ALL__ | 240 | 7 | zone2_sp 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 13 | high | NELSON_R5 | zone2_sp | __ALL__ | 458 | 5 | zone2_sp 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 14 | high | NELSON_R5 | zone2_sp | __ALL__ | 552 | 6 | zone2_sp 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 15 | high | NELSON_R5 | zone2_sp | __ALL__ | 635 | 7 | zone2_sp 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 16 | high | NELSON_R5 | zone2_sp | __ALL__ | 832 | 4 | zone2_sp 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 17 | high | NELSON_R5 | zone2_sp | __ALL__ | 987 | 6 | zone2_sp 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 18 | high | NELSON_R5 | zone2_sp | __ALL__ | 1167 | 1 | zone2_sp 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 19 | high | NELSON_R5 | zone2_sp | __ALL__ | 1390 | 6 | zone2_sp 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 20 | high | NELSON_R5 | zone2_sp | __ALL__ | 1523 | 7 | zone2_sp 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 21 | high | NELSON_R5 | zone2_sp | __ALL__ | 1676 | 3 | zone2_sp 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 22 | high | NELSON_R6 | melt_temp | __ALL__ | 258 | 204.3 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 23 | high | NELSON_R6 | melt_temp | __ALL__ | 437 | 206 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 24 | high | NELSON_R6 | melt_temp | __ALL__ | 739 | 204.4 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 25 | high | NELSON_R6 | melt_temp | __ALL__ | 924 | 205.6 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 26 | high | NELSON_R6 | melt_temp | __ALL__ | 1126 | 205.8 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 27 | high | NELSON_R6 | melt_temp | __ALL__ | 1395 | 204.7 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 28 | high | NELSON_R6 | melt_temp | __ALL__ | 1505 | 204.3 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 29 | high | NELSON_R6 | melt_temp | __ALL__ | 1577 | 204.6 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 30 | high | NELSON_R6 | zone2_sp | __ALL__ | 237 | 1 | zone2_sp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 31 | high | NELSON_R6 | zone2_sp | __ALL__ | 657 | 7 | zone2_sp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 32 | high | NELSON_R6 | zone2_sp | __ALL__ | 1678 | 6 | zone2_sp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 33 | warn | NELSON_R2 | melt_temp | __ALL__ | 198 | 204.9 | melt_temp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 34 | warn | NELSON_R2 | melt_temp | __ALL__ | 737 | 205 | melt_temp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 35 | warn | NELSON_R2 | melt_temp | __ALL__ | 1165 | 205.1 | melt_temp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 36 | warn | NELSON_R2 | melt_temp | __ALL__ | 1371 | 205.1 | melt_temp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 37 | warn | NELSON_R2 | zone2_sp | __ALL__ | 248 | 5 | zone2_sp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 38 | warn | NELSON_R2 | zone2_sp | __ALL__ | 831 | 8 | zone2_sp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 39 | warn | NELSON_R2 | zone2_sp | __ALL__ | 1023 | 4 | zone2_sp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 40 | warn | NELSON_R2 | zone2_sp | __ALL__ | 1142 | 1 | zone2_sp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 41 | warn | NELSON_R2 | zone2_sp | __ALL__ | 1475 | 5 | zone2_sp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |


> 级别语义：`info` 记录级 / `warn` 趋势与待确认趋势 / `high` 统计异常 / `critical` 越规格。
> 本系统为纯分析系统：所有告警仅为建议核查项，不下发任何参数，动作决策由产线（AWS 侧）做出。

## 二、稳态映射（C3）

- **__ALL__**：steady=1734

## 三、操作窗口投影（C2）

- **C2 漂移投影未启用**：基线中无 operating_windows —— 构建基线时传入 --doe-run-dir 注册 DOE 先验操作窗即可启用（C2 drift projection disabled: no operating_windows in baseline (build with --doe-run-dir to enable)）

## 四、防风暴抑制

合并触发 8 组同 key 重复；静默期 30 行；同类抑制窗口 60 分钟；迟滞 5 点

## 五、告警事件摘要（incidents）

| 事件 | 参数 | 类别 | 峰值级别 | 跨度(行) | 告警数 | 规则 |
|------|------|------|----------|----------|--------|------|
| EVT-20261005175457-010 | melt_temp | spc | high | 256 | 7 | NELSON_R2、NELSON_R6、NELSON_R5… |
| EVT-20261005175457-011 | zone2_sp | spc | high | 288 | 7 | NELSON_R5、NELSON_R2、NELSON_R1… |
| EVT-20261005175457-002 | melt_temp | spc | high | 356 | 6 | NELSON_R2、NELSON_R1、NELSON_R6… |
| EVT-20261005175457-003 | zone2_sp | spc | high | 76 | 4 | NELSON_R6、NELSON_R5、NELSON_R2… |
| EVT-20261005175457-004 | zone2_sp | spc | high | 199 | 4 | NELSON_R5、NELSON_R6 |
| EVT-20261005175457-008 | zone2_sp | spc | high | 180 | 4 | NELSON_R5、NELSON_R2 |
| EVT-20261005175457-005 | melt_temp | spc | high | 52 | 3 | NELSON_R1、NELSON_R2、NELSON_R6 |
| EVT-20261005175457-006 | zone2_sp | spc | high | 1 | 2 | NELSON_R2、NELSON_R5 |
| EVT-20261005175457-009 | melt_temp | spc | high | 39 | 2 | NELSON_R6、NELSON_R2 |
| EVT-20261005175457-001 | zone2_sp | spc | high | 0 | 1 | NELSON_R5 |
| EVT-20261005175457-007 | melt_temp | spc | high | 0 | 1 | NELSON_R6 |

## 六、建议后续动作

- 有 `high`/`critical` 告警：按告警中的 `suggested_check` 现场核查；需要根因分析时转 `industrial-diagnostician`，需要参数窗口/工况数据分析时转 `industrial-doe-analyzer`。
- 事件摘要按峰值级别与告警数排序；完整逐段告警在 alert.json 的 `alerts` 数组（契约不变），事件视图在 `events` 数组。
- 本报告由脚本生成（`authored_by: script`）；代理只允许追加中文 `interpretation` 注记，禁止改动任何数值字段。
