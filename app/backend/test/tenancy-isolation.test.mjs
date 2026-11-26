// Multi-tenancy isolation e2e (P0-6 wave 2) — ownership filtering + RBAC.
//
// Boots the REAL backend with auth ENABLED against an isolated DB (and an
// isolated ontology store) and proves the isolation contract end to end:
//   - creation persists the creator's owner_user_id (run / chat / folder / log)
//   - user B gets 404 (never 403) on every read/act/delete of user A's run,
//     chat session, data folder and workspace artifacts — incl. via API token
//   - an admin can see and act on both users' rows; legacy NULL-owner rows are
//     visible to the admin only
//   - quota: a user's upload burst ends in 429 while another user is unaffected
//   - ontology destructive ops are admin-only (403 for a regular user)
//
// Everything the test creates (workspace run dirs, data folders, temp DBs) is
// removed in after().

import { test, describe, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { spawn } from 'child_process';
import { join, dirname, basename } from 'path';
import { fileURLToPath } from 'url';
import { mkdtempSync, writeFileSync, mkdirSync, rmSync, existsSync } from 'fs';
import { tmpdir } from 'os';

const here = dirname(fileURLToPath(import.meta.url));
const backendDir = join(here, '..');
const repoRoot = join(backendDir, '..', '..');
const RUNS_DIR = join(repoRoot, 'workspace', 'diagnostic-runs');
const DATA_DIR = join(repoRoot, 'data');

const PORT = 3993;
const BASE = `http://127.0.0.1:${PORT}`;
const WORK = mkdtempSync(join(tmpdir(), 'idd-tenancy-iso-'));
const DB_PATH = join(WORK, 'tenancy.db');
const STORE_DIR = join(WORK, 'ontology-store');

const PASSWORD = 'Secret12345';

let server;
let serverLog = '';

// Tokens for the four identities: bootstrap admin, two regular users and a
// burst user (rate-limit probe).
const tok = { admin: '', alice: '', bob: '', carol: '' };
const ids = { admin: null, alice: null, bob: null, carol: null };

// Resources created through the API.
let aliceRun = null;    // { runId, workspace }
let bobRun = null;
let bobExtTask = null;  // { taskId, runId }
let aliceChatId = null;
let legacyRunId = null;
let bobUploadFolder = '';
let aliceUploadFolder = '';

const createdDataDirs = new Set();

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

async function api(method, path, { token, body, headers, raw } = {}) {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: {
      ...(raw ? {} : { 'Content-Type': 'application/json' }),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(headers || {}),
    },
    body: body === undefined || raw ? body : JSON.stringify(body),
    signal: AbortSignal.timeout(30000),
  });
  let json = null;
  try { json = await res.json(); } catch { /* non-JSON (SSE, html) */ }
  return { status: res.status, body: json, headers: res.headers };
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
      AUTH_JWT_SECRET: 'tenancy-isolation-e2e-fixed-secret-0123456789',
      // Isolated ontology store: destructive-op probes must not touch the real one.
      ONTOLOGY_STORE_DIR: STORE_DIR,
    },
    windowsHide: true,
  });
  server.stdout.on('data', (d) => { serverLog += d.toString(); });
  server.stderr.on('data', (d) => { serverLog += d.toString(); });
  await waitHealthy();

  // Bootstrap admin first (first register wins the admin role), then users.
  for (const [name, username] of [['admin', 'iso_admin'], ['alice', 'iso_alice'], ['bob', 'iso_bob'], ['carol', 'iso_carol']]) {
    const r = await api('POST', '/api/auth/register', { body: { username, password: PASSWORD } });
    assert.equal(r.status, 200, `${username} register: ${JSON.stringify(r.body)}`);
    tok[name] = r.body.data.session_token;
    ids[name] = r.body.data.user.id;
  }
  assert.equal(ids.admin !== null && ids.alice !== null && ids.bob !== null && ids.carol !== null, true);
});

after(async () => {
  // Remove every workspace run dir this test created (mock runs write real dirs).
  try {
    if (existsSync(DB_PATH)) {
      const Database = (await import('better-sqlite3')).default;
      const db = new Database(DB_PATH, { readonly: true });
      const rows = db.prepare('SELECT workspace_path FROM diagnostic_runs WHERE workspace_path IS NOT NULL').all();
      db.close();
      for (const row of rows) {
        const dir = join(repoRoot, row.workspace_path);
        if (dir.startsWith(RUNS_DIR) && existsSync(dir)) rmSync(dir, { recursive: true, force: true });
      }
    }
  } catch { /* best-effort debris cleanup */ }
  for (const dir of createdDataDirs) {
    try { rmSync(dir, { recursive: true, force: true }); } catch { /* ignore */ }
  }
  try { rmSync(WORK, { recursive: true, force: true }); } catch { /* ignore */ }

  if (server && !server.killed) {
    server.kill();
    await new Promise((r) => setTimeout(r, 300));
    try { spawn('taskkill', ['/pid', String(server.pid), '/T', '/F'], { windowsHide: true, stdio: 'ignore' }); } catch { /* ignore */ }
  }
});

async function waitForRunStatus(runId, token, statuses, timeoutMs = 30000) {
  const deadline = Date.now() + timeoutMs;
  let last = null;
  while (Date.now() < deadline) {
    const { body } = await api('GET', `/api/diagnosis/status/${runId}`, { token });
    last = body?.data;
    if (statuses.includes(last?.status)) return last;
    await new Promise((r) => setTimeout(r, 300));
  }
  throw new Error(`run ${runId} did not reach ${statuses} (last: ${last?.status})\n${serverLog.slice(-2000)}`);
}

/** One mock-harness run: /start → /execute → wait for completion. */
async function createMockRun(token, sceneName) {
  const start = await api('POST', '/api/diagnosis/start', {
    token,
    body: { harness: 'mock', dataPath: 'data/smoke.csv', sceneName, userQuestion: `tenancy isolation ${sceneName}` },
  });
  assert.equal(start.status, 200, `start ${sceneName}: ${JSON.stringify(start.body)}`);
  const runId = start.body.data.runId;
  const exec = await api('POST', `/api/diagnosis/execute/${runId}`, { token });
  assert.ok([200, 409].includes(exec.status), `execute ${sceneName}: ${JSON.stringify(exec.body)}`);
  const run = await waitForRunStatus(runId, token, ['completed', 'failed']);
  assert.equal(run.status, 'completed', `run ${runId} status`);
  return { runId, workspace: run.workspace_path ? basename(run.workspace_path) : null };
}

// ─────────────────────────────────────────────────────────────────────────────

describe('creation persists ownership', () => {
  test('alice and bob each create a mock run; owner_user_id is the creator', async () => {
    aliceRun = await createMockRun(tok.alice, 'iso_alice');
    bobRun = await createMockRun(tok.bob, 'iso_bob');
    assert.ok(aliceRun.runId && bobRun.runId);
    assert.ok(aliceRun.workspace, 'alice run linked a workspace dir');

    const Database = (await import('better-sqlite3')).default;
    const db = new Database(DB_PATH, { readonly: true });
    try {
      const a = db.prepare('SELECT owner_user_id FROM diagnostic_runs WHERE run_id = ?').get(aliceRun.runId);
      const b = db.prepare('SELECT owner_user_id FROM diagnostic_runs WHERE run_id = ?').get(bobRun.runId);
      assert.equal(a.owner_user_id, ids.alice, 'alice owns her run');
      assert.equal(b.owner_user_id, ids.bob, 'bob owns his run');
      // diagnosis_logs inherit the run's owner (insertLog derives it from the run row)
      const logs = db.prepare('SELECT DISTINCT owner_user_id FROM diagnosis_logs WHERE run_id = ?').all(aliceRun.runId);
      assert.deepEqual(logs.map((l) => l.owner_user_id), [ids.alice], 'alice logs are owned by alice');
    } finally {
      db.close();
    }
  });
});

describe('run isolation — user B gets 404 on user A runs', () => {
  test('bob cannot see or act on alice\'s run through any diagnosis endpoint', async () => {
    const runId = aliceRun.runId;
    const cases = [
      ['GET', `/api/diagnosis/status/${runId}`],
      ['GET', `/api/diagnosis/snapshot/${runId}`],
      ['GET', `/api/diagnosis/session/${runId}`],
      ['GET', `/api/diagnosis/tasks/${runId}`],
      ['GET', `/api/diagnosis/stream/${runId}`],
      ['POST', `/api/diagnosis/stop/${runId}`],
      ['POST', `/api/diagnosis/execute/${runId}`],
      ['POST', `/api/diagnosis/continue/${runId}`],
      ['POST', `/api/diagnosis/enhance/${runId}`],
      ['GET', `/api/history/runs/${runId}`],
      ['DELETE', `/api/history/runs/${runId}`],
    ];
    for (const [method, path] of cases) {
      const r = await api(method, path, { token: tok.bob, body: method === 'POST' ? {} : undefined });
      assert.equal(r.status, 404, `${method} ${path} → expected 404, got ${r.status} ${JSON.stringify(r.body)}`);
    }

    // POST /chat answers 404 as well (run chat relay)
    const chat = await api('POST', `/api/diagnosis/chat/${runId}`, { token: tok.bob, body: { message: 'hi' } });
    assert.equal(chat.status, 404, JSON.stringify(chat.body));

    // POST /answer: the denial is indistinguishable from "no pending question"
    const answer = await api('POST', `/api/diagnosis/answer/${runId}`, {
      token: tok.bob, body: { questionId: 'q', toolUseId: 't', answers: { a: 'b' } },
    });
    assert.equal(answer.status, 404, JSON.stringify(answer.body));
  });

  test('bob\'s run list has his run but not alice\'s (and vice versa)', async () => {
    const bobList = await api('GET', '/api/diagnosis/list', { token: tok.bob });
    assert.equal(bobList.status, 200);
    const bobIds = bobList.body.data.map((r) => r.run_id);
    assert.ok(bobIds.includes(bobRun.runId), 'bob sees his own run');
    assert.ok(!bobIds.includes(aliceRun.runId), 'bob must not see alice\'s run');

    const aliceList = await api('GET', '/api/diagnosis/list', { token: tok.alice });
    const aliceIds = aliceList.body.data.map((r) => r.run_id);
    assert.ok(aliceIds.includes(aliceRun.runId));
    assert.ok(!aliceIds.includes(bobRun.runId));

    const historyAlice = await api('GET', '/api/history/runs', { token: tok.alice });
    const historyIds = historyAlice.body.data.map((r) => r.run_id);
    assert.ok(historyIds.includes(aliceRun.runId));
    assert.ok(!historyIds.includes(bobRun.runId));

    const aliceStatus = await api('GET', `/api/diagnosis/status/${aliceRun.runId}`, { token: tok.alice });
    assert.equal(aliceStatus.status, 200, 'the owner still reads her own run');
  });

  test('admin sees both runs; legacy NULL-owner run is admin-only', async () => {
    // Insert a legacy row (owner_user_id NULL = pre-migration / unowned).
    const Database = (await import('better-sqlite3')).default;
    legacyRunId = `legacy_${Date.now().toString(36)}`;
    const db = new Database(DB_PATH);
    try {
      db.prepare(
        `INSERT INTO diagnostic_runs (run_id, name, scene_name, data_path, owner_user_id)
         VALUES (?, ?, 'legacy_scene', 'data/smoke.csv', NULL)`,
      ).run(legacyRunId, legacyRunId);
    } finally {
      db.close();
    }

    const adminList = await api('GET', '/api/diagnosis/list', { token: tok.admin });
    const adminIds = adminList.body.data.map((r) => r.run_id);
    assert.ok(adminIds.includes(aliceRun.runId), 'admin sees alice\'s run');
    assert.ok(adminIds.includes(bobRun.runId), 'admin sees bob\'s run');
    assert.ok(adminIds.includes(legacyRunId), 'admin sees the legacy NULL-owner run');

    for (const who of ['alice', 'bob']) {
      const r = await api('GET', `/api/diagnosis/status/${legacyRunId}`, { token: tok[who] });
      assert.equal(r.status, 404, `${who} must not see the legacy run`);
      const del = await api('DELETE', `/api/history/runs/${legacyRunId}`, { token: tok[who] });
      assert.equal(del.status, 404, `${who} must not delete the legacy run`);
    }

    const adminSee = await api('GET', `/api/diagnosis/status/${legacyRunId}`, { token: tok.admin });
    assert.equal(adminSee.status, 200, 'admin reads the legacy run');
    const adminHistory = await api('GET', `/api/history/runs/${legacyRunId}`, { token: tok.admin });
    assert.equal(adminHistory.status, 200, 'admin reads legacy run logs');

    // B's earlier attempted DELETE on alice's run must not have removed it.
    const stillThere = await api('GET', `/api/diagnosis/status/${aliceRun.runId}`, { token: tok.alice });
    assert.equal(stillThere.status, 200, 'alice\'s run survived bob\'s DELETE attempt');
  });
});

describe('workspace artifacts follow the run owner', () => {
  test('bob is denied report/files/html/asset/preview/chart-data of alice\'s workspace', async () => {
    const ws = aliceRun.workspace;
    assert.ok(ws, 'a run dir name is available');

    const denied = [
      [`/api/files/workspace/report/${ws}`, 404],
      [`/api/files/workspace/optimizer/${ws}`, 404],
      [`/api/files/workspace/files/${ws}`, 404],
      [`/api/files/workspace/html/${ws}`, 404],
      [`/api/files/workspace/asset/${ws}/report.md`, 404],
      [`/api/files/data/file/workspace/diagnostic-runs/${ws}/report.md`, 404],
      [`/api/omp/runs/${ws}`, 404],
      [`/api/omp/runs/${ws}/summary`, 404],
      [`/api/omp/runs/${ws}/artifact/report`, 404],
    ];
    for (const [path, expected] of denied) {
      const r = await api('GET', path, { token: tok.bob });
      assert.equal(r.status, expected, `bob GET ${path} → ${r.status} ${JSON.stringify(r.body)}`);
    }

    const workspaceList = await api('GET', '/api/files/workspace', { token: tok.bob });
    assert.equal(workspaceList.status, 200);
    const names = workspaceList.body.data.map((r) => r.name);
    assert.ok(!names.includes(ws), 'alice\'s run dir is not listed for bob');

    // chart-data answers 200 + null (its documented "no data" shape) — never data.
    const chart = await api('GET', `/api/analysis/chart-data/${ws}`, { token: tok.bob });
    assert.equal(chart.status, 200);
    assert.equal(chart.body.data, null, 'no chart data leaks to a non-owner');

    // The owner and the admin still get the real artifacts.
    const ownerReport = await api('GET', `/api/files/workspace/report/${ws}`, { token: tok.alice });
    assert.equal(ownerReport.status, 200, JSON.stringify(ownerReport.body).slice(0, 200));
    const adminReport = await api('GET', `/api/files/workspace/report/${ws}`, { token: tok.admin });
    assert.equal(adminReport.status, 200);
    const ownerAsset = await api('GET', `/api/files/workspace/asset/${ws}/report.md`, { token: tok.alice });
    assert.equal(ownerAsset.status, 200);
  });
});

describe('data folders follow their creator', () => {
  test('bob cannot delete alice\'s folder; alice and the admin can', async () => {
    const name = `iso_folder_alice_${process.pid}`;
    const created = await api('POST', '/api/files/data/folder', { token: tok.alice, body: { name } });
    assert.equal(created.status, 200, JSON.stringify(created.body));
    createdDataDirs.add(join(DATA_DIR, name));

    const bobDelete = await api('DELETE', `/api/files/data/folder/${name}`, { token: tok.bob });
    assert.equal(bobDelete.status, 404, 'foreign folder delete must answer 404');

    const Database = (await import('better-sqlite3')).default;
    const db = new Database(DB_PATH, { readonly: true });
    try {
      const row = db.prepare('SELECT owner_user_id FROM data_folders WHERE name = ?').get(name);
      assert.equal(row.owner_user_id, ids.alice, 'folder row carries the creator');
    } finally {
      db.close();
    }

    const ownerDelete = await api('DELETE', `/api/files/data/folder/${name}`, { token: tok.alice });
    assert.equal(ownerDelete.status, 200, JSON.stringify(ownerDelete.body));
    createdDataDirs.delete(join(DATA_DIR, name));

    // The admin may delete another user's folder.
    const name2 = `iso_folder_bob_${process.pid}`;
    const created2 = await api('POST', '/api/files/data/folder', { token: tok.bob, body: { name: name2 } });
    assert.equal(created2.status, 200, JSON.stringify(created2.body));
    createdDataDirs.add(join(DATA_DIR, name2));
    const adminDelete = await api('DELETE', `/api/files/data/folder/${name2}`, { token: tok.admin });
    assert.equal(adminDelete.status, 200, 'admin reaches other users\' folders');
    createdDataDirs.delete(join(DATA_DIR, name2));
  });
});

describe('chat sessions follow their creator', () => {
  test('alice starts a chat; bob gets 404 on every session endpoint', async () => {
    const start = await api('POST', '/api/chat/start', {
      token: tok.alice,
      body: { harness: 'mock', prompt: 'tenancy isolation chat' },
    });
    assert.equal(start.status, 200, JSON.stringify(start.body));
    aliceChatId = start.body.data.chatId;
    assert.ok(aliceChatId);

    const Database = (await import('better-sqlite3')).default;
    const db = new Database(DB_PATH, { readonly: true });
    try {
      const row = db.prepare('SELECT owner_user_id FROM chat_sessions WHERE chat_id = ?').get(aliceChatId);
      assert.equal(row.owner_user_id, ids.alice, 'chat_sessions.owner_user_id is the creator');
    } finally {
      db.close();
    }

    const denied = [
      ['GET', `/api/chat/session/${aliceChatId}`],
      ['GET', `/api/chat/history/${aliceChatId}`],
      ['POST', `/api/chat/stop/${aliceChatId}`],
      ['DELETE', `/api/chat/session/${aliceChatId}`],
    ];
    for (const [method, path] of denied) {
      const r = await api(method, path, { token: tok.bob, body: method === 'DELETE' || method === 'POST' ? {} : undefined });
      assert.equal(r.status, 404, `bob ${method} ${path} → ${r.status} ${JSON.stringify(r.body)}`);
    }
    const rename = await api('PATCH', `/api/chat/session/${aliceChatId}`, { token: tok.bob, body: { title: 'hijack' } });
    assert.equal(rename.status, 404, JSON.stringify(rename.body));
    const config = await api('PATCH', `/api/chat/session/${aliceChatId}/config`, { token: tok.bob, body: { title: 'hijack' } });
    assert.equal(config.status, 404, JSON.stringify(config.body));
    // send resumes/starts a chat — a foreign session must not be resumable
    const send = await api('POST', `/api/chat/send/${aliceChatId}`, { token: tok.bob, body: { message: 'hi' } });
    assert.equal(send.status, 404, JSON.stringify(send.body));
    // info answers the same neutral shape as for an unknown chat (no title leak)
    const info = await api('GET', `/api/chat/info/${aliceChatId}`, { token: tok.bob });
    assert.equal(info.status, 200);
    assert.equal(info.body.data.active, false);
    assert.equal(info.body.data.title, undefined, 'no session metadata leaks');
    // SSE stream: replay path is gated too
    const stream = await api('GET', `/api/chat/stream/${aliceChatId}`, { token: tok.bob });
    assert.equal(stream.status, 404);

    const bobList = await api('GET', '/api/chat/list', { token: tok.bob });
    assert.equal(bobList.status, 200);
    assert.ok(!bobList.body.data.some((c) => c.chatId === aliceChatId), 'bob\'s chat list hides alice\'s chat');

    const ownerSession = await api('GET', `/api/chat/session/${aliceChatId}`, { token: tok.alice });
    assert.equal(ownerSession.status, 200, 'the owner reads her chat');
    const adminSession = await api('GET', `/api/chat/session/${aliceChatId}`, { token: tok.admin });
    assert.equal(adminSession.status, 200, 'admin reads any chat');
    const adminList = await api('GET', '/api/chat/list', { token: tok.admin });
    assert.ok(adminList.body.data.some((c) => c.chatId === aliceChatId), 'admin list contains it');
  });
});

describe('external API binds to the token\'s user', () => {
  test('bob\'s token gets 404 on alice\'s run; his own analysis works', async () => {
    const bobTokenRes = await api('POST', '/api/auth/tokens', { token: tok.bob, body: { name: 'iso-bob-ext' } });
    assert.equal(bobTokenRes.status, 200, JSON.stringify(bobTokenRes.body));
    const bobToken = bobTokenRes.body.data.token;
    const aliceTokenRes = await api('POST', '/api/auth/tokens', { token: tok.alice, body: { name: 'iso-alice-ext' } });
    const aliceToken = aliceTokenRes.body.data.token;

    const denied = [
      ['GET', `/api/external/v1/analyze/${aliceRun.runId}`],
      ['GET', `/api/external/v1/analyze/${aliceRun.runId}/stream`],
      ['GET', `/api/external/v1/tasks/${aliceRun.runId}`],
      ['GET', `/api/external/v1/tasks/${aliceRun.runId}/result`],
    ];
    for (const [method, path] of denied) {
      const r = await api(method, path, { token: bobToken });
      assert.equal(r.status, 404, `bob token ${method} ${path} → ${r.status} ${JSON.stringify(r.body)}`);
    }
    const stop = await api('POST', `/api/external/v1/analyze/${aliceRun.runId}/stop`, { token: bobToken, body: {} });
    assert.equal(stop.status, 404, JSON.stringify(stop.body));
    const chat = await api('POST', '/api/external/v1/chat', { token: bobToken, body: { run_id: aliceRun.runId, message: 'hi' } });
    assert.equal(chat.status, 404, JSON.stringify(chat.body));

    // Bob's own external analysis is created, visible and pollable for him.
    const analyze = await api('POST', '/api/external/v1/analyze', {
      token: bobToken,
      body: { harness: 'mock', dataPath: 'data/smoke.csv', sceneName: 'iso_ext_bob', question: 'external tenancy' },
    });
    assert.equal(analyze.status, 202, JSON.stringify(analyze.body));
    bobExtTask = { taskId: analyze.body.data.task_id, runId: analyze.body.data.run_id };

    const ownTask = await api('GET', `/api/external/v1/tasks/${bobExtTask.taskId}`, { token: bobToken });
    assert.equal(ownTask.status, 200, JSON.stringify(ownTask.body).slice(0, 200));

    // Another user's session token must not see bob's task either.
    const foreignTask = await api('GET', `/api/external/v1/tasks/${bobExtTask.taskId}`, { token: aliceToken });
    assert.equal(foreignTask.status, 404, 'cross-user task lookup is a 404');

    const bobTasks = await api('GET', '/api/external/v1/tasks', { token: bobToken });
    assert.equal(bobTasks.status, 200);
    assert.ok(bobTasks.body.data.some((t) => t.task_id === bobExtTask.taskId));
    assert.ok(!bobTasks.body.data.some((t) => t.run_id === aliceRun.runId), 'alice\'s run is not in bob\'s task list');
  });
});

describe('quota + RBAC', () => {
  test('bob\'s upload burst ends in 429 while another user is unaffected', async () => {
    bobUploadFolder = `iso_uploads_bob_${process.pid}`;
    createdDataDirs.add(join(DATA_DIR, bobUploadFolder));
    const folder = await api('POST', '/api/files/data/folder', { token: tok.bob, body: { name: bobUploadFolder } });
    assert.equal(folder.status, 200, JSON.stringify(folder.body));

    // Uploads are owner-scoped now: each user bursts against their OWN folder.
    aliceUploadFolder = `iso_uploads_alice_${process.pid}`;
    createdDataDirs.add(join(DATA_DIR, aliceUploadFolder));
    const aliceFolderRow = await api('POST', '/api/files/data/folder', { token: tok.alice, body: { name: aliceUploadFolder } });
    assert.equal(aliceFolderRow.status, 200, JSON.stringify(aliceFolderRow.body));

    const uploadOnce = async (token, folderName) => {
      const form = new FormData();
      form.append('folder', folderName);
      form.append('files', new Blob([`x,u\n1,2\n`], { type: 'text/csv' }), `iso_${Math.random().toString(36).slice(2)}.csv`);
      const res = await fetch(`${BASE}/api/files/data/upload`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: form,
        signal: AbortSignal.timeout(20000),
      });
      let json = null;
      try { json = await res.json(); } catch { /* ignore */ }
      return { status: res.status, body: json, headers: res.headers };
    };

    let blocked = null;
    for (let i = 0; i < 30 && !blocked; i += 1) {
      const r = await uploadOnce(tok.bob, bobUploadFolder);
      if (r.status === 429) blocked = r;
      else assert.equal(r.status, 200, `upload ${i + 1} → ${r.status} ${JSON.stringify(r.body)}`);
    }
    assert.ok(blocked, 'the upload burst must hit the per-user quota (429)');
    assert.equal(blocked.body.code, 'RATE_LIMITED');
    assert.ok(Number(blocked.headers.get('retry-after')) >= 1);
    assert.equal(blocked.body.success, false);

    // Per-user budget: alice is not affected by bob's exhausted window.
    const aliceUpload = await uploadOnce(tok.alice, aliceUploadFolder);
    assert.equal(aliceUpload.status, 200, `alice upload → ${aliceUpload.status} ${JSON.stringify(aliceUpload.body)}`);
  });

  test('diagnosis start quota is per user (burst user only)', async () => {
    const body = { harness: 'mock', dataPath: 'data/smoke.csv', sceneName: 'iso_burst', userQuestion: 'quota probe' };
    let allowed = 0;
    let blocked = null;
    for (let i = 0; i < 14 && !blocked; i += 1) {
      const r = await api('POST', '/api/diagnosis/start', { token: tok.carol, body });
      if (r.status === 429) { blocked = r; break; }
      assert.equal(r.status, 200, `carol start ${i + 1} → ${r.status} ${JSON.stringify(r.body)}`);
      allowed += 1;
      // /start alone never spawns an engine; close the probe run so no stale
      // pending rows pile up (they would matter only after the 24h expiry).
      await api('POST', `/api/diagnosis/stop/${r.body.data.runId}`, { token: tok.carol });
    }
    assert.ok(blocked, `carol must hit the start quota (allowed ${allowed} first)`);
    assert.ok(allowed >= 8, `quota must allow a sane burst (allowed ${allowed})`);
    assert.equal(blocked.body.code, 'RATE_LIMITED');
    assert.ok(Number(blocked.headers.get('retry-after')) >= 1);

    // Bob's budget is separate: he can still start a run.
    const bobStart = await api('POST', '/api/diagnosis/start', { token: tok.bob, body: { ...body, sceneName: 'iso_bob_after_quota' } });
    assert.equal(bobStart.status, 200, `bob after carol's burst: ${bobStart.status} ${JSON.stringify(bobStart.body)}`);
    await api('POST', `/api/diagnosis/stop/${bobStart.body.data.runId}`, { token: tok.bob });
  });

  test('ontology destructive operations are admin-only', async () => {
    // Alice may publish a scene (publish/reuse stay user-level)...
    const scene = `iso_tenancy_scene_${process.pid}`;
    const publish = await api('POST', '/api/ontology/assets', {
      token: tok.alice,
      body: { scene_key: scene, process_type: 'tenancy probe', objective: 'RBAC check' },
    });
    assert.equal(publish.status, 201, JSON.stringify(publish.body).slice(0, 300));
    const version = publish.body.data.version;

    // ...but bob must not delete/deprecate/clone/adopt.
    const destructive = [
      ['DELETE', `/api/ontology/assets/${scene}/${version}`, undefined],
      ['DELETE', `/api/ontology/scenes/${scene}`, undefined],
      ['POST', `/api/ontology/assets/${scene}/${version}/clone`, { target_scene: `${scene}_copy` }],
      ['POST', '/api/ontology/adopt', { runName: 'nonexistent-run-for-rbac' }],
      ['PATCH', `/api/ontology/assets/${scene}/${version}`, { quality: 'deprecated' }],
    ];
    for (const [method, path, body] of destructive) {
      const r = await api(method, path, { token: tok.bob, body });
      assert.equal(r.status, 403, `bob ${method} ${path} → ${r.status} ${JSON.stringify(r.body)}`);
      assert.equal(r.body.code, 'FORBIDDEN');
    }

    // The scene is intact after bob's attempts...
    const stillThere = await api('GET', `/api/ontology/assets/${scene}/${version}`, { token: tok.bob });
    assert.equal(stillThere.status, 200, 'bob may still READ the published scene');

    // ...and the admin can remove it.
    const adminDelete = await api('DELETE', `/api/ontology/scenes/${scene}`, { token: tok.admin });
    assert.equal(adminDelete.status, 200, JSON.stringify(adminDelete.body));

    // Metadata edit (non-destructive) remains user-level for the owner.
    const scene2 = `iso_tenancy_scene2_${process.pid}`;
    const publish2 = await api('POST', '/api/ontology/assets', { token: tok.alice, body: { scene_key: scene2 } });
    assert.equal(publish2.status, 201, JSON.stringify(publish2.body).slice(0, 200));
    const meta = await api('PATCH', `/api/ontology/assets/${scene2}/${publish2.body.data.version}`, {
      token: tok.bob, body: { notes: 'peer metadata edit' },
    });
    assert.notEqual(meta.status, 403, 'plain metadata edits are not admin-gated');
    await api('DELETE', `/api/ontology/scenes/${scene2}`, { token: tok.admin });
  });
});
