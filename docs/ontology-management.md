# 本体模型管理（Ontology Model Management）

本体（`ontology.json`）是整条诊断管线的地基：Step 2 由 `context-builder` 构建，Step 3-9 全部消费它的语义。
本文件记录**本体资产的持久化契约、控制 API、前端可视化与编辑设计**及其依据。

---

## 1. 持久化：唯一事实源

```
data/ontology_store/
├── index.json                     # 资产索引（列表页只读它，O(1)）
└── <scene_key>/
    └── v<N>/
        ├── ontology.json          # 纯领域产物（schema 校验对象）
        └── provenance.json        # 编辑/来源元数据（不进领域文档）
```

**唯一写入口**：`.claude/shared/scripts/ontology_store.mjs`

这是本设计最重要的约束。三条路径全部经由它写入：

| 路径 | 调用点 |
|------|--------|
| Agent / Skill 构建后发布 | `publish({ runDir, scene, buildMode })`（skill 协议 Phase -1 收尾） |
| 管线确定性快路径 | `fastReuse()` → `reuse()` → `addVersion()` |
| 前端在线编辑保存 | `PUT /api/ontology/assets/:scene/:version` → `saveAsset()` → `addVersion()` |

因为共享同一个 `addVersion`，三者共享同一份索引不变量、同一套 CP-2 判据、同一种内容去重行为。
**管理页因此不会成为与 Agent 并行的第二个静默事实源。**

### 编辑器元数据与领域文档分离

`title / tags / notes / quality / origin / parent_version` 全部存在 `index.json` 与 `provenance.json`，
**不写入 `ontology.json`**。这样：

- 领域文档保持纯净 —— skill 的 JSON Schema 校验、LLM 的写入都不受编辑器状态污染；
- 元数据补丁（`PATCH`）不产生新版本；
- 索引可演进（新增 `summary`、`content_sha256` 等字段）而不触碰历史正文。

`backfillIndex()` 对历史条目懒回填 `summary` / `content_sha256` / `title` / `tags` / `origin`，
只改索引不碰正文 —— 所以既有的 3 个老条目无需迁移即可被完整管理。

---

## 2. 版本模型

- **历史不可变**：编辑保存写入 `v(N+1)`，永不覆盖 `v(N)`。
- **指纹继承**：新版本继承源条目的 `schema_fp` / `content_fp`，因此 `findMatch()` 仍能命中，
  复用链路在人工编辑后依然成立（这是"编辑过的本体能被复用"的关键）。
- **内容去重**：同 scene 下内容哈希一致时返回既有版本并标 `deduped: true`，
  避免"打开→保存"产生噪声版本。
- **父版本留痕**：`parent_version` + `provenance.edit_of_version` 记录编辑基线。
- **来源标记**：`origin` = `agent`（管线/采纳）/ `user:<name>`（前端编辑）/ `cli`。

### 并发不变式（RFC 9110 §13 / RFC 6585 §3）

| 条件 | 响应 |
|------|------|
| 编辑既有版本但未携带前置条件 | **428** `PRECONDITION_REQUIRED` |
| `If-Match` / `expected_sha256` 与磁盘内容不符 | **409** `CONTENT_CHANGED` |
| `base_version` 落后于最新版本 | **409** `VERSION_CONFLICT` |
| CP-2 校验失败且未 `force` | **422** `VALIDATION_FAILED`（**不落盘**） |

`GET /assets/:scene/:version` 返回**强 ETag**（`"sha256:…"`，无 `W/` 前缀 —— 弱校验器永远不会匹配 `If-Match`）。

> 关于 428 的诚实边界：RFC 6585 §7.1 明确 "clients cannot rely upon its use to prevent lost update conflicts"。
> 它是**纵深防御**，不能替代客户端始终发送 `If-Match`。前端两者都做。

**冲突时绝不静默重试**：UI 呈现 base / mine / theirs 三方差异，只提供「重新加载」「强制保存」「取消」三个出口。

---

## 3. 控制 API（`/api/ontology`）

### 读取

| 端点 | 说明 |
|------|------|
| `GET /assets?scene=&quality=&q=` | 按场景聚合的资产列表（含 each 版本的 present/bytes/quality/origin/summary） |
| `GET /assets/:scene/:version` | 本体全文 + CP-2 校验 + 健康度量 + 图投影 + 强 ETag |
| `GET /assets/:scene/:version/graph?structure=&relationships=&knowledge=` | 分层图投影 |
| `GET /assets/:scene/:version/metrics` | 模型健康度量 |
| `GET /assets/:scene/:version/validate` | 只读 CP-2 报告 |
| `GET /assets/:scene/:version/provenance` | 溯源 |
| `GET /diff?scene=&from=&to=` | 版本差异 |
| `GET /overview` | 总览统计 |
| `GET /schema` | CP-2 所用的 JSON Schema + 路径常量 |
| `GET /candidates` | run 目录中已构建的本体（含未入库） |

### 写入

| 端点 | 说明 |
|------|------|
| `PUT /assets/:scene/:version` | 保存编辑 → 新版本（需 `If-Match` 或 `expected_sha256`） |
| `POST /assets` | 新建场景（生成已通过 CP-2 的脚手架，含填充指引） |
| `PATCH /assets/:scene/:version` | 元数据（title/tags/notes/quality），不产生新版本 |
| `POST /assets/:scene/:version/clone` | 克隆到新场景 |
| `DELETE /assets/:scene/:version` | 删除单版本（若场景目录变空则一并清理） |
| `DELETE /scenes/:scene` | 删除整场景 |

### 无状态投影（草稿预览）

`POST /validate` · `POST /graph` · `POST /metrics` · `POST /diff` 接受任意本体载荷，
**不落盘**。前端在编辑时就地调用它们，实现"边改边看"而无需保存。

### 复用推荐

`POST /recommend { dataPath?, scene? }` 基于数据指纹（列 schema 哈希）回答
**"是否存在与场景高度相关的可复用本体"**：

- `mode: 'fingerprint'` → `match: 'exact' | 'extend' | 'miss'` + 命中场景/版本/理由 + 数据列清单
- `mode: 'list'` → 无数据路径时列出全部候选资产

这与管线 `resolveOntologyDirective()` 调用的是同一个 `findMatch()`，所以 UI 的推荐与管线的实际复用决策一致。

---

## 4. 可视化：为什么这么画

### 依据

本体的可视化有唯一的形式化视觉语言 **VOWL 2.0**（Visual Notation for OWL Ontologies），
其核心编码被本项目按领域语义重新映射（本模型不是 OWL，但视觉语法可用）：

| VOWL 约定 | 本模型的映射 |
|-----------|--------------|
| 类 = 圆 | 信号 = 圆（按 role 着色） |
| 数据类型 = 矩形 | 元数据列 / 参数组 = 矩形；控制量 / 设备 / 阶段 = 圆角矩形 |
| 对象属性 = 蓝色弧、箭头 | 因果/相关/控制/物理关系 = 带箭头的有向边（按 type 着色） |
| subClassOf = **点线** | 推断关系（`inferred: true`）= **虚线**；实线 = 已确认 |
| 线宽编码 | 关系强度 `strong/moderate/weak` → 3.2 / 2.2 / 1.4 px |
| 高亮 | 选中节点放大 + 琥珀描边；邻接高亮，其余淡出 |

**为什么是力导向布局**：VOWL 自身规定 "force-directed with node centrality ∝ property-relation degree"。
本页另提供环形与自由布局，但默认力导向。

**为什么保留悬空引用节点**：`relationships[].from/to` 指向不存在的列是手写 JSON 最常见的静默损坏。
图里不静默丢弃，而是标红虚线占位节点，并在工具条上提示数量。

### 三层可切换（避免图过载）

- **结构层**（默认开）：场景 → 设备 / 工艺阶段骨架
- **关系层**（默认开）：信号之间的语义边 —— 核心信息
- **知识层**（默认关）：物理原理 / 失效模式 / 差异信号 / 混杂因子 / 参数组

### 全局过滤器

`physical_meaning_confidence`（KNOWN/INFERRED/UNKNOWN）、`behavior_match`、`knowledge_source`
被提升为**图级过滤器**而非仅仅是字段。理由：领域专家的第一个问题永远是
"这些里哪些是实测的，哪些是推断的？" —— 把它做成过滤器，答案是一眼可见的。

### 渲染技术选型

ECharts `graph` series（Canvas / zrender），与项目既有 8 个图表组件同源，**零新增依赖**。
在 100–500 节点量级 Canvas 完全够用；支持 force/circular/none 布局、`roam` 缩放平移、
`draggable` 拖拽、category 着色、自定义 symbol（circle/rect/roundRect/triangle/diamond/pin）、
边箭头与虚线、`emphasis.focus: adjacency` 邻接高亮。

> 备选方案 Cytoscape.js 的独有优势是复合节点（compound nodes）与图算法。
> 本设计以「服务端图投影 + 分类着色 + 参数组」覆盖分组需求，用自研 Tarjan SCC 覆盖环检测，
> 因此不必为此引入第二个图引擎。

---

## 5. 模型健康：可解释而非玄学

所有度量在服务端 `computeMetrics()` 计算（纯函数，可在 `node:test` 中直接断言）。

**规模 / 语义覆盖 / 关系质量 / 一致性 / 图拓扑** 五组指标，加一个加权 0–100 分：

```
cp2(25) + no_dangling(15) + semantics(20) + described(10)
       + mechanism(10) + binding(10) + no_orphans(10)
```

分值的每一项都在 UI 里显示 `points/weight`，可逐项复算。

### 缺陷记录：一种形状服务所有消费者

所有校验发现统一为 **SHACL `sh:ValidationResult` 形状**的记录：

```json
{ "code": "DANGLING_RELATIONSHIP",
  "severity": "critical",                       // ↔ sh:Violation / sh:Warning / sh:Info
  "sourceRule": "referential-integrity",
  "focusNode": "col_ghost",
  "path": "relationships[3].to",
  "pointer": "/relationships/3/to",             // RFC 6901，与 RFC 6902 补丁同一坐标系
  "value": "col_ghost",
  "message": "…", "hint": "…",
  "justification": ["relationships: col_b → col_ghost"] }
```

- **severity 三级**：`critical` / `important` / `minor` —— 与 OOPS! 的三级严重度、SHACL 的三级结果一一对应。
  本模型刻意**不**claim 某个 OOPS! 编号的严重度（如 P04/P08 实为 Minor）；悬空端点没有 OOPS! 等价项，
  本系统按工程后果评为 critical，因为一条悬空 `from` 会静默破坏全部下游消费者。
- **`pointer` 与 JSON Pointer 对齐**：校验错误的位置与未来的 RFC 6902 修复补丁共享坐标，
  因此"点错误 → 定位字段 → 生成修复"是机械可得的，而不是特例代码。
  ⚠️ RFC 6901 转义必须先 `~`→`~0` 再 `/`→`~1`，顺序不可交换（信号列名可能含 `/`）。
- **`justification` = 最小致因断言子集**（对应 OWL Explanation 的 justification 概念）。
  只报"有问题"不可操作，报出"是这两条断言蕴含了它"才可操作。

### 图算法

- **因果环**：Tarjan 强连通分量。因果子图必须是 DAG，SCC 大小 > 1 即建模错误或未显式处理的反馈回路。
- **矛盾聚集**：`CONTRADICTED` 信号若集中在同一 `stage_ref`，问题更可能出在**阶段模型**而非单个信号。
- **度异常**：度 > 均值 + 2σ 的节点可能过度声称解释力。
- **影响面**（`impactAnalysis`）：从任一节点 BFS 上/下游可达集。

---

## 6. Agent → 前端的桥

`industrial-ontology-builder`（王教授）按 skill 协议写 `workspace/diagnostic-runs/<run>/01_ontology/ontology.json`，
收尾调用 `ontology_store.mjs publish` 入库。**入库后前端即可读取、可视化、编辑**。

但 publish 失败不阻断管线（设计如此），因此 `GET /candidates` 额外扫描全部 run 目录，
用**内容哈希**比对是否已入库，未入库的标 `adoptable: true`，前端一键采纳（支持批量）。

这形成了一条诚实的链路：

```
Agent 构建 → RUN_DIR/01_ontology/ontology.json
                    │ publish（正常路径）
                    ↓
              data/ontology_store/  ←→  前端管理页（可视化 / 编辑 / 版本 / 复用推荐）
                    │ findMatch + reuse
                    ↓
              下一次诊断 run（复用人/Agent 编辑后的语义）
```

**采纳 ≠ 直接写入**：Agent 产物首先作为候选呈现（带 CP-2 判定与规模摘要），由人决定是否入库。
这与成熟知识管理产品把 LLM 输出建模为"可审阅建议 + 置信度 + 采纳/驳回"的做法一致，
也与本模型自身的 `physical_meaning_confidence` 三级语义一致。

---

## 7. 测试

| 层次 | 文件 | 用例 |
|------|------|------|
| store 原语 + 图投影 + 度量 + 差异 + 保存不变式 + 全链路 | `app/backend/test/ontology-control.test.mjs` | 41 |
| 真实 HTTP 端到端（起真服务，驱动完整生命周期） | `app/backend/test/ontology-api.e2e.test.mjs` | 25 |
| 真实浏览器端到端（Playwright 驱动运行中的 GUI） | `tests/e2e/ontology-ui-e2e.py` | 31 |

```bash
cd app/backend && npm test                       # 全部后端用例（含上述前两组）
python tests/e2e/ontology-ui-e2e.py              # 需要 3210/5180 已启动 + 一个可用账号
```

浏览器用例覆盖：登录 → 进入本体页 → 资产列表 → 图渲染（canvas 真有尺寸）→ 图层切换 →
点击节点填充检视面板 → 结构编辑器 → 改字段 → 校验 → 保存 → **服务端核对新版本与语义** →
刷新后仍读到新版本 → 版本差异含改动字段 → 模型健康 → 采纳候选模态 → 新建模态 → 零 console 错误。

---

## 8. 已知边界

- **不做实时协同编辑**。本体是 schema 校验的领域文档，`column` 唯一性、`from/to` 引用完整性、
  因果无环性都是 **check-then-set 不变量** —— 这类约束必须被**拒绝**而非被"合并"。
  因此选择乐观并发（强 ETag + `If-Match`）+ 显式冲突解决，而不是 CRDT。
- **删除是破坏性的**：`deprecated`（保留可寻址性）是首选动作，删除是次级动作并二次确认。
  一个对已发布实体直接提供 Delete 的管理界面是有缺陷的。
- **`format` 关键字默认仅作注解**（JSON Schema 规范 §7.2.1：实现 MUST 默认禁用 format 断言），
  所以 `format: "date-time"` 不会自动拒绝坏输入 —— 需要这类约束时应显式加 `pattern`。
- **未实现的候选能力**（已评估，暂不做）：JSON-Patch 变更日志（当前以不可变版本 + 结构化差异代替）、
  逐规则 Enforce/Report/Ignore 策略档、导入期校验阶段、变更集审阅工作流。
