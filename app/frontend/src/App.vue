<template>
  <div :class="['app-shell', { 'app-shell-collapsed': sidebarCollapsed }]">
    <aside class="app-sidebar">
      <div class="app-brand">
        <div class="app-brand-mark">ID</div>
        <div class="app-brand-copy">
          <div class="app-brand-kicker">{{ $t('common.appKicker') }}</div>
          <div class="app-brand-title">{{ $t('common.appName') }}</div>
          <div class="app-brand-subtitle">{{ $t('common.appSubtitle') }}</div>
        </div>
        <button
          class="app-sidebar-toggle"
          type="button"
          :title="sidebarCollapsed ? $t('sidebar.expandSidebar') : $t('sidebar.collapseSidebar')"
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
            v-for="h in harnessList"
            :key="h.id"
            type="button"
            class="app-harness-btn"
            :class="{ active: harness === h.id }"
            :title="h.description"
            @click="selectHarness(h.id)"
          >
            <span class="app-harness-icon">{{ h.id === 'claude' ? '⌘' : '⛭' }}</span>
            <span class="app-harness-copy">
              <span class="app-harness-label">{{ h.name }}</span>
              <span class="app-harness-sub">{{ h.capabilities?.includes('live') ? $t('sidebar.sdkEngine') : $t('sidebar.rpcBridge') }}</span>
            </span>
          </button>
        </div>
        <div class="app-presence" :class="wsStatusClass">
          <span class="app-presence-dot"></span>
          <span>{{ wsStatusText }}</span>
        </div>
        <div class="app-sidebar-note">
          <span class="app-sidebar-note-label">{{ $t('common.theme') }}</span>
          <span class="app-sidebar-note-value">{{ $t('common.themeValue') }}</span>
        </div>
        <div class="app-sidebar-note" v-if="analysisTargetLabel">
          <span class="app-sidebar-note-label">{{ $t('common.selection') }}</span>
          <span class="app-sidebar-note-value">{{ analysisTargetLabel }}</span>
        </div>
        <button
          class="app-lang-toggle"
          type="button"
          :title="$t('lang.switchTo')"
          @click="onToggleLocale"
        >
          🌐 {{ $t('lang.switch') }}
        </button>
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
          :harness="harness"
          @started="onDiagnosisStarted"
          @view-report="onViewReport"
          @go-data="currentTab = 'data'"
        />

        <ChatView v-else-if="currentTab === 'chat'" :harness="harness" />

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
          <OmpRunsView
            :harness-id="harness"
            :harness-name="activeHarnessMeta.name"
            :capabilities="activeHarnessMeta.capabilities || []"
          />
        </div>
      </main>
    </section>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useI18n } from 'vue-i18n';
import DataBrowser from './components/data/DataBrowser.vue';
import DiagnosisView from './components/diagnosis/DiagnosisView.vue';
import ChatView from './components/chat/ChatView.vue';
import ReportViewer from './components/reports/ReportViewer.vue';
import HistoryList from './components/history/HistoryList.vue';
import OmpRunsView from './components/harness/HarnessRunsView.vue';
import { useDiagnosisRealtimeStore } from './stores/diagnosisRealtimeStore.js';
import { api } from './api/index.js';
import { toggleLocale } from './i18n/index.js';

const { t, tm } = useI18n();

const currentTab = ref('data');
const analysisTarget = ref(null);
const autoOpenRunId = ref(null);
const openReportPath = ref(null);
const sidebarCollapsed = ref(false);
const harness = ref('claude'); // default engine id; list refreshed from registry
const harnessList = ref([]); // [{id, name, kind, description, capabilities}] from /api/harness

const { state: rtState, init, teardown } = useDiagnosisRealtimeStore();

const wsStatusClass = computed(() => {
  if (rtState.wsConnected && (rtState.wsStatus === 'ready' || rtState.wsStatus === 'connected')) return 'ws-ok';
  if (rtState.wsStatus === 'connecting') return 'ws-connecting';
  if (rtState.reconnectAttempts > 0 && !rtState.wsConnected) return 'ws-reconnecting';
  return 'ws-offline';
});

const wsStatusText = computed(() => {
  if (rtState.wsConnected && (rtState.wsStatus === 'ready' || rtState.wsStatus === 'connected')) return t('ws.realtimeConnected');
  if (rtState.wsStatus === 'connecting') return t('ws.connecting');
  if (rtState.reconnectAttempts > 0 && !rtState.wsConnected) return t('ws.reconnecting');
  if (rtState.wsStatus === 'idle') return t('ws.waiting');
  return t('ws.disconnected');
});

const tabs = computed(() => [
  { key: 'data', label: t('tabs.data.label'), icon: '◫', kicker: t('tabs.data.kicker'), title: t('tabs.data.title'), description: t('tabs.data.description'), caption: t('tabs.data.caption') },
  { key: 'diagnose', label: t('tabs.diagnose.label'), icon: '◎', kicker: t('tabs.diagnose.kicker'), title: t('tabs.diagnose.title'), description: t('tabs.diagnose.description'), caption: t('tabs.diagnose.caption') },
  { key: 'chat', label: t('tabs.chat.label'), icon: '⌘', kicker: t('tabs.chat.kicker'), title: t('tabs.chat.title'), description: t('tabs.chat.description'), caption: t('tabs.chat.caption') },
  { key: 'reports', label: t('tabs.reports.label'), icon: '▣', kicker: t('tabs.reports.kicker'), title: t('tabs.reports.title'), description: t('tabs.reports.description'), caption: t('tabs.reports.caption') },
  { key: 'history', label: t('tabs.history.label'), icon: '◌', kicker: t('tabs.history.kicker'), title: t('tabs.history.title'), description: t('tabs.history.description'), caption: t('tabs.history.caption') },
]);

// OMP harness tab — visible only when the selected engine supports runs
const activeHarnessMeta = computed(() =>
  harnessList.value.find((h) => h.id === harness.value) || { id: harness.value, name: harness.value }
);

const ompTab = computed(() => ({
  key: 'omp', label: `${activeHarnessMeta.value.name} ${t('tabs.omp.runsSuffix')}`, icon: '⛭', kicker: t('tabs.omp.kicker'),
  title: `${activeHarnessMeta.value.name}${t('tabs.omp.titleSuffix')}`,
  description: `${t('tabs.omp.descriptionPre')} ${activeHarnessMeta.value.name} ${t('tabs.omp.descriptionMid')}`,
  caption: `${t('tabs.omp.captionPre')} ${activeHarnessMeta.value.name} ${t('tabs.omp.captionMid')}`,
}));

const visibleTabs = computed(() => {
  if (harness.value !== 'claude') {
    return [...tabs.value.slice(0, 5), ompTab.value];
  }
  return tabs.value;
});

const activeTabMeta = computed(() => visibleTabs.value.find(tab => tab.key === currentTab.value) || visibleTabs.value[0]);

const contentClass = computed(() => ({
  'app-content-chat': currentTab.value === 'chat',
  'app-content-diagnose': currentTab.value === 'diagnose',
}));

const analysisTargetLabel = computed(() => {
  const target = analysisTarget.value;
  if (!target) return '';
  if (target.mode === 'file') return target.file?.name || t('data.fileSelected');
  if (target.mode === 'folder') return target.name || t('data.folderSelected');
  if (target.mode === 'multi') return t('data.filesSelected', { count: target.files?.length || 0 });
  return t('data.selectionReady');
});

function loadSidebarState() {
  try {
    sidebarCollapsed.value = localStorage.getItem('idd.sidebarCollapsed') === '1';
    const savedHarness = localStorage.getItem('idd.harness');
    if (savedHarness) harness.value = savedHarness;
    if (harness.value !== 'claude' && currentTab.value !== 'omp') currentTab.value = 'omp';
  } catch {}
}

async function refreshHarnesses() {
  try {
    const list = await api.listHarnesses();
    harnessList.value = list;
    // Validate persisted selection against the registry
    if (!list.some((h) => h.id === harness.value)) {
      harness.value = list[0]?.id || 'claude';
      try { localStorage.setItem('idd.harness', harness.value); } catch {}
    }
  } catch {
    harnessList.value = [];
  }
}

function selectHarness(next) {
  harness.value = next;
  try {
    localStorage.setItem('idd.harness', next);
  } catch {}
  if (next !== 'claude') {
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

function onToggleLocale() {
  toggleLocale();
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
  refreshHarnesses();
  init();
});
onUnmounted(() => teardown());
</script>

<style>
@import './styles/global.css';
</style>
