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
import resultsRoutes from './routes/results.routes.mjs';
import lineMemoryRoutes from './routes/line-memory.routes.mjs';
import knowledgePublicationRoutes from './routes/knowledge-publication.routes.mjs';
import knowledgeRoutes from './routes/knowledge.routes.mjs';
import productionLineRoutes from './routes/production-line.routes.mjs';
import { authGuard } from './middleware/auth.middleware.mjs';
import { closeAllEngines } from './services/diagnosis.service.mjs';
import { initWebSocket, closeWebSocket, getWSS } from './transport/ws-server.mjs';
import { buildCorsOptions, resolveAllowedOrigins } from './transport/cors.mjs';
import {
  setShuttingDown, registerShutdownHook, runShutdownHooks, shutdownGuardMiddleware,
  isShuttingDown, getShutdownReason,
} from './lifecycle.mjs';
import { getActiveRuns as getActiveEngineRuns } from './engine/diagnosis-engine.mjs';
import { initDB, stmts, db } from './db/database.mjs';
import { listHarnesses, getHarness } from './harness/registry.mjs';
import { existsSync, statfsSync } from 'fs';
import { server as serverConfig, config as appConfig, PROJECT_ROOT } from '../../../config/loader.mjs';
import logger from './utils/logger.mjs';

const SHUTDOWN_TIMEOUT_MS = 10_000;

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

  // Results library backfill (2026-10-25): materialize analysis_results rows
  // for completed runs that predate the library. Insert-only and idempotent —
  // existing rows (and their user description/tags) are never rewritten.
  const { backfillResults } = await import('./services/results-library.service.mjs');
  try {
    const backfill = backfillResults();
    logger.info(
      `Results library backfill: ${backfill.inserted} inserted, ${backfill.skipped} present, ${backfill.failed} failed`,
      { context: 'Init' },
    );
  } catch (err) {
    logger.warn(`Results backfill failed: ${err.message}`, { context: 'Init' });
  }

  logger.info('Initialization complete.', { context: 'Init' });
}

const PORT = process.env.PORT || serverConfig.port;

const app = express();

// ─── TRUST_PROXY：反代后的真实客户端 IP ─────────────────────────────────────
// 生产拓扑（docker-compose）中 backend 位于 nginx 之后：不信任代理时 req.ip
// 是 nginx 的地址，per-IP 控制（登录限流 / 审计）会把所有真实客户端并成同一个
// 桶（rateLimit.mjs 的默认 key 就是 req.ip）。未设置 → false（直连语义不变，
// 也绝不盲目信任 X-Forwarded-For）；`TRUST_PROXY=1` → 信任 1 跳（本仓库 nginx
// 拓扑，docker-compose.yml 已为该服务设好）；`0/false/no/off` → false；其他
// 数值按跳数解析，非数字则原样交给 Express（其接受 'loopback'、CIDR 列表等表
// 达式）。注意：信任代理会让客户端可伪造该跳的 X-Forwarded-For —— 只有在前面
// 确实有自己控制的代理时才开启。
function resolveTrustProxy(raw) {
  if (raw === undefined || raw === null) return false;
  const value = String(raw).trim();
  if (value === '' || /^(false|no|off)$/i.test(value)) return false;
  const hops = Number(value);
  if (Number.isFinite(hops) && hops >= 0) return hops === 0 ? false : Math.floor(hops);
  return value; // 'loopback' / '10.0.0.0/8,172.16.0.0/12' / … — Express expression
}
app.set('trust proxy', resolveTrustProxy(process.env.TRUST_PROXY));

// ─── CORS：显式白名单（CORS_ORIGINS env > config.server.cors_origins）───
// 旧行为 app.use(cors()) 对任意来源回 Access-Control-Allow-Origin: *；现在只有
// 白名单来源获得 CORS 头，无 Origin 的请求（curl/探测/同源）不受影响。
const corsOrigins = resolveAllowedOrigins({ env: process.env, config: appConfig });
app.use(cors(buildCorsOptions({ env: process.env, config: appConfig })));
logger.info(`CORS allowlist: ${corsOrigins.length ? corsOrigins.join(', ') : '(none — only origin-less requests)'}`, { context: 'CORS' });

// ─── 健康探针：存活（liveness）+ 就绪（readiness）───────────────────────────
// 两个端点都注册在「停机守卫」与「鉴权守卫」之前，原因：
//   · 探针（Docker HEALTHCHECK / compose / nginx / k8s）不带凭据，而
//     auth.middleware.mjs 的白名单只列了 /health —— 前置注册让就绪探针保持公开，
//     无需改动该文件；
//   · 停机守卫的 /api/health 豁免（lifecycle.mjs）继续作为冗余防线，而这里自
//     处理的停机语义更精确：存活探针继续 200（进程还在），就绪探针显式 503
//     {status:"unavailable", reasons:["shutting_down"]}。
// 存活端点的响应结构与拆分前完全一致（兼容既有探针/脚本）。

// 专项分析（稳定性/快筛/经验/寻优）已全部改为 harness 真实执行：前端经
// POST /api/diagnosis/start { analysisIntent } 拉起对应 skill 的智能体运行。
// 旧的固定脚本 HTTP 集成（/api/sentinel 等）已整体退役。

// GET /api/health — liveness：进程存活 + DB 可达 + 活跃运行数 + 内存
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

// ── Readiness 内部实现 ──────────────────────────────────────────────────────
const READINESS_DATA_DIR = join(PROJECT_ROOT, appConfig.data?.dir || 'data');
const ENGINE_TIMED_OUT = Symbol('engine-probe-timeout');

/** health.min_free_mb（默认 500MB）→ bytes；env 覆盖走 config/loader.mjs。 */
function minFreeBytes() {
  const configured = Number(appConfig.health?.min_free_mb);
  const mb = Number.isFinite(configured) && configured >= 0 ? configured : 500;
  return mb * 1024 * 1024;
}

/** health.engine_probe_timeout_ms（默认 2500ms）——就绪请求等待引擎探测的上限。 */
function engineProbeTimeoutMs() {
  const configured = Number(appConfig.health?.engine_probe_timeout_ms);
  return Number.isFinite(configured) && configured > 0 ? configured : 2500;
}

/** 数据目录可用空间（statfs 不可用时如实跳过，绝不猜测）。 */
function diskCheck() {
  if (typeof statfsSync !== 'function') {
    return { status: 'skipped', note: 'statfs unavailable on this node build' };
  }
  try {
    const stats = statfsSync(READINESS_DATA_DIR);
    const freeBytes = Number(stats?.bavail) * Number(stats?.bsize);
    if (!Number.isFinite(freeBytes)) {
      return { status: 'skipped', note: 'statfs returned no usable numbers' };
    }
    const thresholdBytes = minFreeBytes();
    const check = {
      status: freeBytes < thresholdBytes ? 'warn' : 'ok',
      free_mb: Math.round(freeBytes / 1024 / 1024),
      threshold_mb: Math.round(thresholdBytes / 1024 / 1024),
    };
    return check;
  } catch (err) {
    // No path/message leak: the readiness endpoint is public.
    return { status: 'skipped', note: `statfs failed (${err?.code || 'unknown error'})` };
  }
}

// 引擎可用性：复用 /api/harness/* 的既有探测（harness.health() →
// engine/cli-common 的二进制解析 + `--version` 探测缓存），不新增探测实现。
// 整轮扫描按 harness.health_cache_ms（默认 30s）缓存 —— OMP 的 health() 每次
// 都会真正 spawn 一次 `omp --version`，绝不能每个就绪请求都做一遍；超出
// health.engine_probe_timeout_ms 的扫描先返回 "unknown"，随后在后台填缓存。
let engineSummaryCache = { at: 0, value: null };
let engineSummaryInFlight = null;

function engineSummaryTtlMs() {
  const configured = Number(appConfig.harness?.health_cache_ms);
  return Number.isFinite(configured) && configured >= 0 ? configured : 30_000;
}

async function probeEngines() {
  const manifests = listHarnesses();
  const results = await Promise.all(manifests.map(async (m) => {
    try {
      const health = await getHarness(m.id).health();
      return { id: m.id, available: health?.available === true };
    } catch {
      return { id: m.id, available: false };
    }
  }));
  const available = results.filter((r) => r.available).map((r) => r.id);
  return {
    status: available.length > 0 ? 'ok' : 'warn',
    available: available.length,
    total: results.length,
    engines: available,
  };
}

async function engineCheck() {
  const cached = engineSummaryCache.value;
  if (cached && Date.now() - engineSummaryCache.at < engineSummaryTtlMs()) return cached;

  if (!engineSummaryInFlight) {
    engineSummaryInFlight = probeEngines()
      .then((summary) => {
        engineSummaryCache = { at: Date.now(), value: summary };
        return summary;
      })
      .catch(() => ({ status: 'skipped', note: 'engine probe failed' }))
      .finally(() => { engineSummaryInFlight = null; });
  }

  let timer;
  const timeout = new Promise((resolve) => {
    timer = setTimeout(() => resolve(ENGINE_TIMED_OUT), engineProbeTimeoutMs());
    timer.unref?.();
  });
  const result = await Promise.race([engineSummaryInFlight, timeout]);
  clearTimeout(timer);
  if (result === ENGINE_TIMED_OUT) return { status: 'unknown', note: 'engine probe still running' };
  return result;
}

// GET /api/health/ready — readiness：DB（关键依赖）+ 磁盘/引擎（告警项）
//   · 关键依赖故障（DB 不可用 / 正在停机）→ 503 {status:"unavailable"}
//   · 告警（数据目录剩余空间不足 / 无可用引擎）→ 200 {status:"degraded", reasons:[...]}
app.get('/api/health/ready', async (req, res) => {
  try {
    const reasons = [];
    const checks = {
      status: 'ok',
      timestamp: new Date().toISOString(),
      uptime: process.uptime(),
      checks: {},
      reasons,
    };

    // (0) 停机中：不再接受新工作，进程退出前持续 503
    if (isShuttingDown()) {
      reasons.push('shutting_down');
      checks.checks.shutdown = { status: 'error', reason: getShutdownReason() || 'unknown' };
    }

    // (1) DB — 关键依赖
    try {
      db.prepare('SELECT 1 AS ok').get();
      checks.checks.database = { status: 'ok' };
    } catch (err) {
      checks.checks.database = { status: 'error', message: err.message };
      reasons.push('database_unavailable');
    }

    // (2) 数据目录磁盘空间 — 仅告警
    const disk = diskCheck();
    checks.checks.disk = disk;
    if (disk.status === 'warn') reasons.push('low_disk');

    // (3) 引擎可用性（缓存探测）— 仅告警
    const engines = await engineCheck();
    checks.checks.engines = engines;
    if (engines.status === 'warn') reasons.push('no_engines_available');

    const degraded = reasons.length > 0;
    const critical = reasons.includes('shutting_down') || reasons.includes('database_unavailable');
    checks.status = critical ? 'unavailable' : (degraded ? 'degraded' : 'ok');
    res.status(critical ? 503 : 200).json(checks);
  } catch (err) {
    // 就绪探针绝不允许未捕获异常（express 4 不接管 async 错误，否则会触发
    // unhandledRejection → 停机）。失败即"未就绪"，但不泄漏内部细节。
    logger.warn(`Readiness check failed: ${err?.message || err}`, { context: 'Health', stack: err?.stack });
    if (!res.headersSent) {
      res.status(503).json({
        status: 'unavailable',
        timestamp: new Date().toISOString(),
        uptime: process.uptime(),
        checks: {},
        reasons: ['check_failed'],
      });
    }
  }
});

// ─── 优雅停机守卫 ───
// 停机期间新到的 /api 请求立即 503；健康探针在上面已自行处理停机语义
// （存活 200 / 就绪 503），lifecycle 的 /api/health 豁免仍是冗余防线。
app.use(shutdownGuardMiddleware());

app.use(express.json({ limit: serverConfig.body_limit }));

// ─── Auth: 全局 API 鉴权拦截 ───
// 白名单（在 authGuard 内）：POST /api/auth/register、POST /api/auth/login、GET /api/health。
// 健康探针（GET /api/health、GET /api/health/ready）已在其上方挂载，因此探针
// 不经过鉴权守卫，也无需扩展 auth.middleware.mjs 的白名单。
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
app.use('/api/results', resultsRoutes);
app.use('/api/analysis', analysisRoutes);
app.use('/api/chat', chatRoutes);
app.use('/api/omp', ompRoutes);
app.use('/api/harness', harnessRoutes);
app.use('/api/ontology', ontologyRoutes);
app.use('/api/line-memory', lineMemoryRoutes);
app.use('/api', knowledgePublicationRoutes);
app.use('/api/lines', productionLineRoutes);
app.use('/api/knowledge', knowledgeRoutes);

// 专项分析（稳定性/快筛/经验/寻优）已全部改为 harness 真实执行：前端经
// POST /api/diagnosis/start { analysisIntent } 拉起对应 skill 的智能体运行。
// 旧的固定脚本 HTTP 集成（/api/sentinel 等）已整体退役。

// 健康探针（GET /api/health 存活 / GET /api/health/ready 就绪）在文件上方、
// 两个守卫之前注册 —— 必须保持在该位置，探针不带凭据。

// Serve Vue frontend in production
const frontendDist = join(PROJECT_ROOT, 'app', 'frontend', 'dist');
app.use(express.static(frontendDist));
app.get('*', (req, res) => {
  if (req.path.startsWith('/api/') || req.path.startsWith('/ws')) {
    return res.status(404).json({ success: false, error: 'Not found' });
  }
  res.sendFile(join(frontendDist, 'index.html'));
});

// ─── 全局错误中间件（必须在所有路由之后）───
// 未处理异常统一记日志（含 stack）并返回固定 JSON；err.message 绝不下发到
// 客户端（内部实现细节 / SQL / 路径）。4xx（如 body-parser 的非法 JSON）
// 保留原状态码，同样不泄漏 message。
app.use((err, req, res, next) => {
  logger.error(`Unhandled error on ${req.method} ${req.originalUrl}: ${err?.message || err}`, {
    context: 'ErrorHandler',
    stack: err?.stack,
    code: err?.code,
    status: err?.status || err?.statusCode,
  });
  if (res.headersSent) return next(err);
  const status = Number(err?.status || err?.statusCode);
  if (Number.isInteger(status) && status >= 400 && status < 500) {
    return res.status(status).json({ success: false, error: 'Bad request', code: 'BAD_REQUEST' });
  }
  return res.status(500).json({ success: false, error: 'Internal server error', code: 'INTERNAL' });
});

// Create HTTP server (shared by Express + WebSocket)
const server = createServer(app);

// Initialize WebSocket server on /ws
initWebSocket(server);

// ─── 进程级故障与优雅停机（P0-4）─────────────────────────────────────────────
let shutdownInProgress = false;

// (c) WAL flush: 注册为停机钩子，保证在退出前把 -wal 内容并回主库。
registerShutdownHook(() => {
  db.pragma('wal_checkpoint(TRUNCATE)');
  logger.info('SQLite WAL checkpointed', { context: 'Shutdown' });
});

/** (a) 通知所有活跃引擎进程结束（closeAllEngines 逐引擎 no-op 安全）。 */
function notifyLiveEngines() {
  const runIds = new Set();
  try { for (const runId of getActiveEngineRuns()) runIds.add(runId); } catch { /* engine never started */ }
  try { for (const row of stmts.getActiveRuns.all()) runIds.add(row.run_id); } catch { /* db unavailable */ }
  for (const runId of runIds) {
    try {
      closeAllEngines(runId);
      logger.info(`Closed engine for run ${runId}`, { context: 'Shutdown' });
    } catch (err) {
      logger.warn(`closeAllEngines(${runId}) failed: ${err?.message || err}`, { context: 'Shutdown' });
    }
  }
}

/** (b) 停止接受连接并等待在途请求结束（有界，超时后强制关闭）。 */
function closeHttpServer(httpServer, timeoutMs = SHUTDOWN_TIMEOUT_MS) {
  return new Promise((resolve) => {
    let settled = false;
    const finish = () => { if (!settled) { settled = true; clearTimeout(timer); resolve(); } };
    const timer = setTimeout(() => {
      logger.warn(`HTTP server still busy after ${timeoutMs}ms — forcing remaining connections`, { context: 'Shutdown' });
      try { httpServer.closeAllConnections?.(); } catch { /* older node */ }
      finish();
    }, timeoutMs);
    timer.unref?.();
    try {
      httpServer.close(finish);
      httpServer.closeIdleConnections?.(); // keep-alive sockets must not hold the drain
    } catch (err) {
      logger.warn(`HTTP server close failed: ${err.message}`, { context: 'Shutdown' });
      finish();
    }
  });
}

function closeWebSocketClients() {
  const wss = getWSS();
  if (!wss) return;
  for (const client of wss.clients) {
    try { client.close(1001, 'Server shutting down'); } catch { /* already closing */ }
  }
}

async function gracefulShutdown(reason, exitCode = 0) {
  if (shutdownInProgress) return;
  shutdownInProgress = true;
  setShuttingDown(reason);
  logger.warn(`Graceful shutdown starting (${reason})`, { context: 'Shutdown' });

  // Stop active session chats first: each owns a live engine child whose
  // session file must be released before the process exits (orphaned omp
  // children hold cross-process session locks and break the next resume).
  try {
    const { listActiveChats, stopChat } = await import('./services/chat.service.mjs');
    for (const chat of listActiveChats()) {
      if (chat.status === 'active') {
        try { stopChat(chat.chatId); } catch { /* best effort */ }
      }
    }
  } catch (err) {
    logger.warn(`Active chat shutdown incomplete: ${err.message}`, { context: 'Shutdown' });
  }

  notifyLiveEngines();          // (a) live engine processes
  closeWebSocketClients();
  await closeHttpServer(server); // (b) drain HTTP

  const hookErrors = await runShutdownHooks({ // (c) WAL checkpoint + registered cleanup
    onError: (err) => logger.error(`Shutdown hook failed: ${err?.message || err}`, { context: 'Shutdown', stack: err?.stack }),
  });
  if (hookErrors.length) logger.warn(`${hookErrors.length} shutdown hook(s) failed`, { context: 'Shutdown' });

  logger.info('Shutdown complete', { context: 'Shutdown' });
  process.exit(exitCode);       // (d)
}

function installProcessHandlers() {
  // 未捕获异常 / 未处理 Promise：记录完整堆栈后优雅停机并以 1 退出；10s 兜底
  // 保证绝不停在停机流程里（failsafe 自身 unref，不影响正常退出时序）。
  process.on('uncaughtException', (err) => {
    logger.error(`Uncaught exception: ${err?.stack || err?.message || err}`, { context: 'Fatal', stack: err?.stack });
    setTimeout(() => process.exit(1), SHUTDOWN_TIMEOUT_MS).unref();
    gracefulShutdown('uncaughtException', 1);
  });

  process.on('unhandledRejection', (reason) => {
    const err = reason instanceof Error ? reason : new Error(String(reason));
    logger.error(`Unhandled rejection: ${err.stack}`, { context: 'Fatal', stack: err.stack });
    setTimeout(() => process.exit(1), SHUTDOWN_TIMEOUT_MS).unref();
    gracefulShutdown('unhandledRejection', 1);
  });

  for (const signal of ['SIGTERM', 'SIGINT', 'SIGBREAK']) {
    process.on(signal, () => {
      if (shutdownInProgress) {
        logger.warn(`Second ${signal} — exiting immediately`, { context: 'Shutdown' });
        process.exit(1);
      }
      logger.info(`${signal} received`, { context: 'Shutdown' });
      gracefulShutdown(signal, 0);
    });
  }
}

installProcessHandlers();

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
// Engine children, active chats, the WS server and the WAL checkpoint are all
// handled by installProcessHandlers() → gracefulShutdown() above (single
// implementation — a merge briefly carried a second legacy shutdown here, and
// two concurrent handlers on one signal could exit before the hooks ran).

// Periodic event-log retention (startup applies it too): long claude runs can
// emit >100k events; the UI only renders the newest window.
setInterval(() => {
  import('./services/retention.service.mjs')
    .then(({ applyEventStreamRetention }) => applyEventStreamRetention())
    .catch((err) => logger.warn(`Event retention tick failed: ${err.message}`, { context: 'Retention' }));
}, 6 * 60 * 60 * 1000).unref?.();

export default app;
