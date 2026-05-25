import { createServer } from 'http';
import express from 'express';
import cors from 'cors';
import { join } from 'path';
import fileRoutes from './routes/files.routes.mjs';
import diagnosisRoutes from './routes/diagnosis.routes.mjs';
import historyRoutes from './routes/history.routes.mjs';
import { initWebSocket } from './transport/ws-server.mjs';
import { initDB, stmts } from './db/database.mjs';
import { existsSync } from 'fs';
import { server as serverConfig, PROJECT_ROOT } from '../../../config/loader.mjs';

async function initialize() {
  console.log('[Init] Checking project configuration...');

  // Verify default.yaml exists
  const defaultYamlPath = join(PROJECT_ROOT, 'config', 'default.yaml');
  if (!existsSync(defaultYamlPath)) {
    console.error('[Init] FATAL: config/default.yaml not found');
    console.error('[Init] Run: ind-diag init');
    process.exit(1);
  }
  console.log('[Init] Config loaded successfully');

  // Init database (idempotent)
  initDB();

  // Mark stale runs as interrupted
  const staleRuns = stmts.getActiveRuns.all();
  if (staleRuns.length > 0) {
    for (const run of staleRuns) {
      stmts.failRun.run({ runId: run.run_id, error: 'Server restarted — diagnosis interrupted' });
      console.log(`[Init] Marked stale run as interrupted: ${run.run_id}`);
    }
  }

  console.log('[Init] Initialization complete.');
}

const PORT = process.env.PORT || serverConfig.port;

const app = express();

app.use(cors());
app.use(express.json({ limit: serverConfig.body_limit }));

// Serve uploaded data files statically (for preview/download)
app.use('/data-files', express.static(join(PROJECT_ROOT, 'data')));
app.use('/workspace-files', express.static(join(PROJECT_ROOT, 'workspace')));

// API routes
app.use('/api/files', fileRoutes);
app.use('/api/diagnosis', diagnosisRoutes);
app.use('/api/history', historyRoutes);

// Health check
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// Serve Vue frontend in production
const frontendDist = join(PROJECT_ROOT, 'app', 'frontend', 'dist');
app.use(express.static(frontendDist));
app.get('*', (req, res) => {
  if (!req.path.startsWith('/api/') && !req.path.startsWith('/ws')) {
    res.sendFile(join(frontendDist, 'index.html'));
  }
});

// Create HTTP server (shared by Express + WebSocket)
const server = createServer(app);

// Initialize WebSocket server on /ws
initWebSocket(server);

initialize().then(() => {
  server.listen(PORT, () => {
    console.log(`[Industrial Diagnostic API] HTTP + WebSocket server on http://localhost:${PORT}`);
    console.log(`[Industrial Diagnostic API] WebSocket endpoint: ws://localhost:${PORT}/ws`);
    console.log(`[Industrial Diagnostic API] Project root: ${PROJECT_ROOT}`);
    console.log(`[Industrial Diagnostic API] Data dir: ${join(PROJECT_ROOT, 'data')}`);
  });
}).catch(err => {
  console.error('[Init] Failed to start:', err.message);
  process.exit(1);
});

export default app;
