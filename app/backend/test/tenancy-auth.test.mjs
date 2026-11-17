// Multi-tenancy / auth hardening e2e (P0-6).
//
// Boots the REAL backend (auth ENABLED — the default) against an isolated DB and
// exercises the frozen interface the next wave depends on:
//   - POST /login (and /register) issue the HttpOnly `idd_session` cookie
//   - the cookie authenticates protected routes; Bearer keeps working; API
//     tokens stay header-only (a token in the cookie is ignored)
//   - POST /logout clears the cookie
//   - CSRF: state-changing requests authenticated via COOKIE require a
//     same-origin (or allowlisted) Origin/Referer; Bearer is exempt
//   - login rate limit: burst ends in 429 + Retry-After
//   - WS handshake accepts the idd_session cookie (subprotocol/query unchanged)
//   - the ownership helper contract consumed by the tenancy wave

import { test, describe, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { spawn } from 'child_process';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { mkdtempSync } from 'fs';
import { tmpdir } from 'os';
import { WebSocket } from 'ws';
import { rateLimit, rateLimitKeyByIp, rateLimitKeyByUser } from '../src/middleware/rateLimit.mjs';
import { isAdmin, canAccessOwner, applyOwnerScope, ownerColumn } from '../src/middleware/ownership.mjs';
import { parseCookies, looksLikeSessionJwt, buildSessionCookie, buildClearedSessionCookie, SESSION_COOKIE_NAME } from '../src/middleware/auth.middleware.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const backendDir = join(here, '..');
const PORT = 3991;
const BASE = `http://127.0.0.1:${PORT}`;
const WS_URL = `ws://127.0.0.1:${PORT}/ws`;
const DB_PATH = join(mkdtempSync(join(tmpdir(), 'idd-tenancy-auth-')), 'auth.db');

const USERNAME = 'tenancy_admin';
const PASSWORD = 'Secret12345';

let server;
let serverLog = '';
let sessionToken = '';       // login JWT (Bearer)
let sessionCookie = '';      // `idd_session=<jwt>` cookie header value
let apiToken = '';           // idd_… API token (header-only)
let loginAttempts = 0;       // every POST /api/auth/login this file has made

async function waitHealthy(timeoutMs = 40000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const res = await fetch(`${BASE}/api/health`, { signal: AbortSignal.timeout(1500) });
      if (res.ok) return;
    } catch { /* not up yet */ }
    await new Promise((r) => setTimeout(r, 400));
  }
  throw new Error(`server not healthy after ${timeoutMs}ms\n${serverLog.slice(-4000)}`);
}

before(async () => {
  server = spawn(process.execPath, [join(backendDir, 'src', 'index.mjs')], {
    cwd: backendDir,
    env: {
      ...process.env,
      PORT: String(PORT),
      SERVER_PORT: String(PORT),
      DATABASE_PATH: DB_PATH,
      AUTH_ENABLED: '1',
      // Deterministic signing key — the child must not read/write data/.auth-jwt-secret.
      AUTH_JWT_SECRET: 'tenancy-auth-e2e-fixed-secret-0123456789',
    },
    windowsHide: true,
  });
  server.stdout.on('data', (d) => { serverLog += d.toString(); });
  server.stderr.on('data', (d) => { serverLog += d.toString(); });
  await waitHealthy();
});

after(async () => {
  if (server && !server.killed) {
    server.kill();
    await new Promise((r) => setTimeout(r, 300));
    try {
      spawn('taskkill', ['/pid', String(server.pid), '/T', '/F'], { windowsHide: true, stdio: 'ignore' });
    } catch { /* ignore */ }
  }
});

/** Unified request helper: never throws; returns status/body/headers/setCookies. */
async function req(method, path, { body, headers } = {}) {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: { 'Content-Type': 'application/json', ...(headers || {}) },
    body: body === undefined ? undefined : JSON.stringify(body),
    redirect: 'manual',
    signal: AbortSignal.timeout(20000),
  });
  let json = null;
  try { json = await res.json(); } catch { /* non-JSON */ }
  const setCookies = typeof res.headers.getSetCookie === 'function' ? res.headers.getSetCookie() : [];
  return { status: res.status, body: json, headers: res.headers, setCookies };
}

function cookieHeaderFrom(setCookies, name = SESSION_COOKIE_NAME) {
  for (const raw of setCookies) {
    const [pair] = raw.split(';');
    const eq = pair.indexOf('=');
    if (eq < 0) continue;
    if (pair.slice(0, eq).trim() === name) return pair.trim();
  }
  return null;
}

/** Split a Set-Cookie value into { name, value, attrs }. */
function parseSetCookie(raw) {
  const [pair, ...attrs] = raw.split(';').map((s) => s.trim());
  const eq = pair.indexOf('=');
  const parsed = { name: pair.slice(0, eq), value: pair.slice(eq + 1), attrs: {} };
  for (const attr of attrs) {
    const i = attr.indexOf('=');
    if (i < 0) parsed.attrs[attr.toLowerCase()] = true;
    else parsed.attrs[attr.slice(0, i).toLowerCase()] = attr.slice(i + 1);
  }
  return parsed;
}

// ─────────────────────────────────────────────────────────────────────────────

describe('session cookie — issue, authenticate, clear', () => {
  test('first register creates the bootstrap admin and issues the session cookie', async () => {
    const r = await req('POST', '/api/auth/register', { body: { username: USERNAME, password: PASSWORD } });
    assert.equal(r.status, 200, JSON.stringify(r.body));
    assert.equal(r.body.success, true);
    assert.equal(r.body.data.user.role, 'admin');

    const cookie = parseSetCookie(r.setCookies.find((c) => c.startsWith(`${SESSION_COOKIE_NAME}=`)) || '');
    assert.equal(cookie.name, SESSION_COOKIE_NAME);
    assert.equal(cookie.value, r.body.data.session_token, 'cookie carries the session JWT itself');
    assert.equal(cookie.attrs.httponly, true, 'HttpOnly');
    assert.equal(String(cookie.attrs.samesite).toLowerCase(), 'strict', 'SameSite=Strict');
    assert.equal(cookie.attrs.path, '/');
    assert.equal(String(cookie.attrs['max-age']), String(r.body.data.expires_in));
    assert.equal(cookie.attrs.secure, undefined, 'no Secure on plain-http test deployments');
  });

  test('login sets the cookie and keeps the response body backward compatible', async () => {
    loginAttempts += 1;
    const r = await req('POST', '/api/auth/login', { body: { username: USERNAME, password: PASSWORD } });
    assert.equal(r.status, 200, JSON.stringify(r.body));
    assert.equal(r.body.success, true);
    assert.equal(r.body.data.user.username, USERNAME);
    assert.equal(r.body.data.token_type, 'Bearer');
    assert.equal(typeof r.body.data.session_token, 'string');

    const cookie = parseSetCookie(r.setCookies.find((c) => c.startsWith(`${SESSION_COOKIE_NAME}=`)) || '');
    assert.equal(cookie.value, r.body.data.session_token);
    assert.equal(cookie.attrs.httponly, true);
    assert.equal(String(cookie.attrs.samesite).toLowerCase(), 'strict');
    assert.equal(cookie.attrs.path, '/');
    assert.equal(Number(cookie.attrs['max-age']), Number(r.body.data.expires_in));

    sessionToken = r.body.data.session_token;
    sessionCookie = `${SESSION_COOKIE_NAME}=${cookie.value}`;
  });

  test('the cookie alone authenticates protected routes (/me and /api/history)', async () => {
    const me = await req('GET', '/api/auth/me', { headers: { Cookie: sessionCookie } });
    assert.equal(me.status, 200, JSON.stringify(me.body));
    assert.equal(me.body.data.user.username, USERNAME);
    assert.equal(me.body.data.auth_type, 'session');

    const history = await req('GET', '/api/history/runs', { headers: { Cookie: sessionCookie } });
    assert.equal(history.status, 200, JSON.stringify(history.body));
    assert.equal(history.body.success, true);
    assert.ok(Array.isArray(history.body.data));
  });

  test('a Bearer header still works and takes precedence over the cookie', async () => {
    const me = await req('GET', '/api/auth/me', {
      headers: { Authorization: `Bearer ${sessionToken}`, Cookie: `${SESSION_COOKIE_NAME}=garbage` },
    });
    assert.equal(me.status, 200, JSON.stringify(me.body));
    assert.equal(me.body.data.auth_type, 'session');
  });

  test('API tokens stay header-only: a token in the cookie is ignored', async () => {
    const created = await req('POST', '/api/auth/tokens', {
      headers: { Authorization: `Bearer ${sessionToken}` },
      body: { name: 'tenancy-e2e' },
    });
    assert.equal(created.status, 200, JSON.stringify(created.body));
    apiToken = created.body.data.token;
    assert.ok(apiToken.startsWith('idd_'));

    const viaHeader = await req('GET', '/api/auth/me', { headers: { Authorization: `Bearer ${apiToken}` } });
    assert.equal(viaHeader.status, 200);
    assert.equal(viaHeader.body.data.auth_type, 'api_token');

    const viaCookie = await req('GET', '/api/auth/me', { headers: { Cookie: `${SESSION_COOKIE_NAME}=${apiToken}` } });
    assert.equal(viaCookie.status, 401, 'API tokens must not authenticate through the cookie channel');
    assert.equal(viaCookie.body.code, 'AUTH_REQUIRED');
  });

  test('POST /logout clears the cookie and reports ok', async () => {
    const r = await req('POST', '/api/auth/logout', { headers: { Cookie: sessionCookie, Origin: BASE }, body: {} });
    assert.equal(r.status, 200, JSON.stringify(r.body));
    assert.equal(r.body.success, true);
    assert.equal(r.body.data.ok, true);

    const cleared = parseSetCookie(r.setCookies.find((c) => c.startsWith(`${SESSION_COOKIE_NAME}=`)) || '');
    assert.equal(cleared.name, SESSION_COOKIE_NAME);
    assert.equal(cleared.value, '');
    assert.equal(String(cleared.attrs['max-age']), '0');
    assert.equal(cleared.attrs.httponly, true);
    assert.equal(String(cleared.attrs.samesite).toLowerCase(), 'strict');
  });
});

describe('CSRF — cookie-authenticated mutations require same-origin', () => {
  test('foreign Origin on a cookie-authenticated POST is blocked with 403 CSRF_BLOCKED', async () => {
    const r = await req('POST', '/api/auth/tokens', {
      headers: { Cookie: sessionCookie, Origin: 'http://evil.example.com' },
      body: { name: 'csrf-attempt' },
    });
    assert.equal(r.status, 403, JSON.stringify(r.body));
    assert.equal(r.body.code, 'CSRF_BLOCKED');
    assert.equal(r.body.success, false);
  });

  test('missing Origin/Referer on a cookie-authenticated POST is blocked', async () => {
    const r = await req('POST', '/api/auth/tokens', {
      headers: { Cookie: sessionCookie },
      body: { name: 'no-origin' },
    });
    assert.equal(r.status, 403);
    assert.equal(r.body.code, 'CSRF_BLOCKED');
  });

  test('same-origin Origin passes; allowlisted dev origin (Vite proxy) also passes', async () => {
    const sameOrigin = await req('POST', '/api/auth/tokens', {
      headers: { Cookie: sessionCookie, Origin: BASE },
      body: { name: 'csrf-same-origin' },
    });
    assert.equal(sameOrigin.status, 200, JSON.stringify(sameOrigin.body));
    assert.ok(sameOrigin.body.data.token.startsWith('idd_'));

    // config.server.cors_origins ships the Vite dev origins; behind the proxy
    // Origin (5180) and Host (3210) differ, yet both are the same application.
    const viaDevOrigin = await req('POST', '/api/auth/tokens', {
      headers: { Cookie: sessionCookie, Origin: 'http://localhost:5180' },
      body: { name: 'csrf-dev-origin' },
    });
    assert.equal(viaDevOrigin.status, 200, JSON.stringify(viaDevOrigin.body));
  });

  test('Referer is honoured when Origin is absent (same-origin passes, foreign is blocked)', async () => {
    const ok = await req('POST', '/api/auth/tokens', {
      headers: { Cookie: sessionCookie, Referer: `${BASE}/diagnose` },
      body: { name: 'csrf-referer-ok' },
    });
    assert.equal(ok.status, 200, JSON.stringify(ok.body));

    const bad = await req('POST', '/api/auth/tokens', {
      headers: { Cookie: sessionCookie, Referer: 'http://evil.example.com/diagnose' },
      body: { name: 'csrf-referer-bad' },
    });
    assert.equal(bad.status, 403);
    assert.equal(bad.body.code, 'CSRF_BLOCKED');
  });

  test('Bearer-authenticated requests are exempt from the CSRF check', async () => {
    const r = await req('POST', '/api/auth/tokens', {
      headers: { Authorization: `Bearer ${sessionToken}`, Origin: 'http://evil.example.com' },
      body: { name: 'bearer-exempt' },
    });
    assert.equal(r.status, 200, JSON.stringify(r.body));
    assert.ok(r.body.data.token.startsWith('idd_'));
  });

  test('safe methods (GET) are never CSRF-checked', async () => {
    const r = await req('GET', '/api/history/runs', {
      headers: { Cookie: sessionCookie, Origin: 'http://evil.example.com' },
    });
    assert.equal(r.status, 200, JSON.stringify(r.body));
  });

  test('login/register/logout are exempt paths', async () => {
    // login: no session yet → CSRF never applies (wrong password → 401, not 403)
    loginAttempts += 1;
    const login = await req('POST', '/api/auth/login', {
      headers: { Origin: 'http://evil.example.com' },
      body: { username: USERNAME, password: 'wrong-password-1' },
    });
    assert.notEqual(login.status, 403);
    assert.equal(login.status, 401, JSON.stringify(login.body));

    // logout: session teardown only destroys the caller's own credential
    const logout = await req('POST', '/api/auth/logout', {
      headers: { Cookie: sessionCookie, Origin: 'http://evil.example.com' },
      body: {},
    });
    assert.equal(logout.status, 200, JSON.stringify(logout.body));
    assert.equal(logout.body.data.ok, true);
  });
});

describe('login rate limit — burst ends in 429 with Retry-After', () => {
  test('wrong-password burst hits the limiter; further attempts stay blocked', async () => {
    let attempts = 0;
    let blocked = null;
    for (; attempts < 10; attempts += 1) {
      loginAttempts += 1;
      const r = await req('POST', '/api/auth/login', {
        headers: { Origin: BASE },
        body: { username: USERNAME, password: `wrong-password-burst-${attempts}` },
      });
      if (r.status === 429) { blocked = r; break; }
      assert.equal(r.status, 401, `attempt ${attempts + 1} → unexpected ${r.status}: ${JSON.stringify(r.body)}`);
    }

    assert.ok(blocked, `a 429 must arrive within 10 burst attempts (login attempts so far: ${loginAttempts})`);
    assert.equal(blocked.body.success, false);
    assert.equal(blocked.body.code, 'RATE_LIMITED');
    const retryAfter = Number(blocked.headers.get('retry-after'));
    assert.ok(Number.isFinite(retryAfter) && retryAfter >= 1, `Retry-After must be a positive integer, got ${blocked.headers.get('retry-after')}`);
    assert.ok(retryAfter <= 60, 'Retry-After must not exceed the configured window');

    // The limiter stays blocking for the rest of the window.
    const again = await req('POST', '/api/auth/login', {
      headers: { Origin: BASE },
      body: { username: USERNAME, password: 'wrong-password-after' },
    });
    assert.equal(again.status, 429);
    assert.equal(again.body.code, 'RATE_LIMITED');
    assert.ok(Number(again.headers.get('retry-after')) >= 1);

    // Rate limiting is scoped to login: other auth routes still answer.
    const me = await req('GET', '/api/auth/me', { headers: { Cookie: sessionCookie } });
    assert.equal(me.status, 200);
  });
});

describe('WebSocket — idd_session cookie authenticates the handshake', () => {
  function openWs(headers) {
    return new Promise((resolve, reject) => {
      const ws = new WebSocket(WS_URL, { headers });
      ws.on('error', () => { /* rejected handshakes surface as close 4401 */ });
      ws.closed = new Promise((res) => ws.once('close', (code) => res(code)));
      const inbox = [];
      const waiters = [];
      ws.on('message', (raw) => {
        let parsed = null;
        try { parsed = JSON.parse(raw.toString()); } catch { /* ignore */ }
        const waiter = waiters.shift();
        if (waiter) waiter(parsed);
        else inbox.push(parsed);
      });
      ws.next = () => (inbox.length ? Promise.resolve(inbox.shift()) : new Promise((r) => waiters.push(r)));
      ws.once('open', () => resolve(ws));
      ws.once('error', reject);
    });
  }

  test('cookie authenticates; missing and API-token cookies are rejected with 4401', async () => {
    const ok = await openWs({ Cookie: sessionCookie });
    try {
      const welcome = await ok.next();
      assert.equal(welcome.type, 'welcome');
    } finally {
      ok.close();
    }

    const noCookie = await openWs({});
    assert.equal(await noCookie.closed, 4401);

    const tokenInCookie = await openWs({ Cookie: `${SESSION_COOKIE_NAME}=${apiToken}` });
    assert.equal(await tokenInCookie.closed, 4401, 'WS cookie channel is session-JWT only');
  });
});

// ─── Unit contracts (frozen interface for the tenancy wave) ──────────────────

describe('ownership helpers — scope contract', () => {
  const admin = { id: 1, username: 'a', role: 'admin' };
  const user = { id: 7, username: 'u', role: 'user' };

  test('isAdmin / canAccessOwner', () => {
    assert.equal(isAdmin(admin), true);
    assert.equal(isAdmin(user), false);
    assert.equal(isAdmin(null), false);

    assert.equal(canAccessOwner(admin, 7), true, 'admin reaches other users rows');
    assert.equal(canAccessOwner(admin, null), true, 'admin reaches unowned (legacy) rows');
    assert.equal(canAccessOwner(user, 7), true);
    assert.equal(canAccessOwner(user, 8), false);
    assert.equal(canAccessOwner(user, null), false, 'unowned rows are admin-only');
    assert.equal(canAccessOwner(null, 7), false);
  });

  test('applyOwnerScope returns { clause, params }', () => {
    assert.deepEqual(applyOwnerScope(admin), { clause: '1=1', params: [] });
    assert.deepEqual(applyOwnerScope(user), { clause: 't.owner_user_id = ?', params: [7] });
    assert.deepEqual(applyOwnerScope(user, { alias: 'r' }), { clause: 'r.owner_user_id = ?', params: [7] });
    assert.deepEqual(applyOwnerScope(user, { alias: '' }), { clause: 'owner_user_id = ?', params: [7] });
    assert.deepEqual(applyOwnerScope(null), { clause: '1=0', params: [] });
    assert.equal(ownerColumn('r'), 'r.owner_user_id');
  });

  test('the scope clause is valid SQL against the shipped schema', async () => {
    const Database = (await import('better-sqlite3')).default;
    const { runMigrations } = await import('../src/db/migrations.mjs');
    const dir = mkdtempSync(join(tmpdir(), 'idd-owner-scope-'));
    const db = new Database(join(dir, 'scope.db'));
    try {
      db.pragma('foreign_keys = ON');
      runMigrations(db, { log: { info: () => {} } });
      db.prepare("INSERT INTO users (id, username, password_hash, role) VALUES (1,'adm','x','admin'), (7,'u','x','user')").run();
      db.prepare("INSERT INTO diagnostic_runs (run_id, name, scene_name, data_path, owner_user_id) VALUES ('mine','mine','s','p',7)").run();
      db.prepare("INSERT INTO diagnostic_runs (run_id, name, scene_name, data_path, owner_user_id) VALUES ('legacy','legacy','s','p',NULL)").run();
      db.prepare("INSERT INTO diagnostic_runs (run_id, name, scene_name, data_path, owner_user_id) VALUES ('theirs','theirs','s','p',99)").run();

      const list = (who) => {
        const { clause, params } = applyOwnerScope(who, { alias: 'r' });
        return db.prepare(`SELECT r.run_id FROM diagnostic_runs r WHERE ${clause} ORDER BY r.run_id`).all(...params).map((x) => x.run_id);
      };
      assert.deepEqual(list(user), ['mine']);
      assert.deepEqual(list(admin), ['legacy', 'mine', 'theirs']);
      assert.deepEqual(list(null), []);
    } finally {
      db.close();
    }
  });
});

describe('rate limit factory — deterministic unit behaviour', () => {
  function fakeReq(extra = {}) {
    return { ip: '10.0.0.1', headers: {}, method: 'POST', ...extra };
  }

  function fakeRes() {
    const res = {
      headers: {},
      statusCode: 200,
      body: null,
      headersSent: false,
      setHeader(name, value) { res.headers[name.toLowerCase()] = String(value); },
      status(code) { res.statusCode = code; return res; },
      json(payload) { res.body = payload; res.headersSent = true; return res; },
    };
    return res;
  }

  function call(mw, req) {
    const res = fakeRes();
    let passed = false;
    mw(req, res, () => { passed = true; });
    return { res, passed };
  }

  test('allows max requests then 429s with Retry-After and a RATE_LIMITED body', () => {
    const mw = rateLimit({ windowMs: 60_000, max: 3, keyFn: rateLimitKeyByIp });
    const req = fakeReq();
    for (let i = 1; i <= 3; i += 1) {
      const { res, passed } = call(mw, req);
      assert.equal(passed, true, `request ${i} passes`);
      assert.equal(res.headersSent, false);
    }
    const { res, passed } = call(mw, fakeReq());
    assert.equal(passed, false, '4th request is blocked');
    assert.equal(res.statusCode, 429);
    assert.equal(res.body.success, false);
    assert.equal(res.body.code, 'RATE_LIMITED');
    assert.ok(typeof res.body.error === 'string' && res.body.error.length > 0);
    const retryAfter = Number(res.headers['retry-after']);
    assert.ok(Number.isInteger(retryAfter) && retryAfter >= 1 && retryAfter <= 60);
    assert.equal(res.body.retry_after, retryAfter);

    // Blocked requests do not extend the window: after it elapses, traffic resumes.
    const later = Date.now() + 60_001;
    const realNow = Date.now;
    Date.now = () => later;
    try {
      const afterWindow = call(mw, fakeReq());
      assert.equal(afterWindow.passed, true, 'window expiry frees the key');
    } finally {
      Date.now = realNow;
    }
  });

  test('keys are isolated per keyFn result (IP vs user)', () => {
    const mw = rateLimit({ windowMs: 60_000, max: 1, keyFn: rateLimitKeyByUser });
    const onlyOne = call(mw, { ip: '10.0.0.1', user: { id: 1 } });
    assert.equal(onlyOne.passed, true);
    const sameUser = call(mw, { ip: '10.0.0.2', user: { id: 1 } });
    assert.equal(sameUser.passed, false, 'user budget is shared across IPs');
    const otherUser = call(mw, { ip: '10.0.0.1', user: { id: 2 } });
    assert.equal(otherUser.passed, true);
    const anon = call(mw, { ip: '10.0.0.9' });
    assert.equal(anon.passed, true, 'anonymous falls back to the IP key');
    assert.equal(rateLimitKeyByIp({ ip: '1.2.3.4' }), 'ip:1.2.3.4');
    assert.equal(rateLimitKeyByUser({ user: { id: 5 } }), 'user:5');
  });

  test('onLimit hook can observe and take over the 429', () => {
    const seen = [];
    const mw = rateLimit({
      windowMs: 60_000,
      max: 1,
      keyFn: () => 'k',
      onLimit: (req, res, info) => { seen.push(info); return true; },
    });
    assert.equal(call(mw, fakeReq()).passed, true);
    const { res, passed } = call(mw, fakeReq());
    assert.equal(passed, false);
    assert.equal(res.headersSent, false, 'hook took over the response');
    assert.equal(seen.length, 1);
    assert.equal(seen[0].limit, 1);
    assert.equal(typeof seen[0].retryAfterSec, 'number');
  });

  test('invalid configuration is rejected loudly', () => {
    assert.throws(() => rateLimit({ windowMs: 0 }), /windowMs/);
    assert.throws(() => rateLimit({ max: 0 }), /max/);
    assert.throws(() => rateLimit({ keyFn: 'nope' }), /keyFn/);
  });
});

describe('cookie helpers (unit)', () => {
  test('parseCookies / looksLikeSessionJwt', () => {
    assert.deepEqual(parseCookies('a=1; b=two; idd_session=x.y.z'), { a: '1', b: 'two', idd_session: 'x.y.z' });
    assert.deepEqual(parseCookies(''), {});
    assert.deepEqual(parseCookies(undefined), {});
    assert.equal(looksLikeSessionJwt('a.b.c'), true);
    assert.equal(looksLikeSessionJwt('idd_abc'), false);
    assert.equal(looksLikeSessionJwt('a.b'), false);
    assert.equal(looksLikeSessionJwt(''), false);
    assert.equal(looksLikeSessionJwt(null), false);
  });

  test('cookie builders honour COOKIE_SECURE=1', () => {
    const issued = buildSessionCookie('t.t.t', 3600);
    assert.match(issued, /^idd_session=t\.t\.t; HttpOnly; SameSite=Strict; Path=\/; Max-Age=3600$/);
    assert.match(buildClearedSessionCookie(), /^idd_session=; HttpOnly; SameSite=Strict; Path=\/; Max-Age=0$/);

    process.env.COOKIE_SECURE = '1';
    try {
      assert.match(buildSessionCookie('t.t.t', 60), /; Secure; Max-Age=60$/);
      assert.match(buildClearedSessionCookie(), /; Secure; Max-Age=0$/);
    } finally {
      delete process.env.COOKIE_SECURE;
    }
  });
});
