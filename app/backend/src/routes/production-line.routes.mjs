// Production-line identity and membership API.
//
// A line's UUID is the authorization key. Names and aliases are display-only;
// no route accepts a name/alias as a substitute for line_id.
import { Router } from 'express';
import {
  createLine, listLines, updateLine,
  listLineMembers, setLineMember, removeLineMember,
  bindLegacyRun, listLegacyRuns, listLineRunBindings,
} from '../services/production-line.service.mjs';
import logger from '../utils/logger.mjs';

const router = Router();

function sendError(res, err) {
  const status = Number(err?.status) || 500;
  if (status >= 500) {
    logger.error(`[production-line] ${err?.stack || err?.message || err}`, { context: 'ProductionLine' });
    return res.status(status).json({
      success: false,
      code: err?.code || 'PRODUCTION_LINE_ERROR',
      error: '产线服务内部错误，请查看后端日志后重试',
    });
  }
  return res.status(status).json({
    success: false,
    code: err?.code || 'PRODUCTION_LINE_ERROR',
    error: err?.message || '请求无效',
  });
}

const wrap = (fn) => (req, res) => {
  try { return fn(req, res); } catch (err) { return sendError(res, err); }
};

router.post('/', wrap((req, res) => {
  res.status(201).json({ success: true, data: createLine(req.user, req.body || {}) });
}));

router.get('/', wrap((req, res) => {
  res.json({ success: true, data: listLines(req.user) });
}));

router.patch('/:lineId', wrap((req, res) => {
  res.json({ success: true, data: updateLine(req.user, req.params.lineId, req.body || {}) });
}));

router.get('/:lineId/members', wrap((req, res) => {
  res.json({ success: true, data: listLineMembers(req.user, req.params.lineId) });
}));

router.put('/:lineId/members/:userId', wrap((req, res) => {
  res.json({
    success: true,
    data: setLineMember(req.user, req.params.lineId, req.params.userId, req.body?.role),
  });
}));

router.delete('/:lineId/members/:userId', wrap((req, res) => {
  res.json({
    success: true,
    data: removeLineMember(req.user, req.params.lineId, req.params.userId),
  });
}));

router.get('/legacy-runs', wrap((req, res) => {
  res.json({ success: true, data: listLegacyRuns(req.user, {
    limit: req.query.limit,
    offset: req.query.offset,
  }) });
}));

router.post('/:lineId/legacy-runs/:runId/bind', wrap((req, res) => {
  res.json({ success: true, data: bindLegacyRun(req.user, req.params.lineId, req.params.runId) });
}));

router.get('/:lineId/legacy-bindings', wrap((req, res) => {
  const data = listLineRunBindings(req.user, req.params.lineId, {
    limit: req.query.limit,
    offset: req.query.offset,
  });
  res.json({ success: true, data });
}));

export default router;
