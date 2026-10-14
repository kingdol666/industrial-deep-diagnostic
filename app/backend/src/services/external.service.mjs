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
import { getWorkspaceReport, listWorkspaceHtml } from './files.service.mjs';
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
// Non-wait analyze returns a task_id; this registry owns the lifecycle. When
// a run reaches a terminal state the unified result (incl. report file paths)
// is built ONCE and stored in the entry, so later result queries are stable.
const TERMINAL = new Set(['completed', 'failed', 'stopped', 'interrupted']);
const tasks = new Map(); // task_id -> entry

function _rand4() {
  return Math.random().toString(36).slice(2, 6).toUpperCase();
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

/** Refresh one task entry from live run state; stores the result once. */
export async function refreshTask(taskId) {
  const e = tasks.get(taskId);
  if (!e) return null;
  const built = await buildExternalResult(e.run_id);
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

export function getTaskEntry(taskId) {
  return tasks.get(taskId) ?? null;
}

export function listTaskEntries() {
  return [...tasks.values()].map((e) => ({
    task_id: e.task_id, run_id: e.run_id, intent: e.intent,
    harness: e.harness, status: e.status, created_at: e.created_at,
  }));
}

export function chatWithRun(runId, message) {
  return sendChatMessage(runId, message);
}
