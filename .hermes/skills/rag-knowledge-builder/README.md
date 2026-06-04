# RAG Knowledge Builder Skill

这是一个**本体优先**的知识构建 Skill。它的目标不是简单检索，而是把检索到的知识组织成一个**可供下游 Skill 直接消费的领域本体模型**。

## Skill 定位

当任务需要：
- 构建领域本体
- 形成概念层次和关系图谱
- 从 RAG 检索结果中提炼结构化知识
- 为下游诊断/分析 Skill 提供领域语义支撑

就应该使用这个 Skill。

## 这个 Skill 输出什么

它会输出一组本体相关工件：
- `rag_ontology_draft.json`：结构化本体
- `rag_ontology_nl_spec.md`：人类可读自然语言规范
- `rag_structured_data.json`：机器消费模板
- `rag_scored_chunks.json`：检索块与评分结果
- `rag_audit_log.json`：质量审查日志
- `rag_clarification_needed.json`：待澄清概念

## 标准执行流程

### Phase 0：Engine Startup
- 启动或检查 `rag-retrieval-engine`

### Phase 1：Knowledge Collection
- 本地知识库检索
- 可选 Web 检索
- 检索块评分与筛选

### Phase 2：Ontology Construction
- 领域理解
- 概念定义
- 层次关系构建
- 约束与术语映射
- 输出 JSON + Markdown 双版本本体

### Phase 3：Structured Data Generation
- 生成查询模板、验证规则、结构化模板

### Phase 4：Quality Verification
- 检查本体完整性、一致性、可追溯性与下游可用性

## 与诊断 Skill 的关系

这个 Skill 通常作为：
- `industrial-deep-diagnostic` 的上游知识构建模块
- 或者独立的领域知识准备模块

关系是：
```text
RAG Engine -> RAG Knowledge Builder Skill -> Industrial Deep Diagnostic Skill
```

## 优势

- 本体优先，而不是“搜索结果堆砌”
- 同时面向机器和人类输出
- 可作为多个下游 Skill 的语义基础设施
- 领域无关，可复用于工业、医学、法律、科研等场景

## 典型用途

- 为工业诊断构建领域本体
- 为复杂问答系统构建术语与关系图谱
- 为数据分析系统提供概念字典与因果语义支撑

## 关键入口

- 主协议：`SKILL.md`
- 输出目录：通常写入 `run_dir/00_input/`
- 引擎服务：见 `rag-retrieval-engine/README.md`
