<template>
  <div :class="['chat-shell', { 'chat-shell-collapsed': chatSidebarCollapsed }]">
    <aside class="chat-sidebar">
      <div class="chat-sidebar-top">
        <div class="chat-sidebar-brand-row">
          <div class="chat-sidebar-brand">
            <div class="chat-sidebar-kicker">{{ $t('chat.sidebarKicker') }}</div>
            <div class="chat-sidebar-heading">{{ $t('chat.sidebarHeading') }}</div>
          </div>
          <button
            class="chat-sidebar-toggle"
            type="button"
            :title="chatSidebarCollapsed ? $t('chat.expandSidebar') : $t('chat.collapseSidebar')"
            @click="toggleChatSidebar"
          >
            {{ chatSidebarCollapsed ? '›' : '‹' }}
          </button>
        </div>
        <button class="btn btn-primary chat-sidebar-new" :title="chatSidebarCollapsed ? $t('chat.newChat') : ''" @click="createChatPanel" :disabled="loading">
          <span class="chat-sidebar-new-icon">+</span>
          <span class="chat-sidebar-new-label">{{ $t('chat.newChatLabel') }}</span>
        </button>
      </div>

      <div class="chat-sidebar-groups">
        <div class="chat-sidebar-group">
          <div class="chat-sidebar-header">
            <h3>{{ $t('chat.chatGroup') }}</h3>
            <button class="btn btn-sm" @click="refreshChats">{{ $t('common.refresh') }}</button>
          </div>
          <div class="chat-sidebar-list">
            <button
              v-for="panel in chatPanels"
              :key="panel.localId"
              class="chat-session-item"
              :class="{ active: activePanel?.localId === panel.localId }"
              :title="panel.title"
              @click="selectPanel(panel.localId)"
            >
              <div class="chat-session-head">
                <span class="chat-session-type">{{ $t('chat.chatGroup') }}</span>
                <div v-if="panel.chatId" class="chat-session-actions" @click.stop>
                  <button class="session-icon-btn" @click="renameChatPanel(panel)">✎</button>
                  <button class="session-icon-btn danger" @click="removeChatPanel(panel)">✕</button>
                </div>
              </div>
              <div class="chat-session-avatar">{{ sessionAvatar(panel.title, 'C') }}</div>
              <div class="chat-session-name">{{ panel.title }}</div>
              <div class="chat-session-meta">
                <span>{{ shortId(panel.sessionId || panel.chatId || panel.localId) }}</span>
                <span :class="['badge', panel.status === 'active' ? 'badge-green' : 'badge-blue']">
                  {{ panel.status === 'active' ? $t('chat.active') : $t('chat.saved') }}
                </span>
              </div>
            </button>
            <div v-if="chatPanels.length === 0" class="chat-sidebar-empty">{{ $t('chat.noChats') }}</div>
          </div>
        </div>

        <div class="chat-sidebar-group diagnose-group">
          <div class="chat-sidebar-header">
            <h3>{{ $t('chat.diagnoseGroup') }}</h3>
            <button class="btn btn-sm" @click="refreshDiagnosePanels">{{ $t('common.refresh') }}</button>
          </div>
          <div class="chat-sidebar-list">
            <button
              v-for="panel in diagnosePanels"
              :key="panel.localId"
              class="chat-session-item diagnose-item"
              :class="{ active: activePanel?.localId === panel.localId }"
              :title="panel.title"
              @click="selectPanel(panel.localId)"
            >
              <div class="chat-session-head">
                <span class="chat-session-type diagnose-type">{{ $t('chat.diagnoseGroup') }}</span>
              </div>
              <div class="chat-session-avatar diagnose-avatar">{{ sessionAvatar(panel.title, 'D') }}</div>
              <div class="chat-session-name">{{ panel.title }}</div>
              <div class="chat-session-meta">
                <span>{{ shortId(panel.runId) }}</span>
                <span :class="['badge', runBadgeClass(panel.status)]">{{ runStatusLabel(panel.status) }}</span>
              </div>
            </button>
            <div v-if="diagnosePanels.length === 0" class="chat-sidebar-empty">{{ $t('chat.noDiagnoses') }}</div>
          </div>
        </div>
      </div>

      <div class="chat-sidebar-footer">
        <span class="chat-connection-dot" :class="wsConnected ? 'online' : 'offline'"></span>
        <span>{{ wsConnected ? $t('chat.wsConnected') : $t('chat.wsDisconnected') }}</span>
      </div>
    </aside>

    <section class="chat-main">
      <div class="chat-main-header">
        <button class="chat-model-btn" type="button">
          {{ activePanel?.kind === 'diagnose' ? $t('chat.diagnoseGroup') : $t('chat.chatGroup') }}
          <span class="chat-model-chevron">⌄</span>
        </button>
        <div class="chat-header-actions">
          <span class="chat-status" :class="wsConnected ? 'chat-status-online' : 'chat-status-offline'">
            {{ wsConnected ? (activePanelRunning ? $t('ws.streaming') : $t('ws.ready')) : $t('ws.disconnected') }}
          </span>
          <button class="btn btn-danger btn-sm" @click="stopActivePanel" :disabled="!canStop">{{ $t('common.stop') }}</button>
        </div>
      </div>

      <div class="chat-stage" v-if="!activePanel">
        <div class="chat-empty">
          <div class="chat-empty-icon">💬</div>
          <h3>{{ $t('chat.startConversation') }}</h3>
          <p>{{ $t('chat.startConversationDesc') }}</p>
        </div>
      </div>

      <div v-else class="chat-stage">
        <div class="chat-session-title">
          <div class="chat-main-badges">
            <span class="chat-main-kind" :class="activePanel.kind === 'diagnose' ? 'kind-diagnose' : 'kind-chat'">
              {{ activePanel.kind === 'diagnose' ? $t('chat.diagnoseSession') : $t('chat.chatSession') }}
            </span>
            <span class="chat-session-chip" v-if="activePanel?.sessionId">{{ $t('chat.sessionChip') }}: {{ shortId(activePanel.sessionId) }}</span>
            <span class="chat-session-chip" v-if="activePanel?.chatId">{{ $t('chat.chatChip') }}: {{ shortId(activePanel.chatId) }}</span>
            <span class="chat-session-chip" v-if="activePanel?.runId">{{ $t('chat.runChip') }}: {{ shortId(activePanel.runId) }}</span>
          </div>
          <h2 class="chat-title">{{ activePanelTitle }}</h2>
        </div>

        <div class="chat-thread-shell">
          <div class="chat-stage-banner" v-if="activePanel.kind === 'diagnose'">
            <div class="chat-stage-banner-title">{{ $t('chat.diagnoseBannerTitle') }}</div>
            <div class="chat-stage-banner-text">{{ $t('chat.diagnoseBannerText') }}</div>
          </div>

          <div class="chat-thread">
            <div class="chat-welcome" v-if="activePanel.events.length === 0">
              <div class="chat-empty-icon">✨</div>
              <h3>{{ activePanel.kind === 'diagnose' ? $t('chat.welcomeDiagnose') : $t('chat.welcomeChat') }}</h3>
              <p>{{ activePanel.kind === 'diagnose' ? $t('chat.welcomeDiagnoseDesc') : $t('chat.welcomeChatDesc') }}</p>
            </div>

            <MessageStream
              v-else
              :key="activePanel.localId"
              :events="activePanel.events"
              :isRunning="activePanelRunning"
              :connected="wsConnected"
            />
          </div>
        </div>

        <div class="chat-composer-shell">
          <div class="chat-composer-wrap">
            <div class="chat-composer">
              <textarea
                v-model="draft"
                class="chat-input"
                :placeholder="activePanel.kind === 'diagnose' ? $t('chat.placeholderDiagnose') : $t('chat.placeholderChat')"
                :disabled="loading"
                @keydown.enter.exact.prevent="submitMessage"
                @keydown.enter.shift.exact.stop
              />
              <div class="chat-composer-footer">
                <div class="chat-composer-runtime">
                  <template v-if="activePanel.kind === 'chat'">
                    <button
                      class="chat-inline-control chat-inline-path"
                      type="button"
                      :disabled="runtimeConfigSaving || directoryPickerLoading || isChatCwdLocked(activePanel)"
                      :title="chatCwdControlTitle(activePanel)"
                      @click="pickDirectoryFromSystem()"
                    >
                      <span class="chat-inline-icon">+</span>
                      <span class="chat-inline-text">{{ displayChatCwd(activePanel) }}</span>
                    </button>
                    <label class="chat-inline-select-wrap">
                      <span class="chat-inline-select-icon">!</span>
                      <select
                        class="chat-inline-select"
                        :value="getChatPermissionMode(activePanel)"
                        :disabled="runtimeConfigSaving || directoryPickerLoading"
                        @change="onPermissionModeChange($event.target.value)"
                      >
                        <option v-for="option in permissionModeOptions" :key="option.value" :value="option.value">
                          {{ option.shortLabel }}
                        </option>
                      </select>
                    </label>
                  </template>
                  <span v-else class="chat-inline-note">{{ $t('chat.msgToDiagnoseOnly') }}</span>
                </div>
                <button class="btn btn-primary chat-send-btn" @click="submitMessage" :disabled="!draft.trim() || loading">
                  {{ activePanel.kind === 'diagnose' ? $t('chat.sendToSession') : (activePanel.chatId ? $t('chat.send') : $t('chat.startChatBtn')) }}
                </button>
              </div>
            </div>
            <div v-if="activePanel.kind === 'chat' && (runtimeConfigSaving || directoryPickerLoading || runtimeConfigError || isChatCwdLocked(activePanel))" class="chat-runtime-feedback">
              <span v-if="runtimeConfigSaving">{{ $t('chat.savingConfig') }}</span>
              <span v-else-if="directoryPickerLoading">{{ $t('chat.openingPicker') }}</span>
              <span v-else-if="!runtimeConfigError && isChatCwdLocked(activePanel)">{{ $t('chat.cwdLockedHint') }}</span>
              <span v-else>{{ runtimeConfigError }}</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { api, wsUrl } from '../../api/index.js';
import MessageStream from '../diagnosis/MessageStream.vue';
import { getRunStatusBadgeClass, getRunStatusLabel, normalizeRunSummary } from '../../utils/diagnosisRun.js';

const { t } = useI18n();

const panels = ref([]);
const activePanelId = ref(null);
const draft = ref('');
const loading = ref(false);
const wsConnected = ref(false);
const currentSession = ref(null);
const runtimeConfigSaving = ref(false);
const runtimeConfigError = ref('');
const directoryPickerLoading = ref(false);
const chatSidebarCollapsed = ref(false);

const chatCatalog = ref([]);
const runCatalog = ref([]);

const DEFAULT_CHAT_CWD = '/Volumes/laxer/codes/skills/industrial-deep-diagnostic';
const permissionModeOptions = computed(() => [
  { value: 'default', shortLabel: t('chat.permission_default') },
  { value: 'acceptEdits', shortLabel: t('chat.permission_acceptEdits') },
  { value: 'dontAsk', shortLabel: t('chat.permission_dontAsk') },
  { value: 'auto', shortLabel: t('chat.permission_auto') },
  { value: 'plan', shortLabel: t('chat.permission_plan') },
  { value: 'bypassPermissions', shortLabel: t('chat.permission_bypassPermissions') },
]);

let socket = null;
let reconnectTimer = null;
let manualClose = false;
let localSeq = 0;
let requestSeq = 0;
const pendingChatRequests = new Map();

const activePanel = computed(() => panels.value.find(item => item.localId === activePanelId.value) || null);
const chatPanels = computed(() => panels.value.filter(item => item.kind === 'chat'));
const diagnosePanels = computed(() => panels.value.filter(item => item.kind === 'diagnose'));
const activePanelTitle = computed(() => activePanel.value?.title || t('chat.newChatLabel'));
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

function loadChatSidebarState() {
  try {
    chatSidebarCollapsed.value = localStorage.getItem('idd.chatSidebarCollapsed') === '1';
  } catch {}
}

function toggleChatSidebar() {
  chatSidebarCollapsed.value = !chatSidebarCollapsed.value;
  try {
    localStorage.setItem('idd.chatSidebarCollapsed', chatSidebarCollapsed.value ? '1' : '0');
  } catch {}
}

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

function sessionAvatar(value, fallback = '?') {
  const text = String(value || '').trim();
  return text ? text.charAt(0).toUpperCase() : fallback;
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
    originSessionId: null,
    currentSessionId: null,
    cwd: kind === 'chat' ? DEFAULT_CHAT_CWD : null,
    permissionMode: kind === 'chat' ? 'default' : null,
    status: kind === 'chat' ? 'draft' : 'pending',
    events: [],
    subscribed: false,
    hydrated: false,
    metadata: {},
  });
}

function createChatPanel() {
  const panel = createBasePanel('chat', t('chat.newChatLabel'));
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
    originSessionId: panel.originSessionId || null,
    currentSessionId: panel.currentSessionId || null,
    cwd: panel.cwd || null,
    permissionMode: panel.permissionMode || null,
    title: panel.title || null,
    status: panel.status || null,
  };
}

function getChatPermissionMode(panel) {
  return panel?.permissionMode || 'default';
}

function getChatCwd(panel) {
  return panel?.cwd || DEFAULT_CHAT_CWD;
}

function isChatCwdLocked(panel) {
  if (!panel || panel.kind !== 'chat') return true;
  return !!panel.chatId || ['active', 'completed', 'failed', 'stopped'].includes(panel.status);
}

function chatCwdControlTitle(panel) {
  return isChatCwdLocked(panel)
    ? t('chat.cwdLockedTitle')
    : t('chat.cwdPickTitle');
}

function displayChatCwd(panel) {
  return shortPath(getChatCwd(panel));
}

function shortPath(value) {
  if (!value) return t('common.notSet');
  const str = String(value);
  if (str.length <= 42) return str;
  return `...${str.slice(-39)}`;
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
  const scene = normalized?.scene_name || normalized?.name || normalized?.run_id || t('chat.diagnoseDefaultTitle');
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
    panel.originSessionId = normalized.session_id || normalized.sessionId || panel.originSessionId || null;
    panel.currentSessionId = normalized.session_id || normalized.sessionId || panel.currentSessionId || null;
    panel.status = normalized.engineStatus || normalized.status || 'pending';
    panel.metadata.run = normalized;
    panels.value.push(panel);
  } else {
    panel.title = buildDiagnoseTitle(normalized);
    panel.sessionId = normalized.session_id || normalized.sessionId || panel.sessionId;
    panel.originSessionId = normalized.session_id || normalized.sessionId || panel.originSessionId || panel.sessionId;
    panel.currentSessionId = normalized.session_id || normalized.sessionId || panel.currentSessionId || panel.sessionId;
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
  panel.originSessionId = payload.session?.originSessionId || payload.session?.sessionId || panel.originSessionId || panel.sessionId;
  panel.currentSessionId = payload.session?.currentSessionId || panel.currentSessionId || panel.sessionId;
  panel.permissionMode = payload.session?.permissionMode || panel.permissionMode || 'default';
  panel.cwd = payload.session?.cwd || panel.cwd || DEFAULT_CHAT_CWD;
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
  panel.originSessionId = panel.sessionId || panel.originSessionId;
  panel.currentSessionId = panel.sessionId || panel.currentSessionId;
  if (!panel.title || panel.title === t('chat.diagnoseDefaultTitle')) {
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
        panel.originSessionId = message.data?.originSessionId || message.data?.sessionId || panel.originSessionId || panel.sessionId;
        panel.currentSessionId = message.data?.currentSessionId || panel.currentSessionId || panel.sessionId;
        panel.permissionMode = message.data?.permissionMode || panel.permissionMode || 'default';
        panel.cwd = message.data?.cwd || panel.cwd || DEFAULT_CHAT_CWD;
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
    case 'run_chat_ack':
    case 'run_continue_ack': {
      const panel = panels.value.find(item => item.kind === 'diagnose' && item.runId === message.data?.runId);
      if (panel) {
        if (message.type === 'run_continue_ack') {
          panel.status = message.data?.status || 'running';
        }
        syncCurrentSessionIfActive(panel);
      }
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
          data: { error: message.data?.message || message.data?.error || t('chat.wsRequestFailed') },
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
      panel = createBasePanel('chat', entry.title || `${t('chat.chatGroup')} ${shortId(entry.chatId)}`);
      panels.value.unshift(panel);
    }
    panel.chatId = entry.chatId || panel.chatId;
    panel.sessionId = entry.sessionId || panel.sessionId;
    panel.originSessionId = entry.originSessionId || entry.sessionId || panel.originSessionId || panel.sessionId;
    panel.currentSessionId = entry.currentSessionId || panel.currentSessionId || panel.sessionId;
    panel.permissionMode = entry.permissionMode || panel.permissionMode || 'default';
    panel.cwd = entry.cwd || panel.cwd || DEFAULT_CHAT_CWD;
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

async function persistChatConfig(panel, patch = {}) {
  if (!panel || panel.kind !== 'chat') return;
  const previousPermissionMode = panel.permissionMode || 'default';
  const previousCwd = panel.cwd || DEFAULT_CHAT_CWD;
  runtimeConfigError.value = '';

  if (patch.permissionMode != null) panel.permissionMode = patch.permissionMode;
  if (patch.cwd != null) panel.cwd = patch.cwd;
  syncCurrentSessionIfActive(panel);

  if (!panel.chatId) return;

  runtimeConfigSaving.value = true;
  try {
    const updated = await api.updateChatSessionConfig(panel.chatId, patch);
    panel.permissionMode = updated.permissionMode || panel.permissionMode || 'default';
    panel.cwd = updated.cwd || panel.cwd || DEFAULT_CHAT_CWD;
    syncCurrentSessionIfActive(panel);
  } catch (err) {
    panel.permissionMode = previousPermissionMode;
    panel.cwd = previousCwd;
    runtimeConfigError.value = err.message || t('chat.configSaveFailed');
    syncCurrentSessionIfActive(panel);
    throw err;
  } finally {
    runtimeConfigSaving.value = false;
  }
}

async function onPermissionModeChange(value) {
  const panel = activePanel.value;
  if (!panel || panel.kind !== 'chat') return;
  try {
    await persistChatConfig(panel, { permissionMode: value });
  } catch {}
}

async function pickDirectoryFromSystem() {
  const panel = activePanel.value;
  if (!panel || panel.kind !== 'chat') return;
  if (isChatCwdLocked(panel)) {
    runtimeConfigError.value = t('chat.cwdLockedHint');
    return;
  }
  runtimeConfigError.value = '';
  directoryPickerLoading.value = true;
  try {
    const result = await api.pickChatDirectory(getChatCwd(panel));
    if (result?.canceled || !result?.path) return;
    await persistChatConfig(panel, { cwd: result.path });
  } catch {}
  finally {
    directoryPickerLoading.value = false;
  }
}

async function renameChatPanel(panel) {
  if (!panel?.chatId) return;
  const title = window.prompt(t('chat.renameTitle'), panel.title || '');
  if (!title || !title.trim()) return;
  const updated = await api.renameChatSession(panel.chatId, title.trim());
  panel.title = updated.title || title.trim();
  syncCurrentSessionIfActive(panel);
}

async function removeChatPanel(panel) {
  if (!panel) return;
  const ok = window.confirm(t('chat.deleteConfirm', { title: panel.title }));
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
            permissionMode: getChatPermissionMode(panel),
            cwd: getChatCwd(panel),
          },
        });
        if (!sent) {
          pendingChatRequests.delete(clientRequestId);
          const result = await api.startChat({
            prompt: text,
            permissionMode: getChatPermissionMode(panel),
            cwd: getChatCwd(panel),
          });
          panel.chatId = result.chatId;
          panel.sessionId = result.sessionId || null;
          panel.originSessionId = result.originSessionId || result.sessionId || null;
          panel.currentSessionId = result.currentSessionId || result.sessionId || null;
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
            originSessionId: session.originSessionId || session.sessionId,
            permissionMode: getChatPermissionMode(panel),
            cwd: getChatCwd(panel),
          },
        });
        if (!sent) {
          pendingChatRequests.delete(clientRequestId);
          const result = await api.sendChatMessage(session.chatId, {
            message: text,
            sessionId: session.sessionId,
            originSessionId: session.originSessionId || session.sessionId,
            permissionMode: getChatPermissionMode(panel),
            cwd: getChatCwd(panel),
          });
          panel.chatId = result.chatId;
          panel.sessionId = result.sessionId || panel.sessionId;
          panel.originSessionId = result.originSessionId || result.sessionId || panel.originSessionId || panel.sessionId;
          panel.currentSessionId = result.currentSessionId || panel.currentSessionId || panel.sessionId;
          subscribeChatPanel(panel);
          syncCurrentSessionIfActive(panel);
        }
      }
      panel.status = 'active';
      if (panel.title === t('chat.newChatLabel')) panel.title = text.slice(0, 28);
      syncCurrentSessionIfActive(panel);
    } else if (session.kind === 'diagnose' && session.runId) {
      const sent = sendWS({ type: 'run_chat', runId: session.runId, message: text });

      if (!sent) {
        await api.sendChat(session.runId, text);
      }
      panel.metadata.run = {
        ...(panel.metadata.run || {}),
        error_message: '',
      };
      subscribeDiagnosePanel(panel);
      syncCurrentSessionIfActive(panel);
    }
    draft.value = '';
  } catch (err) {
    const target = panel || activePanel.value;
    if (target) {
      appendPanelEvent(target, {
        type: 'error',
        data: { error: err.message || t('chat.sendFailed') },
      });
    }
  } finally {
    loading.value = false;
  }
}

onMounted(async () => {
  loadChatSidebarState();
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
  grid-template-columns: 216px minmax(0, 1fr);
  gap: 0;
  height: 100%;
  min-height: 0;
  border: none;
  border-radius: 24px;
  overflow: hidden;
  background:
    radial-gradient(circle at top left, color-mix(in srgb, var(--accent) 12%, transparent), transparent 24%),
    radial-gradient(circle at top right, color-mix(in srgb, var(--purple) 12%, transparent), transparent 22%),
    linear-gradient(180deg, color-mix(in srgb, var(--surface-soft) 82%, transparent), color-mix(in srgb, var(--surface) 88%, transparent));
  border: 1px solid var(--border);
  box-shadow: var(--shadow-md);
  backdrop-filter: blur(var(--acrylic-blur-lg)) saturate(var(--acrylic-sat));
  -webkit-backdrop-filter: blur(var(--acrylic-blur-lg)) saturate(var(--acrylic-sat));
}

.chat-shell.chat-shell-collapsed {
  grid-template-columns: 78px minmax(0, 1fr);
}

.chat-sidebar,
.chat-main {
  min-height: 0;
}

.chat-sidebar {
  display: flex;
  flex-direction: column;
  background: color-mix(in srgb, var(--bg-sidebar) 94%, transparent);
  border-right: 1px solid var(--border);
  backdrop-filter: blur(var(--acrylic-blur)) saturate(var(--acrylic-sat));
  -webkit-backdrop-filter: blur(var(--acrylic-blur)) saturate(var(--acrylic-sat));
  box-shadow: var(--glass-highlight);
}

.chat-sidebar-top {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px 10px 10px;
  border-bottom: none;
}

.chat-sidebar-brand-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.chat-sidebar-brand {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  flex: 1;
}

.chat-sidebar-kicker {
  font-size: 10px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--text3);
}

.chat-sidebar-heading {
  font-size: 16px;
  font-weight: 700;
  color: var(--text);
}

.chat-sidebar-toggle {
  width: 30px;
  height: 30px;
  border-radius: 10px;
  border: 1px solid var(--border);
  background: color-mix(in srgb, var(--surface-soft) 88%, transparent);
  color: var(--text2);
  cursor: pointer;
  transition: 0.16s ease;
  flex: 0 0 auto;
}

.chat-sidebar-toggle:hover {
  color: var(--text);
  border-color: var(--border-strong);
  background: color-mix(in srgb, var(--surface-strong) 92%, transparent);
}

.chat-sidebar-new {
  width: 100%;
  justify-content: center;
  min-height: 36px;
  border-radius: 12px;
  background: linear-gradient(180deg, rgba(31, 111, 235, 0.96), rgba(20, 91, 201, 0.96));
  box-shadow: 0 12px 32px rgba(12, 33, 75, 0.35);
  padding: 0 12px;
}

.chat-sidebar-new-icon {
  font-size: 16px;
  line-height: 1;
}

.chat-sidebar-new-label {
  white-space: nowrap;
}

.chat-sidebar-groups {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 4px 6px 10px;
}

.chat-sidebar-group + .chat-sidebar-group {
  margin-top: 14px;
}

.chat-sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 6px 8px;
}

.chat-sidebar-header h3 {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--text3);
}

.chat-sidebar-list {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.chat-session-item {
  width: 100%;
  text-align: left;
  background: color-mix(in srgb, var(--surface) 88%, transparent);
  border: 1px solid color-mix(in srgb, var(--border) 92%, transparent);
  color: var(--text);
  border-radius: 13px;
  padding: 9px 9px 9px;
  cursor: pointer;
  transition: 0.18s ease;
}

.chat-session-item:hover {
  background: color-mix(in srgb, var(--surface-soft) 92%, transparent);
  border-color: var(--border-strong);
  transform: translateY(-1px);
}

.chat-session-item.active {
  background: linear-gradient(180deg, color-mix(in srgb, var(--surface-soft) 94%, transparent), color-mix(in srgb, var(--surface) 96%, transparent));
  border-color: color-mix(in srgb, var(--accent) 26%, var(--border));
  box-shadow: var(--shadow-sm);
}

.diagnose-item.active {
  border-color: color-mix(in srgb, var(--cyan) 28%, var(--border));
}

.chat-session-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 7px;
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
  background: color-mix(in srgb, var(--accent) 12%, transparent);
  border: 1px solid color-mix(in srgb, var(--accent) 20%, transparent);
}

.chat-session-avatar {
  width: 28px;
  height: 28px;
  border-radius: 10px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 8px;
  background: color-mix(in srgb, var(--accent) 12%, transparent);
  border: 1px solid color-mix(in srgb, var(--accent) 18%, transparent);
  color: var(--accent);
  font-size: 12px;
  font-weight: 800;
}

.diagnose-avatar {
  background: color-mix(in srgb, var(--cyan) 12%, transparent);
  border-color: color-mix(in srgb, var(--cyan) 18%, transparent);
  color: var(--cyan);
}

.diagnose-type {
  color: var(--cyan);
  background: color-mix(in srgb, var(--cyan) 12%, transparent);
  border-color: color-mix(in srgb, var(--cyan) 18%, transparent);
}

.chat-session-name {
  font-size: 12px;
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
  font-size: 10px;
  color: var(--text3);
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
  border: 1px solid rgba(255, 255, 255, 0.04);
  background: color-mix(in srgb, var(--surface-soft) 85%, transparent);
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
  border-color: color-mix(in srgb, var(--accent) 24%, transparent);
  background: color-mix(in srgb, var(--accent) 10%, transparent);
}

.session-icon-btn.danger:hover {
  color: var(--red);
  border-color: color-mix(in srgb, var(--red) 24%, transparent);
  background: color-mix(in srgb, var(--red) 10%, transparent);
}

.chat-sidebar-empty {
  padding: 10px 8px;
  color: var(--text3);
  font-size: 12px;
  line-height: 1.5;
}

.chat-sidebar-footer {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 12px 10px;
  border-top: 1px solid var(--border);
  color: var(--text2);
  font-size: 11px;
  background: linear-gradient(180deg, transparent, color-mix(in srgb, var(--bg-sidebar) 96%, transparent));
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
  background:
    linear-gradient(180deg, color-mix(in srgb, var(--surface-soft) 82%, transparent), color-mix(in srgb, var(--surface) 96%, transparent)),
    radial-gradient(circle at top, color-mix(in srgb, var(--accent) 10%, transparent), transparent 32%);
}

.chat-main-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  height: 44px;
  padding: 0 14px;
  border-bottom: 1px solid var(--border);
  background: color-mix(in srgb, var(--surface) 88%, transparent);
  backdrop-filter: blur(14px);
  flex-shrink: 0;
}

.chat-model-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: none;
  background: transparent;
  color: var(--text);
  font-size: 15px;
  font-weight: 700;
  cursor: pointer;
  padding: 8px 8px;
  border-radius: 12px;
}

.chat-model-btn:hover {
  background: color-mix(in srgb, var(--surface-soft) 88%, transparent);
}

.chat-model-chevron {
  color: var(--text2);
  font-size: 15px;
}

.chat-header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.chat-main-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 8px;
}

.chat-main-kind,
.chat-session-chip,
.chat-status {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 600;
  background: color-mix(in srgb, var(--surface-soft) 88%, transparent);
  color: var(--text2);
  border: 1px solid var(--border);
}

.kind-chat {
  color: var(--accent);
  background: color-mix(in srgb, var(--accent) 12%, transparent);
}

.kind-diagnose {
  color: var(--cyan);
  background: color-mix(in srgb, var(--cyan) 12%, transparent);
}

.chat-title {
  font-size: 22px;
  line-height: 1.1;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 0;
  letter-spacing: -0.02em;
}

.chat-subtitle {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.chat-status-online {
  color: var(--green);
  background: color-mix(in srgb, var(--green) 14%, transparent);
}

.chat-status-offline {
  color: var(--yellow);
  background: color-mix(in srgb, var(--yellow) 14%, transparent);
}

.chat-stage {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  position: relative;
  background: radial-gradient(circle at top center, color-mix(in srgb, var(--accent) 7%, transparent), transparent 28%);
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
  width: min(1180px, calc(100% - 18px));
  margin: 10px auto 6px;
  flex-shrink: 0;
}

.chat-stage-banner {
  margin: 0 auto 6px;
  width: min(1180px, calc(100% - 18px));
  padding: 8px 12px;
  border-radius: 18px;
  border: 1px solid color-mix(in srgb, var(--accent) 16%, var(--border));
  background: linear-gradient(180deg, color-mix(in srgb, var(--surface-soft) 96%, transparent), color-mix(in srgb, var(--surface) 96%, transparent));
  box-shadow: var(--shadow-sm);
}

.chat-stage-banner-title {
  font-size: 11px;
  font-weight: 700;
  color: var(--accent);
  text-transform: uppercase;
  letter-spacing: .08em;
}

.chat-stage-banner-text {
  margin-top: 4px;
  font-size: 12px;
  color: var(--text2);
}

.chat-thread {
  flex: 1;
  min-height: 0;
  width: 100%;
  display: flex;
  justify-content: center;
  overflow: hidden;
  padding: 0 4px;
}

.chat-thread :deep(.message-stream) {
  width: min(1180px, 100%);
  height: 100%;
  min-height: 0;
  background: transparent;
  border: none;
  border-radius: 0;
  padding: 6px 0 14px;
  overflow-y: auto;
  scroll-padding-bottom: 28px;
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
  width: 64px;
  height: 64px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 26px;
  border-radius: 20px;
  background: linear-gradient(180deg, color-mix(in srgb, var(--accent) 18%, transparent), color-mix(in srgb, var(--purple) 10%, transparent));
  border: 1px solid var(--border);
  box-shadow: var(--shadow-sm);
}

.chat-composer-shell {
  padding: 6px 12px 8px;
  border-top: none;
  background: linear-gradient(180deg, transparent, color-mix(in srgb, var(--surface) 84%, transparent) 34%, color-mix(in srgb, var(--surface) 96%, transparent) 100%);
  flex-shrink: 0;
}

.chat-composer-wrap {
  width: 100%;
  max-width: 1180px;
  margin: 0 auto;
}

.chat-composer {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 18px;
  border: 1px solid var(--border);
  background: linear-gradient(180deg, color-mix(in srgb, var(--surface-strong) 96%, transparent), color-mix(in srgb, var(--surface) 98%, transparent));
  box-shadow: var(--shadow-md);
  backdrop-filter: blur(18px);
}

.chat-input {
  width: 100%;
  min-height: 72px;
  max-height: 160px;
  border-radius: 16px;
  padding: 3px 5px;
  font-size: 15px;
  resize: vertical;
  background: transparent;
  border: none;
  box-shadow: none;
  line-height: 1.6;
}

.chat-input::placeholder {
  color: var(--text3);
}

.chat-composer-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: 34px;
}

.chat-composer-runtime {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  flex: 1;
}

.chat-inline-control,
.chat-inline-select-wrap,
.chat-inline-note {
  min-height: 32px;
  border-radius: 999px;
  border: 1px solid var(--border);
  background: color-mix(in srgb, var(--surface-soft) 90%, transparent);
  color: var(--text);
}

.chat-inline-control,
.chat-inline-select-wrap {
  transition: border-color 0.16s ease, background 0.16s ease, transform 0.16s ease;
}

.chat-inline-control:hover,
.chat-inline-select-wrap:hover {
  border-color: color-mix(in srgb, var(--accent) 22%, transparent);
  background: color-mix(in srgb, var(--surface-strong) 92%, transparent);
}

.chat-inline-control {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  max-width: 100%;
  padding: 0 12px;
  cursor: pointer;
}

.chat-inline-control:disabled,
.chat-inline-select:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.chat-inline-icon,
.chat-inline-select-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  flex: 0 0 auto;
  color: var(--accent);
  font-size: 18px;
  line-height: 1;
}

.chat-inline-text,
.chat-inline-note {
  font-size: 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.chat-inline-select-wrap {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 0 10px;
}

.chat-inline-select {
  appearance: none;
  border: none;
  background: transparent;
  color: var(--text);
  font-size: 12px;
  font-weight: 600;
  min-width: 88px;
  padding-right: 18px;
  box-shadow: none;
}

.chat-inline-select:focus {
  box-shadow: none;
}

.chat-inline-note {
  display: inline-flex;
  align-items: center;
  padding: 0 12px;
  color: var(--text2);
}

.chat-send-btn {
  min-width: 96px;
  height: 36px;
  justify-content: center;
  border-radius: 18px;
  font-weight: 700;
  box-shadow: 0 14px 28px color-mix(in srgb, var(--accent) 18%, transparent);
}

.chat-runtime-feedback {
  margin-top: 6px;
  padding: 0 4px;
  font-size: 12px;
  color: var(--text3);
}

.chat-shell.chat-shell-collapsed .chat-sidebar {
  align-items: stretch;
}

.chat-shell.chat-shell-collapsed .chat-sidebar-top {
  padding-left: 8px;
  padding-right: 8px;
}

.chat-shell.chat-shell-collapsed .chat-sidebar-brand {
  display: none;
}

.chat-shell.chat-shell-collapsed .chat-sidebar-brand-row {
  justify-content: center;
}

.chat-shell.chat-shell-collapsed .chat-sidebar-new {
  min-width: 0;
  padding: 0;
}

.chat-shell.chat-shell-collapsed .chat-sidebar-new-label,
.chat-shell.chat-shell-collapsed .chat-sidebar-header h3,
.chat-shell.chat-shell-collapsed .chat-sidebar-header .btn,
.chat-shell.chat-shell-collapsed .chat-session-name,
.chat-shell.chat-shell-collapsed .chat-session-meta,
.chat-shell.chat-shell-collapsed .chat-sidebar-empty,
.chat-shell.chat-shell-collapsed .chat-sidebar-footer span:last-child {
  display: none;
}

.chat-shell.chat-shell-collapsed .chat-sidebar-groups {
  padding-left: 8px;
  padding-right: 8px;
}

.chat-shell.chat-shell-collapsed .chat-sidebar-header {
  justify-content: center;
  padding-left: 0;
  padding-right: 0;
}

.chat-shell.chat-shell-collapsed .chat-session-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 8px 6px;
  border-radius: 14px;
}

.chat-shell.chat-shell-collapsed .chat-session-head {
  margin-bottom: 6px;
}

.chat-shell.chat-shell-collapsed .chat-session-type {
  padding: 3px 6px;
  font-size: 9px;
}

.chat-shell.chat-shell-collapsed .chat-session-actions {
  display: none;
}

.chat-shell.chat-shell-collapsed .chat-session-avatar {
  width: 34px;
  height: 34px;
  margin-bottom: 0;
}

.chat-shell.chat-shell-collapsed .chat-sidebar-footer {
  justify-content: center;
  padding-left: 8px;
  padding-right: 8px;
}

@media (max-width: 1100px) {
  .chat-shell {
    grid-template-columns: 1fr;
    height: auto;
    min-height: 0;
  }

  .chat-sidebar {
    border-right: none;
    border-bottom: 1px solid var(--border);
  }

  .chat-main-header {
    padding: 0 12px;
  }

  .chat-session-title,
  .chat-stage-banner {
    width: min(1180px, calc(100% - 12px));
  }
}

@media (max-width: 760px) {
  .chat-sidebar-top {
    padding: 16px 12px 12px;
  }

  .chat-main-header {
    flex-direction: column;
    align-items: stretch;
    justify-content: center;
    height: auto;
    padding: 14px 16px;
  }

  .chat-title {
    font-size: 22px;
  }

  .chat-thread {
    padding: 0 8px;
  }

  .chat-composer-shell {
    padding: 14px 12px 16px;
  }

  .chat-composer {
    border-radius: 22px;
  }

  .chat-composer-footer {
    flex-direction: column;
    align-items: stretch;
  }

  .chat-composer-runtime {
    flex-wrap: wrap;
  }

  .chat-inline-control,
  .chat-inline-select-wrap,
  .chat-inline-note {
    width: 100%;
  }

  .chat-send-btn {
    width: 100%;
  }
}
</style>
