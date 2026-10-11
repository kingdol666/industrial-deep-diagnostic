# 产线哨兵巡检报告（watch 模式）

- **生成时间**：2026-10-06T04:32:25.406499+00:00
- **总体状态**：**alert** · 告警数 **47**
- **数据**：`D:\codes\industrial-deep-diagnostic\workspace\aw-exchange\ln-d7e0a2a2_rr-9b067_20261006T123114_merged.csv`（5000 行；时间列 time；分组列 -）
- **基线**：模式：prior（v1.0.0），路径：D:\codes\industrial-deep-diagnostic\workspace\closedloop\sentinel\baselines\演示线1·挤出主机PLC(Modbus TCP)\watch_baseline.json
- **耗时**：65 ms（零 LLM / 零网络，全部统计由确定性脚本计算）


## 一、告警清单

| # | 级别 | 规则 | 参数/指标 | 分组 | 位置 | 观测值 | 建议 |
|---|------|------|-----------|------|------|--------|------|
| 1 | high | ROBUST_Z_OUTLIER | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 2402 | 17.4 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 稳健 z 分数 \|-65.76\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 2 | high | ROBUST_Z_OUTLIER | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 2607 | 0 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 稳健 z 分数 \|-71.85\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 3 | high | ROBUST_Z_OUTLIER | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 2760 | 0 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 稳健 z 分数 \|-71.85\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 4 | high | ROBUST_Z_OUTLIER | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | __ALL__ | 3036 | 69 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) 稳健 z 分数 \|14.56\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 5 | high | NELSON_R1 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 2500 | 200.2 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 6 | high | NELSON_R1 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 2711 | 199.9 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 7 | high | NELSON_R1 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 4999 | 180 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 8 | high | NELSON_R1 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | __ALL__ | 4999 | 69 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 9 | high | NELSON_R5 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 2402 | 17.4 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 10 | high | NELSON_R5 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 2607 | 0 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 11 | high | NELSON_R5 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 2671 | 208.6 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 12 | high | NELSON_R5 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 2760 | 0 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 13 | high | NELSON_R5 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 4999 | 180 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 14 | high | NELSON_R5 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | __ALL__ | 3023 | 65.5 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 15 | high | NELSON_R5 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | __ALL__ | 4999 | 69 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 16 | high | NELSON_R6 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 2402 | 17.4 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 17 | high | NELSON_R6 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 2607 | 0 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 18 | high | NELSON_R6 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 2671 | 208.6 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 19 | high | NELSON_R6 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 2760 | 0 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 20 | high | NELSON_R6 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 4999 | 180 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 21 | high | NELSON_R6 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | __ALL__ | 3023 | 65.5 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 22 | high | NELSON_R6 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | __ALL__ | 4999 | 69 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 23 | warn | NELSON_R2 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 8 | 205.9 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 24 | warn | NELSON_R2 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 2410 | 160.1 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 25 | warn | NELSON_R2 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 2615 | 154.8 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 26 | warn | NELSON_R2 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 2679 | 209.2 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 27 | warn | NELSON_R2 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 2768 | 156.8 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 28 | warn | NELSON_R2 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | __ALL__ | 42 | 5 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 29 | warn | NELSON_R2 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | __ALL__ | 3031 | 64.2 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 30 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 1005 | 205.5 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 31 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 1639 | 206.4 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 32 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 2063 | 205.7 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 33 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 2407 | 138.3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 34 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 2676 | 204.8 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 35 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 2765 | 126.4 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 36 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 2848 | 180.2 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 37 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 3054 | 178.5 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 38 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 3326 | 180.3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 39 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 3541 | 179.6 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 40 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 3721 | 179.3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 41 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 3787 | 178.8 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 42 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 3936 | 180.7 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 43 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 4015 | 180.4 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 44 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 4147 | 180.8 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 45 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 4564 | 180.4 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 46 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 4771 | 181.4 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 47 | warn | NELSON_R3 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | __ALL__ | 4976 | 179.1 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |


> 级别语义：`info` 记录级 / `warn` 趋势与待确认趋势 / `high` 统计异常 / `critical` 越规格。
> 本系统为纯分析系统：所有告警仅为建议核查项，不下发任何参数，动作决策由产线（AWS 侧）做出。

## 二、稳态映射（C3）

- **__ALL__**：steady=5000

## 三、操作窗口投影（C2）

- **C2 漂移投影未启用**：基线中无 operating_windows —— 构建基线时传入 --doe-run-dir 注册 DOE 先验操作窗即可启用（C2 drift projection disabled: no operating_windows in baseline (build with --doe-run-dir to enable)）

## 四、防风暴抑制

合并触发 9 组同 key 重复；静默期 30 行；同类抑制窗口 60 分钟；迟滞 5 点

## 五、告警事件摘要（incidents）

| 事件 | 参数 | 类别 | 峰值级别 | 跨度(行) | 告警数 | 规则 |
|------|------|------|----------|----------|--------|------|
| EVT-20261006043225-007 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | spc | high | 446 | 18 | NELSON_R5、NELSON_R6、NELSON_R3… |
| EVT-20261006043225-020 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | spc | high | 23 | 4 | NELSON_R3、NELSON_R1、NELSON_R5… |
| EVT-20261006043225-010 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | spc | high | 8 | 3 | NELSON_R5、NELSON_R6、NELSON_R2 |
| EVT-20261006043225-021 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | spc | high | 0 | 3 | NELSON_R1、NELSON_R5、NELSON_R6 |
| EVT-20261006043225-006 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | multivariate | high | 0 | 1 | ROBUST_Z_OUTLIER |
| EVT-20261006043225-008 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | multivariate | high | 0 | 1 | ROBUST_Z_OUTLIER |
| EVT-20261006043225-009 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | multivariate | high | 0 | 1 | ROBUST_Z_OUTLIER |
| EVT-20261006043225-011 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | multivariate | high | 0 | 1 | ROBUST_Z_OUTLIER |
| EVT-20261006043225-015 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | spc | warn | 66 | 2 | NELSON_R3 |
| EVT-20261006043225-016 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | spc | warn | 79 | 2 | NELSON_R3 |
| EVT-20261006043225-001 | 演示·挤出主机PLC(Modbus TCP)·熔体温度(dn-0183240d) | spc | warn | 0 | 1 | NELSON_R2 |
| EVT-20261006043225-002 | 演示·晶点计数从站(Modbus RTU)·晶点计数(dn-a41c49cc) | spc | warn | 0 | 1 | NELSON_R2 |

（其余 9 个事件见 alert.json 的 events 数组；完整逐段告警在 alerts 数组，契约不变）

## 六、建议后续动作

- 有 `high`/`critical` 告警：按告警中的 `suggested_check` 现场核查；需要根因分析时转 `industrial-diagnostician`，需要参数窗口/工况数据分析时转 `industrial-doe-analyzer`。
- 事件摘要按峰值级别与告警数排序；完整逐段告警在 alert.json 的 `alerts` 数组（契约不变），事件视图在 `events` 数组。
- 本报告由脚本生成（`authored_by: script`）；代理只允许追加中文 `interpretation` 注记，禁止改动任何数值字段。
