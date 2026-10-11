# 产线哨兵巡检报告（watch 模式）

- **生成时间**：2026-10-05T08:13:02.401581+00:00
- **总体状态**：**alert** · 告警数 **4807**
- **数据**：`D:\codes\industrial-deep-diagnostic\workspace\live-demo-20261005\work_watch.csv`（43849 行；时间列 ts_dcs；分组列 shift）
- **基线**：模式：prior（v1.0.0），路径：D:\codes\industrial-deep-diagnostic\workspace\live-demo-20261005\sentinel_baseline.json
- **耗时**：819 ms（零 LLM / 零网络，全部统计由确定性脚本计算）


## 一、告警清单

| # | 级别 | 规则 | 参数/指标 | 分组 | 位置 | 观测值 | 建议 |
|---|------|------|-----------|------|------|--------|------|
| 1 | high | ROBUST_Z_OUTLIER | fan_pump_speed_rpm | 1 | 3779 | 919.6 | fan_pump_speed_rpm 稳健 z 分数 \|3.56\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 2 | high | ROBUST_Z_OUTLIER | fan_pump_speed_rpm | 1 | 4006 | 919.2 | fan_pump_speed_rpm 稳健 z 分数 \|3.52\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 3 | high | ROBUST_Z_OUTLIER | fan_pump_speed_rpm | 1 | 4085 | 922.3 | fan_pump_speed_rpm 稳健 z 分数 \|3.83\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 4 | high | ROBUST_Z_OUTLIER | fan_pump_speed_rpm | 1 | 4386 | 920.6 | fan_pump_speed_rpm 稳健 z 分数 \|3.66\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 5 | high | ROBUST_Z_OUTLIER | fan_pump_speed_rpm | 1 | 4865 | 919.8 | fan_pump_speed_rpm 稳健 z 分数 \|3.58\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 6 | high | ROBUST_Z_OUTLIER | fan_pump_speed_rpm | 1 | 4959 | 920 | fan_pump_speed_rpm 稳健 z 分数 \|3.60\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 7 | high | ROBUST_Z_OUTLIER | fan_pump_speed_rpm | 1 | 5100 | 923.8 | fan_pump_speed_rpm 稳健 z 分数 \|3.98\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 8 | high | ROBUST_Z_OUTLIER | fan_pump_speed_rpm | 1 | 5220 | 919.3 | fan_pump_speed_rpm 稳健 z 分数 \|3.53\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 9 | high | ROBUST_Z_OUTLIER | fan_pump_speed_rpm | 1 | 5350 | 922.3 | fan_pump_speed_rpm 稳健 z 分数 \|3.83\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 10 | high | ROBUST_Z_OUTLIER | fan_pump_speed_rpm | 1 | 8968 | 945.2 | fan_pump_speed_rpm 稳健 z 分数 \|6.15\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 11 | high | ROBUST_Z_OUTLIER | fan_pump_speed_rpm | 1 | 9067 | 940.8 | fan_pump_speed_rpm 稳健 z 分数 \|5.70\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 12 | high | ROBUST_Z_OUTLIER | fan_pump_speed_rpm | 1 | 9189 | 937.4 | fan_pump_speed_rpm 稳健 z 分数 \|5.36\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 13 | high | ROBUST_Z_OUTLIER | fan_pump_speed_rpm | 1 | 10653 | 923.1 | fan_pump_speed_rpm 稳健 z 分数 \|3.91\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 14 | high | ROBUST_Z_OUTLIER | fan_pump_speed_rpm | 1 | 10747 | 920.7 | fan_pump_speed_rpm 稳健 z 分数 \|3.67\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 15 | high | ROBUST_Z_OUTLIER | fan_pump_speed_rpm | 1 | 10846 | 920.2 | fan_pump_speed_rpm 稳健 z 分数 \|3.62\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 16 | high | ROBUST_Z_OUTLIER | fan_pump_speed_rpm | 1 | 12004 | 919.4 | fan_pump_speed_rpm 稳健 z 分数 \|3.54\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 17 | high | ROBUST_Z_OUTLIER | fan_pump_speed_rpm | 1 | 12311 | 920 | fan_pump_speed_rpm 稳健 z 分数 \|3.60\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 18 | high | ROBUST_Z_OUTLIER | fan_pump_speed_rpm | 1 | 12405 | 922.4 | fan_pump_speed_rpm 稳健 z 分数 \|3.84\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 19 | high | ROBUST_Z_OUTLIER | fan_pump_speed_rpm | 1 | 12522 | 922.2 | fan_pump_speed_rpm 稳健 z 分数 \|3.82\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 20 | high | ROBUST_Z_OUTLIER | fan_pump_speed_rpm | 1 | 12636 | 921.5 | fan_pump_speed_rpm 稳健 z 分数 \|3.75\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 21 | high | ROBUST_Z_OUTLIER | fan_pump_speed_rpm | 1 | 12867 | 919.7 | fan_pump_speed_rpm 稳健 z 分数 \|3.57\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 22 | high | ROBUST_Z_OUTLIER | fan_pump_speed_rpm | 1 | 13019 | 920.2 | fan_pump_speed_rpm 稳健 z 分数 \|3.62\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 23 | high | ROBUST_Z_OUTLIER | fan_pump_speed_rpm | 1 | 13548 | 923.3 | fan_pump_speed_rpm 稳健 z 分数 \|3.93\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 24 | high | ROBUST_Z_OUTLIER | fan_pump_speed_rpm | 1 | 13867 | 919.6 | fan_pump_speed_rpm 稳健 z 分数 \|3.56\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 25 | high | ROBUST_Z_OUTLIER | fan_pump_speed_rpm | 1 | 18609 | 937.4 | fan_pump_speed_rpm 稳健 z 分数 \|5.36\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 26 | high | ROBUST_Z_OUTLIER | fan_pump_speed_rpm | 1 | 18853 | 940.5 | fan_pump_speed_rpm 稳健 z 分数 \|5.67\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 27 | high | ROBUST_Z_OUTLIER | fan_pump_speed_rpm | 1 | 19111 | 942.1 | fan_pump_speed_rpm 稳健 z 分数 \|5.83\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 28 | high | ROBUST_Z_OUTLIER | fan_pump_speed_rpm | 1 | 19282 | 942.5 | fan_pump_speed_rpm 稳健 z 分数 \|5.87\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 29 | high | ROBUST_Z_OUTLIER | fan_pump_speed_rpm | 1 | 19468 | 948.8 | fan_pump_speed_rpm 稳健 z 分数 \|6.51\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 30 | high | ROBUST_Z_OUTLIER | fan_pump_speed_rpm | 1 | 19569 | 948.1 | fan_pump_speed_rpm 稳健 z 分数 \|6.44\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 31 | high | ROBUST_Z_OUTLIER | fan_pump_speed_rpm | 1 | 20212 | 950.9 | fan_pump_speed_rpm 稳健 z 分数 \|6.72\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 32 | high | ROBUST_Z_OUTLIER | fan_pump_speed_rpm | 1 | 21161 | 956.3 | fan_pump_speed_rpm 稳健 z 分数 \|7.27\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 33 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 1 | 5544 | 34.26 | headbox_pressure_kPa 稳健 z 分数 \|3.89\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 34 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 1 | 6150 | 32.85 | headbox_pressure_kPa 稳健 z 分数 \|3.56\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 35 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 1 | 7307 | 32.63 | headbox_pressure_kPa 稳健 z 分数 \|3.50\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 36 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 1 | 7459 | 33.1 | headbox_pressure_kPa 稳健 z 分数 \|3.62\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 37 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 1 | 7605 | 32.86 | headbox_pressure_kPa 稳健 z 分数 \|3.56\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 38 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 1 | 7781 | 32.68 | headbox_pressure_kPa 稳健 z 分数 \|3.52\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 39 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 1 | 7920 | 33.07 | headbox_pressure_kPa 稳健 z 分数 \|3.61\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 40 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 1 | 8080 | 33.24 | headbox_pressure_kPa 稳健 z 分数 \|3.65\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 41 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 1 | 8243 | 33.83 | headbox_pressure_kPa 稳健 z 分数 \|3.79\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 42 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 1 | 8408 | 35.03 | headbox_pressure_kPa 稳健 z 分数 \|4.08\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 43 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 1 | 8611 | 34.04 | headbox_pressure_kPa 稳健 z 分数 \|3.84\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 44 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 1 | 8699 | 33.99 | headbox_pressure_kPa 稳健 z 分数 \|3.83\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 45 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 1 | 8803 | 34.58 | headbox_pressure_kPa 稳健 z 分数 \|3.97\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 46 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 1 | 8945 | 37.12 | headbox_pressure_kPa 稳健 z 分数 \|4.58\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 47 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 1 | 9078 | 36.54 | headbox_pressure_kPa 稳健 z 分数 \|4.44\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 48 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 1 | 9218 | 35.99 | headbox_pressure_kPa 稳健 z 分数 \|4.31\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 49 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 1 | 9435 | 35.34 | headbox_pressure_kPa 稳健 z 分数 \|4.15\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 50 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 1 | 9551 | 34.47 | headbox_pressure_kPa 稳健 z 分数 \|3.94\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 51 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 1 | 9746 | 33.49 | headbox_pressure_kPa 稳健 z 分数 \|3.71\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 52 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 1 | 9866 | 32.74 | headbox_pressure_kPa 稳健 z 分数 \|3.53\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 53 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 1 | 10101 | 32.64 | headbox_pressure_kPa 稳健 z 分数 \|3.51\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 54 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 1 | 10565 | 55.94 | headbox_pressure_kPa 稳健 z 分数 \|9.08\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 55 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 1 | 14009 | 34.17 | headbox_pressure_kPa 稳健 z 分数 \|3.87\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 56 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 1 | 16051 | 32.81 | headbox_pressure_kPa 稳健 z 分数 \|3.55\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 57 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 1 | 16197 | 33 | headbox_pressure_kPa 稳健 z 分数 \|3.59\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 58 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 1 | 16348 | 32.64 | headbox_pressure_kPa 稳健 z 分数 \|3.51\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 59 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 1 | 16463 | 32.78 | headbox_pressure_kPa 稳健 z 分数 \|3.54\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 60 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 1 | 16636 | 32.88 | headbox_pressure_kPa 稳健 z 分数 \|3.56\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 61 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 1 | 16810 | 33.12 | headbox_pressure_kPa 稳健 z 分数 \|3.62\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 62 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 1 | 16993 | 34.2 | headbox_pressure_kPa 稳健 z 分数 \|3.88\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 63 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 1 | 17080 | 32.91 | headbox_pressure_kPa 稳健 z 分数 \|3.57\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 64 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 1 | 17157 | 34.44 | headbox_pressure_kPa 稳健 z 分数 \|3.94\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 65 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 1 | 17372 | 34.59 | headbox_pressure_kPa 稳健 z 分数 \|3.97\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 66 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 1 | 17532 | 34.89 | headbox_pressure_kPa 稳健 z 分数 \|4.04\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 67 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 1 | 17735 | 35.1 | headbox_pressure_kPa 稳健 z 分数 \|4.09\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 68 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 1 | 17893 | 34.98 | headbox_pressure_kPa 稳健 z 分数 \|4.07\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 69 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 1 | 18026 | 35.03 | headbox_pressure_kPa 稳健 z 分数 \|4.08\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 70 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 1 | 18192 | 35.21 | headbox_pressure_kPa 稳健 z 分数 \|4.12\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 71 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 1 | 18285 | 33.2 | headbox_pressure_kPa 稳健 z 分数 \|3.64\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 72 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 1 | 18562 | 35.44 | headbox_pressure_kPa 稳健 z 分数 \|4.18\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 73 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 1 | 18691 | 35.55 | headbox_pressure_kPa 稳健 z 分数 \|4.20\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 74 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 1 | 18880 | 36.27 | headbox_pressure_kPa 稳健 z 分数 \|4.37\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 75 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 1 | 18993 | 35.49 | headbox_pressure_kPa 稳健 z 分数 \|4.19\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 76 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 1 | 19125 | 33.04 | headbox_pressure_kPa 稳健 z 分数 \|3.60\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 77 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 1 | 19307 | 38.5 | headbox_pressure_kPa 稳健 z 分数 \|4.91\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 78 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 1 | 19467 | 37.51 | headbox_pressure_kPa 稳健 z 分数 \|4.67\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 79 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 1 | 19650 | 37.77 | headbox_pressure_kPa 稳健 z 分数 \|4.73\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 80 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 1 | 19856 | 38.18 | headbox_pressure_kPa 稳健 z 分数 \|4.83\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 81 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 1 | 19954 | 32.73 | headbox_pressure_kPa 稳健 z 分数 \|3.53\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 82 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 1 | 20116 | 33.18 | headbox_pressure_kPa 稳健 z 分数 \|3.63\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 83 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 1 | 20256 | 32.67 | headbox_pressure_kPa 稳健 z 分数 \|3.51\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 84 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 1 | 20482 | 32.75 | headbox_pressure_kPa 稳健 z 分数 \|3.53\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 85 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 1 | 20650 | 32.88 | headbox_pressure_kPa 稳健 z 分数 \|3.56\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 86 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 1 | 20762 | 38.89 | headbox_pressure_kPa 稳健 z 分数 \|5.00\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 87 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 1 | 20828 | 33.46 | headbox_pressure_kPa 稳健 z 分数 \|3.70\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 88 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 1 | 21185 | 33.78 | headbox_pressure_kPa 稳健 z 分数 \|3.78\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 89 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 1 | 21250 | 39.04 | headbox_pressure_kPa 稳健 z 分数 \|5.04\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 90 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 1 | 21404 | 39.66 | headbox_pressure_kPa 稳健 z 分数 \|5.19\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 91 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 1 | 21559 | 40.14 | headbox_pressure_kPa 稳健 z 分数 \|5.30\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 92 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 1 | 21697 | 40.55 | headbox_pressure_kPa 稳健 z 分数 \|5.40\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 93 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 1 | 21829 | 35.12 | headbox_pressure_kPa 稳健 z 分数 \|4.10\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 94 | high | ROBUST_Z_OUTLIER | stock_temp_C | 1 | 381 | 64.8 | stock_temp_C 稳健 z 分数 \|3.88\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 95 | high | ROBUST_Z_OUTLIER | stock_temp_C | 1 | 10815 | 24.8 | stock_temp_C 稳健 z 分数 \|-4.79\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 96 | high | ROBUST_Z_OUTLIER | stock_temp_C | 1 | 14860 | 29.2 | stock_temp_C 稳健 z 分数 \|-3.83\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 97 | high | ROBUST_Z_OUTLIER | stock_temp_C | 1 | 16673 | 29.3 | stock_temp_C 稳健 z 分数 \|-3.81\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 98 | high | ROBUST_Z_OUTLIER | stock_temp_C | 1 | 16971 | 29.2 | stock_temp_C 稳健 z 分数 \|-3.83\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 99 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 86 | 1.268 | white_water_consistency_pct 稳健 z 分数 \|3.52\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 100 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 266 | 1.339 | white_water_consistency_pct 稳健 z 分数 \|4.18\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 101 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 378 | 0.369 | white_water_consistency_pct 稳健 z 分数 \|-4.83\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 102 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 615 | 1.274 | white_water_consistency_pct 稳健 z 分数 \|3.57\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 103 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 703 | 1.313 | white_water_consistency_pct 稳健 z 分数 \|3.94\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 104 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 805 | 1.812 | white_water_consistency_pct 稳健 z 分数 \|8.57\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 105 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 997 | 1.3 | white_water_consistency_pct 稳健 z 分数 \|3.82\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 106 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 1348 | 1.417 | white_water_consistency_pct 稳健 z 分数 \|4.90\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 107 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 1525 | 0.458 | white_water_consistency_pct 稳健 z 分数 \|-4.00\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 108 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 1610 | 2 | white_water_consistency_pct 稳健 z 分数 \|10.32\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 109 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 1874 | 1.324 | white_water_consistency_pct 稳健 z 分数 \|4.04\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 110 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 1977 | 1.273 | white_water_consistency_pct 稳健 z 分数 \|3.57\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 111 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 2066 | 1.925 | white_water_consistency_pct 稳健 z 分数 \|9.62\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 112 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 2152 | 1.436 | white_water_consistency_pct 稳健 z 分数 \|5.08\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 113 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 2388 | 1.338 | white_water_consistency_pct 稳健 z 分数 \|4.17\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 114 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 2778 | 1.282 | white_water_consistency_pct 稳健 z 分数 \|3.65\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 115 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 3099 | 1.411 | white_water_consistency_pct 稳健 z 分数 \|4.85\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 116 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 3244 | 1.38 | white_water_consistency_pct 稳健 z 分数 \|4.56\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 117 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 3351 | 0.3 | white_water_consistency_pct 稳健 z 分数 \|-5.47\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 118 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 3556 | 0.3 | white_water_consistency_pct 稳健 z 分数 \|-5.47\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 119 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 3633 | 1.716 | white_water_consistency_pct 稳健 z 分数 \|7.68\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 120 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 3699 | 1.266 | white_water_consistency_pct 稳健 z 分数 \|3.50\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 121 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 3866 | 1.412 | white_water_consistency_pct 稳健 z 分数 \|4.86\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 122 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 3931 | 1.303 | white_water_consistency_pct 稳健 z 分数 \|3.84\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 123 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 4138 | 1.397 | white_water_consistency_pct 稳健 z 分数 \|4.72\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 124 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 4270 | 1.328 | white_water_consistency_pct 稳健 z 分数 \|4.08\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 125 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 4370 | 1.345 | white_water_consistency_pct 稳健 z 分数 \|4.23\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 126 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 4488 | 1.323 | white_water_consistency_pct 稳健 z 分数 \|4.03\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 127 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 4568 | 1.354 | white_water_consistency_pct 稳健 z 分数 \|4.32\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 128 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 4699 | 1.328 | white_water_consistency_pct 稳健 z 分数 \|4.08\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 129 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 4778 | 1.288 | white_water_consistency_pct 稳健 z 分数 \|3.70\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 130 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 4910 | 1.379 | white_water_consistency_pct 稳健 z 分数 \|4.55\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 131 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 5024 | 1.37 | white_water_consistency_pct 稳健 z 分数 \|4.47\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 132 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 5133 | 1.269 | white_water_consistency_pct 稳健 z 分数 \|3.53\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 133 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 5305 | 1.641 | white_water_consistency_pct 稳健 z 分数 \|6.98\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 134 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 5547 | 1.267 | white_water_consistency_pct 稳健 z 分数 \|3.51\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 135 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 5612 | 1.285 | white_water_consistency_pct 稳健 z 分数 \|3.68\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 136 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 5785 | 1.36 | white_water_consistency_pct 稳健 z 分数 \|4.37\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 137 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 5870 | 1.308 | white_water_consistency_pct 稳健 z 分数 \|3.89\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 138 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 6037 | 1.299 | white_water_consistency_pct 稳健 z 分数 \|3.81\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 139 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 6103 | 1.443 | white_water_consistency_pct 稳健 z 分数 \|5.14\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 140 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 6358 | 1.527 | white_water_consistency_pct 稳健 z 分数 \|5.92\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 141 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 6516 | 1.336 | white_water_consistency_pct 稳健 z 分数 \|4.15\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 142 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 6786 | 1.287 | white_water_consistency_pct 稳健 z 分数 \|3.70\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 143 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 7034 | 1.268 | white_water_consistency_pct 稳健 z 分数 \|3.52\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 144 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 7318 | 1.32 | white_water_consistency_pct 稳健 z 分数 \|4.00\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 145 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 7387 | 1.504 | white_water_consistency_pct 稳健 z 分数 \|5.71\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 146 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 7722 | 1.32 | white_water_consistency_pct 稳健 z 分数 \|4.00\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 147 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 8082 | 1.311 | white_water_consistency_pct 稳健 z 分数 \|3.92\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 148 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 8608 | 1.295 | white_water_consistency_pct 稳健 z 分数 \|3.77\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 149 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 8822 | 1.469 | white_water_consistency_pct 稳健 z 分数 \|5.39\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 150 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 9173 | 1.269 | white_water_consistency_pct 稳健 z 分数 \|3.53\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 151 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 9765 | 1.294 | white_water_consistency_pct 稳健 z 分数 \|3.76\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 152 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 9989 | 1.445 | white_water_consistency_pct 稳健 z 分数 \|5.16\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 153 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 10122 | 1.405 | white_water_consistency_pct 稳健 z 分数 \|4.79\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 154 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 10251 | 1.297 | white_water_consistency_pct 稳健 z 分数 \|3.79\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 155 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 10382 | 1.266 | white_water_consistency_pct 稳健 z 分数 \|3.50\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 156 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 10513 | 1.537 | white_water_consistency_pct 稳健 z 分数 \|6.02\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 157 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 10643 | 1.289 | white_water_consistency_pct 稳健 z 分数 \|3.71\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 158 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 10747 | 1.311 | white_water_consistency_pct 稳健 z 分数 \|3.92\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 159 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 10818 | 1.29 | white_water_consistency_pct 稳健 z 分数 \|3.72\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 160 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 10929 | 1.3 | white_water_consistency_pct 稳健 z 分数 \|3.82\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 161 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 10990 | 1.304 | white_water_consistency_pct 稳健 z 分数 \|3.85\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 162 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 11120 | 1.427 | white_water_consistency_pct 稳健 z 分数 \|5.00\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 163 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 11364 | 1.304 | white_water_consistency_pct 稳健 z 分数 \|3.85\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 164 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 11535 | 1.279 | white_water_consistency_pct 稳健 z 分数 \|3.62\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 165 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 11835 | 1.294 | white_water_consistency_pct 稳健 z 分数 \|3.76\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 166 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 12041 | 1.355 | white_water_consistency_pct 稳健 z 分数 \|4.33\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 167 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 12123 | 1.526 | white_water_consistency_pct 稳健 z 分数 \|5.91\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 168 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 12244 | 1.357 | white_water_consistency_pct 稳健 z 分数 \|4.35\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 169 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 12387 | 1.463 | white_water_consistency_pct 稳健 z 分数 \|5.33\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 170 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 12480 | 1.269 | white_water_consistency_pct 稳健 z 分数 \|3.53\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 171 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 12546 | 1.289 | white_water_consistency_pct 稳健 z 分数 \|3.71\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 172 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 12643 | 1.38 | white_water_consistency_pct 稳健 z 分数 \|4.56\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 173 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 12713 | 2 | white_water_consistency_pct 稳健 z 分数 \|10.32\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 174 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 12930 | 1.593 | white_water_consistency_pct 稳健 z 分数 \|6.54\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 175 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 13053 | 1.271 | white_water_consistency_pct 稳健 z 分数 \|3.55\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 176 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 13191 | 1.461 | white_water_consistency_pct 稳健 z 分数 \|5.31\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 177 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 13352 | 1.275 | white_water_consistency_pct 稳健 z 分数 \|3.58\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 178 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 13447 | 1.328 | white_water_consistency_pct 稳健 z 分数 \|4.08\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 179 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 13708 | 1.367 | white_water_consistency_pct 稳健 z 分数 \|4.44\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 180 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 14085 | 1.378 | white_water_consistency_pct 稳健 z 分数 \|4.54\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 181 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 14195 | 2 | white_water_consistency_pct 稳健 z 分数 \|10.32\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 182 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 14477 | 1.291 | white_water_consistency_pct 稳健 z 分数 \|3.73\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 183 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 14677 | 1.288 | white_water_consistency_pct 稳健 z 分数 \|3.70\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 184 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 14796 | 1.289 | white_water_consistency_pct 稳健 z 分数 \|3.71\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 185 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 14919 | 1.27 | white_water_consistency_pct 稳健 z 分数 \|3.54\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 186 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 15090 | 1.266 | white_water_consistency_pct 稳健 z 分数 \|3.50\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 187 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 15334 | 1.287 | white_water_consistency_pct 稳健 z 分数 \|3.70\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 188 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 15425 | 1.285 | white_water_consistency_pct 稳健 z 分数 \|3.68\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 189 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 15547 | 1.381 | white_water_consistency_pct 稳健 z 分数 \|4.57\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 190 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 15657 | 1.388 | white_water_consistency_pct 稳健 z 分数 \|4.63\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 191 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 15763 | 1.275 | white_water_consistency_pct 稳健 z 分数 \|3.58\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 192 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 15844 | 1.637 | white_water_consistency_pct 稳健 z 分数 \|6.94\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 193 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 15922 | 1.331 | white_water_consistency_pct 稳健 z 分数 \|4.10\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 194 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 16025 | 1.28 | white_water_consistency_pct 稳健 z 分数 \|3.63\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 195 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 16250 | 1.377 | white_water_consistency_pct 稳健 z 分数 \|4.53\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 196 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 16312 | 1.28 | white_water_consistency_pct 稳健 z 分数 \|3.63\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 197 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 16455 | 1.333 | white_water_consistency_pct 稳健 z 分数 \|4.12\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 198 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 16579 | 1.279 | white_water_consistency_pct 稳健 z 分数 \|3.62\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 199 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 16670 | 1.306 | white_water_consistency_pct 稳健 z 分数 \|3.87\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 200 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 16855 | 1.707 | white_water_consistency_pct 稳健 z 分数 \|7.59\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 201 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 17311 | 1.328 | white_water_consistency_pct 稳健 z 分数 \|4.08\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 202 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 1 | 18787 | 1.289 | white_water_consistency_pct 稳健 z 分数 \|3.71\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 203 | high | ROBUST_Z_OUTLIER | fan_pump_speed_rpm | 2 | 4501 | 919.8 | fan_pump_speed_rpm 稳健 z 分数 \|3.58\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 204 | high | ROBUST_Z_OUTLIER | fan_pump_speed_rpm | 2 | 4777 | 921.3 | fan_pump_speed_rpm 稳健 z 分数 \|3.73\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 205 | high | ROBUST_Z_OUTLIER | fan_pump_speed_rpm | 2 | 4922 | 921 | fan_pump_speed_rpm 稳健 z 分数 \|3.70\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 206 | high | ROBUST_Z_OUTLIER | fan_pump_speed_rpm | 2 | 5059 | 920.4 | fan_pump_speed_rpm 稳健 z 分数 \|3.64\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 207 | high | ROBUST_Z_OUTLIER | fan_pump_speed_rpm | 2 | 5257 | 924.1 | fan_pump_speed_rpm 稳健 z 分数 \|4.01\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 208 | high | ROBUST_Z_OUTLIER | fan_pump_speed_rpm | 2 | 5330 | 919.3 | fan_pump_speed_rpm 稳健 z 分数 \|3.53\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 209 | high | ROBUST_Z_OUTLIER | fan_pump_speed_rpm | 2 | 5414 | 919.5 | fan_pump_speed_rpm 稳健 z 分数 \|3.55\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 210 | high | ROBUST_Z_OUTLIER | fan_pump_speed_rpm | 2 | 5555 | 923.9 | fan_pump_speed_rpm 稳健 z 分数 \|3.99\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 211 | high | ROBUST_Z_OUTLIER | fan_pump_speed_rpm | 2 | 5929 | 919.1 | fan_pump_speed_rpm 稳健 z 分数 \|3.51\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 212 | high | ROBUST_Z_OUTLIER | fan_pump_speed_rpm | 2 | 6037 | 922.5 | fan_pump_speed_rpm 稳健 z 分数 \|3.85\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 213 | high | ROBUST_Z_OUTLIER | fan_pump_speed_rpm | 2 | 9171 | 942.7 | fan_pump_speed_rpm 稳健 z 分数 \|5.89\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 214 | high | ROBUST_Z_OUTLIER | fan_pump_speed_rpm | 2 | 9238 | 939 | fan_pump_speed_rpm 稳健 z 分数 \|5.52\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 215 | high | ROBUST_Z_OUTLIER | fan_pump_speed_rpm | 2 | 9331 | 940.8 | fan_pump_speed_rpm 稳健 z 分数 \|5.70\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 216 | high | ROBUST_Z_OUTLIER | fan_pump_speed_rpm | 2 | 9471 | 928.8 | fan_pump_speed_rpm 稳健 z 分数 \|4.49\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 217 | high | ROBUST_Z_OUTLIER | fan_pump_speed_rpm | 2 | 11151 | 919.9 | fan_pump_speed_rpm 稳健 z 分数 \|3.59\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 218 | high | ROBUST_Z_OUTLIER | fan_pump_speed_rpm | 2 | 12811 | 919.1 | fan_pump_speed_rpm 稳健 z 分数 \|3.51\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 219 | high | ROBUST_Z_OUTLIER | fan_pump_speed_rpm | 2 | 13058 | 920.5 | fan_pump_speed_rpm 稳健 z 分数 \|3.65\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 220 | high | ROBUST_Z_OUTLIER | fan_pump_speed_rpm | 2 | 13271 | 920.8 | fan_pump_speed_rpm 稳健 z 分数 \|3.68\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 221 | high | ROBUST_Z_OUTLIER | fan_pump_speed_rpm | 2 | 19437 | 949.9 | fan_pump_speed_rpm 稳健 z 分数 \|6.62\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 222 | high | ROBUST_Z_OUTLIER | fan_pump_speed_rpm | 2 | 19584 | 941.3 | fan_pump_speed_rpm 稳健 z 分数 \|5.75\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 223 | high | ROBUST_Z_OUTLIER | fan_pump_speed_rpm | 2 | 19849 | 945.1 | fan_pump_speed_rpm 稳健 z 分数 \|6.14\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 224 | high | ROBUST_Z_OUTLIER | fan_pump_speed_rpm | 2 | 20074 | 943.6 | fan_pump_speed_rpm 稳健 z 分数 \|5.99\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 225 | high | ROBUST_Z_OUTLIER | fan_pump_speed_rpm | 2 | 21911 | 958.1 | fan_pump_speed_rpm 稳健 z 分数 \|7.45\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 226 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 2 | 7305 | 32.82 | headbox_pressure_kPa 稳健 z 分数 \|3.51\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 227 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 2 | 7418 | 33.12 | headbox_pressure_kPa 稳健 z 分数 \|3.58\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 228 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 2 | 7592 | 32.96 | headbox_pressure_kPa 稳健 z 分数 \|3.54\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 229 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 2 | 7710 | 32.8 | headbox_pressure_kPa 稳健 z 分数 \|3.51\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 230 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 2 | 7883 | 32.92 | headbox_pressure_kPa 稳健 z 分数 \|3.54\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 231 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 2 | 8002 | 32.88 | headbox_pressure_kPa 稳健 z 分数 \|3.53\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 232 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 2 | 8158 | 33.14 | headbox_pressure_kPa 稳健 z 分数 \|3.59\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 233 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 2 | 8334 | 33.35 | headbox_pressure_kPa 稳健 z 分数 \|3.64\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 234 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 2 | 8512 | 33.9 | headbox_pressure_kPa 稳健 z 分数 \|3.77\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 235 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 2 | 8723 | 33.92 | headbox_pressure_kPa 稳健 z 分数 \|3.77\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 236 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 2 | 8834 | 34.06 | headbox_pressure_kPa 稳健 z 分数 \|3.81\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 237 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 2 | 8969 | 34.76 | headbox_pressure_kPa 稳健 z 分数 \|3.97\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 238 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 2 | 9064 | 33.3 | headbox_pressure_kPa 稳健 z 分数 \|3.63\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 239 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 2 | 9139 | 37.23 | headbox_pressure_kPa 稳健 z 分数 \|4.56\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 240 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 2 | 9279 | 36.3 | headbox_pressure_kPa 稳健 z 分数 \|4.34\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 241 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 2 | 9436 | 36.58 | headbox_pressure_kPa 稳健 z 分数 \|4.40\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 242 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 2 | 9642 | 35.36 | headbox_pressure_kPa 稳健 z 分数 \|4.11\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 243 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 2 | 9791 | 34.54 | headbox_pressure_kPa 稳健 z 分数 \|3.92\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 244 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 2 | 9969 | 33.39 | headbox_pressure_kPa 稳健 z 分数 \|3.65\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 245 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 2 | 10144 | 32.9 | headbox_pressure_kPa 稳健 z 分数 \|3.53\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 246 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 2 | 10341 | 32.78 | headbox_pressure_kPa 稳健 z 分数 \|3.50\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 247 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 2 | 12748 | 33.13 | headbox_pressure_kPa 稳健 z 分数 \|3.59\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 248 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 2 | 15968 | 32.78 | headbox_pressure_kPa 稳健 z 分数 \|3.50\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 249 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 2 | 16478 | 32.82 | headbox_pressure_kPa 稳健 z 分数 \|3.51\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 250 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 2 | 16656 | 33.1 | headbox_pressure_kPa 稳健 z 分数 \|3.58\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 251 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 2 | 16807 | 32.79 | headbox_pressure_kPa 稳健 z 分数 \|3.50\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 252 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 2 | 16969 | 32.81 | headbox_pressure_kPa 稳健 z 分数 \|3.51\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 253 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 2 | 17172 | 33.54 | headbox_pressure_kPa 稳健 z 分数 \|3.68\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 254 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 2 | 17349 | 34 | headbox_pressure_kPa 稳健 z 分数 \|3.79\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 255 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 2 | 17519 | 34.44 | headbox_pressure_kPa 稳健 z 分数 \|3.90\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 256 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 2 | 17689 | 35.74 | headbox_pressure_kPa 稳健 z 分数 \|4.20\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 257 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 2 | 17942 | 34.86 | headbox_pressure_kPa 稳健 z 分数 \|4.00\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 258 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 2 | 18052 | 35.12 | headbox_pressure_kPa 稳健 z 分数 \|4.06\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 259 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 2 | 18198 | 35.22 | headbox_pressure_kPa 稳健 z 分数 \|4.08\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 260 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 2 | 18350 | 34.69 | headbox_pressure_kPa 稳健 z 分数 \|3.95\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 261 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 2 | 18496 | 35.48 | headbox_pressure_kPa 稳健 z 分数 \|4.14\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 262 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 2 | 18729 | 35.09 | headbox_pressure_kPa 稳健 z 分数 \|4.05\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 263 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 2 | 18854 | 35.87 | headbox_pressure_kPa 稳健 z 分数 \|4.23\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 264 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 2 | 18980 | 35.48 | headbox_pressure_kPa 稳健 z 分数 \|4.14\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 265 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 2 | 19143 | 37.16 | headbox_pressure_kPa 稳健 z 分数 \|4.54\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 266 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 2 | 19244 | 35.94 | headbox_pressure_kPa 稳健 z 分数 \|4.25\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 267 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 2 | 19378 | 37.56 | headbox_pressure_kPa 稳健 z 分数 \|4.63\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 268 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 2 | 19504 | 34.01 | headbox_pressure_kPa 稳健 z 分数 \|3.79\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 269 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 2 | 19631 | 32.82 | headbox_pressure_kPa 稳健 z 分数 \|3.51\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 270 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 2 | 19719 | 37.16 | headbox_pressure_kPa 稳健 z 分数 \|4.54\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 271 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 2 | 19847 | 32.91 | headbox_pressure_kPa 稳健 z 分数 \|3.53\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 272 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 2 | 19939 | 37.71 | headbox_pressure_kPa 稳健 z 分数 \|4.67\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 273 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 2 | 20031 | 33.38 | headbox_pressure_kPa 稳健 z 分数 \|3.64\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 274 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 2 | 20139 | 32.96 | headbox_pressure_kPa 稳健 z 分数 \|3.54\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 275 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 2 | 20249 | 38.52 | headbox_pressure_kPa 稳健 z 分数 \|4.86\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 276 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 2 | 20451 | 32.91 | headbox_pressure_kPa 稳健 z 分数 \|3.53\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 277 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 2 | 20557 | 33.04 | headbox_pressure_kPa 稳健 z 分数 \|3.56\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 278 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 2 | 20690 | 33.05 | headbox_pressure_kPa 稳健 z 分数 \|3.57\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 279 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 2 | 20827 | 32.96 | headbox_pressure_kPa 稳健 z 分数 \|3.54\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 280 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 2 | 21064 | 33.15 | headbox_pressure_kPa 稳健 z 分数 \|3.59\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 281 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 2 | 21171 | 33.7 | headbox_pressure_kPa 稳健 z 分数 \|3.72\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 282 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 2 | 21307 | 33.82 | headbox_pressure_kPa 稳健 z 分数 \|3.75\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 283 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 2 | 21520 | 40.17 | headbox_pressure_kPa 稳健 z 分数 \|5.25\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 284 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 2 | 21639 | 34.6 | headbox_pressure_kPa 稳健 z 分数 \|3.93\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 285 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 2 | 21732 | 40.76 | headbox_pressure_kPa 稳健 z 分数 \|5.39\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 286 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 2 | 21844 | 40.4 | headbox_pressure_kPa 稳健 z 分数 \|5.31\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 287 | high | ROBUST_Z_OUTLIER | headbox_pressure_kPa | 2 | 21933 | 34.8 | headbox_pressure_kPa 稳健 z 分数 \|3.98\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 288 | high | ROBUST_Z_OUTLIER | stock_temp_C | 2 | 8197 | 30.1 | stock_temp_C 稳健 z 分数 \|-3.64\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 289 | high | ROBUST_Z_OUTLIER | stock_temp_C | 2 | 12663 | 30.4 | stock_temp_C 稳健 z 分数 \|-3.57\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 290 | high | ROBUST_Z_OUTLIER | stock_temp_C | 2 | 14440 | 29.7 | stock_temp_C 稳健 z 分数 \|-3.73\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 291 | high | ROBUST_Z_OUTLIER | stock_temp_C | 2 | 18370 | 30.2 | stock_temp_C 稳健 z 分数 \|-3.62\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 292 | high | ROBUST_Z_OUTLIER | stock_temp_C | 2 | 20628 | 69.8 | stock_temp_C 稳健 z 分数 \|4.96\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 293 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 5 | 1.781 | white_water_consistency_pct 稳健 z 分数 \|8.44\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 294 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 262 | 0.495 | white_water_consistency_pct 稳健 z 分数 \|-3.75\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 295 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 424 | 1.266 | white_water_consistency_pct 稳健 z 分数 \|3.55\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 296 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 957 | 1.368 | white_water_consistency_pct 稳健 z 分数 \|4.52\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 297 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 1157 | 0.507 | white_water_consistency_pct 稳健 z 分数 \|-3.64\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 298 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 1258 | 1.717 | white_water_consistency_pct 稳健 z 分数 \|7.83\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 299 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 1517 | 1.485 | white_water_consistency_pct 稳健 z 分数 \|5.63\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 300 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 1658 | 1.845 | white_water_consistency_pct 稳健 z 分数 \|9.04\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 301 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 1811 | 1.395 | white_water_consistency_pct 稳健 z 分数 \|4.78\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 302 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 1873 | 1.276 | white_water_consistency_pct 稳健 z 分数 \|3.65\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 303 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 2025 | 1.543 | white_water_consistency_pct 稳健 z 分数 \|6.18\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 304 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 2368 | 0.51 | white_water_consistency_pct 稳健 z 分数 \|-3.61\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 305 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 2526 | 0.3 | white_water_consistency_pct 稳健 z 分数 \|-5.60\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 306 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 2685 | 1.519 | white_water_consistency_pct 稳健 z 分数 \|5.95\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 307 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 2788 | 1.263 | white_water_consistency_pct 稳健 z 分数 \|3.53\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 308 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 2850 | 1.387 | white_water_consistency_pct 稳健 z 分数 \|4.70\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 309 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 3020 | 1.263 | white_water_consistency_pct 稳健 z 分数 \|3.53\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 310 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 3303 | 1.397 | white_water_consistency_pct 稳健 z 分数 \|4.80\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 311 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 3510 | 1.29 | white_water_consistency_pct 稳健 z 分数 \|3.78\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 312 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 3596 | 1.447 | white_water_consistency_pct 稳健 z 分数 \|5.27\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 313 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 3795 | 1.261 | white_water_consistency_pct 稳健 z 分数 \|3.51\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 314 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 3926 | 1.523 | white_water_consistency_pct 稳健 z 分数 \|5.99\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 315 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 4334 | 1.399 | white_water_consistency_pct 稳健 z 分数 \|4.81\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 316 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 4583 | 1.419 | white_water_consistency_pct 稳健 z 分数 \|5.00\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 317 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 4786 | 1.262 | white_water_consistency_pct 稳健 z 分数 \|3.52\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 318 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 4980 | 1.286 | white_water_consistency_pct 稳健 z 分数 \|3.74\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 319 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 5057 | 1.28 | white_water_consistency_pct 稳健 z 分数 \|3.69\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 320 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 5133 | 1.27 | white_water_consistency_pct 稳健 z 分数 \|3.59\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 321 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 5239 | 1.292 | white_water_consistency_pct 稳健 z 分数 \|3.80\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 322 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 5345 | 0.485 | white_water_consistency_pct 稳健 z 分数 \|-3.85\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 323 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 5442 | 1.377 | white_water_consistency_pct 稳健 z 分数 \|4.61\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 324 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 5665 | 1.329 | white_water_consistency_pct 稳健 z 分数 \|4.15\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 325 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 5788 | 1.394 | white_water_consistency_pct 稳健 z 分数 \|4.77\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 326 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 6112 | 1.562 | white_water_consistency_pct 稳健 z 分数 \|6.36\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 327 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 6473 | 1.401 | white_water_consistency_pct 稳健 z 分数 \|4.83\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 328 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 6668 | 1.273 | white_water_consistency_pct 稳健 z 分数 \|3.62\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 329 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 6732 | 1.284 | white_water_consistency_pct 稳健 z 分数 \|3.72\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 330 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 7052 | 0.486 | white_water_consistency_pct 稳健 z 分数 \|-3.84\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 331 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 7216 | 1.54 | white_water_consistency_pct 稳健 z 分数 \|6.15\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 332 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 7397 | 1.468 | white_water_consistency_pct 稳健 z 分数 \|5.47\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 333 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 7935 | 1.333 | white_water_consistency_pct 稳健 z 分数 \|4.19\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 334 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 8254 | 1.705 | white_water_consistency_pct 稳健 z 分数 \|7.72\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 335 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 8559 | 1.262 | white_water_consistency_pct 稳健 z 分数 \|3.52\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 336 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 9939 | 1.282 | white_water_consistency_pct 稳健 z 分数 \|3.71\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 337 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 10001 | 1.262 | white_water_consistency_pct 稳健 z 分数 \|3.52\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 338 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 10510 | 1.512 | white_water_consistency_pct 稳健 z 分数 \|5.89\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 339 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 10935 | 1.284 | white_water_consistency_pct 稳健 z 分数 \|3.72\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 340 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 10998 | 1.338 | white_water_consistency_pct 稳健 z 分数 \|4.24\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 341 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 11070 | 0.508 | white_water_consistency_pct 稳健 z 分数 \|-3.63\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 342 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 11289 | 1.304 | white_water_consistency_pct 稳健 z 分数 \|3.91\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 343 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 11514 | 1.398 | white_water_consistency_pct 稳健 z 分数 \|4.81\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 344 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 11768 | 0.3 | white_water_consistency_pct 稳健 z 分数 \|-5.60\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 345 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 11896 | 1.293 | white_water_consistency_pct 稳健 z 分数 \|3.81\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 346 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 12159 | 1.36 | white_water_consistency_pct 稳健 z 分数 \|4.45\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 347 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 12431 | 1.681 | white_water_consistency_pct 稳健 z 分数 \|7.49\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 348 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 12798 | 1.288 | white_water_consistency_pct 稳健 z 分数 \|3.76\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 349 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 12960 | 1.297 | white_water_consistency_pct 稳健 z 分数 \|3.85\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 350 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 13036 | 1.297 | white_water_consistency_pct 稳健 z 分数 \|3.85\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 351 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 13221 | 1.271 | white_water_consistency_pct 稳健 z 分数 \|3.60\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 352 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 13452 | 1.35 | white_water_consistency_pct 稳健 z 分数 \|4.35\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 353 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 13532 | 2 | white_water_consistency_pct 稳健 z 分数 \|10.51\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 354 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 13636 | 1.332 | white_water_consistency_pct 稳健 z 分数 \|4.18\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 355 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 13749 | 2 | white_water_consistency_pct 稳健 z 分数 \|10.51\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 356 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 13871 | 1.375 | white_water_consistency_pct 稳健 z 分数 \|4.59\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 357 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 14061 | 1.415 | white_water_consistency_pct 稳健 z 分数 \|4.97\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 358 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 14249 | 1.708 | white_water_consistency_pct 稳健 z 分数 \|7.74\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 359 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 14338 | 1.283 | white_water_consistency_pct 稳健 z 分数 \|3.72\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 360 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 14577 | 1.27 | white_water_consistency_pct 稳健 z 分数 \|3.59\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 361 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 14699 | 1.293 | white_water_consistency_pct 稳健 z 分数 \|3.81\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 362 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 15061 | 1.326 | white_water_consistency_pct 稳健 z 分数 \|4.12\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 363 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 15197 | 1.294 | white_water_consistency_pct 稳健 z 分数 \|3.82\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 364 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 15294 | 1.36 | white_water_consistency_pct 稳健 z 分数 \|4.45\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 365 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 15440 | 1.285 | white_water_consistency_pct 稳健 z 分数 \|3.73\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 366 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 15793 | 1.528 | white_water_consistency_pct 稳健 z 分数 \|6.04\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 367 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 16107 | 1.295 | white_water_consistency_pct 稳健 z 分数 \|3.83\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 368 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 16338 | 1.321 | white_water_consistency_pct 稳健 z 分数 \|4.08\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 369 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 16410 | 1.55 | white_water_consistency_pct 稳健 z 分数 \|6.25\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 370 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 16652 | 1.631 | white_water_consistency_pct 稳健 z 分数 \|7.01\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 371 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 17198 | 1.262 | white_water_consistency_pct 稳健 z 分数 \|3.52\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 372 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 17836 | 1.299 | white_water_consistency_pct 稳健 z 分数 \|3.87\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 373 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 17996 | 1.301 | white_water_consistency_pct 稳健 z 分数 \|3.89\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 374 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 18525 | 1.273 | white_water_consistency_pct 稳健 z 分数 \|3.62\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 375 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 18607 | 1.338 | white_water_consistency_pct 稳健 z 分数 \|4.24\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 376 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 18825 | 1.277 | white_water_consistency_pct 稳健 z 分数 \|3.66\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 377 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 18976 | 1.289 | white_water_consistency_pct 稳健 z 分数 \|3.77\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 378 | high | ROBUST_Z_OUTLIER | white_water_consistency_pct | 2 | 19431 | 1.493 | white_water_consistency_pct 稳健 z 分数 \|5.71\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 379 | high | NELSON_R1 | fan_pump_speed_rpm | 1 | 28 | 901.2 | fan_pump_speed_rpm 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 380 | high | NELSON_R1 | fan_pump_speed_rpm | 1 | 5950 | 914.3 | fan_pump_speed_rpm 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 381 | high | NELSON_R1 | fan_pump_speed_rpm | 1 | 6081 | 905.1 | fan_pump_speed_rpm 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 382 | high | NELSON_R1 | fan_pump_speed_rpm | 1 | 6225 | 914.1 | fan_pump_speed_rpm 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 383 | high | NELSON_R1 | fan_pump_speed_rpm | 1 | 6724 | 913.3 | fan_pump_speed_rpm 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 384 | high | NELSON_R1 | fan_pump_speed_rpm | 1 | 6936 | 910.8 | fan_pump_speed_rpm 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 385 | high | NELSON_R1 | fan_pump_speed_rpm | 1 | 10072 | 912.1 | fan_pump_speed_rpm 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 386 | high | NELSON_R1 | fan_pump_speed_rpm | 1 | 10256 | 919.6 | fan_pump_speed_rpm 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 387 | high | NELSON_R1 | fan_pump_speed_rpm | 1 | 10359 | 909.6 | fan_pump_speed_rpm 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 388 | high | NELSON_R1 | fan_pump_speed_rpm | 1 | 10509 | 909.2 | fan_pump_speed_rpm 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 389 | high | NELSON_R1 | fan_pump_speed_rpm | 1 | 10606 | 917.1 | fan_pump_speed_rpm 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 390 | high | NELSON_R1 | fan_pump_speed_rpm | 1 | 13144 | 912.7 | fan_pump_speed_rpm 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 391 | high | NELSON_R1 | fan_pump_speed_rpm | 1 | 13214 | 910.7 | fan_pump_speed_rpm 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 392 | high | NELSON_R1 | fan_pump_speed_rpm | 1 | 13308 | 917.9 | fan_pump_speed_rpm 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 393 | high | NELSON_R1 | fan_pump_speed_rpm | 1 | 13402 | 909.6 | fan_pump_speed_rpm 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 394 | high | NELSON_R1 | fan_pump_speed_rpm | 1 | 13606 | 914.3 | fan_pump_speed_rpm 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 395 | high | NELSON_R1 | fan_pump_speed_rpm | 1 | 14121 | 915.4 | fan_pump_speed_rpm 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 396 | high | NELSON_R1 | fan_pump_speed_rpm | 1 | 14222 | 912.1 | fan_pump_speed_rpm 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 397 | high | NELSON_R1 | fan_pump_speed_rpm | 1 | 14460 | 918.5 | fan_pump_speed_rpm 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 398 | high | NELSON_R1 | fan_pump_speed_rpm | 1 | 14777 | 916.7 | fan_pump_speed_rpm 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 399 | high | NELSON_R1 | fan_pump_speed_rpm | 1 | 14866 | 918.4 | fan_pump_speed_rpm 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 400 | high | NELSON_R1 | fan_pump_speed_rpm | 1 | 16194 | 913.5 | fan_pump_speed_rpm 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 401 | high | NELSON_R1 | fan_pump_speed_rpm | 1 | 21860 | 938.2 | fan_pump_speed_rpm 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 402 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 25 | 23.98 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 403 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 154 | 24.03 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 404 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 292 | 24.44 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 405 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 466 | 24.34 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 406 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 611 | 24.27 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 407 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 783 | 24.3 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 408 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 882 | 22.84 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 409 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 962 | 24.04 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 410 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 1083 | 24.05 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 411 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 1220 | 24.41 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 412 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 1356 | 22.47 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 413 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 1580 | 24.86 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 414 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 1923 | 22.57 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 415 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 2189 | 25.91 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 416 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 2287 | 22.57 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 417 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 2373 | 25.9 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 418 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 2482 | 22.21 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 419 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 2623 | 22.43 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 420 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 2699 | 26.11 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 421 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 2800 | 23.18 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 422 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 3024 | 26.54 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 423 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 3181 | 26.23 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 424 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 3311 | 22.55 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 425 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 3391 | 26.35 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 426 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 3482 | 22.74 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 427 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 3729 | 27.36 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 428 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 3909 | 27.46 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 429 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 4095 | 27.93 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 430 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 4284 | 28.16 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 431 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 4415 | 28.43 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 432 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 4519 | 28.63 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 433 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 4686 | 28.63 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 434 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 4766 | 24.97 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 435 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 4981 | 22.72 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 436 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 5121 | 29.65 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 437 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 5264 | 29.42 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 438 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 5445 | 29.71 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 439 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 5589 | 29.65 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 440 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 5725 | 30.12 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 441 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 5892 | 29.54 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 442 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 6033 | 29.94 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 443 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 6183 | 22.61 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 444 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 6305 | 26.01 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 445 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 6658 | 22.35 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 446 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 6899 | 23.24 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 447 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 7019 | 27.27 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 448 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 7269 | 27.45 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 449 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 7397 | 23.05 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 450 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 8252 | 32.71 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 451 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 9298 | 26.34 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 452 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 9574 | 33.71 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 453 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 10285 | 23.49 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 454 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 10440 | 22.49 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 455 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 10583 | 22.21 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 456 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 10713 | 28.66 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 457 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 10890 | 27.96 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 458 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 11087 | 27.04 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 459 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 11218 | 27.08 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 460 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 11397 | 26.81 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 461 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 11556 | 27.27 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 462 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 11617 | 23.37 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 463 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 11735 | 27.51 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 464 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 11864 | 28.06 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 465 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 11972 | 28.87 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 466 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 12135 | 28.47 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 467 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 12262 | 28.94 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 468 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 12419 | 29.02 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 469 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 12639 | 29.35 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 470 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 12974 | 22.72 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 471 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 13114 | 22.2 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 472 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 13239 | 22.27 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 473 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 13364 | 22.45 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 474 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 13526 | 30.19 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 475 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 13715 | 22.48 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 476 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 13883 | 22.48 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 477 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 14092 | 22.81 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 478 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 14198 | 22.42 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 479 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 14401 | 23.36 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 480 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 14918 | 23.65 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 481 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 15240 | 27.49 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 482 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 15312 | 23.69 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 483 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 15389 | 26.94 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 484 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 15454 | 27.45 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 485 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 16111 | 22.89 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 486 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 16332 | 32.32 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 487 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 17237 | 25.07 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 488 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 17450 | 25.48 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 489 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 17691 | 29.98 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 490 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 17942 | 25.96 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 491 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 18029 | 34.31 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 492 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 18634 | 26.08 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 493 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 18947 | 26.35 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 494 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 19442 | 31.43 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 495 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 19989 | 37.8 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 496 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 20086 | 27.79 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 497 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 20246 | 27.83 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 498 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 20398 | 38.08 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 499 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 21616 | 29.16 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 500 | high | NELSON_R1 | headbox_pressure_kPa | 1 | 21860 | 35.05 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 501 | high | NELSON_R1 | jet_to_wire_ratio | 1 | 497 | 1.115 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 502 | high | NELSON_R1 | jet_to_wire_ratio | 1 | 803 | 0.921 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 503 | high | NELSON_R1 | jet_to_wire_ratio | 1 | 1217 | 0.907 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 504 | high | NELSON_R1 | jet_to_wire_ratio | 1 | 1307 | 0.917 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 505 | high | NELSON_R1 | jet_to_wire_ratio | 1 | 1769 | 1.112 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 506 | high | NELSON_R1 | jet_to_wire_ratio | 1 | 1834 | 0.924 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 507 | high | NELSON_R1 | jet_to_wire_ratio | 1 | 2220 | 1.121 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 508 | high | NELSON_R1 | jet_to_wire_ratio | 1 | 2342 | 0.913 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 509 | high | NELSON_R1 | jet_to_wire_ratio | 1 | 3369 | 1.113 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 510 | high | NELSON_R1 | jet_to_wire_ratio | 1 | 3835 | 0.917 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 511 | high | NELSON_R1 | jet_to_wire_ratio | 1 | 4070 | 1.122 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 512 | high | NELSON_R1 | jet_to_wire_ratio | 1 | 4870 | 0.902 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 513 | high | NELSON_R1 | jet_to_wire_ratio | 1 | 5175 | 1.121 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 514 | high | NELSON_R1 | jet_to_wire_ratio | 1 | 5369 | 1.129 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 515 | high | NELSON_R1 | jet_to_wire_ratio | 1 | 5805 | 1.117 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 516 | high | NELSON_R1 | jet_to_wire_ratio | 1 | 5923 | 0.928 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 517 | high | NELSON_R1 | jet_to_wire_ratio | 1 | 6962 | 0.924 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 518 | high | NELSON_R1 | jet_to_wire_ratio | 1 | 7102 | 1.129 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 519 | high | NELSON_R1 | jet_to_wire_ratio | 1 | 7523 | 0.92 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 520 | high | NELSON_R1 | jet_to_wire_ratio | 1 | 7673 | 1.112 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 521 | high | NELSON_R1 | jet_to_wire_ratio | 1 | 7735 | 1.117 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 522 | high | NELSON_R1 | jet_to_wire_ratio | 1 | 8117 | 1.111 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 523 | high | NELSON_R1 | jet_to_wire_ratio | 1 | 8524 | 1.111 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 524 | high | NELSON_R1 | jet_to_wire_ratio | 1 | 8889 | 0.914 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 525 | high | NELSON_R1 | jet_to_wire_ratio | 1 | 9061 | 1.116 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 526 | high | NELSON_R1 | jet_to_wire_ratio | 1 | 9735 | 1.117 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 527 | high | NELSON_R1 | jet_to_wire_ratio | 1 | 10036 | 0.928 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 528 | high | NELSON_R1 | jet_to_wire_ratio | 1 | 10512 | 0.918 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 529 | high | NELSON_R1 | jet_to_wire_ratio | 1 | 10716 | 0.904 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 530 | high | NELSON_R1 | jet_to_wire_ratio | 1 | 11178 | 1.114 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 531 | high | NELSON_R1 | jet_to_wire_ratio | 1 | 11867 | 1.165 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 532 | high | NELSON_R1 | jet_to_wire_ratio | 1 | 12450 | 0.919 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 533 | high | NELSON_R1 | jet_to_wire_ratio | 1 | 12746 | 1.115 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 534 | high | NELSON_R1 | jet_to_wire_ratio | 1 | 12877 | 0.923 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 535 | high | NELSON_R1 | jet_to_wire_ratio | 1 | 13242 | 1.131 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 536 | high | NELSON_R1 | jet_to_wire_ratio | 1 | 14373 | 1.12 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 537 | high | NELSON_R1 | jet_to_wire_ratio | 1 | 14442 | 1.116 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 538 | high | NELSON_R1 | jet_to_wire_ratio | 1 | 15224 | 0.926 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 539 | high | NELSON_R1 | jet_to_wire_ratio | 1 | 15490 | 1.128 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 540 | high | NELSON_R1 | jet_to_wire_ratio | 1 | 16193 | 1.112 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 541 | high | NELSON_R1 | jet_to_wire_ratio | 1 | 16667 | 1.112 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 542 | high | NELSON_R1 | jet_to_wire_ratio | 1 | 17759 | 0.91 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 543 | high | NELSON_R1 | jet_to_wire_ratio | 1 | 18533 | 0.899 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 544 | high | NELSON_R1 | jet_to_wire_ratio | 1 | 19185 | 0.912 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 545 | high | NELSON_R1 | jet_to_wire_ratio | 1 | 19320 | 1.112 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 546 | high | NELSON_R1 | jet_to_wire_ratio | 1 | 19561 | 1.116 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 547 | high | NELSON_R1 | jet_to_wire_ratio | 1 | 20360 | 1.117 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 548 | high | NELSON_R1 | jet_to_wire_ratio | 1 | 20549 | 0.922 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 549 | high | NELSON_R1 | jet_to_wire_ratio | 1 | 20781 | 1.133 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 550 | high | NELSON_R1 | jet_to_wire_ratio | 1 | 21733 | 1.113 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 551 | high | NELSON_R1 | jet_to_wire_ratio | 1 | 21853 | 1.116 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 552 | high | NELSON_R1 | machine_speed_mmin | 1 | 5 | 1704 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 553 | high | NELSON_R1 | machine_speed_mmin | 1 | 416 | 1714 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 554 | high | NELSON_R1 | machine_speed_mmin | 1 | 723 | 1702 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 555 | high | NELSON_R1 | machine_speed_mmin | 1 | 907 | 1699 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 556 | high | NELSON_R1 | machine_speed_mmin | 1 | 1208 | 1714 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 557 | high | NELSON_R1 | machine_speed_mmin | 1 | 1394 | 1698 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 558 | high | NELSON_R1 | machine_speed_mmin | 1 | 1526 | 1702 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 559 | high | NELSON_R1 | machine_speed_mmin | 1 | 1684 | 1701 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 560 | high | NELSON_R1 | machine_speed_mmin | 1 | 1996 | 1696 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 561 | high | NELSON_R1 | machine_speed_mmin | 1 | 2332 | 1715 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 562 | high | NELSON_R1 | machine_speed_mmin | 1 | 2833 | 1699 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 563 | high | NELSON_R1 | machine_speed_mmin | 1 | 3334 | 1728 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 564 | high | NELSON_R1 | machine_speed_mmin | 1 | 3660 | 1701 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 565 | high | NELSON_R1 | machine_speed_mmin | 1 | 3867 | 1699 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 566 | high | NELSON_R1 | machine_speed_mmin | 1 | 4669 | 1697 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 567 | high | NELSON_R1 | machine_speed_mmin | 1 | 4798 | 1690 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 568 | high | NELSON_R1 | machine_speed_mmin | 1 | 5094 | 1707 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 569 | high | NELSON_R1 | machine_speed_mmin | 1 | 5388 | 1699 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 570 | high | NELSON_R1 | machine_speed_mmin | 1 | 5836 | 1695 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 571 | high | NELSON_R1 | machine_speed_mmin | 1 | 6316 | 1692 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 572 | high | NELSON_R1 | machine_speed_mmin | 1 | 6468 | 1695 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 573 | high | NELSON_R1 | machine_speed_mmin | 1 | 6773 | 1699 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 574 | high | NELSON_R1 | machine_speed_mmin | 1 | 7026 | 1694 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 575 | high | NELSON_R1 | machine_speed_mmin | 1 | 7788 | 1701 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 576 | high | NELSON_R1 | machine_speed_mmin | 1 | 7923 | 1706 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 577 | high | NELSON_R1 | machine_speed_mmin | 1 | 8085 | 1694 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 578 | high | NELSON_R1 | machine_speed_mmin | 1 | 8404 | 1711 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 579 | high | NELSON_R1 | machine_speed_mmin | 1 | 8799 | 1705 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 580 | high | NELSON_R1 | machine_speed_mmin | 1 | 8940 | 1700 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 581 | high | NELSON_R1 | machine_speed_mmin | 1 | 9409 | 1702 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 582 | high | NELSON_R1 | machine_speed_mmin | 1 | 9548 | 1697 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 583 | high | NELSON_R1 | machine_speed_mmin | 1 | 10406 | 1714 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 584 | high | NELSON_R1 | machine_speed_mmin | 1 | 10887 | 1702 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 585 | high | NELSON_R1 | machine_speed_mmin | 1 | 11371 | 1700 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 586 | high | NELSON_R1 | machine_speed_mmin | 1 | 11683 | 1758 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 587 | high | NELSON_R1 | machine_speed_mmin | 1 | 12394 | 1697 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 588 | high | NELSON_R1 | machine_speed_mmin | 1 | 12577 | 1699 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 589 | high | NELSON_R1 | machine_speed_mmin | 1 | 13207 | 1702 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 590 | high | NELSON_R1 | machine_speed_mmin | 1 | 13507 | 1698 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 591 | high | NELSON_R1 | machine_speed_mmin | 1 | 13838 | 1701 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 592 | high | NELSON_R1 | machine_speed_mmin | 1 | 14166 | 1700 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 593 | high | NELSON_R1 | machine_speed_mmin | 1 | 14330 | 1725 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 594 | high | NELSON_R1 | machine_speed_mmin | 1 | 14506 | 1713 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 595 | high | NELSON_R1 | machine_speed_mmin | 1 | 15283 | 1697 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 596 | high | NELSON_R1 | machine_speed_mmin | 1 | 15471 | 1690 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 597 | high | NELSON_R1 | machine_speed_mmin | 1 | 16000 | 1709 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 598 | high | NELSON_R1 | machine_speed_mmin | 1 | 16462 | 1713 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 599 | high | NELSON_R1 | machine_speed_mmin | 1 | 16639 | 1703 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 600 | high | NELSON_R1 | machine_speed_mmin | 1 | 16812 | 1706 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 601 | high | NELSON_R1 | machine_speed_mmin | 1 | 17131 | 1700 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 602 | high | NELSON_R1 | machine_speed_mmin | 1 | 17349 | 1695 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 603 | high | NELSON_R1 | machine_speed_mmin | 1 | 17537 | 1701 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 604 | high | NELSON_R1 | machine_speed_mmin | 1 | 17726 | 1697 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 605 | high | NELSON_R1 | machine_speed_mmin | 1 | 17882 | 1698 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 606 | high | NELSON_R1 | machine_speed_mmin | 1 | 18173 | 1704 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 607 | high | NELSON_R1 | machine_speed_mmin | 1 | 18517 | 1714 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 608 | high | NELSON_R1 | machine_speed_mmin | 1 | 18846 | 1712 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 609 | high | NELSON_R1 | machine_speed_mmin | 1 | 19131 | 1709 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 610 | high | NELSON_R1 | machine_speed_mmin | 1 | 19303 | 1709 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 611 | high | NELSON_R1 | machine_speed_mmin | 1 | 19467 | 1696 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 612 | high | NELSON_R1 | machine_speed_mmin | 1 | 19638 | 1705 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 613 | high | NELSON_R1 | machine_speed_mmin | 1 | 19843 | 1690 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 614 | high | NELSON_R1 | machine_speed_mmin | 1 | 19999 | 1700 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 615 | high | NELSON_R1 | machine_speed_mmin | 1 | 20421 | 1707 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 616 | high | NELSON_R1 | stock_temp_C | 1 | 2 | 52.6 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 617 | high | NELSON_R1 | stock_temp_C | 1 | 199 | 40.7 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 618 | high | NELSON_R1 | stock_temp_C | 1 | 381 | 64.8 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 619 | high | NELSON_R1 | stock_temp_C | 1 | 800 | 52.6 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 620 | high | NELSON_R1 | stock_temp_C | 1 | 1068 | 60.3 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 621 | high | NELSON_R1 | stock_temp_C | 1 | 1327 | 41.3 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 622 | high | NELSON_R1 | stock_temp_C | 1 | 1469 | 53.7 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 623 | high | NELSON_R1 | stock_temp_C | 1 | 2716 | 41.4 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 624 | high | NELSON_R1 | stock_temp_C | 1 | 2804 | 41.2 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 625 | high | NELSON_R1 | stock_temp_C | 1 | 3033 | 41.5 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 626 | high | NELSON_R1 | stock_temp_C | 1 | 3105 | 41 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 627 | high | NELSON_R1 | stock_temp_C | 1 | 3421 | 39.1 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 628 | high | NELSON_R1 | stock_temp_C | 1 | 3616 | 54 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 629 | high | NELSON_R1 | stock_temp_C | 1 | 3725 | 41.3 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 630 | high | NELSON_R1 | stock_temp_C | 1 | 3992 | 55.2 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 631 | high | NELSON_R1 | stock_temp_C | 1 | 4085 | 38.9 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 632 | high | NELSON_R1 | stock_temp_C | 1 | 4360 | 54.6 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 633 | high | NELSON_R1 | stock_temp_C | 1 | 4486 | 41.3 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 634 | high | NELSON_R1 | stock_temp_C | 1 | 4827 | 41.4 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 635 | high | NELSON_R1 | stock_temp_C | 1 | 5199 | 38.5 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 636 | high | NELSON_R1 | stock_temp_C | 1 | 5485 | 41.1 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 637 | high | NELSON_R1 | stock_temp_C | 1 | 5883 | 41.1 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 638 | high | NELSON_R1 | stock_temp_C | 1 | 6236 | 40.7 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 639 | high | NELSON_R1 | stock_temp_C | 1 | 6559 | 41.2 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 640 | high | NELSON_R1 | stock_temp_C | 1 | 6741 | 40.5 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 641 | high | NELSON_R1 | stock_temp_C | 1 | 6920 | 36.4 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 642 | high | NELSON_R1 | stock_temp_C | 1 | 7095 | 40.7 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 643 | high | NELSON_R1 | stock_temp_C | 1 | 7264 | 39.6 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 644 | high | NELSON_R1 | stock_temp_C | 1 | 7436 | 40.2 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 645 | high | NELSON_R1 | stock_temp_C | 1 | 7627 | 41.5 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 646 | high | NELSON_R1 | stock_temp_C | 1 | 7808 | 39.5 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 647 | high | NELSON_R1 | stock_temp_C | 1 | 8209 | 40.8 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 648 | high | NELSON_R1 | stock_temp_C | 1 | 8319 | 41.4 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 649 | high | NELSON_R1 | stock_temp_C | 1 | 8568 | 40.4 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 650 | high | NELSON_R1 | stock_temp_C | 1 | 8655 | 41.3 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 651 | high | NELSON_R1 | stock_temp_C | 1 | 8905 | 41.1 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 652 | high | NELSON_R1 | stock_temp_C | 1 | 9234 | 39.6 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 653 | high | NELSON_R1 | stock_temp_C | 1 | 9585 | 40.3 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 654 | high | NELSON_R1 | stock_temp_C | 1 | 9946 | 41 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 655 | high | NELSON_R1 | stock_temp_C | 1 | 10275 | 39.6 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 656 | high | NELSON_R1 | stock_temp_C | 1 | 10565 | 36.8 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 657 | high | NELSON_R1 | stock_temp_C | 1 | 10962 | 37.1 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 658 | high | NELSON_R1 | stock_temp_C | 1 | 11339 | 38.8 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 659 | high | NELSON_R1 | stock_temp_C | 1 | 11759 | 40.5 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 660 | high | NELSON_R1 | stock_temp_C | 1 | 12104 | 39.8 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 661 | high | NELSON_R1 | stock_temp_C | 1 | 12414 | 40.3 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 662 | high | NELSON_R1 | stock_temp_C | 1 | 12564 | 38 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 663 | high | NELSON_R1 | stock_temp_C | 1 | 12820 | 37.6 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 664 | high | NELSON_R1 | stock_temp_C | 1 | 13078 | 35.9 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 665 | high | NELSON_R1 | stock_temp_C | 1 | 13179 | 39.6 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 666 | high | NELSON_R1 | stock_temp_C | 1 | 13430 | 35.4 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 667 | high | NELSON_R1 | stock_temp_C | 1 | 13509 | 38.6 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 668 | high | NELSON_R1 | stock_temp_C | 1 | 13759 | 35.4 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 669 | high | NELSON_R1 | stock_temp_C | 1 | 13839 | 36.5 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 670 | high | NELSON_R1 | stock_temp_C | 1 | 14265 | 41.5 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 671 | high | NELSON_R1 | stock_temp_C | 1 | 14624 | 40.5 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 672 | high | NELSON_R1 | stock_temp_C | 1 | 14958 | 38.5 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 673 | high | NELSON_R1 | stock_temp_C | 1 | 15254 | 35.3 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 674 | high | NELSON_R1 | stock_temp_C | 1 | 15665 | 38.3 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 675 | high | NELSON_R1 | stock_temp_C | 1 | 16050 | 41.5 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 676 | high | NELSON_R1 | stock_temp_C | 1 | 16228 | 36.8 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 677 | high | NELSON_R1 | stock_temp_C | 1 | 16350 | 38.9 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 678 | high | NELSON_R1 | stock_temp_C | 1 | 16751 | 40.4 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 679 | high | NELSON_R1 | stock_temp_C | 1 | 17090 | 39.6 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 680 | high | NELSON_R1 | stock_temp_C | 1 | 17447 | 40.6 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 681 | high | NELSON_R1 | stock_temp_C | 1 | 17719 | 37.4 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 682 | high | NELSON_R1 | stock_temp_C | 1 | 17803 | 39.8 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 683 | high | NELSON_R1 | stock_temp_C | 1 | 17927 | 40.5 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 684 | high | NELSON_R1 | stock_temp_C | 1 | 18167 | 40.1 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 685 | high | NELSON_R1 | stock_temp_C | 1 | 18521 | 40.1 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 686 | high | NELSON_R1 | stock_temp_C | 1 | 18686 | 41.4 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 687 | high | NELSON_R1 | stock_temp_C | 1 | 18909 | 41.3 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 688 | high | NELSON_R1 | stock_temp_C | 1 | 19070 | 40.5 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 689 | high | NELSON_R1 | stock_temp_C | 1 | 19251 | 39.9 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 690 | high | NELSON_R1 | stock_temp_C | 1 | 19438 | 40.9 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 691 | high | NELSON_R1 | stock_temp_C | 1 | 19602 | 40.9 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 692 | high | NELSON_R1 | stock_temp_C | 1 | 19816 | 41 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 693 | high | NELSON_R1 | stock_temp_C | 1 | 20185 | 40.1 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 694 | high | NELSON_R1 | stock_temp_C | 1 | 20328 | 39.2 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 695 | high | NELSON_R1 | stock_temp_C | 1 | 20545 | 41.5 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 696 | high | NELSON_R1 | stock_temp_C | 1 | 20709 | 40.6 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 697 | high | NELSON_R1 | stock_temp_C | 1 | 20992 | 41.5 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 698 | high | NELSON_R1 | stock_temp_C | 1 | 21329 | 39.9 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 699 | high | NELSON_R1 | stock_temp_C | 1 | 21701 | 41.3 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 700 | high | NELSON_R1 | vacuum_pump1_kPa | 1 | 606 | 36.1 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 701 | high | NELSON_R1 | vacuum_pump1_kPa | 1 | 1368 | 67.7 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 702 | high | NELSON_R1 | vacuum_pump1_kPa | 1 | 1724 | 67.1 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 703 | high | NELSON_R1 | vacuum_pump1_kPa | 1 | 1890 | 34 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 704 | high | NELSON_R1 | vacuum_pump1_kPa | 1 | 2073 | 67.6 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 705 | high | NELSON_R1 | vacuum_pump1_kPa | 1 | 2371 | 36 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 706 | high | NELSON_R1 | vacuum_pump1_kPa | 1 | 2675 | 67.9 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 707 | high | NELSON_R1 | vacuum_pump1_kPa | 1 | 2758 | 36.3 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 708 | high | NELSON_R1 | vacuum_pump1_kPa | 1 | 2844 | 67.7 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 709 | high | NELSON_R1 | vacuum_pump1_kPa | 1 | 3574 | 34.9 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 710 | high | NELSON_R1 | vacuum_pump1_kPa | 1 | 3727 | 36.2 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 711 | high | NELSON_R1 | vacuum_pump1_kPa | 1 | 4454 | 68.5 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 712 | high | NELSON_R1 | vacuum_pump1_kPa | 1 | 4878 | 68.9 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 713 | high | NELSON_R1 | vacuum_pump1_kPa | 1 | 5165 | 67.4 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 714 | high | NELSON_R1 | vacuum_pump1_kPa | 1 | 5291 | 67.4 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 715 | high | NELSON_R1 | vacuum_pump1_kPa | 1 | 5550 | 33.4 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 716 | high | NELSON_R1 | vacuum_pump1_kPa | 1 | 5861 | 36 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 717 | high | NELSON_R1 | vacuum_pump1_kPa | 1 | 6529 | 35.7 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 718 | high | NELSON_R1 | vacuum_pump1_kPa | 1 | 6600 | 68.5 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 719 | high | NELSON_R1 | vacuum_pump1_kPa | 1 | 7286 | 68.3 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 720 | high | NELSON_R1 | vacuum_pump1_kPa | 1 | 7974 | 36.6 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 721 | high | NELSON_R1 | vacuum_pump1_kPa | 1 | 8535 | 68.4 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 722 | high | NELSON_R1 | vacuum_pump1_kPa | 1 | 8955 | 67.1 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 723 | high | NELSON_R1 | vacuum_pump1_kPa | 1 | 9478 | 68.1 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 724 | high | NELSON_R1 | vacuum_pump1_kPa | 1 | 9741 | 36.7 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 725 | high | NELSON_R1 | vacuum_pump1_kPa | 1 | 9841 | 35.1 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 726 | high | NELSON_R1 | vacuum_pump1_kPa | 1 | 10092 | 34.3 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 727 | high | NELSON_R1 | vacuum_pump1_kPa | 1 | 10171 | 67.6 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 728 | high | NELSON_R1 | vacuum_pump1_kPa | 1 | 10522 | 67.9 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 729 | high | NELSON_R1 | vacuum_pump1_kPa | 1 | 10754 | 69.6 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 730 | high | NELSON_R1 | vacuum_pump1_kPa | 1 | 11088 | 35.8 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 731 | high | NELSON_R1 | vacuum_pump1_kPa | 1 | 11193 | 35.6 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 732 | high | NELSON_R1 | vacuum_pump1_kPa | 1 | 12602 | 33.2 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 733 | high | NELSON_R1 | vacuum_pump1_kPa | 1 | 12923 | 69.8 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 734 | high | NELSON_R1 | vacuum_pump1_kPa | 1 | 13587 | 69.8 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 735 | high | NELSON_R1 | vacuum_pump1_kPa | 1 | 13741 | 67.7 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 736 | high | NELSON_R1 | vacuum_pump1_kPa | 1 | 13914 | 68.6 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 737 | high | NELSON_R1 | vacuum_pump1_kPa | 1 | 14534 | 36.8 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 738 | high | NELSON_R1 | vacuum_pump1_kPa | 1 | 14752 | 36.2 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 739 | high | NELSON_R1 | vacuum_pump1_kPa | 1 | 15126 | 35.6 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 740 | high | NELSON_R1 | vacuum_pump1_kPa | 1 | 16153 | 71.3 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 741 | high | NELSON_R1 | vacuum_pump1_kPa | 1 | 16335 | 35.5 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 742 | high | NELSON_R1 | vacuum_pump1_kPa | 1 | 16445 | 68 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 743 | high | NELSON_R1 | vacuum_pump1_kPa | 1 | 17136 | 35.6 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 744 | high | NELSON_R1 | vacuum_pump1_kPa | 1 | 17542 | 35.5 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 745 | high | NELSON_R1 | vacuum_pump1_kPa | 1 | 18376 | 67 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 746 | high | NELSON_R1 | vacuum_pump1_kPa | 1 | 18837 | 36.2 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 747 | high | NELSON_R1 | vacuum_pump1_kPa | 1 | 18983 | 67.8 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 748 | high | NELSON_R1 | vacuum_pump1_kPa | 1 | 19181 | 67.1 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 749 | high | NELSON_R1 | vacuum_pump1_kPa | 1 | 19502 | 36.8 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 750 | high | NELSON_R1 | vacuum_pump1_kPa | 1 | 19563 | 36.4 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 751 | high | NELSON_R1 | vacuum_pump1_kPa | 1 | 19771 | 36.5 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 752 | high | NELSON_R1 | vacuum_pump1_kPa | 1 | 19967 | 36.5 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 753 | high | NELSON_R1 | vacuum_pump1_kPa | 1 | 20072 | 36.9 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 754 | high | NELSON_R1 | vacuum_pump1_kPa | 1 | 20159 | 67.2 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 755 | high | NELSON_R1 | vacuum_pump1_kPa | 1 | 20771 | 68.9 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 756 | high | NELSON_R1 | vacuum_pump1_kPa | 1 | 20846 | 68.9 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 757 | high | NELSON_R1 | vacuum_pump1_kPa | 1 | 21753 | 35.9 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 758 | high | NELSON_R1 | white_water_consistency_pct | 1 | 86 | 1.268 | white_water_consistency_pct 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 759 | high | NELSON_R1 | white_water_consistency_pct | 1 | 266 | 1.339 | white_water_consistency_pct 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 760 | high | NELSON_R1 | white_water_consistency_pct | 1 | 378 | 0.369 | white_water_consistency_pct 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 761 | high | NELSON_R1 | white_water_consistency_pct | 1 | 534 | 1.132 | white_water_consistency_pct 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 762 | high | NELSON_R1 | white_water_consistency_pct | 1 | 1222 | 1.17 | white_water_consistency_pct 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 763 | high | NELSON_R1 | white_water_consistency_pct | 1 | 1303 | 1.151 | white_water_consistency_pct 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 764 | high | NELSON_R1 | white_water_consistency_pct | 1 | 1770 | 1.113 | white_water_consistency_pct 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 765 | high | NELSON_R1 | white_water_consistency_pct | 1 | 2152 | 1.436 | white_water_consistency_pct 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 766 | high | NELSON_R1 | white_water_consistency_pct | 1 | 2629 | 1.148 | white_water_consistency_pct 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 767 | high | NELSON_R1 | white_water_consistency_pct | 1 | 2863 | 1.148 | white_water_consistency_pct 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 768 | high | NELSON_R1 | white_water_consistency_pct | 1 | 21021 | 1.216 | white_water_consistency_pct 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 769 | high | NELSON_R1 | white_water_consistency_pct | 1 | 21399 | 1.235 | white_water_consistency_pct 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 770 | high | NELSON_R1 | white_water_consistency_pct | 1 | 21564 | 1.218 | white_water_consistency_pct 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 771 | high | NELSON_R1 | white_water_consistency_pct | 1 | 21690 | 1.247 | white_water_consistency_pct 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 772 | high | NELSON_R1 | white_water_consistency_pct | 1 | 21821 | 1.265 | white_water_consistency_pct 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 773 | high | NELSON_R1 | fan_pump_speed_rpm | 2 | 9 | 906.4 | fan_pump_speed_rpm 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 774 | high | NELSON_R1 | fan_pump_speed_rpm | 2 | 412 | 905.7 | fan_pump_speed_rpm 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 775 | high | NELSON_R1 | fan_pump_speed_rpm | 2 | 5425 | 918.8 | fan_pump_speed_rpm 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 776 | high | NELSON_R1 | fan_pump_speed_rpm | 2 | 5544 | 911.4 | fan_pump_speed_rpm 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 777 | high | NELSON_R1 | fan_pump_speed_rpm | 2 | 5730 | 916.7 | fan_pump_speed_rpm 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 778 | high | NELSON_R1 | fan_pump_speed_rpm | 2 | 6009 | 910 | fan_pump_speed_rpm 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 779 | high | NELSON_R1 | fan_pump_speed_rpm | 2 | 6122 | 919.3 | fan_pump_speed_rpm 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 780 | high | NELSON_R1 | fan_pump_speed_rpm | 2 | 6189 | 910 | fan_pump_speed_rpm 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 781 | high | NELSON_R1 | fan_pump_speed_rpm | 2 | 6314 | 911.3 | fan_pump_speed_rpm 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 782 | high | NELSON_R1 | fan_pump_speed_rpm | 2 | 6456 | 908.7 | fan_pump_speed_rpm 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 783 | high | NELSON_R1 | fan_pump_speed_rpm | 2 | 6717 | 908.5 | fan_pump_speed_rpm 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 784 | high | NELSON_R1 | fan_pump_speed_rpm | 2 | 6821 | 914.6 | fan_pump_speed_rpm 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 785 | high | NELSON_R1 | fan_pump_speed_rpm | 2 | 7240 | 920.8 | fan_pump_speed_rpm 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 786 | high | NELSON_R1 | fan_pump_speed_rpm | 2 | 7366 | 911.2 | fan_pump_speed_rpm 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 787 | high | NELSON_R1 | fan_pump_speed_rpm | 2 | 10457 | 916.1 | fan_pump_speed_rpm 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 788 | high | NELSON_R1 | fan_pump_speed_rpm | 2 | 10682 | 907.6 | fan_pump_speed_rpm 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 789 | high | NELSON_R1 | fan_pump_speed_rpm | 2 | 10807 | 907.3 | fan_pump_speed_rpm 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 790 | high | NELSON_R1 | fan_pump_speed_rpm | 2 | 10897 | 913.7 | fan_pump_speed_rpm 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 791 | high | NELSON_R1 | fan_pump_speed_rpm | 2 | 13134 | 912.7 | fan_pump_speed_rpm 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 792 | high | NELSON_R1 | fan_pump_speed_rpm | 2 | 13420 | 916.5 | fan_pump_speed_rpm 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 793 | high | NELSON_R1 | fan_pump_speed_rpm | 2 | 13690 | 908.2 | fan_pump_speed_rpm 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 794 | high | NELSON_R1 | fan_pump_speed_rpm | 2 | 13779 | 918.2 | fan_pump_speed_rpm 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 795 | high | NELSON_R1 | fan_pump_speed_rpm | 2 | 13999 | 916.4 | fan_pump_speed_rpm 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 796 | high | NELSON_R1 | fan_pump_speed_rpm | 2 | 14092 | 915.1 | fan_pump_speed_rpm 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 797 | high | NELSON_R1 | fan_pump_speed_rpm | 2 | 14198 | 907.9 | fan_pump_speed_rpm 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 798 | high | NELSON_R1 | fan_pump_speed_rpm | 2 | 14433 | 920.9 | fan_pump_speed_rpm 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 799 | high | NELSON_R1 | fan_pump_speed_rpm | 2 | 14548 | 915.8 | fan_pump_speed_rpm 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 800 | high | NELSON_R1 | fan_pump_speed_rpm | 2 | 14705 | 910.3 | fan_pump_speed_rpm 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 801 | high | NELSON_R1 | fan_pump_speed_rpm | 2 | 14820 | 918.4 | fan_pump_speed_rpm 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 802 | high | NELSON_R1 | fan_pump_speed_rpm | 2 | 15123 | 914 | fan_pump_speed_rpm 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 803 | high | NELSON_R1 | fan_pump_speed_rpm | 2 | 21987 | 943.7 | fan_pump_speed_rpm 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 804 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 27 | 24.46 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 805 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 97 | 22.13 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 806 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 256 | 23.92 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 807 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 338 | 22.09 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 808 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 431 | 24.07 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 809 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 536 | 24.49 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 810 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 733 | 24.43 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 811 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 920 | 24.48 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 812 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 1012 | 24.26 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 813 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 1205 | 24.22 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 814 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 1400 | 25.14 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 815 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 1576 | 25.01 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 816 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 1925 | 22.3 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 817 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 2131 | 22.13 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 818 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 2299 | 22.23 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 819 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 2412 | 26.3 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 820 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 2487 | 22.85 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 821 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 2577 | 26.19 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 822 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 2670 | 23.27 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 823 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 2732 | 26.38 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 824 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 2793 | 23.03 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 825 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 2922 | 26.57 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 826 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 3077 | 26.54 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 827 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 3158 | 22.48 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 828 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 3227 | 26.58 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 829 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 3423 | 26.64 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 830 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 3511 | 23.07 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 831 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 3586 | 26.78 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 832 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 3788 | 27.75 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 833 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 3961 | 27.61 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 834 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 4147 | 28.07 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 835 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 4319 | 28.03 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 836 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 4448 | 28.38 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 837 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 4538 | 28.28 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 838 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 4722 | 29.11 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 839 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 4861 | 29.08 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 840 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 5026 | 21.99 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 841 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 5146 | 22.45 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 842 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 5281 | 29.12 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 843 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 5404 | 29.46 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 844 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 5489 | 29.71 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 845 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 5665 | 29.79 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 846 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 5785 | 29.72 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 847 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 5963 | 22.37 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 848 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 6115 | 23.16 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 849 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 6258 | 22.7 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 850 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 6412 | 22.37 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 851 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 6779 | 23.19 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 852 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 7052 | 23.16 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 853 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 7290 | 32.05 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 854 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 7492 | 24.13 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 855 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 7624 | 24.25 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 856 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 7746 | 32.47 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 857 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 7838 | 27.92 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 858 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 8072 | 24.65 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 859 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 10010 | 33.63 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 860 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 10324 | 27.49 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 861 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 10548 | 30.97 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 862 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 10611 | 22.92 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 863 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 10761 | 22.65 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 864 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 10888 | 29.37 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 865 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 11243 | 28.34 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 866 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 11383 | 27.53 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 867 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 11562 | 26.99 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 868 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 11648 | 23.11 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 869 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 11726 | 26.3 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 870 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 11858 | 27.12 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 871 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 11958 | 24.7 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 872 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 12149 | 27.83 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 873 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 12292 | 28.24 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 874 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 12451 | 28.55 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 875 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 12581 | 28.86 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 876 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 12760 | 22.44 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 877 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 12936 | 29.29 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 878 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 13110 | 22.03 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 879 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 13432 | 22.42 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 880 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 13536 | 29.39 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 881 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 13685 | 22.79 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 882 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 13853 | 22.24 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 883 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 14039 | 22.62 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 884 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 14182 | 22.05 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 885 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 14343 | 22.69 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 886 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 14583 | 26.94 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 887 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 14821 | 30.88 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 888 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 15377 | 23.67 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 889 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 15814 | 31.62 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 890 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 16313 | 31.88 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 891 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 16468 | 32.13 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 892 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 17412 | 28.96 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 893 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 18014 | 29.69 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 894 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 18355 | 34.41 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 895 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 18475 | 30.28 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 896 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 18938 | 26.12 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 897 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 20579 | 32.91 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 898 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 20841 | 33.05 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 899 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 21334 | 33.55 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 900 | high | NELSON_R1 | headbox_pressure_kPa | 2 | 21987 | 39.61 | headbox_pressure_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 901 | high | NELSON_R1 | jet_to_wire_ratio | 2 | 123 | 0.927 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 902 | high | NELSON_R1 | jet_to_wire_ratio | 2 | 463 | 1.113 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 903 | high | NELSON_R1 | jet_to_wire_ratio | 2 | 538 | 1.133 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 904 | high | NELSON_R1 | jet_to_wire_ratio | 2 | 1012 | 1.113 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 905 | high | NELSON_R1 | jet_to_wire_ratio | 2 | 1161 | 1.143 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 906 | high | NELSON_R1 | jet_to_wire_ratio | 2 | 1602 | 1.125 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 907 | high | NELSON_R1 | jet_to_wire_ratio | 2 | 1926 | 0.929 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 908 | high | NELSON_R1 | jet_to_wire_ratio | 2 | 2202 | 0.921 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 909 | high | NELSON_R1 | jet_to_wire_ratio | 2 | 2443 | 0.927 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 910 | high | NELSON_R1 | jet_to_wire_ratio | 2 | 2675 | 1.119 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 911 | high | NELSON_R1 | jet_to_wire_ratio | 2 | 2764 | 1.119 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 912 | high | NELSON_R1 | jet_to_wire_ratio | 2 | 2908 | 1.119 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 913 | high | NELSON_R1 | jet_to_wire_ratio | 2 | 3619 | 1.11 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 914 | high | NELSON_R1 | jet_to_wire_ratio | 2 | 4430 | 0.925 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 915 | high | NELSON_R1 | jet_to_wire_ratio | 2 | 4672 | 0.929 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 916 | high | NELSON_R1 | jet_to_wire_ratio | 2 | 4861 | 0.923 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 917 | high | NELSON_R1 | jet_to_wire_ratio | 2 | 5053 | 0.914 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 918 | high | NELSON_R1 | jet_to_wire_ratio | 2 | 5225 | 0.919 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 919 | high | NELSON_R1 | jet_to_wire_ratio | 2 | 5723 | 0.922 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 920 | high | NELSON_R1 | jet_to_wire_ratio | 2 | 6141 | 1.11 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 921 | high | NELSON_R1 | jet_to_wire_ratio | 2 | 6904 | 1.113 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 922 | high | NELSON_R1 | jet_to_wire_ratio | 2 | 7440 | 0.929 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 923 | high | NELSON_R1 | jet_to_wire_ratio | 2 | 7769 | 1.121 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 924 | high | NELSON_R1 | jet_to_wire_ratio | 2 | 7975 | 1.122 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 925 | high | NELSON_R1 | jet_to_wire_ratio | 2 | 8540 | 0.929 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 926 | high | NELSON_R1 | jet_to_wire_ratio | 2 | 8795 | 1.113 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 927 | high | NELSON_R1 | jet_to_wire_ratio | 2 | 9318 | 0.93 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 928 | high | NELSON_R1 | jet_to_wire_ratio | 2 | 9419 | 0.913 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 929 | high | NELSON_R1 | jet_to_wire_ratio | 2 | 9598 | 0.919 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 930 | high | NELSON_R1 | jet_to_wire_ratio | 2 | 9770 | 1.126 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 931 | high | NELSON_R1 | jet_to_wire_ratio | 2 | 10025 | 1.116 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 932 | high | NELSON_R1 | jet_to_wire_ratio | 2 | 11359 | 0.925 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 933 | high | NELSON_R1 | jet_to_wire_ratio | 2 | 11563 | 1.11 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 934 | high | NELSON_R1 | jet_to_wire_ratio | 2 | 12872 | 0.92 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 935 | high | NELSON_R1 | jet_to_wire_ratio | 2 | 13019 | 0.926 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 936 | high | NELSON_R1 | jet_to_wire_ratio | 2 | 13130 | 1.121 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 937 | high | NELSON_R1 | jet_to_wire_ratio | 2 | 13711 | 1.121 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 938 | high | NELSON_R1 | jet_to_wire_ratio | 2 | 13880 | 1.111 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 939 | high | NELSON_R1 | jet_to_wire_ratio | 2 | 14063 | 1.115 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 940 | high | NELSON_R1 | jet_to_wire_ratio | 2 | 14334 | 0.929 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 941 | high | NELSON_R1 | jet_to_wire_ratio | 2 | 14483 | 1.11 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 942 | high | NELSON_R1 | jet_to_wire_ratio | 2 | 15180 | 1.133 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 943 | high | NELSON_R1 | jet_to_wire_ratio | 2 | 15504 | 1.136 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 944 | high | NELSON_R1 | jet_to_wire_ratio | 2 | 15824 | 1.11 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 945 | high | NELSON_R1 | jet_to_wire_ratio | 2 | 15967 | 0.929 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 946 | high | NELSON_R1 | jet_to_wire_ratio | 2 | 16346 | 0.91 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 947 | high | NELSON_R1 | jet_to_wire_ratio | 2 | 17197 | 1.117 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 948 | high | NELSON_R1 | jet_to_wire_ratio | 2 | 17518 | 0.929 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 949 | high | NELSON_R1 | jet_to_wire_ratio | 2 | 17688 | 0.928 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 950 | high | NELSON_R1 | jet_to_wire_ratio | 2 | 18157 | 0.908 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 951 | high | NELSON_R1 | jet_to_wire_ratio | 2 | 19208 | 0.913 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 952 | high | NELSON_R1 | jet_to_wire_ratio | 2 | 19369 | 1.11 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 953 | high | NELSON_R1 | jet_to_wire_ratio | 2 | 19534 | 0.93 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 954 | high | NELSON_R1 | jet_to_wire_ratio | 2 | 19647 | 1.11 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 955 | high | NELSON_R1 | jet_to_wire_ratio | 2 | 19855 | 1.117 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 956 | high | NELSON_R1 | jet_to_wire_ratio | 2 | 20058 | 0.912 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 957 | high | NELSON_R1 | jet_to_wire_ratio | 2 | 20184 | 0.93 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 958 | high | NELSON_R1 | jet_to_wire_ratio | 2 | 20565 | 1.114 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 959 | high | NELSON_R1 | jet_to_wire_ratio | 2 | 20772 | 0.912 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 960 | high | NELSON_R1 | jet_to_wire_ratio | 2 | 21286 | 1.112 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 961 | high | NELSON_R1 | jet_to_wire_ratio | 2 | 21479 | 1.125 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 962 | high | NELSON_R1 | jet_to_wire_ratio | 2 | 21646 | 1.114 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 963 | high | NELSON_R1 | jet_to_wire_ratio | 2 | 21834 | 0.929 | jet_to_wire_ratio 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 964 | high | NELSON_R1 | machine_speed_mmin | 2 | 5 | 1730 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 965 | high | NELSON_R1 | machine_speed_mmin | 2 | 378 | 1710 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 966 | high | NELSON_R1 | machine_speed_mmin | 2 | 555 | 1723 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 967 | high | NELSON_R1 | machine_speed_mmin | 2 | 678 | 1698 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 968 | high | NELSON_R1 | machine_speed_mmin | 2 | 872 | 1697 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 969 | high | NELSON_R1 | machine_speed_mmin | 2 | 1163 | 1702 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 970 | high | NELSON_R1 | machine_speed_mmin | 2 | 1550 | 1691 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 971 | high | NELSON_R1 | machine_speed_mmin | 2 | 1687 | 1698 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 972 | high | NELSON_R1 | machine_speed_mmin | 2 | 1825 | 1720 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 973 | high | NELSON_R1 | machine_speed_mmin | 2 | 2003 | 1703 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 974 | high | NELSON_R1 | machine_speed_mmin | 2 | 2342 | 1696 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 975 | high | NELSON_R1 | machine_speed_mmin | 2 | 2865 | 1692 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 976 | high | NELSON_R1 | machine_speed_mmin | 2 | 3729 | 1694 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 977 | high | NELSON_R1 | machine_speed_mmin | 2 | 4096 | 1693 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 978 | high | NELSON_R1 | machine_speed_mmin | 2 | 4300 | 1700 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 979 | high | NELSON_R1 | machine_speed_mmin | 2 | 4534 | 1701 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 980 | high | NELSON_R1 | machine_speed_mmin | 2 | 4699 | 1698 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 981 | high | NELSON_R1 | machine_speed_mmin | 2 | 4827 | 1699 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 982 | high | NELSON_R1 | machine_speed_mmin | 2 | 4961 | 1699 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 983 | high | NELSON_R1 | machine_speed_mmin | 2 | 5405 | 1694 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 984 | high | NELSON_R1 | machine_speed_mmin | 2 | 5888 | 1694 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 985 | high | NELSON_R1 | machine_speed_mmin | 2 | 6380 | 1702 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 986 | high | NELSON_R1 | machine_speed_mmin | 2 | 6564 | 1725 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 987 | high | NELSON_R1 | machine_speed_mmin | 2 | 6873 | 1710 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 988 | high | NELSON_R1 | machine_speed_mmin | 2 | 7137 | 1714 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 989 | high | NELSON_R1 | machine_speed_mmin | 2 | 7278 | 1746 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 990 | high | NELSON_R1 | machine_speed_mmin | 2 | 7573 | 1708 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 991 | high | NELSON_R1 | machine_speed_mmin | 2 | 7699 | 1690 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 992 | high | NELSON_R1 | machine_speed_mmin | 2 | 8009 | 1700 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 993 | high | NELSON_R1 | machine_speed_mmin | 2 | 8161 | 1696 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 994 | high | NELSON_R1 | machine_speed_mmin | 2 | 8337 | 1693 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 995 | high | NELSON_R1 | machine_speed_mmin | 2 | 8522 | 1698 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 996 | high | NELSON_R1 | machine_speed_mmin | 2 | 8718 | 1699 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 997 | high | NELSON_R1 | machine_speed_mmin | 2 | 9114 | 1706 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 998 | high | NELSON_R1 | machine_speed_mmin | 2 | 9428 | 1704 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 999 | high | NELSON_R1 | machine_speed_mmin | 2 | 9630 | 1710 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1000 | high | NELSON_R1 | machine_speed_mmin | 2 | 9772 | 1699 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1001 | high | NELSON_R1 | machine_speed_mmin | 2 | 10695 | 1716 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1002 | high | NELSON_R1 | machine_speed_mmin | 2 | 11184 | 1699 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1003 | high | NELSON_R1 | machine_speed_mmin | 2 | 11509 | 1698 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1004 | high | NELSON_R1 | machine_speed_mmin | 2 | 11709 | 1694 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1005 | high | NELSON_R1 | machine_speed_mmin | 2 | 11978 | 1699 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1006 | high | NELSON_R1 | machine_speed_mmin | 2 | 12895 | 1706 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1007 | high | NELSON_R1 | machine_speed_mmin | 2 | 13082 | 1701 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1008 | high | NELSON_R1 | machine_speed_mmin | 2 | 14129 | 1707 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1009 | high | NELSON_R1 | machine_speed_mmin | 2 | 14463 | 1690 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1010 | high | NELSON_R1 | machine_speed_mmin | 2 | 14624 | 1706 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1011 | high | NELSON_R1 | machine_speed_mmin | 2 | 14800 | 1707 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1012 | high | NELSON_R1 | machine_speed_mmin | 2 | 15129 | 1702 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1013 | high | NELSON_R1 | machine_speed_mmin | 2 | 15324 | 1699 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1014 | high | NELSON_R1 | machine_speed_mmin | 2 | 15774 | 1700 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1015 | high | NELSON_R1 | machine_speed_mmin | 2 | 16316 | 1702 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1016 | high | NELSON_R1 | machine_speed_mmin | 2 | 16810 | 1692 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1017 | high | NELSON_R1 | machine_speed_mmin | 2 | 17172 | 1704 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1018 | high | NELSON_R1 | machine_speed_mmin | 2 | 17473 | 1691 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1019 | high | NELSON_R1 | machine_speed_mmin | 2 | 17686 | 1697 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1020 | high | NELSON_R1 | machine_speed_mmin | 2 | 17888 | 1696 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1021 | high | NELSON_R1 | machine_speed_mmin | 2 | 18363 | 1719 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1022 | high | NELSON_R1 | machine_speed_mmin | 2 | 18493 | 1691 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1023 | high | NELSON_R1 | machine_speed_mmin | 2 | 18678 | 1699 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1024 | high | NELSON_R1 | machine_speed_mmin | 2 | 19127 | 1705 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1025 | high | NELSON_R1 | machine_speed_mmin | 2 | 19384 | 1699 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1026 | high | NELSON_R1 | machine_speed_mmin | 2 | 19543 | 1711 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1027 | high | NELSON_R1 | machine_speed_mmin | 2 | 19700 | 1707 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1028 | high | NELSON_R1 | machine_speed_mmin | 2 | 19887 | 1707 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1029 | high | NELSON_R1 | machine_speed_mmin | 2 | 20041 | 1716 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1030 | high | NELSON_R1 | machine_speed_mmin | 2 | 21147 | 1319 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1031 | high | NELSON_R1 | machine_speed_mmin | 2 | 21987 | 1708 | machine_speed_mmin 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1032 | high | NELSON_R1 | stock_temp_C | 2 | 37 | 56.9 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1033 | high | NELSON_R1 | stock_temp_C | 2 | 163 | 40.3 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1034 | high | NELSON_R1 | stock_temp_C | 2 | 258 | 41 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1035 | high | NELSON_R1 | stock_temp_C | 2 | 346 | 53.2 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1036 | high | NELSON_R1 | stock_temp_C | 2 | 583 | 40.9 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1037 | high | NELSON_R1 | stock_temp_C | 2 | 677 | 54.7 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1038 | high | NELSON_R1 | stock_temp_C | 2 | 2258 | 52.8 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1039 | high | NELSON_R1 | stock_temp_C | 2 | 2759 | 41.2 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1040 | high | NELSON_R1 | stock_temp_C | 2 | 3124 | 41.1 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1041 | high | NELSON_R1 | stock_temp_C | 2 | 3267 | 62.4 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1042 | high | NELSON_R1 | stock_temp_C | 2 | 3436 | 40.7 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1043 | high | NELSON_R1 | stock_temp_C | 2 | 3806 | 41.3 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1044 | high | NELSON_R1 | stock_temp_C | 2 | 4159 | 41.4 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1045 | high | NELSON_R1 | stock_temp_C | 2 | 4522 | 40.5 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1046 | high | NELSON_R1 | stock_temp_C | 2 | 4883 | 40.4 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1047 | high | NELSON_R1 | stock_temp_C | 2 | 5221 | 41.2 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1048 | high | NELSON_R1 | stock_temp_C | 2 | 5432 | 40.1 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1049 | high | NELSON_R1 | stock_temp_C | 2 | 5601 | 41.4 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1050 | high | NELSON_R1 | stock_temp_C | 2 | 5863 | 38.5 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1051 | high | NELSON_R1 | stock_temp_C | 2 | 6298 | 41.1 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1052 | high | NELSON_R1 | stock_temp_C | 2 | 6385 | 39.1 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1053 | high | NELSON_R1 | stock_temp_C | 2 | 6670 | 41.4 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1054 | high | NELSON_R1 | stock_temp_C | 2 | 7028 | 41.2 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1055 | high | NELSON_R1 | stock_temp_C | 2 | 7201 | 41.4 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1056 | high | NELSON_R1 | stock_temp_C | 2 | 7390 | 39.5 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1057 | high | NELSON_R1 | stock_temp_C | 2 | 7571 | 39.7 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1058 | high | NELSON_R1 | stock_temp_C | 2 | 7669 | 40.2 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1059 | high | NELSON_R1 | stock_temp_C | 2 | 7924 | 40.2 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1060 | high | NELSON_R1 | stock_temp_C | 2 | 8026 | 40.9 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1061 | high | NELSON_R1 | stock_temp_C | 2 | 8169 | 38.1 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1062 | high | NELSON_R1 | stock_temp_C | 2 | 8283 | 40.1 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1063 | high | NELSON_R1 | stock_temp_C | 2 | 8416 | 39.4 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1064 | high | NELSON_R1 | stock_temp_C | 2 | 8668 | 41.4 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1065 | high | NELSON_R1 | stock_temp_C | 2 | 9030 | 39 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1066 | high | NELSON_R1 | stock_temp_C | 2 | 9373 | 36.3 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1067 | high | NELSON_R1 | stock_temp_C | 2 | 9453 | 40.6 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1068 | high | NELSON_R1 | stock_temp_C | 2 | 9802 | 39.4 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1069 | high | NELSON_R1 | stock_temp_C | 2 | 10215 | 40.1 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1070 | high | NELSON_R1 | stock_temp_C | 2 | 10586 | 40.4 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1071 | high | NELSON_R1 | stock_temp_C | 2 | 10964 | 40.9 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1072 | high | NELSON_R1 | stock_temp_C | 2 | 11303 | 40.5 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1073 | high | NELSON_R1 | stock_temp_C | 2 | 11507 | 36.5 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1074 | high | NELSON_R1 | stock_temp_C | 2 | 11676 | 39.3 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1075 | high | NELSON_R1 | stock_temp_C | 2 | 11997 | 38.8 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1076 | high | NELSON_R1 | stock_temp_C | 2 | 12436 | 40.2 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1077 | high | NELSON_R1 | stock_temp_C | 2 | 12801 | 39.7 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1078 | high | NELSON_R1 | stock_temp_C | 2 | 13168 | 40.6 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1079 | high | NELSON_R1 | stock_temp_C | 2 | 13500 | 40.4 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1080 | high | NELSON_R1 | stock_temp_C | 2 | 13832 | 40.7 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1081 | high | NELSON_R1 | stock_temp_C | 2 | 14213 | 40.5 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1082 | high | NELSON_R1 | stock_temp_C | 2 | 14581 | 41.1 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1083 | high | NELSON_R1 | stock_temp_C | 2 | 14760 | 33.7 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1084 | high | NELSON_R1 | stock_temp_C | 2 | 14939 | 41.1 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1085 | high | NELSON_R1 | stock_temp_C | 2 | 15297 | 39.4 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1086 | high | NELSON_R1 | stock_temp_C | 2 | 15619 | 39.9 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1087 | high | NELSON_R1 | stock_temp_C | 2 | 15997 | 40.3 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1088 | high | NELSON_R1 | stock_temp_C | 2 | 16368 | 40.3 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1089 | high | NELSON_R1 | stock_temp_C | 2 | 16726 | 41.2 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1090 | high | NELSON_R1 | stock_temp_C | 2 | 17067 | 39.3 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1091 | high | NELSON_R1 | stock_temp_C | 2 | 17434 | 41 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1092 | high | NELSON_R1 | stock_temp_C | 2 | 17707 | 37 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1093 | high | NELSON_R1 | stock_temp_C | 2 | 17781 | 39.5 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1094 | high | NELSON_R1 | stock_temp_C | 2 | 17905 | 40.9 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1095 | high | NELSON_R1 | stock_temp_C | 2 | 18129 | 37.9 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1096 | high | NELSON_R1 | stock_temp_C | 2 | 18441 | 39 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1097 | high | NELSON_R1 | stock_temp_C | 2 | 18578 | 39.6 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1098 | high | NELSON_R1 | stock_temp_C | 2 | 18848 | 40 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1099 | high | NELSON_R1 | stock_temp_C | 2 | 18968 | 41.3 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1100 | high | NELSON_R1 | stock_temp_C | 2 | 19173 | 41.3 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1101 | high | NELSON_R1 | stock_temp_C | 2 | 19315 | 39 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1102 | high | NELSON_R1 | stock_temp_C | 2 | 19424 | 36.5 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1103 | high | NELSON_R1 | stock_temp_C | 2 | 19511 | 40.5 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1104 | high | NELSON_R1 | stock_temp_C | 2 | 19687 | 41.4 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1105 | high | NELSON_R1 | stock_temp_C | 2 | 19838 | 39.4 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1106 | high | NELSON_R1 | stock_temp_C | 2 | 20047 | 41.4 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1107 | high | NELSON_R1 | stock_temp_C | 2 | 20137 | 38.6 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1108 | high | NELSON_R1 | stock_temp_C | 2 | 20414 | 41 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1109 | high | NELSON_R1 | stock_temp_C | 2 | 20539 | 40.6 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1110 | high | NELSON_R1 | stock_temp_C | 2 | 20773 | 39.8 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1111 | high | NELSON_R1 | stock_temp_C | 2 | 20879 | 40.6 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1112 | high | NELSON_R1 | stock_temp_C | 2 | 21109 | 41.3 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1113 | high | NELSON_R1 | stock_temp_C | 2 | 21479 | 41.1 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1114 | high | NELSON_R1 | stock_temp_C | 2 | 21854 | 41.4 | stock_temp_C 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1115 | high | NELSON_R1 | vacuum_pump1_kPa | 2 | 621 | 68 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1116 | high | NELSON_R1 | vacuum_pump1_kPa | 2 | 738 | 36.6 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1117 | high | NELSON_R1 | vacuum_pump1_kPa | 2 | 890 | 35.2 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1118 | high | NELSON_R1 | vacuum_pump1_kPa | 2 | 1172 | 34.4 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1119 | high | NELSON_R1 | vacuum_pump1_kPa | 2 | 1445 | 67.2 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1120 | high | NELSON_R1 | vacuum_pump1_kPa | 2 | 1639 | 67.4 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1121 | high | NELSON_R1 | vacuum_pump1_kPa | 2 | 1943 | 69 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1122 | high | NELSON_R1 | vacuum_pump1_kPa | 2 | 2077 | 36.1 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1123 | high | NELSON_R1 | vacuum_pump1_kPa | 2 | 2459 | 67.3 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1124 | high | NELSON_R1 | vacuum_pump1_kPa | 2 | 2922 | 68.7 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1125 | high | NELSON_R1 | vacuum_pump1_kPa | 2 | 3113 | 32.9 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1126 | high | NELSON_R1 | vacuum_pump1_kPa | 2 | 4677 | 68 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1127 | high | NELSON_R1 | vacuum_pump1_kPa | 2 | 7104 | 35.3 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1128 | high | NELSON_R1 | vacuum_pump1_kPa | 2 | 7650 | 67.5 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1129 | high | NELSON_R1 | vacuum_pump1_kPa | 2 | 8674 | 35.7 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1130 | high | NELSON_R1 | vacuum_pump1_kPa | 2 | 8850 | 68.5 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1131 | high | NELSON_R1 | vacuum_pump1_kPa | 2 | 9155 | 67.6 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1132 | high | NELSON_R1 | vacuum_pump1_kPa | 2 | 9297 | 69 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1133 | high | NELSON_R1 | vacuum_pump1_kPa | 2 | 9511 | 36.8 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1134 | high | NELSON_R1 | vacuum_pump1_kPa | 2 | 10099 | 67.6 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1135 | high | NELSON_R1 | vacuum_pump1_kPa | 2 | 10536 | 67.8 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1136 | high | NELSON_R1 | vacuum_pump1_kPa | 2 | 10982 | 34.6 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1137 | high | NELSON_R1 | vacuum_pump1_kPa | 2 | 11560 | 69 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1138 | high | NELSON_R1 | vacuum_pump1_kPa | 2 | 11691 | 36.7 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1139 | high | NELSON_R1 | vacuum_pump1_kPa | 2 | 11886 | 36.7 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1140 | high | NELSON_R1 | vacuum_pump1_kPa | 2 | 12108 | 34.8 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1141 | high | NELSON_R1 | vacuum_pump1_kPa | 2 | 12274 | 67.3 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1142 | high | NELSON_R1 | vacuum_pump1_kPa | 2 | 12593 | 36.2 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1143 | high | NELSON_R1 | vacuum_pump1_kPa | 2 | 12978 | 36.4 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1144 | high | NELSON_R1 | vacuum_pump1_kPa | 2 | 13103 | 68 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1145 | high | NELSON_R1 | vacuum_pump1_kPa | 2 | 13173 | 36.8 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1146 | high | NELSON_R1 | vacuum_pump1_kPa | 2 | 15059 | 34.1 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1147 | high | NELSON_R1 | vacuum_pump1_kPa | 2 | 15155 | 36.1 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1148 | high | NELSON_R1 | vacuum_pump1_kPa | 2 | 15736 | 68.9 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1149 | high | NELSON_R1 | vacuum_pump1_kPa | 2 | 15942 | 68.3 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1150 | high | NELSON_R1 | vacuum_pump1_kPa | 2 | 17723 | 71.1 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1151 | high | NELSON_R1 | vacuum_pump1_kPa | 2 | 18088 | 69.9 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1152 | high | NELSON_R1 | vacuum_pump1_kPa | 2 | 18505 | 34.5 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1153 | high | NELSON_R1 | vacuum_pump1_kPa | 2 | 19090 | 68.1 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1154 | high | NELSON_R1 | vacuum_pump1_kPa | 2 | 19303 | 35.2 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1155 | high | NELSON_R1 | vacuum_pump1_kPa | 2 | 19492 | 70.2 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1156 | high | NELSON_R1 | vacuum_pump1_kPa | 2 | 19689 | 68 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1157 | high | NELSON_R1 | vacuum_pump1_kPa | 2 | 19945 | 68.4 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1158 | high | NELSON_R1 | vacuum_pump1_kPa | 2 | 20496 | 68.7 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1159 | high | NELSON_R1 | vacuum_pump1_kPa | 2 | 20647 | 36.8 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1160 | high | NELSON_R1 | vacuum_pump1_kPa | 2 | 20872 | 36.9 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1161 | high | NELSON_R1 | vacuum_pump1_kPa | 2 | 21278 | 68 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1162 | high | NELSON_R1 | vacuum_pump1_kPa | 2 | 21586 | 36.5 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1163 | high | NELSON_R1 | vacuum_pump1_kPa | 2 | 21852 | 71 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1164 | high | NELSON_R1 | vacuum_pump1_kPa | 2 | 21965 | 68 | vacuum_pump1_kPa 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1165 | high | NELSON_R1 | white_water_consistency_pct | 2 | 5 | 1.781 | white_water_consistency_pct 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1166 | high | NELSON_R1 | white_water_consistency_pct | 2 | 250 | 1.14 | white_water_consistency_pct 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1167 | high | NELSON_R1 | white_water_consistency_pct | 2 | 494 | 1.144 | white_water_consistency_pct 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1168 | high | NELSON_R1 | white_water_consistency_pct | 2 | 629 | 1.128 | white_water_consistency_pct 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1169 | high | NELSON_R1 | white_water_consistency_pct | 2 | 876 | 1.234 | white_water_consistency_pct 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1170 | high | NELSON_R1 | white_water_consistency_pct | 2 | 957 | 1.368 | white_water_consistency_pct 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1171 | high | NELSON_R1 | white_water_consistency_pct | 2 | 1082 | 1.164 | white_water_consistency_pct 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1172 | high | NELSON_R1 | white_water_consistency_pct | 2 | 1235 | 1.142 | white_water_consistency_pct 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1173 | high | NELSON_R1 | white_water_consistency_pct | 2 | 1368 | 1.127 | white_water_consistency_pct 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1174 | high | NELSON_R1 | white_water_consistency_pct | 2 | 2095 | 1.163 | white_water_consistency_pct 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1175 | high | NELSON_R1 | white_water_consistency_pct | 2 | 12129 | 1.152 | white_water_consistency_pct 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1176 | high | NELSON_R1 | white_water_consistency_pct | 2 | 20593 | 1.16 | white_water_consistency_pct 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1177 | high | NELSON_R1 | white_water_consistency_pct | 2 | 20885 | 1.167 | white_water_consistency_pct 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1178 | high | NELSON_R1 | white_water_consistency_pct | 2 | 21198 | 1.238 | white_water_consistency_pct 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1179 | high | NELSON_R1 | white_water_consistency_pct | 2 | 21478 | 1.318 | white_water_consistency_pct 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1180 | high | NELSON_R1 | white_water_consistency_pct | 2 | 21987 | 1.213 | white_water_consistency_pct 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 1181 | high | NELSON_R5 | fan_pump_speed_rpm | 1 | 14 | 886.9 | fan_pump_speed_rpm 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1182 | high | NELSON_R5 | fan_pump_speed_rpm | 1 | 2286 | 893.7 | fan_pump_speed_rpm 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1183 | high | NELSON_R5 | fan_pump_speed_rpm | 1 | 2565 | 889.6 | fan_pump_speed_rpm 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1184 | high | NELSON_R5 | fan_pump_speed_rpm | 1 | 2705 | 893.9 | fan_pump_speed_rpm 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1185 | high | NELSON_R5 | fan_pump_speed_rpm | 1 | 2880 | 893.6 | fan_pump_speed_rpm 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1186 | high | NELSON_R5 | fan_pump_speed_rpm | 1 | 2943 | 894.4 | fan_pump_speed_rpm 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1187 | high | NELSON_R5 | fan_pump_speed_rpm | 1 | 3127 | 900.5 | fan_pump_speed_rpm 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1188 | high | NELSON_R5 | fan_pump_speed_rpm | 1 | 3250 | 893.1 | fan_pump_speed_rpm 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1189 | high | NELSON_R5 | fan_pump_speed_rpm | 1 | 3445 | 890.6 | fan_pump_speed_rpm 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1190 | high | NELSON_R5 | fan_pump_speed_rpm | 1 | 3559 | 890.8 | fan_pump_speed_rpm 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1191 | high | NELSON_R5 | fan_pump_speed_rpm | 1 | 3688 | 894.2 | fan_pump_speed_rpm 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1192 | high | NELSON_R5 | fan_pump_speed_rpm | 1 | 11244 | 892.8 | fan_pump_speed_rpm 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1193 | high | NELSON_R5 | fan_pump_speed_rpm | 1 | 11959 | 891.9 | fan_pump_speed_rpm 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1194 | high | NELSON_R5 | fan_pump_speed_rpm | 1 | 21860 | 938.2 | fan_pump_speed_rpm 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1195 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 26 | 18.21 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1196 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 99 | 20.7 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1197 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 235 | 19.91 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1198 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 354 | 20.99 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1199 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 467 | 18.27 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1200 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 681 | 21.04 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1201 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 784 | 17.89 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1202 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 855 | 20.53 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1203 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 963 | 18.17 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1204 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 1084 | 17.95 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1205 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 1192 | 21.29 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1206 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 1407 | 24.93 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1207 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 1581 | 18.43 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1208 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 1724 | 18.8 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1209 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 1843 | 19.35 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1210 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 2019 | 25.87 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1211 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 2189 | 25.91 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1212 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 2373 | 25.9 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1213 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 2556 | 19.71 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1214 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 2700 | 20.13 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1215 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 2827 | 23.03 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1216 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 3025 | 19.67 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1217 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 3182 | 19.49 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1218 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 3392 | 19.97 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1219 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 3530 | 19.79 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1220 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 3731 | 20.62 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1221 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 3910 | 19.83 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1222 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 4098 | 20.63 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1223 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 4286 | 20.44 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1224 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 4415 | 28.43 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1225 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 4519 | 28.63 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1226 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 4766 | 24.97 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1227 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 5180 | 25.2 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1228 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 5347 | 25.47 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1229 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 5525 | 25.73 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1230 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 5589 | 29.65 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1231 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 6305 | 26.01 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1232 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 6658 | 22.35 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1233 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 7019 | 27.27 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1234 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 7269 | 27.45 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1235 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 7397 | 23.05 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1236 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 8252 | 32.71 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1237 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 9298 | 26.34 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1238 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 9574 | 33.71 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1239 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 10290 | 22.89 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1240 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 10651 | 25.21 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1241 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 10890 | 27.96 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1242 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 11088 | 20.55 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1243 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 11218 | 27.08 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1244 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 11398 | 19.91 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1245 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 11557 | 20.04 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1246 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 11736 | 20.56 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1247 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 11990 | 20.18 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1248 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 12430 | 21.87 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1249 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 12760 | 29.47 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1250 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 13114 | 22.2 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1251 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 13526 | 30.19 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1252 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 13715 | 22.48 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1253 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 14401 | 23.36 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1254 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 14918 | 23.65 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1255 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 15240 | 27.49 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1256 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 15312 | 23.69 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1257 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 15389 | 26.94 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1258 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 15454 | 27.45 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1259 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 16332 | 32.32 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1260 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 17237 | 25.07 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1261 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 17450 | 25.48 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1262 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 17691 | 29.98 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1263 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 17942 | 25.96 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1264 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 18029 | 34.31 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1265 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 18634 | 26.08 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1266 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 18947 | 26.35 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1267 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 19442 | 31.43 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1268 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 19989 | 37.8 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1269 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 20086 | 27.79 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1270 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 20246 | 27.83 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1271 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 20398 | 38.08 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1272 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 21616 | 29.16 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1273 | high | NELSON_R5 | headbox_pressure_kPa | 1 | 21860 | 35.05 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1274 | high | NELSON_R5 | jet_to_wire_ratio | 1 | 498 | 1.006 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1275 | high | NELSON_R5 | jet_to_wire_ratio | 1 | 1088 | 1.064 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1276 | high | NELSON_R5 | jet_to_wire_ratio | 1 | 1573 | 1.037 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1277 | high | NELSON_R5 | jet_to_wire_ratio | 1 | 1715 | 1.081 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1278 | high | NELSON_R5 | jet_to_wire_ratio | 1 | 1849 | 1.082 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1279 | high | NELSON_R5 | jet_to_wire_ratio | 1 | 2536 | 0.989 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1280 | high | NELSON_R5 | jet_to_wire_ratio | 1 | 3249 | 0.951 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1281 | high | NELSON_R5 | jet_to_wire_ratio | 1 | 4047 | 1.081 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1282 | high | NELSON_R5 | jet_to_wire_ratio | 1 | 4628 | 1.096 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1283 | high | NELSON_R5 | jet_to_wire_ratio | 1 | 5123 | 0.956 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1284 | high | NELSON_R5 | jet_to_wire_ratio | 1 | 5222 | 1.083 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1285 | high | NELSON_R5 | jet_to_wire_ratio | 1 | 6961 | 1.085 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1286 | high | NELSON_R5 | jet_to_wire_ratio | 1 | 8526 | 1.011 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1287 | high | NELSON_R5 | jet_to_wire_ratio | 1 | 8835 | 0.956 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1288 | high | NELSON_R5 | jet_to_wire_ratio | 1 | 9472 | 1.001 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1289 | high | NELSON_R5 | jet_to_wire_ratio | 1 | 9562 | 0.978 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1290 | high | NELSON_R5 | jet_to_wire_ratio | 1 | 11172 | 1.045 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1291 | high | NELSON_R5 | jet_to_wire_ratio | 1 | 11252 | 0.956 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1292 | high | NELSON_R5 | jet_to_wire_ratio | 1 | 12418 | 0.958 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1293 | high | NELSON_R5 | jet_to_wire_ratio | 1 | 12886 | 0.959 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1294 | high | NELSON_R5 | jet_to_wire_ratio | 1 | 13300 | 1.089 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1295 | high | NELSON_R5 | jet_to_wire_ratio | 1 | 13932 | 1.093 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1296 | high | NELSON_R5 | jet_to_wire_ratio | 1 | 14374 | 1.062 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1297 | high | NELSON_R5 | jet_to_wire_ratio | 1 | 14687 | 0.995 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1298 | high | NELSON_R5 | jet_to_wire_ratio | 1 | 15011 | 1.081 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1299 | high | NELSON_R5 | jet_to_wire_ratio | 1 | 15492 | 1.082 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1300 | high | NELSON_R5 | jet_to_wire_ratio | 1 | 16211 | 1.031 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1301 | high | NELSON_R5 | jet_to_wire_ratio | 1 | 17130 | 1 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1302 | high | NELSON_R5 | jet_to_wire_ratio | 1 | 17673 | 1.083 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1303 | high | NELSON_R5 | jet_to_wire_ratio | 1 | 17808 | 1.005 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1304 | high | NELSON_R5 | jet_to_wire_ratio | 1 | 17987 | 1.015 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1305 | high | NELSON_R5 | jet_to_wire_ratio | 1 | 18655 | 0.953 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1306 | high | NELSON_R5 | jet_to_wire_ratio | 1 | 19320 | 1.112 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1307 | high | NELSON_R5 | jet_to_wire_ratio | 1 | 19934 | 1.002 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1308 | high | NELSON_R5 | jet_to_wire_ratio | 1 | 20006 | 0.955 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1309 | high | NELSON_R5 | jet_to_wire_ratio | 1 | 20170 | 1.042 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1310 | high | NELSON_R5 | jet_to_wire_ratio | 1 | 21791 | 1.021 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1311 | high | NELSON_R5 | machine_speed_mmin | 1 | 26 | 1303 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1312 | high | NELSON_R5 | machine_speed_mmin | 1 | 88 | 1518 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1313 | high | NELSON_R5 | machine_speed_mmin | 1 | 155 | 1324 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1314 | high | NELSON_R5 | machine_speed_mmin | 1 | 221 | 1513 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1315 | high | NELSON_R5 | machine_speed_mmin | 1 | 293 | 1315 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1316 | high | NELSON_R5 | machine_speed_mmin | 1 | 467 | 1319 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1317 | high | NELSON_R5 | machine_speed_mmin | 1 | 612 | 1319 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1318 | high | NELSON_R5 | machine_speed_mmin | 1 | 784 | 1313 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1319 | high | NELSON_R5 | machine_speed_mmin | 1 | 846 | 1512 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1320 | high | NELSON_R5 | machine_speed_mmin | 1 | 963 | 1322 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1321 | high | NELSON_R5 | machine_speed_mmin | 1 | 1084 | 1320 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1322 | high | NELSON_R5 | machine_speed_mmin | 1 | 1234 | 1326 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1323 | high | NELSON_R5 | machine_speed_mmin | 1 | 1301 | 1506 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1324 | high | NELSON_R5 | machine_speed_mmin | 1 | 1423 | 1323 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1325 | high | NELSON_R5 | machine_speed_mmin | 1 | 1581 | 1316 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1326 | high | NELSON_R5 | machine_speed_mmin | 1 | 1724 | 1325 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1327 | high | NELSON_R5 | machine_speed_mmin | 1 | 1843 | 1318 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1328 | high | NELSON_R5 | machine_speed_mmin | 1 | 1919 | 1516 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1329 | high | NELSON_R5 | machine_speed_mmin | 1 | 2042 | 1705 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1330 | high | NELSON_R5 | machine_speed_mmin | 1 | 2203 | 1332 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1331 | high | NELSON_R5 | machine_speed_mmin | 1 | 2405 | 1316 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1332 | high | NELSON_R5 | machine_speed_mmin | 1 | 2474 | 1514 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1333 | high | NELSON_R5 | machine_speed_mmin | 1 | 2556 | 1322 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1334 | high | NELSON_R5 | machine_speed_mmin | 1 | 2620 | 1504 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1335 | high | NELSON_R5 | machine_speed_mmin | 1 | 2700 | 1308 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1336 | high | NELSON_R5 | machine_speed_mmin | 1 | 2763 | 1508 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1337 | high | NELSON_R5 | machine_speed_mmin | 1 | 2886 | 1317 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1338 | high | NELSON_R5 | machine_speed_mmin | 1 | 3025 | 1330 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1339 | high | NELSON_R5 | machine_speed_mmin | 1 | 3094 | 1522 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1340 | high | NELSON_R5 | machine_speed_mmin | 1 | 3182 | 1322 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1341 | high | NELSON_R5 | machine_speed_mmin | 1 | 3255 | 1508 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1342 | high | NELSON_R5 | machine_speed_mmin | 1 | 3392 | 1340 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1343 | high | NELSON_R5 | machine_speed_mmin | 1 | 3530 | 1335 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1344 | high | NELSON_R5 | machine_speed_mmin | 1 | 3596 | 1508 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1345 | high | NELSON_R5 | machine_speed_mmin | 1 | 3730 | 1324 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1346 | high | NELSON_R5 | machine_speed_mmin | 1 | 3805 | 1529 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1347 | high | NELSON_R5 | machine_speed_mmin | 1 | 3867 | 1699 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1348 | high | NELSON_R5 | machine_speed_mmin | 1 | 3974 | 1533 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1349 | high | NELSON_R5 | machine_speed_mmin | 1 | 4096 | 1319 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1350 | high | NELSON_R5 | machine_speed_mmin | 1 | 4285 | 1332 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1351 | high | NELSON_R5 | machine_speed_mmin | 1 | 4429 | 1339 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1352 | high | NELSON_R5 | machine_speed_mmin | 1 | 4568 | 1324 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1353 | high | NELSON_R5 | machine_speed_mmin | 1 | 4687 | 1323 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1354 | high | NELSON_R5 | machine_speed_mmin | 1 | 4837 | 1335 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1355 | high | NELSON_R5 | machine_speed_mmin | 1 | 4981 | 1318 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1356 | high | NELSON_R5 | machine_speed_mmin | 1 | 5122 | 1316 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1357 | high | NELSON_R5 | machine_speed_mmin | 1 | 5265 | 1330 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1358 | high | NELSON_R5 | machine_speed_mmin | 1 | 5446 | 1320 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1359 | high | NELSON_R5 | machine_speed_mmin | 1 | 5562 | 1697 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1360 | high | NELSON_R5 | machine_speed_mmin | 1 | 5726 | 1368 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1361 | high | NELSON_R5 | machine_speed_mmin | 1 | 5893 | 1331 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1362 | high | NELSON_R5 | machine_speed_mmin | 1 | 6034 | 1316 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1363 | high | NELSON_R5 | machine_speed_mmin | 1 | 6173 | 1318 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1364 | high | NELSON_R5 | machine_speed_mmin | 1 | 6240 | 1516 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1365 | high | NELSON_R5 | machine_speed_mmin | 1 | 6338 | 1305 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1366 | high | NELSON_R5 | machine_speed_mmin | 1 | 6402 | 1470 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1367 | high | NELSON_R5 | machine_speed_mmin | 1 | 6519 | 1321 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1368 | high | NELSON_R5 | machine_speed_mmin | 1 | 6654 | 1337 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1369 | high | NELSON_R5 | machine_speed_mmin | 1 | 6793 | 1326 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1370 | high | NELSON_R5 | machine_speed_mmin | 1 | 6895 | 1320 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1371 | high | NELSON_R5 | machine_speed_mmin | 1 | 6958 | 1507 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1372 | high | NELSON_R5 | machine_speed_mmin | 1 | 7074 | 1320 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1373 | high | NELSON_R5 | machine_speed_mmin | 1 | 7196 | 1704 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1374 | high | NELSON_R5 | machine_speed_mmin | 1 | 7338 | 1322 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1375 | high | NELSON_R5 | machine_speed_mmin | 1 | 7400 | 1511 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1376 | high | NELSON_R5 | machine_speed_mmin | 1 | 7495 | 1320 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1377 | high | NELSON_R5 | machine_speed_mmin | 1 | 7650 | 1323 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1378 | high | NELSON_R5 | machine_speed_mmin | 1 | 7716 | 1510 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1379 | high | NELSON_R5 | machine_speed_mmin | 1 | 7821 | 1317 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1380 | high | NELSON_R5 | machine_speed_mmin | 1 | 7953 | 1293 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1381 | high | NELSON_R5 | machine_speed_mmin | 1 | 8128 | 1311 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1382 | high | NELSON_R5 | machine_speed_mmin | 1 | 8278 | 1327 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1383 | high | NELSON_R5 | machine_speed_mmin | 1 | 8450 | 1330 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1384 | high | NELSON_R5 | machine_speed_mmin | 1 | 8518 | 1515 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1385 | high | NELSON_R5 | machine_speed_mmin | 1 | 8614 | 1319 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1386 | high | NELSON_R5 | machine_speed_mmin | 1 | 8826 | 1350 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1387 | high | NELSON_R5 | machine_speed_mmin | 1 | 8960 | 1308 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1388 | high | NELSON_R5 | machine_speed_mmin | 1 | 9025 | 1513 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1389 | high | NELSON_R5 | machine_speed_mmin | 1 | 9099 | 1342 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1390 | high | NELSON_R5 | machine_speed_mmin | 1 | 9278 | 1320 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1391 | high | NELSON_R5 | machine_speed_mmin | 1 | 9339 | 1509 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1392 | high | NELSON_R5 | machine_speed_mmin | 1 | 9438 | 1335 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1393 | high | NELSON_R5 | machine_speed_mmin | 1 | 9602 | 1316 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1394 | high | NELSON_R5 | machine_speed_mmin | 1 | 9680 | 1564 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1395 | high | NELSON_R5 | machine_speed_mmin | 1 | 9772 | 1304 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1396 | high | NELSON_R5 | machine_speed_mmin | 1 | 9942 | 1302 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1397 | high | NELSON_R5 | machine_speed_mmin | 1 | 10008 | 1499 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1398 | high | NELSON_R5 | machine_speed_mmin | 1 | 10106 | 1707 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1399 | high | NELSON_R5 | machine_speed_mmin | 1 | 10278 | 1317 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1400 | high | NELSON_R5 | machine_speed_mmin | 1 | 10432 | 1329 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1401 | high | NELSON_R5 | machine_speed_mmin | 1 | 10499 | 1563 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1402 | high | NELSON_R5 | machine_speed_mmin | 1 | 10583 | 1328 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1403 | high | NELSON_R5 | machine_speed_mmin | 1 | 10644 | 1503 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1404 | high | NELSON_R5 | machine_speed_mmin | 1 | 10714 | 1304 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1405 | high | NELSON_R5 | machine_speed_mmin | 1 | 10801 | 1543 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1406 | high | NELSON_R5 | machine_speed_mmin | 1 | 10926 | 1324 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1407 | high | NELSON_R5 | machine_speed_mmin | 1 | 10990 | 1497 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1408 | high | NELSON_R5 | machine_speed_mmin | 1 | 11088 | 1309 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1409 | high | NELSON_R5 | machine_speed_mmin | 1 | 11245 | 1331 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1410 | high | NELSON_R5 | machine_speed_mmin | 1 | 11398 | 1320 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1411 | high | NELSON_R5 | machine_speed_mmin | 1 | 11519 | 1699 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1412 | high | NELSON_R5 | machine_speed_mmin | 1 | 11736 | 1317 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1413 | high | NELSON_R5 | machine_speed_mmin | 1 | 11865 | 1322 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1414 | high | NELSON_R5 | machine_speed_mmin | 1 | 12034 | 1527 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1415 | high | NELSON_R5 | machine_speed_mmin | 1 | 12136 | 1308 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1416 | high | NELSON_R5 | machine_speed_mmin | 1 | 12263 | 1318 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1417 | high | NELSON_R5 | machine_speed_mmin | 1 | 12331 | 1514 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1418 | high | NELSON_R5 | machine_speed_mmin | 1 | 12420 | 1313 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1419 | high | NELSON_R5 | machine_speed_mmin | 1 | 12640 | 1318 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1420 | high | NELSON_R5 | machine_speed_mmin | 1 | 12710 | 1506 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1421 | high | NELSON_R5 | machine_speed_mmin | 1 | 12785 | 1321 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1422 | high | NELSON_R5 | machine_speed_mmin | 1 | 12849 | 1513 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1423 | high | NELSON_R5 | machine_speed_mmin | 1 | 12962 | 1314 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1424 | high | NELSON_R5 | machine_speed_mmin | 1 | 13031 | 1521 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1425 | high | NELSON_R5 | machine_speed_mmin | 1 | 13114 | 1310 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1426 | high | NELSON_R5 | machine_speed_mmin | 1 | 13235 | 1319 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1427 | high | NELSON_R5 | machine_speed_mmin | 1 | 13364 | 1332 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1428 | high | NELSON_R5 | machine_speed_mmin | 1 | 13429 | 1518 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1429 | high | NELSON_R5 | machine_speed_mmin | 1 | 13563 | 1306 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1430 | high | NELSON_R5 | machine_speed_mmin | 1 | 13708 | 1319 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1431 | high | NELSON_R5 | machine_speed_mmin | 1 | 13857 | 1334 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1432 | high | NELSON_R5 | machine_speed_mmin | 1 | 13928 | 1494 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1433 | high | NELSON_R5 | machine_speed_mmin | 1 | 14002 | 1698 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1434 | high | NELSON_R5 | machine_speed_mmin | 1 | 14096 | 1504 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1435 | high | NELSON_R5 | machine_speed_mmin | 1 | 14192 | 1336 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1436 | high | NELSON_R5 | machine_speed_mmin | 1 | 14379 | 1331 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1437 | high | NELSON_R5 | machine_speed_mmin | 1 | 14442 | 1514 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1438 | high | NELSON_R5 | machine_speed_mmin | 1 | 14543 | 1321 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1439 | high | NELSON_R5 | machine_speed_mmin | 1 | 14737 | 1327 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1440 | high | NELSON_R5 | machine_speed_mmin | 1 | 14867 | 1318 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1441 | high | NELSON_R5 | machine_speed_mmin | 1 | 14933 | 1507 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1442 | high | NELSON_R5 | machine_speed_mmin | 1 | 15043 | 1331 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1443 | high | NELSON_R5 | machine_speed_mmin | 1 | 15173 | 1321 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1444 | high | NELSON_R5 | machine_speed_mmin | 1 | 15307 | 1333 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1445 | high | NELSON_R5 | machine_speed_mmin | 1 | 15385 | 1523 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1446 | high | NELSON_R5 | machine_speed_mmin | 1 | 15525 | 1319 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1447 | high | NELSON_R5 | machine_speed_mmin | 1 | 15694 | 1319 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1448 | high | NELSON_R5 | machine_speed_mmin | 1 | 15859 | 1320 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1449 | high | NELSON_R5 | machine_speed_mmin | 1 | 15931 | 1514 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1450 | high | NELSON_R5 | machine_speed_mmin | 1 | 16059 | 1302 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1451 | high | NELSON_R5 | machine_speed_mmin | 1 | 16230 | 1321 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1452 | high | NELSON_R5 | machine_speed_mmin | 1 | 16297 | 1524 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1453 | high | NELSON_R5 | machine_speed_mmin | 1 | 16359 | 1323 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1454 | high | NELSON_R5 | machine_speed_mmin | 1 | 16504 | 1697 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1455 | high | NELSON_R5 | machine_speed_mmin | 1 | 16681 | 1322 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1456 | high | NELSON_R5 | machine_speed_mmin | 1 | 16750 | 1517 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1457 | high | NELSON_R5 | machine_speed_mmin | 1 | 16881 | 1319 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1458 | high | NELSON_R5 | machine_speed_mmin | 1 | 17021 | 1314 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1459 | high | NELSON_R5 | machine_speed_mmin | 1 | 17190 | 1326 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1460 | high | NELSON_R5 | machine_speed_mmin | 1 | 17267 | 1525 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1461 | high | NELSON_R5 | machine_speed_mmin | 1 | 17398 | 1312 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1462 | high | NELSON_R5 | machine_speed_mmin | 1 | 17605 | 1390 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1463 | high | NELSON_R5 | machine_speed_mmin | 1 | 17739 | 1310 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1464 | high | NELSON_R5 | machine_speed_mmin | 1 | 17813 | 1518 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1465 | high | NELSON_R5 | machine_speed_mmin | 1 | 17907 | 1334 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1466 | high | NELSON_R5 | machine_speed_mmin | 1 | 17969 | 1496 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1467 | high | NELSON_R5 | machine_speed_mmin | 1 | 18034 | 1698 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1468 | high | NELSON_R5 | machine_speed_mmin | 1 | 18214 | 1325 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1469 | high | NELSON_R5 | machine_speed_mmin | 1 | 18277 | 1506 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1470 | high | NELSON_R5 | machine_speed_mmin | 1 | 18394 | 1315 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1471 | high | NELSON_R5 | machine_speed_mmin | 1 | 18456 | 1514 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1472 | high | NELSON_R5 | machine_speed_mmin | 1 | 18553 | 1695 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1473 | high | NELSON_R5 | machine_speed_mmin | 1 | 18712 | 1307 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1474 | high | NELSON_R5 | machine_speed_mmin | 1 | 18784 | 1518 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1475 | high | NELSON_R5 | machine_speed_mmin | 1 | 18908 | 1322 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1476 | high | NELSON_R5 | machine_speed_mmin | 1 | 19026 | 1330 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1477 | high | NELSON_R5 | machine_speed_mmin | 1 | 19177 | 1309 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1478 | high | NELSON_R5 | machine_speed_mmin | 1 | 19348 | 1311 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1479 | high | NELSON_R5 | machine_speed_mmin | 1 | 19511 | 1327 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1480 | high | NELSON_R5 | machine_speed_mmin | 1 | 19705 | 1306 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1481 | high | NELSON_R5 | machine_speed_mmin | 1 | 19892 | 1319 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1482 | high | NELSON_R5 | machine_speed_mmin | 1 | 20037 | 1693 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1483 | high | NELSON_R5 | machine_speed_mmin | 1 | 20208 | 1320 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1484 | high | NELSON_R5 | machine_speed_mmin | 1 | 20317 | 1332 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1485 | high | NELSON_R5 | machine_speed_mmin | 1 | 20422 | 1338 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1486 | high | NELSON_R5 | machine_speed_mmin | 1 | 20576 | 1316 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1487 | high | NELSON_R5 | machine_speed_mmin | 1 | 20649 | 1490 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1488 | high | NELSON_R5 | machine_speed_mmin | 1 | 20763 | 1306 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1489 | high | NELSON_R5 | machine_speed_mmin | 1 | 20884 | 1293 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1490 | high | NELSON_R5 | machine_speed_mmin | 1 | 21012 | 1313 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1491 | high | NELSON_R5 | machine_speed_mmin | 1 | 21252 | 1308 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1492 | high | NELSON_R5 | machine_speed_mmin | 1 | 21408 | 1687 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1493 | high | NELSON_R5 | machine_speed_mmin | 1 | 21565 | 1313 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1494 | high | NELSON_R5 | machine_speed_mmin | 1 | 21645 | 1517 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1495 | high | NELSON_R5 | machine_speed_mmin | 1 | 21725 | 1331 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1496 | high | NELSON_R5 | machine_speed_mmin | 1 | 21795 | 1495 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1497 | high | NELSON_R5 | stock_temp_C | 1 | 2 | 52.6 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1498 | high | NELSON_R5 | stock_temp_C | 1 | 199 | 40.7 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1499 | high | NELSON_R5 | stock_temp_C | 1 | 381 | 64.8 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1500 | high | NELSON_R5 | stock_temp_C | 1 | 756 | 50.5 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1501 | high | NELSON_R5 | stock_temp_C | 1 | 976 | 44.9 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1502 | high | NELSON_R5 | stock_temp_C | 1 | 1087 | 48.8 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1503 | high | NELSON_R5 | stock_temp_C | 1 | 1470 | 50.3 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1504 | high | NELSON_R5 | stock_temp_C | 1 | 1835 | 49.6 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1505 | high | NELSON_R5 | stock_temp_C | 1 | 2025 | 44.5 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1506 | high | NELSON_R5 | stock_temp_C | 1 | 2367 | 47.4 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1507 | high | NELSON_R5 | stock_temp_C | 1 | 2712 | 43.1 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1508 | high | NELSON_R5 | stock_temp_C | 1 | 3047 | 43.6 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1509 | high | NELSON_R5 | stock_temp_C | 1 | 3407 | 42.7 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1510 | high | NELSON_R5 | stock_temp_C | 1 | 3490 | 41.1 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1511 | high | NELSON_R5 | stock_temp_C | 1 | 3758 | 43.5 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1512 | high | NELSON_R5 | stock_temp_C | 1 | 4089 | 42.3 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1513 | high | NELSON_R5 | stock_temp_C | 1 | 4232 | 43 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1514 | high | NELSON_R5 | stock_temp_C | 1 | 4464 | 44.4 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1515 | high | NELSON_R5 | stock_temp_C | 1 | 4613 | 43 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1516 | high | NELSON_R5 | stock_temp_C | 1 | 4817 | 43.3 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1517 | high | NELSON_R5 | stock_temp_C | 1 | 4967 | 42.9 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1518 | high | NELSON_R5 | stock_temp_C | 1 | 5352 | 42.5 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1519 | high | NELSON_R5 | stock_temp_C | 1 | 5491 | 43.2 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1520 | high | NELSON_R5 | stock_temp_C | 1 | 5683 | 43.3 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1521 | high | NELSON_R5 | stock_temp_C | 1 | 5853 | 41.8 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1522 | high | NELSON_R5 | stock_temp_C | 1 | 6048 | 43.8 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1523 | high | NELSON_R5 | stock_temp_C | 1 | 6199 | 44 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1524 | high | NELSON_R5 | stock_temp_C | 1 | 6423 | 44.3 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1525 | high | NELSON_R5 | stock_temp_C | 1 | 6553 | 43.8 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1526 | high | NELSON_R5 | stock_temp_C | 1 | 6780 | 44 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1527 | high | NELSON_R5 | stock_temp_C | 1 | 6899 | 44 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1528 | high | NELSON_R5 | stock_temp_C | 1 | 7146 | 43.4 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1529 | high | NELSON_R5 | stock_temp_C | 1 | 7237 | 43.8 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1530 | high | NELSON_R5 | stock_temp_C | 1 | 7513 | 43.7 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1531 | high | NELSON_R5 | stock_temp_C | 1 | 7900 | 42.6 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1532 | high | NELSON_R5 | stock_temp_C | 1 | 8266 | 43.5 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1533 | high | NELSON_R5 | stock_temp_C | 1 | 8633 | 44.6 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1534 | high | NELSON_R5 | stock_temp_C | 1 | 9300 | 44.6 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1535 | high | NELSON_R5 | stock_temp_C | 1 | 10275 | 39.6 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1536 | high | NELSON_R5 | stock_temp_C | 1 | 10565 | 36.8 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1537 | high | NELSON_R5 | stock_temp_C | 1 | 11022 | 41.1 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1538 | high | NELSON_R5 | stock_temp_C | 1 | 13078 | 35.9 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1539 | high | NELSON_R5 | stock_temp_C | 1 | 13430 | 35.4 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1540 | high | NELSON_R5 | stock_temp_C | 1 | 13759 | 35.4 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1541 | high | NELSON_R5 | stock_temp_C | 1 | 15665 | 38.3 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1542 | high | NELSON_R5 | stock_temp_C | 1 | 16228 | 36.8 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1543 | high | NELSON_R5 | stock_temp_C | 1 | 16546 | 38.9 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1544 | high | NELSON_R5 | stock_temp_C | 1 | 17123 | 44.7 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1545 | high | NELSON_R5 | stock_temp_C | 1 | 17269 | 38.6 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1546 | high | NELSON_R5 | stock_temp_C | 1 | 17496 | 43.8 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1547 | high | NELSON_R5 | stock_temp_C | 1 | 17889 | 43.5 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1548 | high | NELSON_R5 | stock_temp_C | 1 | 18169 | 40.4 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1549 | high | NELSON_R5 | stock_temp_C | 1 | 18231 | 42.1 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1550 | high | NELSON_R5 | stock_temp_C | 1 | 18584 | 43.8 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1551 | high | NELSON_R5 | stock_temp_C | 1 | 18947 | 42.6 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1552 | high | NELSON_R5 | stock_temp_C | 1 | 19155 | 39.5 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1553 | high | NELSON_R5 | stock_temp_C | 1 | 19323 | 43.2 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1554 | high | NELSON_R5 | stock_temp_C | 1 | 19435 | 44.1 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1555 | high | NELSON_R5 | stock_temp_C | 1 | 19661 | 42.9 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1556 | high | NELSON_R5 | stock_temp_C | 1 | 19793 | 43.1 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1557 | high | NELSON_R5 | stock_temp_C | 1 | 20036 | 43.5 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1558 | high | NELSON_R5 | stock_temp_C | 1 | 20171 | 43 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1559 | high | NELSON_R5 | stock_temp_C | 1 | 20383 | 43.6 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1560 | high | NELSON_R5 | stock_temp_C | 1 | 20763 | 44.2 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1561 | high | NELSON_R5 | stock_temp_C | 1 | 20959 | 43.7 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1562 | high | NELSON_R5 | stock_temp_C | 1 | 21129 | 43.5 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1563 | high | NELSON_R5 | stock_temp_C | 1 | 21314 | 43.1 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1564 | high | NELSON_R5 | stock_temp_C | 1 | 21685 | 43.8 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1565 | high | NELSON_R5 | stock_temp_C | 1 | 21841 | 42.5 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1566 | high | NELSON_R5 | vacuum_pump1_kPa | 1 | 350 | 63.1 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1567 | high | NELSON_R5 | vacuum_pump1_kPa | 1 | 1708 | 52.8 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1568 | high | NELSON_R5 | vacuum_pump1_kPa | 1 | 1803 | 43.6 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1569 | high | NELSON_R5 | vacuum_pump1_kPa | 1 | 3729 | 56.6 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1570 | high | NELSON_R5 | vacuum_pump1_kPa | 1 | 4264 | 58.1 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1571 | high | NELSON_R5 | vacuum_pump1_kPa | 1 | 4565 | 41.4 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1572 | high | NELSON_R5 | vacuum_pump1_kPa | 1 | 4730 | 56 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1573 | high | NELSON_R5 | vacuum_pump1_kPa | 1 | 5167 | 62.5 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1574 | high | NELSON_R5 | vacuum_pump1_kPa | 1 | 5352 | 62.1 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1575 | high | NELSON_R5 | vacuum_pump1_kPa | 1 | 5535 | 52 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1576 | high | NELSON_R5 | vacuum_pump1_kPa | 1 | 5643 | 56.8 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1577 | high | NELSON_R5 | vacuum_pump1_kPa | 1 | 6061 | 46.7 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1578 | high | NELSON_R5 | vacuum_pump1_kPa | 1 | 8535 | 68.4 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1579 | high | NELSON_R5 | vacuum_pump1_kPa | 1 | 8847 | 38.8 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1580 | high | NELSON_R5 | vacuum_pump1_kPa | 1 | 9688 | 58.8 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1581 | high | NELSON_R5 | vacuum_pump1_kPa | 1 | 10094 | 41.8 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1582 | high | NELSON_R5 | vacuum_pump1_kPa | 1 | 11691 | 61.9 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1583 | high | NELSON_R5 | vacuum_pump1_kPa | 1 | 11779 | 55.8 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1584 | high | NELSON_R5 | vacuum_pump1_kPa | 1 | 12212 | 55.7 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1585 | high | NELSON_R5 | vacuum_pump1_kPa | 1 | 12803 | 56.5 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1586 | high | NELSON_R5 | vacuum_pump1_kPa | 1 | 12898 | 63.9 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1587 | high | NELSON_R5 | vacuum_pump1_kPa | 1 | 13406 | 49.8 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1588 | high | NELSON_R5 | vacuum_pump1_kPa | 1 | 13769 | 41.8 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1589 | high | NELSON_R5 | vacuum_pump1_kPa | 1 | 13887 | 41.5 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1590 | high | NELSON_R5 | vacuum_pump1_kPa | 1 | 14053 | 63.7 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1591 | high | NELSON_R5 | vacuum_pump1_kPa | 1 | 14964 | 51.5 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1592 | high | NELSON_R5 | vacuum_pump1_kPa | 1 | 15128 | 40.2 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1593 | high | NELSON_R5 | vacuum_pump1_kPa | 1 | 15320 | 62.3 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1594 | high | NELSON_R5 | vacuum_pump1_kPa | 1 | 15481 | 62.2 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1595 | high | NELSON_R5 | vacuum_pump1_kPa | 1 | 15686 | 41.7 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1596 | high | NELSON_R5 | vacuum_pump1_kPa | 1 | 16026 | 49 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1597 | high | NELSON_R5 | vacuum_pump1_kPa | 1 | 16474 | 64.3 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1598 | high | NELSON_R5 | vacuum_pump1_kPa | 1 | 17224 | 62.3 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1599 | high | NELSON_R5 | vacuum_pump1_kPa | 1 | 17666 | 55.1 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1600 | high | NELSON_R5 | vacuum_pump1_kPa | 1 | 17922 | 41.2 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1601 | high | NELSON_R5 | vacuum_pump1_kPa | 1 | 18025 | 62.6 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1602 | high | NELSON_R5 | vacuum_pump1_kPa | 1 | 19363 | 65.6 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1603 | high | NELSON_R5 | vacuum_pump1_kPa | 1 | 19931 | 38 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1604 | high | NELSON_R5 | vacuum_pump1_kPa | 1 | 20883 | 51.2 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1605 | high | NELSON_R5 | vacuum_pump1_kPa | 1 | 21084 | 53.6 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1606 | high | NELSON_R5 | vacuum_pump1_kPa | 1 | 21279 | 40.1 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1607 | high | NELSON_R5 | vacuum_pump1_kPa | 1 | 21653 | 64.1 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1608 | high | NELSON_R5 | vacuum_pump1_kPa | 1 | 21755 | 41.5 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1609 | high | NELSON_R5 | vacuum_pump1_kPa | 1 | 21857 | 41.6 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1610 | high | NELSON_R5 | white_water_consistency_pct | 1 | 82 | 1.073 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1611 | high | NELSON_R5 | white_water_consistency_pct | 1 | 150 | 1.071 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1612 | high | NELSON_R5 | white_water_consistency_pct | 1 | 346 | 1.031 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1613 | high | NELSON_R5 | white_water_consistency_pct | 1 | 512 | 0.998 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1614 | high | NELSON_R5 | white_water_consistency_pct | 1 | 582 | 1.025 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1615 | high | NELSON_R5 | white_water_consistency_pct | 1 | 907 | 1.102 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1616 | high | NELSON_R5 | white_water_consistency_pct | 1 | 1063 | 0.975 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1617 | high | NELSON_R5 | white_water_consistency_pct | 1 | 1223 | 0.912 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1618 | high | NELSON_R5 | white_water_consistency_pct | 1 | 5454 | 0.929 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1619 | high | NELSON_R5 | white_water_consistency_pct | 1 | 5594 | 0.998 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1620 | high | NELSON_R5 | white_water_consistency_pct | 1 | 6050 | 1.01 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1621 | high | NELSON_R5 | white_water_consistency_pct | 1 | 6145 | 0.974 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1622 | high | NELSON_R5 | white_water_consistency_pct | 1 | 6351 | 1.019 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1623 | high | NELSON_R5 | white_water_consistency_pct | 1 | 6734 | 0.964 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1624 | high | NELSON_R5 | white_water_consistency_pct | 1 | 6817 | 1.026 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1625 | high | NELSON_R5 | white_water_consistency_pct | 1 | 6932 | 1.005 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1626 | high | NELSON_R5 | white_water_consistency_pct | 1 | 7188 | 1.023 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1627 | high | NELSON_R5 | white_water_consistency_pct | 1 | 7360 | 1.031 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1628 | high | NELSON_R5 | white_water_consistency_pct | 1 | 7480 | 1.024 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1629 | high | NELSON_R5 | white_water_consistency_pct | 1 | 7710 | 1.134 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1630 | high | NELSON_R5 | white_water_consistency_pct | 1 | 7819 | 1.029 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1631 | high | NELSON_R5 | white_water_consistency_pct | 1 | 8083 | 0.899 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1632 | high | NELSON_R5 | white_water_consistency_pct | 1 | 9831 | 1.03 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1633 | high | NELSON_R5 | white_water_consistency_pct | 1 | 9931 | 1.007 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1634 | high | NELSON_R5 | white_water_consistency_pct | 1 | 10096 | 1.012 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1635 | high | NELSON_R5 | white_water_consistency_pct | 1 | 10270 | 1.03 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1636 | high | NELSON_R5 | white_water_consistency_pct | 1 | 12908 | 1.004 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1637 | high | NELSON_R5 | white_water_consistency_pct | 1 | 13063 | 1.031 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1638 | high | NELSON_R5 | white_water_consistency_pct | 1 | 13136 | 1.021 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1639 | high | NELSON_R5 | white_water_consistency_pct | 1 | 13404 | 0.969 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1640 | high | NELSON_R5 | white_water_consistency_pct | 1 | 13543 | 1.08 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1641 | high | NELSON_R5 | white_water_consistency_pct | 1 | 13607 | 1.005 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1642 | high | NELSON_R5 | white_water_consistency_pct | 1 | 13763 | 1.001 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1643 | high | NELSON_R5 | white_water_consistency_pct | 1 | 13873 | 1.032 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1644 | high | NELSON_R5 | white_water_consistency_pct | 1 | 14221 | 1.035 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1645 | high | NELSON_R5 | white_water_consistency_pct | 1 | 14373 | 1.031 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1646 | high | NELSON_R5 | white_water_consistency_pct | 1 | 14538 | 1.015 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1647 | high | NELSON_R5 | white_water_consistency_pct | 1 | 14660 | 1.035 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1648 | high | NELSON_R5 | white_water_consistency_pct | 1 | 14856 | 1.031 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1649 | high | NELSON_R5 | white_water_consistency_pct | 1 | 15063 | 1.079 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1650 | high | NELSON_R5 | white_water_consistency_pct | 1 | 15134 | 1.08 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1651 | high | NELSON_R5 | white_water_consistency_pct | 1 | 15394 | 1.026 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1652 | high | NELSON_R5 | white_water_consistency_pct | 1 | 15625 | 0.95 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1653 | high | NELSON_R5 | white_water_consistency_pct | 1 | 15963 | 0.992 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1654 | high | NELSON_R5 | white_water_consistency_pct | 1 | 16417 | 0.999 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1655 | high | NELSON_R5 | white_water_consistency_pct | 1 | 16630 | 0.856 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1656 | high | NELSON_R5 | white_water_consistency_pct | 1 | 16747 | 0.938 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1657 | high | NELSON_R5 | white_water_consistency_pct | 1 | 16953 | 1.018 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1658 | high | NELSON_R5 | white_water_consistency_pct | 1 | 17477 | 0.862 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1659 | high | NELSON_R5 | white_water_consistency_pct | 1 | 18141 | 0.968 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1660 | high | NELSON_R5 | white_water_consistency_pct | 1 | 18807 | 0.967 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1661 | high | NELSON_R5 | white_water_consistency_pct | 1 | 20757 | 0.991 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1662 | high | NELSON_R5 | white_water_consistency_pct | 1 | 21172 | 1.016 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1663 | high | NELSON_R5 | white_water_consistency_pct | 1 | 21860 | 1.224 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1664 | high | NELSON_R5 | fan_pump_speed_rpm | 2 | 15 | 891.6 | fan_pump_speed_rpm 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1665 | high | NELSON_R5 | fan_pump_speed_rpm | 2 | 2014 | 895.3 | fan_pump_speed_rpm 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1666 | high | NELSON_R5 | fan_pump_speed_rpm | 2 | 2470 | 892 | fan_pump_speed_rpm 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1667 | high | NELSON_R5 | fan_pump_speed_rpm | 2 | 2572 | 895.1 | fan_pump_speed_rpm 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1668 | high | NELSON_R5 | fan_pump_speed_rpm | 2 | 2657 | 898.6 | fan_pump_speed_rpm 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1669 | high | NELSON_R5 | fan_pump_speed_rpm | 2 | 2917 | 895.4 | fan_pump_speed_rpm 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1670 | high | NELSON_R5 | fan_pump_speed_rpm | 2 | 3034 | 892.3 | fan_pump_speed_rpm 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1671 | high | NELSON_R5 | fan_pump_speed_rpm | 2 | 3110 | 894.5 | fan_pump_speed_rpm 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1672 | high | NELSON_R5 | fan_pump_speed_rpm | 2 | 3422 | 894.8 | fan_pump_speed_rpm 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1673 | high | NELSON_R5 | fan_pump_speed_rpm | 2 | 3541 | 893.3 | fan_pump_speed_rpm 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1674 | high | NELSON_R5 | fan_pump_speed_rpm | 2 | 3646 | 888.7 | fan_pump_speed_rpm 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1675 | high | NELSON_R5 | fan_pump_speed_rpm | 2 | 11447 | 893.8 | fan_pump_speed_rpm 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1676 | high | NELSON_R5 | fan_pump_speed_rpm | 2 | 11700 | 887.9 | fan_pump_speed_rpm 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1677 | high | NELSON_R5 | fan_pump_speed_rpm | 2 | 21987 | 943.7 | fan_pump_speed_rpm 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1678 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 28 | 18.04 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1679 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 142 | 17.21 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1680 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 369 | 20.96 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1681 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 432 | 18.02 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1682 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 734 | 17.9 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1683 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 809 | 20.78 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1684 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 921 | 17.89 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1685 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 1142 | 20.72 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1686 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 1205 | 24.22 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1687 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 1400 | 25.14 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1688 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 1577 | 18.73 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1689 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 1639 | 21.56 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1690 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 1721 | 18.88 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1691 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 1857 | 19.05 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1692 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 1932 | 22.17 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1693 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 2043 | 25.34 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1694 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 2197 | 25.91 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1695 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 2413 | 19.54 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1696 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 2491 | 22.57 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1697 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 2578 | 19.51 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1698 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 2733 | 19.99 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1699 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 2923 | 19.57 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1700 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 3078 | 19.76 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1701 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 3227 | 26.58 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1702 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 3424 | 19.69 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1703 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 3511 | 23.07 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1704 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 3587 | 19.68 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1705 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 3789 | 20.65 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1706 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 3962 | 20.42 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1707 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 4153 | 20.37 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1708 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 4538 | 28.28 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1709 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 4732 | 22.12 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1710 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 5072 | 25.39 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1711 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 5404 | 29.46 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1712 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 6330 | 25.95 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1713 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 6814 | 27.42 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1714 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 7052 | 23.16 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1715 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 7290 | 32.05 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1716 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 7681 | 28.36 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1717 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 7746 | 32.47 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1718 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 7838 | 27.92 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1719 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 8072 | 24.65 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1720 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 10010 | 33.63 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1721 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 10324 | 27.49 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1722 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 10548 | 30.97 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1723 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 10611 | 22.92 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1724 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 10987 | 25.02 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1725 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 11144 | 24.5 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1726 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 11246 | 20.4 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1727 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 11384 | 19.96 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1728 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 11563 | 19.88 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1729 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 11740 | 20.51 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1730 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 11859 | 20.15 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1731 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 12009 | 20.48 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1732 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 12151 | 20.72 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1733 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 12584 | 20.55 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1734 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 12936 | 29.29 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1735 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 13175 | 25.47 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1736 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 13695 | 22.41 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1737 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 13914 | 25.84 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1738 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 14408 | 26.54 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1739 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 14583 | 26.94 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1740 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 14821 | 30.88 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1741 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 15377 | 23.67 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1742 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 15814 | 31.62 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1743 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 16313 | 31.88 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1744 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 16468 | 32.13 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1745 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 17412 | 28.96 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1746 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 18014 | 29.69 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1747 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 18355 | 34.41 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1748 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 18475 | 30.28 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1749 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 18938 | 26.12 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1750 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 20579 | 32.91 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1751 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 20841 | 33.05 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1752 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 21334 | 33.55 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1753 | high | NELSON_R5 | headbox_pressure_kPa | 2 | 21987 | 39.61 | headbox_pressure_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1754 | high | NELSON_R5 | jet_to_wire_ratio | 2 | 125 | 1.03 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1755 | high | NELSON_R5 | jet_to_wire_ratio | 2 | 259 | 1.09 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1756 | high | NELSON_R5 | jet_to_wire_ratio | 2 | 1014 | 0.948 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1757 | high | NELSON_R5 | jet_to_wire_ratio | 2 | 1602 | 1.125 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1758 | high | NELSON_R5 | jet_to_wire_ratio | 2 | 1789 | 1.009 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1759 | high | NELSON_R5 | jet_to_wire_ratio | 2 | 2054 | 1.035 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1760 | high | NELSON_R5 | jet_to_wire_ratio | 2 | 2455 | 1.014 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1761 | high | NELSON_R5 | jet_to_wire_ratio | 2 | 3232 | 1.011 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1762 | high | NELSON_R5 | jet_to_wire_ratio | 2 | 4480 | 0.905 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1763 | high | NELSON_R5 | jet_to_wire_ratio | 2 | 4605 | 1.003 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1764 | high | NELSON_R5 | jet_to_wire_ratio | 2 | 6508 | 1.085 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1765 | high | NELSON_R5 | jet_to_wire_ratio | 2 | 7353 | 0.933 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1766 | high | NELSON_R5 | jet_to_wire_ratio | 2 | 8269 | 1.048 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1767 | high | NELSON_R5 | jet_to_wire_ratio | 2 | 8592 | 1.023 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1768 | high | NELSON_R5 | jet_to_wire_ratio | 2 | 8682 | 1.097 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1769 | high | NELSON_R5 | jet_to_wire_ratio | 2 | 9125 | 1.101 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1770 | high | NELSON_R5 | jet_to_wire_ratio | 2 | 9718 | 1.028 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1771 | high | NELSON_R5 | jet_to_wire_ratio | 2 | 10027 | 0.984 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1772 | high | NELSON_R5 | jet_to_wire_ratio | 2 | 10182 | 0.962 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1773 | high | NELSON_R5 | jet_to_wire_ratio | 2 | 10376 | 1.012 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1774 | high | NELSON_R5 | jet_to_wire_ratio | 2 | 10582 | 0.953 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1775 | high | NELSON_R5 | jet_to_wire_ratio | 2 | 11697 | 1.042 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1776 | high | NELSON_R5 | jet_to_wire_ratio | 2 | 11801 | 0.973 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1777 | high | NELSON_R5 | jet_to_wire_ratio | 2 | 11996 | 1.02 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1778 | high | NELSON_R5 | jet_to_wire_ratio | 2 | 12130 | 1.067 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1779 | high | NELSON_R5 | jet_to_wire_ratio | 2 | 12338 | 0.937 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1780 | high | NELSON_R5 | jet_to_wire_ratio | 2 | 12482 | 1.087 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1781 | high | NELSON_R5 | jet_to_wire_ratio | 2 | 13154 | 1.004 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1782 | high | NELSON_R5 | jet_to_wire_ratio | 2 | 13249 | 0.941 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1783 | high | NELSON_R5 | jet_to_wire_ratio | 2 | 13749 | 1.081 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1784 | high | NELSON_R5 | jet_to_wire_ratio | 2 | 13939 | 1.031 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1785 | high | NELSON_R5 | jet_to_wire_ratio | 2 | 14039 | 0.972 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1786 | high | NELSON_R5 | jet_to_wire_ratio | 2 | 14557 | 1.022 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1787 | high | NELSON_R5 | jet_to_wire_ratio | 2 | 14867 | 0.948 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1788 | high | NELSON_R5 | jet_to_wire_ratio | 2 | 15143 | 0.953 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1789 | high | NELSON_R5 | jet_to_wire_ratio | 2 | 15618 | 1.007 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1790 | high | NELSON_R5 | jet_to_wire_ratio | 2 | 15826 | 1.018 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1791 | high | NELSON_R5 | jet_to_wire_ratio | 2 | 15943 | 1 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1792 | high | NELSON_R5 | jet_to_wire_ratio | 2 | 16695 | 0.96 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1793 | high | NELSON_R5 | jet_to_wire_ratio | 2 | 16842 | 0.957 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1794 | high | NELSON_R5 | jet_to_wire_ratio | 2 | 17582 | 0.958 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1795 | high | NELSON_R5 | jet_to_wire_ratio | 2 | 17696 | 1.081 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1796 | high | NELSON_R5 | jet_to_wire_ratio | 2 | 17992 | 0.952 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1797 | high | NELSON_R5 | jet_to_wire_ratio | 2 | 18243 | 0.951 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1798 | high | NELSON_R5 | jet_to_wire_ratio | 2 | 18982 | 1.092 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1799 | high | NELSON_R5 | jet_to_wire_ratio | 2 | 19371 | 1.085 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1800 | high | NELSON_R5 | jet_to_wire_ratio | 2 | 19649 | 1.083 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1801 | high | NELSON_R5 | jet_to_wire_ratio | 2 | 19793 | 1.006 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1802 | high | NELSON_R5 | jet_to_wire_ratio | 2 | 20185 | 1.035 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1803 | high | NELSON_R5 | jet_to_wire_ratio | 2 | 20885 | 1.01 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1804 | high | NELSON_R5 | jet_to_wire_ratio | 2 | 21034 | 1.031 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1805 | high | NELSON_R5 | jet_to_wire_ratio | 2 | 21583 | 0.958 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1806 | high | NELSON_R5 | jet_to_wire_ratio | 2 | 21827 | 1 | jet_to_wire_ratio 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1807 | high | NELSON_R5 | machine_speed_mmin | 2 | 28 | 1315 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1808 | high | NELSON_R5 | machine_speed_mmin | 2 | 142 | 1320 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1809 | high | NELSON_R5 | machine_speed_mmin | 2 | 318 | 1495 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1810 | high | NELSON_R5 | machine_speed_mmin | 2 | 432 | 1326 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1811 | high | NELSON_R5 | machine_speed_mmin | 2 | 572 | 1296 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1812 | high | NELSON_R5 | machine_speed_mmin | 2 | 734 | 1309 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1813 | high | NELSON_R5 | machine_speed_mmin | 2 | 808 | 1513 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1814 | high | NELSON_R5 | machine_speed_mmin | 2 | 921 | 1328 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1815 | high | NELSON_R5 | machine_speed_mmin | 2 | 1044 | 1302 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1816 | high | NELSON_R5 | machine_speed_mmin | 2 | 1212 | 1717 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1817 | high | NELSON_R5 | machine_speed_mmin | 2 | 1290 | 1507 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1818 | high | NELSON_R5 | machine_speed_mmin | 2 | 1415 | 1313 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1819 | high | NELSON_R5 | machine_speed_mmin | 2 | 1480 | 1510 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1820 | high | NELSON_R5 | machine_speed_mmin | 2 | 1577 | 1325 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1821 | high | NELSON_R5 | machine_speed_mmin | 2 | 1721 | 1312 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1822 | high | NELSON_R5 | machine_speed_mmin | 2 | 1857 | 1325 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1823 | high | NELSON_R5 | machine_speed_mmin | 2 | 1925 | 1524 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1824 | high | NELSON_R5 | machine_speed_mmin | 2 | 2071 | 1305 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1825 | high | NELSON_R5 | machine_speed_mmin | 2 | 2225 | 1362 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1826 | high | NELSON_R5 | machine_speed_mmin | 2 | 2413 | 1317 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1827 | high | NELSON_R5 | machine_speed_mmin | 2 | 2480 | 1504 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1828 | high | NELSON_R5 | machine_speed_mmin | 2 | 2578 | 1317 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1829 | high | NELSON_R5 | machine_speed_mmin | 2 | 2650 | 1512 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1830 | high | NELSON_R5 | machine_speed_mmin | 2 | 2733 | 1330 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1831 | high | NELSON_R5 | machine_speed_mmin | 2 | 2923 | 1327 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1832 | high | NELSON_R5 | machine_speed_mmin | 2 | 3078 | 1318 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1833 | high | NELSON_R5 | machine_speed_mmin | 2 | 3158 | 1509 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1834 | high | NELSON_R5 | machine_speed_mmin | 2 | 3248 | 1310 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1835 | high | NELSON_R5 | machine_speed_mmin | 2 | 3313 | 1510 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1836 | high | NELSON_R5 | machine_speed_mmin | 2 | 3424 | 1312 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1837 | high | NELSON_R5 | machine_speed_mmin | 2 | 3493 | 1495 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1838 | high | NELSON_R5 | machine_speed_mmin | 2 | 3587 | 1334 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1839 | high | NELSON_R5 | machine_speed_mmin | 2 | 3653 | 1514 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1840 | high | NELSON_R5 | machine_speed_mmin | 2 | 3789 | 1327 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1841 | high | NELSON_R5 | machine_speed_mmin | 2 | 3856 | 1505 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1842 | high | NELSON_R5 | machine_speed_mmin | 2 | 3962 | 1316 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1843 | high | NELSON_R5 | machine_speed_mmin | 2 | 4029 | 1499 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1844 | high | NELSON_R5 | machine_speed_mmin | 2 | 4148 | 1326 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1845 | high | NELSON_R5 | machine_speed_mmin | 2 | 4225 | 1511 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1846 | high | NELSON_R5 | machine_speed_mmin | 2 | 4320 | 1311 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1847 | high | NELSON_R5 | machine_speed_mmin | 2 | 4449 | 1315 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1848 | high | NELSON_R5 | machine_speed_mmin | 2 | 4582 | 1314 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1849 | high | NELSON_R5 | machine_speed_mmin | 2 | 4723 | 1316 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1850 | high | NELSON_R5 | machine_speed_mmin | 2 | 4862 | 1326 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1851 | high | NELSON_R5 | machine_speed_mmin | 2 | 5025 | 1299 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1852 | high | NELSON_R5 | machine_speed_mmin | 2 | 5146 | 1313 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1853 | high | NELSON_R5 | machine_speed_mmin | 2 | 5282 | 1319 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1854 | high | NELSON_R5 | machine_speed_mmin | 2 | 5344 | 1502 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1855 | high | NELSON_R5 | machine_speed_mmin | 2 | 5490 | 1346 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1856 | high | NELSON_R5 | machine_speed_mmin | 2 | 5557 | 1508 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1857 | high | NELSON_R5 | machine_speed_mmin | 2 | 5666 | 1317 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1858 | high | NELSON_R5 | machine_speed_mmin | 2 | 5786 | 1318 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1859 | high | NELSON_R5 | machine_speed_mmin | 2 | 5962 | 1324 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1860 | high | NELSON_R5 | machine_speed_mmin | 2 | 6026 | 1519 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1861 | high | NELSON_R5 | machine_speed_mmin | 2 | 6114 | 1335 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1862 | high | NELSON_R5 | machine_speed_mmin | 2 | 6240 | 1312 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1863 | high | NELSON_R5 | machine_speed_mmin | 2 | 6403 | 1322 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1864 | high | NELSON_R5 | machine_speed_mmin | 2 | 6484 | 1510 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1865 | high | NELSON_R5 | machine_speed_mmin | 2 | 6602 | 1316 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1866 | high | NELSON_R5 | machine_speed_mmin | 2 | 6666 | 1514 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1867 | high | NELSON_R5 | machine_speed_mmin | 2 | 6761 | 1318 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1868 | high | NELSON_R5 | machine_speed_mmin | 2 | 6903 | 1312 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1869 | high | NELSON_R5 | machine_speed_mmin | 2 | 6998 | 1316 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1870 | high | NELSON_R5 | machine_speed_mmin | 2 | 7071 | 1517 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1871 | high | NELSON_R5 | machine_speed_mmin | 2 | 7180 | 1342 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1872 | high | NELSON_R5 | machine_speed_mmin | 2 | 7318 | 1317 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1873 | high | NELSON_R5 | machine_speed_mmin | 2 | 7459 | 1309 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1874 | high | NELSON_R5 | machine_speed_mmin | 2 | 7598 | 1330 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1875 | high | NELSON_R5 | machine_speed_mmin | 2 | 7757 | 1322 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1876 | high | NELSON_R5 | machine_speed_mmin | 2 | 7916 | 1322 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1877 | high | NELSON_R5 | machine_speed_mmin | 2 | 8029 | 1320 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1878 | high | NELSON_R5 | machine_speed_mmin | 2 | 8221 | 1324 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1879 | high | NELSON_R5 | machine_speed_mmin | 2 | 8383 | 1321 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1880 | high | NELSON_R5 | machine_speed_mmin | 2 | 8558 | 1321 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1881 | high | NELSON_R5 | machine_speed_mmin | 2 | 8636 | 1523 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1882 | high | NELSON_R5 | machine_speed_mmin | 2 | 8758 | 1310 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1883 | high | NELSON_R5 | machine_speed_mmin | 2 | 8858 | 1699 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1884 | high | NELSON_R5 | machine_speed_mmin | 2 | 8981 | 1693 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1885 | high | NELSON_R5 | machine_speed_mmin | 2 | 9149 | 1321 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1886 | high | NELSON_R5 | machine_speed_mmin | 2 | 9217 | 1479 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1887 | high | NELSON_R5 | machine_speed_mmin | 2 | 9298 | 1323 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1888 | high | NELSON_R5 | machine_speed_mmin | 2 | 9367 | 1503 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1889 | high | NELSON_R5 | machine_speed_mmin | 2 | 9495 | 1318 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1890 | high | NELSON_R5 | machine_speed_mmin | 2 | 9560 | 1519 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1891 | high | NELSON_R5 | machine_speed_mmin | 2 | 9678 | 1334 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1892 | high | NELSON_R5 | machine_speed_mmin | 2 | 9848 | 1314 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1893 | high | NELSON_R5 | machine_speed_mmin | 2 | 9919 | 1502 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1894 | high | NELSON_R5 | machine_speed_mmin | 2 | 10017 | 1322 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1895 | high | NELSON_R5 | machine_speed_mmin | 2 | 10086 | 1491 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1896 | high | NELSON_R5 | machine_speed_mmin | 2 | 10209 | 1313 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1897 | high | NELSON_R5 | machine_speed_mmin | 2 | 10280 | 1499 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1898 | high | NELSON_R5 | machine_speed_mmin | 2 | 10383 | 1700 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1899 | high | NELSON_R5 | machine_speed_mmin | 2 | 10473 | 1512 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1900 | high | NELSON_R5 | machine_speed_mmin | 2 | 10572 | 1320 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1901 | high | NELSON_R5 | machine_speed_mmin | 2 | 10745 | 1302 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1902 | high | NELSON_R5 | machine_speed_mmin | 2 | 10818 | 1516 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1903 | high | NELSON_R5 | machine_speed_mmin | 2 | 10889 | 1317 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1904 | high | NELSON_R5 | machine_speed_mmin | 2 | 10969 | 1507 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1905 | high | NELSON_R5 | machine_speed_mmin | 2 | 11055 | 1320 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1906 | high | NELSON_R5 | machine_speed_mmin | 2 | 11244 | 1320 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1907 | high | NELSON_R5 | machine_speed_mmin | 2 | 11384 | 1327 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1908 | high | NELSON_R5 | machine_speed_mmin | 2 | 11563 | 1318 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1909 | high | NELSON_R5 | machine_speed_mmin | 2 | 11636 | 1500 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1910 | high | NELSON_R5 | machine_speed_mmin | 2 | 11723 | 1695 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1911 | high | NELSON_R5 | machine_speed_mmin | 2 | 11859 | 1306 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1912 | high | NELSON_R5 | machine_speed_mmin | 2 | 12009 | 1334 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1913 | high | NELSON_R5 | machine_speed_mmin | 2 | 12150 | 1317 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1914 | high | NELSON_R5 | machine_speed_mmin | 2 | 12212 | 1506 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1915 | high | NELSON_R5 | machine_speed_mmin | 2 | 12293 | 1292 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1916 | high | NELSON_R5 | machine_speed_mmin | 2 | 12452 | 1315 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1917 | high | NELSON_R5 | machine_speed_mmin | 2 | 12516 | 1516 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1918 | high | NELSON_R5 | machine_speed_mmin | 2 | 12582 | 1338 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1919 | high | NELSON_R5 | machine_speed_mmin | 2 | 12662 | 1507 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1920 | high | NELSON_R5 | machine_speed_mmin | 2 | 12759 | 1314 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1921 | high | NELSON_R5 | machine_speed_mmin | 2 | 12827 | 1515 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1922 | high | NELSON_R5 | machine_speed_mmin | 2 | 12965 | 1322 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1923 | high | NELSON_R5 | machine_speed_mmin | 2 | 13107 | 1332 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1924 | high | NELSON_R5 | machine_speed_mmin | 2 | 13172 | 1500 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1925 | high | NELSON_R5 | machine_speed_mmin | 2 | 13267 | 1325 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1926 | high | NELSON_R5 | machine_speed_mmin | 2 | 13339 | 1494 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1927 | high | NELSON_R5 | machine_speed_mmin | 2 | 13430 | 1319 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1928 | high | NELSON_R5 | machine_speed_mmin | 2 | 13537 | 1320 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1929 | high | NELSON_R5 | machine_speed_mmin | 2 | 13666 | 1314 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1930 | high | NELSON_R5 | machine_speed_mmin | 2 | 13728 | 1514 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1931 | high | NELSON_R5 | machine_speed_mmin | 2 | 13852 | 1322 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1932 | high | NELSON_R5 | machine_speed_mmin | 2 | 14023 | 1353 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1933 | high | NELSON_R5 | machine_speed_mmin | 2 | 14161 | 1342 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1934 | high | NELSON_R5 | machine_speed_mmin | 2 | 14237 | 1510 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1935 | high | NELSON_R5 | machine_speed_mmin | 2 | 14333 | 1312 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1936 | high | NELSON_R5 | machine_speed_mmin | 2 | 14498 | 1346 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1937 | high | NELSON_R5 | machine_speed_mmin | 2 | 14674 | 1310 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1938 | high | NELSON_R5 | machine_speed_mmin | 2 | 14848 | 1327 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1939 | high | NELSON_R5 | machine_speed_mmin | 2 | 15023 | 1324 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1940 | high | NELSON_R5 | machine_speed_mmin | 2 | 15187 | 1323 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1941 | high | NELSON_R5 | machine_speed_mmin | 2 | 15261 | 1508 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1942 | high | NELSON_R5 | machine_speed_mmin | 2 | 15324 | 1699 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1943 | high | NELSON_R5 | machine_speed_mmin | 2 | 15498 | 1320 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1944 | high | NELSON_R5 | machine_speed_mmin | 2 | 15633 | 1313 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1945 | high | NELSON_R5 | machine_speed_mmin | 2 | 15702 | 1515 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1946 | high | NELSON_R5 | machine_speed_mmin | 2 | 15832 | 1320 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1947 | high | NELSON_R5 | machine_speed_mmin | 2 | 15991 | 1315 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1948 | high | NELSON_R5 | machine_speed_mmin | 2 | 16058 | 1509 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1949 | high | NELSON_R5 | machine_speed_mmin | 2 | 16162 | 1326 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1950 | high | NELSON_R5 | machine_speed_mmin | 2 | 16224 | 1520 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1951 | high | NELSON_R5 | machine_speed_mmin | 2 | 16366 | 1324 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1952 | high | NELSON_R5 | machine_speed_mmin | 2 | 16550 | 1288 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1953 | high | NELSON_R5 | machine_speed_mmin | 2 | 16620 | 1512 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1954 | high | NELSON_R5 | machine_speed_mmin | 2 | 16684 | 1352 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1955 | high | NELSON_R5 | machine_speed_mmin | 2 | 16883 | 1611 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1956 | high | NELSON_R5 | machine_speed_mmin | 2 | 17015 | 1326 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1957 | high | NELSON_R5 | machine_speed_mmin | 2 | 17232 | 1321 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1958 | high | NELSON_R5 | machine_speed_mmin | 2 | 17375 | 1321 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1959 | high | NELSON_R5 | machine_speed_mmin | 2 | 17541 | 1319 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1960 | high | NELSON_R5 | machine_speed_mmin | 2 | 17613 | 1519 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1961 | high | NELSON_R5 | machine_speed_mmin | 2 | 17706 | 1689 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1962 | high | NELSON_R5 | machine_speed_mmin | 2 | 17809 | 1528 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1963 | high | NELSON_R5 | machine_speed_mmin | 2 | 17943 | 1308 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1964 | high | NELSON_R5 | machine_speed_mmin | 2 | 18062 | 1326 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1965 | high | NELSON_R5 | machine_speed_mmin | 2 | 18133 | 1515 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1966 | high | NELSON_R5 | machine_speed_mmin | 2 | 18233 | 1325 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1967 | high | NELSON_R5 | machine_speed_mmin | 2 | 18396 | 1338 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1968 | high | NELSON_R5 | machine_speed_mmin | 2 | 18549 | 1305 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1969 | high | NELSON_R5 | machine_speed_mmin | 2 | 18615 | 1489 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1970 | high | NELSON_R5 | machine_speed_mmin | 2 | 18740 | 1328 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1971 | high | NELSON_R5 | machine_speed_mmin | 2 | 18902 | 1316 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1972 | high | NELSON_R5 | machine_speed_mmin | 2 | 19009 | 1319 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1973 | high | NELSON_R5 | machine_speed_mmin | 2 | 19178 | 1306 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1974 | high | NELSON_R5 | machine_speed_mmin | 2 | 19420 | 1332 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1975 | high | NELSON_R5 | machine_speed_mmin | 2 | 19580 | 1291 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1976 | high | NELSON_R5 | machine_speed_mmin | 2 | 19748 | 1323 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1977 | high | NELSON_R5 | machine_speed_mmin | 2 | 19951 | 1309 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1978 | high | NELSON_R5 | machine_speed_mmin | 2 | 20084 | 1313 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1979 | high | NELSON_R5 | machine_speed_mmin | 2 | 20256 | 1325 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1980 | high | NELSON_R5 | machine_speed_mmin | 2 | 20410 | 1323 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1981 | high | NELSON_R5 | machine_speed_mmin | 2 | 20519 | 1315 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1982 | high | NELSON_R5 | machine_speed_mmin | 2 | 20630 | 1323 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1983 | high | NELSON_R5 | machine_speed_mmin | 2 | 20760 | 1338 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1984 | high | NELSON_R5 | machine_speed_mmin | 2 | 20827 | 1511 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1985 | high | NELSON_R5 | machine_speed_mmin | 2 | 20935 | 1322 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1986 | high | NELSON_R5 | machine_speed_mmin | 2 | 21029 | 1332 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1987 | high | NELSON_R5 | machine_speed_mmin | 2 | 21136 | 1330 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1988 | high | NELSON_R5 | machine_speed_mmin | 2 | 21255 | 1332 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1989 | high | NELSON_R5 | machine_speed_mmin | 2 | 21409 | 1304 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1990 | high | NELSON_R5 | machine_speed_mmin | 2 | 21472 | 1505 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1991 | high | NELSON_R5 | machine_speed_mmin | 2 | 21568 | 1319 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1992 | high | NELSON_R5 | machine_speed_mmin | 2 | 21629 | 1510 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1993 | high | NELSON_R5 | machine_speed_mmin | 2 | 21733 | 1310 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1994 | high | NELSON_R5 | machine_speed_mmin | 2 | 21795 | 1504 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1995 | high | NELSON_R5 | machine_speed_mmin | 2 | 21864 | 1322 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1996 | high | NELSON_R5 | machine_speed_mmin | 2 | 21926 | 1506 | machine_speed_mmin 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1997 | high | NELSON_R5 | stock_temp_C | 2 | 19 | 50.1 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1998 | high | NELSON_R5 | stock_temp_C | 2 | 364 | 50.6 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 1999 | high | NELSON_R5 | stock_temp_C | 2 | 583 | 40.9 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2000 | high | NELSON_R5 | stock_temp_C | 2 | 714 | 49.9 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2001 | high | NELSON_R5 | stock_temp_C | 2 | 1078 | 50.3 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2002 | high | NELSON_R5 | stock_temp_C | 2 | 1491 | 50.5 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2003 | high | NELSON_R5 | stock_temp_C | 2 | 1653 | 41.7 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2004 | high | NELSON_R5 | stock_temp_C | 2 | 1827 | 51 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2005 | high | NELSON_R5 | stock_temp_C | 2 | 2044 | 43.2 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2006 | high | NELSON_R5 | stock_temp_C | 2 | 2362 | 42.1 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2007 | high | NELSON_R5 | stock_temp_C | 2 | 2738 | 43.1 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2008 | high | NELSON_R5 | stock_temp_C | 2 | 3094 | 44.2 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2009 | high | NELSON_R5 | stock_temp_C | 2 | 3413 | 44.4 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2010 | high | NELSON_R5 | stock_temp_C | 2 | 3530 | 43.1 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2011 | high | NELSON_R5 | stock_temp_C | 2 | 3808 | 43.4 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2012 | high | NELSON_R5 | stock_temp_C | 2 | 3888 | 43.4 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2013 | high | NELSON_R5 | stock_temp_C | 2 | 4156 | 43.7 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2014 | high | NELSON_R5 | stock_temp_C | 2 | 4275 | 42.5 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2015 | high | NELSON_R5 | stock_temp_C | 2 | 4482 | 44.2 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2016 | high | NELSON_R5 | stock_temp_C | 2 | 4621 | 43.3 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2017 | high | NELSON_R5 | stock_temp_C | 2 | 4855 | 44.8 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2018 | high | NELSON_R5 | stock_temp_C | 2 | 5006 | 39.2 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2019 | high | NELSON_R5 | stock_temp_C | 2 | 5207 | 43.9 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2020 | high | NELSON_R5 | stock_temp_C | 2 | 5291 | 40.7 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2021 | high | NELSON_R5 | stock_temp_C | 2 | 5584 | 44.5 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2022 | high | NELSON_R5 | stock_temp_C | 2 | 5756 | 43.4 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2023 | high | NELSON_R5 | stock_temp_C | 2 | 5924 | 44 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2024 | high | NELSON_R5 | stock_temp_C | 2 | 6116 | 43.5 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2025 | high | NELSON_R5 | stock_temp_C | 2 | 6249 | 42.9 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2026 | high | NELSON_R5 | stock_temp_C | 2 | 6494 | 43.6 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2027 | high | NELSON_R5 | stock_temp_C | 2 | 6647 | 43.5 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2028 | high | NELSON_R5 | stock_temp_C | 2 | 6875 | 43.5 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2029 | high | NELSON_R5 | stock_temp_C | 2 | 6965 | 43.9 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2030 | high | NELSON_R5 | stock_temp_C | 2 | 7257 | 43.4 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2031 | high | NELSON_R5 | stock_temp_C | 2 | 7605 | 40.5 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2032 | high | NELSON_R5 | stock_temp_C | 2 | 7979 | 43.4 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2033 | high | NELSON_R5 | stock_temp_C | 2 | 8169 | 38.1 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2034 | high | NELSON_R5 | stock_temp_C | 2 | 8342 | 43.3 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2035 | high | NELSON_R5 | stock_temp_C | 2 | 8759 | 42.9 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2036 | high | NELSON_R5 | stock_temp_C | 2 | 9107 | 44.1 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2037 | high | NELSON_R5 | stock_temp_C | 2 | 9211 | 43.7 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2038 | high | NELSON_R5 | stock_temp_C | 2 | 9522 | 43.6 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2039 | high | NELSON_R5 | stock_temp_C | 2 | 9995 | 38.5 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2040 | high | NELSON_R5 | stock_temp_C | 2 | 11507 | 36.5 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2041 | high | NELSON_R5 | stock_temp_C | 2 | 12569 | 36.7 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2042 | high | NELSON_R5 | stock_temp_C | 2 | 15003 | 40.8 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2043 | high | NELSON_R5 | stock_temp_C | 2 | 15667 | 41.3 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2044 | high | NELSON_R5 | stock_temp_C | 2 | 17229 | 40.1 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2045 | high | NELSON_R5 | stock_temp_C | 2 | 17541 | 44.1 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2046 | high | NELSON_R5 | stock_temp_C | 2 | 17852 | 43.9 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2047 | high | NELSON_R5 | stock_temp_C | 2 | 18204 | 40.3 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2048 | high | NELSON_R5 | stock_temp_C | 2 | 18555 | 42.8 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2049 | high | NELSON_R5 | stock_temp_C | 2 | 18888 | 43.5 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2050 | high | NELSON_R5 | stock_temp_C | 2 | 18963 | 43.3 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2051 | high | NELSON_R5 | stock_temp_C | 2 | 19205 | 43.8 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2052 | high | NELSON_R5 | stock_temp_C | 2 | 19313 | 43.4 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2053 | high | NELSON_R5 | stock_temp_C | 2 | 19548 | 45.7 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2054 | high | NELSON_R5 | stock_temp_C | 2 | 19671 | 43.3 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2055 | high | NELSON_R5 | stock_temp_C | 2 | 19838 | 39.4 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2056 | high | NELSON_R5 | stock_temp_C | 2 | 19912 | 43.7 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2057 | high | NELSON_R5 | stock_temp_C | 2 | 20023 | 44 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2058 | high | NELSON_R5 | stock_temp_C | 2 | 20239 | 43.3 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2059 | high | NELSON_R5 | stock_temp_C | 2 | 20389 | 42.8 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2060 | high | NELSON_R5 | stock_temp_C | 2 | 20545 | 41.1 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2061 | high | NELSON_R5 | stock_temp_C | 2 | 20737 | 43 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2062 | high | NELSON_R5 | stock_temp_C | 2 | 20926 | 43.1 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2063 | high | NELSON_R5 | stock_temp_C | 2 | 21097 | 43.6 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2064 | high | NELSON_R5 | stock_temp_C | 2 | 21171 | 36.8 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2065 | high | NELSON_R5 | stock_temp_C | 2 | 21258 | 42.5 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2066 | high | NELSON_R5 | stock_temp_C | 2 | 21476 | 43.3 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2067 | high | NELSON_R5 | stock_temp_C | 2 | 21578 | 40.9 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2068 | high | NELSON_R5 | stock_temp_C | 2 | 21962 | 43.5 | stock_temp_C 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2069 | high | NELSON_R5 | vacuum_pump1_kPa | 2 | 274 | 41.4 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2070 | high | NELSON_R5 | vacuum_pump1_kPa | 2 | 591 | 40 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2071 | high | NELSON_R5 | vacuum_pump1_kPa | 2 | 2077 | 36.1 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2072 | high | NELSON_R5 | vacuum_pump1_kPa | 2 | 2154 | 54.8 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2073 | high | NELSON_R5 | vacuum_pump1_kPa | 2 | 2524 | 52.6 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2074 | high | NELSON_R5 | vacuum_pump1_kPa | 2 | 3181 | 48.6 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2075 | high | NELSON_R5 | vacuum_pump1_kPa | 2 | 4623 | 59.5 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2076 | high | NELSON_R5 | vacuum_pump1_kPa | 2 | 4931 | 52.1 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2077 | high | NELSON_R5 | vacuum_pump1_kPa | 2 | 5357 | 54.6 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2078 | high | NELSON_R5 | vacuum_pump1_kPa | 2 | 5834 | 54.5 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2079 | high | NELSON_R5 | vacuum_pump1_kPa | 2 | 6648 | 49.5 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2080 | high | NELSON_R5 | vacuum_pump1_kPa | 2 | 7182 | 44.6 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2081 | high | NELSON_R5 | vacuum_pump1_kPa | 2 | 7244 | 64 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2082 | high | NELSON_R5 | vacuum_pump1_kPa | 2 | 7692 | 43.6 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2083 | high | NELSON_R5 | vacuum_pump1_kPa | 2 | 8370 | 57.5 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2084 | high | NELSON_R5 | vacuum_pump1_kPa | 2 | 8598 | 41.7 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2085 | high | NELSON_R5 | vacuum_pump1_kPa | 2 | 8999 | 61 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2086 | high | NELSON_R5 | vacuum_pump1_kPa | 2 | 9299 | 62.8 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2087 | high | NELSON_R5 | vacuum_pump1_kPa | 2 | 9653 | 54.2 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2088 | high | NELSON_R5 | vacuum_pump1_kPa | 2 | 10062 | 48.3 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2089 | high | NELSON_R5 | vacuum_pump1_kPa | 2 | 10397 | 45.3 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2090 | high | NELSON_R5 | vacuum_pump1_kPa | 2 | 11693 | 53.1 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2091 | high | NELSON_R5 | vacuum_pump1_kPa | 2 | 12771 | 41.8 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2092 | high | NELSON_R5 | vacuum_pump1_kPa | 2 | 13212 | 46.2 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2093 | high | NELSON_R5 | vacuum_pump1_kPa | 2 | 14364 | 65.8 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2094 | high | NELSON_R5 | vacuum_pump1_kPa | 2 | 15155 | 36.1 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2095 | high | NELSON_R5 | vacuum_pump1_kPa | 2 | 15738 | 48.7 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2096 | high | NELSON_R5 | vacuum_pump1_kPa | 2 | 16085 | 65.1 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2097 | high | NELSON_R5 | vacuum_pump1_kPa | 2 | 16375 | 49.1 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2098 | high | NELSON_R5 | vacuum_pump1_kPa | 2 | 17026 | 65.9 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2099 | high | NELSON_R5 | vacuum_pump1_kPa | 2 | 17144 | 48.9 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2100 | high | NELSON_R5 | vacuum_pump1_kPa | 2 | 17823 | 41.5 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2101 | high | NELSON_R5 | vacuum_pump1_kPa | 2 | 17983 | 47.2 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2102 | high | NELSON_R5 | vacuum_pump1_kPa | 2 | 18131 | 65.2 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2103 | high | NELSON_R5 | vacuum_pump1_kPa | 2 | 19200 | 57 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2104 | high | NELSON_R5 | vacuum_pump1_kPa | 2 | 20235 | 54.2 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2105 | high | NELSON_R5 | vacuum_pump1_kPa | 2 | 20947 | 55.6 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2106 | high | NELSON_R5 | vacuum_pump1_kPa | 2 | 21587 | 50.8 | vacuum_pump1_kPa 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2107 | high | NELSON_R5 | white_water_consistency_pct | 2 | 40 | 0.977 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2108 | high | NELSON_R5 | white_water_consistency_pct | 2 | 633 | 1.058 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2109 | high | NELSON_R5 | white_water_consistency_pct | 2 | 961 | 1.001 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2110 | high | NELSON_R5 | white_water_consistency_pct | 2 | 5103 | 1.025 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2111 | high | NELSON_R5 | white_water_consistency_pct | 2 | 5842 | 1.011 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2112 | high | NELSON_R5 | white_water_consistency_pct | 2 | 6052 | 0.959 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2113 | high | NELSON_R5 | white_water_consistency_pct | 2 | 6329 | 0.983 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2114 | high | NELSON_R5 | white_water_consistency_pct | 2 | 6416 | 1.025 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2115 | high | NELSON_R5 | white_water_consistency_pct | 2 | 6562 | 1.026 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2116 | high | NELSON_R5 | white_water_consistency_pct | 2 | 6632 | 0.986 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2117 | high | NELSON_R5 | white_water_consistency_pct | 2 | 6934 | 1.036 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2118 | high | NELSON_R5 | white_water_consistency_pct | 2 | 7025 | 1.014 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2119 | high | NELSON_R5 | white_water_consistency_pct | 2 | 7225 | 0.947 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2120 | high | NELSON_R5 | white_water_consistency_pct | 2 | 7302 | 1.324 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2121 | high | NELSON_R5 | white_water_consistency_pct | 2 | 7401 | 1.025 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2122 | high | NELSON_R5 | white_water_consistency_pct | 2 | 7516 | 1.125 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2123 | high | NELSON_R5 | white_water_consistency_pct | 2 | 7728 | 0.95 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2124 | high | NELSON_R5 | white_water_consistency_pct | 2 | 8051 | 1.035 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2125 | high | NELSON_R5 | white_water_consistency_pct | 2 | 8132 | 0.3 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2126 | high | NELSON_R5 | white_water_consistency_pct | 2 | 8291 | 1.036 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2127 | high | NELSON_R5 | white_water_consistency_pct | 2 | 8551 | 1.029 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2128 | high | NELSON_R5 | white_water_consistency_pct | 2 | 8720 | 0.962 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2129 | high | NELSON_R5 | white_water_consistency_pct | 2 | 8873 | 0.876 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2130 | high | NELSON_R5 | white_water_consistency_pct | 2 | 9014 | 0.927 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2131 | high | NELSON_R5 | white_water_consistency_pct | 2 | 9545 | 1.035 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2132 | high | NELSON_R5 | white_water_consistency_pct | 2 | 9930 | 1.034 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2133 | high | NELSON_R5 | white_water_consistency_pct | 2 | 10155 | 1.028 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2134 | high | NELSON_R5 | white_water_consistency_pct | 2 | 10318 | 0.997 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2135 | high | NELSON_R5 | white_water_consistency_pct | 2 | 10517 | 1.005 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2136 | high | NELSON_R5 | white_water_consistency_pct | 2 | 10725 | 1.083 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2137 | high | NELSON_R5 | white_water_consistency_pct | 2 | 12968 | 1.061 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2138 | high | NELSON_R5 | white_water_consistency_pct | 2 | 13425 | 0.933 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2139 | high | NELSON_R5 | white_water_consistency_pct | 2 | 13575 | 0.891 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2140 | high | NELSON_R5 | white_water_consistency_pct | 2 | 13938 | 1.012 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2141 | high | NELSON_R5 | white_water_consistency_pct | 2 | 14154 | 0.884 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2142 | high | NELSON_R5 | white_water_consistency_pct | 2 | 14240 | 0.968 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2143 | high | NELSON_R5 | white_water_consistency_pct | 2 | 14379 | 1.018 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2144 | high | NELSON_R5 | white_water_consistency_pct | 2 | 14514 | 1.034 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2145 | high | NELSON_R5 | white_water_consistency_pct | 2 | 14678 | 0.845 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2146 | high | NELSON_R5 | white_water_consistency_pct | 2 | 14773 | 0.893 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2147 | high | NELSON_R5 | white_water_consistency_pct | 2 | 14954 | 1.031 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2148 | high | NELSON_R5 | white_water_consistency_pct | 2 | 15143 | 0.98 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2149 | high | NELSON_R5 | white_water_consistency_pct | 2 | 15460 | 0.957 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2150 | high | NELSON_R5 | white_water_consistency_pct | 2 | 15654 | 0.931 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2151 | high | NELSON_R5 | white_water_consistency_pct | 2 | 15719 | 0.998 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2152 | high | NELSON_R5 | white_water_consistency_pct | 2 | 16367 | 1.005 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2153 | high | NELSON_R5 | white_water_consistency_pct | 2 | 16432 | 1.033 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2154 | high | NELSON_R5 | white_water_consistency_pct | 2 | 17113 | 1.01 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2155 | high | NELSON_R5 | white_water_consistency_pct | 2 | 17276 | 1.011 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2156 | high | NELSON_R5 | white_water_consistency_pct | 2 | 17474 | 1.019 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2157 | high | NELSON_R5 | white_water_consistency_pct | 2 | 18104 | 1.006 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2158 | high | NELSON_R5 | white_water_consistency_pct | 2 | 18677 | 0.885 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2159 | high | NELSON_R5 | white_water_consistency_pct | 2 | 21987 | 1.213 | white_water_consistency_pct 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 2160 | high | NELSON_R6 | fan_pump_speed_rpm | 1 | 5 | 899.4 | fan_pump_speed_rpm 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2161 | high | NELSON_R6 | fan_pump_speed_rpm | 1 | 568 | 889.7 | fan_pump_speed_rpm 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2162 | high | NELSON_R6 | fan_pump_speed_rpm | 1 | 914 | 886.5 | fan_pump_speed_rpm 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2163 | high | NELSON_R6 | fan_pump_speed_rpm | 1 | 1007 | 889.8 | fan_pump_speed_rpm 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2164 | high | NELSON_R6 | fan_pump_speed_rpm | 1 | 1125 | 894 | fan_pump_speed_rpm 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2165 | high | NELSON_R6 | fan_pump_speed_rpm | 1 | 1197 | 897.3 | fan_pump_speed_rpm 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2166 | high | NELSON_R6 | fan_pump_speed_rpm | 1 | 1409 | 889.1 | fan_pump_speed_rpm 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2167 | high | NELSON_R6 | fan_pump_speed_rpm | 1 | 1530 | 889.4 | fan_pump_speed_rpm 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2168 | high | NELSON_R6 | fan_pump_speed_rpm | 1 | 1608 | 890.1 | fan_pump_speed_rpm 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2169 | high | NELSON_R6 | fan_pump_speed_rpm | 1 | 1670 | 904.1 | fan_pump_speed_rpm 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2170 | high | NELSON_R6 | fan_pump_speed_rpm | 1 | 1950 | 904.2 | fan_pump_speed_rpm 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2171 | high | NELSON_R6 | fan_pump_speed_rpm | 1 | 21860 | 938.2 | fan_pump_speed_rpm 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2172 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 26 | 18.21 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2173 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 155 | 17.28 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2174 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 293 | 18.09 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2175 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 467 | 18.27 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2176 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 556 | 20.71 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2177 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 784 | 17.89 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2178 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 963 | 18.17 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2179 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 1084 | 17.95 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2180 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 1192 | 21.29 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2181 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 1407 | 24.93 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2182 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 1581 | 18.43 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2183 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 1724 | 18.8 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2184 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 1843 | 19.35 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2185 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 2019 | 25.87 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2186 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 2189 | 25.91 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2187 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 2373 | 25.9 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2188 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 2566 | 19.6 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2189 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 2707 | 19.38 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2190 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 2827 | 23.03 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2191 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 2902 | 19.51 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2192 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 3037 | 19.45 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2193 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 3192 | 19.66 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2194 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 4335 | 20.92 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2195 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 4415 | 28.43 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2196 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 4519 | 28.63 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2197 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 4766 | 24.97 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2198 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 5180 | 25.2 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2199 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 5347 | 25.47 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2200 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 5525 | 25.73 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2201 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 5589 | 29.65 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2202 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 6305 | 26.01 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2203 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 6658 | 22.35 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2204 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 7019 | 27.27 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2205 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 7269 | 27.45 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2206 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 7397 | 23.05 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2207 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 8252 | 32.71 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2208 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 9298 | 26.34 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2209 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 9574 | 33.71 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2210 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 10290 | 22.89 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2211 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 10651 | 25.21 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2212 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 10890 | 27.96 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2213 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 11218 | 27.08 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2214 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 11455 | 20.12 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2215 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 11617 | 23.37 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2216 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 12430 | 21.87 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2217 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 12760 | 29.47 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2218 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 13114 | 22.2 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2219 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 13526 | 30.19 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2220 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 13715 | 22.48 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2221 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 14401 | 23.36 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2222 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 14918 | 23.65 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2223 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 15240 | 27.49 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2224 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 15312 | 23.69 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2225 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 15389 | 26.94 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2226 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 15454 | 27.45 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2227 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 16332 | 32.32 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2228 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 17237 | 25.07 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2229 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 17450 | 25.48 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2230 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 17691 | 29.98 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2231 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 17942 | 25.96 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2232 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 18029 | 34.31 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2233 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 18634 | 26.08 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2234 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 18947 | 26.35 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2235 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 19442 | 31.43 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2236 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 19989 | 37.8 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2237 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 20086 | 27.79 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2238 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 20246 | 27.83 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2239 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 20398 | 38.08 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2240 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 21616 | 29.16 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2241 | high | NELSON_R6 | headbox_pressure_kPa | 1 | 21860 | 35.05 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2242 | high | NELSON_R6 | jet_to_wire_ratio | 1 | 307 | 0.966 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2243 | high | NELSON_R6 | jet_to_wire_ratio | 1 | 557 | 1.058 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2244 | high | NELSON_R6 | jet_to_wire_ratio | 1 | 768 | 1.054 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2245 | high | NELSON_R6 | jet_to_wire_ratio | 1 | 1056 | 0.976 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2246 | high | NELSON_R6 | jet_to_wire_ratio | 1 | 2368 | 1.043 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2247 | high | NELSON_R6 | jet_to_wire_ratio | 1 | 3504 | 0.967 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2248 | high | NELSON_R6 | jet_to_wire_ratio | 1 | 3788 | 0.968 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2249 | high | NELSON_R6 | jet_to_wire_ratio | 1 | 4528 | 1.056 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2250 | high | NELSON_R6 | jet_to_wire_ratio | 1 | 5125 | 0.989 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2251 | high | NELSON_R6 | jet_to_wire_ratio | 1 | 5502 | 0.974 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2252 | high | NELSON_R6 | jet_to_wire_ratio | 1 | 5737 | 1.048 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2253 | high | NELSON_R6 | jet_to_wire_ratio | 1 | 6074 | 0.98 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2254 | high | NELSON_R6 | jet_to_wire_ratio | 1 | 6369 | 1.062 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2255 | high | NELSON_R6 | jet_to_wire_ratio | 1 | 6834 | 0.974 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2256 | high | NELSON_R6 | jet_to_wire_ratio | 1 | 6979 | 1.028 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2257 | high | NELSON_R6 | jet_to_wire_ratio | 1 | 7067 | 1.053 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2258 | high | NELSON_R6 | jet_to_wire_ratio | 1 | 7604 | 1.034 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2259 | high | NELSON_R6 | jet_to_wire_ratio | 1 | 7968 | 0.988 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2260 | high | NELSON_R6 | jet_to_wire_ratio | 1 | 8318 | 0.984 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2261 | high | NELSON_R6 | jet_to_wire_ratio | 1 | 8405 | 1.061 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2262 | high | NELSON_R6 | jet_to_wire_ratio | 1 | 8836 | 0.976 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2263 | high | NELSON_R6 | jet_to_wire_ratio | 1 | 9231 | 0.976 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2264 | high | NELSON_R6 | jet_to_wire_ratio | 1 | 9564 | 0.954 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2265 | high | NELSON_R6 | jet_to_wire_ratio | 1 | 9789 | 1.032 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2266 | high | NELSON_R6 | jet_to_wire_ratio | 1 | 9885 | 0.986 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2267 | high | NELSON_R6 | jet_to_wire_ratio | 1 | 10597 | 1.058 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2268 | high | NELSON_R6 | jet_to_wire_ratio | 1 | 10885 | 0.961 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2269 | high | NELSON_R6 | jet_to_wire_ratio | 1 | 11231 | 1.075 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2270 | high | NELSON_R6 | jet_to_wire_ratio | 1 | 11386 | 0.975 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2271 | high | NELSON_R6 | jet_to_wire_ratio | 1 | 11750 | 0.964 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2272 | high | NELSON_R6 | jet_to_wire_ratio | 1 | 12238 | 1.058 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2273 | high | NELSON_R6 | jet_to_wire_ratio | 1 | 12374 | 1.062 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2274 | high | NELSON_R6 | jet_to_wire_ratio | 1 | 12598 | 1.02 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2275 | high | NELSON_R6 | jet_to_wire_ratio | 1 | 13279 | 1.063 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2276 | high | NELSON_R6 | jet_to_wire_ratio | 1 | 13541 | 0.966 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2277 | high | NELSON_R6 | jet_to_wire_ratio | 1 | 13771 | 0.971 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2278 | high | NELSON_R6 | jet_to_wire_ratio | 1 | 13889 | 0.987 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2279 | high | NELSON_R6 | jet_to_wire_ratio | 1 | 14042 | 1.061 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2280 | high | NELSON_R6 | jet_to_wire_ratio | 1 | 14218 | 0.976 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2281 | high | NELSON_R6 | jet_to_wire_ratio | 1 | 14346 | 1.056 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2282 | high | NELSON_R6 | jet_to_wire_ratio | 1 | 14988 | 0.988 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2283 | high | NELSON_R6 | jet_to_wire_ratio | 1 | 15184 | 1.064 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2284 | high | NELSON_R6 | jet_to_wire_ratio | 1 | 15627 | 0.943 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2285 | high | NELSON_R6 | jet_to_wire_ratio | 1 | 16058 | 1.068 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2286 | high | NELSON_R6 | jet_to_wire_ratio | 1 | 16326 | 1.057 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2287 | high | NELSON_R6 | jet_to_wire_ratio | 1 | 16404 | 1.005 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2288 | high | NELSON_R6 | jet_to_wire_ratio | 1 | 16598 | 0.982 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2289 | high | NELSON_R6 | jet_to_wire_ratio | 1 | 17020 | 1.012 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2290 | high | NELSON_R6 | jet_to_wire_ratio | 1 | 17223 | 1.036 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2291 | high | NELSON_R6 | jet_to_wire_ratio | 1 | 17581 | 1.045 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2292 | high | NELSON_R6 | jet_to_wire_ratio | 1 | 18570 | 0.964 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2293 | high | NELSON_R6 | jet_to_wire_ratio | 1 | 18650 | 1.061 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2294 | high | NELSON_R6 | jet_to_wire_ratio | 1 | 19869 | 0.987 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2295 | high | NELSON_R6 | jet_to_wire_ratio | 1 | 20439 | 1.057 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2296 | high | NELSON_R6 | jet_to_wire_ratio | 1 | 20632 | 1.01 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2297 | high | NELSON_R6 | jet_to_wire_ratio | 1 | 20694 | 0.97 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2298 | high | NELSON_R6 | jet_to_wire_ratio | 1 | 21272 | 1.057 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2299 | high | NELSON_R6 | machine_speed_mmin | 1 | 26 | 1303 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2300 | high | NELSON_R6 | machine_speed_mmin | 1 | 88 | 1518 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2301 | high | NELSON_R6 | machine_speed_mmin | 1 | 155 | 1324 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2302 | high | NELSON_R6 | machine_speed_mmin | 1 | 221 | 1513 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2303 | high | NELSON_R6 | machine_speed_mmin | 1 | 293 | 1315 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2304 | high | NELSON_R6 | machine_speed_mmin | 1 | 467 | 1319 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2305 | high | NELSON_R6 | machine_speed_mmin | 1 | 612 | 1319 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2306 | high | NELSON_R6 | machine_speed_mmin | 1 | 784 | 1313 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2307 | high | NELSON_R6 | machine_speed_mmin | 1 | 846 | 1512 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2308 | high | NELSON_R6 | machine_speed_mmin | 1 | 963 | 1322 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2309 | high | NELSON_R6 | machine_speed_mmin | 1 | 1084 | 1320 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2310 | high | NELSON_R6 | machine_speed_mmin | 1 | 1234 | 1326 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2311 | high | NELSON_R6 | machine_speed_mmin | 1 | 1301 | 1506 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2312 | high | NELSON_R6 | machine_speed_mmin | 1 | 1423 | 1323 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2313 | high | NELSON_R6 | machine_speed_mmin | 1 | 1581 | 1316 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2314 | high | NELSON_R6 | machine_speed_mmin | 1 | 1724 | 1325 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2315 | high | NELSON_R6 | machine_speed_mmin | 1 | 1843 | 1318 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2316 | high | NELSON_R6 | machine_speed_mmin | 1 | 1919 | 1516 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2317 | high | NELSON_R6 | machine_speed_mmin | 1 | 2042 | 1705 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2318 | high | NELSON_R6 | machine_speed_mmin | 1 | 2203 | 1332 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2319 | high | NELSON_R6 | machine_speed_mmin | 1 | 2405 | 1316 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2320 | high | NELSON_R6 | machine_speed_mmin | 1 | 2474 | 1514 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2321 | high | NELSON_R6 | machine_speed_mmin | 1 | 2556 | 1322 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2322 | high | NELSON_R6 | machine_speed_mmin | 1 | 2620 | 1504 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2323 | high | NELSON_R6 | machine_speed_mmin | 1 | 2700 | 1308 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2324 | high | NELSON_R6 | machine_speed_mmin | 1 | 2763 | 1508 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2325 | high | NELSON_R6 | machine_speed_mmin | 1 | 2886 | 1317 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2326 | high | NELSON_R6 | machine_speed_mmin | 1 | 3025 | 1330 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2327 | high | NELSON_R6 | machine_speed_mmin | 1 | 3094 | 1522 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2328 | high | NELSON_R6 | machine_speed_mmin | 1 | 3182 | 1322 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2329 | high | NELSON_R6 | machine_speed_mmin | 1 | 3255 | 1508 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2330 | high | NELSON_R6 | machine_speed_mmin | 1 | 3392 | 1340 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2331 | high | NELSON_R6 | machine_speed_mmin | 1 | 3530 | 1335 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2332 | high | NELSON_R6 | machine_speed_mmin | 1 | 3596 | 1508 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2333 | high | NELSON_R6 | machine_speed_mmin | 1 | 3730 | 1324 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2334 | high | NELSON_R6 | machine_speed_mmin | 1 | 3805 | 1529 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2335 | high | NELSON_R6 | machine_speed_mmin | 1 | 3867 | 1699 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2336 | high | NELSON_R6 | machine_speed_mmin | 1 | 3974 | 1533 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2337 | high | NELSON_R6 | machine_speed_mmin | 1 | 4096 | 1319 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2338 | high | NELSON_R6 | machine_speed_mmin | 1 | 4285 | 1332 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2339 | high | NELSON_R6 | machine_speed_mmin | 1 | 4429 | 1339 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2340 | high | NELSON_R6 | machine_speed_mmin | 1 | 4568 | 1324 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2341 | high | NELSON_R6 | machine_speed_mmin | 1 | 4687 | 1323 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2342 | high | NELSON_R6 | machine_speed_mmin | 1 | 4837 | 1335 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2343 | high | NELSON_R6 | machine_speed_mmin | 1 | 4981 | 1318 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2344 | high | NELSON_R6 | machine_speed_mmin | 1 | 5122 | 1316 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2345 | high | NELSON_R6 | machine_speed_mmin | 1 | 5265 | 1330 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2346 | high | NELSON_R6 | machine_speed_mmin | 1 | 5446 | 1320 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2347 | high | NELSON_R6 | machine_speed_mmin | 1 | 5562 | 1697 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2348 | high | NELSON_R6 | machine_speed_mmin | 1 | 5726 | 1368 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2349 | high | NELSON_R6 | machine_speed_mmin | 1 | 5893 | 1331 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2350 | high | NELSON_R6 | machine_speed_mmin | 1 | 6034 | 1316 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2351 | high | NELSON_R6 | machine_speed_mmin | 1 | 6173 | 1318 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2352 | high | NELSON_R6 | machine_speed_mmin | 1 | 6240 | 1516 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2353 | high | NELSON_R6 | machine_speed_mmin | 1 | 6338 | 1305 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2354 | high | NELSON_R6 | machine_speed_mmin | 1 | 6402 | 1470 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2355 | high | NELSON_R6 | machine_speed_mmin | 1 | 6519 | 1321 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2356 | high | NELSON_R6 | machine_speed_mmin | 1 | 6654 | 1337 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2357 | high | NELSON_R6 | machine_speed_mmin | 1 | 6793 | 1326 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2358 | high | NELSON_R6 | machine_speed_mmin | 1 | 6895 | 1320 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2359 | high | NELSON_R6 | machine_speed_mmin | 1 | 6958 | 1507 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2360 | high | NELSON_R6 | machine_speed_mmin | 1 | 7074 | 1320 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2361 | high | NELSON_R6 | machine_speed_mmin | 1 | 7196 | 1704 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2362 | high | NELSON_R6 | machine_speed_mmin | 1 | 7338 | 1322 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2363 | high | NELSON_R6 | machine_speed_mmin | 1 | 7400 | 1511 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2364 | high | NELSON_R6 | machine_speed_mmin | 1 | 7495 | 1320 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2365 | high | NELSON_R6 | machine_speed_mmin | 1 | 7650 | 1323 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2366 | high | NELSON_R6 | machine_speed_mmin | 1 | 7716 | 1510 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2367 | high | NELSON_R6 | machine_speed_mmin | 1 | 7821 | 1317 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2368 | high | NELSON_R6 | machine_speed_mmin | 1 | 7953 | 1293 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2369 | high | NELSON_R6 | machine_speed_mmin | 1 | 8128 | 1311 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2370 | high | NELSON_R6 | machine_speed_mmin | 1 | 8278 | 1327 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2371 | high | NELSON_R6 | machine_speed_mmin | 1 | 8450 | 1330 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2372 | high | NELSON_R6 | machine_speed_mmin | 1 | 8518 | 1515 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2373 | high | NELSON_R6 | machine_speed_mmin | 1 | 8614 | 1319 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2374 | high | NELSON_R6 | machine_speed_mmin | 1 | 8826 | 1350 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2375 | high | NELSON_R6 | machine_speed_mmin | 1 | 8960 | 1308 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2376 | high | NELSON_R6 | machine_speed_mmin | 1 | 9025 | 1513 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2377 | high | NELSON_R6 | machine_speed_mmin | 1 | 9099 | 1342 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2378 | high | NELSON_R6 | machine_speed_mmin | 1 | 9278 | 1320 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2379 | high | NELSON_R6 | machine_speed_mmin | 1 | 9339 | 1509 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2380 | high | NELSON_R6 | machine_speed_mmin | 1 | 9438 | 1335 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2381 | high | NELSON_R6 | machine_speed_mmin | 1 | 9602 | 1316 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2382 | high | NELSON_R6 | machine_speed_mmin | 1 | 9680 | 1564 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2383 | high | NELSON_R6 | machine_speed_mmin | 1 | 9772 | 1304 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2384 | high | NELSON_R6 | machine_speed_mmin | 1 | 9942 | 1302 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2385 | high | NELSON_R6 | machine_speed_mmin | 1 | 10008 | 1499 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2386 | high | NELSON_R6 | machine_speed_mmin | 1 | 10106 | 1707 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2387 | high | NELSON_R6 | machine_speed_mmin | 1 | 10278 | 1317 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2388 | high | NELSON_R6 | machine_speed_mmin | 1 | 10432 | 1329 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2389 | high | NELSON_R6 | machine_speed_mmin | 1 | 10499 | 1563 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2390 | high | NELSON_R6 | machine_speed_mmin | 1 | 10583 | 1328 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2391 | high | NELSON_R6 | machine_speed_mmin | 1 | 10644 | 1503 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2392 | high | NELSON_R6 | machine_speed_mmin | 1 | 10714 | 1304 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2393 | high | NELSON_R6 | machine_speed_mmin | 1 | 10801 | 1543 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2394 | high | NELSON_R6 | machine_speed_mmin | 1 | 10926 | 1324 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2395 | high | NELSON_R6 | machine_speed_mmin | 1 | 10990 | 1497 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2396 | high | NELSON_R6 | machine_speed_mmin | 1 | 11088 | 1309 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2397 | high | NELSON_R6 | machine_speed_mmin | 1 | 11245 | 1331 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2398 | high | NELSON_R6 | machine_speed_mmin | 1 | 11398 | 1320 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2399 | high | NELSON_R6 | machine_speed_mmin | 1 | 11519 | 1699 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2400 | high | NELSON_R6 | machine_speed_mmin | 1 | 11736 | 1317 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2401 | high | NELSON_R6 | machine_speed_mmin | 1 | 11865 | 1322 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2402 | high | NELSON_R6 | machine_speed_mmin | 1 | 12034 | 1527 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2403 | high | NELSON_R6 | machine_speed_mmin | 1 | 12136 | 1308 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2404 | high | NELSON_R6 | machine_speed_mmin | 1 | 12263 | 1318 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2405 | high | NELSON_R6 | machine_speed_mmin | 1 | 12331 | 1514 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2406 | high | NELSON_R6 | machine_speed_mmin | 1 | 12420 | 1313 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2407 | high | NELSON_R6 | machine_speed_mmin | 1 | 12640 | 1318 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2408 | high | NELSON_R6 | machine_speed_mmin | 1 | 12710 | 1506 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2409 | high | NELSON_R6 | machine_speed_mmin | 1 | 12785 | 1321 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2410 | high | NELSON_R6 | machine_speed_mmin | 1 | 12849 | 1513 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2411 | high | NELSON_R6 | machine_speed_mmin | 1 | 12962 | 1314 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2412 | high | NELSON_R6 | machine_speed_mmin | 1 | 13031 | 1521 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2413 | high | NELSON_R6 | machine_speed_mmin | 1 | 13114 | 1310 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2414 | high | NELSON_R6 | machine_speed_mmin | 1 | 13235 | 1319 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2415 | high | NELSON_R6 | machine_speed_mmin | 1 | 13364 | 1332 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2416 | high | NELSON_R6 | machine_speed_mmin | 1 | 13429 | 1518 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2417 | high | NELSON_R6 | machine_speed_mmin | 1 | 13563 | 1306 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2418 | high | NELSON_R6 | machine_speed_mmin | 1 | 13708 | 1319 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2419 | high | NELSON_R6 | machine_speed_mmin | 1 | 13857 | 1334 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2420 | high | NELSON_R6 | machine_speed_mmin | 1 | 13928 | 1494 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2421 | high | NELSON_R6 | machine_speed_mmin | 1 | 14002 | 1698 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2422 | high | NELSON_R6 | machine_speed_mmin | 1 | 14096 | 1504 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2423 | high | NELSON_R6 | machine_speed_mmin | 1 | 14192 | 1336 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2424 | high | NELSON_R6 | machine_speed_mmin | 1 | 14379 | 1331 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2425 | high | NELSON_R6 | machine_speed_mmin | 1 | 14442 | 1514 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2426 | high | NELSON_R6 | machine_speed_mmin | 1 | 14543 | 1321 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2427 | high | NELSON_R6 | machine_speed_mmin | 1 | 14737 | 1327 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2428 | high | NELSON_R6 | machine_speed_mmin | 1 | 14867 | 1318 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2429 | high | NELSON_R6 | machine_speed_mmin | 1 | 14933 | 1507 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2430 | high | NELSON_R6 | machine_speed_mmin | 1 | 15043 | 1331 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2431 | high | NELSON_R6 | machine_speed_mmin | 1 | 15173 | 1321 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2432 | high | NELSON_R6 | machine_speed_mmin | 1 | 15307 | 1333 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2433 | high | NELSON_R6 | machine_speed_mmin | 1 | 15385 | 1523 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2434 | high | NELSON_R6 | machine_speed_mmin | 1 | 15525 | 1319 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2435 | high | NELSON_R6 | machine_speed_mmin | 1 | 15694 | 1319 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2436 | high | NELSON_R6 | machine_speed_mmin | 1 | 15859 | 1320 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2437 | high | NELSON_R6 | machine_speed_mmin | 1 | 15931 | 1514 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2438 | high | NELSON_R6 | machine_speed_mmin | 1 | 16059 | 1302 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2439 | high | NELSON_R6 | machine_speed_mmin | 1 | 16230 | 1321 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2440 | high | NELSON_R6 | machine_speed_mmin | 1 | 16297 | 1524 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2441 | high | NELSON_R6 | machine_speed_mmin | 1 | 16359 | 1323 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2442 | high | NELSON_R6 | machine_speed_mmin | 1 | 16504 | 1697 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2443 | high | NELSON_R6 | machine_speed_mmin | 1 | 16681 | 1322 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2444 | high | NELSON_R6 | machine_speed_mmin | 1 | 16750 | 1517 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2445 | high | NELSON_R6 | machine_speed_mmin | 1 | 16881 | 1319 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2446 | high | NELSON_R6 | machine_speed_mmin | 1 | 17021 | 1314 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2447 | high | NELSON_R6 | machine_speed_mmin | 1 | 17190 | 1326 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2448 | high | NELSON_R6 | machine_speed_mmin | 1 | 17267 | 1525 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2449 | high | NELSON_R6 | machine_speed_mmin | 1 | 17398 | 1312 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2450 | high | NELSON_R6 | machine_speed_mmin | 1 | 17605 | 1390 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2451 | high | NELSON_R6 | machine_speed_mmin | 1 | 17739 | 1310 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2452 | high | NELSON_R6 | machine_speed_mmin | 1 | 17813 | 1518 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2453 | high | NELSON_R6 | machine_speed_mmin | 1 | 17907 | 1334 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2454 | high | NELSON_R6 | machine_speed_mmin | 1 | 17969 | 1496 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2455 | high | NELSON_R6 | machine_speed_mmin | 1 | 18034 | 1698 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2456 | high | NELSON_R6 | machine_speed_mmin | 1 | 18214 | 1325 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2457 | high | NELSON_R6 | machine_speed_mmin | 1 | 18277 | 1506 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2458 | high | NELSON_R6 | machine_speed_mmin | 1 | 18394 | 1315 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2459 | high | NELSON_R6 | machine_speed_mmin | 1 | 18456 | 1514 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2460 | high | NELSON_R6 | machine_speed_mmin | 1 | 18553 | 1695 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2461 | high | NELSON_R6 | machine_speed_mmin | 1 | 18712 | 1307 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2462 | high | NELSON_R6 | machine_speed_mmin | 1 | 18784 | 1518 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2463 | high | NELSON_R6 | machine_speed_mmin | 1 | 18908 | 1322 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2464 | high | NELSON_R6 | machine_speed_mmin | 1 | 19026 | 1330 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2465 | high | NELSON_R6 | machine_speed_mmin | 1 | 19177 | 1309 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2466 | high | NELSON_R6 | machine_speed_mmin | 1 | 19348 | 1311 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2467 | high | NELSON_R6 | machine_speed_mmin | 1 | 19511 | 1327 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2468 | high | NELSON_R6 | machine_speed_mmin | 1 | 19705 | 1306 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2469 | high | NELSON_R6 | machine_speed_mmin | 1 | 19892 | 1319 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2470 | high | NELSON_R6 | machine_speed_mmin | 1 | 20037 | 1693 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2471 | high | NELSON_R6 | machine_speed_mmin | 1 | 20208 | 1320 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2472 | high | NELSON_R6 | machine_speed_mmin | 1 | 20317 | 1332 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2473 | high | NELSON_R6 | machine_speed_mmin | 1 | 20422 | 1338 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2474 | high | NELSON_R6 | machine_speed_mmin | 1 | 20576 | 1316 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2475 | high | NELSON_R6 | machine_speed_mmin | 1 | 20649 | 1490 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2476 | high | NELSON_R6 | machine_speed_mmin | 1 | 20763 | 1306 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2477 | high | NELSON_R6 | machine_speed_mmin | 1 | 20884 | 1293 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2478 | high | NELSON_R6 | machine_speed_mmin | 1 | 21012 | 1313 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2479 | high | NELSON_R6 | machine_speed_mmin | 1 | 21252 | 1308 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2480 | high | NELSON_R6 | machine_speed_mmin | 1 | 21409 | 1332 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2481 | high | NELSON_R6 | machine_speed_mmin | 1 | 21565 | 1313 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2482 | high | NELSON_R6 | machine_speed_mmin | 1 | 21645 | 1517 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2483 | high | NELSON_R6 | machine_speed_mmin | 1 | 21725 | 1331 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2484 | high | NELSON_R6 | machine_speed_mmin | 1 | 21795 | 1495 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2485 | high | NELSON_R6 | stock_temp_C | 1 | 120 | 48.6 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2486 | high | NELSON_R6 | stock_temp_C | 1 | 231 | 44.3 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2487 | high | NELSON_R6 | stock_temp_C | 1 | 516 | 49.7 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2488 | high | NELSON_R6 | stock_temp_C | 1 | 614 | 45.9 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2489 | high | NELSON_R6 | stock_temp_C | 1 | 738 | 48.6 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2490 | high | NELSON_R6 | stock_temp_C | 1 | 851 | 50 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2491 | high | NELSON_R6 | stock_temp_C | 1 | 953 | 44.1 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2492 | high | NELSON_R6 | stock_temp_C | 1 | 1201 | 48.4 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2493 | high | NELSON_R6 | stock_temp_C | 1 | 1277 | 44.6 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2494 | high | NELSON_R6 | stock_temp_C | 1 | 1540 | 48.2 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2495 | high | NELSON_R6 | stock_temp_C | 1 | 1718 | 45.1 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2496 | high | NELSON_R6 | stock_temp_C | 1 | 1826 | 48.7 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2497 | high | NELSON_R6 | stock_temp_C | 1 | 1899 | 49 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2498 | high | NELSON_R6 | stock_temp_C | 1 | 1987 | 45.2 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2499 | high | NELSON_R6 | stock_temp_C | 1 | 2083 | 44.7 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2500 | high | NELSON_R6 | stock_temp_C | 1 | 2237 | 49.2 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2501 | high | NELSON_R6 | stock_temp_C | 1 | 2353 | 45.5 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2502 | high | NELSON_R6 | stock_temp_C | 1 | 2454 | 45.1 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2503 | high | NELSON_R6 | stock_temp_C | 1 | 2519 | 50.6 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2504 | high | NELSON_R6 | stock_temp_C | 1 | 2666 | 45.3 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2505 | high | NELSON_R6 | stock_temp_C | 1 | 2809 | 45.5 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2506 | high | NELSON_R6 | stock_temp_C | 1 | 2894 | 49.4 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2507 | high | NELSON_R6 | stock_temp_C | 1 | 3055 | 42.9 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2508 | high | NELSON_R6 | stock_temp_C | 1 | 3161 | 44.7 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2509 | high | NELSON_R6 | stock_temp_C | 1 | 3279 | 49.5 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2510 | high | NELSON_R6 | stock_temp_C | 1 | 3529 | 45.1 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2511 | high | NELSON_R6 | stock_temp_C | 1 | 3719 | 46.6 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2512 | high | NELSON_R6 | stock_temp_C | 1 | 3896 | 46 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2513 | high | NELSON_R6 | stock_temp_C | 1 | 4261 | 45.4 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2514 | high | NELSON_R6 | stock_temp_C | 1 | 4643 | 44.9 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2515 | high | NELSON_R6 | stock_temp_C | 1 | 4797 | 44.4 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2516 | high | NELSON_R6 | stock_temp_C | 1 | 5000 | 49.8 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2517 | high | NELSON_R6 | stock_temp_C | 1 | 5388 | 44.3 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2518 | high | NELSON_R6 | stock_temp_C | 1 | 5476 | 46 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2519 | high | NELSON_R6 | stock_temp_C | 1 | 5727 | 45.7 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2520 | high | NELSON_R6 | stock_temp_C | 1 | 5824 | 44.9 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2521 | high | NELSON_R6 | stock_temp_C | 1 | 6088 | 45.2 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2522 | high | NELSON_R6 | stock_temp_C | 1 | 6426 | 43.8 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2523 | high | NELSON_R6 | stock_temp_C | 1 | 6851 | 44.8 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2524 | high | NELSON_R6 | stock_temp_C | 1 | 7189 | 48.3 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2525 | high | NELSON_R6 | stock_temp_C | 1 | 8305 | 43.1 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2526 | high | NELSON_R6 | stock_temp_C | 1 | 10275 | 39.6 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2527 | high | NELSON_R6 | stock_temp_C | 1 | 10565 | 36.8 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2528 | high | NELSON_R6 | stock_temp_C | 1 | 11022 | 41.1 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2529 | high | NELSON_R6 | stock_temp_C | 1 | 13078 | 35.9 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2530 | high | NELSON_R6 | stock_temp_C | 1 | 13430 | 35.4 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2531 | high | NELSON_R6 | stock_temp_C | 1 | 13759 | 35.4 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2532 | high | NELSON_R6 | stock_temp_C | 1 | 15665 | 38.3 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2533 | high | NELSON_R6 | stock_temp_C | 1 | 16228 | 36.8 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2534 | high | NELSON_R6 | stock_temp_C | 1 | 16546 | 38.9 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2535 | high | NELSON_R6 | stock_temp_C | 1 | 17269 | 38.6 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2536 | high | NELSON_R6 | stock_temp_C | 1 | 18169 | 40.4 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2537 | high | NELSON_R6 | stock_temp_C | 1 | 18231 | 42.1 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2538 | high | NELSON_R6 | stock_temp_C | 1 | 18607 | 46.3 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2539 | high | NELSON_R6 | stock_temp_C | 1 | 19155 | 39.5 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2540 | high | NELSON_R6 | stock_temp_C | 1 | 19397 | 44.6 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2541 | high | NELSON_R6 | stock_temp_C | 1 | 19731 | 44.7 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2542 | high | NELSON_R6 | stock_temp_C | 1 | 20080 | 44.4 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2543 | high | NELSON_R6 | stock_temp_C | 1 | 20432 | 45 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2544 | high | NELSON_R6 | stock_temp_C | 1 | 20513 | 43.8 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2545 | high | NELSON_R6 | stock_temp_C | 1 | 20794 | 44.4 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2546 | high | NELSON_R6 | stock_temp_C | 1 | 20931 | 44 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2547 | high | NELSON_R6 | stock_temp_C | 1 | 21170 | 45 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2548 | high | NELSON_R6 | stock_temp_C | 1 | 21279 | 44.6 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2549 | high | NELSON_R6 | stock_temp_C | 1 | 21340 | 41.2 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2550 | high | NELSON_R6 | stock_temp_C | 1 | 21489 | 44.4 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2551 | high | NELSON_R6 | stock_temp_C | 1 | 21860 | 43 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2552 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 366 | 64.2 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2553 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 802 | 49.4 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2554 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 1253 | 59.1 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2555 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 1332 | 58.9 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2556 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 1520 | 45 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2557 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 1802 | 64.3 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2558 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 1866 | 57.6 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2559 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 2071 | 42.8 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2560 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 2389 | 57.9 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2561 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 2878 | 64.8 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2562 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 3079 | 48.2 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2563 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 3507 | 59.5 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2564 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 3691 | 59.7 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2565 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 4104 | 61.4 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2566 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 4266 | 45.4 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2567 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 4421 | 59.4 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2568 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 4565 | 41.4 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2569 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 4920 | 48.8 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2570 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 5644 | 57.9 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2571 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 5813 | 49.2 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2572 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 6388 | 48.1 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2573 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 6747 | 52.3 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2574 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 7230 | 40.3 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2575 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 7636 | 58 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2576 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 7974 | 36.6 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2577 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 8253 | 51.6 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2578 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 9129 | 46.3 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2579 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 9530 | 45.5 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2580 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 9690 | 52 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2581 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 9861 | 64.3 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2582 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 9948 | 50.8 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2583 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 10070 | 46.1 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2584 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 10162 | 58 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2585 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 10329 | 60.9 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2586 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 10484 | 57.5 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2587 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 11046 | 55.2 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2588 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 11151 | 44.7 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2589 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 11254 | 41.1 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2590 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 11348 | 57.4 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2591 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 11477 | 42.3 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2592 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 12215 | 57.7 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2593 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 12382 | 46.9 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2594 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 12773 | 47.5 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2595 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 13051 | 57.4 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2596 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 13354 | 45.6 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2597 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 13442 | 56.6 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2598 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 14107 | 57.1 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2599 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 14287 | 62.5 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2600 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 14882 | 61.6 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2601 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 15073 | 43.8 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2602 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 15161 | 59.1 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2603 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 15721 | 57.4 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2604 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 16394 | 47.5 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2605 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 17128 | 61.7 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2606 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 17250 | 64.6 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2607 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 17612 | 61.3 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2608 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 17691 | 58 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2609 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 17912 | 59.3 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2610 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 18362 | 59.1 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2611 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 18549 | 42.5 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2612 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 18986 | 56.6 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2613 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 20019 | 57.7 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2614 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 20351 | 56.4 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2615 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 21280 | 43.4 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2616 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 21413 | 50.6 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2617 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 21634 | 49.6 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2618 | high | NELSON_R6 | vacuum_pump1_kPa | 1 | 21835 | 46.9 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2619 | high | NELSON_R6 | white_water_consistency_pct | 1 | 6 | 0.979 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2620 | high | NELSON_R6 | white_water_consistency_pct | 1 | 2404 | 0.961 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2621 | high | NELSON_R6 | white_water_consistency_pct | 1 | 2897 | 1.005 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2622 | high | NELSON_R6 | white_water_consistency_pct | 1 | 3183 | 1.041 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2623 | high | NELSON_R6 | white_water_consistency_pct | 1 | 3502 | 1.089 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2624 | high | NELSON_R6 | white_water_consistency_pct | 1 | 3636 | 1.044 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2625 | high | NELSON_R6 | white_water_consistency_pct | 1 | 3741 | 0.934 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2626 | high | NELSON_R6 | white_water_consistency_pct | 1 | 3842 | 0.962 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2627 | high | NELSON_R6 | white_water_consistency_pct | 1 | 4026 | 0.923 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2628 | high | NELSON_R6 | white_water_consistency_pct | 1 | 4338 | 0.845 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2629 | high | NELSON_R6 | white_water_consistency_pct | 1 | 4440 | 0.804 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2630 | high | NELSON_R6 | white_water_consistency_pct | 1 | 4622 | 0.944 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2631 | high | NELSON_R6 | white_water_consistency_pct | 1 | 4780 | 1.021 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2632 | high | NELSON_R6 | white_water_consistency_pct | 1 | 4847 | 0.949 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2633 | high | NELSON_R6 | white_water_consistency_pct | 1 | 5127 | 1.125 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2634 | high | NELSON_R6 | white_water_consistency_pct | 1 | 5635 | 0.946 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2635 | high | NELSON_R6 | white_water_consistency_pct | 1 | 5879 | 1.025 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2636 | high | NELSON_R6 | white_water_consistency_pct | 1 | 7249 | 0.958 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2637 | high | NELSON_R6 | white_water_consistency_pct | 1 | 7711 | 0.803 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2638 | high | NELSON_R6 | white_water_consistency_pct | 1 | 10751 | 0.794 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2639 | high | NELSON_R6 | white_water_consistency_pct | 1 | 10872 | 0.629 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2640 | high | NELSON_R6 | white_water_consistency_pct | 1 | 11103 | 1.021 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2641 | high | NELSON_R6 | white_water_consistency_pct | 1 | 11188 | 0.943 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2642 | high | NELSON_R6 | white_water_consistency_pct | 1 | 11401 | 0.921 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2643 | high | NELSON_R6 | white_water_consistency_pct | 1 | 11529 | 0.793 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2644 | high | NELSON_R6 | white_water_consistency_pct | 1 | 11771 | 1.019 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2645 | high | NELSON_R6 | white_water_consistency_pct | 1 | 11878 | 0.948 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2646 | high | NELSON_R6 | white_water_consistency_pct | 1 | 12121 | 1.001 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2647 | high | NELSON_R6 | white_water_consistency_pct | 1 | 12329 | 0.936 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2648 | high | NELSON_R6 | white_water_consistency_pct | 1 | 12513 | 0.952 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2649 | high | NELSON_R6 | white_water_consistency_pct | 1 | 13192 | 0.941 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2650 | high | NELSON_R6 | white_water_consistency_pct | 1 | 13405 | 0.945 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2651 | high | NELSON_R6 | white_water_consistency_pct | 1 | 13625 | 0.952 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2652 | high | NELSON_R6 | white_water_consistency_pct | 1 | 16074 | 0.945 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2653 | high | NELSON_R6 | white_water_consistency_pct | 1 | 21173 | 0.946 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2654 | high | NELSON_R6 | white_water_consistency_pct | 1 | 21860 | 1.224 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2655 | high | NELSON_R6 | fan_pump_speed_rpm | 2 | 21 | 892.6 | fan_pump_speed_rpm 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2656 | high | NELSON_R6 | fan_pump_speed_rpm | 2 | 373 | 889.9 | fan_pump_speed_rpm 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2657 | high | NELSON_R6 | fan_pump_speed_rpm | 2 | 909 | 885.6 | fan_pump_speed_rpm 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2658 | high | NELSON_R6 | fan_pump_speed_rpm | 2 | 1028 | 899.2 | fan_pump_speed_rpm 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2659 | high | NELSON_R6 | fan_pump_speed_rpm | 2 | 1282 | 897.7 | fan_pump_speed_rpm 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2660 | high | NELSON_R6 | fan_pump_speed_rpm | 2 | 1362 | 898.9 | fan_pump_speed_rpm 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2661 | high | NELSON_R6 | fan_pump_speed_rpm | 2 | 1493 | 887.4 | fan_pump_speed_rpm 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2662 | high | NELSON_R6 | fan_pump_speed_rpm | 2 | 1745 | 893.4 | fan_pump_speed_rpm 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2663 | high | NELSON_R6 | fan_pump_speed_rpm | 2 | 2471 | 888.9 | fan_pump_speed_rpm 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2664 | high | NELSON_R6 | fan_pump_speed_rpm | 2 | 21987 | 943.7 | fan_pump_speed_rpm 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2665 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 28 | 18.04 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2666 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 142 | 17.21 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2667 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 257 | 18.45 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2668 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 369 | 20.96 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2669 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 432 | 18.02 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2670 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 536 | 24.49 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2671 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 734 | 17.9 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2672 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 921 | 17.89 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2673 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 1205 | 24.22 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2674 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 1400 | 25.14 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2675 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 1577 | 18.73 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2676 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 1639 | 21.56 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2677 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 1721 | 18.88 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2678 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 1857 | 19.05 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2679 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 1932 | 22.17 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2680 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 2043 | 25.34 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2681 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 2197 | 25.91 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2682 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 2416 | 20.01 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2683 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 2583 | 19.67 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2684 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 2751 | 19.63 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2685 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 2930 | 19.88 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2686 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 3081 | 19.67 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2687 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 3227 | 26.58 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2688 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 3511 | 23.07 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2689 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 4538 | 28.28 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2690 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 4732 | 22.12 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2691 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 5072 | 25.39 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2692 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 5404 | 29.46 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2693 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 6330 | 25.95 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2694 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 6814 | 27.42 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2695 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 7052 | 23.16 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2696 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 7290 | 32.05 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2697 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 7681 | 28.36 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2698 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 7746 | 32.47 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2699 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 7838 | 27.92 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2700 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 8072 | 24.65 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2701 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 10010 | 33.63 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2702 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 10324 | 27.49 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2703 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 10548 | 30.97 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2704 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 10611 | 22.92 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2705 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 10987 | 25.02 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2706 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 11144 | 24.5 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2707 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 11589 | 19.93 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2708 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 12036 | 20.55 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2709 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 12191 | 21.14 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2710 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 12618 | 21.91 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2711 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 12936 | 29.29 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2712 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 13175 | 25.47 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2713 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 13695 | 22.41 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2714 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 13914 | 25.84 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2715 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 14408 | 26.54 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2716 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 14583 | 26.94 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2717 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 14821 | 30.88 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2718 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 15377 | 23.67 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2719 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 15814 | 31.62 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2720 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 16313 | 31.88 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2721 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 16468 | 32.13 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2722 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 17412 | 28.96 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2723 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 18014 | 29.69 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2724 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 18355 | 34.41 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2725 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 18475 | 30.28 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2726 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 18938 | 26.12 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2727 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 20579 | 32.91 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2728 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 20841 | 33.05 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2729 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 21334 | 33.55 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2730 | high | NELSON_R6 | headbox_pressure_kPa | 2 | 21987 | 39.61 | headbox_pressure_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2731 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 237 | 1.067 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2732 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 762 | 1.055 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2733 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 1058 | 1.052 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2734 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 1508 | 0.995 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2735 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 1602 | 1.125 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2736 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 1674 | 1.056 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2737 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 2418 | 1.058 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2738 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 2752 | 0.982 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2739 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 2839 | 0.988 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2740 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 2912 | 1 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2741 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 3003 | 1.074 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2742 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 3172 | 1.054 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2743 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 3234 | 0.987 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2744 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 3399 | 0.949 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2745 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 3512 | 1.067 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2746 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 4350 | 1.068 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2747 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 4743 | 0.963 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2748 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 5192 | 0.976 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2749 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 5641 | 1.027 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2750 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 5975 | 1.054 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2751 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 6154 | 0.988 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2752 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 6650 | 1.109 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2753 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 6769 | 1.052 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2754 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 7253 | 0.989 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2755 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 7629 | 1.056 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2756 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 8417 | 1.052 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2757 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 8668 | 0.988 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2758 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 8777 | 1.008 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2759 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 8970 | 1.065 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2760 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 9616 | 1.058 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2761 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 9830 | 0.957 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2762 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 9953 | 1.056 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2763 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 10304 | 0.985 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2764 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 10810 | 1.069 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2765 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 10923 | 1.061 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2766 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 11076 | 1.059 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2767 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 11782 | 0.977 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2768 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 11968 | 1.06 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2769 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 12623 | 1.066 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2770 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 12720 | 0.988 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2771 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 13481 | 1.051 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2772 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 13898 | 0.988 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2773 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 14744 | 1.051 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2774 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 14897 | 1.073 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2775 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 15061 | 1.081 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2776 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 15333 | 1.062 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2777 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 15489 | 0.98 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2778 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 15605 | 1.073 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2779 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 15693 | 0.986 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2780 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 15944 | 0.98 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2781 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 16077 | 1.074 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2782 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 16325 | 1.064 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2783 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 17352 | 1.057 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2784 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 18503 | 0.967 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2785 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 18799 | 1.004 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2786 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 19117 | 1.073 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2787 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 19339 | 1.012 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2788 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 19490 | 1.068 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2789 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 19558 | 0.97 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2790 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 20020 | 1.042 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2791 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 20222 | 1.055 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2792 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 20797 | 0.966 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2793 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 21006 | 1.054 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2794 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 21137 | 1.073 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2795 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 21289 | 1.036 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2796 | high | NELSON_R6 | jet_to_wire_ratio | 2 | 21732 | 1.067 | jet_to_wire_ratio 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2797 | high | NELSON_R6 | machine_speed_mmin | 2 | 28 | 1315 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2798 | high | NELSON_R6 | machine_speed_mmin | 2 | 142 | 1320 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2799 | high | NELSON_R6 | machine_speed_mmin | 2 | 318 | 1495 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2800 | high | NELSON_R6 | machine_speed_mmin | 2 | 432 | 1326 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2801 | high | NELSON_R6 | machine_speed_mmin | 2 | 572 | 1296 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2802 | high | NELSON_R6 | machine_speed_mmin | 2 | 734 | 1309 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2803 | high | NELSON_R6 | machine_speed_mmin | 2 | 808 | 1513 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2804 | high | NELSON_R6 | machine_speed_mmin | 2 | 921 | 1328 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2805 | high | NELSON_R6 | machine_speed_mmin | 2 | 1044 | 1302 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2806 | high | NELSON_R6 | machine_speed_mmin | 2 | 1212 | 1717 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2807 | high | NELSON_R6 | machine_speed_mmin | 2 | 1290 | 1507 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2808 | high | NELSON_R6 | machine_speed_mmin | 2 | 1415 | 1313 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2809 | high | NELSON_R6 | machine_speed_mmin | 2 | 1480 | 1510 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2810 | high | NELSON_R6 | machine_speed_mmin | 2 | 1577 | 1325 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2811 | high | NELSON_R6 | machine_speed_mmin | 2 | 1721 | 1312 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2812 | high | NELSON_R6 | machine_speed_mmin | 2 | 1857 | 1325 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2813 | high | NELSON_R6 | machine_speed_mmin | 2 | 1925 | 1524 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2814 | high | NELSON_R6 | machine_speed_mmin | 2 | 2071 | 1305 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2815 | high | NELSON_R6 | machine_speed_mmin | 2 | 2225 | 1362 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2816 | high | NELSON_R6 | machine_speed_mmin | 2 | 2413 | 1317 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2817 | high | NELSON_R6 | machine_speed_mmin | 2 | 2480 | 1504 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2818 | high | NELSON_R6 | machine_speed_mmin | 2 | 2578 | 1317 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2819 | high | NELSON_R6 | machine_speed_mmin | 2 | 2650 | 1512 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2820 | high | NELSON_R6 | machine_speed_mmin | 2 | 2733 | 1330 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2821 | high | NELSON_R6 | machine_speed_mmin | 2 | 2923 | 1327 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2822 | high | NELSON_R6 | machine_speed_mmin | 2 | 3078 | 1318 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2823 | high | NELSON_R6 | machine_speed_mmin | 2 | 3158 | 1509 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2824 | high | NELSON_R6 | machine_speed_mmin | 2 | 3248 | 1310 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2825 | high | NELSON_R6 | machine_speed_mmin | 2 | 3313 | 1510 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2826 | high | NELSON_R6 | machine_speed_mmin | 2 | 3424 | 1312 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2827 | high | NELSON_R6 | machine_speed_mmin | 2 | 3493 | 1495 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2828 | high | NELSON_R6 | machine_speed_mmin | 2 | 3587 | 1334 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2829 | high | NELSON_R6 | machine_speed_mmin | 2 | 3653 | 1514 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2830 | high | NELSON_R6 | machine_speed_mmin | 2 | 3789 | 1327 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2831 | high | NELSON_R6 | machine_speed_mmin | 2 | 3856 | 1505 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2832 | high | NELSON_R6 | machine_speed_mmin | 2 | 3962 | 1316 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2833 | high | NELSON_R6 | machine_speed_mmin | 2 | 4029 | 1499 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2834 | high | NELSON_R6 | machine_speed_mmin | 2 | 4148 | 1326 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2835 | high | NELSON_R6 | machine_speed_mmin | 2 | 4225 | 1511 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2836 | high | NELSON_R6 | machine_speed_mmin | 2 | 4320 | 1311 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2837 | high | NELSON_R6 | machine_speed_mmin | 2 | 4449 | 1315 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2838 | high | NELSON_R6 | machine_speed_mmin | 2 | 4582 | 1314 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2839 | high | NELSON_R6 | machine_speed_mmin | 2 | 4723 | 1316 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2840 | high | NELSON_R6 | machine_speed_mmin | 2 | 4862 | 1326 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2841 | high | NELSON_R6 | machine_speed_mmin | 2 | 5025 | 1299 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2842 | high | NELSON_R6 | machine_speed_mmin | 2 | 5146 | 1313 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2843 | high | NELSON_R6 | machine_speed_mmin | 2 | 5282 | 1319 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2844 | high | NELSON_R6 | machine_speed_mmin | 2 | 5344 | 1502 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2845 | high | NELSON_R6 | machine_speed_mmin | 2 | 5490 | 1346 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2846 | high | NELSON_R6 | machine_speed_mmin | 2 | 5557 | 1508 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2847 | high | NELSON_R6 | machine_speed_mmin | 2 | 5666 | 1317 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2848 | high | NELSON_R6 | machine_speed_mmin | 2 | 5786 | 1318 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2849 | high | NELSON_R6 | machine_speed_mmin | 2 | 5962 | 1324 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2850 | high | NELSON_R6 | machine_speed_mmin | 2 | 6026 | 1519 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2851 | high | NELSON_R6 | machine_speed_mmin | 2 | 6114 | 1335 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2852 | high | NELSON_R6 | machine_speed_mmin | 2 | 6240 | 1312 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2853 | high | NELSON_R6 | machine_speed_mmin | 2 | 6403 | 1322 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2854 | high | NELSON_R6 | machine_speed_mmin | 2 | 6484 | 1510 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2855 | high | NELSON_R6 | machine_speed_mmin | 2 | 6602 | 1316 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2856 | high | NELSON_R6 | machine_speed_mmin | 2 | 6666 | 1514 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2857 | high | NELSON_R6 | machine_speed_mmin | 2 | 6761 | 1318 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2858 | high | NELSON_R6 | machine_speed_mmin | 2 | 6903 | 1312 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2859 | high | NELSON_R6 | machine_speed_mmin | 2 | 6998 | 1316 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2860 | high | NELSON_R6 | machine_speed_mmin | 2 | 7071 | 1517 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2861 | high | NELSON_R6 | machine_speed_mmin | 2 | 7180 | 1342 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2862 | high | NELSON_R6 | machine_speed_mmin | 2 | 7318 | 1317 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2863 | high | NELSON_R6 | machine_speed_mmin | 2 | 7459 | 1309 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2864 | high | NELSON_R6 | machine_speed_mmin | 2 | 7598 | 1330 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2865 | high | NELSON_R6 | machine_speed_mmin | 2 | 7757 | 1322 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2866 | high | NELSON_R6 | machine_speed_mmin | 2 | 7916 | 1322 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2867 | high | NELSON_R6 | machine_speed_mmin | 2 | 8029 | 1320 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2868 | high | NELSON_R6 | machine_speed_mmin | 2 | 8221 | 1324 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2869 | high | NELSON_R6 | machine_speed_mmin | 2 | 8383 | 1321 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2870 | high | NELSON_R6 | machine_speed_mmin | 2 | 8558 | 1321 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2871 | high | NELSON_R6 | machine_speed_mmin | 2 | 8636 | 1523 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2872 | high | NELSON_R6 | machine_speed_mmin | 2 | 8758 | 1310 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2873 | high | NELSON_R6 | machine_speed_mmin | 2 | 8858 | 1699 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2874 | high | NELSON_R6 | machine_speed_mmin | 2 | 8981 | 1693 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2875 | high | NELSON_R6 | machine_speed_mmin | 2 | 9149 | 1321 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2876 | high | NELSON_R6 | machine_speed_mmin | 2 | 9217 | 1479 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2877 | high | NELSON_R6 | machine_speed_mmin | 2 | 9298 | 1323 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2878 | high | NELSON_R6 | machine_speed_mmin | 2 | 9367 | 1503 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2879 | high | NELSON_R6 | machine_speed_mmin | 2 | 9495 | 1318 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2880 | high | NELSON_R6 | machine_speed_mmin | 2 | 9560 | 1519 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2881 | high | NELSON_R6 | machine_speed_mmin | 2 | 9678 | 1334 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2882 | high | NELSON_R6 | machine_speed_mmin | 2 | 9848 | 1314 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2883 | high | NELSON_R6 | machine_speed_mmin | 2 | 9919 | 1502 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2884 | high | NELSON_R6 | machine_speed_mmin | 2 | 10017 | 1322 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2885 | high | NELSON_R6 | machine_speed_mmin | 2 | 10086 | 1491 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2886 | high | NELSON_R6 | machine_speed_mmin | 2 | 10209 | 1313 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2887 | high | NELSON_R6 | machine_speed_mmin | 2 | 10280 | 1499 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2888 | high | NELSON_R6 | machine_speed_mmin | 2 | 10383 | 1700 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2889 | high | NELSON_R6 | machine_speed_mmin | 2 | 10473 | 1512 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2890 | high | NELSON_R6 | machine_speed_mmin | 2 | 10572 | 1320 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2891 | high | NELSON_R6 | machine_speed_mmin | 2 | 10745 | 1302 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2892 | high | NELSON_R6 | machine_speed_mmin | 2 | 10818 | 1516 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2893 | high | NELSON_R6 | machine_speed_mmin | 2 | 10889 | 1317 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2894 | high | NELSON_R6 | machine_speed_mmin | 2 | 10969 | 1507 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2895 | high | NELSON_R6 | machine_speed_mmin | 2 | 11055 | 1320 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2896 | high | NELSON_R6 | machine_speed_mmin | 2 | 11244 | 1320 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2897 | high | NELSON_R6 | machine_speed_mmin | 2 | 11384 | 1327 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2898 | high | NELSON_R6 | machine_speed_mmin | 2 | 11563 | 1318 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2899 | high | NELSON_R6 | machine_speed_mmin | 2 | 11636 | 1500 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2900 | high | NELSON_R6 | machine_speed_mmin | 2 | 11723 | 1695 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2901 | high | NELSON_R6 | machine_speed_mmin | 2 | 11859 | 1306 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2902 | high | NELSON_R6 | machine_speed_mmin | 2 | 12009 | 1334 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2903 | high | NELSON_R6 | machine_speed_mmin | 2 | 12150 | 1317 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2904 | high | NELSON_R6 | machine_speed_mmin | 2 | 12212 | 1506 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2905 | high | NELSON_R6 | machine_speed_mmin | 2 | 12293 | 1292 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2906 | high | NELSON_R6 | machine_speed_mmin | 2 | 12452 | 1315 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2907 | high | NELSON_R6 | machine_speed_mmin | 2 | 12516 | 1516 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2908 | high | NELSON_R6 | machine_speed_mmin | 2 | 12582 | 1338 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2909 | high | NELSON_R6 | machine_speed_mmin | 2 | 12662 | 1507 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2910 | high | NELSON_R6 | machine_speed_mmin | 2 | 12759 | 1314 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2911 | high | NELSON_R6 | machine_speed_mmin | 2 | 12827 | 1515 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2912 | high | NELSON_R6 | machine_speed_mmin | 2 | 12965 | 1322 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2913 | high | NELSON_R6 | machine_speed_mmin | 2 | 13107 | 1332 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2914 | high | NELSON_R6 | machine_speed_mmin | 2 | 13172 | 1500 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2915 | high | NELSON_R6 | machine_speed_mmin | 2 | 13267 | 1325 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2916 | high | NELSON_R6 | machine_speed_mmin | 2 | 13339 | 1494 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2917 | high | NELSON_R6 | machine_speed_mmin | 2 | 13430 | 1319 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2918 | high | NELSON_R6 | machine_speed_mmin | 2 | 13537 | 1320 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2919 | high | NELSON_R6 | machine_speed_mmin | 2 | 13666 | 1314 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2920 | high | NELSON_R6 | machine_speed_mmin | 2 | 13728 | 1514 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2921 | high | NELSON_R6 | machine_speed_mmin | 2 | 13852 | 1322 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2922 | high | NELSON_R6 | machine_speed_mmin | 2 | 14023 | 1353 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2923 | high | NELSON_R6 | machine_speed_mmin | 2 | 14161 | 1342 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2924 | high | NELSON_R6 | machine_speed_mmin | 2 | 14237 | 1510 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2925 | high | NELSON_R6 | machine_speed_mmin | 2 | 14333 | 1312 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2926 | high | NELSON_R6 | machine_speed_mmin | 2 | 14498 | 1346 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2927 | high | NELSON_R6 | machine_speed_mmin | 2 | 14674 | 1310 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2928 | high | NELSON_R6 | machine_speed_mmin | 2 | 14848 | 1327 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2929 | high | NELSON_R6 | machine_speed_mmin | 2 | 15023 | 1324 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2930 | high | NELSON_R6 | machine_speed_mmin | 2 | 15187 | 1323 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2931 | high | NELSON_R6 | machine_speed_mmin | 2 | 15261 | 1508 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2932 | high | NELSON_R6 | machine_speed_mmin | 2 | 15324 | 1699 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2933 | high | NELSON_R6 | machine_speed_mmin | 2 | 15498 | 1320 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2934 | high | NELSON_R6 | machine_speed_mmin | 2 | 15633 | 1313 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2935 | high | NELSON_R6 | machine_speed_mmin | 2 | 15702 | 1515 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2936 | high | NELSON_R6 | machine_speed_mmin | 2 | 15832 | 1320 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2937 | high | NELSON_R6 | machine_speed_mmin | 2 | 15991 | 1315 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2938 | high | NELSON_R6 | machine_speed_mmin | 2 | 16058 | 1509 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2939 | high | NELSON_R6 | machine_speed_mmin | 2 | 16162 | 1326 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2940 | high | NELSON_R6 | machine_speed_mmin | 2 | 16224 | 1520 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2941 | high | NELSON_R6 | machine_speed_mmin | 2 | 16366 | 1324 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2942 | high | NELSON_R6 | machine_speed_mmin | 2 | 16550 | 1288 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2943 | high | NELSON_R6 | machine_speed_mmin | 2 | 16620 | 1512 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2944 | high | NELSON_R6 | machine_speed_mmin | 2 | 16684 | 1352 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2945 | high | NELSON_R6 | machine_speed_mmin | 2 | 16884 | 1321 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2946 | high | NELSON_R6 | machine_speed_mmin | 2 | 17015 | 1326 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2947 | high | NELSON_R6 | machine_speed_mmin | 2 | 17232 | 1321 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2948 | high | NELSON_R6 | machine_speed_mmin | 2 | 17375 | 1321 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2949 | high | NELSON_R6 | machine_speed_mmin | 2 | 17541 | 1319 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2950 | high | NELSON_R6 | machine_speed_mmin | 2 | 17613 | 1519 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2951 | high | NELSON_R6 | machine_speed_mmin | 2 | 17706 | 1689 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2952 | high | NELSON_R6 | machine_speed_mmin | 2 | 17809 | 1528 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2953 | high | NELSON_R6 | machine_speed_mmin | 2 | 17943 | 1308 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2954 | high | NELSON_R6 | machine_speed_mmin | 2 | 18062 | 1326 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2955 | high | NELSON_R6 | machine_speed_mmin | 2 | 18133 | 1515 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2956 | high | NELSON_R6 | machine_speed_mmin | 2 | 18233 | 1325 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2957 | high | NELSON_R6 | machine_speed_mmin | 2 | 18396 | 1338 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2958 | high | NELSON_R6 | machine_speed_mmin | 2 | 18549 | 1305 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2959 | high | NELSON_R6 | machine_speed_mmin | 2 | 18615 | 1489 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2960 | high | NELSON_R6 | machine_speed_mmin | 2 | 18740 | 1328 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2961 | high | NELSON_R6 | machine_speed_mmin | 2 | 18902 | 1316 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2962 | high | NELSON_R6 | machine_speed_mmin | 2 | 19009 | 1319 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2963 | high | NELSON_R6 | machine_speed_mmin | 2 | 19178 | 1306 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2964 | high | NELSON_R6 | machine_speed_mmin | 2 | 19420 | 1332 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2965 | high | NELSON_R6 | machine_speed_mmin | 2 | 19580 | 1291 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2966 | high | NELSON_R6 | machine_speed_mmin | 2 | 19748 | 1323 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2967 | high | NELSON_R6 | machine_speed_mmin | 2 | 19951 | 1309 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2968 | high | NELSON_R6 | machine_speed_mmin | 2 | 20084 | 1313 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2969 | high | NELSON_R6 | machine_speed_mmin | 2 | 20256 | 1325 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2970 | high | NELSON_R6 | machine_speed_mmin | 2 | 20410 | 1323 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2971 | high | NELSON_R6 | machine_speed_mmin | 2 | 20519 | 1315 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2972 | high | NELSON_R6 | machine_speed_mmin | 2 | 20630 | 1323 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2973 | high | NELSON_R6 | machine_speed_mmin | 2 | 20760 | 1338 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2974 | high | NELSON_R6 | machine_speed_mmin | 2 | 20827 | 1511 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2975 | high | NELSON_R6 | machine_speed_mmin | 2 | 20935 | 1322 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2976 | high | NELSON_R6 | machine_speed_mmin | 2 | 21029 | 1332 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2977 | high | NELSON_R6 | machine_speed_mmin | 2 | 21136 | 1330 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2978 | high | NELSON_R6 | machine_speed_mmin | 2 | 21255 | 1332 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2979 | high | NELSON_R6 | machine_speed_mmin | 2 | 21409 | 1304 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2980 | high | NELSON_R6 | machine_speed_mmin | 2 | 21472 | 1505 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2981 | high | NELSON_R6 | machine_speed_mmin | 2 | 21568 | 1319 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2982 | high | NELSON_R6 | machine_speed_mmin | 2 | 21629 | 1510 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2983 | high | NELSON_R6 | machine_speed_mmin | 2 | 21733 | 1310 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2984 | high | NELSON_R6 | machine_speed_mmin | 2 | 21795 | 1504 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2985 | high | NELSON_R6 | machine_speed_mmin | 2 | 21864 | 1322 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2986 | high | NELSON_R6 | machine_speed_mmin | 2 | 21926 | 1506 | machine_speed_mmin 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2987 | high | NELSON_R6 | stock_temp_C | 2 | 117 | 48.8 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2988 | high | NELSON_R6 | stock_temp_C | 2 | 192 | 45 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2989 | high | NELSON_R6 | stock_temp_C | 2 | 329 | 49.1 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2990 | high | NELSON_R6 | stock_temp_C | 2 | 467 | 48.9 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2991 | high | NELSON_R6 | stock_temp_C | 2 | 561 | 46 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2992 | high | NELSON_R6 | stock_temp_C | 2 | 677 | 54.7 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2993 | high | NELSON_R6 | stock_temp_C | 2 | 809 | 50.2 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2994 | high | NELSON_R6 | stock_temp_C | 2 | 914 | 44.8 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2995 | high | NELSON_R6 | stock_temp_C | 2 | 1052 | 48.6 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2996 | high | NELSON_R6 | stock_temp_C | 2 | 1149 | 45.7 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2997 | high | NELSON_R6 | stock_temp_C | 2 | 1276 | 44.9 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2998 | high | NELSON_R6 | stock_temp_C | 2 | 1345 | 46.4 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 2999 | high | NELSON_R6 | stock_temp_C | 2 | 1418 | 48.9 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3000 | high | NELSON_R6 | stock_temp_C | 2 | 1543 | 48.5 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3001 | high | NELSON_R6 | stock_temp_C | 2 | 1648 | 44 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3002 | high | NELSON_R6 | stock_temp_C | 2 | 1804 | 52.3 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3003 | high | NELSON_R6 | stock_temp_C | 2 | 2078 | 44.5 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3004 | high | NELSON_R6 | stock_temp_C | 2 | 2197 | 48.6 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3005 | high | NELSON_R6 | stock_temp_C | 2 | 2340 | 45.7 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3006 | high | NELSON_R6 | stock_temp_C | 2 | 2451 | 45.2 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3007 | high | NELSON_R6 | stock_temp_C | 2 | 2597 | 49.8 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3008 | high | NELSON_R6 | stock_temp_C | 2 | 2704 | 45.5 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3009 | high | NELSON_R6 | stock_temp_C | 2 | 2803 | 43.7 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3010 | high | NELSON_R6 | stock_temp_C | 2 | 2955 | 48.9 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3011 | high | NELSON_R6 | stock_temp_C | 2 | 3059 | 44.9 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3012 | high | NELSON_R6 | stock_temp_C | 2 | 3227 | 45.1 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3013 | high | NELSON_R6 | stock_temp_C | 2 | 3583 | 45.3 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3014 | high | NELSON_R6 | stock_temp_C | 2 | 3952 | 45.7 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3015 | high | NELSON_R6 | stock_temp_C | 2 | 4046 | 47.8 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3016 | high | NELSON_R6 | stock_temp_C | 2 | 4133 | 45.2 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3017 | high | NELSON_R6 | stock_temp_C | 2 | 4275 | 42.5 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3018 | high | NELSON_R6 | stock_temp_C | 2 | 4661 | 45.4 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3019 | high | NELSON_R6 | stock_temp_C | 2 | 5006 | 39.2 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3020 | high | NELSON_R6 | stock_temp_C | 2 | 5169 | 44.9 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3021 | high | NELSON_R6 | stock_temp_C | 2 | 5291 | 40.7 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3022 | high | NELSON_R6 | stock_temp_C | 2 | 5406 | 44.5 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3023 | high | NELSON_R6 | stock_temp_C | 2 | 5533 | 45 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3024 | high | NELSON_R6 | stock_temp_C | 2 | 5800 | 44.7 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3025 | high | NELSON_R6 | stock_temp_C | 2 | 5867 | 42 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3026 | high | NELSON_R6 | stock_temp_C | 2 | 6181 | 46 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3027 | high | NELSON_R6 | stock_temp_C | 2 | 6550 | 44.7 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3028 | high | NELSON_R6 | stock_temp_C | 2 | 6940 | 44.8 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3029 | high | NELSON_R6 | stock_temp_C | 2 | 8169 | 38.1 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3030 | high | NELSON_R6 | stock_temp_C | 2 | 8759 | 42.9 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3031 | high | NELSON_R6 | stock_temp_C | 2 | 9995 | 38.5 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3032 | high | NELSON_R6 | stock_temp_C | 2 | 11507 | 36.5 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3033 | high | NELSON_R6 | stock_temp_C | 2 | 12569 | 36.7 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3034 | high | NELSON_R6 | stock_temp_C | 2 | 15003 | 40.8 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3035 | high | NELSON_R6 | stock_temp_C | 2 | 15667 | 41.3 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3036 | high | NELSON_R6 | stock_temp_C | 2 | 17229 | 40.1 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3037 | high | NELSON_R6 | stock_temp_C | 2 | 19615 | 44.1 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3038 | high | NELSON_R6 | stock_temp_C | 2 | 19838 | 39.4 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3039 | high | NELSON_R6 | stock_temp_C | 2 | 19953 | 44.1 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3040 | high | NELSON_R6 | stock_temp_C | 2 | 20259 | 45.5 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3041 | high | NELSON_R6 | stock_temp_C | 2 | 20545 | 41.1 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3042 | high | NELSON_R6 | stock_temp_C | 2 | 20638 | 45.2 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3043 | high | NELSON_R6 | stock_temp_C | 2 | 20955 | 45.9 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3044 | high | NELSON_R6 | stock_temp_C | 2 | 21171 | 36.8 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3045 | high | NELSON_R6 | stock_temp_C | 2 | 21283 | 47.6 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3046 | high | NELSON_R6 | stock_temp_C | 2 | 21578 | 40.9 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3047 | high | NELSON_R6 | stock_temp_C | 2 | 21663 | 45.3 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3048 | high | NELSON_R6 | stock_temp_C | 2 | 21987 | 44.2 | stock_temp_C 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3049 | high | NELSON_R6 | vacuum_pump1_kPa | 2 | 103 | 41.5 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3050 | high | NELSON_R6 | vacuum_pump1_kPa | 2 | 390 | 45.5 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3051 | high | NELSON_R6 | vacuum_pump1_kPa | 2 | 593 | 47.1 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3052 | high | NELSON_R6 | vacuum_pump1_kPa | 2 | 1351 | 60.2 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3053 | high | NELSON_R6 | vacuum_pump1_kPa | 2 | 1710 | 47.3 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3054 | high | NELSON_R6 | vacuum_pump1_kPa | 2 | 2107 | 38.5 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3055 | high | NELSON_R6 | vacuum_pump1_kPa | 2 | 2241 | 44.4 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3056 | high | NELSON_R6 | vacuum_pump1_kPa | 2 | 2660 | 46.7 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3057 | high | NELSON_R6 | vacuum_pump1_kPa | 2 | 2764 | 45.1 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3058 | high | NELSON_R6 | vacuum_pump1_kPa | 2 | 3763 | 53.7 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3059 | high | NELSON_R6 | vacuum_pump1_kPa | 2 | 4623 | 59.5 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3060 | high | NELSON_R6 | vacuum_pump1_kPa | 2 | 4697 | 44 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3061 | high | NELSON_R6 | vacuum_pump1_kPa | 2 | 4898 | 58.6 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3062 | high | NELSON_R6 | vacuum_pump1_kPa | 2 | 4995 | 62.6 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3063 | high | NELSON_R6 | vacuum_pump1_kPa | 2 | 5148 | 57.4 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3064 | high | NELSON_R6 | vacuum_pump1_kPa | 2 | 6785 | 42.2 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3065 | high | NELSON_R6 | vacuum_pump1_kPa | 2 | 6985 | 38 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3066 | high | NELSON_R6 | vacuum_pump1_kPa | 2 | 7308 | 48.6 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3067 | high | NELSON_R6 | vacuum_pump1_kPa | 2 | 7504 | 53 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3068 | high | NELSON_R6 | vacuum_pump1_kPa | 2 | 7863 | 59 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3069 | high | NELSON_R6 | vacuum_pump1_kPa | 2 | 8068 | 47 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3070 | high | NELSON_R6 | vacuum_pump1_kPa | 2 | 8855 | 58.8 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3071 | high | NELSON_R6 | vacuum_pump1_kPa | 2 | 9082 | 65 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3072 | high | NELSON_R6 | vacuum_pump1_kPa | 2 | 9337 | 40.4 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3073 | high | NELSON_R6 | vacuum_pump1_kPa | 2 | 9456 | 42.4 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3074 | high | NELSON_R6 | vacuum_pump1_kPa | 2 | 9591 | 55.2 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3075 | high | NELSON_R6 | vacuum_pump1_kPa | 2 | 9652 | 41.9 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3076 | high | NELSON_R6 | vacuum_pump1_kPa | 2 | 10200 | 48.6 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3077 | high | NELSON_R6 | vacuum_pump1_kPa | 2 | 10502 | 58.1 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3078 | high | NELSON_R6 | vacuum_pump1_kPa | 2 | 10816 | 62.9 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3079 | high | NELSON_R6 | vacuum_pump1_kPa | 2 | 10903 | 58.6 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3080 | high | NELSON_R6 | vacuum_pump1_kPa | 2 | 11139 | 44.5 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3081 | high | NELSON_R6 | vacuum_pump1_kPa | 2 | 11216 | 57.6 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3082 | high | NELSON_R6 | vacuum_pump1_kPa | 2 | 11331 | 65.4 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3083 | high | NELSON_R6 | vacuum_pump1_kPa | 2 | 11625 | 60.2 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3084 | high | NELSON_R6 | vacuum_pump1_kPa | 2 | 12451 | 46.6 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3085 | high | NELSON_R6 | vacuum_pump1_kPa | 2 | 12727 | 57.2 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3086 | high | NELSON_R6 | vacuum_pump1_kPa | 2 | 12834 | 51.9 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3087 | high | NELSON_R6 | vacuum_pump1_kPa | 2 | 13060 | 42.1 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3088 | high | NELSON_R6 | vacuum_pump1_kPa | 2 | 13149 | 53.3 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3089 | high | NELSON_R6 | vacuum_pump1_kPa | 2 | 13214 | 42.5 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3090 | high | NELSON_R6 | vacuum_pump1_kPa | 2 | 13532 | 45.6 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3091 | high | NELSON_R6 | vacuum_pump1_kPa | 2 | 14259 | 62.2 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3092 | high | NELSON_R6 | vacuum_pump1_kPa | 2 | 14327 | 59.1 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3093 | high | NELSON_R6 | vacuum_pump1_kPa | 2 | 14828 | 59.9 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3094 | high | NELSON_R6 | vacuum_pump1_kPa | 2 | 15456 | 46.1 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3095 | high | NELSON_R6 | vacuum_pump1_kPa | 2 | 16087 | 57.3 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3096 | high | NELSON_R6 | vacuum_pump1_kPa | 2 | 16360 | 44 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3097 | high | NELSON_R6 | vacuum_pump1_kPa | 2 | 16497 | 58.2 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3098 | high | NELSON_R6 | vacuum_pump1_kPa | 2 | 17002 | 42.7 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3099 | high | NELSON_R6 | vacuum_pump1_kPa | 2 | 17817 | 45.7 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3100 | high | NELSON_R6 | vacuum_pump1_kPa | 2 | 17890 | 59.3 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3101 | high | NELSON_R6 | vacuum_pump1_kPa | 2 | 18995 | 46.2 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3102 | high | NELSON_R6 | vacuum_pump1_kPa | 2 | 19328 | 57.6 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3103 | high | NELSON_R6 | vacuum_pump1_kPa | 2 | 19554 | 61.8 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3104 | high | NELSON_R6 | vacuum_pump1_kPa | 2 | 19925 | 53 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3105 | high | NELSON_R6 | vacuum_pump1_kPa | 2 | 20358 | 52 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3106 | high | NELSON_R6 | vacuum_pump1_kPa | 2 | 20714 | 50.9 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3107 | high | NELSON_R6 | vacuum_pump1_kPa | 2 | 20801 | 55.6 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3108 | high | NELSON_R6 | vacuum_pump1_kPa | 2 | 20885 | 48.4 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3109 | high | NELSON_R6 | vacuum_pump1_kPa | 2 | 20957 | 57.7 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3110 | high | NELSON_R6 | vacuum_pump1_kPa | 2 | 21235 | 59.8 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3111 | high | NELSON_R6 | vacuum_pump1_kPa | 2 | 21364 | 38.1 | vacuum_pump1_kPa 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3112 | high | NELSON_R6 | white_water_consistency_pct | 2 | 42 | 0.853 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3113 | high | NELSON_R6 | white_water_consistency_pct | 2 | 315 | 1.007 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3114 | high | NELSON_R6 | white_water_consistency_pct | 2 | 2509 | 0.868 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3115 | high | NELSON_R6 | white_water_consistency_pct | 2 | 2891 | 0.922 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3116 | high | NELSON_R6 | white_water_consistency_pct | 2 | 3114 | 1.109 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3117 | high | NELSON_R6 | white_water_consistency_pct | 2 | 3329 | 1.044 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3118 | high | NELSON_R6 | white_water_consistency_pct | 2 | 3491 | 0.939 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3119 | high | NELSON_R6 | white_water_consistency_pct | 2 | 3576 | 1.032 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3120 | high | NELSON_R6 | white_water_consistency_pct | 2 | 3749 | 0.886 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3121 | high | NELSON_R6 | white_water_consistency_pct | 2 | 3823 | 1.07 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3122 | high | NELSON_R6 | white_water_consistency_pct | 2 | 3888 | 1.044 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3123 | high | NELSON_R6 | white_water_consistency_pct | 2 | 3951 | 0.9 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3124 | high | NELSON_R6 | white_water_consistency_pct | 2 | 4023 | 1.102 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3125 | high | NELSON_R6 | white_water_consistency_pct | 2 | 4156 | 1.012 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3126 | high | NELSON_R6 | white_water_consistency_pct | 2 | 4270 | 1.001 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3127 | high | NELSON_R6 | white_water_consistency_pct | 2 | 4364 | 0.999 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3128 | high | NELSON_R6 | white_water_consistency_pct | 2 | 4460 | 0.961 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3129 | high | NELSON_R6 | white_water_consistency_pct | 2 | 4782 | 0.901 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3130 | high | NELSON_R6 | white_water_consistency_pct | 2 | 5008 | 0.923 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3131 | high | NELSON_R6 | white_water_consistency_pct | 2 | 5273 | 0.953 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3132 | high | NELSON_R6 | white_water_consistency_pct | 2 | 6051 | 1.094 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3133 | high | NELSON_R6 | white_water_consistency_pct | 2 | 8720 | 0.962 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3134 | high | NELSON_R6 | white_water_consistency_pct | 2 | 8873 | 0.876 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3135 | high | NELSON_R6 | white_water_consistency_pct | 2 | 10561 | 1.232 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3136 | high | NELSON_R6 | white_water_consistency_pct | 2 | 11024 | 0.915 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3137 | high | NELSON_R6 | white_water_consistency_pct | 2 | 11286 | 0.928 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3138 | high | NELSON_R6 | white_water_consistency_pct | 2 | 11438 | 0.939 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3139 | high | NELSON_R6 | white_water_consistency_pct | 2 | 11676 | 0.992 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3140 | high | NELSON_R6 | white_water_consistency_pct | 2 | 11803 | 0.624 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3141 | high | NELSON_R6 | white_water_consistency_pct | 2 | 11888 | 1.093 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3142 | high | NELSON_R6 | white_water_consistency_pct | 2 | 12007 | 0.921 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3143 | high | NELSON_R6 | white_water_consistency_pct | 2 | 12086 | 1.033 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3144 | high | NELSON_R6 | white_water_consistency_pct | 2 | 12311 | 1.001 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3145 | high | NELSON_R6 | white_water_consistency_pct | 2 | 12416 | 0.96 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3146 | high | NELSON_R6 | white_water_consistency_pct | 2 | 12841 | 1.053 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3147 | high | NELSON_R6 | white_water_consistency_pct | 2 | 13425 | 0.933 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3148 | high | NELSON_R6 | white_water_consistency_pct | 2 | 13705 | 0.892 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3149 | high | NELSON_R6 | white_water_consistency_pct | 2 | 13867 | 1.012 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3150 | high | NELSON_R6 | white_water_consistency_pct | 2 | 14013 | 0.958 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3151 | high | NELSON_R6 | white_water_consistency_pct | 2 | 14678 | 0.845 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3152 | high | NELSON_R6 | white_water_consistency_pct | 2 | 14859 | 0.856 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3153 | high | NELSON_R6 | white_water_consistency_pct | 2 | 21987 | 1.213 | white_water_consistency_pct 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 3154 | warn | NELSON_R2 | fan_pump_speed_rpm | 1 | 16 | 896 | fan_pump_speed_rpm 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3155 | warn | NELSON_R2 | fan_pump_speed_rpm | 1 | 398 | 897.4 | fan_pump_speed_rpm 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3156 | warn | NELSON_R2 | fan_pump_speed_rpm | 1 | 471 | 899.3 | fan_pump_speed_rpm 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3157 | warn | NELSON_R2 | fan_pump_speed_rpm | 1 | 586 | 896.5 | fan_pump_speed_rpm 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3158 | warn | NELSON_R2 | fan_pump_speed_rpm | 1 | 686 | 898.1 | fan_pump_speed_rpm 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3159 | warn | NELSON_R2 | fan_pump_speed_rpm | 1 | 753 | 896 | fan_pump_speed_rpm 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3160 | warn | NELSON_R2 | fan_pump_speed_rpm | 1 | 938 | 894.6 | fan_pump_speed_rpm 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3161 | warn | NELSON_R2 | fan_pump_speed_rpm | 1 | 1025 | 897.9 | fan_pump_speed_rpm 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3162 | warn | NELSON_R2 | fan_pump_speed_rpm | 1 | 1138 | 898.8 | fan_pump_speed_rpm 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3163 | warn | NELSON_R2 | fan_pump_speed_rpm | 1 | 1419 | 905.3 | fan_pump_speed_rpm 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3164 | warn | NELSON_R2 | fan_pump_speed_rpm | 1 | 1514 | 895 | fan_pump_speed_rpm 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3165 | warn | NELSON_R2 | fan_pump_speed_rpm | 1 | 1962 | 905 | fan_pump_speed_rpm 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3166 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 8 | 24.03 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3167 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 74 | 18.22 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3168 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 175 | 18.13 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3169 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 310 | 18.11 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3170 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 487 | 18.22 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3171 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 798 | 18.26 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3172 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 971 | 17.87 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3173 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 1133 | 20.79 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3174 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 1202 | 24.54 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3175 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 1309 | 21.12 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3176 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 1496 | 21.21 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3177 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 1596 | 18.52 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3178 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 1748 | 19.15 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3179 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 1855 | 19.03 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3180 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 2029 | 25.63 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3181 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 2199 | 26.34 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3182 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 2383 | 25.89 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3183 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 2837 | 26.85 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3184 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 2921 | 19.73 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3185 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 4345 | 24.31 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3186 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 4425 | 28.37 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3187 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 4529 | 28.41 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3188 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 4776 | 25.4 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3189 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 5190 | 25.57 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3190 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 5357 | 25.16 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3191 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 5535 | 29.7 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3192 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 5599 | 22.17 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3193 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 6315 | 30.14 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3194 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 6668 | 22.98 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3195 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 7029 | 31.55 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3196 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 7279 | 28.13 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3197 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 7407 | 27.75 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3198 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 8262 | 33.25 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3199 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 9308 | 26.04 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3200 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 9584 | 34.05 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3201 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 10300 | 23.86 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3202 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 10661 | 24.32 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3203 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 10900 | 28.55 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3204 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 11228 | 27.12 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3205 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 11465 | 23.14 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3206 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 11627 | 23.44 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3207 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 12440 | 21.36 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3208 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 12770 | 29.94 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3209 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 13124 | 22.52 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3210 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 13536 | 30.07 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3211 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 13725 | 22.91 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3212 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 14411 | 23.17 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3213 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 14928 | 23.66 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3214 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 15250 | 27.34 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3215 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 15322 | 23.58 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3216 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 15399 | 27.26 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3217 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 15464 | 27.52 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3218 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 16342 | 32.02 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3219 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 17247 | 25.16 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3220 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 17460 | 29.47 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3221 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 17701 | 29.25 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3222 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 17952 | 26.01 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3223 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 18039 | 34.68 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3224 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 18644 | 29.16 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3225 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 18957 | 30.41 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3226 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 19452 | 31.65 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3227 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 19999 | 37.69 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3228 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 20096 | 28.03 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3229 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 20256 | 32.67 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3230 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 20408 | 37.69 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3231 | warn | NELSON_R2 | headbox_pressure_kPa | 1 | 21626 | 29.39 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3232 | warn | NELSON_R2 | jet_to_wire_ratio | 1 | 182 | 1.069 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3233 | warn | NELSON_R2 | jet_to_wire_ratio | 1 | 308 | 1.016 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3234 | warn | NELSON_R2 | jet_to_wire_ratio | 1 | 463 | 1.025 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3235 | warn | NELSON_R2 | jet_to_wire_ratio | 1 | 1098 | 0.995 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3236 | warn | NELSON_R2 | jet_to_wire_ratio | 1 | 1484 | 1.018 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3237 | warn | NELSON_R2 | jet_to_wire_ratio | 1 | 1711 | 0.999 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3238 | warn | NELSON_R2 | jet_to_wire_ratio | 1 | 1873 | 1 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3239 | warn | NELSON_R2 | jet_to_wire_ratio | 1 | 2698 | 1.08 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3240 | warn | NELSON_R2 | jet_to_wire_ratio | 1 | 2954 | 1.02 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3241 | warn | NELSON_R2 | jet_to_wire_ratio | 1 | 3588 | 1.03 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3242 | warn | NELSON_R2 | jet_to_wire_ratio | 1 | 4279 | 1.038 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3243 | warn | NELSON_R2 | jet_to_wire_ratio | 1 | 4402 | 0.979 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3244 | warn | NELSON_R2 | jet_to_wire_ratio | 1 | 4912 | 1.043 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3245 | warn | NELSON_R2 | jet_to_wire_ratio | 1 | 6474 | 0.996 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3246 | warn | NELSON_R2 | jet_to_wire_ratio | 1 | 6929 | 1.038 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3247 | warn | NELSON_R2 | jet_to_wire_ratio | 1 | 8422 | 0.961 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3248 | warn | NELSON_R2 | jet_to_wire_ratio | 1 | 8991 | 1.032 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3249 | warn | NELSON_R2 | jet_to_wire_ratio | 1 | 9598 | 1.011 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3250 | warn | NELSON_R2 | jet_to_wire_ratio | 1 | 10273 | 1.002 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3251 | warn | NELSON_R2 | jet_to_wire_ratio | 1 | 10791 | 1.045 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3252 | warn | NELSON_R2 | jet_to_wire_ratio | 1 | 11117 | 1.026 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3253 | warn | NELSON_R2 | jet_to_wire_ratio | 1 | 12048 | 1.038 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3254 | warn | NELSON_R2 | jet_to_wire_ratio | 1 | 12639 | 1.049 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3255 | warn | NELSON_R2 | jet_to_wire_ratio | 1 | 12843 | 1.024 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3256 | warn | NELSON_R2 | jet_to_wire_ratio | 1 | 13048 | 1.028 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3257 | warn | NELSON_R2 | jet_to_wire_ratio | 1 | 13689 | 0.99 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3258 | warn | NELSON_R2 | jet_to_wire_ratio | 1 | 14259 | 1.007 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3259 | warn | NELSON_R2 | jet_to_wire_ratio | 1 | 14463 | 1.029 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3260 | warn | NELSON_R2 | jet_to_wire_ratio | 1 | 14525 | 1.047 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3261 | warn | NELSON_R2 | jet_to_wire_ratio | 1 | 15175 | 1.028 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3262 | warn | NELSON_R2 | jet_to_wire_ratio | 1 | 15261 | 0.969 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3263 | warn | NELSON_R2 | jet_to_wire_ratio | 1 | 15869 | 0.985 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3264 | warn | NELSON_R2 | jet_to_wire_ratio | 1 | 16140 | 0.978 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3265 | warn | NELSON_R2 | jet_to_wire_ratio | 1 | 16347 | 0.994 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3266 | warn | NELSON_R2 | jet_to_wire_ratio | 1 | 16889 | 1.002 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3267 | warn | NELSON_R2 | jet_to_wire_ratio | 1 | 17022 | 0.942 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3268 | warn | NELSON_R2 | jet_to_wire_ratio | 1 | 17572 | 0.988 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3269 | warn | NELSON_R2 | jet_to_wire_ratio | 1 | 18463 | 1.027 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3270 | warn | NELSON_R2 | jet_to_wire_ratio | 1 | 18652 | 1.037 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3271 | warn | NELSON_R2 | jet_to_wire_ratio | 1 | 19467 | 0.968 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3272 | warn | NELSON_R2 | jet_to_wire_ratio | 1 | 20756 | 1.004 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3273 | warn | NELSON_R2 | jet_to_wire_ratio | 1 | 20901 | 1.003 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3274 | warn | NELSON_R2 | jet_to_wire_ratio | 1 | 21468 | 0.997 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3275 | warn | NELSON_R2 | machine_speed_mmin | 1 | 8 | 1684 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3276 | warn | NELSON_R2 | machine_speed_mmin | 1 | 105 | 1506 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3277 | warn | NELSON_R2 | machine_speed_mmin | 1 | 262 | 1696 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3278 | warn | NELSON_R2 | machine_speed_mmin | 1 | 413 | 1692 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3279 | warn | NELSON_R2 | machine_speed_mmin | 1 | 475 | 1319 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3280 | warn | NELSON_R2 | machine_speed_mmin | 1 | 575 | 1689 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3281 | warn | NELSON_R2 | machine_speed_mmin | 1 | 731 | 1686 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3282 | warn | NELSON_R2 | machine_speed_mmin | 1 | 792 | 1311 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3283 | warn | NELSON_R2 | machine_speed_mmin | 1 | 869 | 1510 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3284 | warn | NELSON_R2 | machine_speed_mmin | 1 | 1050 | 1685 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3285 | warn | NELSON_R2 | machine_speed_mmin | 1 | 1201 | 1715 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3286 | warn | NELSON_R2 | machine_speed_mmin | 1 | 1372 | 1694 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3287 | warn | NELSON_R2 | machine_speed_mmin | 1 | 1534 | 1697 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3288 | warn | NELSON_R2 | machine_speed_mmin | 1 | 1687 | 1697 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3289 | warn | NELSON_R2 | machine_speed_mmin | 1 | 1814 | 1702 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3290 | warn | NELSON_R2 | machine_speed_mmin | 1 | 2000 | 1706 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3291 | warn | NELSON_R2 | machine_speed_mmin | 1 | 2134 | 1702 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3292 | warn | NELSON_R2 | machine_speed_mmin | 1 | 2211 | 1316 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3293 | warn | NELSON_R2 | machine_speed_mmin | 1 | 2308 | 1502 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3294 | warn | NELSON_R2 | machine_speed_mmin | 1 | 2413 | 1338 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3295 | warn | NELSON_R2 | machine_speed_mmin | 1 | 2521 | 1726 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3296 | warn | NELSON_R2 | machine_speed_mmin | 1 | 2670 | 1696 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3297 | warn | NELSON_R2 | machine_speed_mmin | 1 | 2839 | 1687 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3298 | warn | NELSON_R2 | machine_speed_mmin | 1 | 2979 | 1706 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3299 | warn | NELSON_R2 | machine_speed_mmin | 1 | 3104 | 1509 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3300 | warn | NELSON_R2 | machine_speed_mmin | 1 | 3307 | 1510 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3301 | warn | NELSON_R2 | machine_speed_mmin | 1 | 3400 | 1334 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3302 | warn | NELSON_R2 | machine_speed_mmin | 1 | 3499 | 1708 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3303 | warn | NELSON_R2 | machine_speed_mmin | 1 | 3661 | 1673 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3304 | warn | NELSON_R2 | machine_speed_mmin | 1 | 3738 | 1319 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3305 | warn | NELSON_R2 | machine_speed_mmin | 1 | 3877 | 1702 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3306 | warn | NELSON_R2 | machine_speed_mmin | 1 | 4035 | 1714 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3307 | warn | NELSON_R2 | machine_speed_mmin | 1 | 4104 | 1326 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3308 | warn | NELSON_R2 | machine_speed_mmin | 1 | 4232 | 1727 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3309 | warn | NELSON_R2 | machine_speed_mmin | 1 | 4293 | 1339 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3310 | warn | NELSON_R2 | machine_speed_mmin | 1 | 4384 | 1705 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3311 | warn | NELSON_R2 | machine_speed_mmin | 1 | 4518 | 1703 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3312 | warn | NELSON_R2 | machine_speed_mmin | 1 | 4660 | 1705 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3313 | warn | NELSON_R2 | machine_speed_mmin | 1 | 4761 | 1505 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3314 | warn | NELSON_R2 | machine_speed_mmin | 1 | 4989 | 1344 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3315 | warn | NELSON_R2 | machine_speed_mmin | 1 | 5095 | 1674 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3316 | warn | NELSON_R2 | machine_speed_mmin | 1 | 5215 | 1701 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3317 | warn | NELSON_R2 | machine_speed_mmin | 1 | 5392 | 1721 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3318 | warn | NELSON_R2 | machine_speed_mmin | 1 | 5454 | 1302 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3319 | warn | NELSON_R2 | machine_speed_mmin | 1 | 5533 | 1693 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3320 | warn | NELSON_R2 | machine_speed_mmin | 1 | 5676 | 1507 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3321 | warn | NELSON_R2 | machine_speed_mmin | 1 | 5839 | 1698 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3322 | warn | NELSON_R2 | machine_speed_mmin | 1 | 5901 | 1319 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3323 | warn | NELSON_R2 | machine_speed_mmin | 1 | 6001 | 1695 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3324 | warn | NELSON_R2 | machine_speed_mmin | 1 | 6123 | 1682 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3325 | warn | NELSON_R2 | machine_speed_mmin | 1 | 6314 | 1705 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3326 | warn | NELSON_R2 | machine_speed_mmin | 1 | 6467 | 1691 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3327 | warn | NELSON_R2 | machine_speed_mmin | 1 | 6620 | 1672 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3328 | warn | NELSON_R2 | machine_speed_mmin | 1 | 6775 | 1691 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3329 | warn | NELSON_R2 | machine_speed_mmin | 1 | 6869 | 1714 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3330 | warn | NELSON_R2 | machine_speed_mmin | 1 | 7029 | 1694 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3331 | warn | NELSON_R2 | machine_speed_mmin | 1 | 7300 | 1695 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3332 | warn | NELSON_R2 | machine_speed_mmin | 1 | 7464 | 1674 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3333 | warn | NELSON_R2 | machine_speed_mmin | 1 | 7609 | 1675 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3334 | warn | NELSON_R2 | machine_speed_mmin | 1 | 7788 | 1701 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3335 | warn | NELSON_R2 | machine_speed_mmin | 1 | 7926 | 1695 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3336 | warn | NELSON_R2 | machine_speed_mmin | 1 | 8049 | 1507 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3337 | warn | NELSON_R2 | machine_speed_mmin | 1 | 8237 | 1699 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3338 | warn | NELSON_R2 | machine_speed_mmin | 1 | 8409 | 1743 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3339 | warn | NELSON_R2 | machine_speed_mmin | 1 | 8587 | 1708 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3340 | warn | NELSON_R2 | machine_speed_mmin | 1 | 8683 | 1690 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3341 | warn | NELSON_R2 | machine_speed_mmin | 1 | 8806 | 1709 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3342 | warn | NELSON_R2 | machine_speed_mmin | 1 | 8944 | 1694 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3343 | warn | NELSON_R2 | machine_speed_mmin | 1 | 9075 | 1700 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3344 | warn | NELSON_R2 | machine_speed_mmin | 1 | 9216 | 1710 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3345 | warn | NELSON_R2 | machine_speed_mmin | 1 | 9286 | 1320 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3346 | warn | NELSON_R2 | machine_speed_mmin | 1 | 9408 | 1697 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3347 | warn | NELSON_R2 | machine_speed_mmin | 1 | 9555 | 1722 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3348 | warn | NELSON_R2 | machine_speed_mmin | 1 | 9735 | 1680 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3349 | warn | NELSON_R2 | machine_speed_mmin | 1 | 9873 | 1696 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3350 | warn | NELSON_R2 | machine_speed_mmin | 1 | 9950 | 1309 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3351 | warn | NELSON_R2 | machine_speed_mmin | 1 | 10061 | 1713 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3352 | warn | NELSON_R2 | machine_speed_mmin | 1 | 10209 | 1715 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3353 | warn | NELSON_R2 | machine_speed_mmin | 1 | 10286 | 1311 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3354 | warn | NELSON_R2 | machine_speed_mmin | 1 | 10364 | 1497 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3355 | warn | NELSON_R2 | machine_speed_mmin | 1 | 10559 | 1698 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3356 | warn | NELSON_R2 | machine_speed_mmin | 1 | 10682 | 1702 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3357 | warn | NELSON_R2 | machine_speed_mmin | 1 | 10869 | 1460 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3358 | warn | NELSON_R2 | machine_speed_mmin | 1 | 11049 | 1698 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3359 | warn | NELSON_R2 | machine_speed_mmin | 1 | 11191 | 1708 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3360 | warn | NELSON_R2 | machine_speed_mmin | 1 | 11253 | 1314 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3361 | warn | NELSON_R2 | machine_speed_mmin | 1 | 11369 | 1695 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3362 | warn | NELSON_R2 | machine_speed_mmin | 1 | 11504 | 1697 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3363 | warn | NELSON_R2 | machine_speed_mmin | 1 | 11640 | 1509 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3364 | warn | NELSON_R2 | machine_speed_mmin | 1 | 11810 | 1677 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3365 | warn | NELSON_R2 | machine_speed_mmin | 1 | 11873 | 1317 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3366 | warn | NELSON_R2 | machine_speed_mmin | 1 | 11952 | 1692 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3367 | warn | NELSON_R2 | machine_speed_mmin | 1 | 12076 | 1718 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3368 | warn | NELSON_R2 | machine_speed_mmin | 1 | 12144 | 1323 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3369 | warn | NELSON_R2 | machine_speed_mmin | 1 | 12233 | 1705 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3370 | warn | NELSON_R2 | machine_speed_mmin | 1 | 12386 | 1698 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3371 | warn | NELSON_R2 | machine_speed_mmin | 1 | 12571 | 1702 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3372 | warn | NELSON_R2 | machine_speed_mmin | 1 | 12648 | 1330 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3373 | warn | NELSON_R2 | machine_speed_mmin | 1 | 12764 | 1705 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3374 | warn | NELSON_R2 | machine_speed_mmin | 1 | 12912 | 1709 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3375 | warn | NELSON_R2 | machine_speed_mmin | 1 | 13070 | 1710 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3376 | warn | NELSON_R2 | machine_speed_mmin | 1 | 13210 | 1756 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3377 | warn | NELSON_R2 | machine_speed_mmin | 1 | 13306 | 1695 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3378 | warn | NELSON_R2 | machine_speed_mmin | 1 | 13372 | 1310 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3379 | warn | NELSON_R2 | machine_speed_mmin | 1 | 13490 | 1724 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3380 | warn | NELSON_R2 | machine_speed_mmin | 1 | 13571 | 1334 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3381 | warn | NELSON_R2 | machine_speed_mmin | 1 | 13645 | 1704 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3382 | warn | NELSON_R2 | machine_speed_mmin | 1 | 13716 | 1314 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3383 | warn | NELSON_R2 | machine_speed_mmin | 1 | 13822 | 1508 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3384 | warn | NELSON_R2 | machine_speed_mmin | 1 | 13971 | 1705 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3385 | warn | NELSON_R2 | machine_speed_mmin | 1 | 14171 | 1687 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3386 | warn | NELSON_R2 | machine_speed_mmin | 1 | 14332 | 1715 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3387 | warn | NELSON_R2 | machine_speed_mmin | 1 | 14502 | 1692 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3388 | warn | NELSON_R2 | machine_speed_mmin | 1 | 14663 | 1699 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3389 | warn | NELSON_R2 | machine_speed_mmin | 1 | 14745 | 1324 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3390 | warn | NELSON_R2 | machine_speed_mmin | 1 | 14810 | 1706 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3391 | warn | NELSON_R2 | machine_speed_mmin | 1 | 14875 | 1385 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3392 | warn | NELSON_R2 | machine_speed_mmin | 1 | 14961 | 1501 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3393 | warn | NELSON_R2 | machine_speed_mmin | 1 | 15051 | 1305 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3394 | warn | NELSON_R2 | machine_speed_mmin | 1 | 15134 | 1706 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3395 | warn | NELSON_R2 | machine_speed_mmin | 1 | 15258 | 1501 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3396 | warn | NELSON_R2 | machine_speed_mmin | 1 | 15475 | 1712 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3397 | warn | NELSON_R2 | machine_speed_mmin | 1 | 15637 | 1690 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3398 | warn | NELSON_R2 | machine_speed_mmin | 1 | 15702 | 1312 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3399 | warn | NELSON_R2 | machine_speed_mmin | 1 | 15778 | 1504 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3400 | warn | NELSON_R2 | machine_speed_mmin | 1 | 15867 | 1317 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3401 | warn | NELSON_R2 | machine_speed_mmin | 1 | 16005 | 1682 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3402 | warn | NELSON_R2 | machine_speed_mmin | 1 | 16067 | 1318 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3403 | warn | NELSON_R2 | machine_speed_mmin | 1 | 16181 | 1689 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3404 | warn | NELSON_R2 | machine_speed_mmin | 1 | 16334 | 1693 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3405 | warn | NELSON_R2 | machine_speed_mmin | 1 | 16468 | 1701 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3406 | warn | NELSON_R2 | machine_speed_mmin | 1 | 16604 | 1512 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3407 | warn | NELSON_R2 | machine_speed_mmin | 1 | 16797 | 1502 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3408 | warn | NELSON_R2 | machine_speed_mmin | 1 | 16889 | 1330 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3409 | warn | NELSON_R2 | machine_speed_mmin | 1 | 16982 | 1680 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3410 | warn | NELSON_R2 | machine_speed_mmin | 1 | 17134 | 1704 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3411 | warn | NELSON_R2 | machine_speed_mmin | 1 | 17198 | 1312 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3412 | warn | NELSON_R2 | machine_speed_mmin | 1 | 17345 | 1511 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3413 | warn | NELSON_R2 | machine_speed_mmin | 1 | 17535 | 1700 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3414 | warn | NELSON_R2 | machine_speed_mmin | 1 | 17613 | 1314 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3415 | warn | NELSON_R2 | machine_speed_mmin | 1 | 17713 | 1701 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3416 | warn | NELSON_R2 | machine_speed_mmin | 1 | 17879 | 1690 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3417 | warn | NELSON_R2 | machine_speed_mmin | 1 | 18032 | 1710 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3418 | warn | NELSON_R2 | machine_speed_mmin | 1 | 18178 | 1755 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3419 | warn | NELSON_R2 | machine_speed_mmin | 1 | 18326 | 1726 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3420 | warn | NELSON_R2 | machine_speed_mmin | 1 | 18402 | 1318 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3421 | warn | NELSON_R2 | machine_speed_mmin | 1 | 18524 | 1692 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3422 | warn | NELSON_R2 | machine_speed_mmin | 1 | 18676 | 1506 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3423 | warn | NELSON_R2 | machine_speed_mmin | 1 | 18848 | 1708 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3424 | warn | NELSON_R2 | machine_speed_mmin | 1 | 18916 | 1312 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3425 | warn | NELSON_R2 | machine_speed_mmin | 1 | 19001 | 1704 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3426 | warn | NELSON_R2 | machine_speed_mmin | 1 | 19135 | 1686 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3427 | warn | NELSON_R2 | machine_speed_mmin | 1 | 19307 | 1699 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3428 | warn | NELSON_R2 | machine_speed_mmin | 1 | 19461 | 1502 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3429 | warn | NELSON_R2 | machine_speed_mmin | 1 | 19634 | 1689 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3430 | warn | NELSON_R2 | machine_speed_mmin | 1 | 19713 | 1334 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3431 | warn | NELSON_R2 | machine_speed_mmin | 1 | 19840 | 1714 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3432 | warn | NELSON_R2 | machine_speed_mmin | 1 | 19997 | 1711 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3433 | warn | NELSON_R2 | machine_speed_mmin | 1 | 20153 | 1687 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3434 | warn | NELSON_R2 | machine_speed_mmin | 1 | 20216 | 1309 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3435 | warn | NELSON_R2 | machine_speed_mmin | 1 | 20290 | 1693 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3436 | warn | NELSON_R2 | machine_speed_mmin | 1 | 20395 | 1694 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3437 | warn | NELSON_R2 | machine_speed_mmin | 1 | 20530 | 1705 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3438 | warn | NELSON_R2 | machine_speed_mmin | 1 | 20706 | 1708 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3439 | warn | NELSON_R2 | machine_speed_mmin | 1 | 20771 | 1313 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3440 | warn | NELSON_R2 | machine_speed_mmin | 1 | 20867 | 1702 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3441 | warn | NELSON_R2 | machine_speed_mmin | 1 | 21090 | 1740 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3442 | warn | NELSON_R2 | machine_speed_mmin | 1 | 21217 | 1710 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3443 | warn | NELSON_R2 | machine_speed_mmin | 1 | 21352 | 1698 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3444 | warn | NELSON_R2 | machine_speed_mmin | 1 | 21417 | 1316 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3445 | warn | NELSON_R2 | machine_speed_mmin | 1 | 21504 | 1632 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3446 | warn | NELSON_R2 | machine_speed_mmin | 1 | 21573 | 1338 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3447 | warn | NELSON_R2 | machine_speed_mmin | 1 | 21683 | 1699 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3448 | warn | NELSON_R2 | stock_temp_C | 1 | 8 | 50.2 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3449 | warn | NELSON_R2 | stock_temp_C | 1 | 152 | 48.4 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3450 | warn | NELSON_R2 | stock_temp_C | 1 | 279 | 45.7 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3451 | warn | NELSON_R2 | stock_temp_C | 1 | 556 | 45.5 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3452 | warn | NELSON_R2 | stock_temp_C | 1 | 673 | 45.6 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3453 | warn | NELSON_R2 | stock_temp_C | 1 | 925 | 44.5 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3454 | warn | NELSON_R2 | stock_temp_C | 1 | 1041 | 46 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3455 | warn | NELSON_R2 | stock_temp_C | 1 | 1258 | 45.9 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3456 | warn | NELSON_R2 | stock_temp_C | 1 | 1427 | 47.6 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3457 | warn | NELSON_R2 | stock_temp_C | 1 | 1576 | 47.9 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3458 | warn | NELSON_R2 | stock_temp_C | 1 | 1746 | 45.7 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3459 | warn | NELSON_R2 | stock_temp_C | 1 | 1928 | 47.9 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3460 | warn | NELSON_R2 | stock_temp_C | 1 | 2083 | 44.7 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3461 | warn | NELSON_R2 | stock_temp_C | 1 | 2253 | 47.3 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3462 | warn | NELSON_R2 | stock_temp_C | 1 | 2376 | 41.7 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3463 | warn | NELSON_R2 | stock_temp_C | 1 | 2471 | 46.1 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3464 | warn | NELSON_R2 | stock_temp_C | 1 | 2601 | 48.4 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3465 | warn | NELSON_R2 | stock_temp_C | 1 | 2872 | 47.7 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3466 | warn | NELSON_R2 | stock_temp_C | 1 | 3005 | 45 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3467 | warn | NELSON_R2 | stock_temp_C | 1 | 3144 | 44.5 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3468 | warn | NELSON_R2 | stock_temp_C | 1 | 3241 | 48.1 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3469 | warn | NELSON_R2 | stock_temp_C | 1 | 3309 | 47.6 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3470 | warn | NELSON_R2 | stock_temp_C | 1 | 3579 | 48.6 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3471 | warn | NELSON_R2 | stock_temp_C | 1 | 3968 | 47.7 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3472 | warn | NELSON_R2 | stock_temp_C | 1 | 4362 | 47.6 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3473 | warn | NELSON_R2 | stock_temp_C | 1 | 4670 | 45.7 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3474 | warn | NELSON_R2 | stock_temp_C | 1 | 4755 | 46.7 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3475 | warn | NELSON_R2 | stock_temp_C | 1 | 5009 | 44.1 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3476 | warn | NELSON_R2 | stock_temp_C | 1 | 5121 | 46.3 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3477 | warn | NELSON_R2 | stock_temp_C | 1 | 5403 | 46.3 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3478 | warn | NELSON_R2 | stock_temp_C | 1 | 5764 | 43.9 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3479 | warn | NELSON_R2 | stock_temp_C | 1 | 6135 | 45.4 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3480 | warn | NELSON_R2 | stock_temp_C | 1 | 6436 | 43.2 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3481 | warn | NELSON_R2 | stock_temp_C | 1 | 6811 | 43.8 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3482 | warn | NELSON_R2 | stock_temp_C | 1 | 7198 | 45.2 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3483 | warn | NELSON_R2 | stock_temp_C | 1 | 7282 | 42.2 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3484 | warn | NELSON_R2 | stock_temp_C | 1 | 7934 | 43.2 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3485 | warn | NELSON_R2 | stock_temp_C | 1 | 8056 | 39 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3486 | warn | NELSON_R2 | stock_temp_C | 1 | 8315 | 43.2 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3487 | warn | NELSON_R2 | stock_temp_C | 1 | 8590 | 41.9 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3488 | warn | NELSON_R2 | stock_temp_C | 1 | 8693 | 39.9 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3489 | warn | NELSON_R2 | stock_temp_C | 1 | 10285 | 38.2 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3490 | warn | NELSON_R2 | stock_temp_C | 1 | 10575 | 35.3 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3491 | warn | NELSON_R2 | stock_temp_C | 1 | 11032 | 41 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3492 | warn | NELSON_R2 | stock_temp_C | 1 | 11454 | 40.5 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3493 | warn | NELSON_R2 | stock_temp_C | 1 | 13088 | 36.2 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3494 | warn | NELSON_R2 | stock_temp_C | 1 | 13440 | 36.2 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3495 | warn | NELSON_R2 | stock_temp_C | 1 | 13769 | 34.8 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3496 | warn | NELSON_R2 | stock_temp_C | 1 | 15675 | 39.4 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3497 | warn | NELSON_R2 | stock_temp_C | 1 | 16038 | 39.8 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3498 | warn | NELSON_R2 | stock_temp_C | 1 | 16238 | 35.2 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3499 | warn | NELSON_R2 | stock_temp_C | 1 | 16556 | 38.9 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3500 | warn | NELSON_R2 | stock_temp_C | 1 | 17155 | 43.5 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3501 | warn | NELSON_R2 | stock_temp_C | 1 | 17279 | 38.3 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3502 | warn | NELSON_R2 | stock_temp_C | 1 | 18179 | 40.7 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3503 | warn | NELSON_R2 | stock_temp_C | 1 | 18241 | 43.3 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3504 | warn | NELSON_R2 | stock_temp_C | 1 | 18673 | 42.9 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3505 | warn | NELSON_R2 | stock_temp_C | 1 | 19165 | 38.2 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3506 | warn | NELSON_R2 | stock_temp_C | 1 | 19698 | 44.6 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3507 | warn | NELSON_R2 | stock_temp_C | 1 | 20119 | 46.5 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3508 | warn | NELSON_R2 | stock_temp_C | 1 | 20496 | 45.8 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3509 | warn | NELSON_R2 | stock_temp_C | 1 | 20596 | 42.3 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3510 | warn | NELSON_R2 | stock_temp_C | 1 | 20826 | 45.9 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3511 | warn | NELSON_R2 | stock_temp_C | 1 | 21184 | 46.8 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3512 | warn | NELSON_R2 | stock_temp_C | 1 | 21350 | 41.3 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3513 | warn | NELSON_R2 | stock_temp_C | 1 | 21521 | 46.1 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3514 | warn | NELSON_R2 | stock_temp_C | 1 | 21635 | 46.6 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3515 | warn | NELSON_R2 | vacuum_pump1_kPa | 1 | 484 | 65.9 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3516 | warn | NELSON_R2 | vacuum_pump1_kPa | 1 | 741 | 51.9 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3517 | warn | NELSON_R2 | vacuum_pump1_kPa | 1 | 957 | 54.6 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3518 | warn | NELSON_R2 | vacuum_pump1_kPa | 1 | 1346 | 49.1 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3519 | warn | NELSON_R2 | vacuum_pump1_kPa | 1 | 2064 | 55.1 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3520 | warn | NELSON_R2 | vacuum_pump1_kPa | 1 | 3927 | 60.5 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3521 | warn | NELSON_R2 | vacuum_pump1_kPa | 1 | 4052 | 50.6 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3522 | warn | NELSON_R2 | vacuum_pump1_kPa | 1 | 4397 | 54.6 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3523 | warn | NELSON_R2 | vacuum_pump1_kPa | 1 | 4769 | 57.8 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3524 | warn | NELSON_R2 | vacuum_pump1_kPa | 1 | 5121 | 42.5 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3525 | warn | NELSON_R2 | vacuum_pump1_kPa | 1 | 5335 | 47.4 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3526 | warn | NELSON_R2 | vacuum_pump1_kPa | 1 | 5629 | 58.6 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3527 | warn | NELSON_R2 | vacuum_pump1_kPa | 1 | 5814 | 49.4 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3528 | warn | NELSON_R2 | vacuum_pump1_kPa | 1 | 6506 | 53.1 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3529 | warn | NELSON_R2 | vacuum_pump1_kPa | 1 | 6605 | 52.7 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3530 | warn | NELSON_R2 | vacuum_pump1_kPa | 1 | 6803 | 52.1 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3531 | warn | NELSON_R2 | vacuum_pump1_kPa | 1 | 7304 | 49.6 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3532 | warn | NELSON_R2 | vacuum_pump1_kPa | 1 | 7680 | 47.2 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3533 | warn | NELSON_R2 | vacuum_pump1_kPa | 1 | 8000 | 54.3 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3534 | warn | NELSON_R2 | vacuum_pump1_kPa | 1 | 9155 | 57.3 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3535 | warn | NELSON_R2 | vacuum_pump1_kPa | 1 | 11301 | 47.1 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3536 | warn | NELSON_R2 | vacuum_pump1_kPa | 1 | 11483 | 51.3 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3537 | warn | NELSON_R2 | vacuum_pump1_kPa | 1 | 11636 | 52.4 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3538 | warn | NELSON_R2 | vacuum_pump1_kPa | 1 | 11970 | 57.7 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3539 | warn | NELSON_R2 | vacuum_pump1_kPa | 1 | 13806 | 52.8 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3540 | warn | NELSON_R2 | vacuum_pump1_kPa | 1 | 14838 | 59.9 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3541 | warn | NELSON_R2 | vacuum_pump1_kPa | 1 | 15117 | 43.3 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3542 | warn | NELSON_R2 | vacuum_pump1_kPa | 1 | 15537 | 56.6 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3543 | warn | NELSON_R2 | vacuum_pump1_kPa | 1 | 16276 | 41.2 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3544 | warn | NELSON_R2 | vacuum_pump1_kPa | 1 | 16952 | 48.8 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3545 | warn | NELSON_R2 | vacuum_pump1_kPa | 1 | 17745 | 53.8 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3546 | warn | NELSON_R2 | vacuum_pump1_kPa | 1 | 18411 | 51.4 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3547 | warn | NELSON_R2 | vacuum_pump1_kPa | 1 | 18796 | 55.8 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3548 | warn | NELSON_R2 | vacuum_pump1_kPa | 1 | 19254 | 52.8 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3549 | warn | NELSON_R2 | vacuum_pump1_kPa | 1 | 19847 | 49.1 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3550 | warn | NELSON_R2 | vacuum_pump1_kPa | 1 | 20100 | 50.9 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3551 | warn | NELSON_R2 | vacuum_pump1_kPa | 1 | 20708 | 53.9 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3552 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 8 | 0.963 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3553 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 1168 | 1.019 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3554 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 1498 | 0.935 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3555 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 1603 | 0.927 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3556 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 1781 | 0.945 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3557 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 1849 | 0.935 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3558 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 2565 | 1.052 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3559 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 2835 | 1.096 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3560 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 3032 | 1.069 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3561 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 3159 | 1.089 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3562 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 3431 | 1.048 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3563 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 3506 | 0.971 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3564 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 3649 | 1.05 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3565 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 3767 | 1.136 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3566 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 4042 | 0.964 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3567 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 4272 | 1.205 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3568 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 4413 | 1.09 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3569 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 4640 | 1.061 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3570 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 4731 | 1.052 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3571 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 4830 | 0.996 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3572 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 5051 | 1.047 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3573 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 5137 | 1.024 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3574 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 5215 | 1.049 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3575 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 5365 | 1.108 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3576 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 5604 | 1.069 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3577 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 5786 | 1.113 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3578 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 6135 | 1.122 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3579 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 6220 | 1.024 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3580 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 6370 | 1.015 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3581 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 6512 | 1.14 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3582 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 6655 | 1.042 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3583 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 7006 | 1.248 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3584 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 7179 | 1.116 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3585 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 7259 | 1.098 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3586 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 7585 | 1.179 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3587 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 7721 | 1.158 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3588 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 7836 | 1.127 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3589 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 7980 | 1.209 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3590 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 8388 | 1.175 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3591 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 8663 | 1.122 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3592 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 8952 | 1.289 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3593 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 9147 | 1.171 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3594 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 9209 | 1.174 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3595 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 9314 | 1.186 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3596 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 9539 | 1.191 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3597 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 9617 | 1.097 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3598 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 9832 | 1.011 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3599 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 10047 | 1.077 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3600 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 10405 | 1.012 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3601 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 10486 | 1.11 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3602 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 10738 | 1.056 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3603 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 10881 | 0.964 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3604 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 11206 | 1.027 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3605 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 11447 | 1.097 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3606 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 11538 | 1.134 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3607 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 11882 | 0.949 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3608 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 11945 | 1.033 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3609 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 12134 | 1.164 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3610 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 12386 | 1.024 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3611 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 12564 | 1.141 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3612 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 12664 | 1.051 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3613 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 12747 | 1.085 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3614 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 12941 | 1.153 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3615 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 13083 | 1.068 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3616 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 13169 | 0.935 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3617 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 13285 | 1.032 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3618 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 13435 | 1.098 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3619 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 13605 | 1.124 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3620 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 13795 | 1.034 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3621 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 14120 | 1.125 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3622 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 14411 | 1.121 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3623 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 14716 | 1.103 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3624 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 14824 | 1.067 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3625 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 14919 | 1.27 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3626 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 15033 | 1.123 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3627 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 15179 | 1.138 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3628 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 15461 | 1.025 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3629 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 15793 | 1.036 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3630 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 15990 | 1.093 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3631 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 16096 | 1.09 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3632 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 16379 | 1.136 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3633 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 16545 | 1.184 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3634 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 16814 | 1.063 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3635 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 16936 | 1.132 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3636 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 17443 | 1.062 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3637 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 17574 | 1.09 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3638 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 17735 | 1.195 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3639 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 17854 | 1.033 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3640 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 19327 | 1.192 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3641 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 19736 | 1.142 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3642 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 19901 | 1.113 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3643 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 20249 | 1.338 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3644 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 20494 | 1.25 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3645 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 20739 | 1.163 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3646 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 21088 | 1.239 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3647 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 21183 | 1.223 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3648 | warn | NELSON_R2 | white_water_consistency_pct | 1 | 21506 | 1.171 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3649 | warn | NELSON_R2 | fan_pump_speed_rpm | 2 | 14 | 901 | fan_pump_speed_rpm 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3650 | warn | NELSON_R2 | fan_pump_speed_rpm | 2 | 219 | 887.4 | fan_pump_speed_rpm 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3651 | warn | NELSON_R2 | fan_pump_speed_rpm | 2 | 428 | 893.8 | fan_pump_speed_rpm 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3652 | warn | NELSON_R2 | fan_pump_speed_rpm | 2 | 632 | 892.5 | fan_pump_speed_rpm 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3653 | warn | NELSON_R2 | fan_pump_speed_rpm | 2 | 719 | 897.4 | fan_pump_speed_rpm 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3654 | warn | NELSON_R2 | fan_pump_speed_rpm | 2 | 1089 | 893.3 | fan_pump_speed_rpm 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3655 | warn | NELSON_R2 | fan_pump_speed_rpm | 2 | 1215 | 903 | fan_pump_speed_rpm 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3656 | warn | NELSON_R2 | fan_pump_speed_rpm | 2 | 1296 | 893.6 | fan_pump_speed_rpm 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3657 | warn | NELSON_R2 | fan_pump_speed_rpm | 2 | 1378 | 909.3 | fan_pump_speed_rpm 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3658 | warn | NELSON_R2 | fan_pump_speed_rpm | 2 | 1471 | 899 | fan_pump_speed_rpm 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3659 | warn | NELSON_R2 | fan_pump_speed_rpm | 2 | 1698 | 902.9 | fan_pump_speed_rpm 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3660 | warn | NELSON_R2 | fan_pump_speed_rpm | 2 | 1785 | 897.5 | fan_pump_speed_rpm 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3661 | warn | NELSON_R2 | headbox_pressure_kPa | 2 | 8 | 24.14 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3662 | warn | NELSON_R2 | headbox_pressure_kPa | 2 | 193 | 17.67 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3663 | warn | NELSON_R2 | headbox_pressure_kPa | 2 | 282 | 18.22 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3664 | warn | NELSON_R2 | headbox_pressure_kPa | 2 | 452 | 17.79 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3665 | warn | NELSON_R2 | headbox_pressure_kPa | 2 | 546 | 24.06 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3666 | warn | NELSON_R2 | headbox_pressure_kPa | 2 | 759 | 17.97 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3667 | warn | NELSON_R2 | headbox_pressure_kPa | 2 | 964 | 20.87 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3668 | warn | NELSON_R2 | headbox_pressure_kPa | 2 | 1215 | 24.52 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3669 | warn | NELSON_R2 | headbox_pressure_kPa | 2 | 1298 | 21.37 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3670 | warn | NELSON_R2 | headbox_pressure_kPa | 2 | 1509 | 21.6 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3671 | warn | NELSON_R2 | headbox_pressure_kPa | 2 | 1594 | 18.59 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3672 | warn | NELSON_R2 | headbox_pressure_kPa | 2 | 1779 | 21.79 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3673 | warn | NELSON_R2 | headbox_pressure_kPa | 2 | 1942 | 22.45 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3674 | warn | NELSON_R2 | headbox_pressure_kPa | 2 | 2053 | 25.53 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3675 | warn | NELSON_R2 | headbox_pressure_kPa | 2 | 2207 | 25.93 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3676 | warn | NELSON_R2 | headbox_pressure_kPa | 2 | 2426 | 19.26 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3677 | warn | NELSON_R2 | headbox_pressure_kPa | 2 | 2501 | 22.3 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3678 | warn | NELSON_R2 | headbox_pressure_kPa | 2 | 3153 | 19.71 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3679 | warn | NELSON_R2 | headbox_pressure_kPa | 2 | 3237 | 26.97 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3680 | warn | NELSON_R2 | headbox_pressure_kPa | 2 | 3521 | 22.68 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3681 | warn | NELSON_R2 | headbox_pressure_kPa | 2 | 4548 | 28.17 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3682 | warn | NELSON_R2 | headbox_pressure_kPa | 2 | 4742 | 21.7 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3683 | warn | NELSON_R2 | headbox_pressure_kPa | 2 | 5082 | 25.3 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3684 | warn | NELSON_R2 | headbox_pressure_kPa | 2 | 5414 | 29.46 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3685 | warn | NELSON_R2 | headbox_pressure_kPa | 2 | 6340 | 25.79 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3686 | warn | NELSON_R2 | headbox_pressure_kPa | 2 | 6824 | 27.06 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3687 | warn | NELSON_R2 | headbox_pressure_kPa | 2 | 7062 | 23.23 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3688 | warn | NELSON_R2 | headbox_pressure_kPa | 2 | 7300 | 31.69 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3689 | warn | NELSON_R2 | headbox_pressure_kPa | 2 | 7691 | 27.97 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3690 | warn | NELSON_R2 | headbox_pressure_kPa | 2 | 7756 | 32.6 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3691 | warn | NELSON_R2 | headbox_pressure_kPa | 2 | 7848 | 28.13 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3692 | warn | NELSON_R2 | headbox_pressure_kPa | 2 | 8082 | 24.33 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3693 | warn | NELSON_R2 | headbox_pressure_kPa | 2 | 10020 | 25.05 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3694 | warn | NELSON_R2 | headbox_pressure_kPa | 2 | 10334 | 31.52 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3695 | warn | NELSON_R2 | headbox_pressure_kPa | 2 | 10558 | 30.6 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3696 | warn | NELSON_R2 | headbox_pressure_kPa | 2 | 10621 | 26.41 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3697 | warn | NELSON_R2 | headbox_pressure_kPa | 2 | 10997 | 24.97 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3698 | warn | NELSON_R2 | headbox_pressure_kPa | 2 | 11154 | 24.68 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3699 | warn | NELSON_R2 | headbox_pressure_kPa | 2 | 12046 | 24.03 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3700 | warn | NELSON_R2 | headbox_pressure_kPa | 2 | 12201 | 20.8 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3701 | warn | NELSON_R2 | headbox_pressure_kPa | 2 | 12628 | 21.88 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3702 | warn | NELSON_R2 | headbox_pressure_kPa | 2 | 12946 | 29.66 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3703 | warn | NELSON_R2 | headbox_pressure_kPa | 2 | 13185 | 25.81 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3704 | warn | NELSON_R2 | headbox_pressure_kPa | 2 | 13705 | 22.24 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3705 | warn | NELSON_R2 | headbox_pressure_kPa | 2 | 13924 | 25.7 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3706 | warn | NELSON_R2 | headbox_pressure_kPa | 2 | 14424 | 26.36 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3707 | warn | NELSON_R2 | headbox_pressure_kPa | 2 | 14593 | 26.77 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3708 | warn | NELSON_R2 | headbox_pressure_kPa | 2 | 14832 | 30.9 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3709 | warn | NELSON_R2 | headbox_pressure_kPa | 2 | 15387 | 23.57 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3710 | warn | NELSON_R2 | headbox_pressure_kPa | 2 | 15824 | 31.8 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3711 | warn | NELSON_R2 | headbox_pressure_kPa | 2 | 16323 | 31.56 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3712 | warn | NELSON_R2 | headbox_pressure_kPa | 2 | 16478 | 32.82 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3713 | warn | NELSON_R2 | headbox_pressure_kPa | 2 | 17422 | 29.04 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3714 | warn | NELSON_R2 | headbox_pressure_kPa | 2 | 18024 | 35.08 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3715 | warn | NELSON_R2 | headbox_pressure_kPa | 2 | 18365 | 34.34 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3716 | warn | NELSON_R2 | headbox_pressure_kPa | 2 | 18485 | 29.96 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3717 | warn | NELSON_R2 | headbox_pressure_kPa | 2 | 18948 | 29.93 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3718 | warn | NELSON_R2 | headbox_pressure_kPa | 2 | 20589 | 31.99 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3719 | warn | NELSON_R2 | headbox_pressure_kPa | 2 | 20851 | 33.15 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3720 | warn | NELSON_R2 | headbox_pressure_kPa | 2 | 21344 | 33.42 | headbox_pressure_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3721 | warn | NELSON_R2 | jet_to_wire_ratio | 2 | 227 | 0.969 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3722 | warn | NELSON_R2 | jet_to_wire_ratio | 2 | 733 | 1.022 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3723 | warn | NELSON_R2 | jet_to_wire_ratio | 2 | 796 | 1.024 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3724 | warn | NELSON_R2 | jet_to_wire_ratio | 2 | 1626 | 1.035 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3725 | warn | NELSON_R2 | jet_to_wire_ratio | 2 | 2073 | 1.084 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3726 | warn | NELSON_R2 | jet_to_wire_ratio | 2 | 3409 | 1.013 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3727 | warn | NELSON_R2 | jet_to_wire_ratio | 2 | 4227 | 1.028 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3728 | warn | NELSON_R2 | jet_to_wire_ratio | 2 | 5370 | 1.034 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3729 | warn | NELSON_R2 | jet_to_wire_ratio | 2 | 5870 | 1.009 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3730 | warn | NELSON_R2 | jet_to_wire_ratio | 2 | 6382 | 0.964 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3731 | warn | NELSON_R2 | jet_to_wire_ratio | 2 | 7220 | 1.022 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3732 | warn | NELSON_R2 | jet_to_wire_ratio | 2 | 8903 | 1.001 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3733 | warn | NELSON_R2 | jet_to_wire_ratio | 2 | 9260 | 1.008 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3734 | warn | NELSON_R2 | jet_to_wire_ratio | 2 | 9882 | 0.973 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3735 | warn | NELSON_R2 | jet_to_wire_ratio | 2 | 10749 | 1.01 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3736 | warn | NELSON_R2 | jet_to_wire_ratio | 2 | 10854 | 1.037 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3737 | warn | NELSON_R2 | jet_to_wire_ratio | 2 | 11135 | 1 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3738 | warn | NELSON_R2 | jet_to_wire_ratio | 2 | 11438 | 0.985 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3739 | warn | NELSON_R2 | jet_to_wire_ratio | 2 | 11968 | 1.06 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3740 | warn | NELSON_R2 | jet_to_wire_ratio | 2 | 12133 | 1.075 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3741 | warn | NELSON_R2 | jet_to_wire_ratio | 2 | 12478 | 1.001 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3742 | warn | NELSON_R2 | jet_to_wire_ratio | 2 | 13701 | 1.056 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3743 | warn | NELSON_R2 | jet_to_wire_ratio | 2 | 14036 | 1.017 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3744 | warn | NELSON_R2 | jet_to_wire_ratio | 2 | 17349 | 1.053 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3745 | warn | NELSON_R2 | jet_to_wire_ratio | 2 | 18357 | 0.981 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3746 | warn | NELSON_R2 | jet_to_wire_ratio | 2 | 18702 | 1.011 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3747 | warn | NELSON_R2 | jet_to_wire_ratio | 2 | 19490 | 1.068 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3748 | warn | NELSON_R2 | jet_to_wire_ratio | 2 | 20326 | 1.035 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3749 | warn | NELSON_R2 | jet_to_wire_ratio | 2 | 20609 | 0.996 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3750 | warn | NELSON_R2 | jet_to_wire_ratio | 2 | 21030 | 1.055 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3751 | warn | NELSON_R2 | jet_to_wire_ratio | 2 | 21152 | 0.976 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3752 | warn | NELSON_R2 | jet_to_wire_ratio | 2 | 21547 | 1.054 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3753 | warn | NELSON_R2 | jet_to_wire_ratio | 2 | 21947 | 1.054 | jet_to_wire_ratio 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3754 | warn | NELSON_R2 | machine_speed_mmin | 2 | 8 | 1707 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3755 | warn | NELSON_R2 | machine_speed_mmin | 2 | 110 | 1693 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3756 | warn | NELSON_R2 | machine_speed_mmin | 2 | 230 | 1700 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3757 | warn | NELSON_R2 | machine_speed_mmin | 2 | 360 | 1515 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3758 | warn | NELSON_R2 | machine_speed_mmin | 2 | 541 | 1692 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3759 | warn | NELSON_R2 | machine_speed_mmin | 2 | 685 | 1716 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3760 | warn | NELSON_R2 | machine_speed_mmin | 2 | 833 | 1500 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3761 | warn | NELSON_R2 | machine_speed_mmin | 2 | 1011 | 1699 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3762 | warn | NELSON_R2 | machine_speed_mmin | 2 | 1170 | 1705 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3763 | warn | NELSON_R2 | machine_speed_mmin | 2 | 1351 | 1688 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3764 | warn | NELSON_R2 | machine_speed_mmin | 2 | 1423 | 1331 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3765 | warn | NELSON_R2 | machine_speed_mmin | 2 | 1536 | 1697 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3766 | warn | NELSON_R2 | machine_speed_mmin | 2 | 1689 | 1692 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3767 | warn | NELSON_R2 | machine_speed_mmin | 2 | 1824 | 1701 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3768 | warn | NELSON_R2 | machine_speed_mmin | 2 | 2004 | 1678 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3769 | warn | NELSON_R2 | machine_speed_mmin | 2 | 2079 | 1328 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3770 | warn | NELSON_R2 | machine_speed_mmin | 2 | 2166 | 1708 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3771 | warn | NELSON_R2 | machine_speed_mmin | 2 | 2233 | 1331 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3772 | warn | NELSON_R2 | machine_speed_mmin | 2 | 2348 | 1700 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3773 | warn | NELSON_R2 | machine_speed_mmin | 2 | 2421 | 1322 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3774 | warn | NELSON_R2 | machine_speed_mmin | 2 | 2534 | 1703 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3775 | warn | NELSON_R2 | machine_speed_mmin | 2 | 2698 | 1706 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3776 | warn | NELSON_R2 | machine_speed_mmin | 2 | 2862 | 1698 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3777 | warn | NELSON_R2 | machine_speed_mmin | 2 | 2931 | 1322 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3778 | warn | NELSON_R2 | machine_speed_mmin | 2 | 3023 | 1712 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3779 | warn | NELSON_R2 | machine_speed_mmin | 2 | 3086 | 1323 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3780 | warn | NELSON_R2 | machine_speed_mmin | 2 | 3196 | 1703 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3781 | warn | NELSON_R2 | machine_speed_mmin | 2 | 3373 | 1702 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3782 | warn | NELSON_R2 | machine_speed_mmin | 2 | 3547 | 1694 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3783 | warn | NELSON_R2 | machine_speed_mmin | 2 | 3732 | 1688 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3784 | warn | NELSON_R2 | machine_speed_mmin | 2 | 3797 | 1316 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3785 | warn | NELSON_R2 | machine_speed_mmin | 2 | 3912 | 1716 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3786 | warn | NELSON_R2 | machine_speed_mmin | 2 | 4100 | 1698 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3787 | warn | NELSON_R2 | machine_speed_mmin | 2 | 4286 | 1511 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3788 | warn | NELSON_R2 | machine_speed_mmin | 2 | 4396 | 1712 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3789 | warn | NELSON_R2 | machine_speed_mmin | 2 | 4457 | 1320 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3790 | warn | NELSON_R2 | machine_speed_mmin | 2 | 4537 | 1699 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3791 | warn | NELSON_R2 | machine_speed_mmin | 2 | 4664 | 1505 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3792 | warn | NELSON_R2 | machine_speed_mmin | 2 | 4932 | 1523 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3793 | warn | NELSON_R2 | machine_speed_mmin | 2 | 5033 | 1319 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3794 | warn | NELSON_R2 | machine_speed_mmin | 2 | 5121 | 1692 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3795 | warn | NELSON_R2 | machine_speed_mmin | 2 | 5240 | 1697 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3796 | warn | NELSON_R2 | machine_speed_mmin | 2 | 5412 | 1716 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3797 | warn | NELSON_R2 | machine_speed_mmin | 2 | 5498 | 1314 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3798 | warn | NELSON_R2 | machine_speed_mmin | 2 | 5613 | 1701 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3799 | warn | NELSON_R2 | machine_speed_mmin | 2 | 5674 | 1332 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3800 | warn | NELSON_R2 | machine_speed_mmin | 2 | 5765 | 1698 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3801 | warn | NELSON_R2 | machine_speed_mmin | 2 | 5894 | 1690 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3802 | warn | NELSON_R2 | machine_speed_mmin | 2 | 5970 | 1328 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3803 | warn | NELSON_R2 | machine_speed_mmin | 2 | 6088 | 1709 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3804 | warn | NELSON_R2 | machine_speed_mmin | 2 | 6196 | 1689 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3805 | warn | NELSON_R2 | machine_speed_mmin | 2 | 6358 | 1693 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3806 | warn | NELSON_R2 | machine_speed_mmin | 2 | 6560 | 1699 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3807 | warn | NELSON_R2 | machine_speed_mmin | 2 | 6728 | 1697 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3808 | warn | NELSON_R2 | machine_speed_mmin | 2 | 6838 | 1500 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3809 | warn | NELSON_R2 | machine_speed_mmin | 2 | 6975 | 1710 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3810 | warn | NELSON_R2 | machine_speed_mmin | 2 | 7139 | 1689 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3811 | warn | NELSON_R2 | machine_speed_mmin | 2 | 7281 | 1712 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3812 | warn | NELSON_R2 | machine_speed_mmin | 2 | 7417 | 1699 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3813 | warn | NELSON_R2 | machine_speed_mmin | 2 | 7579 | 1696 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3814 | warn | NELSON_R2 | machine_speed_mmin | 2 | 7888 | 1712 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3815 | warn | NELSON_R2 | machine_speed_mmin | 2 | 8008 | 1700 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3816 | warn | NELSON_R2 | machine_speed_mmin | 2 | 8165 | 1698 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3817 | warn | NELSON_R2 | machine_speed_mmin | 2 | 8229 | 1299 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3818 | warn | NELSON_R2 | machine_speed_mmin | 2 | 8339 | 1701 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3819 | warn | NELSON_R2 | machine_speed_mmin | 2 | 8520 | 1698 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3820 | warn | NELSON_R2 | machine_speed_mmin | 2 | 8720 | 1696 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3821 | warn | NELSON_R2 | machine_speed_mmin | 2 | 8966 | 1643 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3822 | warn | NELSON_R2 | machine_speed_mmin | 2 | 9119 | 1718 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3823 | warn | NELSON_R2 | machine_speed_mmin | 2 | 9267 | 1697 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3824 | warn | NELSON_R2 | machine_speed_mmin | 2 | 9392 | 1501 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3825 | warn | NELSON_R2 | machine_speed_mmin | 2 | 9503 | 1319 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3826 | warn | NELSON_R2 | machine_speed_mmin | 2 | 9638 | 1676 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3827 | warn | NELSON_R2 | machine_speed_mmin | 2 | 9779 | 1686 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3828 | warn | NELSON_R2 | machine_speed_mmin | 2 | 9856 | 1351 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3829 | warn | NELSON_R2 | machine_speed_mmin | 2 | 9977 | 1708 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3830 | warn | NELSON_R2 | machine_speed_mmin | 2 | 10149 | 1710 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3831 | warn | NELSON_R2 | machine_speed_mmin | 2 | 10217 | 1321 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3832 | warn | NELSON_R2 | machine_speed_mmin | 2 | 10340 | 1702 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3833 | warn | NELSON_R2 | machine_speed_mmin | 2 | 10515 | 1695 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3834 | warn | NELSON_R2 | machine_speed_mmin | 2 | 10580 | 1314 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3835 | warn | NELSON_R2 | machine_speed_mmin | 2 | 10699 | 1679 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3836 | warn | NELSON_R2 | machine_speed_mmin | 2 | 10869 | 1695 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3837 | warn | NELSON_R2 | machine_speed_mmin | 2 | 11013 | 1673 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3838 | warn | NELSON_R2 | machine_speed_mmin | 2 | 11190 | 1707 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3839 | warn | NELSON_R2 | machine_speed_mmin | 2 | 11252 | 1316 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3840 | warn | NELSON_R2 | machine_speed_mmin | 2 | 11352 | 1688 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3841 | warn | NELSON_R2 | machine_speed_mmin | 2 | 11503 | 1693 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3842 | warn | NELSON_R2 | machine_speed_mmin | 2 | 11571 | 1316 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3843 | warn | NELSON_R2 | machine_speed_mmin | 2 | 11715 | 1702 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3844 | warn | NELSON_R2 | machine_speed_mmin | 2 | 11819 | 1698 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3845 | warn | NELSON_R2 | machine_speed_mmin | 2 | 11980 | 1720 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3846 | warn | NELSON_R2 | machine_speed_mmin | 2 | 12090 | 1699 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3847 | warn | NELSON_R2 | machine_speed_mmin | 2 | 12158 | 1315 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3848 | warn | NELSON_R2 | machine_speed_mmin | 2 | 12261 | 1703 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3849 | warn | NELSON_R2 | machine_speed_mmin | 2 | 12395 | 1696 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3850 | warn | NELSON_R2 | machine_speed_mmin | 2 | 12460 | 1319 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3851 | warn | NELSON_R2 | machine_speed_mmin | 2 | 12559 | 1700 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3852 | warn | NELSON_R2 | machine_speed_mmin | 2 | 12716 | 1697 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3853 | warn | NELSON_R2 | machine_speed_mmin | 2 | 12901 | 1713 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3854 | warn | NELSON_R2 | machine_speed_mmin | 2 | 12973 | 1325 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3855 | warn | NELSON_R2 | machine_speed_mmin | 2 | 13076 | 1703 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3856 | warn | NELSON_R2 | machine_speed_mmin | 2 | 13232 | 1697 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3857 | warn | NELSON_R2 | machine_speed_mmin | 2 | 13385 | 1715 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3858 | warn | NELSON_R2 | machine_speed_mmin | 2 | 13512 | 1708 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3859 | warn | NELSON_R2 | machine_speed_mmin | 2 | 13795 | 1693 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3860 | warn | NELSON_R2 | machine_speed_mmin | 2 | 13860 | 1293 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3861 | warn | NELSON_R2 | machine_speed_mmin | 2 | 13921 | 1508 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3862 | warn | NELSON_R2 | machine_speed_mmin | 2 | 14031 | 1332 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3863 | warn | NELSON_R2 | machine_speed_mmin | 2 | 14135 | 1707 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3864 | warn | NELSON_R2 | machine_speed_mmin | 2 | 14273 | 1706 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3865 | warn | NELSON_R2 | machine_speed_mmin | 2 | 14341 | 1330 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3866 | warn | NELSON_R2 | machine_speed_mmin | 2 | 14469 | 1706 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3867 | warn | NELSON_R2 | machine_speed_mmin | 2 | 14629 | 1704 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3868 | warn | NELSON_R2 | machine_speed_mmin | 2 | 14778 | 1510 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3869 | warn | NELSON_R2 | machine_speed_mmin | 2 | 14970 | 1703 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3870 | warn | NELSON_R2 | machine_speed_mmin | 2 | 15031 | 1323 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3871 | warn | NELSON_R2 | machine_speed_mmin | 2 | 15115 | 1690 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3872 | warn | NELSON_R2 | machine_speed_mmin | 2 | 15195 | 1328 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3873 | warn | NELSON_R2 | machine_speed_mmin | 2 | 15320 | 1691 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3874 | warn | NELSON_R2 | machine_speed_mmin | 2 | 15603 | 1696 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3875 | warn | NELSON_R2 | machine_speed_mmin | 2 | 15776 | 1694 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3876 | warn | NELSON_R2 | machine_speed_mmin | 2 | 15840 | 1329 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3877 | warn | NELSON_R2 | machine_speed_mmin | 2 | 15929 | 1705 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3878 | warn | NELSON_R2 | machine_speed_mmin | 2 | 15999 | 1340 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3879 | warn | NELSON_R2 | machine_speed_mmin | 2 | 16101 | 1711 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3880 | warn | NELSON_R2 | machine_speed_mmin | 2 | 16170 | 1326 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3881 | warn | NELSON_R2 | machine_speed_mmin | 2 | 16310 | 1694 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3882 | warn | NELSON_R2 | machine_speed_mmin | 2 | 16374 | 1334 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3883 | warn | NELSON_R2 | machine_speed_mmin | 2 | 16472 | 1706 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3884 | warn | NELSON_R2 | machine_speed_mmin | 2 | 16558 | 1326 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3885 | warn | NELSON_R2 | machine_speed_mmin | 2 | 16661 | 1701 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3886 | warn | NELSON_R2 | machine_speed_mmin | 2 | 16814 | 1703 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3887 | warn | NELSON_R2 | machine_speed_mmin | 2 | 16892 | 1333 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3888 | warn | NELSON_R2 | machine_speed_mmin | 2 | 16973 | 1701 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3889 | warn | NELSON_R2 | machine_speed_mmin | 2 | 17176 | 1690 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3890 | warn | NELSON_R2 | machine_speed_mmin | 2 | 17240 | 1331 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3891 | warn | NELSON_R2 | machine_speed_mmin | 2 | 17343 | 1700 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3892 | warn | NELSON_R2 | machine_speed_mmin | 2 | 17478 | 1700 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3893 | warn | NELSON_R2 | machine_speed_mmin | 2 | 17549 | 1337 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3894 | warn | NELSON_R2 | machine_speed_mmin | 2 | 17688 | 1696 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3895 | warn | NELSON_R2 | machine_speed_mmin | 2 | 17859 | 1509 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3896 | warn | NELSON_R2 | machine_speed_mmin | 2 | 17951 | 1314 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3897 | warn | NELSON_R2 | machine_speed_mmin | 2 | 18032 | 1691 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3898 | warn | NELSON_R2 | machine_speed_mmin | 2 | 18197 | 1712 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3899 | warn | NELSON_R2 | machine_speed_mmin | 2 | 18358 | 1699 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3900 | warn | NELSON_R2 | machine_speed_mmin | 2 | 18494 | 1684 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3901 | warn | NELSON_R2 | machine_speed_mmin | 2 | 18557 | 1319 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3902 | warn | NELSON_R2 | machine_speed_mmin | 2 | 18685 | 1705 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3903 | warn | NELSON_R2 | machine_speed_mmin | 2 | 18748 | 1323 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3904 | warn | NELSON_R2 | machine_speed_mmin | 2 | 18845 | 1700 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3905 | warn | NELSON_R2 | machine_speed_mmin | 2 | 18910 | 1317 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3906 | warn | NELSON_R2 | machine_speed_mmin | 2 | 18984 | 1702 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3907 | warn | NELSON_R2 | machine_speed_mmin | 2 | 19131 | 1713 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3908 | warn | NELSON_R2 | machine_speed_mmin | 2 | 19383 | 1707 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3909 | warn | NELSON_R2 | machine_speed_mmin | 2 | 19544 | 1689 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3910 | warn | NELSON_R2 | machine_speed_mmin | 2 | 19707 | 1706 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3911 | warn | NELSON_R2 | machine_speed_mmin | 2 | 19828 | 1502 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3912 | warn | NELSON_R2 | machine_speed_mmin | 2 | 19891 | 1695 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3913 | warn | NELSON_R2 | machine_speed_mmin | 2 | 19959 | 1326 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3914 | warn | NELSON_R2 | machine_speed_mmin | 2 | 20047 | 1708 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3915 | warn | NELSON_R2 | machine_speed_mmin | 2 | 20177 | 1700 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3916 | warn | NELSON_R2 | machine_speed_mmin | 2 | 20264 | 1312 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3917 | warn | NELSON_R2 | machine_speed_mmin | 2 | 20363 | 1709 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3918 | warn | NELSON_R2 | machine_speed_mmin | 2 | 20489 | 1709 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3919 | warn | NELSON_R2 | machine_speed_mmin | 2 | 20601 | 1700 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3920 | warn | NELSON_R2 | machine_speed_mmin | 2 | 20731 | 1697 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3921 | warn | NELSON_R2 | machine_speed_mmin | 2 | 20886 | 1675 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3922 | warn | NELSON_R2 | machine_speed_mmin | 2 | 21109 | 1694 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3923 | warn | NELSON_R2 | machine_speed_mmin | 2 | 21209 | 1681 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3924 | warn | NELSON_R2 | machine_speed_mmin | 2 | 21341 | 1509 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3925 | warn | NELSON_R2 | machine_speed_mmin | 2 | 21417 | 1298 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3926 | warn | NELSON_R2 | machine_speed_mmin | 2 | 21509 | 1688 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3927 | warn | NELSON_R2 | machine_speed_mmin | 2 | 21576 | 1334 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3928 | warn | NELSON_R2 | machine_speed_mmin | 2 | 21671 | 1699 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3929 | warn | NELSON_R2 | machine_speed_mmin | 2 | 21741 | 1314 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3930 | warn | NELSON_R2 | machine_speed_mmin | 2 | 21836 | 1684 | machine_speed_mmin 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3931 | warn | NELSON_R2 | stock_temp_C | 2 | 8 | 50.5 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3932 | warn | NELSON_R2 | stock_temp_C | 2 | 179 | 46.1 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3933 | warn | NELSON_R2 | stock_temp_C | 2 | 263 | 46 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3934 | warn | NELSON_R2 | stock_temp_C | 2 | 480 | 48 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3935 | warn | NELSON_R2 | stock_temp_C | 2 | 658 | 47.8 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3936 | warn | NELSON_R2 | stock_temp_C | 2 | 849 | 47.1 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3937 | warn | NELSON_R2 | stock_temp_C | 2 | 972 | 44 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3938 | warn | NELSON_R2 | stock_temp_C | 2 | 1158 | 50.6 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3939 | warn | NELSON_R2 | stock_temp_C | 2 | 1381 | 46.9 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3940 | warn | NELSON_R2 | stock_temp_C | 2 | 1607 | 45.8 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3941 | warn | NELSON_R2 | stock_temp_C | 2 | 1757 | 45.6 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3942 | warn | NELSON_R2 | stock_temp_C | 2 | 1926 | 47.1 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3943 | warn | NELSON_R2 | stock_temp_C | 2 | 2099 | 44.4 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3944 | warn | NELSON_R2 | stock_temp_C | 2 | 2183 | 48.6 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3945 | warn | NELSON_R2 | stock_temp_C | 2 | 2281 | 47.8 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3946 | warn | NELSON_R2 | stock_temp_C | 2 | 2510 | 47.3 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3947 | warn | NELSON_R2 | stock_temp_C | 2 | 2681 | 45.6 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3948 | warn | NELSON_R2 | stock_temp_C | 2 | 2777 | 42.7 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3949 | warn | NELSON_R2 | stock_temp_C | 2 | 2999 | 47.6 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3950 | warn | NELSON_R2 | stock_temp_C | 2 | 3239 | 46 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3951 | warn | NELSON_R2 | stock_temp_C | 2 | 3661 | 48.7 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3952 | warn | NELSON_R2 | stock_temp_C | 2 | 3942 | 46.1 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3953 | warn | NELSON_R2 | stock_temp_C | 2 | 4285 | 42.8 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3954 | warn | NELSON_R2 | stock_temp_C | 2 | 4374 | 48.3 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3955 | warn | NELSON_R2 | stock_temp_C | 2 | 4444 | 46 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3956 | warn | NELSON_R2 | stock_temp_C | 2 | 4512 | 42.4 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3957 | warn | NELSON_R2 | stock_temp_C | 2 | 4697 | 45.1 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3958 | warn | NELSON_R2 | stock_temp_C | 2 | 5016 | 43.3 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3959 | warn | NELSON_R2 | stock_temp_C | 2 | 5127 | 46.5 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3960 | warn | NELSON_R2 | stock_temp_C | 2 | 5301 | 41.1 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3961 | warn | NELSON_R2 | stock_temp_C | 2 | 5456 | 44.1 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3962 | warn | NELSON_R2 | stock_temp_C | 2 | 5855 | 46.2 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3963 | warn | NELSON_R2 | stock_temp_C | 2 | 6118 | 41.5 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3964 | warn | NELSON_R2 | stock_temp_C | 2 | 6211 | 45 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3965 | warn | NELSON_R2 | stock_temp_C | 2 | 6290 | 44.3 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3966 | warn | NELSON_R2 | stock_temp_C | 2 | 6659 | 43.2 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3967 | warn | NELSON_R2 | stock_temp_C | 2 | 7314 | 45.1 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3968 | warn | NELSON_R2 | stock_temp_C | 2 | 7411 | 37.3 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3969 | warn | NELSON_R2 | stock_temp_C | 2 | 7983 | 43.2 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3970 | warn | NELSON_R2 | stock_temp_C | 2 | 8179 | 37.2 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3971 | warn | NELSON_R2 | stock_temp_C | 2 | 8769 | 43.3 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3972 | warn | NELSON_R2 | stock_temp_C | 2 | 9102 | 42.4 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3973 | warn | NELSON_R2 | stock_temp_C | 2 | 10005 | 37.8 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3974 | warn | NELSON_R2 | stock_temp_C | 2 | 11313 | 40.2 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3975 | warn | NELSON_R2 | stock_temp_C | 2 | 11517 | 36.2 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3976 | warn | NELSON_R2 | stock_temp_C | 2 | 12579 | 36.8 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3977 | warn | NELSON_R2 | stock_temp_C | 2 | 15013 | 39.7 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3978 | warn | NELSON_R2 | stock_temp_C | 2 | 15677 | 45.2 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3979 | warn | NELSON_R2 | stock_temp_C | 2 | 16854 | 41.3 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3980 | warn | NELSON_R2 | stock_temp_C | 2 | 17239 | 40.3 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3981 | warn | NELSON_R2 | stock_temp_C | 2 | 18239 | 43.3 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3982 | warn | NELSON_R2 | stock_temp_C | 2 | 18392 | 37.6 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3983 | warn | NELSON_R2 | stock_temp_C | 2 | 19250 | 43.6 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3984 | warn | NELSON_R2 | stock_temp_C | 2 | 19333 | 41.9 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3985 | warn | NELSON_R2 | stock_temp_C | 2 | 19848 | 39.5 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3986 | warn | NELSON_R2 | stock_temp_C | 2 | 20555 | 42.9 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3987 | warn | NELSON_R2 | stock_temp_C | 2 | 20637 | 44.6 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3988 | warn | NELSON_R2 | stock_temp_C | 2 | 21008 | 46.2 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3989 | warn | NELSON_R2 | stock_temp_C | 2 | 21181 | 37.9 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3990 | warn | NELSON_R2 | stock_temp_C | 2 | 21292 | 46.5 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3991 | warn | NELSON_R2 | stock_temp_C | 2 | 21399 | 46.1 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3992 | warn | NELSON_R2 | stock_temp_C | 2 | 21554 | 41.3 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3993 | warn | NELSON_R2 | stock_temp_C | 2 | 21784 | 46.6 | stock_temp_C 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3994 | warn | NELSON_R2 | vacuum_pump1_kPa | 2 | 277 | 50.5 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3995 | warn | NELSON_R2 | vacuum_pump1_kPa | 2 | 559 | 57.4 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3996 | warn | NELSON_R2 | vacuum_pump1_kPa | 2 | 738 | 36.6 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3997 | warn | NELSON_R2 | vacuum_pump1_kPa | 2 | 1069 | 51.7 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3998 | warn | NELSON_R2 | vacuum_pump1_kPa | 2 | 2244 | 51.1 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 3999 | warn | NELSON_R2 | vacuum_pump1_kPa | 2 | 2557 | 51.6 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4000 | warn | NELSON_R2 | vacuum_pump1_kPa | 2 | 2903 | 45.8 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4001 | warn | NELSON_R2 | vacuum_pump1_kPa | 2 | 3448 | 51.4 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4002 | warn | NELSON_R2 | vacuum_pump1_kPa | 2 | 3899 | 43.8 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4003 | warn | NELSON_R2 | vacuum_pump1_kPa | 2 | 4613 | 50.2 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4004 | warn | NELSON_R2 | vacuum_pump1_kPa | 2 | 5624 | 55.9 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4005 | warn | NELSON_R2 | vacuum_pump1_kPa | 2 | 6444 | 45.7 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4006 | warn | NELSON_R2 | vacuum_pump1_kPa | 2 | 6671 | 52.2 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4007 | warn | NELSON_R2 | vacuum_pump1_kPa | 2 | 8187 | 47.9 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4008 | warn | NELSON_R2 | vacuum_pump1_kPa | 2 | 8698 | 51.4 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4009 | warn | NELSON_R2 | vacuum_pump1_kPa | 2 | 8888 | 61.3 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4010 | warn | NELSON_R2 | vacuum_pump1_kPa | 2 | 9042 | 55.9 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4011 | warn | NELSON_R2 | vacuum_pump1_kPa | 2 | 9391 | 55.4 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4012 | warn | NELSON_R2 | vacuum_pump1_kPa | 2 | 9748 | 49.8 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4013 | warn | NELSON_R2 | vacuum_pump1_kPa | 2 | 9830 | 50.1 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4014 | warn | NELSON_R2 | vacuum_pump1_kPa | 2 | 10727 | 55 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4015 | warn | NELSON_R2 | vacuum_pump1_kPa | 2 | 11104 | 49.5 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4016 | warn | NELSON_R2 | vacuum_pump1_kPa | 2 | 11358 | 52.5 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4017 | warn | NELSON_R2 | vacuum_pump1_kPa | 2 | 12541 | 49.4 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4018 | warn | NELSON_R2 | vacuum_pump1_kPa | 2 | 12700 | 45.6 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4019 | warn | NELSON_R2 | vacuum_pump1_kPa | 2 | 13686 | 57.7 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4020 | warn | NELSON_R2 | vacuum_pump1_kPa | 2 | 13776 | 54.9 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4021 | warn | NELSON_R2 | vacuum_pump1_kPa | 2 | 14720 | 47.8 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4022 | warn | NELSON_R2 | vacuum_pump1_kPa | 2 | 15134 | 51.5 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4023 | warn | NELSON_R2 | vacuum_pump1_kPa | 2 | 15348 | 54.4 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4024 | warn | NELSON_R2 | vacuum_pump1_kPa | 2 | 15625 | 49.2 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4025 | warn | NELSON_R2 | vacuum_pump1_kPa | 2 | 15804 | 49.5 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4026 | warn | NELSON_R2 | vacuum_pump1_kPa | 2 | 15947 | 56.1 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4027 | warn | NELSON_R2 | vacuum_pump1_kPa | 2 | 16027 | 52.5 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4028 | warn | NELSON_R2 | vacuum_pump1_kPa | 2 | 17545 | 56.2 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4029 | warn | NELSON_R2 | vacuum_pump1_kPa | 2 | 17741 | 54.2 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4030 | warn | NELSON_R2 | vacuum_pump1_kPa | 2 | 18115 | 53.4 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4031 | warn | NELSON_R2 | vacuum_pump1_kPa | 2 | 18270 | 52.7 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4032 | warn | NELSON_R2 | vacuum_pump1_kPa | 2 | 18658 | 57.4 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4033 | warn | NELSON_R2 | vacuum_pump1_kPa | 2 | 19042 | 45.7 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4034 | warn | NELSON_R2 | vacuum_pump1_kPa | 2 | 19312 | 55.5 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4035 | warn | NELSON_R2 | vacuum_pump1_kPa | 2 | 20120 | 61.2 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4036 | warn | NELSON_R2 | vacuum_pump1_kPa | 2 | 20554 | 51.9 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4037 | warn | NELSON_R2 | vacuum_pump1_kPa | 2 | 21043 | 50.4 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4038 | warn | NELSON_R2 | vacuum_pump1_kPa | 2 | 21406 | 51.2 | vacuum_pump1_kPa 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4039 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 31 | 0.906 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4040 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 1142 | 0.965 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4041 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 1580 | 0.963 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4042 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 1893 | 1.088 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4043 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 2930 | 0.995 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4044 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 3000 | 0.928 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4045 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 3254 | 1.137 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4046 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 3332 | 1.059 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4047 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 3511 | 1.033 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4048 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 3899 | 1.109 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4049 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 3970 | 1.283 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4050 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 4048 | 1.055 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4051 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 4172 | 1.025 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4052 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 4290 | 1.034 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4053 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 4491 | 1.097 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4054 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 4661 | 1.038 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4055 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 4792 | 0.968 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4056 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 4996 | 1.091 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4057 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 5129 | 1.066 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4058 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 5283 | 1.057 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4059 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 5624 | 1.115 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4060 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 5942 | 1.187 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4061 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 6057 | 0.945 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4062 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 6230 | 1.157 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4063 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 6398 | 1.122 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4064 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 6536 | 1.057 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4065 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 6671 | 1.115 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4066 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 6782 | 1.095 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4067 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 6909 | 1.041 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4068 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 7068 | 1.128 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4069 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 7179 | 1.13 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4070 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 7245 | 1.09 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4071 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 7369 | 1.039 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4072 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 7500 | 1.182 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4073 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 7561 | 0.955 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4074 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 7669 | 1.188 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4075 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 7754 | 1.082 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4076 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 7879 | 1.092 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4077 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 8076 | 1.081 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4078 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 8141 | 1.147 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4079 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 8316 | 1.101 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4080 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 8459 | 1.181 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4081 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 8882 | 1.144 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4082 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 9033 | 1.193 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4083 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 9253 | 1.109 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4084 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 9489 | 1.072 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4085 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 9555 | 1.126 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4086 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 9866 | 1.015 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4087 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 10165 | 1.036 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4088 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 10406 | 1.12 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4089 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 10495 | 1.078 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4090 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 10571 | 1.2 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4091 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 10761 | 1.064 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4092 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 10894 | 1.123 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4093 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 11042 | 1.098 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4094 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 11230 | 1.043 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4095 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 11482 | 1.006 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4096 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 11624 | 1.138 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4097 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 11777 | 0.964 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4098 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 12100 | 1.029 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4099 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 12209 | 1.076 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4100 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 12444 | 0.967 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4101 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 12523 | 1.093 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4102 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 12746 | 1.11 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4103 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 12924 | 1.099 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4104 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 13049 | 1.089 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4105 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 13141 | 1.084 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4106 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 13473 | 1.033 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4107 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 13584 | 1.194 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4108 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 13826 | 1.147 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4109 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 13981 | 1.058 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4110 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 14163 | 1.064 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4111 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 14293 | 1.173 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4112 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 14377 | 1.058 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4113 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 14536 | 0.992 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4114 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 14672 | 1.098 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4115 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 14868 | 1.036 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4116 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 15007 | 1.03 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4117 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 15256 | 1.139 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4118 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 15556 | 1.209 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4119 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 15689 | 1.126 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4120 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 15776 | 1.106 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4121 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 15896 | 1.037 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4122 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 16066 | 1.127 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4123 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 16345 | 1.182 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4124 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 16417 | 1.2 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4125 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 16498 | 1.136 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4126 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 16622 | 1.163 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4127 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 17101 | 1.118 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4128 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 17208 | 1.092 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4129 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 17420 | 1.192 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4130 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 17521 | 1.154 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4131 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 17610 | 1.139 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4132 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 17859 | 1.108 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4133 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 17989 | 1.194 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4134 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 18071 | 1.104 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4135 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 18240 | 1.181 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4136 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 18502 | 1.172 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4137 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 18686 | 1.286 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4138 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 18887 | 1.144 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4139 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 19210 | 1.196 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4140 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 19313 | 1.187 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4141 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 19516 | 1.231 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4142 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 19601 | 1.183 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4143 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 19671 | 1.182 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4144 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 19733 | 1.171 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4145 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 19911 | 1.208 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4146 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 20105 | 1.186 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4147 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 20174 | 1.102 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4148 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 20534 | 1.167 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4149 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 20643 | 1.219 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4150 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 21051 | 1.185 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4151 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 21398 | 1.301 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4152 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 21541 | 1.212 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4153 | warn | NELSON_R2 | white_water_consistency_pct | 2 | 21692 | 1.149 | white_water_consistency_pct 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 4154 | warn | NELSON_R3 | fan_pump_speed_rpm | 1 | 404 | 905.9 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4155 | warn | NELSON_R3 | fan_pump_speed_rpm | 1 | 1249 | 906.4 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4156 | warn | NELSON_R3 | fan_pump_speed_rpm | 1 | 1315 | 905.5 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4157 | warn | NELSON_R3 | fan_pump_speed_rpm | 1 | 1693 | 890.6 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4158 | warn | NELSON_R3 | fan_pump_speed_rpm | 1 | 2565 | 889.6 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4159 | warn | NELSON_R3 | fan_pump_speed_rpm | 1 | 3114 | 906.2 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4160 | warn | NELSON_R3 | fan_pump_speed_rpm | 1 | 3247 | 899.2 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4161 | warn | NELSON_R3 | fan_pump_speed_rpm | 1 | 5225 | 901 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4162 | warn | NELSON_R3 | fan_pump_speed_rpm | 1 | 5391 | 900.3 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4163 | warn | NELSON_R3 | fan_pump_speed_rpm | 1 | 6071 | 910.5 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4164 | warn | NELSON_R3 | fan_pump_speed_rpm | 1 | 6273 | 900.4 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4165 | warn | NELSON_R3 | fan_pump_speed_rpm | 1 | 6722 | 921.8 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4166 | warn | NELSON_R3 | fan_pump_speed_rpm | 1 | 6840 | 919.1 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4167 | warn | NELSON_R3 | fan_pump_speed_rpm | 1 | 7341 | 923.3 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4168 | warn | NELSON_R3 | fan_pump_speed_rpm | 1 | 7761 | 927.4 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4169 | warn | NELSON_R3 | fan_pump_speed_rpm | 1 | 8129 | 923.2 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4170 | warn | NELSON_R3 | fan_pump_speed_rpm | 1 | 8816 | 917 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4171 | warn | NELSON_R3 | fan_pump_speed_rpm | 1 | 9030 | 929.4 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4172 | warn | NELSON_R3 | fan_pump_speed_rpm | 1 | 9164 | 930.7 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4173 | warn | NELSON_R3 | fan_pump_speed_rpm | 1 | 9993 | 925.5 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4174 | warn | NELSON_R3 | fan_pump_speed_rpm | 1 | 10303 | 917.5 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4175 | warn | NELSON_R3 | fan_pump_speed_rpm | 1 | 11086 | 895.4 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4176 | warn | NELSON_R3 | fan_pump_speed_rpm | 1 | 11249 | 909 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4177 | warn | NELSON_R3 | fan_pump_speed_rpm | 1 | 11837 | 901.1 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4178 | warn | NELSON_R3 | fan_pump_speed_rpm | 1 | 11949 | 915.4 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4179 | warn | NELSON_R3 | fan_pump_speed_rpm | 1 | 12074 | 910.5 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4180 | warn | NELSON_R3 | fan_pump_speed_rpm | 1 | 12384 | 899.8 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4181 | warn | NELSON_R3 | fan_pump_speed_rpm | 1 | 12897 | 916.3 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4182 | warn | NELSON_R3 | fan_pump_speed_rpm | 1 | 13044 | 915.1 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4183 | warn | NELSON_R3 | fan_pump_speed_rpm | 1 | 13859 | 905.1 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4184 | warn | NELSON_R3 | fan_pump_speed_rpm | 1 | 15023 | 920.5 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4185 | warn | NELSON_R3 | fan_pump_speed_rpm | 1 | 15218 | 920.6 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4186 | warn | NELSON_R3 | fan_pump_speed_rpm | 1 | 15739 | 919.7 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4187 | warn | NELSON_R3 | fan_pump_speed_rpm | 1 | 16140 | 926.1 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4188 | warn | NELSON_R3 | fan_pump_speed_rpm | 1 | 16607 | 914 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4189 | warn | NELSON_R3 | fan_pump_speed_rpm | 1 | 16791 | 916.2 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4190 | warn | NELSON_R3 | fan_pump_speed_rpm | 1 | 16929 | 919.8 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4191 | warn | NELSON_R3 | fan_pump_speed_rpm | 1 | 17237 | 914.9 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4192 | warn | NELSON_R3 | fan_pump_speed_rpm | 1 | 17744 | 922.2 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4193 | warn | NELSON_R3 | fan_pump_speed_rpm | 1 | 17909 | 920.2 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4194 | warn | NELSON_R3 | fan_pump_speed_rpm | 1 | 18111 | 916.3 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4195 | warn | NELSON_R3 | fan_pump_speed_rpm | 1 | 19810 | 929.7 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4196 | warn | NELSON_R3 | fan_pump_speed_rpm | 1 | 20372 | 937.8 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4197 | warn | NELSON_R3 | fan_pump_speed_rpm | 1 | 20755 | 935.9 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4198 | warn | NELSON_R3 | fan_pump_speed_rpm | 1 | 21200 | 938.2 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4199 | warn | NELSON_R3 | fan_pump_speed_rpm | 1 | 21332 | 932.2 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4200 | warn | NELSON_R3 | fan_pump_speed_rpm | 1 | 21645 | 950.6 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4201 | warn | NELSON_R3 | headbox_pressure_kPa | 1 | 222 | 21.56 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4202 | warn | NELSON_R3 | headbox_pressure_kPa | 1 | 408 | 26.39 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4203 | warn | NELSON_R3 | headbox_pressure_kPa | 1 | 1933 | 21.86 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4204 | warn | NELSON_R3 | headbox_pressure_kPa | 1 | 3272 | 23.01 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4205 | warn | NELSON_R3 | headbox_pressure_kPa | 1 | 3970 | 20.87 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4206 | warn | NELSON_R3 | headbox_pressure_kPa | 1 | 4144 | 20.47 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4207 | warn | NELSON_R3 | headbox_pressure_kPa | 1 | 4811 | 28.51 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4208 | warn | NELSON_R3 | headbox_pressure_kPa | 1 | 5472 | 21.73 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4209 | warn | NELSON_R3 | headbox_pressure_kPa | 1 | 6230 | 21.89 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4210 | warn | NELSON_R3 | headbox_pressure_kPa | 1 | 6795 | 23.1 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4211 | warn | NELSON_R3 | headbox_pressure_kPa | 1 | 7548 | 28.2 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4212 | warn | NELSON_R3 | headbox_pressure_kPa | 1 | 8667 | 28.81 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4213 | warn | NELSON_R3 | headbox_pressure_kPa | 1 | 8877 | 31.58 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4214 | warn | NELSON_R3 | headbox_pressure_kPa | 1 | 9027 | 31.2 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4215 | warn | NELSON_R3 | headbox_pressure_kPa | 1 | 9549 | 34.34 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4216 | warn | NELSON_R3 | headbox_pressure_kPa | 1 | 10114 | 23.29 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4217 | warn | NELSON_R3 | headbox_pressure_kPa | 1 | 10463 | 24.42 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4218 | warn | NELSON_R3 | headbox_pressure_kPa | 1 | 10553 | 29.47 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4219 | warn | NELSON_R3 | headbox_pressure_kPa | 1 | 10945 | 20.96 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4220 | warn | NELSON_R3 | headbox_pressure_kPa | 1 | 11248 | 19.51 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4221 | warn | NELSON_R3 | headbox_pressure_kPa | 1 | 11616 | 23.77 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4222 | warn | NELSON_R3 | headbox_pressure_kPa | 1 | 11885 | 20.45 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4223 | warn | NELSON_R3 | headbox_pressure_kPa | 1 | 12003 | 20.83 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4224 | warn | NELSON_R3 | headbox_pressure_kPa | 1 | 12492 | 25.66 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4225 | warn | NELSON_R3 | headbox_pressure_kPa | 1 | 13064 | 30.3 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4226 | warn | NELSON_R3 | headbox_pressure_kPa | 1 | 13268 | 26.24 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4227 | warn | NELSON_R3 | headbox_pressure_kPa | 1 | 13513 | 30.46 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4228 | warn | NELSON_R3 | headbox_pressure_kPa | 1 | 13857 | 22.52 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4229 | warn | NELSON_R3 | headbox_pressure_kPa | 1 | 13976 | 30.14 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4230 | warn | NELSON_R3 | headbox_pressure_kPa | 1 | 14379 | 22.98 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4231 | warn | NELSON_R3 | headbox_pressure_kPa | 1 | 14996 | 31.85 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4232 | warn | NELSON_R3 | headbox_pressure_kPa | 1 | 15387 | 27.44 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4233 | warn | NELSON_R3 | headbox_pressure_kPa | 1 | 17034 | 24.87 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4234 | warn | NELSON_R3 | headbox_pressure_kPa | 1 | 17191 | 25 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4235 | warn | NELSON_R3 | headbox_pressure_kPa | 1 | 17287 | 30 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4236 | warn | NELSON_R3 | headbox_pressure_kPa | 1 | 17608 | 25.4 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4237 | warn | NELSON_R3 | headbox_pressure_kPa | 1 | 17749 | 26.09 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4238 | warn | NELSON_R3 | headbox_pressure_kPa | 1 | 18458 | 29.98 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4239 | warn | NELSON_R3 | headbox_pressure_kPa | 1 | 18780 | 26.6 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4240 | warn | NELSON_R3 | headbox_pressure_kPa | 1 | 19650 | 37.77 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4241 | warn | NELSON_R3 | headbox_pressure_kPa | 1 | 19941 | 32.45 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4242 | warn | NELSON_R3 | headbox_pressure_kPa | 1 | 21132 | 28.66 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4243 | warn | NELSON_R3 | jet_to_wire_ratio | 1 | 428 | 1.04 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4244 | warn | NELSON_R3 | jet_to_wire_ratio | 1 | 493 | 0.967 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4245 | warn | NELSON_R3 | jet_to_wire_ratio | 1 | 3481 | 1.059 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4246 | warn | NELSON_R3 | jet_to_wire_ratio | 1 | 4759 | 0.975 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4247 | warn | NELSON_R3 | jet_to_wire_ratio | 1 | 5218 | 0.983 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4248 | warn | NELSON_R3 | jet_to_wire_ratio | 1 | 5805 | 1.117 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4249 | warn | NELSON_R3 | jet_to_wire_ratio | 1 | 5932 | 1.039 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4250 | warn | NELSON_R3 | jet_to_wire_ratio | 1 | 6688 | 1.085 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4251 | warn | NELSON_R3 | jet_to_wire_ratio | 1 | 6848 | 0.981 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4252 | warn | NELSON_R3 | jet_to_wire_ratio | 1 | 8661 | 1.007 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4253 | warn | NELSON_R3 | jet_to_wire_ratio | 1 | 9544 | 0.967 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4254 | warn | NELSON_R3 | jet_to_wire_ratio | 1 | 9702 | 1.041 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4255 | warn | NELSON_R3 | jet_to_wire_ratio | 1 | 10232 | 0.965 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4256 | warn | NELSON_R3 | jet_to_wire_ratio | 1 | 10527 | 1.057 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4257 | warn | NELSON_R3 | jet_to_wire_ratio | 1 | 13242 | 1.131 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4258 | warn | NELSON_R3 | jet_to_wire_ratio | 1 | 13586 | 1.04 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4259 | warn | NELSON_R3 | jet_to_wire_ratio | 1 | 13952 | 1.048 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4260 | warn | NELSON_R3 | jet_to_wire_ratio | 1 | 14055 | 1.071 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4261 | warn | NELSON_R3 | jet_to_wire_ratio | 1 | 17224 | 1.011 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4262 | warn | NELSON_R3 | jet_to_wire_ratio | 1 | 17811 | 1.067 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4263 | warn | NELSON_R3 | jet_to_wire_ratio | 1 | 18680 | 1.049 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4264 | warn | NELSON_R3 | jet_to_wire_ratio | 1 | 20823 | 1.071 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4265 | warn | NELSON_R3 | jet_to_wire_ratio | 1 | 21236 | 1.04 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4266 | warn | NELSON_R3 | jet_to_wire_ratio | 1 | 21335 | 1.008 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4267 | warn | NELSON_R3 | jet_to_wire_ratio | 1 | 21436 | 1.094 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4268 | warn | NELSON_R3 | jet_to_wire_ratio | 1 | 21529 | 0.999 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4269 | warn | NELSON_R3 | machine_speed_mmin | 1 | 344 | 1514 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4270 | warn | NELSON_R3 | machine_speed_mmin | 1 | 408 | 1697 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4271 | warn | NELSON_R3 | machine_speed_mmin | 1 | 484 | 1332 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4272 | warn | NELSON_R3 | machine_speed_mmin | 1 | 722 | 1500 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4273 | warn | NELSON_R3 | machine_speed_mmin | 1 | 862 | 1506 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4274 | warn | NELSON_R3 | machine_speed_mmin | 1 | 1167 | 1525 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4275 | warn | NELSON_R3 | machine_speed_mmin | 1 | 1343 | 1484 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4276 | warn | NELSON_R3 | machine_speed_mmin | 1 | 1760 | 1494 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4277 | warn | NELSON_R3 | machine_speed_mmin | 1 | 1823 | 1707 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4278 | warn | NELSON_R3 | machine_speed_mmin | 1 | 2722 | 1347 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4279 | warn | NELSON_R3 | machine_speed_mmin | 1 | 3717 | 1717 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4280 | warn | NELSON_R3 | machine_speed_mmin | 1 | 3823 | 1524 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4281 | warn | NELSON_R3 | machine_speed_mmin | 1 | 4155 | 1500 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4282 | warn | NELSON_R3 | machine_speed_mmin | 1 | 4295 | 1350 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4283 | warn | NELSON_R3 | machine_speed_mmin | 1 | 4453 | 1310 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4284 | warn | NELSON_R3 | machine_speed_mmin | 1 | 4696 | 1322 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4285 | warn | NELSON_R3 | machine_speed_mmin | 1 | 4839 | 1321 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4286 | warn | NELSON_R3 | machine_speed_mmin | 1 | 4908 | 1519 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4287 | warn | NELSON_R3 | machine_speed_mmin | 1 | 5462 | 1334 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4288 | warn | NELSON_R3 | machine_speed_mmin | 1 | 5920 | 1315 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4289 | warn | NELSON_R3 | machine_speed_mmin | 1 | 6309 | 1710 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4290 | warn | NELSON_R3 | machine_speed_mmin | 1 | 6405 | 1515 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4291 | warn | NELSON_R3 | machine_speed_mmin | 1 | 6952 | 1294 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4292 | warn | NELSON_R3 | machine_speed_mmin | 1 | 7301 | 1677 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4293 | warn | NELSON_R3 | machine_speed_mmin | 1 | 7549 | 1516 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4294 | warn | NELSON_R3 | machine_speed_mmin | 1 | 7661 | 1325 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4295 | warn | NELSON_R3 | machine_speed_mmin | 1 | 8116 | 1687 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4296 | warn | NELSON_R3 | machine_speed_mmin | 1 | 8280 | 1308 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4297 | warn | NELSON_R3 | machine_speed_mmin | 1 | 8583 | 1713 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4298 | warn | NELSON_R3 | machine_speed_mmin | 1 | 8647 | 1525 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4299 | warn | NELSON_R3 | machine_speed_mmin | 1 | 9015 | 1306 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4300 | warn | NELSON_R3 | machine_speed_mmin | 1 | 9155 | 1526 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4301 | warn | NELSON_R3 | machine_speed_mmin | 1 | 9510 | 1520 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4302 | warn | NELSON_R3 | machine_speed_mmin | 1 | 9599 | 1693 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4303 | warn | NELSON_R3 | machine_speed_mmin | 1 | 10009 | 1511 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4304 | warn | NELSON_R3 | machine_speed_mmin | 1 | 10223 | 1701 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4305 | warn | NELSON_R3 | machine_speed_mmin | 1 | 10398 | 1698 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4306 | warn | NELSON_R3 | machine_speed_mmin | 1 | 10470 | 1314 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4307 | warn | NELSON_R3 | machine_speed_mmin | 1 | 10624 | 1308 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4308 | warn | NELSON_R3 | machine_speed_mmin | 1 | 10938 | 1334 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4309 | warn | NELSON_R3 | machine_speed_mmin | 1 | 11364 | 1781 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4310 | warn | NELSON_R3 | machine_speed_mmin | 1 | 11612 | 1316 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4311 | warn | NELSON_R3 | machine_speed_mmin | 1 | 11683 | 1758 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4312 | warn | NELSON_R3 | machine_speed_mmin | 1 | 11771 | 1513 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4313 | warn | NELSON_R3 | machine_speed_mmin | 1 | 11920 | 1526 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4314 | warn | NELSON_R3 | machine_speed_mmin | 1 | 12059 | 1498 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4315 | warn | NELSON_R3 | machine_speed_mmin | 1 | 12803 | 1325 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4316 | warn | NELSON_R3 | machine_speed_mmin | 1 | 12872 | 1485 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4317 | warn | NELSON_R3 | machine_speed_mmin | 1 | 13153 | 1524 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4318 | warn | NELSON_R3 | machine_speed_mmin | 1 | 13370 | 1302 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4319 | warn | NELSON_R3 | machine_speed_mmin | 1 | 13858 | 1333 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4320 | warn | NELSON_R3 | machine_speed_mmin | 1 | 13967 | 1719 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4321 | warn | NELSON_R3 | machine_speed_mmin | 1 | 14098 | 1510 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4322 | warn | NELSON_R3 | machine_speed_mmin | 1 | 14190 | 1686 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4323 | warn | NELSON_R3 | machine_speed_mmin | 1 | 14495 | 1716 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4324 | warn | NELSON_R3 | machine_speed_mmin | 1 | 14666 | 1707 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4325 | warn | NELSON_R3 | machine_speed_mmin | 1 | 15043 | 1331 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4326 | warn | NELSON_R3 | machine_speed_mmin | 1 | 15164 | 1709 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4327 | warn | NELSON_R3 | machine_speed_mmin | 1 | 15262 | 1526 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4328 | warn | NELSON_R3 | machine_speed_mmin | 1 | 16201 | 1712 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4329 | warn | NELSON_R3 | machine_speed_mmin | 1 | 16570 | 1522 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4330 | warn | NELSON_R3 | machine_speed_mmin | 1 | 16682 | 1315 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4331 | warn | NELSON_R3 | machine_speed_mmin | 1 | 16759 | 1520 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4332 | warn | NELSON_R3 | machine_speed_mmin | 1 | 17107 | 1505 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4333 | warn | NELSON_R3 | machine_speed_mmin | 1 | 17388 | 1689 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4334 | warn | NELSON_R3 | machine_speed_mmin | 1 | 17531 | 1718 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4335 | warn | NELSON_R3 | machine_speed_mmin | 1 | 18074 | 1322 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4336 | warn | NELSON_R3 | machine_speed_mmin | 1 | 19294 | 1524 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4337 | warn | NELSON_R3 | machine_speed_mmin | 1 | 19405 | 1507 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4338 | warn | NELSON_R3 | machine_speed_mmin | 1 | 19514 | 1316 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4339 | warn | NELSON_R3 | machine_speed_mmin | 1 | 19582 | 1489 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4340 | warn | NELSON_R3 | machine_speed_mmin | 1 | 19910 | 1303 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4341 | warn | NELSON_R3 | machine_speed_mmin | 1 | 19991 | 1722 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4342 | warn | NELSON_R3 | machine_speed_mmin | 1 | 20655 | 1491 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4343 | warn | NELSON_R3 | machine_speed_mmin | 1 | 20815 | 1520 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4344 | warn | NELSON_R3 | machine_speed_mmin | 1 | 21062 | 1498 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4345 | warn | NELSON_R3 | machine_speed_mmin | 1 | 21499 | 1711 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4346 | warn | NELSON_R3 | machine_speed_mmin | 1 | 21651 | 1525 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4347 | warn | NELSON_R3 | stock_temp_C | 1 | 883 | 47.4 | stock_temp_C 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4348 | warn | NELSON_R3 | stock_temp_C | 1 | 1085 | 51.6 | stock_temp_C 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4349 | warn | NELSON_R3 | stock_temp_C | 1 | 1433 | 49.2 | stock_temp_C 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4350 | warn | NELSON_R3 | stock_temp_C | 1 | 3216 | 48.1 | stock_temp_C 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4351 | warn | NELSON_R3 | stock_temp_C | 1 | 4326 | 47.4 | stock_temp_C 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4352 | warn | NELSON_R3 | stock_temp_C | 1 | 5365 | 45 | stock_temp_C 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4353 | warn | NELSON_R3 | stock_temp_C | 1 | 5508 | 44.6 | stock_temp_C 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4354 | warn | NELSON_R3 | stock_temp_C | 1 | 7007 | 37.4 | stock_temp_C 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4355 | warn | NELSON_R3 | stock_temp_C | 1 | 7278 | 40.8 | stock_temp_C 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4356 | warn | NELSON_R3 | stock_temp_C | 1 | 8957 | 41.8 | stock_temp_C 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4357 | warn | NELSON_R3 | stock_temp_C | 1 | 9946 | 41 | stock_temp_C 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4358 | warn | NELSON_R3 | stock_temp_C | 1 | 10198 | 37.1 | stock_temp_C 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4359 | warn | NELSON_R3 | stock_temp_C | 1 | 12424 | 40.4 | stock_temp_C 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4360 | warn | NELSON_R3 | stock_temp_C | 1 | 13540 | 40.4 | stock_temp_C 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4361 | warn | NELSON_R3 | stock_temp_C | 1 | 15062 | 39.7 | stock_temp_C 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4362 | warn | NELSON_R3 | stock_temp_C | 1 | 15980 | 37.5 | stock_temp_C 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4363 | warn | NELSON_R3 | stock_temp_C | 1 | 17018 | 39.1 | stock_temp_C 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4364 | warn | NELSON_R3 | stock_temp_C | 1 | 17349 | 37.5 | stock_temp_C 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4365 | warn | NELSON_R3 | stock_temp_C | 1 | 18129 | 39.6 | stock_temp_C 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4366 | warn | NELSON_R3 | stock_temp_C | 1 | 19054 | 45.8 | stock_temp_C 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4367 | warn | NELSON_R3 | stock_temp_C | 1 | 19434 | 43 | stock_temp_C 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4368 | warn | NELSON_R3 | stock_temp_C | 1 | 19603 | 42.6 | stock_temp_C 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4369 | warn | NELSON_R3 | stock_temp_C | 1 | 19806 | 44.8 | stock_temp_C 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4370 | warn | NELSON_R3 | stock_temp_C | 1 | 20793 | 45.4 | stock_temp_C 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4371 | warn | NELSON_R3 | stock_temp_C | 1 | 21111 | 43.2 | stock_temp_C 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4372 | warn | NELSON_R3 | vacuum_pump1_kPa | 1 | 103 | 56.4 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4373 | warn | NELSON_R3 | vacuum_pump1_kPa | 1 | 1076 | 49.9 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4374 | warn | NELSON_R3 | vacuum_pump1_kPa | 1 | 1373 | 49.1 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4375 | warn | NELSON_R3 | vacuum_pump1_kPa | 1 | 2027 | 57.9 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4376 | warn | NELSON_R3 | vacuum_pump1_kPa | 1 | 2153 | 56.7 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4377 | warn | NELSON_R3 | vacuum_pump1_kPa | 1 | 3323 | 58.3 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4378 | warn | NELSON_R3 | vacuum_pump1_kPa | 1 | 3391 | 59.5 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4379 | warn | NELSON_R3 | vacuum_pump1_kPa | 1 | 3482 | 55.6 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4380 | warn | NELSON_R3 | vacuum_pump1_kPa | 1 | 4096 | 43.4 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4381 | warn | NELSON_R3 | vacuum_pump1_kPa | 1 | 4435 | 54.3 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4382 | warn | NELSON_R3 | vacuum_pump1_kPa | 1 | 4844 | 61.7 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4383 | warn | NELSON_R3 | vacuum_pump1_kPa | 1 | 5215 | 43.6 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4384 | warn | NELSON_R3 | vacuum_pump1_kPa | 1 | 5338 | 57.6 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4385 | warn | NELSON_R3 | vacuum_pump1_kPa | 1 | 5548 | 57.8 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4386 | warn | NELSON_R3 | vacuum_pump1_kPa | 1 | 5774 | 61 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4387 | warn | NELSON_R3 | vacuum_pump1_kPa | 1 | 5954 | 43.5 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4388 | warn | NELSON_R3 | vacuum_pump1_kPa | 1 | 6068 | 56.8 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4389 | warn | NELSON_R3 | vacuum_pump1_kPa | 1 | 6506 | 53.1 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4390 | warn | NELSON_R3 | vacuum_pump1_kPa | 1 | 8064 | 41.8 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4391 | warn | NELSON_R3 | vacuum_pump1_kPa | 1 | 8161 | 59.1 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4392 | warn | NELSON_R3 | vacuum_pump1_kPa | 1 | 8986 | 48.3 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4393 | warn | NELSON_R3 | vacuum_pump1_kPa | 1 | 9253 | 61.5 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4394 | warn | NELSON_R3 | vacuum_pump1_kPa | 1 | 10149 | 58.6 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4395 | warn | NELSON_R3 | vacuum_pump1_kPa | 1 | 10616 | 62.4 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4396 | warn | NELSON_R3 | vacuum_pump1_kPa | 1 | 10885 | 47 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4397 | warn | NELSON_R3 | vacuum_pump1_kPa | 1 | 11019 | 48.2 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4398 | warn | NELSON_R3 | vacuum_pump1_kPa | 1 | 11223 | 46 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4399 | warn | NELSON_R3 | vacuum_pump1_kPa | 1 | 11637 | 46.1 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4400 | warn | NELSON_R3 | vacuum_pump1_kPa | 1 | 12998 | 55.2 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4401 | warn | NELSON_R3 | vacuum_pump1_kPa | 1 | 13308 | 56.3 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4402 | warn | NELSON_R3 | vacuum_pump1_kPa | 1 | 13704 | 48.5 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4403 | warn | NELSON_R3 | vacuum_pump1_kPa | 1 | 14038 | 53 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4404 | warn | NELSON_R3 | vacuum_pump1_kPa | 1 | 15155 | 60.4 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4405 | warn | NELSON_R3 | vacuum_pump1_kPa | 1 | 15560 | 45.1 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4406 | warn | NELSON_R3 | vacuum_pump1_kPa | 1 | 15734 | 57 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4407 | warn | NELSON_R3 | vacuum_pump1_kPa | 1 | 15948 | 60.2 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4408 | warn | NELSON_R3 | vacuum_pump1_kPa | 1 | 16362 | 45.3 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4409 | warn | NELSON_R3 | vacuum_pump1_kPa | 1 | 17354 | 56.1 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4410 | warn | NELSON_R3 | vacuum_pump1_kPa | 1 | 17979 | 56.7 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4411 | warn | NELSON_R3 | vacuum_pump1_kPa | 1 | 18125 | 45.7 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4412 | warn | NELSON_R3 | vacuum_pump1_kPa | 1 | 18561 | 46.4 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4413 | warn | NELSON_R3 | vacuum_pump1_kPa | 1 | 18652 | 59.5 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4414 | warn | NELSON_R3 | vacuum_pump1_kPa | 1 | 19453 | 53.9 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4415 | warn | NELSON_R3 | vacuum_pump1_kPa | 1 | 19769 | 61 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4416 | warn | NELSON_R3 | vacuum_pump1_kPa | 1 | 20046 | 50.4 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4417 | warn | NELSON_R3 | vacuum_pump1_kPa | 1 | 20219 | 37.7 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4418 | warn | NELSON_R3 | vacuum_pump1_kPa | 1 | 20320 | 45.9 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4419 | warn | NELSON_R3 | vacuum_pump1_kPa | 1 | 20530 | 56.4 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4420 | warn | NELSON_R3 | vacuum_pump1_kPa | 1 | 20867 | 62.7 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4421 | warn | NELSON_R3 | white_water_consistency_pct | 1 | 996 | 1.167 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4422 | warn | NELSON_R3 | white_water_consistency_pct | 1 | 2725 | 0.952 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4423 | warn | NELSON_R3 | white_water_consistency_pct | 1 | 2972 | 1.079 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4424 | warn | NELSON_R3 | white_water_consistency_pct | 1 | 3129 | 0.976 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4425 | warn | NELSON_R3 | white_water_consistency_pct | 1 | 3212 | 1.159 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4426 | warn | NELSON_R3 | white_water_consistency_pct | 1 | 3319 | 1.09 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4427 | warn | NELSON_R3 | white_water_consistency_pct | 1 | 3556 | 0.3 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4428 | warn | NELSON_R3 | white_water_consistency_pct | 1 | 3772 | 0.833 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4429 | warn | NELSON_R3 | white_water_consistency_pct | 1 | 3901 | 0.967 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4430 | warn | NELSON_R3 | white_water_consistency_pct | 1 | 4514 | 1.042 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4431 | warn | NELSON_R3 | white_water_consistency_pct | 1 | 4963 | 1.281 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4432 | warn | NELSON_R3 | white_water_consistency_pct | 1 | 5247 | 1.13 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4433 | warn | NELSON_R3 | white_water_consistency_pct | 1 | 5404 | 1.035 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4434 | warn | NELSON_R3 | white_water_consistency_pct | 1 | 6357 | 1.137 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4435 | warn | NELSON_R3 | white_water_consistency_pct | 1 | 6531 | 1.139 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4436 | warn | NELSON_R3 | white_water_consistency_pct | 1 | 6645 | 1.268 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4437 | warn | NELSON_R3 | white_water_consistency_pct | 1 | 7616 | 1.053 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4438 | warn | NELSON_R3 | white_water_consistency_pct | 1 | 7861 | 0.784 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4439 | warn | NELSON_R3 | white_water_consistency_pct | 1 | 7987 | 1.089 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4440 | warn | NELSON_R3 | white_water_consistency_pct | 1 | 8568 | 1.061 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4441 | warn | NELSON_R3 | white_water_consistency_pct | 1 | 8976 | 1.051 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4442 | warn | NELSON_R3 | white_water_consistency_pct | 1 | 9549 | 1.041 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4443 | warn | NELSON_R3 | white_water_consistency_pct | 1 | 11041 | 0.987 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4444 | warn | NELSON_R3 | white_water_consistency_pct | 1 | 11280 | 1.072 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4445 | warn | NELSON_R3 | white_water_consistency_pct | 1 | 12095 | 0.967 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4446 | warn | NELSON_R3 | white_water_consistency_pct | 1 | 12528 | 1.096 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4447 | warn | NELSON_R3 | white_water_consistency_pct | 1 | 13058 | 1.06 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4448 | warn | NELSON_R3 | white_water_consistency_pct | 1 | 13465 | 1.05 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4449 | warn | NELSON_R3 | white_water_consistency_pct | 1 | 13810 | 0.839 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4450 | warn | NELSON_R3 | white_water_consistency_pct | 1 | 14023 | 1.056 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4451 | warn | NELSON_R3 | white_water_consistency_pct | 1 | 14111 | 0.83 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4452 | warn | NELSON_R3 | white_water_consistency_pct | 1 | 14494 | 1.019 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4453 | warn | NELSON_R3 | white_water_consistency_pct | 1 | 14676 | 0.983 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4454 | warn | NELSON_R3 | white_water_consistency_pct | 1 | 14746 | 0.913 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4455 | warn | NELSON_R3 | white_water_consistency_pct | 1 | 15395 | 1.014 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4456 | warn | NELSON_R3 | white_water_consistency_pct | 1 | 15625 | 0.95 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4457 | warn | NELSON_R3 | white_water_consistency_pct | 1 | 16125 | 1.027 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4458 | warn | NELSON_R3 | white_water_consistency_pct | 1 | 16347 | 1.112 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4459 | warn | NELSON_R3 | white_water_consistency_pct | 1 | 17145 | 1.099 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4460 | warn | NELSON_R3 | white_water_consistency_pct | 1 | 17769 | 1.25 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4461 | warn | NELSON_R3 | white_water_consistency_pct | 1 | 18146 | 1.197 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4462 | warn | NELSON_R3 | white_water_consistency_pct | 1 | 18687 | 1.232 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4463 | warn | NELSON_R3 | white_water_consistency_pct | 1 | 18846 | 1.219 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4464 | warn | NELSON_R3 | white_water_consistency_pct | 1 | 19399 | 1.179 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4465 | warn | NELSON_R3 | white_water_consistency_pct | 1 | 20898 | 1.112 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4466 | warn | NELSON_R3 | white_water_consistency_pct | 1 | 21132 | 1.513 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4467 | warn | NELSON_R3 | white_water_consistency_pct | 1 | 21337 | 1.123 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4468 | warn | NELSON_R3 | white_water_consistency_pct | 1 | 21560 | 1.44 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4469 | warn | NELSON_R3 | white_water_consistency_pct | 1 | 21671 | 1.158 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4470 | warn | NELSON_R3 | fan_pump_speed_rpm | 2 | 144 | 895.7 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4471 | warn | NELSON_R3 | fan_pump_speed_rpm | 2 | 1769 | 902.1 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4472 | warn | NELSON_R3 | fan_pump_speed_rpm | 2 | 1972 | 907.6 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4473 | warn | NELSON_R3 | fan_pump_speed_rpm | 2 | 2222 | 895.1 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4474 | warn | NELSON_R3 | fan_pump_speed_rpm | 2 | 2322 | 888.8 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4475 | warn | NELSON_R3 | fan_pump_speed_rpm | 2 | 2936 | 899.4 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4476 | warn | NELSON_R3 | fan_pump_speed_rpm | 2 | 3297 | 900.3 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4477 | warn | NELSON_R3 | fan_pump_speed_rpm | 2 | 4470 | 914.2 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4478 | warn | NELSON_R3 | fan_pump_speed_rpm | 2 | 4893 | 914.1 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4479 | warn | NELSON_R3 | fan_pump_speed_rpm | 2 | 5458 | 911.7 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4480 | warn | NELSON_R3 | fan_pump_speed_rpm | 2 | 5812 | 899.1 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4481 | warn | NELSON_R3 | fan_pump_speed_rpm | 2 | 6065 | 919.2 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4482 | warn | NELSON_R3 | fan_pump_speed_rpm | 2 | 6232 | 904.9 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4483 | warn | NELSON_R3 | fan_pump_speed_rpm | 2 | 6298 | 922.8 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4484 | warn | NELSON_R3 | fan_pump_speed_rpm | 2 | 7059 | 909.3 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4485 | warn | NELSON_R3 | fan_pump_speed_rpm | 2 | 7310 | 906.8 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4486 | warn | NELSON_R3 | fan_pump_speed_rpm | 2 | 7417 | 910.9 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4487 | warn | NELSON_R3 | fan_pump_speed_rpm | 2 | 9004 | 930.4 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4488 | warn | NELSON_R3 | fan_pump_speed_rpm | 2 | 9477 | 932 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4489 | warn | NELSON_R3 | fan_pump_speed_rpm | 2 | 9565 | 925.3 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4490 | warn | NELSON_R3 | fan_pump_speed_rpm | 2 | 9650 | 917.7 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4491 | warn | NELSON_R3 | fan_pump_speed_rpm | 2 | 10365 | 906.6 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4492 | warn | NELSON_R3 | fan_pump_speed_rpm | 2 | 10446 | 905.8 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4493 | warn | NELSON_R3 | fan_pump_speed_rpm | 2 | 10635 | 908.4 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4494 | warn | NELSON_R3 | fan_pump_speed_rpm | 2 | 11027 | 901.4 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4495 | warn | NELSON_R3 | fan_pump_speed_rpm | 2 | 11372 | 906.7 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4496 | warn | NELSON_R3 | fan_pump_speed_rpm | 2 | 11610 | 897.4 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4497 | warn | NELSON_R3 | fan_pump_speed_rpm | 2 | 12206 | 900.1 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4498 | warn | NELSON_R3 | fan_pump_speed_rpm | 2 | 12347 | 907.6 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4499 | warn | NELSON_R3 | fan_pump_speed_rpm | 2 | 12658 | 914.7 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4500 | warn | NELSON_R3 | fan_pump_speed_rpm | 2 | 12992 | 902.6 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4501 | warn | NELSON_R3 | fan_pump_speed_rpm | 2 | 13941 | 920 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4502 | warn | NELSON_R3 | fan_pump_speed_rpm | 2 | 14057 | 919.4 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4503 | warn | NELSON_R3 | fan_pump_speed_rpm | 2 | 14711 | 920.1 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4504 | warn | NELSON_R3 | fan_pump_speed_rpm | 2 | 14859 | 919.9 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4505 | warn | NELSON_R3 | fan_pump_speed_rpm | 2 | 15181 | 905.2 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4506 | warn | NELSON_R3 | fan_pump_speed_rpm | 2 | 15356 | 920.4 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4507 | warn | NELSON_R3 | fan_pump_speed_rpm | 2 | 15554 | 921.1 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4508 | warn | NELSON_R3 | fan_pump_speed_rpm | 2 | 15853 | 921.3 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4509 | warn | NELSON_R3 | fan_pump_speed_rpm | 2 | 16056 | 929.1 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4510 | warn | NELSON_R3 | fan_pump_speed_rpm | 2 | 16554 | 920.1 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4511 | warn | NELSON_R3 | fan_pump_speed_rpm | 2 | 16821 | 928.8 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4512 | warn | NELSON_R3 | fan_pump_speed_rpm | 2 | 16884 | 922 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4513 | warn | NELSON_R3 | fan_pump_speed_rpm | 2 | 17007 | 934.2 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4514 | warn | NELSON_R3 | fan_pump_speed_rpm | 2 | 17480 | 917.4 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4515 | warn | NELSON_R3 | fan_pump_speed_rpm | 2 | 17646 | 911.2 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4516 | warn | NELSON_R3 | fan_pump_speed_rpm | 2 | 18018 | 919.9 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4517 | warn | NELSON_R3 | fan_pump_speed_rpm | 2 | 19696 | 928.7 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4518 | warn | NELSON_R3 | fan_pump_speed_rpm | 2 | 20102 | 925.9 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4519 | warn | NELSON_R3 | fan_pump_speed_rpm | 2 | 20494 | 930.7 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4520 | warn | NELSON_R3 | fan_pump_speed_rpm | 2 | 21377 | 933.2 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4521 | warn | NELSON_R3 | fan_pump_speed_rpm | 2 | 21644 | 945 | fan_pump_speed_rpm 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4522 | warn | NELSON_R3 | headbox_pressure_kPa | 2 | 9 | 24.08 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4523 | warn | NELSON_R3 | headbox_pressure_kPa | 2 | 870 | 24.6 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4524 | warn | NELSON_R3 | headbox_pressure_kPa | 2 | 1222 | 18.61 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4525 | warn | NELSON_R3 | headbox_pressure_kPa | 2 | 1728 | 18.46 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4526 | warn | NELSON_R3 | headbox_pressure_kPa | 2 | 2593 | 19.96 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4527 | warn | NELSON_R3 | headbox_pressure_kPa | 2 | 2880 | 27.25 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4528 | warn | NELSON_R3 | headbox_pressure_kPa | 2 | 3089 | 20.55 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4529 | warn | NELSON_R3 | headbox_pressure_kPa | 2 | 4812 | 25.39 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4530 | warn | NELSON_R3 | headbox_pressure_kPa | 2 | 5106 | 24.85 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4531 | warn | NELSON_R3 | headbox_pressure_kPa | 2 | 5196 | 25.61 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4532 | warn | NELSON_R3 | headbox_pressure_kPa | 2 | 5567 | 25.27 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4533 | warn | NELSON_R3 | headbox_pressure_kPa | 2 | 5773 | 29.81 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4534 | warn | NELSON_R3 | headbox_pressure_kPa | 2 | 5888 | 31.22 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4535 | warn | NELSON_R3 | headbox_pressure_kPa | 2 | 6108 | 29.2 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4536 | warn | NELSON_R3 | headbox_pressure_kPa | 2 | 6219 | 30.76 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4537 | warn | NELSON_R3 | headbox_pressure_kPa | 2 | 6477 | 22.24 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4538 | warn | NELSON_R3 | headbox_pressure_kPa | 2 | 6553 | 30.54 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4539 | warn | NELSON_R3 | headbox_pressure_kPa | 2 | 7073 | 27.44 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4540 | warn | NELSON_R3 | headbox_pressure_kPa | 2 | 7566 | 28.6 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4541 | warn | NELSON_R3 | headbox_pressure_kPa | 2 | 7722 | 32.15 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4542 | warn | NELSON_R3 | headbox_pressure_kPa | 2 | 9362 | 26.22 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4543 | warn | NELSON_R3 | headbox_pressure_kPa | 2 | 9521 | 26.37 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4544 | warn | NELSON_R3 | headbox_pressure_kPa | 2 | 9848 | 25.53 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4545 | warn | NELSON_R3 | headbox_pressure_kPa | 2 | 9920 | 29.04 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4546 | warn | NELSON_R3 | headbox_pressure_kPa | 2 | 10210 | 23.63 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4547 | warn | NELSON_R3 | headbox_pressure_kPa | 2 | 10341 | 32.78 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4548 | warn | NELSON_R3 | headbox_pressure_kPa | 2 | 10412 | 23.09 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4549 | warn | NELSON_R3 | headbox_pressure_kPa | 2 | 10572 | 22.85 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4550 | warn | NELSON_R3 | headbox_pressure_kPa | 2 | 10934 | 21.45 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4551 | warn | NELSON_R3 | headbox_pressure_kPa | 2 | 11271 | 20.76 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4552 | warn | NELSON_R3 | headbox_pressure_kPa | 2 | 11852 | 27.09 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4553 | warn | NELSON_R3 | headbox_pressure_kPa | 2 | 12098 | 28.26 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4554 | warn | NELSON_R3 | headbox_pressure_kPa | 2 | 12182 | 21.05 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4555 | warn | NELSON_R3 | headbox_pressure_kPa | 2 | 12454 | 21.21 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4556 | warn | NELSON_R3 | headbox_pressure_kPa | 2 | 12585 | 20.17 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4557 | warn | NELSON_R3 | headbox_pressure_kPa | 2 | 13072 | 29.49 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4558 | warn | NELSON_R3 | headbox_pressure_kPa | 2 | 13324 | 22.25 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4559 | warn | NELSON_R3 | headbox_pressure_kPa | 2 | 13831 | 30.28 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4560 | warn | NELSON_R3 | headbox_pressure_kPa | 2 | 14690 | 23.22 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4561 | warn | NELSON_R3 | headbox_pressure_kPa | 2 | 14850 | 23.25 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4562 | warn | NELSON_R3 | headbox_pressure_kPa | 2 | 15430 | 27.53 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4563 | warn | NELSON_R3 | headbox_pressure_kPa | 2 | 15505 | 23.99 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4564 | warn | NELSON_R3 | headbox_pressure_kPa | 2 | 15751 | 27.82 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4565 | warn | NELSON_R3 | headbox_pressure_kPa | 2 | 16093 | 32.05 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4566 | warn | NELSON_R3 | headbox_pressure_kPa | 2 | 16163 | 23.59 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4567 | warn | NELSON_R3 | headbox_pressure_kPa | 2 | 16230 | 27.53 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4568 | warn | NELSON_R3 | headbox_pressure_kPa | 2 | 16644 | 28.12 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4569 | warn | NELSON_R3 | headbox_pressure_kPa | 2 | 16928 | 27.96 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4570 | warn | NELSON_R3 | headbox_pressure_kPa | 2 | 17864 | 29.72 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4571 | warn | NELSON_R3 | headbox_pressure_kPa | 2 | 18769 | 25.38 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4572 | warn | NELSON_R3 | headbox_pressure_kPa | 2 | 18947 | 30.29 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4573 | warn | NELSON_R3 | headbox_pressure_kPa | 2 | 19320 | 31.15 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4574 | warn | NELSON_R3 | headbox_pressure_kPa | 2 | 19421 | 26.55 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4575 | warn | NELSON_R3 | headbox_pressure_kPa | 2 | 19692 | 30.89 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4576 | warn | NELSON_R3 | headbox_pressure_kPa | 2 | 19958 | 28.41 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4577 | warn | NELSON_R3 | headbox_pressure_kPa | 2 | 20412 | 27.05 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4578 | warn | NELSON_R3 | headbox_pressure_kPa | 2 | 20724 | 37.93 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4579 | warn | NELSON_R3 | headbox_pressure_kPa | 2 | 21410 | 28.76 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4580 | warn | NELSON_R3 | headbox_pressure_kPa | 2 | 21737 | 29.4 | headbox_pressure_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4581 | warn | NELSON_R3 | jet_to_wire_ratio | 2 | 153 | 1.065 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4582 | warn | NELSON_R3 | jet_to_wire_ratio | 2 | 806 | 0.994 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4583 | warn | NELSON_R3 | jet_to_wire_ratio | 2 | 1237 | 1.048 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4584 | warn | NELSON_R3 | jet_to_wire_ratio | 2 | 1494 | 0.989 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4585 | warn | NELSON_R3 | jet_to_wire_ratio | 2 | 2197 | 0.984 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4586 | warn | NELSON_R3 | jet_to_wire_ratio | 2 | 2336 | 0.997 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4587 | warn | NELSON_R3 | jet_to_wire_ratio | 2 | 3343 | 0.994 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4588 | warn | NELSON_R3 | jet_to_wire_ratio | 2 | 3425 | 1.053 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4589 | warn | NELSON_R3 | jet_to_wire_ratio | 2 | 4611 | 0.939 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4590 | warn | NELSON_R3 | jet_to_wire_ratio | 2 | 5203 | 0.977 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4591 | warn | NELSON_R3 | jet_to_wire_ratio | 2 | 6157 | 1.056 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4592 | warn | NELSON_R3 | jet_to_wire_ratio | 2 | 6467 | 0.998 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4593 | warn | NELSON_R3 | jet_to_wire_ratio | 2 | 6895 | 1.064 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4594 | warn | NELSON_R3 | jet_to_wire_ratio | 2 | 7644 | 1.053 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4595 | warn | NELSON_R3 | jet_to_wire_ratio | 2 | 7872 | 0.956 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4596 | warn | NELSON_R3 | jet_to_wire_ratio | 2 | 8590 | 0.956 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4597 | warn | NELSON_R3 | jet_to_wire_ratio | 2 | 9137 | 1.065 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4598 | warn | NELSON_R3 | jet_to_wire_ratio | 2 | 9435 | 1.065 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4599 | warn | NELSON_R3 | jet_to_wire_ratio | 2 | 11372 | 1.031 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4600 | warn | NELSON_R3 | jet_to_wire_ratio | 2 | 11449 | 1.067 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4601 | warn | NELSON_R3 | jet_to_wire_ratio | 2 | 11513 | 1.052 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4602 | warn | NELSON_R3 | jet_to_wire_ratio | 2 | 12074 | 0.973 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4603 | warn | NELSON_R3 | jet_to_wire_ratio | 2 | 12355 | 1.069 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4604 | warn | NELSON_R3 | jet_to_wire_ratio | 2 | 12697 | 0.932 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4605 | warn | NELSON_R3 | jet_to_wire_ratio | 2 | 13494 | 1.07 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4606 | warn | NELSON_R3 | jet_to_wire_ratio | 2 | 13680 | 1.028 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4607 | warn | NELSON_R3 | jet_to_wire_ratio | 2 | 14157 | 1.044 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4608 | warn | NELSON_R3 | jet_to_wire_ratio | 2 | 15327 | 1.047 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4609 | warn | NELSON_R3 | jet_to_wire_ratio | 2 | 15925 | 0.989 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4610 | warn | NELSON_R3 | jet_to_wire_ratio | 2 | 16252 | 0.986 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4611 | warn | NELSON_R3 | jet_to_wire_ratio | 2 | 16344 | 0.963 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4612 | warn | NELSON_R3 | jet_to_wire_ratio | 2 | 16732 | 0.97 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4613 | warn | NELSON_R3 | jet_to_wire_ratio | 2 | 17012 | 0.987 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4614 | warn | NELSON_R3 | jet_to_wire_ratio | 2 | 17913 | 1.061 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4615 | warn | NELSON_R3 | jet_to_wire_ratio | 2 | 18519 | 1.015 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4616 | warn | NELSON_R3 | jet_to_wire_ratio | 2 | 19040 | 0.99 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4617 | warn | NELSON_R3 | jet_to_wire_ratio | 2 | 19814 | 1.072 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4618 | warn | NELSON_R3 | jet_to_wire_ratio | 2 | 19887 | 1.031 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4619 | warn | NELSON_R3 | jet_to_wire_ratio | 2 | 20051 | 0.97 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4620 | warn | NELSON_R3 | jet_to_wire_ratio | 2 | 20423 | 0.971 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4621 | warn | NELSON_R3 | jet_to_wire_ratio | 2 | 20593 | 0.987 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4622 | warn | NELSON_R3 | jet_to_wire_ratio | 2 | 20703 | 1.072 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4623 | warn | NELSON_R3 | jet_to_wire_ratio | 2 | 21147 | 1.007 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4624 | warn | NELSON_R3 | jet_to_wire_ratio | 2 | 21370 | 1.069 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4625 | warn | NELSON_R3 | jet_to_wire_ratio | 2 | 21729 | 1.069 | jet_to_wire_ratio 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4626 | warn | NELSON_R3 | machine_speed_mmin | 2 | 105 | 1707 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4627 | warn | NELSON_R3 | machine_speed_mmin | 2 | 433 | 1300 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4628 | warn | NELSON_R3 | machine_speed_mmin | 2 | 691 | 1689 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4629 | warn | NELSON_R3 | machine_speed_mmin | 2 | 1392 | 1697 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4630 | warn | NELSON_R3 | machine_speed_mmin | 2 | 1525 | 1522 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4631 | warn | NELSON_R3 | machine_speed_mmin | 2 | 1849 | 1704 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4632 | warn | NELSON_R3 | machine_speed_mmin | 2 | 2208 | 1689 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4633 | warn | NELSON_R3 | machine_speed_mmin | 2 | 2401 | 1678 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4634 | warn | NELSON_R3 | machine_speed_mmin | 2 | 2645 | 1324 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4635 | warn | NELSON_R3 | machine_speed_mmin | 2 | 3125 | 1301 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4636 | warn | NELSON_R3 | machine_speed_mmin | 2 | 3800 | 1334 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4637 | warn | NELSON_R3 | machine_speed_mmin | 2 | 4479 | 1494 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4638 | warn | NELSON_R3 | machine_speed_mmin | 2 | 5007 | 1685 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4639 | warn | NELSON_R3 | machine_speed_mmin | 2 | 5165 | 1345 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4640 | warn | NELSON_R3 | machine_speed_mmin | 2 | 5419 | 1701 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4641 | warn | NELSON_R3 | machine_speed_mmin | 2 | 5686 | 1330 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4642 | warn | NELSON_R3 | machine_speed_mmin | 2 | 5813 | 1326 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4643 | warn | NELSON_R3 | machine_speed_mmin | 2 | 6556 | 1705 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4644 | warn | NELSON_R3 | machine_speed_mmin | 2 | 6629 | 1328 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4645 | warn | NELSON_R3 | machine_speed_mmin | 2 | 7411 | 1701 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4646 | warn | NELSON_R3 | machine_speed_mmin | 2 | 7642 | 1530 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4647 | warn | NELSON_R3 | machine_speed_mmin | 2 | 8386 | 1311 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4648 | warn | NELSON_R3 | machine_speed_mmin | 2 | 8608 | 1314 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4649 | warn | NELSON_R3 | machine_speed_mmin | 2 | 8715 | 1710 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4650 | warn | NELSON_R3 | machine_speed_mmin | 2 | 9768 | 1531 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4651 | warn | NELSON_R3 | machine_speed_mmin | 2 | 10089 | 1514 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4652 | warn | NELSON_R3 | machine_speed_mmin | 2 | 10795 | 1302 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4653 | warn | NELSON_R3 | machine_speed_mmin | 2 | 11089 | 1301 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4654 | warn | NELSON_R3 | machine_speed_mmin | 2 | 11832 | 1670 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4655 | warn | NELSON_R3 | machine_speed_mmin | 2 | 12085 | 1700 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4656 | warn | NELSON_R3 | machine_speed_mmin | 2 | 12612 | 1334 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4657 | warn | NELSON_R3 | machine_speed_mmin | 2 | 13109 | 1312 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4658 | warn | NELSON_R3 | machine_speed_mmin | 2 | 14026 | 1313 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4659 | warn | NELSON_R3 | machine_speed_mmin | 2 | 14596 | 1509 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4660 | warn | NELSON_R3 | machine_speed_mmin | 2 | 14798 | 1725 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4661 | warn | NELSON_R3 | machine_speed_mmin | 2 | 15368 | 1311 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4662 | warn | NELSON_R3 | machine_speed_mmin | 2 | 15494 | 1714 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4663 | warn | NELSON_R3 | machine_speed_mmin | 2 | 16177 | 1340 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4664 | warn | NELSON_R3 | machine_speed_mmin | 2 | 16310 | 1694 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4665 | warn | NELSON_R3 | machine_speed_mmin | 2 | 16594 | 1321 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4666 | warn | NELSON_R3 | machine_speed_mmin | 2 | 16922 | 1514 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4667 | warn | NELSON_R3 | machine_speed_mmin | 2 | 17016 | 1321 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4668 | warn | NELSON_R3 | machine_speed_mmin | 2 | 17093 | 1529 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4669 | warn | NELSON_R3 | machine_speed_mmin | 2 | 17923 | 1693 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4670 | warn | NELSON_R3 | machine_speed_mmin | 2 | 18215 | 1732 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4671 | warn | NELSON_R3 | machine_speed_mmin | 2 | 18424 | 1334 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4672 | warn | NELSON_R3 | machine_speed_mmin | 2 | 18490 | 1707 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4673 | warn | NELSON_R3 | machine_speed_mmin | 2 | 18866 | 1692 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4674 | warn | NELSON_R3 | machine_speed_mmin | 2 | 19347 | 1519 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4675 | warn | NELSON_R3 | machine_speed_mmin | 2 | 19814 | 1506 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4676 | warn | NELSON_R3 | machine_speed_mmin | 2 | 20206 | 1684 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4677 | warn | NELSON_R3 | machine_speed_mmin | 2 | 20293 | 1331 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4678 | warn | NELSON_R3 | machine_speed_mmin | 2 | 20530 | 1331 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4679 | warn | NELSON_R3 | machine_speed_mmin | 2 | 20783 | 1307 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4680 | warn | NELSON_R3 | machine_speed_mmin | 2 | 20924 | 1715 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4681 | warn | NELSON_R3 | machine_speed_mmin | 2 | 21031 | 1297 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4682 | warn | NELSON_R3 | machine_speed_mmin | 2 | 21701 | 1712 | machine_speed_mmin 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4683 | warn | NELSON_R3 | stock_temp_C | 2 | 2077 | 45.8 | stock_temp_C 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4684 | warn | NELSON_R3 | stock_temp_C | 2 | 2959 | 47 | stock_temp_C 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4685 | warn | NELSON_R3 | stock_temp_C | 2 | 4047 | 46.5 | stock_temp_C 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4686 | warn | NELSON_R3 | stock_temp_C | 2 | 4307 | 44.8 | stock_temp_C 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4687 | warn | NELSON_R3 | stock_temp_C | 2 | 5791 | 43.2 | stock_temp_C 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4688 | warn | NELSON_R3 | stock_temp_C | 2 | 5856 | 46.9 | stock_temp_C 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4689 | warn | NELSON_R3 | stock_temp_C | 2 | 6298 | 41.1 | stock_temp_C 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4690 | warn | NELSON_R3 | stock_temp_C | 2 | 6749 | 38.4 | stock_temp_C 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4691 | warn | NELSON_R3 | stock_temp_C | 2 | 8210 | 37.4 | stock_temp_C 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4692 | warn | NELSON_R3 | stock_temp_C | 2 | 8487 | 39.6 | stock_temp_C 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4693 | warn | NELSON_R3 | stock_temp_C | 2 | 8696 | 40.3 | stock_temp_C 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4694 | warn | NELSON_R3 | stock_temp_C | 2 | 10701 | 39.2 | stock_temp_C 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4695 | warn | NELSON_R3 | stock_temp_C | 2 | 10849 | 36.2 | stock_temp_C 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4696 | warn | NELSON_R3 | stock_temp_C | 2 | 11995 | 40.1 | stock_temp_C 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4697 | warn | NELSON_R3 | stock_temp_C | 2 | 13678 | 34.2 | stock_temp_C 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4698 | warn | NELSON_R3 | stock_temp_C | 2 | 14017 | 37.1 | stock_temp_C 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4699 | warn | NELSON_R3 | stock_temp_C | 2 | 14155 | 39.6 | stock_temp_C 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4700 | warn | NELSON_R3 | stock_temp_C | 2 | 15605 | 39.5 | stock_temp_C 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4701 | warn | NELSON_R3 | stock_temp_C | 2 | 15991 | 41.3 | stock_temp_C 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4702 | warn | NELSON_R3 | stock_temp_C | 2 | 16234 | 36.7 | stock_temp_C 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4703 | warn | NELSON_R3 | stock_temp_C | 2 | 17079 | 41.1 | stock_temp_C 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4704 | warn | NELSON_R3 | stock_temp_C | 2 | 18817 | 39.8 | stock_temp_C 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4705 | warn | NELSON_R3 | stock_temp_C | 2 | 20694 | 46.9 | stock_temp_C 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4706 | warn | NELSON_R3 | stock_temp_C | 2 | 20773 | 39.8 | stock_temp_C 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4707 | warn | NELSON_R3 | stock_temp_C | 2 | 21198 | 44.2 | stock_temp_C 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4708 | warn | NELSON_R3 | vacuum_pump1_kPa | 2 | 596 | 61.3 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4709 | warn | NELSON_R3 | vacuum_pump1_kPa | 2 | 770 | 56.5 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4710 | warn | NELSON_R3 | vacuum_pump1_kPa | 2 | 1807 | 59.8 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4711 | warn | NELSON_R3 | vacuum_pump1_kPa | 2 | 2181 | 57.7 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4712 | warn | NELSON_R3 | vacuum_pump1_kPa | 2 | 2545 | 44.7 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4713 | warn | NELSON_R3 | vacuum_pump1_kPa | 2 | 2736 | 58.7 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4714 | warn | NELSON_R3 | vacuum_pump1_kPa | 2 | 3315 | 59.7 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4715 | warn | NELSON_R3 | vacuum_pump1_kPa | 2 | 3426 | 45.7 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4716 | warn | NELSON_R3 | vacuum_pump1_kPa | 2 | 3993 | 42.2 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4717 | warn | NELSON_R3 | vacuum_pump1_kPa | 2 | 4342 | 48.4 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4718 | warn | NELSON_R3 | vacuum_pump1_kPa | 2 | 4857 | 43.6 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4719 | warn | NELSON_R3 | vacuum_pump1_kPa | 2 | 5492 | 41.5 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4720 | warn | NELSON_R3 | vacuum_pump1_kPa | 2 | 5593 | 65.7 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4721 | warn | NELSON_R3 | vacuum_pump1_kPa | 2 | 6076 | 58.7 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4722 | warn | NELSON_R3 | vacuum_pump1_kPa | 2 | 6549 | 58.3 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4723 | warn | NELSON_R3 | vacuum_pump1_kPa | 2 | 6887 | 56.5 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4724 | warn | NELSON_R3 | vacuum_pump1_kPa | 2 | 7815 | 61.5 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4725 | warn | NELSON_R3 | vacuum_pump1_kPa | 2 | 8104 | 58.1 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4726 | warn | NELSON_R3 | vacuum_pump1_kPa | 2 | 8333 | 47.5 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4727 | warn | NELSON_R3 | vacuum_pump1_kPa | 2 | 8592 | 58.6 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4728 | warn | NELSON_R3 | vacuum_pump1_kPa | 2 | 9500 | 56.4 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4729 | warn | NELSON_R3 | vacuum_pump1_kPa | 2 | 9638 | 50.4 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4730 | warn | NELSON_R3 | vacuum_pump1_kPa | 2 | 9803 | 53.4 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4731 | warn | NELSON_R3 | vacuum_pump1_kPa | 2 | 9867 | 43.9 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4732 | warn | NELSON_R3 | vacuum_pump1_kPa | 2 | 9974 | 43.1 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4733 | warn | NELSON_R3 | vacuum_pump1_kPa | 2 | 10530 | 47 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4734 | warn | NELSON_R3 | vacuum_pump1_kPa | 2 | 10911 | 50.3 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4735 | warn | NELSON_R3 | vacuum_pump1_kPa | 2 | 11047 | 54.9 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4736 | warn | NELSON_R3 | vacuum_pump1_kPa | 2 | 12823 | 56.6 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4737 | warn | NELSON_R3 | vacuum_pump1_kPa | 2 | 13171 | 47 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4738 | warn | NELSON_R3 | vacuum_pump1_kPa | 2 | 14308 | 60.1 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4739 | warn | NELSON_R3 | vacuum_pump1_kPa | 2 | 14443 | 43.3 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4740 | warn | NELSON_R3 | vacuum_pump1_kPa | 2 | 14590 | 47.1 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4741 | warn | NELSON_R3 | vacuum_pump1_kPa | 2 | 15651 | 42.9 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4742 | warn | NELSON_R3 | vacuum_pump1_kPa | 2 | 16055 | 58.1 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4743 | warn | NELSON_R3 | vacuum_pump1_kPa | 2 | 16342 | 47.3 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4744 | warn | NELSON_R3 | vacuum_pump1_kPa | 2 | 16747 | 43.5 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4745 | warn | NELSON_R3 | vacuum_pump1_kPa | 2 | 18046 | 37.7 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4746 | warn | NELSON_R3 | vacuum_pump1_kPa | 2 | 18117 | 46 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4747 | warn | NELSON_R3 | vacuum_pump1_kPa | 2 | 19297 | 45.8 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4748 | warn | NELSON_R3 | vacuum_pump1_kPa | 2 | 19455 | 46.9 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4749 | warn | NELSON_R3 | vacuum_pump1_kPa | 2 | 19608 | 56.9 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4750 | warn | NELSON_R3 | vacuum_pump1_kPa | 2 | 20763 | 42.8 | vacuum_pump1_kPa 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4751 | warn | NELSON_R3 | white_water_consistency_pct | 2 | 513 | 1.019 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4752 | warn | NELSON_R3 | white_water_consistency_pct | 2 | 678 | 1.046 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4753 | warn | NELSON_R3 | white_water_consistency_pct | 2 | 800 | 1.035 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4754 | warn | NELSON_R3 | white_water_consistency_pct | 2 | 1234 | 0.831 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4755 | warn | NELSON_R3 | white_water_consistency_pct | 2 | 1388 | 0.899 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4756 | warn | NELSON_R3 | white_water_consistency_pct | 2 | 1530 | 0.985 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4757 | warn | NELSON_R3 | white_water_consistency_pct | 2 | 1897 | 0.982 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4758 | warn | NELSON_R3 | white_water_consistency_pct | 2 | 2274 | 1.087 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4759 | warn | NELSON_R3 | white_water_consistency_pct | 2 | 2379 | 1.004 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4760 | warn | NELSON_R3 | white_water_consistency_pct | 2 | 3252 | 0.97 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4761 | warn | NELSON_R3 | white_water_consistency_pct | 2 | 3320 | 1.08 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4762 | warn | NELSON_R3 | white_water_consistency_pct | 2 | 3847 | 1.267 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4763 | warn | NELSON_R3 | white_water_consistency_pct | 2 | 3970 | 1.283 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4764 | warn | NELSON_R3 | white_water_consistency_pct | 2 | 4814 | 0.969 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4765 | warn | NELSON_R3 | white_water_consistency_pct | 2 | 5882 | 1.006 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4766 | warn | NELSON_R3 | white_water_consistency_pct | 2 | 6555 | 1.089 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4767 | warn | NELSON_R3 | white_water_consistency_pct | 2 | 7045 | 1.26 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4768 | warn | NELSON_R3 | white_water_consistency_pct | 2 | 7334 | 1.167 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4769 | warn | NELSON_R3 | white_water_consistency_pct | 2 | 7402 | 1.012 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4770 | warn | NELSON_R3 | white_water_consistency_pct | 2 | 7689 | 1.142 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4771 | warn | NELSON_R3 | white_water_consistency_pct | 2 | 8062 | 1.057 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4772 | warn | NELSON_R3 | white_water_consistency_pct | 2 | 8478 | 1.034 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4773 | warn | NELSON_R3 | white_water_consistency_pct | 2 | 8572 | 1.184 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4774 | warn | NELSON_R3 | white_water_consistency_pct | 2 | 8807 | 0.954 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4775 | warn | NELSON_R3 | white_water_consistency_pct | 2 | 9700 | 1.29 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4776 | warn | NELSON_R3 | white_water_consistency_pct | 2 | 10486 | 0.771 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4777 | warn | NELSON_R3 | white_water_consistency_pct | 2 | 10560 | 0.875 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4778 | warn | NELSON_R3 | white_water_consistency_pct | 2 | 10767 | 1.163 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4779 | warn | NELSON_R3 | white_water_consistency_pct | 2 | 11173 | 0.905 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4780 | warn | NELSON_R3 | white_water_consistency_pct | 2 | 11595 | 0.952 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4781 | warn | NELSON_R3 | white_water_consistency_pct | 2 | 12417 | 0.913 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4782 | warn | NELSON_R3 | white_water_consistency_pct | 2 | 12537 | 1.001 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4783 | warn | NELSON_R3 | white_water_consistency_pct | 2 | 12714 | 1.222 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4784 | warn | NELSON_R3 | white_water_consistency_pct | 2 | 12831 | 1.109 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4785 | warn | NELSON_R3 | white_water_consistency_pct | 2 | 13100 | 0.939 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4786 | warn | NELSON_R3 | white_water_consistency_pct | 2 | 13282 | 1.034 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4787 | warn | NELSON_R3 | white_water_consistency_pct | 2 | 13430 | 1.141 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4788 | warn | NELSON_R3 | white_water_consistency_pct | 2 | 13796 | 1.104 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4789 | warn | NELSON_R3 | white_water_consistency_pct | 2 | 14204 | 1.049 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4790 | warn | NELSON_R3 | white_water_consistency_pct | 2 | 14279 | 1.085 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4791 | warn | NELSON_R3 | white_water_consistency_pct | 2 | 14437 | 1.107 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4792 | warn | NELSON_R3 | white_water_consistency_pct | 2 | 14515 | 0.95 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4793 | warn | NELSON_R3 | white_water_consistency_pct | 2 | 15967 | 1.197 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4794 | warn | NELSON_R3 | white_water_consistency_pct | 2 | 16471 | 1.162 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4795 | warn | NELSON_R3 | white_water_consistency_pct | 2 | 18128 | 1.258 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4796 | warn | NELSON_R3 | white_water_consistency_pct | 2 | 18227 | 1.329 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4797 | warn | NELSON_R3 | white_water_consistency_pct | 2 | 18558 | 1.012 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4798 | warn | NELSON_R3 | white_water_consistency_pct | 2 | 18726 | 0.957 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4799 | warn | NELSON_R3 | white_water_consistency_pct | 2 | 18912 | 1.259 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4800 | warn | NELSON_R3 | white_water_consistency_pct | 2 | 19358 | 1.145 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4801 | warn | NELSON_R3 | white_water_consistency_pct | 2 | 19919 | 1.312 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4802 | warn | NELSON_R3 | white_water_consistency_pct | 2 | 20131 | 0.971 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4803 | warn | NELSON_R3 | white_water_consistency_pct | 2 | 20427 | 1.334 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4804 | warn | NELSON_R3 | white_water_consistency_pct | 2 | 20838 | 1.467 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4805 | warn | NELSON_R3 | white_water_consistency_pct | 2 | 20960 | 1.14 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4806 | warn | NELSON_R3 | white_water_consistency_pct | 2 | 21182 | 1.293 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 4807 | warn | NELSON_R3 | white_water_consistency_pct | 2 | 21803 | 1.104 | white_water_consistency_pct 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |


> 级别语义：`info` 记录级 / `warn` 趋势与待确认趋势 / `high` 统计异常 / `critical` 越规格。
> 本系统为纯分析系统：所有告警仅为建议核查项，不下发任何参数，动作决策由产线（AWS 侧）做出。

## 二、稳态映射（C3）

- **1**：steady=21861
- **2**：marginal=2、steady=21986

## 三、操作窗口投影（C2）

- **C2 漂移投影未启用**：基线中无 operating_windows —— 构建基线时传入 --doe-run-dir 注册 DOE 先验操作窗即可启用（C2 drift projection disabled: no operating_windows in baseline (build with --doe-run-dir to enable)）

## 四、防风暴抑制

合并触发 78 组同 key 重复；静默期 30 行；同类抑制窗口 60 分钟；迟滞 5 点

## 五、告警事件摘要（incidents）

| 事件 | 参数 | 类别 | 峰值级别 | 跨度(行) | 告警数 | 规则 |
|------|------|------|----------|----------|--------|------|
| EVT-20261005081302-003 | machine_speed_mmin | spc | high | 5260 | 171 | NELSON_R1、NELSON_R2、NELSON_R5… |
| EVT-20261005081302-112 | machine_speed_mmin | spc | high | 4895 | 157 | NELSON_R2、NELSON_R1、NELSON_R5… |
| EVT-20261005081302-397 | machine_speed_mmin | spc | high | 4423 | 144 | NELSON_R1、NELSON_R2、NELSON_R5… |
| EVT-20261005081302-361 | machine_speed_mmin | spc | high | 4016 | 133 | NELSON_R1、NELSON_R2、NELSON_R5… |
| EVT-20261005081302-666 | machine_speed_mmin | spc | high | 3068 | 100 | NELSON_R1、NELSON_R2、NELSON_R5… |
| EVT-20261005081302-004 | machine_speed_mmin | spc | high | 2728 | 90 | NELSON_R1、NELSON_R2、NELSON_R5… |
| EVT-20261005081302-937 | machine_speed_mmin | spc | high | 2444 | 80 | NELSON_R1、NELSON_R2、NELSON_R5… |
| EVT-20261005081302-575 | machine_speed_mmin | spc | high | 1621 | 62 | NELSON_R2、NELSON_R1、NELSON_R5… |
| EVT-20261005081302-010 | stock_temp_C | spc | high | 2795 | 61 | NELSON_R2、NELSON_R5、NELSON_R1… |
| EVT-20261005081302-051 | headbox_pressure_kPa | spc | high | 1788 | 55 | NELSON_R5、NELSON_R1、NELSON_R6… |
| EVT-20261005081302-224 | machine_speed_mmin | spc | high | 1686 | 55 | NELSON_R1、NELSON_R2、NELSON_R5… |
| EVT-20261005081302-008 | headbox_pressure_kPa | spc | high | 1588 | 50 | NELSON_R2、NELSON_R1、NELSON_R5… |

（其余 1033 个事件见 alert.json 的 events 数组；完整逐段告警在 alerts 数组，契约不变）

## 六、建议后续动作

- 有 `high`/`critical` 告警：按告警中的 `suggested_check` 现场核查；需要根因分析时转 `industrial-diagnostician`，需要参数窗口/工况数据分析时转 `industrial-doe-analyzer`。
- 事件摘要按峰值级别与告警数排序；完整逐段告警在 alert.json 的 `alerts` 数组（契约不变），事件视图在 `events` 数组。
- 本报告由脚本生成（`authored_by: script`）；代理只允许追加中文 `interpretation` 注记，禁止改动任何数值字段。
