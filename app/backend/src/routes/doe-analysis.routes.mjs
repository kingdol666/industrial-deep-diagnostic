// DOE/工况分析 routes — 分析中心「工况DOE分析」模式的后端面。
import { Router } from 'express';
import {
  submitDoeAnalysis, doeTaskView, listDoeRuns, getDoeRun, getTaskLog, doeTasks,
} from '../services/doe-analysis.service.mjs';
import { streamTaskSSE } from '../services/closedloop.util.mjs';

const router = Router();

// 异步提交：POST /api/doe-analysis/tasks { data_path, time_col?, context?, scene? }
router.post('/tasks', (req, res) => {
  try {
    const created = submitDoeAnalysis(req.body ?? {});
    res.json({ success: true, data: created });
  } catch (err) {
    res.status(err.status || 500).json({ success: false, error: err.message });
  }
});

// 任务视图：GET /api/doe-analysis/tasks/:taskId
router.get('/tasks/:taskId', (req, res) => {
  const view = doeTaskView(req.params.taskId);
  if (!view) return res.status(404).json({ success: false, error: 'Task not found' });
  res.json({ success: true, data: view });
});

// 实时日志流：GET /api/doe-analysis/tasks/:taskId/stream（SSE：log/status/done）
router.get('/tasks/:taskId/stream', (req, res) => {
  streamTaskSSE(req, res, {
    taskId: req.params.taskId,
    getTask: (id) => doeTasks.get(id),
    getLog: (id) => getTaskLog(id),
  });
});

// 历史列表：GET /api/doe-analysis/runs
router.get('/runs', (_req, res) => {
  res.json({ success: true, data: listDoeRuns() });
});

// 单份全量产物：GET /api/doe-analysis/runs/:taskId
router.get('/runs/:taskId', (req, res) => {
  const found = getDoeRun(req.params.taskId);
  if (!found) return res.status(404).json({ success: false, error: 'Run not found' });
  res.json({ success: true, data: found });
});

export default router;
