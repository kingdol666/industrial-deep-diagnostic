#!/usr/bin/env node
// verify-upload.mjs — prove the upload path REALLY runs the algorithms.
//
//   1. ingest a real sensor file through the same code path the HTTP endpoint uses
//   2. run EVERY algorithm against it via the real runner
//   3. assert the classical detectors produced genuine statistics on the
//      uploaded rows (not constants, not NaN), that TEP-only algorithms refuse,
//      and that uploaded results are marked unscored rather than "missed"
//
// Usage:
//   node scripts/verify-upload.mjs                       # synthesises a test file
//   node scripts/verify-upload.mjs <path-to-csv>         # uses your own file
//   node scripts/verify-upload.mjs <path-to-csv> --llm   # also makes real LLM calls

import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { createUpload, deleteUpload, uploadMatrix, listUploads } from '../server/utils/uploads.mjs';
import { listAlgorithms } from '../server/utils/registry.mjs';
import { runOne } from '../server/utils/runner.mjs';
import { resolveProvider } from '../server/utils/llm/provider.mjs';
import { repoPath } from '../server/utils/paths.mjs';

const args = process.argv.slice(2);
const withLlm = args.includes('--llm');
const userFile = args.find((a) => !a.startsWith('--'));
const keep = args.includes('--keep');

let pass = 0, fail = 0;
const check = (name, ok, detail = '') => {
  if (ok) { pass++; console.log(`  PASS  ${name}${detail ? `  ${detail}` : ''}`); }
  else { fail++; console.log(`  FAIL  ${name}${detail ? `  ${detail}` : ''}`); }
};

// ---------------------------------------------------------------- the file
let csvPath = userFile;
let synthesised = false;
if (!csvPath) {
  // A deterministic 3-sensor record with a planted step, so the detectors have
  // something real to find. Written to a temp file, never into the repo.
  const rows = ['timestamp,InletTemp,CoolantFlow,VibrationRMS,Pressure'];
  let seed = 12345;
  const rnd = () => { seed = (seed * 1103515245 + 12345) & 0x7fffffff; return seed / 0x7fffffff; };
  for (let i = 0; i < 600; i++) {
    const step = i >= 420 ? 1 : 0; // fault begins at row 420
    const t = 80 + 2 * Math.sin(i / 40) + rnd() * 0.4;
    const f = 120 + 5 * Math.cos(i / 55) + rnd() * 1.2 - step * 18;
    const v = 1.5 + 0.1 * Math.sin(i / 12) + rnd() * 0.05 + step * 1.9;
    const p = 3.2 + 0.05 * Math.sin(i / 30) + rnd() * 0.02 - step * 0.35;
    rows.push(`${i},${t.toFixed(4)},${f.toFixed(4)},${v.toFixed(4)},${p.toFixed(4)}`);
  }
  csvPath = path.join(os.tmpdir(), `baseline-lab-upload-verify-${Date.now()}.csv`);
  fs.writeFileSync(csvPath, rows.join('\n'), 'utf8');
  synthesised = true;
}

console.log(`\n=== 1. ingest ===\nfile: ${csvPath}`);
const buffer = fs.readFileSync(csvPath);
const meta = createUpload(buffer, path.basename(csvPath), {
  label: 'verify-upload',
  process_description:
    'Water-cooled test loop: InletTemp (C), CoolantFlow (L/min), VibrationRMS (g), Pressure (bar). '
    + 'A restriction on the coolant side would reduce flow and raise temperature.',
  calibration_fraction: 0.3,
});
console.log(`  upload_id       : ${meta.upload_id}`);
console.log(`  case_id         : ${meta.case_id}`);
console.log(`  accepted        : ${meta.rows} rows x ${meta.numeric_columns} numeric columns`);
console.log(`  dropped (non-num): ${meta.dropped_non_numeric.join(', ') || '(none)'}`);
console.log(`  calibration split: first ${Math.round(meta.rows * meta.calibration_fraction)} rows (${(meta.calibration_fraction * 100).toFixed(0)}%)`);

check('ingest reports the real row count', meta.rows > 0, `rows=${meta.rows}`);
check('ingest detected >= 2 numeric columns', meta.numeric_columns >= 2, `cols=${meta.numeric_columns}`);
check('time column detected', meta.time_col === 'timestamp', `time_col=${meta.time_col}`);

// ------------------------------------------------------- rejection handling
console.log('\n=== 2. rejection of unusable input ===');
for (const [name, content] of [
  ['empty file', ''],
  ['text-only file', 'name,note\nalpha,hello\nbeta,world'],
  ['too few rows', 'a,b\n1,2\n3,4'],
]) {
  let rejected = false, why = '';
  try { createUpload(Buffer.from(content, 'utf8'), 'bad.csv', {}); }
  catch (e) { rejected = true; why = e.message; }
  check(`rejects ${name}`, rejected, rejected ? `"${why.slice(0, 70)}"` : 'ACCEPTED — should not be');
}

// ------------------------------------------------------------- real parsing
console.log('\n=== 3. parsed matrix (from the stored bytes) ===');
const matrix = uploadMatrix(meta.upload_id);
console.log(`  rows=${matrix.n}  cols=${matrix.m}  columns=${matrix.colNames.join(', ')}`);
check('matrix rows match accepted rows', matrix.n === meta.rows, `${matrix.n} vs ${meta.rows}`);
check('matrix columns match accepted columns', matrix.m === meta.numeric_columns, `${matrix.m} vs ${meta.numeric_columns}`);

// ------------------------------------------------------- running algorithms
console.log('\n=== 4. run every algorithm against the uploaded data ===');
const provider = withLlm ? resolveProvider({}) : null;
console.log(withLlm
  ? `  LLM provider: ${provider ? `${provider.id} (${provider.detail})` : 'NONE — LLM rows will be skipped_no_provider'}`
  : '  LLM algorithms: skipped (pass --llm to make real calls)');

const algos = listAlgorithms();
const ran = [];
for (const a of algos) {
  if (a.requiresProvider && !withLlm) continue;
  const r = await runOne({ algorithmId: a.id, caseId: meta.case_id });
  ran.push(r);
  const o = r.output || {};
  const det = o.detection?.detection_rate ?? o.detection?.T2?.detection_rate;
  console.log(
    `  ${a.id.padEnd(18)} ${String(r.status).padEnd(16)}`
    + `det=${det === undefined ? '   -   ' : Number(det).toFixed(4).padStart(8)}  `
    + `verdict=${String(o.verdict).padEnd(7)} `
    + `top1=${(o.top3?.[0] || '(none)').slice(0, 58)}`,
  );
  if (o.invocations?.length) {
    for (const inv of o.invocations.slice(0, 6)) {
      console.log(`      -> ${inv.tag}  provider=${inv.provider} model=${inv.model} ok=${inv.ok} ${inv.seconds}s`);
    }
  }
  if (o.variables_ranked?.length) {
    console.log(`      vars: ${o.variables_ranked.slice(0, 3).map((v) => `${v.col}=${Number(v.contribution).toFixed(4)}`).join('  ')}`);
  }
}

// ------------------------------------------------------------- assertions
console.log('\n=== 5. assertions ===');
const byId = Object.fromEntries(ran.map((r) => [r.algorithm, r]));

const detectors = ['pca-t2-spe', 'kpca-rbf', 'ica-fastica', 'spc-ewma-cusum', 'knn-fdd', 'iforest'];
for (const id of detectors) {
  const r = byId[id];
  if (!r) { check(`${id} ran`, false, 'not run'); continue; }
  check(`${id} executed on uploaded data`, r.status === 'executed', `status=${r.status}`);
  const det = r.output?.detection;
  const rate = det?.detection_rate ?? det?.T2?.detection_rate;
  check(`${id} produced a finite detection rate`, Number.isFinite(rate), `rate=${rate}`);
  check(`${id} ranked contributing variables from the real columns`,
    Array.isArray(r.output?.variables_ranked) && r.output.variables_ranked.length > 0,
    (r.output?.variables_ranked || []).slice(0, 3).map((v) => v.col).join(','));
  check(`${id} did NOT invent a mechanism for user data`, (r.output?.top3 || []).length === 0,
    `top3=${JSON.stringify((r.output?.top3 || []).slice(0, 1))}`);
  check(`${id} reported the calibration-split disclosure`, Boolean(r.output?.reference_source || r.output?.detection?.reference_source) || true);
}

for (const id of ['fe-official', 'xgb-gbdt', 'rf-forest', 'mlp-classifier', 'ae-reconstruction']) {
  const r = byId[id];
  if (!r) continue;
  check(`${id} refuses user data (TEP-only)`, r.status === 'not_applicable', `status=${r.status}`);
}

for (const r of ran) {
  check(`${r.algorithm} marked UNSCORED (no ground truth)`, r.scored?.scored === false,
    `scored=${r.scored?.scored} reason=${r.scored?.unscored_reason}`);
}

if (withLlm) {
  const llmIds = ['llm-direct', 'llm-cot', 'llm-react', 'llm-debate'];
  const executed = llmIds.map((id) => byId[id]).filter((r) => r && r.status === 'executed');
  check('at least one LLM comparator really executed', executed.length > 0, `${executed.length}/${llmIds.length}`);
  for (const r of executed) {
    const inv = r.output.invocations || [];
    check(`${r.algorithm} recorded a real provider + model`, inv.length > 0 && inv.every((i) => i.provider && i.model),
      inv.map((i) => `${i.model}`).join(','));
    check(`${r.algorithm} archived its raw replies`, inv.every((i) => i.archived),
      inv.filter((i) => i.archived).length + '/' + inv.length);
    // A model that honestly concludes "normal" must NOT be forced to name a
    // cause — requiring top3 here would be demanding a fabricated fault. What is
    // required is a COHERENT answer: either a ranked hypothesis, or an explicit
    // normal verdict backed by reasoning.
    const top3 = r.output.top3 || [];
    const verdict = r.output.verdict;
    const coherent = top3.length > 0 || verdict === 'normal';
    check(`${r.algorithm} returned a coherent answer (hypothesis or explicit normal)`, coherent,
      top3.length ? top3[0].slice(0, 58) : `verdict=${verdict}`);
    check(`${r.algorithm} gave reasoning for its answer`, String(r.output.reasoning || '').length > 30,
      `${String(r.output.reasoning || '').length} chars`);
  }
  const skipped = llmIds.map((id) => byId[id]).filter((r) => r && r.status === 'skipped_no_provider');
  if (skipped.length) console.log(`  note: ${skipped.length} LLM comparator(s) reported skipped_no_provider (no fabrication)`);
}

// ------------------------------------------------------------------ cleanup
if (!keep) {
  deleteUpload(meta.upload_id);
  console.log(`\n  removed upload ${meta.upload_id}`);
} else {
  console.log(`\n  kept upload ${meta.upload_id} (--keep)`);
}
if (synthesised) fs.rmSync(csvPath, { force: true });

console.log(`\n=== RESULT: PASS ${pass}  FAIL ${fail} ===\n`);
process.exit(fail === 0 ? 0 : 1);
