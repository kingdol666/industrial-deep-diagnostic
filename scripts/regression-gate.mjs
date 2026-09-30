#!/usr/bin/env node
// regression-gate.mjs — defect-fixture regression gate (plan v1 B7).
//
// Every deterministic gate added by the pipeline-optimization plan must FAIL
// on its corresponding historical defect fixture and PASS on clean input.
// Run before merging any change to gates/tools/schemas:
//   node scripts/regression-gate.mjs
// Exit 0 = all regressions hold. Exit 1 = a gate lost its teeth.
//
// Fixtures are synthesized in a temp dir from the historical defect
// morphologies of run 202609300452274_cement_ball_mill_fulltest:
//   F1 "≈38min" unit narrative        → pre_audit_lint L1 must FAIL
//   F2 blank title-only plot          → plot_verification ink check must FAIL
//   F3 confidence sum broken (85≠80)  → diagnostic-quality-check must FAIL
//   F4 dual-drive field drift         → quality-check must emit CONTRACT_DRIFT warning
//   CLEAN: untampered copies          → lint L1 passes, quality-check PASS

import fs from 'fs';
import path from 'path';
import { execFileSync } from 'child_process';
import { fileURLToPath } from 'url';

const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const RUN = path.join(REPO, 'workspace', 'diagnostic-runs', '202609300452274_cement_ball_mill_fulltest');
const TMP = path.join(REPO, '.omc', 'tmp', 'regression_gate');
const PY = fs.existsSync(path.join(REPO, '.claude/shared/scripts/.venv/Scripts/python.exe'))
  ? path.join(REPO, '.claude/shared/scripts/.venv/Scripts/python.exe')
  : path.join(REPO, '.claude/shared/scripts/.venv/bin/python');
const LINT = path.join(REPO, '.claude/skills/industrial-analysis-auto/scripts/pre_audit_lint.mjs');
const QC = path.join(REPO, '.claude/skills/industrial-diagnostician/scripts/diagnostic-quality-check.mjs');
const PLOT = path.join(REPO, '.claude/skills/industrial-data-processor/scripts/plot_verification.py');

let failures = 0;
const check = (name, cond, detail) => {
  console.log(`${cond ? '✔' : '✘'} ${name}${cond ? '' : ' — ' + detail}`);
  if (!cond) failures++;
};
// gates under test exit non-zero when they (correctly) FAIL a fixture — parse stdout regardless
const runJson = (cmd, args) => {
  try {
    return JSON.parse(execFileSync(cmd, args, { stdio: ['ignore', 'pipe', 'pipe'] }).toString());
  } catch (e) {
    const out = e.stdout ? e.stdout.toString() : '';
    try { return JSON.parse(out); } catch { throw e; }
  }
};

fs.rmSync(TMP, { recursive: true, force: true });

// ── F1: unit-narrative fixture ──
const f1 = path.join(TMP, 'f1_unit_narrative');
for (const d of ['04_diagnostics', '02_processed', '03_figures', '05_review']) fs.mkdirSync(path.join(f1, d), { recursive: true });
fs.copyFileSync(path.join(RUN, '04_diagnostics/diagnosis.json'), path.join(f1, '04_diagnostics/diagnosis.json'));
fs.copyFileSync(path.join(RUN, '02_processed/time_lag_analysis.json'), path.join(f1, '02_processed/time_lag_analysis.json'));
fs.copyFileSync(path.join(RUN, '03_figures/plot_manifest.json'), path.join(f1, '03_figures/plot_manifest.json'));
let rpt = fs.readFileSync(path.join(RUN, 'report.md'), 'utf-8');
rpt = rpt.replace('19 步为化验样本步，中位间隔 2.07h，跨度约 1.6–2.2 天', '19 步按标称 2min ≈38min，量级不变');
fs.writeFileSync(path.join(f1, 'report.md'), rpt);
const lint1 = JSON.parse(execFileSync('node', [LINT, f1, '--report-only'], { stdio: ['ignore', 'pipe', 'ignore'] }).toString());
check('F1 lint L1 catches steps→time unit narrative',
  lint1.issues.some(i => i.rule === 'L1_duration_claim' && i.severity === 'FAIL'),
  JSON.stringify(lint1.issues.map(i => i.rule)));

// ── F2: blank plot fixture ──
const f2 = path.join(TMP, 'f2_blank_plot');
fs.mkdirSync(path.join(f2, '03_figures'), { recursive: true });
execFileSync(PY, ['-c', `
from PIL import Image, ImageDraw
img = Image.new('RGB', (1600, 1200), 'white')
d = ImageDraw.Draw(img)
d.text((600, 40), 'Causal Evidence Map', fill='black')
img.save(r'${path.join(f2, '03_figures/fig_blank.png').replace(/\\/g, '/')}')
`]);
fs.writeFileSync(path.join(f2, '03_figures/plot_manifest.json'),
  JSON.stringify({ plots: [{ filename: 'fig_blank.png', path: '03_figures/fig_blank.png' }] }));
let plotFail = '';
try {
  execFileSync(PY, [PLOT, f2], { stdio: ['ignore', 'pipe', 'pipe'] });
} catch (e) { plotFail = String(e.stderr || ''); }
check('F2 plot ink check rejects blank title-only render', /ink check|near-blank/.test(plotFail), plotFail.slice(0, 120));

// ── F3: confidence closure fixture ──
const f3 = path.join(TMP, 'f3_confidence');
for (const d of ['04_diagnostics', '02_processed']) fs.mkdirSync(path.join(f3, d), { recursive: true });
for (const f of ['diagnosis.json', 'evidence.json', 'confidence.json', 'reasoning_chain.json'])
  fs.copyFileSync(path.join(RUN, '04_diagnostics', f), path.join(f3, '04_diagnostics', f));
for (const f of ['anomaly_report.json', 'data_analysis_conclusion.json'])
  fs.copyFileSync(path.join(RUN, '02_processed', f), path.join(f3, '02_processed', f));
{
  const c = JSON.parse(fs.readFileSync(path.join(f3, '04_diagnostics/confidence.json'), 'utf-8'));
  c.confidence_breakdown.H1.confidence_score = 85; // break 19+22+16+15+8=80
  fs.writeFileSync(path.join(f3, '04_diagnostics/confidence.json'), JSON.stringify(c, null, 2));
}
const qc3 = runJson('node', [QC, f3]);
check('F3 confidence closure mismatch detected',
  qc3.issues.some(i => i.code === 'CONFIDENCE_H1_SUM_MISMATCH'),
  JSON.stringify(qc3.issues.map(i => i.code)));

// ── F4: dual-drive field-drift fixture (fallback must engage + warn) ──
const f4 = path.join(TMP, 'f4_contract_drift');
for (const d of ['04_diagnostics', '02_processed']) fs.mkdirSync(path.join(f4, d), { recursive: true });
for (const f of ['diagnosis.json', 'evidence.json', 'confidence.json', 'reasoning_chain.json'])
  fs.copyFileSync(path.join(RUN, '04_diagnostics', f), path.join(f4, '04_diagnostics', f));
for (const f of ['data_analysis_conclusion.json'])
  fs.copyFileSync(path.join(RUN, '02_processed', f), path.join(f4, '02_processed', f));
{
  const a = JSON.parse(fs.readFileSync(path.join(RUN, '02_processed/anomaly_report.json'), 'utf-8'));
  // revert to the pre-remediation shape: empty primary path, rich legacy layer
  a.dual_drive_analysis.cross_domain_links = [];
  fs.writeFileSync(path.join(f4, '02_processed/anomaly_report.json'), JSON.stringify(a, null, 2));
}
const qc4 = runJson('node', [QC, f4]);
check('F4 contract drift -> fallback engages with CONTRACT_DRIFT warning (no false critical)',
  qc4.issues.some(i => i.code === 'CONTRACT_DRIFT_DUAL_DRIVE_INPUTS' && i.severity === 'warning') &&
  !qc4.issues.some(i => i.code === 'DUAL_DRIVE_OUTPUT_WITHOUT_INPUT'),
  JSON.stringify(qc4.issues.map(i => i.code)));

// ── CLEAN: real run artifacts must pass ──
const lintClean = JSON.parse(execFileSync('node', [LINT, RUN, '--report-only'], { stdio: ['ignore', 'pipe', 'ignore'] }).toString());
check('CLEAN lint L1 has no duration-claim failure on fixed report',
  !lintClean.issues.some(i => i.rule === 'L1_duration_claim'),
  JSON.stringify(lintClean.issues.map(i => i.rule + ':' + i.severity)));
const qcClean = runJson('node', [QC, RUN]);
check('CLEAN quality gate passes on real run', qcClean.status === 'PASS', qcClean.status);

fs.writeFileSync(path.join(REPO, '.omc', 'tmp', 'regression_gate_last_run.json'),
  JSON.stringify({ at: new Date().toISOString(), failures, passed: failures === 0 }, null, 2));
console.log(failures === 0 ? '\nREGRESSION_GATE: PASS (all gates hold their teeth)' : `\nREGRESSION_GATE: FAIL (${failures} gate(s) lost their teeth)`);
process.exit(failures === 0 ? 0 : 1);
