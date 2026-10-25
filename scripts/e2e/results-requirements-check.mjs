#!/usr/bin/env node
// Requirement-level acceptance for the analysis-results management feature.
// Maps 1:1 to the user's stated requirements:
//   R1 对分析结果的分类        — create category, assign to a result, filter by it, unassign
//   R2 查看全部的描述          — every visible result carries a readable display_text;
//                                description overrides the auto summary
//   R3 根据 id 查看元信息      — metadata: workspace/report{path,bytes}/html[]/artifacts/duration/engine
//   R4 查看详细的报告          — report.md full text + report URL + HTML reports all READABLE
//
// Uses an idd_ API token (the AWS integration path). Mutations are restored.
// Usage: node scripts/e2e/results-requirements-check.mjs --base http://127.0.0.1:3210
const args = process.argv.slice(2);
const opt = (n, d = null) => { const i = args.indexOf(`--${n}`); return i >= 0 ? args[i + 1] : d; };
const BASE = opt('base', 'http://127.0.0.1:3210').replace(/\/$/, '');
const USER = opt('user', 'e2e_ontology');
const PASS = opt('password', 'E2e-Onto-2026!');

let passes = 0;
let failures = 0;
const requirement = { R1: [], R2: [], R3: [], R4: [] };
function check(req, name, ok, detail = '') {
  console.log(`${ok ? 'PASS' : 'FAIL'}  [${req}] ${name}${detail ? `  ${String(detail).slice(0, 220)}` : ''}`);
  if (ok) { passes += 1; requirement[req].push(true); } else { failures += 1; requirement[req].push(false); }
  return ok;
}

// ── auth: mint an API token (AWS path) ──
const login = await fetch(`${BASE}/api/auth/login`, {
  method: 'POST', headers: { 'content-type': 'application/json' },
  body: JSON.stringify({ username: USER, password: PASS }),
});
const sessionToken = (await login.json().catch(() => ({})))?.data?.session_token || '';
if (!sessionToken) { console.error('login failed'); process.exit(1); }
const tokenRes = await fetch(`${BASE}/api/auth/tokens`, {
  method: 'POST', headers: { 'content-type': 'application/json', authorization: `Bearer ${sessionToken}` },
  body: JSON.stringify({ name: `req-check-${Date.now().toString(36)}`, expires_in_days: 1 }),
});
const API_TOKEN = (await tokenRes.json())?.data?.token || '';
if (!API_TOKEN) { console.error('token mint failed'); process.exit(1); }

async function api(path, { method = 'GET', body } = {}) {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: { 'content-type': 'application/json', authorization: `Bearer ${API_TOKEN}` },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  let json = null;
  try { json = await res.json(); } catch { /* file body */ }
  return { status: res.status, json };
}

// Console route returns `data` as the card ARRAY (external nests under
// data.results) — normalise once so assertions cannot read the wrong shape.
async function listConsole(params) {
  const r = await api(`/api/results?${params}`);
  return {
    status: r.status,
    results: Array.isArray(r.json?.data) ? r.json.data : [],
    total: r.json?.total ?? 0,
  };
}

async function readFileUrl(url) {
  if (!url) return { status: 0, bytes: 0, text: '' };
  const res = await fetch(`${BASE}${url}`, { headers: { authorization: `Bearer ${API_TOKEN}` } });
  const text = await res.text();
  return { status: res.status, bytes: Buffer.byteLength(text, 'utf-8'), text, contentType: res.headers.get('content-type') || '' };
}

const GT = '837404b0'; // ground-truth stability run (65.8 / C · 波动)

// ═══ R1 对分析结果的分类 ═══════════════════════════════════════════════════
console.log('\n── R1 对分析结果的分类 ──────────────────────────────────────────');
const cats = await api('/api/history/categories');
check('R1', '分类列表可读（run_categories）', cats.status === 200 && Array.isArray(cats.json?.data),
  `${cats.json?.data?.length ?? 0} categories`);

const catName = `需求验收-${Date.now().toString(36)}`;
const created = await api('/api/history/categories', { method: 'POST', body: { name: catName } });
const catId = created.json?.data?.id;
check('R1', '创建分类（POST /api/history/categories）', created.status === 201 && !!catId, `${catName} → ${catId}`);

const assigned = await api(`/api/results/${GT}`, { method: 'PATCH', body: { category_id: catId } });
check('R1', '给分析结果指派分类（PATCH /api/results/:id category_id）',
  assigned.status === 200 && assigned.json?.data?.category_id === catId, assigned.json?.data?.category_id);

const listByCat = await listConsole(`category_id=${encodeURIComponent(catId)}&limit=50`);
const catCards = listByCat.results;
check('R1', '按分类筛选结果（GET /api/results?category_id=…）',
  listByCat.status === 200 && catCards.length >= 1 && catCards.every((c) => c.category_id === catId),
  `${catCards.length} results`);
check('R1', '结果卡片带分类字段', catCards.some((c) => c.result_id === GT && c.category_id === catId));

const detailCat = await api(`/api/results/${GT}?include_md=false`);
check('R1', '详情返回分类', detailCat.json?.data?.category_id === catId);
check('R1', '结果库外部路由同样支持分类筛选',
  (await api(`/api/external/v1/results?category_id=${encodeURIComponent(catId)}`)).json?.data?.results?.some((c) => c.result_id === GT));

// ═══ R2 查看全部的描述 ════════════════════════════════════════════════════
console.log('\n── R2 查看全部的描述 ───────────────────────────────────────────');
const all = [];
for (let offset = 0; offset < 400; offset += 200) {
  const page = await listConsole(`limit=200&offset=${offset}`);
  all.push(...page.results);
  if (page.results.length < 200) break;
}
check('R2', '索引可分页取回全部结果', all.length >= 90, `${all.length} results`);
const emptyText = all.filter((r) => !r.display_text || !r.display_text.trim());
check('R2', '每条结果都有可读的描述/摘要（display_text 非空）', emptyText.length === 0,
  emptyText.length ? `${emptyText.length} empty: ${emptyText.slice(0, 3).map((r) => r.result_id).join(',')}` : '0 empty');
check('R2', '卡片同时暴露 description 与派生的 display_text',
  all.every((r) => (r.description === null || typeof r.description === 'string') && typeof r.display_text === 'string'));

const autoSummary = all.find((r) => r.result_id === GT)?.display_text || '';
const descText = `需求验收描述-${Date.now().toString(36)}`;
await api(`/api/results/${GT}`, { method: 'PATCH', body: { description: descText } });
const afterDesc = (await listConsole(`q=${encodeURIComponent(descText)}`)).results;
check('R2', '编辑描述后索引即可按描述检索到（display_text = description）',
  afterDesc.length === 1 && afterDesc[0].result_id === GT && afterDesc[0].display_text === descText);
// clear the description again → the card must fall back to the auto summary
await api(`/api/results/${GT}`, { method: 'PATCH', body: { description: null } });
const byScene = (await listConsole(`q=${encodeURIComponent(GT)}`)).results;
check('R2', '清除描述后回落到自动摘要（display_text = summary）',
  byScene.length === 1 && byScene[0].description === null
  && byScene[0].display_text === autoSummary && autoSummary.length > 20,
  `auto: ${autoSummary.slice(0, 60)}…`);

// ═══ R3 根据 id 查看元信息 ════════════════════════════════════════════════
console.log('\n── R3 根据 id 查看元信息 ───────────────────────────────────────');
const det = (await api(`/api/results/${GT}?include_md=false`)).json?.data || {};
const meta = det.metadata || {};
check('R3', '按 id 取详情（GET /api/results/:id）', det.result_id === GT && det.derived === false);
check('R3', '元信息：workspace_path', !!meta.workspace_path, meta.workspace_path);
check('R3', '元信息：report_md{path,bytes}', !!meta.report_md?.path && meta.report_md.bytes > 0, `${meta.report_md?.bytes} B`);
check('R3', '元信息：HTML 报告清单', Array.isArray(meta.html) && meta.html.length >= 1
  && meta.html.every((h) => h.path && h.bytes > 0), meta.html?.map((h) => h.path).join(','));
check('R3', '元信息：工件清单（kind/path/bytes）', Array.isArray(meta.artifacts) && meta.artifacts.length >= 3,
  `${meta.artifacts?.length} artifacts`);
check('R3', '元信息：时长/引擎/数据指纹',
  typeof meta.duration_ms === 'number' && !!meta.engine && !!meta.data_fingerprint,
  `${Math.round((meta.duration_ms || 0) / 1000)}s · ${meta.engine} · ${String(meta.data_fingerprint).slice(0, 20)}…`);
check('R3', '元信息：运行态（status / session_resumable）',
  det.run?.run_id === GT && typeof det.run?.session_resumable === 'boolean', JSON.stringify(det.run));
check('R3', '详情内联 summary_json（评分/结论/溯源）',
  det.summary_json?.key_numbers?.score === 65.8 && det.verdict === 'C · 波动'
  && Object.keys(det.summary_json?.sources || {}).length >= 3);

// metadata must be SELF-VERIFYING: every advertised path is readable via API
let readable = 0;
for (const h of (det.files?.html || [])) {
  const r = await readFileUrl(h.url);
  if (r.status === 200 && r.text.length > 500) readable += 1;
}
check('R3', '元信息中的 HTML 路径全部可直读（内容 >500 字符）',
  readable === (det.files?.html || []).length && readable >= 1, `${readable}/${det.files?.html?.length ?? 0}`);

const runName = String(meta.workspace_path).split(/[/\\]/).filter(Boolean).pop();
let artReadable = 0;
for (const a of meta.artifacts || []) {
  const url = `/api/files/workspace/asset/${encodeURIComponent(runName)}/${a.path}`;
  const res = await fetch(`${BASE}${url}`, { headers: { authorization: `Bearer ${API_TOKEN}` } });
  if (res.status === 200 && (await res.arrayBuffer()).byteLength > 0) artReadable += 1;
}
check('R3', '元信息中的工件路径全部可直读', artReadable === (meta.artifacts || []).length && artReadable >= 3,
  `${artReadable}/${meta.artifacts?.length ?? 0}`);

// ═══ R4 查看详细的报告 ════════════════════════════════════════════════════
console.log('\n── R4 查看详细的报告 ───────────────────────────────────────────');
const full = (await api(`/api/results/${GT}?include_md=true`)).json?.data || {};
check('R4', '详情携带 report.md 全文', typeof full.report_md === 'string' && full.report_md.length > 5000,
  `${full.report_md?.length} chars`);
check('R4', '报告全文与磁盘字节一致', Buffer.byteLength(full.report_md || '', 'utf-8') === meta.report_md?.bytes,
  `${Buffer.byteLength(full.report_md || '', 'utf-8')} vs ${meta.report_md?.bytes}`);
const reportJson = await api(full.report_md_url);
check('R4', 'report_md_url 返回 JSON 信封 {name,content} 且内容与内联全文一致',
  reportJson.status === 200
  && typeof reportJson.json?.data?.content === 'string'
  && reportJson.json.data.content === full.report_md,
  `${reportJson.status} / ${reportJson.json?.data?.content?.length} chars`);
const htmlEntry = (full.files?.html || []).find((h) => h.path.includes('line_stability_report.html')) || (full.files?.html || [])[0];
const htmlRead = await readFileUrl(htmlEntry?.url);
check('R4', 'HTML 报告可直读并渲染（text/html + <html>）',
  htmlRead.status === 200 && htmlRead.contentType.includes('text/html') && /<html[\s>]/i.test(htmlRead.text),
  `${htmlRead.status} ${htmlRead.contentType} ${htmlRead.bytes}B`);
check('R4', '报告渲染内容包含真实结论（稳定性报告标题/评分）',
  /产线|稳定性|65\.8/.test(htmlRead.text) && /产线|稳定性/.test(full.report_md || ''));

// ═══ restore ══════════════════════════════════════════════════════════════
await api(`/api/results/${GT}`, { method: 'PATCH', body: { description: null, category_id: null } });
await api(`/api/history/categories/${encodeURIComponent(catId)}`, { method: 'DELETE' });
const restored = (await api(`/api/results/${GT}?include_md=false`)).json?.data || {};
check('R1', '验收后恢复原状（描述 null、分类 null）',
  restored.description === null && restored.category_id === null);

// ═══ requirement summary ══════════════════════════════════════════════════
console.log('\nRequirement | Checks | Result');
console.log('------------+--------+--------');
for (const [key, label] of [['R1', '对分析结果的分类'], ['R2', '查看全部的描述'], ['R3', '按 id 查看元信息'], ['R4', '查看详细报告']]) {
  const list = requirement[key];
  console.log(`${label.padEnd(11)} | ${String(list.length).padStart(6)} | ${list.every(Boolean) ? '✓ 全部通过' : '✗ 存在失败'}`);
}
console.log(`\n[RESULT] passes=${passes} failures=${failures}`);
if (failures) process.exitCode = 1;
