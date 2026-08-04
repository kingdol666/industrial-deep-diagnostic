<template>
  <div class="omp-view">
    <!-- ── Header ── -->
    <div class="omp-header">
      <div class="omp-header-copy">
        <div class="omp-header-kicker">{{ $t('harness.headerKicker') }} · {{ harnessName }}</div>
        <h2 class="omp-header-title">{{ harnessName }}{{ $t('harness.headerTitle') }}</h2>
        <p class="omp-header-sub">
          {{ $t('harness.descPre') }} {{ harnessName }} {{ $t('harness.descMid') }}
          <span v-if="runsDirLabel">{{ $t('harness.dirLabel') }}<code>{{ runsDirLabel }}</code></span>
        </p>
      </div>
      <div class="omp-header-meta">
        <button class="btn btn-sm" :disabled="loading" @click="load()">
          {{ loading ? $t('harness.scanning') : $t('harness.refresh') }}
        </button>
        <span class="omp-engine-pill" :class="{ off: !health.available }">
          <span class="omp-engine-dot" />
          {{ health.available ? `${harnessName} ${$t('harness.engineOnline')} · ${runCountLabel} ${$t('harness.engineRunsSuffix')}` : `${harnessName} ${$t('harness.engineUnavailable')}` }}
        </span>
      </div>
    </div>

    <!-- ── Capability chips ── -->
    <div v-if="capabilities.length" class="omp-caps">
      <span
        v-for="c in capabilities"
        :key="c"
        class="omp-cap"
        :class="{ disabled: !capabilityMap[c] }"
      >
        {{ capLabel(c) }}
      </span>
    </div>

    <!-- ── Stats row ── -->
    <div v-if="runs.length" class="omp-stats">
      <div class="omp-stat"><span class="omp-stat-num">{{ runs.length }}</span><span class="omp-stat-label">{{ $t('harness.statTotal') }}</span></div>
      <div class="omp-stat"><span class="omp-stat-num">{{ completedCount }}</span><span class="omp-stat-label">{{ $t('harness.statCompleted') }}</span></div>
      <div class="omp-stat"><span class="omp-stat-num">{{ enhancedCount }}</span><span class="omp-stat-label">{{ $t('harness.statEnhanced') }}</span></div>
      <div class="omp-stat"><span class="omp-stat-num">{{ withHtmlCount }}</span><span class="omp-stat-label">{{ $t('harness.statHtml') }}</span></div>
    </div>

    <!-- ── Run list ── -->
    <div v-if="loading" class="empty-state"><div class="spinner" /> {{ $t('harness.loadingRuns') }}</div>

    <div v-else-if="error" class="omp-error">{{ error }}</div>

    <div v-else-if="!runs.length" class="empty-state">
      <p>{{ $t('harness.noRuns') }}</p>
    </div>

    <div v-else class="omp-run-list">
      <div
        v-for="run in runs"
        :key="run.name"
        class="omp-run-card"
        :class="{ open: selected === run.name }"
        @click="toggleRun(run.name)"
      >
        <div class="omp-run-card-head">
          <div class="omp-run-badges">
            <span class="omp-status" :class="statusClass(run)">{{ statusText(run) }}</span>
            <span v-if="run.verdict" class="badge" :class="verdictClass(run.verdict)">{{ run.verdict }}</span>
            <span v-if="run.enhancement_status" class="badge" :class="enhClass(run.enhancement_status)">
              E:{{ run.enhancement_status.replace('READY', 'R').replace('_WITH_WARNINGS', '±') }}
            </span>
          </div>
          <div class="omp-run-meta">
            <span>{{ formatTime(run.created) }}</span>
            <span>· {{ run.artifact_count }} {{ $t('harness.artifactCount') }}</span>
            <span>· {{ run.agents.length || 0 }} {{ $t('harness.agentCount') }}</span>
          </div>
        </div>
        <div class="omp-run-title">{{ run.display_name }}</div>
        <div class="omp-run-name"><code>{{ run.name }}</code></div>

        <!-- ── Detail panel ── -->
        <div v-if="selected === run.name" class="omp-run-detail" @click.stop>
          <HarnessRunDetail
            :name="run.name"
            :harness-id="harnessId"
            :harness-name="harnessName"
            :capabilities="capabilities"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { api } from '../../api/index.js';
import HarnessRunDetail from './HarnessRunDetail.vue';

const { t } = useI18n();

const props = defineProps({
  harnessId: { type: String, required: true },
  harnessName: { type: String, default: 'Engine' },
  capabilities: { type: Array, default: () => [] },
});

const runs = ref([]);
const loading = ref(false);
const error = ref('');
const selected = ref(null);
const health = ref({ available: false, meta: {} });

const capabilityMap = computed(() =>
  Object.fromEntries(props.capabilities.map((c) => [c, true]))
);
const runsDirLabel = computed(() => {
  const dir = health.value.meta?.runs_dir || '';
  return dir ? dir.replace(/\\/g, '/') : '';
});
const runCountLabel = computed(() => health.value.meta?.run_count ?? 0);

const completedCount = computed(() => runs.value.filter((r) => r.verdict === 'ENDORSED').length);
const enhancedCount = computed(() => runs.value.filter((r) => r.enhancement_status).length);
const withHtmlCount = computed(() => runs.value.filter((r) => r.has_html).length);

function capLabel(c) {
  const keyMap = { live: 'cap_live', runs: 'cap_runs', report: 'cap_report', html: 'cap_html', enhancement: 'cap_enhancement', chat: 'cap_chat' };
  const key = keyMap[c];
  return key ? t(`harness.${key}`) : c;
}

function statusClass(run) {
  if (run.baseline_status === 'completed') return 'st-completed';
  if (run.baseline_status === 'report_ready') return 'st-report';
  if (run.baseline_status === 'diagnosed') return 'st-diagnosed';
  if (run.baseline_status === 'in_progress') return 'st-progress';
  return 'st-init';
}

function statusText(run) {
  const keyMap = {
    completed: 'status_completed',
    report_ready: 'status_report_ready',
    diagnosed: 'status_diagnosed',
    in_progress: 'status_in_progress',
    initialized: 'status_initialized',
    unknown: 'status_unknown',
  };
  const key = keyMap[run.baseline_status];
  return key ? t(`harness.${key}`) : run.baseline_status;
}

function verdictClass(v) {
  return { ENDORSED: 'badge-green', CONDITIONAL: 'badge-yellow', REJECTED: 'badge-red' }[v] || 'badge-blue';
}

function enhClass(s) {
  if (!s) return 'badge-blue';
  if (s === 'READY') return 'badge-green';
  if (s === 'READY_WITH_WARNINGS') return 'badge-yellow';
  return 'badge-red';
}

function formatTime(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  const locale = t('common.appName') === 'Industrial Deep Diagnostic' ? 'zh-CN' : 'en-US';
  return d.toLocaleString(locale, { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
}

async function load() {
  loading.value = true;
  error.value = '';
  try {
    const [h, r] = await Promise.all([
      api.harnessHealth(props.harnessId),
      api.harnessRuns(props.harnessId),
    ]);
    health.value = h;
    runs.value = r;
  } catch (e) {
    error.value = `${props.harnessName}${t('harness.bridgeFailed')}${e.message}`;
  } finally {
    loading.value = false;
  }
}

function toggleRun(name) {
  selected.value = selected.value === name ? null : name;
}

onMounted(load);
</script>
