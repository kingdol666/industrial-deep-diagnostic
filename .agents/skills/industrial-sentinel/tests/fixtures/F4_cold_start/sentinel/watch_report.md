# 产线哨兵巡检报告（watch 模式）

- **生成时间**：2026-10-01T13:56:38.207210+00:00
- **总体状态**：**alert** · 告警数 **2**
- **数据**：`D:\codes\myskills\industrial-deep-diagnostic\.claude\skills\industrial-sentinel\tests\fixtures\F4_cold_start\watch.csv`（240 行；时间列 -；分组列 -）
- **基线**：模式：self（self:v1.0.0）
- **耗时**：16 ms（零 LLM / 零网络，全部统计由确定性脚本计算）

> **冷启动提示**：本次运行为冷启动 self 基线（窗口前段稳态行自建，已跳过马氏距离），TTL 48 小时，请尽快用历史数据运行 build_baseline.py 固化正式基线

## 一、告警清单

| # | 级别 | 规则 | 参数/指标 | 分组 | 位置 | 观测值 | 建议 |
|---|------|------|-----------|------|------|--------|------|
| 1 | high | NELSON_R1 | temp | __ALL__ | 200 | 50.5 | temp 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 2 | warn | SELF_BASELINE | - | - | - | - | self 基线仅覆盖本窗口，统计功效有限；48 小时内请用历史数据运行 build_baseline.py 固化正式基线 |


> 级别语义：`info` 记录级 / `warn` 趋势与待确认趋势 / `high` 统计异常 / `critical` 越规格。
> 本系统为纯分析系统：所有告警仅为建议核查项，不下发任何参数，动作决策由产线（AWS 侧）做出。

## 二、稳态映射（C3）

- **__ALL__**：steady=240

## 三、操作窗口投影（C2）

- 无操作窗口投影

## 四、防风暴抑制

合并触发 0 组同 key 重复；静默期 30 行；同类抑制窗口 60 分钟；迟滞 5 点

## 五、建议后续动作

- 有 `high`/`critical` 告警：按告警中的 `suggested_check` 现场核查；需要根因分析时转 `industrial-diagnostician`，需要参数窗口/工况数据分析时转 `industrial-doe-analyzer`。
- 本报告由脚本生成（`authored_by: script`）；代理只允许追加中文 `interpretation` 注记，禁止改动任何数值字段。
