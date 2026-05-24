<template>
  <div class="diagnosis-panel">
    <!-- Selected file info -->
    <div class="card" v-if="selectedFile">
      <div class="card-title">Selected Data</div>
      <div class="selected-info">
        <div class="info-row">
          <span class="info-label">File:</span>
          <span class="info-value">{{ selectedFile.name }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">Size:</span>
          <span class="info-value">{{ formatSize(selectedFile.size) }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">Path:</span>
          <span class="info-value path">{{ selectedFile.path }}</span>
        </div>
      </div>
    </div>

    <div class="card" v-else>
      <div class="empty-state">
        <p>No data file selected. Go to the Data tab and select a file to analyze.</p>
      </div>
    </div>

    <!-- Analysis form -->
    <div class="card" v-if="selectedFile && !isRunning">
      <div class="card-title">Analysis Configuration</div>
      <div class="form-group">
        <label>Scene Name</label>
        <input v-model="sceneName" placeholder="Auto-generated from file name" />
      </div>
      <div class="form-group">
        <label>Your Question / Analysis Goal</label>
        <textarea
          v-model="userQuestion"
          placeholder="Describe what you want to diagnose. For example: 'Why did the coating thickness deviate after shift change?' or 'Analyze the root cause of temperature anomalies in the reactor'"
          rows="4"
        ></textarea>
      </div>
      <div class="form-group">
        <label>Max Turns</label>
        <input v-model.number="maxTurns" type="number" min="10" max="500" style="max-width:120px" />
      </div>
      <div class="form-actions">
        <button class="btn btn-primary" @click="startDiagnosis" :disabled="!selectedFile">
          Start Analysis
        </button>
      </div>
    </div>

    <!-- Running state -->
    <div class="card" v-if="isRunning">
      <div class="card-title">
        <div class="spinner"></div>
        <span>Diagnosis Running...</span>
        <span class="badge badge-blue">{{ runId }}</span>
      </div>
      <div class="progress-bar" style="margin-bottom:16px">
        <div class="progress-fill" :style="{ width: progressPct + '%' }"></div>
      </div>
      <div class="stop-actions">
        <button class="btn btn-danger btn-sm" @click="stopDiagnosis">Stop Analysis</button>
      </div>
    </div>

    <!-- Live output -->
    <div class="card output-card" v-if="isRunning || messages.length > 0">
      <div class="card-title">
        Live Output
        <span class="badge badge-green" v-if="!isRunning && completed">Completed</span>
        <span class="badge badge-red" v-if="!isRunning && failed">Failed</span>
      </div>
      <div class="output-stream" ref="outputStream">
        <div
          v-for="(msg, i) in messages"
          :key="i"
          :class="['output-line', 'output-' + msg.type]"
        >
          <span class="output-tag" v-if="msg.type === 'tool_use'">TOOL</span>
          <span class="output-tag tag-error" v-if="msg.type === 'error'">ERR</span>
          <span class="output-tag tag-system" v-if="msg.type === 'system'">SYS</span>
          <span class="output-text">{{ msg.content }}</span>
        </div>
        <div v-if="isRunning" class="output-line output-waiting">
          <div class="spinner" style="width:12px;height:12px;border-width:1.5px;"></div>
          <span class="output-text">Waiting for output...</span>
        </div>
      </div>
      <div v-if="truncated" class="truncation-notice">
        Output truncated — showing last 200 messages
      </div>
    </div>

    <!-- Result summary -->
    <div class="card" v-if="result">
      <div class="card-title">Result</div>
      <div class="result-info">
        <div class="info-row">
          <span class="info-label">Status:</span>
          <span :class="['badge', result.status === 'completed' ? 'badge-green' : 'badge-red']">
            {{ result.status }}
          </span>
        </div>
        <div class="info-row" v-if="result.score != null">
          <span class="info-label">Score:</span>
          <span class="info-value">{{ result.score }}/100</span>
        </div>
        <div class="info-row" v-if="result.verdict">
          <span class="info-label">Verdict:</span>
          <span :class="['badge', verdictClass(result.verdict)]">{{ result.verdict }}</span>
        </div>
        <div class="info-row" v-if="result.reportPath">
          <span class="info-label">Report:</span>
          <button class="btn btn-sm" @click="viewReport">View Report</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, watch, onUnmounted } from 'vue';
import { api } from '../api.js';

const props = defineProps({
  selectedFile: { type: Object, default: null },
});

const emit = defineEmits(['started']);

const sceneName = ref('');
const userQuestion = ref('');
const maxTurns = ref(200);
const isRunning = ref(false);
const completed = ref(false);
const failed = ref(false);
const runId = ref(null);
const messages = ref([]);
const result = ref(null);
const progressPct = ref(0);
const outputStream = ref(null);
let eventSource = null;
let didComplete = false;
let didError = false;
let msgCount = 0;
const MAX_MESSAGES = 200;
const truncated = ref(false);

// Cleanup on component unmount (tab switch)
onUnmounted(() => {
  closeSSE();
});

watch(() => props.selectedFile, (file) => {
  // Full teardown of any running diagnosis
  closeSSE();
  isRunning.value = false;
  progressPct.value = 0;
  didComplete = false;
  didError = false;
  msgCount = 0;
  truncated.value = false;

  if (file && !sceneName.value) {
    sceneName.value = file.name.replace(/\.[^.]+$/, '').replace(/[^a-zA-Z0-9]/g, '_');
  }
  messages.value = [];
  result.value = null;
  completed.value = false;
  failed.value = false;
});

async function startDiagnosis() {
  if (!props.selectedFile) return;

  closeSSE();
  isRunning.value = true;
  completed.value = false;
  failed.value = false;
  messages.value = [];
  result.value = null;
  msgCount = 0;
  didComplete = false;
  didError = false;
  truncated.value = false;
  progressPct.value = 5;

  try {
    const data = await api.startDiagnosis({
      dataPath: props.selectedFile.path,
      userQuestion: userQuestion.value,
      sceneName: sceneName.value || undefined,
      maxTurns: maxTurns.value,
    });

    runId.value = data.runId;
    emit('started', data.runId);
    addMessage('system', `Run started: ${data.runId} (${data.name})`);

    // Open SSE stream
    eventSource = new EventSource(api.streamUrl(data.runId));

    function safeParse(data) {
      try { return JSON.parse(data); } catch { return null; }
    }

    eventSource.addEventListener('status', (e) => {
      const d = safeParse(e.data);
      if (d) addMessage('system', `Status: ${d.status}`);
    });

    eventSource.addEventListener('message', (e) => {
      const d = safeParse(e.data);
      if (d) {
        const text = d.content || '';
        if (text) {
          addMessage('text', text);
          progressPct.value = Math.min(90, progressPct.value + 2);
        }
      }
    });

    eventSource.addEventListener('tool_use', (e) => {
      const d = safeParse(e.data);
      if (d) {
        const inputStr = (d.input != null && typeof d.input === 'object')
          ? JSON.stringify(d.input).slice(0, 200)
          : String(d.input ?? '').slice(0, 200);
        addMessage('tool_use', `[${d.name}] ${inputStr}`);
        progressPct.value = Math.min(90, progressPct.value + 5);
      }
    });

    eventSource.addEventListener('log', (e) => {
      const d = safeParse(e.data);
      if (d) addMessage('system', d.message);
    });

    eventSource.addEventListener('stats', (e) => {
      const d = safeParse(e.data);
      if (d) addMessage('system', `Stats: ${JSON.stringify(d).slice(0, 200)}`);
    });

    eventSource.addEventListener('complete', (e) => {
      if (didError) return;
      didComplete = true;
      const d = safeParse(e.data);
      completed.value = true;
      isRunning.value = false;
      progressPct.value = 100;
      result.value = d || {};
      addMessage('system', `Completed! Score: ${d?.score ?? 'N/A'}, Verdict: ${d?.verdict ?? 'N/A'}`);
      closeSSE();
    });

    eventSource.addEventListener('error', (e) => {
      if (didComplete) return;
      didError = true;
      const d = safeParse(e.data);
      failed.value = true;
      isRunning.value = false;
      result.value = d || {};
      addMessage('error', d?.error || 'Diagnosis failed');
      closeSSE();
    });

    eventSource.onerror = () => {
      if (didComplete || didError) return;
      if (isRunning.value) {
        failed.value = true;
        isRunning.value = false;
        addMessage('error', 'Connection lost');
        closeSSE();
      }
    };
  } catch (err) {
    isRunning.value = false;
    failed.value = true;
    addMessage('error', 'Failed to start: ' + err.message);
  }
}

function stopDiagnosis() {
  if (runId.value) {
    api.stopDiagnosis(runId.value);
  }
  closeSSE();
  isRunning.value = false;
  completed.value = false;
  failed.value = false;
  addMessage('system', 'Stopped by user');
}

function closeSSE() {
  if (eventSource) {
    eventSource.close();
    eventSource = null;
  }
}

function addMessage(type, content) {
  msgCount++;
  messages.value.push({ type, content });
  if (messages.value.length > MAX_MESSAGES) {
    messages.value = messages.value.slice(-MAX_MESSAGES);
    truncated.value = true;
  }
  nextTick(() => {
    if (outputStream.value) {
      outputStream.value.scrollTop = outputStream.value.scrollHeight;
    }
  });
}

function viewReport() {
  if (result.value?.reportPath) {
    window.open(`/workspace-files/${result.value.reportPath}`, '_blank');
  }
}

function verdictClass(verdict) {
  if (verdict === 'PASS' || verdict === 'ENDORSED') return 'badge-green';
  if (verdict === 'CONDITIONAL' || verdict === 'NEEDS_REPAIR') return 'badge-yellow';
  return 'badge-red';
}

function formatSize(bytes) {
  if (!bytes) return '0 B';
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}
</script>

<style scoped>
.form-group { margin-bottom: 16px; }
.form-group label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: var(--text2);
  margin-bottom: 6px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.form-actions { margin-top: 20px; }

.selected-info { display: flex; flex-direction: column; gap: 6px; }
.info-row { display: flex; align-items: center; gap: 8px; }
.info-label { font-size: 12px; color: var(--text2); min-width: 60px; }
.info-value { font-size: 13px; }
.info-value.path { font-family: monospace; font-size: 12px; color: var(--accent); }

.output-card { margin-top: 16px; }

.output-stream {
  background: var(--surface2);
  border-radius: var(--radius);
  padding: 12px;
  max-height: 500px;
  overflow-y: auto;
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: 12px;
  line-height: 1.6;
}

.output-line {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 2px 0;
}

.output-tag {
  display: inline-block;
  padding: 0 4px;
  background: rgba(88, 166, 255, 0.15);
  color: var(--accent);
  border-radius: 3px;
  font-size: 10px;
  font-weight: 600;
  flex-shrink: 0;
  line-height: 18px;
}

.tag-error { background: rgba(248, 81, 73, 0.15); color: var(--red); }
.tag-system { background: rgba(139, 148, 158, 0.15); color: var(--text2); }

.output-text {
  color: var(--text);
  white-space: pre-wrap;
  word-break: break-all;
}

.output-error .output-text { color: var(--red); }
.output-system .output-text { color: var(--text2); }

.output-waiting {
  color: var(--text2);
  display: flex;
  align-items: center;
  gap: 8px;
}

.truncation-notice {
  font-size: 11px;
  color: var(--yellow);
  background: rgba(210, 153, 34, 0.08);
  padding: 4px 12px;
  border-radius: 4px;
  margin-top: 8px;
  text-align: center;
}

.stop-actions { margin-top: 12px; }

.result-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
</style>
