<template>
  <div class="cl-panel">
    <!-- ── campaign 列表 + 发起 ── -->
    <div class="cl-grid-2">
      <section class="cl-card">
        <h3>{{ $t('closedloop.optimizer.campaigns') }}</h3>
        <table v-if="campaigns.length" class="cl-table">
          <thead>
            <tr>
              <th>{{ $t('closedloop.optimizer.campaignId') }}</th>
              <th>{{ $t('closedloop.optimizer.phase') }}</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="c in campaigns" :key="c.campaign_id" :class="{ current: c.campaign_id === selectedId }">
              <td class="strong">{{ c.campaign_id }}</td>
              <td><span class="cl-pill" :class="phaseClass(c.phase)">{{ c.phase }}</span></td>
              <td>
                <button type="button" class="cl-btn small ghost" @click="selectCampaign(c.campaign_id)">
                  {{ $t('closedloop.optimizer.stateRefresh') }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
        <p v-else class="cl-empty">{{ $t('closedloop.common.none') }}</p>
      </section>

      <section class="cl-card">
        <h3>{{ $t('closedloop.optimizer.initTitle') }}</h3>
        <div class="cl-field">
          <label>{{ $t('closedloop.optimizer.objectiveJson') }}</label>
          <textarea v-model="objective" rows="9" spellcheck="false" />
        </div>
        <div class="cl-actions">
          <button type="button" class="cl-btn small ghost" @click="objective = OBJECTIVE_EXAMPLE">{{ $t('closedloop.experience.examples') }}</button>
          <button type="button" class="cl-btn" :disabled="busy.init" @click="submitInit">
            {{ busy.init ? $t('closedloop.common.busy') : $t('closedloop.common.run') }}
          </button>
        </div>
        <div v-if="initError" class="cl-alert error">{{ initError }}</div>
      </section>
    </div>

    <!-- ── 会话状态 ── -->
    <section class="cl-card">
      <h3>{{ $t('closedloop.optimizer.stateTitle') }}</h3>
      <p v-if="!selectedId" class="cl-empty">{{ $t('closedloop.optimizer.noState') }}</p>
      <template v-else>
        <div class="cl-kv">
          <span>{{ $t('closedloop.optimizer.campaignId') }}: <b>{{ selectedId }}</b></span>
          <span>{{ $t('closedloop.optimizer.phase') }}: <span class="cl-pill" :class="phaseClass(state?.phase)">{{ state?.phase || '–' }}</span></span>
          <span v-if="state?.budget">{{ $t('closedloop.optimizer.round') }}: <b>{{ state.budget.rounds_used }}/{{ state.budget.max_rounds }}</b></span>
          <span v-if="state?.budget">{{ $t('closedloop.optimizer.budget') }}: <b>{{ state.budget.trials_used }}/{{ state.budget.max_trials }} trials</b></span>
        </div>
        <div v-if="state?.next_action" class="cl-note">
          {{ $t('closedloop.optimizer.nextAction') }}: <b>{{ state.next_action.action }}</b>
          <span v-if="(state.next_action.reasons || []).length"> — {{ state.next_action.reasons.join('; ') }}</span>
        </div>
      </template>
    </section>

    <!-- ── design / ingest ── -->
    <div v-if="selectedId" class="cl-grid-2">
      <section class="cl-card">
        <h3>{{ $t('closedloop.optimizer.design') }}</h3>
        <div class="cl-actions">
          <button type="button" class="cl-btn" :disabled="busy.design || isTerminal" @click="submitDesign">
            {{ busy.design ? $t('closedloop.common.busy') : $t('closedloop.optimizer.design') }}
          </button>
          <button
            v-if="lastDesign" type="button" class="cl-btn small ghost"
            @click="makeReceiptTemplate"
          >{{ $t('closedloop.optimizer.makeTemplate') }}</button>
        </div>
        <div v-if="lastDesign" class="cl-screen-out">
          <div class="cl-kv">
            <span>{{ $t('closedloop.optimizer.round') }}: <b>{{ lastDesign.round_id }}</b></span>
            <span>{{ $t('closedloop.optimizer.method') }}: <b>{{ lastDesign.method }}</b></span>
            <span>{{ $t('closedloop.optimizer.trials') }}: <b>{{ (lastDesign.trial_design?.trials || []).length }}</b></span>
          </div>
          <table class="cl-table">
            <thead>
              <tr>
                <th>trial</th>
                <th>setpoints</th>
                <th>reason</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="tr in lastDesign.trial_design?.trials || []" :key="tr.trial_id">
                <td class="strong">{{ tr.trial_id }}</td>
                <td>{{ formatSetpoints(tr.setpoints) }}</td>
                <td :title="tr.selection_reason">{{ (tr.selection_reason || '').slice(0, 44) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="cl-card">
        <h3>{{ $t('closedloop.optimizer.ingestTitle') }}</h3>
        <div class="cl-field">
          <label>{{ $t('closedloop.optimizer.trialJson') }}</label>
          <textarea v-model="trialResult" rows="9" spellcheck="false" />
        </div>
        <div class="cl-actions">
          <button type="button" class="cl-btn" :disabled="busy.ingest || isTerminal" @click="submitIngest">
            {{ busy.ingest ? $t('closedloop.common.busy') : $t('closedloop.common.run') }}
          </button>
          <button
            v-if="!isTerminal" type="button" class="cl-btn small ghost"
            :disabled="busy.pause" @click="doPause"
          >{{ $t('closedloop.optimizer.pause') }}</button>
          <button
            v-if="state?.phase === 'paused'" type="button" class="cl-btn small ghost"
            :disabled="busy.pause" @click="doResume"
          >{{ $t('closedloop.optimizer.resume') }}</button>
        </div>
        <div v-if="ingestError" class="cl-alert error">{{ ingestError }}</div>
        <div v-if="lastIngest" class="cl-note">
          {{ $t('closedloop.common.status') }}: <b>{{ lastIngest.phase }}</b>
          <span v-if="lastIngest.stdout_tail" class="mono-dim"> — {{ lastIngest.stdout_tail.slice(0, 120) }}</span>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import { api } from '../../api/index.js';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();

const OBJECTIVE_EXAMPLE = JSON.stringify({
  contract_version: '1.0',
  campaign_id: 'OPT-20261002-001',
  target_metric: 'yield_pct',
  goal: 'target',
  target_range: [98.0, 100.2],
  factors: [
    { name: 'temp', type: 'numeric', min: 82.0, max: 88.0, unit: 'degC' },
    { name: 'press', type: 'numeric', min: 0.55, max: 0.65, unit: 'MPa' },
  ],
  budget: { max_rounds: 10, max_trials: 30 },
  noise: { replicates_for_sigma: 3 },
  seed: 7,
}, null, 2);

const campaigns = ref([]);
const selectedId = ref('');
const state = ref(null);
const objective = ref(OBJECTIVE_EXAMPLE);
const trialResult = ref('');
const lastDesign = ref(null);
const lastIngest = ref(null);
const initError = ref('');
const ingestError = ref('');
const busy = ref({ init: false, design: false, ingest: false, pause: false });

const isTerminal = computed(() =>
  ['converged', 'exhausted', 'aborted'].includes(state.value?.phase));

function phaseClass(phase) {
  if (phase === 'converged') return 'ok';
  if (['paused', 'exhausted', 'aborted'].includes(phase)) return 'high';
  return '';
}
function formatSetpoints(sp) {
  return Object.entries(sp || {}).map(([k, v]) => `${k}=${v}`).join(', ');
}

async function loadCampaigns() {
  try {
    const data = await api.optimizerCampaigns();
    campaigns.value = Array.isArray(data) ? data : [];
  } catch { campaigns.value = []; }
}
async function selectCampaign(id) {
  selectedId.value = id;
  try {
    const data = await api.optimizerState(id);
    state.value = data;
  } catch (e) {
    state.value = { phase: 'error', next_action: { action: '-', reasons: [e.message] } };
  }
}
onMounted(loadCampaigns);

async function submitInit() {
  let parsed;
  try { parsed = JSON.parse(objective.value); } catch {
    initError.value = t('closedloop.common.jsonInvalid');
    return;
  }
  busy.value.init = true;
  initError.value = '';
  try {
    const data = await api.optimizerCampaign(parsed);
    await loadCampaigns();
    await selectCampaign(data.campaign_id);
  } catch (e) {
    initError.value = e.message;
  } finally { busy.value.init = false; }
}

async function submitDesign() {
  busy.value.design = true;
  try {
    const data = await api.optimizerRound({ campaign_id: selectedId.value, action: 'design' });
    lastDesign.value = data;
    await selectCampaign(selectedId.value);
  } catch (e) {
    lastDesign.value = null;
    ingestError.value = e.message;
  } finally { busy.value.design = false; }
}

// 由当前布点生成 trial_result 回执骨架（AWS/人工填入 measurements）
function makeReceiptTemplate() {
  if (!lastDesign.value) return;
  const skeleton = {
    result_version: '1.0',
    campaign_id: selectedId.value,
    round_id: lastDesign.value.round_id,
    trials: (lastDesign.value.trial_design?.trials || []).map((tr) => ({
      trial_id: tr.trial_id,
      status: 'completed',
      measurements: { [state.value?.objective?.target_metric || 'metric']: [0.0, 0.0, 0.0] },
    })),
  };
  trialResult.value = JSON.stringify(skeleton, null, 2);
}

async function submitIngest() {
  let parsed;
  try { parsed = JSON.parse(trialResult.value); } catch {
    ingestError.value = t('closedloop.common.jsonInvalid');
    return;
  }
  busy.value.ingest = true;
  ingestError.value = '';
  try {
    const data = await api.optimizerRound({
      campaign_id: selectedId.value, action: 'ingest', trial_result: parsed,
    });
    lastIngest.value = data;
    await selectCampaign(selectedId.value);
  } catch (e) {
    ingestError.value = e.message;
  } finally { busy.value.ingest = false; }
}

async function doPause() {
  busy.value.pause = true;
  try {
    await api.optimizerPause(selectedId.value);
    await selectCampaign(selectedId.value);
  } catch (e) { ingestError.value = e.message; } finally { busy.value.pause = false; }
}
async function doResume() {
  busy.value.pause = true;
  try {
    await api.optimizerResume(selectedId.value);
    await selectCampaign(selectedId.value);
  } catch (e) { ingestError.value = e.message; } finally { busy.value.pause = false; }
}
</script>

<style scoped>
.cl-actions { margin-top: 10px; display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.cl-screen-out { margin-top: 10px; display: flex; flex-direction: column; gap: 8px; }
tr.current td { background: var(--accent-soft); }
.mono-dim { font-family: var(--font-mono); font-size: 10.5px; color: var(--text-dim); }
</style>
