# Plans — 开发计划索引

> 本目录存放可执行的开发计划。计划状态以文件头 `Status` 为准；未标记 `approved`/`executed` 的计划不得直接进入实现。

| 计划 | 状态 | 范围 | 入口 |
|---|---|---|---|
| DOE 数据分析流程优化（本体优先） | `executed`（IDD Phase 0–5；Phase 6 平台侧未执行） | IDD DOE 分析流程 + AgentWorkShop 跨仓库集成 | [doe-analysis-flow-optimization-plan-2026-10-17.md](doe-analysis-flow-optimization-plan-2026-10-17.md) |
| 验收 Traceability Matrix | `filled`（37 条已回填：PASS/部分/延期） | 37 条验收 → test/fixture/命令/证据映射 | [doe-traceability.md](doe-traceability.md) |
| 契约冻结（Phase 0） | `frozen` | run_table / doe_context / analysis_context / artifact manifest + round-trip | [contracts/README.md](contracts/README.md) |
| 基线快照（Phase 0） | 冻结 | 双仓库 SHA/工具链/测试基线/隔离工作树 | [doe-baseline-2026-10-17.md](doe-baseline-2026-10-17.md) |
| 验收执行摘要 | 证据 | 套件结果 / MC / 性能 / 端到端实测 / 延期项 | [evidence/doe-2026-10-17/summary.md](evidence/doe-2026-10-17/summary.md) |
| **DOE 端到端演示**（BOPET 真实场景） | 可重跑 | 模拟真实试验数据 + 植入真值 + 60 条断言 + 人读报告 | [demo/doe-bopet/README.md](demo/doe-bopet/README.md) |
| **平台抓数全场景实测**（异常/波动/DOE/异构/本体/检索） | 可重跑 | AgentWorkShop 抓数格式 + 三类任务 + E-1H + 100 条断言 | [doe-field-trial-2026-10-17.md](doe-field-trial-2026-10-17.md) · [demo/aws-capture-doe/README.md](demo/aws-capture-doe/README.md) |
| **DOE 泛化语料**（12 行业 × 12 设计/数据形态） | 可重跑 | 全因子/部分因子/CCD/BBD/OA/LHS/观测/设计-only/多响应/约束/单位 | [demo/doe-generality/GENERALITY.md](demo/doe-generality/GENERALITY.md) |
| **AgentWorkShop 集成审计 + E2E** | 实测 | IDD API 全量盘点 + 插件设计审计 + 真实 OMP/插件探针 + 投产判定 | [agentworkshop-integration-audit-2026-10-17.md](agentworkshop-integration-audit-2026-10-17.md) |

## 执行约定

1. 开工前记录双仓库 SHA、工作树状态、Node/Python/uv 版本与硬件规格。
2. 按计划 Phase 0 → Phase 5 顺序执行；阶段退出标准未满足不得进入下一阶段。
3. 每条验收 ID 必须映射到 test case / fixture / 命令 / 证据文件（`doe-traceability.md`）。
4. 所有统计数字由确定性脚本计算；Agent 只解释，禁止手改 JSON/HTML。
5. 跨仓库（AgentWorkShop）任务单独跟踪，不阻塞 IDD-only MVP。

## 执行状态（2026-10-17）

- 执行工作树 `D:/codes/myskills/idd-doe-impl`，分支 `feat/doe-ontology-first`（自 `1ff3d6c`）；主工作树 421 条并行变更未被触碰。
- 终态：`run_tests.py 199/199`、`phase1 68/68`、`phase2 130/130`、`phase3 82/82`、`gate-v11 44/44`、`roundtrip 28/28`、`backend 150/150`。
- 平台抓数全场景实测：`aws_capture 46/46`、`stability 117/117`、`sentinel 107/107`、`run_demo 100/100`、`routing 20/20`（合计 1,059 条断言全绿）；报告见 `doe-field-trial-2026-10-17.md`。
- 泛化语料：12/12 case、132/132 断言；API/插件审计与真实 E2E 见 `agentworkshop-integration-audit-2026-10-17.md`。
- 延期项与已知口径差异见 `evidence/doe-2026-10-17/summary.md` §6；平台侧 P0/P1 缺口见 `doe-field-trial-2026-10-17.md` §6 与集成审计报告 §3/§7。
