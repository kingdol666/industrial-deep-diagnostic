// File Routes — Thin HTTP handlers, delegates business logic to file service
//
// Tenancy (P0-6): run-scoped reads (workspace report/files/html/asset/preview
// inside a run dir) and folder writes are viewer-scoped — a resource the caller
// may not see answers exactly like a missing one (404 / null), never 403.

import { Router } from 'express';
import multer from 'multer';
import { join, basename } from 'path';
import { existsSync } from 'fs';
import { config, PROJECT_ROOT, data as dataConfig } from '../../../../config/loader.mjs';
import {
  listDataDir, listDataFolder, createDataFolder, deleteDataFolder,
  listWorkspaceRuns, getWorkspaceReport, getWorkspaceOptimizer,
  listWorkspaceFiles, listWorkspaceHtml, getWorkspaceAsset, readDataFile, isSystemDatabaseFile, DATA_DIR,
} from '../services/files.service.mjs';
import { rewriteHtmlAssetUrls, callerToken, isHtmlContentType } from '../utils/html-assets.mjs';
import { resolveInside, sanitizeFileName } from '../utils/pathGuard.mjs';
import { userRateLimit } from '../services/tenancy.mjs';
import logger from '../utils/logger.mjs';

const UPLOAD_DIR = join(PROJECT_ROOT, dataConfig.upload_dir);
const FOLDER_NAME_RE = new RegExp(dataConfig.folder_name_pattern);

const router = Router();

// 文件上传限流（P0-6）：config.security.upload_rate_limit（默认 20 次/分钟/用户）。
// 放在 multer 之前 —— 被限流的请求连 multipart 正文都不必解析。
// AUTH_ENABLED=0 下自动让行（见 tenancy.userRateLimit）。
const uploadLimitCfg = config.security?.upload_rate_limit || {};
const uploadRateLimit = userRateLimit({
  windowMs: Number(uploadLimitCfg.window_ms ?? uploadLimitCfg.windowMs ?? 60_000),
  max: Number(uploadLimitCfg.max ?? 20),
});

// Uniform error shape. PathViolationError carries status 400 + code
// PATH_OUTSIDE_BASE and validation 4xx keep their user-facing message; a 5xx
// answer is GENERIC with a stable code and the real error goes to the log
// (B4 leak class — an internal message must not reach the client).
function sendError(res, err, fallbackStatus = 500) {
  const status = err?.status || fallbackStatus;
  if (status >= 500) {
    logger.error(`[files] ${err?.stack || err?.message || err}`, { context: 'Files' });
    return res.status(status).json({
      success: false,
      code: err?.code || 'FILES_INTERNAL_ERROR',
      error: '文件服务内部错误，请查看后端日志后重试',
    });
  }
  const body = { success: false, error: err?.message || '请求无效' };
  if (err?.code) body.code = err.code;
  return res.status(status).json(body);
}

const upload = multer({
  dest: UPLOAD_DIR,
  limits: { fileSize: dataConfig.upload.max_file_size_mb * 1024 * 1024 },
});

// Browse a nested data folder using a safely resolved relative path.
router.get('/data/browse', async (req, res) => {
  try {
    const entries = await listDataFolder(req.query.path || '');
    res.json({ success: true, data: entries });
  } catch (err) {
    sendError(res, err);
  }
});

// List all data files and folders
router.get('/data', async (req, res) => {
  try {
    const entries = await listDataDir(DATA_DIR);
    res.json({ success: true, data: entries });
  } catch (err) {
    sendError(res, err);
  }
});

// List files in a subfolder
router.get('/data/:folder', async (req, res) => {
  try {
    // resolveInside proves containment segment-wise: a string prefix check let
    // `../data-evil` (a sibling whose name starts with "data") through.
    const folderPath = resolveInside(DATA_DIR, req.params.folder, { label: 'folder' });
    if (!existsSync(folderPath)) {
      return res.status(404).json({ success: false, error: 'Folder not found' });
    }
    const entries = await listDataDir(folderPath);
    res.json({ success: true, data: entries });
  } catch (err) {
    sendError(res, err);
  }
});

// Create a new subfolder (owned by the creator)
router.post('/data/folder', async (req, res) => {
  try {
    const { name, description } = req.body;
    if (!name || !FOLDER_NAME_RE.test(name)) {
      return res.status(400).json({ success: false, error: 'Invalid folder name' });
    }
    const result = await createDataFolder(name, description || '', req.user);
    res.json({ success: true, data: result });
  } catch (err) {
    sendError(res, err);
  }
});

// Delete a subfolder (only empty ones or user-created; owner/admin only)
router.delete('/data/folder/:name', async (req, res) => {
  try {
    await deleteDataFolder(req.params.name, req.user);
    res.json({ success: true });
  } catch (err) {
    sendError(res, err);
  }
});

// Upload files to a folder
router.post('/data/upload', uploadRateLimit, upload.array('files', dataConfig.upload.max_files), async (req, res) => {
  try {
    const folder = req.body.folder || req.query.folder || '';
    // Dot-dirs below data/ are system areas (e.g. the JWT secret and temp
    // upload staging live next to them) — never an upload target. Plain `.`/`..`
    // segments are traversal and stay with resolveInside (PATH_OUTSIDE_BASE).
    if (String(folder).split(/[\\/]+/).some((s) => s.startsWith('.') && s !== '.' && s !== '..')) {
      return res.status(400).json({ success: false, error: 'Dot folders are not valid upload targets' });
    }
    const targetDir = folder
      ? resolveInside(DATA_DIR, folder, { label: 'folder' })
      : DATA_DIR;
    if (!existsSync(targetDir)) {
      const { mkdir } = await import('fs/promises');
      await mkdir(targetDir, { recursive: true });
    }

    const uploaded = [];
    for (const file of req.files || []) {
      // The multipart filename is fully attacker-controlled: it may carry
      // directory components (`../`, `C:\`) that would rename the temp file
      // outside targetDir. Reduce it to a safe leaf name first.
      const safeName = sanitizeFileName(file.originalname);
      if (!safeName) {
        return res.status(400).json({ success: false, error: 'Invalid file name' });
      }
      // A dot name would overwrite system files (e.g. `.auth-jwt-secret`
      // signs every session) — the read path hides dotfiles for the same reason.
      if (safeName.startsWith('.')) {
        return res.status(400).json({ success: false, error: 'Dot files cannot be uploaded' });
      }
      // Uploading resolves an arbitrary name — a file named like the system
      // database would overwrite the live DB, so refuse it up front.
      if (isSystemDatabaseFile(safeName)) {
        return res.status(400).json({ success: false, error: 'System database file cannot be uploaded' });
      }
      // sanitizeFileName returns a bare leaf name (no separators, not `.`/`..`),
      // so joining it onto the already-verified targetDir cannot escape.
      const destPath = join(targetDir, safeName);
      const { rename } = await import('fs/promises');
      await rename(file.path, destPath);
      uploaded.push({
        name: safeName,
        size: file.size,
        path: folder ? `data/${folder}/${safeName}` : `data/${safeName}`,
      });
    }
    res.json({ success: true, data: uploaded });
  } catch (err) {
    sendError(res, err);
  }
});

// Read file content (for preview)
router.get('/data/file/*', async (req, res) => {
  try {
    const { ext } = req.query;
    const result = await readDataFile(req.params[0], req.user);

    if (ext === 'binary') {
      res.setHeader('Content-Type', 'application/octet-stream');
      res.setHeader('Content-Disposition', `attachment; filename="${basename(req.params[0])}"`);
      return res.send(Buffer.from(result.fullContent, 'utf-8'));
    }
    res.json({ success: true, data: { path: result.path, content: result.content, size: result.size } });
  } catch (err) {
    sendError(res, err);
  }
});

// List diagnostic run results (own runs; all for an admin)
router.get('/workspace', async (req, res) => {
  try {
    const runs = await listWorkspaceRuns(req.user);
    res.json({ success: true, data: runs });
  } catch (err) {
    sendError(res, err);
  }
});

// Get report content
router.get('/workspace/report/:runName', async (req, res) => {
  try {
    const report = await getWorkspaceReport(req.params.runName, req.user);
    if (!report) return res.status(404).json({ success: false, error: 'Report not found' });
    res.json({ success: true, data: report });
  } catch (err) {
    sendError(res, err);
  }
});

// Get optimizer content
router.get('/workspace/optimizer/:runName', async (req, res) => {
  try {
    const optimizer = await getWorkspaceOptimizer(req.params.runName, req.user);
    if (!optimizer) return res.status(404).json({ success: false, error: 'optimizer.md not found' });
    res.json({ success: true, data: optimizer });
  } catch (err) {
    sendError(res, err);
  }
});

// List files in a diagnostic run workspace
router.get('/workspace/files/:runName', async (req, res) => {
  try {
    const files = await listWorkspaceFiles(req.params.runName, req.user);
    if (!files) return res.status(404).json({ success: false, error: 'Run not found' });
    res.json({ success: true, data: files });
  } catch (err) {
    sendError(res, err);
  }
});

// List the HTML reports produced inside a run dir (any subdirectory). The
// Reports viewer renders one tab per entry so every analysis skill's HTML
// artifact is viewable regardless of the filename convention it uses.
router.get('/workspace/html/:runName', async (req, res) => {
  try {
    const htmls = await listWorkspaceHtml(req.params.runName, req.user);
    if (!htmls) return res.status(404).json({ success: false, error: 'Run not found' });
    res.json({ success: true, data: htmls });
  } catch (err) {
    sendError(res, err);
  }
});

// Serve workspace asset files (images, etc.) for report rendering
router.get('/workspace/asset/:runName/*', async (req, res) => {
  try {
    const asset = await getWorkspaceAsset(req.params.runName, req.params[0], req.user);
    if (!asset) return res.status(404).json({ success: false, error: 'File not found' });

    res.setHeader('Content-Type', asset.contentType);
    res.setHeader('Cache-Control', `public, max-age=${dataConfig.asset_cache_max_age}`);

    // A generated report references its figures with run-relative paths. This
    // route has no static handler, so those URLs must be rewritten before the
    // document reaches the browser — and the token forwarded, because the
    // resulting <img> requests cannot carry an Authorization header.
    if (isHtmlContentType(asset.contentType)) {
      const html = asset.content.toString('utf8');
      return res.send(rewriteHtmlAssetUrls(html, req.params.runName, callerToken(req)));
    }

    res.send(asset.content);
  } catch (err) {
    sendError(res, err);
  }
});

export default router;
