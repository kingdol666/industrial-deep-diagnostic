# Industrial Deep Diagnostic — 技能系统优化计划 v3（可执行版）

> 基于 v2 的完整自审计修正。v2 的 7 项设计正确但**引用迁移范围低估 3x、依赖顺序未明确、验收标准缺失**。
> v3 修正：精确文件清单、严格依赖顺序、每阶段验收门、完整 blast radius。

---

## 零、审计基线（不可变）

```
项目总代码量:     140,344 行
重复脚本浪费:     120,659 字节（4 组脚本 × 18 个副本）
Schema 冗余:      46 个文件分布在 3 个目录（5 个 schema 版本不一致）
Agent Protocol:   306,023 字节（9 个文件，最大 84KB）
validate.mjs 引用: ~70 个文件（其中 ~34 个是硬依赖）
```

---

## 一、优化方案（4 个 Phase，13 个可执行步骤）

### Phase A: Foundation — 统一共享基础设施（P0）

> **必须先做**。所有后续 Phase 依赖此 Phase 的路径约定。

#### Step A1: 创建 shared/ 目录结构

```
.claude/shared/                    ← 新建：项目级共享目录
├── schemas/                       ← 16 个 schema 的唯一权威副本
│   └── _schema_index.json         ← 轻量索引：{ "diagnosis": "diagnosis_schema.json", ... }
├── scripts/                       ← 4 个共享脚本的唯一副本
│   ├── validate.mjs
│   ├── append-pipeline-event.mjs
│   ├── uv_env_setup.mjs
│   └── convert.mjs
└── README.md                      ← 使用约定：SHARED_PATH 变量、路径约定
```

**执行清单**:
- [ ] `mkdir -p .claude/shared/schemas .claude/shared/scripts`
- [ ] 从 `.claude/skills/industrial-analysis-auto/schemas/` 复制全部 16 个 schema → `shared/schemas/`
- [ ] 从 `.claude/skills/industrial-analysis-auto/scripts/` 复制 4 个共享脚本 → `shared/scripts/`
- [ ] 创建 `shared/schemas/_schema_index.json`
- [ ] 创建 `shared/README.md`（内容：SHARED_PATH 约定、脚本用途表）

#### Step A2: 在所有 Agent Context 中注入 SHARED_PATH

**blast radius**: 12 个 SKILL.md + 9 个 `.omp/agents/*.md` + 1 个 orchestrator SKILL.md = **22 个文件**

每个文件的 Agent prompt 模板中，在现有 `SKILL_PATH=...` 之后添加一行：
```
SHARED_PATH=<project-root>/.claude/shared
```

**执行清单**:
- [ ] 更新 12 个 `.omp/skills/*/SKILL.md` — Agent prompt 模板中加入 SHARED_PATH
- [ ] 更新 9 个 `.omp/agents/*.md` — 参数段中加入 SHARED_PATH
- [ ] 更新 `.omp/skills/industrial-analysis-auto/SKILL.md` — orchestrator prompt 中加入 SHARED_PATH

#### Step A3: 迁移硬引用（validate.mjs / append-pipeline-event.mjs / uv_env_setup.mjs / convert.mjs）

**blast radius**: ~34 个文件中的 bash 命令和 `$SKILL_PATH/scripts/validate.mjs` 引用

替换规则：
```
旧: $SKILL_PATH/scripts/validate.mjs    → 新: $SHARED_PATH/scripts/validate.mjs
旧: $SKILL_PATH/scripts/append-pipeline-event.mjs → 新: $SHARED_PATH/scripts/append-pipeline-event.mjs
旧: $SKILL_PATH/scripts/uv_env_setup.mjs → 新: $SHARED_PATH/scripts/uv_env_setup.mjs
旧: $SKILL_PATH/scripts/convert.mjs     → 新: $SHARED_PATH/scripts/convert.mjs
```

**执行清单**:
- [ ] 更新 12 个 `.omp/skills/*/SKILL.md` — bash 验证段
- [ ] 更新 9 个 `.claude/skills/*/references/agent-protocol.md` — bash 调用段
- [ ] 更新 9 个 `.omp/agents/*.md` — 部分 agent 的脚本调用
- [ ] 更新 `industrial-analysis-auto/SKILL.md` — Step 9 finalize 段
- [ ] 更新 `artifact-check.mjs` — resolveScript() 映射表（如果引用 validate.mjs）
- [ ] 更新 `pipeline-log-check.mjs` — 如果引用 append-pipeline-event.mjs
- [ ] 更新 `finalize-run-artifacts.mjs` — 如果引用共享脚本

#### Step A4: 删除冗余文件

**删除清单（共 ~46+ 个文件）**:

| 目录 | 文件 | 数量 |
|:-----|:-----|:----:|
| `.hermes/skills/industrial-deep-diagnostic/schemas/` | 全部 `*_schema.json` | 14 |
| `.agents/skills/industrial-deep-diagnostic/schemas/` | 全部 `*_schema.json` | 16 |
| `.claude/skills/industrial-data-processor/scripts/` | `validate.mjs` | 1 |
| `.claude/skills/industrial-diagnostician/scripts/` | `validate.mjs` | 1 |
| `.claude/skills/industrial-html-reviewer/scripts/` | `validate.mjs` | 1 |
| `.claude/skills/industrial-judge/scripts/` | `validate.mjs` | 1 |
| `.claude/skills/industrial-ontology-builder/scripts/` | `validate.mjs` | 1 |
| `.claude/skills/industrial-reporter/scripts/` | `validate.mjs` | 1 |
| `.claude/skills/industrial-vlm-analyzer/scripts/` | `validate.mjs` | 1 |
| `.claude/skills/industrial-data-processor/scripts/` | `append-pipeline-event.mjs` | 1 |
| `.claude/skills/industrial-physical-auditor/scripts/` | `append-pipeline-event.mjs` | 1 |
| `.claude/skills/industrial-reporter/scripts/` | `append-pipeline-event.mjs` | 1 |
| `.claude/skills/industrial-vlm-analyzer/scripts/` | `append-pipeline-event.mjs` | 1 |
| `.claude/skills/industrial-data-processor/scripts/` | `uv_env_setup.mjs` | 1 |
| `.claude/skills/industrial-physical-auditor/scripts/` | `uv_env_setup.mjs` | 1 |
| `.claude/skills/industrial-data-processor/scripts/` | `convert.mjs` | 1 |
| `.hermes/skills/industrial-deep-diagnostic/scripts/` | `validate.mjs`, `append-pipeline-event.mjs`, `uv_env_setup.mjs` | 3 |
| `.agents/skills/industrial-deep-diagnostic/scripts/` | `validate.mjs`, `append-pipeline-event.mjs`, `uv_env_setup.mjs`, `convert.mjs` | 4 |
| `.hermes/` | **整个目录标记 deprecated**（添加 `DEPRECATED.md`） | 1 |

**执行清单**:
- [ ] `grep -r "\.hermes/" --include="*.{mjs,js,py,md}" .claude/ .omp/` → 确认无硬编码引用
- [ ] `grep -r "\.agents/skills/" --include="*.{mjs,js,py,md}" .claude/ .omp/` → 确认引用路径
- [ ] 删除上述 schema 文件
- [ ] 删除上述重复脚本文件
- [ ] 在 `.hermes/` 根创建 `DEPRECATED.md`（说明：schema 和脚本引用迁移到 shared/）
- [ ] 不删除 `.hermes/` 的非 schema/非脚本文件（agents 定义、config 等仍可能被引用）

#### Phase A 验收门

```bash
# Gate A1: shared/ 目录完整性
test -d .claude/shared/schemas && test -d .claude/shared/scripts
test -f .claude/shared/scripts/validate.mjs
test -f .claude/shared/scripts/append-pipeline-event.mjs

# Gate A2: 旧路径无残留（关键路径检查）
! grep -r "skills/industrial-data-processor/scripts/validate.mjs" .omp/ .claude/skills/*/SKILL.md 2>/dev/null

# Gate A3: 新路径存在（抽样验证）
grep -q "SHARED_PATH/scripts/validate.mjs" .omp/skills/industrial-data-processor/SKILL.md

# Gate A4: 无 .hermes/ schemas 残留
test ! -d .hermes/skills/industrial-deep-diagnostic/schemas

# Gate A5: Full pipeline smoke test
# 使用 examples/reactor_temperature 样例数据跑完整 pipeline
```

---

### Phase B: Agent Protocol 精简（P1）

> **依赖 Phase A**：agent 需要 SHARED_PATH 来引用 shared 脚本。可与 Phase A 部分并行（A1-A2 完成后即可开始）。

#### Step B1: 提取通用参考材料到 resources/

对 data-processor 和 diagnostician（最重的两个）创建以下独立文件：

| 新文件 | 来源 | 内容 | 大小 |
|:-------|:-----|:-----|:----:|
| `data-processor/resources/execution_reference.md` | agent-protocol.md 的 bash 命令段 | 所有 dp_toolkit/stats/stats_validate 的完整命令、参数表 | ~15KB |
| `data-processor/resources/anti_spurious_rules.md` | agent-protocol.md 的 v6.4-v6.7 段 | Simpson/去趋势/时滞/批次/留一法规则 | ~10KB |
| `diagnostician/resources/execution_reference.md` | agent-protocol.md 的 Phase 详细说明 | 每个 Phase 的详细操作、输出 schema 说明 | ~8KB |

**执行清单**:
- [ ] 从 `data-processor/references/agent-protocol.md` 提取 bash 命令段 → `resources/execution_reference.md`
- [ ] 从 `data-processor/references/agent-protocol.md` 提取 v6.4-v6.7 段 → `resources/anti_spurious_rules.md`
- [ ] 从 `diagnostician/references/agent-protocol.md` 提取详细 Phase 说明 → `resources/execution_reference.md`

#### Step B2: 重写 agent-protocol.md 为检查清单格式

**目标格式（每个 protocol 适用）**:

```markdown
# [Agent Name] — Execution Checklist

## Parameters
- RUN_DIR, SKILL_PATH, SHARED_PATH, DATA_PATH

## Phase 0: [名称]
- [ ] Read: [文件列表]
- [ ] Verify: [验收条件]
- [ ] Write: [输出文件]
- Gate: [CP 条件]
→ 如需详细命令: read resources/execution_reference.md#phase-0

## Phase 1: [名称]
...
## Output Verification
- [ ] node "$SHARED_PATH/scripts/validate.mjs" "<schema>" "<output>"

## On-Demand References
| 场景 | 读取 |
|:-----|:-----|
| 需要精确 bash 命令 | resources/execution_reference.md |
| |r|≥0.3 相关出现 | resources/anti_spurious_rules.md |
| 物理推断不确定 | resources/physics_inference_framework.md |
| 证据等级不确定 | resources/evidence_rules.md |
```

**执行清单（按 skill 逐个重写）**:

| Skill | 当前大小 | 目标大小 | 签字 |
|:------|:------:|:------:|:---:|
| data-processor | 84,424B | ~8,000B | [ ] |
| diagnostician | 67,878B | ~7,000B | [ ] |
| ontology-builder | 40,119B | ~6,000B | [ ] |
| physical-auditor | 33,318B | ~5,000B | [ ] |
| reporter | 32,140B | ~5,000B | [ ] |
| judge | 29,745B | ~5,000B | [ ] |
| html-visualizer | 7,094B | ~3,000B | [ ] |
| vlm-analyzer | 6,537B | ~2,500B | [ ] |
| html-reviewer | 4,768B | ~2,000B | [ ] |

#### Step B3: 更新 .omp/agents/*.md 的初始化段

当前每个 `.omp/agents/<name>.md` 的初始化段列出要读取的资源文件。修改为：

```markdown
## 初始化
1. Read `${SKILL_PATH}/references/agent-protocol.md` — 执行检查清单
2. 按需读取 on-demand references（见检查清单底部的引用表）
```

**执行清单**:
- [ ] 更新 9 个 `.omp/agents/*.md` 的初始化段
- [ ] 确保每个 agent 的 "补充指导" 段包含 on-demand 引用提示

#### Phase B 验收门

```bash
# Gate B1: 所有 protocol 文件大小在目标范围内
for f in .claude/skills/*/references/agent-protocol.md; do
  size=$(wc -c < "$f")
  echo "$size $f"
done

# Gate B2: 所有 protocol 包含 "On-Demand References" 段
grep -l "On-Demand References" .claude/skills/*/references/agent-protocol.md | wc -l
# 期望: 7 (html-visualizer 和 html-reviewer 协议较短，可选)

# Gate B3: 提取的参考文件存在
test -f .claude/skills/industrial-data-processor/resources/execution_reference.md
test -f .claude/skills/industrial-data-processor/resources/anti_spurious_rules.md

# Gate B4: Full pipeline 输出质量不下降
# 跑 examples/reactor_temperature → 对比 Phase A 基线的 diagnosis.json + report.md
```

---

### Phase C: 结构性合并（P2, P3, P4）

> **依赖 Phase B**：agent protocol 需先精简，为新增/合并的 Phase 腾空间。

#### Step C1: P2 — VLM Analyzer 合并到 Data Processor

**文件操作清单**:

| 操作 | 文件 | 说明 |
|:-----|:-----|:-----|
| MOVE | `industrial-vlm-analyzer/scripts/visual_analysis.py` → `industrial-data-processor/scripts/visual_analysis.py` | VLM 分析脚本 |
| MOVE | `industrial-vlm-analyzer/scripts/vlm-verification-check.mjs` → `industrial-data-processor/scripts/vlm-verification-check.mjs` | VLM 防伪造验证 |
| MERGE | `industrial-vlm-analyzer/references/agent-protocol.md` 内容 → `industrial-data-processor/references/agent-protocol.md` 新 Phase 5.5 | VLM 协议合并 |
| DELETE | `.omp/skills/industrial-vlm-analyzer/SKILL.md` | 删除独立 skill |
| DELETE | `.omp/agents/vlm-visual-analyzer.md` | 删除独立 agent |
| DELETE | `.claude/skills/industrial-vlm-analyzer/` | 删除整个 skill 目录 |
| DELETE | `.hermes/agents/vlm-visual-analyzer.md` | 删除 hermes 副本 |
| UPDATE | `.omp/skills/industrial-analysis-auto/SKILL.md` | 移除 Step 3.5，将 VLM 合并到 Step 3 描述 |
| UPDATE | `.omp/skills/industrial-data-processor/SKILL.md` | 添加 Phase 5.5 VLM 描述 |

**data-processor protocol 新增 Phase 5.5**:
```markdown
## Phase 5.5: VLM Visual Analysis (optional, auto-degrade)
- [ ] If VLM_ENABLED=true: run python visual_analysis.py
- [ ] Else: write visual_analysis.json as metadata-only skeleton
- [ ] Run: node vlm-verification-check.mjs (if VLM was used)
- Gate: visual_analysis.json exists (metadata or VLM-enriched)
→ 详见: resources/execution_reference.md#phase-5.5
```

**执行清单**:
- [ ] 确认 `visual_analysis.py` 中所有路径引用指向 `$RUN_DIR`（不依赖 skill 目录路径）
- [ ] 执行文件移动和删除
- [ ] 更新 orchestrator SKILL.md：移除 Step 3.5，Step 3 描述中加入 "含 VLM 视觉分析（metadata-first，按需 VLM API）"
- [ ] 更新 pipeline flow 图：移除 Step 3.5
- [ ] 更新 Checkpoint Gates：移除 VLM 相关 gate（原无 CP gate for 3.5）

#### Step C2: P3a — 统一统计管线

**文件操作清单**:

| 操作 | 文件 | 说明 |
|:-----|:-----|:-----|
| CREATE | `industrial-data-processor/scripts/stats/__init__.py` | 包初始化 |
| CREATE | `industrial-data-processor/scripts/stats/run.py` | 统一入口 |
| CREATE | `industrial-data-processor/scripts/stats/core_stats.py` | Pearson/Spearman/去趋势/CCF |
| CREATE | `industrial-data-processor/scripts/stats/anti_spurious.py` | Simpson/离群/留一法/变点 |
| CREATE | `industrial-data-processor/scripts/stats/batch_integrity.py` | 批次唯一性验证 |
| DELETE | `industrial-data-processor/scripts/stats.mjs` | 功能被 core_stats.py 覆盖 |
| DELETE | `industrial-data-processor/scripts/stats_validate.mjs` | 功能被 anti_spurious.py 覆盖 |
| DELETE | `industrial-data-processor/scripts/stats_analysis.py` | 功能被 core_stats.py + anti_spurious.py 覆盖 |
| DELETE | `.hermes/.../scripts/stats.mjs`, `stats_validate.mjs`, `stats_analysis.py` | hermes 副本 |
| DELETE | `.agents/.../scripts/stats.mjs`, `stats_validate.mjs`, `stats_analysis.py` | agents 副本 |
| UPDATE | `data-processor/references/agent-protocol.md` | Phase 2 改为调用 `stats/run.py` |
| UPDATE | `data-processor/resources/execution_reference.md` | 更新 stats 命令 |

**run.py 接口约定**:
```python
# 用法: python stats/run.py --run-dir <RUN_DIR> [--mode full|correlation|spurious|batch]
# 输入: RUN_DIR/02_processed/cleaned_data.json
# 输出: RUN_DIR/02_processed/validate_report.json
```

**执行清单**:
- [ ] 实现 core_stats.py（从 stats_analysis.py 移植 Pearson/Spearman/去趋势/CCF + 从 stats.mjs 移植基础统计）
- [ ] 实现 anti_spurious.py（从 stats_validate.mjs 移植 Simpson/离群/留一法/变点逻辑）
- [ ] 实现 batch_integrity.py（从 cleaning_integrity_check.py 移植批次验证）
- [ ] 实现 run.py（统一入口，按 mode 参数分发）
- [ ] 回归测试：旧脚本输出 vs 新管线输出 → 数值一致性验证

#### Step C3: P3c — Post-processing 合并

**文件操作清单**:

| 操作 | 文件 | 说明 |
|:-----|:-----|:-----|
| CREATE | `industrial-data-processor/scripts/data-processor-finalize.mjs` | 合并 normalize + synthesize |
| DELETE | `industrial-data-processor/scripts/normalize-anomaly-report.mjs` | — |
| DELETE | `industrial-data-processor/scripts/synthesize-data-analysis-conclusion.mjs` | — |
| DELETE | `.hermes/.../scripts/normalize-anomaly-report.mjs` | hermes 副本 |
| DELETE | `.hermes/.../scripts/synthesize-data-analysis-conclusion.mjs` | hermes 副本 |
| DELETE | `.agents/.../scripts/normalize-anomaly-report.mjs` | agents 副本 |
| DELETE | `.agents/.../scripts/synthesize-data-analysis-conclusion.mjs` | agents 副本 |
| UPDATE | `data-processor/references/agent-protocol.md` | Phase 6 改为调用 data-processor-finalize.mjs |
| UPDATE | `industrial-analysis-auto/SKILL.md` | Step 3 post-processing 段更新 |

#### Step C4: P4 — Finalize 阶段合并

**文件操作清单**:

| 操作 | 文件 | 说明 |
|:-----|:-----|:-----|
| CREATE | `industrial-analysis-auto/scripts/pipeline-finalize.mjs` | 合并 3 个脚本 |
| DELETE | `industrial-analysis-auto/scripts/evidence-closure-check.mjs` | — |
| DELETE | `industrial-analysis-auto/scripts/artifact-check.mjs` | — |
| DELETE | `industrial-analysis-auto/scripts/finalize-run-artifacts.mjs` | — |
| DELETE | `.hermes/.../scripts/evidence-closure-check.mjs` | hermes 副本 |
| DELETE | `.hermes/.../scripts/artifact-check.mjs` | hermes 副本 |
| DELETE | `.hermes/.../scripts/finalize-run-artifacts.mjs` | hermes 副本 |
| DELETE | `.agents/.../scripts/evidence-closure-check.mjs` | agents 副本 |
| DELETE | `.agents/.../scripts/artifact-check.mjs` | agents 副本 |
| DELETE | `.agents/.../scripts/finalize-run-artifacts.mjs` | agents 副本 |
| UPDATE | `industrial-analysis-auto/SKILL.md` | Step 9 改为单个 bash 调用 |

**pipeline-finalize.mjs 接口约定**:
```bash
# 用法
node "$SHARED_PATH/../skills/industrial-analysis-auto/scripts/pipeline-finalize.mjs" "$RUN_DIR"

# 内部顺序执行 5 个步骤
# Step 1: 产物清单（45 项核心检查）
# Step 2: 批量 Schema 验证
# Step 3: 证据闭合检查（4 项闭合规则）
# Step 4: Judge Gate 交叉审计
# Step 5: 管道事件归档 + pipeline-log-check
```

**执行清单**:
- [ ] 从 3 个脚本提取所有检查项 → 合并去重 → 列表（确认恰好 45 项）
- [ ] 实现 pipeline-finalize.mjs
- [ ] 更新 orchestrator SKILL.md 的 Step 9

#### Phase C 验收门

```bash
# Gate C1: VLM 相关文件清理
test ! -d .omp/skills/industrial-vlm-analyzer
test ! -f .omp/agents/vlm-visual-analyzer.md
test -f .claude/skills/industrial-data-processor/scripts/visual_analysis.py

# Gate C2: 统计管线新结构
test -f .claude/skills/industrial-data-processor/scripts/stats/run.py
test ! -f .claude/skills/industrial-data-processor/scripts/stats.mjs
test ! -f .claude/skills/industrial-data-processor/scripts/stats_validate.mjs

# Gate C3: Post-processing 合并
test -f .claude/skills/industrial-data-processor/scripts/data-processor-finalize.mjs
test ! -f .claude/skills/industrial-data-processor/scripts/normalize-anomaly-report.mjs

# Gate C4: Finalize 合并
test -f .claude/skills/industrial-analysis-auto/scripts/pipeline-finalize.mjs
test ! -f .claude/skills/industrial-analysis-auto/scripts/evidence-closure-check.mjs

# Gate C5: Full pipeline end-to-end（最关键验收）
# 输出: report.md + diagnostic-report.html 内容与 Phase A 基线一致
```

---

### Phase D: 文档精简（P5, P6, P7）

> **独立于 Phase A/B/C**。可在任何阶段执行。

#### Step D1: P5 — 编排器 SKILL.md 精简

**文件**: `.omp/skills/industrial-analysis-auto/SKILL.md`
**变更**: 320 行 → ~150 行

- [ ] bash 命令示例合并为 1 个通用模板
- [ ] Red-Light Blacklist 移到 `resources/red_light_blacklist.md`
- [ ] 合并重复的 Checkpoint Gates 表格
- [ ] 保留: Pipeline Flow 图、Sub-Skill Map、Repair Governance、Path Stability

#### Step D2: P6 — rag-knowledge-builder 职责澄清

**变更**: 0 文件操作

- [ ] 在 `industrial-ontology-builder/SKILL.md` 的 Agent prompt 中加入明确声明：
  "优先使用内置 RAG 协议（resources/rag_deep_understanding_protocol.md）。仅在用户显式指定或内置 RAG 不可用时 fallback 到 rag-knowledge-builder skill。"
- [ ] 确认 `parameter_to_physics.json` 在两边各存一份不构成维护问题（都从同一个上游生成）

#### Step D3: P7 — HTML skill 关系澄清

**文件**: `.omp/skills/industrial-html-visualizer/SKILL.md`
**变更**: 198 行 → ~85 行

- [ ] 移除 "runtime readiness" 段（已在 diagnostic-html-visualizer 中定义）
- [ ] 移除 "visual standards" 段（同上）
- [ ] 保留: Inputs、Outputs、Execution（管线约束）、HTML Opt-Out、Verification

#### Phase D 验收门

```bash
# Gate D1: 编排器 SKILL.md 精简
test $(wc -l < .omp/skills/industrial-analysis-auto/SKILL.md) -le 180

# Gate D2: HTML skill 精简
test $(wc -l < .omp/skills/industrial-html-visualizer/SKILL.md) -le 100
```

---

## 二、执行顺序（严格依赖图）

```
Phase A: Foundation (P0)
  ├── A1: 创建 shared/          ← 无依赖
  ├── A2: 注入 SHARED_PATH      ← 依赖 A1
  ├── A3: 迁移硬引用            ← 依赖 A2
  └── A4: 删除冗余文件           ← 依赖 A3
       ↓
Phase B: Protocol (P1)
  ├── B1: 提取参考材料           ← 依赖 Phase A 完成
  ├── B2: 重写 protocol          ← 依赖 B1
  └── B3: 更新 agent 初始化      ← 依赖 B2
       ↓
Phase C: Structural (P2+P3+P4)
  ├── C1: VLM 合并 (P2)         ← 依赖 B2 (data-processor protocol ready)
  ├── C2: 统计合并 (P3a)        ← 依赖 Phase A (shared scripts)
  ├── C3: Post-process 合并 (P3c) ← 依赖 B2
  └── C4: Finalize 合并 (P4)    ← 依赖 Phase A
       ↓
Phase D: Documentation (P5+P6+P7) ← 任意时间
```

**可并行执行**:
- Phase B 和 Phase C 的准备工作（C2/C3/C4 的新脚本编写）可在 Phase A 完成后并行
- Phase D 全程独立

---

## 三、简洁效果预估

| 指标 | 当前 | 优化后 | 变化 |
|:----:|:----:|:------:|:----:|
| 总代码行数 | 140,344 | ~105,000 | **-25%** |
| 脚本文件数 | 51 | ~28 | **-45%** |
| Schema 副本 | 46/3 目录 | 16/1 目录 | **-65%** |
| Agent Protocol 总体积 | 306KB | ~45KB | **-85%** |
| Agent 启动 token | 60K-120K | 10K-20K | **-83%** |
| 重复脚本实例 | 18 | 0 | **-100%** |
| Pipeline 步骤 | 12 | 11 | -1 |
| Skill 数量 | 12 | 11 | -1 |

---

## 四、不变的核心设计

- ✅ 诊断管线架构（Step 0-9）
- ✅ Checkpoint Gate 系统（CP-1 到 CP-9）
- ✅ Agent 委派模式
- ✅ 数据/物理双驱动
- ✅ 反假相关 v6.4-v6.7（移到 on-demand 加载）
- ✅ Repair Governance（Best-of-3 + 全局上限 5）
- ✅ Agent 隔离通信
- ✅ 诊断 = 排除而非确认

---

## 五、风险矩阵

| 风险 | 等级 | 缓解措施 | 回退方案 |
|:-----|:----:|:---------|:--------|
| `validate.mjs` 引用更新遗漏 | 中 | 全局 grep + 每 Phase 验收门自动检测 | git revert |
| Agent protocol 过度精简导致输出质量下降 | 中 | Phase B 验收门跑对比测试 | 保留旧 protocol 在 `references/agent-protocol-full.md` |
| 统计管线合并引入数值漂移 | 中 | C2 回归测试逐算法对比 | 保留旧脚本目录作为参考 |
| `.hermes/` 被外部系统依赖 | 高 | A4 仅删除 schemas + 重复脚本，不删 agents/config | 完整保留 .hermes/ 仅标记 deprecated |
| 合并后 script 路径硬编码残留 | 低 | Phase A 验收门 grep 检查 | 逐个文件修复 |

---

## 六、版本记录

| 版本 | 日期 | 变更 |
|:-----|:-----|:-----|
| v1 | — | 初版（5 项优化 + 3 项算法增强） |
| v2 | 2026-07-28 | 基于源码审计修正（7 项优化，新增 P0/P5-P7） |
| v3 | 2026-07-28 | 自审计修正：精确文件清单、blast radius 核算（~34 硬依赖）、严格依赖顺序、每 Phase 验收门、风险回退方案 |
