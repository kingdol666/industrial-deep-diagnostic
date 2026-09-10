<template>
  <div class="onto-view">
    <!-- ═══ 工具栏 ═══ -->
    <header class="onto-toolbar">
      <div class="onto-toolbar-left">
        <input
          v-model="search" class="onto-search" type="search"
          :placeholder="$t('ontology.searchPlaceholder')"
        />
        <span class="onto-toolbar-meta">
          {{ $t('ontology.scenes', { n: listing?.scene_count || 0 }) }} ·
          {{ $t('ontology.versions', { n: listing?.version_count || 0 }) }} ·
          {{ $t('ontology.reuseTotal', { n: listing?.assets?.reduce((a, s) => a + s.total_reuse, 0) || 0 }) }}
        </span>
      </div>

      <div class="onto-toolbar-right">
        <button type="button" class="onto-btn" @click="openCreate">{{ $t('ontology.create') }}</button>
        <button type="button" class="onto-btn" @click="openAdopt">{{ $t('ontology.adopt') }}</button>
        <button type="button" class="onto-btn ghost" :title="$t('ontology.refresh')" @click="reloadAll">⟳</button>
      </div>
    </header>

    <div class="onto-alert error" v-if="error">
      <span>{{ error }}</span>
      <button type="button" @click="error = ''">✕</button>
    </div>
    <div class="onto-alert ok" v-if="notice">
      <span>{{ notice }}</span>
      <button type="button" @click="notice = ''">✕</button>
    </div>

    <!-- ═══ 三栏工作区 ═══ -->
    <div class="onto-work">
      <!-- ── 左：资产列表 ── -->
      <aside class="onto-rail">
        <div class="onto-rail-head">
          <span>{{ $t('ontology.assets') }}</span>
          <span class="onto-rail-dir mono" :title="listing?.store_dir">{{ listing?.store_dir }}</span>
        </div>
        <div class="onto-rail-body">
          <p v-if="!filteredAssets.length" class="onto-empty">{{ $t('ontology.noAssets') }}</p>
          <div v-for="s in filteredAssets" :key="s.scene_key" class="onto-scene">
            <button
              type="button" class="onto-scene-head"
              :class="{ active: current?.scene_key === s.scene_key, broken: s.broken }"
              @click="openScene(s.scene_key, s.latest_version)"
            >
              <span class="onto-scene-name">{{ s.title || s.scene_key }}</span>
              <span class="onto-scene-sub mono">{{ s.scene_key }}</span>
              <span class="onto-scene-stats">
                <span class="onto-mini-stat">{{ $t('ontology.version', { version: s.latest_version }) }}</span>
                <span v-if="s.version_count > 1" class="onto-mini-stat">×{{ s.version_count }}</span>
                <span v-if="s.total_reuse" class="onto-mini-stat reuse">↻{{ s.total_reuse }}</span>
                <span v-if="s.broken" class="onto-mini-stat bad">!</span>
              </span>
              <span v-if="s.summary" class="onto-scene-summary">
                {{ $t('ontology.signalCount', { n: s.summary.signals }) }} · {{ $t('ontology.relCount', { n: s.summary.relationships }) }}
                <template v-if="s.summary.process_type"> · {{ shortProcess(s.summary.process_type) }}</template>
              </span>
              <span v-if="s.tags?.length" class="onto-scene-tags">
                <span v-for="tg in s.tags" :key="tg" class="onto-tag">{{ tg }}</span>
              </span>
            </button>
            <div v-if="current?.scene_key === s.scene_key" class="onto-version-list">
              <button
                v-for="v in s.versions" :key="`${s.scene_key}-${v.version}`"
                type="button" class="onto-version-item"
                :class="{ active: current?.version === v.version, broken: !v.present }"
                @click="openScene(s.scene_key, v.version)"
              >
                <span class="mono">v{{ v.version }}</span>
                <span class="onto-version-mode">{{ v.build_mode }}</span>
                <span class="onto-version-q" :class="`q-${v.quality}`">{{ qualityLabel(v.quality) }}</span>
                <span class="onto-version-origin">{{ v.origin.startsWith('user') ? '👤' : '🤖' }}</span>
                <span v-if="v.version === s.latest_version" class="onto-version-latest">{{ $t('ontology.latest') }}</span>
              </button>
            </div>
          </div>
        </div>
      </aside>

      <!-- ── 中：工作区 ── -->
      <main class="onto-main">
        <p v-if="!current" class="onto-placeholder">{{ $t('ontology.noSelection') }}</p>

        <template v-else>
          <div class="onto-main-head">
            <div class="onto-main-title">
              <h2 class="mono">{{ current.scene_key }} <span class="onto-vtag">v{{ current.version }}</span></h2>
              <span class="onto-write-target mono" :title="$t('ontology.path')">
                ✎ {{ current.absolute_path }}
              </span>
            </div>
            <div class="onto-main-actions">
              <span v-if="dirty" class="onto-dirty">{{ $t('ontology.dirty') }}</span>
              <span v-else class="onto-clean">✓ {{ $t('ontology.saved') }}</span>
              <!-- 注意：`:disabled="busy"` 在 busy==='' 时会渲染 disabled=""，
                   Vue 的 includeBooleanAttr 把空串视为 true → 按钮永久禁用。
                   必须显式转成布尔。 -->
              <button type="button" class="onto-btn" :disabled="!!busy" @click="doValidate">
                {{ busy === 'validate' ? $t('ontology.validating') : $t('ontology.validate') }}
              </button>
              <button type="button" class="onto-btn ghost" :disabled="!dirty" @click="revert">{{ $t('ontology.revert') }}</button>
              <button
                type="button" class="onto-btn primary"
                :disabled="busy === 'save' || !current"
                :title="$t('ontology.saveHint', { next: nextVersion })"
                @click="doSave"
              >
                {{ $t('ontology.save') }}
              </button>
            </div>
          </div>

          <!-- 校验结果条（错误汇总 + 定位） -->
          <div v-if="validation && !validation.ok" class="onto-errors">
            <div class="onto-errors-head">
              <span>{{ $t('ontology.errorsCount', { n: validation.errors.length }) }}</span>
              <span class="mono dim">{{ $t('ontology.validateFail', { n: validation.errors.length }) }}</span>
            </div>
            <ul class="onto-errors-list">
              <li v-for="(e, i) in validation.errors.slice(0, 8)" :key="`ve-${i}`">
                <code class="mono">{{ e.path }}</code>
                <span>{{ e.message }}</span>
                <button
                  v-if="pointerToPath(e.path)" type="button" class="onto-link"
                  @click="jumpTo(e.path)"
                >{{ $t('ontology.jumpToField') }}</button>
              </li>
            </ul>
          </div>
          <div v-else-if="validation && validation.ok" class="onto-ok-strip">
            ✓ {{ $t('ontology.validateOk') }} · {{ validation.bytes }} B
          </div>

          <!-- 视图切换 -->
          <nav class="onto-tabs">
            <button
              v-for="v in views" :key="v.key" type="button"
              class="onto-tab" :class="{ active: view === v.key }"
              @click="view = v.key"
            >{{ $t(v.label) }}</button>
          </nav>

          <div class="onto-view-body" :class="{ 'no-scroll': view === 'graph' }">
            <!-- 图视图 -->
            <div v-if="view === 'graph'" class="onto-graph-host">
              <OntologyGraph
                :graph="graphFiltered"
                :layers="layers"
                :selected-id="selection?.data?.id || ''"
                :empty-text="$t('ontology.graph.empty')"
                @update:layers="onLayers"
                @select="onSelect"
              />
              <div class="onto-filters" v-if="graph?.nodes?.length">
                <span class="onto-filters-title">{{ $t('ontology.graph.filters') }}</span>
                <label class="onto-filter">
                  <span>{{ $t('ontology.graph.filterConfidence') }}</span>
                  <select v-model="filterConfidence">
                    <option value="all">{{ $t('ontology.graph.filterNone') }}</option>
                    <option value="KNOWN">KNOWN</option>
                    <option value="INFERRED">INFERRED</option>
                    <option value="UNKNOWN">UNKNOWN</option>
                  </select>
                </label>
                <label class="onto-filter">
                  <span>{{ $t('ontology.graph.filterBehavior') }}</span>
                  <select v-model="filterBehavior">
                    <option value="all">{{ $t('ontology.graph.filterNone') }}</option>
                    <option value="CONSISTENT">CONSISTENT</option>
                    <option value="CONTRADICTED">CONTRADICTED</option>
                    <option value="UNVERIFIED">UNVERIFIED</option>
                  </select>
                </label>
                <label class="onto-filter">
                  <span>{{ $t('ontology.graph.filterKnowledge') }}</span>
                  <select v-model="filterSource">
                    <option value="all">{{ $t('ontology.graph.filterNone') }}</option>
                    <option v-for="k in knowledgeSources" :key="k" :value="k">{{ k }}</option>
                  </select>
                </label>
                <span v-if="hiddenByFilter" class="onto-filter-note">
                  {{ $t('ontology.graph.filtered', { n: hiddenByFilter }) }}
                </span>
              </div>
            </div>

            <!-- 结构编辑 -->
            <OntologyEditor
              v-else-if="view === 'structure'"
              :ontology="draft"
              @update:ontology="onDraft"
            />

            <!-- JSON -->
            <div v-else-if="view === 'json'" class="onto-json-host">
              <p class="onto-hint">{{ $t('ontology.editor.jsonHint') }}</p>
              <textarea
                class="onto-json mono" :value="jsonText"
                spellcheck="false" @input="onJsonInput"
              ></textarea>
            </div>

            <!-- 模型健康 -->
            <div v-else-if="view === 'metrics'" class="onto-metrics">
              <template v-if="metrics?.available">
                <div class="onto-metrics-hero">
                  <div class="onto-health-score">
                    <span class="onto-health-num">{{ metrics.health.score }}</span>
                    <span class="onto-health-grade" :class="`grade-${metrics.health.grade}`">{{ metrics.health.grade }}</span>
                  </div>
                  <div class="onto-breakdown">
                    <div v-for="b in metrics.health.breakdown" :key="b.key" class="onto-breakdown-row">
                      <span class="onto-breakdown-label mono">{{ b.key }}</span>
                      <span class="onto-breakdown-bar">
                        <span class="onto-breakdown-fill" :style="{ width: `${b.value * 100}%` }"></span>
                      </span>
                      <span class="onto-breakdown-pts mono">{{ b.points }}/{{ b.weight }}</span>
                    </div>
                  </div>
                </div>

                <div class="onto-metric-grid">
                  <section class="onto-metric-card">
                    <h5>{{ $t('ontology.metricsSemantic') }}</h5>
                    <dl class="onto-dl compact">
                      <div><dt>{{ $t('ontology.known') }}</dt><dd class="mono">{{ metrics.semantic_coverage.known }}</dd></div>
                      <div><dt>{{ $t('ontology.inferred') }}</dt><dd class="mono">{{ metrics.semantic_coverage.inferred }}</dd></div>
                      <div><dt>{{ $t('ontology.unknown') }}</dt><dd class="mono">{{ metrics.semantic_coverage.unknown }}</dd></div>
                      <div><dt>{{ $t('ontology.described') }}</dt><dd class="mono">{{ pct(metrics.semantic_coverage.described_ratio) }}</dd></div>
                      <div><dt>{{ $t('ontology.withUnit') }}</dt><dd class="mono">{{ pct(metrics.semantic_coverage.unit_ratio) }}</dd></div>
                      <div><dt>{{ $t('ontology.withRange') }}</dt><dd class="mono">{{ pct(metrics.semantic_coverage.range_ratio) }}</dd></div>
                      <div><dt>{{ $t('ontology.withGoverningLaw') }}</dt><dd class="mono">{{ pct(metrics.semantic_coverage.governing_law_ratio) }}</dd></div>
                    </dl>
                  </section>

                  <section class="onto-metric-card">
                    <h5>{{ $t('ontology.metricsRelationship') }}</h5>
                    <dl class="onto-dl compact">
                      <div><dt>{{ $t('ontology.editor.relationships') }}</dt><dd class="mono">{{ metrics.relationship_quality.total }}</dd></div>
                      <div><dt>{{ $t('ontology.withMechanism') }}</dt><dd class="mono">{{ pct(metrics.relationship_quality.mechanism_ratio) }}</dd></div>
                      <div><dt>{{ $t('ontology.withEquation') }}</dt><dd class="mono">{{ pct(metrics.relationship_quality.equation_ratio) }}</dd></div>
                      <div><dt>{{ $t('ontology.dataValidated') }}</dt><dd class="mono">{{ pct(metrics.relationship_quality.data_validated_ratio) }}</dd></div>
                      <div><dt>{{ $t('ontology.lagDocumented') }}</dt><dd class="mono">{{ pct(metrics.relationship_quality.lag_documented_ratio) }}</dd></div>
                      <div><dt>{{ $t('ontology.density') }}</dt><dd class="mono">{{ metrics.relationship_quality.density ?? '—' }}</dd></div>
                    </dl>
                  </section>

                  <section class="onto-metric-card">
                    <h5>{{ $t('ontology.metricsConsistency') }}</h5>
                    <dl class="onto-dl compact">
                      <div><dt>CONSISTENT</dt><dd class="mono good">{{ metrics.consistency.behavior.CONSISTENT }}</dd></div>
                      <div><dt>CONTRADICTED</dt><dd class="mono bad">{{ metrics.consistency.behavior.CONTRADICTED }}</dd></div>
                      <div><dt>UNVERIFIED</dt><dd class="mono">{{ metrics.consistency.behavior.UNVERIFIED }}</dd></div>
                      <div><dt>{{ $t('ontology.dangling') }}</dt><dd class="mono" :class="{ bad: metrics.consistency.dangling_relationships }">{{ metrics.consistency.dangling_relationships }}</dd></div>
                      <div><dt>{{ $t('ontology.orphanSignals') }}</dt><dd class="mono" :class="{ warn: metrics.consistency.orphan_signals }">{{ metrics.consistency.orphan_signals }}</dd></div>
                      <div><dt>{{ $t('ontology.duplicateColumns') }}</dt><dd class="mono" :class="{ bad: metrics.consistency.duplicate_columns.length }">{{ metrics.consistency.duplicate_columns.length }}</dd></div>
                    </dl>
                  </section>

                  <section class="onto-metric-card">
                    <h5>{{ $t('ontology.metricsTopology') }}</h5>
                    <dl class="onto-dl compact">
                      <div><dt>{{ $t('ontology.causalCycles') }}</dt>
                        <dd class="mono" :class="{ bad: metrics.topology.causal_cycle_count }">{{ metrics.topology.causal_cycle_count }}</dd></div>
                      <div><dt>mean degree</dt><dd class="mono">{{ metrics.topology.mean_degree }}</dd></div>
                      <div><dt>degree σ</dt><dd class="mono">{{ metrics.topology.degree_sd }}</dd></div>
                      <div><dt>{{ $t('ontology.degreeOutliers') }}</dt>
                        <dd class="mono" :class="{ warn: metrics.topology.degree_outliers.length }">{{ metrics.topology.degree_outliers.length }}</dd></div>
                      <div><dt>{{ $t('ontology.contradictionClusters') }}</dt>
                        <dd class="mono" :class="{ warn: metrics.topology.contradiction_clusters.length }">{{ metrics.topology.contradiction_clusters.length }}</dd></div>
                      <div><dt>attribute richness</dt><dd class="mono">{{ metrics.topology.attribute_richness ?? '—' }}</dd></div>
                    </dl>
                  </section>
                </div>

                <section class="onto-findings-full">
                  <h5>{{ $t('ontology.errorsTitle') }} ({{ metrics.findings.length }})</h5>
                  <p v-if="!metrics.findings.length" class="onto-empty">{{ $t('ontology.noErrors') }}</p>
                  <div
                    v-for="(f, i) in metrics.findings" :key="`mf-${i}`"
                    class="onto-finding" :class="`sev-${f.severity}`"
                  >
                    <span class="onto-finding-sev">{{ severityLabel(f.severity) }}</span>
                    <span class="onto-finding-code mono">{{ f.code }}</span>
                    <span class="onto-finding-rule mono dim">{{ findingRule(f) }}</span>
                    <p class="onto-finding-msg">{{ findingText(f) }}</p>
                    <p v-if="f.focusNode" class="onto-finding-hint mono">{{ $t('ontology.findingFocus') }}: {{ f.focusNode }}
                      <span v-if="f.pointer" class="dim"> ({{ f.pointer }})</span></p>
                    <p v-if="f.hint" class="onto-finding-hint">{{ f.hint }}</p>
                    <p v-if="f.justification?.length" class="onto-finding-hint dim">
                      {{ $t('ontology.findingJustification') }}: {{ f.justification.join(' · ') }}
                    </p>
                  </div>
                </section>
              </template>
              <p v-else class="onto-empty">{{ metrics?.reason || $t('ontology.noErrors') }}</p>
            </div>

            <!-- 版本差异 -->
            <OntologyDiff
              v-else-if="view === 'diff'"
              :diff="diff"
              :versions="currentSceneVersions"
              :from-version="diffFrom"
              :to-version="diffTo"
              @update:from-version="onDiffFrom"
              @update:to-version="onDiffTo"
            />

            <!-- 基本面 -->
            <div v-else class="onto-info">
              <section class="onto-metric-card">
                <h5>{{ $t('ontology.editMeta') }}</h5>
                <div class="onto-field-grid">
                  <label class="onto-field"><span>{{ $t('ontology.title') }}</span>
                    <input v-model="metaTitle" @change="saveMeta" /></label>
                  <label class="onto-field"><span>{{ $t('ontology.tags') }}</span>
                    <input v-model="metaTags" :placeholder="$t('ontology.tagsHint')" @change="saveMeta" /></label>
                  <label class="onto-field wide"><span>{{ $t('ontology.notes') }}</span>
                    <textarea rows="2" v-model="metaNotes" @change="saveMeta"></textarea></label>
                </div>
              </section>

              <section class="onto-metric-card">
                <h5>{{ $t('ontology.provenance') }}</h5>
                <pre class="onto-pre mono">{{ JSON.stringify(provenance, null, 2) }}</pre>
              </section>

              <section class="onto-metric-card danger-zone">
                <h5>{{ $t('ontology.quality') }}</h5>
                <div class="onto-danger-row">
                  <button type="button" class="onto-btn" :title="$t('ontology.deprecateHint')" @click="setQuality('deprecated')">
                    {{ $t('ontology.deprecate') }}
                  </button>
                  <button type="button" class="onto-btn" @click="setQuality('endorsed')">{{ $t('ontology.qualityEndorsed') }}</button>
                  <button type="button" class="onto-btn" @click="setQuality('unvalidated')">{{ $t('ontology.qualityUnvalidated') }}</button>
                </div>
                <div class="onto-danger-row">
                  <button type="button" class="onto-btn danger" @click="doDeleteVersion">{{ $t('ontology.deleteVersion') }}</button>
                  <button type="button" class="onto-btn danger" @click="doDeleteScene">{{ $t('ontology.deleteScene') }}</button>
                </div>
                <div class="onto-danger-row">
                  <input v-model="cloneTarget" class="onto-input" :placeholder="$t('ontology.cloneTarget')" />
                  <button type="button" class="onto-btn" @click="doClone">{{ $t('ontology.cloneSubmit') }}</button>
                </div>
              </section>
            </div>
          </div>
        </template>
      </main>

      <!-- ── 右：检视面板 ── -->
      <aside class="onto-inspector-host">
        <OntologyInspector
          :asset="current"
          :graph="graph"
          :metrics="metrics"
          :etag="etag"
          :selection="selection"
          @select="onSelect"
          @clear="selection = null"
        />
      </aside>
    </div>

    <!-- ═══ 冲突对话框 ═══ -->
    <div v-if="conflict" class="onto-modal-backdrop" @click.self="conflict = null">
      <div class="onto-modal">
        <h3>{{ $t('ontology.conflictTitle') }}</h3>
        <p>{{ conflict }}</p>
        <div class="onto-modal-actions">
          <button type="button" class="onto-btn primary" @click="reloadCurrent">{{ $t('ontology.conflictReload') }}</button>
          <button type="button" class="onto-btn danger" @click="forceSave">{{ $t('ontology.conflictForce') }}</button>
          <button type="button" class="onto-btn ghost" @click="conflict = null">{{ $t('ontology.cancel') }}</button>
        </div>
      </div>
    </div>

    <!-- ═══ 新建对话框 ═══ -->
    <div v-if="createOpen" class="onto-modal-backdrop" @click.self="createOpen = false">
      <div class="onto-modal">
        <h3>{{ $t('ontology.createTitle') }}</h3>
        <label class="onto-field">
          <span>{{ $t('ontology.createSceneKey') }}</span>
          <input v-model="createScene" class="mono" placeholder="my_scene_key" />
        </label>
        <p class="onto-hint">{{ $t('ontology.createSceneKeyHint') }}</p>
        <label class="onto-field">
          <span>{{ $t('ontology.createProcessType') }}</span>
          <input v-model="createProcess" />
        </label>
        <label class="onto-field">
          <span>{{ $t('ontology.createObjective') }}</span>
          <input v-model="createObjective" />
        </label>
        <div class="onto-modal-actions">
          <button type="button" class="onto-btn primary" :disabled="!validSceneKey" @click="doCreate">
            {{ $t('ontology.createSubmit') }}
          </button>
          <button type="button" class="onto-btn ghost" @click="createOpen = false">{{ $t('ontology.cancel') }}</button>
        </div>
      </div>
    </div>

    <!-- ═══ 采纳对话框 ═══ -->
    <div v-if="adoptOpen" class="onto-modal-backdrop wide" @click.self="adoptOpen = false">
      <div class="onto-modal wide">
        <h3>{{ $t('ontology.adoptTitle') }}</h3>
        <p class="onto-hint">{{ $t('ontology.adoptHint') }}</p>
        <div class="onto-adopt-bar">
          <span class="mono dim">{{ candidates?.runs_dir }}</span>
          <button
            type="button" class="onto-btn"
            :disabled="!adoptableCandidates.length || busy === 'adoptAll'"
            @click="adoptAll"
          >{{ $t('ontology.adoptAll') }} ({{ adoptableCandidates.length }})</button>
        </div>
        <div class="onto-adopt-list">
          <div v-for="c in candidates?.candidates || []" :key="c.run_name" class="onto-adopt-row">
            <div class="onto-adopt-main">
              <span class="onto-adopt-name">{{ c.display_name }}</span>
              <span class="onto-adopt-sub mono">{{ c.run_name }}</span>
              <span class="onto-adopt-scene mono">→ {{ c.proposed_scene }}</span>
              <span v-if="c.summary" class="onto-adopt-stats">
                {{ $t('ontology.signalCount', { n: c.summary.signals }) }} · {{ $t('ontology.relCount', { n: c.summary.relationships }) }}
              </span>
              <span v-if="c.in_store" class="onto-adopt-badge ok">
                {{ $t('ontology.adopted') }} v{{ c.in_store.version }}
              </span>
              <span v-else-if="c.parse_error" class="onto-adopt-badge bad">JSON ✗</span>
              <span v-else-if="c.validation && !c.validation.ok" class="onto-adopt-badge warn">
                CP-2 ✗ ({{ c.validation.errors.length }})
              </span>
              <span v-else class="onto-adopt-badge">CP-2 ✓</span>
            </div>
            <button
              type="button" class="onto-btn" :disabled="!c.adoptable || busy === `adopt:${c.run_name}`"
              @click="adoptOne(c)"
            >{{ c.adoptable ? $t('ontology.adoptAction') : $t('ontology.adoptNoNeed') }}</button>
          </div>
          <p v-if="!(candidates?.candidates || []).length" class="onto-empty">{{ $t('ontology.adoptEmpty') }}</p>
        </div>
        <div class="onto-modal-actions">
          <button type="button" class="onto-btn ghost" @click="adoptOpen = false">{{ $t('ontology.cancel') }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { api, ApiError } from '../../api/index.js';
import OntologyGraph from './OntologyGraph.vue';
import OntologyEditor from './OntologyEditor.vue';
import OntologyInspector from './OntologyInspector.vue';
import OntologyDiff from './OntologyDiff.vue';

const { t } = useI18n();

const KNOWLEDGE_SOURCES = ['rag_retrieval', 'reference_doc', 'web_research', 'auto_inferred', 'user_provided'];

const views = [
  { key: 'graph', label: 'ontology.viewGraph' },
  { key: 'structure', label: 'ontology.viewStructure' },
  { key: 'json', label: 'ontology.viewJson' },
  { key: 'metrics', label: 'ontology.viewMetrics' },
  { key: 'diff', label: 'ontology.viewDiff' },
  { key: 'info', label: 'ontology.viewInfo' },
];

const listing = ref(null);
const current = ref(null);          // 服务端加载的资产（含 entry / validation / ontology）
const draft = ref(null);            // 本地工作副本
const metrics = ref(null);
const graph = ref(null);
const validation = ref(null);
const provenance = ref(null);
const etag = ref('');
const selection = ref(null);
const view = ref('graph');
const layers = ref({ structure: true, relationships: true, knowledge: false });
const search = ref('');
const error = ref('');
const notice = ref('');
const busy = ref('');
const conflict = ref('');
const dirty = ref(false);

const metaTitle = ref('');
const metaTags = ref('');
const metaNotes = ref('');
const cloneTarget = ref('');

const createOpen = ref(false);
const createScene = ref('');
const createProcess = ref('');
const createObjective = ref('');

const adoptOpen = ref(false);
const candidates = ref(null);

const diff = ref(null);
const diffFrom = ref(1);
const diffTo = ref(1);

const filterConfidence = ref('all');
const filterBehavior = ref('all');
const filterSource = ref('all');

const jsonText = ref('');
let jsonError = false;

const knowledgeSources = KNOWLEDGE_SOURCES;

// ─── 派生 ───

const filteredAssets = computed(() => {
  const assets = listing.value?.assets || [];
  const q = search.value.trim().toLowerCase();
  if (!q) return assets;
  return assets.filter((s) =>
    s.scene_key.toLowerCase().includes(q)
    || (s.title || '').toLowerCase().includes(q)
    || s.tags.some((x) => x.toLowerCase().includes(q))
    || (s.summary?.process_type || '').toLowerCase().includes(q));
});

const nextVersion = computed(() => (current.value?.version ?? 0) + 1);

const currentSceneVersions = computed(() => {
  const s = (listing.value?.assets || []).find((a) => a.scene_key === current.value?.scene_key);
  return (s?.versions || []).map((v) => v.version).sort((a, b) => a - b);
});

const validSceneKey = computed(() => /^[A-Za-z0-9._-]{3,64}$/.test(createScene.value.trim()));

const adoptableCandidates = computed(() =>
  (candidates.value?.candidates || []).filter((c) => c.adoptable));

/** 客户端过滤图：语义置信度 / 行为一致性 / 知识来源（研究结论：专家第一问是"哪些是测的、哪些是推断的"）。 */
const graphFiltered = computed(() => {
  if (!graph.value?.nodes) return graph.value;
  const keep = new Set();
  for (const n of graph.value.nodes) {
    const d = n.detail || {};
    if (filterConfidence.value !== 'all' && (d.confidence || 'UNKNOWN') !== filterConfidence.value) continue;
    if (filterBehavior.value !== 'all' && (d.behavior_match || 'UNVERIFIED') !== filterBehavior.value) continue;
    if (filterSource.value !== 'all' && n.kind === 'signal' && (d.knowledge_source || '') !== filterSource.value) continue;
    keep.add(n.id);
  }
  // 非信号节点（设备/阶段/知识）在按信号属性过滤时也应保留 —— 否则骨架会消失
  for (const n of graph.value.nodes) if (n.kind !== 'signal') keep.add(n.id);
  return {
    ...graph.value,
    nodes: graph.value.nodes.filter((n) => keep.has(n.id)),
    edges: graph.value.edges.filter((e) => keep.has(e.source) && keep.has(e.target)),
  };
});

const hiddenByFilter = computed(() => {
  if (!graph.value?.nodes) return 0;
  const shown = new Set((graphFiltered.value?.nodes || []).map((n) => n.id));
  return graph.value.nodes.filter((n) => n.kind === 'signal' && !shown.has(n.id)).length;
});

// ─── 数据加载 ───

async function reloadAll() {
  try {
    listing.value = await api.ontologyAssets();
  } catch (e) {
    error.value = `${t('ontology.error.load')}: ${e.message}`;
  }
}

async function openScene(sceneKey, version) {
  if (dirty.value && !window.confirm(t('ontology.revertConfirm'))) return;
  busy.value = 'load';
  error.value = '';
  try {
    const asset = await api.ontologyAsset(sceneKey, version);
    current.value = asset;
    draft.value = JSON.parse(JSON.stringify(asset.ontology));
    metrics.value = asset.metrics;
    graph.value = asset.graph;
    validation.value = asset.validation;
    etag.value = asset.etag || asset.entry?.content_sha256 || '';
    selection.value = null;
    dirty.value = false;
    jsonError = false;
    jsonText.value = JSON.stringify(asset.ontology, null, 2);
    metaTitle.value = asset.entry?.title || sceneKey;
    metaTags.value = (asset.entry?.tags || []).join(', ');
    metaNotes.value = asset.entry?.notes || '';
    cloneTarget.value = '';
    try {
      const p = await api.ontologyProvenance(sceneKey, version);
      provenance.value = p.provenance;
    } catch { provenance.value = null; }
    if (view.value === 'diff') await loadDiff();
  } catch (e) {
    error.value = `${t('ontology.error.load')}: ${e.message}`;
  } finally {
    busy.value = '';
  }
}

function reloadCurrent() {
  conflict.value = '';
  if (current.value) openScene(current.value.scene_key, current.value.version);
}

// ─── 草稿变更（唯一的 draft 真相；图/度量在本地即时重投影） ───

let reprojectTimer = null;
function onDraft(next) {
  draft.value = next;
  dirty.value = true;
  jsonText.value = JSON.stringify(next, null, 2);
  scheduleReproject();
}

function scheduleReproject() {
  if (reprojectTimer) clearTimeout(reprojectTimer);
  reprojectTimer = setTimeout(reproject, 320);
}

async function reproject() {
  if (!draft.value) return;
  try {
    const [g, m, v] = await Promise.all([
      api.ontologyProjectGraph(draft.value, layers.value),
      api.ontologyProjectMetrics(draft.value),
      api.ontologyValidate(draft.value),
    ]);
    graph.value = g.graph;
    metrics.value = m.metrics;
    validation.value = v;
  } catch (e) {
    // 投影失败不阻断编辑，只提示
    error.value = e.message;
  }
}

function onJsonInput(ev) {
  const text = ev.target.value;
  jsonText.value = text;
  try {
    const parsed = JSON.parse(text);
    jsonError = false;
    draft.value = parsed;
    dirty.value = true;
    scheduleReproject();
  } catch (e) {
    jsonError = true;
    error.value = `${t('ontology.editor.jsonInvalid')}: ${e.message}`;
  }
}

function onLayers(next) {
  layers.value = next;
  reproject();
}

function revert() {
  if (!window.confirm(t('ontology.revertConfirm'))) return;
  if (current.value) {
    draft.value = JSON.parse(JSON.stringify(current.value.ontology));
    graph.value = current.value.graph;
    metrics.value = current.value.metrics;
    validation.value = current.value.validation;
    jsonText.value = JSON.stringify(current.value.ontology, null, 2);
    dirty.value = false;
    error.value = '';
  }
}

// ─── 保存 / 校验 ───

async function doValidate() {
  busy.value = 'validate';
  error.value = '';
  try {
    const res = await api.ontologyValidate(draft.value);
    validation.value = res;
    metrics.value = res.metrics || metrics.value;
    notice.value = res.ok
      ? t('ontology.validateOk')
      : t('ontology.validateFail', { n: res.errors.length });
  } catch (e) {
    error.value = e.message;
  } finally {
    busy.value = '';
  }
}

async function doSave(force = false) {
  if (!current.value) return;
  if (jsonError) {
    error.value = t('ontology.editor.jsonInvalid');
    return;
  }
  busy.value = 'save';
  error.value = '';
  try {
    const res = await api.ontologySave(current.value.scene_key, current.value.version, {
      ontology: draft.value,
      expected_sha256: etag.value,
      force,
      tags: metaTags.value.split(',').map((s) => s.trim()).filter(Boolean),
      notes: metaNotes.value,
      title: metaTitle.value,
    });
    conflict.value = '';
    notice.value = res.deduped
      ? t('ontology.saved')
      : `${t('ontology.saved')} → v${res.version}`;
    await reloadAll();
    await openScene(current.value.scene_key, res.deduped ? current.value.version : res.version);
  } catch (e) {
    handleSaveError(e);
  } finally {
    busy.value = '';
  }
}

function handleSaveError(e) {
  if (!(e instanceof ApiError)) { error.value = e.message; return; }
  if (e.code === 'VERSION_CONFLICT') {
    conflict.value = t('ontology.conflictVersion', {
      base: e.details?.base_version ?? current.value?.version,
      latest: e.details?.latest_version ?? '?',
    });
  } else if (e.code === 'CONTENT_CHANGED') {
    conflict.value = t('ontology.conflictContent');
  } else if (e.code === 'PRECONDITION_REQUIRED') {
    conflict.value = t('ontology.conflictPrecondition');
    if (e.details?.current_sha256) etag.value = e.details.current_sha256;
  } else if (e.code === 'VALIDATION_FAILED') {
    validation.value = { ok: false, errors: e.details?.errors || [], warnings: e.details?.warnings || [], bytes: e.details?.bytes || 0 };
    error.value = t('ontology.validateFail', { n: (e.details?.errors || []).length });
  } else {
    error.value = `${t('ontology.error.save')}: ${e.message}`;
  }
}

async function forceSave() {
  if (!window.confirm(t('ontology.forceConfirm'))) return;
  conflict.value = '';
  await doSave(true);
}

async function saveMeta() {
  if (!current.value) return;
  try {
    await api.ontologyPatch(current.value.scene_key, current.value.version, {
      title: metaTitle.value,
      tags: metaTags.value.split(',').map((s) => s.trim()).filter(Boolean),
      notes: metaNotes.value,
    });
    await reloadAll();
  } catch (e) {
    error.value = e.message;
  }
}

async function setQuality(quality) {
  if (!current.value) return;
  try {
    await api.ontologyPatch(current.value.scene_key, current.value.version, { quality });
    await openScene(current.value.scene_key, current.value.version);
    await reloadAll();
  } catch (e) {
    error.value = e.message;
  }
}

async function doDeleteVersion() {
  if (!current.value || !window.confirm(t('ontology.deleteConfirm'))) return;
  try {
    await api.ontologyDeleteVersion(current.value.scene_key, current.value.version);
    current.value = null; draft.value = null;
    await reloadAll();
    notice.value = t('ontology.saved');
  } catch (e) {
    error.value = `${t('ontology.error.delete')}: ${e.message}`;
  }
}

async function doDeleteScene() {
  if (!current.value || !window.confirm(t('ontology.deleteConfirm'))) return;
  try {
    await api.ontologyDeleteScene(current.value.scene_key);
    current.value = null; draft.value = null;
    await reloadAll();
  } catch (e) {
    error.value = `${t('ontology.error.delete')}: ${e.message}`;
  }
}

async function doClone() {
  if (!current.value || !cloneTarget.value.trim()) return;
  try {
    const res = await api.ontologyClone(current.value.scene_key, current.value.version, {
      target_scene: cloneTarget.value.trim(),
    });
    await reloadAll();
    await openScene(res.scene_key, res.version);
  } catch (e) {
    error.value = e.message;
  }
}

// ─── 新建 / 采纳 ───

function openCreate() {
  createScene.value = '';
  createProcess.value = '';
  createObjective.value = '';
  createOpen.value = true;
}

async function doCreate() {
  if (!validSceneKey.value) { error.value = t('ontology.error.invalidSceneKey'); return; }
  busy.value = 'create';
  try {
    const res = await api.ontologyCreate({
      scene_key: createScene.value.trim(),
      process_type: createProcess.value.trim(),
      objectives: createObjective.value.trim() ? [createObjective.value.trim()] : [],
      title: createScene.value.trim(),
    });
    createOpen.value = false;
    await reloadAll();
    await openScene(res.scene_key, res.version);
  } catch (e) {
    error.value = e.message;
  } finally {
    busy.value = '';
  }
}

async function openAdopt() {
  adoptOpen.value = true;
  try { candidates.value = await api.ontologyCandidates(); } catch (e) { error.value = e.message; }
}

async function adoptOne(c) {
  busy.value = `adopt:${c.run_name}`;
  try {
    await api.ontologyAdopt({ runDir: c.run_dir, runName: c.run_name, scene: c.proposed_scene });
    candidates.value = await api.ontologyCandidates();
    await reloadAll();
  } catch (e) {
    error.value = `${t('ontology.error.adopt')}: ${e.message}`;
  } finally {
    busy.value = '';
  }
}

async function adoptAll() {
  const list = adoptableCandidates.value;
  if (!list.length) return;
  if (!window.confirm(t('ontology.adoptAllConfirm', { n: list.length }))) return;
  busy.value = 'adoptAll';
  let ok = 0;
  for (const c of list) {
    try {
      await api.ontologyAdopt({ runDir: c.run_dir, runName: c.run_name, scene: c.proposed_scene });
      ok++;
    } catch { /* 单个失败不阻断其余 */ }
  }
  busy.value = '';
  notice.value = t('ontology.adoptResult', { n: ok });
  candidates.value = await api.ontologyCandidates();
  await reloadAll();
}

// ─── 差异 ───

async function loadDiff() {
  if (!current.value) return;
  const versions = currentSceneVersions.value;
  if (versions.length < 2) { diff.value = null; return; }
  const to = diffTo.value && versions.includes(diffTo.value) ? diffTo.value : current.value.version;
  const from = diffFrom.value && versions.includes(diffFrom.value) && diffFrom.value !== to
    ? diffFrom.value : versions.filter((v) => v !== to).slice(-1)[0];
  diffFrom.value = from;
  diffTo.value = to;
  try {
    const res = await api.ontologyDiffVersions(current.value.scene_key, from, to);
    diff.value = res.diff;
  } catch (e) {
    error.value = e.message;
  }
}

function onDiffFrom(v) { diffFrom.value = v; loadDiff(); }
function onDiffTo(v) { diffTo.value = v; loadDiff(); }

// ─── 交互 ───

function onSelect(sel) { selection.value = sel; }

function jumpTo(path) {
  const seg = pointerToPath(path);
  if (seg) {
    view.value = 'structure';
    notice.value = `${t('ontology.jumpToField')}: ${seg}`;
  }
}

/** `$.signals.process_parameters[0].unit` → `signals › process_parameters[0] › unit`（面包屑可读化） */
function pointerToPath(path) {
  if (!path || !path.startsWith('$')) return '';
  return path.slice(1).replace(/^\./, '').replace(/\./g, ' › ');
}

function pct(v) { return v === null || v === undefined ? '—' : `${Math.round(v * 100)}%`; }
function severityLabel(s) {
  return { critical: t('ontology.severityCritical'), important: t('ontology.severityImportant'), minor: t('ontology.severityMinor') }[s] || s;
}
function qualityLabel(q) {
  return {
    endorsed: t('ontology.qualityEndorsed'), rejected: t('ontology.qualityRejected'),
    deprecated: t('ontology.qualityDeprecated'), unvalidated: t('ontology.qualityUnvalidated'),
  }[q] || q;
}
function shortProcess(p) {
  const s = String(p || '');
  return s.length > 34 ? `${s.slice(0, 33)}…` : s;
}

watch(view, (v) => { if (v === 'diff') loadDiff(); });
watch([filterConfidence, filterBehavior, filterSource], () => { /* computed 自动生效 */ });
watch(draft, () => { /* 由 onDraft/onJsonInput 显式设置 dirty */ }, { deep: false });

onMounted(async () => {
  await reloadAll();
  const first = listing.value?.assets?.[0];
  if (first) await openScene(first.scene_key, first.latest_version);
});
/**
 * Server findings carry a stable `code` plus structured fields; the human
 * sentence is rendered client-side so it follows the active locale. The
 * server text is the fallback for codes this build does not know yet.
 */
function findingText(f) {
  const key = `ontology.findingCode.${f.code}`;
  const localised = t(key);
  return localised === key ? f.message : localised;
}

function findingRule(f) {
  const key = `ontology.findingRule.${f.sourceRule}`;
  const localised = t(key);
  return localised === key ? f.sourceRule : localised;
}
</script>

<style scoped>
.onto-view {
  display: flex;
  flex-direction: column;
  gap: 10px;
  height: 100%;
  min-height: 0;
}

/* ── 工具栏 ── */
.onto-toolbar {
  display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
  padding: 8px 10px; border: 1px solid var(--border); border-radius: var(--radius);
  background: var(--surface);
}
.onto-toolbar-left { display: flex; align-items: center; gap: 12px; flex: 1; min-width: 240px; }
.onto-toolbar-right { display: flex; gap: 6px; }
.onto-search {
  flex: 1; max-width: 340px;
  background: var(--surface-soft); border: 1px solid var(--border);
  border-radius: var(--radius-xs); color: var(--text); font-size: 12px; padding: 5px 9px;
}
.onto-search:focus { outline: none; border-color: var(--border-accent); }
.onto-toolbar-meta { font-size: 10.5px; color: var(--text3); font-family: var(--font-mono); }

.onto-btn {
  border: 1px solid var(--border-strong); background: var(--surface);
  color: var(--text2); font-size: 11.5px; padding: 5px 11px;
  border-radius: var(--radius-xs); cursor: pointer; white-space: nowrap;
  transition: all 0.14s ease;
}
.onto-btn:hover:not(:disabled) { border-color: var(--border-accent); color: var(--accent-bright); }
.onto-btn:disabled { opacity: 0.42; cursor: not-allowed; }
.onto-btn.primary { background: var(--accent-soft); border-color: var(--border-accent); color: var(--accent-bright); }
.onto-btn.primary:hover:not(:disabled) { background: var(--accent-soft-strong); }
.onto-btn.ghost { background: transparent; }
.onto-btn.danger { color: var(--red); border-color: rgba(212,93,61,0.35); }
.onto-btn.danger:hover:not(:disabled) { background: rgba(212,93,61,0.1); }

.onto-alert {
  display: flex; align-items: center; gap: 8px; font-size: 11.5px;
  padding: 7px 10px; border-radius: var(--radius-xs); border: 1px solid;
}
.onto-alert.error { color: var(--red); border-color: rgba(212,93,61,0.35); background: rgba(212,93,61,0.07); }
.onto-alert.ok { color: var(--green); border-color: rgba(143,191,106,0.3); background: rgba(143,191,106,0.06); }
.onto-alert button { margin-left: auto; background: none; border: none; color: inherit; cursor: pointer; }

/* ── 三栏 ── */
.onto-work {
  display: grid;
  grid-template-columns: 268px minmax(0, 1fr) 336px;
  gap: 10px;
  flex: 1;
  min-height: 0;
}
@media (max-width: 1400px) {
  .onto-work { grid-template-columns: 240px minmax(0, 1fr) 300px; }
}
@media (max-width: 1150px) {
  .onto-work { grid-template-columns: 1fr; }
  .onto-rail, .onto-inspector-host { max-height: 340px; }
}

.onto-rail {
  display: flex; flex-direction: column; min-height: 0;
  border: 1px solid var(--border); border-radius: var(--radius); background: var(--surface);
}
.onto-rail-head {
  display: flex; flex-direction: column; gap: 2px;
  padding: 8px 10px; border-bottom: 1px solid var(--border);
  font-size: 10px; letter-spacing: 0.06em; text-transform: uppercase; color: var(--text3);
}
.onto-rail-dir {
  font-size: 9px; color: var(--text-dim); text-transform: none;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; direction: rtl; text-align: left;
}
.onto-rail-body { overflow-y: auto; padding: 6px; min-height: 0; }
.onto-scene { margin-bottom: 3px; }
.onto-scene-head {
  display: flex; flex-direction: column; gap: 2px; width: 100%; text-align: left;
  border: 1px solid transparent; border-radius: var(--radius-sm);
  background: none; padding: 7px 8px; cursor: pointer; color: var(--text2);
}
.onto-scene-head:hover { background: var(--surface-soft); }
.onto-scene-head.active { background: var(--accent-soft); border-color: var(--border-accent); }
.onto-scene-head.broken { border-color: rgba(212,93,61,0.35); }
.onto-scene-name { font-size: 12px; font-weight: 600; color: var(--text); }
.onto-scene-head.active .onto-scene-name { color: var(--accent-bright); }
.onto-scene-sub { font-size: 9.5px; color: var(--text-dim); }
.onto-scene-stats { display: flex; gap: 5px; margin-top: 2px; flex-wrap: wrap; }
.onto-mini-stat { font-size: 9.5px; font-family: var(--font-mono); color: var(--text3); }
.onto-mini-stat.reuse { color: var(--cyan); }
.onto-mini-stat.bad { color: var(--red); }
.onto-scene-summary { font-size: 10px; color: var(--text3); }
.onto-scene-tags { display: flex; gap: 3px; flex-wrap: wrap; margin-top: 2px; }
.onto-tag {
  font-size: 9px; padding: 0 5px; border-radius: 999px;
  border: 1px solid var(--border-strong); color: var(--text3);
}
.onto-version-list {
  display: flex; flex-direction: column; gap: 1px;
  padding: 3px 0 5px 10px; border-left: 1px solid var(--border); margin-left: 9px;
}
.onto-version-item {
  display: flex; align-items: center; gap: 6px;
  border: none; background: none; cursor: pointer; color: var(--text3);
  font-size: 10px; padding: 3px 6px; border-radius: var(--radius-xs); text-align: left;
}
.onto-version-item:hover { background: var(--surface-soft); color: var(--text); }
.onto-version-item.active { background: var(--surface-muted); color: var(--accent-bright); }
.onto-version-item.broken { color: var(--red); }
.onto-version-mode { font-size: 9px; color: var(--text-dim); }
.onto-version-q { font-size: 9px; }
.onto-version-q.q-endorsed { color: var(--green); }
.onto-version-q.q-rejected { color: var(--red); }
.onto-version-q.q-deprecated { color: var(--text-dim); }
.onto-version-origin { font-size: 10px; }
.onto-version-latest { font-size: 8.5px; color: var(--accent); margin-left: auto; }

/* ── 主区 ── */
.onto-main {
  display: flex; flex-direction: column; gap: 9px; min-height: 0; min-width: 0;
  border: 1px solid var(--border); border-radius: var(--radius);
  background: var(--surface); padding: 10px;
}
.onto-placeholder {
  margin: auto; font-size: 12.5px; color: var(--text3); text-align: center; max-width: 320px;
}
.onto-main-head {
  display: flex; align-items: flex-start; justify-content: space-between;
  gap: 12px; flex-wrap: wrap;
}
.onto-main-title { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
.onto-main-title h2 { margin: 0; font-size: 15px; color: var(--text); display: flex; align-items: baseline; gap: 7px; }
.onto-vtag { font-size: 11px; color: var(--accent); }
.onto-write-target {
  font-size: 9.5px; color: var(--text-dim);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 560px;
  direction: rtl; text-align: left;
}
.onto-main-actions { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.onto-dirty { font-size: 10.5px; color: var(--yellow); font-family: var(--font-mono); }
.onto-clean { font-size: 10.5px; color: var(--text3); font-family: var(--font-mono); }

.onto-errors {
  border: 1px solid rgba(212,93,61,0.35); background: rgba(212,93,61,0.06);
  border-radius: var(--radius-xs); padding: 7px 10px;
}
.onto-errors-head { display: flex; gap: 10px; align-items: baseline; font-size: 11.5px; color: var(--red); }
.onto-errors-list { margin: 5px 0 0; padding-left: 16px; display: flex; flex-direction: column; gap: 3px; }
.onto-errors-list li { font-size: 11px; color: var(--text2); }
.onto-errors-list code { color: var(--accent); font-size: 10px; margin-right: 6px; }
.onto-link {
  background: none; border: none; color: var(--accent); cursor: pointer;
  font-size: 10.5px; text-decoration: underline; margin-left: 6px; padding: 0;
}
.onto-ok-strip {
  font-size: 11px; color: var(--green); border: 1px solid rgba(143,191,106,0.28);
  background: rgba(143,191,106,0.05); border-radius: var(--radius-xs); padding: 5px 10px;
}

.onto-tabs { display: flex; gap: 3px; flex-wrap: wrap; border-bottom: 1px solid var(--border); }
.onto-tab {
  border: none; background: none; color: var(--text3); font-size: 11.5px;
  padding: 6px 11px; cursor: pointer; border-bottom: 2px solid transparent;
}
.onto-tab:hover { color: var(--text); }
.onto-tab.active { color: var(--accent-bright); border-bottom-color: var(--accent); }

.onto-view-body { flex: 1; min-height: 0; display: flex; flex-direction: column; gap: 8px; overflow-y: auto; }
.onto-view-body.no-scroll { overflow: hidden; }
.onto-graph-host { display: flex; flex-direction: column; gap: 8px; flex: 1; min-height: 0; }

.onto-filters {
  display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
  padding: 6px 9px; border: 1px solid var(--border); border-radius: var(--radius-xs);
  background: var(--surface-soft);
}
.onto-filters-title { font-size: 10px; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text3); }
.onto-filter { display: flex; align-items: center; gap: 5px; font-size: 10.5px; color: var(--text3); }
.onto-filter select {
  background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-xs);
  color: var(--text2); font-size: 10.5px; padding: 2px 5px;
}
.onto-filter-note { font-size: 10.5px; color: var(--yellow); font-family: var(--font-mono); }

.onto-json-host { display: flex; flex-direction: column; gap: 6px; flex: 1; min-height: 0; }
.onto-json {
  flex: 1; min-height: 380px; width: 100%;
  background: var(--surface-soft); border: 1px solid var(--border);
  border-radius: var(--radius-xs); color: var(--text); font-size: 11.5px;
  line-height: 1.5; padding: 9px; resize: vertical; tab-size: 2;
}
.onto-json:focus { outline: none; border-color: var(--border-accent); }
.onto-hint { font-size: 11px; color: var(--text3); margin: 0; }

/* ── 度量 ── */
.onto-metrics { display: flex; flex-direction: column; gap: 10px; }
.onto-metrics-hero {
  display: flex; gap: 18px; align-items: center; flex-wrap: wrap;
  border: 1px solid var(--border); border-radius: var(--radius); padding: 12px 14px; background: var(--surface-soft);
}
.onto-health-score { display: flex; align-items: baseline; gap: 7px; }
.onto-health-num { font-family: var(--font-display); font-size: 38px; line-height: 1; color: var(--accent-bright); }
.onto-health-grade {
  font-family: var(--font-mono); font-size: 17px; padding: 1px 8px;
  border-radius: var(--radius-xs); border: 1px solid var(--border-strong);
}
.grade-A { color: var(--green); border-color: rgba(143,191,106,0.45); }
.grade-B { color: #9fd07a; border-color: rgba(159,208,122,0.4); }
.grade-C { color: var(--yellow); border-color: rgba(212,169,61,0.4); }
.grade-D { color: #e08a3d; border-color: rgba(224,138,61,0.4); }
.grade-E { color: var(--red); border-color: rgba(212,93,61,0.45); }
.onto-breakdown { flex: 1; min-width: 260px; display: flex; flex-direction: column; gap: 3px; }
.onto-breakdown-row { display: grid; grid-template-columns: 108px 1fr 52px; gap: 8px; align-items: center; font-size: 10px; }
.onto-breakdown-label { color: var(--text3); }
.onto-breakdown-bar { height: 5px; background: var(--surface-muted); border-radius: 999px; overflow: hidden; }
.onto-breakdown-fill { display: block; height: 100%; background: linear-gradient(90deg, var(--accent-strong), var(--accent-bright)); }
.onto-breakdown-pts { color: var(--text3); text-align: right; }

.onto-metric-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 9px; }
.onto-metric-card {
  border: 1px solid var(--border); border-radius: var(--radius);
  padding: 10px 12px; background: var(--surface); display: flex; flex-direction: column; gap: 7px;
}
.onto-metric-card h5 {
  margin: 0; font-size: 10px; letter-spacing: 0.06em; text-transform: uppercase; color: var(--text3);
}
.onto-metric-card.danger-zone { border-color: rgba(212,93,61,0.25); }
.onto-dl { margin: 0; display: flex; flex-direction: column; gap: 3px; }
.onto-dl > div { display: flex; gap: 8px; align-items: baseline; font-size: 11px; }
.onto-dl dt { flex: 0 0 52%; color: var(--text3); font-size: 10.5px; }
.onto-dl dd { margin: 0; color: var(--text); }
.onto-dl dd.mono { font-family: var(--font-mono); }
.onto-dl dd.good { color: var(--green); }
.onto-dl dd.warn { color: var(--yellow); }
.onto-dl dd.bad { color: var(--red); }

.onto-findings-full { display: flex; flex-direction: column; gap: 6px; }
.onto-findings-full h5 {
  margin: 0; font-size: 10px; letter-spacing: 0.06em; text-transform: uppercase; color: var(--text3);
}
.onto-finding {
  display: flex; flex-direction: column; gap: 3px;
  border: 1px solid var(--border); border-left-width: 2px;
  border-radius: var(--radius-xs); padding: 6px 9px; background: var(--surface-soft);
}
.onto-finding.sev-critical { border-left-color: var(--red); }
.onto-finding.sev-important { border-left-color: var(--yellow); }
.onto-finding.sev-minor { border-left-color: var(--text3); }
.onto-finding-sev { font-size: 9.5px; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text3); }
.onto-finding-code { font-size: 10px; color: var(--accent); }
.onto-finding-rule { font-size: 9.5px; margin-left: 6px; }
.onto-finding-msg { margin: 0; font-size: 11px; color: var(--text); line-height: 1.45; }
.onto-finding-hint { margin: 0; font-size: 10.5px; color: var(--text3); line-height: 1.45; }
.onto-finding-hint.dim, .dim { color: var(--text-dim); }

/* ── 基本面 ── */
.onto-info { display: flex; flex-direction: column; gap: 9px; }
.onto-info .onto-field-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 8px; }
.onto-field { display: flex; flex-direction: column; gap: 3px; }
.onto-field.wide { grid-column: 1 / -1; }
.onto-field > span { font-size: 10px; text-transform: uppercase; letter-spacing: 0.04em; color: var(--text3); }
.onto-field input, .onto-field textarea, .onto-input {
  background: var(--surface-soft); border: 1px solid var(--border);
  border-radius: var(--radius-xs); color: var(--text); font-size: 12px; padding: 4px 7px;
}
.onto-pre {
  margin: 0; font-size: 10.5px; line-height: 1.5; color: var(--text2);
  background: var(--surface-soft); border: 1px solid var(--border);
  border-radius: var(--radius-xs); padding: 8px; max-height: 240px; overflow: auto;
  white-space: pre-wrap; word-break: break-word;
}
.onto-danger-row { display: flex; gap: 6px; flex-wrap: wrap; }

.onto-inspector-host {
  border: 1px solid var(--border); border-radius: var(--radius);
  background: var(--surface); padding: 10px; min-height: 0;
}

/* ── 模态 ── */
.onto-modal-backdrop {
  position: fixed; inset: 0; z-index: 60;
  background: rgba(6, 7, 5, 0.72); backdrop-filter: blur(2px);
  display: flex; align-items: center; justify-content: center; padding: 24px;
}
.onto-modal {
  width: min(520px, 100%); max-height: 86vh; overflow-y: auto;
  border: 1px solid var(--border-strong); border-radius: var(--radius-lg);
  background: var(--surface-strong); box-shadow: var(--shadow-lg);
  padding: 18px 20px; display: flex; flex-direction: column; gap: 10px;
}
.onto-modal.wide { width: min(920px, 100%); }
.onto-modal h3 { margin: 0; font-size: 14px; color: var(--text); }
.onto-modal p { margin: 0; font-size: 12px; color: var(--text2); line-height: 1.55; }
.onto-modal-actions { display: flex; gap: 7px; justify-content: flex-end; flex-wrap: wrap; margin-top: 4px; }
.onto-adopt-bar { display: flex; align-items: center; gap: 10px; justify-content: space-between; }
.onto-adopt-list { display: flex; flex-direction: column; gap: 4px; max-height: 52vh; overflow-y: auto; }
.onto-adopt-row {
  display: flex; align-items: center; gap: 10px; justify-content: space-between;
  border: 1px solid var(--border); border-radius: var(--radius-xs);
  padding: 6px 9px; background: var(--surface);
}
.onto-adopt-main { display: flex; align-items: baseline; gap: 8px; flex-wrap: wrap; min-width: 0; }
.onto-adopt-name { font-size: 12px; color: var(--text); }
.onto-adopt-sub { font-size: 9.5px; color: var(--text-dim); }
.onto-adopt-scene { font-size: 10px; color: var(--accent); }
.onto-adopt-stats { font-size: 10px; color: var(--text3); }
.onto-adopt-badge {
  font-size: 9.5px; font-family: var(--font-mono); padding: 0 6px; border-radius: 999px;
  border: 1px solid var(--border-strong); color: var(--text3);
}
.onto-adopt-badge.ok { color: var(--green); border-color: rgba(143,191,106,0.35); }
.onto-adopt-badge.warn { color: var(--yellow); border-color: rgba(212,169,61,0.35); }
.onto-adopt-badge.bad { color: var(--red); border-color: rgba(212,93,61,0.4); }
.onto-empty { font-size: 11.5px; color: var(--text3); margin: 4px 0; }
.mono { font-family: var(--font-mono); }
</style>
