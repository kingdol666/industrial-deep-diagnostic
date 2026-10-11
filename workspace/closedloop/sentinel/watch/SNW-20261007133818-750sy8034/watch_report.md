# 产线哨兵巡检报告（watch 模式）

- **生成时间**：2026-10-07T13:38:21.382393+00:00
- **总体状态**：**alert** · 告警数 **30**
- **数据**：`D:\codes\industrial-deep-diagnostic\workspace\aw-exchange\inj-r2.csv`（269 行；时间列 time；分组列 -）
- **基线**：模式：prior（v1.0.0），路径：D:\codes\industrial-deep-diagnostic\workspace\closedloop\sentinel\baselines\inj-weight-ln5b\watch_baseline.json
- **耗时**：77 ms（零 LLM / 零网络，全部统计由确定性脚本计算）


## 一、告警清单

| # | 级别 | 规则 | 参数/指标 | 分组 | 位置 | 观测值 | 建议 |
|---|------|------|-----------|------|------|--------|------|
| 1 | high | ROBUST_Z_OUTLIER | 注塑·SP注射速度回读(dn-9ebe1c76) | __ALL__ | 0 | 100 | 注塑·SP注射速度回读(dn-9ebe1c76) 稳健 z 分数 \|4.61\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 2 | high | ROBUST_Z_OUTLIER | 注塑·制品克重(dn-5ec3ed17) | __ALL__ | 37 | 31.78 | 注塑·制品克重(dn-5ec3ed17) 稳健 z 分数 \|-11.53\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 3 | high | ROBUST_Z_OUTLIER | 注塑·制品克重(dn-5ec3ed17) | __ALL__ | 132 | 32.27 | 注塑·制品克重(dn-5ec3ed17) 稳健 z 分数 \|-4.09\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 4 | high | ROBUST_Z_OUTLIER | 注塑·模具温度PV(dn-76a63d2c) | __ALL__ | 177 | 30.9 | 注塑·模具温度PV(dn-76a63d2c) 稳健 z 分数 \|-43.98\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 5 | high | ROBUST_Z_OUTLIER | 注塑·注射压力(dn-9e70726e) | __ALL__ | 50 | 66.5 | 注塑·注射压力(dn-9e70726e) 稳健 z 分数 \|10.92\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 6 | high | ROBUST_Z_OUTLIER | 注塑·缩痕率(dn-72bfca8c) | __ALL__ | 17 | 1.96 | 注塑·缩痕率(dn-72bfca8c) 稳健 z 分数 \|3.83\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 7 | high | ROBUST_Z_OUTLIER | 注塑·飞边率(dn-1c371346) | __ALL__ | 101 | 0.091 | 注塑·飞边率(dn-1c371346) 稳健 z 分数 \|3.75\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 8 | high | NELSON_R1 | 注塑·缩痕率(dn-72bfca8c) | __ALL__ | 4 | 1.71 | 注塑·缩痕率(dn-72bfca8c) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 9 | high | NELSON_R1 | 注塑·飞边率(dn-1c371346) | __ALL__ | 82 | 0.059 | 注塑·飞边率(dn-1c371346) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 10 | high | NELSON_R1 | 注塑·飞边率(dn-1c371346) | __ALL__ | 197 | 0.063 | 注塑·飞边率(dn-1c371346) 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 11 | high | NELSON_R5 | 注塑·飞边率(dn-1c371346) | __ALL__ | 43 | 0.044 | 注塑·飞边率(dn-1c371346) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 12 | high | NELSON_R5 | 注塑·飞边率(dn-1c371346) | __ALL__ | 184 | 0 | 注塑·飞边率(dn-1c371346) 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 13 | high | NELSON_R6 | 注塑·注射压力(dn-9e70726e) | __ALL__ | 229 | 63.3 | 注塑·注射压力(dn-9e70726e) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 14 | high | NELSON_R6 | 注塑·熔体温度(dn-4a69619f) | __ALL__ | 6 | 224.2 | 注塑·熔体温度(dn-4a69619f) 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 15 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 123 | - | __ALL__ 组在第 123 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 16 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 143 | - | __ALL__ 组在第 143 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 17 | warn | NELSON_R2 | 注塑·SP保压压力回读(dn-b21e20cb) | __ALL__ | 8 | 50 | 注塑·SP保压压力回读(dn-b21e20cb) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 18 | warn | NELSON_R2 | 注塑·SP模温回读(dn-0065481e) | __ALL__ | 8 | 32 | 注塑·SP模温回读(dn-0065481e) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 19 | warn | NELSON_R2 | 注塑·SP注射速度回读(dn-9ebe1c76) | __ALL__ | 8 | 100 | 注塑·SP注射速度回读(dn-9ebe1c76) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 20 | warn | NELSON_R2 | 注塑·制品克重(dn-5ec3ed17) | __ALL__ | 9 | 31.83 | 注塑·制品克重(dn-5ec3ed17) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 21 | warn | NELSON_R2 | 注塑·制品克重(dn-5ec3ed17) | __ALL__ | 183 | 32.27 | 注塑·制品克重(dn-5ec3ed17) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 22 | warn | NELSON_R2 | 注塑·模具温度PV(dn-76a63d2c) | __ALL__ | 8 | 31.7 | 注塑·模具温度PV(dn-76a63d2c) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 23 | warn | NELSON_R2 | 注塑·注射压力(dn-9e70726e) | __ALL__ | 8 | 64.1 | 注塑·注射压力(dn-9e70726e) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 24 | warn | NELSON_R2 | 注塑·熔体温度(dn-4a69619f) | __ALL__ | 8 | 224.8 | 注塑·熔体温度(dn-4a69619f) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 25 | warn | NELSON_R2 | 注塑·熔体温度(dn-4a69619f) | __ALL__ | 239 | 225.1 | 注塑·熔体温度(dn-4a69619f) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 26 | warn | NELSON_R2 | 注塑·缩痕率(dn-72bfca8c) | __ALL__ | 9 | 1.66 | 注塑·缩痕率(dn-72bfca8c) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 27 | warn | NELSON_R2 | 注塑·节拍(dn-b12e8f1d) | __ALL__ | 8 | 12.8 | 注塑·节拍(dn-b12e8f1d) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 28 | warn | NELSON_R2 | 注塑·节拍(dn-b12e8f1d) | __ALL__ | 181 | 12.8 | 注塑·节拍(dn-b12e8f1d) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 29 | warn | NELSON_R2 | 注塑·飞边率(dn-1c371346) | __ALL__ | 11 | 0 | 注塑·飞边率(dn-1c371346) 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 30 | warn | NELSON_R3 | 注塑·缩痕率(dn-72bfca8c) | __ALL__ | 230 | 1.3 | 注塑·缩痕率(dn-72bfca8c) 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |


> 级别语义：`info` 记录级 / `warn` 趋势与待确认趋势 / `high` 统计异常 / `critical` 越规格。
> 本系统为纯分析系统：所有告警仅为建议核查项，不下发任何参数，动作决策由产线（AWS 侧）做出。

## 二、稳态映射（C3）

- **__ALL__**：steady=247、transition=22

## 三、操作窗口投影（C2）

- **C2 漂移投影未启用**：基线中无 operating_windows —— 构建基线时传入 --doe-run-dir 注册 DOE 先验操作窗即可启用（C2 drift projection disabled: no operating_windows in baseline (build with --doe-run-dir to enable)）

## 四、防风暴抑制

合并触发 10 组同 key 重复；静默期 30 行；同类抑制窗口 60 分钟；迟滞 5 点

## 五、告警事件摘要（incidents）

| 事件 | 参数 | 类别 | 峰值级别 | 跨度(行) | 告警数 | 规则 |
|------|------|------|----------|----------|--------|------|
| EVT-20261007133821-011 | 注塑·飞边率(dn-1c371346) | spc | high | 186 | 5 | NELSON_R2、NELSON_R5、NELSON_R1 |
| EVT-20261007133821-002 | 注塑·缩痕率(dn-72bfca8c) | spc | high | 5 | 2 | NELSON_R1、NELSON_R2 |
| EVT-20261007133821-003 | 注塑·熔体温度(dn-4a69619f) | spc | high | 2 | 2 | NELSON_R6、NELSON_R2 |
| EVT-20261007133821-013 | 注塑·制品克重(dn-5ec3ed17) | multivariate | high | 95 | 2 | ROBUST_Z_OUTLIER |
| EVT-20261007133821-001 | 注塑·SP注射速度回读(dn-9ebe1c76) | multivariate | high | 0 | 1 | ROBUST_Z_OUTLIER |
| EVT-20261007133821-012 | 注塑·缩痕率(dn-72bfca8c) | multivariate | high | 0 | 1 | ROBUST_Z_OUTLIER |
| EVT-20261007133821-014 | 注塑·注射压力(dn-9e70726e) | multivariate | high | 0 | 1 | ROBUST_Z_OUTLIER |
| EVT-20261007133821-015 | 注塑·飞边率(dn-1c371346) | multivariate | high | 0 | 1 | ROBUST_Z_OUTLIER |
| EVT-20261007133821-017 | 注塑·模具温度PV(dn-76a63d2c) | multivariate | high | 0 | 1 | ROBUST_Z_OUTLIER |
| EVT-20261007133821-020 | 注塑·注射压力(dn-9e70726e) | spc | high | 0 | 1 | NELSON_R6 |
| EVT-20261007133821-016 | - | regime | warn | 20 | 2 | REGIME_CHANGE_NEW |
| EVT-20261007133821-004 | 注塑·SP保压压力回读(dn-b21e20cb) | spc | warn | 0 | 1 | NELSON_R2 |

（其余 10 个事件见 alert.json 的 events 数组；完整逐段告警在 alerts 数组，契约不变）

## 六、建议后续动作

- 有 `high`/`critical` 告警：按告警中的 `suggested_check` 现场核查；需要根因分析时转 `industrial-diagnostician`，需要参数窗口/工况数据分析时转 `industrial-doe-analyzer`。
- 事件摘要按峰值级别与告警数排序；完整逐段告警在 alert.json 的 `alerts` 数组（契约不变），事件视图在 `events` 数组。
- 本报告由脚本生成（`authored_by: script`）；代理只允许追加中文 `interpretation` 注记，禁止改动任何数值字段。
