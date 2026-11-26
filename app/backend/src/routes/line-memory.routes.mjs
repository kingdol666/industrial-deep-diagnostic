// Line Memory Routes — 跨 run 产线记忆 / 本体提案 API
//
// 挂载于 /api/line-memory（authGuard 已由 /api 前缀统一拦截）。
// 端点：
//   GET  /lines                                   产线索引（stats + latest_state）
//   GET  /lines/:key                              产线详情（consensus entries + proposals）
//   GET  /lines/:key/findings?limit&offset&subject&claim_type   原始 findings（分页）
//   GET  /lines/:key/ontology                     本体版本链（含各别名 scene）
//   POST /lines/:key/refute                       人工反证 {entry_key, reason}
//   POST /lines/:key/unrefute                     撤销人工反证 {entry_key}
//   POST /lines/:key/merge                        合并产线 {into}
//   POST /lines/:key/consolidate                  强制重算（运维）
//   GET  /proposals?status&line_key               提案台账
//   POST /proposals/:id/approve|reject            人工批准/拒绝（removal / 挂起修正）
import { Router } from 'express';
import { listReviewedMemory } from '../services/human-review.service.mjs';

import {
  listLines, getLineDetail, listLineFindings, ontologyVersionsForLine,
  refuteEntry, mergeLine, consolidateLine, decideProposalById,
} from '../services/line-memory.service.mjs';
import { readProposalLog } from '../../../../.claude/shared/scripts/line_memory.mjs';

const router = Router();

function wrap(handler) {
  return (req, res) => {
    try {
      handler(req, res);
    } catch (err) {
      const status = err.status || 500;
      res.status(status).json({
        success: false,
        code: err.code || 'LINE_MEMORY_ERROR',
        error: err.message,
      });
    }
  };
}

// Mutating endpoints (refute / unrefute / merge / consolidate / proposal
// approve-reject) rewrite CROSS-TENANT shared memory — admin-only, same rule
// as the other destructive management surfaces. Auth-gated GETs stay open to
// every authenticated user.
import { adminOnly } from '../services/tenancy.mjs';

router.get('/reviews', wrap((req, res) => {
  res.json({ success: true, data: listReviewedMemory(req.user, req.query) });
}));

router.get('/lines', wrap((req, res) => {
  res.json({ success: true, data: listLines() });
}));

router.get('/lines/:key', wrap((req, res) => {
  res.json({ success: true, data: getLineDetail(req.params.key) });
}));

router.get('/lines/:key/findings', wrap((req, res) => {
  const { limit, offset, subject, claim_type } = req.query;
  res.json({
    success: true,
    data: listLineFindings(req.params.key, { limit, offset, subject, claim_type }),
  });
}));

router.get('/lines/:key/ontology', wrap((req, res) => {
  res.json({ success: true, data: ontologyVersionsForLine(req.params.key) });
}));

router.post('/lines/:key/refute', adminOnly, wrap((req, res) => {
  const { entry_key, reason } = req.body || {};
  if (!entry_key) {
    return res.status(400).json({ success: false, code: 'ENTRY_REQUIRED', error: 'entry_key 必填' });
  }
  const consensus = refuteEntry(req.params.key, entry_key, { reason, status: 'refuted' });
  res.json({ success: true, data: { line_key: consensus.line_key, entry_key, status: 'refuted' } });
}));

router.post('/lines/:key/unrefute', adminOnly, wrap((req, res) => {
  const { entry_key } = req.body || {};
  if (!entry_key) {
    return res.status(400).json({ success: false, code: 'ENTRY_REQUIRED', error: 'entry_key 必填' });
  }
  const consensus = refuteEntry(req.params.key, entry_key, { status: 'active' });
  res.json({ success: true, data: { line_key: consensus.line_key, entry_key, status: 'active' } });
}));

router.post('/lines/:key/merge', adminOnly, wrap((req, res) => {
  const { into } = req.body || {};
  if (!into) {
    return res.status(400).json({ success: false, code: 'INTO_REQUIRED', error: 'into(目标 line_key) 必填' });
  }
  const result = mergeLine(req.params.key, into);
  res.json({ success: true, data: result });
}));

router.post('/lines/:key/consolidate', adminOnly, wrap((req, res) => {
  const consensus = consolidateLine(req.params.key);
  res.json({ success: true, data: { line_key: consensus.line_key, stats: consensus.stats } });
}));

router.get('/proposals', wrap((req, res) => {
  const { status, line_key, scene_key } = req.query;
  let rows = readProposalLog();
  if (status) rows = rows.filter((p) => p.status === status);
  if (line_key) rows = rows.filter((p) => p.line_key === line_key);
  if (scene_key) rows = rows.filter((p) => p.scene_key === scene_key);
  rows.sort((a, b) => String(b.created_at || '').localeCompare(String(a.created_at || '')));
  res.json({ success: true, data: rows });
}));

function decide(action) {
  return wrap((req, res) => {
    const record = decideProposalById(req.params.id, action, req.user?.username || 'console');
    res.json({ success: true, data: record });
  });
}

router.post('/proposals/:id/approve', adminOnly, decide('approve'));
router.post('/proposals/:id/reject', adminOnly, decide('reject'));

export default router;
