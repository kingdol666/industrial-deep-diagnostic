// Experience Routes — thin HTTP handlers（业务逻辑在 experience.service.mjs）
//
// Workstream D 契约（AgentWorkShop idd-closedloop-bridge / IDD_ROUTES）：
//   POST /api/experience/actions          批量动作摄取（≤100，schema 400，幂等）
//   GET  /api/experience/actions/:id/status
//   GET  /api/experience/attribution/:jobId
//   GET|POST /api/experience/recommend    fault_signature → recommendation
//   POST /api/experience/feedback         佐证/反证回填
//
// recommend 同时暴露 GET（fault_signature 以 query JSON 串传）与 POST（插件
// experience_recommend 的 payload 形状），路由路径保持不变。

import { Router } from 'express';
import {
  ingestActions, actionStatus, attributionView, recommend, feedback, libraryInfo,
} from '../services/experience.service.mjs';

const router = Router();

// 批量动作摄取（异步归因 job）
router.post('/actions', (req, res) => {
  try {
    const data = ingestActions(req.body ?? {});
    res.json({ success: true, data });
  } catch (err) {
    res.status(err.status || 500).json({ success: false, error: err.message });
  }
});

// 按动作 id 查归因 job 状态
router.get('/actions/:id/status', (req, res) => {
  const view = actionStatus(req.params.id);
  if (!view) return res.status(404).json({ success: false, error: 'action_log_id not found' });
  res.json({ success: true, data: view });
});

// 归因 job 视图（完成时携带 attribution 报告原文）
router.get('/attribution/:jobId', (req, res) => {
  const view = attributionView(req.params.jobId);
  if (!view) return res.status(404).json({ success: false, error: 'attribution job not found' });
  res.json({ success: true, data: view });
});

// 故障签名 → playbook 检索（命中 / 四级降级链）
async function recommendHandler(req, res) {
  try {
    let faultSignature = req.body?.fault_signature ?? null;
    let topK = req.body?.top_k;
    if (!faultSignature && req.query.fault_signature) {
      try { faultSignature = JSON.parse(String(req.query.fault_signature)); } catch {
        return res.status(400).json({ success: false, error: 'fault_signature query must be JSON' });
      }
    }
    if (topK === undefined && req.query.top_k) topK = Number(req.query.top_k);
    const data = await recommend({ fault_signature: faultSignature, top_k: topK });
    res.json({ success: true, data });
  } catch (err) {
    res.status(err.status || 500).json({ success: false, error: err.message });
  }
}
router.post('/recommend', recommendHandler);
router.get('/recommend', recommendHandler);

// 经验反馈（effective/ineffective/harmful/confirmed → 佐证/反证计数）
router.post('/feedback', async (req, res) => {
  try {
    const data = await feedback(req.body ?? {});
    res.json({ success: true, data });
  } catch (err) {
    res.status(err.status || 500).json({ success: false, error: err.message });
  }
});

// 运维/测试：经验库位置与条目数
router.get('/library', (_req, res) => {
  res.json({ success: true, data: libraryInfo() });
});

export default router;
