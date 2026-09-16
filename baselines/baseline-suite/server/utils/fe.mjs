// fe.mjs — FaultExplainer-protocol replication (arm ii of the paper's §8.4 suite).
//
// Faithful to the FE official implementation (li-group/FaultExplainer @ 2fcfee9,
// vendored at baselines/FaultExplainer): PCA retained at 90% cumulative variance,
// Hotelling T2 alarm with alpha=0.01 (F-distribution limit), a fault is declared
// on 6 consecutive T2 alarms, the top-6 T2-contribution features are fed to the
// EXPLAIN_ROOT prompt together with the documented 15-fault TEP cause list.
import fs from 'node:fs';
import path from 'node:path';
import { REPO, tepCauseTable } from './repo.mjs';
import { loadMatrix, pcaModel, statistics, scenarioControl, TEP_FAULT_START } from './pca.mjs';

const VAR_CUTOFF_FE = 0.90;   // FE official: PCA(0.9)
const ALPHA = 0.01;           // FE official: T2(alpha=0.01, F-dist)
const CONSECUTIVE = 6;        // FE official: 6-consecutive trigger
const TOP_FEATURES = 6;       // FE official: top-6 T2-contribution features

// Wilson-Hilferty normal approximation of chi-square quantiles, then the
// F-limit T2^lim = h(n-1)/(n-h) * F_{h,n-h}(1-alpha). Validated against the
// archived FE official-code run (fe_official_code block in baselines.json).
function invNorm(p) {
  const a = [-3.969683028665376e1, 2.209460984245205e2, -2.759285104469687e2, 1.38357751867269e2, -3.066479806614716e1, 2.506628277459239];
  const b = [-5.447609879822406e1, 1.615858368580409e2, -1.556989798598866e2, 6.680131188771972e1, -1.328068155288572e1];
  const c = [-7.784894002430293e-3, -3.223964580411365e-1, -2.400758277161838, -2.549732539343734, 4.374664141464968, 2.938163982698783];
  const d = [7.784695709041462e-3, 3.224671290700398e-1, 2.445134137142996, 3.754408661907416];
  const pl = 0.02425;
  let q, r;
  if (p < pl) { q = Math.sqrt(-2 * Math.log(p)); return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1); }
  if (p <= 1 - pl) { q = p - 0.5; r = q * q; return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1); }
  q = Math.sqrt(-2 * Math.log(1 - p)); return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1);
}
function chi2q(df, p) { return df * Math.pow(1 - 2 / (9 * df) + invNorm(p) * Math.sqrt(2 / (9 * df)), 3); }
// FE official model.py: scaling_factor = a(n-1)(n+1) / (n(n-a)) times F_{1-alpha}(a, n-a)
function t2Limit(h, n, alpha) {
  const fRatio = (chi2q(h, 1 - alpha) / h) / (chi2q(n - h, 1 - alpha) / (n - h));
  return ((h * (n - 1) * (n + 1)) / (n * (n - h))) * fRatio;
}

/** FE arm — detection + top-6 per-feature T2 contributions + EXPLAIN_ROOT prompt.
 *  Documented deviation: the model is trained on the benchmark's normal-control
 *  recording (not FE's own 500-sample fault0), so detection outcomes on the
 *  benchmark corpus are the suite's own faithful-protocol execution. */
export function runFeArm(routing) {
  const control = scenarioControl(routing.dataset);
  const { mat: trainMat } = loadMatrix(control.csv);
  const model = pcaModel(trainMat, VAR_CUTOFF_FE);
  const trainN = trainMat.length;
  const { mat, cols } = loadMatrix(routing.csv);
  const stats = statistics(mat, model);
  const n = stats.length;
  const start = routing.dataset === 'tep' && !routing.control ? TEP_FAULT_START - 1 : 0;
  const h = model.a;

  const limit = t2Limit(h, trainN, ALPHA); // F-limit uses the TRAINING sample size (FE model.py self.n)
  const alarms = stats.map((s) => s.t2 > limit);
  let faultAt = -1, run = 0;
  for (let i = start; i < n; i++) {
    run = alarms[i] ? run + 1 : 0;
    if (run >= CONSECUTIVE) { faultAt = i - CONSECUTIVE + 1; break; }
  }

  // per-feature T2 decomposition at the first 6-consecutive-anomaly sample
  // (FE test_explain.py ranks t2_<feature> = z_j * (P L^-1 P^T z)_j there;
  // the j-sum of this decomposition equals the total T2). When the trigger
  // never fires, fall back to the fault-window max-T2 sample and say so.
  let idx = faultAt;
  if (idx < 0) {
    idx = start;
    for (let i = start; i < n; i++) if (stats[i].t2 > stats[idx].t2) idx = i;
  }
  const s = stats[idx];
  const perFeature = cols.map((name, j) => {
    let back = 0;
    for (let k = 0; k < model.P.length; k++) back += s.scores[k] * model.P[k][j] / model.lam[k];
    return { feature: name, t2_contribution: +(s.z[j] * back).toFixed(4) };
  }).sort((a, b) => b.t2_contribution - a.t2_contribution).slice(0, TOP_FEATURES);

  const detected = faultAt >= 0;
  const prompt = buildExplainRoot(perFeature, detected);
  return {
    arm: 'fe-protocol',
    method: `FE replication (protocol-faithful): PCA(${VAR_CUTOFF_FE}) + T2(alpha=${ALPHA}, F-limit ${limit.toFixed(1)}) + ${CONSECUTIVE}-consecutive trigger + top-${TOP_FEATURES} per-feature T2 contributions at trigger + EXPLAIN_ROOT. Trained on the benchmark normal-control recording (documented deviation from FE's fault0 corpus).`,
    detection: {
      detected,
      first_alarm_index: faultAt,
      alarm_region: faultAt >= 0 ? `rows ${faultAt + 1}..${n}` : `no ${CONSECUTIVE}-consecutive alarm (contribution sample: row ${idx + 1}, window max-T2 fallback)`,
      t2_limit: +limit.toFixed(2),
      components_retained: h,
      max_T2: +Math.max(...stats.slice(start).map((x) => x.t2)).toFixed(1),
      t2_at_contribution_sample: +s.t2.toFixed(1),
    },
    features: perFeature,
    prompt,
    prompt_arm: 'EXPLAIN_ROOT (root-causes-included; documented 15-fault TEP cause list)',
  };
}

/** FE's EXPLAIN_ROOT prompt shape (upstream prompts.py): features + cause list + JSON answer contract. */
export function buildExplainRoot(top6, detected) {
  const causes = tepCauseTable();
  const featureLines = top6.map((f, i) => `${i + 1}. ${f.feature} (T2 contribution ${f.t2_contribution})`).join('\n');
  const causeLines = Object.entries(causes.faults).map(([id, d]) => `- ${id}: ${d}`).join('\n');
  return [
    'You are an expert in industrial process monitoring and root-cause diagnosis of the Tennessee Eastman Process.',
    'The monitoring layer reports the following abnormal situation:',
    `Detection outcome: ${detected ? 'FAULT detected' : 'no decisive alarm'};`,
    'Top contributing features (T2 contribution ranking):',
    featureLines,
    '',
    'The documented root-cause catalogue of the process is:',
    causeLines,
    '',
    'EXPLAIN_ROOT: explain the root cause of the reported abnormality. Rank the three most probable root causes from the catalogue and justify each briefly using the contributing features.',
    'Answer with STRICT JSON only: {"top3": ["<IDVxx: description>", ...], "reasoning": "<3-5 sentences>"}',
  ].join('\n');
}
