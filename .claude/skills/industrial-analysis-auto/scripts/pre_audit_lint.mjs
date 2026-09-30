#!/usr/bin/env node
// pre_audit_lint.mjs — deterministic pre-audit lint (Step 6 → Step 7 gate).
//
// Runs AFTER the reporter completes and BEFORE the final physical audit is
// dispatched. Catches mechanically-checkable defect classes at birth instead
// of letting them surface in Step 7 (run 202609300452274 spent 45 min in an
// audit-repair loop over findings that are all deterministic):
//   L1 duration_claim   — steps→time narratives must be derivable from
//                         time_lag_analysis.json step_interval_seconds; when
//                         unit_conversion_available=false, any lag-context
//                         duration narrative is a unit error (the "≈38min" bug).
//   L2 plot_ink         — plot PNGs must render real content (delegates to
//                         plot_verification.py, which enforces the ink check).
//   L3 summary_verbatim — run_summary primary_finding / conclusion type /
//                         confidence must match diagnosis.json verbatim.
//   L4 report_numbers   — report.md must state the same conclusion type and
//                         confidence as diagnosis.json (no transcription drift).
//   L5 sections         — report-section-check.mjs must pass.
//   L6 figure_refs      — every 03_figures PNG referenced in report.md exists;
//                         every MANDATORY image in vlm_input_manifest exists.
//
// REPORT-ONLY: this lint never edits artifacts. Failures go back to the
// reporter as a targeted repair list; the final audit keeps full semantic
// authority. Strict mode (default) exits 1 on any FAIL; --report-only exits 0
// and just prints the report (use during calibration).
//
// Usage: node pre_audit_lint.mjs <run_dir> [--report-only]

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { execFileSync } from 'child_process';

// repo root = 4 levels up from this script (.claude/skills/industrial-analysis-auto/scripts/)
const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..', '..', '..');

const runDir = path.resolve(process.argv[2] || '');
const reportOnly = process.argv.includes('--report-only');
if (!fs.existsSync(runDir)) {
  console.error(`run_dir not found: ${runDir}`);
  process.exit(2);
}
const j = p => JSON.parse(fs.readFileSync(p, 'utf-8'));
const read = p => (fs.existsSync(p) ? fs.readFileSync(p, 'utf-8') : '');
const issues = [];
const add = (rule, severity, message, evidence) => issues.push({ rule, severity, message, evidence });

// ── load artifacts ──
const reportText = read(path.join(runDir, 'report.md'));
const diagnosis = j(path.join(runDir, '04_diagnostics', 'diagnosis.json'));
let runSummary = {};
try { runSummary = j(path.join(runDir, 'run_summary.json')); } catch { /* optional */ }
let lag = null;
try { lag = j(path.join(runDir, '02_processed', 'time_lag_analysis.json')); } catch { /* optional */ }

// ── L1: duration-claim guard ──
// Catches narratives like "19 步 ... ≈38min" that cannot be derived from the
// lag artifact. Only fires on lines that mention BOTH a step count and a
// duration, within a lag/CCF context — prose durations elsewhere are not
// this lint's business.
if (lag && reportText) {
  const interval = lag.step_interval_seconds ?? lag.sampling_interval_seconds ?? null;
  const convertible = lag.unit_conversion_available === true && interval > 0;
  const lines = reportText.split(/\r?\n/);
  const stepRe = /(\d+)\s*步/;
  const durRe = /[≈~约＝=]\s*(\d+(?:\.\d+)?)\s*(分钟|min|h|小时|hr|天|day)/i;
  const ctxRe = /(lag|ccf|滞后|领先|时滞|步长)/i;
  const UNIT = { 分钟: 60, min: 60, h: 3600, 小时: 3600, hr: 3600, 天: 86400, day: 86400 };
  lines.forEach((line, i) => {
    if (!ctxRe.test(line)) return;
    const sm = line.match(stepRe);
    const dm = line.match(durRe);
    if (!sm || !dm) return;
    const steps = parseInt(sm[1], 10);
    const unitSec = UNIT[dm[2]] || UNIT[dm[2].toLowerCase()] || 1;
    const claimSec = parseFloat(dm[1]) * unitSec;
    if (!convertible) {
      add('L1_duration_claim', 'FAIL',
        `L${i + 1}: lag 语境下把 ${steps} 步叙述为时长，但 time_lag_analysis.json unit_conversion_available=false（step_interval_seconds=null）——步数不得换算为时间。`,
        line.trim().slice(0, 160));
      return;
    }
    const expectSec = steps * interval;
    const tol = Math.max(expectSec * 0.1, 1);
    if (Math.abs(claimSec - expectSec) > tol) {
      add('L1_duration_claim', 'FAIL',
        `L${i + 1}: "${steps} 步 ≈ ${dm[1]}${dm[2]}" 与工件换算不符——按 step_interval_seconds=${interval}s 应为 ${(expectSec / 3600).toFixed(2)}h（偏差 ${(Math.abs(claimSec - expectSec) / 3600).toFixed(2)}h）。`,
        line.trim().slice(0, 160));
    }
  });
}

// ── L2: plot ink (delegate to the CP-4 gate, same rules) ──
const plotManifestPath = path.join(runDir, '03_figures', 'plot_manifest.json');
if (fs.existsSync(plotManifestPath)) {
  const py = path.join(REPO_ROOT, '.claude', 'shared', 'scripts', '.venv', 'Scripts', 'python.exe');
  const pyAlt = path.join(REPO_ROOT, '.claude', 'shared', 'scripts', '.venv', 'bin', 'python');
  const pyBin = [py, pyAlt].find(p => fs.existsSync(p));
  const script = path.join(REPO_ROOT, '.claude', 'skills', 'industrial-data-processor', 'scripts', 'plot_verification.py');
  if (pyBin && fs.existsSync(script)) {
    try {
      execFileSync(pyBin, [script, runDir], { stdio: 'pipe' });
    } catch (e) {
      add('L2_plot_ink', 'FAIL', 'plot_verification（含墨迹校验）未通过，见其输出。', String(e.stderr || e.message).slice(0, 400));
    }
  }
}

// ── L3: run_summary verbatim ──
if (runSummary.primary_finding && diagnosis.primary_finding && runSummary.primary_finding !== diagnosis.primary_finding) {
  add('L3_summary_verbatim', 'FAIL', 'run_summary.json primary_finding 与 diagnosis.json 不一致——必须 verbatim 复制。', {
    run_summary_head: String(runSummary.primary_finding).slice(0, 100),
    diagnosis_head: String(diagnosis.primary_finding).slice(0, 100),
  });
}
const runType = runSummary.diagnosis_type || runSummary.conclusion_type;
const diagType = diagnosis.conclusion_type || diagnosis.diagnosis_type;
if (runType && diagType && runType !== diagType) {
  add('L3_summary_verbatim', 'FAIL', `conclusion type 漂移: run_summary="${runType}" vs diagnosis="${diagType}"`);
}

// ── L4: report numbers vs diagnosis ──
if (reportText) {
  const dType = diagnosis.conclusion_type || diagnosis.diagnosis_type;
  if (dType && !reportText.includes(dType)) {
    add('L4_report_numbers', 'FAIL', `report.md 未出现 diagnosis 结论类型 "${dType}"（或拼写漂移）。`);
  }
  const conf = diagnosis.confidence?.score ?? diagnosis.confidence_score
    ?? (typeof diagnosis.confidence === 'number' ? diagnosis.confidence : null);
  if (conf != null && !new RegExp(String(conf)).test(reportText)) {
    add('L4_report_numbers', 'FAIL', `report.md 未出现置信度 ${conf}——与 diagnosis.json 不一致或遗漏。`);
  }
}

// ── L5: sections ──
const sectionCheck = path.join(REPO_ROOT, '.claude', 'skills', 'industrial-reporter', 'scripts', 'report-section-check.mjs');
if (fs.existsSync(sectionCheck)) {
  try {
    execFileSync('node', [sectionCheck, runDir], { stdio: 'pipe' });
  } catch (e) {
    add('L5_sections', 'FAIL', 'report-section-check 未通过。', String(e.stderr || e.message).slice(0, 300));
  }
}

// ── L6: figure references ──
const figDir = path.join(runDir, '03_figures');
const figRefs = [...reportText.matchAll(/03_figures\/([\w.\-]+\.png)/g)].map(m => m[1]);
for (const f of new Set(figRefs)) {
  if (!fs.existsSync(path.join(figDir, f))) {
    add('L6_figure_refs', 'FAIL', `report.md 引用的图不存在: 03_figures/${f}`);
  }
}
const vlmManifestPath = path.join(figDir, 'vlm_input_manifest.json');
if (fs.existsSync(vlmManifestPath)) {
  try {
    const vm = j(vlmManifestPath);
    for (const img of (vm.vlm_images || [])) {
      if ((img.priority === 'MANDATORY' || img.priority === 'SUPPLEMENTARY') &&
          !fs.existsSync(path.join(figDir, img.filename))) {
        add('L6_figure_refs', 'FAIL', `vlm_input_manifest 的 ${img.priority} 图缺失: ${img.filename}`);
      }
    }
  } catch { /* optional artifact */ }
}

// ── report ──
const fails = issues.filter(i => i.severity === 'FAIL');
const result = {
  run_dir: runDir,
  checked_at: new Date().toISOString(),
  mode: reportOnly ? 'report_only' : 'strict',
  status: fails.length === 0 ? 'PASS' : 'FAIL',
  summary: { fails: fails.length, total_issues: issues.length },
  issues,
};
const outPath = path.join(runDir, '05_review', 'pre_audit_lint.json');
try {
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  fs.writeFileSync(outPath, JSON.stringify(result, null, 2));
} catch { /* best effort */ }
console.log(JSON.stringify(result, null, 2));
process.exit(fails.length === 0 || reportOnly ? 0 : 1);
