# Shared Resources — Industrial Deep Diagnostic

项目级共享目录。所有 skill 通过 `$SHARED_PATH` 环境变量引用此目录。

## Path Convention

```
SHARED_PATH=<project-root>/.omp/shared
```

Agent prompt 模板中注入：
```
SHARED_PATH=<project-root>/.omp/shared
```

## Directory Structure

```
shared/
├── schemas/        ← 16 JSON Schema (draft-07)，唯一权威副本
├── scripts/        ← 4 个共享 Node.js 脚本
└── README.md       ← 本文件
```

## Shared Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `validate.mjs` | JSON Schema 验证 | `node "$SHARED_PATH/scripts/validate.mjs" <schema.json> <data.json>` |
| `append-pipeline-event.mjs` | 管道事件日志追加 | `node "$SHARED_PATH/scripts/append-pipeline-event.mjs" <RUN_DIR> --event <event> ...` |
| `uv_env_setup.mjs` | Python uv venv 初始化 | `node "$SHARED_PATH/scripts/uv_env_setup.mjs"` |
| `convert.mjs` | CSV/TSV → JSON 转换 | `node "$SHARED_PATH/scripts/convert.mjs" <file> --output out.json` |

## Design Principle

- 每个文件只有一份。修改一处，全局生效。
- 不在此目录存放 skill 特有脚本。
- Schema 以 `.omp/skills/industrial-analysis-auto/schemas/` 为权威源。
