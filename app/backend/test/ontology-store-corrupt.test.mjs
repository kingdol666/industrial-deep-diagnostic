// Corrupt ontology store index — the explicit 500 contract.
//
// readIndex() refuses a corrupt index (it backs the original up) precisely so
// no writer can persist the damage. The SERVICE layer must surface that as a
// caught 500 {code:'ONTOLOGY_STORE_CORRUPT'} with a generic message — the
// backup path belongs in the server log, never in the response body.
//
// This file runs in its own process (node --test), so it pins DATABASE_PATH and
// ONTOLOGY_STORE_DIR to a temp dir BEFORE the service modules are imported and
// never touches the real store.
import { test, describe, before, after, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, writeFileSync, readdirSync, readFileSync, rmSync } from 'fs';
import { tmpdir } from 'os';
import { join } from 'path';

const WORK = mkdtempSync(join(tmpdir(), 'idd-ontology-corrupt-'));
const STORE = join(WORK, 'store');
process.env.DATABASE_PATH = join(WORK, 'corrupt.db');
process.env.ONTOLOGY_STORE_DIR = STORE;

const svc = await import('../src/services/ontology.service.mjs');

const INDEX = join(STORE, 'index.json');
const CORRUPT = '{"version": 1, "entries": '; // truncated JSON

before(() => {
  mkdirSync(STORE, { recursive: true });
});

afterEach(() => {
  // Restore the corrupt index for the next case (a failed read leaves a backup).
  writeFileSync(INDEX, CORRUPT);
});

after(() => {
  try { rmSync(WORK, { recursive: true, force: true }); } catch { /* windows lock */ }
});

/** Every service entry point that reads the index must answer this error. */
const READERS = {
  listAssets: () => svc.listAssets({}),
  storeOverview: () => svc.storeOverview(),
  listCandidates: () => svc.listCandidates({}),
  getAsset: () => svc.getAsset('probe_scene', 1),
  cloneAsset: () => svc.cloneAsset({ sceneKey: 'probe_scene', version: 1, targetScene: 'probe_copy' }),
  saveAsset: () => svc.saveAsset({ sceneKey: 'probe_scene_new', ontology: { scene: {} }, baseVersion: null }),
  patchAsset: () => svc.patchAsset('probe_scene', 1, {}),
  deleteVersion: () => svc.deleteVersion('probe_scene', 1),
  deleteScene: () => svc.deleteScene('probe_scene'),
  recommend: () => svc.recommend({}),
};

describe('corrupt store index → explicit 500 ONTOLOGY_STORE_CORRUPT', () => {
  before(() => {
    writeFileSync(INDEX, CORRUPT);
  });

  for (const [name, call] of Object.entries(READERS)) {
    test(`${name} answers the explicit 500 without leaking the backup path`, () => {
      let thrown = null;
      try { call(); } catch (err) { thrown = err; }
      assert.ok(thrown, `${name} must refuse a corrupt index instead of returning empty data`);
      assert.equal(thrown.status, 500, `${name}: status`);
      assert.equal(thrown.code, 'ONTOLOGY_STORE_CORRUPT', `${name}: code`);
      assert.ok(thrown.message.length > 0, `${name}: message`);
      // The backup path is operational detail: log-only, never client-facing.
      assert.ok(!/index\.json\.corrupt-/.test(thrown.message), `${name}: backup path must not leak`);
    });
  }

  test('the corrupt original is backed up (nothing is silently zeroed)', () => {
    try { svc.listAssets({}); } catch { /* expected */ }
    const backups = readdirSync(STORE).filter((f) => f.startsWith('index.json.corrupt-'));
    assert.ok(backups.length >= 1, 'a corrupt backup exists');
    assert.equal(readFileSync(join(STORE, backups[0]), 'utf-8'), CORRUPT, 'the backup is byte-identical');
    // The live index is untouched — a repair can still find the original bytes.
    assert.equal(readFileSync(INDEX, 'utf-8'), CORRUPT);
  });

  test('a healthy store keeps working (the guard is not a blanket refusal)', () => {
    writeFileSync(INDEX, JSON.stringify({ version: 1, entries: [] }));
    const listing = svc.listAssets({});
    assert.equal(listing.scene_count, 0, 'an empty-but-valid store lists fine');
  });
});
