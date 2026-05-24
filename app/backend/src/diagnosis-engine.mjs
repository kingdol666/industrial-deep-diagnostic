// Diagnosis Engine — Central pub/sub event bus for diagnosis runs
// Decouples Claude Code process events from transport (WebSocket/SSE)

import { EventEmitter } from 'events';

const engine = new EventEmitter();

// Per-run state: { subscribers: Set<callback>, child: ChildProcess, events: [] }
const runs = new Map();

const MAX_EVENT_BUFFER = 500;

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
    existing.events = [];
    existing.status = 'pending';
    existing.child = null;
    existing.meta = {};
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

  // Add timestamp
  const enriched = { ...event, _ts: Date.now(), _seq: run.events.length };

  // Buffer (circular)
  run.events.push(enriched);
  if (run.events.length > MAX_EVENT_BUFFER) {
    run.events = run.events.slice(-MAX_EVENT_BUFFER);
  }

  // Broadcast to all subscribers
  for (const cb of run.subscribers) {
    try { cb(enriched); } catch {}
  }

  // Also emit on the global engine for monitoring
  engine.emit(`run:${runId}`, enriched);
  engine.emit('event', { runId, event: enriched });
}

// Subscribe to run events — callback receives enriched event objects
// Returns an unsubscribe function
export function subscribe(runId, callback) {
  const run = runs.get(runId);
  if (!run) return () => {};

  run.subscribers.add(callback);

  // Replay buffered events for late joiners
  for (const event of run.events) {
    try { callback(event); } catch {}
  }

  return () => {
    run.subscribers.delete(callback);
  };
}

// Get all buffered events (for status/polling fallback)
export function getEvents(runId) {
  return runs.get(runId)?.events ?? [];
}

export function closeRun(runId) {
  const run = runs.get(runId);
  if (!run) return;

  // Notify subscribers
  for (const cb of run.subscribers) {
    try { cb({ type: 'stream_end', _ts: Date.now() }); } catch {}
  }

  run.subscribers.clear();
  runs.delete(runId);
  engine.emit(`run:closed`, runId);
}

export function hasRun(runId) {
  return runs.has(runId);
}

export function getActiveRuns() {
  return Array.from(runs.keys());
}

export default engine;
