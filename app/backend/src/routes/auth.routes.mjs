// Auth Routes — 注册 / 登录 / 登出 / 会话信息 / API Token 管理
//
// 除 register / login 外，本路由组同样被 authGuard 保护（guard 白名单只放行前两者）。
//
// 会话 Cookie（P0-6）：POST /login（以及同样自动登录的 POST /register）在返回体
// 不变的前提下额外下发 HttpOnly 会话 Cookie `idd_session`；POST /logout 清除它。
// 浏览器随后可凭 Cookie 调用全部 /api/*（CSRF 同源守卫见 auth.middleware.mjs）。

import { Router } from 'express';
import {
  registerUser, loginUser, getUserById,
  createApiToken, listApiTokens, revokeApiToken, AuthError,
} from '../services/auth.service.mjs';
import { buildSessionCookie, buildClearedSessionCookie } from '../middleware/auth.middleware.mjs';
import logger from '../utils/logger.mjs';
import { rateLimit, rateLimitKeyByIp } from '../middleware/rateLimit.mjs';
import { config } from '../../../../config/loader.mjs';

const router = Router();

// 登录限流（P0-6）：默认 5 次/分钟/IP，config.security.login_rate_limit 可调。
const loginLimitCfg = config.security?.login_rate_limit || {};
export const loginRateLimiter = rateLimit({
  windowMs: Number(loginLimitCfg.window_ms ?? loginLimitCfg.windowMs ?? 60_000),
  max: Number(loginLimitCfg.max ?? 5),
  keyFn: rateLimitKeyByIp,
  onLimit: (req, res, info) => {
    // 只做可观测性；响应交给通用 429（Retry-After 已由 limiter 设置）。
    res.setHeader('X-RateLimit-Limit', String(info.limit));
    return false;
  },
});

function handle(res, fn) {
  try {
    const data = fn();
    res.json({ success: true, data });
  } catch (err) {
    if (err instanceof AuthError) {
      return res.status(err.status).json({ success: false, code: err.code, error: err.message });
    }
    // B4: 未预期的内部错误只回稳定 code；真实错误进日志。
    logger.error(`[auth] ${err?.stack || err?.message || err}`, { context: 'Auth' });
    return res.status(500).json({ success: false, code: 'AUTH_INTERNAL_ERROR', error: '认证服务内部错误，请查看后端日志后重试' });
  }
}

/** 在响应体完全不变的前提下补上会话 Cookie。 */
function withSessionCookie(res, result) {
  if (result && result.session_token) {
    res.setHeader('Set-Cookie', buildSessionCookie(result.session_token, result.expires_in));
  }
  return result;
}

// 公开：注册（成功即自动登录，返回会话 token + 下发会话 Cookie）
router.post('/register', (req, res) => {
  handle(res, () => withSessionCookie(res, registerUser(req.body || {})));
});

// 公开：登录（限流 5 次/分钟/IP；成功返回会话 token + 下发会话 Cookie）
router.post('/login', loginRateLimiter, (req, res) => {
  handle(res, () => withSessionCookie(res, loginUser(req.body || {})));
});

// 需认证：登出（无状态 JWT 无法在服务端吊销，这里清除浏览器 Cookie）
router.post('/logout', (req, res) => {
  res.setHeader('Set-Cookie', buildClearedSessionCookie());
  res.json({ success: true, data: { ok: true, logged_out: true } });
});

// 需认证：当前用户身份（Bearer / Cookie 均可）
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
