import { Router } from 'express';
import { searchForRun, getForRun, listRunRetrievals } from '../services/knowledge.service.mjs';
import logger from '../utils/logger.mjs';

const router = Router();
const handle = (fn) => (req, res) => {
  res.set('Cache-Control', 'no-store');
  try {
    res.json({ success: true, data: fn({ actor: req.user, run_id: req.params.runId }, req) });
  } catch (err) {
    const status = err.status || 500;
    if (status >= 500) logger.error(`Knowledge lookup failed: ${err.code || err.name}`, { context: 'Knowledge' });
    res.status(status).json({ success: false, code: status >= 500 ? 'KNOWLEDGE_UNAVAILABLE' : err.code,
      error: status >= 500 ? '知识服务暂不可用' : err.message });
  }
};

router.post('/runs/:runId/search', handle((scope, req) => searchForRun(scope, req.body)));
router.get('/runs/:runId/items/:refId', handle((scope, req) => getForRun(scope, req.params.refId)));
router.get('/runs/:runId/retrievals', handle(listRunRetrievals));

export default router;
