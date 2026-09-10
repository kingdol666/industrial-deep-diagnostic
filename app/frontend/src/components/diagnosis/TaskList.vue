<template>
  <div class="task-list">
    <!-- Toolbar — title becomes a labelled rail, action stays right -->
    <div class="ip-panel-head tl-toolbar">
      <span class="ip-label">{{ $t('taskList.title') }}</span>
      <span class="tl-counts">
        <span class="ip-chip accent no-dot">{{ $t('taskList.active') }} {{ runningRuns.length }}</span>
        <span class="ip-chip muted no-dot">{{ $t('taskList.history') }} {{ pastRuns.length }}</span>
      </span>
      <button class="btn btn-sm" @click="$emit('new-task')">{{ $t('taskList.newTask') }}</button>
    </div>

    <!-- Loading -->
    <div v-if="loading && runs.length === 0" class="ip-empty">
      <div class="spinner"></div>
      <span class="ip-empty-title">{{ $t('taskList.loadingTasks') }}</span>
    </div>

    <!-- Empty -->
    <div v-else-if="!loading && runs.length === 0" class="ip-empty">
      <span class="ip-empty-mark">[ ]</span>
      <span class="ip-empty-title">{{ $t('taskList.empty') }}</span>
      <span class="ip-empty-hint">{{ $t('taskList.emptyHint') }}</span>
    </div>

    <!-- Runs — one dense readout, grouped by state rather than by card style -->
    <template v-else>
      <div class="ip-table tl-table">
        <div class="ip-thead tl-cols">
          <span>{{ $t('taskList.colRun') }}</span>
          <span>{{ $t('taskList.colState') }}</span>
          <span>{{ $t('taskList.colVerdict') }}</span>
          <span class="ta-r">{{ $t('taskList.colScore') }}</span>
          <span class="ta-r">{{ $t('taskList.colTime') }}</span>
        </div>

        <div class="tl-body ip-scroll">
          <template v-if="runningRuns.length > 0">
            <div class="tl-group-label">
              <span class="tl-pulse"></span>{{ $t('taskList.active') }}
            </div>
            <div
              v-for="run in runningRuns" :key="run.run_id"
              class="ip-row tl-cols tl-row is-active"
              @click="$emit('view-run', run.run_id)"
            >
              <span class="tl-name">
                <span class="tl-scene">{{ run.scene_name }}</span>
                <span class="tl-id mono">#{{ run.run_id }}</span>
                <span v-if="run.user_question" class="tl-question" :title="run.user_question">
                  {{ run.user_question }}
                </span>
              </span>
              <span><span class="ip-chip accent">{{ getRunStatusLabel(run) }}</span></span>
              <span class="tl-verdict">{{ getEffectiveRunStatus(run) === 'running' ? $t('taskList.inProgress') : $t('taskList.awaitingAnswer') }}</span>
              <span class="ta-r tl-score">—</span>
              <span class="ta-r tl-time">{{ formatTime(run.created_at) }}</span>
            </div>
          </template>

          <template v-if="pastRuns.length > 0">
            <div class="tl-group-label">{{ $t('taskList.history') }}</div>
            <div
              v-for="run in pastRuns" :key="run.run_id"
              class="ip-row tl-cols tl-row"
              @click="onPastRunClick(run)"
            >
              <span class="tl-name">
                <span class="tl-scene">{{ run.scene_name }}</span>
                <span class="tl-id mono">#{{ run.run_id }}</span>
                <span v-if="run.error_message" class="tl-error" :title="run.error_message">
                  {{ run.error_message }}
                </span>
              </span>
              <span><span class="ip-chip" :class="statusTone(run)">{{ getRunStatusLabel(run) }}</span></span>
              <span class="tl-verdict" :class="verdictColor(run.judge_verdict)">{{ run.judge_verdict || '—' }}</span>
              <span class="ta-r tl-score" :class="scoreTone(run.score)">
                {{ run.score != null ? run.score : '—' }}
              </span>
              <span class="ta-r tl-time">{{ formatTime(run.created_at) }}</span>
            </div>
          </template>
        </div>
      </div>
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

/** Map the legacy badge class onto the instrument chip tone. */
function statusTone(run) {
  const cls = getRunStatusBadgeClass(run) || '';
  if (cls.includes('green')) return 'ok';
  if (cls.includes('red')) return 'bad';
  if (cls.includes('yellow')) return 'warn';
  if (cls.includes('blue')) return 'info';
  return 'muted';
}

function scoreTone(score) {
  if (score == null) return '';
  if (score >= 90) return 'ok';
  if (score >= 70) return 'warn';
  return 'bad';
}

function verdictColor(v) {
  if (v === 'PASS' || v === 'ENDORSED') return 'text-green';
  if (v === 'CONDITIONAL' || v === 'NEEDS_REPAIR') return 'text-yellow';
  if (!v) return '';
  return 'text-red';
}

onMounted(() => {
  // connect is managed centrally by App.vue
  refreshCatalog();
});
</script>

<style scoped>
.task-list { display: flex; flex-direction: column; gap: 10px; }

.tl-toolbar { gap: 10px; }
.tl-toolbar .ip-label { flex: 1; }
.tl-counts { display: flex; gap: 5px; }
.tl-counts .ip-chip { font-size: var(--fs-micro); }

/* One shared column template so the header and every row stay aligned. */
.tl-cols {
  grid-template-columns: minmax(0, 2.6fr) 104px minmax(90px, 0.8fr) 54px 96px;
}
.tl-table { min-height: 0; }
.tl-body { overflow-y: auto; min-height: 0; }
.tl-row { cursor: pointer; min-height: 34px; }

.tl-group-label {
  display: flex;
  align-items: center;
  gap: 6px;
  height: 24px;
  padding: 0 12px;
  font-size: var(--fs-micro);
  letter-spacing: var(--track-label);
  text-transform: uppercase;
  color: var(--text3);
  background: var(--surface-soft);
  border-bottom: 1px solid var(--border);
  position: sticky;
  top: 28px;
  z-index: 1;
}

.tl-pulse {
  width: 5px; height: 5px; border-radius: 50%;
  background: var(--accent);
  animation: tlPulse 1.5s ease-in-out infinite;
}
@keyframes tlPulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(232,163,61,0.55); }
  50% { box-shadow: 0 0 0 4px rgba(232,163,61,0); }
}

.tl-name { display: flex; align-items: baseline; gap: 8px; min-width: 0; }
.tl-scene {
  font-size: var(--fs-body);
  font-weight: 500;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 34ch;
}
.tl-id { font-size: var(--fs-micro); color: var(--text-dim); flex: none; }
.tl-question {
  font-size: var(--fs-micro);
  color: var(--text3);
  font-style: italic;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
}
.tl-error { font-size: var(--fs-micro); color: var(--red); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.tl-verdict { font-size: var(--fs-micro); font-family: var(--font-mono); color: var(--text3); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tl-score { font-family: var(--font-mono); font-variant-numeric: tabular-nums; color: var(--text2); }
.tl-score.ok { color: var(--green); }
.tl-score.warn { color: var(--yellow); }
.tl-score.bad { color: var(--red); }
.tl-time { font-family: var(--font-mono); font-size: var(--fs-micro); color: var(--text3); white-space: nowrap; }

.text-green { color: var(--green); }
.text-yellow { color: var(--yellow); }
.text-red { color: var(--red); }
</style>
