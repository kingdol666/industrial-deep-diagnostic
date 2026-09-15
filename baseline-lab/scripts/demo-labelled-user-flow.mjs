#!/usr/bin/env node
// demo-labelled-user-flow.mjs — the realistic user scenario:
//
//   "I have labelled historical data for my process, and a new record to diagnose."
//
// Builds a labelled training CSV from the repository's prepared TEP runs (as a
// stand-in for a user's own historical labelled data), uploads it TOGETHER with
// an unlabelled record, and runs the full algorithm set through the live HTTP
// diagnosis API — proving the supervised classifiers work on a user's own
// classes, not TEP IDV labels.
//
//   node scripts/demo-labelled-user-flow.mjs

import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { repoPath } from '../server/utils/paths.mjs';

const BASE = process.env.LAB_URL || 'http://localhost:5190';
const TEP = (f) => repoPath('data', 'benchmark', 'prepared', 'tep', f);

// A user's labelled history: their own class names, their own columns.
const HISTORY = [
  { file: 'd00_te.csv', label: 'healthy' },
  { file: 'd01_te.csv', label: 'feed_ratio_drift' },
  { file: 'd04_te.csv', label: 'reactor_cooling_fault' },
  { file: 'd07_te.csv', label: 'header_pressure_loss' },
  { file: 'd14_te.csv', label: 'reactor_valve_stiction' },
];

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'lab-labelled-'));

// ---- build the labelled training CSV (feature columns + a label column) -----
function readCsv(file) {
  const lines = fs.readFileSync(file, 'utf8').split(/\r?\n/).filter(Boolean);
  return { header: lines[0].split(','), rows: lines.slice(1).map((l) => l.split(',')) };
}

const first = readCsv(TEP(HISTORY[0].file));
// Drop the timestamp, keep the sensor columns a user would actually have.
const keepIdx = first.header.map((h, i) => i).filter((i) => !/^timestamp$/i.test(first.header[i]));
const keepNames = keepIdx.map((i) => first.header[i]);

let out = [...keepNames, 'fault_label'].join(',');
let perClassRows = 0;
for (const { file, label } of HISTORY) {
  const { rows } = readCsv(TEP(file));
  for (let i = 0; i < rows.length; i += 20) {       // subsample: a user would not dump everything
    const r = rows[i];
    out += `\n${keepIdx.map((j) => r[j]).join(',')},${label}`;
    perClassRows++;
  }
}
const trainFile = path.join(tmp, 'labelled_history.csv');
fs.writeFileSync(trainFile, out, 'utf8');
console.log(`\n=== labelled training file (as a user would supply) ===`);
console.log(`  ${path.basename(trainFile)}: ${perClassRows} rows, ${HISTORY.length} classes, label column 'fault_label'`);
console.log(`  classes: ${HISTORY.map((h) => h.label).join(', ')}`);

// ---- the record to diagnose: d14 again, unlabelled -------------------------
const recordPath = TEP('d14_te.csv');

// ---- upload BOTH files -----------------------------------------------------
const fd = new FormData();
fd.append('file', new Blob([fs.readFileSync(recordPath)]), 'new_record.csv');
fd.append('training', new Blob([fs.readFileSync(trainFile)]), 'labelled_history.csv');
fd.append('label_column', 'fault_label');
fd.append('label', 'user record + labelled history');
fd.append('calibration_fraction', '0.25');
fd.append('process_description', 'Chemical process. Columns are XMEAS_n sensor measurements and XMV_n manipulators. '
  + 'Labelled history includes healthy operation plus four known fault classes.');

console.log(`\n=== upload ===`);
const up = await fetch(`${BASE}/api/uploads`, { method: 'POST', body: fd }).then((r) => r.json());
if (!up?.upload) { console.error('upload failed:', JSON.stringify(up).slice(0, 400)); process.exit(1); }
console.log(`  ${up.summary}`);
console.log(`  case_id: ${up.upload.case_id}`);

// ---- run EVERY algorithm, including the three classifiers ------------------
const cap = await fetch(`${BASE}/api/diagnose`).then((r) => r.json());
const all = cap.runnable.map((a) => a.id);
console.log(`\n=== running all ${all.length} algorithms ===`);

const started = await fetch(`${BASE}/api/diagnose`, {
  method: 'POST',
  headers: { 'content-type': 'application/json' },
  body: JSON.stringify({ uploadId: up.upload.upload_id, algorithms: all }),
}).then((r) => r.json());
console.log(`  job ${started.job_id}  running ${started.algorithms.length}  refused ${started.refused?.length || 0}`);

const t0 = Date.now();
const res = await fetch(`${BASE}${started.stream_url}`, { headers: { accept: 'text/event-stream' } });
const reader = res.body.getReader();
const dec = new TextDecoder();
let buf = '', done = false;
const live = new Map();
while (!done) {
  const { value, done: d } = await reader.read();
  if (d) break;
  buf += dec.decode(value, { stream: true });
  const frames = buf.split('\n\n'); buf = frames.pop();
  for (const f of frames) {
    for (const line of f.split('\n')) {
      if (!line.startsWith('data: ')) continue;
      const e = JSON.parse(line.slice(6));
      if (e.type === 'algorithm_start') live.set(e.algorithm, Date.now());
      if (e.type === 'algorithm_done') {
        const s = ((Date.now() - live.get(e.algorithm)) / 1000).toFixed(1);
        console.log(`  [${String(e.status).padEnd(16)}] ${e.algorithm.padEnd(18)} ${s.padStart(6)}s  ${String(e.summary).slice(0, 82)}`);
      }
      if (['complete', 'end', 'error'].includes(e.type)) done = true;
    }
  }
}

const final = await fetch(`${BASE}/api/diagnose/${started.job_id}`).then((r) => r.json());
const rep = final.report;

console.log(`\n${'='.repeat(94)}\nSUPERVISED CLASSIFIERS TRAINED ON THE USER'S OWN LABELS\n${'='.repeat(94)}`);
for (const f of rep.findings.filter((x) => ['xgb-gbdt', 'rf-forest', 'mlp-classifier'].includes(x.algorithm))) {
  console.log(`\n  ${f.algorithm}  [${f.status}]${f.verdict ? ' verdict=' + f.verdict : ''}`);
  if (f.hypotheses.length) f.hypotheses.forEach((h, i) => console.log(`    ${i + 1}. ${h}`));
  if (f.invocations?.length) for (const i of f.invocations) console.log(`    model ${i.model} ${i.seconds}s`);
  console.log(`    ${String(f.reasoning).replace(/\s+/g, ' ').slice(0, 220)}`);
}

console.log(`\n${'='.repeat(94)}\nALL ALGORITHMS\n${'='.repeat(94)}`);
const yes = rep.findings.filter((f) => f.status === 'executed').length;
const na = rep.findings.filter((f) => f.status === 'not_applicable').length;
for (const f of rep.findings) {
  const det = f.detection_rate !== null ? `alarm=${(f.detection_rate * 100).toFixed(1)}%` : '';
  console.log(`  ${String(f.algorithm).padEnd(18)} ${String(f.status).padEnd(16)} ${String(f.verdict || '-').padEnd(7)} ${det}`);
}
console.log(`\n  executed: ${yes}   not applicable: ${na}   total: ${rep.findings.length}`);
console.log(`  elapsed: ${((Date.now() - t0) / 1000).toFixed(1)}s  (LLM algorithms dominate)`);

// ---- no TEP label may leak into a user-trained answer ----------------------
const leak = rep.findings
  .filter((f) => ['xgb-gbdt', 'rf-forest', 'mlp-classifier'].includes(f.algorithm))
  .flatMap((f) => f.hypotheses)
  .filter((h) => /IDV\s*\(?\d/i.test(h));
console.log(leak.length
  ? `\n  ⚠ TEP label leaked into a user-trained answer: ${leak.join(' | ')}`
  : '\n  ✔ no TEP/IDV label appears in any user-trained answer — the models speak the user\'s classes');

fs.rmSync(tmp, { recursive: true, force: true });
await fetch(`${BASE}/api/uploads/${up.upload.upload_id}`, { method: 'DELETE' });
console.log('');
