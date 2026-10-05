# 产线哨兵巡检报告（watch 模式）

- **生成时间**：2026-10-04T06:36:23.637062+00:00
- **总体状态**：**alert** · 告警数 **9**
- **数据**：`D:\codes\industrial-deep-diagnostic\workspace\field-tests\fieldtest-20261004\cases\T2_sentinel_stream\window_drift.csv`（240 行；时间列 timestamp；分组列 -）
- **基线**：模式：prior（v1.0.0），路径：D:\codes\industrial-deep-diagnostic\workspace\field-tests\fieldtest-20261004\results\T2\baseline\watch_baseline.json
- **耗时**：15 ms（零 LLM / 零网络，全部统计由确定性脚本计算）


## 一、告警清单

| # | 级别 | 规则 | 参数/指标 | 分组 | 位置 | 观测值 | 建议 |
|---|------|------|-----------|------|------|--------|------|
| 1 | high | ROBUST_Z_OUTLIER | speed_rpm | __ALL__ | 32 | 1252 | speed_rpm 稳健 z 分数 \|3.57\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 2 | high | ROBUST_Z_OUTLIER | speed_rpm | __ALL__ | 238 | 1265 | speed_rpm 稳健 z 分数 \|22.25\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 3 | high | NELSON_R1 | speed_rpm | __ALL__ | 22 | 1252 | speed_rpm 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 4 | high | NELSON_R1 | speed_rpm | __ALL__ | 239 | 1264 | speed_rpm 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 5 | high | NELSON_R5 | speed_rpm | __ALL__ | 239 | 1264 | speed_rpm 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 6 | high | NELSON_R6 | speed_rpm | __ALL__ | 239 | 1264 | speed_rpm 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 7 | high | WINDOW_DRIFT_PROJECTION | speed_rpm | __ALL__ | - | 1263 | speed_rpm 按当前漂移速率预计 3.4 小时后触及窗口边界 [1225.0, 1275.0]，请提前安排核查 |
| 8 | warn | VARIANCE_RATIO_HIGH | speed_rpm | __ALL__ | - | 4.184 | speed_rpm 稳态段标准差为基线的 11.9 倍，离散度显著升高，建议检查波动来源 |
| 9 | warn | NELSON_R2 | speed_rpm | __ALL__ | 14 | 1251 | speed_rpm 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |


> 级别语义：`info` 记录级 / `warn` 趋势与待确认趋势 / `high` 统计异常 / `critical` 越规格。
> 本系统为纯分析系统：所有告警仅为建议核查项，不下发任何参数，动作决策由产线（AWS 侧）做出。

## 二、稳态映射（C3）

- **__ALL__**：steady=240

## 三、操作窗口投影（C2）

- **speed_rpm**：当前 1263，斜率 3.606/h，距边界 3.4438713818479867 h（级别 high）

## 四、防风暴抑制

合并触发 2 组同 key 重复；静默期 30 行；同类抑制窗口 60 分钟；迟滞 5 点

## 五、建议后续动作

- 有 `high`/`critical` 告警：按告警中的 `suggested_check` 现场核查；需要根因分析时转 `industrial-diagnostician`，需要参数窗口/工况数据分析时转 `industrial-doe-analyzer`。
- 本报告由脚本生成（`authored_by: script`）；代理只允许追加中文 `interpretation` 注记，禁止改动任何数值字段。
