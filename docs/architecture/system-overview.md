# System Overview

## 系统分层

当前项目由 4 个主要层次组成：

1. **Application Layer**
   - `app/backend/`
   - `app/frontend/`
   - `commands/`
   - `config/`

2. **Skill Layer**
   - `.claude/skills/industrial-deep-diagnostic/`
   - `.claude/skills/rag-knowledge-builder/`

3. **Knowledge Service Layer**
   - `rag-retrieval-engine/`

4. **Data & Artifact Layer**
   - `data/`
   - `workspace/`
   - `runs/`

## 核心协作关系

```text
WebUI / CLI
   -> backend orchestration
   -> industrial-deep-diagnostic skill
      -> rag-knowledge-builder skill
         -> rag-retrieval-engine
```

## 设计原则

- 应用层负责交互与运行管理
- Skill 层负责智能工作流与结构化产物
- RAG 服务层负责知识检索基础设施
- 数据与产物层负责输入数据、运行日志与结果沉淀
