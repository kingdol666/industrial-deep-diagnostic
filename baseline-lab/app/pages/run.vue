<script setup>
// 02 — Run baselines.
const { data: state } = await useFetch('/api/state', { key: 'lab-state' });

const selectedAlgos = ref([]);
const selectedCases = ref([]);
const job = ref(null);
const poll = ref(null);
const busy = ref(false);
const errorMsg = ref('');

// Sensible default: the deterministic algorithms that need no provider.
onMounted(() => {
  const all = state.value?.algorithms || [];
  selectedAlgos.value = all.filter((a) => !a.requiresProvider).map((a) => a.id);
  selectedCases.value = (state.value?.cases || []).map((c) => c.case_id);
});

const groups = computed(() => {
  const fams = state.value?.families || {};
  const out = {};
  for (const a of state.value?.algorithms || []) {
    out[a.family] = out[a.family] || { label: fams[a.family] || a.family, items: [] };
    out[a.family].items.push(a);
  }
  return out;
});

const anyNeedsProvider = computed(() =>
  (state.value?.algorithms || []).some((a) => selectedAlgos.value.includes(a.id) && a.requiresProvider),
);
const providerAvailable = computed(() => Boolean(state.value?.resolved_provider));

const totalRuns = computed(() => selectedAlgos.value.length * selectedCases.value.length);
const pct = computed(() => (job.value?.total ? Math.round((job.value.done / job.value.total) * 100) : 0));

function toggleAll(family, on) {
  const ids = groups.value[family].items.map((a) => a.id);
  const set = new Set(selectedAlgos.value);
  ids.forEach((id) => (on ? set.add(id) : set.delete(id)));
  selectedAlgos.value = [...set];
}
function familyState(family) {
  const ids = groups.value[family].items.map((a) => a.id);
  const on = ids.filter((id) => selectedAlgos.value.includes(id)).length;
  return on === 0 ? 'none' : on === ids.length ? 'all' : 'some';
}

async function start() {
  errorMsg.value = '';
  busy.value = true;
  job.value = null;
  if (poll.value) clearInterval(poll.value);
  try {
    const res = await $fetch('/api/run', {
      method: 'POST',
      body: { algorithms: selectedAlgos.value, cases: selectedCases.value, label: 'ui' },
    });
    job.value = { job_id: res.job_id, done: 0, total: res.total, state: 'running', log: [], live: {} };
    poll.value = setInterval(async () => {
      try {
        const s = await $fetch(`/api/run/${res.job_id}`);
        job.value = s;
        if (s.state !== 'running') {
          clearInterval(poll.value);
          poll.value = null;
          busy.value = false;
        }
      } catch (e) {
        clearInterval(poll.value);
        poll.value = null;
        busy.value = false;
        errorMsg.value = String(e?.data?.statusMessage || e.message);
      }
    }, 900);
  } catch (e) {
    busy.value = false;
    errorMsg.value = String(e?.data?.statusMessage || e.message);
  }
}

onBeforeUnmount(() => poll.value && clearInterval(poll.value));

const outcomeLabel = {
  hit: 'HIT', miss: 'miss', abstain: 'abstain',
  'control-pass': 'control-pass', 'FALSE-ALARM': 'FALSE-ALARM',
  skipped_no_provider: 'skipped', error: 'ERROR', not_applicable: 'n/a',
};
</script>

<template>
  <div>
    <div class="page-head">
      <h1>运行基线 · Run</h1>
      <p>
        选择算法 × 场景，真实执行并即时评分。确定性算法在进程内离线跑完；LLM 算法通过已解析的 provider
        发起<strong>真实调用</strong>——若 provider 不可用，会如实记为 <code>skipped_no_provider</code> 而绝不编造答案。
      </p>
    </div>

    <div v-if="anyNeedsProvider && !providerAvailable" class="callout warn">
      <strong>注意：</strong>所选算法包含需要 LLM provider 的项目，但当前未检测到可用 provider。
      这些项会被记为 <code>skipped_no_provider</code> 并给出空结论。启动前可设置
      <code>BASELINE_LLM_PROVIDER</code> / <code>BASELINE_LLM_API_KEY</code>，
      或直接使用本机已安装的 harness CLI（如 <code>cli:claude</code>、<code>cli:dsh</code>）。
    </div>

    <div v-if="anyNeedsProvider && state?.comparability?.status === 'different_model'" class="callout bad">
      <strong>可比性告警（模型混淆）：</strong>
      仓库归档的 LLM 基线由
      <code>{{ state.comparability.archived?.model || '未知模型' }}</code> 产生，
      而本实验室将调用 <code>{{ state.comparability.lab_model }}</code>。
      两者<strong>不是同一模型</strong>，因此本次 LLM 基线的数字
      <strong>不能与 <code>results/benchmark/baselines.json</code> 直接比较</strong>——
      这是一个新模型上的新实验。若要与归档结果对齐，请通过
      <code>BASELINE_LLM_MODEL</code> / <code>BASELINE_LLM_PROVIDER</code> 指回原模型。
    </div>

    <div class="grid g2">
      <!-- algorithms -->
      <div class="panel">
        <h2>
          算法
          <span class="badge info">{{ selectedAlgos.length }} selected</span>
        </h2>
        <p class="panel-sub">按族选择；同一族内可单独勾选。</p>

        <div v-for="(g, fam) in groups" :key="fam" style="margin-bottom: 12px">
          <div class="toolbar" style="margin-bottom: 4px">
            <strong class="small">{{ g.label }}</strong>
            <span class="tiny muted mono">{{ g.items.length }}</span>
            <span class="spacer" />
            <button class="ghost tiny" style="padding: 2px 8px" @click="toggleAll(fam, familyState(fam) !== 'all')">
              {{ familyState(fam) === 'all' ? '取消全选' : '全选' }}
            </button>
          </div>
          <div style="display: flex; flex-direction: column; gap: 4px">
            <label v-for="a in g.items" :key="a.id" class="row">
              <input type="checkbox" :value="a.id" v-model="selectedAlgos" />
              <span class="mono tiny" style="min-width: 108px; color: var(--ink-dim)">{{ a.id }}</span>
              <span class="small">{{ a.label }}</span>
              <span v-if="a.requiresProvider" class="badge violet tiny">LLM</span>
              <span v-else class="badge ok tiny">offline</span>
              <span v-if="a.domains" class="badge tiny">{{ a.domains.join('/') }}</span>
            </label>
          </div>
        </div>
      </div>

      <!-- cases -->
      <div class="panel">
        <h2>
          场景
          <span class="badge info">{{ selectedCases.length }} / {{ state?.cases?.length || 0 }}</span>
        </h2>
        <p class="panel-sub">12 个场景 = 9 故障 + 3 正常对照。对照组用于度量误报。</p>
        <div class="toolbar">
          <button class="ghost" style="padding: 2px 8px" @click="selectedCases = (state?.cases || []).map((c) => c.case_id)">
            全选
          </button>
          <button class="ghost" style="padding: 2px 8px" @click="selectedCases = (state?.cases || []).filter((c) => !c.control).map((c) => c.case_id)">
            仅故障
          </button>
          <button class="ghost" style="padding: 2px 8px" @click="selectedCases = (state?.cases || []).filter((c) => c.control).map((c) => c.case_id)">
            仅对照
          </button>
          <button class="ghost" style="padding: 2px 8px" @click="selectedCases = (state?.cases || []).filter((c) => c.dataset === 'tep').map((c) => c.case_id)">
            仅 TEP
          </button>
        </div>
        <div style="display: flex; flex-direction: column; gap: 4px">
          <label v-for="c in state?.cases || []" :key="c.case_id" class="row">
            <input type="checkbox" :value="c.case_id" v-model="selectedCases" />
            <span class="mono tiny" style="min-width: 210px; color: var(--ink-dim)">{{ c.case_id }}</span>
            <span class="badge tiny">{{ c.dataset }}</span>
            <span v-if="c.control" class="badge cyan tiny">CONTROL</span>
            <span v-else class="badge bad tiny">fault</span>
          </label>
        </div>
      </div>
    </div>

    <div class="panel">
      <div class="toolbar">
        <button class="primary" :disabled="busy || !selectedAlgos.length || !selectedCases.length" @click="start">
          {{ busy ? '运行中…' : `运行 ${totalRuns} 组` }}
        </button>
        <span v-if="state?.resolved_provider" class="badge ok">provider: {{ state.resolved_provider.id }}</span>
        <span v-else class="badge warn">provider: none</span>
        <span class="spacer" />
        <span class="tiny muted">{{ selectedAlgos.length }} 算法 × {{ selectedCases.length }} 场景</span>
      </div>

      <div v-if="errorMsg" class="callout bad">{{ errorMsg }}</div>
    </div>

    <!-- live progress -->
    <div v-if="job" class="panel">
      <h2>
        进度
        <span class="badge" :class="job.state === 'complete' ? 'ok' : job.state === 'error' ? 'bad' : 'info'">
          {{ job.state }}
        </span>
        <span v-if="job.run_id" class="badge">{{ job.run_id }}</span>
      </h2>

      <div class="bar" style="margin: 8px 0"><i :style="{ width: pct + '%' }" /></div>
      <div class="tiny muted mono" style="margin-bottom: 12px">{{ job.done }} / {{ job.total }} ({{ pct }}%)</div>

      <div v-if="job.error" class="callout bad"><pre>{{ job.error }}</pre></div>

      <div v-if="Object.keys(job.live || {}).length" class="table-wrap" style="margin-bottom: 12px">
        <table>
          <thead>
            <tr>
              <th>算法</th>
              <th class="num">完成</th>
              <th class="num">Top-1</th>
              <th class="num">Wilson 95%</th>
              <th class="num">精确 IDV</th>
              <th class="num">对照通过</th>
              <th class="num">误报</th>
              <th class="num">弃权</th>
              <th class="num">失败</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(l, id) in job.live" :key="id">
              <td class="mono">{{ id }}</td>
              <td class="num">{{ l.done }}</td>
              <td class="num">{{ l.hits }}/{{ l.faults }}</td>
              <td class="num">{{ l.wilson ? `[${l.wilson[0]}, ${l.wilson[1]}]` : '—' }}</td>
              <td class="num">{{ l.exact }}</td>
              <td class="num">{{ l.controlPass }}/{{ l.controls }}</td>
              <td class="num" :style="l.falseAlarms ? 'color: var(--bad)' : ''">{{ l.falseAlarms }}</td>
              <td class="num">{{ l.abstain }}</td>
              <td class="num" :style="l.failed ? 'color: var(--warn)' : ''">{{ l.failed }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <details v-if="job.log?.length" open>
        <summary>执行日志（最近 {{ job.log.length }} 条）</summary>
        <div class="log">
          <div v-for="(e, i) in job.log.filter((x) => x.kind === 'done').slice(-90)" :key="i">
            <span class="alg">{{ e.algorithm }}</span>
            <span class="case">{{ e.case }}</span>
            <span class="out" :class="e.outcome">{{ outcomeLabel[e.outcome] || e.outcome }}</span>
            <span class="muted">{{ (e.top3 || []).slice(0, 1).join('') }}</span>
          </div>
        </div>
      </details>

      <div v-if="job.state === 'complete'" style="margin-top: 12px">
        <NuxtLink :to="`/results?run=${job.run_id}`">
          <button class="primary">查看完整对比结果 →</button>
        </NuxtLink>
      </div>
    </div>
  </div>
</template>
