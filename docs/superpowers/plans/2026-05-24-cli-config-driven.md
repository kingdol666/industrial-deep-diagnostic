# CLI-Driven & Config-Driven Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the project into a production-quality CLI-driven application with automatic startup initialization, CLI-based config management, and global binary registration.

**Architecture:** `config/loader.mjs` is the single config entry point shared by CLI and backend. CLI commands (`ind-diag init|config|backend|frontend|all|build|status`) operate through loader helpers. Backend auto-inits DB and config on startup. `package.json` `bin` field maps `ind-diag` to `commands/cli.mjs`.

**Tech Stack:** Node.js ESM, js-yaml, better-sqlite3, Express, Vue 3 + Vite

---

## File Map

| File | Role |
|------|------|
| `config/loader.mjs` | Config loading, deep-merge, env override, YAML read/write helpers |
| `commands/cli.mjs` | CLI entry point — all user-facing commands |
| `app/backend/src/db.mjs` | SQLite init, migrations, prepared statements |
| `app/backend/src/index.mjs` | Express server bootstrap with auto-init |
| `package.json` | Project metadata, bin alias, scripts |
| `.gitignore` | Ignore local.yaml and build artifacts |

---

### Task 1: Add Config Write Helpers to loader.mjs

**Files:**
- Modify: `config/loader.mjs`

- [ ] **Step 1: Add `getKey(obj, dotPath)` helper**

In `config/loader.mjs`, add after the `deepMerge` function:

```javascript
// Get a nested value by dot-path: "server.port" → config.server.port
function getKey(obj, dotPath) {
  const keys = dotPath.split('.');
  let current = obj;
  for (const k of keys) {
    if (current == null || typeof current !== 'object') return undefined;
    current = current[k];
  }
  return current;
}
```

- [ ] **Step 2: Add `setKey(obj, dotPath, value)` helper**

Add after `getKey`:

```javascript
// Set a nested value by dot-path, creating intermediate objects as needed
function setKey(obj, dotPath, value) {
  const keys = dotPath.split('.');
  let current = obj;
  for (let i = 0; i < keys.length - 1; i++) {
    if (!current[keys[i]] || typeof current[keys[i]] !== 'object') {
      current[keys[i]] = {};
    }
    current = current[keys[i]];
  }
  current[keys[keys.length - 1]] = value;
  return obj;
}
```

- [ ] **Step 3: Add `removeKey(obj, dotPath)` helper**

Add after `setKey`:

```javascript
// Remove a nested key by dot-path
function removeKey(obj, dotPath) {
  const keys = dotPath.split('.');
  let current = obj;
  for (let i = 0; i < keys.length - 1; i++) {
    if (current == null || typeof current[keys[i]] !== 'object') return obj;
    current = current[keys[i]];
  }
  if (current && typeof current === 'object') {
    delete current[keys[keys.length - 1]];
  }
  return obj;
}
```

- [ ] **Step 4: Add `saveLocalYaml(configObj)` helper**

Add after `removeKey`. Uses `js-yaml` dump:

```javascript
import { dump } from 'js-yaml';
import { writeFileSync, mkdirSync } from 'fs';

const LOCAL_YAML_PATH = join(__dirname, 'local.yaml');

function saveLocalYaml(configObj) {
  const yaml = dump(configObj, { indent: 2, lineWidth: 120, noRefs: true });
  writeFileSync(LOCAL_YAML_PATH, yaml, 'utf-8');
}
```

- [ ] **Step 5: Add `loadLocalYaml()` helper**

Add after `saveLocalYaml`:

```javascript
function loadLocalYaml() {
  return loadYAML(LOCAL_YAML_PATH);
}
```

- [ ] **Step 6: Export the new helpers**

Update the export block at the bottom to include:

```javascript
export { getKey, setKey, removeKey, saveLocalYaml, loadLocalYaml };
```

- [ ] **Step 7: Verify syntax**

Run: `cd /Volumes/laxer/codes/skills/ industrial-deep-diagnostic && node --check config/loader.mjs`
Expected: no output

---

### Task 2: Export Explicit initDB from db.mjs

**Files:**
- Modify: `app/backend/src/db.mjs`

- [ ] **Step 1: Wrap table creation in `initDB()` function, export it**

In `db.mjs`, the `db.exec(CREATE TABLE ...)` runs at module load. Keep that but also export a named `initDB` function that runs the same SQL idempotently and logs progress:

```javascript
export function initDB() {
  console.log('[DB] Initializing database...');
  console.log(`[DB] Path: ${DB_PATH}`);

  db.exec(`
    CREATE TABLE IF NOT EXISTS diagnostic_runs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      run_id TEXT NOT NULL UNIQUE,
      name TEXT NOT NULL,
      scene_name TEXT NOT NULL,
      data_path TEXT NOT NULL,
      data_folder TEXT,
      user_question TEXT,
      status TEXT DEFAULT 'pending',
      session_id TEXT,
      workspace_path TEXT,
      report_path TEXT,
      score INTEGER,
      judge_verdict TEXT,
      error_message TEXT,
      model TEXT DEFAULT '${config.claude.model}',
      max_turns INTEGER DEFAULT ${config.claude.max_turns},
      created_at TEXT DEFAULT (datetime('now')),
      updated_at TEXT DEFAULT (datetime('now')),
      completed_at TEXT
    );

    CREATE TABLE IF NOT EXISTS diagnosis_logs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      run_id TEXT NOT NULL,
      role TEXT NOT NULL,
      content TEXT,
      message_type TEXT DEFAULT 'text',
      tool_name TEXT,
      created_at TEXT DEFAULT (datetime('now')),
      FOREIGN KEY (run_id) REFERENCES diagnostic_runs(run_id)
    );

    CREATE TABLE IF NOT EXISTS data_folders (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL UNIQUE,
      path TEXT NOT NULL,
      description TEXT,
      file_count INTEGER DEFAULT 0,
      created_at TEXT DEFAULT (datetime('now'))
    );
  `);

  // Migration: add report_language column if missing
  try {
    db.exec(`ALTER TABLE diagnostic_runs ADD COLUMN report_language TEXT DEFAULT '${config.diagnosis.default_language}'`);
  } catch {}

  console.log('[DB] Database initialized successfully.');
}
```

- [ ] **Step 2: Verify syntax**

Run: `cd /Volumes/laxer/codes/skills/ industrial-deep-diagnostic && node --check app/backend/src/db.mjs`
Expected: no output

---

### Task 3: Add Auto-Init to index.mjs

**Files:**
- Modify: `app/backend/src/index.mjs`

- [ ] **Step 1: Add `initialize()` function with logging**

Add before the `createServer` call. The function validates config, inits DB, and marks stale runs:

```javascript
import { initDB } from './db.mjs';
import { existsSync } from 'fs';
import { join } from 'path';

async function initialize() {
  console.log('[Init] Checking project configuration...');

  // Verify default.yaml exists
  const defaultYamlPath = join(PROJECT_ROOT, 'config', 'default.yaml');
  if (!existsSync(defaultYamlPath)) {
    console.error('[Init] FATAL: config/default.yaml not found');
    console.error('[Init] Run: ind-diag init');
    process.exit(1);
  }
  console.log(`[Init] Config loaded from: ${defaultYamlPath}`);

  // Init database (idempotent)
  initDB();

  // Mark stale runs as interrupted
  const staleRuns = stmts.getActiveRuns.all();
  if (staleRuns.length > 0) {
    for (const run of staleRuns) {
      stmts.failRun.run({ runId: run.run_id, error: 'Server restarted — diagnosis interrupted' });
      console.log(`[Init] Marked stale run as interrupted: ${run.run_id}`);
    }
  }

  console.log('[Init] Initialization complete.');
}
```

- [ ] **Step 2: Call initialize() before server.listen**

Wrap the server start:

```javascript
initialize().then(() => {
  server.listen(PORT, () => {
    console.log(`[Industrial Diagnostic API] HTTP + WebSocket server on http://localhost:${PORT}`);
    console.log(`[Industrial Diagnostic API] WebSocket endpoint: ws://localhost:${PORT}/ws`);
    console.log(`[Industrial Diagnostic API] Project root: ${PROJECT_ROOT}`);
    console.log(`[Industrial Diagnostic API] Data dir: ${join(PROJECT_ROOT, 'data')}`);
  });
}).catch(err => {
  console.error('[Init] Failed to start:', err.message);
  process.exit(1);
});
```

- [ ] **Step 3: Remove old top-level stale-run marking and listen call**

Delete the old `staleRuns` loop and `server.listen()` at the bottom of the file (they're now inside `initialize()`).

- [ ] **Step 4: Verify syntax**

Run: `cd /Volumes/laxer/codes/skills/ industrial-deep-diagnostic && node --check app/backend/src/index.mjs`
Expected: no output

---

### Task 4: Rewrite commands/cli.mjs — Full CLI

**Files:**
- Modify: `commands/cli.mjs`

This is the largest task. The file needs a complete rewrite.

- [ ] **Step 1: Write the new CLI skeleton**

Replace the entire `commands/cli.mjs` content with:

```javascript
#!/usr/bin/env node
import { spawn } from 'child_process';
import { join } from 'path';
import { existsSync, readdirSync } from 'fs';
import {
  PROJECT_ROOT, config,
  getKey, setKey, removeKey, saveLocalYaml, loadLocalYaml,
  server as serverConfig, frontend as frontendConfig
} from '../config/loader.mjs';

const BACKEND_DIR = join(PROJECT_ROOT, 'app', 'backend');
const FRONTEND_DIR = join(PROJECT_ROOT, 'app', 'frontend');
const BACKEND_PORT = serverConfig.port;
const FRONTEND_PORT = frontendConfig.port;

// ─── Helpers ────────────────────────────────────────────────

function printBanner() {
  console.log('');
  console.log('  ╔══════════════════════════════════════════════╗');
  console.log('  ║   Industrial Deep Diagnostic — CLI v1.0       ║');
  console.log('  ╚══════════════════════════════════════════════╝');
  console.log('');
}

function printUsage() {
  printBanner();
  console.log('  Usage: ind-diag <command> [options]');
  console.log('');
  console.log('  Commands:');
  console.log('    init                  Initialize project (check DB, config)');
  console.log('    config                 Manage configuration');
  console.log('      config list          Show merged configuration');
  console.log('      config get <key>     Get a config value (e.g. server.port)');
  console.log('      config set <key> <v> Set a config value, saves to local.yaml');
  console.log('      config reset <key>   Remove a key from local.yaml');
  console.log('      config path          Show config file paths');
  console.log(`    backend               Start backend server (port ${BACKEND_PORT})`);
  console.log(`    frontend              Start frontend dev server (port ${FRONTEND_PORT})`);
  console.log('    all                   Start backend + frontend');
  console.log('    build                 Build frontend for production');
  console.log('    status                Project status overview');
  console.log('    help                  Show this help');
  console.log('');
  console.log('  Examples:');
  console.log('    ind-diag all');
  console.log('    ind-diag config set server.port 9090');
  console.log('    ind-diag config get server.port');
  console.log('');
}

async function runCommand(cmd, args, cwd) {
  return new Promise((resolve, reject) => {
    const child = spawn(cmd, args, { cwd, stdio: 'inherit', shell: true });
    child.on('close', (code) => {
      if (code === 0) resolve();
      else reject(new Error(`${cmd} exited with code ${code}`));
    });
    child.on('error', reject);
  });
}

function checkDeps(dir, name) {
  if (!existsSync(join(dir, 'node_modules'))) {
    console.log(`\n  [INSTALL] Installing ${name} dependencies...`);
    return runCommand('npm', ['install'], dir);
  }
  console.log(`  [OK] ${name} dependencies found`);
  return Promise.resolve();
}

function parseValue(raw) {
  if (raw === 'true') return true;
  if (raw === 'false') return false;
  if (raw === 'null') return null;
  if (/^-?\d+$/.test(raw)) return parseInt(raw, 10);
  if (/^-?\d+\.\d+$/.test(raw)) return parseFloat(raw);
  return raw;
}

// ─── Commands ───────────────────────────────────────────────

async function cmdInit() {
  console.log('\n  Initializing Industrial Deep Diagnostic...\n');

  const defaultYaml = join(PROJECT_ROOT, 'config', 'default.yaml');
  if (!existsSync(defaultYaml)) {
    console.error('  [ERROR] config/default.yaml not found!');
    console.error('  The project appears to be corrupted. Please re-clone the repository.');
    process.exit(1);
  }
  console.log(`  [OK] Config: ${defaultYaml}`);

  const localYaml = join(PROJECT_ROOT, 'config', 'local.yaml');
  if (existsSync(localYaml)) {
    console.log(`  [OK] Local config: ${localYaml}`);
  } else {
    console.log('  [--] No local config (using defaults)');
  }

  // Init DB via backend module
  try {
    const { initDB } = await import('../app/backend/src/db.mjs');
    initDB();
  } catch (err) {
    console.error(`  [ERROR] Database init failed: ${err.message}`);
    process.exit(1);
  }

  console.log('\n  Initialization complete. Run: ind-diag all');
}

function cmdConfigList() {
  const { dump } = await_import('js-yaml');
  const output = dump(config, { indent: 2, lineWidth: 120, noRefs: true });
  console.log(output);
}

function cmdConfigGet(key) {
  const value = getKey(config, key);
  if (value === undefined) {
    console.error(`Key not found: ${key}`);
    process.exit(1);
  }
  if (typeof value === 'object') {
    const { dump } = require_import('js-yaml');
    console.log(dump(value, { indent: 2, lineWidth: 120, noRefs: true }));
  } else {
    console.log(value);
  }
}

function cmdConfigSet(key, rawValue) {
  const value = parseValue(rawValue);
  const local = loadLocalYaml();
  setKey(local, key, value);
  saveLocalYaml(local);
  console.log(`Set ${key} = ${JSON.stringify(value)} (saved to config/local.yaml)`);
}

function cmdConfigReset(key) {
  const local = loadLocalYaml();
  const current = getKey(local, key);
  if (current === undefined) {
    console.log(`Key "${key}" is not set in local.yaml (already using default)`);
    return;
  }
  removeKey(local, key);
  saveLocalYaml(local);
  const defaultValue = getKey(config, key);
  console.log(`Reset ${key} (default: ${JSON.stringify(defaultValue)})`);
}

function cmdConfigPath() {
  console.log(`  Default config: ${join(PROJECT_ROOT, 'config', 'default.yaml')}`);
  const localPath = join(PROJECT_ROOT, 'config', 'local.yaml');
  console.log(`  Local config:   ${localPath} ${existsSync(localPath) ? '(exists)' : '(not created)'}`);
}

async function cmdBackend() {
  console.log('\n  Starting Express API server...');
  await checkDeps(BACKEND_DIR, 'backend');
  console.log(`  Backend: http://localhost:${BACKEND_PORT}`);
  console.log(`  Project root: ${PROJECT_ROOT}`);
  console.log('');
  return runCommand('node', ['src/index.mjs'], BACKEND_DIR);
}

async function cmdFrontend() {
  console.log('\n  Starting Vue dev server...');
  await checkDeps(FRONTEND_DIR, 'frontend');
  console.log(`  Frontend: http://localhost:${FRONTEND_PORT}`);
  console.log('');
  return runCommand('npx', ['vite', '--host'], FRONTEND_DIR);
}

async function cmdAll() {
  printBanner();
  console.log('  Starting full stack...');
  console.log(`  Backend:  http://localhost:${BACKEND_PORT}`);
  console.log(`  Frontend: http://localhost:${FRONTEND_PORT}`);
  console.log('');

  await checkDeps(BACKEND_DIR, 'backend');
  await checkDeps(FRONTEND_DIR, 'frontend');

  const backend = spawn('node', ['src/index.mjs'], { cwd: BACKEND_DIR, stdio: 'inherit', shell: true });
  await new Promise(r => setTimeout(r, 1500));

  const frontend = spawn('npx', ['vite', '--host'], { cwd: FRONTEND_DIR, stdio: 'inherit', shell: true });

  const cleanup = () => { backend.kill('SIGTERM'); frontend.kill('SIGTERM'); process.exit(0); };
  process.on('SIGINT', cleanup);
  process.on('SIGTERM', cleanup);

  await new Promise((resolve) => {
    backend.on('close', () => { frontend.kill(); resolve(); });
    frontend.on('close', () => { backend.kill(); resolve(); });
  });
}

async function cmdBuild() {
  console.log('\n  Building frontend for production...');
  await checkDeps(FRONTEND_DIR, 'frontend');
  return runCommand('npx', ['vite', 'build'], FRONTEND_DIR);
}

function cmdStatus() {
  printBanner();
  console.log('  Project Information:');
  console.log(`    Root:        ${PROJECT_ROOT}`);
  console.log(`    Backend:     ${BACKEND_DIR}`);
  console.log(`    Frontend:    ${FRONTEND_DIR}`);
  console.log(`    Config:      ${join(PROJECT_ROOT, 'config', 'default.yaml')}`);
  console.log(`    Local conf:  ${join(PROJECT_ROOT, 'config', 'local.yaml')} ${existsSync(join(PROJECT_ROOT, 'config', 'local.yaml')) ? '(exists)' : '(none)'}`);
  console.log(`    Backend port:  ${BACKEND_PORT}`);
  console.log(`    Frontend port: ${FRONTEND_PORT}`);
  console.log('');

  const dataDir = join(PROJECT_ROOT, 'data');
  if (existsSync(dataDir)) {
    const dataFiles = readdirSync(dataDir).filter(f => !f.startsWith('.'));
    console.log(`    Data files: ${dataFiles.length} in data/`);
    for (const f of dataFiles.slice(0, 5)) console.log(`      - ${f}`);
    if (dataFiles.length > 5) console.log(`      ... and ${dataFiles.length - 5} more`);
  }

  const runsDir = join(PROJECT_ROOT, 'workspace', 'diagnostic-runs');
  if (existsSync(runsDir)) {
    const runs = readdirSync(runsDir).filter(f => !f.startsWith('.'));
    console.log(`\n    Diagnostic runs: ${runs.length}`);
  }

  console.log(`\n    Dependencies:`);
  console.log(`      Backend:  ${existsSync(join(BACKEND_DIR, 'node_modules')) ? 'Installed' : 'NOT installed'}`);
  console.log(`      Frontend: ${existsSync(join(FRONTEND_DIR, 'node_modules')) ? 'Installed' : 'NOT installed'}`);
  console.log('');
}

// ─── Router ──────────────────────────────────────────────────

const commands = {
  init: cmdInit,
  list: cmdConfigList,
  get: cmdConfigGet,
  set: cmdConfigSet,
  reset: cmdConfigReset,
  path: cmdConfigPath,
  backend: cmdBackend,
  frontend: cmdFrontend,
  all: cmdAll,
  build: cmdBuild,
  status: cmdStatus,
  help: () => { printUsage(); process.exit(0); },
};

const cmd = process.argv[2];

if (!cmd) {
  printUsage();
  process.exit(0);
}

// Handle "config <subcommand>" pattern
if (cmd === 'config') {
  const sub = process.argv[3];
  if (!sub || !commands[sub]) {
    console.log('  Usage: ind-diag config <list|get|set|reset|path>');
    console.log('  Run:   ind-diag help');
    process.exit(1);
  }
  if (sub === 'list') commands.list();
  else if (sub === 'get') {
    const key = process.argv[4];
    if (!key) { console.error('Usage: ind-diag config get <key>'); process.exit(1); }
    commands.get(key);
  }
  else if (sub === 'set') {
    const key = process.argv[4];
    const value = process.argv[5];
    if (!key || value === undefined) { console.error('Usage: ind-diag config set <key> <value>'); process.exit(1); }
    commands.set(key, value);
  }
  else if (sub === 'reset') {
    const key = process.argv[4];
    if (!key) { console.error('Usage: ind-diag config reset <key>'); process.exit(1); }
    commands.reset(key);
  }
  else if (sub === 'path') commands.path();
  process.exit(0);
}

if (!commands[cmd]) {
  console.error(`  Unknown command: ${cmd}`);
  console.error('  Run: ind-diag help');
  process.exit(1);
}

Promise.resolve(commands[cmd]()).catch((err) => {
  console.error(`\n  [ERROR] ${err.message}`);
  process.exit(1);
});
```

- [ ] **Step 2: Fix the import approach for js-yaml dump in config commands**

The `config list` and `config get` commands need `js-yaml`'s `dump`. The above uses pseudo-code `await_import` and `require_import`. Replace those with a proper dynamic import at the top of the command functions:

In `cmdConfigList`:
```javascript
async function cmdConfigList() {
  const { dump } = await import('js-yaml');
  const output = dump(config, { indent: 2, lineWidth: 120, noRefs: true });
  console.log(output);
}
```

In `cmdConfigGet`:
```javascript
async function cmdConfigGet(key) {
  const value = getKey(config, key);
  if (value === undefined) {
    console.error(`Key not found: ${key}`);
    process.exit(1);
  }
  if (typeof value === 'object') {
    const { dump } = await import('js-yaml');
    console.log(dump(value, { indent: 2, lineWidth: 120, noRefs: true }));
  } else {
    console.log(value);
  }
}
```

And update the router for `list` and `get` to use `.then()` or await since they're now async:

```javascript
if (cmd === 'config') {
  const sub = process.argv[3];
  // ...
  (async () => {
    if (sub === 'list') await commands.list();
    else if (sub === 'get') {
      const key = process.argv[4];
      if (!key) { console.error('Usage: ind-diag config get <key>'); process.exit(1); }
      await commands.get(key);
    }
    // ... rest
    process.exit(0);
  })();
  return; // don't fall through to Promise.resolve below
}
```

- [ ] **Step 3: Verify syntax**

Run: `cd /Volumes/laxer/codes/skills/ industrial-deep-diagnostic && node --check commands/cli.mjs`
Expected: no output

---

### Task 5: Update package.json — bin, scripts, metadata

**Files:**
- Modify: `package.json`

- [ ] **Step 1: Rewrite package.json**

```json
{
  "name": "industrial-deep-diagnostic",
  "version": "1.0.0",
  "description": "端到端工业深度诊断系统 — 调用 Claude Code CLI 对工业数据进行 8 阶段根因分析",
  "type": "module",
  "bin": {
    "ind-diag": "./commands/cli.mjs"
  },
  "scripts": {
    "start": "node commands/cli.mjs all",
    "backend": "node commands/cli.mjs backend",
    "frontend": "node commands/cli.mjs frontend",
    "build": "node commands/cli.mjs build",
    "status": "node commands/cli.mjs status",
    "link": "npm link",
    "test": "echo \"Error: no test specified\" && exit 1"
  },
  "repository": {
    "type": "git",
    "url": "git+https://github.com/kingdol666/industrial-deep-diagnostic.git"
  },
  "keywords": ["industrial", "diagnostic", "root-cause-analysis", "claude"],
  "author": "",
  "license": "ISC",
  "bugs": {
    "url": "https://github.com/kingdol666/industrial-deep-diagnostic/issues"
  },
  "homepage": "https://github.com/kingdol666/industrial-deep-diagnostic#readme",
  "dependencies": {
    "js-yaml": "^4.1.1"
  }
}
```

---

### Task 6: Update .gitignore

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Add config/local.yaml to .gitignore**

```
# Config (user overrides)
config/local.yaml
```

---

### Task 7: Integration Test — Full Verification

- [ ] **Step 1: Syntax check all files**

```bash
cd "/Volumes/laxer/codes/skills/ industrial-deep-diagnostic" && \
  node --check config/loader.mjs && \
  node --check commands/cli.mjs && \
  node --check app/backend/src/db.mjs && \
  node --check app/backend/src/index.mjs && \
  echo "ALL OK"
```

- [ ] **Step 2: Test CLI help**

```bash
node commands/cli.mjs help
```
Expected: prints usage with all commands

- [ ] **Step 3: Test config list**

```bash
node commands/cli.mjs config list
```
Expected: prints merged config as YAML

- [ ] **Step 4: Test config set/get/reset**

```bash
node commands/cli.mjs config set server.port 9090
node commands/cli.mjs config get server.port
# Expected: 9090
node commands/cli.mjs config reset server.port
node commands/cli.mjs config get server.port
# Expected: 3210 (default)
```

- [ ] **Step 5: Test init**

```bash
node commands/cli.mjs init
```
Expected: prints OK for config and DB init

- [ ] **Step 6: Test status**

```bash
node commands/cli.mjs status
```
Expected: prints project overview

- [ ] **Step 7: npm link and global command test**

```bash
cd "/Volumes/laxer/codes/skills/ industrial-deep-diagnostic" && npm link
which ind-diag
ind-diag help
```
Expected: `which ind-diag` prints a path, `ind-diag help` prints usage

- [ ] **Step 8: Start backend and run API tests**

```bash
ind-diag backend &
sleep 2
curl http://localhost:3210/api/health
# Expected: {"status":"ok",...}
```

- [ ] **Step 9: Build frontend**

```bash
ind-diag build
```
Expected: `app/frontend/dist/` created with index.html and assets

- [ ] **Step 10: Serve built frontend and verify**

```bash
curl -s http://localhost:3210/ | head -5
# Expected: HTML content from dist/index.html
```

- [ ] **Step 11: Cleanup**

```bash
# Kill test backend
pkill -f "node src/index.mjs"
# Remove test local.yaml
rm -f "/Volumes/laxer/codes/skills/ industrial-deep-diagnostic/config/local.yaml"
```

---

## Verification Summary

1. `ind-diag help` — full usage output
2. `ind-diag config list` — merged config YAML
3. `ind-diag config set server.port 9090 && ind-diag config get server.port` → `9090`
4. `ind-diag config reset server.port && ind-diag config get server.port` → `3210`
5. `ind-diag init` — validates config and DB
6. `ind-diag status` — project overview
7. `ind-diag backend` — auto-inits, starts server on configured port
8. `ind-diag build` — produces `app/frontend/dist/` with index.html
9. Backend serves built frontend at `http://localhost:3210/`
10. All 10 API tests pass
11. `npm link` → `ind-diag` available globally
