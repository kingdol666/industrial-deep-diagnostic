import { after, before, test } from 'node:test';
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { mkdtempSync, rmSync } from 'node:fs';
import { createServer } from 'node:net';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import Database from 'better-sqlite3';

const backend = fileURLToPath(new URL('../', import.meta.url));
const dir = mkdtempSync(join(tmpdir(), 'idd-hitl-'));
const dbPath = join(dir, 'e2e.sqlite');
let server, base, owner, other, admin;
let logs = '';
const review = '/api/results/hitl-source/review';
const external = '/api/external/v1/results/hitl-source/review';

async function req(method, path, { session, body, apiToken } = {}) {
  const res = await fetch(`${base}${path}`, {
    method,
    headers: {
      'Content-Type': 'application/json', Origin: base,
      ...(session && { Cookie: session.cookie }),
      ...(apiToken && { Authorization: `Bearer ${apiToken}` }),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal: AbortSignal.timeout(5000),
  });
  return { status: res.status, body: await res.json(), cookie: res.headers.get('set-cookie')?.split(';')[0] };
}

before(async () => {
  const reservation = createServer().listen(0, '127.0.0.1');
  await once(reservation, 'listening');
  const { port } = reservation.address();
  await new Promise((resolve) => reservation.close(resolve));
  base = `http://127.0.0.1:${port}`;
  server = spawn(process.execPath, ['src/index.mjs'], {
    cwd: backend,
    env: { ...process.env, PORT: String(port), SERVER_PORT: String(port), DATABASE_PATH: dbPath, DATA_DIR: dir,
      AUTH_ENABLED: '1', AUTH_JWT_SECRET: 'isolated-hitl-test-signing-key-0123456789' },
    windowsHide: true,
  });
  server.stdout.on('data', (buf) => { logs += buf; });
  server.stderr.on('data', (buf) => { logs += buf; });
  let healthy = false;
  for (let i = 0; i < 100 && server.exitCode === null; i++) {
    try { if ((await req('GET', '/api/health')).status === 200) { healthy = true; break; } } catch { /* booting */ }
    await new Promise((resolve) => setTimeout(resolve, 200));
  }
  assert.ok(healthy, logs.slice(-3000));
  async function register(username) {
    const res = await req('POST', '/api/auth/register', { body: { username, password: 'IsolatedHitl123' } });
    assert.equal(res.status, 200);
    return { cookie: res.cookie, id: res.body.data.user.id };
  }
  admin = await register('hitl_admin');
  owner = await register('hitl_owner');
  other = await register('hitl_other');
  const db = new Database(dbPath);
  try {
    const insert = db.prepare(`INSERT INTO diagnostic_runs (run_id, name, scene_name, data_path, status, owner_user_id, user_id, harness)
      VALUES (?, ?, 'Demo Line', 'demo.csv', ?, ?, ?, 'claude')`);
    for (const [id, status, user] of [['hitl-source', 'completed', owner.id], ['hitl-target', 'pending', owner.id],
      ['hitl-foreign-target', 'pending', other.id]]) insert.run(id, id, status, user, String(user));
    db.prepare(`INSERT INTO analysis_results (result_id, run_id, intent, summary) VALUES
      ('hitl-source', 'hitl-source', 'deep-diagnosis', '自动报告：温度漂移与缺陷相关')`).run();
  } finally { db.close(); }
});

after(async () => {
  if (server?.exitCode === null && server?.signalCode === null) {
    const exit = once(server, 'exit');
    server.kill();
    await exit;
  }
  rmSync(dir, { recursive: true, force: true, maxRetries: 3 });
});

test('review lifecycle preserves the original, rejects stale writes, and governs reuse', async () => {
  const initial = await req('GET', review, { session: owner });
  assert.equal(initial.status, 200, JSON.stringify(initial.body));
  assert.equal(initial.body.data.status, 'unreviewed');
  assert.equal(initial.body.data.revision, 0);
  const update = async (revision, patch) => req('PATCH', review, { session: owner, body: { revision, ...patch } });
  const confirmed = await update(0, { status: 'confirmed', comment: '调整温控后缺陷率下降', takeaway: '先检查温控反馈' });
  assert.equal(confirmed.status, 200, JSON.stringify(confirmed.body));
  assert.equal(confirmed.body.data.revision, 1);
  assert.equal(confirmed.body.data.status, 'confirmed');
  assert.equal(confirmed.body.data.actor.username, 'hitl_owner');
  assert.match(confirmed.body.data.synthesis.text, /温度漂移与缺陷相关/);
  assert.match(confirmed.body.data.synthesis.text, /调整温控后缺陷率下降/);
  assert.equal((await req('GET', external, { session: owner })).body.data.status, 'confirmed');
  for (const id of ['hitl-target', 'hitl-foreign-target']) {
    const r = await req('GET', `/api/diagnosis/review-context/${id}`, { session: id === 'hitl-target' ? owner : other });
    assert.equal(r.status, 200);
    assert.deepEqual(r.body.data.map((x) => x.run_id), id === 'hitl-target' ? ['hitl-source'] : []);
    if (id === 'hitl-target') assert.match(r.body.data[0].takeaway, /先检查温控反馈/);
  }
  const edited = await update(1, { takeaway: '先检查测温校准', summary: '人工修订：优先校准测温' });
  assert.equal(edited.body.data.synthesis.source, 'human');
  assert.equal(edited.body.data.status, 'confirmed');
  assert.equal((await update(1, { status: 'ineffective' })).status, 409);
  const undone = await update(2, { status: 'unreviewed', summary: null });
  assert.equal(undone.body.data.status, 'unreviewed');
  assert.equal(undone.body.data.synthesis.source, 'derived');
  assert.deepEqual((await req('GET', '/api/diagnosis/review-context/hitl-target', { session: owner })).body.data, []);
  const ineffective = await update(3, { status: 'ineffective', comment: '对照批次未复现' });
  assert.equal(ineffective.body.data.status, 'ineffective');
  assert.equal(ineffective.body.data.comment, '对照批次未复现');
  assert.deepEqual((await req('GET', '/api/diagnosis/review-context/hitl-target', { session: owner })).body.data, []);
  const history = await req('GET', `${review}/history`, { session: owner });
  assert.deepEqual(history.body.data.map((x) => [x.revision, x.status]), [[4, 'ineffective'], [3, 'unreviewed'], [2, 'confirmed'], [1, 'confirmed']]);
  const details = await req('GET', '/api/results/hitl-source', { session: owner });
  assert.equal(details.body.data.summary, '自动报告：温度漂移与缺陷相关');
});

test('reviews respect ownership, completed status, and authenticated human authorship', async () => {
  assert.equal((await req('GET', review, { session: other })).status, 404);
  assert.equal((await req('GET', '/api/results/hitl-source', { session: other })).status, 404);
  const retained = await req('GET', '/api/line-memory/reviews?status=ineffective', { session: owner });
  assert.deepEqual(retained.body.data.items.map((item) => [item.run_id, item.status]), [['hitl-source', 'ineffective']]);
  assert.deepEqual((await req('GET', '/api/line-memory/reviews', { session: other })).body.data.items, []);
  assert.equal((await req('PATCH', external, { session: other, body: { revision: 4, status: 'confirmed' } })).status, 404);
  assert.equal((await req('GET', review, { session: admin })).status, 200);
  assert.equal((await req('PATCH', '/api/results/hitl-target/review', { session: owner, body: { revision: 0, status: 'confirmed' } })).status, 409);
  assert.equal((await req('PATCH', review, { session: owner, body: { revision: 4, status: 'fabricated' } })).status, 400);
  const token = await req('POST', '/api/auth/tokens', { session: owner, body: { name: 'machine client' } });
  assert.equal(token.status, 200);
  assert.equal((await req('PATCH', review, { apiToken: token.body.data.token, body: { revision: 4, status: 'confirmed' } })).status, 403);
});

test('re-completion and a manual reuse opt-out keep previously confirmed entries out of new context', async () => {
  const preview = '/api/diagnosis/review-context/hitl-target';
  const patch = (revision, body) => req('PATCH', review, { session: owner, body: { revision, ...body } });
  assert.equal((await patch(4, { status: 'confirmed', reuse_enabled: false })).status, 200);
  assert.deepEqual((await req('GET', preview, { session: owner })).body.data, []);
  assert.equal((await patch(5, { reuse_enabled: true })).status, 200);
  assert.equal((await req('GET', preview, { session: owner })).body.data[0].revision, 6);
  const db = new Database(dbPath);
  try {
    db.prepare("UPDATE diagnostic_runs SET completed_at = '2026-11-26 09:30:00' WHERE run_id = 'hitl-source'").run();
  } finally { db.close(); }
  assert.equal((await req('GET', review, { session: owner })).body.data.stale, true);
  assert.deepEqual((await req('GET', preview, { session: owner })).body.data, []);
  assert.equal((await patch(6, { status: 'confirmed' })).body.data.stale, false);
  assert.equal((await req('GET', preview, { session: owner })).body.data[0].revision, 7);
});
