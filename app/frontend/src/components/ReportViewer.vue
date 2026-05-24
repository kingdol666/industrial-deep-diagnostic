<template>
  <div class="report-viewer">
    <div class="toolbar">
      <div class="toolbar-left">
        <h3>Reports</h3>
        <span class="path-label" v-if="selectedRun">/ {{ selectedRun }}</span>
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
              <span v-if="run.hasReport" class="badge badge-green">Has Report</span>
              <span v-else class="badge badge-yellow">No Report</span>
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
        <button class="btn btn-sm" @click="selectedRun = null; reportContent = null">Back to Reports</button>
        <span style="margin-left:8px">Run: {{ formatRunName(selectedRun) }}</span>
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
      <div v-if="selectedRun" style="margin-top:16px">
        <button
          class="btn btn-primary"
          @click="loadReport(selectedRun)"
          :disabled="loadingReport"
        >{{ loadingReport ? 'Loading Report...' : 'Load Report' }}</button>
      </div>
    </div>

    <!-- Report content -->
    <div class="card report-card" v-if="reportContent">
      <div class="card-title">
        <button class="btn btn-sm" @click="selectedRun = null; reportContent = null">Back to Reports</button>
        <span style="margin-left:8px">Report: {{ formatRunName(selectedRun) }}</span>
        <button class="btn btn-sm" @click="copyReport" style="margin-left:auto">Copy</button>
      </div>
      <div class="report-body" v-html="renderedReport"></div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue';
import { api } from '../api.js';
import { marked } from 'marked';

const props = defineProps({
  autoRunId: { type: String, default: null },
  targetRunName: { type: String, default: null },
});

const runs = ref([]);
const loadingRuns = ref(false);
const selectedRun = ref(null);
const reportContent = ref(null);
const loadingReport = ref(false);
const runFiles = ref([]);
const loadingFiles = ref(false);

onMounted(() => {
  loadRuns();
});

watch(() => props.autoRunId, (newId) => {
  if (newId) {
    // Wait a bit for the report to be generated, then try to load it
    loadRuns();
  }
});

watch(() => props.targetRunName, (name) => {
  if (name) {
    selectedRun.value = name;
    reportContent.value = null;
    loadingFiles.value = true;
    api.listWorkspaceFiles(name).then(files => {
      runFiles.value = files;
    }).catch(() => {
      runFiles.value = [];
    }).finally(() => {
      loadingFiles.value = false;
    });
    loadingReport.value = true;
    api.getReport(name).then(data => {
      reportContent.value = data.content;
    }).catch(() => {
      reportContent.value = '# Report Not Found\n\nThe report file could not be loaded.';
    }).finally(() => {
      loadingReport.value = false;
    });
  }
});

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

async function openRun(run) {
  selectedRun.value = run.name;
  reportContent.value = null;

  loadingFiles.value = true;
  try {
    runFiles.value = await api.listWorkspaceFiles(run.name);
  } catch {
    runFiles.value = [];
  } finally {
    loadingFiles.value = false;
  }

  if (run.hasReport) {
    await loadReport(run.name);
  }
}

async function loadReport(runName) {
  loadingReport.value = true;
  try {
    const data = await api.getReport(runName);
    reportContent.value = data.content;
  } catch (err) {
    console.error('Failed to load report:', err);
    reportContent.value = '# Report Not Found\n\nThe report file could not be loaded.';
  } finally {
    loadingReport.value = false;
  }
}

function downloadReport() {
  if (!reportContent.value || !selectedRun.value) return;
  const blob = new Blob([reportContent.value], { type: 'text/markdown' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `diagnostic-report-${selectedRun.value}.md`;
  a.click();
  URL.revokeObjectURL(url);
}

async function copyReport() {
  if (!reportContent.value) return;
  try {
    await navigator.clipboard.writeText(reportContent.value);
  } catch {
    // fallback
    const ta = document.createElement('textarea');
    ta.value = reportContent.value;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
  }
}

const renderedReport = computed(() => {
  if (!reportContent.value) return '';
  return marked(reportContent.value, {
    breaks: true,
    gfm: true,
  });
});

function formatRunName(name) {
  // Convert timestamp-based names: 20260521080744._PVA-TEST-V3 → PVA-TEST-V3 (2026-05-21 08:07)
  const match = name.match(/^(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})[._]\s*(.+)/);
  if (match) {
    const [, y, m, d, hh, mm, ss, label] = match;
    return `${label} (${y}-${m}-${d} ${hh}:${mm})`;
  }
  return name;
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

.toolbar-left { display: flex; align-items: center; gap: 8px; }
.toolbar-left h3 { font-size: 16px; font-weight: 600; }

.path-label { color: var(--text2); font-size: 13px; }

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

.report-body {
  padding: 16px 0;
  line-height: 1.7;
  font-size: 14px;
}

.report-body :deep(h1) {
  font-size: 22px;
  font-weight: 700;
  margin: 24px 0 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border);
  color: var(--text);
}

.report-body :deep(h2) {
  font-size: 18px;
  font-weight: 600;
  margin: 20px 0 10px;
  color: var(--text);
}

.report-body :deep(h3) {
  font-size: 15px;
  font-weight: 600;
  margin: 16px 0 8px;
  color: var(--text);
}

.report-body :deep(p) { margin: 8px 0; color: var(--text); }

.report-body :deep(ul), .report-body :deep(ol) {
  margin: 8px 0;
  padding-left: 24px;
  color: var(--text);
}

.report-body :deep(li) { margin: 4px 0; }

.report-body :deep(code) {
  background: var(--surface2);
  padding: 2px 6px;
  border-radius: 3px;
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: 13px;
  color: var(--accent);
}

.report-body :deep(pre) {
  background: var(--surface2);
  padding: 16px;
  border-radius: var(--radius);
  overflow-x: auto;
  margin: 12px 0;
}

.report-body :deep(pre code) {
  background: none;
  padding: 0;
  color: var(--text);
}

.report-body :deep(blockquote) {
  border-left: 3px solid var(--accent);
  margin: 12px 0;
  padding: 4px 16px;
  color: var(--text2);
  background: rgba(88, 166, 255, 0.05);
  border-radius: 0 var(--radius) var(--radius) 0;
}

.report-body :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 12px 0;
  font-size: 13px;
}

.report-body :deep(th) {
  background: var(--surface2);
  padding: 8px 12px;
  text-align: left;
  font-weight: 600;
  border-bottom: 2px solid var(--border);
}

.report-body :deep(td) {
  padding: 8px 12px;
  border-bottom: 1px solid var(--border);
}

.report-body :deep(tr:hover td) {
  background: rgba(88, 166, 255, 0.03);
}

.report-body :deep(strong) { font-weight: 700; color: var(--text); }

.report-body :deep(a) {
  color: var(--accent);
  text-decoration: none;
}

.report-body :deep(a:hover) { text-decoration: underline; }

.report-body :deep(hr) {
  border: none;
  border-top: 1px solid var(--border);
  margin: 20px 0;
}

.report-body :deep(img) {
  max-width: 100%;
  border-radius: var(--radius);
  margin: 12px 0;
}
</style>
