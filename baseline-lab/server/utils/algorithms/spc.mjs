// Univariate SPC ensemble — EWMA + two-sided CUSUM on every numeric column.
//
// Protocol (Roberts 1959 for EWMA; Page 1954 for CUSUM; Montgomery, "Statistical
// Quality Control" for the standard tuned constants):
//
//   reference = the normal-control scenario file of the SAME dataset
//   mu_j, sigma_j = REFERENCE column mean / population std (zero-variance
//     columns are guarded to scale 1 by colStats, so a constant sensor yields
//     z = 0 and cannot produce NaN)
//   z_tj      = (x_tj - mu_j) / sigma_j
//   EWMA      e_t = lambda z_t + (1 - lambda) e_{t-1},  e_0 = 0,  lambda = 0.2
//   CUSUM     S+_t = max(0, S+_{t-1} + z_t - k),  S-_t = max(0, S-_{t-1} - z_t - k)
//             with k = 0.5 sigma (the textbook k = delta/2 = 0.5 sigma default);
//             the decision interval h = 5 sigma is the textbook default and is
//             reported as `nominal_cusum_h`. The OPERATIVE limit is the
//             99th percentile of the reference statistic series (leakage-free:
//             calibrated on the reference file only), which for correlated
//             process data is typically below the i.i.d. h = 5 design point.
//   a column alarms at row t when |e_t| > ewma_limit_j or CUSUM_t > cusum_limit_j
//   ensemble alarm statistic a_t = max_j max(|e_tj|/ewma_limit_j, CUSUM_tj/cusum_limit_j)
//     (dimensionless; a_t > 1 is exactly "at least one column chart exceeded its
//      own reference-calibrated limit")
//   MULTIPLICITY CONTROL: the operative decision limit is the 99th percentile of
//     the REFERENCE ensemble series a_t, i.e. the same reference-calibration
//     principle applied to the combined statistic. This matters: with m
//     independent charts each at their own 1% level, ">= 1 column alarm" fires on
//     1-(1-0.01)^m of normal rows (41% at m=52, 8% at m=8, 28% at m=32) — measured
//     on the reference files: 48.1% (TEP, m=52), 13.0% (SKAB, m=8), 27.4%
//     (IndPenSim, m=32). A detector that alarms on half of all normal TEP rows is
//     not a detector, so the alarm is raised when a_t exceeds the reference
//     99th percentile of a_t (measured limits 1.44 / 1.39 / 1.38) and the literal
//     ">= 1 column alarm" rate (a_t > 1) is ALSO reported as
//     `any_column_alarm_rate` so the difference is auditable. Both numbers come
//     from the reference file only — nothing is calibrated on the file under test.
//   contributors   = (per-column alarm frequency normalised by the largest
//                     column frequency) x (mean |z| over the fault window)
//     i.e. a column must both alarm often and deviate far to rank first.
//
// HONESTY CONTRACT: this module produces CONTRIBUTING VARIABLES, not mechanisms.
// The variable → root-cause step is the separate, documented mapping in
// ../tep-affinity.mjs and is reported in `diagnosis_step`.

import { quantile, colStats, mean } from '../linalg.mjs';
import { detectionStats, detectorVerdict } from './_shared.mjs';
import { variablesToCandidates, affinityAvailable } from '../tep-affinity.mjs';

export const meta = {
  id: 'spc-ewma-cusum',
  label: '单变量统计过程控制集成 (EWMA+CUSUM)',
  short: 'SPC',
  family: 'classical',
  kind: 'detector',
  deterministic: true,
  requiresProvider: false,
  needsReference: true,
  description:
    'Per-column EWMA (lambda=0.2) and two-sided CUSUM (k=0.5 sigma, h=5 sigma nominal) against reference mean/sigma with 99th-percentile per-column reference limits; the combined exceedance statistic is alarmed at its own reference 99th percentile (multiplicity control over the column union), and contributors are normalised alarm frequency x mean |z| deviation.',
  provenance: {
    basis: ['roberts1959ewma', 'page1954cusum', 'montgomerysqc'],
    repo: null,
    note: 'Deterministic in-process reimplementation on the lab linalg primitives; a fully univariate chart ensemble, so it is domain-agnostic (works on TEP, SKAB and IndPenSim alike).',
  },
};

export const EWMA_LAMBDA = 0.2;
export const CUSUM_K = 0.5;
export const CUSUM_H = 5;
export const ALARM_Q = 0.99;
const LIMIT_FLOOR = 1e-9;

/**
 * Calibrate the per-column limits on the reference series (in-sample charts).
 * Constant columns give limit 0, which LIMIT_FLOOR turns into "any deviation
 * from a perfectly constant reference is an alarm" instead of a 0/0 NaN.
 */
export function fitSpc(train) {
  const m = train[0].length;
  const { mu, sd } = colStats(train, 0);

  const n = train.length;
  const ewma = new Float64Array(m);
  const sp = new Float64Array(m);
  const sn = new Float64Array(m);
  const ewmaSeries = Array.from({ length: m }, () => new Float64Array(n));
  const cusumSeries = Array.from({ length: m }, () => new Float64Array(n));

  for (let t = 0; t < n; t++) {
    const row = train[t];
    for (let j = 0; j < m; j++) {
      const z = (row[j] - mu[j]) / sd[j];
      ewma[j] = EWMA_LAMBDA * z + (1 - EWMA_LAMBDA) * ewma[j];
      sp[j] = Math.max(0, sp[j] + z - CUSUM_K);
      sn[j] = Math.max(0, sn[j] - z - CUSUM_K);
      const cs = Math.max(sp[j], sn[j]);
      ewmaSeries[j][t] = Math.abs(ewma[j]);
      cusumSeries[j][t] = cs;
    }
  }

  const ewmaLimit = new Float64Array(m);
  const cusumLimit = new Float64Array(m);
  for (let j = 0; j < m; j++) {
    const e = Array.from(ewmaSeries[j]).sort((a, b) => a - b);
    const c = Array.from(cusumSeries[j]).sort((a, b) => a - b);
    ewmaLimit[j] = quantile(e, ALARM_Q);
    cusumLimit[j] = quantile(c, ALARM_Q);
  }

  return { mu, sd, m, n, ewmaLimit, cusumLimit };
}

/**
 * Run the chart ensemble over a row sequence (state starts at zero, exactly as
 * on the reference series). Returns per-row statistics and per-column alarms.
 */
export function spcSeries(rows, model) {
  const { mu, sd, m, ewmaLimit, cusumLimit } = model;
  const n = rows.length;
  const ewma = new Float64Array(m);
  const sp = new Float64Array(m);
  const sn = new Float64Array(m);

  const out = {
    z: new Array(n),
    ensemble: new Float64Array(n),
    columnAlarm: new Uint8Array(n * m),
  };

  for (let t = 0; t < n; t++) {
    const row = rows[t];
    const zt = new Float64Array(m);
    let ens = 0;
    for (let j = 0; j < m; j++) {
      const raw = (row[j] - mu[j]) / sd[j];
      const z = Number.isFinite(raw) ? raw : 0;
      zt[j] = z;
      ewma[j] = EWMA_LAMBDA * z + (1 - EWMA_LAMBDA) * ewma[j];
      sp[j] = Math.max(0, sp[j] + z - CUSUM_K);
      sn[j] = Math.max(0, sn[j] - z - CUSUM_K);
      const cs = Math.max(sp[j], sn[j]);
      const rE = Math.abs(ewma[j]) / Math.max(ewmaLimit[j], LIMIT_FLOOR);
      const rC = cs / Math.max(cusumLimit[j], LIMIT_FLOOR);
      const r = Math.max(Number.isFinite(rE) ? rE : 0, Number.isFinite(rC) ? rC : 0);
      if (r > 1) out.columnAlarm[t * m + j] = 1;
      if (r > ens) ens = r;
    }
    out.z[t] = zt;
    out.ensemble[t] = Number.isFinite(ens) ? ens : 0;
  }
  return out;
}

export async function run(ctx) {
  const t0 = Date.now();
  const { caseDef, matrix, reference } = ctx;
  if (!reference) throw new Error('SPC baseline requires a normal-control reference for this dataset');
  if (reference.matrix.m !== matrix.m) {
    throw new Error(`SPC: reference width ${reference.matrix.m} does not match case width ${matrix.m}`);
  }

  const model = fitSpc(reference.matrix.X);
  const refSeries = spcSeries(reference.matrix.X, model);
  const ensembleLimit = quantile(Array.from(refSeries.ensemble).sort((a, b) => a - b), ALARM_Q);

  const series = spcSeries(matrix.X, model);
  const win = ctx.faultWindow;

  // Primary rule: the combined exceedance statistic above its OWN reference
  // 99th percentile (multiplicity-controlled). The literal ">= 1 column alarm"
  // reading (statistic > 1) is reported alongside for auditability.
  const det = detectionStats(Array.from(series.ensemble), ensembleLimit, win, matrix.n);
  const detAny = detectionStats(Array.from(series.ensemble), 1, win, matrix.n);

  const m = matrix.m;
  const winRows = win.end - win.start;
  const alarmCount = new Float64Array(m);
  const absZSum = new Float64Array(m);
  for (let t = win.start; t < win.end; t++) {
    const zt = series.z[t];
    for (let j = 0; j < m; j++) {
      if (series.columnAlarm[t * m + j]) alarmCount[j]++;
      absZSum[j] += Math.abs(zt[j]);
    }
  }
  const freq = Array.from(alarmCount, (c) => (winRows ? c / winRows : 0));
  const meanAbsZ = Array.from(absZSum, (s) => (winRows ? s / winRows : 0));
  const maxFreq = Math.max(0, ...freq);

  const ranked = Array.from({ length: m }, (_, j) => ({
    col: matrix.colNames[j],
    contribution: Number(((maxFreq > 0 ? freq[j] / maxFreq : 0) * meanAbsZ[j]).toFixed(6)),
    alarm_frequency: Number(freq[j].toFixed(4)),
    mean_abs_z: Number(meanAbsZ[j].toFixed(4)),
  })).sort((a, b) => b.contribution - a.contribution);

  const topAll = ranked.slice(0, 6);
  const topVars = topAll.map((r) => ({ col: r.col, contribution: r.contribution }));
  const columnsAlarming = freq.filter((f) => f > 0).length;
  const detectable = det.detection_rate > 0.05;

  const candidates = affinityAvailable(caseDef.dataset) && detectable
    ? variablesToCandidates(topVars.map((v) => v.col))
    : [];

  const winMeanAbsZ = meanAbsZ.length ? mean(meanAbsZ) : 0;
  const params = `lambda=${EWMA_LAMBDA} k=${CUSUM_K} h=${CUSUM_H} cols=${m}`;

  return {
    top3: candidates.map((c) => c.label),
    verdict: detectorVerdict(caseDef, det),
    variable_top3: topVars.map((v) => v.col),
    variables_ranked: topAll,
    detection: {
      detection_rate: det.detection_rate,
      alarms: det.alarms,
      window_rows: det.window_rows,
      pre_window_alarm_rate: det.pre_window_alarm_rate,
      threshold: det.threshold,
      max_stat: det.max_stat,
      series_head: det.series_head,
      ensemble: det,
      ensemble_limit: det.threshold,
      reference_ensemble_limit: Number(ensembleLimit.toFixed(6)),
      any_column_alarm_rate: detAny.detection_rate,
      any_column_alarms: detAny.alarms,
      any_column_pre_window_alarm_rate: detAny.pre_window_alarm_rate,
      decision_rule:
        'combined exceedance statistic a_t = max_j max(|EWMA_tj|/limit_j, CUSUM_tj/limit_j) above the reference 99th percentile of a_t (multiplicity-controlled); a_t > 1 ("at least one column chart exceeded its own limit") is reported as any_column_alarm_rate',
      columns_alarming: columnsAlarming,
      columns_total: m,
      nominal_cusum_h: CUSUM_H,
      nominal_cusum_k: CUSUM_K,
      ewma_lambda: EWMA_LAMBDA,
      ewma_limit_median: Number(quantile(Array.from(model.ewmaLimit).sort((a, b) => a - b), 0.5).toFixed(6)),
      cusum_limit_median: Number(quantile(Array.from(model.cusumLimit).sort((a, b) => a - b), 0.5).toFixed(6)),
      mean_abs_z_over_window: Number(winMeanAbsZ.toFixed(4)),
      detectable,
      params,
    },
    reasoning: detectable
      ? `The EWMA/CUSUM ensemble alarms on ${det.alarms}/${det.window_rows} fault-window rows (${(det.detection_rate * 100).toFixed(2)}%) with the combined exceedance statistic above its reference 99th-percentile limit ${det.threshold} (pre-window alarm rate ${det.pre_window_alarm_rate === null ? 'n/a' : (det.pre_window_alarm_rate * 100).toFixed(2) + '%'}); the literal "at least one column above its own limit" rule would fire on ${(detAny.detection_rate * 100).toFixed(2)}% of the window and ${detAny.pre_window_alarm_rate === null ? 'n/a' : (detAny.pre_window_alarm_rate * 100).toFixed(2) + '%'} of pre-window rows, which is the uncorrected ${m}-column union. ${columnsAlarming}/${m} columns exceed their per-column reference 99th-percentile limits at all (median EWMA limit ${quantile(Array.from(model.ewmaLimit).sort((a, b) => a - b), 0.5).toFixed(3)}, median CUSUM limit ${quantile(Array.from(model.cusumLimit).sort((a, b) => a - b), 0.5).toFixed(3)}, nominal h=${CUSUM_H} sigma). Highest normalised alarm-frequency x mean|z|: ${topAll.slice(0, 3).map((r) => `${r.col}(freq ${r.alarm_frequency}, |z| ${r.mean_abs_z})`).join(', ')}. Mechanism mapping (separate knowledge step): ${candidates.map((c) => c.idv).join(' > ') || 'none'}.`
      : `No detection: the combined EWMA/CUSUM exceedance statistic alarms on only ${det.alarms}/${det.window_rows} fault-window rows (${(det.detection_rate * 100).toFixed(2)}%) against its reference 99th-percentile limit ${det.threshold} (pre-window alarm rate ${det.pre_window_alarm_rate === null ? 'n/a' : (det.pre_window_alarm_rate * 100).toFixed(2) + '%'}). For transparency, the uncorrected "at least one column above its own limit" rule fires on ${(detAny.detection_rate * 100).toFixed(2)}% of the window rows (${columnsAlarming}/${m} columns alarm at all) — that inflation is the ${m}-column multiplicity of per-column 1% charts, not evidence of a fault. The chart ensemble reports no fault and therefore yields no root-cause candidates.`,
    diagnosis_step: affinityAvailable(caseDef.dataset)
      ? 'per-column (normalised per-column alarm frequency x mean |z| deviation) over the fault window -> top-6 -> documented TEP variable-affinity table (tep-affinity.mjs)'
      : 'unavailable for this domain (no published variable->cause table); per-column chart statistics reported as variables only',
    runtime_ms: Date.now() - t0,
  };
}
