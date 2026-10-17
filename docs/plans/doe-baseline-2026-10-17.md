# DOE 分析流程优化 · 基线快照（Phase 0）

- 日期：2026-10-17
- 用途：`doe-analysis-flow-optimization-plan-2026-10-17.md` 的 Phase 0 基线
- 状态：**Phase 0 已执行**（隔离工作树已建立、基线已复现、冻结清单已闭合）

## 1. 仓库基线（冻结值）

| 项 | 值 |
|---|---|
| 主工作树路径 | `D:\codes\myskills\industrial-deep-diagnostic` |
| 主工作树 SHA | `1ff3d6c80c681edff382979c69b416fe4b5f58dd` |
| 主工作树分支 | `v4-AgentWorkShopIntegrate` |
| 主工作树状态 | **421 条未提交变更**（并行会话产物、非本计划；未触碰） |
| **本计划工作树** | `D:\codes\myskills\idd-doe-impl` |
| **本计划分支** | `feat/doe-ontology-first`（从 `1ff3d6c` 建立） |
| **本计划起始 SHA** | `1ff3d6c80c681edff382979c69b416fe4b5f58dd` |
| AgentWorkShop HEAD | `1e0cf1d72afabf694bc9bd87817c4c21d49a365a`（未触碰；Phase 6 单独跟踪） |
| 隔离方式 | `git worktree add D:/codes/myskills/idd-doe-impl -b feat/doe-ontology-first HEAD` |

> 主工作树的 421 条变更**未被修改**：未 `git stash`、未提交、未 checkout。
> 本计划全部实现落在 `D:\codes\myskills\idd-doe-impl`，以 `feat/doe-ontology-first` 分支独立评审/合并。
> ⚠️ 该分支基线**不含**并行会话对 `ontology_store.mjs`（加锁 / `ONTOLOGY_STORE_DIR`）等文件的改动；
> 合并时需要人工协调，见 §6。

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
| venv | `.claude/shared/scripts/.venv`（uv 管理；每个 worktree 独立引导） |

## 3. 测试基线（在干净工作树实跑）

| 套件 | 结果 | 命令 |
|---|---|---|
| IDD DOE analyzer | **136/136 绿** | `uv run --project .claude/shared/scripts python .claude/skills/industrial-doe-analyzer/tests/run_tests.py all` |
| 契约 round-trip（P0-2 新增） | **28/28 绿** | `uv run --project .claude/shared/scripts python docs/plans/contracts/roundtrip_test.py` |

> 已知套件副作用：`cmd_profile` 会把 `_predictor_cols` / `inference.assigned_by` 回写进
> `00_input/analysis_context.json`（契约 §3 要求合并结果写回本文件），因此跑完套件后 12 个
> fixture 的 context 文件会显示为 `M`。这是**既有行为**，用 `git checkout -- <fixtures>` 还原；
> Phase 5 将让 `run_tests.py` 自行还原输入夹具，消除该噪声。

## 4. 开工冻结清单（Phase 0 执行结果）

1. ✅ **隔离**：工作树 `D:/codes/myskills/idd-doe-impl` + 分支 `feat/doe-ontology-first`；主工作树 421 条变更未触碰。
2. ✅ **记录**：本文件 §1/§2 填入实际 SHA 与工具链。
3. ✅ **重跑基线**：DOE 136/136 在上述命令下于干净工作树复现。
4. ✅ **填 traceability**：`docs/plans/doe-traceability.md` 37 条全部有映射（含 owner 与延期说明）。
5. ✅ **契约冻结**：`docs/plans/contracts/`（README + 3 个 schema + run_table.md + examples + 28 条 round-trip 断言）。
6. ✅ **禁止项遵守**：未在主工作树提交、未 `git stash`、未修改并行会话文件。

## 5. Phase 0 退出条件

- [x] 干净工作树 + 分支已建立
- [x] 双仓库 SHA / 工具链 / 硬件已记录
- [x] IDD DOE 136/136 在干净工作树复现
- [x] 契约 schema + 示例 + round-trip 测试通过（28/28）
- [x] traceability 37 条全部有映射
- [x] 计划状态 `pending approval` → `approved (executing)`（2026-10-17，按用户指令批准）

## 6. 合并冲突预告（收尾时必读）

`feat/doe-ontology-first` 与主工作树未提交改动存在**已知重叠文件**，合并需人工处理：

| 文件 | 本计划改动 | 主工作树并行改动 |
|---|---|---|
| `.claude/shared/scripts/ontology_store.mjs` | 加 `profile`/`context_fp` 索引与过滤（P1-2） | 加锁 / `ONTOLOGY_STORE_DIR` / 坏索引备份（+400 行） |
| `app/backend/src/services/diagnosis.service.mjs` | DOE intent 本体编排（P1-6） | 多租户 / 归属过滤等（+241 行） |
| `app/backend/src/services/omp.service.mjs` | DOE artifact map（P4-2） | 路由 / 服务加固 |
| `config/loader.mjs` | 仅在需要新配置项时 | 配置加固（+135 行） |

策略：本计划改动保持**加法式补丁**（新增字段/函数、不改既有语义），降低合并成本。
建议合并顺序：先把主工作树改动提交，再 rebase `feat/doe-ontology-first`。
