// Diagnosis Engine — Central pub/sub event bus for diagnosis runs
// Decouples Claude Code process events from transport (WebSocket/SSE)

import { EventEmitter } from 'events';
import { engine as engineConfig } from '../../../../config/loader.mjs';
import logger from '../utils/logger.mjs';

const engine = new EventEmitter();

// Per-run state: { subscribers: Set<callback>, child: ChildProcess, events: [] }
const runs = new Map();

const MAX_EVENT_BUFFER = engineConfig.max_event_buffer;
const MAX_RUNS = 100;
const CLEANUP_INTERVAL = 5 * 60 * 1000; // 5 minutes

// Periodic cleanup: remove finished runs that have no active subscribers
setInterval(() => {
  if (runs.size <= MAX_RUNS) return;
  const finished = [];
  for (const [runId, run] of runs) {
    if (run.status === 'completed' || run.status === 'failed' || run.status === 'stopped') {
      if (run.subscribers.size === 0) finished.push(runId);
    }
  }
  for (const runId of finished) {
    runs.delete(runId);
  }
  if (finished.length > 0) logger.info(`Cleaned up ${finished.length} finished runs, ${runs.size} remaining`, { context: 'Engine' });
}, CLEANUP_INTERVAL);

export function createRun(runId) {
  if (runs.has(runId)) return;
  runs.set(runId, {
    subscribers: new Set(),
    child: null,
    events: [],
    status: 'pending',
    meta: {},
  });
}

export function resetRun(runId) {
  const existing = runs.get(runId);
  if (existing) {
    // Preserve events for SSE/WS subscribers and sessionId for resume
    existing.status = 'pending';
    existing.child = null;
    existing.meta = { sessionId: existing.meta.sessionId };
  } else {
    createRun(runId);
  }
}

export function setChild(runId, child) {
  const run = runs.get(runId);
  if (run) run.child = child;
}

export function getChild(runId) {
  return runs.get(runId)?.child ?? null;
}

export function setMeta(runId, meta) {
  const run = runs.get(runId);
  if (run) Object.assign(run.meta, meta);
}

export function getMeta(runId) {
  return runs.get(runId)?.meta ?? {};
}

export function updateStatus(runId, status) {
  const run = runs.get(runId);
  if (run) run.status = status;
}

export function getStatus(runId) {
  return runs.get(runId)?.status ?? null;
}

// Emit event to all subscribers AND buffer it
export function emit(runId, event) {
  const run = runs.get(runId);
  if (!run) return;

  const enriched = { ...event, _ts: Date.now(), _seq: run.events.length };

  run.events.push(enriched);
  if (run.events.length > MAX_EVENT_BUFFER) {
    run.events = run.events.slice(-MAX_EVENT_BUFFER);
  }

  for (const cb of run.subscribers) {
    try { cb(enriched); } catch (e) { logger.error(`Subscriber error: ${e.message}`, { context: 'Engine' }); }
  }

  engine.emit(`run:${runId}`, enriched);
  engine.emit('event', { runId, event: enriched });
}

export function subscribe(runId, callback) {
  const run = runs.get(runId);
  if (!run) return () => {};

  run.subscribers.add(callback);

  for (const event of run.events) {
    try { callback(event); } catch (e) { logger.error(`Replay error: ${e.message}`, { context: 'Engine' }); }
  }

  return () => {
    run.subscribers.delete(callback);
  };
}

export function getEvents(runId) {
  return runs.get(runId)?.events ?? [];
}

export function closeRun(runId) {
  const run = runs.get(runId);
  if (!run) return;

  for (const cb of run.subscribers) {
    try { cb({ type: 'stream_end', _ts: Date.now() }); } catch (e) { logger.error(`Close callback error: ${e.message}`, { context: 'Engine' }); }
  }

  run.subscribers.clear();
  runs.delete(runId);
  engine.emit('run:closed', runId);
}

export function hasRun(runId) {
  return runs.has(runId);
}

export function getActiveRuns() {
  return Array.from(runs.keys());
}

export default engine;
