<template>
  <div class="onto-inspector">
    <!-- ── 未选中：显示资产基本面 / 度量 ── -->
    <template v-if="!selection">
      <div class="onto-insp-header">
        <span class="onto-insp-kicker">{{ $t('ontology.viewInfo') }}</span>
        <span class="onto-insp-title">{{ asset?.scene_key }} · v{{ asset?.version }}</span>
      </div>

      <div class="onto-health-card" v-if="metrics?.health">
        <div class="onto-health-score">
          <span class="onto-health-num">{{ metrics.health.score }}</span>
          <span class="onto-health-grade" :class="`grade-${metrics.health.grade}`">{{ metrics.health.grade }}</span>
        </div>
        <div class="onto-health-meta">
          <span>{{ $t('ontology.metricsScore') }}</span>
          <span class="onto-health-sub">
            {{ $t('ontology.severityCritical') }} {{ metrics.finding_counts?.critical || 0 }} ·
            {{ $t('ontology.severityImportant') }} {{ metrics.finding_counts?.important || 0 }} ·
            {{ $t('ontology.severityMinor') }} {{ metrics.finding_counts?.minor || 0 }}
          </span>
        </div>
      </div>

      <dl class="onto-dl" v-if="entry">
        <div><dt>{{ $t('ontology.quality') }}</dt><dd>
          <span class="onto-q" :class="`q-${entry.quality}`">{{ qualityLabel(entry.quality) }}</span>
        </dd></div>
        <div><dt>{{ $t('ontology.origin') }}</dt><dd>{{ originLabel(entry.origin) }}</dd></div>
        <div><dt>{{ $t('ontology.buildMode') }}</dt><dd class="mono">{{ entry.build_mode || '—' }}</dd></div>
        <div v-if="entry.parent_version"><dt>{{ $t('ontology.parentVersion') }}</dt><dd class="mono">v{{ entry.parent_version }}</dd></div>
        <div><dt>{{ $t('ontology.reuseCount') }}</dt><dd class="mono">{{ entry.reuse_count || 0 }}</dd></div>
        <div><dt>{{ $t('ontology.bytes') }}</dt><dd class="mono">{{ bytesLabel }}</dd></div>
        <div><dt>{{ $t('ontology.createdAt') }}</dt><dd class="mono">{{ shortTime(entry.created_at) }}</dd></div>
        <div><dt>{{ $t('ontology.updatedAt') }}</dt><dd class="mono">{{ shortTime(entry.updated_at) }}</dd></div>
        <div v-if="entry.built_from_run"><dt>{{ $t('ontology.builtFromRun') }}</dt><dd class="mono ellipsis">{{ entry.built_from_run }}</dd></div>
        <div v-if="entry.fingerprinted_from"><dt>{{ $t('ontology.fingerprintedFrom') }}</dt>
          <dd class="mono ellipsis" :title="entry.fingerprinted_from">{{ basename(entry.fingerprinted_from) }}</dd></div>
        <div v-if="entry.schema_fp"><dt>{{ $t('ontology.fingerprint') }}</dt>
          <dd class="mono ellipsis" :title="entry.schema_fp">{{ entry.schema_fp.slice(7, 19) }}…</dd></div>
        <div v-if="etag"><dt>{{ $t('ontology.etag') }}</dt>
          <dd class="mono ellipsis" :title="etag">{{ etag.slice(7, 19) }}…</dd></div>
      </dl>

      <div class="onto-insp-section" v-if="metrics">
        <h5>{{ $t('ontology.metricsScale') }}</h5>
        <dl class="onto-dl compact">
          <div><dt>{{ $t('ontology.editor.signals') }}</dt><dd class="mono">{{ metrics.scale.signals_total }}</dd></div>
          <div><dt>{{ $t('ontology.editor.relationships') }}</dt><dd class="mono">{{ metrics.scale.relationships }}</dd></div>
          <div><dt>{{ $t('ontology.editor.stages') }}</dt><dd class="mono">{{ metrics.scale.stages }}</dd></div>
          <div><dt>{{ $t('ontology.editor.equipment') }}</dt><dd class="mono">{{ metrics.scale.equipment }}</dd></div>
          <div><dt>{{ $t('ontology.editor.principles') }}</dt><dd class="mono">{{ metrics.scale.physical_principles }}</dd></div>
          <div><dt>{{ $t('ontology.orphanSignals') }}</dt>
            <dd class="mono" :class="{ warn: metrics.consistency.orphan_signals > 0 }">{{ metrics.consistency.orphan_signals }}</dd></div>
          <div><dt>{{ $t('ontology.dangling') }}</dt>
            <dd class="mono" :class="{ bad: metrics.consistency.dangling_relationships > 0 }">{{ metrics.consistency.dangling_relationships }}</dd></div>
          <div><dt>{{ $t('ontology.causalCycles') }}</dt>
            <dd class="mono" :class="{ bad: metrics.topology?.causal_cycle_count > 0 }">{{ metrics.topology?.causal_cycle_count ?? 0 }}</dd></div>
        </dl>
      </div>
    </template>

    <!-- ── 选中节点 ── -->
    <template v-else-if="selection.kind === 'node'">
      <div class="onto-insp-header">
        <span class="onto-insp-kicker">{{ $t('ontology.entitySignal') }} · {{ selection.data.kind }}</span>
        <span class="onto-insp-title mono">{{ selection.data.id }}</span>
        <button type="button" class="onto-insp-close" @click="$emit('clear')">✕</button>
      </div>

      <div class="onto-chip-row">
        <span v-if="selection.data.role" class="onto-chip-sm">{{ selection.data.role }}</span>
        <span v-if="selection.data.bucket" class="onto-chip-sm muted">{{ selection.data.bucket }}</span>
        <span v-if="d.confidence" class="onto-chip-sm" :class="`c-${String(d.confidence).toLowerCase()}`">{{ d.confidence }}</span>
        <span v-if="d.behavior_match" class="onto-chip-sm" :class="`b-${String(d.behavior_match).toLowerCase()}`">{{ d.behavior_match }}</span>
        <span class="onto-chip-sm muted">{{ $t('ontology.degree') }} {{ selection.data.degree ?? 0 }}</span>
      </div>

      <div class="onto-insp-section" v-if="d.unit || d.normal_range">
        <h5>{{ $t('ontology.secIdentity') }}</h5>
        <dl class="onto-dl compact">
          <div v-if="d.unit"><dt>{{ $t('ontology.editor.unit') }}</dt><dd>{{ d.unit }}</dd></div>
          <div v-if="d.normal_range"><dt>{{ $t('ontology.editor.normalRange') }}</dt>
            <dd class="mono">[{{ d.normal_range?.[0] ?? '—' }}, {{ d.normal_range?.[1] ?? '—' }}]</dd></div>
          <div v-if="d.target !== null && d.target !== undefined"><dt>{{ $t('ontology.editor.target') }}</dt><dd class="mono">{{ d.target }}</dd></div>
          <div v-if="d.setpoint !== null && d.setpoint !== undefined"><dt>setpoint</dt><dd class="mono">{{ d.setpoint }}</dd></div>
        </dl>
      </div>

      <div class="onto-insp-section" v-if="d.physical_meaning">
        <h5>{{ $t('ontology.secSemantics') }}</h5>
        <p class="onto-prose">{{ d.physical_meaning }}</p>
        <p v-if="d.inference_basis" class="onto-prose dim">↳ {{ d.inference_basis }}</p>
      </div>

      <div class="onto-insp-section" v-if="d.governing_law">
        <h5>{{ $t('ontology.secPhysics') }}</h5>
        <code class="onto-code">{{ d.governing_law }}</code>
      </div>

      <!-- 预期 vs 观测：推断行内联呈现（同一面板，靠底色区分，而非另开 tab） -->
      <div class="onto-insp-section" v-if="d.expected_data_behavior || d.observed_data_behavior">
        <h5>{{ $t('ontology.secBehavior') }}</h5>
        <div class="onto-behavior">
          <div class="onto-behavior-row expected">
            <span class="onto-behavior-tag">{{ $t('ontology.inModel') }}</span>
            <span>{{ d.expected_data_behavior || $t('ontology.notFilled') }}</span>
          </div>
          <div class="onto-behavior-row observed">
            <span class="onto-behavior-tag">{{ $t('ontology.inData') }}</span>
            <span>{{ d.observed_data_behavior || $t('ontology.notFilled') }}</span>
          </div>
        </div>
        <p v-if="d.discrepancy_signal" class="onto-prose warn">{{ d.discrepancy_signal }}</p>
      </div>

      <div class="onto-insp-section" v-if="d.data_facts">
        <h5>data_facts</h5>
        <dl class="onto-dl compact">
          <div v-for="(v, k) in flatFacts(d.data_facts)" :key="`f-${k}`">
            <dt class="mono">{{ k }}</dt><dd class="mono">{{ v }}</dd>
          </div>
        </dl>
      </div>

      <div class="onto-insp-section">
        <h5>{{ $t('ontology.secConnectivity') }}</h5>
        <div class="onto-edge-group">
          <div class="onto-edge-label">{{ $t('ontology.outEdges') }} ({{ outEdges.length }})</div>
          <button
            v-for="e in outEdges" :key="`o-${e.id}`" type="button" class="onto-edge-item"
            @click="$emit('select', { kind: 'edge', data: e })"
          >
            <span class="onto-edge-dot" :style="{ background: e.color }"></span>
            <span class="mono">{{ e.target }}</span>
            <span class="onto-edge-type">{{ e.label || e.type }}</span>
          </button>
          <p v-if="!outEdges.length" class="onto-prose dim">{{ $t('ontology.impactNone') }}</p>
        </div>
        <div class="onto-edge-group">
          <div class="onto-edge-label">{{ $t('ontology.inEdges') }} ({{ inEdges.length }})</div>
          <button
            v-for="e in inEdges" :key="`i-${e.id}`" type="button" class="onto-edge-item"
            @click="$emit('select', { kind: 'edge', data: e })"
          >
            <span class="onto-edge-dot" :style="{ background: e.color }"></span>
            <span class="mono">{{ e.source }}</span>
            <span class="onto-edge-type">{{ e.label || e.type }}</span>
          </button>
          <p v-if="!inEdges.length" class="onto-prose dim">{{ $t('ontology.impactNone') }}</p>
        </div>
      </div>

      <div class="onto-insp-section" v-if="relatedFindings.length">
        <h5>{{ $t('ontology.secFindings') }} ({{ relatedFindings.length }})</h5>
        <div v-for="f in relatedFindings" :key="f.code + f.message" class="onto-finding" :class="`sev-${f.severity}`">
          <span class="onto-finding-sev">{{ severityLabel(f.severity) }}</span>
          <span class="onto-finding-code mono">{{ f.code }}</span>
          <p class="onto-finding-msg">{{ findingText(f) }}</p>
          <p v-if="f.hint" class="onto-finding-hint">{{ f.hint }}</p>
        </div>
      </div>
    </template>

    <!-- ── 选中边 ── -->
    <template v-else>
      <div class="onto-insp-header">
        <span class="onto-insp-kicker">{{ $t('ontology.entityEdge') }}</span>
        <span class="onto-insp-title mono">{{ selection.data.source }} → {{ selection.data.target }}</span>
        <button type="button" class="onto-insp-close" @click="$emit('clear')">✕</button>
      </div>

      <div class="onto-chip-row">
        <span class="onto-chip-sm" :style="{ color: selection.data.color, borderColor: selection.data.color }">
          {{ selection.data.label || selection.data.type }}
        </span>
        <span v-if="ed.strength" class="onto-chip-sm muted">{{ ed.strength }}</span>
        <span v-if="ed.inferred" class="onto-chip-sm" style="color:#6ba8b8">{{ $t('ontology.editor.inferred') }}</span>
      </div>

      <div class="onto-insp-section" v-if="ed.mechanism">
        <h5>{{ $t('ontology.editor.mechanism') }}</h5>
        <p class="onto-prose">{{ ed.mechanism }}</p>
      </div>
      <div class="onto-insp-section" v-if="ed.governing_equation">
        <h5>{{ $t('ontology.editor.equation') }}</h5>
        <code class="onto-code">{{ ed.governing_equation }}</code>
      </div>

      <div class="onto-insp-section">
        <h5>{{ $t('ontology.metricsRelationship') }}</h5>
        <dl class="onto-dl compact">
          <div v-if="ed.predicted_functional_form"><dt>{{ $t('ontology.editor.functionalForm') }}</dt><dd class="mono">{{ ed.predicted_functional_form }}</dd></div>
          <div v-if="ed.data_direction_validated"><dt>{{ $t('ontology.dataValidated') }}</dt><dd class="mono">{{ ed.data_direction_validated }}</dd></div>
          <div v-if="ed.time_lag"><dt>{{ $t('ontology.editor.timeLag') }}</dt><dd>{{ ed.time_lag }}</dd></div>
          <div v-if="ed.optimal_lag"><dt>optimal_lag</dt><dd class="mono">{{ ed.optimal_lag.steps }} {{ $t('ontology.steps') }} / {{ ed.optimal_lag.seconds ?? '—' }}s</dd></div>
          <div v-if="ed.lag_agreement"><dt>lag_agreement</dt><dd class="mono">{{ ed.lag_agreement }}</dd></div>
          <div v-if="ed.lag_compensated_correlation?.r !== undefined">
            <dt>lag_compensated r</dt><dd class="mono">{{ ed.lag_compensated_correlation.r }}</dd></div>
          <div v-if="ed.lag_detection_method"><dt>lag_detection_method</dt><dd class="mono">{{ ed.lag_detection_method }}</dd></div>
        </dl>
        <p v-if="ed.lag_discrepancy_note" class="onto-prose warn">{{ ed.lag_discrepancy_note }}</p>
      </div>

      <div class="onto-insp-section" v-if="ed.evidence">
        <h5>evidence</h5>
        <p class="onto-prose">{{ ed.evidence }}</p>
      </div>
      <div class="onto-insp-section" v-if="ed.uncertainty">
        <h5>uncertainty</h5>
        <p class="onto-prose warn">{{ ed.uncertainty }}</p>
      </div>
      <div class="onto-insp-section" v-if="ed.stage2_queue">
        <p class="onto-prose dim">stage2_queue: true</p>
      </div>
    </template>

    <!-- ── 问题清单（始终可见，点击定位）── -->
    <div class="onto-insp-section findings-list" v-if="metrics?.findings?.length">
      <h5>
        {{ $t('ontology.errorsTitle') }}
        <span class="onto-count-badge">{{ visibleFindings.length }}</span>
      </h5>
      <div class="onto-sev-filter">
        <button
          v-for="s in ['critical', 'important', 'minor']" :key="s" type="button"
          class="onto-chip" :class="{ active: sevFilter.includes(s) }"
          :title="$t('ontology.filterBySeverity')" @click="toggleSev(s)"
        >
          <span class="onto-sev-dot" :class="`sev-${s}`"></span>
          {{ severityLabel(s) }} {{ metrics.finding_counts?.[s] || 0 }}
        </button>
      </div>
      <button
        v-for="(f, i) in visibleFindings" :key="`fd-${i}`" type="button"
        class="onto-finding clickable" :class="`sev-${f.severity}`"
        @click="$emit('select', { kind: 'node', data: { id: f.focusNode, kind: 'finding' } })"
      >
        <span class="onto-finding-sev">{{ severityLabel(f.severity) }}</span>
        <span class="onto-finding-code mono">{{ f.code }}</span>
        <p class="onto-finding-msg">{{ findingText(f) }}</p>
        <p v-if="f.focusNode" class="onto-finding-hint mono">{{ $t('ontology.findingFocus') }}: {{ f.focusNode }}
          <span v-if="f.pointer" class="dim"> ({{ f.pointer }})</span>
        </p>
        <p v-if="f.hint" class="onto-finding-hint">{{ f.hint }}</p>
        <p v-if="f.justification?.length" class="onto-finding-hint dim">
          {{ $t('ontology.findingJustification') }}: {{ f.justification.join(' · ') }}
        </p>
      </button>
      <p v-if="!visibleFindings.length" class="onto-prose dim">{{ $t('ontology.noErrors') }}</p>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();

const props = defineProps({
  asset: { type: Object, default: null },
  graph: { type: Object, default: () => ({ nodes: [], edges: [] }) },
  metrics: { type: Object, default: null },
  etag: { type: String, default: '' },
  selection: { type: Object, default: null },
});
defineEmits(['select', 'clear']);

const entry = computed(() => props.asset?.entry || null);
const d = computed(() => props.selection?.data?.detail || {});
const ed = computed(() => props.selection?.data?.detail || {});

const sevFilter = ref(['critical', 'important', 'minor']);
function toggleSev(s) {
  const i = sevFilter.value.indexOf(s);
  if (i >= 0) sevFilter.value.splice(i, 1);
  else sevFilter.value.push(s);
}

const visibleFindings = computed(() =>
  (props.metrics?.findings || []).filter((f) => sevFilter.value.includes(f.severity)));

const outEdges = computed(() => {
  const id = props.selection?.data?.id;
  if (!id) return [];
  return (props.graph?.edges || []).filter((e) => e.source === id);
});
const inEdges = computed(() => {
  const id = props.selection?.data?.id;
  if (!id) return [];
  return (props.graph?.edges || []).filter((e) => e.target === id);
});

const relatedFindings = computed(() => {
  const id = props.selection?.data?.id;
  if (!id) return [];
  return (props.metrics?.findings || []).filter((f) => f.focusNode === id || (f.justification || []).some((j) => String(j).includes(id)));
});

const bytesLabel = computed(() => {
  const b = entry.value?.bytes ?? props.asset?.bytes ?? 0;
  if (b > 1024 * 1024) return `${(b / 1024 / 1024).toFixed(2)} MB`;
  if (b > 1024) return `${(b / 1024).toFixed(1)} KB`;
  return `${b} B`;
});

function flatFacts(o) {
  const out = {};
  for (const [k, v] of Object.entries(o || {})) {
    out[k] = typeof v === 'object' && v !== null ? JSON.stringify(v) : v;
  }
  return out;
}

function basename(p) {
  return String(p || '').split(/[\\/]/).pop();
}
function shortTime(iso) {
  if (!iso) return '—';
  return String(iso).replace('T', ' ').slice(0, 19);
}
function severityLabel(s) {
  return { critical: t('ontology.severityCritical'), important: t('ontology.severityImportant'), minor: t('ontology.severityMinor') }[s] || s;
}
function qualityLabel(q) {
  return {
    endorsed: t('ontology.qualityEndorsed'), rejected: t('ontology.qualityRejected'),
    deprecated: t('ontology.qualityDeprecated'), unvalidated: t('ontology.qualityUnvalidated'),
  }[q] || q;
}
function originLabel(o) {
  if (!o) return t('ontology.originUnknown');
  if (o.startsWith('agent')) return t('ontology.originAgent');
  if (o.startsWith('user')) return t('ontology.originUser');
  return o;
}
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
.onto-inspector {
  display: flex;
  flex-direction: column;
  gap: 10px;
  overflow-y: auto;
  min-height: 0;
  height: 100%;
  padding-right: 4px;
}
.onto-insp-header {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 6px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border);
}
.onto-insp-kicker {
  font-size: 9.5px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text3);
  width: 100%;
}
.onto-insp-title { font-size: 13px; font-weight: 600; color: var(--text); word-break: break-all; }
.onto-insp-title.mono { font-family: var(--font-mono); font-size: 12px; }
.onto-insp-close {
  margin-left: auto; border: none; background: none; color: var(--text3);
  cursor: pointer; font-size: 12px; padding: 0 2px;
}
.onto-insp-close:hover { color: var(--text); }

.onto-health-card {
  display: flex; align-items: center; gap: 12px;
  border: 1px solid var(--border); border-radius: var(--radius);
  padding: 10px 12px; background: var(--surface);
}
.onto-health-score { display: flex; align-items: baseline; gap: 6px; }
.onto-health-num { font-family: var(--font-display); font-size: 30px; line-height: 1; color: var(--accent-bright); }
.onto-health-grade {
  font-family: var(--font-mono); font-size: 15px; padding: 1px 7px;
  border-radius: var(--radius-xs); border: 1px solid var(--border-strong);
}
.grade-A { color: var(--green); border-color: rgba(143,191,106,0.45); }
.grade-B { color: #9fd07a; border-color: rgba(159,208,122,0.4); }
.grade-C { color: var(--yellow); border-color: rgba(212,169,61,0.4); }
.grade-D { color: #e08a3d; border-color: rgba(224,138,61,0.4); }
.grade-E { color: var(--red); border-color: rgba(212,93,61,0.45); }
.onto-health-meta { display: flex; flex-direction: column; gap: 2px; font-size: 11.5px; color: var(--text2); }
.onto-health-sub { font-size: 10.5px; color: var(--text3); }

.onto-dl { margin: 0; display: flex; flex-direction: column; gap: 4px; }
.onto-dl > div { display: flex; gap: 8px; align-items: baseline; font-size: 11.5px; }
.onto-dl dt { flex: 0 0 42%; color: var(--text3); font-size: 10.5px; }
.onto-dl dd { margin: 0; color: var(--text); min-width: 0; }
.onto-dl.compact dt { flex: 0 0 48%; }
.onto-dl dd.mono, .mono { font-family: var(--font-mono); }
.onto-dl dd.ellipsis { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.onto-dl dd.warn { color: var(--yellow); }
.onto-dl dd.bad { color: var(--red); }

.onto-q { font-size: 10.5px; padding: 1px 6px; border-radius: 999px; border: 1px solid var(--border-strong); }
.q-endorsed { color: var(--green); border-color: rgba(143,191,106,0.4); }
.q-rejected { color: var(--red); border-color: rgba(212,93,61,0.45); }
.q-deprecated { color: var(--text3); text-decoration: line-through; }
.q-unvalidated { color: var(--yellow); border-color: rgba(212,169,61,0.3); }

.onto-insp-section { display: flex; flex-direction: column; gap: 6px; }
.onto-insp-section h5 {
  margin: 0; font-size: 10px; letter-spacing: 0.07em; text-transform: uppercase;
  color: var(--text3); display: flex; align-items: center; gap: 6px;
}
.onto-prose { margin: 0; font-size: 11.5px; line-height: 1.55; color: var(--text); }
.onto-prose.dim { color: var(--text3); }
.onto-prose.warn { color: var(--yellow); }
.onto-code {
  display: block; font-family: var(--font-mono); font-size: 11px;
  background: var(--surface-soft); border: 1px solid var(--border);
  border-radius: var(--radius-xs); padding: 5px 7px; color: var(--accent-bright);
  word-break: break-all;
}
.onto-chip-row { display: flex; flex-wrap: wrap; gap: 4px; }
.onto-chip-sm {
  font-size: 10px; font-family: var(--font-mono); padding: 1px 6px;
  border-radius: 999px; border: 1px solid var(--border-strong); color: var(--text2);
}
.onto-chip-sm.muted { color: var(--text3); }
.onto-chip-sm.c-known { color: var(--green); }
.onto-chip-sm.c-inferred { color: var(--yellow); }
.onto-chip-sm.b-contradicted { color: var(--red); }
.onto-chip-sm.b-consistent { color: var(--green); }

.onto-behavior { display: flex; flex-direction: column; gap: 5px; }
.onto-behavior-row {
  display: flex; gap: 8px; font-size: 11px; padding: 5px 7px;
  border-radius: var(--radius-xs); border-left: 2px solid var(--border-strong);
  background: var(--surface-soft); color: var(--text);
}
.onto-behavior-row.expected { border-left-color: var(--cyan); }
.onto-behavior-row.observed { border-left-color: var(--accent); background: rgba(232,163,61,0.05); }
.onto-behavior-tag { flex: 0 0 62px; color: var(--text3); font-size: 10px; }

.onto-edge-group { display: flex; flex-direction: column; gap: 3px; }
.onto-edge-label { font-size: 10px; color: var(--text3); }
.onto-edge-item {
  display: flex; align-items: center; gap: 6px; font-size: 11px;
  background: var(--surface-soft); border: 1px solid var(--border);
  border-radius: var(--radius-xs); padding: 3px 7px; cursor: pointer; color: var(--text2);
  text-align: left;
}
.onto-edge-item:hover { border-color: var(--border-accent); color: var(--text); }
.onto-edge-dot { width: 6px; height: 6px; border-radius: 50%; flex: none; }
.onto-edge-type { margin-left: auto; font-size: 9.5px; color: var(--text3); }

.findings-list { border-top: 1px solid var(--border); padding-top: 10px; }
.onto-sev-filter { display: flex; gap: 5px; flex-wrap: wrap; }
.onto-chip {
  display: inline-flex; align-items: center; gap: 5px;
  border: 1px solid var(--border); background: var(--surface); color: var(--text2);
  font-size: 10.5px; padding: 2px 8px; border-radius: 999px; cursor: pointer;
}
.onto-chip.active { border-color: var(--border-accent); background: var(--accent-soft); color: var(--accent-bright); }
.onto-sev-dot { width: 6px; height: 6px; border-radius: 50%; }
.onto-sev-dot.sev-critical { background: var(--red); }
.onto-sev-dot.sev-important { background: var(--yellow); }
.onto-sev-dot.sev-minor { background: var(--text3); }

.onto-finding {
  display: flex; flex-direction: column; gap: 3px;
  border: 1px solid var(--border); border-left-width: 2px;
  border-radius: var(--radius-xs); padding: 6px 8px; background: var(--surface-soft);
  text-align: left; width: 100%;
}
.onto-finding.clickable { cursor: pointer; font: inherit; }
.onto-finding.clickable:hover { border-color: var(--border-strong); background: var(--surface); }
.onto-finding.sev-critical { border-left-color: var(--red); }
.onto-finding.sev-important { border-left-color: var(--yellow); }
.onto-finding.sev-minor { border-left-color: var(--text3); }
.onto-finding-sev { font-size: 9.5px; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text3); }
.onto-finding-code { font-size: 10px; color: var(--accent); }
.onto-finding-msg { margin: 0; font-size: 11px; color: var(--text); line-height: 1.45; }
.onto-finding-hint { margin: 0; font-size: 10.5px; color: var(--text3); line-height: 1.45; }
.onto-finding-hint.dim { color: var(--text-dim); }
</style>
