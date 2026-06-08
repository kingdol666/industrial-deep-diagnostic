import { computed, reactive, readonly } from 'vue';
import { api, wsUrl } from '../api/index.js';
import { isActiveRunStatus, isTerminalRunStatus, normalizeRunSummary } from '../utils/diagnosisRun.js';

const MAX_EVENTS = 3000;
const RECONNECT_BASE_MS = 1500;
const RECONNECT_MAX_MS = 10000;

const state = reactive({
  wsConnected: false,
  wsStatus: 'idle',
  lastError: '',
  reconnectAttempts: 0,
  catalogRuns: [],
  activeRunId: null,
  runSnapshots: {},
});

let socket = null;
let reconnectTimer = null;
let manualClose = false;

function ensureRunSnapshot(runId) {
  if (!runId) return null;
  if (!state.runSnapshots[runId]) {
    state.runSnapshots[runId] = reactive({
      runId,
      run: null,
      events: [],
      liveStatus: 'pending',
      hasActiveEngineRun: false,
      isHydrating: false,
      isSubscribed: false,
      currentQuestion: null,
      hitlRequest: null,
      lastEventSeq: -1,
      lastSyncAt: null,
    });
  }
  return state.runSnapshots[runId];
}

function mergeCatalogRuns(runs) {
  state.catalogRuns = (runs || []).map(normalizeRunSummary).filter(Boolean);
}

function upsertCatalogRun(run) {
  const normalized = normalizeRunSummary(run);
  if (!normalized?.run_id) return;
  const index = state.catalogRuns.findIndex(item => item.run_id === normalized.run_id);
  if (index >= 0) {
    state.catalogRuns[index] = {
      ...state.catalogRuns[index],
      ...normalized,
    };
  } else {
    state.catalogRuns.unshift(normalized);
  }
}

function applyRunPatch(snapshot, patch = {}) {
  if (!snapshot) return;
  snapshot.run = normalizeRunSummary({
    ...(snapshot.run || {}),
    run_id: snapshot.runId,
    ...patch,
  });
  upsertCatalogRun(snapshot.run);
}

function rebuildDerivedState(snapshot) {
  snapshot.currentQuestion = null;
  snapshot.hitlRequest = null;
  snapshot.lastEventSeq = -1;

  for (const event of snapshot.events) {
    snapshot.lastEventSeq = Math.max(snapshot.lastEventSeq, event?._seq ?? -1);
    if (event?.type === 'question') snapshot.currentQuestion = event.data || null;
    if (event?.type === 'question_result') snapshot.currentQuestion = null;
    if (event?.type === 'hitl_request') snapshot.hitlRequest = event.data || null;
    if (event?.type === 'hitl_result') snapshot.hitlRequest = null;
    if (event?.type === 'status' && event.data?.status) {
      snapshot.liveStatus = event.data.status;
      applyRunPatch(snapshot, {
        status: event.data.status,
        engineStatus: event.data.status,
        workspace_path: event.data.workspacePath ?? snapshot.run?.workspace_path ?? null,
        report_path: event.data.reportPath ?? snapshot.run?.report_path ?? null,
        score: event.data.score ?? snapshot.run?.score ?? null,
        judge_verdict: event.data.verdict ?? snapshot.run?.judge_verdict ?? null,
        error_message: event.data.error ?? snapshot.run?.error_message ?? null,
      });
      snapshot.hasActiveEngineRun = event.data.status === 'running';
      if (isTerminalRunStatus(event.data.status)) {
        snapshot.currentQuestion = null;
        snapshot.hitlRequest = null;
      }
    }
    if (event?.type === 'complete' && event.data?.status) {
      snapshot.liveStatus = event.data.status;
      applyRunPatch(snapshot, {
        status: event.data.status,
        engineStatus: event.data.status,
        workspace_path: event.data.workspacePath ?? snapshot.run?.workspace_path ?? null,
        report_path: event.data.reportPath ?? snapshot.run?.report_path ?? null,
        score: event.data.score ?? snapshot.run?.score ?? null,
        judge_verdict: event.data.verdict ?? snapshot.run?.judge_verdict ?? null,
        error_message: event.data.error ?? snapshot.run?.error_message ?? null,
      });
      snapshot.hasActiveEngineRun = false;
      if (isTerminalRunStatus(event.data.status)) {
        snapshot.currentQuestion = null;
        snapshot.hitlRequest = null;
      }
    }
    if (event?.type === 'error') {
      snapshot.liveStatus = event.data?.status || 'failed';
      applyRunPatch(snapshot, {
        status: event.data?.status || 'failed',
        engineStatus: event.data?.status || 'failed',
        error_message: event.data?.error ?? snapshot.run?.error_message ?? null,
      });
      snapshot.hasActiveEngineRun = false;
      snapshot.currentQuestion = null;
      snapshot.hitlRequest = null;
    }
  }

  if (snapshot.run?.status && !snapshot.liveStatus) {
    snapshot.liveStatus = snapshot.run.status;
  }
}

function setSnapshotFromPayload(runId, payload) {
  const snapshot = ensureRunSnapshot(runId);
  if (!snapshot) return null;

  if (payload.run) {
    snapshot.run = normalizeRunSummary(payload.run);
    upsertCatalogRun(payload.run);
  }
  snapshot.liveStatus = payload.liveStatus || snapshot.run?.engineStatus || snapshot.run?.status || snapshot.liveStatus;
  snapshot.hasActiveEngineRun = !!payload.hasActiveEngineRun;
  snapshot.events = Array.isArray(payload.events) ? payload.events.slice(-MAX_EVENTS) : [];
  snapshot.lastSyncAt = payload.sentAt || new Date().toISOString();
  snapshot.isHydrating = false;
  rebuildDerivedState(snapshot);
  if (!snapshot.currentQuestion && payload.currentQuestion) {
    snapshot.currentQuestion = payload.currentQuestion;
  }
  return snapshot;
}

function appendEvent(runId, event) {
  const snapshot = ensureRunSnapshot(runId);
  if (!snapshot || !event) return;

  const seq = event._seq ?? -1;
  if (seq >= 0 && seq <= snapshot.lastEventSeq) return;

  snapshot.events.push(event);
  if (snapshot.events.length > MAX_EVENTS) {
    snapshot.events.splice(0, snapshot.events.length - MAX_EVENTS);
  }
  snapshot.lastEventSeq = Math.max(snapshot.lastEventSeq, seq);
  snapshot.lastSyncAt = new Date().toISOString();

  if (event.type === 'question') snapshot.currentQuestion = event.data || null;
  if (event.type === 'question_result') snapshot.currentQuestion = null;
  if (event.type === 'hitl_request') snapshot.hitlRequest = event.data || null;
  if (event.type === 'hitl_result') snapshot.hitlRequest = null;
  if (event.type === 'status' && event.data?.status) {
    snapshot.liveStatus = event.data.status;
    applyRunPatch(snapshot, {
      status: event.data.status,
      engineStatus: event.data.status,
      workspace_path: event.data.workspacePath ?? snapshot.run?.workspace_path ?? null,
      report_path: event.data.reportPath ?? snapshot.run?.report_path ?? null,
      score: event.data.score ?? snapshot.run?.score ?? null,
      judge_verdict: event.data.verdict ?? snapshot.run?.judge_verdict ?? null,
      error_message: event.data.error ?? snapshot.run?.error_message ?? null,
    });
    snapshot.hasActiveEngineRun = event.data.status === 'running';
    if (isTerminalRunStatus(event.data.status)) {
      snapshot.currentQuestion = null;
      snapshot.hitlRequest = null;
    }
  }
  if (event.type === 'complete' && event.data?.status) {
    snapshot.liveStatus = event.data.status;
    applyRunPatch(snapshot, {
      status: event.data.status,
      engineStatus: event.data.status,
      workspace_path: event.data.workspacePath ?? snapshot.run?.workspace_path ?? null,
      report_path: event.data.reportPath ?? snapshot.run?.report_path ?? null,
      score: event.data.score ?? snapshot.run?.score ?? null,
      judge_verdict: event.data.verdict ?? snapshot.run?.judge_verdict ?? null,
      error_message: event.data.error ?? snapshot.run?.error_message ?? null,
    });
    snapshot.hasActiveEngineRun = false;
    if (isTerminalRunStatus(event.data.status)) {
      snapshot.currentQuestion = null;
      snapshot.hitlRequest = null;
    }
  }
  if (event.type === 'error') {
    snapshot.liveStatus = event.data?.status || 'failed';
    applyRunPatch(snapshot, {
      status: event.data?.status || 'failed',
      engineStatus: event.data?.status || 'failed',
      error_message: event.data?.error ?? snapshot.run?.error_message ?? null,
    });
    snapshot.hasActiveEngineRun = false;
    snapshot.currentQuestion = null;
    snapshot.hitlRequest = null;
  }
}

function handleSocketMessage(message) {
  switch (message.type) {
    case 'welcome':
      state.wsStatus = 'ready';
      break;
    case 'catalog_snapshot':
    case 'catalog_update':
      mergeCatalogRuns(message.data?.runs || []);
      break;
    case 'run_updated':
      if (message.data?.run) upsertCatalogRun(message.data.run);
      if (message.data?.runId && state.runSnapshots[message.data.runId]) {
        const snapshot = ensureRunSnapshot(message.data.runId);
        snapshot.run = normalizeRunSummary(message.data.run);
        snapshot.liveStatus = message.data.liveStatus || snapshot.liveStatus;
        snapshot.hasActiveEngineRun = !!message.data.hasActiveEngineRun;
        if (message.data?.statusEvent?.data?.error) {
          applyRunPatch(snapshot, { error_message: message.data.statusEvent.data.error });
        }
      }
      break;
    case 'run_snapshot':
      if (message.data?.runId) {
        setSnapshotFromPayload(message.data.runId, message.data);
      }
      break;
    case 'run_event':
      if (message.data?.runId && message.data?.event) {
        appendEvent(message.data.runId, message.data.event);
      }
      break;
    case 'subscribed': {
      const snapshot = ensureRunSnapshot(message.data?.runId);
      if (snapshot) snapshot.isSubscribed = true;
      break;
    }
    case 'unsubscribed': {
      const snapshot = ensureRunSnapshot(message.data?.runId);
      if (snapshot) snapshot.isSubscribed = false;
      break;
    }
    case 'error':
      state.lastError = message.data?.message || 'WebSocket error';
      break;
    default:
      break;
  }
}

function send(message) {
  if (!socket || socket.readyState !== WebSocket.OPEN) return false;
  socket.send(JSON.stringify(message));
  return true;
}

function scheduleReconnect() {
  if (manualClose || reconnectTimer) return;
  const delay = Math.min(RECONNECT_MAX_MS, RECONNECT_BASE_MS * (state.reconnectAttempts + 1));
  reconnectTimer = window.setTimeout(() => {
    reconnectTimer = null;
    connect();
  }, delay);
}

export function connect() {
  if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
    return;
  }

  manualClose = false;
  state.wsStatus = 'connecting';
  socket = new WebSocket(wsUrl());

  socket.onopen = () => {
    state.wsConnected = true;
    state.wsStatus = 'connected';
    state.reconnectAttempts = 0;
    send({ type: 'watch_catalog', enabled: true });
    if (state.activeRunId) {
      send({ type: 'subscribe_run', runId: state.activeRunId });
      send({ type: 'get_run_snapshot', runId: state.activeRunId });
    }
  };

  socket.onmessage = (event) => {
    try {
      handleSocketMessage(JSON.parse(event.data));
    } catch (err) {
      state.lastError = err.message || 'Failed to parse WebSocket payload';
    }
  };

  socket.onerror = () => {
    state.wsStatus = 'error';
  };

  socket.onclose = () => {
    state.wsConnected = false;
    state.wsStatus = manualClose ? 'closed' : 'disconnected';
    socket = null;
    if (!manualClose) {
      state.reconnectAttempts += 1;
      scheduleReconnect();
    }
  };
}

export function disconnect() {
  manualClose = true;
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
  if (socket) {
    socket.close();
    socket = null;
  }
  state.wsConnected = false;
  state.wsStatus = 'closed';
}

export function subscribeRun(runId) {
  if (!runId) return;
  if (state.activeRunId && state.activeRunId !== runId) {
    unsubscribeRun(state.activeRunId);
  }
  state.activeRunId = runId;
  const snapshot = ensureRunSnapshot(runId);
  snapshot.isHydrating = true;
  connect();
  if (state.wsConnected) {
    send({ type: 'subscribe_run', runId });
    send({ type: 'get_run_snapshot', runId });
  }
}

export function unsubscribeRun(runId = state.activeRunId) {
  if (!runId) return;
  send({ type: 'unsubscribe_run', runId });
  if (state.activeRunId === runId) state.activeRunId = null;
}

export async function hydrateRun(runId) {
  if (!runId) return null;
  const snapshot = ensureRunSnapshot(runId);
  snapshot.isHydrating = true;

  try {
    const realtimeSnapshot = await api.getRunSnapshot(runId);
    return setSnapshotFromPayload(runId, {
      run: realtimeSnapshot.run,
      liveStatus: realtimeSnapshot.liveStatus,
      hasActiveEngineRun: realtimeSnapshot.hasActiveEngineRun,
      currentQuestion: realtimeSnapshot.currentQuestion || null,
      events: realtimeSnapshot.events || [],
      sentAt: new Date().toISOString(),
    });
  } finally {
    snapshot.isHydrating = false;
  }
}

export async function refreshCatalog() {
  try {
    const runs = await api.listRuns();
    mergeCatalogRuns(runs || []);
  } catch (err) {
    state.lastError = err.message || 'Failed to refresh catalog';
  }
}

export function setRunStatusLocally(runId, patch) {
  const snapshot = ensureRunSnapshot(runId);
  if (!snapshot) return;
  snapshot.run = normalizeRunSummary({
    ...(snapshot.run || {}),
    run_id: runId,
    ...patch,
  });
  if (patch?.status) snapshot.liveStatus = patch.status;
  upsertCatalogRun(snapshot.run);
}

export function clearActiveRun() {
  if (state.activeRunId) unsubscribeRun(state.activeRunId);
  state.activeRunId = null;
}

export function useDiagnosisRealtimeStore() {
  const activeSnapshot = computed(() => (
    state.activeRunId ? state.runSnapshots[state.activeRunId] || null : null
  ));

  const runningRuns = computed(() => state.catalogRuns.filter(
    run => isActiveRunStatus(run),
  ));

  const pastRuns = computed(() => state.catalogRuns.filter(
    run => !isActiveRunStatus(run),
  ));

  return {
    state: readonly(state),
    activeSnapshot,
    runningRuns,
    pastRuns,
    connect,
    disconnect,
    subscribeRun,
    unsubscribeRun,
    hydrateRun,
    refreshCatalog,
    clearActiveRun,
    setRunStatusLocally,
    ensureRunSnapshot,
  };
}
