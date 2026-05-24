# CLI-Driven & Config-Driven Architecture

> **Status:** Approved | **Date:** 2026-05-24

## Goal

Transform the project into a production-quality CLI-driven application with centralized configuration, automatic startup initialization, CLI-based config management, and global binary registration.

## Architecture

```
commands/cli.mjs (bin: ind-diag)
    │
    ├── init          → config/loader.mjs + app/backend/src/db.mjs
    ├── config *      → config/loader.mjs + config/local.yaml
    ├── backend       → app/backend/src/index.mjs (auto-init on start)
    ├── frontend      → app/frontend/vite.config.js
    ├── all           → backend + frontend
    ├── build         → npm run build (frontend)
    ├── status        → read-only project info
    └── help
```

Single config entry point: `config/loader.mjs` — shared by CLI and backend. CLI never duplicates config logic.

## Components

### 1. CLI Commands

```
ind-diag <command> [args]

init                  Initialize project (check DB, config, deps)
config list           Print merged config (default + local + env)
config get <key>      Read single key (dot-path: server.port)
config set <key> <v>  Write to config/local.yaml (deep-merge)
config reset <key>    Remove key from local.yaml, restore default
config path           Print paths to default.yaml and local.yaml
backend               Start backend (auto-init before listen)
frontend              Start Vite dev server
all                   Start backend + frontend
build                 Build frontend for production
status                Project status overview
help                  Usage help
```

### 2. Startup Initialization (backend/all commands)

```
load config/loader.mjs
    │
    ├── default.yaml missing  → FATAL: "config/default.yaml not found"
    ├── parse error            → FATAL: print parse error, exit
    └── OK → merged config in memory
              │
              ├── DB file missing → CREATE TABLE IF NOT EXISTS (idempotent)
              ├── DB exists       → run CREATE TABLE IF NOT EXISTS (safe)
              └── migration       → ALTER TABLE add columns if missing (try/catch)
              │
              ├── Mark stale 'running' runs as interrupted
              └── Start HTTP server
```

All init steps are idempotent. Users never need to manually init — backend auto-inits.

### 3. Config Management

- `config set server.port 9090` writes to `config/local.yaml`
- `config get server.port` reads from merged config (default + local + env)
- `config reset server.port` removes the key from `local.yaml`
- `config list` prints the full merged config as YAML
- `local.yaml` is .gitignore'd — user settings stay local

### 4. Package Binary Registration

```json
{
  "name": "industrial-deep-diagnostic",
  "bin": {
    "ind-diag": "./commands/cli.mjs"
  }
}
```

After `npm link` in project root, `ind-diag` available globally.

### 5. Production Build

- `ind-diag build` runs `vite build` in frontend
- `ind-diag backend` serves built frontend from `app/frontend/dist/`
- Express static middleware serves dist; SPA fallback handles client-side routing

## Files Changed

| File | Action | Purpose |
|------|--------|---------|
| `package.json` | Modify | Add `bin` field, update `name`, add scripts |
| `commands/cli.mjs` | Rewrite | Full CLI with init/config/backend/frontend/all/build/status |
| `config/loader.mjs` | Modify | Add `setKey()`, `removeKey()`, `writeLocalYaml()` helpers |
| `app/backend/src/index.mjs` | Modify | Extract init logic; auto-init on startup |
| `app/backend/src/db.mjs` | Modify | Export `initDB()` function for explicit initialization |
| `.gitignore` | Modify | Add `config/local.yaml` |

## Verification

1. `ind-diag help` — prints usage
2. `ind-diag config list` — prints merged config
3. `ind-diag config set server.port 9090` — writes local.yaml, `ind-diag config get server.port` → 9090
4. `ind-diag config reset server.port` — removes from local.yaml, port back to 3210
5. `ind-diag backend` — auto-inits DB, starts server on configured port
6. `ind-diag build` — builds frontend, `ind-diag backend` serves it
7. All 10 API tests pass after build
8. `npm link && ind-diag status` works from any directory
