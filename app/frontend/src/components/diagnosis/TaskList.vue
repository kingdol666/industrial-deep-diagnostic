<template>
  <div class="task-list">
    <!-- New Task Button -->
    <div class="tl-toolbar">
      <span class="tl-title">全部诊断任务</span>
      <button class="btn btn-sm" @click="$emit('new-task')">+ 新建任务</button>
    </div>

    <!-- Loading -->
    <div v-if="loading && runs.length === 0" class="empty-state">
      <div class="spinner" style="margin:0 auto 8px"></div>
      <p>正在加载任务...</p>
    </div>

    <!-- Empty -->
    <div v-else-if="!loading && runs.length === 0" class="empty-state">
      <p style="font-size:28px;margin-bottom:12px;">🔬</p>
      <p>当前还没有诊断任务</p>
      <p style="font-size:12px;color:var(--text2);margin-top:4px;">
        请先在数据页选择文件，再发起新的诊断
      </p>
    </div>

    <!-- Runs grouped: running first, then past -->
    <template v-else>
      <!-- Running Tasks -->
      <template v-if="runningRuns.length > 0">
        <div class="tl-group-label">
          <span class="status-dot dot-blue pulse" style="display:inline-block;width:6px;height:6px;margin-right:6px;"></span>
          活跃任务 ({{ runningRuns.length }})
        </div>
        <div
          v-for="run in runningRuns" :key="run.run_id"
          class="tl-run-card tl-run-running"
          @click="$emit('view-run', run.run_id)"
        >
          <div class="run-main">
            <div class="run-header">
              <span class="run-scene">{{ run.scene_name }}</span>
              <span :class="['badge', getRunStatusBadgeClass(run)]">{{ getRunStatusLabel(run) }}</span>
            </div>
            <div class="run-id">#{{ run.run_id }}</div>
            <div class="run-meta">
              <span>{{ formatTime(run.created_at) }}</span>
              <span v-if="getEffectiveRunStatus(run) === 'running'">诊断执行中...</span>
              <span v-else-if="getEffectiveRunStatus(run) === 'awaiting_input'">等待你的回答...</span>
            </div>
            <div class="run-question" v-if="run.user_question">{{ run.user_question.slice(0, 120) }}{{ run.user_question.length > 120 ? '...' : '' }}</div>
          </div>
          <div class="run-arrow">→</div>
        </div>
      </template>

      <!-- Past Tasks -->
      <template v-if="pastRuns.length > 0">
        <div class="tl-group-label">
          历史任务 ({{ pastRuns.length }})
        </div>
        <div
          v-for="run in pastRuns" :key="run.run_id"
          class="tl-run-card tl-run-past"
          @click="onPastRunClick(run)"
        >
          <div class="run-main">
            <div class="run-header">
              <span class="run-scene">{{ run.scene_name }}</span>
              <span :class="['badge', getRunStatusBadgeClass(run)]">{{ getRunStatusLabel(run) }}</span>
            </div>
            <div class="run-id">#{{ run.run_id }}</div>
            <div class="run-meta">
              <span>{{ formatTime(run.created_at) }}</span>
              <span v-if="run.score != null">评分: {{ run.score }}/100</span>
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
import { computed, onMounted } from 'vue';
import { useDiagnosisRealtimeStore } from '../../stores/diagnosisRealtimeStore.js';
import { formatTime } from '../../utils/time.js';
import { getEffectiveRunStatus, getRunStatusBadgeClass, getRunStatusLabel } from '../../utils/diagnosisRun.js';

const emit = defineEmits(['view-run', 'view-report', 'new-task']);
const { state, runningRuns, pastRuns, refreshCatalog, connect } = useDiagnosisRealtimeStore();
const loading = computed(() => state.wsStatus === 'connecting' && state.catalogRuns.length === 0);
const runs = computed(() => state.catalogRuns);

function onPastRunClick(run) {
  if (run.report_path) {
    emit('view-report', run.report_path);
  } else {
    // Always allow viewing run details (completed without report, failed, stopped, pending)
    emit('view-run', run.run_id);
  }
}

function verdictColor(v) {
  if (v === 'PASS' || v === 'ENDORSED') return 'text-green';
  if (v === 'CONDITIONAL' || v === 'NEEDS_REPAIR') return 'text-yellow';
  return 'text-red';
}

onMounted(() => {
  // connect is managed centrally by App.vue
  refreshCatalog();
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
