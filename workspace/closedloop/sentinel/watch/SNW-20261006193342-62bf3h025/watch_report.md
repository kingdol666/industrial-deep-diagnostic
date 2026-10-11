# 产线哨兵巡检报告（watch 模式）

- **生成时间**：2026-10-06T19:33:42.999638+00:00
- **总体状态**：**alert** · 告警数 **120**
- **数据**：`D:\codes\industrial-deep-diagnostic\workspace\aw-exchange\watch_full_ascii2.csv`（11083 行；时间列 time；分组列 -）
- **基线**：模式：prior（v1.0.0），路径：D:\codes\industrial-deep-diagnostic\workspace\closedloop\sentinel\baselines\ln-d7e0a2a2\watch_baseline.json
- **耗时**：102 ms（零 LLM / 零网络，全部统计由确定性脚本计算）


## 一、告警清单

| # | 级别 | 规则 | 参数/指标 | 分组 | 位置 | 观测值 | 建议 |
|---|------|------|-----------|------|------|--------|------|
| 1 | high | ROBUST_Z_OUTLIER | dot_count | __ALL__ | 0 | 65.5 | dot_count 稳健 z 分数 \|27.98\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 2 | high | ROBUST_Z_OUTLIER | melt_temp | __ALL__ | 5103 | 30.8 | melt_temp 稳健 z 分数 \|-268.42\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 3 | high | ROBUST_Z_OUTLIER | melt_temp | __ALL__ | 6075 | 198.6 | melt_temp 稳健 z 分数 \|-13.95\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 4 | high | ROBUST_Z_OUTLIER | melt_temp | __ALL__ | 7776 | 212.1 | melt_temp 稳健 z 分数 \|6.52\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 5 | high | ROBUST_Z_OUTLIER | melt_temp | __ALL__ | 7968 | 212.1 | melt_temp 稳健 z 分数 \|6.52\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 6 | high | ROBUST_Z_OUTLIER | melt_temp | __ALL__ | 8054 | 211.8 | melt_temp 稳健 z 分数 \|6.07\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 7 | high | ROBUST_Z_OUTLIER | melt_temp | __ALL__ | 8178 | 212.1 | melt_temp 稳健 z 分数 \|6.52\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 8 | high | ROBUST_Z_OUTLIER | melt_temp | __ALL__ | 8242 | 211.8 | melt_temp 稳健 z 分数 \|6.07\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 9 | high | ROBUST_Z_OUTLIER | melt_temp | __ALL__ | 8530 | 212.1 | melt_temp 稳健 z 分数 \|6.52\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 10 | high | ROBUST_Z_OUTLIER | melt_temp | __ALL__ | 8635 | 212.1 | melt_temp 稳健 z 分数 \|6.52\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 11 | high | ROBUST_Z_OUTLIER | melt_temp | __ALL__ | 8720 | 211.7 | melt_temp 稳健 z 分数 \|5.91\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 12 | high | ROBUST_Z_OUTLIER | melt_temp | __ALL__ | 9525 | 113.8 | melt_temp 稳健 z 分数 \|-142.55\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 13 | high | NELSON_R1 | dot_count | __ALL__ | 5102 | 65.5 | dot_count 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 14 | high | NELSON_R1 | dot_count | __ALL__ | 6570 | 9 | dot_count 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 15 | high | NELSON_R1 | dot_count | __ALL__ | 7270 | 9 | dot_count 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 16 | high | NELSON_R1 | dot_count | __ALL__ | 7991 | 9 | dot_count 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 17 | high | NELSON_R1 | dot_count | __ALL__ | 9477 | 9 | dot_count 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 18 | high | NELSON_R1 | dot_count | __ALL__ | 9619 | 10 | dot_count 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 19 | high | NELSON_R1 | dot_count | __ALL__ | 9705 | 9 | dot_count 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 20 | high | NELSON_R1 | dot_count | __ALL__ | 10260 | 9 | dot_count 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 21 | high | NELSON_R1 | dot_count | __ALL__ | 10579 | 9 | dot_count 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 22 | high | NELSON_R1 | dot_count | __ALL__ | 10657 | 10 | dot_count 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 23 | high | NELSON_R1 | melt_temp | __ALL__ | 8843 | 209.4 | melt_temp 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 24 | high | NELSON_R1 | melt_temp | __ALL__ | 11022 | 206.6 | melt_temp 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 25 | high | NELSON_R5 | dot_count | __ALL__ | 5103 | 3 | dot_count 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 26 | high | NELSON_R5 | dot_count | __ALL__ | 6332 | 3 | dot_count 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 27 | high | NELSON_R5 | dot_count | __ALL__ | 6537 | 8 | dot_count 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 28 | high | NELSON_R5 | dot_count | __ALL__ | 6628 | 7 | dot_count 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 29 | high | NELSON_R5 | dot_count | __ALL__ | 6721 | 2 | dot_count 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 30 | high | NELSON_R5 | dot_count | __ALL__ | 6859 | 4 | dot_count 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 31 | high | NELSON_R5 | dot_count | __ALL__ | 7343 | 1 | dot_count 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 32 | high | NELSON_R5 | dot_count | __ALL__ | 7495 | 4 | dot_count 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 33 | high | NELSON_R5 | dot_count | __ALL__ | 7569 | 7 | dot_count 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 34 | high | NELSON_R5 | dot_count | __ALL__ | 7775 | 6 | dot_count 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 35 | high | NELSON_R5 | dot_count | __ALL__ | 7960 | 4 | dot_count 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 36 | high | NELSON_R5 | dot_count | __ALL__ | 8096 | 8 | dot_count 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 37 | high | NELSON_R5 | dot_count | __ALL__ | 8230 | 5 | dot_count 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 38 | high | NELSON_R5 | dot_count | __ALL__ | 8900 | 4 | dot_count 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 39 | high | NELSON_R5 | dot_count | __ALL__ | 9056 | 0 | dot_count 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 40 | high | NELSON_R5 | dot_count | __ALL__ | 9163 | 4 | dot_count 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 41 | high | NELSON_R5 | dot_count | __ALL__ | 9254 | 4 | dot_count 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 42 | high | NELSON_R5 | dot_count | __ALL__ | 9620 | 3 | dot_count 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 43 | high | NELSON_R5 | dot_count | __ALL__ | 10080 | 7 | dot_count 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 44 | high | NELSON_R5 | dot_count | __ALL__ | 10201 | 0 | dot_count 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 45 | high | NELSON_R5 | dot_count | __ALL__ | 10268 | 3 | dot_count 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 46 | high | NELSON_R5 | dot_count | __ALL__ | 10460 | 8 | dot_count 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 47 | high | NELSON_R5 | dot_count | __ALL__ | 10626 | 1 | dot_count 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 48 | high | NELSON_R5 | dot_count | __ALL__ | 10780 | 7 | dot_count 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 49 | high | NELSON_R5 | dot_count | __ALL__ | 10980 | 7 | dot_count 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 50 | high | NELSON_R5 | melt_temp | __ALL__ | 8850 | 208.9 | melt_temp 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 51 | high | NELSON_R6 | dot_count | __ALL__ | 5103 | 3 | dot_count 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 52 | high | NELSON_R6 | dot_count | __ALL__ | 6376 | 6 | dot_count 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 53 | high | NELSON_R6 | dot_count | __ALL__ | 6630 | 2 | dot_count 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 54 | high | NELSON_R6 | dot_count | __ALL__ | 6914 | 6 | dot_count 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 55 | high | NELSON_R6 | dot_count | __ALL__ | 7089 | 5 | dot_count 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 56 | high | NELSON_R6 | dot_count | __ALL__ | 7226 | 1 | dot_count 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 57 | high | NELSON_R6 | dot_count | __ALL__ | 7344 | 2 | dot_count 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 58 | high | NELSON_R6 | dot_count | __ALL__ | 8098 | 6 | dot_count 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 59 | high | NELSON_R6 | dot_count | __ALL__ | 8246 | 2 | dot_count 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 60 | high | NELSON_R6 | dot_count | __ALL__ | 8427 | 6 | dot_count 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 61 | high | NELSON_R6 | dot_count | __ALL__ | 8804 | 2 | dot_count 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 62 | high | NELSON_R6 | dot_count | __ALL__ | 9208 | 2 | dot_count 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 63 | high | NELSON_R6 | dot_count | __ALL__ | 9299 | 2 | dot_count 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 64 | high | NELSON_R6 | dot_count | __ALL__ | 9414 | 6 | dot_count 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 65 | high | NELSON_R6 | dot_count | __ALL__ | 9718 | 6 | dot_count 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 66 | high | NELSON_R6 | dot_count | __ALL__ | 10081 | 3 | dot_count 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 67 | high | NELSON_R6 | dot_count | __ALL__ | 10175 | 2 | dot_count 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 68 | high | NELSON_R6 | dot_count | __ALL__ | 10273 | 7 | dot_count 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 69 | high | NELSON_R6 | dot_count | __ALL__ | 10397 | 5 | dot_count 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 70 | high | NELSON_R6 | dot_count | __ALL__ | 10460 | 8 | dot_count 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 71 | high | NELSON_R6 | dot_count | __ALL__ | 10593 | 3 | dot_count 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 72 | high | NELSON_R6 | dot_count | __ALL__ | 11020 | 2 | dot_count 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 73 | high | NELSON_R6 | melt_temp | __ALL__ | 8854 | 208.2 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 74 | high | NELSON_R6 | melt_temp | __ALL__ | 10965 | 207.3 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 75 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 10899 | - | __ALL__ 组在第 10899 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 76 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 5108 | - | __ALL__ 组在第 5108 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 77 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 5125 | - | __ALL__ 组在第 5125 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 78 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 7613 | - | __ALL__ 组在第 7613 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 79 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 8811 | - | __ALL__ 组在第 8811 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 80 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 9489 | - | __ALL__ 组在第 9489 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 81 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 9553 | - | __ALL__ 组在第 9553 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 82 | warn | VARIANCE_RATIO_HIGH | dot_count | __ALL__ | - | 30.56 | dot_count 稳态段标准差为基线的 20.6 倍，离散度显著升高，建议检查波动来源 |
| 83 | warn | VARIANCE_RATIO_HIGH | melt_temp | __ALL__ | - | 8.901 | melt_temp 稳态段标准差为基线的 22.2 倍，离散度显著升高，建议检查波动来源 |
| 84 | warn | NELSON_R2 | dot_count | __ALL__ | 8 | 65.5 | dot_count 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 85 | warn | NELSON_R2 | dot_count | __ALL__ | 6690 | 4 | dot_count 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 86 | warn | NELSON_R2 | dot_count | __ALL__ | 6913 | 6 | dot_count 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 87 | warn | NELSON_R2 | dot_count | __ALL__ | 7105 | 2 | dot_count 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 88 | warn | NELSON_R2 | dot_count | __ALL__ | 7253 | 3 | dot_count 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 89 | warn | NELSON_R2 | dot_count | __ALL__ | 7433 | 2 | dot_count 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 90 | warn | NELSON_R2 | dot_count | __ALL__ | 7578 | 0 | dot_count 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 91 | warn | NELSON_R2 | dot_count | __ALL__ | 7682 | 4 | dot_count 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 92 | warn | NELSON_R2 | dot_count | __ALL__ | 7930 | 3 | dot_count 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 93 | warn | NELSON_R2 | dot_count | __ALL__ | 8151 | 2 | dot_count 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 94 | warn | NELSON_R2 | dot_count | __ALL__ | 8371 | 4 | dot_count 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 95 | warn | NELSON_R2 | dot_count | __ALL__ | 8549 | 1 | dot_count 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 96 | warn | NELSON_R2 | dot_count | __ALL__ | 8740 | 3 | dot_count 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 97 | warn | NELSON_R2 | dot_count | __ALL__ | 8895 | 4 | dot_count 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 98 | warn | NELSON_R2 | dot_count | __ALL__ | 9000 | 4 | dot_count 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 99 | warn | NELSON_R2 | dot_count | __ALL__ | 9340 | 4 | dot_count 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 100 | warn | NELSON_R2 | dot_count | __ALL__ | 9535 | 3 | dot_count 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 101 | warn | NELSON_R2 | dot_count | __ALL__ | 9717 | 2 | dot_count 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 102 | warn | NELSON_R2 | dot_count | __ALL__ | 9835 | 3 | dot_count 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 103 | warn | NELSON_R2 | dot_count | __ALL__ | 9980 | 2 | dot_count 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 104 | warn | NELSON_R2 | dot_count | __ALL__ | 10358 | 4 | dot_count 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 105 | warn | NELSON_R2 | dot_count | __ALL__ | 10756 | 2 | dot_count 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 106 | warn | NELSON_R2 | dot_count | __ALL__ | 10874 | 4 | dot_count 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 107 | warn | NELSON_R2 | melt_temp | __ALL__ | 8 | 198.8 | melt_temp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 108 | warn | NELSON_R2 | melt_temp | __ALL__ | 8861 | 208.1 | melt_temp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 109 | warn | NELSON_R2 | melt_temp | __ALL__ | 9091 | 208.4 | melt_temp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 110 | warn | NELSON_R3 | melt_temp | __ALL__ | 890 | 199.4 | melt_temp 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 111 | warn | NELSON_R3 | melt_temp | __ALL__ | 2537 | 200.3 | melt_temp 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 112 | warn | NELSON_R3 | melt_temp | __ALL__ | 3225 | 199.4 | melt_temp 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 113 | warn | NELSON_R3 | melt_temp | __ALL__ | 4037 | 199.4 | melt_temp 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 114 | warn | NELSON_R3 | melt_temp | __ALL__ | 4340 | 200.8 | melt_temp 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 115 | warn | NELSON_R3 | melt_temp | __ALL__ | 7611 | 203 | melt_temp 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 116 | warn | NELSON_R3 | melt_temp | __ALL__ | 8874 | 207.9 | melt_temp 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 117 | warn | NELSON_R3 | melt_temp | __ALL__ | 9354 | 208.8 | melt_temp 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 118 | warn | NELSON_R3 | melt_temp | __ALL__ | 9482 | 167.2 | melt_temp 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 119 | warn | NELSON_R3 | melt_temp | __ALL__ | 9550 | 148.2 | melt_temp 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 120 | warn | NELSON_R3 | melt_temp | __ALL__ | 10897 | 198.4 | melt_temp 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |


> 级别语义：`info` 记录级 / `warn` 趋势与待确认趋势 / `high` 统计异常 / `critical` 越规格。
> 本系统为纯分析系统：所有告警仅为建议核查项，不下发任何参数，动作决策由产线（AWS 侧）做出。

## 二、稳态映射（C3）

- **__ALL__**：steady=11083

## 三、操作窗口投影（C2）

- **C2 漂移投影未启用**：基线中无 operating_windows —— 构建基线时传入 --doe-run-dir 注册 DOE 先验操作窗即可启用（C2 drift projection disabled: no operating_windows in baseline (build with --doe-run-dir to enable)）

## 四、防风暴抑制

合并触发 10 组同 key 重复；静默期 30 行；同类抑制窗口 60 分钟；迟滞 5 点

## 五、告警事件摘要（incidents）

| 事件 | 参数 | 类别 | 峰值级别 | 跨度(行) | 告警数 | 规则 |
|------|------|------|----------|----------|--------|------|
| EVT-20261006193342-037 | dot_count | spc | high | 1040 | 21 | NELSON_R2、NELSON_R5、NELSON_R6… |
| EVT-20261006193342-029 | dot_count | spc | high | 1095 | 20 | NELSON_R2、NELSON_R6、NELSON_R5… |
| EVT-20261006193342-019 | dot_count | spc | high | 549 | 11 | NELSON_R6、NELSON_R2、NELSON_R1… |
| EVT-20261006193342-023 | dot_count | spc | high | 316 | 8 | NELSON_R2、NELSON_R5、NELSON_R1… |
| EVT-20261006193342-016 | dot_count | spc | high | 184 | 6 | NELSON_R5、NELSON_R1、NELSON_R6… |
| EVT-20261006193342-031 | melt_temp | spc | high | 31 | 5 | NELSON_R1、NELSON_R5、NELSON_R6… |
| EVT-20261006193342-011 | dot_count | spc | high | 1 | 3 | NELSON_R1、NELSON_R5、NELSON_R6 |
| EVT-20261006193342-017 | dot_count | spc | high | 55 | 3 | NELSON_R5、NELSON_R2、NELSON_R6 |
| EVT-20261006193342-027 | melt_temp | multivariate | high | 190 | 3 | ROBUST_Z_OUTLIER |
| EVT-20261006193342-038 | melt_temp | spc | high | 125 | 3 | NELSON_R3、NELSON_R6、NELSON_R1 |
| EVT-20261006193342-015 | dot_count | spc | high | 44 | 2 | NELSON_R5、NELSON_R6 |
| EVT-20261006193342-018 | dot_count | spc | high | 16 | 2 | NELSON_R6、NELSON_R2 |

（其余 27 个事件见 alert.json 的 events 数组；完整逐段告警在 alerts 数组，契约不变）

## 六、建议后续动作

- 有 `high`/`critical` 告警：按告警中的 `suggested_check` 现场核查；需要根因分析时转 `industrial-diagnostician`，需要参数窗口/工况数据分析时转 `industrial-doe-analyzer`。
- 事件摘要按峰值级别与告警数排序；完整逐段告警在 alert.json 的 `alerts` 数组（契约不变），事件视图在 `events` 数组。
- 本报告由脚本生成（`authored_by: script`）；代理只允许追加中文 `interpretation` 注记，禁止改动任何数值字段。
