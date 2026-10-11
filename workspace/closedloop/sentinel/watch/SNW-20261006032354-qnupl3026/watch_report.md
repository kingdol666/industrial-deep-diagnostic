# 产线哨兵巡检报告（watch 模式）

- **生成时间**：2026-10-06T03:23:54.577032+00:00
- **总体状态**：**alert** · 告警数 **69**
- **数据**：`D:\codes\industrial-deep-diagnostic\workspace\aw-exchange\ln1_merged_20261006112221.csv`（1713 行；时间列 time；分组列 -）
- **基线**：模式：prior（v1.0.0），路径：D:\codes\industrial-deep-diagnostic\workspace\closedloop\sentinel\baselines\演示线1\watch_baseline.json
- **耗时**：48 ms（零 LLM / 零网络，全部统计由确定性脚本计算）


## 一、告警清单

| # | 级别 | 规则 | 参数/指标 | 分组 | 位置 | 观测值 | 建议 |
|---|------|------|-----------|------|------|--------|------|
| 1 | high | ROBUST_Z_OUTLIER | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 1044 | 210.1 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 稳健 z 分数 \|6.22\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 2 | high | ROBUST_Z_OUTLIER | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 1210 | 199.6 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 稳健 z 分数 \|-9.71\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 3 | high | ROBUST_Z_OUTLIER | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 1322 | 208.6 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 稳健 z 分数 \|3.94\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 4 | high | ROBUST_Z_OUTLIER | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 1559 | 177.9 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 稳健 z 分数 \|-42.61\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 5 | high | ROBUST_Z_OUTLIER | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | __ALL__ | 1690 | 69 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) 稳健 z 分数 \|29.57\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 6 | high | NELSON_R1 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 52 | 204.8 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 7 | high | NELSON_R1 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 1034 | 204.8 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 8 | high | NELSON_R1 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 1164 | 207.5 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 9 | high | NELSON_R1 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 1319 | 179.2 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 10 | high | NELSON_R1 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 1410 | 200.2 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 11 | high | NELSON_R1 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 1559 | 177.9 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 12 | high | NELSON_R1 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 1711 | 178.6 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 13 | high | NELSON_R1 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | __ALL__ | 12 | 9 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 14 | high | NELSON_R1 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | __ALL__ | 175 | 9 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 15 | high | NELSON_R1 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | __ALL__ | 1712 | 68.9 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 16 | high | NELSON_R5 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 261 | 206.1 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 17 | high | NELSON_R5 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 349 | 205.4 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 18 | high | NELSON_R5 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 561 | 206 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 19 | high | NELSON_R5 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 712 | 205.1 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 20 | high | NELSON_R5 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 1048 | 17.4 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 21 | high | NELSON_R5 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 1161 | 209.2 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 22 | high | NELSON_R5 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 1319 | 179.2 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 23 | high | NELSON_R5 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 1410 | 200.2 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 24 | high | NELSON_R5 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 1474 | 180.3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 25 | high | NELSON_R5 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | __ALL__ | 96 | 4 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 26 | high | NELSON_R5 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | __ALL__ | 537 | 7 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 27 | high | NELSON_R5 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | __ALL__ | 626 | 7 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 28 | high | NELSON_R5 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | __ALL__ | 906 | 4 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 29 | high | NELSON_R5 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | __ALL__ | 990 | 0 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 30 | high | NELSON_R5 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | __ALL__ | 1677 | 65.5 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 31 | high | NELSON_R6 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 12 | 206.2 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 32 | high | NELSON_R6 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 254 | 205.8 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 33 | high | NELSON_R6 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 367 | 205.3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 34 | high | NELSON_R6 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 506 | 205.6 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 35 | high | NELSON_R6 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 712 | 205.1 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 36 | high | NELSON_R6 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 830 | 206.4 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 37 | high | NELSON_R6 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 988 | 205.5 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 38 | high | NELSON_R6 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 1161 | 209.2 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 39 | high | NELSON_R6 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 1319 | 179.2 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 40 | high | NELSON_R6 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 1410 | 200.2 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 41 | high | NELSON_R6 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | __ALL__ | 298 | 3 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 42 | high | NELSON_R6 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | __ALL__ | 443 | 2 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 43 | high | NELSON_R6 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | __ALL__ | 1677 | 65.5 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 44 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 1053 | - | __ALL__ 组在第 1053 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 45 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 1099 | - | __ALL__ 组在第 1099 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 46 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 1114 | - | __ALL__ 组在第 1114 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 47 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 1260 | - | __ALL__ 组在第 1260 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 48 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 1320 | - | __ALL__ 组在第 1320 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 49 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 1339 | - | __ALL__ 组在第 1339 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 50 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 1422 | - | __ALL__ 组在第 1422 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 51 | warn | VARIANCE_RATIO_HIGH | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | - | 18.48 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 稳态段标准差为基线的 45.7 倍，离散度显著升高，建议检查波动来源 |
| 52 | warn | VARIANCE_RATIO_HIGH | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | __ALL__ | - | 9.026 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) 稳态段标准差为基线的 5.9 倍，离散度显著升高，建议检查波动来源 |
| 53 | warn | NELSON_R2 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 42 | 205.3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 54 | warn | NELSON_R2 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 183 | 206.8 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 55 | warn | NELSON_R2 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 687 | 205.8 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 56 | warn | NELSON_R2 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 1174 | 201.1 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 57 | warn | NELSON_R2 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 1420 | 152 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 58 | warn | NELSON_R2 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | __ALL__ | 133 | 6 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 59 | warn | NELSON_R2 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | __ALL__ | 419 | 4 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 60 | warn | NELSON_R2 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | __ALL__ | 927 | 4 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 61 | warn | NELSON_R2 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | __ALL__ | 1051 | 3 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 62 | warn | NELSON_R2 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | __ALL__ | 1246 | 4 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 63 | warn | NELSON_R2 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | __ALL__ | 1421 | 3 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 64 | warn | NELSON_R2 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | __ALL__ | 1685 | 64.2 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 65 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 1086 | 180.1 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 66 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 1166 | 205.8 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 67 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 1418 | 126.4 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 68 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 1501 | 180.2 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 69 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 1709 | 178.3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |


> 级别语义：`info` 记录级 / `warn` 趋势与待确认趋势 / `high` 统计异常 / `critical` 越规格。
> 本系统为纯分析系统：所有告警仅为建议核查项，不下发任何参数，动作决策由产线（AWS 侧）做出。

## 二、稳态映射（C3）

- **__ALL__**：steady=1713

## 三、操作窗口投影（C2）

- **C2 漂移投影未启用**：基线中无 operating_windows —— 构建基线时传入 --doe-run-dir 注册 DOE 先验操作窗即可启用（C2 drift projection disabled: no operating_windows in baseline (build with --doe-run-dir to enable)）

## 四、防风暴抑制

合并触发 10 组同 key 重复；静默期 30 行；同类抑制窗口 60 分钟；迟滞 5 点

## 五、告警事件摘要（incidents）

| 事件 | 参数 | 类别 | 峰值级别 | 跨度(行) | 告警数 | 规则 |
|------|------|------|----------|----------|--------|------|
| EVT-20261006032354-017 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | spc | high | 240 | 11 | NELSON_R1、NELSON_R5、NELSON_R6… |
| EVT-20261006032354-011 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | spc | high | 186 | 9 | NELSON_R6、NELSON_R1、NELSON_R5… |
| EVT-20261006032354-005 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | spc | high | 184 | 5 | NELSON_R2、NELSON_R6、NELSON_R5 |
| EVT-20261006032354-003 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | spc | high | 163 | 4 | NELSON_R1、NELSON_R5、NELSON_R2 |
| EVT-20261006032354-007 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | spc | high | 207 | 4 | NELSON_R2、NELSON_R6、NELSON_R5 |
| EVT-20261006032354-009 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | spc | high | 143 | 4 | NELSON_R2、NELSON_R5、NELSON_R6 |
| EVT-20261006032354-010 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | spc | high | 145 | 4 | NELSON_R5、NELSON_R2 |
| EVT-20261006032354-020 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | spc | high | 35 | 4 | NELSON_R5、NELSON_R6、NELSON_R2… |
| EVT-20261006032354-004 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | spc | high | 40 | 3 | NELSON_R6、NELSON_R2、NELSON_R1 |
| EVT-20261006032354-008 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | spc | high | 55 | 2 | NELSON_R6、NELSON_R5 |
| EVT-20261006032354-014 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | multivariate | high | 112 | 2 | ROBUST_Z_OUTLIER |
| EVT-20261006032354-022 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | spc | high | 2 | 2 | NELSON_R3、NELSON_R1 |

（其余 10 个事件见 alert.json 的 events 数组；完整逐段告警在 alerts 数组，契约不变）

## 六、建议后续动作

- 有 `high`/`critical` 告警：按告警中的 `suggested_check` 现场核查；需要根因分析时转 `industrial-diagnostician`，需要参数窗口/工况数据分析时转 `industrial-doe-analyzer`。
- 事件摘要按峰值级别与告警数排序；完整逐段告警在 alert.json 的 `alerts` 数组（契约不变），事件视图在 `events` 数组。
- 本报告由脚本生成（`authored_by: script`）；代理只允许追加中文 `interpretation` 注记，禁止改动任何数值字段。
