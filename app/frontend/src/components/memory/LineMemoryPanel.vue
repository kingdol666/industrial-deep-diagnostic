<template>
  <div class="line-memory" data-testid="line-memory">
    <!-- ── 左栏:产线列表 ── -->
    <aside class="lm-side card">
      <div class="lm-side-head">
        <div>
          <div class="lm-side-title">{{ $t('memory.title') }}</div>
          <div class="lm-side-sub">{{ $t('memory.subtitle') }}</div>
        </div>
        <button class="btn btn-sm" data-testid="lm-refresh" :disabled="loadingLines" @click="refreshAll">
          {{ loadingLines ? $t('memory.loading') : $t('memory.refresh') }}
        </button>
      </div>

      <div v-if="linesError" class="lm-error">{{ linesError }}</div>
      <div v-else-if="!lines.length && !loadingLines" class="lm-empty">
        {{ $t('memory.noLines') }}
        <div class="lm-empty-hint">{{ $t('memory.noLinesHint') }}</div>
      </div>

      <button
        v-for="line in lines"
        :key="line.line_key"
        class="lm-line-pill"
        :class="{ active: line.line_key === selectedKey }"
        data-testid="lm-line-pill"
        @click="selectLine(line.line_key)"
      >
        <div class="lm-line-name">{{ line.name || line.line_key }}</div>
        <div class="lm-line-key">{{ line.line_key }}</div>
        <div class="lm-line-chips">
          <span v-if="line.stats" class="lm-chip lm-chip-consensus">{{ line.stats.consensus }} {{ $t('memory.gradeConsensus') }}</span>
          <span v-if="line.stats" class="lm-chip">{{ line.stats.candidate }} {{ $t('memory.gradeCandidate') }}</span>
          <span v-if="line.stats && line.stats.competing" class="lm-chip lm-chip-warn">{{ line.stats.competing }} {{ $t('memory.gradeCompeting') }}</span>
          <span v-if="line.pending_proposals" class="lm-chip lm-chip-warn">{{ line.pending_proposals }} {{ $t('memory.pendingShort') }}</span>
        </div>
        <div v-if="line.latest_state" class="lm-line-score">
          <span class="lm-score-num">{{ fmtNum(line.latest_state.score) }}</span>
          <span class="lm-score-grade" v-if="line.latest_state.grade">{{ line.latest_state.grade }}</span>
          <span class="lm-score-label" v-if="line.latest_state.label">{{ line.latest_state.label }}</span>
        </div>
      </button>
    </aside>

    <!-- ── 右栏:选中产线详情 ── -->
    <section class="lm-detail">
      <div v-if="detailError" class="lm-error">{{ detailError }}</div>
      <div v-else-if="!selectedKey" class="lm-empty card">{{ $t('memory.selectLine') }}</div>

      <template v-else-if="detail">
        <!-- 概览条 -->
        <div class="card lm-overview">
          <div class="lm-overview-main">
            <div class="lm-overview-title">{{ detail.name || detail.line_key }}</div>
            <div class="lm-overview-aliases" v-if="detail.aliases && detail.aliases.length">
              {{ $t('memory.aliases') }}: {{ detail.aliases.slice(0, 6).join(' · ') }}
            </div>
          </div>
          <div class="lm-stat-grid" v-if="detail.consensus">
            <div class="lm-stat"><b>{{ detail.consensus.stats.findings }}</b><span>{{ $t('memory.statFindings') }}</span></div>
            <div class="lm-stat"><b class="lm-c-consensus">{{ detail.consensus.stats.consensus }}</b><span>{{ $t('memory.gradeConsensus') }}</span></div>
            <div class="lm-stat"><b>{{ detail.consensus.stats.candidate }}</b><span>{{ $t('memory.gradeCandidate') }}</span></div>
            <div class="lm-stat"><b>{{ detail.consensus.stats.singleton }}</b><span>{{ $t('memory.gradeSingleton') }}</span></div>
            <div class="lm-stat"><b class="lm-c-warn">{{ detail.consensus.stats.competing }}</b><span>{{ $t('memory.gradeCompeting') }}</span></div>
            <div class="lm-stat"><b>{{ detail.consensus.stats.stale || 0 }}</b><span>{{ $t('memory.statStale') }}</span></div>
          </div>
          <div class="lm-overview-actions">
            <button class="btn btn-sm" data-testid="lm-merge" :disabled="!otherLines.length" @click="showMerge = !showMerge">
              {{ $t('memory.mergeAction') }}
            </button>
            <button class="btn btn-sm" data-testid="lm-consolidate" @click="reconsolidate">{{ $t('memory.reconsolidate') }}</button>
          </div>
          <div v-if="showMerge" class="lm-merge-row">
            <select v-model="mergeTarget" data-testid="lm-merge-target">
              <option value="">{{ $t('memory.mergeSelect') }}</option>
              <option v-for="l in otherLines" :key="l.line_key" :value="l.line_key">{{ l.name || l.line_key }}</option>
            </select>
            <button class="btn btn-sm btn-primary" :disabled="!mergeTarget || merging" @click="doMerge">
              {{ merging ? $t('memory.loading') : $t('memory.mergeConfirm') }}
            </button>
          </div>
        </div>

        <!-- 子视图切换 -->
        <div class="lm-subtabs">
          <button class="lm-subtab" :class="{ active: subView === 'consensus' }" data-testid="lm-tab-consensus" @click="subView = 'consensus'">
            {{ $t('memory.tabConsensus') }} <span class="lm-count">{{ detail.consensus ? detail.consensus.entries.length : 0 }}</span>
          </button>
          <button class="lm-subtab" :class="{ active: subView === 'proposals' }" data-testid="lm-tab-proposals" @click="subView = 'proposals'">
            {{ $t('memory.tabProposals') }} <span class="lm-count">{{ detail.proposals.length }}</span>
          </button>
          <button class="lm-subtab" :class="{ active: subView === 'ontology' }" data-testid="lm-tab-ontology" @click="subView = 'ontology'">
            {{ $t('memory.tabOntology') }} <span class="lm-count">{{ ontologyVersionCount }}</span>
          </button>
        </div>

        <!-- 共识条目 -->
        <div v-if="subView === 'consensus'" class="lm-entries">
          <div v-if="detail.consensus && !detail.consensus.entries.length" class="lm-empty card">
            {{ $t('memory.noEntries') }}
          </div>
          <div
            v-for="entry in visibleEntries"
            :key="entry.entry_key"
            class="card lm-entry"
            :class="'lm-entry-' + entry.grade"
            data-testid="lm-entry"
          >
            <div class="lm-entry-head" @click="toggleExpand(entry.entry_key)">
              <span class="lm-badge" :class="'lm-badge-' + entry.grade">{{ gradeLabel(entry.grade) }}</span>
              <span class="lm-entry-subject">{{ entry.subject }}</span>
              <span class="lm-entry-claim">{{ entry.claim_type }}</span>
              <span class="lm-entry-dirs">
                <span v-for="d in entry.directions" :key="d.direction || 'none'" class="lm-dir" :class="{ refuted: d.status === 'refuted' }">
                  {{ d.direction || '—' }} ×{{ d.independent }}<template v-if="d.status === 'refuted'"> {{ $t('memory.refutedShort') }}</template>
                </span>
              </span>
              <span v-if="entry.stale" class="lm-chip lm-chip-warn">{{ $t('memory.staleShort') }}</span>
              <span class="lm-entry-meta">{{ fmtDate(entry.last_seen) }} · {{ $t('memory.confidenceShort') }} {{ entry.confidence ?? '—' }}</span>
              <span class="lm-expand">{{ expanded[entry.entry_key] ? '▾' : '▸' }}</span>
            </div>
            <div class="lm-entry-narrative">{{ entry.narrative }}</div>
            <div v-if="expanded[entry.entry_key]" class="lm-entry-body">
              <div class="lm-entry-section">
                <div class="lm-entry-section-title">{{ $t('memory.sourcesTitle') }}（{{ entry.sources.length }}）</div>
                <div class="lm-source-row" v-for="(s, i) in entry.sources.slice(0, 20)" :key="i">
                  <button class="lm-link" :title="$t('memory.openRun')" @click.stop="emitOpenRun(s.run_id)">{{ s.run_id }}</button>
                  <span class="lm-source-date">{{ fmtDate(s.observed_at) }}</span>
                  <span class="lm-source-dir" v-if="s.direction">{{ s.direction }}</span>
                  <span class="lm-source-detail">{{ s.detail }}</span>
                </div>
              </div>
              <div class="lm-entry-actions">
                <button
                  v-if="!isManuallyRefuted(entry)"
                  class="btn btn-sm"
                  data-testid="lm-refute"
                  @click.stop="promptRefute(entry)"
                >{{ $t('memory.refuteAction') }}</button>
                <button
                  v-else
                  class="btn btn-sm"
                  data-testid="lm-unrefute"
                  @click.stop="unrefute(entry)"
                >{{ $t('memory.unrefuteAction') }}</button>
              </div>
            </div>
          </div>
          <div v-if="sortedEntries.length > visibleLimit" class="lm-more-row">
            <button class="btn btn-sm" data-testid="lm-show-more" @click="visibleLimit += 60">
              {{ $t('memory.showMore', { n: sortedEntries.length - visibleLimit }) }}
            </button>
          </div>
        </div>

        <!-- 本体提案 -->
        <div v-else-if="subView === 'proposals'" class="lm-entries">
          <div v-if="!detail.proposals.length" class="lm-empty card">{{ $t('memory.noProposals') }}</div>
          <div v-for="p in detail.proposals" :key="p.proposal_id" class="card lm-proposal" data-testid="lm-proposal">
            <div class="lm-proposal-head">
              <span class="lm-badge" :class="'lm-tier-' + p.tier">{{ tierLabel(p.tier) }}</span>
              <span class="lm-badge" :class="'lm-status-' + p.status">{{ statusLabel(p.status) }}</span>
              <span class="lm-entry-subject">{{ p.op }} · {{ p.target }}</span>
              <span class="lm-entry-meta">{{ p.scene_key }} · {{ fmtDate(p.created_at) }}</span>
            </div>
            <div class="lm-entry-narrative">{{ p.rationale }}</div>
            <div class="lm-proposal-meta">
              <span v-if="p.applied && p.applied.version">→ v{{ p.applied.version }}</span>
              <span v-if="p.corroborating_runs && p.corroborating_runs.length">{{ $t('memory.corroboratedBy', { n: p.corroborating_runs.length }) }}</span>
              <span v-if="p.validation && !p.validation.ok" class="lm-c-warn">{{ (p.validation.errors || []).join('; ') }}</span>
            </div>
            <div class="lm-entry-actions" v-if="p.status === 'pending_approval' || p.status === 'pending_corroboration'">
              <button class="btn btn-sm btn-primary" data-testid="lm-approve" :disabled="decidingId === p.proposal_id" @click="decide(p, 'approve')">{{ $t('memory.approve') }}</button>
              <button class="btn btn-sm" data-testid="lm-reject" :disabled="decidingId === p.proposal_id" @click="decide(p, 'reject')">{{ $t('memory.reject') }}</button>
            </div>
          </div>
        </div>

        <!-- 本体版本链 -->
        <div v-else class="lm-entries">
          <div v-if="!ontologyScenes.length" class="lm-empty card">{{ $t('memory.noOntology') }}</div>
          <div v-for="scene in ontologyScenes" :key="scene.scene_key" class="card lm-ontology-scene" data-testid="lm-ontology-scene">
            <div class="lm-ontology-scene-title">{{ scene.scene_key }}</div>
            <div class="lm-version-row" v-for="v in scene.versions" :key="v.version">
              <span class="lm-version-num">v{{ v.version }}</span>
              <span class="lm-version-parent" v-if="v.parent_version">← v{{ v.parent_version }}</span>
              <span class="lm-badge lm-tier-auto" v-if="v.origin === 'diagnosis'">{{ $t('memory.originDiagnosis') }}</span>
              <span class="lm-version-quality">{{ v.quality || 'unvalidated' }}</span>
              <span class="lm-version-mode">{{ v.build_mode || '—' }}</span>
              <span class="lm-version-date">{{ fmtDate(v.created_at) }}</span>
              <button v-if="v.built_from_run" class="lm-link" @click="emitOpenRun(v.built_from_run)">{{ v.built_from_run }}</button>
            </div>
          </div>
        </div>
      </template>

      <div v-else-if="loadingDetail" class="lm-empty card">{{ $t('memory.loading') }}</div>
    </section>

    <!-- 人工反证输入 -->
    <div v-if="refuteTarget" class="lm-modal-mask" @click.self="refuteTarget = null">
      <div class="card lm-modal">
        <div class="lm-modal-title">{{ $t('memory.refuteTitle', { subject: refuteTarget.subject }) }}</div>
        <textarea v-model="refuteReason" rows="3" :placeholder="$t('memory.refuteReasonPlaceholder')" data-testid="lm-refute-reason"></textarea>
        <div class="lm-modal-actions">
          <button class="btn btn-sm" @click="refuteTarget = null">{{ $t('memory.cancel') }}</button>
          <button class="btn btn-sm btn-primary" :disabled="refuting" @click="confirmRefute">{{ refuting ? $t('memory.loading') : $t('memory.refuteConfirm') }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { api } from '../../api/index.js';
import i18n from '../../i18n/index.js';

const emit = defineEmits(['open-run']);
const t = (k, args) => i18n.global.t(k, args);

const lines = ref([]);
const loadingLines = ref(false);
const linesError = ref('');
const selectedKey = ref('');
const detail = ref(null);
const loadingDetail = ref(false);
const detailError = ref('');
const ontologyScenes = ref([]);
const subView = ref('consensus');
const expanded = ref({});
const visibleLimit = ref(60);
const showMerge = ref(false);
const mergeTarget = ref('');
const merging = ref(false);
const refuteTarget = ref(null);
const refuteReason = ref('');
const refuting = ref(false);
const decidingId = ref('');

const otherLines = computed(() => lines.value.filter((l) => l.line_key !== selectedKey.value));
const sortedEntries = computed(() => {
  const order = { consensus: 0, candidate: 1, competing: 2, singleton: 3, refuted: 4 };
  const entries = detail.value?.consensus?.entries || [];
  return [...entries].sort((a, b) => {
    const ga = order[a.grade] ?? 9;
    const gb = order[b.grade] ?? 9;
    if (ga !== gb) return ga - gb;
    return (b.independent || 0) - (a.independent || 0);
  });
});
const ontologyVersionCount = computed(() => ontologyScenes.value.reduce((n, s) => n + s.versions.length, 0));
// Large lines (150+ leads) must not render every card at once.
const visibleEntries = computed(() => sortedEntries.value.slice(0, visibleLimit.value));

function fmtNum(v) {
  const n = Number(v);
  return Number.isFinite(n) ? (Math.round(n * 10) / 10) : '—';
}
function fmtDate(v) {
  if (!v) return '—';
  return String(v).slice(0, 16).replace('T', ' ');
}
function gradeLabel(g) {
  const map = {
    consensus: t('memory.gradeConsensus'),
    candidate: t('memory.gradeCandidate'),
    singleton: t('memory.gradeSingleton'),
    competing: t('memory.gradeCompeting'),
    refuted: t('memory.gradeRefuted'),
  };
  return map[g] || g;
}
function tierLabel(tier) {
  return { additive: t('memory.tierAdditive'), correction: t('memory.tierCorrection'), removal: t('memory.tierRemoval') }[tier] || tier;
}
function statusLabel(status) {
  const map = {
    applied: t('memory.statusApplied'),
    pending_corroboration: t('memory.statusPendingCorroboration'),
    pending_approval: t('memory.statusPendingApproval'),
    rejected: t('memory.statusRejected'),
    invalid: t('memory.statusInvalid'),
    apply_failed: t('memory.statusApplyFailed'),
  };
  return map[status] || status;
}
function isManuallyRefuted(entry) {
  return entry.override && entry.override.status === 'refuted';
}
function emitOpenRun(runId) {
  if (runId) emit('open-run', runId);
}
function toggleExpand(key) {
  expanded.value = { ...expanded.value, [key]: !expanded.value[key] };
}

async function loadLines(keepSelection = false) {
  loadingLines.value = true;
  linesError.value = '';
  try {
    const data = await api.lineMemoryListLines();
    lines.value = Array.isArray(data) ? data : [];
    if (!keepSelection || !lines.value.some((l) => l.line_key === selectedKey.value)) {
      if (lines.value.length) await selectLine(lines.value[0].line_key);
      else { selectedKey.value = ''; detail.value = null; }
    }
  } catch (err) {
    linesError.value = err.message || String(err);
  } finally {
    loadingLines.value = false;
  }
}

async function selectLine(key) {
  selectedKey.value = key;
  loadingDetail.value = true;
  detailError.value = '';
  expanded.value = {};
  visibleLimit.value = 60;
  showMerge.value = false;
  try {
    const [d, ont] = await Promise.all([
      api.lineMemoryGetLine(key),
      api.lineMemoryOntology(key).catch(() => ({ scenes: [] })),
    ]);
    detail.value = d;
    ontologyScenes.value = (ont && ont.scenes) || [];
  } catch (err) {
    detailError.value = err.message || String(err);
    detail.value = null;
  } finally {
    loadingDetail.value = false;
  }
}

async function refreshAll() {
  await loadLines(true);
  if (selectedKey.value) await selectLine(selectedKey.value);
}

async function reconsolidate() {
  if (!selectedKey.value) return;
  try {
    await api.lineMemoryConsolidate(selectedKey.value);
    await refreshAll();
  } catch (err) {
    detailError.value = err.message || String(err);
  }
}

async function doMerge() {
  if (!selectedKey.value || !mergeTarget.value) return;
  merging.value = true;
  try {
    await api.lineMemoryMerge(selectedKey.value, mergeTarget.value);
    mergeTarget.value = '';
    showMerge.value = false;
    selectedKey.value = '';
    await loadLines(false);
  } catch (err) {
    detailError.value = err.message || String(err);
  } finally {
    merging.value = false;
  }
}

function promptRefute(entry) {
  refuteTarget.value = entry;
  refuteReason.value = '';
}
async function confirmRefute() {
  if (!refuteTarget.value) return;
  refuting.value = true;
  try {
    await api.lineMemoryRefute(selectedKey.value, {
      entry_key: refuteTarget.value.entry_key,
      reason: refuteReason.value,
    });
    refuteTarget.value = null;
    await selectLine(selectedKey.value);
    await loadLines(true);
  } catch (err) {
    detailError.value = err.message || String(err);
  } finally {
    refuting.value = false;
  }
}
async function unrefute(entry) {
  try {
    await api.lineMemoryUnrefute(selectedKey.value, { entry_key: entry.entry_key });
    await selectLine(selectedKey.value);
    await loadLines(true);
  } catch (err) {
    detailError.value = err.message || String(err);
  }
}
async function decide(p, action) {
  decidingId.value = p.proposal_id;
  try {
    if (action === 'approve') await api.lineMemoryApproveProposal(p.proposal_id);
    else await api.lineMemoryRejectProposal(p.proposal_id);
    await selectLine(selectedKey.value);
    await loadLines(true);
  } catch (err) {
    detailError.value = err.message || String(err);
  } finally {
    decidingId.value = '';
  }
}

onMounted(() => loadLines(false));
</script>

<style scoped>
.line-memory {
  display: grid;
  grid-template-columns: 300px 1fr;
  gap: 14px;
  align-items: start;
}
@media (max-width: 1100px) {
  .line-memory { grid-template-columns: 1fr; }
}
.lm-side { padding: 14px; display: flex; flex-direction: column; gap: 8px; position: sticky; top: 12px; max-height: calc(100vh - 90px); overflow: auto; }
.lm-side-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; }
.lm-side-title { font-weight: 600; color: var(--text); }
.lm-side-sub { font-size: 11px; color: var(--text3); margin-top: 2px; }
.lm-line-pill {
  display: flex; flex-direction: column; gap: 4px; text-align: left;
  background: var(--surface-soft); border: 1px solid var(--border);
  border-radius: 8px; padding: 10px; cursor: pointer; color: var(--text2);
  transition: border-color 0.15s, background 0.15s;
}
.lm-line-pill:hover { border-color: var(--border-strong); }
.lm-line-pill.active { border-color: var(--border-accent); background: var(--surface2); }
.lm-line-name { font-size: 13px; font-weight: 600; color: var(--text); }
.lm-line-key { font-size: 10px; color: var(--text-dim); font-family: ui-monospace, monospace; }
.lm-line-chips { display: flex; flex-wrap: wrap; gap: 4px; }
.lm-chip { font-size: 10px; padding: 1px 6px; border-radius: 999px; background: var(--surface2); color: var(--text3); border: 1px solid var(--border); }
.lm-chip-consensus { color: var(--accent-bright); border-color: var(--border-accent); }
.lm-chip-warn { color: #e07a5f; border-color: rgba(224, 122, 95, 0.35); }
.lm-line-score { display: flex; align-items: baseline; gap: 6px; margin-top: 2px; }
.lm-score-num { font-size: 18px; font-weight: 700; color: var(--text); }
.lm-score-grade { font-size: 11px; padding: 0 6px; border-radius: 4px; background: var(--surface2); color: var(--accent); }
.lm-score-label { font-size: 11px; color: var(--text3); }

.lm-detail { display: flex; flex-direction: column; gap: 10px; min-width: 0; }
.lm-overview { padding: 14px; display: flex; flex-wrap: wrap; gap: 12px; align-items: center; }
.lm-overview-main { flex: 1 1 240px; min-width: 200px; }
.lm-overview-title { font-size: 16px; font-weight: 700; color: var(--text); }
.lm-overview-aliases { font-size: 11px; color: var(--text3); margin-top: 3px; word-break: break-all; }
.lm-stat-grid { display: flex; flex-wrap: wrap; gap: 14px; }
.lm-stat { display: flex; flex-direction: column; align-items: center; min-width: 48px; }
.lm-stat b { font-size: 17px; color: var(--text); }
.lm-stat span { font-size: 10px; color: var(--text3); }
.lm-c-consensus { color: var(--accent) !important; }
.lm-c-warn { color: #e07a5f !important; }
.lm-overview-actions { display: flex; gap: 6px; }
.lm-merge-row { flex-basis: 100%; display: flex; gap: 8px; align-items: center; }
.lm-merge-row select { flex: 1; max-width: 320px; }

.lm-subtabs { display: flex; gap: 6px; border-bottom: 1px solid var(--border); padding-bottom: 0; }
.lm-subtab {
  background: none; border: none; color: var(--text3); padding: 8px 12px; cursor: pointer;
  font-size: 13px; border-bottom: 2px solid transparent;
}
.lm-subtab.active { color: var(--accent); border-bottom-color: var(--accent); }
.lm-count { font-size: 10px; background: var(--surface2); border-radius: 999px; padding: 0 6px; margin-left: 4px; }

.lm-entries { display: flex; flex-direction: column; gap: 8px; }
.lm-entry { padding: 10px 12px; border-left: 3px solid var(--border-strong); }
.lm-entry-consensus { border-left-color: var(--accent); }
.lm-entry-candidate { border-left-color: #c9a227; }
.lm-entry-competing { border-left-color: #e07a5f; }
.lm-entry-refuted { opacity: 0.72; }
.lm-entry-head { display: flex; align-items: center; gap: 8px; cursor: pointer; flex-wrap: wrap; }
.lm-entry-subject { font-weight: 600; color: var(--text); font-size: 13px; }
.lm-entry-claim { font-size: 11px; color: var(--text3); font-family: ui-monospace, monospace; }
.lm-entry-dirs { display: flex; gap: 4px; flex-wrap: wrap; }
.lm-dir { font-size: 10px; background: var(--surface2); padding: 1px 6px; border-radius: 4px; color: var(--text2); }
.lm-dir.refuted { text-decoration: line-through; color: var(--text-dim); }
.lm-entry-meta { margin-left: auto; font-size: 10px; color: var(--text3); }
.lm-expand { color: var(--text3); font-size: 11px; }
.lm-entry-narrative { font-size: 12px; color: var(--text2); margin-top: 6px; }
.lm-entry-body { margin-top: 8px; border-top: 1px dashed var(--border); padding-top: 8px; }
.lm-entry-section-title { font-size: 11px; color: var(--text3); margin-bottom: 4px; }
.lm-source-row { display: flex; gap: 8px; font-size: 11px; color: var(--text3); padding: 2px 0; align-items: baseline; }
.lm-source-date { flex: 0 0 auto; color: var(--text-dim); }
.lm-source-dir { flex: 0 0 auto; color: var(--accent); }
.lm-source-detail { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.lm-link { background: none; border: none; padding: 0; color: var(--accent); cursor: pointer; font-size: 11px; text-decoration: underline dotted; }
.lm-entry-actions { display: flex; gap: 6px; margin-top: 8px; }
.lm-more-row { display: flex; justify-content: center; padding: 10px 0; }

.lm-badge { font-size: 10px; padding: 1px 7px; border-radius: 999px; border: 1px solid var(--border); color: var(--text2); }
.lm-badge-consensus { color: #14150f; background: var(--accent); border-color: var(--accent); font-weight: 700; }
.lm-badge-candidate { color: #c9a227; border-color: rgba(201, 162, 39, 0.4); }
.lm-badge-competing { color: #e07a5f; border-color: rgba(224, 122, 95, 0.4); }
.lm-badge-singleton { color: var(--text3); }
.lm-badge-refuted { color: var(--text-dim); }
.lm-tier-additive { color: #7fb069; border-color: rgba(127, 176, 105, 0.4); }
.lm-tier-correction { color: #c9a227; border-color: rgba(201, 162, 39, 0.4); }
.lm-tier-removal { color: #e07a5f; border-color: rgba(224, 122, 95, 0.4); }
.lm-status-applied { color: #7fb069; }
.lm-status-pending_approval, .lm-status-pending_corroboration { color: var(--accent); }
.lm-status-rejected, .lm-status-invalid, .lm-status-apply_failed { color: #e07a5f; }

.lm-proposal { padding: 10px 12px; }
.lm-proposal-head { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.lm-proposal-meta { display: flex; gap: 10px; font-size: 11px; color: var(--text3); margin-top: 6px; flex-wrap: wrap; }

.lm-ontology-scene { padding: 12px; }
.lm-ontology-scene-title { font-size: 13px; font-weight: 600; color: var(--text); margin-bottom: 8px; font-family: ui-monospace, monospace; }
.lm-version-row { display: flex; gap: 10px; align-items: center; padding: 4px 0; font-size: 12px; color: var(--text2); border-top: 1px dashed var(--border); }
.lm-version-num { font-weight: 700; color: var(--accent); }
.lm-version-parent { color: var(--text-dim); font-size: 11px; }
.lm-version-quality, .lm-version-mode, .lm-version-date { font-size: 11px; color: var(--text3); }
.lm-version-date { margin-left: auto; }

.lm-empty { padding: 20px; text-align: center; color: var(--text3); font-size: 13px; }
.lm-empty-hint { font-size: 11px; color: var(--text-dim); margin-top: 6px; }
.lm-error { padding: 10px 12px; border: 1px solid rgba(224, 122, 95, 0.4); border-radius: 8px; color: #e07a5f; font-size: 12px; }

.lm-modal-mask { position: fixed; inset: 0; background: rgba(0, 0, 0, 0.55); display: flex; align-items: center; justify-content: center; z-index: 60; }
.lm-modal { width: min(480px, 92vw); padding: 16px; display: flex; flex-direction: column; gap: 10px; }
.lm-modal-title { font-size: 14px; font-weight: 600; color: var(--text); }
.lm-modal textarea { width: 100%; resize: vertical; background: var(--surface-soft); color: var(--text); border: 1px solid var(--border); border-radius: 6px; padding: 8px; font-size: 12px; }
.lm-modal-actions { display: flex; justify-content: flex-end; gap: 8px; }
</style>
