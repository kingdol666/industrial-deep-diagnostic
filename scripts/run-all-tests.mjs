#!/usr/bin/env node
// run-all-tests.mjs — the root test aggregate (`npm test` at the repo root).
//
// Runs every test surface of this repository SEQUENTIALLY, each with a clear
// header, and prints a final summary. Exits non-zero if any step fails.
//
// Steps:
//   1 backend   — `npm test` in app/backend (node --test; the run prints its own case count)
//   2 shared    — node scripts/test-shared-scripts.mjs (ontology store / manifest repair / validate)
//   3 skills    — node scripts/test-skills.mjs (skill-package contract gates G1-G7)
//   4 mirrors   — node scripts/sync-harness-skills.mjs --check (mirror drift guard)
//   5 docs      — node scripts/check-doc-numbers.mjs (documentation-truth guard)
//   6 runtimes  — every allowlisted skill runtime battery via the shared uv venv
//                 (.claude/skills/<name>/tests/run_tests.py)
//
// Flags:
//   --fast        skip the heavy steps (backend npm test + all python runtime batteries)
//   --no-backend  skip only the backend step (node/python steps still run)
//   --list        print the steps and the runtime allowlist, then exit 0
//
// The runtime allowlist is HARDCODED on purpose: each entry was verified green
// against the untouched skill tree before being added. A runner that is red for
// pre-existing reasons must stay OUT of this list (a known-red runner would only
// mask real regressions) — fix it first, then add it here.

import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(import.meta.dirname, '..');
const argv = process.argv.slice(2);
const has = (f) => argv.includes(f);
const FAST = has('--fast');
const NO_BACKEND = FAST || has('--no-backend');
const NODE = process.execPath;

// ── runtime battery allowlist (each entry verified exit 0 in this tree) ──
// Canonical runners are `.claude/skills/<name>/tests/run_tests.py`; a few skills
// additionally ship standalone `tests/test_*.py` module batteries.
const RUNTIME_BATTERY_ALLOWLIST = [
  '.claude/skills/darwin-skill/tests/run_tests.py',
  '.claude/skills/industrial-analysis-enhance-auto/tests/run_tests.py',
  '.claude/skills/industrial-data-preprocessor/tests/run_tests.py',
  '.claude/skills/industrial-deep-analysis/tests/run_tests.py',
  '.claude/skills/industrial-doe-analyzer/tests/run_tests.py',
  '.claude/skills/industrial-enhanced-html-reviewer/tests/run_tests.py',
  '.claude/skills/industrial-enhanced-html-visualizer/tests/run_tests.py',
  '.claude/skills/industrial-hetero-preprocessor/tests/run_tests.py',
  '.claude/skills/industrial-html-reviewer/tests/run_tests.py',
  '.claude/skills/industrial-html-visualizer/tests/run_tests.py',
  '.claude/skills/industrial-line-stability-report/tests/run_tests.py',
  '.claude/skills/industrial-ontology-builder/tests/run_tests.py',
  '.claude/skills/industrial-optimizer-loop/tests/run_tests.py',
  '.claude/skills/industrial-physical-auditor/tests/run_tests.py',
  '.claude/skills/industrial-physics-bridge/tests/run_tests.py',
  '.claude/skills/industrial-sentinel/tests/run_tests.py',
  '.claude/skills/industrial-tuning-memory/tests/run_tests.py',
  '.claude/skills/rag-knowledge-builder/tests/run_tests.py',
  // standalone module batteries (own __main__ entry, no run_tests.py wrapper)
  '.claude/skills/industrial-data-processor/tests/test_hetero_heatmap.py',
  '.claude/skills/industrial-data-preprocessor/tests/test_preprocessor.py',
  '.claude/skills/industrial-deep-analysis/tests/test_inference_engine.py',
];

// ── python runtime (shared uv project — same resolution as the skill docs) ──
function resolvePython() {
  const r = spawnSync(NODE, [path.join(ROOT, '.claude/shared/scripts/uv_env_setup.mjs'), '--check-only'], {
    cwd: ROOT, encoding: 'utf8', timeout: 300000,
  });
  if (r.status !== 0 || !r.stdout) return null;
  try {
    const info = JSON.parse(r.stdout.trim().split('\n').pop());
    if (!info.available) return null;
    if (Array.isArray(info.uv_cmd) && info.uv_cmd.length) return { cmd: info.uv_cmd[0], prefix: [...info.uv_cmd.slice(1), 'python'] };
    if (info.python) return { cmd: info.python, prefix: [] };
  } catch { /* fall through */ }
  return null;
}

const npmCmd = process.platform === 'win32' ? 'npm.cmd' : 'npm';
const steps = [];
steps.push({
  name: 'backend',
  title: 'Backend test suite (app/backend)',
  cmd: npmCmd, args: ['test'], cwd: path.join(ROOT, 'app', 'backend'),
  skip: NO_BACKEND, why: NO_BACKEND ? '--fast/--no-backend' : '',
});
for (const [name, script, title] of [
  ['shared-scripts', 'scripts/test-shared-scripts.mjs', 'Shared-script safety tests (store / manifest / validate)'],
  ['skill-contracts', 'scripts/test-skills.mjs', 'Skill package contract gates (G1-G7)'],
  ['mirror-drift', 'scripts/sync-harness-skills.mjs', 'Harness skill mirrors in sync (.claude -> .agents/.hermes)'],
  ['doc-numbers', 'scripts/check-doc-numbers.mjs', 'Documentation-truth guard (counts / CLI verbs / retired scripts)'],
]) {
  steps.push({ name, title, cmd: NODE, args: [path.join(ROOT, script), ...(name === 'mirror-drift' ? ['--check'] : [])], cwd: ROOT, skip: false, why: '' });
}

const runnerSteps = RUNTIME_BATTERY_ALLOWLIST.map((rel) => {
  const parts = rel.split('/');                       // .claude/skills/<skill>/tests/<file>
  const skill = parts[2];
  const file = parts[parts.length - 1];
  return {
    rel,
    name: file === 'run_tests.py' ? skill : `${skill}/${file.replace(/\.py$/, '')}`,
    runner: path.join(ROOT, rel),
  };
});

if (has('--list')) {
  console.log('run-all-tests — steps');
  for (const s of steps) console.log(`  ${s.name.padEnd(14)} ${s.title}${s.skip ? '  [skipped]' : ''}`);
  console.log(`  runtimes       ${runnerSteps.length} skill batteries:`);
  for (const r of runnerSteps) console.log(`                   ${r.rel}`);
  process.exit(0);
}

let python = null;
function stepHeader(i, total, step) {
  console.log(`\n${'═'.repeat(72)}`);
  console.log(`[${i}/${total}] ${step.name} — ${step.title}`);
  console.log('═'.repeat(72));
}

const results = [];
function record(name, code, secs, note = '') {
  results.push({ name, code, secs, note });
  const mark = code === 0 ? 'PASS' : 'FAIL';
  console.log(`\n--- ${mark} ${name} (${secs}s)${note ? ` ${note}` : ''}`);
}

function runStep(step) {
  const t0 = Date.now();
  if (step.skip) { record(step.name, 0, 0, `skipped (${step.why})`); return true; }
  const r = spawnSync(step.cmd, step.args, { cwd: step.cwd, stdio: 'inherit', timeout: 900000 });
  const secs = Math.round((Date.now() - t0) / 1000);
  if (r.error) { console.error(`  spawn error: ${r.error.message}`); record(step.name, 1, secs, `spawn error: ${r.error.message}`); return false; }
  record(step.name, r.status ?? 1, secs);
  return (r.status ?? 1) === 0;
}

console.log('run-all-tests — repository-wide test aggregate');
console.log(`  mode: ${FAST ? '--fast (backend + python batteries skipped)' : NO_BACKEND ? '--no-backend (python batteries still run)' : 'full'}`);

const totalSteps = steps.length + (FAST ? 0 : runnerSteps.length);
let failed = 0;
let idx = 0;

for (const step of steps) {
  idx += 1;
  stepHeader(idx, totalSteps, step);
  if (!runStep(step)) failed += 1;
}

if (!FAST) {
  python = resolvePython();
  if (!python) {
    console.error('\nFATAL: no working python for the shared venv (uv_env_setup --check-only failed)');
    console.error('       the runtime batteries cannot run — fix the python env or use --fast to skip them');
    record('python-env', 1, 0, 'uv_env_setup --check-only failed');
    failed += 1;
  } else {
    console.log(`\npython runtime: ${python.cmd} ${python.prefix.join(' ')} (shared uv project)`);
    for (const r of runnerSteps) {
      idx += 1;
      const step = { name: `skill:${r.name}`, title: `${r.rel}`, cmd: python.cmd, args: [...python.prefix, r.runner], cwd: ROOT, skip: false };
      stepHeader(idx, totalSteps, step);
      if (!fs.existsSync(r.runner)) {
        console.error(`  MISSING runner: ${r.runner} (allowlist entry must be updated)`);
        record(step.name, 1, 0, 'runner file missing');
        failed += 1;
        continue;
      }
      if (!runStep(step)) failed += 1;
    }
  }
}

// ── summary ──
console.log(`\n${'═'.repeat(72)}`);
console.log('SUMMARY');
console.log('═'.repeat(72));
const pad = Math.max(...results.map((r) => r.name.length));
for (const r of results) {
  console.log(`  ${r.code === 0 ? 'PASS' : 'FAIL'}  ${r.name.padEnd(pad)}  ${String(r.secs).padStart(4)}s  ${r.note}`);
}
const passed = results.filter((r) => r.code === 0).length;
console.log(`\n${passed}/${results.length} steps passed${failed ? ` — ${failed} FAILED` : ' — ALL GREEN'}`);
process.exit(failed ? 1 : 0);
