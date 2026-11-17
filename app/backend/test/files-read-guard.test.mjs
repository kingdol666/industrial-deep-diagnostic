// Read endpoint (preview + download) — system infrastructure is not user data.
//
// The listing HIDES the SQLite database, its WAL/SHM siblings and every dot
// name, but the read route served them: `data/diagnostic.db` (all tenants' rows
// + scrypt password hashes), `data/.auth-jwt-secret` (the session-signing key)
// and anything under the ontology store were downloadable by any authenticated
// user. This pins the read-side guard: dot segments, the configured system
// database family and the ontology store answer the endpoint's usual
// 403 'Access denied'; ordinary files keep serving and the listing is unchanged.
//
// Isolation: DATA_DIR is overridden BEFORE any module loads, so every fixture
// lives under a throwaway data root (unique per process) and the real data
// directory is never read or written by this file.
import { test, describe, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { join, basename } from 'path';
import { mkdirSync, writeFileSync, rmSync } from 'fs';

const TMP_DATA_REL = `data/files-read-guard-${process.pid}-${Date.now()}`;
process.env.DATA_DIR = TMP_DATA_REL;

const { readDataFile, listDataDir, DATA_DIR } = await import('../src/services/files.service.mjs');
const { config } = await import('../../../config/loader.mjs');

const DB_FILE = basename(config.database.path); // the configured system database
const DB_BYTES = 'SQLite format 3\0' + 'must-not-be-served';
const rel = (p) => `${TMP_DATA_REL}/${p}`;       // PROJECT_ROOT-relative, as the route passes it
const fixture = (p) => join(DATA_DIR, p);        // absolute, for creating the fixtures

// Fixture tree under the temp data root:
//   report.csv                    ordinary user file (served)
//   nested/deep/report.final.csv  ordinary file, dot MID-name (served)
//   notes.db                      unrelated .db name → ordinary user data (served)
//   <db> (+ -wal/-shm)            the system database family (refused)
//   .hidden / .hiddendir/x.txt    dotfile / dot-directory content (refused)
//   ontology_store/x.json         ontology store state (refused)
mkdirSync(fixture(join('nested', 'deep')), { recursive: true });
mkdirSync(fixture('.hiddendir'), { recursive: true });
mkdirSync(fixture('ontology_store'), { recursive: true });
writeFileSync(fixture('report.csv'), 't,x\n1,2\n');
writeFileSync(fixture(join('nested', 'deep', 'report.final.csv')), 't,x\n3,4\n');
writeFileSync(fixture('notes.db'), DB_BYTES);
writeFileSync(fixture(DB_FILE), DB_BYTES);
writeFileSync(fixture(`${DB_FILE}-wal`), 'wal-bytes');
writeFileSync(fixture(`${DB_FILE}-shm`), 'shm-bytes');
writeFileSync(fixture('.hidden'), 'must never be served');
writeFileSync(fixture(join('.hiddendir', 'x.txt')), 'must never be served either');
writeFileSync(fixture(join('ontology_store', 'x.json')), '{"entries":[]}');

after(() => {
  rmSync(DATA_DIR, { recursive: true, force: true });
  delete process.env.DATA_DIR;
});

const assertAccessDenied = (promise) => assert.rejects(
  promise,
  (err) => err.status === 403 && err.message === 'Access denied',
);

describe('readDataFile — system infrastructure answers 403 Access denied', () => {
  const refused = [
    ['the configured system database', DB_FILE],
    ['its WAL sibling', `${DB_FILE}-wal`],
    ['its SHM sibling', `${DB_FILE}-shm`],
    ['a dotfile', '.hidden'],
    ['a file inside a dot-directory', '.hiddendir/x.txt'],
    ['ontology store state', 'ontology_store/x.json'],
    ['the system db name inside a nested folder', `nested/deep/${DB_FILE}`],
  ];
  for (const [label, name] of refused) {
    test(`${label} → 403`, () => assertAccessDenied(() => readDataFile(rel(name))));
  }

  test('a non-existent system-database name also answers 403 (existence is not probeable)', () =>
    assertAccessDenied(() => readDataFile(rel(`${DB_FILE}-definitely-missing`))));

  test('a windows case variant of the system database name is refused too', { skip: process.platform === 'win32' ? false : 'win32 casing guard' }, () =>
    // On a case-insensitive filesystem `DIAGNOSTIC.DB` opens the very same file;
    // the exact-name predicate alone would have admitted it.
    assertAccessDenied(() => readDataFile(rel(DB_FILE.toUpperCase()))));
});

describe('readDataFile — ordinary files are unchanged', () => {
  test('a plain data file serves its content', async () => {
    const result = await readDataFile(rel('report.csv'));
    assert.equal(result.content, 't,x\n1,2\n');
    assert.equal(result.size, 't,x\n1,2\n'.length);
  });

  test('a filename with a dot mid-name is not a dotfile', async () => {
    const result = await readDataFile(rel('nested/deep/report.final.csv'));
    assert.equal(result.content, 't,x\n3,4\n');
  });

  test('a nested path with `.` segments still serves (they normalize, they are not dot names)', async () => {
    const result = await readDataFile(rel('./nested/./deep/report.final.csv'));
    assert.equal(result.content, 't,x\n3,4\n');
  });

  test('a .db file that is NOT the configured system database is ordinary user data', async () => {
    const result = await readDataFile(rel('notes.db'));
    assert.equal(result.content, DB_BYTES);
  });
});

describe('GET /api/files/data/file/* — the HTTP contract (preview and ?ext=binary)', () => {
  let server;
  let baseUrl;

  before(async () => {
    const express = (await import('express')).default;
    const { default: filesRoutes } = await import('../src/routes/files.routes.mjs');
    const app = express();
    app.use(express.json());
    app.use('/api/files', filesRoutes);
    server = app.listen(0);
    await new Promise((r) => server.once('listening', r));
    baseUrl = `http://127.0.0.1:${server.address().port}`;
  });

  after(() => {
    if (server) server.close();
  });

  const url = (p, query = '') => `${baseUrl}/api/files/data/file/${encodeURIComponent(rel(p))}${query}`;

  test('JSON preview of an ordinary file → 200 with content', async () => {
    const res = await fetch(url('report.csv'));
    assert.equal(res.status, 200);
    const body = await res.json();
    assert.equal(body.success, true);
    assert.equal(body.data.content, 't,x\n1,2\n');
  });

  test('?ext=binary of an ordinary file → 200 octet-stream attachment', async () => {
    const res = await fetch(url('report.csv', '?ext=binary'));
    assert.equal(res.status, 200);
    assert.equal(res.headers.get('content-type'), 'application/octet-stream');
    assert.match(res.headers.get('content-disposition') || '', /^attachment; filename="report\.csv"$/);
    assert.equal(Buffer.from(await res.arrayBuffer()).toString('utf-8'), 't,x\n1,2\n');
  });

  test('JSON preview of the system database → 403 Access denied, never 200', async () => {
    const res = await fetch(url(DB_FILE));
    assert.equal(res.status, 403);
    const body = await res.json();
    assert.equal(body.success, false);
    assert.equal(body.error, 'Access denied');
  });

  test('?ext=binary of the system database (and its wal/shm) → 403, never the bytes', async () => {
    for (const name of [DB_FILE, `${DB_FILE}-wal`, `${DB_FILE}-shm`]) {
      const res = await fetch(url(name, '?ext=binary'));
      assert.equal(res.status, 403, `${name} must not download`);
      const body = await res.json();
      assert.equal(body.error, 'Access denied');
    }
  });

  test('JSON preview of a dotfile and of a dot-directory file → 403', async () => {
    for (const name of ['.hidden', '.hiddendir/x.txt']) {
      const res = await fetch(url(name));
      assert.equal(res.status, 403, `${name} must not preview`);
      assert.equal((await res.json()).error, 'Access denied');
    }
  });

  test('JSON preview of ontology store content → 403', async () => {
    const res = await fetch(url('ontology_store/x.json'));
    assert.equal(res.status, 403);
    assert.equal((await res.json()).error, 'Access denied');
  });
});

describe('the data listing is unchanged by the read guard', () => {
  test('hides the system database family and dot names, shows ordinary entries', async () => {
    const entries = await listDataDir(DATA_DIR);
    // `notes.db` is listed on purpose: only the CONFIGURED database name (plus
    // its -wal/-shm siblings) is infrastructure — an unrelated .db file is
    // ordinary user data, in the listing and on the read path alike.
    assert.deepEqual(entries.map((e) => e.name), ['nested', 'ontology_store', 'notes.db', 'report.csv']);
    for (const hidden of [DB_FILE, `${DB_FILE}-wal`, `${DB_FILE}-shm`, '.hidden', '.hiddendir']) {
      assert.ok(!entries.some((entry) => entry.name === hidden), `${hidden} must stay hidden`);
    }
  });
});
