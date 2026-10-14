<template>
  <div class="atl">
    <!-- Folder browser: breadcrumb + entries (folders selectable, data folders only) -->
    <div class="atl-browser">
      <div class="atl-crumb">
        <button type="button" class="atl-crumb-btn" @click="browse('')">
          data:
        </button>
        <template v-for="(seg, i) in crumbs" :key="i">
          <span class="atl-crumb-sep">/</span>
          <button type="button" class="atl-crumb-btn" @click="browse(seg.path)">{{ seg.name }}</button>
        </template>
        <button type="button" class="atl-crumb-up" :disabled="!crumbs.length" :title="$t('closedloop.launcher.up')" @click="browseUp">↑</button>
      </div>

      <div class="atl-entries ip-scroll">
        <div v-if="loading" class="atl-state">{{ $t('closedloop.launcher.loading') }}</div>
        <div v-else-if="!entries.length" class="atl-state">{{ $t('closedloop.launcher.empty') }}</div>
        <template v-else>
          <button
            v-for="e in entries" :key="e.name"
            type="button" class="atl-entry"
            :class="{ selected: selectedPath === joinPath(e.name), dim: e.type !== 'folder' }"
            :disabled="e.type !== 'folder'"
            @click="e.type === 'folder' ? (selectedPath === joinPath(e.name) ? openFolder(e.name) : pick(e.name)) : null"
            @dblclick="e.type === 'folder' && openFolder(e.name)"
          >
            <span class="atl-entry-icon">{{ e.type === 'folder' ? (selectedPath === joinPath(e.name) ? '☑' : '▤') : '·' }}</span>
            <span class="atl-entry-name">{{ e.name }}</span>
            <span class="atl-entry-meta">{{ e.type === 'folder' ? $t('closedloop.launcher.folder') : formatSize(e.size) }}</span>
          </button>
        </template>
      </div>

      <div class="atl-selection">
        <template v-if="selectedPath">
          <span class="atl-selection-label">{{ $t('closedloop.launcher.selected') }}</span>
          <code class="atl-selection-path">data/{{ selectedPath }}</code>
        </template>
        <template v-else>
          <span class="atl-selection-label dim">{{ $t('closedloop.launcher.none') }}</span>
        </template>
      </div>
    </div>

    <textarea
      v-model="question"
      class="atl-question"
      rows="2"
      :placeholder="questionPlaceholder || $t('closedloop.launcher.questionPlaceholder')"
    ></textarea>

    <div class="atl-actions">
      <span class="atl-note">{{ $t('closedloop.launcher.note', { skill }) }}</span>
      <button type="button" class="atl-launch" :disabled="!selectedPath || launching" @click="launch">
        {{ launching ? $t('closedloop.launcher.starting') : $t('closedloop.launcher.launch') }}
      </button>
    </div>
    <p v-if="error" class="atl-error">{{ error }}</p>
  </div>
</template>

<script setup>
// Shared launcher for the specialized-analysis panels: pick a data folder,
// then dispatch a REAL harness run with the panel's analysisIntent. The agent
// (not a script wrapper) executes the matching skill protocol; the live
// process is shown by the run view the parent navigates to.
import { ref, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { api } from '../../api/index.js';

const props = defineProps({
  intent: { type: String, required: true },
  skill: { type: String, required: true },
  harness: { type: String, default: 'claude' },
  questionPlaceholder: { type: String, default: '' },
});
const emit = defineEmits(['launched']);

const { t } = useI18n();

const entries = ref([]);
const loading = ref(false);
const cwd = ref('');           // relative dir currently listed
const selectedPath = ref('');  // relative folder chosen for analysis
const question = ref('');
const launching = ref(false);
const error = ref('');

const crumbs = computed(() => {
  if (!cwd.value) return [];
  const parts = cwd.value.split('/');
  return parts.map((name, i) => ({ name, path: parts.slice(0, i + 1).join('/') }));
});

function joinPath(name) {
  return cwd.value ? `${cwd.value}/${name}` : name;
}

async function browse(path) {
  loading.value = true;
  error.value = '';
  try {
    const res = await api.browseData(path);
    // request() unwraps the envelope: res is already the entries array.
    const list = Array.isArray(res) ? res : (res?.data || []);
    entries.value = list.filter((e) => e.type === 'folder' || /\.(csv|tsv|xlsx|xls|json|parquet)$/i.test(e.ext || e.name || ''));
    cwd.value = path || '';
    // Selection outside the newly listed dir no longer exists — drop it.
    if (selectedPath.value && !selectedPath.value.startsWith(cwd.value)) selectedPath.value = '';
  } catch (err) {
    error.value = err?.message || String(err);
    entries.value = [];
  } finally {
    loading.value = false;
  }
}

function browseUp() {
  const parts = cwd.value.split('/');
  parts.pop();
  browse(parts.join('/'));
}

function openFolder(name) {
  browse(joinPath(name));
}

function pick(name) {
  selectedPath.value = joinPath(name);
}

function formatSize(bytes) {
  if (!bytes) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

async function launch() {
  if (!selectedPath.value || launching.value) return;
  launching.value = true;
  error.value = '';
  try {
    const folderPath = selectedPath.value;
    const folderName = folderPath.split('/').pop();
    const payload = {
      folderPath,
      analysisIntent: props.intent,
      harness: props.harness,
      sceneName: folderName,
      reportLanguage: 'zh',
    };
    if (question.value.trim()) payload.userQuestion = question.value.trim();
    const data = await api.startDiagnosis(payload);
    await api.executeDiagnosis(data.runId);
    emit('launched', data.runId);
  } catch (err) {
    error.value = err?.message || String(err);
  } finally {
    launching.value = false;
  }
}

onMounted(() => browse(''));
</script>

<style scoped>
.atl { display: flex; flex-direction: column; gap: 10px; }
.atl-browser {
  background: var(--surface-soft);
  border: 1px solid var(--border);
  border-radius: 10px;
  overflow: hidden;
}
.atl-crumb {
  display: flex; align-items: center; gap: 4px; flex-wrap: wrap;
  padding: 8px 12px;
  border-bottom: 1px solid var(--border);
  font-family: var(--font-mono, monospace);
  font-size: 12px;
}
.atl-crumb-btn { appearance: none; background: none; border: none; padding: 2px 4px; color: var(--accent); cursor: pointer; font: inherit; border-radius: 4px; }
.atl-crumb-btn:hover { background: color-mix(in srgb, var(--accent) 10%, transparent); }
.atl-crumb-sep { color: var(--text3); }
.atl-crumb-up { margin-left: auto; appearance: none; background: none; border: 1px solid var(--border); border-radius: 6px; color: var(--text2); cursor: pointer; padding: 2px 8px; font-size: 12px; }
.atl-crumb-up:disabled { opacity: .4; cursor: not-allowed; }
.atl-entries { max-height: 220px; overflow-y: auto; }
.atl-state { padding: 16px 12px; text-align: center; color: var(--text2); font-size: 12px; }
.atl-entry {
  display: flex; align-items: center; gap: 8px; width: 100%;
  appearance: none; background: none; border: none;
  padding: 7px 12px; cursor: pointer; text-align: left;
  color: var(--text); font-size: 12.5px; font-family: inherit;
  border-bottom: 1px solid color-mix(in srgb, var(--border) 50%, transparent);
}
.atl-entry:hover:not(:disabled) { background: color-mix(in srgb, var(--accent) 7%, transparent); }
.atl-entry:disabled { cursor: default; color: var(--text3); }
.atl-entry.selected { background: color-mix(in srgb, var(--accent) 12%, transparent); }
.atl-entry.dim { opacity: .55; }
.atl-entry-icon { color: var(--accent); flex-shrink: 0; }
.atl-entry-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-family: var(--font-mono, monospace); }
.atl-entry-meta { font-size: 11px; color: var(--text2); flex-shrink: 0; }
.atl-selection { display: flex; align-items: center; gap: 8px; padding: 8px 12px; border-top: 1px solid var(--border); font-size: 12px; }
.atl-selection-label { color: var(--text2); flex-shrink: 0; }
.atl-selection-label.dim { color: var(--text3); }
.atl-selection-path { color: var(--accent); font-family: var(--font-mono, monospace); overflow: hidden; text-overflow: ellipsis; }
.atl-question {
  background: var(--surface-soft); border: 1px solid var(--border);
  border-radius: 10px; padding: 9px 12px; color: var(--text);
  font-size: 12.5px; font-family: inherit; resize: vertical; min-height: 44px;
}
.atl-question:focus { outline: none; border-color: var(--accent); }
.atl-actions { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.atl-note { font-size: 11px; color: var(--text2); line-height: 1.5; }
.atl-launch {
  appearance: none; border: none; border-radius: 10px; cursor: pointer;
  padding: 9px 20px; font-size: 13px; font-weight: 600; font-family: inherit;
  background: linear-gradient(135deg, var(--accent2), var(--accent)); color: #fff;
  transition: opacity .15s, transform .15s;
  flex-shrink: 0;
}
.atl-launch:hover:not(:disabled) { opacity: .9; transform: translateY(-1px); }
.atl-launch:disabled { opacity: .4; cursor: not-allowed; }
.atl-error { margin: 0; font-size: 12px; color: var(--red); word-break: break-all; }
</style>
