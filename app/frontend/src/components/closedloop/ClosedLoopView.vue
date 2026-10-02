<template>
  <div class="cl-view">
    <header class="cl-head">
      <div class="cl-head-text">
        <p class="cl-kicker">{{ $t('tabs.closedloop.kicker') }}</p>
        <h2 class="cl-title">{{ $t('tabs.closedloop.title') }}</h2>
        <p class="cl-desc">{{ $t('tabs.closedloop.description') }}</p>
      </div>
      <button type="button" class="cl-btn ghost" :title="$t('closedloop.common.refresh')" @click="reloadKey++">⟳</button>
    </header>

    <nav class="cl-subtabs">
      <button
        v-for="key in subtabs" :key="key" type="button"
        :class="['cl-subtab', { active: subtab === key }]"
        @click="subtab = key"
      >{{ $t(`closedloop.subtabs.${key}`) }}</button>
    </nav>

    <SentinelPanel v-if="subtab === 'sentinel'" :key="`s-${reloadKey}`" />
    <ExperiencePanel v-else-if="subtab === 'experience'" :key="`e-${reloadKey}`" />
    <OptimizerPanel v-else :key="`o-${reloadKey}`" />
  </div>
</template>

<script setup>
import { ref } from 'vue';
import SentinelPanel from './SentinelPanel.vue';
import ExperiencePanel from './ExperiencePanel.vue';
import OptimizerPanel from './OptimizerPanel.vue';

const subtabs = ['sentinel', 'experience', 'optimizer'];
const subtab = ref('sentinel');
const reloadKey = ref(0);
</script>

<style scoped>
.cl-view {
  display: flex;
  flex-direction: column;
  gap: 14px;
  height: 100%;
  overflow-y: auto;
  padding: 18px 22px 26px;
}
.cl-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}
.cl-kicker {
  margin: 0 0 2px;
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--accent);
}
.cl-title {
  margin: 0 0 6px;
  font-family: var(--font-display);
  font-size: 26px;
  font-weight: 600;
  color: var(--text);
}
.cl-desc {
  margin: 0;
  max-width: 720px;
  font-size: 13px;
  line-height: 1.55;
  color: var(--text3);
}
.cl-subtabs {
  display: flex;
  gap: 8px;
  border-bottom: 1px solid var(--border);
  padding-bottom: 0;
}
.cl-subtab {
  appearance: none;
  border: 1px solid transparent;
  border-bottom: none;
  background: transparent;
  color: var(--text3);
  font-family: var(--font-ui);
  font-size: 13px;
  padding: 8px 16px;
  cursor: pointer;
  border-radius: 8px 8px 0 0;
  position: relative;
  top: 1px;
}
.cl-subtab:hover { color: var(--text2); }
.cl-subtab.active {
  background: var(--surface);
  border-color: var(--border);
  color: var(--accent);
  font-weight: 600;
}
</style>

<style>
/* ── shared closed-loop console styles (cl- prefix, used by the 3 panels) ── */
.cl-panel { display: flex; flex-direction: column; gap: 16px; }
.cl-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 14px 16px 16px;
}
.cl-card h3 {
  margin: 0 0 4px;
  font-family: var(--font-ui);
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
}
.cl-card .cl-card-desc {
  margin: 0 0 12px;
  font-size: 12px;
  line-height: 1.5;
  color: var(--text3);
}
.cl-form {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
  gap: 10px 12px;
  align-items: end;
}
.cl-field { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.cl-field label {
  font-family: var(--font-mono);
  font-size: 10.5px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text3);
}
.cl-field input,
.cl-field select,
.cl-field textarea {
  background: var(--surface-soft);
  border: 1px solid var(--border-strong);
  border-radius: 6px;
  color: var(--text);
  font-family: var(--font-mono);
  font-size: 12px;
  padding: 7px 9px;
  width: 100%;
  box-sizing: border-box;
}
.cl-field textarea { resize: vertical; min-height: 84px; line-height: 1.5; }
.cl-field input:focus,
.cl-field select:focus,
.cl-field textarea:focus { outline: none; border-color: var(--border-accent); }
.cl-btn {
  appearance: none;
  border: 1px solid var(--border-accent);
  background: var(--accent-soft);
  color: var(--accent-bright);
  font-family: var(--font-ui);
  font-size: 12.5px;
  font-weight: 600;
  padding: 8px 16px;
  border-radius: 6px;
  cursor: pointer;
  white-space: nowrap;
}
.cl-btn:hover:not(:disabled) { background: var(--accent-soft-strong); }
.cl-btn:disabled { opacity: 0.45; cursor: not-allowed; }
.cl-btn.ghost {
  border-color: var(--border-strong);
  background: transparent;
  color: var(--text3);
}
.cl-btn.small { padding: 5px 10px; font-size: 11.5px; }
.cl-note { font-size: 11.5px; color: var(--text3); line-height: 1.5; margin: 8px 0 0; }
.cl-alert {
  display: flex;
  align-items: center;
  gap: 10px;
  border: 1px solid var(--border-strong);
  border-left: 3px solid var(--accent);
  border-radius: 6px;
  padding: 8px 12px;
  font-size: 12.5px;
  color: var(--text2);
  background: var(--surface-soft);
}
.cl-alert.error { border-left-color: #e05d4a; color: #f0b9ad; }
.cl-alert.ok { border-left-color: #7fb069; color: #c9d8b8; }
.cl-kv {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 14px;
  font-family: var(--font-mono);
  font-size: 11.5px;
  color: var(--text2);
}
.cl-kv b { color: var(--text); font-weight: 600; }
.cl-pill {
  display: inline-block;
  font-family: var(--font-mono);
  font-size: 10.5px;
  padding: 1px 8px;
  border-radius: 999px;
  border: 1px solid var(--border-strong);
  color: var(--text2);
}
.cl-pill.critical, .cl-pill.high { border-color: rgba(224, 93, 74, 0.5); color: #f0a99b; }
.cl-pill.medium, .cl-pill.warn { border-color: rgba(232, 163, 61, 0.5); color: var(--accent-bright); }
.cl-pill.low, .cl-pill.info, .cl-pill.ok { border-color: rgba(127, 176, 105, 0.5); color: #a9c795; }
.cl-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.cl-table th {
  text-align: left;
  font-family: var(--font-mono);
  font-size: 10.5px;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--text3);
  border-bottom: 1px solid var(--border-strong);
  padding: 6px 8px;
}
.cl-table td {
  padding: 6px 8px;
  border-bottom: 1px solid var(--border);
  color: var(--text2);
  font-family: var(--font-mono);
  font-size: 11.5px;
}
.cl-table td.strong { color: var(--text); }
.cl-empty { font-size: 12px; color: var(--text-dim); padding: 10px 4px; }
.cl-pre {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 10px 12px;
  font-family: var(--font-mono);
  font-size: 11px;
  line-height: 1.55;
  color: var(--text2);
  overflow-x: auto;
  max-height: 300px;
  white-space: pre-wrap;
  word-break: break-all;
}
.cl-grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
@media (max-width: 1100px) { .cl-grid-2 { grid-template-columns: 1fr; } }
</style>
