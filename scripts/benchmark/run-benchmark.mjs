#!/usr/bin/env node
// run-benchmark.mjs — reviewer-facing entry point for the IDD diagnosis benchmark.
//
// Executes the full benchmark flow against the CURRENT pipeline:
//   S0  environment check
//   S1  prepare     — deterministic statistics per scenario (run dirs + digests)
//   S2  briefs      — emit blind-diagnosis task packs (statistics + process
//                     description ONLY; truth stays with the grader) and print
//                     the diagnosis instruction for the executing agent
//   S3  diagnose    — the executing agent writes notes/<case>.note.json per the
//                     skill protocol (this step is agent-in-the-loop by design);
//                     this stage verifies notes exist and are schema-complete
//   S4  commit+gate — expand notes into pipeline artifacts, run pipeline gates,
//                     grade against truth (independent scorer)
//   S5  aggregate   — metrics.json + reproducibility gate (REPRODUCIBLE required)
//   S6  report      — generate the HTML scoring report (with baselines)
//
// Usage:
//   node scripts/benchmark/run-benchmark.mjs                 # full flow
//   node scripts/benchmark/run-benchmark.mjs --skip-prepare  # reuse run dirs
//   node scripts/benchmark/run-benchmark.mjs --skip-report   # no HTML rebuild
// Every stage fails fast with a non-zero exit on deviation.

import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';

const ROOT = path.resolve(import.meta.dirname, '..', '..');
const CASES = 'scripts/benchmark/cases/benchmark_cases.json';
const RUN_TIER = path.join(ROOT, '.claude/skills/industrial-benchmark-runner/scripts/run-tier.mjs');
const NOTES = path.join(ROOT, 'results/benchmark/notes');
const PY = path.join(ROOT, '.claude/shared/scripts/.venv/Scripts/python.exe');

const args = process.argv.slice(2);
const flag = (n) => args.includes(n);

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
  for (const f of [CASES, 'scripts/benchmark/aggregate.mjs', 'scripts/benchmark/build-report.mjs']) {
    if (!fs.existsSync(path.join(ROOT, f))) throw new Error(`missing: ${f}`);
  }
  if (!fs.existsSync(PY)) throw new Error(`missing python venv: ${PY} (run node .claude/shared/scripts/uv_env_setup.mjs)`);
  const all = JSON.parse(fs.readFileSync(path.join(ROOT, CASES), 'utf8'));
  const fault = all.cases.filter((c) => !c.control).length;
  if (all.cases.length !== 8 || fault !== 5) throw new Error(`case contract: ${all.cases.length}/${fault} (expected 8/5)`);
  return `8 scenarios (5 fault + 3 control)`;
});

// ── S1 prepare ──
stage('S1 prepare (deterministic statistics)', () => {
  if (!flag('--skip-prepare')) {
    run('node', [RUN_TIER, 'prepare', '--tier', CASES, '--force']);
  } else {
    run('node', [RUN_TIER, 'prepare', '--tier', CASES]);
  }
  return 'run dirs + digests ready';
});

// ── S2 briefs + diagnosis instruction ──
stage('S2 briefs (blind task packs)', () => {
  run('node', [RUN_TIER, 'brief', '--tier', CASES]);
  return 'evidence briefs in results/benchmark/briefs/ (no truth inside)';
});

// ── S3 diagnose (agent-in-the-loop) ──
stage('S3 diagnose (agent writes notes from briefs)', () => {
  const all = JSON.parse(fs.readFileSync(path.join(ROOT, CASES), 'utf8'));
  const missing = [];
  for (const c of all.cases) {
    const p = path.join(NOTES, `${c.case_id}.note.json`);
    if (!fs.existsSync(p)) { missing.push(c.case_id); continue; }
    const n = JSON.parse(fs.readFileSync(p, 'utf8'));
    const ok = n.diagnosis_type && n.ontology?.variables?.length && Array.isArray(n.hypotheses)
      && n.hypotheses.length >= 3 && n.primary_finding && n.confidence
      && n.hypotheses.filter((h) => h.verdict === 'surviving').length >= 1;
    if (!ok) missing.push(`${c.case_id} (incomplete)`);
  }
  if (missing.length) {
    throw new Error(
      `${missing.length} scenario(s) need on-the-spot diagnosis. ` +
      `For each, read results/benchmark/briefs/<case>.brief.json (statistical evidence ONLY — ` +
      `truth/keywords are withheld by design), reason per the industrial-diagnostician skill protocol, ` +
      `and write results/benchmark/notes/<case>.note.json (schema: run-tier.mjs notes template). ` +
      `Missing: ${missing.join(', ')}`);
  }
  return 'all 8 notes present and schema-complete';
});

// ── S4 commit + gate + grade ──
stage('S4 commit (pipeline artifacts + gates + grading)', () => {
  const out = run('node', [RUN_TIER, 'commit', '--tier', CASES]);
  const lines = out.split('\n').filter((l) => l.startsWith('[commit]'));
  const skipped = out.match(/skipped (\d+)/);
  if (skipped && Number(skipped[1]) > 0) throw new Error(`${skipped[1]} scenario(s) skipped`);
  if (lines.length !== 8) throw new Error(`committed ${lines.length} != 8`);
  return lines.map((l) => l.replace('[commit] ', '')).join(' | ');
});

// ── S5 aggregate + reproducibility gate ──
stage('S5 aggregate + reproducibility gate', () => {
  run('node', ['scripts/benchmark/aggregate.mjs', '--tier-file', CASES]);
  const m = JSON.parse(fs.readFileSync(path.join(ROOT, 'results/benchmark/metrics.json'), 'utf8'));
  const expect = { total_cases: 8, executed: 8, fault_cases: 5, control_cases: 3, top1: 5, topk: 5, cdr: 1, calibrated: 5, overconfident: 0, control_pass: 3, false_alarms: 0 };
  for (const [k, v] of Object.entries(expect)) {
    if (m[k] !== v) throw new Error(`metrics.${k}=${JSON.stringify(m[k])} expected ${JSON.stringify(v)} — see gradings/`);
  }
  const v = run('node', [path.join(ROOT, '.claude/skills/industrial-benchmark-runner/scripts/verify-repro.mjs'), '--tier', CASES]);
  if (!/REPRODUCIBLE/.test(v)) throw new Error(v.slice(-200));
  return `Top-1 ${m.top1}/${m.fault_cases}, CDR ${m.cdr}, controls ${m.control_pass}/${m.control_cases} — REPRODUCIBLE`;
});

// ── S6 report ──
if (!flag('--skip-report')) {
  stage('S6 report (HTML)', () => {
    run('node', ['scripts/benchmark/build-report.mjs']);
    return 'experience/benchmark-report.html regenerated';
  });
}

console.log(`
  ═══════════════════════════════════════════════════════════
  IDD Diagnosis Benchmark — PASSED
  Scoring report : experience/benchmark-report.html
  Metrics        : results/benchmark/metrics.json
  Per-scenario   : results/benchmark/gradings/*.json (truth-compared)
  Exec. proofs   : per-run .pipeline_events.jsonl (gate-checked)
  ═══════════════════════════════════════════════════════════`);
