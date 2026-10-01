// Sentinel Routes — thin HTTP handlers（业务逻辑在 sentinel.service.mjs）
//
// Workstream D 契约（AgentWorkShop idd-closedloop-bridge / IDD_ROUTES）：
//   POST /api/sentinel/tasks      watch 批筛异步任务（提交即返 task_id）
//   GET  /api/sentinel/tasks/:id  任务状态/结果（alert 摘要 + 产物路径）
//   POST /api/sentinel/screen     fast-screen 同步（≤15s；exit_code + alert 摘要）
//   POST /api/sentinel/baseline   基线构建异步任务（build_baseline.py）

import { Router } from 'express';
import {
  screen, submitWatch, watchTaskView, anyTaskView, submitBaseline, listBaselines,
} from '../services/sentinel.service.mjs';

const router = Router();

// 整窗批筛（异步）：sentinel.py watch
router.post('/tasks', (req, res) => {
  try {
    const created = submitWatch(req.body ?? {});
    res.json({ success: true, data: created });
  } catch (err) {
    res.status(err.status || 500).json({ success: false, error: err.message });
  }
});

// 任务视图：watch / baseline 任务共用 GET /tasks/:id（插件 sentinel_status 语义）
router.get('/tasks/:taskId', (req, res) => {
  const view = anyTaskView(req.params.taskId) ?? watchTaskView(req.params.taskId);
  if (!view) return res.status(404).json({ success: false, error: 'Task not found' });
  res.json({ success: true, data: view });
});

// 增量快筛（同步 ≤15s）：sentinel_fast.py；无基线 → exit_code=2（200 信封）
router.post('/screen', async (req, res) => {
  try {
    const data = await screen(req.body ?? {});
    res.json({ success: true, data });
  } catch (err) {
    res.status(err.status || 500).json({ success: false, error: err.message });
  }
});

// 基线构建（异步）：build_baseline.py；成功后按 line 登记
router.post('/baseline', (req, res) => {
  try {
    const created = submitBaseline(req.body ?? {});
    res.json({ success: true, data: created });
  } catch (err) {
    res.status(err.status || 500).json({ success: false, error: err.message });
  }
});

// 运维/测试：基线登记表
router.get('/baselines', (_req, res) => {
  res.json({ success: true, data: listBaselines() });
});

export default router;
