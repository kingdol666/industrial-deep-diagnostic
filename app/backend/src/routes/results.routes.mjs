// Results Routes — console surface for the analysis results library.
//
//   GET   /api/results                       → flat summary cards (filters + paging)
//   GET   /api/results/:resultId             → full detail (summary_json/metadata/report_md)
//   PATCH /api/results/:resultId             → description / tags / title / category_id
//   GET   /api/results/categories            → categories with per-caller result counts
//   POST   /api/results/categories           → create a category
//   PATCH  /api/results/categories/:id       → rename
//   DELETE /api/results/categories/:id       → delete (clears result refs)
//   GET   /api/results/categories/:id/results→ every result in a category, description view
//
// The external surface (/api/external/v1/results*) delegates to the same
// service functions — one implementation, two mounts. Category mutations
// delegate to the history service (per-user isolation, single truth).
import { Router } from 'express';

import {
  listResults, getResultDetail, updateResult,
  listResultCategories, createResultCategory, renameResultCategory,
  deleteResultCategory, listResultsByCategory,
} from '../services/results-library.service.mjs';

const router = Router();

function sendError(res, err) {
  const status = err.status || 500;
  res.status(status).json({ success: false, code: err.code || 'RESULTS_ERROR', error: err.message });
}

const wrap = (fn) => (req, res) => {
  try {
    fn(req, res);
  } catch (err) {
    sendError(res, err);
  }
};

router.get('/', wrap((req, res) => {
  const data = listResults(req.user, req.query);
  res.json({ success: true, data: data.results, total: data.total, limit: data.limit, offset: data.offset, brief: data.brief });
}));

// ── categories on the results surface ─────────────────────────────────────
// ROUTE ORDER: /categories* must be declared BEFORE /:resultId, otherwise
// "categories" is captured as a result id.
router.get('/categories', wrap((req, res) => {
  res.json({ success: true, data: listResultCategories(req.user) });
}));

router.post('/categories', wrap((req, res) => {
  res.status(201).json({ success: true, data: createResultCategory(req.body?.name, req.user) });
}));

router.patch('/categories/:id', wrap((req, res) => {
  res.json({ success: true, data: renameResultCategory(req.params.id, req.body?.name, req.user) });
}));

router.delete('/categories/:id', wrap((req, res) => {
  res.json({ success: true, data: deleteResultCategory(req.params.id, req.user) });
}));

// The category-centric description view: all results of one category.
router.get('/categories/:id/results', wrap((req, res) => {
  const view = listResultsByCategory(req.params.id, req.user, {
    limit: req.query.limit,
    offset: req.query.offset,
  });
  res.json({ success: true, data: view });
}));

router.get('/:resultId', wrap((req, res) => {
  const includeMd = req.query.include_md !== 'false' && req.query.include_md !== '0';
  const detail = getResultDetail(req.params.resultId, { user: req.user, includeMd });
  res.json({ success: true, data: detail });
}));

router.patch('/:resultId', wrap((req, res) => {
  const detail = updateResult(req.params.resultId, req.body || {}, req.user);
  res.json({ success: true, data: detail });
}));

export default router;
