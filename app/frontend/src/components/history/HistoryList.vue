<template>
  <div class="history-list">
    <div class="toolbar">
      <div class="toolbar-left">
        <h3>Diagnosis History</h3>
        <span class="count-badge" v-if="runs.length">{{ runs.length }} runs</span>
      </div>
      <div class="toolbar-right">
        <button class="btn" @click="loadHistory" :disabled="loading">Refresh</button>
        <button class="btn btn-danger btn-sm" @click="clearHistory" :disabled="!runs.length || loading">
          Clear All
        </button>
      </div>
    </div>

    <div v-if="loading" class="empty-state">
      <div class="spinner" style="width:24px;height:24px;border-width:2px;"></div>
      <p>Loading history...</p>
    </div>

    <div v-else-if="runs.length === 0" class="empty-state">
      <p>No diagnosis runs yet. Upload data and start an analysis from the Diagnose tab.</p>
    </div>

    <div v-else class="history-table-wrapper">
      <table class="history-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Scene</th>
            <th>Data File</th>
            <th>Question</th>
            <th>Status</th>
            <th>Score</th>
            <th>Verdict</th>
            <th>Created</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="run in runs"
            :key="run.run_id"
            :class="['history-row', `row-${run.status}`]"
            @click="toggleDetail(run.run_id)"
          >
            <td class="cell-name">{{ run.name }}</td>
            <td>{{ run.scene_name }}</td>
            <td class="cell-path">{{ run.data_path }}</td>
            <td class="cell-question">
              <span v-if="run.user_question" :title="run.user_question">
                {{ truncate(run.user_question, 40) }}
              </span>
              <span v-else class="text-muted">--</span>
            </td>
            <td>
              <span :class="['badge', statusBadge(run.status)]">{{ run.status }}</span>
            </td>
            <td>
              <span v-if="run.score != null" :class="['score', scoreClass(run.score)]">
                {{ run.score }}
              </span>
              <span v-else class="text-muted">--</span>
            </td>
            <td>
              <span v-if="run.judge_verdict" :class="['badge', verdictBadge(run.judge_verdict)]">
                {{ run.judge_verdict }}
              </span>
              <span v-else class="text-muted">--</span>
            </td>
            <td class="cell-date">{{ formatDate(run.created_at) }}</td>
            <td class="cell-actions" @click.stop>
              <button
                v-if="run.session_id"
                class="btn btn-sm btn-session"
                @click="viewSession(run)"
              >Session</button>
              <button
                v-if="run.status === 'completed' && run.report_path"
                class="btn btn-sm btn-primary"
                @click="viewReport(run)"
              >Report</button>
              <button
                v-if="run.status === 'failed' || run.status === 'stopped'"
                class="btn btn-sm btn-continue"
                @click="continueRun(run)"
                :disabled="continuingRun === run.run_id"
              >
                <template v-if="continuingRun === run.run_id">
                  <span class="spinner-sm"></span> Retrying...
                </template>
                <template v-else>
                  Continue
                </template>
              </button>
              <button class="btn btn-sm" @click="toggleDetail(run.run_id)">
                {{ expandedRun === run.run_id ? 'Hide' : 'Details' }}
              </button>
              <button
                class="btn btn-sm btn-danger"
                @click="deleteRun(run.run_id)"
              >Del</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Expanded detail panel -->
    <div v-if="expandedRun && detailRun" class="card detail-panel">
      <div class="card-title">
        Run Detail: {{ detailRun.name }}
        <button class="btn btn-sm" @click="expandedRun = null" style="margin-left:auto">Close</button>
      </div>
      <div class="detail-grid">
        <div class="detail-item">
          <span class="detail-label">Run ID</span>
          <span class="detail-value">{{ detailRun.run_id }}</span>
        </div>
        <div class="detail-item">
          <span class="detail-label">Status</span>
          <span :class="['badge', statusBadge(detailRun.status)]">{{ detailRun.status }}</span>
        </div>
        <div class="detail-item">
          <span class="detail-label">Model</span>
          <span class="detail-value">{{ detailRun.model }}</span>
        </div>
        <div class="detail-item">
          <span class="detail-label">Max Turns</span>
          <span class="detail-value">{{ detailRun.max_turns }}</span>
        </div>
        <div class="detail-item">
          <span class="detail-label">Data Path</span>
          <span class="detail-value path">{{ detailRun.data_path }}</span>
        </div>
        <div class="detail-item">
          <span class="detail-label">Workspace</span>
          <span class="detail-value path">{{ detailRun.workspace_path || '--' }}</span>
        </div>
        <div class="detail-item">
          <span class="detail-label">Created</span>
          <span class="detail-value">{{ formatDate(detailRun.created_at) }}</span>
        </div>
        <div class="detail-item">
          <span class="detail-label">Completed</span>
          <span class="detail-value">{{ detailRun.completed_at ? formatDate(detailRun.completed_at) : '--' }}</span>
        </div>
        <div class="detail-item" v-if="detailRun.user_question">
          <span class="detail-label">Question</span>
          <span class="detail-value">{{ detailRun.user_question }}</span>
        </div>
        <div class="detail-item" v-if="detailRun.error_message">
          <span class="detail-label">Error</span>
          <span class="detail-value error-text">{{ detailRun.error_message }}</span>
        </div>
      </div>

      <!-- Logs -->
      <div v-if="logs.length > 0" class="logs-section">
        <div class="card-title" style="margin-top:16px">Diagnosis Logs ({{ logs.length }} entries)</div>
        <div class="log-stream">
          <div
            v-for="(log, i) in paginatedLogs"
            :key="i"
            :class="['log-line', `log-${log.role}`]"
          >
            <span class="log-time">{{ log.created_at?.slice(11, 19) || '' }}</span>
            <span :class="['log-tag', `tag-${log.message_type}`]">
              {{ log.message_type === 'tool_use' ? 'TOOL' : log.role.toUpperCase() }}
            </span>
            <span class="log-content">{{ truncate(log.content, 300) }}</span>
          </div>
        </div>
        <div v-if="logs.length > 50" class="log-pagination">
          <button class="btn btn-sm" @click="logPage--" :disabled="logPage <= 1">Prev</button>
          <span class="page-info">{{ logPage }} / {{ maxLogPage }}</span>
          <button class="btn btn-sm" @click="logPage++" :disabled="logPage >= maxLogPage">Next</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { api } from '../../api/index.js';

const emit = defineEmits(['open-report', 'continue-run']);

const runs = ref([]);
const loading = ref(false);
const continuingRun = ref(null);
const expandedRun = ref(null);
const detailRun = ref(null);
const logs = ref([]);
const logPage = ref(1);
const pageSize = 50;

onMounted(() => loadHistory());

async function loadHistory() {
  loading.value = true;
  try {
    runs.value = await api.getRuns();
  } catch (err) {
    console.error('Failed to load history:', err);
  } finally {
    loading.value = false;
  }
}

async function toggleDetail(runId) {
  if (expandedRun.value === runId) {
    expandedRun.value = null;
    detailRun.value = null;
    logs.value = [];
    return;
  }

  expandedRun.value = runId;
  logPage.value = 1;
  try {
    const data = await api.getRunWithLogs(runId);
    detailRun.value = data;
    logs.value = data.logs || [];
  } catch {
    detailRun.value = runs.value.find(r => r.run_id === runId);
    logs.value = [];
  }
}

function viewReport(run) {
  emit('open-report', run.report_path);
}

function viewSession(run) {
  emit('continue-run', run.run_id);
}

async function continueRun(run) {
  if (continuingRun.value) return;
  continuingRun.value = run.run_id;
  try {
    await api.continueDiagnosis(run.run_id);
    emit('continue-run', run.run_id);
    await loadHistory();
  } catch (err) {
    alert('Failed to continue: ' + err.message);
  } finally {
    continuingRun.value = null;
  }
}

async function deleteRun(runId) {
  if (!confirm(`Delete run ${runId}? This only deletes the database record, not the workspace files.`)) return;
  try {
    await api.deleteRun(runId);
    if (expandedRun.value === runId) {
      expandedRun.value = null;
      detailRun.value = null;
      logs.value = [];
    }
    await loadHistory();
  } catch (err) {
    alert('Failed to delete run: ' + err.message);
  }
}

async function clearHistory() {
  if (!confirm('Delete ALL history records? Workspace files will NOT be affected.')) return;
  for (const run of runs.value) {
    try { await api.deleteRun(run.run_id); } catch {}
  }
  expandedRun.value = null;
  detailRun.value = null;
  logs.value = [];
  await loadHistory();
}

function truncate(text, max) {
  if (!text) return '';
  if (text.length <= max) return text;
  return text.slice(0, max) + '...';
}

function formatDate(dateStr) {
  if (!dateStr) return '--';
  try {
    return new Date(dateStr).toLocaleString();
  } catch {
    return dateStr;
  }
}

function statusBadge(status) {
  switch (status) {
    case 'completed': return 'badge-green';
    case 'running': return 'badge-blue';
    case 'pending': return 'badge-yellow';
    case 'failed': return 'badge-red';
    case 'stopped': return 'badge-purple';
    default: return '';
  }
}

function scoreClass(score) {
  if (score >= 90) return 'score-high';
  if (score >= 70) return 'score-mid';
  return 'score-low';
}

function verdictBadge(verdict) {
  if (verdict === 'PASS' || verdict === 'ENDORSED') return 'badge-green';
  if (verdict === 'CONDITIONAL') return 'badge-yellow';
  return 'badge-red';
}

const maxLogPage = computed(() => Math.max(1, Math.ceil(logs.value.length / pageSize)));

const paginatedLogs = computed(() => {
  const start = (logPage.value - 1) * pageSize;
  return logs.value.slice(start, start + pageSize);
});
</script>

<style scoped>
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.toolbar-left { display: flex; align-items: center; gap: 8px; }
.toolbar-left h3 { font-size: 16px; font-weight: 600; }

.count-badge {
  font-size: 12px;
  color: var(--text2);
  background: var(--surface2);
  padding: 2px 10px;
  border-radius: 10px;
}

.toolbar-right { display: flex; gap: 8px; }

.history-table-wrapper {
  overflow-x: auto;
  border: 1px solid var(--border);
  border-radius: var(--radius);
}

.history-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.history-table thead {
  background: var(--surface);
  position: sticky;
  top: 0;
  z-index: 1;
}

.history-table th {
  padding: 10px 12px;
  text-align: left;
  font-weight: 600;
  font-size: 12px;
  color: var(--text2);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-bottom: 2px solid var(--border);
  white-space: nowrap;
}

.history-table td {
  padding: 10px 12px;
  border-bottom: 1px solid var(--border);
  vertical-align: middle;
}

.history-row {
  cursor: pointer;
  transition: background 0.1s;
}

.history-row:hover { background: rgba(88, 166, 255, 0.03); }

.row-running { background: rgba(88, 166, 255, 0.04); }
.row-failed { background: rgba(248, 81, 73, 0.03); }

.cell-name { font-weight: 600; font-size: 12px; max-width: 160px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cell-path { font-family: 'SF Mono', 'Fira Code', monospace; font-size: 11px; color: var(--accent); max-width: 140px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cell-question { max-width: 200px; }
.cell-date { font-size: 11px; color: var(--text2); white-space: nowrap; }
.cell-actions { display: flex; gap: 4px; }

.text-muted { color: var(--text2); font-size: 12px; }

.score { font-weight: 700; font-size: 13px; }
.score-high { color: var(--green); }
.score-mid { color: var(--yellow); }
.score-low { color: var(--red); }

.detail-panel { margin-top: 16px; }

.detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 8px;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.detail-label {
  font-size: 11px;
  color: var(--text2);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.detail-value {
  font-size: 13px;
}

.detail-value.path {
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: 11px;
  color: var(--accent);
  word-break: break-all;
}

.error-text { color: var(--red); }

.logs-section { margin-top: 8px; }

.log-stream {
  background: var(--surface2);
  border-radius: var(--radius);
  padding: 8px;
  max-height: 400px;
  overflow-y: auto;
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: 11px;
  line-height: 1.6;
}

.log-line {
  display: flex;
  gap: 8px;
  padding: 3px 4px;
  align-items: flex-start;
}

.log-line:hover { background: rgba(88, 166, 255, 0.05); border-radius: 2px; }

.log-time {
  color: var(--text2);
  flex-shrink: 0;
  font-size: 10px;
}

.log-tag {
  display: inline-block;
  padding: 0 4px;
  border-radius: 3px;
  font-size: 9px;
  font-weight: 700;
  flex-shrink: 0;
  line-height: 16px;
}

.tag-text { background: rgba(188, 140, 255, 0.15); color: var(--purple); }
.tag-tool_use { background: rgba(88, 166, 255, 0.15); color: var(--accent); }

.log-content {
  color: var(--text);
  white-space: pre-wrap;
  word-break: break-all;
}

.btn-continue {
  background: rgba(88, 166, 255, 0.1);
  border-color: var(--accent);
  color: var(--accent);
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.btn-continue:hover {
  background: rgba(88, 166, 255, 0.2);
}

.btn-session {
  background: rgba(163, 113, 247, 0.1);
  border-color: #a371f7;
  color: #a371f7;
}
.btn-session:hover {
  background: rgba(163, 113, 247, 0.2);
}

.spinner-sm {
  display: inline-block;
  width: 12px;
  height: 12px;
  border: 2px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.log-pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-top: 8px;
  padding: 8px;
}

.page-info {
  font-size: 12px;
  color: var(--text2);
}
</style>
