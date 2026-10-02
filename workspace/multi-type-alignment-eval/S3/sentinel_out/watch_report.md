# 产线哨兵巡检报告（watch 模式）

- **生成时间**：2026-10-01T12:58:48.521599+00:00
- **总体状态**：**alert** · 告警数 **33**
- **数据**：`D:\codes\myskills\industrial-deep-diagnostic\workspace\multi-type-alignment-eval\S3\s3_watch.csv`（150 行；时间列 timestamp；分组列 -）
- **基线**：模式：prior（v1.0.0），路径：D:\codes\myskills\industrial-deep-diagnostic\workspace\multi-type-alignment-eval\S3\watch_baseline.json
- **耗时**：15 ms（零 LLM / 零网络，全部统计由确定性脚本计算）


## 一、告警清单

| # | 级别 | 规则 | 参数/指标 | 分组 | 位置 | 观测值 | 建议 |
|---|------|------|-----------|------|------|--------|------|
| 1 | high | NELSON_R1 | dev_pos07 | __ALL__ | 26 | 38.46 | dev_pos07 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 2 | high | NELSON_R1 | die_bolt_T3_pct | __ALL__ | 26 | 49.46 | die_bolt_T3_pct 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 3 | high | NELSON_R1 | die_bolt_T3_pct | __ALL__ | 130 | 52.05 | die_bolt_T3_pct 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 4 | high | NELSON_R1 | melt_temp_C | __ALL__ | 43 | 192.5 | melt_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 5 | high | NELSON_R1 | melt_temp_C | __ALL__ | 129 | 197.5 | melt_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 6 | high | NELSON_R1 | pull_speed_mpm | __ALL__ | 5 | 121.4 | pull_speed_mpm 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 7 | high | NELSON_R1 | pull_speed_mpm | __ALL__ | 111 | 121.2 | pull_speed_mpm 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 8 | high | NELSON_R1 | td_std | __ALL__ | 26 | 8.413 | td_std 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 9 | high | NELSON_R1 | zone_L | __ALL__ | 39 | 108.5 | zone_L 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 10 | high | NELSON_R5 | dev_pos07 | __ALL__ | 41 | 39.18 | dev_pos07 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 11 | high | NELSON_R5 | dev_pos07 | __ALL__ | 112 | 42.32 | dev_pos07 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 12 | high | NELSON_R5 | die_bolt_T3_pct | __ALL__ | 112 | 54.34 | die_bolt_T3_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 13 | high | NELSON_R5 | mean_thk | __ALL__ | 137 | 103.9 | mean_thk 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 14 | high | NELSON_R5 | melt_temp_C | __ALL__ | 43 | 192.5 | melt_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 15 | high | NELSON_R5 | melt_temp_C | __ALL__ | 129 | 197.5 | melt_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 16 | high | NELSON_R5 | pull_speed_mpm | __ALL__ | 29 | 120.7 | pull_speed_mpm 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 17 | high | NELSON_R5 | pull_speed_mpm | __ALL__ | 113 | 120.1 | pull_speed_mpm 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 18 | high | NELSON_R5 | td_std | __ALL__ | 112 | 9.177 | td_std 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 19 | high | NELSON_R5 | zone_L | __ALL__ | 131 | 109.1 | zone_L 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 20 | high | NELSON_R6 | dev_pos07 | __ALL__ | 24 | 40.77 | dev_pos07 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 21 | high | NELSON_R6 | dev_pos07 | __ALL__ | 137 | 42.33 | dev_pos07 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 22 | high | NELSON_R6 | die_bolt_T3_pct | __ALL__ | 24 | 52.29 | die_bolt_T3_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 23 | high | NELSON_R6 | die_bolt_T3_pct | __ALL__ | 137 | 54.34 | die_bolt_T3_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 24 | high | NELSON_R6 | melt_temp_C | __ALL__ | 131 | 194.4 | melt_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 25 | high | NELSON_R6 | pull_speed_mpm | __ALL__ | 4 | 119.9 | pull_speed_mpm 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 26 | high | NELSON_R6 | pull_speed_mpm | __ALL__ | 119 | 119.8 | pull_speed_mpm 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 27 | high | NELSON_R6 | td_std | __ALL__ | 24 | 8.885 | td_std 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 28 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 50 | - | __ALL__ 组在第 50 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 29 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 74 | - | __ALL__ 组在第 74 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 30 | warn | NELSON_R2 | die_bolt_T3_pct | __ALL__ | 47 | 51.89 | die_bolt_T3_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 31 | warn | NELSON_R2 | melt_temp_C | __ALL__ | 45 | 194.5 | melt_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 32 | warn | NELSON_R3 | melt_temp_C | __ALL__ | 24 | 196.4 | melt_temp_C 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 33 | warn | NELSON_R3 | pull_speed_mpm | __ALL__ | 116 | 119.2 | pull_speed_mpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |


> 级别语义：`info` 记录级 / `warn` 趋势与待确认趋势 / `high` 统计异常 / `critical` 越规格。
> 本系统为纯分析系统：所有告警仅为建议核查项，不下发任何参数，动作决策由产线（AWS 侧）做出。

## 二、稳态映射（C3）

- **__ALL__**：steady=128、transition=22

## 三、操作窗口投影（C2）

- 无操作窗口投影

## 四、防风暴抑制

合并触发 12 组同 key 重复；静默期 30 行；同类抑制窗口 60 分钟；迟滞 5 点

## 五、建议后续动作

- 有 `high`/`critical` 告警：按告警中的 `suggested_check` 现场核查；需要根因分析时转 `industrial-diagnostician`，需要参数窗口/工况数据分析时转 `industrial-doe-analyzer`。
- 本报告由脚本生成（`authored_by: script`）；代理只允许追加中文 `interpretation` 注记，禁止改动任何数值字段。
