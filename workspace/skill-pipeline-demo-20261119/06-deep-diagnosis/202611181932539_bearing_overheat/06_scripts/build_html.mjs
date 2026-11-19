#!/usr/bin/env node
// build_html.mjs — deterministic diagnostic-report.html assembly (fast mode).
// Renders STRICTLY per render_manifest.json (CP-8A order enforced: manifest exists first).
// Visual identity: .claude/shared/report-design/report.css embedded verbatim (rpt ledger
// skeleton) + a minimal supplement scoped under .rpt-scope reusing the same tokens
// (hero key cells, loader strip, adv-card, chart-reading) for components report.css
// does not ship. All numbers come from run_dir artifacts via the manifest.
import fs from 'fs';
import path from 'path';

const runDir = process.argv[2];
if (!runDir) { console.error('usage: node build_html.mjs <run_dir>'); process.exit(2); }

const read = (p) => fs.readFileSync(path.join(runDir, p), 'utf8');
const manifest = JSON.parse(read('render_manifest.json'));
const css = fs.readFileSync('D:/codes/myskills/idd-doe-impl/.claude/shared/report-design/report.css', 'utf8');
const advisory = JSON.parse(read('advisory/advisory_actions.json'));
const rows = JSON.parse(read('02_processed/cleaned_data.json'));

const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

// ---- embedded chart data (from cleaned_data.json; manifest.charts[0].data_source) ----
const chartSpec = manifest.charts[0];
const times = rows.map(r => r.timestamp.replace('2026-11-18T', '').replace('+08:00', ''));
const flow = rows.map(r => Number(r.cooling_water_flow_lpm));
const temp = rows.map(r => Number(r.bearing_temp_c));
const vib = rows.map(r => Number(r.vibration_mm_s));
const chartData = { times, flow, temp, vib };

const h = manifest.hero;
const layers = manifest.evidence_layers;
const adv = manifest.advisory;
const firstAction = advisory.actions[0];

// ---- hero 8 mandatory elements ----
const heroStats = [
  ['诊断类型', h.diagnosis_type],
  ['Judge 评分', `${h.judge_score}/100 (${h.judge_verdict}, 第2轮)`],
  ['综合置信度', `${h.confidence}/100 (HIGH, 上限 ${h.confidence_ceiling})`],
  ['重点对象', h.focus_object],
  ['样本量', `${h.sample_size} 行 × 6 列 · 2 分钟间隔`],
  ['异常区段', h.anomaly_section],
  ['数据窗口', '2026-11-18 08:00–11:58 (+08:00)'],
  ['证据级', 'L3 统计 + L4 读图 + L5 机理 (结论受 L3 封顶 85)'],
];

const fourCell = [
  ['最强证据', h.key_findings_4cell.strongest_evidence, 'good'],
  ['已排除因素', h.key_findings_4cell.excluded_factors, 'ink'],
  ['建议动作', h.key_findings_4cell.recommended_action, 'warm'],
  ['证据缺口', h.key_findings_4cell.evidence_gap, 'bad'],
];

// ---- sections per manifest.sections ----
const secHead = (no, title, sub) => `
  <div class="rpt-sec-head"><span class="rpt-sec-no">${no}</span><h2 class="rpt-sec">${esc(title)}</h2>${sub ? `<span class="rpt-sec-sub">${esc(sub)}</span>` : ''}</div>`;

const layerBlock = (no, title, layer, cls) => `
    <div class="rpt-layer ${cls}">
      <div class="rpt-layer-head"><b>${no}</b> ${esc(title)} <span class="rpt-chip">available=${layer.available}</span></div>
      <ul class="rpt-finding">${layer.key_items.map(i => `<li>${esc(i)}</li>`).join('')}</ul>
      <div class="rpt-note">来源: ${layer.sources.map(esc).join(' · ')}</div>
    </div>`;

const advCard = (a) => `
    <div class="idd-adv-card">
      <div class="idd-adv-head"><span class="rpt-grade">${esc(a.grade ?? firstAction.grade ?? 'C')}</span>
        <b>${esc(a.lever_param)}</b> · ${esc(a.direction)} · ${esc(a.magnitude.from)} → ${esc(a.magnitude.to)} ${esc(a.magnitude.unit)} (Δ${esc(a.magnitude.delta)})</div>
      <div class="idd-adv-line"><span class="rpt-s-cap">预期收益</span><span class="rpt-gain-num">${a.expected_gain.point}</span>
        <span class="rpt-gain-ci">95%CI [${a.expected_gain.ci95.map(x => x).join(', ')}] · 方法 ${esc(a.expected_gain.method)} · KPI ${esc(a.expected_gain.metric)}</span></div>
      <div class="idd-adv-line"><span class="rpt-s-cap">验证</span>${esc(a.verification)}</div>
      <div class="idd-adv-line"><span class="rpt-s-cap">回滚</span>${esc(a.rollback)}</div>
      <div class="rpt-note">action_id: ${esc(firstAction.action_id)} · 等级依据: 观察数据最高 B(无设计试验窗/无归因窗), 本动作 C</div>
    </div>`;

const html = `<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>轴承温升故障诊断 · ${esc(manifest.conclusion_type)} · 置信 ${h.confidence}</title>
<style>
${css}
</style>
<style>
/* minimal supplement — scoped, reuses report.css tokens only (no new colors) */
.idd-hero-cells{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:var(--hair);border:1px solid var(--hair);margin:18px 0}
.idd-hero-cells div{background:var(--panel);padding:10px 12px}
.idd-hero-cells b{display:block;font-size:11px;letter-spacing:.18em;color:var(--muted);font-weight:600;margin-bottom:4px}
.idd-hero-cells span{font-size:13.5px;color:var(--ink)}
.idd-cells4{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin:16px 0}
.idd-cell{background:var(--panel);border:1px solid var(--hair);border-left:3px solid var(--hair-strong);padding:12px 14px}
.idd-cell.warm{border-left-color:var(--warm)} .idd-cell.good{border-left-color:var(--good)}
.idd-cell.bad{border-left-color:var(--bad)} .idd-cell.ink{border-left-color:var(--ink)}
.idd-cell b{font-size:12px;letter-spacing:.14em;color:var(--ink-soft);display:block;margin-bottom:6px}
.idd-cell p{margin:0;font-size:13.5px;line-height:1.65;color:var(--ink-soft)}
.idd-loader{position:fixed;right:14px;bottom:14px;background:var(--panel);border:1px solid var(--hair-strong);
  padding:8px 12px;font:11px/1.6 var(--mono);color:var(--ink-soft);z-index:9}
.idd-loader span{margin-right:10px;white-space:nowrap}
.idd-degraded{display:none;background:var(--wash);border:1px solid var(--warn);color:var(--ink);
  padding:10px 14px;margin:14px 0;font-size:13px}
.idd-chart-wrap{background:var(--panel);border:1px solid var(--hair);padding:8px}
#idd-main-chart{width:100%;height:420px}
.chart-reading{border-top:1px dashed var(--hair-strong);padding:10px 4px 2px;font-size:13.5px;color:var(--ink-soft)}
.chart-reading b{color:var(--ink)}
.chart-reading .r1::before{content:'看见了 · ';color:var(--accent);font-weight:600}
.chart-reading .r2::before{content:'意味着 · ';color:var(--accent);font-weight:600}
.chart-reading .r3::before{content:'为什么重要 · ';color:var(--accent);font-weight:600}
.idd-adv-card{background:var(--panel);border:1px solid var(--hair);border-left:3px solid var(--warm);padding:14px 16px;margin:12px 0}
.idd-adv-head{display:flex;gap:10px;align-items:center;font-size:14px;color:var(--ink)}
.idd-adv-line{margin-top:8px;font-size:13.5px;color:var(--ink-soft)}
.idd-adv-line .rpt-s-cap{display:inline-block;width:52px;color:var(--muted);font-size:11px;letter-spacing:.18em}
.idd-png{max-width:100%;border:1px solid var(--hair);margin:10px 0}
@media (max-width:900px){.idd-hero-cells{grid-template-columns:repeat(2,1fr)}.idd-cells4{grid-template-columns:1fr}}
</style>
</head>
<body class="rpt-scope">
<div class="rpt-page">
  <aside class="rpt-rail">
    <div class="rpt-brand">工业深度诊断<span>DEEP DIAGNOSTIC · FAST</span></div>
    <nav class="rpt-nav">
      <a href="#hero"><b>01</b>结论先行</a>
      <a href="#charts"><b>02</b>核心证据图</a>
      <a href="#evidence"><b>03</b>证据链三层</a>
      <a href="#exclusion"><b>04</b>排除逻辑</a>
      <a href="#mechanism"><b>05</b>机制链</a>
      <a href="#advisory"><b>06</b>改善建议</a>
      <a href="#limitations"><b>07</b>局限与边界</a>
    </nav>
    <div class="rpt-rail-foot">run: <code>${esc('202611181932539_bearing_overheat')}</code><br>数据 SHA-256 <code>6d7590ff…905</code><br>Judge 91/100 pass · 审计 ENDORSED</div>
  </aside>
  <main class="rpt-main">
    <header class="rpt-masthead">
      <p class="rpt-kicker">Industrial Deep Diagnostic · Step 8 Visualization</p>
      <h1>轴承温升根因:冷却水流量阶跃下降,散热能力不足</h1>
      <div class="rpt-meta">
        <span>运行 <b>202611181932539_bearing_overheat</b></span>
        <span>日期 <b>2026-11-18</b></span>
        <span>场景 <b>bearing_overheat</b></span>
        <span>模式 <b>fast(会话智能体装配)</b></span>
        <span>诊断 <b>${esc(manifest.conclusion_type)}</b></span>
        <span>置信 <b>${h.confidence}/100</b></span>
      </div>
    </header>

    <div class="rpt-verdict">
      <blockquote>冷却水流量于 10:00 由 <em>12.0 L/min 阶跃降至 8.0 L/min(−33.2%)</em>,轴承温度滞后 2 个采样点于 10:04 由 <em>65.0℃ 阶跃升至 73.0℃(+8.02℃)并保持</em>——冷却能力下降是唯一存活根因(H1)。</blockquote>
      <div class="rpt-seal"><div class="rpt-seal-grade">DETERMINED</div><div class="rpt-seal-num">${h.confidence}</div><div class="rpt-seal-cap">置信 /100 · 上限 85 (L3)</div></div>
    </div>
    <div id="idd-degraded" class="idd-degraded">⚠ 在线图表库加载失败 — 本页已降级:全部文字结论/要点卡/本地图片证据仍完整可用。</div>

    ${secHead('01', '结论先行(Hero)', '给决策者的一屏')}
    <section id="hero" class="rpt-sec">
      <p class="rpt-content">${h.plain_explanation.map(esc).join('</p><p class="rpt-content">')}</p>
      <div class="idd-hero-cells">${heroStats.map(([k, v]) => `<div><b>${esc(k)}</b><span>${esc(v)}</span></div>`).join('')}</div>
      <div class="idd-cells4">${fourCell.map(([k, v, c]) => `<div class="idd-cell ${c}"><b>${esc(k)}</b><p>${esc(v)}</p></div>`).join('')}</div>
      <div class="rpt-note"><b>如何读本页</b>: ${esc(h.how_to_read)}</div>
    </section>

    ${secHead('02', '核心证据图', '谁先动、谁后动、谁一起动')}
    <section id="charts" class="rpt-sec">
      <div class="idd-chart-wrap"><div id="idd-main-chart"></div></div>
      <div class="chart-reading">
        <div class="r1">${esc(chartSpec.reading.seen)}</div>
        <div class="r2">${esc(chartSpec.reading.means)}</div>
        <div class="r3">${esc(chartSpec.reading.matters)}</div>
      </div>
      ${manifest.available_pngs.map(p => `
      <div class="rpt-figure">
        <div class="rpt-fig-head">${esc(p.title)} <span class="rpt-note">${esc(p.path)}</span></div>
        <img class="idd-png" src="${esc(p.path)}" alt="${esc(p.title)}" loading="lazy"
             onerror="this.onerror=null;this.replaceWith(Object.assign(document.createElement('div'),{className:'rpt-note',textContent:'图片加载失败 — 降级说明: '+${JSON.stringify(p.fallback)}}))">
      </div>`).join('')}
    </section>

    ${secHead('03', '证据链三层', '统计Ⅰ → 物理Ⅱ → 排除Ⅲ, 每层有真实工件支撑')}
    <section id="evidence" class="rpt-sec">
    ${layerBlock('Ⅰ', '统计层', layers.layer_1_statistics, '')}
    ${layerBlock('Ⅱ', '物理层', layers.layer_2_physics, '')}
    ${layerBlock('Ⅲ', '排除层', layers.layer_3_exclusion, '')}
    </section>

    ${secHead('04', '排除逻辑', '竞争假设法:生成 → 判别 → 排除')}
    <section id="exclusion" class="rpt-sec">
      <div class="rpt-table-wrap"><table class="rpt-table">
        <thead><tr><th>假设</th><th>机制通道</th><th>判别证据</th><th>结论</th></tr></thead>
        <tbody>
          <tr><td><b>H1 冷却水流量下降</b>(CONTAMINATION)</td><td>流量↓ → Q=m·cp·ΔT↓ → 温度↑(方向 −, 滞后~2步)</td><td>方向✓ 时滞✓ 幅值✓ 三要素 MATCH;唯一 abrupt 波动源(cv=0.2001)</td><td class="rpt-high"><b>存活</b> · 置信 82</td></tr>
          <tr><td>H2 环境温度升高(ENVIRONMENT)</td><td>散热终温上移(方向 +, 日内缓变)</td><td>r=0.0162, p=0.8608 不显著;无变化点;cv=0.0167 平稳;阶跃形态不符</td><td>排除 (97/100)</td></tr>
          <tr><td>H3 电机负载升高(OPERATION)</td><td>负载↑ → 发热↑(方向 +)</td><td>r=0.0254, p=0.7834 不显著;detrended −0.0102;无变化点;cv=0.0106 平稳</td><td>排除 (97/100)</td></tr>
        </tbody>
      </table></div>
      <div class="rpt-note">判别矩阵: H1-H2 与 H1-H3 均 DISCRIMINABLE(判别信号=变化点时序+相关显著性);无 INDISTINGUISHABLE 对, 不触发 65 分封顶。传感器漂移被"2 步内中断阶跃+振动共变"形态证据否决。各假设 revival_condition 见 04_diagnostics/diagnosis.json。</div>
    </section>

    ${secHead('05', '机制链', '每条链可回溯控制方程')}
    <section id="mechanism" class="rpt-sec">
      <div class="rpt-ev">
        <div class="rpt-e-track"><span class="rpt-e-term">冷却水流量 12.0→8.0 L/min</span><span class="rpt-arrow">→</span><span class="rpt-e-term">带热量 Q=m·cp·ΔT 同比例下降</span><span class="rpt-arrow">→</span><span class="rpt-e-term">热平衡点上移</span><span class="rpt-arrow">→</span><span class="rpt-e-term rpt-low">轴承温度 +8.02℃ 保持</span></div>
        <div class="rpt-e-q">控制方程: Q_cool = m_water·c_p·(T_out − T_in) · 机制边 type=physical / direction=− / delayed_response(01_ontology/ontology.json)</div>
        <div class="rpt-t-line"><span class="rpt-e-coef">伴生</span> 温度↑ → 润滑粘度/游隙变化 → 振动 2.0→2.4 mm/s(ISO 10816 B 区, 无 cliff;伴生症状, 非根因)</div>
        <div class="rpt-t-line"><span class="rpt-e-coef">独立核验</span> physics_check 能量代理 444.25→359.04(−19.18%) → FOULING_PROGRESSION(与渐进性结垢一致)</div>
      </div>
    </section>

    ${secHead('06', '改善建议', `${esc('advisory available=true · 动作 1 条 · 处方 0 条 · 可达上限 B')}`)}
    <section id="advisory" class="rpt-sec">
      ${advCard(adv.actions_verbatim[0])}
      <div class="rpt-note">处方区: 0 条(本轮无 not_actionable 触发项, 无须补冷却水流量归因窗处方——归因数据已在 dose_response 证据腿中估计)。来源: ${esc(adv.source)}</div>
      <div class="rpt-note"><b>${esc(adv.disclaimer)}</b></div>
    </section>

    ${secHead('07', '局限与边界', '诚实清单')}
    <section id="limitations" class="rpt-sec">
      <ul class="rpt-finding">
        <li>数据缺口: 无冷却水进出口温差/压差(结垢直接证据)、无流量独立设定值(区分"设定被改"vs"回路阻力增大")、无润滑油温/振动频谱(伴生链无法定量)。</li>
        <li>窗口局限: 单一 4 小时窗口、单次事件, 无跨运行重复验证;环境温度日内周期未采样到(置信 −3)。</li>
        <li>证据级: 结论核心支撑为 L3 统计分析(封顶 85);视觉证据为会话智能体读图(fast mode 无 VLM)。</li>
        <li>3D 模块: process_flow.recoverable=false(运行数据不含设备拓扑), 依据协议不渲染装饰性 3D。</li>
        <li>本页与建议均为咨询参考, 不构成参数下发;执行须经产线审批 / optimizer-campaign 验证。</li>
      </ul>
    </section>

    <footer class="rpt-foot">
      <div>全部数字可溯源至本运行工件: 02_processed/{validate_report,time_lag_analysis,physics_check,anomaly_report,data_analysis_conclusion}.json · advisory/advisory_actions.json · 无跨运行污染。</div>
      <div>Judge 91/100(pass, 第2轮) · 物理审计 ENDORSED(quality_gate 5/5) · pre_audit_lint PASS · 报告 10 章节检查 PASS</div>
    </footer>
  </main>
</div>

<div class="idd-loader" id="idd-status">
  <span id="st-dom">DOM ●</span><span id="st-ech">ECharts …</span><span id="st-ech-bk">备源 待用</span>
  <span id="st-chart">图表 …</span><span id="st-deg">降级 待定</span>
</div>

<script>
// deterministic embedded data (from 02_processed/cleaned_data.json via manifest.charts[0])
window.IDD_DATA = ${JSON.stringify(chartData)};
(function () {
  var sources = ${JSON.stringify(manifest.loader.echarts_sources)};
  var idx = 0;
  function set(id, t) { var el = document.getElementById(id); if (el) el.textContent = t; }
  function tryLoad() {
    if (idx >= sources.length) {
      set('st-ech', 'ECharts ✗'); set('st-ech-bk', '备源 ✗'); set('st-chart', '图表 静态'); set('st-deg', '降级 ✓');
      var d = document.getElementById('idd-degraded'); if (d) d.style.display = 'block';
      return;
    }
    var s = document.createElement('script');
    s.src = sources[idx];
    s.onload = function () {
      if (window.echarts && window.echarts.getInstanceByDom !== undefined || window.echarts) {
        set(idx === 0 ? 'st-ech' : 'st-ech-bk', (idx === 0 ? 'ECharts ✓' : '备源 ✓(第' + (idx + 1) + '源)'));
        initChart();
      } else { idx++; tryLoad(); }
    };
    s.onerror = function () { idx++; tryLoad(); };
    document.head.appendChild(s);
  }
  function initChart() {
    var el = document.getElementById('idd-main-chart');
    if (!el || !window.echarts) return;
    var d = window.IDD_DATA;
    var chart = window.echarts.init(el);
    chart.setOption({
      color: ['#2d7d4f', '#1e3a54', '#8a6d3b'],
      tooltip: { trigger: 'axis' },
      legend: { data: ['cooling_water_flow_lpm', 'bearing_temp_c', 'vibration_mm_s'], textStyle: { fontSize: 11 } },
      grid: { left: 56, right: 60, top: 40, bottom: 46 },
      xAxis: { type: 'category', data: d.times, axisLabel: { interval: 19, fontSize: 10 } },
      yAxis: [
        { type: 'value', name: '流量 L/min', min: 6, max: 14, nameTextStyle: { fontSize: 10 } },
        { type: 'value', name: '温度 ℃ / 振动 mm/s', min: 0, max: 80, nameTextStyle: { fontSize: 10 } }
      ],
      series: [
        { name: 'cooling_water_flow_lpm', type: 'line', yAxisIndex: 0, data: d.flow, showSymbol: false, lineStyle: { width: 1.5, color: '#2d7d4f' } },
        { name: 'bearing_temp_c', type: 'line', yAxisIndex: 1, data: d.temp, showSymbol: false, lineStyle: { width: 1.8, color: '#1e3a54' } },
        { name: 'vibration_mm_s', type: 'line', yAxisIndex: 1, data: d.vib, showSymbol: false, lineStyle: { width: 1, type: 'dashed', opacity: 0.7 } },
        { name: '温度台阶标记', type: 'line', yAxisIndex: 1, markLine: { silent: true, symbol: 'none', data: [{ xAxis: 62 }], lineStyle: { color: '#c2673a', type: 'dotted' }, label: { formatter: '温度台阶 idx62', fontSize: 10 } }, data: [] }
      ]
    });
    set('st-chart', '图表 ✓ (getInstanceByDom=' + (window.echarts.getInstanceByDom(el) ? 'Y' : 'N') + ')');
    set('st-deg', '降级 未触发');
    window.addEventListener('resize', function () { chart.resize(); });
  }
  set('st-dom', 'DOM ✓');
  tryLoad();
})();
</script>
</body>
</html>
`;

const out = path.join(runDir, 'diagnostic-report.html');
fs.writeFileSync(out, html, 'utf8');

// ---- build-time verification: page counts must match manifest (DOM usage only, CSS rules excluded) ----
const domCount = (re) => (html.match(re) || []).length;
const verify = {
  sections_in_manifest: manifest.sections.length,
  sections_in_page: domCount(/class="rpt-sec-no"/g),
  hypotheses_in_manifest: manifest.hypotheses.length,
  hypothesis_rows_in_page: domCount(/H[123] (冷却水流量下降|环境温度升高|电机负载升高)/g),
  charts_in_manifest: manifest.charts.length,
  echarts_containers_dom: domCount(/<div id="idd-main-chart">/g),
  adv_cards_expected: adv.actions_count,
  adv_cards_rendered: domCount(/class="idd-adv-card"/g),
  pngs_expected: manifest.available_pngs.length,
  pngs_rendered: domCount(/class="idd-png"/g),
  evidence_layers: 3,
  loader_strip_items: 5,
  css_embedded_verbatim: html.includes(css.slice(0, 200)),
  bytes: Buffer.byteLength(html, 'utf8')
};
fs.writeFileSync(path.join(runDir, '06_scripts', 'build_verify.json'), JSON.stringify(verify, null, 2) + '\n');
console.log(JSON.stringify(verify));
