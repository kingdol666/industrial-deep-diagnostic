# 产线哨兵巡检报告（watch 模式）

- **生成时间**：2026-10-12T02:20:49.648367+00:00
- **总体状态**：**alert** · 告警数 **71**
- **数据**：`D:\codes\industrial-deep-diagnostic\workspace\aw-exchange\diag-r3-full.csv`（1466 行；时间列 time；分组列 -）
- **基线**：模式：prior（v1.0.0），路径：D:\codes\industrial-deep-diagnostic\workspace\closedloop\sentinel\baselines\A2O-ln0d5bfeac\watch_baseline.json
- **耗时**：40 ms（零 LLM / 零网络，全部统计由确定性脚本计算）


## 一、告警清单

| # | 级别 | 规则 | 参数/指标 | 分组 | 位置 | 观测值 | 建议 |
|---|------|------|-----------|------|------|--------|------|
| 1 | high | ROBUST_Z_OUTLIER | 好氧区DO(dn-70fb6d7d) | __ALL__ | 34 | 1.58 | 好氧区DO(dn-70fb6d7d) 稳健 z 分数 \|-26.50\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 2 | high | ROBUST_Z_OUTLIER | 好氧区DO(dn-70fb6d7d) | __ALL__ | 1458 | 5.27 | 好氧区DO(dn-70fb6d7d) 稳健 z 分数 \|15.47\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 3 | high | NELSON_R1 | 好氧区DO(dn-70fb6d7d) | __ALL__ | 1465 | 5.11 | 好氧区DO(dn-70fb6d7d) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 4 | high | NELSON_R1 | 进水COD(dn-918bbaa8) | __ALL__ | 50 | 403 | 进水COD(dn-918bbaa8) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 5 | high | NELSON_R1 | 进水COD(dn-918bbaa8) | __ALL__ | 131 | 403 | 进水COD(dn-918bbaa8) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 6 | high | NELSON_R1 | 进水COD(dn-918bbaa8) | __ALL__ | 278 | 403 | 进水COD(dn-918bbaa8) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 7 | high | NELSON_R1 | 进水COD(dn-918bbaa8) | __ALL__ | 710 | 401 | 进水COD(dn-918bbaa8) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 8 | high | NELSON_R1 | 进水COD(dn-918bbaa8) | __ALL__ | 890 | 403 | 进水COD(dn-918bbaa8) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 9 | high | NELSON_R1 | 进水COD(dn-918bbaa8) | __ALL__ | 1063 | 440 | 进水COD(dn-918bbaa8) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 10 | high | NELSON_R1 | 进水COD(dn-918bbaa8) | __ALL__ | 1269 | 440 | 进水COD(dn-918bbaa8) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 11 | high | NELSON_R1 | 进水COD(dn-918bbaa8) | __ALL__ | 1381 | 401 | 进水COD(dn-918bbaa8) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 12 | high | NELSON_R1 | 进水氨氮(dn-74a93dd4) | __ALL__ | 30 | 37.4 | 进水氨氮(dn-74a93dd4) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 13 | high | NELSON_R1 | 进水氨氮(dn-74a93dd4) | __ALL__ | 292 | 33.3 | 进水氨氮(dn-74a93dd4) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 14 | high | NELSON_R1 | 进水氨氮(dn-74a93dd4) | __ALL__ | 463 | 36.8 | 进水氨氮(dn-74a93dd4) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 15 | high | NELSON_R1 | 进水氨氮(dn-74a93dd4) | __ALL__ | 698 | 37.3 | 进水氨氮(dn-74a93dd4) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 16 | high | NELSON_R1 | 进水氨氮(dn-74a93dd4) | __ALL__ | 805 | 37.1 | 进水氨氮(dn-74a93dd4) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 17 | high | NELSON_R1 | 进水氨氮(dn-74a93dd4) | __ALL__ | 1124 | 37.8 | 进水氨氮(dn-74a93dd4) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 18 | high | NELSON_R1 | 进水氨氮(dn-74a93dd4) | __ALL__ | 1270 | 36.9 | 进水氨氮(dn-74a93dd4) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 19 | high | NELSON_R1 | 进水氨氮(dn-74a93dd4) | __ALL__ | 1407 | 32.4 | 进水氨氮(dn-74a93dd4) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 20 | high | NELSON_R1 | 风压PV(dn-884bca68) | __ALL__ | 239 | 62.8 | 风压PV(dn-884bca68) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 21 | high | NELSON_R1 | 风压PV(dn-884bca68) | __ALL__ | 523 | 57.8 | 风压PV(dn-884bca68) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 22 | high | NELSON_R1 | 风压PV(dn-884bca68) | __ALL__ | 796 | 57.8 | 风压PV(dn-884bca68) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 23 | high | NELSON_R1 | 风压PV(dn-884bca68) | __ALL__ | 1191 | 63.4 | 风压PV(dn-884bca68) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 24 | high | NELSON_R5 | 好氧区DO(dn-70fb6d7d) | __ALL__ | 34 | 1.58 | 好氧区DO(dn-70fb6d7d) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 25 | high | NELSON_R5 | 好氧区DO(dn-70fb6d7d) | __ALL__ | 1465 | 5.11 | 好氧区DO(dn-70fb6d7d) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 26 | high | NELSON_R5 | 进水COD(dn-918bbaa8) | __ALL__ | 13 | 424 | 进水COD(dn-918bbaa8) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 27 | high | NELSON_R5 | 进水COD(dn-918bbaa8) | __ALL__ | 692 | 429 | 进水COD(dn-918bbaa8) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 28 | high | NELSON_R5 | 进水COD(dn-918bbaa8) | __ALL__ | 891 | 411 | 进水COD(dn-918bbaa8) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 29 | high | NELSON_R5 | 进水COD(dn-918bbaa8) | __ALL__ | 1417 | 428 | 进水COD(dn-918bbaa8) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 30 | high | NELSON_R5 | 进水氨氮(dn-74a93dd4) | __ALL__ | 16 | 35.2 | 进水氨氮(dn-74a93dd4) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 31 | high | NELSON_R5 | 进水氨氮(dn-74a93dd4) | __ALL__ | 251 | 35.7 | 进水氨氮(dn-74a93dd4) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 32 | high | NELSON_R5 | 进水氨氮(dn-74a93dd4) | __ALL__ | 983 | 35.1 | 进水氨氮(dn-74a93dd4) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 33 | high | NELSON_R5 | 进水氨氮(dn-74a93dd4) | __ALL__ | 1186 | 35.4 | 进水氨氮(dn-74a93dd4) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 34 | high | NELSON_R5 | 进水氨氮(dn-74a93dd4) | __ALL__ | 1295 | 36 | 进水氨氮(dn-74a93dd4) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 35 | high | NELSON_R6 | 好氧区DO(dn-70fb6d7d) | __ALL__ | 34 | 1.58 | 好氧区DO(dn-70fb6d7d) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 36 | high | NELSON_R6 | 好氧区DO(dn-70fb6d7d) | __ALL__ | 1465 | 5.11 | 好氧区DO(dn-70fb6d7d) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 37 | high | NELSON_R6 | 进水COD(dn-918bbaa8) | __ALL__ | 9 | 429 | 进水COD(dn-918bbaa8) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 38 | high | NELSON_R6 | 进水COD(dn-918bbaa8) | __ALL__ | 175 | 428 | 进水COD(dn-918bbaa8) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 39 | high | NELSON_R6 | 进水COD(dn-918bbaa8) | __ALL__ | 527 | 399 | 进水COD(dn-918bbaa8) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 40 | high | NELSON_R6 | 进水COD(dn-918bbaa8) | __ALL__ | 760 | 427 | 进水COD(dn-918bbaa8) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 41 | high | NELSON_R6 | 进水COD(dn-918bbaa8) | __ALL__ | 1109 | 431 | 进水COD(dn-918bbaa8) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 42 | high | NELSON_R6 | 进水氨氮(dn-74a93dd4) | __ALL__ | 15 | 36.3 | 进水氨氮(dn-74a93dd4) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 43 | high | NELSON_R6 | 进水氨氮(dn-74a93dd4) | __ALL__ | 187 | 36.2 | 进水氨氮(dn-74a93dd4) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 44 | high | NELSON_R6 | 进水氨氮(dn-74a93dd4) | __ALL__ | 784 | 33.4 | 进水氨氮(dn-74a93dd4) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 45 | high | NELSON_R6 | 进水氨氮(dn-74a93dd4) | __ALL__ | 900 | 35.4 | 进水氨氮(dn-74a93dd4) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 46 | high | NELSON_R6 | 进水氨氮(dn-74a93dd4) | __ALL__ | 1131 | 34.6 | 进水氨氮(dn-74a93dd4) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 47 | high | NELSON_R6 | 进水氨氮(dn-74a93dd4) | __ALL__ | 1247 | 35.1 | 进水氨氮(dn-74a93dd4) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 48 | high | NELSON_R6 | 进水氨氮(dn-74a93dd4) | __ALL__ | 1411 | 36.2 | 进水氨氮(dn-74a93dd4) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 49 | high | NELSON_R6 | 风压PV(dn-884bca68) | __ALL__ | 180 | 59 | 风压PV(dn-884bca68) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 50 | high | NELSON_R6 | 风压PV(dn-884bca68) | __ALL__ | 284 | 59.5 | 风压PV(dn-884bca68) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 51 | high | NELSON_R6 | 风压PV(dn-884bca68) | __ALL__ | 741 | 58.7 | 风压PV(dn-884bca68) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 52 | warn | NELSON_R2 | 好氧区DO(dn-70fb6d7d) | __ALL__ | 8 | 5.13 | 好氧区DO(dn-70fb6d7d) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 53 | warn | NELSON_R2 | 进水COD(dn-918bbaa8) | __ALL__ | 603 | 434 | 进水COD(dn-918bbaa8) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 54 | warn | NELSON_R2 | 进水COD(dn-918bbaa8) | __ALL__ | 916 | 417 | 进水COD(dn-918bbaa8) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 55 | warn | NELSON_R2 | 进水COD(dn-918bbaa8) | __ALL__ | 1212 | 406 | 进水COD(dn-918bbaa8) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 56 | warn | NELSON_R2 | 进水COD(dn-918bbaa8) | __ALL__ | 1360 | 414 | 进水COD(dn-918bbaa8) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 57 | warn | NELSON_R2 | 进水氨氮(dn-74a93dd4) | __ALL__ | 116 | 35.6 | 进水氨氮(dn-74a93dd4) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 58 | warn | NELSON_R2 | 进水氨氮(dn-74a93dd4) | __ALL__ | 220 | 34.3 | 进水氨氮(dn-74a93dd4) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 59 | warn | NELSON_R2 | 进水氨氮(dn-74a93dd4) | __ALL__ | 565 | 34.5 | 进水氨氮(dn-74a93dd4) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 60 | warn | NELSON_R2 | 进水氨氮(dn-74a93dd4) | __ALL__ | 901 | 35.4 | 进水氨氮(dn-74a93dd4) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 61 | warn | NELSON_R2 | 进水氨氮(dn-74a93dd4) | __ALL__ | 1039 | 34.6 | 进水氨氮(dn-74a93dd4) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 62 | warn | NELSON_R2 | 进水氨氮(dn-74a93dd4) | __ALL__ | 1147 | 34.3 | 进水氨氮(dn-74a93dd4) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 63 | warn | NELSON_R2 | 进水氨氮(dn-74a93dd4) | __ALL__ | 1242 | 35.1 | 进水氨氮(dn-74a93dd4) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 64 | warn | NELSON_R2 | 进水氨氮(dn-74a93dd4) | __ALL__ | 1306 | 34.7 | 进水氨氮(dn-74a93dd4) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 65 | warn | NELSON_R2 | 进水氨氮(dn-74a93dd4) | __ALL__ | 1410 | 34.1 | 进水氨氮(dn-74a93dd4) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 66 | warn | NELSON_R2 | 风压PV(dn-884bca68) | __ALL__ | 113 | 61.8 | 风压PV(dn-884bca68) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 67 | warn | NELSON_R2 | 风压PV(dn-884bca68) | __ALL__ | 1334 | 59.9 | 风压PV(dn-884bca68) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 68 | warn | NELSON_R3 | 好氧区DO(dn-70fb6d7d) | __ALL__ | 39 | 5.02 | 好氧区DO(dn-70fb6d7d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 69 | warn | NELSON_R3 | 好氧区DO(dn-70fb6d7d) | __ALL__ | 826 | 5.1 | 好氧区DO(dn-70fb6d7d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 70 | warn | NELSON_R3 | 好氧区DO(dn-70fb6d7d) | __ALL__ | 1319 | 5 | 好氧区DO(dn-70fb6d7d) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 71 | warn | NELSON_R3 | 风压PV(dn-884bca68) | __ALL__ | 169 | 59.8 | 风压PV(dn-884bca68) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |


> 级别语义：`info` 记录级 / `warn` 趋势与待确认趋势 / `high` 统计异常 / `critical` 越规格。
> 本系统为纯分析系统：所有告警仅为建议核查项，不下发任何参数，动作决策由产线（AWS 侧）做出。

## 二、稳态映射（C3）

- **__ALL__**：steady=1466

## 三、操作窗口投影（C2）

- **C2 漂移投影未启用**：基线中无 operating_windows —— 构建基线时传入 --doe-run-dir 注册 DOE 先验操作窗即可启用（C2 drift projection disabled: no operating_windows in baseline (build with --doe-run-dir to enable)）

## 四、防风暴抑制

合并触发 16 组同 key 重复；静默期 30 行；同类抑制窗口 60 分钟；迟滞 5 点

## 五、告警事件摘要（incidents）

| 事件 | 参数 | 类别 | 峰值级别 | 跨度(行) | 告警数 | 规则 |
|------|------|------|----------|----------|--------|------|
| EVT-20261012022049-009 | 进水氨氮(dn-74a93dd4) | spc | high | 713 | 19 | NELSON_R1、NELSON_R6、NELSON_R2… |
| EVT-20261012022049-003 | 进水氨氮(dn-74a93dd4) | spc | high | 277 | 8 | NELSON_R6、NELSON_R5、NELSON_R1… |
| EVT-20261012022049-013 | 进水COD(dn-918bbaa8) | spc | high | 354 | 7 | NELSON_R1、NELSON_R6、NELSON_R2… |
| EVT-20261012022049-002 | 进水COD(dn-918bbaa8) | spc | high | 269 | 6 | NELSON_R6、NELSON_R5、NELSON_R1 |
| EVT-20261012022049-005 | 风压PV(dn-884bca68) | spc | high | 171 | 5 | NELSON_R2、NELSON_R3、NELSON_R6… |
| EVT-20261012022049-008 | 进水COD(dn-918bbaa8) | spc | high | 233 | 5 | NELSON_R6、NELSON_R2、NELSON_R5… |
| EVT-20261012022049-001 | 好氧区DO(dn-70fb6d7d) | spc | high | 31 | 4 | NELSON_R2、NELSON_R5、NELSON_R6… |
| EVT-20261012022049-012 | 进水COD(dn-918bbaa8) | spc | high | 26 | 3 | NELSON_R1、NELSON_R5、NELSON_R2 |
| EVT-20261012022049-018 | 好氧区DO(dn-70fb6d7d) | spc | high | 0 | 3 | NELSON_R1、NELSON_R5、NELSON_R6 |
| EVT-20261012022049-006 | 进水氨氮(dn-74a93dd4) | spc | high | 102 | 2 | NELSON_R1、NELSON_R2 |
| EVT-20261012022049-010 | 风压PV(dn-884bca68) | spc | high | 55 | 2 | NELSON_R6、NELSON_R1 |
| EVT-20261012022049-004 | 好氧区DO(dn-70fb6d7d) | multivariate | high | 0 | 1 | ROBUST_Z_OUTLIER |

（其余 6 个事件见 alert.json 的 events 数组；完整逐段告警在 alerts 数组，契约不变）

## 六、建议后续动作

- 有 `high`/`critical` 告警：按告警中的 `suggested_check` 现场核查；需要根因分析时转 `industrial-diagnostician`，需要参数窗口/工况数据分析时转 `industrial-doe-analyzer`。
- 事件摘要按峰值级别与告警数排序；完整逐段告警在 alert.json 的 `alerts` 数组（契约不变），事件视图在 `events` 数组。
- 本报告由脚本生成（`authored_by: script`）；代理只允许追加中文 `interpretation` 注记，禁止改动任何数值字段。
