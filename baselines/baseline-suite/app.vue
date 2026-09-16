<template>
  <div class="wrap">
    <h1>IDD Baseline Suite <span class="sub">— 复刻对照诊断算法 · Nuxt</span></h1>
    <p class="note">
      三条基线臂：① 经典 PCA 监测（Chiang 2001/Qin 2012：对照训练 / 95% 方差 / T²+Q / 99 分位 / SPE top-3）；
      ② FaultExplainer 协议复刻（PCA(0.9) + T²(α=0.01 F 限) + 6 连续触发 + top-6 T² 贡献特征 + EXPLAIN_ROOT）；
      ③ 同模型裸 LLM 单次调用协议（盲态摘要，无候选 / 含候选 / FE 官方提示三种 regime）。
      LLM 臂在配置 <code>BASELINE_LLM_BASE_URL/KEY/MODEL</code> 时为 live 单次调用，否则回放同 GLM 部署的归档真实回答（标注 recorded）。
      本套件按契约<b>不读取任何真值/关键词</b>；准确率评分在 benchmark 侧完成。
    </p>
    <p class="note" v-if="message" :class="{ err: messageIsErr }">{{ message }}</p>
    <table>
      <thead>
        <tr><th>场景</th><th>数据集</th><th>角色</th><th>行×列</th><th>操作</th></tr>
      </thead>
      <tbody>
        <tr v-for="s in scenarios" :key="s.case_id">
          <td><code>{{ s.case_id }}</code></td>
          <td>{{ s.dataset }}</td>
          <td>{{ s.role }}</td>
          <td>{{ s.rows }} × {{ s.columns }}</td>
          <td class="ops">
            <button :disabled="busy" @click="run(s.case_id, 'pca')">PCA</button>
            <button :disabled="busy" @click="run(s.case_id, 'fe')">FE 协议</button>
            <button :disabled="busy" @click="run(s.case_id, 'llm', 'no_candidates')">裸LLM(无候选)</button>
            <button v-if="s.dataset === 'tep'" :disabled="busy" @click="run(s.case_id, 'llm', 'with_candidates')">裸LLM(含候选)</button>
            <button v-if="s.dataset === 'tep'" :disabled="busy" @click="run(s.case_id, 'llm', 'fe_official')">LLM(FE官方)</button>
          </td>
        </tr>
      </tbody>
    </table>
    <details v-if="last"><summary>最近一次结果（{{ last.case_id }} · {{ last.arm }}<template v-if="last.regime"> · {{ last.regime }}</template>）— 已存 {{ last.saved_to }}</summary>
      <pre>{{ JSON.stringify(last, null, 2) }}</pre>
    </details>
    <footer>
      baselines/baseline-suite · 上游快照：<code>baselines/FaultExplainer</code> @ 2fcfee9（MIT）·
      复现流程见 <code>docs/benchmark/baseline-suite-pipeline.md</code>
    </footer>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const scenarios = ref([])
const last = ref(null)
const busy = ref(false)
const message = ref('')
const messageIsErr = ref(false)

onMounted(async () => {
  try { scenarios.value = await $fetch('/api/scenarios') }
  catch (e) { message.value = '场景列表加载失败：' + e.message; messageIsErr.value = true }
})

async function run(caseId, arm, regime) {
  busy.value = true
  message.value = `运行 ${caseId} · ${arm}${regime ? ' · ' + regime : ''} …`
  messageIsErr.value = false
  try {
    last.value = await $fetch(`/api/diagnose/${caseId}`, { method: 'POST', body: { arm, regime } })
    message.value = `完成 ${caseId} · ${arm}${regime ? ' · ' + regime : ''}（${last.value.mode || 'deterministic'}）`
  } catch (e) {
    message.value = '失败：' + (e.data?.statusMessage || e.message)
    messageIsErr.value = true
  } finally { busy.value = false }
}
</script>

<style>
body { font-family: "Source Han Sans SC", "Noto Sans SC", system-ui, sans-serif; color:#1c2733; margin:0; background:#f4f7fb; }
.wrap { max-width: 980px; margin: 0 auto; padding: 32px 24px 64px; }
h1 { font-size: 22px; border-bottom: 3px solid #1c2733; padding-bottom: 8px; }
.sub { font-size: 14px; color: #5a6a7a; font-weight: 400; }
.note { font-size: 13px; color: #40506a; background: #fff; border: 1px solid #d9e2ec; border-radius: 6px; padding: 10px 14px; line-height: 1.7; }
.note.err { color: #b42323; border-color: #e4b6b6; }
table { width: 100%; border-collapse: collapse; margin-top: 16px; background: #fff; font-size: 13px; }
th, td { border: 1px solid #d9e2ec; padding: 7px 10px; text-align: left; }
th { background: #eef3f9; }
.ops button { margin-right: 6px; padding: 4px 9px; font-size: 12px; cursor: pointer; border: 1px solid #1f5eff; background: #fff; color: #1f5eff; border-radius: 4px; }
.ops button:hover { background: #1f5eff; color: #fff; }
.ops button:disabled { opacity: .5; cursor: wait; }
details { margin-top: 14px; }
pre { background: #0f1822; color: #d8e4f2; padding: 14px; border-radius: 6px; font-size: 12px; overflow-x: auto; max-height: 480px; }
footer { margin-top: 26px; font-size: 12px; color: #5a6a7a; border-top: 1px solid #d9e2ec; padding-top: 10px; }
code { background: #eef3f9; padding: 1px 4px; border-radius: 3px; }
</style>
