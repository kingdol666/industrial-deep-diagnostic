// Schema migration framework (P0-6) — versioning, transactionality, legacy
// stamping and idempotency.
//
// These tests drive throwaway DB files directly through src/db/migrations.mjs
// (the live handle from database.mjs is never imported here — imports of that
// module would migrate whatever DATABASE_PATH points at).
//
// Legacy shapes are produced by calling the shipped migrations' `up()` steps
// in sequence, which is exactly the shape older binaries left behind.

import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import Database from 'better-sqlite3';
import { mkdtempSync } from 'fs';
import { tmpdir } from 'os';
import { join } from 'path';
import {
  MIGRATIONS,
  LATEST_SCHEMA_VERSION,
  OWNER_TABLES,
  OWNER_INDEXES,
  runMigrations,
  getSchemaVersion,
  listAppliedMigrations,
  detectLegacyVersion,
  tableExists,
  columnExists,
  indexExists,
} from '../src/db/migrations.mjs';

const silent = { info: () => {}, warn: () => {} };
const run = (db, opts = {}) => runMigrations(db, { log: silent, ...opts });

function tempDb(name) {
  const dir = mkdtempSync(join(tmpdir(), `idd-migrations-${name}-`));
  const db = new Database(join(dir, `${name}.db`));
  db.pragma('journal_mode = WAL');
  db.pragma('foreign_keys = ON');
  return db;
}

function insertUser(db, username, role) {
  return db.prepare('INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)')
    .run(username, 'scrypt$fake', role).lastInsertRowid;
}

function insertRun(db, runId) {
  db.prepare('INSERT INTO diagnostic_runs (run_id, name, scene_name, data_path) VALUES (?, ?, ?, ?)')
    .run(runId, runId, 'scene', '/tmp/none.csv');
}

const V1 = MIGRATIONS.find((m) => m.version === 1);
const V2 = MIGRATIONS.find((m) => m.version === 2);

describe('migrations — fresh database', () => {
  test('applies v1→latest, creating every table, column and index', () => {
    const db = tempDb('fresh');
    try {
      assert.equal(detectLegacyVersion(db), 0, 'empty file is not a legacy DB');
      const res = run(db);

      assert.equal(res.fromVersion, 0);
      assert.equal(res.toVersion, LATEST_SCHEMA_VERSION);
      assert.deepEqual(res.applied, MIGRATIONS.map((m) => m.version));
      assert.equal(res.legacyStamped, false);
      assert.equal(LATEST_SCHEMA_VERSION, 6);

      for (const t of [
        'diagnostic_runs', 'diagnosis_logs', 'diagnosis_event_stream', 'data_folders',
        'chat_sessions', 'chat_messages', 'users', 'api_tokens', 'schema_version',
        'run_categories', 'external_tasks', 'analysis_results', 'diagnosis_review_revisions',
      ]) {
        assert.ok(tableExists(db, t), `table ${t} must exist`);
      }

      // v2 additions preserved from the retired ad-hoc ensure block
      for (const c of ['report_language', 'harness', 'ontology_hit', 'enhancement_policy',
        'enhancement_triggered', 'analysis_intent', 'timeout_minutes']) {
        assert.ok(columnExists(db, 'diagnostic_runs', c), `diagnostic_runs.${c}`);
      }
      for (const c of ['origin_session_id', 'permission_mode', 'cwd', 'harness']) {
        assert.ok(columnExists(db, 'chat_sessions', c), `chat_sessions.${c}`);
      }
      const fks = db.prepare('PRAGMA foreign_key_list(diagnosis_logs)').all();
      assert.ok(fks.some((fk) => fk.on_delete === 'CASCADE'), 'diagnosis_logs must cascade on run delete');

      // v3 ownership columns + hot indexes
      for (const t of OWNER_TABLES) {
        assert.ok(columnExists(db, t, 'owner_user_id'), `${t}.owner_user_id`);
      }
      for (const idx of Object.values(OWNER_INDEXES)) {
        assert.ok(indexExists(db, idx), `index ${idx}`);
      }

      // v4 run-management columns + results library tables
      for (const c of ['user_id', 'title', 'deleted_at', 'category_id']) {
        assert.ok(columnExists(db, 'diagnostic_runs', c), `diagnostic_runs.${c}`);
      }

      // schema_version bookkeeping
      const rows = listAppliedMigrations(db);
      assert.deepEqual(rows.map((r) => r.version), [1, 2, 3, 4, 5, 6]);
      assert.deepEqual(rows.map((r) => r.name), MIGRATIONS.map((m) => m.name));
      assert.ok(rows.every((r) => typeof r.applied_at === 'string' && r.applied_at.length > 0));
    } finally {
      db.close();
    }
  });

  test('a fresh DB with no admin user leaves owner_user_id NULL', () => {
    const db = tempDb('fresh-noadmin');
    try {
      run(db);
      insertRun(db, 'r-noadmin');
      assert.equal(
        db.prepare("SELECT owner_user_id FROM diagnostic_runs WHERE run_id = 'r-noadmin'").get().owner_user_id,
        null,
      );
    } finally {
      db.close();
    }
  });
});

describe('migrations — legacy databases (no schema_version)', () => {
  test('v2-shaped legacy DB is stamped at v2 and only v3 runs (with backfill)', () => {
    const db = tempDb('legacy-v2');
    try {
      V1.up(db);
      V2.up(db); // exactly what the pre-framework initDB left behind
      assert.equal(tableExists(db, 'schema_version'), false, 'pre-framework DB has no stamp table');

      const adminId = insertUser(db, 'oldadmin', 'admin');
      insertUser(db, 'bob', 'user');
      insertRun(db, 'legacy-run');
      db.prepare("INSERT INTO diagnosis_logs (run_id, role) VALUES ('legacy-run', 'user')").run();
      db.prepare("INSERT INTO chat_sessions (chat_id, title) VALUES ('c1', 'legacy chat')").run();
      db.prepare("INSERT INTO data_folders (name, path) VALUES ('f1', '/tmp/f1')").run();

      assert.equal(detectLegacyVersion(db), 2);

      const res = run(db);
      assert.equal(res.legacyStamped, true);
      assert.equal(res.fromVersion, 2);
      assert.deepEqual(res.applied, [3, 4, 5, 6]);
      assert.equal(res.toVersion, LATEST_SCHEMA_VERSION);

      // Backfill: historical rows belong to the lowest-id admin.
      assert.equal(
        db.prepare("SELECT owner_user_id FROM diagnostic_runs WHERE run_id = 'legacy-run'").get().owner_user_id,
        Number(adminId),
      );
      assert.equal(db.prepare('SELECT owner_user_id FROM diagnosis_logs').get().owner_user_id, Number(adminId));
      assert.equal(db.prepare("SELECT owner_user_id FROM chat_sessions WHERE chat_id = 'c1'").get().owner_user_id, Number(adminId));
      assert.equal(db.prepare("SELECT owner_user_id FROM data_folders WHERE name = 'f1'").get().owner_user_id, Number(adminId));

      // The stamp records the detected version, not a fabricated v1.
      const stamped = listAppliedMigrations(db);
      assert.deepEqual(stamped.map((r) => r.version), [2, 3, 4, 5, 6]);
      assert.equal(stamped[0].name, 'legacy-stamp');
    } finally {
      db.close();
    }
  });

  test('legacy DB without an admin user keeps owner_user_id NULL (admin-only rows)', () => {
    const db = tempDb('legacy-noadmin');
    try {
      V1.up(db);
      V2.up(db);
      insertUser(db, 'regular', 'user');
      insertRun(db, 'run-orphan');

      const res = run(db);
      assert.equal(res.legacyStamped, true);
      assert.deepEqual(res.applied, [3, 4, 5, 6]);
      assert.equal(
        db.prepare("SELECT owner_user_id FROM diagnostic_runs WHERE run_id = 'run-orphan'").get().owner_user_id,
        null,
      );
    } finally {
      db.close();
    }
  });

  test('v1-shaped legacy DB is stamped at v1 and the guarded v2 additions run', () => {
    const db = tempDb('legacy-v1');
    try {
      V1.up(db);
      insertRun(db, 'ancient-run');
      assert.equal(detectLegacyVersion(db), 1, 'missing v2 columns → only v1 is provable');

      const res = run(db);
      assert.equal(res.legacyStamped, true);
      assert.equal(res.fromVersion, 1);
      assert.deepEqual(res.applied, [2, 3, 4, 5, 6]);

      for (const c of ['report_language', 'harness', 'timeout_minutes']) {
        assert.ok(columnExists(db, 'diagnostic_runs', c), `diagnostic_runs.${c} added by v2`);
      }
      assert.ok(columnExists(db, 'chat_sessions', 'cwd'));
      assert.ok(tableExists(db, 'users'), 'auth tables are part of v2');
      assert.ok(columnExists(db, 'diagnostic_runs', 'owner_user_id'));
      // Pre-existing row survived and received the documented defaults.
      const row = db.prepare("SELECT harness, analysis_intent, enhancement_policy FROM diagnostic_runs WHERE run_id = 'ancient-run'").get();
      assert.deepEqual(
        { harness: row.harness, analysis_intent: row.analysis_intent, enhancement_policy: row.enhancement_policy },
        { harness: 'claude', analysis_intent: 'deep-diagnosis', enhancement_policy: 'auto' },
      );
    } finally {
      db.close();
    }
  });

  test('a partial v2 shape is not trusted as v2 — the guarded migration fills the gap', () => {
    const db = tempDb('legacy-partial');
    try {
      V1.up(db);
      db.exec(`ALTER TABLE diagnostic_runs ADD COLUMN report_language TEXT DEFAULT 'zh'`);
      db.exec(`ALTER TABLE diagnostic_runs ADD COLUMN harness TEXT DEFAULT 'claude'`);

      assert.equal(detectLegacyVersion(db), 1, 'one missing marker must drop the stamp back to v1');

      const res = run(db);
      assert.deepEqual(res.applied, [2, 3, 4, 5, 6], 'v2 re-runs idempotently and adds what is missing');
      assert.ok(columnExists(db, 'diagnostic_runs', 'timeout_minutes'));
      assert.ok(columnExists(db, 'diagnostic_runs', 'ontology_hit'));
      assert.ok(columnExists(db, 'chat_sessions', 'harness'));
      assert.ok(tableExists(db, 'api_tokens'));
    } finally {
      db.close();
    }
  });

  test('a fully-upgraded DB that lost its schema_version is stamped at the latest version', () => {
    const db = tempDb('legacy-v3');
    try {
      for (const m of MIGRATIONS) m.up(db);
      assert.equal(tableExists(db, 'schema_version'), false);

      assert.equal(detectLegacyVersion(db), LATEST_SCHEMA_VERSION);
      const res = run(db);
      assert.equal(res.legacyStamped, true);
      assert.equal(res.fromVersion, LATEST_SCHEMA_VERSION);
      assert.deepEqual(res.applied, []);
    } finally {
      db.close();
    }
  });
});

describe('migrations — idempotency and incremental application', () => {
  test('running twice changes nothing', () => {
    const db = tempDb('twice');
    try {
      const first = run(db);
      const second = run(db);
      assert.deepEqual(second.applied, []);
      assert.equal(second.fromVersion, LATEST_SCHEMA_VERSION);
      assert.equal(second.toVersion, LATEST_SCHEMA_VERSION);
      assert.equal(second.legacyStamped, false);
      assert.equal(getSchemaVersion(db), LATEST_SCHEMA_VERSION);
      assert.equal(listAppliedMigrations(db).length, first.applied.length);
    } finally {
      db.close();
    }
  });

  test('re-running after a new migration applies only the new one', () => {
    const db = tempDb('incremental');
    try {
      run(db);
      const future = {
        version: LATEST_SCHEMA_VERSION + 1,
        name: 'test-only-future',
        up: (d) => d.exec('CREATE TABLE IF NOT EXISTS t_future (id INTEGER)'),
      };
      const res = run(db, { migrations: [...MIGRATIONS, future] });
      assert.deepEqual(res.applied, [LATEST_SCHEMA_VERSION + 1]);
      assert.equal(res.fromVersion, LATEST_SCHEMA_VERSION);
      assert.equal(res.toVersion, LATEST_SCHEMA_VERSION + 1);
      assert.ok(tableExists(db, 't_future'));
    } finally {
      db.close();
    }
  });

  test('a throwing migration rolls back its own effects and stamp (BEGIN IMMEDIATE)', () => {
    const db = tempDb('rollback');
    try {
      const bad = {
        version: LATEST_SCHEMA_VERSION + 10,
        name: 'bad',
        up: (d) => {
          d.exec('CREATE TABLE t_bad (id INTEGER)');
          throw new Error('boom');
        },
      };
      assert.throws(() => run(db, { migrations: [...MIGRATIONS, bad] }), /boom/);

      assert.equal(tableExists(db, 't_bad'), false, 'DDL must roll back with the failed migration');
      assert.equal(getSchemaVersion(db), LATEST_SCHEMA_VERSION, 'no stamp for the failed step');
      assert.equal(listAppliedMigrations(db).length, MIGRATIONS.length);
    } finally {
      db.close();
    }
  });
});
