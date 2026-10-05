# 产线哨兵巡检报告（watch 模式）

- **生成时间**：2026-10-04T06:36:22.896462+00:00
- **总体状态**：**alert** · 告警数 **3**
- **数据**：`D:\codes\industrial-deep-diagnostic\workspace\field-tests\fieldtest-20261004\cases\T2_sentinel_stream\window_changepoint.csv`（240 行；时间列 timestamp；分组列 -）
- **基线**：模式：prior（v1.0.0），路径：D:\codes\industrial-deep-diagnostic\workspace\field-tests\fieldtest-20261004\results\T2\baseline\watch_baseline.json
- **耗时**：19 ms（零 LLM / 零网络，全部统计由确定性脚本计算）


## 一、告警清单

| # | 级别 | 规则 | 参数/指标 | 分组 | 位置 | 观测值 | 建议 |
|---|------|------|-----------|------|------|--------|------|
| 1 | high | ROBUST_Z_OUTLIER | temp_c | __ALL__ | 152 | 88.28 | temp_c 稳健 z 分数 \|37.44\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 2 | warn | REGIME_CHANGE_NEW | - | __ALL__ | 121 | - | __ALL__ 组在第 121 行附近检出新的工况变化点，其后 30 行已静默并重估中心线 |
| 3 | warn | VARIANCE_RATIO_HIGH | temp_c | __ALL__ | - | 1.603 | temp_c 稳态段标准差为基线的 34.8 倍，离散度显著升高，建议检查波动来源 |


> 级别语义：`info` 记录级 / `warn` 趋势与待确认趋势 / `high` 统计异常 / `critical` 越规格。
> 本系统为纯分析系统：所有告警仅为建议核查项，不下发任何参数，动作决策由产线（AWS 侧）做出。

## 二、稳态映射（C3）

- **__ALL__**：steady=229、transition=11

## 三、操作窗口投影（C2）

- **speed_rpm**：当前 1250，斜率 -0.004782/h，距边界 5228.220624361615 h（级别 info）

## 四、防风暴抑制

合并触发 0 组同 key 重复；静默期 30 行；同类抑制窗口 60 分钟；迟滞 5 点

## 五、建议后续动作

- 有 `high`/`critical` 告警：按告警中的 `suggested_check` 现场核查；需要根因分析时转 `industrial-diagnostician`，需要参数窗口/工况数据分析时转 `industrial-doe-analyzer`。
- 本报告由脚本生成（`authored_by: script`）；代理只允许追加中文 `interpretation` 注记，禁止改动任何数值字段。
