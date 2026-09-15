<script setup>
// 06 — 自建数据诊断 (bring your own data).
//
// Upload a file, pick algorithms, run them for real. Every number on this page
// comes back from an actual algorithm execution against the uploaded rows, and
// every LLM row names the provider and model that actually answered.
const { data: uploadsData, refresh: refreshUploads } = await useFetch('/api/uploads', { key: 'uploads' });
const { data: state } = await useFetch('/api/state', { key: 'lab-state' });

const fileInput = ref(null);
const file = ref(null);
const dragging = ref(false);
const label = ref('');
const processDescription = ref('');
const calibration = ref(30);
const uploading = ref(false);
const uploadError = ref('');
const current = ref(null);       // the upload meta we are working with
const inspection = ref(null);    // GET /api/uploads/:id payload

const selectedAlgos = ref([]);
const job = ref(null);
const poll = ref(null);
const running = ref(false);
const runError = ref('');

// Only algorithms that can legitimately run on a user's data start selected.
const APPLICABLE = ['pca-t2-spe', 'kpca-rbf', 'ica-fastica', 'spc-ewma-cusum', 'knn-fdd', 'iforest', 'llm-direct', 'llm-cot', 'llm-react', 'llm-debate'];

onMounted(() => {
  selectedAlgos.value = APPLICABLE.filter((id) => (state.value?.algorithms || []).some((a) => a.id === id));
});

const algoById = computed(() => Object.fromEntries((state.value?.algorithms || []).map((a) => [a.id, a])));
const providerAvailable = computed(() => Boolean(state.value?.resolved_provider));
const notApplicable = computed(() => uploadsData.value?.applicability?.not_applicable || {});
const selLlm = computed(() => selectedAlgos.value.some((id) => algoById.value[id]?.requiresProvider));

function pickFile(f) {
  if (!f) return;
  file.value = f;
  if (!label.value) label.value = f.name.replace(/\.[^.]+$/, '');
}
function onDrop(e) {
  dragging.value = false;
  pickFile(e.dataTransfer?.files?.[0]);
}

async function doUpload() {
  uploadError.value = '';
  if (!file.value) { uploadError.value = '请先选择一个数据文件'; return; }
  uploading.value = true;
  try {
    const fd = new FormData();
    fd.append('file', file.value);
    fd.append('label', label.value);
    fd.append('process_description', processDescription.value);
    fd.append('calibration_fraction', String(calibration.value / 100));
    const res = await $fetch('/api/uploads', { method: 'POST', body: fd });
    current.value = res.upload;
    inspection.value = await $fetch(`/api/uploads/${res.upload.upload_id}`);
    await refreshUploads();
    file.value = null;
    if (fileInput.value) fileInput.value.value = '';
  } catch (e) {
    uploadError.value = String(e?.data?.statusMessage || e.message);
  } finally {
    uploading.value = false;
  }
}

async function useExisting(u) {
  current.value = u;
  inspection.value = await $fetch(`/api/uploads/${u.upload_id}`);
  label.value = u.label;
  processDescription.value = u.process_description || '';
  calibration.value = Math.round((u.calibration_fraction ?? 0.3) * 100);
}

async function removeUpload(u) {
  await $fetch(`/api/uploads/${u.upload_id}`, { method: 'DELETE' });
  if (current.value?.upload_id === u.upload_id) { current.value = null; inspection.value = null; }
  await refreshUploads();
}

async function run() {
  runError.value = '';
  if (!current.value) { runError.value = '请先上传数据'; return; }
  if (!selectedAlgos.value.length) { runError.value = '请至少选择一个算法'; return; }
  running.value = true;
  job.value = null;
  if (poll.value) clearInterval(poll.value);
  try {
    const res = await $fetch('/api/run', {
      method: 'POST',
      body: { algorithms: selectedAlgos.value, cases: [current.value.case_id], label: 'custom' },
    });
    job.value = { job_id: res.job_id, done: 0, total: res.total, state: 'running', log: [], live: {} };
    poll.value = setInterval(async () => {
      try {
        const s = await $fetch(`/api/run/${res.job_id}`);
        job.value = s;
        if (s.state !== 'running') { clearInterval(poll.value); poll.value = null; running.value = false; loadResults(s); }
      } catch (e) {
        clearInterval(poll.value); poll.value = null; running.value = false;
        runError.value = String(e?.data?.statusMessage || e.message);
      }
    }, 1200);
  } catch (e) {
    running.value = false;
    runError.value = String(e?.data?.statusMessage || e.message);
  }
}

// Full per-algorithm results from the persisted sweep.
const results = ref(null);
async function loadResults(j) {
  const runId = j?.run_id;
  if (!runId) return;
  try { results.value = await $fetch(`/api/sweeps/${runId}`); } catch { /* keep whatever we have */ }
}

onBeforeUnmount(() => poll.value && clearInterval(poll.value));

const pretty = (v) => (v === null || v === undefined ? '—' : v);
function detRate(o) {
  const d = o?.detection;
  if (!d) return null;
  if (typeof d.detection_rate === 'number') return d.detection_rate;
  const t2 = d.T2?.detection_rate, spe = d.SPE?.detection_rate;
  if (t2 === undefined && spe === undefined) return null;
  return Math.max(t2 ?? 0, spe ?? 0);
}
function invocations(o) {
  return Array.isArray(o?.invocations) ? o.invocations : [];
}
</script>

<template>
  <div>
    <div class="page-head">
      <h1>自建数据诊断 · Bring your own data</h1>
      <p>
        上传你自己的时序数据，选择要复现的算法，<strong>后端会真的把算法跑在你的数据上</strong>；
        每个 LLM 算法会<strong>真实调用一次模型</strong>，页面显示的就是该模型这一次的真实回答
        （含 provider、模型名、耗时），不是预生成的产物。
      </p>
    </div>

    <!-- ---------------------------------------------------------- upload -->
    <div class="grid g2">
      <div class="panel">
        <h2>1 · 上传数据</h2>
        <p class="panel-sub">CSV（逗号分隔，首行表头）。至少 10 行、2 个数值列。</p>

        <div
          class="dropzone"
          :class="{ over: dragging }"
          @dragover.prevent="dragging = true"
          @dragleave.prevent="dragging = false"
          @drop.prevent="onDrop"
          @click="fileInput?.click()"
        >
          <input ref="fileInput" type="file" accept=".csv,.txt,.tsv,text/csv" style="display: none" @change="pickFile($event.target.files?.[0])" />
          <div v-if="!file" class="dz-empty">
            <strong>拖入文件</strong> 或点击选择<br />
            <span class="tiny muted">支持 .csv / .tsv / .txt</span>
          </div>
          <div v-else class="dz-file">
            <span class="badge info">{{ (file.size / 1024).toFixed(1) }} KB</span>
            <span class="mono">{{ file.name }}</span>
          </div>
        </div>

        <div class="spacer-y" />
        <label class="row" style="display: block">
          <span class="tiny muted">名称（可选）</span>
          <input v-model="label" type="text" placeholder="例如 BOPET 纵拉段 3 号线" style="width: 100%" />
        </label>
        <div class="spacer-y" />
        <label class="row" style="display: block">
          <span class="tiny muted">工艺描述（可选，但强烈建议——这是 LLM 唯一的领域上下文）</span>
          <textarea
            v-model="processDescription"
            rows="4"
            placeholder="例：水冷试验回路。列含义：InletTemp=入口温度(℃)、CoolantFlow=冷却水流量(L/min)、VibrationRMS=振动 RMS(g)、Pressure=压力(bar)。冷却侧堵塞会导致流量下降、温度上升。"
            style="width: 100%; font: inherit; font-size: 13px; padding: 7px 9px; border-radius: 5px; border: 1px solid var(--line); background: var(--bg-inset); color: var(--ink); resize: vertical"
          />
        </label>
        <div class="spacer-y" />
        <label class="row">
          <span class="tiny muted">前</span>
          <input v-model.number="calibration" type="range" min="5" max="80" step="5" style="flex: 1" />
          <span class="mono tiny">{{ calibration }}%</span>
        </label>
        <div class="tiny muted" style="margin-top: 2px">
          用文件前 {{ calibration }}% 的行标定检测阈值，其余作为监测区间。没有独立正常工况基线时这是标准做法，
          结果会明确标注为「自参照标定」。
        </div>

        <div class="spacer-y" />
        <div class="toolbar">
          <button class="primary" :disabled="uploading || !file" @click="doUpload">
            {{ uploading ? '上传解析中…' : '上传并解析' }}
          </button>
        </div>
        <div v-if="uploadError" class="callout bad">{{ uploadError }}</div>
      </div>

      <!-- ------------------------------------------------- parsed evidence -->
      <div class="panel">
        <h2>2 · 解析结果（真实读取）</h2>
        <p class="panel-sub">下面的行列数是后端解析你上传的字节后实测出来的，不是回显你填的内容。</p>

        <div v-if="!inspection" class="callout">
          还没有数据。上传后这里会显示实测行数、数值列、被丢弃的列，以及真实的统计摘要。
        </div>

        <template v-else>
          <div class="grid g3" style="margin-bottom: 10px">
            <div class="stat accent">
              <div class="k">行数</div>
              <div class="v">{{ inspection.parsed.rows }}</div>
            </div>
            <div class="stat accent">
              <div class="k">数值列</div>
              <div class="v">{{ inspection.parsed.numeric_columns }}</div>
            </div>
            <div class="stat">
              <div class="k">标定区间</div>
              <div class="v">{{ Math.round(inspection.parsed.rows * (current?.calibration_fraction ?? 0.3)) }}</div>
              <div class="s">监测 {{ inspection.parsed.rows - Math.round(inspection.parsed.rows * (current?.calibration_fraction ?? 0.3)) }} 行</div>
            </div>
          </div>

          <dl class="kv">
            <dt>文件</dt><dd>{{ current?.original_name }}</dd>
            <dt>列</dt><dd>{{ inspection.parsed.columns.join(', ') }}</dd>
            <dt v-if="current?.excluded_index_column">已排除索引列</dt>
            <dd v-if="current?.excluded_index_column">
              {{ current.excluded_index_column }} <span class="muted">({{ current.excluded_index_reason }})</span>
            </dd>
            <dt v-if="current?.dropped_non_numeric?.length">丢弃的非数值列</dt>
            <dd v-if="current?.dropped_non_numeric?.length">{{ current.dropped_non_numeric.join(', ') }}</dd>
          </dl>

          <div class="spacer-y" />
          <div class="tiny muted">前 5 行（后端真实解析所得）</div>
          <div class="table-wrap">
            <table>
              <thead><tr><th v-for="c in inspection.parsed.columns" :key="c" class="num">{{ c }}</th></tr></thead>
              <tbody>
                <tr v-for="(r, i) in inspection.parsed.first_rows" :key="i">
                  <td v-for="c in inspection.parsed.columns" :key="c" class="num tiny">{{ r[c] }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <details style="margin-top: 10px">
            <summary>盲态统计摘要（算法看到的就是这些）</summary>
            <div class="table-wrap">
              <table>
                <thead><tr><th>列</th><th class="num">max |z|</th><th class="num">超 3σ 比例</th></tr></thead>
                <tbody>
                  <tr v-for="d in inspection.digest" :key="d.col">
                    <td class="mono tiny">{{ d.col }}</td>
                    <td class="num">{{ d.max_abs_z }}</td>
                    <td class="num">{{ (d.pct_z3 * 100).toFixed(1) }}%</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </details>
        </template>
      </div>
    </div>

    <!-- ------------------------------------------------------- algorithm -->
    <div class="panel">
      <h2>3 · 选择算法并运行</h2>
      <p class="panel-sub">
        可跑的是不依赖 TEP 领域知识的算法；需要 TEP 标签或 TEP 专用协议的被自动排除，理由列在下方。
      </p>

      <div v-if="selLlm && !providerAvailable" class="callout warn">
        所选包含 LLM 算法，但没有可用 provider —— 它们会被如实记为 <code>skipped_no_provider</code>，不会编造答案。
      </div>

      <div style="display: flex; flex-direction: column; gap: 4px; margin-bottom: 12px">
        <label v-for="id in APPLICABLE" :key="id" class="row">
          <input type="checkbox" :value="id" v-model="selectedAlgos" :disabled="!algoById[id]" />
          <span class="mono tiny" style="min-width: 108px; color: var(--ink-dim)">{{ id }}</span>
          <span class="small">{{ algoById[id]?.label || '（未加载）' }}</span>
          <span v-if="algoById[id]?.requiresProvider" class="badge violet tiny">LLM · 真实调用</span>
          <span v-else class="badge ok tiny">离线确定性</span>
        </label>
      </div>

      <details>
        <summary>为什么另外 {{ Object.keys(notApplicable).length }} 个算法不能跑在你的数据上</summary>
        <ul class="tight">
          <li v-for="(why, id) in notApplicable" :key="id"><code>{{ id }}</code> — {{ why }}</li>
        </ul>
      </details>

      <div class="spacer-y" />
      <div class="toolbar">
        <button class="primary" :disabled="running || !current || !selectedAlgos.length" @click="run">
          {{ running ? '运行中…' : `运行 ${selectedAlgos.length} 个算法` }}
        </button>
        <span v-if="state?.resolved_provider" class="badge ok">provider: {{ state.resolved_provider.id }}</span>
        <span class="spacer" />
        <span v-if="job" class="tiny muted mono">{{ job.done }}/{{ job.total }}</span>
      </div>
      <div v-if="runError" class="callout bad">{{ runError }}</div>
      <div v-if="job && job.state === 'running'" class="bar" style="margin-top: 8px"><i :style="{ width: (job.total ? (job.done / job.total) * 100 : 0) + '%' }" /></div>
    </div>

    <!-- --------------------------------------------------------- results -->
    <div v-if="results" class="panel">
      <h2>4 · 运行结果 <span class="badge info">{{ results.results.length }} 个算法</span></h2>
      <div class="callout">
        <strong>本页不计分。</strong>你的数据没有金标准，所以所有结论都标为
        <span class="badge warn">UNSCORED</span>——我们不会把它伪装成命中或未命中。
        检测统计与机理假设都是真实计算/调用所得。
      </div>

      <div v-for="r in results.results" :key="r.algorithm" class="panel" style="background: var(--bg-inset)">
        <div class="toolbar" style="margin-bottom: 6px">
          <strong class="mono">{{ r.algorithm }}</strong>
          <span class="badge" :class="r.status === 'executed' ? 'ok' : r.status === 'not_applicable' ? '' : 'warn'">{{ r.status }}</span>
          <span class="badge warn">UNSCORED</span>
          <template v-for="inv in invocations(r.output)" :key="inv.tag">
            <span class="badge violet" :title="`${inv.provider} · ${inv.seconds}s`">
              模型 {{ inv.model }} · {{ inv.seconds }}s
            </span>
          </template>
          <span class="spacer" />
          <span v-if="detRate(r.output) !== null" class="tiny mono">报警率 {{ (detRate(r.output) * 100).toFixed(1) }}%</span>
        </div>

        <div v-if="invocations(r.output).length" class="callout" style="margin: 4px 0 8px">
          <strong>真实模型调用：</strong>
          <span v-for="(inv, i) in invocations(r.output)" :key="i" class="tiny mono">
            {{ inv.tag }} → provider={{ inv.provider }} model={{ inv.model }} ok={{ inv.ok }}
            <span v-if="inv.archived">· 原始回复已归档 <code>{{ inv.archived }}</code></span>
            <span v-if="inv.error" style="color: var(--bad)"> · {{ inv.error }}</span><br />
          </span>
        </div>

        <div v-if="r.output?.top3?.length">
          <div class="tiny muted">机理假设（ranked）</div>
          <ol style="margin: 2px 0 6px; padding-left: 20px">
            <li v-for="(t, i) in r.output.top3" :key="i">{{ t }}</li>
          </ol>
        </div>

        <div v-if="r.output?.variables_ranked?.length">
          <div class="tiny muted">贡献变量排序（真实计算）</div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>变量</th><th class="num">贡献</th></tr></thead>
              <tbody>
                <tr v-for="v in r.output.variables_ranked.slice(0, 6)" :key="v.col">
                  <td class="mono tiny">{{ v.col }}</td>
                  <td class="num">{{ Number(v.contribution).toFixed(4) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div v-if="r.output?.reasoning" class="small dim" style="margin-top: 8px">
          <div class="tiny muted">reasoning</div>
          {{ r.output.reasoning }}
        </div>

        <details style="margin-top: 6px">
          <summary>原始输出 JSON</summary>
          <pre>{{ JSON.stringify(r.output, null, 1).slice(0, 6000) }}</pre>
        </details>
      </div>
    </div>

    <!-- ------------------------------------------------------ past uploads -->
    <div v-if="uploadsData?.uploads?.length" class="panel">
      <h2>已上传的数据集</h2>
      <div class="table-wrap">
        <table>
          <thead><tr><th>名称</th><th>文件</th><th class="num">行 × 列</th><th>上传时间</th><th></th></tr></thead>
          <tbody>
            <tr v-for="u in uploadsData.uploads" :key="u.upload_id">
              <td>{{ u.label }}</td>
              <td class="mono tiny dim">{{ u.original_name }}</td>
              <td class="num tiny">{{ u.rows }} × {{ u.numeric_columns }}</td>
              <td class="tiny muted">{{ new Date(u.uploaded_at).toLocaleString() }}</td>
              <td>
                <button class="ghost tiny" style="padding: 2px 8px" @click="useExisting(u)">使用</button>
                <button class="ghost tiny" style="padding: 2px 8px; color: var(--bad)" @click="removeUpload(u)">删除</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<style scoped>
  .dropzone {
    border: 1.5px dashed var(--line);
    border-radius: 8px;
    padding: 22px 16px;
    text-align: center;
    cursor: pointer;
    background: var(--bg-inset);
    transition: border-color 0.15s ease, background 0.15s ease;
  }
  .dropzone:hover, .dropzone.over { border-color: var(--accent); background: #101b28; }
  .dz-empty { color: var(--ink-dim); font-size: 13px; }
  .dz-file { display: flex; align-items: center; justify-content: center; gap: 8px; font-size: 13px; }
</style>
