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

  // Init DB
  try {
    const { initDB } = await import('../app/backend/src/db/database.mjs');
    initDB();
  } catch (err) {
    console.error(`  [ERROR] Database init failed: ${err.message}`);
    process.exit(1);
  }

  console.log('\n  Initialization complete. Run: ind-diag all');
}

async function cmdConfigList() {
  const { dump } = await import('js-yaml');
  const output = dump(config, { indent: 2, lineWidth: 120, noRefs: true });
  console.log(output);
}

async function cmdConfigGet(key) {
  const value = getKey(config, key);
  if (value === undefined) {
    console.error(`Key not found: ${key}`);
    process.exit(1);
  }
  if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
    const { dump } = await import('js-yaml');
    console.log(dump(value, { indent: 2, lineWidth: 120, noRefs: true }));
  } else if (Array.isArray(value)) {
    console.log(JSON.stringify(value, null, 2));
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
  const localYaml = join(PROJECT_ROOT, 'config', 'local.yaml');
  console.log(`    Local conf:  ${localYaml} ${existsSync(localYaml) ? '(exists)' : '(none)'}`);
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

async function main() {
  const cmd = process.argv[2];

  if (!cmd || cmd === 'help') {
    printUsage();
    process.exit(0);
  }

  // Handle "config <subcommand>" pattern
  if (cmd === 'config') {
    const sub = process.argv[3];

    if (!sub) {
      console.error('  Usage: ind-diag config <list|get|set|reset|path>');
      process.exit(1);
    }

    try {
      if (sub === 'list') {
        await cmdConfigList();
      } else if (sub === 'get') {
        const key = process.argv[4];
        if (!key) { console.error('Usage: ind-diag config get <key>'); process.exit(1); }
        await cmdConfigGet(key);
      } else if (sub === 'set') {
        const key = process.argv[4];
        const value = process.argv[5];
        if (!key || value === undefined) { console.error('Usage: ind-diag config set <key> <value>'); process.exit(1); }
        cmdConfigSet(key, value);
      } else if (sub === 'reset') {
        const key = process.argv[4];
        if (!key) { console.error('Usage: ind-diag config reset <key>'); process.exit(1); }
        cmdConfigReset(key);
      } else if (sub === 'path') {
        cmdConfigPath();
      } else {
        console.error(`  Unknown config command: ${sub}`);
        console.error('  Run: ind-diag help');
        process.exit(1);
      }
    } catch (err) {
      console.error(`  [ERROR] ${err.message}`);
      process.exit(1);
    }
    return;
  }

  // Handle top-level commands
  const commands = {
    init: cmdInit,
    backend: cmdBackend,
    frontend: cmdFrontend,
    all: cmdAll,
    build: cmdBuild,
    status: cmdStatus,
  };

  if (!commands[cmd]) {
    console.error(`  Unknown command: ${cmd}`);
    console.error('  Run: ind-diag help');
    process.exit(1);
  }

  await commands[cmd]();
}

main().catch((err) => {
  console.error(`\n  [ERROR] ${err.message}`);
  process.exit(1);
});
