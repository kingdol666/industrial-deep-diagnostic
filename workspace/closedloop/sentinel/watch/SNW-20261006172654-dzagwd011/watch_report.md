# 产线哨兵巡检报告（watch 模式）

- **生成时间**：2026-10-06T17:26:54.847209+00:00
- **总体状态**：**alert** · 告警数 **112**
- **数据**：`D:\codes\industrial-deep-diagnostic\workspace\aw-exchange\watch_ln-d7e0a2a2_rr-9b067_20261007T0116.csv`（5000 行；时间列 ts_ms；分组列 -）
- **基线**：模式：prior（v1.0.0），路径：D:\codes\industrial-deep-diagnostic\workspace\closedloop\sentinel\baselines\演示线1·挤出主机PLC(Modbus TCP)\watch_baseline.json
- **耗时**：34 ms（零 LLM / 零网络，全部统计由确定性脚本计算）


## 一、告警清单

| # | 级别 | 规则 | 参数/指标 | 分组 | 位置 | 观测值 | 建议 |
|---|------|------|-----------|------|------|--------|------|
| 1 | high | ROBUST_Z_OUTLIER | gel_count | __ALL__ | 115 | 65.5 | gel_count 稳健 z 分数 \|47.59\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 2 | high | ROBUST_Z_OUTLIER | gel_count | __ALL__ | 3946 | 0 | gel_count 稳健 z 分数 \|-3.93\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 3 | high | ROBUST_Z_OUTLIER | gel_count | __ALL__ | 4177 | 0 | gel_count 稳健 z 分数 \|-3.93\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 4 | high | ROBUST_Z_OUTLIER | gel_count | __ALL__ | 4316 | 0 | gel_count 稳健 z 分数 \|-3.93\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 5 | high | ROBUST_Z_OUTLIER | gel_count | __ALL__ | 4466 | 0 | gel_count 稳健 z 分数 \|-3.93\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 6 | high | ROBUST_Z_OUTLIER | gel_count | __ALL__ | 4582 | 0 | gel_count 稳健 z 分数 \|-3.93\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 7 | high | ROBUST_Z_OUTLIER | gel_count | __ALL__ | 4694 | 0 | gel_count 稳健 z 分数 \|-3.93\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 8 | high | ROBUST_Z_OUTLIER | gel_count | __ALL__ | 4822 | 0 | gel_count 稳健 z 分数 \|-3.93\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 9 | high | ROBUST_Z_OUTLIER | gel_count | __ALL__ | 4904 | 0 | gel_count 稳健 z 分数 \|-3.93\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 10 | high | ROBUST_Z_OUTLIER | melt_temp | __ALL__ | 2360 | 30.8 | melt_temp 稳健 z 分数 \|-256.59\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 11 | high | ROBUST_Z_OUTLIER | melt_temp | __ALL__ | 4990 | 211.7 | melt_temp 稳健 z 分数 \|17.74\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 12 | high | ROBUST_Z_OUTLIER | ts_ms | __ALL__ | 0 | 1.791e+12 | ts_ms 稳健 z 分数 \|-8.28\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 13 | high | NELSON_R1 | gel_count | __ALL__ | 4999 | 6 | gel_count 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 14 | high | NELSON_R1 | melt_temp | __ALL__ | 199 | 198.5 | melt_temp 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 15 | high | NELSON_R1 | melt_temp | __ALL__ | 1349 | 201.2 | melt_temp 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 16 | high | NELSON_R1 | melt_temp | __ALL__ | 1500 | 201.6 | melt_temp 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 17 | high | NELSON_R1 | melt_temp | __ALL__ | 2383 | 201.2 | melt_temp 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 18 | high | NELSON_R1 | melt_temp | __ALL__ | 2501 | 201.3 | melt_temp 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 19 | high | NELSON_R1 | melt_temp | __ALL__ | 2633 | 201.1 | melt_temp 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 20 | high | NELSON_R1 | melt_temp | __ALL__ | 2742 | 201.1 | melt_temp 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 21 | high | NELSON_R1 | melt_temp | __ALL__ | 2915 | 201.2 | melt_temp 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 22 | high | NELSON_R1 | melt_temp | __ALL__ | 3190 | 201.1 | melt_temp 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 23 | high | NELSON_R1 | melt_temp | __ALL__ | 3314 | 198.6 | melt_temp 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 24 | high | NELSON_R1 | melt_temp | __ALL__ | 3381 | 201.1 | melt_temp 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 25 | high | NELSON_R1 | melt_temp | __ALL__ | 3751 | 201.1 | melt_temp 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 26 | high | NELSON_R1 | melt_temp | __ALL__ | 3846 | 201.1 | melt_temp 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 27 | high | NELSON_R1 | melt_temp | __ALL__ | 4277 | 201.1 | melt_temp 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 28 | high | NELSON_R1 | melt_temp | __ALL__ | 4825 | 201.1 | melt_temp 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 29 | high | NELSON_R1 | melt_temp | __ALL__ | 4999 | 211.4 | melt_temp 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 30 | high | NELSON_R1 | ts_ms | __ALL__ | 4999 | 1.791e+12 | ts_ms 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 31 | high | NELSON_R5 | gel_count | __ALL__ | 2360 | 3 | gel_count 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 32 | high | NELSON_R5 | gel_count | __ALL__ | 4999 | 6 | gel_count 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 33 | high | NELSON_R5 | melt_temp | __ALL__ | 489 | 200.7 | melt_temp 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 34 | high | NELSON_R5 | melt_temp | __ALL__ | 626 | 200.7 | melt_temp 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 35 | high | NELSON_R5 | melt_temp | __ALL__ | 1338 | 200.7 | melt_temp 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 36 | high | NELSON_R5 | melt_temp | __ALL__ | 2367 | 209.5 | melt_temp 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 37 | high | NELSON_R5 | melt_temp | __ALL__ | 2564 | 200.2 | melt_temp 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 38 | high | NELSON_R5 | melt_temp | __ALL__ | 2657 | 199.9 | melt_temp 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 39 | high | NELSON_R5 | melt_temp | __ALL__ | 2893 | 200.7 | melt_temp 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 40 | high | NELSON_R5 | melt_temp | __ALL__ | 3399 | 201.2 | melt_temp 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 41 | high | NELSON_R5 | melt_temp | __ALL__ | 3516 | 200.1 | melt_temp 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 42 | high | NELSON_R5 | melt_temp | __ALL__ | 4166 | 199.9 | melt_temp 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 43 | high | NELSON_R5 | melt_temp | __ALL__ | 4278 | 199.9 | melt_temp 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 44 | high | NELSON_R5 | melt_temp | __ALL__ | 4828 | 200.8 | melt_temp 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 45 | high | NELSON_R5 | melt_temp | __ALL__ | 4999 | 211.4 | melt_temp 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 46 | high | NELSON_R5 | ts_ms | __ALL__ | 2360 | 1.791e+12 | ts_ms 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 47 | high | NELSON_R5 | ts_ms | __ALL__ | 4999 | 1.791e+12 | ts_ms 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 48 | high | NELSON_R6 | gel_count | __ALL__ | 2360 | 3 | gel_count 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 49 | high | NELSON_R6 | gel_count | __ALL__ | 4999 | 6 | gel_count 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 50 | high | NELSON_R6 | melt_temp | __ALL__ | 539 | 200.7 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 51 | high | NELSON_R6 | melt_temp | __ALL__ | 703 | 200.6 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 52 | high | NELSON_R6 | melt_temp | __ALL__ | 883 | 200.6 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 53 | high | NELSON_R6 | melt_temp | __ALL__ | 1067 | 200.8 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 54 | high | NELSON_R6 | melt_temp | __ALL__ | 1144 | 199.1 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 55 | high | NELSON_R6 | melt_temp | __ALL__ | 1290 | 199.9 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 56 | high | NELSON_R6 | melt_temp | __ALL__ | 1676 | 200.6 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 57 | high | NELSON_R6 | melt_temp | __ALL__ | 2090 | 200.5 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 58 | high | NELSON_R6 | melt_temp | __ALL__ | 2285 | 200.5 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 59 | high | NELSON_R6 | melt_temp | __ALL__ | 2367 | 209.5 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 60 | high | NELSON_R6 | melt_temp | __ALL__ | 2585 | 199.9 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 61 | high | NELSON_R6 | melt_temp | __ALL__ | 2762 | 200.3 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 62 | high | NELSON_R6 | melt_temp | __ALL__ | 2885 | 200.3 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 63 | high | NELSON_R6 | melt_temp | __ALL__ | 3228 | 200.9 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 64 | high | NELSON_R6 | melt_temp | __ALL__ | 3390 | 199.7 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 65 | high | NELSON_R6 | melt_temp | __ALL__ | 3797 | 200.4 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 66 | high | NELSON_R6 | melt_temp | __ALL__ | 4075 | 200.6 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 67 | high | NELSON_R6 | melt_temp | __ALL__ | 4159 | 200.1 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 68 | high | NELSON_R6 | melt_temp | __ALL__ | 4750 | 199.9 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 69 | high | NELSON_R6 | melt_temp | __ALL__ | 4928 | 199.5 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 70 | high | NELSON_R6 | melt_temp | __ALL__ | 4999 | 211.4 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 71 | high | NELSON_R6 | ts_ms | __ALL__ | 2360 | 1.791e+12 | ts_ms 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 72 | high | NELSON_R6 | ts_ms | __ALL__ | 4999 | 1.791e+12 | ts_ms 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 73 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 115 | - | __ALL__ 组在第 115 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 74 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 135 | - | __ALL__ 组在第 135 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 75 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 368 | - | __ALL__ 组在第 368 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 76 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 393 | - | __ALL__ 组在第 393 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 77 | warn | VARIANCE_RATIO_HIGH | gel_count | __ALL__ | - | 30.41 | gel_count 稳态段标准差为基线的 35.5 倍，离散度显著升高，建议检查波动来源 |
| 78 | warn | VARIANCE_RATIO_HIGH | melt_temp | __ALL__ | - | 5.294 | melt_temp 稳态段标准差为基线的 13.1 倍，离散度显著升高，建议检查波动来源 |
| 79 | warn | VARIANCE_RATIO_HIGH | ts_ms | __ALL__ | - | 7.583e+06 | ts_ms 稳态段标准差为基线的 7.3 倍，离散度显著升高，建议检查波动来源 |
| 80 | warn | NELSON_R2 | gel_count | __ALL__ | 431 | 65.5 | gel_count 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 81 | warn | NELSON_R2 | gel_count | __ALL__ | 2368 | 5 | gel_count 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 82 | warn | NELSON_R2 | melt_temp | __ALL__ | 38 | 200.2 | melt_temp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 83 | warn | NELSON_R2 | melt_temp | __ALL__ | 840 | 200.3 | melt_temp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 84 | warn | NELSON_R2 | melt_temp | __ALL__ | 1019 | 200.7 | melt_temp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 85 | warn | NELSON_R2 | melt_temp | __ALL__ | 1130 | 200.2 | melt_temp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 86 | warn | NELSON_R2 | melt_temp | __ALL__ | 1314 | 200.5 | melt_temp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 87 | warn | NELSON_R2 | melt_temp | __ALL__ | 2086 | 200.4 | melt_temp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 88 | warn | NELSON_R2 | melt_temp | __ALL__ | 2375 | 203.6 | melt_temp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 89 | warn | NELSON_R2 | melt_temp | __ALL__ | 2528 | 200.5 | melt_temp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 90 | warn | NELSON_R2 | melt_temp | __ALL__ | 2888 | 200.6 | melt_temp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 91 | warn | NELSON_R2 | melt_temp | __ALL__ | 2962 | 200.7 | melt_temp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 92 | warn | NELSON_R2 | melt_temp | __ALL__ | 3283 | 200.2 | melt_temp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 93 | warn | NELSON_R2 | melt_temp | __ALL__ | 3528 | 200.2 | melt_temp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 94 | warn | NELSON_R2 | melt_temp | __ALL__ | 3664 | 200.4 | melt_temp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 95 | warn | NELSON_R2 | melt_temp | __ALL__ | 3787 | 200.1 | melt_temp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 96 | warn | NELSON_R2 | melt_temp | __ALL__ | 3972 | 200.4 | melt_temp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 97 | warn | NELSON_R2 | melt_temp | __ALL__ | 4159 | 200.1 | melt_temp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 98 | warn | NELSON_R2 | melt_temp | __ALL__ | 4327 | 200.9 | melt_temp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 99 | warn | NELSON_R2 | melt_temp | __ALL__ | 4521 | 200.1 | melt_temp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 100 | warn | NELSON_R2 | melt_temp | __ALL__ | 4600 | 200 | melt_temp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 101 | warn | NELSON_R2 | melt_temp | __ALL__ | 4748 | 200.5 | melt_temp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 102 | warn | NELSON_R2 | melt_temp | __ALL__ | 4927 | 200.7 | melt_temp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 103 | warn | NELSON_R2 | ts_ms | __ALL__ | 8 | 1.791e+12 | ts_ms 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 104 | warn | NELSON_R2 | ts_ms | __ALL__ | 431 | 1.791e+12 | ts_ms 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 105 | warn | NELSON_R2 | ts_ms | __ALL__ | 2368 | 1.791e+12 | ts_ms 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 106 | warn | NELSON_R3 | melt_temp | __ALL__ | 501 | 199.4 | melt_temp 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 107 | warn | NELSON_R3 | melt_temp | __ALL__ | 1303 | 199.4 | melt_temp 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 108 | warn | NELSON_R3 | melt_temp | __ALL__ | 1601 | 200.8 | melt_temp 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 109 | warn | NELSON_R3 | melt_temp | __ALL__ | 2365 | 95.3 | melt_temp 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 110 | warn | NELSON_R3 | melt_temp | __ALL__ | 4964 | 203 | melt_temp 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 111 | warn | NELSON_R3 | ts_ms | __ALL__ | 5 | 1.791e+12 | ts_ms 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 112 | warn | NELSON_R3 | ts_ms | __ALL__ | 428 | 1.791e+12 | ts_ms 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |


> 级别语义：`info` 记录级 / `warn` 趋势与待确认趋势 / `high` 统计异常 / `critical` 越规格。
> 本系统为纯分析系统：所有告警仅为建议核查项，不下发任何参数，动作决策由产线（AWS 侧）做出。

## 二、稳态映射（C3）

- **__ALL__**：steady=5000

## 三、操作窗口投影（C2）

- **C2 漂移投影未启用**：基线中无 operating_windows —— 构建基线时传入 --doe-run-dir 注册 DOE 先验操作窗即可启用（C2 drift projection disabled: no operating_windows in baseline (build with --doe-run-dir to enable)）

## 四、防风暴抑制

合并触发 14 组同 key 重复；静默期 30 行；同类抑制窗口 60 分钟；迟滞 5 点

## 五、告警事件摘要（incidents）

| 事件 | 参数 | 类别 | 峰值级别 | 跨度(行) | 告警数 | 规则 |
|------|------|------|----------|----------|--------|------|
| EVT-20261006172654-019 | melt_temp | spc | high | 477 | 14 | NELSON_R6、NELSON_R3、NELSON_R5… |
| EVT-20261006172654-032 | melt_temp | spc | high | 251 | 10 | NELSON_R2、NELSON_R6、NELSON_R1… |
| EVT-20261006172654-024 | melt_temp | spc | high | 338 | 9 | NELSON_R1、NELSON_R6、NELSON_R2… |
| EVT-20261006172654-027 | melt_temp | spc | high | 355 | 8 | NELSON_R2、NELSON_R6、NELSON_R5… |
| EVT-20261006172654-013 | melt_temp | spc | high | 214 | 5 | NELSON_R5、NELSON_R3、NELSON_R6 |
| EVT-20261006172654-016 | melt_temp | spc | high | 59 | 5 | NELSON_R6、NELSON_R3、NELSON_R2… |
| EVT-20261006172654-023 | melt_temp | spc | high | 77 | 5 | NELSON_R6、NELSON_R2、NELSON_R5… |
| EVT-20261006172654-025 | melt_temp | spc | high | 182 | 5 | NELSON_R2、NELSON_R1、NELSON_R6 |
| EVT-20261006172654-015 | melt_temp | spc | high | 125 | 4 | NELSON_R2、NELSON_R6 |
| EVT-20261006172654-017 | melt_temp | spc | high | 176 | 3 | NELSON_R1、NELSON_R3、NELSON_R6 |
| EVT-20261006172654-021 | gel_count | spc | high | 8 | 3 | NELSON_R5、NELSON_R6、NELSON_R2 |
| EVT-20261006172654-022 | ts_ms | spc | high | 8 | 3 | NELSON_R5、NELSON_R6、NELSON_R2 |

（其余 24 个事件见 alert.json 的 events 数组；完整逐段告警在 alerts 数组，契约不变）

## 六、建议后续动作

- 有 `high`/`critical` 告警：按告警中的 `suggested_check` 现场核查；需要根因分析时转 `industrial-diagnostician`，需要参数窗口/工况数据分析时转 `industrial-doe-analyzer`。
- 事件摘要按峰值级别与告警数排序；完整逐段告警在 alert.json 的 `alerts` 数组（契约不变），事件视图在 `events` 数组。
- 本报告由脚本生成（`authored_by: script`）；代理只允许追加中文 `interpretation` 注记，禁止改动任何数值字段。
