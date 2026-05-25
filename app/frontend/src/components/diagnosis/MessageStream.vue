<template>
  <div class="message-stream" ref="streamEl">
    <!-- Connecting overlay -->
    <div v-if="!connected && isRunning" class="ms-connecting">
      <div class="spinner-sm"></div>
      <span>Connecting to engine...</span>
    </div>

    <template v-for="(ev, i) in visibleEvents" :key="ev._seq ?? i">

      <!-- THINKING -->
      <div v-if="ev.type === 'thinking'" class="ms-item ms-thinking">
        <div class="ms-rail"><div class="ms-dot dot-purple"></div></div>
        <div class="ms-body">
          <div class="ms-card card-thinking" @click="toggleThinking(ev)">
            <div class="ms-card-header">
              <span class="ms-card-icon">🧠</span>
              <span class="ms-card-title">Agent Reasoning</span>
              <span class="ms-card-toggle" :class="{ open: expandedThinking.has(ev._seq) }">▶</span>
            </div>
            <div v-if="expandedThinking.has(ev._seq)" class="ms-thinking-content">
              {{ ev.data.content }}
            </div>
          </div>
        </div>
      </div>

      <!-- ASSISTANT MESSAGE -->
      <div v-else-if="ev.type === 'message'" class="ms-item ms-msg">
        <div class="ms-rail"><div class="ms-dot dot-blue"></div></div>
        <div class="ms-body">
          <div class="ms-card card-msg">
            <div class="ms-card-header">
              <span class="ms-card-icon">🤖</span>
              <span class="ms-card-title">Analysis</span>
            </div>
            <div class="msg-content" v-html="renderMd(ev.data.content)"></div>
          </div>
        </div>
      </div>

      <!-- TOOL USE -->
      <div v-else-if="ev.type === 'tool_use'" class="ms-item ms-tool">
        <div class="ms-rail"><div class="ms-dot" :class="toolDotClass(ev.data.name)"></div></div>
        <div class="ms-body">
          <div class="ms-card card-tool" :class="'tool-' + toolCategory(ev.data.name)">
            <div class="ms-card-header">
              <span class="ms-tool-badge">{{ ev.data.name }}</span>
              <span class="ms-tool-id">{{ ev.data.id?.slice(0, 8) }}</span>
            </div>
            <div class="ms-tool-input">
              <template v-if="ev.data.name === 'Bash'">
                <span class="tool-label">$</span>
                <code>{{ ev.data.input?.command || '' }}</code>
              </template>
              <template v-else-if="ev.data.name === 'Read'">
                <span class="tool-label">file:</span>
                <code>{{ ev.data.input?.file_path || '' }}</code>
              </template>
              <template v-else-if="ev.data.name === 'Write'">
                <span class="tool-label">→</span>
                <code>{{ ev.data.input?.file_path || '' }}</code>
              </template>
              <template v-else-if="ev.data.name === 'Edit'">
                <span class="tool-label">✏</span>
                <code>{{ ev.data.input?.file_path || '' }}</code>
              </template>
              <template v-else-if="ev.data.name === 'Glob'">
                <span class="tool-label">🔍</span>
                <code>{{ ev.data.input?.pattern || '' }}</code>
              </template>
              <template v-else-if="ev.data.name === 'WebSearch'">
                <span class="tool-label">🌐</span>
                <code>{{ ev.data.input?.query || '' }}</code>
              </template>
              <template v-else-if="ev.data.name === 'Skill'">
                <span class="tool-label">⚡</span>
                <code>{{ ev.data.input?.skill || ev.data.input?.args || '' }}</code>
              </template>
              <template v-else-if="ev.data.name === 'AskUserQuestion'">
                <span class="tool-label">❓</span>
                <code>Asking user {{ ev.data.input?.questions?.length || 0 }} question(s)</code>
              </template>
              <template v-else>
                <code>{{ formatToolInput(ev.data.input) }}</code>
              </template>
            </div>
          </div>
        </div>
      </div>

      <!-- TOOL RESULT -->
      <div v-else-if="ev.type === 'tool_result'" class="ms-item ms-result">
        <div class="ms-rail"><div class="ms-dot" :class="ev.data.isError ? 'dot-red' : 'dot-green'"></div></div>
        <div class="ms-body">
          <div :class="['ms-result-card', ev.data.isError ? 'result-err' : 'result-ok']">
            <span class="result-icon">{{ ev.data.isError ? '✗' : '✓' }}</span>
            <span class="result-text" v-if="ev.data.summary">{{ ev.data.summary }}</span>
          </div>
        </div>
      </div>

      <!-- SYSTEM -->
      <div v-else-if="ev.type === 'system'" class="ms-item ms-sys">
        <div class="ms-rail"><div class="ms-dot dot-gray"></div></div>
        <div class="ms-body">
          <div class="ms-sys-card">
            <template v-if="ev.subtype === 'init'">
              Engine initialized · Model: <strong>{{ ev.data?.model }}</strong> · Tools: <strong>{{ ev.data?.tools?.length }}</strong>
            </template>
            <template v-else-if="ev.subtype === 'artifacts'">
              Artifacts: <strong>{{ (ev.data?.artifacts || []).join(', ') }}</strong>
              <span v-if="ev.data?.score != null"> · Score: <strong>{{ ev.data.score }}</strong></span>
            </template>
            <template v-else>{{ ev.subtype || 'System' }}</template>
          </div>
        </div>
      </div>

      <!-- STATS -->
      <div v-else-if="ev.type === 'stats'" class="ms-item ms-stats">
        <div class="ms-rail"><div class="ms-dot dot-yellow"></div></div>
        <div class="ms-body">
          <div class="ms-stats-card">
            <div class="stat-item"><span class="stat-val">{{ ev.data.numTurns }}</span><span class="stat-lbl">Turns</span></div>
            <div class="stat-item"><span class="stat-val">{{ formatDuration(ev.data.durationMs) }}</span><span class="stat-lbl">Duration</span></div>
            <div class="stat-item"><span class="stat-val">${{ (ev.data.totalCost || 0).toFixed(4) }}</span><span class="stat-lbl">Cost</span></div>
            <div class="stat-item" v-if="ev.data.stopReason"><span class="stat-val">{{ ev.data.stopReason }}</span><span class="stat-lbl">Reason</span></div>
          </div>
        </div>
      </div>

      <!-- HITL -->
      <div v-else-if="ev.type === 'hitl_request'" class="ms-item ms-hitl">
        <div class="ms-rail"><div class="ms-dot dot-red pulse"></div></div>
        <div class="ms-body">
          <div class="ms-card card-hitl">
            <div class="hitl-warn">⚠ Dangerous command: {{ ev.data.riskDesc }}</div>
            <code class="hitl-cmd">{{ ev.data.command }}</code>
          </div>
        </div>
      </div>

    </template>

    <!-- Live typing indicator -->
    <div v-if="isRunning && connected" class="ms-item ms-typing">
      <div class="ms-rail"><div class="ms-dot dot-blue pulse"></div></div>
      <div class="ms-body">
        <div class="typing-indicator">
          <span></span><span></span><span></span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue';
import { renderMarkdown } from '../../utils/markdown.js';

const props = defineProps({
  events: { type: Array, default: () => [] },
  isRunning: { type: Boolean, default: false },
  connected: { type: Boolean, default: false },
});

const expandedThinking = ref(new Set());
const streamEl = ref(null);
const MAX_EVENTS = 500;

const visibleEvents = computed(() => {
  if (props.events.length <= MAX_EVENTS) return props.events;
  return props.events.slice(-MAX_EVENTS);
});

function toggleThinking(ev) {
  const key = ev._seq;
  const next = new Set(expandedThinking.value);
  if (next.has(key)) next.delete(key); else next.add(key);
  expandedThinking.value = next;
}

function toolCategory(name) {
  if (['Read', 'Glob'].includes(name)) return 'read';
  if (['Write', 'Edit', 'NotebookEdit'].includes(name)) return 'write';
  if (name === 'Bash') return 'bash';
  if (['WebSearch', 'WebFetch'].includes(name)) return 'web';
  if (name === 'Skill') return 'skill';
  return 'default';
}

function toolDotClass(name) {
  const map = {
    Read: 'dot-blue', Glob: 'dot-blue', Bash: 'dot-yellow', Write: 'dot-green',
    Edit: 'dot-green', Skill: 'dot-purple', WebSearch: 'dot-cyan', WebFetch: 'dot-cyan',
    AskUserQuestion: 'dot-purple',
  };
  return map[name] || 'dot-blue';
}

function formatToolInput(input) {
  if (!input) return '';
  if (typeof input === 'string') return input.slice(0, 300);
  return JSON.stringify(input, null, 2).slice(0, 300);
}

function formatDuration(ms) {
  if (!ms) return '0s';
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`;
}

function renderMd(text) {
  return renderMarkdown(text);
}

// Auto-scroll when new events arrive
watch(() => props.events.length, () => {
  nextTick(() => {
    if (streamEl.value) {
      streamEl.value.scrollTo({ top: streamEl.value.scrollHeight, behavior: 'smooth' });
    }
  });
});
</script>

<style scoped>
.message-stream {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 20px 16px;
  flex: 1; overflow-y: auto; scroll-behavior: smooth;
  min-height: 200px;
}

.ms-connecting {
  display: flex; align-items: center; gap: 10px;
  justify-content: center; padding: 32px; color: var(--text2); font-size: 13px;
}

/* Timeline Item */
.ms-item {
  display: flex; gap: 12px; padding: 4px 0;
  animation: fadeSlideIn .25s ease;
}
@keyframes fadeSlideIn {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Rail */
.ms-rail {
  display: flex; flex-direction: column; align-items: center;
  width: 20px; flex-shrink: 0; position: relative;
}
.ms-rail::before {
  content: ''; position: absolute; top: 0; bottom: 0; left: 50%;
  width: 1px; background: var(--border); transform: translateX(-50%);
}
.ms-item:first-child .ms-rail::before { top: 50%; }
.ms-item:last-child .ms-rail::before { bottom: 50%; }

.ms-dot {
  width: 8px; height: 8px; border-radius: 50%; z-index: 1;
  position: relative; flex-shrink: 0; margin: 6px 0;
}
.dot-blue { background: var(--accent); }
.dot-green { background: var(--green); }
.dot-red { background: var(--red); }
.dot-yellow { background: var(--yellow); }
.dot-purple { background: var(--purple); }
.dot-cyan { background: #22d3ee; }
.dot-gray { background: var(--text2); }
.ms-dot.pulse { animation: dotPulse 1.5s infinite; }
@keyframes dotPulse {
  0%, 100% { box-shadow: 0 0 0 0 currentColor; }
  50% { box-shadow: 0 0 0 4px transparent; }
}
.dot-blue.pulse { color: var(--accent); }
.dot-red.pulse { color: var(--red); }

/* Body */
.ms-body { flex: 1; min-width: 0; padding-right: 4px; }

/* Event Cards */
.ms-card { border-radius: 8px; overflow: hidden; }

/* Thinking */
.card-thinking {
  background: rgba(188,140,255,.05); border: 1px solid rgba(188,140,255,.15);
  border-radius: 8px; cursor: pointer;
}
.card-thinking:hover { background: rgba(188,140,255,.08); }
.ms-card-header {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 12px; font-size: 12px;
}
.ms-card-icon { font-size: 14px; }
.ms-card-title { font-weight: 600; color: var(--text2); }
.ms-card-toggle { margin-left: auto; font-size: 10px; color: var(--text2); transition: transform .2s; }
.ms-card-toggle.open { transform: rotate(90deg); }
.ms-thinking-content {
  padding: 8px 16px 12px; font-size: 12px; color: var(--text2);
  line-height: 1.6; font-family: 'SF Mono', 'Fira Code', monospace;
  border-top: 1px solid rgba(188,140,255,.1);
  white-space: pre-wrap; max-height: 300px; overflow-y: auto;
}

/* Message */
.card-msg { background: transparent; border: none; }
.msg-content { font-size: 13px; line-height: 1.8; color: var(--text); }
.msg-content :deep(p) { margin: 4px 0; }
.msg-content :deep(code) { background: var(--surface2); padding: 2px 6px; border-radius: 3px; font-size: 12px; color: var(--accent); }
.msg-content :deep(pre) { background: var(--surface2); padding: 12px; border-radius: 6px; overflow-x: auto; font-size: 12px; margin: 8px 0; }
.msg-content :deep(pre code) { background: none; padding: 0; color: var(--text); }
.msg-content :deep(ul), .msg-content :deep(ol) { padding-left: 20px; margin: 4px 0; }
.msg-content :deep(strong) { font-weight: 700; color: #fff; }
.msg-content :deep(h1), .msg-content :deep(h2), .msg-content :deep(h3) { margin: 12px 0 4px; font-size: 15px; color: var(--accent); }
.msg-content :deep(blockquote) { border-left: 3px solid var(--accent); padding-left: 12px; color: var(--text2); margin: 8px 0; }
.msg-content :deep(table) { border-collapse: collapse; margin: 8px 0; width: 100%; }
.msg-content :deep(th), .msg-content :deep(td) { border: 1px solid var(--border); padding: 6px 10px; font-size: 12px; }
.msg-content :deep(th) { background: var(--surface2); font-weight: 600; }

/* Tool Use */
.card-tool { border-radius: 8px; padding: 10px 14px; }
.tool-read { background: rgba(88,166,255,.05); border: 1px solid rgba(88,166,255,.12); }
.tool-write { background: rgba(63,185,80,.05); border: 1px solid rgba(63,185,80,.12); }
.tool-bash { background: rgba(210,153,34,.05); border: 1px solid rgba(210,153,34,.12); }
.tool-web { background: rgba(34,211,238,.05); border: 1px solid rgba(34,211,238,.12); }
.tool-skill { background: rgba(188,140,255,.05); border: 1px solid rgba(188,140,255,.12); }
.tool-default { background: var(--surface2); border: 1px solid var(--border); }

.ms-tool-badge {
  display: inline-block; padding: 2px 10px; border-radius: 4px;
  font-size: 11px; font-weight: 700; background: rgba(255,255,255,.06); color: var(--text);
  letter-spacing: .3px;
}
.ms-tool-id { font-size: 10px; color: var(--text2); font-family: monospace; margin-left: 8px; }
.ms-tool-input {
  margin-top: 8px; font-size: 12px; line-height: 1.5;
  display: flex; align-items: flex-start; gap: 6px; flex-wrap: wrap;
}
.ms-tool-input .tool-label { color: var(--text2); font-weight: 600; font-size: 11px; flex-shrink: 0; }
.ms-tool-input code {
  font-family: 'SF Mono', 'Fira Code', monospace; font-size: 11px;
  color: var(--accent); background: rgba(88,166,255,.06);
  padding: 2px 8px; border-radius: 4px; word-break: break-all;
}
.tool-bash .ms-tool-input code { color: var(--yellow); background: rgba(210,153,34,.06); }
.tool-write .ms-tool-input code { color: var(--green); background: rgba(63,185,80,.06); }

/* Tool Result */
.ms-result-card {
  display: flex; align-items: flex-start; gap: 8px;
  padding: 6px 12px; border-radius: 6px; font-size: 12px;
}
.result-ok { background: rgba(63,185,80,.05); color: var(--green); }
.result-err { background: rgba(248,81,73,.05); color: var(--red); }
.result-icon { font-weight: 700; flex-shrink: 0; }
.result-text { color: var(--text2); font-family: 'SF Mono', monospace; font-size: 11px;
  max-height: 80px; overflow-y: auto; line-height: 1.5; word-break: break-all; }

/* System */
.ms-sys-card {
  font-size: 12px; color: var(--text2); padding: 6px 12px;
  background: rgba(139,148,158,.04); border-radius: 6px;
}
.ms-sys-card strong { color: var(--text); }

/* Stats */
.ms-stats-card {
  display: flex; gap: 20px; flex-wrap: wrap;
  padding: 10px 16px; background: rgba(210,153,34,.04);
  border: 1px solid rgba(210,153,34,.1); border-radius: 8px;
}
.stat-item { display: flex; flex-direction: column; gap: 2px; }
.stat-val { font-size: 14px; font-weight: 700; color: var(--yellow); font-variant-numeric: tabular-nums; }
.stat-lbl { font-size: 10px; color: var(--text2); text-transform: uppercase; }

/* HITL */
.card-hitl {
  padding: 10px 14px; background: rgba(248,81,73,.05);
  border: 1px solid rgba(248,81,73,.15); border-radius: 8px;
}
.hitl-warn { font-size: 12px; color: var(--red); font-weight: 600; margin-bottom: 6px; }
.hitl-cmd { font-size: 11px; color: var(--text2); font-family: monospace; word-break: break-all; }

/* Typing */
.typing-indicator { display: flex; gap: 4px; padding: 8px 0; }
.typing-indicator span {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--accent); opacity: .4;
  animation: typingBounce 1.2s infinite;
}
.typing-indicator span:nth-child(2) { animation-delay: .2s; }
.typing-indicator span:nth-child(3) { animation-delay: .4s; }
@keyframes typingBounce {
  0%, 60%, 100% { transform: translateY(0); opacity: .4; }
  30% { transform: translateY(-4px); opacity: 1; }
}

.spinner-sm {
  display: inline-block; width: 14px; height: 14px;
  border: 2px solid var(--border); border-top-color: var(--accent);
  border-radius: 50%; animation: spin .8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
