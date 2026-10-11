# 产线哨兵巡检报告（watch 模式）

- **生成时间**：2026-10-10T02:52:03.101981+00:00
- **总体状态**：**alert** · 告警数 **2**
- **数据**：`D:\codes\industrial-deep-diagnostic\.claude\skills\industrial-sentinel\tests\fixtures\F4_cold_start\watch.csv`（240 行；时间列 -；分组列 -）
- **基线**：模式：self（self:v1.0.0）
- **耗时**：26 ms（零 LLM / 零网络，全部统计由确定性脚本计算）

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

- **C2 漂移投影未启用**：基线中无 operating_windows —— 构建基线时传入 --doe-run-dir 注册 DOE 先验操作窗即可启用（C2 drift projection disabled: no operating_windows in baseline (build with --doe-run-dir to enable)）

## 四、防风暴抑制

合并触发 0 组同 key 重复；静默期 30 行；同类抑制窗口 60 分钟；迟滞 5 点

## 五、告警事件摘要（incidents）

| 事件 | 参数 | 类别 | 峰值级别 | 跨度(行) | 告警数 | 规则 |
|------|------|------|----------|----------|--------|------|
| EVT-20261010025203-002 | temp | spc | high | 0 | 1 | NELSON_R1 |
| EVT-20261010025203-001 | - | baseline | warn | 0 | 1 | SELF_BASELINE |

## 六、建议后续动作

- 有 `high`/`critical` 告警：按告警中的 `suggested_check` 现场核查；需要根因分析时转 `industrial-diagnostician`，需要参数窗口/工况数据分析时转 `industrial-doe-analyzer`。
- 事件摘要按峰值级别与告警数排序；完整逐段告警在 alert.json 的 `alerts` 数组（契约不变），事件视图在 `events` 数组。
- 本报告由脚本生成（`authored_by: script`）；代理只允许追加中文 `interpretation` 注记，禁止改动任何数值字段。
