<template>
  <div class="app">
    <header class="app-header">
      <div class="header-left">
        <h1 class="logo">Industrial Deep Diagnostic</h1>
        <span class="version">v4.2</span>
      </div>
      <nav class="header-nav">
        <button
          v-for="tab in tabs" :key="tab.key"
          :class="['nav-btn', { active: currentTab === tab.key }]"
          @click="currentTab = tab.key"
        >{{ tab.label }}</button>
      </nav>
    </header>
    <main class="app-main">
      <DataBrowser
        v-if="currentTab === 'data'"
        @select-file="onSelectFile"
        @select-folder="onSelectFolder"
        @select-files="onSelectFiles"
      />
      <DiagnosisView
        v-if="currentTab === 'diagnose'"
        :analysisTarget="analysisTarget"
        :autoRunId="autoOpenRunId"
        @started="onDiagnosisStarted"
        @view-report="onViewReport"
        @go-data="currentTab = 'data'"
      />
      <ReportViewer
        v-if="currentTab === 'reports'"
        :auto-run-id="autoOpenRunId"
        :target-run-name="openReportPath"
      />
      <HistoryList
        v-if="currentTab === 'history'"
        @open-report="onOpenReport"
        @continue-run="onContinueRun"
      />
    </main>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import DataBrowser from './components/DataBrowser.vue';
import DiagnosisView from './components/DiagnosisView.vue';
import ReportViewer from './components/ReportViewer.vue';
import HistoryList from './components/HistoryList.vue';

const currentTab = ref('data');
const analysisTarget = ref(null);
const autoOpenRunId = ref(null);
const openReportPath = ref(null);

const tabs = [
  { key: 'data', label: 'Data' },
  { key: 'diagnose', label: 'Diagnose' },
  { key: 'reports', label: 'Reports' },
  { key: 'history', label: 'History' },
];

function onSelectFile(file) {
  analysisTarget.value = { mode: 'file', file };
  currentTab.value = 'diagnose';
}

function onSelectFolder(folderInfo) {
  analysisTarget.value = { mode: 'folder', ...folderInfo };
  currentTab.value = 'diagnose';
}

function onSelectFiles(files) {
  analysisTarget.value = { mode: 'multi', files };
  currentTab.value = 'diagnose';
}

function onDiagnosisStarted(runId) {
  autoOpenRunId.value = runId;
}

function onContinueRun(runId) {
  autoOpenRunId.value = runId;
  currentTab.value = 'diagnose';
}

function onViewReport(reportPath) {
  if (reportPath) {
    const parts = reportPath.split('/');
    openReportPath.value = parts[parts.length - 2] || '';
  }
  currentTab.value = 'reports';
}

function onOpenReport(reportPath) {
  if (reportPath) {
    const parts = reportPath.split('/');
    openReportPath.value = parts[parts.length - 2] || '';
  }
  currentTab.value = 'reports';
}
</script>

<style>
:root {
  --bg: #0d1117;
  --surface: #161b22;
  --surface2: #1c2333;
  --border: #30363d;
  --text: #e6edf3;
  --text2: #8b949e;
  --accent: #58a6ff;
  --accent2: #1f6feb;
  --green: #3fb950;
  --red: #f85149;
  --yellow: #d29922;
  --purple: #bc8cff;
  --radius: 8px;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.5;
}

.app { min-height: 100vh; display: flex; flex-direction: column; }

.app-header {
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  padding: 0 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 56px;
  flex-shrink: 0;
}

.header-left { display: flex; align-items: center; gap: 10px; }

.logo {
  font-size: 18px;
  font-weight: 700;
  background: linear-gradient(135deg, var(--accent), var(--purple));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.version {
  font-size: 11px;
  color: var(--text2);
  background: var(--surface2);
  padding: 2px 8px;
  border-radius: 10px;
}

.header-nav { display: flex; gap: 4px; }

.nav-btn {
  background: transparent;
  border: none;
  color: var(--text2);
  padding: 8px 16px;
  border-radius: var(--radius);
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.15s;
}

.nav-btn:hover { color: var(--text); background: var(--surface2); }

.nav-btn.active {
  color: var(--accent);
  background: rgba(88, 166, 255, 0.1);
}

.app-main {
  flex: 1;
  overflow: auto;
  padding: 24px;
  max-width: 1400px;
  width: 100%;
  margin: 0 auto;
}

/* Shared component styles */
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 20px;
  margin-bottom: 16px;
}

.card-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface2);
  color: var(--text);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s;
  font-weight: 500;
}

.btn:hover { border-color: var(--accent); color: var(--accent); }

.btn-primary {
  background: var(--accent2);
  border-color: var(--accent2);
  color: #fff;
}

.btn-primary:hover { background: var(--accent); }

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-danger { border-color: var(--red); color: var(--red); }
.btn-danger:hover { background: rgba(248, 81, 73, 0.1); }

.btn-sm { padding: 4px 12px; font-size: 12px; }

.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 600;
}

.badge-green { background: rgba(63, 185, 80, 0.15); color: var(--green); }
.badge-yellow { background: rgba(210, 153, 34, 0.15); color: var(--yellow); }
.badge-red { background: rgba(248, 81, 73, 0.15); color: var(--red); }
.badge-blue { background: rgba(88, 166, 255, 0.15); color: var(--accent); }
.badge-purple { background: rgba(188, 140, 255, 0.15); color: var(--purple); }

input, textarea, select {
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 8px 12px;
  color: var(--text);
  font-size: 14px;
  width: 100%;
  transition: border-color 0.15s;
}

input:focus, textarea:focus, select:focus {
  outline: none;
  border-color: var(--accent);
}

textarea { resize: vertical; min-height: 80px; font-family: inherit; }

.empty-state {
  text-align: center;
  padding: 48px 24px;
  color: var(--text2);
}

.empty-state p { font-size: 14px; margin-top: 8px; }

.progress-bar {
  height: 4px;
  background: var(--surface2);
  border-radius: 2px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--accent2), var(--accent));
  border-radius: 2px;
  transition: width 0.3s;
}

.spinner {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.fade-enter-active, .fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: var(--text2); }
</style>
