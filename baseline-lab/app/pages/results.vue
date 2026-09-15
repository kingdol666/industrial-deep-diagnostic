<script setup>
// 03 — Results comparison across persisted sweeps.
const route = useRoute();
const { data: state } = await useFetch('/api/state', { key: 'lab-state' });

const { data: sweepList, refresh: refreshList } = await useFetch('/api/sweeps', { key: 'sweeps' });

// Resolve the initial sweep on the SERVER so the first paint already has data.
// Previously this was a `useFetch` with a null URL, which Nuxt stringifies to
// "null" and then throws on — a 500 on first visit.
const runId = ref(
  route.query.run ? String(route.query.run) : (sweepList.value?.sweeps?.[0]?.run_id ?? null),
);

const { data: sweep, pending, error: sweepError } = await useAsyncData(
  () => `sweep-${runId.value || 'none'}`,
  async () => {
    if (!runId.value) return null;
    try {
      return await $fetch(`/api/sweeps/${runId.value}`);
    } catch (e) {
      return { meta: { run_id: runId.value }, results: [], partial: true, summary: null, load_error: String(e?.data?.statusMessage || e.message) };
    }
  },
  { watch: [runId] },
);

watch(runId, (v) => { if (v) navigateTo({ query: { run: v } }, { replace: true }); });

const byAlgo = computed(() => {
  const s = sweep.value?.summary;
  if (!s) return [];
  return Object.entries(s.by_algorithm).map(([id, v]) => ({ id, ...v }));
});

// per-case matrix: rows = cases, cols = algorithms
const caseIds = computed(() => sweep.value?.meta?.cases || []);
const algoIds = computed(() => sweep.value?.meta?.algorithms || []);

function cell(caseId, algoId) {
  const r = sweep.value?.results?.find((x) => x.case_id === caseId && x.algorithm === algoId);
  if (!r) return null;
  return r;
}
function cellText(r) {
  if (!r) return '—';
  if (r.status !== 'executed') return { skipped_no_provider: 'skip', error: 'err', not_applicable: 'n/a' }[r.status] || r.status;
  const s = r.scored;
  if (s.control) return s.control_pass ? '✓' : '✗FA';
  if (s.exact_idv_top1_hit) return '★';
  if (s.strict_top1_hit) return '✓';
  if (s.top3?.length) return '·';
  return '∅';
}
function cellTitle(r) {
  if (!r) return '';
  const s = r.scored || {};
  return [
    `${r.algorithm} × ${r.case_id}`,
    `status: ${r.status}`,
    s.control ? `control_pass=${s.control_pass} false_alarm=${s.false_alarm}` : `strict=${s.strict_top1_hit} exact_idv=${s.exact_idv_top1_hit} fe_style=${s.fe_style_top3_hit}`,
    s.true_idv ? `truth: ${s.true_idv}` : '',
    `top3: ${(s.top3 || []).join(' | ') || '(empty)'}`,
  ].filter(Boolean).join('\n');
}
function cellClass(r) {
  if (!r) return 'muted';
  if (r.status === 'not_applicable') return 'muted';
  if (r.status === 'skipped_no_provider') return 'warn';
  if (r.status === 'error') return 'bad';
  const s = r.scored;
  if (s.control) return s.control_pass ? 'ok' : 'bad';
  if (s.exact_idv_top1_hit) return 'star';
  if (s.strict_top1_hit) return 'ok';
  if (s.top3?.length) return 'miss';
  return 'muted';
}

const expanded = ref(null);
function toggle(key) { expanded.value = expanded.value === key ? null : key; }
</script>

<template>
  <div>
    <div class="page-head">
      <h1>结果对比 · Results</h1>
      <p>
        逐场景 × 逐算法的判定矩阵与汇总指标。图例：<span class="badge ok">★</span> 精确命中真实 IDV ·
        <span class="badge ok">✓</span> 机制关键词命中 · <span class="badge">·</span> 给出结论但未命中 ·
        <span class="badge">∅</span> 弃权 · <span class="badge cyan">✓</span> 对照判正常 ·
        <span class="badge bad">✗FA</span> 对照误报 · <span class="badge warn">skip</span> 无 provider 未执行。
      </p>
    </div>

    <div class="panel">
      <div class="toolbar">
        <label class="row">
          <span class="small dim">Sweep</span>
          <select v-model="runId">
            <option :value="null">— 选择 —</option>
            <option v-for="s in sweepList?.sweeps || []" :key="s.run_id" :value="s.run_id">
              {{ s.run_id }} · {{ s.complete ? 'complete' : 'partial' }} · {{ s.result_count }} rows
            </option>
          </select>
        </label>
        <span class="spacer" />
        <button class="ghost" @click="refreshList(); runId = runId">刷新</button>
      </div>

      <div v-if="!sweepList?.sweeps?.length" class="callout">
        还没有任何 sweep。前往 <NuxtLink to="/run">运行基线</NuxtLink>，或执行
        <code>node scripts/sweep.mjs --family classical</code>。
      </div>
    </div>

    <div v-if="pending" class="panel">加载中…</div>
    <div v-if="sweepError" class="callout bad">加载失败：{{ sweepError.message }}</div>
    <div v-if="sweep?.load_error" class="callout bad">该 sweep 读取失败：{{ sweep.load_error }}</div>

    <template v-if="sweep && !sweep.load_error">
      <div v-if="sweep.partial" class="callout warn">
        该 sweep 未完成（partial）——只显示已落盘的 {{ sweep.results.length }} 条结果。
      </div>

      <div
        v-if="sweep.results.some((r) => ['llm-direct', 'llm-cot', 'llm-react', 'llm-debate', 'fe-official'].includes(r.algorithm)) && state?.comparability?.status === 'different_model'"
        class="callout bad"
      >
        <strong>可比性告警：</strong>本表含 LLM 基线。仓库归档基线由
        <code>{{ state.comparability.archived?.model || '未知' }}</code> 产生，
        本次由 <code>{{ state.comparability.lab_model }}</code> 产生。
        <strong>模型不同，二者不可直比</strong>——请把 LLM 行读作“当前模型下的独立测量”，
        而不是“对归档基线的复现”。
      </div>

      <!-- summary -->
      <div class="panel">
        <h2>汇总指标</h2>
        <p class="panel-sub">
          <strong>Top-1%</strong> = IDD rubric 口径（rank-1 命中机制关键词或真实 IDV 编号）；
          <strong>精确 IDV</strong> = rank-1 明确写出真实 IDV 编号，严格于前者——
          因为 {IDV4, IDV11, IDV14} 等故障族共享同一批关键词，关键词命中并不等于族内区分成功。
        </p>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>算法</th>
                <th>状态</th>
                <th class="num">Top-1</th>
                <th class="num">Top-1%</th>
                <th class="num">Wilson 95%</th>
                <th class="num">精确 IDV</th>
                <th class="num">FE@3</th>
                <th class="num">对照通过</th>
                <th class="num">误报</th>
                <th class="num">弃权</th>
                <th class="num">过度自信</th>
                <th class="num">未执行</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="a in byAlgo" :key="a.id">
                <td class="mono">{{ a.id }}</td>
                <td>
                  <span class="badge" :class="a.status === 'executed' ? 'ok' : a.status === 'skipped_no_provider' ? 'warn' : a.status === 'partial_error' ? 'bad' : ''">
                    {{ a.status }}
                  </span>
                </td>
                <td class="num">{{ a.metrics.top1 }}/{{ a.metrics.fault_cases }}</td>
                <td class="num">{{ a.metrics.top1_rate == null ? '—' : (a.metrics.top1_rate * 100).toFixed(0) + '%' }}</td>
                <td class="num tiny">
                  {{ a.metrics.top1_wilson ? `[${a.metrics.top1_wilson[0]}, ${a.metrics.top1_wilson[1]}]` : '—' }}
                </td>
                <td class="num">{{ a.metrics.exact_idv_top1 }}/{{ a.metrics.tep_fault_cases }}</td>
                <td class="num">{{ a.metrics.fe_style_top3 }}/{{ a.metrics.tep_fault_cases }}</td>
                <td class="num">{{ a.metrics.control_pass }}/{{ a.metrics.control_cases }}</td>
                <td class="num" :style="a.metrics.false_alarms ? 'color: var(--bad); font-weight:600' : ''">
                  {{ a.metrics.false_alarms }}
                </td>
                <td class="num">{{ a.metrics.abstained }}</td>
                <td class="num">{{ a.metrics.overconfident }}</td>
                <td class="num">{{ a.skipped_no_provider + a.errors + a.not_applicable }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- matrix -->
      <div class="panel">
        <h2>逐场景判定矩阵</h2>
        <p class="panel-sub">行 = 场景，列 = 算法。悬停查看完整结论文本；点击单元格展开详情。</p>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>场景</th>
                <th>真值</th>
                <th v-for="alg in algoIds" :key="alg" class="num mono tiny">{{ alg }}</th>
              </tr>
            </thead>
            <tbody>
              <template v-for="c in caseIds" :key="c">
                <tr>
                  <td class="mono tiny">{{ c }}</td>
                  <td class="tiny dim mono">
                    {{ cell(c, algoIds[0])?.scored?.true_idv || (cell(c, algoIds[0])?.scored?.control ? 'NORMAL' : '—') }}
                  </td>
                  <td
                    v-for="alg in algoIds"
                    :key="alg"
                    class="num"
                    style="cursor: pointer"
                    :title="cellTitle(cell(c, alg))"
                    @click="toggle(`${c}|${alg}`)"
                  >
                    <span :class="cellClass(cell(c, alg))" style="font-weight: 600">{{ cellText(cell(c, alg)) }}</span>
                  </td>
                </tr>
                <tr v-if="expanded && expanded.startsWith(c + '|')">
                  <td :colspan="algoIds.length + 2" style="background: var(--bg-inset)">
                    <div v-for="alg in algoIds" :key="alg">
                      <template v-if="expanded === `${c}|${alg}`">
                        <div class="small" style="margin-bottom: 4px">
                          <strong class="mono">{{ alg }}</strong>
                          <span class="badge" style="margin-left: 6px">{{ cell(c, alg)?.status }}</span>
                          <span v-if="cell(c, alg)?.scored?.strict_top1_hit" class="badge ok" style="margin-left: 6px">keyword hit</span>
                          <span v-if="cell(c, alg)?.scored?.exact_idv_top1_hit" class="badge ok" style="margin-left: 6px">exact IDV</span>
                          <span v-if="cell(c, alg)?.scored?.false_alarm" class="badge bad" style="margin-left: 6px">FALSE ALARM</span>
                        </div>
                        <div v-if="cell(c, alg)?.output?.top3?.length" class="small">
                          <div class="muted tiny">top3</div>
                          <ol style="margin: 2px 0 6px; padding-left: 20px">
                            <li v-for="(t, i) in cell(c, alg).output.top3" :key="i">{{ t }}</li>
                          </ol>
                        </div>
                        <div v-if="cell(c, alg)?.output?.reasoning" class="small dim">
                          <div class="muted tiny">reasoning</div>
                          {{ cell(c, alg).output.reasoning }}
                        </div>
                        <div v-if="cell(c, alg)?.output?.diagnosis_step" class="tiny muted" style="margin-top: 4px">
                          diagnosis step: {{ cell(c, alg).output.diagnosis_step }}
                        </div>
                        <details v-if="cell(c, alg)?.output">
                          <summary>原始输出</summary>
                          <pre>{{ JSON.stringify(cell(c, alg).output, null, 1).slice(0, 4000) }}</pre>
                        </details>
                      </template>
                    </div>
                  </td>
                </tr>
              </template>
            </tbody>
          </table>
        </div>
      </div>
    </template>

    <style scoped>
      .ok { color: var(--ok); }
      .bad { color: var(--bad); }
      .warn { color: var(--warn); }
      .miss { color: var(--ink-faint); }
      .star { color: var(--cyan); }
      .muted { color: var(--ink-faint); opacity: 0.55; }
    </style>
  </div>
</template>
