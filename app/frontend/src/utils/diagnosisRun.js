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

export function getRunStatusLabel(runOrStatus) {
  const status = typeof runOrStatus === 'string'
    ? runOrStatus
    : getEffectiveRunStatus(runOrStatus);

  switch (status) {
    case 'completed': return '已完成';
    case 'running': return '运行中';
    case 'awaiting_input': return '等待回答';
    case 'pending': return '待执行';
    case 'failed': return '失败';
    case 'stopped': return '已停止';
    default: return status || '未知';
  }
}

export function getRunStatusBadgeClass(runOrStatus) {
  const status = typeof runOrStatus === 'string'
    ? runOrStatus
    : getEffectiveRunStatus(runOrStatus);

  switch (status) {
    case 'completed': return 'badge-green';
    case 'running': return 'badge-blue';
    case 'awaiting_input': return 'badge-purple';
    case 'pending': return 'badge-yellow';
    case 'failed': return 'badge-red';
    case 'stopped': return 'badge-purple';
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

export function isActiveRunStatus(runOrStatus) {
  const status = typeof runOrStatus === 'string'
    ? runOrStatus
    : getEffectiveRunStatus(runOrStatus);
  return ['running', 'awaiting_input'].includes(status);
}
