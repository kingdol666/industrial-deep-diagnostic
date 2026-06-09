// File Service — Data directory listing and file management logic

import { readdir, stat, mkdir, rm, readFile, realpath } from 'fs/promises';
import { existsSync } from 'fs';
import { execFile as execFileCallback } from 'child_process';
import { join, extname, dirname, resolve } from 'path';
import { promisify } from 'util';
import { config, PROJECT_ROOT, data as dataConfig, pipeline as pipeConfig } from '../../../../config/loader.mjs';
import logger from '../utils/logger.mjs';
import { stmts } from '../db/database.mjs';

const DATA_DIR = join(PROJECT_ROOT, dataConfig.dir);
const execFile = promisify(execFileCallback);

// List contents of a data directory with metadata
export async function listDataDir(dir) {
  if (!existsSync(dir)) return [];
  const entries = await readdir(dir);
  const result = [];
  for (const entry of entries) {
    if (entry.startsWith('.') || entry === 'references') continue;
    const fullPath = join(dir, entry);
    try {
      const s = await stat(fullPath);
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

// List all diagnostic workspace runs
export async function listWorkspaceRuns() {
  const runsDir = join(PROJECT_ROOT, 'workspace', 'diagnostic-runs');
  if (!existsSync(runsDir)) return [];

  const entries = await readdir(runsDir);
  const runs = [];
  for (const entry of entries) {
    const fullPath = join(runsDir, entry);
    const s = await stat(fullPath);
    if (s.isDirectory()) {
      const reportPath = join(fullPath, pipeConfig.report_filename);
      const optimizerPath = join(fullPath, pipeConfig.optimizer_filename);
      runs.push({
        name: entry,
        path: `workspace/diagnostic-runs/${entry}`,
        hasReport: existsSync(reportPath),
        hasOptimizer: existsSync(optimizerPath),
        created: s.mtime.toISOString(),
      });
    }
  }
  runs.sort((a, b) => new Date(b.created) - new Date(a.created));
  return runs;
}

// Get workspace report content
export async function getWorkspaceReport(runName) {
  const reportPath = join(PROJECT_ROOT, 'workspace', 'diagnostic-runs', runName, pipeConfig.report_filename);
  if (!existsSync(reportPath)) return null;
  const content = await readFile(reportPath, 'utf-8');
  return { name: runName, content };
}

// Get workspace optimizer content
export async function getWorkspaceOptimizer(runName) {
  const optimizerPath = join(PROJECT_ROOT, 'workspace', 'diagnostic-runs', runName, pipeConfig.optimizer_filename);
  if (!existsSync(optimizerPath)) return null;
  const content = await readFile(optimizerPath, 'utf-8');
  return { name: runName, content };
}

// List files in a diagnostic run workspace
export async function listWorkspaceFiles(runName) {
  const runDir = join(PROJECT_ROOT, 'workspace', 'diagnostic-runs', runName);
  if (!existsSync(runDir)) return null;
  return await listDirRecursive(runDir, runDir);
}

// Create a data subfolder
export async function createDataFolder(name, description = '') {
  const folderPath = join(DATA_DIR, name);
  if (existsSync(folderPath)) {
    const err = new Error('Folder already exists');
    err.status = 409;
    throw err;
  }
  await mkdir(folderPath, { recursive: true });
  stmts.insertFolder.run({ name, path: folderPath, description, fileCount: 0 });
  return { name, path: folderPath };
}

// Delete an empty data subfolder
export async function deleteDataFolder(name) {
  const folderPath = join(DATA_DIR, name);
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

// Read a file (for preview) — returns content text with optional binary mode
export async function readDataFile(filePath) {
  const absPath = join(PROJECT_ROOT, filePath);
  if (!absPath.startsWith(DATA_DIR) && !absPath.startsWith(join(PROJECT_ROOT, 'workspace'))) {
    const err = new Error('Access denied');
    err.status = 403;
    throw err;
  }
  if (!existsSync(absPath)) {
    const err = new Error('File not found');
    err.status = 404;
    throw err;
  }
  const content = await readFile(absPath, 'utf-8');
  const preview = content.slice(0, dataConfig.file_preview_max_chars);
  return { path: filePath, content: preview, size: content.length, fullContent: content };
}

// Serve workspace asset with path traversal protection
export async function getWorkspaceAsset(runName, subpath) {
  const filePath = join(PROJECT_ROOT, 'workspace', 'diagnostic-runs', runName, subpath);
  if (!existsSync(filePath)) return null;

  const { realpath: resolvePath } = await import('fs/promises');
  const resolved = await resolvePath(filePath);
  const workspaceRoot = await resolvePath(join(PROJECT_ROOT, 'workspace'));

  if (!resolved.startsWith(workspaceRoot)) {
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
    '/Users',
    '/Volumes',
    '/tmp',
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

  if (process.platform !== 'darwin') {
    const err = new Error('Native folder picker is currently supported on macOS only');
    err.status = 501;
    throw err;
  }

  const script = [
    'set defaultFolder to POSIX file (system attribute "CODEX_CHAT_PICKER_DEFAULT_PATH")',
    'set chosenFolder to choose folder with prompt "选择 Chat 工作目录" default location defaultFolder',
    'POSIX path of chosenFolder',
  ];

  try {
    const { stdout } = await execFile(
      'osascript',
      script.flatMap(line => ['-e', line]),
      {
        env: {
          ...process.env,
          CODEX_CHAT_PICKER_DEFAULT_PATH: defaultPath,
        },
        timeout: 120000,
      },
    );

    const selected = normalizeDirectoryPath(stdout.trim());
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
