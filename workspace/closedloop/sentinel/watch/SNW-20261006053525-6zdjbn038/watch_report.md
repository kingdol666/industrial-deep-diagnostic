# 产线哨兵巡检报告（watch 模式）

- **生成时间**：2026-10-06T05:35:26.022122+00:00
- **总体状态**：**alert** · 告警数 **50**
- **数据**：`D:\codes\industrial-deep-diagnostic\workspace\aw-exchange\v2_stage1_merged_ln1_20261006T133118.csv`（1737 行；时间列 time；分组列 -）
- **基线**：模式：prior（v1.0.0），路径：D:\codes\industrial-deep-diagnostic\workspace\closedloop\sentinel\baselines\演示线1·挤出主机PLC(Modbus TCP)\watch_baseline.json
- **耗时**：47 ms（零 LLM / 零网络，全部统计由确定性脚本计算）


## 一、告警清单

| # | 级别 | 规则 | 参数/指标 | 分组 | 位置 | 观测值 | 建议 |
|---|------|------|-----------|------|------|--------|------|
| 1 | high | ROBUST_Z_OUTLIER | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 2 | 179.2 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 稳健 z 分数 \|-9.13\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 2 | high | ROBUST_Z_OUTLIER | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 226 | 177.6 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 稳健 z 分数 \|-9.69\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 3 | high | ROBUST_Z_OUTLIER | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 340 | 177.9 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 稳健 z 分数 \|-9.59\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 4 | high | ROBUST_Z_OUTLIER | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 523 | 179.6 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 稳健 z 分数 \|-8.99\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 5 | high | ROBUST_Z_OUTLIER | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 749 | 178.4 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 稳健 z 分数 \|-9.41\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 6 | high | ROBUST_Z_OUTLIER | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 1452 | 177.5 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 稳健 z 分数 \|-9.73\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 7 | high | ROBUST_Z_OUTLIER | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 1675 | 178.2 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 稳健 z 分数 \|-9.48\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 8 | high | ROBUST_Z_OUTLIER | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | __ALL__ | 7 | 69 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) 稳健 z 分数 \|14.56\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 9 | high | NELSON_R1 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 28 | 180.4 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 10 | high | NELSON_R1 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 327 | 179.5 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 11 | high | NELSON_R1 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 487 | 179.2 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 12 | high | NELSON_R1 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 600 | 179.6 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 13 | high | NELSON_R1 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 784 | 178.9 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 14 | high | NELSON_R1 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 1561 | 181 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 15 | high | NELSON_R1 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 1736 | 181.8 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 16 | high | NELSON_R1 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | __ALL__ | 1736 | 67 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 17 | high | NELSON_R5 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 28 | 180.4 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 18 | high | NELSON_R5 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 327 | 179.5 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 19 | high | NELSON_R5 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 487 | 179.2 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 20 | high | NELSON_R5 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 600 | 179.6 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 21 | high | NELSON_R5 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 784 | 178.9 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 22 | high | NELSON_R5 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 1561 | 181 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 23 | high | NELSON_R5 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 1736 | 181.8 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 24 | high | NELSON_R5 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | __ALL__ | 1736 | 67 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 25 | high | NELSON_R6 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 28 | 180.4 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 26 | high | NELSON_R6 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 327 | 179.5 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 27 | high | NELSON_R6 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 487 | 179.2 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 28 | high | NELSON_R6 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 600 | 179.6 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 29 | high | NELSON_R6 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 784 | 178.9 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 30 | high | NELSON_R6 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 1561 | 181 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 31 | high | NELSON_R6 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 1736 | 181.8 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 32 | high | NELSON_R6 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | __ALL__ | 1736 | 67 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 33 | warn | NELSON_R2 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 8 | 179.2 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 34 | warn | NELSON_R2 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 337 | 179.2 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 35 | warn | NELSON_R2 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 497 | 181.2 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 36 | warn | NELSON_R2 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 610 | 179.7 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 37 | warn | NELSON_R2 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 794 | 180.3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 38 | warn | NELSON_R2 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 1571 | 178.4 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 39 | warn | NELSON_R2 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | __ALL__ | 8 | 67.8 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 40 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 123 | 180.9 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 41 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 224 | 178.5 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 42 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 319 | 180.6 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 43 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 536 | 179.7 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 44 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 735 | 179.2 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 45 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 824 | 180.3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 46 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 897 | 181.3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 47 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 1033 | 178.3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 48 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 1341 | 179.6 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 49 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 1542 | 181 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 50 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 1734 | 182.1 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |


> 级别语义：`info` 记录级 / `warn` 趋势与待确认趋势 / `high` 统计异常 / `critical` 越规格。
> 本系统为纯分析系统：所有告警仅为建议核查项，不下发任何参数，动作决策由产线（AWS 侧）做出。

## 二、稳态映射（C3）

- **__ALL__**：steady=1737

## 三、操作窗口投影（C2）

- **C2 漂移投影未启用**：基线中无 operating_windows —— 构建基线时传入 --doe-run-dir 注册 DOE 先验操作窗即可启用（C2 drift projection disabled: no operating_windows in baseline (build with --doe-run-dir to enable)）

## 四、防风暴抑制

合并触发 6 组同 key 重复；静默期 30 行；同类抑制窗口 60 分钟；迟滞 5 点

## 五、告警事件摘要（incidents）

| 事件 | 参数 | 类别 | 峰值级别 | 跨度(行) | 告警数 | 规则 |
|------|------|------|----------|----------|--------|------|
| EVT-20261006053526-003 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | spc | high | 329 | 11 | NELSON_R2、NELSON_R1、NELSON_R5… |
| EVT-20261006053526-006 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | spc | high | 123 | 9 | NELSON_R1、NELSON_R5、NELSON_R6… |
| EVT-20261006053526-008 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | spc | high | 162 | 7 | NELSON_R3、NELSON_R1、NELSON_R5… |
| EVT-20261006053526-013 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | spc | high | 29 | 5 | NELSON_R3、NELSON_R1、NELSON_R5… |
| EVT-20261006053526-015 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | spc | high | 2 | 4 | NELSON_R3、NELSON_R1、NELSON_R5… |
| EVT-20261006053526-016 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | spc | high | 0 | 3 | NELSON_R1、NELSON_R5、NELSON_R6 |
| EVT-20261006053526-005 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | multivariate | high | 114 | 2 | ROBUST_Z_OUTLIER |
| EVT-20261006053526-001 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | multivariate | high | 0 | 1 | ROBUST_Z_OUTLIER |
| EVT-20261006053526-002 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | multivariate | high | 0 | 1 | ROBUST_Z_OUTLIER |
| EVT-20261006053526-007 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | multivariate | high | 0 | 1 | ROBUST_Z_OUTLIER |
| EVT-20261006053526-009 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | multivariate | high | 0 | 1 | ROBUST_Z_OUTLIER |
| EVT-20261006053526-012 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | multivariate | high | 0 | 1 | ROBUST_Z_OUTLIER |

（其余 4 个事件见 alert.json 的 events 数组；完整逐段告警在 alerts 数组，契约不变）

## 六、建议后续动作

- 有 `high`/`critical` 告警：按告警中的 `suggested_check` 现场核查；需要根因分析时转 `industrial-diagnostician`，需要参数窗口/工况数据分析时转 `industrial-doe-analyzer`。
- 事件摘要按峰值级别与告警数排序；完整逐段告警在 alert.json 的 `alerts` 数组（契约不变），事件视图在 `events` 数组。
- 本报告由脚本生成（`authored_by: script`）；代理只允许追加中文 `interpretation` 注记，禁止改动任何数值字段。
