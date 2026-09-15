// Shared algorithm context: reference (normal) data selection, detection
// metrics, and result shaping.
//
// PROTOCOL (kept identical to scripts/benchmark/baseline_pca.mjs so the lab's
// PCA numbers are directly comparable with the repository's archived
// results/benchmark/baseline_pca_rca.json):
//   reference = the normal-control scenario file of the SAME dataset
//   detection = alarm rate over the case's fault window
//     tep   : data rows 161.. (published TEP d0X onset, 3-min sampling)
//     other : whole file (prepared segments are already windowed)
//   alarm threshold = derived from the REFERENCE distribution only, never
//     from the file under test.

import { loadCasesRaw, repoPath, exists } from '../paths.mjs';
import { faultWindow, loadCaseMatrix, loadMatrixCached, calibrationRows } from '../dataset.mjs';

/** The dataset's normal-control case (the only legitimate training source). */
export function controlCaseFor(dataset) {
  const c = loadCasesRaw().find((x) => x.dataset === dataset && x.control);
  if (!c) return null;
  return { ...c, csv_abs: repoPath(c.csv) };
}

/**
 * Build the evaluation context handed to every algorithm.
 * `caseDef` MUST already be sanitized (no truth fields) — see paths.mjs.
 *
 * REFERENCE SELECTION
 * -------------------
 * Benchmark cases: the dataset's registered normal-control scenario file. This
 * is the protocol the repository's own PCA script uses, which is what makes the
 * lab's numbers comparable with results/benchmark/baseline_pca_rca.json.
 *
 * Uploaded user data: there is no registered control, so the reference is a
 * CALIBRATION SPLIT of the uploaded record itself — the first
 * `calibration_fraction` (default 30%) of rows. That is the standard approach for
 * a single unlabelled record and it needs no second file from the user, but it is
 * a weaker footing than an independent normal run, so it is recorded in
 * `reference.source` and surfaced in the result and the UI rather than hidden.
 */
export function buildContext(caseDef, { log = () => {} } = {}) {
  const matrix = loadCaseMatrix(caseDef);

  const isUpload = caseDef.dataset === 'custom' || Boolean(caseDef.upload);
  let reference = null;
  let win;

  if (isUpload) {
    const fraction = caseDef.upload?.calibration_fraction ?? 0.3;
    const cut = calibrationRows(matrix.n, fraction);
    reference = {
      case_id: `${caseDef.case_id}:calibration`,
      matrix: {
        ...matrix,
        X: matrix.X.slice(0, cut),
        n: cut,
        times: matrix.times.slice(0, cut),
      },
      is_self: true,
      source: 'in-file calibration split',
      disclosure:
        `Thresholds are calibrated on the first ${cut} of ${matrix.n} rows (${(fraction * 100).toFixed(0)}%) `
        + 'of THIS file. No independent normal-operation baseline was supplied, so treat the control limits as '
        + 'self-referenced: if that leading segment is not representative of normal operation, the limits inherit that.',
      calibration_rows: cut,
      monitored_rows: matrix.n - cut,
    };
    win = { start: cut, end: matrix.n };
  } else {
    win = faultWindow(caseDef, matrix.n);
    const ctrl = controlCaseFor(caseDef.dataset);
    if (ctrl && exists(ctrl.csv_abs)) {
      reference = {
        case_id: ctrl.case_id,
        matrix: loadMatrixCached(ctrl.csv_abs),
        is_self: ctrl.case_id === caseDef.case_id,
        source: 'registered normal-control case',
        disclosure: `Thresholds come from the dataset's normal-control scenario (${ctrl.case_id}).`,
      };
    }
  }

  return {
    caseDef,
    matrix,
    faultWindow: win,
    reference,
    has_ground_truth: !isUpload,
    log,
    /** rows of the case inside its monitoring window */
    faultRows() {
      return matrix.X.slice(win.start, win.end);
    },
  };
}

/**
 * Detection statistics from a per-row statistic series.
 * `threshold` applies to the reference-derived control limit.
 */
export function detectionStats(stat, threshold, win, n) {
  const inWin = stat.slice(win.start, win.end);
  const alarms = inWin.filter((v) => v > threshold).length;
  const rate = inWin.length ? alarms / inWin.length : 0;
  const refRate = stat.slice(0, win.start).length
    ? stat.slice(0, win.start).filter((v) => v > threshold).length / stat.slice(0, win.start).length
    : null;
  return {
    detection_rate: Number(rate.toFixed(4)),
    alarms,
    window_rows: inWin.length,
    pre_window_alarm_rate: refRate === null ? null : Number(refRate.toFixed(4)),
    threshold: Number.isFinite(threshold) ? Number(threshold.toFixed(6)) : threshold,
    max_stat: Number(Math.max(...stat.map((v) => (Number.isFinite(v) ? v : 0))).toFixed(6)),
    series_head: stat.slice(0, 8).map((v) => Number((Number.isFinite(v) ? v : 0).toFixed(4))),
  };
}

/**
 * Rank variables by mean contribution over the fault window.
 * `contrib` is a function (rowIndex) -> per-variable contribution array.
 */
export function rankContributors(matrix, win, contrib, { topK = 6 } = {}) {
  const m = matrix.m;
  const sums = new Float64Array(m);
  let count = 0;
  for (let i = win.start; i < win.end; i++) {
    const c = contrib(i);
    if (!c) continue;
    for (let j = 0; j < m; j++) sums[j] += Math.abs(c[j]);
    count++;
  }
  if (!count) return [];
  const ranked = Array.from({ length: m }, (_, j) => ({
    col: matrix.colNames[j],
    contribution: sums[j] / count,
  }));
  ranked.sort((a, b) => b.contribution - a.contribution);
  return ranked.slice(0, topK).map((r) => ({
    col: r.col,
    contribution: Number(r.contribution.toFixed(6)),
  }));
}

/** Standard "alarm = statistic above limit" verdict for a detector. */
export function detectorVerdict(caseDef, det, { minRate = 0.05 } = {}) {
  if (caseDef.control) {
    // A control case should NOT alarm; report honestly either way.
    return det.detection_rate > minRate ? 'fault' : 'normal';
  }
  return det.detection_rate > minRate ? 'fault' : 'normal';
}
