# 产线哨兵巡检报告（watch 模式）

- **生成时间**：2026-10-10T02:52:13.312773+00:00
- **总体状态**：**alert** · 告警数 **12**
- **数据**：`D:\codes\industrial-deep-diagnostic\.claude\skills\industrial-sentinel\tests\fixtures\T7_events_ar1\watch.csv`（200 行；时间列 ts；分组列 -）
- **基线**：模式：prior（v1.0.0），路径：D:\codes\industrial-deep-diagnostic\.claude\skills\industrial-sentinel\tests\fixtures\T7_events_ar1\watch_baseline.json
- **耗时**：22 ms（零 LLM / 零网络，全部统计由确定性脚本计算）


## 一、告警清单

| # | 级别 | 规则 | 参数/指标 | 分组 | 位置 | 观测值 | 建议 |
|---|------|------|-----------|------|------|--------|------|
| 1 | high | ROBUST_Z_OUTLIER | temp | __ALL__ | 15 | 55.08 | temp 稳健 z 分数 \|3.65\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 2 | high | NELSON_R1 | temp | __ALL__ | 39 | 52.82 | temp 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 3 | high | NELSON_R1 | temp | __ALL__ | 181 | 51.73 | temp 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 4 | high | NELSON_R5 | temp | __ALL__ | 164 | 55.2 | temp 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 5 | high | NELSON_R6 | temp | __ALL__ | 165 | 54.46 | temp 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 6 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 130 | - | __ALL__ 组在第 130 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 7 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 74 | - | __ALL__ 组在第 74 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 8 | warn | NELSON_R2 | temp | __ALL__ | 8 | 53.54 | temp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 9 | warn | NELSON_R2 | temp | __ALL__ | 168 | 54.39 | temp 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 10 | warn | NELSON_R3 | temp | __ALL__ | 10 | 52.75 | temp 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 11 | warn | NELSON_R3 | temp | __ALL__ | 111 | 54.41 | temp 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |
| 12 | warn | NELSON_R3 | temp | __ALL__ | 193 | 55.2 | temp 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |


> 级别语义：`info` 记录级 / `warn` 趋势与待确认趋势 / `high` 统计异常 / `critical` 越规格。
> 本系统为纯分析系统：所有告警仅为建议核查项，不下发任何参数，动作决策由产线（AWS 侧）做出。

## 二、稳态映射（C3）

- **__ALL__**：steady=200

## 三、操作窗口投影（C2）

- **C2 漂移投影未启用**：基线中无 operating_windows —— 构建基线时传入 --doe-run-dir 注册 DOE 先验操作窗即可启用（C2 drift projection disabled: no operating_windows in baseline (build with --doe-run-dir to enable)）

## 四、防风暴抑制

合并触发 6 组同 key 重复；静默期 30 行；同类抑制窗口 60 分钟；迟滞 5 点

## 五、告警事件摘要（incidents）

| 事件 | 参数 | 类别 | 峰值级别 | 跨度(行) | 告警数 | 规则 |
|------|------|------|----------|----------|--------|------|
| EVT-20261010025213-001 | temp | spc | high | 185 | 9 | NELSON_R2、NELSON_R3、NELSON_R1… |
| EVT-20261010025213-002 | temp | multivariate | high | 0 | 1 | ROBUST_Z_OUTLIER |
| EVT-20261010025213-003 | - | regime | warn | 56 | 2 | REGIME_CHANGE_NEW |

## 六、建议后续动作

- 有 `high`/`critical` 告警：按告警中的 `suggested_check` 现场核查；需要根因分析时转 `industrial-diagnostician`，需要参数窗口/工况数据分析时转 `industrial-doe-analyzer`。
- 事件摘要按峰值级别与告警数排序；完整逐段告警在 alert.json 的 `alerts` 数组（契约不变），事件视图在 `events` 数组。
- 本报告由脚本生成（`authored_by: script`）；代理只允许追加中文 `interpretation` 注记，禁止改动任何数值字段。
