# 变更日志

所有 notable 变更都会记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

---

## [Unreleased]

### Added
- 新增完整文档体系：`README.md`、`QUICKSTART.md`、`TROUBLESHOOTING.md`、`CONTRIBUTING.md`、`CHANGELOG.md`、`ARCHITECTURE.md`、`AGENTS.md`、`GLOSSARY.md`、`SECURITY.md`、`PERFORMANCE.md`、`EVAL.md`、`MIGRATION.md`
- 文档索引与快速上手指南

### Changed
- 优化 SKILL.md 中 HTML 自动构建章节的表述，明确禁止 Step 7→8 处临时询问用户

---

## [v6.7] — 2026-06-20

### Added
- 编码 Failure A：leave-one-out leverage contract（R2）
- 编码 Failure B：batch identity integrity（R1）
- 数据清洗来源一致性（cleaned / raw_fallback）强制记录

### Changed
- data-processor 增加 string-type-gotcha 防御深度
- 强化反幻觉数据治理要求

### Fixed
- HTML opt-out 场景下 finalize 阻塞问题

---

## [v6.6] — 2026-06-19

### Added
- batch/lot id 唯一性验证
- duplicate_batch_report.json 生成要求
- 同 batch 分裂记录必须合并或标记

### Changed
- data-processor Phase 2.2.5 清洗完整性校验增强

---

## [v6.5] — 2026-06-18

### Added
- 生产工况检测：startup / shutdown / steady-state 三算法融合
- per-product 强制分析：识别 anomaly rate 最高的产品
- production_regime_filter.json

### Changed
- 统计分析前必须先过滤到稳态数据
- data-processor 交付契约扩展

---

## [v6.4] — 2026-06-17

### Added
- 时滞补偿分析：time_lag_compensator.mjs
- time_lag_analysis.json 输出
- physics_discrepancy_alerts 检测

### Changed
- diagnostician 必须在形成因果假设前读取 time_lag_analysis.json
- judge 增加 lag-compensated correlation 审计项

---

## [v6.3] — 2026-06-16

### Added
- HTML 可视化自动构建：Step 8 + Step 8.5
- diagnostic-html-visualizer skill 独立协议
- html-reviewer 可视化审校 Agent

### Changed
- 默认交付物必须同时包含 report.md 和 diagnostic-report.html
- HTML 构建成为强制收尾步骤，除非用户前置 opt-out

---

## [v6.2] — 2026-06-15

### Added
- interaction_mode：auto / interactive / minimal
- 新 schemas：run_config、run_summary、html_review 等
- 清理旧版冗余 schema

### Changed
- clarification gate 与 interaction_mode 深度集成

---

## [v6.1] — 2026-06-14

### Added
- report-reviewer 预报告审计模式（PRE_REPORT_AUDIT=true）
- optimizer_preflight.md
- judge 与 pre-audit 并行执行机制

### Changed
- Step 5 拆分为 Step 5a（judge）和 Step 5b（pre-audit）

---

## [v6.0] — 2026-06-13

### Added
- 数据鉴别力评估（Data Discriminability Assessment）
- INDISTINGUISHABLE 竞争假设检测
- confidence ceiling ≤65 规则

### Changed
- diagnostician 必须显式检查竞争假设的可区分性

---

## [v5.x] 及更早

- 早期版本实现了基础多 Agent 诊断管线
- 包含 context-builder、data-processor、diagnostician、judge、reporter、report-reviewer
- 证据等级 L1-L7、反推测四条件、竞争集协议等核心机制

---

## 版本号规则

本 skill 使用语义化版本：

- **MAJOR**：架构级变更，破坏向后兼容
- **MINOR**：新增显著功能或方法论增强
- **PATCH**：修复、文档改进、小优化

当前主要版本为 v6.x，每次 minor 升级通常对应一个方法论增强（如 v6.4 时滞补偿、v6.5 工况过滤、v6.6 batch 完整性、v6.7 leave-one-out leverage）。
