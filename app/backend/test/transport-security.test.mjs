// Transport security (P0-9) + graceful-shutdown guard (P0-4).
//
// Covers: CORS allowlist (unit + express integration), safeSend backpressure,
// WebSocket payload cap (1009) + `idd-token` subprotocol negotiation, and the
// shutdown guard middleware.
//
// House pattern (see registry.test.mjs): the environment must be fixed BEFORE
// the module graph is imported — config is resolved at import time — so every
// app module below is loaded with a dynamic import.
import { test, describe, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'http';
import { mkdtempSync } from 'fs';
import { tmpdir } from 'os';
import { join } from 'path';
import express from 'express';
import cors from 'cors';
import { WebSocket } from 'ws';

// Isolated DB; small payload cap so a 128KB frame is unambiguously over it;
// auth off so the WS connection tests observe transport behaviour, not 4401.
process.env.DATABASE_PATH = join(mkdtempSync(join(tmpdir(), 'idd-transport-')), 'transport.db');
process.env.WS_MAX_PAYLOAD_BYTES = String(64 * 1024);
process.env.AUTH_ENABLED = '0';

// src/engine/diagnosis-engine.mjs (not editable in this wave) installs a
// 5-minute housekeeping interval at module load without unref'ing it, so
// importing ws-server would keep this test process alive forever. Unref every
// interval created while the app module graph loads; any other leaked handle
// still hangs the file loudly.
const realSetInterval = globalThis.setInterval;
globalThis.setInterval = (...args) => {
  const timer = realSetInterval(...args);
  timer.unref?.();
  return timer;
};
let corsModule;
let wsModule;
let lifecycleModule;
try {
  corsModule = await import('../src/transport/cors.mjs');
  wsModule = await import('../src/transport/ws-server.mjs');
  lifecycleModule = await import('../src/lifecycle.mjs');
} finally {
  globalThis.setInterval = realSetInterval;
}

const { buildCorsOptions, resolveAllowedOrigins } = corsModule;
const { safeSend, initWebSocket, getWSS, WS_TOKEN_PROTOCOL } = wsModule;
const {
  isShuttingDown, setShuttingDown, registerShutdownHook, runShutdownHooks, shutdownGuardMiddleware,
} = lifecycleModule;

const DEV_ORIGINS = ['http://localhost:5180', 'http://127.0.0.1:5180'];

function listen(server) {
  return new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
}
function closeServer(server) {
  return new Promise((resolve) => server.close(resolve));
}

// ─── lifecycle: shutdown hooks ───────────────────────────────────────────────
// Declared FIRST: the guard suite below flips the process-wide shutdown flag,
// and registerShutdownHook short-circuits once shutdown has started.
describe('lifecycle — shutdown hooks', () => {
  test('LIFO order, failures contained, runs exactly once', async () => {
    const order = [];
    registerShutdownHook(() => { order.push('first'); });
    registerShutdownHook(() => { throw new Error('hook boom'); });
    registerShutdownHook(async () => { order.push('third'); });

    const reported = [];
    const errors = await runShutdownHooks({ onError: (err) => reported.push(err.message) });

    assert.deepEqual(order, ['third', 'first'], 'hooks unwind LIFO, a throwing hook does not block the rest');
    assert.deepEqual(reported, ['hook boom']);
    assert.equal(errors.length, 1);
    assert.deepEqual(await runShutdownHooks(), [], 'second run is a no-op');
  });
});

// ─── CORS allowlist ─────────────────────────────────────────────────────────
function ask(options, origin) {
  return new Promise((resolve, reject) => {
    options.origin(origin, (err, allowed) => (err ? reject(err) : resolve(allowed)));
  });
}

describe('CORS allowlist — buildCorsOptions', () => {
  test('listed origin allowed, unlisted origin denied, no-Origin passes', async () => {
    const options = buildCorsOptions({ env: {}, config: { server: { cors_origins: DEV_ORIGINS } } });
    assert.equal(await ask(options, 'http://localhost:5180'), true);
    assert.equal(await ask(options, 'http://127.0.0.1:5180'), true);
    assert.equal(await ask(options, 'http://evil.example'), false);
    assert.equal(await ask(options, undefined), true, 'curl / probes / same-origin send no Origin');
  });

  test('CORS_ORIGINS env overrides config.server.cors_origins (comma-separated)', async () => {
    const env = { CORS_ORIGINS: ' https://a.example , https://b.example ' };
    assert.deepEqual(resolveAllowedOrigins({ env, config: { server: { cors_origins: DEV_ORIGINS } } }),
      ['https://a.example', 'https://b.example']);
    const options = buildCorsOptions({ env, config: { server: { cors_origins: DEV_ORIGINS } } });
    assert.equal(await ask(options, 'https://a.example'), true);
    assert.equal(await ask(options, 'http://localhost:5180'), false, 'env replaces the config list, not extends it');
  });

  test('config/default.yaml ships the Vite dev origins', async () => {
    const { config } = await import('../../../config/loader.mjs');
    assert.deepEqual(config.server.cors_origins, DEV_ORIGINS);
  });

  test('express + cors package: headers only for allowlisted origins', async () => {
    const app = express();
    app.use(cors(buildCorsOptions({ env: {}, config: { server: { cors_origins: DEV_ORIGINS } } })));
    app.get('/api/health', (req, res) => res.json({ success: true }));
    const server = createServer(app);
    await listen(server);
    const base = `http://127.0.0.1:${server.address().port}`;
    try {
      const allowed = await fetch(`${base}/api/health`, { headers: { Origin: 'http://localhost:5180' } });
      assert.equal(allowed.status, 200);
      assert.equal(allowed.headers.get('access-control-allow-origin'), 'http://localhost:5180');

      const denied = await fetch(`${base}/api/health`, { headers: { Origin: 'http://evil.example' } });
      assert.equal(denied.status, 200, 'CORS is browser-enforced — the request itself still completes');
      assert.equal(denied.headers.get('access-control-allow-origin'), null);

      const noOrigin = await fetch(`${base}/api/health`);
      assert.equal(noOrigin.status, 200);
      assert.equal(noOrigin.headers.get('access-control-allow-origin'), null);
    } finally {
      await closeServer(server);
    }
  });
});

// ─── safeSend backpressure ──────────────────────────────────────────────────
describe('safeSend — backpressure', () => {
  function fakeSocket(bufferedAmount) {
    return {
      readyState: 1,
      OPEN: 1,
      bufferedAmount,
      sent: [],
      send(payload) { this.sent.push(payload); },
    };
  }

  test('non-critical dropped above 4MB, critical always sent', () => {
    const ws = fakeSocket(5 * 1024 * 1024);
    assert.equal(safeSend(ws, { type: 'catalog_update', data: {} }), false);
    assert.equal(ws.sent.length, 0, 'slow client: stale snapshot is dropped, not buffered');

    assert.equal(safeSend(ws, { type: 'error', data: { message: 'boom' } }, { critical: true }), true);
    assert.equal(ws.sent.length, 1);
    assert.equal(JSON.parse(ws.sent[0]).type, 'error');
  });

  test('below the threshold non-critical frames are still sent', () => {
    const ws = fakeSocket(1024);
    assert.equal(safeSend(ws, { type: 'ping', data: {} }), true);
    assert.equal(ws.sent.length, 1);
  });

  test('closed socket: nothing sent', () => {
    const ws = fakeSocket(0);
    ws.readyState = 3;
    assert.equal(safeSend(ws, { type: 'error' }, { critical: true }), false);
    assert.equal(ws.sent.length, 0);
  });
});

// ─── WebSocket server: payload cap + subprotocol token ──────────────────────
describe('WebSocket transport hardening', () => {
  let httpServer;
  let base;
  const clients = new Set();

  before(async () => {
    httpServer = createServer((req, res) => { res.writeHead(404); res.end(); });
    await listen(httpServer);
    base = `ws://127.0.0.1:${httpServer.address().port}/ws`;
    initWebSocket(httpServer);
  });

  after(async () => {
    for (const ws of clients) { try { ws.terminate(); } catch { /* already gone */ } }
    getWSS()?.close();
    await closeServer(httpServer);
  });

  function open(protocols, url = base) {
    return new Promise((resolve, reject) => {
      const ws = protocols ? new WebSocket(url, protocols) : new WebSocket(url);
      clients.add(ws);
      // Attached at construction: the server may close before the test asks.
      ws.closed = new Promise((resolveClose) => ws.once('close', (code) => resolveClose(code)));
      // Buffer from connection start: `welcome` can land before the test
      // attaches its own listener.
      ws.inbox = [];
      ws.inboxWaiters = [];
      ws.on('message', (raw) => {
        const parsed = JSON.parse(raw.toString());
        const waiter = ws.inboxWaiters.shift();
        if (waiter) waiter(parsed);
        else ws.inbox.push(parsed);
      });
      ws.once('open', () => resolve(ws));
      ws.once('error', reject);
    });
  }

  function nextMessage(ws) {
    if (ws.inbox.length) return Promise.resolve(ws.inbox.shift());
    return new Promise((resolve) => ws.inboxWaiters.push(resolve));
  }

  test('frame above WS_MAX_PAYLOAD_BYTES (64KB) closes the socket with 1009', async () => {
    const ws = await open();
    const closed = new Promise((resolve) => ws.once('close', (code) => resolve(code)));
    ws.send(Buffer.alloc(128 * 1024, 0x41)); // 128KB in one frame
    assert.equal(await closed, 1009);
  });

  test('idd-token subprotocol is selected when offered', async () => {
    const ws = await open([WS_TOKEN_PROTOCOL, 'dummy-token']);
    assert.equal(ws.protocol, WS_TOKEN_PROTOCOL);
    assert.equal((await nextMessage(ws)).type, 'welcome');
    ws.close();
  });

  test('client offering no subprotocol still connects (legacy clients)', async () => {
    const ws = await open();
    assert.equal(ws.protocol, '');
    assert.equal((await nextMessage(ws)).type, 'welcome');
    ws.close();
  });

  describe('token transport with auth enabled', () => {
    let token = '';

    before(async () => {
      process.env.AUTH_ENABLED = '1'; // read per-connection by isAuthEnabled()
      const { registerUser, createApiToken } = await import('../src/services/auth.service.mjs');
      const { user } = registerUser({ username: `ws_token_${Date.now().toString(36)}`, password: 'Secret12345' });
      token = createApiToken(user, { name: 'ws-transport-test' }).token;
    });

    after(() => { process.env.AUTH_ENABLED = '0'; });

    test('token offered as idd-token subprotocol authenticates', async () => {
      const ws = await open([WS_TOKEN_PROTOCOL, token]);
      assert.equal(ws.protocol, WS_TOKEN_PROTOCOL);
      assert.equal((await nextMessage(ws)).type, 'welcome');
      ws.close();
    });

    test('deprecated ?token= query fallback still authenticates', async () => {
      const ws = await open(null, `${base}?token=${encodeURIComponent(token)}`);
      assert.equal((await nextMessage(ws)).type, 'welcome');
      ws.close();
    });

    test('invalid subprotocol token is rejected with 4401', async () => {
      const ws = await open([WS_TOKEN_PROTOCOL, 'not-a-real-token']);
      assert.equal(await ws.closed, 4401);
    });

    test('no token at all is rejected with 4401', async () => {
      const ws = await open();
      assert.equal(await ws.closed, 4401);
    });
  });
});

// ─── graceful shutdown guard ────────────────────────────────────────────────
describe('shutdown guard — new API traffic fails fast, health probe still answers', () => {
  test('503 SHUTTING_DOWN once shutting down; GET /api/health passes through', async () => {
    const app = express();
    app.use(shutdownGuardMiddleware());
    app.get('/api/health', (req, res) => res.json({ success: true, status: 'ok' }));
    app.post('/api/diagnosis/start', (req, res) => res.json({ success: true }));
    const server = createServer(app);
    await listen(server);
    const base = `http://127.0.0.1:${server.address().port}`;
    try {
      assert.equal(isShuttingDown(), false);
      assert.equal((await fetch(`${base}/api/diagnosis/start`, { method: 'POST' })).status, 200);

      setShuttingDown('test');
      assert.equal(isShuttingDown(), true);
      assert.equal(setShuttingDown('again'), false, 'first reason wins');

      const blocked = await fetch(`${base}/api/diagnosis/start`, { method: 'POST' });
      assert.equal(blocked.status, 503);
      assert.deepEqual(await blocked.json(), { success: false, code: 'SHUTTING_DOWN' });

      const health = await fetch(`${base}/api/health`);
      assert.equal(health.status, 200, 'liveness probe must keep answering while draining');
      assert.equal((await health.json()).status, 'ok');
    } finally {
      await closeServer(server);
    }
  });
});
