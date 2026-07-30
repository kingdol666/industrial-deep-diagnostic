#!/usr/bin/env node
// uv_env_setup.mjs — Cross-platform Python venv bootstrap
// Falls back to system Python when uv is unavailable (e.g., Windows)
// Usage: node uv_env_setup.mjs [--skill-path <path>] [--check-only]

import { execSync } from 'child_process';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const checkOnly = args.includes('--check-only');

const SCRIPTS_DIR = __dirname;
const VENV_DIR = path.join(SCRIPTS_DIR, '.venv');
const REQ_FILE = path.join(SCRIPTS_DIR, 'requirements.txt');

function run(cmd) {
  try {
    return execSync(cmd, { encoding: 'utf-8', timeout: 120000 }).trim();
  } catch { return null; }
}

function detectPython() {
  // Try uv venv first
  const uv = run('uv --version 2>&1');
  if (uv) return { type: 'uv', bin: 'uv', python: getVenvPython() };

  // Try system Python on Windows (pip installed packages)
  for (const py of ['python3', 'python']) {
    const v = run(`${py} --version 2>&1`);
    if (v) return { type: 'system', bin: py, python: py };
  }
  return null;
}

function getVenvPython() {
  // Cross-platform venv Python path
  return process.platform === 'win32'
    ? path.join(VENV_DIR, 'Scripts', 'python.exe')
    : path.join(VENV_DIR, 'bin', 'python');
}

function ensureVenv(py) {
  if (py.type === 'uv') {
    const venvPython = getVenvPython();
    if (!fs.existsSync(venvPython)) {
      run(`uv venv "${VENV_DIR}"`);
      run(`uv pip install -r "${REQ_FILE}"`);
    }
    py.python = venvPython;
  }
  return py.python;
}

if (checkOnly) {
  const py = detectPython();
  const result = { available: !!py, python: py?.python || null, venv_ready: py?.type === 'uv' ? fs.existsSync(path.join(VENV_DIR, 'bin', 'python')) : false };
  console.log(JSON.stringify(result));
  process.exit(result.available ? 0 : 1);
}

const py = detectPython();
if (!py) {
  console.log(JSON.stringify({ error: 'No Python found', fix: 'Install Python 3.10+ from python.org' }));
  process.exit(1);
}

const pythonBin = ensureVenv(py);
console.log(JSON.stringify({ python: pythonBin, type: py.type, ok: true }));
