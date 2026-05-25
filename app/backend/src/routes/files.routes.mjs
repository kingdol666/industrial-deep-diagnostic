// File Routes — Thin HTTP handlers, delegates business logic to file service

import { Router } from 'express';
import multer from 'multer';
import { join, basename } from 'path';
import { existsSync } from 'fs';
import { config, PROJECT_ROOT, data as dataConfig } from '../../../../config/loader.mjs';
import {
  listDataDir, createDataFolder, deleteDataFolder,
  listWorkspaceRuns, getWorkspaceReport, getWorkspaceOptimizer,
  listWorkspaceFiles, getWorkspaceAsset, readDataFile, DATA_DIR,
} from '../services/files.service.mjs';

const UPLOAD_DIR = join(PROJECT_ROOT, dataConfig.upload_dir);
const FOLDER_NAME_RE = new RegExp(dataConfig.folder_name_pattern);

const router = Router();

const upload = multer({
  dest: UPLOAD_DIR,
  limits: { fileSize: dataConfig.upload.max_file_size_mb * 1024 * 1024 },
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
    const folderPath = join(DATA_DIR, req.params.folder);
    if (!folderPath.startsWith(DATA_DIR)) {
      return res.status(400).json({ success: false, error: 'Invalid path' });
    }
    if (!existsSync(folderPath)) {
      return res.status(404).json({ success: false, error: 'Folder not found' });
    }
    const entries = await listDataDir(folderPath);
    res.json({ success: true, data: entries });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
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
    const folder = req.body.folder || req.query.folder || '';
    const targetDir = folder ? join(DATA_DIR, folder) : DATA_DIR;
    if (!targetDir.startsWith(DATA_DIR)) {
      return res.status(400).json({ success: false, error: 'Invalid path' });
    }
    if (!existsSync(targetDir)) {
      const { mkdir } = await import('fs/promises');
      await mkdir(targetDir, { recursive: true });
    }

    const uploaded = [];
    for (const file of req.files || []) {
      const destPath = join(targetDir, file.originalname);
      const { rename } = await import('fs/promises');
      await rename(file.path, destPath);
      uploaded.push({
        name: file.originalname,
        size: file.size,
        path: folder ? `data/${folder}/${file.originalname}` : `data/${file.originalname}`,
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

// Get optimizer content
router.get('/workspace/optimizer/:runName', async (req, res) => {
  try {
    const optimizer = await getWorkspaceOptimizer(req.params.runName);
    if (!optimizer) return res.status(404).json({ success: false, error: 'optimizer.md not found' });
    res.json({ success: true, data: optimizer });
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

// Serve workspace asset files (images, etc.) for report rendering
router.get('/workspace/asset/:runName/*', async (req, res) => {
  try {
    const asset = await getWorkspaceAsset(req.params.runName, req.params[0]);
    if (!asset) return res.status(404).json({ success: false, error: 'File not found' });

    res.setHeader('Content-Type', asset.contentType);
    res.setHeader('Cache-Control', `public, max-age=${dataConfig.asset_cache_max_age}`);
    res.send(asset.content);
  } catch (err) {
    const status = err.status || 500;
    res.status(status).json({ success: false, error: err.message });
  }
});

export default router;
