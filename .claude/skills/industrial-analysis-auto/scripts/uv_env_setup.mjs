#!/usr/bin/env node
// uv_env_setup.mjs — Ensure uv + Python venv are ready for industrial-deep-diagnostic
// Usage: node uv_env_setup.mjs [--skill-path <path>] [--check-only]
//
// Outputs JSON: { python: "<abs-path>", uv: "<abs-path>", venv_dir: "<abs-path>", installed: true }
// Exit 0 on success, 1 on failure.

import { execSync } from 'child_process';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const skillPathIdx = args.indexOf('--skill-path');
const checkOnly = args.includes('--check-only');

// Resolve paths
const SCRIPTS_DIR = __dirname;
const VENV_DIR = path.join(SCRIPTS_DIR, '.venv');
const REQ_FILE = path.join(SCRIPTS_DIR, 'requirements.txt');

function run(cmd) {
  try {
    return execSync(cmd, { encoding: 'utf-8', stdio: ['pipe', 'pipe', 'pipe'] }).trim();
  } catch {
    return null;
  }
}

function findUv() {
  return run('which uv 2>/dev/null') || null;
}

function installUv() {
  console.error('[uv_env] uv not found, installing...');
  // Try official installer
  run('bash -c "curl -LsSf https://astral.sh/uv/install.sh | sh 2>&1"');
  // Brew fallback
  if (!findUv()) run('brew install uv 2>&1');
  // PATH expansion for common install locations
  const candidates = [
    path.join(process.env.HOME || '/root', '.local', 'bin', 'uv'),
    '/usr/local/bin/uv',
    '/opt/homebrew/bin/uv',
  ];
  for (const c of candidates) {
    if (fs.existsSync(c)) return c;
  }
  return findUv();
}

function getPythonBin() {
  return path.join(VENV_DIR, 'bin', 'python');
}

function venvReady() {
  const bin = getPythonBin();
  if (!fs.existsSync(bin)) return false;
  const check = run(`"${bin}" -c "import matplotlib, numpy, pandas, seaborn, openpyxl, scipy"`);
  return check !== null;
}

function createVenv(uvBin) {
  console.error(`[uv_env] Creating venv at ${VENV_DIR}`);
  run(`"${uvBin}" venv "${VENV_DIR}" --python 3.12 --seed --clear`);
  if (!fs.existsSync(getPythonBin())) {
    // Fallback: try system python3
    run(`python3 -m venv "${VENV_DIR}" --clear`);
  }
}

function installDeps(uvBin) {
  console.error('[uv_env] Installing dependencies...');
  const pythonBin = getPythonBin();
  // Prefer uv pip (fast), fallback to regular pip
  let result = run(`"${uvBin}" pip install -r "${REQ_FILE}" --python "${pythonBin}"`);
  if (!result) {
    result = run(`"${pythonBin}" -m pip install -r "${REQ_FILE}"`);
  }
  // Install scipy separately if not picked up (large binary, sometimes skipped)
  const scipyCheck = run(`"${pythonBin}" -c "import scipy"`);
  if (!scipyCheck) {
    run(`"${uvBin}" pip install scipy --python "${pythonBin}"`);
  }
}

// === Main ===

let uvBin = findUv();
if (!uvBin) {
  uvBin = installUv();
  if (!uvBin) {
    console.error('[uv_env] FAILED: Could not install uv. Run: curl -LsSf https://astral.sh/uv/install.sh | sh');
    process.exit(1);
  }
}

// Expand ~ in uv path
if (uvBin.startsWith('~')) {
  uvBin = path.join(process.env.HOME || '', uvBin.slice(1));
}

if (checkOnly) {
  const ready = venvReady();
  console.log(JSON.stringify({
    python: ready ? getPythonBin() : null,
    uv: uvBin,
    venv_dir: VENV_DIR,
    installed: ready,
  }));
  process.exit(ready ? 0 : 1);
}

if (!venvReady()) {
  createVenv(uvBin);
  installDeps(uvBin);
}

if (!venvReady()) {
  console.error('[uv_env] FAILED: venv not functional after setup');
  process.exit(1);
}

// Success output — machine-readable JSON to stdout
const output = {
  python: getPythonBin(),
  uv: uvBin,
  venv_dir: VENV_DIR,
  installed: true,
};
console.log(JSON.stringify(output));
