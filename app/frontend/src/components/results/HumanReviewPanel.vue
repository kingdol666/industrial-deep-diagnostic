<template>
  <section class="review-panel" data-testid="human-review">
    <header>
      <strong>{{ $t('review.title') }}</strong>
      <span v-if="review" :class="['review-badge', review.status]">{{ $t(`review.${review.status}`) }}</span>
      <small v-if="review?.revision">{{ $t('review.revision', { n: review.revision, user: review.actor?.username }) }}</small>
    </header>
    <p v-if="error" role="alert">{{ error }}</p>
    <button v-if="error" type="button" class="btn btn-sm" :disabled="busy" @click="load">{{ $t('review.reload') }}</button>
    <p v-if="loading">{{ $t('common.loadingEllipsis') }}</p>
    <form v-if="review" @submit.prevent="save" class="review-form">
      <p v-if="review.stale" role="status">{{ $t('review.stale') }}</p>
      <p>{{ $t('review.hint') }}</p>
      <label>{{ $t('review.status') }}
        <select v-model="draft.status" data-testid="review-status">
          <option v-for="status in statuses" :key="status" :value="status">{{ $t(`review.${status}`) }}</option>
        </select>
      </label>
      <label>{{ $t('review.comment') }}<textarea v-model="draft.comment" data-testid="review-comment" rows="2" maxlength="4000" /></label>
      <label>{{ $t('review.takeaway') }}<textarea v-model="draft.takeaway" data-testid="review-takeaway" rows="2" maxlength="1500" /></label>
      <label class="review-checkbox"><input type="checkbox" v-model="draft.reuse_enabled" data-testid="review-reuse" />{{ $t('review.allowReuse') }}</label>
      <div v-if="review.synthesis.text" class="review-synthesis" data-testid="review-synthesis">
        <strong>{{ $t(`review.${review.synthesis.source}`) }}</strong>
        <p>{{ review.synthesis.text }}</p>
      </div>
      <label>{{ $t('review.summary') }}<textarea v-model="draft.summary" data-testid="review-summary" rows="2" maxlength="6000" :placeholder="$t('review.summaryHint')" /></label>
      <div class="review-actions">
        <button type="submit" class="btn btn-primary btn-sm" :disabled="busy || conflict" data-testid="review-save">{{ $t('review.save') }}</button>
        <button v-if="review.status !== 'unreviewed'" type="button" class="btn btn-sm" :disabled="busy || conflict" data-testid="review-undo" @click="save('unreviewed')">{{ $t('review.undo') }}</button>
        <button v-if="review.revision" type="button" class="btn btn-sm" :disabled="busy" :aria-expanded="showHistory" data-testid="review-history" @click="toggleHistory">{{ $t('review.history') }}</button>
        <span v-if="saved" role="status">{{ $t('review.saved') }}</span>
      </div>
    </form>
    <ol v-if="showHistory" class="review-history">
      <li v-for="item in revisions" :key="item.revision">
        <details>
          <summary>{{ $t('review.revision', { n: item.revision, user: item.actor.username }) }} · {{ $t(`review.${item.status}`) }} · <time :datetime="item.created_at">{{ displayDate(item.created_at) }}</time></summary>
          <p v-if="item.comment">{{ $t('review.comment') }}: {{ item.comment }}</p>
          <p v-if="item.takeaway">{{ $t('review.takeaway') }}: {{ item.takeaway }}</p>
          <p v-if="item.synthesis.text">{{ $t(`review.${item.synthesis.source}`) }}: {{ item.synthesis.text }}</p>
        </details>
      </li>
    </ol>
    <button v-if="showHistory && nextBefore" type="button" class="btn btn-sm" :disabled="busy" @click="loadHistory(nextBefore)">{{ $t('review.more') }}</button>
  </section>
</template>

<script setup>
import { reactive, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { api } from '../../api/index.js';

const props = defineProps({ runId: { type: String, required: true } });
const emit = defineEmits(['updated']);
const { t, locale } = useI18n();
const statuses = ['unreviewed', 'confirmed', 'ineffective'];
const review = ref(null);
const draft = reactive({});
const loading = ref(false);
const busy = ref(false);
const saved = ref(false);
const conflict = ref(false);
const error = ref('');
const revisions = ref([]);
const showHistory = ref(false);
const nextBefore = ref(null);

function assign(value) {
  review.value = value;
  Object.assign(draft, { status: value.status, comment: value.comment ?? '', takeaway: value.takeaway ?? '',
    reuse_enabled: value.reuse_enabled, summary: value.synthesis.source === 'human' ? value.synthesis.text : '' });
}

async function load() {
  loading.value = true;
  review.value = null;
  error.value = '';
  saved.value = false;
  conflict.value = false;
  showHistory.value = false;
  try { assign(await api.getResultReview(props.runId)); }
  catch (err) { error.value = err.code === 'REVIEW_UNAVAILABLE' ? t('review.unavailable') : err.message; }
  finally { loading.value = false; }
}

async function save(status) {
  busy.value = true;
  saved.value = false;
  error.value = '';
  try {
    const patch = typeof status === 'string'
      ? { status }
      : { status: draft.status, comment: draft.comment || null, takeaway: draft.takeaway || null, reuse_enabled: draft.reuse_enabled };
    const previousSummary = review.value.synthesis.source === 'human' ? review.value.synthesis.text : '';
    if (typeof status !== 'string' && draft.summary !== previousSummary) patch.summary = draft.summary || null;
    const result = await api.patchResultReview(props.runId, { revision: review.value.revision, ...patch });
    assign(result);
    saved.value = true;
    emit('updated', result);
    if (showHistory.value) await loadHistory();
  } catch (err) {
    conflict.value = err.code === 'REVIEW_REVISION_CONFLICT';
    error.value = conflict.value ? t('review.conflict') : err.message;
  } finally { busy.value = false; }
}

async function loadHistory(before) {
  busy.value = true;
  try {
    const data = await api.listResultReviewHistory(props.runId, before);
    revisions.value = before ? [...revisions.value, ...data.data] : data.data;
    nextBefore.value = data.next_before;
  } catch (err) { error.value = err.message; }
  finally { busy.value = false; }
}

function toggleHistory() {
  showHistory.value = !showHistory.value;
  if (showHistory.value) loadHistory();
}

function displayDate(value) { return new Date(value).toLocaleString(locale.value); }
watch(() => props.runId, load, { immediate: true });
</script>

<style scoped>
.review-panel { padding: 14px; border: 1px solid var(--border); border-radius: 8px; margin-block: 12px; }
.review-panel header, .review-actions { display: flex; align-items: center; flex-wrap: wrap; gap: 8px 12px; }
.review-panel header small { opacity: .78; }
.review-panel p { margin-block: 4px; }
.review-badge { padding: 2px 8px; border: 1px solid currentColor; border-radius: 12px; font-size: .82em; }
.review-badge.confirmed { color: #4ca87d; }
.review-badge.ineffective { color: #d37b66; }
.review-form { display: grid; gap: 10px; margin-top: 8px; }
.review-form label { display: grid; gap: 3px; }
.review-form select { width: fit-content; max-width: 100%; }
.review-form textarea, .review-form select { color: inherit; font: inherit; background: transparent; padding: 6px; border: 1px solid var(--border); border-radius: 5px; }
.review-form textarea { width: 100%; resize: vertical; }
.review-form .review-checkbox { display: flex; gap: 6px; align-items: center; }
.review-synthesis, .review-history { border-left: 2px solid var(--border-strong); padding-left: 12px; }
.review-synthesis p, .review-history p { white-space: pre-wrap; overflow-wrap: anywhere; }
.review-history { padding-left: 28px; }
.review-history summary { cursor: pointer; }
</style>
