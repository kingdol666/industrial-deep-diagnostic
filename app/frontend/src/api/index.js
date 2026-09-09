const BASE = '/api';
const TOKEN_KEY = 'auth_token';
const USER_KEY = 'auth_user';

// ─── 客户端会话管理 ───
export function getToken() {
  try { return localStorage.getItem(TOKEN_KEY) || ''; } catch { return ''; }
}
export function setToken(token) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch { /* ignore */ }
}
export function getStoredUser() {
  try { return JSON.parse(localStorage.getItem(USER_KEY) || 'null'); } catch { return null; }
}
export function setStoredUser(user) {
  try {
    if (user) localStorage.setItem(USER_KEY, JSON.stringify(user));
    else localStorage.removeItem(USER_KEY);
  } catch { /* ignore */ }
}

// 全局 401 处理：清除本地会话并通知 App 回到登录页
function handleUnauthorized() {
  setToken('');
  setStoredUser(null);
  window.dispatchEvent(new CustomEvent('auth:unauthorized'));
}

function authHeaders(extra = {}) {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}`, ...extra } : { ...extra };
}

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    ...options,
  });
  const data = await res.json();
  if (res.status === 401) {
    handleUnauthorized();
    throw new Error(data.error || '认证失败，请重新登录');
  }
  if (!data.success) throw new Error(data.error || 'Request failed');
  return data.data;
}

export const api = {
  // ── Auth（register/login 为公开端点，其余需认证）──
  authRegister: (params) => request('/auth/register', { method: 'POST', body: JSON.stringify(params) }),
  authLogin: (params) => request('/auth/login', { method: 'POST', body: JSON.stringify(params) }),
  authMe: () => request('/auth/me'),
  listTokens: () => request('/auth/tokens'),
  createToken: (params) => request('/auth/tokens', { method: 'POST', body: JSON.stringify(params) }),
  revokeToken: (id) => request(`/auth/tokens/${id}`, { method: 'DELETE' }),

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
      headers: authHeaders(),
      body: formData,
    }).then(async (r) => {
      const d = await r.json();
      if (r.status === 401) { handleUnauthorized(); throw new Error(d.error || '认证失败，请重新登录'); }
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
  enhanceDiagnosis: (runId) =>
    request(`/diagnosis/enhance/${runId}`, { method: 'POST' }),
  listOntologyStore: () => request('/ontology/store'),
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
  chatStreamUrl: (chatId) => `${BASE}/chat/stream/${chatId}?token=${encodeURIComponent(getToken())}`,

  // SSE stream
  streamUrl: (runId) => `${BASE}/diagnosis/stream/${runId}?token=${encodeURIComponent(getToken())}`,

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

// WebSocket URL (same host, port determined at runtime) — 连接时携带 token 鉴权
export function wsUrl() {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const token = encodeURIComponent(getToken());
  return `${proto}//${location.host}/ws${token ? `?token=${token}` : ''}`;
}
