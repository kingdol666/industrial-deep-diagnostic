// History Routes — Thin HTTP handlers, delegates business logic to history service

import { Router } from 'express';
import { getAllRuns, getRunWithLogs, deleteRun } from '../services/history.service.mjs';

const router = Router();

// Get all runs
router.get('/runs', (req, res) => {
  try {
    const runs = getAllRuns();
    res.json({ success: true, data: runs });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

// Get a specific run with logs
router.get('/runs/:runId', (req, res) => {
  try {
    const run = getRunWithLogs(req.params.runId);
    if (!run) return res.status(404).json({ success: false, error: 'Run not found' });
    res.json({ success: true, data: run });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

// Delete a run record
router.delete('/runs/:runId', (req, res) => {
  try {
    deleteRun(req.params.runId);
    res.json({ success: true });
  } catch (err) {
    const status = err.status || 500;
    res.status(status).json({ success: false, error: err.message });
  }
});

export default router;
