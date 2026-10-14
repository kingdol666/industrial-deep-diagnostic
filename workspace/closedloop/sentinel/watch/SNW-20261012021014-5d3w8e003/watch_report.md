# 产线哨兵巡检报告（watch 模式）

- **生成时间**：2026-10-12T02:10:14.794187+00:00
- **总体状态**：**alert** · 告警数 **33**
- **数据**：`D:\codes\industrial-deep-diagnostic\workspace\aw-exchange\diag-r2-full.csv`（575 行；时间列 time；分组列 -）
- **基线**：模式：prior（v1.0.0），路径：D:\codes\industrial-deep-diagnostic\workspace\closedloop\sentinel\baselines\A2O-ln0d5bfeac\watch_baseline.json
- **耗时**：28 ms（零 LLM / 零网络，全部统计由确定性脚本计算）


## 一、告警清单

| # | 级别 | 规则 | 参数/指标 | 分组 | 位置 | 观测值 | 建议 |
|---|------|------|-----------|------|------|--------|------|
| 1 | high | ROBUST_Z_OUTLIER | 好氧区DO(dn-70fb6d7d) | __ALL__ | 376 | 5.2 | 好氧区DO(dn-70fb6d7d) 稳健 z 分数 \|14.67\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 2 | high | NELSON_R1 | 好氧区DO(dn-70fb6d7d) | __ALL__ | 574 | 5.1 | 好氧区DO(dn-70fb6d7d) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 3 | high | NELSON_R1 | 进水COD(dn-918bbaa8) | __ALL__ | 11 | 437 | 进水COD(dn-918bbaa8) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 4 | high | NELSON_R1 | 进水COD(dn-918bbaa8) | __ALL__ | 125 | 401 | 进水COD(dn-918bbaa8) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 5 | high | NELSON_R1 | 进水COD(dn-918bbaa8) | __ALL__ | 305 | 403 | 进水COD(dn-918bbaa8) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 6 | high | NELSON_R1 | 进水COD(dn-918bbaa8) | __ALL__ | 478 | 440 | 进水COD(dn-918bbaa8) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 7 | high | NELSON_R1 | 进水氨氮(dn-74a93dd4) | __ALL__ | 4 | 33.1 | 进水氨氮(dn-74a93dd4) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 8 | high | NELSON_R1 | 进水氨氮(dn-74a93dd4) | __ALL__ | 113 | 37.3 | 进水氨氮(dn-74a93dd4) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 9 | high | NELSON_R1 | 进水氨氮(dn-74a93dd4) | __ALL__ | 220 | 37.1 | 进水氨氮(dn-74a93dd4) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 10 | high | NELSON_R1 | 进水氨氮(dn-74a93dd4) | __ALL__ | 539 | 37.8 | 进水氨氮(dn-74a93dd4) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 11 | high | NELSON_R1 | 风压PV(dn-884bca68) | __ALL__ | 211 | 57.8 | 风压PV(dn-884bca68) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 12 | high | NELSON_R5 | 好氧区DO(dn-70fb6d7d) | __ALL__ | 574 | 5.1 | 好氧区DO(dn-70fb6d7d) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 13 | high | NELSON_R5 | 进水COD(dn-918bbaa8) | __ALL__ | 2 | 414 | 进水COD(dn-918bbaa8) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 14 | high | NELSON_R5 | 进水COD(dn-918bbaa8) | __ALL__ | 107 | 429 | 进水COD(dn-918bbaa8) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 15 | high | NELSON_R5 | 进水COD(dn-918bbaa8) | __ALL__ | 306 | 411 | 进水COD(dn-918bbaa8) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 16 | high | NELSON_R5 | 进水氨氮(dn-74a93dd4) | __ALL__ | 5 | 34.6 | 进水氨氮(dn-74a93dd4) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 17 | high | NELSON_R5 | 进水氨氮(dn-74a93dd4) | __ALL__ | 398 | 35.1 | 进水氨氮(dn-74a93dd4) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 18 | high | NELSON_R6 | 好氧区DO(dn-70fb6d7d) | __ALL__ | 574 | 5.1 | 好氧区DO(dn-70fb6d7d) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 19 | high | NELSON_R6 | 进水COD(dn-918bbaa8) | __ALL__ | 6 | 417 | 进水COD(dn-918bbaa8) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 20 | high | NELSON_R6 | 进水COD(dn-918bbaa8) | __ALL__ | 175 | 427 | 进水COD(dn-918bbaa8) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 21 | high | NELSON_R6 | 进水COD(dn-918bbaa8) | __ALL__ | 524 | 431 | 进水COD(dn-918bbaa8) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 22 | high | NELSON_R6 | 进水氨氮(dn-74a93dd4) | __ALL__ | 7 | 34.4 | 进水氨氮(dn-74a93dd4) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 23 | high | NELSON_R6 | 进水氨氮(dn-74a93dd4) | __ALL__ | 199 | 33.4 | 进水氨氮(dn-74a93dd4) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 24 | high | NELSON_R6 | 进水氨氮(dn-74a93dd4) | __ALL__ | 315 | 35.4 | 进水氨氮(dn-74a93dd4) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 25 | high | NELSON_R6 | 进水氨氮(dn-74a93dd4) | __ALL__ | 546 | 34.6 | 进水氨氮(dn-74a93dd4) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 26 | high | NELSON_R6 | 风压PV(dn-884bca68) | __ALL__ | 156 | 58.7 | 风压PV(dn-884bca68) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 27 | warn | NELSON_R2 | 好氧区DO(dn-70fb6d7d) | __ALL__ | 8 | 5.01 | 好氧区DO(dn-70fb6d7d) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 28 | warn | NELSON_R2 | 进水COD(dn-918bbaa8) | __ALL__ | 18 | 434 | 进水COD(dn-918bbaa8) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 29 | warn | NELSON_R2 | 进水COD(dn-918bbaa8) | __ALL__ | 331 | 417 | 进水COD(dn-918bbaa8) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 30 | warn | NELSON_R2 | 进水氨氮(dn-74a93dd4) | __ALL__ | 316 | 35.4 | 进水氨氮(dn-74a93dd4) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 31 | warn | NELSON_R2 | 进水氨氮(dn-74a93dd4) | __ALL__ | 454 | 34.6 | 进水氨氮(dn-74a93dd4) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 32 | warn | NELSON_R2 | 进水氨氮(dn-74a93dd4) | __ALL__ | 562 | 34.3 | 进水氨氮(dn-74a93dd4) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 33 | warn | NELSON_R3 | 好氧区DO(dn-70fb6d7d) | __ALL__ | 241 | 5.1 | 好氧区DO(dn-70fb6d7d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |


> 级别语义：`info` 记录级 / `warn` 趋势与待确认趋势 / `high` 统计异常 / `critical` 越规格。
> 本系统为纯分析系统：所有告警仅为建议核查项，不下发任何参数，动作决策由产线（AWS 侧）做出。

## 二、稳态映射（C3）

- **__ALL__**：steady=575

## 三、操作窗口投影（C2）

- **C2 漂移投影未启用**：基线中无 operating_windows —— 构建基线时传入 --doe-run-dir 注册 DOE 先验操作窗即可启用（C2 drift projection disabled: no operating_windows in baseline (build with --doe-run-dir to enable)）

## 四、防风暴抑制

合并触发 9 组同 key 重复；静默期 30 行；同类抑制窗口 60 分钟；迟滞 5 点

## 五、告警事件摘要（incidents）

| 事件 | 参数 | 类别 | 峰值级别 | 跨度(行) | 告警数 | 规则 |
|------|------|------|----------|----------|--------|------|
| EVT-20261012021014-002 | 进水氨氮(dn-74a93dd4) | spc | high | 558 | 13 | NELSON_R1、NELSON_R5、NELSON_R6… |
| EVT-20261012021014-001 | 进水COD(dn-918bbaa8) | spc | high | 173 | 7 | NELSON_R5、NELSON_R6、NELSON_R1… |
| EVT-20261012021014-006 | 进水COD(dn-918bbaa8) | spc | high | 26 | 3 | NELSON_R1、NELSON_R5、NELSON_R2 |
| EVT-20261012021014-009 | 好氧区DO(dn-70fb6d7d) | spc | high | 0 | 3 | NELSON_R1、NELSON_R5、NELSON_R6 |
| EVT-20261012021014-004 | 风压PV(dn-884bca68) | spc | high | 55 | 2 | NELSON_R6、NELSON_R1 |
| EVT-20261012021014-008 | 进水COD(dn-918bbaa8) | spc | high | 46 | 2 | NELSON_R1、NELSON_R6 |
| EVT-20261012021014-007 | 好氧区DO(dn-70fb6d7d) | multivariate | high | 0 | 1 | ROBUST_Z_OUTLIER |
| EVT-20261012021014-003 | 好氧区DO(dn-70fb6d7d) | spc | warn | 0 | 1 | NELSON_R2 |
| EVT-20261012021014-005 | 好氧区DO(dn-70fb6d7d) | spc | warn | 0 | 1 | NELSON_R3 |

## 六、建议后续动作

- 有 `high`/`critical` 告警：按告警中的 `suggested_check` 现场核查；需要根因分析时转 `industrial-diagnostician`，需要参数窗口/工况数据分析时转 `industrial-doe-analyzer`。
- 事件摘要按峰值级别与告警数排序；完整逐段告警在 alert.json 的 `alerts` 数组（契约不变），事件视图在 `events` 数组。
- 本报告由脚本生成（`authored_by: script`）；代理只允许追加中文 `interpretation` 注记，禁止改动任何数值字段。
