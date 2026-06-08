<template>
  <div class="chat-shell">
    <aside class="chat-sidebar">
      <div class="chat-sidebar-top">
        <div class="chat-sidebar-brand">
          <div class="chat-sidebar-kicker">Workspace Chat</div>
          <div class="chat-sidebar-heading">Conversations</div>
        </div>
        <button class="btn btn-primary chat-sidebar-new" @click="createChatPanel" :disabled="loading">New Chat</button>
      </div>

      <div class="chat-sidebar-groups">
        <div class="chat-sidebar-group">
          <div class="chat-sidebar-header">
            <h3>Chat</h3>
            <button class="btn btn-sm" @click="refreshChats">Refresh</button>
          </div>
          <div class="chat-sidebar-list">
            <button
              v-for="panel in chatPanels"
              :key="panel.localId"
              class="chat-session-item"
              :class="{ active: activePanel?.localId === panel.localId }"
              @click="selectPanel(panel.localId)"
            >
              <div class="chat-session-head">
                <span class="chat-session-type">Chat</span>
                <div v-if="panel.chatId" class="chat-session-actions" @click.stop>
                  <button class="session-icon-btn" @click="renameChatPanel(panel)">✎</button>
                  <button class="session-icon-btn danger" @click="removeChatPanel(panel)">✕</button>
                </div>
              </div>
              <div class="chat-session-name">{{ panel.title }}</div>
              <div class="chat-session-meta">
                <span>{{ shortId(panel.sessionId || panel.chatId || panel.localId) }}</span>
                <span :class="['badge', panel.status === 'active' ? 'badge-green' : 'badge-blue']">
                  {{ panel.status === 'active' ? 'active' : 'saved' }}
                </span>
              </div>
            </button>
            <div v-if="chatPanels.length === 0" class="chat-sidebar-empty">No chat sessions yet.</div>
          </div>
        </div>

        <div class="chat-sidebar-group diagnose-group">
          <div class="chat-sidebar-header">
            <h3>Diagnose Sessions</h3>
            <button class="btn btn-sm" @click="refreshDiagnosePanels">Refresh</button>
          </div>
          <div class="chat-sidebar-list">
            <button
              v-for="panel in diagnosePanels"
              :key="panel.localId"
              class="chat-session-item diagnose-item"
              :class="{ active: activePanel?.localId === panel.localId }"
              @click="selectPanel(panel.localId)"
            >
              <div class="chat-session-head">
                <span class="chat-session-type diagnose-type">Diagnose</span>
              </div>
              <div class="chat-session-name">{{ panel.title }}</div>
              <div class="chat-session-meta">
                <span>{{ shortId(panel.runId) }}</span>
                <span :class="['badge', runBadgeClass(panel.status)]">{{ runStatusLabel(panel.status) }}</span>
              </div>
            </button>
            <div v-if="diagnosePanels.length === 0" class="chat-sidebar-empty">No diagnosis sessions found.</div>
          </div>
        </div>
      </div>

      <div class="chat-sidebar-footer">
        <span class="chat-connection-dot" :class="wsConnected ? 'online' : 'offline'"></span>
        <span>{{ wsConnected ? 'WebSocket connected' : 'WebSocket disconnected' }}</span>
      </div>
    </aside>

    <section class="chat-main">
      <div class="chat-main-header">
        <button class="chat-model-btn" type="button">
          {{ activePanel?.kind === 'diagnose' ? 'Diagnose' : 'Chat' }}
          <span class="chat-model-chevron">⌄</span>
        </button>
        <div class="chat-header-actions">
          <span class="chat-status" :class="wsConnected ? 'chat-status-online' : 'chat-status-offline'">
            {{ wsConnected ? (activePanelRunning ? 'Streaming' : 'Ready') : 'Disconnected' }}
          </span>
          <button class="btn btn-danger btn-sm" @click="stopActivePanel" :disabled="!canStop">Stop</button>
        </div>
      </div>

      <div class="chat-stage" v-if="!activePanel">
        <div class="chat-empty">
          <div class="chat-empty-icon">💬</div>
          <h3>Start a conversation</h3>
          <p>Chat and diagnose sessions both stream through the same WebSocket transport.</p>
        </div>
      </div>

      <div v-else class="chat-stage">
        <div class="chat-session-title">
          <div class="chat-main-badges">
            <span class="chat-main-kind" :class="activePanel.kind === 'diagnose' ? 'kind-diagnose' : 'kind-chat'">
              {{ activePanel.kind === 'diagnose' ? 'Diagnose Session' : 'Chat Session' }}
            </span>
            <span class="chat-session-chip" v-if="activePanel?.sessionId">session: {{ shortId(activePanel.sessionId) }}</span>
            <span class="chat-session-chip" v-if="activePanel?.chatId">chat: {{ shortId(activePanel.chatId) }}</span>
            <span class="chat-session-chip" v-if="activePanel?.runId">run: {{ shortId(activePanel.runId) }}</span>
          </div>
          <h2 class="chat-title">{{ activePanelTitle }}</h2>
        </div>

        <div class="chat-thread-shell">
          <div class="chat-stage-banner" v-if="activePanel.kind === 'diagnose'">
            <div class="chat-stage-banner-title">Diagnose Session</div>
            <div class="chat-stage-banner-text">这里展示诊断会话的真实对话内容，并可在同一处继续补充说明。</div>
          </div>

          <div class="chat-thread">
            <div class="chat-welcome" v-if="activePanel.events.length === 0">
              <div class="chat-empty-icon">✨</div>
              <h3>{{ activePanel.kind === 'diagnose' ? '诊断会话已连接' : 'What would you like to ask?' }}</h3>
              <p>{{ activePanel.kind === 'diagnose' ? '诊断对话会在这里持续同步。' : 'This mode supports the same tools and semantic rendering as diagnosis.' }}</p>
            </div>

            <MessageStream
              v-else
              :events="activePanel.events"
              :isRunning="activePanelRunning"
              :connected="wsConnected"
            />
          </div>
        </div>

        <div class="chat-composer-shell">
          <div class="chat-composer-wrap">
            <div class="chat-hint">
              <template v-if="activePanel.kind === 'diagnose'">
                运行中会直接注入当前诊断会话；已完成/失败/停止时会以 continue 方式恢复
              </template>
              <template v-else>
                Enter to send · Shift+Enter for newline
              </template>
            </div>
            <div class="chat-composer">
              <textarea
                v-model="draft"
                class="chat-input"
                :placeholder="activePanel.kind === 'diagnose' ? '补充诊断说明，或基于当前 session 继续对话…' : 'Message Claude...'"
                :disabled="loading"
                @keydown.enter.exact.prevent="submitMessage"
                @keydown.enter.shift.exact.stop
              />
              <div class="chat-composer-actions">
                <button class="btn btn-primary chat-send-btn" @click="submitMessage" :disabled="!draft.trim() || loading">
                  {{ activePanel.kind === 'diagnose' ? '继续诊断' : (activePanel.chatId ? 'Send' : 'Start Chat') }}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue';
import { api, wsUrl } from '../../api/index.js';
import MessageStream from '../diagnosis/MessageStream.vue';
import { getRunStatusBadgeClass, getRunStatusLabel, normalizeRunSummary } from '../../utils/diagnosisRun.js';

const panels = ref([]);
const activePanelId = ref(null);
const draft = ref('');
const loading = ref(false);
const wsConnected = ref(false);
const currentSession = ref(null);

const chatCatalog = ref([]);
const runCatalog = ref([]);

let socket = null;
let reconnectTimer = null;
let manualClose = false;
let localSeq = 0;
let requestSeq = 0;
const pendingChatRequests = new Map();

const activePanel = computed(() => panels.value.find(item => item.localId === activePanelId.value) || null);
const chatPanels = computed(() => panels.value.filter(item => item.kind === 'chat'));
const diagnosePanels = computed(() => panels.value.filter(item => item.kind === 'diagnose'));
const activePanelTitle = computed(() => activePanel.value?.title || 'New Chat');
const activePanelRunning = computed(() => {
  const panel = activePanel.value;
  if (!panel) return false;
  if (panel.kind === 'chat') return panel.status === 'active';
  return ['running', 'awaiting_input'].includes(panel.status);
});
const canStop = computed(() => {
  const panel = activePanel.value;
  if (!panel) return false;
  if (panel.kind === 'chat') return !!panel.chatId && panel.status === 'active';
  return !!panel.runId && ['running', 'awaiting_input'].includes(panel.status);
});

function nextSeq() {
  localSeq += 1;
  return localSeq;
}

function nextRequestId(prefix = 'req') {
  requestSeq += 1;
  return `${prefix}_${Date.now()}_${requestSeq}`;
}

function shortId(value) {
  return value ? String(value).slice(0, 8) : '--';
}

function runStatusLabel(status) {
  return getRunStatusLabel(status);
}

function runBadgeClass(status) {
  return getRunStatusBadgeClass(status);
}

function createBasePanel(kind, title) {
  return reactive({
    localId: `${kind}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    kind,
    title,
    chatId: null,
    runId: null,
    sessionId: null,
    status: kind === 'chat' ? 'draft' : 'pending',
    events: [],
    subscribed: false,
    hydrated: false,
    metadata: {},
  });
}

function createChatPanel() {
  const panel = createBasePanel('chat', 'New Chat');
  panels.value.unshift(panel);
  activePanelId.value = panel.localId;
  syncCurrentSession(panel);
  draft.value = '';
  return panel;
}

function buildSessionFromPanel(panel) {
  if (!panel) return null;
  return {
    localId: panel.localId,
    kind: panel.kind,
    chatId: panel.chatId || null,
    runId: panel.runId || null,
    sessionId: panel.sessionId || null,
    title: panel.title || null,
    status: panel.status || null,
  };
}

function syncCurrentSession(panel = activePanel.value) {
  currentSession.value = buildSessionFromPanel(panel);
  return currentSession.value;
}

function syncCurrentSessionIfActive(panel) {
  if (panel?.localId && panel.localId === activePanelId.value) syncCurrentSession(panel);
}

function findPanelForSession(session) {
  if (!session) return null;
  return panels.value.find(item => item.localId === session.localId)
    || (session.chatId ? panels.value.find(item => item.kind === 'chat' && item.chatId === session.chatId) : null)
    || (session.runId ? panels.value.find(item => item.kind === 'diagnose' && item.runId === session.runId) : null)
    || null;
}

function buildDiagnoseTitle(run) {
  const normalized = normalizeRunSummary(run);
  const scene = normalized?.scene_name || normalized?.name || normalized?.run_id || 'Diagnose Session';
  return `${scene}`;
}

function ensureDiagnosePanel(run) {
  const normalized = normalizeRunSummary(run);
  if (!normalized?.run_id) return null;
  let panel = panels.value.find(item => item.kind === 'diagnose' && item.runId === normalized.run_id);
  if (!panel) {
    panel = createBasePanel('diagnose', buildDiagnoseTitle(normalized));
    panel.runId = normalized.run_id;
    panel.sessionId = normalized.session_id || normalized.sessionId || null;
    panel.status = normalized.engineStatus || normalized.status || 'pending';
    panel.metadata.run = normalized;
    panels.value.push(panel);
  } else {
    panel.title = buildDiagnoseTitle(normalized);
    panel.sessionId = normalized.session_id || normalized.sessionId || panel.sessionId;
    panel.status = normalized.engineStatus || normalized.status || panel.status;
    panel.metadata.run = normalized;
  }
  return panel;
}

function selectPanel(localId) {
  activePanelId.value = localId;
  const panel = activePanel.value;
  if (!panel) return;
  syncCurrentSession(panel);
  if (panel.kind === 'chat' && panel.chatId) subscribeChatPanel(panel);
  if (panel.kind === 'diagnose' && panel.runId) subscribeDiagnosePanel(panel);
}

function ensureSocket() {
  if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) return;
  manualClose = false;
  socket = new WebSocket(wsUrl());

  socket.onopen = () => {
    wsConnected.value = true;
    sendWS({ type: 'watch_catalog', enabled: true });
    sendWS({ type: 'watch_chats', enabled: true });
    for (const panel of panels.value) {
      if (panel.kind === 'chat' && panel.chatId) {
        sendWS({ type: 'subscribe_chat', chatId: panel.chatId });
        sendWS({ type: 'get_chat_snapshot', chatId: panel.chatId });
      }
      if (panel.kind === 'diagnose' && panel.runId) {
        sendWS({ type: 'subscribe_run', runId: panel.runId });
        sendWS({ type: 'get_run_snapshot', runId: panel.runId });
      }
    }
  };

  socket.onmessage = (event) => {
    try {
      handleWSMessage(JSON.parse(event.data));
    } catch (err) {
      console.error('Failed to parse websocket payload', err);
    }
  };

  socket.onerror = () => {
    wsConnected.value = false;
  };

  socket.onclose = () => {
    wsConnected.value = false;
    socket = null;
    if (!manualClose) {
      reconnectTimer = window.setTimeout(() => {
        reconnectTimer = null;
        ensureSocket();
      }, 1500);
    }
  };
}

function disconnectSocket() {
  manualClose = true;
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
  if (socket) {
    socket.close();
    socket = null;
  }
  wsConnected.value = false;
}

function sendWS(payload) {
  if (!socket || socket.readyState !== WebSocket.OPEN) return false;
  socket.send(JSON.stringify(payload));
  return true;
}

function subscribeChatPanel(panel) {
  if (!panel?.chatId) return;
  ensureSocket();
  if (wsConnected.value) {
    sendWS({ type: 'subscribe_chat', chatId: panel.chatId });
    sendWS({ type: 'get_chat_snapshot', chatId: panel.chatId });
  }
}

function subscribeDiagnosePanel(panel) {
  if (!panel?.runId) return;
  ensureSocket();
  if (wsConnected.value) {
    sendWS({ type: 'subscribe_run', runId: panel.runId });
    sendWS({ type: 'get_run_snapshot', runId: panel.runId });
  }
}

function restoreChatEvent(row) {
  const seq = nextSeq();
  if (row.type === 'user_message') return { ...row, _seq: seq };
  if (row.type === 'message') return { ...row, _seq: seq };
  if (row.type === 'thinking') return { ...row, _seq: seq };
  if (row.type === 'tool_use') return { ...row, _seq: seq };
  if (row.type === 'tool_result') return { ...row, _seq: seq };
  if (row.type === 'stats') return { ...row, _seq: seq };
  if (row.type === 'error') return { ...row, _seq: seq };
  if (row.type === 'complete') return { ...row, _seq: seq };
  if (row.type === 'system') return { ...row, _seq: seq };
  return { ...row, _seq: seq };
}

function setChatSnapshot(panel, payload) {
  panel.chatId = payload.session?.chatId || payload.chatId || panel.chatId;
  panel.sessionId = payload.session?.sessionId || panel.sessionId;
  panel.title = payload.session?.title || panel.title;
  panel.status = payload.session?.status || panel.status;
  panel.events = (payload.events || []).map(item => restoreChatEvent(item));
  panel.hydrated = true;
  syncCurrentSessionIfActive(panel);
}

function setDiagnoseSnapshot(panel, payload) {
  panel.status = payload.liveStatus || payload.run?.engineStatus || payload.run?.status || panel.status;
  panel.metadata.run = normalizeRunSummary(payload.run || panel.metadata.run || {});
  panel.sessionId = payload.run?.session_id || payload.run?.sessionId || panel.metadata.run?.session_id || panel.metadata.run?.sessionId || panel.sessionId;
  if (!panel.title || panel.title === 'Diagnose Session') {
    panel.title = buildDiagnoseTitle(payload.run || panel.metadata.run);
  }
  panel.events = normalizeDiagnoseEvents(payload.events || []);
  panel.hydrated = true;
  syncCurrentSessionIfActive(panel);
}

function normalizeDiagnoseEvents(events) {
  const list = [];
  for (const ev of events || []) {
    if (!ev) continue;
    if (ev.type === 'user_message' && shouldHideDiagnoseUserMessage(ev)) continue;
    list.push({
      ...ev,
      _seq: typeof ev._seq === 'number' ? ev._seq : nextSeq(),
    });
  }
  return list;
}

function shouldHideDiagnoseUserMessage(ev) {
  const text = String(ev?.data?.content || '');
  return text.includes('以下是对你上一轮结构化问题的正式回答，请基于这些答案继续当前诊断');
}

function appendPanelEvent(panel, event) {
  if (!panel || !event) return;
  const next = {
    ...event,
    _seq: typeof event._seq === 'number' ? event._seq : nextSeq(),
  };
  if (panel.kind === 'diagnose' && next.type === 'user_message' && shouldHideDiagnoseUserMessage(next)) return;
  panel.events.push(next);
  if (panel.events.length > 3000) panel.events.splice(0, panel.events.length - 3000);
}

function handleWSMessage(message) {
  switch (message.type) {
    case 'catalog_snapshot':
    case 'catalog_update':
      runCatalog.value = message.data?.runs || [];
      refreshDiagnosePanelsFromCatalog();
      break;
    case 'chat_catalog_snapshot':
      chatCatalog.value = message.data?.chats || [];
      mergeChatPanelsFromCatalog();
      break;
    case 'chat_snapshot': {
      const chatId = message.data?.chatId || message.data?.session?.chatId;
      const panel = panels.value.find(item => item.kind === 'chat' && item.chatId === chatId);
      if (panel) setChatSnapshot(panel, message.data);
      break;
    }
    case 'chat_event': {
      const panel = panels.value.find(item => item.kind === 'chat' && item.chatId === message.data?.chatId);
      if (panel) {
        appendPanelEvent(panel, message.data.event);
        if (message.data.event?.type === 'complete') panel.status = 'completed';
        if (message.data.event?.type === 'error') panel.status = 'failed';
        syncCurrentSessionIfActive(panel);
      }
      break;
    }
    case 'chat_started':
    case 'chat_sent': {
      const requestId = message.data?.clientRequestId || null;
      const pending = requestId ? pendingChatRequests.get(requestId) : null;
      const panel = pending
        ? findPanelForSession(pending)
        : panels.value.find(item => item.kind === 'chat' && item.chatId === message.data?.chatId)
          || (activePanel.value?.kind === 'chat' ? activePanel.value : null);
      if (panel?.kind === 'chat') {
        panel.chatId = message.data?.chatId || panel.chatId;
        panel.sessionId = message.data?.sessionId || panel.sessionId;
        panel.status = 'active';
        subscribeChatPanel(panel);
        syncCurrentSessionIfActive(panel);
      }
      if (requestId) pendingChatRequests.delete(requestId);
      break;
    }
    case 'chat_stopped': {
      const panel = panels.value.find(item => item.kind === 'chat' && item.chatId === message.data?.chatId);
      if (panel) {
        panel.status = message.data?.stopped ? 'stopped' : panel.status;
        syncCurrentSessionIfActive(panel);
      }
      break;
    }
    case 'run_snapshot': {
      const panel = panels.value.find(item => item.kind === 'diagnose' && item.runId === message.data?.runId);
      if (panel) setDiagnoseSnapshot(panel, message.data);
      break;
    }
    case 'run_event': {
      const panel = panels.value.find(item => item.kind === 'diagnose' && item.runId === message.data?.runId);
      if (panel) {
        appendPanelEvent(panel, message.data.event);
        if (message.data.event?.type === 'status' && message.data.event?.data?.status) {
          panel.status = message.data.event.data.status;
        }
        if (message.data.event?.type === 'complete' && message.data.event?.data?.status) {
          panel.status = message.data.event.data.status;
        }
        if (message.data.event?.type === 'error') {
          panel.status = message.data.event?.data?.status || 'failed';
        }
        syncCurrentSessionIfActive(panel);
      }
      break;
    }
    case 'run_updated': {
      const panel = panels.value.find(item => item.kind === 'diagnose' && item.runId === message.data?.runId);
      if (panel) {
        panel.status = message.data?.liveStatus || panel.status;
        panel.metadata.run = normalizeRunSummary(message.data.run || panel.metadata.run || {});
        syncCurrentSessionIfActive(panel);
      }
      refreshDiagnosePanelsFromCatalog();
      break;
    }
    case 'error': {
      const requestId = message.data?.clientRequestId || null;
      const pending = requestId ? pendingChatRequests.get(requestId) : null;
      const panel = pending
        ? findPanelForSession(pending)
        : (message.data?.chatId
          ? panels.value.find(item => item.kind === 'chat' && item.chatId === message.data.chatId)
          : activePanel.value);
      if (panel) {
        appendPanelEvent(panel, {
          type: 'error',
          data: { error: message.data?.message || message.data?.error || 'WebSocket request failed' },
        });
        if (panel.kind === 'chat') panel.status = 'failed';
        syncCurrentSessionIfActive(panel);
      }
      if (requestId) pendingChatRequests.delete(requestId);
      break;
    }
    default:
      break;
  }
}

function mergeChatPanelsFromCatalog() {
  for (const entry of chatCatalog.value) {
    let panel = panels.value.find(item => item.kind === 'chat' && item.chatId === entry.chatId);
    if (!panel && entry.sessionId) {
      panel = panels.value.find(item => item.kind === 'chat' && item.sessionId === entry.sessionId);
    }
    if (!panel) {
      panel = createBasePanel('chat', entry.title || `Chat ${shortId(entry.chatId)}`);
      panels.value.unshift(panel);
    }
    panel.chatId = entry.chatId || panel.chatId;
    panel.sessionId = entry.sessionId || panel.sessionId;
    panel.title = entry.title || panel.title;
    panel.status = entry.status || panel.status;
    syncCurrentSessionIfActive(panel);
    if (!panel.hydrated && panel.chatId) subscribeChatPanel(panel);
  }
}

function refreshDiagnosePanelsFromCatalog() {
  for (const run of runCatalog.value) {
    const panel = ensureDiagnosePanel(run);
    if (panel && !panel.hydrated) subscribeDiagnosePanel(panel);
  }
}

async function refreshChats() {
  try {
    const remote = await api.listChats();
    chatCatalog.value = remote || [];
    mergeChatPanelsFromCatalog();
  } catch (err) {
    console.error('Failed to refresh chats', err);
  }
}

async function refreshDiagnosePanels() {
  try {
    const runs = await api.listRuns();
    runCatalog.value = runs || [];
    refreshDiagnosePanelsFromCatalog();
  } catch (err) {
    console.error('Failed to refresh diagnose sessions', err);
  }
}

async function renameChatPanel(panel) {
  if (!panel?.chatId) return;
  const title = window.prompt('Rename session', panel.title || '');
  if (!title || !title.trim()) return;
  const updated = await api.renameChatSession(panel.chatId, title.trim());
  panel.title = updated.title || title.trim();
  syncCurrentSessionIfActive(panel);
}

async function removeChatPanel(panel) {
  if (!panel) return;
  const ok = window.confirm(`Delete session "${panel.title}"? This will remove its history.`);
  if (!ok) return;
  if (panel.chatId) {
    await api.deleteChatSession(panel.chatId);
  }
  panels.value = panels.value.filter(item => item.localId !== panel.localId);
  if (activePanelId.value === panel.localId) {
    activePanelId.value = panels.value[0]?.localId || null;
    if (!activePanelId.value) createChatPanel();
    else syncCurrentSession(activePanel.value);
  }
}

async function stopActivePanel() {
  const panel = findPanelForSession(currentSession.value) || activePanel.value;
  if (!panel) return;
  if (panel.kind === 'chat' && panel.chatId) {
    if (!sendWS({ type: 'chat_stop', chatId: panel.chatId })) {
      await api.stopChat(panel.chatId).catch(() => {});
    }
    panel.status = 'stopped';
    syncCurrentSessionIfActive(panel);
    return;
  }
  if (panel.kind === 'diagnose' && panel.runId) {
    await api.stopDiagnosis(panel.runId).catch(() => {});
    panel.status = 'stopped';
    syncCurrentSessionIfActive(panel);
  }
}

async function submitMessage() {
  const text = draft.value.trim();
  if (!text) return;
  let session = currentSession.value || syncCurrentSession(activePanel.value);
  let panel = findPanelForSession(session);
  if (!panel) {
    panel = createChatPanel();
    session = syncCurrentSession(panel);
  }
  if (!session) session = syncCurrentSession(panel);

  loading.value = true;
  try {
    if (session.kind === 'chat') {
      panel.events.push({ type: 'user_message', data: { role: 'user', content: text }, _seq: nextSeq() });
      if (!session.chatId) {
        const clientRequestId = nextRequestId('chat_start');
        pendingChatRequests.set(clientRequestId, buildSessionFromPanel(panel));
        const sent = sendWS({
          type: 'chat_start',
          clientRequestId,
          payload: {
            prompt: text,
            permissionMode: 'bypassPermissions',
          },
        });
        if (!sent) {
          pendingChatRequests.delete(clientRequestId);
          const result = await api.startChat({ prompt: text, permissionMode: 'bypassPermissions' });
          panel.chatId = result.chatId;
          panel.sessionId = result.sessionId || null;
          subscribeChatPanel(panel);
          syncCurrentSessionIfActive(panel);
        }
      } else {
        const clientRequestId = nextRequestId('chat_send');
        pendingChatRequests.set(clientRequestId, buildSessionFromPanel(panel));
        const sent = sendWS({
          type: 'chat_send',
          clientRequestId,
          chatId: session.chatId,
          message: text,
          payload: {
            message: text,
            sessionId: session.sessionId,
            permissionMode: 'bypassPermissions',
          },
        });
        if (!sent) {
          pendingChatRequests.delete(clientRequestId);
          const result = await api.sendChatMessage(session.chatId, {
            message: text,
            sessionId: session.sessionId,
            permissionMode: 'bypassPermissions',
          });
          panel.chatId = result.chatId;
          panel.sessionId = result.sessionId || panel.sessionId;
          subscribeChatPanel(panel);
          syncCurrentSessionIfActive(panel);
        }
      }
      panel.status = 'active';
      if (panel.title === 'New Chat') panel.title = text.slice(0, 28);
      syncCurrentSessionIfActive(panel);
    } else if (session.kind === 'diagnose' && session.runId) {
      const running = ['running', 'awaiting_input'].includes(panel.status);
      const sent = running
        ? sendWS({ type: 'run_chat', runId: session.runId, message: text })
        : sendWS({ type: 'run_continue', runId: session.runId, followUpMessage: text });

      if (!sent) {
        if (running) {
          await api.sendChat(session.runId, text);
        } else {
          await api.continueDiagnosis(session.runId, text);
        }
      }
      panel.status = 'running';
      appendPanelEvent(panel, {
        type: 'user_message',
        data: { role: 'user', content: text, source: 'chat_ui' },
      });
      subscribeDiagnosePanel(panel);
      syncCurrentSessionIfActive(panel);
    }
    draft.value = '';
  } catch (err) {
    const target = panel || activePanel.value;
    if (target) {
      appendPanelEvent(target, {
        type: 'error',
        data: { error: err.message || 'Send failed' },
      });
    }
  } finally {
    loading.value = false;
  }
}

onMounted(async () => {
  ensureSocket();
  await Promise.all([refreshChats(), refreshDiagnosePanels()]);
  if (diagnosePanels.value[0]) {
    activePanelId.value = diagnosePanels.value[0].localId;
    syncCurrentSession(diagnosePanels.value[0]);
  } else if (chatPanels.value[0]) {
    activePanelId.value = chatPanels.value[0].localId;
    syncCurrentSession(chatPanels.value[0]);
  } else {
    createChatPanel();
  }
});

onBeforeUnmount(() => {
  disconnectSocket();
});
</script>

<style scoped>
.chat-shell {
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr);
  gap: 0;
  height: calc(100vh - 56px);
  min-height: 0;
  border: none;
  border-radius: 0;
  overflow: hidden;
  background: #050505;
  box-shadow: none;
}

.chat-sidebar,
.chat-main {
  min-height: 0;
}

.chat-sidebar {
  display: flex;
  flex-direction: column;
  background: #050505;
  border-right: 1px solid #272727;
}

.chat-sidebar-top {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 12px 10px 10px;
  border-bottom: none;
}

.chat-sidebar-brand {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.chat-sidebar-kicker {
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text2);
}

.chat-sidebar-heading {
  font-size: 16px;
  font-weight: 700;
  color: var(--text);
}

.chat-sidebar-new {
  width: 100%;
  justify-content: center;
}

.chat-sidebar-groups {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 8px 6px 16px;
}

.chat-sidebar-group + .chat-sidebar-group {
  margin-top: 12px;
}

.chat-sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 8px 10px;
}

.chat-sidebar-header h3 {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--text2);
}

.chat-sidebar-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.chat-session-item {
  width: 100%;
  text-align: left;
  background: transparent;
  border: 1px solid transparent;
  color: var(--text);
  border-radius: 10px;
  padding: 10px 10px 9px;
  cursor: pointer;
  transition: 0.16s ease;
}

.chat-session-item:hover {
  background: #1f1f1f;
  border-color: transparent;
}

.chat-session-item.active {
  background: #2f2f2f;
  border-color: transparent;
  box-shadow: none;
}

.diagnose-item.active {
  background: #2f2f2f;
  border-color: transparent;
}

.chat-session-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}

.chat-session-type {
  display: inline-flex;
  align-items: center;
  padding: 3px 8px;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--accent);
  background: rgba(88,166,255,.10);
}

.diagnose-type {
  color: #22d3ee;
  background: rgba(34,211,238,.10);
}

.chat-session-name {
  font-size: 13px;
  font-weight: 700;
  color: var(--text);
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chat-session-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-size: 12px;
  color: var(--text2);
}

.chat-session-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.session-icon-btn {
  width: 24px;
  height: 24px;
  border-radius: 8px;
  border: 1px solid transparent;
  background: rgba(255,255,255,.03);
  color: var(--text2);
  cursor: pointer;
  transition: .15s ease;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
}

.session-icon-btn:hover {
  color: var(--text);
  border-color: rgba(88,166,255,.18);
  background: rgba(88,166,255,.08);
}

.session-icon-btn.danger:hover {
  color: var(--red);
  border-color: rgba(248,81,73,.18);
  background: rgba(248,81,73,.08);
}

.chat-sidebar-empty {
  padding: 8px;
  color: var(--text2);
  font-size: 12px;
}

.chat-sidebar-footer {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px;
  border-top: 1px solid #272727;
  color: var(--text2);
  font-size: 12px;
}

.chat-connection-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: var(--yellow);
  box-shadow: 0 0 0 4px rgba(210,153,34,.10);
}

.chat-connection-dot.online {
  background: var(--green);
  box-shadow: 0 0 0 4px rgba(63,185,80,.10);
}

.chat-main {
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: #050505;
}

.chat-main-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  height: 52px;
  padding: 0 18px;
  border-bottom: 1px solid #111;
  background: #050505;
  flex-shrink: 0;
}

.chat-model-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: none;
  background: transparent;
  color: #f5f5f5;
  font-size: 20px;
  font-weight: 700;
  cursor: pointer;
  padding: 8px 6px;
}

.chat-model-btn:hover {
  background: #1f1f1f;
  border-radius: 8px;
}

.chat-model-chevron {
  color: #b4b4b4;
  font-size: 16px;
}

.chat-header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.chat-main-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 10px;
}

.chat-main-kind,
.chat-session-chip,
.chat-status {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  background: rgba(255,255,255,.05);
  color: var(--text2);
}

.kind-chat {
  color: var(--accent);
  background: rgba(88,166,255,.10);
}

.kind-diagnose {
  color: #22d3ee;
  background: rgba(34,211,238,.10);
}

.chat-title {
  font-size: 18px;
  line-height: 1.2;
  font-weight: 700;
  color: #f4f7fb;
  margin-bottom: 0;
}

.chat-subtitle {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.chat-status-online {
  color: var(--green);
  background: rgba(63,185,80,.12);
}

.chat-status-offline {
  color: var(--yellow);
  background: rgba(210,153,34,.12);
}

.chat-stage {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  position: relative;
}

.chat-thread-shell {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding: 0;
  overflow: hidden;
}

.chat-session-title {
  width: min(920px, calc(100% - 40px));
  margin: 16px auto 8px;
  flex-shrink: 0;
}

.chat-stage-banner {
  margin: 0 auto 12px;
  width: min(920px, calc(100% - 40px));
  padding: 13px 16px;
  border-radius: 8px;
  border: 1px solid rgba(88,166,255,.18);
  background: rgba(88,166,255,.07);
}

.chat-stage-banner-title {
  font-size: 12px;
  font-weight: 700;
  color: var(--accent);
  text-transform: uppercase;
  letter-spacing: .08em;
}

.chat-stage-banner-text {
  margin-top: 4px;
  font-size: 13px;
  color: var(--text2);
}

.chat-thread {
  flex: 1;
  min-height: 0;
  width: 100%;
  display: flex;
  justify-content: center;
  overflow: hidden;
}

.chat-thread :deep(.message-stream) {
  width: min(920px, calc(100% - 40px));
  height: 100%;
  min-height: 0;
  background: transparent;
  border: none;
  border-radius: 0;
  padding: 16px 0 24px;
  overflow-y: auto;
}

.chat-empty,
.chat-welcome {
  min-height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: var(--text2);
  text-align: center;
  padding: 48px 16px;
}

.chat-empty-icon {
  font-size: 36px;
}

.chat-composer-shell {
  padding: 12px 18px 12px;
  border-top: none;
  background: #050505;
  flex-shrink: 0;
}

.chat-composer-wrap {
  width: 100%;
  max-width: 860px;
  margin: 0 auto;
}

.chat-hint {
  font-size: 12px;
  color: #8f8f8f;
  margin-bottom: 8px;
  padding: 0 4px;
}

.chat-composer {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  align-items: end;
  padding: 10px;
  border-radius: 24px;
  border: 1px solid #3a3a3a;
  background: #252525;
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,0.04),
    0 10px 30px rgba(0,0,0,0.22);
}

.chat-input {
  width: 100%;
  min-height: 50px;
  max-height: 180px;
  border-radius: 18px;
  padding: 13px 14px;
  font-size: 15px;
  resize: vertical;
  background: transparent;
  border: none;
  box-shadow: none;
}

.chat-composer-actions {
  display: flex;
  align-items: center;
  justify-content: center;
  align-self: stretch;
}

.chat-send-btn {
  min-width: 92px;
  height: 44px;
  justify-content: center;
  border-radius: 22px;
}

@media (max-width: 1100px) {
  .chat-shell {
    grid-template-columns: 1fr;
    height: auto;
    min-height: 0;
  }

  .chat-sidebar {
    border-right: none;
    border-bottom: 1px solid rgba(255,255,255,0.06);
  }

  .chat-main-header {
    padding: 16px 18px 14px;
  }

  .chat-thread-shell,
  .chat-composer-shell {
    padding-left: 14px;
    padding-right: 14px;
  }
}

@media (max-width: 760px) {
  .chat-shell {
    border-radius: 16px;
  }

  .chat-main-header {
    flex-direction: column;
    align-items: stretch;
  }

  .chat-title {
    font-size: 22px;
  }

  .chat-composer {
    grid-template-columns: 1fr;
  }

  .chat-send-btn {
    width: 100%;
  }
}
</style>
