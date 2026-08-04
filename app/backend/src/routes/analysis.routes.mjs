import { Router } from 'express';
import { getRunChartData } from '../services/analysis.service.mjs';

const router = Router();

router.get('/chart-data/:runDirName([a-zA-Z0-9_-]+)', (req, res) => {
  try {
    const { runDirName } = req.params;
    const chartData = getRunChartData(runDirName);
    // Return 200 with null data when the run exists but has no chart artifacts.
    // Using 404 here caused browser console noise on every report open;
    // the frontend already handles null/empty gracefully (shows no charts).
    res.json({ success: true, data: chartData || null });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

export default router;
