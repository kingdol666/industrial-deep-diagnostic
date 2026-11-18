<template>
  <!-- 会话探针（GET /api/auth/me）未出结果前先渲染启动态：cookie 会话下
       "已登录/未登录" 只有问过服务端才知道，直接渲染登录页会先闪一下门槛。 -->
  <div v-if="!authReady" class="app-boot" role="status" aria-live="polite">
    <span class="app-boot-dots" aria-hidden="true"><i></i><i></i><i></i></span>
    <span class="app-boot-label">{{ $t('auth.booting') }}</span>
  </div>
  <AuthView v-else-if="!authed" :boot-notice="authNotice" @authed="onAuthed" />
  <div v-else :class="['app-shell', { 'app-shell-collapsed': sidebarCollapsed, 'app-shell-nav-open': mobileNavOpen }]">
    <aside class="app-sidebar">
      <div class="app-brand">
        <div class="app-brand-mark">ID</div>
        <div class="app-brand-copy">
          <div class="app-brand-kicker">{{ $t('common.appKicker') }}</div>
          <div class="app-brand-title">{{ $t('common.appName') }}</div>
          <div class="app-brand-subtitle">{{ $t('common.appSubtitle') }}</div>
        </div>
        <!-- Phone only: the rail becomes a command bar and the nav lives
             behind this toggle, so content is not pushed below a 500px band. -->
        <button
          class="app-nav-toggle"
          type="button"
          :aria-expanded="mobileNavOpen"
          :title="mobileNavOpen ? $t('sidebar.collapseSidebar') : $t('sidebar.expandSidebar')"
          @click="mobileNavOpen = !mobileNavOpen"
        >
          <span class="app-nav-toggle-bars" aria-hidden="true"></span>
        </button>
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
          :data-testid="`nav-${tab.key}`"
          :class="['app-nav-item', { active: currentTab === tab.key }]"
          :title="tab.label"
          @click="selectTab(tab.key)"
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
            <button class="app-userbox-name" type="button" data-testid="open-settings" :title="$t('tabs.settings.title')" @click="selectTab('settings')">{{ authUser.username }}</button>
            <span class="app-userbox-role">{{ authUser.role === 'admin' ? $t('auth.roleAdmin') : $t('auth.roleUser') }}</span>
          </div>
          <button class="app-userbox-logout" data-testid="logout" type="button" :title="$t('auth.logoutTitle')" @click="logout">{{ $t('auth.logout') }}</button>
        </div>

        <!-- 执行引擎选择：真下拉列表。14 个引擎全部列出；启动探测判定的
             不可用引擎置灰禁选（探针错误进 title），可用的原生承载诊断与
             聊天。面板向上弹出（选择器位于侧栏底部），点击外部 / Esc 关闭。 -->
        <div ref="engineBox" class="app-engine" :class="{ open: engineListOpen }">
          <button
            type="button"
            class="app-engine-current"
            :aria-expanded="engineListOpen"
            aria-haspopup="listbox"
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
            <span class="app-engine-caret">{{ engineListOpen ? '▾' : '▴' }}</span>
          </button>

          <div v-if="engineListOpen" class="app-engine-menu ip-scroll" role="listbox" :aria-label="$t('sidebar.engine')">
            <button
              v-for="h in harnessList"
              :key="h.id"
              type="button"
              role="option"
              class="app-engine-row"
              :class="{ active: harness === h.id, offline: isHarnessOffline(h.id) }"
              :disabled="isHarnessOffline(h.id)"
              :aria-selected="harness === h.id"
              :title="harnessTitle(h)"
              @click="selectHarness(h.id)"
            >
              <span class="app-engine-dot" :class="isHarnessOffline(h.id) ? 'off' : 'on'"></span>
              <span class="app-engine-row-name">{{ h.name }}</span>
              <span class="app-engine-row-sub">{{ harnessSub(h) }}</span>
            </button>
          </div>
        </div>

        <div class="app-sidebar-note" v-if="analysisTargetLabel">
          <span class="app-sidebar-note-label">{{ $t('common.selection') }}</span>
          <span class="app-sidebar-note-value">{{ analysisTargetLabel }}</span>
        </div>
        <!-- Presence and the language switch share one footer row: stacked, the
             lone 「中」 button read as an orphan at the rail's dead end. -->
        <div class="app-footer-row">
          <div class="app-presence" :class="wsStatusClass">
            <span class="app-presence-dot"></span>
            <span>{{ wsStatusText }}</span>
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

        <ChatView v-else-if="currentTab === 'chat'" :harness="harness" :harness-name="activeHarnessMeta.name" />

        <div v-else-if="currentTab === 'reports'" class="app-view-frame">
          <ReportViewer
            :auto-run-id="autoOpenRunId"
            :target-run-name="openReportPath"
          />
        </div>

        <div v-else-if="currentTab === 'results'" class="app-view-frame">
          <ResultsLibrary @open-report="onOpenReport" />
        </div>

        <div v-else-if="currentTab === 'memory'" class="app-view-frame">
          <LineMemoryPanel @open-report="onOpenReport" @open-run="onOpenRun" />
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

        <div v-else-if="currentTab === 'settings'" class="app-view-frame">
          <SettingsView />
        </div>
      </main>
    </section>
  </div>

  <!-- F1 兜底：子树（含异步加载的视图 chunk）渲染出错时，给出可操作的兜底，
       绝不留白屏。文案刻意不走 i18n —— i18n 本身出错时它还要能显示。 -->
  <div v-if="fatalError" class="app-fatal" role="alert">
    <div class="app-fatal-card">
      <div class="app-fatal-kicker">UI ERROR</div>
      <p class="app-fatal-message">
        界面渲染出错，受影响的部分已中止。<br>
        Something went wrong while rendering the UI.
      </p>
      <pre v-if="fatalError.detail" class="app-fatal-detail">{{ fatalError.detail }}</pre>
      <button class="app-fatal-reload" type="button" @click="reloadPage">
        重新加载 · Reload
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, onErrorCaptured, defineAsyncComponent } from 'vue';
import { useI18n } from 'vue-i18n';
import { useDiagnosisRealtimeStore } from './stores/diagnosisRealtimeStore.js';
import { api } from './api/index.js';
import AuthView from './components/auth/AuthView.vue';
import { toggleLocale } from './i18n/index.js';

// ─── F2b：视图级代码分割 ───
// 每个视图独立 chunk：首屏（登录/数据页）不再为九个页面的依赖买单（ECharts
// 只在真正打开图表视图时才下载）。AuthView 刻意保持静态导入 —— 它是所有人
// 进入的第一道门，异步化意味着"开门"本身要先等一次网络往返，且 chunk 加载
// 失败会连登录页都看不到；它很小，代价不值得。
const DataBrowser = defineAsyncComponent(() => import('./components/data/DataBrowser.vue'));
const DiagnosisView = defineAsyncComponent(() => import('./components/diagnosis/DiagnosisView.vue'));
const ChatView = defineAsyncComponent(() => import('./components/chat/ChatView.vue'));
const ReportViewer = defineAsyncComponent(() => import('./components/reports/ReportViewer.vue'));
const HistoryList = defineAsyncComponent(() => import('./components/history/HistoryList.vue'));
const OmpRunsView = defineAsyncComponent(() => import('./components/harness/HarnessRunsView.vue'));
const OntologyView = defineAsyncComponent(() => import('./components/ontology/OntologyView.vue'));
// 结果库 / 产线记忆 / 设置（run-management + line-memory 融合新增）走同一条
// 异步 chunk 规则 —— 设置页的 i18n 体积不小，没必要进首屏。
const ResultsLibrary = defineAsyncComponent(() => import('./components/results/ResultsLibrary.vue'));
const LineMemoryPanel = defineAsyncComponent(() => import('./components/memory/LineMemoryPanel.vue'));
const SettingsView = defineAsyncComponent(() => import('./components/settings/SettingsView.vue'));

const { t } = useI18n();

// ─── 认证状态门禁（HttpOnly cookie 会话）───
// 页面不再持有任何会话凭据：cookie 由服务端下发，JS 读不到。登录态的唯一
// 权威来源是启动时的一次 GET /api/auth/me；用户对象只驻留内存（刷新后由
// /me 重建，无需 localStorage 影子副本）。
const authed = ref(false);
const authReady = ref(false);   // /me 探针是否已出结果（false → 渲染启动态）
const authUser = ref(null);
const authNotice = ref('');     // 非 401 启动失败的原因，展示在登录页

function onAuthed(user) {
  authUser.value = user;
  authed.value = true;
  authNotice.value = '';
  // 登录成功后（重）建立实时通道：cookie 会话下 WS 握手自动携带凭据
  teardown();
  init();
  refreshHarnesses();
}
function onUnauthorized() {
  authed.value = false;
  authUser.value = null;
  authNotice.value = '';   // 会话过期是正常路径，登录页不需要多余解释
  teardown();
}
async function logout() {
  try {
    await api.authLogout();
  } catch (err) {
    // HttpOnly cookie 只能由服务端清除：请求失败通常意味着后端已不可达，
    // 本地照常退出到登录页（会话 cookie 将随后端重启/过期自然失效）。
    console.warn('[auth] logout request failed:', err?.message || err);
  }
  authUser.value = null;
  authed.value = false;
  authNotice.value = '';
  teardown();
}

/**
 * 启动探针 —— 会话的权威判定，整个生命周期只跑一次：
 *   200 且带 user → 已登录，进入控制台；
 *   200 但无 user / 401 → 未登录，展示登录页（登录页本身不含任何猜测）；
 *   其他失败（后端不可达 / 5xx）→ 同样落在登录页，但把原因显示出来。
 * 任何结果都不会触发 /me 重试 —— 不存在探针循环。
 *
 * AUTH_ENABLED=0 的开发模式：后端视一切请求为"未认证但放行"，/me 可能返回
 * 401/500/空体，而普通受保护接口全部成功。因此探针失败后只做一次开放模式
 * 判定（调一次 /api/harness）：成功 → 按开发者身份直接进入控制台（无用户
 * 框）；失败 → 回登录页。两种模式各自最多多一次请求。
 */
async function detectOpenMode() {
  try {
    const list = await api.listHarnesses();
    authed.value = true;
    authUser.value = null; // 开放模式下没有用户对象，用户框/登出按钮隐藏
    return Array.isArray(list) ? list : [];
  } catch {
    return null;
  }
}

async function bootAuth() {
  let openModeHarnesses = null;
  let failure = null;
  try {
    const me = await api.authMe();
    const user = me?.user || me || null;
    if (user && (user.username || user.id)) {
      authUser.value = user;
      authed.value = true;
    } else {
      openModeHarnesses = await detectOpenMode();
    }
  } catch (err) {
    failure = err;
    openModeHarnesses = await detectOpenMode();
  } finally {
    authReady.value = true;
  }
  if (authed.value) {
    refreshHarnesses(openModeHarnesses);
    init();
  } else if (failure && failure.status !== 401) {
    // 401 = 正常的"未登录"，登录页无需解释；其余失败给出原因（服务端消息或
    // 网络层不可达提示）。只提示一次，不做自动重试。
    authNotice.value = failure.message && failure.status
      ? failure.message
      : t('auth.bootUnreachable');
  }
}

// ─── F1：白屏兜底（根级捕获）───
// 任何子树（含异步视图 chunk 加载失败）抛错都在壳内兜底展示，绝不留白屏。
// 返回 false 阻止错误继续冒泡到 app.config.errorHandler —— 那里还有一层纯
// DOM 兜底（main.js），专治连 App 自身渲染都失败、这份模板根本没机会渲染的
// 极端情况。
const fatalError = ref(null);
onErrorCaptured((err, _instance, info) => {
  console.error('[App] captured render error:', info, err);
  if (!fatalError.value) {
    fatalError.value = { detail: err?.message || String(err ?? ''), info };
  }
  return false;
});

function reloadPage() {
  window.location.reload();
}

const currentTab = ref('data');
const analysisTarget = ref(null);
const autoOpenRunId = ref(null);
const openReportPath = ref(null);
const sidebarCollapsed = ref(false);
const mobileNavOpen = ref(false);   // phones only: nav drawer
const engineListOpen = ref(false);
const engineBox = ref(null);
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
  { key: 'results', label: t('tabs.results.label'), icon: '▤', kicker: t('tabs.results.kicker'), title: t('tabs.results.title'), description: t('tabs.results.description'), caption: t('tabs.results.caption') },
  { key: 'memory', label: t('tabs.memory.label'), icon: '◈', kicker: t('tabs.memory.kicker'), title: t('tabs.memory.title'), description: t('tabs.memory.description'), caption: t('tabs.memory.caption') },
  { key: 'ontology', label: t('tabs.ontology.label'), icon: '⬡', kicker: t('tabs.ontology.kicker'), title: t('tabs.ontology.title'), description: t('tabs.ontology.description'), caption: t('tabs.ontology.caption') },
  { key: 'history', label: t('tabs.history.label'), icon: '◌', kicker: t('tabs.history.kicker'), title: t('tabs.history.title'), description: t('tabs.history.description'), caption: t('tabs.history.caption') },
  { key: 'settings', label: t('tabs.settings.label'), icon: '⚙', kicker: t('tabs.settings.kicker'), title: t('tabs.settings.title'), description: t('tabs.settings.description'), caption: t('tabs.settings.caption') },
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

/**
 * @param {Array|null} prefetched 开放模式探针已取回的一份引擎列表（复用，
 *   避免开发模式下启动时对 /api/harness 打两次）。
 */
async function refreshHarnesses(prefetched = null) {
  try {
    const list = prefetched || await api.listHarnesses();
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
  if (isHarnessOffline(next)) return; // 不可用引擎禁选 —— 永不产生 409 惊喜
  harness.value = next;
  try {
    localStorage.setItem('idd.harness', next);
  } catch {}
  engineListOpen.value = false;
  if (activeHarnessSupportsRuns.value) {
    currentTab.value = 'omp';
  } else if (currentTab.value === 'omp') {
    currentTab.value = 'diagnose';
  }
}

// 下拉的关闭语义：点击面板外 / Esc 收起。监听器常驻但先做廉价短路，
// 面板未打开时直接返回。
function onGlobalPointerDown(e) {
  if (!engineListOpen.value) return;
  if (engineBox.value && !engineBox.value.contains(e.target)) engineListOpen.value = false;
}
function onGlobalKeydown(e) {
  if (engineListOpen.value && e.key === 'Escape') engineListOpen.value = false;
}

function toggleSidebar() {
  sidebarCollapsed.value = !sidebarCollapsed.value;
  try {
    localStorage.setItem('idd.sidebarCollapsed', sidebarCollapsed.value ? '1' : '0');
  } catch {}
}

/**
 * Every tab change goes through here so the phone drawer closes itself. The
 * drawer is an overlay: leaving it open after a selection would hide the page
 * the user just asked for.
 */
function selectTab(key) {
  currentTab.value = key;
  mobileNavOpen.value = false;
}

// The drawer is meaningless once the viewport is wide enough for the rail.
// Without this, resizing up and back down leaves the nav stuck open.
function onViewportResize() {
  if (window.innerWidth > PHONE_MAX && mobileNavOpen.value) mobileNavOpen.value = false;
}
const PHONE_MAX = 700;

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

// report_path is persisted with the platform separator (backslashes on
// Windows). Splitting on '/' alone made the run-dir segment undefined there,
// so the Report button landed on the run list instead of the opened report.
function runDirFromReportPath(reportPath) {
  const parts = String(reportPath || '').split(/[/\\]/);
  return parts[parts.length - 2] || '';
}

function onViewReport(reportPath) {
  if (reportPath) openReportPath.value = runDirFromReportPath(reportPath);
  currentTab.value = 'reports';
}

function onOpenReport(reportPath) {
  if (reportPath) openReportPath.value = runDirFromReportPath(reportPath);
  currentTab.value = 'reports';
}

// 产线记忆 → 溯源 run:直接用 runId 打开 Reports（ReportViewer 的 auto-run-id）。
function onOpenRun(runId) {
  if (runId) autoOpenRunId.value = runId;
  currentTab.value = 'reports';
}

onMounted(() => {
  loadSidebarState();
  window.addEventListener('auth:unauthorized', onUnauthorized);
  window.addEventListener('resize', onViewportResize);
  document.addEventListener('pointerdown', onGlobalPointerDown);
  document.addEventListener('keydown', onGlobalKeydown);
  // 会话判定异步进行：探针返回前保持启动态，返回后才决定登录页 / 控制台。
  bootAuth();
});
onUnmounted(() => {
  window.removeEventListener('auth:unauthorized', onUnauthorized);
  window.removeEventListener('resize', onViewportResize);
  document.removeEventListener('pointerdown', onGlobalPointerDown);
  document.removeEventListener('keydown', onGlobalKeydown);
  teardown();
});
</script>

<style>
@import './styles/global.css';

/* ─── 启动态：/me 探针进行中（与登录页同底，避免任何色彩跳变）─── */
.app-boot {
  min-height: 100vh;
  min-height: 100dvh;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 14px;
  background-color: var(--bg);
  background-image:
    linear-gradient(var(--bg-grid) 1px, transparent 1px),
    linear-gradient(90deg, var(--bg-grid) 1px, transparent 1px);
  background-size: 32px 32px;
}

.app-boot-dots {
  display: inline-flex;
  gap: 6px;
}

.app-boot-dots i {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--accent);
  animation: app-boot-blink 1.2s ease-in-out infinite;
}

.app-boot-dots i:nth-child(2) { animation-delay: 0.18s; }
.app-boot-dots i:nth-child(3) { animation-delay: 0.36s; }

@keyframes app-boot-blink {
  0%, 100% { opacity: 0.25; }
  50% { opacity: 1; }
}

.app-boot-label {
  font-family: var(--font-mono);
  font-size: var(--fs-label);
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--text3);
}

/* ─── F1 兜底遮罩：错误绝不等于白屏 ─── */
.app-fatal {
  position: fixed;
  inset: 0;
  z-index: 9999;
  display: grid;
  place-items: center;
  padding: 24px;
  background: var(--bg);
}

.app-fatal-card {
  width: 100%;
  max-width: 460px;
  background: var(--surface);
  border: 1px solid var(--red-border);
  border-radius: var(--radius-sm);
  box-shadow: var(--shadow-lg), var(--inset-hi);
  padding: 22px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.app-fatal-kicker {
  font-family: var(--font-mono);
  font-size: var(--fs-micro);
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--red);
}

.app-fatal-message {
  font-size: var(--fs-sm);
  line-height: 1.55;
  color: var(--text2);
}

.app-fatal-detail {
  max-height: 160px;
  overflow: auto;
  margin: 0;
  padding: 8px 10px;
  background: var(--red-soft);
  border: 1px solid var(--red-border);
  border-radius: var(--radius-xs);
  color: var(--red);
  font-family: var(--font-mono);
  font-size: var(--fs-micro);
  white-space: pre-wrap;
  word-break: break-word;
}

.app-fatal-reload {
  align-self: flex-start;
  min-height: 34px;
  padding: 0 14px;
  border: 1px solid var(--accent-strong);
  border-radius: var(--radius-xs);
  background: var(--accent);
  color: #1a1408;
  font-family: var(--font-ui);
  font-size: var(--fs-sm);
  font-weight: 600;
  cursor: pointer;
  transition: background 0.14s ease, border-color 0.14s ease;
}

.app-fatal-reload:hover {
  background: var(--accent-bright);
  border-color: var(--accent);
}
</style>
