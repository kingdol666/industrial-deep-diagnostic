<script setup>
// 05 — Cases and datasets.
const { data: state } = await useFetch('/api/state', { key: 'lab-state' });

const grouped = computed(() => {
  const by = {};
  for (const c of state?.cases || []) {
    by[c.dataset] = by[c.dataset] || [];
    by[c.dataset].push(c);
  }
  return by;
});

const DATASET_INFO = {
  tep: {
    label: 'Tennessee Eastman Process',
    kind: '连续化工过程仿真（Downs & Vogel 标准）',
    detail: '反应器-冷凝器-气液分离器-汽提塔 + 循环压缩机；XMEAS_1..41 / XMV_1..11；3 分钟采样，第 161 样本起为故障时段。',
    role: '主战场：与 FaultExplainer 逐故障可比',
  },
  skab: {
    label: 'SKAB (Skoltech Anomaly Benchmark)',
    kind: '真实泵阀试验台',
    detail: '水箱 + 离心泵 + 阀门闭环回路；振动/电流/压力/温度/流量；1 Hz 采样，异常区间不提供时标。',
    role: '真实台架泛化 + 误报检验',
  },
  indpensim: {
    label: 'IndPenSim',
    kind: '工业规模青霉素批式发酵仿真',
    detail: '批过程多变量轨迹；Fault reference 标注列被显式排除出证据（防记忆污染）。',
    role: '批过程泛化',
  },
};
</script>

<template>
  <div>
    <div class="page-head">
      <h1>场景与数据 · Cases</h1>
      <p>
        实验室直接读取 IDD 仓库的 12 个场景定义与 <code>data/benchmark/prepared/</code> 下的真实数据，
        不复制、不改写。真值仅用于<strong>评分阶段</strong>：算法收到的是剥离了
        <code>truth</code>/<code>keywords</code>/<code>literature_baseline</code> 的净化对象。
      </p>
    </div>

    <div class="grid g3" style="margin-bottom: 16px">
      <div v-for="(info, ds) in DATASET_INFO" :key="ds" class="panel" style="margin-bottom: 0">
        <h2>{{ info.label }}</h2>
        <p class="panel-sub" style="margin-bottom: 6px">{{ info.kind }}</p>
        <div class="small dim">{{ info.detail }}</div>
        <div style="margin-top: 8px">
          <span class="badge info">{{ info.role }}</span>
          <span class="badge">{{ (grouped[ds] || []).length }} 场景</span>
        </div>
      </div>
    </div>

    <div v-for="(items, ds) in grouped" :key="ds" class="panel">
      <h2>{{ DATASET_INFO[ds]?.label || ds }} <span class="badge info">{{ items.length }}</span></h2>
      <div class="table-wrap">
        <table>
          <thead>
            <tr><th>case_id</th><th>角色</th><th>数据文件</th><th>说明</th></tr>
          </thead>
          <tbody>
            <tr v-for="c in items" :key="c.case_id">
              <td class="mono tiny">{{ c.case_id }}</td>
              <td>
                <span class="badge" :class="c.control ? 'cyan' : 'bad'">
                  {{ c.control ? 'CONTROL (正常)' : 'fault' }}
                </span>
              </td>
              <td class="mono tiny dim">{{ c.csv }}</td>
              <td class="small muted">
                {{ c.control
                  ? '正常对照：检测器报警即为误报，直接计入 false_alarms。'
                  : '故障场景：真值与判定关键词仅存在于评分器侧，不下发给算法。' }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="panel">
      <h2>仓库契约</h2>
      <dl class="kv">
        <dt>repo root</dt><dd>{{ state?.repo?.root }}</dd>
        <dt>cases file</dt><dd>{{ state?.repo?.cases_file }} ({{ state?.repo?.cases_present ? 'present' : 'MISSING' }})</dd>
        <dt>FaultExplainer</dt><dd>{{ state?.repo?.fault_explainer?.path }}</dd>
        <dt>FE commit</dt><dd>{{ state?.repo?.fault_explainer?.commit || '—' }}</dd>
        <dt>FE 自带产物</dt><dd>{{ state?.repo?.fault_explainer?.processed_outputs ? 'frontend/public/fault*.csv（用于逐行核对）' : 'MISSING' }}</dd>
        <dt>归档 LLM 回答</dt><dd>results/benchmark/baseline_fe_answers/ · {{ state?.repo?.archived_llm_answers }} 份</dd>
      </dl>
      <div class="callout" style="margin-top: 12px">
        <strong>为什么读而不复制数据：</strong>单一真源。若实验室复制一份数据，两份数据一旦漂移，
        所有复现声明即刻失效。实验室只写 <code>baseline-lab/results/</code>。
      </div>
    </div>
  </div>
</template>
