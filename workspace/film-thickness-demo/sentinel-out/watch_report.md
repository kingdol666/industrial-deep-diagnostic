# 产线哨兵巡检报告（watch 模式）

- **生成时间**：2026-10-01T12:34:32.517263+00:00
- **总体状态**：**alert** · 告警数 **89**
- **数据**：`D:\codes\myskills\industrial-deep-diagnostic\workspace\film-thickness-demo\aligned.csv`（1200 行；时间列 timestamp；分组列 -）
- **基线**：模式：prior（v1.0.0），路径：D:\codes\myskills\industrial-deep-diagnostic\workspace\film-thickness-demo\watch_baseline.json
- **耗时**：23 ms（零 LLM / 零网络，全部统计由确定性脚本计算）


## 一、告警清单

| # | 级别 | 规则 | 参数/指标 | 分组 | 位置 | 观测值 | 建议 |
|---|------|------|-----------|------|------|--------|------|
| 1 | high | ROBUST_Z_OUTLIER | dev_pos07 | __ALL__ | 464 | 0.9977 | dev_pos07 稳健 z 分数 \|3.51\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 2 | high | ROBUST_Z_OUTLIER | dev_pos07 | __ALL__ | 707 | 3.09 | dev_pos07 稳健 z 分数 \|11.07\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 3 | high | ROBUST_Z_OUTLIER | mean_thk | __ALL__ | 595 | 49.75 | mean_thk 稳健 z 分数 \|3.57\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 4 | high | ROBUST_Z_OUTLIER | mean_thk | __ALL__ | 868 | 49.34 | mean_thk 稳健 z 分数 \|-4.12\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 5 | high | ROBUST_Z_OUTLIER | mean_thk | __ALL__ | 1194 | 48.62 | mean_thk 稳健 z 分数 \|-17.73\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 6 | high | ROBUST_Z_OUTLIER | zone_L | __ALL__ | 496 | 49.65 | zone_L 稳健 z 分数 \|3.53\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 7 | high | ROBUST_Z_OUTLIER | zone_L | __ALL__ | 1199 | 48.39 | zone_L 稳健 z 分数 \|-12.19\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 8 | high | ROBUST_Z_OUTLIER | zone_R | __ALL__ | 793 | 49.1 | zone_R 稳健 z 分数 \|-3.54\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 9 | high | ROBUST_Z_OUTLIER | zone_R | __ALL__ | 1162 | 48.5 | zone_R 稳健 z 分数 \|-11.58\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 10 | high | NELSON_R1 | dev_pos07 | __ALL__ | 9 | -0.6013 | dev_pos07 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 11 | high | NELSON_R1 | dev_pos07 | __ALL__ | 451 | 0.7159 | dev_pos07 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 12 | high | NELSON_R1 | mean_thk | __ALL__ | 185 | 49.46 | mean_thk 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 13 | high | NELSON_R1 | mean_thk | __ALL__ | 512 | 49.67 | mean_thk 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 14 | high | NELSON_R1 | mean_thk | __ALL__ | 805 | 49.46 | mean_thk 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 15 | high | NELSON_R1 | mean_thk | __ALL__ | 1097 | 48.85 | mean_thk 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 16 | high | NELSON_R1 | zone_L | __ALL__ | 8 | 49.15 | zone_L 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 17 | high | NELSON_R1 | zone_L | __ALL__ | 459 | 49.54 | zone_L 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 18 | high | NELSON_R1 | zone_L | __ALL__ | 764 | 49.66 | zone_L 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 19 | high | NELSON_R1 | zone_L | __ALL__ | 937 | 49.18 | zone_L 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 20 | high | NELSON_R1 | zone_L | __ALL__ | 1159 | 48.77 | zone_L 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 21 | high | NELSON_R1 | zone_R | __ALL__ | 802 | 49.17 | zone_R 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 22 | high | NELSON_R5 | mean_thk | __ALL__ | 335 | 49.59 | mean_thk 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 23 | high | NELSON_R5 | mean_thk | __ALL__ | 512 | 49.67 | mean_thk 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 24 | high | NELSON_R5 | mean_thk | __ALL__ | 713 | 49.61 | mean_thk 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 25 | high | NELSON_R5 | mean_thk | __ALL__ | 813 | 49.57 | mean_thk 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 26 | high | NELSON_R5 | mean_thk | __ALL__ | 1101 | 48.87 | mean_thk 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 27 | high | NELSON_R5 | mean_thk | __ALL__ | 1165 | 48.67 | mean_thk 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 28 | high | NELSON_R5 | zone_L | __ALL__ | 31 | 49.41 | zone_L 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 29 | high | NELSON_R5 | zone_L | __ALL__ | 460 | 49.41 | zone_L 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 30 | high | NELSON_R5 | zone_L | __ALL__ | 939 | 49.35 | zone_L 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 31 | high | NELSON_R5 | zone_L | __ALL__ | 1101 | 48.71 | zone_L 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 32 | high | NELSON_R5 | zone_R | __ALL__ | 38 | 49.39 | zone_R 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 33 | high | NELSON_R5 | zone_R | __ALL__ | 766 | 49.24 | zone_R 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 34 | high | NELSON_R5 | zone_R | __ALL__ | 1170 | 48.52 | zone_R 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 35 | high | NELSON_R6 | dev_pos07 | __ALL__ | 284 | 0.4505 | dev_pos07 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 36 | high | NELSON_R6 | mean_thk | __ALL__ | 33 | 49.57 | mean_thk 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 37 | high | NELSON_R6 | mean_thk | __ALL__ | 415 | 49.61 | mean_thk 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 38 | high | NELSON_R6 | mean_thk | __ALL__ | 762 | 49.61 | mean_thk 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 39 | high | NELSON_R6 | mean_thk | __ALL__ | 1115 | 48.75 | mean_thk 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 40 | high | NELSON_R6 | zone_L | __ALL__ | 22 | 49.27 | zone_L 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 41 | high | NELSON_R6 | zone_L | __ALL__ | 127 | 49.31 | zone_L 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 42 | high | NELSON_R6 | zone_L | __ALL__ | 194 | 49.28 | zone_L 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 43 | high | NELSON_R6 | zone_L | __ALL__ | 475 | 49.39 | zone_L 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 44 | high | NELSON_R6 | zone_L | __ALL__ | 1108 | 48.63 | zone_L 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 45 | high | NELSON_R6 | zone_L | __ALL__ | 1178 | 48.49 | zone_L 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 46 | high | NELSON_R6 | zone_R | __ALL__ | 356 | 49.45 | zone_R 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 47 | high | NELSON_R6 | zone_R | __ALL__ | 1101 | 48.76 | zone_R 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 48 | high | NELSON_R6 | zone_R | __ALL__ | 1190 | 48.58 | zone_R 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 49 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 1005 | - | __ALL__ 组在第 1005 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 50 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 1066 | - | __ALL__ 组在第 1066 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 51 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 420 | - | __ALL__ 组在第 420 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 52 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 477 | - | __ALL__ 组在第 477 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 53 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 547 | - | __ALL__ 组在第 547 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 54 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 732 | - | __ALL__ 组在第 732 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 55 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 771 | - | __ALL__ 组在第 771 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 56 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 831 | - | __ALL__ 组在第 831 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 57 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 860 | - | __ALL__ 组在第 860 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 58 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 905 | - | __ALL__ 组在第 905 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 59 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 953 | - | __ALL__ 组在第 953 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 60 | warn | VARIANCE_RATIO_HIGH | dev_pos07 | __ALL__ | - | 1.196 | dev_pos07 稳态段标准差为基线的 6.4 倍，离散度显著升高，建议检查波动来源 |
| 61 | warn | VARIANCE_RATIO_HIGH | mean_thk | __ALL__ | - | 0.3061 | mean_thk 稳态段标准差为基线的 9.0 倍，离散度显著升高，建议检查波动来源 |
| 62 | warn | VARIANCE_RATIO_HIGH | zone_L | __ALL__ | - | 0.3567 | zone_L 稳态段标准差为基线的 6.2 倍，离散度显著升高，建议检查波动来源 |
| 63 | warn | VARIANCE_RATIO_HIGH | zone_R | __ALL__ | - | 0.2595 | zone_R 稳态段标准差为基线的 4.7 倍，离散度显著升高，建议检查波动来源 |
| 64 | warn | NELSON_R2 | dev_pos07 | __ALL__ | 33 | 0.0716 | dev_pos07 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 65 | warn | NELSON_R2 | dev_pos07 | __ALL__ | 168 | -0.0047 | dev_pos07 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 66 | warn | NELSON_R2 | dev_pos07 | __ALL__ | 288 | 0.2827 | dev_pos07 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 67 | warn | NELSON_R2 | mean_thk | __ALL__ | 459 | 49.62 | mean_thk 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 68 | warn | NELSON_R2 | mean_thk | __ALL__ | 822 | 49.5 | mean_thk 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 69 | warn | NELSON_R2 | mean_thk | __ALL__ | 1104 | 48.78 | mean_thk 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 70 | warn | NELSON_R2 | mean_thk | __ALL__ | 1181 | 48.69 | mean_thk 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 71 | warn | NELSON_R2 | zone_L | __ALL__ | 213 | 49.39 | zone_L 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 72 | warn | NELSON_R2 | zone_L | __ALL__ | 289 | 49.37 | zone_L 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 73 | warn | NELSON_R2 | zone_L | __ALL__ | 457 | 49.46 | zone_L 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 74 | warn | NELSON_R2 | zone_L | __ALL__ | 944 | 49.34 | zone_L 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 75 | warn | NELSON_R2 | zone_L | __ALL__ | 1104 | 48.68 | zone_L 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 76 | warn | NELSON_R2 | zone_R | __ALL__ | 83 | 49.38 | zone_R 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 77 | warn | NELSON_R2 | zone_R | __ALL__ | 1113 | 48.75 | zone_R 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 78 | warn | NELSON_R2 | zone_R | __ALL__ | 1191 | 48.63 | zone_R 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 79 | warn | NELSON_R3 | dev_pos07 | __ALL__ | 53 | -0.2999 | dev_pos07 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 80 | warn | NELSON_R3 | dev_pos07 | __ALL__ | 823 | 2.301 | dev_pos07 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 81 | warn | NELSON_R3 | mean_thk | __ALL__ | 707 | 49.63 | mean_thk 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 82 | warn | NELSON_R3 | zone_L | __ALL__ | 120 | 49.42 | zone_L 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 83 | warn | NELSON_R3 | zone_L | __ALL__ | 405 | 49.46 | zone_L 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 84 | warn | NELSON_R3 | zone_L | __ALL__ | 679 | 49.66 | zone_L 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 85 | warn | NELSON_R3 | zone_R | __ALL__ | 84 | 49.29 | zone_R 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 86 | warn | NELSON_R3 | zone_R | __ALL__ | 313 | 49.43 | zone_R 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 87 | warn | NELSON_R3 | zone_R | __ALL__ | 413 | 49.47 | zone_R 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 88 | warn | NELSON_R3 | zone_R | __ALL__ | 718 | 49.42 | zone_R 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 89 | warn | NELSON_R3 | zone_R | __ALL__ | 1126 | 48.65 | zone_R 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |


> 级别语义：`info` 记录级 / `warn` 趋势与待确认趋势 / `high` 统计异常 / `critical` 越规格。
> 本系统为纯分析系统：所有告警仅为建议核查项，不下发任何参数，动作决策由产线（AWS 侧）做出。

## 二、稳态映射（C3）

- **__ALL__**：marginal=7、steady=1072、transition=121

## 三、操作窗口投影（C2）

- 无操作窗口投影

## 四、防风暴抑制

合并触发 21 组同 key 重复；静默期 30 行；同类抑制窗口 60 分钟；迟滞 5 点

## 五、建议后续动作

- 有 `high`/`critical` 告警：按告警中的 `suggested_check` 现场核查；需要根因分析时转 `industrial-diagnostician`，需要参数窗口/工况数据分析时转 `industrial-doe-analyzer`。
- 本报告由脚本生成（`authored_by: script`）；代理只允许追加中文 `interpretation` 注记，禁止改动任何数值字段。
