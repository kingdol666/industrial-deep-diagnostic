// Lifecycle — process-level shutdown coordination.
//
// Dependency-free by design (no logger, no config): the entrypoint owns the
// logging, this module owns the *state* so anything can ask "are we going
// down?" or attach cleanup without importing the server.
//
//   setShuttingDown(reason)   → flips the flag read by shutdownGuardMiddleware
//   isShuttingDown()          → guard predicate
//   registerShutdownHook(fn)  → LIFO cleanup callbacks (WAL checkpoint, …)
//   runShutdownHooks()        → awaited exactly once, each hook isolated
//
// Used by src/index.mjs for SIGTERM/SIGINT + fatal-error shutdown.

let shuttingDown = false;
let shutdownReason = null;
let hooks = [];
let hooksRan = false;

export function isShuttingDown() {
  return shuttingDown;
}

export function getShutdownReason() {
  return shutdownReason;
}

/** Idempotent: the first reason wins (a second signal must not rewrite it). */
export function setShuttingDown(reason = 'unspecified') {
  if (shuttingDown) return false;
  shuttingDown = true;
  shutdownReason = String(reason);
  return true;
}

/**
 * Register a cleanup callback. Hooks run in reverse registration order (LIFO),
 * so later-registered, more specific cleanup unwinds first.
 * A hook registered while shutdown is already running is invoked immediately
 * (fire-and-forget) instead of being silently dropped.
 */
export function registerShutdownHook(fn) {
  if (typeof fn !== 'function') return false;
  if (shuttingDown || hooksRan) {
    Promise.resolve()
      .then(() => fn())
      .catch(() => { /* late hook failure must not surface as an unhandled rejection */ });
    return false;
  }
  hooks.push(fn);
  return true;
}

/**
 * Run every registered hook (LIFO) exactly once. A throwing hook never blocks
 * the others — its error is collected and handed to `onError` (optional).
 * Returns the errors array; a second call is a no-op returning [].
 */
export async function runShutdownHooks({ onError } = {}) {
  if (hooksRan) return [];
  hooksRan = true;
  const pending = hooks;
  hooks = [];
  const errors = [];
  for (let i = pending.length - 1; i >= 0; i -= 1) {
    try {
      await pending[i]();
    } catch (err) {
      errors.push(err);
      try { if (typeof onError === 'function') onError(err); } catch { /* reporting must not break shutdown */ }
    }
  }
  return errors;
}

/**
 * Express-compatible middleware: while shutting down, new API traffic gets a
 * 503 so clients fail fast and retry elsewhere instead of hammering a draining
 * process. GET /api/health stays answered — a liveness probe must be able to
 * observe the process until it is actually gone.
 */
export function shutdownGuardMiddleware() {
  return function shutdownGuard(req, res, next) {
    if (!shuttingDown) return next();
    const path = String(req?.path || req?.url || '');
    if (!path.startsWith('/api')) return next();
    if (req.method === 'GET' && path === '/api/health') return next();
    res.setHeader('Connection', 'close');
    return res.status(503).json({ success: false, code: 'SHUTTING_DOWN' });
  };
}
