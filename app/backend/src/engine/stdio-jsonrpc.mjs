// stdio-jsonrpc — NDJSON JSON-RPC 2.0 client over a child process.
//
// Used by the resident-session engines that speak JSON-RPC over stdio:
// codex (app-server) and the ACP family (dsh / hermes / qwen).
//
// Distinguishes the three message classes (多 Harness 架构 · 共享基础设施):
//   · responses  → resolve the pending request (by id)
//   · notifications → {method, params} without id → onNotification
//   · server→client requests → {method, params, id} → onRequest handler,
//     whose return value is sent back (approval / permission callbacks)
//
// Unknown frames are parsed-tolerantly: malformed lines are counted, never
// fatal (schema drift protection).

export function createStdioJsonRpc(proc, {
  onRequest = null,           // async (method, params) => result  (server→client request)
  onNotification = null,      // (method, params) => void
  requestTimeoutMs = 30000,
  label = 'jsonrpc',
} = {}) {
  const pending = new Map();
  let nextId = 1;
  let malformed = 0;
  let dead = false;
  const notificationQueue = [];
  const waiters = [];

  const flushWaiters = () => {
    while (waiters.length && notificationQueue.length) {
      const w = waiters.shift();
      w(notificationQueue.shift());
    }
  };

  const handleFrame = (frame) => {
    if (!frame || typeof frame !== 'object') return;
    if (frame.id !== undefined && frame.id !== null && (frame.result !== undefined || frame.error !== undefined)) {
      // Response to our request
      const entry = pending.get(frame.id);
      if (!entry) return;
      pending.delete(frame.id);
      clearTimeout(entry.timer);
      if (frame.error) {
        const err = new Error(frame.error.message || `JSON-RPC error ${frame.error.code}`);
        err.code = frame.error.code;
        err.data = frame.error.data;
        entry.reject(err);
      } else {
        entry.resolve(frame.result);
      }
      return;
    }
    if (typeof frame.method === 'string') {
      if (frame.id !== undefined && frame.id !== null) {
        // Server→client request (e.g. approval prompts)
        if (!onRequest) {
          sendResponse(frame.id, null, { code: -32601, message: 'Method not handled by client' });
          return;
        }
        Promise.resolve()
          .then(() => onRequest(frame.method, frame.params ?? {}))
          .then((result) => sendResponse(frame.id, result ?? {}))
          .catch((e) => sendResponse(frame.id, null, { code: -32000, message: e.message }));
        return;
      }
      notificationQueue.push({ method: frame.method, params: frame.params ?? {} });
      if (onNotification) {
        try { onNotification(notificationQueue[notificationQueue.length - 1]); } catch { /* handlers are defensive */ }
      }
      flushWaiters();
    }
  };

  let lineBuf = '';
  proc.stdout?.on('data', (d) => {
    lineBuf += d.toString();
    let idx;
    while ((idx = lineBuf.indexOf('\n')) >= 0) {
      const line = lineBuf.slice(0, idx).trim();
      lineBuf = lineBuf.slice(idx + 1);
      if (!line) continue;
      try {
        handleFrame(JSON.parse(line));
      } catch {
        malformed += 1; // malformed line — counted, not fatal
      }
    }
  });

  proc.on('exit', () => {
    dead = true;
    for (const [, entry] of pending) {
      clearTimeout(entry.timer);
      entry.reject(Object.assign(new Error(`${label} process exited before response`), { code: 'PROC_EXIT' }));
    }
    pending.clear();
    flushWaiters();
  });

  proc.on('error', (err) => {
    dead = true;
    for (const [, entry] of pending) {
      clearTimeout(entry.timer);
      entry.reject(Object.assign(new Error(`${label} spawn error: ${err.message}`), { code: 'SPAWN_ERROR' }));
    }
    pending.clear();
    flushWaiters();
  });

  function sendRaw(obj) {
    if (dead || proc.stdin.destroyed) throw new Error(`${label} stdin closed`);
    proc.stdin.write(`${JSON.stringify(obj)}\n`);
  }

  function sendResponse(id, result, error) {
    try {
      sendRaw(error ? { jsonrpc: '2.0', id, error } : { jsonrpc: '2.0', id, result: result ?? {} });
    } catch { /* process gone — nothing to answer */ }
  }

  return {
    /** Client→server request; rejects on error response / timeout / exit. */
    request(method, params, { timeoutMs = requestTimeoutMs } = {}) {
      if (dead) return Promise.reject(Object.assign(new Error(`${label} process not alive`), { code: 'PROC_EXIT' }));
      const id = nextId++;
      return new Promise((resolve, reject) => {
        const timer = timeoutMs > 0
          ? setTimeout(() => {
            pending.delete(id);
            reject(Object.assign(new Error(`${label} request timeout: ${method}`), { code: 'TIMEOUT' }));
          }, timeoutMs)
          : null;
        pending.set(id, { resolve, reject, timer });
        try {
          sendRaw({ jsonrpc: '2.0', id, method, params: params ?? {} });
        } catch (e) {
          clearTimeout(timer);
          pending.delete(id);
          reject(e);
        }
      });
    },
    /** Fire-and-forget client notification. */
    notify(method, params) {
      try { sendRaw({ jsonrpc: '2.0', method, params: params ?? {} }); } catch { /* ignore */ }
    },
    /** Next notification (for tests / polling consumers). */
    nextNotification(timeoutMs = 5000) {
      if (notificationQueue.length) return Promise.resolve(notificationQueue.shift());
      return new Promise((resolve, reject) => {
        const timer = setTimeout(() => {
          const i = waiters.indexOf(resolver);
          if (i >= 0) waiters.splice(i, 1);
          reject(new Error('notification wait timeout'));
        }, timeoutMs);
        const resolver = (n) => { clearTimeout(timer); resolve(n); };
        waiters.push(resolver);
      });
    },
    get dead() { return dead; },
    malformedCount: () => malformed,
    /** Feed a raw line (test hook). */
    _handleLine: (line) => handleFrame(JSON.parse(line)),
  };
}
