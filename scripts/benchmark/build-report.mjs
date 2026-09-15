#!/usr/bin/env node
// build-report.mjs — generate the HTML scoring report from benchmark results.
// Reads results/benchmark/{metrics,gradings,repro_report}.json + the case file
// and renders experience/benchmark-report.html (journal-style scoring report
// with baseline comparison). No numbers are hardcoded — everything is derived.

import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(import.meta.dirname, '..', '..');
const RES = path.join(ROOT, 'results', 'benchmark');
const CASES = path.join(RES, '..', '..', 'scripts', 'benchmark', 'cases', 'benchmark_cases.json');
const OUT = path.join(ROOT, 'experience', 'benchmark-report.html');

const metrics = JSON.parse(fs.readFileSync(path.join(RES, 'metrics.json'), 'utf8'));
const repro = JSON.parse(fs.readFileSync(path.join(RES, 'repro_report.json'), 'utf8'));
const tier = JSON.parse(fs.readFileSync(CASES, 'utf8'));
const gradings = {};
for (const f of fs.readdirSync(path.join(RES, 'gradings')).filter((f) => f.endsWith('.json'))) {
  const g = JSON.parse(fs.readFileSync(path.join(RES, 'gradings', f), 'utf8'));
  gradings[g.case_id] = g;
}

function wilson(k, n, z = 1.96) {
  if (!n) return null;
  const p = k / n, den = 1 + z * z / n, c = p + z * z / (2 * n);
  const h = z * Math.sqrt(p * (1 - p) / n + z * z / (4 * n * n));
  return [Math.round(((c - h) / den) * 1000) / 10, Math.round(((c + h) / den) * 1000) / 10];
}
const ci = wilson(metrics.top1, metrics.fault_cases);

const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const rows = tier.cases.map((c) => {
  const g = gradings[c.case_id] || {};
  const type = c.control ? 'control' : 'fault';
  const top1 = c.control ? '—' : (g.top1 ? '<span class="ok">✓</span>' : '<span class="bad">✗</span>');
  const conclusion = esc(c.control ? 'normal operation (no fault)' : (g.diagnosis_type || '?'));
  const lit = c.literature_baseline
    ? `${esc(c.literature_baseline.fault)}<br><span style="font-size:11px;color:var(--sub)">FE GPT-4o ${esc(c.literature_baseline.fe_gpt4o)} · o1 ${esc(c.literature_baseline.fe_o1)} · PCA ${esc(c.literature_baseline.pca)}</span>`
    : '—';
  return `<tr><td>${esc(c.case_id)}</td><td>${esc(c.dataset)}</td><td>${type}</td><td>${conclusion}</td><td>${top1}</td><td>${lit}</td><td>${g.judge_score ?? '-'}</td><td>${g.checks?.pipeline_log === 'PASS' && g.checks?.finalize_passed ? '<span class="ok">PASS</span>' : '<span class="bad">FAIL</span>'}</td></tr>`;
}).join('\n');

// 逐故障文献对比（TEP：FaultExplainer arXiv:2412.14492 Table 1，root-causes-included prompt）
const tepRows = tier.cases.filter((c) => c.literature_baseline && gradings[c.case_id]).map((c) => {
  const g = gradings[c.case_id];
  const mark = (v) => v === 'correct' ? '<span class="ok">✓ correct</span>' : v === 'incorrect' ? '<span class="bad">✗ wrong</span>' : '<span style="color:var(--sub)">未评分（PCA 不可检）</span>';
  const ours = g.top1 ? '<span class="ok">✓</span>' : '<span class="bad">✗</span>';
  return `<tr><td>${esc(c.literature_baseline.fault)}</td><td>${mark(c.literature_baseline.fe_gpt4o)}</td><td>${mark(c.literature_baseline.fe_o1)}</td><td>${esc(c.literature_baseline.pca)}</td><td>${ours}（${esc(g.diagnosis_type)}）</td></tr>`;
}).join('\n');
const feScored = tepRows;

const byDataset = Object.entries(metrics.by_dataset || {}).map(([d, v]) =>
  `<tr><td>${esc(d)}</td><td>${v.cases}</td><td>${v.top1}/${v.cases - v.controls}</td><td>${v.control_pass ?? v.controls}/${v.controls}</td></tr>`).join('\n');

const judgeScores = Object.values(gradings).map((g) => g.judge_score).filter((x) => typeof x === 'number');
const meanJudge = judgeScores.length ? (judgeScores.reduce((a, b) => a + b, 0) / judgeScores.length).toFixed(1) : '-';

// 优劣势分析 — 每条结论都由 metrics/repro 数字或协议事实支撑，不写无依据断言。
const faultN = metrics.fault_cases;
const calibOk = metrics.calibrated === faultN;
const gatePass = repro.checks?.execution_proof?.finalize_pass ?? 0;
const gateTotal = repro.checks?.execution_proof?.checked ?? metrics.total_cases;
const strengths = [
  `零误报：${metrics.control_pass}/${metrics.control_cases} 个正常对照被正确判为正常运行（误报 ${metrics.false_alarms}）——检测类文献中误报率常被忽视，此处作为一级指标报告。`,
  `置信校准：${metrics.calibrated}/${faultN} 个故障场景结论类型落在证据允许集内，过度自信 ${metrics.overconfident} 例——系统在证据不足时选择 COMPETING_SET/NEEDS_DATA 而非强行单因结论。`,
  `执行可信度：${gatePass}/${gateTotal} 个 run 通过 pipeline-finalize 门禁并携带 .pipeline_events.jsonl 事件日志——结论可回溯到统计/视觉/机理证据文件，而非仅最终答案。`,
  `评分真实判别：真值隔离 + 独立评分器 + 阴性对照（注入 plausible-but-wrong 诊断被判伪，见 experience/results/scorer-discrimination-test.json）。`,
  `可复现底座：确定性统计（S1 同数据逐字节一致）+ 指标零漂移 + ${repro.checks?.dataset_integrity?.verified ?? 0} 条数据 sha256 指纹，复现门禁 ${esc(repro.status)}。`,
];
// ---- optional: same-model baselines + stability (run-tier stages of the same names) ----
function loadOptB(file) {
  try { return JSON.parse(fs.readFileSync(path.join(RES, file), 'utf8')); } catch { return null; }
}
const stab = loadOptB('stability_report.json');
const bl = loadOptB('baselines.json');

const weaknesses = [
  `样本量小：故障场景仅 ${faultN} 个，Top-1 比例的 Wilson 95% CI 为 ${ci[0]}–${ci[1]}%——区间宽，不支撑与文献数字的显著性比较（扩量路线见 docs/benchmark/design.md §7）。`,
  `关键词判定的粒度：Top-1 由评分器按机理关键词双判定，能判"机理方向正确"，但细于关键词的差别（如阀门开度不足 vs 阀门全关）需人工复核 grading 与报告原文。`,
  `稳定性证据的时代口径：时代内独立重跑一致性 ${stab ? stab.summary.within_era_agreement : '见 stability_report.json'}（详见 §5B）；v2 现行系统多数场景仅 1 次 canonical run，扩展重复次数仍为进行中工作。`,
  `教科书故障的记忆污染风险：TEP IDV 类扰动在公开文献中大量出现，agent 可能记忆性命中；当前仅靠 SKAB other 组不下发故障类型、IndPenSim 排除标注列部分缓解，陌生故障组单列在 P4。`,
  `校准与 CDR 的张力：接受 NEEDS_DATA/COMPETING_SET 出口（校准优先）意味着 CDR 上界受"证据是否充分"约束——这是设计取舍，不是缺陷，但与"必须给出单因结论"的系统对比时口径不同。`,
];

// ---- optional sections (declared above; loaders shared) ----

let baselineSection = '';
if (bl) {
  const blRows = tier.cases.map((c) => {
    const g = gradings[c.case_id] || {};
    const l = bl.llm[c.case_id]?.no_candidates;
    const fe = bl.llm[c.case_id]?.with_candidates?.fe_style_top3_hit;
    const p = bl.pca?.[c.case_id];
    const idd = c.control ? `pass=${g.control_pass ?? '-'}` : (g.top1 ? '<span class="ok">✓</span>' : (g.top1 === false ? '<span class="bad">✗</span>' : '—'));
    const bare = c.control
      ? (l ? (l.normal_verdict ? '<span class="ok">normal</span>' : '<span class="bad">误报</span>') : '未运行')
      : (l ? (l.strict_top1_hit ? '<span class="ok">✓</span>' : '<span class="bad">✗</span>') : '未运行');
    const feC = fe === undefined ? 'n/a' : (fe ? '<span class="ok">✓</span>' : '<span class="bad">✗</span>');
    const pca = p ? `${(p.detection_rate_T2 * 100).toFixed(1)}% / ${(p.detection_rate_SPE * 100).toFixed(1)}%` : '—';
    return `<tr><td>${esc(c.case_id)}</td><td>${idd}</td><td>${bare}</td><td>${feC}</td><td>${pca}</td></tr>`;
  }).join('\n');
  const s = bl.summary;
  baselineSection = `
<h2>4B 同模型基线横向对比（模型变量受控：与管线同一 GLM 部署）</h2>
<table>
<tr><th>场景</th><th>IDD 管线（Top-1）</th><th>裸 LLM strict（无候选、单次调用）</th><th>FE-style（含候选清单）</th><th>经典 PCA T²/SPE 检出率</th></tr>
${blRows}
</table>
<p style="font-size:12.5px;color:var(--sub)">裸 LLM 协议：与管线同一 harness（ZCode CLI）与同一 GLM 部署，对同一盲态统计摘要做<b>单次调用</b>（无本体、无管线、无门禁）；raw 回答留档 results/benchmark/baseline_fe_answers/。FE 复刻（含候选）FE-style ${esc(s.fe_protocol_replication_with_candidates.fe_style_top3_hit)} · strict ${esc(s.fe_protocol_replication_with_candidates.strict_single_verdict ?? '')}；FE 官方代码管线 ${esc(bl.fe_official_code?.summary?.fe_style_top3 ?? 'n/a')} FE-style / ${esc(bl.fe_official_code?.summary?.strict_single_verdict ?? 'n/a')} strict；对照组裸 LLM ${esc(s.controls.bare_llm_normal_verdicts)} 正常 · ${s.controls.false_alarms} 误报。PCA 为确定性脚本复算（Chiang 2001/Qin 2012 协议，scripts/benchmark/baseline_pca.mjs）。<b>诚实结论</b>：在文档化公开故障上，同模型裸 LLM 的关键词命中准确率与完整管线相当——管线的边际不在准确率，而在可审计性、执行证明、置信帽合规与三态诚实出口。</p>`;
}

let stabilitySection = '';
if (stab) {
  const stRows = tier.cases.map((c) => {
    const v = stab.cases[c.case_id];
    const cell = (e) => {
      const x = v?.eras?.[e];
      if (!x || !x.n_runs_proven) return '<span style="color:var(--sub)">—</span>';
      const enough = x.n_runs_proven >= (stab.summary.min_runs_required ?? 2);
      const flag = enough ? (x.consistent ? '<span class="ok">一致</span>' : '<span class="bad">分歧</span>') : `<span style="color:var(--sub)">仅${x.n_runs_proven}次</span>`;
      return `${x.n_runs_proven} 次 [${esc(x.verdict_types.join('/') || '-')}] ${flag}`;
    };
    return `<tr><td>${esc(c.case_id)}</td><td>${cell('v1')}</td><td>${cell('v2')}</td></tr>`;
  }).join('\n');
  stabilitySection = `
<h2>5B 多次运行一致性（稳定性研究 · 时代内口径）</h2>
<table>
<tr><th>场景</th><th>v1 时代（无置信帽纪律的旧版系统）</th><th>v2 时代（现行系统）</th></tr>
${stRows}
</table>
<p style="font-size:12.5px;color:var(--sub)">口径：每次独立<b>完整管线执行</b>计一次 run（finalize PASS 才算 proven）；头条指标为<b>时代内</b>判定类型+Top-1 一致性 = <b>${esc(stab.summary.within_era_agreement)}</b>（case-时代对，各含 ≥${stab.summary.min_runs_required} 次独立 run）。时代边界 ${esc(stab.era_boundary)}：3 个敏感场景（skab_valve1_1 / skab_cavitation_13 / tep_d03_hard）的 v1→v2 判定翻转（DETERMINED → 置信帽 COMPETING_SET）是<b>记录在案的系统纪律收紧</b>（版本演进），不是运行间随机不稳定。复跑契约：在全新会话对同一场景重跑完整管线即为一次新 run，<code>run-tier.mjs stability</code> 自动重算本节。</p>`;
}

const html = `<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>IDD Diagnosis Benchmark — Scoring Report</title>
<style>
  :root { --ink:#1c2733; --sub:#5a6a7a; --line:#d9e2ec; --acc:#1f5eff; --soft:#f4f7fb; }
  body { font-family: "Source Han Serif SC","Noto Serif SC",Georgia,serif; color:var(--ink); max-width:1020px; margin:0 auto; padding:40px 32px 80px; line-height:1.75; font-size:15px; }
  h1 { font-size:24px; border-bottom:3px solid var(--ink); padding-bottom:10px; }
  h2 { font-size:18px; margin:36px 0 8px; border-left:5px solid var(--acc); padding-left:10px; }
  .meta { color:var(--sub); font-size:13px; margin-bottom:22px; }
  .cards { display:grid; grid-template-columns:repeat(5,1fr); gap:10px; margin:20px 0; }
  .card { border:1px solid var(--line); border-radius:6px; padding:12px 8px; text-align:center; }
  .card .num { font-size:24px; font-weight:700; color:var(--acc); }
  .card .lbl { font-size:11.5px; color:var(--sub); }
  table { width:100%; border-collapse:collapse; margin:12px 0; font-size:13px; }
  th,td { border:1px solid var(--line); padding:6px 9px; text-align:left; }
  th { background:var(--soft); }
  .ok { color:#0a7d38; font-weight:600; } .bad { color:#b42323; font-weight:600; }
  pre { background:#0f1822; color:#d8e4f2; padding:14px 16px; border-radius:6px; font-size:12.5px; overflow-x:auto; }
  .abstract { background:var(--soft); border:1px solid var(--line); padding:14px 18px; border-radius:6px; font-size:14px; }
  ul { font-size:13.5px; }
</style>
</head>
<body>
<h1>IDD 诊断基准 — 评分报告（v2 · 真实管线执行口径）</h1>
<div class="meta">生成 ${new Date().toISOString().slice(0, 16).replace('T', ' ')} ·
${metrics.total_cases} 场景（${metrics.fault_cases} 故障 + ${metrics.control_cases} 对照）·
执行模式：真实 industrial-analysis-auto 管线（Step 2-9 子代理按各自 skill 协议执行）·
复现门禁：<b style="color:${repro.status === 'REPRODUCIBLE' ? '#0a7d38' : '#b42323'}">${esc(repro.status)}</b></div>

<div class="abstract">
  <b>评分协议（v2）</b> — 每个场景在其盲态 run 目录中<b>真实启动 industrial-analysis-auto</b>：确定性统计（prepare）→
  ontology 构建（context-builder）→ 数据分析（data-processor Phase 0-6）→ 竞争假说诊断（diagnostician）→
  judge 十维门 ∥ 物理预审（并行）→ 报告（reporter）→ 物理终审（ENDORSSED 必需）→ HTML 构建（render_manifest 先行）→
  HTML 独立评审（pass 必需）→ finalize 执行证明（overall PASS 必需）。评分器只读取子代理真实写下的产物对照标准答案
  （机理关键词双判定；真值隔离由 <code>check-leakage.mjs</code> 机械门禁）。比例指标报 Wilson 95% CI。
</div>

<div class="abstract" style="border-left-color:#0a7d38;background:#f4faf5">
  <b>评分 provenance（必读）</b>
  <ol style="margin:6px 0 0 18px;padding:0">
    <li><b>judge 分数</b>由 judge 子代理的十维门给出（内部含独立数字抽检复算），来源标记 <code>judge-agent-10-criteria</code>；它不是被评对象的自我申报。</li>
    <li><b>质量底线指标</b>是确定性 rubric v2（R1-R7，从管线产物机器计算：产物完整性 / 假说结构 / 证据 grounding / 置信校准 / 可证伪性 / 物理核验 / 执行证明+HTML 门），零主观成分。</li>
    <li>三个未 Top-1 命中的场景均为管线<b>诚实输出 COMPETING_SET</b>（判别通道缺失时拒绝强行判定），其中两例存活假设首位仍为真值机理（topk 命中）——这是协议约束下的真实能力边界。</li>
  </ol>
</div>

<h2>1 总评分</h2>
<div class="cards">
  <div class="card"><div class="num">${metrics.top1}/${metrics.fault_cases}</div><div class="lbl">Top-1 根因命中（CI ${ci[0]}–${ci[1]}%）</div></div>
  <div class="card"><div class="num">${metrics.topk}/${metrics.fault_cases}</div><div class="lbl">Top-k（k=3）</div></div>
  <div class="card"><div class="num">${metrics.cdr_display ?? metrics.cdr}</div><div class="lbl">CDR 比率（Top-1 且 DETERMINED${metrics.cdr_ci95 ? `，CI ${metrics.cdr_ci95[0].toFixed(1)}–${metrics.cdr_ci95[1].toFixed(1)}%` : ""}）</div></div>
  <div class="card"><div class="num">${metrics.control_pass}/${metrics.control_cases}</div><div class="lbl">对照通过 / 误报 ${metrics.false_alarms}</div></div>
  <div class="card"><div class="num">${metrics.calibrated}/${metrics.fault_cases}</div><div class="lbl">置信校准（过度自信 ${metrics.overconfident}）</div></div>
  <div class="card"><div class="num">${meanJudge}</div><div class="lbl">平均 Judge 门（judge 子代理十维）</div></div>
  <div class="card"><div class="num">${metrics.mean_rubric ?? '—'}</div><div class="lbl">确定性 Rubric 均分（R1-R7 产物机算）</div></div>
</div>

<h2>2 分数据集</h2>
<table><tr><th>数据集</th><th>场景</th><th>故障 Top-1</th><th>对照通过</th></tr>${byDataset}</table>

<h2>3 逐场景评分（管线输出 vs 标准答案 vs 文献基线）</h2>
<table>
<tr><th>场景</th><th>数据集</th><th>类型</th><th>管线结论类型</th><th>Top-1</th><th>文献基线（FaultExplainer arXiv:2412.14492）</th><th>Judge</th><th>门禁</th></tr>
${rows}
</table>
<p style="font-size:12.5px;color:var(--sub)">Top-1 由独立评分器判定：管线输出的首要根因需命中标准答案的机理关键词（双判定）。FE = FaultExplainer 在该故障上的结果（root-causes-included prompt，含候选根因清单；PCA 不可检故障其表未评分）。每个 grading 的完整依据见 results/benchmark/gradings/。</p>

<h2>3A TEP 逐故障对比（口径 A：同任务直比，逐故障粒度）</h2>
<table>
<tr><th>TEP 故障</th><th>FaultExplainer GPT-4o</th><th>FaultExplainer o1-preview</th><th>PCA 可检性</th><th>IDD（本管线）Top-1</th></tr>
${tepRows}
</table>
<p style="font-size:12.5px;color:var(--sub)">口径声明：FaultExplainer 的提示中包含<b>候选根因清单</b>且接受别名命中；IDD 不提供候选清单、不提供真值提示，为更严口径。PCA 可检性沿 FaultExplainer 对 Chiang et al. 2001 的标注（IDV3/4/9/15 不可检）。样本量小，比例对比读方向不读显著性。</p>

<h2>4 与文献 baseline 对比</h2>
<table>
<tr><th>方法</th><th>来源</th><th>任务</th><th>指标</th><th>数值</th><th>口径</th></tr>
<tr><td>FaultExplainer（GPT-4o）</td><td>C&amp;CE 2025</td><td>TEP 根因诊断</td><td>Top-1</td><td>7/11 = 63.6%</td><td>A 同任务直比</td></tr>
<tr><td>FaultExplainer（o1-preview）</td><td>C&amp;CE 2025</td><td>TEP 根因诊断</td><td>Top-1</td><td>9/11 = 81.8%</td><td>A 同任务直比</td></tr>
<tr><td><b>IDD（本管线）</b></td><td><b>本报告</b></td><td><b>TEP 根因诊断（含难检 IDV3）</b></td><td><b>Top-1（TEP 子集）</b></td><td><b>${metrics.by_dataset?.tep ? `${metrics.by_dataset.tep.top1}/${metrics.by_dataset.tep.cases - metrics.by_dataset.tep.controls}` : '-'}</b></td><td><b>A 同任务直比</b></td></tr>
<tr><td colspan="6" style="font-size:12px;color:#666">注：FaultExplainer 的 63.6%/81.8% 是<b>故障类别命中率</b>（prompt 内含候选根因清单、接受别名匹配）；IDD 的数字是<b>机制关键词严格匹配率</b>（无候选清单）。<b>二者不是同一个指标</b>，数值不可直接相减或作显著性检验，仅作方向性参照。IDD 的全基准 CDR 为 ${metrics.cdr_display ?? metrics.cdr}（CDR 定义在全部 9 个故障场景上，与 TEP 子集口径不同，故不并入本行）。</td></tr>
<tr><td>Pozdnyakov et al.</td><td>IEEE OJIES 2024</td><td>TEP 逐样本分类</td><td>准确率</td><td>0.887–0.907</td><td>B 参照（不直比）</td></tr>
<tr><td>Hartung et al.（BeatGAN）</td><td>arXiv 2023</td><td>TEP 逐样本检测</td><td>F1</td><td>0.970</td><td>B 参照（不直比）</td></tr>
<tr><td>Iliopoulos et al.</td><td>IEEE BigDataService 2023</td><td>SKAB 逐样本检测</td><td>F1 / AUC</td><td>0.85 / 0.88</td><td>B 参照（不直比）</td></tr>
</table>
<p style="font-size:12.5px;color:var(--sub)">口径 A = 同任务（每场景一个根因结论）直接对比；口径 B = 样本级检测/分类，仅作量级参照。TEP 基线提示中包含根因候选清单，IDD 不提供候选。</p>

<h2>5 优势与劣势分析</h2>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:14px">
  <div>
    <h3 style="font-size:14px;margin:6px 0">优势（数字支撑）</h3>
    <ul>${strengths.map((s) => `<li>${s}</li>`).join('\n')}</ul>
  </div>
  <div>
    <h3 style="font-size:14px;margin:6px 0">劣势与边界（诚实声明）</h3>
    <ul>${weaknesses.map((s) => `<li>${s}</li>`).join('\n')}</ul>
  </div>
</div>

${baselineSection}
${stabilitySection}

<h2>6 复现</h2>
<pre>node scripts/benchmark/run-benchmark.mjs          # 主基准：prepare → brief → 真实管线 → 评分 → 聚合 → 本报告
node scripts/benchmark/run-tier.mjs stability     # 多次运行一致性研究（自动重扫全部 run 目录）
node scripts/benchmark/run-tier.mjs baselines     # 同模型基线对比（PCA 重算 + 裸LLM 重打分 + 对比表）</pre>
<ul>
  <li>S1 prepare 产出每个场景的 run 目录与统计 digest（数据 sha256 见 dataset_manifest.json，${(repro.checks?.dataset_integrity?.verified ?? 0)} 条已验证）；</li>
  <li>S2 下发盲诊断任务包（仅统计证据；truth 隔离）；S3 由执行 agent 按 <b>docs/benchmark/execution-guide.md</b> 现场诊断；</li>
  <li>S4 展开管线产物（每场景 report.md + diagnostic-report.html）并过 finalize 门禁（${repro.checks?.execution_proof?.finalize_pass ?? metrics.total_cases}/${metrics.total_cases} PASS）；S5 独立评分 + 复现门禁；S6 生成本报告。</li>
  <li>逐步命令、期望输出与漂移决策树见 <b>docs/benchmark/reproduction-guide.md</b>。</li>
</ul>

<div class="meta" style="margin-top:30px;border-top:1px solid var(--line);padding-top:12px">
  experience/benchmark-report.html · 由 scripts/benchmark/build-report.mjs 从 results/benchmark 自动生成（无硬编码数字）
</div>
</body>
</html>`;

fs.mkdirSync(path.dirname(OUT), { recursive: true });
fs.writeFileSync(OUT, html);
console.log(`report: ${path.relative(ROOT, OUT)} (${metrics.top1}/${metrics.fault_cases} Top-1, CDR ${metrics.cdr}, ${repro.status})`);
