<template>
  <div class="chat-shell">
    <section class="chat-main">
      <div class="chat-topbar">
        <div class="chat-title-group">
          <h2 class="chat-title">{{ activeSession?.title || 'New Chat' }}</h2>
          <div class="chat-subtitle">
            <span class="chat-session-chip" v-if="activeSession?.sessionId">session: {{ shortId(activeSession.sessionId) }}</span>
            <span class="chat-session-chip" v-if="activeSession?.chatId">chat: {{ shortId(activeSession.chatId) }}</span>
            <span class="chat-status" :class="connected ? 'chat-status-online' : 'chat-status-offline'">
              {{ connected ? (isRunning ? 'Streaming' : 'Ready') : 'Disconnected' }}
            </span>
          </div>
        </div>
        <div class="chat-topbar-actions">
          <button class="btn" @click="createChat" :disabled="loading">New Chat</button>
          <button class="btn btn-danger" @click="stopActiveChat" :disabled="!canStop">Stop</button>
        </div>
      </div>

      <div class="chat-stage" v-if="!activeSession">
        <div class="chat-empty">
          <div class="chat-empty-icon">💬</div>
          <h3>Start a normal conversation</h3>
          <p>Use the same Claude backend, but in a plain chat mode.</p>
        </div>
      </div>

      <div v-else class="chat-stage">
        <div class="chat-scroll">
          <div class="chat-welcome" v-if="activeSession.userMessages.length === 0 && renderedEvents.length === 0">
            <div class="chat-empty-icon">✨</div>
            <h3>What would you like to ask?</h3>
            <p>This mode supports the same streaming, tools, and semantic rendering as diagnosis.</p>
          </div>

          <div v-for="message in chatTimeline" :key="message.key" class="chat-row" :class="message.role === 'user' ? 'chat-row-user' : 'chat-row-assistant'">
            <template v-if="message.role === 'user'">
              <div class="chat-bubble chat-bubble-user">{{ message.content }}</div>
            </template>
            <template v-else>
              <div class="chat-avatar">C</div>
              <div class="chat-assistant-panel">
                <MessageStream
                  :events="message.events"
                  :isRunning="message.isRunning"
                  :connected="connected"
                />
              </div>
            </template>
          </div>
        </div>

        <div class="chat-composer">
          <textarea
            v-model="draft"
            class="chat-input"
            placeholder="Message Claude..."
            :disabled="loading"
            @keydown.enter.exact.prevent="submitMessage"
            @keydown.enter.shift.exact.stop
          />
          <div class="chat-composer-actions">
            <div class="chat-hint">Enter to send · Shift+Enter for newline</div>
            <button class="btn btn-primary" @click="submitMessage" :disabled="!draft.trim() || loading">
              {{ activeSession ? 'Send' : 'Start Chat' }}
            </button>
          </div>
        </div>
      </div>
    </section>

    <aside class="chat-sidebar">
      <div class="chat-sidebar-header">
        <h3>Sessions</h3>
        <button class="btn btn-sm" @click="refreshSessions">Refresh</button>
      </div>
      <div class="chat-sidebar-list">
        <button
          v-for="session in sessions"
          :key="session.localId"
          class="chat-session-item"
          :class="{ active: activeSession?.localId === session.localId }"
          @click="selectSession(session.localId)"
        >
          <div class="chat-session-head">
            <div class="chat-session-name">{{ session.title }}</div>
            <div v-if="session.chatId" class="chat-session-actions" @click.stop>
              <button class="session-icon-btn" @click="renameSession(session)">✎</button>
              <button class="session-icon-btn danger" @click="removeSession(session)">✕</button>
            </div>
          </div>
          <div class="chat-session-meta">
            <span>{{ shortId(session.sessionId || session.chatId || session.localId) }}</span>
            <span :class="['badge', session.active ? 'badge-green' : 'badge-blue']">{{ session.active ? 'active' : 'saved' }}</span>
          </div>
        </button>
        <div v-if="sessions.length === 0" class="chat-sidebar-empty">No chat sessions yet.</div>
      </div>
    </aside>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { api } from '../../api/index.js';
import MessageStream from '../diagnosis/MessageStream.vue';

const sessions = ref([]);
const activeSessionId = ref(null);
const draft = ref('');
const loading = ref(false);
const connected = ref(false);
const isRunning = ref(false);

let eventSource = null;
let localSeq = 0;

const activeSession = computed(() => sessions.value.find(s => s.localId === activeSessionId.value) || null);

const renderedEvents = computed(() => activeSession.value?.events || []);
const canStop = computed(() => !!activeSession.value?.chatId && isRunning.value === true);

const chatTimeline = computed(() => {
  const session = activeSession.value;
  if (!session) return [];
  const items = [];
  for (const userMsg of session.userMessages) {
    items.push({
      key: `user:${userMsg.id}`,
      role: 'user',
      content: userMsg.content,
    });
    items.push({
      key: `assistant:${userMsg.id}`,
      role: 'assistant',
      events: session.assistantStreams[userMsg.id] || [],
      isRunning: session.pendingMessageId === userMsg.id && isRunning.value,
    });
  }
  return items;
});

function createSessionShell(title = 'New Chat') {
  const id = `local_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
  return {
    localId: id,
    title,
    chatId: null,
    sessionId: null,
    active: false,
    userMessages: [],
    assistantStreams: {},
    pendingMessageId: null,
    events: [],
  };
}

function hydrateSessionFromHistory(history) {
  const base = createSessionShell(history?.session?.title || 'Saved Chat');
  base.chatId = history?.session?.chatId || null;
  base.sessionId = history?.session?.sessionId || null;
  base.title = history?.session?.title || 'Saved Chat';
  base.active = history?.session?.status === 'active';
  const messages = history?.messages || [];

  let lastUserId = null;
  for (const msg of messages) {
    if (msg.role === 'user' && msg.event_type === 'user_message') {
      const userId = `hist_user_${msg.id}`;
      base.userMessages.push({ id: userId, content: msg.content || '' });
      base.assistantStreams[userId] = [];
      lastUserId = userId;
      continue;
    }

    if (!lastUserId) {
      lastUserId = `hist_bootstrap_${msg.id}`;
      base.userMessages.push({ id: lastUserId, content: '[Conversation restored]' });
      base.assistantStreams[lastUserId] = [];
    }

    const ev = restoreEventFromMessageRow(msg);
    base.events.push(ev);
    base.assistantStreams[lastUserId].push(ev);
  }

  return base;
}

function restoreEventFromMessageRow(row) {
  const seq = ++localSeq;
  const subtype = row.event_subtype || null;
  if (row.event_type === 'message') return { type: 'message', data: { role: 'assistant', content: row.content || '' }, _seq: seq };
  if (row.event_type === 'thinking') return { type: 'thinking', data: { content: row.content || '' }, _seq: seq };
  if (row.event_type === 'tool_use') {
    try {
      const parsed = JSON.parse(row.content || '{}');
      return { type: 'tool_use', data: parsed, _seq: seq };
    } catch {
      return { type: 'tool_use', data: { name: subtype || 'Tool', input: { raw: row.content || '' } }, _seq: seq };
    }
  }
  if (row.event_type === 'tool_result') {
    return { type: 'tool_result', data: { toolUseId: '', summary: row.content || '', isError: subtype === 'error' }, _seq: seq };
  }
  if (row.event_type === 'result') {
    try {
      const parsed = JSON.parse(row.content || '{}');
      return { type: 'stats', data: parsed, _seq: seq };
    } catch {
      return { type: 'stats', data: {}, _seq: seq };
    }
  }
  if (row.event_type === 'error') {
    return { type: 'error', data: { error: row.content || 'Chat error' }, _seq: seq };
  }
  if (row.event_type === 'stream_event' || row.event_type === 'raw') {
    try {
      return { type: 'stream_event', subtype: subtype || 'stream_event', data: JSON.parse(row.content || '{}'), _seq: seq };
    } catch {
      return { type: 'unknown', subtype: subtype || row.event_type, data: row.content || '', _seq: seq };
    }
  }
  if (row.event_type === 'system') {
    try {
      const parsed = JSON.parse(row.content || '{}');
      return { type: 'system', subtype: parsed.subtype || subtype || 'system', data: parsed, _seq: seq };
    } catch {
      return { type: 'system', subtype: subtype || 'system', data: { content: row.content || '' }, _seq: seq };
    }
  }
  return { type: 'unknown', subtype: row.event_type || 'unknown', data: row.content || '', _seq: seq };
}

function createChat() {
  const session = createSessionShell();
  sessions.value.unshift(session);
  activeSessionId.value = session.localId;
  draft.value = '';
  closeStream();
  connected.value = false;
  isRunning.value = false;
}

function selectSession(localId) {
  activeSessionId.value = localId;
  closeStream();
  connected.value = false;
  isRunning.value = false;
}

function shortId(value) {
  return value ? String(value).slice(0, 8) : '--';
}

function ensureActiveSession() {
  if (!activeSession.value) createChat();
  return activeSession.value;
}

function pushSessionEvent(session, userMessageId, ev) {
  session.events.push(ev);
  if (!session.assistantStreams[userMessageId]) session.assistantStreams[userMessageId] = [];
  session.assistantStreams[userMessageId].push(ev);
}

function openChatStream(session, userMessageId, chatId) {
  closeStream();
  connected.value = false;
  isRunning.value = true;
  eventSource = new EventSource(api.chatStreamUrl(chatId));

  const push = (type, data, subtype = null) => {
    const event = { type, data, subtype, _seq: ++localSeq };
    pushSessionEvent(session, userMessageId, event);
  };

  eventSource.addEventListener('chat_init', (e) => {
    try {
      const d = JSON.parse(e.data);
      session.chatId = d.chatId || session.chatId;
      session.sessionId = d.sessionId || session.sessionId;
      session.active = true;
      session.title = session.title === 'New Chat'
        ? (session.userMessages[0]?.content?.slice(0, 28) || 'New Chat')
        : session.title;
    } catch {}
  });

  eventSource.addEventListener('system', (e) => {
    try { push('system', JSON.parse(e.data), JSON.parse(e.data)?.subtype || 'system'); } catch {}
  });
  eventSource.addEventListener('result', (e) => {
    try {
      const d = JSON.parse(e.data);
      push('stats', d);
      push('complete', { status: d?.subtype === 'success' ? 'completed' : 'failed', error: d?.stopReason || '', score: null, verdict: d?.subtype || '' });
    } catch {}
  });
  eventSource.addEventListener('message', (e) => {
    try { push('message', JSON.parse(e.data)); } catch {}
  });
  eventSource.addEventListener('thinking', (e) => {
    try { push('thinking', JSON.parse(e.data)); } catch {}
  });
  eventSource.addEventListener('tool_use', (e) => {
    try { push('tool_use', JSON.parse(e.data)); } catch {}
  });
  eventSource.addEventListener('tool_result', (e) => {
    try { push('tool_result', JSON.parse(e.data)); } catch {}
  });
  eventSource.addEventListener('stream_event', (e) => {
    try {
      const d = JSON.parse(e.data);
      const normalized = normalizeChatStreamEvent(d);
      push(normalized.type, normalized.data, normalized.subtype);
    } catch {}
  });
  eventSource.addEventListener('raw', (e) => {
    try {
      const d = JSON.parse(e.data);
      push('unknown', d, d?.type || 'raw');
    } catch {}
  });
  eventSource.addEventListener('chat_complete', () => {
    connected.value = false;
    isRunning.value = false;
    session.pendingMessageId = null;
    closeStream();
  });
  eventSource.addEventListener('chat_error', (e) => {
    try {
      const d = JSON.parse(e.data);
      push('error', { error: d.error || 'Chat failed' });
    } catch {}
    connected.value = false;
    isRunning.value = false;
    session.pendingMessageId = null;
    closeStream();
  });
  eventSource.onopen = () => {
    connected.value = true;
  };
  eventSource.onerror = () => {
    connected.value = false;
  };
}

async function submitMessage() {
  const text = draft.value.trim();
  if (!text) return;

  const session = ensureActiveSession();
  const userMessageId = `um_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
  session.userMessages.push({ id: userMessageId, content: text });
  session.pendingMessageId = userMessageId;
  if (!session.assistantStreams[userMessageId]) session.assistantStreams[userMessageId] = [];
  draft.value = '';
  loading.value = true;

  try {
    let result;
    if (!session.chatId || !session.sessionId) {
      result = await api.startChat({
        prompt: text,
        permissionMode: 'bypassPermissions',
      });
    } else {
      result = await api.sendChatMessage(session.chatId, {
        message: text,
        sessionId: session.sessionId,
        permissionMode: 'bypassPermissions',
      });
    }

    session.chatId = result.chatId;
    session.sessionId = result.sessionId || session.sessionId;
    session.active = true;
    if (session.title === 'New Chat') session.title = text.slice(0, 28);
    openChatStream(session, userMessageId, result.chatId);
  } catch (err) {
    pushSessionEvent(session, userMessageId, { type: 'error', data: { error: err.message }, _seq: ++localSeq });
    session.pendingMessageId = null;
  } finally {
    loading.value = false;
  }
}

async function stopActiveChat() {
  if (!activeSession.value?.chatId) return;
  try {
    await api.stopChat(activeSession.value.chatId);
  } catch {}
  isRunning.value = false;
  connected.value = false;
  activeSession.value.active = false;
  activeSession.value.pendingMessageId = null;
  closeStream();
}

async function refreshSessions() {
  const remote = await api.listChats().catch(() => []);
  const merged = [];
  for (const item of remote || []) {
    const existing = sessions.value.find(s => s.chatId === item.chatId);
    if (existing) {
      existing.sessionId = item.sessionId || existing.sessionId;
      existing.title = item.title || existing.title;
      existing.active = item.status === 'active';
      merged.push(existing);
      continue;
    }
    try {
      const history = await api.getChatHistory(item.chatId);
      merged.push(hydrateSessionFromHistory(history));
    } catch {
      merged.push({
        ...createSessionShell(item.title || `Chat ${shortId(item.chatId)}`),
        chatId: item.chatId,
        sessionId: item.sessionId || null,
        title: item.title || `Chat ${shortId(item.chatId)}`,
        active: item.status === 'active',
      });
    }
  }
  if (merged.length) {
    sessions.value = [...merged, ...sessions.value.filter(local => !local.chatId)];
    if (!activeSession.value && sessions.value[0]) activeSessionId.value = sessions.value[0].localId;
  }
}

async function renameSession(session) {
  if (!session.chatId) return;
  const title = window.prompt('Rename session', session.title || '');
  if (!title || !title.trim()) return;
  const updated = await api.renameChatSession(session.chatId, title.trim());
  session.title = updated.title || title.trim();
}

async function removeSession(session) {
  const ok = window.confirm(`Delete session "${session.title}"? This will remove its history.`);
  if (!ok) return;

  if (session.chatId) {
    await api.deleteChatSession(session.chatId);
  }

  sessions.value = sessions.value.filter(s => s.localId !== session.localId);

  if (activeSessionId.value === session.localId) {
    if (sessions.value.length > 0) {
      activeSessionId.value = sessions.value[0].localId;
    } else {
      createChat();
    }
  }
}

function closeStream() {
  if (eventSource) {
    eventSource.close();
    eventSource = null;
  }
}

function normalizeChatStreamEvent(payload) {
  const raw = payload?.event || payload;
  if (raw?.type === 'task_progress') {
    return {
      type: 'task_progress',
      subtype: 'task_progress',
      data: {
        taskId: raw.task?.id || raw.task_id || raw.id || '',
        agentName: raw.task?.name || raw.name || 'Sub-agent',
        status: raw.task?.status || raw.status || 'running',
        currentStep: raw.message || raw.current_step || '',
        progress: raw.progress || null,
        events: (raw.events || raw.task?.events || []).slice(0, 50),
      },
    };
  }
  if (raw?.type === 'assistant' || raw?.type === 'message' || raw?.type === 'text') {
    return { type: 'stream_event', subtype: raw.type || 'message', data: raw };
  }
  if (raw?.type === 'tool_use') {
    return { type: 'tool_use', subtype: 'tool_use', data: { name: raw.name, input: raw.input, id: raw.id } };
  }
  if (raw?.type === 'tool_result') {
    return {
      type: 'tool_result',
      subtype: 'tool_result',
      data: {
        toolUseId: raw.tool_use_id || raw.toolUseId || raw.id || '',
        summary: typeof raw.content === 'string' ? raw.content.slice(0, 300) : (raw.summary || ''),
        isError: !!raw.is_error || !!raw.isError,
      },
    };
  }
  if (raw?.type === 'thinking') {
    return { type: 'thinking', subtype: 'thinking', data: { content: raw.thinking || raw.content || '' } };
  }
  if (raw?.type === 'system') {
    return { type: 'system', subtype: raw.subtype || 'system', data: raw };
  }
  return {
    type: 'stream_event',
    subtype: raw?.type || payload?.type || 'stream_event',
    data: raw,
  };
}

onMounted(() => {
  createChat();
  refreshSessions();
});

onBeforeUnmount(() => {
  closeStream();
});
</script>

<style scoped>
.chat-shell {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
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
.chat-scroll {
  flex: 1;
  overflow: auto;
  padding: 28px 28px 10px;
}
.chat-row {
  display: flex;
  gap: 14px;
  margin-bottom: 22px;
}
.chat-row-user {
  justify-content: flex-end;
}
.chat-bubble {
  max-width: min(860px, 78%);
  padding: 14px 16px;
  border-radius: 20px;
  line-height: 1.65;
  white-space: pre-wrap;
}
.chat-bubble-user {
  background: linear-gradient(135deg, var(--accent2), var(--accent));
  color: #fff;
  border-bottom-right-radius: 6px;
  box-shadow: 0 10px 24px rgba(31,111,235,.22);
}
.chat-avatar {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  background: linear-gradient(135deg, #7c3aed, #3b82f6);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  color: #fff;
  flex-shrink: 0;
  margin-top: 4px;
}
.chat-assistant-panel {
  flex: 1;
  min-width: 0;
  background: rgba(255,255,255,.02);
  border: 1px solid rgba(255,255,255,.04);
  border-radius: 18px;
  padding: 14px 14px 0;
  backdrop-filter: blur(4px);
}
.chat-assistant-panel :deep(.message-stream) {
  background: transparent;
  border: none;
  padding: 0;
  min-height: auto;
}
.chat-composer {
  border-top: 1px solid var(--border);
  padding: 18px 20px 20px;
  background: linear-gradient(180deg, rgba(13,17,23,0) 0%, rgba(22,27,34,0.95) 14%);
}
.chat-input {
  min-height: 108px;
  border-radius: 18px;
  padding: 16px 18px;
  font-size: 15px;
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
.chat-sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 18px 14px;
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
  font-size: 11px;
  color: var(--text2);
}
.chat-sidebar-empty,
.chat-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  color: var(--text2);
  height: 100%;
}
.chat-empty-icon {
  font-size: 36px;
  margin-bottom: 12px;
}
@media (max-width: 1100px) {
  .chat-shell {
    grid-template-columns: 1fr;
    height: auto;
  }
  .chat-sidebar {
    min-height: 260px;
  }
}
</style>
