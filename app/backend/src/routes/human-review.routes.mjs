import { Router } from 'express';
import { getReview, listReviewHistory, updateReview } from '../services/human-review.service.mjs';
import logger from '../utils/logger.mjs';

const router = Router();
const handle = (fn) => (req, res) => {
  try {
    res.json({ success: true, ...fn(req) });
  } catch (err) {
    const status = err.status || 500;
    if (status >= 500) logger.error(err.stack || err.message, { context: 'HumanReview' });
    res.status(status).json({ success: false, code: err.code || 'REVIEW_ERROR',
      error: status >= 500 ? '人工复核服务异常，请查看后端日志' : err.message });
  }
};

router.get('/:resultId/review', handle((req) => ({ data: getReview(req.params.resultId, req.user) })));
router.get('/:resultId/review/history', handle((req) => {
  const { revisions, next } = listReviewHistory(req.params.resultId, req.user, req.query.before);
  return { data: revisions, next_before: next };
}));
router.patch('/:resultId/review', handle((req) => ({
  data: updateReview(req.params.resultId, req.body, req.user, req.auth_type),
})));

export default router;
