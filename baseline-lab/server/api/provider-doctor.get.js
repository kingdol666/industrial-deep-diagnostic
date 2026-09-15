// GET /api/provider-doctor — diagnose LLM provider discovery inside the server.
//
// Provider detection depends on PATH resolution and env vars, both of which can
// differ between the shell you launch from and the bundled server runtime. This
// route reports exactly what the server process can see, plus an explicit
// directory scan, so a "no provider" result is explainable rather than opaque.

import { defineEventHandler } from 'h3';
import fs from 'node:fs';
import path from 'node:path';
import { detectProviders, resolveProvider, CLI_HARNESSES } from '../utils/llm/provider.mjs';

function findIn(dir, bin) {
  const exts = ['.exe', '.cmd', '.bat', '.ps1', ''];
  const hits = [];
  for (const e of exts) {
    const p = path.join(dir, bin + e);
    try {
      fs.accessSync(p, fs.constants.F_OK);
      hits.push(p);
    } catch { /* absent */ }
  }
  return hits;
}

export default defineEventHandler(() => {
  const rawPath = process.env.PATH || process.env.Path || '';
  const dirs = rawPath.split(path.delimiter).filter(Boolean);

  const cliDiagnostics = {};
  for (const [id, spec] of Object.entries(CLI_HARNESSES)) {
    const hits = [];
    for (const d of dirs) {
      const found = findIn(d, spec.bin);
      if (found.length) hits.push(...found);
    }
    cliDiagnostics[id] = { bin: spec.bin, found_on_path: hits };
  }

  // Extra locations worth checking when PATH is incomplete (e.g. a bundled
  // server runtime that inherited a reduced environment).
  const extraDirs = [
    path.join(process.env.USERPROFILE || '', '.local', 'bin'),
    path.join(process.env.USERPROFILE || '', '.bun', 'bin'),
    path.join(process.env.APPDATA || '', 'npm'),
    process.env.LOCALAPPDATA ? path.join(process.env.LOCALAPPDATA, 'hermes', 'bin') : '',
  ].filter(Boolean);

  const extra = {};
  for (const d of extraDirs) {
    for (const [id, spec] of Object.entries(CLI_HARNESSES)) {
      const found = findIn(d, spec.bin);
      if (found.length) {
        extra[id] = extra[id] || [];
        extra[id].push(...found);
      }
    }
  }

  let resolved = null;
  let resolveError = null;
  try {
    resolved = resolveProvider({});
  } catch (err) {
    resolveError = String(err && err.message ? err.message : err);
  }

  return {
    cwd: process.cwd(),
    platform: process.platform,
    path_delimiter: path.delimiter,
    path_entry_count: dirs.length,
    path_entries: dirs,
    path_contains_local_bin: rawPath.includes('.local'),
    env_llm: {
      BASELINE_LLM_PROVIDER: process.env.BASELINE_LLM_PROVIDER || null,
      BASELINE_LLM_MODEL: process.env.BASELINE_LLM_MODEL || null,
      BASELINE_LLM_BASE_URL: process.env.BASELINE_LLM_BASE_URL ? '(set)' : null,
      BASELINE_LLM_API_KEY: process.env.BASELINE_LLM_API_KEY ? '(set)' : null,
      BASELINE_LLM_CLI_PATH: process.env.BASELINE_LLM_CLI_PATH || null,
    },
    cli_diagnostics: cliDiagnostics,
    extra_dirs_scanned: extraDirs,
    found_in_extra_dirs: extra,
    detected: detectProviders({}),
    resolved: resolved ? { id: resolved.id, detail: resolved.detail } : null,
    resolve_error: resolveError,
    remedy:
      'If a harness is installed but not found, set BASELINE_LLM_CLI_PATH to the ' +
      'absolute binary path, or add its directory to PATH before starting the lab.',
  };
});
