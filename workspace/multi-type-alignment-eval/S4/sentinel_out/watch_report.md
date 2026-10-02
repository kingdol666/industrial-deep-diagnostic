# 产线哨兵巡检报告（watch 模式）

- **生成时间**：2026-10-01T12:59:37.820424+00:00
- **总体状态**：**alert** · 告警数 **37**
- **数据**：`D:\codes\myskills\industrial-deep-diagnostic\workspace\multi-type-alignment-eval\S4\s4_watch.csv`（300 行；时间列 timestamp；分组列 -）
- **基线**：模式：prior（v1.0.0），路径：D:\codes\myskills\industrial-deep-diagnostic\workspace\multi-type-alignment-eval\S4\watch_baseline.json
- **耗时**：24 ms（零 LLM / 零网络，全部统计由确定性脚本计算）


## 一、告警清单

| # | 级别 | 规则 | 参数/指标 | 分组 | 位置 | 观测值 | 建议 |
|---|------|------|-----------|------|------|--------|------|
| 1 | high | ROBUST_Z_OUTLIER | band_mean | __ALL__ | 82 | 41.54 | band_mean 稳健 z 分数 \|3.60\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 2 | high | ROBUST_Z_OUTLIER | band_mean | __ALL__ | 264 | 41.74 | band_mean 稳健 z 分数 \|3.79\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 3 | high | ROBUST_Z_OUTLIER | furnace_temp_C | __ALL__ | 89 | 1190 | furnace_temp_C 稳健 z 分数 \|3.54\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 4 | high | ROBUST_Z_OUTLIER | furnace_temp_C | __ALL__ | 261 | 1191 | furnace_temp_C 稳健 z 分数 \|3.89\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 5 | high | NELSON_R1 | band_mean | __ALL__ | 16 | 39.38 | band_mean 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 6 | high | NELSON_R1 | band_mean | __ALL__ | 115 | 41.54 | band_mean 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 7 | high | NELSON_R1 | band_ref_mean | __ALL__ | 222 | 34.39 | band_ref_mean 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 8 | high | NELSON_R1 | furnace_temp_C | __ALL__ | 13 | 1184 | furnace_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 9 | high | NELSON_R1 | stir_speed_rpm | __ALL__ | 140 | 88.02 | stir_speed_rpm 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 10 | high | NELSON_R5 | band_mean | __ALL__ | 17 | 38.51 | band_mean 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 11 | high | NELSON_R5 | band_mean | __ALL__ | 116 | 40.74 | band_mean 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 12 | high | NELSON_R5 | band_ref_mean | __ALL__ | 127 | 34.13 | band_ref_mean 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 13 | high | NELSON_R5 | band_ref_mean | __ALL__ | 190 | 33.57 | band_ref_mean 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 14 | high | NELSON_R5 | furnace_temp_C | __ALL__ | 14 | 1182 | furnace_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 15 | high | NELSON_R5 | furnace_temp_C | __ALL__ | 113 | 1188 | furnace_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 16 | high | NELSON_R5 | stir_speed_rpm | __ALL__ | 7 | 89.36 | stir_speed_rpm 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 17 | high | NELSON_R5 | stir_speed_rpm | __ALL__ | 142 | 91.34 | stir_speed_rpm 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 18 | high | NELSON_R6 | band_mean | __ALL__ | 17 | 38.51 | band_mean 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 19 | high | NELSON_R6 | band_mean | __ALL__ | 119 | 40.67 | band_mean 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 20 | high | NELSON_R6 | furnace_temp_C | __ALL__ | 4 | 1178 | furnace_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 21 | high | NELSON_R6 | furnace_temp_C | __ALL__ | 115 | 1189 | furnace_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 22 | high | NELSON_R6 | stir_speed_rpm | __ALL__ | 7 | 89.36 | stir_speed_rpm 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 23 | high | NELSON_R6 | stir_speed_rpm | __ALL__ | 135 | 88.75 | stir_speed_rpm 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 24 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 57 | - | __ALL__ 组在第 57 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 25 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 76 | - | __ALL__ 组在第 76 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 26 | warn | NELSON_R2 | band_mean | __ALL__ | 32 | 36.99 | band_mean 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 27 | warn | NELSON_R2 | band_mean | __ALL__ | 119 | 40.67 | band_mean 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 28 | warn | NELSON_R2 | furnace_temp_C | __ALL__ | 38 | 1182 | furnace_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 29 | warn | NELSON_R2 | furnace_temp_C | __ALL__ | 116 | 1187 | furnace_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 30 | warn | NELSON_R2 | furnace_temp_C | __ALL__ | 245 | 1186 | furnace_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 31 | warn | NELSON_R2 | stir_speed_rpm | __ALL__ | 125 | 88.85 | stir_speed_rpm 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 32 | warn | NELSON_R3 | band_mean | __ALL__ | 160 | 38.67 | band_mean 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 33 | warn | NELSON_R3 | furnace_temp_C | __ALL__ | 157 | 1183 | furnace_temp_C 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 34 | warn | NELSON_R3 | stir_speed_rpm | __ALL__ | 12 | 91.3 | stir_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 35 | warn | NELSON_R3 | stir_speed_rpm | __ALL__ | 116 | 91.11 | stir_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 36 | warn | NELSON_R3 | stir_speed_rpm | __ALL__ | 203 | 92.18 | stir_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 37 | warn | NELSON_R3 | stir_speed_rpm | __ALL__ | 273 | 88.33 | stir_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |


> 级别语义：`info` 记录级 / `warn` 趋势与待确认趋势 / `high` 统计异常 / `critical` 越规格。
> 本系统为纯分析系统：所有告警仅为建议核查项，不下发任何参数，动作决策由产线（AWS 侧）做出。

## 二、稳态映射（C3）

- **__ALL__**：steady=278、transition=22

## 三、操作窗口投影（C2）

- 无操作窗口投影

## 四、防风暴抑制

合并触发 18 组同 key 重复；静默期 30 行；同类抑制窗口 60 分钟；迟滞 5 点

## 五、建议后续动作

- 有 `high`/`critical` 告警：按告警中的 `suggested_check` 现场核查；需要根因分析时转 `industrial-diagnostician`，需要参数窗口/工况数据分析时转 `industrial-doe-analyzer`。
- 本报告由脚本生成（`authored_by: script`）；代理只允许追加中文 `interpretation` 注记，禁止改动任何数值字段。
