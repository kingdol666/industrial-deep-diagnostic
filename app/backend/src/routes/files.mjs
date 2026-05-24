import { Router } from 'express';
import multer from 'multer';
import { readdir, stat, mkdir, rm, writeFile } from 'fs/promises';
import { join, basename, extname } from 'path';
import { existsSync } from 'fs';
import { DATA_DIR, PROJECT_ROOT } from '../claude-code.mjs';
import { stmts } from '../db.mjs';

const router = Router();

const upload = multer({
  dest: join(PROJECT_ROOT, 'data', '.uploads'),
  limits: { fileSize: 500 * 1024 * 1024 },
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
    if (!name || !/^[a-zA-Z0-9_\-一-龥]+$/.test(name)) {
      return res.status(400).json({ success: false, error: 'Invalid folder name' });
    }
    const folderPath = join(DATA_DIR, name);
    if (existsSync(folderPath)) {
      return res.status(409).json({ success: false, error: 'Folder already exists' });
    }
    await mkdir(folderPath, { recursive: true });
    stmts.insertFolder.run({ name, path: folderPath, description: description || '', fileCount: 0 });
    res.json({ success: true, data: { name, path: folderPath } });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

// Delete a subfolder (only empty ones or user-created)
router.delete('/data/folder/:name', async (req, res) => {
  try {
    const { name } = req.params;
    const folderPath = join(DATA_DIR, name);
    if (!existsSync(folderPath)) {
      return res.status(404).json({ success: false, error: 'Folder not found' });
    }
    const files = await readdir(folderPath);
    if (files.length > 0) {
      return res.status(400).json({ success: false, error: 'Folder is not empty' });
    }
    await rm(folderPath, { recursive: true });
    try { stmts.deleteFolder.run(name); } catch {}
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

// Upload files to a folder
router.post('/data/upload', upload.array('files', 50), async (req, res) => {
  try {
    const folder = req.body.folder || req.query.folder || '';
    const targetDir = folder ? join(DATA_DIR, folder) : DATA_DIR;
    if (!targetDir.startsWith(DATA_DIR)) {
      return res.status(400).json({ success: false, error: 'Invalid path' });
    }
    if (!existsSync(targetDir)) {
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
    const filePath = join(PROJECT_ROOT, req.params[0]);
    if (!filePath.startsWith(DATA_DIR) && !filePath.startsWith(join(PROJECT_ROOT, 'workspace'))) {
      return res.status(403).json({ success: false, error: 'Access denied' });
    }
    if (!existsSync(filePath)) {
      return res.status(404).json({ success: false, error: 'File not found' });
    }
    const { readFile } = await import('fs/promises');
    const { ext } = req.query;
    const content = await readFile(filePath, ext === 'binary' ? null : 'utf-8');
    if (ext === 'binary') {
      res.setHeader('Content-Type', 'application/octet-stream');
      res.setHeader('Content-Disposition', `attachment; filename="${basename(filePath)}"`);
      return res.send(content);
    }
    const text = typeof content === 'string' ? content : content.toString('utf-8');
    const preview = text.slice(0, 50000);
    res.json({ success: true, data: { path: req.params[0], content: preview, size: text.length } });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

// List diagnostic run results
router.get('/workspace', async (req, res) => {
  try {
    const runsDir = join(PROJECT_ROOT, 'workspace', 'diagnostic-runs');
    if (!existsSync(runsDir)) {
      return res.json({ success: true, data: [] });
    }
    const entries = await readdir(runsDir);
    const runs = [];
    for (const entry of entries) {
      const fullPath = join(runsDir, entry);
      const s = await stat(fullPath);
      if (s.isDirectory()) {
        const reportPath = join(fullPath, 'report.md');
        const optimizerPath = join(fullPath, 'optimizer.md');
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
    res.json({ success: true, data: runs });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

// Get report content
router.get('/workspace/report/:runName', async (req, res) => {
  try {
    const reportPath = join(PROJECT_ROOT, 'workspace', 'diagnostic-runs', req.params.runName, 'report.md');
    if (!existsSync(reportPath)) {
      return res.status(404).json({ success: false, error: 'Report not found' });
    }
    const { readFile } = await import('fs/promises');
    const content = await readFile(reportPath, 'utf-8');
    res.json({ success: true, data: { name: req.params.runName, content } });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

// Get optimizer content
router.get('/workspace/optimizer/:runName', async (req, res) => {
  try {
    const optimizerPath = join(PROJECT_ROOT, 'workspace', 'diagnostic-runs', req.params.runName, 'optimizer.md');
    if (!existsSync(optimizerPath)) {
      return res.status(404).json({ success: false, error: 'optimizer.md not found' });
    }
    const { readFile } = await import('fs/promises');
    const content = await readFile(optimizerPath, 'utf-8');
    res.json({ success: true, data: { name: req.params.runName, content } });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

// List files in a diagnostic run workspace
router.get('/workspace/files/:runName', async (req, res) => {
  try {
    const runDir = join(PROJECT_ROOT, 'workspace', 'diagnostic-runs', req.params.runName);
    if (!existsSync(runDir)) {
      return res.status(404).json({ success: false, error: 'Run not found' });
    }
    const files = await listDirRecursive(runDir, runDir);
    res.json({ success: true, data: files });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

// Serve workspace asset files (images, etc.) for report rendering
router.get('/workspace/asset/:runName/*', async (req, res) => {
  try {
    const subpath = req.params[0];
    const filePath = join(PROJECT_ROOT, 'workspace', 'diagnostic-runs', req.params.runName, subpath);

    if (!existsSync(filePath)) {
      return res.status(404).json({ success: false, error: 'File not found' });
    }

    const { realpath: resolvePath } = await import('fs/promises');
    const resolved = await resolvePath(filePath);
    const workspaceRoot = await resolvePath(join(PROJECT_ROOT, 'workspace'));

    if (!resolved.startsWith(workspaceRoot)) {
      return res.status(403).json({ success: false, error: 'Access denied' });
    }

    const ext = extname(filePath).toLowerCase();
    const mimeTypes = {
      '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
      '.gif': 'image/gif', '.svg': 'image/svg+xml', '.webp': 'image/webp',
      '.json': 'application/json', '.csv': 'text/csv', '.html': 'text/html',
    };
    const contentType = mimeTypes[ext] || 'application/octet-stream';

    res.setHeader('Content-Type', contentType);
    res.setHeader('Cache-Control', 'public, max-age=3600');

    const { readFile } = await import('fs/promises');
    const content = await readFile(filePath);
    res.send(content);
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

async function listDataDir(dir) {
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
    } catch {}
  }
  return result.sort((a, b) => {
    if (a.type !== b.type) return a.type === 'folder' ? -1 : 1;
    return a.name.localeCompare(b.name);
  });
}

async function listDirRecursive(dir, base, prefix = '') {
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

export default router;
