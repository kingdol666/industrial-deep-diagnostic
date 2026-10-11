# 产线哨兵巡检报告（watch 模式）

- **生成时间**：2026-10-06T09:00:14.164466+00:00
- **总体状态**：**alert** · 告警数 **61**
- **数据**：`D:\codes\industrial-deep-diagnostic\workspace\aw-exchange\merged_ln-d7e0a2a2_20261006T165922.csv`（5000 行；时间列 time；分组列 -）
- **基线**：模式：prior（v1.0.0），路径：D:\codes\industrial-deep-diagnostic\workspace\closedloop\sentinel\baselines\演示线1·挤出主机PLC(Modbus TCP)\watch_baseline.json
- **耗时**：242 ms（零 LLM / 零网络，全部统计由确定性脚本计算）


## 一、告警清单

| # | 级别 | 规则 | 参数/指标 | 分组 | 位置 | 观测值 | 建议 |
|---|------|------|-----------|------|------|--------|------|
| 1 | high | ROBUST_Z_OUTLIER | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 599 | 177.9 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 稳健 z 分数 \|-9.59\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 2 | high | ROBUST_Z_OUTLIER | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 4616 | 177.5 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 稳健 z 分数 \|-9.73\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 3 | high | ROBUST_Z_OUTLIER | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | __ALL__ | 214 | 69 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) 稳健 z 分数 \|14.56\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 4 | high | ROBUST_Z_OUTLIER | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | __ALL__ | 3885 | 69 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) 稳健 z 分数 \|14.56\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 5 | high | ROBUST_Z_OUTLIER | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | __ALL__ | 3998 | 69 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) 稳健 z 分数 \|14.56\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 6 | high | ROBUST_Z_OUTLIER | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | __ALL__ | 4814 | 69 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) 稳健 z 分数 \|14.56\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 7 | high | NELSON_R1 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 1042 | 199.6 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 8 | high | NELSON_R5 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 2429 | 16.8 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 9 | high | NELSON_R5 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | __ALL__ | 3615 | 67.2 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 10 | high | NELSON_R6 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 2429 | 16.8 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 11 | high | NELSON_R6 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 4082 | 181.5 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 12 | high | NELSON_R6 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 4619 | 179.6 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 13 | high | NELSON_R6 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | __ALL__ | 3703 | 64 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 14 | high | NELSON_R6 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | __ALL__ | 3797 | 63.2 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 15 | high | NELSON_R6 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | __ALL__ | 3909 | 63.3 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 16 | high | NELSON_R6 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | __ALL__ | 4173 | 65.6 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 17 | high | NELSON_R6 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | __ALL__ | 4304 | 65.7 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 18 | high | NELSON_R6 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | __ALL__ | 4923 | 66.4 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 19 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 202 | - | __ALL__ 组在第 202 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 20 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 2265 | - | __ALL__ 组在第 2265 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 21 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 2281 | - | __ALL__ 组在第 2281 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 22 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 2345 | - | __ALL__ 组在第 2345 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 23 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 2378 | - | __ALL__ 组在第 2378 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 24 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 2395 | - | __ALL__ 组在第 2395 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 25 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 2439 | - | __ALL__ 组在第 2439 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 26 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 985 | - | __ALL__ 组在第 985 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 27 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 996 | - | __ALL__ 组在第 996 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 28 | warn | NELSON_R2 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 8 | 180.6 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 29 | warn | NELSON_R2 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 2437 | 158.2 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 30 | warn | NELSON_R2 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 2658 | 180.2 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 31 | warn | NELSON_R2 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 3320 | 178.8 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 32 | warn | NELSON_R2 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 3466 | 179.4 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 33 | warn | NELSON_R2 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 3567 | 180.4 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 34 | warn | NELSON_R2 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 4976 | 179.5 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 35 | warn | NELSON_R2 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | __ALL__ | 2477 | 65.7 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 36 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 82 | 181.3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 37 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 243 | 181.8 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 38 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 598 | 178.2 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 39 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 883 | 179.5 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 40 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 2251 | 199.3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 41 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 2332 | 205.3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 42 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 2434 | 136.7 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 43 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 2570 | 179.6 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 44 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 2669 | 182 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 45 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 2793 | 179.4 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 46 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 2904 | 179.4 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 47 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 2968 | 180.5 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 48 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 3031 | 179.5 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 49 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 3126 | 179.6 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 50 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 3328 | 178.8 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 51 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 3400 | 179.8 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 52 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 3496 | 179.8 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 53 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 3736 | 181.2 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 54 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 3846 | 178.9 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 55 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 4186 | 179.4 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 56 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 4275 | 181.8 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 57 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 4368 | 180.1 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 58 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 4499 | 179.6 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 59 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 4616 | 177.5 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 60 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 4703 | 180.8 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 61 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 4988 | 178.9 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |


> 级别语义：`info` 记录级 / `warn` 趋势与待确认趋势 / `high` 统计异常 / `critical` 越规格。
> 本系统为纯分析系统：所有告警仅为建议核查项，不下发任何参数，动作决策由产线（AWS 侧）做出。

## 二、稳态映射（C3）

- **__ALL__**：abnormal=45、marginal=23、steady=4833、transition=99

## 三、操作窗口投影（C2）

- **C2 漂移投影未启用**：基线中无 operating_windows —— 构建基线时传入 --doe-run-dir 注册 DOE 先验操作窗即可启用（C2 drift projection disabled: no operating_windows in baseline (build with --doe-run-dir to enable)）

## 四、防风暴抑制

合并触发 8 组同 key 重复；静默期 30 行；同类抑制窗口 60 分钟；迟滞 5 点

## 五、告警事件摘要（incidents）

| 事件 | 参数 | 类别 | 峰值级别 | 跨度(行) | 告警数 | 规则 |
|------|------|------|----------|----------|--------|------|
| EVT-20261006090014-010 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | spc | high | 186 | 6 | NELSON_R3、NELSON_R5、NELSON_R6… |
| EVT-20261006090014-016 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | spc | high | 294 | 4 | NELSON_R5、NELSON_R6 |
| EVT-20261006090014-019 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | spc | high | 286 | 4 | NELSON_R6、NELSON_R3 |
| EVT-20261006090014-022 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | spc | high | 204 | 4 | NELSON_R3、NELSON_R6 |
| EVT-20261006090014-018 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | multivariate | high | 113 | 2 | ROBUST_Z_OUTLIER |
| EVT-20261006090014-003 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | multivariate | high | 0 | 1 | ROBUST_Z_OUTLIER |
| EVT-20261006090014-006 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | multivariate | high | 0 | 1 | ROBUST_Z_OUTLIER |
| EVT-20261006090014-009 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | spc | high | 0 | 1 | NELSON_R1 |
| EVT-20261006090014-020 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | spc | high | 0 | 1 | NELSON_R6 |
| EVT-20261006090014-021 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | spc | high | 0 | 1 | NELSON_R6 |
| EVT-20261006090014-023 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | multivariate | high | 0 | 1 | ROBUST_Z_OUTLIER |
| EVT-20261006090014-024 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | multivariate | high | 0 | 1 | ROBUST_Z_OUTLIER |

（其余 14 个事件见 alert.json 的 events 数组；完整逐段告警在 alerts 数组，契约不变）

## 六、建议后续动作

- 有 `high`/`critical` 告警：按告警中的 `suggested_check` 现场核查；需要根因分析时转 `industrial-diagnostician`，需要参数窗口/工况数据分析时转 `industrial-doe-analyzer`。
- 事件摘要按峰值级别与告警数排序；完整逐段告警在 alert.json 的 `alerts` 数组（契约不变），事件视图在 `events` 数组。
- 本报告由脚本生成（`authored_by: script`）；代理只允许追加中文 `interpretation` 注记，禁止改动任何数值字段。
