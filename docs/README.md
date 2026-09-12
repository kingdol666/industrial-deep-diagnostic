# Docs — 项目文档索引（仅保留有效文档）

> 2026-09-12 清理后：只保留与当前系统实现一致、且被代码/benchmark 引用的文档。
> 已删除：过期实验手册（docs/experience，被根 `experience/` 证据库取代）、
> 被取代的规划（skill-optimization-plan v1-v3，由 v4 取代）、未落地方案
> （DOE-integration-plan / architect-proposal）、历史工作流沉淀（superpowers）、
> 空占位目录（reference/guides）。

## 核心文档

| 文档 | 内容 |
|---|---|
| [api.md](api.md) | 外部 API 接口定义 + 错误码表 + 接入三步（已验证） |
| [benchmark/](benchmark/README.md) | 诊断基准唯一文档入口：README（8 场景）+ design（指标/期刊 baseline 对标/口径 A/B）+ execution-guide（管线执行规程）+ reproduction-guide（复现手册）；编排脚本在 `scripts/benchmark/` |
| [multi-harness.md](multi-harness.md) | 14 执行引擎适配架构（能力矩阵、工程纪律、API） |
| [publication-strategy-report.md](publication-strategy-report.md) | 投稿策划（AEI 主投、章节模板、对比矩阵、命中率策略） |
| [dataset-experiment-research.md](dataset-experiment-research.md) | 数据集调研与实验设计依据 |
| [ontology-management.md](ontology-management.md) | 本体模型管理（持久化/版本/复用） |
| [agentworkshop-integration.md](agentworkshop-integration.md) | AgentWorkShop 插件集成契约 |

## 系统与规划

| 文档 | 内容 |
|---|---|
| `architecture/` | 系统架构、仓库布局、数据流、管线图（SVG/HTML） |
| `design/` | 已批准的设计方向 |
| [skill-optimization-plan-v4.md](skill-optimization-plan-v4.md) | 技能系统优化计划 v4（已实施：本体资产化/提速/意图驱动） |
| [efficiency-optimization-plan-v5.md](efficiency-optimization-plan-v5.md) | 效率优化计划 v5（已实施：确定性快路径） |
| [process-engineer-perspective.md](process-engineer-perspective.md) | 工艺工程师视角的系统可用性设计 |

## 阅读顺序

1. `architecture/system-overview.md` → `architecture/repository-layout.md`
2. `benchmark/README.md` → `benchmark/design.md` → 根 `experience/README.md`（证据库与复现）
3. 需要外部集成时读 `api.md`、`agentworkshop-integration.md`、`multi-harness.md`
