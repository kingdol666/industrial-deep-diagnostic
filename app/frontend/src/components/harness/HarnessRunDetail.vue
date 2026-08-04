<template>
  <div class="omp-detail" v-if="run">
    <!-- ── Tabs (capability-driven: only what this engine supports) ── -->
    <div class="omp-detail-tabs">
      <button
        v-for="t in visibleTabs"
        :key="t.key"
        class="omp-tab"
        :class="{ active: activeTab === t.key }"
        @click="activeTab = t.key"
      >
        {{ t.label }}
      </button>
    </div>

    <div v-if="detailError" class="omp-error">{{ detailError }}</div>

    <!-- ══ Overview (always available) ══ -->
    <div v-if="activeTab === 'overview'" class="omp-panel">
      <div class="omp-grid2">
        <div class="omp-card">
          <div class="omp-card-title">基线管线状态</div>
          <div class="omp-kv">
            <div class="omp-kv-row"><span>执行状态</span><b>{{ run.baseline.status }}</b></div>
            <div class="omp-kv-row"><span>审计判定</span><b>{{ run.baseline.verdict || '—' }}</b></div>
            <div class="omp-kv-row"><span>报告</span><b>{{ run.baseline.hasReport ? '✓' : '—' }}</b></div>
            <div class="omp-kv-row"><span>HTML</span><b>{{ run.baseline.hasHtml ? '✓' : '—' }}</b></div>
            <div class="omp-kv-row"><span>诊断</span><b>{{ run.baseline.hasDiagnosis ? '✓' : '—' }}</b></div>
            <div class="omp-kv-row"><span>参与代理</span><b>{{ run.baseline.agents.join(', ') || '—' }}</b></div>
          </div>
        </div>
        <div class="omp-card">
          <div class="omp-card-title">增强管线状态</div>
          <template v-if="run.enhancement">
            <div class="omp-kv">
              <div class="omp-kv-row"><span>增强状态</span><b>{{ run.enhancement.status || '—' }}</b></div>
              <div class="omp-kv-row"><span>数据指纹</span><b class="mono">{{ shortHash(run.enhancement.data_sha256) }}</b></div>
              <div class="omp-kv-row"><span>数据规模</span><b>{{ run.enhancement.rows }} 行 × {{ run.enhancement.cols }} 列</b></div>
              <div class="omp-kv-row"><span>产物覆盖</span><b>{{ enhancementDone }}/9</b></div>
            </div>
            <div class="omp-art-progress"><div class="omp-art-fill" :style="{ width: `${(enhancementDone / 9) * 100}%` }" /></div>
          </template>
          <p v-else class="omp-muted">该运行未执行增强管线（E1-E8）。</p>
        </div>
      </div>

      <div class="omp-card">
        <div class="omp-card-title">关键发现</div>
        <p v-if="summary && summary.primary_finding" class="omp-finding">{{ summary.primary_finding }}</p>
        <p v-else class="omp-muted">暂无摘要（未生成诊断结论）。</p>
        <div v-if="summary && summary.enhanced_relationships" class="omp-kv omp-inline">
          <div class="omp-kv-row"><span>增强关系</span><b>{{ summary.enhanced_relationships }}</b></div>
          <div class="omp-kv-row"><span>机理链</span><b>{{ summary.enhanced_mechanism_chains }}</b></div>
          <div class="omp-kv-row"><span>证据缺口</span><b>{{ summary.enhanced_gaps }}</b></div>
        </div>
      </div>
    </div>

    <!-- ══ Events ══ -->
    <div v-if="activeTab === 'events'" class="omp-panel">
      <div class="omp-card">
        <div class="omp-card-title">执行证明 · 事件日志（{{ run.events.length }} 条）</div>
        <div v-if="!run.events.length" class="omp-muted">无事件记录。</div>
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
        <div v-else class="omp-muted">选择上方文档查看内容。</div>
      </div>
      <div v-else class="omp-muted">该引擎不支持报告读取（capability: report）。</div>
    </div>

    <!-- ══ HTML (requires 'html' capability) ══ -->
    <div v-if="activeTab === 'html'" class="omp-panel">
      <div v-if="supports('html')">
        <div class="omp-report-tools">
          <button class="btn btn-sm" :class="{ active: htmlMode === 'baseline' }" @click="htmlMode = 'baseline'">基线 HTML</button>
          <button class="btn btn-sm" :class="{ active: htmlMode === 'enhanced' }" @click="htmlMode = 'enhanced'">增强 HTML</button>
        </div>
        <iframe
          v-if="htmlSrc"
          :src="htmlSrc"
          class="omp-iframe"
          sandbox="allow-scripts allow-same-origin"
          :title="`${harnessName} HTML 报告`"
        />
        <div v-else class="omp-muted">该运行没有可用的 HTML 产物。</div>
      </div>
      <div v-else class="omp-muted">该引擎不支持 HTML 预览（capability: html）。</div>
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
      <div v-else class="omp-muted">该引擎不支持增强产物读取（capability: enhancement）。</div>
    </div>
  </div>
  <div v-else class="empty-state"><div class="spinner" /> 加载运行详情…</div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue';
import { api } from '../../api/index.js';
import { renderMarkdown } from '../../utils/markdown.js';

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

const allTabs = [
  { key: 'overview', label: '概览' },
  { key: 'events', label: '执行证明' },
  { key: 'reports', label: '报告', cap: 'report' },
  { key: 'html', label: 'HTML 预览', cap: 'html' },
  { key: 'enhancement', label: '增强产物', cap: 'enhancement' },
];

/** Capability-driven tab filtering — engines expose only what they implement. */
const visibleTabs = computed(() => allTabs.filter((t) => !t.cap || props.capabilities.includes(t.cap)));

const enhArtifacts = [
  { kind: 'coverage', label: 'E1 覆盖率', file: 'analysis_coverage.json' },
  { kind: 'derived', label: 'E2 衍生特征', file: 'derived_features.json' },
  { kind: 'deep', label: 'E3 条件分析', file: 'deep_data_analysis.json' },
  { kind: 'graph', label: 'E3.5 关联图', file: 'association_graph.json' },
  { kind: 'bridge', label: 'E5 物理桥接', file: 'physics_bridge.json' },
  { kind: 'knowledge', label: 'E6 知识融合', file: 'enhanced_knowledge.json' },
  { kind: 'markdown', label: 'E7a MD 报告', file: 'enhanced_analysis.md' },
  { kind: 'review', label: 'E7c 审校', file: 'enhancement_html_review.json' },
  { kind: 'status', label: 'E8 状态', file: 'enhancement_status.json' },
];

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
    return new Date(iso).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
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
    detailError.value = `读取报告失败：${e.message}`;
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
    detailError.value = `读取增强产物失败：${e.message}`;
  }
}

async function loadHtml() {
  htmlSrc.value = '';
  detailError.value = '';
  try {
    htmlSrc.value = api.harnessHtmlUrl(props.harnessId, props.name, htmlMode.value);
  } catch (e) {
    detailError.value = `HTML 加载失败：${e.message}`;
  }
}

watch(htmlMode, loadHtml);

async function load() {
  detailError.value = '';
  try {
    run.value = await api.harnessRun(props.harnessId, props.name);
  } catch (e) {
    detailError.value = `加载运行失败：${e.message}`;
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
