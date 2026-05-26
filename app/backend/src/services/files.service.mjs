// File Service — Data directory listing and file management logic

import { readdir, stat, mkdir, rm, readFile } from 'fs/promises';
import { existsSync } from 'fs';
import { join, extname } from 'path';
import { config, PROJECT_ROOT, data as dataConfig, pipeline as pipeConfig } from '../../../../config/loader.mjs';
import logger from '../utils/logger.mjs';
import { stmts } from '../db/database.mjs';

const DATA_DIR = join(PROJECT_ROOT, dataConfig.dir);

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

export { DATA_DIR };
