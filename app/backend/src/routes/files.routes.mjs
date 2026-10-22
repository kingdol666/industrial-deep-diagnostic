// File Routes — Thin HTTP handlers, delegates business logic to file service

import { Router } from 'express';
import multer from 'multer';
import { join, basename, resolve, relative, isAbsolute, sep } from 'path';
import { existsSync } from 'fs';
import { config, PROJECT_ROOT, data as dataConfig } from '../../../../config/loader.mjs';
import {
  listDataDir, listDataFolder, createDataFolder, deleteDataFolder,
  listWorkspaceRuns, getWorkspaceReport, getWorkspaceOptimizer,
  listWorkspaceFiles, listWorkspaceHtml, getWorkspaceAsset, readDataFile, isSystemDatabaseFile, DATA_DIR,
} from '../services/files.service.mjs';
import { rewriteHtmlAssetUrls, callerToken, isHtmlContentType } from '../utils/html-assets.mjs';

const UPLOAD_DIR = join(PROJECT_ROOT, dataConfig.upload_dir);
const FOLDER_NAME_RE = new RegExp(dataConfig.folder_name_pattern);

const router = Router();

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
    res.status(err.status || 500).json({ success: false, error: err.message });
  }
});

// List all data files and folders
router.get('/data', async (req, res) => {
  try {
    const entries = await listDataDir(DATA_DIR);
    res.json({ success: true, data: entries });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

// List files in a subfolder
router.get('/data/:folder', async (req, res) => {
  try {
    // listDataFolder resolves real paths and rejects traversal / non-folders;
    // a join()+startsWith() prefix check is not containment (data-evil would pass).
    const entries = await listDataFolder(req.params.folder);
    res.json({ success: true, data: entries });
  } catch (err) {
    res.status(err.status || 500).json({ success: false, error: err.message });
  }
});

// Create a new subfolder
router.post('/data/folder', async (req, res) => {
  try {
    const { name, description } = req.body;
    if (!name || !FOLDER_NAME_RE.test(name)) {
      return res.status(400).json({ success: false, error: 'Invalid folder name' });
    }
    const result = await createDataFolder(name, description || '');
    res.json({ success: true, data: result });
  } catch (err) {
    const status = err.status || 500;
    res.status(status).json({ success: false, error: err.message });
  }
});

// Delete a subfolder (only empty ones or user-created)
router.delete('/data/folder/:name', async (req, res) => {
  try {
    await deleteDataFolder(req.params.name);
    res.json({ success: true });
  } catch (err) {
    const status = err.status || 500;
    res.status(status).json({ success: false, error: err.message });
  }
});

// Upload files to a folder
router.post('/data/upload', upload.array('files', dataConfig.upload.max_files), async (req, res) => {
  try {
    const folder = String(req.body.folder || req.query.folder || '');
    // Real containment: resolve() normalises "..", then relative() decides
    // whether the result is still inside DATA_DIR. startsWith() would let a
    // sibling whose name shares the prefix through.
    const targetDir = folder ? resolve(DATA_DIR, folder) : DATA_DIR;
    const relDir = relative(DATA_DIR, targetDir);
    if (relDir === '..' || relDir.startsWith(`..${sep}`) || isAbsolute(relDir)) {
      return res.status(400).json({ success: false, error: 'Invalid path' });
    }
    if (!existsSync(targetDir)) {
      const { mkdir } = await import('fs/promises');
      await mkdir(targetDir, { recursive: true });
    }

    const uploaded = [];
    for (const file of req.files || []) {
      // The multipart filename is client-controlled: keep only its basename so
      // a crafted "../../x" cannot escape targetDir, and keep the live DB safe.
      const name = basename(String(file.originalname || ''));
      if (!name || name === '.' || name === '..') {
        return res.status(400).json({ success: false, error: 'Invalid file name' });
      }
      if (isSystemDatabaseFile(name)) {
        return res.status(400).json({ success: false, error: 'System database file cannot be uploaded' });
      }
      const destPath = join(targetDir, name);
      const { rename } = await import('fs/promises');
      await rename(file.path, destPath);
      uploaded.push({
        name,
        size: file.size,
        path: folder ? `data/${folder}/${name}` : `data/${name}`,
      });
    }
    res.json({ success: true, data: uploaded });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

// Read file content (for preview)
router.get('/data/file/*', async (req, res) => {
  try {
    const { ext } = req.query;
    const result = await readDataFile(req.params[0]);

    if (ext === 'binary') {
      res.setHeader('Content-Type', 'application/octet-stream');
      res.setHeader('Content-Disposition', `attachment; filename="${basename(req.params[0])}"`);
      return res.send(Buffer.from(result.fullContent, 'utf-8'));
    }
    res.json({ success: true, data: { path: result.path, content: result.content, size: result.size } });
  } catch (err) {
    const status = err.status || 500;
    res.status(status).json({ success: false, error: err.message });
  }
});

// List diagnostic run results
router.get('/workspace', async (req, res) => {
  try {
    const runs = await listWorkspaceRuns();
    res.json({ success: true, data: runs });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

// Get report content
router.get('/workspace/report/:runName', async (req, res) => {
  try {
    const report = await getWorkspaceReport(req.params.runName);
    if (!report) return res.status(404).json({ success: false, error: 'Report not found' });
    res.json({ success: true, data: report });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

// Get optimizer content. The report viewer probes this for EVERY opened run,
// and most runs have no optimizer.md — same convention as the harness artifact
// endpoints: 200 + null instead of a 404 that only feeds the console.
router.get('/workspace/optimizer/:runName', async (req, res) => {
  try {
    const optimizer = await getWorkspaceOptimizer(req.params.runName);
    res.json({ success: true, data: optimizer ?? null });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

// List files in a diagnostic run workspace
router.get('/workspace/files/:runName', async (req, res) => {
  try {
    const files = await listWorkspaceFiles(req.params.runName);
    if (!files) return res.status(404).json({ success: false, error: 'Run not found' });
    res.json({ success: true, data: files });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

// List the HTML reports produced inside a run dir (any subdirectory). The
// Reports viewer renders one tab per entry so every analysis skill's HTML
// artifact is viewable regardless of the filename convention it uses.
router.get('/workspace/html/:runName', async (req, res) => {
  try {
    const htmls = await listWorkspaceHtml(req.params.runName);
    res.json({ success: true, data: htmls });
  } catch (err) {
    const status = err.status || 500;
    res.status(status).json({ success: false, error: err.message });
  }
});

// Serve workspace asset files (images, etc.) for report rendering
router.get('/workspace/asset/:runName/*', async (req, res) => {
  try {
    const asset = await getWorkspaceAsset(req.params.runName, req.params[0]);
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
    const status = err.status || 500;
    res.status(status).json({ success: false, error: err.message });
  }
});

export default router;
