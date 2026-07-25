#!/usr/bin/env node
// rag-retrieval-engine/start.mjs — Cross-platform RAG engine starter
// Replaces start.sh. Works on Windows, Linux, and macOS.
//
// Usage:
//   node rag-retrieval-engine/start.mjs

import { execSync } from 'child_process';
import { join, dirname, resolve } from 'path';
import { fileURLToPath } from 'url';
import { existsSync } from 'fs';
import { isWindows, commandExists } from '../commands/cross-platform.mjs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const RAG_DIR = resolve(__dirname);

function printHeader() {
  console.log('');
  console.log('  ╔══════════════════════════════════════════════╗');
  console.log('  ║   RAG Retrieval Engine — Startup              ║');
  console.log('  ╚══════════════════════════════════════════════╝');
  console.log('');
}

async function runCommand(cmd, args, cwd) {
  return new Promise((resolve, reject) => {
    const child = spawn(cmd, args, { cwd, stdio: 'inherit', shell: isWindows });
    child.on('close', (code) => {
      if (code === 0) resolve();
      else reject(new Error(`${cmd} exited with code ${code}`));
    });
    child.on('error', reject);
  });
}

async function main() {
  printHeader();

  // 1. Check Python
  const pythonCmd = isWindows ? 'python' : 'python3';
  let hasPython = commandExists(pythonCmd);
  if (!hasPython) {
    hasPython = commandExists('python');
  }
  if (!hasPython) {
    console.error('  [ERROR] Python >= 3.9 is required but not found in PATH');
    console.error('  Install Python from https://www.python.org/downloads/');
    process.exit(1);
  }
  console.log(`  [OK] Python found`);

  // 2. Check for uv (preferred) or pip
  const hasUv = commandExists('uv');
  const hasPip = commandExists(isWindows ? 'pip' : 'pip3') || commandExists('pip');

  if (!hasUv && !hasPip) {
    console.error('  [ERROR] Neither uv nor pip found');
    console.error('  Install uv: https://docs.astral.sh/uv/getting-started/installation/');
    process.exit(1);
  }

  // 3. Create virtual environment (if not exists)
  if (!existsSync(join(RAG_DIR, '.venv'))) {
    console.log('  Creating virtual environment...');
    if (hasUv) {
      await runCommand('uv', ['venv'], RAG_DIR);
    } else {
      await runCommand(pythonCmd, ['-m', 'venv', '.venv'], RAG_DIR);
    }
    console.log('  [OK] Virtual environment created');
  }

  // 4. Install dependencies
  console.log('  Installing dependencies...');
  if (hasUv) {
    await runCommand('uv', ['sync'], RAG_DIR);
  } else {
    // With pip, use the requirements.txt
    const pipCmd = isWindows ? join(RAG_DIR, '.venv', 'Scripts', 'pip.exe') : join(RAG_DIR, '.venv', 'bin', 'pip');
    const reqFile = join(RAG_DIR, 'requirements.txt');
    if (existsSync(reqFile)) {
      await runCommand(pipCmd, ['install', '-r', reqFile], RAG_DIR);
    }
  }
  console.log('  [OK] Dependencies installed');

  // 5. Start server
  console.log('  Starting RAG Retrieval Engine...');
  console.log('  API: http://localhost:8765');
  console.log('  Press Ctrl+C to stop');
  console.log('');

  const pythonExec = hasUv
    ? 'uv'
    : isWindows
      ? join(RAG_DIR, '.venv', 'Scripts', 'python.exe')
      : join(RAG_DIR, '.venv', 'bin', 'python');

  const pythonArgs = hasUv
    ? ['run', 'python', 'server.py']
    : ['server.py'];

  const server = spawn(pythonExec, pythonArgs, {
    cwd: RAG_DIR,
    stdio: 'inherit',
    shell: isWindows,
  });

  const cleanup = () => {
    console.log('\n  Stopping RAG engine...');
    try {
      if (isWindows) {
        execSync(`taskkill /PID ${server.pid} /T /F`, { stdio: 'ignore' });
      } else {
        server.kill('SIGTERM');
      }
    } catch {}
    console.log('  RAG engine stopped.');
    process.exit(0);
  };

  process.on('SIGINT', cleanup);
  if (!isWindows) process.on('SIGTERM', cleanup);

  server.on('close', (code) => {
    console.log(`\n  RAG engine exited with code ${code}`);
    process.exit(code || 0);
  });

  server.on('error', (err) => {
    console.error(`  [ERROR] RAG engine failed: ${err.message}`);
    process.exit(1);
  });
}

main().catch((err) => {
  console.error(`  [ERROR] ${err.message}`);
  process.exit(1);
});