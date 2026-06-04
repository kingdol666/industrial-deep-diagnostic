# Hermes Skill Standardization Guide

本文件定义当前 `industrial-deep-diagnostic` skill 在 Hermes 下的推荐规范，用于约束后续 skill 演进、子 agent 新增和执行流程维护。

## 1. 目录职责

| Path | Role |
|------|------|
| `SKILL.md` | skill 入口文档。只负责触发条件、主流程、加载规则、校验规则。 |
| `.hermes/agents.yaml` | 项目级子 agent 运行配置。定义模型、工具集、spawn 方式、是否为 orchestrator。 |
| `.hermes/config.yaml` | Hermes delegation 配置。定义默认 delegation 模型与嵌套委托深度。 |
| `.hermes/setup_skills.sh` | 生成项目专用 Hermes profile，不向全局 `~/.hermes/skills/` 注册 skill。 |
| `.hermes/agents/*.md` | 子 agent 启动模板。供主 agent 或父级子 agent 读取后发起 `delegate_task` / `terminal_spawn`。 |
| `agents/*.md` | 子 agent 完整执行协议。被实际启动后的子 agent 自行读取和执行。 |
| `resources/` | 按需加载的方法论、知识框架、交付契约。 |
| `schemas/` | 所有结构化输出的 schema。 |
| `scripts/` | 运行期工具脚本。 |

## 2. 子 Agent 创建规范

新增一个子 agent 时，必须同时创建两层文档：

1. `agents/<name>.md`
2. `.hermes/agents/<name>.md`

缺一不可。

### 2.1 `agents/<name>.md` 必须包含

- agent 身份与目标
- 输入参数说明
- 分阶段执行协议
- 输出工件路径
- schema-first 约束
- 完成判定标准

### 2.2 `.hermes/agents/<name>.md` 必须包含

- `Hermes launch stub only` 提示
- `delegate_task(...)` 或 `terminal_spawn` 示例
- `spawn_method`
- `role` (`leaf` 或 `orchestrator`)
- full protocol 入口：`SKILL_PATH/agents/<name>.md`

### 2.3 何时使用 `role: orchestrator`

只有当该子 agent 需要继续启动下一级子 agent 时，才设置为 `orchestrator`。

当前 skill 中：
- `data-processor` 是 `orchestrator`
- 其余 agent 都应保持 `leaf`

## 3. 委托执行规范

### 3.1 主 agent 允许做的事

- 读取 `SKILL.md`
- 读取 `.hermes/agents.yaml`
- 读取对应 `.hermes/agents/<name>.md`
- 组装 `delegate_task` / `terminal_spawn` 参数
- 等待子 agent 完成
- 校验输出工件与事件日志

### 3.2 主 agent 不允许做的事

- 读取 `agents/<name>.md` 后自己代替子 agent 执行完整业务协议
- 绕过 `.hermes/agents/*.md` 直接随意拼子 agent 调用
- 在没有 orchestrator 权限时让子 agent 再次委托

### 3.3 嵌套委托前提

若存在 `A -> B` 嵌套委托：

- `A` 必须在 `.hermes/agents.yaml` 中声明 `role: orchestrator`
- `.hermes/config.yaml` 必须设置：
  - `delegation.orchestrator_enabled: true`
  - `delegation.max_spawn_depth >= 2`

当前 skill 的唯一嵌套委托为：

- `data-processor -> vlm-visual-analyzer`

## 4. 推荐主流程

主 agent 推荐执行顺序：

1. 读取 `SKILL.md`
2. 读取 `.hermes/agents.yaml`
3. 执行 Step 0 / Step 1 主流程
4. 逐步读取对应 `.hermes/agents/<name>.md`
5. 发起委托
6. 子 agent 自行读取 `agents/<name>.md`
7. 每步结束后执行 schema 校验
8. 最终执行 artifact 与 pipeline event 校验

## 5. 维护规则

- 修改子 agent 行为时，优先更新 `agents/*.md`
- 修改子 agent 启动方式时，更新 `.hermes/agents/*.md` 与 `.hermes/agents.yaml`
- 若新增嵌套委托，必须同步审查 `.hermes/config.yaml`
- 不再新增第三套 agent 协议入口，避免职责漂移
- 保持项目本地加载方式；不要重新引入全局 symlink 注册方案

## 6. 当前标准化结果

当前 skill 已按本规范收敛为：

- 一份主入口：`SKILL.md`
- 一套项目级 launch stubs：`.hermes/agents/*.md`
- 一套 skill 内完整协议：`agents/*.md`
- 一份项目级 agent 配置：`.hermes/agents.yaml`
- 一份 delegation 配置：`.hermes/config.yaml`

后续扩展请保持这一分层，不要把“启动模板”和“完整协议”重新混回同一个文件。
