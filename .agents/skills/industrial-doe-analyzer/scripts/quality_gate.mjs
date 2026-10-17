#!/usr/bin/env node
// quality_gate.mjs — deterministic gate G1-G11 for industrial-doe-analyzer.
// Exit 0 = all pass; exit 1 = at least one FAIL (with named check IDs).
//
// G1 effect_table rows: p/q present OR an allowed reason_code (never silent)
// G2 correlation pairs |r|>=0.3: real anti-spurious verdict + non-empty verdicts
// G3 windows within applicability_domain observed ranges unless extrapolation
// G4 observational mode: every window confirmation_needed === true (hard)
// G5 every plotted figure: ink_ok + exists + min bytes
// G6 all 9 artifacts schema-valid (validate.mjs) + STRICT extra-keys check on
//    recommendations/doe_conclusion (validate.mjs only warns on additionalProperties)
// G7 report.html: >=20KB/<=5MB + per-artifact sha256 + mode sections + chart
//    readings + no leaked NaN/Infinity/undefined/null tokens
//
// ---- v1.1 gates (contract docs/plans/contracts/README.md §11; P2-8/P4-4) ----
// G8  association-screen pairs never enter a window's evidence_refs/factor;
//     association_screen.causal_claim === "none"; association_screen_ref.sha256
//     must match the file on disk
// G9  four-interval semantics: PI half-width > mean-CI half-width at the same
//     point, pi95_method discloses the "1 +" term, PI never presented as a
//     pass/yield rate
// G10 joint_setpoints[] actionable integrity (0 hard-constraint violations,
//     unit_status valid, feasible, inside the design/observed region) + every
//     blocked entry disclosed in actionable_summary.blocked with a reason
// G11 factor_response_matrix covers every declared factor x response; every
//     cell carries window_id or a §5.4 no_window_reason
//
// v1.1 fields are OPTIONAL additions (§0 compatibility red line): when the
// artifact a G8-G11 check inspects is ABSENT the check reports "n/a (…)" and
// does NOT fail, so legacy run dirs (no v1.1 artifacts) stay green.

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
  // FAIL always prints its detail; a PASS only prints it when it is an explicit
  // "n/a (…)" skip note, so v1.1 gates that ran on absent artifacts are visible
  // in the log without changing the established PASS/FAIL line shape.
  const suffix = ok ? (/^n\/a/.test(String(detail || '')) ? ` - ${detail}` : '') : ` - ${detail}`;
  console.log(`${ok ? 'PASS' : 'FAIL'} ${id}${suffix}`);
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
// Key lists are kept VERBATIM in sync with the frozen contract
// (docs/plans/contracts/README.md §5/§6 — §0 "质量门白名单" red line).
// v1.1 (§5.1) top-level additions:
//   units, design_region, joint_windows, joint_setpoints, factor_response_matrix,
//   actionable_summary, interval_disclosure, association_screen_ref,
//   next_design_ref, grid_plan
// v1.1 (§5.2) operating_windows[] additions (the legacy 15 keys stay):
//   window_role, actionable, actionable_blockers, in_design_hull,
//   constraints_applied, constraint_violations, predicted_at_center
// NOT whitelisted here because the gate does not key-check them: nested
// objects/lists (expected_effect, predicted_at_center, joint_setpoints[] items,
// setpoints[] items, effect_table rows, model.json blocks) — validate.mjs only
// warns on additionalProperties, so §5.2/§5.3/§6 additions there are additive.
const REC_KEYS = ['contract_version', 'audience', 'analysis_mode', 'operating_windows',
  'current_baseline', 'setpoints', 'interactions', 'conflicts', 'response_specs',
  'confirmations', 'watchlist', 'constraints', 'applicability_domain',
  'invalidation_conditions', 'usage_rules', 'provenance',
  'units', 'design_region', 'joint_windows', 'joint_setpoints',
  'factor_response_matrix', 'actionable_summary', 'interval_disclosure',
  'association_screen_ref', 'next_design_ref', 'grid_plan'];
const WIN_KEYS = ['id', 'priority', 'factor', 'factor_unit', 'response', 'range', 'shape',
  'expected_effect', 'confidence', 'fdr_q', 'sample_size', 'evidence_refs',
  'extrapolation', 'confirmation_needed', 'notes',
  'window_role', 'actionable', 'actionable_blockers', 'in_design_hull',
  'constraints_applied', 'constraint_violations', 'predicted_at_center'];
// doe_conclusion.json: unchanged from v1.0 — contract §5/§6 define no new
// conclusion keys and scripts/conclusion_template.py (the only emitter) copies
// none, so CONC_KEYS must not grow speculatively.
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
  'conclusions/recommendations.json',
  // v1.1: §11 renders these two, so they legitimately appear in report meta
  '01_ontology/ontology_brief.json', 'conclusions/next_design.json'];
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

// ================= v1.1 gates G8-G11 (contract §11) =================
// Shared helpers — every gate below is OPTIONAL-aware: the artifact it inspects
// may simply not exist in a legacy run dir (then it reports n/a and passes).

const P_ASSOC = path.join(runDir, '02_analysis', 'association_screen.json');
const NO_WINDOW_REASONS = new Set([
  'NO_SIGNIFICANT_FACTOR', 'GRID_EMPTY', 'NO_FEASIBLE_POINT', 'DISCONNECTED_WINDOW',
  'DIRECTION_ONLY', 'CONSTRAINTS_INFEASIBLE', 'UNIT_MISSING', 'UNIT_CONFLICT',
  'EXTRAPOLATION_ONLY', 'HULL_UNSUPPORTED', 'NOT_ESTIMABLE', 'TREND_CONFOUNDED_NO_WINDOW',
  'DESIGN_NOT_INFORMATIVE', 'RESPONSE_ALL_MISSING']);   // §5.4 enum (frozen)
const PI_METHOD_KEY = /^(pi95_method|pi_method)$/;
const PI_TOKEN = /(^|_)(pi|pi95|prediction_interval)([_0-9]|$)/i;
const RATE_WORD = /(pass|yield|accept|conform|compliance|qualif|良率|合格)/i;

function sha256File(p) {
  return crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
}
function walkObjects(node, visit, p = '$') {
  if (Array.isArray(node)) {
    node.forEach((v, i) => walkObjects(v, visit, `${p}[${i}]`));
  } else if (node && typeof node === 'object') {
    visit(node, p);
    for (const [k, v] of Object.entries(node)) walkObjects(v, visit, `${p}.${k}`);
  }
}
function halfWidth(v) {
  if (!Array.isArray(v) || v.length !== 2) return null;
  const [lo, hi] = v;
  if (!Number.isFinite(lo) || !Number.isFinite(hi) || hi < lo) return null;
  return (hi - lo) / 2;
}
const windowsOf = (recs && Array.isArray(recs.operating_windows)) ? recs.operating_windows : [];

// ---- G8: association screen must never enter a window ----
// Checks: causal_claim === "none"; association_screen_ref.sha256 matches disk;
// no window cites the screen or an association pair (evidence_refs / factor).
{
  const assoc = readJson(P_ASSOC);
  const ref = (recs && recs.association_screen_ref && typeof recs.association_screen_ref === 'object')
    ? recs.association_screen_ref : null;
  if (!assoc && !ref) {
    check('G8_association_not_in_windows', true,
      'n/a (no association_screen artifact or association_screen_ref)');
  } else {
    const bad = [];
    if (assoc) {
      if (assoc.causal_claim !== 'none') {
        bad.push(`association_screen.causal_claim=${JSON.stringify(assoc.causal_claim)} (must be "none")`);
      }
    }
    if (ref) {
      if (ref.causal_claim !== undefined && ref.causal_claim !== 'none') {
        bad.push(`association_screen_ref.causal_claim=${JSON.stringify(ref.causal_claim)} (must be "none")`);
      }
      const rel = (typeof ref.path === 'string' && ref.path) ? ref.path : '02_analysis/association_screen.json';
      const resolved = path.resolve(runDir, rel);
      const root = path.resolve(runDir);
      if (resolved !== root && !resolved.startsWith(root + path.sep)) {
        bad.push(`association_screen_ref.path escapes run_dir: ${rel}`);
      } else if (!fs.existsSync(resolved)) {
        bad.push(`association_screen_ref.path missing on disk: ${rel}`);
      } else {
        const disk = sha256File(resolved);
        if (!ref.sha256) bad.push('association_screen_ref.sha256 missing');
        else if (String(ref.sha256).toLowerCase() !== disk) {
          bad.push(`association_screen_ref.sha256 mismatch (disk=${disk.slice(0, 12)}…)`);
        }
      }
    }
    const pairs = (assoc && Array.isArray(assoc.pairs)) ? assoc.pairs.filter((x) => x && typeof x === 'object') : [];
    for (const w of windowsOf) {
      const refs = Array.isArray(w.evidence_refs) ? w.evidence_refs.map(String) : [];
      for (const r of refs) {
        if (/association_screen/i.test(r)) {
          bad.push(`${w.id}.evidence_refs cites the association screen: ${r}`);
        }
        for (const pr of pairs) {
          const tok = (pr.factor && pr.response) ? [`${pr.factor}~${pr.response}`, `${pr.response}~${pr.factor}`] : [];
          if (tok.some((t) => r.includes(t))) {
            bad.push(`${w.id}.evidence_refs cites association pair: ${r}`);
          }
        }
      }
      // The screen is a lead generator, not a source of window evidence. A
      // *designed* factor legitimately appears in both places: its window comes
      // from the designed analysis and the screen merely reports its assessed
      // effect. Only non-designed variables (non_factor / held_constant /
      // unmodeled) are forbidden from doubling as a window's factor — that is the
      // laundering this gate exists to stop. A pair carrying no `kind` is treated
      // as non-designed, i.e. conservatively forbidden.
      for (const pr of pairs) {
        if (pr.factor !== w.factor) continue;
        if (pr.kind === 'designed_factor') continue;
        bad.push(`${w.id}.factor=${w.factor} is an association-screen ${pr.kind || 'unclassified'} pair factor`);
      }
    }
    check('G8_association_not_in_windows', bad.length === 0, bad.slice(0, 5).join('; '));
  }
}

// ---- G9: four-interval semantics (DS-07 red line) ----
// For every same-point pair carrying both pi95 and mean_ci95: PI half-width must
// be STRICTLY larger. Any PI method disclosure must contain the "1 +" term.
// No key may present a PI as a pass/yield rate.
{
  let nPi = 0, nMeanCi = 0, nPiMethod = 0;
  const bad = [];
  if (recs) {
    walkObjects(recs, (obj, p) => {
      const hasPi = obj.pi95 !== undefined && obj.pi95 !== null;
      const hasCi = obj.mean_ci95 !== undefined && obj.mean_ci95 !== null;
      if (hasPi) {
        nPi += 1;
        // a scalar pi95 (e.g. 0.95) is exactly the "PI sold as a pass rate" hazard
        if (halfWidth(obj.pi95) === null) {
          bad.push(`${p}.pi95 must be a numeric [lo,hi] interval (never a scalar pass rate)`);
        }
      }
      if (hasCi) {
        nMeanCi += 1;
        if (halfWidth(obj.mean_ci95) === null) {
          bad.push(`${p}.mean_ci95 must be a numeric [lo,hi] interval`);
        }
      }
      if (hasPi && hasCi) {
        const hPi = halfWidth(obj.pi95);
        const hCi = halfWidth(obj.mean_ci95);
        if (hPi !== null && hCi !== null) {
          // With zero residual variance the two intervals coincide exactly
          // (sigma = 0 -> both half-widths are 0), so equality is mathematically
          // correct there. Everywhere else the PI must be strictly wider.
          const degenerate = hPi === 0 && hCi === 0;
          if (!(hPi > hCi) && !degenerate) {
            bad.push(`${p}: PI half-width ${hPi} <= mean-CI half-width ${hCi}`);
          }
        }
      }
      for (const [k, v] of Object.entries(obj)) {
        if (PI_METHOD_KEY.test(k)) {
          // A null/empty disclosure means "no PI was computed for this run"
          // (e.g. an observational run with no windows) — honest, not a violation.
          if (v === null || v === undefined || v === '') continue;
          nPiMethod += 1;
          if (typeof v !== 'string' || !/1\s*\+/.test(v)) {
            bad.push(`${p}.${k} misses the "1 +" PI term`);
          }
        }
        if (PI_TOKEN.test(k) && RATE_WORD.test(k)) {
          bad.push(`${p}.${k} presents a PI as a pass/yield rate`);
        }
      }
    });
    if (nPi > 0 && nPiMethod === 0) {
      bad.push('pi95 present without any pi95_method/pi_method disclosure');
    }
  }
  const active = !!recs && (nPi > 0 || nMeanCi > 0 || nPiMethod > 0);
  check('G9_interval_semantics', active ? bad.length === 0 : true,
    active ? bad.slice(0, 5).join('; ')
      : 'n/a (no pi95/mean_ci95 interval fields in recommendations)');
}

// ---- G10: joint_setpoints actionable integrity + blocked disclosure ----
// "Inside the design region" is verified in RAW units against
// applicability_domain.factor_observed_ranges (the gate cannot invert coded
// bounds without the factor center/half-range); coded hull/leverage checks are
// the emitter's job (P2-3) and disclosed via design_region.
{
  const js = (recs && Array.isArray(recs.joint_setpoints)) ? recs.joint_setpoints : null;
  if (!js || js.length === 0) {
    check('G10_joint_actionable', true, 'n/a (no joint_setpoints in recommendations)');
  } else {
    const bad = [];
    const ranges = (recs.applicability_domain || {}).factor_observed_ranges || {};
    const summary = (recs.actionable_summary && typeof recs.actionable_summary === 'object')
      ? recs.actionable_summary : null;
    const blockedById = new Map();
    if (summary && Array.isArray(summary.blocked)) {
      summary.blocked.forEach((b, i) => {
        if (!b || typeof b !== 'object') { bad.push(`actionable_summary.blocked[${i}] is not an object`); return; }
        const bid = b.setpoint_id || b.window_id;
        if (!bid) { bad.push(`actionable_summary.blocked[${i}] has no setpoint_id/window_id`); return; }
        const reasons = Array.isArray(b.reasons)
          ? b.reasons.filter((r) => r !== null && r !== undefined && String(r).length) : [];
        if (!reasons.length) bad.push(`actionable_summary.blocked[${bid}] carries no reason`);
        blockedById.set(String(bid), b);
      });
    }
    js.forEach((sp, i) => {
      if (!sp || typeof sp !== 'object') { bad.push(`joint_setpoints[${i}] is not an object`); return; }
      const id = String(sp.id || sp.setpoint_id || `joint_setpoints[${i}]`);
      const blockers = Array.isArray(sp.blockers)
        ? sp.blockers.filter((x) => x !== null && x !== undefined && String(x).length) : [];
      if (sp.actionable === true) {
        if (sp.hard_constraint_violations !== 0) {
          bad.push(`${id}: actionable with hard_constraint_violations=` +
            `${JSON.stringify(sp.hard_constraint_violations)} (must be 0)`);
        }
        if (sp.unit_status !== 'valid') {
          bad.push(`${id}: actionable with unit_status=${JSON.stringify(sp.unit_status)} (must be "valid")`);
        }
        if (sp.feasible !== true && sp.constraints_ok !== true) {
          bad.push(`${id}: actionable but neither feasible nor constraints_ok is true`);
        }
        const facs = (sp.factors && typeof sp.factors === 'object') ? sp.factors : null;
        if (!facs) {
          bad.push(`${id}: actionable without factors{}`);
        } else {
          for (const [f, v] of Object.entries(facs)) {
            if (typeof v !== 'number') continue;
            const obs = ranges[f];
            if (obs && (v < obs.min - 1e-9 || v > obs.max + 1e-9)) {
              bad.push(`${id}: ${f}=${v} outside design/observed range [${obs.min}, ${obs.max}]`);
            }
          }
        }
        if (sp.constraint_slack && typeof sp.constraint_slack === 'object') {
          for (const [f, s] of Object.entries(sp.constraint_slack)) {
            if (typeof s === 'number' && s < 0) {
              bad.push(`${id}: negative constraint_slack for ${f} (${s})`);
            }
          }
        }
      }
      const isBlocked = sp.actionable !== true || blockers.length > 0;
      if (isBlocked && !blockedById.has(id)) {
        bad.push(`${id}: blocked/not-actionable but missing from actionable_summary.blocked`);
      }
    });
    if (!summary && js.some((sp) => !sp || sp.actionable !== true)) {
      bad.push('actionable_summary missing while joint_setpoints has non-actionable entries');
    }
    check('G10_joint_actionable', bad.length === 0, bad.slice(0, 5).join('; '));
  }
}

// ---- G11: factor_response_matrix coverage (0 silent cells) ----
// Universe = declared factors x responses from analysis_context.json (fallback:
// observed ranges x response_specs keys). Every cell needs window_id OR a §5.4
// no_window_reason.
{
  const matrix = (recs && Array.isArray(recs.factor_response_matrix)) ? recs.factor_response_matrix : null;
  if (!matrix) {
    check('G11_factor_response_coverage', true, 'n/a (no factor_response_matrix in recommendations)');
  } else {
    const bad = [];
    const ctx = readJson(P.context);
    let factors = ((ctx || {}).factors || []).map((f) => f && f.col).filter(Boolean);
    let responses = ((ctx || {}).responses || []).map((r) => r && r.col).filter(Boolean);
    if (!factors.length) factors = Object.keys((recs.applicability_domain || {}).factor_observed_ranges || {});
    if (!responses.length) responses = Object.keys(recs.response_specs || {});
    const seen = new Set();
    matrix.forEach((cell, i) => {
      const p = `factor_response_matrix[${i}]`;
      if (!cell || typeof cell !== 'object') { bad.push(`${p} is not an object`); return; }
      if (!cell.factor || !cell.response) { bad.push(`${p}: missing factor/response`); return; }
      seen.add(`${cell.factor}\u0000${cell.response}`);
      const hasWin = cell.window_id !== undefined && cell.window_id !== null && cell.window_id !== '';
      const reason = cell.no_window_reason;
      const hasReason = reason !== undefined && reason !== null && reason !== '';
      if (!hasWin && !hasReason) {
        bad.push(`${p} (${cell.factor}×${cell.response}): neither window_id nor no_window_reason`);
      }
      if (hasReason && !NO_WINDOW_REASONS.has(String(reason))) {
        bad.push(`${p} (${cell.factor}×${cell.response}): no_window_reason="${reason}" not in the §5.4 enum`);
      }
    });
    const missing = [];
    for (const f of factors) {
      for (const r of responses) if (!seen.has(`${f}\u0000${r}`)) missing.push(`${f}×${r}`);
    }
    if (missing.length) {
      bad.push(`missing cells: ${missing.slice(0, 6).join(', ')}${missing.length > 6 ? ` (+${missing.length - 6})` : ''}`);
    }
    check('G11_factor_response_coverage', bad.length === 0, bad.length ? bad.slice(0, 5).join('; ')
      : (factors.length && responses.length ? ''
        : `matrix present; declared factor×response universe unknown (cells=${matrix.length})`));
  }
}

const failed = results.filter((r) => !r.ok);
console.log(`\n[GATE] ${results.length - failed.length}/${results.length} checks passed` +
  (failed.length ? ` — FAIL(${failed.map((f) => f.id).join(', ')})` : ' — ALL PASS'));
process.exit(failed.length ? 1 : 0);
