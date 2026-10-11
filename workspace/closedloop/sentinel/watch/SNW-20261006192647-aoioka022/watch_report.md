# 产线哨兵巡检报告（watch 模式）

- **生成时间**：2026-10-06T19:26:47.812953+00:00
- **总体状态**：**alert** · 告警数 **107**
- **数据**：`D:\codes\industrial-deep-diagnostic\workspace\aw-exchange\merged_full_ascii.csv`（5000 行；时间列 time；分组列 -）
- **基线**：模式：prior（v1.0.0），路径：D:\codes\industrial-deep-diagnostic\workspace\closedloop\sentinel\baselines\ln-d7e0a2a2\watch_baseline.json
- **耗时**：59 ms（零 LLM / 零网络，全部统计由确定性脚本计算）


## 一、告警清单

| # | 级别 | 规则 | 参数/指标 | 分组 | 位置 | 观测值 | 建议 |
|---|------|------|-----------|------|------|--------|------|
| 1 | high | ROBUST_Z_OUTLIER | melt_temp | __ALL__ | 169 | 198.8 | melt_temp 稳健 z 分数 \|-13.65\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 2 | high | ROBUST_Z_OUTLIER | melt_temp | __ALL__ | 1692 | 212.1 | melt_temp 稳健 z 分数 \|6.52\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 3 | high | ROBUST_Z_OUTLIER | melt_temp | __ALL__ | 1884 | 212.1 | melt_temp 稳健 z 分数 \|6.52\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 4 | high | ROBUST_Z_OUTLIER | melt_temp | __ALL__ | 1970 | 211.8 | melt_temp 稳健 z 分数 \|6.07\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 5 | high | ROBUST_Z_OUTLIER | melt_temp | __ALL__ | 2094 | 212.1 | melt_temp 稳健 z 分数 \|6.52\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 6 | high | ROBUST_Z_OUTLIER | melt_temp | __ALL__ | 2158 | 211.8 | melt_temp 稳健 z 分数 \|6.07\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 7 | high | ROBUST_Z_OUTLIER | melt_temp | __ALL__ | 2446 | 212.1 | melt_temp 稳健 z 分数 \|6.52\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 8 | high | ROBUST_Z_OUTLIER | melt_temp | __ALL__ | 2551 | 212.1 | melt_temp 稳健 z 分数 \|6.52\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 9 | high | ROBUST_Z_OUTLIER | melt_temp | __ALL__ | 2636 | 211.7 | melt_temp 稳健 z 分数 \|5.91\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 10 | high | ROBUST_Z_OUTLIER | melt_temp | __ALL__ | 3441 | 113.8 | melt_temp 稳健 z 分数 \|-142.55\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 11 | high | NELSON_R1 | dot_count | __ALL__ | 486 | 9 | dot_count 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 12 | high | NELSON_R1 | dot_count | __ALL__ | 1186 | 9 | dot_count 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 13 | high | NELSON_R1 | dot_count | __ALL__ | 1907 | 9 | dot_count 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 14 | high | NELSON_R1 | dot_count | __ALL__ | 3393 | 9 | dot_count 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 15 | high | NELSON_R1 | dot_count | __ALL__ | 3535 | 10 | dot_count 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 16 | high | NELSON_R1 | dot_count | __ALL__ | 3621 | 9 | dot_count 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 17 | high | NELSON_R1 | dot_count | __ALL__ | 4176 | 9 | dot_count 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 18 | high | NELSON_R1 | dot_count | __ALL__ | 4495 | 9 | dot_count 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 19 | high | NELSON_R1 | dot_count | __ALL__ | 4573 | 10 | dot_count 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 20 | high | NELSON_R1 | melt_temp | __ALL__ | 2759 | 209.4 | melt_temp 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 21 | high | NELSON_R1 | melt_temp | __ALL__ | 4938 | 206.6 | melt_temp 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 22 | high | NELSON_R5 | dot_count | __ALL__ | 248 | 3 | dot_count 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 23 | high | NELSON_R5 | dot_count | __ALL__ | 453 | 8 | dot_count 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 24 | high | NELSON_R5 | dot_count | __ALL__ | 544 | 7 | dot_count 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 25 | high | NELSON_R5 | dot_count | __ALL__ | 637 | 2 | dot_count 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 26 | high | NELSON_R5 | dot_count | __ALL__ | 775 | 4 | dot_count 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 27 | high | NELSON_R5 | dot_count | __ALL__ | 1259 | 1 | dot_count 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 28 | high | NELSON_R5 | dot_count | __ALL__ | 1411 | 4 | dot_count 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 29 | high | NELSON_R5 | dot_count | __ALL__ | 1485 | 7 | dot_count 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 30 | high | NELSON_R5 | dot_count | __ALL__ | 1691 | 6 | dot_count 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 31 | high | NELSON_R5 | dot_count | __ALL__ | 1876 | 4 | dot_count 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 32 | high | NELSON_R5 | dot_count | __ALL__ | 2012 | 8 | dot_count 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 33 | high | NELSON_R5 | dot_count | __ALL__ | 2146 | 5 | dot_count 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 34 | high | NELSON_R5 | dot_count | __ALL__ | 2816 | 4 | dot_count 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 35 | high | NELSON_R5 | dot_count | __ALL__ | 2972 | 0 | dot_count 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 36 | high | NELSON_R5 | dot_count | __ALL__ | 3079 | 4 | dot_count 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 37 | high | NELSON_R5 | dot_count | __ALL__ | 3170 | 4 | dot_count 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 38 | high | NELSON_R5 | dot_count | __ALL__ | 3536 | 3 | dot_count 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 39 | high | NELSON_R5 | dot_count | __ALL__ | 3996 | 7 | dot_count 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 40 | high | NELSON_R5 | dot_count | __ALL__ | 4117 | 0 | dot_count 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 41 | high | NELSON_R5 | dot_count | __ALL__ | 4184 | 3 | dot_count 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 42 | high | NELSON_R5 | dot_count | __ALL__ | 4376 | 8 | dot_count 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 43 | high | NELSON_R5 | dot_count | __ALL__ | 4542 | 1 | dot_count 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 44 | high | NELSON_R5 | dot_count | __ALL__ | 4696 | 7 | dot_count 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 45 | high | NELSON_R5 | dot_count | __ALL__ | 4896 | 7 | dot_count 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 46 | high | NELSON_R5 | melt_temp | __ALL__ | 2766 | 208.9 | melt_temp 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 47 | high | NELSON_R6 | dot_count | __ALL__ | 292 | 6 | dot_count 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 48 | high | NELSON_R6 | dot_count | __ALL__ | 546 | 2 | dot_count 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 49 | high | NELSON_R6 | dot_count | __ALL__ | 830 | 6 | dot_count 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 50 | high | NELSON_R6 | dot_count | __ALL__ | 1005 | 5 | dot_count 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 51 | high | NELSON_R6 | dot_count | __ALL__ | 1142 | 1 | dot_count 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 52 | high | NELSON_R6 | dot_count | __ALL__ | 1260 | 2 | dot_count 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 53 | high | NELSON_R6 | dot_count | __ALL__ | 2014 | 6 | dot_count 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 54 | high | NELSON_R6 | dot_count | __ALL__ | 2162 | 2 | dot_count 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 55 | high | NELSON_R6 | dot_count | __ALL__ | 2343 | 6 | dot_count 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 56 | high | NELSON_R6 | dot_count | __ALL__ | 2720 | 2 | dot_count 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 57 | high | NELSON_R6 | dot_count | __ALL__ | 3124 | 2 | dot_count 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 58 | high | NELSON_R6 | dot_count | __ALL__ | 3215 | 2 | dot_count 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 59 | high | NELSON_R6 | dot_count | __ALL__ | 3330 | 6 | dot_count 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 60 | high | NELSON_R6 | dot_count | __ALL__ | 3634 | 6 | dot_count 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 61 | high | NELSON_R6 | dot_count | __ALL__ | 3997 | 3 | dot_count 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 62 | high | NELSON_R6 | dot_count | __ALL__ | 4091 | 2 | dot_count 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 63 | high | NELSON_R6 | dot_count | __ALL__ | 4189 | 7 | dot_count 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 64 | high | NELSON_R6 | dot_count | __ALL__ | 4313 | 5 | dot_count 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 65 | high | NELSON_R6 | dot_count | __ALL__ | 4376 | 8 | dot_count 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 66 | high | NELSON_R6 | dot_count | __ALL__ | 4509 | 3 | dot_count 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 67 | high | NELSON_R6 | dot_count | __ALL__ | 4936 | 2 | dot_count 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 68 | high | NELSON_R6 | melt_temp | __ALL__ | 2770 | 208.2 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 69 | high | NELSON_R6 | melt_temp | __ALL__ | 4881 | 207.3 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 70 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 114 | - | __ALL__ 组在第 114 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 71 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 1529 | - | __ALL__ 组在第 1529 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 72 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 2727 | - | __ALL__ 组在第 2727 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 73 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 3405 | - | __ALL__ 组在第 3405 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 74 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 3474 | - | __ALL__ 组在第 3474 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 75 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 4820 | - | __ALL__ 组在第 4820 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 76 | warn | VARIANCE_RATIO_HIGH | melt_temp | __ALL__ | - | 10 | melt_temp 稳态段标准差为基线的 24.9 倍，离散度显著升高，建议检查波动来源 |
| 77 | warn | NELSON_R2 | dot_count | __ALL__ | 606 | 4 | dot_count 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 78 | warn | NELSON_R2 | dot_count | __ALL__ | 829 | 6 | dot_count 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 79 | warn | NELSON_R2 | dot_count | __ALL__ | 1021 | 2 | dot_count 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 80 | warn | NELSON_R2 | dot_count | __ALL__ | 1169 | 3 | dot_count 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 81 | warn | NELSON_R2 | dot_count | __ALL__ | 1349 | 2 | dot_count 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 82 | warn | NELSON_R2 | dot_count | __ALL__ | 1494 | 0 | dot_count 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 83 | warn | NELSON_R2 | dot_count | __ALL__ | 1598 | 4 | dot_count 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 84 | warn | NELSON_R2 | dot_count | __ALL__ | 1846 | 3 | dot_count 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 85 | warn | NELSON_R2 | dot_count | __ALL__ | 2067 | 2 | dot_count 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 86 | warn | NELSON_R2 | dot_count | __ALL__ | 2287 | 4 | dot_count 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 87 | warn | NELSON_R2 | dot_count | __ALL__ | 2465 | 1 | dot_count 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 88 | warn | NELSON_R2 | dot_count | __ALL__ | 2656 | 3 | dot_count 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 89 | warn | NELSON_R2 | dot_count | __ALL__ | 2811 | 4 | dot_count 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 90 | warn | NELSON_R2 | dot_count | __ALL__ | 2916 | 4 | dot_count 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 91 | warn | NELSON_R2 | dot_count | __ALL__ | 3256 | 4 | dot_count 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 92 | warn | NELSON_R2 | dot_count | __ALL__ | 3451 | 3 | dot_count 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 93 | warn | NELSON_R2 | dot_count | __ALL__ | 3633 | 2 | dot_count 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 94 | warn | NELSON_R2 | dot_count | __ALL__ | 3751 | 3 | dot_count 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 95 | warn | NELSON_R2 | dot_count | __ALL__ | 3896 | 2 | dot_count 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 96 | warn | NELSON_R2 | dot_count | __ALL__ | 4274 | 4 | dot_count 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 97 | warn | NELSON_R2 | dot_count | __ALL__ | 4672 | 2 | dot_count 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 98 | warn | NELSON_R2 | dot_count | __ALL__ | 4790 | 4 | dot_count 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 99 | warn | NELSON_R2 | melt_temp | __ALL__ | 8 | 200.3 | melt_temp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 100 | warn | NELSON_R2 | melt_temp | __ALL__ | 2777 | 208.1 | melt_temp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 101 | warn | NELSON_R2 | melt_temp | __ALL__ | 3007 | 208.4 | melt_temp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 102 | warn | NELSON_R3 | melt_temp | __ALL__ | 1527 | 203 | melt_temp 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 103 | warn | NELSON_R3 | melt_temp | __ALL__ | 2790 | 207.9 | melt_temp 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 104 | warn | NELSON_R3 | melt_temp | __ALL__ | 3270 | 208.8 | melt_temp 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 105 | warn | NELSON_R3 | melt_temp | __ALL__ | 3398 | 167.2 | melt_temp 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 106 | warn | NELSON_R3 | melt_temp | __ALL__ | 3466 | 148.2 | melt_temp 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 107 | warn | NELSON_R3 | melt_temp | __ALL__ | 4813 | 198.4 | melt_temp 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |


> 级别语义：`info` 记录级 / `warn` 趋势与待确认趋势 / `high` 统计异常 / `critical` 越规格。
> 本系统为纯分析系统：所有告警仅为建议核查项，不下发任何参数，动作决策由产线（AWS 侧）做出。

## 二、稳态映射（C3）

- **__ALL__**：abnormal=70、marginal=16、shutdown=1、steady=4847、transition=66

## 三、操作窗口投影（C2）

- **C2 漂移投影未启用**：基线中无 operating_windows —— 构建基线时传入 --doe-run-dir 注册 DOE 先验操作窗即可启用（C2 drift projection disabled: no operating_windows in baseline (build with --doe-run-dir to enable)）

## 四、防风暴抑制

合并触发 10 组同 key 重复；静默期 30 行；同类抑制窗口 60 分钟；迟滞 5 点

## 五、告警事件摘要（incidents）

| 事件 | 参数 | 类别 | 峰值级别 | 跨度(行) | 告警数 | 规则 |
|------|------|------|----------|----------|--------|------|
| EVT-20261006192647-027 | dot_count | spc | high | 1040 | 21 | NELSON_R2、NELSON_R5、NELSON_R6… |
| EVT-20261006192647-019 | dot_count | spc | high | 1095 | 20 | NELSON_R2、NELSON_R6、NELSON_R5… |
| EVT-20261006192647-009 | dot_count | spc | high | 549 | 11 | NELSON_R6、NELSON_R2、NELSON_R1… |
| EVT-20261006192647-013 | dot_count | spc | high | 316 | 8 | NELSON_R2、NELSON_R5、NELSON_R1… |
| EVT-20261006192647-006 | dot_count | spc | high | 184 | 6 | NELSON_R5、NELSON_R1、NELSON_R6… |
| EVT-20261006192647-021 | melt_temp | spc | high | 31 | 5 | NELSON_R1、NELSON_R5、NELSON_R6… |
| EVT-20261006192647-007 | dot_count | spc | high | 55 | 3 | NELSON_R5、NELSON_R2、NELSON_R6 |
| EVT-20261006192647-017 | melt_temp | multivariate | high | 190 | 3 | ROBUST_Z_OUTLIER |
| EVT-20261006192647-028 | melt_temp | spc | high | 125 | 3 | NELSON_R3、NELSON_R6、NELSON_R1 |
| EVT-20261006192647-005 | dot_count | spc | high | 44 | 2 | NELSON_R5、NELSON_R6 |
| EVT-20261006192647-008 | dot_count | spc | high | 16 | 2 | NELSON_R6、NELSON_R2 |
| EVT-20261006192647-014 | melt_temp | multivariate | high | 86 | 2 | ROBUST_Z_OUTLIER |

（其余 17 个事件见 alert.json 的 events 数组；完整逐段告警在 alerts 数组，契约不变）

## 六、建议后续动作

- 有 `high`/`critical` 告警：按告警中的 `suggested_check` 现场核查；需要根因分析时转 `industrial-diagnostician`，需要参数窗口/工况数据分析时转 `industrial-doe-analyzer`。
- 事件摘要按峰值级别与告警数排序；完整逐段告警在 alert.json 的 `alerts` 数组（契约不变），事件视图在 `events` 数组。
- 本报告由脚本生成（`authored_by: script`）；代理只允许追加中文 `interpretation` 注记，禁止改动任何数值字段。
