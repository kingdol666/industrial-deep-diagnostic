#!/usr/bin/env node
// Final front/back contract probe — GET-only against existing runs.
// No diagnosis is started (no /diagnosis/start, no /execute, no external analyze).
//
// Usage: node scripts/e2e/api-contract-final.mjs --base http://127.0.0.1:3210
const args = process.argv.slice(2);
const opt = (n, d = null) => { const i = args.indexOf(`--${n}`); return i >= 0 ? args[i + 1] : d; };
const BASE = opt('base', 'http://127.0.0.1:3210').replace(/\/$/, '');
const USER = opt('user', 'e2e_ontology');
const PASS = opt('password', 'E2e-Onto-2026!');
const RUN = opt('run', '837404b0');
const HISTORY_RUN = opt('history-run', '46833919');

let failures = 0;
function check(name, ok, detail = '') {
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? `  ${String(detail).slice(0, 220)}` : ''}`);
  if (!ok) failures += 1;
}

let token = '';
async function api(method, path, { auth = true, raw = false } = {}) {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: {
      'content-type': 'application/json',
      ...(auth && token ? { authorization: `Bearer ${token}` } : {}),
    },
  });
  if (raw) return { status: res.status, res, text: await res.text() };
  const json = await res.json().catch(() => ({}));
  return { status: res.status, json };
}

const loginRes = await fetch(`${BASE}/api/auth/login`, {
  method: 'POST', headers: { 'content-type': 'application/json' },
  body: JSON.stringify({ username: USER, password: PASS }),
});
const loginJson = await loginRes.json();
token = loginJson?.data?.session_token || '';
check('auth login returns session token', loginRes.status === 200 && !!token, loginRes.status);

const unauth = await api('GET', '/api/history/runs?limit=1', { auth: false });
check('unauthenticated API is rejected', unauth.status === 401, unauth.status);

const health = await api('GET', '/api/health', { auth: false });
check('health ok', health.status === 200 && health.json.status === 'ok', health.status);

const harness = await api('GET', '/api/harness');
check('GET /api/harness lists 14 engines', harness.status === 200 && harness.json.data?.length === 14, harness.json.data?.length);
const chatIds = (harness.json.data || []).filter((h) => h.capabilities?.includes('chat')).map((h) => h.id).sort();
check('chat capability truth', JSON.stringify(chatIds) === JSON.stringify(['claude', 'goose', 'mock', 'omp']), chatIds.join(','));

const avail = await api('GET', '/api/harness/availability');
const items = avail.json.data || [];
check('availability 14 + one default', avail.status === 200 && items.length === 14 && items.filter((a) => a.default).length === 1,
  `${items.length}/${items.filter((a) => a.default).map((a) => a.id).join(',')}`);
check('availability carries provider_error field', items.every((a) => Object.prototype.hasOwnProperty.call(a, 'provider_error')));

const def = await api('GET', '/api/harness/default');
check('default harness resolvable', def.status === 200 && !!def.json.data?.id, def.json.data?.id);

const caps = await api('GET', '/api/external/v1/capabilities');
const capH = caps.json.data?.harnesses || [];
check('external capabilities 6 intents + honest matrix', caps.status === 200
  && caps.json.data?.intents?.length === 6
  && capH.length >= 14
  && capH.every((h) => Array.isArray(h.supported_intents) && h.supported_intents.length === 6 && typeof h.session_resume === 'boolean'),
  `${caps.json.data?.intents?.length} intents / ${capH.length} harnesses`);

const list = await api('GET', '/api/history/runs?limit=5');
check('history list returns rows', list.status === 200 && Array.isArray(list.json.data) && list.json.data.length > 0,
  `${list.json.data?.length} rows`);

const hist = await api('GET', `/api/history/runs/${HISTORY_RUN}`);
check('history detail carries artifact-derived outcome', hist.status === 200
  && hist.json.data?.score === 65.8 && String(hist.json.data?.judge_verdict || '').includes('波动'),
  JSON.stringify({ score: hist.json.data?.score, verdict: hist.json.data?.judge_verdict }));

const snap = await api('GET', `/api/diagnosis/snapshot/${RUN}?events_limit=200`);
check('snapshot is windowed', snap.status === 200
  && Array.isArray(snap.json.data?.events) && snap.json.data.events.length <= 200
  && snap.json.data.events_total > snap.json.data.events.length
  && snap.json.data.events_truncated === true
  && snap.json.data.events_limit === 200,
  JSON.stringify({ shown: snap.json.data?.events?.length, total: snap.json.data?.events_total, truncated: snap.json.data?.events_truncated }));

const map = await api('GET', `/api/diagnosis/session-map/${RUN}`);
check('session map is honest', map.status === 200 && map.json.data?.harness === 'claude'
  && map.json.data?.session_kind === 'claude' && map.json.data?.resumable === true
  && map.json.data?.harness_matches_session === true, JSON.stringify(map.json.data));

const ext = await api('GET', `/api/external/v1/analyze/${RUN}`);
check('external result: completed + real mode', ext.status === 200
  && ext.json.data?.status === 'completed' && ext.json.data?.analysis_mode === 'real', ext.json.data?.status);
check('external result: score/verdict/artifacts', ext.json.data?.result?.score === 65.8
  && String(ext.json.data?.result?.verdict || '').includes('波动')
  && Array.isArray(ext.json.data?.result?.artifacts?.artifacts)
  && ext.json.data.result.artifacts.artifacts.length > 0,
  JSON.stringify({ score: ext.json.data?.result?.score, verdict: ext.json.data?.result?.verdict }));
check('external result: HTML artifacts listed', Array.isArray(ext.json.data?.files?.html) && ext.json.data.files.html.length > 0,
  (ext.json.data?.files?.html || []).map((h) => h.path).join(','));

const ws = hist.json.data?.workspace_path;
const wsName = ws ? String(ws).split(/[/\\]/).pop() : null;
check('history row exposes workspace', !!wsName, wsName);
if (wsName) {
  const report = await api('GET', `/api/files/workspace/report/${encodeURIComponent(wsName)}`);
  check('report markdown served', report.status === 200 && (report.json.data?.content || '').length > 500,
    (report.json.data?.content || '').length);
  const optimizer = await api('GET', `/api/files/workspace/optimizer/${encodeURIComponent(wsName)}`);
  check('missing optimizer.md is 200+null (no 404 noise)', optimizer.status === 200 && optimizer.json.data === null,
    JSON.stringify(optimizer.json.data));
  const asset = await api('GET', `/api/files/workspace/asset/${encodeURIComponent(wsName)}/line_report/line_stability_report.html?token=${encodeURIComponent(token)}`, { auth: false, raw: true });
  check('report HTML asset served', asset.status === 200 && asset.text.length > 10000 && /<html/i.test(asset.text),
    `${asset.status} ${asset.text.length} bytes`);
}

const missing = await api('GET', '/api/diagnosis/snapshot/does-not-exist-xyz');
check('unknown run is 404', missing.status === 404, missing.status);

console.log(`\n[RESULT] failures=${failures}`);
process.exit(failures ? 1 : 0);
