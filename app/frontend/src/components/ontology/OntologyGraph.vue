<template>
  <div class="onto-graph">
    <div class="onto-graph-canvas" ref="canvasEl">
      <v-chart
        v-if="graph && graph.nodes && graph.nodes.length"
        ref="chartRef"
        class="onto-graph-chart"
        :option="option"
        :update-options="{ notMerge: true }"
        autoresize
        @click="onChartClick"
        @mouseover="onHover"
        @mouseout="onHoverOut"
      />
      <div v-else class="onto-graph-empty">
        <div class="onto-graph-empty-mark">◌</div>
        <p>{{ emptyText || $t('ontology.graph.empty') }}</p>
      </div>
    </div>

    <div class="onto-graph-legend">
      <div class="onto-legend-block">
        <div class="onto-legend-title">{{ t('ontology.graph.legendNodes') }}</div>
        <div class="onto-legend-items">
          <button
            v-for="c in graph.categories || []"
            :key="c.name"
            type="button"
            class="onto-legend-item"
            :class="{ dimmed: hiddenCategories.includes(c.name) }"
            :title="$t('ontology.graph.toggle')"
            @click="toggleCategory(c.name)"
          >
            <span class="onto-legend-swatch" :style="{ background: c.color, borderRadius: c.symbol === 'rect' ? '1px' : '50%' }"></span>
            <span>{{ c.label }}</span>
            <span class="onto-legend-count">{{ countByCategory(c.name) }}</span>
          </button>
        </div>
      </div>
      <div class="onto-legend-block">
        <div class="onto-legend-title">{{ t('ontology.graph.legendEdges') }}</div>
        <div class="onto-legend-items">
          <span v-for="e in edgeLegend" :key="e.type" class="onto-legend-item static">
            <span class="onto-legend-line" :style="{ background: e.color, height: `${e.width}px` }"></span>
            <span>{{ e.label }}</span>
          </span>
        </div>
        <div class="onto-legend-note">{{ t('ontology.graph.dashedNote') }}</div>
      </div>
    </div>

    <div class="onto-graph-toolbar">
      <div class="onto-toolbar-group">
        <span class="onto-toolbar-label">{{ t('ontology.graph.layout') }}</span>
        <button
          v-for="l in layouts"
          :key="l.key"
          type="button"
          class="onto-chip"
          :class="{ active: layout === l.key }"
          :title="l.hint"
          @click="layout = l.key"
        >{{ l.label }}</button>
      </div>
      <div class="onto-toolbar-group">
        <span class="onto-toolbar-label">{{ t('ontology.graph.layers') }}</span>
        <button
          type="button" class="onto-chip" :class="{ active: layers.structure }"
          :title="t('ontology.graph.layerStructureHint')"
          @click="$emit('update:layers', { ...layers, structure: !layers.structure })"
        >{{ t('ontology.graph.layerStructure') }}</button>
        <button
          type="button" class="onto-chip" :class="{ active: layers.relationships }"
          :title="t('ontology.graph.layerRelationshipHint')"
          @click="$emit('update:layers', { ...layers, relationships: !layers.relationships })"
        >{{ t('ontology.graph.layerRelationship') }}</button>
        <button
          type="button" class="onto-chip" :class="{ active: layers.knowledge }"
          :title="t('ontology.graph.layerKnowledgeHint')"
          @click="$emit('update:layers', { ...layers, knowledge: !layers.knowledge })"
        >{{ t('ontology.graph.layerKnowledge') }}</button>
      </div>
      <div class="onto-toolbar-group">
        <button type="button" class="onto-chip" :title="t('ontology.graph.fitHint')" @click="fit">{{ t('ontology.graph.fit') }}</button>
        <label class="onto-switch" :title="t('ontology.graph.labelsHint')">
          <input type="checkbox" v-model="showEdgeLabels" />
          <span>{{ t('ontology.graph.edgeLabels') }}</span>
        </label>
      </div>
    </div>

    <div v-if="graph && (graph.unresolved?.length || graph.orphan_signals?.length)" class="onto-graph-warnings">
      <span v-if="graph.unresolved?.length" class="onto-warn-chip" :title="unresolvedTitle">
        ⚠ {{ t('ontology.graph.dangling', { n: graph.unresolved.length }) }}
      </span>
      <span v-if="graph.orphan_signals?.length" class="onto-warn-chip" :title="orphanTitle">
        ⚠ {{ t('ontology.graph.orphans', { n: graph.orphan_signals.length }) }}
      </span>
      <span v-if="graph.unresolved_refs?.length" class="onto-warn-chip" :title="unresolvedRefTitle">
        ⚠ {{ t('ontology.graph.unresolvedRefs', { n: graph.unresolved_refs.length }) }}
      </span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue';
import { useI18n } from 'vue-i18n';
import VChart from 'vue-echarts';
import { use } from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import { GraphChart } from 'echarts/charts';
import { TooltipComponent, LegendComponent, TitleComponent } from 'echarts/components';

use([CanvasRenderer, GraphChart, TooltipComponent, LegendComponent, TitleComponent]);

const { t } = useI18n();

const props = defineProps({
  graph: { type: Object, default: () => ({ nodes: [], edges: [], categories: [] }) },
  layers: { type: Object, default: () => ({ structure: true, relationships: true, knowledge: false }) },
  selectedId: { type: String, default: '' },
  emptyText: { type: String, default: '' },
});
const emit = defineEmits(['select', 'update:layers']);

const chartRef = ref(null);
const canvasEl = ref(null);
const layout = ref('force');
const showEdgeLabels = ref(true);
const hiddenCategories = ref([]);
const hoveredId = ref('');

const layouts = computed(() => [
  { key: 'force', label: t('ontology.graph.layoutForce'), hint: t('ontology.graph.layoutForceHint') },
  { key: 'circular', label: t('ontology.graph.layoutCircular'), hint: t('ontology.graph.layoutCircularHint') },
  { key: 'none', label: t('ontology.graph.layoutNone'), hint: t('ontology.graph.layoutNoneHint') },
]);

const EDGE_LEGEND_TYPES = [
  { type: 'causal', key: 'ontology.graph.edgeCausal', color: '#f97362', width: 3 },
  { type: 'correlative', key: 'ontology.graph.edgeCorrelative', color: '#4ea8f5', width: 2 },
  { type: 'control', key: 'ontology.graph.edgeControl', color: '#31c9a8', width: 3 },
  { type: 'physical', key: 'ontology.graph.edgePhysical', color: '#c9a227', width: 3 },
];
const edgeLegend = computed(() => {
  const present = new Set((props.graph?.edges || []).filter((e) => e.relation === 'relationship').map((e) => e.type));
  const known = EDGE_LEGEND_TYPES.filter((e) => present.has(e.type));
  const list = known.length ? known : EDGE_LEGEND_TYPES;
  return list.map((e) => ({ ...e, label: t(e.key) }));
});

function countByCategory(name) {
  return (props.graph?.nodes || []).filter((n) => n.category === name).length;
}

function toggleCategory(name) {
  const i = hiddenCategories.value.indexOf(name);
  if (i >= 0) hiddenCategories.value.splice(i, 1);
  else hiddenCategories.value.push(name);
}

const unresolvedTitle = computed(() =>
  (props.graph?.unresolved || []).map((u) => `${u.from} → ${u.to} (${u.reason})`).join('\n'));
const orphanTitle = computed(() => (props.graph?.orphan_signals || []).join('\n'));
const unresolvedRefTitle = computed(() => (props.graph?.unresolved_refs || []).join('\n'));

// ── 邻接索引：选中/悬停时高亮邻居 ──
const adjacency = computed(() => {
  const map = new Map();
  for (const e of props.graph?.edges || []) {
    if (!map.has(e.source)) map.set(e.source, new Set());
    if (!map.has(e.target)) map.set(e.target, new Set());
    map.get(e.source).add(e.target);
    map.get(e.target).add(e.source);
  }
  return map;
});

const focusId = computed(() => hoveredId.value || props.selectedId || '');
const neighbors = computed(() => (focusId.value ? adjacency.value.get(focusId.value) || new Set() : null));

const visibleNodes = computed(() =>
  (props.graph?.nodes || []).filter((n) => !hiddenCategories.value.includes(n.category)));

const option = computed(() => {
  const g = props.graph || { nodes: [], edges: [] };
  const focus = focusId.value;
  const near = neighbors.value;
  const visibleIds = new Set(visibleNodes.value.map((n) => n.id));
  const catIndex = new Map((g.categories || []).map((c, i) => [c.name, i]));

  const nodes = visibleNodes.value.map((n) => {
    const dim = focus && n.id !== focus && !(near && near.has(n.id));
    const isFocus = n.id === focus;
    const isSignal = n.kind === 'signal';
    const baseSize = isSignal ? (n.role === 'target' ? 46 : 38) : 34;
    return {
      id: n.id,
      name: n.id,
      value: n.label || n.id,
      symbol: n.symbol || (n.category ? undefined : 'circle'),
      symbolSize: isFocus ? baseSize + 12 : baseSize,
      category: catIndex.get(n.category) ?? 0,
      itemStyle: {
        color: n.unresolved_ref ? 'transparent' : undefined,
        borderColor: n.unresolved_ref ? '#d45d3d' : (isFocus ? '#f4b65a' : 'rgba(0,0,0,0.45)'),
        borderWidth: n.unresolved_ref || isFocus ? 2.5 : 1,
        borderType: n.unresolved_ref ? 'dashed' : 'solid',
        opacity: dim ? 0.18 : 1,
        shadowBlur: isFocus ? 18 : 0,
        shadowColor: 'rgba(244,182,90,0.55)',
      },
      label: {
        show: true,
        position: 'bottom',
        distance: 6,
        formatter: () => shortNodeLabel(n),
        color: dim ? 'rgba(168,164,148,0.35)' : (isFocus ? '#f4b65a' : '#c9c4b2'),
        fontSize: isFocus ? 12 : 10.5,
        fontWeight: isFocus || n.role === 'target' ? 600 : 400,
        fontFamily: 'var(--font-mono)',
      },
      _raw: n,
    };
  });

  const links = (g.edges || [])
    .filter((e) => visibleIds.has(e.source) && visibleIds.has(e.target))
    .map((e) => {
      const dim = focus && e.source !== focus && e.target !== focus;
      const isRel = e.relation === 'relationship';
      return {
        source: e.source,
        target: e.target,
        value: e.label || '',
        lineStyle: {
          color: e.color,
          width: e.width || 1.5,
          type: e.dashed ? 'dashed' : 'solid',
          opacity: dim ? 0.08 : (isRel ? 0.92 : 0.42),
          curveness: isRel ? 0.14 : 0.06,
        },
        symbol: e.arrow ? ['none', 'arrow'] : ['none', 'none'],
        symbolSize: e.arrow ? [0, 7] : [0, 0],
        label: {
          show: showEdgeLabels.value && isRel,
          formatter: e.label || '',
          fontSize: 9,
          color: dim ? 'rgba(168,164,148,0.15)' : e.color,
          fontFamily: 'var(--font-mono)',
        },
        _raw: e,
      };
    });

  return {
    backgroundColor: 'transparent',
    animationDuration: 420,
    animationEasingUpdate: 'cubicOut',
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(20,21,15,0.96)',
      borderColor: 'rgba(237,232,216,0.13)',
      borderWidth: 1,
      padding: [8, 10],
      textStyle: { color: '#ede8d8', fontSize: 11.5, fontFamily: 'var(--font-ui)' },
      formatter: tooltipFormatter,
    },
    legend: { show: false },
    series: [{
      type: 'graph',
      layout: layout.value,
      roam: true,
      draggable: true,
      focusNodeAdjacency: false,
      categories: (g.categories || []).map((c) => ({
        name: c.name,
        itemStyle: { color: c.color },
        symbol: c.symbol || 'circle',
      })),
      force: {
        repulsion: Math.max(180, 2600 / Math.max(1, Math.sqrt(nodes.length))),
        gravity: 0.06,
        edgeLength: [70, 170],
        layoutAnimation: nodes.length <= 160,
        friction: 0.14,
      },
      circular: { rotateLabel: false },
      edgeSymbolSize: 7,
      labelLayout: { hideOverlap: true },
      emphasis: {
        focus: 'adjacency',
        scale: 1.12,
        lineStyle: { width: 3.4, opacity: 1 },
        label: { fontSize: 12.5, color: '#f4b65a' },
      },
      blur: { itemStyle: { opacity: 0.12 }, lineStyle: { opacity: 0.05 }, label: { opacity: 0.12 } },
      data: nodes,
      links,
    }],
  };
});

function shortNodeLabel(n) {
  const raw = n._raw || {};
  const text = String(raw.label || n.value || n.id);
  const firstLine = text.split('\n')[0];
  return firstLine.length > 22 ? `${firstLine.slice(0, 21)}…` : firstLine;
}

function tooltipFormatter(params) {
  if (params.dataType === 'edge') {
    const e = params.data._raw || {};
    const rows = [`<b style="color:${e.color}">${e.label || e.type || '关系'}</b>`];
    rows.push(`<span style="color:#a8a494">${e.source} → ${e.target}</span>`);
    const d = e.detail || {};
    if (d.mechanism) rows.push(`<div style="max-width:320px;white-space:normal;margin-top:4px">${escapeHtml(d.mechanism)}</div>`);
    if (d.governing_equation) rows.push(`<code style="color:#c9a227">${escapeHtml(d.governing_equation)}</code>`);
    if (d.inferred) rows.push('<span style="color:#a8a494">inferred: true（未做数据方向验证）</span>');
    return rows.join('<br/>');
  }
  const n = params.data._raw || {};
  const d = n.detail || {};
  const rows = [`<b style="color:#f4b65a">${escapeHtml(n.id)}</b>`];
  if (n.role) rows.push(`<span style="color:#a8a494">role: ${n.role}${n.bucket ? ` · ${n.bucket}` : ''}</span>`);
  if (n.kind && n.kind !== 'signal') rows.push(`<span style="color:#a8a494">${n.kind}</span>`);
  if (d.unit) rows.push(`unit: ${escapeHtml(d.unit)}`);
  if (d.physical_meaning) rows.push(`<div style="max-width:320px;white-space:normal;margin-top:4px">${escapeHtml(d.physical_meaning)}</div>`);
  if (n.degree !== undefined) rows.push(`<span style="color:#6c6a5e">degree ${n.degree}</span>`);
  rows.push('<span style="color:#6c6a5e;font-size:10px">点击查看/编辑详情</span>');
  return rows.join('<br/>');
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[c]));
}

function onChartClick(params) {
  const raw = params?.data?._raw;
  if (!raw) return;
  if (params.dataType === 'edge') emit('select', { kind: 'edge', data: raw });
  else emit('select', { kind: 'node', data: raw });
}

let hoverTimer = null;
function onHover(params) {
  if (hoverTimer) { clearTimeout(hoverTimer); hoverTimer = null; }
  const id = params?.data?._raw?.id;
  if (params?.dataType === 'node' && id) hoveredId.value = id;
}
function onHoverOut() {
  hoverTimer = setTimeout(() => { hoveredId.value = ''; }, 60);
}

function fit() {
  // ECharts graph 的 roam 缩放没有公开的 fit API；用 notMerge 重绘重置视图。
  nextTick(() => {
    const chart = chartRef.value;
    if (!chart) return;
    const inst = chart.chart || chart;
    if (typeof inst?.dispatchAction === 'function') {
      inst.dispatchAction({ type: 'restore' });
    }
  });
}

watch(() => props.graph, () => { hiddenCategories.value = []; }, { deep: false });

onMounted(() => { /* chart 自动挂载 */ });
onUnmounted(() => { if (hoverTimer) clearTimeout(hoverTimer); });
</script>

<style scoped>
.onto-graph {
  display: flex;
  flex-direction: column;
  min-height: 0;
  height: 100%;
  gap: 8px;
}
.onto-graph-canvas {
  position: relative;
  flex: 1;
  min-height: 320px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background:
    radial-gradient(circle at 50% 45%, rgba(232, 163, 61, 0.045), transparent 62%),
    var(--surface-soft);
  overflow: hidden;
}
.onto-graph-chart { width: 100%; height: 100%; }
.onto-graph-empty {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: var(--text3);
  font-size: 12.5px;
}
.onto-graph-empty-mark { font-size: 34px; opacity: 0.4; }

.onto-graph-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 18px;
  padding: 8px 10px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface);
}
.onto-legend-block { display: flex; flex-direction: column; gap: 5px; }
.onto-legend-title {
  font-size: 10px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text3);
}
.onto-legend-items { display: flex; flex-wrap: wrap; gap: 6px 12px; align-items: center; }
.onto-legend-item {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  color: var(--text2);
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
}
.onto-legend-item.static { cursor: default; }
.onto-legend-item.dimmed { opacity: 0.34; text-decoration: line-through; }
.onto-legend-swatch { width: 10px; height: 10px; flex: none; }
.onto-legend-line { width: 18px; border-radius: 2px; flex: none; }
.onto-legend-count {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--text3);
}
.onto-legend-note { font-size: 10px; color: var(--text-dim); }

.onto-graph-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  align-items: center;
}
.onto-toolbar-group { display: flex; align-items: center; gap: 5px; }
.onto-toolbar-label {
  font-size: 10px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text3);
  margin-right: 2px;
}
.onto-chip {
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text2);
  font-size: 11px;
  padding: 3px 9px;
  border-radius: 999px;
  cursor: pointer;
  transition: all 0.14s ease;
}
.onto-chip:hover { border-color: var(--border-strong); color: var(--text); }
.onto-chip.active {
  border-color: var(--border-accent);
  background: var(--accent-soft);
  color: var(--accent-bright);
}
.onto-switch {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  color: var(--text2);
  cursor: pointer;
}
.onto-switch input { accent-color: var(--accent); }

.onto-graph-warnings { display: flex; flex-wrap: wrap; gap: 8px; }
.onto-warn-chip {
  font-size: 10.5px;
  font-family: var(--font-mono);
  color: var(--yellow);
  background: rgba(212, 169, 61, 0.1);
  border: 1px solid rgba(212, 169, 61, 0.3);
  border-radius: var(--radius-xs);
  padding: 2px 7px;
  cursor: help;
}
</style>
