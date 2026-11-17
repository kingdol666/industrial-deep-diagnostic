// Auth Middleware — 全局 API 鉴权拦截 + 会话 Cookie + CSRF 同源守卫
//
// 使用方式（index.mjs）：
//   app.use('/api', authGuard);    // 挂载在所有 /api 路由之前
//
// 白名单：POST /api/auth/register、POST /api/auth/login、GET /api/health
// 其余 /api/* 一律要求凭据，凭据来源（二选一，header 优先）：
//   1) Authorization: Bearer <登录会话 JWT 或 idd_ API Token> / X-Api-Token / ?token=
//   2) Cookie `idd_session=<登录会话 JWT>`（浏览器同源会话；API Token 不放行 Cookie）
// 判定结果写入 req.auth_source（'header' | 'cookie'），供 CSRF 守卫与审计使用。
//
// CSRF：Cookie 鉴权是非浏览器无法伪造的“自动携带凭据”，因此状态变更方法
// （POST/PUT/PATCH/DELETE）在 cookie 来源下要求 Origin 或 Referer 与 Host 同源
// （或命中 config.server.cors_origins 白名单，兼顾 Vite 代理开发态）；否则
// 403 CSRF_BLOCKED。Bearer/API Token 是显式凭据，不在 CSRF 威胁模型内，豁免。
// 豁免路径：/auth/login、/auth/register（尚无会话）、/auth/logout（仅销毁调用者
// 自身凭据，跨站注销只是骚扰而非提权）。
//
// 说明：authGuard 内部即完成 requireAuth +（cookie 来源的）CSRF 校验，因此不
// 需要在 index.mjs 追加挂载；csrfGuard 作为独立导出，供将来显式编排使用。

import { authenticate, AuthError, getUserById } from '../services/auth.service.mjs';
import { resolveAllowedOrigins } from '../transport/cors.mjs';
import { config } from '../../../../config/loader.mjs';

// 注意：authGuard 挂载在 app.use('/api', ...) 上，req.path 为去掉 /api 前缀的相对路径
const PUBLIC_EXACT = new Set(['/health']);
const PUBLIC_PREFIXES = ['/auth/login', '/auth/register'];

/** CSRF 豁免路径（同上，未挂 /api 前缀的相对路径）。 */
const CSRF_EXEMPT_PATHS = new Set(['/auth/login', '/auth/register', '/auth/logout']);

const SAFE_METHODS = new Set(['GET', 'HEAD', 'OPTIONS']);

/** 浏览器会话 Cookie 名（POST /api/auth/login 下发）。 */
export const SESSION_COOKIE_NAME = 'idd_session';

/** req.auth_source 取值。 */
export const AUTH_SOURCE_HEADER = 'header';
export const AUTH_SOURCE_COOKIE = 'cookie';

export function isPublicPath(path) {
  if (PUBLIC_EXACT.has(path)) return true;
  return PUBLIC_PREFIXES.some((p) => path === p || path.startsWith(`${p}/`));
}

// ─── Cookie helpers (zero-dependency) ───────────────────────────────────────

/** Parse a `Cookie:` header into `{ name: value }`. Tolerates quoted values. */
export function parseCookies(header) {
  const out = {};
  if (!header || typeof header !== 'string') return out;
  for (const part of header.split(';')) {
    const eq = part.indexOf('=');
    if (eq < 0) continue;
    const name = part.slice(0, eq).trim();
    if (!name) continue;
    let value = part.slice(eq + 1).trim();
    if (value.length >= 2 && value.startsWith('"') && value.endsWith('"')) {
      value = value.slice(1, -1);
    }
    try {
      value = decodeURIComponent(value);
    } catch { /* keep raw */ }
    out[name] = value;
  }
  return out;
}

/**
 * Session-JWT shape test. The cookie channel carries ONLY login-session JWTs:
 * an `idd_…` API token placed in a cookie (or any non-JWT string) is ignored —
 * API tokens stay header-only.
 */
export function looksLikeSessionJwt(token) {
  if (typeof token !== 'string' || token.length === 0) return false;
  if (token.startsWith('idd_')) return false;
  return token.split('.').length === 3;
}

/** The session JWT carried by the `idd_session` cookie, or null. */
export function sessionCookieToken(req) {
  const fromParsed = req?.cookies?.[SESSION_COOKIE_NAME];
  const raw = typeof fromParsed === 'string' && fromParsed
    ? fromParsed
    : parseCookies(req?.headers?.cookie)[SESSION_COOKIE_NAME];
  return looksLikeSessionJwt(raw) ? raw : null;
}

function cookieAttributes() {
  const attrs = ['HttpOnly', 'SameSite=Strict', 'Path=/'];
  // Secure 只在显式配置或 HTTPS 部署时开启：本地 http 调试下带上会让浏览器丢弃 Cookie。
  if (process.env.COOKIE_SECURE === '1') attrs.push('Secure');
  return attrs;
}

/** `Set-Cookie` value issuing the session cookie. */
export function buildSessionCookie(token, maxAgeSeconds) {
  const maxAge = Math.max(0, Math.floor(Number(maxAgeSeconds) || 0));
  return [`${SESSION_COOKIE_NAME}=${token}`, ...cookieAttributes(), `Max-Age=${maxAge}`].join('; ');
}

/** `Set-Cookie` value expiring the session cookie (logout). */
export function buildClearedSessionCookie() {
  return [`${SESSION_COOKIE_NAME}=`, ...cookieAttributes(), 'Max-Age=0'].join('; ');
}

// ─── CSRF: cookie 凭据要求同源 Origin/Referer ───────────────────────────────

function hostMatches(urlString, host) {
  if (!urlString || !host) return false;
  try {
    return new URL(urlString).host === host;
  } catch {
    return false;
  }
}

function trustedOrigin(urlString) {
  if (!urlString) return false;
  let origin;
  try {
    origin = new URL(urlString).origin;
  } catch {
    return false;
  }
  // 运维配置的浏览器来源（server.cors_origins / CORS_ORIGINS env）：开发态
  // Vite 代理（changeOrigin: true）下 Origin/Host 不同源，但这些来源本来就是
  // 本应用自身，纳入信任边界；攻击者站点不在白名单内，CSRF 防护不受影响。
  return resolveAllowedOrigins({ env: process.env, config }).includes(origin);
}

/**
 * Decide whether a state-changing request authenticated by COOKIE may proceed.
 * @returns {null|{code:string,error:string}} null = allowed
 */
export function checkCsrf(req) {
  const method = String(req?.method || 'GET').toUpperCase();
  if (SAFE_METHODS.has(method)) return null;
  if (CSRF_EXEMPT_PATHS.has(req?.path || '')) return null;

  const host = req?.headers?.host || '';
  const origin = req?.headers?.origin;
  const referer = req?.headers?.referer;

  if (origin && origin !== 'null') {
    if (hostMatches(origin, host) || trustedOrigin(origin)) return null;
    return { code: 'CSRF_BLOCKED', error: '跨站请求被拒绝：Origin 与请求 Host 不一致' };
  }
  if (!origin && referer) {
    if (hostMatches(referer, host) || trustedOrigin(referer)) return null;
    return { code: 'CSRF_BLOCKED', error: '跨站请求被拒绝：Referer 与请求 Host 不一致' };
  }
  return { code: 'CSRF_BLOCKED', error: '跨站请求被拒绝：Cookie 鉴权的状态变更请求缺少 Origin/Referer' };
}

/**
 * Standalone CSRF middleware — mount AFTER auth (needs `req.auth_source`).
 * authGuard already performs this check inline; exported for explicit chains.
 */
export function csrfGuard(req, res, next) {
  if (req.auth_source !== AUTH_SOURCE_COOKIE) return next();
  const verdict = checkCsrf(req);
  if (verdict) {
    return res.status(403).json({ success: false, code: verdict.code, error: verdict.error });
  }
  next();
}

// ─── Authentication ─────────────────────────────────────────────────────────

function hasHeaderCredential(req) {
  const header = req?.headers?.authorization;
  if (header && /^Bearer\s+/i.test(header)) return true;
  if (req?.headers?.['x-api-token']) return true;
  if (req?.query?.token) return true;
  return false;
}

/** 保证 req.user 至少携带 { id, username, role }。 */
function ensureUserShape(user) {
  if (!user) return user;
  if (user.id !== undefined && user.username !== undefined && user.role !== undefined) return user;
  const fresh = getUserById(user.id);
  return fresh || user;
}

export function requireAuth(req, res, next) {
  try {
    let authSource = AUTH_SOURCE_HEADER;
    let credentialReq = req;

    if (!hasHeaderCredential(req)) {
      const cookieToken = sessionCookieToken(req);
      if (!cookieToken) {
        // 没有 header 凭据也没有会话 Cookie → 让 authenticate 抛标准 AUTH_REQUIRED
        authenticate(req);
      }
      authSource = AUTH_SOURCE_COOKIE;
      credentialReq = { headers: { authorization: `Bearer ${cookieToken}` } };
    }

    const { user, auth_type, token_id } = authenticate(credentialReq);
    req.user = ensureUserShape(user);
    req.auth_type = auth_type;
    req.token_id = token_id ?? null;
    req.auth_source = authSource;

    if (authSource === AUTH_SOURCE_COOKIE) {
      const verdict = checkCsrf(req);
      if (verdict) {
        return res.status(403).json({ success: false, code: verdict.code, error: verdict.error });
      }
    }
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
