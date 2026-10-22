<template>
  <div class="history-list">
    <div class="toolbar">
      <div class="toolbar-left">
        <h3>{{ $t('history.title') }}</h3>
        <span class="count-badge" v-if="totalCount">{{ totalCount }} {{ $t('history.countSuffix') }}</span>
      </div>
      <div class="toolbar-right">
        <button class="btn" @click="loadHistory" :disabled="loading">{{ $t('common.refresh') }}</button>
        <button class="btn" :class="{ 'btn-active': showCategoryPanel }" @click="showCategoryPanel = !showCategoryPanel">
          {{ $t('history.categoryPanelTitle') }}
        </button>
        <button
          class="btn btn-danger btn-sm"
          @click="clearHistory"
          :disabled="!runs.length || loading || filters.include_deleted"
        >
          {{ $t('history.clearHistory') }}
        </button>
      </div>
    </div>

    <div class="filter-bar">
      <input
        v-model="filters.q"
        class="filter-search"
        :placeholder="$t('history.searchPlaceholder')"
        @input="onSearchInput"
        @keyup.enter="loadHistory"
      />
      <select v-model="filters.status" @change="loadHistory">
        <option value="">{{ $t('history.allStatuses') }}</option>
        <option v-for="s in statusOptions" :key="s" :value="s">{{ getRunStatusLabel(s) }}</option>
      </select>
      <select v-model="filters.category_id" @change="loadHistory">
        <option value="">{{ $t('history.allCategories') }}</option>
        <option v-for="cat in categories" :key="cat.id" :value="cat.id">{{ cat.name }}</option>
      </select>
      <label class="recycle-toggle">
        <input type="checkbox" v-model="filters.include_deleted" @change="loadHistory" />
        {{ $t('history.recycleBin') }}
      </label>
    </div>

    <!-- Lightweight category manager: create / rename / delete -->
    <div v-if="showCategoryPanel" class="card category-panel">
      <div class="card-title">
        {{ $t('history.categoryPanelTitle') }}
        <button class="btn btn-sm" style="margin-left:auto" @click="showCategoryPanel = false">
          {{ $t('common.close') }}
        </button>
      </div>
      <div class="category-create">
        <input
          v-model="newCategoryName"
          :placeholder="$t('history.categoryName')"
          maxlength="60"
          @keydown.enter.prevent="createCategory"
        />
        <button class="btn btn-sm btn-primary" :disabled="!newCategoryName.trim() || creatingCategory" @click="createCategory">
          {{ $t('history.newCategory') }}
        </button>
      </div>
      <div v-if="!categories.length" class="text-muted">{{ $t('history.noCategories') }}</div>
      <div v-else class="category-rows">
        <div v-for="cat in categories" :key="cat.id" class="category-row">
          <template v-if="renamingCategoryId === cat.id">
            <input
              v-model="renameCategoryName"
              maxlength="60"
              @keydown.enter.prevent="saveCategoryRename(cat)"
              @keydown.esc.prevent="renamingCategoryId = null"
            />
            <button class="btn btn-sm" @click="saveCategoryRename(cat)">{{ $t('history.save') }}</button>
            <button class="btn btn-sm" @click="renamingCategoryId = null">{{ $t('common.cancel') }}</button>
          </template>
          <template v-else>
            <span class="category-name">{{ cat.name }}</span>
            <span class="category-count">{{ cat.run_count }}</span>
            <button class="btn btn-sm" @click="startCategoryRename(cat)">{{ $t('history.renameCategory') }}</button>
            <button class="btn btn-sm btn-danger" @click="removeCategory(cat)">{{ $t('history.deleteCategory') }}</button>
          </template>
        </div>
      </div>
    </div>

    <div v-if="loading" class="empty-state">
      <div class="spinner" style="width:24px;height:24px;border-width:2px;"></div>
      <p>{{ $t('history.loadingHistory') }}</p>
    </div>

    <div v-else-if="runs.length === 0" class="empty-state">
      <p>{{ filters.include_deleted ? $t('history.emptyDeleted') : $t('history.empty') }}</p>
    </div>

    <div v-else class="history-table-wrapper">
      <table class="history-table">
        <thead>
          <tr>
            <th>{{ $t('history.colTitle') }}</th>
            <th>{{ $t('history.colCategory') }}</th>
            <th>{{ $t('history.colScene') }}</th>
            <th>{{ $t('history.colData') }}</th>
            <th>{{ $t('history.colQuestion') }}</th>
            <th>{{ $t('history.colStatus') }}</th>
            <th>{{ $t('history.colScore') }}</th>
            <th>{{ $t('history.colVerdict') }}</th>
            <th>{{ $t('history.colCreated') }}</th>
            <th>{{ $t('history.colActions') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="run in runs"
            :key="run.run_id"
            :class="['history-row', `row-${getEffectiveRunStatus(run)}`, { 'row-deleted': run.deleted_at }]"
            @click="toggleDetail(run.run_id)"
          >
            <td class="cell-name" @click.stop @dblclick.stop="startEdit(run)">
              <input
                v-if="editingRunId === run.run_id"
                :ref="setEditInput"
                v-model="editTitle"
                class="inline-title-input"
                maxlength="200"
                @keydown.enter.prevent="saveTitle(run, true)"
                @keydown.esc.prevent="cancelEdit"
                @blur="saveTitle(run)"
                @click.stop
              />
              <span v-else class="title-view" :title="run.deleted_at ? runTitle(run) : $t('history.renameHint')">
                <span v-if="run.deleted_at" class="deleted-badge">{{ $t('history.recycleBin') }}</span>
                <span class="title-text">{{ runTitle(run) }}</span>
              </span>
            </td>
            <td class="cell-category" @click.stop>
              <select
                class="row-category"
                :value="run.category_id || ''"
                @change="changeCategory(run, $event)"
              >
                <option value="">{{ $t('history.uncategorized') }}</option>
                <option v-for="cat in categories" :key="cat.id" :value="cat.id">{{ cat.name }}</option>
              </select>
            </td>
            <td>{{ run.scene_name }}</td>
            <td class="cell-path">{{ run.data_path }}</td>
            <td class="cell-question">
              <span v-if="run.user_question" :title="run.user_question">
                {{ truncate(run.user_question, 40) }}
              </span>
              <span v-else class="text-muted">--</span>
            </td>
            <td>
              <span :class="['badge', getRunStatusBadgeClass(run)]">{{ getRunStatusLabel(run) }}</span>
            </td>
            <td>
              <span v-if="run.score != null" :class="['score', scoreClass(run.score)]">
                {{ run.score }}
              </span>
              <span v-else class="text-muted">--</span>
            </td>
            <td>
              <span v-if="run.judge_verdict" :class="['badge', verdictBadge(run.judge_verdict)]">
                {{ run.judge_verdict }}
              </span>
              <span v-else class="text-muted">--</span>
            </td>
            <td class="cell-date">{{ formatDate(run.created_at) }}</td>
            <td class="cell-actions" @click.stop>
              <template v-if="filters.include_deleted">
                <button class="btn btn-sm btn-restore" @click="restoreRun(run.run_id)">
                  {{ $t('history.restore') }}
                </button>
                <button class="btn btn-sm btn-danger" @click="purgeRun(run.run_id)">
                  {{ $t('history.purge') }}
                </button>
              </template>
              <template v-else>
                <span v-if="run.harness && run.harness !== 'claude'" class="engine-badge" :title="$t('history.executedByEngine', { engine: run.harness })">{{ run.harness.toUpperCase() }}</span>
                <span v-if="run.ontology_hit === 'reused'" class="engine-badge ont-badge" :title="$t('history.ontologyReusedTitle')">{{ $t('history.ontologyReused') }}</span>
                <span v-else-if="run.ontology_hit === 'extended'" class="engine-badge ont-badge" :title="$t('history.ontologyExtendedTitle')">{{ $t('history.ontologyExtended') }}</span>
                <span v-if="run.enhancement_triggered" class="engine-badge enh-badge" :title="$t('history.enhancedTitle')">E0-E8</span>
                <button
                  v-if="run.session_id"
                  class="btn btn-sm btn-session"
                  @click="viewSession(run)"
                >{{ $t('history.session') }}</button>
                <button
                  v-if="getEffectiveRunStatus(run) === 'completed' && run.report_path"
                  class="btn btn-sm btn-primary"
                  @click="viewReport(run)"
                >{{ $t('history.report') }}</button>
                <button
                  v-if="getEffectiveRunStatus(run) === 'completed' && !run.enhancement_triggered"
                  class="btn btn-sm btn-enhance"
                  @click="enhanceRun(run)"
                  :disabled="enhancingRun === run.run_id"
                >
                  <template v-if="enhancingRun === run.run_id">
                    <span class="spinner-sm"></span> {{ $t('history.enhancing') }}
                  </template>
                  <template v-else>
                    {{ $t('history.enhance') }}
                  </template>
                </button>
                <button
                  v-if="canContinueChat(run)"
                  class="btn btn-sm btn-continue"
                  :title="run.session_id ? $t('history.continueChat') : $t('history.noSessionHint')"
                  @click="openRun(run)"
                >{{ $t('history.continueChat') }}</button>
              </template>
              <button class="btn btn-sm" @click="toggleDetail(run.run_id)">
                {{ expandedRun === run.run_id ? $t('history.collapse') : $t('history.detail') }}
              </button>
              <button
                v-if="!filters.include_deleted"
                class="btn btn-sm btn-danger"
                @click="deleteRun(run.run_id)"
              >{{ $t('history.delete') }}</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Expanded detail panel -->
    <div v-if="expandedRun && detailRun" class="card detail-panel">
      <div class="card-title">
        {{ $t('history.runDetail') }}{{ detailRun.title || detailRun.name }}
        <button class="btn btn-sm" @click="expandedRun = null" style="margin-left:auto">{{ $t('common.close') }}</button>
      </div>
      <div class="detail-grid">
        <div class="detail-item">
          <span class="detail-label">{{ $t('history.runId') }}</span>
          <span class="detail-value">{{ detailRun.run_id }}</span>
        </div>
        <div class="detail-item">
          <span class="detail-label">{{ $t('history.status') }}</span>
          <span :class="['badge', getRunStatusBadgeClass(detailRun)]">{{ getRunStatusLabel(detailRun) }}</span>
        </div>
        <div class="detail-item">
          <span class="detail-label">{{ $t('history.model') }}</span>
          <span class="detail-value">{{ detailRun.model || $t('history.model_default') }}</span>
        </div>
        <div class="detail-item">
          <span class="detail-label">{{ $t('history.maxTurns') }}</span>
          <span class="detail-value">{{ detailRun.max_turns }}</span>
        </div>
        <div class="detail-item">
          <span class="detail-label">{{ $t('history.dataPath') }}</span>
          <span class="detail-value path">{{ detailRun.data_path }}</span>
        </div>
        <div class="detail-item">
          <span class="detail-label">{{ $t('history.workspace') }}</span>
          <span class="detail-value path">{{ detailRun.workspace_path || '--' }}</span>
        </div>
        <div class="detail-item">
          <span class="detail-label">{{ $t('history.colCategory') }}</span>
          <span class="detail-value">{{ categoryName(detailRun.category_id) }}</span>
        </div>
        <div class="detail-item">
          <span class="detail-label">{{ $t('history.createdAt') }}</span>
          <span class="detail-value">{{ formatDate(detailRun.created_at) }}</span>
        </div>
        <div class="detail-item">
          <span class="detail-label">{{ $t('history.completedAt') }}</span>
          <span class="detail-value">{{ detailRun.completed_at ? formatDate(detailRun.completed_at) : '--' }}</span>
        </div>
        <div class="detail-item" v-if="detailRun.deleted_at">
          <span class="detail-label">{{ $t('history.deletedAt') }}</span>
          <span class="detail-value error-text">{{ formatDate(detailRun.deleted_at) }}</span>
        </div>
        <div class="detail-item" v-if="detailRun.user_question">
          <span class="detail-label">{{ $t('history.question') }}</span>
          <span class="detail-value">{{ detailRun.user_question }}</span>
        </div>
        <div class="detail-item" v-if="detailRun.error_message">
          <span class="detail-label">{{ $t('history.error') }}</span>
          <span class="detail-value error-text" :title="detailRun.error_message">{{ formatRunErrorMessage(detailRun.error_message) }}</span>
        </div>
      </div>

      <!-- Logs -->
      <div v-if="logs.length > 0" class="logs-section">
        <div class="card-title" style="margin-top:16px">{{ $t('history.logsTitle') }}（{{ logs.length }} {{ $t('history.logsSuffix') }}）</div>
        <div class="log-stream">
          <div
            v-for="(log, i) in paginatedLogs"
            :key="i"
            :class="['log-line', `log-${log.role}`]"
          >
            <span class="log-time">{{ log.created_at?.slice(11, 19) || '' }}</span>
            <span :class="['log-tag', `tag-${log.message_type}`]">
              {{ log.message_type === 'tool_use' ? 'TOOL' : log.role.toUpperCase() }}
            </span>
            <span class="log-content">{{ truncate(log.content, 300) }}</span>
          </div>
        </div>
        <div v-if="logs.length > 50" class="log-pagination">
          <button class="btn btn-sm" @click="logPage--" :disabled="logPage <= 1">{{ $t('common.prev') }}</button>
          <span class="page-info">{{ logPage }} {{ $t('common.of') }} {{ maxLogPage }}</span>
          <button class="btn btn-sm" @click="logPage++" :disabled="logPage >= maxLogPage">{{ $t('common.next') }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, nextTick, onMounted, onUnmounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { api } from '../../api/index.js';
import {
  getEffectiveRunStatus,
  getRunStatusBadgeClass,
  getRunStatusLabel,
  normalizeRunSummary,
  formatRunErrorMessage,
} from '../../utils/diagnosisRun.js';

const { t } = useI18n();

const emit = defineEmits(['open-report', 'continue-run']);

const statusOptions = ['completed', 'running', 'awaiting_input', 'pending', 'failed', 'stopped', 'expired'];
const chatStatuses = ['completed', 'stopped', 'failed'];

const runs = ref([]);
const totalCount = ref(0);
const loading = ref(false);
const categories = ref([]);
const enhancingRun = ref(null);
const expandedRun = ref(null);
const detailRun = ref(null);
const logs = ref([]);
const logPage = ref(1);
const pageSize = 50;

const filters = reactive({
  q: '',
  status: '',
  category_id: '',
  include_deleted: false,
});

const showCategoryPanel = ref(false);
const newCategoryName = ref('');
const creatingCategory = ref(false);
const renamingCategoryId = ref(null);
const renameCategoryName = ref('');

const editingRunId = ref(null);
const editTitle = ref('');
const editInputEl = ref(null);
const savingTitle = ref(false);

let searchTimer = null;

onMounted(() => {
  loadHistory();
  loadCategories();
});

onUnmounted(() => clearTimeout(searchTimer));

async function loadHistory() {
  loading.value = true;
  try {
    const result = await api.listRuns({
      include_deleted: filters.include_deleted ? 'true' : undefined,
      category_id: filters.category_id || undefined,
      status: filters.status || undefined,
      q: filters.q.trim() || undefined,
    });
    runs.value = result.runs.map(normalizeRunSummary);
    totalCount.value = result.total;
  } catch (err) {
    console.error('Failed to load history:', err);
  } finally {
    loading.value = false;
  }
}

async function loadCategories() {
  try {
    categories.value = await api.listRunCategories();
  } catch (err) {
    console.error('Failed to load categories:', err);
  }
}

function onSearchInput() {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(loadHistory, 300);
}

function runTitle(run) {
  return run.title || run.name || '--';
}

function categoryName(id) {
  if (!id) return t('history.uncategorized');
  return categories.value.find(c => c.id === id)?.name || '--';
}

function startEdit(run) {
  if (filters.include_deleted) return;
  editingRunId.value = run.run_id;
  editTitle.value = run.title || run.name || '';
  nextTick(() => {
    editInputEl.value?.focus();
    editInputEl.value?.select();
  });
}

function setEditInput(el) {
  if (el) editInputEl.value = el;
}

function cancelEdit() {
  editingRunId.value = null;
  editTitle.value = '';
}

async function saveTitle(run, notifyEmpty = false) {
  if (editingRunId.value !== run.run_id || savingTitle.value) return;
  const title = editTitle.value.trim();
  if (!title) {
    if (notifyEmpty) {
      alert(t('history.titleRequired'));
    } else {
      cancelEdit();
    }
    return;
  }
  if (title === (run.title || '')) {
    cancelEdit();
    return;
  }
  savingTitle.value = true;
  try {
    const updated = await api.renameRun(run.run_id, title);
    run.title = updated.title;
    cancelEdit();
  } catch (err) {
    alert(t('history.renameFailed') + err.message);
  } finally {
    savingTitle.value = false;
  }
}

async function changeCategory(run, event) {
  const categoryId = event.target.value || null;
  try {
    const updated = await api.setRunCategory(run.run_id, categoryId);
    run.category_id = updated.category_id;
    loadCategories();
  } catch (err) {
    event.target.value = run.category_id || '';
    alert(t('history.categoryAssignFailed') + err.message);
  }
}

async function createCategory() {
  const name = newCategoryName.value.trim();
  if (!name) return;
  creatingCategory.value = true;
  try {
    await api.createRunCategory(name);
    newCategoryName.value = '';
    await loadCategories();
  } catch (err) {
    alert(err.code === 'CATEGORY_EXISTS' ? t('history.categoryExists') : t('history.categoryCreateFailed') + err.message);
  } finally {
    creatingCategory.value = false;
  }
}

function startCategoryRename(cat) {
  renamingCategoryId.value = cat.id;
  renameCategoryName.value = cat.name;
}

async function saveCategoryRename(cat) {
  const name = renameCategoryName.value.trim();
  if (!name) return;
  if (name === cat.name) {
    renamingCategoryId.value = null;
    return;
  }
  try {
    await api.renameRunCategory(cat.id, name);
    renamingCategoryId.value = null;
    await loadCategories();
  } catch (err) {
    alert(err.code === 'CATEGORY_EXISTS' ? t('history.categoryExists') : t('history.categoryRenameFailed') + err.message);
  }
}

async function removeCategory(cat) {
  if (!confirm(t('history.categoryDeleteConfirm', { name: cat.name }))) return;
  try {
    await api.deleteRunCategory(cat.id);
    if (filters.category_id === cat.id) filters.category_id = '';
    await loadCategories();
    await loadHistory();
  } catch (err) {
    alert(t('history.categoryDeleteFailed') + err.message);
  }
}

function canContinueChat(run) {
  return !filters.include_deleted && chatStatuses.includes(getEffectiveRunStatus(run));
}

// One-click deep enhancement (E0-E8) — deterministic scripts, baseline must be complete
async function enhanceRun(run) {
  enhancingRun.value = run.run_id;
  try {
    await api.enhanceDiagnosis(run.run_id);
    // Poll briefly so the badge reflects the triggered state
    setTimeout(() => loadHistory(), 1200);
  } catch (err) {
    console.error('Enhancement failed:', err);
    alert(err.message || 'Enhancement failed');
  } finally {
    enhancingRun.value = null;
  }
}

async function toggleDetail(runId) {
  if (expandedRun.value === runId) {
    resetDetail();
    return;
  }

  expandedRun.value = runId;
  logPage.value = 1;
  try {
    const data = await api.getRunWithLogs(runId);
    detailRun.value = normalizeRunSummary(data);
    logs.value = data.logs || [];
  } catch {
    detailRun.value = runs.value.find(r => r.run_id === runId);
    logs.value = [];
  }
}

function resetDetail() {
  expandedRun.value = null;
  detailRun.value = null;
  logs.value = [];
}

function viewReport(run) {
  emit('open-report', run.report_path);
}

function viewSession(run) {
  emit('continue-run', run.run_id);
}

// Opening the run view is all a follow-up needs: its bottom input sends the
// next message through the run's locked harness (session rebuilt if absent).
function openRun(run) {
  emit('continue-run', run.run_id);
}

async function deleteRun(runId) {
  if (!confirm(t('history.softDeleteConfirm', { id: runId }))) return;
  try {
    await api.deleteRun(runId);
    if (expandedRun.value === runId) resetDetail();
    await loadHistory();
    loadCategories();
  } catch (err) {
    alert(t('history.deleteFailed') + err.message);
  }
}

async function restoreRun(runId) {
  try {
    await api.restoreRun(runId);
    if (expandedRun.value === runId) resetDetail();
    await loadHistory();
    loadCategories();
  } catch (err) {
    alert(t('history.restoreFailed') + err.message);
  }
}

async function purgeRun(runId) {
  if (!confirm(t('history.purgeConfirm', { id: runId }))) return;
  try {
    await api.deleteRun(runId, { purge: true });
    if (expandedRun.value === runId) resetDetail();
    await loadHistory();
    loadCategories();
  } catch (err) {
    alert(t('history.purgeFailed') + err.message);
  }
}

async function clearHistory() {
  if (!confirm(t('history.clearConfirm'))) return;
  for (const run of runs.value) {
    try { await api.deleteRun(run.run_id); } catch {}
  }
  resetDetail();
  await loadHistory();
  loadCategories();
}

function truncate(text, max) {
  if (!text) return '';
  if (text.length <= max) return text;
  return text.slice(0, max) + '...';
}

function formatDate(dateStr) {
  if (!dateStr) return '--';
  try {
    return new Date(dateStr).toLocaleString();
  } catch {
    return dateStr;
  }
}

function scoreClass(score) {
  if (score >= 90) return 'score-high';
  if (score >= 70) return 'score-mid';
  return 'score-low';
}

function verdictBadge(verdict) {
  if (verdict === 'PASS' || verdict === 'ENDORSED') return 'badge-green';
  if (verdict === 'CONDITIONAL') return 'badge-yellow';
  return 'badge-red';
}

const maxLogPage = computed(() => Math.max(1, Math.ceil(logs.value.length / pageSize)));

const paginatedLogs = computed(() => {
  const start = (logPage.value - 1) * pageSize;
  return logs.value.slice(start, start + pageSize);
});
</script>

<style scoped>
.history-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 100%;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding: 18px 20px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: linear-gradient(180deg, color-mix(in srgb, var(--surface-strong) 82%, transparent), color-mix(in srgb, var(--surface) 90%, transparent));
  box-shadow: var(--shadow-sm);
  backdrop-filter: blur(var(--acrylic-blur)) saturate(var(--acrylic-sat));
  -webkit-backdrop-filter: blur(var(--acrylic-blur)) saturate(var(--acrylic-sat));
}

.toolbar-left { display: flex; align-items: center; gap: 8px; }
.toolbar-left h3 { font-size: 16px; font-weight: 600; }

.count-badge {
  font-size: 12px;
  color: var(--text2);
  background: var(--surface-soft);
  padding: 2px 10px;
  border-radius: 10px;
  border: 1px solid var(--border);
}

.toolbar-right { display: flex; gap: 8px; }

/* ── Server-side filter bar ─────────────────────────────────────────────── */
.filter-bar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: color-mix(in srgb, var(--surface) 90%, transparent);
  box-shadow: var(--shadow-sm);
}

.filter-bar .filter-search {
  width: 240px;
  min-height: 32px;
  padding: 6px 10px;
  font-size: 12.5px;
}

.filter-bar select {
  width: auto;
  min-width: 128px;
  min-height: 32px;
  padding: 6px 28px 6px 10px;
  font-size: 12.5px;
}

.recycle-toggle {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12.5px;
  color: var(--text2);
  cursor: pointer;
  white-space: nowrap;
}

.recycle-toggle input {
  width: auto;
  padding: 0;
  margin: 0;
}

/* ── Category manager ───────────────────────────────────────────────────── */
.category-panel { margin-bottom: 0; }

.category-create {
  display: flex;
  gap: 8px;
  margin-bottom: 10px;
}

.category-create input {
  width: 240px;
  min-height: 32px;
  padding: 6px 10px;
}

.category-rows {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.category-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.category-name { font-size: 13px; font-weight: 600; }
.category-count { font-size: 11px; color: var(--text2); min-width: 18px; }

.category-row input {
  width: 200px;
  min-height: 28px;
  padding: 3px 8px;
  font-size: 12px;
}

.history-table-wrapper {
  overflow-x: auto;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: color-mix(in srgb, var(--surface) 90%, transparent);
  box-shadow: var(--shadow-sm);
  backdrop-filter: blur(var(--acrylic-blur)) saturate(var(--acrylic-sat));
  -webkit-backdrop-filter: blur(var(--acrylic-blur)) saturate(var(--acrylic-sat));
}

.history-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.history-table thead {
  background: var(--surface);
  position: sticky;
  top: 0;
  z-index: 1;
}

.history-table th {
  padding: 8px 10px;
  text-align: left;
  font-weight: 600;
  font-size: 12px;
  color: var(--text2);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-bottom: 2px solid var(--border);
  white-space: nowrap;
}

/* Dense readout: one --row-h-lg (40px) line per run, set by the height of the
   tallest control in the row (a 28px btn-sm), not by stacked dead space. */
.history-table td {
  padding: 0 10px;
  height: var(--row-h-lg);
  border-bottom: 1px solid var(--border);
  vertical-align: middle;
}

.history-row {
  cursor: pointer;
  transition: background 0.1s;
}

/* Hover is interaction feedback, so it rides the accent ramp — the same idiom
   as .log-line:hover below — instead of a foreign blue wash. */
.history-row:hover { background: color-mix(in srgb, var(--accent) 3%, transparent); }

.row-running { background: color-mix(in srgb, var(--accent) 6%, transparent); }
.row-failed { background: color-mix(in srgb, var(--red) 5%, transparent); }
.row-deleted { opacity: 0.68; }

/* Elastic text columns: one line each, ellipsized. Name / scene / path / question
   are identifiers and prose that the detail panel already carries in full, and
   the question cell also holds the whole string in its title, so a one-line cap
   costs no information but buys back a 40px row. */
.cell-name { font-weight: 600; font-size: 12px; overflow: hidden; }
.cell-path { font-family: 'SF Mono', 'Fira Code', monospace; font-size: 11px; color: var(--accent); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cell-question { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cell-date { font-size: 11px; color: var(--text2); white-space: nowrap; }
.cell-actions { display: flex; gap: 4px; }

.title-view {
  display: flex;
  align-items: center;
  gap: 4px;
  min-width: 0;
}

.title-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.deleted-badge {
  flex: none;
  font-size: 9px;
  font-weight: 600;
  color: var(--red);
  border: 1px solid color-mix(in srgb, var(--red) 45%, transparent);
  background: color-mix(in srgb, var(--red) 8%, transparent);
  border-radius: 3px;
  padding: 0 4px;
  line-height: 15px;
}

.inline-title-input {
  width: 100%;
  min-height: 26px;
  padding: 2px 6px;
  font-size: 12px;
  font-weight: 600;
}

.cell-category { overflow: hidden; }

.row-category {
  width: 100%;
  min-height: 26px;
  padding: 2px 22px 2px 6px;
  font-size: 11.5px;
  background-position: right 6px center;
}

/* Scene has no class of its own — it is the third column. Same treatment. */
.history-table td:nth-child(3) { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* ── Column template ──────────────────────────────────────────────────────
   Ten columns, so the geometry is declared once here instead of being
   renegotiated for every row by the auto table algorithm. Fixed layout makes
   those declarations exact: no lane can be crushed by a long value, and every
   elastic cell ellipsizes instead of wrapping.

   The control rail is sized from measured content; the title and category
   lanes carry the editable controls. Everything is one line, so each row is
   exactly --row-h-lg (40px). Narrower windows keep the declared lanes and the
   wrapper scrolls instead of stacking controls into columns. */
.history-table {
  table-layout: fixed;
  min-width: 1336px;
}

.history-table th:nth-child(1) { width: 150px; }  /* 标题 */
.history-table th:nth-child(2) { width: 118px; }  /* 分类 */
.history-table th:nth-child(3) { width: 84px; }   /* 场景 */
.history-table th:nth-child(4) { width: 72px; }   /* 数据文件 */
.history-table th:nth-child(5) { width: 96px; }   /* 问题 */
.history-table th:nth-child(6) { width: 76px; }   /* 状态 */
.history-table th:nth-child(7) { width: 46px; }   /* 评分 */
.history-table th:nth-child(8) { width: 102px; }  /* 结论 */
.history-table th:nth-child(9) { width: 112px; }  /* 创建时间 */
.history-table th:nth-child(10) { width: 480px; } /* 操作 */

.history-list .badge {
  white-space: nowrap;
  word-break: keep-all;
}

/* The rail is one instrument line. The global .cell-actions rule wraps and caps
   at 340px for narrow non-table windows; inside the ledger the rail instead
   keeps its chips + buttons on a single row and lets .history-table-wrapper
   scroll, so controls are never stacked into a column. */
.history-table .cell-actions {
  flex-wrap: nowrap;
  justify-content: flex-end;
  max-width: none;
}

.history-table .cell-actions > * { flex: none; }

.text-muted { color: var(--text2); font-size: 12px; }

.score { font-weight: 700; font-size: 13px; }
.score-high { color: var(--green); }
.score-mid { color: var(--yellow); }
.score-low { color: var(--red); }

.detail-panel { margin-top: 16px; }

.detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 8px;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.detail-label {
  font-size: 11px;
  color: var(--text2);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.detail-value {
  font-size: 13px;
}

.detail-value.path {
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: 11px;
  color: var(--accent);
  word-break: break-all;
}

.error-text { color: var(--red); }

.logs-section { margin-top: 8px; }

.log-stream {
  background: var(--surface-soft);
  border-radius: var(--radius);
  padding: 8px;
  max-height: 400px;
  overflow-y: auto;
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: 11px;
  line-height: 1.6;
}

.log-line {
  display: flex;
  gap: 8px;
  padding: 3px 4px;
  align-items: flex-start;
}

.log-line:hover { background: color-mix(in srgb, var(--accent) 8%, transparent); border-radius: 6px; }

.log-time {
  color: var(--text2);
  flex-shrink: 0;
  font-size: 10px;
}

.log-tag {
  display: inline-block;
  padding: 0 4px;
  border-radius: 3px;
  font-size: 9px;
  font-weight: 700;
  flex-shrink: 0;
  line-height: 16px;
}

.tag-text { background: color-mix(in srgb, var(--purple) 14%, transparent); color: var(--purple); }
.tag-tool_use { background: color-mix(in srgb, var(--accent) 14%, transparent); color: var(--accent); }

.log-content {
  color: var(--text);
  white-space: pre-wrap;
  word-break: break-all;
}

.btn-continue {
  background: color-mix(in srgb, var(--accent) 10%, transparent);
  border-color: var(--accent);
  color: var(--accent);
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.btn-continue:hover {
  background: color-mix(in srgb, var(--accent) 18%, transparent);
}

.btn-restore {
  background: color-mix(in srgb, var(--green) 10%, transparent);
  border-color: var(--green);
  color: var(--green);
}
.btn-restore:hover {
  background: color-mix(in srgb, var(--green) 18%, transparent);
}

.btn-session {
  background: color-mix(in srgb, var(--purple) 10%, transparent);
  border-color: var(--purple);
  color: var(--purple);
}
.btn-session:hover {
  background: color-mix(in srgb, var(--purple) 18%, transparent);
}

.spinner-sm {
  display: inline-block;
  width: 12px;
  height: 12px;
  border: 2px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.log-pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-top: 8px;
  padding: 8px;
}

.page-info {
  font-size: 12px;
  color: var(--text2);
}
</style>
