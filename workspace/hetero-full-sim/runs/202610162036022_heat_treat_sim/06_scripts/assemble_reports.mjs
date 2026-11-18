#!/usr/bin/env node
/**
 * assemble_reports.mjs — data-processor Phase 2/3 helper (deterministic).
 *
 * 1) Merges the two stats-pipeline runs (_tmp_correlation.json + _tmp_spurious.json)
 *    into schema-shaped 02_processed/validate_report.json
 *    ({validations[], summary{}, metadata{}} per validate_report_schema.json).
 * 2) Builds 02_processed/feature_summary.json (columns/dataset_profile/metadata
 *    per feature_summary_schema.json) from 02_processed/cleaned_data.csv.
 * 3) Prints a digest of the top correlation/anti-spurious findings.
 *
 * Usage: node assemble_reports.mjs <RUN_DIR>
 */
import fs from 'node:fs';
import path from 'node:path';

const RUN = process.argv[2];
if (!RUN) { console.error('usage: node assemble_reports.mjs <RUN_DIR>'); process.exit(1); }
const P = (...a) => path.join(RUN, ...a);
const j = (p) => JSON.parse(fs.readFileSync(p, 'utf8'));

const corr = j(P('02_processed/_tmp_correlation.json')).correlation;
const spur = j(P('02_processed/_tmp_spurious.json')).anti_spurious;
const sel = j(P('02_processed/analysis_parameter_selection.json'));

// ---------- 1) validate_report.json ----------
const targets = corr.data_summary.target_columns;
const predictors = corr.data_summary.predictor_columns;
const validations = [];
const flagsByPair = { trend: new Map(), simpson: new Map(), spearman_div: new Map(), outlier: new Map(), loo: new Map() };

const addFlags = (arr, map, keyFields) => {
  for (const rec of arr || []) {
    const k = `${rec.parameter}||${rec.target}`;
    const k2 = `${rec.param}||${rec.target}`;
    map.set(k, rec); map.set(k2, rec);
  }
};
addFlags(spur.time_trend_confounding, flagsByPair.trend);
addFlags(spur.simpson_paradox, flagsByPair.simpson);
addFlags(spur.spearman_divergence, flagsByPair.spearman_div);
addFlags(spur.outlier_sensitivity, flagsByPair.outlier);
addFlags(spur.leave_one_out_leverage, flagsByPair.loo);

for (const t of targets) {
  const rec = corr.target_analysis[t];
  if (!rec) continue;
  const pear = rec.pearson_correlations || {};
  const spear = rec.spearman_correlations || {};
  const detr = rec.detrended_correlations || {};
  const lags = rec.best_lags || {};
  for (const p of predictors) {
    const pr = pear[p];
    if (!pr || typeof pr.r !== 'number') continue;
    const key = `${p}||${t}`;
    const v = {
      parameter: p,
      target: t,
      pearson_r: pr.r,
      p_value: pr.p ?? 1,
      n: pr.n ?? null,
    };
    if (spear[p] && typeof spear[p].r === 'number') v.spearman_rho = spear[p].r;
    const dt = detr[p];
    if (dt && typeof dt.detrended_r === 'number') {
      v.detrended_r = dt.detrended_r;
      v.detrended_p_value = dt.detrended_p;
      v.detrended_attenuation_pct = dt.attenuation_pct;
      v.trend_confounded = !!dt.trend_confounded;
    }
    const bl = lags[p];
    if (bl && typeof bl.lag === 'number') { v.best_lag_steps = bl.lag; v.best_lag_r = bl.r; v.best_lag_n = bl.n; }
    if (flagsByPair.trend.has(key)) v.trend_confounding = flagsByPair.trend.get(key);
    if (flagsByPair.simpson.has(key)) v.simpson_check = flagsByPair.simpson.get(key);
    if (flagsByPair.spearman_div.has(key)) v.spearman_divergence = flagsByPair.spearman_div.get(key);
    if (flagsByPair.outlier.has(key)) v.outlier_sensitivity = flagsByPair.outlier.get(key);
    if (flagsByPair.loo.has(key)) v.leave_one_out = flagsByPair.loo.get(key);
    const absR = Math.abs(pr.r);
    v.significance = (pr.p ?? 1) < 0.05 ? 'significant' : ((pr.p ?? 1) < 0.10 ? 'marginal' : 'not_significant');
    const atten = (typeof v.detrended_r === 'number' && absR > 1e-9)
      ? Math.abs(v.detrended_r) / absR : null;
    const rhoGap = (typeof v.spearman_rho === 'number') ? absR - Math.abs(v.spearman_rho) : null;
    v.evidence_grade = (absR >= 0.7 && !v.trend_confounded && (pr.p ?? 1) < 0.001) ? 'STRONG'
      : (absR >= 0.5 && !v.trend_confounded) ? 'MODERATE'
      : absR >= 0.3 ? 'WEAK' : 'NONE';
    const warn = [];
    if (v.trend_confounded) warn.push('flagged by time-trend-confounding check');
    if (atten !== null && atten < 0.5) warn.push(`detrending attenuation ${(100 * (1 - atten)).toFixed(0)}% (raw |r|=${absR.toFixed(3)} -> detrended |r|=${Math.abs(v.detrended_r).toFixed(3)})`);
    if (rhoGap !== null && rhoGap >= 0.3 && absR >= 0.5) warn.push(`level-shift dominated: |Pearson r|=${absR.toFixed(3)} vs |Spearman rho|=${Math.abs(v.spearman_rho).toFixed(3)} — correlation concentrated in step/regime level changes, not monotone co-movement`);
    if (warn.length) v.warnings = warn;
    validations.push(v);
  }
}

const sig = validations.filter(v => v.significance === 'significant');
const trendConf = validations.filter(v => v.trend_confounded || v.trend_confounding).length;
const levelShift = validations.filter(v => v.warnings && v.warnings.some(w => w.startsWith('level-shift'))).length;
const simpsonFlags = validations.filter(v => v.simpson_check).length;
const looPassed = validations.filter(v => !v.leave_one_out).length;
const top = [...validations].sort((a, b) => Math.abs(b.pearson_r) - Math.abs(a.pearson_r)).slice(0, 30)
  .map(v => ({ parameter: v.parameter, target: v.target, pearson_r: v.pearson_r, spearman_rho: v.spearman_rho ?? null, detrended_r: v.detrended_r ?? null, best_lag_steps: v.best_lag_steps ?? null, evidence_grade: v.evidence_grade }));

const validate_report = {
  validations,
  summary: {
    total_pairs_analyzed: validations.length,
    significant_pairs: sig.length,
    simpson_safe_pairs: validations.length - simpsonFlags,
    detrended_robust_pairs: validations.length - trendConf,
    trend_confounded_pairs: trendConf,
    level_shift_dominated_pairs: levelShift,
    leave_one_out_passed_pairs: looPassed,
    top_correlations: top,
    spurious_summary: spur.summary,
    overall_validity: spur.overall_validity,
    multiple_testing: corr.multiple_testing,
    change_point_detection: spur.change_point_detection,
    dropped_requested_columns: corr.data_summary.dropped_requested_columns,
    best_global_lags: (() => { const m = {}; for (const t of targets) { const r = corr.target_analysis[t]; if (!r || !r.best_lags) continue; const top3 = Object.entries(r.best_lags).sort((a, b) => Math.abs(b[1]) - Math.abs(a[1])).slice(0, 3); m[t] = Object.fromEntries(top3); } return m; })(),
  },
  metadata: {
    generated_by: 'data-processor (assemble_reports.mjs) merging stats/run.py correlation+spurious',
    pipeline_phase: 'Phase 2.3 statistical analysis & validation',
    data_source: 'cleaned',
    sample_size: corr.data_summary.total_rows,
    anti_spurious_rules_applied: ['v6.4 lagged CCF (max_lag=20)', 'v6.5 production-state steady filtering (1367/1440 rows)', 'v6.6 batch identity (N/A: no batch column)', 'v6.7 trend confounding + Simpson + outlier leverage + Spearman divergence + change point', 'detrended correlation attenuation', 'multiple-testing correction'],
    notes: 'stats input = cleaned_data_steady_only.csv (v6.5 steady-state subset, 1367 rows); correlation section from run --mode correlation, anti-spurious from run --mode spurious; HX columns are backward-merged step-constant blocks (PROF 30min / MAP 2h / IMG 1h) -> effective n is the snapshot count, row-level p-values are pseudo-replicated.',
  },
};
fs.writeFileSync(P('02_processed/validate_report.json'), JSON.stringify(validate_report, null, 1));
console.log(`validate_report.json: ${validations.length} pair records, ${sig.length} significant, ${trendConf} trend-flagged`);

// ---------- 2) feature_summary.json ----------
const csv = fs.readFileSync(P('02_processed/cleaned_data.csv'), 'utf8').split(/\r?\n/).filter(Boolean);
const hdr = csv[0].split(',').map((h, i) => i === 0 ? h.replace(/^\uFEFF/, '') : h);
const rows = csv.slice(1).map(l => l.split(','));
const num = (s) => { const v = Number(s); return (s === '' || s === undefined || Number.isNaN(v)) ? null : v; };
const colVals = {}; for (const c of hdr) colVals[c] = [];
for (const r of rows) for (let i = 0; i < hdr.length; i++) colVals[hdr[i]].push(r[i]);

const quality = new Set(sel.quality_targets);
const roleOf = (c) => {
  if (c === '时间') return 'time_index';
  if (c === 'time_hours') return 'time_index';
  if (quality.has(c)) return 'quality_target';
  if (c.startsWith('HX-TXT-')) return 'metadata';
  return 'process_parameter';
};
const q = (s, p) => { const a = [...s].sort((x, y) => x - y); const h = (a.length - 1) * p, lo = Math.floor(h), hi = Math.ceil(h); return a[lo] + (a[hi] - a[lo]) * (h - lo); };
const columns = {};
for (const c of hdr) {
  const raw = colVals[c];
  const vals = raw.map(num).filter(v => v !== null);
  const missing = raw.length - vals.length;
  const e = { dtype: vals.length === raw.length && /^-?\d+(\.\d+)?$/.test(String(vals[0] ?? '')) ? 'number' : (c === '时间' ? 'string' : 'number'), count: vals.length, missing, missing_pct: +(missing / raw.length * 100).toFixed(2), role: roleOf(c) };
  if (vals.length >= 2) {
    const m = vals.reduce((a, b) => a + b, 0) / vals.length;
    const sd = Math.sqrt(vals.reduce((a, b) => a + (b - m) ** 2, 0) / (vals.length - 1));
    const srt = [...vals].sort((a, b) => a - b);
    const q25 = q(vals, 0.25), q50 = q(vals, 0.5), q75 = q(vals, 0.75), iqr = q75 - q25;
    e.mean = +m.toFixed(6); e.std = +sd.toFixed(6);
    e.min = srt[0]; e.max = srt[srt.length - 1]; e.q25 = q25; e.q50 = q50; e.q75 = q75;
    e.unique_values = new Set(vals).size;
    e.outlier_count = vals.filter(v => v < q25 - 1.5 * iqr || v > q75 + 1.5 * iqr).length;
    e.outlier_pct = +(e.outlier_count / vals.length * 100).toFixed(2);
    if (sd > 1e-12) {
      e.skewness = +(vals.reduce((a, b) => a + ((b - m) / sd) ** 3, 0) / vals.length).toFixed(4);
      e.kurtosis = +(vals.reduce((a, b) => a + ((b - m) / sd) ** 4, 0) / vals.length - 3).toFixed(4);
    }
  } else if (c === '时间') {
    e.unique_values = new Set(raw).size; e.min = undefined; e.max = undefined; delete e.min; delete e.max;
  }
  columns[c] = e;
}
const t0 = new Date(colVals['时间'][0] + 'Z').getTime(), t1 = new Date(colVals['时间'][colVals['时间'].length - 1] + 'Z').getTime();
const feature_summary = {
  columns,
  dataset_profile: {
    row_count: rows.length,
    column_count: hdr.length,
    time_range: { start: 0, end: +((t1 - t0) / 3600000).toFixed(2), duration: +((t1 - t0) / 3600000).toFixed(2) },
    time_column: '时间', time_start: colVals['时间'][0], time_end: colVals['时间'][colVals['时间'].length - 1],
    sampling_interval_minutes: 10,
    hetero_note: 'HX columns are backward-merged step-constant blocks: PROF 30min/480 snapshots, MAP 2h/120, IMG 1h/240, TXT 9 notes. Effective n for HX columns = snapshot count, not row count.',
    product_groups: [], group_sizes: {},
  },
  metadata: {
    generated_by: 'data-processor (assemble_reports.mjs)',
    data_source: 'cleaned',
    timestamp: new Date().toISOString(),
    source_file: '02_processed/cleaned_data.csv (1440 rows full data; stats run on cleaned_data_steady_only.csv 1367 rows)',
  },
};
fs.writeFileSync(P('02_processed/feature_summary.json'), JSON.stringify(feature_summary, null, 1));
console.log(`feature_summary.json: ${Object.keys(columns).length} columns`);

// ---------- 3) digest ----------
console.log('\n=== TOP 20 |r| pairs (steady-state, n=1367) ===');
for (const v of top.slice(0, 20)) {
  console.log(`${v.pearson_r.toFixed(3)} sp=${v.spearman_rho === null || v.spearman_rho === undefined ? 'NA' : v.spearman_rho.toFixed(3)} detr=${v.detrended_r === null || v.detrended_r === undefined ? 'NA' : v.detrended_r.toFixed(3)} lag=${v.best_lag_steps} | ${v.parameter} -> ${v.target} [${v.evidence_grade}]`);
}
console.log('\n=== spurious summary ===');
console.log(JSON.stringify(spur.summary, null, 1));
console.log('overall_validity:', spur.overall_validity);
console.log('\n=== change-point detection (key targets) ===');
for (const t of ['FUR-YIELD', 'FUR-OUT-TEMP', 'HX-PROF-L1BANDTEMPPROFILE30M-MEAN', 'HX-PROF-L1BANDTEMPPROFILE30M-STD', 'HX-PROF-L1BANDTEMPPROFILE30M-EDGE-R-DEV', 'HX-PROF-L1BANDTEMPPROFILE30M-SHIFT-EST']) {
  const cp = spur.change_point_detection?.[t];
  if (!cp) { console.log(t, '-> (not in change_point_detection)'); continue; }
  const txt = JSON.stringify(cp);
  console.log(t, '-> n_changes=' + (cp.n_changes ?? '?') + ' n_segments=' + (cp.n_segments ?? '?') + ' ' + txt.slice(0, 220));
}
console.log('\n=== best lags for key pairs (steps of 10min) ===');
for (const t of targets.slice(0, 20)) {
  const bl = validate_report.summary.best_global_lags[t] || {};
  console.log(t, '->', JSON.stringify(bl));
}
console.log('\nkey pair detail:');
for (const [p, t] of [['FUR-Z3-TEMP', 'FUR-OUT-TEMP'], ['FUR-Z3-TEMP', 'FUR-YIELD'], ['FUR-SPEED', 'FUR-OUT-TEMP'], ['HX-MAP-L1FURNACETHERMALMAP2-ASYM-LR', 'HX-PROF-L1BANDTEMPPROFILE30M-EDGE-L-DEV'], ['HX-MAP-L1FURNACETHERMALMAP2-ASYM-LR', 'HX-PROF-L1BANDTEMPPROFILE30M-EDGE-R-DEV'], ['FUR-PRES', 'HX-IMG-L1SURFACECCDINDEX-DARKFRAC'], ['HX-PROF-L1BANDTEMPPROFILE30M-SHIFT-EST', 'HX-PROF-L1BANDTEMPPROFILE30M-EDGE-L-DEV']]) {
  const v = validations.find(x => x.parameter === p && x.target === t);
  console.log(JSON.stringify(v));
}
