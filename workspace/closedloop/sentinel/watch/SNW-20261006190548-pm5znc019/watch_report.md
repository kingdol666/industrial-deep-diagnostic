# 产线哨兵巡检报告（watch 模式）

- **生成时间**：2026-10-06T19:05:50.696343+00:00
- **总体状态**：**alert** · 告警数 **37**
- **数据**：`D:\codes\industrial-deep-diagnostic\workspace\aw-exchange\line1-exam-watch4h-ascii-20261007T0304.csv`（5000 行；时间列 time；分组列 -）
- **基线**：模式：prior（v1.0.0），路径：D:\codes\industrial-deep-diagnostic\workspace\closedloop\sentinel\baselines\演示线1·挤出主机PLC(Modbus TCP)\watch_baseline.json
- **耗时**：104 ms（零 LLM / 零网络，全部统计由确定性脚本计算）


## 一、告警清单

| # | 级别 | 规则 | 参数/指标 | 分组 | 位置 | 观测值 | 建议 |
|---|------|------|-----------|------|------|--------|------|
| 1 | high | ROBUST_Z_OUTLIER | melt_temp | __ALL__ | 3827 | 113.8 | melt_temp 稳健 z 分数 \|-130.72\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 2 | high | NELSON_R1 | melt_temp | __ALL__ | 263 | 198.6 | melt_temp 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 3 | high | NELSON_R1 | melt_temp | __ALL__ | 4838 | 190.5 | melt_temp 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 4 | high | NELSON_R1 | melt_temp | __ALL__ | 4996 | 193.1 | melt_temp 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 5 | high | NELSON_R5 | melt_temp | __ALL__ | 465 | 200.1 | melt_temp 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 6 | high | NELSON_R5 | melt_temp | __ALL__ | 543 | 200.9 | melt_temp 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 7 | high | NELSON_R5 | melt_temp | __ALL__ | 1227 | 199.9 | melt_temp 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 8 | high | NELSON_R5 | melt_temp | __ALL__ | 3781 | 196.7 | melt_temp 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 9 | high | NELSON_R5 | melt_temp | __ALL__ | 4381 | 191.7 | melt_temp 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 10 | high | NELSON_R6 | melt_temp | __ALL__ | 399 | 199.8 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 11 | high | NELSON_R6 | melt_temp | __ALL__ | 681 | 199.9 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 12 | high | NELSON_R6 | melt_temp | __ALL__ | 1024 | 200.6 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 13 | high | NELSON_R6 | melt_temp | __ALL__ | 1376 | 199.4 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 14 | high | NELSON_R6 | melt_temp | __ALL__ | 3781 | 196.7 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 15 | high | NELSON_R6 | melt_temp | __ALL__ | 4138 | 192.3 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 16 | high | NELSON_R6 | melt_temp | __ALL__ | 4382 | 191.1 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 17 | high | NELSON_R6 | melt_temp | __ALL__ | 4557 | 192.4 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 18 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 1920 | - | __ALL__ 组在第 1920 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 19 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 3113 | - | __ALL__ 组在第 3113 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 20 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 3792 | - | __ALL__ 组在第 3792 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 21 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 3859 | - | __ALL__ 组在第 3859 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 22 | warn | VARIANCE_RATIO_HIGH | melt_temp | __ALL__ | - | 11.96 | melt_temp 稳态段标准差为基线的 29.6 倍，离散度显著升高，建议检查波动来源 |
| 23 | warn | NELSON_R2 | melt_temp | __ALL__ | 618 | 200.1 | melt_temp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 24 | warn | NELSON_R2 | melt_temp | __ALL__ | 921 | 200.4 | melt_temp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 25 | warn | NELSON_R2 | melt_temp | __ALL__ | 1016 | 199.2 | melt_temp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 26 | warn | NELSON_R2 | melt_temp | __ALL__ | 1108 | 200.1 | melt_temp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 27 | warn | NELSON_R2 | melt_temp | __ALL__ | 1340 | 199.6 | melt_temp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 28 | warn | NELSON_R2 | melt_temp | __ALL__ | 1470 | 200.1 | melt_temp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 29 | warn | NELSON_R2 | melt_temp | __ALL__ | 1919 | 207.7 | melt_temp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 30 | warn | NELSON_R2 | melt_temp | __ALL__ | 3789 | 141.6 | melt_temp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 31 | warn | NELSON_R2 | melt_temp | __ALL__ | 4136 | 191.3 | melt_temp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 32 | warn | NELSON_R2 | melt_temp | __ALL__ | 4351 | 191.2 | melt_temp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 33 | warn | NELSON_R3 | melt_temp | __ALL__ | 1913 | 203 | melt_temp 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 34 | warn | NELSON_R3 | melt_temp | __ALL__ | 3176 | 207.9 | melt_temp 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 35 | warn | NELSON_R3 | melt_temp | __ALL__ | 3656 | 208.8 | melt_temp 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 36 | warn | NELSON_R3 | melt_temp | __ALL__ | 3784 | 167.2 | melt_temp 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 37 | warn | NELSON_R3 | melt_temp | __ALL__ | 3852 | 148.2 | melt_temp 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |


> 级别语义：`info` 记录级 / `warn` 趋势与待确认趋势 / `high` 统计异常 / `critical` 越规格。
> 本系统为纯分析系统：所有告警仅为建议核查项，不下发任何参数，动作决策由产线（AWS 侧）做出。

## 二、稳态映射（C3）

- **__ALL__**：steady=5000

## 三、操作窗口投影（C2）

- **C2 漂移投影未启用**：基线中无 operating_windows —— 构建基线时传入 --doe-run-dir 注册 DOE 先验操作窗即可启用（C2 drift projection disabled: no operating_windows in baseline (build with --doe-run-dir to enable)）

## 四、防风暴抑制

合并触发 5 组同 key 重复；静默期 30 行；同类抑制窗口 60 分钟；迟滞 5 点

## 五、告警事件摘要（incidents）

| 事件 | 参数 | 类别 | 峰值级别 | 跨度(行) | 告警数 | 规则 |
|------|------|------|----------|----------|--------|------|
| EVT-20261006190550-004 | melt_temp | spc | high | 549 | 8 | NELSON_R2、NELSON_R6、NELSON_R5 |
| EVT-20261006190550-003 | melt_temp | spc | high | 282 | 5 | NELSON_R6、NELSON_R5、NELSON_R2 |
| EVT-20261006190550-010 | melt_temp | spc | high | 71 | 5 | NELSON_R5、NELSON_R6、NELSON_R3… |
| EVT-20261006190550-014 | melt_temp | spc | high | 31 | 3 | NELSON_R2、NELSON_R5、NELSON_R6 |
| EVT-20261006190550-013 | melt_temp | spc | high | 2 | 2 | NELSON_R2、NELSON_R6 |
| EVT-20261006190550-002 | melt_temp | spc | high | 0 | 1 | NELSON_R1 |
| EVT-20261006190550-012 | melt_temp | multivariate | high | 0 | 1 | ROBUST_Z_OUTLIER |
| EVT-20261006190550-015 | melt_temp | spc | high | 0 | 1 | NELSON_R6 |
| EVT-20261006190550-016 | melt_temp | spc | high | 0 | 1 | NELSON_R1 |
| EVT-20261006190550-017 | melt_temp | spc | high | 0 | 1 | NELSON_R1 |
| EVT-20261006190550-005 | melt_temp | spc | warn | 6 | 2 | NELSON_R3、NELSON_R2 |
| EVT-20261006190550-011 | - | regime | warn | 67 | 2 | REGIME_CHANGE_NEW |

（其余 5 个事件见 alert.json 的 events 数组；完整逐段告警在 alerts 数组，契约不变）

## 六、建议后续动作

- 有 `high`/`critical` 告警：按告警中的 `suggested_check` 现场核查；需要根因分析时转 `industrial-diagnostician`，需要参数窗口/工况数据分析时转 `industrial-doe-analyzer`。
- 事件摘要按峰值级别与告警数排序；完整逐段告警在 alert.json 的 `alerts` 数组（契约不变），事件视图在 `events` 数组。
- 本报告由脚本生成（`authored_by: script`）；代理只允许追加中文 `interpretation` 注记，禁止改动任何数值字段。
