<template>
  <AuthView v-if="!authed" @authed="onAuthed" />
  <div v-else :class="['app-shell', { 'app-shell-collapsed': sidebarCollapsed }]">
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
        <div v-if="authUser" class="app-userbox">
          <div class="app-userbox-info">
            <span class="app-userbox-name">{{ authUser.username }}</span>
            <span class="app-userbox-role">{{ authUser.role === 'admin' ? $t('auth.roleAdmin') : $t('auth.roleUser') }}</span>
          </div>
          <button class="app-userbox-logout" type="button" :title="$t('auth.logoutTitle')" @click="logout">{{ $t('auth.logout') }}</button>
        </div>

        <!-- 执行引擎选择：14 个引擎若平铺成一堵墙就无法扫读。
             改为「当前引擎读数 + 可展开清单」：状态点、名称、副标题各自成列。 -->
        <div class="app-engine" :class="{ open: engineListOpen }">
          <button
            type="button"
            class="app-engine-current"
            :title="harnessTitle(activeHarnessMeta)"
            @click="engineListOpen = !engineListOpen"
          >
            <span class="app-engine-icon">{{ harnessIcon(activeHarnessMeta) }}</span>
            <span class="app-engine-copy">
              <span class="ip-label">{{ $t('sidebar.engine') }}</span>
              <span class="app-engine-name">{{ activeHarnessMeta.name }}</span>
            </span>
            <span class="app-engine-state" :class="isHarnessOffline(harness) ? 'off' : 'on'">
              {{ isHarnessOffline(harness) ? $t('sidebar.offline') : $t('sidebar.ready') }}
            </span>
            <span class="app-engine-caret">{{ engineListOpen ? '▾' : '▸' }}</span>
          </button>

          <div v-if="engineListOpen" class="app-engine-list ip-scroll">
            <button
              v-for="h in harnessList"
              :key="h.id"
              type="button"
              class="app-engine-row"
              :class="{ active: harness === h.id, offline: isHarnessOffline(h.id) }"
              :title="harnessTitle(h)"
              @click="selectHarness(h.id)"
            >
              <span class="app-engine-dot" :class="isHarnessOffline(h.id) ? 'off' : 'on'"></span>
              <span class="app-engine-row-name">{{ h.name }}</span>
              <span class="app-engine-row-sub">{{ harnessSub(h) }}</span>
            </button>
          </div>
        </div>

        <div class="app-presence" :class="wsStatusClass">
          <span class="app-presence-dot"></span>
          <span>{{ wsStatusText }}</span>
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
          {{ $t('lang.switch') }}
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
          :harness-name="activeHarnessMeta.name"
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

        <div v-else-if="currentTab === 'ontology'" class="app-view-frame ontology-frame">
          <OntologyView />
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
import OntologyView from './components/ontology/OntologyView.vue';
import { useDiagnosisRealtimeStore } from './stores/diagnosisRealtimeStore.js';
import { api, getToken, setToken, setStoredUser, getStoredUser } from './api/index.js';
import AuthView from './components/auth/AuthView.vue';
import { toggleLocale } from './i18n/index.js';

const { t, tm } = useI18n();

// ─── 认证状态门禁 ───
const authed = ref(!!getToken());
const authUser = ref(getStoredUser());
function onAuthed(user) {
  authUser.value = user;
  authed.value = true;
  // 登录成功后（重）建立实时通道：携带 token 的 WS 连接
  teardown();
  init();
  refreshHarnesses();
}
function onUnauthorized() {
  authed.value = false;
  authUser.value = null;
  teardown();
}
function logout() {
  setToken('');
  setStoredUser(null);
  authUser.value = null;
  authed.value = false;
  teardown();
}

const currentTab = ref('data');
const analysisTarget = ref(null);
const autoOpenRunId = ref(null);
const openReportPath = ref(null);
const sidebarCollapsed = ref(false);
const engineListOpen = ref(false);
const harness = ref('claude'); // default engine id; list refreshed from registry
const harnessList = ref([]); // [{id, name, kind, description, capabilities}] from /api/harness
const harnessAvailability = ref({}); // id -> available (from /api/harness/availability)
const defaultHarnessId = ref(null); // server-resolved best-adapted available engine

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
  { key: 'ontology', label: t('tabs.ontology.label'), icon: '⬡', kicker: t('tabs.ontology.kicker'), title: t('tabs.ontology.title'), description: t('tabs.ontology.description'), caption: t('tabs.ontology.caption') },
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

const activeHarnessSupportsRuns = computed(() =>
  (activeHarnessMeta.value.capabilities || []).includes('runs')
);

// 本体页与 History 都必须常驻 —— 早先的 slice(0, 5) 在加入 Ontology 后把 History 挤出了导航栏，
// 用户会以为历史记录被删了。引擎专属的 runs 页作为附加项追加在末尾。
const visibleTabs = computed(() => (
  activeHarnessSupportsRuns.value ? [...tabs.value, ompTab.value] : tabs.value
));

const activeTabMeta = computed(() => visibleTabs.value.find(tab => tab.key === currentTab.value) || visibleTabs.value[0]);

const contentClass = computed(() => ({
  'app-content-chat': currentTab.value === 'chat',
  'app-content-diagnose': currentTab.value === 'diagnose',
  'app-content-ontology': currentTab.value === 'ontology',
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
    if (activeHarnessSupportsRuns.value && currentTab.value !== 'omp') currentTab.value = 'omp';
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
    // 可用性探测（服务器端缓存）— 未安装的引擎灰化显示；采纳服务端默认引擎
    try {
      const availability = await api.harnessAvailability();
      harnessAvailability.value = Object.fromEntries(
        (availability || []).map((a) => [a.id, !!a.available]),
      );
      const defaultEntry = (availability || []).find((a) => a.default === true);
      defaultHarnessId.value = defaultEntry?.id || null;
      // 无本地保存的选择时 → 采用服务端解析的默认引擎（适配最好的已装引擎）
      if (!localStorage.getItem('idd.harness') && defaultEntry) {
        harness.value = defaultEntry.id;
        try { localStorage.setItem('idd.harness', defaultEntry.id); } catch {}
      }
      // 已保存的引擎不可用 → 切到默认可用引擎，避免"选中即 409"
      if (harnessAvailability.value[harness.value] === false && defaultEntry) {
        harness.value = defaultEntry.id;
        try { localStorage.setItem('idd.harness', defaultEntry.id); } catch {}
      }
    } catch { harnessAvailability.value = {}; }
  } catch {
    harnessList.value = [];
  }
}

// ── Harness 按钮元数据（图标 / 可用性 / 副标题）──
const HARNESS_ICONS = {
  claude: '⌘', omp: '⛭', mock: '▶', codex: '⌥', dsh: '◇', opencode: '◐',
  gemini: '✦', copilot: '⎇', cursor: '▮', crush: '▚', goose: 'ƒ', qwen: '⌗',
  pi: 'π', hermes: '☲',
};

function harnessIcon(h) {
  return HARNESS_ICONS[h.id] || (h.name || h.id || '?').charAt(0).toUpperCase();
}

function isHarnessOffline(id) {
  return harnessAvailability.value[id] === false;
}

function harnessSub(h) {
  if (harnessAvailability.value[h.id] === false) return t('sidebar.engineUnavailable');
  if (defaultHarnessId.value === h.id) return t('sidebar.defaultEngine');
  if ((h.capabilities || []).includes('live')) return t('sidebar.sdkEngine');
  return t('sidebar.rpcBridge');
}

function harnessTitle(h) {
  const desc = h.description || h.name;
  return isHarnessOffline(h.id) ? `${desc} — ${t('sidebar.engineUnavailableTitle')}` : desc;
}

function selectHarness(next) {
  harness.value = next;
  try {
    localStorage.setItem('idd.harness', next);
  } catch {}
  if (activeHarnessSupportsRuns.value) {
    currentTab.value = 'omp';
  } else if (currentTab.value === 'omp') {
    currentTab.value = 'diagnose';
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
  window.addEventListener('auth:unauthorized', onUnauthorized);
  if (authed.value) {
    refreshHarnesses();
    init();
  }
});
onUnmounted(() => {
  window.removeEventListener('auth:unauthorized', onUnauthorized);
  teardown();
});
</script>

<style>
@import './styles/global.css';
</style>
