import { Router } from 'express';
import { db, stmts } from '../db.mjs';

const router = Router();

// Get all runs
router.get('/runs', (req, res) => {
  try {
    const runs = stmts.getAllRuns.all();
    res.json({ success: true, data: runs });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

// Get a specific run with logs
router.get('/runs/:runId', (req, res) => {
  try {
    const run = stmts.getRunById.get(req.params.runId);
    if (!run) return res.status(404).json({ success: false, error: 'Run not found' });
    const logs = stmts.getLogsByRunId.all(req.params.runId);
    res.json({ success: true, data: { ...run, logs } });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

// Delete a run record
router.delete('/runs/:runId', (req, res) => {
  try {
    const run = stmts.getRunById.get(req.params.runId);
    if (!run) return res.status(404).json({ success: false, error: 'Run not found' });
    db.prepare('DELETE FROM diagnosis_logs WHERE run_id = ?').run(req.params.runId);
    db.prepare('DELETE FROM diagnostic_runs WHERE run_id = ?').run(req.params.runId);
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

export default router;
