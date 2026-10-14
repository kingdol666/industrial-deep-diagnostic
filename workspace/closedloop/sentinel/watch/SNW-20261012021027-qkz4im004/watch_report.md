# 产线哨兵巡检报告（watch 模式）

- **生成时间**：2026-10-12T02:10:27.799135+00:00
- **总体状态**：**alert** · 告警数 **67**
- **数据**：`D:\codes\industrial-deep-diagnostic\workspace\aw-exchange\diag-r3-full.csv`（1465 行；时间列 time；分组列 -）
- **基线**：模式：prior（v1.0.0），路径：D:\codes\industrial-deep-diagnostic\workspace\closedloop\sentinel\baselines\A2O-ln0d5bfeac\watch_baseline.json
- **耗时**：37 ms（零 LLM / 零网络，全部统计由确定性脚本计算）


## 一、告警清单

| # | 级别 | 规则 | 参数/指标 | 分组 | 位置 | 观测值 | 建议 |
|---|------|------|-----------|------|------|--------|------|
| 1 | high | ROBUST_Z_OUTLIER | 好氧区DO(dn-70fb6d7d) | __ALL__ | 333 | 1.58 | 好氧区DO(dn-70fb6d7d) 稳健 z 分数 \|-26.50\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 2 | high | ROBUST_Z_OUTLIER | 好氧区DO(dn-70fb6d7d) | __ALL__ | 542 | 5.24 | 好氧区DO(dn-70fb6d7d) 稳健 z 分数 \|15.13\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 3 | high | NELSON_R1 | 好氧区DO(dn-70fb6d7d) | __ALL__ | 1464 | 4.99 | 好氧区DO(dn-70fb6d7d) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 4 | high | NELSON_R1 | 进水COD(dn-918bbaa8) | __ALL__ | 11 | 400 | 进水COD(dn-918bbaa8) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 5 | high | NELSON_R1 | 进水COD(dn-918bbaa8) | __ALL__ | 176 | 439 | 进水COD(dn-918bbaa8) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 6 | high | NELSON_R1 | 进水COD(dn-918bbaa8) | __ALL__ | 430 | 403 | 进水COD(dn-918bbaa8) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 7 | high | NELSON_R1 | 进水COD(dn-918bbaa8) | __ALL__ | 577 | 403 | 进水COD(dn-918bbaa8) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 8 | high | NELSON_R1 | 进水COD(dn-918bbaa8) | __ALL__ | 1009 | 401 | 进水COD(dn-918bbaa8) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 9 | high | NELSON_R1 | 进水COD(dn-918bbaa8) | __ALL__ | 1189 | 403 | 进水COD(dn-918bbaa8) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 10 | high | NELSON_R1 | 进水COD(dn-918bbaa8) | __ALL__ | 1362 | 440 | 进水COD(dn-918bbaa8) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 11 | high | NELSON_R1 | 进水氨氮(dn-74a93dd4) | __ALL__ | 83 | 36.8 | 进水氨氮(dn-74a93dd4) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 12 | high | NELSON_R1 | 进水氨氮(dn-74a93dd4) | __ALL__ | 329 | 37.4 | 进水氨氮(dn-74a93dd4) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 13 | high | NELSON_R1 | 进水氨氮(dn-74a93dd4) | __ALL__ | 591 | 33.3 | 进水氨氮(dn-74a93dd4) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 14 | high | NELSON_R1 | 进水氨氮(dn-74a93dd4) | __ALL__ | 762 | 36.8 | 进水氨氮(dn-74a93dd4) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 15 | high | NELSON_R1 | 进水氨氮(dn-74a93dd4) | __ALL__ | 997 | 37.3 | 进水氨氮(dn-74a93dd4) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 16 | high | NELSON_R1 | 进水氨氮(dn-74a93dd4) | __ALL__ | 1104 | 37.1 | 进水氨氮(dn-74a93dd4) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 17 | high | NELSON_R1 | 进水氨氮(dn-74a93dd4) | __ALL__ | 1423 | 37.8 | 进水氨氮(dn-74a93dd4) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 18 | high | NELSON_R1 | 风压PV(dn-884bca68) | __ALL__ | 180 | 62.8 | 风压PV(dn-884bca68) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 19 | high | NELSON_R1 | 风压PV(dn-884bca68) | __ALL__ | 538 | 62.8 | 风压PV(dn-884bca68) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 20 | high | NELSON_R1 | 风压PV(dn-884bca68) | __ALL__ | 822 | 57.8 | 风压PV(dn-884bca68) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 21 | high | NELSON_R1 | 风压PV(dn-884bca68) | __ALL__ | 1095 | 57.8 | 风压PV(dn-884bca68) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 22 | high | NELSON_R5 | 好氧区DO(dn-70fb6d7d) | __ALL__ | 333 | 1.58 | 好氧区DO(dn-70fb6d7d) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 23 | high | NELSON_R5 | 好氧区DO(dn-70fb6d7d) | __ALL__ | 1464 | 4.99 | 好氧区DO(dn-70fb6d7d) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 24 | high | NELSON_R5 | 进水COD(dn-918bbaa8) | __ALL__ | 6 | 423 | 进水COD(dn-918bbaa8) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 25 | high | NELSON_R5 | 进水COD(dn-918bbaa8) | __ALL__ | 141 | 426 | 进水COD(dn-918bbaa8) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 26 | high | NELSON_R5 | 进水COD(dn-918bbaa8) | __ALL__ | 991 | 429 | 进水COD(dn-918bbaa8) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 27 | high | NELSON_R5 | 进水COD(dn-918bbaa8) | __ALL__ | 1190 | 411 | 进水COD(dn-918bbaa8) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 28 | high | NELSON_R5 | 进水氨氮(dn-74a93dd4) | __ALL__ | 36 | 34.7 | 进水氨氮(dn-74a93dd4) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 29 | high | NELSON_R5 | 进水氨氮(dn-74a93dd4) | __ALL__ | 187 | 35 | 进水氨氮(dn-74a93dd4) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 30 | high | NELSON_R5 | 进水氨氮(dn-74a93dd4) | __ALL__ | 550 | 35.7 | 进水氨氮(dn-74a93dd4) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 31 | high | NELSON_R5 | 进水氨氮(dn-74a93dd4) | __ALL__ | 1282 | 35.1 | 进水氨氮(dn-74a93dd4) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 32 | high | NELSON_R6 | 好氧区DO(dn-70fb6d7d) | __ALL__ | 333 | 1.58 | 好氧区DO(dn-70fb6d7d) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 33 | high | NELSON_R6 | 好氧区DO(dn-70fb6d7d) | __ALL__ | 1464 | 4.99 | 好氧区DO(dn-70fb6d7d) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 34 | high | NELSON_R6 | 进水COD(dn-918bbaa8) | __ALL__ | 13 | 430 | 进水COD(dn-918bbaa8) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 35 | high | NELSON_R6 | 进水COD(dn-918bbaa8) | __ALL__ | 74 | 410 | 进水COD(dn-918bbaa8) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 36 | high | NELSON_R6 | 进水COD(dn-918bbaa8) | __ALL__ | 474 | 428 | 进水COD(dn-918bbaa8) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 37 | high | NELSON_R6 | 进水COD(dn-918bbaa8) | __ALL__ | 826 | 399 | 进水COD(dn-918bbaa8) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 38 | high | NELSON_R6 | 进水COD(dn-918bbaa8) | __ALL__ | 1059 | 427 | 进水COD(dn-918bbaa8) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 39 | high | NELSON_R6 | 进水COD(dn-918bbaa8) | __ALL__ | 1408 | 431 | 进水COD(dn-918bbaa8) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 40 | high | NELSON_R6 | 进水氨氮(dn-74a93dd4) | __ALL__ | 76 | 34.5 | 进水氨氮(dn-74a93dd4) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 41 | high | NELSON_R6 | 进水氨氮(dn-74a93dd4) | __ALL__ | 486 | 36.2 | 进水氨氮(dn-74a93dd4) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 42 | high | NELSON_R6 | 进水氨氮(dn-74a93dd4) | __ALL__ | 1083 | 33.4 | 进水氨氮(dn-74a93dd4) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 43 | high | NELSON_R6 | 进水氨氮(dn-74a93dd4) | __ALL__ | 1199 | 35.4 | 进水氨氮(dn-74a93dd4) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 44 | high | NELSON_R6 | 进水氨氮(dn-74a93dd4) | __ALL__ | 1430 | 34.6 | 进水氨氮(dn-74a93dd4) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 45 | high | NELSON_R6 | 风压PV(dn-884bca68) | __ALL__ | 131 | 59.3 | 风压PV(dn-884bca68) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 46 | high | NELSON_R6 | 风压PV(dn-884bca68) | __ALL__ | 479 | 59 | 风压PV(dn-884bca68) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 47 | high | NELSON_R6 | 风压PV(dn-884bca68) | __ALL__ | 583 | 59.5 | 风压PV(dn-884bca68) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 48 | high | NELSON_R6 | 风压PV(dn-884bca68) | __ALL__ | 1040 | 58.7 | 风压PV(dn-884bca68) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 49 | warn | NELSON_R2 | 好氧区DO(dn-70fb6d7d) | __ALL__ | 8 | 5.02 | 好氧区DO(dn-70fb6d7d) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 50 | warn | NELSON_R2 | 好氧区DO(dn-70fb6d7d) | __ALL__ | 343 | 5.17 | 好氧区DO(dn-70fb6d7d) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 51 | warn | NELSON_R2 | 进水COD(dn-918bbaa8) | __ALL__ | 108 | 413 | 进水COD(dn-918bbaa8) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 52 | warn | NELSON_R2 | 进水COD(dn-918bbaa8) | __ALL__ | 234 | 430 | 进水COD(dn-918bbaa8) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 53 | warn | NELSON_R2 | 进水COD(dn-918bbaa8) | __ALL__ | 902 | 434 | 进水COD(dn-918bbaa8) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 54 | warn | NELSON_R2 | 进水COD(dn-918bbaa8) | __ALL__ | 1215 | 417 | 进水COD(dn-918bbaa8) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 55 | warn | NELSON_R2 | 进水氨氮(dn-74a93dd4) | __ALL__ | 101 | 36.2 | 进水氨氮(dn-74a93dd4) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 56 | warn | NELSON_R2 | 进水氨氮(dn-74a93dd4) | __ALL__ | 291 | 35.6 | 进水氨氮(dn-74a93dd4) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 57 | warn | NELSON_R2 | 进水氨氮(dn-74a93dd4) | __ALL__ | 415 | 35.6 | 进水氨氮(dn-74a93dd4) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 58 | warn | NELSON_R2 | 进水氨氮(dn-74a93dd4) | __ALL__ | 519 | 34.3 | 进水氨氮(dn-74a93dd4) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 59 | warn | NELSON_R2 | 进水氨氮(dn-74a93dd4) | __ALL__ | 864 | 34.5 | 进水氨氮(dn-74a93dd4) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 60 | warn | NELSON_R2 | 进水氨氮(dn-74a93dd4) | __ALL__ | 1200 | 35.4 | 进水氨氮(dn-74a93dd4) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 61 | warn | NELSON_R2 | 进水氨氮(dn-74a93dd4) | __ALL__ | 1338 | 34.6 | 进水氨氮(dn-74a93dd4) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 62 | warn | NELSON_R2 | 进水氨氮(dn-74a93dd4) | __ALL__ | 1446 | 34.3 | 进水氨氮(dn-74a93dd4) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 63 | warn | NELSON_R2 | 风压PV(dn-884bca68) | __ALL__ | 205 | 59.7 | 风压PV(dn-884bca68) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 64 | warn | NELSON_R2 | 风压PV(dn-884bca68) | __ALL__ | 412 | 61.8 | 风压PV(dn-884bca68) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 65 | warn | NELSON_R3 | 好氧区DO(dn-70fb6d7d) | __ALL__ | 338 | 5.02 | 好氧区DO(dn-70fb6d7d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 66 | warn | NELSON_R3 | 好氧区DO(dn-70fb6d7d) | __ALL__ | 1125 | 5.1 | 好氧区DO(dn-70fb6d7d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 67 | warn | NELSON_R3 | 风压PV(dn-884bca68) | __ALL__ | 468 | 59.8 | 风压PV(dn-884bca68) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |


> 级别语义：`info` 记录级 / `warn` 趋势与待确认趋势 / `high` 统计异常 / `critical` 越规格。
> 本系统为纯分析系统：所有告警仅为建议核查项，不下发任何参数，动作决策由产线（AWS 侧）做出。

## 二、稳态映射（C3）

- **__ALL__**：steady=1465

## 三、操作窗口投影（C2）

- **C2 漂移投影未启用**：基线中无 operating_windows —— 构建基线时传入 --doe-run-dir 注册 DOE 先验操作窗即可启用（C2 drift projection disabled: no operating_windows in baseline (build with --doe-run-dir to enable)）

## 四、防风暴抑制

合并触发 16 组同 key 重复；静默期 30 行；同类抑制窗口 60 分钟；迟滞 5 点

## 五、告警事件摘要（incidents）

| 事件 | 参数 | 类别 | 峰值级别 | 跨度(行) | 告警数 | 规则 |
|------|------|------|----------|----------|--------|------|
| EVT-20261012021027-003 | 进水氨氮(dn-74a93dd4) | spc | high | 555 | 12 | NELSON_R5、NELSON_R6、NELSON_R1… |
| EVT-20261012021027-013 | 进水氨氮(dn-74a93dd4) | spc | high | 449 | 10 | NELSON_R1、NELSON_R6、NELSON_R2… |
| EVT-20261012021027-001 | 进水COD(dn-918bbaa8) | spc | high | 228 | 8 | NELSON_R5、NELSON_R1、NELSON_R6… |
| EVT-20261012021027-007 | 风压PV(dn-884bca68) | spc | high | 171 | 5 | NELSON_R2、NELSON_R3、NELSON_R6… |
| EVT-20261012021027-012 | 进水COD(dn-918bbaa8) | spc | high | 233 | 5 | NELSON_R6、NELSON_R2、NELSON_R5… |
| EVT-20261012021027-006 | 好氧区DO(dn-70fb6d7d) | spc | high | 10 | 4 | NELSON_R5、NELSON_R6、NELSON_R3… |
| EVT-20261012021027-004 | 风压PV(dn-884bca68) | spc | high | 74 | 3 | NELSON_R6、NELSON_R1、NELSON_R2 |
| EVT-20261012021027-008 | 进水COD(dn-918bbaa8) | spc | high | 147 | 3 | NELSON_R1、NELSON_R6 |
| EVT-20261012021027-016 | 进水COD(dn-918bbaa8) | spc | high | 26 | 3 | NELSON_R1、NELSON_R5、NELSON_R2 |
| EVT-20261012021027-018 | 好氧区DO(dn-70fb6d7d) | spc | high | 0 | 3 | NELSON_R1、NELSON_R5、NELSON_R6 |
| EVT-20261012021027-010 | 进水氨氮(dn-74a93dd4) | spc | high | 102 | 2 | NELSON_R1、NELSON_R2 |
| EVT-20261012021027-014 | 风压PV(dn-884bca68) | spc | high | 55 | 2 | NELSON_R6、NELSON_R1 |

（其余 6 个事件见 alert.json 的 events 数组；完整逐段告警在 alerts 数组，契约不变）

## 六、建议后续动作

- 有 `high`/`critical` 告警：按告警中的 `suggested_check` 现场核查；需要根因分析时转 `industrial-diagnostician`，需要参数窗口/工况数据分析时转 `industrial-doe-analyzer`。
- 事件摘要按峰值级别与告警数排序；完整逐段告警在 alert.json 的 `alerts` 数组（契约不变），事件视图在 `events` 数组。
- 本报告由脚本生成（`authored_by: script`）；代理只允许追加中文 `interpretation` 注记，禁止改动任何数值字段。
