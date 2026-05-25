// History Service — CRUD operations for diagnosis run history

import { db, stmts } from '../db/database.mjs';

export function getAllRuns() {
  return stmts.getAllRuns.all();
}

export function getRunWithLogs(runId) {
  const run = stmts.getRunById.get(runId);
  if (!run) return null;
  const logs = stmts.getLogsByRunId.all(runId);
  return { ...run, logs };
}

export function deleteRun(runId) {
  const run = stmts.getRunById.get(runId);
  if (!run) {
    const err = new Error('Run not found');
    err.status = 404;
    throw err;
  }
  db.prepare('DELETE FROM diagnosis_logs WHERE run_id = ?').run(runId);
  db.prepare('DELETE FROM diagnostic_runs WHERE run_id = ?').run(runId);
  return true;
}
