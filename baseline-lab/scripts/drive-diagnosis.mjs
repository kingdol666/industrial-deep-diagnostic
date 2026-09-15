// Drive a real diagnosis through the HTTP API and print the SSE stream live.
//
// This mirrors exactly what the browser does: POST /api/diagnose, then consume
// GET /api/diagnose/:id/stream as Server-Sent Events, then read the final report.
//
//   node scripts/drive-diagnosis.mjs <uploadId> [algo,algo,...]

const uploadId = process.argv[2];
const algos = (process.argv[3] || 'pca-t2-spe,kpca-rbf,llm-direct,llm-cot').split(',').map((s) => s.trim());
if (!uploadId) {
  console.error('usage: node scripts/drive-diagnosis.mjs <uploadId> [algo,algo,...]');
  process.exit(2);
}
const BASE = process.env.LAB_URL || 'http://localhost:5190';

const t0 = Date.now();
const el = () => `${((Date.now() - t0) / 1000).toFixed(1)}s`.padStart(7);

console.log(`\nPOST ${BASE}/api/diagnose`);
const started = await fetch(`${BASE}/api/diagnose`, {
  method: 'POST',
  headers: { 'content-type': 'application/json' },
  body: JSON.stringify({ uploadId, algorithms: algos }),
}).then(async (r) => {
  const j = await r.json();
  if (!r.ok) throw new Error(`start failed: ${r.status} ${JSON.stringify(j)}`);
  return j;
});
console.log(`  job_id   : ${started.job_id}`);
console.log(`  running  : ${started.algorithms.join(', ')}`);
if (started.refused?.length) {
  for (const r of started.refused) console.log(`  refused  : ${r.algorithm} — ${r.reason}`);
}
console.log(`  stream   : ${started.stream_url}\n`);

// ---- consume the live SSE stream, exactly as the frontend does --------------
const res = await fetch(`${BASE}${started.stream_url}`, { headers: { accept: 'text/event-stream' } });
if (!res.ok) throw new Error(`stream failed: ${res.status}`);

const reader = res.body.getReader();
const dec = new TextDecoder();
let buf = '';
let done = false;

while (!done) {
  const { value, done: streamEnd } = await reader.read();
  if (streamEnd) break;
  buf += dec.decode(value, { stream: true });
  const frames = buf.split('\n\n');
  buf = frames.pop();
  for (const frame of frames) {
    for (const line of frame.split('\n')) {
      if (!line.startsWith('data: ')) continue;
      const e = JSON.parse(line.slice(6));
      const tag = `[${el()}] ${String(e.type).padEnd(17)}`;
      switch (e.type) {
        case 'stage':
          console.log(`${tag} ${e.message}`);
          if (e.refused) for (const r of e.refused) console.log(`                          refused: ${r.algorithm}`);
          break;
        case 'algorithm_start':
          console.log(`${tag} ${e.algorithm}  (${e.family}${e.requires_provider ? ', needs LLM' : ', offline'})`);
          break;
        case 'llm_call_start':
          console.log(`${tag}   -> calling ${e.provider} / model=${e.model}  tag=${e.tag}  prompt=${e.prompt_chars} chars`);
          break;
        case 'llm_call_done':
          console.log(`${tag}   <- ${e.ok ? 'ok' : 'FAILED'} in ${e.seconds}s${e.error ? ` error=${e.error}` : ''}`);
          if (e.reply_head) console.log(`                          reply: ${String(e.reply_head).replace(/\s+/g, ' ').slice(0, 150)}`);
          break;
        case 'algorithm_done':
          console.log(`${tag} ${e.algorithm} -> ${e.status}${e.verdict ? ` / ${e.verdict}` : ''}  ${e.duration_ms ? (e.duration_ms / 1000).toFixed(1) + 's' : ''}`);
          console.log(`                          ${e.summary}`);
          for (const i of e.invocations || []) console.log(`                          call ${i.tag}: ${i.provider}/${i.model} ${i.seconds}s`);
          break;
        case 'complete':
          console.log(`${tag} report ready`);
          done = true;
          break;
        case 'error':
          console.log(`${tag} ERROR ${e.message}`);
          done = true;
          break;
        case 'end':
          console.log(`${tag} stream ended`);
          done = true;
          break;
        default:
          console.log(`${tag} ${JSON.stringify(e).slice(0, 140)}`);
      }
    }
  }
}

// ---- the rendered report ----------------------------------------------------
const final = await fetch(`${BASE}/api/diagnose/${started.job_id}`).then((r) => r.json());
const rep = final.report;
if (!rep) {
  console.log('\nno report produced');
  process.exit(1);
}

console.log(`\n${'='.repeat(78)}\nDIAGNOSIS REPORT  (${rep.dataset.label})\n${'='.repeat(78)}`);
console.log(`dataset   : ${rep.dataset.original_name} — ${rep.dataset.rows} rows x ${rep.dataset.numeric_columns} cols`);
console.log(`excluded  : ${rep.dataset.excluded_index_column || '(none)'}`);
console.log(`calibration: ${rep.method.calibration_rows} rows | monitored: ${rep.method.monitored_rows} rows`);
console.log(`headline  : ${rep.headline.executed} executed · ${rep.headline.fault_verdicts} fault · ${rep.headline.normal_verdicts} normal · ${rep.headline.llm_mechanisms} LLM mechanism(s)`);
console.log(`duration  : ${(rep.duration_ms / 1000).toFixed(1)}s`);

if (rep.mechanism_hypotheses.length) {
  console.log('\n--- MECHANISM HYPOTHESES (real LLM calls) ---');
  for (const m of rep.mechanism_hypotheses) {
    console.log(`\n  ${m.algorithm}  [${m.provider}/${m.model}] ${m.calls} call(s), ${m.seconds.toFixed(1)}s`);
    m.hypotheses.forEach((h, i) => console.log(`    ${i + 1}. ${String(h).slice(0, 130)}`));
    console.log(`    reasoning: ${String(m.reasoning).replace(/\s+/g, ' ').slice(0, 220)}...`);
  }
}

if (rep.consensus_variables.length) {
  console.log('\n--- VARIABLE CONSENSUS (independent detectors) ---');
  for (const v of rep.consensus_variables.slice(0, 8)) console.log(`  ${String(v.column).padEnd(16)} flagged by ${v.algorithms} algorithm(s)`);
}

console.log('\n--- PER-ALGORITHM ---');
for (const f of rep.findings) {
  const det = f.detection_rate !== null ? `alarm=${(f.detection_rate * 100).toFixed(1)}%` : '';
  console.log(`  ${String(f.algorithm).padEnd(18)} ${String(f.status).padEnd(16)} ${String(f.verdict || '-').padEnd(7)} ${det}`);
  if (f.variables.length) console.log(`      vars: ${f.variables.slice(0, 4).map((v) => `${v.column}=${v.contribution.toFixed(3)}`).join('  ')}`);
}
console.log('');
