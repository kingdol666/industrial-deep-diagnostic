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
} from '../services/external.service.mjs';
import { ANALYSIS_INTENTS } from '../engine/claude-client.mjs';

const router = Router();
const TERMINAL = new Set(['completed', 'failed', 'stopped', 'interrupted']);

// ── GET /v1/capabilities — mode + harness discovery ────────────────────────
router.get('/v1/capabilities', async (req, res) => {
  try {
    const intents = listIntents();
    let harnesses = [];
    try {
      harnesses = (listHarnesses() || []).map((h) => ({
        id: h.id,
        label: h.label ?? h.name ?? h.id,
        runs_capable: !!h.runsCapable,
      }));
    } catch { /* harness listing is advisory for callers */ }
    res.json({ success: true, data: { intents, harnesses } });
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
      reportLanguage: body.reportLanguage || 'zh',
      userQuestion: body.question || '',
      maxTurns: body.maxTurns,
    });
    const runId = created.runId;
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
      while (Date.now() < deadline) {
        await new Promise((r) => setTimeout(r, 2000));
        const cur = await buildExternalResult(runId);
        if (!cur) break;
        if (TERMINAL.has(cur.status)) {
          return res.json({ success: true, data: cur });
        }
      }
      return res.status(202).json({
        success: true,
        data: { ...((await buildExternalResult(runId)) || { run_id: runId }), wait: 'timeout_still_running' },
      });
    }

    res.status(202).json({
      success: true,
      data: {
        run_id: runId,
        status: 'running',
        links: {
          status: `/api/external/v1/analyze/${runId}`,
          result: `/api/external/v1/analyze/${runId}`,
          stream: `/api/external/v1/analyze/${runId}/stream`,
        },
      },
    });
  } catch (err) {
    const status = err.status || 500;
    res.status(status).json({
      success: false, code: err.code || 'EXTERNAL_ANALYZE_ERROR', error: err.message,
    });
  }
});

// ── GET /v1/analyze/:runId — unified status/result view ────────────────────
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
  const sent = await chatWithRun(runId, message);
  if (!sent) {
    return res.status(409).json({
      success: false,
      code: 'EXTERNAL_CHAT_UNAVAILABLE',
      error: 'Run not found or no live engine process — chat requires a running analysis.',
    });
  }
  res.json({ success: true, data: { run_id: runId, delivered: true } });
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
