<template>
  <div class="omp-detail" v-if="run">
    <!-- ── Tabs (capability-driven: only what this engine supports) ── -->
    <div class="omp-detail-tabs">
      <button
        v-for="tb in visibleTabs"
        :key="tb.key"
        class="omp-tab"
        :class="{ active: activeTab === tb.key }"
        @click="activeTab = tb.key"
      >
        {{ tb.label }}
      </button>
    </div>

    <div v-if="detailError" class="omp-error">{{ detailError }}</div>

    <!-- ══ Overview (always available) ══ -->
    <div v-if="activeTab === 'overview'" class="omp-panel">
      <div class="omp-grid2">
        <div class="omp-card">
          <div class="omp-card-title">{{ $t('harness.baselineStatus') }}</div>
          <div class="omp-kv">
            <div class="omp-kv-row"><span>{{ $t('harness.execStatus') }}</span><b>{{ run.baseline.status }}</b></div>
            <div class="omp-kv-row"><span>{{ $t('harness.auditVerdict') }}</span><b>{{ run.baseline.verdict || '—' }}</b></div>
            <div class="omp-kv-row"><span>{{ $t('harness.report') }}</span><b>{{ run.baseline.hasReport ? '✓' : '—' }}</b></div>
            <div class="omp-kv-row"><span>{{ $t('harness.html') }}</span><b>{{ run.baseline.hasHtml ? '✓' : '—' }}</b></div>
            <div class="omp-kv-row"><span>{{ $t('harness.diagnosis') }}</span><b>{{ run.baseline.hasDiagnosis ? '✓' : '—' }}</b></div>
            <div class="omp-kv-row"><span>{{ $t('harness.agents') }}</span><b>{{ run.baseline.agents.join(', ') || '—' }}</b></div>
          </div>
        </div>
        <div class="omp-card">
          <div class="omp-card-title">{{ $t('harness.enhancementStatus') }}</div>
          <template v-if="run.enhancement">
            <div class="omp-kv">
              <div class="omp-kv-row"><span>{{ $t('harness.enhStatus') }}</span><b>{{ run.enhancement.status || '—' }}</b></div>
              <div class="omp-kv-row"><span>{{ $t('harness.dataFingerprint') }}</span><b class="mono">{{ shortHash(run.enhancement.data_sha256) }}</b></div>
              <div class="omp-kv-row"><span>{{ $t('harness.dataScale') }}</span><b>{{ run.enhancement.rows }} {{ $t('harness.rowsSuffix') }} × {{ run.enhancement.cols }} {{ $t('harness.colsSuffix') }}</b></div>
              <div class="omp-kv-row"><span>{{ $t('harness.artifactCoverage') }}</span><b>{{ enhancementDone }}/9</b></div>
            </div>
            <div class="omp-art-progress"><div class="omp-art-fill" :style="{ width: `${(enhancementDone / 9) * 100}%` }" /></div>
          </template>
          <p v-else class="omp-muted">{{ $t('harness.noEnhancement') }}</p>
        </div>
      </div>

      <div class="omp-card">
        <div class="omp-card-title">{{ $t('harness.keyFindings') }}</div>
        <p v-if="summary && summary.primary_finding" class="omp-finding">{{ summary.primary_finding }}</p>
        <p v-else class="omp-muted">{{ $t('harness.noSummary') }}</p>
        <div v-if="summary && summary.enhanced_relationships" class="omp-kv omp-inline">
          <div class="omp-kv-row"><span>{{ $t('harness.enhancedRelationships') }}</span><b>{{ summary.enhanced_relationships }}</b></div>
          <div class="omp-kv-row"><span>{{ $t('harness.mechanismChains') }}</span><b>{{ summary.enhanced_mechanism_chains }}</b></div>
          <div class="omp-kv-row"><span>{{ $t('harness.evidenceGaps') }}</span><b>{{ summary.enhanced_gaps }}</b></div>
        </div>
      </div>
    </div>

    <!-- ══ Events ══ -->
    <div v-if="activeTab === 'events'" class="omp-panel">
      <div class="omp-card">
        <div class="omp-card-title">{{ $t('harness.execProof') }}（{{ run.events.length }} {{ $t('harness.eventsSuffix') }}）</div>
        <div v-if="!run.events.length" class="omp-muted">{{ $t('harness.noEvents') }}</div>
        <div v-else class="omp-events">
          <div v-for="(ev, i) in run.events" :key="i" class="omp-event" :class="`ev-${ev.type}`">
            <span class="omp-event-time">{{ ev.time ? formatTime(ev.time) : '' }}</span>
            <span class="omp-event-type">{{ ev.type }}</span>
            <span class="omp-event-agent">{{ ev.agent || ev.step || '' }}</span>
            <span class="omp-event-files">{{ (ev.files || []).join(', ').slice(0, 80) }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- ══ Reports (requires 'report' capability) ══ -->
    <div v-if="activeTab === 'reports'" class="omp-panel">
      <div v-if="supports('report')">
        <div class="omp-report-tools">
          <button
            v-for="r in reportKinds"
            :key="r"
            class="btn btn-sm"
            :class="{ active: activeReport === r }"
            @click="openReport(r)"
          >
            {{ { report: 'report.md', optimizer: 'optimizer.md', preflight: 'optimizer_preflight.md' }[r] }}
          </button>
        </div>
        <div v-if="reportText" class="omp-markdown" v-html="renderedReport" />
        <div v-else class="omp-muted">{{ $t('harness.selectDoc') }}</div>
      </div>
      <div v-else class="omp-muted">{{ $t('harness.noReportCap') }}</div>
    </div>

    <!-- ══ HTML (requires 'html' capability) ══ -->
    <div v-if="activeTab === 'html'" class="omp-panel">
      <div v-if="supports('html')">
        <div class="omp-report-tools">
          <button class="btn btn-sm" :class="{ active: htmlMode === 'baseline' }" @click="htmlMode = 'baseline'">{{ $t('harness.baselineHtml') }}</button>
          <button class="btn btn-sm" :class="{ active: htmlMode === 'enhanced' }" @click="htmlMode = 'enhanced'">{{ $t('harness.enhancedHtml') }}</button>
        </div>
        <iframe
          v-if="htmlSrc"
          :src="htmlSrc"
          class="omp-iframe"
          sandbox="allow-scripts allow-same-origin"
          :title="`${harnessName} ${$t('harness.htmlReportTitle')}`"
        />
        <div v-else class="omp-muted">{{ $t('harness.noHtml') }}</div>
      </div>
      <div v-else class="omp-muted">{{ $t('harness.noHtmlCap') }}</div>
    </div>

    <!-- ══ Enhancement (requires 'enhancement' capability) ══ -->
    <div v-if="activeTab === 'enhancement'" class="omp-panel">
      <div v-if="supports('enhancement')">
        <div class="omp-enh-grid">
          <button
            v-for="a in enhArtifacts"
            :key="a.kind"
            class="omp-enh-card"
            :class="{ active: activeEnh === a.kind }"
            @click="openEnh(a.kind)"
          >
            <span class="omp-enh-name">{{ a.label }}</span>
            <span class="omp-enh-file">{{ a.file }}</span>
          </button>
        </div>
        <div v-if="enhContent" class="omp-enh-content">
          <pre v-if="isJsonView">{{ JSON.stringify(enhContent, null, 2).slice(0, 8000) }}</pre>
          <div v-else class="omp-markdown" v-html="renderedEnh" />
        </div>
      </div>
      <div v-else class="omp-muted">{{ $t('harness.noEnhCap') }}</div>
    </div>
  </div>
  <div v-else class="empty-state"><div class="spinner" /> {{ $t('harness.loadingDetail') }}</div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { api } from '../../api/index.js';
import { renderMarkdown } from '../../utils/markdown.js';

const { t } = useI18n();

const props = defineProps({
  name: { type: String, required: true },
  harnessId: { type: String, required: true },
  harnessName: { type: String, default: 'Engine' },
  capabilities: { type: Array, default: () => [] },
});

const run = ref(null);
const summary = ref(null);
const detailError = ref('');
const activeTab = ref('overview');
const activeReport = ref('report');
const reportText = ref('');
const htmlMode = ref('baseline');
const htmlSrc = ref('');
const activeEnh = ref('deep');
const enhContent = ref(null);

const reportKinds = ['report', 'optimizer', 'preflight'];

const allTabs = computed(() => [
  { key: 'overview', label: t('harness.tabOverview') },
  { key: 'events', label: t('harness.tabEvents') },
  { key: 'reports', label: t('harness.tabReports'), cap: 'report' },
  { key: 'html', label: t('harness.tabHtml'), cap: 'html' },
  { key: 'enhancement', label: t('harness.tabEnhancement'), cap: 'enhancement' },
]);

/** Capability-driven tab filtering — engines expose only what they implement. */
const visibleTabs = computed(() => allTabs.value.filter((tb) => !tb.cap || props.capabilities.includes(tb.cap)));

const enhArtifacts = computed(() => [
  { kind: 'coverage', label: t('harness.enh_e1'), file: 'analysis_coverage.json' },
  { kind: 'derived', label: t('harness.enh_e2'), file: 'derived_features.json' },
  { kind: 'deep', label: t('harness.enh_e3'), file: 'deep_data_analysis.json' },
  { kind: 'graph', label: t('harness.enh_e35'), file: 'association_graph.json' },
  { kind: 'bridge', label: t('harness.enh_e5'), file: 'physics_bridge.json' },
  { kind: 'knowledge', label: t('harness.enh_e6'), file: 'enhanced_knowledge.json' },
  { kind: 'markdown', label: t('harness.enh_e7a'), file: 'enhanced_analysis.md' },
  { kind: 'review', label: t('harness.enh_e7c'), file: 'enhancement_html_review.json' },
  { kind: 'status', label: t('harness.enh_e8'), file: 'enhancement_status.json' },
]);

function supports(cap) {
  return props.capabilities.includes(cap);
}

const isJsonView = computed(() => activeEnh.value !== 'markdown');

const enhancementDone = computed(() => {
  if (!run.value?.enhancement?.artifacts) return 0;
  return Object.values(run.value.enhancement.artifacts).filter(Boolean).length;
});

const renderedReport = computed(() => (reportText.value ? renderMarkdown(reportText.value) : ''));
const renderedEnh = computed(() =>
  enhContent.value && !isJsonView.value ? renderMarkdown(enhContent.value) : ''
);

function shortHash(h) {
  return h ? h.slice(0, 12) : '—';
}

function formatTime(iso) {
  try {
    const locale = t('common.appName') === 'Industrial Deep Diagnostic' ? 'zh-CN' : 'en-US';
    return new Date(iso).toLocaleTimeString(locale, { hour: '2-digit', minute: '2-digit' });
  } catch {
    return iso || '';
  }
}

async function openReport(kind) {
  activeReport.value = kind;
  detailError.value = '';
  try {
    const art = await api.harnessArtifact(props.harnessId, props.name, kind);
    reportText.value = art?.content || '';
  } catch (e) {
    reportText.value = '';
    detailError.value = `${t('harness.readReportFailed')}${e.message}`;
  }
}

async function openEnh(kind) {
  activeEnh.value = kind;
  detailError.value = '';
  try {
    const art = await api.harnessEnhancement(props.harnessId, props.name, kind);
    enhContent.value = art?.content ?? null;
  } catch (e) {
    enhContent.value = null;
    detailError.value = `${t('harness.readEnhFailed')}${e.message}`;
  }
}

async function loadHtml() {
  htmlSrc.value = '';
  detailError.value = '';
  // Guard: only set the iframe src when the run actually has the HTML artifact.
  // The HTML tab is shown whenever the engine supports the capability, but
  // individual runs may not have generated HTML — loading a non-existent
  // file would 404 in the iframe and create console noise.
  const runData = run.value;
  if (!runData) return;
  const hasBaseline = !!runData.baseline?.hasHtml;
  const hasEnhanced = !!runData.enhancement?.artifacts?.['enhanced-analysis.html'];
  const available = htmlMode.value === 'enhanced' ? hasEnhanced : hasBaseline;
  if (!available) return;
  try {
    htmlSrc.value = api.harnessHtmlUrl(props.harnessId, props.name, htmlMode.value);
  } catch (e) {
    detailError.value = `${t('harness.htmlLoadFailed')}${e.message}`;
  }
}

watch(htmlMode, loadHtml);

async function load() {
  detailError.value = '';
  try {
    run.value = await api.harnessRun(props.harnessId, props.name);
  } catch (e) {
    detailError.value = `${t('harness.loadRunFailed')}${e.message}`;
    return;
  }
  try {
    summary.value = await api.harnessSummary(props.harnessId, props.name);
  } catch {
    summary.value = null;
  }
  if (supports('report')) await openReport(activeReport.value);
  if (supports('enhancement')) await openEnh(activeEnh.value);
  if (supports('html')) await loadHtml();
}

watch(() => props.name, load);
onMounted(load);
</script>
