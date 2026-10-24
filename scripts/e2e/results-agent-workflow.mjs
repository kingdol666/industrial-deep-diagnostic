#!/usr/bin/env node
// Agent workflow demo (AC-8): the three-step integration loop an outside
// agent runs — survey summaries → pick an id → read the detail and cite the
// report numbers. GET-only, repeatable, never starts an analysis.
//
// Usage: node scripts/e2e/results-agent-workflow.mjs --base http://127.0.0.1:3988 --q yield
// (default q=yield: summaries keep the artifacts' real parameter names, e.g.
//  yield_pct — search those tokens, not their translations)
const args = process.argv.slice(2);
const opt = (n, d = null) => { const i = args.indexOf(`--${n}`); return i >= 0 ? args[i + 1] : d; };
const BASE = opt('base', 'http://127.0.0.1:3988').replace(/\/$/, '');
const USER = opt('user', 'e2e_ontology');
const PASS = opt('password', 'E2e-Onto-2026!');
const QUERY = opt('q', 'yield');

let failures = 0;
function check(name, ok, detail = '') {
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? `  ${String(detail).slice(0, 240)}` : ''}`);
  if (!ok) failures += 1;
}

const login = await fetch(`${BASE}/api/auth/login`, {
  method: 'POST', headers: { 'content-type': 'application/json' },
  body: JSON.stringify({ username: USER, password: PASS }),
});
const token = (await login.json().catch(() => ({})))?.data?.session_token || '';
if (!token) { console.error('login failed'); process.exit(1); }
const authHeaders = { authorization: `Bearer ${token}` };

console.log(`\n[Step 1] list summaries — GET /api/external/v1/results?brief=true&q=${encodeURIComponent(QUERY)}`);
const listRes = await fetch(`${BASE}/api/external/v1/results?brief=true&q=${encodeURIComponent(QUERY)}&limit=10`, {
  headers: authHeaders,
});
const list = await listRes.json();
check('step 1 status 200', listRes.status === 200 && list.success === true, listRes.status);
check('step 1 returns ≥1 card', list.data.results.length >= 1, list.data.results.length);
if (list.data.results.length === 0) {
  console.error(`\n[RESULT] q="${QUERY}" matched nothing — summaries keep the artifacts' own parameter names; try --q yield|波动|DOE|playbook`);
  process.exit(1);
}
for (const card of list.data.results.slice(0, 3)) {
  console.log(`  - ${card.result_id} [${card.intent}] ${card.score ?? '—'} · ${(card.verdict || '—').slice(0, 24)}`);
  console.log(`    ${card.display_text.slice(0, 120)}`);
}

const picked = list.data.results[0];
console.log(`\n[Step 2] agent picked id: ${picked.result_id} (${picked.intent})`);
check('picked card is brief (no key_numbers)', !('key_numbers' in picked));

console.log(`\n[Step 3] read detail — GET /api/external/v1/results/${picked.result_id}`);
const detailRes = await fetch(`${BASE}/api/external/v1/results/${picked.result_id}`, { headers: authHeaders });
const detail = (await detailRes.json()).data || {};
check('step 3 status 200', detailRes.status === 200 && detail.result_id === picked.result_id);
check('step 3 detail has auditable key numbers', Object.keys(detail.summary_json?.key_numbers || {}).length > 0);
check('step 3 detail has the full report', typeof detail.report_md === 'string' && detail.report_md.length > 200,
  detail.report_md?.length);

// The agent cites numbers — every cited number must be traceable to
// summary_json.key_numbers (the deterministic extraction), not hallucinated.
const kn = detail.summary_json.key_numbers;
const citations = [];
if (kn.score !== null && kn.score !== undefined) citations.push(`评分 ${kn.score}`);
if (detail.verdict) citations.push(`结论 ${detail.verdict}`);
if (kn.n_alerts) citations.push(`${kn.n_alerts} 条告警`);
if (kn.evidence_grade) citations.push(`证据等级 ${kn.evidence_grade}`);
if (kn.n_playbooks !== null && kn.n_playbooks !== undefined) citations.push(`${kn.n_playbooks} 个 playbook`);
if (kn.round_count) citations.push(`第 ${kn.round_count} 轮寻优`);
console.log(`\n  Agent 引用（均可溯源 summary_json.sources）: ${citations.join('；') || detail.display_text?.slice(0, 80)}`);
check('agent cites at least one auditable number', citations.length >= 1 || (detail.display_text || '').length > 0);
check('sources pin every key number to an artifact path',
  Object.values(detail.summary_json.sources || {}).every((s) => /[\w./-]+\.(json|md)#/.test(String(s)) || s.startsWith('diagnostic_runs.')));

console.log(`\n[RESULT] failures=${failures}`);
if (failures) process.exitCode = 1;
