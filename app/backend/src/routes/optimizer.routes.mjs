// Optimizer Routes — thin HTTP handlers（业务逻辑在 optimizer.service.mjs）
//
// Workstream D 契约（AgentWorkShop idd-closedloop-bridge / IDD_ROUTES）：
//   POST /api/optimizer/campaign          创建 campaign（objective，O-G1 校验）
//   POST /api/optimizer/round             action=design|ingest
//   GET  /api/optimizer/state?campaign_id=
//   POST /api/optimizer/pause|resume      控制面（paused 为状态机合法 phase）

import { Router } from 'express';
import {
  createCampaign, round, state, pause, resume, listCampaigns,
} from '../services/optimizer.service.mjs';

const router = Router();

// 创建 campaign（optimizer.py init；O-G1 失败 → 400 + 逐条错误）
router.post('/campaign', async (req, res) => {
  try {
    const data = await createCampaign(req.body ?? {});
    res.json({ success: true, data });
  } catch (err) {
    res.status(err.status || 500).json({ success: false, error: err.message });
  }
});

// 轮次操作：design（取布点）/ ingest（回收 trial_result + 状态转移）
router.post('/round', async (req, res) => {
  try {
    const data = await round(req.body ?? {});
    res.json({ success: true, data });
  } catch (err) {
    res.status(err.status || 500).json({ success: false, error: err.message });
  }
});

// campaign 状态（phase/incumbent/预算/信念/轮次历史）
router.get('/state', (req, res) => {
  try {
    const data = state({ campaign_id: req.query.campaign_id });
    res.json({ success: true, data });
  } catch (err) {
    res.status(err.status || 500).json({ success: false, error: err.message });
  }
});

// 暂停 / 恢复（控制面）
router.post('/pause', (req, res) => {
  try {
    res.json({ success: true, data: pause(req.body ?? {}) });
  } catch (err) {
    res.status(err.status || 500).json({ success: false, error: err.message });
  }
});

router.post('/resume', (req, res) => {
  try {
    res.json({ success: true, data: resume(req.body ?? {}) });
  } catch (err) {
    res.status(err.status || 500).json({ success: false, error: err.message });
  }
});

// 运维/测试：全部 campaign
router.get('/campaigns', (_req, res) => {
  res.json({ success: true, data: listCampaigns() });
});

export default router;
