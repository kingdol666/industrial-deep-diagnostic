import { Router } from 'express';
import { getRunChartData } from '../services/analysis.service.mjs';

const router = Router();

router.get('/chart-data/:runDirName', (req, res) => {
  try {
    const { runDirName } = req.params;
    if (runDirName.includes('..') || runDirName.includes('/')) {
      return res.status(400).json({ success: false, error: 'Invalid run directory name' });
    }
    const chartData = getRunChartData(runDirName);
    if (!chartData) {
      return res.status(404).json({ success: false, error: 'No chart data available for this run' });
    }
    res.json({ success: true, data: chartData });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

export default router;
