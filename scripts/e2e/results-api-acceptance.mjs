#!/usr/bin/env node
// Results-library API acceptance (plan 2026-10-25 §3, AC-3..AC-7 + console mirror).
// GET-heavy against a LIVE server with the real DB; the only mutations are a
// PATCH round-trip on one legacy NULL-owner result that is restored afterwards.
//
// Usage: node scripts/e2e/results-api-acceptance.mjs --base http://127.0.0.1:3988
const args = process.argv.slice(2);
const opt = (n, d = null) => { const i = args.indexOf(`--${n}`); return i >= 0 ? args[i + 1] : d; };
const BASE = opt('base', 'http://127.0.0.1:3988').replace(/\/$/, '');
const USER = opt('user', 'e2e_ontology');
const PASS = opt('password', 'E2e-Onto-2026!');

let failures = 0;
let passes = 0;
function check(name, ok, detail = '') {
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? `  ${String(detail).slice(0, 240)}` : ''}`);
  if (ok) passes += 1; else failures += 1;
}

let token = '';
async function api(method, path, body, { auth = true } = {}) {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: {
      'content-type': 'application/json',
      ...(auth && token ? { authorization: `Bearer ${token}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const json = await res.json().catch(() => ({}));
  return { status: res.status, json };
}

// ── auth ──
const login = await fetch(`${BASE}/api/auth/login`, {
  method: 'POST', headers: { 'content-type': 'application/json' },
  body: JSON.stringify({ username: USER, password: PASS }),
});
token = (await login.json().catch(() => ({})))?.data?.session_token || '';
check('login', login.status === 200 && !!token, login.status);

// ── AC-7: capabilities ──
const caps = await api('GET', '/api/external/v1/capabilities');
check('AC-7 capabilities.results_index = true',
  caps.status === 200 && caps.json.data?.results_index === true);
check('AC-7 capabilities lists results endpoints',
  Array.isArray(caps.json.data?.results_endpoints) && caps.json.data.results_endpoints.length === 3);

// ── AC-3: index + filters ──
const unauth = await api('GET', '/api/external/v1/results?limit=1', null, { auth: false });
check('AC-3 unauthenticated index → 401', unauth.status === 401, unauth.status);

const idx = await api('GET', '/api/external/v1/results?limit=200');
// Visibility scoping: a non-admin caller sees legacy NULL-owner rows plus
// their own — the dev DB holds rows owned by other e2e users, so the visible
// total legitimately sits slightly below the full backfill count (106).
check('AC-3 index returns success + total (≥90 visible to this principal)',
  idx.status === 200 && idx.json.success === true && idx.json.data.total >= 90, idx.json.data?.total);
const first = idx.json.data.results[0];
check('AC-3 card contract (result_id/title/display_text/intent/tags/has_report)',
  first && 'result_id' in first && 'title' in first && 'display_text' in first
  && 'intent' in first && Array.isArray(first.tags) && typeof first.has_report === 'boolean');
check('AC-3 card never carries report_md full text', !('report_md' in first) && !('metadata' in first));

// all six intents are represented in the backfilled library
const intentsSeen = new Set(idx.json.data.results.map((r) => r.intent));
const six = ['deep-diagnosis', 'stability-report', 'quick-screen', 'doe-analysis', 'experience-mining', 'optimizer-campaign'];
check('AC-2 all six intents present in the index', six.every((i) => intentsSeen.has(i)), [...intentsSeen].join(','));

const stab = idx.json.data.results.find((r) => r.intent === 'stability-report' && r.has_report);
check('a stability-report result with a report exists', !!stab, stab?.result_id);
// has_html is derived from the stored metadata — it must be truthful.
check('AC-3 has_html is truthful for the stability run (has line_stability_report.html)',
  typeof stab?.has_html === 'boolean' && stab.has_html === true, stab?.has_html);

// q filter: the stability statement mentions 波动/参数 — search by a rare scene token instead
const qHit = await api('GET', '/api/external/v1/results?q=accept_api&intent=stability-report');
check('AC-3 q + intent filter narrows to the accept_api stability run',
  qHit.status === 200 && qHit.json.data.results.every((r) => r.intent === 'stability-report')
  && qHit.json.data.results.some((r) => /accept_api/.test(`${r.title} ${r.scene} ${r.display_text}`)),
  `${qHit.json.data.results.length} hits`);

// tag filter (after the PATCH round-trip below it must still match exactly)
const tagMiss = await api('GET', '/api/external/v1/results?tag=reslib_e2e_tag');
check('AC-3 tag filter misses before tagging', tagMiss.json.data.results.every((r) => !(r.tags || []).includes('reslib_e2e_tag')));

// min_score
const hi = await api('GET', '/api/external/v1/results?min_score=90&limit=200');
check('AC-3 min_score=90 excludes a 65.8 stability result',
  hi.status === 200 && hi.json.data.results.every((r) => r.score === null || r.score >= 90));

// sort score_desc → first non-null scores are the largest
const sorted = await api('GET', '/api/external/v1/results?sort=score_desc&limit=200');
const scores = sorted.json.data.results.map((r) => r.score).filter((s) => s !== null);
check('AC-3 sort=score_desc is monotonic non-increasing',
  scores.every((s, i) => i === 0 || scores[i - 1] >= s), scores.slice(0, 5).join(','));

// invalid params
const badIntent = await api('GET', '/api/external/v1/results?intent=nope');
check('AC-3 invalid intent → 400 RESULTS_QUERY_INVALID',
  badIntent.status === 400 && badIntent.json.code === 'RESULTS_QUERY_INVALID');
const badSort = await api('GET', '/api/external/v1/results?sort=rand');
check('AC-3 invalid sort → 400', badSort.status === 400 && badSort.json.code === 'RESULTS_QUERY_INVALID');

// brief mode
const brief = await api('GET', '/api/external/v1/results?brief=true&intent=stability-report&limit=5');
const briefCard = brief.json.data.results[0];
check('AC-3 brief drops key_numbers and caps display_text ≤161',
  briefCard && !('key_numbers' in briefCard) && briefCard.display_text.length <= 161,
  briefCard?.display_text?.length);
const briefBytes = JSON.stringify(brief.json.data.results[0]).length;
check('AC-3 brief card ≤ ~600 chars', briefBytes <= 700, briefBytes);

// paging
const page1 = await api('GET', '/api/external/v1/results?limit=2&offset=0&sort=created_desc');
const page2 = await api('GET', '/api/external/v1/results?limit=2&offset=2&sort=created_desc');
check('AC-3 paging: offset shifts the window',
  page1.json.data.results.length === 2 && page2.json.data.results.length === 2
  && page1.json.data.results[0].result_id !== page2.json.data.results[0].result_id);

// ── AC-4: detail ──
const detail = await api('GET', `/api/external/v1/results/${stab.result_id}`);
const d = detail.json.data || {};
check('AC-4 detail returns the full contract',
  detail.status === 200 && d.result_id === stab.result_id && d.derived === false);
check('AC-4 detail carries summary_json.key_numbers + sources',
  d.summary_json?.key_numbers && d.summary_json?.sources && Object.keys(d.summary_json.sources).length > 0);
check('AC-4 detail carries metadata.report_md{path,bytes}',
  d.metadata?.report_md?.path && d.metadata.report_md.bytes > 0, d.metadata?.report_md?.bytes);
check('AC-4 detail report_md is the full text', typeof d.report_md === 'string' && d.report_md.length > 500, d.report_md?.length);
check('AC-4 detail files.html entries have urls',
  Array.isArray(d.files?.html) && d.files.html.every((h) => h.url?.startsWith('/api/files/workspace/asset/')));
check('AC-4 detail run block', d.run?.run_id === stab.result_id && typeof d.run?.session_resumable === 'boolean');

const noMd = await api('GET', `/api/external/v1/results/${stab.result_id}?include_md=false`);
check('AC-4 include_md=false omits the body but keeps the url',
  noMd.json.data.report_md === null && !!noMd.json.data.report_md_url);

const notFound = await api('GET', '/api/external/v1/results/no_such_result');
check('AC-4 unknown id → 404 RESULT_NOT_FOUND',
  notFound.status === 404 && notFound.json.code === 'RESULT_NOT_FOUND');

// console mirror parity
const mirror = await api('GET', `/api/results/${stab.result_id}`);
check('console mirror /api/results/:id matches the external detail',
  mirror.status === 200 && mirror.json.data.result_id === stab.result_id
  && mirror.json.data.score === d.score && mirror.json.data.verdict === d.verdict);

// ── AC-5: PATCH round-trip (restores everything afterwards) ──
const patch = await api('PATCH', `/api/external/v1/results/${stab.result_id}`, {
  description: 'e2e 验收描述：演示 PATCH 可编辑描述',
  tags: ['reslib_e2e_tag', '验收'],
});
check('AC-5 PATCH description+tags → 200 with updated card',
  patch.status === 200 && patch.json.data.description === 'e2e 验收描述：演示 PATCH 可编辑描述'
  && JSON.stringify(patch.json.data.tags) === JSON.stringify(['reslib_e2e_tag', '验收']));

const afterPatchList = await api('GET', '/api/external/v1/results?tag=reslib_e2e_tag');
check('AC-5 patched description wins display_text and tag filter hits',
  afterPatchList.json.data.results.some((r) => r.result_id === stab.result_id
    && r.display_text === 'e2e 验收描述：演示 PATCH 可编辑描述'));
const qDesc = await api('GET', '/api/external/v1/results?q=演示 PATCH 可编辑描述');
check('AC-5 q search matches the edited description',
  qDesc.json.data.results.some((r) => r.result_id === stab.result_id));

const patchSummary = await api('PATCH', `/api/external/v1/results/${stab.result_id}`, { summary: 'hacked' });
check('AC-5 PATCH summary → 400 SUMMARY_READONLY',
  patchSummary.status === 400 && patchSummary.json.code === 'SUMMARY_READONLY');
const patchBad = await api('PATCH', `/api/external/v1/results/${stab.result_id}`, { description: 'x'.repeat(2001) });
check('AC-5 PATCH oversized description → 400', patchBad.status === 400 && patchBad.json.code === 'RESULT_PATCH_INVALID');
const patchNone = await api('PATCH', `/api/external/v1/results/${stab.result_id}`, {});
check('AC-5 PATCH empty body → 400', patchNone.status === 400);
const patchMissing = await api('PATCH', '/api/external/v1/results/no_such_result', { description: 'x' });
check('AC-5 PATCH unknown id → 404 RESULT_NOT_FOUND',
  patchMissing.status === 404 && patchMissing.json.code === 'RESULT_NOT_FOUND');

// restore the pre-test state
const restore = await api('PATCH', `/api/external/v1/results/${stab.result_id}`, { description: null, tags: [] });
check('PATCH restore returns the card to a clean state',
  restore.status === 200 && restore.json.data.description === null
  && JSON.stringify(restore.json.data.tags) === '[]');
const postRestore = await api('GET', `/api/external/v1/results/${stab.result_id}`);
check('restored summary is intact (user edits did not touch the auto summary)',
  postRestore.json.data.summary.length > 20);

console.log(`\n[RESULT] passes=${passes} failures=${failures}`);
process.exit(failures ? 1 : 0);
