// WebSocket Server — enterprise-grade real-time diagnosis streaming
// Protocol: catalog snapshots + run snapshots + incremental run events

import { WebSocketServer } from 'ws';
import engine, {
  subscribe,
  getActiveRuns,
} from '../engine/diagnosis-engine.mjs';
import {
  listRuns,
  getRunRealtimeSnapshot,
  continueDiagnosis,
  sendChatMessage as sendDiagnosisChatMessage,
} from '../services/diagnosis.service.mjs';
import { hitlRequests } from '../services/diagnosis.service.mjs';
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

let wss = null;
const clientState = new WeakMap();

function safeSend(ws, payload) {
  if (!ws || ws.readyState !== ws.OPEN) return;
  ws.send(JSON.stringify(payload));
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

function sendCatalogSnapshot(ws) {
  const runs = listRuns().map(makeRunSummary);
  safeSend(ws, {
    type: 'catalog_snapshot',
    data: {
      runs,
      activeRuns: getActiveRuns(),
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

function sendChatCatalogSnapshot(ws) {
  const chats = listActiveChats().map(makeChatSummary);
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

function buildChatSnapshot(chatId) {
  const history = getChatHistory(chatId);
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
        cwd: history.session.cwd || null,
        createdAt: history.session.createdAt || null,
        updatedAt: history.session.updatedAt || null,
      },
      events: (history.messages || []).map((row, index) => mapChatMessageRowToWS(row, index + 1)),
    };
  }

  return null;
}

function sendChatSnapshot(ws, chatId) {
  const snapshot = buildChatSnapshot(chatId);
  if (!snapshot) {
    safeSend(ws, {
      type: 'error',
      data: { message: `Chat not found: ${chatId}`, chatId },
    });
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

function subscribeChat(ws, state, chatId) {
  clearChatSubscription(state, chatId);

  const snapshotExists = sendChatSnapshot(ws, chatId);
  if (!snapshotExists) return;

  const unsubscribe = subscribeChatEvents(chatId, (eventType, data) => {
    safeSend(ws, {
      type: 'chat_event',
      data: {
        chatId,
        event: mapChatEventForWS(eventType, data),
      },
    });
  });

  state.chatSubscriptions.set(chatId, { unsubscribe });
  safeSend(ws, {
    type: 'chat_subscribed',
    data: { chatId },
  });
}

function sendRunSnapshot(ws, runId) {
  const snapshot = getRunRealtimeSnapshot(runId);
  if (!snapshot) {
    safeSend(ws, {
      type: 'error',
      data: { message: `Run not found: ${runId}`, runId },
    });
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
      sentAt: new Date().toISOString(),
    },
  });
  return true;
}

function broadcastCatalogUpdate() {
  if (!wss) return;
  const runs = listRuns().map(makeRunSummary);
  const payload = {
    type: 'catalog_update',
    data: {
      runs,
      activeRuns: getActiveRuns(),
      sentAt: new Date().toISOString(),
    },
  };

  for (const ws of wss.clients) {
    const state = clientState.get(ws);
    if (state?.watchCatalog) safeSend(ws, payload);
  }
}

function broadcastRunStatusUpdate(runId, event) {
  if (!wss || event.type !== 'status') return;
  const snapshot = getRunRealtimeSnapshot(runId);
  if (!snapshot) return;

  const payload = {
    type: 'run_updated',
    data: {
      runId,
      run: snapshot.run,
      liveStatus: snapshot.liveStatus,
      hasActiveEngineRun: snapshot.hasActiveEngineRun,
      statusEvent: event,
      sentAt: new Date().toISOString(),
    },
  };

  for (const ws of wss.clients) {
    const state = clientState.get(ws);
    if (state?.watchCatalog) safeSend(ws, payload);
  }
}

function subscribeRun(ws, state, runId) {
  clearRunSubscription(state, runId);

  const snapshotExists = sendRunSnapshot(ws, runId);
  if (!snapshotExists) return;

  const unsubscribe = subscribe(runId, (event) => {
    safeSend(ws, {
      type: 'run_event',
      data: {
        runId,
        event,
      },
    });
  });

  state.subscriptions.set(runId, { unsubscribe });

  safeSend(ws, {
    type: 'subscribed',
    data: {
      runId,
      activeRuns: getActiveRuns(),
    },
  });
}

export function initWebSocket(httpServer) {
  wss = new WebSocketServer({ server: httpServer, path: '/ws' });

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
    const state = getOrCreateState(ws);
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
            subscribeRun(ws, state, msg.runId);
            break;
          }

          case 'unsubscribe_run': {
            if (msg.runId) clearRunSubscription(state, msg.runId);
            safeSend(ws, { type: 'unsubscribed', data: { runId: msg.runId || null } });
            break;
          }

          case 'watch_catalog': {
            state.watchCatalog = msg.enabled !== false;
            sendCatalogSnapshot(ws);
            break;
          }

          case 'get_catalog': {
            sendCatalogSnapshot(ws);
            break;
          }

          case 'get_run_snapshot': {
            sendRunSnapshot(ws, msg.runId);
            break;
          }

          case 'list_runs': {
            sendCatalogSnapshot(ws);
            break;
          }

          case 'watch_chats': {
            sendChatCatalogSnapshot(ws);
            break;
          }

          case 'get_chat_catalog': {
            sendChatCatalogSnapshot(ws);
            break;
          }

          case 'subscribe_chat': {
            subscribeChat(ws, state, msg.chatId);
            break;
          }

          case 'unsubscribe_chat': {
            if (msg.chatId) clearChatSubscription(state, msg.chatId);
            safeSend(ws, { type: 'chat_unsubscribed', data: { chatId: msg.chatId || null } });
            break;
          }

          case 'get_chat_snapshot': {
            sendChatSnapshot(ws, msg.chatId);
            break;
          }

          case 'chat_start': {
            startChat(msg.payload || {})
              .then((result) => {
                safeSend(ws, {
                  type: 'chat_started',
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
                sendChatCatalogSnapshot(ws);
                subscribeChat(ws, state, result.chatId);
              })
              .catch((err) => {
                safeSend(ws, {
                  type: 'error',
                  data: { message: err.message || 'Failed to start chat', clientRequestId: msg.clientRequestId || null },
                });
              });
            break;
          }

          case 'chat_send': {
            sendChatMessage(msg.chatId, msg.message, msg.payload || {})
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
                sendChatCatalogSnapshot(ws);
                subscribeChat(ws, state, result.chatId);
              })
              .catch((err) => {
                safeSend(ws, {
                  type: 'error',
                  data: { message: err.message || 'Failed to send chat message', chatId: msg.chatId || null, clientRequestId: msg.clientRequestId || null },
                });
              });
            break;
          }

          case 'chat_stop': {
            const stopped = stopChat(msg.chatId);
            safeSend(ws, {
              type: 'chat_stopped',
              data: { chatId: msg.chatId, stopped },
            });
            sendChatCatalogSnapshot(ws);
            if (msg.chatId) sendChatSnapshot(ws, msg.chatId);
            break;
          }

          case 'run_chat': {
            const sent = sendDiagnosisChatMessage(msg.runId, msg.message || '');
            safeSend(ws, {
              type: 'run_chat_ack',
              data: { runId: msg.runId, resumed: !!sent },
            });
            if (!sent) {
              safeSend(ws, {
                type: 'error',
                data: { message: `Failed to send diagnosis chat message for run ${msg.runId}`, runId: msg.runId },
              });
            }
            break;
          }

          case 'run_continue': {
            try {
              const result = continueDiagnosis(msg.runId, msg.followUpMessage || null);
              safeSend(ws, {
                type: 'run_continue_ack',
                data: result,
              });
            } catch (err) {
              safeSend(ws, {
                type: 'error',
                data: { message: err.message || 'Failed to continue run', runId: msg.runId },
              });
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

          case 'hitl_respond': {
            const { hitlId, approved } = msg;
            const entry = hitlRequests.get(hitlId);
            if (entry) {
              hitlRequests.delete(hitlId);
              entry.resolve(approved === true);
              safeSend(ws, {
                type: 'hitl_ack',
                data: { hitlId, approved: approved === true },
              });
            } else {
              safeSend(ws, {
                type: 'error',
                data: { message: `HITL request not found: ${hitlId}` },
              });
            }
            break;
          }

          default:
            safeSend(ws, {
              type: 'error',
              data: { message: `Unknown message type: ${msg.type}` },
            });
        }
      } catch (err) {
        safeSend(ws, {
          type: 'error',
          data: { message: `Invalid message: ${err.message}` },
        });
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

    safeSend(ws, {
      type: 'welcome',
      data: {
        version: '2.0',
        activeRuns: getActiveRuns(),
        capabilities: ['catalog_snapshot', 'run_snapshot', 'run_event', 'run_updated', 'chat_catalog_snapshot', 'chat_snapshot', 'chat_event'],
      },
    });
  });

  logger.info('Server ready on path /ws', { context: 'WebSocket' });
  return wss;
}

export function getWSS() {
  return wss;
}
