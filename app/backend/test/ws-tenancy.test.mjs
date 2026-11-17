// WebSocket tenancy enforcement (P0-6 wave 3) — the socket's authenticated
// user is the viewer for every run/chat-scoped frame.
//
// Boots the REAL backend with auth ENABLED against an isolated DB (mock engine)
// and proves over real WebSocket connections that:
//   · the run catalog (list_runs / catalog_snapshot) is per owner — the admin
//     still sees both users, so the filter is privilege-aware, not blunt,
//   · foreign run snapshots and actions (get_run_snapshot / run_chat /
//     run_continue) are refused with the protocol's not-found error frame,
//   · subscribing to a foreign run is refused AND delivers none of that run's
//     events — proved with a sentinel event that demonstrably reaches the owner
//     over the same window,
//   · the per-viewer catalog broadcasts (catalog_update / run_updated) stay
//     filtered while a run really emits status events,
//   · the chat catalog hides foreign sessions and foreign chat subscribe /
//     send / stop are refused, while the owner's own subscription streams its
//     events.
//
// Everything this test creates (workspace run dirs, temp DB) is removed in
// after(). Debris is swept by the mock engine's `<ts>_<scene>` naming.

import { test, describe, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { spawn } from 'child_process';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { mkdtempSync, rmSync, readdirSync, existsSync } from 'fs';
import { tmpdir } from 'os';
import net from 'net';
import { WebSocket } from 'ws';

const here = dirname(fileURLToPath(import.meta.url));
const backendDir = join(here, '..');
const repoRoot = join(backendDir, '..', '..');
const RUNS_DIR = join(repoRoot, 'workspace', 'diagnostic-runs');

async function freePort() {
  return new Promise((resolve, reject) => {
    const srv = net.createServer();
    srv.once('error', reject);
    srv.listen(0, '127.0.0.1', () => {
      const { port } = srv.address();
      srv.close(() => resolve(port));
    });
  });
}
const PORT = await freePort();
const BASE = `http://127.0.0.1:${PORT}`;
const WS_URL = `ws://127.0.0.1:${PORT}/ws`;
const WORK = mkdtempSync(join(tmpdir(), 'idd-ws-tenancy-'));
const DB_PATH = join(WORK, 'ws-tenancy.db');
const PASSWORD = 'Secret12345';

// Mirror of WS_TOKEN_PROTOCOL in src/transport/ws-server.mjs — kept literal on
// purpose: importing that module here would boot a second engine/DB in-process.
const TOKEN_PROTOCOL = 'idd-token';

const SCENE_ALICE = 'ws_ten_alice';
const SCENE_BOB = 'ws_ten_bob';
const TEST_STARTED_MS = Date.now();

let server;
let serverLog = '';
const tok = { admin: '', alice: '', bob: '' };
let aliceRunId = '';
let bobRunId = '';
let aliceChatId = '';

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function waitHealthy(timeoutMs = 40000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const res = await fetch(`${BASE}/api/health`, { signal: AbortSignal.timeout(1500) });
      if (res.ok) return;
    } catch { /* not up yet */ }
    await sleep(400);
  }
  throw new Error(`server not healthy after ${timeoutMs}ms\n${serverLog.slice(-4000)}`);
}

async function api(method, path, { token, body } = {}) {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal: AbortSignal.timeout(30000),
  });
  let json = null;
  try { json = await res.json(); } catch { /* non-JSON */ }
  return { status: res.status, body: json };
}

async function startMockRun(token, scene) {
  const start = await api('POST', '/api/diagnosis/start', {
    token,
    body: { harness: 'mock', dataPath: 'data/smoke.csv', sceneName: scene, userQuestion: `ws tenancy ${scene}` },
  });
  assert.equal(start.status, 200, `start ${scene}: ${JSON.stringify(start.body)}`);
  const runId = start.body.data.runId;
  const exec = await api('POST', `/api/diagnosis/execute/${runId}`, { token });
  assert.ok([200, 409].includes(exec.status), `execute ${scene}: ${JSON.stringify(exec.body)}`);
  const deadline = Date.now() + 30000;
  while (Date.now() < deadline) {
    const st = await api('GET', `/api/diagnosis/status/${runId}`, { token });
    if (st.body?.data && ['completed', 'failed'].includes(st.body.data.status)) {
      assert.equal(st.body.data.status, 'completed', `run ${runId} status`);
      return runId;
    }
    await sleep(200);
  }
  throw new Error(`run ${runId} did not finish\n${serverLog.slice(-2000)}`);
}

// ─── WS client helpers ───────────────────────────────────────────────────────
function connect(token, label) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(WS_URL, [TOKEN_PROTOCOL, token]);
    ws.label = label;
    ws.inbox = [];
    ws.waiters = [];
    ws.on('message', (raw) => {
      let msg;
      try { msg = JSON.parse(raw.toString()); } catch { return; }
      const idx = ws.waiters.findIndex((w) => w.match(msg));
      if (idx >= 0) {
        const [w] = ws.waiters.splice(idx, 1);
        w.resolve(msg);
      } else {
        ws.inbox.push(msg);
      }
    });
    ws.once('open', () => resolve(ws));
    ws.once('error', reject);
  });
}

function send(ws, msg) {
  ws.send(JSON.stringify(msg));
}

/** Wait for a frame (string type or predicate), or fail after timeoutMs. */
function waitFor(ws, match, what, timeoutMs = 8000) {
  const predicate = typeof match === 'string' ? (m) => m.type === match : match;
  const idx = ws.inbox.findIndex(predicate);
  if (idx >= 0) return Promise.resolve(ws.inbox.splice(idx, 1)[0]);
  return new Promise((resolve, reject) => {
    const waiter = { match: predicate, resolve: (m) => { clearTimeout(timer); resolve(m); } };
    const timer = setTimeout(() => {
      const i = ws.waiters.indexOf(waiter);
      if (i >= 0) ws.waiters.splice(i, 1);
      reject(new Error(`${ws.label}: timed out waiting for ${what} (types in inbox: ${ws.inbox.map((m) => m.type).join(',') || 'none'})`));
    }, timeoutMs);
    ws.waiters.push(waiter);
  });
}

/** Consume everything buffered so far (used to bound "no leak" windows). */
function takeInbox(ws) {
  const frames = ws.inbox.slice();
  ws.inbox.length = 0;
  return frames;
}

const RUN_SCOPED_TYPES = ['run_event', 'run_snapshot', 'subscribed', 'run_updated'];

before(async () => {
  server = spawn(process.execPath, [join(backendDir, 'src', 'index.mjs')], {
    cwd: backendDir,
    env: {
      ...process.env,
      PORT: String(PORT),
      SERVER_PORT: String(PORT),
      DATABASE_PATH: DB_PATH,
      AUTH_ENABLED: '1',
      AUTH_JWT_SECRET: 'ws-tenancy-e2e-fixed-secret-0123456789abcd',
    },
    windowsHide: true,
  });
  server.stdout.on('data', (d) => { serverLog += d.toString(); });
  server.stderr.on('data', (d) => { serverLog += d.toString(); });
  await waitHealthy();

  // Bootstrap admin first (the first registration wins the admin role), then
  // two regular users: the admin is the positive control for every filter.
  for (const [name, username] of [['admin', 'ws_ten_admin'], ['alice', 'ws_ten_alice'], ['bob', 'ws_ten_bob']]) {
    const r = await api('POST', '/api/auth/register', { body: { username, password: PASSWORD } });
    assert.equal(r.status, 200, `${username} register: ${JSON.stringify(r.body)}`);
    tok[name] = r.body.data.session_token;
  }

  aliceRunId = await startMockRun(tok.alice, SCENE_ALICE);
  bobRunId = await startMockRun(tok.bob, SCENE_BOB);

  const chat = await api('POST', '/api/chat/start', {
    token: tok.alice,
    body: { harness: 'mock', prompt: 'ws tenancy chat' },
  });
  assert.equal(chat.status, 200, `chat start: ${JSON.stringify(chat.body)}`);
  aliceChatId = chat.body.data.chatId;
});

after(async () => {
  // Stop the mock chat the test started (it has no DB-linked run dir).
  if (aliceChatId) {
    try { await api('POST', `/api/chat/stop/${aliceChatId}`, { token: tok.alice, body: {} }); } catch { /* best effort */ }
  }
  // Sweep the mock engine's run dirs for this test's scenes...
  try {
    if (existsSync(RUNS_DIR)) {
      for (const entry of readdirSync(RUNS_DIR)) {
        if (entry.endsWith(`_${SCENE_ALICE}`) || entry.endsWith(`_${SCENE_BOB}`)) {
          rmSync(join(RUNS_DIR, entry), { recursive: true, force: true });
        }
        // ...and the `<ts>_chat` dir the mock chat turn creates (timestamped
        // after this file started, so parallel suites keep theirs).
        const chatDir = /^(\d+)_chat$/.exec(entry);
        if (chatDir && Number(chatDir[1]) >= TEST_STARTED_MS - 5000) {
          rmSync(join(RUNS_DIR, entry), { recursive: true, force: true });
        }
      }
    }
  } catch { /* best-effort debris cleanup */ }
  try { rmSync(WORK, { recursive: true, force: true }); } catch { /* windows lock */ }

  if (server && !server.killed) {
    server.kill();
    await sleep(300);
    try { spawn('taskkill', ['/pid', String(server.pid), '/T', '/F'], { windowsHide: true, stdio: 'ignore' }); } catch { /* ignore */ }
  }
});

// ─────────────────────────────────────────────────────────────────────────────

describe('WS run scope follows the socket identity', () => {
  let aliceWs;
  let bobWs;

  before(async () => {
    aliceWs = await connect(tok.alice, 'aliceWs');
    bobWs = await connect(tok.bob, 'bobWs');
    // Handshake frame for both (auth passed — no 4401 close).
    assert.equal((await waitFor(aliceWs, 'welcome', 'alice welcome')).type, 'welcome');
    assert.equal((await waitFor(bobWs, 'welcome', 'bob welcome')).type, 'welcome');
  });

  after(() => {
    for (const ws of [aliceWs, bobWs]) { try { ws.close(); } catch { /* already gone */ } }
  });

  test('run catalog is per owner; the admin still sees both users', async () => {
    send(bobWs, { type: 'list_runs' });
    const bobCatalog = await waitFor(bobWs, 'catalog_snapshot', 'bob catalog');
    const bobIds = bobCatalog.data.runs.map((r) => r.runId);
    assert.ok(bobIds.includes(bobRunId), 'bob sees his own run');
    assert.ok(!bobIds.includes(aliceRunId), 'bob must not see alice\'s run');

    send(aliceWs, { type: 'list_runs' });
    const aliceCatalog = await waitFor(aliceWs, 'catalog_snapshot', 'alice catalog');
    const aliceIds = aliceCatalog.data.runs.map((r) => r.runId);
    assert.ok(aliceIds.includes(aliceRunId), 'alice sees her own run');
    assert.ok(!aliceIds.includes(bobRunId), 'alice must not see bob\'s run');

    const adminWs = await connect(tok.admin, 'adminWs');
    try {
      await waitFor(adminWs, 'welcome', 'admin welcome');
      send(adminWs, { type: 'list_runs' });
      const adminCatalog = await waitFor(adminWs, 'catalog_snapshot', 'admin catalog');
      const adminIds = adminCatalog.data.runs.map((r) => r.runId);
      assert.ok(adminIds.includes(aliceRunId) && adminIds.includes(bobRunId),
        'the admin sees both users\' runs — the filter is privilege-aware');
    } finally {
      try { adminWs.close(); } catch { /* already gone */ }
    }
  });

  test('foreign snapshots and run actions are refused', async () => {
    send(bobWs, { type: 'get_run_snapshot', runId: aliceRunId });
    const snapshotRefusal = await waitFor(bobWs, 'error', 'bob snapshot refusal');
    assert.match(snapshotRefusal.data.message, /Run not found/);
    assert.equal(snapshotRefusal.data.runId, aliceRunId);

    send(bobWs, { type: 'run_chat', runId: aliceRunId, message: 'hijack' });
    const chatAck = await waitFor(bobWs, 'run_chat_ack', 'bob run_chat ack');
    assert.equal(chatAck.data.resumed, false, 'a foreign run chat is never resumed');
    const chatRefusal = await waitFor(bobWs, 'error', 'bob run_chat refusal');
    assert.match(chatRefusal.data.message, /Failed to send diagnosis chat message/);

    send(bobWs, { type: 'run_continue', runId: aliceRunId });
    const continueRefusal = await waitFor(bobWs, 'error', 'bob run_continue refusal');
    assert.match(continueRefusal.data.message, /Run not found/);

    // The owner's run is untouched by the refused actions...
    const status = await api('GET', `/api/diagnosis/status/${aliceRunId}`, { token: tok.alice });
    assert.equal(status.status, 200);
    assert.equal(status.body.data.status, 'completed');
    // ...and the refused chat message left no trace in the run's log.
    const Database = (await import('better-sqlite3')).default;
    const db = new Database(DB_PATH, { readonly: true });
    try {
      const hit = db.prepare("SELECT COUNT(*) AS c FROM diagnosis_logs WHERE run_id = ? AND content LIKE '%hijack%'").get(aliceRunId);
      assert.equal(hit.c, 0, 'the refused message must never reach the run log');
    } finally {
      db.close();
    }
  });

  test('subscribing to a foreign run is refused and leaks no events', async () => {
    send(bobWs, { type: 'subscribe_run', runId: aliceRunId });
    const refusal = await waitFor(bobWs, 'error', 'bob subscribe refusal');
    assert.match(refusal.data.message, /Run not found/);
    assert.deepEqual(takeInbox(bobWs).filter((m) => RUN_SCOPED_TYPES.includes(m.type)), [],
      'no run_snapshot / subscribed ack for a refused subscription');

    // Owner side: snapshot + ack + a live sentinel event on her own stream.
    send(aliceWs, { type: 'subscribe_run', runId: aliceRunId });
    const snapshot = await waitFor(aliceWs, 'run_snapshot', 'alice run_snapshot');
    assert.equal(snapshot.data.runId, aliceRunId);
    await waitFor(aliceWs, 'subscribed', 'alice subscribed ack');
    takeInbox(aliceWs); // drop the replayed history frames

    const SENTINEL = 'ws-tenancy sentinel';
    send(aliceWs, { type: 'run_chat', runId: aliceRunId, message: SENTINEL });
    const ack = await waitFor(aliceWs, 'run_chat_ack', 'alice run_chat ack');
    assert.equal(ack.data.resumed, true, 'the owner\'s run chat is resumed (mock session)');
    const sentinel = await waitFor(
      aliceWs,
      (m) => m.type === 'run_event' && m.data.runId === aliceRunId
        && m.data.event?.type === 'user_message' && m.data.event?.data?.content === SENTINEL,
      'owner receives the sentinel event',
    );
    assert.equal(sentinel.data.event.data.source, 'chat');

    // Same window, other socket: not a single run-scoped frame may appear.
    await sleep(900);
    const leaked = takeInbox(bobWs).filter((m) => RUN_SCOPED_TYPES.includes(m.type));
    assert.deepEqual(leaked, [], `bob received run-scoped frames for a foreign run: ${JSON.stringify(leaked).slice(0, 400)}`);
  });

  test('catalog broadcasts stay filtered while the run emits status events', async () => {
    send(aliceWs, { type: 'watch_catalog' });
    send(bobWs, { type: 'watch_catalog' });
    await waitFor(aliceWs, 'catalog_snapshot', 'alice catalog snapshot');
    await waitFor(bobWs, 'catalog_snapshot', 'bob catalog snapshot');
    takeInbox(aliceWs);
    takeInbox(bobWs);

    // A second execution of alice's run emits real `status` events, which drive
    // broadcastCatalogUpdate + broadcastRunStatusUpdate.
    send(aliceWs, { type: 'run_continue', runId: aliceRunId });
    await waitFor(aliceWs, 'run_continue_ack', 'alice run_continue ack');
    await waitFor(bobWs, 'catalog_update', 'bob catalog_update broadcast');

    await sleep(1200); // let the mock run finish emitting
    const bobFrames = takeInbox(bobWs);
    const bobUpdates = bobFrames.filter((m) => m.type === 'catalog_update');
    assert.ok(bobUpdates.length >= 1, 'bob really received catalog broadcasts');
    for (const update of bobUpdates) {
      const ids = update.data.runs.map((r) => r.runId);
      assert.ok(!ids.includes(aliceRunId), 'broadcast catalogs must not leak alice\'s run to bob');
      assert.ok(!update.data.activeRuns.includes(aliceRunId), 'nor its active-run entry');
    }
    assert.deepEqual(bobFrames.filter((m) => m.type === 'run_updated' && m.data.runId === aliceRunId), [],
      'no run_updated frame for a foreign run');

    const aliceFrames = takeInbox(aliceWs);
    const aliceUpdates = aliceFrames.filter((m) => m.type === 'catalog_update');
    assert.ok(aliceUpdates.some((m) => m.data.runs.map((r) => r.runId).includes(aliceRunId)),
      'alice\'s own broadcasts contain her run');
    assert.ok(aliceFrames.some((m) => m.type === 'run_updated' && m.data.runId === aliceRunId),
      'alice receives run_updated for her own run');
  });
});

describe('WS chat scope follows the socket identity', () => {
  let aliceWs;
  let bobWs;

  before(async () => {
    aliceWs = await connect(tok.alice, 'aliceChatWs');
    bobWs = await connect(tok.bob, 'bobChatWs');
    await waitFor(aliceWs, 'welcome', 'alice welcome');
    await waitFor(bobWs, 'welcome', 'bob welcome');
  });

  after(() => {
    for (const ws of [aliceWs, bobWs]) { try { ws.close(); } catch { /* already gone */ } }
  });

  test('chat catalog hides foreign sessions', async () => {
    send(bobWs, { type: 'get_chat_catalog' });
    const catalog = await waitFor(bobWs, 'chat_catalog_snapshot', 'bob chat catalog');
    assert.ok(!catalog.data.chats.some((c) => c.chatId === aliceChatId),
      'bob\'s chat catalog must not list alice\'s chat');
  });

  test('foreign chat subscribe / send / stop are refused; the owner streams events', async () => {
    // Bob: subscribe refused (a subscription would stream alice's chat events).
    send(bobWs, { type: 'subscribe_chat', chatId: aliceChatId });
    const subRefusal = await waitFor(bobWs, 'error', 'bob chat subscribe refusal');
    assert.match(subRefusal.data.message, /Chat not found/);
    assert.deepEqual(takeInbox(bobWs).filter((m) => m.type.startsWith('chat_snapshot') || m.type === 'chat_subscribed'), [],
      'no chat snapshot / subscription ack for a refused subscribe');

    // Bob: send refused (chat service answers a foreign chat like a missing one).
    send(bobWs, { type: 'chat_send', chatId: aliceChatId, message: 'hijack' });
    const sendRefusal = await waitFor(bobWs, 'error', 'bob chat send refusal');
    assert.match(sendRefusal.data.message, /not found/i);
    assert.deepEqual(takeInbox(bobWs).filter((m) => m.type === 'chat_sent'), [],
      'a refused send never acks as sent');

    // Bob: stop refused (false) and alice's chat survives it.
    send(bobWs, { type: 'chat_stop', chatId: aliceChatId });
    const stopAck = await waitFor(bobWs, 'chat_stopped', 'bob chat_stop ack');
    assert.equal(stopAck.data.stopped, false);

    // Owner: subscribe, then send — the sentinel proves events reach her socket.
    send(aliceWs, { type: 'subscribe_chat', chatId: aliceChatId });
    const snapshot = await waitFor(aliceWs, 'chat_snapshot', 'alice chat_snapshot');
    assert.equal(snapshot.data.chatId, aliceChatId);
    await waitFor(aliceWs, 'chat_subscribed', 'alice chat_subscribed ack');
    takeInbox(aliceWs);

    send(aliceWs, { type: 'chat_send', chatId: aliceChatId, message: 'ws-tenancy chat sentinel' });
    const sent = await waitFor(aliceWs, 'chat_sent', 'alice chat_sent ack');
    assert.equal(sent.data.chatId, aliceChatId);
    const live = await waitFor(
      aliceWs,
      (m) => m.type === 'chat_event' && m.data.chatId === aliceChatId,
      'alice receives a live chat event',
    );
    assert.ok(live.data.event, 'the forwarded chat event carries its payload');

    // Bob's window: no chat_event for alice's chat, before or after the send.
    await sleep(900);
    const leaked = takeInbox(bobWs).filter((m) => m.type === 'chat_event' || m.type === 'chat_snapshot');
    assert.deepEqual(leaked, [], `bob received chat frames for a foreign chat: ${JSON.stringify(leaked).slice(0, 400)}`);
  });
});
