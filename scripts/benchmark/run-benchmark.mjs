#!/usr/bin/env node
// run-benchmark.mjs — reviewer-facing entry point for the IDD diagnosis benchmark.
//
// Executes the full benchmark flow against the CURRENT pipeline:
//   S0  environment check
//   S1  prepare     — deterministic statistics per scenario (run dirs + digests)
//   S2  briefs      — emit blind-diagnosis task packs (statistics + process
//                     description ONLY; truth stays with the grader)
//   S3  pipeline    — the REAL industrial-analysis-auto pipeline executes per
//                     scenario in its prepared run dir (context-builder →
//                     data-processor → diagnostician → judge ∥ pre-audit →
//                     reporter → final audit → html-visualizer → html-reviewer
//                     → finalize); this stage verifies the full artifact set.
//                     Scripted note expansion is RETIRED (it fabricated
//                     artifacts and agent events).
//   S4  grade       — score each completed run dir against truth (independent
//                     scorer reading what the sub-skill agents actually wrote)
//                     + deterministic quality rubric
//   S5  aggregate   — metrics.json + reproducibility gate (REPRODUCIBLE required)
//   S6  report      — generate the HTML scoring report (with baselines)
//
// Usage:
//   node scripts/benchmark/run-benchmark.mjs                    # full flow (reuses run dirs)
//   node scripts/benchmark/run-benchmark.mjs --force-prepare    # re-prepares ALL run dirs (destroys completed pipeline artifacts!)
//   node scripts/benchmark/run-benchmark.mjs --skip-report      # no HTML rebuild
// Every stage fails fast with a non-zero exit on deviation.

import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';

const ROOT = path.resolve(import.meta.dirname, '..', '..');
const CASES = 'scripts/benchmark/cases/benchmark_cases.json';
const RUN_TIER = path.join(ROOT, 'scripts/benchmark/run-tier.mjs');
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
  for (const f of [CASES, 'scripts/benchmark/aggregate.mjs', 'scripts/benchmark/build-report.mjs', 'scripts/benchmark/check-leakage.mjs']) {
    if (!fs.existsSync(path.join(ROOT, f))) throw new Error(`missing: ${f}`);
  }
  if (!fs.existsSync(PY)) throw new Error(`missing python venv: ${PY} (run node .claude/shared/scripts/uv_env_setup.mjs)`);
  const all = JSON.parse(fs.readFileSync(path.join(ROOT, CASES), 'utf8'));
  const fault = all.cases.filter((c) => !c.control).length;
  const lit = all.cases.filter((c) => !c.control && c.literature_baseline).length;
  const tep = all.cases.filter((c) => c.dataset === 'tep' && !c.control);
  if (all.cases.length !== 12 || fault !== 9) throw new Error(`case contract: ${all.cases.length}/${fault} (expected 12/9)`);
  if (lit !== tep.length || tep.length < 6) throw new Error(`per-fault literature baseline (TEP subset): ${lit}/${tep.length} (expected ${tep.length}>=6)`);
  // truth-isolation sentinel (briefs + notes + run-dir user_context) — non-zero exit aborts the run
  run('node', [path.join(ROOT, 'scripts/benchmark/check-leakage.mjs'), '--tier', CASES], { timeout: 120000 });
  return `12 scenarios (9 fault + 3 control); TEP subset ${tep.length} with per-fault literature baselines; leakage sentinel PASS`;
});

// ── S1 prepare ──
stage('S1 prepare (deterministic statistics)', () => {
  // v2: default REUSES existing run dirs — in pipeline-execution mode the run
  // dir HOLDS the real pipeline artifacts, so force-rebuilding would destroy
  // completed scenarios. Re-prepare from scratch only with --force-prepare.
  if (flag('--force-prepare')) {
    run('node', [RUN_TIER, 'prepare', '--tier', CASES, '--force']);
    return 'run dirs re-prepared from scratch (--force-prepare)';
  }
  run('node', [RUN_TIER, 'prepare', '--tier', CASES]);
  return 'run dirs ready (existing reused)';
});

// ── S2 briefs + diagnosis instruction ──
stage('S2 briefs (blind task packs)', () => {
  run('node', [RUN_TIER, 'brief', '--tier', CASES]);
  return 'evidence briefs in results/benchmark/briefs/ (no truth inside)';
});

// ── S3 pipeline execution (real industrial-analysis-auto per scenario) ──
stage('S3 pipeline (industrial-analysis-auto executes per scenario)', () => {
  const all = JSON.parse(fs.readFileSync(path.join(ROOT, CASES), 'utf8'));
  let out;
  try {
    out = run('node', [RUN_TIER, 'pipeline', '--tier', CASES]);
  } catch (e) {
    out = (e.stdout || '') + (e.stderr || '');
  }
  const incomplete = (out.match(/NO RUN DIR|INCOMPLETE|ERROR/g) || []).length;
  if (incomplete) {
    throw new Error(
      `${incomplete} scenario run dir(s) lack full pipeline artifacts. Execute the REAL pipeline per scenario: ` +
      `in each prepared run dir (workspace/diagnostic-runs/bench_<case_id>), run skill://industrial-analysis-auto Steps 2-9 — ` +
      `dispatch the context-builder / data-processor / diagnostician / judge / report-reviewer / reporter / html-visualizer / ` +
      `html-reviewer sub-skills per their own protocols (html-visualizer/html-reviewer under the diagnostic-html-visualizer ` +
      `design system: render_manifest.json FIRST → page → html_selfcheck.json → independent review). ` +
      `Scripted note expansion is retired. Per-case gaps: node scripts/benchmark/run-tier.mjs pipeline`);
  }
  return `all ${all.cases.length} scenario run dirs carry full pipeline artifacts (ontology → diagnosis → judge/audit → report → html)`;
});

// ── S4 grade from real pipeline artifacts ──
stage('S4 grade (truth-comparison on agent-authored artifacts)', () => {
  const out = run('node', [RUN_TIER, 'commit', '--tier', CASES]);
  const lines = out.split('\n').filter((l) => l.startsWith('[commit]'));
  const skipped = out.match(/skipped (\d+)/);
  if (skipped && Number(skipped[1]) > 0) throw new Error(`${skipped[1]} scenario(s) skipped: ${out.split('\n').filter(l => l.includes('— ')).slice(0, 3).join(' / ')}`);
  if (lines.length !== 12) throw new Error(`graded ${lines.length} != 12`);
  // deterministic quality rubric on pipeline artifacts (agent-authored, never self-declared)
  run('node', [path.join(ROOT, 'scripts/benchmark/judge-rubric.mjs'), '--tier', CASES]);
  return lines.map((l) => l.replace('[commit] ', '')).join(' | ');
});

// ── S5 aggregate + reproducibility gate ──
stage('S5 aggregate + reproducibility gate', () => {
  run('node', ['scripts/benchmark/aggregate.mjs', '--tier-file', CASES]);
  const m = JSON.parse(fs.readFileSync(path.join(ROOT, 'results/benchmark/metrics.json'), 'utf8'));
  // v2 结构化门禁：只硬断言"全部场景真实执行且带执行证明"。
  // 结果质量指标（top1/control_pass/overconfident…）是**测量值**，如实报告，
  // 不设地板断言——预设结果地板会诱导为了过门禁而粉饰结果（v1 的教训）。
  for (const k of ['total_cases', 'executed']) {
    if (m[k] !== 12) throw new Error(`metrics.${k}=${JSON.stringify(m[k])} expected 12 — see gradings/`);
  }
  const v = run('node', [path.join(ROOT, 'scripts/benchmark/verify-repro.mjs'), '--tier', CASES]);
  if (!/REPRODUCIBLE/.test(v)) throw new Error(v.slice(-200));
  return `executed ${m.executed}/${m.total_cases} — Top-1 ${m.top1}/${m.fault_cases}, CDR ${m.cdr}, controls ${m.control_pass}/${m.control_cases}, false alarms ${m.false_alarms}, overconfident ${m.overconfident} — REPRODUCIBLE`;
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
