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
  getRunSnapshot: (runId) => request(`/diagnosis/snapshot/${runId}`),
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

  // Chat
  startChat: (params) =>
    request('/chat/start', { method: 'POST', body: JSON.stringify(params) }),
  sendChatMessage: (chatId, params) =>
    request(`/chat/send/${chatId}`, { method: 'POST', body: JSON.stringify(params) }),
  stopChat: (chatId) =>
    request(`/chat/stop/${chatId}`, { method: 'POST' }),
  getChatInfo: (chatId) => request(`/chat/info/${chatId}`),
  getChatSession: (chatId) => request(`/chat/session/${chatId}`),
  renameChatSession: (chatId, title) =>
    request(`/chat/session/${chatId}`, { method: 'PATCH', body: JSON.stringify({ title }) }),
  updateChatSessionConfig: (chatId, params) =>
    request(`/chat/session/${chatId}/config`, { method: 'PATCH', body: JSON.stringify(params) }),
  deleteChatSession: (chatId) =>
    request(`/chat/session/${chatId}`, { method: 'DELETE' }),
  getChatHistory: (chatId) => request(`/chat/history/${chatId}`),
  listChats: () => request('/chat/list'),
  listChatDirectories: (path) => request(path ? `/chat/directories?path=${encodeURIComponent(path)}` : '/chat/directories'),
  pickChatDirectory: (path) =>
    request('/chat/directories/pick', {
      method: 'POST',
      body: JSON.stringify(path ? { path } : {}),
    }),
  chatStreamUrl: (chatId) => `${BASE}/chat/stream/${chatId}`,

  // SSE stream
  streamUrl: (runId) => `${BASE}/diagnosis/stream/${runId}`,

  // ── Harness abstraction (engine-agnostic; Claude/OMP/Codex... all implement) ──
  listHarnesses: () => request('/harness'),
  harnessHealth: (id) => request(`/harness/${id}/health`),
  harnessRuns: (id) => request(`/harness/${id}/runs`),
  harnessRun: (id, name) => request(`/harness/${id}/runs/${encodeURIComponent(name)}`),
  harnessSummary: (id, name) => request(`/harness/${id}/runs/${encodeURIComponent(name)}/summary`),
  harnessArtifact: (id, name, kind) =>
    request(`/harness/${id}/runs/${encodeURIComponent(name)}/artifact/${kind}`),
  harnessEnhancement: (id, name, kind) =>
    request(`/harness/${id}/runs/${encodeURIComponent(name)}/enhancement/${kind}`),
  harnessHtmlUrl: (id, name, mode = 'baseline') =>
    `${BASE}/harness/${id}/runs/${encodeURIComponent(name)}/html?mode=${mode}`,

  // ── OMP harness bridge (legacy alias, kept for compatibility) ──
  ompHealth: () => request('/omp/health'),
  listOmpRuns: () => request('/omp/runs'),
  getOmpRun: (name) => request(`/omp/runs/${encodeURIComponent(name)}`),
  getOmpSummary: (name) => request(`/omp/runs/${encodeURIComponent(name)}/summary`),
  getOmpArtifact: (name, kind) =>
    request(`/omp/runs/${encodeURIComponent(name)}/artifact/${kind}`),
  getOmpEnhancement: (name, kind) =>
    request(`/omp/runs/${encodeURIComponent(name)}/enhancement/${kind}`),
  ompHtmlUrl: (name) => `${BASE}/omp/runs/${encodeURIComponent(name)}/html`,
  ompEnhHtmlUrl: (name) => `${BASE}/omp/runs/${encodeURIComponent(name)}/enhancement/html`,
};

// WebSocket URL (same host, port determined at runtime)
export function wsUrl() {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${proto}//${location.host}/ws`;
}
