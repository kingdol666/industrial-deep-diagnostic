import Database from 'better-sqlite3';
import { mkdirSync } from 'fs';
import { join, dirname } from 'path';
import { config, PROJECT_ROOT } from '../../../../config/loader.mjs';

const DB_PATH = join(PROJECT_ROOT, config.database.path);
mkdirSync(dirname(DB_PATH), { recursive: true });

const db = new Database(DB_PATH);
db.pragma(`journal_mode = ${config.database.journal_mode}`);
db.pragma(`foreign_keys = ${config.database.foreign_keys ? 'ON' : 'OFF'}`);

function sqlQuote(str) {
  return String(str).replace(/'/g, "''");
}

export function initDB() {
  console.log('[DB] Initializing database...');
  console.log(`[DB] Path: ${DB_PATH}`);

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

    CREATE INDEX IF NOT EXISTS idx_runs_status ON diagnostic_runs(status);
    CREATE INDEX IF NOT EXISTS idx_runs_created ON diagnostic_runs(created_at);
    CREATE INDEX IF NOT EXISTS idx_logs_run_id ON diagnosis_logs(run_id);

    CREATE TABLE IF NOT EXISTS data_folders (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL UNIQUE,
      path TEXT NOT NULL,
      description TEXT,
      file_count INTEGER DEFAULT 0,
      created_at TEXT DEFAULT (datetime('now'))
    );
  `);

  // Migration: add report_language column if missing
  const cols = db.prepare('PRAGMA table_info(diagnostic_runs)').all();
  const hasReportLang = cols.some(c => c.name === 'report_language');
  if (!hasReportLang) {
    db.exec(`ALTER TABLE diagnostic_runs ADD COLUMN report_language TEXT DEFAULT '${sqlQuote(config.diagnosis.default_language)}'`);
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

  console.log('[DB] Database initialized successfully.');
}

initDB();

// Prepared statements
const stmts = {
  insertRun: db.prepare(`
    INSERT INTO diagnostic_runs (run_id, name, scene_name, data_path, data_folder, user_question, model, max_turns, report_language)
    VALUES (@runId, @name, @sceneName, @dataPath, @dataFolder, @userQuestion, @model, @maxTurns, @reportLanguage)
  `),
  updateRunStatus: db.prepare(`
    UPDATE diagnostic_runs SET status = @status, updated_at = datetime('now') WHERE run_id = @runId
  `),
  completeRun: db.prepare(`
    UPDATE diagnostic_runs
    SET status = 'completed', workspace_path = @workspacePath, report_path = @reportPath,
        score = @score, judge_verdict = @judgeVerdict, completed_at = datetime('now'), updated_at = datetime('now')
    WHERE run_id = @runId
  `),
  failRun: db.prepare(`
    UPDATE diagnostic_runs SET status = 'failed', error_message = @error, updated_at = datetime('now') WHERE run_id = @runId
  `),
  insertLog: db.prepare(`
    INSERT INTO diagnosis_logs (run_id, role, content, message_type, tool_name)
    VALUES (@runId, @role, @content, @messageType, @toolName)
  `),
  getAllRuns: db.prepare(`
    SELECT id, run_id, name, scene_name, data_path, data_folder, user_question, status,
           score, judge_verdict, created_at, completed_at, error_message
    FROM diagnostic_runs ORDER BY created_at DESC
  `),
  getRunById: db.prepare('SELECT * FROM diagnostic_runs WHERE run_id = ?'),
  getLogsByRunId: db.prepare('SELECT * FROM diagnosis_logs WHERE run_id = ? ORDER BY created_at ASC'),
  getActiveRuns: db.prepare("SELECT run_id FROM diagnostic_runs WHERE status = 'running'"),
  insertFolder: db.prepare(`
    INSERT INTO data_folders (name, path, description, file_count) VALUES (@name, @path, @description, @fileCount)
  `),
  getAllFolders: db.prepare('SELECT * FROM data_folders ORDER BY created_at DESC'),
  getFolderByName: db.prepare('SELECT * FROM data_folders WHERE name = ?'),
  deleteFolder: db.prepare('DELETE FROM data_folders WHERE name = ?'),
};

export { db, stmts };
