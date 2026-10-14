// External API service — stable integration surface for outside callers.
//
// Composes the internal diagnosis/files services into an integration-first
// contract: capability discovery (intents + harnesses), one-shot analysis
// launching, unified result views (status + score/verdict + report markdown +
// html artifact list) and run-scoped chat relay. Auth is inherited from the
// global authGuard (session JWT or idd_ API token).
import { basename } from 'path';

import {
  getRunStatus, getDiagTaskView, sendChatMessage,
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
  return out;
}

export function chatWithRun(runId, message) {
  return sendChatMessage(runId, message);
}
