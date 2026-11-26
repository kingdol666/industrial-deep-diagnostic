// Diagnosis Routes — Thin HTTP handlers, delegates business logic to diagnosis service
//
// Tenancy (P0-6): every run-scoped endpoint passes `req.user` as the viewer.
// A run the caller may not see is answered exactly like a missing one (404) —
// the services return null/false for that case, so no error path can leak the
// existence of another user's run.

import { Router } from 'express';
import {
  validateDataPath, createDiagnosisRun, listRuns, getRunStatus,
  stopDiagnosis, sendChatMessage, continueDiagnosis, answerQuestion,
  triggerDiagnosis, startStream, subscribeSSE,
  getSessionContent, getRunRealtimeSnapshot, triggerEnhancement,
  assertRunHarnessUsable, getDiagTaskView,
} from '../services/diagnosis.service.mjs';
import { sessionMap } from '../services/session-integrity.service.mjs';
import { getRunReviewContext } from '../services/line-memory.service.mjs';
import { stmts } from '../db/database.mjs';
import { userRateLimit } from '../services/tenancy.mjs';
import { config } from '../../../../config/loader.mjs';
import logger from '../utils/logger.mjs';

const router = Router();

// 诊断启动/执行限流（P0-6）：config.security.start_rate_limit（默认 10 次/分钟/用户）。
// 与 /start 共享同一预算的是 /execute 与 /tasks —— 三者都创建一个真实运行，
// 只限其中一个等于没限。AUTH_ENABLED=0 下自动让行（见 tenancy.userRateLimit）。
const startLimitCfg = config.security?.start_rate_limit || {};
const startRateLimit = userRateLimit({
  windowMs: Number(startLimitCfg.window_ms ?? startLimitCfg.windowMs ?? 60_000),
  max: Number(startLimitCfg.max ?? 10),
});

/**
 * Uniform error shape. 4xx keep their user-facing message + code (validation,
 * DATA_NOT_FOUND, PATH_TRAVERSAL, …). 5xx answer a GENERIC message with a
 * stable code and log the real error server-side — an internal stack/message
 * must not reach the client (B4 leak class).
 */
function sendError(res, err, { fallbackCode = 'DIAGNOSIS_INTERNAL_ERROR', status: fallbackStatus = 500 } = {}) {
  const status = err?.status || fallbackStatus;
  if (status >= 500) {
    logger.error(`[diagnosis] ${err?.stack || err?.message || err}`, { context: 'Diagnosis' });
    return res.status(status).json({
      success: false,
      code: err?.code || fallbackCode,
      error: '诊断服务内部错误，请查看后端日志后重试',
    });
  }
  return res.status(status).json({
    success: false,
    ...(err?.code ? { code: err.code } : {}),
    error: err?.message || '请求无效',
  });
}

router.get('/review-context/:runId', (req, res) => {
  try {
    res.json({ success: true, data: getRunReviewContext(req.params.runId, req.user) });
  } catch (err) {
    sendError(res, err);
  }
});

// Start a new diagnosis
router.post('/start', startRateLimit, async (req, res) => {
  try {
    const { dataPath, folderPath, dataPaths, sceneName, harness } = req.body;

    // 执行前强校验 — unknown → 400 / not installed → 409, before any run state exists
    await assertRunHarnessUsable(harness);

    // Validate all data paths before creating the run
    if (dataPaths && Array.isArray(dataPaths) && dataPaths.length > 0) {
      for (const dp of dataPaths) {
        await validateDataPath(dp);
      }
    } else if (folderPath) {
      await validateDataPath(folderPath);
    } else if (dataPath) {
      await validateDataPath(dataPath);
    }

    // Both ownership columns: user_id drives the run-management filters
    // (listRunsForUser/requireRun), owner_user_id drives tenancy (canView).
    const result = createDiagnosisRun({ ...req.body, executeImmediately: false, userId: req.user?.id ?? null, ownerUserId: req.user });
    res.json({ success: true, data: result });
  } catch (err) {
    sendError(res, err, { fallbackCode: 'DIAGNOSIS_START_FAILED' });
  }
});

// List all diagnosis runs (own runs; every run for an admin)
router.get('/list', (req, res) => {
  try {
    const runs = listRuns(req.user);
    res.json({ success: true, data: runs });
  } catch (err) {
    sendError(res, err, { fallbackCode: 'DIAGNOSIS_LIST_FAILED' });
  }
});

router.get('/session/:runId', async (req, res) => {
  try {
    const { runId } = req.params;
    const data = await getSessionContent(runId, req.user);
    res.json({ success: true, data });
  } catch (err) {
    sendError(res, err, { fallbackCode: 'DIAGNOSIS_SESSION_FAILED' });
  }
});

// SSE stream endpoint
router.get('/stream/:runId', async (req, res) => {
  const { runId } = req.params;
  const streamInfo = startStream(runId, req.user);

  if (!streamInfo) {
    return res.status(404).json({ success: false, error: 'Run not found' });
  }

  // Already finished — send completion and end
  if (streamInfo.isFinished) {
    const { currentStatus, run } = streamInfo;
    res.writeHead(200, {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      Connection: 'keep-alive',
    });
    res.write(`event: complete\ndata: ${JSON.stringify({
      status: currentStatus, reportPath: run.report_path,
      score: run.score, verdict: run.judge_verdict,
    })}\n\n`);
    res.end();
    return;
  }

  res.writeHead(200, {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    Connection: 'keep-alive',
    'X-Accel-Buffering': 'no',
  });

  const sendSSE = (event, data) => {
    if (res.destroyed) return;
    res.write(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`);
  };

  const unsub = subscribeSSE(runId, (event, data) => {
    if (res.destroyed) return;
    if (event === 'stream_end') {
      if (!res.destroyed) res.end();
    } else {
      sendSSE(event, data);
    }
  });

  req.on('close', () => {
    unsub();
    if (!res.destroyed) res.end();
  });

  // Start diagnosis if still pending (use triggerDiagnosis for guard checks)
  if (streamInfo.currentStatus === 'pending') {
    try {
      triggerDiagnosis(runId, req.user);
    } catch (err) {
      sendSSE('error', { runId, error: err.message });
      res.end();
    }
  }
});

// Stop a running diagnosis
router.post('/stop/:runId', (req, res) => {
  const { runId } = req.params;
  // Ownership first: a foreign (or unknown) run must not reveal whether a
  // process exists for it.
  if (!getRunStatus(runId, req.user)) {
    return res.status(404).json({ success: false, error: 'Run not found' });
  }
  try {
    const result = stopDiagnosis(runId, req.user);
    res.json({ success: true, data: result });
  } catch (err) {
    res.status(err.status || 500).json({
      success: false,
      code: err.code || 'DIAGNOSIS_STOP_ERROR',
      error: err.message,
    });
  }
});

// Trigger execution for an already-created pending run
router.post('/execute/:runId', startRateLimit, async (req, res) => {
  try {
    const result = triggerDiagnosis(req.params.runId, req.user);
    res.json({ success: true, data: result });
  } catch (err) {
    sendError(res, err, { fallbackCode: 'DIAGNOSIS_EXECUTE_FAILED' });
  }
});

// Send a chat message to the running engine process.
// The run's harness is fixed at creation: this endpoint never accepts a harness
// override, because resuming a session on a different engine would look up a
// session id that engine never created (plan v2 B0.4).
router.post('/chat/:runId', async (req, res) => {
  const { runId } = req.params;
  const { message, maxTurns } = req.body;

  if (!message || typeof message !== 'string') {
    return res.status(400).json({ success: false, error: 'message is required' });
  }

  try {
    const sent = await sendChatMessage(runId, message, req.user, { maxTurns });
    if (!sent) {
      // 404 now means exactly one thing: the run does not exist (or is not
      // visible to this caller). A run that exists but cannot resume/rebuild
      // throws 409 with a code.
      return res.status(404).json({
        success: false,
        code: 'RUN_NOT_FOUND',
        error: `Run not found: ${runId}`,
      });
    }
    res.json({
      success: true,
      data: {
        runId,
        mode: sent.mode,
        resumed: sent.mode === 'session',
        reason: sent.reason ?? null,
      },
    });
  } catch (err) {
    const status = err.status || 500;
    res.status(status).json({
      success: false,
      code: err.code || 'CHAT_ERROR',
      error: err.message,
      harness: err.harness ?? null,
      run_id: err.runId ?? runId,
    });
  }
});

// Session mapping audit (plan v2 B0.3): shows which harness session a run is
// bound to, whether it is resumable, and whether a missing id can be reconciled.
// Tenancy-scoped like every sibling — the session binding is run data.
router.get('/session-map/:runId', (req, res) => {
  try {
    const run = getRunStatus(req.params.runId, req.user);
    if (!run) return res.status(404).json({ success: false, error: 'Run not found' });
    res.json({ success: true, data: sessionMap(run) });
  } catch (err) {
    res.status(err.status || 500).json({ success: false, code: err.code || 'DIAGNOSIS_ERROR', error: err.message });
  }
});

// Continue / retry a failed or stopped run
router.post('/continue/:runId', async (req, res) => {
  try {
    const { followUpMessage } = req.body || {};
    const result = continueDiagnosis(req.params.runId, followUpMessage, { viewer: req.user });
    res.json({ success: true, data: result });
  } catch (err) {
    sendError(res, err, { fallbackCode: 'DIAGNOSIS_CONTINUE_FAILED' });
  }
});

// Submit answer to AskUserQuestion
router.post('/answer/:runId', (req, res) => {
  const { runId } = req.params;
  const { questionId, toolUseId, answers } = req.body;

  if (!toolUseId || !answers) {
    return res.status(400).json({ success: false, error: 'toolUseId and answers are required' });
  }

  const answered = answerQuestion(runId, questionId, toolUseId, answers, req.user);
  if (!answered) {
    return res.status(404).json({ success: false, error: 'Process not found or already ended' });
  }

  res.json({ success: true, data: { runId, questionId, answered: true } });
});

// Get run status
router.get('/status/:runId', (req, res) => {
  const run = getRunStatus(req.params.runId, req.user);
  if (!run) return res.status(404).json({ success: false, error: 'Run not found' });
  res.json({ success: true, data: run });
});

// Get run realtime snapshot from DB event stream + current status.
// `?events_limit=N` (100..10000, default 2000) bounds the event payload;
// the response reports events_total / events_truncated.
router.get('/snapshot/:runId', (req, res) => {
  const snapshot = getRunRealtimeSnapshot(req.params.runId, {
    viewer: req.user,
    eventsLimit: req.query.events_limit,
  });
  if (!snapshot) return res.status(404).json({ success: false, error: 'Run not found' });
  res.json({ success: true, data: snapshot });
});

// POST /api/diagnosis/enhance/:runId — one-click deep enhancement (E0-E8) for a completed run
router.post('/enhance/:runId', async (req, res) => {
  try {
    const result = await triggerEnhancement(req.params.runId, req.user);
    res.json({ success: true, data: result });
  } catch (err) {
    sendError(res, err, { fallbackCode: 'DIAGNOSIS_ENHANCE_FAILED' });
  }
});

// ── 异步任务 API(AgentWorkShop diag-bridge 任务管理面)─────────────────
// POST /tasks:接收即返 task_id——诊断放入任务管理(run 记录 + 引擎子进程后台
// 线程执行),调用方绝不阻塞;GET /tasks/:taskId 查询状态,完成后 result 携带
// 诊断总结与报告 md 绝对路径,供外部(如 kb_agent)接续入库。

// Start a diagnosis as a managed async task: acknowledge immediately.
router.post('/tasks', startRateLimit, async (req, res) => {
  try {
    const { dataPath, folderPath, dataPaths, harness } = req.body;
    await assertRunHarnessUsable(harness);
    if (dataPaths && Array.isArray(dataPaths) && dataPaths.length > 0) {
      for (const dp of dataPaths) await validateDataPath(dp);
    } else if (folderPath) {
      await validateDataPath(folderPath);
    } else if (dataPath) {
      await validateDataPath(dataPath);
    }
    const created = createDiagnosisRun({ ...req.body, executeImmediately: true, userId: req.user?.id ?? null, ownerUserId: req.user });
    const taskId = created.runId ?? created.id ?? '';
    if (!taskId) {
      return res.status(500).json({ success: false, code: 'TASK_CREATE_FAILED', error: 'createDiagnosisRun 未返回 runId' });
    }
    // 如实回执：triggerDiagnosis 返回真实准入结果 —— 容量已满时 run 进入
    // 'queued'，ack 必须说 queued（旧实现硬编码 'running'，调用方会以为诊断
    // 已在执行）。拉起异常时同样以 run 行状态为准，不编造。
    let admission;
    try {
      admission = triggerDiagnosis(taskId, req.user);
    } catch (execErr) {
      // 拉起失败:run 已标记 failed,GET /tasks/:id 会如实呈现错误
      console.warn(`[diagnosis] task execute failed: ${execErr.message}`);
      admission = { status: getRunStatus(taskId, req.user)?.status ?? 'failed' };
    }
    res.json({
      success: true,
      data: {
        task_id: taskId,
        status: admission.status ?? 'running',
        poll: 'GET /api/diagnosis/tasks/' + taskId,
      },
    });
  } catch (err) {
    sendError(res, err, { fallbackCode: 'DIAGNOSIS_TASK_FAILED' });
  }
});

// Task view: status + result(诊断总结 + report md 绝对路径,完成后可得)
router.get('/tasks/:taskId', (req, res) => {
  const view = getDiagTaskView(req.params.taskId, req.user);
  if (!view) return res.status(404).json({ success: false, error: 'Task not found' });
  res.json({ success: true, data: view });
});

export default router;
