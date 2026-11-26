// File Service — Data directory listing and file management logic

import { readdir, stat, lstat, mkdir, rm, readFile, realpath } from 'fs/promises';
import { existsSync } from 'fs';
import { execFile as execFileCallback } from 'child_process';
import { join, extname, dirname, resolve, relative, basename, isAbsolute, sep } from 'path';
import { homedir } from 'os';
import { promisify } from 'util';
import { config, PROJECT_ROOT, data as dataConfig, pipeline as pipeConfig } from '../../../../config/loader.mjs';
import logger from '../utils/logger.mjs';
import { resolveInside, isInside } from '../utils/pathGuard.mjs';
import { db, stmts } from '../db/database.mjs';
import { canView, resolveOwnerId, INTERNAL } from './tenancy.mjs';
// The ontology store resolves its own directory (honors ONTOLOGY_STORE_DIR).
import { STORE_DIR as ONTOLOGY_STORE_DIR } from '../../../../.claude/shared/scripts/ontology_store.mjs';

const DATA_DIR = join(PROJECT_ROOT, dataConfig.dir);
const WORKSPACE_DIR = join(PROJECT_ROOT, 'workspace');
const RUNS_DIR = join(WORKSPACE_DIR, 'diagnostic-runs');
const execFile = promisify(execFileCallback);

// Resolve a run name (URL param) to its directory inside the runs root, or null
// when it would escape — a bare `join(RUNS_DIR, name)` lets `..\..\data` through.
function resolveRunDir(runName) {
  try {
    return resolveInside(RUNS_DIR, runName, { label: 'run name' });
  } catch {
    return null;
  }
}

// ── Workspace run ownership (P0-6) ──────────────────────────────────────────
// The workspace is keyed by DIRECTORY name (workspace/diagnostic-runs/<name>,
// chosen by the pipeline — e.g. `<timestamp>_<scene>`), while ownership lives on
// the diagnostic_runs row. Map one to the other by the identity fields the DB
// actually stores, trying them all:
//   workspace_path = 'workspace/diagnostic-runs/<name>'   (the linked dir, either separator)
//   run_id  = <name>   (external callers address runs by run id)
//   name    = <name>   (the `<scene>_<runId>` row name)
// No matching row → NULL semantics: the directory is unowned/legacy and only an
// admin may read it.
const runByWorkspaceName = db.prepare(`
  SELECT run_id, name, workspace_path, owner_user_id
  FROM diagnostic_runs
  WHERE run_id = @runName OR name = @runName
     OR workspace_path = @rel OR workspace_path = @relBackslash OR workspace_path = @abs
  ORDER BY completed_at DESC
  LIMIT 1
`);

const reviewRunByExactWorkspace = db.prepare(`SELECT run_id, status, harness, owner_user_id, deleted_at
  FROM diagnostic_runs WHERE workspace_path IN (?, ?, ?, ?) LIMIT 2`);

function workspaceReviewId(name, viewer) {
  const rel = `workspace/diagnostic-runs/${name}`;
  const abs = join(PROJECT_ROOT, rel);
  const rows = reviewRunByExactWorkspace.all(rel, rel.replaceAll('/', '\\'), abs, abs.replaceAll('\\', '/'));
  const row = rows.length === 1 ? rows[0] : null;
  return row && !row.deleted_at && row.status === 'completed' && row.harness !== 'mock'
    && canView(viewer, row.owner_user_id) ? row.run_id : null;
}

/** The diagnostic_runs row behind a workspace directory name, or undefined. */
export function workspaceRunRow(runName) {
  const name = String(runName || '');
  if (!name) return undefined;
  const rel = `workspace/diagnostic-runs/${name}`;
  try {
    return runByWorkspaceName.get({
      runName: name,
      rel,
      relBackslash: rel.replace(/\//g, '\\'),
      abs: join(PROJECT_ROOT, rel),
    });
  } catch (e) {
    logger.error(`workspace run ownership lookup failed for ${name}: ${e.message}`, { context: 'Files' });
    return undefined;
  }
}

/**
 * May `viewer` read/act on the workspace directory `runName`?
 * Matching run row → its owner rule; no row (unknown/legacy dir) → NULL rule
 * (admin-only, unless tenancy is off in dev mode). INTERNAL callers bypass.
 */
export function canViewWorkspaceRun(viewer, runName) {
  const row = workspaceRunRow(runName);
  return canView(viewer, row ? row.owner_user_id : null);
}

/** Run-scoped subtree of the workspace (`.../diagnostic-runs/<name>/...`)? */
function workspaceRunNameOfPath(absPath) {
  if (!isInside(RUNS_DIR, absPath)) return null;
  const rel = relative(RUNS_DIR, absPath);
  if (!rel || rel === '..' || rel.startsWith('..')) return null;
  return rel.split(/[\\/]+/).filter(Boolean)[0] || null;
}

// The system's own SQLite database lives inside the data directory (WAL mode
// keeps `-wal` / `-shm` siblings next to it). It is infrastructure, not user
// data: listing, overwriting or deleting it can corrupt a running system, so
// it is hidden from user-facing listings and destructive endpoints refuse it.
// Matched by the configured db filename plus any `-` suffixed sibling.
export function isSystemDatabaseFile(name) {
  const dbFileName = basename(config.database.path);
  return typeof name === 'string' && (name === dbFileName || name.startsWith(`${dbFileName}-`));
}

// ── Read guard — system infrastructure is not user data ─────────────────────
// The read endpoint serves file CONTENT, so hiding these names from the listing
// is not enforcement: without the same rule on the read path, any authenticated
// user could download `data/diagnostic.db` (every tenant's rows + scrypt
// password hashes), its `-wal` / `-shm` siblings, `data/.auth-jwt-secret` (the
// session-signing key) and anything under the ontology store.
//
// The ontology store keeps its own state (index + version dirs). Its
// conventional home is `<data.dir>/ontology_store`, while the store module
// resolves the actual directory (ONTOLOGY_STORE_DIR overrides it) — refuse
// reads inside either.
const ONTOLOGY_STORE_DIRS = [...new Set([ONTOLOGY_STORE_DIR, join(DATA_DIR, 'ontology_store')])];

// isSystemDatabaseFile matches the configured name exactly, but Windows
// filenames are case-insensitive: `Diagnostic.DB` opens the very same
// `diagnostic.db` file. Fold the comparison on win32 — the platform where the
// two spellings are provably one file (on a case-sensitive FS they are not).
function isCaseFoldedSystemDatabaseName(name) {
  if (process.platform !== 'win32' || typeof name !== 'string') return false;
  const lower = name.toLowerCase();
  const dbLower = basename(config.database.path).toLowerCase();
  return lower === dbLower || lower.startsWith(`${dbLower}-`);
}

// Is a read of `absPath` (already proven inside DATA_DIR / WORKSPACE_DIR)
// refused? Yes when
//   (a) any path segment BELOW the readable root is a dot name — the same
//       dotfiles / dot-directories the data listing hides (a dot MID-name such
//       as `report.v2.csv` is an ordinary name and stays readable);
//   (b) the basename is the configured system database or a WAL/SHM sibling;
//   (c) the path lands inside the ontology store.
function isRefusedReadPath(absPath) {
  const root = isInside(DATA_DIR, absPath) ? DATA_DIR : WORKSPACE_DIR;
  const segments = relative(root, absPath).split(/[\\/]+/).filter(Boolean);
  if (segments.some((segment) => segment.startsWith('.'))) return true;
  const name = basename(absPath);
  if (isSystemDatabaseFile(name) || isCaseFoldedSystemDatabaseName(name)) return true;
  return ONTOLOGY_STORE_DIRS.some((storeDir) => isInside(storeDir, absPath));
}

const dataNotFound = () => Object.assign(new Error('Data path not found'), { status: 404, code: 'NOT_FOUND' });

// Top-level registrations are the ownership boundary. Resolve from the
// configured data root before opening anything, and do not follow links.
function canViewDataPath(viewer, path) {
  const top = relative(DATA_DIR, path).split(sep)[0];
  const row = top && stmts.getFolderByName.get(top);
  const registered = row && relative(join(DATA_DIR, top), resolve(row.path)) === '';
  return canView(viewer, registered ? row.owner_user_id : null);
}

export async function requireDataPath(relativePath, viewer, { directory = false } = {}) {
  // label kept as 'folder': the route-level traversal contract (400
  // PATH_OUTSIDE_BASE, "Invalid folder: …") is asserted verbatim by tests.
  const path = resolveInside(DATA_DIR, String(relativePath || '.'), { label: 'folder' });
  if (!canViewDataPath(viewer, path) || isRefusedReadPath(path)) throw dataNotFound();
  let current = DATA_DIR;
  let info = await lstat(current).catch(() => null);
  if (!info || info.isSymbolicLink()) throw dataNotFound();
  for (const part of relative(DATA_DIR, path).split(sep).filter(Boolean)) {
    current = join(current, part);
    info = await lstat(current).catch(() => null);
    if (!info || info.isSymbolicLink()) throw dataNotFound();
  }
  if (directory ? !info.isDirectory() : !info.isFile()) throw dataNotFound();
  return path;
}

export async function listDataFolder(relativePath = '', viewer = INTERNAL) {
  const path = resolveInside(DATA_DIR, String(relativePath || '.'), { label: 'folder' });
  if (path === DATA_DIR) {
    return (await listDataDir(DATA_DIR)).filter(({ name }) => canViewDataPath(viewer, join(DATA_DIR, name)));
  }
  return listDataDir(await requireDataPath(relativePath, viewer, { directory: true }));
}

// List contents of a data directory with metadata
export async function listDataDir(dir) {
  if (!existsSync(dir)) return [];
  const entries = await readdir(dir);
  const result = [];
  for (const entry of entries) {
    if (entry.startsWith('.') || entry === 'references' || isSystemDatabaseFile(entry)) continue;
    const fullPath = join(dir, entry);
    try {
      const s = await lstat(fullPath);
      if (s.isSymbolicLink() || isRefusedReadPath(fullPath)) continue;
      result.push({
        name: entry,
        type: s.isDirectory() ? 'folder' : 'file',
        size: s.size,
        modified: s.mtime.toISOString(),
        ext: extname(entry).toLowerCase(),
      });
    } catch (e) { logger.error(`Error: ${e.message}`, { context: 'Files' }); }
  }
  return result.sort((a, b) => {
    if (a.type !== b.type) return a.type === 'folder' ? -1 : 1;
    return a.name.localeCompare(b.name);
  });
}

// Recursively list all files in a directory tree
export async function listDirRecursive(dir, base, prefix = '') {
  const entries = await readdir(dir);
  const files = [];
  for (const entry of entries) {
    const fullPath = join(dir, entry);
    const s = await stat(fullPath);
    const relPath = prefix ? `${prefix}/${entry}` : entry;
    if (s.isDirectory()) {
      files.push(...await listDirRecursive(fullPath, base, relPath));
    } else {
      files.push({
        name: entry,
        path: relPath,
        size: s.size,
        ext: extname(entry).toLowerCase(),
      });
    }
  }
  return files;
}

// List all diagnostic workspace runs the viewer may see (own runs; all for an
// admin; a directory with no matching run row is unowned → admin-only).
export async function listWorkspaceRuns(viewer = INTERNAL) {
  const runsDir = RUNS_DIR;
  if (!existsSync(runsDir)) return [];

  const entries = await readdir(runsDir);
  const runs = [];
  for (const entry of entries) {
    const fullPath = join(runsDir, entry);
    const s = await stat(fullPath);
    if (s.isDirectory()) {
      if (!canViewWorkspaceRun(viewer, entry)) continue;
      const reportPath = join(fullPath, pipeConfig.report_filename);
      const optimizerPath = join(fullPath, pipeConfig.optimizer_filename);
      runs.push({
        name: entry,
        path: `workspace/diagnostic-runs/${entry}`,
        review_run_id: workspaceReviewId(entry, viewer),
        hasReport: existsSync(reportPath),
        hasOptimizer: existsSync(optimizerPath),
        hasHtml: existsSync(join(fullPath, 'diagnostic-report.html')),
        created: s.mtime.toISOString(),
      });
    }
  }
  runs.sort((a, b) => new Date(b.created) - new Date(a.created));
  return runs;
}

// Get workspace report content (viewer-scoped: null → route answers 404)
export async function getWorkspaceReport(runName, viewer = INTERNAL) {
  if (!canViewWorkspaceRun(viewer, runName)) return null;
  const runDir = resolveRunDir(runName);
  if (!runDir) return null;
  const reportPath = join(runDir, pipeConfig.report_filename);
  if (!existsSync(reportPath)) return null;
  const content = await readFile(reportPath, 'utf-8');
  return { name: runName, content };
}

// Get workspace optimizer content (viewer-scoped)
export async function getWorkspaceOptimizer(runName, viewer = INTERNAL) {
  if (!canViewWorkspaceRun(viewer, runName)) return null;
  const runDir = resolveRunDir(runName);
  if (!runDir) return null;
  const optimizerPath = join(runDir, pipeConfig.optimizer_filename);
  if (!existsSync(optimizerPath)) return null;
  const content = await readFile(optimizerPath, 'utf-8');
  return { name: runName, content };
}

// List files in a diagnostic run workspace (viewer-scoped)
export async function listWorkspaceFiles(runName, viewer = INTERNAL) {
  if (!canViewWorkspaceRun(viewer, runName)) return null;
  const runDir = resolveRunDir(runName);
  if (!runDir || !existsSync(runDir)) return null;
  return await listDirRecursive(runDir, runDir);
}

// HTML reports produced inside a run dir, as run-relative paths sorted with
// root-level artifacts first (the conventional primary report). Consumed by
// the Reports viewer to render one HTML tab per artifact, whatever filename
// convention the executing skill used. (viewer-scoped)
export async function listWorkspaceHtml(runName, viewer = INTERNAL) {
  if (!/^[A-Za-z0-9][A-Za-z0-9_.-]*$/.test(String(runName))) {
    const err = new Error('Invalid run name');
    err.status = 400;
    throw err;
  }
  if (!canViewWorkspaceRun(viewer, runName)) return null;
  const runDir = resolveRunDir(runName);
  if (!runDir || !existsSync(runDir)) return null;
  const files = await listDirRecursive(runDir, runDir);
  return files
    .filter((f) => f.ext === '.html')
    .map((f) => f.path)
    .sort((a, b) => {
      const depth = a.split('/').length - b.split('/').length;
      return depth !== 0 ? depth : a.localeCompare(b);
    });
}

// Create a data subfolder. `ownerUserId` (a user object or an id) becomes the
// row's owner_user_id; NULL when the request had no identity (AUTH_ENABLED=0).
export async function createDataFolder(name, description = '', ownerUserId = null) {
  const folderPath = resolveInside(DATA_DIR, name, { label: 'folder name' });
  if (existsSync(folderPath)) {
    const err = new Error('Folder already exists');
    err.status = 409;
    throw err;
  }
  await mkdir(folderPath, { recursive: true });
  stmts.insertFolder.run({
    name,
    path: folderPath,
    description,
    fileCount: 0,
    ownerUserId: resolveOwnerId(ownerUserId),
  });
  return { name, path: folderPath };
}

// Delete an empty data subfolder. Ownership first (a folder the viewer may not
// see answers 404 exactly like a missing one — including a registered folder
// owned by another user and an unregistered (unowned) directory, which is
// admin-only once auth is on).
export async function deleteDataFolder(name, viewer = INTERNAL) {
  if (isSystemDatabaseFile(name)) {
    const err = new Error('System database file cannot be deleted');
    err.status = 400;
    throw err;
  }
  const row = stmts.getFolderByName.get(String(name));
  if (!canView(viewer, row ? row.owner_user_id : null)) {
    const err = new Error('Folder not found');
    err.status = 404;
    err.code = 'NOT_FOUND';
    throw err;
  }
  const folderPath = resolveInside(DATA_DIR, name, { label: 'folder name' });
  if (!existsSync(folderPath)) {
    const err = new Error('Folder not found');
    err.status = 404;
    throw err;
  }
  const entries = await readdir(folderPath);
  if (entries.length > 0) {
    const err = new Error('Folder is not empty');
    err.status = 400;
    throw err;
  }
  await rm(folderPath, { recursive: true });
  try { stmts.deleteFolder.run(name); } catch (e) { logger.error(`Error: ${e.message}`, { context: 'Files' }); }
  return true;
}

// Read a file (for preview) — returns content text with optional binary mode.
// Tenant rule: a path inside a run directory (workspace/diagnostic-runs/<name>/…)
// is a run-scoped artifact and follows that run's owner; foreign → 404.
// Containment is decided on REAL paths (a symlink/junction cannot escape), and
// hidden files / the system database are never user-facing data: the JWT secret
// lives at data/.auth-jwt-secret, so a prefix check alone would leak it.
export async function readDataFile(filePath, viewer = INTERNAL) {
  // `filePath` is a PROJECT_ROOT-relative path from the preview route. Resolve
  // it against the project root, then prove it lands under one of the two
  // readable roots by segment — the old string-prefix check also admitted
  // siblings named like the roots (`workspace-evil/`, `data-evil/`).
  let absPath;
  try {
    absPath = resolveInside(PROJECT_ROOT, filePath, { label: 'file path' });
  } catch {
    absPath = null;
  }
  if (!absPath || (!isInside(DATA_DIR, absPath) && !isInside(WORKSPACE_DIR, absPath))) {
    const err = new Error('Access denied');
    err.status = 403;
    throw err;
  }
  const runName = workspaceRunNameOfPath(absPath);
  if (runName && !canViewWorkspaceRun(viewer, runName)) {
    const err = new Error('File not found');
    err.status = 404;
    throw err;
  }
  // Shape-based refusal runs after the tenant rule (a foreign run's artifact
  // still answers 404, never a 403 that would confirm it) and BEFORE any
  // filesystem access — existence of a system file must not be probeable
  // either. Same 403 'Access denied' this function already answers with.
  if (isRefusedReadPath(absPath)) {
    const err = new Error('Access denied');
    err.status = 403;
    throw err;
  }
  if (isInside(DATA_DIR, absPath)) {
    await requireDataPath(relative(DATA_DIR, absPath), viewer);
  } else if (!runName && !canView(viewer, null)) {
    throw dataNotFound();
  }
  if (!existsSync(absPath)) {
    const err = new Error('File not found');
    err.status = 404;
    throw err;
  }
  const [absReal, dataReal, wsReal] = await Promise.all([
    realpath(absPath).catch(() => null),
    realpath(DATA_DIR).catch(() => null),
    realpath(join(PROJECT_ROOT, 'workspace')).catch(() => null),
  ]);
  if (!absReal) {
    const err = new Error('File not found');
    err.status = 404;
    throw err;
  }
  const inside = (root) => Boolean(root) && (absReal === root || absReal.startsWith(root + sep));
  if (!inside(dataReal) && !inside(wsReal)) {
    const err = new Error('Access denied');
    err.status = 403;
    throw err;
  }
  const rel = inside(dataReal) ? relative(dataReal, absReal) : relative(wsReal, absReal);
  if (rel.split(sep).some((seg) => seg.startsWith('.'))) {
    const err = new Error('Access denied');
    err.status = 403;
    throw err;
  }
  if (isSystemDatabaseFile(basename(absReal))) {
    const err = new Error('Access denied');
    err.status = 403;
    throw err;
  }
  const content = await readFile(absReal, 'utf-8');
  const preview = content.slice(0, dataConfig.file_preview_max_chars);
  return { path: filePath, content: preview, size: content.length, fullContent: content };
}

// Serve workspace asset with path traversal protection (viewer-scoped: a run
// the viewer may not see is null → route 404, not a 403 that would confirm it).
export async function getWorkspaceAsset(runName, subpath, viewer = INTERNAL) {
  if (!canViewWorkspaceRun(viewer, runName)) return null;
  const runDir = resolveRunDir(runName);
  if (!runDir) return null;
  const filePath = join(runDir, subpath);
  if (!existsSync(filePath)) return null;

  const { realpath: resolvePath } = await import('fs/promises');
  const resolved = await resolvePath(filePath);
  // Containment base must be the RESOLVED directory of the run being served,
  // not the runs root: `<runA>/../<runB>/report.md` stays inside diagnostic-runs
  // (so a root-based check admits it) while serving ANOTHER run's file. The run
  // dir itself may be a junction (run-archive migration), so both sides of the
  // comparison are realpaths — comparing against the un-resolved run dir would
  // 403 every asset on such installs.
  const runRoot = await resolvePath(runDir);

  if (resolved !== runRoot && !resolved.startsWith(runRoot + sep)) {
    const err = new Error('Access denied');
    err.status = 403;
    throw err;
  }

  const ext = extname(filePath).toLowerCase();
  const contentType = config.mime_types[ext] || 'application/octet-stream';
  const content = await readFile(filePath);

  return { content, contentType, ext };
}

function normalizeDirectoryPath(rawPath) {
  const requested = typeof rawPath === 'string' && rawPath.trim() ? rawPath.trim() : PROJECT_ROOT;
  return resolve(requested);
}

function platformRoots() {
  if (process.platform === 'win32') {
    const drives = [];
    for (let code = 65; code <= 90; code++) {
      const drive = `${String.fromCharCode(code)}:\\`;
      if (existsSync(drive)) drives.push(drive);
    }
    const home = homedir();
    return [home, ...drives].filter(Boolean);
  }
  if (process.platform === 'darwin') return ['/Users', '/Volumes'];
  return ['/tmp', homedir() || '/root'];
}

export async function listChatDirectories(rawPath = PROJECT_ROOT) {
  const resolved = normalizeDirectoryPath(rawPath);
  if (!existsSync(resolved)) {
    const err = new Error(`Directory not found: ${resolved}`);
    err.status = 404;
    throw err;
  }

  const resolvedReal = await realpath(resolved);
  const dirStat = await stat(resolvedReal);
  if (!dirStat.isDirectory()) {
    const err = new Error(`Not a directory: ${resolvedReal}`);
    err.status = 400;
    throw err;
  }

  const children = [];
  for (const entry of await readdir(resolvedReal)) {
    if (entry.startsWith('.')) continue;
    const fullPath = join(resolvedReal, entry);
    try {
      const entryStat = await stat(fullPath);
      if (!entryStat.isDirectory()) continue;
      children.push({
        name: entry,
        path: fullPath,
        modified: entryStat.mtime.toISOString(),
      });
    } catch (err) {
      logger.warn(`Skipping directory entry ${fullPath}: ${err.message}`, { context: 'Files' });
    }
  }

  children.sort((a, b) => a.name.localeCompare(b.name));

  const quickRoots = [
    PROJECT_ROOT,
    DATA_DIR,
    join(PROJECT_ROOT, 'workspace'),
    ...platformRoots(),
  ].filter((value, index, list) => value && list.indexOf(value) === index && existsSync(value));

  return {
    path: resolvedReal,
    parent: resolvedReal === dirname(resolvedReal) ? null : dirname(resolvedReal),
    children,
    quickRoots,
  };
}

export async function pickChatDirectory(rawPath = PROJECT_ROOT) {
  const defaultPath = normalizeDirectoryPath(rawPath);

  let pickerBinary = 'osascript';
  let pickerArgs = [];
  let pickerOpts = {};

  if (process.platform === 'win32') {
    const psScript = [
      'Add-Type -AssemblyName System.Windows.Forms',
      '$d = New-Object System.Windows.Forms.FolderBrowserDialog',
      `$d.SelectedPath = '${defaultPath.replace(/'/g, "''")}'`,
      '$d.ShowNewFolderButton = $true',
      'if ($d.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { Write-Output $d.SelectedPath }',
    ].join('; ');
    pickerBinary = 'powershell.exe';
    pickerArgs = ['-NoProfile', '-STA', '-Command', psScript];
    pickerOpts = { env: { ...process.env, CODEX_CHAT_PICKER_DEFAULT_PATH: defaultPath }, timeout: 120000 };
  } else if (process.platform === 'darwin') {
    const script = [
      'set defaultFolder to POSIX file (system attribute "CODEX_CHAT_PICKER_DEFAULT_PATH")',
      'set chosenFolder to choose folder with prompt "选择 Chat 工作目录" default location defaultFolder',
      'POSIX path of chosenFolder',
    ];
    pickerArgs = script.flatMap(line => ['-e', line]);
    pickerOpts = { env: { ...process.env, CODEX_CHAT_PICKER_DEFAULT_PATH: defaultPath }, timeout: 120000 };
  } else {
    const err = new Error('Native folder picker is currently supported on macOS and Windows only');
    err.status = 501;
    throw err;
  }

  try {
    const { stdout } = await execFile(
      pickerBinary,
      pickerArgs,
      pickerOpts,
    );

    const rawChosen = String(stdout || '').trim();
    if (!rawChosen) {
      return { canceled: true, path: null };
    }

    const selected = normalizeDirectoryPath(rawChosen);
    if (!existsSync(selected)) {
      const err = new Error(`Selected directory not found: ${selected}`);
      err.status = 400;
      throw err;
    }

    const selectedReal = await realpath(selected);
    const dirStat = await stat(selectedReal);
    if (!dirStat.isDirectory()) {
      const err = new Error(`Selected path is not a directory: ${selectedReal}`);
      err.status = 400;
      throw err;
    }

    return {
      canceled: false,
      path: selectedReal,
    };
  } catch (err) {
    const stderr = String(err?.stderr || '');
    const message = String(err?.message || '');
    if (/User canceled|execution error: User canceled/i.test(`${stderr}\n${message}`)) {
      return {
        canceled: true,
        path: null,
      };
    }
    throw err;
  }
}

export { DATA_DIR };
