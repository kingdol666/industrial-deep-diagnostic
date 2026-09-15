#!/usr/bin/env node
// verify-all-algorithms.mjs — exercise EVERY registered algorithm against an
// uploaded dataset through the real HTTP diagnosis API, and report honestly
// which ones are usable by a user and which are not.
//
//   node scripts/verify-all-algorithms.mjs <path-to-csv> [--llm] [--label name]
//
// The point is not to make every row say PASS. The point is to establish, with
// evidence, what a user actually gets for each algorithm on their own data —
// and to make any gap impossible to miss.

import fs from 'node:fs';
import path from 'node:path';
import { listAlgorithms, moduleHealth } from '../server/utils/registry.mjs';

const BASE = process.env.LAB_URL || 'http://localhost:5190';
const args = process.argv.slice(2);
const csvPath = args.find((a) => !a.startsWith('--'));
const withLlm = args.includes('--llm');
const label = args.includes('--label') ? args[args.indexOf('--label') + 1] : 'all-algorithms-verify';

if (!csvPath) { console.error('usage: node scripts/verify-all-algorithms.mjs <csv> [--llm]'); process.exit(2); }
if (!fs.existsSync(csvPath)) { console.error(`no such file: ${csvPath}`); process.exit(2); }

// ---------------------------------------------------------------- upload
console.log(`\n=== upload ===\nfile: ${csvPath}`);
const buf = fs.readFileSync(csvPath);
const fd = new FormData();
fd.append('file', new Blob([buf]), path.basename(csvPath));
fd.append('label', label);
fd.append('calibration_fraction', '0.25');
fd.append('process_description',
  'Uploaded industrial time-series record. Columns are sensor and manipulator tags; '
  + 'the first 25% of rows is treated as the calibration (nominal) segment.');

const up = await fetch(`${BASE}/api/uploads`, { method: 'POST', body: fd }).then((r) => r.json());
if (!up?.upload) { console.error('upload failed:', JSON.stringify(up).slice(0, 300)); process.exit(1); }
console.log(`  ${up.summary}`);
console.log(`  case_id: ${up.upload.case_id}`);

// ------------------------------------------------------- what the API says
const cap = await fetch(`${BASE}/api/diagnose`).then((r) => r.json());
console.log(`\n=== API capability report ===`);
console.log(`  runnable: ${cap.runnable.length}   refused: ${cap.refused.length}`);
for (const r of cap.refused) console.log(`    REFUSED ${r.id.padEnd(18)} ${r.reason}`);

// ---------------------------------------------------------- run everything
const health = moduleHealth();
const all = listAlgorithms().map((a) => a.id);
const toRun = withLlm ? all : all.filter((id) => !listAlgorithms().find((a) => a.id === id).requiresProvider);

console.log(`\n=== running ${toRun.length}/${all.length} algorithms (${withLlm ? 'including' : 'excluding'} LLM) ===`);

const started = await fetch(`${BASE}/api/diagnose`, {
  method: 'POST',
  headers: { 'content-type': 'application/json' },
  body: JSON.stringify({ uploadId: up.upload.upload_id, algorithms: toRun }),
}).then(async (r) => {
  const j = await r.json();
  if (!r.ok) { console.error('start failed:', JSON.stringify(j).slice(0, 400)); process.exit(1); }
  return j;
});
console.log(`  job: ${started.job_id}  running: ${started.algorithms.length}  refused: ${started.refused?.length || 0}`);
for (const r of started.refused || []) console.log(`    refused at start: ${r.algorithm} — ${r.reason}`);

// consume the SSE stream and note how long each algorithm took
const live = new Map();
const res = await fetch(`${BASE}${started.stream_url}`, { headers: { accept: 'text/event-stream' } });
const reader = res.body.getReader();
const dec = new TextDecoder();
let buf2 = '';
let finished = false;
while (!finished) {
  const { value, done } = await reader.read();
  if (done) break;
  buf2 += dec.decode(value, { stream: true });
  const frames = buf2.split('\n\n');
  buf2 = frames.pop();
  for (const f of frames) {
    for (const line of f.split('\n')) {
      if (!line.startsWith('data: ')) continue;
      const e = JSON.parse(line.slice(6));
      if (e.type === 'algorithm_start') live.set(e.algorithm, { started: Date.now(), calls: 0 });
      if (e.type === 'llm_call_done') { const l = live.get(e.algorithm); if (l) l.calls++; }
      if (e.type === 'algorithm_done') {
        const l = live.get(e.algorithm) || {};
        l.status = e.status; l.verdict = e.verdict; l.summary = e.summary;
        l.seconds = (Date.now() - l.started) / 1000;
        live.set(e.algorithm, l);
        console.log(`  [${String(e.status).padEnd(16)}] ${e.algorithm.padEnd(18)} ${l.seconds.toFixed(1)}s  ${String(e.summary).slice(0, 80)}`);
      }
      if (e.type === 'complete' || e.type === 'end' || e.type === 'error') finished = true;
    }
  }
}

const final = await fetch(`${BASE}/api/diagnose/${started.job_id}`).then((r) => r.json());
const rep = final.report;
if (!rep) { console.error('\nno report produced'); process.exit(1); }

// ------------------------------------------------------------- the verdict
console.log(`\n${'='.repeat(96)}\nPER-ALGORITHM USABILITY ON UPLOADED DATA\n${'='.repeat(96)}`);
const byAlgo = Object.fromEntries(rep.findings.map((f) => [f.algorithm, f]));

const rows = [];
for (const id of all) {
  const meta = listAlgorithms().find((a) => a.id === id);
  const f = byAlgo[id];
  const refused = (started.refused || []).find((r) => r.algorithm === id);
  let usable, why;
  if (f && f.status === 'executed') { usable = 'YES'; why = f.verdict ? `verdict=${f.verdict}` : 'executed'; }
  else if (f && f.status === 'skipped_no_provider') { usable = 'needs provider'; why = 'no LLM provider configured'; }
  else if (f && f.status === 'error') { usable = 'FAILED'; why = String(f.reasoning).slice(0, 70); }
  else if (refused) { usable = 'NOT APPLICABLE'; why = refused.reason; }
  else if (f && f.status === 'not_applicable') { usable = 'NOT APPLICABLE'; why = String(f.not_applicable_reason).slice(0, 70); }
  else { usable = 'not run'; why = withLlm ? 'unknown' : 'LLM algorithm, use --llm'; }
  rows.push({ id, family: meta.family, deterministic: meta.deterministic, requires_provider: Boolean(meta.requiresProvider), usable, why, seconds: live.get(id)?.seconds });
}

const w = [18, 11, 8, 16, 8];
console.log(['algorithm', 'family', 'det?', 'usable', 'secs'].map((h, i) => h.padEnd(w[i])).join('') + 'why');
console.log('-'.repeat(140));
for (const r of rows) {
  console.log(
    r.id.padEnd(w[0]) + String(r.family).padEnd(w[1]) + String(r.deterministic).padEnd(w[2])
    + r.usable.padEnd(w[3]) + (r.seconds != null ? r.seconds.toFixed(1) : '-').padEnd(w[4]) + String(r.why).slice(0, 60),
  );
}

const counts = rows.reduce((a, r) => { a[r.usable] = (a[r.usable] || 0) + 1; return a; }, {});
console.log('\nsummary:', JSON.stringify(counts));
console.log(`modules loaded: ${health.filter((h) => h.loaded).length}/${health.length}`);
const missing = health.filter((h) => !h.loaded);
if (missing.length) for (const m of missing) console.log(`  MISSING MODULE ${m.file}: ${m.error}`);

console.log(`\nreport: ${BASE}/api/diagnose/${started.job_id}`);
console.log(`events: ${rep.findings.length} findings, ${rep.headline.executed} executed\n`);

const notUsable = rows.filter((r) => r.usable !== 'YES' && !(r.usable === 'needs provider'));
console.log(notUsable.length
  ? `⚠ ${notUsable.length} algorithm(s) are NOT usable by a user on their own data:\n` +
    notUsable.map((r) => `    ${r.id}: ${r.why}`).join('\n') + '\n'
  : '✔ every algorithm executed on the uploaded data\n');

process.exit(0);
