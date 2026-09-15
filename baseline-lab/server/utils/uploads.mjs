// Upload store — lets a user run the reproduction algorithms on their OWN data.
//
// Everything here is real ingest, not a placeholder: the uploaded bytes are
// parsed with the same CSV reader the benchmark cases use, validated for usable
// numeric content, and the measured shape (rows x numeric columns) is recorded
// in meta.json. If a file has no usable numeric columns the upload is REJECTED
// rather than stored and silently mishandled later.
//
// Resolution of `up_<id>` case ids lives in paths.mjs (the dependency-free
// layer). This module only WRITES and MANAGES uploads, and paths.mjs must never
// import it back — that cycle would evaluate `UPLOADS_DIR()` before `LAB_ROOT`
// exists and throw a TDZ error instead of degrading gracefully.

import fs from 'node:fs';
import path from 'node:path';
import {
  UPLOADS_DIR, caseIdForUpload, loadUploadMeta, uploadDataFile,
  ensureDir, exists, readJsonSafe, writeJson,
} from './paths.mjs';
import { parseCsv, loadMatrixCached, clearMatrixCache } from './dataset.mjs';

// NOTE: UPLOAD_PREFIX / caseIdForUpload / loadUploadMeta / uploadDataFile are
// deliberately NOT re-exported here. paths.mjs already exports them, and a
// second export surface made Nitro's import scanner report them as duplicates
// on every rebuild. Import them from paths.mjs.

/** Hard cap on a single upload. Generous for sensor exports, bounded for a dev server. */
export const MAX_UPLOAD_BYTES = 64 * 1024 * 1024;

function uploadDir(uploadId) {
  return path.join(UPLOADS_DIR(), uploadId);
}

function assertSafeId(uploadId) {
  if (!/^[A-Za-z0-9_-]{6,64}$/.test(String(uploadId || ''))) {
    throw new Error(`invalid upload id: ${uploadId}`);
  }
}

// ------------------------------------------------------------------ ingest

/**
 * Identify a time / row-index column.
 *
 * A datetime string is dropped automatically by the numeric filter, but many
 * exports use a NUMERIC index ("Time (h)", "t", "step", "sample"). If such a
 * column is left in the feature set it does not describe the process at all —
 * and because it is perfectly monotonic it tends to dominate distance- and
 * contribution-based statistics.
 *
 * NOTE: this correction is applied to UPLOADS ONLY, deliberately. The
 * repository's archived PCA baseline (results/benchmark/baseline_pca_rca.json)
 * was computed WITH IndPenSim's numeric `Time (h)` column in the feature set, so
 * changing the shared loader would silently break the verified 12/12 PCA
 * reproduction. Fixing the benchmark protocol is a separate, disclosed change.
 */
function detectIndexColumn(header, rows, timeCol) {
  // 1) by name
  const NAME = /^(time(\s*\(.*\))?|timestamp|datetime|date|ts|t|index|idx|step|sample|no\.?|#)$/i;
  const byName = header.findIndex((h) => NAME.test(String(h).trim()));
  if (byName >= 0) {
    return { index: byName, column: header[byName], reason: 'header name identifies a time/index column' };
  }
  if (timeCol) {
    const i = header.indexOf(timeCol);
    if (i >= 0) return { index: i, column: timeCol, reason: 'detected as the time column' };
  }
  // 2) by behaviour: strictly monotonic numeric column with a constant step
  for (let j = 0; j < header.length; j++) {
    const vals = [];
    for (const r of rows) {
      const v = Number(r[j]);
      if (Number.isNaN(v)) { vals.length = 0; break; }
      vals.push(v);
    }
    if (vals.length < 10) continue;
    let step = vals[1] - vals[0];
    let monotonic = true;
    for (let i = 2; i < vals.length; i++) {
      const d = vals[i] - vals[i - 1];
      if (Math.abs(d - step) > Math.abs(step) * 1e-6 + 1e-9) { monotonic = false; break; }
    }
    if (monotonic && step !== 0) {
      return { index: j, column: header[j], reason: 'strictly monotonic with a constant step (a row index, not a sensor)' };
    }
  }
  return null;
}

/** Re-serialise rows with one column removed. */
function csvWithoutColumn(header, rows, dropIndex) {
  const keep = header.map((_, j) => j).filter((j) => j !== dropIndex);
  const esc = (s) => {
    const v = s === undefined || s === null ? '' : String(s);
    return /[",\n\r]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v;
  };
  const out = [keep.map((j) => esc(header[j])).join(',')];
  for (const r of rows) out.push(keep.map((j) => esc(r[j])).join(','));
  return out.join('\n');
}

/**
 * Parse and validate an uploaded buffer. Returns the analysis of the content;
 * throws with a user-facing message when the file cannot be used.
 */
export function analyzeUpload(buffer, filename) {
  const text = buffer.toString('utf8');
  if (!text.trim()) throw new Error('the uploaded file is empty');

  const { header, rows } = parseCsv(text);
  if (!header.length) throw new Error('could not read a header row from the file');
  if (rows.length < 10) {
    throw new Error(`only ${rows.length} data row(s) found — at least 10 are needed to compute anything meaningful`);
  }

  const timeCol = header.find((h) => /^(timestamp|time|datetime|date|ts)$/i.test(String(h).trim())) || null;
  const index = detectIndexColumn(header, rows, timeCol);

  // Which columns actually carry numbers? (same rule the benchmark loader uses)
  const numericCols = [];
  const emptyCols = [];
  const allNullCols = [];
  for (let j = 0; j < header.length; j++) {
    if (index && j === index.index) continue; // a row index is not a feature
    let numeric = 0, nonEmpty = 0;
    for (const r of rows) {
      const v = r[j];
      if (v === '' || v === undefined) continue;
      nonEmpty++;
      if (!Number.isNaN(Number(v))) numeric++;
    }
    if (nonEmpty === 0) allNullCols.push(header[j]);
    else if (numeric === 0) emptyCols.push(header[j]);
    else numericCols.push(header[j]);
  }

  if (numericCols.length < 2) {
    throw new Error(
      `only ${numericCols.length} numeric column(s) detected — at least 2 are required for multivariate monitoring. `
      + `Columns seen: ${header.slice(0, 12).join(', ')}${header.length > 12 ? ', …' : ''}`,
    );
  }

  return {
    original_name: filename || 'upload.csv',
    bytes: buffer.length,
    rows: rows.length,
    header_columns: header.length,
    numeric_columns: numericCols.length,
    columns: numericCols,
    dropped_non_numeric: emptyCols,
    dropped_empty: allNullCols,
    time_col: index ? index.column : null,
    excluded_index_column: index ? index.column : null,
    excluded_index_reason: index ? index.reason : null,
    header_preview: header.slice(0, 60),
    // Kept so the caller can rewrite the CSV with the index column removed.
    _raw: { header, rows, dropIndex: index ? index.index : -1 },
  };
}

/** Persist an uploaded dataset. Returns its meta. */
export function createUpload(buffer, filename, options = {}) {
  if (buffer.length > MAX_UPLOAD_BYTES) {
    throw new Error(`file is ${(buffer.length / 1048576).toFixed(1)} MB, over the ${MAX_UPLOAD_BYTES / 1048576} MB limit`);
  }
  const analysis = analyzeUpload(buffer, filename); // throws before anything is written

  const uploadId = `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 8)}`;
  const dir = ensureDir(uploadDir(uploadId));

  // Store the feature matrix WITHOUT the detected time/index column, so nothing
  // downstream can accidentally treat a row counter as a sensor.
  const { _raw, ...meta0 } = analysis;
  const stored = _raw.dropIndex >= 0
    ? csvWithoutColumn(_raw.header, _raw.rows, _raw.dropIndex)
    : buffer.toString('utf8');
  fs.writeFileSync(path.join(dir, 'data.csv'), stored, 'utf8');

  // Optional LABELLED training file. Supervised comparators cannot run on
  // unlabelled data without inventing class labels; supplying this is what makes
  // them usable. Stored verbatim (no index-column surgery: the label column must
  // survive) and validated for a usable label column.
  let training = null;
  if (options.training_buffer?.length) {
    const tName = options.training_filename || 'training.csv';
    const tText = options.training_buffer.toString('utf8');
    const { header, rows } = parseCsv(tText);
    if (rows.length < 20) throw new Error(`training file has only ${rows.length} row(s); at least 20 are needed`);
    const labelCol = String(options.label_column || '').trim()
      || header.find((h) => /^(label|class|fault|y|target|idv)$/i.test(String(h).trim()));
    if (!labelCol) {
      throw new Error(
        `could not identify a label column in ${tName}. Name it label/class/fault/y/target, `
        + `or pass label_column explicitly. Columns seen: ${header.slice(0, 12).join(', ')}`,
      );
    }
    const li = header.indexOf(labelCol);
    if (li < 0) throw new Error(`label column '${labelCol}' is not present in ${tName}`);
    const labels = [...new Set(rows.map((r) => String(r[li]).trim()))].filter(Boolean);
    if (labels.length < 2) {
      throw new Error(`training file has only ${labels.length} distinct label(s) — a classifier needs at least 2`);
    }
    // Drop the index column from the TRAINING file by its OWN detection.
    //
    // BUG THIS FIXES: the diagnosis file's `dropIndex` was being applied to the
    // training file. The two files rarely have the same column order — the
    // diagnosis file leads with `timestamp` while a user's labelled export might
    // not — so a positional drop silently deleted a real sensor (XMEAS_1),
    // and the classifiers then failed to align with a confusing message.
    // Columns must be reconciled BY NAME, never by position.
    const tIndex = detectIndexColumn(header, rows, null);
    const tDrop = tIndex && tIndex.index !== li ? tIndex.index : -1;
    const tStored = tDrop >= 0 ? csvWithoutColumn(header, rows, tDrop) : tText;
    fs.writeFileSync(path.join(dir, 'training.csv'), tStored, 'utf8');
    training = {
      path: path.join(dir, 'training.csv'),
      original_name: tName,
      label_column: labelCol,
      rows: rows.length,
      classes: labels.length,
      class_names: labels.slice(0, 60),
      dropped_index_column: tDrop >= 0 ? header[tDrop] : null,
      columns: header.filter((_, i) => i !== tDrop && i !== li),
    };
  }

  const meta = {
    upload_id: uploadId,
    case_id: caseIdForUpload(uploadId),
    uploaded_at: new Date().toISOString(),
    ...meta0,
    stored_bytes: Buffer.byteLength(stored, 'utf8'),
    // User-supplied context. `process_description` is fed to the LLM comparators
    // verbatim; it is the only domain knowledge the system has for this data.
    label: String(options.label || '').trim() || filename || uploadId,
    process_description: String(options.process_description || '').trim(),
    // Optional fixed cause list (newline- or semicolon-separated). The
    // FaultExplainer protocol prompts the model with a documented cause list; on
    // user data that list must come from the user, not from TEP.
    cause_list: parseCauseList(options.cause_list),
    // Fraction of the record used to calibrate thresholds (see _shared.mjs).
    calibration_fraction: normaliseCalibration(options.calibration_fraction),
    notes: String(options.notes || '').trim(),
    training,
  };
  writeJson(path.join(dir, 'meta.json'), meta);
  return meta;
}

/** Parse a user-supplied cause list into [{ id, description }]. */
function parseCauseList(raw) {
  const text = String(raw || '').trim();
  if (!text) return null;
  const lines = text.split(/[\n;]+/).map((s) => s.trim()).filter(Boolean);
  if (!lines.length) return null;
  return lines.slice(0, 60).map((line, i) => {
    const m = line.match(/^([^:：]{1,24})[:：]\s*(.+)$/);
    return m ? { id: m[1].trim(), description: m[2].trim() } : { id: `C${i + 1}`, description: line };
  });
}

function normaliseCalibration(v) {
  const f = Number(v);
  if (!Number.isFinite(f)) return 0.3;
  return Math.min(0.8, Math.max(0.05, f));
}

// ------------------------------------------------------------------ access

export function listUploads() {
  const dir = UPLOADS_DIR();
  if (!exists(dir)) return [];
  return fs
    .readdirSync(dir, { withFileTypes: true })
    .filter((d) => d.isDirectory())
    .map((d) => readJsonSafe(path.join(dir, d.name, 'meta.json'), null))
    .filter(Boolean)
    .sort((a, b) => String(b.uploaded_at).localeCompare(String(a.uploaded_at)));
}

/** Full meta for one upload (delegates to the dependency-free resolver). */
export function getUpload(uploadId) {
  return loadUploadMeta(uploadId);
}

export function uploadMatrix(uploadId) {
  return loadMatrixCached(uploadDataFile(uploadId));
}

export function deleteUpload(uploadId) {
  assertSafeId(uploadId);
  const dir = uploadDir(uploadId);
  if (!exists(dir)) return false;
  // Drop the cached parsed matrix first, so a later upload that reuses the id
  // cannot be served stale rows.
  clearMatrixCache(path.join(dir, 'data.csv'));
  fs.rmSync(dir, { recursive: true, force: true });
  return true;
}

