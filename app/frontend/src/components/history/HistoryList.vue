<template>
  <div class="history-list">
    <div class="toolbar">
      <div class="toolbar-left">
        <h3>诊断历史</h3>
        <span class="count-badge" v-if="runs.length">{{ runs.length }} 条</span>
      </div>
      <div class="toolbar-right">
        <button class="btn" @click="loadHistory" :disabled="loading">刷新</button>
        <button class="btn btn-danger btn-sm" @click="clearHistory" :disabled="!runs.length || loading">
          清空记录
        </button>
      </div>
    </div>

    <div v-if="loading" class="empty-state">
      <div class="spinner" style="width:24px;height:24px;border-width:2px;"></div>
      <p>正在加载历史记录...</p>
    </div>

    <div v-else-if="runs.length === 0" class="empty-state">
      <p>当前还没有诊断记录。请先在诊断页发起一次分析。</p>
    </div>

    <div v-else class="history-table-wrapper">
      <table class="history-table">
        <thead>
          <tr>
            <th>任务名</th>
            <th>场景</th>
            <th>数据文件</th>
            <th>问题</th>
            <th>状态</th>
            <th>评分</th>
            <th>结论</th>
            <th>创建时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="run in runs"
            :key="run.run_id"
            :class="['history-row', `row-${getEffectiveRunStatus(run)}`]"
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
              <span :class="['badge', getRunStatusBadgeClass(run)]">{{ getRunStatusLabel(run) }}</span>
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
              >会话</button>
              <button
                v-if="getEffectiveRunStatus(run) === 'completed' && run.report_path"
                class="btn btn-sm btn-primary"
                @click="viewReport(run)"
              >报告</button>
              <button
                v-if="getEffectiveRunStatus(run) === 'failed' || getEffectiveRunStatus(run) === 'stopped'"
                class="btn btn-sm btn-continue"
                @click="continueRun(run)"
                :disabled="continuingRun === run.run_id"
              >
                <template v-if="continuingRun === run.run_id">
                  <span class="spinner-sm"></span> 继续中...
                </template>
                <template v-else>
                  继续诊断
                </template>
              </button>
              <button class="btn btn-sm" @click="toggleDetail(run.run_id)">
                {{ expandedRun === run.run_id ? '收起' : '详情' }}
              </button>
              <button
                class="btn btn-sm btn-danger"
                @click="deleteRun(run.run_id)"
              >删除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Expanded detail panel -->
    <div v-if="expandedRun && detailRun" class="card detail-panel">
      <div class="card-title">
        运行详情：{{ detailRun.name }}
        <button class="btn btn-sm" @click="expandedRun = null" style="margin-left:auto">关闭</button>
      </div>
      <div class="detail-grid">
        <div class="detail-item">
          <span class="detail-label">运行 ID</span>
          <span class="detail-value">{{ detailRun.run_id }}</span>
        </div>
        <div class="detail-item">
          <span class="detail-label">状态</span>
          <span :class="['badge', getRunStatusBadgeClass(detailRun)]">{{ getRunStatusLabel(detailRun) }}</span>
        </div>
        <div class="detail-item">
          <span class="detail-label">Model</span>
          <span class="detail-value">{{ detailRun.model }}</span>
        </div>
        <div class="detail-item">
          <span class="detail-label">最大轮次</span>
          <span class="detail-value">{{ detailRun.max_turns }}</span>
        </div>
        <div class="detail-item">
          <span class="detail-label">数据路径</span>
          <span class="detail-value path">{{ detailRun.data_path }}</span>
        </div>
        <div class="detail-item">
          <span class="detail-label">工作区</span>
          <span class="detail-value path">{{ detailRun.workspace_path || '--' }}</span>
        </div>
        <div class="detail-item">
          <span class="detail-label">创建时间</span>
          <span class="detail-value">{{ formatDate(detailRun.created_at) }}</span>
        </div>
        <div class="detail-item">
          <span class="detail-label">完成时间</span>
          <span class="detail-value">{{ detailRun.completed_at ? formatDate(detailRun.completed_at) : '--' }}</span>
        </div>
        <div class="detail-item" v-if="detailRun.user_question">
          <span class="detail-label">诊断问题</span>
          <span class="detail-value">{{ detailRun.user_question }}</span>
        </div>
        <div class="detail-item" v-if="detailRun.error_message">
          <span class="detail-label">错误</span>
          <span class="detail-value error-text">{{ detailRun.error_message }}</span>
        </div>
      </div>

      <!-- Logs -->
      <div v-if="logs.length > 0" class="logs-section">
        <div class="card-title" style="margin-top:16px">诊断日志（{{ logs.length }} 条）</div>
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
          <button class="btn btn-sm" @click="logPage--" :disabled="logPage <= 1">上一页</button>
          <span class="page-info">{{ logPage }} / {{ maxLogPage }}</span>
          <button class="btn btn-sm" @click="logPage++" :disabled="logPage >= maxLogPage">下一页</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { api } from '../../api/index.js';
import {
  getEffectiveRunStatus,
  getRunStatusBadgeClass,
  getRunStatusLabel,
  normalizeRunSummary,
} from '../../utils/diagnosisRun.js';

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
    runs.value = (await api.getRuns()).map(normalizeRunSummary);
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
    detailRun.value = normalizeRunSummary(data);
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
    alert('继续诊断失败：' + err.message);
  } finally {
    continuingRun.value = null;
  }
}

async function deleteRun(runId) {
  if (!confirm(`确认删除运行 ${runId} 吗？这只会删除数据库记录，不会删除工作区文件。`)) return;
  try {
    await api.deleteRun(runId);
    if (expandedRun.value === runId) {
      expandedRun.value = null;
      detailRun.value = null;
      logs.value = [];
    }
    await loadHistory();
  } catch (err) {
    alert('删除运行失败：' + err.message);
  }
}

async function clearHistory() {
  if (!confirm('确认清空全部历史记录吗？工作区文件不会被删除。')) return;
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
.history-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 100%;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding: 18px 20px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: linear-gradient(180deg, color-mix(in srgb, var(--surface-strong) 94%, transparent), color-mix(in srgb, var(--surface) 98%, transparent));
  box-shadow: var(--shadow-sm);
}

.toolbar-left { display: flex; align-items: center; gap: 8px; }
.toolbar-left h3 { font-size: 16px; font-weight: 600; }

.count-badge {
  font-size: 12px;
  color: var(--text2);
  background: var(--surface-soft);
  padding: 2px 10px;
  border-radius: 10px;
  border: 1px solid var(--border);
}

.toolbar-right { display: flex; gap: 8px; }

.history-table-wrapper {
  overflow-x: auto;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: color-mix(in srgb, var(--surface) 98%, transparent);
  box-shadow: var(--shadow-sm);
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

.row-running { background: color-mix(in srgb, var(--accent) 6%, transparent); }
.row-failed { background: color-mix(in srgb, var(--red) 5%, transparent); }

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
  background: var(--surface-soft);
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

.log-line:hover { background: color-mix(in srgb, var(--accent) 8%, transparent); border-radius: 6px; }

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

.tag-text { background: color-mix(in srgb, var(--purple) 14%, transparent); color: var(--purple); }
.tag-tool_use { background: color-mix(in srgb, var(--accent) 14%, transparent); color: var(--accent); }

.log-content {
  color: var(--text);
  white-space: pre-wrap;
  word-break: break-all;
}

.btn-continue {
  background: color-mix(in srgb, var(--accent) 10%, transparent);
  border-color: var(--accent);
  color: var(--accent);
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.btn-continue:hover {
  background: color-mix(in srgb, var(--accent) 18%, transparent);
}

.btn-session {
  background: color-mix(in srgb, var(--purple) 10%, transparent);
  border-color: var(--purple);
  color: var(--purple);
}
.btn-session:hover {
  background: color-mix(in srgb, var(--purple) 18%, transparent);
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
