// Health endpoints — liveness (GET /api/health) + readiness (GET /api/health/ready).
//
// Boots the REAL app module graph in-process against an isolated temp DB and
// asserts both HTTP contracts, including the graceful-shutdown semantics:
//   · liveness keeps its legacy shape and keeps answering while draining,
//   · readiness is public (no credentials) and reports
//       503 {status:"unavailable", reasons:["shutting_down"]} while draining,
//       200 {status:"degraded",  reasons:["low_disk"]} for warnings.
//
// House pattern (transport-security.test.mjs): the environment must be fixed
// BEFORE the module graph is imported — config is resolved at import time and
// index.mjs starts listening in the same tick chain.
import { test, describe, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync } from 'fs';
import { createServer } from 'net';
import { tmpdir } from 'os';
import { join } from 'path';

const tmpRoot = mkdtempSync(join(tmpdir(), 'idd-health-'));
process.env.DATABASE_PATH = join(tmpRoot, 'health.db');
process.env.AUTH_ENABLED = '1'; // probes must stay public WITH auth enabled

// Every CLI engine is pointed at a missing binary through the documented
// override chain (config → HARNESS_<ID>_COMMAND → PATH) so the readiness engine
// sweep fails fast and deterministically instead of probing whatever happens to
// be installed on the build agent. The in-process engines (mock, claude SDK)
// stay available.
for (const id of ['CODEX', 'DSH', 'HERMES', 'QWEN', 'OPENCODE', 'GEMINI', 'COPILOT', 'CURSOR', 'CRUSH', 'GOOSE', 'PI', 'OMP']) {
  process.env[`HARNESS_${id}_COMMAND`] = join(tmpRoot, `no-such-${id.toLowerCase()}`);
}
process.env.READINESS_ENGINE_PROBE_TIMEOUT_MS = '1500'; // keep the sweep bounded in CI

/** Reserve (and immediately release) a free port for the in-process server. */
function freePort() {
  return new Promise((resolve, reject) => {
    const probe = createServer();
    probe.once('error', reject);
    probe.listen(0, '127.0.0.1', () => {
      const { port } = probe.address();
      probe.close(() => resolve(port));
    });
  });
}
const PORT = await freePort();
process.env.PORT = String(PORT);
process.env.SERVER_PORT = String(PORT);

// src/engine/diagnosis-engine.mjs installs a housekeeping interval at module
// load without unref'ing it → unref every interval created while the app graph
// loads, so this test process can exit (transport-security.test.mjs guard).
const realSetInterval = globalThis.setInterval;
globalThis.setInterval = (...args) => {
  const timer = realSetInterval(...args);
  timer.unref?.();
  return timer;
};
let lifecycleModule;
let wsModule;
let configModule;
try {
  await import('../src/index.mjs');
  lifecycleModule = await import('../src/lifecycle.mjs');
  wsModule = await import('../src/transport/ws-server.mjs');
  configModule = await import('../../../config/loader.mjs');
} finally {
  globalThis.setInterval = realSetInterval;
}

const BASE = `http://127.0.0.1:${PORT}`;

async function waitHealthy(timeoutMs = 20000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const res = await fetch(`${BASE}/api/health`, { signal: AbortSignal.timeout(1500) });
      if (res.ok) return;
    } catch { /* not up yet */ }
    await new Promise((r) => setTimeout(r, 200));
  }
  throw new Error('in-process server did not become healthy');
}

before(async () => { await waitHealthy(); });

after(async () => {
  // index.mjs does not export the http.Server it created; the WebSocket server
  // holds the same instance (wss._server, set by ws when handed `server`).
  // ORDER MATTERS: wss.close() sets wss._server = null (ws clears the external
  // server it was given), so the reference must be captured BEFORE closing the
  // wss — otherwise the listener is never released and this process hangs.
  const wss = wsModule.getWSS();
  const httpServer = wss?._server;
  try { wss?.close(); } catch { /* already gone */ }
  try {
    httpServer?.close();
    httpServer?.closeIdleConnections?.(); // keep-alive sockets must not hold the drain
  } catch { /* already gone */ }
});

describe('liveness — GET /api/health', () => {
  test('keeps the legacy shape (ok + timestamp/uptime/memory/checks)', async () => {
    const res = await fetch(`${BASE}/api/health`);
    assert.equal(res.status, 200);
    const body = await res.json();

    assert.equal(body.status, 'ok');
    assert.ok(!Number.isNaN(Date.parse(body.timestamp)), 'timestamp is ISO-parseable');
    assert.ok(typeof body.uptime === 'number' && body.uptime >= 0);
    assert.ok(body.memory, 'memory block present');
    for (const key of ['rss', 'heapUsed', 'heapTotal']) {
      assert.ok(typeof body.memory[key] === 'string' && body.memory[key].endsWith('MB'), `memory.${key}`);
    }
    assert.equal(body.checks.database.status, 'ok');
    assert.equal(typeof body.checks.activeRuns, 'number');
  });
});

describe('readiness — GET /api/health/ready', () => {
  test('200 with db/disk/engines checks and a reasons array', async () => {
    const res = await fetch(`${BASE}/api/health/ready`);
    assert.equal(res.status, 200, 'no critical dependency is down in this test');
    const body = await res.json();

    assert.ok(['ok', 'degraded'].includes(body.status), `unexpected status: ${body.status}`);
    assert.ok(Array.isArray(body.reasons));
    assert.equal(body.checks.database.status, 'ok');

    assert.ok(['ok', 'warn', 'skipped'].includes(body.checks.disk.status), 'disk check reported');
    if (body.checks.disk.status !== 'skipped') {
      assert.ok(Number.isFinite(body.checks.disk.free_mb));
      assert.ok(Number.isFinite(body.checks.disk.threshold_mb));
    }

    assert.ok(['ok', 'warn', 'unknown', 'skipped'].includes(body.checks.engines.status), 'engine check reported');
    assert.ok(body.checks.engines.total >= 1, 'the registry always has engines (mock is in-process)');
    assert.ok(body.checks.engines.available <= body.checks.engines.total);
  });

  test('engine availability reuses the harness probes (in-process engines available)', async () => {
    // Warm or cached — both paths are fine; the mock engine cannot go away.
    const body = await (await fetch(`${BASE}/api/health/ready`)).json();
    if (body.checks.engines.status === 'ok') {
      assert.ok(body.checks.engines.engines.includes('mock'));
    }
  });

  test('low free space → HTTP 200 + status degraded + reasons [low_disk]', async () => {
    const { config } = configModule;
    const savedHealth = config.health;
    try {
      // Threshold above any real disk → guaranteed warn. Read per request.
      config.health = { ...(savedHealth || {}), min_free_mb: 1e9 };
      const res = await fetch(`${BASE}/api/health/ready`);
      assert.equal(res.status, 200, 'disk pressure is a warning, never a 503');
      const body = await res.json();

      assert.equal(body.status, 'degraded');
      assert.ok(body.reasons.includes('low_disk'));
      if (body.checks.disk.status === 'warn') {
        assert.ok(body.checks.disk.free_mb < body.checks.disk.threshold_mb);
      }
    } finally {
      config.health = savedHealth;
    }
  });

  test('public probe: reachable without credentials while auth is enabled', async () => {
    const protectedRes = await fetch(`${BASE}/api/history`);
    assert.equal(protectedRes.status, 401, 'auth guard is active for the rest of /api');

    const readyRes = await fetch(`${BASE}/api/health/ready`);
    assert.equal(readyRes.status, 200, 'probes carry no credentials');

    const liveRes = await fetch(`${BASE}/api/health`);
    assert.equal(liveRes.status, 200);
  });
});

// LAST describe on purpose: setShuttingDown flips a process-wide flag.
describe('graceful shutdown — liveness answers, readiness reports shutting down', () => {
  test('readiness 503 unavailable/shutting_down; liveness still 200 ok', async () => {
    lifecycleModule.setShuttingDown('health-test');
    try {
      const ready = await fetch(`${BASE}/api/health/ready`);
      assert.equal(ready.status, 503, 'readiness must fail while draining');
      const readyBody = await ready.json();
      assert.equal(readyBody.status, 'unavailable');
      assert.ok(readyBody.reasons.includes('shutting_down'));
      assert.equal(readyBody.checks.shutdown.status, 'error');
      assert.equal(readyBody.checks.database.status, 'ok', 'checks still run — the dependency is reported');

      const live = await fetch(`${BASE}/api/health`);
      assert.equal(live.status, 200, 'a liveness probe must be answered until the process is gone');
      const liveBody = await live.json();
      assert.equal(liveBody.status, 'ok');
      assert.equal(liveBody.checks.database.status, 'ok');

      const blocked = await fetch(`${BASE}/api/history`);
      assert.equal(blocked.status, 503, 'new work is refused while draining');
      assert.equal((await blocked.json()).code, 'SHUTTING_DOWN');
    } finally {
      lifecycleModule.setShuttingDown('health-test'); // idempotent — documents the process-wide flag
    }
  });
});
