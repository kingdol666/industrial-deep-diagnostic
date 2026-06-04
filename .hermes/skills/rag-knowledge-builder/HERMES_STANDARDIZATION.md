# Hermes Skill Standardization Guide

本文件定义 `rag-knowledge-builder` 在当前项目中的 Hermes 规范化约定。

## 1. 目录职责

| Path | Role |
|------|------|
| `SKILL.md` | skill 主入口。定义触发条件、阶段顺序、输入输出契约、加载规则。 |
| `.hermes/agents/rag-*.md` | Hermes 启动模板。供主 agent 在各阶段发起 `delegate_task`。 |
| `agents/*.md` | 每个阶段的完整执行协议，由被启动的子 agent 自行读取。 |
| `.hermes/agents.yaml` | 共享 agent runtime 配置，登记 RAG 阶段 agent。 |
| `.hermes/config.yaml` | 共享 delegation 配置。 |
| `.hermes/setup_skills.sh` | 生成项目专用 Hermes profile，不把 skill 注册到全局 skill 目录。 |
| `resources/` | 本体设计原则、集成指南、评分 rubric 等参考。 |
| `scripts/` | RAG engine 客户端与辅助脚本。 |

## 2. 子 Agent 分层

RAG skill 采用以下分层：

1. `rag-retrieval-agent`
2. `rag-scoring-agent`
3. `rag-ontology-construction-agent`
4. `rag-structured-data-generator`
5. `rag-quality-verification-agent`

这些名称用于 `.hermes/agents.yaml` 的运行时登记；对应的完整协议正文仍位于 `agents/*.md`。

## 3. 主 Agent 执责边界

主 agent 负责：

- 读取 `SKILL.md`
- 读取对应 `.hermes/agents/rag-*.md`
- 按阶段发起委托
- 检查阶段产物是否存在
- 执行最终完整性校验

主 agent 不负责：

- 读取 `agents/*.md` 后自己执行完整阶段协议
- 跳过评分或质量验证阶段
- 直接绕过 launch stubs 拼接临时 prompt

## 4. 执行建议

推荐阶段顺序：

1. Phase 0: engine startup / health check
2. Phase 1a: retrieval
3. Phase 1b: scoring
4. Phase 2: ontology construction
5. Phase 3: structured data generation
6. Phase 4: quality verification

如果作为 consumer skill 的前置步骤运行，也建议保持这一顺序。

## 5. 维护规则

- 修改阶段业务协议时，更新 `agents/*.md`
- 修改委托入口时，更新 `.hermes/agents/rag-*.md`
- 修改模型、toolsets、迭代上限时，更新 `.hermes/agents.yaml`
- 不新增与现有两层并行的第三套 phase 协议入口
- 保持项目本地加载；不要引入全局 `~/.hermes/skills/` 注册
