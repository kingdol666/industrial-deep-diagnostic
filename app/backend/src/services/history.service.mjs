// History Service — CRUD operations for diagnosis run history
//
// Tenancy (P0-6): every read/delete is viewer-scoped. `viewer` is req.user for
// API callers (own runs, everything for an admin; legacy NULL-owner runs are
// admin-only) and INTERNAL for trusted service-internal calls. A run the
// viewer may not see is reported exactly like a missing one (null / 404).

import { db, stmts } from '../db/database.mjs';
import { getRunRealtimeSnapshot, getRunStatus, listRuns } from './diagnosis.service.mjs';
import { INTERNAL } from './tenancy.mjs';

export function getAllRuns(viewer = INTERNAL) {
  return listRuns(viewer).map(run => ({
    ...run,
    liveStatus: run.engineStatus || run.status,
  }));
}

export function getRunWithLogs(runId, viewer = INTERNAL) {
  const run = getRunStatus(runId, viewer);
  if (!run) return null;
  const snapshot = getRunRealtimeSnapshot(runId, viewer);
  const logs = stmts.getLogsByRunId.all(runId);
  return {
    ...run,
    engineStatus: snapshot?.liveStatus || run.engineStatus || run.status,
    liveStatus: snapshot?.liveStatus || run.engineStatus || run.status,
    hasActiveEngineRun: snapshot?.hasActiveEngineRun || false,
    currentQuestion: snapshot?.currentQuestion || null,
    logs,
  };
}

export function deleteRun(runId, viewer = INTERNAL) {
  const run = getRunStatus(runId, viewer);
  if (!run) {
    const err = new Error('Run not found');
    err.status = 404;
    err.code = 'NOT_FOUND';
    throw err;
  }
  db.prepare('DELETE FROM diagnosis_logs WHERE run_id = ?').run(runId);
  stmts.deleteEventStreamByRunId.run(runId);
  db.prepare('DELETE FROM diagnostic_runs WHERE run_id = ?').run(runId);
  return true;
}
