<template>
  <div class="data-picker">
    <div class="data-picker-head">
      <span class="data-picker-label">{{ label }}</span>
      <span class="data-picker-current">{{ currentLabel }}</span>
      <button v-if="currentFolder" type="button" class="data-picker-up" @click="goUp">
        {{ $t('closedloop.dataPicker.up') }}
      </button>
    </div>
    <div v-if="loading" class="data-picker-state">{{ $t('closedloop.dataPicker.loading') }}</div>
    <div v-else-if="error" class="data-picker-state error">{{ error }}</div>
    <div v-else class="data-picker-list">
      <button
        v-for="entry in folders" :key="entry.name"
        type="button" class="data-picker-folder" @click="openFolder(entry.name)">
        <span aria-hidden="true">📁</span>
        <span>{{ entry.name }}</span>
        <span aria-hidden="true">›</span>
      </button>
      <button v-if="allowFolder && currentFolder" type="button" class="data-picker-select-folder" @click="selectCurrentFolder">
        {{ $t('closedloop.dataPicker.useFolder') }} · data/{{ currentFolder }}
      </button>
      <div v-if="inputPath && inputType === 'directory'" class="data-picker-directory-selected">
        {{ $t('closedloop.dataPicker.selectedFolder') }}: {{ inputPath }}
      </div>
      <button
        v-for="entry in dataFiles" :key="entry.name"
        type="button"
        class="data-picker-file"
        :class="{ selected: inputType === 'file' && pathFor(entry.name) === inputPath }"
        :aria-pressed="inputType === 'file' && pathFor(entry.name) === inputPath"
        @click="selectFile(entry.name)">
        <span aria-hidden="true">▤</span>
        <span class="data-picker-file-name">{{ entry.name }}</span>
        <span class="data-picker-meta">{{ formatSize(entry.size) }} · {{ entry.ext }}</span>
      </button>
      <p v-if="entries.length === 0" class="data-picker-state">
        {{ $t('closedloop.dataPicker.empty') }}
      </p>
      <p v-else-if="!dataFiles.length" class="data-picker-hint">
        {{ $t('closedloop.dataPicker.noFiles') }}
      </p>
      <p v-else-if="!folders.length" class="data-picker-hint">
        {{ $t('closedloop.dataPicker.noFolders') }}
      </p>
    </div>
    <div class="data-picker-selection">
      <span>{{ $t('closedloop.dataPicker.selected') }}:</span>
      <strong>{{ inputPath || $t('closedloop.dataPicker.none') }}</strong>
      <span v-if="inputPath && inputType === 'file' && !isSupportedPath(inputPath)" class="data-picker-incompatible">
        {{ $t('closedloop.dataPicker.incompatible') }}
      </span>
      <button v-if="inputPath" type="button" class="data-picker-clear" @click="clearSelection">
        {{ $t('closedloop.dataPicker.clear') }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { api } from '../../api/index.js';

const props = defineProps({
  modelValue: { type: Object, default: () => ({ kind: 'file', path: '' }) },
  label: { type: String, required: true },
  extensions: { type: Array, default: () => ['.csv'] },
  allowFolder: { type: Boolean, default: false },
});
const emit = defineEmits(['update:modelValue', 'compatibility']);

const currentFolder = ref('');
const entries = ref([]);
const loading = ref(false);
const error = ref('');
const inputType = computed(() => props.modelValue?.kind || 'file');
const inputPath = computed(() => props.modelValue?.path || '');
const folders = computed(() => entries.value.filter((entry) => entry.type === 'folder'));
const allowedExtensions = computed(() => new Set(props.extensions.map((ext) => String(ext).toLowerCase())));
const dataFiles = computed(() => entries.value.filter((entry) =>
  entry.type === 'file' && allowedExtensions.value.has(String(entry.ext || '').toLowerCase())));
const currentLabel = computed(() => currentFolder.value ? `data/${currentFolder.value}` : 'data/');
const compatible = computed(() => !inputPath.value || inputType.value === 'directory' || isSupportedPath(inputPath.value));
watch(compatible, (value) => emit('compatibility', value), { immediate: true });

async function loadFolder(path = '') {
  loading.value = true;
  error.value = '';
  try {
    entries.value = await api.browseData(path) || [];
    currentFolder.value = path;
  } catch (err) {
    entries.value = [];
    error.value = err.message || String(err);
  } finally {
    loading.value = false;
  }
}

function openFolder(name) {
  loadFolder(currentFolder.value ? `${currentFolder.value}/${name}` : name);
}
function goUp() {
  const parts = currentFolder.value.split('/');
  parts.pop();
  loadFolder(parts.join('/'));
}
function pathFor(name) {
  const path = currentFolder.value ? `${currentFolder.value}/${name}` : name;
  return `data/${path}`;
}
function persist(value) {
  try { localStorage.setItem('closedloop_selected_data_input', JSON.stringify(value)); } catch { /* optional persistence */ }
  emit('update:modelValue', value);
}
function selectFile(name) {
  persist({ kind: 'file', path: pathFor(name) });
}
function selectCurrentFolder() {
  if (!currentFolder.value) return;
  persist({ kind: 'directory', path: `data/${currentFolder.value}` });
}
function clearSelection() {
  try { localStorage.removeItem('closedloop_selected_data_input'); } catch { /* optional persistence */ }
  emit('update:modelValue', { kind: 'file', path: '' });
}
function isSupportedPath(value) {
  const normalized = String(value || '').replace(/\\/g, '/');
  const basename = normalized.slice(normalized.lastIndexOf('/') + 1);
  const ext = basename.includes('.') ? `.${basename.split('.').pop()?.toLowerCase()}` : '';
  return allowedExtensions.value.has(ext);
}
function formatSize(bytes) {
  if (bytes == null) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

onMounted(() => {
  let saved = props.modelValue;
  if (!saved?.path) {
    try { saved = JSON.parse(localStorage.getItem('closedloop_selected_data_input') || 'null'); } catch { saved = null; }
    if (saved?.path && (saved.kind === 'directory' || isSupportedPath(saved.path))) emit('update:modelValue', saved);
  }
  const path = String(saved?.path || '').replace(/\\\\/g, '/').replace(/^data\//, '');
  const parts = path.split('/').filter(Boolean);
  loadFolder(saved?.kind === 'directory' ? path : parts.length > 1 ? parts.slice(0, -1).join('/') : '');
});

watch(() => props.modelValue?.path, (value) => {
  if (!value) return;
  const normalized = String(value).replace(/\\\\/g, '/').replace(/^data\//, '');
  const parts = normalized.split('/').filter(Boolean);
  const folder = props.modelValue?.kind === 'directory' ? normalized : parts.length > 1 ? parts.slice(0, -1).join('/') : '';
  if (folder !== currentFolder.value) loadFolder(folder);
});
</script>

<style scoped>
.data-picker { display: flex; flex-direction: column; gap: 8px; min-width: 0; }
.data-picker-head { display: flex; align-items: center; gap: 8px; min-width: 0; }
.data-picker-label { font-family: var(--font-mono); font-size: 10.5px; letter-spacing: .06em; text-transform: uppercase; color: var(--text3); }
.data-picker-current { margin-left: auto; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font: 11px var(--font-mono); color: var(--text2); }
.data-picker-up, .data-picker-clear { appearance: none; border: 1px solid var(--border-strong); border-radius: 5px; background: transparent; color: var(--text2); padding: 3px 7px; cursor: pointer; font: inherit; }
.data-picker-list { display: flex; flex-direction: column; gap: 4px; max-height: 190px; overflow-y: auto; border: 1px solid var(--border); border-radius: 6px; padding: 5px; background: var(--surface-soft); }
.data-picker-folder, .data-picker-file { display: flex; align-items: center; gap: 8px; width: 100%; min-width: 0; border: 1px solid transparent; border-radius: 5px; padding: 6px 8px; text-align: left; color: var(--text2); background: transparent; cursor: pointer; font: 12px var(--font-ui); }
.data-picker-folder:hover, .data-picker-file:hover, .data-picker-select-folder:hover { border-color: var(--border-accent); background: var(--accent-soft); }
.data-picker-directory-selected { padding: 6px 8px; border: 1px solid var(--accent); border-radius: 5px; color: var(--accent-bright); font: 11px var(--font-mono); }
.data-picker-select-folder { width: 100%; border: 1px solid var(--border-accent); border-radius: 5px; padding: 6px 8px; background: var(--accent-soft); color: var(--accent-bright); cursor: pointer; text-align: left; font: 12px var(--font-ui); }
.data-picker-file.selected { border-color: var(--accent); background: var(--accent-soft); color: var(--accent-bright); }
.data-picker-file-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.data-picker-meta { font: 10px var(--font-mono); color: var(--text3); white-space: nowrap; }
.data-picker-state, .data-picker-hint { margin: 4px; color: var(--text3); font-size: 12px; }
.data-picker-state.error { color: #e0703a; }
.data-picker-selection { display: flex; align-items: center; gap: 6px; min-width: 0; color: var(--text3); font-size: 11px; }
.data-picker-selection strong { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--text2); font: 11px var(--font-mono); }
.data-picker-incompatible { color: #e0703a; white-space: nowrap; }
</style>
