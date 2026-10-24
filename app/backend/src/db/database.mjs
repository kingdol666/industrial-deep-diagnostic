import Database from 'better-sqlite3';
import { mkdirSync } from 'fs';
import { resolve, dirname } from 'path';
import { config, PROJECT_ROOT } from '../../../../config/loader.mjs';
import logger from '../utils/logger.mjs';

const DB_PATH = resolve(PROJECT_ROOT, config.database.path); // absolute DATABASE_PATH overrides are honored
mkdirSync(dirname(DB_PATH), { recursive: true });

const db = new Database(DB_PATH);
db.pragma(`journal_mode = ${config.database.journal_mode}`);
db.pragma(`foreign_keys = ${config.database.foreign_keys ? 'ON' : 'OFF'}`);

function sqlQuote(str) {
  return String(str).replace(/'/g, "''");
}

export function initDB() {
  logger.info('Initializing database...', { context: 'DB' });
  logger.info(`Path: ${DB_PATH}`, { context: 'DB' });

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

    -- Run management (2026-10-22): user-created categories. Rows are scoped to
    -- the owning user; a category name is unique per user only.
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

  // Migration: add report_language column if missing
  const cols = db.prepare('PRAGMA table_info(diagnostic_runs)').all();
  const hasReportLang = cols.some(c => c.name === 'report_language');
  if (!hasReportLang) {
    db.exec(`ALTER TABLE diagnostic_runs ADD COLUMN report_language TEXT DEFAULT '${sqlQuote(config.diagnosis.default_language)}'`);
  }

  // Migration: harness column — which engine executed the run ('claude' | 'omp')
  const hasHarness = cols.some(c => c.name === 'harness');
  if (!hasHarness) {
    db.exec(`ALTER TABLE diagnostic_runs ADD COLUMN harness TEXT DEFAULT 'claude'`);
    db.exec(`UPDATE diagnostic_runs SET harness = 'claude' WHERE harness IS NULL`);
  }

  // Migration: ontology asset reuse tracking ('reused' | 'extended' | 'built' | null)
  if (!cols.some(c => c.name === 'ontology_hit')) {
    db.exec(`ALTER TABLE diagnostic_runs ADD COLUMN ontology_hit TEXT`);
  }

  // Migration: enhancement (E0-E8) intent policy ('auto' | 'on' | 'off') + trigger flag
  if (!cols.some(c => c.name === 'enhancement_policy')) {
    db.exec(`ALTER TABLE diagnostic_runs ADD COLUMN enhancement_policy TEXT DEFAULT 'auto'`);
    db.exec(`UPDATE diagnostic_runs SET enhancement_policy = 'auto' WHERE enhancement_policy IS NULL`);
  }
  if (!cols.some(c => c.name === 'enhancement_triggered')) {
    db.exec(`ALTER TABLE diagnostic_runs ADD COLUMN enhancement_triggered INTEGER DEFAULT 0`);
  }

  // Migration: analysis intent — every run is a real agent execution; the
  // intent names which skill protocol the harness drove (deep-diagnosis is
  // the default 9-stage pipeline). Legacy rows predate the workbench.
  if (!cols.some(c => c.name === 'analysis_intent')) {
    db.exec(`ALTER TABLE diagnostic_runs ADD COLUMN analysis_intent TEXT DEFAULT 'deep-diagnosis'`);
    db.exec(`UPDATE diagnostic_runs SET analysis_intent = 'deep-diagnosis' WHERE analysis_intent IS NULL`);
  }

  // Migration: run management columns (2026-10-22) — ownership, user-editable
  // title, soft-delete timestamp and a single-level user category.
  if (!cols.some(c => c.name === 'user_id')) {
    db.exec('ALTER TABLE diagnostic_runs ADD COLUMN user_id TEXT');
  }
  if (!cols.some(c => c.name === 'title')) {
    db.exec('ALTER TABLE diagnostic_runs ADD COLUMN title TEXT');
    db.exec('UPDATE diagnostic_runs SET title = name WHERE title IS NULL');
  }
  if (!cols.some(c => c.name === 'deleted_at')) {
    db.exec('ALTER TABLE diagnostic_runs ADD COLUMN deleted_at TEXT');
  }
  if (!cols.some(c => c.name === 'category_id')) {
    db.exec('ALTER TABLE diagnostic_runs ADD COLUMN category_id TEXT');
  }
  db.exec('CREATE INDEX IF NOT EXISTS idx_runs_user ON diagnostic_runs(user_id)');
  db.exec('CREATE INDEX IF NOT EXISTS idx_runs_category ON diagnostic_runs(category_id)');

  const chatCols = db.prepare('PRAGMA table_info(chat_sessions)').all();
  const hasOriginSessionId = chatCols.some(c => c.name === 'origin_session_id');
  if (!hasOriginSessionId) {
    db.exec('ALTER TABLE chat_sessions ADD COLUMN origin_session_id TEXT');
    db.exec(`
      UPDATE chat_sessions
      SET origin_session_id = session_id
      WHERE origin_session_id IS NULL AND session_id IS NOT NULL
    `);
  }

  const hasPermissionMode = chatCols.some(c => c.name === 'permission_mode');
  if (!hasPermissionMode) {
    db.exec(`ALTER TABLE chat_sessions ADD COLUMN permission_mode TEXT DEFAULT 'bypassPermissions'`);
    db.exec(`
      UPDATE chat_sessions
      SET permission_mode = 'bypassPermissions'
      WHERE permission_mode IS NULL OR permission_mode = ''
    `);
  }

  const hasCwd = chatCols.some(c => c.name === 'cwd');
  if (!hasCwd) {
    db.exec(`ALTER TABLE chat_sessions ADD COLUMN cwd TEXT DEFAULT '${sqlQuote(PROJECT_ROOT)}'`);
    db.exec(`
      UPDATE chat_sessions
      SET cwd = '${sqlQuote(PROJECT_ROOT)}'
      WHERE cwd IS NULL OR cwd = ''
    `);
  }

  // NOTE: diagnostic_runs.harness is migrated above ("Migration: harness
  // column"). `cols` was snapshotted BEFORE that ALTER, so re-checking it here
  // would see a stale "column missing" and re-issue ALTER TABLE, crashing with
  // "duplicate column name: harness" on every fresh database. Do not repeat it.
  const hasChatHarness = chatCols.some(c => c.name === 'harness');
  if (!hasChatHarness) {
    db.exec(`ALTER TABLE chat_sessions ADD COLUMN harness TEXT DEFAULT 'claude'`);
    db.exec(`UPDATE chat_sessions SET harness = 'claude' WHERE harness IS NULL`);
  }

  // Migration: rebuild diagnosis_logs with ON DELETE CASCADE if missing
  const fkCols = db.prepare('PRAGMA foreign_key_list(diagnosis_logs)').all();
  const hasCascade = fkCols.some(fk => fk.on_delete === 'CASCADE');
  if (fkCols.length > 0 && !hasCascade) {
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

  // ─── Auth subsystem (v4): users + api_tokens ───
  // Idempotent CREATE IF NOT EXISTS — no column-snapshot migration pitfalls here.
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

  logger.info('Database initialized successfully.', { context: 'DB' });
}

initDB();

// Prepared statements
const stmts = {
  insertRun: db.prepare(`
    INSERT INTO diagnostic_runs (run_id, name, title, scene_name, data_path, data_folder, user_question, model, max_turns, report_language, harness, ontology_hit, enhancement_policy, enhancement_triggered, analysis_intent, user_id)
    VALUES (@runId, @name, @title, @sceneName, @dataPath, @dataFolder, @userQuestion, @model, @maxTurns, @reportLanguage, @harness, @ontologyHit, @enhancementPolicy, @enhancementTriggered, @analysisIntent, @userId)
  `),
  setRunOntologyHit: db.prepare(`
    UPDATE diagnostic_runs SET ontology_hit = @ontologyHit, updated_at = datetime('now') WHERE run_id = @runId
  `),
  setRunEnhancement: db.prepare(`
    UPDATE diagnostic_runs
    SET enhancement_triggered = @enhancementTriggered,
        enhancement_policy = COALESCE(@enhancementPolicy, enhancement_policy),
        updated_at = datetime('now')
    WHERE run_id = @runId
  `),
  updateRunStatus: db.prepare(`
    UPDATE diagnostic_runs SET status = @status, updated_at = datetime('now') WHERE run_id = @runId
  `),
  completeRun: db.prepare(`
    UPDATE diagnostic_runs
    SET status = 'completed',
        workspace_path = COALESCE(@workspacePath, workspace_path),
        report_path = COALESCE(@reportPath, report_path),
        score = COALESCE(@score, score),
        judge_verdict = COALESCE(@judgeVerdict, judge_verdict),
        error_message = NULL,
        completed_at = datetime('now'), updated_at = datetime('now')
    WHERE run_id = @runId
  `),
  failRun: db.prepare(`
    UPDATE diagnostic_runs SET status = 'failed', error_message = @error, updated_at = datetime('now') WHERE run_id = @runId
  `),
  insertLog: db.prepare(`
    INSERT INTO diagnosis_logs (run_id, role, content, message_type, tool_name)
    VALUES (@runId, @role, @content, @messageType, @toolName)
  `),
  insertEventStream: db.prepare(`
    INSERT INTO diagnosis_event_stream (run_id, seq, event_type, event_subtype, payload_json)
    VALUES (@runId, @seq, @eventType, @eventSubtype, @payloadJson)
  `),
  getAllRuns: db.prepare(`
    SELECT id, run_id, name, title, scene_name, data_path, data_folder, user_question, status,
           session_id, workspace_path, report_path, score, judge_verdict, harness,
           ontology_hit, enhancement_policy, enhancement_triggered, analysis_intent,
           user_id, category_id, deleted_at,
           created_at, updated_at, completed_at, error_message
    FROM diagnostic_runs ORDER BY created_at DESC
  `),
  // Filtered listing (2026-10-22): ownership + soft-delete + category + status
  // + free-text, with LIMIT/OFFSET. NULL filters are no-ops by design.
  listRunsFiltered: db.prepare(`
    SELECT id, run_id, name, title, scene_name, data_path, data_folder, user_question, status,
           session_id, workspace_path, report_path, score, judge_verdict, harness,
           ontology_hit, enhancement_policy, enhancement_triggered, analysis_intent,
           user_id, category_id, deleted_at,
           created_at, updated_at, completed_at, error_message
    FROM diagnostic_runs
    -- Legacy rows (user_id IS NULL) predate ownership and stay visible to every
    -- authenticated user; newly created rows are scoped to their creator.
    WHERE (@userId IS NULL OR user_id = @userId OR user_id IS NULL)
      AND (@includeDeleted = 1 OR deleted_at IS NULL)
      AND (@categoryId IS NULL OR category_id = @categoryId)
      AND (@status IS NULL OR status = @status)
      AND (@q IS NULL OR title LIKE @q OR name LIKE @q OR scene_name LIKE @q OR user_question LIKE @q)
    ORDER BY created_at DESC
    LIMIT @limit OFFSET @offset
  `),
  countRunsFiltered: db.prepare(`
    SELECT COUNT(*) AS n FROM diagnostic_runs
    WHERE (@userId IS NULL OR user_id = @userId OR user_id IS NULL)
      AND (@includeDeleted = 1 OR deleted_at IS NULL)
      AND (@categoryId IS NULL OR category_id = @categoryId)
      AND (@status IS NULL OR status = @status)
      AND (@q IS NULL OR title LIKE @q OR name LIKE @q OR scene_name LIKE @q OR user_question LIKE @q)
  `),
  renameRun: db.prepare(`
    UPDATE diagnostic_runs SET title = @title, updated_at = datetime('now') WHERE run_id = @runId
  `),
  setRunCategory: db.prepare(`
    UPDATE diagnostic_runs SET category_id = @categoryId, updated_at = datetime('now') WHERE run_id = @runId
  `),
  softDeleteRun: db.prepare(`
    UPDATE diagnostic_runs SET deleted_at = datetime('now'), updated_at = datetime('now') WHERE run_id = @runId
  `),
  restoreRun: db.prepare(`
    UPDATE diagnostic_runs SET deleted_at = NULL, updated_at = datetime('now') WHERE run_id = @runId
  `),
  deleteRunRow: db.prepare('DELETE FROM diagnostic_runs WHERE run_id = ?'),
  deleteLogsByRunId: db.prepare('DELETE FROM diagnosis_logs WHERE run_id = ?'),
  clearRunWorkspacePaths: db.prepare(`
    UPDATE diagnostic_runs SET workspace_path = NULL, report_path = NULL,
           updated_at = datetime('now') WHERE run_id = @runId
  `),
  getPendingRuns: db.prepare("SELECT run_id FROM diagnostic_runs WHERE status = 'pending'"),
  markStopped: db.prepare(`
    UPDATE diagnostic_runs SET status = 'stopped', error_message = @error,
           completed_at = datetime('now'), updated_at = datetime('now')
    WHERE run_id = @runId
  `),
  getRunsMissingSession: db.prepare(`
    SELECT run_id, harness, workspace_path FROM diagnostic_runs
    WHERE session_id IS NULL AND status IN ('completed', 'stopped', 'failed')
  `),
  setRunSessionIfNull: db.prepare(`
    UPDATE diagnostic_runs SET session_id = @sessionId, updated_at = datetime('now')
    WHERE run_id = @runId AND session_id IS NULL
  `),
  // ── run categories (2026-10-22) ──
  insertCategory: db.prepare(`
    INSERT INTO run_categories (id, user_id, name) VALUES (@id, @userId, @name)
  `),
  listCategories: db.prepare(`
    SELECT c.*, (SELECT COUNT(*) FROM diagnostic_runs r
                 WHERE r.category_id = c.id AND r.deleted_at IS NULL) AS run_count
    FROM run_categories c
    WHERE (@userId IS NULL OR c.user_id = @userId)
    ORDER BY c.created_at ASC
  `),
  getCategoryById: db.prepare('SELECT * FROM run_categories WHERE id = ?'),
  getCategoryByName: db.prepare('SELECT * FROM run_categories WHERE user_id = @userId AND name = @name'),
  renameCategory: db.prepare('UPDATE run_categories SET name = @name WHERE id = @id'),
  deleteCategory: db.prepare('DELETE FROM run_categories WHERE id = ?'),
  clearCategoryRefs: db.prepare('UPDATE diagnostic_runs SET category_id = NULL WHERE category_id = ?'),
  // ── external tasks (2026-10-22) ──
  insertExternalTask: db.prepare(`
    INSERT INTO external_tasks (task_id, run_id, intent, harness, scene, objective, status)
    VALUES (@taskId, @runId, @intent, @harness, @scene, @objective, @status)
  `),
  getExternalTask: db.prepare('SELECT * FROM external_tasks WHERE task_id = ?'),
  getExternalTaskByRun: db.prepare('SELECT * FROM external_tasks WHERE run_id = ? ORDER BY created_at DESC LIMIT 1'),
  listExternalTasks: db.prepare(`
    SELECT * FROM external_tasks ORDER BY created_at DESC LIMIT @limit
  `),
  updateExternalTaskStatus: db.prepare(`
    UPDATE external_tasks SET status = @status, updated_at = datetime('now') WHERE task_id = @taskId
  `),
  getRunById: db.prepare('SELECT * FROM diagnostic_runs WHERE run_id = ?'),
  getLogsByRunId: db.prepare('SELECT * FROM diagnosis_logs WHERE run_id = ? ORDER BY created_at ASC'),
  getEventStreamByRunId: db.prepare(`
    SELECT run_id, seq, event_type, event_subtype, payload_json, created_at
    FROM diagnosis_event_stream
    WHERE run_id = ?
    ORDER BY id ASC
  `),
  // Tail read for snapshots: newest N rows (descending LIMIT) re-sorted ASC.
  // A 50k-event claude run used to serialize its whole stream (11.5 MB) on
  // every open; the view only renders the tail.
  getEventStreamTail: db.prepare(`
    SELECT run_id, seq, event_type, event_subtype, payload_json, created_at
    FROM (
      SELECT * FROM diagnosis_event_stream
      WHERE run_id = ?
      ORDER BY seq DESC
      LIMIT ?
    )
    ORDER BY seq ASC
  `),
  countEventStreamByRunId: db.prepare(`
    SELECT COUNT(*) AS n FROM diagnosis_event_stream WHERE run_id = ?
  `),
  // Keep the newest @keep rows for a run; oldest seqs are removed. MAX(seq)
  // is untouched, so createRun()'s sequence continuation stays correct.
  pruneEventStreamForRun: db.prepare(`
    DELETE FROM diagnosis_event_stream
    WHERE run_id = @runId
      AND seq NOT IN (
        SELECT seq FROM diagnosis_event_stream
        WHERE run_id = @runId
        ORDER BY seq DESC
        LIMIT @keep
      )
  `),
  listRunsOverEventCap: db.prepare(`
    SELECT run_id, COUNT(*) AS n
    FROM diagnosis_event_stream
    GROUP BY run_id
    HAVING COUNT(*) > @cap
  `),
  getMaxEventSeq: db.prepare(`
    SELECT COALESCE(MAX(seq), -1) AS maxSeq FROM diagnosis_event_stream WHERE run_id = ?
  `),
  getActiveRuns: db.prepare("SELECT run_id FROM diagnostic_runs WHERE status = 'running'"),
  insertFolder: db.prepare(`
    INSERT INTO data_folders (name, path, description, file_count) VALUES (@name, @path, @description, @fileCount)
  `),
  getAllFolders: db.prepare('SELECT * FROM data_folders ORDER BY created_at DESC'),
  getFolderByName: db.prepare('SELECT * FROM data_folders WHERE name = ?'),
  deleteFolder: db.prepare('DELETE FROM data_folders WHERE name = ?'),
  getClaimedWorkspacePaths: db.prepare('SELECT workspace_path FROM diagnostic_runs WHERE workspace_path IS NOT NULL'),
  updateRunSession: db.prepare('UPDATE diagnostic_runs SET session_id = @sessionId, updated_at = datetime(\'now\') WHERE run_id = @runId'),
  insertChatSession: db.prepare(`
    INSERT INTO chat_sessions (chat_id, title, session_id, origin_session_id, status, model, permission_mode, cwd, harness)
    VALUES (@chatId, @title, @sessionId, @originSessionId, @status, @model, @permissionMode, @cwd, @harness)
  `),
  updateChatSession: db.prepare(`
    UPDATE chat_sessions
    SET title = COALESCE(@title, title),
        session_id = COALESCE(@sessionId, session_id),
        origin_session_id = COALESCE(origin_session_id, @originSessionId, session_id),
        permission_mode = COALESCE(@permissionMode, permission_mode),
        cwd = COALESCE(@cwd, cwd),
        harness = COALESCE(@harness, harness),
        status = COALESCE(@status, status),
        updated_at = datetime('now'),
        completed_at = CASE
          WHEN @status = 'active' THEN NULL
          WHEN @status IN ('completed', 'failed', 'stopped') THEN datetime('now')
          ELSE completed_at
        END
    WHERE chat_id = @chatId
  `),
  patchChatSessionConfig: db.prepare(`
    UPDATE chat_sessions
    SET title = COALESCE(@title, title),
        permission_mode = COALESCE(@permissionMode, permission_mode),
        cwd = COALESCE(@cwd, cwd),
        updated_at = datetime('now')
    WHERE chat_id = @chatId
  `),
  getChatSessionByChatId: db.prepare('SELECT * FROM chat_sessions WHERE chat_id = ?'),
  getChatSessionBySessionId: db.prepare('SELECT * FROM chat_sessions WHERE session_id = ? ORDER BY created_at DESC LIMIT 1'),
  getAllChatSessions: db.prepare(`
    SELECT * FROM chat_sessions ORDER BY updated_at DESC, created_at DESC
  `),
  renameChatSession: db.prepare(`
    UPDATE chat_sessions
    SET title = @title, updated_at = datetime('now')
    WHERE chat_id = @chatId
  `),
  deleteChatSession: db.prepare(`
    DELETE FROM chat_sessions WHERE chat_id = ?
  `),
  insertChatMessage: db.prepare(`
    INSERT INTO chat_messages (chat_id, role, content, event_type, event_subtype)
    VALUES (@chatId, @role, @content, @eventType, @eventSubtype)
  `),
  getChatMessagesByChatId: db.prepare(`
    SELECT * FROM chat_messages WHERE chat_id = ? ORDER BY id ASC
  `),
  deleteEventStreamByRunId: db.prepare('DELETE FROM diagnosis_event_stream WHERE run_id = ?'),

  // ─── Auth: users ───
  insertUser: db.prepare(`
    INSERT INTO users (username, email, password_hash, role)
    VALUES (@username, @email, @passwordHash, @role)
  `),
  countUsers: db.prepare('SELECT COUNT(*) AS c FROM users'),
  getUserById: db.prepare(`
    SELECT id, username, email, role, created_at, last_login_at
    FROM users WHERE id = ?
  `),
  getUserByUsername: db.prepare('SELECT * FROM users WHERE username = ?'),
  getUserByEmail: db.prepare('SELECT * FROM users WHERE email = ?'),
  touchUserLogin: db.prepare(`
    UPDATE users SET last_login_at = datetime('now'), updated_at = datetime('now') WHERE id = ?
  `),

  // ─── Auth: api tokens ───
  insertApiToken: db.prepare(`
    INSERT INTO api_tokens (user_id, name, token_hash, token_prefix, expires_at)
    VALUES (@userId, @name, @tokenHash, @tokenPrefix, @expiresAt)
  `),
  // ── analysis results library (2026-10-25) ──
  // UPSERT refreshes the DERIVED fields only; description/tags survive a
  // continue/rebuild re-completion (AC-11: update, never duplicate).
  upsertResult: db.prepare(`
    INSERT INTO analysis_results
      (result_id, run_id, description, summary, summary_json, tags, metadata,
       intent, scene_name, harness, score, verdict, user_id, created_at, updated_at)
    VALUES
      (@resultId, @runId, NULL, @summary, @summaryJson, '[]', @metadata,
       @intent, @sceneName, @harness, @score, @verdict, @userId, @createdAt, datetime('now'))
    ON CONFLICT(result_id) DO UPDATE SET
      summary = excluded.summary,
      summary_json = excluded.summary_json,
      metadata = excluded.metadata,
      intent = excluded.intent,
      scene_name = excluded.scene_name,
      harness = excluded.harness,
      score = excluded.score,
      verdict = excluded.verdict,
      user_id = excluded.user_id,
      created_at = excluded.created_at,
      updated_at = datetime('now')
  `),
  getResultByRunId: db.prepare('SELECT * FROM analysis_results WHERE run_id = ?'),
  updateResultUserFields: db.prepare(`
    UPDATE analysis_results
    SET description = @description,
        tags = @tags,
        updated_at = datetime('now')
    WHERE result_id = @resultId
  `),
  deleteResultByRunId: db.prepare('DELETE FROM analysis_results WHERE run_id = ?'),
  // Index query: joined with the run row for title/category/soft-delete truth.
  // Visibility matches history semantics — own rows plus legacy NULL rows.
  listResultsFiltered: db.prepare(`
    SELECT a.result_id, a.run_id, a.description, a.summary, a.summary_json, a.tags, a.metadata,
           a.intent, a.scene_name, a.harness, a.score, a.verdict, a.user_id,
           a.created_at AS result_created_at, a.updated_at,
           r.title, r.name, r.category_id, r.completed_at, r.report_path, r.workspace_path
    FROM analysis_results a
    JOIN diagnostic_runs r ON r.run_id = a.run_id
    WHERE r.deleted_at IS NULL
      AND (@userId IS NULL OR a.user_id IS NULL OR a.user_id = @userId)
      AND (@intent IS NULL OR a.intent = @intent)
      AND (@categoryId IS NULL OR r.category_id = @categoryId)
      AND (@scene IS NULL OR a.scene_name = @scene)
      AND (@harness IS NULL OR a.harness = @harness)
      AND (@minScore IS NULL OR a.score >= @minScore)
      AND (@tagPattern IS NULL OR a.tags LIKE @tagPattern)
      AND (@q IS NULL OR a.description LIKE @q OR a.summary LIKE @q
           OR r.title LIKE @q OR r.name LIKE @q OR a.scene_name LIKE @q OR a.tags LIKE @q)
    ORDER BY
      CASE WHEN @sort = 'created_asc' THEN a.created_at END ASC,
      CASE WHEN @sort = 'score_desc' THEN (a.score IS NULL) END ASC,
      CASE WHEN @sort = 'score_desc' THEN a.score END DESC,
      a.created_at DESC
    LIMIT @limit OFFSET @offset
  `),
  countResultsFiltered: db.prepare(`
    SELECT COUNT(*) AS n
    FROM analysis_results a
    JOIN diagnostic_runs r ON r.run_id = a.run_id
    WHERE r.deleted_at IS NULL
      AND (@userId IS NULL OR a.user_id IS NULL OR a.user_id = @userId)
      AND (@intent IS NULL OR a.intent = @intent)
      AND (@categoryId IS NULL OR r.category_id = @categoryId)
      AND (@scene IS NULL OR a.scene_name = @scene)
      AND (@harness IS NULL OR a.harness = @harness)
      AND (@minScore IS NULL OR a.score >= @minScore)
      AND (@tagPattern IS NULL OR a.tags LIKE @tagPattern)
      AND (@q IS NULL OR a.description LIKE @q OR a.summary LIKE @q
           OR r.title LIKE @q OR r.name LIKE @q OR a.scene_name LIKE @q OR a.tags LIKE @q)
  `),

  getApiTokenByHash: db.prepare('SELECT * FROM api_tokens WHERE token_hash = ?'),
  getApiTokenById: db.prepare('SELECT * FROM api_tokens WHERE id = ?'),
  listApiTokensByUser: db.prepare(`
    SELECT id, name, token_prefix, created_at, expires_at, last_used_at, revoked_at
    FROM api_tokens WHERE user_id = ? ORDER BY created_at DESC
  `),
  revokeApiToken: db.prepare(`
    UPDATE api_tokens SET revoked_at = datetime('now')
    WHERE id = ? AND revoked_at IS NULL
  `),
  touchApiTokenUsed: db.prepare(`UPDATE api_tokens SET last_used_at = datetime('now') WHERE id = ?`),
};

export { db, stmts };
