#!/usr/bin/env node
// uv_env_setup.mjs — Cross-platform Python venv bootstrap (uv-first)
//
// Primary engine: uv project at .claude/shared/scripts/pyproject.toml
//   - venv: .claude/shared/scripts/.venv (uv default project environment)
//   - deps: synced from pyproject.toml via `uv sync --project <dir>`
//   - fallback: requirements.txt (legacy) if pyproject.toml absent
// Falls back to system Python when uv is unavailable or the venv is broken
// (e.g., Windows App Control Policy blocking DLL loads).
//
// Usage:
//   node uv_env_setup.mjs [--check-only] [--force-sync]
// Output JSON: { python, type, ok, venv_ready, uv_project, uv_cmd }
//   uv_cmd: ["uv","run","--project",<dir>] when uv is available (use with runCmd)

import { execSync } from 'child_process';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const checkOnly = args.includes('--check-only');
const forceSync = args.includes('--force-sync');

const SCRIPTS_DIR = __dirname;
const VENV_DIR = path.join(SCRIPTS_DIR, '.venv');
const REQ_FILE = path.join(SCRIPTS_DIR, 'requirements.txt');
const PYPROJECT = path.join(SCRIPTS_DIR, 'pyproject.toml');

function run(cmd) {
  try {
    return execSync(cmd, { encoding: 'utf-8', timeout: 300000 }).trim();
  } catch { return null; }
}

function getVenvPython() {
  // Cross-platform venv Python path
  return process.platform === 'win32'
    ? path.join(VENV_DIR, 'Scripts', 'python.exe')
    : path.join(VENV_DIR, 'bin', 'python');
}

/**
 * Verify a Python binary can import the critical packages (numpy, pandas).
 * Returns false if the binary is missing, packages aren't installed, or
 * DLL loading is blocked by security policy (Windows App Control / AppLocker).
 */
function verifyPython(pythonBin) {
  try {
    execSync(`"${pythonBin}" -c "import numpy, pandas"`, {
      encoding: 'utf-8', timeout: 30000, stdio: 'pipe',
    });
    return true;
  } catch {
    return false;
  }
}

/** Sync deps into the shared venv. Prefers pyproject.toml (uv project), falls back to requirements.txt. */
function syncVenv(uvCmd) {
  if (fs.existsSync(PYPROJECT)) {
    run(`uv sync --project "${SCRIPTS_DIR}" --quiet`);
  } else if (fs.existsSync(REQ_FILE)) {
    run(`uv pip install -p "${getVenvPython()}" -r "${REQ_FILE}"`);
  }
}

/**
 * Find a working Python binary.
 * Strategy 1: uv-managed venv (create + sync from pyproject.toml, verify).
 * Strategy 2: system Python with packages already installed.
 * Falls back transparently when the venv is broken by OS security policy.
 */
function findWorkingPython() {
  const uv = run('uv --version 2>&1');

  // Strategy 1: uv-managed venv
  if (uv) {
    const venvPython = getVenvPython();
    if (!fs.existsSync(venvPython) || forceSync) {
      run(`uv venv "${VENV_DIR}"`);
      syncVenv();
    }
    if (verifyPython(venvPython)) {
      return {
        python: venvPython,
        type: 'uv',
        venv_ready: true,
        uv_project: SCRIPTS_DIR,
        uv_cmd: ['uv', 'run', '--project', SCRIPTS_DIR],
      };
    }
    // Venv exists but is broken — attempt one repair sync, then fall through.
    if (fs.existsSync(PYPROJECT)) {
      run(`uv sync --project "${SCRIPTS_DIR}" --quiet`);
      if (verifyPython(venvPython)) {
        return {
          python: venvPython,
          type: 'uv',
          venv_ready: true,
          uv_project: SCRIPTS_DIR,
          uv_cmd: ['uv', 'run', '--project', SCRIPTS_DIR],
        };
      }
    }
  }

  // Strategy 2: system Python
  for (const py of ['python3', 'python']) {
    const v = run(`"${py}" --version 2>&1`);
    if (v && verifyPython(py)) {
      return { python: py, type: 'system', venv_ready: false, uv_project: null, uv_cmd: null };
    }
  }

  return null;
}

if (checkOnly) {
  const py = findWorkingPython();
  const result = {
    available: !!py,
    python: py?.python || null,
    venv_ready: py?.venv_ready ?? false,
    type: py?.type || null,
    uv_project: py?.uv_project || null,
    uv_cmd: py?.uv_cmd || null,
  };
  console.log(JSON.stringify(result));
  process.exit(result.available ? 0 : 1);
}

const py = findWorkingPython();
if (!py) {
  console.log(JSON.stringify({
    error: 'No working Python found',
    fix: 'Install Python 3.10+ with numpy and pandas (pip install numpy pandas matplotlib scipy), or install uv (https://docs.astral.sh/uv/)',
  }));
  process.exit(1);
}

console.log(JSON.stringify({
  python: py.python,
  type: py.type,
  ok: true,
  venv_ready: py.venv_ready,
  uv_project: py.uv_project,
  uv_cmd: py.uv_cmd,
}));
