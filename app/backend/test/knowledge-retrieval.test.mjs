import { after, test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdirSync, mkdtempSync, rmSync, writeFileSync, realpathSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { InMemoryTransport } from '@modelcontextprotocol/sdk/inMemory.js';

const dir = mkdtempSync(join(tmpdir(), 'idd-knowledge-'));
process.env.DATABASE_PATH = join(dir, 'test.sqlite');
process.env.DATA_DIR = dir;
const { db } = await import('../src/db/database.mjs');
const { createLine } = await import('../src/services/production-line.service.mjs');
const { createAsset, publishVersion, setVersionGrant, withdrawVersion } = await import('../src/services/knowledge-publication.service.mjs');
const { searchForRun, getForRun, recordCompletedEvidence, listRunRetrievals } = await import('../src/services/knowledge.service.mjs');
const { assertKnowledgeHarness, bindKnowledgeTools, preflightKnowledgeRun } = await import('../src/services/knowledge-runtime.service.mjs');
const { buildMemoryToolDirective, buildLineMemoryDirective } = await import('../src/engine/claude-client.mjs');
after(() => { db.close(); rmSync(dir, { recursive: true, force: true, maxRetries: 3 }); });

const user = (id) => ({ id, role: 'user', username: `operator${id}`, auth_type: 'session' });
const alice = user(31);
const bob = user(32);
for (const u of [alice, bob]) db.prepare('INSERT INTO users (id,username,password_hash,role) VALUES (?,?,?,?)').run(u.id, u.username, 'test', u.role);
const line = (actor) => createLine(actor, { name: '同名线' }).line_id;
const a = line(alice), b = line(alice), c = line(bob);
const insert = db.prepare(`INSERT INTO diagnostic_runs (run_id,name,scene_name,data_path,status,owner_user_id,user_id,harness,line_id,knowledge_policy_json,dataset_refs_json)
  VALUES (@id,@id,'同名线','demo.csv',@status,@owner,@ownerText,'claude',@line,@policy,'[]')`);
const run = (id, actor, line, references = []) => {
  insert.run({ id, owner: actor.id, ownerText: String(actor.id), line, status: 'pending', policy: JSON.stringify({ mode: 'on_demand', own_line: true, references }) });
  return { actor, run_id: id };
};
const complete = (id) => db.prepare("UPDATE diagnostic_runs SET status='completed',completed_at='2026-11-26 10:00:00' WHERE run_id=?").run(id);
const getRow = (id) => db.prepare('SELECT * FROM diagnostic_runs WHERE run_id=?').get(id);
const fixture = (id, actor, scope, subject) => {
  run(id, actor, scope);
  complete(id);
  assert.equal(recordCompletedEvidence(id, 1, [{ finding_id: id, subject, detail: '测温后核对校准' }]), 1);
};
const hit = (scope) => searchForRun(scope, { query: '测温' }).items;

 test('scoped short and trigram queries exclude equally named lines and prevent reuse of opaque references across attempts', () => {
  fixture('a-source', alice, a, '测温校准-本线');
  fixture('b-source', alice, b, '测温校准-隔壁线');
  fixture('c-source', bob, c, '测温校准-他人线');
  const target = run('target', alice, a);
  assert.deepEqual(hit(target).map((i) => i.title), ['测温校准-本线']);
  assert.equal(searchForRun(target, { query: '测温校' }).items.length, 1);
  const [item] = hit(target);
  assert.equal(getForRun(target, item.ref_id).item.detail, '测温后核对校准');
  assert.throws(() => getForRun(run('another', alice, a), item.ref_id), { code: 'KNOWLEDGE_ITEM_NOT_FOUND' });
  assert.throws(() => hit({ ...target, actor: bob }), { code: 'RUN_NOT_FOUND' });
  assert.deepEqual(searchForRun(target, { query: '没有这样的信号' }).items, []);
  const audit = listRunRetrievals(target);
  assert.ok(audit.items.every((i) => i.channel === 'preview'));
  assert.doesNotMatch(JSON.stringify(audit), /测温|校准/);
});

 test('selected publication is advisory; revocation invalidates an issued ref and stops launch', () => {
  const v = createAsset(bob, c, { kind: 'experience', title: '测温维护提示', summary: '测温核对', content: '测温参考需在本线独立验证' });
  const ref = { asset_id: v.asset_id, version: v.version };
  publishVersion(bob, ref, { confirmed: true, visibility: 'catalog', public_read: true });
  const target = run('selected', alice, b, [ref]);
  assert.equal(hit(target).some((i) => i.source_kind === 'published_asset'), false);
  setVersionGrant(bob, ref, alice.id, { rights: ['reuse'] });
  assert.equal(hit(run('unselected', alice, b)).some((i) => i.source_kind === 'published_asset'), false);
  const item = hit(target).find((i) => i.source_kind === 'published_asset');
  assert.equal(item.evidence_level, 'L5');
  assert.equal(getForRun(target, item.ref_id).item.detail, '测温参考需在本线独立验证');
  assert.throws(() => preflightKnowledgeRun(getRow(target.run_id)), { code: 'KNOWLEDGE_ISOLATION_REQUIRED' });
  withdrawVersion(bob, ref);
  assert.throws(() => getForRun(target, item.ref_id), { code: 'KNOWLEDGE_ITEM_NOT_FOUND' });
  assert.throws(() => preflightKnowledgeRun(getRow(target.run_id)), { code: 'KNOWLEDGE_SOURCE_UNAVAILABLE' });
});

 test('second completion invalidates old observations and budget is scoped to a host attempt', () => {
  const target = run('repeat', alice, a);
  const [old] = hit(target);
  complete('a-source');
  assert.equal(getRow('a-source').completion_revision, 2);
  assert.deepEqual(hit(target), []);
  assert.throws(() => getForRun(target, old.ref_id), { code: 'KNOWLEDGE_ITEM_NOT_FOUND' });
  db.prepare("UPDATE diagnostic_runs SET status='running' WHERE run_id=?").run(target.run_id);
  const attempt = { ...target, attempt_id: 'trusted-test-attempt' };
  for (let i = 0; i < 20; i++) assert.deepEqual(hit(attempt), []);
  assert.throws(() => hit(attempt), { code: 'KNOWLEDGE_BUDGET_EXCEEDED' });
  assert.throws(() => assertKnowledgeHarness('mock', { mode: 'on_demand' }), { code: 'KNOWLEDGE_UNAVAILABLE_ON_HARNESS' });
  assert.doesNotThrow(() => assertKnowledgeHarness('mock', { mode: 'disabled' }));
});

test('host-bound SDK tools read SQLite only on call and reuse neither preview nor a closed attempt', async (t) => {
  const scope = run('tool-runtime', alice, b);
  db.prepare("UPDATE diagnostic_runs SET status='running' WHERE run_id=?").run(scope.run_id);
  let active = true;
  const sdk = await bindKnowledgeTools(getRow(scope.run_id), alice, () => active);
  const client = new Client({ name: 'idd-knowledge-runtime-test', version: '1' });
  const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
  t.after(async () => { await client.close(); await sdk.instance.close(); });
  await sdk.instance.connect(serverTransport);
  await client.connect(clientTransport);
  await client.listTools();
  assert.match(buildMemoryToolDirective(sdk), /memory_search/);
  assert.doesNotMatch(buildMemoryToolDirective(sdk), /测温校准-隔壁线/);
  assert.equal(buildLineMemoryDirective({ text: '测温校准-隔壁线' }), '');
  assert.deepEqual(listRunRetrievals(scope).items, []);
  const result = await client.callTool({ name: 'memory_search', arguments: { query: '测温', user_id: bob.id, line_id: c } });
  const [item] = JSON.parse(result.content[0].text).items;
  assert.equal(item.title, '测温校准-隔壁线');
  assert.throws(() => getForRun(scope, item.ref_id), { code: 'KNOWLEDGE_ITEM_NOT_FOUND' });
  const get = () => client.callTool({ name: 'memory_get', arguments: { ref_id: item.ref_id } });
  assert.equal(JSON.parse((await get()).content[0].text).item.detail, '测温后核对校准');
  assert.ok(listRunRetrievals(scope).items.some((r) => r.channel === 'agent'));
  active = false;
  assert.equal((await get()).isError, true);
});

test('bound job inputs are checked individually against the job owner data roots', async () => {
  const { authorizeBoundInputs } = await import('../src/services/line-input.service.mjs');
  const ownFolder = join(dir, 'own');
  const peerFolder = join(dir, 'peer');
  for (const [folder, owner] of [[ownFolder, alice], [peerFolder, bob]]) {
    mkdirSync(folder);
    writeFileSync(join(folder, 'test.csv'), 'time,reading\n0,1\n');
    db.prepare('INSERT INTO data_folders(name,path,owner_user_id) VALUES (?,?,?)').run(folder, folder, owner.id);
  }
  const base = { line_id: a, owner_user_id: alice.id, harness: 'claude' };
  const good = join(ownFolder, 'test.csv');
  const bad = join(peerFolder, 'test.csv');
  assert.deepEqual(authorizeBoundInputs({ ...base, data_path: good }), [realpathSync(good)]);
  assert.throws(() => authorizeBoundInputs({ ...base, data_path: bad }), { code: 'LINE_INPUT_UNAVAILABLE' });
  assert.throws(() => authorizeBoundInputs({ ...base, data_path: JSON.stringify([good, bad]) }), { code: 'LINE_INPUT_UNAVAILABLE' });
});
