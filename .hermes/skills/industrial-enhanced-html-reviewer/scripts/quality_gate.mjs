#!/usr/bin/env node
// quality_gate.mjs — enhanced review gate. Runs scripts/html_reviewer.py (deterministic reviewer) on
// <RUN_DIR>/enhancement/{enhanced_knowledge.json, enhanced-analysis.html} and maps its verdict.
//
// Usage: node quality_gate.mjs --run-dir <RUN_DIR> [--python <exe>] [--no-run] [--allow-warn]
// Exit: 0 ok (verdict pass; or warn + --allow-warn) | 1 hard error (script/python failure)
//       | 2 undetermined (input artifact absent — the enhanced build has not run)
//       | 3 gate-fail (verdict warn without --allow-warn, or fail)
//
// Verdict semantics (scripts/html_reviewer.py): blocking_issues -> fail; score < 75 -> warn; else pass.
// --no-run consumes an existing enhancement_html_review.json instead of re-running the reviewer.

import { existsSync, readFileSync, statSync } from 'fs';
import { spawnSync } from 'child_process';
import { dirname, join, resolve } from 'path';
import { fileURLToPath } from 'url';

const HERE = dirname(fileURLToPath(import.meta.url));
const REVIEWER = join(HERE, 'html_reviewer.py');
const args = process.argv.slice(2);
const has = (k) => args.includes(k);
const argOf = (k) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : undefined; };
const RUN_DIR = argOf('--run-dir') || args.find((a) => !a.startsWith('--'));
const NO_RUN = has('--no-run');
const ALLOW_WARN = has('--allow-warn');

const ENH = RUN_DIR ? resolve(RUN_DIR, 'enhancement') : null;
const KNOWLEDGE = ENH && resolve(ENH, 'enhanced_knowledge.json');
const HTML = ENH && resolve(ENH, 'enhanced-analysis.html');
const SELFCHECK = ENH && resolve(ENH, 'html_selfcheck.json');
const OUTPUT = ENH && resolve(ENH, 'enhancement_html_review.json');

const emit = (verdict, extra = {}) => {
  console.log(JSON.stringify({
    gate: 'enhanced_html_reviewer_quality_gate', run_dir: RUN_DIR || null, review: OUTPUT, verdict, ...extra,
  }, null, 2));
  process.exit({ ok: 0, hard_error: 1, undetermined: 2, gate_fail: 3 }[verdict]);
};

if (!RUN_DIR || !existsSync(RUN_DIR)) emit('hard_error', { reason: 'usage: quality_gate.mjs --run-dir <RUN_DIR> [--python <exe>] [--no-run] [--allow-warn]' });

// ── U1: required inputs (else undetermined) ─────────────────────────────────
if (!NO_RUN) {
  const missing = [KNOWLEDGE, HTML].filter((p) => !existsSync(p) || !statSync(p).isFile());
  if (missing.length) {
    emit('undetermined', { reason: `enhanced build artifacts absent (${missing.join(', ')}) — industrial-enhanced-html-visualizer has not run` });
  }
}

// ── U2: resolve a python that can run the stdlib-only reviewer ──────────────
function findPython() {
  if (argOf('--python')) return argOf('--python');
  if (process.env.PYTHON) return process.env.PYTHON;
  const venv = ['Scripts/python.exe', 'bin/python'].map((p) => resolve(HERE, '..', '..', '..', 'shared', 'scripts', '.venv', p));
  for (const p of venv) if (existsSync(p)) return p;
  return process.platform === 'win32' ? 'python' : 'python3';
}

// ── U3: review (run the script unless --no-run) ─────────────────────────────
if (!NO_RUN) {
  if (!existsSync(REVIEWER)) emit('hard_error', { reason: `reviewer script missing: ${REVIEWER}` });
  const py = findPython();
  const argv = [REVIEWER, '--knowledge', KNOWLEDGE, '--html', HTML, '--output', OUTPUT];
  if (existsSync(SELFCHECK)) argv.push('--selfcheck', SELFCHECK);
  const proc = spawnSync(py, argv, { encoding: 'utf-8', timeout: 120000, shell: false });
  if (proc.error || proc.status !== 0) {
    emit('hard_error', {
      reason: `html_reviewer.py failed (python=${py}, status=${proc.status}${proc.error ? `, ${proc.error.message}` : ''})`,
      stderr: (proc.stderr || '').slice(-400),
    });
  }
}

// ── U4: consume the review artifact ─────────────────────────────────────────
if (!existsSync(OUTPUT) || !statSync(OUTPUT).isFile()) {
  emit('undetermined', { reason: `${OUTPUT} absent — the enhanced review has not run` });
}
let r;
try { r = JSON.parse(readFileSync(OUTPUT, 'utf-8')); }
catch (e) { emit('hard_error', { reason: `enhancement_html_review.json unparseable: ${e.message}` }); }
if (!['pass', 'warn', 'fail'].includes(r.verdict)) {
  emit('hard_error', { reason: `unexpected verdict "${r.verdict}" from html_reviewer.py` });
}

// ── U5: map the verdict ─────────────────────────────────────────────────────
const summary = {
  verdict_value: r.verdict,
  overall_score: r.overall_score,
  blocking_issues: (r.blocking_issues || []).length,
  warnings: (r.warnings || []).length,
  html_size_bytes: r.html_size_bytes,
};
if (r.verdict === 'pass') emit('ok', summary);
if (r.verdict === 'warn' && ALLOW_WARN) emit('ok', { ...summary, note: 'warn accepted via --allow-warn (informational)' });
emit('gate_fail', {
  ...summary,
  fails: r.verdict === 'warn'
    ? ['U5: verdict warn — fix the warnings and re-review (or set --allow-warn for informational use)']
    : ['U5: verdict fail — rebuild enhancement/enhanced-analysis.html, then re-review'],
});
