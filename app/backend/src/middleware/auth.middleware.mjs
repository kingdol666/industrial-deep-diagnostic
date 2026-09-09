// Auth Middleware — 全局 API 鉴权拦截
//
// 使用方式（index.mjs）：
//   app.use(authGuard);            // 挂载在所有 /api 路由之前
//
// 白名单：POST /api/auth/register、POST /api/auth/login、GET /api/health
// 其余 /api/* 一律要求 Authorization: Bearer <token>（登录会话 JWT 或 API Token）

import { authenticate, AuthError } from '../services/auth.service.mjs';

// 注意：authGuard 挂载在 app.use('/api', ...) 上，req.path 为去掉 /api 前缀的相对路径
const PUBLIC_EXACT = new Set(['/health']);
const PUBLIC_PREFIXES = ['/auth/login', '/auth/register'];

export function isPublicPath(path) {
  if (PUBLIC_EXACT.has(path)) return true;
  return PUBLIC_PREFIXES.some((p) => path === p || path.startsWith(`${p}/`));
}

export function requireAuth(req, res, next) {
  try {
    const { user, auth_type, token_id } = authenticate(req);
    req.user = user;
    req.auth_type = auth_type;
    req.token_id = token_id ?? null;
    next();
  } catch (err) {
    if (err instanceof AuthError) {
      return res.status(err.status).json({ success: false, code: err.code, error: err.message });
    }
    return res.status(500).json({ success: false, code: 'AUTH_INTERNAL_ERROR', error: err.message });
  }
}

export function authGuard(req, res, next) {
  if (isPublicPath(req.path)) return next();
  return requireAuth(req, res, next);
}

// 角色权限门禁（权限系统扩展点）
export function requireRole(...roles) {
  return (req, res, next) => {
    if (!req.user) {
      return res.status(401).json({ success: false, code: 'AUTH_REQUIRED', error: '未认证' });
    }
    if (!roles.includes(req.user.role)) {
      return res.status(403).json({ success: false, code: 'FORBIDDEN', error: `需要角色: ${roles.join(' 或 ')}` });
    }
    next();
  };
}
