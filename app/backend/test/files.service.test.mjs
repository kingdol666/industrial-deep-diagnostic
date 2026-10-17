// Files service — system database artifacts are infrastructure, never user data.
// The data page must not list data/diagnostic.db (+ WAL/SHM siblings), and the
// destructive endpoints must refuse those names even when called exactly.
import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, writeFileSync, mkdirSync, rmSync } from 'fs';
import { tmpdir } from 'os';
import { join, basename } from 'path';

const { isSystemDatabaseFile, listDataDir, listDataFolder, deleteDataFolder, readDataFile, DATA_DIR } = await import('../src/services/files.service.mjs');
const { config, PROJECT_ROOT } = await import('../../../config/loader.mjs');

const DB_FILE = basename(config.database.path);

describe('isSystemDatabaseFile — configured db name plus WAL/SHM siblings', () => {
  test('matches the db file and its -wal/-shm siblings', () => {
    assert.equal(isSystemDatabaseFile(DB_FILE), true);
    assert.equal(isSystemDatabaseFile(`${DB_FILE}-wal`), true);
    assert.equal(isSystemDatabaseFile(`${DB_FILE}-shm`), true);
  });

  test('leaves regular user data alone', () => {
    assert.equal(isSystemDatabaseFile('sensor.csv'), false);
    assert.equal(isSystemDatabaseFile(`my${DB_FILE}`), false);
    assert.equal(isSystemDatabaseFile(`${DB_FILE}.bak`), false);
    assert.equal(isSystemDatabaseFile('references'), false);
    assert.equal(isSystemDatabaseFile(undefined), false);
  });
});

describe('listDataDir — hides system database artifacts from the user listing', () => {
  test('db + siblings are filtered, user files stay', async () => {
    const dir = mkdtempSync(join(tmpdir(), 'idd-files-'));
    writeFileSync(join(dir, DB_FILE), 'db');
    writeFileSync(join(dir, `${DB_FILE}-wal`), 'wal');
    writeFileSync(join(dir, `${DB_FILE}-shm`), 'shm');
    writeFileSync(join(dir, 'sensor.csv'), 'timestamp,value\n');

    const entries = await listDataDir(dir);
    assert.deepEqual(entries.map((e) => e.name), ['sensor.csv']);
  });
});

describe('listDataFolder — safely browses nested directories under data root', () => {
  test('lists nested entries and rejects traversal or non-folder paths', async () => {
    const dir = join(DATA_DIR, `.browse-test-${process.pid}`);
    mkdirSync(join(dir, 'nested'), { recursive: true });
    writeFileSync(join(dir, 'nested', 'sample.csv'), 't,x\\n1,2\\n');
    try {
      const entries = await listDataFolder(`.browse-test-${process.pid}/nested`);
      assert.deepEqual(entries.map((entry) => entry.name), ['sample.csv']);
      await assert.rejects(() => listDataFolder('../workspace'), (err) => err.status === 400);
      await assert.rejects(() => listDataFolder(`.browse-test-${process.pid}/nested/sample.csv`), (err) => err.status === 400);
      await assert.rejects(() => listDataFolder(`.browse-test-${process.pid}/../..`), (err) => err.status === 400);
    } finally {
      const { rmSync } = await import('fs');
      rmSync(dir, { recursive: true, force: true });
    }
  });
});

describe('deleteDataFolder — refuses the system database by exact name', () => {
  test('400 with a human error, before any filesystem access', async () => {
    await assert.rejects(
      () => deleteDataFolder(DB_FILE),
      (err) => err.status === 400 && /System database file cannot be deleted/.test(err.message),
    );
    await assert.rejects(
      () => deleteDataFolder(`${DB_FILE}-wal`),
      (err) => err.status === 400,
    );
  });
});

describe('readDataFile — real-path containment, hidden files, system database', () => {
  const ws = join(PROJECT_ROOT, 'workspace');
  const pid = process.pid;
  const visible = `idd-probe-${pid}.txt`;
  const hidden = `.idd-probe-${pid}`;
  const dbDir = `idd-probe-db-${pid}`;

  test('a normal workspace file is readable', async () => {
    writeFileSync(join(ws, visible), 'hello');
    try {
      const r = await readDataFile(`workspace/${visible}`);
      assert.equal(r.content, 'hello');
      assert.equal(r.size, 5);
    } finally { rmSync(join(ws, visible), { force: true }); }
  });

  test('hidden files (e.g. data/.auth-jwt-secret) are refused', async () => {
    writeFileSync(join(ws, hidden), 'secret');
    writeFileSync(join(DATA_DIR, hidden), 'secret');
    try {
      await assert.rejects(() => readDataFile(`workspace/${hidden}`),
        (err) => err.status === 403);
      await assert.rejects(() => readDataFile(`data/${hidden}`),
        (err) => err.status === 403);
    } finally {
      rmSync(join(ws, hidden), { force: true });
      rmSync(join(DATA_DIR, hidden), { force: true });
    }
  });

  test('a system-database-named file is refused even outside data/', async () => {
    mkdirSync(join(ws, dbDir), { recursive: true });
    writeFileSync(join(ws, dbDir, DB_FILE), 'not-the-db');
    try {
      await assert.rejects(() => readDataFile(`workspace/${dbDir}/${DB_FILE}`),
        (err) => err.status === 403);
    } finally { rmSync(join(ws, dbDir), { recursive: true, force: true }); }
  });

  test('a project file outside data/ and workspace/ is refused', async () => {
    await assert.rejects(() => readDataFile('config/default.yaml'),
      (err) => err.status === 403);
  });
});
