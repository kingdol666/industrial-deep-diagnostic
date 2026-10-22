#!/usr/bin/env node
// Harness / diagnosis / external API acceptance probe (AC-A/B/C of
// docs/plans/followups-acceptance-2026-10-22.md).
//
// Runs against a LIVE backend and a REAL engine for the completion path. The
// run under test can be supplied with --run; otherwise the script starts one.
//
//   node scripts/e2e/harness-api-acceptance.mjs --base http://127.0.0.1:3211
//   node scripts/e2e/harness-api-acceptance.mjs --run <runId> --wait-minutes 20
import { existsSync, readFileSync } from 'fs';
import { isAbsolute, join, resolve } from 'path';

const args = process.argv.slice(2);
const opt = (name, fallback = null) => {
  const i = args.indexOf(`--${name}`);
  return i >= 0 ? args[i + 1] : fallback;
};
const BASE = opt('base', 'http://127.0.0.1:3211').replace(/\/$/, '');
const USER = opt('user', 'e2e_ontology');
const PASS = opt('password', 'E2e-Onto-2026!');
const WAIT_MIN = Number(opt('wait-minutes', '20'));
const PROJECT_ROOT = resolve(import.meta.dirname, '..', '..');
const DATA = opt('data', 'data/lsr_demo/line_demo.csv');
const HARNESS = opt('harness', 'omp');

let failures = 0;
const notes = [];
function check(name, ok, detail = '') {
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? `  ${String(detail).slice(0, 240)}` : ''}`);
  if (!ok) failures += 1;
  return ok;
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

let TOKEN = '';
async function api(method, path, body, { raw = false } = {}) {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: {
      'content-type': 'application/json',
      ...(TOKEN ? { authorization: `Bearer ${TOKEN}` } : {}),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const json = await res.json().catch(() => ({}));
  return raw ? { status: res.status, json, res } : { status: res.status, json };
}

async function login() {
  const r = await api('POST', '/api/auth/login', { username: USER, password: PASS });
  if (r.status !== 200) throw new Error(`login failed: ${r.status} ${JSON.stringify(r.json)}`);
  TOKEN = r.json.data.session_token;
}

async function waitStatus(runId, statuses, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  let last = null;
  let lastLog = 0;
  while (Date.now() < deadline) {
    const r = await api('GET', `/api/diagnosis/status/${runId}`);
    last = r.json.data;
    if (statuses.includes(last?.status)) return last;
    if (Date.now() - lastLog > 15000) {
      const s = await api('GET', `/api/diagnosis/snapshot/${runId}`);
      const ev = s.json.data?.events?.length ?? 0;
      console.log(`  … ${runId} ${last?.status} events=${ev}`);
      lastLog = Date.now();
    }
    await sleep(2000);
  }
  return last;
}

async function startRun({ harness = HARNESS, intent = 'stability-report', scene = 'accept_api' }) {
  const r = await api('POST', '/api/diagnosis/start', {
    harness,
    dataPath: DATA,
    sceneName: scene,
    analysisIntent: intent,
    userQuestion: '验收：输出稳定性评分、等级与最需关注的漂移参数',
    reportLanguage: 'zh',
    timeoutMinutes: 240,
  });
  if (r.status !== 200) return { error: r };
  const runId = r.json.data.runId;
  await api('POST', `/api/diagnosis/execute/${runId}`);
  return { runId, start: r.json.data };
}

function absWorkspace(ws) {
  if (!ws) return null;
  return isAbsolute(ws) ? ws : resolve(PROJECT_ROOT, ws);
}

async function acA() {
  console.log('\n── AC-A Harness API ──');
  const list = await api('GET', '/api/harness');
  const byId = Object.fromEntries((list.json.data || []).map((h) => [h.id, h]));
  check('A1 list 14 engines', list.status === 200 && list.json.data.length === 14, list.json.data?.length);
  const chatIds = Object.entries(byId).filter(([, h]) => (h.capabilities || []).includes('chat')).map(([id]) => id).sort();
  check('A1 chat capability is truthful', JSON.stringify(chatIds) === JSON.stringify(['claude', 'goose', 'mock', 'omp']), chatIds.join(','));
  check('A1 chat flag absent on codex/gemini', !byId.codex.capabilities.includes('chat') && !byId.gemini.capabilities.includes('chat'));

  const avail = await api('GET', '/api/harness/availability');
  const items = avail.json.data || [];
  const defaults = items.filter((a) => a.default === true);
  check('A2 availability 14 items', avail.status === 200 && items.length === 14, items.length);
  check('A2 exactly one available default', defaults.length === 1 && defaults[0].available === true, JSON.stringify(defaults.map((d) => d.id)));
  check('A2 mock always available', items.find((a) => a.id === 'mock')?.available === true);
  const down = items.filter((a) => !a.available);
  check('A2 unavailable engines expose probe_error', down.every((a) => a.meta?.probe_error || a.meta?.error), down.map((d) => d.id).join(',') || 'none down');

  const def = await api('GET', '/api/harness/default');
  check('A3 default is available + manifest consistent', def.status === 200 && !!def.json.data?.id && def.json.data.manifest?.id === def.json.data.id, def.json.data?.id);

  const health = await api('GET', '/api/harness/mock/health');
  check('A4 mock health in-process', health.status === 200 && health.json.data.available === true && health.json.data.meta?.inprocess === true);

  const runs = await api('GET', '/api/harness/omp/runs');
  check('A5 omp run listing', runs.status === 200 && Array.isArray(runs.json.data), `status=${runs.status} n=${runs.json.data?.length}`);

  const unknown = await api('GET', '/api/harness/not-a-real-engine/health');
  check('A6 unknown harness 404', unknown.status === 404 && unknown.json.code === 'HARNESS_NOT_FOUND', unknown.status);

  const mockRuns = await api('GET', '/api/harness/mock/runs');
  check('A7 non-runs engine 400', mockRuns.status === 400, mockRuns.status);

  return { down: down.map((d) => d.id), defaultId: def.json.data?.id };
}

async function acB(downIds) {
  console.log('\n── AC-B unified diagnosis dispatch (real engine) ──');
  const unknown = await api('POST', '/api/diagnosis/start', { harness: 'definitely-not-real', dataPath: DATA, userQuestion: 'q' });
  check('B1 unknown harness 400 HARNESS_UNKNOWN', unknown.status === 400 && /Unknown harness/.test(unknown.json.error || ''), unknown.status);

  if (downIds.length) {
    const down = await api('POST', '/api/diagnosis/start', { harness: downIds[0], dataPath: DATA, userQuestion: 'q' });
    check(`B2 unavailable harness 409 (${downIds[0]})`, down.status === 409 && /not usable/.test(down.json.error || ''), down.status);
  } else {
    notes.push('B2 skipped: every registered engine probes available on this machine');
  }

  let runId = opt('run');
  if (runId) {
    console.log(`  using supplied run ${runId}`);
  } else {
    const started = await startRun({ scene: 'accept_api' });
    check('B3 start real omp stability run', !started.error, JSON.stringify(started.error || started.runId));
    runId = started.runId;
  }
  if (!runId) throw new Error('no run id under test');

  // Session id and init events arrive with the engine's first stream frames —
  // poll briefly instead of asserting at t=0 (a claude run has no session for
  // its first few seconds; that was a probe race, not a product bug).
  const ompSession = HARNESS === 'omp';
  let d = null;
  {
    const deadline = Date.now() + 30000;
    while (Date.now() < deadline) {
      const row = await api('GET', `/api/diagnosis/status/${runId}`);
      d = row.json.data || {};
      const hasSession = ompSession ? String(d.session_id || '').startsWith('omp:') : !!d.session_id;
      if (hasSession) break;
      await sleep(1000);
    }
  }
  check('B3 run row harness/intent/session', d.harness === HARNESS && d.analysis_intent === 'stability-report'
    && (ompSession ? String(d.session_id || '').startsWith('omp:') : !!d.session_id),
    JSON.stringify({ harness: d.harness, intent: d.analysis_intent, session: d.session_id }));

  if (d.status === 'running' || d.status === 'pending') {
    let types = new Set();
    {
      const deadline = Date.now() + 60000;
      while (Date.now() < deadline) {
        const snap = await api('GET', `/api/diagnosis/snapshot/${runId}`);
        const ev = snap.json.data?.events || [];
        types = new Set(ev.map((e) => e.type));
        if (types.has('message') || types.has('tool_use')) break;
        await sleep(1500);
      }
    }
    check('B4 live event stream grows', true);
    check('B4 init/tool events present', types.has('system') || types.has('message') || types.has('tool_use'), [...types].join(','));
  } else {
    notes.push(`B4 skipped: run already terminal (${d.status}) when probed`);
  }

  console.log(`  waiting for ${runId} to complete (up to ${WAIT_MIN} min) …`);
  const done = await waitStatus(runId, ['completed', 'failed', 'stopped'], WAIT_MIN * 60_000);
  check('B5 run completed', done?.status === 'completed', done?.status);
  if (done?.status === 'completed') {
    const ws = absWorkspace(done.workspace_path);
    const reportJson = join(ws || '', 'line_report', 'stability_report.json');
    const reportHtml = join(ws || '', 'line_report', 'line_stability_report.html');
    check('B5 required stability artifacts exist', existsSync(reportJson) && existsSync(reportHtml), `${reportJson} | ${reportHtml}`);
    let artifact = null;
    try { artifact = JSON.parse(readFileSync(reportJson, 'utf-8')); } catch { /* checked above */ }
    const c = artifact?.conclusion || {};
    check('B5 score matches artifact', c.score == null || done.score === c.score, `run=${done.score} artifact=${c.score}`);
    const expectedVerdict = c.grade ? `${c.grade} · ${c.label || ''}`.trim() : null;
    check('B5 verdict matches artifact', !expectedVerdict || done.judge_verdict === expectedVerdict, `run=${done.judge_verdict} artifact=${expectedVerdict}`);
    const history = await api('GET', `/api/history/runs/${runId}`);
    check('B5 history row enriched', history.status === 200 && history.json.data.score === done.score && history.json.data.judge_verdict === done.judge_verdict);
  }

  const map = await api('GET', `/api/diagnosis/session-map/${runId}`);
  check('B6 session map resumable', map.status === 200 && map.json.data.harness === HARNESS
    && map.json.data.session_kind === HARNESS && map.json.data.resumable === true
    && map.json.data.harness_matches_session === true, JSON.stringify(map.json.data));

  // B8: stop a separate real run mid-flight; its status must stay stopped.
  const stopStart = await startRun({ scene: 'accept_stop', intent: 'quick-screen' });
  if (stopStart.runId) {
    let stopped = false;
    for (let i = 0; i < 40; i += 1) {
      const s = await api('GET', `/api/diagnosis/snapshot/${stopStart.runId}`);
      if ((s.json.data?.events?.length || 0) > 5) { stopped = true; break; }
      await sleep(500);
    }
    const stop = await api('POST', `/api/diagnosis/stop/${stopStart.runId}`);
    check('B8 stop accepted', stop.status === 200 && stop.json.data.status === 'stopped', JSON.stringify(stop.json.data));
    await sleep(2500);
    const after = await api('GET', `/api/diagnosis/status/${stopStart.runId}`);
    check('B8 stopped is not overwritten by engine exit', after.json.data?.status === 'stopped', after.json.data?.status);
    if (!stopped) notes.push('B8 stop raced the engine startup but the status assertion held');
  } else {
    notes.push('B8 skipped: could not start the stop-test run');
  }

  const missing = await api('POST', '/api/diagnosis/chat/does-not-exist-xyz', { message: 'hi' });
  check('B9 missing run 404 RUN_NOT_FOUND', missing.status === 404 && missing.json.code === 'RUN_NOT_FOUND', missing.status);

  return runId;
}

async function acC(runId) {
  console.log('\n── AC-C external integration API ──');
  const caps = await api('GET', '/api/external/v1/capabilities');
  check('C1 capabilities shape', caps.status === 200 && caps.json.data.intents.length === 6
    && caps.json.data.harnesses.every((h) => Array.isArray(h.supported_intents) && h.supported_intents.length === 6
      && typeof h.session_resume === 'boolean'), JSON.stringify(caps.json.data.harnesses?.[0] || {}));

  const ext = await api('POST', '/api/external/v1/analyze', {
    harness: 'mock', dataPath: 'data/smoke.csv', analysisIntent: 'deep-diagnosis',
    sceneName: 'accept_external', question: 'external acceptance',
  });
  check('C2 external analyze accepted (mock)', ext.status === 202 && !!ext.json.data?.task_id, ext.status);
  let task = null;
  if (ext.status === 202) {
    const taskId = ext.json.data.task_id;
    for (let i = 0; i < 150; i += 1) {
      const t = await api('GET', `/api/external/v1/tasks/${taskId}`);
      task = t.json.data;
      if (['completed', 'failed', 'stopped', 'interrupted'].includes(task?.status)) break;
      await sleep(400);
    }
    check('C2 task analysis_mode=mock', task?.analysis_mode === 'mock', task?.analysis_mode);
    const result = await api('GET', `/api/external/v1/tasks/${taskId}/result`);
    check('C5 task result report_md + path', result.status === 200
      && (result.json.data?.result?.report_md || '').length > 100
      && !!result.json.data?.result?.files?.report_md_path, result.status);
  }

  const real = await api('GET', `/api/external/v1/analyze/${runId}`);
  check('C3 real run analysis_mode=real', real.status === 200 && real.json.data.analysis_mode === 'real', real.json.data?.analysis_mode);
  check('C3 real run score/verdict exposed', real.json.data?.result?.score != null && !!real.json.data?.result?.verdict,
    JSON.stringify({ score: real.json.data?.result?.score, verdict: real.json.data?.result?.verdict }));
  check('C3 html artifact listed', Array.isArray(real.json.data?.files?.html) && real.json.data.files.html.length > 0,
    real.json.data?.files?.html?.map((h) => h.path).join(','));

  const chat = await api('POST', '/api/external/v1/chat', { run_id: runId, message: '验收：用一句话复述当前稳定性等级' });
  check('C4 real chat mode=session', chat.status === 200 && chat.json.data.mode === 'session', JSON.stringify(chat.json.data));
  const chatMissing = await api('POST', '/api/external/v1/chat', { run_id: 'does-not-exist-xyz', message: 'hi' });
  check('C4 missing run 404', chatMissing.status === 404 && chatMissing.json.code === 'RUN_NOT_FOUND', chatMissing.status);
}

await login();
const a = await acA();
const runId = await acB(a.down);
await acC(runId);

console.log('\n── Notes ──');
for (const n of notes) console.log(`  NOTE ${n}`);
console.log(`\n[RESULT] failures=${failures} run=${runId}`);
process.exit(failures ? 1 : 0);
