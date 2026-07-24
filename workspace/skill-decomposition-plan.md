# 工业深度诊断 Skill 分解计划

> 目标：将单体重工业诊断 skill 拆解为原子化模块技能 + 自动编排器
> 日期：2026-07-24

---
## 关键修正声明

> ⚠️ 本计划已通过二次审查，修复了 3 个关键错误，见 §"审查发现的修正"。

> ### 审查发现的纠正
> 
> | # | 原版本错误 | 修正 | 影响 |
> |---|----------|------|------|
> | 1 | **§3.1 架构总览** — 子Agent协议（agents/*.md）要"移入"各模块 skill 目录 | 子Agent协议**禁止移动**。它们必须保留在 `.claude/agents/` 下——subagent_type 系统从此处解析协议。移入 skill 目录会破坏子Agent启动机制 | 🔴 阻断级 |
> | 2 | **§3.1 架构总览** — schemas/ scripts/ resources/ 目录标记为 "REMOVED" 要分散到各 skill | 这些目录**保留不动**。所有模块 skill 共享原路径下的脚本、schema、资源。SKILL.md 通过 SKILL_PATH 指向原目录来引用 | 🔴 阻断级 |
> | 3 | **§3.4~§3.5** — 详细表格列出每个文件归属哪个 skill，及跨skill资源"复制到各自skill目录" | 已替换为"不移动，共享原位置"的简表。统一走 SKILL_PATH 引用 | 🟡 中，原计划可执行但引入不必要的复杂性 |
> | 4 | **§6.2 权衡决策** — 最后一行 "批量 git mv" | 已替换为"逐个按需创建" | 🟢 低，语义修正 |
> | 5 | **§3.2 模块契约** — 未说明模块 SKILL.md 如何引用共享路径 | 已补充设定 SKILL_PATH 指向原始 skill 目录的设计 | 🟡 中 |
> 
> **根本原因**：原计划误解了 OMC 的 subagent_type 注册机制。子Agent类型在 `.claude/agents/` 注册，不在 skill 目录内。这导致整个"文件移动"的思路是错误的。修正后的架构是"轻量级新增"方案——不移动任何文件，只创建薄 SKILL.md。

---

## 一、现状分析：为什么"重"？

### 1.1 当前单体结构的规模

| 类型 | 数量 | 总大小 | 说明 |
|------|------|--------|------|
| SKILL.md | 1 | 711行 | 编排 + Agent协议 + 检查点 + 故障恢复 |
| Agent协议 | 9 | ~350KB | 每个Agent的完整执行协议 |
| Resources | 14 | ~130KB | 领域知识框架 |
| Scripts | 27 | ~460KB | 统计分析、可视化、验证工具 |
| JSON Schema | 16 | ~50KB | 结构化数据契约 |

### 1.2 实际耦合度（关键发现）

**文件级依赖分析结论：耦合度远低于表面印象。**

| 依赖类型 | 现状 | 严重程度 |
|----------|------|---------|
| Agent→Script | 极弱 — 每个Agent只引用2-3个脚本 | 🟢 易解耦 |
| Agent→Schema | 极弱 — 只有 Judge/Reporter/VLM 引用自己的schema | 🟢 易解耦 |
| Agent→Resources | 弱 — 每个Agent引用0-3个资源文件 | 🟢 易解耦 |
| Agent间通信 | 无直接依赖 — 只通过 RUN_DIR 文件契约通信 | ✅ 天然解耦 |
| 共享基础设施 | validate.mjs + 全部 schemas（最多）| 🟡 少量耦合 |
| Python环境 | 共享 venv (pyproject.toml) | 🟡 中等 |

**核心结论：当前单体结构的"重"不是技术耦合导致的，是组织方式的臃肿。**

### 1.3 真正的"重"在哪里

```
伪因1: 代码耦合                    ✘ 伪 — 各Agent通过文件契约解耦，不是函数调用
伪因2: 业务逻辑交织                ✘ 伪 — Step 0-9 本身就是流水线，边界清晰
伪因3: 依赖沉重                    ✘ 伪 — 只有 validate.mjs + schemas 共享

真因1: 所有Agent协议堆在一个SKILL.md   ✓ — 711行一个人读不完
真因2: 所有Resources在同一个目录       ✓ — 但每个Agent只用其中2-3个
真因3: 无法最小粒度使用                ✓ — /industrial-deep-diagnostic 必须跑全流程
真因4: 没有单独发布能力                ✓ — 不能只安装"统计引擎"或"本体构建器"
```

---

## 二、可行性评估：能拆吗？

### 2.1 能拆，且拆的边界是自然的

```
Pipeline Step          → Skill Module
─────────────────────────────────────
Step 0-1: Setup+Inspect → infrastructure (保持内嵌)
Step 2: Context Build   → industrial-ontology-builder    🟢 独立模块
Step 3: Data Process    → industrial-data-processor      🟢 独立模块
Step 3.5: VLM           → industrial-vlm-analyzer        🟢 独立模块
Step 4: Diagnose        → industrial-diagnostician       🟢 独立模块
Step 5a: Judge          → industrial-judge               🟢 独立模块
Step 5b/7: Audit        → industrial-physical-auditor    🟢 独立模块
Step 6: Report          → industrial-reporter            🟢 独立模块
Step 8: HTML            → industrial-html-visualizer     🟢 独立模块
Step 8.5: HTML Review   → industrial-html-reviewer       🟢 独立模块

Orchestrator            → industrial-deep-diagnostic     🆕 瘦编排层
```

### 2.2 关键可行性问题

| 问题 | 答案 |
|------|------|
| Agent sub_type 注册需要每个skill独立吗？ | **不需要。** 子Agent类型已经在平台注册为可独立调用的 agent type（`context-builder`, `data-processor` 等）。拆分为 skill 后，每个 skill 在自己的 SKILL.md 中通过 Agent 工具调用这些 subagent_type 即可。 |
| 共享文件（validate.mjs + schemas）放在哪？ | 方案A: **共享库 skill** — 创建一个 `industrial-skill-common` skill 只放共享工具，所有其他 skill 通过 `SKILL_PATH` 引用。方案B: **复制到每个 skill** — 每个 skill 维护自己的 validate.mjs + 自己需要的 schemas（推荐，因为 schemas 每个 skill 只用到 1-2 个，validate.mjs 仅 7.7KB）。 |
| Python venv 怎么办？ | **每个 skill 独立 venv**（推荐） 或 **共享顶层 venv**。做独立 venv 成本低（uv_env_setup.mjs 仅 3.6KB），且避免版本冲突。 |
| RUN_DIR 目录约定要改吗？ | **不改。** 文件契约是 pipeline 的核心接口，所有 skill 读写相同的 RUN_DIR 目录结构（`00_input/`, `01_ontology/` 等）。这是编排器的职责——确保每个 skill 收到正确的 RUN_DIR。 |
| 相互引用 Resources 怎么办？ | **按 skill 拆分 Resource**。diagnostician 不需要 visual_analysis_framework.md；data-processor 不需要 physics_inference_framework.md。每个 skill 只带自己需要的 2-3 个资源。 |
| 跨 skill 的 CP 检查点怎么管？ | **编排器负责 CP 检查。** 每个 skill 完成时产出校验过的文件，编排器在上游执行 CP 检查后，才启动下游 skill。这是编排器的核心职责。 |

### 2.3 可行性结论

**✅ 完全可行。** 实际代码耦合度低，拆分主要是文件组织问题，不是架构重构。8个模块 skill + 1个编排器 + 1个共享库 ≈ 10个 skill 目录，每个 skill 的 SKILL.md 控制在 100 行以内。

---

## 三、分解设计

### 3.1 架构总览

```
industrial-deep-diagnostic/          ← 项目根（CLAUDE.md + config + app + data + rag-engine）
├── .claude/
│   ├── agents/                       ← [保留不动] 子Agent类型注册于此（subagent_type解析来源）
│   │   ├── context-builder.md
│   │   ├── data-processor.md
│   │   ├── vlm-visual-analyzer.md
│   │   ├── diagnostician.md
│   │   ├── judge.md
│   │   ├── report-reviewer.md
│   │   ├── reporter.md
│   │   ├── html-visualizer.md
│   │   └── html-reviewer.md
│   │
│   ├── skills/
│   │   ├── industrial-deep-diagnostic/   ← [保留不动] 共享基础设施（scripts/schemas/resources）
│   │   │   ├── SKILL.md             (~200行，从711行精简为编排器)
│   │   │   ├── scripts/ (全部原有脚本 — 所有模块skill共享)
│   │   │   ├── schemas/ (全部原有schema — 所有模块skill共享)
│   │   │   └── resources/ (全部原有资源 — 所有模块skill共享)
│   │   │
│   │   ├── industrial-ontology-builder/   ← [NEW] 模块skill（仅SKILL.md，无agents/scripts/schemas）
│   │   │   └── SKILL.md             (~80行 — 引用 .claude/agents/ 和 .claude/skills/industrial-deep-diagnostic/)
│   │   │
│   │   ├── industrial-data-processor/    ← [NEW] 模块skill
│   │   │   └── SKILL.md             (~80行)
│   │   │
│   │   ├── industrial-vlm-analyzer/      ← [NEW] 模块skill
│   │   │   └── SKILL.md             (~50行)
│   │   │
│   │   ├── industrial-diagnostician/     ← [NEW] 模块skill
│   │   │   └── SKILL.md             (~80行)
│   │   │
│   │   ├── industrial-judge/             ← [NEW] 模块skill
│   │   │   └── SKILL.md             (~50行)
│   │   │
│   │   ├── industrial-physical-auditor/  ← [NEW] 模块skill
│   │   │   └── SKILL.md             (~50行)
│   │   │
│   │   ├── industrial-reporter/          ← [NEW] 模块skill
│   │   │   └── SKILL.md             (~50行)
│   │   │
│   │   ├── industrial-html-visualizer/   ← [NEW] 模块skill
│   │   │   └── SKILL.md             (~50行)
│   │   │
│   │   └── industrial-html-reviewer/     ← [NEW] 模块skill
│   │       └── SKILL.md             (~30行)
│   │
│   └── ... (其他skill保持不变)
│
├── schemas/                           ← [保留不动] 不被移动
├── scripts/                           ← [保留不动] 不被移动
├── resources/                         ← [保留不动] 不被移动
│
└── ... (rest unchanged)
```

### 3.2 模块契约：最小可调用单元

### 3.2 模块契约：最小可调用单元

每个模块 skill 的 SKILL.md 必须明确定义：

```markdown
# industrial-<模块名>

## 功能
一句话描述这个模块做什么。

## 输入（必须）
- `RUN_DIR/XX_xxx/xxx.json` — 描述输入文件

## 输出
- `RUN_DIR/YY_yyy/yyy.json` — 描述输出文件

## 用法
/industrial-<模块名> RUN_DIR=/path

## 依赖
- 需要哪些上游文件已存在（不要求全pipeline，只要求直接依赖）
```

### 3.3 编排器设计：industrial-deep-diagnostic

编排器不再是全协议，而是：

```markdown
# industrial-deep-diagnostic (编排器)

## 功能
编排 8 个模块 skill 按顺序执行完整工业诊断 pipeline。

## 流程
1. Setup + Inspect（内建）
2. 调用 /industrial-ontology-builder   (Step 2)
3. 运行 Clarification Gate（内建）
4. 调用 /industrial-data-processor     (Step 3 + 3.5)
5. 调用 /industrial-diagnostician      (Step 4)
6. 并行调用 /industrial-judge + /industrial-physical-auditor (Step 5a+5b)
7. 修复循环（如果Judge < 90 或 pre-audit有阻断项）
8. 调用 /industrial-reporter           (Step 6)
9. 调用 /industrial-physical-auditor   (Step 7, 终审)
10. 调用 /industrial-html-visualizer   (Step 8)
11. 调用 /industrial-html-reviewer     (Step 8.5)
12. Finalize（内建）

## 检查点 (CP-1 ~ CP-9)
每个步骤完成后验证产物，决定继续/修复/回退。

## 修复循环协议
Judge best-of-3, anti-oscillation, global cap ≤ 5
```

### 3.4 资源分布（不移动，共享原位置）

**核心决策：所有 scripts / schemas / resources 保持不变，留在原 skill 目录下。** 每个模块 skill 的 SKILL.md 通过 `SKILL_PATH` 指向原目录来引用这些资源。这是最简洁的方案，避免了文件移动带来的层级混乱和引用路径维护问题。

| 文件位置 | 说明 |
|----------|------|
| `.claude/skills/industrial-deep-diagnostic/scripts/` | 保持不动，作为所有模块 skill 的共享脚本池 |
| `.claude/skills/industrial-deep-diagnostic/schemas/` | 保持不动，作为所有模块 skill 的共享 schema 池 |
| `.claude/skills/industrial-deep-diagnostic/resources/` | 保持不动，作为所有模块 skill 的共享资源池 |
| `.claude/agents/` | 保持不动，作为子 Agent 类型注册点 |

### 3.5 共享资源策略（跨 skill 引用）

两个资源被多个 skill 引用：
- `evidence_rules.md` → 被 diagnostician + judge + report-reviewer 引用
- `data_ontology_mapping_framework.md` → 被 context-builder + data-processor 引用

**方案**：不复制，不移动。各模块 skill 的 SKILL.md 中明确声明这些资源的路径，统一指向主工程 `.claude/skills/industrial-deep-diagnostic/`。所有模块 skill 的 `SKILL_PATH` 指向 `.claude/skills/industrial-deep-diagnostic/`。

---

## 四、实施路线图

### 阶段 1：准备（1天）
1. 确保 `SKILL_PATH` 正确指向 `.claude/skills/industrial-deep-diagnostic/`（所有模块 skill 共享此路径）
2. 确认 `agents/`、`scripts/`、`schemas/`、`resources/` 等目录存在且完整
3. 为每个模块创建 `.claude/skills/industrial-<name>/` 目录
4. 将本计划的"Example SKILL.md"适配注入各模块目录

### 阶段 2：增量式模块包装（3-4天，按独立 skill 批量创建）

**核心理念：不移动任何文件。** 当前 `SKILL.md`、`agents/`、`scripts/`、`schemas/`、`resources/` 全部保留在原位置不动。每个模块 skill 只是一个**轻量包装层**——SKILL.md 告诉 Agent 去哪里读取原有的 agents/*.md 协议、以及如何调用主工程的 scripts/、schemas/、resources/。

每个模块 skill 的操作：
1. 在 `.claude/skills/` 下创建 skill 目录 `industrial-<name>/`
2. 创建 SKILL.md（~30-80 行），内容为：
   - 功能说明（1-2句）
   - 输入/输出契约（文件级，指向 `RUN_DIR/XX_xxx/xxx.json`）
   - 启动方式示例
   - **调用原来 agent 协议的指令**（`Read "$SKILL_PATH/../industrial-deep-diagnostic/agents/<protocol>.md" and execute the complete protocol.`）
   - 对应的主工程 scripts/、schemas/、resources/ 的引用路径（指向 `$SKILL_PATH/../industrial-deep-diagnostic/scripts/` 等）
3. 可选：在主工程 `.claude/skills/industrial-deep-diagnostic/SKILL.md` 中更新 Agent 调用路径（从原来的 `RunDir/agents/name.md` 改为新 skill 的引用方式）
4. **不复制、不移动任何脚本、schema、资源文件。** 所有共享文件归主工程 skill 管理。

**Example SKILL.md for a module:**
```markdown
# industrial-ontology-builder

## 功能
工业诊断 Step 2 — RAG 检索 + 网络搜索 + 数据自描述 → ontology.json

## 输入
- `RUN_DIR/00_input/input_manifest.json`（数据列描述）
- `RUN_DIR/00_input/user_context.json`（用户上下文）

## 输出
- `RUN_DIR/01_ontology/ontology.json`
- `RUN_DIR/01_ontology/clarification_needed.json`
- `RUN_DIR/00_input/rag_deep_understanding.json`

## 用法
```
/industrial-ontology-builder RUN_DIR=/path
```

## 依赖
- 共享基础设施（validate.mjs, setup.mjs）由主工程 `industrial-deep-diagnostic` 提供
- schema 文件：`$SKILL_PATH/../industrial-deep-diagnostic/schemas/ontology_schema.json`
- 资源文件：`$SKILL_PATH/../industrial-deep-diagnostic/resources/rag_deep_understanding_protocol.md`

## 执行
```bash
# 协议文件位于主工程 agent 目录下
# Read the full protocol: $SKILL_PATH/../industrial-deep-diagnostic/agents/context-builder.md
# 执行 context-builder.md 中的 Phase A-D 协议
# 验证: node "$SKILL_PATH/../industrial-deep-diagnostic/scripts/validate.mjs" "$SKILL_PATH/../industrial-deep-diagnostic/schemas/ontology_schema.json" "$RUN_DIR/01_ontology/ontology.json"
```

**执行顺序**（按依赖关系）：
1. `industrial-ontology-builder` — 无上游skill依赖
2. `industrial-data-processor` — 无上游skill依赖
3. `industrial-vlm-analyzer` — 通过data-processor调用，但可以独立运行
4. `industrial-diagnostician` — 依赖data-processor输出
5. `industrial-judge` — 依赖diagnostician输出，也可独立评审
6. `industrial-physical-auditor` — 依赖reporter或diagnostician输出
7. `industrial-reporter` — 依赖diagnostician+judge输出
8. `industrial-html-visualizer` — 依赖所有上游
9. `industrial-html-reviewer` — 依赖html-visualizer输出
### 阶段 3：重构编排器（1天）
1. 清理 `industrial-deep-diagnostic/SKILL.md` 从 711 行精简到 ~200 行
2. 只保留：编排逻辑、CP检查点、修复循环、故障恢复
3. 删除所有 Agent 协议内容（Agent协议移到了各个子 skill 中）
4. 保留 engineering_delivery_contract.md + pipeline_coherence_and_synergy.md
5. 保留 artifact-check.mjs + pipeline-log-check.mjs + evidence-closure-check.mjs 等编排脚本

### 阶段 4：Agent协议瘦身（并行于阶段3）
每个 Agent 协议从原来的 ~30-90KB 精简：
- 去掉 Pipeline 编排相关内容（移到编排器 SKILL.md）
- 去掉跨步骤的协同协议（移到编排器或各 skill SKILL.md）
- 只保留自己的执行协议（Phase 0-7 / 分析流程）
- 目标是每个 agent protocol < 30KB

### 阶段 5：测试与验证
1. 单独测试每个模块 skill 的独立调用
2. 测试编排器全流程编排
3. 运行 ground truth 评估集
4. 修复路径冲突 / schema 引用问题

---

## 五、使用场景

### 场景 A：全流程诊断（完整pipeline）
```
用户: /industrial-deep-diagnostic
→ 编排器自动按 Step 0-9 调度各模块 skill
→ 用户"零干预"获得 report.md + diagnostic-report.html
```

### 场景 B：只做数据分析
```
用户: /industrial-data-processor RUN_DIR=/path/to/existing/run
→ 跳过本体构建
→ 基于已有数据直接做统计分析 + 出图
→ 适合：已有ontology，只想跑统计验证
```

### 场景 C：只做诊断（已有数据分析结论）
```
用户: /industrial-diagnostician RUN_DIR=/path
→ 跳过 Step 0-3
→ 基于已有 data_analysis_conclusion.json 做物理诊断
→ 适合：多次迭代诊断
```

### 场景 D：只做质量评审（已有诊断结果）
```
用户: /industrial-judge RUN_DIR=/path
→ 评审已有诊断的质量
→ 适合：复核历史诊断
```

### 场景 E：自动化编排器
```
用户: /autopilot "在 /data/cnc.csv 上做工业诊断"
→ autopilot 调用 /industrial-deep-diagnostic
→ 编排器自动调度子模块
```

---

## 六、风险与权衡

### 6.1 风险

| 风险 | 等级 | 缓解措施 |
|------|:----:|---------|
| 路径兼容性破坏 — `SKILL_PATH` 指向改变了 | 🔴高 | 保持 `SKILL_PATH` 指向主工程 `.claude/skills/industrial-deep-diagnostic/`，所有模块 skill 通过 `.claude/skills/` 下工业的子目录层级正确找到主工程 scripts/schemas/resources |
| 子Agent sub_type 注册名不变 | 🟢低 | subagent type name 不变（`context-builder`, `data-processor` 等），各skill SKILL.md 中 Agent 调用方式不变 |
| 用户自定义脚本引用原路径 | 🟡中 | 保留 6 个月的迁移期：在原路径放 README 说明新路径 |
| 编排器 SKILL.md 过薄失去自包含性 | 🟡中 | 编排器 SKILL.md 应包含"如何安装各模块skill"的说明 |
| 拆得太碎（10个skill） | 🟡中 | 这是合理的粒度——每个技能都真正独立可用。用户不需要全部安装 |
| git 历史混乱 | 🟢低 | 用 git mv 保持历史连续性 |
| eval-assertions.mjs 引用路径失效 | 🟡中 | 更新 eval-assertions.mjs 中的路径常量 |

### 6.2 权衡决策

| 选项 A | vs | 选项 B | 选择 | 原因 |
|--------|:--:|--------|:----:|------|
| 共享 validate.mjs + schemas | vs | 复制到每个 skill | **绝对不复制** | validate.mjs 仅 7.7KB，但保持与主工程同步比复制更重要；模块 SKILL.md 直接引用主工程的路径 |
| 共享 venv | vs | 每个 skill 独立 venv | **共享** | Python依赖都相同（numpy/scipy/matplotlib），共享改一个地方就行 |
| 共享受欢迎资源（evidence_rules.md 被3个skill引用） | vs | 复制到每个 skill | **不复制，路径引用** | 每个文件 <6KB，但复制会导致版本漂移隐患；模块 SKILL.md 直接通过主工程路径访问 |
| 编排器中内建 Setup+Inspect | vs | 拆成单独的 skill | **内建** | Step 0-1 是纯CLI脚本执行，不涉及子Agent，没必要独立skill |
| 文件级契约共享（RUN_DIR 目录结构） | vs | 每个 skill 独立定义契约 | **共享** | RUN_DIR 目录结构是 pipeline 的核心接口，改变成本太高 |
| 一次性创建所有模块 skill | vs | 逐个按需创建 | **逐个按需创建** | 优先级从常用开始（ontology-builder / diagnostician），每个模块独立发布，不阻塞其他模块 |

---

## 七、评估指标

完成后衡量效果：

| 指标 | 当前值 | 目标值 |
|------|:------:|:------:|
| SKILL.md 行数（编排器） | 711 | ≤200 |
| 单个 SKILL.md 最大行数（非编排器） | — | ≤80 |
| 独立可调用的 skill 数 | 1 | 9（8模块 + 1编排器） |
| 任何 Agent 协议最大大小 | 92KB | ≤30KB |
| 编排器 SKILL.md 中的 Agent 启动代码重复 | 大量 | 统一模板 |
| 最小诊断用例（e.g. 只重新评审）步骤数 | 9 | 1（单独调用 judge） |
| 新场景适配需要修改的文件范围 | 1个大目录 | 1个模块 skill |