<template>
  <div class="onto-diff">
    <div class="onto-diff-picker">
      <label class="onto-field">
        <span>{{ $t('ontology.diff.from') }}</span>
        <select :value="fromVersion" @change="$emit('update:fromVersion', Number($event.target.value))">
          <option v-for="v in versions" :key="`f-${v}`" :value="v">v{{ v }}</option>
        </select>
      </label>
      <span class="onto-diff-arrow">→</span>
      <label class="onto-field">
        <span>{{ $t('ontology.diff.to') }}</span>
        <select :value="toVersion" @change="$emit('update:toVersion', Number($event.target.value))">
          <option v-for="v in versions" :key="`t-${v}`" :value="v">v{{ v }}</option>
        </select>
      </label>
    </div>

    <p v-if="!diff" class="onto-empty">{{ $t('ontology.diff.empty') }}</p>

    <template v-else>
      <div v-if="diff.summary.structurally_identical" class="onto-diff-identical">
        ✓ {{ diff.summary.identical ? $t('ontology.diff.identical') : $t('ontology.diff.structurallyIdentical') }}
      </div>

      <div class="onto-diff-summary" v-else>
        <div v-for="c in summaryCards" :key="c.key" class="onto-diff-card" :class="{ zero: !c.value }">
          <span class="onto-diff-card-num">{{ c.value }}</span>
          <span class="onto-diff-card-label">{{ c.label }}</span>
        </div>
      </div>

      <div v-for="section in changedSections" :key="section.label" class="onto-diff-section">
        <h5>{{ section.label }}</h5>

        <div v-if="section.added.length" class="onto-diff-group">
          <span class="onto-diff-tag added">+ {{ $t('ontology.diff.added') }} ({{ section.added.length }})</span>
          <span v-for="k in section.added" :key="`a-${k}`" class="onto-diff-key mono">{{ k }}</span>
        </div>

        <div v-if="section.removed.length" class="onto-diff-group">
          <span class="onto-diff-tag removed">− {{ $t('ontology.diff.removed') }} ({{ section.removed.length }})</span>
          <span v-for="k in section.removed" :key="`r-${k}`" class="onto-diff-key mono">{{ k }}</span>
        </div>

        <div v-if="section.changed.length" class="onto-diff-group column">
          <span class="onto-diff-tag changed">~ {{ $t('ontology.diff.changed') }} ({{ section.changed.length }})</span>
          <div v-for="c in section.changed" :key="`c-${c.key}`" class="onto-diff-change">
            <div class="onto-diff-change-head mono">{{ c.key }}</div>
            <table class="onto-diff-table">
              <tbody>
                <tr v-for="(f, fi) in c.fields" :key="`cf-${fi}`">
                  <td class="path mono">{{ f.path }}</td>
                  <td class="before">{{ fmt(f.before) }}</td>
                  <td class="after">{{ fmt(f.after) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div v-if="diff.scene.length" class="onto-diff-section">
        <h5>{{ $t('ontology.diff.sceneFields') }}</h5>
        <table class="onto-diff-table">
          <tbody>
            <tr v-for="(f, i) in diff.scene" :key="`s-${i}`">
              <td class="path mono">{{ f.path }}</td>
              <td class="before">{{ fmt(f.before) }}</td>
              <td class="after">{{ fmt(f.after) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="diff.metadata.length" class="onto-diff-section">
        <h5>{{ $t('ontology.diff.metadataFields') }}</h5>
        <table class="onto-diff-table">
          <tbody>
            <tr v-for="(f, i) in diff.metadata" :key="`m-${i}`">
              <td class="path mono">{{ f.path }}</td>
              <td class="before">{{ fmt(f.before) }}</td>
              <td class="after">{{ fmt(f.after) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();

const props = defineProps({
  diff: { type: Object, default: null },
  versions: { type: Array, default: () => [] },
  fromVersion: { type: Number, default: 1 },
  toVersion: { type: Number, default: 1 },
});
defineEmits(['update:fromVersion', 'update:toVersion']);

const summaryCards = computed(() => {
  const s = props.diff?.summary || {};
  return [
    { key: 'sa', value: s.signals_added, label: t('ontology.diff.signalsAdded') },
    { key: 'sr', value: s.signals_removed, label: t('ontology.diff.signalsRemoved') },
    { key: 'sc', value: s.signals_changed, label: t('ontology.diff.signalsChanged') },
    { key: 'ra', value: s.relationships_added, label: t('ontology.diff.relationshipsAdded') },
    { key: 'rr', value: s.relationships_removed, label: t('ontology.diff.relationshipsRemoved') },
    { key: 'rc', value: s.relationships_changed, label: t('ontology.diff.relationshipsChanged') },
  ];
});

const changedSections = computed(() =>
  (props.diff?.sections || []).filter(
    (s) => s.added.length || s.removed.length || s.changed.length,
  ));

function fmt(v) {
  if (v === null || v === undefined) return '—';
  if (typeof v === 'object') return JSON.stringify(v);
  const s = String(v);
  return s.length > 160 ? `${s.slice(0, 157)}…` : s;
}
</script>

<style scoped>
.onto-diff { display: flex; flex-direction: column; gap: 12px; overflow-y: auto; height: 100%; padding-right: 4px; }
.onto-diff-picker { display: flex; align-items: flex-end; gap: 10px; flex-wrap: wrap; }
.onto-diff-picker .onto-field { min-width: 120px; }
.onto-field { display: flex; flex-direction: column; gap: 3px; }
.onto-field > span { font-size: 10px; text-transform: uppercase; letter-spacing: 0.04em; color: var(--text3); }
.onto-field select {
  background: var(--surface-soft); border: 1px solid var(--border); border-radius: var(--radius-xs);
  color: var(--text); font-size: 12px; padding: 4px 7px;
}
.onto-diff-arrow { color: var(--text3); padding-bottom: 5px; }
.onto-diff-identical {
  font-size: 12px; color: var(--green); border: 1px solid rgba(143,191,106,0.3);
  background: rgba(143,191,106,0.07); border-radius: var(--radius); padding: 9px 12px;
}
.onto-diff-summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(110px, 1fr)); gap: 7px; }
.onto-diff-card {
  border: 1px solid var(--border); border-radius: var(--radius); padding: 8px 10px;
  background: var(--surface); display: flex; flex-direction: column; gap: 2px;
}
.onto-diff-card.zero { opacity: 0.42; }
.onto-diff-card-num { font-family: var(--font-display); font-size: 20px; color: var(--accent-bright); line-height: 1; }
.onto-diff-card-label { font-size: 10px; color: var(--text3); }

.onto-diff-section { display: flex; flex-direction: column; gap: 7px; }
.onto-diff-section h5 {
  margin: 0; font-size: 11px; letter-spacing: 0.05em; text-transform: uppercase; color: var(--text2);
  border-bottom: 1px solid var(--border); padding-bottom: 5px;
}
.onto-diff-group { display: flex; flex-wrap: wrap; gap: 5px; align-items: center; }
.onto-diff-group.column { flex-direction: column; align-items: stretch; }
.onto-diff-tag {
  font-size: 10px; font-family: var(--font-mono); padding: 1px 7px; border-radius: 999px;
  border: 1px solid var(--border-strong); flex: none;
}
.onto-diff-tag.added { color: var(--green); border-color: rgba(143,191,106,0.4); }
.onto-diff-tag.removed { color: var(--red); border-color: rgba(212,93,61,0.4); }
.onto-diff-tag.changed { color: var(--yellow); border-color: rgba(212,169,61,0.4); }
.onto-diff-key {
  font-size: 10.5px; background: var(--surface-soft); border: 1px solid var(--border);
  border-radius: var(--radius-xs); padding: 1px 6px; color: var(--text2);
}
.onto-diff-change { border: 1px solid var(--border); border-radius: var(--radius-xs); overflow: hidden; }
.onto-diff-change-head {
  font-size: 11px; padding: 4px 8px; background: var(--surface); color: var(--accent);
  border-bottom: 1px solid var(--border);
}
.onto-diff-table { width: 100%; border-collapse: collapse; font-size: 11px; }
.onto-diff-table td { padding: 3px 8px; border-bottom: 1px solid var(--border); vertical-align: top; }
.onto-diff-table tr:last-child td { border-bottom: none; }
.onto-diff-table .path { color: var(--text3); font-size: 10px; width: 34%; word-break: break-all; }
.onto-diff-table .before { color: var(--red); text-decoration: line-through; opacity: 0.75; width: 33%; word-break: break-word; }
.onto-diff-table .after { color: var(--green); width: 33%; word-break: break-word; }
.onto-empty { font-size: 11.5px; color: var(--text3); }
</style>
