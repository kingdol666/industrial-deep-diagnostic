# 产线哨兵巡检报告（watch 模式）

- **生成时间**：2026-10-01T17:46:26.733087+00:00
- **总体状态**：**alert** · 告警数 **11**
- **数据**：`D:\codes\myskills\industrial-deep-diagnostic\workspace\e2e-closedloop-t4\e2e\sentinel\window_fault.csv`（10000 行；时间列 t；分组列 -）
- **基线**：模式：prior（v1.0.0），路径：D:\codes\myskills\industrial-deep-diagnostic\workspace\closedloop\sentinel\baselines\L1-UI\watch_baseline.json
- **耗时**：52 ms（零 LLM / 零网络，全部统计由确定性脚本计算）


## 一、告警清单

| # | 级别 | 规则 | 参数/指标 | 分组 | 位置 | 观测值 | 建议 |
|---|------|------|-----------|------|------|--------|------|
| 1 | critical | WINDOW_OUT_OF_RANGE | temp | __ALL__ | - | 88.45 | temp 当前值 88.45 已越出操作窗口 [82.0, 82.75]，请立即核实工艺状态 |
| 2 | high | ROBUST_Z_OUTLIER | temp | __ALL__ | 3160 | 85.13 | temp 稳健 z 分数 \|3.64\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 3 | high | ROBUST_Z_OUTLIER | temp | __ALL__ | 9996 | 89.22 | temp 稳健 z 分数 \|118.64\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 4 | high | NELSON_R1 | temp | __ALL__ | 3110 | 85.09 | temp 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 5 | high | NELSON_R1 | temp | __ALL__ | 9999 | 89.18 | temp 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 6 | high | NELSON_R5 | temp | __ALL__ | 3123 | 85.06 | temp 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 7 | high | NELSON_R5 | temp | __ALL__ | 9999 | 89.18 | temp 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 8 | high | NELSON_R6 | temp | __ALL__ | 3066 | 85.05 | temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 9 | high | NELSON_R6 | temp | __ALL__ | 9999 | 89.18 | temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 10 | warn | VARIANCE_RATIO_HIGH | temp | __ALL__ | - | 1.398 | temp 稳态段标准差为基线的 77.7 倍，离散度显著升高，建议检查波动来源 |
| 11 | warn | NELSON_R2 | temp | __ALL__ | 3044 | 85.05 | temp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |


> 级别语义：`info` 记录级 / `warn` 趋势与待确认趋势 / `high` 统计异常 / `critical` 越规格。
> 本系统为纯分析系统：所有告警仅为建议核查项，不下发任何参数，动作决策由产线（AWS 侧）做出。

## 二、稳态映射（C3）

- **__ALL__**：steady=10000

## 三、操作窗口投影（C2）

- **temp**：当前 88.45，斜率 27.6/h，距边界 0.0 h（级别 critical）

## 四、防风暴抑制

合并触发 5 组同 key 重复；静默期 30 行；同类抑制窗口 60 分钟；迟滞 5 点

## 五、建议后续动作

- 有 `high`/`critical` 告警：按告警中的 `suggested_check` 现场核查；需要根因分析时转 `industrial-diagnostician`，需要参数窗口/工况数据分析时转 `industrial-doe-analyzer`。
- 本报告由脚本生成（`authored_by: script`）；代理只允许追加中文 `interpretation` 注记，禁止改动任何数值字段。
