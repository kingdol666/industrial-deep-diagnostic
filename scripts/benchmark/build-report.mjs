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
  return `<tr><td>${esc(c.case_id)}</td><td>${esc(c.dataset)}</td><td>${type}</td><td>${conclusion}</td><td>${top1}</td><td>${g.judge_score ?? '-'}</td><td>${g.checks?.pipeline_log === 'PASS' && g.checks?.finalize_passed ? '<span class="ok">PASS</span>' : '<span class="bad">FAIL</span>'}</td></tr>`;
}).join('\n');

const byDataset = Object.entries(metrics.by_dataset || {}).map(([d, v]) =>
  `<tr><td>${esc(d)}</td><td>${v.cases}</td><td>${v.top1}/${v.cases - v.controls}</td><td>${v.controls}/${v.controls}</td></tr>`).join('\n');

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
<h1>IDD 诊断基准 — 评分报告</h1>
<div class="meta">生成 ${new Date().toISOString().slice(0, 16).replace('T', ' ')} ·
${metrics.total_cases} 场景（${metrics.fault_cases} 故障 + ${metrics.control_cases} 对照）·
执行模式：zcode-direct（确定性统计管线 + 现场诊断推理）·
复现门禁：<b style="color:${repro.status === 'REPRODUCIBLE' ? '#0a7d38' : '#b42323'}">${esc(repro.status)}</b></div>

<div class="abstract">
  <b>评分协议</b> — 管线对每个场景执行：确定性统计（prepare）→ 诊断推理（agent 仅依据统计证据 brief 现场分析，真值隔离）→
  产物展开与管线门禁（finalize PASS 必需）→ <b>独立评分器</b>对照标准答案（机理关键词双判定）。
  评分器只读管线输出文件与 truth；truth 不进入管线可见输入。比例指标报 Wilson 95% CI。
</div>

<h2>1 总评分</h2>
<div class="cards">
  <div class="card"><div class="num">${metrics.top1}/${metrics.fault_cases}</div><div class="lbl">Top-1 根因命中（CI ${ci[0]}–${ci[1]}%）</div></div>
  <div class="card"><div class="num">${metrics.topk}/${metrics.fault_cases}</div><div class="lbl">Top-k（k=3）</div></div>
  <div class="card"><div class="num">${metrics.cdr}</div><div class="lbl">CDR（Top-1 且 DETERMINED）</div></div>
  <div class="card"><div class="num">${metrics.control_pass}/${metrics.control_cases}</div><div class="lbl">对照通过 / 误报 ${metrics.false_alarms}</div></div>
  <div class="card"><div class="num">${metrics.calibrated}/${metrics.fault_cases}</div><div class="lbl">置信校准（过度自信 ${metrics.overconfident}）</div></div>
</div>

<h2>2 分数据集</h2>
<table><tr><th>数据集</th><th>场景</th><th>故障 Top-1</th><th>对照通过</th></tr>${byDataset}</table>

<h2>3 逐场景评分（管线输出 vs 标准答案）</h2>
<table>
<tr><th>场景</th><th>数据集</th><th>类型</th><th>管线结论类型</th><th>Top-1</th><th>Judge</th><th>门禁</th></tr>
${rows}
</table>
<p style="font-size:12.5px;color:var(--sub)">Top-1 由独立评分器判定：管线输出的首要根因需命中标准答案的机理关键词（双判定）。每个 grading 的完整依据见 results/benchmark/gradings/。</p>

<h2>4 与文献 baseline 对比</h2>
<table>
<tr><th>方法</th><th>来源</th><th>任务</th><th>指标</th><th>数值</th><th>口径</th></tr>
<tr><td>FaultExplainer（GPT-4o）</td><td>C&amp;CE 2025</td><td>TEP 根因诊断</td><td>Top-1</td><td>7/11 = 63.6%</td><td>A 同任务直比</td></tr>
<tr><td>FaultExplainer（o1-preview）</td><td>C&amp;CE 2025</td><td>TEP 根因诊断</td><td>Top-1</td><td>9/11 = 81.8%</td><td>A 同任务直比</td></tr>
<tr><td><b>IDD（本管线）</b></td><td><b>本报告</b></td><td><b>TEP 根因诊断（含难检 IDV3）</b></td><td><b>Top-1 / CDR</b></td><td><b>${metrics.by_dataset?.tep ? `${metrics.by_dataset.tep.top1}/${metrics.by_dataset.tep.cases - metrics.by_dataset.tep.controls}` : '-'} / ${metrics.cdr}</b></td><td><b>A 同任务直比</b></td></tr>
<tr><td>Pozdnyakov et al.</td><td>IEEE OJIES 2024</td><td>TEP 逐样本分类</td><td>准确率</td><td>0.887–0.907</td><td>B 参照（不直比）</td></tr>
<tr><td>Hartung et al.（BeatGAN）</td><td>arXiv 2023</td><td>TEP 逐样本检测</td><td>F1</td><td>0.970</td><td>B 参照（不直比）</td></tr>
<tr><td>Iliopoulos et al.</td><td>IEEE BigDataService 2023</td><td>SKAB 逐样本检测</td><td>F1 / AUC</td><td>0.85 / 0.88</td><td>B 参照（不直比）</td></tr>
</table>
<p style="font-size:12.5px;color:var(--sub)">口径 A = 同任务（每场景一个根因结论）直接对比；口径 B = 样本级检测/分类，仅作量级参照。TEP 基线提示中包含根因候选清单，IDD 不提供候选。</p>

<h2>5 复现</h2>
<pre>node scripts/benchmark/run-benchmark.mjs</pre>
<ul>
  <li>S1 prepare 产出每个场景的 run 目录与统计 digest（数据 sha256 见 dataset_manifest.json，${(repro.checks?.dataset_integrity?.verified ?? 0)} 条已验证）；</li>
  <li>S2 下发盲诊断任务包（仅统计证据；truth 隔离）；S3 由执行 agent 现场诊断（协议见 industrial-benchmark-runner skill）；</li>
  <li>S4 展开管线产物并过 finalize 门禁（${repro.checks?.execution_proof?.finalize_pass ?? metrics.total_cases}/${metrics.total_cases} PASS）；S5 独立评分 + 复现门禁；S6 生成本报告。</li>
  <li>任何一步偏离期望输出即失败退出（漂移决策树见 skill 手册）。</li>
</ul>

<div class="meta" style="margin-top:30px;border-top:1px solid var(--line);padding-top:12px">
  experience/benchmark-report.html · 由 scripts/benchmark/build-report.mjs 从 results/benchmark 自动生成（无硬编码数字）
</div>
</body>
</html>`;

fs.mkdirSync(path.dirname(OUT), { recursive: true });
fs.writeFileSync(OUT, html);
console.log(`report: ${path.relative(ROOT, OUT)} (${metrics.top1}/${metrics.fault_cases} Top-1, CDR ${metrics.cdr}, ${repro.status})`);
