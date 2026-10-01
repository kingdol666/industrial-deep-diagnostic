# 数据分析报告 — {{RUN_ID}}

> 由 industrial-doe-analyzer 生成 · 分析模式 {{MODE}} · 设计类型 {{DESIGN_TYPE}} ·
> 证据等级 {{GRADE}} · 下游合同 recommendations.json v{{CONTRACT_VERSION}}
>
> 本模板供 agent 撰写 report.md（中文）；人类可读的交互版 report.html 由
> `analyze.py report` 脚本确定性渲染，两者数字同源（9 个工件 JSON），禁止手改 HTML。

---

## 一、10 秒结论卡

| 项 | 值 |
|---|---|
| 关键因子（按效应强度） | {{TOP_FACTORS}} |
| 推荐操作窗口数 | {{N_WINDOWS}}（其中 {{N_CONFIRM}} 条需先做确认试验） |
| 预期收益（最优窗口） | {{BEST_EXPECTED_EFFECT}} |
| 证据等级 | {{GRADE}}（{{GRADE_REASON}}） |
| 最重要的限制 | {{TOP_LIMITATION}} |

**一句话结论**：{{ONE_SENTENCE}}

---

## 二、1 分钟证据层

### 2.1 效应/相关排序
{{EVIDENCE_TABLE}}

### 2.2 关键图
{{FIGURE_GALLERY}}

### 2.3 稳定性/能力（观察档适用）
{{STABILITY_SUMMARY}}

---

## 三、深读审计层

### 3.1 模型与检验细节
{{AUDIT_DETAILS}}

### 3.2 披露与限制（全部保留，不得删除）
{{LIMITATIONS}}

### 3.3 确认试验计划
{{CONFIRMATIONS}}

### 3.4 下游使用规则
{{USAGE_RULES}}

- 适用域：n={{N_ROWS}}，时间跨度 {{TIME_SPAN}}，工况限定 {{REGIME}}
- 失效条件：{{INVALIDATION}}

---

## 附：工件索引
{{ARTIFACT_INDEX}}
