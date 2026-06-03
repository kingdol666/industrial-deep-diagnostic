# Repository Layout

## 顶层目录职责

- `app/`：应用实现（前后端）
- `commands/`：CLI 入口与启动脚本
- `config/`：项目配置
- `data/`：样例数据、评测数据、参考资料
- `docs/`：项目说明文档
- `rag-retrieval-engine/`：RAG HTTP 服务
- `workspace/`：主要运行产物目录
- `runs/`：额外历史实验/独立运行目录
- `.claude/skills/`：项目内 Skill 定义

## 特殊目录说明

### `workspace/`
面向日常运行的正式输出目录：
- `workspace/diagnostic-runs/`
- `workspace/rag-outputs/`
- `workspace/bridge-runs/`

### `runs/`
保留历史实验性或特定场景运行产物，不作为主输出目录。

### `garden-gpt-image-2/` 与 `ppt_workspace/`
当前属于辅助素材 / 历史实验资产，不是诊断主链路的一部分。后续如长期保留，建议进一步归档到独立 `experiments/` 或 `tools/` 体系。
