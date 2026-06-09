<template>
  <div :class="['diagnosis-view', { 'diagnosis-view-run': viewingRun }]">
    <!-- Back button (when viewing a specific run) -->
    <div class="dv-nav" v-if="viewingRun">
      <button class="btn btn-sm" @click="goBack">← 返回任务列表</button>
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
              <template v-else>已选择 {{ analysisTarget.files.length }} 个文件</template>
            </div>
            <div class="ds-sub" v-if="analysisTarget.mode === 'file'">
              {{ formatSize(analysisTarget.file.size) }} · {{ analysisTarget.file.path }}
            </div>
            <div class="ds-sub" v-else-if="analysisTarget.mode === 'folder'">
              {{ analysisTarget.csvCount || 0 }} 个数据文件
            </div>
          </div>
        </div>
      </div>

      <!-- Control Panel -->
      <div class="ctrl-bar" v-if="analysisTarget && !started">
        <div class="ctrl-form">
          <input v-model="sceneName" placeholder="场景名称（可选）" class="ctrl-input" />
          <textarea v-model="userQuestion" placeholder="请输入你希望系统诊断的问题" rows="3" class="ctrl-textarea"></textarea>
          <div class="ctrl-row">
            <div class="turns-control">
              <label class="turns-label">最大轮次</label>
              <select v-model.number="maxTurns" class="ctrl-input ctrl-select">
                <option :value="0">不限</option>
                <option :value="50">50</option>
                <option :value="100">100</option>
                <option :value="200">200</option>
                <option :value="300">300</option>
                <option :value="500">500</option>
              </select>
            </div>
            <div class="turns-control">
              <label class="turns-label">报告语言</label>
              <select v-model="reportLanguage" class="ctrl-input ctrl-select">
                <option value="zh">中文</option>
                <option value="en">English</option>
              </select>
            </div>
            <button class="ctrl-btn ctrl-btn-go" @click="start" :disabled="!analysisTarget">
              开始诊断
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
      <div class="run-layout">
        <div class="run-header">
          <!-- Status Bar -->
          <div class="status-bar">
            <div class="status-left">
              <div class="status-dot" :class="statusDotClass"></div>
              <span class="status-label">{{ statusLabel }}</span>
              <span class="status-run-id">#{{ runId }}</span>
            </div>
            <div class="status-metrics">
              <div class="smetric"><span class="sm-val">{{ turnCount }}</span><span class="sm-lbl">轮次</span></div>
              <div class="smetric"><span class="sm-val">{{ toolCount }}</span><span class="sm-lbl">工具</span></div>
              <div class="smetric"><span class="sm-val">{{ msgCount }}</span><span class="sm-lbl">消息</span></div>
              <div class="smetric sm-time"><span class="sm-val">{{ elapsed }}</span></div>
            </div>
            <button v-if="canStop" class="stop-btn" @click="stop">停止</button>
          </div>

          <!-- Phase Indicator -->
          <div class="phase-bar" v-if="currentPhase">
            <div class="phase-icon">{{ phaseIcon }}</div>
            <span class="phase-text">{{ currentPhase }}</span>
            <div class="phase-progress-track">
              <div class="phase-progress-fill" :style="{ width: progressPct + '%' }"></div>
            </div>
          </div>
        </div>

        <div class="run-body">
          <div class="run-message-region">
            <MessageStream
              :key="runId || 'diagnosis-run'"
              :events="events"
              :isRunning="isRunning"
              :connected="connected"
            />
          </div>

          <div v-if="completed || failed" class="run-support-stack">
            <!-- Completion Banner -->
            <div :class="['result-banner', verdictClass]">
              <div class="rb-icon">{{ resultBannerIcon }}</div>
              <div class="rb-info">
                <div class="rb-title">{{ resultBannerTitle }}</div>
                <div class="rb-meta">
                  <span v-if="score != null" class="rb-score">评分: {{ score }}/100</span>
                  <span v-if="verdict" class="rb-verdict">{{ verdict }}</span>
                  <span v-if="errorMsg" class="rb-error">{{ errorMsg }}</span>
                </div>
                <div class="rb-actions">
                  <button v-if="reportPath" class="rb-btn rb-btn-primary" @click="openReport">查看完整报告</button>
                  <button v-if="reportPath" class="rb-btn rb-btn-md" @click="downloadReportMD">下载 Markdown</button>
                  <button v-if="failed && runId" class="rb-btn rb-btn-retry" @click="retryDiagnosis">继续诊断</button>
                </div>
                <div class="rb-hint" v-if="failed">
                  可在下方输入补充指令，并基于本次上下文继续诊断。
                </div>
              </div>
            </div>

            <!-- Chart Dashboard -->
            <div v-if="completed" class="card chart-dashboard">
              <div class="card-title" style="display:flex;align-items:center;justify-content:space-between">
                <span>📊 诊断数据可视化</span>
                <div style="display:flex;gap:6px;">
                  <button v-if="chartData === null" class="btn btn-sm" @click="loadCharts" :disabled="chartLoading">加载图表</button>
                  <button v-if="chartData" class="btn btn-sm" @click="toggleCharts">
                    {{ showCharts ? '收起' : '展开' }}
                  </button>
                </div>
              </div>
              <div v-if="chartLoading" style="padding:12px;text-align:center;color:var(--text2)">加载图表数据中...</div>
              <div v-if="chartData && !chartData.heatmap && !chartData.confidence && !chartData.runSummary" style="padding:12px;text-align:center;color:var(--text2)">
                该诊断运行没有可用的图表数据。
              </div>
              <div v-if="showCharts && chartData" class="chart-grid">
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
          </div>
        </div>

        <div class="run-footer">
          <!-- Answer Bar -->
          <AnswerBar
            :questionData="currentQuestion"
            :runId="runId"
            @answer="onAnswer"
            @skip="onSkipQuestion"
          />

          <!-- Chat Input — fixed at the bottom of the live run layout -->
          <ChatInput
            v-if="viewingRun"
            ref="chatInputRef"
            class="run-input-dock"
            :isRunning="isRunning"
            :terminalStatus="completed ? 'completed' : (failed ? liveStatus : '')"
            :runId="runId"
            @send-message="onSendMessage"
            @resume-with-message="onResumeWithMessage"
          />
        </div>
      </div>
    </template>

    <!-- HITL Approval Dialog -->
    <Teleport to="body">
      <div v-if="hitlPending" class="hitl-overlay">
        <div class="hitl-dialog">
          <div class="hitl-header">
            <span class="hitl-icon">⚠️</span>
            <span class="hitl-title">检测到高风险命令</span>
          </div>
          <div class="hitl-risk" :class="'risk-' + (hitlRisk || 'high')">{{ hitlRisk || 'HIGH' }} 风险</div>
          <div class="hitl-desc">{{ hitlDesc }}</div>
          <pre class="hitl-command">{{ hitlCommand }}</pre>
          <div class="hitl-actions">
            <button class="hitl-btn hitl-deny" @click="respondHITL(false)">拒绝并停止</button>
            <button class="hitl-btn hitl-approve" @click="respondHITL(true)">批准并继续</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue';
import { api } from '../../api/index.js';
import { useDiagnosisRealtimeStore } from '../../stores/diagnosisRealtimeStore.js';
import { getEffectiveRunStatus, getRunStatusLabel } from '../../utils/diagnosisRun.js';
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

const {
  state: realtimeState,
  activeSnapshot,
  connect,
  disconnect,
  subscribeRun,
  hydrateRun,
  refreshCatalog,
  clearActiveRun,
  setRunStatusLocally,
} = useDiagnosisRealtimeStore();

const viewingRun = ref(false);
const sceneName = ref('');
const userQuestion = ref('');
const maxTurns = ref(0);
const reportLanguage = ref('zh');
const started = ref(false);
const elapsed = ref('0:00');
const currentPhase = ref('');
const progressPct = ref(0);
const chartData = ref(null);
const chartLoading = ref(false);
const showCharts = ref(true);
const chatInputRef = ref(null);
const dismissedQuestionId = ref(null);

let elapsedTimer = null;

const snapshot = computed(() => activeSnapshot.value);
const run = computed(() => snapshot.value?.run || null);
const runId = computed(() => run.value?.run_id || props.autoRunId || null);
const runName = computed(() => run.value?.name || '');
const liveStatus = computed(() => getEffectiveRunStatus({
  ...run.value,
  engineStatus: snapshot.value?.liveStatus || run.value?.engineStatus || run.value?.status || 'pending',
}));
const connected = computed(() => realtimeState.wsConnected);
const isHydrating = computed(() => !!snapshot.value?.isHydrating);
const events = computed(() => snapshot.value?.events || []);
const isRunning = computed(() => liveStatus.value === 'running');
const isAwaitingInput = computed(() => liveStatus.value === 'awaiting_input');
const canStop = computed(() => isRunning.value || isAwaitingInput.value);
const completed = computed(() => liveStatus.value === 'completed');
const failed = computed(() => liveStatus.value === 'failed' || liveStatus.value === 'stopped');
const score = computed(() => run.value?.score ?? null);
const verdict = computed(() => run.value?.judge_verdict ?? null);
const reportPath = computed(() => run.value?.report_path ?? null);
const errorMsg = computed(() => run.value?.error_message || '');
const currentQuestion = computed(() => {
  const question = snapshot.value?.currentQuestion || null;
  if (!question) return null;
  return dismissedQuestionId.value === question.questionId ? null : question;
});
const hitlRequest = computed(() => snapshot.value?.hitlRequest || null);
const hitlPending = computed(() => !!hitlRequest.value);
const hitlId = computed(() => hitlRequest.value?.hitlId || null);
const hitlCommand = computed(() => hitlRequest.value?.command || '');
const hitlRisk = computed(() => hitlRequest.value?.riskLevel || '');
const hitlDesc = computed(() => hitlRequest.value?.riskDesc || '');

const turnCount = computed(() => {
  const latest = [...events.value].reverse().find(ev => ev.type === 'stats');
  return latest?.data?.numTurns || 0;
});

const toolCount = computed(() => events.value.filter(ev => ev.type === 'tool_use').length);
const msgCount = computed(() => events.value.filter(ev => ev.type === 'message').length);

const latestToolName = computed(() => {
  const latest = [...events.value].reverse().find(ev => ev.type === 'tool_use');
  return latest?.data?.name || '';
});

const latestTaskStep = computed(() => {
  const latest = [...events.value].reverse().find(ev => ev.type === 'task_progress');
  return latest?.data?.currentStep || latest?.data?.status || '';
});

const statusDotClass = computed(() => {
  if (completed.value) return 'dot-green';
  if (failed.value) return 'dot-red';
  if (isAwaitingInput.value) return 'dot-purple pulse';
  if (isRunning.value) return 'dot-blue pulse';
  return 'dot-gray';
});

const statusLabel = computed(() => {
  if (isHydrating.value) return '同步中';
  if (isRunning.value) return connected.value ? '诊断中' : '重连中';
  if (isAwaitingInput.value) return '等待回答';
  if (liveStatus.value === 'pending') return '待执行';
  return getRunStatusLabel(liveStatus.value);
});

const phaseIcon = computed(() => {
  const p = currentPhase.value;
  if (p.includes('等待用户') || p.includes('等待回答')) return '❓';
  if (p.includes('读取') || p.includes('数据')) return '📂';
  if (p.includes('执行') || p.includes('分析')) return '⚙️';
  if (p.includes('生成') || p.includes('输出')) return '📝';
  if (p.includes('规划')) return '📋';
  if (p.includes('诊断') || p.includes('技能')) return '🔬';
  if (p.includes('探索')) return '🔍';
  if (p.includes('检索') || p.includes('网页')) return '🌐';
  if (p.includes('图') || p.includes('可视化')) return '📊';
  return '⚙️';
});

const verdictClass = computed(() => {
  if (failed.value) return 'banner-fail';
  if (verdict.value === 'PASS' || verdict.value === 'ENDORSED') return 'banner-pass';
  if (verdict.value === 'CONDITIONAL' || verdict.value === 'NEEDS_REPAIR') return 'banner-warn';
  return 'banner-pass';
});

const resultBannerTitle = computed(() => {
  if (completed.value) return '诊断已完成';
  if (liveStatus.value === 'stopped') return '诊断已停止';
  return '诊断失败';
});

const resultBannerIcon = computed(() => {
  if (completed.value) return '✓';
  if (liveStatus.value === 'stopped') return '■';
  return '✗';
});

function detectPhase(toolName) {
  const phases = {
    Read: '读取文件',
    Bash: '执行分析命令',
    Write: '生成输出',
    Edit: '修订报告',
    TodoWrite: '规划步骤',
    Task: '创建任务',
    Skill: '调用诊断技能',
    Glob: '探索目录',
    WebSearch: '检索参考资料',
    WebFetch: '抓取参考资料',
    NotebookEdit: '生成可视化',
  };
  return phases[toolName] || (toolName ? `执行工具：${toolName}` : '');
}

function startElapsed() {
  stopElapsed();
  elapsedTimer = setInterval(() => {
    const start = run.value?.created_at ? new Date(run.value.created_at).getTime() : Date.now();
    const diff = Math.max(0, Math.floor((Date.now() - start) / 1000));
    elapsed.value = `${Math.floor(diff / 60)}:${String(diff % 60).padStart(2, '0')}`;
  }, 1000);
}

function stopElapsed() {
  if (elapsedTimer) clearInterval(elapsedTimer);
  elapsedTimer = null;
}

function formatSize(bytes) {
  if (!bytes) return '0 B';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function toggleCharts() {
  showCharts.value = !showCharts.value;
}

async function fetchChartData(runDir) {
  if (!runDir) return;
  chartLoading.value = true;
  try {
    const dirName = runDir.replace('workspace/diagnostic-runs/', '');
    const res = await fetch(`/api/analysis/chart-data/${encodeURIComponent(dirName)}`);
    const json = await res.json();
    chartData.value = json.success && json.data ? json.data : {};
  } catch (err) {
    console.error('Failed to fetch chart data:', err);
    chartData.value = {};
  } finally {
    chartLoading.value = false;
  }
}

function loadCharts() {
  if (chartLoading.value || !reportPath.value) return;
  const runDir = reportPath.value.split('/').slice(0, -1).join('/');
  fetchChartData(runDir);
}

async function start() {
  if (!props.analysisTarget) return;

  window.scrollTo({ top: 0, behavior: 'auto' });
  viewingRun.value = true;
  started.value = true;
  chartData.value = null;
  showCharts.value = true;
  currentPhase.value = 'Initializing...';
  progressPct.value = 5;

  const target = props.analysisTarget;
  const payload = {
    userQuestion: userQuestion.value,
    sceneName: sceneName.value || undefined,
    reportLanguage: reportLanguage.value,
  };

  if (maxTurns.value > 0) payload.maxTurns = maxTurns.value;
  if (target.mode === 'multi') {
    payload.dataPaths = target.files.map(f => (typeof f === 'string' ? f : f.path));
  } else if (target.mode === 'folder') {
    payload.folderPath = target.path;
  } else {
    payload.dataPath = target.file.path;
  }

  try {
    const data = await api.startDiagnosis(payload);
    emit('started', data.runId);
    setRunStatusLocally(data.runId, {
      name: data.name,
      scene_name: data.name,
      status: 'pending',
      engineStatus: 'pending',
      score: null,
      judge_verdict: null,
      report_path: null,
      error_message: '',
    });
    subscribeRun(data.runId);
    await hydrateRun(data.runId);
    await api.executeDiagnosis(data.runId);
  } catch (err) {
    console.error('Failed to start diagnosis:', err);
  }
}

async function stop() {
  if (!runId.value) return;
  await api.stopDiagnosis(runId.value);
  setRunStatusLocally(runId.value, { status: 'stopped', engineStatus: 'stopped' });
}

async function retryDiagnosis() {
  if (!runId.value) return;
  await api.continueDiagnosis(runId.value);
  markRunContinuing();
}

function respondHITL(approved) {
  if (hitlId.value) api.respondHITL(hitlId.value, approved).catch(() => {});
}

function openReport() {
  if (reportPath.value) emit('view-report', reportPath.value);
}

async function downloadReportMD() {
  if (!reportPath.value) return;
  const parts = reportPath.value.split('/');
  const currentRunName = parts[parts.length - 2] || '';
  if (!currentRunName) return;
  try {
    const data = await api.getReport(currentRunName);
    if (!data?.content) return;
    const blob = new Blob([data.content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `diagnostic-report-${currentRunName}.md`;
    a.click();
    URL.revokeObjectURL(url);
  } catch (err) {
    console.error('Failed to download report:', err);
  }
}

async function onAnswer({ questionId, toolUseId, answers }) {
  if (!runId.value) return;
  dismissedQuestionId.value = questionId || currentQuestion.value?.questionId || null;
  await api.submitAnswer(runId.value, questionId, toolUseId, answers);
}

function onSkipQuestion() {
  dismissedQuestionId.value = currentQuestion.value?.questionId || null;
}

async function onSendMessage(message) {
  if (!runId.value) return;
  await api.sendChat(runId.value, message);
}

async function onResumeWithMessage(message) {
  if (!runId.value) return;
  await api.sendChat(runId.value, message);
  subscribeRun(runId.value);
}

function markRunContinuing() {
  if (!runId.value) return;
  setRunStatusLocally(runId.value, {
    status: 'running',
    engineStatus: 'running',
    score: null,
    judge_verdict: null,
    report_path: null,
    error_message: '',
  });
  subscribeRun(runId.value);
}

async function openRun(rid) {
  window.scrollTo({ top: 0, behavior: 'auto' });
  viewingRun.value = true;
  started.value = true;
  chartData.value = null;
  showCharts.value = true;
  await hydrateRun(rid);
  subscribeRun(rid);
}

function goBack() {
  clearActiveRun();
  viewingRun.value = false;
  started.value = false;
  currentPhase.value = '';
  progressPct.value = 0;
  chartData.value = null;
  stopElapsed();
}

function onViewReport(path) {
  emit('view-report', path);
}

function goToData() {
  emit('go-data');
}

watch(() => props.analysisTarget, (target) => {
  viewingRun.value = false;
  started.value = false;
  chartData.value = null;
  currentPhase.value = '';
  progressPct.value = 0;
  clearActiveRun();
  if (target?.mode === 'file' && !sceneName.value) {
    sceneName.value = target.file.name.replace(/\.[^.]+$/, '').replace(/[^a-zA-Z0-9]/g, '_');
  } else if (target?.mode === 'folder' && !sceneName.value) {
    sceneName.value = target.name || '';
  }
}, { immediate: true });

watch(() => props.autoRunId, async (newRunId) => {
  if (!newRunId) return;
  viewingRun.value = true;
  started.value = true;
  await hydrateRun(newRunId);
  subscribeRun(newRunId);
}, { immediate: true });

watch(events, (nextEvents) => {
  const latestQuestion = [...nextEvents].reverse().find(ev => ev.type === 'question');
  const latestQuestionResult = [...nextEvents].reverse().find(ev => ev.type === 'question_result');
  const latestComplete = [...nextEvents].reverse().find(ev => ev.type === 'complete');
  const latestError = [...nextEvents].reverse().find(ev => ev.type === 'error');
  const phaseFromStep = latestTaskStep.value;
  const phaseFromTool = detectPhase(latestToolName.value);

  if (latestQuestion && latestQuestion.data?.questionId !== dismissedQuestionId.value) {
    dismissedQuestionId.value = null;
  }
  if (latestQuestionResult) {
    dismissedQuestionId.value = null;
  }

  if (latestComplete || latestError) {
    currentPhase.value = '';
    progressPct.value = 100;
    if (reportPath.value && chartData.value === null) {
      const runDir = reportPath.value.split('/').slice(0, -1).join('/');
      fetchChartData(runDir);
    }
  } else if (phaseFromStep) {
    currentPhase.value = phaseFromStep;
    progressPct.value = Math.min(92, Math.max(progressPct.value, 65));
  } else if (phaseFromTool) {
    currentPhase.value = phaseFromTool;
    progressPct.value = Math.min(90, progressPct.value + 3);
  } else if (isAwaitingInput.value) {
    currentPhase.value = '等待用户回答...';
    progressPct.value = Math.max(progressPct.value, 75);
  } else if (isHydrating.value) {
    currentPhase.value = '同步实时状态中...';
    progressPct.value = Math.max(progressPct.value, 15);
  } else if (isRunning.value) {
    currentPhase.value = '等待下一步分析执行...';
    progressPct.value = Math.min(88, Math.max(progressPct.value, 20));
  }

  const questionStillPending = latestQuestion
    && (!latestQuestionResult || (latestQuestionResult._seq ?? -1) < (latestQuestion._seq ?? -1))
    && !latestComplete
    && !latestError
    && isAwaitingInput.value;

  if (questionStillPending) {
    currentPhase.value = '等待用户回答...';
    progressPct.value = Math.max(progressPct.value, 75);
  }
}, { deep: true, immediate: true });

watch([isRunning, isAwaitingInput, () => run.value?.created_at], ([running, awaiting]) => {
  if (running || awaiting) startElapsed();
  else stopElapsed();
}, { immediate: true });

onMounted(() => {
  // connect/disconnect is managed centrally by App.vue
  // Only refresh catalog data when entering this page
  refreshCatalog();
});

onUnmounted(() => {
  stopElapsed();
});
</script>

<style scoped>
.diagnosis-view {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-height: 0;
  height: 100%;
  overflow-y: auto;
  overflow-x: hidden;
  padding-right: 2px;
}

.diagnosis-view-run {
  height: 100%;
  flex: 1;
  overflow: hidden;
  padding: 0;
}

.run-layout {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  gap: 12px;
  overflow: hidden;
}

.run-header {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex-shrink: 0;
}

.run-body {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  gap: 8px;
  overflow: hidden;
}

.run-message-region {
  flex: 1;
  min-height: 0;
  display: flex;
  overflow: hidden;
}

.run-message-region :deep(.message-stream) {
  flex: 1;
  min-height: 0;
}

.run-support-stack {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex-shrink: 0;
}

.run-footer {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex-shrink: 0;
  padding-bottom: 12px;
}

.run-input-dock {
  margin-top: 0;
  flex-shrink: 0;
}

/* Nav */
.dv-nav {
  display: flex; align-items: center; gap: 12px;
  margin-bottom: 2px;
}
.dv-nav-title { font-size: 14px; font-weight: 600; color: var(--text); }
.dv-nav-id { font-size: 11px; color: var(--text2); font-family: monospace; background: var(--surface2); padding: 2px 8px; border-radius: 4px; }

/* ========== Data Source ========== */
.ds-card {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 18px; margin-bottom: 0;
  box-shadow: var(--shadow-sm);
}
.ds-card-header { display: flex; align-items: center; gap: 12px; }
.ds-icon { font-size: 22px; }
.ds-title { font-size: 14px; font-weight: 600; }
.ds-sub { font-size: 12px; color: var(--text2); margin-top: 2px; font-family: monospace; }

/* ========== Control Bar ========== */
.ctrl-bar { margin-bottom: 2px; }
.ctrl-form {
  display: flex; flex-direction: column; gap: 10px;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 18px;
  box-shadow: var(--shadow-sm);
}
.ctrl-input, .ctrl-textarea {
  background: var(--surface-soft); border: 1px solid var(--border);
  border-radius: 14px; padding: 10px 13px; color: var(--text);
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
  border-radius: var(--radius); padding: 14px 18px; margin-bottom: 0;
  box-shadow: var(--shadow-sm);
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
  padding: 6px 14px; background: color-mix(in srgb, var(--red) 10%, transparent); color: var(--red);
  border: 1px solid color-mix(in srgb, var(--red) 28%, transparent); border-radius: 10px; font-size: 12px;
  font-weight: 600; cursor: pointer; transition: all .15s;
}
.stop-btn:hover { background: color-mix(in srgb, var(--red) 16%, transparent); }

/* ========== Phase Bar ========== */
.phase-bar {
  display: flex; align-items: center; gap: 10px;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 12px 16px; margin-bottom: 0;
  box-shadow: var(--shadow-sm);
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
  box-shadow: var(--shadow-sm);
}
.banner-pass { background: color-mix(in srgb, var(--green) 8%, var(--surface)); border: 1px solid color-mix(in srgb, var(--green) 22%, var(--border)); }
.banner-warn { background: color-mix(in srgb, var(--yellow) 8%, var(--surface)); border: 1px solid color-mix(in srgb, var(--yellow) 22%, var(--border)); }
.banner-fail { background: color-mix(in srgb, var(--red) 8%, var(--surface)); border: 1px solid color-mix(in srgb, var(--red) 22%, var(--border)); }
.rb-icon {
  width: 40px; height: 40px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 20px; font-weight: 700;
}
.banner-pass .rb-icon { background: color-mix(in srgb, var(--green) 16%, transparent); color: var(--green); }
.banner-warn .rb-icon { background: color-mix(in srgb, var(--yellow) 16%, transparent); color: var(--yellow); }
.banner-fail .rb-icon { background: color-mix(in srgb, var(--red) 16%, transparent); color: var(--red); }
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
.rb-btn-md { background: color-mix(in srgb, var(--accent) 10%, transparent); color: var(--accent); border: 1px solid color-mix(in srgb, var(--accent) 26%, transparent); }
.rb-btn-md:hover { background: color-mix(in srgb, var(--accent) 16%, transparent); }
.rb-btn-retry { background: color-mix(in srgb, var(--red) 10%, transparent); color: var(--red); border: 1px solid color-mix(in srgb, var(--red) 26%, transparent); }
.rb-btn-retry:hover { background: color-mix(in srgb, var(--red) 16%, transparent); }
.rb-hint { font-size: 12px; color: var(--text2); margin-top: 8px; font-style: italic; }

/* ========== HITL Overlay ========== */
.hitl-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,.45);
  display: flex; align-items: center; justify-content: center;
  z-index: 1000; backdrop-filter: blur(4px);
}
.hitl-dialog {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 24px;
  max-width: 560px; width: 90%; box-shadow: var(--shadow-lg);
}
.hitl-header { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
.hitl-icon { font-size: 28px; }
.hitl-title { font-size: 16px; font-weight: 700; }
.hitl-risk {
  display: inline-block; padding: 3px 10px; border-radius: 4px;
  font-size: 11px; font-weight: 700; letter-spacing: .5px; margin-bottom: 12px;
}
.risk-HIGH, .risk-SERIOUS { background: color-mix(in srgb, var(--red) 14%, transparent); color: var(--red); }
.risk-MEDIUM, .risk-WARN { background: color-mix(in srgb, var(--yellow) 14%, transparent); color: var(--yellow); }
.hitl-desc { font-size: 13px; color: var(--text); margin-bottom: 12px; line-height: 1.5; }
.hitl-dialog pre {
  background: var(--surface-soft); color: var(--red); padding: 12px; border-radius: 10px;
  font-size: 12px; font-family: 'SF Mono', monospace; white-space: pre-wrap;
  word-break: break-all; margin-bottom: 20px; border: 1px solid color-mix(in srgb, var(--red) 24%, var(--border));
}
.hitl-actions { display: flex; gap: 12px; justify-content: flex-end; }
.hitl-btn {
  padding: 10px 24px; border: none; border-radius: var(--radius);
  font-size: 14px; font-weight: 600; cursor: pointer; transition: all .15s;
}
.hitl-deny { background: color-mix(in srgb, var(--red) 12%, transparent); color: var(--red); border: 1px solid color-mix(in srgb, var(--red) 50%, var(--border)); }
.hitl-deny:hover { background: color-mix(in srgb, var(--red) 20%, transparent); }
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

@media (max-width: 900px) {
  .diagnosis-view-run {
    padding: 0;
  }

  .status-bar {
    flex-wrap: wrap;
    justify-content: space-between;
  }

  .status-metrics {
    order: 3;
    width: 100%;
    justify-content: flex-start;
    flex-wrap: wrap;
    gap: 12px;
  }

  .phase-bar {
    flex-wrap: wrap;
  }

  .phase-text {
    white-space: normal;
  }

  .chart-grid {
    grid-template-columns: 1fr;
  }

  .chart-cell-half {
    grid-column: 1 / -1;
  }
}
</style>
