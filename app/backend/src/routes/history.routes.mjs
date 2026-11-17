// History Routes — Thin HTTP handlers, delegates business logic to history service
//
// Tenancy: the viewer is always req.user — another user's run answers 404 on
// every verb (see history.service.mjs).

import { Router } from 'express';
import { getAllRuns, getRunWithLogs, deleteRun } from '../services/history.service.mjs';
import logger from '../utils/logger.mjs';

const router = Router();

function sendError(res, err, fallbackCode) {
  const status = err?.status || 500;
  if (status >= 500) {
    // B4: internal messages stay server-side; the client gets a stable code.
    logger.error(`[history] ${err?.stack || err?.message || err}`, { context: 'History' });
    return res.status(status).json({ success: false, code: err?.code || fallbackCode, error: '历史记录服务内部错误，请查看后端日志后重试' });
  }
  return res.status(status).json({
    success: false,
    ...(err?.code ? { code: err.code } : {}),
    error: err?.message || '请求无效',
  });
}

// Get all runs (own runs; every run for an admin)
router.get('/runs', (req, res) => {
  try {
    const runs = getAllRuns(req.user);
    res.json({ success: true, data: runs });
  } catch (err) {
    sendError(res, err, 'HISTORY_LIST_FAILED');
  }
});

// Get a specific run with logs
router.get('/runs/:runId', (req, res) => {
  try {
    const run = getRunWithLogs(req.params.runId, req.user);
    if (!run) return res.status(404).json({ success: false, error: 'Run not found' });
    res.json({ success: true, data: run });
  } catch (err) {
    sendError(res, err, 'HISTORY_GET_FAILED');
  }
});

// Delete a run record
router.delete('/runs/:runId', (req, res) => {
  try {
    deleteRun(req.params.runId, req.user);
    res.json({ success: true });
  } catch (err) {
    sendError(res, err, 'HISTORY_DELETE_FAILED');
  }
});

export default router;
