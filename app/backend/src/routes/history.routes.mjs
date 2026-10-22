// History Routes — Thin HTTP handlers, delegates business logic to history service.
//
// Management surface (plan v2 Phase A): filtered listing, rename, categorize,
// soft delete / restore / purge, and per-user categories. Every mutating route
// passes the authenticated principal so ownership is enforced in one place.
import { Router } from 'express';
import {
  listRunsForUser, getRunWithLogs, deleteRun,
  renameRun, setRunCategory, softDeleteRun, restoreRun, purgeRun,
  listCategories, createCategory, renameCategory, deleteCategory,
} from '../services/history.service.mjs';

const router = Router();

function sendError(res, err) {
  const status = err.status || 500;
  res.status(status).json({ success: false, code: err.code || 'HISTORY_ERROR', error: err.message });
}

/** Express error wrapper (async-safe). */
const wrap = (fn) => (req, res) => {
  try {
    fn(req, res);
  } catch (err) {
    sendError(res, err);
  }
};

// List runs — ownership + soft-delete + category/status/text filters + paging.
router.get('/runs', wrap((req, res) => {
  const data = listRunsForUser(req.user, {
    includeDeleted: req.query.include_deleted === 'true' || req.query.include_deleted === '1',
    categoryId: req.query.category_id || null,
    status: req.query.status || null,
    q: req.query.q || null,
    limit: req.query.limit,
    offset: req.query.offset,
  });
  res.json({ success: true, data: data.runs, total: data.total, limit: data.limit, offset: data.offset });
}));

// Get a specific run with logs
router.get('/runs/:runId', wrap((req, res) => {
  const run = getRunWithLogs(req.params.runId);
  if (!run) return res.status(404).json({ success: false, error: 'Run not found' });
  res.json({ success: true, data: run });
}));

// Rename / categorize (either field, or both).
router.patch('/runs/:runId', wrap((req, res) => {
  const { title, category_id: categoryId } = req.body || {};
  let updated = null;
  if (title !== undefined) updated = renameRun(req.params.runId, title, req.user);
  if (categoryId !== undefined) updated = setRunCategory(req.params.runId, categoryId, req.user);
  if (!updated) {
    return res.status(400).json({
      success: false, code: 'NOTHING_TO_UPDATE', error: 'Provide title and/or category_id',
    });
  }
  res.json({ success: true, data: updated });
}));

// Delete — soft by default; ?purge=true also removes the workspace directory.
router.delete('/runs/:runId', wrap((req, res) => {
  const purge = req.query.purge === 'true' || req.query.purge === '1';
  const result = deleteRun(req.params.runId, req.user, { purge });
  res.json({ success: true, data: result });
}));

// Restore a soft-deleted run.
router.post('/runs/:runId/restore', wrap((req, res) => {
  res.json({ success: true, data: restoreRun(req.params.runId, req.user) });
}));

// Hard delete (explicit, same as DELETE?purge=true).
router.delete('/runs/:runId/purge', wrap((req, res) => {
  res.json({ success: true, data: purgeRun(req.params.runId, req.user) });
}));

// ── categories ──────────────────────────────────────────────────────────

router.get('/categories', wrap((req, res) => {
  res.json({ success: true, data: listCategories(req.user) });
}));

router.post('/categories', wrap((req, res) => {
  res.status(201).json({ success: true, data: createCategory(req.body?.name, req.user) });
}));

router.patch('/categories/:id', wrap((req, res) => {
  res.json({ success: true, data: renameCategory(req.params.id, req.body?.name, req.user) });
}));

router.delete('/categories/:id', wrap((req, res) => {
  res.json({ success: true, data: deleteCategory(req.params.id, req.user) });
}));

export default router;
