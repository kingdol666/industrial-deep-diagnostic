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
  //   v1 baseline tables → v2 run/chat columns + auth tables → v3 owner columns
  //   → v4 run management (title/category/soft-delete), external task registry,
  //     analysis results library.
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
  // user_id / title: the results-library + run-management columns (v4 migration).
  // timeout_minutes: per-run budget persisted at create time so it survives
  // /execute, Continue and queued drains.
  insertRun: db.prepare(`
    INSERT INTO diagnostic_runs (run_id, name, title, scene_name, data_path, data_folder, user_question, model, max_turns, report_language, harness, ontology_hit, enhancement_policy, enhancement_triggered, analysis_intent, user_id, timeout_minutes, owner_user_id)
    VALUES (@runId, @name, @title, @sceneName, @dataPath, @dataFolder, @userQuestion, @model, @maxTurns, @reportLanguage, @harness, @ontologyHit, @enhancementPolicy, @enhancementTriggered, @analysisIntent, @userId, @timeoutMinutes, @ownerUserId)
  `),
  insertRunWithKnowledge: db.prepare(`
    INSERT INTO diagnostic_runs (run_id, name, title, scene_name, data_path, data_folder, user_question, model, max_turns, report_language, harness, ontology_hit, enhancement_policy, enhancement_triggered, analysis_intent, user_id, timeout_minutes, owner_user_id, line_id, knowledge_policy_json, dataset_refs_json)
    VALUES (@runId, @name, @title, @sceneName, @dataPath, @dataFolder, @userQuestion, @model, @maxTurns, @reportLanguage, @harness, @ontologyHit, @enhancementPolicy, @enhancementTriggered, @analysisIntent, @userId, @timeoutMinutes, @ownerUserId, @lineId, @knowledgePolicyJson, @datasetRefsJson)
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
    SELECT id, run_id, name, title, scene_name, data_path, data_folder, user_question, status,
           session_id, workspace_path, report_path, score, judge_verdict, harness,
           ontology_hit, enhancement_policy, enhancement_triggered, analysis_intent,
           user_id, category_id, deleted_at, owner_user_id,
           line_id, knowledge_policy_json, dataset_refs_json,
           created_at, updated_at, completed_at, error_message
    FROM diagnostic_runs ORDER BY created_at DESC
  `),
  // Filtered listing (2026-10-22): ownership + soft-delete + category + status
  // + free-text, with LIMIT/OFFSET. NULL filters are no-ops by design.
  listRunsFiltered: db.prepare(`
    SELECT id, run_id, name, title, scene_name, data_path, data_folder, user_question, status,
           session_id, workspace_path, report_path, score, judge_verdict, harness,
           ontology_hit, enhancement_policy, enhancement_triggered, analysis_intent,
           user_id, category_id, deleted_at, owner_user_id,
           line_id, knowledge_policy_json, dataset_refs_json,
           created_at, updated_at, completed_at, error_message
    FROM diagnostic_runs
    -- Visibility (matches getRunStatus/requireRun): own rows, plus rows that
    -- are unowned under BOTH columns. A user_id-NULL row whose owner_user_id
    -- was backfilled (v3) belongs to the bootstrap admin — listing it to a
    -- non-admin would create a ghost row that 404s on detail (existence leak).
    WHERE (@userId IS NULL
           OR user_id = @userId
           OR (user_id IS NULL AND owner_user_id IS NULL))
      AND (@includeDeleted = 1 OR deleted_at IS NULL)
      AND (@categoryId IS NULL OR category_id = @categoryId)
      AND (@status IS NULL OR status = @status)
      AND (@q IS NULL OR title LIKE @q OR name LIKE @q OR scene_name LIKE @q OR user_question LIKE @q)
    ORDER BY created_at DESC
    LIMIT @limit OFFSET @offset
  `),
  countRunsFiltered: db.prepare(`
    SELECT COUNT(*) AS n FROM diagnostic_runs
    WHERE (@userId IS NULL
           OR user_id = @userId
           OR (user_id IS NULL AND owner_user_id IS NULL))
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
  // Categories on the results surface, each with its result count under the
  // index's visibility rule (own + legacy NULL-owner rows only).
  listResultCategories: db.prepare(`
    SELECT c.id, c.name, c.created_at,
      (SELECT COUNT(*)
       FROM analysis_results a
       JOIN diagnostic_runs r ON r.run_id = a.run_id
       WHERE r.category_id = c.id
         AND r.deleted_at IS NULL
         AND (@userId IS NULL OR a.user_id IS NULL OR a.user_id = @userId)
      ) AS result_count
    FROM run_categories c
    WHERE (@userId IS NULL OR c.user_id = @userId)
    ORDER BY c.created_at ASC
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
