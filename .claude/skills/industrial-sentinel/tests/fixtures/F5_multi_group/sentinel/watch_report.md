# 产线哨兵巡检报告（watch 模式）

- **生成时间**：2026-10-05T07:49:41.292536+00:00
- **总体状态**：**alert** · 告警数 **5**
- **数据**：`D:\codes\industrial-deep-diagnostic\.claude\skills\industrial-sentinel\tests\fixtures\F5_multi_group\watch.csv`（700 行；时间列 -；分组列 line）
- **基线**：模式：prior（v1.0.0），路径：D:\codes\industrial-deep-diagnostic\.claude\skills\industrial-sentinel\tests\fixtures\F5_multi_group\watch_baseline.json
- **耗时**：25 ms（零 LLM / 零网络，全部统计由确定性脚本计算）


## 一、告警清单

| # | 级别 | 规则 | 参数/指标 | 分组 | 位置 | 观测值 | 建议 |
|---|------|------|-----------|------|------|--------|------|
| 1 | high | ROBUST_Z_OUTLIER | temp | A | 150 | 50.5 | temp 稳健 z 分数 \|11.23\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 2 | high | ROBUST_Z_OUTLIER | temp | B | 150 | 50.5 | temp 稳健 z 分数 \|11.34\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 3 | high | NELSON_R1 | temp | A | 150 | 50.5 | temp 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 4 | high | NELSON_R1 | temp | B | 150 | 50.5 | temp 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 5 | warn | UNSEEN_GROUP | - | C | - | - | 分组 C 未在基线登记，请扩充基线（build_baseline.py）或核对分组列取值 |


> 级别语义：`info` 记录级 / `warn` 趋势与待确认趋势 / `high` 统计异常 / `critical` 越规格。
> 本系统为纯分析系统：所有告警仅为建议核查项，不下发任何参数，动作决策由产线（AWS 侧）做出。

## 二、稳态映射（C3）

- **A**：steady=300
- **B**：steady=300
- **C**：steady=100

## 三、操作窗口投影（C2）

- **C2 漂移投影未启用**：基线中无 operating_windows —— 构建基线时传入 --doe-run-dir 注册 DOE 先验操作窗即可启用（C2 drift projection disabled: no operating_windows in baseline (build with --doe-run-dir to enable)）

## 四、防风暴抑制

合并触发 0 组同 key 重复；静默期 30 行；同类抑制窗口 60 分钟；迟滞 5 点

## 五、告警事件摘要（incidents）

| 事件 | 参数 | 类别 | 峰值级别 | 跨度(行) | 告警数 | 规则 |
|------|------|------|----------|----------|--------|------|
| EVT-20261005074941-002 | temp | multivariate | high | 0 | 1 | ROBUST_Z_OUTLIER |
| EVT-20261005074941-003 | temp | multivariate | high | 0 | 1 | ROBUST_Z_OUTLIER |
| EVT-20261005074941-004 | temp | spc | high | 0 | 1 | NELSON_R1 |
| EVT-20261005074941-005 | temp | spc | high | 0 | 1 | NELSON_R1 |
| EVT-20261005074941-001 | - | baseline | warn | 0 | 1 | UNSEEN_GROUP |

## 六、建议后续动作

- 有 `high`/`critical` 告警：按告警中的 `suggested_check` 现场核查；需要根因分析时转 `industrial-diagnostician`，需要参数窗口/工况数据分析时转 `industrial-doe-analyzer`。
- 事件摘要按峰值级别与告警数排序；完整逐段告警在 alert.json 的 `alerts` 数组（契约不变），事件视图在 `events` 数组。
- 本报告由脚本生成（`authored_by: script`）；代理只允许追加中文 `interpretation` 注记，禁止改动任何数值字段。
