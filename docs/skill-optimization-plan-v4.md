# Industrial Deep Diagnostic — 技能系统优化计划 v4

> 主题：**本体资产化复用 + 全链路提速 + 普通诊断/增强诊断（E0-E8）意图驱动一体化**
> 基线：v3 已落地的 shared/ 基础设施 + uv 优先 Python 执行 + 双 harness（claude / omp）真实集成
> 撰写日期：2026-09-07（基于真实运行实测数据，非推测）

---

## 零、实测瓶颈证据（不可变基线）

### 0.1 实测运行时间线（run `63480d72`，scene `data`，数据 `eval_cnc_spindle_wear/data.csv` 1050 行 × 14 列，OMP 引擎，maxTurns=20）

| 阶段 | 时间窗 | 耗时 | 占比 | 备注 |
|------|--------|------|-----|------|
| 会话启动 + 读 SKILL.md | 17:03:41 → 17:04:55 | ~1.2 min | 6% | SKILL.md 全文被读两次 |
| Step 0/1 setup + inspect | 17:04:55 → 17:06:48 | ~2 min | 10% | 含一次 `cd /d` Windows 失败重试（+43s） |
| 描述统计（内联） | 17:06:48 → 17:08:09 | ~1.3 min | 6% | |
| **本体构建（Step 2）** | 17:08:09 → 17:23:42 | **~15.6 min** | **76%** | 见下分解 |
| 收尾 | 17:23:42 → 17:24:18 | ~0.6 min | 3% | |

**本体阶段 15.6 分钟的分解**：

| 子阶段 | 耗时 | 说明 |
|--------|------|------|
| OntologyBuild 子代理执行 | **11.5 min** | 17:08:09 派发 → 17:19:37 **以失败告终，产出为零**（write 步骤目录错误） |
| 主代理 hub wait 串行阻塞 | 12 min（含在前者内） | 180s + 240s + 300s 三次串行等待，期间完全空转 |
| 主代理读 transcript + 3 次读 schema | ~3 min | 失败后排查 |
| 主代理手写 minimal ontology | ~1 min | 按 agent-protocol.md L102 兜底协议执行，产物 7.7KB 通过 CP-2 |

> **结论：本场景 76% 的墙钟时间消耗在"每次从零构建本体"上，其中绝大部分又是子代理失败后的无效等待。** 本体复用 + 失败快速止损是收益最大的两项优化，实测可把单次运行从 ~21 min 压到 **≤ 6 min（复用命中时 ≤ 3 min）**。

### 0.2 结构性问题清单（按 skill 逐一核实）

| # | 位置 | 问题 | 类型 |
|---|------|------|------|
| P1 | 全局 | **本体零复用**：每次运行全量重建 `ontology.json`，无任何指纹/缓存/注册表 | 结构性 |
| P2 | ontology-builder 子代理 | write 步骤目录错误导致 11.5 min 全废（疑与 OMP task 子代理的 cwd/相对路径有关），且主代理 hub wait 最长可阻塞 12 min 才止损 | 缺陷+策略 |
| P3 | orchestration | Step 2（本体）与 Step 0.5-1 的数据剖析完全串行，但数据剖析（格式/质量/统计画像）并不依赖本体语义 | 编排 |
| P4 | diagnostician 修复循环 | best-of-3 每轮全量重算 4 个诊断 JSON，而 judge 的 repair_instructions 通常只涉及 1-2 个维度 | 策略 |
| P5 | judge/auditor | 每轮修复后 Judge 从零重读全部 9 个产物 | 策略 |
| P6 | setup | `cd /d`（cmd 语法）在 POSIX bash 下失败重试；skill 未声明 shell 兼容约定 | 缺陷 |
| P7 | enhance-auto | **增强管线无法从普通诊断自动衔接**：基线管线 Step 0-9 从不调用 E0-E8；后端无任何 `POST /enhance` API；只能手动 CLI 或在提示词里碰运气 | 集成缺失 |
| P8 | enhance-auto / web_search | RAG 不可达时 fallback 正确，但探测与 web 搜索（最多 5 次 × 15s）在不可控网络下拖慢本体构建 | 策略 |
| P9 | 数据契约 | `.pipeline_events.jsonl` 事件稀疏（实测仅 2 条），无法做步骤级 profiling | 可观测性 |

### 0.3 已经很好、不要动的设计

- E1-E6 增强阶段**全部是确定性 Python 脚本（零 LLM）**，且已有 mtime skip（`enhance_orchestrator.mjs` L93-101）——增强管线本身很快，缺的只是"触发衔接"。
- Step 5a/5b 已并行；修复治理（best-of-3、全局上限 5、反振荡）健全。
- VLM 阶段已限定 2 张强制图 + manifest 过滤。
- `parameter_to_physics.json` 兜底库与 RAG `/accumulate` 知识积累接口已存在，可直接作为本体资产的底座。

---

## 一、优化总架构：三层一体

```
L1 本体资产化（Ontology Store）        ← 最大收益：单次省 76% 墙钟
L2 全链路提速（每步精修）              ← 叠加收益：再省 20-40%
L3 增强诊断意图集成（auto/深度/普通）   ← 产品完整性：用户一句话决定深度
```

设计原则（对齐 v3 审计基线）：
1. **脚本能做的绝不进 LLM**；LLM 只做语义判断。
2. 所有优化通过 **prompt/runtime-protocol 与 run_config 贯通**，claude 与 omp 双 harness 无差别生效。
3. 产物契约不破坏：`ontology.json` schema（v6.4）、CP 检查点命令、`enhancement/` 目录结构保持向后兼容。

---

## 二、L1 本体资产化：Ontology Store（核心，Phase A）

### A1. 存储设计

新增项目级资产目录（不属于任何 run）：

```
data/ontology_store/
├── index.json                      # 注册表
└── <scene_key>/                    # 如 eval_cnc_spindle_wear
    └── v3/                         # 版本递增
        ├── ontology.json           # 与 ontology_schema.json v6.4 兼容
        ├── provenance.json         # 溯源（见下）
        └── attachments/            # rag_deep_understanding.json 等附属产物（可选）
```

`index.json` 结构：

```json
{
  "version": 1,
  "entries": [
    {
      "scene_key": "eval_cnc_spindle_wear",
      "version": 3,
      "schema_fp": "sha256:<列名+列序+dtype 的规范哈希>",
      "content_fp": "sha256:<采样内容哈希，可选>",
      "build_mode": "full|extend",
      "built_from_run": "202609061704559_data",
      "created_at": "...",
      "reuse_count": 7,
      "quality": "endorsed|unvalidated|challenged",
      "path": "eval_cnc_spindle_wear/v3/ontology.json"
    }
  ]
}
```

`provenance.json`：来源 run、构建模式、数据文件指纹、RAG/引用调用计数、CP-2 校验时间、后续每次 reuse 的 run_id 列表。

**指纹定义（关键决策）**：
- `schema_fp` = sha256(规范化 JSON of `[ {column, dtype, position} ]`)，由脚本对数据文件前 N=1000 行推断 dtype 生成。**同 schema 即视为"同一数据场景"**。
- `content_fp` = sha256(文件大小 + 首/中/尾各 100 行内容哈希)。用于同 schema 不同批次时提示"建议 extend 校验"。
- 匹配三级：`exact`（schema_fp 全等 → 可直接 reuse）→ `superset/subset`（列集合差异非空 → 走 extend）→ `miss`（full）。

### A2. 新共享脚本 `.claude/shared/scripts/ontology_store.mjs`

零依赖（对齐 validate.mjs 风格），子命令：

```
node .claude/shared/scripts/ontology_store.mjs fingerprint <data.csv>   # 输出 {schema_fp, content_fp, columns[]}
node .claude/shared/scripts/ontology_store.mjs find <data.csv> [--scene <key>] [--schema-fp <fp>]
    # → {match: exact|extend|miss, ontology_path?, scene_key, version, provenance_path?}
node .claude/shared/scripts/ontology_store.mjs publish --run-dir <RUN_DIR> [--scene <key>] [--build-mode full|extend]
    # CP-2 通过后调用：校验 run 目录 ontology.json ≥1KB 且 schema-valid → 拷贝入 store → 写 index/provenance → 输出 scene_key/version
node .claude/shared/scripts/ontology_store.mjs reuse --source <store_path> --run-dir <RUN_DIR>
    # 复用命中时：拷贝 ontology.json 到 run 目录 → 写 reuse 事件到 .pipeline_events.jsonl
node .claude/shared/scripts/ontology_store.mjs stats                    # 列表 + 命中率统计
```

### A3. Skill 协议改造：ontology-builder 增加 Phase -1（模式分派）

`run_config.json` 新增字段（由后端注入，见 A5）：

```json
"ontology": { "mode": "auto|full|reuse|extend", "source": "<store path 或 旧 run dir 路径，可选>" }
```

`industrial-ontology-builder/references/agent-protocol.md` 在 Phase 0 之前插入：

```
## Phase -1: Ontology Mode Dispatch (deterministic, ≤30s)
1. Read $RUN_DIR/00_input/run_config.json → ontology.mode
2. mode == reuse:
   a. bash: ontology_store.mjs reuse --source <source> --run-dir $RUN_DIR
   b. Run CP-2 (schema validate + ≥1KB) — 不得跳过
   c. Run CP-3 clarification（沿用本次 run 的 clarification_needed.json）
   d. Write reuse event；直接进入 Phase 5 输出校验并结束。禁止调用 RAG / web_search / references 检索。
3. mode == extend:
   a. fingerprint 本次数据 → 与 source 本体 diff 列集合
   b. 仅对「新增列 / 角色未定列」执行 Phase 1-4（检索范围限定在 diff 列）
   c. 合并进存量本体：新增 signals/relationships；被新数据证伪的 normal_range/behavior 需更新
     并把 behavior_match 置 CONTRADICTED + knowledge_source=auto_inferred
   d. version bump（provenance 记录 parent version + diff 摘要）→ Phase 5
4. mode == full 或 auto 且 find 结果为 miss：现行 Phase 0-5 全流程
5. 所有模式收尾后执行：ontology_store.mjs publish --run-dir $RUN_DIR（CP-2 已过为前提）
```

同步修改：
- `SKILL.md` 执行流表加入 Phase -1 行（模式分派表）。
- **编排器** `industrial-analysis-auto/SKILL.md` Step 2 增加一行：派发 prompt 中必须透传 `ONTOLOGY_MODE/ONTOLOGY_SOURCE`（来自 run_config），并在 CP-2 通过后追加 publish 命令。
- 兜底协议（agent-protocol L95-102）追加一条：主代理手写 minimal ontology 后同样执行 publish（build_mode=full, quality=unvalidated）——实测运行里主代理兜底写的本体因此自动入库，下次同场景即可命中。

### A4. 失败止损（针对 P2，与 A3 同步落地）

1. **hub wait 上限治理**：编排器 Step 2 增加规则——子代理累计等待超过 **8 min** 仍未产出 `01_ontology/ontology.json` → 立即 abort 子代理任务，转主代理本地脚本构建（读取 `parameter_to_physics.json` + schema，≤3 min），不再 180s+240s+300s 串行等满。
2. **子代理 write 失败根因修复**：在 dispatch prompt 中强制要求子代理使用 run_dir 的**绝对路径**写文件（编排器 dispatch 模板已带 RUN_DIR 绝对路径，但需在 context-builder 的 agent-protocol Phase 5 加一句「所有 write 使用 prompt 给出的绝对路径，禁止相对路径」）；修复后在 `.omp/agents/context-builder.md` 的初始化段同步声明。此项落地后用「单场景 full 构建」回归验证子代理成功率。
3. **事件密度**：编排器要求每个 step 写 `step_start` / `step_complete` 事件（append-pipeline-event.mjs 已有，补调用点），修复 P9 可观测性。

### A5. 后端/API/前端贯通

| 层 | 改动 |
|----|------|
| `config/default.yaml` | 新增 `ontology.store_dir: "data/ontology_store"`、`ontology.default_mode: "auto"`、`ontology.subagent_wait_cap_seconds: 480` |
| `diagnosis.service.mjs` | `createDiagnosisRun` 接受 `ontologyMode`（`auto|full|reuse|extend`）与 `ontologySource`；写入 run_config（Step 0 setup.mjs 生成 `00_input/run_config.json` 时透传）；run 行新增 `ontology_hit`（null/reused/extended/built）+ `ontology_version`（meta 即可） |
| `claude-client.mjs` / `omp-client.mjs` | `buildRuntimeProtocol` 增加第 9 条规则：`9. Ontology asset policy: honor run_config.ontology.mode — reuse 命中时禁止重建，extend 时仅对 diff 列做增量检索；CP-2 校验在任何模式下都不可跳过。`（两引擎共享同一函数，天然一致） |
| `DiagnosisView.vue` | "开始诊断"卡片增加**本体来源**选择：`自动（推荐）` / `强制重建` / `复用指定场景`（下拉列出 store 中已有 scene_key，来自新 API） |
| 新 API | `GET /api/ontology/store`（列出 index）；`GET /api/ontology/store/:scene`（版本+provenance）；挂在 diagnosis routes 同级 |
| History 页 | run 记录显示 `本体: 复用v3 / 增量v4 / 新建` 徽标 + 本体阶段耗时 |

### A6. 质量治理（防止复用污染诊断）

- **CP-2 永不跳过**：reuse 只是跳过"构建"，不跳过"校验"。schema 校验 + ≥1KB + clarification 状态三者照旧。
- **角色漂移防护**：extend 合并时，已有 `role=target/confounder` 的信号不允许被自动改角色；如冲突，写 `clarification_needed.json` 走 CP-3。
- **质量标记**：`quality=endorsed`（该本体参与的 run 获得 Judge ≥90 或 optimizer ENDORSED 时自动升级，由 Step 7/9 finalize 时回写 index）/ `unvalidated`（新建未参与过诊断）/ `challenged`（审计挑战成功，降权并在 reuse 时提示）。
- **用户兜底**：任何模式下用户可 force_full；store 提供 `deprecate` 子命令。
- **保留策略**：每 scene 保留最近 10 版 + 所有 endorsed 版。

### A7. 验收门（Phase A）

```bash
# Gate A1: 脚本与目录
node .claude/shared/scripts/ontology_store.mjs stats   # 正常输出空/已有注册表
# Gate A2: 指纹稳定性（同文件两次指纹一致）
fp1=$(node .../ontology_store.mjs fingerprint data/eval_cnc_spindle_wear/data.csv | jq -r .schema_fp)
fp2=$(node .../ontology_store.mjs fingerprint data/eval_cnc_spindle_wear/data.csv | jq -r .schema_fp)
test "$fp1" = "$fp2"
# Gate A3: full 构建 → publish 入库
# （跑一次单场景诊断，CP-2 后查询）node .../ontology_store.mjs stats | grep eval_cnc_spindle_wear
# Gate A4: reuse 命中端到端
# 第二次同场景诊断：run_config.ontology.mode=auto → 事件流出现 ontology_reused，
# 且 17:03→完成 总时长 ≤ 6 min（对比基线 20.6 min），01_ontology/ontology.json 与 store 版本 sha256 一致
# Gate A5: extend 路径
# 给同 schema 数据加一列新参数 → mode=auto → 事件流出现 ontology_extended，diff 列走检索，
# CP-2 通过，store 出现 v+1 版本且 provenance 记录 parent_version
# Gate A6: 双 harness 一致性
# claude 与 omp 各跑一次 reuse 命中场景，两者事件流均出现 ontology_reused
```

**预期收益**：复用命中场景本体阶段 15.6 min → **≤0.5 min**；单场景首次 full 构建因止损治理（wait cap + write 修复）从 16 min → **6-8 min**。迭代调参类重复诊断（最常见工作流）整体时长 **~21 min → ~5-6 min**。

---

## 三、L2 全链路提速（Phase B）

> 按"改动 → 文件 → 验收"给每个优化点，均为独立可回滚的小步。

### B1. Step 2（本体）与 Step 0.5-1（数据剖析）并行【编排级，最大项】

- 现状：inspect → 本体 → data-processor 全串行；数据剖析实际不依赖本体。
- 改动：编排器 Step 1 完成后**同时**派发两个子任务：
  - `context-builder`（本体，按 A3 模式分派）
  - `data-processor` 的 **Phase 0-1 前置段**（探查/场景分类/生产状态识别，产出 `pre_profile.json`，明确标注"语义解释留待本体 ready"）
  - 本体 ready 后 data-processor 从 Phase 2 起接续（读 pre_profile.json 免重复探查）。
- 串行依赖保持的底线：Phase 2+ 的语义分析（discrepancy、R2 校验）仍必须以 ontology 为输入（维持 ontology_first 契约的**语义部分**）。
- 文件：`industrial-analysis-auto/SKILL.md` Step 1-3 编排块、`industrial-data-processor/references/agent-protocol.md`（Phase 0-1 可前置说明 + pre_profile.json 契约）。
- 验收：full 构建场景下本体阶段与数据剖析阶段时间轴重叠（DB 事件流两 agent 活动交叠）且 CP-4 通过；pre_profile.json 存在且被 Phase 2 消费。
- 收益：full 场景再省 2-4 min；reuse 场景收益小（本体已秒级）。

### B2. 修复循环定向化（diagnostician + judge）【策略级】

- 现状：best-of-3 每轮 diagnostician 全量重算 4 个 JSON；judge 每轮全量重审 9 产物。
- 改动：
  - `judge` 产出时把 `blocking_issues` 结构化（dimension → files → instructions），写 `judge_repair_scope.json`。
  - `diagnostician` 增加 `REPAIR_SCOPE` 协议：第 2/3 轮仅允许重算 scope 内文件，未涉及文件从 best_round 快照原样恢复并在 reasoning_chain 标注 `carried_over: true`。
  - `judge` 第 2/3 轮仅复审 scope 内维度 + 上轮 blocking 的复核（首轮已 pass 维度引用上轮结论）。
- 文件：`industrial-judge/SKILL.md`（结构化 scope 输出契约）、`industrial-diagnostician/SKILL.md`（REPAIR_SCOPE 协议）、`industrial-analysis-auto/SKILL.md` 修复循环块（快照/恢复逻辑已有，补 scope 透传）。
- 验收：构造一个 judge 70-89 分 run：第 2 轮修复只重算 scope 文件（事件流可见 carried_over），修复后总分 ≥90，全局轮次计数行为不变。
- 收益：每轮修复省 40-60%（触发修复的运行平均省 3-6 min）。

### B3. RAG/网络快失败【策略级，P8】

- 改动：
  - 编排器 Step 0 增加：`curl -m 3 http://localhost:8764/health` 探测，结果写入 run_config.rag_available；ontology-builder 据此直接选路径（省去执行期反复探测）。
  - web_search 每查询超时 15s → **8s**（`rag-retrieval-engine/config.yaml`），最多 5 次 → 复用模式下 0 次。
  - reuse/extend 模式下 Phase 2（web 研究）默认跳过。
- 文件：`rag-retrieval-engine/config.yaml`、`industrial-analysis-auto/SKILL.md`（探测注入）、ontology-builder agent-protocol（Phase -1/2 关联）。
- 验收：RAG 引擎停止时 full 构建不出现 >30s 的探测挂起；reuse 模式事件流零 web_search 调用。
- 收益：RAG 不可用场景省 1-3 min 空转。

### B4. Windows shell 兼容（P6）

- 改动：`industrial-analysis-auto/SKILL.md` Step 0 增加约定：**所有 bash 命令不得使用 cmd 内建语法（`cd /d`、`dir`）**，跨盘切换直接以绝对路径调用（`node "D:/.../setup.mjs"`），或 `cd "D:/path" && cmd`。
- 同时在 setup.mjs / inspect.mjs 的 README 注释标注 POSIX 路径写法示例。
- 验收：新 run 事件流无 `cd /d` 失败重试。
- 收益：~1 min/次 + 减少无谓 turn 消耗。

### B5. VLM 阶段轻量化（可选）

- `vlm-visual-analyzer` thinkingLevel high → medium（`.omp/agents/vlm-visual-analyzer.md`），只在 SUPPLEMENTARY 图 ≥3 张时维持 high（规则写入 dispatch prompt）。
- 验收：visual_analysis.json 仍通过 vlm-verification-check.mjs，描述质量抽样对比可接受。
- 收益：~0.5-1 min。

### B6. 模型分层与 turn 预算（治理项）

- reuse 模式的本体校验合并若由主代理直接执行（无需派子代理），明确允许用轻量路径（OMP `--smol` 自动生效于子任务）。
- 编排器为每个 Step 声明建议轮次预算（写入 SKILL.md 表格）：Step2 ≤6、Step3 ≤10、Step4 ≤12、5a/5b ≤6、Step6 ≤6、8/8.5 ≤6；超预算触发与 B1 相同的止损检查。预算是"提示性治理"而非硬截断，避免伤及质量。
- 验收：run_summary.json 记录各 step 实际 turns，连续 3 个 run 无 step 超预算 2 倍。

### Phase B 验收门

```bash
# Gate B1: 并行编排 — DB 事件流中 context-builder 与 data-processor 前置段活动时间重叠
# Gate B2: 定向修复 — 构造 70-89 分 run，第 2 轮事件流出现 carried_over 且通过 CP-6
# Gate B3: RAG down 全管线不出现 >30s 挂起（时间线抽查）
# Gate B4: 无 cd /d 重试
# Gate B5(可选): VLM medium 通过反伪造校验
# 综合: 同场景第二次运行（reuse+并行+无修复）端到端 ≤ 5 min（基线 20.6 min）
```

---

## 四、L3 增强诊断意图集成（Phase C，用户核心诉求）

### C1. 意图检测：用户提示词 → 深度增强自动启动

**三态策略**（`enhancement` 字段，默认 `auto`）：

| 值 | 行为 |
|----|------|
| `auto`（默认） | 规则引擎检测 userQuestion：命中深度意图 → 基线完成后自动启动 E0-E8；未命中 → 普通流程，但完成后前端提示"可一键增强" |
| `force_on` | 必定自动启动增强（前端"深度增强诊断"勾选 / API 字段） |
| `force_off` | 禁止（省时省 token） |

**规则引擎（零 LLM 成本，后端实现）** `app/backend/src/utils/enhance-intent.mjs`：

```
强信号（直接 force_on 行为）：深度诊断、深度分析、增强诊断、深挖、根因机理、物理机理验证、
        反事实/条件分析、 association graph、deep dive、enhanced analysis、E0-E8
弱信号（计入置信度，≥2 条才触发）：全面、彻底、完整分析、机理、关联、为什么、how exactly
命中强信号 → enhancement=force_on；弱信号≥2 → auto 触发 + 前端提示可取消（run 启动后 60s 内）
其余 → 普通流程
```

检测结果持久化：`diagnostic_runs` 加列 `enhancement_policy`（auto/on/off）+ `enhancement_triggered`（0/1）——沿用 harness 列的迁移模式。

### C2. 执行链衔接：普通诊断完成 → E0-E8

关键事实（探索已证实）：**E1-E6 全部是确定性脚本，无需 LLM**。所以衔接成本极低，有两种触发路径，推荐 P1 为主、P2 兜底：

**P1（主路径，agent 会话内衔接）**：
- 编排器 `industrial-analysis-auto/SKILL.md` Step 9 后新增 **Step 10（条件步骤）**：
  ```
  ## Step 10: Enhanced Diagnosis (conditional)
  读取 run_config.enhancement（auto 检测结果 / force_on / force_off）。
  - force_off → 跳过。
  - force_on 或 (auto 且 intent_hit=true) →
    bash: node .claude/skills/industrial-analysis-enhance-auto/scripts/enhance_orchestrator.mjs --run-dir "$RUN_DIR"
    （E0 若 BLOCKED → 记录 enhancement_status.json{status:blocked,reason} 并继续收尾，不失败整个 run）
    完成后写 pipeline 事件 step_complete enhance；报告.md 的附录区追加一行
    “深度增强分析已生成：enhancement/enhanced_analysis.md”
  - auto 未命中 → 写事件 enhance_skipped{reason:no_intent}；报告尾部追加一句
    “如需深度增强诊断（E0-E8 关联/机理/权衡分析），可在本运行上直接启动。”
  ```
- runtime-protocol 第 10 条（两引擎同步注入）：`10. Enhancement policy: honor run_config.enhancement as described by the skill protocol; deep-enhancement runs reuse the SAME ontology and run dir, never rebuild baseline.`
- 优势：同一会话、同一 run 目录、执行证明链完整、双 harness 天然一致；OMP 的 enhance-orchestrator agent 定义已存在（Entry B 语义）。

**P2（兜底路径，后端 API 补跑）**：
- 新增 `POST /api/diagnosis/enhance/:runId`：校验 run status=completed 且基线产物齐 → 更新 enhancement_policy=on → 重开一个轻量 agent 会话执行 Mode B 命令（或直接 spawn 脚本进程，产物回写 run 目录 + 事件流）。
- 前端：History/Reports 页对已完成 run 提供「一键深度增强」按钮；Diagnose 页新增三态选择「增强诊断：自动检测（默认）/ 深度增强 / 普通」。
- 该 API 同时服务"run 完成后用户改主意"的场景。

### C3. 与 L1 的完美集成（一体化关键设计）

1. **增强管线消费的本体即资产本体**：E1-E6 读 `01_ontology/ontology.json`，无论是 reuse/extend/full 产出，来源透明（provenance 可查）。复用本体 → 增强阶段零额外语义成本。
2. **知识飞轮**：E6 产物 `enhancement/enhanced_knowledge.json` 中诊断验证过的关系 → 调 RAG `/accumulate`（credibility=accumulated_diag_verified:8 已内置）→ 下次 full/extend 构建时检索质量提升。落地：`enhance_orchestrator.mjs` E8 阶段追加可选步骤（RAG 可达时调用，失败静默跳过）。
3. **本体升级联动**：extend 产生新版本后，历史 run 的增强报告不受影响（各自 run 目录持有当时版本快照）；新 run 自动用最新版。

### C4. 验收门（Phase C）

```bash
# Gate C1: 意图命中 — userQuestion 含“做一次深度诊断，验证物理机理” →
#   DB run 行 enhancement_policy=on；基线完成后事件流出现 step_complete enhance；
#   enhancement/ 目录 9 件套齐全（enhancement_status.json status=completed）
# Gate C2: 意图未命中 — 普通问题 → 事件流出现 enhance_skipped{reason:no_intent}，无 enhancement 目录
# Gate C3: force_off — 即使强信号也不启动
# Gate C4: 一键增强 — 对已完成的普通 run 调 POST /enhance/:runId → 增强产物生成、History 页出现增强徽标
# Gate C5: 双 harness — omp 与 claude 各验证 Gate C1 一次
# Gate C6: 复用联动 — reuse 命中的 run 触发增强，E0 检查通过（本体来自 store 快照）
```

**预期收益**：增强诊断从"需要用户懂 CLI/技能名手动触发"变为"说一句话自动完成"；E0-E8 脚本链本身 ≤3-5 min（无 LLM），叠加复用本体后**深度诊断总增量成本 ≈ 3-5 min**。

---

## 五、落地路线图与工作量

| Phase | 内容 | 规模 | 依赖 | 预期效果 |
|-------|------|------|------|---------|
| **A**（先行，1-2 天） | A1-A7：ontology_store.mjs、Phase -1、publish/reuse、wait-cap 止损、write 路径修复、后端字段+API+前端选择、runtime rule 9 | ~6 个文件新增/修改 + 1 个新脚本 + 3 处 skill 文档 | 无 | 重复场景 **21min → 5-6min（-70%+）** |
| **B**（A 后，1-2 天） | B1 并行剖析、B2 定向修复、B3 快失败、B4 shell 兼容、B5/B6 治理 | 全部为 skill 文档 + 少量脚本参数 | A（B1 依赖 Phase -1 的模式分派） | 首跑再 -20-40%；修复轮 -50% |
| **C**（可与 B 并行，1-2 天） | C1 意图引擎、C2 Step10 + POST /enhance、C3 知识飞轮、前端三态+按钮 | 1 个新 util + 路由 + 编排器 Step10 + 前端两处 | A（复用联动）、基线管线稳定 | 深度诊断一句话直达，增量 ≤5 min |

**总预期**：普通重复诊断 21 min → **≤6 min**；首次 full 21 min → **≤12 min**；深度增强从"独立重跑"变为"同一 run 内 +3-5 min"；token 消耗同步下降（轮次减少 + reuse 零检索 + E 段零 LLM）。

## 六、风险与回滚

| 风险 | 缓解 | 回滚 |
|------|------|------|
| 复用过期/错误本体导致诊断质量下降 | schema_fp 严格匹配；CP-2 永不跳过；quality 标记 + Judge 审计知识来源字段；用户 force_full | `ontology.default_mode: full` 一键全局回到旧行为 |
| schema 演进（v6.4 变更）使旧资产失效 | index 记录 schema 版本号；版本不匹配自动降级 miss→full | — |
| Step10 自动增强拖长普通 run | force_off / auto 未命中即跳过；E0 BLOCKED 静默降级；增强阶段独立事件可单独禁用 | `enhancement.default: off` |
| 并行剖析引入语义越界（未等本体就做结论） | pre_profile 契约明确 Phase 0-1 只做格式/质量/状态识别；CP-4 语义校验不变 | B1 单独回滚为串行 |
| 定向修复漏修 | carried_over 标记 + judge 复审 scope 外维度抽样；全局轮次上限不变 | B2 开关回全量重算 |

## 七、与既有计划的关系

- v3 的 shared/ 基础设施、uv 优先、agent-protocol 清单化是本计划的前置（已落地）。
- 本计划不改动 v3 定义的产物契约与 CP 命令语义，只在其上叠加**资产层（L1）与意图层（L3）**；所有 SKILL.md 修改保持 v3 的"检查清单格式"。
