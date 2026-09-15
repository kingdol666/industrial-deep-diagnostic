<script setup>
// 04 — Algorithm registry reference.
const { data: state } = await useFetch('/api/state', { key: 'lab-state' });

const open = ref(null);
const famOrder = ['classical', 'supervised', 'official', 'llm'];
const grouped = computed(() => {
  const fams = state.value?.families || {};
  const out = [];
  for (const f of famOrder) {
    const items = (state.value?.algorithms || []).filter((a) => a.family === f);
    if (items.length) out.push({ family: f, label: fams[f] || f, items });
  }
  return out;
});
</script>

<template>
  <div>
    <div class="page-head">
      <h1>算法清单 · Algorithms</h1>
      <p>
        每个条目都是一个可执行模块（<code>meta</code> + <code>async run(ctx)</code>）。
        这里同时列出<strong>已加载</strong>与<strong>声明但缺失</strong>的模块——缺一个就显示一个缺口，不会静默略过。
      </p>
    </div>

    <div class="panel">
      <h2>模块健康度</h2>
      <p class="panel-sub">注册表按清单动态加载；导入失败的模块被如实标记，不会拖垮整个注册表。</p>
      <div class="table-wrap">
        <table>
          <thead><tr><th>文件</th><th>族</th><th>算法 ID</th><th>状态</th></tr></thead>
          <tbody>
            <tr v-for="m in state?.modules || []" :key="m.file">
              <td class="mono tiny">algorithms/{{ m.file }}</td>
              <td class="tiny">{{ m.family }}</td>
              <td class="mono tiny">{{ m.id || '—' }}</td>
              <td>
                <span class="badge" :class="m.loaded ? 'ok' : 'bad'">{{ m.loaded ? 'loaded' : 'missing' }}</span>
                <span v-if="m.error" class="tiny muted" style="margin-left: 6px">{{ m.error }}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-for="g in grouped" :key="g.family" class="panel">
      <h2>{{ g.label }} <span class="badge info">{{ g.items.length }}</span></h2>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>ID</th><th>名称</th><th>确定性</th><th>依赖</th><th>适用域</th><th>协议说明</th><th>出处</th>
            </tr>
          </thead>
          <tbody>
            <template v-for="a in g.items" :key="a.id">
              <tr>
                <td class="mono tiny">{{ a.id }}</td>
                <td style="min-width: 200px">{{ a.label }}</td>
                <td>
                  <span class="badge" :class="a.deterministic ? 'ok' : 'warn'">{{ a.deterministic ? 'yes' : 'stochastic' }}</span>
                </td>
                <td class="tiny">{{ a.requiresProvider ? 'LLM provider' : 'offline' }}</td>
                <td class="tiny mono">{{ a.domains ? a.domains.join(', ') : 'all' }}</td>
                <td class="small dim" style="max-width: 52ch">{{ a.description }}</td>
                <td>
                  <button class="ghost tiny" style="padding: 2px 8px" @click="open = open === a.id ? null : a.id">
                    {{ open === a.id ? '收起' : '展开' }}
                  </button>
                </td>
              </tr>
              <tr v-if="open === a.id">
                <td colspan="7" style="background: var(--bg-inset)">
                  <dl class="kv">
                    <dt>id</dt><dd>{{ a.id }}</dd>
                    <dt>family</dt><dd>{{ a.family }}</dd>
                    <dt>kind</dt><dd>{{ a.kind }}</dd>
                    <dt>deterministic</dt><dd>{{ a.deterministic }}</dd>
                    <dt>requires provider</dt><dd>{{ a.requiresProvider }}</dd>
                    <dt>needs reference</dt><dd>{{ a.needsReference }}</dd>
                    <dt>needs training</dt><dd>{{ a.needsTraining ?? false }}</dd>
                    <dt>regimes</dt><dd>{{ a.regimes ? a.regimes.join(', ') : '—' }}</dd>
                  </dl>
                  <div v-if="a.provenance" style="margin-top: 8px">
                    <div class="tiny muted">provenance</div>
                    <pre>{{ JSON.stringify(a.provenance, null, 1) }}</pre>
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
    </div>

    <div class="panel">
      <h2>仅引用、无法在本仓库复现的对照</h2>
      <p class="panel-sub">上游未开源或需要外部密钥；本实验室登记缺口并提供替代方案。</p>
      <div class="table-wrap">
        <table>
          <thead><tr><th>对照</th><th>状态</th><th>原因</th><th>替代</th></tr></thead>
          <tbody>
            <tr v-for="c in state?.citation_only || []" :key="c.id">
              <td style="min-width: 190px">
                <div>{{ c.label }}</div>
                <div class="tiny muted">{{ c.claimed_in }}</div>
              </td>
              <td><span class="badge warn">{{ c.status }}</span></td>
              <td class="small dim" style="max-width: 40ch">{{ c.reason }}</td>
              <td class="small" style="max-width: 32ch">{{ c.mitigated_by }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
