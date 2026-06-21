# Industrial Deep Diagnostic

> 多智能体工业深度诊断系统：将传感器/工艺数据转化为可审计、可执行的根因分析。

---

## 一句话说明

**Industrial Deep Diagnostic** 是一套面向流程制造与工业设备诊断的端到端多智能体系统。它通过 "本体构建 → 统计验证 → 竞争假说 → 物理验证 → 质量审计 → 可视化交付" 的九步管线，把 CSV/XLSX/Parquet 数据转化为 `report.md` + `diagnostic-report.html` + `optimizer.md` 的完整交付物。

---

## 适用场景

| 适合 | 不适合 |
|------|--------|
| 流程制造产线异常（化工、材料、薄膜、冶金） | 金融、生物、社会科学数据 |
| 质量缺陷根因分析 | 纯探索性数据分析 |
| 设备故障/传感器异常 | 实时在线诊断（<1 分钟响应） |
| 工艺参数优化建议 | 数据量极小（<100 行） |

---

## 快速开始

见 [QUICKSTART.md](./QUICKSTART.md)。

---

## 核心特性

1. **本体优先 (ontology_first)**：先理解参数物理含义，再做统计分析。
2. **统计防陷阱**：Simpson's Paradox 检测、趋势混淆去趋势、时滞补偿、生产工况过滤。
3. **物理锚定**：每个因果结论必须追溯到一级原理方程（Arrhenius、热膨胀、Darcy、Bernoulli 等）。
4. **竞争假说协议**：`DETERMINED` / `COMPETING_SET` / `NEEDS_DATA` 三态，禁止强行下结论。
5. **多 Agent 审计**：Judge 质量门 + report-reviewer 物理真相审计 + html-reviewer 可视化审校。
6. **执行证明**：仅文件存在不算执行，必须通过 `.pipeline_events.jsonl` 校验。
7. **自动 HTML 可视化**：Step 7 `ENDORSED` 后自动构建 ECharts + Three.js 讲解页。

---

## 文档索引

| 文档 | 用途 | 读者 |
|------|------|------|
| [SKILL.md](./SKILL.md) | 主执行协议 | 主 Agent、所有使用者 |
| [pipeline-execution.md](./pipeline-execution.md) | 详细执行参考、命令、校验 | 主 Agent、调试修复 |
| [CLAUDE.md](./CLAUDE.md) | 开发者注意事项 | Skill 开发者 |
| [QUICKSTART.md](./QUICKSTART.md) | 5 分钟上手 | 新用户 |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | 架构设计说明书 | 架构师、开发者 |
| [AGENTS.md](./AGENTS.md) | 子 Agent 人格与职责速查 | 所有使用者 |
| [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) | 故障排查手册 | 运维、调试者 |
| [CONTRIBUTING.md](./CONTRIBUTING.md) | 修改与贡献规范 | 开发者 |
| [CHANGELOG.md](./CHANGELOG.md) | 版本变更日志 | 所有使用者 |
| [GLOSSARY.md](./GLOSSARY.md) | 术语表 | 新用户 |
| [SECURITY.md](./SECURITY.md) | 数据安全与隐私 | 运维、审计 |
| [PERFORMANCE.md](./PERFORMANCE.md) | 性能与成本指南 | 部署者 |
| [EVAL.md](./EVAL.md) | Eval 运行与扩展说明 | 开发者、测试 |
| [MIGRATION.md](./MIGRATION.md) | 版本迁移指南 | 升级用户 |
| [resources/engineering_delivery_contract.md](./resources/engineering_delivery_contract.md) | 工程交付标准 | 所有使用者 |

### Agent 协议

- [agents/context-builder.md](./agents/context-builder.md)
- [agents/data-processor.md](./agents/data-processor.md)
- [agents/vlm-visual-analyzer.md](./agents/vlm-visual-analyzer.md)
- [agents/diagnostician.md](./agents/diagnostician.md)
- [agents/judge.md](./agents/judge.md)
- [agents/report-reviewer.md](./agents/report-reviewer.md)
- [agents/reporter.md](./agents/reporter.md)
- [agents/html-visualizer.md](./agents/html-visualizer.md)
- [agents/html-reviewer.md](./agents/html-reviewer.md)

### 方法论资源

- [resources/evidence_rules.md](./resources/evidence_rules.md)
- [resources/diagnosis_method.md](./resources/diagnosis_method.md)
- [resources/physics_inference_framework.md](./resources/physics_inference_framework.md)
- [resources/diagnostician_dual_drive_reference.md](./resources/diagnostician_dual_drive_reference.md)
- [resources/process_knowledge_base.md](./resources/process_knowledge_base.md)
- [resources/scenario_patterns.md](./resources/scenario_patterns.md)
- [resources/visual_analysis_framework.md](./resources/visual_analysis_framework.md)
- [resources/data_ontology_mapping_framework.md](./resources/data_ontology_mapping_framework.md)
- [resources/rag_deep_understanding_protocol.md](./resources/rag_deep_understanding_protocol.md)
- [resources/rag_integration_guide.md](./resources/rag_integration_guide.md)
- [resources/pipeline_coherence_and_synergy.md](./resources/pipeline_coherence_and_synergy.md)
- [resources/script_and_toolkit_reference.md](./resources/script_and_toolkit_reference.md)
- [resources/engineering_delivery_contract.md](./resources/engineering_delivery_contract.md)

---

## 执行命令

```bash
# 完整管线（Steps 0-9）
/industrial-deep-diagnostic

# 跳过数据导入，从 Step 2 开始
/industrial-deep-diagnostic analyze

# 重新评审已有结果
/industrial-deep-diagnostic review

# 重新生成报告
/industrial-deep-diagnostic report

# 仅运行报告审计
/industrial-deep-diagnostic audit
```

---

## 交付物

一次完整运行交付：

```
workspace/diagnostic-runs/<timestamp>_<scene>/
├── 00_input/              # 输入数据 + 上下文
├── 01_ontology/           # 本体模型
├── 02_processed/          # 统计分析与数据结论
├── 03_figures/            # 可视化图表 + VLM 分析
├── 04_diagnostics/        # 诊断、证据、置信度、推理链
├── 05_review/             # Judge + Reviewer + HTML 审校
├── report.md              # 中文诊断报告
├── optimizer.md           # 优化建议与审计意见
├── diagnostic-report.html # HTML 可视化讲解页
└── run_summary.json       # 运行摘要
```

---

## 语言约定

- 默认输出语言：**中文**
- 报告、诊断结论、审计文档使用中文
- JSON enum 字段保持英文

---

## 版本

当前版本见 [CHANGELOG.md](./CHANGELOG.md)。

---

## 许可证与贡献

见 [CONTRIBUTING.md](./CONTRIBUTING.md)。
