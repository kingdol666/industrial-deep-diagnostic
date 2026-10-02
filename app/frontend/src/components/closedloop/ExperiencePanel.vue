<template>
  <div class="cl-panel">
    <!-- ── 库状态 ── -->
    <section class="cl-card">
      <h3>{{ $t('closedloop.experience.title') }}</h3>
      <p class="cl-card-desc">{{ $t('closedloop.experience.desc') }}</p>
      <div class="cl-kv">
        <span>{{ $t('closedloop.experience.entries') }}: <b>{{ library.store_entries ?? '–' }}</b></span>
        <span>{{ $t('closedloop.experience.store') }}: <b :title="library.store_path">{{ shortPath(library.store_path) }}</b></span>
      </div>
    </section>

    <!-- ── 摄取 + 检索 ── -->
    <div class="cl-grid-2">
      <section class="cl-card">
        <h3>{{ $t('closedloop.experience.ingestTitle') }}</h3>
        <div class="cl-form one-col">
          <div class="cl-field">
            <label>{{ $t('closedloop.experience.actionsJson') }}</label>
            <textarea v-model="ingest.actions" rows="8" spellcheck="false" />
          </div>
          <div class="cl-field">
            <label>{{ $t('closedloop.experience.dataset') }}</label>
            <input v-model="ingest.data_path" list="exp-data-paths" placeholder="data/.../series.csv" />
          </div>
          <div class="cl-form">
            <div class="cl-field">
              <label>{{ $t('closedloop.experience.metric') }}</label>
              <input v-model="ingest.metric" placeholder="yield_pct" />
            </div>
            <div class="cl-field">
              <label>{{ $t('closedloop.sentinel.timeCol') }}</label>
              <input v-model="ingest.time_col" placeholder="t" />
            </div>
          </div>
        </div>
        <div class="cl-actions">
          <button type="button" class="cl-btn small ghost" @click="fillIngestExample">{{ $t('closedloop.experience.examples') }}</button>
          <button type="button" class="cl-btn" :disabled="busy.ingest" @click="submitIngest">
            {{ busy.ingest ? $t('closedloop.common.busy') : $t('closedloop.common.run') }}
          </button>
        </div>
        <div v-if="job" class="cl-screen-out">
          <div class="cl-kv">
            <span>{{ $t('closedloop.experience.jobId') }}: <b>{{ job.job_id || jobId }}</b></span>
            <span>{{ $t('closedloop.common.status') }}: <b :class="job.status === 'failed' ? 'bad-text' : 'ok-text'">{{ job.status }}</b></span>
            <span v-if="job.reports">{{ $t('closedloop.experience.entries') }}: <b>{{ job.reports.length }}</b></span>
          </div>
          <div v-if="job.error" class="cl-alert error">{{ job.error }}</div>
        </div>
      </section>

      <section class="cl-card">
        <h3>{{ $t('closedloop.experience.recommendTitle') }}</h3>
        <div class="cl-field">
          <label>{{ $t('closedloop.experience.signatureJson') }}</label>
          <textarea v-model="signature" rows="8" spellcheck="false" />
        </div>
        <div class="cl-actions">
          <button type="button" class="cl-btn small ghost" @click="fillSignatureExample">{{ $t('closedloop.experience.examples') }}</button>
          <button type="button" class="cl-btn" :disabled="busy.recommend" @click="submitRecommend">
            {{ busy.recommend ? $t('closedloop.common.busy') : $t('closedloop.common.run') }}
          </button>
        </div>
        <div v-if="recommendation" class="cl-screen-out">
          <div class="cl-alert" :class="isHit ? 'ok' : ''">
            {{ isHit ? $t('closedloop.experience.hit') : $t('closedloop.experience.noHit') }}
            <span v-if="recommendation.match_scope" class="cl-pill">{{ $t('closedloop.experience.scope') }}: {{ recommendation.match_scope }}</span>
          </div>
          <div v-for="pb in recommendation.playbooks || []" :key="pb.experience_id" class="cl-playbook">
            <div class="cl-kv">
              <span>{{ $t('closedloop.experience.score') }}: <b>{{ pb.match_score }}</b></span>
              <span>{{ $t('closedloop.experience.grade') }}: <span class="cl-pill">{{ pb.evidence_grade }}</span></span>
              <span class="cl-pill">autonomy: {{ pb.autonomy_level === null ? 'null (AWS)' : pb.autonomy_level }}</span>
            </div>
            <div v-if="(pb.action_sequence || []).length" class="cl-note">
              {{ $t('closedloop.experience.actionSeq') }}:
              <span v-for="(s, i) in pb.action_sequence" :key="i" class="cl-pill">{{ s.parameter }} → {{ s.to }}{{ s.unit || '' }}</span>
            </div>
            <div v-if="pb.expected_effect" class="cl-note">
              {{ $t('closedloop.experience.expectedEffect') }}: <b>{{ pb.expected_effect.delta }}</b>
              <span v-if="pb.expected_effect.ci95"> (CI95 {{ pb.expected_effect.ci95.join(' ~ ') }})</span>
            </div>
            <div class="cl-note mono-dim">{{ pb.experience_id }}</div>
            <div class="cl-actions">
              <button type="button" class="cl-btn small" @click="useForFeedback(pb.experience_id)">
                {{ $t('closedloop.experience.feedbackTitle') }} →
              </button>
            </div>
          </div>
          <div v-if="!isHit && (recommendation.degradation_path || []).length" class="cl-note">
            {{ $t('closedloop.experience.degradation') }}: {{ (recommendation.degradation_path || []).join(' → ') }}
          </div>
        </div>
      </section>
    </div>

    <!-- ── 反馈 ── -->
    <section class="cl-card">
      <h3>{{ $t('closedloop.experience.feedbackTitle') }}</h3>
      <div class="cl-form">
        <div class="cl-field grow">
          <label>{{ $t('closedloop.experience.expId') }}</label>
          <input v-model="feedback.experience_id" placeholder="exp_fault_control_recipe_…" />
        </div>
        <div class="cl-field">
          <label>{{ $t('closedloop.experience.fbResult') }}</label>
          <select v-model="feedback.result">
            <option value="effective">{{ $t('closedloop.experience.effective') }}</option>
            <option value="ineffective">{{ $t('closedloop.experience.ineffective') }}</option>
            <option value="harmful">{{ $t('closedloop.experience.harmful') }}</option>
            <option value="confirmed">{{ $t('closedloop.experience.confirmed') }}</option>
          </select>
        </div>
        <div class="cl-field grow">
          <label>{{ $t('closedloop.experience.note') }}</label>
          <input v-model="feedback.note" />
        </div>
        <div class="cl-field btn-field">
          <button type="button" class="cl-btn" :disabled="busy.feedback" @click="submitFeedback">
            {{ busy.feedback ? $t('closedloop.common.busy') : $t('closedloop.common.run') }}
          </button>
        </div>
      </div>
      <div v-if="fbOutcome" class="cl-alert" :class="fbOutcome.ok ? 'ok' : 'error'">{{ fbOutcome.text }}</div>
    </section>

    <datalist id="exp-data-paths">
      <option v-for="p in dataPaths" :key="p" :value="p" />
    </datalist>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue';
import { api } from '../../api/index.js';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();

const library = ref({});
const dataPaths = ref([]);
const busy = reactive({ ingest: false, recommend: false, feedback: false });

const ingest = reactive({
  actions: '',
  data_path: '',
  metric: 'yield_pct',
  time_col: 't',
});
const signature = ref('');
const job = ref(null);
const jobId = ref('');
const recommendation = ref(null);
const feedback = reactive({ experience_id: '', result: 'effective', note: '' });
const fbOutcome = ref(null);

const INGEST_EXAMPLE = JSON.stringify([
  {
    schema_version: '1.0',
    ts: '2026-01-05T00:33:20Z',
    actor: { actor_id: 'ENG-ZHANG-0091', actor_type: 'engineer', display_alias: null },
    actions: [{ parameter: 'temp', from: 85.0, to: 88.0, unit: 'degC' }],
    bundled_action: { is_bundle: false, bundle_reason: 'single', note: null },
    context: { product: 'PA', machine: 'L1', regime_label: 'S1', steady_segment_ref: null, group_key: null },
    trigger: { trigger_type: 'alert', ref_id: 'ALT-20261001-001' },
    attribution_confounds: [],
    recommendation_ref: null,
    ingest_meta: { source: 'csv_import', ingested_at: null },
  },
], null, 2);

const SIGNATURE_EXAMPLE = JSON.stringify({
  signature_version: '1.0',
  source_ref: 'ALT-20261001-001',
  anomalous_params: [{ parameter: 'temp', direction: 'high', severity: 3.6 }],
  regime: { product: 'PA', machine: 'L1', regime_label: 'S1' },
  degraded_metric: 'yield_pct',
}, null, 2);

function fillIngestExample() { ingest.actions = INGEST_EXAMPLE; }
function fillSignatureExample() { signature.value = SIGNATURE_EXAMPLE; }

function shortPath(p) {
  if (!p) return '-';
  const s = String(p).replace(/\\/g, '/');
  return s.length > 64 ? `…${s.slice(-62)}` : s;
}
function parseJson(text) {
  try { return { ok: true, value: JSON.parse(text) }; }
  catch { return { ok: false }; }
}

async function loadLibrary() {
  try {
    const data = await api.experienceLibrary();
    library.value = data || {};
  } catch { library.value = {}; }
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
      } catch { /* entry may be a plain file */ }
    }
    dataPaths.value = out;
  } catch { /* optional */ }
}
onMounted(() => { loadLibrary(); loadDataPaths(); });

async function submitIngest() {
  const parsed = parseJson(ingest.actions);
  if (!parsed.ok) {
    job.value = { status: 'failed', error: t('closedloop.common.jsonInvalid') };
    return;
  }
  busy.ingest = true;
  job.value = { status: 'running' };
  try {
    const data = await api.experienceIngest({
      action_log: parsed.value,
      data_path: ingest.data_path || undefined,
      metric: ingest.metric || null,
      time_col: ingest.time_col || 't',
    });
    jobId.value = data.attribution_job_id;
    for (let i = 0; i < 180; i++) {
      const view = await api.experienceJob(data.attribution_job_id);
      job.value = view.data || { status: 'running' };
      if (['completed', 'failed'].includes(job.value.status)) break;
      await new Promise((r) => setTimeout(r, 1500));
    }
    await loadLibrary();
  } catch (e) {
    job.value = { status: 'failed', error: e.message };
  } finally { busy.ingest = false; }
}

const isHit = ref(false);
async function submitRecommend() {
  const parsed = parseJson(signature.value);
  if (!parsed.ok) {
    recommendation.value = { recommendation_status: 'invalid_json', degradation_path: [t('closedloop.common.jsonInvalid')] };
    return;
  }
  busy.recommend = true;
  try {
    const data = await api.experienceRecommend({ fault_signature: parsed.value, top_k: 3 });
    recommendation.value = data;
    isHit.value = data?.recommendation_status === 'playbook_hit';
  } catch (e) {
    recommendation.value = { recommendation_status: 'error', degradation_path: [e.message] };
  } finally { busy.recommend = false; }
}

function useForFeedback(expId) {
  feedback.experience_id = expId;
  window.scrollTo?.({ top: document.body.scrollHeight, behavior: 'smooth' });
}

async function submitFeedback() {
  if (!feedback.experience_id) return;
  busy.feedback = true;
  fbOutcome.value = null;
  try {
    await api.experienceFeedback({
      experience_id: feedback.experience_id,
      result: feedback.result,
      note: feedback.note || null,
    });
    fbOutcome.value = { ok: true, text: `${t('closedloop.common.ok')}: ${feedback.experience_id} → ${feedback.result}` };
    await loadLibrary();
  } catch (e) {
    fbOutcome.value = { ok: false, text: `${t('closedloop.common.failed')}: ${e.message}` };
  } finally { busy.feedback = false; }
}
</script>

<style scoped>
.cl-actions { margin-top: 10px; display: flex; gap: 8px; align-items: center; }
.btn-field { justify-content: flex-end; }
.cl-screen-out { margin-top: 10px; display: flex; flex-direction: column; gap: 8px; }
.one-col { grid-template-columns: 1fr; }
.cl-playbook {
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  background: var(--surface-soft);
}
.mono-dim { font-family: var(--font-mono); font-size: 10.5px; color: var(--text-dim); }
.ok-text { color: #a9c795; }
.bad-text { color: #f0a99b; }
</style>
