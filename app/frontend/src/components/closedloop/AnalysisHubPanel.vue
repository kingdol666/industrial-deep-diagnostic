<template>
  <div class="cl-panel">
    <!-- ── 分析模式选择 ── -->
    <section class="cl-card">
      <h3>{{ $t('closedloop.hub.title') }}</h3>
      <p class="cl-card-desc">{{ $t('closedloop.hub.desc') }}</p>
      <div class="hub-modes">
        <button v-for="m in modes" :key="m.key" type="button"
                :class="['hub-mode', { active: mode === m.key }]" @click="mode = m.key">
          <span class="hub-mode-name">{{ $t(`closedloop.hub.mode.${m.key}`) }}</span>
          <span class="hub-mode-desc">{{ $t(`closedloop.hub.modeDesc.${m.key}`) }}</span>
          <span class="hub-mode-skill">{{ m.skill }}</span>
        </button>
      </div>

      <div class="cl-form" style="margin-top: 12px">
        <div class="cl-field">
          <label>{{ $t('closedloop.hub.dataCsv') }}</label>
          <input v-model="form.data_path" list="cl-data-paths-hub" placeholder="data/.../xxx.csv" />
          <datalist id="cl-data-paths-hub">
            <option v-for="p in dataPaths" :key="p" :value="p" />
          </datalist>
        </div>
        <div class="cl-field">
          <label>{{ $t('closedloop.stability.line') }}</label>
          <input v-model="form.line_id" placeholder="L1-extruder-206" />
        </div>
        <div class="cl-field">
          <label>{{ $t('closedloop.sentinel.timeCol') }}</label>
          <input v-model="form.time_col" placeholder="t" />
        </div>

        <template v-if="mode === 'stability'">
          <div class="cl-field">
            <label>{{ $t('closedloop.stability.start') }} · {{ $t('closedloop.common.optional') }}</label>
            <input v-model="form.start" placeholder="2026-10-01T08:00:00" />
          </div>
          <div class="cl-field">
            <label>{{ $t('closedloop.stability.end') }} · {{ $t('closedloop.common.optional') }}</label>
            <input v-model="form.end" placeholder="2026-10-01T20:00:00" />
          </div>
          <div class="cl-field">
            <label>ontology.json · {{ $t('closedloop.common.optional') }}</label>
            <input v-model="form.ontology_path" placeholder="data/.../ontology.json" />
          </div>
          <div class="cl-field">
            <label>sentinel baseline · {{ $t('closedloop.common.optional') }}</label>
            <input v-model="form.baseline_path" list="cl-baseline-paths-hub" />
            <datalist id="cl-baseline-paths-hub">
              <option v-for="b in baselines" :key="b.line" :value="b.baseline_path" />
            </datalist>
          </div>
        </template>

        <template v-else-if="mode === 'doe'">
          <div class="cl-field">
            <label>{{ $t('closedloop.stability.scene') }} · {{ $t('closedloop.common.optional') }}</label>
            <input v-model="form.scene" placeholder="scene_key" />
          </div>
          <div class="cl-field wide">
            <label>analysis_context JSON · {{ $t('closedloop.common.optional') }}</label>
            <textarea v-model="form.context_text" style="min-height: 64px"
                      placeholder='{"responses":["yield_pct"],"alpha":0.05}'></textarea>
          </div>
        </template>

        <template v-else-if="mode === 'sentinel'">
          <div class="cl-field">
            <label>sentinel baseline · {{ $t('closedloop.common.optional') }}</label>
            <input v-model="form.baseline_path" list="cl-baseline-paths-hub2" />
            <datalist id="cl-baseline-paths-hub2">
              <option v-for="b in baselines" :key="b.line" :value="b.baseline_path" />
            </datalist>
          </div>
        </template>
      </div>

      <div class="cl-actions">
        <button type="button" class="cl-btn" :disabled="busy" @click="run">
          {{ busy ? $t('closedloop.common.busy') : $t('closedloop.hub.run') }}
        </button>
        <span v-if="error" class="cl-alert error">{{ error }}</span>
      </div>
    </section>

    <!-- ── 实时控制台 ── -->
    <section v-if="consoleLines.length || busy" class="cl-card">
      <h3>{{ $t('closedloop.hub.console') }}</h3>
      <div ref="consoleBox" class="hub-console">
        <div v-for="(l, i) in consoleLines" :key="i" class="hub-line"
             :class="{ err: l.stream === 'stderr' }">
          <span class="hub-ts">{{ fmtTs(l.ts) }}</span>
          <span class="hub-stream">{{ l.stream }}</span>
          <span>{{ l.line }}</span>
        </div>
        <div v-if="!consoleLines.length" class="cl-empty">{{ $t('closedloop.hub.consoleEmpty') }}</div>
      </div>
      <div class="cl-kv" style="margin-top: 8px">
        <span>{{ $t('closedloop.common.status') }}: <b>{{ statusText }}</b></span>
        <span v-if="taskId">task: <b>{{ taskId }}</b></span>
      </div>
    </section>

    <!-- ── 结果视图 ── -->
    <section v-if="result" class="cl-card">
      <div class="hub-result-head">
        <h3>{{ $t('closedloop.hub.result') }}</h3>
        <div class="hub-tabs">
          <button v-for="t in resultTabs" :key="t.key" type="button"
                  :class="['hub-tab', { active: resultTab === t.key }]"
                  @click="resultTab = t.key">{{ $t(t.label) }}</button>
        </div>
      </div>

      <!-- 稳定性摘要 -->
      <div v-if="mode === 'stability' && summary" class="cl-kv" style="margin: 8px 0">
        <span>{{ $t('closedloop.stability.score') }}:
          <b>{{ summary.score }} · {{ summary.grade }} · {{ summary.label }}</b></span>
        <span>{{ $t('closedloop.stability.params') }}: <b>{{ summary.n_parameters_assessed }}</b></span>
      </div>
      <p v-if="mode === 'stability' && summary" class="hub-statement">{{ summary.statement }}</p>
      <div v-if="mode === 'doe' && doeSummary" class="cl-kv" style="margin: 8px 0">
        <span>mode: <b>{{ doeSummary.mode }}</b></span>
        <span v-if="doeSummary.headline">{{ doeSummary.headline }}</span>
        <span>windows: <b>{{ doeSummary.n_windows }}</b></span>
      </div>

      <!-- HTML 报告 -->
      <iframe v-if="resultTab === 'html' && result.htmlUrl" class="hub-frame"
              :src="result.htmlUrl" :title="$t('closedloop.hub.tabHtml')"></iframe>
      <p v-else-if="resultTab === 'html'" class="cl-empty">{{ $t('closedloop.hub.noHtml') }}</p>

      <!-- Markdown 报告 -->
      <div v-if="resultTab === 'md'" class="hub-md" v-html="mdHtml"></div>
      <p v-if="resultTab === 'md' && !mdHtml" class="cl-empty">{{ $t('closedloop.hub.noMd') }}</p>

      <!-- 产物清单 -->
      <div v-if="resultTab === 'artifacts'">
        <table v-if="result.artifacts?.length" class="cl-table">
          <thead><tr><th>#</th><th>artifact</th></tr></thead>
          <tbody>
            <tr v-for="(a, i) in result.artifacts" :key="a">
              <td class="num">{{ i + 1 }}</td><td>{{ a }}</td>
            </tr>
          </tbody>
        </table>
        <p v-else class="cl-empty">{{ $t('closedloop.common.none') }}</p>
      </div>

      <div class="cl-actions">
        <button v-if="result.htmlUrl" type="button" class="cl-btn small"
                @click="openUrl(result.htmlUrl)">{{ $t('closedloop.stability.openHtml') }}</button>
        <button v-if="result.mdUrl" type="button" class="cl-btn small ghost"
                @click="openUrl(result.mdUrl)">Markdown</button>
      </div>
    </section>

    <!-- ── 历史分析 ── -->
    <section class="cl-card">
      <h3>{{ $t('closedloop.hub.runsTitle') }}</h3>
      <table v-if="runs.length" class="cl-table">
        <thead><tr>
          <th>{{ $t('closedloop.hub.modeKind') }}</th>
          <th>task</th>
          <th>{{ $t('closedloop.common.status') }}</th>
          <th>{{ $t('closedloop.stability.generated') }}</th>
          <th></th>
        </tr></thead>
        <tbody>
          <tr v-for="r in runs" :key="r.kind + r.task_id">
            <td>{{ r.kind }}</td>
            <td class="strong">{{ r.task_id }}</td>
            <td>{{ r.status }}</td>
            <td>{{ shortTime(r.generated_at) }}</td>
            <td>
              <button v-if="r.report_url" type="button" class="cl-btn small ghost"
                      @click="openUrl(r.report_url)">HTML</button>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-else class="cl-empty">{{ $t('closedloop.common.none') }}</p>
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue';
import { api, authHeaders } from '../../api/index.js';
import { useI18n } from 'vue-i18n';
import { renderMarkdown } from '../../utils/markdown.js';

const { t } = useI18n();

const modes = [
  { key: 'stability', skill: 'industrial-line-stability-report' },
  { key: 'doe', skill: 'industrial-doe-analyzer' },
  { key: 'sentinel', skill: 'industrial-sentinel' },
];
const mode = ref('stability');
const busy = ref(false);
const error = ref('');
const taskId = ref(null);
const consoleLines = ref([]);
const consoleBox = ref(null);
const result = ref(null);
const resultTab = ref('html');
const summary = ref(null);
const doeSummary = ref(null);
const mdHtml = ref('');
const dataPaths = ref([]);
const baselines = ref([]);
const runs = ref([]);

const form = reactive({
  data_path: '', line_id: '', time_col: 't',
  start: '', end: '', ontology_path: '', baseline_path: '',
  scene: '', context_text: '',
});

const statusText = computed(() => {
  if (busy.value) return t('closedloop.common.running');
  if (result.value) return t('closedloop.common.completed');
  return '—';
});

const resultTabs = computed(() => {
  const tabs = [{ key: 'html', label: 'closedloop.hub.tabHtml' }];
  if (mode.value === 'stability') tabs.push({ key: 'md', label: 'closedloop.hub.tabMd' });
  tabs.push({ key: 'artifacts', label: 'closedloop.hub.tabArtifacts' });
  return tabs;
});

function fmtTs(ts) {
  return ts ? new Date(ts).toLocaleTimeString() : '';
}
function shortTime(v) {
  return v ? String(v).replace('T', ' ').slice(0, 16) : '—';
}
function openUrl(url) { window.open(url, '_blank', 'noopener'); }
function workspaceFileUrl(absPath) {
  if (!absPath) return null;
  const parts = String(absPath).replace(/\\/g, '/').split('/workspace/');
  return parts.length === 2 ? `/workspace-files/${parts[1]}` : null;
}

// fetch 流式消费 SSE（EventSource 无法带 Authorization 头）
async function consumeSSE(url, onEvent) {
  const res = await fetch(url, { headers: authHeaders() });
  if (!res.ok || !res.body) throw new Error(`stream ${res.status}`);
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = '';
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const chunks = buf.split('\n\n');
    buf = chunks.pop() ?? '';
    for (const chunk of chunks) {
      let event = 'message';
      let data = '';
      for (const line of chunk.split('\n')) {
        if (line.startsWith('event: ')) event = line.slice(7).trim();
        else if (line.startsWith('data: ')) data += line.slice(6);
      }
      if (data) {
        try { onEvent(event, JSON.parse(data)); } catch { /* ignore parse errors */ }
      }
    }
  }
}

function pushLine(entry) {
  consoleLines.value.push(entry);
  nextTick(() => {
    const box = consoleBox.value;
    if (box) box.scrollTop = box.scrollHeight;
  });
}

async function runStability() {
  const created = await api.lineReportRun({
    data_path: form.data_path,
    line_id: form.line_id || null,
    time_col: form.time_col || null,
    start: form.start || null,
    end: form.end || null,
    baseline_path: form.baseline_path || null,
    ontology_path: form.ontology_path || null,
    scene: form.scene || null,
  });
  taskId.value = created.task_id;
  await consumeSSE(`/api/line-report/tasks/${created.task_id}/stream`, (event, data) => {
    if (event === 'log') pushLine(data);
    if (event === 'done' && data.status === 'completed' && data.result?.report) {
      const r = data.result;
      summary.value = {
        score: r.report.conclusion?.score, grade: r.report.conclusion?.grade,
        label: r.report.conclusion?.label, statement: r.report.conclusion?.statement,
        n_parameters_assessed: r.report.conclusion?.n_parameters_assessed,
      };
      result.value = {
        htmlUrl: r.html_url, mdUrl: r.md_url,
        artifacts: ['stability_report.json', 'charts.json',
                    'line_stability_report.html', 'line_stability_report.md',
                    'html_selfcheck.json'],
      };
    }
  });
}

async function runDoe() {
  let context = null;
  if (form.context_text.trim()) {
    try { context = JSON.parse(form.context_text); }
    catch { throw new Error(t('closedloop.common.jsonInvalid')); }
  }
  const created = await api.doeAnalysisRun({
    data_path: form.data_path,
    time_col: form.time_col || null,
    scene: form.scene || null,
    context,
  });
  taskId.value = created.task_id;
  await consumeSSE(`/api/doe-analysis/tasks/${created.task_id}/stream`, (event, data) => {
    if (event === 'log') pushLine(data);
    if (event === 'done' && data.status === 'completed') {
      result.value = {
        htmlUrl: data.result?.report_url ?? null,
        mdUrl: null,
        artifacts: data.result?.artifacts ?? [],
      };
    }
  });
  const full = await api.doeAnalysisRunDetail(taskId.value);
  const c = full?.conclusions ?? {};
  doeSummary.value = {
    mode: c.doe_conclusion?.mode ?? null,
    headline: c.doe_conclusion?.headline ?? c.doe_conclusion?.summary ?? null,
    n_windows: (c.recommendations?.operating_windows ?? []).length,
  };
}

async function runSentinel() {
  const created = await api.sentinelWatch({
    data_path: form.data_path,
    baseline_path: form.baseline_path || null,
    time_col: form.time_col || null,
  });
  taskId.value = created.task_id;
  pushLine({ ts: Date.now(), stream: 'stdout', line: `[hub] 哨兵批筛任务 ${created.task_id} 已提交` });
  for (let i = 0; i < 120; i++) {
    const data = await api.sentinelTask(created.task_id);
    if (data && (data.status === 'completed' || data.status === 'failed')) {
      const reportUrl = workspaceFileUrl(data.result?.report_path);
      result.value = {
        htmlUrl: reportUrl, mdUrl: reportUrl,
        artifacts: data.result?.alert_path ? ['sentinel/alert.json', 'sentinel/watch_report.md'] : [],
      };
      resultTab.value = 'html';
      summary.value = {
        score: null, grade: null, label: data.alert_status ?? data.exit_code,
        statement: `exit_code=${data.exit_code} · alert_status=${data.alert_status ?? '—'} · `
          + `n_alerts=${data.result?.n_alerts ?? '—'}`,
      };
      pushLine({ ts: Date.now(), stream: 'stdout', line: `[hub] 哨兵任务完成 exit=${data.exit_code}` });
      return;
    }
    await new Promise((r) => setTimeout(r, 1500));
  }
  throw new Error('sentinel poll timeout');
}

async function run() {
  if (!form.data_path) return;
  busy.value = true;
  error.value = '';
  result.value = null;
  summary.value = null;
  doeSummary.value = null;
  mdHtml.value = '';
  resultTab.value = 'html';
  consoleLines.value = [];
  taskId.value = null;
  try {
    if (mode.value === 'stability') await runStability();
    else if (mode.value === 'doe') await runDoe();
    else await runSentinel();
    loadRuns();
  } catch (e) {
    error.value = e.message;
    pushLine({ ts: Date.now(), stream: 'stderr', line: `[hub] ${e.message}` });
  } finally { busy.value = false; }
}

async function loadMd() {
  if (mode.value !== 'stability' || !result.value?.mdUrl) { mdHtml.value = ''; return; }
  try {
    const res = await fetch(result.value.mdUrl);
    mdHtml.value = res.ok ? renderMarkdown(await res.text()) : '';
  } catch { mdHtml.value = ''; }
}

async function loadDataPaths() {
  try {
    const folders = await api.listData();
    const out = [];
    for (const f of (folders || []).slice(0, 40)) {
      const name = typeof f === 'string' ? f : (f.name || f.folder);
      if (!name || name.startsWith('.')) continue;
      try {
        const files = await api.listData(name);
        for (const file of (files || []).slice(0, 20)) {
          const fname = typeof file === 'string' ? file : (file.name || file.file);
          if (fname && /\.(csv|json)$/i.test(fname)) out.push(`data/${name}/${fname}`);
        }
      } catch { /* folder may be a plain file entry */ }
    }
    dataPaths.value = out;
  } catch { /* listing optional */ }
}

async function loadBaselines() {
  try {
    const data = await api.sentinelBaselines();
    baselines.value = Object.entries(data?.lines || {}).map(([line, entry]) => ({ line, ...entry }));
  } catch { baselines.value = []; }
}

async function loadRuns() {
  try {
    const [lineRuns, doeRuns] = await Promise.all([
      api.lineReportRuns().catch(() => []),
      api.doeAnalysisRuns().catch(() => []),
    ]);
    const map = (list, kind, urlKey) => (list || []).map((x) => ({
      kind, task_id: x.task_id, status: x.status ?? x.outcome ?? '—',
      generated_at: x.generated_at, report_url: x[urlKey] ?? null,
    }));
    runs.value = [
      ...map(lineRuns, 'stability', 'html_url'),
      ...map(doeRuns, 'doe', 'report_url'),
    ].slice(0, 30);
  } catch { runs.value = []; }
}

watch(resultTab, (tab) => { if (tab === 'md') loadMd(); });

onMounted(() => { loadDataPaths(); loadBaselines(); loadRuns(); });
</script>

<style scoped>
.hub-modes { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 10px; }
.hub-mode {
  appearance: none; text-align: left; cursor: pointer;
  background: var(--surface-soft); border: 1px solid var(--border-strong);
  border-radius: 10px; padding: 12px 14px; color: var(--text2);
  display: flex; flex-direction: column; gap: 4px;
}
.hub-mode:hover { border-color: var(--border-accent); }
.hub-mode.active { border-color: var(--accent); background: var(--accent-soft); }
.hub-mode-name { font-weight: 700; font-size: 13px; color: var(--text); }
.hub-mode.active .hub-mode-name { color: var(--accent-bright); }
.hub-mode-desc { font-size: 11.5px; line-height: 1.5; color: var(--text3); }
.hub-mode-skill { font-family: var(--font-mono); font-size: 10px; color: var(--text-dim); }
.hub-console {
  background: var(--bg); border: 1px solid var(--border); border-radius: 8px;
  font-family: var(--font-mono); font-size: 11px; line-height: 1.6;
  padding: 10px 12px; max-height: 260px; overflow-y: auto;
}
.hub-line { white-space: pre-wrap; word-break: break-all; color: var(--text2); }
.hub-line.err { color: #f0b9ad; }
.hub-ts { color: var(--text-dim); margin-right: 8px; }
.hub-stream { color: var(--accent); margin-right: 8px; }
.hub-result-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.hub-tabs { display: flex; gap: 6px; }
.hub-tab {
  appearance: none; cursor: pointer; border: 1px solid var(--border-strong);
  background: transparent; color: var(--text3); border-radius: 6px;
  font-size: 12px; padding: 5px 12px;
}
.hub-tab.active { border-color: var(--accent); color: var(--accent-bright); background: var(--accent-soft); }
.hub-frame { width: 100%; height: 620px; border: 1px solid var(--border-strong); border-radius: 8px; background: #101418; }
.hub-md {
  border: 1px solid var(--border); border-radius: 8px; padding: 14px 18px;
  background: var(--surface-soft); max-height: 620px; overflow-y: auto;
  font-size: 13px; line-height: 1.7; color: var(--text2);
}
.hub-md :deep(table) { border-collapse: collapse; width: 100%; margin: 8px 0; }
.hub-md :deep(th), .hub-md :deep(td) { border: 1px solid var(--border-strong); padding: 4px 8px; font-size: 12px; }
.hub-md :deep(h1) { font-size: 18px; }
.hub-md :deep(h2) { font-size: 15px; border-bottom: 1px solid var(--border); padding-bottom: 4px; }
.hub-md :deep(h3) { font-size: 13.5px; }
.hub-md :deep(blockquote) { border-left: 3px solid var(--accent); margin: 6px 0; padding: 2px 10px; color: var(--text3); }
.hub-statement { font-size: 13px; color: var(--text2); margin: 4px 0 10px; }
.cl-field.wide { grid-column: 1 / -1; }
</style>
