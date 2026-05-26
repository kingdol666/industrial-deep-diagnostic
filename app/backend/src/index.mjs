import { createServer } from 'http';
import express from 'express';
import cors from 'cors';
import { join } from 'path';
import fileRoutes from './routes/files.routes.mjs';
import diagnosisRoutes from './routes/diagnosis.routes.mjs';
import historyRoutes from './routes/history.routes.mjs';
import analysisRoutes from './routes/analysis.routes.mjs';
import { initWebSocket } from './transport/ws-server.mjs';
import { initDB, stmts, db } from './db/database.mjs';
import { existsSync } from 'fs';
import { server as serverConfig, PROJECT_ROOT } from '../../../config/loader.mjs';
import logger from './utils/logger.mjs';

async function initialize() {
  logger.info('Checking project configuration...', { context: 'Init' });

  // Verify default.yaml exists
  const defaultYamlPath = join(PROJECT_ROOT, 'config', 'default.yaml');
  if (!existsSync(defaultYamlPath)) {
    logger.error('FATAL: config/default.yaml not found', { context: 'Init' });
    logger.error('Run: ind-diag init', { context: 'Init' });
    process.exit(1);
  }
  logger.info('Config loaded successfully', { context: 'Init' });

  // Init database (idempotent)
  initDB();

  // Mark stale runs as interrupted
  const staleRuns = stmts.getActiveRuns.all();
  if (staleRuns.length > 0) {
    for (const run of staleRuns) {
      stmts.failRun.run({ runId: run.run_id, error: 'Server restarted — diagnosis interrupted' });
      logger.info(`Marked stale run as interrupted: ${run.run_id}`, { context: 'Init', runId: run.run_id });
    }
  }

  logger.info('Initialization complete.', { context: 'Init' });
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
app.use('/api/analysis', analysisRoutes);

// Health check with DB status, active runs, and metrics
app.get('/api/health', (req, res) => {
  const checks = {
    status: 'ok',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    memory: {
      rss: Math.round(process.memoryUsage().rss / 1024 / 1024) + 'MB',
      heapUsed: Math.round(process.memoryUsage().heapUsed / 1024 / 1024) + 'MB',
      heapTotal: Math.round(process.memoryUsage().heapTotal / 1024 / 1024) + 'MB',
    },
    checks: {},
  };

  // Database check
  try {
    db.prepare('SELECT 1 AS ok').get();
    checks.checks.database = { status: 'ok' };
  } catch (err) {
    checks.checks.database = { status: 'error', message: err.message };
    checks.status = 'degraded';
  }

  // Active runs count
  try {
    const count = stmts.getActiveRuns.all().length;
    checks.checks.activeRuns = count;
  } catch {}

  const httpCode = checks.status === 'ok' ? 200 : 503;
  res.status(httpCode).json(checks);
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
    logger.info(`HTTP + WebSocket server on http://localhost:${PORT}`, { context: 'Server' });
    logger.info(`WebSocket endpoint: ws://localhost:${PORT}/ws`, { context: 'Server' });
    logger.info(`Project root: ${PROJECT_ROOT}`, { context: 'Server' });
    logger.info(`Data dir: ${join(PROJECT_ROOT, 'data')}`, { context: 'Server' });
  });
}).catch(err => {
  logger.error(`Failed to start: ${err.message}`, { context: 'Init' });
  process.exit(1);
});

export default app;
