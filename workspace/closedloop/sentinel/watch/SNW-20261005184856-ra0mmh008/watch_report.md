# 产线哨兵巡检报告（watch 模式）

- **生成时间**：2026-10-05T18:48:57.386217+00:00
- **总体状态**：**alert** · 告警数 **45**
- **数据**：`D:\codes\industrial-deep-diagnostic\workspace\aw-exchange\line1-disturb-0244-watch.csv`（2600 行；时间列 time；分组列 -）
- **基线**：模式：prior（v1.0.0），路径：D:\codes\industrial-deep-diagnostic\workspace\closedloop\sentinel\baselines\演示线1\watch_baseline.json
- **耗时**：81 ms（零 LLM / 零网络，全部统计由确定性脚本计算）


## 一、告警清单

| # | 级别 | 规则 | 参数/指标 | 分组 | 位置 | 观测值 | 建议 |
|---|------|------|-----------|------|------|--------|------|
| 1 | high | NELSON_R1 | melt_temp | __ALL__ | 867 | 203.8 | melt_temp 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 2 | high | NELSON_R1 | melt_temp | __ALL__ | 981 | 203.8 | melt_temp 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 3 | high | NELSON_R1 | melt_temp | __ALL__ | 1309 | 206.3 | melt_temp 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 4 | high | NELSON_R1 | melt_temp | __ALL__ | 1435 | 203.8 | melt_temp 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 5 | high | NELSON_R1 | melt_temp | __ALL__ | 1524 | 203.9 | melt_temp 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 6 | high | NELSON_R1 | melt_temp | __ALL__ | 1702 | 203.9 | melt_temp 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 7 | high | NELSON_R1 | melt_temp | __ALL__ | 1834 | 206.5 | melt_temp 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 8 | high | NELSON_R1 | melt_temp | __ALL__ | 2454 | 206.3 | melt_temp 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 9 | high | NELSON_R5 | melt_temp | __ALL__ | 252 | 205.1 | melt_temp 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 10 | high | NELSON_R5 | melt_temp | __ALL__ | 351 | 204.3 | melt_temp 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 11 | high | NELSON_R5 | melt_temp | __ALL__ | 716 | 204.9 | melt_temp 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 12 | high | NELSON_R5 | melt_temp | __ALL__ | 1246 | 205.1 | melt_temp 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 13 | high | NELSON_R5 | melt_temp | __ALL__ | 1431 | 205.4 | melt_temp 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 14 | high | NELSON_R5 | melt_temp | __ALL__ | 1887 | 205.1 | melt_temp 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 15 | high | NELSON_R5 | melt_temp | __ALL__ | 1978 | 205.2 | melt_temp 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 16 | high | NELSON_R5 | melt_temp | __ALL__ | 2068 | 206.1 | melt_temp 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 17 | high | NELSON_R5 | melt_temp | __ALL__ | 2160 | 206 | melt_temp 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 18 | high | NELSON_R5 | melt_temp | __ALL__ | 2448 | 204.4 | melt_temp 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 19 | high | NELSON_R6 | melt_temp | __ALL__ | 159 | 205.6 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 20 | high | NELSON_R6 | melt_temp | __ALL__ | 363 | 205.2 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 21 | high | NELSON_R6 | melt_temp | __ALL__ | 633 | 204.6 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 22 | high | NELSON_R6 | melt_temp | __ALL__ | 746 | 204.1 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 23 | high | NELSON_R6 | melt_temp | __ALL__ | 817 | 204.6 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 24 | high | NELSON_R6 | melt_temp | __ALL__ | 984 | 204.6 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 25 | high | NELSON_R6 | melt_temp | __ALL__ | 1056 | 204.7 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 26 | high | NELSON_R6 | melt_temp | __ALL__ | 1378 | 205.7 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 27 | high | NELSON_R6 | melt_temp | __ALL__ | 1485 | 204.8 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 28 | high | NELSON_R6 | melt_temp | __ALL__ | 1584 | 205.1 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 29 | high | NELSON_R6 | melt_temp | __ALL__ | 1715 | 205.5 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 30 | high | NELSON_R6 | melt_temp | __ALL__ | 1908 | 204.7 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 31 | high | NELSON_R6 | melt_temp | __ALL__ | 2001 | 205.3 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 32 | high | NELSON_R6 | melt_temp | __ALL__ | 2138 | 204.6 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 33 | high | NELSON_R6 | melt_temp | __ALL__ | 2376 | 205.2 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 34 | high | NELSON_R6 | melt_temp | __ALL__ | 2457 | 205.6 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 35 | high | NELSON_R6 | melt_temp | __ALL__ | 2567 | 205.8 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 36 | warn | NELSON_R2 | melt_temp | __ALL__ | 118 | 205 | melt_temp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 37 | warn | NELSON_R2 | melt_temp | __ALL__ | 402 | 205.1 | melt_temp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 38 | warn | NELSON_R2 | melt_temp | __ALL__ | 528 | 204.9 | melt_temp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 39 | warn | NELSON_R2 | melt_temp | __ALL__ | 609 | 205.1 | melt_temp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 40 | warn | NELSON_R2 | melt_temp | __ALL__ | 1440 | 204.7 | melt_temp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 41 | warn | NELSON_R2 | melt_temp | __ALL__ | 1652 | 204.6 | melt_temp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 42 | warn | NELSON_R2 | melt_temp | __ALL__ | 2065 | 205 | melt_temp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 43 | warn | NELSON_R2 | melt_temp | __ALL__ | 2239 | 204.8 | melt_temp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 44 | warn | NELSON_R2 | melt_temp | __ALL__ | 2486 | 205.1 | melt_temp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 45 | warn | NELSON_R3 | melt_temp | __ALL__ | 1206 | 205 | melt_temp 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |


> 级别语义：`info` 记录级 / `warn` 趋势与待确认趋势 / `high` 统计异常 / `critical` 越规格。
> 本系统为纯分析系统：所有告警仅为建议核查项，不下发任何参数，动作决策由产线（AWS 侧）做出。

## 二、稳态映射（C3）

- **__ALL__**：steady=2600

## 三、操作窗口投影（C2）

- **C2 漂移投影未启用**：基线中无 operating_windows —— 构建基线时传入 --doe-run-dir 注册 DOE 先验操作窗即可启用（C2 drift projection disabled: no operating_windows in baseline (build with --doe-run-dir to enable)）

## 四、防风暴抑制

合并触发 4 组同 key 重复；静默期 30 行；同类抑制窗口 60 分钟；迟滞 5 点

## 五、告警事件摘要（incidents）

| 事件 | 参数 | 类别 | 峰值级别 | 跨度(行) | 告警数 | 规则 |
|------|------|------|----------|----------|--------|------|
| EVT-20261005184857-003 | melt_temp | spc | high | 1033 | 23 | NELSON_R3、NELSON_R5、NELSON_R1… |
| EVT-20261005184857-002 | melt_temp | spc | high | 528 | 10 | NELSON_R2、NELSON_R6、NELSON_R5… |
| EVT-20261005184857-001 | melt_temp | spc | high | 284 | 6 | NELSON_R2、NELSON_R6、NELSON_R5 |
| EVT-20261005184857-004 | melt_temp | spc | high | 191 | 6 | NELSON_R6、NELSON_R5、NELSON_R1… |

## 六、建议后续动作

- 有 `high`/`critical` 告警：按告警中的 `suggested_check` 现场核查；需要根因分析时转 `industrial-diagnostician`，需要参数窗口/工况数据分析时转 `industrial-doe-analyzer`。
- 事件摘要按峰值级别与告警数排序；完整逐段告警在 alert.json 的 `alerts` 数组（契约不变），事件视图在 `events` 数组。
- 本报告由脚本生成（`authored_by: script`）；代理只允许追加中文 `interpretation` 注记，禁止改动任何数值字段。
