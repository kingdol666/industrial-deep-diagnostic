import i18n from '../i18n/index.js';

export function normalizeRunSummary(run) {
  if (!run) return null;

  return {
    ...run,
    run_id: run.run_id || run.runId || null,
    session_id: run.session_id || run.sessionId || null,
    scene_name: run.scene_name || run.sceneName || '',
    judge_verdict: run.judge_verdict || run.verdict || null,
    report_path: run.report_path || run.reportPath || null,
    workspace_path: run.workspace_path || run.workspacePath || null,
    error_message: run.error_message || run.errorMessage || null,
    engineStatus: run.engineStatus || run.liveStatus || run.status || 'pending',
    created_at: run.created_at || run.createdAt || null,
    completed_at: run.completed_at || run.completedAt || null,
  };
}

export function getEffectiveRunStatus(run) {
  const normalized = normalizeRunSummary(run);
  return normalized?.engineStatus || normalized?.status || 'pending';
}

/**
 * Map a run status to an i18n key suffix.
 * Statuses not in the map fall back to 'unknown'.
 */
function statusKey(status) {
  const keys = ['completed', 'running', 'awaiting_input', 'pending', 'failed', 'stopped', 'expired', 'in_progress', 'draft', 'active'];
  return keys.includes(status) ? status : 'unknown';
}

export function getRunStatusLabel(runOrStatus) {
  const status = typeof runOrStatus === 'string'
    ? runOrStatus
    : getEffectiveRunStatus(runOrStatus);
  return i18n.global.t(`status.${statusKey(status)}`);
}

export function getRunStatusBadgeClass(runOrStatus) {
  const status = typeof runOrStatus === 'string'
    ? runOrStatus
    : getEffectiveRunStatus(runOrStatus);

  switch (status) {
    case 'completed': return 'badge-green';
    case 'running': return 'badge-blue';
    case 'awaiting_input': return 'badge-purple';
    // pending / stopped / expired are not warnings: a queued run, a deliberate
    // stop and an orphaned never-executed run all stay neutral so amber keeps
    // its meaning (live) and red keeps failure. Before this, a 100-row task
    // list rendered twenty amber PENDING chips and the accent meant nothing.
    case 'pending': return 'badge-neutral';
    case 'failed': return 'badge-red';
    case 'stopped': return 'badge-neutral';
    case 'expired': return 'badge-neutral';
    default: return '';
  }
}

export function getRunWorkspaceName(run) {
  const normalized = normalizeRunSummary(run);
  if (!normalized) return '';

  const reportPath = normalized.report_path || '';
  if (reportPath.includes('/')) {
    return reportPath.split('/').slice(-2, -1)[0] || '';
  }

  const workspacePath = normalized.workspace_path || '';
  if (workspacePath.includes('/')) {
    return workspacePath.split('/').pop() || '';
  }

  if (normalized.name) return normalized.name;
  return '';
}

export function isTerminalRunStatus(runOrStatus) {
  const status = typeof runOrStatus === 'string'
    ? runOrStatus
    : getEffectiveRunStatus(runOrStatus);
  return ['completed', 'failed', 'stopped'].includes(status);
}

const ERROR_DISPLAY_MAX = 140;

function tryParseJsonObject(text) {
  if (!text.startsWith('{') && !text.startsWith('[')) return null;
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

/**
 * Human-readable one-line rendering of a failed run's error_message. Raw
 * values often look like `Query stopped: {"error":{"message":"..."}}` — a
 * JSON blob unusable in a table cell. Extract the nested message, keep the
 * upstream HTTP status when the text carries one, then truncate for display;
 * the full text stays available to the row via the title attribute.
 */
export function formatRunErrorMessage(raw) {
  if (raw == null) return '';
  let text = String(raw).trim();
  if (!text) return '';

  // Strip a leading transport prefix, e.g. `Query stopped: {...}`.
  text = text.replace(/^Query stopped:\s*/i, '');

  // Prefer the human message nested inside a JSON error blob.
  const parsed = tryParseJsonObject(text);
  if (parsed && typeof parsed === 'object') {
    const nested = parsed.error && typeof parsed.error === 'object' ? parsed.error.message : null;
    const message = typeof nested === 'string' && nested.trim() ? nested : parsed.message;
    if (typeof message === 'string' && message.trim()) text = message.trim();
  }

  // Keep the upstream status visible when the message references it.
  const statusMatch = text.match(/upstream_status: HTTP (\d+)/);
  if (statusMatch) text = `HTTP ${statusMatch[1]}: ${text}`;

  if (text.length > ERROR_DISPLAY_MAX) {
    text = `${text.slice(0, ERROR_DISPLAY_MAX - 3)}...`;
  }
  return text;
}

export function isActiveRunStatus(runOrStatus) {
  const status = typeof runOrStatus === 'string'
    ? runOrStatus
    : getEffectiveRunStatus(runOrStatus);
  return ['running', 'awaiting_input'].includes(status);
}
