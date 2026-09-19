// Files service — system database artifacts are infrastructure, never user data.
// The data page must not list data/diagnostic.db (+ WAL/SHM siblings), and the
// destructive endpoints must refuse those names even when called exactly.
import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, writeFileSync } from 'fs';
import { tmpdir } from 'os';
import { join, basename } from 'path';

const { isSystemDatabaseFile, listDataDir, deleteDataFolder } = await import('../src/services/files.service.mjs');
const { config } = await import('../../../config/loader.mjs');

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
