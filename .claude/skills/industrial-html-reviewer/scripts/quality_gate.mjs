#!/usr/bin/env node
// quality_gate.mjs — Step 8.5 review-artifact gate (05_review/html_review.json).
//
// Usage: node quality_gate.mjs --run-dir <RUN_DIR> [--review <path>]
// Exit: 0 ok | 1 hard error (bad inputs) | 2 undetermined (review artifact absent — review not run)
//       | 3 gate-fail (unparseable / field violation)
//
// Structural validity only per schemas/html_review_schema.json — the verdict VALUE (pass/warn/fail) is a
// legitimate review outcome and does not fail the gate; contradictory artifacts do (see R7/R8).
// Deeper schema validation stays available via the shared validate.mjs.

import { existsSync, readFileSync, statSync } from 'fs';
import { resolve } from 'path';

const VERDICTS = ['pass', 'warn', 'fail'];
const CHECK_NAMES = [
  'hero_clarity', 'evidence_layer_1_statistical', 'evidence_layer_2_physics', 'evidence_layer_3_exclusion',
  'image_usage_from_03_figures', 'three_d_fidelity', 'chart_initialization', 'dual_evidence_per_conclusion',
  'plain_language_translation', 'action_and_limitations', 'render_manifest_produced',
  'manifest_page_consistency', 'no_cross_run_pollution', 'selfcheck_audit',
];
const args = process.argv.slice(2);
const argOf = (k) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : undefined; };
const RUN_DIR = argOf('--run-dir') || args.find((a) => !a.startsWith('--'));
const REVIEW = resolve(argOf('--review') || (RUN_DIR ? resolve(RUN_DIR, '05_review', 'html_review.json') : ''));
const TARGET = RUN_DIR ? resolve(RUN_DIR, '05_review', 'html_review.json') : REVIEW;

const FAILS = [];
const fail = (id, msg) => FAILS.push(`${id}: ${msg}`);
const emit = (verdict, extra = {}) => {
  console.log(JSON.stringify({
    gate: 'html_reviewer_quality_gate', artifact: REVIEW, run_dir: RUN_DIR || null, verdict, fails: FAILS, ...extra,
  }, null, 2));
  process.exit({ ok: 0, hard_error: 1, undetermined: 2, gate_fail: 3 }[verdict]);
};

if (!RUN_DIR && !argOf('--review')) {
  emit('hard_error', { reason: 'usage: quality_gate.mjs --run-dir <RUN_DIR> [--review <path>]' });
}
if (!existsSync(REVIEW) || !statSync(REVIEW).isFile()) {
  emit('undetermined', { reason: `${TARGET} absent — Step 8.5 (industrial-html-reviewer) has not run` });
}

let r;
try { r = JSON.parse(readFileSync(REVIEW, 'utf-8')); }
catch (e) { fail('R1', `html_review.json unparseable: ${e.message}`); emit('gate_fail'); }
if (typeof r !== 'object' || r === null || Array.isArray(r)) {
  fail('R1', 'html_review.json is not a JSON object'); emit('gate_fail');
}

const isStr = (v) => typeof v === 'string' && v.trim().length > 0;
const strArray = (v) => Array.isArray(v) && v.every(isStr);

// ── R2: required fields present with correct types (schema `required`) ──────
for (const key of ['verdict', 'overall_score', 'blocking_issues', 'warnings', 'checks']) {
  if (!(key in r)) fail('R2', `missing required field "${key}"`);
}
// ── R3: verdict enum ───────────────────────────────────────────────────────
if ('verdict' in r && !VERDICTS.includes(r.verdict)) {
  fail('R3', `verdict "${r.verdict}" not in ${VERDICTS.join('|')}`);
}
// ── R4: overall_score 0-100 ────────────────────────────────────────────────
if ('overall_score' in r && !(typeof r.overall_score === 'number' && r.overall_score >= 0 && r.overall_score <= 100)) {
  fail('R4', `overall_score "${r.overall_score}" is not a number in 0-100`);
}
// ── R5: string arrays (blocking_issues / warnings never objects) ───────────
for (const key of ['blocking_issues', 'warnings']) {
  if (key in r && !strArray(r[key])) fail('R5', `${key} must be an array of non-empty strings`);
}
// ── R6: checks[] shape + closed check-name enum ────────────────────────────
if ('checks' in r) {
  if (!Array.isArray(r.checks) || r.checks.length === 0) {
    fail('R6', 'checks must be a non-empty array');
  } else {
    for (const c of r.checks) {
      if (!c || typeof c !== 'object' || !isStr(c.name) || !isStr(c.evidence) || !['pass', 'fail'].includes(c.status)) {
        fail('R6', `check entry invalid (need name/evidence strings + status pass|fail): ${JSON.stringify(c)?.slice(0, 80)}`);
      } else if (!CHECK_NAMES.includes(c.name)) {
        fail('R6', `check name "${c.name}" not in the schema enum`);
      }
    }
  }
}
// ── R7: verdict consistency (no silent contradictions) ─────────────────────
const blockers = Array.isArray(r.blocking_issues) ? r.blocking_issues.length : 0;
const failedChecks = Array.isArray(r.checks) ? r.checks.filter((c) => c && c.status === 'fail').length : 0;
if (r.verdict === 'pass' && blockers > 0) fail('R7', 'verdict pass with non-empty blocking_issues');
if (r.verdict === 'fail' && blockers === 0 && failedChecks === 0) {
  fail('R7', 'verdict fail without a blocking issue or a failed check — fail must be substantiated');
}
// ── R8: every failed check has a blocker string citing it ──────────────────
if (failedChecks > 0 && blockers === 0) {
  fail('R8', `${failedChecks} failed check(s) but blocking_issues is empty — blockers must cite the failing check`);
}

emit(FAILS.length ? 'gate_fail' : 'ok', {
  verdict_value: r.verdict,
  overall_score: r.overall_score,
  checks: Array.isArray(r.checks) ? r.checks.length : 0,
  blocking_issues: blockers,
  warnings: Array.isArray(r.warnings) ? r.warnings.length : 0,
});
