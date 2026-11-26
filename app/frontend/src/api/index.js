const BASE = '/api';

// The client is a plain module, so it reaches the i18n instance directly rather
// than through a component's `useI18n()`. Locale switches are reactive: the
// message is resolved at throw time, not at module load.
import i18n from '../i18n/index.js';

function msg(key, fallback) {
  const v = i18n.global.t(key);
  return v && v !== key ? v : fallback;
}

// ─── 会话管理（HttpOnly cookie）───
// 会话凭据是服务端下发的 HttpOnly `idd_session` cookie（SameSite=Strict），
// JavaScript 读不到、也不需要读：同源的 fetch / <img> / <iframe> / WebSocket
// 握手都会自动携带它，状态变更请求由浏览器自动附上同源 Origin。
// 因此这里没有 getToken/setToken，也不再注入 `Authorization: Bearer`——
// Bearer 通道仅保留给外部程序化调用的 API Token，与页面会话无关。
// 登录态的唯一权威来源是 GET /api/auth/me（见 App.vue 的启动探针）。

// 全局 401 处理：通知 App 回到登录页。cookie 由服务端清除/过期，客户端
// 无本地凭据可清（也不该清 —— localStorage 里的任何副本都已经不存在了）。
function handleUnauthorized() {
  window.dispatchEvent(new CustomEvent('auth:unauthorized'));
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

function buildQuery(params = {}) {
  const qs = new URLSearchParams(
    Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== ''),
  ).toString();
  return qs ? `?${qs}` : '';
}

async function requestEnvelope(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    // Same-origin: the browser attaches the HttpOnly session cookie and the
    // Origin header on its own. No Authorization header is injected for
    // in-browser session calls (Bearer is for external API tokens only).
    headers: { 'Content-Type': 'application/json' },
    // Diagnostic state must never be served from heuristic cache: the ETag on
    // /ontology responses let a stale pre-restart payload outlive the server
    // that produced it. Revalidate every API GET.
    cache: 'no-cache',
    ...options,
  });
  let data;
  try {
    data = await res.json();
  } catch {
    throw new ApiError(`${msg('ontology.badResponse', 'Server returned a non-JSON response')} (HTTP ${res.status})`,
      { status: res.status });
  }
  if (res.status === 401) {
    handleUnauthorized();
    throw new ApiError(data.error || msg('ontology.authRequired', 'Authentication failed — please sign in again'),
      { status: 401, code: data.code });
  }
  if (!data.success) {
    throw new ApiError(data.error || 'Request failed', {
      status: res.status, code: data.code, details: data.details,
    });
  }
  return data;
}

async function request(path, options = {}) {
  return (await requestEnvelope(path, options)).data;
}

function jsonRequest(path, method, body) {
  return request(path, { method, ...(body === undefined ? {} : { body: JSON.stringify(body) }) });
}

const versionPath = ({ asset_id, version }) => `/knowledge/assets/${encodeURIComponent(asset_id)}/versions/${encodeURIComponent(version)}`;
const runKnowledgePath = (id) => `/knowledge/runs/${encodeURIComponent(id)}`;

export const api = {
  // ── Auth（register/login 为公开端点，其余需认证）──
  // login 成功即由服务端 Set-Cookie 下发 HttpOnly 会话 cookie；响应体本身
  // 不含会话凭据（前端随后向 /me 取权威用户对象）。logout 清 cookie。
  authRegister: (params) => request('/auth/register', { method: 'POST', body: JSON.stringify(params) }),
  authLogin: (params) => request('/auth/login', { method: 'POST', body: JSON.stringify(params) }),
  authLogout: () => request('/auth/logout', { method: 'POST' }),
  authMe: () => request('/auth/me'),
  listTokens: () => request('/auth/tokens'),
  createToken: (params) => request('/auth/tokens', { method: 'POST', body: JSON.stringify(params) }),
  revokeToken: (id) => request(`/auth/tokens/${id}`, { method: 'DELETE' }),

  // Data files
  listData: (folder) => request(folder ? `/files/data/${folder}` : '/files/data'),
  browseData: (path = '') => request(`/files/data/browse?path=${encodeURIComponent(path)}`),
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
      // Multipart: let the browser set the boundary; the session cookie rides
      // along same-origin.
      body: formData,
    }).then(async (r) => {
      const d = await r.json();
      if (r.status === 401) {
        handleUnauthorized();
        throw new Error(d.error || msg('ontology.authRequired', 'Authentication failed — please sign in again'));
      }
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
  // HTML reports inside a run dir (run-relative paths, any subdirectory)
  listRunHtml: (name) => request(`/files/workspace/html/${encodeURIComponent(name)}`),
  getChartData: (dirName) => request(`/analysis/chart-data/${encodeURIComponent(dirName)}`),

  // Production lines and versioned knowledge. Catalog discovery is not an access check.
  listProductionLines: () => request('/lines'),
  createProductionLine: (body) => jsonRequest('/lines', 'POST', body),
  createKnowledgeAsset: (lineId, body) => jsonRequest(`/lines/${encodeURIComponent(lineId)}/assets`, 'POST', body),
  listKnowledgeCatalog: (params) => request(`/knowledge/catalog${buildQuery(params)}`),
  publishKnowledgeVersion: (ref, body) => jsonRequest(`${versionPath(ref)}/publish`, 'POST', body),
  withdrawKnowledgeVersion: (ref) => jsonRequest(`${versionPath(ref)}/withdraw`, 'POST', {}),
  setKnowledgeGrant: (ref, userId, rights) => jsonRequest(`${versionPath(ref)}/grants/${encodeURIComponent(userId)}`, 'PUT', { rights }),
  revokeKnowledgeGrant: (ref, userId) => jsonRequest(`${versionPath(ref)}/grants/${encodeURIComponent(userId)}`, 'DELETE'),
  searchRunKnowledge: (id, query) => jsonRequest(`${runKnowledgePath(id)}/search`, 'POST', { query }),
  getRunKnowledgeItem: (id, refId) => request(`${runKnowledgePath(id)}/items/${encodeURIComponent(refId)}`),
  listRunRetrievals: (id) => request(`${runKnowledgePath(id)}/retrievals`),

  // Diagnosis
  startDiagnosis: (params) =>
    request('/diagnosis/start', { method: 'POST', body: JSON.stringify(params) }),
  executeDiagnosis: (runId) =>
    request(`/diagnosis/execute/${runId}`, { method: 'POST' }),
  enhanceDiagnosis: (runId) =>
    request(`/diagnosis/enhance/${runId}`, { method: 'POST' }),
  listOntologyStore: () => request('/ontology/store'),

  // ── Line memory（产线记忆：跨 run 共性结论 / 本体提案 / 版本链）──
  lineMemoryListLines: () => request('/line-memory/lines'),
  lineMemoryGetLine: (key) => request(`/line-memory/lines/${encodeURIComponent(key)}`),
  lineMemoryFindings: (key, params = {}) => {
    const qs = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== ''),
    ).toString();
    return request(`/line-memory/lines/${encodeURIComponent(key)}/findings${qs ? `?${qs}` : ''}`);
  },
  lineMemoryOntology: (key) => request(`/line-memory/lines/${encodeURIComponent(key)}/ontology`),
  lineMemoryRefute: (key, body) =>
    request(`/line-memory/lines/${encodeURIComponent(key)}/refute`, { method: 'POST', body: JSON.stringify(body) }),
  lineMemoryUnrefute: (key, body) =>
    request(`/line-memory/lines/${encodeURIComponent(key)}/unrefute`, { method: 'POST', body: JSON.stringify(body) }),
  lineMemoryMerge: (key, into) =>
    request(`/line-memory/lines/${encodeURIComponent(key)}/merge`, { method: 'POST', body: JSON.stringify({ into }) }),
  lineMemoryConsolidate: (key) =>
    request(`/line-memory/lines/${encodeURIComponent(key)}/consolidate`, { method: 'POST', body: '{}' }),
  lineMemoryProposals: (params = {}) => {
    const qs = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== ''),
    ).toString();
    return request(`/line-memory/proposals${qs ? `?${qs}` : ''}`);
  },
  lineMemoryApproveProposal: (id) =>
    request(`/line-memory/proposals/${encodeURIComponent(id)}/approve`, { method: 'POST', body: '{}' }),
  lineMemoryRejectProposal: (id) =>
    request(`/line-memory/proposals/${encodeURIComponent(id)}/reject`, { method: 'POST', body: '{}' }),

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
  // Snapshot event window is bounded server-side (default 2000; the view only
  // renders the tail). events_total / events_truncated ride on the response.
  getRunSnapshot: (runId, eventsLimit = 2000) =>
    request(`/diagnosis/snapshot/${runId}?events_limit=${encodeURIComponent(eventsLimit)}`),
  stopDiagnosis: (runId) =>
    request(`/diagnosis/stop/${runId}`, { method: 'POST' }),
  continueDiagnosis: (runId, followUpMessage) =>
    request(`/diagnosis/continue/${runId}`, {
      method: 'POST',
      body: followUpMessage ? JSON.stringify({ followUpMessage }) : undefined,
    }),
  // The run's harness is locked on the server; never send one here.
  sendRunChat: (runId, message, maxTurns) =>
    request(`/diagnosis/chat/${runId}`, {
      method: 'POST',
      body: JSON.stringify(maxTurns ? { message, maxTurns } : { message }),
    }),
  sendChat: (runId, message, maxTurns) => api.sendRunChat(runId, message, maxTurns),
  getSessionMap: (runId) => request(`/diagnosis/session-map/${runId}`),
  respondHITL: (hitlId, approved) =>
    request(`/diagnosis/hitl/${hitlId}`, { method: 'POST', body: JSON.stringify({ approved }) }),
  listDiagnosisRuns: () => request('/diagnosis/list'),
  submitAnswer: (runId, questionId, toolUseId, answers) =>
    request(`/diagnosis/answer/${runId}`, {
      method: 'POST',
      body: JSON.stringify({ questionId, toolUseId, answers }),
    }),

  // ── History（服务端过滤 + 软删/回收站 + 分类）──
  // Returns { runs, total, limit, offset }; `include_deleted=true` opens the
  // recycle bin, `category_id`/`status`/`q` are server-side filters.
  listRuns: async (params = {}) => {
    const envelope = await requestEnvelope(`/history/runs${buildQuery(params)}`);
    return {
      runs: envelope.data || [],
      total: envelope.total ?? (envelope.data?.length || 0),
      limit: envelope.limit,
      offset: envelope.offset,
    };
  },
  getRuns: async (params = {}) => (await api.listRuns(params)).runs,
  getRunWithLogs: (runId) => request(`/history/runs/${runId}`),
  renameRun: (runId, title) =>
    request(`/history/runs/${runId}`, { method: 'PATCH', body: JSON.stringify({ title }) }),
  setRunCategory: (runId, categoryId) =>
    request(`/history/runs/${runId}`, { method: 'PATCH', body: JSON.stringify({ category_id: categoryId }) }),
  // Soft delete by default; { purge: true } also removes the workspace directory.
  deleteRun: (runId, opts = {}) => {
    const purge = opts === true || opts?.purge === true;
    return request(`/history/runs/${runId}${purge ? '?purge=true' : ''}`, { method: 'DELETE' });
  },
  restoreRun: (runId) =>
    request(`/history/runs/${runId}/restore`, { method: 'POST' }),
  listRunCategories: () => request('/history/categories'),
  createRunCategory: (name) =>
    request('/history/categories', { method: 'POST', body: JSON.stringify({ name }) }),
  renameRunCategory: (id, name) =>
    request(`/history/categories/${id}`, { method: 'PATCH', body: JSON.stringify({ name }) }),
  deleteRunCategory: (id) =>
    request(`/history/categories/${id}`, { method: 'DELETE' }),
  getSessionContent: (runId) => request(`/diagnosis/session/${runId}`),

  // ── Results library（扁平分析结果库：摘要索引 → id → 详情 + 编辑）──
  // Returns { results, total, limit, offset, brief }; server-side filters
  // q/intent/category_id/tag/scene/harness/min_score/sort/limit/offset/brief.
  listResults: async (params = {}) => {
    const envelope = await requestEnvelope(`/results${buildQuery(params)}`);
    return {
      results: envelope.data || [],
      total: envelope.total ?? (envelope.data?.length || 0),
      limit: envelope.limit,
      offset: envelope.offset,
      brief: envelope.brief,
    };
  },
  // include_md=false omits the report body (detail without the bulk).
  getResultDetail: (resultId, { includeMd = false } = {}) =>
    request(`/results/${encodeURIComponent(resultId)}${includeMd ? '' : '?include_md=false'}`),
  // User-editable fields only (summary/summary_json are server-managed).
  patchResult: (resultId, body) =>
    request(`/results/${encodeURIComponent(resultId)}`, { method: 'PATCH', body: JSON.stringify(body) }),
  listReviewedMemory: (params) => request(`/line-memory/reviews${buildQuery(params)}`),
  getResultReview: (id) => request(`/results/${encodeURIComponent(id)}/review`),
  patchResultReview: (id, body) => request(`/results/${encodeURIComponent(id)}/review`, { method: 'PATCH', body: JSON.stringify(body) }),
  listResultReviewHistory: (id, before) => requestEnvelope(`/results/${encodeURIComponent(id)}/review/history${buildQuery({ before })}`),
  // Category management on the results surface (same service as /history).
  listResultCategories: () => request('/results/categories'),
  createResultCategory: (name) =>
    request('/results/categories', { method: 'POST', body: JSON.stringify({ name }) }),

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
  // SSE/EventSource 与 <img>/<iframe> 一样无法携带自定义请求头，但会话现在是
  // 同源 HttpOnly cookie —— 浏览器对这些请求自动附带，URL 里不再有 token。
  chatStreamUrl: (chatId) => `${BASE}/chat/stream/${chatId}`,

  // SSE stream
  streamUrl: (runId) => `${BASE}/diagnosis/stream/${runId}`,

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
  // Loaded as an <iframe src>. The iframe is same-origin, so the browser
  // attaches the session cookie automatically — no token in the URL.
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

  // 说明：固定脚本分析（sentinel / line-report 的 HTTP 直包端点）已从产品面退役——
  // 所有分析由集成智能体经 /api/diagnosis/start（analysisIntent）真实执行。
};

// WebSocket URL (same host, port determined at runtime).
// The handshake is same-origin, so the browser sends the HttpOnly session
// cookie with it automatically — no token in the URL (it used to leak into
// access logs / proxies) and no token subprotocol to offer anymore.
export function wsUrl() {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${proto}//${location.host}/ws`;
}
