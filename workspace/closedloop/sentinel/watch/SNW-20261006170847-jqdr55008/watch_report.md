# 产线哨兵巡检报告（watch 模式）

- **生成时间**：2026-10-06T17:08:48.300395+00:00
- **总体状态**：**alert** · 告警数 **23**
- **数据**：`D:\codes\industrial-deep-diagnostic\workspace\aw-exchange\line1-merged-ascii-20261007T005537Z.csv`（1741 行；时间列 time；分组列 -）
- **基线**：模式：prior（v1.0.0），路径：D:\codes\industrial-deep-diagnostic\workspace\closedloop\sentinel\baselines\演示线1·挤出主机PLC(Modbus TCP)\watch_baseline.json
- **耗时**：44 ms（零 LLM / 零网络，全部统计由确定性脚本计算）


## 一、告警清单

| # | 级别 | 规则 | 参数/指标 | 分组 | 位置 | 观测值 | 建议 |
|---|------|------|-----------|------|------|--------|------|
| 1 | high | ROBUST_Z_OUTLIER | gel_count | __ALL__ | 1292 | 0 | gel_count 稳健 z 分数 \|-3.93\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 2 | high | ROBUST_Z_OUTLIER | gel_count | __ALL__ | 1527 | 0 | gel_count 稳健 z 分数 \|-3.93\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 3 | high | ROBUST_Z_OUTLIER | gel_count | __ALL__ | 1667 | 0 | gel_count 稳健 z 分数 \|-3.93\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 4 | high | NELSON_R1 | gel_count | __ALL__ | 1055 | 2 | gel_count 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 5 | high | NELSON_R1 | gel_count | __ALL__ | 1164 | 6 | gel_count 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 6 | high | NELSON_R1 | gel_count | __ALL__ | 1333 | 6 | gel_count 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 7 | high | NELSON_R5 | gel_count | __ALL__ | 1063 | 3 | gel_count 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 8 | high | NELSON_R5 | gel_count | __ALL__ | 1165 | 4 | gel_count 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 9 | high | NELSON_R5 | gel_count | __ALL__ | 1336 | 4 | gel_count 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 10 | high | NELSON_R6 | gel_count | __ALL__ | 1063 | 3 | gel_count 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 11 | high | NELSON_R6 | gel_count | __ALL__ | 1170 | 4 | gel_count 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 12 | high | NELSON_R6 | gel_count | __ALL__ | 1335 | 2 | gel_count 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 13 | high | NELSON_R6 | gel_count | __ALL__ | 1469 | 4 | gel_count 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 14 | high | NELSON_R6 | gel_count | __ALL__ | 1619 | 4 | gel_count 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 15 | high | NELSON_R6 | gel_count | __ALL__ | 1736 | 3 | gel_count 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 16 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 1024 | - | __ALL__ 组在第 1024 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 17 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 1106 | - | __ALL__ 组在第 1106 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 18 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 1134 | - | __ALL__ 组在第 1134 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 19 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 1268 | - | __ALL__ 组在第 1268 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 20 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 1300 | - | __ALL__ 组在第 1300 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 21 | warn | NELSON_R2 | gel_count | __ALL__ | 8 | 5 | gel_count 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 22 | warn | NELSON_R2 | gel_count | __ALL__ | 1392 | 4 | gel_count 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 23 | warn | NELSON_R2 | gel_count | __ALL__ | 1618 | 6 | gel_count 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |


> 级别语义：`info` 记录级 / `warn` 趋势与待确认趋势 / `high` 统计异常 / `critical` 越规格。
> 本系统为纯分析系统：所有告警仅为建议核查项，不下发任何参数，动作决策由产线（AWS 侧）做出。

## 二、稳态映射（C3）

- **__ALL__**：steady=1741

## 三、操作窗口投影（C2）

- **C2 漂移投影未启用**：基线中无 operating_windows —— 构建基线时传入 --doe-run-dir 注册 DOE 先验操作窗即可启用（C2 drift projection disabled: no operating_windows in baseline (build with --doe-run-dir to enable)）

## 四、防风暴抑制

合并触发 5 组同 key 重复；静默期 30 行；同类抑制窗口 60 分钟；迟滞 5 点

## 五、告警事件摘要（incidents）

| 事件 | 参数 | 类别 | 峰值级别 | 跨度(行) | 告警数 | 规则 |
|------|------|------|----------|----------|--------|------|
| EVT-20261006170848-003 | gel_count | spc | high | 115 | 6 | NELSON_R1、NELSON_R5、NELSON_R6 |
| EVT-20261006170848-006 | gel_count | spc | high | 136 | 5 | NELSON_R1、NELSON_R6、NELSON_R5… |
| EVT-20261006170848-008 | gel_count | spc | high | 118 | 3 | NELSON_R2、NELSON_R6 |
| EVT-20261006170848-005 | gel_count | multivariate | high | 0 | 1 | ROBUST_Z_OUTLIER |
| EVT-20261006170848-007 | gel_count | multivariate | high | 0 | 1 | ROBUST_Z_OUTLIER |
| EVT-20261006170848-009 | gel_count | multivariate | high | 0 | 1 | ROBUST_Z_OUTLIER |
| EVT-20261006170848-002 | - | regime | warn | 110 | 3 | REGIME_CHANGE_NEW |
| EVT-20261006170848-004 | - | regime | warn | 32 | 2 | REGIME_CHANGE_NEW |
| EVT-20261006170848-001 | gel_count | spc | warn | 0 | 1 | NELSON_R2 |

## 六、建议后续动作

- 有 `high`/`critical` 告警：按告警中的 `suggested_check` 现场核查；需要根因分析时转 `industrial-diagnostician`，需要参数窗口/工况数据分析时转 `industrial-doe-analyzer`。
- 事件摘要按峰值级别与告警数排序；完整逐段告警在 alert.json 的 `alerts` 数组（契约不变），事件视图在 `events` 数组。
- 本报告由脚本生成（`authored_by: script`）；代理只允许追加中文 `interpretation` 注记，禁止改动任何数值字段。
