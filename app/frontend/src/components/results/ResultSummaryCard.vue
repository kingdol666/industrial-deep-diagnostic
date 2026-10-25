<template>
  <div class="result-card" :data-testid="`result-card-${resultId}`">
    <div v-if="loading" class="result-card-muted">{{ $t('results.loadingDetail') }}</div>

    <div v-else-if="error" class="result-card-muted">
      {{ $t('results.detailLoadFailed') }}{{ error.message || error }}
    </div>

    <template v-else-if="detail">
      <!-- auto summary (system-managed, read-only) -->
      <div class="result-summary-block">
        <div class="result-summary-head">
          <span class="detail-label">{{ $t('results.autoSummary') }}</span>
          <span v-if="detail.derived" class="badge badge-soft" :title="$t('results.derivedHint')">
            {{ $t('results.derivedBadge') }}
          </span>
        </div>
        <p class="result-summary-text" :data-testid="`result-summary-${resultId}`">
          {{ detail.summary || $t('results.noSummary') }}
        </p>
        <div v-if="keyNumberEntries.length" class="result-key-numbers">
          <span
            v-for="[k, v] in keyNumberEntries"
            :key="k"
            class="result-kn-chip"
            :title="detail.summary_json?.sources?.[k] || k"
          >
            <span class="result-kn-key">{{ keyLabel(k) }}</span>
            <span class="result-kn-val">{{ formatKn(v) }}</span>
          </span>
        </div>
        <div v-if="profileSentence" class="result-profile">{{ profileSentence }}</div>
      </div>

      <!-- user-editable description -->
      <div class="result-desc-block">
        <span class="detail-label">{{ $t('results.description') }}</span>
        <div v-if="!editing" class="result-desc-view">
          <p class="result-desc-text" :class="{ muted: !detail.description }" :data-testid="`result-desc-${resultId}`">
            {{ detail.description || $t('results.descriptionEmpty') }}
          </p>
          <button class="btn btn-sm" :data-testid="`result-desc-edit-${resultId}`" @click="startEdit">
            {{ $t('results.editDescription') }}
          </button>
        </div>
        <div v-else class="result-desc-edit">
          <textarea
            v-model="draftDescription"
            rows="3"
            maxlength="2000"
            :data-testid="`result-desc-input-${resultId}`"
            :placeholder="$t('results.descriptionPlaceholder')"
          ></textarea>
          <div class="result-desc-actions">
            <button class="btn btn-sm btn-primary" :disabled="saving" :data-testid="`result-desc-save-${resultId}`" @click="save">
              {{ $t('common.save') }}
            </button>
            <button class="btn btn-sm" :disabled="saving" @click="cancelEdit">{{ $t('common.cancel') }}</button>
            <span v-if="saveError" class="error-text">{{ saveError }}</span>
          </div>
        </div>
      </div>

      <!-- user-editable tags -->
      <div class="result-tags-block">
        <span class="detail-label">{{ $t('results.tags') }}</span>
        <div v-if="!editingTags" class="result-tags-view">
          <span v-if="!detail.tags?.length" class="muted">{{ $t('results.tagsEmpty') }}</span>
          <span v-for="tag in detail.tags" :key="tag" class="result-tag-chip" :data-testid="`result-tag-${resultId}`">{{ tag }}</span>
          <button class="btn btn-sm" :data-testid="`result-tags-edit-${resultId}`" @click="startEditTags">
            {{ $t('results.editTags') }}
          </button>
        </div>
        <div v-else class="result-tags-edit">
          <input
            v-model="draftTags"
            type="text"
            maxlength="680"
            :data-testid="`result-tags-input-${resultId}`"
            :placeholder="$t('results.tagsPlaceholder')"
          />
          <div class="result-desc-actions">
            <button class="btn btn-sm btn-primary" :disabled="saving" :data-testid="`result-tags-save-${resultId}`" @click="saveTags">
              {{ $t('common.save') }}
            </button>
            <button class="btn btn-sm" :disabled="saving" @click="editingTags = false">{{ $t('common.cancel') }}</button>
            <span v-if="tagsError" class="error-text">{{ tagsError }}</span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { api } from '../../api/index.js';

const props = defineProps({
  resultId: { type: String, required: true },
});
const emit = defineEmits(['updated']);

const { t } = useI18n();
const detail = ref(null);
const loading = ref(false);
const error = ref(null);

const editing = ref(false);
const editingTags = ref(false);
const draftDescription = ref('');
const draftTags = ref('');
const saving = ref(false);
const saveError = ref('');
const tagsError = ref('');

const keyNumberEntries = computed(() => {
  const kn = detail.value?.summary_json?.key_numbers;
  if (!kn || typeof kn !== 'object') return [];
  return Object.entries(kn).filter(([, v]) => v !== null && v !== undefined && v !== '');
});

const profileSentence = computed(() => {
  const p = detail.value?.summary_json?.data_profile;
  if (!p) return '';
  const bits = [];
  if (p.rows !== null && p.rows !== undefined) bits.push(`${t('results.profileRows')} ${p.rows}`);
  if (Array.isArray(p.parameter_cols) && p.parameter_cols.length) {
    bits.push(`${t('results.profileParams')} ${p.parameter_cols.length}`);
  }
  if (p.time_range?.[0]) bits.push(`${p.time_range[0]} ~ ${p.time_range[1] ?? ''}`.trim());
  return bits.join(' · ');
});

function keyLabel(k) {
  return t(`results.kn.${k}`) !== `results.kn.${k}` ? t(`results.kn.${k}`) : k;
}

function formatKn(v) {
  if (typeof v === 'boolean') return v ? '✓' : '✗';
  if (typeof v === 'number') return Number.isInteger(v) ? String(v) : String(Number(v.toFixed(3)));
  if (v !== null && typeof v === 'object') {
    // Compact object rendering (e.g. findings_by_severity → info 2 · warn 3).
    const entries = Array.isArray(v) ? v.map((x, i) => [String(i), x]) : Object.entries(v);
    const text = entries.slice(0, 6).map(([k, n]) => `${k} ${formatKn(n)}`).join(' · ');
    return entries.length > 6 ? `${text} …` : text;
  }
  return String(v);
}

async function load() {
  loading.value = true;
  error.value = null;
  try {
    detail.value = await api.getResultDetail(props.resultId, { includeMd: false });
  } catch (err) {
    error.value = err;
  } finally {
    loading.value = false;
  }
}

function startEdit() {
  draftDescription.value = detail.value?.description || '';
  saveError.value = '';
  editing.value = true;
}

function cancelEdit() {
  editing.value = false;
  draftDescription.value = '';
}

async function save() {
  if (saving.value) return;
  saving.value = true;
  saveError.value = '';
  try {
    const clean = draftDescription.value.trim();
    detail.value = await api.patchResult(props.resultId, { description: clean || null });
    editing.value = false;
    emit('updated', detail.value);
  } catch (err) {
    saveError.value = err.message || String(err);
  } finally {
    saving.value = false;
  }
}

function startEditTags() {
  draftTags.value = (detail.value?.tags || []).join(', ');
  tagsError.value = '';
  editingTags.value = true;
}

async function saveTags() {
  if (saving.value) return;
  saving.value = true;
  tagsError.value = '';
  const tags = draftTags.value.split(/[,，]/).map((s) => s.trim()).filter(Boolean);
  try {
    detail.value = await api.patchResult(props.resultId, { tags });
    editingTags.value = false;
    emit('updated', detail.value);
  } catch (err) {
    tagsError.value = err.message || String(err);
  } finally {
    saving.value = false;
  }
}

defineExpose({ reload: load });

onMounted(load);
</script>

<style scoped>
.result-card {
  border: 1px solid var(--border-color, #d8dee9);
  border-radius: 10px;
  padding: 14px 16px;
  background: var(--surface-soft, #f7f9fc);
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.result-card-muted { color: var(--text-muted, #7b869a); font-size: 13px; }
.result-summary-head { display: flex; align-items: center; gap: 8px; }
.result-summary-text {
  margin: 6px 0 0;
  font-size: 13.5px;
  line-height: 1.65;
  white-space: pre-wrap;
}
.result-key-numbers { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
.result-kn-chip {
  display: inline-flex; gap: 6px; align-items: baseline;
  border: 1px solid var(--border-color, #d8dee9); border-radius: 999px;
  padding: 2px 10px; font-size: 12px; background: var(--surface, #fff);
}
.result-kn-key { color: var(--text-muted, #7b869a); }
.result-kn-val { font-weight: 600; }
.result-profile { margin-top: 6px; font-size: 12px; color: var(--text-muted, #7b869a); }
.result-desc-view { display: flex; gap: 10px; align-items: flex-start; }
.result-desc-text { margin: 6px 0 0; flex: 1; font-size: 13.5px; line-height: 1.6; }
.result-desc-text.muted { color: var(--text-muted, #9aa4b5); font-style: italic; }
.result-desc-edit textarea, .result-tags-edit input {
  width: 100%; box-sizing: border-box; margin-top: 6px;
  border: 1px solid var(--border-color, #d8dee9); border-radius: 8px; padding: 8px 10px;
  font: inherit; font-size: 13px;
}
.result-desc-actions { display: flex; gap: 8px; align-items: center; margin-top: 8px; }
.result-tags-view { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.result-tag-chip {
  border-radius: 999px; padding: 2px 10px; font-size: 12px;
  background: var(--accent-soft, #e8f0fe); color: var(--accent-text, #2456c4);
}
.muted { color: var(--text-muted, #9aa4b5); }
.error-text { color: #c0392b; font-size: 12px; }
</style>
