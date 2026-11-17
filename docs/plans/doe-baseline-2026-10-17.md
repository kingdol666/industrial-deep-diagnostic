# DOE 分析流程优化 · 基线快照（Phase 0）

- 日期：2026-10-17
- 用途：`doe-analysis-flow-optimization-plan-2026-10-17.md` 的 Phase 0 基线；开工前先复核本文件
- 状态：只读快照；**不代表工作树干净，也不授权直接开工**

## 1. 仓库基线

| 项 | 值 |
|---|---|
| IDD 路径 | `D:\codes\myskills\industrial-deep-diagnostic` |
| IDD HEAD | `1ff3d6c80c681edff382979c69b416fe4b5f58dd` |
| IDD 工作树 | **420 条未提交变更**（`git status --short` 计数） |
| AgentWorkShop HEAD | `1e0cf1d72afabf694bc9bd87817c4c21d49a365a` |
| AgentWorkShop 工作树 | **48 条未提交变更**（并行会话；非本计划产物） |
| 计划文档 | `docs/plans/doe-analysis-flow-optimization-plan-2026-10-17.md` |
| Traceability | `docs/plans/doe-traceability.md` |

> **重要**：IDD 工作树的 420 条变更不是本计划创建的。开工前必须隔离，禁止直接在当前脏树上实现或提交；不要使用 `git stash`（并行会话会受影响）。建议用 `git worktree add` 从 HEAD 建干净工作树，或单独 clone。

## 2. 工具链

| 项 | 值 |
|---|---|
| OS / Arch | Windows (`win32 x64`) |
| Node | `v24.19.0` |
| npm | `11.17.0` |
| pnpm | `11.23.0` |
| Python | `3.12.7` |
| uv | `0.11.29` |
| CPU | AMD Ryzen 7 9700X 8-Core |
| RAM | 31.1 GB |

## 3. 测试基线（2026-10-17 实跑）

| 套件 | 结果 | 命令/证据 |
|---|---|---|
| IDD DOE analyzer | **136/136 绿** | `uv run --project .claude/shared/scripts python .claude/skills/industrial-doe-analyzer/tests/run_tests.py all` |
| IDD skill 数 | 24 个 | `ls .claude/skills` |
| AgentWorkShop 单元 | **219/219 绿** | `npm run test:unit`（见 `.AgentWorkShop/analysis/release-acceptance-2026-10-17.md`） |
| AgentWorkShop typecheck | 通过 | `npm run typecheck` |
| tool-verify E2E | 13/13 | `tmp-e2e/tool-verify-node-scope-20261017.mjs` |
| 诊断/DOE 已知缺口 | 见计划 §2 | 代码级证据已核对 |

> 这些基线是在当前脏树上跑的，只能证明“当时可跑”；Phase 0 必须在干净工作树上重跑并记录输出。

## 4. 开工冻结清单（Phase 0 必做）

1. **隔离**：
   ```bash
   cd D:/codes/myskills/industrial-deep-diagnostic
   git rev-parse HEAD                      # 记录
   git worktree add ../idd-doe-impl -b feat/doe-ontology-first HEAD
   cd ../idd-doe-impl
   ```
   或在独立 clone 中执行；不要动主工作树 420 条变更。
2. **记录**：把本文件复制/更新到新工作树，填入实际 SHA 与 `git status --short` 计数。
3. **重跑基线**：DOE 136/136、诊断管线相关测试、`quality_gate.mjs` 现有用例；红灯先修基线，不进入 Phase 1。
4. **填 traceability**：`docs/plans/doe-traceability.md` 的基线记录与 Phase 0 必填 case。
5. **契约冻结**：`run_table.csv` / `doe_context.json` / `analysis_context.json` / artifact manifest 的 schema 与示例先评审，再动实现。
6. **禁止**：直接在当前脏树提交、`git stash`、修改并行会话文件。

## 5. Phase 0 退出条件

- [ ] 干净工作树 + 分支已建立
- [ ] 双仓库 SHA / 工具链 / 硬件已记录
- [ ] IDD DOE 136/136 在干净工作树复现
- [ ] 契约 schema + 示例 + round-trip 测试通过
- [ ] traceability 37 条全部有映射（可先 TBD，但必须有 owner/计划）
- [ ] 计划状态从 `pending approval` 改为 `approved` 后才进入 Phase 1
