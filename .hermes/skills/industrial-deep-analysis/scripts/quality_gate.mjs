#!/usr/bin/env node
// quality_gate.mjs — deterministic quality gate for industrial-deep-analysis
// (the E1-E4 deep-analysis layer).
//
// Thin by design: (a) checks that the run dir carries the E1-E4 artifacts the
// SKILL.md requires and that they parse, then (b) delegates the authoritative
// structural verification to the skill's own Python verifier
// `scripts/verify_enhancement.py` (which exits non-zero naming the failing
// rule) and maps its exit code into the gate verdict + JSON report.
//
// Usage:
//   node quality_gate.mjs --run-dir <RUN_DIR> [--python <interpreter>]
//
// Exit codes (house convention):
//   0 ok        — all E1-E4 artifacts present, parse, and verify_enhancement.py passed
//   1 hard error — bad inputs (no/unreadable --run-dir) or no usable Python
//                  interpreter could run the verifier
//   2 undetermined — the deep-analysis enhancement was not run for this run
//                  dir (none of the E1-E4 artifacts exist)
//   3 gate-fail — the chain ran but violates its contract: some artifacts are
//                  missing/corrupt, or verify_enhancement.py reported failures
//
// Python resolution order: --python <interp> → `uv run --project
// <repo>/.claude/shared/scripts python` → the shared venv interpreter
// (Scripts/python.exe on Windows, bin/python on POSIX) → plain `python`.
// The verifier is stdlib-only, so any Python ≥3.10 works.

import { spawnSync } from 'child_process';
import { existsSync, readFileSync } from 'fs';
import { dirname, join, resolve } from 'path';
import { fileURLToPath } from 'url';

const HERE = dirname(fileURLToPath(import.meta.url));
const REPO = resolve(HERE, '..', '..', '..', '..');
const SHARED_SCRIPTS = join(REPO, '.claude', 'shared', 'scripts');
const VERIFIER = join(HERE, 'verify_enhancement.py');

const args = process.argv.slice(2);
const argOf = (k) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : undefined; };
const RUN_DIR_ARG = argOf('--run-dir');
const PYTHON_ARG = argOf('--python');

const FAILS = [];
const NOTES = [];
const fail = (id, msg) => FAILS.push(`${id}: ${msg}`);
const note = (msg) => NOTES.push(msg);

function emit(verdict, reason, extra = {}) {
  console.log(JSON.stringify({
    gate: 'deep_analysis_quality_gate',
    verdict,
    ...(reason ? { reason } : {}),
    fails: FAILS,
    notes: NOTES,
    ...extra,
  }, null, 2));
  process.exit({ ok: 0, hard_error: 1, undetermined: 2, gate_fail: 3 }[verdict]);
}

process.on('uncaughtException', (e) => {
  fail('GATE', `unhandled error: ${e.message}`);
  emit('gate_fail', null);
});

// ── args ───────────────────────────────────────────────────────────────
if (!RUN_DIR_ARG) {
  FAILS.push('ARGS: missing --run-dir <RUN_DIR>');
  emit('hard_error', 'usage: node quality_gate.mjs --run-dir <RUN_DIR> [--python <interpreter>]');
}
const RUN_DIR = resolve(RUN_DIR_ARG);
if (!existsSync(RUN_DIR)) {
  FAILS.push('ARGS', `run dir does not exist: ${RUN_DIR}`);
  emit('hard_error', null);
}
const ENH = join(RUN_DIR, 'enhancement');

// ── (a) E1-E4 artifacts required by SKILL.md ───────────────────────────
// [relative path, human label, required top-level key (array), stage]
const ARTIFACTS = [
  ['enhancement/analysis_coverage.json', 'E1 coverage', 'columns'],
  ['enhancement/derived_features.json', 'E2 derived features', 'features'],
  ['enhancement/deep_data_analysis.json', 'E3+E4 relationships & tradeoffs', 'relationships'],
  ['enhancement/association_graph.json', 'E3.5 association graph', 'nodes'],
];
const CSV_ARTIFACT = 'enhancement/derived_data.csv';
const present = [];
const missing = [];
for (const [rel, label, key, stage] of ARTIFACTS) {
  if (existsSync(join(RUN_DIR, rel))) present.push([rel, label, key, stage]);
  else missing.push([rel, label, stage]);
}
const csvPath = join(RUN_DIR, CSV_ARTIFACT);
const csvPresent = existsSync(csvPath);

// stage identity: zero artifacts => the enhancement never ran
if (present.length === 0 && !csvPresent) {
  emit('undetermined', `${ENH} has none of the E1-E4 artifacts (${ARTIFACTS.map(([r]) => r).join(', ')}, ${CSV_ARTIFACT}) — the deep-analysis enhancement was not run for this run dir`);
}

// local structural checks (fast, structured; verify_enhancement.py below is authoritative)
for (const [rel, label, key, stage] of present) {
  try {
    const data = JSON.parse(readFileSync(join(RUN_DIR, rel), 'utf-8'));
    if (!Array.isArray(data[key])) {
      fail('A1', `${rel} (${label}) has no \`${key}\` array — artifact does not parse as the ${stage} output`);
    } else if (data[key].length === 0) {
      note(`A1: ${rel} \`${key}\` array is empty (verify_enhancement.py decides whether that is fatal)`);
    }
  } catch (e) {
    fail('A1', `${rel} (${label}) is unparseable JSON: ${e.message}`);
  }
}
for (const [rel, label, stage] of missing) fail('A2', `missing artifact: ${rel} (${label}, ${stage})`);
if (!csvPresent) fail('A2', `missing artifact: ${CSV_ARTIFACT} (E2 derived data table)`);
if (csvPresent) {
  try {
    const head = readFileSync(csvPath, 'utf-8').replace(/^\uFEFF/, '').split(/\r?\n/)[0] || '';
    if (!head.trim() || head.split(',').every((c) => !c.trim())) fail('A1', `${CSV_ARTIFACT} has no header row`);
  } catch (e) {
    fail('A1', `${CSV_ARTIFACT} unreadable: ${e.message}`);
  }
}

// ── (b) delegate to scripts/verify_enhancement.py ──────────────────────
// The verifier is the authoritative rule set (E1 statuses, E2 computed-feature
// membership, E3 validity flags/q_values, E4 tradeoff fields, E3.5 graph
// integrity); it exits non-zero naming the failing rule.
function interpreterCandidates() {
  const cands = [];
  if (PYTHON_ARG) cands.push({ cmd: PYTHON_ARG, args: [], label: `--python ${PYTHON_ARG}` });
  cands.push({
    cmd: 'uv',
    args: ['run', '--project', SHARED_SCRIPTS, 'python'],
    label: 'uv run --project .claude/shared/scripts python',
  });
  const venv = process.platform === 'win32'
    ? join(SHARED_SCRIPTS, '.venv', 'Scripts', 'python.exe')
    : join(SHARED_SCRIPTS, '.venv', 'bin', 'python');
  if (existsSync(venv)) cands.push({ cmd: venv, args: [], label: venv });
  cands.push({ cmd: 'python', args: [], label: 'python (PATH)' });
  return cands;
}

const LOOKS_UNAVAILABLE = /ENOENT|not recognized|No such file|command not found|failed to (spawn|execute|run)|program not found/i;

function runVerifier() {
  let lastDiag = null;
  for (const cand of interpreterCandidates()) {
    const r = spawnSync(cand.cmd, [...cand.args, VERIFIER, '--run-dir', RUN_DIR], {
      encoding: 'utf-8', timeout: 120000,
    });
    if (r.error && LOOKS_UNAVAILABLE.test(String(r.error.message))) {
      lastDiag = `${cand.label}: ${r.error.message}`;
      continue;
    }
    if (r.status === null) {
      // killed (timeout) or spawn failure with an unhelpful message
      if (!r.stdout && !r.stderr) { lastDiag = `${cand.label}: no output (timeout or spawn failure)`; continue; }
    }
    let verdict = null;
    try {
      const line = String(r.stdout || '').trim().split(/\r?\n/).find((l) => l.startsWith('{'));
      verdict = line ? JSON.parse(line) : null;
    } catch { verdict = null; }
    // re-try only when the invocation itself produced nothing usable AND an
    // availability-style error is present in stderr (never when the verifier
    // ran and reported real failures)
    if (!verdict && r.status !== 0 && LOOKS_UNAVAILABLE.test(String(r.stderr || ''))) {
      lastDiag = `${cand.label}: ${String(r.stderr).trim().split(/\r?\n/)[0]}`;
      continue;
    }
    return { cand, result: r, verdict };
  }
  return { cand: null, result: null, verdict: null, lastDiag };
}

const ran = runVerifier();
if (!ran.cand) {
  FAILS.push('PY1', `no usable Python interpreter for verify_enhancement.py (${ran.lastDiag || 'all candidates failed'})`);
  FAILS.push('PY1', `hint: install uv or run inside the repo venv — uv run --project .claude/shared/scripts python ${VERIFIER} --run-dir <RUN_DIR>`);
  emit('hard_error', 'cannot execute scripts/verify_enhancement.py');
}
const { cand, result, verdict } = ran;
note(`delegated to verify_enhancement.py via ${cand.label}`);

const delegation = {
  interpreter: cand.label,
  exit_code: result.status,
  ok: verdict ? verdict.ok === true : null,
  n_failures: verdict && Number.isFinite(verdict.n_failures) ? verdict.n_failures : null,
};

if (result.status === 0) {
  if (!verdict || verdict.ok !== true) {
    fail('PY2', 'verify_enhancement.py exited 0 without a parseable {"ok": true} verdict');
  }
} else {
  const detail = verdict
    ? `verify_enhancement.py reported ${verdict.n_failures ?? '?'} failure(s)`
    : `verify_enhancement.py exited ${result.status} without a JSON verdict (crash on corrupt artifacts?)`;
  fail('PY2', detail);
  const tail = String(result.stdout || result.stderr || '')
    .trim().split(/\r?\n/).filter((l) => l.startsWith('FAIL:') || l.startsWith('{'))
    .slice(0, 12);
  for (const l of tail) note(l.slice(0, 300));
}

// ── verdict ────────────────────────────────────────────────────────────
if (FAILS.length) emit('gate_fail', null, { delegation });
emit('ok', null, {
  artifacts: {
    coverage: 'enhancement/analysis_coverage.json',
    derived_features: 'enhancement/derived_features.json',
    derived_data: CSV_ARTIFACT,
    deep_data_analysis: 'enhancement/deep_data_analysis.json',
    association_graph: 'enhancement/association_graph.json',
  },
  delegation,
});
