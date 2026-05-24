<template>
  <div class="data-browser">
    <div class="toolbar">
      <div class="toolbar-left">
        <a class="breadcrumb-root" @click="goHome">Data Files</a>
        <template v-if="currentFolder">
          <span class="breadcrumb-sep">/</span>
          <a class="breadcrumb-path" @click="goHome">{{ currentFolder }}</a>
        </template>
      </div>
      <div class="toolbar-right">
        <button class="btn" @click="showNewFolder = true">+ New Folder</button>
        <button class="btn btn-primary" @click="triggerUpload">Upload File</button>
        <input ref="fileInput" type="file" multiple @change="onUpload" style="display:none" />
        <button class="btn" v-if="currentFolder" @click="navigateUp">.. Back</button>
      </div>
    </div>

    <!-- New folder dialog -->
    <div v-if="showNewFolder" class="card new-folder-form">
      <div class="form-row">
        <input v-model="newFolderName" placeholder="Folder name (letters, numbers, _ -)" @keyup.enter="createFolder" />
        <input v-model="newFolderDesc" placeholder="Description (optional)" />
        <button class="btn btn-primary btn-sm" @click="createFolder" :disabled="!newFolderName">Create</button>
        <button class="btn btn-sm" @click="showNewFolder = false">Cancel</button>
      </div>
    </div>

    <!-- Upload progress -->
    <div v-if="uploading" class="card">
      <div class="upload-progress">
        <div class="spinner"></div>
        <span>Uploading {{ uploadCount }} file(s)...</span>
      </div>
    </div>

    <!-- File list -->
    <div v-if="loading" class="empty-state">
      <div class="spinner" style="width:32px;height:32px;border-width:3px;"></div>
      <p>Loading...</p>
    </div>

    <div v-else-if="items.length === 0" class="empty-state">
      <p>No files found. Upload data files or create a folder to get started.</p>
    </div>

    <div v-else>
      <div class="selection-toolbar" v-if="selectedFiles.size > 0">
        <button class="btn btn-primary btn-sm" @click="analyzeSelected">
          Analyze Selected ({{ selectedFiles.size }})
        </button>
        <button class="btn btn-sm" @click="clearSelection">Clear</button>
      </div>
      <div class="folder-toolbar" v-if="currentFolder">
        <button class="btn btn-primary btn-sm" @click="analyzeFolder">
          Analyze Entire Folder
        </button>
      </div>
      <div class="file-grid">
        <div
          v-for="item in items"
          :key="item.name"
          :class="['file-card', { selected: isSelected(item) }]"
          @click="onItemClick(item)"
          @dblclick="onItemDblClick(item)"
        >
          <div class="file-check-col" v-if="item.type === 'file' && isDataFile(item.ext)">
            <input
              type="checkbox"
              :checked="selectedFiles.has(currentFolder ? `data/${currentFolder}/${item.name}` : `data/${item.name}`)"
              @change.stop="toggleFileSelect(currentFolder ? `data/${currentFolder}/${item.name}` : `data/${item.name}`)"
              class="file-checkbox"
            />
          </div>
          <div class="file-icon">
            <span v-if="item.type === 'folder'">📁</span>
            <span v-else>{{ fileIcon(item.ext) }}</span>
          </div>
          <div class="file-info">
            <div class="file-name">{{ item.name }}</div>
            <div class="file-meta">
              <span v-if="item.type === 'file'">{{ formatSize(item.size) }}</span>
              <span v-if="item.type === 'folder'">Folder</span>
              <span class="file-ext" v-if="item.ext">{{ item.ext }}</span>
            </div>
          </div>
          <div class="file-actions">
            <button
              v-if="item.type === 'file' && isDataFile(item.ext)"
              class="btn btn-primary btn-sm"
              @click.stop="selectForDiagnosis(item)"
            >Analyze</button>
            <button
              v-if="item.type === 'file' && ['.csv', '.json', '.md', '.txt', '.tsv'].includes(item.ext)"
              class="btn btn-sm"
              @click.stop="preview(item)"
            >Preview</button>
          </div>
        </div>
      </div>
    </div>

    <!-- File preview -->
    <div v-if="previewFile" class="card preview-card">
      <div class="card-title">
        <span>Preview: {{ previewFile.name }}</span>
        <button class="btn btn-sm" @click="previewFile = null">Close</button>
      </div>
      <pre class="preview-content">{{ previewContent }}</pre>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { api } from '../api.js';

const emit = defineEmits(['select-file', 'select-folder', 'select-files']);

const items = ref([]);
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
    alert('Upload failed: ' + err.message);
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
    alert('Failed to create folder: ' + err.message);
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
    ? `${currentFolder.value}/${item.name}`
    : item.name;
  try {
    const data = await api.readFile(path);
    previewFile.value = item;
    previewContent.value = data.content;
  } catch (err) {
    alert('Failed to read file: ' + err.message);
  }
}

function fileIcon(ext) {
  const icons = {
    '.csv': '📊', '.xlsx': '📊', '.xls': '📊', '.json': '📋',
    '.tsv': '📊', '.parquet': '📦', '.py': '🐍', '.md': '📝',
  };
  return icons[ext] || '📄';
}

function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}
</script>

<style scoped>
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.toolbar-left { display: flex; align-items: center; gap: 6px; }

.breadcrumb-root {
  font-size: 16px;
  font-weight: 600;
  color: var(--text);
  cursor: pointer;
  text-decoration: none;
}
.breadcrumb-root:hover { color: var(--accent); }

.breadcrumb-sep {
  color: var(--text2);
  font-size: 13px;
}

.breadcrumb-path {
  font-size: 13px;
  color: var(--text2);
  cursor: pointer;
  text-decoration: none;
}
.breadcrumb-path:hover { color: var(--accent); }

.toolbar-right { display: flex; gap: 8px; }

.new-folder-form .form-row {
  display: flex; gap: 8px; align-items: center;
}
.new-folder-form input { max-width: 240px; }

.upload-progress {
  display: flex; align-items: center; gap: 12px;
  color: var(--accent);
}

.file-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
}

.file-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 14px;
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  transition: all 0.15s;
}

.file-card:hover { border-color: var(--accent); }

.file-card.selected {
  border-color: var(--accent2);
  background: rgba(31, 111, 235, 0.05);
}

.file-icon { font-size: 24px; flex-shrink: 0; }

.file-info { flex: 1; min-width: 0; }

.file-name {
  font-size: 13px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.file-meta {
  font-size: 11px;
  color: var(--text2);
  display: flex;
  gap: 8px;
  margin-top: 2px;
}

.file-ext { color: var(--purple); text-transform: uppercase; font-size: 10px; }

.file-actions { flex-shrink: 0; }

.preview-card { margin-top: 16px; }

.preview-content {
  background: var(--surface2);
  padding: 16px;
  border-radius: var(--radius);
  font-size: 12px;
  font-family: 'SF Mono', 'Fira Code', monospace;
  max-height: 400px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
}

.file-check-col {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

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
  background: var(--surface2);
  border-radius: var(--radius);
  margin-bottom: 12px;
  align-items: center;
}
</style>
