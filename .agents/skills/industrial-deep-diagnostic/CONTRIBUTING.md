# 贡献与修改规范

本文件说明如何安全地修改 `industrial-deep-diagnostic` skill，以及如何向本仓库贡献代码。

---

## 1. 修改前的必读清单

修改任何文件前，先阅读：

1. [SKILL.md](./SKILL.md) — 主执行协议，权威来源
2. [CLAUDE.md](./CLAUDE.md) — 开发者注意事项
3. [pipeline-execution.md](./pipeline-execution.md) — 详细执行参考
4. [resources/engineering_delivery_contract.md](./resources/engineering_delivery_contract.md) — 交付标准

---

## 2. 双版本同步规则

本 skill 同时维护两个版本：

- `.claude/skills/industrial-deep-diagnostic/` — Claude Code 使用
- `.agents/skills/industrial-deep-diagnostic/` — Codex/其他 Agent 使用

**任何修改必须同时同步到两个版本**，除非修改明确只针对某一平台。

同步方式：

```bash
# 从 .claude 同步到 .agents
rsync -av --delete .claude/skills/industrial-deep-diagnostic/ .agents/skills/industrial-deep-diagnostic/
```

修改后请运行一致性检查：

```bash
diff -r .claude/skills/industrial-deep-diagnostic/ .agents/skills/industrial-deep-diagnostic/
```

仅允许以下差异：
- 平台特定的路径引用
- 明确标记的平台适配说明

---

## 3. 文件组织约定

| 目录 | 用途 | 新增文件规则 |
|------|------|-------------|
| `agents/` | 子 Agent 协议 | 新增 Agent 必须同时更新 SKILL.md 的 Loading Guide 和 Execution Flow |
| `resources/` | 按需加载的方法论资源 | 新增资源必须在 SKILL.md Level 3 表格中注册 |
| `schemas/` | JSON Schema | 新增 schema 必须在 pipeline-execution.md Step Command Reference 中注册验证命令 |
| `scripts/` | 可执行脚本 | 新增脚本必须在 `resources/script_and_toolkit_reference.md` 中登记 |
| `templates/` | 输出模板 | 新增模板必须在对应 Agent 协议中引用 |
| `tests/checklists/` | 检查清单 | 新增检查项需说明触发场景 |
| `examples/` | 示例数据/本体 | 新增示例需说明适用场景 |

---

## 4. 修改 Agent 协议的规范

### 4.1 必须包含的章节

每个 Agent 协议（`agents/*.md`）必须包含：

1. **人格定义 / Persona**：经验背景、专业判断准则
2. **Core Principle**：该 Agent 的核心工作原则
3. **Parameters**：接收的参数列表
4. **Mandatory Delivery Contract**：完成前必须交付的产物
5. **Step-by-Step Protocol**：分阶段执行步骤
6. **Language Note**：输出语言约定

### 4.2 禁止的行为

- 不要假设主 Agent 会替你执行工作
- 不要引用不存在的 schema 或脚本
- 不要新增与现有编号体系冲突的编号
- 不要删除已有的红灯动作或治理规则，除非经过完整审计

---

## 5. 编号体系保护

本 skill 使用四套独立编号体系：

| 体系 | 范围 | 示例 |
|------|------|------|
| Pipeline Step 0-9 | 编排层 | Step 4: Diagnostician |
| Agent Phase 0-7 | Diagnostician 内部 | Phase 1: Data Probing |
| Reasoning Segment R1-R8 | reasoning_chain.json | R4: Hypothesis Generation |
| Method Stage 1-6 | diagnosis_method.md | Stage 3: Temporal Analysis |

新增编号时必须确保：
- 不冲突
- 在对应文档中说明编号体系
- 不在不同体系间混用

---

## 6. Schema 修改规范

1. **向后兼容优先**：新增字段应为 optional，避免破坏旧产物
2. **枚举值稳定**：enum 值修改会影响下游 Agent 判断，需谨慎
3. **中文自然语言 + 英文 enum**：自然语言描述用中文，结构化字段和 enum 保持英文
4. **同步验证脚本**：修改 schema 后检查 `validate.mjs` 是否需要更新

---

## 7. 新增 Eval 的规范

1. 在 `evals/evals.json` 中添加新场景
2. 在 `test-prompts.json` 中添加对应提示词
3. 每次 eval 运行后更新 `results.tsv`
4. 新增 eval 必须覆盖至少一种失败模式或边界场景

---

## 8. 文档修改规范

1. 新增文档必须在本 `README.md` 的文档索引中注册
2. 关键修改必须在 `CHANGELOG.md` 中记录
3. 文档中使用代码引用时必须使用 `file:///` 绝对路径链接
4. 避免在文档中写时间估计或性能承诺

---

## 9. 提交规范

提交信息格式：

```
<type>(<scope>): <subject>

<body>
```

类型：
- `feat`：新功能
- `fix`：修复
- `docs`：文档
- `refactor`：重构
- `chore`：杂项
- `sync`：双版本同步

范围示例：
- `industrial-deep-diagnostic`
- `diagnostic-html-visualizer`
- `agents/diagnostician`
- `schemas`
- `scripts`

---

## 10. 测试要求

任何修改都应运行以下检查：

```bash
# Schema 验证（以 ontology 为例）
node scripts/validate.mjs schemas/ontology_schema.json <test_ontology.json>

# 产物完整性
node scripts/artifact-check.mjs <RUN_DIR> <SKILL_PATH>

# 证据闭环
node scripts/evidence-closure-check.mjs <RUN_DIR> --write

# 执行日志
node scripts/pipeline-log-check.mjs <RUN_DIR>
```

---

## 11. 安全与隐私

- 不要提交包含真实生产数据的文件
- 不要提交 `.env`、凭证或 API key
- 日志和产物中若包含敏感数据，应在 `.gitignore` 中排除
- 详见 [SECURITY.md](./SECURITY.md)
