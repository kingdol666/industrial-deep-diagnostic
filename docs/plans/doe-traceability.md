# DOE 分析流程优化 · 验收 Traceability Matrix

- 日期：2026-10-17
- 对应计划：`doe-analysis-flow-optimization-plan-2026-10-17.md`
- 状态：模板（Phase 0 填写；未映射的验收项不得标记 PASS）

> 规则：每条验收 ID 必须有 test case + fixture + 命令 + 证据文件。没有映射 = 未验证。
> 证据文件建议落 `workspace/acceptance/doe-<date>/`，包含命令输出摘要、JSON、截图、hash。

| 验收 ID | 条件 | 测试 case | Fixture | 命令 | 证据 | 状态 |
|---|---|---|---|---|---|---|
| OD-01 | DOE 使用 ontology-builder（profile=doe） | TBD | TBD | TBD | TBD | 未验证 |
| OD-02 | 先查 store；exact reuse ≤60s | TBD | TBD | TBD | TBD | 未验证 |
| OD-03 | design-only 先验构建 | TBD | TBD | TBD | TBD | 未验证 |
| OD-04 | Agent 理解门 | TBD | TBD | TBD | TBD | 未验证 |
| OD-05 | 本体后再分析 | TBD | TBD | TBD | TBD | 未验证 |
| OD-06 | 一致性 | TBD | TBD | TBD | TBD | 未验证 |
| OD-07 | 版本钉住 | TBD | TBD | TBD | TBD | 未验证 |
| OD-08 | 诊断回归 | TBD | TBD | TBD | TBD | 未验证 |
| OD-09 | 映射覆盖 | TBD | TBD | TBD | TBD | 未验证 |
| OD-10 | 报告引用 | TBD | TBD | TBD | TBD | 未验证 |
| OD-11 | handoff | TBD | TBD | TBD | TBD | 未验证 |
| DS-01 | 设计识别 | TBD | TBD | TBD | TBD | 未验证 |
| DS-02 | 效应恢复 | TBD | TBD | TBD | TBD | 未验证 |
| DS-03 | factor×response 覆盖 | TBD | TBD | TBD | TBD | 未验证 |
| DS-04 | 多响应 | TBD | TBD | TBD | TBD | 未验证 |
| DS-05 | 约束 | TBD | TBD | TBD | TBD | 未验证 |
| DS-06 | 单位 | TBD | TBD | TBD | TBD | 未验证 |
| DS-07 | 预测区间 | TBD | TBD | TBD | TBD | 未验证 |
| DS-08 | 联合窗口 | TBD | TBD | TBD | TBD | 未验证 |
| DS-09 | active/grid | TBD | TBD | TBD | TBD | 未验证 |
| DS-10 | association screen | TBD | TBD | TBD | TBD | 未验证 |
| DS-11 | 确认/下一轮 | TBD | TBD | TBD | TBD | 未验证 |
| DS-12 | 初始设计 | TBD | TBD | TBD | TBD | 未验证 |
| DS-13 | 向后兼容 | TBD | TBD | TBD | TBD | 未验证 |
| AR-01 | artifact manifest | TBD | TBD | TBD | TBD | 未验证 |
| AR-02 | report | TBD | TBD | TBD | TBD | 未验证 |
| AR-03 | gate | TBD | TBD | TBD | TBD | 未验证 |
| RG-01 | 既有测试 | TBD | TBD | TBD | TBD | 未验证 |
| RG-02 | 新增测试 | TBD | TBD | TBD | TBD | 未验证 |
| RG-03 | 确定性 | TBD | TBD | TBD | TBD | 未验证 |
| RG-04 | 诊断回归 | TBD | TBD | TBD | TBD | 未验证 |
| RG-05 | 性能 | TBD | TBD | TBD | TBD | 未验证 |
| RG-06 | 可复现 | TBD | TBD | TBD | TBD | 未验证 |
| XR-01 | `doe_context → analysis_context` | TBD | TBD | TBD | TBD | 未验证 |
| XR-02 | artifact 回流 | TBD | TBD | TBD | TBD | 未验证 |
| XR-03 | 优化 handoff | TBD | TBD | TBD | TBD | 未验证 |
| XR-04 | 执行 | TBD | TBD | TBD | TBD | 未验证 |

## 基线记录（Phase 0 填写）

```
IDD SHA:
AgentWorkShop SHA:
IDD working tree:
Node / npm / pnpm:
Python / uv:
Hardware:
Date:
Runner:
```

## Phase 0 必填 case 建议

- `T-DATA-01`：`00_input` 同时含 `run_table.csv`/`doe_context.json`/`exclusions/` 时，分析器选 run_table。
- `T-ONT-01`：design-only（响应空）建 ontology + brief，不跑统计。
- `T-ONT-02`：同 profile/scene/context_fp → reuse ≤60s；context 变化 → extend。
- `T-ONT-03`：Agent 未读 brief → 阻断；读后写 analysis_plan 才继续。
- `T-STAT-01`：PI 覆盖率 n≥2000；CI 不冒充 PI。
- `T-STAT-02`：约束绑定（无约束最优点在约束外）。
- `T-STAT-03`：多响应 joint_setpoint 同时可行。
- `T-STAT-04`：单位缺失/冲突阻断 actionable window。
- `T-NEXT-01`：aliased → fold-over；linear → augment star；non-randomized → confirm。
- `T-ART-01`：tasks+external 均返回 12 类 artifact；缺失/坏 schema 显式失败。
- `T-REG-01`：既有 136 断言仍绿。
