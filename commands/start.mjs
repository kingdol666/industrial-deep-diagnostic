#!/usr/bin/env node
// commands/start.mjs — Cross-platform service starter
// Replaces start-all.sh, start-backend.sh, start-frontend.sh
// Works on Windows, Linux, and macOS.
//
// Usage:
//   node commands/start.mjs all       - Start backend + frontend
//   node commands/start.mjs backend   - Start backend only
//   node commands/start.mjs frontend  - Start frontend only

import { spawn } from 'child_process';
import { join, dirname, resolve } from 'path';
import { fileURLToPath } from 'url';
import { existsSync, mkdirSync } from 'fs';
import { nodeCmd, npxCmd, npmCmd, isWindows, killProcess, gracefulKill, onShutdown } from './cross-platform.mjs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const PROJECT_ROOT = resolve(__dirname, '..');
const BACKEND_DIR = join(PROJECT_ROOT, 'app', 'backend');
const FRONTEND_DIR = join(PROJECT_ROOT, 'app', 'frontend');
const BACKEND_PORT = process.env.SERVER_PORT || 3210;
const FRONTEND_PORT = process.env.FRONTEND_PORT || 5180;

// ─── Helpers ──────────────────────────────────────────────

function printHeader(title) {
  const line = '='.repeat(36);
  console.log('');
  console.log(`  Industrial Deep Diagnostic — ${title}`);
  console.log(`  ${line}`);
  console.log('');
}

function checkNodeVersion() {
  try {
    const ver = process.version;
    const major = parseInt(ver.slice(1).split('.')[0], 10);
    if (major < 18) {
      console.error(`  [ERROR] Node.js >= 18 required, found ${ver}`);
      process.exit(1);
    }
    console.log(`  Node.js: ${ver}`);
    return true;
  } catch {
    console.error('  [ERROR] Node.js is not installed');
    process.exit(1);
  }
}

async function installDeps(dir, name) {
  if (!existsSync(join(dir, 'node_modules'))) {
    console.log('');
    console.log(`  [INSTALL] Installing ${name} dependencies...`);
    return new Promise((resolve, reject) => {
      const child = spawn(npmCmd(), ['install'], {
        cwd: dir,
        stdio: 'inherit',
        shell: isWindows,
      });
      child.on('close', (code) => {
        if (code === 0) resolve();
        else reject(new Error(`npm install failed with code ${code}`));
      });
      child.on('error', reject);
    });
  }
  console.log(`  [OK] ${name} dependencies found`);
}

function ensureDirectories() {
  const dataDir = join(PROJECT_ROOT, 'data');
  const workspaceDir = join(PROJECT_ROOT, 'workspace', 'diagnostic-runs');
  mkdirSync(dataDir, { recursive: true });
  mkdirSync(workspaceDir, { recursive: true });
}

// ─── Starters ──────────────────────────────────────────────

function startBackend() {
  const child = spawn(nodeCmd(), ['src/index.mjs'], {
    cwd: BACKEND_DIR,
    stdio: 'inherit',
    shell: isWindows,
  });
  child.on('error', (err) => {
    console.error(`  [ERROR] Backend failed to start: ${err.message}`);
  });
  return child;
}

function startFrontend() {
  const child = spawn(npxCmd(), ['vite', '--host'], {
    cwd: FRONTEND_DIR,
    stdio: 'inherit',
    shell: isWindows,
  });
  child.on('error', (err) => {
    console.error(`  [ERROR] Frontend failed to start: ${err.message}`);
  });
  return child;
}

// ─── Commands ──────────────────────────────────────────────

async function cmdAll() {
  printHeader('Full Stack');
  checkNodeVersion();
  ensureDirectories();

  await installDeps(BACKEND_DIR, 'backend');
  await installDeps(FRONTEND_DIR, 'frontend');

  console.log('');
  console.log(`  Backend:  http://localhost:${BACKEND_PORT}`);
  console.log(`  Frontend: http://localhost:${FRONTEND_PORT}`);
  console.log('');
  console.log('  Open http://localhost:5180 in your browser.');
  console.log('  Press Ctrl+C to stop all.');
  console.log('');

  const backend = startBackend();
  // Wait for backend to initialize before starting frontend
  await new Promise(r => setTimeout(r, 1500));
  const frontend = startFrontend();

  onShutdown(() => {
    console.log('\n  Shutting down...');
    killProcess(backend);
    killProcess(frontend);
    console.log('  All processes stopped.');
  });

  await new Promise((resolve) => {
    backend.on('close', () => { killProcess(frontend); resolve(); });
    frontend.on('close', () => { killProcess(backend); resolve(); });
  });
}

async function cmdBackend() {
  printHeader('Backend');
  checkNodeVersion();
  ensureDirectories();
  await installDeps(BACKEND_DIR, 'backend');

  console.log(`  Starting Express API server on http://localhost:${BACKEND_PORT}`);
  console.log(`  Project root: ${PROJECT_ROOT}`);
  console.log(`  Data: ${join(PROJECT_ROOT, 'data')}`);
  console.log(`  Workspace: ${join(PROJECT_ROOT, 'workspace', 'diagnostic-runs')}`);
  console.log('');
  console.log('  Press Ctrl+C to stop');
  console.log('');

  const backend = startBackend();

  onShutdown(() => {
    console.log('\n  Stopping backend...');
    killProcess(backend);
  });

  await new Promise((resolve) => {
    backend.on('close', resolve);
  });
}

async function cmdFrontend() {
  printHeader('Frontend');
  checkNodeVersion();
  await installDeps(FRONTEND_DIR, 'frontend');

  console.log(`  Starting Vue dev server on http://localhost:${FRONTEND_PORT}`);
  console.log(`  Backend API proxy: /api → http://localhost:${BACKEND_PORT}`);
  console.log('');
  console.log('  Press Ctrl+C to stop');
  console.log('');

  const frontend = startFrontend();

  onShutdown(() => {
    console.log('\n  Stopping frontend...');
    killProcess(frontend);
  });

  await new Promise((resolve) => {
    frontend.on('close', resolve);
  });
}

// ─── Main ──────────────────────────────────────────────────

const command = process.argv[2] || 'all';

(async () => {
  try {
    switch (command) {
      case 'all':
        await cmdAll();
        break;
      case 'backend':
        await cmdBackend();
        break;
      case 'frontend':
        await cmdFrontend();
        break;
      default:
        console.error(`  Unknown command: ${command}`);
        console.error('  Usage: node commands/start.mjs [all|backend|frontend]');
        process.exit(1);
    }
  } catch (err) {
    console.error(`\n  [ERROR] ${err.message}`);
    process.exit(1);
  }
})();