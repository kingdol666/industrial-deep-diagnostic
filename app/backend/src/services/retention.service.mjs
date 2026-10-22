// Workspace retention — keeps `workspace/diagnostic-runs` bounded (plan v2 D5).
//
// Two independent policies, both driven by config.data:
//   * retention_days          — completed/stopped/failed run workspaces older
//                               than N days are removed; the DB row stays (its
//                               report paths are cleared so the API is honest).
//   * purge_deleted_after_days — runs whose soft delete is older than N days
//                               are purged entirely (row + workspace).
// Runs that are still live (pending/running/awaiting_input) are never touched.
import { existsSync, rmSync, readdirSync, statSync } from 'fs';
import { join, relative } from 'path';
import { stmts } from '../db/database.mjs';
import { PROJECT_ROOT, config } from '../../../../config/loader.mjs';
import logger from '../utils/logger.mjs';

const LIVE = new Set(['pending', 'running', 'awaiting_input']);

function daysAgoIso(days) {
  const ms = Date.now() - Number(days) * 24 * 60 * 60 * 1000;
  return new Date(ms).toISOString().replace('T', ' ').slice(0, 19);
}

function removeWorkspace(recorded) {
  if (!recorded) return false;
  const normalized = String(recorded).replace(/\\/g, '/');
  if (!normalized.startsWith('workspace/diagnostic-runs/')) return false;
  const abs = join(PROJECT_ROOT, normalized);
  if (!existsSync(abs)) return false;
  try {
    rmSync(abs, { recursive: true, force: true });
    return true;
  } catch (err) {
    logger.warn(`Retention: failed to remove ${normalized}: ${err.message}`, { context: 'Retention' });
    return false;
  }
}

/**
 * Apply both retention policies. Called once at startup; safe to call again.
 * @returns {{expiredWorkspaces:number, purgedRuns:number, orphansRemoved:number}}
 */
export function applyRetentionPolicies(now = Date.now()) {
  const retentionDays = Number(config.data?.retention_days);
  const purgeDays = Number(config.data?.purge_deleted_after_days);
  let expiredWorkspaces = 0;
  let purgedRuns = 0;

  // 1) Purge soft-deleted runs past their grace period (row + workspace).
  if (Number.isFinite(purgeDays) && purgeDays >= 0) {
    const cutoff = daysAgoIso(purgeDays);
    const rows = stmts.listRunsFiltered.all({
      userId: null, includeDeleted: 1, categoryId: null, status: null, q: null,
      limit: 10000, offset: 0,
    }).filter((r) => r.deleted_at && r.deleted_at <= cutoff);
    for (const row of rows) {
      removeWorkspace(row.workspace_path);
      try {
        stmts.deleteLogsByRunId.run(row.run_id);
        stmts.deleteEventStreamByRunId.run(row.run_id);
        stmts.deleteRunRow.run(row.run_id);
        purgedRuns += 1;
      } catch (err) {
        logger.warn(`Retention: purge failed for ${row.run_id}: ${err.message}`, { context: 'Retention' });
      }
    }
  }

  // 2) Expire old workspaces of terminal runs (DB row and its history stay).
  if (Number.isFinite(retentionDays) && retentionDays > 0) {
    const cutoff = daysAgoIso(retentionDays);
    const rows = stmts.listRunsFiltered.all({
      userId: null, includeDeleted: 1, categoryId: null, status: null, q: null,
      limit: 10000, offset: 0,
    }).filter((r) => !r.deleted_at && r.workspace_path && r.created_at && r.created_at <= cutoff
      && !LIVE.has(r.status));
    for (const row of rows) {
      if (removeWorkspace(row.workspace_path)) {
        // Keep the row; clear the now-dangling pointers so APIs do not 404-fail
        // silently while still advertising a report that no longer exists.
        stmts.clearRunWorkspacePaths.run({ runId: row.run_id });
        expiredWorkspaces += 1;
      }
    }
  }

  // 3) Orphan sweep: directories on disk with no DB row (older than the
  // retention horizon) are removed. This is the failure mode the adoption bug
  // used to produce; the sweep keeps it from accumulating.
  let orphansRemoved = 0;
  const wsRoot = join(PROJECT_ROOT, config.data?.workspace_dir || 'workspace/diagnostic-runs');
  if (Number.isFinite(retentionDays) && retentionDays > 0 && existsSync(wsRoot)) {
    const claimed = new Set(
      stmts.getClaimedWorkspacePaths.all()
        .map((r) => String(r.workspace_path || '').replace(/\\/g, '/'))
        .filter(Boolean)
        .map((p) => p.split('/').pop()),
    );
    const cutoffMs = now - retentionDays * 24 * 60 * 60 * 1000;
    for (const name of readdirSync(wsRoot)) {
      const dir = join(wsRoot, name);
      try {
        if (!statSync(dir).isDirectory()) continue;
        if (claimed.has(name)) continue;
        if (statSync(dir).mtimeMs > cutoffMs) continue;
        rmSync(dir, { recursive: true, force: true });
        orphansRemoved += 1;
      } catch { /* ignore a single unreadable entry */ }
    }
  }

  if (expiredWorkspaces || purgedRuns || orphansRemoved) {
    logger.info(
      `Retention: expired ${expiredWorkspaces} workspace(s), purged ${purgedRuns} run(s), `
      + `removed ${orphansRemoved} orphan dir(s)`,
      { context: 'Retention' },
    );
  }
  return { expiredWorkspaces, purgedRuns, orphansRemoved, ...applyEventStreamRetention() };
}

/** Exposed for tests: relative form of a workspace path, or null. */
export function workspaceRel(abs) {
  if (!abs) return null;
  return relative(PROJECT_ROOT, abs).replace(/\\/g, '/');
}

/**
 * Bound the event log per run. A long claude run can emit >100k events; the UI
 * only ever renders the newest window, so keeping every row forever grows the
 * DB without adding user-visible value. The newest N rows are kept (MAX(seq)
 * is preserved, so session-chat sequence continuation stays correct).
 * Only terminal runs are pruned — a live run's tail is its live stream.
 * @returns {{runs:number, deleted:number}}
 */
export function applyEventStreamRetention({ runIds = null } = {}) {
  const cap = Number(config.data?.event_stream_max_rows_per_run);
  if (!Number.isFinite(cap) || cap <= 0) return { eventRunsPruned: 0, eventRowsDeleted: 0 };
  const keep = Math.trunc(cap);
  let runs = 0;
  let deleted = 0;
  // `runIds` scopes the sweep for tests. Tests MUST pass it: a global sweep
  // with a test-sized cap would prune every run in the database.
  const candidates = Array.isArray(runIds)
    ? runIds
      .map((id) => ({ run_id: id, n: stmts.countEventStreamByRunId.get(id).n }))
      .filter((row) => row.n > keep)
    : stmts.listRunsOverEventCap.all({ cap: keep });
  for (const row of candidates) {
    const run = stmts.getRunById.get(row.run_id);
    if (!run || LIVE.has(run.status)) continue;
    const before = Number(row.n);
    try {
      stmts.pruneEventStreamForRun.run({ runId: row.run_id, keep });
      const after = stmts.countEventStreamByRunId.get(row.run_id).n;
      deleted += Math.max(0, before - after);
      runs += 1;
    } catch (err) {
      logger.warn(`Retention: event prune failed for ${row.run_id}: ${err.message}`, { context: 'Retention' });
    }
  }
  if (runs > 0) {
    logger.info(`Retention: pruned ${deleted} old event row(s) across ${runs} run(s) (keep ${keep}/run)`, {
      context: 'Retention',
    });
  }
  return { eventRunsPruned: runs, eventRowsDeleted: deleted };
}
