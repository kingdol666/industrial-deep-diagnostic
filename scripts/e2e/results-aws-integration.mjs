#!/usr/bin/env node
// AgentWorkShop (AWS) integration acceptance for the results library.
//
// Simulates the AWS-side agent exactly as it will integrate: authenticate with
// an `idd_` API TOKEN (not a session JWT), then
//   1. survey the flat result index,
//   2. fetch one result's detail by run id,
//   3. READ the actual files the detail points at — report.md full text, every
//      HTML report, and every artifact JSON — through the API, with no local
//      filesystem access,
//   4. verify the summary's key numbers are traceable to those artifacts.
//
// Usage: node scripts/e2e/results-aws-integration.mjs --base http://127.0.0.1:3210
const args = process.argv.slice(2);
const opt = (n, d = null) => { const i = args.indexOf(`--${n}`); return i >= 0 ? args[i + 1] : d; };
const BASE = opt('base', 'http://127.0.0.1:3210').replace(/\/$/, '');
const USER = opt('user', 'e2e_ontology');
const PASS = opt('password', 'E2e-Onto-2026!');

let passes = 0;
let failures = 0;
function check(name, ok, detail = '') {
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? `  ${String(detail).slice(0, 240)}` : ''}`);
  if (ok) passes += 1; else failures += 1;
  return ok;
}

// ── 1) AWS onboarding: session login ONCE, mint an API token, use it after ──
const login = await fetch(`${BASE}/api/auth/login`, {
  method: 'POST', headers: { 'content-type': 'application/json' },
  body: JSON.stringify({ username: USER, password: PASS }),
});
const sessionToken = (await login.json().catch(() => ({})))?.data?.session_token || '';
if (!sessionToken) { console.error('login failed'); process.exit(1); }

const tokenRes = await fetch(`${BASE}/api/auth/tokens`, {
  method: 'POST',
  headers: { 'content-type': 'application/json', authorization: `Bearer ${sessionToken}` },
  body: JSON.stringify({ name: `aws-e2e-${Date.now().toString(36)}`, expires_in_days: 1 }),
});
const tokenJson = await tokenRes.json().catch(() => ({}));
const AWS_TOKEN = tokenJson?.data?.token || '';
check('AWS onboarding: mint idd_ API token', tokenRes.status === 200 && /^idd_/.test(AWS_TOKEN), tokenJson?.data?.token_prefix);

// Every call below authenticates with the API TOKEN only — never the session.
async function api(path, { method = 'GET', body, headers = {} } = {}) {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: { 'content-type': 'application/json', authorization: `Bearer ${AWS_TOKEN}`, ...headers },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const contentType = res.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    return { status: res.status, json: await res.json().catch(() => ({})), contentType, bytes: null };
  }
  const buf = Buffer.from(await res.arrayBuffer());
  return { status: res.status, buffer: buf, contentType, bytes: buf.length };
}

// ── 2) Capability + index survey ──────────────────────────────────────────
const caps = await api('/api/external/v1/capabilities');
check('capabilities advertises results_index', caps.json?.data?.results_index === true);

const unauth = await fetch(`${BASE}/api/external/v1/results?limit=1`);
check('index rejects a token-less caller with 401', unauth.status === 401, unauth.status);

const idx = await api('/api/external/v1/results?limit=200');
check('API token authenticates the index', idx.status === 200 && idx.json?.success === true, idx.json?.data?.total);
const cards = idx.json?.data?.results || [];

// Token via query string (the path iframes/SSE use) — same auth contract.
const qTokenProbe = await fetch(`${BASE}/api/external/v1/results?limit=1&token=${encodeURIComponent(AWS_TOKEN)}`);
check('API token also works as ?token= (iframe/SSE fallback)', qTokenProbe.status === 200, qTokenProbe.status);

// ── helpers ──────────────────────────────────────────────────────────────
function evalJsonPath(doc, path) {
  // Supports a.b.c and a[0].b over the sources notation "file#a.b[0].c".
  const parts = path.replace(/\[(\d+)\]/g, '.$1').split('.').filter(Boolean);
  let cur = doc;
  for (const p of parts) {
    if (cur === null || cur === undefined) return undefined;
    cur = cur[p];
  }
  return cur;
}

function runNameOf(workspacePath) {
  if (!workspacePath) return null;
  const parts = String(workspacePath).split(/[/\\]/).filter(Boolean);
  return parts[parts.length - 1] || null;
}

// Asset URLs serve the RAW file (JSON artifacts included) — never an envelope.
async function readAsset(runName, relPath, { authHeader = true } = {}) {
  const url = `/api/files/workspace/asset/${encodeURIComponent(runName)}/${relPath}`;
  const res = await fetch(`${BASE}${url}${authHeader ? '' : `?token=${encodeURIComponent(AWS_TOKEN)}`}`, {
    headers: authHeader ? { authorization: `Bearer ${AWS_TOKEN}` } : {},
  });
  const buf = Buffer.from(await res.arrayBuffer());
  return { status: res.status, buffer: buf, contentType: res.headers.get('content-type') || '', bytes: buf.length };
}

// ── 3) Per-intent end-to-end: detail → read files → trace numbers ─────────
const PREFERRED = {
  'stability-report': '837404b0',
  'quick-screen': '46894aff',
  'doe-analysis': '19c1b216',
  'experience-mining': 'c2ef3526',
  'optimizer-campaign': 'a3cd1d7f',
  'deep-diagnosis': '5503f6c1',
};
const INTENTS = Object.keys(PREFERRED);
const summaryRows = [];

for (const intent of INTENTS) {
  const preferredId = PREFERRED[intent];
  const card = cards.find((c) => c.result_id === preferredId)
    || cards.find((c) => c.intent === intent && (c.has_report || c.has_html))
    || cards.find((c) => c.intent === intent);
  if (!card) {
    check(`${intent}: present in index`, false, 'no result visible for this principal');
    summaryRows.push({ intent, run: '—', score: '—', verdict: '—', report: '—', html: 0, artifacts: '0/0', ok: false });
    continue;
  }

  const detailRes = await api(`/api/external/v1/results/${encodeURIComponent(card.result_id)}?include_md=true`);
  const d = detailRes.json?.data || {};
  const meta = d.metadata || {};
  const runName = runNameOf(meta.workspace_path);
  let ok = true;

  ok = check(`${intent}: detail by run id (${card.result_id})`, detailRes.status === 200 && d.result_id === card.result_id && d.derived === false) && ok;
  ok = check(`${intent}: detail carries score/verdict/intent`, d.intent === intent && 'score' in d && 'verdict' in d, `${d.score} · ${d.verdict}`) && ok;
  ok = check(`${intent}: metadata.workspace_path + duration`, !!meta.workspace_path && meta.duration_ms !== undefined, meta.workspace_path) && ok;
  ok = check(`${intent}: metadata.report_md{path,bytes}`, !!meta.report_md?.path && meta.report_md.bytes > 0, `${meta.report_md?.bytes} B`) && ok;
  ok = check(`${intent}: metadata.html[] entries have path+bytes`, Array.isArray(meta.html) && meta.html.every((h) => h.path && h.bytes >= 0), `${meta.html?.length ?? 0} html`) && ok;

  // report.md full text rides in the detail…
  ok = check(`${intent}: report_md full text in detail`, typeof d.report_md === 'string' && d.report_md.length > 50, `${d.report_md?.length} chars`) && ok;

  // …and is READABLE through the API file endpoint (AWS agent has no disk).
  const reportUrlRes = await api(d.report_md_url);
  const reportContent = reportUrlRes.json?.data?.content;
  ok = check(`${intent}: report_md_url readable via API`, reportUrlRes.status === 200 && typeof reportContent === 'string' && reportContent.length > 50, `${reportUrlRes.status} / ${reportContent?.length} chars`) && ok;
  ok = check(`${intent}: API-read report matches the embedded text`, typeof reportContent === 'string' && reportContent === d.report_md) && ok;
  ok = check(`${intent}: API-read report bytes match metadata`, typeof reportContent === 'string'
    && Buffer.byteLength(reportContent, 'utf-8') === meta.report_md?.bytes, `${Buffer.byteLength(reportContent || '', 'utf-8')} vs ${meta.report_md?.bytes}`) && ok;

  // every HTML file the detail advertises must be readable + real HTML
  let htmlOk = 0;
  for (const h of (d.files?.html || [])) {
    const served = await api(h.url);
    const text = served.buffer?.toString('utf8') || '';
    const good = served.status === 200 && served.contentType.includes('text/html')
      && text.length > 500 && /<html[\s>]/i.test(text);
    if (good) htmlOk += 1;
    ok = check(`${intent}: HTML readable — ${h.path}`, good, `${served.status} ${served.bytes}B ${served.contentType}`) && ok;
  }
  if (!(d.files?.html || []).length) {
    ok = check(`${intent}: HTML list present (or legitimately empty)`, true, 'no html artifact for this run') && ok;
  }

  // every artifact path in metadata must be readable; JSONs must parse
  let artOk = 0;
  const arts = Array.isArray(meta.artifacts) ? meta.artifacts : [];
  for (const a of arts) {
    const served = await readAsset(runName, a.path);
    let good = served.status === 200 && served.bytes > 0;
    if (good && a.path.endsWith('.json')) {
      try { JSON.parse(served.buffer.toString('utf8')); } catch { good = false; }
    }
    if (good) artOk += 1;
    if (!good) ok = check(`${intent}: artifact readable — ${a.path}`, false, `${served.status} ${served.bytes}B`) && ok;
  }
  ok = check(`${intent}: all ${arts.length} artifacts readable via API`, artOk === arts.length, `${artOk}/${arts.length}`) && ok;

  // key numbers must trace to artifact fields (sources notation file#jsonpath)
  const kn = d.summary_json?.key_numbers || {};
  const sources = d.summary_json?.sources || {};
  let traced = 0;
  let traceChecked = 0;
  for (const [key, src] of Object.entries(sources)) {
    const [rel, jp] = String(src).split('#');
    if (!rel || !rel.endsWith('.json') || !jp) continue;
    const knValue = kn[key];
    if (knValue === undefined || (typeof knValue === 'object' && knValue !== null)) continue;
    traceChecked += 1;
    const served = await readAsset(runName, rel);
    if (served.status !== 200) continue;
    let doc;
    try { doc = JSON.parse(served.buffer.toString('utf8')); } catch { continue; }
    const actual = evalJsonPath(doc, jp);
    const match = Array.isArray(actual)
      ? (typeof knValue === 'number' && actual.length === knValue)
      : (actual === knValue || String(actual) === String(knValue));
    if (match) traced += 1;
    else check(`${intent}: source trace ${key}`, false, `${src} → ${JSON.stringify(actual)} vs ${JSON.stringify(knValue)}`);
  }
  ok = check(`${intent}: key numbers trace to artifacts`, traceChecked === 0 || traced === traceChecked, `${traced}/${traceChecked} traced`) && ok;

  summaryRows.push({
    intent,
    run: card.result_id,
    score: d.score ?? '—',
    verdict: d.verdict ?? '—',
    report: `${meta.report_md?.bytes ?? 0} B`,
    html: (d.files?.html || []).length,
    artifacts: `${artOk}/${arts.length}`,
    ok,
  });
}

// ── 4) include_md=false still yields readable pointers ────────────────────
const light = await api(`/api/external/v1/results/${encodeURIComponent(PREFERRED['stability-report'])}?include_md=false`);
check('include_md=false omits the body', light.json?.data?.report_md === null);
const lightRead = await api(light.json?.data?.report_md_url || '/x');
check('include_md=false report URL still readable', lightRead.status === 200 && (lightRead.json?.data?.content || '').length > 50);

// ── 5) token-only file read for an HTML report (iframe fallback path) ─────
const stabDetail = (await api(`/api/external/v1/results/${encodeURIComponent(PREFERRED['stability-report'])}?include_md=false`)).json?.data;
const firstHtml = stabDetail?.files?.html?.[0];
const viaQuery = firstHtml ? await readAsset(runNameOf(stabDetail.metadata.workspace_path), firstHtml.path, { authHeader: false }) : null;
check('HTML report readable with ?token= only (no auth header)', !!viaQuery && viaQuery.status === 200 && /<html[\s>]/i.test(viaQuery.buffer.toString('utf8')), viaQuery ? `${viaQuery.status} ${viaQuery.bytes}B` : 'no html');

// ── 6) hardcoded spot-checks on the known ground-truth run ────────────────
const gt = (await api(`/api/external/v1/results/${encodeURIComponent(PREFERRED['stability-report'])}?include_md=false`)).json?.data || {};
check('ground truth: 837404b0 score 65.8 / verdict C · 波动', gt.score === 65.8 && gt.verdict === 'C · 波动', `${gt.score} · ${gt.verdict}`);
check('ground truth: stability statement carries 343 SPC episodes + yield_pct',
  /343/.test(gt.summary_json?.conclusion || '') && /yield_pct/.test(gt.summary_json?.conclusion || ''));
check('ground truth: html list includes line_stability_report.html',
  (gt.files?.html || []).some((h) => h.path.includes('line_stability_report.html')));

// ── 7) user-field management through the API token ────────────────────────
const patch = await api(`/api/external/v1/results/${encodeURIComponent(PREFERRED['stability-report'])}`, {
  method: 'PATCH', body: { description: 'AWS 集成验收写入的描述', tags: ['aws-e2e'] },
});
check('PATCH via API token', patch.status === 200 && patch.json?.data?.description === 'AWS 集成验收写入的描述'
  && JSON.stringify(patch.json?.data?.tags) === JSON.stringify(['aws-e2e']));
const byTag = await api('/api/external/v1/results?tag=aws-e2e');
check('tag filter finds the tagged result', byTag.json?.data?.results?.some((r) => r.result_id === PREFERRED['stability-report']));
const restore = await api(`/api/external/v1/results/${encodeURIComponent(PREFERRED['stability-report'])}`, {
  method: 'PATCH', body: { description: null, tags: [] },
});
check('PATCH restore', restore.status === 200 && restore.json?.data?.description === null);
check('unknown result id → 404 RESULT_NOT_FOUND',
  (await api('/api/external/v1/results/nope')).json?.code === 'RESULT_NOT_FOUND');

// ── report table ─────────────────────────────────────────────────────────
console.log('\nIntent               | Run      | Score | Verdict      | Report   | HTML | Artifacts | OK');
console.log('---------------------+----------+-------+--------------+----------+------+-----------+----');
for (const r of summaryRows) {
  console.log(
    `${r.intent.padEnd(20)} | ${String(r.run).padEnd(8)} | ${String(r.score).padEnd(5)} | ${String(r.verdict).padEnd(12)} | ${String(r.report).padEnd(8)} | ${String(r.html).padEnd(4)} | ${String(r.artifacts).padEnd(9)} | ${r.ok ? '✓' : '✗'}`,
  );
}
console.log(`\n[RESULT] passes=${passes} failures=${failures}`);
if (failures) process.exitCode = 1;
