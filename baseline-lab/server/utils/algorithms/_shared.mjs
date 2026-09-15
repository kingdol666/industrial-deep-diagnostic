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
import { faultWindow, loadCaseMatrix, loadMatrixCached, calibrationRows, readCsv } from '../dataset.mjs';

/** The dataset's normal-control case (the only legitimate training source). */
export function controlCaseFor(dataset) {
  const c = loadCasesRaw().find((x) => x.dataset === dataset && x.control);
  if (!c) return null;
  return { ...c, csv_abs: repoPath(c.csv) };
}

/**
 * Resolve the supervised training corpus for a case.
 *
 * TEP cases train on FaultExplainer's labelled runs, exactly as before — that is
 * the published protocol and it keeps the benchmark gates bit-identical.
 *
 * USER DATA has no labels, so a supervised classifier cannot be applied and
 * cannot be silently "adapted". What makes it usable is the user supplying their
 * OWN labelled file: `ctx.training.source === 'user-upload'`. When they have not,
 * the algorithms refuse with instructions instead of inventing classes.
 */
export function resolveTraining(caseDef) {
  const isUpload = caseDef.dataset === 'custom' || Boolean(caseDef.upload);
  if (!isUpload) {
    return { available: true, source: 'tep-faultexplainer' };
  }
  const t = caseDef.upload?.training;
  if (t?.path && exists(t.path)) {
    return { available: true, source: 'user-upload', path: t.path, label_column: t.label_column, meta: t };
  }
  return {
    available: false,
    source: null,
    reason:
      'No labelled training data was supplied with this upload. The supervised comparators (xgb-gbdt, '
      + 'rf-forest, mlp-classifier) are classifiers: they need examples of each fault class to learn from, '
      + 'and they cannot be applied to unlabelled data without inventing labels. Re-upload including a '
      + 'labelled training CSV to make them usable.',
  };
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
    training: resolveTraining(caseDef),
    is_upload: isUpload,
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

// ------------------------------------- user-supplied labelled training file
//
// The supervised comparators (xgb-gbdt, rf-forest, mlp-classifier) are
// classifiers: they need labelled examples. For a TEP benchmark case those come
// from FaultExplainer's corpus — that is the published protocol and it stays
// untouched. For an uploaded dataset the ONLY legitimate source is a labelled
// file the USER supplies (`ctx.training.source === 'user-upload'`); labelling
// their data ourselves would be fabrication, which is why an upload without one
// is refused outright (see resolveTraining above).
//
// Every join here is BY NAME, never by position. A positionally shifted feature
// vector still produces perfectly confident numbers, so a mismatch is an ERROR,
// never a best-effort guess.

/** Minimum labelled rows accepted from a user file (a classifier below this is degenerate). */
export const USER_MIN_ROWS = 20;
/** Minimum labelled rows per class (the class block must support a window aggregate). */
export const USER_MIN_ROWS_PER_CLASS = 10;
/** Smallest aggregation window that still gives a meaningful mean |first difference|. */
export const USER_MIN_WINDOW = 10;
/** Cap on how many names an alignment error prints (a 200-column dump helps nobody). */
const MAX_NAMES_IN_ERROR = 10;

/**
 * Adapt the aggregation window to a small labelled file.
 *
 * The TEP protocol aggregates 80-sample windows with stride 20. A user file of
 * 3 x 60 rows would yield ZERO such windows per class — an empty training matrix
 * and a silently useless model. So the window shrinks to a quarter of the
 * smallest class (never below USER_MIN_WINDOW, never above the protocol window)
 * and the stride to a quarter of the window. That reproduces the TEP 80/20
 * protocol EXACTLY as soon as every class has >= 320 rows, and degrades in a
 * disclosed way below that: the effective window is reported in the result.
 */
export function adaptTrainingWindow(rowsPerClass, protocolWindow = 80, protocolStride = 20) {
  const minRows = Math.min(...rowsPerClass);
  const window = Math.max(USER_MIN_WINDOW, Math.min(protocolWindow, Math.floor(minRows / 4)));
  const stride = Math.max(1, Math.floor((window * protocolStride) / protocolWindow));
  return { window, stride, minRows };
}

/**
 * Index of the class the user's OWN label strings identify as "normal", or -1.
 *
 * TEP fixes this by protocol (class 0 = Normal). On user data the labels are the
 * user's words, so the normal-vs-fault verdict is only asserted when a name
 * actually says so — otherwise `verdict` stays null rather than declaring an
 * arbitrary alphabetically-first class to be a fault.
 */
const NORMAL_LABEL_RE =
  /^(normal|no[_\- ]?fault|fault[_\- ]?free|no[_\- ]?failure|healthy|health|nominal|ok|okay|good|baseline|none|n|0)$/i;

export function uploadNormalClassIndex(labelNames) {
  return (labelNames || []).findIndex((n) => NORMAL_LABEL_RE.test(String(n).trim()));
}

/** Locale-independent string order (localeCompare depends on ICU and locale). */
function compareLabels(a, b) {
  return a < b ? -1 : a > b ? 1 : 0;
}

function nameList(names) {
  const head = names.slice(0, MAX_NAMES_IN_ERROR).join(', ');
  return names.length > MAX_NAMES_IN_ERROR ? `${head}, … (+${names.length - MAX_NAMES_IN_ERROR} more)` : head;
}

/** '' / null -> missing; anything non-numeric -> null. */
function numericValue(v) {
  if (v === '' || v === undefined || v === null) return null;
  const x = Number(String(v).trim());
  return Number.isFinite(x) ? x : null;
}

/** A column is a feature only if every non-empty entry is a number. */
function isNumericColumn(rows, j) {
  let any = false;
  for (let i = 0; i < rows.length; i++) {
    const raw = rows[i][j];
    if (numericValue(raw) === null) {
      if (raw !== '' && raw !== undefined && raw !== null) return false;
      continue;
    }
    any = true;
  }
  return any;
}

/** Forward-fill, then back-fill leading gaps — the convention loadMatrix uses. */
function fillColumn(rows, j) {
  const out = new Float64Array(rows.length);
  let last = null;
  for (let i = 0; i < rows.length; i++) {
    const v = numericValue(rows[i][j]);
    if (v !== null) last = v;
    out[i] = last === null ? NaN : last;
  }
  let first = null;
  for (let i = 0; i < rows.length; i++) if (!Number.isNaN(out[i])) { first = out[i]; break; }
  for (let i = 0; i < rows.length; i++) if (Number.isNaN(out[i])) out[i] = first ?? 0;
  return out;
}

/**
 * Split the monitored (fault) window into the SAME row-length windows the model
 * was trained on.
 *
 * WHY THIS EXISTS — the feature triple [mean, sd, mean |first difference|] is not
 * scale-free. A 15-row window and a 105-row window of the same stationary signal
 * have SYSTEMATICALLY different sd / mean|diff| (a longer window averages over
 * more of the oscillation). Scoring one whole-record aggregate with a model
 * trained on short windows therefore asks a question the model was never trained
 * on: on the verification case the sd features landed ~2.8 standard deviations
 * away from EVERY class while only the mean features still pointed at the right
 * one — the random forest and the boosted trees survived that (their splits lean
 * on the mean), the MLP did not.
 *
 * Scoring the monitored window in training-length windows removes the shift, and
 * the per-window answers are averaged (the agreement between them is reported,
 * so a near-tie across windows is visible rather than hidden).
 *
 * Falls back to a single (short) aggregate when the record is shorter than one
 * training window — disclosed in the result rather than silently rescaled.
 */
export function scoringWindows(rows, window, stride) {
  if (!rows.length) return [];
  if (!(window > 1) || rows.length < window) return [rows];
  const step = Math.max(1, stride || 1);
  const out = [];
  for (let s = 0; s + window <= rows.length; s += step) out.push(rows.slice(s, s + window));
  return out;
}

/**
 * Load a user-supplied labelled training file into the same corpus shape
 * loadFeTrainingSet() returns, with its feature columns re-ordered into the
 * DIAGNOSIS matrix's column order — so the windowed feature construction stays
 * byte-for-byte the one the TEP protocol uses.
 *
 * `training` is `ctx.training` ({ path, label_column, meta }).
 * `caseCols` is `ctx.matrix.colNames` — the columns of the data being diagnosed.
 *
 * Throws (never guesses) on: a missing/undeclared label column, a mismatched
 * feature column set, fewer than 2 classes, or a file too small to train on.
 */
export function loadUserTrainingCorpus(training, caseCols, { window: protocolWindow = 80, stride: protocolStride = 20 } = {}) {
  if (!training || !training.path) {
    throw new Error('no labelled training file was supplied for this upload — nothing to train on');
  }
  const originalName = training.original_name || training.meta?.original_name || null;
  const file = originalName ? `'${originalName}'` : training.path;
  if (!exists(training.path)) throw new Error(`the labelled training file is missing on disk: ${training.path}`);
  if (!Array.isArray(caseCols) || !caseCols.length) {
    throw new Error('the diagnosis data has no numeric columns, so a training file cannot be aligned to it');
  }
  const caseDupes = caseCols.filter((c, i) => caseCols.indexOf(c) !== i);
  if (caseDupes.length) {
    throw new Error(`the diagnosis data has duplicate column name(s) [${nameList([...new Set(caseDupes)])}] — aligning by name is ambiguous`);
  }

  const { header, rows } = readCsv(training.path);
  if (!header.length) throw new Error(`could not read a header row from the training file ${file}`);
  if (!rows.length) throw new Error(`the training file ${file} has no data rows`);

  // ---- label column (defensive: the upload store already validated it) -----
  const labelCol = String(training.label_column || '').trim();
  const li = labelCol ? header.indexOf(labelCol) : -1;
  if (li < 0) {
    throw new Error(
      `the training file ${file} has no label column named '${labelCol || '(none declared)'}'. `
      + `Columns present: [${nameList(header)}]. The class column must exist and be named label/class/fault/y/target, `
      + 'or be passed explicitly as label_column.',
    );
  }

  // ---- feature columns ----------------------------------------------------
  const featureCols = [];
  const pos = new Map();
  const nonNumeric = [];
  const seenNames = new Set();
  for (let j = 0; j < header.length; j++) {
    if (j === li) continue;
    const name = header[j];
    if (seenNames.has(name)) {
      throw new Error(`the training file ${file} has a duplicate column name '${name}' — aligning by name is ambiguous`);
    }
    seenNames.add(name);
    if (!isNumericColumn(rows, j)) { nonNumeric.push(name); continue; }
    pos.set(name, j);
    featureCols.push(name);
  }
  if (!featureCols.length) {
    throw new Error(`the training file ${file} has no numeric feature column besides the label column '${labelCol}'`);
  }

  const caseSet = new Set(caseCols);
  const missing = caseCols.filter((c) => !pos.has(c));             // diagnosis has it, training does not
  const extra = featureCols.filter((c) => !caseSet.has(c));        // training has it, diagnosis does not
  if (missing.length || extra.length) {
    throw new Error(
      `feature-column alignment failed between the diagnosis data and the training file ${file}: `
      + (missing.length ? `the training file has no column(s) [${nameList(missing)}] that the diagnosis data provides; ` : '')
      + (extra.length ? `the training file provides column(s) [${nameList(extra)}] that the diagnosis data does not; ` : '')
      + `features are matched BY NAME (column order may differ; the label column '${labelCol}' is excluded). `
      + `Diagnosis columns: [${nameList(caseCols)}]. Training feature columns: [${nameList(featureCols)}].`,
    );
  }

  // ---- class labels: the distinct strings, sorted deterministically --------
  const rawLabels = rows.map((r) => String(r[li] ?? '').trim());
  const labelNames = [...new Set(rawLabels.filter(Boolean))].sort(compareLabels);
  if (labelNames.length < 2) {
    throw new Error(
      `the training file ${file} has ${labelNames.length} distinct class label(s) in '${labelCol}' `
      + `(${labelNames.map((s) => `'${s}'`).join(', ') || 'none'}) — a classifier needs at least 2.`,
    );
  }
  const classOf = new Map(labelNames.map((s, k) => [s, k]));

  const kept = [];
  const byClass = Array.from({ length: labelNames.length }, () => []);
  let unlabelled = 0;
  for (let i = 0; i < rows.length; i++) {
    const s = rawLabels[i];
    if (!s || !classOf.has(s)) { unlabelled++; continue; }
    kept.push(i);
    byClass[classOf.get(s)].push(i);
  }
  if (kept.length < USER_MIN_ROWS) {
    throw new Error(
      `the training file ${file} has only ${kept.length} labelled row(s) (of ${rows.length}) — `
      + `at least ${USER_MIN_ROWS} are needed to train a classifier.`,
    );
  }
  const runsPerClass = byClass.map((a) => a.length);
  const thin = runsPerClass.findIndex((n) => n < USER_MIN_ROWS_PER_CLASS);
  if (thin >= 0) {
    throw new Error(
      `class '${labelNames[thin]}' has only ${runsPerClass[thin]} labelled row(s) in ${file} — at least `
      + `${USER_MIN_ROWS_PER_CLASS} per class are needed, because the model aggregates a window of the class's own rows. `
      + `Rows per class: [${labelNames.map((n, k) => `${n}=${runsPerClass[k]}`).join(', ')}].`,
    );
  }

  // ---- matrix in DIAGNOSIS column order (features stay apples-to-apples) ---
  const cols = caseCols.slice();
  const columns = cols.map((c) => fillColumn(rows, pos.get(c)));
  const X = Array.from({ length: rows.length }, (_, i) => Float64Array.from(cols, (_, c) => columns[c][i]));

  const { window, stride, minRows } = adaptTrainingWindow(runsPerClass, protocolWindow, protocolStride);

  return {
    cols,
    X,
    byClass,
    labelNames,
    classCount: labelNames.length,
    runsPerClass,
    source: 'user-upload',
    // Cache isolation: a model trained on one user's file must never be reused
    // for another's (or for the TEP corpus).
    cacheKey: `user-upload:${training.path}`,
    path: training.path,
    original_name: originalName,
    label_column: labelCol,
    window,
    stride,
    minRowsPerClass: minRows,
    protocolWindow,
    totalRows: rows.length,
    usedRows: kept.length,
    droppedRows: 0,
    unnamedRuns: 0,
    unlabelledRows: unlabelled,
    nonNumericColumns: nonNumeric,
  };
}
