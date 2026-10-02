<template>
  <div class="cl-panel">
    <!-- ── 基线登记表 ── -->
    <section class="cl-card">
      <h3>{{ $t('closedloop.sentinel.baselines') }}</h3>
      <p class="cl-card-desc">{{ $t('closedloop.sentinel.desc') }}</p>
      <table v-if="baselines.length" class="cl-table">
        <thead>
          <tr>
            <th>{{ $t('closedloop.sentinel.line') }}</th>
            <th>baseline</th>
            <th>{{ $t('closedloop.common.status') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="b in baselines" :key="b.line">
            <td class="strong">{{ b.line }}</td>
            <td :title="b.baseline_path">{{ shortPath(b.baseline_path) }}</td>
            <td><span class="cl-pill ok">registered</span></td>
          </tr>
        </tbody>
      </table>
      <p v-else class="cl-empty">{{ $t('closedloop.common.none') }}</p>
    </section>

    <!-- ── 构建基线 + 批筛 ── -->
    <div class="cl-grid-2">
      <section class="cl-card">
        <h3>{{ $t('closedloop.sentinel.buildTitle') }}</h3>
        <div class="cl-form">
          <div class="cl-field">
            <label>{{ $t('closedloop.sentinel.line') }}</label>
            <input v-model="buildForm.line" placeholder="L1" />
          </div>
          <div class="cl-field">
            <label>{{ $t('closedloop.sentinel.historyCsv') }}</label>
            <input v-model="buildForm.history_csv" list="cl-data-paths" placeholder="data/.../history.csv" />
          </div>
          <div class="cl-field">
            <label>{{ $t('closedloop.sentinel.doeRunDir') }} · {{ $t('closedloop.common.optional') }}</label>
            <input v-model="buildForm.doe_run_dir" placeholder="workspace/.../doe_run" />
          </div>
          <div class="cl-field">
            <label>{{ $t('closedloop.sentinel.timeCol') }}</label>
            <input v-model="buildForm.time_col" placeholder="t" />
          </div>
        </div>
        <div class="cl-actions">
          <button type="button" class="cl-btn" :disabled="busy.build" @click="submitBuild">
            {{ busy.build ? $t('closedloop.common.busy') : $t('closedloop.common.run') }}
          </button>
        </div>
        <task-result v-if="tasks.build" :task="tasks.build" kind="baseline" />
      </section>

      <section class="cl-card">
        <h3>{{ $t('closedloop.sentinel.watchTitle') }}</h3>
        <div class="cl-form">
          <div class="cl-field">
            <label>{{ $t('closedloop.sentinel.watchData') }}</label>
            <input v-model="watchForm.data_path" list="cl-data-paths" placeholder="data/.../window.csv" />
          </div>
          <div class="cl-field">
            <label>{{ $t('closedloop.sentinel.baselinePath') }}</label>
            <input v-model="watchForm.baseline_path" list="cl-baseline-paths" :placeholder="$t('closedloop.common.optional')" />
          </div>
          <div class="cl-field">
            <label>{{ $t('closedloop.sentinel.timeCol') }}</label>
            <input v-model="watchForm.time_col" placeholder="t" />
          </div>
        </div>
        <div class="cl-actions">
          <button type="button" class="cl-btn" :disabled="busy.watch" @click="submitWatch">
            {{ busy.watch ? $t('closedloop.common.busy') : $t('closedloop.common.run') }}
          </button>
        </div>
        <task-result v-if="tasks.watch" :task="tasks.watch" kind="watch" />
      </section>
    </div>

    <!-- ── 快筛 ── -->
    <section class="cl-card">
      <h3>{{ $t('closedloop.sentinel.screenTitle') }}</h3>
      <div class="cl-form">
        <div class="cl-field">
          <label>{{ $t('closedloop.sentinel.screenData') }}</label>
          <input v-model="screenForm.data_path" list="cl-data-paths" placeholder="data/.../new_rows.csv" />
        </div>
        <div class="cl-field">
          <label>{{ $t('closedloop.sentinel.timeCol') }}</label>
          <input v-model="screenForm.time_col" placeholder="t" />
        </div>
        <div class="cl-field btn-field">
          <button type="button" class="cl-btn" :disabled="busy.screen" @click="submitScreen">
            {{ busy.screen ? $t('closedloop.common.busy') : $t('closedloop.common.run') }}
          </button>
        </div>
      </div>
      <div v-if="screenResult" class="cl-screen-out">
        <div class="cl-kv">
          <span>{{ $t('closedloop.common.exitCode') }}: <b :class="exitClass(screenResult.exit_code)">{{ screenResult.exit_code }}</b></span>
          <span>{{ $t('closedloop.common.status') }}: <b>{{ screenResult.status }}</b></span>
          <span>{{ $t('closedloop.sentinel.nAlerts') }}: <b>{{ screenResult.n_alerts ?? (screenResult.alerts || []).length }}</b></span>
          <span v-if="screenResult.baseline_mode">{{ $t('closedloop.sentinel.baselineMode') }}: <b>{{ screenResult.baseline_mode }}</b></span>
          <span v-if="screenResult.error" class="bad-text">{{ screenResult.error }}</span>
        </div>
        <alert-table v-if="(screenResult.alerts || []).length" :alerts="screenResult.alerts.slice(0, 5)" />
      </div>
    </section>

    <datalist id="cl-baseline-paths">
      <option v-for="b in baselines" :key="b.line" :value="b.baseline_path" />
    </datalist>
    <datalist id="cl-data-paths">
      <option v-for="p in dataPaths" :key="p" :value="p" />
    </datalist>
  </div>
</template>

<script setup>
import { defineComponent, h, onMounted, reactive, ref } from 'vue';
import { api } from '../../api/index.js';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();

const baselines = ref([]);
const dataPaths = ref([]);
const busy = reactive({ build: false, watch: false, screen: false });
const tasks = reactive({ build: null, watch: null });
const screenResult = ref(null);
const buildForm = reactive({ line: '', history_csv: '', doe_run_dir: '', time_col: 't' });
const watchForm = reactive({ data_path: '', baseline_path: '', time_col: 't' });
const screenForm = reactive({ data_path: '', time_col: 't' });

function shortPath(p) {
  if (!p) return '-';
  const s = String(p).replace(/\\/g, '/');
  return s.length > 58 ? `…${s.slice(-56)}` : s;
}
function exitClass(code) {
  if (code === 0) return 'ok-text';
  if (code === 1) return 'warn-text';
  return 'bad-text';
}

// 服务端真实数据文件清单 → datalist（folder/file 两级拼路径）
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

// 提交即返 task_id → 每秒轮询直到 completed/failed
async function pollTask(taskId, slot, onDone) {
  for (let i = 0; i < 180; i++) {
    const data = await api.sentinelTask(taskId);
    tasks[slot] = data || { status: 'queued' };
    if (data && (data.status === 'completed' || data.status === 'failed')) {
      onDone?.(data);
      return data;
    }
    await new Promise((r) => setTimeout(r, 1000));
  }
  tasks[slot] = { status: 'failed', error: 'poll timeout' };
  return null;
}

async function submitBuild() {
  if (!buildForm.line || !buildForm.history_csv) return;
  busy.build = true;
  tasks.build = { status: 'queued' };
  try {
    const data = await api.sentinelBaselineBuild({
      line: buildForm.line,
      history_csv: buildForm.history_csv,
      doe_run_dir: buildForm.doe_run_dir || null,
      time_col: buildForm.time_col || null,
    });
    await pollTask(data.task_id, 'build', () => loadBaselines());
  } catch (e) {
    tasks.build = { status: 'failed', error: e.message };
  } finally { busy.build = false; }
}

async function submitWatch() {
  if (!watchForm.data_path) return;
  busy.watch = true;
  tasks.watch = { status: 'queued' };
  try {
    const data = await api.sentinelWatch({
      data_path: watchForm.data_path,
      baseline_path: watchForm.baseline_path || null,
      time_col: watchForm.time_col || null,
    });
    await pollTask(data.task_id, 'watch', () => {});
  } catch (e) {
    tasks.watch = { status: 'failed', error: e.message };
  } finally { busy.watch = false; }
}

async function submitScreen() {
  if (!screenForm.data_path) return;
  busy.screen = true;
  screenResult.value = null;
  try {
    const data = await api.sentinelScreen({
      data_path: screenForm.data_path,
      time_col: screenForm.time_col || null,
    });
    screenResult.value = data;
  } catch (e) {
    screenResult.value = { exit_code: -1, status: 'error', alerts: [], error: e.message };
  } finally { busy.screen = false; }
}

async function loadBaselines() {
  try {
    const data = await api.sentinelBaselines();
    const lines = data?.lines || {};
    baselines.value = Object.entries(lines).map(([line, entry]) => ({ line, ...entry }));
  } catch { baselines.value = []; }
}
onMounted(() => { loadBaselines(); loadDataPaths(); });

// ── 内联子组件（template 内 kebab-case 使用）──
const AlertTable = defineComponent({
  name: 'AlertTable',
  props: { alerts: { type: Array, required: true } },
  setup(props) {
    return () => h('div', [
      h('p', { class: 'cl-note' }, t('closedloop.sentinel.firstAlerts')),
      h('table', { class: 'cl-table' }, [
        h('thead', h('tr', [
          h('th', t('closedloop.sentinel.rule')),
          h('th', t('closedloop.sentinel.parameter')),
          h('th', t('closedloop.common.severity')),
          h('th', t('closedloop.sentinel.observed')),
        ])),
        h('tbody', props.alerts.map((a, i) => h('tr', { key: a.alert_id || i }, [
          h('td', { class: 'strong' }, `${a.check_type || ''}/${a.rule_name || ''}`),
          h('td', a.parameter || '-'),
          h('td', h('span', { class: `cl-pill ${a.severity || 'info'}` }, a.severity || 'info')),
          h('td', a.observed != null ? String(a.observed.value ?? JSON.stringify(a.observed)) : '-'),
        ]))),
      ]),
    ]);
  },
});

const TaskResult = defineComponent({
  name: 'TaskResult',
  props: {
    task: { type: Object, required: true },
    kind: { type: String, default: 'watch' },
  },
  setup(props) {
    return () => {
      // 任务视图是拍平形态：exit_code / alerts / n_alerts / baseline_path 都在顶层
      const task = props.task || {};
      const r = { ...(task.result || {}), ...task };
      if (task.status !== 'completed' && task.status !== 'failed') {
        return h('p', { class: 'cl-note' }, t('closedloop.sentinel.pollHint'));
      }
      if (task.status === 'failed') {
        return h('div', { class: 'cl-alert error' },
          `${t('closedloop.common.failed')}: ${task.error || r.error || 'unknown'}`);
      }
      if (props.kind === 'baseline') {
        return h('div', { class: 'cl-screen-out' }, [
          h('div', { class: 'cl-alert ok' },
            `${t('closedloop.common.ok')} · ${r.line || ''} → ${shortPath(r.baseline_path || '-')}`),
        ]);
      }
      const alerts = r.alerts || [];
      return h('div', { class: 'cl-screen-out' }, [
        h('div', { class: 'cl-kv' }, [
          h('span', `${t('closedloop.common.exitCode')}: `),
          h('b', { class: exitClass(r.exit_code) }, String(r.exit_code ?? '-')),
          h('span', ` · ${t('closedloop.common.status')}: `),
          h('b', String(r.alert_status ?? r.status ?? '-')),
          h('span', ` · ${t('closedloop.sentinel.nAlerts')}: `),
          h('b', String(r.n_alerts ?? alerts.length)),
          r.baseline_mode ? h('span', ` · ${t('closedloop.sentinel.baselineMode')}: ${r.baseline_mode}`) : null,
          r.n_rows ? h('span', ` · ${t('closedloop.common.rows')}: ${r.n_rows}`) : null,
        ]),
        alerts.length ? h(AlertTable, { alerts: alerts.slice(0, 5) }) : null,
      ]);
    };
  },
});
</script>

<style scoped>
.cl-actions { margin-top: 10px; display: flex; gap: 8px; }
.btn-field { justify-content: flex-end; }
.cl-screen-out { margin-top: 10px; display: flex; flex-direction: column; gap: 8px; }
.ok-text { color: #a9c795; }
.warn-text { color: var(--accent-bright); }
.bad-text { color: #f0a99b; }
</style>
