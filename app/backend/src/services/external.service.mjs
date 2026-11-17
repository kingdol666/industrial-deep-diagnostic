// External API service — stable integration surface for outside callers.
//
// Composes the internal diagnosis/files services into an integration-first
// contract: capability discovery (intents + harnesses), one-shot analysis
// launching, unified result views (status + score/verdict + report markdown +
// html artifact list) and run-scoped chat relay. Auth is inherited from the
// global authGuard (session JWT or idd_ API token).
import { basename, join } from 'path';

import { PROJECT_ROOT } from '../../../../config/loader.mjs';
import {
  getRunStatus, getDiagTaskView, sendChatMessage, getRunRealtimeSnapshot, canViewRun,
} from './diagnosis.service.mjs';
import { getWorkspaceReport, listWorkspaceHtml } from './files.service.mjs';
import { INTERNAL } from './tenancy.mjs';
import { ANALYSIS_INTENTS } from '../engine/claude-client.mjs';

// Modes an external caller can request, with the skill each one executes.
export function listIntents() {
  return Object.entries(ANALYSIS_INTENTS).map(([intent, spec]) => ({
    intent,
    skill: intent === 'deep-diagnosis' ? 'industrial-analysis-auto' : (spec?.skill ?? null),
    default: intent === 'deep-diagnosis',
  }));
}

export function findIntent(intent) {
  return Object.prototype.hasOwnProperty.call(ANALYSIS_INTENTS, String(intent))
    ? String(intent) : null;
}

export function externalLinks(runId) {
  const base = `/api/external/v1/analyze/${encodeURIComponent(runId)}`;
  return {
    status: base,
    result: base,
    stream: `${base}/stream`,
    report_md: `/api/files/workspace/report/${encodeURIComponent(runId)}`,
  };
}

/**
 * Unified result view for a run: identity + live status; when terminal also
 * score/verdict/summary, the full report markdown, and every HTML artifact
 * found in the run workspace (whatever skill produced it).
 *
 * `viewer` binds the view to the API token's user: a run the caller may not
 * see is indistinguishable from a missing one (null → route 404).
 */
export async function buildExternalResult(runId, viewer = INTERNAL) {
  if (!canViewRun(runId, viewer)) return null;
  const view = getDiagTaskView(runId, viewer);
  if (!view) return null;
  const run = getRunStatus(runId, viewer);
  const wsName = run?.workspace_path ? basename(run.workspace_path) : null;

  const out = {
    run_id: runId,
    status: view.status,
    run_status: view.run_status,
    name: view.name,
    scene: view.scene,
    harness: view.harness,
    intent: run?.analysis_intent ?? null,
    objective: run?.user_question || null,
    created_at: view.created_at,
    finished_at: view.finished_at,
    workspace: run?.workspace_path ?? null,
    links: externalLinks(runId),
    result: null,
    html_reports: [],
  };

  if (view.result) out.result = { ...view.result };

  if (wsName) {
    try {
      out.html_reports = (await listWorkspaceHtml(wsName, viewer)) ?? [];
    } catch { /* listing is best-effort for the unified view */ }
    if (view.status === 'completed') {
      try {
        const rep = await getWorkspaceReport(wsName, viewer);
        if (rep?.content) {
          out.result = out.result || {};
          out.result.report_md = rep.content;
        }
      } catch { /* report.md optional in the unified view */ }
    }
  }
  if (out.result && wsName) {
    out.result.report_md_url =
      `/api/files/workspace/report/${encodeURIComponent(wsName)}`;
  }
  // Concrete file locations for every report artifact (md + html), both as
  // on-disk absolute paths and as token-authenticated API URLs.
  const htmlList = Array.isArray(out.html_reports) ? out.html_reports : [];
  out.files = {
    workspace_path: run?.workspace_path ?? null,
    report_md_path: run?.report_path
      ? join(PROJECT_ROOT, run.report_path) : null,
    report_md_url: out.result?.report_md_url ?? null,
    html: htmlList.map((rel) => ({
      path: rel,
      abs_path: join(PROJECT_ROOT, 'workspace', 'diagnostic-runs', wsName || '', rel),
      url: `/api/files/workspace/asset/${encodeURIComponent(wsName || '')}/${rel}`,
    })),
  };
  return out;
}

// ── Task manager ────────────────────────────────────────────────────────────
// Non-wait analyze returns a task_id; this registry owns the lifecycle. When
// a run reaches a terminal state the unified result (incl. report file paths)
// is built ONCE and stored in the entry, so later result queries are stable.
//
// The registry is bounded: terminal entries are pruned on every task creation
// (older than TASK_TTL_MS) and the map is hard-capped at TASK_MAX_ENTRIES by
// evicting the oldest terminal entries first. Non-terminal (accepted/queued/
// running) entries are NEVER evicted — a caller polling a live task must
// always find it.
const TERMINAL = new Set(['completed', 'failed', 'stopped', 'interrupted']);
const tasks = new Map(); // task_id -> entry
const TASK_MAX_ENTRIES = 200;
const TASK_TTL_MS = 24 * 60 * 60 * 1000; // terminal entries older than 24h

function _rand4() {
  return Math.random().toString(36).slice(2, 6).toUpperCase();
}

/** Timestamp an entry is aged by: finished_at, else created_at, else 0. */
function _entryTime(e) {
  return Date.parse(e.finished_at || e.created_at || '') || 0;
}

/**
 * Prune terminal tasks older than TASK_TTL_MS, then enforce the hard cap by
 * evicting the oldest terminal entries. Never touches non-terminal entries;
 * when nothing evictable remains (all entries live) the map may briefly exceed
 * the cap — correctness for live tasks beats the cap.
 */
export function evictStaleTasks(now = Date.now()) {
  for (const [id, e] of tasks) {
    if (!TERMINAL.has(e.status)) continue;
    const ts = _entryTime(e);
    if (ts && now - ts > TASK_TTL_MS) tasks.delete(id);
  }
  while (tasks.size > TASK_MAX_ENTRIES) {
    let oldestId = null;
    let oldestTs = Infinity;
    for (const [id, e] of tasks) {
      if (!TERMINAL.has(e.status)) continue;
      const ts = _entryTime(e);
      if (ts < oldestTs) { oldestTs = ts; oldestId = id; }
    }
    if (!oldestId) break; // only non-terminal entries left — nothing to evict
    tasks.delete(oldestId);
  }
  return tasks.size;
}

/** Registry size — introspection for tests / ops. */
export function taskRegistrySize() {
  return tasks.size;
}

export function createTask(runId, { intent, harness, scene, objective }) {
  const task_id = `TASK-${Date.now().toString(36).toUpperCase()}-${_rand4()}`;
  const now = new Date().toISOString();
  const entry = {
    task_id,
    run_id: runId,
    intent,
    harness,
    scene: scene ?? null,
    objective: objective ?? null,
    status: 'accepted',
    created_at: now,
    started_at: null,
    finished_at: null,
    progress: { events: 0, tools: 0, phase: 'queued' },
    links: {
      task: `/api/external/v1/tasks/${task_id}`,
      result: `/api/external/v1/tasks/${task_id}/result`,
      stream: `/api/external/v1/analyze/${encodeURIComponent(runId)}/stream`,
      status: `/api/external/v1/analyze/${encodeURIComponent(runId)}`,
    },
    result: null,
    error: null,
  };
  tasks.set(task_id, entry);
  // Prune + cap AFTER inserting, so the registry never holds more than
  // TASK_MAX_ENTRIES while an evictable (terminal) entry exists.
  evictStaleTasks();
  return entry;
}

function _runningTaskFor(runId) {
  for (const e of tasks.values()) {
    if (e.run_id === runId) return e;
  }
  return null;
}

export function getTaskByRun(runId) {
  return _runningTaskFor(runId);
}

/**
 * Refresh one task entry from live run state; stores the result once.
 * `viewer` binds the task to the API token's user: a task whose run the caller
 * may not see is null (route 404) — no cross-token task visibility.
 */
export async function refreshTask(taskId, viewer = INTERNAL) {
  const e = tasks.get(taskId);
  if (!e) return null;
  if (!canViewRun(e.run_id, viewer)) return null;
  const built = await buildExternalResult(e.run_id, viewer);
  if (!built) {
    e.status = 'failed';
    e.error = 'run not found';
    return e;
  }
  e.status = built.status === 'running' ? 'running' : built.status;
  if (e.status === 'running' && !e.started_at) e.started_at = built.created_at ?? e.started_at;
  if (TERMINAL.has(e.status)) {
    e.finished_at = built.finished_at ?? new Date().toISOString();
    if (!e.result) e.result = {
      summary: built.result?.summary ?? null,
      verdict: built.result?.verdict ?? null,
      score: built.result?.score ?? null,
      report_md: built.result?.report_md ?? null,
      files: built.files ?? null,
    };
    if (built.result?.error) e.error = built.result.error;
  } else {
    // live progress from the run's realtime snapshot (event-stream counters)
    const snap = getRunRealtimeSnapshot(e.run_id);
    if (snap) {
      const events = Array.isArray(snap.events) ? snap.events : [];
      e.progress.events = events.length;
      e.progress.tools = events.filter((ev) =>
        String(ev?.type || '').includes('tool') || ev?.tool_use_id).length;
      e.progress.phase = snap.hasActiveEngineRun ? 'executing' : 'awaiting';
      const last = events[events.length - 1];
      e.progress.last_event = last ? String(last.type || last.event || 'event') : e.progress.last_event;
    }
  }
  return e;
}

export function getTaskEntry(taskId, viewer = INTERNAL) {
  const e = tasks.get(taskId) ?? null;
  if (!e) return null;
  if (!canViewRun(e.run_id, viewer)) return null;
  return e;
}

/** Task index for a token: only tasks whose run the caller may see. */
export function listTaskEntries(viewer = INTERNAL) {
  return [...tasks.values()]
    .filter((e) => canViewRun(e.run_id, viewer))
    .map((e) => ({
      task_id: e.task_id, run_id: e.run_id, intent: e.intent,
      harness: e.harness, status: e.status, created_at: e.created_at,
    }));
}

/**
 * Run-scoped chat relay for external callers.
 * @returns {{ok:true}|{ok:false, reason:'not_found'|'unavailable'}} — not_found
 * (foreign or missing run) must be answered 404, unavailable (no live engine)
 * keeps the historical 409.
 */
export async function chatWithRun(runId, message, viewer = INTERNAL) {
  if (!canViewRun(runId, viewer)) return { ok: false, reason: 'not_found' };
  const sent = await sendChatMessage(runId, message, viewer);
  return sent ? { ok: true } : { ok: false, reason: 'unavailable' };
}
