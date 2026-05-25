<template>
  <div class="task-list">
    <!-- New Task Button -->
    <div class="tl-toolbar">
      <span class="tl-title">All Diagnosis Tasks</span>
      <button class="btn btn-sm" @click="$emit('new-task')">+ New Task</button>
    </div>

    <!-- Loading -->
    <div v-if="loading && runs.length === 0" class="empty-state">
      <div class="spinner" style="margin:0 auto 8px"></div>
      <p>Loading tasks...</p>
    </div>

    <!-- Empty -->
    <div v-else-if="!loading && runs.length === 0" class="empty-state">
      <p style="font-size:28px;margin-bottom:12px;">🔬</p>
      <p>No diagnosis tasks yet</p>
      <p style="font-size:12px;color:var(--text2);margin-top:4px;">
        Select a data file from the Data tab to start a new diagnosis
      </p>
    </div>

    <!-- Runs grouped: running first, then past -->
    <template v-else>
      <!-- Running Tasks -->
      <template v-if="runningRuns.length > 0">
        <div class="tl-group-label">
          <span class="status-dot dot-blue pulse" style="display:inline-block;width:6px;height:6px;margin-right:6px;"></span>
          Running ({{ runningRuns.length }})
        </div>
        <div
          v-for="run in runningRuns" :key="run.run_id"
          class="tl-run-card tl-run-running"
          @click="$emit('view-run', run.run_id)"
        >
          <div class="run-main">
            <div class="run-header">
              <span class="run-scene">{{ run.scene_name }}</span>
              <span class="badge badge-blue">running</span>
            </div>
            <div class="run-id">#{{ run.run_id }}</div>
            <div class="run-meta">
              <span>{{ formatTime(run.created_at) }}</span>
              <span v-if="run.engineStatus === 'running'">In progress...</span>
            </div>
            <div class="run-question" v-if="run.user_question">{{ run.user_question.slice(0, 120) }}{{ run.user_question.length > 120 ? '...' : '' }}</div>
          </div>
          <div class="run-arrow">→</div>
        </div>
      </template>

      <!-- Past Tasks -->
      <template v-if="pastRuns.length > 0">
        <div class="tl-group-label">
          Past Tasks ({{ pastRuns.length }})
        </div>
        <div
          v-for="run in pastRuns" :key="run.run_id"
          class="tl-run-card tl-run-past"
          @click="onPastRunClick(run)"
        >
          <div class="run-main">
            <div class="run-header">
              <span class="run-scene">{{ run.scene_name }}</span>
              <span :class="['badge', statusBadge(run.status)]">{{ run.status }}</span>
            </div>
            <div class="run-id">#{{ run.run_id }}</div>
            <div class="run-meta">
              <span>{{ formatTime(run.created_at) }}</span>
              <span v-if="run.score != null">Score: {{ run.score }}/100</span>
              <span v-if="run.judge_verdict" :class="verdictColor(run.judge_verdict)">{{ run.judge_verdict }}</span>
              <span v-if="run.error_message" class="run-error-msg">{{ run.error_message.slice(0, 80) }}</span>
            </div>
          </div>
          <div class="run-arrow">→</div>
        </div>
      </template>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onUnmounted } from 'vue';
import { api } from '../api.js';

const emit = defineEmits(['view-run', 'view-report', 'new-task']);
const runs = ref([]);
const loading = ref(true);
let pollTimer = null;

async function fetchRuns() {
  try {
    const data = await api.listRuns();
    runs.value = data || [];
  } catch {
    // keep existing data on error
  } finally {
    loading.value = false;
  }
}

const runningRuns = computed(() =>
  runs.value.filter(r => r.status === 'running' || r.engineStatus === 'running')
);

const pastRuns = computed(() =>
  runs.value.filter(r => r.status !== 'running' && r.engineStatus !== 'running')
);

function onPastRunClick(run) {
  if (run.report_path) {
    emit('view-report', run.report_path);
  } else {
    // Always allow viewing run details (completed without report, failed, stopped, pending)
    emit('view-run', run.run_id);
  }
}

function statusBadge(status) {
  if (status === 'completed') return 'badge-green';
  if (status === 'failed') return 'badge-red';
  if (status === 'stopped') return 'badge-yellow';
  return 'badge-blue';
}

function verdictColor(v) {
  if (v === 'PASS' || v === 'ENDORSED') return 'text-green';
  if (v === 'CONDITIONAL' || v === 'NEEDS_REPAIR') return 'text-yellow';
  return 'text-red';
}

function formatTime(ts) {
  if (!ts) return '';
  try {
    const d = new Date(ts + 'Z');
    const now = new Date();
    const diff = now - d;
    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    return d.toLocaleDateString();
  } catch {
    return ts;
  }
}

// Initial fetch
fetchRuns();

// Poll every 10s
pollTimer = setInterval(fetchRuns, 10000);

onUnmounted(() => {
  clearInterval(pollTimer);
});
</script>

<style scoped>
.task-list { display: flex; flex-direction: column; gap: 8px; }

.tl-toolbar {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 8px;
}

.tl-title {
  font-size: 16px; font-weight: 700; color: var(--text);
}

.tl-group-label {
  font-size: 11px; font-weight: 700; color: var(--text2);
  text-transform: uppercase; letter-spacing: .5px;
  padding: 8px 0 4px;
}

.tl-run-card {
  display: flex; align-items: center; gap: 12px;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 14px 16px;
  cursor: pointer; transition: all .15s;
}

.tl-run-card:hover {
  border-color: var(--accent);
  background: var(--surface2);
}

.tl-run-running { border-left: 3px solid var(--accent); }

.tl-run-past { border-left: 3px solid transparent; }

.run-main { flex: 1; min-width: 0; }

.run-header {
  display: flex; align-items: center; gap: 8px;
  margin-bottom: 4px;
}

.run-scene { font-size: 14px; font-weight: 600; color: var(--text); }

.run-id { font-size: 11px; color: var(--text2); font-family: monospace; margin-bottom: 4px; }

.run-meta {
  display: flex; align-items: center; gap: 12px;
  font-size: 11px; color: var(--text2);
}

.run-question {
  font-size: 12px; color: var(--text2);
  margin-top: 6px; font-style: italic; opacity: .7;
}

.run-error-msg {
  color: var(--red); font-family: monospace; font-size: 10px;
  max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}

.run-arrow { color: var(--text2); font-size: 16px; transition: transform .15s; }
.tl-run-card:hover .run-arrow { transform: translateX(3px); color: var(--accent); }

.text-green { color: var(--green); }
.text-yellow { color: var(--yellow); }
.text-red { color: var(--red); }

.status-dot.pulse { animation: dotPulse 1.5s infinite; }
@keyframes dotPulse {
  0%, 100% { box-shadow: 0 0 0 0 var(--accent); }
  50% { box-shadow: 0 0 0 4px transparent; }
}
</style>
