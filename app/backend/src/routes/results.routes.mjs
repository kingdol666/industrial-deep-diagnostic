// Results Routes — console surface for the analysis results library.
//
//   GET   /api/results            → flat summary cards (filters + paging)
//   GET   /api/results/:resultId  → full detail (summary_json/metadata/report_md)
//   PATCH /api/results/:resultId  → description / tags / title / category_id
//
// The external surface (/api/external/v1/results*) delegates to the same
// service functions — one implementation, two mounts.
import { Router } from 'express';

import { listResults, getResultDetail, updateResult } from '../services/results-library.service.mjs';

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
