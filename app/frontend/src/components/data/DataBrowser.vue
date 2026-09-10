<template>
  <div class="data-browser">
    <div class="toolbar">
      <div class="toolbar-left">
        <a class="breadcrumb-root" @click="goHome">{{ $t('data.title') }}</a>
        <template v-if="currentFolder">
          <span class="breadcrumb-sep">/</span>
          <a class="breadcrumb-path" @click="goHome">{{ currentFolder }}</a>
        </template>
      </div>
      <div class="toolbar-right">
        <button class="btn" @click="showNewFolder = true">{{ $t('data.newFolder') }}</button>
        <button class="btn btn-primary" @click="triggerUpload">{{ $t('data.uploadFile') }}</button>
        <input ref="fileInput" type="file" multiple @change="onUpload" style="display:none" />
        <button class="btn" v-if="currentFolder" @click="navigateUp">{{ $t('data.back') }}</button>
      </div>
    </div>

    <!-- New folder dialog -->
    <div v-if="showNewFolder" class="card new-folder-form">
      <div class="form-row">
        <input v-model="newFolderName" :placeholder="$t('data.folderNamePlaceholder')" @keyup.enter="createFolder" />
        <input v-model="newFolderDesc" :placeholder="$t('data.folderDescPlaceholder')" />
        <button class="btn btn-primary btn-sm" @click="createFolder" :disabled="!newFolderName">{{ $t('common.create') }}</button>
        <button class="btn btn-sm" @click="showNewFolder = false">{{ $t('common.cancel') }}</button>
      </div>
    </div>

    <!-- Upload progress -->
    <div v-if="uploading" class="card">
      <div class="upload-progress">
        <div class="spinner"></div>
        <span>{{ $t('data.uploading', { count: uploadCount }) }}</span>
      </div>
    </div>

    <!-- File list -->
    <div v-if="loading" class="empty-state">
      <div class="spinner" style="width:32px;height:32px;border-width:3px;"></div>
      <p>{{ $t('common.loading') }}</p>
    </div>

    <div v-else-if="items.length === 0" class="empty-state">
      <p>{{ $t('data.noFiles') }}</p>
    </div>

    <div v-else>
      <!-- Readout strip — counts and total weight, so the page states its own
           contents before you scroll. An instrument tells you its range. -->
      <div class="ip-stats data-stats">
        <div class="ip-stat">
          <span class="ip-stat-value">{{ folderCount }}</span>
          <span class="ip-stat-label">{{ $t('data.statFolders') }}</span>
        </div>
        <div class="ip-stat">
          <span class="ip-stat-value">{{ dataFileCount }}</span>
          <span class="ip-stat-label">{{ $t('data.statDataFiles') }}</span>
        </div>
        <div class="ip-stat">
          <span class="ip-stat-value">{{ formatSize(totalBytes) }}</span>
          <span class="ip-stat-label">{{ $t('data.statTotalSize') }}</span>
        </div>
        <div class="ip-stat">
          <span class="ip-stat-value" :class="selectedFiles.size ? 'accent' : ''">{{ selectedFiles.size }}</span>
          <span class="ip-stat-label">{{ $t('data.statSelected') }}</span>
        </div>
      </div>

      <div class="selection-toolbar" v-if="selectedFiles.size > 0">
        <button class="btn btn-primary btn-sm" @click="analyzeSelected">
          {{ $t('data.analyzeSelected', { count: selectedFiles.size }) }}
        </button>
        <button class="btn btn-sm" @click="clearSelection">{{ $t('common.clear') }}</button>
      </div>
      <div class="folder-toolbar" v-if="currentFolder">
        <button class="btn btn-primary btn-sm" @click="analyzeFolder">
          {{ $t('data.analyzeFolder') }}
        </button>
      </div>

      <!-- Manifest — a dense readout instead of a sparse card grid. Names sit
           in a fixed column so 40 rows can be scanned vertically; size is
           right-aligned and tabular so magnitudes compare at a glance. -->
      <div class="ip-table ip-panel data-manifest">
        <div class="ip-thead manifest-cols">
          <span class="col-check"></span>
          <span>{{ $t('data.colName') }}</span>
          <span>{{ $t('data.colType') }}</span>
          <span class="ta-r">{{ $t('data.colSize') }}</span>
          <span class="ta-r">{{ $t('data.colActions') }}</span>
        </div>
        <div class="manifest-body ip-scroll">
          <div
            v-for="item in items"
            :key="item.name"
            class="ip-row manifest-cols"
            :class="{ 'is-active': isSelected(item) }"
            @click="onItemClick(item)"
            @dblclick="onItemDblClick(item)"
          >
            <span class="col-check">
              <input
                v-if="item.type === 'file' && isDataFile(item.ext)"
                type="checkbox"
                :checked="selectedFiles.has(currentFolder ? `data/${currentFolder}/${item.name}` : `data/${item.name}`)"
                @change.stop="toggleFileSelect(currentFolder ? `data/${currentFolder}/${item.name}` : `data/${item.name}`)"
                class="file-checkbox"
              />
            </span>

            <span class="cell-name ip-primary" :title="item.name">
              <svg v-if="item.type === 'folder'" class="ip-glyph ip-glyph-dir" viewBox="0 0 16 16">
                <path d="M1.5 3.5h4l1.2 1.6h7.8v7.4h-13z" />
                <path d="M1.5 5.1h13" />
              </svg>
              <svg v-else-if="isDataFile(item.ext)" class="ip-glyph ip-glyph-data" viewBox="0 0 16 16">
                <path d="M2.5 13.5v-11h11v11z" />
                <path d="M5 10.5v-2M8 10.5v-5M11 10.5v-3" />
              </svg>
              <svg v-else class="ip-glyph ip-glyph-file" viewBox="0 0 16 16">
                <path d="M3.5 1.5h5.5l3.5 3.5v9.5h-9z" />
                <path d="M9 1.5v3.5h3.5" />
              </svg>
              <span class="name-text">{{ item.name }}</span>
            </span>

            <span class="ip-sub">{{ item.type === 'folder' ? $t('data.folder') : (item.ext || '—') }}</span>
            <span class="ta-r ip-sub">{{ item.type === 'file' ? formatSize(item.size) : '—' }}</span>

            <span class="ta-r cell-actions">
              <button
                v-if="item.type === 'file' && isDataFile(item.ext)"
                class="btn btn-primary btn-sm"
                @click.stop="selectForDiagnosis(item)"
              >{{ $t('data.analyze') }}</button>
              <button
                v-if="item.type === 'file' && ['.csv', '.json', '.md', '.txt', '.tsv'].includes(item.ext)"
                class="btn btn-sm"
                @click.stop="preview(item)"
              >{{ $t('data.preview') }}</button>
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- File preview -->
    <div v-if="previewFile" class="card preview-card">
      <div class="card-title">
        <span>{{ $t('data.previewColon') }}{{ previewFile.name }}</span>
        <button class="btn btn-sm" @click="previewFile = null">{{ $t('common.close') }}</button>
      </div>
      <pre class="preview-content">{{ previewContent }}</pre>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { api } from '../../api/index.js';

const { t } = useI18n();

const emit = defineEmits(['select-file', 'select-folder', 'select-files']);

const items = ref([]);

// Readout strip derives from the loaded folder — no extra request.
const folderCount = computed(() => items.value.filter((i) => i.type === 'folder').length);
const dataFileCount = computed(() =>
  items.value.filter((i) => i.type === 'file' && isDataFile(i.ext)).length);
const totalBytes = computed(() =>
  items.value.reduce((sum, i) => sum + (i.type === 'file' ? (i.size || 0) : 0), 0));
const loading = ref(false);
const currentFolder = ref('');
const showNewFolder = ref(false);
const newFolderName = ref('');
const newFolderDesc = ref('');
const uploading = ref(false);
const uploadCount = ref(0);
const selectedFile = ref(null);
const selectedFiles = ref(new Set());
const previewFile = ref(null);
const previewContent = ref('');
const fileInput = ref(null);

onMounted(() => loadData());

async function loadData(folder) {
  loading.value = true;
  try {
    items.value = await api.listData(folder || '');
    currentFolder.value = folder || '';
  } catch (err) {
    console.error('Failed to load data:', err);
  } finally {
    loading.value = false;
  }
}

function triggerUpload() {
  fileInput.value.click();
}

async function onUpload(e) {
  const files = Array.from(e.target.files || []);
  if (!files.length) return;
  uploading.value = true;
  uploadCount.value = files.length;
  try {
    await api.uploadFiles(currentFolder.value, files);
    await loadData(currentFolder.value || undefined);
  } catch (err) {
    alert(t('data.uploadFailed') + err.message);
  } finally {
    uploading.value = false;
    e.target.value = '';
  }
}

async function createFolder() {
  if (!newFolderName.value) return;
  try {
    await api.createFolder(newFolderName.value, newFolderDesc.value);
    showNewFolder.value = false;
    newFolderName.value = '';
    newFolderDesc.value = '';
    await loadData();
  } catch (err) {
    alert(t('data.createFolderFailed') + err.message);
  }
}

function onItemClick(item) {
  if (item.type === 'file') {
    selectedFile.value = item;
  }
}

function onItemDblClick(item) {
  if (item.type === 'folder') {
    clearSelection();
    loadData(item.name);
  } else if (isDataFile(item.ext)) {
    selectForDiagnosis(item);
  }
}

function goHome() {
  clearSelection();
  loadData();
}

function navigateUp() {
  clearSelection();
  loadData();
}

function toggleFileSelect(filePath) {
  const next = new Set(selectedFiles.value);
  if (next.has(filePath)) {
    next.delete(filePath);
  } else {
    next.add(filePath);
  }
  selectedFiles.value = next;
}

function clearSelection() {
  selectedFiles.value = new Set();
  selectedFile.value = null;
}

function analyzeSelected() {
  const files = Array.from(selectedFiles.value);
  emit('select-files', files);
}

function analyzeFolder() {
  const csvFiles = items.value.filter(f => f.type === 'file' && isDataFile(f.ext));
  emit('select-folder', {
    path: `data/${currentFolder.value}`,
    name: currentFolder.value,
    csvFiles: csvFiles.map(f => `data/${currentFolder.value}/${f.name}`),
    csvCount: csvFiles.length,
  });
}

function selectForDiagnosis(item) {
  const path = currentFolder.value
    ? `data/${currentFolder.value}/${item.name}`
    : `data/${item.name}`;
  emit('select-file', { ...item, path, folder: currentFolder.value });
}

function isSelected(item) {
  return selectedFile.value?.name === item.name;
}

function isDataFile(ext) {
  return ['.csv', '.xlsx', '.xls', '.parquet', '.json', '.tsv'].includes(ext);
}

async function preview(item) {
  const path = currentFolder.value
    ? `data/${currentFolder.value}/${item.name}`
    : `data/${item.name}`;
  try {
    const data = await api.readFile(path);
    previewFile.value = item;
    previewContent.value = data.content;
  } catch (err) {
    alert(t('data.readFailed') + err.message);
  }
}


function formatSize(bytes) {
  if (bytes === null || bytes === undefined) return '—';
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}
</script>

<style scoped>
.data-browser {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 100%;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  padding: 8px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface);
}

.toolbar-left { display: flex; align-items: center; gap: 6px; min-width: 0; }

.breadcrumb-root {
  font-family: var(--font-mono);
  font-size: var(--fs-lg);
  font-weight: 500;
  letter-spacing: -0.01em;
  color: var(--text);
  cursor: pointer;
  text-decoration: none;
}
.breadcrumb-root:hover { color: var(--accent); }

.breadcrumb-sep {
  color: var(--text-dim);
  font-size: var(--fs-body);
}

.breadcrumb-path {
  font-family: var(--font-mono);
  font-size: var(--fs-body);
  color: var(--accent);
  cursor: pointer;
  text-decoration: none;
}
.breadcrumb-path:hover { color: var(--accent-bright); }

.toolbar-right { display: flex; gap: 6px; }

.new-folder-form .form-row {
  display: flex; gap: 8px; align-items: center;
  flex-wrap: wrap;
}
.new-folder-form input { max-width: 240px; }

.upload-progress {
  display: flex; align-items: center; gap: 12px;
  color: var(--accent);
}

.data-stats { margin-bottom: 12px; }
.data-manifest { min-height: 0; }
.manifest-cols {
  grid-template-columns: 26px minmax(0, 2.4fr) 96px 92px minmax(120px, auto);
}
.manifest-body { overflow-y: auto; min-height: 0; }
.manifest-body .ip-row { cursor: pointer; }
.col-check { display: flex; align-items: center; }
.cell-name { display: flex; align-items: center; gap: 8px; min-width: 0; }
.cell-name .name-text { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cell-actions { display: flex; gap: 5px; justify-content: flex-end; }
.cell-actions .btn { padding: 2px 8px; font-size: var(--fs-micro); }
.file-checkbox { accent-color: var(--accent); width: 13px; height: 13px; cursor: pointer; }

.file-checkbox {
  width: 16px;
  height: 16px;
  cursor: pointer;
  accent-color: var(--accent2);
}

.selection-toolbar, .folder-toolbar {
  display: flex;
  gap: 8px;
  padding: 8px 12px;
  background: var(--surface-soft);
  border-radius: var(--radius);
  margin-bottom: 12px;
  align-items: center;
  border: 1px solid var(--border);
}
</style>
