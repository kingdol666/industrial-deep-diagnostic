# 文档总索引

本文件汇总 `industrial-deep-diagnostic` skill 的所有文档，按用途分类，便于快速定位。

---

## 入门必读

| 文档 | 用途 |
|------|------|
| [README.md](./README.md) | 项目总览、特性、交付物 |
| [QUICKSTART.md](./QUICKSTART.md) | 5 分钟上手、触发命令、输出解读 |
| [GLOSSARY.md](./GLOSSARY.md) | 术语表 |

---

## 执行与排错

| 文档 | 用途 |
|------|------|
| [SKILL.md](./SKILL.md) | 主执行协议、Agent 启动模板、红灯动作 |
| [pipeline-execution.md](./pipeline-execution.md) | 详细命令、校验脚本、修复循环 |
| [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) | 常见故障排查、恢复动作、调试技巧 |

---

## 架构与设计

| 文档 | 用途 |
|------|------|
| [ARCHITECTURE.md](./ARCHITECTURE.md) | 系统分层、数据流、治理机制、扩展方式 |
| [AGENTS.md](./AGENTS.md) | 子 Agent 人格、职责、输入输出速查 |
| [resources/engineering_delivery_contract.md](./resources/engineering_delivery_contract.md) | 工程交付标准 |

---

## 开发维护

| 文档 | 用途 |
|------|------|
| [CLAUDE.md](./CLAUDE.md) | 开发者注意事项、关键陷阱 |
| [CONTRIBUTING.md](./CONTRIBUTING.md) | 修改规范、双版本同步、提交规范 |
| [SYNC.md](./SYNC.md) | `.claude/` 与 `.agents/` 双版本同步说明 |
| [CHANGELOG.md](./CHANGELOG.md) | 版本变更日志 |
| [MIGRATION.md](./MIGRATION.md) | 版本迁移指南 |
| [EVAL.md](./EVAL.md) | Eval 运行与扩展 |

---

## 安全与性能

| 文档 | 用途 |
|------|------|
| [SECURITY.md](./SECURITY.md) | 数据安全、隐私、审计 |
| [PERFORMANCE.md](./PERFORMANCE.md) | 运行时间、Token 成本、优化建议 |

---

## 子 Agent 协议

| Agent | 文档 |
|-------|------|
| context-builder | [agents/context-builder.md](./agents/context-builder.md) |
| data-processor | [agents/data-processor.md](./agents/data-processor.md) |
| vlm-visual-analyzer | [agents/vlm-visual-analyzer.md](./agents/vlm-visual-analyzer.md) |
| diagnostician | [agents/diagnostician.md](./agents/diagnostician.md) |
| judge | [agents/judge.md](./agents/judge.md) |
| report-reviewer | [agents/report-reviewer.md](./agents/report-reviewer.md) |
| reporter | [agents/reporter.md](./agents/reporter.md) |
| html-visualizer | [agents/html-visualizer.md](./agents/html-visualizer.md) |
| html-reviewer | [agents/html-reviewer.md](./agents/html-reviewer.md) |

---

## 方法论资源

| 文档 | 用途 |
|------|------|
| [resources/evidence_rules.md](./resources/evidence_rules.md) | 证据等级、反推测规则 |
| [resources/diagnosis_method.md](./resources/diagnosis_method.md) | 通用诊断方法论 Stage 1-6 |
| [resources/physics_inference_framework.md](./resources/physics_inference_framework.md) | 一级原理推导 L1-L5 |
| [resources/process_knowledge_base.md](./resources/process_knowledge_base.md) | 跨行业物理原理 |
| [resources/scenario_patterns.md](./resources/scenario_patterns.md) | 场景特定分析模式 |
| [resources/visual_analysis_framework.md](./resources/visual_analysis_framework.md) | VLM 图像分析框架 |
| [resources/data_ontology_mapping_framework.md](./resources/data_ontology_mapping_framework.md) | 数据↔本体双向映射 |
| [resources/rag_deep_understanding_protocol.md](./resources/rag_deep_understanding_protocol.md) | RAG 深度理解协议 |
| [resources/rag_integration_guide.md](./resources/rag_integration_guide.md) | RAG 集成指南 |
| [resources/diagnostician_dual_drive_reference.md](./resources/diagnostician_dual_drive_reference.md) | 双驱动分析参考 |
| [resources/pipeline_coherence_and_synergy.md](./resources/pipeline_coherence_and_synergy.md) | 步骤协同规则 |
| [resources/script_and_toolkit_reference.md](./resources/script_and_toolkit_reference.md) | 脚本工具目录 |

---

## 检查清单

| 文档 | 用途 |
|------|------|
| [tests/checklists/ontology_checklist.md](./tests/checklists/ontology_checklist.md) | 本体质量检查 |
| [tests/checklists/diagnosis_checklist.md](./tests/checklists/diagnosis_checklist.md) | 诊断质量检查 |
| [tests/checklists/judge_checklist.md](./tests/checklists/judge_checklist.md) | Judge 审查检查 |
| [tests/checklists/report_checklist.md](./tests/checklists/report_checklist.md) | 报告质量检查 |

---

## 快速问题对应表

| 我想知道... | 读这个 |
|:------------|:-------|
| 这是什么 skill | README.md |
| 怎么跑起来 | QUICKSTART.md |
| 某一步怎么执行 | pipeline-execution.md |
| 为什么失败了 | TROUBLESHOOTING.md |
| 各个 Agent 是干什么的 | AGENTS.md |
| 系统怎么设计的 | ARCHITECTURE.md |
| 想修改/贡献 | CONTRIBUTING.md + SYNC.md |
| 版本变了什么 | CHANGELOG.md |
| 老版本怎么迁移 | MIGRATION.md |
| 术语不懂 | GLOSSARY.md |
| 数据安全 | SECURITY.md |
| 运行多慢/多贵 | PERFORMANCE.md |
| 怎么加测试 | EVAL.md |
