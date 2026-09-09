// Auth Service — 用户注册/登录 + API Token 管理的核心业务逻辑
//
// 设计规范：
// - 密码：scrypt (N=16384, r=8, p=1) + 每用户独立随机盐，timingSafeEqual 恒时比较
// - 登录会话：HS256 JWT（零第三方依赖），默认 24h 过期
// - API Token：`idd_` 前缀 + 256bit 熵，仅创建时返回一次明文；库中只存 SHA-256 哈希
// - 权限：role 字段（首个注册用户自动为 admin）；token 归属其创建者
// - JWT 密钥：优先 env AUTH_JWT_SECRET，否则生成并持久化到 data/.auth-jwt-secret

import crypto from 'crypto';
import { existsSync, readFileSync, writeFileSync } from 'fs';
import { join } from 'path';
import { stmts } from '../db/database.mjs';
import { PROJECT_ROOT } from '../../../../config/loader.mjs';
import logger from '../utils/logger.mjs';

const SCRYPT = { N: 16384, r: 8, p: 1, keylen: 64 };

// 与 index.mjs 的 API 鉴权开关保持一致（WS /ws 通道共用）
export function isAuthEnabled() {
  return process.env.AUTH_ENABLED !== '0';
}
const SESSION_TTL_HOURS = Number(process.env.AUTH_SESSION_TTL_HOURS || 24);
const TOKEN_DEFAULT_TTL_DAYS = 30;
const TOKEN_MAX_TTL_DAYS = 365;
const USERNAME_RE = /^[a-zA-Z0-9_-]{3,32}$/;
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

// ─── Errors ───

export class AuthError extends Error {
  constructor(status, code, message) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

// ─── JWT secret ───

let _secret = null;
function getJwtSecret() {
  if (_secret) return _secret;
  if (process.env.AUTH_JWT_SECRET) {
    _secret = process.env.AUTH_JWT_SECRET;
    return _secret;
  }
  const secretFile = join(PROJECT_ROOT, 'data', '.auth-jwt-secret');
  try {
    if (existsSync(secretFile)) {
      _secret = readFileSync(secretFile, 'utf-8').trim();
      if (_secret) return _secret;
    }
    _secret = crypto.randomBytes(48).toString('hex');
    writeFileSync(secretFile, _secret, { mode: 0o600 });
    logger.info('Generated new JWT secret (persisted to data/.auth-jwt-secret)', { context: 'Auth' });
    return _secret;
  } catch (err) {
    throw new AuthError(500, 'AUTH_SECRET_ERROR', `Cannot load/generate JWT secret: ${err.message}`);
  }
}

// ─── Password hashing ───

export function hashPassword(password) {
  const salt = crypto.randomBytes(16).toString('hex');
  const hash = crypto.scryptSync(password, salt, SCRYPT.keylen, { N: SCRYPT.N, r: SCRYPT.r, p: SCRYPT.p }).toString('hex');
  return `scrypt$${SCRYPT.N}$${SCRYPT.r}$${SCRYPT.p}$${salt}$${hash}`;
}

export function verifyPassword(password, stored) {
  try {
    const [alg, N, r, p, salt, hash] = String(stored).split('$');
    if (alg !== 'scrypt') return false;
    const candidate = crypto.scryptSync(password, salt, SCRYPT.keylen, { N: +N, r: +r, p: +p });
    const expected = Buffer.from(hash, 'hex');
    return candidate.length === expected.length && crypto.timingSafeEqual(candidate, expected);
  } catch {
    return false;
  }
}

// ─── JWT (HS256, zero-dependency) ───

function b64url(input) {
  return Buffer.from(input).toString('base64url');
}

export function signJwt(payload, ttlSeconds) {
  const header = b64url(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
  const now = Math.floor(Date.now() / 1000);
  const body = b64url(JSON.stringify({ ...payload, iat: now, exp: now + ttlSeconds }));
  const sig = crypto.createHmac('sha256', getJwtSecret()).update(`${header}.${body}`).digest('base64url');
  return `${header}.${body}.${sig}`;
}

export function verifyJwt(token) {
  const parts = String(token).split('.');
  if (parts.length !== 3) return { ok: false, reason: 'malformed' };
  const [header, body, sig] = parts;
  const expected = crypto.createHmac('sha256', getJwtSecret()).update(`${header}.${body}`).digest('base64url');
  const a = Buffer.from(sig);
  const b = Buffer.from(expected);
  if (a.length !== b.length || !crypto.timingSafeEqual(a, b)) return { ok: false, reason: 'signature' };
  let payload;
  try {
    payload = JSON.parse(Buffer.from(body, 'base64url').toString('utf-8'));
  } catch {
    return { ok: false, reason: 'malformed' };
  }
  if (!payload.exp || Math.floor(Date.now() / 1000) > payload.exp) return { ok: false, reason: 'expired' };
  return { ok: true, payload };
}

// ─── Users ───

function publicUser(row) {
  if (!row) return null;
  return { id: row.id, username: row.username, email: row.email, role: row.role, created_at: row.created_at, last_login_at: row.last_login_at };
}

export function registerUser({ username, email, password }) {
  if (!username || !USERNAME_RE.test(String(username))) {
    throw new AuthError(400, 'VALIDATION_ERROR', 'username 必须为 3-32 位字母/数字/下划线/连字符');
  }
  if (!password || String(password).length < 8 || !/[a-zA-Z]/.test(password) || !/[0-9]/.test(password)) {
    throw new AuthError(400, 'VALIDATION_ERROR', 'password 至少 8 位且同时包含字母和数字');
  }
  if (email && !EMAIL_RE.test(String(email))) {
    throw new AuthError(400, 'VALIDATION_ERROR', 'email 格式不正确');
  }
  if (stmts.getUserByUsername.get(username)) {
    throw new AuthError(409, 'USER_EXISTS', `用户名已存在: ${username}`);
  }
  if (email && stmts.getUserByEmail.get(email)) {
    throw new AuthError(409, 'USER_EXISTS', `邮箱已被注册: ${email}`);
  }
  // 首个注册用户自动成为 admin（权限系统引导）
  const isFirst = stmts.countUsers.get().c === 0;
  const role = isFirst ? 'admin' : 'user';
  const info = stmts.insertUser.run({
    username,
    email: email || null,
    passwordHash: hashPassword(password),
    role,
  });
  const user = stmts.getUserById.get(info.lastInsertRowid);
  logger.info(`User registered: ${username} (role=${role})`, { context: 'Auth' });
  const sessionToken = signJwt({ sub: user.id, username: user.username, role: user.role, type: 'session' }, SESSION_TTL_HOURS * 3600);
  return { user: publicUser(user), session_token: sessionToken, token_type: 'Bearer', expires_in: SESSION_TTL_HOURS * 3600 };
}

export function loginUser({ username, password }) {
  if (!username || !password) {
    throw new AuthError(400, 'VALIDATION_ERROR', 'username 与 password 必填');
  }
  const row = stmts.getUserByUsername.get(String(username));
  // 用户不存在与密码错误返回同一错误，避免用户名枚举
  if (!row || !verifyPassword(password, row.password_hash)) {
    throw new AuthError(401, 'AUTH_INVALID_CREDENTIALS', '用户名或密码错误');
  }
  stmts.touchUserLogin.run(row.id);
  const user = stmts.getUserById.get(row.id);
  const sessionToken = signJwt({ sub: user.id, username: user.username, role: user.role, type: 'session' }, SESSION_TTL_HOURS * 3600);
  return { user: publicUser(user), session_token: sessionToken, token_type: 'Bearer', expires_in: SESSION_TTL_HOURS * 3600 };
}

export function getUserById(id) {
  return publicUser(stmts.getUserById.get(id));
}

// ─── API Tokens ───

function sha256(text) {
  return crypto.createHash('sha256').update(text).digest('hex');
}

export function createApiToken(user, { name, expires_in_days }) {
  if (!name || typeof name !== 'string' || !name.trim() || name.trim().length > 64) {
    throw new AuthError(400, 'VALIDATION_ERROR', 'token 名称必填且不超过 64 字符');
  }
  let days = TOKEN_DEFAULT_TTL_DAYS;
  if (expires_in_days !== undefined && expires_in_days !== null) {
    days = Number(expires_in_days);
    if (!Number.isInteger(days) || days < 1 || days > TOKEN_MAX_TTL_DAYS) {
      throw new AuthError(400, 'VALIDATION_ERROR', `expires_in_days 须为 1-${TOKEN_MAX_TTL_DAYS} 的整数（传 null 表示永久）`);
    }
  }
  const plaintext = `idd_${crypto.randomBytes(32).toString('base64url')}`;
  const expiresAt = expires_in_days === null ? null : new Date(Date.now() + days * 86400_000).toISOString();
  const info = stmts.insertApiToken.run({
    userId: user.id,
    name: name.trim(),
    tokenHash: sha256(plaintext),
    tokenPrefix: plaintext.slice(0, 12),
    expiresAt,
  });
  logger.info(`API token created: user=${user.username} name=${name.trim()} id=${info.lastInsertRowid}`, { context: 'Auth' });
  return {
    id: info.lastInsertRowid,
    name: name.trim(),
    token: plaintext, // 仅此一次返回明文
    token_prefix: plaintext.slice(0, 12),
    created_at: new Date().toISOString(),
    expires_at: expiresAt,
    notice: '请立即保存 token 明文，系统仅存储其 SHA-256 哈希，之后无法再次查看',
  };
}

export function listApiTokens(user) {
  return stmts.listApiTokensByUser.all(user.id).map((t) => ({
    ...t,
    status: t.revoked_at ? 'revoked' : t.expires_at && new Date(t.expires_at) < new Date() ? 'expired' : 'active',
  }));
}

export function revokeApiToken(user, tokenId) {
  const row = stmts.getApiTokenById.get(Number(tokenId));
  if (!row) throw new AuthError(404, 'TOKEN_NOT_FOUND', `token 不存在: ${tokenId}`);
  // 权限检查：仅属主或 admin 可吊销
  if (row.user_id !== user.id && user.role !== 'admin') {
    throw new AuthError(403, 'FORBIDDEN', '无权吊销他人的 token');
  }
  stmts.revokeApiToken.run(row.id);
  return { id: row.id, revoked: true };
}

// ─── Request authentication ───

function extractBearerToken(req) {
  const header = req.headers.authorization;
  if (header && /^Bearer\s+/i.test(header)) {
    return header.replace(/^Bearer\s+/i, '').trim();
  }
  if (req.headers['x-api-token']) return String(req.headers['x-api-token']).trim();
  // SSE/EventSource 无法自定义 header，允许 ?token= 查询参数回退（仅 GET 流式端点使用）
  if (req.query?.token) return String(req.query.token).trim();
  return null;
}

export function authenticate(req) {
  const token = extractBearerToken(req);
  if (!token) {
    throw new AuthError(401, 'AUTH_REQUIRED', '缺少认证凭据：请在 Authorization 头携带 Bearer <token>（登录会话或 API Token）');
  }

  // 通道 1：登录会话 JWT
  const jwt = verifyJwt(token);
  if (jwt.ok && jwt.payload?.type === 'session') {
    const user = stmts.getUserById.get(jwt.payload.sub);
    if (!user) throw new AuthError(401, 'AUTH_INVALID', '会话对应用户不存在');
    return { user, auth_type: 'session' };
  }
  if (!jwt.ok && jwt.reason === 'expired' && token.split('.').length === 3) {
    throw new AuthError(401, 'AUTH_TOKEN_EXPIRED', '登录会话已过期，请重新登录');
  }

  // 通道 2：API Token（SHA-256 哈希比对）
  const row = stmts.getApiTokenByHash.get(sha256(token));
  if (!row) {
    throw new AuthError(401, 'AUTH_INVALID', '认证凭据无效或已失效');
  }
  if (row.revoked_at) {
    throw new AuthError(401, 'AUTH_TOKEN_REVOKED', `API token 已被吊销 (id=${row.id})`);
  }
  if (row.expires_at && new Date(row.expires_at) < new Date()) {
    throw new AuthError(401, 'AUTH_TOKEN_EXPIRED', `API token 已过期 (id=${row.id}, expires_at=${row.expires_at})`);
  }
  const user = stmts.getUserById.get(row.user_id);
  if (!user) throw new AuthError(401, 'AUTH_INVALID', 'token 对应用户不存在');
  stmts.touchApiTokenUsed.run(row.id);
  return { user, auth_type: 'api_token', token_id: row.id };
}
