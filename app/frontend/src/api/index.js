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

/** API 错误：携带服务端 code / status / details，供调用方做分支处理（如 409 版本冲突）。 */
export class ApiError extends Error {
  constructor(message, { status, code, details } = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    ...options,
  });
  let data;
  try {
    data = await res.json();
  } catch {
    throw new ApiError(`服务端返回了非 JSON 响应 (HTTP ${res.status})`, { status: res.status });
  }
  if (res.status === 401) {
    handleUnauthorized();
    throw new ApiError(data.error || '认证失败，请重新登录', { status: 401, code: data.code });
  }
  if (!data.success) {
    throw new ApiError(data.error || 'Request failed', {
      status: res.status, code: data.code, details: data.details,
    });
  }
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

  // ── Ontology asset control plane（本体管理页：列表 / 可视化 / 编辑 / 复用 / 采纳）──
  ontologyAssets: (params = {}) => {
    const qs = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== ''),
    ).toString();
    return request(`/ontology/assets${qs ? `?${qs}` : ''}`);
  },
  ontologyOverview: () => request('/ontology/overview'),
  ontologySchema: () => request('/ontology/schema'),
  ontologyAsset: (scene, version, opts = {}) => {
    const qs = new URLSearchParams(
      Object.entries(opts).filter(([, v]) => v !== undefined).map(([k, v]) => [k, String(v)]),
    ).toString();
    return request(`/ontology/assets/${encodeURIComponent(scene)}/${version}${qs ? `?${qs}` : ''}`);
  },
  ontologyGraph: (scene, version, layers = {}) => {
    const qs = new URLSearchParams(
      Object.entries(layers).filter(([, v]) => v !== undefined).map(([k, v]) => [k, v ? '1' : '0']),
    ).toString();
    return request(`/ontology/assets/${encodeURIComponent(scene)}/${version}/graph${qs ? `?${qs}` : ''}`);
  },
  ontologyMetrics: (scene, version) =>
    request(`/ontology/assets/${encodeURIComponent(scene)}/${version}/metrics`),
  ontologyValidateAsset: (scene, version) =>
    request(`/ontology/assets/${encodeURIComponent(scene)}/${version}/validate`),
  ontologyProvenance: (scene, version) =>
    request(`/ontology/assets/${encodeURIComponent(scene)}/${version}/provenance`),
  // 保存编辑 → 生成新版本 v(N+1)；body: { ontology, base_version, title, tags, notes, force }
  ontologySave: (scene, version, body) =>
    request(`/ontology/assets/${encodeURIComponent(scene)}/${version}`, {
      method: 'PUT', body: JSON.stringify(body),
    }),
  ontologyCreate: (body) =>
    request('/ontology/assets', { method: 'POST', body: JSON.stringify(body) }),
  ontologyPatch: (scene, version, patch) =>
    request(`/ontology/assets/${encodeURIComponent(scene)}/${version}`, {
      method: 'PATCH', body: JSON.stringify(patch),
    }),
  ontologyClone: (scene, version, body) =>
    request(`/ontology/assets/${encodeURIComponent(scene)}/${version}/clone`, {
      method: 'POST', body: JSON.stringify(body),
    }),
  ontologyDeleteVersion: (scene, version) =>
    request(`/ontology/assets/${encodeURIComponent(scene)}/${version}`, { method: 'DELETE' }),
  ontologyDeleteScene: (scene) =>
    request(`/ontology/scenes/${encodeURIComponent(scene)}`, { method: 'DELETE' }),
  ontologyValidate: (ontology) =>
    request('/ontology/validate', { method: 'POST', body: JSON.stringify({ ontology }) }),
  ontologyProjectGraph: (ontology, layers) =>
    request('/ontology/graph', { method: 'POST', body: JSON.stringify({ ontology, layers }) }),
  ontologyProjectMetrics: (ontology) =>
    request('/ontology/metrics', { method: 'POST', body: JSON.stringify({ ontology }) }),
  ontologyDiffDraft: (before, after) =>
    request('/ontology/diff', { method: 'POST', body: JSON.stringify({ before, after }) }),
  ontologyDiffVersions: (scene, from, to) =>
    request(`/ontology/diff?scene=${encodeURIComponent(scene)}&from=${from}&to=${to}`),
  ontologyRecommend: (body) =>
    request('/ontology/recommend', { method: 'POST', body: JSON.stringify(body) }),
  ontologyCandidates: (params = {}) => {
    const qs = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== ''),
    ).toString();
    return request(`/ontology/candidates${qs ? `?${qs}` : ''}`);
  },
  ontologyAdopt: (body) =>
    request('/ontology/adopt', { method: 'POST', body: JSON.stringify(body) }),

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
  harnessAvailability: () => request('/harness/availability'),
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
