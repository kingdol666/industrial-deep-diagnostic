# 产线哨兵巡检报告（watch 模式）

- **生成时间**：2026-10-06T04:01:21.471601+00:00
- **总体状态**：**alert** · 告警数 **47**
- **数据**：`D:\codes\industrial-deep-diagnostic\workspace\aw-exchange\merged_ln-d7e0a2a2_20261006T115940.csv`（1721 行；时间列 time；分组列 -）
- **基线**：模式：prior（v1.0.0），路径：D:\codes\industrial-deep-diagnostic\workspace\closedloop\sentinel\baselines\演示线1·挤出主机PLC(Modbus TCP)\watch_baseline.json
- **耗时**：39 ms（零 LLM / 零网络，全部统计由确定性脚本计算）


## 一、告警清单

| # | 级别 | 规则 | 参数/指标 | 分组 | 位置 | 观测值 | 建议 |
|---|------|------|-----------|------|------|--------|------|
| 1 | high | ROBUST_Z_OUTLIER | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 1 | 178.4 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 稳健 z 分数 \|-41.70\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 2 | high | ROBUST_Z_OUTLIER | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 147 | 199.6 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 稳健 z 分数 \|-9.55\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 3 | high | ROBUST_Z_OUTLIER | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 259 | 208.6 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 稳健 z 分数 \|4.09\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 4 | high | ROBUST_Z_OUTLIER | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 496 | 177.9 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 稳健 z 分数 \|-42.46\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 5 | high | ROBUST_Z_OUTLIER | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 1154 | 178 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 稳健 z 分数 \|-42.31\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 6 | high | ROBUST_Z_OUTLIER | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 1253 | 178 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 稳健 z 分数 \|-42.31\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 7 | high | ROBUST_Z_OUTLIER | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 1531 | 178.5 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 稳健 z 分数 \|-41.55\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 8 | high | ROBUST_Z_OUTLIER | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 1666 | 178.2 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 稳健 z 分数 \|-42.01\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 9 | high | ROBUST_Z_OUTLIER | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | __ALL__ | 627 | 69 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) 稳健 z 分数 \|29.57\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 10 | high | NELSON_R1 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 39 | 207.7 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 11 | high | NELSON_R1 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 256 | 179.2 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 12 | high | NELSON_R1 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 450 | 179.8 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 13 | high | NELSON_R5 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 36 | 210.3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 14 | high | NELSON_R5 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 105 | 205.2 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 15 | high | NELSON_R5 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 256 | 179.2 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 16 | high | NELSON_R5 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 450 | 179.8 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 17 | high | NELSON_R6 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 36 | 210.3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 18 | high | NELSON_R6 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 98 | 209.2 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 19 | high | NELSON_R6 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 256 | 179.2 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 20 | high | NELSON_R6 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 347 | 200.2 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 21 | high | NELSON_R6 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 450 | 179.8 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 22 | high | NELSON_R6 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 864 | 180.9 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 23 | high | NELSON_R6 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 1042 | 181.6 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 24 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 202 | - | __ALL__ 组在第 202 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 25 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 257 | - | __ALL__ 组在第 257 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 26 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 276 | - | __ALL__ 组在第 276 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 27 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 359 | - | __ALL__ 组在第 359 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 28 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 51 | - | __ALL__ 组在第 51 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 29 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 614 | - | __ALL__ 组在第 614 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 30 | warn | VARIANCE_RATIO_HIGH | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | __ALL__ | - | 30.07 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) 稳态段标准差为基线的 2.2 倍，离散度显著升高，建议检查波动来源 |
| 31 | warn | NELSON_R2 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 9 | 179 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 32 | warn | NELSON_R2 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 106 | 203.6 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 33 | warn | NELSON_R2 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 357 | 152 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 34 | warn | NELSON_R2 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 460 | 180.5 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 35 | warn | NELSON_R2 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 672 | 180.1 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 36 | warn | NELSON_R2 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 1666 | 178.2 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 37 | warn | NELSON_R2 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | __ALL__ | 8 | 3 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 38 | warn | NELSON_R2 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | __ALL__ | 187 | 6 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 39 | warn | NELSON_R2 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | __ALL__ | 355 | 3 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 40 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 23 | 180.1 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 41 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 103 | 205.8 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 42 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 355 | 126.4 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 43 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 438 | 180.2 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 44 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 721 | 180.7 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 45 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 1139 | 179.6 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 46 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 1325 | 178.6 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 47 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 1582 | 180.3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |


> 级别语义：`info` 记录级 / `warn` 趋势与待确认趋势 / `high` 统计异常 / `critical` 越规格。
> 本系统为纯分析系统：所有告警仅为建议核查项，不下发任何参数，动作决策由产线（AWS 侧）做出。

## 二、稳态映射（C3）

- **__ALL__**：steady=1721

## 三、操作窗口投影（C2）

- **C2 漂移投影未启用**：基线中无 operating_windows —— 构建基线时传入 --doe-run-dir 注册 DOE 先验操作窗即可启用（C2 drift projection disabled: no operating_windows in baseline (build with --doe-run-dir to enable)）

## 四、防风暴抑制

合并触发 7 组同 key 重复；静默期 30 行；同类抑制窗口 60 分钟；迟滞 5 点

## 五、告警事件摘要（incidents）

| 事件 | 参数 | 类别 | 峰值级别 | 跨度(行) | 告警数 | 规则 |
|------|------|------|----------|----------|--------|------|
| EVT-20261006040121-009 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | spc | high | 204 | 11 | NELSON_R1、NELSON_R5、NELSON_R6… |
| EVT-20261006040121-004 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | spc | high | 97 | 9 | NELSON_R2、NELSON_R3、NELSON_R5… |
| EVT-20261006040121-006 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | multivariate | high | 112 | 2 | ROBUST_Z_OUTLIER |
| EVT-20261006040121-016 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | spc | high | 97 | 2 | NELSON_R6、NELSON_R3 |
| EVT-20261006040121-017 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | multivariate | high | 99 | 2 | ROBUST_Z_OUTLIER |
| EVT-20261006040121-002 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | multivariate | high | 0 | 1 | ROBUST_Z_OUTLIER |
| EVT-20261006040121-011 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | multivariate | high | 0 | 1 | ROBUST_Z_OUTLIER |
| EVT-20261006040121-013 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | multivariate | high | 0 | 1 | ROBUST_Z_OUTLIER |
| EVT-20261006040121-015 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | spc | high | 0 | 1 | NELSON_R6 |
| EVT-20261006040121-019 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | multivariate | high | 0 | 1 | ROBUST_Z_OUTLIER |
| EVT-20261006040121-021 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | multivariate | high | 0 | 1 | ROBUST_Z_OUTLIER |
| EVT-20261006040121-008 | - | regime | warn | 157 | 4 | REGIME_CHANGE_NEW |

（其余 9 个事件见 alert.json 的 events 数组；完整逐段告警在 alerts 数组，契约不变）

## 六、建议后续动作

- 有 `high`/`critical` 告警：按告警中的 `suggested_check` 现场核查；需要根因分析时转 `industrial-diagnostician`，需要参数窗口/工况数据分析时转 `industrial-doe-analyzer`。
- 事件摘要按峰值级别与告警数排序；完整逐段告警在 alert.json 的 `alerts` 数组（契约不变），事件视图在 `events` 数组。
- 本报告由脚本生成（`authored_by: script`）；代理只允许追加中文 `interpretation` 注记，禁止改动任何数值字段。
