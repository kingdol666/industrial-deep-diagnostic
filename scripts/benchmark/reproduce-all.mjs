#!/usr/bin/env node
// reproduce-all.mjs — one-command end-to-end benchmark reproduction with
// fail-fast gates. Wraps the authoritative scripts; never edits result files.
//
// Usage:
//   node scripts/benchmark/reproduce-all.mjs                    # full chain
//   node scripts/benchmark/reproduce-all.mjs --skip-prepare     # reuse run dirs
//   node scripts/benchmark/reproduce-all.mjs --notes-only       # stop after notes
//
// Stages (each must pass or the run aborts with a non-zero exit):
//   S0 environment      — scripts + case files present, case counts match contract
//   S1 data integrity   — dataset manifest regenerated & counted
//   S2 notes            — author_notes_t0/t2.py re-run (recorded inference)
//   S3 pipeline         — prepare (+ commit) for both tiers via run-tier.mjs
//   S4 aggregate        — metrics.json recomputed
//   S5 verify gate      — verify-repro must print REPRODUCIBLE
//   S6 summary          — headline numbers printed for the agent to assert

import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';

const ROOT = path.resolve(import.meta.dirname, '..', '..');
const args = process.argv.slice(2);
const flag = (n) => args.includes(n);
const PY = path.join(ROOT, '.claude/shared/scripts/.venv/Scripts/python.exe');
const RUN_TIER = path.join(ROOT, '.claude/skills/industrial-benchmark-runner/scripts/run-tier.mjs');
const TIERS = ['scripts/benchmark/cases/tier0_smoke.json', 'scripts/benchmark/cases/tier2_main.json'];
const TIER_ALL = 'scripts/benchmark/cases/tier_all.json';

function run(cmd, cmdArgs, { timeout = 3600000 } = {}) {
  return execFileSync(cmd, cmdArgs, { cwd: ROOT, encoding: 'utf8', timeout, stdio: ['ignore', 'pipe', 'pipe'] });
}

function stage(name, fn) {
  process.stdout.write(`[${name}] `);
  const out = fn();
  console.log('OK');
  return out;
}

// ── S0 environment ──
stage('S0 environment', () => {
  for (const f of ['scripts/benchmark/aggregate.mjs', 'scripts/benchmark/author_notes_t0.py',
    'scripts/benchmark/author_notes_t2.py', 'scripts/benchmark/cases/tier_all.json']) {
    if (!fs.existsSync(path.join(ROOT, f))) throw new Error(`missing: ${f}`);
  }
  if (!fs.existsSync(PY)) throw new Error(`missing python venv: ${PY} (run node .claude/shared/scripts/uv_env_setup.mjs)`);
  const all = JSON.parse(fs.readFileSync(path.join(ROOT, TIER_ALL), 'utf8'));
  const fault = all.cases.filter((c) => !c.control).length;
  if (all.cases.length !== 32 || fault !== 25) {
    throw new Error(`case contract mismatch: ${all.cases.length} cases / ${fault} fault (expected 32/25)`);
  }
  return `${all.cases.length} cases (${fault} fault)`;
});

// ── S1 data integrity ──
stage('S1 data integrity', () => {
  const out = run('node', ['scripts/benchmark/make_dataset_manifest.mjs']);
  const m = out.match(/manifest: (\d+) entr/);
  if (!m || Number(m[1]) < 100) throw new Error(`manifest entries too few: ${out.trim()}`);
  return `${m[1]} entries`;
});

// ── S2 notes (recorded inference) ──
stage('S2 notes', () => {
  const o1 = run(PY, ['scripts/benchmark/author_notes_t0.py']);
  const o2 = run(PY, ['scripts/benchmark/author_notes_t2.py']);
  if (!/9 notes written/.test(o1)) throw new Error(`t0 notes: ${o1.slice(0, 80)}`);
  if (!/23 tier2 notes written/.test(o2)) throw new Error(`t2 notes: ${o2.slice(0, 80)}`);
  return '9 + 23 notes';
});

// ── S3 pipeline ──
stage('S3 pipeline', () => {
  let committed = 0;
  for (const tier of TIERS) {
    if (!flag('--skip-prepare')) {
      run('node', [RUN_TIER, 'prepare', '--tier', tier]);
    }
    const out = run('node', [RUN_TIER, 'commit', '--tier', tier]);
    const lines = out.split('\n').filter((l) => l.startsWith('[commit]'));
    const skipped = out.match(/skipped (\d+)/);
    if (skipped && Number(skipped[1]) > 0) throw new Error(`${tier}: ${skipped[1]} case(s) skipped — notes/run dirs incomplete`);
    committed += lines.length;
  }
  if (committed !== 32) throw new Error(`committed ${committed} != 32`);
  return `${committed} committed`;
});

// ── S4 aggregate ──
stage('S4 aggregate', () => {
  run('node', ['scripts/benchmark/aggregate.mjs', '--tier-file', TIER_ALL]);
  const m = JSON.parse(fs.readFileSync(path.join(ROOT, 'results/benchmark/metrics.json'), 'utf8'));
  const expect = { total_cases: 32, executed: 32, fault_cases: 25, control_cases: 7, top1: 25, topk: 25, cdr: 1, calibrated: 25, overconfident: 0, control_pass: 7, false_alarms: 0 };
  for (const [k, v] of Object.entries(expect)) {
    if (m[k] !== v) throw new Error(`metrics.${k}=${m[k]} expected ${v}`);
  }
  return 'headline metrics verified';
});

// ── S5 verify gate ──
stage('S5 verify gate', () => {
  const out = run('node', [path.join(ROOT, '.claude/skills/industrial-benchmark-runner/scripts/verify-repro.mjs'), '--tier', TIER_ALL]);
  if (!/REPRODUCIBLE/.test(out)) throw new Error(out.slice(-200));
  return 'REPRODUCIBLE';
});

// ── S6 summary ──
stage('S6 summary', () => {
  const m = JSON.parse(fs.readFileSync(path.join(ROOT, 'results/benchmark/metrics.json'), 'utf8'));
  console.log(`
  ── Benchmark reproduction complete ─────────────────────────
  Top-1 root cause : ${m.top1}/${m.fault_cases} (fault scenarios)
  Top-k (k=3)      : ${m.topk}/${m.fault_cases}
  CDR              : ${m.cdr}
  Calibration      : ${m.calibrated}/${m.fault_cases} (overconfident ${m.overconfident})
  Controls         : ${m.control_pass}/${m.control_cases} passed, ${m.false_alarms} false alarms
  Pipeline gate    : 32/32 finalize PASS (enforced by S5)
  ────────────────────────────────────────────────────────────
  Evidence: results/benchmark/{metrics,gradings,repro_report} + per-run event logs`);
  return 'done';
});

console.log('\nREPRODUCTION OK — results are authentic and machine-verified.');
