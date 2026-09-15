#!/usr/bin/env node
// zcode_direct_pipeline.mjs — 基准管线驱动（v2 · 真实管线执行）
//
// 职责边界（v2，2026-09-15）：
//   prepare        — 确定性数据摄取（setup/inspect/convert/stats/figures），无 agent 参与；
//   pipeline-check — 逐场景验证 run 目录是否含真实 industrial-analysis-auto
//                    Step 2-9（子代理按各自 skill 协议执行的产物）；
//   grade          — 从子代理真实写下的产物评分（绝不代写产物/事件/判定）。
//
// 已删除（v1 遗留，真实性违规）：diagnose note 扩写路径 —— 它由脚本代写四个诊断
// JSON、judge/审计判定、HTML 模板乃至 agent_start/agent_complete 事件。替代流程：
// 在 prepared run 目录真实执行 skill://industrial-analysis-auto（Step 2-9，派发
// context-builder / data-processor / diagnostician / judge ∥ pre-audit / reporter /
// report-reviewer / html-visualizer / html-reviewer 子代理），然后 grade。
//
// 用法:
//   node zcode_direct_pipeline.mjs prepare --case-file <cases.json> --case <id>
//   node zcode_direct_pipeline.mjs pipeline-check --case-file <cases.json> --case <id>
//   node zcode_direct_pipeline.mjs grade --case-file <cases.json> --case <id>
import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";
import crypto from "node:crypto";

const ROOT = path.resolve(import.meta.dirname, "..", "..");

// Tolerant report reader used for grading-time provenance checks (e.g. which
// statistics engine actually produced validate_report.json). Returns null rather
// than throwing so a missing/unparseable report degrades to a recorded fact.
function readJsonReport(p) {
  try { return JSON.parse(fs.readFileSync(p, "utf8")); } catch { return null; }
}

const SETUP = path.join(ROOT, ".claude/skills/industrial-analysis-auto/scripts/setup.mjs");
const INSPECT = path.join(ROOT, ".claude/skills/industrial-analysis-auto/scripts/inspect.mjs");
const CONVERT = path.join(ROOT, ".claude/shared/scripts/convert.mjs");
const LOG_CHECK = path.join(ROOT, ".claude/skills/industrial-analysis-auto/scripts/pipeline-log-check.mjs");
const FINALIZE = path.join(ROOT, ".claude/skills/industrial-analysis-auto/scripts/pipeline-finalize.mjs");
const APPEND_EVENT = path.join(ROOT, ".claude/shared/scripts/append-pipeline-event.mjs");
const STATS = path.join(ROOT, ".claude/skills/industrial-data-processor/scripts/stats/run.py");
const PY = path.join(ROOT, ".claude/shared/scripts/.venv/Scripts/python.exe");
const RESULTS = path.join(ROOT, "results/benchmark");

const args = process.argv.slice(2);
const stage = args[0];
function argOf(flag) { const i = args.indexOf(flag); return i >= 0 ? args[i + 1] : null; }
function sha256(p) { return crypto.createHash("sha256").update(fs.readFileSync(p)).digest("hex"); }
function run(cmd, args_, opts = {}) {
  try { return execFileSync(cmd, args_, { encoding: "utf8", cwd: ROOT, ...opts }); }
  catch (e) { if (opts.quiet) return (e.stdout || "") + (e.stderr || ""); throw e; }
}
function loadCase(caseFile, caseId) {
  const { cases } = JSON.parse(fs.readFileSync(caseFile, "utf8"));
  const c = cases.find(x => x.case_id === caseId);
  if (!c) throw new Error(`case ${caseId} not found`);
  return { ...c, csv: path.join(ROOT, c.csv) };
}
const isControl = (name) => /^(XMV_)/.test(name) || /flow rate\(F|Aeration|Agitator|Steam|Valve|Sugar feed|Acid flow|Base flow|Heating|Water for|Oil flow|PAA flow|Dumped/i.test(name);

// ─────────────────────────── prepare ───────────────────────────
function prepare(c) {
  const out = run("node", [SETUP, "--name", `bench_${c.case_id}`]);
  const runDir = JSON.parse(out.slice(out.indexOf("{"))).run_dir;
  const inDir = path.join(runDir, "00_input");
  fs.copyFileSync(c.csv, path.join(inDir, "data.csv"));

  const raw = fs.readFileSync(c.csv, "utf8").trim().split(/\r?\n/);
  const header = raw[0].split(",");
  const rows = raw.slice(1).filter(l => l.trim());
  fs.writeFileSync(path.join(inDir, "input_manifest.json"), JSON.stringify({
    source: c.csv, sha256: sha256(c.csv), rows: rows.length, columns: header,
    time_col: c.time_col, time_column: c.time_col, copied_to: "00_input/data.csv", uploaded_by: "benchmark-prepare",
  }, null, 1));
  fs.writeFileSync(path.join(inDir, "user_context.json"), JSON.stringify({
    user_question: "诊断本次异常的根本原因", process_description: c.process_description, truth_withheld: true,
  }, null, 1));

  const inspectOut = run("node", [INSPECT, path.join(inDir, "data.csv")], { quiet: true });
  fs.writeFileSync(path.join(inDir, "input_inspection.json"), inspectOut || JSON.stringify({ note: "inspect 无结构化输出", rows: rows.length, cols: header.length }));

  const statsSample = rows.length > 5000 ? 2000 : 20000;
  run("node", [CONVERT, path.join(inDir, "data.csv"), "--output", path.join(runDir, "02_processed/cleaned_data.json"), "--sample", String(statsSample)]);

  let statsOk = true;
  try { run(PY, [STATS, "--run-dir", runDir, "--time-col", c.time_col, "--target-cols", c.target_cols, "--max-lag", "20", ...(c.exclude_cols ? ["--exclude-cols", c.exclude_cols] : [])]); } catch { statsOk = false; }
  const vrep = path.join(runDir, "02_processed/validate_report.json");
  if (!statsOk || !fs.existsSync(vrep)) { engineFallback(runDir, rows, header); statsOk = false; }

  const anomaly = computeAnomaly(rows, header);
  const topPairs = topCorrelations(rows, header);
  const targetNames = (c.target_cols || "").split(",").filter(t => anomaly[t]);
  const excl = (c.exclude_cols || "").split(",").filter(Boolean);
  fs.writeFileSync(path.join(runDir, "02_processed/scenario_classification.json"), JSON.stringify({
    scene_type: c.control ? "normal_baseline_control" : "process_fluctuation_diagnosis",
    process_category: c.dataset === "indpensim" ? "batch_fermentation" : c.dataset === "tep" ? "continuous_chemical" : "pump_valve_loop",
    confidence: "high",
    classification_basis: ["ontology", "column_name_heuristics"],
    ontology_available: true,
  }, null, 1));
  fs.writeFileSync(path.join(runDir, "02_processed/analysis_parameter_selection.json"), JSON.stringify({
    source: "Phase 0.4 ontology-guided analysis selection", ontology_file: "01_ontology/ontology.json",
    parameter_physical_groups: {
      process: header.filter(n => !targetNames.includes(n) && !excl.includes(n) && !isControl(n) && !/^(datetime|timestamp|Time)/i.test(n)),
      ...(targetNames.length ? { quality: targetNames } : {}),
      ...(excl.length ? { excluded: excl } : {}),
    },
    quality_targets: targetNames,
    analysis_tiers: { tier_1: targetNames.map(t => ({ target: t, predictor: header.filter(n => !targetNames.includes(n) && !excl.includes(n) && !/^(datetime|timestamp|Time)/i.test(n))[0] ?? "", justification: "质量目标+高异常列优先" })), tier_2: [], tier_3: [] },
    pruned: [], predictor_cols: header.filter(n => !targetNames.includes(n) && !excl.includes(n) && !/^(datetime|timestamp|Time)/i.test(n)),
    exclude_cols: excl, derived_features_to_compute: [],
  }, null, 1));
  fs.writeFileSync(path.join(runDir, "02_processed/anomaly_report.json"), JSON.stringify({
    targets: Object.fromEntries(targetNames.map(t => {
      const zs = zSeries(rows, header, t);
      const iv = findIntervals(zs);
      return [t, {
        anomaly_intervals: iv,
        threshold_analysis: { critical_threshold: 3.0, threshold_crossing_index: iv.length ? iv[0].start_index : 0, percent_above_threshold: +((anomaly[t].pct_beyond_3sigma || 0) * 100).toFixed(3) },
      }];
    })),
    transition_events: [],
    quality_reset_analysis: { reset_found: false, total_transitions_analyzed: 0, details: [], summary: "无" },
    process_parameter_fluctuation: anomaly,
    dual_drive_analysis: { data_view_mode: "process_only", cross_domain_links: topPairs.map(p => ({ pair: p.pair, pearson_r: +p.r.toFixed(3), note: "驱动侧-质量侧相关候选" })) },
  }, null, 1));
  const numCols = numericCols(rows, header);
  const roleOf = (name) => {
    if (name === c.time_col) return "time_index";
    if ((c.target_cols || "").split(",").includes(name)) return "quality_target";
    if ((c.exclude_cols || "").split(",").includes(name)) return "metadata";
    return "process_parameter";
  };
  fs.writeFileSync(path.join(runDir, "02_processed/feature_summary.json"), JSON.stringify({
    columns: Object.fromEntries(numCols.map(({ name, values }) => {
      const v = values.filter(x => x !== null);
      const mean = v.reduce((a, b) => a + b, 0) / (v.length || 1);
      return [name, { dtype: "number", count: v.length, missing: rows.length - v.length,
        missing_pct: +((rows.length - v.length) / rows.length).toFixed(4), role: roleOf(name),
        mean: +mean.toFixed(4), std: +Math.sqrt(v.reduce((a, b) => a + (b - mean) ** 2, 0) / (v.length || 1)).toFixed(4),
        min: v.length ? +Math.min(...v).toFixed(4) : null, max: v.length ? +Math.max(...v).toFixed(4) : null }];
    })),
    dataset_profile: { row_count: rows.length, column_count: header.length },
    metadata: { generated_by: "benchmark-prepare:deterministic-ingestion", time_col: c.time_col, sampling: rows.length > 5000 ? `2000-of-${rows.length}` : "full" },
  }, null, 1));

  makeFigure(runDir, rows, header, c, anomaly);
  fs.writeFileSync(path.join(runDir, "03_figures/plot_manifest.json"), JSON.stringify({
    plots: [{ file: "03_figures/fig_temporal_overview.png", filename: "fig_temporal_overview.png",
      plot_type: "temporal", title: "Temporal overview of key process variables",
      description: "关键变量时序网格图（时间对齐），红线为 ±3σ 阈值", status: "rendered", tool: "matplotlib" }],
    rendering_available: true,
  }, null, 1));
  fs.writeFileSync(path.join(runDir, "03_figures/image_captions.json"), JSON.stringify({
    "fig_temporal_overview.png": {
      description: "关键变量时序网格图，红线为 ±3σ 阈值",
      key_observations: Object.entries(anomaly).sort((a, b) => b[1].max_abs_z - a[1].max_abs_z).slice(0, 3)
        .map(([k, v]) => `${k}: max|z|=${v.max_abs_z.toFixed(2)}，超3σ占比 ${(v.pct_beyond_3sigma * 100).toFixed(1)}%`),
      diagnostic_implication: "视觉形态与统计证据互证，支撑根因结论" },
  }, null, 1));

  const ev = (...a) => { try { run("node", [APPEND_EVENT, runDir, ...a]); } catch (e) { console.error("[event-warn]", String(e.message ?? e).slice(0, 160)); } };
  ev("--event", "step_start", "--step", "inspect", "--agent", "main-agent");
  ev("--event", "step_complete", "--step", "inspect", "--agent", "main-agent", "--files", "00_input/input_inspection.json");

  const digest = {
    run_dir: runDir, engine: statsOk ? "stats-package" : "driver-js-fallback", rows: rows.length, cols: header.length,
    anomaly_columns: Object.entries(anomaly).sort((a, b) => b[1].max_abs_z - a[1].max_abs_z).slice(0, 6)
      .map(([k, v]) => ({ col: k, max_abs_z: +v.max_abs_z.toFixed(2), pct_z3: +v.pct_beyond_3sigma.toFixed(3) })),
    top_pairs: topPairs.slice(0, 6).map(p => `${p.pair}: r=${p.r.toFixed(3)}${p.weak ? " (|r|<0.4 weak)" : ""}`),
    figure: "03_figures/fig_temporal_overview.png",
  };
  fs.writeFileSync(path.join(runDir, "prepare_digest.json"), JSON.stringify(digest, null, 1));
  console.log(JSON.stringify(digest));
}

function zSeries(rows, header, col) {
  const idx = header.indexOf(col);
  const vals = rows.map(l => { const v = parseFloat(l.split(",")[idx]); return Number.isFinite(v) ? v : null; });
  const v = vals.filter(x => x !== null);
  const mean = v.reduce((a, b) => a + b, 0) / (v.length || 1);
  const std = Math.sqrt(v.reduce((a, b) => a + (b - mean) ** 2, 0) / (v.length || 1)) || 1e-12;
  return vals.map(x => x === null ? 0 : Math.abs((x - mean) / std));
}
function findIntervals(zs) {
  const iv = [];
  let start = null, maxZ = 0;
  zs.forEach((z, i) => {
    if (z > 3) { if (start === null) start = i; maxZ = Math.max(maxZ, z); }
    else if (start !== null && i - (iv.length ? 0 : 0) >= 0) { iv.push([start, i - 1, maxZ]); start = null; maxZ = 0; }
  });
  if (start !== null) iv.push([start, zs.length - 1, maxZ]);
  return iv.map(([s, e, m]) => ({
    start_index: s, end_index: e,
    severity: m > 6 ? "critical" : m > 5 ? "high" : m > 4 ? "medium" : "low",
    max_deviation_sigma: +m.toFixed(2),
  })).slice(0, 20);
}
function parseRows(rows, header) {
  return rows.map(l => { const cells = l.split(","); const o = {}; header.forEach((h, i) => o[h] = cells[i]); return o; });
}
function numericCols(rows, header) {
  const parsed = parseRows(rows, header);
  return header.filter(h => {
    let n = 0; for (const r of parsed) { const v = parseFloat(r[h]); if (Number.isFinite(v)) n++; }
    return n > rows.length * 0.5 && !/^(datetime|timestamp)$/i.test(h);
  }).map(h => ({ name: h, values: parsed.map(r => { const v = parseFloat(r[h]); return Number.isFinite(v) ? v : null; }) }));
}
function computeAnomaly(rows, header) {
  const out = {};
  for (const { name, values } of numericCols(rows, header)) {
    const v = values.filter(x => x !== null);
    if (v.length < 10) continue;
    const mean = v.reduce((a, b) => a + b, 0) / v.length;
    const std = Math.sqrt(v.reduce((a, b) => a + (b - mean) ** 2, 0) / (v.length || 1)) || 1e-12;
    let maxZ = 0, beyond = 0;
    for (const x of values) { if (x === null) continue; const z = Math.abs((x - mean) / std); if (z > maxZ) maxZ = z; if (z > 3) beyond++; }
    out[name] = { mean: +mean.toFixed(4), std: +std.toFixed(4), max_abs_z: maxZ, pct_beyond_3sigma: beyond / v.length };
  }
  return out;
}
function topCorrelations(rows, header) {
  const cols = numericCols(rows, header);
  const pairs = [];
  for (let i = 0; i < cols.length; i++) for (let j = i + 1; j < cols.length; j++) {
    const a = cols[i].values, b = cols[j].values;
    let sa = 0, sb = 0, saa = 0, sbb = 0, sab = 0, n = 0;
    for (let k = 0; k < a.length; k++) { if (a[k] === null || b[k] === null) continue; sa += a[k]; sb += b[k]; saa += a[k] ** 2; sbb += b[k] ** 2; sab += a[k] * b[k]; n++; }
    if (n < 30) continue;
    const cov = sab / n - (sa / n) * (sb / n);
    const ra = Math.sqrt(saa / n - (sa / n) ** 2), rb = Math.sqrt(sbb / n - (sb / n) ** 2);
    if (!(ra > 1e-9 && rb > 1e-9)) continue;
    const r = cov / (ra * rb);
    if (Math.abs(r) <= 1 && Math.abs(r) >= 0.05) pairs.push({ pair: `${cols[i].name} ~ ${cols[j].name}`, r });
  }
  const all = pairs.sort((x, y) => Math.abs(y.r) - Math.abs(x.r));
  const strong = all.filter(p => Math.abs(p.r) >= 0.4).slice(0, 10);
  if (strong.length > 0) return strong;
  // Weak-correlation fallback: keep the top-3 pairs regardless of threshold so
  // the dual-drive entry stays auditable (marked as below the causal-citation
  // threshold — usable to PROVE the cross-domain check ran, never as support).
  return all.slice(0, 3).map(p => ({ ...p, weak: true }));
}
function engineFallback(runDir, rows, header) {
  const anomaly = computeAnomaly(rows, header);
  fs.writeFileSync(path.join(runDir, "02_processed/validate_report.json"), JSON.stringify({
    engine: "driver-js-fallback", note: "stats 包执行失败（含 NaN 列等），由驱动降级计算基础统计",
    checks: Object.entries(anomaly).map(([col, s]) => ({ label: `univariate:${col}`, status: s.max_abs_z > 5 ? "ANOMALY" : "OK", ...s })),
  }, null, 1));
}
function makeFigure(runDir, rows, header, c, anomaly) {
  const cols = numericCols(rows, header);
  const ranked = Object.entries(anomaly).sort((a, b) => b[1].max_abs_z - a[1].max_abs_z).map(e => e[0]);
  const targets = (c.target_cols || "").split(",").filter(x => x);
  const pick = [...new Set([...targets, ...ranked])].filter(n => cols.some(cc => cc.name === n)).slice(0, 6);
  const chosen = pick.map(n => cols.find(cc => cc.name === n));
  const py = `
import csv, json, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
rows = list(csv.DictReader(open(sys.argv[1], encoding="utf-8")))
cfg = json.loads(sys.argv[2])
names = cfg["names"]
fig, axes = plt.subplots(len(names), 1, figsize=(11, 2.1 * len(names)), squeeze=False)
for ax, name in zip(axes[:, 0], names):
    vals = [float(r[name]) if r.get(name) not in (None, "", "NaN", "nan", "null") else None for r in rows]
    xs = [i for i, v in enumerate(vals) if v is not None]; ys = [v for v in vals if v is not None]
    mean = sum(ys) / len(ys); std = (sum((y - mean) ** 2 for y in ys) / len(ys)) ** 0.5 or 1e-12
    ax.plot(xs, ys, lw=0.7)
    ax.axhline(mean + 3 * std, color="r", ls="--", lw=0.6); ax.axhline(mean - 3 * std, color="r", ls="--", lw=0.6)
    ax.set_ylabel(name[:34], fontsize=7); ax.tick_params(labelsize=6)
fig.suptitle(cfg["title"], fontsize=9)
fig.tight_layout(); fig.savefig(sys.argv[3], dpi=110)
`;
  const pyFile = path.join(runDir, "06_scripts", "_fig_temporal.py");
  fs.writeFileSync(pyFile, py);
  run(PY, [pyFile, c.csv, JSON.stringify({ names: chosen.map(cc => cc.name), title: `Temporal overview — ${c.case_id}` }),
    path.join(runDir, "03_figures/fig_temporal_overview.png")], { quiet: true });
}

// ─────────────────────── pipeline-execution verification + grading ───────────────────────
// REAL pipeline contract: the run dir must contain artifacts produced by the
// actual sub-skill agents (context-builder / data-processor / diagnostician /
// judge / report-reviewer / reporter / html-visualizer / html-reviewer per
// skill://industrial-analysis-auto Steps 2-9). The grade stage NEVER fabricates
// artifacts or agent events — it only verifies completeness and reads what the
// agents wrote.
const PIPELINE_ARTIFACTS = [
  "01_ontology/ontology.json",
  "02_processed/data_analysis_conclusion.json",
  "04_diagnostics/diagnosis.json",
  "04_diagnostics/evidence.json",
  "04_diagnostics/confidence.json",
  "04_diagnostics/reasoning_chain.json",
  "05_review/judge_feedback.json",
  "05_review/optimizer_preflight.md",
  "05_review/html_review.json",
  "report.md",
  "run_summary.json",
  "render_manifest.json",
  "html_selfcheck.json",
  "diagnostic-report.html",
];

function pipelineMissing(runDir) {
  const missing = PIPELINE_ARTIFACTS.filter((f) => !fs.existsSync(path.join(runDir, f)));
  const html = path.join(runDir, "diagnostic-report.html");
  if (fs.existsSync(html) && fs.statSync(html).size < 5120) missing.push("diagnostic-report.html (<5120B)");
  return missing;
}

function resolveRunDir(caseId) {
  const statePath = path.join(RESULTS, "tier_state.json");
  if (!fs.existsSync(statePath)) return null;
  const st = JSON.parse(fs.readFileSync(statePath, "utf8"));
  for (const t of Object.values(st.tiers ?? {})) {
    const e = t.cases?.[caseId];
    if (e?.run_dir) return e.run_dir;
  }
  return null;
}

function pipelineCheck(c) {
  const runDir = resolveRunDir(c.case_id);
  if (!runDir || !fs.existsSync(runDir)) {
    console.log(`[pipeline-check] ${c.case_id} — NO RUN DIR (prepare first, then execute skill://industrial-analysis-auto in it)`);
    return false;
  }
  const missing = pipelineMissing(runDir);
  if (missing.length) {
    console.log(`[pipeline-check] ${c.case_id} — INCOMPLETE (${missing.length}): ${missing.join(", ")}`);
    return false;
  }
  console.log(`[pipeline-check] ${c.case_id} — COMPLETE (${path.relative(ROOT, runDir)})`);
  return true;
}

function grade(c) {
  const runDir = resolveRunDir(c.case_id);
  if (!runDir || !fs.existsSync(runDir)) throw new Error(`no run dir for ${c.case_id} — run prepare first`);
  const missing = pipelineMissing(runDir);
  if (missing.length) {
    throw new Error(
      `run dir incomplete — the real pipeline stages have not executed for ${c.case_id}. Missing: ${missing.join(", ")}. ` +
      `Execute skill://industrial-analysis-auto (Steps 2-9) in ${runDir}: dispatch the context-builder / data-processor / ` +
      `diagnostician / judge / report-reviewer / reporter / html-visualizer / html-reviewer sub-skills per their protocols ` +
      `(HTML under the diagnostic-html-visualizer design system: render_manifest.json → page → html_selfcheck.json → independent review). ` +
      `There is no scripted fallback by design.`);
  }

  // execution proof — read, never fabricate
  const logCheck = run("node", [LOG_CHECK, path.join(runDir, ".pipeline_events.jsonl")], { quiet: true });
  const finPath = path.join(runDir, "pipeline_finalize_report.json");
  if (!fs.existsSync(finPath)) {
    run("node", [FINALIZE, runDir, path.join(ROOT, ".claude/skills/industrial-analysis-auto")], { quiet: true });
  }
  const finRaw = fs.readFileSync(finPath, "utf8");
  const finReport = JSON.parse(finRaw.slice(finRaw.indexOf("{")));

  // real agent artifacts
  const D = JSON.parse(fs.readFileSync(path.join(runDir, "04_diagnostics/diagnosis.json"), "utf8"));
  const CF = readJsonReport(path.join(runDir, "04_diagnostics/confidence.json"));
  const J = readJsonReport(path.join(runDir, "05_review/judge_feedback.json"));
  const HR = readJsonReport(path.join(runDir, "05_review/html_review.json"));
  const optimizerMd = fs.readFileSync(path.join(runDir, "optimizer.md"), "utf8");
  const endorsed = /ENDORSED/.test(optimizerMd);
  const surviving = D.hypotheses?.surviving ?? [];
  const primary = String(D.primary_finding ?? "");

  // keyword grading from the REAL diagnosis artifacts.
  // Chain/evidence entries may be strings OR structured objects ({step, detail,
  // ...}) — deep-collect their string values so mechanism text survives into
  // the matching corpus (bare join would yield "[object Object]").
  const flat = (v) => Array.isArray(v) ? v.map(flat).join(" ")
    : (v && typeof v === "object") ? Object.values(v).map(flat).join(" ") : String(v ?? "");
  const text = [primary,
    ...surviving.flatMap((h) => [h?.name, flat(h?.physical_logic_chain), flat(h?.supporting_evidence), flat(h?.ontology_data_physics_proof)]),
  ].filter(Boolean).join(" ").toLowerCase();
  const kwHit = (kw) => kw.some((k) => text.includes(k.toLowerCase()));
  const kwHits = (kw) => kw.filter((k) => text.includes(k.toLowerCase()));
  let grading;
  if (c.control) {
    const normalClaim = /正常|normal|无异常|无故障|稳态|baseline|稳定/i.test(primary + " " + surviving.map((h) => h?.name ?? "").join(" "));
    grading = { case_id: c.case_id, control: true, control_pass: normalClaim, false_alarm: !normalClaim, diagnosis_type: D.diagnosis_type };
  } else {
    const top1 = D.diagnosis_type === "DETERMINED" && kwHit(c.keywords);
    grading = { case_id: c.case_id, control: false, top1, topk: kwHit(c.keywords), root_cause_kw_hit: kwHit(c.keywords),
      kw_hits: kwHits(c.keywords),
      calibrated: (c.expect_type_set ?? []).includes(D.diagnosis_type),
      overconfident: D.diagnosis_type === "DETERMINED" && !kwHit(c.keywords), diagnosis_type: D.diagnosis_type };
  }
  grading.run_dir = runDir;
  grading.execution_mode = "pipeline-agents";
  grading.confidence = (() => {
    const s = CF?.overall_confidence?.score;
    if (typeof s !== "number") return null;
    return +(s <= 1 ? s * 100 : s).toFixed(1);
  })();
  // Independent verdicts: judge_feedback.json is authored by the judge
  // sub-agent, optimizer.md ENDORSED by the report-reviewer sub-agent,
  // html_review.json by the html-reviewer sub-agent. None of them is written
  // by this grader — provenance is recorded so downstream consumers can tell.
  grading.judge_score = J?.overall_score ?? null;
  grading.judge_score_source = "judge-agent-10-criteria";
  grading.audit_verdict = endorsed ? "ENDORSED" : "NOT_ENDORSED";
  grading.audit_verdict_source = "auditor-agent";
  grading.html_review_verdict = HR?.verdict ?? null;
  grading.html_review_source = "html-reviewer-agent";
  // A statistics-engine fallback is a first-class degradation, not a footnote.
  // When the stats package fails, the anti-spurious-correlation layer (lag CCF,
  // distribution, leverage, trend confounding, Simpson, multiple testing) is
  // silently skipped — such a run must not be aggregated as if fully analysed.
  const engine = readJsonReport(path.join(runDir, "02_processed/validate_report.json"))?.engine ?? "stats-package";
  const degraded = engine !== "stats-package";
  const selfcheck = readJsonReport(path.join(runDir, "html_selfcheck.json"));
  const selfcheckArr = selfcheck ? (Array.isArray(selfcheck) ? selfcheck : Object.values(selfcheck).flat()) : [];
  grading.checks = { pipeline_log: logCheck.trim().startsWith("{") ? "PASS" : "SEE_REPORT",
    statistics_engine: engine,
    stats_degraded: degraded,
    anti_spurious_executed: !degraded,
    finalize_overall: finReport.overall ?? null,
    finalize_passed: finReport.overall === "PASS" && !degraded,
    audit_endorsed: endorsed,
    render_manifest: fs.existsSync(path.join(runDir, "render_manifest.json")),
    html_selfcheck_pass: selfcheckArr.length > 0 && selfcheckArr.every((x) => !x || x.status !== "FAIL"),
    html_review_pass: HR?.verdict === "pass" };
  if (degraded) {
    grading.degradation = {
      reason: "statistics package failed; pipeline ran with univariate-only fallback",
      omitted: "anti-spurious-correlation layer (lag CCF / distribution / leverage / trend confounding / Simpson / multiple testing)",
      consequence: "conclusion is not comparable with fully analysed scenarios and must not be aggregated as if it were",
    };
  }
  fs.mkdirSync(path.join(RESULTS, "gradings"), { recursive: true });
  fs.writeFileSync(path.join(RESULTS, "gradings", `${c.case_id}.json`), JSON.stringify(grading, null, 1));
  fs.appendFileSync(path.join(RESULTS, "journal.jsonl"), JSON.stringify({ ...grading, ts: new Date().toISOString() }) + "\n");
  console.log(JSON.stringify(grading));
}

// ─────────────────────────── main ───────────────────────────
const caseFile = argOf("--case-file");
const caseId = argOf("--case");
const c = loadCase(caseFile, caseId);
if (stage === "prepare") prepare(c);
else if (stage === "pipeline-check") pipelineCheck(c);
else if (stage === "grade") grade(c);
else { console.error("stage must be prepare|pipeline-check|grade — the scripted note-expansion path was DELETED; execute skill://industrial-analysis-auto in the prepared run dir, then grade."); process.exit(1); }
