// WebSocket Server — Real-time diagnosis event streaming
// Clients subscribe to specific run channels and receive typed events

import { WebSocketServer } from 'ws';
import { subscribe, getEvents, getStatus, getActiveRuns, hasRun } from '../engine/diagnosis-engine.mjs';
import { hitlRequests } from '../services/diagnosis.service.mjs';

let wss = null;

export function initWebSocket(httpServer) {
  wss = new WebSocketServer({ server: httpServer, path: '/ws' });

  wss.on('connection', (ws) => {
    let subscribedRunId = null;
    let unsubscribe = null;

    ws.on('message', (raw) => {
      try {
        const msg = JSON.parse(raw.toString());

        switch (msg.type) {
          case 'subscribe': {
            // Unsubscribe from previous run first
            if (unsubscribe) unsubscribe();

            const { runId } = msg;
            subscribedRunId = runId;

            if (!hasRun(runId)) {
              ws.send(JSON.stringify({
                type: 'error',
                data: { message: `Run not found: ${runId}`, runId },
              }));
              return;
            }

            unsubscribe = subscribe(runId, (event) => {
              if (ws.readyState === ws.OPEN) {
                ws.send(JSON.stringify(event));
              }
            });

            const events = getEvents(runId);
            ws.send(JSON.stringify({
              type: 'connected',
              data: { runId, status: getStatus(runId), bufferedEventCount: events.length },
            }));

            break;
          }

          case 'unsubscribe': {
            if (unsubscribe) {
              unsubscribe();
              unsubscribe = null;
            }
            subscribedRunId = null;
            ws.send(JSON.stringify({ type: 'unsubscribed', data: {} }));
            break;
          }

          case 'list_runs': {
            ws.send(JSON.stringify({
              type: 'active_runs',
              data: { runs: getActiveRuns() },
            }));
            break;
          }

          case 'ping': {
            ws.send(JSON.stringify({ type: 'pong', data: {} }));
            break;
          }

          case 'hitl_respond': {
            const { hitlId, approved } = msg;
            const entry = hitlRequests.get(hitlId);
            if (entry) {
              hitlRequests.delete(hitlId);
              entry.resolve(approved === true);
              ws.send(JSON.stringify({
                type: 'hitl_ack',
                data: { hitlId, approved: approved === true },
              }));
            } else {
              ws.send(JSON.stringify({
                type: 'error',
                data: { message: `HITL request not found: ${hitlId}` },
              }));
            }
            break;
          }

          default:
            ws.send(JSON.stringify({
              type: 'error',
              data: { message: `Unknown message type: ${msg.type}` },
            }));
        }
      } catch (err) {
        ws.send(JSON.stringify({
          type: 'error',
          data: { message: `Invalid message: ${err.message}` },
        }));
      }
    });

    ws.on('close', () => {
      if (unsubscribe) {
        unsubscribe();
        unsubscribe = null;
      }
    });

    ws.on('error', () => {});

    ws.send(JSON.stringify({
      type: 'welcome',
      data: { version: '1.0', activeRuns: getActiveRuns() },
    }));
  });

  console.log(`[WebSocket] Server ready on path /ws`);
  return wss;
}

export function getWSS() {
  return wss;
}
