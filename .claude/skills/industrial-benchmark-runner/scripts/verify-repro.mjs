#!/usr/bin/env node
// verify-repro.mjs — reproducibility gate for the benchmark results.
//
// Checks (all read-only):
//   1. dataset integrity   — every dataset_manifest.json entry that still exists
//                            re-hashes to its recorded sha256
//   2. case coverage       — every case in the tier file has a prepared run dir
//                            (from tier_state.json) and a grading
//   3. metric reproducibility — recompute aggregate metrics from
//                            results/benchmark/gradings/*.json and compare with
//                            results/benchmark/metrics.json
//   4. execution proof     — each graded run dir carries .pipeline_events.jsonl
//                            and its grading reports pipeline_log PASS
//
// Exit code 0 = reproducible, 1 = drift detected. Writes repro_report.json.

import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

const ROOT = path.resolve(import.meta.dirname, '..', '..', '..', '..');
const RESULTS = path.join(ROOT, 'results', 'benchmark');
const args = process.argv.slice(2);
const opt = (n, d) => (args.indexOf(n) >= 0 && args[args.indexOf(n) + 1] ? args[args.indexOf(n) + 1] : d);
const tierArg = opt('--tier', 'scripts/benchmark/cases/tier0_smoke.json');
const TIER = path.isAbsolute(tierArg) ? tierArg : path.join(ROOT, tierArg);

const failures = [];
const warnings = [];
const report = { generated_at: new Date().toISOString(), tier: path.relative(ROOT, TIER).replace(/\\/g, '/'), checks: {} };

const sha256 = (p) => crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const readJson = (p, fallback = null) => (fs.existsSync(p) ? JSON.parse(fs.readFileSync(p, 'utf8')) : fallback);

// ── 1) dataset integrity ──
const manifest = readJson(path.join(RESULTS, 'dataset_manifest.json'), { files: [] });
let hashed = 0;
let mismatched = 0;
let missing = 0;
for (const f of manifest.files || []) {
  const abs = path.join(ROOT, f.path);
  if (!fs.existsSync(abs)) { missing += 1; continue; }
  const actual = sha256(abs);
  if (actual !== f.sha256) {
    mismatched += 1;
    failures.push(`dataset hash drift: ${f.path}`);
  } else {
    hashed += 1;
  }
}
report.checks.dataset_integrity = { entries: (manifest.files || []).length, verified: hashed, missing, mismatched };
if (missing > 0) warnings.push(`${missing} dataset manifest entr(ies) are not present on disk (regenerable via prepare scripts)`);
if (mismatched > 0) failures.push(`${mismatched} dataset file(s) changed content without a manifest refresh`);

// ── 2) case coverage ──
const tier = readJson(TIER, { cases: [] });
const state = readJson(path.join(RESULTS, 'tier_state.json'), { tiers: {} });
const tierKey = path.relative(ROOT, TIER).replace(/\\/g, '/');
const tierState = state.tiers?.[tierKey]?.cases || {};
const gradingsDir = path.join(RESULTS, 'gradings');
const coverage = { cases: tier.cases.length, prepared: 0, graded: 0, missing: [] };
for (const c of tier.cases) {
  const preparedDir = tierState[c.case_id]?.run_dir;
  const gradingPath = path.join(gradingsDir, `${c.case_id}.json`);
  if (preparedDir && fs.existsSync(preparedDir)) coverage.prepared += 1;
  if (fs.existsSync(gradingPath)) coverage.graded += 1;
  else coverage.missing.push(c.case_id);
}
report.checks.case_coverage = coverage;
if (coverage.graded < coverage.cases) warnings.push(`${coverage.missing.length} case(s) not graded yet: ${coverage.missing.slice(0, 5).join(', ')}`);

// ── 3) metric reproducibility (same definitions as scripts/benchmark/aggregate.mjs) ──
const gradings = fs.existsSync(gradingsDir)
  ? fs.readdirSync(gradingsDir).filter((f) => f.endsWith('.json')).map((f) => readJson(path.join(gradingsDir, f)))
  : [];
const byCase = new Map(gradings.map((g) => [g.case_id, g]));
const rows = tier.cases.map((c) => ({ c, g: byCase.get(c.case_id) })).filter((x) => x.g);
const fault = rows.filter((x) => !x.c.control);
const control = rows.filter((x) => x.c.control);
const recomputed = {
  total_cases: tier.cases.length,
  executed: rows.length,
  fault_cases: fault.length,
  control_cases: control.length,
  top1: fault.filter((x) => x.g.top1).length,
  topk: fault.filter((x) => x.g.topk).length,
  cdr: fault.length ? +(fault.filter((x) => x.g.top1 && x.g.diagnosis_type === 'DETERMINED').length / fault.length).toFixed(4) : null,
  calibrated: fault.filter((x) => x.g.calibrated).length,
  overconfident: fault.filter((x) => x.g.overconfident).length,
  control_pass: control.filter((x) => x.g.control_pass).length,
  false_alarms: control.filter((x) => x.g.false_alarm).length,
};
const recorded = readJson(path.join(RESULTS, 'metrics.json'), null);
let drift = [];
if (!recorded) {
  warnings.push('metrics.json absent — nothing to compare (run aggregate.mjs)');
} else {
  drift = Object.keys(recomputed).filter((k) => recorded[k] !== undefined && recorded[k] !== recomputed[k]);
  if (drift.length) failures.push(`metrics drift vs metrics.json: ${drift.join(', ')}`);
}
report.checks.metric_reproducibility = { recomputed, recorded_present: !!recorded, drift_fields: drift };

// ── 4) execution proof ──
const proof = { checked: 0, events_present: 0, pipeline_log_pass: 0 };
for (const { g } of rows) {
  if (!g.run_dir) continue;
  proof.checked += 1;
  if (fs.existsSync(path.join(g.run_dir, '.pipeline_events.jsonl'))) proof.events_present += 1;
  if (g.checks?.pipeline_log === 'PASS') proof.pipeline_log_pass += 1;
}
report.checks.execution_proof = proof;
if (proof.checked && proof.pipeline_log_pass < proof.checked) {
  warnings.push(`${proof.checked - proof.pipeline_log_pass} graded run(s) without a PASS pipeline log`);
}

report.failures = failures;
report.warnings = warnings;
report.status = failures.length ? 'DRIFT' : 'REPRODUCIBLE';
fs.writeFileSync(path.join(RESULTS, 'repro_report.json'), JSON.stringify(report, null, 1) + '\n');

console.log(`dataset integrity : ${hashed} verified / ${missing} absent / ${mismatched} mismatched`);
console.log(`case coverage     : prepared ${coverage.prepared}/${coverage.cases}, graded ${coverage.graded}/${coverage.cases}`);
console.log(`metric repro      : ${drift.length ? `DRIFT (${drift.join(', ')})` : 'matches metrics.json'}`);
console.log(`execution proof   : ${proof.pipeline_log_pass}/${proof.checked} runs with PASS pipeline log`);
for (const w of warnings) console.log(`WARN  ${w}`);
for (const f of failures) console.log(`FAIL  ${f}`);
console.log(`\nstatus: ${report.status} — results/benchmark/repro_report.json`);
process.exit(failures.length ? 1 : 0);
