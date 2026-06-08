<template>
  <div class="chat-shell">
    <section class="chat-main">
      <div class="chat-topbar">
        <div class="chat-title-group">
          <h2 class="chat-title">{{ activePanelTitle }}</h2>
          <div class="chat-subtitle">
            <span class="chat-session-chip" v-if="activePanel?.sessionId">session: {{ shortId(activePanel.sessionId) }}</span>
            <span class="chat-session-chip" v-if="activePanel?.chatId">chat: {{ shortId(activePanel.chatId) }}</span>
            <span class="chat-session-chip" v-if="activePanel?.runId">run: {{ shortId(activePanel.runId) }}</span>
            <span class="chat-status" :class="wsConnected ? 'chat-status-online' : 'chat-status-offline'">
              {{ wsConnected ? (activePanelRunning ? 'Streaming' : 'Ready') : 'Disconnected' }}
            </span>
          </div>
        </div>
        <div class="chat-topbar-actions">
          <button class="btn" @click="createChatPanel" :disabled="loading">New Chat</button>
          <button class="btn btn-danger" @click="stopActivePanel" :disabled="!canStop">Stop</button>
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
        <div class="chat-stage-banner" v-if="activePanel.kind === 'diagnose'">
          <div class="chat-stage-banner-title">Diagnose Session</div>
          <div class="chat-stage-banner-text">这里展示诊断会话的真实对话内容，并可在同一处继续补充说明。</div>
        </div>

        <div class="chat-scroll">
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
            <div class="chat-hint">
              <template v-if="activePanel.kind === 'diagnose'">
                运行中会直接注入当前诊断会话；已完成/失败/停止时会以 continue 方式恢复
              </template>
              <template v-else>
                Enter to send · Shift+Enter for newline
              </template>
            </div>
            <button class="btn btn-primary" @click="submitMessage" :disabled="!draft.trim() || loading">
              {{ activePanel.kind === 'diagnose' ? '继续诊断' : (activePanel.chatId ? 'Send' : 'Start Chat') }}
            </button>
          </div>
        </div>
      </div>
    </section>

    <aside class="chat-sidebar">
      <div class="chat-sidebar-section">
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
              <div class="chat-session-name">{{ panel.title }}</div>
              <div v-if="panel.chatId" class="chat-session-actions" @click.stop>
                <button class="session-icon-btn" @click="renameChatPanel(panel)">✎</button>
                <button class="session-icon-btn danger" @click="removeChatPanel(panel)">✕</button>
              </div>
            </div>
            <div class="chat-session-meta">
              <span>{{ shortId(panel.sessionId || panel.chatId || panel.localId) }}</span>
              <span :class="['badge', panel.status === 'active' ? 'badge-green' : 'badge-blue']">{{ panel.status === 'active' ? 'active' : 'saved' }}</span>
            </div>
          </button>
          <div v-if="chatPanels.length === 0" class="chat-sidebar-empty">No chat sessions yet.</div>
        </div>
      </div>

      <div class="chat-sidebar-section diagnose-section">
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
              <div class="chat-session-name">{{ panel.title }}</div>
            </div>
            <div class="chat-session-meta">
              <span>{{ shortId(panel.runId) }}</span>
              <span :class="['badge', runBadgeClass(panel.status)]">{{ runStatusLabel(panel.status) }}</span>
            </div>
          </button>
          <div v-if="diagnosePanels.length === 0" class="chat-sidebar-empty">No diagnosis sessions found.</div>
        </div>
      </div>
    </aside>
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

const chatCatalog = ref([]);
const runCatalog = ref([]);

let socket = null;
let reconnectTimer = null;
let manualClose = false;
let localSeq = 0;

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
  draft.value = '';
  return panel;
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
    panel.status = normalized.engineStatus || normalized.status || 'pending';
    panel.metadata.run = normalized;
    panels.value.push(panel);
  } else {
    panel.title = buildDiagnoseTitle(normalized);
    panel.status = normalized.engineStatus || normalized.status || panel.status;
    panel.metadata.run = normalized;
  }
  return panel;
}

function selectPanel(localId) {
  activePanelId.value = localId;
  const panel = activePanel.value;
  if (!panel) return;
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
}

function setDiagnoseSnapshot(panel, payload) {
  panel.status = payload.liveStatus || payload.run?.engineStatus || payload.run?.status || panel.status;
  panel.metadata.run = normalizeRunSummary(payload.run || panel.metadata.run || {});
  if (!panel.title || panel.title === 'Diagnose Session') {
    panel.title = buildDiagnoseTitle(payload.run || panel.metadata.run);
  }
  panel.events = normalizeDiagnoseEvents(panel, payload.events || []);
  panel.hydrated = true;
}

function normalizeDiagnoseEvents(panel, events) {
  const list = [];
  for (const ev of events || []) {
    if (!ev) continue;
    if (ev.type === 'user_message' && shouldHideDiagnoseUserMessage(ev)) {
      continue;
    }
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
  if (panel.kind === 'diagnose' && next.type === 'user_message' && shouldHideDiagnoseUserMessage(next)) {
    return;
  }
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
      }
      break;
    }
    case 'chat_started':
    case 'chat_sent': {
      const panel = activePanel.value;
      if (panel?.kind === 'chat') {
        panel.chatId = message.data?.chatId || panel.chatId;
        panel.sessionId = message.data?.sessionId || panel.sessionId;
        panel.status = 'active';
      }
      break;
    }
    case 'chat_stopped': {
      const panel = panels.value.find(item => item.kind === 'chat' && item.chatId === message.data?.chatId);
      if (panel) panel.status = message.data?.stopped ? 'stopped' : panel.status;
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
      }
      break;
    }
    case 'run_updated': {
      const panel = panels.value.find(item => item.kind === 'diagnose' && item.runId === message.data?.runId);
      if (panel) {
        panel.status = message.data?.liveStatus || panel.status;
        panel.metadata.run = normalizeRunSummary(message.data.run || panel.metadata.run || {});
      }
      refreshDiagnosePanelsFromCatalog();
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
  }
}

async function stopActivePanel() {
  const panel = activePanel.value;
  if (!panel) return;
  if (panel.kind === 'chat' && panel.chatId) {
    if (!sendWS({ type: 'chat_stop', chatId: panel.chatId })) {
      await api.stopChat(panel.chatId).catch(() => {});
    }
    panel.status = 'stopped';
    return;
  }
  if (panel.kind === 'diagnose' && panel.runId) {
    await api.stopDiagnosis(panel.runId).catch(() => {});
    panel.status = 'stopped';
  }
}

async function submitMessage() {
  const text = draft.value.trim();
  if (!text) return;
  let panel = activePanel.value;
  if (!panel) panel = createChatPanel();

  loading.value = true;
  try {
    if (panel.kind === 'chat') {
      panel.events.push({ type: 'user_message', data: { role: 'user', content: text }, _seq: nextSeq() });
      if (!panel.chatId) {
        const sent = sendWS({
          type: 'chat_start',
          payload: {
            prompt: text,
            permissionMode: 'bypassPermissions',
          },
        });
        if (!sent) {
          const result = await api.startChat({ prompt: text, permissionMode: 'bypassPermissions' });
          panel.chatId = result.chatId;
          panel.sessionId = result.sessionId || null;
          subscribeChatPanel(panel);
        }
      } else {
        const sent = sendWS({
          type: 'chat_send',
          chatId: panel.chatId,
          message: text,
          payload: {
            message: text,
            sessionId: panel.sessionId,
            permissionMode: 'bypassPermissions',
          },
        });
        if (!sent) {
          const result = await api.sendChatMessage(panel.chatId, {
            message: text,
            sessionId: panel.sessionId,
            permissionMode: 'bypassPermissions',
          });
          panel.chatId = result.chatId;
          panel.sessionId = result.sessionId || panel.sessionId;
          subscribeChatPanel(panel);
        }
      }
      panel.status = 'active';
      if (panel.title === 'New Chat') panel.title = text.slice(0, 28);
    } else if (panel.kind === 'diagnose' && panel.runId) {
      const running = ['running', 'awaiting_input'].includes(panel.status);
      const sent = running
        ? sendWS({ type: 'run_chat', runId: panel.runId, message: text })
        : sendWS({ type: 'run_continue', runId: panel.runId, followUpMessage: text });

      if (!sent) {
        if (running) {
          await api.sendChat(panel.runId, text);
        } else {
          await api.continueDiagnosis(panel.runId, text);
        }
      }
      panel.status = 'running';
      appendPanelEvent(panel, {
        type: 'user_message',
        data: { role: 'user', content: text, source: 'chat_ui' },
      });
      subscribeDiagnosePanel(panel);
    }
    draft.value = '';
  } catch (err) {
    const target = activePanel.value;
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
  createChatPanel();
  await Promise.all([refreshChats(), refreshDiagnosePanels()]);
  if (!activePanelId.value && panels.value[0]) {
    activePanelId.value = panels.value[0].localId;
  }
});

onBeforeUnmount(() => {
  disconnectSocket();
});
</script>

<style scoped>
.chat-shell {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 18px;
  height: calc(100vh - 120px);
}
.chat-main,
.chat-sidebar {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 16px;
  min-height: 0;
}
.chat-main {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 20px 60px rgba(0,0,0,.18);
}
.chat-topbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 20px;
  border-bottom: 1px solid var(--border);
  background:
    radial-gradient(circle at top left, rgba(88,166,255,.10), transparent 34%),
    linear-gradient(180deg, rgba(255,255,255,.02), rgba(255,255,255,0));
}
.chat-title {
  font-size: 18px;
  font-weight: 700;
}
.chat-subtitle {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 6px;
}
.chat-session-chip,
.chat-status {
  display: inline-flex;
  align-items: center;
  padding: 3px 10px;
  border-radius: 999px;
  background: var(--surface2);
  color: var(--text2);
  font-size: 11px;
}
.chat-status-online {
  color: var(--green);
  background: rgba(63, 185, 80, 0.1);
}
.chat-status-offline {
  color: var(--yellow);
  background: rgba(210, 153, 34, 0.12);
}
.chat-topbar-actions {
  display: flex;
  gap: 10px;
}
.chat-stage {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background:
    radial-gradient(circle at 20% 0%, rgba(124,58,237,.06), transparent 25%),
    radial-gradient(circle at 85% 15%, rgba(34,211,238,.05), transparent 24%);
}
.chat-stage-banner {
  margin: 16px 20px 0;
  padding: 12px 14px;
  border-radius: 14px;
  border: 1px solid rgba(88,166,255,.18);
  background: rgba(88,166,255,.08);
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
.chat-scroll {
  flex: 1;
  overflow: auto;
  padding: 20px 22px 8px;
}
.chat-scroll :deep(.message-stream) {
  min-height: 100%;
}
.chat-welcome,
.chat-empty {
  height: 100%;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 12px;
  color: var(--text2);
  text-align: center;
}
.chat-empty-icon {
  font-size: 32px;
}
.chat-composer {
  border-top: 1px solid var(--border);
  padding: 18px 20px 20px;
  background: linear-gradient(180deg, rgba(13,17,23,0) 0%, rgba(22,27,34,0.95) 14%);
}
.chat-input {
  width: 100%;
  min-height: 110px;
  border-radius: 18px;
  padding: 16px 18px;
  font-size: 15px;
  resize: vertical;
  box-shadow: inset 0 1px 0 rgba(255,255,255,.02);
}
.chat-composer-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 12px;
}
.chat-hint {
  font-size: 12px;
  color: var(--text2);
}
.chat-sidebar {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 18px 50px rgba(0,0,0,.16);
}
.chat-sidebar-section {
  display: flex;
  flex-direction: column;
  min-height: 0;
  flex: 1;
}
.diagnose-section {
  border-top: 1px solid var(--border);
}
.chat-sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 18px 12px;
  border-bottom: 1px solid var(--border);
}
.chat-sidebar-list {
  flex: 1;
  overflow: auto;
  padding: 12px;
}
.chat-session-item {
  width: 100%;
  text-align: left;
  background: transparent;
  border: 1px solid transparent;
  color: var(--text);
  border-radius: 14px;
  padding: 12px;
  margin-bottom: 10px;
  cursor: pointer;
  transition: .16s ease;
}
.chat-session-head {
  display: flex;
  align-items: center;
  gap: 8px;
  justify-content: space-between;
  margin-bottom: 8px;
}
.chat-session-item:hover {
  background: var(--surface2);
  border-color: rgba(88,166,255,.16);
}
.chat-session-item.active {
  background: rgba(88,166,255,.08);
  border-color: rgba(88,166,255,.25);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.03);
}
.diagnose-item.active {
  background: rgba(34,211,238,.10);
  border-color: rgba(34,211,238,.22);
}
.chat-session-name {
  font-size: 13px;
  font-weight: 700;
  color: var(--text);
  min-width: 0;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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
.chat-session-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-size: 12px;
  color: var(--text2);
}
.chat-sidebar-empty {
  padding: 10px 4px;
  color: var(--text2);
  font-size: 12px;
}

@media (max-width: 1100px) {
  .chat-shell {
    grid-template-columns: 1fr;
    height: auto;
  }
  .chat-sidebar {
    min-height: 420px;
  }
}
</style>
