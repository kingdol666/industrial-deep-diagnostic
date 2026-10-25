#!/usr/bin/env node
// Session-management acceptance probe (plan v2 Phase E).
//
// Runs in two stages around a backend restart because two requirements are
// restart-scoped:
//   stage before  — create the fixtures (pending run, lost session id, task,
//                   category, renamed/categorized/soft-deleted run);
//   stage after   — assert pending→stopped, session recovery, task survival,
//                   filtered listing, restore/purge, session-map.
//
// Usage:
//   node scripts/e2e/session-management-e2e.mjs before --base http://127.0.0.1:3210 --token <idd_...>
//   node scripts/e2e/session-management-e2e.mjs after  --base http://127.0.0.1:3210 --token <idd_...>
import { stmts } from '../../app/backend/src/db/database.mjs';

const args = process.argv.slice(2);
const stage = args[0];
const opt = (name, fallback = null) => {
  const i = args.indexOf(`--${name}`);
  return i >= 0 ? args[i + 1] : fallback;
};
const BASE = opt('base', 'http://127.0.0.1:3210');
const TOKEN = process.env.E2E_TOKEN || opt('token');
const STATE_FILE = opt('state', '.runtime-e2e-session-state.json');

if (!TOKEN) {
  console.error('missing --token <idd_...> (or E2E_TOKEN env)');
  process.exit(2);
}

const H = { 'Content-Type': 'application/json', Authorization: `Bearer ${TOKEN}` };
let failures = 0;
function check(name, ok, detail = '') {
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? `  ${String(detail).slice(0, 300)}` : ''}`);
  if (!ok) failures += 1;
}
async function api(method, path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: H,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  let json = null;
  try { json = await res.json(); } catch { /* non-JSON */ }
  return { status: res.status, json };
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function insertRun(id, { status, harness = 'claude', sessionId = null, intent = 'deep-diagnosis' }) {
  stmts.insertRun.run({
    runId: id, name: id, title: id, sceneName: 'e2e_session_scene',
    dataPath: 'data/smoke.csv', dataFolder: null, userQuestion: 'e2e',
    model: null, maxTurns: 10, reportLanguage: 'zh', harness,
    ontologyHit: 0, enhancementPolicy: 'auto', enhancementTriggered: 0,
    analysisIntent: intent, userId: null,
  });
  stmts.updateRunStatus.run({ runId: id, status });
  if (sessionId) stmts.updateRunSession.run({ runId: id, sessionId });
}

async function stageBefore() {
  const suffix = Date.now().toString(36).slice(-5);
  const state = { suffix };

  // 1) pending run → must become stopped after restart (S4)
  state.pendingRun = `e2e-pend-${suffix}`;
  insertRun(state.pendingRun, { status: 'pending' });

  // 2) completed run whose session id was lost → must be reconciled (S5②)
  state.lostRun = `e2e-lost-${suffix}`;
  const uuid = '3f2504e0-4f89-11d3-9a0c-0305e82c3301';
  insertRun(state.lostRun, { status: 'completed' });
  stmts.insertEventStream.run({
    runId: state.lostRun, seq: 1, eventType: 'system', eventSubtype: 'init',
    payloadJson: JSON.stringify({ type: 'system', subtype: 'init', session_id: uuid }),
  });
  state.lostUuid = uuid;

  // 3) external task (mock, non-wait) → must survive restart (P1)
  const task = await api('POST', '/api/external/v1/analyze', {
    folderPath: 'lsr_demo', analysisIntent: 'stability-report', harness: 'mock',
    sceneName: 'e2e_task_scene', question: 'e2e task persistence',
  });
  check('P1a task created (202)', task.status === 202 && !!task.json?.data?.task_id, JSON.stringify(task.json).slice(0, 200));
  state.taskId = task.json?.data?.task_id;
  state.taskRunId = task.json?.data?.run_id;

  // 4) category + rename + categorize (M2/M3)
  const cat = await api('POST', '/api/history/categories', { name: `E2E-${suffix}` });
  check('M3a category created', cat.status === 201 && !!cat.json?.data?.id, JSON.stringify(cat.json).slice(0, 200));
  state.categoryId = cat.json?.data?.id;

  const dup = await api('POST', '/api/history/categories', { name: `E2E-${suffix}` });
  check('M3b duplicate category refused (409)', dup.status === 409 && dup.json?.code === 'CATEGORY_EXISTS', dup.status);

  const rename = await api('PATCH', `/api/history/runs/${state.lostRun}`, { title: `重命名-${suffix}` });
  check('M2 rename ok', rename.status === 200 && rename.json?.data?.title === `重命名-${suffix}`, JSON.stringify(rename.json?.data).slice(0, 160));

  const blank = await api('PATCH', `/api/history/runs/${state.lostRun}`, { title: '   ' });
  check('M2b blank title refused (400)', blank.status === 400, blank.status);

  const catRun = await api('PATCH', `/api/history/runs/${state.lostRun}`, { category_id: state.categoryId });
  check('M3c categorize ok', catRun.status === 200 && catRun.json?.data?.category_id === state.categoryId, JSON.stringify(catRun.json?.data).slice(0, 160));

  const filtered = await api('GET', `/api/history/runs?category_id=${state.categoryId}`);
  const ids = (filtered.json?.data || []).map((r) => r.run_id);
  check('M3d category filter hits', filtered.status === 200 && ids.includes(state.lostRun), ids.join(','));

  // 5) soft delete + restore (M4) on a dedicated row
  state.softRun = `e2e-soft-${suffix}`;
  insertRun(state.softRun, { status: 'completed' });
  const del = await api('DELETE', `/api/history/runs/${state.softRun}`);
  check('M4a soft delete', del.status === 200 && del.json?.data?.purged === false, JSON.stringify(del.json?.data));
  const hidden = await api('GET', '/api/history/runs?limit=1000');
  check('M4b soft-deleted hidden by default', !(hidden.json?.data || []).some((r) => r.run_id === state.softRun));
  const shown = await api('GET', '/api/history/runs?include_deleted=true&limit=1000');
  check('M4c visible with include_deleted', (shown.json?.data || []).some((r) => r.run_id === state.softRun));
  const restored = await api('POST', `/api/history/runs/${state.softRun}/restore`);
  check('M4d restore ok', restored.status === 200 && !restored.json?.data?.deleted_at, JSON.stringify(restored.json?.data).slice(0, 160));

  // 6) harness lock: a claude run carrying an omp session id → 409 (S6)
  state.mismatchRun = `e2e-mismatch-${suffix}`;
  insertRun(state.mismatchRun, { status: 'completed', harness: 'claude', sessionId: `omp:run:${suffix}` });
  const chatBad = await api('POST', `/api/diagnosis/chat/${state.mismatchRun}`, { message: 'hello' });
  check('S6 harness mismatch refused (409)', chatBad.status === 409 && chatBad.json?.code === 'RUN_HARNESS_MISMATCH', JSON.stringify(chatBad.json).slice(0, 200));

  // 7) no-session stopped run → chat must not fail; it rebuilds via Continue (S3b)
  state.noSessionRun = `e2e-nosess-${suffix}`;
  insertRun(state.noSessionRun, { status: 'stopped', harness: 'mock' });
  const chatNoSess = await api('POST', `/api/diagnosis/chat/${state.noSessionRun}`, { message: '基于当前上下文继续' });
  check('S3b no-session chat accepted (rebuild path)', chatNoSess.status === 200, JSON.stringify(chatNoSess.json).slice(0, 200));

  // 8) session-map audit (S5④)
  const map = await api('GET', `/api/diagnosis/session-map/${state.lostRun}`);
  check('S5d session-map shape',
    map.status === 200 && map.json?.data?.harness === 'claude'
    && map.json?.data?.reconcilable === true && map.json?.data?.session_kind === 'none',
    JSON.stringify(map.json?.data).slice(0, 240));

  const fs = await import('node:fs');
  fs.writeFileSync(STATE_FILE, JSON.stringify(state, null, 2));
  console.log(`\nstate written to ${STATE_FILE}`);
  console.log(`[BEFORE] failures=${failures}`);
  process.exit(failures ? 1 : 0);
}

async function stageAfter() {
  const fs = await import('node:fs');
  const state = JSON.parse(fs.readFileSync(STATE_FILE, 'utf8'));

  // S4: pending → stopped after restart
  const pend = await api('GET', `/api/history/runs/${state.pendingRun}`);
  check('S4 pending→stopped after restart',
    pend.json?.data?.status === 'stopped' && /restarted before execution/i.test(pend.json?.data?.error_message || ''),
    `status=${pend.json?.data?.status} err=${pend.json?.data?.error_message}`);

  // S5②: session id recovered from event stream
  const lost = await api('GET', `/api/diagnosis/session-map/${state.lostRun}`);
  check('S5b session id reconciled after restart',
    lost.json?.data?.session_id === state.lostUuid && lost.json?.data?.resumable === true,
    JSON.stringify(lost.json?.data).slice(0, 240));

  // P1: task survives restart and reports a real terminal state
  if (state.taskId) {
    const task = await api('GET', `/api/external/v1/tasks/${state.taskId}`);
    const st = task.json?.data?.status;
    check('P1b task queryable after restart',
      task.status === 200 && ['completed', 'running', 'accepted', 'failed', 'stopped'].includes(st),
      `status=${task.status} task=${st}`);
    const list = await api('GET', '/api/external/v1/tasks');
    const flat = JSON.stringify(list.json);
    check('P1c task listed after restart', flat.includes(state.taskId), list.status);
  }

  // M4e: purge removes row and (when recorded) the workspace directory
  const purge = await api('DELETE', `/api/history/runs/${state.pendingRun}?purge=true`);
  check('M4e purge ok', purge.status === 200 && purge.json?.data?.purged === true, JSON.stringify(purge.json?.data));
  const gone = await api('GET', `/api/history/runs/${state.pendingRun}`);
  check('M4f purged run gone (404)', gone.status === 404, gone.status);

  // M3e: deleting a category clears the reference but keeps the run
  if (state.categoryId) {
    const delCat = await api('DELETE', `/api/history/categories/${state.categoryId}`);
    check('M3e category deleted', delCat.status === 200, JSON.stringify(delCat.json?.data));
    const run = await api('GET', `/api/history/runs/${state.lostRun}`);
    check('M3f run kept, category cleared',
      run.status === 200 && (run.json?.data?.category_id === null || run.json?.data?.category_id === undefined),
      JSON.stringify(run.json?.data?.category_id));
  }

  // P2: specialist artifact manifest. Prefer a real (non-mock) stability run so
  // the probe proves the specialist inventory, not just the mock's report.md.
  const runs = await api('GET', '/api/history/runs?limit=200');
  const candidates = (runs.json?.data || []).filter(
    (r) => r.analysis_intent === 'stability-report' && r.status === 'completed'
      && r.workspace_path && r.harness !== 'mock',
  );
  let checked = null;
  for (const candidate of candidates.slice(0, 5)) {
    const result = await api('GET', `/api/external/v1/analyze/${candidate.run_id}`);
    const art = result.json?.data?.result?.artifacts;
    const kinds = (art?.artifacts || []).map((a) => a.kind);
    checked = { art, kinds, run: candidate.run_id };
    if (kinds.includes('stability_report') && kinds.includes('stability_html')) break;
  }
  check('P2 stability artifact manifest applicable',
    checked?.art?.applicable === true && checked.kinds.includes('stability_report')
    && checked.kinds.includes('stability_html'),
    checked ? `run=${checked.run} applicable=${checked.art?.applicable} kinds=${checked.kinds.join(',')}`
      : 'no real completed stability run found');

  console.log(`[AFTER] failures=${failures}`);
  process.exit(failures ? 1 : 0);
}

if (stage === 'before') await stageBefore();
else if (stage === 'after') await stageAfter();
else {
  console.error('usage: session-management-e2e.mjs before|after --base <url> --token <idd_...>');
  process.exit(2);
}
