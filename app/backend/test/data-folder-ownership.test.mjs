import { test, describe, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { spawn } from 'child_process';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { mkdtempSync, mkdirSync, writeFileSync, rmSync, symlinkSync } from 'fs';
import { tmpdir } from 'os';

const backendDir = join(dirname(fileURLToPath(import.meta.url)), '..');
const repoRoot = join(backendDir, '..', '..');
const workDir = mkdtempSync(join(tmpdir(), 'idd-data-folder-ownership-'));
const dataRel = `data/data-folder-ownership-${process.pid}-${Date.now()}`;
const dataDir = join(repoRoot, dataRel);
const dbPath = join(workDir, 'ownership.db');
const port = 3995;
const baseUrl = `http://127.0.0.1:${port}`;
const password = 'Secret12345';
const tokens = {};
let server;
let serverLog = '';
let aliceFolder;
let bobFolder;

async function waitHealthy(timeoutMs = 40000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const res = await fetch(`${baseUrl}/api/health`, { signal: AbortSignal.timeout(1500) });
      if (res.ok) return;
    } catch { /* wait for startup */ }
    await new Promise((resolve) => setTimeout(resolve, 300));
  }
  throw new Error(`server not healthy after ${timeoutMs}ms\n${serverLog.slice(-4000)}`);
}

async function api(method, path, { user, body, raw, headers = {} } = {}) {
  const res = await fetch(`${baseUrl}${path}`, {
    method,
    headers: {
      ...(raw ? {} : { 'Content-Type': 'application/json' }),
      ...(user ? { Authorization: `Bearer ${tokens[user]}` } : {}),
      ...headers,
    },
    body: body === undefined || raw ? body : JSON.stringify(body),
    signal: AbortSignal.timeout(15000),
  });
  let json = null;
  try { json = await res.json(); } catch { /* binary response */ }
  return { status: res.status, body: json, headers: res.headers };
}

function fileUrl(path) {
  return `/api/files/data/file/${path.split('/').map(encodeURIComponent).join('/')}`;
}

async function upload(user, folder, filename, contents = 'time,value\n0,1\n') {
  const form = new FormData();
  if (folder !== undefined) form.append('folder', folder);
  form.append('files', new Blob([contents], { type: 'text/csv' }), filename);
  // The multipart body must ride in `body`; `raw` only suppresses the JSON
  // content-type header — a bare `raw: form` sent a bodyless POST that the
  // old route silently answered 200 with nothing uploaded.
  return api('POST', '/api/files/data/upload', { user, body: form, raw: true });
}

before(async () => {
  server = spawn(process.execPath, [join(backendDir, 'src', 'index.mjs')], {
    cwd: backendDir,
    env: {
      ...process.env,
      PORT: String(port),
      SERVER_PORT: String(port),
      DATABASE_PATH: dbPath,
      DATA_DIR: dataRel,
      AUTH_ENABLED: '1',
      AUTH_JWT_SECRET: 'data-folder-ownership-test-secret-0123456789',
    },
    windowsHide: true,
  });
  server.stdout.on('data', (chunk) => { serverLog += chunk.toString(); });
  server.stderr.on('data', (chunk) => { serverLog += chunk.toString(); });
  await waitHealthy();

  for (const [key, username] of [['admin', 'df_admin'], ['alice', 'df_alice'], ['bob', 'df_bob']]) {
    const result = await api('POST', '/api/auth/register', {
      body: { username, password },
    });
    assert.equal(result.status, 200, `${username} registration: ${JSON.stringify(result.body)}`);
    tokens[key] = result.body.data.session_token;
  }

  aliceFolder = `df_alice_${process.pid}`;
  bobFolder = `df_bob_${process.pid}`;
  for (const [user, name] of [['alice', aliceFolder], ['bob', bobFolder]]) {
    const result = await api('POST', '/api/files/data/folder', { user, body: { name } });
    assert.equal(result.status, 200, `${name} creation: ${JSON.stringify(result.body)}`);
  }

  mkdirSync(join(dataDir, 'df_legacy_unregistered'), { recursive: true });
  writeFileSync(join(dataDir, 'df_root_private.csv'), 'root,private\n');
  writeFileSync(join(dataDir, 'df_legacy_unregistered', 'private.csv'), 'legacy,private\n');
  assert.equal((await upload('alice', aliceFolder, 'owned.csv')).status, 200);
});

after(async () => {
  if (server && !server.killed) {
    server.kill();
    await new Promise((resolve) => setTimeout(resolve, 300));
    try {
      spawn('taskkill', ['/pid', String(server.pid), '/T', '/F'], { windowsHide: true, stdio: 'ignore' });
    } catch { /* best-effort child cleanup */ }
  }
  try { rmSync(dataDir, { recursive: true, force: true }); } catch { /* best-effort fixture cleanup */ }
  try { rmSync(workDir, { recursive: true, force: true }); } catch { /* best-effort fixture cleanup */ }
});

describe('authenticated data-folder ownership', () => {
  test('root listing only returns the caller-owned registered folder and no root files', async () => {
    const alice = await api('GET', '/api/files/data', { user: 'alice' });
    assert.equal(alice.status, 200);
    assert.deepEqual(alice.body.data.map((entry) => entry.name), [aliceFolder]);

    const bob = await api('GET', '/api/files/data', { user: 'bob' });
    assert.equal(bob.status, 200);
    assert.deepEqual(bob.body.data.map((entry) => entry.name), [bobFolder]);
  });

  test('nested browse and folder list hide foreign and unregistered folders', async () => {
    for (const path of [
      `/api/files/data/${encodeURIComponent(aliceFolder)}`,
      `/api/files/data/browse?path=${encodeURIComponent(aliceFolder)}`,
      `/api/files/data/browse?path=${encodeURIComponent('df_legacy_unregistered')}`,
    ]) {
      const denied = await api('GET', path, { user: 'bob' });
      assert.equal(denied.status, 404, `${path} should be hidden: ${JSON.stringify(denied.body)}`);
    }

    const owner = await api('GET', `/api/files/data/${encodeURIComponent(aliceFolder)}`, { user: 'alice' });
    assert.equal(owner.status, 200);
    assert.ok(owner.body.data.some((entry) => entry.name === 'owned.csv'));
  });

  test('preview is owner-scoped and authenticated responses are not cacheable', async () => {
    const foreign = await api('GET', fileUrl(`${dataRel}/${aliceFolder}/owned.csv`), { user: 'bob' });
    assert.equal(foreign.status, 404);

    const rootFile = await api('GET', fileUrl(`${dataRel}/df_root_private.csv`), { user: 'alice' });
    assert.equal(rootFile.status, 404);

    const owner = await api('GET', fileUrl(`${dataRel}/${aliceFolder}/owned.csv`), { user: 'alice' });
    assert.equal(owner.status, 200);
    assert.equal(owner.body.data.content, 'time,value\n0,1\n');
    assert.match(owner.headers.get('cache-control') || '', /private/i);
    assert.match(owner.headers.get('cache-control') || '', /no-store/i);
  });

  test('upload requires an owned registered folder and leaves denied targets unchanged', async () => {
    const foreign = await upload('bob', aliceFolder, 'bob-attempt.csv');
    assert.equal(foreign.status, 404);

    const root = await upload('bob', undefined, 'root-attempt.csv');
    assert.equal(root.status, 404);

    const owner = await upload('alice', aliceFolder, 'alice-second.csv');
    assert.equal(owner.status, 200, JSON.stringify(owner.body));

    const aliceEntries = await api('GET', `/api/files/data/${encodeURIComponent(aliceFolder)}`, { user: 'alice' });
    assert.ok(aliceEntries.body.data.some((entry) => entry.name === 'alice-second.csv'));
    assert.ok(!aliceEntries.body.data.some((entry) => entry.name === 'bob-attempt.csv'));
  });

  test('admin retains access to legacy folders and files', async () => {
    const listing = await api('GET', '/api/files/data', { user: 'admin' });
    assert.equal(listing.status, 200);
    assert.ok(listing.body.data.some((entry) => entry.name === aliceFolder));
    assert.ok(listing.body.data.some((entry) => entry.name === bobFolder));
    assert.ok(listing.body.data.some((entry) => entry.name === 'df_legacy_unregistered'));

    const legacy = await api('GET', fileUrl(`${dataRel}/df_legacy_unregistered/private.csv`), { user: 'admin' });
    assert.equal(legacy.status, 200);
  });

  test('symlink paths are not listed or previewed as owned-folder content', async (t) => {
    const outsideDir = join(workDir, 'outside');
    mkdirSync(outsideDir, { recursive: true });
    writeFileSync(join(outsideDir, 'private.csv'), 'outside,private\n');
    try {
      symlinkSync(outsideDir, join(dataDir, aliceFolder, 'df_external_alias'), 'dir');
    } catch (err) {
      if (['EPERM', 'EACCES', 'ENOTSUP'].includes(err.code)) return t.skip(`directory symlinks unavailable: ${err.code}`);
      throw err;
    }

    const listing = await api('GET', `/api/files/data/${encodeURIComponent(aliceFolder)}`, { user: 'alice' });
    assert.equal(listing.status, 200);
    assert.ok(!listing.body.data.some((entry) => entry.name === 'df_external_alias'));

    const preview = await api('GET', fileUrl(`${dataRel}/${aliceFolder}/df_external_alias/private.csv`), { user: 'alice' });
    // Escape attempts answer the same 404 as missing content — symlinked
    // paths are never listed or previewed as owned-folder content.
    assert.equal(preview.status, 404);
    assert.equal(preview.body?.error, 'Data path not found');
  });
});
