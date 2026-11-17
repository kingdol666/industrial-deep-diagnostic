import { Router } from 'express';
import { getRunChartData } from '../services/analysis.service.mjs';
import logger from '../utils/logger.mjs';

const router = Router();

router.get('/chart-data/:runDirName([a-zA-Z0-9_-]+)', (req, res) => {
  try {
    const { runDirName } = req.params;
    // Viewer-scoped: a run dir owned by someone else (or an unowned one) reads
    // as null, exactly like a missing directory.
    const chartData = getRunChartData(runDirName, req.user);
    // Return 200 with null data when the run exists but has no chart artifacts.
    // Using 404 here caused browser console noise on every report open;
    // the frontend already handles null/empty gracefully (shows no charts).
    res.json({ success: true, data: chartData || null });
  } catch (err) {
    // B4: generic 500 body; the real error goes to the log.
    logger.error(`[analysis] ${err?.stack || err?.message || err}`, { context: 'Analysis' });
    res.status(500).json({ success: false, code: 'ANALYSIS_INTERNAL_ERROR', error: '分析服务内部错误，请查看后端日志后重试' });
  }
});

export default router;
