// Tenancy policy for the request/service layer (P0-6 multi-tenancy, wave 2).
//
// This module is the ONE place that decides WHETHER ownership filtering applies.
// It wraps the frozen contract in src/middleware/ownership.mjs (who may see a
// row) with the deployment switch (whether identities exist at all):
//
//   AUTH_ENABLED=1 (default): authGuard runs first, so every /api request
//   carries req.user. A row is visible to its owner, to an admin, and — only
//   to an admin — when its owner_user_id is NULL (legacy/unowned, see the
//   migrations v3 backfill).
//
//   AUTH_ENABLED=0 (single-operator dev mode, §index.mjs does not even mount
//   the guard): req.user never exists, so enforcing tenancy would hide every
//   row from the only operator. Filtering is therefore bypassed, and rows
//   created by such a request keep owner_user_id NULL — i.e. they become
//   admin-only the moment auth is turned back on.
//
// Deny semantics: unviewable resources answer 404, never 403 — a foreign id
// must be indistinguishable from a missing one (no existence leak). The
// services do this by returning null/false/[] and the routes by 404ing.
//
// INTERNAL is the viewer sent by trusted service-to-service calls (a service
// asking for a row it already owns the context of). Route handlers must never
// pass it — they pass `req.user`, whose absence in auth-enabled mode is denied
// by canView() (fail closed).

import { canAccessOwner, isAdmin } from '../middleware/ownership.mjs';
import { rateLimit, rateLimitKeyByUser } from '../middleware/rateLimit.mjs';
import { isAuthEnabled } from './auth.service.mjs';

/** Trusted service-internal viewer: no filtering. Never exposed to routes. */
export const INTERNAL = Symbol.for('idd.tenancy.internal-viewer');

/** True when this deployment has identities and ownership must be enforced. */
export function tenancyEnabled() {
  return isAuthEnabled();
}

/**
 * owner_user_id to persist for a creation request. Accepts a user object
 * (`{ id }`), a raw id, or null/undefined — anything unusable becomes NULL
 * (legacy/unowned semantics, admin-only once auth is on).
 * @returns {number|null}
 */
export function resolveOwnerId(value) {
  const raw = value && typeof value === 'object' ? value.id : value;
  if (raw === null || raw === undefined || raw === '') return null;
  const n = Number(raw);
  return Number.isInteger(n) && n > 0 ? n : null;
}

/**
 * May `viewer` see (or act on) a row owned by `ownerId`?
 *
 * Signature by caller:
 *   INTERNAL        → trusted service-internal call → yes.
 *   undefined       → NO viewer context exists at all: either AUTH_ENABLED=0
 *                     (dev mode, authGuard not mounted) or a caller that mounts
 *                     the bare router in-process. With the guard mounted
 *                     (production), requireAuth always populates req.user, so
 *                     undefined cannot occur there → legacy/dev semantics
 *                     (no filtering) are safe.
 *   null / {}       → explicit "no authenticated user" → no (see canAccessOwner).
 *   { id, role }    → own rows only; admin sees everything; NULL-owner rows are
 *                     admin-only.
 */
export function canView(viewer, ownerId) {
  if (viewer === undefined || viewer === INTERNAL) return true;
  if (!tenancyEnabled()) return true;
  return canAccessOwner(viewer, ownerId);
}

/**
 * Admin-only middleware for destructive management operations.
 *
 * Uses the frozen requireRole('admin') when auth is on; in AUTH_ENABLED=0 dev
 * mode there is no identity to check, so the guard steps aside (the operator of
 * a local dev instance is the admin). Mirrors the §index.mjs mounting rule.
 */
export function adminOnly(req, res, next) {
  if (!tenancyEnabled()) return next();
  if (!req.user) {
    return res.status(401).json({ success: false, code: 'AUTH_REQUIRED', error: '未认证' });
  }
  if (!isAdmin(req.user)) {
    return res.status(403).json({ success: false, code: 'FORBIDDEN', error: '需要角色: admin' });
  }
  next();
}

/**
 * User-keyed rate limiter that steps aside in AUTH_ENABLED=0 dev mode.
 *
 * Rate limiting needs an identity to be meaningful: in the dev mode above,
 * keying a local operator by IP would throttle the only person using the
 * console (and the self-tests that drive it). With auth on, the budget is
 * per authenticated user with an IP fallback for anonymous traffic
 * (rateLimitKeyByUser).
 *
 * @param {{windowMs:number, max:number, code?:string, message?:string}} opts
 */
export function userRateLimit({ windowMs, max, code = 'RATE_LIMITED', message } = {}) {
  const limiter = rateLimit({
    windowMs,
    max,
    keyFn: rateLimitKeyByUser,
    code,
    ...(message ? { message } : {}),
  });
  const middleware = (req, res, next) => (tenancyEnabled() ? limiter(req, res, next) : next());
  middleware.reset = limiter.reset;
  middleware.windowMs = limiter.windowMs;
  middleware.max = limiter.max;
  return middleware;
}
