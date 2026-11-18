// Schema migration framework (P0-6).
//
// Before this file the schema evolution lived as an ad-hoc block of
// `PRAGMA table_info` guards inside initDB() — correct but unversioned: there
// was no way to tell which shape a given DB file had, and every new column
// re-ran the whole guard chain. Now:
//
//   - `schema_version` records (version, name, applied_at) per applied step.
//   - MIGRATIONS is the ordered, append-only list. Never edit a shipped
//     migration; add a new one.
//   - Every migration runs inside its own BEGIN IMMEDIATE transaction: SQLite
//     DDL is transactional, so a throwing step leaves neither its tables nor
//     its stamp behind.
//   - A legacy DB (no `schema_version` table, i.e. created before this
//     framework) is detected by inspecting which marker objects/columns exist,
//     stamped at the highest CONTIGUOUS matching version, and the remaining
//     migrations are applied normally. Guarded steps make a conservative stamp
//     safe: re-running a migration whose effects already exist is a no-op.
//
// Ownership: this module never imports the live `db` handle — the caller
// passes it in, so unit tests can drive throwaway DB files.

import { config, PROJECT_ROOT } from '../../../../config/loader.mjs';
import logger from '../utils/logger.mjs';

function sqlQuote(str) {
  return String(str).replace(/'/g, "''");
}

// ─── Introspection helpers (exported for tests and later waves) ──────────────

export function tableExists(db, name) {
  return !!db.prepare("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?").get(name);
}

export function columnExists(db, table, column) {
  if (!tableExists(db, table)) return false;
  return db.prepare(`PRAGMA table_info(${table})`).all().some((c) => c.name === column);
}

export function indexExists(db, name) {
  return !!db.prepare("SELECT 1 FROM sqlite_master WHERE type = 'index' AND name = ?").get(name);
}

function foreignKeyHasCascade(db, table) {
  if (!tableExists(db, table)) return false;
  const fks = db.prepare(`PRAGMA foreign_key_list(${table})`).all();
  return fks.length > 0 && fks.some((fk) => fk.on_delete === 'CASCADE');
}

// ─── v3 contract: ownership columns (consumed by the tenancy wave) ───────────

/** Tables that gain `owner_user_id` (NULL = legacy/unowned, admin-visible). */
export const OWNER_TABLES = Object.freeze([
  'diagnostic_runs',
  'chat_sessions',
  'data_folders',
  'diagnosis_logs',
]);

/** Index names created for the two hot ownership lookups. */
export const OWNER_INDEXES = Object.freeze({
  diagnostic_runs: 'idx_runs_owner_user_id',
  chat_sessions: 'idx_chat_sessions_owner_user_id',
});

// ─── Migration definitions ──────────────────────────────────────────────────

const DIAGNOSTIC_RUN_COLUMNS_V2 = [
  'report_language', 'harness', 'ontology_hit', 'enhancement_policy',
  'enhancement_triggered', 'analysis_intent', 'timeout_minutes',
];
const CHAT_SESSION_COLUMNS_V2 = ['origin_session_id', 'permission_mode', 'cwd', 'harness'];

const BASELINE_TABLES = [
  'diagnostic_runs', 'diagnosis_logs', 'diagnosis_event_stream',
  'data_folders', 'chat_sessions', 'chat_messages',
];

/**
 * Ordered migration list. `up(db)` must be idempotent under its own guards;
 * `detect(db)` reports whether the migration's effects are already present on
 * a pre-framework DB (legacy stamping only — it is never consulted for DBs
 * that already carry a schema_version row).
 */
export const MIGRATIONS = [
  {
    version: 1,
    name: 'baseline',
    detect: (db) => BASELINE_TABLES.every((t) => tableExists(db, t)),
    up: (db) => {
      db.exec(`
        CREATE TABLE IF NOT EXISTS diagnostic_runs (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          run_id TEXT NOT NULL UNIQUE,
          name TEXT NOT NULL,
          scene_name TEXT NOT NULL,
          data_path TEXT NOT NULL,
          data_folder TEXT,
          user_question TEXT,
          status TEXT DEFAULT 'pending',
          session_id TEXT,
          workspace_path TEXT,
          report_path TEXT,
          score INTEGER,
          judge_verdict TEXT,
          error_message TEXT,
          model TEXT DEFAULT '${sqlQuote(config.claude.model)}',
          max_turns INTEGER DEFAULT ${Number(config.claude.max_turns)},
          created_at TEXT DEFAULT (datetime('now')),
          updated_at TEXT DEFAULT (datetime('now')),
          completed_at TEXT
        );

        CREATE TABLE IF NOT EXISTS diagnosis_logs (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          run_id TEXT NOT NULL,
          role TEXT NOT NULL,
          content TEXT,
          message_type TEXT DEFAULT 'text',
          tool_name TEXT,
          created_at TEXT DEFAULT (datetime('now')),
          FOREIGN KEY (run_id) REFERENCES diagnostic_runs(run_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS diagnosis_event_stream (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          run_id TEXT NOT NULL,
          seq INTEGER NOT NULL,
          event_type TEXT NOT NULL,
          event_subtype TEXT,
          payload_json TEXT,
          created_at TEXT DEFAULT (datetime('now')),
          FOREIGN KEY (run_id) REFERENCES diagnostic_runs(run_id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_runs_status ON diagnostic_runs(status);
        CREATE INDEX IF NOT EXISTS idx_runs_created ON diagnostic_runs(created_at);
        CREATE INDEX IF NOT EXISTS idx_logs_run_id ON diagnosis_logs(run_id);
        CREATE INDEX IF NOT EXISTS idx_event_stream_run_seq ON diagnosis_event_stream(run_id, seq);

        CREATE TABLE IF NOT EXISTS data_folders (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          name TEXT NOT NULL UNIQUE,
          path TEXT NOT NULL,
          description TEXT,
          file_count INTEGER DEFAULT 0,
          created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS chat_sessions (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          chat_id TEXT NOT NULL UNIQUE,
          title TEXT,
          session_id TEXT,
          origin_session_id TEXT,
          status TEXT DEFAULT 'active',
          model TEXT DEFAULT '${sqlQuote(config.claude.model)}',
          permission_mode TEXT DEFAULT 'bypassPermissions',
          cwd TEXT DEFAULT '${sqlQuote(PROJECT_ROOT)}',
          created_at TEXT DEFAULT (datetime('now')),
          updated_at TEXT DEFAULT (datetime('now')),
          completed_at TEXT
        );

        CREATE TABLE IF NOT EXISTS chat_messages (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          chat_id TEXT NOT NULL,
          role TEXT NOT NULL,
          content TEXT,
          event_type TEXT DEFAULT 'message',
          event_subtype TEXT,
          created_at TEXT DEFAULT (datetime('now')),
          FOREIGN KEY (chat_id) REFERENCES chat_sessions(chat_id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_chat_sessions_created ON chat_sessions(created_at);
        CREATE INDEX IF NOT EXISTS idx_chat_messages_chat_id ON chat_messages(chat_id);
      `);
    },
  },
  {
    version: 2,
    name: 'run-and-chat-columns-plus-auth',
    // A DB is v2-shaped only when EVERY guarded addition is present — a partial
    // shape must fall back to v1 so the guarded ALTERs fill the gaps.
    detect: (db) => (
      DIAGNOSTIC_RUN_COLUMNS_V2.every((c) => columnExists(db, 'diagnostic_runs', c))
      && CHAT_SESSION_COLUMNS_V2.every((c) => columnExists(db, 'chat_sessions', c))
      && foreignKeyHasCascade(db, 'diagnosis_logs')
      && tableExists(db, 'users')
      && tableExists(db, 'api_tokens')
    ),
    up: (db) => {
      // ── diagnostic_runs additions (ported from the ad-hoc ensure block) ──
      // report_language: report output language per run.
      if (!columnExists(db, 'diagnostic_runs', 'report_language')) {
        db.exec(`ALTER TABLE diagnostic_runs ADD COLUMN report_language TEXT DEFAULT '${sqlQuote(config.diagnosis.default_language)}'`);
      }
      // harness: which engine executed the run ('claude' | 'omp' | …).
      if (!columnExists(db, 'diagnostic_runs', 'harness')) {
        db.exec(`ALTER TABLE diagnostic_runs ADD COLUMN harness TEXT DEFAULT 'claude'`);
        db.exec(`UPDATE diagnostic_runs SET harness = 'claude' WHERE harness IS NULL`);
      }
      // ontology_hit: ontology asset reuse tracking ('reused' | 'extended' | 'built' | null).
      if (!columnExists(db, 'diagnostic_runs', 'ontology_hit')) {
        db.exec(`ALTER TABLE diagnostic_runs ADD COLUMN ontology_hit TEXT`);
      }
      // enhancement (E0-E8) intent policy ('auto' | 'on' | 'off') + trigger flag.
      if (!columnExists(db, 'diagnostic_runs', 'enhancement_policy')) {
        db.exec(`ALTER TABLE diagnostic_runs ADD COLUMN enhancement_policy TEXT DEFAULT 'auto'`);
        db.exec(`UPDATE diagnostic_runs SET enhancement_policy = 'auto' WHERE enhancement_policy IS NULL`);
      }
      if (!columnExists(db, 'diagnostic_runs', 'enhancement_triggered')) {
        db.exec(`ALTER TABLE diagnostic_runs ADD COLUMN enhancement_triggered INTEGER DEFAULT 0`);
      }
      // analysis_intent: which skill protocol the harness drove per run.
      if (!columnExists(db, 'diagnostic_runs', 'analysis_intent')) {
        db.exec(`ALTER TABLE diagnostic_runs ADD COLUMN analysis_intent TEXT DEFAULT 'deep-diagnosis'`);
        db.exec(`UPDATE diagnostic_runs SET analysis_intent = 'deep-diagnosis' WHERE analysis_intent IS NULL`);
      }
      // timeout_minutes: per-run engine turn timeout (the DB row is the single
      // source for start + Continue/queued drains, which re-read the row).
      if (!columnExists(db, 'diagnostic_runs', 'timeout_minutes')) {
        db.exec('ALTER TABLE diagnostic_runs ADD COLUMN timeout_minutes REAL');
      }

      // ── chat_sessions additions ──
      if (!columnExists(db, 'chat_sessions', 'origin_session_id')) {
        db.exec('ALTER TABLE chat_sessions ADD COLUMN origin_session_id TEXT');
        db.exec(`
          UPDATE chat_sessions
          SET origin_session_id = session_id
          WHERE origin_session_id IS NULL AND session_id IS NOT NULL
        `);
      }
      if (!columnExists(db, 'chat_sessions', 'permission_mode')) {
        db.exec(`ALTER TABLE chat_sessions ADD COLUMN permission_mode TEXT DEFAULT 'bypassPermissions'`);
        db.exec(`
          UPDATE chat_sessions
          SET permission_mode = 'bypassPermissions'
          WHERE permission_mode IS NULL OR permission_mode = ''
        `);
      }
      if (!columnExists(db, 'chat_sessions', 'cwd')) {
        db.exec(`ALTER TABLE chat_sessions ADD COLUMN cwd TEXT DEFAULT '${sqlQuote(PROJECT_ROOT)}'`);
        db.exec(`
          UPDATE chat_sessions
          SET cwd = '${sqlQuote(PROJECT_ROOT)}'
          WHERE cwd IS NULL OR cwd = ''
        `);
      }
      if (!columnExists(db, 'chat_sessions', 'harness')) {
        db.exec(`ALTER TABLE chat_sessions ADD COLUMN harness TEXT DEFAULT 'claude'`);
        db.exec(`UPDATE chat_sessions SET harness = 'claude' WHERE harness IS NULL`);
      }

      // ── diagnosis_logs: rebuild with ON DELETE CASCADE when missing ──
      // NOTE: never repeat a column check on a stale `cols` snapshot — re-issuing
      // ALTER TABLE ADD COLUMN crashes with "duplicate column name".
      if (!foreignKeyHasCascade(db, 'diagnosis_logs') && tableExists(db, 'diagnosis_logs')) {
        const fks = db.prepare('PRAGMA foreign_key_list(diagnosis_logs)').all();
        if (fks.length > 0) {
          db.exec(`
            ALTER TABLE diagnosis_logs RENAME TO diagnosis_logs_old;
            CREATE TABLE diagnosis_logs (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              run_id TEXT NOT NULL,
              role TEXT NOT NULL,
              content TEXT,
              message_type TEXT DEFAULT 'text',
              tool_name TEXT,
              created_at TEXT DEFAULT (datetime('now')),
              FOREIGN KEY (run_id) REFERENCES diagnostic_runs(run_id) ON DELETE CASCADE
            );
            INSERT INTO diagnosis_logs SELECT * FROM diagnosis_logs_old;
            DROP TABLE diagnosis_logs_old;
            CREATE INDEX IF NOT EXISTS idx_logs_run_id ON diagnosis_logs(run_id);
          `);
        }
      }

      // ── auth subsystem: users + api_tokens (idempotent CREATE IF NOT EXISTS) ──
      db.exec(`
        CREATE TABLE IF NOT EXISTS users (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          username TEXT NOT NULL UNIQUE,
          email TEXT UNIQUE,
          password_hash TEXT NOT NULL,
          role TEXT NOT NULL DEFAULT 'user',
          created_at TEXT DEFAULT (datetime('now')),
          updated_at TEXT DEFAULT (datetime('now')),
          last_login_at TEXT
        );

        CREATE TABLE IF NOT EXISTS api_tokens (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER NOT NULL,
          name TEXT NOT NULL,
          token_hash TEXT NOT NULL UNIQUE,
          token_prefix TEXT NOT NULL,
          created_at TEXT DEFAULT (datetime('now')),
          expires_at TEXT,
          last_used_at TEXT,
          revoked_at TEXT,
          FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_api_tokens_user_id ON api_tokens(user_id);
      `);
    },
  },
  {
    version: 3,
    name: 'tenancy-owner-columns',
    detect: (db) => OWNER_TABLES.every((t) => columnExists(db, t, 'owner_user_id')),
    up: (db) => {
      // owner_user_id NULL = legacy/unowned row, visible+administrable to
      // admins only (see src/middleware/ownership.mjs for the scope contract).
      for (const table of OWNER_TABLES) {
        if (!tableExists(db, table)) continue;
        if (!columnExists(db, table, 'owner_user_id')) {
          db.exec(`ALTER TABLE ${table} ADD COLUMN owner_user_id INTEGER`);
        }
      }
      db.exec(`CREATE INDEX IF NOT EXISTS ${OWNER_INDEXES.diagnostic_runs} ON diagnostic_runs(owner_user_id)`);
      db.exec(`CREATE INDEX IF NOT EXISTS ${OWNER_INDEXES.chat_sessions} ON chat_sessions(owner_user_id)`);

      // One-time backfill: historical rows belong to the bootstrap (lowest-id)
      // admin when one exists; without an admin they stay NULL (admin-visible).
      if (tableExists(db, 'users')) {
        const admin = db.prepare("SELECT id FROM users WHERE role = 'admin' ORDER BY id ASC LIMIT 1").get();
        if (admin) {
          for (const table of OWNER_TABLES) {
            if (!tableExists(db, table)) continue;
            db.prepare(`UPDATE ${table} SET owner_user_id = ? WHERE owner_user_id IS NULL`).run(admin.id);
          }
        }
      }
    },
  },
  {
    version: 4,
    name: 'run-management-and-results-library',
    detect: (db) => tableExists(db, 'run_categories')
      && tableExists(db, 'external_tasks')
      && tableExists(db, 'analysis_results')
      && columnExists(db, 'diagnostic_runs', 'deleted_at'),
    up: (db) => {
      // ── Run management (2026-10-22): user-created categories. Rows are
      // scoped to the owning user; a category name is unique per user only.
      db.exec(`
        ALTER TABLE diagnostic_runs ADD COLUMN user_id TEXT;
        ALTER TABLE diagnostic_runs ADD COLUMN title TEXT;
        ALTER TABLE diagnostic_runs ADD COLUMN deleted_at TEXT;
        ALTER TABLE diagnostic_runs ADD COLUMN category_id TEXT;
      `);

      db.exec(`
        CREATE TABLE IF NOT EXISTS run_categories (
          id TEXT PRIMARY KEY,
          user_id TEXT NOT NULL,
          name TEXT NOT NULL,
          created_at TEXT DEFAULT (datetime('now')),
          UNIQUE(user_id, name)
        );

        -- External task registry (2026-10-22): the task_id -> run_id binding must
        -- survive a backend restart (it used to live only in a process Map).
        CREATE TABLE IF NOT EXISTS external_tasks (
          task_id TEXT PRIMARY KEY,
          run_id TEXT NOT NULL,
          intent TEXT,
          harness TEXT,
          scene TEXT,
          objective TEXT,
          status TEXT DEFAULT 'accepted',
          created_at TEXT DEFAULT (datetime('now')),
          updated_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_external_tasks_run ON external_tasks(run_id);
        CREATE INDEX IF NOT EXISTS idx_external_tasks_created ON external_tasks(created_at);

        -- Analysis results library (2026-10-25): one row per COMPLETED analysis,
        -- result_id = run_id (single key). Derived fields (summary/summary_json/
        -- metadata/score/verdict/intent/scene/harness/user_id) are refreshed by the
        -- completion hook + startup backfill; description/tags are user-editable via
        -- PATCH. title / category / soft-delete are NOT mirrored here — reads JOIN
        -- diagnostic_runs so the run row stays the single source of truth.
        CREATE TABLE IF NOT EXISTS analysis_results (
          result_id TEXT PRIMARY KEY,
          run_id TEXT NOT NULL UNIQUE,
          description TEXT,
          summary TEXT DEFAULT '',
          summary_json TEXT,
          tags TEXT DEFAULT '[]',
          metadata TEXT,
          intent TEXT NOT NULL,
          scene_name TEXT,
          harness TEXT,
          score REAL,
          verdict TEXT,
          user_id TEXT,
          created_at TEXT,
          updated_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_results_intent ON analysis_results(intent);
        CREATE INDEX IF NOT EXISTS idx_results_user ON analysis_results(user_id);
        CREATE INDEX IF NOT EXISTS idx_results_created ON analysis_results(created_at);
      `);
    },
  },
];

export const LATEST_SCHEMA_VERSION = MIGRATIONS.reduce((max, m) => Math.max(max, m.version), 0);

// ─── schema_version table ───────────────────────────────────────────────────

const SCHEMA_VERSION_DDL = `
  CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL,
    name TEXT NOT NULL,
    applied_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (version)
  )
`;

export function ensureSchemaVersionTable(db) {
  db.exec(SCHEMA_VERSION_DDL);
}

/** Highest applied version, or 0 for a DB without a schema_version row. */
export function getSchemaVersion(db) {
  if (!tableExists(db, 'schema_version')) return 0;
  const row = db.prepare('SELECT MAX(version) AS v FROM schema_version').get();
  return Number(row?.v || 0);
}

export function listAppliedMigrations(db) {
  if (!tableExists(db, 'schema_version')) return [];
  return db.prepare('SELECT version, name, applied_at FROM schema_version ORDER BY version ASC').all();
}

/**
 * Highest CONTIGUOUS version whose effects are already present on a DB that
 * has no schema_version rows. 0 = empty/new DB (all migrations pending).
 */
export function detectLegacyVersion(db, migrations = MIGRATIONS) {
  const ordered = [...migrations].sort((a, b) => a.version - b.version);
  let detected = 0;
  for (const m of ordered) {
    let applied = false;
    try {
      applied = typeof m.detect === 'function' ? m.detect(db) === true : false;
    } catch {
      applied = false;
    }
    if (!applied) break;
    detected = m.version;
  }
  return detected;
}

// ─── Runner ─────────────────────────────────────────────────────────────────

/**
 * Apply every pending migration in order, each in its own BEGIN IMMEDIATE
 * transaction, stamping `schema_version` as it goes.
 *
 * @returns {{fromVersion:number,toVersion:number,applied:number[],legacyStamped:boolean,latestVersion:number}}
 */
export function runMigrations(db, { migrations = MIGRATIONS, log = logger } = {}) {
  const ordered = [...migrations].sort((a, b) => a.version - b.version);
  const latestVersion = ordered.reduce((max, m) => Math.max(max, m.version), 0);

  ensureSchemaVersionTable(db);

  let current = getSchemaVersion(db);
  let legacyStamped = false;

  if (current === 0) {
    const detected = detectLegacyVersion(db, ordered);
    if (detected > 0) {
      db.prepare('INSERT OR IGNORE INTO schema_version (version, name) VALUES (?, ?)')
        .run(detected, 'legacy-stamp');
      current = detected;
      legacyStamped = true;
      log?.info?.(`Legacy database detected — stamped at schema v${detected} (pre-framework DB)`, { context: 'DB' });
    }
  }

  const fromVersion = current;
  const applied = [];
  const stamp = db.prepare('INSERT INTO schema_version (version, name) VALUES (@version, @name)');

  for (const migration of ordered) {
    if (migration.version <= current) continue;
    const run = db.transaction(() => {
      migration.up(db);
      stamp.run({ version: migration.version, name: migration.name });
    });
    run.immediate();
    applied.push(migration.version);
    log?.info?.(`Migration v${migration.version} (${migration.name}) applied`, { context: 'DB' });
  }

  return {
    fromVersion,
    toVersion: getSchemaVersion(db),
    applied,
    legacyStamped,
    latestVersion,
  };
}
