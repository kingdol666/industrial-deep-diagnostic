<template>
  <section class="catalog" :aria-label="$t('lines.catalog')">
    <div class="catalog-head">
      <h3>{{ $t('lines.catalog') }}</h3>
      <p>{{ $t('lines.catalogBoundary') }}</p>
    </div>
    <form class="catalog-controls" @submit.prevent="load()">
      <input v-model.trim="query" type="search" maxlength="120" :aria-label="$t('lines.catalogQuery')" :placeholder="$t('lines.catalogQuery')" />
      <select v-model="kind" :aria-label="$t('lines.kind')">
        <option value="">{{ $t('lines.allKinds') }}</option>
        <option v-for="value in kinds" :key="value" :value="value">{{ $t(`lines.kinds.${value}`) }}</option>
      </select>
      <button type="submit" class="btn btn-sm" :disabled="loading">{{ $t('common.search') }}</button>
    </form>
    <p v-if="error" role="alert" class="catalog-error">{{ error }}</p>
    <p v-if="loading" role="status">{{ $t('common.loading') }}</p>
    <p v-else-if="!error && !items.length">{{ $t('lines.emptyCatalog') }}</p>
    <ul v-if="items.length" class="catalog-items">
      <li v-for="item in items" :key="versionKey(item)">
        <div class="item-main">
          <strong>{{ item.title }}</strong>
          <span class="item-meta">{{ $t(`lines.kinds.${item.kind}`) }} · {{ $t('lines.version', { version: item.version }) }}</span>
          <p>{{ item.summary }}</p>
          <code>{{ item.asset_id }}</code>
        </div>
        <button v-if="selectable(item)" type="button" class="btn btn-sm" :aria-pressed="isSelected(item)"
          :disabled="!isSelected(item) && atLimit(item.kind)" @click="toggle(item)">
          {{ $t(isSelected(item) ? 'lines.remove' : item.kind === 'dataset' ? 'lines.selectDataset' : 'lines.selectExperience') }}
        </button>
      </li>
    </ul>
    <button v-if="cursor" type="button" class="btn btn-sm" :disabled="loading" @click="load(true)">{{ $t('lines.loadMore') }}</button>

    <template v-if="select">
      <details class="direct-reference">
        <summary>{{ $t('lines.addById') }}</summary>
        <p>{{ $t('lines.addByIdHint') }}</p>
        <form class="catalog-controls" @submit.prevent="addDirect">
          <select v-model="directKind" :aria-label="$t('lines.kind')">
            <option v-if="allowText" value="experience">{{ $t('lines.experienceRefs') }}</option>
            <option value="dataset">{{ $t('lines.kinds.dataset') }}</option>
          </select>
          <input v-model.trim="directId" required maxlength="36" :placeholder="$t('lines.assetId')" :aria-label="$t('lines.assetId')" />
          <input v-model="directVersion" type="number" required min="1" max="9007199254740991" step="1" :aria-label="$t('lines.versionNumber')" />
          <button class="btn btn-sm" type="submit" :disabled="atLimit(directKind)">{{ $t('lines.addVersion') }}</button>
        </form>
        <p v-if="directError" role="alert" class="catalog-error">{{ $t('lines.invalidRef') }}</p>
      </details>
      <div v-for="group in groups" :key="group.label" class="selection">
        <strong>{{ $t(`lines.${group.label}`) }} · {{ group.items.length }}/8</strong>
        <ul v-if="group.items.length" class="catalog-items">
          <li v-for="item in group.items" :key="versionKey(item)">
            <div class="item-main">
              <strong>{{ item.title || item.asset_id }}</strong>
              <span class="item-meta">{{ $t('lines.version', { version: item.version }) }}</span>
            </div>
            <button type="button" class="btn btn-sm" @click="toggle(item)">{{ $t('lines.remove') }}</button>
          </li>
        </ul>
        <p v-else>{{ $t('lines.noneSelected') }}</p>
      </div>
    </template>
  </section>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { api } from '../../api/index.js';

const props = defineProps({
  select: Boolean,
  allowText: { type: Boolean, default: true },
  references: { type: Array, default: () => [] },
  datasets: { type: Array, default: () => [] },
  revision: { type: Number, default: 0 },
});
const emit = defineEmits(['update:references', 'update:datasets']);
const { t } = useI18n();
const kinds = ['experience', 'memory_excerpt', 'dataset'];
const query = ref('');
const kind = ref('');
const loading = ref(false);
const error = ref('');
const items = ref([]);
const cursor = ref(null);
let activeFilters = {};
const directKind = ref(props.allowText ? 'experience' : 'dataset');
const directId = ref('');
const directVersion = ref(1);
const directError = ref(false);
const groups = computed(() => [
  ...(props.allowText ? [{ label: 'experienceRefs', items: props.references }] : []),
  { label: 'datasetRefs', items: props.datasets },
]);
watch(() => props.allowText, (value) => { if (!value) directKind.value = 'dataset'; });

const versionKey = (item) => `${item.asset_id}:${item.version}`;
const groupItems = (kind) => kind === 'dataset' ? props.datasets : props.references;
const atLimit = (kind) => groupItems(kind).length >= 8;
const isSelected = (item) => groupItems(item.kind).some((ref) => versionKey(ref) === versionKey(item));
const selectable = (item) => props.select && (item.kind === 'dataset' || props.allowText);

function toggle(item) {
  const values = groupItems(item.kind);
  const selected = isSelected(item);
  if (!selected && atLimit(item.kind)) return;
  const next = selected ? values.filter((ref) => versionKey(ref) !== versionKey(item)) : [...values, item];
  if (item.kind === 'dataset') emit('update:datasets', next);
  else emit('update:references', next);
}

function addDirect() {
  const version = Number(directVersion.value);
  const asset_id = directId.value.toLowerCase();
  directError.value = !/^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/.test(asset_id) || !Number.isSafeInteger(version) || version < 1;
  if (directError.value) return;
  const item = { asset_id, version, kind: directKind.value };
  if (!isSelected(item)) toggle(item);
  directId.value = '';
}

let loadSequence = 0;
async function load(more = false) {
  const sequence = ++loadSequence;
  if (!more) {
    activeFilters = { q: query.value, kind: kind.value };
    items.value = [];
    cursor.value = null;
  }
  loading.value = true;
  error.value = '';
  try {
    const result = await api.listKnowledgeCatalog({ ...activeFilters, cursor: more ? cursor.value : null });
    if (sequence !== loadSequence) return;
    const combined = [...items.value, ...result.items];
    items.value = [...new Map(combined.map((item) => [versionKey(item), item])).values()];
    cursor.value = result.next_cursor;
  } catch {
    if (sequence === loadSequence) error.value = t('lines.catalogError');
  } finally {
    if (sequence === loadSequence) loading.value = false;
  }
}

onMounted(() => load());
watch(() => props.revision, () => load());
</script>

<style scoped>
.catalog { display: grid; gap: .7rem; padding: 1rem; border: 1px solid var(--border-strong); border-radius: 8px; background: var(--surface-soft); min-width: 0; }
.catalog h3, .catalog p, .catalog ul { margin: 0; }
.catalog p { color: var(--text2); font-size: .85rem; }
.catalog-head { display: grid; gap: .2rem; }
.catalog-controls { display: flex; flex-wrap: wrap; gap: .45rem; align-items: stretch; }
.catalog-controls :is(input, select) { color: var(--text); background: var(--surface); border: 1px solid var(--border-strong); border-radius: 5px; padding: .4rem .55rem; min-width: 0; font: inherit; }
.catalog-controls input:not([type='number']) { flex: 1 1 13rem; }
.catalog-controls input[type='number'] { width: 5rem; }
.catalog-items { list-style: none; padding: 0; }
.catalog-items li { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: .6rem; border-top: 1px solid var(--border); padding: .65rem 0; }
.item-main { display: grid; gap: .18rem; min-width: 0; overflow-wrap: anywhere; }
.item-meta, code { color: var(--text2); font: .75rem var(--font-mono); }
.catalog > .btn { justify-self: start; }
.direct-reference { padding: .6rem 0; border-block: 1px solid var(--border); }
.direct-reference summary { cursor: pointer; }
.direct-reference p, .direct-reference form { margin-block-start: .45rem; }
.selection > strong { font-size: .85rem; }
.catalog .catalog-error { color: var(--red); }
</style>
