#!/usr/bin/env node
// quality_gate.mjs — deterministic gate G1-G6 for industrial-doe-analyzer.
// Exit 0 = all pass; exit 1 = at least one FAIL (with named check IDs).
//
// G1 effect_table rows: p/q present OR an allowed reason_code (never silent)
// G2 correlation pairs |r|>=0.3: real anti-spurious verdict + non-empty verdicts
// G3 windows within applicability_domain observed ranges unless extrapolation
// G4 observational mode: every window confirmation_needed === true (hard)
// G5 every plotted figure: ink_ok + exists + min bytes
// G6 all 9 artifacts schema-valid (validate.mjs) + STRICT extra-keys check on
//    recommendations/doe_conclusion (validate.mjs only warns on additionalProperties)

import fs from 'fs';
import path from 'path';
import crypto from 'crypto';
import { execFileSync } from 'child_process';

const args = process.argv.slice(2);
const runDir = args[0];
if (!runDir) {
  console.error('Usage: node quality_gate.mjs <run_dir> --skill-path <skill> --shared-path <shared>');
  process.exit(1);
}
function flag(name, fallback) {
  const i = args.indexOf(name);
  return i >= 0 && args[i + 1] ? args[i + 1] : fallback;
}
const skillPath = flag('--skill-path', path.join('..', 'industrial-doe-analyzer'));
const sharedPath = flag('--shared-path', path.join('..', '..', '..', '.claude', 'shared'));

const results = [];
function check(id, ok, detail) {
  results.push({ id, ok: !!ok, detail });
  console.log(`${ok ? 'PASS' : 'FAIL'} ${id} ${ok ? '' : '- ' + detail}`);
}

function readJson(p) {
  try {
    return JSON.parse(fs.readFileSync(p, 'utf8'));
  } catch (e) {
    return null;
  }
}

const P = {
  context: path.join(runDir, '00_input', 'analysis_context.json'),
  profile: path.join(runDir, '01_profile', 'data_profile.json'),
  effect: path.join(runDir, '02_analysis', 'effect_table.json'),
  model: path.join(runDir, '02_analysis', 'model.json'),
  corr: path.join(runDir, '02_analysis', 'correlation_report.json'),
  stab: path.join(runDir, '02_analysis', 'stability_report.json'),
  manifest: path.join(runDir, '03_figures', 'plot_manifest.json'),
  conclusion: path.join(runDir, 'conclusions', 'doe_conclusion.json'),
  recs: path.join(runDir, 'conclusions', 'recommendations.json'),
  report: path.join(runDir, 'report.html'),
};
const SCHEMAS = {
  [P.context]: 'analysis_context.schema.json',
  [P.profile]: 'data_profile.schema.json',
  [P.effect]: 'effect_table.schema.json',
  [P.model]: 'model.schema.json',
  [P.corr]: 'correlation_report.schema.json',
  [P.stab]: 'stability_report.schema.json',
  [P.manifest]: 'plot_manifest.schema.json',
  [P.conclusion]: 'doe_conclusion.schema.json',
  [P.recs]: 'recommendations.schema.json',
};

const mode = (() => {
  const c = readJson(P.conclusion);
  const p = readJson(P.profile);
  return (c && c.analysis_mode) || (p && p.design && p.design.mode) || 'observational';
})();

const REQUIRED_FILES = mode === 'designed'
  ? ['context', 'profile', 'effect', 'model', 'manifest', 'conclusion', 'recs', 'report']
  : ['context', 'profile', 'corr', 'stab', 'manifest', 'conclusion', 'recs', 'report'];
for (const key of REQUIRED_FILES) {
  check(`FILE_${key}`, fs.existsSync(P[key]), `missing artifact ${P[key]}`);
}

// ---- G1 ----
const effect = readJson(P.effect);
if (effect) {
  let bad = [];
  for (const fam of effect.families || []) {
    for (const t of fam.tests || []) {
      const hasP = t.p_value !== null && t.p_value !== undefined;
      const hasQ = t.q_value_bh !== null && t.q_value_bh !== undefined;
      const reasonOk = ['aliased', 'saturated', 'zero_variance', 'pooled'].includes(t.reason_code);
      if (t.estimable === false) {
        if (!reasonOk) bad.push(`${fam.response}/${t.term}: estimable=false without reason_code`);
      } else if (!hasP && !hasQ && !reasonOk) {
        bad.push(`${fam.response}/${t.term}: missing p/q without reason_code`);
      }
      if (t.n === undefined || t.n === null) bad.push(`${fam.response}/${t.term}: missing n`);
    }
  }
  check('G1_effect_rows_complete', bad.length === 0, bad.slice(0, 5).join('; '));
}

// ---- G2 ----
const corr = readJson(P.corr);
if (corr) {
  let bad = [];
  for (const p of corr.pairs || []) {
    if (Math.abs(p.r || 0) >= 0.3) {
      if (!['PASS', 'CAUTION', 'FAIL'].includes(p.anti_spurious_verdict)) {
        bad.push(`${p.target}~${p.parameter}: verdict=${p.anti_spurious_verdict}`);
      } else if (!p.verdicts || Object.keys(p.verdicts).length === 0) {
        bad.push(`${p.target}~${p.parameter}: empty verdicts`);
      }
    }
  }
  check('G2_correlation_antispurious', bad.length === 0, bad.slice(0, 5).join('; '));
}

// ---- G3 ----
const recs = readJson(P.recs);
if (recs) {
  const ranges = (recs.applicability_domain || {}).factor_observed_ranges || {};
  let bad = [];
  for (const w of recs.operating_windows || []) {
    const obs = ranges[w.factor];
    if (!obs) { bad.push(`${w.id}: no observed range for ${w.factor}`); continue; }
    if (w.extrapolation === true) continue;
    if (w.range[0] < obs.min - 1e-9 || w.range[1] > obs.max + 1e-9) {
      bad.push(`${w.id}: window [${w.range}] outside observed [${obs.min}, ${obs.max}]`);
    }
  }
  check('G3_windows_in_domain', bad.length === 0, bad.slice(0, 5).join('; '));
}

// ---- G4 ----
if (mode === 'observational') {
  const bad = (recs?.operating_windows || [])
    .filter((w) => w.confirmation_needed !== true)
    .map((w) => w.id);
  check('G4_observational_confirmation_required', bad.length === 0,
    bad.length ? `windows without confirmation_needed=true: ${bad.join(',')}` : '');
} else {
  check('G4_observational_confirmation_required', true, 'n/a (designed mode)');
}

// ---- G5 ----
const manifest = readJson(P.manifest);
if (manifest) {
  let bad = [];
  for (const p of manifest.plots || []) {
    const fp = path.join(runDir, '03_figures', p.file);
    if (!fs.existsSync(fp)) { bad.push(`${p.file}: missing`); continue; }
    const size = fs.statSync(fp).size;
    if (size < 2048) bad.push(`${p.file}: only ${size}B`);
    if (p.ink_ok !== true) bad.push(`${p.file}: ink_ok=${p.ink_ok} (${p.ink_detail || ''})`);
  }
  check('G5_figures_ink_and_presence', bad.length === 0, bad.slice(0, 5).join('; '));
}

// ---- G6a: validate.mjs for every artifact ----
const validator = path.join(sharedPath, 'scripts', 'validate.mjs');
let schemaBad = [];
if (fs.existsSync(validator)) {
  for (const [file, schema] of Object.entries(SCHEMAS)) {
    if (!fs.existsSync(file)) continue; // already reported by FILE_*
    const schemaPath = path.join(skillPath, 'schemas', schema);
    try {
      execFileSync('node', [validator, schemaPath, file], { stdio: 'pipe' });
    } catch (e) {
      // P0-4: surface the validator's own output (validate.mjs reports on stdout)
      // instead of only the bare "Command failed" message
      const detail = [e.stdout, e.stderr]
        .map((s) => String(s || '').trim())
        .filter(Boolean)
        .join(' | ');
      schemaBad.push(`${path.basename(file)}: ` +
        (detail || String(e.message || 'validation failed')).slice(0, 240));
    }
  }
  check('G6_schema_validation', schemaBad.length === 0, schemaBad.slice(0, 5).join('; '));
} else {
  check('G6_schema_validation', false, `validator not found at ${validator}`);
}

// ---- G6b: STRICT extra-keys check (validate.mjs only warns) ----
const REC_KEYS = ['contract_version', 'audience', 'analysis_mode', 'operating_windows',
  'current_baseline', 'setpoints', 'interactions', 'conflicts', 'response_specs',
  'confirmations', 'watchlist', 'constraints', 'applicability_domain',
  'invalidation_conditions', 'usage_rules', 'provenance'];
const WIN_KEYS = ['id', 'priority', 'factor', 'factor_unit', 'response', 'range', 'shape',
  'expected_effect', 'confidence', 'fdr_q', 'sample_size', 'evidence_refs',
  'extrapolation', 'confirmation_needed', 'notes'];
const CONC_KEYS = ['generated_at', 'analysis_mode', 'design_type', 'evidence_grade',
  'grade_checklist', 'authored_by', 'key_findings', 'limitations', 'figure_index',
  'recommendations_ref', 'downstream_usage_card'];

function extraKeys(obj, allowed) {
  return Object.keys(obj || {}).filter((k) => !allowed.includes(k));
}
if (recs) {
  let bad = extraKeys(recs, REC_KEYS);
  for (const w of recs.operating_windows || []) {
    bad = bad.concat(extraKeys(w, WIN_KEYS).map((k) => `${w.id}.${k}`));
  }
  check('G6_strict_extra_keys_recommendations', bad.length === 0,
    bad.length ? `undeclared keys: ${bad.slice(0, 8).join(', ')}` : '');
}
const conclusion = readJson(P.conclusion);
if (conclusion) {
  const bad = extraKeys(conclusion, CONC_KEYS);
  check('G6_strict_extra_keys_conclusion', bad.length === 0,
    bad.length ? `undeclared keys: ${bad.join(', ')}` : '');
}

// ---- G7: report.html (single-file interactive report) ----
// G7a exists and >= 20KB            G7b embedded per-artifact sha256 matches disk
// G7c mode-scoped section ids       G7d every .chart block has .chart-reading
// G7e body text has no NaN/Infinity/undefined/null (nulls render as "—")
// G7f size <= 5MB
const reportPath = path.join(runDir, 'report.html');
const REPORT_PATHS = ['00_input/analysis_context.json', '01_profile/data_profile.json',
  '02_analysis/effect_table.json', '02_analysis/model.json',
  '02_analysis/correlation_report.json', '02_analysis/stability_report.json',
  '03_figures/plot_manifest.json', 'conclusions/doe_conclusion.json',
  'conclusions/recommendations.json'];
const MODE_REQUIRED_ARTIFACTS = mode === 'designed'
  ? ['00_input/analysis_context.json', '01_profile/data_profile.json',
     '02_analysis/effect_table.json', '02_analysis/model.json',
     '03_figures/plot_manifest.json', 'conclusions/doe_conclusion.json',
     'conclusions/recommendations.json']
  : ['00_input/analysis_context.json', '01_profile/data_profile.json',
     '02_analysis/correlation_report.json', '02_analysis/stability_report.json',
     '03_figures/plot_manifest.json', 'conclusions/doe_conclusion.json',
     'conclusions/recommendations.json'];

if (fs.existsSync(reportPath)) {
  const html = fs.readFileSync(reportPath, 'utf8');
  const size = Buffer.byteLength(html, 'utf8');
  check('G7a_report_present_sized', size >= 20 * 1024,
    `report.html only ${size}B (need >= 20480B) — run analyze.py report`);
  check('G7f_report_size_cap', size <= 5 * 1024 * 1024,
    `report.html ${size}B exceeds 5MB cap`);

  // G7b: embedded meta sha256 must match disk recompute (post-build tamper tripwire)
  const metaMatch = html.match(
    /<script id="report-meta" type="application\/json">([\s\S]*?)<\/script>/);
  if (!metaMatch) {
    check('G7b_report_meta_sha256', false, 'no <script id="report-meta"> block found');
  } else {
    let meta = null;
    try {
      meta = JSON.parse(metaMatch[1].replace(/<\\\//g, '</'));
    } catch (e) {
      meta = null;
    }
    if (!meta || typeof meta !== 'object' || !meta.artifacts) {
      check('G7b_report_meta_sha256', false, 'report-meta block is not valid JSON');
    } else {
      let bad = [];
      const listed = new Set(Object.keys(meta.artifacts));
      for (const rel of MODE_REQUIRED_ARTIFACTS) {
        if (!listed.has(rel)) { bad.push(`${rel}: not listed in report meta`); continue; }
        const fp = path.join(runDir, rel);
        if (!fs.existsSync(fp)) { bad.push(`${rel}: artifact file missing`); continue; }
        const disk = crypto.createHash('sha256').update(fs.readFileSync(fp)).digest('hex');
        if (disk !== meta.artifacts[rel]) {
          bad.push(`${rel}: sha256 mismatch (artifact changed after report build)`);
        }
      }
      for (const rel of listed) {
        if (!REPORT_PATHS.includes(rel)) bad.push(`${rel}: unexpected path in report meta`);
      }
      check('G7b_report_meta_sha256', bad.length === 0, bad.slice(0, 5).join('; '));
    }
  }

  // G7c: mode-scoped section ids
  const baseSecs = ['sec-hero', 'sec-0', 'sec-1', 'sec-2', 'sec-3', 'sec-8', 'sec-9', 'sec-10', 'sec-appendix'];
  const modeSecs = mode === 'designed'
    ? baseSecs.concat(['sec-4', 'sec-5'])
    : baseSecs.concat(['sec-6b', 'sec-7']);
  const missingSecs = modeSecs.filter((id) => !html.includes(`id="${id}"`));
  check('G7c_report_sections_for_mode', missingSecs.length === 0,
    missingSecs.length ? `missing section ids: ${missingSecs.join(', ')}` : '');

  // G7d: every .chart figure carries a .chart-reading
  const figs = html.match(/<figure class="chart"[\s\S]*?<\/figure>/g) || [];
  const badFigs = figs.filter((f) => !f.includes('class="chart-reading"'))
    .map((f) => (f.match(/id="chart-\d+"/) || ['?'])[0]);
  check('G7d_report_chart_readings', badFigs.length === 0,
    badFigs.length ? `${badFigs.length}/${figs.length} chart figures without .chart-reading: ${badFigs.join(', ')}` : '');
  if (figs.length === 0) {
    check('G7d_report_chart_readings', false, 'no .chart figures found in report.html');
  }

  // G7e: no NaN/Infinity/undefined/null in body text (scripts stripped)
  const stripped = html.replace(/<script[\s\S]*?<\/script>/gi, ' ');
  const banned = ['NaN', 'Infinity', 'undefined', 'null'];
  const hits = [];
  for (const w of banned) {
    const idx = stripped.search(new RegExp(`\\b${w}\\b`));
    if (idx >= 0) hits.push(`${w} at ...${stripped.slice(Math.max(0, idx - 50), idx + 50).replace(/\s+/g, ' ')}...`);
  }
  check('G7e_report_no_leaked_tokens', hits.length === 0, hits.slice(0, 3).join(' | '));
} else {
  check('G7a_report_present_sized', false, `missing artifact ${reportPath}`);
  check('G7b_report_meta_sha256', false, 'report.html absent');
  check('G7c_report_sections_for_mode', false, 'report.html absent');
  check('G7d_report_chart_readings', false, 'report.html absent');
  check('G7e_report_no_leaked_tokens', false, 'report.html absent');
  check('G7f_report_size_cap', false, 'report.html absent');
}

const failed = results.filter((r) => !r.ok);
console.log(`\n[GATE] ${results.length - failed.length}/${results.length} checks passed` +
  (failed.length ? ` — FAIL(${failed.map((f) => f.id).join(', ')})` : ' — ALL PASS'));
process.exit(failed.length ? 1 : 0);
