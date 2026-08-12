# Shared Resources — Industrial Deep Diagnostic

项目级共享目录。所有 skill 通过 `$SHARED_PATH` 环境变量引用此目录。

## Path Convention

```
SHARED_PATH=<project-root>/.claude/shared
```

Agent prompt 模板中注入：
```
SHARED_PATH=<project-root>/.claude/shared
```

## Directory Structure

```
shared/
├── schemas/        ← 28 JSON Schema (draft-07)，唯一权威副本
├── scripts/        ← 9 个共享 Node.js 脚本 + 1 个 Python 脚本 (vlm_image_reader.py)
└── README.md       ← 本文件
```

## Shared Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `validate.mjs` | JSON Schema 验证 | `node "$SHARED_PATH/scripts/validate.mjs" <schema.json> <data.json>` |
| `append-pipeline-event.mjs` | 管道事件日志追加 + manifest 同步 | `node "$SHARED_PATH/scripts/append-pipeline-event.mjs" <RUN_DIR> --event <event> ...` |
| `uv_env_setup.mjs` | Python 共享 venv 初始化 (Windows: Scripts/python.exe, POSIX: bin/python) | `node "$SHARED_PATH/scripts/uv_env_setup.mjs"` |
| `convert.mjs` | CSV/TSV → JSON 转换 (BOM 自动剥离) | `node "$SHARED_PATH/scripts/convert.mjs" <file> --output out.json` |
| `verify-agents.mjs` | Agent frontmatter + VLM dispatch chain 验证 | `node "$SHARED_PATH/scripts/verify-agents.mjs"` |
| `master-validate.mjs` | 仓库健康综合检查 (schemas + agents + skills + CP gates) | `node "$SHARED_PATH/scripts/master-validate.mjs"` |
| `smoke-test-agents.mjs` | Agent spawn + 模型 + VLM 链冒烟测试 | `node "$SHARED_PATH/scripts/smoke-test-agents.mjs"` |
| `e2e-pipeline-test.mjs` | 端到端管线全流程冒烟测试 (Step 0-9 + E1-E8) | `node "$SHARED_PATH/scripts/e2e-pipeline-test.mjs"` |
| `vlm_image_reader.py` | VLM 视觉模型直调 (PNG/JPEG → 结构化分析) | `uv run --project "$SHARED_PATH/scripts" python "$SHARED_PATH/scripts/vlm_image_reader.py" <image> [question]` |

## Design Principle

- 每个文件只有一份。修改一处，全局生效。
- 不在此目录存放 skill 特有脚本。
- Schema 以 `.claude/shared/schemas/` 为唯一权威副本，各 skill 的 `schemas/` 目录为同步副本。
