<template>
  <div class="results-library" data-testid="results-library">
    <!-- Filter bar -->
    <div class="card results-filter-bar">
      <div class="results-filter-row">
        <input
          v-model="filters.q"
          class="results-search"
          type="text"
          data-testid="results-search"
          :placeholder="$t('results.searchPlaceholder')"
          @input="onSearchInput"
        />
        <select v-model="filters.intent" data-testid="results-intent-filter" @change="reload">
          <option value="">{{ $t('results.allIntents') }}</option>
          <option v-for="opt in intentOptions" :key="opt" :value="opt">{{ intentLabel(opt) }}</option>
        </select>
        <select v-model="filters.category_id" data-testid="results-category-filter" @change="reload">
          <option value="">{{ $t('results.allCategories') }}</option>
          <option v-for="cat in categories" :key="cat.id" :value="cat.id">{{ cat.name }}（{{ cat.result_count ?? 0 }}）</option>
        </select>
        <button
          class="btn btn-sm results-category-create-btn"
          data-testid="results-category-create"
          :title="$t('results.createCategory')"
          @click="showCategoryCreate = !showCategoryCreate"
        >＋</button>
        <input
          v-if="showCategoryCreate"
          v-model="newCategoryName"
          class="results-category-name-input"
          type="text"
          maxlength="60"
          data-testid="results-category-name-input"
          :placeholder="$t('results.categoryNamePlaceholder')"
          @keyup.enter="createCategory"
        />
        <button
          v-if="showCategoryCreate"
          class="btn btn-sm btn-primary"
          data-testid="results-category-save"
          :disabled="creatingCategory || !newCategoryName.trim()"
          @click="createCategory"
        >{{ $t('common.create') }}</button>
        <input
          v-model="filters.tag"
          class="results-tag-input"
          type="text"
          data-testid="results-tag-filter"
          :placeholder="$t('results.tagFilter')"
          @input="onSearchInput"
        />
        <select v-model="filters.sort" data-testid="results-sort" @change="reload">
          <option value="created_desc">{{ $t('results.sortCreatedDesc') }}</option>
          <option value="created_asc">{{ $t('results.sortCreatedAsc') }}</option>
          <option value="score_desc">{{ $t('results.sortScoreDesc') }}</option>
        </select>
      </div>
      <div class="results-filter-meta">
        <span data-testid="results-total">{{ $t('results.totalCount', { n: total }) }}</span>
        <span v-if="loading">{{ $t('common.loadingEllipsis') }}</span>
      </div>
    </div>

    <!-- Flat results table -->
    <div class="card results-table-card">
      <div v-if="!loading && results.length === 0" class="results-empty" data-testid="results-empty">
        {{ $t('results.empty') }}
      </div>
      <table v-else class="results-table">
        <thead>
          <tr>
            <th>{{ $t('results.colTitle') }}</th>
            <th>{{ $t('results.colSummary') }}</th>
            <th>{{ $t('results.colIntent') }}</th>
            <th>{{ $t('results.colCategory') }}</th>
            <th>{{ $t('results.colTags') }}</th>
            <th>{{ $t('results.colScore') }}</th>
            <th>{{ $t('results.colVerdict') }}</th>
            <th>{{ $t('results.colCreated') }}</th>
            <th class="cell-actions">{{ $t('results.colActions') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(r, i) in results"
            :key="r.result_id"
            :data-testid="`results-row-${i}`"
            :class="{ 'row-active': selectedId === r.result_id }"
            @click="openDetail(r.result_id)"
          >
            <td class="cell-title">
              <span class="result-title" :title="r.title">{{ r.title }}</span>
              <span v-if="r.has_html" class="result-html-dot" :title="$t('results.hasHtml')">HTML</span>
            </td>
            <td class="cell-summary">
              <span class="result-display" :title="r.display_text">{{ r.display_text || '--' }}</span>
            </td>
            <td>
              <span :class="['badge', `intent-${r.intent}`]">{{ intentLabel(r.intent) }}</span>
            </td>
            <td class="cell-category" :data-testid="`results-cat-${i}`">
              <span v-if="r.category_id">{{ categoryName(r.category_id) }}</span>
              <span v-else class="muted">--</span>
            </td>
            <td class="cell-tags">
              <span v-if="!r.tags?.length" class="muted">--</span>
              <span v-for="tag in r.tags.slice(0, 3)" :key="tag" class="result-tag-chip">{{ tag }}</span>
              <span v-if="r.tags?.length > 3" class="muted">+{{ r.tags.length - 3 }}</span>
            </td>
            <td><span v-if="r.score !== null && r.score !== undefined" class="result-score">{{ r.score }}</span><span v-else class="muted">--</span></td>
            <td><span class="result-verdict">{{ r.verdict || '--' }}</span></td>
            <td class="cell-created">{{ formatDateShort(r.created_at) }}</td>
            <td class="cell-actions" @click.stop>
              <button class="btn btn-sm" :data-testid="`results-detail-btn-${i}`" @click="openDetail(r.result_id)">
                {{ $t('results.detailAction') }}
              </button>
              <button
                v-if="r.has_report"
                class="btn btn-sm"
                :data-testid="`results-report-btn-${i}`"
                @click="openReport(r)"
              >
                {{ $t('results.reportAction') }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- Paging -->
      <div v-if="total > pageSize" class="results-pagination">
        <button class="btn btn-sm" :disabled="page <= 1 || loading" data-testid="results-prev" @click="page--; load()">
          {{ $t('common.prev') }}
        </button>
        <span class="page-info">{{ page }} / {{ maxPage }}</span>
        <button class="btn btn-sm" :disabled="page >= maxPage || loading" data-testid="results-next" @click="page++; load()">
          {{ $t('common.next') }}
        </button>
      </div>
    </div>

    <!-- Detail drawer -->
    <div v-if="selectedId" class="results-drawer" data-testid="results-drawer">
      <div class="results-drawer-head">
        <div class="results-drawer-title">
          <span>{{ selected?.title || selectedId }}</span>
          <span v-if="selected" :class="['badge', `intent-${selected.intent}`]">{{ intentLabel(selected.intent) }}</span>
          <span v-if="selected?.score !== null && selected?.score !== undefined" class="result-score">{{ selected.score }}</span>
          <span v-if="selected?.verdict" class="result-verdict">{{ selected.verdict }}</span>
        </div>
        <button class="btn btn-sm" data-testid="results-drawer-close" @click="selectedId = null">
          {{ $t('common.close') }}
        </button>
      </div>

      <ResultSummaryCard ref="summaryCard" :result-id="selectedId" @updated="onDetailUpdated" />

      <div v-if="detailMeta" class="results-meta-block">
        <div class="detail-grid">
          <div class="detail-item">
            <span class="detail-label">{{ $t('results.metaResultId') }}</span>
            <span class="detail-value">{{ detailMeta.result_id }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">{{ $t('results.metaScene') }}</span>
            <span class="detail-value">{{ detailMeta.scene || '--' }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">{{ $t('results.metaHarness') }}</span>
            <span class="detail-value">{{ detailMeta.harness || '--' }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">{{ $t('results.metaCategory') }}</span>
            <select
              v-model="draftCategory"
              class="result-category-select"
              data-testid="results-detail-category"
              :disabled="categorySaving"
              @change="saveCategory"
            >
              <option value="">{{ $t('history.uncategorized') }}</option>
              <option v-for="cat in categories" :key="cat.id" :value="cat.id">{{ cat.name }}</option>
            </select>
            <span v-if="categorySaving" class="muted">{{ $t('common.loadingEllipsis') }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">{{ $t('results.metaCompleted') }}</span>
            <span class="detail-value">{{ formatDateShort(detailMeta.completed_at) }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">{{ $t('results.metaReport') }}</span>
            <span class="detail-value">
              {{ detailMeta.metadata?.report_md ? `${detailMeta.metadata.report_md.bytes} B` : '--' }}
            </span>
          </div>
        </div>
        <div v-if="htmlFiles.length" class="results-html-links">
          <span class="detail-label">{{ $t('results.htmlFiles') }}</span>
          <div v-for="h in htmlFiles" :key="h.path" class="results-html-link">
            <a :href="h.url + assetToken" target="_blank" rel="noopener">{{ h.path }}</a>
            <span class="muted">（{{ h.bytes ?? '--' }} B）</span>
          </div>
        </div>
        <div v-if="detailMeta.summary_json?.sources && sourceEntries.length" class="results-sources">
          <span class="detail-label">{{ $t('results.sources') }}</span>
          <ul>
            <li v-for="[k, v] in sourceEntries" :key="k"><code>{{ k }}</code> ← {{ v }}</li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { api, getToken } from '../../api/index.js';
import ResultSummaryCard from './ResultSummaryCard.vue';

const { t } = useI18n();
const emit = defineEmits(['open-report']);

const intentOptions = ['deep-diagnosis', 'stability-report', 'quick-screen', 'doe-analysis', 'experience-mining', 'optimizer-campaign'];
const pageSize = 50;

const results = ref([]);
const total = ref(0);
const page = ref(1);
const loading = ref(false);
const categories = ref([]);
const selectedId = ref(null);
const detailMeta = ref(null);
const summaryCard = ref(null);

const filters = reactive({ q: '', intent: '', category_id: '', tag: '', sort: 'created_desc' });
const draftCategory = ref('');
const categorySaving = ref(false);
const showCategoryCreate = ref(false);
const newCategoryName = ref('');
const creatingCategory = ref(false);

const maxPage = computed(() => Math.max(1, Math.ceil(total.value / pageSize)));
const selected = computed(() => results.value.find((r) => r.result_id === selectedId.value) || null);
const htmlFiles = computed(() => detailMeta.value?.files?.html || []);
const sourceEntries = computed(() => Object.entries(detailMeta.value?.summary_json?.sources || {}).slice(0, 10));
const assetToken = computed(() => {
  const token = getToken();
  return token ? `?token=${encodeURIComponent(token)}` : '';
});

function intentLabel(intent) {
  const key = `results.intentNames.${intent}`;
  if (t(key) !== key) return t(key);
  return intent;
}

let searchTimer = null;
function onSearchInput() {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(reload, 300);
}

function reload() {
  page.value = 1;
  load();
}

async function load() {
  loading.value = true;
  try {
    const data = await api.listResults({
      q: filters.q.trim() || undefined,
      intent: filters.intent || undefined,
      category_id: filters.category_id || undefined,
      tag: filters.tag.trim() || undefined,
      sort: filters.sort || undefined,
      limit: pageSize,
      offset: (page.value - 1) * pageSize,
    });
    results.value = data.results;
    total.value = data.total;
  } catch (err) {
    console.error('Failed to load results:', err);
    results.value = [];
    total.value = 0;
  } finally {
    loading.value = false;
  }
}

async function loadCategories() {
  try {
    // Results-surface listing: result_count matches what THIS page can list
    // (own + legacy rows), unlike history's run_count.
    categories.value = await api.listResultCategories();
  } catch (err) {
    console.error('Failed to load categories:', err);
  }
}

// Create a category on the results surface (same service as History); on
// success it becomes the active filter so the new category is immediately
// visible (empty until results are assigned to it).
async function createCategory() {
  const name = newCategoryName.value.trim();
  if (!name || creatingCategory.value) return;
  creatingCategory.value = true;
  try {
    const created = await api.createResultCategory(name);
    newCategoryName.value = '';
    showCategoryCreate.value = false;
    await loadCategories();
    filters.category_id = created.id;
    await load();
  } catch (err) {
    alert(`${t('results.categoryCreateFailed')}${err.message || err}`);
  } finally {
    creatingCategory.value = false;
  }
}

function categoryName(id) {
  if (!id) return t('history.uncategorized');
  return categories.value.find((c) => c.id === id)?.name || '--';
}

async function openDetail(resultId) {
  selectedId.value = resultId;
  detailMeta.value = null;
  try {
    detailMeta.value = await api.getResultDetail(resultId, { includeMd: false });
    draftCategory.value = detailMeta.value?.category_id || '';
  } catch (err) {
    console.error('Failed to load result detail:', err);
  }
}

// Category assignment lives on the run row (single source of truth); the
// PATCH delegates there and the table column follows immediately.
async function saveCategory() {
  if (!selectedId.value || categorySaving.value) return;
  categorySaving.value = true;
  try {
    const updated = await api.patchResult(selectedId.value, { category_id: draftCategory.value || null });
    detailMeta.value = { ...detailMeta.value, ...updated };
    const row = results.value.find((r) => r.result_id === selectedId.value);
    if (row) row.category_id = updated.category_id;
    if (filters.category_id) await load();
  } catch (err) {
    alert(`${t('results.categorySaveFailed')}${err.message || err}`);
    draftCategory.value = detailMeta.value?.category_id || '';
  } finally {
    categorySaving.value = false;
  }
}

function onDetailUpdated(updated) {
  detailMeta.value = { ...detailMeta.value, ...updated };
  const row = results.value.find((r) => r.result_id === updated.result_id);
  if (row) {
    row.description = updated.description;
    row.tags = updated.tags;
    row.display_text = updated.description || row.display_text;
  }
}

// Reports tab expects a run-dir-relative report path (App derives the run dir
// from it). The card carries no path, so read it from the detail metadata —
// reusing an already-loaded drawer detail when it matches the row.
async function openReport(row) {
  let path = null;
  if (detailMeta.value?.result_id === row.result_id) {
    path = detailMeta.value.metadata?.report_md?.path || null;
  }
  if (!path) {
    try {
      const d = await api.getResultDetail(row.result_id, { includeMd: false });
      path = d.metadata?.report_md?.path
        || (d.metadata?.workspace_path ? `${d.metadata.workspace_path}/report.md` : null);
    } catch (err) {
      console.error('Failed to resolve report path:', err);
    }
  }
  emit('open-report', path || '');
}

function formatDateShort(s) {
  if (!s) return '--';
  return String(s).slice(0, 16);
}

onMounted(() => {
  load();
  loadCategories();
});
</script>

<style scoped>
.results-library { display: flex; flex-direction: column; gap: 14px; }
.results-filter-bar { padding: 12px 16px; }
.results-filter-row { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }
.results-search { flex: 2 1 220px; min-width: 180px; }
.results-tag-input { flex: 1 1 140px; min-width: 120px; }
.results-filter-row select {
  flex: 1 1 150px; min-width: 130px;
}
.results-filter-row input, .results-filter-row select {
  border: 1px solid var(--border-color, #d8dee9); border-radius: 8px;
  padding: 7px 10px; font-size: 13px; background: var(--surface, #fff);
}
.results-filter-meta {
  margin-top: 8px; font-size: 12px; color: var(--text-muted, #7b869a);
  display: flex; gap: 12px;
}
.results-table-card { padding: 0; overflow-x: auto; }
.results-empty { padding: 40px 16px; text-align: center; color: var(--text-muted, #7b869a); }
.results-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.results-table th {
  text-align: left; padding: 10px 12px; font-size: 12px; color: var(--text-muted, #7b869a);
  border-bottom: 1px solid var(--border-color, #d8dee9);
  position: sticky; top: 0; background: var(--surface, #fff);
}
.results-table td {
  padding: 9px 12px; border-bottom: 1px solid var(--border-color-soft, #eaeef4);
  vertical-align: top;
}
.results-table tbody tr { cursor: pointer; }
.results-table tbody tr:hover { background: var(--surface-soft, #f5f8fd); }
.row-active { background: var(--accent-soft, #e8f0fe) !important; }
.cell-title { max-width: 220px; }
.result-title { font-weight: 600; display: inline-block; max-width: 190px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; vertical-align: bottom; }
.result-html-dot {
  margin-left: 6px; font-size: 10px; padding: 1px 5px; border-radius: 4px;
  background: var(--accent-soft, #e8f0fe); color: var(--accent-text, #2456c4);
}
.cell-summary { max-width: 340px; }
.result-display {
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
  overflow: hidden; line-height: 1.5; color: var(--text-secondary, #4a5568);
}
.cell-tags { max-width: 140px; display: flex; flex-wrap: wrap; gap: 4px; }
.result-tag-chip {
  border-radius: 999px; padding: 1px 8px; font-size: 11px;
  background: var(--accent-soft, #e8f0fe); color: var(--accent-text, #2456c4);
}
.result-score { font-weight: 700; font-variant-numeric: tabular-nums; }
.result-verdict { font-size: 12px; }
.cell-created { white-space: nowrap; color: var(--text-muted, #7b869a); font-variant-numeric: tabular-nums; }
.cell-actions { white-space: nowrap; text-align: right; }
.cell-actions .btn { margin-left: 6px; }
.results-pagination { display: flex; align-items: center; gap: 10px; justify-content: center; padding: 12px; }
.page-info { font-size: 12px; color: var(--text-muted, #7b869a); }

.results-drawer {
  border: 1px solid var(--border-color, #d8dee9); border-radius: 12px;
  padding: 14px 16px; background: var(--surface, #fff);
  display: flex; flex-direction: column; gap: 12px;
}
.results-drawer-head { display: flex; align-items: center; gap: 10px; }
.results-drawer-title { display: flex; align-items: center; gap: 8px; font-weight: 600; flex: 1; min-width: 0; }
.results-drawer-title > span:first-child {
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.results-meta-block { display: flex; flex-direction: column; gap: 10px; }
.results-html-links { display: flex; flex-direction: column; gap: 4px; font-size: 12.5px; }
.results-html-link a { color: var(--accent-text, #2456c4); }
.results-sources { font-size: 12px; }
.results-sources ul { margin: 4px 0 0; padding-left: 18px; }
.results-sources code { background: var(--surface-soft, #f0f3f8); padding: 0 4px; border-radius: 4px; }
.result-category-select {
  border: 1px solid var(--border-color, #d8dee9); border-radius: 8px;
  padding: 4px 8px; font-size: 12.5px; background: var(--surface, #fff); max-width: 180px;
}
.results-category-create-btn { flex: 0 0 auto; }
.results-category-name-input {
  flex: 1 1 150px; min-width: 130px;
  border: 1px solid var(--border-color, #d8dee9); border-radius: 8px;
  padding: 7px 10px; font-size: 13px; background: var(--surface, #fff);
}
.muted { color: var(--text-muted, #9aa4b5); }

@media (max-width: 1100px) {
  .cell-summary { max-width: 240px; }
  .cell-tags { display: none; }
}
</style>
