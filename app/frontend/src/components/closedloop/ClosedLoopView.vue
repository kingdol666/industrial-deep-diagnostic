<template>
  <div class="cl-view">
    <header class="cl-head">
      <div class="cl-head-text">
        <p class="cl-kicker">{{ $t('tabs.closedloop.kicker') }}</p>
        <h2 class="cl-title">{{ $t('tabs.closedloop.title') }}</h2>
        <p class="cl-desc">{{ $t('tabs.closedloop.description') }}</p>
      </div>
    </header>

    <nav class="cl-subtabs">
      <button
        v-for="key in subtabs" :key="key" type="button"
        :class="['cl-subtab', { active: subtab === key }]"
        @click="subtab = key"
      >{{ $t(`closedloop.subtabs.${key}`) }}</button>
    </nav>

    <!-- v-show (not v-if): launcher selection survives subtab switches -->
    <div v-for="key in subtabs" :key="key" v-show="subtab === key" class="cl-panel">
      <div class="cl-card">
        <h3>{{ $t(`closedloop.panels.${key}.title`) }}</h3>
        <p class="cl-panel-desc">{{ $t(`closedloop.panels.${key}.desc`) }}</p>
        <AgentTaskLauncher
          :intent="key"
          :skill="PANEL_SKILL[key]"
          :harness="harness"
          @launched="onLaunched"
        />
      </div>

      <div class="cl-card">
        <div class="cl-runs-head">
          <h3>{{ $t('closedloop.runs.title') }}</h3>
          <button type="button" class="cl-refresh" :title="$t('closedloop.runs.refresh')" @click="loadRuns">⟳</button>
        </div>
        <div v-if="runsLoading" class="cl-state">{{ $t('closedloop.runs.loading') }}</div>
        <div v-else-if="!intentRuns.length" class="cl-state">{{ $t('closedloop.runs.empty') }}</div>
        <table v-else class="cl-runs">
          <thead>
            <tr>
              <th>{{ $t('closedloop.runs.name') }}</th>
              <th>{{ $t('closedloop.runs.status') }}</th>
              <th>{{ $t('closedloop.runs.time') }}</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in intentRuns" :key="r.run_id">
              <td class="cl-run-name" :title="r.name">{{ r.name }}</td>
              <td><span class="cl-run-status" :class="statusClass(r)">{{ statusLabel(r) }}</span></td>
              <td class="cl-run-time">{{ shortTime(r.created_at) }}</td>
              <td class="cl-run-actions">
                <button type="button" class="cl-open" @click="emit('open-run', r.run_id)">{{ $t('closedloop.runs.open') }}</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
// Specialized analysis console — every panel dispatches a REAL harness run
// whose agent executes the panel's skill protocol (no script wrappers; the
// retired fixed-script HTTP integrations are gone). The analysis process is
// shown by the live run view; artifacts persist in the run dir + DB.
import { ref, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import AgentTaskLauncher from './AgentTaskLauncher.vue';
import { api } from '../../api/index.js';
import { getEffectiveRunStatus } from '../../utils/diagnosisRun.js';

const props = defineProps({
  harness: { type: String, default: 'claude' },
});

const emit = defineEmits(['launched', 'open-run']);

const { t } = useI18n();

// Panel → analysisIntent (ids mirror ANALYSIS_INTENTS in the backend) and
// the skill whose protocol the agent will follow.
const subtabs = ['stability-report', 'quick-screen', 'experience-mining', 'optimizer-campaign'];
const PANEL_SKILL = {
  'stability-report': 'industrial-line-stability-report',
  'quick-screen': 'industrial-sentinel',
  'experience-mining': 'industrial-tuning-memory',
  'optimizer-campaign': 'industrial-optimizer-loop',
};

const subtab = ref('stability-report');
const allRuns = ref([]);
const runsLoading = ref(false);

const intentRuns = computed(() =>
  allRuns.value.filter((r) => (r.analysis_intent || 'deep-diagnosis') === subtab.value).slice(0, 8),
);

async function loadRuns() {
  runsLoading.value = true;
  try {
    const res = await api.getRuns();
    allRuns.value = Array.isArray(res) ? res : (res?.data || []);
  } catch {
    allRuns.value = [];
  } finally {
    runsLoading.value = false;
  }
}

function statusClass(run) {
  const s = getEffectiveRunStatus(run);
  if (s === 'completed') return 'ok';
  if (s === 'failed' || s === 'stopped' || s === 'expired') return 'bad';
  return 'busy';
}

function statusLabel(run) {
  return getRunStatusLabelSafe(run);
}

function getRunStatusLabelSafe(run) {
  const s = getEffectiveRunStatus(run);
  const key = {
    completed: 'completed', failed: 'failed', stopped: 'stopped',
    running: 'running', pending: 'queued', awaiting_input: 'awaiting',
    expired: 'expired', interrupted: 'failed',
  }[s];
  return key ? t(`closedloop.runs.status_${key}`) : s;
}

function shortTime(value) {
  if (!value) return '';
  const d = new Date(String(value).includes('T') ? value : `${value}Z`);
  return Number.isFinite(d.getTime())
    ? d.toLocaleString(undefined, { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
    : value;
}

function onLaunched(runId) {
  loadRuns();
  emit('launched', runId);
}

onMounted(loadRuns);
</script>

<style scoped>
.cl-view {
  display: flex;
  flex-direction: column;
  gap: 14px;
  height: 100%;
  overflow-y: auto;
  padding: 18px 22px 26px;
}
.cl-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}
.cl-kicker {
  margin: 0 0 2px;
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--accent);
}
.cl-title {
  margin: 0 0 6px;
  font-family: var(--font-display);
  font-size: 26px;
  font-weight: 600;
  color: var(--text);
}
.cl-desc {
  margin: 0;
  max-width: 760px;
  font-size: 13px;
  line-height: 1.55;
  color: var(--text3);
}
.cl-subtabs {
  display: flex;
  gap: 8px;
  border-bottom: 1px solid var(--border);
  padding-bottom: 0;
}
.cl-subtab {
  appearance: none;
  border: 1px solid transparent;
  border-bottom: none;
  background: transparent;
  color: var(--text3);
  font-family: var(--font-ui);
  font-size: 13px;
  padding: 8px 16px;
  cursor: pointer;
  border-radius: 8px 8px 0 0;
  position: relative;
  top: 1px;
}
.cl-subtab:hover { color: var(--text2); }
.cl-subtab.active {
  background: var(--surface);
  border-color: var(--border);
  color: var(--accent);
  font-weight: 600;
}
.cl-panel { display: flex; flex-direction: column; gap: 16px; }
.cl-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 14px 16px 16px;
}
.cl-card h3 {
  margin: 0 0 4px;
  font-family: var(--font-ui);
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
}
.cl-panel-desc { margin: 0 0 12px; font-size: 12px; line-height: 1.6; color: var(--text2); }
.cl-runs-head { display: flex; align-items: center; justify-content: space-between; }
.cl-refresh { appearance: none; background: none; border: 1px solid var(--border); border-radius: 8px; color: var(--text2); cursor: pointer; padding: 2px 10px; font-size: 13px; }
.cl-refresh:hover { color: var(--text); border-color: var(--accent); }
.cl-state { padding: 14px 0 6px; text-align: center; color: var(--text2); font-size: 12px; }
.cl-runs { width: 100%; border-collapse: collapse; margin-top: 8px; font-size: 12.5px; }
.cl-runs th {
  text-align: left; padding: 6px 8px; color: var(--text2); font-weight: 600;
  font-size: 11px; text-transform: uppercase; letter-spacing: .4px;
  border-bottom: 1px solid var(--border);
}
.cl-runs td { padding: 7px 8px; border-bottom: 1px solid color-mix(in srgb, var(--border) 55%, transparent); }
.cl-run-name { font-family: var(--font-mono, monospace); max-width: 280px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cl-run-time { color: var(--text2); font-variant-numeric: tabular-nums; }
.cl-run-actions { text-align: right; }
.cl-run-status { display: inline-block; padding: 2px 10px; border-radius: 99px; font-size: 11px; font-weight: 600; }
.cl-run-status.ok { background: color-mix(in srgb, var(--green) 12%, transparent); color: var(--green); }
.cl-run-status.bad { background: color-mix(in srgb, var(--red) 12%, transparent); color: var(--red); }
.cl-run-status.busy { background: color-mix(in srgb, var(--accent) 12%, transparent); color: var(--accent); }
.cl-open {
  appearance: none; background: color-mix(in srgb, var(--accent) 10%, transparent);
  border: 1px solid color-mix(in srgb, var(--accent) 26%, transparent);
  color: var(--accent); border-radius: 8px; padding: 4px 12px;
  font-size: 12px; font-weight: 600; cursor: pointer; font-family: inherit;
}
.cl-open:hover { background: color-mix(in srgb, var(--accent) 18%, transparent); }
</style>
