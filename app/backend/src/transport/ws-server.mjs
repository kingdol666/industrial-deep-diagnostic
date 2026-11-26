// WebSocket Server — enterprise-grade real-time diagnosis streaming
// Protocol: catalog snapshots + run snapshots + incremental run events

import { WebSocketServer } from 'ws';
import engine, {
  getActiveRuns,
} from '../engine/diagnosis-engine.mjs';
import {
  listRuns,
  getRunRealtimeSnapshot,
  canViewRun,
  continueDiagnosis,
  sendChatMessage as sendDiagnosisChatMessage,
  // Viewing subscription: seeds the engine entry from the persisted run so a
  // completed run is not reported as "pending" just because it was opened.
  subscribeRunView as subscribe,
} from '../services/diagnosis.service.mjs';
import {
  listActiveChats,
  getChatHistory,
  startChat,
  sendChatMessage,
  stopChat,
  subscribeChatEvents,
} from '../services/chat.service.mjs';
import { websocket as wsConfig } from '../../../../config/loader.mjs';
import logger from '../utils/logger.mjs';
import { authenticate, isAuthEnabled, AuthError } from '../services/auth.service.mjs';
import { sessionCookieToken } from '../middleware/auth.middleware.mjs';
import { resolveOwnerId } from '../services/tenancy.mjs';

let wss = null;
const clientState = new WeakMap();

// ─── Tenancy (P0-6) ─────────────────────────────────────────────────────────
// `ws.authUser`, written by the handshake below, is the single identity source
// for a connection: every run/chat-scoped read, subscription and action passes
// it to the service layer as the `viewer` (the services already filter by
// ownership). A foreign resource is handled exactly like a missing one — same
// "not found" error frame, no subscription, no events — which is the convention
// this file has always used for unknown ids, and it keeps existence private.
//
// AUTH_ENABLED=0 (single-operator dev mode): the handshake stores nothing, so
// the viewer is `undefined`, which every service's default parameter maps to
// the trusted INTERNAL viewer — the pre-tenancy, unfiltered behaviour the local
// console relies on.
function viewerOf(ws) {
  return ws?.authUser;
}

/** Cache key for per-viewer fan-out inside one broadcast pass. */
function viewerKey(viewer) {
  return viewer && viewer.id !== undefined && viewer.id !== null ? `u:${viewer.id}` : 'internal';
}

/** RunIds with a live engine that this viewer may see (runId-only, still per-owner). */
function activeRunsFor(viewer) {
  return getActiveRuns().filter((runId) => canViewRun(runId, viewer));
}

// ─── Wire limits / backpressure ──────────────────────────────────────────────
// Frames above the payload cap close the connection with 1009 (ws default is
// 100MB — far too much for a browser admin console).
const DEFAULT_MAX_PAYLOAD_BYTES = 1024 * 1024; // 1MB
// A client whose send buffer grows past this is not keeping up: drop its
// non-critical frames rather than buffering megabytes of stale UI updates.
const MAX_BUFFERED_BEFORE_DROP = 4 * 1024 * 1024; // 4MB
const backpressureWarned = new WeakSet();

function resolveMaxPayload() {
  const raw = process.env.WS_MAX_PAYLOAD_BYTES;
  if (raw !== undefined && raw !== '') {
    const parsed = Number(raw);
    if (Number.isFinite(parsed) && parsed > 0) return Math.floor(parsed);
    logger.warn(`Ignoring invalid WS_MAX_PAYLOAD_BYTES=${raw} (expected positive number)`, { context: 'WS' });
  }
  return DEFAULT_MAX_PAYLOAD_BYTES;
}

/**
 * Send a frame unless the socket is closed, or unless it is non-critical and
 * the client is too far behind. Terminal/error/auth frames pass `critical:
 * true` so a slow client still learns the run ended (they are small and rare —
 * drops there would leave the UI waiting forever).
 * Exported for the transport-security test.
 */
export function safeSend(ws, payload, { critical = false } = {}) {
  if (!ws || ws.readyState !== ws.OPEN) return false;
  if (!critical && Number(ws.bufferedAmount || 0) > MAX_BUFFERED_BEFORE_DROP) {
    if (!backpressureWarned.has(ws)) {
      backpressureWarned.add(ws);
      logger.warn(`Backpressure: dropping non-critical frames (bufferedAmount=${ws.bufferedAmount})`, { context: 'WS' });
    }
    return false;
  }
  ws.send(JSON.stringify(payload));
  return true;
}

// ─── Token transport ─────────────────────────────────────────────────────────
// Preferred: the token travels as a WebSocket subprotocol offer
//   new WebSocket(url, ['idd-token', token])
// which browsers permit (unlike custom headers) and which keeps credentials out
// of URLs, access logs and proxy logs.
export const WS_TOKEN_PROTOCOL = 'idd-token';

/** Read `<token>` from `Sec-WebSocket-Protocol: idd-token, <token>`. */
function tokenFromSubprotocol(req) {
  const header = req?.headers?.['sec-websocket-protocol'];
  if (!header) return '';
  const parts = String(header).split(',').map((p) => p.trim()).filter(Boolean);
  const idx = parts.indexOf(WS_TOKEN_PROTOCOL);
  return idx >= 0 ? (parts[idx + 1] || '') : '';
}

/**
 * @deprecated /ws?token=<token> — kept one release for compatibility with
 * already-deployed clients. Remove next release: URL-borne credentials leak
 * into logs, browser history and referrers.
 */
function tokenFromQuery(req) {
  try {
    return new URL(req?.url || '/ws', 'http://localhost').searchParams.get('token') || '';
  } catch {
    return '';
  }
}

/**
 * 会话 Cookie 回退（P0-6）：登录后由 POST /api/auth/login 下发的 HttpOnly
 * `idd_session` Cookie 会随同源握手请求自动携带（浏览器无法给 WebSocket 自定义
 * header，URL 里放凭据又会泄漏）。仅接受会话 JWT 形态 —— API Token 保持
 * header/subprotocol-only，与 HTTP 侧策略一致。
 */
function tokenFromCookie(req) {
  return sessionCookieToken(req) || '';
}

function getOrCreateState(ws) {
  let state = clientState.get(ws);
  if (!state) {
    state = {
      subscriptions: new Map(),
      chatSubscriptions: new Map(),
      watchCatalog: false,
      lastPongAt: Date.now(),
      heartbeatTimer: null,
      clientId: `client_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`,
    };
    clientState.set(ws, state);
  }
  return state;
}

function clearRunSubscription(state, runId) {
  const entry = state.subscriptions.get(runId);
  if (entry?.unsubscribe) entry.unsubscribe();
  state.subscriptions.delete(runId);
}

function clearAllSubscriptions(state) {
  for (const runId of state.subscriptions.keys()) {
    clearRunSubscription(state, runId);
  }
  for (const chatId of state.chatSubscriptions.keys()) {
    const entry = state.chatSubscriptions.get(chatId);
    if (entry?.unsubscribe) entry.unsubscribe();
    state.chatSubscriptions.delete(chatId);
  }
  if (state.heartbeatTimer) {
    clearInterval(state.heartbeatTimer);
    state.heartbeatTimer = null;
  }
}

function clearChatSubscription(state, chatId) {
  const entry = state.chatSubscriptions.get(chatId);
  if (entry?.unsubscribe) entry.unsubscribe();
  state.chatSubscriptions.delete(chatId);
}

function makeRunSummary(run) {
  return {
    runId: run.run_id,
    sessionId: run.session_id || null,
    name: run.name,
    sceneName: run.scene_name,
    status: run.status,
    engineStatus: run.engineStatus || run.status,
    createdAt: run.created_at,
    completedAt: run.completed_at || null,
    score: run.score ?? null,
    verdict: run.judge_verdict ?? null,
    reportPath: run.report_path ?? null,
    errorMessage: run.error_message ?? null,
  };
}

// `viewer` = the socket's authenticated user: the run list and the active-run
// ids are filtered to what this viewer may see.
function sendCatalogSnapshot(ws, viewer) {
  const runs = listRuns(viewer).map(makeRunSummary);
  safeSend(ws, {
    type: 'catalog_snapshot',
    data: {
      runs,
      activeRuns: activeRunsFor(viewer),
      sentAt: new Date().toISOString(),
    },
  });
}

function makeChatSummary(session) {
  return {
    chatId: session.chatId,
    sessionId: session.sessionId || null,
    originSessionId: session.originSessionId || session.sessionId || null,
    currentSessionId: session.currentSessionId || null,
    title: session.title || '',
    status: session.status || 'unknown',
    permissionMode: session.permissionMode || 'default',
    cwd: session.cwd || null,
    createdAt: session.createdAt || null,
    updatedAt: session.updatedAt || null,
  };
}

function sendChatCatalogSnapshot(ws, viewer) {
  const chats = listActiveChats(viewer).map(makeChatSummary);
  safeSend(ws, {
    type: 'chat_catalog_snapshot',
    data: {
      chats,
      sentAt: new Date().toISOString(),
    },
  });
}

function mapChatEventForWS(eventType, data) {
  if (eventType === 'message') return { type: 'message', data };
  if (eventType === 'thinking') return { type: 'thinking', data };
  if (eventType === 'tool_use') return { type: 'tool_use', data };
  if (eventType === 'tool_result') return { type: 'tool_result', data };
  if (eventType === 'system') return { type: 'system', subtype: data?.subtype || 'system', data };
  if (eventType === 'result') return { type: 'stats', data };
  if (eventType === 'stream_event') {
    return {
      type: 'stream_event',
      subtype: data?.type || 'stream_event',
      data,
    };
  }
  if (eventType === 'raw') {
    return {
      type: 'stream_event',
      subtype: data?.type || 'raw',
      data,
    };
  }
  if (eventType === 'chat_error') {
    return { type: 'error', data: { error: data?.error || 'Chat failed' } };
  }
  if (eventType === 'chat_complete') {
    return { type: 'complete', data: { status: 'completed' } };
  }
  if (eventType === 'chat_init') {
    return { type: 'system', subtype: 'init', data };
  }
  return { type: 'stream_event', subtype: eventType, data };
}

function mapChatMessageRowToWS(row, seq) {
  const subtype = row.event_subtype || null;
  if (row.event_type === 'user_message') {
    return {
      type: 'user_message',
      data: { role: 'user', content: row.content || '' },
      _seq: seq,
    };
  }
  if (row.event_type === 'message') {
    return {
      type: 'message',
      data: { role: 'assistant', content: row.content || '' },
      _seq: seq,
    };
  }
  if (row.event_type === 'thinking') {
    return {
      type: 'thinking',
      data: { content: row.content || '' },
      _seq: seq,
    };
  }
  if (row.event_type === 'tool_use') {
    try {
      return {
        type: 'tool_use',
        data: JSON.parse(row.content || '{}'),
        _seq: seq,
      };
    } catch {
      return {
        type: 'tool_use',
        data: { name: subtype || 'Tool', input: { raw: row.content || '' } },
        _seq: seq,
      };
    }
  }
  if (row.event_type === 'tool_result') {
    return {
      type: 'tool_result',
      data: {
        toolUseId: '',
        summary: row.content || '',
        isError: subtype === 'error',
      },
      _seq: seq,
    };
  }
  if (row.event_type === 'result') {
    try {
      return {
        type: 'stats',
        data: JSON.parse(row.content || '{}'),
        _seq: seq,
      };
    } catch {
      return {
        type: 'stats',
        data: { subtype: subtype || 'completed' },
        _seq: seq,
      };
    }
  }
  if (row.event_type === 'error') {
    return {
      type: 'error',
      data: { error: row.content || 'Chat error' },
      _seq: seq,
    };
  }
  if (row.event_type === 'system') {
    try {
      const parsed = JSON.parse(row.content || '{}');
      return {
        type: 'system',
        subtype: parsed.subtype || subtype || 'system',
        data: parsed,
        _seq: seq,
      };
    } catch {
      return {
        type: 'system',
        subtype: subtype || 'system',
        data: { content: row.content || '' },
        _seq: seq,
      };
    }
  }
  if (row.event_type === 'stream_event' || row.event_type === 'raw') {
    try {
      return {
        type: 'stream_event',
        subtype: subtype || row.event_type || 'stream_event',
        data: JSON.parse(row.content || '{}'),
        _seq: seq,
      };
    } catch {
      return {
        type: 'stream_event',
        subtype: subtype || row.event_type || 'stream_event',
        data: { raw: row.content || '' },
        _seq: seq,
      };
    }
  }
  return {
    type: 'stream_event',
    subtype: row.event_type || 'unknown',
    data: { raw: row.content || '' },
    _seq: seq,
  };
}

// `viewer` gates the history read: a foreign chat is indistinguishable from a
// missing one → null → the same "Chat not found" error frame.
function buildChatSnapshot(chatId, viewer) {
  const history = getChatHistory(chatId, viewer);
  if (history) {
    return {
      chatId,
      session: {
        chatId: history.session.chatId,
        sessionId: history.session.sessionId || null,
        originSessionId: history.session.originSessionId || history.session.sessionId || null,
        currentSessionId: history.session.currentSessionId || null,
        title: history.session.title || '',
        status: history.session.status || 'unknown',
        permissionMode: history.session.permissionMode || 'default',
        // 全引擎时代：快照如实携带真实 harness（mock/gemini/codex/…），不再压成 omp/claude
        harness: history.session.harness || 'claude',
        cwd: history.session.cwd || null,
        createdAt: history.session.createdAt || null,
        updatedAt: history.session.updatedAt || null,
      },
      events: (history.messages || []).map((row, index) => mapChatMessageRowToWS(row, index + 1)),
    };
  }

  return null;
}

function sendChatSnapshot(ws, chatId, viewer) {
  const snapshot = buildChatSnapshot(chatId, viewer);
  if (!snapshot) {
    safeSend(ws, {
      type: 'error',
      data: { message: `Chat not found: ${chatId}`, chatId },
    }, { critical: true });
    return false;
  }

  safeSend(ws, {
    type: 'chat_snapshot',
    data: {
      ...snapshot,
      sentAt: new Date().toISOString(),
    },
  });
  return true;
}

function subscribeChat(ws, state, chatId, viewer) {
  clearChatSubscription(state, chatId);

  // Foreign chat → snapshot is null → refusal frame, no subscription (a
  // subscription would otherwise stream the owner's chat events to this socket).
  const snapshotExists = sendChatSnapshot(ws, chatId, viewer);
  if (!snapshotExists) return;

  const unsubscribe = subscribeChatEvents(chatId, (eventType, data) => {
    safeSend(ws, {
      type: 'chat_event',
      data: {
        chatId,
        event: mapChatEventForWS(eventType, data),
      },
    });
  }, viewer);

  state.chatSubscriptions.set(chatId, { unsubscribe });
  safeSend(ws, {
    type: 'chat_subscribed',
    data: { chatId },
  });
}

function sendRunSnapshot(ws, runId, viewer) {
  const snapshot = getRunRealtimeSnapshot(runId, viewer);
  if (!snapshot) {
    safeSend(ws, {
      type: 'error',
      data: { message: `Run not found: ${runId}`, runId },
    }, { critical: true });
    return false;
  }

  safeSend(ws, {
    type: 'run_snapshot',
    data: {
      runId,
      run: snapshot.run,
      liveStatus: snapshot.liveStatus,
      hasActiveEngineRun: snapshot.hasActiveEngineRun,
      currentQuestion: snapshot.currentQuestion || null,
      events: snapshot.events,
      events_total: snapshot.events_total,
      events_truncated: snapshot.events_truncated,
      events_limit: snapshot.events_limit,
      sentAt: new Date().toISOString(),
    },
  });
  return true;
}

// Per-viewer fan-out: each watching socket gets only the runs it may see
// (payload computed once per distinct viewer in this pass).
function broadcastCatalogUpdate() {
  if (!wss) return;
  const byViewer = new Map();
  for (const ws of wss.clients) {
    const state = clientState.get(ws);
    if (!state?.watchCatalog) continue;
    const viewer = viewerOf(ws);
    const key = viewerKey(viewer);
    let data = byViewer.get(key);
    if (!data) {
      data = {
        runs: listRuns(viewer).map(makeRunSummary),
        activeRuns: activeRunsFor(viewer),
      };
      byViewer.set(key, data);
    }
    safeSend(ws, {
      type: 'catalog_update',
      data: {
        runs: data.runs,
        activeRuns: data.activeRuns,
        sentAt: new Date().toISOString(),
      },
    });
  }
}

function broadcastRunStatusUpdate(runId, event) {
  if (!wss || event.type !== 'status') return;
  const byViewer = new Map(); // viewer key → snapshot | null
  for (const ws of wss.clients) {
    const state = clientState.get(ws);
    if (!state?.watchCatalog) continue;
    const viewer = viewerOf(ws);
    const key = viewerKey(viewer);
    if (!byViewer.has(key)) byViewer.set(key, getRunRealtimeSnapshot(runId, viewer));
    const snapshot = byViewer.get(key);
    // null = a run this viewer may not see (foreign or gone): silence, exactly
    // like the pre-existing missing-run branch.
    if (!snapshot) continue;

    safeSend(ws, {
      type: 'run_updated',
      data: {
        runId,
        run: snapshot.run,
        liveStatus: snapshot.liveStatus,
        hasActiveEngineRun: snapshot.hasActiveEngineRun,
        statusEvent: event,
        sentAt: new Date().toISOString(),
      },
    });
  }
}

function subscribeRun(ws, state, runId, viewer) {
  clearRunSubscription(state, runId);

  // Foreign run → snapshot null → refusal frame, and crucially NO subscribe()
  // call below: the engine's event stream must never reach this socket.
  const snapshotExists = sendRunSnapshot(ws, runId, viewer);
  if (!snapshotExists) return;

  const unsubscribe = subscribe(runId, (event) => {
    // Terminal run frames are always delivered — a dropped `complete`/`error`
    // would leave the client waiting on a finished run.
    const terminal = event?.type === 'complete' || event?.type === 'error' || event?.type === 'stream_end';
    safeSend(ws, {
      type: 'run_event',
      data: {
        runId,
        event,
      },
    }, { critical: terminal });
  });

  state.subscriptions.set(runId, { unsubscribe });

  safeSend(ws, {
    type: 'subscribed',
    data: {
      runId,
      activeRuns: activeRunsFor(viewer),
    },
  });
}

export function initWebSocket(httpServer) {
  const maxPayload = resolveMaxPayload();
  wss = new WebSocketServer({
    server: httpServer,
    path: '/ws',
    maxPayload,
    // Select the token-carrying subprotocol when the client offers it; fall
    // back to ws' own default (first protocol offered) so clients that
    // negotiate something else are unaffected.
    handleProtocols: (protocols) => {
      const offered = protocols instanceof Set ? protocols : new Set(protocols || []);
      if (offered.has(WS_TOKEN_PROTOCOL)) return WS_TOKEN_PROTOCOL;
      return offered.values().next().value || false;
    },
  });
  logger.info(`WebSocket server ready (path /ws, maxPayload=${maxPayload}B)`, { context: 'WS' });

  engine.on('event', ({ runId, event }) => {
    if (event.type === 'status' || event.type === 'complete' || event.type === 'error') {
      broadcastCatalogUpdate();
    }
    broadcastRunStatusUpdate(runId, event);
  });

  engine.on('run:closed', () => {
    broadcastCatalogUpdate();
  });

  wss.on('connection', (ws, req) => {
    // ─── 连接鉴权：subprotocol ['idd-token', <token>]（与 HTTP API 同一 token 体系）───
    if (isAuthEnabled()) {
      try {
        // 凭据解析顺序：subprotocol（首选，浏览器可携带且不入日志）→ query
        // token（旧客户端过渡回退，下一版本移除）→ idd_session Cookie（同源浏览器
        // 会话，登录后自动携带）。三者走同一 authenticate 校验路径。
        const token = tokenFromSubprotocol(req) || tokenFromQuery(req) || tokenFromCookie(req);
        const fakeReq = { headers: token ? { authorization: `Bearer ${token}` } : {} };
        const { user } = authenticate(fakeReq);
        ws.authUser = user;
      } catch (err) {
        const code = err instanceof AuthError ? err.code : 'AUTH_INTERNAL_ERROR';
        logger.warn(`WS connection rejected: ${code}`, { context: 'WS' });
        ws.close(4401, `unauthorized: ${code}`);
        return;
      }
    }

    const state = getOrCreateState(ws);
    // This connection's viewer for the whole session (undefined in dev mode).
    const viewer = viewerOf(ws);
    const clientIp = req?.headers?.['x-forwarded-for']?.split(',')[0]?.trim() || req?.socket?.remoteAddress || 'unknown';
    logger.info(`Client connected: ${state.clientId} (IP: ${clientIp}, total: ${wss.clients.size})`, { context: 'WS' });

    // --- Server-side heartbeat ---
    const hbInterval = wsConfig?.heartbeat_interval_ms || 30000;
    const hbTimeout = wsConfig?.heartbeat_timeout_ms || 60000;
    state.lastPongAt = Date.now();

    state.heartbeatTimer = setInterval(() => {
      if (ws.readyState !== ws.OPEN) return;
      const elapsed = Date.now() - state.lastPongAt;
      if (elapsed > hbTimeout) {
        logger.warn(`Heartbeat timeout (${elapsed}ms) — terminating ${state.clientId}`, { context: 'WS' });
        ws.terminate();
        return;
      }
      safeSend(ws, { type: 'ping', data: { ts: Date.now() } });
    }, hbInterval);

    ws.on('message', (raw) => {
      try {
        const msg = JSON.parse(raw.toString());

        switch (msg.type) {
          case 'subscribe_run': {
            subscribeRun(ws, state, msg.runId, viewer);
            break;
          }

          case 'unsubscribe_run': {
            if (msg.runId) clearRunSubscription(state, msg.runId);
            safeSend(ws, { type: 'unsubscribed', data: { runId: msg.runId || null } });
            break;
          }

          case 'watch_catalog': {
            state.watchCatalog = msg.enabled !== false;
            sendCatalogSnapshot(ws, viewer);
            break;
          }

          case 'get_catalog': {
            sendCatalogSnapshot(ws, viewer);
            break;
          }

          case 'get_run_snapshot': {
            sendRunSnapshot(ws, msg.runId, viewer);
            break;
          }

          case 'list_runs': {
            sendCatalogSnapshot(ws, viewer);
            break;
          }

          case 'watch_chats': {
            sendChatCatalogSnapshot(ws, viewer);
            break;
          }

          case 'get_chat_catalog': {
            sendChatCatalogSnapshot(ws, viewer);
            break;
          }

          case 'subscribe_chat': {
            subscribeChat(ws, state, msg.chatId, viewer);
            break;
          }

          case 'unsubscribe_chat': {
            if (msg.chatId) clearChatSubscription(state, msg.chatId);
            safeSend(ws, { type: 'chat_unsubscribed', data: { chatId: msg.chatId || null } });
            break;
          }

          case 'get_chat_snapshot': {
            sendChatSnapshot(ws, msg.chatId, viewer);
            break;
          }

          case 'chat_start': {
            startChat({ ...(msg.payload || {}), viewer, ownerUserId: resolveOwnerId(viewer) })
              .then((result) => {
                safeSend(ws, {
                  type: 'chat_started',
                  data: {
                    chatId: result.chatId,
                    sessionId: result.sessionId || null,
                    originSessionId: result.originSessionId || result.sessionId || null,
                    currentSessionId: result.currentSessionId || null,
                    permissionMode: result.permissionMode || 'default',permissionMode: result.permissionMode || 'default',
                    harness: result.harness || 'claude',
                    cwd: result.cwd || null,
                    clientRequestId: msg.clientRequestId || null,
                  },
                });
                sendChatCatalogSnapshot(ws, viewer);
                subscribeChat(ws, state, result.chatId, viewer);
              })
              .catch((err) => {
                safeSend(ws, {
                  type: 'error',
                  data: { message: err.message || 'Failed to start chat', clientRequestId: msg.clientRequestId || null },
                }, { critical: true });
              });
            break;
          }

          case 'chat_send': {
            // Mirror the HTTP route: `viewer` gates the act (a foreign chat
            // throws CHAT_NOT_FOUND → refusal frame) and stamps ownership when
            // this call creates the session.
            sendChatMessage(msg.chatId, msg.message, {
              ...(msg.payload || {}),
              viewer,
              ownerUserId: resolveOwnerId(viewer),
            })
              .then((result) => {
                safeSend(ws, {
                  type: 'chat_sent',
                  data: {
                    chatId: result.chatId,
                    sessionId: result.sessionId || null,
                    originSessionId: result.originSessionId || result.sessionId || null,
                    currentSessionId: result.currentSessionId || null,
                    permissionMode: result.permissionMode || 'default',
                    cwd: result.cwd || null,
                    clientRequestId: msg.clientRequestId || null,
                  },
                });
                sendChatCatalogSnapshot(ws, viewer);
                subscribeChat(ws, state, result.chatId, viewer);
              })
              .catch((err) => {
                safeSend(ws, {
                  type: 'error',
                  data: { message: err.message || 'Failed to send chat message', chatId: msg.chatId || null, clientRequestId: msg.clientRequestId || null },
                }, { critical: true });
              });
            break;
          }

          case 'chat_stop': {
            const stopped = stopChat(msg.chatId, viewer);
            safeSend(ws, {
              type: 'chat_stopped',
              data: { chatId: msg.chatId, stopped },
            });
            sendChatCatalogSnapshot(ws, viewer);
            if (msg.chatId) sendChatSnapshot(ws, msg.chatId, viewer);
            break;
          }

          case 'run_chat': {
            // sendChatMessage is async: await it before acking, otherwise
            // `!!sent` is true for any Promise and a refused/failed send would
            // be reported as resumed (the pre-tenancy bug this handler had).
            Promise.resolve(sendDiagnosisChatMessage(msg.runId, msg.message || '', viewer))
              .then((sent) => {
                safeSend(ws, {
                  type: 'run_chat_ack',
                  data: { runId: msg.runId, resumed: !!sent },
                });
                if (!sent) {
                  // Foreign (or unknown) run → the same refusal as a failed send.
                  safeSend(ws, {
                    type: 'error',
                    data: { message: `Failed to send diagnosis chat message for run ${msg.runId}`, runId: msg.runId },
                  }, { critical: true });
                }
              })
              .catch((err) => {
                safeSend(ws, {
                  type: 'run_chat_ack',
                  data: { runId: msg.runId, resumed: false },
                });
                safeSend(ws, {
                  type: 'error',
                  data: { message: err.message || `Failed to send diagnosis chat message for run ${msg.runId}`, runId: msg.runId },
                }, { critical: true });
              });
            break;
          }

          case 'run_continue': {
            try {
              const result = continueDiagnosis(msg.runId, msg.followUpMessage || null, { viewer });
              safeSend(ws, {
                type: 'run_continue_ack',
                data: result,
              });
            } catch (err) {
              safeSend(ws, {
                type: 'error',
                data: { message: err.message || 'Failed to continue run', runId: msg.runId },
              }, { critical: true });
            }
            break;
          }

          case 'ping': {
            state.lastPongAt = Date.now();
            safeSend(ws, { type: 'pong', data: { ts: Date.now() } });
            break;
          }

          case 'pong': {
            state.lastPongAt = Date.now();
            break;
          }

          // NOTE: the old `hitl_respond` handler is gone with the HITL
          // registry. Approval is not interactive — `hitl_request` events are
          // informational notices emitted by the diagnosis service, and
          // dangerous commands are auto-approved by the SDK. An unknown
          // message type (incl. a legacy hitl_respond) gets the default error
          // frame below.

          default:
            safeSend(ws, {
              type: 'error',
              data: { message: `Unknown message type: ${msg.type}` },
            }, { critical: true });
        }
      } catch (err) {
        safeSend(ws, {
          type: 'error',
          data: { message: `Invalid message: ${err.message}` },
        }, { critical: true });
      }
    });

    ws.on('close', () => {
      logger.info(`Client disconnected: ${state.clientId} (remaining: ${wss ? wss.clients.size : 0})`, { context: 'WS' });
      if (state.heartbeatTimer) {
        clearInterval(state.heartbeatTimer);
        state.heartbeatTimer = null;
      }
      clearAllSubscriptions(state);
    });

    ws.on('error', (err) => {
      logger.error(`Connection error: ${err.message}`, { context: 'WS' });
    });

    // Handshake result — the client cannot use the socket until it lands.
    safeSend(ws, {
      type: 'welcome',
      data: {
        version: '2.0',
        activeRuns: activeRunsFor(viewer),
        capabilities: ['catalog_snapshot', 'run_snapshot', 'run_event', 'run_updated', 'chat_catalog_snapshot', 'chat_snapshot', 'chat_event'],
      },
    }, { critical: true });
  });

  logger.info('Server ready on path /ws', { context: 'WebSocket' });
  return wss;
}

export function getWSS() {
  return wss;
}

/** Close the WebSocket server (graceful shutdown). */
export function closeWebSocket() {
  if (!wss) return;
  for (const ws of wss.clients) {
    try { ws.close(1001, 'server shutting down'); } catch { /* already gone */ }
  }
  try { wss.close(); } catch { /* already closed */ }
  wss = null;
}
