#!/usr/bin/env node
// quality_gate.mjs — POST-HOC quality gate for a completed enhancement run
// (industrial-analysis-enhance-auto, E0 → E8).
//
// The orchestrator enforces the orchestration_contract helpers at generation
// time; this gate RE-RUNS those same checks against a finished run dir —
// importing the exported helpers from ./orchestration_contract.mjs rather than
// forking the logic — and adds the e2e marker checks for the E0-E8 artifacts
// the SKILL.md output table lists.
//
// Usage:
//   node quality_gate.mjs --run-dir <RUN_DIR>
//
// Exit codes (house convention):
//   0 ok        — E8 recorded a passing status and every post-hoc contract
//                 check holds
//   1 hard error — bad inputs (no/unreadable --run-dir) or the E8 marker is
//                 unreadable (stage identity cannot be decided)
//   2 undetermined — the enhancement was not run for this run dir: no
//                 enhancement/ artifacts at all, the E8 marker absent (the
//                 E0-E8 chain did not complete), or E0 recorded BLOCKED
//                 (baseline artifacts missing — nothing was enhanced)
//   3 gate-fail — the chain ran but violates its contract: missing/corrupt
//                 E-markers, review not passing, status drift between the
//                 recorded and recomputed enhancement status, a FAILED
//                 knowledge status, a missing association graph for a
//                 present E3 output, a baseline hash mismatch, stale stage
//                 signatures, or an invalid enhanced_knowledge.json

import { spawnSync } from 'child_process';
import { existsSync, readFileSync, readdirSync, statSync } from 'fs';
import { dirname, join, resolve } from 'path';
import { fileURLToPath } from 'url';
import {
  fileHash,
  isFreshBySignature,
  resolveEnhancementStatus,
  reviewIsPassing,
  reviewStatus,
  shouldBuildAssociationGraph,
} from './orchestration_contract.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const REPO = resolve(HERE, '..', '..', '..', '..');
const SHARED = join(REPO, '.claude', 'shared');
const VALIDATOR = join(SHARED, 'scripts', 'validate.mjs');

const args = process.argv.slice(2);
const argOf = (k) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : undefined; };
const RUN_DIR_ARG = argOf('--run-dir');

const FAILS = [];
const NOTES = [];
const fail = (id, msg) => FAILS.push(`${id}: ${msg}`);
const note = (msg) => NOTES.push(msg);

function emit(verdict, reason, extra = {}) {
  console.log(JSON.stringify({
    gate: 'enhancement_quality_gate',
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
  emit('hard_error', 'usage: node quality_gate.mjs --run-dir <RUN_DIR>');
}
const RUN_DIR = resolve(RUN_DIR_ARG);
if (!existsSync(RUN_DIR) || !statSync(RUN_DIR).isDirectory()) {
  FAILS.push('ARGS', `run dir does not exist or is not a directory: ${RUN_DIR}`);
  emit('hard_error', null);
}
const ENH = join(RUN_DIR, 'enhancement');

// ── stage identity: E8 marker = enhancement_status.json ────────────────
const STATUS_PATH = join(ENH, 'enhancement_status.json');
if (!existsSync(ENH)) {
  emit('undetermined', `enhancement/ does not exist — the E0-E8 enhancement stage was not run for this run dir`);
}
if (!existsSync(STATUS_PATH)) {
  const stray = existsSync(ENH) ? readdirSafe(ENH).filter((f) => f !== 'enhancement_status.json') : [];
  if (stray.length) note(`E-stage artifacts present without the E8 marker: ${stray.slice(0, 8).join(', ')} — an incomplete chain cannot be graded`);
  emit('undetermined', 'enhancement/enhancement_status.json (E8 marker) is absent — the enhancement chain did not complete; nothing to grade');
}
let recordedStatus = null;
try {
  recordedStatus = JSON.parse(readFileSync(STATUS_PATH, 'utf-8'));
} catch (e) {
  emit('hard_error', `enhancement_status.json (E8 marker) is unreadable: ${e.message}`);
}
if (recordedStatus && recordedStatus.status === 'BLOCKED') {
  emit('undetermined', `E0 recorded BLOCKED — baseline diagnostic artifacts are missing (${(recordedStatus.missing || []).join(', ') || 'see enhancement_status.json'}); the enhancement was not run`);
}

function readdirSafe(dir) {
  try { return readdirSync(dir); } catch { return []; }
}

// ── e2e markers (E0-E8, per the SKILL.md output table) ─────────────────
const MARKERS = [
  ['enhancement_manifest.json', 'E0 runtime manifest', 'json'],
  ['analysis_coverage.json', 'E1 column coverage', 'json'],
  ['derived_features.json', 'E2 derived features', 'json'],
  ['deep_data_analysis.json', 'E3 deep data analysis', 'json'],
  ['physics_bridge.json', 'E5 physics bridge', 'json'],
  ['enhanced_knowledge.json', 'E6 enhanced knowledge', 'json'],
  ['enhanced_analysis.md', 'E7a markdown report', 'text'],
  ['enhanced-analysis.html', 'E7b ECharts page', 'text'],
  ['html_selfcheck.json', 'E7b page self-check', 'json'],
  ['enhancement_html_review.json', 'E7c HTML review', 'json'],
];
const parsed = {};
let markerFailures = 0;
for (const [rel, label, kind] of MARKERS) {
  const p = join(ENH, rel);
  if (!existsSync(p)) {
    fail('M1', `missing marker: enhancement/${rel} (${label})`);
    markerFailures += 1;
    continue;
  }
  try {
    const raw = readFileSync(p, 'utf-8');
    if (kind === 'text') {
      if (!raw.trim()) { fail('M1', `empty marker: enhancement/${rel} (${label})`); markerFailures += 1; }
      else if (rel.endsWith('.html') && Buffer.byteLength(raw) < 1024) {
        note(`M1: enhancement/${rel} is only ${Buffer.byteLength(raw)}B — suspiciously small for the E7b page`);
      }
    } else {
      parsed[rel] = JSON.parse(raw);
    }
  } catch (e) {
    fail('M1', `corrupt marker: enhancement/${rel} (${label}) — ${e.message}`);
    markerFailures += 1;
  }
}
if (existsSync(join(ENH, 'derived_data.csv'))) note('M1: derived_data.csv present (E2 table)');
else note('M1: enhancement/derived_data.csv absent (not listed in the SKILL.md output table; verify_enhancement.py of industrial-deep-analysis owns that check)');

const manifest = parsed['enhancement_manifest.json'] || null;
const knowledge = parsed['enhanced_knowledge.json'] || null;
const review = parsed['enhancement_html_review.json'] || null;
const deepAnalysis = parsed['deep_data_analysis.json'] || null;

// ── contract re-run (helpers imported, not forked) ─────────────────────
const launchOk = markerFailures === 0;
const knowledgeStatus = knowledge ? knowledge.enhancement_status : null;

if (knowledge && !['READY', 'READY_WITH_WARNINGS'].includes(knowledgeStatus)) {
  fail('C1', `enhanced_knowledge.enhancement_status=${knowledgeStatus} is not READY/READY_WITH_WARNINGS`);
}
if (review) {
  if (!reviewIsPassing(review)) {
    const verdict = reviewStatus(review);
    const blocking = Array.isArray(review.blocking_issues) ? review.blocking_issues.length : '(not an array)';
    fail('C2', `HTML review is not passing: reviewStatus=${verdict}, verdict=${review.verdict}, blocking_issues=${blocking}`);
  }
} else if (launchOk) {
  fail('C2', 'enhancement_html_review.json missing — READY is blocked (review artifact required)');
}

const recomputedStatus = resolveEnhancementStatus({ launchOk, knowledgeStatus, review });
if (recomputedStatus === 'FAILED') {
  fail('C3', `recomputed enhancement status is FAILED (recorded=${recordedStatus?.status})`);
}
if (recordedStatus && recordedStatus.status !== recomputedStatus) {
  fail('C4', `status drift: enhancement_status.json records ${recordedStatus.status} but the contract recomputes ${recomputedStatus} — artifacts are stale or tampered`);
}

// association graph: E3 emits it; the contract schedules a build when absent.
const graphExists = existsSync(join(ENH, 'association_graph.json'));
const e3Ok = !!deepAnalysis;
if (shouldBuildAssociationGraph({ e3Ok, graphExists })) {
  fail('C5', 'E3 output (deep_data_analysis.json) exists but association_graph.json is absent — the graph must have been emitted by E3');
}

// provenance: the manifest's baseline hash must still match the disk.
if (manifest) {
  const declared = manifest.data_source && manifest.data_source.sha256;
  const cleaned = join(RUN_DIR, '02_processed', 'cleaned_data.csv');
  const actual = fileHash(cleaned);
  if (!declared) note('C6: enhancement_manifest.data_source.sha256 not recorded — baseline hash not verifiable');
  else if (!actual) fail('C6', `enhancement_manifest records a baseline sha256 but ${cleaned} is missing`);
  else if (declared !== actual) fail('C6', 'baseline cleaned_data.csv changed after the enhancement ran (manifest sha256 mismatch) — enhancement artifacts are stale');
}

// freshness sidecars: recompute every recorded input hash via fileHash and
// compare with isFreshBySignature (the script hash is trusted from the sidecar).
let freshChecked = 0;
for (const [rel] of MARKERS) {
  const artifact = join(ENH, rel);
  const sigPath = `${artifact}.signature.json`;
  if (!existsSync(sigPath)) continue;
  let stored = null;
  try { stored = JSON.parse(readFileSync(sigPath, 'utf-8')); } catch { fail('C7', `${rel}.signature.json unparseable`); continue; }
  const recomputedInputs = {};
  for (const [inputPath, storedHash] of Object.entries(stored.inputs || {})) {
    recomputedInputs[inputPath] = fileHash(inputPath);
    if (storedHash && !recomputedInputs[inputPath]) {
      fail('C7', `${rel} is stale: recorded input ${inputPath} no longer exists`);
    }
  }
  if (!isFreshBySignature(stored, { scriptHash: stored.scriptHash, inputs: recomputedInputs })) {
    const drifted = Object.keys(recomputedInputs).filter((k) => (stored.inputs || {})[k] !== recomputedInputs[k]);
    fail('C7', `${rel} is stale: recorded input(s) changed after the stage ran — ${drifted.slice(0, 3).join(', ')}`);
  }
  freshChecked += 1;
}
note(freshChecked ? `C7: freshness verified for ${freshChecked} artifact signature(s)` : 'C7: no .signature.json sidecars — freshness not verifiable (artifacts were not signature-checked by the orchestrator)');

// enhanced_knowledge.json schema (the shared contract for the E6 deliverable)
if (knowledge && existsSync(VALIDATOR)) {
  const schema = join(SHARED, 'schemas', 'enhanced_knowledge_schema.json');
  if (existsSync(schema)) {
    const r = spawnSync(process.execPath, [VALIDATOR, schema, join(ENH, 'enhanced_knowledge.json')],
      { encoding: 'utf-8', timeout: 60000 });
    let report = null;
    try { report = JSON.parse(String(r.stdout || '{}')); } catch { report = null; }
    if (!report) fail('C8', `validate.mjs produced no parseable report: ${String(r.stderr || '').slice(0, 200)}`);
    else if (report.valid !== true) {
      fail('C8', `enhanced_knowledge.json fails enhanced_knowledge_schema.json: ${JSON.stringify(report.errors || []).slice(0, 300)}`);
    }
  } else {
    note('C8: enhanced_knowledge_schema.json not found — schema check skipped');
  }
} else if (!existsSync(VALIDATOR)) {
  note('C8: .claude/shared/scripts/validate.mjs not found — schema check skipped');
}

// ── verdict ────────────────────────────────────────────────────────────
const contract = {
  recorded_status: recordedStatus?.status ?? null,
  recomputed_status: recomputedStatus,
  knowledge_status: knowledgeStatus,
  review_status: review ? reviewStatus(review) : null,
  launch_ok: launchOk,
};
if (FAILS.length) emit('gate_fail', null, { contract });
emit('ok', null, { status: contract.recomputed_status, contract });
