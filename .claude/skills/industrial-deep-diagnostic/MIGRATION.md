# 版本迁移指南

## 当前版本

见 [CHANGELOG.md](./CHANGELOG.md)。

## v6.x 主要变更速查

| 版本 | 关键变更 | 迁移注意 |
|:----:|:---------|:---------|
| v6.7 | R2 leave-one-out leverage、R1 batch identity integrity、数据清洗来源一致性 | 检查自定义脚本是否修改 data_source |
| v6.6 | batch/lot id 唯一性验证、duplicate_batch_report.json | 有 batch 列的数据需重新分析 |
| v6.5 | 生产工况检测、production_regime_filter.json、per-product 强制分析 | 多产品数据诊断结论可能变化 |
| v6.4 | 时滞补偿、time_lag_analysis.json、physics_discrepancy_alerts | 因果结论需引用滞后分析 |
| v6.3 | HTML 自动构建、diagnostic-html-visualizer skill | 默认交付 HTML，需前置 opt-out |
| v6.2 | interaction_mode、新 schemas | 运行配置需符合新 schema |
| v6.1 | 预报告审计、optimizer_preflight.md | Step 5 拆分为 5a/5b |
| v6.0 | 数据鉴别力评估、INDISTINGUISHABLE、confidence ceiling ≤65 | diagnostician 输出结构扩展 |

## 从 v5.x 迁移到 v6.x

### 1. 运行命令

v5 的 `/diagnose` 命令已合并为：

```
/industrial-deep-diagnostic
```

### 2. 产物变化

新增产物：

- `diagnostic-report.html`
- `05_review/html_review.json`
- `02_processed/time_lag_analysis.json`
- `02_processed/production_regime_filter.json`
- `05_review/optimizer_preflight.md`

### 3. Schema 变化

- `diagnosis_schema.json` 增加 `data_discriminability` 字段
- `data_analysis_conclusion_schema.json` 增加 `cleaning_integrity` 字段
- 新增 `html_review_schema.json`

### 4. 行为变化

- HTML 可视化现在是默认交付物
- Judge 评分需 ≥90 且无 blocking issues 才能进入 reporter
- report-reviewer 在 Step 5b 预审计阶段与 Judge 并行

## 从 v6.x 早期版本迁移

### v6.5 → v6.6

- data-processor 现在验证 batch/lot id 唯一性
- 重复 batch 记录必须合并或标记
- 自定义脚本需确保不破坏 batch 完整性

### v6.6 → v6.7

- data-processor 必须记录 `cleaning_integrity.data_source`
- 所有下游分析需从该单一权威源读取
- HTML 页面必须展示"数据治理"披露卡

## 向后兼容策略

本 skill 尽量保持向后兼容：

- 新增 schema 字段通常为 optional
- 旧产物缺失时 Agent 按 fallback 规则处理
- 运行命令保持 `/industrial-deep-diagnostic` 主入口不变

## 弃用通知

| 版本 | 弃用项 | 替代方案 |
|:----:|:-------|:---------|
| v6.3 | 主 Agent 在主上下文生成报告页面 | 使用 html-visualizer 子 Agent |
| v6.5 | 不区分稳态/非稳态的统计分析 | 使用 production_regime_filter.json |
| v6.6 | 忽略 batch id 唯一性的分析 | 使用 duplicate_batch_report.json |
| v6.7 | 不记录 data_source 的分析 | 使用 cleaning_integrity.data_source |
