# Plans — 开发计划索引

> 本目录存放可执行的开发计划。计划状态以文件头 `Status` 为准；未标记 `approved`/`executed` 的计划不得直接进入实现。

| 计划 | 状态 | 范围 | 入口 |
|---|---|---|---|
| DOE 数据分析流程优化（本体优先） | `pending approval` | IDD DOE 分析流程 + AgentWorkShop 跨仓库集成 | [doe-analysis-flow-optimization-plan-2026-10-17.md](doe-analysis-flow-optimization-plan-2026-10-17.md) |
| 验收 Traceability Matrix（模板） | `pending approval` | 37 条验收 → test/fixture/命令/证据映射 | [doe-traceability.md](doe-traceability.md) |
| 基线快照（Phase 0） | 只读 | 双仓库 SHA/工具链/测试基线/冻结清单 | [doe-baseline-2026-10-17.md](doe-baseline-2026-10-17.md) |

## 执行约定

1. 开工前记录双仓库 SHA、工作树状态、Node/Python/uv 版本与硬件规格。
2. 按计划 Phase 0 → Phase 5 顺序执行；阶段退出标准未满足不得进入下一阶段。
3. 每条验收 ID 必须映射到 test case / fixture / 命令 / 证据文件（`doe-traceability.md`）。
4. 所有统计数字由确定性脚本计算；Agent 只解释，禁止手改 JSON/HTML。
5. 跨仓库（AgentWorkShop）任务单独跟踪，不阻塞 IDD-only MVP。
