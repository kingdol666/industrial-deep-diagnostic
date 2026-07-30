# 系统架构师方案：从诊断管线到 DOE 知识引擎

> **角色**: 知识工程 + Agent 设计
> **基于**: 现有 v6.4 管线（12 Skills / 9 Agents / Step 0–9 / CP-1~CP-9 / `.pipeline_events.jsonl`）
> **设计原则**: 每一项都映射到现有 `SKILL_PATH`/`SHARED_PATH`/`RUN_DIR` 约定和事件日志，不引入平行体系。

---

## 0. 设计哲学：一个图，三个视图

Cambridge Digital Twin（发现1）的核心洞察是**分层知识图谱**。但在我们这个系统里，分层不是额外的数据库，而是**同一个知识图谱在不同 Step 的投影**：

```
ontology.json          ← Step 2 产出：物理层（参数语义 + 控制方程 + 物理关系）
    ↓ 因果证据回填
relationship_graph.json ← Step 3.5 产出：因果层（partial_r + dY/dX + 交互 + 安全窗）
    ↓ 跨 run 累积
process_knowledge.kg   ← Step 5.5 产出：知识层（跨场景、跨时间、带置信度衰减）
    ↓ DOE Agent 消费
doe_decisions.jsonl    ← DOE Agent 产出：决策层（实验设计 + 执行反馈）
```

**关键设计决策**: 不新建独立 GraphDB。三视图复用同一套节点/边 Schema，区别只在**证据来源**和**置信度**。这是部署简易性和可追溯性的最优折中（详见第2节）。

---

## 1. ontology.json → DOE 可消费的知识图谱

### 1.1 现状诊断

当前 `relationship_v6_3`（ontology_schema.json:213-278）已经是一个有向图边结构：

| 现有字段 | DOE 价值 | 缺失 |
|---------|---------|------|
| `from`/`to`/`type`(causal/correlative/control/physical) | 拓扑骨架 | 无效应量 |
| `strength`(strong/moderate/weak) | 粗粒度排序 | 无数值，DOE 无法排序 |
| `governing_equation` | 物理依据 | 无方程灵敏度 |
| `predicted_functional_form` | 形态提示 | 无数据拟合确认 |
| `lag_compensated_correlation.r` | 时滞修正后相关 | 停在相关，未到因果 |

**结论**: 边结构已有，但缺少**DOE 可操作的量化属性**（效应量、置信区间、交互、窗口）。这些正好是 `causal_deep_analysis.py`（Phase 1）产出的内容。所以升级不是改 ontology 本身，而是**在 Step 3.5 把因果证据回填到边属性上**。

### 1.2 新增节点类型（3种）

现有 ontology 的"节点"是 `signals`（inspection_signals / process_parameters / control_variables）。这些是**物理参数节点**，需要补充 3 种 DOE 语义节点：

```jsonc
// node_type: "quality_target"  ← DOE 优化的目标量
{
  "id": "QT_conversion_pct",
  "node_type": "quality_target",
  "column": "conversion_pct",
  "direction": "maximize",       // maximize | minimize | target
  "spec": ">=85",
  "unit": "%",
  "linked_signals": ["conversion_pct"]
}

// node_type: "operating_lever"  ← DOE 可调的杠杆参数
{
  "id": "OL_reactor_temp_C",
  "node_type": "operating_lever",
  "column": "reactor_temp_C",
  "adjustable": true,            // DCS 可控
  "controllability": "direct",   // direct | indirect | constrained
  "safe_window_ref": "SW_reactor_temp_C",
  "unit": "°C"
}

// node_type: "constraint"       ← DOE 不能调但必须监控的约束
{
  "id": "CS_byproduct_ppm",
  "node_type": "constraint",
  "column": "byproduct_ppm",
  "spec": "<=150",
  "role": "quality_guard",       // quality_guard | safety_guard | cost_guard
  "unit": "ppm"
}
```

**为什么是这 3 种**: DOE 的全部决策可以归约为一个标准问题——在 `constraint` 约束下，移动哪些 `operating_lever` 能让 `quality_target` 最优。这三种节点让知识图谱直接表达 DOE 问题结构，无需 Agent 再"猜"。

### 1.3 新增边类型（5种）

在 `relationship.type` enum 上**不删除**现有 4 种（causal/correlative/control/physical），新增 5 种 DOE 语义边：

| 新边类型 | from → to | 物理含义 | DOE 用途 |
|---------|-----------|---------|---------|
| `QUANTIFIED_CAUSAL` | lever→target | 经 partial_r/dY_dX 验证的因果 | 排序杠杆 |
| `INTERACTS_WITH` | lever↔lever | X1 效应取决于 X2 水平 | 设计析因 |
| `BOUNDED_BY` | lever→constraint | 调杠杆会触碰约束 | 风险评估 |
| `SYNERGISTIC` | (leverA,leverB)→target | 交互系数>0，协同增益 | 联合调参 |
| `ANTAGONISTIC` | (leverA,leverB)→target | 交互系数<0，互相抵消 | 避免无效组合 |

### 1.4 回填机制：边属性扩展（向后兼容）

在 `relationship_v6_3` 上新增一个可选对象 `doe_enrichment`，**不破坏 v6.4 已验证的管线**：

```jsonc
{
  "from": "reactor_temp_C",
  "to": "conversion_pct",
  "type": "causal",
  "mechanism": "Arrhenius rate law: k = A·exp(-Ea/RT)",
  "governing_equation": "r = k·C_A·C_B",
  "doe_enrichment": {                      // ← Step 3.5 回填
    "node_role": {"from": "operating_lever", "to": "quality_target"},
    "edge_type": "QUANTIFIED_CAUSAL",
    "partial_r": 0.52,
    "partial_r_ci": [0.41, 0.62],
    "dY_dX": 0.42,
    "dY_dX_unit": "% per °C",
    "dY_dX_ci": [0.35, 0.49],
    "evidence_run_id": "20260730143022_cstr",
    "evidence_level": "L3",
    "n_observations": 1440,
    "doe_implication": "温度是独立杠杆，净效应比 Pearson r 低 29%（混淆贡献）"
  }
}
```

**向后兼容保证**: `doe_enrichment` 是可选字段。现有 `data_analysis_conclusion_schema.json`、`diagnosis_schema.json`、Judge 的 10 项评分全都不读这个字段，所以**零回归风险**。CP-2（ontology schema-valid）继续校验 v6.4 的 required 字段。

### 1.5 产出文件：`parameter_relationship_graph.json`

这是给 DOE Agent 读的**完整图**，位于 `RUN_DIR/02_processed/parameter_relationship_graph.json`（复用 Phase 2 的产出位置）。它不是新的存储格式，而是 ontology + causal 证据的**投影快照**：

```jsonc
{
  "graph_version": "1.0",
  "run_id": "20260730143022_cstr",
  "scene": "CSTR催化加氢",
  "nodes": [ /* quality_target + operating_lever + constraint 三类 */ ],
  "edges": [ /* QUANTIFIED_CAUSAL + INTERACTS_WITH + BOUNDED_BY + SYNERGISTIC */ ],
  "adjacency": { "reactor_temp_C": {"targets": ["conversion_pct","byproduct_ppm"], "interacts_with": ["h2_partial_pressure_bar"]} },
  "provenance": {"ontology_ref": "01_ontology/ontology.json", "causal_ref": "02_processed/partial_correlation_matrix.json"}
}
```

---

## 2. 持久化策略：SQLite（WAL）为骨，JSONL 为日志，GraphDB 不上

### 2.1 三选一对比

| 维度 | JSONL 追加 | Neo4j GraphDB | **SQLite（推荐）** |
|------|-----------|--------------|----------------|
| 部署 | ✅ 零依赖 | ❌ 需装 JVM + 服务 | ✅ 已在用（`data/diagnostic.db` WAL） |
| 跨 run 查询 | ❌ 全扫描 | ✅ Cypher | ✅ SQL 索引 |
| 增量更新 | ✅ 追加即可 | ⚠️ 需 merge 逻辑 | ✅ UPSERT |
| 因果证据衰减 | ❌ 难 | ⚠️ 需脚本 | ✅ UPDATE + 时间戳 |
| 历史审计 | ✅ 天然 append-only | ❌ 覆盖语义 | ✅ JSONL 镜像 |
| 现有系统契合 | — | 新引入 | ✅ backend 已用 SQLite WAL |

**决策**: 用 SQLite 做知识库主存储（`workspace/knowledge_base/process_knowledge.db`），同时**镜像一份 JSONL 审计日志**。Neo4j 仅在需要**跨场景图谱可视化**时作为可选导出目标（不进核心路径）。

### 2.2 为什么不上 Neo4j

发现3（Digital Twin KG）的语义关系 REQUIRES/PARTICIPATES_IN/PRODUCES 很诱人，但：
1. 我们的工艺"步骤"粒度是**单 run 内的参数关系**，不是 Cambridge 那种跨工厂的设备-材料-工艺链。图谱深度 ≤3 跳，SQL 的递归 CTE 足够。
2. Neo4j 引入 JVM 依赖，破坏当前"双 Harness 零额外服务"的部署优势（现在只需 Node + Python venv）。
3. 跨场景对比（如 CSTR 温度 vs BOPET 温度）本质是**按参数名 GROUP BY**，SQL 更直接。

### 2.3 SQLite Schema（4 张表）

```sql
-- 知识图谱节点（跨 run 累积）
CREATE TABLE kg_nodes (
  node_id      TEXT PRIMARY KEY,        -- "OL_reactor_temp_C"
  scene_type   TEXT NOT NULL,            -- "CSTR催化加氢"
  column_name  TEXT NOT NULL,
  node_type    TEXT NOT NULL,            -- quality_target|operating_lever|constraint
  first_seen   TEXT, last_updated TEXT,
  confidence   REAL DEFAULT 1.0          -- 衰减用
);

-- 知识图谱边（带证据追溯）
CREATE TABLE kg_edges (
  edge_id      TEXT PRIMARY KEY,         -- "<from>__<to>__<run_id>"
  from_node    TEXT, to_node TEXT,
  edge_type    TEXT,                     -- QUANTIFIED_CAUSAL|INTERACTS_WITH|...
  partial_r    REAL, dY_dX REAL,
  dY_dX_ci_lo  REAL, dY_dX_ci_hi REAL,
  evidence_run_id TEXT, evidence_level TEXT,
  n_obs        INTEGER,
  created_at   TEXT, superseded_by TEXT,  -- 版本链
  FOREIGN KEY (from_node) REFERENCES kg_nodes(node_id)
);
CREATE INDEX idx_edges_from ON kg_edges(from_node, edge_type);
CREATE INDEX idx_edges_scene ON kg_edges(evidence_run_id);

-- DOE 决策与执行反馈（闭环核心）
CREATE TABLE doe_decisions (
  decision_id  TEXT PRIMARY KEY,
  run_id       TEXT, scene_type TEXT,
  plan_json    TEXT NOT NULL,             -- 完整 doe_plan
  status       TEXT DEFAULT 'proposed',   -- proposed|dispatched|executed|failed
  expected_gain TEXT, actual_gain TEXT,
  feedback_json TEXT,
  created_at TEXT, executed_at TEXT
);

-- 安全窗口（按 run 记录，支持漂移检测）
CREATE TABLE safe_windows (
  param        TEXT, scene_type TEXT, run_id TEXT,
  p5 REAL, p25 REAL, median REAL, p75 REAL, p95 REAL,
  optimal_lo REAL, optimal_hi REAL,
  current_median REAL,
  n_obs INTEGER, quality_threshold TEXT,
  recorded_at TEXT,
  PRIMARY KEY (param, scene_type, run_id)
);
```

### 2.4 增量更新协议（UPSERT + 版本链）

```python
# knowledge_base_builder.py 核心
def upsert_edge(conn, edge):
    # 同 from→to→edge_type 已存在 → 标记 superseded_by，插入新版本
    conn.execute("""
      UPDATE kg_edges SET superseded_by = ?
      WHERE from_node=? AND to_node=? AND edge_type=? AND superseded_by IS NULL
    """, (new_id, edge.from, edge.to, edge.type))
    conn.execute("INSERT INTO kg_edges (...) VALUES (...)")
```

**置信度衰减**: `kg_nodes.confidence` 按 `exp(-Δt/τ)` 衰减（τ=180天）。新 run 命中同节点 → confidence 回升。这模仿发现2的"迭代优化实验空间"——旧证据随时间降权，新实验刷新认知。

### 2.5 JSONL 审计镜像（只读、append-only）

每次 `kg_edges` 插入，同时追加一行到 `workspace/knowledge_base/kg_events.jsonl`。这是**不可变审计日志**，满足 `.pipeline_events.jsonl` 同款的"执行证明"理念。GraphDB 没有这种天然 append-only 审计。

---

## 3. DOE Agent 架构：文件驱动的闭环（不是 RPC）

### 3.1 核心约束：复用现有"文件系统通信"范式

现有管线明确："子 agent 通过文件系统通信，不经过主 agent context"（SKILL.md:202）。DOE Agent 必须遵循同一范式——**不用 RPC、不用消息队列、不用 WebSocket**。所有交互通过 `RUN_DIR` 下的 JSON 文件。

### 3.2 DOE Agent 闭环（5 阶段，映射到现有事件日志）

```
┌─────────────────────────────────────────────────────────────┐
│  DOE 闭环（每次实验迭代）                                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ① READ    读 process_knowledge.db + parameter_relationship │
│     │      _graph.json → 理解当前参数关系 + 历史窗口          │
│     ↓                                                       │
│  ② ANALYZE 识别 leverage ranking + gap to target            │
│     │      查 kg_edges WHERE edge_type='QUANTIFIED_CAUSAL'   │
│     ↓        ORDER BY ABS(dY_dX) DESC                       │
│  ③ DESIGN  生成 doe_plan.json (析因/响应面/Bayesian)          │
│     │      遵守 safe_windows 约束 + BOUNDED_BY 边             │
│     ↓                                                       │
│  ④ DISPATCH 写 dispatch_manifest.json → 工艺专家 Agent 拾取   │
│     │      （hub send 或 文件信号）                            │
│     ↓                                                       │
│  ⑤ COLLECT 新数据流入 → 重跑 industrial-analysis-auto         │
│        → knowledge_base_builder 增量更新 kg_edges            │
│        → doe_decisions.status='executed' + actual_gain       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 3.3 DOE Agent 的 dispatch 契约

DOE Agent 不直接调 DCS。它产出一个**人类确认门**后的 dispatch 清单，由工艺专家 Agent（第5节）执行：

```jsonc
// RUN_DIR/04_doe/doe_plan.json
{
  "decision_id": "DOE_20260730143022_001",
  "scene": "CSTR催化加氢",
  "current_gap": {"target": "conversion_pct>=90", "current_median": 85.6, "gap_pct": 4.4},
  "leverage_ranking": [
    {"lever": "reactor_temp_C", "dY_dX": 0.42, "headroom_up": 5.4, "risk": "low",
     "evidence_run": "20260730143022_cstr", "superseded_count": 0}
  ],
  "experiment_design": {
    "type": "central_composite",
    "factors": [{"name":"reactor_temp_C","levels":[185,188,191]},
                {"name":"h2_partial_pressure_bar","levels":[24,26,28]}],
    "center_points": 4, "replicates": 2, "total_runs": 18,
    "rationale": "检测到 SYNERGISTIC 边 (temp×pressure coef=+0.034)，需析因而非单因素"
  },
  "dispatch": [
    {"agent": "temperature_specialist", "action": "setpoint",
     "param": "reactor_temp_C", "value": 188, "ramp_rate": "0.5°C/min",
     "monitor": ["byproduct_ppm"], "abort_if": "byproduct_ppm > 180"}
  ],
  "confirmation_gate": "pending_human_approval"
}
```

### 3.4 反馈回流：DOE Agent 如何"学到"

闭环的关键是 **`actual_gain` vs `expected_gain` 的偏差**会修正知识库：

```python
# knowledge_base_builder.py 反馈处理
def process_doe_feedback(conn, decision_id, actual_data):
    plan = load_doe_decision(decision_id)
    for lever in plan.leverage_ranking:
        expected = lever.dY_dX * lever.delta
        actual = measure_gain(actual_data, lever)
        residual = actual - expected
        # 残差大 → 旧边证据弱化，触发新一轮因果分析
        if abs(residual) > 0.3 * expected:
            flag_edge_for_reanalysis(conn, lever, reason="doe_residual_large")
            conn.execute("UPDATE kg_edges SET confidence *= 0.7 WHERE ...")
```

这实现了发现2（Agent Composition）的"迭代优化实验空间"——但用的是**文件 + SQL**，不是 composite agent framework。

---

## 4. 与 industrial-analysis-auto 的集成：嵌入式（新增 Step 3.5/4.5/5.5）

### 4.1 嵌入式 vs 独立式对比

| 维度 | 嵌入式（新增 Phase） | 独立式（新 Skill） |
|------|-------------------|-----------------|
| 数据可用性 | ✅ Step 2 ontology + Step 3 数据已在内存 | ❌ 需重新加载 |
| 因果证据时效 | ✅ 即算即用 | ⚠️ 快照过期 |
| 管线复杂度 | ⚠️ +3 个 Step | ✅ 不动主线 |
| DOE Agent 复用 | ✅ 主 agent 直接 dispatch | ❌ 需额外编排 |
| 现有 CP 门禁 | ✅ 自然扩展 CP-4.5 | ⚠️ 新建检查点 |
| 回归风险 | 低（新 Step 可选） | 极低（完全隔离） |

**决策: 嵌入式（新增 Step 3.5 / 4.5 / 5.5），但全部设为 `DOE_MODE=enabled` 开关控制，默认 `auto` 模式下跳过，`doe` 模式下启用。**

### 4.2 嵌入点设计（最小侵入）

```
Step 0-1: Setup + Inspect          ← 不动
Step 2:   Ontology Builder         ← 不动（CP-2）
Step 3:   Data Processor           ← 不动（CP-4）
Step 3.5: ★ Causal Deep Analysis   ← causal_deep_analysis.py（Phase 1）
          CP-4.5: parameter_relationship_graph.json schema-valid
Step 4:   Diagnostician            ← 不动（CP-5），但可选读 causal 证据
Step 4.5: ★ Optimization Insights  ← diagnostician 产 optimization_levers
Step 5:   Judge + Auditor          ← 不动（CP-6/8）
Step 5.5: ★ Knowledge Base Update  ← knowledge_base_builder.py 写 SQLite
Step 6+:  Report + HTML            ← 不动
```

### 4.3 事件日志集成（关键：`append-pipeline-event.mjs` 扩展）

现有 `VALID_EVENTS` 和 `AGENT_TO_STEP` 必须扩展，否则 `pipeline-log-check.mjs` 会判定管线不完整：

```javascript
// append-pipeline-event.mjs 扩展（增量，不破坏现有）
const VALID_EVENTS = new Set([
  ...existing 16 events...,
  'doe_causal_analysis_start',      // Step 3.5
  'doe_causal_analysis_complete',
  'doe_optimization_insight_start', // Step 4.5
  'doe_optimization_insight_complete',
  'doe_kb_update_start',            // Step 5.5
  'doe_kb_update_complete',
]);

const AGENT_TO_STEP = {
  ...existing...,
  'data-processor': 'data_processor',     // 3.5 复用 data-processor
  'diagnostician': 'diagnostician',       // 4.5 复用 diagnostician
  'main-agent': null,                     // 5.5 main-agent 直接跑
};

const STEP_PREREQUISITES = {
  ...existing...,
  'causal_analysis': ['data_processor'],      // 3.5 必须在 3 之后
  'optimization_insight': ['causal_analysis'],// 4.5 必须在 3.5 之后
  'kb_update': ['audit'],                     // 5.5 必须在审计之后
};
```

**为什么不新建 agent**: Step 3.5 是 data-processor 的延续（它已有 cleaned_data + validate_report 在内存）；Step 4.5 是 diagnostician 的延续（它已有物理推理上下文）。新建 agent 会丢失这些上下文，违背"文件通信但上下文连续"的原则。

### 4.4 CP 门禁扩展

| 新 CP | 校验内容 | 脚本 |
|-------|---------|------|
| CP-4.5 | `parameter_relationship_graph.json` schema-valid + ≥1 QUANTIFIED_CAUSAL 边 | 复用 `validate.mjs` |
| CP-4.6 | `optimization_levers.json` 每个 lever 有 dY_dX + safe_window 引用 | 新增 check |
| CP-5.5 | `process_knowledge.db` 的 kg_edges 表行数增加 | SQL count |

CP-4.5/4.6 仅在 `DOE_MODE=enabled` 时强制；`auto` 模式下 soft-warn。

---

## 5. 工艺专家 Agent 团队：1 个 Generalist + N 个 Specialist（动态装配）

### 5.1 为什么不是纯 Specialist

发现2（Agent Composition）和发现1（Digital Twin）都暗示 specialist 编排。但工业现实是：
- **CSTR** 需要 温度/压力/流量 specialist
- **BOPET** 需要 39 个温度区 specialist（不可能每区一个 agent）
- **乐凯涂布** 187 列， specialist 组合爆炸

**决策: Generalist 为编排核心，Specialist 按 `parameter_groups`（ontology 已有的分组）动态装配。**

### 5.2 架构：Generalist 编排 + Specialist 按需

```
DOE Generalist Agent (固定 1 个)
  │  读 doe_plan.json → 按 parameter_groups 分派子任务
  │
  ├─ Temperature Specialist (动态创建，当 plan 涉及温度组)
  │    · 读 ontology.parameter_groups.thermal 的所有参数
  │    · 执行 setpoint 调整 + 监控 thermal 相关 constraint
  │
  ├─ Pressure Specialist (动态创建，当 plan 涉及压力组)
  │    · 读 ontology.parameter_groups.pressure
  │
  └─ ... (按 plan 实际涉及的组动态创建)
```

**Specialist 不是硬编码的 agent**，而是 Generalist 根据 `ontology.parameter_groups` 的 key 动态生成的 prompt 模板：

```jsonc
// 工艺专家 Agent 团队 = Generalist + 动态 specialist 列表
{
  "generalist": {
    "agent": "task",
    "role": "编排 + 冲突裁决 + 反馈汇总",
    "reads": ["doe_plan.json", "parameter_relationship_graph.json"]
  },
  "specialists": [
    {
      "name": "thermal_specialist",
      "trigger_group": "thermal",      // 匹配 ontology.parameter_groups.thermal
      "handles": ["reactor_temp_C", "cooling_water_temp_C", "feed_preheat_C"],
      "protocol": "读 references/agent-protocol.md → 执行 dispatch → 写 feedback"
    }
  ]
}
```

### 5.3 协调机制：文件锁 + 优先级（不是 RPC）

多 specialist 可能同时调相互耦合的参数（如温度↑→压力↑）。协调用**文件信号**，不用 RPC：

```jsonc
// RUN_DIR/04_doe/dispatch_semaphore.json
{
  "round": 1,
  "active_specialists": ["thermal", "pressure"],
  "conflict_rule": "thermal 优先（dY_dX 更大），pressure 延迟 1 个采样周期",
  "lock_holders": {"reactor_temp_C": "thermal_specialist", "h2_partial_pressure_bar": "pressure_specialist"}
}
```

Generalist 在派发前检查 `INTERACTS_WITH` / `SYNERGISTIC` 边，若两 specialist 操作的参数有强交互 → **合并为一个联合 specialist**，避免冲突。这比 RPC 协调简单且可审计。

### 5.4 Specialist 的 Agent 定义位置

遵循现有双 Harness 约定（AGENTS.md:19-25）：
- **Generalist**: `.omp/agents/doe-generalist.md`（OMP task-agent 唯一发现源）+ `.claude/skills/industrial-doe-orchestrator/`
- **Specialist 模板**: 不建独立 agent 文件，由 Generalist 在运行时用 `Agent({subagent_type:"task", prompt: specialist_prompt})` 动态生成。这避免 specialist 组合爆炸。

---

## 6. 落地路线图（与现有 V1.0 DOE-integration-plan 对齐）

| 阶段 | 内容 | 涉及现有约定 |
|------|------|-------------|
| **W1-2** | Phase 1: `causal_deep_analysis.py` → Step 3.5 | `industrial-data-processor/scripts/`，CP-4.5 |
| **W3** | Phase 2: `relationship_graph_builder.py` | 输出到 `02_processed/`，新增 schema |
| **W4** | Phase 3: diagnostician Step 4.5 `optimization_insights` | `diagnosis_schema.json` 可选字段 |
| **W5-6** | Phase 4: `knowledge_base_builder.py` + SQLite | `workspace/knowledge_base/process_knowledge.db` |
| **W6** | 事件日志扩展 | `append-pipeline-event.mjs` VALID_EVENTS + STEP_PREREQUISITES |
| **W7** | Phase 5: DOE Generalist Agent + Specialist 模板 | `.omp/agents/doe-generalist.md` |
| **W8** | 端到端闭环测试 | CSTR 场景：诊断 → 知识库 → DOE plan → 模拟反馈 → kb 更新 |

---

## 7. 关键风险与缓解

| 风险 | 缓解 | 验证方式 |
|------|------|---------|
| partial_r 在高维不稳定 | 控制变量 ≤5，LASSO 预筛 | CSTR(16列) + 乐凯(187列) 对比测试 |
| SQLite 并发写（多 run 同时） | 已用 WAL 模式（backend 同款） | `PRAGMA journal_mode=WAL` 确认 |
| Specialist 动态生成 prompt 漂移 | 模板固定，只填参数组 key | 对比 3 次生成的 prompt diff |
| DOE Agent 误读知识库（幻觉边） | 每条建议必须附 `evidence_run_id`，可追溯 | CP-4.5 校验 evidence 字段非空 |
| 新 Step 拖慢管线 | `DOE_MODE=auto` 时 3.5/4.5/5.5 跳过 | `run_config.json` 开关 + 计时 |

---

## 8. 架构一致性自检

| 检查项 | 本方案 | 现有约定 |
|--------|-------|---------|
| Skill 发现 | `.claude/skills/industrial-doe-orchestrator/` | ✅ 符合 AGENTS.md:16 |
| Agent 定义 | `.omp/agents/doe-generalist.md` | ✅ 符合 AGENTS.md:19 |
| Agent 通信 | 文件系统（doe_plan.json / feedback.json） | ✅ 符合 SKILL.md:202 |
| 事件日志 | 扩展 VALID_EVENTS（不新建日志文件） | ✅ 复用 `.pipeline_events.jsonl` |
| 检查点 | CP-4.5/4.6/5.5（soft in auto, hard in doe） | ✅ 符合 CP 门禁范式 |
| 路径变量 | `SKILL_PATH`/`SHARED_PATH`/`RUN_DIR` 不变 | ✅ Dispatch 协议复用 |
| 向后兼容 | `doe_enrichment` 可选字段，v6.4 required 不动 | ✅ 零回归 |
| 存储选型 | SQLite WAL（backend 已用）+ JSONL 审计 | ✅ 无新依赖 |

---

*架构师方案 v1.0 | 知识工程 + Agent 设计 | 基于 v6.4 管线实际约定*
