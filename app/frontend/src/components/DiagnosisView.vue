<template>
  <div class="diagnosis-engine">
    <!-- Data Source Card -->
    <div class="ds-card" v-if="analysisTarget && !started">
      <div class="ds-card-header">
        <div class="ds-icon" :class="'ds-icon-' + (analysisTarget.mode || 'file')">
          {{ analysisTarget.mode === 'folder' ? '📁' : analysisTarget.mode === 'multi' ? '📊' : '📄' }}
        </div>
        <div class="ds-info">
          <div class="ds-title">
            <template v-if="analysisTarget.mode === 'file'">{{ analysisTarget.file.name }}</template>
            <template v-else-if="analysisTarget.mode === 'folder'">{{ analysisTarget.name }}</template>
            <template v-else>{{ analysisTarget.files.length }} selected files</template>
          </div>
          <div class="ds-sub" v-if="analysisTarget.mode === 'file'">
            {{ formatSize(analysisTarget.file.size) }} · {{ analysisTarget.file.path }}
          </div>
          <div class="ds-sub" v-else-if="analysisTarget.mode === 'folder'">
            {{ analysisTarget.csvCount || 0 }} data files
          </div>
        </div>
      </div>
    </div>

    <!-- Control Panel -->
    <div class="ctrl-bar" v-if="analysisTarget && !started">
      <div class="ctrl-form">
        <input v-model="sceneName" placeholder="Scene name (optional)" class="ctrl-input" />
        <textarea v-model="userQuestion" placeholder="What do you want to diagnose?" rows="3" class="ctrl-textarea"></textarea>
        <div class="ctrl-row">
          <div class="turns-control">
            <label class="turns-label">Max Turns</label>
            <select v-model.number="maxTurns" class="ctrl-input ctrl-select">
              <option :value="0">Unlimited</option>
              <option :value="50">50</option>
              <option :value="100">100</option>
              <option :value="200">200</option>
              <option :value="300">300</option>
              <option :value="500">500</option>
            </select>
          </div>
          <div class="turns-control">
            <label class="turns-label">Report Language</label>
            <select v-model="reportLanguage" class="ctrl-input ctrl-select">
              <option value="zh">中文</option>
              <option value="en">English</option>
            </select>
          </div>
          <button class="ctrl-btn ctrl-btn-go" @click="start" :disabled="!analysisTarget">
            Start Analysis
          </button>
        </div>
      </div>
    </div>

    <!-- ============ LIVE RUN VIEW ============ -->
    <template v-if="started">
      <!-- Status Bar -->
      <div class="status-bar">
        <div class="status-left">
          <div class="status-dot" :class="statusDotClass"></div>
          <span class="status-label">{{ statusLabel }}</span>
          <span class="status-run-id">#{{ runId }}</span>
        </div>
        <div class="status-metrics">
          <div class="smetric"><span class="sm-val">{{ turnCount }}</span><span class="sm-lbl">Turns</span></div>
          <div class="smetric"><span class="sm-val">{{ toolCount }}</span><span class="sm-lbl">Tools</span></div>
          <div class="smetric"><span class="sm-val">{{ msgCount }}</span><span class="sm-lbl">Msgs</span></div>
          <div class="smetric sm-time"><span class="sm-val">{{ elapsed }}</span></div>
        </div>
        <button v-if="isRunning" class="stop-btn" @click="stop">Stop</button>
      </div>

      <!-- Phase Indicator -->
      <div class="phase-bar" v-if="currentPhase">
        <div class="phase-icon">{{ phaseIcon }}</div>
        <span class="phase-text">{{ currentPhase }}</span>
        <div class="phase-progress-track">
          <div class="phase-progress-fill" :style="{ width: progressPct + '%' }"></div>
        </div>
      </div>

      <!-- ============ TIMELINE ============ -->
      <div class="timeline" ref="streamEl">
        <!-- Connecting overlay -->
        <div v-if="!connected && isRunning" class="tl-connecting">
          <div class="spinner-sm"></div>
          <span>Connecting to engine...</span>
        </div>

        <template v-for="(ev, i) in visibleEvents" :key="ev._seq ?? i">

          <!-- THINKING -->
          <div v-if="ev.type === 'thinking'" class="tl-item tl-thinking">
            <div class="tl-rail"><div class="tl-dot dot-purple"></div></div>
            <div class="tl-body">
              <div class="tl-card card-thinking" @click="toggleThinking(ev)">
                <div class="tl-card-header">
                  <span class="tl-card-icon">💭</span>
                  <span class="tl-card-title">Agent Reasoning</span>
                  <span class="tl-card-toggle" :class="{ open: expandedThinking.has(ev._seq) }">▶</span>
                </div>
                <div v-if="expandedThinking.has(ev._seq)" class="tl-thinking-content">
                  {{ ev.data.content }}
                </div>
              </div>
            </div>
          </div>

          <!-- ASSISTANT MESSAGE -->
          <div v-else-if="ev.type === 'message'" class="tl-item tl-msg">
            <div class="tl-rail"><div class="tl-dot dot-blue"></div></div>
            <div class="tl-body">
              <div class="tl-card card-msg">
                <div class="tl-card-header">
                  <span class="tl-card-icon">🤖</span>
                  <span class="tl-card-title">Analysis</span>
                </div>
                <div class="msg-content" v-html="renderMd(ev.data.content)"></div>
              </div>
            </div>
          </div>

          <!-- TOOL USE -->
          <div v-else-if="ev.type === 'tool_use'" class="tl-item tl-tool">
            <div class="tl-rail"><div class="tl-dot" :class="toolDotClass(ev.data.name)"></div></div>
            <div class="tl-body">
              <div class="tl-card card-tool" :class="'tool-' + toolCategory(ev.data.name)">
                <div class="tl-card-header">
                  <span class="tl-tool-badge">{{ ev.data.name }}</span>
                  <span class="tl-tool-id">{{ ev.data.id?.slice(0, 8) }}</span>
                </div>
                <div class="tl-tool-input">
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
                  <template v-else>
                    <code>{{ formatToolInput(ev.data.input) }}</code>
                  </template>
                </div>
              </div>
            </div>
          </div>

          <!-- TOOL RESULT -->
          <div v-else-if="ev.type === 'tool_result'" class="tl-item tl-result">
            <div class="tl-rail"><div class="tl-dot" :class="ev.data.isError ? 'dot-red' : 'dot-green'"></div></div>
            <div class="tl-body">
              <div :class="['tl-result-card', ev.data.isError ? 'result-err' : 'result-ok']">
                <span class="result-icon">{{ ev.data.isError ? '✗' : '✓' }}</span>
                <span class="result-text" v-if="ev.data.summary">{{ ev.data.summary }}</span>
              </div>
            </div>
          </div>

          <!-- SYSTEM -->
          <div v-else-if="ev.type === 'system'" class="tl-item tl-sys">
            <div class="tl-rail"><div class="tl-dot dot-gray"></div></div>
            <div class="tl-body">
              <div class="tl-sys-card">
                <template v-if="ev.subtype === 'init'">
                  Engine initialized · Model: <strong>{{ ev.data?.model }}</strong> · Tools: <strong>{{ ev.data?.tools?.length }}</strong>
                </template>
                <template v-else-if="ev.subtype === 'connected'">
                  WebSocket connected · {{ ev.data?.buffered || 0 }} buffered events replayed
                </template>
                <template v-else>{{ ev.subtype || 'System' }}</template>
              </div>
            </div>
          </div>

          <!-- STATS -->
          <div v-else-if="ev.type === 'stats'" class="tl-item tl-stats">
            <div class="tl-rail"><div class="tl-dot dot-yellow"></div></div>
            <div class="tl-body">
              <div class="tl-stats-card">
                <div class="stat-item"><span class="stat-val">{{ ev.data.numTurns }}</span><span class="stat-lbl">Turns</span></div>
                <div class="stat-item"><span class="stat-val">{{ formatDuration(ev.data.durationMs) }}</span><span class="stat-lbl">Duration</span></div>
                <div class="stat-item"><span class="stat-val">${{ (ev.data.totalCost || 0).toFixed(4) }}</span><span class="stat-lbl">Cost</span></div>
                <div class="stat-item" v-if="ev.data.stopReason"><span class="stat-val">{{ ev.data.stopReason }}</span><span class="stat-lbl">Reason</span></div>
              </div>
            </div>
          </div>

          <!-- HITL -->
          <div v-else-if="ev.type === 'hitl_request'" class="tl-item tl-hitl">
            <div class="tl-rail"><div class="tl-dot dot-red pulse"></div></div>
            <div class="tl-body">
              <div class="tl-card card-hitl">
                <div class="hitl-warn">⚠ Dangerous command: {{ ev.data.riskDesc }}</div>
                <code class="hitl-cmd">{{ ev.data.command }}</code>
              </div>
            </div>
          </div>

        </template>

        <!-- Live typing indicator -->
        <div v-if="isRunning && connected" class="tl-item tl-typing">
          <div class="tl-rail"><div class="tl-dot dot-blue pulse"></div></div>
          <div class="tl-body">
            <div class="typing-indicator">
              <span></span><span></span><span></span>
            </div>
          </div>
        </div>
      </div>

      <!-- Completion Banner -->
      <div v-if="completed || failed" :class="['result-banner', verdictClass]">
        <div class="rb-icon">{{ completed ? '✓' : '✗' }}</div>
        <div class="rb-info">
          <div class="rb-title">{{ completed ? 'Diagnosis Complete' : 'Diagnosis Failed' }}</div>
          <div class="rb-meta">
            <span v-if="score != null" class="rb-score">Score: {{ score }}/100</span>
            <span v-if="verdict" class="rb-verdict">{{ verdict }}</span>
            <span v-if="errorMsg" class="rb-error">{{ errorMsg }}</span>
          </div>
          <div class="rb-actions">
            <button v-if="reportPath" class="rb-btn rb-btn-primary" @click="openReport">View Full Report</button>
            <button v-if="failed && runId" class="rb-btn rb-btn-retry" @click="retryDiagnosis">Retry Analysis</button>
          </div>
        </div>
      </div>
    </template>

    <!-- HITL Approval Dialog -->
    <Teleport to="body">
      <div v-if="hitlPending" class="hitl-overlay">
        <div class="hitl-dialog">
          <div class="hitl-header">
            <span class="hitl-icon">⚠️</span>
            <span class="hitl-title">Dangerous Command Detected</span>
          </div>
          <div class="hitl-risk" :class="'risk-' + (hitlRisk || 'high')">{{ hitlRisk || 'HIGH' }} RISK</div>
          <div class="hitl-desc">{{ hitlDesc }}</div>
          <pre class="hitl-command">{{ hitlCommand }}</pre>
          <div class="hitl-actions">
            <button class="hitl-btn hitl-deny" @click="respondHITL(false)">Deny & Stop</button>
            <button class="hitl-btn hitl-approve" @click="respondHITL(true)">Approve & Continue</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onUnmounted } from 'vue';
import { api, wsUrl } from '../api.js';
import { marked } from 'marked';
import DOMPurify from 'dompurify';

const props = defineProps({
  analysisTarget: { type: Object, default: null },
  autoRunId: { type: String, default: null },
});
const emit = defineEmits(['started', 'view-report']);

const sceneName = ref('');
const userQuestion = ref('');
const maxTurns = ref(0);
const reportLanguage = ref('zh');
const started = ref(false);
const isRunning = ref(false);
const completed = ref(false);
const failed = ref(false);
const runId = ref(null);
const connected = ref(false);
const events = ref([]);
const score = ref(null);
const verdict = ref(null);
const reportPath = ref(null);
const turnCount = ref(0);
const toolCount = ref(0);
const msgCount = ref(0);
const startTime = ref(null);
const elapsed = ref('0:00');
const currentPhase = ref('');
const expandedThinking = ref(new Set());
const streamEl = ref(null);
const progressPct = ref(0);
const errorMsg = ref('');

const hitlPending = ref(false);
const hitlId = ref(null);
const hitlCommand = ref('');
const hitlRisk = ref('');
const hitlDesc = ref('');

let ws = null;
let elapsedTimer = null;

// Computed
const statusDotClass = computed(() => {
  if (completed.value) return 'dot-green';
  if (failed.value) return 'dot-red';
  if (isRunning.value) return 'dot-blue pulse';
  return 'dot-gray';
});

const statusLabel = computed(() => {
  if (completed.value) return 'Complete';
  if (failed.value) return 'Failed';
  if (!connected.value) return 'Connecting...';
  if (isRunning.value) return 'Analyzing';
  return 'Ready';
});

const phaseIcon = computed(() => {
  const p = currentPhase.value;
  if (p.includes('Reading') || p.includes('Data')) return '📂';
  if (p.includes('Executing') || p.includes('Analysis')) return '⚙️';
  if (p.includes('Generating') || p.includes('Output')) return '📝';
  if (p.includes('Planning')) return '📋';
  if (p.includes('Diagnostic') || p.includes('Skill')) return '🔬';
  if (p.includes('Exploring')) return '🔍';
  if (p.includes('Consult') || p.includes('Fetch')) return '🌐';
  if (p.includes('Visualization')) return '📊';
  return '⚙️';
});

const verdictClass = computed(() => {
  if (failed.value) return 'banner-fail';
  if (verdict.value === 'PASS' || verdict.value === 'ENDORSED') return 'banner-pass';
  if (verdict.value === 'CONDITIONAL' || verdict.value === 'NEEDS_REPAIR') return 'banner-warn';
  return 'banner-pass';
});

const MAX_EVENTS = 500;
const visibleEvents = computed(() => {
  if (events.value.length <= MAX_EVENTS) return events.value;
  return events.value.slice(-MAX_EVENTS);
});

// WebSocket
function connectWS(rid) {
  if (ws) {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'subscribe', runId: rid }));
      return;
    }
    ws.close();
  }

  ws = new WebSocket(wsUrl());

  ws.onopen = () => {
    connected.value = true;
    ws.send(JSON.stringify({ type: 'subscribe', runId: rid }));
  };

  ws.onmessage = (raw) => {
    try {
      const event = JSON.parse(raw.data);
      handleEvent(event);
    } catch {}
  };

  ws.onclose = () => {
    connected.value = false;
    if (isRunning.value) {
      setTimeout(() => {
        if (isRunning.value && runId.value) connectWS(runId.value);
      }, 2000);
    }
  };

  ws.onerror = () => { connected.value = false; };
}

function handleEvent(event) {
  switch (event.type) {
    case 'connected':
      if (event.data.status === 'running') {
        isRunning.value = true;
        started.value = true;
        if (!startTime.value) { startTime.value = Date.now(); startElapsed(); }
      }
      events.value.push({ type: 'system', subtype: 'connected', data: event.data, _seq: Date.now() });
      break;

    case 'status':
      if (event.data.status === 'running') {
        isRunning.value = true;
        started.value = true;
        if (!startTime.value) { startTime.value = Date.now(); startElapsed(); }
      }
      break;

    case 'message':
      msgCount.value++;
      events.value.push(event);
      tickProgress(2);
      break;

    case 'tool_use':
      toolCount.value++;
      events.value.push(event);
      tickProgress(3);
      detectPhase(event.data.name);
      break;

    case 'tool_result':
      events.value.push(event);
      break;

    case 'thinking':
      events.value.push(event);
      break;

    case 'system':
      events.value.push(event);
      break;

    case 'stats':
      turnCount.value = event.data.numTurns || 0;
      events.value.push(event);
      if (maxTurns.value > 0) {
        progressPct.value = Math.min(95, (turnCount.value / maxTurns.value) * 90);
      } else {
        progressPct.value = Math.min(95, Math.max(progressPct.value, turnCount.value * 0.3));
      }
      break;

    case 'complete':
      completed.value = true;
      isRunning.value = false;
      progressPct.value = 100;
      score.value = event.data.score;
      verdict.value = event.data.verdict;
      reportPath.value = event.data.reportPath;
      errorMsg.value = '';
      hitlPending.value = false;
      emit('started', runId.value);
      stopElapsed();
      break;

    case 'hitl_request':
      hitlId.value = event.data.hitlId;
      hitlCommand.value = event.data.command;
      hitlRisk.value = event.data.riskLevel;
      hitlDesc.value = event.data.riskDesc;
      hitlPending.value = true;
      events.value.push({ type: 'hitl_request', data: event.data, _seq: Date.now() });
      break;

    case 'hitl_result':
      hitlPending.value = false;
      break;

    case 'error':
      failed.value = true;
      isRunning.value = false;
      errorMsg.value = event.data.error || 'Unknown error';
      stopElapsed();
      break;

    case 'stream_end':
      connected.value = false;
      break;
    case 'welcome': case 'pong': break;
  }

  nextTick(() => {
    if (streamEl.value) {
      streamEl.value.scrollTo({ top: streamEl.value.scrollHeight, behavior: 'smooth' });
    }
  });
}

function tickProgress(amount) {
  if (progressPct.value < 90) {
    progressPct.value = Math.min(90, progressPct.value + amount);
  }
}

function detectPhase(toolName) {
  const phases = {
    Read: 'Reading Data Files', Bash: 'Executing Analysis', Write: 'Generating Output',
    Edit: 'Refining Report', TodoWrite: 'Planning Steps', Task: 'Creating Tasks',
    Skill: 'Invoking Diagnostic Pipeline', Glob: 'Exploring Directory',
    WebSearch: 'Searching References', WebFetch: 'Fetching Documentation',
    NotebookEdit: 'Creating Visualizations',
  };
  currentPhase.value = phases[toolName] || `Executing: ${toolName}`;
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
  const map = { Read: 'dot-blue', Glob: 'dot-blue', Bash: 'dot-yellow', Write: 'dot-green',
    Edit: 'dot-green', Skill: 'dot-purple', WebSearch: 'dot-cyan', WebFetch: 'dot-cyan' };
  return map[name] || 'dot-blue';
}

// Actions
async function start() {
  if (!props.analysisTarget) return;

  started.value = true;
  isRunning.value = true;
  completed.value = false;
  failed.value = false;
  events.value = [];
  turnCount.value = 0;
  toolCount.value = 0;
  msgCount.value = 0;
  progressPct.value = 0;
  startTime.value = Date.now();
  currentPhase.value = 'Initializing...';
  score.value = null;
  verdict.value = null;
  reportPath.value = null;
  errorMsg.value = '';
  hitlPending.value = false;

  const target = props.analysisTarget;
  const payload = { userQuestion: userQuestion.value, sceneName: sceneName.value || undefined, reportLanguage: reportLanguage.value };
  if (maxTurns.value > 0) payload.maxTurns = maxTurns.value;

  if (target.mode === 'multi') {
    payload.dataPaths = target.files.map(f => typeof f === 'string' ? f : f.path);
  } else if (target.mode === 'folder') {
    payload.folderPath = target.path;
  } else {
    payload.dataPath = target.file.path;
  }

  try {
    const data = await api.startDiagnosis(payload);
    runId.value = data.runId;
    emit('started', data.runId);

    // Connect WebSocket FIRST, then execute — ensures we catch all events
    connectWS(data.runId);
    startElapsed();

    // Small delay to let WebSocket subscribe before process starts
    await new Promise(r => setTimeout(r, 100));
    await api.executeDiagnosis(data.runId);
  } catch (err) {
    failed.value = true;
    isRunning.value = false;
    errorMsg.value = err.message;
  }
}

async function stop() {
  if (runId.value) await api.stopDiagnosis(runId.value);
  isRunning.value = false;
  if (ws) ws.close();
  stopElapsed();
}

async function retryDiagnosis() {
  if (!runId.value) return;
  try {
    await api.continueDiagnosis(runId.value);
    completed.value = false; failed.value = false; isRunning.value = true;
    events.value = []; turnCount.value = 0; toolCount.value = 0; msgCount.value = 0;
    progressPct.value = 0; startTime.value = Date.now();
    currentPhase.value = 'Retrying analysis...';
    errorMsg.value = ''; score.value = null; verdict.value = null;
    reportPath.value = null; hitlPending.value = false;
    connectWS(runId.value);
    startElapsed();
  } catch (err) { errorMsg.value = err.message; }
}

function respondHITL(approved) {
  if (hitlId.value) {
    api.respondHITL(hitlId.value, approved).catch(() => {});
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'hitl_respond', hitlId: hitlId.value, approved }));
    }
  }
  if (!approved) hitlPending.value = false;
}

function openReport() { if (reportPath.value) emit('view-report', reportPath.value); }

function toggleThinking(ev) {
  const key = ev._seq;
  const next = new Set(expandedThinking.value);
  if (next.has(key)) next.delete(key); else next.add(key);
  expandedThinking.value = next;
}

function startElapsed() {
  stopElapsed();
  elapsedTimer = setInterval(() => {
    if (!startTime.value) return;
    const diff = Math.floor((Date.now() - startTime.value) / 1000);
    elapsed.value = `${Math.floor(diff / 60)}:${String(diff % 60).padStart(2, '0')}`;
  }, 1000);
}
function stopElapsed() { if (elapsedTimer) clearInterval(elapsedTimer); }

// Markdown
const ALLOWED_TAGS = ['h1','h2','h3','h4','h5','h6','p','br','hr','ul','ol','li','blockquote','pre','code','em','strong','a','img','table','thead','tbody','tr','th','td','span','div','details','summary'];
const ALLOWED_ATTR = ['href','src','alt','class','id','target','rel'];
function renderMd(text) {
  if (!text) return '';
  return DOMPurify.sanitize(marked(text, { breaks: true, gfm: true }), { ALLOWED_TAGS, ALLOWED_ATTR });
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

function formatSize(bytes) {
  if (!bytes) return '0 B';
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

watch(() => props.analysisTarget, (target) => {
  if (ws) ws.close();
  started.value = false; isRunning.value = false; completed.value = false;
  failed.value = false; events.value = []; runId.value = null;
  progressPct.value = 0; stopElapsed();
  if (target?.mode === 'file' && !sceneName.value) {
    sceneName.value = target.file.name.replace(/\.[^.]+$/, '').replace(/[^a-zA-Z0-9]/g, '_');
  } else if (target?.mode === 'folder' && !sceneName.value) {
    sceneName.value = target.name || '';
  }
});

// Watch autoRunId — connects to an already-running/continued diagnosis
watch(() => props.autoRunId, async (newRunId) => {
  if (!newRunId) return;

  started.value = true;
  isRunning.value = true;
  completed.value = false;
  failed.value = false;
  events.value = [];
  runId.value = newRunId;
  turnCount.value = 0; toolCount.value = 0; msgCount.value = 0;
  progressPct.value = 0;
  startTime.value = Date.now();
  currentPhase.value = 'Connecting to running diagnosis...';
  score.value = null; verdict.value = null; reportPath.value = null;
  errorMsg.value = ''; hitlPending.value = false;

  connectWS(newRunId);
  startElapsed();

  // Check status in case it already completed
  try {
    const status = await api.getRunStatus(newRunId);
    if (status.status === 'completed' || status.status === 'failed' || status.status === 'stopped') {
      isRunning.value = false;
      if (status.status === 'completed') {
        completed.value = true;
        reportPath.value = status.report_path;
        score.value = status.score;
        verdict.value = status.judge_verdict;
      } else {
        failed.value = true;
        errorMsg.value = status.error_message || 'Run ' + status.status;
      }
      progressPct.value = 100;
      stopElapsed();
    }
  } catch {}
});

onUnmounted(() => { if (ws) ws.close(); stopElapsed(); });
</script>

<style scoped>
/* ========== Data Source ========== */
.ds-card {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 16px; margin-bottom: 12px;
}
.ds-card-header { display: flex; align-items: center; gap: 12px; }
.ds-icon { font-size: 22px; }
.ds-title { font-size: 14px; font-weight: 600; }
.ds-sub { font-size: 12px; color: var(--text2); margin-top: 2px; font-family: monospace; }

/* ========== Control Bar ========== */
.ctrl-bar { margin-bottom: 16px; }
.ctrl-form {
  display: flex; flex-direction: column; gap: 10px;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 16px;
}
.ctrl-input, .ctrl-textarea {
  background: var(--surface2); border: 1px solid var(--border);
  border-radius: 6px; padding: 8px 12px; color: var(--text);
  font-size: 13px; font-family: inherit; width: 100%;
}
.ctrl-input:focus, .ctrl-textarea:focus { outline: none; border-color: var(--accent); }
.ctrl-textarea { resize: vertical; min-height: 60px; }
.ctrl-row { display: flex; gap: 10px; align-items: flex-end; }
.turns-control { display: flex; flex-direction: column; gap: 4px; }
.turns-label { font-size: 11px; color: var(--text2); text-transform: uppercase; letter-spacing: .5px; }
.ctrl-select {
  min-width: 130px; appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' fill='%238b949e' viewBox='0 0 16 16'%3E%3Cpath d='M8 11L3 6h10z'/%3E%3C/svg%3E");
  background-repeat: no-repeat; background-position: right 10px center; padding-right: 28px;
}
.ctrl-btn {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 10px 20px; border: none; border-radius: var(--radius);
  font-size: 14px; font-weight: 600; cursor: pointer; transition: all .15s;
}
.ctrl-btn-go { background: linear-gradient(135deg, var(--accent2), var(--accent)); color: #fff; }
.ctrl-btn-go:hover { opacity: .9; transform: translateY(-1px); }
.ctrl-btn-go:disabled { opacity: .4; cursor: not-allowed; transform: none; }

/* ========== Status Bar ========== */
.status-bar {
  display: flex; align-items: center; gap: 16px;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 12px 16px; margin-bottom: 8px;
}
.status-left { display: flex; align-items: center; gap: 8px; }
.status-dot {
  width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0;
}
.status-label { font-size: 14px; font-weight: 600; }
.status-run-id { font-size: 11px; color: var(--text2); font-family: monospace; background: var(--surface2); padding: 2px 8px; border-radius: 4px; }
.status-metrics { display: flex; gap: 16px; flex: 1; justify-content: center; }
.smetric { display: flex; align-items: center; gap: 4px; }
.sm-val { font-weight: 600; font-size: 13px; font-variant-numeric: tabular-nums; color: var(--text); }
.sm-lbl { font-size: 10px; color: var(--text2); text-transform: uppercase; }
.sm-time .sm-val { color: var(--yellow); }
.stop-btn {
  padding: 6px 14px; background: rgba(248,81,73,.08); color: var(--red);
  border: 1px solid rgba(248,81,73,.3); border-radius: 6px; font-size: 12px;
  font-weight: 600; cursor: pointer; transition: all .15s;
}
.stop-btn:hover { background: rgba(248,81,73,.15); }

/* ========== Phase Bar ========== */
.phase-bar {
  display: flex; align-items: center; gap: 10px;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 10px 16px; margin-bottom: 8px;
}
.phase-icon { font-size: 16px; }
.phase-text { font-size: 12px; color: var(--text2); white-space: nowrap; }
.phase-progress-track {
  flex: 1; height: 3px; background: var(--surface2); border-radius: 2px; overflow: hidden;
}
.phase-progress-fill {
  height: 100%; border-radius: 2px; transition: width .5s ease;
  background: linear-gradient(90deg, var(--accent2), var(--accent));
}

/* ========== Timeline ========== */
.timeline {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 20px 16px;
  max-height: 62vh; overflow-y: auto; scroll-behavior: smooth;
}
.tl-connecting {
  display: flex; align-items: center; gap: 10px;
  justify-content: center; padding: 32px; color: var(--text2); font-size: 13px;
}

/* Timeline Item */
.tl-item {
  display: flex; gap: 12px; padding: 4px 0;
  animation: fadeSlideIn .25s ease;
}
@keyframes fadeSlideIn {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Rail (vertical line + dot) */
.tl-rail {
  display: flex; flex-direction: column; align-items: center;
  width: 20px; flex-shrink: 0; position: relative;
}
.tl-rail::before {
  content: ''; position: absolute; top: 0; bottom: 0; left: 50%;
  width: 1px; background: var(--border); transform: translateX(-50%);
}
.tl-item:first-child .tl-rail::before { top: 50%; }
.tl-item:last-child .tl-rail::before { bottom: 50%; }

.tl-dot {
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
.tl-dot.pulse { animation: dotPulse 1.5s infinite; }
@keyframes dotPulse {
  0%, 100% { box-shadow: 0 0 0 0 currentColor; }
  50% { box-shadow: 0 0 0 4px transparent; }
}
.dot-blue.pulse { color: var(--accent); }
.dot-red.pulse { color: var(--red); }

/* Body */
.tl-body { flex: 1; min-width: 0; padding-right: 4px; }

/* ========== Event Cards ========== */
.tl-card {
  border-radius: 8px; overflow: hidden;
}

/* Thinking */
.card-thinking {
  background: rgba(188,140,255,.05); border: 1px solid rgba(188,140,255,.15);
  border-radius: 8px; cursor: pointer;
}
.card-thinking:hover { background: rgba(188,140,255,.08); }
.tl-card-header {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 12px; font-size: 12px;
}
.tl-card-icon { font-size: 14px; }
.tl-card-title { font-weight: 600; color: var(--text2); }
.tl-card-toggle { margin-left: auto; font-size: 10px; color: var(--text2); transition: transform .2s; }
.tl-card-toggle.open { transform: rotate(90deg); }
.tl-thinking-content {
  padding: 8px 16px 12px; font-size: 12px; color: var(--text2);
  line-height: 1.6; font-family: 'SF Mono', 'Fira Code', monospace;
  border-top: 1px solid rgba(188,140,255,.1);
  white-space: pre-wrap; max-height: 300px; overflow-y: auto;
}

/* Message */
.card-msg {
  background: transparent; border: none;
}
.msg-content {
  font-size: 13px; line-height: 1.8; color: var(--text);
}
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
.card-tool {
  border-radius: 8px; padding: 10px 14px;
}
.tool-read { background: rgba(88,166,255,.05); border: 1px solid rgba(88,166,255,.12); }
.tool-write { background: rgba(63,185,80,.05); border: 1px solid rgba(63,185,80,.12); }
.tool-bash { background: rgba(210,153,34,.05); border: 1px solid rgba(210,153,34,.12); }
.tool-web { background: rgba(34,211,238,.05); border: 1px solid rgba(34,211,238,.12); }
.tool-skill { background: rgba(188,140,255,.05); border: 1px solid rgba(188,140,255,.12); }
.tool-default { background: var(--surface2); border: 1px solid var(--border); }

.tl-tool-badge {
  display: inline-block; padding: 2px 10px; border-radius: 4px;
  font-size: 11px; font-weight: 700; background: rgba(255,255,255,.06); color: var(--text);
  letter-spacing: .3px;
}
.tl-tool-id { font-size: 10px; color: var(--text2); font-family: monospace; margin-left: 8px; }
.tl-tool-input {
  margin-top: 8px; font-size: 12px; line-height: 1.5;
  display: flex; align-items: flex-start; gap: 6px; flex-wrap: wrap;
}
.tl-tool-input .tool-label { color: var(--text2); font-weight: 600; font-size: 11px; flex-shrink: 0; }
.tl-tool-input code {
  font-family: 'SF Mono', 'Fira Code', monospace; font-size: 11px;
  color: var(--accent); background: rgba(88,166,255,.06);
  padding: 2px 8px; border-radius: 4px; word-break: break-all;
}
.tool-bash .tl-tool-input code { color: var(--yellow); background: rgba(210,153,34,.06); }
.tool-write .tl-tool-input code { color: var(--green); background: rgba(63,185,80,.06); }

/* Tool Result */
.tl-result-card {
  display: flex; align-items: flex-start; gap: 8px;
  padding: 6px 12px; border-radius: 6px; font-size: 12px;
}
.result-ok { background: rgba(63,185,80,.05); color: var(--green); }
.result-err { background: rgba(248,81,73,.05); color: var(--red); }
.result-icon { font-weight: 700; flex-shrink: 0; }
.result-text { color: var(--text2); font-family: 'SF Mono', monospace; font-size: 11px;
  max-height: 80px; overflow-y: auto; line-height: 1.5; word-break: break-all; }

/* System */
.tl-sys-card {
  font-size: 12px; color: var(--text2); padding: 6px 12px;
  background: rgba(139,148,158,.04); border-radius: 6px;
}
.tl-sys-card strong { color: var(--text); }

/* Stats */
.tl-stats-card {
  display: flex; gap: 20px; flex-wrap: wrap;
  padding: 10px 16px; background: rgba(210,153,34,.04);
  border: 1px solid rgba(210,153,34,.1); border-radius: 8px;
}
.stat-item { display: flex; flex-direction: column; gap: 2px; }
.stat-val { font-size: 14px; font-weight: 700; color: var(--yellow); font-variant-numeric: tabular-nums; }
.stat-lbl { font-size: 10px; color: var(--text2); text-transform: uppercase; }

/* HITL in timeline */
.card-hitl {
  padding: 10px 14px; background: rgba(248,81,73,.05);
  border: 1px solid rgba(248,81,73,.15); border-radius: 8px;
}
.hitl-warn { font-size: 12px; color: var(--red); font-weight: 600; margin-bottom: 6px; }
.hitl-cmd { font-size: 11px; color: var(--text2); font-family: monospace; word-break: break-all; }

/* Typing indicator */
.typing-indicator {
  display: flex; gap: 4px; padding: 8px 0;
}
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

/* Spinner */
.spinner-sm {
  display: inline-block; width: 14px; height: 14px;
  border: 2px solid var(--border); border-top-color: var(--accent);
  border-radius: 50%; animation: spin .8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ========== Completion Banner ========== */
.result-banner {
  display: flex; align-items: center; gap: 16px;
  padding: 20px; border-radius: var(--radius); margin-top: 8px;
}
.banner-pass { background: rgba(63,185,80,.06); border: 1px solid rgba(63,185,80,.2); }
.banner-warn { background: rgba(210,153,34,.06); border: 1px solid rgba(210,153,34,.2); }
.banner-fail { background: rgba(248,81,73,.06); border: 1px solid rgba(248,81,73,.2); }
.rb-icon {
  width: 40px; height: 40px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 20px; font-weight: 700;
}
.banner-pass .rb-icon { background: rgba(63,185,80,.15); color: var(--green); }
.banner-warn .rb-icon { background: rgba(210,153,34,.15); color: var(--yellow); }
.banner-fail .rb-icon { background: rgba(248,81,73,.15); color: var(--red); }
.rb-title { font-size: 16px; font-weight: 700; }
.rb-meta { display: flex; gap: 16px; font-size: 13px; color: var(--text2); margin-top: 4px; }
.rb-score { color: var(--green); font-weight: 600; }
.rb-verdict { font-weight: 600; }
.rb-error { color: var(--red); font-family: monospace; font-size: 12px; }
.rb-actions { display: flex; gap: 8px; margin-top: 8px; }
.rb-btn {
  padding: 8px 20px; border-radius: 6px; font-size: 13px;
  font-weight: 600; cursor: pointer; border: none; transition: all .15s;
}
.rb-btn-primary { background: var(--accent2); color: #fff; }
.rb-btn-primary:hover { background: var(--accent); }
.rb-btn-retry { background: rgba(248,81,73,.1); color: var(--red); border: 1px solid rgba(248,81,73,.3); }
.rb-btn-retry:hover { background: rgba(248,81,73,.2); }

/* ========== HITL Overlay ========== */
.hitl-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,.7);
  display: flex; align-items: center; justify-content: center;
  z-index: 1000; backdrop-filter: blur(4px);
}
.hitl-dialog {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 24px;
  max-width: 560px; width: 90%; box-shadow: 0 16px 48px rgba(0,0,0,.5);
}
.hitl-header { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
.hitl-icon { font-size: 28px; }
.hitl-title { font-size: 16px; font-weight: 700; }
.hitl-risk {
  display: inline-block; padding: 3px 10px; border-radius: 4px;
  font-size: 11px; font-weight: 700; letter-spacing: .5px; margin-bottom: 12px;
}
.risk-CRITICAL { background: rgba(248,81,73,.15); color: var(--red); }
.risk-HIGH { background: rgba(210,153,34,.15); color: var(--yellow); }
.hitl-desc { font-size: 13px; color: var(--text); margin-bottom: 12px; line-height: 1.5; }
.hitl-dialog pre {
  background: #0d1117; color: var(--red); padding: 12px; border-radius: 6px;
  font-size: 12px; font-family: 'SF Mono', monospace; white-space: pre-wrap;
  word-break: break-all; margin-bottom: 20px; border: 1px solid rgba(248,81,73,.2);
}
.hitl-actions { display: flex; gap: 12px; justify-content: flex-end; }
.hitl-btn {
  padding: 10px 24px; border: none; border-radius: var(--radius);
  font-size: 14px; font-weight: 600; cursor: pointer; transition: all .15s;
}
.hitl-deny { background: rgba(248,81,73,.12); color: var(--red); border: 1px solid var(--red); }
.hitl-deny:hover { background: rgba(248,81,73,.25); }
.hitl-approve { background: linear-gradient(135deg, var(--accent2), var(--accent)); color: #fff; }
.hitl-approve:hover { opacity: .9; transform: translateY(-1px); }
</style>
