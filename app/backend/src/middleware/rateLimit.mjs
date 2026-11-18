// Rate limiting (P0-6) — zero-dependency, in-process, sliding window.
//
// Design notes:
// - A Map<key, timestamps[]> sliding log. Pruning happens per-request on the
//   touched key; a bounded sweep keeps the map from growing without limit when
//   under a wide-spread key (many IPs). No timers: nothing keeps the event
//   loop alive and no background work is scheduled.
// - Blocked requests do NOT extend their own window (the first hit in the
//   window is what Retry-After is computed from).
// - Single-threaded Node makes check-then-record race-free.
// - Process-local state: N replicas each enforce their own budget. For an ops
//   console behind one backend process that is sufficient; a shared store is a
//   later concern.
//
// Usage:
//   router.post('/login', rateLimit({ windowMs: 60000, max: 5, keyFn: rateLimitKeyByIp }), handler)

const DEFAULT_WINDOW_MS = 60_000;
const MAX_TRACKED_KEYS = 10_000;
const SWEEP_EVERY_N_REQUESTS = 500;

/** Default key: the client address (`req.ip` honours Express' trust-proxy setting). */
export function rateLimitKeyByIp(req) {
  const ip = req?.ip || req?.socket?.remoteAddress || req?.connection?.remoteAddress || 'unknown';
  return `ip:${ip}`;
}

/** Key by authenticated user id, falling back to the IP for anonymous requests. */
export function rateLimitKeyByUser(req) {
  const id = req?.user?.id;
  if (id === undefined || id === null) return rateLimitKeyByIp(req);
  return `user:${id}`;
}

/**
 * @param {object} opts
 * @param {number} [opts.windowMs=60000] sliding window length
 * @param {number} [opts.max=60] allowed requests per key per window
 * @param {(req:any)=>string} [opts.keyFn=rateLimitKeyByIp]
 * @param {(req:any,res:any,info:{key:string,retryAfterSec:number,limit:number,windowMs:number})=>boolean|void} [opts.onLimit]
 *        Notification hook (logging/metrics). Return `true` to take over the response;
 *        otherwise the default 429 JSON is sent (unless the hook already sent one).
 * @param {string} [opts.code='RATE_LIMITED'] machine code in the 429 body
 * @param {string} [opts.message] human message in the 429 body
 * @returns {import('express').RequestHandler & { reset(key?:string):void, max:number, windowMs:number }}
 */
export function rateLimit({
  windowMs = DEFAULT_WINDOW_MS,
  max = 60,
  keyFn = rateLimitKeyByIp,
  onLimit = null,
  code = 'RATE_LIMITED',
  message = '请求过于频繁，请稍后再试',
} = {}) {
  const window = Number(windowMs);
  if (!Number.isFinite(window) || window <= 0) {
    throw new TypeError(`rateLimit: windowMs must be a positive number, got ${windowMs}`);
  }
  const limit = Number(max);
  if (!Number.isInteger(limit) || limit <= 0) {
    throw new TypeError(`rateLimit: max must be a positive integer, got ${max}`);
  }
  if (typeof keyFn !== 'function') {
    throw new TypeError('rateLimit: keyFn must be a function');
  }

  /** @type {Map<string, number[]>} key → ascending hit timestamps (ms) */
  const hits = new Map();
  let requestCount = 0;

  function prune(list, now) {
    const cutoff = now - window;
    let stale = 0;
    while (stale < list.length && list[stale] <= cutoff) stale += 1;
    if (stale > 0) list.splice(0, stale);
    return list;
  }

  function sweep(now) {
    for (const [key, list] of hits) {
      if (prune(list, now).length === 0) hits.delete(key);
      if (hits.size <= MAX_TRACKED_KEYS) break;
    }
    // Still oversized (all keys hot) → evict the oldest-inserted keys.
    while (hits.size > MAX_TRACKED_KEYS) {
      hits.delete(hits.keys().next().value);
    }
  }

  function middleware(req, res, next) {
    const now = Date.now();
    const key = String(keyFn(req));
    let list = hits.get(key);
    if (!list) {
      list = [];
      hits.set(key, list);
    }
    prune(list, now);

    if (list.length >= limit) {
      const retryAfterSec = Math.max(1, Math.ceil((list[0] + window - now) / 1000));
      res.setHeader('Retry-After', String(retryAfterSec));
      const info = { key, retryAfterSec, limit, windowMs: window };
      const handled = typeof onLimit === 'function' ? onLimit(req, res, info) === true : false;
      if (!handled && !res.headersSent) {
        res.status(429).json({
          success: false,
          code,
          error: message,
          retry_after: retryAfterSec,
        });
      }
      return;
    }

    list.push(now);
    requestCount += 1;
    if (requestCount % SWEEP_EVERY_N_REQUESTS === 0) sweep(now);

    next();
  }

  middleware.reset = (key) => {
    if (key === undefined) hits.clear();
    else hits.delete(String(key));
  };
  middleware.windowMs = window;
  middleware.max = limit;
  middleware.keyFn = keyFn;

  return middleware;
}

export { MAX_TRACKED_KEYS };
