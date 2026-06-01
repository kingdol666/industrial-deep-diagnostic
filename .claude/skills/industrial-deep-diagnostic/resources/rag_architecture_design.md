# RAG Knowledge Engine — Architecture Design

> 本文件为 `industrial-deep-diagnostic` 技能的下一个重大升级设计：引入 RAG 知识引擎，实现智能检索、自动本体构建、跨运行知识积累，为下游诊断和物理推理提供结构化的物理依据。

---

## 1. 当前问题分析

### 当前 context-builder 的知识获取方式：

```
┌─ Step 1: 读取本地参考文档 ──────────────────┐
│  REFERENCE_DIR 中的文件 → LLM 读取 → 提取    │
│  弱点：受限于 LLM 上下文窗口，大文档会丢失    │
└──────────────────────────────────────────────┘

┌─ Step 2: 可选网络搜索 ───────────────────────┐
│  LLM 内置搜索 → 最多 5 次查询 → web_findings.md │
│  弱点：                                 │
│  · 无结构化存储，每次重新搜索("每次重新发明")  │
│  · 跨运行之间知识不积累                       │
│  · 搜索结果以纯文本保存，无法被后续      │
│    诊断阶段的物理推理引擎(r=0.97)直接消费    │
└──────────────────────────────────────────────┘

┌─ Step 3-4: 手工构建本体 ──────────────────────┐
│  LLM 综合已知信息 → 输出 ontology.json        │
│  弱点：                                 │
│  · 每次从零构建，格式一致性依赖 prompt    │
│  · 未使用已有的领域知识库语义匹配          │
│  · 物理参数与已知机制的关联需人工核对      │
└──────────────────────────────────────────────┘
```

### 核心痛点的根本原因

| 痛点 | 根因 | RAG 如何解决 |
|------|------|-------------|
| 每次诊断从头搜索 | 无持久知识存储 | 向量数据库积累所有知识 |
| 搜索结果结构差 | 存为纯文本文件 | 语义分块 + 结构化 metadata |
| 知识不跨运行复用 | 无知识管理体系 | 按场景类型索引 + 质量评分门控 |
| 物理机制匹配靠直觉 | 没有参数→机制映射检索 | 语义检索直接返回匹配的 causal_chains |
| 本体构建每次不一致 | 没有模板化知识结构 | 检索 chunk → 填充结构化模板 |

---

## 2. 整体架构

```
┌────────────────────────────────────────────────────────────────────┐
│                     RAG KNOWLEDGE ENGINE                           │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐   │
│  │  INGESTION   │  │  RETRIEVAL   │  │  KNOWLEDGE CURATION    │   │
│  │  Pipeline    │  │  Pipeline    │  │  (跨运行)               │   │
│  └──────┬───────┘  └──────┬───────┘  └───────────┬────────────┘   │
│         │                 │                      │                │
│         ▼                 ▼                      ▼                │
│  ┌─────────────────────────────────────────────────────────┐      │
│  │              VECTOR STORE (ChromaDB)                     │      │
│  │                                                          │      │
│  │  [chunk_001] [chunk_002] [chunk_003] ... [chunk_N]     │      │
│  │  • ID      • embedding(768d)  • metadata               │      │
│  │  • content • source_type     • scenario_type            │      │
│  │  • param_names • confidence  • timestamp                │      │
│  └─────────────────────────────────────────────────────────┘      │
│                                                                    │
│  ┌──────────────────────────────────────────┐                    │
│  │        STRUCTURED KNOWLEDGE OUTPUT       │                    │
│  │  ┌──────────────────┐  ┌───────────────┐ │                    │
│  │  │ knowledge_chunks │  │ ontology_draft│ │                    │
│  │  │ .json            │  │ .json         │ │                    │
│  │  └──────────────────┘  └───────────────┘ │                    │
│  └──────────────────────────────────────────┘                    │
└────────────────────────────────────────────────────────────────────┘

         │ 集成到现有流水线
         ▼
┌────────────────────────────────────────────────────────────────────┐
│                    EXISTING PIPELINE                                │
│  Step 0-1 → Step 2 (Context Builder + RAG) → Step 3 → ... → Step 8│
│                        │ RAG 增强                                   │
│                        ├── kb_retrieve.py (场景感知检索)           │
│                        ├── 自动填充 ontology.json 模板             │
│                        └── 物理机制预匹配到短列表参数              │
└────────────────────────────────────────────────────────────────────┘
```

---

## 3. 知识块设计

### 3.1 Chunk 模式

```python
@dataclass
class KnowledgeChunk:
    chunk_id: str                    # "kb_cnc_vibration_001"
    content: str                     # 原始文本块
    embedding: List[float]           # 768d 嵌入向量
    
    # === 身份元数据 ===
    source_type: str                 # "local_reference" | "web_search" | 
                                     # "accumulated_diagnosis" | "user_doc"
    source_path: str                 # 原始文件路径/URL
    source_confidence: float         # 0.0-1.0 来源可靠性评分
    timestamp: str                   # ISO8601 索引时间
    
    # === 场景标签（用于检索过滤）===
    scenario_types: List[str]        # ["CNC", "continuous_film", "batch_chemical", 
                                     #  "heat_exchange", "metal_forming", "generic"]
    applicable_processes: List[str]  # ["BOPET", "PET", "aluminum_cutting", ...]
    
    # === 参数标签（用于精确匹配检索）===
    related_parameters: List[str]    # ["spindle_vibration_mm_s", "MD_TH003", ...]
    related_physical_quantities: List[str]  # ["temperature", "vibration", "pressure"]
    
    # === 机制标签（用于物理推理检索）===
    mechanism_type: str              # "degradation" | "fault_pattern" | "causal_chain" |
                                     # "quantitative_rule" | "equipment_spec" | "control_logic"
    causal_chain: Optional[str]      # 如 "轴承磨损→振动↑→粗糙度↑"
    governing_equation: Optional[str] # 如 "Ra ≈ fz²/(8×rε)"
    
    # === 质量标签 ===
    cross_referenced: bool           # 是否被多个来源交叉验证
    verified_by_run: Optional[str]   # 被哪次诊断运行验证过
    expired: bool                    # 是否已过期（需要重新验证）
```

### 3.2 Chunking 策略（按领域）

```
┌─────────────────────────────────────────┐
│  文档: process_knowledge_base.md        │
│                                         │
│  chunk_001 [scenario: film]             │
│  "PET extrusion temperature: 270-290°C" │
│  → 机制: quantitative_rule             │
│                                         │
│  chunk_002 [scenario: film]             │
│  "PET thermal degradation: Arrhenius"   │
│  → 机制: quantitative_rule             │
│                                         │
│  chunk_003 [scenario: CNC]              │
│  "ISO 10816 vibration severity classes" │
│  → 机制: fault_pattern                 │
└─────────────────────────────────────────┘

┌──────────────────────────────────────────────┐
│  文档: parameter_to_physics.json              │
│                                               │
│  chunk_010 [param: spindle_vibration]         │
│  causal_chain: "轴承磨损→振动↑→粗糙度↑"      │
│  governing_eq: "ISO 10816 Zone C >4.5mm/s"   │
│  → 机制: causal_chain                        │
│                                               │
│  chunk_011 [param: spindle_temp]              │
│  causal_chain: "轴承磨损→摩擦↑→温度↑"        │
│  → 机制: causal_chain                        │
└──────────────────────────────────────────────┘
```

---

## 4. 向量存储策略

### 选型：ChromaDB

| 特性 | ChromaDB | FAISS | Pinecone |
|------|:--------:|:-----:|:--------:|
| 本地化（无服务依赖） | ✅ | ✅ | ❌ |
| 持久化文件存储 | ✅ | ✅ | — |
| metadata 过滤 | ✅ | ❌ | ✅ |
| Python API | ✅ | ✅ | ✅ |
| uv venv 兼容 | ✅ | ✅ | ✅ |
| 增量更新 | ✅ | ✅ | ✅ |
| 安装体积 | 轻量 | 中等 | N/A |

### 存储位置

```
.claude/skills/industrial-deep-diagnostic/
├── knowledge_base/
│   ├── chroma_db/                  ← ChromaDB 持久化目录
│   │   ├── chroma.sqlite3         
│   │   └── ...default_persistent...
│   └── collection_manifest.json    ← 集合版本管理
│       {
│         "version": "1.0",
│         "collections": {
│           "industrial_knowledge": {
│             "chunk_count": 243,
│             "last_updated": "2026-06-01",
│             "sources": [
│               {"name": "process_knowledge_base.md", "chunks": 42},
│               {"name": "parameter_to_physics.json", "chunks": 36},
│               ...
│             ]
│           }
│         }
│       }
```

### 嵌入模型选择

| 方案 | 延迟 | 质量 | 适用场景 |
|------|:----:|:----:|----------|
| **方案 A（推荐）**: `sentence-transformers/all-MiniLM-L6-v2` | ~10ms/chunk ✅ | 中 | 本地运行，无 API 依赖 |
| 方案 B: OpenAI `text-embedding-3-small` | ~100ms (API) | 高 ✅ | 需 API key |
| 方案 C: `nomic-embed-text-v1.5` | ~15ms/chunk | 中高 | 本地，质量接近 B |

**推荐方案 A**：384 维嵌入，本地运行，与 uv 生态兼容。

---

## 5. 注入管道 (Ingestion Pipeline)

### 5.1 执行流程

```
                                     ┌─────────────────────┐
                                     │ kb_build.py         │
                                     │ uv venv Python      │
                                     └──────┬──────────────┘
                                            │
         ┌──────────────────────────────────┼────────────────────┐
         ▼                                  ▼                    ▼
   ┌──────────┐                      ┌──────────┐        ┌──────────────┐
   │ 静态资源  │                      │ 网络知识  │        │ 历史诊断积累  │
   │ (文件系统) │                      │ (API搜索) │        │ (workspace)   │
   └────┬─────┘                      └────┬─────┘        └──────┬───────┘
        │                                  │                     │
        ▼                                  ▼                     ▼
   ┌──────────────────────────────────────────────────────────────┐
   │                    Knowledge Chunking                         │
   │   • RecursiveCharacterTextSplitter(chunk=512, overlap=64)    │
   │   • 领域感知分块: 保留参数名、物理公式、枚举值               │
   └──────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
   ┌──────────────────────────────────────────────────────────────┐
   │                    Embedding Generation                       │
   │   • sentence-transformers 生成 384d 向量                    │
   │   • 每个 chunk 独立嵌入                                      │
   └──────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
   ┌──────────────────────────────────────────────────────────────┐
   │                    ChromaDB Upsert                            │
   │   • 按 chunk_id 幂等插入 (重复 ID 自动覆盖)                 │
   │   • metadata 写入过滤字段 (scenario_type, param_name)        │
   └──────────────────────────────────────────────────────────────┘
```

### 5.2 Ingestion 触发时机

| 时机 | 频率 | 范围 | 说明 |
|------|------|------|------|
| 技能初始化 | 一次 | 全部静态资源 | `kb_build.py --init` |
| 每次诊断运行 (Step 0) | 每次 | 用户参考文档 + 网络结果 | `kb_build.py --ingest-run RUN_DIR` |
| 诊断完成 (Step 8) | 每次 | 诊断结论(高置信度) | `kb_build.py --accumulate RUN_DIR` |
| 手动重建 | 按需 | 全部 | `kb_build.py --rebuild` |

### 5.3 `kb_build.py` 接口设计

```bash
# 初始化：读取所有 reference 文件 + schema 文件 + template 文件
$PYTHON scripts/kb_build.py --init --skill-path SKILL_PATH
# → 索引 process_knowledge_base.md, parameter_to_physics.json, evidence_rules.md, diagnosis_method.md

# 增量注入：单次运行的参考文档
$PYTHON scripts/kb_build.py --ingest-run RUN_DIR
# → 索引 REFERENCE_DIR 文件 + web_findings.md + extracted_knowledge.json

# 从诊断结果积累知识
$PYTHON scripts/kb_build.py --accumulate RUN_DIR --confidence-threshold 0.8
# → 只有当 Judge 评分 >= 90 且 物理审计为 ENDORSED 才积累

# 重建全部
$PYTHON scripts/kb_build.py --rebuild
# → --init + 扫描所有历史 run_dir
```

---

## 6. 检索管道 (Retrieval Pipeline)

### 6.1 场景感知检索

这是核心创新：不用通用搜索，而是**用诊断上下文的语义生成检索查询**。

```
┌────────────────────────────────────────────────────────┐
│  输入: 诊断上下文                                       │
│  · process_type = "CNC machining"                      │
│  · target_col = "surface_roughness_Ra_um"              │
│  · top_params = ["spindle_vibration", "spindle_temp"]  │
│  · anomaly_type = "gradual drift"                      │
│  · grouping_cols = ["material"]                        │
└─────────────────────┬──────────────────────────────────┘
                      │
                      ▼
┌────────────────────────────────────────────────────────┐
│  Query Construction (kb_retrieve.py)                    │
│                                                         │
│  query_primary:  "CNC machining surface roughness       │
│                   spindle vibration bearing wear"       │
│                                                         │
│  filter:  scenario_types=["CNC"]                        │
│           related_parameters=["spindle_vibration_mm_s", │
│                                "surface_roughness_Ra_um"]│
│           mechanism_type=["causal_chain",               │
│                            "quantitative_rule"]         │
└─────────────────────┬──────────────────────────────────┘
                      │
                      ▼
┌────────────────────────────────────────────────────────┐
│  ChromaDB Semantic Search                               │
│                                                         │
│  1. dense_retrieval:  query_embedding → top_k=20       │
│  2. metadata_filter:  scenario_type=CNC (AND)           │
│  3. hybrid_rerank:    BM25 keyword boost + param match  │
│  4. diversity:        MMR (Maximal Marginal Relevance)  │
│                       → 保留 10 个最相关的多样化 chunk  │
└─────────────────────┬──────────────────────────────────┘
                      │
                      ▼
┌────────────────────────────────────────────────────────┐
│  输出: 排序后的知识块 (knowledge_chunks.json)            │
│                                                         │
│  [
│    {chunk_id, content, source, relevance_score(0.93),
│     mechanism: "轴承磨损→振动↑→粗糙度↑",
│     governing_eq: "Ra ≈ fz²/(8×rε)"},
│    {chunk_id, content, source, relevance_score(0.87),
│     mechanism: "ISO 10816 Zone C >4.5mm/s",
│     ...}
│  ]
└────────────────────────────────────────────────────────┘
```

### 6.2 多查询策略

单一查询可能遗漏。使用**多查询扩展**：

```python
# 根据场景自动生成多个查询视角
def build_queries(context):
    queries = []
    
    # 视角 1: 参数物理含义
    queries.append({
        "query": f"{param_name} physical meaning in {process_type}",
        "filter": {"mechanism_type": "equipment_spec"}
    })
    
    # 视角 2: 已知故障模式
    queries.append({
        "query": f"{target_column} degradation root cause {process_type}",
        "filter": {"mechanism_type": "fault_pattern"}
    })
    
    # 视角 3: 定量物理关系
    queries.append({
        "query": f"{param_a} and {param_b} relationship formula",
        "filter": {"mechanism_type": "quantitative_rule"}
    })
    
    # 视角 4: 竞争假设(冲突知识)
    queries.append({
        "query": f"confounding factor {grouping_cols} in {process_type}",
        "filter": {"mechanism_type": "control_logic"}
    })
    
    return queries  # 4 queries × top_k=5 → 20 candidates → rerank → top 10
```

### 6.3 `kb_retrieve.py` 接口

```bash
# 给定诊断上下文，检索最相关的知识
$PYTHON scripts/kb_retrieve.py \
  --scenario "CNC machining" \
  --targets "surface_roughness_Ra_um,thermal_deviation_mm" \
  --parameters "spindle_vibration_mm_s,spindle_temp_C,tool_age_parts" \
  --group-columns "material" \
  --skill-path SKILL_PATH \
  --top-k 10 \
  --output RUN_DIR/00_input/knowledge_chunks.json

# 或只用 run_dir 自动提取上下文
$PYTHON scripts/kb_retrieve.py \
  --from-run RUN_DIR \
  --top-k 10 \
  --output RUN_DIR/00_input/knowledge_chunks.json
```

---

## 7. 自动本体构建

这是 RAG 注入到现有 pipeline 的关键环节。不替换现有 context-builder agent，而是**为其提供结构化知识基础**。

### 7.1 增强后的 Step 2 流程

```
现有:   Step 2.1→ Step 2.2 → Step 2.3 → Step 2.4 → Step 2.5
        (ref search)  (web)    (ontology)  (schema)   (clarify)

RAG 增强:
        ┌─────────────┐
        │ kb_retrieve │  ← 在 Step 2.1 之前执行
        └──────┬──────┘
               │ knowledge_chunks.json
               ▼
        ┌────────────────────────────────────────────┐
        │ 2.1 Auto-Ontology Draft                     │
        │ 从检索到的知识块自动生成 ontology 骨架:     │
        │ - equipment 列表从 matching chunks 提取      │
        │ - 参数物理含义从 knowledge_chunks填充       │
        │ - causal_relationships 从因果链chunk提取    │
        │ - confounders 从故障模式chunk提取           │
        │ - 每个字段标注 confidence + source          │
        └──────────────────┬─────────────────────────┘
                           │ ontology_draft.json
                           ▼
        ┌────────────────────────────────────────────┐
        │ 2.2 Human-like Refinement (现有 LLM 步骤)  │
        │ - LLM 参考 ontology_draft.json 修正        │
        │ - 覆盖：用户上下文 + 数据列名直接匹配      │
        │ - 输出最终 ontology.json                   │
        └────────────────────────────────────────────┘
```

### 7.2 Auto-Ontology Draft 算法

```python
def auto_ontology_draft(knowledge_chunks, column_names, process_type):
    ontology = {
        "scene": {"name": "", "process_type": process_type},
        "signals": {"inspection_signals": [], "process_parameters": [],
                    "control_variables": [], "events": [], "metadata_columns": []},
        "relationships": [],
        "confounders": []
    }
    
    # 1. 列名 → 参数匹配
    for col in column_names:
        # 语义匹配：col.name ↔ chunk.related_parameters
        matching_chunks = semantic_match(col.name, knowledge_chunks)
        if matching_chunks:
            # 从匹配 chunk 提取物理含义
            ontology["signals"]["process_parameters"].append({
                "column": col.name,
                "physical_meaning": matching_chunks[0].content,
                "confidence": matching_chunks[0].source_confidence,
                "source": matching_chunks[0].source_type,
                "governing_law": matching_chunks[0].governing_equation
            })
    
    # 2. 因果链提取
    for chunk in filter_causal_chains(knowledge_chunks):
        # 解析 "A → B → C" 格式的因果链
        ontology["relationships"].append({
            "from": chunk.chain.from_param,
            "to": chunk.chain.to_param,
            "mechanism": chunk.chain.mechanism,
            "confidence": chunk.source_confidence,
            "source": chunk.source_type
        })
    
    # 3. 混杂变量识别
    for chunk in filter_confounders(knowledge_chunks):
        ontology["confounders"].append({
            "variable": chunk.confounder.variable,
            "why": chunk.confounder.rationale,
            "controlled": False
        })
    
    return ontology
```

### 7.3 `ontology_draft.json` 格式

```json
{
  "scene": {
    "process_type": "CNC machining",
    "equipment": [
      {"name": "主轴 (Spindle)", "type": "rotating_equipment",
       "function": "驱动刀具旋转进行切削加工",
       "mechanisms": ["轴承磨损 → 振动↑", "温升 → 热膨胀 → 尺寸偏差"],
       "knowledge_source": "parameter_to_physics.json"}
    ]
  },
  "signals": {
    "process_parameters": [
      {"column": "spindle_vibration_mm_s",
       "inferred_meaning": "主轴振动速度 RMS 值",
       "governing_law": "ISO 10816-1 振动严重度分类",
       "normal_range": [0, 4.5],
       "thresholds": {"warning": 4.5, "critical": 11.2},
       "knowledge_confidence": 0.95,
       "knowledge_source": "parameter_to_physics.json (local_reference)"},
      {"column": "spindle_temp_C",
       "inferred_meaning": "主轴轴承温度",
       "governing_law": "ΔT = P_loss × t / (m × Cp)",
       "normal_range": [20, 60],
       "knowledge_confidence": 0.90,
       "knowledge_source": "parameter_to_physics.json"}
    ]
  },
  "relationships": [
    {"from": "spindle_vibration_mm_s",
     "to": "surface_roughness_Ra_um",
     "physical_mechanism": "轴承磨损→旋转不平衡→振动↑→刀尖位移→表面波纹→Ra↑",
     "governing_equation": "Ra ≈ fz²/(8×rε)",
     "knowledge_confidence": 0.95,
     "knowledge_source": "parameter_to_physics.json"}
  ],
  "confounders": [
    {"variable": "material",
     "why": "不同材料(AL7075/AL6061/SS304)有不同的加工参数范围",
     "should_control": true,
     "knowledge_confidence": 0.85,
     "knowledge_source": "process_knowledge_base.md"}
  ],
  "auto_ontology_summary": {
    "total_columns": 14,
    "columns_matched_to_knowledge": 11,
    "columns_without_knowledge": 3,
    "causal_chains_retrieved": 7,
    "confounders_identified": 2,
    "physical_checks_available": ["thermal_expansion", "vibration_threshold",
                                   "force_balance"]
  }
}
```

---

## 8. 结构化知识封装 — 为诊断推理提供物理依据

### 8.1 增强的 `extracted_knowledge.json`

当前版本只记录参考文档的文本提取。RAG 增强后，加入**程序化可消费的物理依据**：

```json
{
  "version": "2.0-rag",
  "source_files": [...],
  "equipment": [...],
  "process_stages": [...],
  
  "=== NEW RAG FIELDS ===": "",
  
  "rag_retrieval_summary": {
    "retrieval_timestamp": "2026-06-01T10:00:00Z",
    "total_knowledge_chunks_retrieved": 10,
    "chunks_from_local_references": 7,
    "chunks_from_web": 2,
    "chunks_from_accumulated_diagnostics": 1,
    "retrieval_quality_score": 0.87,
    "knowledge_gaps_after_retrieval": 3
  },
  
  "physical_mechanisms": [
    {
      "id": "pm_001",
      "name": "轴承磨损→振动→粗糙度退化",
      "applicable_params": ["spindle_vibration_mm_s", "surface_roughness_Ra_um"],
      "applicable_processes": ["CNC_machining"],
      "causal_chain": "轴承磨损 → 旋转不平衡 → 振动↑ → 刀尖位移 → 表面波纹 → Ra↑",
      "governing_equation": "Ra ≈ fz²/(8×rε); ΔRa_data = 振动振幅 × 刀具刚度倒数",
      "quantitative_verification": {
        "physical_check": "vibration_threshold",
        "threshold": "ISO 10816 Zone C > 4.5mm/s",
        "expected_behavior": "超过阈值时粗糙度指数级上升"
      },
      "competing_mechanisms": [
        {"name": "刀具磨损→粗糙度↑",
         "discriminator": "换刀后粗糙度是否重置？Resets→H1; No reset→H2"}
      ],
      "knowledge_confidence": 0.95,
      "knowledge_source": "parameter_to_physics.json"
    },
    {
      "id": "pm_002",
      "name": "热膨胀→尺寸偏差",
      "applicable_params": ["spindle_temp_C", "thermal_deviation_mm"],
      "causal_chain": "温度↑ → 主轴热膨胀 → 刀具相对位置偏移 → 尺寸偏差",
      "governing_equation": "ΔL = α × L₀ × ΔT; α_steel ≈ 12×10⁻⁶/K",
      "quantitative_verification": {
        "physical_check": "thermal_expansion",
        "ratio_threshold": "predicted/observed ∈ [0.5, 2.0] → PLAUSIBLE"
      },
      "knowledge_confidence": 0.90,
      "knowledge_source": "process_knowledge_base.md"
    }
  ],
  
  "confounders_known": [
    {
      "name": "材料类型 (material)",
      "mechanism": "不同材料硬度不同→相同的刀具磨损程度产生不同的粗糙度",
      "applicable_params": ["material", "surface_roughness_Ra_um"],
      "analysis_required": "stratified by material before claiming universal correlation",
      "knowledge_confidence": 0.85
    }
  ],
  
  "knowledge_gaps": [
    "无主轴轴承的具体型号数据 → 无法精确计算轴承寿命",
    "无切削液配方 → 无法判断冷却效率是否下降",
    "无刀具涂层信息 → 无法精确预测换刀周期"
  ]
}
```

### 8.2 诊断阶段如何使用这些结构

```
                                        ┌────────────────────────────┐
                                        │  extracted_knowledge.json  │
                                        │  (RAG-enhanced v2)         │
                                        └──────────┬─────────────────┘
                                                   │
         ┌─────────────────────────────────────────┼──────────────────────────┐
         ▼                                         ▼                          ▼
┌──────────────────┐                   ┌────────────────────┐    ┌────────────────────┐
│ Diagnostician    │                   │ physics_check.py   │    │ Report Reviewer    │
│ (Step 4)         │                   │ (Step 3.5)         │    │ (Step 7)           │
├──────────────────┤                   ├────────────────────┤    ├────────────────────┤
│ physical_mechanisms  │                │ quantitative_checks │    │ confounders_known  │
│ ② 用预存的causal_chain│                │ ③ 从governing_eq     │    │ ⑤ 验证是否控制了   │
│    替换手工推理       │                │    提取计算参数       │    │    已知混杂变量    │
│ ④ 用competing_mechan│                │    自动运行物理验证   │    │                      │
│    isms 初始化假设    │                │                      │    │                      │
└──────────────────┘                   └────────────────────┘    └────────────────────┘
```

---

## 9. 跨运行知识积累

### 9.1 积累规则

```
每次诊断完成 → 检查是否应积累到 KB:

                     ┌─────────────┐
                     │ Judge ≥ 90? │──No──→ 丢弃，不积累
                     └──────┬──────┘
                            │ Yes
                            ▼
                     ┌───────────────────────┐
                     │ Physical Audit        │
                     │ (optimizer.md)        │
                     │ ENDORSED?             │──No──→ 标记为 LOW_CONFIDENCE
                     └──────┬────────────────┘
                            │ Yes
                            ▼
                     ┌───────────────────────┐
                     │ 提取为 knowledge_chunk │
                     │ · root_cause → chunk  │
                     │ · validation 检查通过 │
                     │   (Simpson ✓trend ✓)  │
                     │ · 标注 verified_by=   │
                     │   run_id              │
                     └──────┬────────────────┘
                            │
                            ▼
                     ┌───────────────────────┐
                     │ kb_build.py --upsert   │
                     │ → 写入 ChromaDB       │
                     │ → 未来诊断可直接检索  │
                     └───────────────────────┘
```

### 9.2 积累质量门控

| 门控 | 条件 | 动作 |
|------|------|------|
| G1 | Judge ≥ 90 且 审计=ENDORSED | 直接积累，confidence=0.90 |
| G2 | Judge ≥ 80 或 审计=CONDITIONAL | 积累但 confidence=0.60，标记为需验证 |
| G3 | Judge < 80 或 审计=REJECTED | 不积累 |
| G4 | 已存在相同 chunk_id | 比较 confidence，保留较高者 |

---

## 10. 新增文件清单

```
.claude/skills/industrial-deep-diagnostic/
├── knowledge_base/                          ← NEW: 向量存储
│   ├── chroma_db/                           ChromaDB 持久化
│   └── collection_manifest.json             集合版本管理
│
├── scripts/
│   ├── kb_build.py                          ← NEW: 注入管道
│   ├── kb_retrieve.py                       ← NEW: 检索管道
│   └── kb_schema.py                         ← NEW: Chunk 数据模型
│
├── agents/
│   └── context-builder.md                   ← ENHANCED: RAG 集成
│
├── resources/
│   └── rag_architecture_design.md           ← THIS FILE: 架构文档
│
├── schemas/
│   ├── knowledge_chunk_schema.json          ← NEW: Chunk schema
│   └── ontology_draft_schema.json           ← NEW: 自动本体草稿 schema
│
├── requirements-rag.txt                     ← NEW: RAG 依赖
│   # sentence-transformers
│   # chromadb
│   # nltk
```

---

## 11. 实施路线图

### Phase 1: 基础设施（3-5 天）
```
1. 创建 kb_schema.py — Chunk 数据模型 + 序列化
2. 创建 requirements-rag.txt — sentence-transformers + chromadb
3. 创建 knowledge_base/ 目录结构 + collection_manifest.json
4. 实现 kb_build.py --init: 索引所有静态资源
5. 编写单元测试: 索引 → 检索 → 验证
```

### Phase 2: 检索集成（2-3 天）
```
1. 实现 kb_retrieve.py: 场景感知检索
2. 实现多查询扩展 (4 perspectives)
3. 实现混合重排序 (dense + BM25 + MMR)
4. 集成到 Step 2 - context-builder: 在参考文档搜索前执行检索
5. 输出 knowledge_chunks.json
```

### Phase 3: 自动本体构建（3-4 天）
```
1. 实现 auto_ontology_draft() 算法
2. 实现 ontology_draft.json → 传递给 LLM 进行精修
3. 实现 knowledge_chunks.json → physical_mechanisms 提取
4. 更新 context-builder.md Step 3 流程
5. 更新 ontology_schema.json (新增 knowledge_confidence 字段)
```

### Phase 4: 跨运行积累（2-3 天）
```
1. 实现 kb_build.py --accumulate: 诊断结果提取
2. 实现质量门控 (G1-G4)
3. 实现 kb_build.py --rebuild: 全量重建
4. 添加运行完成后钩子 (Step 8 → accumulate)
5. 集成到 pipeline-execution.md
```

---

## 12. 与现有技能的兼容性

| 现有组件 | 影响 | 向后兼容 |
|----------|------|:--------:|
| SKILL.md | 新增 RAG 步骤通知 | ✅ 不影响现有 Step 编号 |
| context-builder.md | Step 2 之前新增检索步骤 | ✅ 完全向后兼容 |
| pipeline-execution.md | 新增 Step 2.1 描述 | ✅ 按加载指导有条件加载 |
| schema 文件 | 新增 *draft*.json schema | ✅ 不影响现有 validation |
| evals | 新增 RAG 测试场景 | ✅ 增强，不破坏 |
| `interaction_mode` | auto/minimal 在有RAG时更快 | ✅ 自动模式下减少联网次数 |
