#!/usr/bin/env node
// aggregate.mjs — 汇总 results/benchmark/ 的 journal + gradings → metrics.json + report.md
// 用法: node aggregate.mjs [--tier-file scripts/benchmark/cases/tier0_smoke.json] [--out results/benchmark]
import fs from "node:fs";
import path from "node:path";

const ROOT = path.resolve(import.meta.dirname, "..", "..");
const args = process.argv.slice(2);
const caseFile = path.join(ROOT, args.includes("--tier-file") ? args[args.indexOf("--tier-file") + 1] : "scripts/benchmark/cases/benchmark_cases.json");
const OUT = path.join(ROOT, args.includes("--out") ? args[args.indexOf("--out") + 1] : "results/benchmark");

const { cases } = JSON.parse(fs.readFileSync(caseFile, "utf8"));
const journal = fs.readFileSync(path.join(OUT, "journal.jsonl"), "utf8").trim().split("\n")
  .filter(Boolean).map(l => JSON.parse(l));
// 每 case 取最新一条
const byCase = new Map();
for (const j of journal) byCase.set(j.case_id, j);

const rows = cases.map(c => ({ case: c, g: byCase.get(c.case_id) })).filter(x => x.g);
const fault = rows.filter(x => !x.case.control);
const control = rows.filter(x => x.case.control);
const pct = (a, b) => (b ? (100 * a / b).toFixed(1) : "n/a");

const metrics = {
  generated_at: new Date().toISOString(),
  tier_file: path.relative(ROOT, caseFile),
  total_cases: cases.length, executed: rows.length,
  fault_cases: fault.length, control_cases: control.length,
  top1: fault.filter(x => x.g.top1).length,
  topk: fault.filter(x => x.g.topk).length,
  cdr: fault.length ? +(fault.filter(x => x.g.top1 && x.g.diagnosis_type === "DETERMINED").length / fault.length).toFixed(4) : null,
  calibrated: fault.filter(x => x.g.calibrated).length,
  overconfident: fault.filter(x => x.g.overconfident).length,
  control_pass: control.filter(x => x.g.control_pass).length,
  false_alarms: control.filter(x => x.g.false_alarm).length,
  by_dataset: {},
  per_case: rows.map(({ case: c, g }) => ({
    case_id: c.case_id, dataset: c.dataset, control: !!c.control, diagnosis_type: g.diagnosis_type,
    top1: g.top1 ?? null, topk: g.topk ?? null, calibrated: g.calibrated ?? null,
    control_pass: g.control_pass ?? null, judge_score: g.judge_score,
    finalize_passed: g.checks?.finalize_passed ?? null, run_dir: g.run_dir,
  })),
};
for (const { case: c, g } of rows) {
  const d = metrics.by_dataset[c.dataset] ??= { cases: 0, top1: 0, topk: 0, controls: 0, control_pass: 0 };
  d.cases++;
  if (c.control) { d.controls++; if (g.control_pass) d.control_pass++; }
  else { if (g.top1) d.top1++; if (g.topk) d.topk++; }
}
fs.writeFileSync(path.join(OUT, "metrics.json"), JSON.stringify(metrics, null, 1));

const CDR_REF = [
  ["FaultExplainer（C&CE 2025）— GPT-4o", "TEP 11 个 PCA 可检故障", "7/11 = 63.6%", "引用（论文表）"],
  ["FaultExplainer（C&CE 2025）— o1-preview", "TEP 11 个 PCA 可检故障", "9/11 = 81.8%", "引用（论文表）"],
  ["Gong et al.（JII 2026）多代理框架", "FailureSensorIQ MCQA（Llama3.1-8B）", "36.5% → 54.6%（框架开关）", "引用（论文表）"],
  ["SKAB leaderboard — Conv-AE / MSET / PCA", "SKAB 检测任务（非根因）", "F1 ≈ 0.76–0.78", "引用（waico/skab README）"],
  ["PCA 经典结论（Chiang et al. 2001）", "TEP 21 故障", "IDV 3/9/15 难检", "本地复现：pca_baseline.py（Tier-1）"],
];
const L = [];
L.push(`# Benchmark 报告 — 多场景根因诊断（典型 8 场景集）`);
L.push(`\n> 生成：${metrics.generated_at} · 执行模式：ZCode 直接作业（无 OMP/Claude Code，agent 按 skill 协议执行 Step 0–9）`);
L.push(`\n## 1. 总体指标\n\n| 指标 | 值 |\n|---|---|\n| 执行 cases | ${metrics.executed}/${metrics.total_cases} |\n| Top-1 命中（故障组） | ${metrics.top1}/${fault.length} = ${pct(metrics.top1, fault.length)}% |`);
L.push(`| Top-k 命中 | ${metrics.topk}/${fault.length} = ${pct(metrics.topk, fault.length)}% |`);
L.push(`| CDR（Top-1 且 DETERMINED） | ${metrics.cdr ?? "n/a"} |`);
L.push(`| 三态校准正确率 | ${metrics.calibrated}/${fault.length} |`);
L.push(`| 过度自信（DETERMINED 且错） | ${metrics.overconfident} |`);
L.push(`| 正常控制组通过 / 误报 | ${metrics.control_pass}/${control.length} · 误报 ${metrics.false_alarms} |`);
L.push(`\n## 2. 分数据集\n\n| 数据集 | cases | Top-1 | Top-k | 控制组通过 |\n|---|---|---|---|---|`);
for (const [ds, d] of Object.entries(metrics.by_dataset)) L.push(`| ${ds} | ${d.cases} | ${d.top1} | ${d.topk} | ${d.control_pass}/${d.controls} |`);
L.push(`\n## 3. 逐 case 明细\n\n| case | 结论类型 | Top-1 | Top-k | 校准 | judge | finalize |\n|---|---|---|---|---|---|---|`);
for (const p of metrics.per_case) L.push(`| ${p.case_id} | ${p.diagnosis_type} | ${p.top1} | ${p.topk} | ${p.calibrated} | ${p.judge_score} | ${p.finalize_passed} |`);
L.push(`\n## 4. 与已发表论文对比\n\n| 方法 | 数据/口径 | 报告数字 | 来源 |\n|---|---|---|---|`);
for (const r of CDR_REF) L.push(`| ${r[0]} | ${r[1]} | ${r[2]} | ${r[3]} |`);
L.push(`\n> 口径声明：FaultExplainer 只在 11 个 PCA 可检故障上评测且根因清单在 prompt 内；本基准为"无真值注入"通用推理口径，数字不可直接横比，仅方向性参照。`);
L.push(`\n## 5. 复现信息\n\n- case 定义：${metrics.tier_file}\n- 逐 run 产物：workspace/diagnostic-runs/*_bench_<case_id>/（含 .pipeline_events.jsonl 完整事件日志）\n- 评分：results/benchmark/gradings/*.json；执行日志：results/benchmark/journal.jsonl`);
fs.writeFileSync(path.join(OUT, "report.md"), L.join("\n") + "\n");
console.log(JSON.stringify({ executed: metrics.executed, top1: metrics.top1, cdr: metrics.cdr, control_pass: metrics.control_pass }));
