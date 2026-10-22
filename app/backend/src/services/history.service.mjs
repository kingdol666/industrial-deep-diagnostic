// History Service — CRUD + session management for diagnosis runs.
//
// Management model (plan v2 Phase A):
//   * ownership: a run belongs to the user who created it; admins see everything;
//   * soft delete: `deleted_at` hides a run from the default list and keeps it
//     restorable; an explicit purge removes the row AND its workspace directory;
//   * categories: one flat, user-defined category per run (run_categories).
import { randomUUID } from 'crypto';
import { rmSync } from 'fs';
import { stmts } from '../db/database.mjs';
import { getRunRealtimeSnapshot, listRuns } from './diagnosis.service.mjs';
import logger from '../utils/logger.mjs';

const DEFAULT_LIMIT = 200;
const MAX_LIMIT = 1000;
const TITLE_MAX = 200;
const CATEGORY_MAX = 60;

function httpError(status, code, message) {
  const err = new Error(message);
  err.status = status;
  err.code = code;
  return err;
}

/** Legacy unfiltered listing (kept for internal callers/tests). */
export function getAllRuns() {
  return listRuns().map(run => ({
    ...run,
    liveStatus: run.engineStatus || run.status,
  }));
}

/**
 * Filtered, paginated listing. `user` is the authenticated principal
 * ({ id, role }); a non-admin only ever sees their own runs. `userId: null`
 * (legacy/no-auth callers) means "no ownership filter" — admin semantics.
 */
export function listRunsForUser(user, {
  includeDeleted = false,
  categoryId = null,
  status = null,
  q = null,
  limit = DEFAULT_LIMIT,
  offset = 0,
} = {}) {
  const isAdmin = user?.role === 'admin' || !user?.id;
  const userId = isAdmin ? null : String(user.id);
  const lim = Math.min(MAX_LIMIT, Math.max(1, Number(limit) || DEFAULT_LIMIT));
  const off = Math.max(0, Number(offset) || 0);
  const params = {
    userId,
    includeDeleted: includeDeleted ? 1 : 0,
    categoryId: categoryId || null,
    status: status || null,
    q: q ? `%${String(q).trim()}%` : null,
    limit: lim,
    offset: off,
  };
  const rows = stmts.listRunsFiltered.all(params);
  const total = stmts.countRunsFiltered.get(params).n;
  // Live engine status is only meaningful for rows that still have a live run.
  const live = new Map(listRuns().map(r => [r.run_id, r.engineStatus]));
  return {
    runs: rows.map(run => ({
      ...run,
      liveStatus: live.get(run.run_id) || run.status,
    })),
    total,
    limit: lim,
    offset: off,
  };
}

export function getRunWithLogs(runId) {
  const snapshot = getRunRealtimeSnapshot(runId);
  const run = snapshot?.run || stmts.getRunById.get(runId);
  if (!run) return null;
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

// ── ownership ────────────────────────────────────────────────────────────

/** Load a run the caller may manage. Throws 404/403. */
export function requireRun(runId, user = null) {
  const run = stmts.getRunById.get(runId);
  if (!run) throw httpError(404, 'RUN_NOT_FOUND', `Run not found: ${runId}`);
  if (user?.id && user.role !== 'admin' && run.user_id && String(run.user_id) !== String(user.id)) {
    throw httpError(403, 'RUN_FORBIDDEN', 'This run belongs to another user');
  }
  return run;
}

// ── rename / categorize ──────────────────────────────────────────────────

export function renameRun(runId, title, user = null) {
  requireRun(runId, user);
  const clean = typeof title === 'string' ? title.trim() : '';
  if (!clean) throw httpError(400, 'TITLE_REQUIRED', 'title must be a non-empty string');
  if (clean.length > TITLE_MAX) throw httpError(400, 'TITLE_TOO_LONG', `title must be ≤ ${TITLE_MAX} characters`);
  stmts.renameRun.run({ runId, title: clean });
  return stmts.getRunById.get(runId);
}

export function setRunCategory(runId, categoryId, user = null) {
  requireRun(runId, user);
  let next = null;
  if (categoryId !== null && categoryId !== undefined && categoryId !== '') {
    const category = stmts.getCategoryById.get(String(categoryId));
    if (!category) throw httpError(404, 'CATEGORY_NOT_FOUND', `Category not found: ${categoryId}`);
    if (user?.id && user.role !== 'admin' && String(category.user_id) !== String(user.id)) {
      throw httpError(403, 'CATEGORY_FORBIDDEN', 'This category belongs to another user');
    }
    next = category.id;
  }
  stmts.setRunCategory.run({ runId, categoryId: next });
  return stmts.getRunById.get(runId);
}

// ── delete / restore ─────────────────────────────────────────────────────

/** Soft delete: hide from the default list, keep everything restorable. */
export function softDeleteRun(runId, user = null) {
  requireRun(runId, user);
  stmts.softDeleteRun.run({ runId });
  return { run_id: runId, deleted: true, purged: false };
}

export function restoreRun(runId, user = null) {
  requireRun(runId, user);
  stmts.restoreRun.run({ runId });
  return stmts.getRunById.get(runId);
}

/**
 * Hard delete: remove the row, its logs/events (FK CASCADE) AND the workspace
 * directory. Removing the directory matters beyond disk hygiene: the "latest
 * unclaimed directory" adoption in findLatestRunDir would otherwise let a later
 * run of the same scene claim this run's artifacts.
 */
export function purgeRun(runId, user = null) {
  const run = requireRun(runId, user);
  removeWorkspaceDir(run);
  // Explicit deletes keep working even when the FK cascade was disabled by an
  // old database file.
  stmts.deleteLogsByRunId.run(runId);
  stmts.deleteEventStreamByRunId.run(runId);
  stmts.deleteRunRow.run(runId);
  return { run_id: runId, deleted: true, purged: true, workspace_removed: !!run.workspace_path };
}

/** Legacy DELETE semantics (row-only) are now soft delete + explicit purge. */
export function deleteRun(runId, user = null, { purge = false } = {}) {
  return purge ? purgeRun(runId, user) : softDeleteRun(runId, user);
}

function removeWorkspaceDir(run) {
  const ws = run.workspace_path;
  if (!ws) return;
  // Only ever delete inside the managed workspace tree.
  const normalized = String(ws).replace(/\\/g, '/');
  if (!normalized.startsWith('workspace/diagnostic-runs/')) {
    logger.warn(`Refusing to purge workspace outside diagnostic-runs: ${ws}`, { context: 'History' });
    return;
  }
  try {
    rmSync(ws, { recursive: true, force: true });
  } catch (err) {
    logger.warn(`Workspace purge failed for ${ws}: ${err.message}`, { context: 'History' });
  }
}

// ── categories ───────────────────────────────────────────────────────────

function validateCategoryName(name) {
  const clean = typeof name === 'string' ? name.trim() : '';
  if (!clean) throw httpError(400, 'CATEGORY_NAME_REQUIRED', 'name must be a non-empty string');
  if (clean.length > CATEGORY_MAX) {
    throw httpError(400, 'CATEGORY_NAME_TOO_LONG', `name must be ≤ ${CATEGORY_MAX} characters`);
  }
  return clean;
}

export function listCategories(user = null) {
  const userId = user?.role === 'admin' || !user?.id ? null : String(user.id);
  return stmts.listCategories.all({ userId });
}

export function createCategory(name, user) {
  if (!user?.id) throw httpError(401, 'AUTH_REQUIRED', 'Authentication required to create a category');
  const clean = validateCategoryName(name);
  const userId = String(user.id);
  if (stmts.getCategoryByName.get({ userId, name: clean })) {
    throw httpError(409, 'CATEGORY_EXISTS', `Category "${clean}" already exists`);
  }
  const id = `CAT-${randomUUID().slice(0, 8)}`;
  stmts.insertCategory.run({ id, userId, name: clean });
  return stmts.getCategoryById.get(id);
}

export function renameCategory(categoryId, name, user = null) {
  const category = stmts.getCategoryById.get(categoryId);
  if (!category) throw httpError(404, 'CATEGORY_NOT_FOUND', `Category not found: ${categoryId}`);
  if (user?.id && user.role !== 'admin' && String(category.user_id) !== String(user.id)) {
    throw httpError(403, 'CATEGORY_FORBIDDEN', 'This category belongs to another user');
  }
  const clean = validateCategoryName(name);
  const clash = stmts.getCategoryByName.get({ userId: category.user_id, name: clean });
  if (clash && clash.id !== category.id) {
    throw httpError(409, 'CATEGORY_EXISTS', `Category "${clean}" already exists`);
  }
  stmts.renameCategory.run({ id: categoryId, name: clean });
  return stmts.getCategoryById.get(categoryId);
}

/** Deleting a category never deletes runs: their category_id is cleared. */
export function deleteCategory(categoryId, user = null) {
  const category = stmts.getCategoryById.get(categoryId);
  if (!category) throw httpError(404, 'CATEGORY_NOT_FOUND', `Category not found: ${categoryId}`);
  if (user?.id && user.role !== 'admin' && String(category.user_id) !== String(user.id)) {
    throw httpError(403, 'CATEGORY_FORBIDDEN', 'This category belongs to another user');
  }
  stmts.clearCategoryRefs.run(categoryId);
  stmts.deleteCategory.run(categoryId);
  return { id: categoryId, deleted: true };
}
