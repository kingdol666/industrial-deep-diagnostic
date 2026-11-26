import assert from 'node:assert/strict';
import { createHash, randomUUID } from 'node:crypto';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { once } from 'node:events';
import { after, before, test } from 'node:test';
import express from 'express';

const work = mkdtempSync(join(tmpdir(), 'idd-publications-'));
process.env.DATABASE_PATH = join(work, 'knowledge.sqlite');
process.env.AUTH_JWT_SECRET = 'publication-test-only-secret-abcdefghijk';

let server, base, db, publication;
let publisher, reader, stranger, readerToken, publisherToken, sourceLine, targetLine;

before(async () => {
  // Import dynamically after isolating the production DB and auth configuration.
  const { migrateKnowledgePublication } = await import('../src/db/knowledge-publication.schema.mjs');
  publication = await import('../src/services/knowledge-publication.service.mjs');
  const routes = await import('../src/routes/knowledge-publication.routes.mjs');
  ({ db } = await import('../src/db/database.mjs'));
  const { createApiToken, registerUser } = await import('../src/services/auth.service.mjs');
  const { createLine } = await import('../src/services/production-line.service.mjs');
  migrateKnowledgePublication(db); // also tests safe replay after integration registers v8
  registerUser({ username: 'publication_admin', password: 'TestOnly1234' });
  publisher = registerUser({ username: 'publication_owner', password: 'TestOnly1234' });
  reader = registerUser({ username: 'publication_reader', password: 'TestOnly1234' });
  stranger = registerUser({ username: 'publication_stranger', password: 'TestOnly1234' });
  readerToken = createApiToken(reader.user, { name: 'catalog test' }).token;
  publisherToken = createApiToken(publisher.user, { name: 'cannot publish' }).token;
  sourceLine = createLine(publisher.user, { name: '同名线' }).line_id;
  targetLine = createLine(reader.user, { name: '同名线' }).line_id;
  db.prepare("INSERT INTO production_line_members (line_id,user_id,role) VALUES (?,?,'read')").run(sourceLine, reader.user.id);

  // Real Express router and auth, without bringing up harnesses or background services.
  const app = express();
  app.use(express.json({ limit: '10mb' }));
  app.use('/api', routes.default);
  server = app.listen(0, '127.0.0.1');
  await once(server, 'listening');
  base = `http://127.0.0.1:${server.address().port}/api`;
});

after(async () => {
  if (server) await new Promise((resolve) => server.close(resolve));
  db?.close();
  rmSync(work, { recursive: true, force: true });
});

const catalogPath = '/knowledge/catalog';
const text = { kind: 'experience', title: '波动实例', summary: '脱敏摘要', content: '经人工整理的正文', applicability: '稳定工况' };
const csv = '\uFEFFpressure,label\r\n-1.2,"匿名,批次"\r\n';
const dataset = {
  kind: 'dataset', title: '脱敏对照', summary: '仅限实验验证', csv,
  fields: [{ name: 'pressure', description: '标准化压力' }, { name: 'label', description: '匿名类别' }],
  use_restrictions: '不得对外转发',
};

async function request(method, path, who, body, { raw = false, headers = {} } = {}) {
  const token = who?.session_token ?? who;
  const res = await fetch(base + path, {
    method,
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(body === undefined ? {} : { 'Content-Type': 'application/json' }),
      ...headers,
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  return {
    status: res.status, headers: res.headers,
    body: raw && res.ok ? Buffer.from(await res.arrayBuffer()) : await res.json(),
  };
}

function ok(result, status = 200) {
  assert.equal(result.status, status, JSON.stringify(result.body));
  return result.body.data;
}

function forbiddenVersion(err) {
  return err.status === 404 && err.code === 'KNOWLEDGE_VERSION_NOT_FOUND';
}

function refOf({ asset_id, version }) { return { asset_id, version }; }
function versionPath({ asset_id, version }) { return `/knowledge/assets/${asset_id}/versions/${version}`; }
function grantPath(ref, user) { return `${versionPath(ref)}/grants/${user.user.id}`; }
async function draft(input, line = sourceLine) {
  return refOf(ok(await request('POST', `/lines/${line}/assets`, publisher, input), 201));
}
async function publish(ref, options = {}) {
  return ok(await request('POST', `${versionPath(ref)}/publish`, publisher, { confirmed: true, ...options }));
}

// An exact read grant is separate from both catalog discoverability and reuse.
test('listed does not grant read or reuse; direct grants are exact and revocable', async () => {
  const ref = await draft(text);
  assert.equal((await request('GET', catalogPath)).status, 401);
  assert.equal((await request('GET', catalogPath, undefined, undefined, { headers: { 'X-User-Id': String(publisher.user.id) } })).status, 401);
  assert.deepEqual(ok(await request('GET', catalogPath, readerToken)).items, []);
  const undiscoverable = await request('GET', versionPath(ref), reader);
  const missing = await request('GET', versionPath({ asset_id: randomUUID(), version: 1 }), reader);
  assert.equal(undiscoverable.status, 404);
  assert.deepEqual(undiscoverable.body, missing.body);
  await publish(ref, { visibility: 'catalog' });
  const response = await request('GET', `${catalogPath}?kind=experience&q=波动`, readerToken);
  const [item] = ok(response).items;
  assert.equal(response.headers.get('cache-control'), 'private, no-store');
  assert.deepEqual(refOf(item), ref);
  assert.deepEqual(Object.keys(item).sort(), ['asset_id', 'kind', 'published_at', 'summary', 'title', 'version']);
  assert.deepEqual((await request('GET', versionPath(ref), reader)).body, missing.body);
  assert.throws(() => publication.getPublishedVersion(reader.user, ref, 'reuse'), forbiddenVersion);
  ok(await request('PUT', grantPath(ref, reader), publisher, { rights: ['read'] }));
  assert.equal(ok(await request('GET', versionPath(ref), readerToken)).content, text.content);
  assert.throws(() => publication.getPublishedVersion(reader.user, ref, 'reuse'), forbiddenVersion);
  ok(await request('PUT', grantPath(ref, reader), publisher, { rights: ['reuse'] }));
  assert.deepEqual((await request('GET', versionPath(ref), reader)).body, missing.body);
  const reusable = publication.getPublishedVersion(reader.user, ref, 'reuse');
  assert.deepEqual(Object.keys(reusable).sort(), ['applicability', 'asset_id', 'content', 'kind', 'published_at', 'summary', 'title', 'version']);
  assert.equal(reusable.content, text.content);
  ok(await request('DELETE', grantPath(ref, reader), publisher));
  assert.throws(() => publication.getPublishedVersion(reader.user, ref, 'reuse'), forbiddenVersion);
  const revoked = db.prepare("SELECT actor_user_id, target_user_id, change_json FROM knowledge_publication_audit WHERE asset_id = ? AND action = 'grant_revoked'").get(ref.asset_id);
  assert.equal(revoked.actor_user_id, publisher.user.id);
  assert.equal(revoked.target_user_id, reader.user.id);
  assert.deepEqual(JSON.parse(revoked.change_json), { previous: ['reuse'], rights: [] });
});

test('catalog keyset pages stay scoped and private discoverability requires read', async () => {
  const kind = 'memory_excerpt';
  const ref = await draft({ ...text, kind });
  await publish(ref);
  const first = await draft({ ...text, kind });
  const second = await draft({ ...text, kind });
  await publish(first, { visibility: 'catalog', public_read: true });
  await publish(second, { visibility: 'catalog' });
  ok(await request('PUT', grantPath(ref, reader), publisher, { rights: ['reuse'] }));
  const q = `${catalogPath}?kind=${kind}&q=波动&limit=1`;
  const pageOne = ok(await request('GET', q, reader));
  const pageTwo = ok(await request('GET', `${q}&cursor=${encodeURIComponent(pageOne.next_cursor)}`, reader));
  assert.equal(pageTwo.next_cursor, null);
  assert.deepEqual(new Set([...pageOne.items, ...pageTwo.items].map((item) => item.asset_id)), new Set([first.asset_id, second.asset_id]));
  assert.equal(ok(await request('GET', versionPath(first), stranger)).content, text.content);
  assert.throws(() => publication.getPublishedVersion(stranger.user, first, 'reuse'), forbiddenVersion);
  ok(await request('PUT', grantPath(ref, reader), publisher, { rights: ['read'] }));
  assert.equal(publication.listCatalog(reader.user, { kind }).items.length, 3);
  assert.equal(publication.listCatalog(stranger.user, { kind }).items.length, 2);
  assert.equal((await request('GET', `${q}&cursor=nonsense`, reader)).status, 400);
});

test('dataset read, download and analyze are independent; exact uploaded bytes are immutable', async () => {
  const ref = await draft(dataset);
  await publish(ref, { visibility: 'catalog', public_read: true });
  const scope = { actor: reader.user, line_id: targetLine };
  const metadata = ok(await request('GET', versionPath(ref), reader));
  const bytes = Buffer.from(csv);
  const sha256 = createHash('sha256').update(bytes).digest('hex');
  assert.deepEqual(metadata.fields, dataset.fields);
  assert.equal(metadata.use_restrictions, dataset.use_restrictions);
  assert.equal(metadata.sha256, sha256);
  assert.equal(metadata.size_bytes, bytes.length);
  for (const field of ['csv', 'bytes', 'content', 'line_id', 'workspace_path', 'object_ref']) assert.ok(!Object.hasOwn(metadata, field));
  assert.equal((await request('GET', `${versionPath(ref)}/download`, reader)).status, 404);
  assert.throws(() => publication.stageComparisonDataset(scope, ref), forbiddenVersion);
  assert.throws(() => publication.getPublishedVersion(reader.user, ref, 'reuse'), forbiddenVersion);
  assert.equal((await request('PUT', grantPath(ref, reader), publisher, { rights: ['reuse'] })).status, 400);
  ok(await request('PUT', grantPath(ref, reader), publisher, { rights: ['download'] }));
  const download = await request('GET', `${versionPath(ref)}/download`, readerToken, undefined, { raw: true });
  assert.equal(download.status, 200);
  assert.equal(download.headers.get('cache-control'), 'private, no-store');
  assert.match(download.headers.get('content-disposition'), /^attachment;/);
  assert.equal(download.headers.get('x-content-type-options'), 'nosniff');
  assert.deepEqual(download.body, bytes);
  assert.throws(() => publication.stageComparisonDataset(scope, ref), forbiddenVersion);
  ok(await request('PUT', grantPath(ref, reader), publisher, { rights: ['analyze'] }));
  assert.equal((await request('GET', `${versionPath(ref)}/download`, reader)).status, 404);
  assert.throws(() => publication.stageComparisonDataset({ ...scope, line_id: sourceLine }, ref));
  assert.throws(() => publication.stageComparisonDataset(scope, { ...ref, path: 'data/private.csv' }), forbiddenVersion);
  assert.throws(() => publication.stageComparisonDataset({ path: 'data/private.csv' }, ref), { status: 401 });
  const staged = publication.stageComparisonDataset(scope, ref);
  assert.deepEqual(staged.bytes, bytes);
  assert.equal(staged.metadata.sha256, sha256);
  staged.bytes.fill(0);
  assert.deepEqual(publication.stageComparisonDataset(scope, ref).bytes, bytes);
  ok(await request('DELETE', grantPath(ref, reader), publisher));
  assert.throws(() => publication.stageComparisonDataset(scope, ref), forbiddenVersion);
});

test('withdrawn versions cannot be selected; a new version inherits neither grants nor visibility', async () => {
  const ref = await draft(text);
  await publish(ref, { visibility: 'catalog', public_read: true });
  ok(await request('PUT', grantPath(ref, reader), publisher, { rights: ['reuse'] }));
  const { kind, ...snapshot } = text;
  const ref2 = refOf(ok(await request('POST', `/knowledge/assets/${ref.asset_id}/versions`, publisher, { ...snapshot, content: '第二版正文' }), 201));
  assert.equal(ref2.version, ref.version + 1);
  await publish(ref2);
  assert.equal(publication.getPublishedVersion(reader.user, ref, 'reuse').content, text.content);
  assert.throws(() => publication.getPublishedVersion(reader.user, ref2, 'read'), forbiddenVersion);
  assert.throws(() => publication.getPublishedVersion(reader.user, ref2, 'reuse'), forbiddenVersion);
  ok(await request('POST', `${versionPath(ref)}/withdraw`, publisher));
  assert.throws(() => publication.getPublishedVersion(reader.user, ref, 'reuse'), forbiddenVersion);
  assert.equal((await request('GET', versionPath(ref), reader)).status, 404);
  assert.ok(!publication.listCatalog(reader.user).items.some((item) => item.asset_id === ref.asset_id));
  assert.equal((await request('POST', `${versionPath(ref)}/publish`, publisher, { confirmed: true })).status, 409);
  assert.equal((await request('PUT', grantPath(ref, reader), publisher, { rights: ['reuse'] })).status, 409);
  const audit = db.prepare('SELECT * FROM knowledge_publication_audit WHERE asset_id=? ORDER BY id').all(ref.asset_id);
  assert.deepEqual(audit.map((row) => [row.action, row.version]), [
    ['draft_created', 1], ['published', 1], ['grant_set', 1], ['draft_created', 2], ['published', 2], ['withdrawn', 1],
  ]);
  assert.ok(audit.every((row) => row.actor_user_id === publisher.user.id));
  assert.ok(!JSON.stringify(audit).includes(text.content));
});

test('release only accepts curated data; sessions and current source-line manage are required', async () => {
  const source = `/lines/${sourceLine}/assets`;
  const privatePath = 'workspace/diagnostic-runs/private/report.md';
  assert.equal((await request('POST', source, reader, text)).status, 403);
  assert.equal((await request('POST', source, publisherToken, text)).status, 403);
  for (const forged of [{ path: privatePath }, { source_run_id: randomUUID() }, { actor: publisher.user }]) {
    const rejected = await request('POST', source, publisher, { ...text, ...forged });
    assert.equal(rejected.status, 400);
    assert.ok(!JSON.stringify(rejected.body).includes(privatePath));
  }
  for (const invalid of [
    { ...dataset, csv: undefined, path: privatePath },
    { ...dataset, csv: 'pressure,label\n=1+1,n' },
    { ...dataset, csv: 'pressure,label\n123' },
    { ...dataset, csv: 'pressure,label\n"unclosed,field' },
    { ...dataset, csv: 'pressure,label\n' + 'x'.repeat(1024 * 1024) },
    { ...dataset, fields: [{ name: 'different', description: '不匹配' }] },
  ]) assert.equal((await request('POST', source, publisher, invalid)).status, 400);
  const ref = await draft(text);
  const action = `${versionPath(ref)}/publish`;
  assert.equal((await request('POST', action, publisher, { confirmed: 'true' })).status, 400);
  assert.equal((await request('POST', action, publisher, { confirmed: true, visibility: 'private', public_read: true })).status, 400);
  assert.equal((await request('POST', action, publisherToken, { confirmed: true })).status, 403);
  assert.equal((await request('POST', action, reader, { confirmed: true })).status, 404);
  assert.equal((await request('POST', action, stranger, { confirmed: true })).status, 404);
  const cookie = { Cookie: `idd_session=${publisher.session_token}` };
  assert.equal((await request('POST', action, undefined, { confirmed: true }, { headers: cookie })).status, 403);
  const csrfOk = await request('POST', action, undefined, { confirmed: true, visibility: 'catalog', public_read: true }, {
    headers: { ...cookie, Origin: new URL(base).origin },
  });
  ok(csrfOk);
  const exposed = ok(await request('GET', versionPath(ref), stranger));
  assert.equal(exposed.content, text.content);
  for (const key of ['line_id', 'source_run_id', 'workspace_path', 'created_by_user_id', 'object_ref']) assert.ok(!Object.hasOwn(exposed, key));
  assert.throws(() => db.prepare('UPDATE knowledge_asset_versions SET content=? WHERE asset_id=?').run('rewritten', ref.asset_id), /immutable/);
});

test('ACL and withdrawal changes roll back when their audit insert fails', async () => {
  const ref = await draft(text);
  await publish(ref, { visibility: 'catalog', public_read: true });
  ok(await request('PUT', grantPath(ref, reader), publisher, { rights: ['reuse'] }));
  db.exec(`CREATE TEMP TRIGGER reject_publication_audit BEFORE INSERT ON knowledge_publication_audit
    BEGIN SELECT RAISE(ABORT, 'isolated internal DB error'); END`);
  try {
    const failed = await request('DELETE', grantPath(ref, reader), publisher);
    assert.equal(failed.status, 500);
    assert.ok(!JSON.stringify(failed.body).includes('isolated internal DB error'));
    assert.equal((await request('POST', `${versionPath(ref)}/withdraw`, publisher)).status, 500);
    assert.equal(publication.getPublishedVersion(reader.user, ref, 'reuse').content, text.content);
  } finally {
    db.exec('DROP TRIGGER reject_publication_audit');
  }
});
