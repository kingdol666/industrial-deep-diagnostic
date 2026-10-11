// Line Stability Report routes — 产线运行稳定性报告（闭环协同报告面）。
import { Router } from 'express';
import {
  submitReport, reportTaskView, listReports, getReport, getTaskLog, reportTasks,
} from '../services/line-report.service.mjs';
import { streamTaskSSE } from '../services/closedloop.util.mjs';

const router = Router();

// 异步提交：POST /api/line-report/tasks { data_path, line_id, time_col, ... }
router.post('/tasks', (req, res) => {
  try {
    const created = submitReport(req.body ?? {});
    res.json({ success: true, data: created });
  } catch (err) {
    res.status(err.status || 500).json({ success: false, error: err.message });
  }
});

// 任务视图：GET /api/line-report/tasks/:taskId
router.get('/tasks/:taskId', (req, res) => {
  const view = reportTaskView(req.params.taskId);
  if (!view) return res.status(404).json({ success: false, error: 'Task not found' });
  res.json({ success: true, data: view });
});

// 实时日志流：GET /api/line-report/tasks/:taskId/stream（SSE：log/status/done）
router.get('/tasks/:taskId/stream', (req, res) => {
  streamTaskSSE(req, res, {
    taskId: req.params.taskId,
    getTask: (id) => reportTasks.get(id),
    getLog: (id) => getTaskLog(id),
  });
});

// 历史报告列表：GET /api/line-report/runs
router.get('/runs', (_req, res) => {
  res.json({ success: true, data: listReports() });
});

// 单份完整报告：GET /api/line-report/runs/:taskId
router.get('/runs/:taskId', (req, res) => {
  const found = getReport(req.params.taskId);
  if (!found) return res.status(404).json({ success: false, error: 'Report not found' });
  res.json({ success: true, data: found });
});

export default router;
