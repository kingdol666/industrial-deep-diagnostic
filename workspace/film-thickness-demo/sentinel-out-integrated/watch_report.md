# 产线哨兵巡检报告（watch 模式）

- **生成时间**：2026-10-01T12:38:16.388832+00:00
- **总体状态**：**alert** · 告警数 **141**
- **数据**：`D:\codes\myskills\industrial-deep-diagnostic\workspace\film-thickness-demo\aligned.csv`（1200 行；时间列 timestamp；分组列 -）
- **基线**：模式：prior（v1.0.0），路径：D:\codes\myskills\industrial-deep-diagnostic\workspace\film-thickness-demo\watch_baseline_integrated.json
- **耗时**：25 ms（零 LLM / 零网络，全部统计由确定性脚本计算）


## 一、告警清单

| # | 级别 | 规则 | 参数/指标 | 分组 | 位置 | 观测值 | 建议 |
|---|------|------|-----------|------|------|--------|------|
| 1 | high | ROBUST_Z_OUTLIER | dev_pos07 | __ALL__ | 464 | 0.9977 | dev_pos07 稳健 z 分数 \|3.51\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 2 | high | ROBUST_Z_OUTLIER | dev_pos07 | __ALL__ | 707 | 3.09 | dev_pos07 稳健 z 分数 \|11.07\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 3 | high | ROBUST_Z_OUTLIER | die_bolt_T3_pct | __ALL__ | 504 | 51.27 | die_bolt_T3_pct 稳健 z 分数 \|3.66\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 4 | high | ROBUST_Z_OUTLIER | die_bolt_T3_pct | __ALL__ | 1173 | 56.37 | die_bolt_T3_pct 稳健 z 分数 \|18.04\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 5 | high | ROBUST_Z_OUTLIER | mean_thk | __ALL__ | 595 | 49.75 | mean_thk 稳健 z 分数 \|3.57\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 6 | high | ROBUST_Z_OUTLIER | mean_thk | __ALL__ | 862 | 49.37 | mean_thk 稳健 z 分数 \|-3.60\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 7 | high | ROBUST_Z_OUTLIER | mean_thk | __ALL__ | 1194 | 48.62 | mean_thk 稳健 z 分数 \|-17.73\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 8 | high | ROBUST_Z_OUTLIER | melt_temp_C | __ALL__ | 829 | 285.8 | melt_temp_C 稳健 z 分数 \|3.53\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 9 | high | ROBUST_Z_OUTLIER | melt_temp_C | __ALL__ | 1187 | 287.8 | melt_temp_C 稳健 z 分数 \|12.55\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 10 | high | ROBUST_Z_OUTLIER | zone_L | __ALL__ | 496 | 49.65 | zone_L 稳健 z 分数 \|3.53\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 11 | high | ROBUST_Z_OUTLIER | zone_L | __ALL__ | 1199 | 48.39 | zone_L 稳健 z 分数 \|-12.19\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 12 | high | ROBUST_Z_OUTLIER | zone_R | __ALL__ | 805 | 49.1 | zone_R 稳健 z 分数 \|-3.58\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 13 | high | ROBUST_Z_OUTLIER | zone_R | __ALL__ | 1162 | 48.5 | zone_R 稳健 z 分数 \|-11.58\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 14 | high | NELSON_R1 | dev_pos07 | __ALL__ | 9 | -0.6013 | dev_pos07 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 15 | high | NELSON_R1 | dev_pos07 | __ALL__ | 460 | 0.7195 | dev_pos07 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 16 | high | NELSON_R1 | die_bolt_T3_pct | __ALL__ | 469 | 50.81 | die_bolt_T3_pct 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 17 | high | NELSON_R1 | die_bolt_T3_pct | __ALL__ | 948 | 54.16 | die_bolt_T3_pct 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 18 | high | NELSON_R1 | die_bolt_T3_pct | __ALL__ | 1104 | 55.91 | die_bolt_T3_pct 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 19 | high | NELSON_R1 | mean_thk | __ALL__ | 185 | 49.46 | mean_thk 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 20 | high | NELSON_R1 | mean_thk | __ALL__ | 480 | 49.67 | mean_thk 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 21 | high | NELSON_R1 | mean_thk | __ALL__ | 831 | 49.44 | mean_thk 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 22 | high | NELSON_R1 | mean_thk | __ALL__ | 968 | 49.03 | mean_thk 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 23 | high | NELSON_R1 | melt_temp_C | __ALL__ | 91 | 284.6 | melt_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 24 | high | NELSON_R1 | melt_temp_C | __ALL__ | 742 | 285.4 | melt_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 25 | high | NELSON_R1 | melt_temp_C | __ALL__ | 956 | 286.2 | melt_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 26 | high | NELSON_R1 | melt_temp_C | __ALL__ | 1112 | 287.3 | melt_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 27 | high | NELSON_R1 | zone_L | __ALL__ | 8 | 49.15 | zone_L 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 28 | high | NELSON_R1 | zone_L | __ALL__ | 459 | 49.54 | zone_L 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 29 | high | NELSON_R1 | zone_L | __ALL__ | 749 | 49.63 | zone_L 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 30 | high | NELSON_R1 | zone_L | __ALL__ | 953 | 48.96 | zone_L 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 31 | high | NELSON_R1 | zone_L | __ALL__ | 1086 | 48.51 | zone_L 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 32 | high | NELSON_R1 | zone_R | __ALL__ | 739 | 49.13 | zone_R 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 33 | high | NELSON_R1 | zone_R | __ALL__ | 940 | 49 | zone_R 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 34 | high | NELSON_R1 | zone_R | __ALL__ | 1100 | 48.6 | zone_R 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 35 | high | NELSON_R5 | dev_pos07 | __ALL__ | 983 | 2.701 | dev_pos07 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 36 | high | NELSON_R5 | die_bolt_T3_pct | __ALL__ | 352 | 50.51 | die_bolt_T3_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 37 | high | NELSON_R5 | die_bolt_T3_pct | __ALL__ | 465 | 50.35 | die_bolt_T3_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 38 | high | NELSON_R5 | die_bolt_T3_pct | __ALL__ | 994 | 54.44 | die_bolt_T3_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 39 | high | NELSON_R5 | die_bolt_T3_pct | __ALL__ | 1101 | 55.46 | die_bolt_T3_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 40 | high | NELSON_R5 | mean_thk | __ALL__ | 335 | 49.59 | mean_thk 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 41 | high | NELSON_R5 | mean_thk | __ALL__ | 481 | 49.6 | mean_thk 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 42 | high | NELSON_R5 | mean_thk | __ALL__ | 713 | 49.61 | mean_thk 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 43 | high | NELSON_R5 | mean_thk | __ALL__ | 828 | 49.5 | mean_thk 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 44 | high | NELSON_R5 | mean_thk | __ALL__ | 999 | 48.93 | mean_thk 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 45 | high | NELSON_R5 | mean_thk | __ALL__ | 1199 | 48.62 | mean_thk 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 46 | high | NELSON_R5 | melt_temp_C | __ALL__ | 28 | 285 | melt_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 47 | high | NELSON_R5 | melt_temp_C | __ALL__ | 335 | 285 | melt_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 48 | high | NELSON_R5 | melt_temp_C | __ALL__ | 740 | 285.1 | melt_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 49 | high | NELSON_R5 | melt_temp_C | __ALL__ | 976 | 286.6 | melt_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 50 | high | NELSON_R5 | melt_temp_C | __ALL__ | 1105 | 287.2 | melt_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 51 | high | NELSON_R5 | zone_L | __ALL__ | 31 | 49.41 | zone_L 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 52 | high | NELSON_R5 | zone_L | __ALL__ | 460 | 49.41 | zone_L 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 53 | high | NELSON_R5 | zone_L | __ALL__ | 843 | 49.46 | zone_L 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 54 | high | NELSON_R5 | zone_L | __ALL__ | 972 | 48.82 | zone_L 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 55 | high | NELSON_R5 | zone_L | __ALL__ | 1199 | 48.39 | zone_L 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 56 | high | NELSON_R5 | zone_R | __ALL__ | 38 | 49.39 | zone_R 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 57 | high | NELSON_R5 | zone_R | __ALL__ | 741 | 49.41 | zone_R 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 58 | high | NELSON_R5 | zone_R | __ALL__ | 969 | 48.84 | zone_R 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 59 | high | NELSON_R5 | zone_R | __ALL__ | 1106 | 48.65 | zone_R 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 60 | high | NELSON_R6 | dev_pos07 | __ALL__ | 284 | 0.4505 | dev_pos07 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 61 | high | NELSON_R6 | die_bolt_T3_pct | __ALL__ | 106 | 49.58 | die_bolt_T3_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 62 | high | NELSON_R6 | die_bolt_T3_pct | __ALL__ | 1027 | 55.1 | die_bolt_T3_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 63 | high | NELSON_R6 | die_bolt_T3_pct | __ALL__ | 1116 | 55.33 | die_bolt_T3_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 64 | high | NELSON_R6 | mean_thk | __ALL__ | 33 | 49.57 | mean_thk 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 65 | high | NELSON_R6 | mean_thk | __ALL__ | 473 | 49.59 | mean_thk 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 66 | high | NELSON_R6 | mean_thk | __ALL__ | 732 | 49.59 | mean_thk 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 67 | high | NELSON_R6 | mean_thk | __ALL__ | 1026 | 48.92 | mean_thk 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 68 | high | NELSON_R6 | mean_thk | __ALL__ | 1199 | 48.62 | mean_thk 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 69 | high | NELSON_R6 | melt_temp_C | __ALL__ | 668 | 285.2 | melt_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 70 | high | NELSON_R6 | melt_temp_C | __ALL__ | 745 | 285.4 | melt_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 71 | high | NELSON_R6 | melt_temp_C | __ALL__ | 1043 | 286.7 | melt_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 72 | high | NELSON_R6 | melt_temp_C | __ALL__ | 1116 | 286.9 | melt_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 73 | high | NELSON_R6 | melt_temp_C | __ALL__ | 1199 | 287.6 | melt_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 74 | high | NELSON_R6 | zone_L | __ALL__ | 22 | 49.27 | zone_L 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 75 | high | NELSON_R6 | zone_L | __ALL__ | 127 | 49.31 | zone_L 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 76 | high | NELSON_R6 | zone_L | __ALL__ | 194 | 49.28 | zone_L 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 77 | high | NELSON_R6 | zone_L | __ALL__ | 475 | 49.39 | zone_L 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 78 | high | NELSON_R6 | zone_L | __ALL__ | 863 | 49.52 | zone_L 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 79 | high | NELSON_R6 | zone_L | __ALL__ | 993 | 48.86 | zone_L 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 80 | high | NELSON_R6 | zone_L | __ALL__ | 1199 | 48.39 | zone_L 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 81 | high | NELSON_R6 | zone_R | __ALL__ | 356 | 49.45 | zone_R 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 82 | high | NELSON_R6 | zone_R | __ALL__ | 483 | 49.42 | zone_R 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 83 | high | NELSON_R6 | zone_R | __ALL__ | 735 | 49.32 | zone_R 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 84 | high | NELSON_R6 | zone_R | __ALL__ | 981 | 48.81 | zone_R 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 85 | high | NELSON_R6 | zone_R | __ALL__ | 1112 | 48.71 | zone_R 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 86 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 402 | - | __ALL__ 组在第 402 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 87 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 429 | - | __ALL__ 组在第 429 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 88 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 547 | - | __ALL__ 组在第 547 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 89 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 583 | - | __ALL__ 组在第 583 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 90 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 630 | - | __ALL__ 组在第 630 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 91 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 798 | - | __ALL__ 组在第 798 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 92 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 906 | - | __ALL__ 组在第 906 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 93 | warn | VARIANCE_RATIO_HIGH | dev_pos07 | __ALL__ | - | 1.199 | dev_pos07 稳态段标准差为基线的 6.5 倍，离散度显著升高，建议检查波动来源 |
| 94 | warn | VARIANCE_RATIO_HIGH | die_bolt_T3_pct | __ALL__ | - | 2.077 | die_bolt_T3_pct 稳态段标准差为基线的 8.8 倍，离散度显著升高，建议检查波动来源 |
| 95 | warn | VARIANCE_RATIO_HIGH | mean_thk | __ALL__ | - | 0.3107 | mean_thk 稳态段标准差为基线的 9.2 倍，离散度显著升高，建议检查波动来源 |
| 96 | warn | VARIANCE_RATIO_HIGH | melt_temp_C | __ALL__ | - | 0.8081 | melt_temp_C 稳态段标准差为基线的 5.4 倍，离散度显著升高，建议检查波动来源 |
| 97 | warn | VARIANCE_RATIO_HIGH | zone_L | __ALL__ | - | 0.3617 | zone_L 稳态段标准差为基线的 6.3 倍，离散度显著升高，建议检查波动来源 |
| 98 | warn | VARIANCE_RATIO_HIGH | zone_R | __ALL__ | - | 0.2626 | zone_R 稳态段标准差为基线的 4.7 倍，离散度显著升高，建议检查波动来源 |
| 99 | warn | NELSON_R2 | dev_pos07 | __ALL__ | 33 | 0.0716 | dev_pos07 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 100 | warn | NELSON_R2 | dev_pos07 | __ALL__ | 168 | -0.0047 | dev_pos07 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 101 | warn | NELSON_R2 | dev_pos07 | __ALL__ | 288 | 0.2827 | dev_pos07 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 102 | warn | NELSON_R2 | die_bolt_T3_pct | __ALL__ | 319 | 50.37 | die_bolt_T3_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 103 | warn | NELSON_R2 | die_bolt_T3_pct | __ALL__ | 471 | 50.75 | die_bolt_T3_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 104 | warn | NELSON_R2 | die_bolt_T3_pct | __ALL__ | 944 | 54.06 | die_bolt_T3_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 105 | warn | NELSON_R2 | die_bolt_T3_pct | __ALL__ | 1008 | 54.53 | die_bolt_T3_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 106 | warn | NELSON_R2 | die_bolt_T3_pct | __ALL__ | 1112 | 55.43 | die_bolt_T3_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 107 | warn | NELSON_R2 | mean_thk | __ALL__ | 459 | 49.62 | mean_thk 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 108 | warn | NELSON_R2 | mean_thk | __ALL__ | 748 | 49.64 | mean_thk 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 109 | warn | NELSON_R2 | mean_thk | __ALL__ | 944 | 49.3 | mean_thk 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 110 | warn | NELSON_R2 | mean_thk | __ALL__ | 1086 | 48.79 | mean_thk 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 111 | warn | NELSON_R2 | melt_temp_C | __ALL__ | 42 | 285 | melt_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 112 | warn | NELSON_R2 | melt_temp_C | __ALL__ | 496 | 285.2 | melt_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 113 | warn | NELSON_R2 | melt_temp_C | __ALL__ | 738 | 285.4 | melt_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 114 | warn | NELSON_R2 | melt_temp_C | __ALL__ | 944 | 286.1 | melt_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 115 | warn | NELSON_R2 | melt_temp_C | __ALL__ | 1037 | 286.5 | melt_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 116 | warn | NELSON_R2 | melt_temp_C | __ALL__ | 1109 | 287 | melt_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 117 | warn | NELSON_R2 | zone_L | __ALL__ | 213 | 49.39 | zone_L 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 118 | warn | NELSON_R2 | zone_L | __ALL__ | 289 | 49.37 | zone_L 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 119 | warn | NELSON_R2 | zone_L | __ALL__ | 876 | 49.41 | zone_L 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 120 | warn | NELSON_R2 | zone_L | __ALL__ | 944 | 49.34 | zone_L 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 121 | warn | NELSON_R2 | zone_L | __ALL__ | 1087 | 48.7 | zone_L 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 122 | warn | NELSON_R2 | zone_L | __ALL__ | 1168 | 48.41 | zone_L 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 123 | warn | NELSON_R2 | zone_R | __ALL__ | 83 | 49.38 | zone_R 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 124 | warn | NELSON_R2 | zone_R | __ALL__ | 734 | 49.25 | zone_R 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 125 | warn | NELSON_R2 | zone_R | __ALL__ | 944 | 49.02 | zone_R 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 126 | warn | NELSON_R2 | zone_R | __ALL__ | 1106 | 48.65 | zone_R 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 127 | warn | NELSON_R3 | dev_pos07 | __ALL__ | 53 | -0.2999 | dev_pos07 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 128 | warn | NELSON_R3 | die_bolt_T3_pct | __ALL__ | 867 | 52.89 | die_bolt_T3_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 129 | warn | NELSON_R3 | die_bolt_T3_pct | __ALL__ | 1032 | 54.38 | die_bolt_T3_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 130 | warn | NELSON_R3 | die_bolt_T3_pct | __ALL__ | 1119 | 54.9 | die_bolt_T3_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 131 | warn | NELSON_R3 | mean_thk | __ALL__ | 707 | 49.63 | mean_thk 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 132 | warn | NELSON_R3 | mean_thk | __ALL__ | 1028 | 48.89 | mean_thk 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 133 | warn | NELSON_R3 | melt_temp_C | __ALL__ | 665 | 284.8 | melt_temp_C 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 134 | warn | NELSON_R3 | zone_L | __ALL__ | 120 | 49.42 | zone_L 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 135 | warn | NELSON_R3 | zone_L | __ALL__ | 679 | 49.66 | zone_L 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 136 | warn | NELSON_R3 | zone_R | __ALL__ | 84 | 49.29 | zone_R 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 137 | warn | NELSON_R3 | zone_R | __ALL__ | 313 | 49.43 | zone_R 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 138 | warn | NELSON_R3 | zone_R | __ALL__ | 718 | 49.42 | zone_R 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 139 | warn | NELSON_R3 | zone_R | __ALL__ | 1126 | 48.65 | zone_R 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 140 | warn | WINDOW_OUT_OF_RANGE | die_bolt_T3_pct | __ALL__ | - | 54.95 | die_bolt_T3_pct 当前值 54.95 已越出操作窗口 [50.47203, 52.39935]，请立即核实工艺状态 |
| 141 | warn | WINDOW_OUT_OF_RANGE | melt_temp_C | __ALL__ | - | 286.8 | melt_temp_C 当前值 286.8 已越出操作窗口 [284.82244, 285.21539]，请立即核实工艺状态 |


> 级别语义：`info` 记录级 / `warn` 趋势与待确认趋势 / `high` 统计异常 / `critical` 越规格。
> 本系统为纯分析系统：所有告警仅为建议核查项，不下发任何参数，动作决策由产线（AWS 侧）做出。

## 二、稳态映射（C3）

- **__ALL__**：steady=1079、transition=121

## 三、操作窗口投影（C2）

- **die_bolt_T3_pct**：当前 54.95，斜率 161.3/h，距边界 0.0 h（级别 warn）
- **melt_temp_C**：当前 286.8，斜率 58.52/h，距边界 0.0 h（级别 warn）

## 四、防风暴抑制

合并触发 32 组同 key 重复；静默期 30 行；同类抑制窗口 60 分钟；迟滞 5 点

## 五、建议后续动作

- 有 `high`/`critical` 告警：按告警中的 `suggested_check` 现场核查；需要根因分析时转 `industrial-diagnostician`，需要参数窗口/工况数据分析时转 `industrial-doe-analyzer`。
- 本报告由脚本生成（`authored_by: script`）；代理只允许追加中文 `interpretation` 注记，禁止改动任何数值字段。
