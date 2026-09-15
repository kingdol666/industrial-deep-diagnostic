<script setup>
// 自建数据诊断 — upload your data, run real diagnoses, watch them happen.
//
// The page talks to a dedicated diagnosis API (NOT the benchmark runner):
//   POST /api/diagnose                     start
//   GET  /api/diagnose/:id/stream          live SSE events
//   GET  /api/diagnose/:id                 final structured report
//
// Everything rendered below comes from that stream or that report. There is no
// client-side mock and no canned content: if the backend did not execute an
// algorithm, its card does not exist.
const { data: cap } = await useFetch('/api/diagnose', { key: 'diagnose-capabilities' });
const { data: uploadsData, refresh: refreshUploads } = await useFetch('/api/uploads', { key: 'uploads' });

// ---------------------------------------------------------------- upload
const fileInput = ref(null);
const file = ref(null);
const trainingInput = ref(null);
const trainingFile = ref(null);
const labelColumn = ref('');
const causeList = ref('');
const dragging = ref(false);
const label = ref('');
const processDescription = ref('');
const calibration = ref(30);
const uploading = ref(false);
const uploadError = ref('');
const upload = ref(null);
const inspection = ref(null);
const parsedDetails = ref(false);

function pickFile(f) {
  if (!f) return;
  file.value = f;
  if (!label.value) label.value = f.name.replace(/\.[^.]+$/, '');
}
function onDrop(e) { dragging.value = false; pickFile(e.dataTransfer?.files?.[0]); }
function onPick(e) { pickFile(e.target.files?.[0]); }

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
    // Optional: labelled examples unlock the supervised classifiers; a cause list
    // unlocks the FaultExplainer protocol with candidates that fit this process.
    if (trainingFile.value) fd.append('training', trainingFile.value);
    if (labelColumn.value) fd.append('label_column', labelColumn.value);
    if (causeList.value) fd.append('cause_list', causeList.value);
    const res = await $fetch('/api/uploads', { method: 'POST', body: fd });
    upload.value = res.upload;
    inspection.value = await $fetch(`/api/uploads/${res.upload.upload_id}`);
    parsedDetails.value = true;
    await refreshUploads();
    file.value = null;
    if (fileInput.value) fileInput.value.value = '';
    trainingFile.value = null;
    if (trainingInput.value) trainingInput.value.value = '';
  } catch (e) {
    uploadError.value = String(e?.data?.statusMessage || e.message);
  } finally { uploading.value = false; }
}

async function useExisting(u) {
  upload.value = u;
  inspection.value = await $fetch(`/api/uploads/${u.upload_id}`);
  parsedDetails.value = true;
  label.value = u.label;
  processDescription.value = u.process_description || '';
  calibration.value = Math.round((u.calibration_fraction ?? 0.3) * 100);
}
async function removeUpload(u) {
  await $fetch(`/api/uploads/${u.upload_id}`, { method: 'DELETE' });
  if (upload.value?.upload_id === u.upload_id) { upload.value = null; inspection.value = null; }
  await refreshUploads();
}

// ------------------------------------------------------------- selection
const selected = ref([]);
onMounted(() => {
  selected.value = (cap.value?.runnable || []).map((a) => a.id);
});
const runnable = computed(() => cap.value?.runnable || []);
const refused = computed(() => cap.value?.refused || []);
const byId = computed(() => Object.fromEntries(runnable.value.map((a) => [a.id, a])));
const needsProvider = computed(() => selected.value.some((id) => byId.value[id]?.requires_provider));
const providerReady = computed(() => Boolean(cap.value?.provider));

// ------------------------------------------------------------- diagnosis
const job = ref(null);       // { job_id, ... }
const events = ref([]);      // live event log
const report = ref(null);
const diagnosisError = ref('');
const running = ref(false);
let es = null;

function applyEvent(e) {
  events.value.push(e);
  if (e.type === 'complete') {
    report.value = e.report || null;
    if (job.value) job.value.state = 'complete';
    running.value = false;
    closeStream();
  }
  if (e.type === 'end' && running.value) {
    // stream closed without a complete event: fetch whatever was accumulated
    running.value = false;
    closeStream();
    void refreshFinal();
  }
  if (e.type === 'error') {
    diagnosisError.value = e.message || 'diagnosis failed';
    running.value = false;
    closeStream();
  }
}

function closeStream() {
  if (es) { es.close(); es = null; }
}

async function refreshFinal() {
  if (!job.value) return;
  try {
    const s = await $fetch(`/api/diagnose/${job.value.job_id}`);
    report.value = s.report || report.value;
    if (s.state !== 'running') running.value = false;
  } catch { /* keep what we have */ }
}

async function startDiagnosis() {
  diagnosisError.value = '';
  events.value = [];
  report.value = null;
  if (!upload.value) { diagnosisError.value = '请先上传数据'; return; }
  if (!selected.value.length) { diagnosisError.value = '请至少选择一个算法'; return; }
  running.value = true;
  closeStream();
  try {
    const res = await $fetch('/api/diagnose', {
      method: 'POST',
      body: { uploadId: upload.value.upload_id, algorithms: selected.value },
    });
    job.value = res;
    // Subscribe to the live stream. EventSource is one-directional and
    // reconnects on its own; history is replayed by the server on attach.
    es = new EventSource(res.stream_url);
    es.onmessage = (m) => {
      try { applyEvent(JSON.parse(m.data)); } catch { /* ignore malformed frame */ }
    };
    es.onerror = () => {
      // The server closes the stream when the job ends; only surface an error
      // if we are still supposed to be running.
      if (running.value) { running.value = false; closeStream(); void refreshFinal(); }
    };
  } catch (e) {
    running.value = false;
    diagnosisError.value = String(e?.data?.statusMessage || e.message);
  }
}

onBeforeUnmount(closeStream);

// ------------------------------------------------------------- rendering
const progress = computed(() => {
  const total = job.value?.algorithms?.length || selected.value.length || 0;
  const done = events.value.filter((e) => e.type === 'algorithm_done').length;
  return { done, total, pct: total ? Math.round((done / total) * 100) : 0 };
});

function eventsOf(type) { return events.value.filter((e) => e.type === type); }
function stageEvents() { return eventsOf('stage'); }

const llmCalls = computed(() => {
  const started = eventsOf('llm_call_start');
  const done = eventsOf('llm_call_done');
  return started.map((s, i) => ({ start: s, done: done[i] || null, pending: !done[i] }));
});
const pendingCall = computed(() => llmCalls.value.find((c) => c.pending) || null);

const findingByAlgo = computed(() => Object.fromEntries((report.value?.findings || []).map((f) => [f.algorithm, f])));
const maxVar = computed(() => {
  let m = 0;
  for (const f of report.value?.findings || []) for (const v of f.variables) m = Math.max(m, Math.abs(v.contribution));
  return m || 1;
});

const statusBadge = (s) => ({ executed: 'ok', not_applicable: '', skipped_no_provider: 'warn', error: 'bad' }[s] ?? '');
const verdictBadge = (v) => (v === 'fault' ? 'bad' : v === 'normal' ? 'ok' : '');
const verdictText = (v) => (v === 'fault' ? '检出异常' : v === 'normal' ? '判为正常' : '—');
const fmtSec = (s) => (s == null ? '—' : `${Number(s).toFixed(1)}s`);
</script>

<template>
  <div>
    <div class="page-head">
      <h1>自建数据诊断 · Diagnose your own data</h1>
      <p>
        上传你的时序数据 → 选择要复现的诊断方法 → 后端<strong>真实执行</strong>。
        每个算法都会跑在你的数据行上；每个 LLM 算法都会<strong>真实发起一次模型请求</strong>，
        下面实时显示它调用的是哪个 provider / 哪个模型 / 耗时多久 / 返回了什么。
      </p>
    </div>

    <!-- ============================================================ 1 upload -->
    <div class="panel">
      <h2>1 · 上传数据</h2>
      <p class="panel-sub">
        CSV（逗号分隔，首行表头）。后端会真实解析你的字节并实测行列数；少于 10 行、少于 2 个数值列会被拒绝。
      </p>

      <div class="grid g2">
        <div>
          <div
            class="dropzone" :class="{ over: dragging }"
            @dragover.prevent="dragging = true" @dragleave.prevent="dragging = false"
            @drop.prevent="onDrop" @click="fileInput?.click()"
          >
            <input ref="fileInput" type="file" accept=".csv,.tsv,.txt,text/csv" style="display: none" @change="onPick" />
            <div v-if="!file" class="dz-empty">
              <strong>拖入文件</strong> 或点击选择<br />
              <span class="tiny muted">.csv / .tsv / .txt</span>
            </div>
            <div v-else class="dz-file">
              <span class="badge info">{{ (file.size / 1024).toFixed(1) }} KB</span>
              <span class="mono">{{ file.name }}</span>
            </div>
          </div>

          <div class="spacer-y" />
          <label class="row" style="display: block">
            <span class="tiny muted">名称</span>
            <input v-model="label" type="text" placeholder="例如 3 号线冷却回路" style="width: 100%" />
          </label>
          <div class="spacer-y" />
          <label class="row" style="display: block">
            <span class="tiny muted">工艺描述（LLM 唯一的领域上下文，强烈建议填写）</span>
            <textarea
              v-model="processDescription" rows="5"
              placeholder="例：水冷试验回路。列含义：InletTemp=入口温度(℃)、CoolantFlow=冷却水流量(L/min)、VibrationRMS=振动RMS(g)、Pressure=压力(bar)。冷却侧受限会导致流量下降、温度与振动上升。"
              style="width: 100%; font: inherit; font-size: 13px; padding: 7px 9px; border-radius: 5px; border: 1px solid var(--line); background: var(--bg-inset); color: var(--ink); resize: vertical"
            />
          </label>
          <div class="spacer-y" />
          <label class="row">
            <span class="tiny muted">前</span>
            <input v-model.number="calibration" type="range" min="5" max="80" step="5" style="flex: 1" />
            <span class="mono tiny">{{ calibration }}% 标定</span>
          </label>
          <div class="tiny muted" style="margin-top: 2px">
            用文件前 {{ calibration }}% 的行标定阈值，其余为监测区间。检测器与 LLM 摘要<strong>使用同一分段</strong>，
            否则持续故障会把自己所在的标准差撑大而被掩蔽。
          </div>
          <div class="spacer-y" />
          <details>
            <summary>可选：解锁更多算法（监督分类器 / FaultExplainer 协议）</summary>
            <div class="tiny muted" style="margin: 6px 0">
              不填也能跑 —— 但 <code>xgb-gbdt</code>/<code>rf-forest</code>/<code>mlp-classifier</code>
              是分类器，没有带标签样本就无法学习，会<strong>如实拒绝</strong>而不是编造类别；
              <code>fe-official</code> 的 EXPLAIN_ROOT 需要一个候选成因清单，不给就开放式推理。
            </div>

            <label class="row" style="display: block">
              <span class="tiny muted">① 带标签训练集 CSV（含 label/class/fault 列）</span>
              <div class="toolbar" style="margin-top: 4px">
                <input ref="trainingInput" type="file" accept=".csv,.tsv,.txt,text/csv"
                       @change="trainingFile = $event.target.files?.[0] || null" style="font-size: 12px" />
                <span v-if="trainingFile" class="badge info">{{ trainingFile.name }}</span>
              </div>
            </label>
            <div class="spacer-y" />
            <label class="row" style="display: block">
              <span class="tiny muted">② 标签列名（留空则自动识别 label/class/fault/y/target）</span>
              <input v-model="labelColumn" type="text" placeholder="例如 fault_code" style="width: 100%" />
            </label>
            <div class="spacer-y" />
            <label class="row" style="display: block">
              <span class="tiny muted">③ 候选成因清单（每行一条，可写「编号: 描述」）</span>
              <textarea v-model="causeList" rows="4"
                placeholder="C1: 冷却水阀卡涩/开度不足&#10;C2: 冷却水过滤器堵塞&#10;C3: 泵扬程下降"
                style="width: 100%; font: inherit; font-size: 12px; padding: 6px 8px; border-radius: 5px; border: 1px solid var(--line); background: var(--bg-inset); color: var(--ink); resize: vertical"
              />
            </label>
          </details>

          <div class="spacer-y" />
          <button class="primary" :disabled="uploading || !file" @click="doUpload">
            {{ uploading ? '上传解析中…' : '上传并解析' }}
          </button>
          <div v-if="uploadError" class="callout bad">{{ uploadError }}</div>
        </div>

        <div>
          <div v-if="!inspection" class="callout">
            上传后这里显示后端<strong>实测</strong>的结果：行数、数值列、被排除的索引列、前几行真实取值。
          </div>
          <template v-else>
            <div class="grid g3" style="margin-bottom: 10px">
              <div class="stat accent"><div class="k">行数</div><div class="v">{{ inspection.parsed.rows }}</div></div>
              <div class="stat accent"><div class="k">数值列</div><div class="v">{{ inspection.parsed.numeric_columns }}</div></div>
              <div class="stat">
                <div class="k">标定 / 监测</div>
                <div class="v" style="font-size: 1.1rem">
                  {{ Math.round(inspection.parsed.rows * (upload?.calibration_fraction ?? 0.3)) }}
                  / {{ inspection.parsed.rows - Math.round(inspection.parsed.rows * (upload?.calibration_fraction ?? 0.3)) }}
                </div>
              </div>
            </div>
            <dl class="kv">
              <dt>文件</dt><dd>{{ upload?.original_name }}</dd>
              <dt>列</dt><dd>{{ inspection.parsed.columns.join(', ') }}</dd>
              <template v-if="upload?.excluded_index_column">
                <dt>已排除索引列</dt>
                <dd>{{ upload.excluded_index_column }} <span class="muted">({{ upload.excluded_index_reason }})</span></dd>
              </template>
              <template v-if="upload?.dropped_non_numeric?.length">
                <dt>丢弃非数值列</dt><dd>{{ upload.dropped_non_numeric.join(', ') }}</dd>
              </template>
              <template v-if="upload?.training">
                <dt>训练集</dt>
                <dd>
                  {{ upload.training.rows }} 行 · {{ upload.training.classes }} 类 ·
                  label 列 <code>{{ upload.training.label_column }}</code>
                </dd>
              </template>
              <template v-if="upload?.cause_list">
                <dt>候选成因</dt><dd>{{ upload.cause_list.length }} 条</dd>
              </template>
            </dl>
            <details :open="parsedDetails" style="margin-top: 8px">
              <summary>前 5 行（后端真实解析所得）</summary>
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
            </details>
          </template>
        </div>
      </div>
    </div>

    <!-- ======================================================= 2 algorithms -->
    <div class="panel">
      <h2>2 · 选择要复现的诊断方法</h2>
      <p class="panel-sub">
        {{ runnable.length }} 个方法可跑在你的数据上。需要 TEP 标签或 TEP 专用协议的
        {{ refused.length }} 个方法被排除，理由在下方。
      </p>

      <div class="callout" style="margin-bottom: 10px">
        <strong>两类方法产出不同层次的结果：</strong>
        经典检测器给出<strong>贡献变量</strong>（变量→成因表是 TEP 专用的，替你臆造一张正是诚实红线禁止的事）；
        LLM 方法给出<strong>机理假设</strong>。两者都由后端真实执行。
      </div>

      <div v-if="needsProvider && !providerReady" class="callout warn">
        所选包含 LLM 方法，但当前没有可用 provider —— 它们会被如实记为
        <code>skipped_no_provider</code>，并给出空结论，<strong>不会编造答案</strong>。
      </div>

      <div class="grid g2">
        <div style="display: flex; flex-direction: column; gap: 5px">
          <label v-for="a in runnable" :key="a.id" class="row">
            <input type="checkbox" :value="a.id" v-model="selected" />
            <span class="mono tiny" style="min-width: 112px; color: var(--ink-dim)">{{ a.id }}</span>
            <span class="small">{{ a.label }}</span>
            <span v-if="a.requires_provider" class="badge violet tiny">LLM · 真实调用</span>
            <span v-else class="badge ok tiny">离线</span>
          </label>
        </div>
        <div>
          <details>
            <summary>{{ refused.length }} 个方法为何不能跑（点击展开）</summary>
            <ul class="tight">
              <li v-for="r in refused" :key="r.id">
                <code>{{ r.id }}</code> — {{ r.reason }}
              </li>
            </ul>
          </details>
          <div class="spacer-y" />
          <div class="toolbar">
            <button class="primary" :disabled="running || !upload || !selected.length" @click="startDiagnosis">
              {{ running ? '诊断执行中…' : `开始诊断（${selected.length} 个方法）` }}
            </button>
            <span v-if="cap?.provider" class="badge ok">provider: {{ cap.provider.id }}</span>
            <span v-else class="badge warn">provider: none</span>
          </div>
          <div v-if="diagnosisError" class="callout bad">{{ diagnosisError }}</div>
        </div>
      </div>
    </div>

    <!-- ========================================================= 3 live run -->
    <div v-if="job" class="panel">
      <h2>
        3 · 实时执行
        <span class="badge" :class="job.state === 'complete' ? 'ok' : job.state === 'error' ? 'bad' : 'info'">
          {{ job.state }}
        </span>
        <span class="badge">{{ progress.done }}/{{ progress.total }}</span>
      </h2>

      <div class="bar" style="margin: 8px 0"><i :style="{ width: progress.pct + '%' }" /></div>

      <div v-if="pendingCall" class="callout">
        <strong>正在调用模型…</strong>
        <span class="mono tiny">
          {{ pendingCall.start.algorithm }} / {{ pendingCall.start.tag }} → provider
          {{ pendingCall.start.provider }} · model {{ pendingCall.start.model }}
        </span>
        <span class="spinner" />
      </div>

      <!-- every real model call, as it happens -->
      <div v-if="llmCalls.length" style="margin-bottom: 12px">
        <div class="tiny muted" style="margin-bottom: 4px">真实模型调用（{{ llmCalls.length }} 次）</div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr><th>算法</th><th>阶段</th><th>provider</th><th>模型</th><th class="num">耗时</th><th>状态</th><th>回复摘要</th></tr>
            </thead>
            <tbody>
              <tr v-for="(c, i) in llmCalls" :key="i">
                <td class="mono tiny">{{ c.start.algorithm }}</td>
                <td class="mono tiny">{{ c.start.tag }}</td>
                <td class="mono tiny">{{ c.start.provider }}</td>
                <td class="mono tiny">{{ c.start.model }}</td>
                <td class="num tiny">{{ c.pending ? '…' : fmtSec(c.done.seconds) }}</td>
                <td>
                  <span v-if="c.pending" class="badge warn">running</span>
                  <span v-else-if="c.done.ok" class="badge ok">ok</span>
                  <span v-else class="badge bad">failed</span>
                </td>
                <td class="tiny dim" style="max-width: 42ch">
                  {{ c.pending ? '等待模型返回…' : (c.done.reply_head || c.done.error || '').slice(0, 160) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <details>
        <summary>执行事件流（{{ events.length }} 条）</summary>
        <div class="log">
          <div v-for="e in events" :key="e.seq">
            <span class="case">#{{ e.seq }} {{ e.type }}</span>
            <span class="alg">{{ e.algorithm || e.stage || '' }}</span>
            <span class="muted">{{ (e.message || e.summary || e.tag || '').slice(0, 120) }}</span>
          </div>
        </div>
      </details>
    </div>

    <!-- ========================================================== 4 report -->
    <template v-if="report">
      <div class="panel">
        <h2>4 · 诊断报告</h2>
        <div class="callout warn">
          <strong>本报告不计分。</strong>上传数据没有金标准，因此这里报告的是<strong>真实执行结果</strong>：
          {{ report.headline.executed }} 个方法实际执行，
          {{ report.headline.fault_verdicts }} 个判为异常、{{ report.headline.normal_verdicts }} 个判为正常。
          我们不会把结论包装成"命中"或"未命中"。
        </div>

        <!-- Evidence integrity: an answer built on fabricated tool output must be
             impossible to mistake for a grounded one. -->
        <div v-if="report.evidence_warnings?.length" class="callout bad">
          <strong>⚠ 证据完整性告警（{{ report.evidence_warnings.length }} 个回答）。</strong>
          这些 LLM 回答在生成过程中，模型<strong>自己写了 OBSERVATION 行、或调用了不存在的工具</strong>，
          也就是编造了工具输出。伪造内容已被剥离且<strong>未作为证据</strong>；但该回答里任何
          <em>没有出现在下方工具调用轨迹中</em> 的数字都应视为不可靠：
          <ul class="tight">
            <li v-for="w in report.evidence_warnings" :key="w.algorithm">
              <code>{{ w.algorithm }}</code> — {{ w.integrity }}：{{ w.note }}
              <div v-if="w.violations?.length" class="tiny muted" style="margin-top: 2px">
                {{ w.violations.map((v) => v.kind + (v.tool ? '(' + v.tool + ')' : '')).join('、') }}
              </div>
            </li>
          </ul>
        </div>
        <div
          v-else-if="report.headline.llm_mechanisms && !report.headline.contaminated_answers && !report.headline.unverified_answers"
          class="callout ok"
        >
          证据完整性检查通过：所有 LLM 回答都建立在真实工具观测之上，无伪造观测、无虚构工具调用。
        </div>

        <div class="grid g4" style="margin-bottom: 10px">
          <div class="stat accent"><div class="k">执行方法</div><div class="v">{{ report.headline.executed }}</div></div>
          <div class="stat" :class="report.headline.fault_verdicts ? 'warn' : 'ok'">
            <div class="k">判为异常</div><div class="v">{{ report.headline.fault_verdicts }}</div>
          </div>
          <div class="stat ok"><div class="k">判为正常</div><div class="v">{{ report.headline.normal_verdicts }}</div></div>
          <div class="stat"><div class="k">LLM 机理假设</div><div class="v">{{ report.headline.llm_mechanisms }}</div></div>
        </div>

        <dl class="kv">
          <dt>数据集</dt><dd>{{ report.dataset.label }}（{{ report.dataset.original_name }}）</dd>
          <dt>规模</dt><dd>{{ report.dataset.rows }} 行 × {{ report.dataset.numeric_columns }} 列</dd>
          <dt>标定 / 监测</dt><dd>{{ report.method.calibration_rows }} / {{ report.method.monitored_rows }} 行</dd>
          <dt v-if="report.dataset.excluded_index_column">已排除索引列</dt>
          <dd v-if="report.dataset.excluded_index_column">{{ report.dataset.excluded_index_column }}</dd>
          <dt>总耗时</dt><dd>{{ (report.duration_ms / 1000).toFixed(1) }}s</dd>
        </dl>
      </div>

      <!-- mechanism hypotheses: the LLM layer -->
      <div v-if="report.mechanism_hypotheses.length" class="panel">
        <h2>机理假设（LLM 方法，逐次真实调用）</h2>
        <div v-for="m in report.mechanism_hypotheses" :key="m.algorithm" class="panel" style="background: var(--bg-inset)">
          <div class="toolbar" style="margin-bottom: 6px">
            <strong class="mono">{{ m.algorithm }}</strong>
            <span class="badge violet">{{ m.model }}</span>
            <span class="badge">{{ m.calls }} 次调用 · {{ fmtSec(m.seconds) }}</span>
            <span v-if="m.confidence" class="badge">confidence: {{ m.confidence }}</span>
          </div>
          <ol style="margin: 4px 0 8px; padding-left: 20px">
            <li v-for="(h, i) in m.hypotheses" :key="i" :style="i === 0 ? 'font-weight:550' : ''">{{ h }}</li>
          </ol>
          <div class="small dim">{{ m.reasoning }}</div>
        </div>
      </div>

      <!-- consensus variables -->
      <div v-if="report.consensus_variables.length" class="panel">
        <h2>变量共识</h2>
        <p class="panel-sub">多少种检测器独立地把该变量排进前 5。多方法一致指向的变量更可信。</p>
        <div class="table-wrap">
          <table>
            <thead><tr><th>变量</th><th class="num">独立检出方法数</th><th>占比</th></tr></thead>
            <tbody>
              <tr v-for="v in report.consensus_variables" :key="v.column">
                <td class="mono tiny">{{ v.column }}</td>
                <td class="num">{{ v.algorithms }}</td>
                <td>
                  <div class="bar" style="width: 140px"><i :style="{ width: (v.algorithms / report.headline.executed) * 100 + '%' }" /></div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- per-algorithm findings -->
      <div class="panel">
        <h2>逐方法结果</h2>
        <div v-for="f in report.findings" :key="f.algorithm" class="panel" style="background: var(--bg-inset)">
          <div class="toolbar" style="margin-bottom: 6px">
            <strong class="mono">{{ f.algorithm }}</strong>
            <span class="badge" :class="statusBadge(f.status)">{{ f.status }}</span>
            <span v-if="f.verdict" class="badge" :class="verdictBadge(f.verdict)">{{ verdictText(f.verdict) }}</span>
            <span v-if="f.detection_rate !== null" class="badge info">报警率 {{ (f.detection_rate * 100).toFixed(1) }}%</span>
            <span v-if="f.deterministic" class="badge ok tiny">确定性</span>
            <span v-else class="badge violet tiny">LLM</span>
            <span class="spacer" />
            <span class="tiny muted mono">{{ (f.runtime_ms / 1000).toFixed(1) }}s</span>
          </div>

          <div v-if="f.invocations.length" class="tiny mono dim" style="margin-bottom: 6px">
            <span v-for="(i, k) in f.invocations" :key="k">
              {{ i.tag }} → {{ i.provider }}/{{ i.model }} {{ fmtSec(i.seconds) }}<span v-if="i.archived"> · 已归档</span><br />
            </span>
          </div>

          <div v-if="f.hypotheses.length">
            <div class="tiny muted">排序假设</div>
            <ol style="margin: 2px 0 6px; padding-left: 20px">
              <li v-for="(h, i) in f.hypotheses" :key="i">{{ h }}</li>
            </ol>
          </div>
          <div v-else-if="f.verdict === 'normal'" class="callout ok" style="margin: 4px 0">
            该方法判定<strong>无异常</strong>，因此不给出成因 —— 这是结论，不是缺漏。
          </div>

          <div v-if="f.variables.length" style="margin-top: 6px">
            <div class="tiny muted">贡献变量（真实计算）</div>
            <div v-for="v in f.variables" :key="v.column" style="display: flex; align-items: center; gap: 8px; margin: 2px 0">
              <span class="mono tiny" style="min-width: 150px">{{ v.column }}</span>
              <div class="bar" style="flex: 1; max-width: 220px"><i :style="{ width: (Math.abs(v.contribution) / maxVar) * 100 + '%' }" /></div>
              <span class="mono tiny muted">{{ v.contribution.toFixed(4) }}</span>
            </div>
          </div>

          <div v-if="f.tool_calls?.length" style="margin-top: 6px">
            <details>
              <summary>工具调用轨迹（{{ f.tool_calls.length }} 次）</summary>
              <div v-for="(t, i) in f.tool_calls" :key="i" class="tiny mono" style="margin: 3px 0">
                {{ t.tool }}({{ (t.args || []).join(', ') }}) → {{ JSON.stringify(t.observation).slice(0, 220) }}
              </div>
            </details>
          </div>

          <div v-if="f.reasoning" class="small dim" style="margin-top: 6px">{{ f.reasoning }}</div>

          <details style="margin-top: 6px">
            <summary>原始输出</summary>
            <pre>{{ JSON.stringify(f, null, 1).slice(0, 5000) }}</pre>
          </details>
        </div>
      </div>
    </template>

    <!-- ==================================================== past uploads -->
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
    border: 1.5px dashed var(--line); border-radius: 8px; padding: 22px 16px;
    text-align: center; cursor: pointer; background: var(--bg-inset);
    transition: border-color 0.15s ease, background 0.15s ease;
  }
  .dropzone:hover, .dropzone.over { border-color: var(--accent); background: #101b28; }
  .dz-empty { color: var(--ink-dim); font-size: 13px; }
  .dz-file { display: flex; align-items: center; justify-content: center; gap: 8px; font-size: 13px; }
  .spinner {
    display: inline-block; width: 11px; height: 11px; margin-left: 8px;
    border: 2px solid var(--line); border-top-color: var(--accent);
    border-radius: 50%; animation: spin 0.8s linear infinite; vertical-align: -1px;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
