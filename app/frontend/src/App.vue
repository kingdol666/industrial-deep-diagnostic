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
import DataBrowser from './components/data/DataBrowser.vue';
import DiagnosisView from './components/diagnosis/DiagnosisView.vue';
import ReportViewer from './components/reports/ReportViewer.vue';
import HistoryList from './components/history/HistoryList.vue';

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
@import './styles/global.css';
</style>
