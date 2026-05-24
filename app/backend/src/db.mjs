import Database from 'better-sqlite3';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { mkdirSync } from 'fs';

const __dirname = dirname(fileURLToPath(import.meta.url));
const DB_DIR = join(__dirname, '..', 'data');
mkdirSync(DB_DIR, { recursive: true });

const DB_PATH = join(DB_DIR, 'diagnostic.db');

const db = new Database(DB_PATH);
db.pragma('journal_mode = WAL');
db.pragma('foreign_keys = ON');

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
    model TEXT DEFAULT 'claude-opus-4-7',
    max_turns INTEGER DEFAULT 200,
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
    FOREIGN KEY (run_id) REFERENCES diagnostic_runs(run_id)
  );

  CREATE TABLE IF NOT EXISTS data_folders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    path TEXT NOT NULL,
    description TEXT,
    file_count INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
  );
`);

// Add report_language column if not exists
try { db.exec(`ALTER TABLE diagnostic_runs ADD COLUMN report_language TEXT DEFAULT 'zh'`); } catch {}

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
  getRunById: db.prepare(`SELECT * FROM diagnostic_runs WHERE run_id = ?`),
  getLogsByRunId: db.prepare(`SELECT * FROM diagnosis_logs WHERE run_id = ? ORDER BY created_at ASC`),
  getActiveRuns: db.prepare(`SELECT run_id FROM diagnostic_runs WHERE status = 'running'`),
  insertFolder: db.prepare(`
    INSERT INTO data_folders (name, path, description, file_count) VALUES (@name, @path, @description, @fileCount)
  `),
  getAllFolders: db.prepare(`SELECT * FROM data_folders ORDER BY created_at DESC`),
  getFolderByName: db.prepare(`SELECT * FROM data_folders WHERE name = ?`),
  deleteFolder: db.prepare(`DELETE FROM data_folders WHERE name = ?`),
};

export { db, stmts };
