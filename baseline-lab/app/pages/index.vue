<script setup>
// 01 — Reproduction audit.
// The headline answer to "did the benchmark actually reproduce the baselines?"
const { data, refresh, pending } = await useFetch('/api/audit', { key: 'audit' });

function tone(v) {
  if (v === 'reproduced-bit-faithful' || v === 'reproduced-and-verifiable') return 'ok';
  if (v === 'archived-not-runnable' || v === 'cloned-not-runnable' || v === 'vendored-not-runnable') return 'warn';
  if (v === 'no-code-released' || v === 'citation-only' || v === 'framework-not-in-repo') return 'bad';
  return 'info';
}
function toneLabel(v) {
  return {
    'reproduced-bit-faithful': '已复刻 · 逐位核对',
    'reproduced-and-verifiable': '已复现 · 可验证',
    'archived-not-runnable': '仅有归档 · 不可执行',
    'cloned-not-runnable': '已克隆 · 不可运行',
    'vendored-not-runnable': '已入库 · 不可运行',
    'no-code-released': '未开源 · 无法复现',
    'citation-only': '仅引用数字',
    'framework-not-in-repo': '框架未安装',
    'archived-results': '读取归档',
  }[v] || v;
}
</script>

<template>
  <div>
    <div class="page-head">
      <h1>复现审计 · Reproduction Audit</h1>
      <p>
        本页回答一个可证伪的问题：<strong>IDD 基准里的对照算法，究竟哪些被真正复现并可投入运行？</strong>
        每一项结论都附机器可核验的证据（脚本路径 / 校验门禁 / 实测输出），而非断言。
      </p>
    </div>

    <div v-if="pending" class="panel">加载中…</div>

    <template v-else-if="data">
      <!-- headline -->
      <div class="grid g4" style="margin-bottom: 16px">
        <div class="stat accent">
          <div class="k">本实验室可运行算法</div>
          <div class="v">{{ data.headline.lab_algorithms_runnable }}</div>
          <div class="s">of {{ data.headline.lab_modules_declared }} declared</div>
        </div>
        <div class="stat" :class="data.headline.lab_modules_missing ? 'warn' : 'ok'">
          <div class="k">模块缺失</div>
          <div class="v">{{ data.headline.lab_modules_missing }}</div>
          <div class="s">尚未实现的声明模块</div>
        </div>
        <div class="stat warn">
          <div class="k">审计前可运行的对照</div>
          <div class="v">{{ data.headline.incumbent_runnable_before }}</div>
          <div class="s">仅经典 PCA 脚本</div>
        </div>
        <div class="stat bad">
          <div class="k">仅有引用 / 无法复现</div>
          <div class="v">{{ data.headline.citation_only_comparators }}</div>
          <div class="s">文献数字或未开源实现</div>
        </div>
      </div>

      <!-- the answer -->
      <div class="panel">
        <h2>结论</h2>
        <div class="callout bad" style="margin-top: 4px">
          <strong>审计发现（审计前状态）：</strong>仓库里<strong>真正可运行</strong>的对照算法只有 1 个——确定性 PCA 脚本
          <code>scripts/benchmark/baseline_pca.mjs</code>。其余所谓“基线”分三类问题：
          <ul class="tight">
            <li>
              <strong>裸 LLM 基线是冻结的答案归档，没有执行通路。</strong>
              <code>results/benchmark/baseline_fe_answers/</code> 里 23 份回答是真实模型输出，但
              <code>baseline_llm.mjs check</code> 只打印一段“执行契约”让人手工去跑；
              25 份应有答案里还缺 2 份（<code>tep_d00_normal_control.*</code>）。
            </li>
            <li>
              <strong>FaultExplainer 克隆了但跑不起来。</strong>
              <code>baselines/FaultExplainer</code>（commit 2fcfee9）是完整真实克隆，
              但 <code>backend/.env</code> 的 <code>OPENAI_API_KEY</code> 为空、无 sklearn/fastapi 环境、
              <code>backend/results.txt</code> 为 0 字节——仓库内不存在端到端执行记录。
            </li>
            <li>
              <strong>文档声称的 6 个基线里有 4 类从未实现。</strong>
              <code>docs/publication-strategy-report.md</code> §5.2 的对比矩阵列了
              CoT、ReAct 工具调用、AutoGen 多代理讨论、XGBoost/LSTM，但仓库中没有任何可运行实现。
            </li>
          </ul>
        </div>
        <div class="callout ok">
          <strong>本实验室的动作：</strong>{{ data.answer }}
        </div>
      </div>

      <!-- incumbent findings -->
      <div class="panel">
        <h2>一、仓库原有对照的实测复核</h2>
        <p class="panel-sub">对仓库既有基线逐项实测，判定其真实可运行程度。</p>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>对照</th>
                <th>判定</th>
                <th>可运行</th>
                <th>证据 / 阻塞原因</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="f in data.incumbent_findings" :key="f.id">
                <td style="min-width: 190px">
                  <div style="font-weight: 550">{{ f.label }}</div>
                  <div class="tiny muted mono">{{ f.id }}</div>
                </td>
                <td><span class="badge" :class="tone(f.verdict)">{{ toneLabel(f.verdict) }}</span></td>
                <td>
                  <span class="badge" :class="f.runnable ? 'ok' : 'bad'">
                    {{ f.runnable ? 'yes' : 'no' }}
                  </span>
                </td>
                <td>
                  <div class="small dim" style="margin-bottom: 4px">{{ f.note }}</div>
                  <details>
                    <summary>证据</summary>
                    <pre>{{ JSON.stringify(f.evidence, null, 1) }}</pre>
                  </details>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- lab inventory -->
      <div class="panel">
        <h2>二、本实验室已复现 / 已实现的对照算法</h2>
        <p class="panel-sub">
          全部为可执行模块（<code>meta</code> + <code>run(ctx)</code>）。确定性算法离线运行；
          LLM 算法通过真实 provider 发起调用。
        </p>

        <h3 style="margin-top: 4px">实验室新增的关键复刻</h3>
        <div class="table-wrap" style="margin-bottom: 14px">
          <table>
            <thead><tr><th>复刻</th><th>判定</th><th>证据</th></tr></thead>
            <tbody>
              <tr v-for="f in data.lab_additions" :key="f.id">
                <td style="min-width: 210px">
                  <div style="font-weight: 550">{{ f.label }}</div>
                  <div class="small dim" style="margin-top: 4px">{{ f.note }}</div>
                </td>
                <td><span class="badge" :class="tone(f.verdict)">{{ toneLabel(f.verdict) }}</span></td>
                <td>
                  <details open>
                    <summary>证据</summary>
                    <pre>{{ JSON.stringify(f.evidence, null, 1) }}</pre>
                  </details>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <h3>全部可运行算法</h3>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>名称</th>
                <th>族</th>
                <th>确定性</th>
                <th>依赖</th>
                <th>适用域</th>
                <th>协议</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="a in data.lab_runnable" :key="a.id">
                <td class="mono">{{ a.id }}</td>
                <td style="min-width: 220px">{{ a.label }}</td>
                <td><span class="badge" :class="a.family === 'llm' ? 'violet' : a.family === 'official' ? 'cyan' : a.family === 'supervised' ? 'info' : ''">{{ a.family }}</span></td>
                <td>
                  <span class="badge" :class="a.deterministic ? 'ok' : 'warn'">{{ a.deterministic ? 'yes' : 'stochastic' }}</span>
                </td>
                <td class="tiny">{{ a.requires_provider ? 'LLM provider' : 'offline' }}</td>
                <td class="tiny mono">{{ a.domains ? a.domains.join(',') : 'all' }}</td>
                <td class="small dim" style="max-width: 44ch">{{ a.description }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="data.lab_missing.length" class="callout warn" style="margin-top: 12px">
          <strong>尚未实现的声明模块（{{ data.lab_missing.length }}）：</strong>
          <span class="mono tiny">{{ data.lab_missing.map((m) => m.file).join(', ') }}</span>
        </div>
      </div>

      <!-- citation only -->
      <div class="panel">
        <h2>三、文档声称但无法复现的对照（诚实缺口）</h2>
        <p class="panel-sub">
          这些对照在文档里被当作基线使用，但上游没有可运行实现。本实验室不掩盖它们，而是逐条登记缺口与替代方案。
        </p>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>对照</th>
                <th>状态</th>
                <th>缺口原因</th>
                <th>需要什么</th>
                <th>本仓库替代方案</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="c in data.citation_only" :key="c.id">
                <td style="min-width: 200px">
                  <div style="font-weight: 550">{{ c.label }}</div>
                  <div class="tiny muted">{{ c.claimed_in }}</div>
                </td>
                <td><span class="badge" :class="tone(c.status)">{{ toneLabel(c.status) }}</span></td>
                <td class="small dim" style="max-width: 40ch">{{ c.reason }}</td>
                <td class="tiny mono">{{ c.upstream }}</td>
                <td class="small" style="max-width: 34ch">{{ c.mitigated_by }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- gates + honesty -->
      <div class="grid g2">
        <div class="panel">
          <h2>四、复现验证门禁</h2>
          <p class="panel-sub">可自行重跑的校验脚本；每一条都是“数字对不上就失败”的硬门禁。</p>
          <table>
            <thead><tr><th>脚本</th><th>证明什么</th></tr></thead>
            <tbody>
              <tr v-for="g in data.verification_gates" :key="g.script">
                <td class="mono tiny">{{ g.script.replace('baseline-lab/', '') }}</td>
                <td class="small dim">{{ g.proves }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="panel">
          <h2>五、真实性红线</h2>
          <p class="panel-sub">实验室强制执行、且在任一数字上可被审查的约束。</p>
          <ul class="tight">
            <li v-for="(h, i) in data.honesty_rules" :key="i">{{ h }}</li>
          </ul>
        </div>
      </div>

      <div class="panel">
        <h2>仓库契约</h2>
        <dl class="kv">
          <dt>repo root</dt><dd>{{ data.repo_root }}</dd>
          <dt>generated</dt><dd>{{ data.generated_at }}</dd>
        </dl>
        <div class="spacer-y" />
        <button class="ghost" @click="refresh()">重新审计</button>
      </div>
    </template>
  </div>
</template>
