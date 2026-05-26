// Diagnosis Routes — Thin HTTP handlers, delegates business logic to diagnosis service

import { Router } from 'express';
import {
  validateDataPath, createDiagnosisRun, listRuns, getRunStatus,
  stopDiagnosis, resolveHITLRequest, getPendingHITL,
  sendChatMessage, continueDiagnosis, answerQuestion,
  triggerDiagnosis, startStream, subscribeSSE,
} from '../services/diagnosis.service.mjs';
import { getChild, hasRun } from '../engine/diagnosis-engine.mjs';

const router = Router();

// Start a new diagnosis
router.post('/start', async (req, res) => {
  try {
    const { dataPath, folderPath, dataPaths, sceneName } = req.body;

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

    const result = createDiagnosisRun(req.body);
    res.json({ success: true, data: result });
  } catch (err) {
    const status = err.status || 500;
    res.status(status).json({ success: false, error: err.message });
  }
});

// List all diagnosis runs
router.get('/list', (_req, res) => {
  try {
    const runs = listRuns();
    res.json({ success: true, data: runs });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

// SSE stream endpoint
router.get('/stream/:runId', async (req, res) => {
  const { runId } = req.params;
  const streamInfo = startStream(runId);

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
    triggerDiagnosis(runId);
  }
});

// Stop a running diagnosis
router.post('/stop/:runId', (req, res) => {
  const { runId } = req.params;
  const child = getChild(runId);

  if (child && !child.killed) {
    stopDiagnosis(runId);
    res.json({ success: true, data: { runId, status: 'stopped' } });
  } else if (hasRun(runId)) {
    stopDiagnosis(runId);
    res.json({ success: true, data: { runId, status: 'stopped' } });
  } else {
    res.status(404).json({ success: false, error: 'No active process for this run' });
  }
});

// Trigger execution for an already-created pending run
router.post('/execute/:runId', async (req, res) => {
  try {
    const result = triggerDiagnosis(req.params.runId);
    res.json({ success: true, data: result });
  } catch (err) {
    const status = err.status || 500;
    res.status(status).json({ success: false, error: err.message });
  }
});

// Send a chat message to running Claude process
router.post('/chat/:runId', (req, res) => {
  const { runId } = req.params;
  const { message } = req.body;

  if (!message || typeof message !== 'string') {
    return res.status(400).json({ success: false, error: 'message is required' });
  }

  const sent = sendChatMessage(runId, message);
  if (!sent) {
    return res.status(404).json({
      success: false,
      error: 'Run not found or could not be resumed.',
    });
  }

  res.json({ success: true, data: { runId, resumed: true } });
});

// Continue / retry a failed or stopped run
router.post('/continue/:runId', async (req, res) => {
  try {
    const { followUpMessage } = req.body || {};
    const result = continueDiagnosis(req.params.runId, followUpMessage);
    res.json({ success: true, data: result });
  } catch (err) {
    const status = err.status || 500;
    res.status(status).json({ success: false, error: err.message });
  }
});

// Handle HITL approval/denial from frontend
router.post('/hitl/:hitlId', (req, res) => {
  const { approved } = req.body;
  const result = resolveHITLRequest(req.params.hitlId, approved);

  if (!result) {
    return res.status(404).json({ success: false, error: 'HITL request not found or already resolved' });
  }

  res.json({ success: true, data: result });
});

// Submit answer to AskUserQuestion
router.post('/answer/:runId', (req, res) => {
  const { runId } = req.params;
  const { questionId, toolUseId, answers } = req.body;

  if (!toolUseId || !answers) {
    return res.status(400).json({ success: false, error: 'toolUseId and answers are required' });
  }

  const answered = answerQuestion(runId, questionId, toolUseId, answers);
  if (!answered) {
    return res.status(404).json({ success: false, error: 'Process not found or already ended' });
  }

  res.json({ success: true, data: { runId, questionId, answered: true } });
});

// Get run status
router.get('/status/:runId', (req, res) => {
  const run = getRunStatus(req.params.runId);
  if (!run) return res.status(404).json({ success: false, error: 'Run not found' });
  res.json({ success: true, data: run });
});

// Check pending HITL requests for a run
router.get('/hitl/:runId', (req, res) => {
  const pending = getPendingHITL(req.params.runId);
  res.json({ success: true, data: { pending } });
});

export default router;
