// Token-guard security probe (43-check auth matrix).
// No credential literals anywhere: probe users/passwords/tokens are generated
// at runtime and cleaned up (probe token rows deleted; probe results reset).
// Matrix: public whitelist / token-less 401 / malformed creds / 3 valid channels /
// token lifecycle (expiry, revoke, tamper, forgery, cross-user revoke) / external job loop.
//
// Usage: node scripts/e2e/token-guard-probe.mjs --base http://127.0.0.1:3210
// (reads data/.auth-jwt-secret locally to forge expired/wrong-signature JWTs —
//  no secret value ever leaves the machine or appears in output)
import crypto from 'node:crypto';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { createRequire } from 'node:module';

const args = process.argv.slice(2);
const opt = (n, d = null) => { const i = args.indexOf(`--${n}`); return i >= 0 ? args[i + 1] : d; };
const BASE = opt('base', 'http://127.0.0.1:3210').replace(/\/$/, '');
const require2 = createRequire(join(process.cwd(), 'app', 'backend', 'package.json'));
const Database = require2('better-sqlite3');

let failures = 0;
function check(name, ok, detail = '') {
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? `  ${String(detail).slice(0, 200)}` : ''}`);
  if (!ok) failures += 1;
}
const j = (r) => r.json();

async function call(path, { method = 'GET', headers = {}, body, token } = {}) {
  const h = { ...headers };
  if (token !== undefined) h.authorization = token;
  if (body !== undefined) h['content-type'] = 'application/json';
  const res = await fetch(`${BASE}${path}`, {
    method, headers: h, body: body === undefined ? undefined : JSON.stringify(body),
  });
  let json = null;
  try { json = await res.json(); } catch { /* non-json */ }
  return { status: res.status, json, headers: res.headers };
}

const rand = crypto.randomBytes(4).toString('hex');
const PASS_A = `Sec-${rand}-aB3`;
const userA = `secprobe_a_${rand}`;
const userB = `secprobe_b_${rand}`;

// ── 1. public whitelist ─────────────────────────────────────────────────────
const health = await call('/api/health');
check('[1] GET /api/health open without token', health.status === 200, health.status);
const badLogin = await call('/api/auth/login', { method: 'POST', body: { username: userA, password: 'WrongPass-123' } });
check('[1] login wrong password → 401 AUTH_INVALID_CREDENTIALS',
  badLogin.status === 401 && badLogin.json?.code === 'AUTH_INVALID_CREDENTIALS', `${badLogin.status} ${badLogin.json?.code}`);
const badReg = await call('/api/auth/register', { method: 'POST', body: { username: 'x', password: 'Abcdef12' } });
check('[1] register invalid username → 400 VALIDATION_ERROR',
  badReg.status === 400 && badReg.json?.code === 'VALIDATION_ERROR', `${badReg.status} ${badReg.json?.code}`);

// ── 2. token-less interception across every surface ────────────────────────
const protectedPaths = [
  ['/api/results', 'console results index'],
  ['/api/results/categories', 'console categories'],
  ['/api/external/v1/results', 'external results index'],
  ['/api/external/v1/capabilities', 'external capabilities'],
  ['/api/external/v1/results/nonexistent-id', 'external result detail'],
  ['/api/auth/tokens', 'token management'],
  ['/api/diagnosis/snapshot/no-such-run', 'diagnosis snapshot'],
  ['/api/definitely-not-a-route', 'unknown /api path (guard is global)'],
];
let all401 = true;
for (const [p] of protectedPaths) {
  const r = await call(p);
  const ok = r.status === 401 && r.json?.code === 'AUTH_REQUIRED';
  if (!ok) all401 = false;
  check(`[2] token-less ${p} → 401 AUTH_REQUIRED`, ok, `${r.status} ${r.json?.code ?? ''}`);
}
check('[2] ALL protected surfaces reject token-less callers', all401);

// ── 3. malformed / wrong-scheme credentials ────────────────────────────────
const malformed = [
  ['Bearer  (empty token)', { authorization: 'Bearer ' }],
  ['Bearer   (whitespace only)', { authorization: 'Bearer    ' }],
  ['Basic scheme', { authorization: 'Basic dXNlcjpwYXNz' }],
  ['no scheme at all', { authorization: 'garbage-no-scheme' }],
  ['Bearer bogus-token', { authorization: 'Bearer bogus-token-123' }],
];
for (const [label, h] of malformed) {
  const r = await call('/api/results', { headers: h });
  const code = r.json?.code;
  check(`[3] ${label} → 401 (${code})`, r.status === 401, `${r.status} ${code}`);
}
const viaXApi = await call('/api/results', { headers: { 'x-api-token': 'idd_totally_bogus' } });
check('[3] x-api-token bogus → 401 AUTH_INVALID', viaXApi.status === 401 && viaXApi.json?.code === 'AUTH_INVALID', `${viaXApi.status} ${viaXApi.json?.code}`);
const viaQuery = await call('/api/results?token=idd_totally_bogus');
check('[3] ?token= bogus → 401 AUTH_INVALID', viaQuery.status === 401 && viaQuery.json?.code === 'AUTH_INVALID', `${viaQuery.status} ${viaQuery.json?.code}`);

// ── 4. valid credentials: three channels, two credential kinds ─────────────
const regA = await call('/api/auth/register', { method: 'POST', body: { username: userA, password: PASS_A } });
check('[4] register user A → 200 + session JWT', regA.status === 200 && !!regA.json?.data?.session_token, regA.status);
const jwtA = regA.json?.data?.session_token;
const regB = await call('/api/auth/register', { method: 'POST', body: { username: userB, password: `Sec-${rand}-bB4` } });
check('[4] register user B (for cross-user revoke test)', regB.status === 200, regB.status);

const mint = await call('/api/auth/tokens', { method: 'POST', headers: { authorization: `Bearer ${jwtA}` }, body: { name: `secprobe-${rand}` } });
check('[4] POST /auth/tokens mints idd_ token (plaintext once)', mint.status === 200 && String(mint.json?.data?.token || '').startsWith('idd_'), `${mint.status} prefix=${String(mint.json?.data?.token || '').slice(0, 4)}`);
const tok1 = mint.json?.data?.token;
const tok1Id = mint.json?.data?.id;
const mintBadTtl = await call('/api/auth/tokens', { method: 'POST', headers: { authorization: `Bearer ${jwtA}` }, body: { name: 'bad-ttl', expires_in_days: 400 } });
check('[4] expires_in_days=400 (>365) → 400 VALIDATION_ERROR', mintBadTtl.status === 400 && mintBadTtl.json?.code === 'VALIDATION_ERROR', `${mintBadTtl.status} ${mintBadTtl.json?.code}`);
const mintNoName = await call('/api/auth/tokens', { method: 'POST', headers: { authorization: `Bearer ${jwtA}` }, body: {} });
check('[4] token without name → 400 VALIDATION_ERROR', mintNoName.status === 400, `${mintNoName.status} ${mintNoName.json?.code}`);

const mint2 = await call('/api/auth/tokens', { method: 'POST', headers: { authorization: `Bearer ${jwtA}` }, body: { name: `secprobe-exp-${rand}`, expires_in_days: 1 } });
const tok2 = mint2.json?.data?.token;
const tok2Id = mint2.json?.data?.id;

const caps = await call('/api/external/v1/capabilities', { headers: { authorization: `Bearer ${tok1}` } });
check('[4] Bearer idd_ token → 200 capabilities with results_index',
  caps.status === 200 && caps.json?.data?.results_index === true, `${caps.status} results_index=${caps.json?.data?.results_index}`);
const viaXOk = await call('/api/results', { headers: { 'x-api-token': tok1 } });
check('[4] x-api-token channel → 200', viaXOk.status === 200 && viaXOk.json?.success === true, viaXOk.status);
const viaQOk = await call(`/api/results?token=${encodeURIComponent(tok1)}`);
check('[4] ?token= query channel → 200', viaQOk.status === 200 && viaQOk.json?.success === true, viaQOk.status);
const jwtIdx = await call('/api/results', { headers: { authorization: `Bearer ${jwtA}` } });
check('[4] login-JWT session channel → 200', jwtIdx.status === 200 && jwtIdx.json?.success === true, jwtIdx.status);
const tokList = await call('/api/auth/tokens', { headers: { authorization: `Bearer ${tok1}` } });
check('[4] idd_ token can manage tokens (owner scope)', tokList.status === 200 && Array.isArray(tokList.json?.data), tokList.status);

// ── 5. lifecycle: expiry / revoke / tamper / forgery / cross-user ──────────
// force-expire tok2 via direct DB write (WAL, busy-timed), then expect AUTH_TOKEN_EXPIRED
const db = new Database(join(process.cwd(), 'data', 'diagnostic.db'));
db.pragma('busy_timeout = 5000');
db.prepare('UPDATE api_tokens SET expires_at = ? WHERE id = ?').run(new Date(Date.now() - 60_000).toISOString(), tok2Id);
db.close();
const expired = await call('/api/external/v1/results', { headers: { authorization: `Bearer ${tok2}` } });
check('[5] expired API token → 401 AUTH_TOKEN_EXPIRED',
  expired.status === 401 && expired.json?.code === 'AUTH_TOKEN_EXPIRED', `${expired.status} ${expired.json?.code}`);

const tampered = await call('/api/external/v1/results', { headers: { authorization: `Bearer ${tok1}x` } });
check('[5] tampered token (append char) → 401 AUTH_INVALID',
  tampered.status === 401 && tampered.json?.code === 'AUTH_INVALID', `${tampered.status} ${tampered.json?.code}`);
const truncated = await call('/api/external/v1/results', { headers: { authorization: `Bearer ${tok1.slice(0, 20)}` } });
check('[5] truncated token → 401 AUTH_INVALID',
  truncated.status === 401 && truncated.json?.code === 'AUTH_INVALID', `${truncated.status} ${truncated.json?.code}`);

// forge JWTs locally using the server's real secret file (read-only) — expiry must be enforced
const secret = readFileSync(join(process.cwd(), 'data', '.auth-jwt-secret'), 'utf-8').trim();
const b64u = (o) => Buffer.from(JSON.stringify(o)).toString('base64url');
const sign = (payload, secretKey) => {
  const header = b64u({ alg: 'HS256', typ: 'JWT' });
  const body = b64u(payload);
  const sig = crypto.createHmac('sha256', secretKey).update(`${header}.${body}`).digest('base64url');
  return `${header}.${body}.${sig}`;
};
const forgedExpired = sign({ sub: 1, username: 'admin', role: 'admin', type: 'session', iat: 1e6, exp: Math.floor(Date.now() / 1000) - 3600 }, secret);
const rFe = await call('/api/results', { headers: { authorization: `Bearer ${forgedExpired}` } });
check('[5] forged VALID-signature but EXPIRED session JWT → 401 AUTH_TOKEN_EXPIRED',
  rFe.status === 401 && rFe.json?.code === 'AUTH_TOKEN_EXPIRED', `${rFe.status} ${rFe.json?.code}`);
const forgedSig = sign({ sub: 1, username: 'admin', role: 'admin', type: 'session', exp: Math.floor(Date.now() / 1000) + 3600 }, 'wrong-secret-entirely');
const rFs = await call('/api/results', { headers: { authorization: `Bearer ${forgedSig}` } });
check('[5] forged JWT with WRONG signature (claims admin) → 401',
  rFs.status === 401, `${rFs.status} ${rFs.json?.code}`);

const foreignMint = regB.json?.data?.session_token;
const foreignTok = await call('/api/auth/tokens', { method: 'POST', headers: { authorization: `Bearer ${foreignMint}` }, body: { name: `secprobe-foreign-${rand}` } });
const crossRevoke = await call(`/api/auth/tokens/${foreignTok.json?.data?.id}`, { method: 'DELETE', headers: { authorization: `Bearer ${jwtA}` } });
check('[5] user A revoking user B token → 403 FORBIDDEN',
  crossRevoke.status === 403 && crossRevoke.json?.code === 'FORBIDDEN', `${crossRevoke.status} ${crossRevoke.json?.code}`);

const revoke = await call(`/api/auth/tokens/${tok1Id}`, { method: 'DELETE', headers: { authorization: `Bearer ${jwtA}` } });
check('[5] owner revokes own token → 200', revoke.status === 200 && revoke.json?.data?.revoked === true, revoke.status);
const revokedUse = await call('/api/external/v1/results', { headers: { authorization: `Bearer ${tok1}` } });
check('[5] revoked token reuse → 401 AUTH_TOKEN_REVOKED',
  revokedUse.status === 401 && revokedUse.json?.code === 'AUTH_TOKEN_REVOKED', `${revokedUse.status} ${revokedUse.json?.code}`);

// ── 6. external job + other operations with a FRESH valid token ────────────
const mint3 = await call('/api/auth/tokens', { method: 'POST', headers: { authorization: `Bearer ${jwtA}` }, body: { name: `secprobe-job-${rand}` } });
const tok3 = mint3.json?.data?.token;
const launch = await call('/api/external/v1/analyze', {
  method: 'POST',
  headers: { authorization: `Bearer ${tok3}` },
  body: { harness: 'mock', analysisIntent: 'deep-diagnosis', dataPath: 'data/smoke.csv', sceneName: `secprobe_${rand}`, question: 'token guard acceptance probe' },
});
const taskId = launch.json?.data?.task_id;
const runId = launch.json?.data?.run_id;
check('[6] POST /v1/analyze with idd_ token → 202 + task/run id', launch.status === 202 && !!runId, `${launch.status} ${taskId}/${runId}`);
let status = null;
for (let i = 0; i < 120; i += 1) {
  const t = await call(`/api/external/v1/tasks/${taskId}`, { headers: { authorization: `Bearer ${tok3}` } });
  status = t.json?.data?.status;
  if (['completed', 'failed', 'stopped'].includes(status)) break;
  await new Promise((r) => setTimeout(r, 500));
}
check('[6] external run reached terminal state', status === 'completed', status);
const detail = await call(`/api/external/v1/results/${runId}`, { headers: { authorization: `Bearer ${tok3}` } });
check('[6] result detail readable by token owner', detail.status === 200 && detail.json?.data?.result_id === runId, detail.status);
const cat = await call('/api/results/categories', { method: 'POST', headers: { authorization: `Bearer ${tok3}` }, body: { name: `安全验收-${rand}` } });
check('[6] category create via idd_ token (201 Created)', [200, 201].includes(cat.status) && cat.json?.success === true, `${cat.status} ${cat.json?.data?.name ?? ''}`);
const patch = await call(`/api/external/v1/results/${runId}`, { method: 'PATCH', headers: { authorization: `Bearer ${tok3}` }, body: { description: `token 验收探针 ${rand}` } });
check('[6] PATCH description via external surface', patch.status === 200 && patch.json?.success === true, patch.status);
const catDel = await call(`/api/results/categories/${cat.json?.data?.id}`, { method: 'DELETE', headers: { authorization: `Bearer ${tok3}` } });
check('[6] category delete (cleanup)', catDel.status === 200, catDel.status);

// cleanup: remove probe token rows + descriptions
const db2 = new Database(join(process.cwd(), 'data', 'diagnostic.db'));
db2.pragma('busy_timeout = 5000');
db2.prepare('DELETE FROM api_tokens WHERE user_id IN (SELECT id FROM users WHERE username LIKE ?)').run('secprobe_%');
db2.close();
const patchBack = await call(`/api/external/v1/results/${runId}`, { method: 'PATCH', headers: { authorization: `Bearer ${jwtA}` }, body: { description: '', tags: [] } });
check('[6] probe result description reset', patchBack.status === 200, patchBack.status);

console.log(`\n[RESULT] failures=${failures}`);
process.exitCode = failures ? 1 : 0;
