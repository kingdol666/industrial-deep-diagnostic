import { after, test } from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { once } from 'node:events';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, relative } from 'node:path';
import { setTimeout as delay } from 'node:timers/promises';
import Database from 'better-sqlite3';
import express from 'express';

const dir = mkdtempSync(join(tmpdir(), 'idd-production-lines-'));
process.env.DATABASE_PATH = join(dir, 'test.sqlite');
process.env.DATA_DIR = dir;
process.env.LINE_MEMORY_DIR = join(dir, 'legacy-memory');
process.env.AUTH_ENABLED = '1';
process.env.AUTH_JWT_SECRET = 'production-line-test-isolated-signing-key';

const { config, PROJECT_ROOT } = await import('../../../config/loader.mjs');
const workspace = mkdtempSync(join(PROJECT_ROOT, '.tmp-test-line-workspace-'));
config.data.workspace_dir = relative(PROJECT_ROOT, workspace);
config.engine.close_run_delay_seconds = 0;
const { db, stmts } = await import('../src/db/database.mjs');
const { MIGRATIONS, runMigrations } = await import('../src/db/migrations.mjs');
const { authGuard } = await import('../src/middleware/auth.middleware.mjs');
const { signJwt, createApiToken } = await import('../src/services/auth.service.mjs');
const { createLine, requireLineAction, requireRunKnowledgeScope, normalizeKnowledgeBinding } =
  await import('../src/services/production-line.service.mjs');

after(() => {
  db.close();
  for (const path of [dir, workspace]) rmSync(path, { recursive: true, force: true, maxRetries: 3 });
});

const user = (id, role = 'user') => ({ id, role, username: `line_user_${id}` });
const alice = user(101), bob = user(102), admin = user(103, 'admin');
for (const actor of [alice, bob, admin]) {
  db.prepare('INSERT INTO users (id, username, password_hash, role) VALUES (?, ?, ?, ?)')
    .run(actor.id, actor.username, 'test-only', actor.role);
}

function insertRun(runId, { owner = alice.id, userId = owner, status = 'completed' } = {}) {
  db.prepare(`INSERT INTO diagnostic_runs (run_id, name, scene_name, data_path, status, owner_user_id, user_id)
    VALUES (?, ?, '仅展示别名', 'data.csv', ?, ?, ?)`).run(runId, runId, status, owner, userId == null ? null : String(userId));
}

test('v7 adds nullable scope without changing a v6 legacy run or its review', () => {
  const legacy = new Database(':memory:');
  try {
    const migrateThrough = (version) => runMigrations(legacy, { migrations: MIGRATIONS.filter((m) => m.version <= version), log: null });
    migrateThrough(6);
    legacy.exec(`INSERT INTO diagnostic_runs (run_id, name, scene_name, data_path, user_id, owner_user_id)
      VALUES ('old', 'keep me', 'same name', 'historic.csv', '2', 1);
      INSERT INTO diagnosis_review_revisions (run_id, revision, status, original_summary, reuse_enabled, actor_id, actor_username, created_at)
      VALUES ('old', 1, 'confirmed', 'untouched', 1, 1, 'historic', '2026-11-25');`);
    assert.deepEqual(migrateThrough(7).applied, [7]);
    const run = legacy.prepare('SELECT line_id, knowledge_policy_json, dataset_refs_json, owner_user_id, user_id, name FROM diagnostic_runs').get();
    assert.deepEqual(run, { line_id: null, knowledge_policy_json: null, dataset_refs_json: null, owner_user_id: 1, user_id: '2', name: 'keep me' });
    assert.equal(legacy.prepare('SELECT original_summary FROM diagnosis_review_revisions').pluck().get(), 'untouched');
    assert.equal(legacy.prepare('SELECT COUNT(*) FROM production_lines').pluck().get(), 0);
  } finally { legacy.close(); }
});

test('unbound or ambiguous legacy runs cannot acquire knowledge scope by alias or alternate ownership', () => {
  const { line_id } = createLine(bob, { name: '仅展示别名' });
  assert.throws(() => requireLineAction(alice, line_id, 'read'), { code: 'LINE_NOT_FOUND' });
  assert.throws(() => requireLineAction(bob, '仅展示别名', 'read'), { code: 'LINE_NOT_FOUND' });
  assert.deepEqual(normalizeKnowledgeBinding(bob, line_id), {
    lineId: line_id, knowledgePolicy: { mode: 'on_demand', own_line: true, references: [] }, datasetRefs: [],
  });
  insertRun('legacy-owner');
  assert.deepEqual(requireRunKnowledgeScope(alice, 'legacy-owner'), {
    run_id: 'legacy-owner', line_id: null, owner_user_id: alice.id, knowledge_policy: null, dataset_refs: null,
  });
  insertRun('legacy-conflict', { userId: bob.id });
  insertRun('legacy-unknown', { owner: null, userId: alice.id });
  for (const [actor, run] of [[alice, 'legacy-conflict'], [bob, 'legacy-conflict'], [alice, 'legacy-unknown']]) {
    assert.throws(() => requireRunKnowledgeScope(actor, run), { code: 'RUN_NOT_FOUND' });
  }
});

test('HTTP APIs enforce membership, create-time line binding, alias isolation, and legacy admin gates', async () => {
  const app = express();
  app.use(express.json());
  app.use('/api', authGuard);
  const { getConcurrencySnapshot } = await import('../src/services/diagnosis.service.mjs');
  const [{ default: lines }, { default: diagnosis }, { default: externalRoutes }, { default: lineMemory }] = await Promise.all([
    import('../src/routes/production-line.routes.mjs'),
    import('../src/routes/diagnosis.routes.mjs'),
    import('../src/routes/external.routes.mjs'),
    import('../src/routes/line-memory.routes.mjs'),
  ]);
  app.use('/api/lines', lines);
  app.use('/api/diagnosis', diagnosis);
  app.use('/api/external', externalRoutes);
  app.use('/api/line-memory', lineMemory);
  const server = createServer(app).listen(0, '127.0.0.1');
  await once(server, 'listening');
  const base = `http://127.0.0.1:${server.address().port}`;
  let externalRunId = null;
  const req = async (actor, method, path, body) => {
    const response = await fetch(`${base}${path}`, {
      method,
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${typeof actor === 'string' ? actor : signJwt({ sub: actor.id, type: 'session' }, 60)}` },
      signal: AbortSignal.timeout(5000),
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    return { status: response.status, body: await response.json() };
  };
  try {
    const one = await req(alice, 'POST', '/api/lines', { name: 'HTTP同名线' });
    const two = await req(alice, 'POST', '/api/lines', { name: 'HTTP同名线' });
    assert.equal(one.status, 201);
    assert.equal(two.status, 201);
    const lineId = one.body.data.line_id;
    assert.notEqual(lineId, two.body.data.line_id);

    const aliases = await req(alice, 'PATCH', `/api/lines/${lineId}`, { aliases: ['仅展示别名'] });
    assert.deepEqual(aliases.body.data.aliases, ['仅展示别名']);
    assert.equal((await req(alice, 'GET', '/api/lines', undefined)).body.data.length, 2);
    assert.deepEqual((await req(admin, 'GET', '/api/lines', undefined)).body.data, [], 'site admin does not bypass line membership');
    assert.equal((await req(alice, 'GET', '/api/lines/仅展示别名/members', undefined)).status, 404);

    const member = await req(alice, 'PUT', `/api/lines/${lineId}/members/${bob.id}`, { role: 'read' });
    assert.equal(member.status, 200);
    assert.equal(member.body.data.role, 'read');
    assert.equal((await req(bob, 'PUT', `/api/lines/${lineId}/members/${bob.id}`, { role: 'manage' })).status, 403);
    assert.equal((await req(alice, 'PUT', `/api/lines/${lineId}/members/${alice.id}`, { role: 'read' })).status, 409);
    assert.equal((await req(alice, 'DELETE', `/api/lines/${lineId}/members/${alice.id}`)).status, 409);
    const policy = { mode: 'disabled', own_line: false, references: [] };
    const deniedBody = {
      dataPath: 'config/default.yaml', harness: 'mock', lineId,
      knowledgePolicy: policy, analysisIntent: 'deep-diagnosis',
    };
    assert.equal((await req(bob, 'POST', '/api/diagnosis/start', deniedBody)).status, 403);
    assert.equal((await req(bob, 'POST', '/api/external/v1/analyze', deniedBody)).status, 403);

    const created = await req(alice, 'POST', '/api/diagnosis/start', deniedBody);
    assert.equal(created.status, 200, JSON.stringify(created.body));
    assert.equal(created.body.data.line_id, lineId);
    assert.deepEqual(created.body.data.knowledge_policy, policy);
    const stored = stmts.getRunById.get(created.body.data.runId);
    assert.equal(stored.line_id, lineId);
    assert.deepEqual(JSON.parse(stored.knowledge_policy_json), policy);
    assert.deepEqual(JSON.parse(stored.dataset_refs_json), []);

    const externalBody = { ...deniedBody, sceneName: 'external-bound-line' };
    const apiToken = createApiToken(alice, { name: 'line integration test' }).token;
    const external = await req(apiToken, 'POST', '/api/external/v1/analyze', externalBody);
    assert.equal(external.status, 202, JSON.stringify(external.body));
    externalRunId = external.body.data.run_id;
    const externalRun = stmts.getRunById.get(externalRunId);
    assert.equal(externalRun.line_id, lineId);
    assert.deepEqual(JSON.parse(externalRun.knowledge_policy_json), policy);

    insertRun('legacy-http');
    assert.deepEqual((await req(alice, 'GET', '/api/diagnosis/review-context/legacy-http')).body.data, []);
    assert.equal(stmts.getRunById.get('legacy-http').line_id, null);
    assert.equal((await req(bob, 'GET', '/api/lines/legacy-runs')).status, 403);
    assert.ok((await req(admin, 'GET', '/api/lines/legacy-runs')).body.data.some((entry) => entry.run_id === 'legacy-http'));
    assert.equal((await req(alice, 'POST', `/api/lines/${lineId}/legacy-runs/legacy-conflict/bind`, {})).status, 409);
    assert.equal((await req(alice, 'POST', `/api/lines/${lineId}/legacy-runs/${created.body.data.runId}/bind`, {})).status, 409);
    const bound = await req(alice, 'POST', `/api/lines/${lineId}/legacy-runs/legacy-http/bind`, {});
    assert.equal(bound.status, 200, JSON.stringify(bound.body));
    assert.equal(stmts.getRunById.get('legacy-http').line_id, lineId);
    const audit = await req(alice, 'GET', `/api/lines/${lineId}/legacy-bindings`, undefined);
    assert.ok(audit.body.data.some((entry) => entry.run_id === 'legacy-http'));
    assert.equal(requireRunKnowledgeScope(alice, 'legacy-http').line_id, lineId);

    for (const path of ['/api/line-memory/lines', '/api/line-memory/lines/anything',
      '/api/line-memory/lines/anything/findings', '/api/line-memory/lines/anything/ontology',
      '/api/line-memory/proposals']) {
      assert.equal((await req(bob, 'GET', path, undefined)).status, 403, `${path} must require admin`);
    }
    assert.equal((await req(admin, 'GET', '/api/line-memory/lines')).status, 200);
    assert.equal((await req(admin, 'GET', '/api/line-memory/proposals')).status, 200);
  } finally {
    await new Promise((resolve) => server.close(resolve));
    // External analyze acknowledges before the mock engine or its cleanup ends.
    const deadline = Date.now() + 5000;
    while (Date.now() < deadline) {
      const { executing, queued } = getConcurrencySnapshot();
      if (!executing.length && !queued.length) break;
      await delay(20);
    }
    const { executing, queued } = getConcurrencySnapshot();
    assert.deepEqual([...executing, ...queued], [], 'no engine work may outlive the test database');
    if (externalRunId) assert.equal(stmts.getRunById.get(externalRunId).status, 'completed');
  }
});
