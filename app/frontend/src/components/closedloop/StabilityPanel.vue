<template>
  <div class="cl-panel">
    <!-- ── 生成报告 ── -->
    <section class="cl-card">
      <h3>{{ $t('closedloop.stability.title') }}</h3>
      <p class="cl-card-desc">{{ $t('closedloop.stability.desc') }}</p>
      <div class="cl-form">
        <div class="cl-field">
          <label>{{ $t('closedloop.stability.line') }}</label>
          <input v-model="form.line_id" placeholder="L1-extruder-206" />
        </div>
        <div class="cl-field wide">
          <DataFilePicker v-model="form.data_input" :label="$t('closedloop.stability.dataCsv')" :extensions="['.csv', '.tsv', '.xlsx', '.xls', '.parquet', '.json']" allow-folder />
        </div>
        <div class="cl-field">
          <label>{{ $t('closedloop.sentinel.timeCol') }}</label>
          <input v-model="form.time_col" placeholder="t" />
        </div>
        <div class="cl-field">
          <label>{{ $t('closedloop.stability.start') }} · {{ $t('closedloop.common.optional') }}</label>
          <input v-model="form.start" placeholder="2026-10-01T08:00:00" />
        </div>
        <div class="cl-field">
          <label>{{ $t('closedloop.stability.end') }} · {{ $t('closedloop.common.optional') }}</label>
          <input v-model="form.end" placeholder="2026-10-01T20:00:00" />
        </div>
        <div class="cl-field">
          <label>sentinel baseline · {{ $t('closedloop.common.optional') }}</label>
          <input v-model="form.baseline_path" list="cl-baseline-paths-lsr" placeholder="watch_baseline.json" />
          <datalist id="cl-baseline-paths-lsr">
            <option v-for="b in baselines" :key="b.line" :value="b.baseline_path" />
          </datalist>
        </div>
        <div class="cl-field">
          <label>ontology.json · {{ $t('closedloop.common.optional') }}</label>
          <input v-model="form.ontology_path" placeholder="00_input/ontology.json" />
        </div>
        <div class="cl-field">
          <label>{{ $t('closedloop.stability.scene') }} · {{ $t('closedloop.common.optional') }}</label>
          <input v-model="form.scene" placeholder="cement_ball_mill_e2e" />
        </div>
        <div class="cl-field">
          <label>doe run 目录 · {{ $t('closedloop.common.optional') }}</label>
          <input v-model="form.doe_run_dir" placeholder="workspace/.../doe_run" />
        </div>
        <div class="cl-field wide lsr-check">
          <label class="lsr-checkbox">
            <input v-model="form.doe_auto" type="checkbox" />
            {{ $t('closedloop.stability.doeAuto') }}
          </label>
        </div>
        <div class="cl-field wide">
          <label>action_log JSON · {{ $t('closedloop.common.optional') }}</label>
          <textarea v-model="form.action_log_text" :placeholder="actionLogHint"></textarea>
        </div>
      </div>
      <div class="cl-actions">
        <button type="button" class="cl-btn" :disabled="busy.run || !dataCompatible" @click="submitReport">
          {{ busy.run ? $t('closedloop.common.busy') : $t('closedloop.stability.generate') }}
        </button>
        <span v-if="form.data_input?.kind === 'directory'" class="cl-note">{{ $t('closedloop.dataPicker.folderAdaptive') }}</span>
        <span v-if="!dataCompatible" class="cl-note">{{ $t('closedloop.dataPicker.incompatible') }}</span>
        <span v-if="error" class="cl-alert error">{{ error }}</span>
      </div>
      <task-result v-if="task" :task="task" @open-html="openHtml" />
    </section>

    <!-- ── 报告正体（任务完成后展示） ── -->
    <template v-if="report">
      <section class="cl-card lsr-summary">
        <div class="lsr-hero">
          <div class="lsr-score" :style="{ borderColor: gradeColor, color: gradeColor }">
            <div class="lsr-score-num">{{ report.conclusion?.score ?? '—' }}</div>
            <div class="lsr-score-grade">{{ report.conclusion?.grade ?? 'N/A' }} · {{ report.conclusion?.label }}</div>
          </div>
          <div class="lsr-hero-text">
            <div class="lsr-line">{{ report.line?.line_id || report.report_id }}</div>
            <div class="lsr-statement">{{ report.conclusion?.statement }}</div>
            <div class="cl-kv">
              <span>{{ $t('closedloop.stability.period') }}: <b>{{ shortPeriod(report.period) }}</b></span>
              <span>{{ $t('closedloop.common.rows') }}: <b>{{ report.data?.n_rows_used }}</b></span>
              <span>{{ $t('closedloop.stability.params') }}: <b>{{ report.conclusion?.n_parameters_assessed }}</b></span>
            </div>
          </div>
          <div class="lsr-actions">
            <button v-if="htmlUrl" type="button" class="cl-btn" @click="openHtml">
              {{ $t('closedloop.stability.openHtml') }}
            </button>
          </div>
        </div>

        <h3>{{ $t('closedloop.stability.findings') }}</h3>
        <div v-for="f in (report.findings || []).slice(0, 8)" :key="f.finding_id" class="lsr-finding">
          <span class="cl-pill" :class="f.severity">{{ f.severity }}</span>
          <div class="lsr-finding-body">
            <div class="lsr-finding-title">{{ f.finding_id }} · {{ f.title }}</div>
            <div class="lsr-finding-detail">{{ f.detail }}</div>
          </div>
        </div>
        <p v-if="!(report.findings || []).length" class="cl-empty">{{ $t('closedloop.stability.noFindings') }}</p>

        <h3>{{ $t('closedloop.stability.paramTable') }}</h3>
        <table class="cl-table">
          <thead>
            <tr>
              <th>{{ $t('closedloop.stability.param') }}</th>
              <th>{{ $t('closedloop.common.rows') }}</th>
              <th>CV</th>
              <th>SPC</th>
              <th>Cpk</th>
              <th>{{ $t('closedloop.stability.score') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="p in (report.parameters || [])" :key="p.name">
              <td class="strong">{{ p.name }}<span class="lsr-role">{{ p.role === 'inspection' ? '检测' : '参数' }}</span></td>
              <td>{{ p.n }}</td>
              <td>{{ fmt(p.cv, 4) }}</td>
              <td>{{ p.n_violation_points }}</td>
              <td>{{ fmt(p.capability?.cpk) }}</td>
              <td class="strong">{{ p.score ?? '—' }}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section v-if="htmlUrl" class="cl-card">
        <h3>{{ $t('closedloop.stability.embedded') }}</h3>
        <iframe class="lsr-iframe" :src="htmlUrl" :title="$t('closedloop.stability.embedded')"></iframe>
      </section>
    </template>

    <!-- ── 历史报告 ── -->
    <section class="cl-card">
      <h3>{{ $t('closedloop.stability.runsTitle') }}</h3>
      <table v-if="runs.length" class="cl-table">
        <thead>
          <tr>
            <th>{{ $t('closedloop.stability.line') }}</th>
            <th>{{ $t('closedloop.stability.score') }}</th>
            <th>{{ $t('closedloop.common.status') }}</th>
            <th>{{ $t('closedloop.stability.generated') }}</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in runs" :key="r.task_id">
            <td class="strong">{{ r.line_id || r.task_id }}</td>
            <td>
              <span v-if="r.score != null" class="cl-pill" :class="gradePill(r.grade)">{{ r.score }} · {{ r.grade }}</span>
              <span v-else class="cl-pill">N/A</span>
            </td>
            <td>{{ r.status }}</td>
            <td>{{ shortTime(r.generated_at) }}</td>
            <td>
              <button v-if="r.html_url" type="button" class="cl-btn small ghost" @click="openUrl(r.html_url)">
                {{ $t('closedloop.stability.openHtml') }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-else class="cl-empty">{{ $t('closedloop.common.none') }}</p>
    </section>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref, computed, defineComponent, h } from 'vue';
import { api } from '../../api/index.js';
import { useI18n } from 'vue-i18n';
import DataFilePicker from './DataFilePicker.vue';

const { t } = useI18n();

const baselines = ref([]);
const runs = ref([]);
const busy = reactive({ run: false });
const task = ref(null);
const report = ref(null);
const htmlUrl = ref(null);
const error = ref('');
const form = reactive({
  line_id: '', data_input: { kind: 'file', path: '' }, time_col: 't', start: '', end: '',
  baseline_path: '', doe_run_dir: '', action_log_text: '',
  ontology_path: '', scene: '', doe_auto: false,
});
const dataCompatible = computed(() => {
  const input = form.data_input;
  if (!input?.path || input.kind === 'directory') return true;
  const normalized = String(input.path).replace(/\\/g, '/');
  const basename = normalized.slice(normalized.lastIndexOf('/') + 1);
  const ext = basename.includes('.') ? `.${basename.split('.').pop()?.toLowerCase()}` : '';
  return ['.csv', '.tsv', '.xlsx', '.xls', '.parquet', '.json'].includes(ext);
});
const actionLogHint = '{"schema_version":"1.0","ts":"...","actor":{...},"actions":[{"parameter":"temp","to":86.0,"unit":"C"}]}';

const GRADE_COLORS = { A: '#7fb069', B: '#e8a33d', C: '#e0703a', D: '#e05d4a' };
const gradeColor = computed(() => GRADE_COLORS[report.value?.conclusion?.grade] || '#8a99a8');

function fmt(v, nd = 3) {
  if (v == null) return '—';
  const s = Number(v).toFixed(nd);
  return s.replace(/\.?0+$/, '') || '0';
}
function shortPath(p) {
  if (!p) return '-';
  const s = String(p).replace(/\\/g, '/');
  return s.length > 58 ? `…${s.slice(-56)}` : s;
}
function shortPeriod(period) {
  if (!period?.start) return '—';
  const day = (v) => String(v).replace('T', ' ').slice(5, 16);
  return `${day(period.start)} ~ ${day(period.end)}`;
}
function shortTime(v) {
  return v ? String(v).replace('T', ' ').slice(0, 16) : '—';
}
function gradePill(grade) {
  if (grade === 'A') return 'ok';
  if (grade === 'B') return 'warn';
  if (grade) return 'high';
  return 'info';
}
function openUrl(url) { window.open(url, '_blank', 'noopener'); }
function openHtml() { if (htmlUrl.value) openUrl(htmlUrl.value); }

async function loadBaselines() {
  try {
    const data = await api.sentinelBaselines();
    const lines = data?.lines || {};
    baselines.value = Object.entries(lines).map(([line, entry]) => ({ line, ...entry }));
  } catch { baselines.value = []; }
}

async function loadRuns() {
  try { runs.value = await api.lineReportRuns() || []; } catch { runs.value = []; }
}

async function pollTask(taskId) {
  for (let i = 0; i < 200; i++) {
    const data = await api.lineReportTask(taskId);
    task.value = data || { status: 'queued' };
    if (data && (data.status === 'completed' || data.status === 'failed')) return data;
    await new Promise((r) => setTimeout(r, 1200));
  }
  task.value = { status: 'failed', error: 'poll timeout' };
  return null;
}

async function submitReport() {
  if (!form.data_input?.path) return;
  busy.run = true;
  error.value = '';
  report.value = null;
  htmlUrl.value = null;
  task.value = { status: 'queued' };
  try {
    let actionLog = null;
    if (form.action_log_text.trim()) {
      try { actionLog = JSON.parse(form.action_log_text); }
      catch { throw new Error(t('closedloop.common.jsonInvalid')); }
    }
    const created = await api.lineReportRun({
      ...(form.data_input.kind === 'directory'
        ? { data_dir: form.data_input.path, input_kind: 'directory' }
        : { data_path: form.data_input.path, input_kind: 'file' }),
      line_id: form.line_id || null,
      ...(form.data_input.kind === 'directory' && form.time_col === 't' ? { time_col: null } : { time_col: form.time_col || null }),
      start: form.start || null,
      end: form.end || null,
      baseline_path: form.baseline_path || null,
      doe_run_dir: form.doe_run_dir || null,
      ontology_path: form.ontology_path || null,
      scene: form.scene || null,
      doe_auto: form.doe_auto || false,
      action_log: actionLog,
    });
    const done = await pollTask(created.task_id);
    if (done?.status === 'completed' && done.result?.report) {
      report.value = done.result.report;
      htmlUrl.value = done.result.html_url || null;
    } else if (done?.status === 'failed') {
      error.value = done.error || t('closedloop.common.failed');
    }
    loadRuns();
  } catch (e) {
    error.value = e.message;
    task.value = { status: 'failed', error: e.message };
  } finally { busy.run = false; }
}

onMounted(() => { loadBaselines(); loadRuns(); });

const TaskResult = defineComponent({
  name: 'TaskResult',
  props: { task: { type: Object, required: true } },
  emits: ['open-html'],
  setup(props) {
    return () => {
      const task = props.task || {};
      const summary = task.result?.report_summary;
      if (task.status && !['completed', 'failed'].includes(task.status)) {
        return h('p', { class: 'cl-note' },
          `${t('closedloop.common.' + task.status)} — ${task.task_id || ''}`);
      }
      if (task.status === 'failed') {
        return h('div', { class: 'cl-alert error' }, task.error || t('closedloop.common.failed'));
      }
      if (!summary) return null;
      const kids = [h('div', { class: 'cl-kv' }, [
        h('span', `${t('closedloop.stability.report')} ${summary.report_id}`),
        h('span', `${t('closedloop.stability.score')}: `,
          [h('b', `${summary.score ?? '—'} · ${summary.grade ?? 'N/A'}`)]),
        h('span', `${t('closedloop.stability.params')}: `, [h('b', String(summary.n_parameters_assessed))]),
      ])];
      if (task.result?.html_url) {
        kids.push(h('p', { class: 'cl-note' }, task.result.html_url));
      }
      return h('div', { class: 'cl-alert ok' }, kids);
    };
  },
});
</script>

<style scoped>
.cl-actions { display: flex; align-items: center; gap: 12px; margin-top: 12px; flex-wrap: wrap; }
.cl-field.wide { grid-column: 1 / -1; }
.lsr-check { align-items: center; }
.lsr-checkbox { display: flex; align-items: center; gap: 8px; font-size: 12px; color: var(--text2); cursor: pointer; }
.lsr-checkbox input { width: auto; }
.lsr-hero { display: flex; gap: 18px; align-items: center; flex-wrap: wrap; margin-bottom: 8px; }
.lsr-score {
  border: 2px solid; border-radius: 12px; padding: 10px 18px; text-align: center; min-width: 120px;
}
.lsr-score-num { font-size: 34px; font-weight: 800; line-height: 1.1; }
.lsr-score-grade { font-size: 12px; font-weight: 700; }
.lsr-hero-text { flex: 1; min-width: 260px; }
.lsr-line { font-weight: 700; margin-bottom: 4px; }
.lsr-statement { font-size: 13px; color: var(--text2); margin-bottom: 8px; }
.lsr-actions { display: flex; flex-direction: column; gap: 8px; }
.lsr-finding { display: flex; gap: 10px; padding: 8px 0; border-bottom: 1px solid var(--border); }
.lsr-finding-body { flex: 1; min-width: 0; }
.lsr-finding-title { font-size: 13px; font-weight: 600; color: var(--text); }
.lsr-finding-detail { font-size: 12px; color: var(--text3); margin-top: 2px; line-height: 1.5; }
.lsr-role {
  margin-left: 6px; font-size: 10px; color: var(--text3);
  border: 1px solid var(--border-strong); border-radius: 4px; padding: 0 4px;
}
.lsr-iframe {
  width: 100%; height: 640px; border: 1px solid var(--border-strong);
  border-radius: 8px; background: #101418;
}
</style>
