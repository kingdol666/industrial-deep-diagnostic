<template>
  <div :class="['app-shell', { 'app-shell-collapsed': sidebarCollapsed }]">
    <aside class="app-sidebar">
      <div class="app-brand">
        <div class="app-brand-mark">ID</div>
        <div class="app-brand-copy">
          <div class="app-brand-kicker">Enterprise Workspace</div>
          <div class="app-brand-title">Industrial Deep Diagnostic</div>
          <div class="app-brand-subtitle">工业数据诊断与知识协同工作台</div>
        </div>
        <button
          class="app-sidebar-toggle"
          type="button"
          :title="sidebarCollapsed ? '展开侧边栏' : '折叠侧边栏'"
          @click="toggleSidebar"
        >
          {{ sidebarCollapsed ? '›' : '‹' }}
        </button>
      </div>

      <nav class="app-nav" aria-label="Primary">
        <button
          v-for="tab in visibleTabs"
          :key="tab.key"
          :class="['app-nav-item', { active: currentTab === tab.key }]"
          :title="tab.label"
          @click="currentTab = tab.key"
        >
          <span class="app-nav-icon">{{ tab.icon }}</span>
          <span class="app-nav-copy">
            <span class="app-nav-label">{{ tab.label }}</span>
            <span class="app-nav-caption">{{ tab.caption }}</span>
          </span>
        </button>
      </nav>

      <div class="app-sidebar-footer">
        <div class="app-harness" role="group" aria-label="Engine harness">
          <button
            type="button"
            class="app-harness-btn"
            :class="{ active: harness === 'claude' }"
            title="使用内置 Claude Code 引擎发起实时诊断"
            @click="selectHarness('claude')"
          >
            <span class="app-harness-icon">⌘</span>
            <span class="app-harness-copy">
              <span class="app-harness-label">Claude Code</span>
              <span class="app-harness-sub">SDK 实时引擎</span>
            </span>
          </button>
          <button
            type="button"
            class="app-harness-btn"
            :class="{ active: harness === 'omp' }"
            title="浏览 OMP 代理管线原生产出的运行结果"
            @click="selectHarness('omp')"
          >
            <span class="app-harness-icon">⛭</span>
            <span class="app-harness-copy">
              <span class="app-harness-label">OMP Engine</span>
              <span class="app-harness-sub">RPC 原生桥接</span>
            </span>
          </button>
        </div>
        <div class="app-presence" :class="wsStatusClass">
          <span class="app-presence-dot"></span>
          <span>{{ wsStatusText }}</span>
        </div>
        <div class="app-sidebar-note">
          <span class="app-sidebar-note-label">Theme</span>
          <span class="app-sidebar-note-value">Follow System</span>
        </div>
        <div class="app-sidebar-note" v-if="analysisTargetLabel">
          <span class="app-sidebar-note-label">Selection</span>
          <span class="app-sidebar-note-value">{{ analysisTargetLabel }}</span>
        </div>
      </div>
    </aside>

    <section class="app-body">
      <header class="app-topbar">
        <div class="app-topbar-copy">
          <div class="app-topbar-kicker">{{ activeTabMeta.kicker }}</div>
          <h1 class="app-topbar-title">{{ activeTabMeta.title }}</h1>
          <p class="app-topbar-subtitle">{{ activeTabMeta.description }}</p>
        </div>

        <div class="app-topbar-meta">
          <span class="app-pill">
            <span class="app-pill-dot" :class="wsStatusClass"></span>
            {{ wsStatusText }}
          </span>
          <span class="app-pill app-pill-soft">v4.2</span>
        </div>
      </header>

      <main :class="['app-content', contentClass]">
        <div v-if="currentTab === 'data'" class="app-view-frame">
          <DataBrowser
            @select-file="onSelectFile"
            @select-folder="onSelectFolder"
            @select-files="onSelectFiles"
          />
        </div>

        <DiagnosisView
          v-else-if="currentTab === 'diagnose'"
          :analysisTarget="analysisTarget"
          :autoRunId="autoOpenRunId"
          @started="onDiagnosisStarted"
          @view-report="onViewReport"
          @go-data="currentTab = 'data'"
        />

        <ChatView v-else-if="currentTab === 'chat'" />

        <div v-else-if="currentTab === 'reports'" class="app-view-frame">
          <ReportViewer
            :auto-run-id="autoOpenRunId"
            :target-run-name="openReportPath"
          />
        </div>

        <div v-else-if="currentTab === 'history'" class="app-view-frame">
          <HistoryList
            @open-report="onOpenReport"
            @continue-run="onContinueRun"
          />
        </div>

        <div v-else-if="currentTab === 'omp'" class="app-view-frame">
          <OmpRunsView />
        </div>
      </main>
    </section>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import DataBrowser from './components/data/DataBrowser.vue';
import DiagnosisView from './components/diagnosis/DiagnosisView.vue';
import ChatView from './components/chat/ChatView.vue';
import ReportViewer from './components/reports/ReportViewer.vue';
import HistoryList from './components/history/HistoryList.vue';
import OmpRunsView from './components/omp/OmpRunsView.vue';
import { useDiagnosisRealtimeStore } from './stores/diagnosisRealtimeStore.js';

const currentTab = ref('data');
const analysisTarget = ref(null);
const autoOpenRunId = ref(null);
const openReportPath = ref(null);
const sidebarCollapsed = ref(false);
const harness = ref('claude'); // 'claude' | 'omp' — user-selectable engine

const { state: rtState, init, teardown } = useDiagnosisRealtimeStore();

const wsStatusClass = computed(() => {
  if (rtState.wsConnected && (rtState.wsStatus === 'ready' || rtState.wsStatus === 'connected')) return 'ws-ok';
  if (rtState.wsStatus === 'connecting') return 'ws-connecting';
  if (rtState.reconnectAttempts > 0 && !rtState.wsConnected) return 'ws-reconnecting';
  return 'ws-offline';
});

const wsStatusText = computed(() => {
  if (rtState.wsConnected && (rtState.wsStatus === 'ready' || rtState.wsStatus === 'connected')) return 'Realtime Connected';
  if (rtState.wsStatus === 'connecting') return 'Connecting';
  if (rtState.reconnectAttempts > 0 && !rtState.wsConnected) return 'Reconnecting';
  if (rtState.wsStatus === 'idle') return 'Waiting';
  return 'Disconnected';
});

const tabs = [
  { key: 'data', label: 'Data', icon: '◫', kicker: 'Data Workspace', title: '数据接入与选择', description: '上传工业数据、组织目录，并将目标数据送入后续诊断流程。', caption: 'Upload and select industrial datasets' },
  { key: 'diagnose', label: 'Diagnose', icon: '◎', kicker: 'Diagnostic Run', title: '实时诊断工作台', description: '查看诊断阶段、证据链、图表和交互式追问，像操作一个实时分析会话一样工作。', caption: 'Live root-cause analysis and recovery' },
  { key: 'chat', label: 'Chat', icon: '⌘', kicker: 'Conversation Studio', title: '会话与诊断协同聊天', description: '统一承载普通 Chat 与 Diagnose session，对话、续聊、配置和上下文在同一工作区内完成。', caption: 'Resume chats and diagnose sessions' },
  { key: 'reports', label: 'Reports', icon: '▣', kicker: 'Artifact Review', title: '报告与审计产物', description: '阅读 Markdown 报告、图表和优化审计结果，快速定位结论和关键证据。', caption: 'Read reports and review artifacts' },
  { key: 'history', label: 'History', icon: '◌', kicker: 'Execution Ledger', title: '历史运行记录', description: '按运行状态回看诊断历史、日志与会话，并继续失败或暂停的任务。', caption: 'Track historical runs and outcomes' },
];

// OMP harness tab — visible only when the OMP engine is selected
const ompTab = {
  key: 'omp', label: 'OMP Runs', icon: '⛭', kicker: 'OMP Harness Bridge',
  title: 'OMP 原生运行浏览',
  description: '通过 OMP RPC 桥读取原生管线产物：运行状态、执行证明、报告与增强深挖结果。',
  caption: 'Browse native OMP pipeline outputs',
};

const visibleTabs = computed(() =>
  harness.value === 'omp' ? [...tabs.slice(0, 5), ompTab] : tabs
);

const activeTabMeta = computed(() => visibleTabs.value.find(tab => tab.key === currentTab.value) || visibleTabs.value[0]);

const contentClass = computed(() => ({
  'app-content-chat': currentTab.value === 'chat',
  'app-content-diagnose': currentTab.value === 'diagnose',
}));

const analysisTargetLabel = computed(() => {
  const target = analysisTarget.value;
  if (!target) return '';
  if (target.mode === 'file') return target.file?.name || '1 file selected';
  if (target.mode === 'folder') return target.name || 'Folder selected';
  if (target.mode === 'multi') return `${target.files?.length || 0} files selected`;
  return 'Selection ready';
});

function loadSidebarState() {
  try {
    sidebarCollapsed.value = localStorage.getItem('idd.sidebarCollapsed') === '1';
    const savedHarness = localStorage.getItem('idd.harness');
    if (savedHarness === 'omp' || savedHarness === 'claude') {
      harness.value = savedHarness;
      if (savedHarness === 'omp' && currentTab.value !== 'omp') currentTab.value = 'omp';
    }
  } catch {}
}

function selectHarness(next) {
  harness.value = next;
  try {
    localStorage.setItem('idd.harness', next);
  } catch {}
  if (next === 'omp') {
    currentTab.value = 'omp';
  } else if (currentTab.value === 'omp') {
    currentTab.value = 'data';
  }
}

function toggleSidebar() {
  sidebarCollapsed.value = !sidebarCollapsed.value;
  try {
    localStorage.setItem('idd.sidebarCollapsed', sidebarCollapsed.value ? '1' : '0');
  } catch {}
}

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

onMounted(() => {
  loadSidebarState();
  init();
});
onUnmounted(() => teardown());
</script>

<style>
@import './styles/global.css';
</style>
