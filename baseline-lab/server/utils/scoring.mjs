// Scoring for lab results — semantics copied from the repository so that lab
// numbers are directly comparable with results/benchmark/gradings/*.json and
// with scripts/benchmark/baseline_llm.mjs::scoreAnswer.
//
//   strict  = the rank-1 verdict hits a mechanism keyword, OR (TEP) names the
//             true IDV number. This is the IDD rubric's judgement, applied to
//             whichever answer an algorithm produced.
//   fe_style= (TEP) the true IDV or an alias-class IDV appears anywhere in the
//             top-3 — FaultExplainer's own lenient criterion.
//   control = a control case must return "normal"; a fault verdict is a false
//             alarm, and a fault conclusion is not scored as a hit.
//
// Alias classes and the IDV truth parser are read from the repository's
// scripts/benchmark/cases/tep_cause_table.json, so both graders cannot drift.

import { loadTruth, loadCauseTable, loadCasesRaw, exists, IDD_METRICS, readJson } from './paths.mjs';

const IDV_NUM = /IDV[(\s]*(\d+)/gi;

export function idvNumbers(text) {
  const out = [];
  for (const m of String(text).matchAll(IDV_NUM)) out.push(Number(m[1]));
  return out;
}

export function truthIdv(truth) {
  const m = String(truth || '').match(/IDV[（(]?(\d+)/);
  return m ? Number(m[1]) : null;
}

function aliasOf(idv, causes) {
  for (const cls of causes.alias_classes || []) {
    if (cls.includes(`IDV${idv}`)) return cls;
  }
  return [];
}

/**
 * Score one algorithm output against one case's truth.
 * @param {object} truth  from loadTruth(caseId)
 * @param {object} output algorithm run() result
 */
export function scoreResult(truth, output) {
  const causes = loadCauseTable();
  const top3 = Array.isArray(output?.top3) ? output.top3.map(String).filter(Boolean) : [];
  const top1 = top3[0] || '';
  const lower1 = top1.toLowerCase();
  const lower3 = top3.join(' \n ').toLowerCase();

  // ---- UNSCORED: user-uploaded data has no ground truth ------------------
  // Reporting `strict_top1_hit: false` here would be a lie of omission — it
  // reads as "the algorithm got it wrong" when in fact nothing is known about
  // correctness. Detection statistics and hypotheses are still returned.
  if (truth.has_ground_truth === false) {
    return {
      case_id: truth.case_id,
      control: false,
      scored: false,
      unscored_reason: 'no_ground_truth',
      note: truth.note || 'No ground truth exists for this dataset; this run is reported unscored.',
      top3,
      kw_hits: [],
      strict_top1_hit: null,
      top1_kw_hit: null,
      verdict: output?.verdict ?? (top3.length ? 'fault' : 'normal'),
      control_pass: null,
      false_alarm: null,
      fe_style_top3_hit: null,
      true_idv: null,
      exact_idv_top1_hit: null,
      exact_idv_top3_hit: null,
      strict_but_not_exact: null,
      idv_rank: null,
      diagnosis_type: output?.diagnosis_type || (top3.length ? 'DETERMINED' : 'NEEDS_DATA'),
      calibrated: null,
      overconfident: null,
    };
  }

  const keywords = truth.keywords || [];
  const kwHits = keywords.filter((k) => lower3.includes(String(k).toLowerCase()));
  const top1Kw = keywords.some((k) => lower1.includes(String(k).toLowerCase()));

  const tIdv = truthIdv(truth.truth);
  const top1Idvs = idvNumbers(top1);
  let strict = top1Kw;
  if (tIdv !== null && top1Idvs.length && top1Idvs[0] === tIdv) strict = true;

  const scored = {
    case_id: truth.case_id,
    control: truth.control,
    top3,
    kw_hits: kwHits,
    strict_top1_hit: strict,
    top1_kw_hit: top1Kw,
  };

  // ---- control cases: pass = said normal, false_alarm = claimed a fault
  if (truth.control) {
    const verdict = output?.verdict || (top3.length ? 'fault' : 'normal');
    scored.verdict = verdict;
    scored.control_pass = verdict === 'normal';
    scored.false_alarm = verdict === 'fault';
    scored.strict_top1_hit = false; // controls are not root-cause hits
    return scored;
  }

  const verdict = output?.verdict ?? (top3.length ? 'fault' : 'normal');
  scored.verdict = verdict;
  scored.control_pass = null;
  scored.false_alarm = null;

  // ---- TEP: FE-style leniency on the ranked list
  if (tIdv !== null) {
    const top3Idvs = new Set(top3.flatMap(idvNumbers));
    const hitIds = [tIdv, ...aliasOf(tIdv, causes).map((x) => Number(String(x).replace('IDV', '')))];
    scored.fe_style_top3_hit = hitIds.some((n) => top3Idvs.has(n));
    scored.true_idv = `IDV${tIdv}`;
    scored.alias_class = aliasOf(tIdv, causes);

    // STRICTER THAN THE REPOSITORY RUBRIC — reported alongside `strict_top1_hit`,
    // never instead of it. `strict_top1_hit` accepts a shared mechanism KEYWORD
    // in the rank-1 text, and the fault families {IDV4, IDV11, IDV14} and
    // {IDV5, IDV12, IDV15} share their keywords verbatim ("reactor cooling
    // water", "冷却水"). A keyword hit therefore does NOT establish that the
    // algorithm distinguished the specific fault within the family, whereas the
    // IDV number does. Both are surfaced so the distinction is auditable.
    const nameRank = top3.findIndex((t) => idvNumbers(t).includes(tIdv));
    scored.idv_rank = nameRank >= 0 ? nameRank + 1 : null;
    scored.exact_idv_top1_hit = nameRank === 0;
    scored.exact_idv_top3_hit = nameRank >= 0;
    scored.strict_but_not_exact = Boolean(strict) && nameRank !== 0;
  } else {
    scored.fe_style_top3_hit = null;
    scored.idv_rank = null;
    scored.exact_idv_top1_hit = null;
    scored.exact_idv_top3_hit = null;
    scored.strict_but_not_exact = false;
  }

  // ---- calibration: did the algorithm's declared conclusion type match truth?
  const expect = truth.expect_type_set || [];
  const declared = output?.diagnosis_type || (top3.length ? 'DETERMINED' : 'NEEDS_DATA');
  scored.diagnosis_type = declared;
  scored.calibrated = expect.length ? expect.includes(declared) : null;
  scored.overconfident = declared === 'DETERMINED' && !strict;
  return scored;
}

/** Roll a set of scored results into the headline metrics. */
export function aggregate(scored, { algorithms = null } = {}) {
  const all = Object.values(scored);
  // Unscored rows (user uploads) are excluded from every accuracy denominator —
  // counting them would silently drag every rate toward zero.
  const rows = all.filter((r) => r.scored !== false);
  const unscored = all.filter((r) => r.scored === false);
  const faults = rows.filter((r) => !r.control);
  const controls = rows.filter((r) => r.control);
  const tepFaults = faults.filter((r) => r.true_idv);
  const nonTepFaults = faults.filter((r) => !r.true_idv);

  const pct = (num, den) => (den ? Number((num / den).toFixed(4)) : null);
  const top1Count = faults.filter((r) => r.strict_top1_hit).length;
  const exactCount = tepFaults.filter((r) => r.exact_idv_top1_hit).length;
  return {
    algorithms,
    unscored_rows: unscored.length,
    scored_rows: rows.length,
    cases: rows.length,
    fault_cases: faults.length,
    control_cases: controls.length,
    tep_fault_cases: tepFaults.length,
    nontep_fault_cases: nonTepFaults.length,
    top1: top1Count,
    top1_rate: pct(top1Count, faults.length),
    top1_wilson: wilson(top1Count, faults.length),
    // exact-IDV metrics — only defined on TEP cases (non-TEP have no IDV truth)
    exact_idv_top1: exactCount,
    exact_idv_top1_rate: pct(exactCount, tepFaults.length),
    exact_idv_top1_wilson: wilson(exactCount, tepFaults.length),
    exact_idv_top3: tepFaults.filter((r) => r.exact_idv_top3_hit).length,
    exact_idv_top3_rate: pct(tepFaults.filter((r) => r.exact_idv_top3_hit).length, tepFaults.length),
    strict_but_not_exact: faults.filter((r) => r.strict_but_not_exact).length,
    idv_named: faults.filter((r) => r.idv_rank !== null && r.idv_rank !== undefined).length,
    tep_top1: tepFaults.filter((r) => r.strict_top1_hit).length,
    tep_top1_rate: pct(tepFaults.filter((r) => r.strict_top1_hit).length, tepFaults.length),
    nontep_top1: nonTepFaults.filter((r) => r.strict_top1_hit).length,
    nontep_top1_rate: pct(nonTepFaults.filter((r) => r.strict_top1_hit).length, nonTepFaults.length),
    fe_style_top3: tepFaults.filter((r) => r.fe_style_top3_hit).length,
    fe_style_top3_rate: pct(tepFaults.filter((r) => r.fe_style_top3_hit).length, tepFaults.length),
    control_pass: controls.filter((r) => r.control_pass).length,
    control_pass_rate: pct(controls.filter((r) => r.control_pass).length, controls.length),
    false_alarms: controls.filter((r) => r.false_alarm).length,
    calibrated: faults.filter((r) => r.calibrated).length,
    overconfident: faults.filter((r) => r.overconfident).length,
    answered: faults.filter((r) => r.top3.length > 0).length,
    abstained: faults.filter((r) => r.top3.length === 0).length,
  };
}

/** Wilson 95% score interval — the repository's reporting convention. */
export function wilson(k, n, z = 1.959963984540054) {
  if (!n) return null;
  const p = k / n;
  const denom = 1 + (z * z) / n;
  const centre = p + (z * z) / (2 * n);
  const spread = z * Math.sqrt((p * (1 - p)) / n + (z * z) / (4 * n * n));
  return [Number((((centre - spread) / denom) * 100).toFixed(1)), Number((((centre + spread) / denom) * 100).toFixed(1))];
}

/** The IDD full-pipeline reference row (read from archived results). */
export function iddReference() {
  const cases = loadCasesRaw();
  const out = { available: false };
  if (!exists(IDD_METRICS())) return out;
  try {
    const metrics = readJson(IDD_METRICS());
    out.available = true;
    out.metrics = metrics;
    out.total_cases = cases.length;
  } catch (err) {
    out.error = String(err && err.message ? err.message : err);
  }
  return out;
}
