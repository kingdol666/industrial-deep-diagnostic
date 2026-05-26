<template>
  <div class="diagnosis-view">
    <!-- Back button (when viewing a specific run) -->
    <div class="dv-nav" v-if="viewingRun">
      <button class="btn btn-sm" @click="goBack">← Back to Tasks</button>
      <span class="dv-nav-title" v-if="runName">{{ runName }}</span>
      <span class="dv-nav-id" v-if="runId">#{{ runId }}</span>
    </div>

    <!-- ============ TASK LIST MODE ============ -->
    <template v-if="!viewingRun">
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

      <!-- Task List -->
      <TaskList
        @view-run="openRun"
        @view-report="onViewReport"
        @new-task="goToData"
      />
    </template>

    <!-- ============ LIVE RUN MODE ============ -->
    <template v-if="viewingRun">
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

      <!-- Message Stream -->
      <MessageStream
        :events="events"
        :isRunning="isRunning"
        :connected="connected"
      />

      <!-- Answer Bar -->
      <AnswerBar
        :questionData="currentQuestion"
        :runId="runId"
        @answer="onAnswer"
        @skip="onSkipQuestion"
      />

      <!-- Chat Input (for running AND failed sessions) -->
      <ChatInput
        v-if="viewingRun && (isRunning || failed)"
        ref="chatInputRef"
        :isRunning="isRunning"
        :isFailed="failed"
        :runId="runId"
        @send-message="onSendMessage"
        @resume-with-message="onResumeWithMessage"
      />

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
            <button v-if="reportPath" class="rb-btn rb-btn-md" @click="downloadReportMD">Download MD</button>
            <button v-if="failed && runId" class="rb-btn rb-btn-retry" @click="retryDiagnosis">Retry (Same Parameters)</button>
          </div>
          <div class="rb-hint" v-if="failed">
            To debug the failure, type a follow-up instruction in the chat input below and click "Send & Resume".
          </div>
        </div>
      </div>

      <!-- Chart Dashboard -->
      <div v-if="completed && chartData" class="card chart-dashboard">
        <div class="card-title" style="display:flex;align-items:center;justify-content:space-between">
          <span>📊 诊断数据可视化</span>
          <button class="btn btn-sm" @click="toggleCharts">
            {{ showCharts ? '收起' : '展开' }}
          </button>
        </div>
        <div v-if="showCharts" class="chart-grid">
          <div v-if="chartData.heatmap" class="chart-cell chart-cell-full">
            <div class="card-title" style="font-size:13px">变量相关性矩阵</div>
            <HeatmapChart
              :data="chartData.heatmap.data"
              :x-labels="chartData.heatmap.xLabels"
              :y-labels="chartData.heatmap.yLabels"
              title="Correlation Matrix"
            />
          </div>
          <div v-if="chartData.confidence" class="chart-cell chart-cell-half">
            <GaugeChart
              :value="chartData.confidence.overall"
              title="诊断置信度"
              unit="%"
            />
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
import { api } from '../../api/index.js';
import TaskList from './TaskList.vue';
import MessageStream from './MessageStream.vue';
import AnswerBar from './AnswerBar.vue';
import ChatInput from './ChatInput.vue';
import { HeatmapChart, GaugeChart } from '../charts/index.js';

const props = defineProps({
  analysisTarget: { type: Object, default: null },
  autoRunId: { type: String, default: null },
});

const emit = defineEmits(['started', 'view-report', 'go-data']);

// --- State ---
const viewingRun = ref(false);
const sceneName = ref('');
const userQuestion = ref('');
const maxTurns = ref(0);
const reportLanguage = ref('zh');
const started = ref(false);
const isRunning = ref(false);
const completed = ref(false);
const failed = ref(false);
const runId = ref(null);
const runName = ref('');
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
const progressPct = ref(0);
const errorMsg = ref('');
const currentQuestion = ref(null);
const chatInputRef = ref(null);

const hitlPending = ref(false);
const hitlId = ref(null);
const hitlCommand = ref('');
const hitlRisk = ref('');
const hitlDesc = ref('');

const chartData = ref(null);
const showCharts = ref(true);

let eventSource = null;
let elapsedTimer = null;

// --- Computed ---
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

// --- SSE Connection ---
function connectSSE(rid) {
  closeSSE();

  eventSource = new EventSource(api.streamUrl(rid));

  eventSource.addEventListener('status', (e) => {
    try {
      const d = JSON.parse(e.data);
      if (d.status === 'running') {
        isRunning.value = true;
        started.value = true;
        if (!startTime.value) { startTime.value = Date.now(); startElapsed(); }
      }
    } catch {}
  });

  eventSource.addEventListener('message', (e) => {
    try {
      const d = JSON.parse(e.data);
      msgCount.value++;
      events.value.push({ type: 'message', data: d, _seq: Date.now() });
      tickProgress(2);
    } catch {}
  });

  eventSource.addEventListener('tool_use', (e) => {
    try {
      const d = JSON.parse(e.data);
      toolCount.value++;
      events.value.push({ type: 'tool_use', data: d, _seq: Date.now() });
      tickProgress(3);
      detectPhase(d.name);
    } catch {}
  });

  eventSource.addEventListener('tool_result', (e) => {
    try {
      const d = JSON.parse(e.data);
      events.value.push({ type: 'tool_result', data: d, _seq: Date.now() });
    } catch {}
  });

  eventSource.addEventListener('thinking', (e) => {
    try {
      const d = JSON.parse(e.data);
      events.value.push({ type: 'thinking', data: d, _seq: Date.now() });
    } catch {}
  });

  eventSource.addEventListener('system', (e) => {
    try {
      const d = JSON.parse(e.data);
      events.value.push({ type: 'system', subtype: d?.subtype || 'system', data: d, _seq: Date.now() });
    } catch {}
  });

  eventSource.addEventListener('stats', (e) => {
    try {
      const d = JSON.parse(e.data);
      turnCount.value = d.numTurns || 0;
      events.value.push({ type: 'stats', data: d, _seq: Date.now() });
      progressPct.value = Math.min(95, Math.max(progressPct.value, turnCount.value * 0.3));
    } catch {}
  });

  eventSource.addEventListener('log', (e) => {
    try {
      const d = JSON.parse(e.data);
      events.value.push({ type: 'system', subtype: 'log', data: d, _seq: Date.now() });
    } catch {}
  });

  eventSource.addEventListener('question', (e) => {
    try {
      const d = JSON.parse(e.data);
      currentQuestion.value = d;
      events.value.push({
        type: 'question',
        data: d,
        _seq: Date.now(),
      });
    } catch {}
  });

  eventSource.addEventListener('task_progress', (e) => {
    try {
      const d = JSON.parse(e.data);
      events.value.push({ type: 'task_progress', data: d, _seq: Date.now() });
    } catch {}
  });

  eventSource.addEventListener('unknown', (e) => {
    try {
      const d = JSON.parse(e.data);
      events.value.push({ type: 'unknown', subtype: d?.subtype || 'unknown', data: d, _seq: Date.now() });
    } catch {}
  });

  eventSource.addEventListener('hitl_request', (e) => {
    try {
      const d = JSON.parse(e.data);
      hitlId.value = d.hitlId;
      hitlCommand.value = d.command;
      hitlRisk.value = d.riskLevel;
      hitlDesc.value = d.riskDesc;
      hitlPending.value = true;
      events.value.push({ type: 'hitl_request', data: d, _seq: Date.now() });
    } catch {}
  });

  eventSource.addEventListener('hitl_result', () => {
    hitlPending.value = false;
  });

  eventSource.addEventListener('complete', (e) => {
    try {
      const d = JSON.parse(e.data);
      if (d.status === 'failed') {
        failed.value = true;
        completed.value = false;
        isRunning.value = false;
        errorMsg.value = d.error || 'Diagnosis failed';
      } else {
        completed.value = true;
        failed.value = false;
        isRunning.value = false;
        score.value = d.score;
        verdict.value = d.verdict;
        reportPath.value = d.reportPath;
        if (d.reportPath) {
          const runDir = d.reportPath.split('/').slice(0, -1).join('/');
          fetchChartData(runDir);
        }
        errorMsg.value = '';
      }
      progressPct.value = 100;
      hitlPending.value = false;
      currentQuestion.value = null;
      emit('started', runId.value);
      stopElapsed();
    } catch {}
  });

  eventSource.addEventListener('error', (e) => {
    try {
      const d = JSON.parse(e.data);
      failed.value = true;
      isRunning.value = false;
      errorMsg.value = d.error || 'Unknown error';
      stopElapsed();
    } catch {}
  });

  eventSource.onopen = () => {
    connected.value = true;
  };

  eventSource.onerror = () => {
    connected.value = false;
    if (isRunning.value) {
      setTimeout(() => {
        if (isRunning.value && runId.value) connectSSE(runId.value);
      }, 3000);
    }
  };
}

function closeSSE() {
  if (eventSource) {
    eventSource.close();
    eventSource = null;
  }
}

// --- Actions ---
async function start() {
  if (!props.analysisTarget) return;

  viewingRun.value = true;
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
  currentQuestion.value = null;

  const target = props.analysisTarget;
  const payload = {
    userQuestion: userQuestion.value,
    sceneName: sceneName.value || undefined,
    reportLanguage: reportLanguage.value,
  };
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
    runName.value = data.name;
    emit('started', data.runId);

    connectSSE(data.runId);
    startElapsed();

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
  closeSSE();
  stopElapsed();
}

async function retryDiagnosis() {
  if (!runId.value) return;
  try {
    await api.continueDiagnosis(runId.value);
    completed.value = false;
    failed.value = false;
    isRunning.value = true;
    startTime.value = Date.now();
    currentPhase.value = 'Continuing analysis...';
    errorMsg.value = '';
    score.value = null;
    verdict.value = null;
    reportPath.value = null;
    hitlPending.value = false;
    currentQuestion.value = null;
    // Append separator so user sees continuation, not restart
    events.value.push({
      type: 'system',
      subtype: 'continue',
      data: { message: 'Continuing from previous state...' },
      _seq: Date.now(),
    });
    connectSSE(runId.value);
    startElapsed();
  } catch (err) { errorMsg.value = err.message; }
}

function respondHITL(approved) {
  if (hitlId.value) {
    api.respondHITL(hitlId.value, approved).catch(() => {});
  }
  if (!approved) hitlPending.value = false;
}

function openReport() {
  if (reportPath.value) emit('view-report', reportPath.value);
}

async function downloadReportMD() {
  if (!reportPath.value) return;
  const parts = reportPath.value.split('/');
  const runName = parts[parts.length - 2] || '';
  if (!runName) return;
  try {
    const data = await api.getReport(runName);
    if (!data || !data.content) return;
    const blob = new Blob([data.content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `diagnostic-report-${runName}.md`;
    a.click();
    URL.revokeObjectURL(url);
  } catch (err) {
    console.error('Failed to download report:', err);
  }
}

async function onAnswer({ questionId, toolUseId, answers }) {
  if (!runId.value) return;
  try {
    await api.submitAnswer(runId.value, questionId, toolUseId, answers);
    currentQuestion.value = null;
  } catch (err) {
    console.error('Failed to submit answer:', err);
  }
}

function onSkipQuestion() {
  currentQuestion.value = null;
}

async function onSendMessage(message) {
  if (!runId.value) return;
  try {
    await api.sendChat(runId.value, message);
    events.value.push({
      type: 'system',
      subtype: 'chat_sent',
      data: { message },
      _seq: Date.now(),
    });
  } catch (err) {
    events.value.push({
      type: 'system',
      subtype: 'chat_error',
      data: { error: err.message },
      _seq: Date.now(),
    });
  }
}

async function onResumeWithMessage(message) {
  if (!runId.value) return;
  try {
    await api.continueDiagnosis(runId.value, message);
    failed.value = false;
    completed.value = false;
    isRunning.value = true;
    startTime.value = Date.now();
    currentPhase.value = 'Resuming with follow-up...';
    errorMsg.value = '';
    score.value = null;
    verdict.value = null;
    reportPath.value = null;
    hitlPending.value = false;
    currentQuestion.value = null;
    // Append separator — preserve history so user sees continuation
    events.value.push({
      type: 'system',
      subtype: 'continue',
      data: { message: `User: ${message}` },
      _seq: Date.now(),
    });
    connectSSE(runId.value);
    startElapsed();
  } catch (err) {
    errorMsg.value = err.message;
  }
}

function openRun(rid) {
  viewingRun.value = true;
  runId.value = rid;
  connectSSE(rid);
  startElapsed();
  isRunning.value = true;
  started.value = true;

  // Check current status (used when SSE doesn't settle quickly)
  api.getRunStatus(rid).then(status => {
    runName.value = status.name || '';
    // Only apply if SSE hasn't already resolved
    if (!completed.value && !failed.value) {
      if (status.status === 'completed') {
        completed.value = true;
        isRunning.value = false;
        reportPath.value = status.report_path;
        if (status.report_path) {
          const runDir = status.report_path.split('/').slice(0, -1).join('/');
          fetchChartData(runDir);
        }
        score.value = status.score;
        verdict.value = status.judge_verdict;
        progressPct.value = 100;
        stopElapsed();
      } else if (status.status === 'failed' || status.status === 'stopped') {
        failed.value = true;
        isRunning.value = false;
        errorMsg.value = status.error_message || 'Run ' + status.status;
        stopElapsed();
      }
    }
  }).catch(() => {});
}

function goBack() {
  closeSSE();
  viewingRun.value = false;
  started.value = false;
  isRunning.value = false;
  completed.value = false;
  failed.value = false;
  runId.value = null;
  events.value = [];
  stopElapsed();
}

function onViewReport(reportPath) {
  emit('view-report', reportPath);
}

function goToData() {
  emit('go-data');
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

function startElapsed() {
  stopElapsed();
  startTime.value = Date.now();
  elapsedTimer = setInterval(() => {
    if (!startTime.value) return;
    const diff = Math.floor((Date.now() - startTime.value) / 1000);
    elapsed.value = `${Math.floor(diff / 60)}:${String(diff % 60).padStart(2, '0')}`;
  }, 1000);
}

function stopElapsed() {
  if (elapsedTimer) clearInterval(elapsedTimer);
}

function formatSize(bytes) {
  if (!bytes) return '0 B';
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function toggleCharts() { showCharts.value = !showCharts.value; }

async function fetchChartData(runDir) {
  if (!runDir) return;
  try {
    const dirName = runDir.replace('workspace/diagnostic-runs/', '');
    const res = await fetch(`/api/analysis/chart-data/${encodeURIComponent(dirName)}`);
    const json = await res.json();
    if (json.success && json.data) chartData.value = json.data;
  } catch (err) {
    console.error('Failed to fetch chart data:', err);
  }
}

// --- Watchers ---
watch(() => props.analysisTarget, (target) => {
  closeSSE();
  viewingRun.value = false;
  started.value = false;
  isRunning.value = false;
  completed.value = false;
  failed.value = false;
  events.value = [];
  runId.value = null;
  progressPct.value = 0;
  stopElapsed();
  currentQuestion.value = null;
  if (target?.mode === 'file' && !sceneName.value) {
    sceneName.value = target.file.name.replace(/\.[^.]+$/, '').replace(/[^a-zA-Z0-9]/g, '_');
  } else if (target?.mode === 'folder' && !sceneName.value) {
    sceneName.value = target.name || '';
  }
});

// Watch autoRunId — connects to an already-running/continued diagnosis
watch(() => props.autoRunId, async (newRunId) => {
  if (!newRunId) return;

  viewingRun.value = true;
  started.value = true;
  isRunning.value = true;
  completed.value = false;
  failed.value = false;
  events.value = [];
  runId.value = newRunId;
  turnCount.value = 0;
  toolCount.value = 0;
  msgCount.value = 0;
  progressPct.value = 0;
  startTime.value = Date.now();
  currentPhase.value = 'Connecting to running diagnosis...';
  score.value = null;
  verdict.value = null;
  reportPath.value = null;
  errorMsg.value = '';
  hitlPending.value = false;
  currentQuestion.value = null;

  connectSSE(newRunId);
  startElapsed();

  try {
    const status = await api.getRunStatus(newRunId);
    runName.value = status.name || '';
    if (status.status === 'completed' || status.status === 'failed' || status.status === 'stopped') {
      isRunning.value = false;
      if (status.status === 'completed') {
        completed.value = true;
        reportPath.value = status.report_path;
        if (status.report_path) {
          const runDir = status.report_path.split('/').slice(0, -1).join('/');
          fetchChartData(runDir);
        }
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

onUnmounted(() => {
  closeSSE();
  stopElapsed();
});
</script>

<style scoped>
.diagnosis-view { display: flex; flex-direction: column; gap: 8px; }

/* Nav */
.dv-nav {
  display: flex; align-items: center; gap: 12px;
  margin-bottom: 8px;
}
.dv-nav-title { font-size: 14px; font-weight: 600; color: var(--text); }
.dv-nav-id { font-size: 11px; color: var(--text2); font-family: monospace; background: var(--surface2); padding: 2px 8px; border-radius: 4px; }

/* ========== Data Source ========== */
.ds-card {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 16px; margin-bottom: 8px;
}
.ds-card-header { display: flex; align-items: center; gap: 12px; }
.ds-icon { font-size: 22px; }
.ds-title { font-size: 14px; font-weight: 600; }
.ds-sub { font-size: 12px; color: var(--text2); margin-top: 2px; font-family: monospace; }

/* ========== Control Bar ========== */
.ctrl-bar { margin-bottom: 12px; }
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
  border-radius: var(--radius); padding: 12px 16px; margin-bottom: 4px;
}
.status-left { display: flex; align-items: center; gap: 8px; }
.status-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.status-dot.dot-green { background: var(--green); }
.status-dot.dot-red { background: var(--red); }
.status-dot.dot-blue { background: var(--accent); }
.status-dot.dot-blue.pulse { animation: dotPulse 1.5s infinite; }
.status-dot.dot-gray { background: var(--text2); }
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
  border-radius: var(--radius); padding: 10px 16px; margin-bottom: 4px;
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

@keyframes dotPulse {
  0%, 100% { box-shadow: 0 0 0 0 var(--accent); }
  50% { box-shadow: 0 0 0 4px transparent; }
}

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
.rb-btn-md { background: rgba(88,166,255,.1); color: var(--accent); border: 1px solid rgba(88,166,255,.3); }
.rb-btn-md:hover { background: rgba(88,166,255,.2); }
.rb-btn-retry { background: rgba(248,81,73,.1); color: var(--red); border: 1px solid rgba(248,81,73,.3); }
.rb-btn-retry:hover { background: rgba(248,81,73,.2); }
.rb-hint { font-size: 12px; color: var(--text2); margin-top: 8px; font-style: italic; }

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
.risk-HIGH, .risk-SERIOUS { background: rgba(248,81,73,.15); color: var(--red); }
.risk-MEDIUM, .risk-WARN { background: rgba(210,153,34,.15); color: var(--yellow); }
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

.chart-dashboard { margin-top: 16px; }
.chart-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-top: 12px;
}
.chart-cell { min-height: 300px; }
.chart-cell-full { grid-column: 1 / -1; }
.chart-cell-half { grid-column: span 1; }
</style>
