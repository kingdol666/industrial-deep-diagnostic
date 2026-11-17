import Database from 'better-sqlite3';
import { mkdirSync } from 'fs';
import { resolve, dirname } from 'path';
import { config, PROJECT_ROOT } from '../../../../config/loader.mjs';
import logger from '../utils/logger.mjs';
import { runMigrations, LATEST_SCHEMA_VERSION } from './migrations.mjs';

const DB_PATH = resolve(PROJECT_ROOT, config.database.path); // absolute DATABASE_PATH overrides are honored
mkdirSync(dirname(DB_PATH), { recursive: true });

const db = new Database(DB_PATH);
db.pragma(`journal_mode = ${config.database.journal_mode}`);
db.pragma(`foreign_keys = ${config.database.foreign_keys ? 'ON' : 'OFF'}`);

export function initDB() {
  logger.info('Initializing database...', { context: 'DB' });
  logger.info(`Path: ${DB_PATH}`, { context: 'DB' });

  // Schema evolution lives in ./migrations.mjs (versioned + transactional):
  //   v1 baseline tables → v2 run/chat columns + auth tables → v3 owner columns.
  // A pre-framework DB (no schema_version) is marker-detected and stamped, so
  // this call is safe to repeat (module load + index.mjs initialize()).
  const result = runMigrations(db, { log: logger });
  if (result.applied.length > 0) {
    logger.info(
      `Schema v${result.fromVersion} → v${result.toVersion} (applied: ${result.applied.join(', ')})`,
      { context: 'DB' },
    );
  } else {
    logger.info(`Schema up to date (v${result.toVersion}, latest v${LATEST_SCHEMA_VERSION})`, { context: 'DB' });
  }

  logger.info('Database initialized successfully.', { context: 'DB' });
}

initDB();

// Prepared statements
const stmts = {
  // owner_user_id: the creator's user id (multi-tenancy, P0-6). NULL = unowned
  // row — a run created while AUTH_ENABLED=0 (no identity) — which the ownership
  // contract treats as visible/administrable to admins only.
  insertRun: db.prepare(`
    INSERT INTO diagnostic_runs (run_id, name, scene_name, data_path, data_folder, user_question, model, max_turns, report_language, harness, ontology_hit, enhancement_policy, enhancement_triggered, analysis_intent, timeout_minutes, owner_user_id)
    VALUES (@runId, @name, @sceneName, @dataPath, @dataFolder, @userQuestion, @model, @maxTurns, @reportLanguage, @harness, @ontologyHit, @enhancementPolicy, @enhancementTriggered, @analysisIntent, @timeoutMinutes, @ownerUserId)
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
    SET status = 'completed', workspace_path = @workspacePath, report_path = @reportPath,
        score = @score, judge_verdict = @judgeVerdict, error_message = NULL,
        completed_at = datetime('now'), updated_at = datetime('now')
    WHERE run_id = @runId
  `),
  failRun: db.prepare(`
    UPDATE diagnostic_runs SET status = 'failed', error_message = @error, updated_at = datetime('now') WHERE run_id = @runId
  `),
  // Log ownership is inherited from the run row itself (single source of truth:
  // diagnostic_runs.owner_user_id), so no call site can forget it and a log can
  // never disagree with its run. A NULL-owner (legacy) run keeps NULL logs.
  insertLog: db.prepare(`
    INSERT INTO diagnosis_logs (run_id, role, content, message_type, tool_name, owner_user_id)
    VALUES (@runId, @role, @content, @messageType, @toolName,
            (SELECT owner_user_id FROM diagnostic_runs WHERE run_id = @runId))
  `),
  insertEventStream: db.prepare(`
    INSERT INTO diagnosis_event_stream (run_id, seq, event_type, event_subtype, payload_json)
    VALUES (@runId, @seq, @eventType, @eventSubtype, @payloadJson)
  `),
  getAllRuns: db.prepare(`
    SELECT id, run_id, name, scene_name, data_path, data_folder, user_question, status,
           session_id, workspace_path, report_path, score, judge_verdict, harness,
           ontology_hit, enhancement_policy, enhancement_triggered, analysis_intent,
           created_at, updated_at, completed_at, error_message, owner_user_id
    FROM diagnostic_runs ORDER BY created_at DESC
  `),
  getRunById: db.prepare('SELECT * FROM diagnostic_runs WHERE run_id = ?'),
  getLogsByRunId: db.prepare('SELECT * FROM diagnosis_logs WHERE run_id = ? ORDER BY created_at ASC'),
  getEventStreamByRunId: db.prepare(`
    SELECT run_id, seq, event_type, event_subtype, payload_json, created_at
    FROM diagnosis_event_stream
    WHERE run_id = ?
    ORDER BY id ASC
  `),
  getActiveRuns: db.prepare("SELECT run_id FROM diagnostic_runs WHERE status = 'running'"),
  insertFolder: db.prepare(`
    INSERT INTO data_folders (name, path, description, file_count, owner_user_id)
    VALUES (@name, @path, @description, @fileCount, @ownerUserId)
  `),
  getAllFolders: db.prepare('SELECT * FROM data_folders ORDER BY created_at DESC'),
  getFolderByName: db.prepare('SELECT * FROM data_folders WHERE name = ?'),
  deleteFolder: db.prepare('DELETE FROM data_folders WHERE name = ?'),
  getClaimedWorkspacePaths: db.prepare('SELECT workspace_path FROM diagnostic_runs WHERE workspace_path IS NOT NULL'),
  updateRunSession: db.prepare('UPDATE diagnostic_runs SET session_id = @sessionId, updated_at = datetime(\'now\') WHERE run_id = @runId'),
  insertChatSession: db.prepare(`
    INSERT INTO chat_sessions (chat_id, title, session_id, origin_session_id, status, model, permission_mode, cwd, harness, owner_user_id)
    VALUES (@chatId, @title, @sessionId, @originSessionId, @status, @model, @permissionMode, @cwd, @harness, @ownerUserId)
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
