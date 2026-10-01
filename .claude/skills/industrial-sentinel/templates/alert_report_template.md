# 产线哨兵巡检报告（{{MODE}} 模式）

- **生成时间**：{{GENERATED_AT}}
- **总体状态**：**{{STATUS}}** · 告警数 **{{ALERT_COUNT}}**
- **数据**：`{{DATA_PATH}}`（{{N_ROWS}} 行；时间列 {{TIME_COL}}；分组列 {{GROUP_COL}}）
- **基线**：{{BASELINE_LINE}}
- **耗时**：{{DURATION_MS}} ms（零 LLM / 零网络，全部统计由确定性脚本计算）

{{COLD_START_SECTION}}
## 一、告警清单

{{ALERTS_SECTION}}

> 级别语义：`info` 记录级 / `warn` 趋势与待确认趋势 / `high` 统计异常 / `critical` 越规格。
> 本系统为纯分析系统：所有告警仅为建议核查项，不下发任何参数，动作决策由产线（AWS 侧）做出。

## 二、稳态映射（C3）

{{REGIME_SECTION}}

## 三、操作窗口投影（C2）

{{PROJECTION_SECTION}}

## 四、防风暴抑制

{{SUPPRESSION_SECTION}}

## 五、建议后续动作

- 有 `high`/`critical` 告警：按告警中的 `suggested_check` 现场核查；需要根因分析时转 `industrial-diagnostician`，需要参数窗口/工况数据分析时转 `industrial-doe-analyzer`。
- 本报告由脚本生成（`authored_by: script`）；代理只允许追加中文 `interpretation` 注记，禁止改动任何数值字段。
