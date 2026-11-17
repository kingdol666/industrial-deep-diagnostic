// Diagnosis Engine — Central pub/sub event bus for diagnosis runs
// Decouples Claude Code process events from transport (WebSocket/SSE)

import { EventEmitter } from 'events';
import { engine as engineConfig } from '../../../../config/loader.mjs';
import { stmts } from '../db/database.mjs';
import logger from '../utils/logger.mjs';

const engine = new EventEmitter();

// Per-run state: { subscribers: Set<callback>, child: ChildProcess, events: [] }
const runs = new Map();

const MAX_EVENT_BUFFER = engineConfig.max_event_buffer;
const MAX_RUNS = 100;
const CLEANUP_INTERVAL = 5 * 60 * 1000; // 5 minutes

// ─── Stall watchdog (plan phase 5.4) ────────────────────────────────────────
// A run marked `running` that stops producing events is the one failure mode no
// other layer notices: no error, no completion — just silence (a hung engine
// subprocess, a wedged session). `emit()` below is the single choke point every
// run event flows through, so it stamps `lastEventTs`; the sweep warns once per
// idle window and leaves an informational `run_stalled` event on the run's own
// stream. Terminal runs never warn, and their watchdog state dies with the run
// record (closeRun) — see classifyStall for the exact rules.
const DEFAULT_STALL_WARN_MINUTES = 10;
const STALL_CHECK_INTERVAL = 60 * 1000; // 1 minute — finer than the default 10-min threshold

/** engine.stall_warn_minutes (>0; 0 disables the watchdog). */
function stallWarnMinutes() {
  const configured = Number(engineConfig?.stall_warn_minutes);
  return Number.isFinite(configured) && configured >= 0 ? configured : DEFAULT_STALL_WARN_MINUTES;
}

/**
 * Pure stall decision for one run — extracted so the semantics are
 * unit-testable without timers or the event bus.
 *
 * Rules:
 *   · only `running` runs are stall-eligible (a pending/queued wait and
 *     `awaiting_input` are legitimate, terminal statuses never warn);
 *   · no trustworthy last-event timestamp, an idle span below the threshold,
 *     or a non-positive threshold → no stall;
 *   · an idle window that already warned (`lastWarnedFor >= lastEventTs`)
 *     cannot warn again — only real activity (a larger lastEventTs) re-arms it.
 *
 * @param {{status?:string, lastEventTs?:number|null, now:number,
 *          thresholdMinutes?:number, lastWarnedFor?:number|null}} params
 * @returns {{stalled:boolean, mark:number|null, idleMs:number|null}}
 *   `mark` = the lastEventTs this decision was taken on; a stalled caller
 *   stores it as `lastWarnedFor` to disarm the same idle window.
 */
export function classifyStall({
  status,
  lastEventTs,
  now,
  thresholdMinutes = DEFAULT_STALL_WARN_MINUTES,
  lastWarnedFor = null,
}) {
  const thresholdMs = Number(thresholdMinutes) * 60_000;
  const idleMs = Number.isFinite(lastEventTs) ? Math.max(0, now - lastEventTs) : null;
  if (status !== 'running') return { stalled: false, mark: null, idleMs };
  if (idleMs === null) return { stalled: false, mark: null, idleMs };
  if (!(thresholdMs > 0)) return { stalled: false, mark: null, idleMs };
  if (idleMs < thresholdMs) return { stalled: false, mark: null, idleMs };
  if (Number.isFinite(lastWarnedFor) && lastWarnedFor >= lastEventTs) {
    return { stalled: false, mark: null, idleMs };
  }
  return { stalled: true, mark: lastEventTs, idleMs };
}

/**
 * One stall sweep over the live run map. Exported so the interval below is not
 * the only way to run it (tests drive it with an explicit `now` instead of
 * waiting for the tick).
 */
export function sweepStalledRuns(now = Date.now()) {
  const thresholdMinutes = stallWarnMinutes();
  for (const [runId, run] of runs) {
    const verdict = classifyStall({
      status: run.status,
      lastEventTs: run.lastEventTs,
      now,
      thresholdMinutes,
      lastWarnedFor: run.lastWarnedFor,
    });
    if (!verdict.stalled) continue;

    const idleMinutes = Math.round((verdict.idleMs || 0) / 60_000);
    logger.warn(
      `Run appears stalled — status=running, no event for ${idleMinutes} min (threshold ${thresholdMinutes} min)`,
      { context: 'Engine', runId, idleMinutes },
    );

    // Informational notice on the run's own stream so the console can show why
    // nothing is moving. It is NOT engine activity (`activity: false`): the
    // notice must not re-arm the idle clock or the already-warned window — only
    // real events do (lastWarnedFor is pinned to the anchor left intact).
    emit(runId, {
      type: 'run_stalled',
      data: {
        runId,
        status: run.status,
        idleMinutes,
        thresholdMinutes,
        message: `运行已 ${idleMinutes} 分钟没有新事件（阈值 ${thresholdMinutes} 分钟），可能卡在引擎子进程或会话等待中。`,
      },
    }, { activity: false });
    run.lastWarnedFor = run.lastEventTs;
  }
}

// Periodic cleanup: remove finished runs that have no active subscribers.
// unref'd on purpose — housekeeping must never keep a host process alive
// (in-process test runners importing this module would otherwise hang until
// the 5-minute tick; the HTTP/WS server keeps production alive anyway).
const cleanupInterval = setInterval(() => {
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
cleanupInterval.unref?.();

// Stall sweep — same unref rule as the cleanup tick above.
const stallInterval = setInterval(() => sweepStalledRuns(), STALL_CHECK_INTERVAL);
stallInterval.unref?.();

export function createRun(runId) {
  if (runs.has(runId)) return;
  runs.set(runId, {
    subscribers: new Set(),
    child: null,
    events: [],
    status: 'pending',
    meta: {},
    nextSeq: 0,
    // Stall watchdog state: the idle clock starts at creation and every emit()
    // below moves it forward; `lastWarnedFor` disarms an already-warned window.
    lastEventTs: Date.now(),
    lastWarnedFor: null,
  });
}

export function resetRun(runId) {
  const existing = runs.get(runId);
  if (existing) {
    // Preserve events for SSE/WS subscribers and sessionId for resume
    existing.status = 'pending';
    existing.child = null;
    existing.meta = { ...existing.meta };
    existing.nextSeq = existing.nextSeq ?? existing.events.length;
    // A reopened run starts a fresh idle window.
    existing.lastEventTs = Date.now();
    existing.lastWarnedFor = null;
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
  if (!run || run.status === status) return;
  run.status = status;
  // Stall bookkeeping is per status window: a run that becomes `running`
  // starts its idle clock now (a long pending/queued wait is not a stall) and
  // a run leaving `running` clears the window, so a later resume warns afresh.
  run.lastEventTs = Date.now();
  run.lastWarnedFor = null;
}

export function getStatus(runId) {
  return runs.get(runId)?.status ?? null;
}

// Emit event to all subscribers AND buffer it.
// `activity` (default true): does this event count as engine progress for the
// stall watchdog? Only the watchdog's own informational notices pass false —
// they must neither re-arm the idle clock nor the already-warned window.
export function emit(runId, event, { activity = true } = {}) {
  const run = runs.get(runId);
  if (!run) return;

  const seq = run.nextSeq ?? run.events.length;
  run.nextSeq = seq + 1;

  const enriched = { ...event, _ts: Date.now(), _seq: seq };

  // Stall watchdog choke point: a real event (from any engine or the service
  // layer) moves the idle clock forward. A warned window is left disarmed
  // until this happens (a production anchor is ≥ threshold old, so a later
  // real event always carries a strictly larger timestamp).
  if (activity) run.lastEventTs = enriched._ts;

  run.events.push(enriched);
  if (run.events.length > MAX_EVENT_BUFFER) {
    run.events = run.events.slice(-MAX_EVENT_BUFFER);
  }

  if (event.type !== 'stream_end') {
    try {
      stmts.insertEventStream.run({
        runId,
        seq: enriched._seq,
        eventType: enriched.type || 'unknown',
        eventSubtype: enriched.subtype || null,
        payloadJson: JSON.stringify({
          type: enriched.type,
          subtype: enriched.subtype || null,
          data: enriched.data ?? null,
          ts: enriched._ts,
          seq: enriched._seq,
        }),
      });
    } catch (err) {
      logger.error(`Failed to persist diagnosis event: ${err.message}`, {
        context: 'Engine',
        runId,
      });
    }
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
  return Array.from(runs.entries())
    .filter(([, run]) => run.status === 'running' || run.status === 'awaiting_input')
    .map(([runId]) => runId);
}

export default engine;
