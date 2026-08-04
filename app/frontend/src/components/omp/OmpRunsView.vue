<template>
  <div class="omp-view">
    <!-- ── Header ── -->
    <div class="omp-header">
      <div class="omp-header-copy">
        <div class="omp-header-kicker">Harness Bridge · {{ harnessName }}</div>
        <h2 class="omp-header-title">{{ harnessName }} 原生运行 · 只读浏览</h2>
        <p class="omp-header-sub">
          通过 Harness 接口读取 <code>{{ runsDirLabel }}</code> 中由 {{ harnessName }} 产出的原生分析结果——基线产物、增强深挖、事件执行证明。
        </p>
      </div>
      <div class="omp-header-meta">
        <button class="btn btn-sm" :disabled="loading" @click="load()">
          {{ loading ? '扫描中…' : '⟳ 刷新' }}
        </button>
        <span class="omp-engine-pill" :class="{ off: !health.available }">
          <span class="omp-engine-dot" />
          {{ health.available ? `${harnessName} 在线 · ${health.run_count ?? health.meta?.run_count ?? 0} 个运行` : `${harnessName} 不可用` }}
        </span>
      </div>
    </div>

    <!-- ── Stats row ── -->
    <div v-if="runs.length" class="omp-stats">
      <div class="omp-stat"><span class="omp-stat-num">{{ runs.length }}</span><span class="omp-stat-label">总运行</span></div>
      <div class="omp-stat"><span class="omp-stat-num">{{ completedCount }}</span><span class="omp-stat-label">已完成（ENDORSED）</span></div>
      <div class="omp-stat"><span class="omp-stat-num">{{ enhancedCount }}</span><span class="omp-stat-label">增强完成</span></div>
      <div class="omp-stat"><span class="omp-stat-num">{{ withHtmlCount }}</span><span class="omp-stat-label">HTML 报告</span></div>
    </div>

    <!-- ── Run list ── -->
    <div v-if="loading" class="empty-state"><div class="spinner" /> 正在读取 OMP 运行目录…</div>

    <div v-else-if="error" class="omp-error">{{ error }}</div>

    <div v-else-if="!runs.length" class="empty-state">
      <p>未发现 OMP 运行。请先通过 <code>enhance_orchestrator.mjs</code> 或 OMP 代理管线执行一次诊断。</p>
    </div>

    <div v-else class="omp-run-list">
      <div
        v-for="run in runs"
        :key="run.name"
        class="omp-run-card"
        :class="{ open: selected === run.name }"
        @click="toggleRun(run.name)"
      >
        <div class="omp-run-card-head">
          <div class="omp-run-badges">
            <span class="omp-status" :class="statusClass(run)">{{ statusText(run) }}</span>
            <span v-if="run.verdict" class="badge" :class="verdictClass(run.verdict)">{{ run.verdict }}</span>
            <span v-if="run.enhancement_status" class="badge" :class="enhClass(run.enhancement_status)">
              E:{{ run.enhancement_status.replace('READY', 'R').replace('_WITH_WARNINGS', '±') }}
            </span>
          </div>
          <div class="omp-run-meta">
            <span>{{ formatTime(run.created) }}</span>
            <span>· {{ run.artifact_count }} 产物</span>
            <span>· {{ run.agents.length || 0 }} 代理</span>
          </div>
        </div>
        <div class="omp-run-title">{{ run.display_name }}</div>
        <div class="omp-run-name"><code>{{ run.name }}</code></div>

        <!-- ── Detail panel ── -->
        <div v-if="selected === run.name" class="omp-run-detail" @click.stop>
          <OmpRunDetail :name="run.name" :harness-id="harnessId" :harness-name="harnessName" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { api } from '../../api/index.js';
import OmpRunDetail from './OmpRunDetail.vue';

const props = defineProps({
  harnessId: { type: String, default: 'omp' },
  harnessName: { type: String, default: 'OMP Engine' },
});

const runs = ref([]);
const loading = ref(false);
const error = ref('');
const selected = ref(null);
const health = ref({ available: false, run_count: 0 });
const runsDirLabel = computed(() => {
  const dir = health.value.meta?.runs_dir || '';
  return dir.includes('diagnostic-runs') ? 'workspace/diagnostic-runs/' : (dir || '运行目录');
});

const completedCount = computed(() => runs.value.filter((r) => r.verdict === 'ENDORSED').length);
const enhancedCount = computed(() => runs.value.filter((r) => r.enhancement_status).length);
const withHtmlCount = computed(() => runs.value.filter((r) => r.has_html).length);

function statusClass(run) {
  if (run.baseline_status === 'completed') return 'st-completed';
  if (run.baseline_status === 'report_ready') return 'st-report';
  if (run.baseline_status === 'diagnosed') return 'st-diagnosed';
  if (run.baseline_status === 'in_progress') return 'st-progress';
  return 'st-init';
}

function statusText(run) {
  const map = {
    completed: '完成', report_ready: '报告就绪', diagnosed: '已诊断',
    in_progress: '执行中', initialized: '已初始化', unknown: '未知',
  };
  return map[run.baseline_status] || run.baseline_status;
}

function verdictClass(v) {
  return { ENDORSED: 'badge-green', CONDITIONAL: 'badge-yellow', REJECTED: 'badge-red' }[v] || 'badge-blue';
}

function enhClass(s) {
  if (!s) return 'badge-blue';
  if (s === 'READY') return 'badge-green';
  if (s === 'READY_WITH_WARNINGS') return 'badge-yellow';
  return 'badge-red';
}

function formatTime(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
}

async function load() {
  loading.value = true;
  error.value = '';
  try {
    const [h, r] = await Promise.all([api.harnessHealth(props.harnessId), api.harnessRuns(props.harnessId)]);
    health.value = h;
    runs.value = r;
  } catch (e) {
    error.value = `${props.harnessName} 桥接失败：${e.message}`;
  } finally {
    loading.value = false;
  }
}

function toggleRun(name) {
  selected.value = selected.value === name ? null : name;
}

onMounted(load);
</script>
