// Opt-in real OpenCode/LM Studio smoke test, using only generated data and a temporary database.
// From app/backend: node test/live-gemma-knowledge.mjs
import { mkdtempSync, mkdirSync, writeFileSync, existsSync, readdirSync } from 'node:fs';
import { join, relative, resolve, sep } from 'node:path';
import { tmpdir } from 'node:os';
import { createServer } from 'node:http';
import { once } from 'node:events';
import { setTimeout as delay } from 'node:timers/promises';
import { fileURLToPath } from 'node:url';
import express from 'express';

const root = fileURLToPath(new URL('../../../', import.meta.url));
const scratch = mkdtempSync(join(root, '.tmp-idd-gemma-'));
const stateDir = mkdtempSync(join(tmpdir(), 'idd-gemma-db-'));
Object.assign(process.env, {
  DATABASE_PATH: join(stateDir, 'isolated.sqlite'), DATA_DIR: relative(root, scratch),
  LINE_MEMORY_DIR: join(stateDir, 'memory'), AUTH_ENABLED: '1', AUTH_JWT_SECRET: 'synthetic-test-only',
  IDD_TRUSTED_KNOWLEDGE_RUNTIME: '1', IDD_OPENCODE_LMSTUDIO: '1',
  IDD_OPENCODE_LMSTUDIO_MODEL: process.env.IDD_OPENCODE_LMSTUDIO_MODEL || 'google/gemma-4-12b-qat',
});
const { config } = await import('../../../config/loader.mjs');
const runRoot = join(scratch, 'runs');
const inputs = join(scratch, 'synthetic');
mkdirSync(runRoot);
mkdirSync(inputs);
const file = join(inputs, 'window.csv');
const readings = Array.from({ length: 180 }, (_, i) =>
  `${new Date(Date.UTC(2026, 9, 1, 0, i)).toISOString()},${(60 + Math.sin(i / 4) * 0.4 + (i > 149 ? 4 : 0)).toFixed(3)}`);
writeFileSync(file, `timestamp,temperature\n${readings.join('\n')}\n`);
config.data.workspace_dir = relative(root, runRoot);
config.engine.close_run_delay_seconds = 0;
const { db, stmts } = await import('../src/db/database.mjs');
const { signJwt } = await import('../src/services/auth.service.mjs');
const { authGuard } = await import('../src/middleware/auth.middleware.mjs');
const { recordCompletedEvidence } = await import('../src/services/knowledge.service.mjs');
const { default: lines } = await import('../src/routes/production-line.routes.mjs');
const { default: diagnosis } = await import('../src/routes/diagnosis.routes.mjs');
const { default: knowledge } = await import('../src/routes/knowledge.routes.mjs');
const app = express();
app.use(express.json());
app.use('/api', authGuard);
app.use('/api/lines', lines);
app.use('/api/diagnosis', diagnosis);
app.use('/api/knowledge', knowledge);
const { lastInsertRowid: uid } = db.prepare("INSERT INTO users (username,password_hash,role) VALUES ('fixture_owner','fixture','user')").run();
db.prepare('INSERT INTO data_folders (name,path,owner_user_id) VALUES (?,?,?)').run('synthetic', inputs, uid);
const srv = createServer(app).listen(0, '127.0.0.1');
await once(srv, 'listening');
const headers = { 'Content-Type': 'application/json', Authorization: `Bearer ${signJwt({ sub: Number(uid), type: 'session' }, 1800)}` };
async function request(path, body) {
  const response = await fetch(`http://127.0.0.1:${srv.address().port}/api${path}`, {
    method: body === undefined ? 'GET' : 'POST', headers, signal: AbortSignal.timeout(35000),
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const json = await response.json();
  if (!response.ok) throw new Error(`${path} HTTP ${response.status} ${JSON.stringify(json)}`);
  return json.data ?? json;
}

try {
  const line = await request('/lines', { name: 'Synthetic temperature line' });
  db.prepare(`INSERT INTO diagnostic_runs (run_id,name,scene_name,data_path,status,owner_user_id,user_id,line_id,
    completion_revision,completed_at,dataset_refs_json,harness) VALUES ('synthetic-prior','fixture','fixture',?,'completed',?,?,?,1,'2026-10-01','[]','opencode')`)
    .run(file, uid, String(uid), line.line_id);
  if (recordCompletedEvidence('synthetic-prior', 1, [{ finding_id: 'local-temp', subject: 'temperature',
    detail: 'Synthetic historical temperature observation: fixture reference AMBER-614. Advisory only.' }]) !== 1) {
    throw new Error('Could not seed synthetic history');
  }
  const { runId } = await request('/diagnosis/start', {
    dataPath: file, lineId: line.line_id, harness: process.env.IDD_LIVE_HARNESS || 'opencode', analysisIntent: 'quick-screen', sceneName: 'gemma_qc',
    reportLanguage: 'en', timeoutMinutes: 15, knowledgePolicy: { mode: 'on_demand', own_line: true, references: [] },
    userQuestion: 'Run the Sentinel quick-screen on this synthetic temperature CSV. The historical comparison needed is '
      + 'the synthetic temperature baseline: use the built-in idd_memory search tool for temperature, cite the result as advisory only, then '
      + 'follow the Sentinel skill and generate the gated HTML and alert JSON. Use the absolute directory '
      + `${runRoot.split(sep).join('/')} as the parent of your timestamped run folder with the exact runtime scene suffix. `
      + 'Do not use web or RAG; do not read any other data folders.',
  });
  const audit = db.prepare('SELECT action,outcome,item_count FROM knowledge_retrievals WHERE run_id=? AND attempt_id IS NOT NULL ORDER BY rowid');
  console.log('Created local job', runId, 'in', scratch);
  if (audit.all(runId).length) throw new Error('Unexpected retrieval before execution');
  await request(`/diagnosis/execute/${runId}`, {});
  let prior;
  for (let i = 0; i < 190; i++) {
    const row = stmts.getRunById.get(runId);
    const status = JSON.stringify({ status: row.status, calls: audit.all(runId), workspace: row.workspace_path,
      error: row.error_message, dirs: readdirSync(runRoot) });
    if (status !== prior) { console.log('Observed', status); prior = status; }
    if (!['running', 'pending', 'queued'].includes(row.status)) break;
    await delay(5000);
  }
  const row = stmts.getRunById.get(runId);
  console.log('Final', { status: row.status, workspace: row.workspace_path, report: row.report_path, scratch, stateDir });
  if (row.status !== 'completed' || !audit.all(runId).some((entry) => entry.action === 'search' && entry.item_count > 0)
    || !row.report_path || !existsSync(resolve(root, row.report_path))) process.exitCode = 1;
} finally {
  await new Promise((done) => srv.close(done));
}
