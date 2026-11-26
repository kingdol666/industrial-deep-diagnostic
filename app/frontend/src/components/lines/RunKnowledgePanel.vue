<template>
  <section class="knowledge-panel" :aria-label="$t('lines.runKnowledge')">
    <header class="panel-head">
      <div><h2>{{ $t('lines.runKnowledge') }}</h2><p>{{ $t('lines.boundLine') }} · <code>{{ lineId }}</code></p></div>
      <span class="state">{{ $t(policy?.mode === 'on_demand' ? 'lines.onDemand' : 'lines.disabled') }}</span>
    </header>
    <p v-if="policy?.mode === 'on_demand'">{{ $t(policy.own_line ? 'lines.ownIncluded' : 'lines.ownExcluded') }}</p>
    <div v-for="group in selectedGroups" :key="group.label" class="pin-list">
      <strong>{{ $t(`lines.${group.label}`) }}</strong>
      <ul><li v-for="ref in group.items" :key="`${ref.asset_id}:${ref.version}`"><code>{{ ref.asset_id }}</code> · {{ $t('lines.version', { version: ref.version }) }}</li></ul>
    </div>
    <template v-if="policy?.mode === 'on_demand'">
      <div class="preview-block">
        <h3>{{ $t('lines.previewTitle') }}</h3>
        <p>{{ $t('lines.previewHint') }}</p>
        <form class="preview-form" @submit.prevent="search(query)">
          <input v-model.trim="query" type="search" minlength="2" maxlength="200" required :aria-label="$t('lines.previewQuery')" :placeholder="$t('lines.previewQuery')" />
          <button type="submit" class="btn btn-sm" :disabled="reading || query.length < 2">{{ $t('lines.previewAction') }}</button>
          <button v-if="lastQuery" type="button" class="btn btn-sm" :disabled="reading" @click="search(lastQuery)">{{ $t('lines.recheck') }}</button>
        </form>
        <p v-if="reading" role="status">{{ $t('common.loading') }}</p>
        <p v-if="previewError" role="alert" class="error">{{ previewError }}</p>
        <p v-if="noMatch" role="status">{{ $t('lines.noMatch') }}</p>
        <ul v-if="items.length" class="preview-items">
          <li v-for="item in items" :key="item.ref_id">
            <div class="panel-head">
              <div><strong>{{ item.title }}</strong><p>{{ sourceLabel(item) }} · {{ $t(`lines.review.${item.human_review}`) }} · {{ item.evidence_level }}</p></div>
              <button type="button" class="btn btn-sm" :disabled="reading" @click="getItem(item.ref_id)">{{ $t('lines.checkDetails') }}</button>
            </div>
            <p>{{ item.excerpt }}</p>
            <p v-if="item.applicability">{{ $t('lines.applicability') }}: {{ item.applicability }}</p>
            <p><code>{{ item.ref_id }}</code><template v-if="item.asset_id"> · <code>{{ item.asset_id }}</code></template></p>
            <p v-if="detail?.ref_id === item.ref_id" class="item-detail">{{ detail.detail }}</p>
          </li>
        </ul>
      </div>
      <div class="audit-block">
        <div class="panel-head">
          <h3>{{ $t('lines.audit') }}</h3>
          <button class="btn btn-sm" type="button" :disabled="auditLoading" @click="loadAudit">{{ $t('lines.refreshAudit') }}</button>
        </div>
        <p v-if="auditError" role="alert" class="error">{{ auditError }}</p>
        <template v-else-if="auditLoaded">
          <p class="audit-states">
            <span v-for="channel in channels" :key="channel" class="state">
              {{ $t(`lines.channels.${channel}`) }}: {{ $t(audit.some((row) => row.channel === channel && row.item_count > 0) ? 'lines.retrieved' : 'lines.notRetrieved') }}
            </span>
          </p>
          <p v-if="!audit.length">{{ $t('lines.emptyAudit') }}</p>
          <ul v-else class="audit-list">
            <li v-for="row in audit" :key="row.retrieval_id">
              <div class="audit-row">
                <strong>{{ $t(`lines.channels.${row.channel}`) }} · {{ $t(`lines.actions.${row.action}`) }}</strong>
                <span>{{ outcomeLabel(row.outcome) }} · {{ $t('lines.resultCount', { count: row.item_count }) }}</span>
                <time :datetime="row.created_at">{{ auditTime(row.created_at) }}</time>
              </div>
              <ul v-if="row.refs?.length" class="audit-refs">
                <li v-for="ref in row.refs" :key="ref.ref_id">{{ sourceLabel(ref) }} · <code>{{ ref.ref_id }}</code></li>
              </ul>
            </li>
          </ul>
        </template>
        <p v-else-if="auditLoading" role="status">{{ $t('common.loading') }}</p>
      </div>
    </template>
  </section>
</template>

<script setup>
import { computed, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { api } from '../../api/index.js';

const props = defineProps({
  runId: { type: String, required: true },
  lineId: { type: String, required: true },
  policy: Object,
  datasets: { type: Array, default: () => [] },
  status: String,
});
const { t, locale } = useI18n();
const channels = ['preview', 'agent'];
const query = ref('');
const lastQuery = ref('');
const items = ref([]);
const detail = ref(null);
const reading = ref(false);
const noMatch = ref(false);
const previewError = ref('');
const audit = ref([]);
const auditLoaded = ref(false);
const auditLoading = ref(false);
const auditError = ref('');
let auditSequence = 0;
const selectedGroups = computed(() => [
  { label: 'experienceRefs', items: props.policy?.references ?? [] },
  { label: 'datasetRefs', items: props.datasets },
].filter((group) => group.items.length));

function sourceLabel(item) {
  return `${t(`lines.sources.${item.source_kind}`)} · ${t('lines.version', { version: item.source_version })}`;
}

function outcomeLabel(outcome) {
  if (outcome === 'ok') return t('lines.auditOk');
  if (outcome === 'no_match') return t('lines.auditNoMatch');
  return t('lines.auditDenied');
}

function auditTime(value) {
  const time = new Date(/^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d$/.test(value) ? `${value.replace(' ', 'T')}Z` : value);
  return Number.isNaN(time.getTime()) ? value : time.toLocaleString(locale.value);
}

async function loadAudit() {
  const sequence = ++auditSequence;
  auditLoading.value = true;
  auditError.value = '';
  try {
    const result = await api.listRunRetrievals(props.runId);
    if (sequence !== auditSequence) return;
    audit.value = result.items;
    auditLoaded.value = true;
  } catch {
    if (sequence === auditSequence) auditError.value = t('lines.auditError');
  } finally {
    if (sequence === auditSequence) auditLoading.value = false;
  }
}

async function search(value) {
  if (reading.value || !value) return;
  query.value = value;
  lastQuery.value = value;
  items.value = [];
  detail.value = null;
  noMatch.value = false;
  previewError.value = '';
  reading.value = true;
  try {
    const result = await api.searchRunKnowledge(props.runId, value);
    items.value = result.items;
    noMatch.value = !items.value.length;
  } catch (err) {
    previewError.value = t(err.status === 403 || err.status === 404 || err.status === 409 ? 'lines.previewUnavailable' : 'lines.previewError');
  } finally {
    reading.value = false;
    loadAudit();
  }
}

async function getItem(refId) {
  if (reading.value) return;
  detail.value = null;
  previewError.value = '';
  reading.value = true;
  try {
    detail.value = (await api.getRunKnowledgeItem(props.runId, refId)).item;
  } catch (err) {
    if ([403, 404, 409].includes(err.status)) {
      items.value = items.value.filter((item) => item.ref_id !== refId);
      previewError.value = t('lines.previewUnavailable');
    } else {
      previewError.value = t('lines.previewError');
    }
  } finally {
    reading.value = false;
    loadAudit();
  }
}

watch(() => [props.policy?.mode, props.status], () => {
  if (props.policy?.mode === 'on_demand') loadAudit();
}, { immediate: true });
</script>

<style scoped>
.knowledge-panel, .preview-block, .audit-block { display: grid; gap: .6rem; min-width: 0; }
.knowledge-panel { margin-bottom: .75rem; padding: .9rem; background: var(--surface); border: 1px solid var(--border-strong); border-radius: 8px; }
.knowledge-panel :is(h2, h3, p, ul) { margin: 0; }
.knowledge-panel h2 { font-size: 1rem; }
.knowledge-panel h3 { font-size: .9rem; }
.knowledge-panel p { color: var(--text2); font-size: .85rem; overflow-wrap: anywhere; }
.panel-head, .preview-form, .audit-row, .audit-states { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: .4rem; }
.preview-form input { flex: 1 1 13rem; min-width: 0; padding: .45rem .55rem; color: var(--text); background: var(--surface-soft); border: 1px solid var(--border-strong); border-radius: 5px; font: inherit; }
.preview-block, .audit-block { border-top: 1px solid var(--border-strong); padding-top: .7rem; }
.preview-items, .audit-list { list-style: none; padding: 0; max-height: 24rem; overflow: auto; }
.preview-items > li, .audit-list > li { border-top: 1px solid var(--border); padding: .55rem .15rem; display: grid; gap: .2rem; overflow-wrap: anywhere; }
.pin-list ul, .audit-refs { padding-inline-start: 1.2rem; }
.pin-list, .audit-row, .audit-refs { font-size: .82rem; color: var(--text2); overflow-wrap: anywhere; }
code, time, .state { color: var(--text2); font: .75rem var(--font-mono); overflow-wrap: anywhere; }
.state { padding: .22rem .4rem; border: 1px solid var(--border-strong); border-radius: 4px; }
.audit-states { justify-content: flex-start; }
.knowledge-panel .item-detail { padding: .5rem; background: var(--surface-muted); color: var(--text); white-space: pre-wrap; }
.knowledge-panel .error { color: var(--red); }
</style>
