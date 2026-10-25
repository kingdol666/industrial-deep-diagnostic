#!/usr/bin/env node
// FINAL live acceptance demo for the analysis-results management feature.
//
// One continuous narrative with a FRESH identity (no prior state):
//   0. service health + capability advertisement (results_index)
//   1. external exposure proof: mint an idd_ token, CORS preflight, 401s
//   2. a REAL analysis via POST /v1/analyze (mock harness) → completion hook
//      writes the results row the moment the run lands
//   3. the complete management loop on that result:
//      detail → description/tags PATCH → category create/assign →
//      per-category description view → index filter → report read-back →
//      unassign + category delete (result survives)
//   4. error contract on every new endpoint group
//
// Usage: node scripts/e2e/results-final-acceptance.mjs --base http://127.0.0.1:3210
const args = process.argv.slice(2);
const opt = (n, d = null) => { const i = args.indexOf(`--${n}`); return i >= 0 ? args[i + 1] : d; };
const BASE = opt('base', 'http://127.0.0.1:3210').replace(/\/$/, '');

let passes = 0;
let failures = 0;
function check(name, ok, detail = '') {
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? `  ${String(detail).slice(0, 200)}` : ''}`);
  if (ok) passes += 1; else failures += 1;
  return ok;
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// ── 0. health ──────────────────────────────────────────────────────────────
const health = await fetch(`${BASE}/api/health`).then((r) => r.json()).catch(() => null);
check('[0] backend healthy', !!health && health.status === 'ok');

// ── 1. fresh identity: register → session → idd_ API token ────────────────
const USER = `final_${Date.now().toString(36)}`;
const PASS = 'Final-Accept-2026!';
const reg = await fetch(`${BASE}/api/auth/register`, {
  method: 'POST', headers: { 'content-type': 'application/json' },
  body: JSON.stringify({ username: USER, password: PASS }),
});
const sessionToken = (await reg.json().catch(() => ({})))?.data?.session_token || '';
check('[1] fresh identity registered', reg.status === 200 && !!sessionToken, USER);

const mint = await fetch(`${BASE}/api/auth/tokens`, {
  method: 'POST',
  headers: { 'content-type': 'application/json', authorization: `Bearer ${sessionToken}` },
  body: JSON.stringify({ name: `final-acceptance-${Date.now().toString(36)}`, expires_in_days: 1 }),
});
const TOKEN = (await mint.json().catch(() => ({})))?.data?.token || '';
check('[1] idd_ API token minted for the fresh identity', /^idd_/.test(TOKEN || ''));

async function api(path, { method = 'GET', body, token = TOKEN } = {}) {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: {
      'content-type': 'application/json',
      ...(token ? { authorization: `Bearer ${token}` } : {}),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  return { status: res.status, json: await res.json().catch(() => ({})) };
}

// capability advertisement
const caps = await api('/api/external/v1/capabilities');
check('[1] capabilities advertises results_index + endpoint list',
  caps.json?.data?.results_index === true && Array.isArray(caps.json?.data?.results_endpoints)
  && caps.json.data.results_endpoints.length >= 3, caps.json?.data?.results_endpoints?.join(' | '));

// CORS preflight — proof another origin's browser can call this surface
const preflight = await fetch(`${BASE}/api/external/v1/results?limit=1`, {
  method: 'OPTIONS',
  headers: {
    Origin: 'https://agentworkshop.example',
    'Access-Control-Request-Method': 'GET',
    'Access-Control-Request-Headers': 'authorization,content-type',
  },
});
const acao = preflight.headers.get('access-control-allow-origin');
const acac = preflight.headers.get('access-control-allow-credentials');
check('[1] CORS preflight answered for a foreign origin',
  (preflight.status === 200 || preflight.status === 204) && !!acao,
  `${preflight.status} allow-origin=${acao} creds=${acac}`);

// 401 without a token, on every new endpoint group
const groups = [
  ['GET', '/api/external/v1/results'],
  ['GET', '/api/external/v1/results/categories'],
  ['POST', '/api/external/v1/results/categories'],
  ['GET', '/api/external/v1/results/categories/CAT-xx/results'],
];
let all401 = true;
for (const [method, path] of groups) {
  const r = await api(path, { method, token: null, body: method === 'POST' ? { name: 'x' } : undefined });
  if (r.status !== 401) all401 = false;
}
check('[1] every new endpoint group rejects token-less callers with 401', all401);

// ── 2. a REAL analysis via the external surface ────────────────────────────
const launch = await api('/api/external/v1/analyze', {
  method: 'POST',
  body: {
    harness: 'mock',
    analysisIntent: 'deep-diagnosis',
    dataPath: 'data/smoke.csv',
    sceneName: `final_accept_${Date.now().toString(36)}`,
    question: 'final acceptance demo',
  },
});
const taskId = launch.json?.data?.task_id;
const runId = launch.json?.data?.run_id;
check('[2] POST /v1/analyze accepted a real run', launch.status === 202 && !!runId, `${taskId}/${runId}`);

let status = null;
for (let i = 0; i < 120; i += 1) {
  const t = await api(`/api/external/v1/tasks/${taskId}`);
  status = t.json?.data?.status;
  if (['completed', 'failed', 'stopped'].includes(status)) break;
  await sleep(500);
}
check('[2] the run reached a terminal state', status === 'completed', String(status));

// completion hook wrote the row THIS instant — no backfill, no derive
const detail = await api(`/api/external/v1/results/${runId}?include_md=true`);
const d = detail.json?.data || {};
check('[2] completion hook: results row exists the moment the run lands',
  detail.status === 200 && d.derived === false && d.result_id === runId);
check('[2] detail carries summary + metadata + report',
  typeof d.summary === 'string' && d.summary.length > 0
  && d.metadata?.report_md?.bytes > 0 && typeof d.report_md === 'string' && d.report_md.length > 50,
  `report ${d.metadata?.report_md?.bytes} B`);

// report read-back through the file endpoint
const reportEnv = await api(d.report_md_url);
check('[2] report_md_url content equals the inline text',
  reportEnv.status === 200 && reportEnv.json?.data?.content === d.report_md);

// ── 3. the complete management loop on this result ────────────────────────
const descText = `最终验收描述-${Date.now().toString(36)}`;
const patched = await api(`/api/external/v1/results/${runId}`, {
  method: 'PATCH',
  body: { description: descText, tags: ['final-acceptance', 'demo'] },
});
check('[3] PATCH description+tags via external surface',
  patched.status === 200 && patched.json?.data?.description === descText
  && JSON.stringify(patched.json?.data?.tags) === JSON.stringify(['final-acceptance', 'demo']));

const byDesc = await api(`/api/external/v1/results?q=${encodeURIComponent(descText)}`);
check('[3] index finds the result by its edited description',
  byDesc.json?.data?.results?.length === 1 && byDesc.json.data.results[0].result_id === runId);

const catName = `最终验收分类-${Date.now().toString(36)}`;
const cat = await api('/api/external/v1/results/categories', { method: 'POST', body: { name: catName } });
const catId = cat.json?.data?.id;
check('[3] category created via external API', cat.status === 201 && !!catId, catName);

const assigned = await api(`/api/external/v1/results/${runId}`, { method: 'PATCH', body: { category_id: catId } });
check('[3] result filed into the category', assigned.json?.data?.category_id === catId);

const catList = await api('/api/external/v1/results/categories');
const mine = (catList.json?.data || []).find((c) => c.id === catId);
check('[3] category list shows it with result_count ≥ 1', !!mine && mine.result_count === 1,
  `${mine?.name} → ${mine?.result_count}`);

const view = await api(`/api/external/v1/results/categories/${encodeURIComponent(catId)}/results`);
const vd = view.json?.data || {};
check('[3] per-category description view returns our result with its description',
  view.status === 200 && vd.total === 1
  && vd.results[0]?.result_id === runId && vd.results[0]?.description === descText
  && vd.results[0]?.display_text === descText,
  `${vd.category?.name}: ${vd.total}`);

const filtered = await api(`/api/external/v1/results?category_id=${encodeURIComponent(catId)}`);
check('[3] index filter by category hits exactly this result',
  filtered.json?.data?.total === 1 && filtered.json.data.results[0].result_id === runId);

// console mirror parity for the new surface
const mirror = await api(`/api/results/categories/${encodeURIComponent(catId)}/results`);
check('[3] console mirror /api/results/categories/:id/results returns the same view',
  mirror.status === 200 && mirror.json?.data?.total === vd.total);

// lifecycle safety: unassign + delete → result survives
await api(`/api/external/v1/results/${runId}`, { method: 'PATCH', body: { category_id: null } });
const del = await api(`/api/external/v1/results/categories/${encodeURIComponent(catId)}`, { method: 'DELETE' });
const after = await api(`/api/external/v1/results/${runId}?include_md=false`);
check('[3] delete category keeps the result fully readable',
  del.status === 200 && after.status === 200 && after.json?.data?.category_id === null);
check('[3] category view 404 after deletion',
  (await api(`/api/external/v1/results/categories/${encodeURIComponent(catId)}/results`)).status === 404);

// ── 4. error contract on the new endpoints ─────────────────────────────────
// a LIVE category is needed for the duplicate-name check (the step-3 category
// was deleted there — re-creating its name would legitimately succeed)
const catName2 = `${catName}-b`;
const cat2 = await api('/api/external/v1/results/categories', { method: 'POST', body: { name: catName2 } });
const dup = await api('/api/external/v1/results/categories', { method: 'POST', body: { name: catName2 } });
check('[4] duplicate category name → 409 CATEGORY_EXISTS',
  cat2.status === 201 && dup.status === 409 && dup.json?.code === 'CATEGORY_EXISTS');
await api(`/api/external/v1/results/categories/${encodeURIComponent(cat2.json?.data?.id)}`, { method: 'DELETE' });
const emptyName = await api('/api/external/v1/results/categories', { method: 'POST', body: { name: '  ' } });
check('[4] blank category name → 400', emptyName.status === 400);
const unknownCat = await api('/api/external/v1/results/categories/CAT-nope/results');
check('[4] unknown category → 404 CATEGORY_NOT_FOUND',
  unknownCat.status === 404 && unknownCat.json?.code === 'CATEGORY_NOT_FOUND');
const summaryRo = await api(`/api/external/v1/results/${runId}`, { method: 'PATCH', body: { summary: 'x' } });
check('[4] PATCH summary → 400 SUMMARY_READONLY',
  summaryRo.status === 400 && summaryRo.json?.code === 'SUMMARY_READONLY');
const badQuery = await api('/api/external/v1/results?intent=nope');
check('[4] invalid index query → 400 RESULTS_QUERY_INVALID',
  badQuery.status === 400 && badQuery.json?.code === 'RESULTS_QUERY_INVALID');

console.log(`\n[RESULT] passes=${passes} failures=${failures}`);
if (failures) process.exitCode = 1;
