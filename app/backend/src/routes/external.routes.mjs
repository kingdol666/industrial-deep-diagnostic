// External Routes — v1 integration surface for outside applications.
//
// Stable namespace: /api/external/v1/*
//   GET  /capabilities                → modes (analysis intents) + harness list
//   POST /v1/analyze                  → launch an analysis (mode + harness + folder)
//   GET  /v1/analyze/:runId           → unified status/result view
//   GET  /v1/analyze/:runId/stream    → SSE live events, ends with `result`
//   POST /v1/chat                     → send a dialogue message into a live run
//   POST /v1/analyze/:runId/stop      → stop a running analysis
//
// Auth: inherited from the global authGuard — session JWT or `idd_` API token.
// Everything delegates to the same services the web console uses; this layer
// only shapes an integration-friendly contract.

import { Router } from 'express';

import { listHarnesses } from '../harness/registry.mjs';
import {
  assertRunHarnessUsable, validateDataPath, createDiagnosisRun,
  triggerDiagnosis, stopDiagnosis, subscribeSSE, startStream,
} from '../services/diagnosis.service.mjs';
import {
  buildExternalResult, chatWithRun, findIntent, listIntents,
  createTask, refreshTask, getTaskEntry, listTaskEntries, getTaskByRun,
} from '../services/external.service.mjs';
import { ANALYSIS_INTENTS } from '../engine/claude-client.mjs';
import { supportedIntentsFor } from '../services/intent-capability.service.mjs';
import { engineSupportsSessionChat } from '../services/session-integrity.service.mjs';
import { listResults, getResultDetail, updateResult } from '../services/results-library.service.mjs';

const router = Router();
const TERMINAL = new Set(['completed', 'failed', 'stopped', 'interrupted', 'expired', 'awaiting_input']);

// ── GET /v1/capabilities — mode + harness discovery ────────────────────────
router.get('/v1/capabilities', async (req, res) => {
  try {
    const intents = listIntents();
    let harnesses = [];
    try {
      harnesses = (listHarnesses() || []).map((h) => ({
        id: h.id,
        label: h.label ?? h.name ?? h.id,
        runs_capable: Array.isArray(h.capabilities) && h.capabilities.includes('runs'),
        // Honest capability surface: exact engine support, not a guess.
        session_resume: engineSupportsSessionChat(h.id),
        supported_intents: supportedIntentsFor(h.id),
      }));
    } catch { /* harness listing is advisory for callers */ }
    res.json({
      success: true,
      data: {
        intents,
        results_index: true,
        results_endpoints: [
          'GET /api/external/v1/results',
          'GET /api/external/v1/results/:resultId',
          'PATCH /api/external/v1/results/:resultId',
        ],
        harnesses,
      },
    });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

// ── POST /v1/analyze — launch an analysis on a selected harness ────────────
// Body: {
//   folderPath (required), analysisIntent (default deep-diagnosis),
//   harness (default claude — must be omp / claude / mock / …), sceneName?,
//   question? (→ objective + user_question), reportLanguage? (default zh),
//   wait?: bool (block until terminal; cap wait_timeout_minutes, default 30)
// }
router.post('/v1/analyze', async (req, res) => {
  try {
    const body = req.body || {};
    const harness = body.harness || 'claude';
    const intent = body.analysisIntent
      ? findIntent(body.analysisIntent) : 'deep-diagnosis';
    if (body.analysisIntent && !intent) {
      return res.status(400).json({
        success: false, code: 'EXTERNAL_INTENT_UNKNOWN',
        error: `unknown analysisIntent: ${body.analysisIntent}`,
        supported: Object.keys(ANALYSIS_INTENTS),
      });
    }
    await assertRunHarnessUsable(harness);
    if (!body.folderPath && !body.dataPath && !(Array.isArray(body.dataPaths) && body.dataPaths.length)) {
      return res.status(400).json({
        success: false, code: 'EXTERNAL_DATA_REQUIRED',
        error: 'folderPath (or dataPath/dataPaths) is required',
      });
    }
    if (body.folderPath) await validateDataPath(body.folderPath);
    if (body.dataPath) await validateDataPath(body.dataPath);

    const created = createDiagnosisRun({
      folderPath: body.folderPath,
      dataPath: body.dataPath,
      dataPaths: body.dataPaths,
      sceneName: body.sceneName,
      harness,
      analysisIntent: intent,
      // Attribute the run to the authenticated caller so results-library
      // ownership enforcement (RESULT_FORBIDDEN) applies to external runs too.
      userId: req.user?.id ?? null,
      // DOE ontology-first policy (contracts §7.3). Omitted fields fall back to
      // mode=auto/data_stage=collected; `off` is refused unless the dev override
      // is explicitly set (an external caller can never silently skip the gate).
      ontologyMode: body.ontologyMode,
      ontologyScene: body.ontologyScene,
      ontologySource: body.ontologySource,
      ontologyDataStage: body.ontologyDataStage,
      ontologyDevOverride: body.ontologyDevOverride,
      preprocessingMode: body.preprocessingMode,
      reportLanguage: body.reportLanguage || 'zh',
      userQuestion: body.question || '',
      maxTurns: body.maxTurns,
    });
    const runId = created.runId;
    // Non-wait callers track THIS id through the task manager: the entry owns
    // progress polling and, once terminal, the stored unified result incl.
    // report file paths (md + every html artifact).
    const task = createTask(runId, {
      intent, harness, scene: body.sceneName ?? null, objective: body.question ?? null,
    });
    try {
      triggerDiagnosis(runId);
    } catch (execErr) {
      // launch failure leaves the run marked failed — the result view reports it
      console.warn(`[external] analyze launch failed: ${execErr.message}`);
    }

    const wait = body.wait === true;
    const capMs = Math.max(1, Number(body.wait_timeout_minutes) || 30) * 60 * 1000;
    if (wait) {
      const deadline = Date.now() + capMs;
      let cur = await refreshTask(task.task_id);
      while (cur && !TERMINAL.has(cur.status) && Date.now() < deadline) {
        await new Promise((r) => setTimeout(r, 2000));
        cur = await refreshTask(task.task_id);
      }
      if (cur && TERMINAL.has(cur.status)) {
        return res.json({ success: true, data: cur });
      }
      return res.status(202).json({
        success: true,
        data: { ...(cur || task), wait: 'timeout_still_running' },
      });
    }

    res.status(202).json({
      success: true,
      data: {
        task_id: task.task_id,
        run_id: runId,
        status: task.status,
        links: task.links,
      },
    });
  } catch (err) {
    const status = err.status || 500;
    res.status(status).json({
      success: false, code: err.code || 'EXTERNAL_ANALYZE_ERROR', error: err.message,
    });
  }
});

// ── GET /v1/tasks — list tasks tracked by this backend instance ────────────
router.get('/v1/tasks', (req, res) => {
  res.json({ success: true, data: listTaskEntries() });
});

// ── Results library (2026-10-25): summary index → id → detail, for agents ──
// Index cards carry display_text = description || summary; `brief=true` is the
// token-saving mode (no key_numbers, display_text capped at 160 chars).
router.get('/v1/results', (req, res) => {
  try {
    const data = listResults(req.user, req.query);
    res.json({ success: true, data: data });
  } catch (err) {
    res.status(err.status || 500).json({
      success: false,
      code: err.code || 'RESULTS_QUERY_INVALID',
      error: err.message,
    });
  }
});

// Detail: summary_json (auditable key numbers + sources), metadata (report /
// artifacts / fingerprint), report_md full text (include_md=false to skip).
router.get('/v1/results/:resultId', (req, res) => {
  try {
    const includeMd = req.query.include_md !== 'false' && req.query.include_md !== '0';
    const detail = getResultDetail(req.params.resultId, { user: req.user, includeMd });
    res.json({ success: true, data: detail });
  } catch (err) {
    res.status(err.status || 500).json({
      success: false,
      code: err.code || 'RESULTS_ERROR',
      error: err.message,
    });
  }
});

// Editable: description / tags / title / category_id. summary is read-only.
router.patch('/v1/results/:resultId', (req, res) => {
  try {
    const detail = updateResult(req.params.resultId, req.body || {}, req.user);
    res.json({ success: true, data: detail });
  } catch (err) {
    res.status(err.status || 500).json({
      success: false,
      code: err.code || 'RESULTS_ERROR',
      error: err.message,
    });
  }
});

// ── GET /v1/tasks/:taskId — live progress view (poll this) ─────────────────
router.get('/v1/tasks/:taskId', async (req, res) => {
  const entry = await refreshTask(req.params.taskId);
  if (!entry) {
    // fall back to run-based lookup when the caller only knows the run id
    const byRun = getTaskByRun(req.params.taskId);
    if (byRun) return res.json({ success: true, data: await refreshTask(byRun.task_id) });
    return res.status(404).json({ success: false, error: 'Task not found' });
  }
  res.json({ success: true, data: entry });
});

// ── GET /v1/tasks/:taskId/result — the stored analysis result ──────────────
// Returns the manager's stored result (stable across calls): summary/score/
// verdict/report.md plus concrete md/html file paths. 409 while still running.
router.get('/v1/tasks/:taskId/result', async (req, res) => {
  const entry = await refreshTask(req.params.taskId);
  if (!entry) return res.status(404).json({ success: false, error: 'Task not found' });
  if (!TERMINAL.has(entry.status)) {
    return res.status(409).json({
      success: false,
      code: 'EXTERNAL_TASK_RUNNING',
      error: `task is ${entry.status} — result is available after completion`,
      data: { task_id: entry.task_id, status: entry.status, progress: entry.progress },
    });
  }
  res.json({
    success: true,
    data: {
      task_id: entry.task_id,
      run_id: entry.run_id,
      status: entry.status,
      finished_at: entry.finished_at,
      result: entry.result,
      error: entry.error,
    },
  });
});

// ── GET /v1/analyze/:runId — unified status/result view (run-based) ────────
router.get('/v1/analyze/:runId', async (req, res) => {
  const view = await buildExternalResult(req.params.runId);
  if (!view) return res.status(404).json({ success: false, error: 'Run not found' });
  res.json({ success: true, data: view });
});

// ── GET /v1/analyze/:runId/stream — SSE; ends with a `result` event ────────
router.get('/v1/analyze/:runId/stream', async (req, res) => {
  const { runId } = req.params;
  const streamInfo = startStream(runId);
  if (!streamInfo) {
    return res.status(404).json({ success: false, error: 'Run not found' });
  }

  res.writeHead(200, {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    Connection: 'keep-alive',
    'X-Accel-Buffering': 'no',
  });
  const sendSSE = (event, data) => {
    if (!res.destroyed) res.write(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`);
  };

  // Already terminal → emit the unified result immediately and close.
  const current = await buildExternalResult(runId);
  if (current && TERMINAL.has(current.status)) {
    sendSSE('result', current);
    res.end();
    return;
  }

  const unsub = subscribeSSE(runId, (event, data) => {
    if (res.destroyed) return;
    if (event === 'stream_end') {
      buildExternalResult(runId).then((final) => {
        if (final) sendSSE('result', final);
        if (!res.destroyed) res.end();
      });
    } else {
      sendSSE(event, data);
    }
  });

  req.on('close', () => {
    unsub();
    if (!res.destroyed) res.end();
  });

  if (streamInfo.currentStatus === 'pending') {
    try { triggerDiagnosis(runId); } catch { /* failed runs report via result */ }
  }
});

// ── POST /v1/chat — dialogue into a live analysis run ──────────────────────
router.post('/v1/chat', async (req, res) => {
  const { run_id: runId, message } = req.body || {};
  if (!runId || !message || typeof message !== 'string') {
    return res.status(400).json({
      success: false,
      error: 'run_id and message (string) are required',
    });
  }
  try {
    const sent = await chatWithRun(runId, message);
    if (!sent) {
      return res.status(404).json({
        success: false,
        code: 'RUN_NOT_FOUND',
        error: `Run not found: ${runId}`,
      });
    }
    res.json({
      success: true,
      data: {
        run_id: runId,
        delivered: true,
        mode: sent.mode,
        resumed: sent.mode === 'session',
        reason: sent.reason ?? null,
      },
    });
  } catch (err) {
    res.status(err.status || 500).json({
      success: false,
      code: err.code || 'CHAT_ERROR',
      error: err.message,
      harness: err.harness ?? null,
      run_id: err.runId ?? runId,
    });
  }
});

// ── POST /v1/analyze/:runId/stop — stop a running analysis ─────────────────
router.post('/v1/analyze/:runId/stop', (req, res) => {
  try {
    stopDiagnosis(req.params.runId);
    res.json({ success: true, data: { run_id: req.params.runId, status: 'stopped' } });
  } catch (err) {
    res.status(err.status || 500).json({ success: false, error: err.message });
  }
});

export default router;
