const BASE = '/api';

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  const data = await res.json();
  if (!data.success) throw new Error(data.error || 'Request failed');
  return data.data;
}

export const api = {
  // Data files
  listData: (folder) => request(folder ? `/files/data/${folder}` : '/files/data'),
  createFolder: (name, description) =>
    request('/files/data/folder', { method: 'POST', body: JSON.stringify({ name, description }) }),
  deleteFolder: (name) =>
    request(`/files/data/folder/${name}`, { method: 'DELETE' }),
  uploadFiles: (folder, files) => {
    const formData = new FormData();
    for (const f of files) formData.append('files', f);
    const query = folder ? `?folder=${encodeURIComponent(folder)}` : '';
    return fetch(`${BASE}/files/data/upload${query}`, {
      method: 'POST',
      body: formData,
    }).then(r => r.json()).then(d => {
      if (!d.success) throw new Error(d.error);
      return d.data;
    });
  },
  readFile: (path) => request(`/files/data/file/${encodeURIComponent(path)}`),

  // Workspace
  listWorkspace: () => request('/files/workspace'),
  getReport: (name) => request(`/files/workspace/report/${name}`),
  getOptimizer: (name) => request(`/files/workspace/optimizer/${name}`),
  listWorkspaceFiles: (name) => request(`/files/workspace/files/${name}`),

  // Diagnosis
  startDiagnosis: (params) =>
    request('/diagnosis/start', { method: 'POST', body: JSON.stringify(params) }),
  executeDiagnosis: (runId) =>
    request(`/diagnosis/execute/${runId}`, { method: 'POST' }),
  getRunStatus: (runId) => request(`/diagnosis/status/${runId}`),
  stopDiagnosis: (runId) =>
    request(`/diagnosis/stop/${runId}`, { method: 'POST' }),
  continueDiagnosis: (runId, followUpMessage) =>
    request(`/diagnosis/continue/${runId}`, {
      method: 'POST',
      body: followUpMessage ? JSON.stringify({ followUpMessage }) : undefined,
    }),
  sendChat: (runId, message) =>
    request(`/diagnosis/chat/${runId}`, {
      method: 'POST',
      body: JSON.stringify({ message }),
    }),
  respondHITL: (hitlId, approved) =>
    request(`/diagnosis/hitl/${hitlId}`, { method: 'POST', body: JSON.stringify({ approved }) }),
  listRuns: () => request('/diagnosis/list'),
  submitAnswer: (runId, questionId, toolUseId, answers) =>
    request(`/diagnosis/answer/${runId}`, {
      method: 'POST',
      body: JSON.stringify({ questionId, toolUseId, answers }),
    }),

  // History
  getRuns: () => request('/history/runs'),
  getRunWithLogs: (runId) => request(`/history/runs/${runId}`),
  deleteRun: (runId) =>
    request(`/history/runs/${runId}`, { method: 'DELETE' }),
  getSessionContent: (runId) => request(`/diagnosis/session/${runId}`),

  // SSE stream
  streamUrl: (runId) => `${BASE}/diagnosis/stream/${runId}`,
};

// WebSocket URL (same host, port determined at runtime)
export function wsUrl() {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${proto}//${location.host}/ws`;
}
