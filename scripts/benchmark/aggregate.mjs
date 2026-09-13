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
// gradings/*.json 是评分的唯一权威来源（含 rubric/kw_hits/judge 溯源字段）；
// journal.jsonl 仅作运行历史保留。
const byCase = new Map();
for (const f of fs.readdirSync(path.join(OUT, "gradings")).filter(f => f.endsWith(".json"))) {
  const g = JSON.parse(fs.readFileSync(path.join(OUT, "gradings", f), "utf8"));
  byCase.set(g.case_id, g);
}

const rows = cases.map(c => ({ case: c, g: byCase.get(c.case_id) })).filter(x => x.g);
const fault = rows.filter(x => !x.case.control);
const control = rows.filter(x => x.case.control);
const pct = (a, b) => (b ? (100 * a / b).toFixed(1) : "n/a");

// Wilson score interval — the honest interval for a proportion near 0 or 1,
// where the normal approximation would produce a zero-width interval.
function wilson(k, n, z = 1.96) {
  if (!n) return null;
  const p = k / n, d = 1 + (z * z) / n;
  const c = (p + (z * z) / (2 * n)) / d;
  const h = (z * Math.sqrt((p * (1 - p)) / n + (z * z) / (4 * n * n))) / d;
  return [Math.max(0, 100 * (c - h)), Math.min(100, 100 * (c + h))];
}

// CDR is defined as a *rate* (Top-1 AND DETERMINED, over all fault scenarios).
// It is stored together with its numerator so that no reader can mistake the
// ratio 1.0 for the count "1 case" — which is exactly how it was misreported.
const cdrCount = fault.filter(x => x.g.top1 && x.g.diagnosis_type === "DETERMINED").length;
const cdrValue = fault.length ? +(cdrCount / fault.length).toFixed(4) : null;

// Independent structural audit, if it has been produced. This is the honest
// replacement for the note-copied judge score; it is optional so that the
// aggregator still works before the audit has been run.
const structuralPath = path.join(ROOT, "results/benchmark/structural_audit.json");
const structuralByCase = new Map();
try {
  const sa = JSON.parse(fs.readFileSync(structuralPath, "utf8"));
  for (const r of sa.results ?? []) structuralByCase.set(r.case_id, r);
} catch { /* audit not generated yet */ }

const metrics = {
  generated_at: new Date().toISOString(),
  tier_file: path.relative(ROOT, caseFile),
  total_cases: cases.length, executed: rows.length,
  fault_cases: fault.length, control_cases: control.length,
  top1: fault.filter(x => x.g.top1).length,
  topk: fault.filter(x => x.g.topk).length,
  cdr: cdrValue,
  cdr_count: cdrCount,
  cdr_display: cdrValue === null ? "n/a" : `${cdrValue.toFixed(2)} (${cdrCount}/${fault.length})`,
  cdr_ci95: wilson(cdrCount, fault.length),
  top1_ci95: wilson(fault.filter(x => x.g.top1).length, fault.length),
  calibrated: fault.filter(x => x.g.calibrated).length,
  overconfident: fault.filter(x => x.g.overconfident).length,
  control_pass: control.filter(x => x.g.control_pass).length,
  false_alarms: control.filter(x => x.g.false_alarm).length,
  mean_rubric: rows.length ? +(rows.reduce((a, x) => a + (x.g.rubric?.score ?? 0), 0) / rows.length).toFixed(1) : null,
  by_dataset: {},
  per_case: rows.map(({ case: c, g }) => ({
    case_id: c.case_id, dataset: c.dataset, control: !!c.control, diagnosis_type: g.diagnosis_type,
    top1: g.top1 ?? null, topk: g.topk ?? null, calibrated: g.calibrated ?? null,
    control_pass: g.control_pass ?? null, judge_score: g.judge_score,
    // The judge score is rendered from the agent-authored note, not computed by
    // an independent grader. It is labelled so downstream consumers cannot
    // mistake it for an independently verified quality-gate result.
    judge_score_source: g.judge_score_source ?? "note-self-declared",
    // Independent structural audit (scripts/benchmark/audit-structural.mjs).
    // IMPORTANT: in the released artifact the "10-criterion judge score" is not a
    // judgement at all — zcode_direct_pipeline.mjs:503 set all ten criteria to
    // Math.round(note.judge.score/10), so every criterion in every run scored 9
    // and the reported mean was a restatement of the note's own opinion. This
    // field is the independently computed substitute.
    structural_score: structuralByCase.get(c.case_id)?.structural_score ?? null,
    structural_unmet_checks: structuralByCase.get(c.case_id)?.unmet_checks?.length ?? null,
    finalize_passed: g.checks?.finalize_passed ?? null, run_dir: g.run_dir,
  })),
};
for (const { case: c, g } of rows) {
  const d = metrics.by_dataset[c.dataset] ??= { cases: 0, top1: 0, topk: 0, controls: 0, control_pass: 0 };
  d.cases++;
  if (c.control) { d.controls++; if (g.control_pass) d.control_pass++; }
  else { if (g.top1) d.top1++; if (g.topk) d.topk++; }
}

if (structuralByCase.size) {
  const vals = [...structuralByCase.values()].map(r => r.structural_score);
  metrics.structural_audit = {
    source: "results/benchmark/structural_audit.json",
    script: "scripts/benchmark/audit-structural.mjs",
    covered: vals.length,
    mean_score: +(vals.reduce((a, b) => a + b, 0) / vals.length).toFixed(1),
    distinct_scores: [...new Set(vals)].sort((a, b) => a - b),
    note: "独立于 note 的结构化评分（10 维、加权同项目 judge 模板）。用于替代无判别力的自报 judge 分数。",
  };
}

// Execution-engine provenance: a scenario that silently degraded to the JS
// fallback skipped the entire anti-spurious-correlation layer, so it must be
// visible in the aggregate rather than discoverable only by opening a run dir.
const engineByCase = new Map();
for (const { case: c, g } of rows) {
  // run_dir is recorded as an absolute path; tolerate a repo-relative one too.
  const rd = g.run_dir ?? "";
  const vr = path.join(path.isAbsolute(rd) ? rd : path.join(ROOT, rd), "02_processed/validate_report.json");
  try {
    const v = JSON.parse(fs.readFileSync(vr, "utf8"));
    engineByCase.set(c.case_id, v.engine ?? (v.correlation ? "stats-package" : "unknown"));
  } catch { engineByCase.set(c.case_id, "unknown"); }
}
metrics.execution_integrity = {
  by_engine: {},
  degraded_cases: [...engineByCase.entries()].filter(([, e]) => e !== "stats-package").map(([k]) => k),
  note: "degraded_cases 以 driver-js-fallback 运行：统计包失败，未执行反假相关校验（lag CCF / 分布 / 杠杆 / 趋势混杂 / Simpson / 多重检验），其判别证据链不完整。",
};
for (const e of engineByCase.values()) metrics.execution_integrity.by_engine[e] = (metrics.execution_integrity.by_engine[e] ?? 0) + 1;

fs.writeFileSync(path.join(OUT, "metrics.json"), JSON.stringify(metrics, null, 1));

const CDR_REF = [
  ["FaultExplainer（C&CE 2025）— GPT-4o", "TEP 11 个 PCA 可检故障", "7/11 = 63.6%", "引用（论文表）"],
  ["FaultExplainer（C&CE 2025）— o1-preview", "TEP 11 个 PCA 可检故障", "9/11 = 81.8%", "引用（论文表）"],
  ["Gong et al.（JII 2026）多代理框架", "FailureSensorIQ MCQA（Llama3.1-8B）", "36.5% → 54.6%（框架开关）", "引用（论文表）"],
  ["SKAB leaderboard — Conv-AE / MSET / PCA", "SKAB 检测任务（非根因）", "F1 ≈ 0.76–0.78", "引用（waico/skab README）"],
  ["PCA 经典结论（Chiang et al. 2001）", "TEP 21 故障", "IDV 3/4/9/15 难检", "引用（文献结论）；本仓库对照见 results/benchmark/pca_local.json"],
];
const L = [];
L.push(`# Benchmark 报告 — 12 场景集（TEP 逐故障文献可比）`);
L.push(`\n> 生成：${metrics.generated_at}`);
L.push(`>\n> ⚠️ **被测对象界定（必读）**：本基准测的是**推理层** —— 由 1 次 LLM 推理消费预计算的统计 brief`);
L.push(`> 并产出一份符合诊断协议的 note，随后由模板展开为完整产物集。它**不包含**`);
L.push(`> context-builder / data-processor / diagnostician / judge / 物理审计 等 14 个 agent 的编排执行。`);
L.push(`> 因此本报告的数字**不是**"14-agent 管线整体"的性能，引用时必须保留此界定。`);
L.push(`>\n> ⚠️ **judge 分数不是判断**：展开步骤把所有 10 个维度都设为 \`Math.round(note.judge.score/10)\``);
L.push(`> （\`zcode_direct_pipeline.mjs:503\`），实测 12 次运行中每个维度都恰好是 9，`);
L.push(`> 即"10 维质量门"不携带任何判别信息。请改看第 5 节的**独立结构审计**分数。`);
L.push(`\n## 1. 总体指标\n\n| 指标 | 值 |\n|---|---|\n| 执行 cases | ${metrics.executed}/${metrics.total_cases} |\n| Top-1 命中（故障组） | ${metrics.top1}/${fault.length} = ${pct(metrics.top1, fault.length)}%${metrics.top1_ci95 ? `（Wilson 95% CI ${metrics.top1_ci95[0].toFixed(1)}–${metrics.top1_ci95[1].toFixed(1)}%）` : ""} |`);
L.push(`| Top-k 命中 | ${metrics.topk}/${fault.length} = ${pct(metrics.topk, fault.length)}% |`);
L.push(`| CDR（Top-1 且 DETERMINED，**比率**） | ${metrics.cdr_display}${metrics.cdr_ci95 ? `，Wilson 95% CI ${metrics.cdr_ci95[0].toFixed(1)}–${metrics.cdr_ci95[1].toFixed(1)}%` : ""} |`);
L.push(`| 三态校准正确率 | ${metrics.calibrated}/${fault.length} |`);
L.push(`| 过度自信（DETERMINED 且错） | ${metrics.overconfident} |`);
L.push(`| 正常控制组通过 / 误报 | ${metrics.control_pass}/${control.length} · 误报 ${metrics.false_alarms} |`);
L.push(`| judge 分数 | **agent 自报（note.judge.score），非独立评分；10 维全为同一数字，无判别力** —— mean ${(fault.concat(control).reduce((a, x) => a + (x.g.judge_score ?? 0), 0) / rows.length).toFixed(1)} |`);
L.push(`| 独立结构审计均分 | ${metrics.structural_audit?.mean_score ?? "n/a"}${metrics.structural_audit ? `（覆盖 ${metrics.structural_audit.covered}/${rows.length}；越低表示产物越不完整）` : ""} |`);
L.push(`\n## 2. 分数据集\n\n| 数据集 | cases | Top-1 | Top-k | 控制组通过 |\n|---|---|---|---|---|`);
for (const [ds, d] of Object.entries(metrics.by_dataset)) L.push(`| ${ds} | ${d.cases} | ${d.top1} | ${d.topk} | ${d.control_pass}/${d.controls} |`);
L.push(`\n## 3. 逐 case 明细\n\n| case | 结论类型 | Top-1 | Top-k | 校准 | judge（自报，无判别力） | **独立结构审计** | 未达项 | finalize |\n|---|---|---|---|---|---|---|---|---|`);
for (const p of metrics.per_case) L.push(`| ${p.case_id} | ${p.diagnosis_type} | ${p.top1} | ${p.topk} | ${p.calibrated} | ${p.judge_score} | **${p.structural_score ?? "n/a"}** | ${p.structural_unmet_checks ?? "n/a"} | ${p.finalize_passed} |`);
L.push(`\n## 4. 与已发表论文对比\n\n| 方法 | 数据/口径 | 报告数字 | 来源 |\n|---|---|---|---|`);
for (const r of CDR_REF) L.push(`| ${r[0]} | ${r[1]} | ${r[2]} | ${r[3]} |`);
L.push(`\n> 口径声明：FaultExplainer 只在 11 个 PCA 可检故障上评测且根因清单在 prompt 内；本基准为"无真值注入"通用推理口径，数字不可直接横比，仅方向性参照。`);

const ei = metrics.execution_integrity;
L.push(`\n## 5. 执行完整性（独立结构审计 + 引擎来源）\n`);
L.push(`统计引擎分布：${Object.entries(ei.by_engine).map(([k, v]) => `\`${k}\` ×${v}`).join(" · ")}`);
if (ei.degraded_cases.length) {
  L.push(`\n⚠️ **降级运行场景**：${ei.degraded_cases.map(c => `\`${c}\``).join("、")}`);
  L.push(`\n${ei.note}`);
}
L.push(`\n独立结构审计（\`audit-structural.mjs\`，10 维加权，越低表示产物越不完整）替代了无判别力的自报 judge 分数：\n`);
L.push(`| case | 结构审计 | 自报 judge | 未达项数 |\n|---|---|---|---|`);
for (const p of metrics.per_case) L.push(`| ${p.case_id} | **${p.structural_score ?? "n/a"}** | ${p.judge_score} | ${p.structural_unmet_checks ?? "n/a"} |`);
L.push(`>\n> 指标口径警告：FaultExplainer 报的是**故障类别命中（接受别名、prompt 内含候选清单）**，本基准报的是**机制关键词严格匹配（无候选）**。二者**不是同一个指标**，其数值不可相减、不可作差、不可作显著性检验。`);
L.push(`>\n> 本地 PCA 对照：见 docs/benchmark/design.md 与 results/benchmark/pca_local.json（若缺则该行"本地复现"字样不成立）。`);
L.push(`\n## 5. 复现信息\n\n- case 定义：${metrics.tier_file}\n- 逐 run 产物：workspace/diagnostic-runs/*_bench_<case_id>/（含 .pipeline_events.jsonl 完整事件日志）\n- 评分：results/benchmark/gradings/*.json；执行日志：results/benchmark/journal.jsonl`);
fs.writeFileSync(path.join(OUT, "report.md"), L.join("\n") + "\n");
console.log(JSON.stringify({ executed: metrics.executed, top1: metrics.top1, cdr: metrics.cdr, control_pass: metrics.control_pass }));
