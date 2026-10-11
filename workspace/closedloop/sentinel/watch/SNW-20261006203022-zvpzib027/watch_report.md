# 产线哨兵巡检报告（watch 模式）

- **生成时间**：2026-10-06T20:30:22.752536+00:00
- **总体状态**：**alert** · 告警数 **53**
- **数据**：`D:\codes\industrial-deep-diagnostic\workspace\aw-exchange\line1_melt_step227_screen_20261007_0305-0415.csv`（2048 行；时间列 time；分组列 -）
- **基线**：模式：prior（v1.0.0），路径：D:\codes\industrial-deep-diagnostic\workspace\closedloop\sentinel\baselines\演示线1\watch_baseline.json
- **耗时**：28 ms（零 LLM / 零网络，全部统计由确定性脚本计算）


## 一、告警清单

| # | 级别 | 规则 | 参数/指标 | 分组 | 位置 | 观测值 | 建议 |
|---|------|------|-----------|------|------|--------|------|
| 1 | high | ROBUST_Z_OUTLIER | melt_temp | __ALL__ | 142 | 190.2 | melt_temp 稳健 z 分数 \|-26.69\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 2 | high | NELSON_R1 | dot_count | __ALL__ | 1035 | 9 | dot_count 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 3 | high | NELSON_R1 | melt_temp | __ALL__ | 312 | 206.6 | melt_temp 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 4 | high | NELSON_R1 | melt_temp | __ALL__ | 559 | 209 | melt_temp 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 5 | high | NELSON_R1 | melt_temp | __ALL__ | 879 | 209.1 | melt_temp 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 6 | high | NELSON_R1 | melt_temp | __ALL__ | 1083 | 206.6 | melt_temp 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 7 | high | NELSON_R1 | melt_temp | __ALL__ | 1532 | 206.7 | melt_temp 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 8 | high | NELSON_R1 | melt_temp | __ALL__ | 1707 | 206.7 | melt_temp 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 9 | high | NELSON_R1 | melt_temp | __ALL__ | 1958 | 209 | melt_temp 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 10 | high | NELSON_R5 | melt_temp | __ALL__ | 783 | 207.6 | melt_temp 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 11 | high | NELSON_R5 | melt_temp | __ALL__ | 978 | 206.8 | melt_temp 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 12 | high | NELSON_R5 | melt_temp | __ALL__ | 1235 | 208.5 | melt_temp 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 13 | high | NELSON_R5 | melt_temp | __ALL__ | 1357 | 208.7 | melt_temp 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 14 | high | NELSON_R5 | melt_temp | __ALL__ | 1818 | 207.6 | melt_temp 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 15 | high | NELSON_R5 | melt_temp | __ALL__ | 1979 | 208.3 | melt_temp 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 16 | high | NELSON_R6 | dot_count | __ALL__ | 42 | 4 | dot_count 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 17 | high | NELSON_R6 | dot_count | __ALL__ | 309 | 2 | dot_count 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 18 | high | NELSON_R6 | dot_count | __ALL__ | 943 | 6 | dot_count 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 19 | high | NELSON_R6 | dot_count | __ALL__ | 1100 | 2 | dot_count 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 20 | high | NELSON_R6 | dot_count | __ALL__ | 1498 | 1 | dot_count 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 21 | high | NELSON_R6 | dot_count | __ALL__ | 1580 | 4 | dot_count 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 22 | high | NELSON_R6 | dot_count | __ALL__ | 1869 | 6 | dot_count 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 23 | high | NELSON_R6 | dot_count | __ALL__ | 1983 | 0 | dot_count 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 24 | high | NELSON_R6 | melt_temp | __ALL__ | 401 | 208.4 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 25 | high | NELSON_R6 | melt_temp | __ALL__ | 835 | 207.4 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 26 | high | NELSON_R6 | melt_temp | __ALL__ | 1155 | 207.6 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 27 | high | NELSON_R6 | melt_temp | __ALL__ | 1224 | 207.2 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 28 | high | NELSON_R6 | melt_temp | __ALL__ | 1540 | 208.6 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 29 | high | NELSON_R6 | melt_temp | __ALL__ | 1960 | 208.4 | melt_temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 30 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 185 | - | __ALL__ 组在第 185 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 31 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 208 | - | __ALL__ 组在第 208 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 32 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 241 | - | __ALL__ 组在第 241 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 33 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 336 | - | __ALL__ 组在第 336 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 34 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 63 | - | __ALL__ 组在第 63 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 35 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 87 | - | __ALL__ 组在第 87 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 36 | warn | VARIANCE_RATIO_HIGH | melt_temp | __ALL__ | - | 4.316 | melt_temp 稳态段标准差为基线的 10.8 倍，离散度显著升高，建议检查波动来源 |
| 37 | warn | NELSON_R2 | dot_count | __ALL__ | 40 | 2 | dot_count 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 38 | warn | NELSON_R2 | dot_count | __ALL__ | 160 | 4 | dot_count 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 39 | warn | NELSON_R2 | dot_count | __ALL__ | 292 | 2 | dot_count 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 40 | warn | NELSON_R2 | dot_count | __ALL__ | 496 | 6 | dot_count 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 41 | warn | NELSON_R2 | dot_count | __ALL__ | 602 | 5 | dot_count 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 42 | warn | NELSON_R2 | dot_count | __ALL__ | 1083 | 5 | dot_count 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 43 | warn | NELSON_R2 | dot_count | __ALL__ | 1679 | 4 | dot_count 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 44 | warn | NELSON_R2 | dot_count | __ALL__ | 1836 | 6 | dot_count 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 45 | warn | NELSON_R2 | dot_count | __ALL__ | 1900 | 6 | dot_count 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 46 | warn | NELSON_R2 | dot_count | __ALL__ | 1975 | 5 | dot_count 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 47 | warn | NELSON_R2 | melt_temp | __ALL__ | 8 | 191.7 | melt_temp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 48 | warn | NELSON_R2 | melt_temp | __ALL__ | 299 | 207 | melt_temp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 49 | warn | NELSON_R2 | melt_temp | __ALL__ | 718 | 208.3 | melt_temp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 50 | warn | NELSON_R2 | melt_temp | __ALL__ | 1924 | 208.1 | melt_temp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 51 | warn | NELSON_R3 | melt_temp | __ALL__ | 183 | 198.4 | melt_temp 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 52 | warn | NELSON_R3 | melt_temp | __ALL__ | 1066 | 208.7 | melt_temp 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 53 | warn | NELSON_R3 | melt_temp | __ALL__ | 1770 | 208.2 | melt_temp 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |


> 级别语义：`info` 记录级 / `warn` 趋势与待确认趋势 / `high` 统计异常 / `critical` 越规格。
> 本系统为纯分析系统：所有告警仅为建议核查项，不下发任何参数，动作决策由产线（AWS 侧）做出。

## 二、稳态映射（C3）

- **__ALL__**：abnormal=11、marginal=5、steady=1966、transition=66

## 三、操作窗口投影（C2）

- **C2 漂移投影未启用**：基线中无 operating_windows —— 构建基线时传入 --doe-run-dir 注册 DOE 先验操作窗即可启用（C2 drift projection disabled: no operating_windows in baseline (build with --doe-run-dir to enable)）

## 四、防风暴抑制

合并触发 7 组同 key 重复；静默期 30 行；同类抑制窗口 60 分钟；迟滞 5 点

## 五、告警事件摘要（incidents）

| 事件 | 参数 | 类别 | 峰值级别 | 跨度(行) | 告警数 | 规则 |
|------|------|------|----------|----------|--------|------|
| EVT-20261006203022-010 | melt_temp | spc | high | 517 | 10 | NELSON_R2、NELSON_R5、NELSON_R6… |
| EVT-20261006203022-015 | melt_temp | spc | high | 272 | 7 | NELSON_R1、NELSON_R3、NELSON_R5… |
| EVT-20261006203022-016 | dot_count | spc | high | 147 | 5 | NELSON_R2、NELSON_R6 |
| EVT-20261006203022-006 | melt_temp | spc | high | 218 | 4 | NELSON_R3、NELSON_R2、NELSON_R1… |
| EVT-20261006203022-011 | dot_count | spc | high | 157 | 4 | NELSON_R6、NELSON_R1、NELSON_R2 |
| EVT-20261006203022-003 | dot_count | spc | high | 120 | 3 | NELSON_R2、NELSON_R6 |
| EVT-20261006203022-013 | dot_count | spc | high | 181 | 3 | NELSON_R6、NELSON_R2 |
| EVT-20261006203022-007 | dot_count | spc | high | 17 | 2 | NELSON_R2、NELSON_R6 |
| EVT-20261006203022-014 | melt_temp | spc | high | 8 | 2 | NELSON_R1、NELSON_R6 |
| EVT-20261006203022-005 | melt_temp | multivariate | high | 0 | 1 | ROBUST_Z_OUTLIER |
| EVT-20261006203022-009 | melt_temp | spc | high | 0 | 1 | NELSON_R1 |
| EVT-20261006203022-012 | melt_temp | spc | high | 0 | 1 | NELSON_R5 |

（其余 4 个事件见 alert.json 的 events 数组；完整逐段告警在 alerts 数组，契约不变）

## 六、建议后续动作

- 有 `high`/`critical` 告警：按告警中的 `suggested_check` 现场核查；需要根因分析时转 `industrial-diagnostician`，需要参数窗口/工况数据分析时转 `industrial-doe-analyzer`。
- 事件摘要按峰值级别与告警数排序；完整逐段告警在 alert.json 的 `alerts` 数组（契约不变），事件视图在 `events` 数组。
- 本报告由脚本生成（`authored_by: script`）；代理只允许追加中文 `interpretation` 注记，禁止改动任何数值字段。
