import { createServer } from 'http';
import express from 'express';
import cors from 'cors';
import { join } from 'path';
import fileRoutes from './routes/files.routes.mjs';
import diagnosisRoutes from './routes/diagnosis.routes.mjs';
import historyRoutes from './routes/history.routes.mjs';
import analysisRoutes from './routes/analysis.routes.mjs';
import chatRoutes from './routes/chat.routes.mjs';
import ompRoutes from './routes/omp.routes.mjs';
import ontologyRoutes from './routes/ontology.routes.mjs';
import harnessRoutes from './routes/harness.routes.mjs';
import authRoutes from './routes/auth.routes.mjs';
import externalRoutes from './routes/external.routes.mjs';
import { authGuard } from './middleware/auth.middleware.mjs';
import { initWebSocket, closeWebSocket } from './transport/ws-server.mjs';
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

  // Restart recovery (plan v2 Phase B0):
  //   1. runs that were only ever `pending` never executed → stopped (resumable);
  //   2. runs that were executing when the process died → failed (interrupted);
  //   3. session ids lost in flight are reconciled from the persisted event
  //      stream / omp session dir so the run stays continuable.
  const { recoverInterruptedRuns, reconcileSessionIds } = await import('./services/session-integrity.service.mjs');
  const stopped = recoverInterruptedRuns();
  if (stopped.stopped.length) {
    logger.info(`Pending runs marked stopped: ${stopped.stopped.join(', ')}`, { context: 'Init' });
  }

  // Mark stale runs as interrupted
  const staleRuns = stmts.getActiveRuns.all();
  if (staleRuns.length > 0) {
    for (const run of staleRuns) {
      stmts.failRun.run({ runId: run.run_id, error: 'Server restarted — diagnosis interrupted' });
      logger.info(`Marked stale run as interrupted: ${run.run_id}`, { context: 'Init', runId: run.run_id });
    }
  }

  const reconcile = reconcileSessionIds();
  if (reconcile.recovered.length) {
    logger.info(
      `Reconciled ${reconcile.recovered.length} session id(s): `
      + reconcile.recovered.map((r) => `${r.run_id}<-${r.source}`).join(', '),
      { context: 'Init' },
    );
  }

  // Retention (plan v2 D5): purge expired soft-deleted runs and expire old
  // workspaces / orphan directories. Never touches live runs.
  const { applyRetentionPolicies } = await import('./services/retention.service.mjs');
  applyRetentionPolicies();

  logger.info('Initialization complete.', { context: 'Init' });
}

const PORT = process.env.PORT || serverConfig.port;

const app = express();

app.use(cors());
app.use(express.json({ limit: serverConfig.body_limit }));

// ─── Auth: 全局 API 鉴权拦截 ───
// 白名单（在 authGuard 内）：POST /api/auth/register、POST /api/auth/login、GET /api/health
// 其余所有 /api/* 均要求 Authorization: Bearer <token>（登录会话或 API Token）。
// 可用 env AUTH_ENABLED=0 临时关闭（仅限本机调试）。
if (process.env.AUTH_ENABLED !== '0') {
  app.use('/api', authGuard);
} else {
  logger.warn('AUTH_ENABLED=0 — API 鉴权已临时关闭（仅限本机调试）', { context: 'Auth' });
}

// Auth routes（register/login 为公开端点；/me 与 /tokens 需认证）
app.use('/api/auth', authRoutes);

// External integration surface (stable v1 namespace for outside applications)
app.use('/api/external', externalRoutes);

// API routes
app.use('/api/files', fileRoutes);
app.use('/api/diagnosis', diagnosisRoutes);
app.use('/api/history', historyRoutes);
app.use('/api/analysis', analysisRoutes);
app.use('/api/chat', chatRoutes);
app.use('/api/omp', ompRoutes);
app.use('/api/harness', harnessRoutes);
app.use('/api/ontology', ontologyRoutes);

// 专项分析（稳定性/快筛/经验/寻优）已全部改为 harness 真实执行：前端经
// POST /api/diagnosis/start { analysisIntent } 拉起对应 skill 的智能体运行。
// 旧的固定脚本 HTTP 集成（/api/sentinel 等）已整体退役。

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
  if (req.path.startsWith('/api/') || req.path.startsWith('/ws')) {
    return res.status(404).json({ success: false, error: 'Not found' });
  }
  res.sendFile(join(frontendDist, 'index.html'));
});

// Create HTTP server (shared by Express + WebSocket)
const server = createServer(app);

// Initialize WebSocket server on /ws
initWebSocket(server);

initialize().then(() => {
  // Handle port conflict gracefully (EADDRINUSE) instead of crashing
  server.once('error', (err) => {
    if (err.code === 'EADDRINUSE') {
      logger.error(`Port ${PORT} is already in use. Is another instance running?`, { context: 'Server' });
      logger.error(`Stop the existing process or use a different port via SERVER_PORT env.`, { context: 'Server' });
      process.exit(1);
    }
    logger.error(`Server error: ${err.message}`, { context: 'Server' });
    process.exit(1);
  });
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

// ─── Graceful shutdown ───────────────────────────────────────────────────
// Killing the backend used to leave engine children (omp/claude) alive; they
// keep their session files locked, so the next process's resume hits
// "session open for writing in another omp process" and stalls. Close every
// engine child and the WS server before exiting.
let shuttingDown = false;
async function shutdown(signal) {
  if (shuttingDown) return;
  shuttingDown = true;
  logger.info(`Received ${signal} — shutting down (closing engine children)`, { context: 'Server' });
  try {
    const { shutdownAllEngines } = await import('./services/diagnosis.service.mjs');
    const { listActiveChats, stopChat } = await import('./services/chat.service.mjs');
    for (const chat of listActiveChats()) {
      if (chat.status === 'active') {
        try { stopChat(chat.chatId); } catch { /* best effort */ }
      }
    }
    const closed = shutdownAllEngines();
    logger.info(`Closed engine state for ${closed} run(s)`, { context: 'Server' });
  } catch (err) {
    logger.warn(`Engine shutdown incomplete: ${err.message}`, { context: 'Server' });
  }
  try { closeWebSocket(); } catch { /* best effort */ }
  server.close(() => {
    logger.info('HTTP server closed', { context: 'Server' });
    process.exit(0);
  });
  // A stuck keep-alive connection must not block shutdown forever.
  setTimeout(() => process.exit(0), 5000).unref?.();
}
process.on('SIGINT', () => { void shutdown('SIGINT'); });
process.on('SIGTERM', () => { void shutdown('SIGTERM'); });
process.on('SIGBREAK', () => { void shutdown('SIGBREAK'); }); // Windows Ctrl+Break

// Periodic event-log retention (startup applies it too): long claude runs can
// emit >100k events; the UI only renders the newest window.
setInterval(() => {
  import('./services/retention.service.mjs')
    .then(({ applyEventStreamRetention }) => applyEventStreamRetention())
    .catch((err) => logger.warn(`Event retention tick failed: ${err.message}`, { context: 'Retention' }));
}, 6 * 60 * 60 * 1000).unref?.();

export default app;
