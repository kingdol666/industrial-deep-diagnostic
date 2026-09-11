#!/usr/bin/env node
// smoke-api.mjs — external-caller API smoke test for the multi-harness
// diagnosis console (AgentWorkShop-style engine integration).
//
// Usage:
//   node scripts/smoke-api.mjs --base http://localhost:3211 --token <idd_...>
//   IDD_API_TOKEN=idd_... node scripts/smoke-api.mjs
//
// The token is an API Token created via POST /api/auth/tokens (or a login
// session token). It is NEVER hardcoded — pass it per invocation.

const args = process.argv.slice(2);
function argOf(name, fallback) {
  const i = args.indexOf(name);
  return i >= 0 && args[i + 1] ? args[i + 1] : fallback;
}
const BASE = (argOf('--base', process.env.IDD_BASE_URL || 'http://localhost:3211')).replace(/\/$/, '');
const TOKEN = argOf('--token', process.env.IDD_API_TOKEN || '');

if (!TOKEN) {
  console.error('Missing token. Pass --token <idd_...> or set IDD_API_TOKEN.');
  process.exit(2);
}

let pass = 0;
let fail = 0;
const results = [];

function record(name, ok, detail = '') {
  if (ok) pass += 1;
  else fail += 1;
  results.push(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? ` — ${detail}` : ''}`);
}

async function api(method, path, body, { auth = true } = {}) {
  const headers = { 'content-type': 'application/json' };
  if (auth && TOKEN) headers.Authorization = `Bearer ${TOKEN}`;
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
    signal: AbortSignal.timeout(30000),
  });
  const json = await res.json().catch(() => ({}));
  return { status: res.status, json };
}

async function waitForStatus(runId, statuses, timeoutMs = 30000) {
  const deadline = Date.now() + timeoutMs;
  let last = null;
  while (Date.now() < deadline) {
    const { json } = await api('GET', `/api/diagnosis/status/${runId}`);
    last = json.data;
    if (statuses.includes(last?.status)) return last;
    await new Promise((r) => setTimeout(r, 400));
  }
  return last;
}

async function main() {
  // 1) Auth gate — no token must be rejected
  const anon = await api('GET', '/api/harness', null, { auth: false });
  record('auth gate (no token → 401)', anon.status === 401 && anon.json.success === false, `code=${anon.json.code}`);

  // 2) Token works — harness registry
  const harnesses = await api('GET', '/api/harness');
  const ids = (harnesses.json.data || []).map((h) => h.id);
  record('GET /api/harness → 14 engines', harnesses.status === 200 && ids.length === 14, ids.join(','));

  // 3) Default harness (best-adapted available; omp expected here)
  const def = await api('GET', '/api/harness/default');
  const defId = def.json.data?.id;
  record('GET /api/harness/default → omp', def.status === 200 && defId === 'omp', `default=${defId}`);

  // 4) Availability — exactly one default flag, engines probed
  const av = await api('GET', '/api/harness/availability');
  const defaults = (av.json.data || []).filter((a) => a.default === true);
  const available = (av.json.data || []).filter((a) => a.available === true).map((a) => a.id);
  record('GET /api/harness/availability', av.status === 200 && defaults.length === 1 && available.length >= 10,
    `default=${defaults[0]?.id}, available=${available.length}`);

  // 5) Per-engine health
  for (const id of ['omp', 'mock']) {
    const h = await api('GET', `/api/harness/${id}/health`);
    record(`GET /api/harness/${id}/health`, h.status === 200 && h.json.data?.available === true);
  }

  // 6) Full job on an explicitly chosen harness (mock — zero LLM cost)
  const start = await api('POST', '/api/diagnosis/start', {
    harness: 'mock',
    dataPath: 'data/smoke.csv',
    sceneName: 'api_smoke',
    userQuestion: 'external API smoke test',
    reportLanguage: 'zh',
  });
  const runId = start.json.data?.runId;
  record('POST /diagnosis/start (harness=mock)', start.status === 200 && !!runId, `runId=${runId}, harness=${start.json.data?.harness}`);

  if (runId) {
    const exec = await api('POST', `/api/diagnosis/execute/${runId}`);
    record('POST /diagnosis/execute', exec.status === 200 && exec.json.data?.status === 'running');

    const done = await waitForStatus(runId, ['completed', 'failed']);
    record('run completes', done?.status === 'completed',
      `status=${done?.status}, score=${done?.score}, verdict=${done?.judge_verdict}, report=${done?.report_path ? 'linked' : 'null'}`);

    const snap = await api('GET', `/api/diagnosis/snapshot/${runId}`);
    const types = (snap.json.data?.events || []).map((e) => e.type);
    record('GET /diagnosis/snapshot (event stream)', snap.status === 200
      && types.includes('system') && types.includes('message') && types.includes('stats'));

    // 7) Session chat on the finished run's engine session
    const chat = await api('POST', `/api/diagnosis/chat/${runId}`, { message: '补充说明轴承温升' });
    record('POST /diagnosis/chat (engine session)', chat.status === 200 && chat.json.success === true);

    // 8) Continue — re-run with follow-up context
    const cont = await api('POST', `/api/diagnosis/continue/${runId}`, { followUpMessage: '补充数据说明' });
    const contDone = cont.status === 200 ? await waitForStatus(runId, ['completed', 'failed']) : null;
    record('POST /diagnosis/continue', cont.status === 200 && contDone?.status === 'completed');
  }

  // 9) Default-harness job (omit harness → omp on this machine); create + stop, no LLM spend
  const defJob = await api('POST', '/api/diagnosis/start', {
    dataPath: 'data/smoke.csv', sceneName: 'api_smoke_default', userQuestion: 'default harness check',
  });
  record('POST /diagnosis/start (harness omitted → default)', defJob.status === 200
    && ['omp', 'claude', 'mock'].includes(defJob.json.data?.harness),
    `resolved harness=${defJob.json.data?.harness}`);
  if (defJob.json.data?.runId) await api('POST', `/api/diagnosis/stop/${defJob.json.data.runId}`);

  // 10) Error contracts — readable, coded failures
  const unknown = await api('POST', '/api/diagnosis/start', { harness: 'not-an-engine', dataPath: 'data/smoke.csv' });
  record('unknown harness → 400 HARNESS_UNKNOWN', unknown.status === 400 && unknown.json.code === 'HARNESS_UNKNOWN');

  const uninstalled = await api('POST', '/api/diagnosis/start', { harness: 'hermes', dataPath: 'data/smoke.csv' });
  record('uninstalled harness → 409 HARNESS_UNAVAILABLE', uninstalled.status === 409 && uninstalled.json.code === 'HARNESS_UNAVAILABLE',
    uninstalled.json.error?.slice(0, 60) + '...');

  const chatBad = await api('POST', '/api/chat/start', { harness: 'gemini', prompt: 'hi' });
  record('chat with non-chat harness → 400 CHAT_HARNESS_UNSUPPORTED', chatBad.status === 400 && chatBad.json.code === 'CHAT_HARNESS_UNSUPPORTED');

  // 11) History list
  const list = await api('GET', '/api/diagnosis/list');
  record('GET /diagnosis/list', list.status === 200 && Array.isArray(list.json.data) && list.json.data.length > 0);

  console.log(results.join('\n'));
  console.log(`\n${pass} passed, ${fail} failed — base=${BASE}`);
  process.exit(fail > 0 ? 1 : 0);
}

main().catch((e) => {
  console.error('smoke run crashed:', e.message);
  process.exit(1);
});
