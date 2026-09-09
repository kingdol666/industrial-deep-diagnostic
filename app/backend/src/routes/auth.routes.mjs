// Auth Routes — 注册 / 登录 / 会话信息 / API Token 管理
//
// 除 register / login 外，本路由组同样被 authGuard 保护（guard 白名单只放行前两者）。

import { Router } from 'express';
import {
  registerUser, loginUser, getUserById,
  createApiToken, listApiTokens, revokeApiToken, AuthError,
} from '../services/auth.service.mjs';

const router = Router();

function handle(res, fn) {
  try {
    const data = fn();
    res.json({ success: true, data });
  } catch (err) {
    if (err instanceof AuthError) {
      return res.status(err.status).json({ success: false, code: err.code, error: err.message });
    }
    return res.status(500).json({ success: false, code: 'AUTH_INTERNAL_ERROR', error: err.message });
  }
}

// 公开：注册（成功即自动登录，返回会话 token）
router.post('/register', (req, res) => {
  handle(res, () => registerUser(req.body || {}));
});

// 公开：登录
router.post('/login', (req, res) => {
  handle(res, () => loginUser(req.body || {}));
});

// 需认证：当前用户身份
router.get('/me', (req, res) => {
  handle(res, () => ({ user: getUserById(req.user.id), auth_type: req.auth_type, token_id: req.token_id }));
});

// 需认证：创建 API Token（明文仅返回一次）
router.post('/tokens', (req, res) => {
  handle(res, () => createApiToken(req.user, req.body || {}));
});

// 需认证：列出当前用户的 API Token（脱敏）
router.get('/tokens', (req, res) => {
  handle(res, () => listApiTokens(req.user));
});

// 需认证：吊销 API Token（仅属主或 admin）
router.delete('/tokens/:id', (req, res) => {
  handle(res, () => revokeApiToken(req.user, req.params.id));
});

export default router;
