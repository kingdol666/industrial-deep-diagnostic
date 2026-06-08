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
} from '../services/diagnosis.service.mjs';
import { hitlRequests } from '../services/diagnosis.service.mjs';
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
      watchCatalog: false,
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
}

function makeRunSummary(run) {
  return {
    runId: run.run_id,
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

  wss.on('connection', (ws) => {
    const state = getOrCreateState(ws);

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

          case 'ping': {
            safeSend(ws, { type: 'pong', data: {} });
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
        capabilities: ['catalog_snapshot', 'run_snapshot', 'run_event', 'run_updated'],
      },
    });
  });

  logger.info('Server ready on path /ws', { context: 'WebSocket' });
  return wss;
}

export function getWSS() {
  return wss;
}
