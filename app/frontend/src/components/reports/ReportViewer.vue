<template>
  <div class="report-viewer">
    <div class="toolbar">
      <div class="toolbar-left">
        <a class="breadcrumb-root" @click="goToList">Reports</a>
        <template v-if="selectedRun">
          <span class="breadcrumb-sep">/</span>
          <a class="breadcrumb-path breadcrumb-active" v-if="reportContent || optimizerContent" @click="goToFiles">
            {{ formatRunName(selectedRun) }}
          </a>
          <span class="breadcrumb-current" v-else>{{ formatRunName(selectedRun) }}</span>
          <template v-if="reportContent || optimizerContent">
            <span class="breadcrumb-sep">/</span>
            <span class="breadcrumb-current">{{ activeTab === 'optimizer' ? 'Optimizer' : 'Report' }}</span>
          </template>
        </template>
      </div>
      <div class="toolbar-right">
        <button class="btn" @click="loadRuns" :disabled="loadingRuns">
          {{ loadingRuns ? 'Loading...' : 'Refresh' }}
        </button>
        <button
          v-if="selectedRun && reportContent"
          class="btn btn-primary"
          @click="downloadReport"
        >Download Report</button>
      </div>
    </div>

    <!-- Run selector -->
    <div class="card" v-if="!selectedRun">
      <div class="card-title">Available Diagnostic Reports</div>
      <div v-if="loadingRuns" class="empty-state">
        <div class="spinner" style="width:24px;height:24px;border-width:2px;"></div>
        <p>Loading runs...</p>
      </div>
      <div v-else-if="runs.length === 0" class="empty-state">
        <p>No diagnostic reports found. Run a diagnosis first from the Diagnose tab.</p>
      </div>
      <div v-else class="run-list">
        <div
          v-for="run in runs"
          :key="run.name"
          class="run-item"
          @click="openRun(run)"
        >
          <div class="run-icon">
            <span v-if="run.hasReport">📋</span>
            <span v-else>📁</span>
          </div>
          <div class="run-info">
            <div class="run-name">{{ formatRunName(run.name) }}</div>
            <div class="run-meta">
              <span>{{ formatDate(run.created) }}</span>
              <span v-if="run.hasReport" class="badge badge-green">Report</span>
              <span v-if="run.hasOptimizer" class="badge badge-purple">Optimizer</span>
              <span v-if="!run.hasReport && !run.hasOptimizer" class="badge badge-yellow">No Output</span>
            </div>
          </div>
          <div class="run-actions">
            <button class="btn btn-sm" @click.stop="openRun(run)">View</button>
            <button
              v-if="run.hasReport"
              class="btn btn-sm btn-primary"
              @click.stop="openRun(run)"
            >Read Report</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Run workspace files -->
    <div class="card" v-if="selectedRun && !reportContent">
      <div class="card-title">
        <span>Workspace Files</span>
        <button class="btn btn-sm btn-primary" @click="loadReport(selectedRun)" :disabled="loadingReport" style="margin-left:auto">
          {{ loadingReport ? 'Loading...' : 'Load Report' }}
        </button>
      </div>
      <div v-if="loadingFiles" class="empty-state">
        <div class="spinner"></div>
        <p>Loading files...</p>
      </div>
      <div v-else-if="runFiles.length === 0" class="empty-state">
        <p>No files in this run workspace.</p>
      </div>
      <div v-else class="file-tree">
        <div v-for="file in runFiles" :key="file.path" class="file-tree-item">
          <span class="file-tree-icon">{{ fileIcon(file.ext) }}</span>
          <span class="file-tree-name">{{ file.path }}</span>
          <span class="file-tree-size">{{ formatSize(file.size) }}</span>
        </div>
      </div>
    </div>

    <!-- Report content -->
    <div class="card report-card" v-if="reportContent || optimizerContent">
      <div class="card-title">
        <span>{{ activeTab === 'optimizer' ? 'Optimizer Suggestions' : 'Diagnostic Report' }}</span>
        <div style="margin-left:auto;display:flex;gap:6px;">
          <button class="btn btn-sm" :class="{ 'btn-active': viewRaw }" @click="viewRaw = !viewRaw">{{ viewRaw ? 'View Rendered' : 'View Raw' }}</button>
          <button class="btn btn-sm" @click="copyReport">Copy</button>
          <button
            class="btn btn-sm"
            @click="showChartPanel = !showChartPanel"
          >{{ showChartPanel ? '📊 Hide' : '📊 Charts' }}</button>
        </div>
      </div>
      <div class="report-tabs" v-if="hasOptimizer">
        <button
          :class="['tab-btn', { active: activeTab === 'report' }]"
          @click="activeTab = 'report'"
        >Report</button>
        <button
          :class="['tab-btn', { active: activeTab === 'optimizer' }]"
          @click="activeTab = 'optimizer'"
        >Optimizer</button>
      </div>
      <div class="report-body" v-if="activeTab === 'report' && !viewRaw" v-html="renderedReport"></div>
      <pre class="report-raw" v-if="activeTab === 'report' && viewRaw">{{ reportContent }}</pre>
      <div class="report-body" v-if="activeTab !== 'report' && !viewRaw" v-html="renderedOptimizer"></div>
      <pre class="report-raw" v-if="activeTab !== 'report' && viewRaw">{{ optimizerContent }}</pre>
    </div>

    <!-- Chart panel -->
    <div v-if="showChartPanel && chartData" class="card" style="margin-top:12px">
      <div class="card-title" style="display:flex;align-items:center;justify-content:space-between">
        <span>📊 Interactive Charts</span>
        <button class="btn btn-sm" @click="showChartPanel = false">Close</button>
      </div>
      <div class="chart-grid">
        <div v-if="chartData.heatmap" class="chart-cell chart-cell-full">
          <div class="card-title" style="font-size:13px">Correlation Matrix</div>
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
            title="Confidence Score"
            unit="%"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue';
import { api } from '../../api/index.js';
import { marked } from 'marked';
import DOMPurify from 'dompurify';
import { HeatmapChart, GaugeChart } from '../charts/index.js';

const props = defineProps({
  autoRunId: { type: String, default: null },
  targetRunName: { type: String, default: null },
});

const runs = ref([]);
const loadingRuns = ref(false);
const selectedRun = ref(null);
const reportContent = ref(null);
const optimizerContent = ref(null);
const hasOptimizer = ref(false);
const activeTab = ref('report');
const viewRaw = ref(false);
const loadingReport = ref(false);
const runFiles = ref([]);
const loadingFiles = ref(false);

const showChartPanel = ref(false);
const chartData = ref(null);

onMounted(() => {
  loadRuns();
});

watch(() => props.autoRunId, (newId) => {
  if (newId) {
    loadRuns().then(() => {
      const match = runs.value.find(r => r.name.endsWith(newId) || r.run_id === newId);
      if (match) openRun(match);
    });
  }
});

watch(() => props.targetRunName, (name) => {
  if (name) {
    const requestedName = name;
    selectedRun.value = name;
    reportContent.value = null;
    optimizerContent.value = null;
    hasOptimizer.value = false;
    activeTab.value = 'report';
    loadingFiles.value = true;
    api.listWorkspaceFiles(name).then(files => {
      if (selectedRun.value === requestedName) runFiles.value = files;
    }).catch(() => {
      if (selectedRun.value === requestedName) runFiles.value = [];
    }).finally(() => {
      if (selectedRun.value === requestedName) loadingFiles.value = false;
    });
    loadingReport.value = true;
    api.getReport(name).then(data => {
      if (selectedRun.value === requestedName) reportContent.value = data.content;
      if (selectedRun.value === requestedName) {
        fetchChartData(`workspace/diagnostic-runs/${requestedName}`);
      }
    }).catch(() => {
      if (selectedRun.value === requestedName) reportContent.value = '# Report Not Found\n\nThe report file could not be loaded.';
    }).finally(() => {
      if (selectedRun.value === requestedName) loadingReport.value = false;
    });
    api.getOptimizer(name).then(data => {
      if (selectedRun.value === requestedName) {
        optimizerContent.value = data.content;
        hasOptimizer.value = true;
      }
    }).catch(() => {
      if (selectedRun.value === requestedName) hasOptimizer.value = false;
    });
  }
}, { immediate: true });

async function loadRuns() {
  loadingRuns.value = true;
  try {
    runs.value = await api.listWorkspace();
  } catch (err) {
    console.error('Failed to load runs:', err);
  } finally {
    loadingRuns.value = false;
  }
}

function goToList() {
  selectedRun.value = null;
  reportContent.value = null;
  optimizerContent.value = null;
  hasOptimizer.value = false;
  activeTab.value = 'report';
  runFiles.value = [];
}

function goToFiles() {
  reportContent.value = null;
  optimizerContent.value = null;
  hasOptimizer.value = false;
  activeTab.value = 'report';
}

async function openRun(run) {
  const requestedName = run.name;
  selectedRun.value = run.name;
  reportContent.value = null;
  optimizerContent.value = null;
  hasOptimizer.value = false;
  activeTab.value = 'report';

  loadingFiles.value = true;
  try {
    const files = await api.listWorkspaceFiles(run.name);
    if (selectedRun.value === requestedName) runFiles.value = files;
  } catch {
    if (selectedRun.value === requestedName) runFiles.value = [];
  } finally {
    if (selectedRun.value === requestedName) loadingFiles.value = false;
  }

  if (run.hasReport) {
    await loadReport(run.name);
  }
  if (run.hasOptimizer) {
    await loadOptimizer(run.name);
  }
}

async function loadReport(runName) {
  const requestedName = runName;
  loadingReport.value = true;
  try {
    const data = await api.getReport(runName);
    if (selectedRun.value === requestedName) reportContent.value = data.content;
  } catch (err) {
    console.error('Failed to load report:', err);
    if (selectedRun.value === requestedName) reportContent.value = '# Report Not Found\n\nThe report file could not be loaded.';
  } finally {
    if (selectedRun.value === requestedName) loadingReport.value = false;
  }
}

async function loadOptimizer(runName) {
  const requestedName = runName;
  try {
    const data = await api.getOptimizer(runName);
    if (selectedRun.value === requestedName) {
      optimizerContent.value = data.content;
      hasOptimizer.value = true;
    }
  } catch {
    if (selectedRun.value === requestedName) {
      optimizerContent.value = null;
      hasOptimizer.value = false;
    }
  }
}

function downloadReport() {
  const content = activeTab.value === 'optimizer' ? optimizerContent.value : reportContent.value;
  if (!content || !selectedRun.value) return;
  const ext = activeTab.value === 'optimizer' ? 'optimizer.md' : 'report.md';
  const blob = new Blob([content], { type: 'text/markdown' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `diagnostic-${ext}-${selectedRun.value}.md`;
  a.click();
  URL.revokeObjectURL(url);
}

async function copyReport() {
  if (!reportContent.value) return;
  try {
    await navigator.clipboard.writeText(reportContent.value);
  } catch {
    const ta = document.createElement('textarea');
    ta.value = reportContent.value;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
  }
}

async function fetchChartData(runDir) {
  if (!runDir) return;
  try {
    const dirName = runDir.replace('workspace/diagnostic-runs/', '');
    const res = await fetch(`/api/analysis/chart-data/${encodeURIComponent(dirName)}`);
    const json = await res.json();
    if (json.success && json.data) chartData.value = json.data;
  } catch (err) {
    console.error('Chart fetch failed:', err);
  }
}

function rewriteImageUrls(html, runName) {
  if (!runName) return html;
  return html.replace(
    /(<img\s[^>]*src=")([^"]+)(")/g,
    (match, prefix, src, suffix) => {
      if (src.startsWith('http') || src.startsWith('data:') || src.startsWith('/')) return match;
      return `${prefix}/api/files/workspace/asset/${encodeURIComponent(runName)}/${src}${suffix}`;
    }
  );
}

function renderMarkdown(content, runName) {
  if (!content) return '';
  const raw = marked(content, { breaks: true, gfm: true });
  const withImages = rewriteImageUrls(raw, runName);
  return DOMPurify.sanitize(withImages, {
    ALLOWED_TAGS: ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'br', 'hr',
      'ul', 'ol', 'li', 'blockquote', 'pre', 'code', 'em', 'strong',
      'a', 'img', 'table', 'thead', 'tbody', 'tr', 'th', 'td',
      'span', 'div', 'details', 'summary', 'figure', 'figcaption'],
    ALLOWED_ATTR: ['href', 'src', 'alt', 'class', 'id', 'target', 'rel', 'loading'],
  });
}

const renderedReport = computed(() => renderMarkdown(reportContent.value, selectedRun.value));
const renderedOptimizer = computed(() => renderMarkdown(optimizerContent.value, selectedRun.value));

function formatRunName(name) {
  const match = name.match(/^(\d{4})(\d{2})(\d{2})(\d{1,2})(\d{2})(\d{1,2})[._]\s*(.+)/);
  if (match) {
    const [, y, mo, d, hh, mm, ss, label] = match;
    return `${label} (${y}-${mo}-${d} ${hh}:${mm})`;
  }
  // Fallback: try UUID-suffix format (scene_abc12345)
  const uuidMatch = name.match(/^(.+?)_([a-f0-9]{8})$/);
  if (uuidMatch) {
    return uuidMatch[1].replace(/_/g, ' ');
  }
  return name.replace(/_/g, ' ');
}

function formatDate(dateStr) {
  try {
    return new Date(dateStr).toLocaleString();
  } catch {
    return dateStr;
  }
}

function fileIcon(ext) {
  const icons = {
    '.md': '📝', '.json': '📋', '.csv': '📊', '.png': '🖼️',
    '.jpg': '🖼️', '.svg': '🖼️', '.py': '🐍', '.mjs': '📦',
    '.txt': '📄', '.html': '🌐',
  };
  return icons[ext] || '📄';
}

function formatSize(bytes) {
  if (!bytes) return '0 B';
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}
</script>

<style scoped>
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.toolbar-left { display: flex; align-items: center; gap: 6px; }

.breadcrumb-root {
  font-size: 16px;
  font-weight: 600;
  color: var(--text);
  cursor: pointer;
  text-decoration: none;
  transition: color 0.15s;
}
.breadcrumb-root:hover { color: var(--accent); }

.breadcrumb-sep {
  color: var(--text2);
  font-size: 13px;
}

.breadcrumb-path {
  font-size: 13px;
  color: var(--text2);
  cursor: pointer;
  text-decoration: none;
  transition: color 0.15s;
}
.breadcrumb-path:hover { color: var(--accent); }

.breadcrumb-active {
  color: var(--text2);
}

.breadcrumb-current {
  font-size: 13px;
  color: var(--text);
  font-weight: 500;
}

.toolbar-right { display: flex; gap: 8px; }

.run-list { display: flex; flex-direction: column; gap: 8px; }

.run-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  cursor: pointer;
  transition: all 0.15s;
}

.run-item:hover { border-color: var(--accent); }

.run-icon { font-size: 20px; flex-shrink: 0; }

.run-info { flex: 1; min-width: 0; }

.run-name {
  font-size: 14px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.run-meta {
  font-size: 11px;
  color: var(--text2);
  display: flex;
  gap: 8px;
  margin-top: 2px;
  align-items: center;
}

.run-actions { display: flex; gap: 6px; flex-shrink: 0; }

.file-tree { display: flex; flex-direction: column; gap: 4px; }

.file-tree-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: var(--surface2);
  border-radius: 4px;
  font-size: 13px;
}

.file-tree-icon { flex-shrink: 0; font-size: 14px; }

.file-tree-name {
  flex: 1;
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: 12px;
  color: var(--text);
}

.file-tree-size {
  font-size: 11px;
  color: var(--text2);
  flex-shrink: 0;
}

.report-card { max-width: 100%; }

.report-tabs {
  display: flex;
  gap: 0;
  border-bottom: 2px solid var(--border);
  margin-bottom: 16px;
}

.tab-btn {
  padding: 8px 16px;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  cursor: pointer;
  color: var(--text2);
  font-size: 13px;
  font-weight: 500;
}

.tab-btn.active {
  color: var(--accent);
  border-bottom-color: var(--accent);
}

.tab-btn:hover {
  color: var(--text);
}

.report-body {
  padding: 20px 0;
  line-height: 1.8;
  font-size: 14px;
  color: var(--text);
}

/* Headings */
.report-body :deep(h1) {
  font-size: 24px;
  font-weight: 800;
  margin: 32px 0 16px;
  padding-bottom: 10px;
  border-bottom: 2px solid var(--border);
  color: #fff;
  letter-spacing: -0.3px;
}

.report-body :deep(h2) {
  font-size: 19px;
  font-weight: 700;
  margin: 28px 0 12px;
  padding-bottom: 6px;
  border-bottom: 1px solid rgba(48, 54, 61, 0.6);
  color: var(--text);
  letter-spacing: -0.2px;
}

.report-body :deep(h3) {
  font-size: 16px;
  font-weight: 600;
  margin: 20px 0 8px;
  color: var(--text);
}

.report-body :deep(h4) {
  font-size: 14px;
  font-weight: 600;
  margin: 16px 0 6px;
  color: var(--text2);
}

/* Paragraphs */
.report-body :deep(p) {
  margin: 10px 0;
  color: var(--text);
  line-height: 1.8;
}

/* Lists */
.report-body :deep(ul), .report-body :deep(ol) {
  margin: 10px 0;
  padding-left: 24px;
  color: var(--text);
}

.report-body :deep(li) {
  margin: 6px 0;
  line-height: 1.7;
}

.report-body :deep(li)::marker {
  color: var(--accent);
}

/* Inline code */
.report-body :deep(code) {
  background: rgba(88, 166, 255, 0.1);
  padding: 2px 8px;
  border-radius: 4px;
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 13px;
  color: var(--accent);
  border: 1px solid rgba(88, 166, 255, 0.15);
}

/* Code blocks */
.report-body :deep(pre) {
  background: var(--surface2);
  padding: 16px 20px;
  border-radius: var(--radius);
  overflow-x: auto;
  margin: 14px 0;
  border: 1px solid var(--border);
}

.report-body :deep(pre code) {
  background: none;
  padding: 0;
  color: var(--text);
  border: none;
  font-size: 13px;
  line-height: 1.6;
}

/* Blockquotes */
.report-body :deep(blockquote) {
  border-left: 3px solid var(--accent);
  margin: 14px 0;
  padding: 10px 20px;
  color: var(--text2);
  background: rgba(88, 166, 255, 0.04);
  border-radius: 0 var(--radius) var(--radius) 0;
  font-style: italic;
}

/* Tables */
.report-body :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 16px 0;
  font-size: 13px;
  border-radius: var(--radius);
  overflow: hidden;
  border: 1px solid var(--border);
}

.report-body :deep(th) {
  background: var(--surface2);
  padding: 10px 14px;
  text-align: left;
  font-weight: 600;
  border-bottom: 2px solid var(--border);
  color: var(--text);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.report-body :deep(td) {
  padding: 10px 14px;
  border-bottom: 1px solid rgba(48, 54, 61, 0.5);
  color: var(--text);
}

.report-body :deep(tr:hover td) {
  background: rgba(88, 166, 255, 0.04);
}

.report-body :deep(tr:last-child td) {
  border-bottom: none;
}

/* Strong */
.report-body :deep(strong) {
  font-weight: 700;
  color: #fff;
}

/* Em */
.report-body :deep(em) {
  color: var(--text2);
  font-style: italic;
}

/* Links */
.report-body :deep(a) {
  color: var(--accent);
  text-decoration: none;
  border-bottom: 1px solid transparent;
  transition: border-color 0.15s;
}

.report-body :deep(a:hover) {
  border-bottom-color: var(--accent);
}

/* HR */
.report-body :deep(hr) {
  border: none;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--border), transparent);
  margin: 28px 0;
}

/* Images — the key upgrade */
.report-body :deep(img) {
  max-width: 100%;
  border-radius: var(--radius);
  margin: 16px 0;
  border: 1px solid var(--border);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
  display: block;
}

/* Figure wrapper for images with alt text as caption */
.report-body :deep(p:has(img)) {
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 16px;
  margin: 20px 0;
  text-align: center;
}

.report-body :deep(p:has(img)) img {
  margin: 0 auto 10px;
}

/* Caption text below image (the alt text shows as a separate element) */
.report-body :deep(p:has(img)) img::after {
  content: attr(alt);
}

/* Details/summary */
.report-body :deep(details) {
  margin: 12px 0;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
}

.report-body :deep(summary) {
  padding: 10px 14px;
  cursor: pointer;
  font-weight: 600;
  background: var(--surface2);
  color: var(--text);
  font-size: 13px;
}

.report-body :deep(summary:hover) {
  background: rgba(88, 166, 255, 0.06);
}

.report-body :deep(details > *:not(summary)) {
  padding: 0 14px;
}

/* Raw markdown view */
.report-raw {
  padding: 20px;
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 13px;
  line-height: 1.7;
  color: var(--text);
  white-space: pre-wrap;
  word-break: break-word;
  overflow-x: auto;
  max-height: 80vh;
  overflow-y: auto;
}

.btn-active {
  background: var(--accent);
  color: #fff;
  border-color: var(--accent);
}

.chart-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-top: 12px;
}
.chart-cell { min-height: 300px; }
.chart-cell-full { grid-column: 1 / -1; }
.chart-cell-half { grid-column: span 1; }
</style>
