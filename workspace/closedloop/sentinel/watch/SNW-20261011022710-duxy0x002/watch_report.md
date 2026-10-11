# 产线哨兵巡检报告（watch 模式）

- **生成时间**：2026-10-11T02:27:10.911465+00:00
- **总体状态**：**alert** · 告警数 **84**
- **数据**：`D:\codes\industrial-deep-diagnostic\workspace\aw-exchange\idd-final-merged.csv`（1150 行；时间列 time；分组列 -）
- **基线**：模式：prior（v1.0.0），路径：D:\codes\industrial-deep-diagnostic\workspace\closedloop\sentinel\baselines\A2O-ln0d5bfeac\watch_baseline.json
- **耗时**：30 ms（零 LLM / 零网络，全部统计由确定性脚本计算）


## 一、告警清单

| # | 级别 | 规则 | 参数/指标 | 分组 | 位置 | 观测值 | 建议 |
|---|------|------|-----------|------|------|--------|------|
| 1 | high | ROBUST_Z_OUTLIER | 好氧区DO(dn-70fb6d7d) | __ALL__ | 1032 | 4.23 | 好氧区DO(dn-70fb6d7d) 稳健 z 分数 \|3.64\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 2 | high | NELSON_R1 | 好氧区DO(dn-70fb6d7d) | __ALL__ | 1034 | 4.19 | 好氧区DO(dn-70fb6d7d) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 3 | high | NELSON_R1 | 进水COD(dn-918bbaa8) | __ALL__ | 17 | 402 | 进水COD(dn-918bbaa8) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 4 | high | NELSON_R1 | 进水COD(dn-918bbaa8) | __ALL__ | 285 | 403 | 进水COD(dn-918bbaa8) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 5 | high | NELSON_R1 | 进水COD(dn-918bbaa8) | __ALL__ | 447 | 394 | 进水COD(dn-918bbaa8) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 6 | high | NELSON_R1 | 进水COD(dn-918bbaa8) | __ALL__ | 535 | 440 | 进水COD(dn-918bbaa8) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 7 | high | NELSON_R1 | 进水COD(dn-918bbaa8) | __ALL__ | 649 | 401 | 进水COD(dn-918bbaa8) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 8 | high | NELSON_R1 | 进水COD(dn-918bbaa8) | __ALL__ | 715 | 440 | 进水COD(dn-918bbaa8) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 9 | high | NELSON_R1 | 进水COD(dn-918bbaa8) | __ALL__ | 806 | 402 | 进水COD(dn-918bbaa8) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 10 | high | NELSON_R1 | 进水氨氮(dn-74a93dd4) | __ALL__ | 69 | 33 | 进水氨氮(dn-74a93dd4) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 11 | high | NELSON_R1 | 进水氨氮(dn-74a93dd4) | __ALL__ | 264 | 37 | 进水氨氮(dn-74a93dd4) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 12 | high | NELSON_R1 | 进水氨氮(dn-74a93dd4) | __ALL__ | 352 | 33.3 | 进水氨氮(dn-74a93dd4) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 13 | high | NELSON_R1 | 进水氨氮(dn-74a93dd4) | __ALL__ | 565 | 32.8 | 进水氨氮(dn-74a93dd4) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 14 | high | NELSON_R1 | 进水氨氮(dn-74a93dd4) | __ALL__ | 627 | 33 | 进水氨氮(dn-74a93dd4) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 15 | high | NELSON_R1 | 进水氨氮(dn-74a93dd4) | __ALL__ | 781 | 38.1 | 进水氨氮(dn-74a93dd4) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 16 | high | NELSON_R1 | 进水氨氮(dn-74a93dd4) | __ALL__ | 995 | 32.9 | 进水氨氮(dn-74a93dd4) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 17 | high | NELSON_R1 | 进水氨氮(dn-74a93dd4) | __ALL__ | 1115 | 33.1 | 进水氨氮(dn-74a93dd4) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 18 | high | NELSON_R1 | 风压PV(dn-884bca68) | __ALL__ | 142 | 57.6 | 风压PV(dn-884bca68) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 19 | high | NELSON_R1 | 风压PV(dn-884bca68) | __ALL__ | 336 | 57.9 | 风压PV(dn-884bca68) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 20 | high | NELSON_R1 | 风压PV(dn-884bca68) | __ALL__ | 768 | 57.9 | 风压PV(dn-884bca68) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 21 | high | NELSON_R1 | 风压PV(dn-884bca68) | __ALL__ | 839 | 57.9 | 风压PV(dn-884bca68) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 22 | high | NELSON_R1 | 风压PV(dn-884bca68) | __ALL__ | 921 | 57.1 | 风压PV(dn-884bca68) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 23 | high | NELSON_R1 | 风压PV(dn-884bca68) | __ALL__ | 1081 | 63 | 风压PV(dn-884bca68) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 24 | high | NELSON_R5 | 好氧区DO(dn-70fb6d7d) | __ALL__ | 1149 | 4.18 | 好氧区DO(dn-70fb6d7d) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 25 | high | NELSON_R5 | 进水COD(dn-918bbaa8) | __ALL__ | 18 | 428 | 进水COD(dn-918bbaa8) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 26 | high | NELSON_R5 | 进水COD(dn-918bbaa8) | __ALL__ | 286 | 429 | 进水COD(dn-918bbaa8) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 27 | high | NELSON_R5 | 进水COD(dn-918bbaa8) | __ALL__ | 571 | 420 | 进水COD(dn-918bbaa8) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 28 | high | NELSON_R5 | 进水COD(dn-918bbaa8) | __ALL__ | 692 | 424 | 进水COD(dn-918bbaa8) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 29 | high | NELSON_R5 | 进水COD(dn-918bbaa8) | __ALL__ | 857 | 416 | 进水COD(dn-918bbaa8) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 30 | high | NELSON_R5 | 进水COD(dn-918bbaa8) | __ALL__ | 950 | 423 | 进水COD(dn-918bbaa8) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 31 | high | NELSON_R5 | 进水氨氮(dn-74a93dd4) | __ALL__ | 4 | 36 | 进水氨氮(dn-74a93dd4) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 32 | high | NELSON_R5 | 进水氨氮(dn-74a93dd4) | __ALL__ | 266 | 36.3 | 进水氨氮(dn-74a93dd4) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 33 | high | NELSON_R5 | 进水氨氮(dn-74a93dd4) | __ALL__ | 334 | 35.3 | 进水氨氮(dn-74a93dd4) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 34 | high | NELSON_R5 | 进水氨氮(dn-74a93dd4) | __ALL__ | 505 | 34.8 | 进水氨氮(dn-74a93dd4) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 35 | high | NELSON_R5 | 进水氨氮(dn-74a93dd4) | __ALL__ | 628 | 35.4 | 进水氨氮(dn-74a93dd4) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 36 | high | NELSON_R5 | 进水氨氮(dn-74a93dd4) | __ALL__ | 1010 | 35.2 | 进水氨氮(dn-74a93dd4) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 37 | high | NELSON_R5 | 风压PV(dn-884bca68) | __ALL__ | 313 | 59.8 | 风压PV(dn-884bca68) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 38 | high | NELSON_R5 | 风压PV(dn-884bca68) | __ALL__ | 482 | 62.1 | 风压PV(dn-884bca68) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 39 | high | NELSON_R5 | 风压PV(dn-884bca68) | __ALL__ | 729 | 59.9 | 风压PV(dn-884bca68) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 40 | high | NELSON_R5 | 风压PV(dn-884bca68) | __ALL__ | 1008 | 58.7 | 风压PV(dn-884bca68) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 41 | high | NELSON_R5 | 风压PV(dn-884bca68) | __ALL__ | 1103 | 60.4 | 风压PV(dn-884bca68) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 42 | high | NELSON_R6 | 好氧区DO(dn-70fb6d7d) | __ALL__ | 90 | 3.85 | 好氧区DO(dn-70fb6d7d) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 43 | high | NELSON_R6 | 好氧区DO(dn-70fb6d7d) | __ALL__ | 773 | 3.87 | 好氧区DO(dn-70fb6d7d) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 44 | high | NELSON_R6 | 好氧区DO(dn-70fb6d7d) | __ALL__ | 952 | 3.84 | 好氧区DO(dn-70fb6d7d) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 45 | high | NELSON_R6 | 好氧区DO(dn-70fb6d7d) | __ALL__ | 1149 | 4.18 | 好氧区DO(dn-70fb6d7d) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 46 | high | NELSON_R6 | 进水COD(dn-918bbaa8) | __ALL__ | 49 | 414 | 进水COD(dn-918bbaa8) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 47 | high | NELSON_R6 | 进水COD(dn-918bbaa8) | __ALL__ | 121 | 426 | 进水COD(dn-918bbaa8) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 48 | high | NELSON_R6 | 进水COD(dn-918bbaa8) | __ALL__ | 187 | 431 | 进水COD(dn-918bbaa8) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 49 | high | NELSON_R6 | 进水COD(dn-918bbaa8) | __ALL__ | 491 | 408 | 进水COD(dn-918bbaa8) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 50 | high | NELSON_R6 | 进水COD(dn-918bbaa8) | __ALL__ | 562 | 412 | 进水COD(dn-918bbaa8) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 51 | high | NELSON_R6 | 进水COD(dn-918bbaa8) | __ALL__ | 751 | 406 | 进水COD(dn-918bbaa8) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 52 | high | NELSON_R6 | 进水COD(dn-918bbaa8) | __ALL__ | 949 | 432 | 进水COD(dn-918bbaa8) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 53 | high | NELSON_R6 | 进水COD(dn-918bbaa8) | __ALL__ | 1087 | 428 | 进水COD(dn-918bbaa8) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 54 | high | NELSON_R6 | 进水氨氮(dn-74a93dd4) | __ALL__ | 22 | 34.7 | 进水氨氮(dn-74a93dd4) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 55 | high | NELSON_R6 | 进水氨氮(dn-74a93dd4) | __ALL__ | 140 | 35.7 | 进水氨氮(dn-74a93dd4) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 56 | high | NELSON_R6 | 进水氨氮(dn-74a93dd4) | __ALL__ | 290 | 34.2 | 进水氨氮(dn-74a93dd4) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 57 | high | NELSON_R6 | 进水氨氮(dn-74a93dd4) | __ALL__ | 369 | 35 | 进水氨氮(dn-74a93dd4) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 58 | high | NELSON_R6 | 进水氨氮(dn-74a93dd4) | __ALL__ | 528 | 34.7 | 进水氨氮(dn-74a93dd4) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 59 | high | NELSON_R6 | 进水氨氮(dn-74a93dd4) | __ALL__ | 724 | 36 | 进水氨氮(dn-74a93dd4) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 60 | high | NELSON_R6 | 进水氨氮(dn-74a93dd4) | __ALL__ | 809 | 34.2 | 进水氨氮(dn-74a93dd4) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 61 | high | NELSON_R6 | 进水氨氮(dn-74a93dd4) | __ALL__ | 934 | 35.7 | 进水氨氮(dn-74a93dd4) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 62 | high | NELSON_R6 | 进水氨氮(dn-74a93dd4) | __ALL__ | 1024 | 34.4 | 进水氨氮(dn-74a93dd4) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 63 | high | NELSON_R6 | 风压PV(dn-884bca68) | __ALL__ | 505 | 59 | 风压PV(dn-884bca68) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 64 | high | NELSON_R6 | 风压PV(dn-884bca68) | __ALL__ | 736 | 58.4 | 风压PV(dn-884bca68) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 65 | high | NELSON_R6 | 风压PV(dn-884bca68) | __ALL__ | 874 | 61 | 风压PV(dn-884bca68) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 66 | high | NELSON_R6 | 风压PV(dn-884bca68) | __ALL__ | 975 | 59.5 | 风压PV(dn-884bca68) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 67 | warn | NELSON_R2 | 好氧区DO(dn-70fb6d7d) | __ALL__ | 46 | 3.86 | 好氧区DO(dn-70fb6d7d) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 68 | warn | NELSON_R2 | 好氧区DO(dn-70fb6d7d) | __ALL__ | 189 | 3.91 | 好氧区DO(dn-70fb6d7d) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 69 | warn | NELSON_R2 | 好氧区DO(dn-70fb6d7d) | __ALL__ | 271 | 3.88 | 好氧区DO(dn-70fb6d7d) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 70 | warn | NELSON_R2 | 好氧区DO(dn-70fb6d7d) | __ALL__ | 337 | 3.9 | 好氧区DO(dn-70fb6d7d) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 71 | warn | NELSON_R2 | 好氧区DO(dn-70fb6d7d) | __ALL__ | 534 | 3.87 | 好氧区DO(dn-70fb6d7d) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 72 | warn | NELSON_R2 | 好氧区DO(dn-70fb6d7d) | __ALL__ | 714 | 3.87 | 好氧区DO(dn-70fb6d7d) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 73 | warn | NELSON_R2 | 好氧区DO(dn-70fb6d7d) | __ALL__ | 790 | 3.84 | 好氧区DO(dn-70fb6d7d) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 74 | warn | NELSON_R2 | 好氧区DO(dn-70fb6d7d) | __ALL__ | 858 | 3.84 | 好氧区DO(dn-70fb6d7d) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 75 | warn | NELSON_R2 | 好氧区DO(dn-70fb6d7d) | __ALL__ | 995 | 3.93 | 好氧区DO(dn-70fb6d7d) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 76 | warn | NELSON_R2 | 进水COD(dn-918bbaa8) | __ALL__ | 120 | 426 | 进水COD(dn-918bbaa8) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 77 | warn | NELSON_R2 | 进水COD(dn-918bbaa8) | __ALL__ | 211 | 409 | 进水COD(dn-918bbaa8) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 78 | warn | NELSON_R2 | 进水COD(dn-918bbaa8) | __ALL__ | 490 | 432 | 进水COD(dn-918bbaa8) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 79 | warn | NELSON_R2 | 进水COD(dn-918bbaa8) | __ALL__ | 636 | 418 | 进水COD(dn-918bbaa8) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 80 | warn | NELSON_R2 | 进水COD(dn-918bbaa8) | __ALL__ | 907 | 417 | 进水COD(dn-918bbaa8) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 81 | warn | NELSON_R2 | 进水氨氮(dn-74a93dd4) | __ALL__ | 277 | 35 | 进水氨氮(dn-74a93dd4) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 82 | warn | NELSON_R2 | 进水氨氮(dn-74a93dd4) | __ALL__ | 448 | 35 | 进水氨氮(dn-74a93dd4) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 83 | warn | NELSON_R2 | 风压PV(dn-884bca68) | __ALL__ | 805 | 60.7 | 风压PV(dn-884bca68) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 84 | warn | NELSON_R2 | 风压PV(dn-884bca68) | __ALL__ | 972 | 59.2 | 风压PV(dn-884bca68) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |


> 级别语义：`info` 记录级 / `warn` 趋势与待确认趋势 / `high` 统计异常 / `critical` 越规格。
> 本系统为纯分析系统：所有告警仅为建议核查项，不下发任何参数，动作决策由产线（AWS 侧）做出。

## 二、稳态映射（C3）

- **__ALL__**：steady=1139、transition=11

## 三、操作窗口投影（C2）

- **C2 漂移投影未启用**：基线中无 operating_windows —— 构建基线时传入 --doe-run-dir 注册 DOE 先验操作窗即可启用（C2 drift projection disabled: no operating_windows in baseline (build with --doe-run-dir to enable)）

## 四、防风暴抑制

合并触发 16 组同 key 重复；静默期 30 行；同类抑制窗口 60 分钟；迟滞 5 点

## 五、告警事件摘要（incidents）

| 事件 | 参数 | 类别 | 峰值级别 | 跨度(行) | 告警数 | 规则 |
|------|------|------|----------|----------|--------|------|
| EVT-20261011022710-005 | 进水氨氮(dn-74a93dd4) | spc | high | 545 | 16 | NELSON_R1、NELSON_R5、NELSON_R2… |
| EVT-20261011022710-007 | 进水COD(dn-918bbaa8) | spc | high | 503 | 16 | NELSON_R1、NELSON_R2、NELSON_R6… |
| EVT-20261011022710-011 | 风压PV(dn-884bca68) | spc | high | 374 | 12 | NELSON_R5、NELSON_R6、NELSON_R1… |
| EVT-20261011022710-002 | 进水COD(dn-918bbaa8) | spc | high | 269 | 9 | NELSON_R1、NELSON_R5、NELSON_R6… |
| EVT-20261011022710-010 | 好氧区DO(dn-70fb6d7d) | spc | high | 435 | 9 | NELSON_R2、NELSON_R6、NELSON_R1… |
| EVT-20261011022710-003 | 好氧区DO(dn-70fb6d7d) | spc | high | 291 | 5 | NELSON_R2、NELSON_R6 |
| EVT-20261011022710-012 | 进水氨氮(dn-74a93dd4) | spc | high | 181 | 5 | NELSON_R6、NELSON_R1、NELSON_R5 |
| EVT-20261011022710-001 | 进水氨氮(dn-74a93dd4) | spc | high | 136 | 4 | NELSON_R5、NELSON_R6、NELSON_R1 |
| EVT-20261011022710-006 | 风压PV(dn-884bca68) | spc | high | 23 | 2 | NELSON_R5、NELSON_R1 |
| EVT-20261011022710-008 | 风压PV(dn-884bca68) | spc | high | 23 | 2 | NELSON_R5、NELSON_R6 |
| EVT-20261011022710-004 | 风压PV(dn-884bca68) | spc | high | 0 | 1 | NELSON_R1 |
| EVT-20261011022710-013 | 好氧区DO(dn-70fb6d7d) | multivariate | high | 0 | 1 | ROBUST_Z_OUTLIER |

（其余 2 个事件见 alert.json 的 events 数组；完整逐段告警在 alerts 数组，契约不变）

## 六、建议后续动作

- 有 `high`/`critical` 告警：按告警中的 `suggested_check` 现场核查；需要根因分析时转 `industrial-diagnostician`，需要参数窗口/工况数据分析时转 `industrial-doe-analyzer`。
- 事件摘要按峰值级别与告警数排序；完整逐段告警在 alert.json 的 `alerts` 数组（契约不变），事件视图在 `events` 数组。
- 本报告由脚本生成（`authored_by: script`）；代理只允许追加中文 `interpretation` 注记，禁止改动任何数值字段。
