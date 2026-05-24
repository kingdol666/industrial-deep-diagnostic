#!/usr/bin/env node
import { spawn } from 'child_process';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { existsSync, readdirSync } from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const PROJECT_ROOT = resolvePath(__dirname, '..');
const BACKEND_DIR = join(PROJECT_ROOT, 'app', 'backend');
const FRONTEND_DIR = join(PROJECT_ROOT, 'app', 'frontend');

function resolvePath(base, ...parts) {
  // Handle paths with spaces
  const segments = join(base, ...parts).split('/');
  const resolved = [];
  for (const seg of segments) {
    if (seg === '..') resolved.pop();
    else if (seg !== '.') resolved.push(seg);
  }
  return resolved.join('/');
}

function printBanner() {
  console.log('');
  console.log('  ╔══════════════════════════════════════════════╗');
  console.log('  ║   Industrial Deep Diagnostic — CLI            ║');
  console.log('  ║   Version 1.0.0                               ║');
  console.log('  ╚══════════════════════════════════════════════╝');
  console.log('');
}

function printUsage() {
  printBanner();
  console.log('  Usage: node commands/cli.mjs <command> [options]');
  console.log('');
  console.log('  Commands:');
  console.log('    backend       Start the Express API server (port 3210)');
  console.log('    frontend      Start the Vue dev server (port 5180)');
  console.log('    all           Start both backend and frontend');
  console.log('    build         Build the frontend for production');
  console.log('    install       Install all dependencies');
  console.log('    status        Check project status');
  console.log('    help          Show this help');
  console.log('');
  console.log('  Examples:');
  console.log('    node commands/cli.mjs all');
  console.log('    node commands/cli.mjs backend');
  console.log('');
}

async function runCommand(cmd, args, cwd) {
  return new Promise((resolve, reject) => {
    const child = spawn(cmd, args, {
      cwd,
      stdio: 'inherit',
      shell: true,
    });
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

async function cmdBackend() {
  console.log('\n  Starting Express API server...');
  await checkDeps(BACKEND_DIR, 'backend');
  console.log(`  Backend: http://localhost:3210`);
  console.log(`  Project root: ${PROJECT_ROOT}`);
  console.log('');
  return runCommand('node', ['src/index.mjs'], BACKEND_DIR);
}

async function cmdFrontend() {
  console.log('\n  Starting Vue dev server...');
  await checkDeps(FRONTEND_DIR, 'frontend');
  console.log(`  Frontend: http://localhost:5180`);
  console.log('');
  return runCommand('npx', ['vite', '--host'], FRONTEND_DIR);
}

async function cmdAll() {
  printBanner();
  console.log('  Starting full stack...');
  console.log(`  Backend:  http://localhost:3210`);
  console.log(`  Frontend: http://localhost:5180`);
  console.log('');

  await checkDeps(BACKEND_DIR, 'backend');
  await checkDeps(FRONTEND_DIR, 'frontend');

  const backend = spawn('node', ['src/index.mjs'], {
    cwd: BACKEND_DIR,
    stdio: 'inherit',
    shell: true,
  });

  // Wait for backend to initialize
  await new Promise(r => setTimeout(r, 1500));

  const frontend = spawn('npx', ['vite', '--host'], {
    cwd: FRONTEND_DIR,
    stdio: 'inherit',
    shell: true,
  });

  const cleanup = () => {
    backend.kill('SIGTERM');
    frontend.kill('SIGTERM');
    process.exit(0);
  };

  process.on('SIGINT', cleanup);
  process.on('SIGTERM', cleanup);

  // Wait for either to exit
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

async function cmdInstall() {
  console.log('\n  Installing all dependencies...');

  if (!existsSync(join(BACKEND_DIR, 'package.json'))) {
    console.error('  [ERROR] backend/package.json not found');
    process.exit(1);
  }
  if (!existsSync(join(FRONTEND_DIR, 'package.json'))) {
    console.error('  [ERROR] frontend/package.json not found');
    process.exit(1);
  }

  console.log('\n  --- Backend ---');
  await runCommand('npm', ['install'], BACKEND_DIR);

  console.log('\n  --- Frontend ---');
  await runCommand('npm', ['install'], FRONTEND_DIR);

  console.log('\n  Dependencies installed successfully.');
}

function cmdStatus() {
  printBanner();
  console.log('  Project Information:');
  console.log(`    Root:     ${PROJECT_ROOT}`);
  console.log(`    Backend:  ${BACKEND_DIR}`);
  console.log(`    Frontend: ${FRONTEND_DIR}`);
  console.log('');

  const dataDir = join(PROJECT_ROOT, 'data');
  const workspaceDir = join(PROJECT_ROOT, 'workspace');

  if (existsSync(dataDir)) {
    const dataFiles = readdirSync(dataDir).filter(f => !f.startsWith('.'));
    console.log(`    Data files: ${dataFiles.length} in data/`);
    for (const f of dataFiles.slice(0, 5)) {
      console.log(`      - ${f}`);
    }
    if (dataFiles.length > 5) console.log(`      ... and ${dataFiles.length - 5} more`);
  }

  const runsDir = join(workspaceDir, 'diagnostic-runs');
  if (existsSync(runsDir)) {
    const runs = readdirSync(runsDir).filter(f => !f.startsWith('.'));
    console.log(`\n    Diagnostic runs: ${runs.length} in workspace/diagnostic-runs/`);
  }

  console.log(`\n    Dependencies:`);
  console.log(`      Backend:  ${existsSync(join(BACKEND_DIR, 'node_modules')) ? 'Installed' : 'NOT installed'}`);
  console.log(`      Frontend: ${existsSync(join(FRONTEND_DIR, 'node_modules')) ? 'Installed' : 'NOT installed'}`);
  console.log('');
}

const commands = {
  backend: cmdBackend,
  frontend: cmdFrontend,
  all: cmdAll,
  build: cmdBuild,
  install: cmdInstall,
  status: cmdStatus,
  help: () => { printUsage(); process.exit(0); },
};

const cmd = process.argv[2];

if (!cmd || !commands[cmd]) {
  printUsage();
  process.exit(cmd ? 1 : 0);
}

Promise.resolve(commands[cmd]()).catch((err) => {
  console.error(`\n  [ERROR] ${err.message}`);
  process.exit(1);
});
