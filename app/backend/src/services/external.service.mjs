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
  getRunStatus, getDiagTaskView, sendChatMessage, getRunRealtimeSnapshot,
} from './diagnosis.service.mjs';
import { stmts } from '../db/database.mjs';
import { getWorkspaceReport, listWorkspaceHtml } from './files.service.mjs';
import { ANALYSIS_INTENTS } from '../engine/claude-client.mjs';
import logger from '../utils/logger.mjs';

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
 */
export async function buildExternalResult(runId) {
  const view = getDiagTaskView(runId);
  if (!view) return null;
  const run = getRunStatus(runId);
  const wsName = run?.workspace_path ? basename(run.workspace_path) : null;

  const out = {
    run_id: runId,
    status: view.status,
    run_status: view.run_status,
    name: view.name,
    scene: view.scene,
    harness: view.harness,
    analysis_mode: view.harness === 'mock' ? 'mock' : 'real',
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
      out.html_reports = (await listWorkspaceHtml(wsName)) ?? [];
    } catch { /* listing is best-effort for the unified view */ }
    if (view.status === 'completed') {
      try {
        const rep = await getWorkspaceReport(wsName);
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
// Non-wait analyze returns a task_id; this registry owns the lifecycle. The
// task_id -> run_id binding is also written to `external_tasks` so it survives
// a backend restart (plan v2 Phase C1); the Map remains the hot cache for
// progress counters and the one-shot result snapshot.
const TERMINAL = new Set(['completed', 'failed', 'stopped', 'interrupted', 'expired', 'awaiting_input']);
const tasks = new Map(); // task_id -> entry (hot cache; DB is the durable copy)

function _rand4() {
  return Math.random().toString(36).slice(2, 6).toUpperCase();
}

function _persistTaskStatus(taskId, status) {
  try {
    stmts.updateExternalTaskStatus.run({ taskId, status });
  } catch (err) {
    logger.warn(`external_tasks status update failed for ${taskId}: ${err.message}`, { context: 'External' });
  }
}

export function createTask(runId, { intent, harness, scene, objective }) {
  const task_id = `TASK-${Date.now().toString(36).toUpperCase()}-${_rand4()}`;
  const now = new Date().toISOString();
  const entry = {
    task_id,
    run_id: runId,
    intent,
    harness,
    // mock is an integration double, not a real analysis: callers must be able
    // to tell them apart without guessing from the harness name.
    analysis_mode: harness === 'mock' ? 'mock' : 'real',
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
  try {
    stmts.insertExternalTask.run({
      taskId: task_id,
      runId,
      intent: intent ?? null,
      harness: harness ?? null,
      scene: scene ?? null,
      objective: objective ?? null,
      status: 'accepted',
    });
  } catch (err) {
    logger.warn(`external_tasks insert failed for ${task_id}: ${err.message}`, { context: 'External' });
  }
  return entry;
}

/**
 * Rehydrate a task entry from DB after a restart. Status is re-derived from the
 * run row (the run is the source of truth), so a task whose run completed while
 * the process was down answers with the real terminal state.
 */
function hydrateTask(taskId) {
  const row = stmts.getExternalTask.get(taskId);
  if (!row) return null;
  const run = stmts.getRunById.get(row.run_id);
  if (!run) return null;
  const status = run.status === 'pending' ? row.status : run.status;
  const entry = {
    task_id: row.task_id,
    run_id: row.run_id,
    intent: row.intent,
    harness: row.harness,
    analysis_mode: row.harness === 'mock' ? 'mock' : 'real',
    scene: row.scene,
    objective: row.objective,
    status,
    created_at: row.created_at,
    started_at: null,
    finished_at: run.completed_at || null,
    progress: { events: 0, tools: 0, phase: TERMINAL.has(status) ? 'completed' : 'awaiting' },
    links: {
      task: `/api/external/v1/tasks/${row.task_id}`,
      result: `/api/external/v1/tasks/${row.task_id}/result`,
      stream: `/api/external/v1/analyze/${encodeURIComponent(row.run_id)}/stream`,
      status: `/api/external/v1/analyze/${encodeURIComponent(row.run_id)}`,
    },
    result: null,
    error: run.error_message || null,
    rehydrated: true,
  };
  tasks.set(taskId, entry);
  return entry;
}

function _runningTaskFor(runId) {
  for (const e of tasks.values()) {
    if (e.run_id === runId) return e;
  }
  return null;
}

export function getTaskByRun(runId) {
  const live = _runningTaskFor(runId);
  if (live) return live;
  const row = stmts.getExternalTaskByRun.get(runId);
  return row ? hydrateTask(row.task_id) : null;
}

/** Refresh one task entry from live run state; stores the result once. */
export async function refreshTask(taskId) {
  const e = tasks.get(taskId) || hydrateTask(taskId);
  if (!e) return null;
  const built = await buildExternalResult(e.run_id);
  if (!built) {
    e.status = 'failed';
    e.error = 'run not found';
    _persistTaskStatus(taskId, e.status);
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
      // Same artifact manifest object the tasks view carries (AR-01 同源).
      artifacts: built.result?.artifacts ?? null,
    };
    if (built.result?.error) e.error = built.result.error;
  }
  _persistTaskStatus(taskId, e.status);

  // Progress counters must also be refreshed AFTER the run reaches a terminal
  // state: a task polled for the first time only after completion used to keep
  // events=0/tools=0 forever (the counters were only updated in the live
  // branch). The snapshot is the same source for both branches.
  const snap = getRunRealtimeSnapshot(e.run_id);
  if (snap) {
    const events = Array.isArray(snap.events) ? snap.events : [];
    e.progress.events = events.length;
    e.progress.tools = events.filter((ev) =>
      String(ev?.type || '').includes('tool') || ev?.tool_use_id).length;
    e.progress.phase = TERMINAL.has(e.status)
      ? 'completed'
      : (snap.hasActiveEngineRun ? 'executing' : 'awaiting');
    const last = events[events.length - 1];
    e.progress.last_event = last ? String(last.type || last.event || 'event') : e.progress.last_event;
  }
  return e;
}

export function getTaskEntry(taskId) {
  return tasks.get(taskId) ?? hydrateTask(taskId);
}

export function listTaskEntries() {
  // Durable rows first (survive restarts), overlaid with live cache status.
  const rows = stmts.listExternalTasks.all({ limit: 200 });
  const liveStatus = new Map([...tasks.values()].map((e) => [e.task_id, e.status]));
  const seen = new Set();
  const out = rows.map((row) => {
    seen.add(row.task_id);
    return {
      task_id: row.task_id, run_id: row.run_id, intent: row.intent,
      harness: row.harness,
      analysis_mode: row.harness === 'mock' ? 'mock' : 'real',
      status: liveStatus.get(row.task_id) || row.status,
      created_at: row.created_at,
    };
  });
  for (const e of tasks.values()) {
    if (seen.has(e.task_id)) continue;
    out.push({
      task_id: e.task_id, run_id: e.run_id, intent: e.intent,
      harness: e.harness,
      analysis_mode: e.harness === 'mock' ? 'mock' : 'real',
      status: e.status, created_at: e.created_at,
    });
  }
  return out;
}

export function chatWithRun(runId, message, options = {}) {
  return sendChatMessage(runId, message, options);
}
