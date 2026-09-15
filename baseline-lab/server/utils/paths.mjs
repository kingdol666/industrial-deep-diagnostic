// Path resolution + repo contract for the Baseline Lab.
//
// SINGLE SOURCE OF TRUTH: the lab reads the IDD repository's benchmark case
// definitions, prepared datasets, blind briefs and its own archived results.
// It never writes outside baseline-lab/results/.
//
// TRUTH ISOLATION (mirrors scripts/benchmark/check-leakage.mjs):
//   - `loadCase()`                     -> full case definition (MAY contain truth)
//   - `loadCaseForAlgorithm()`         -> sanitized: truth/keywords/literature_baseline STRIPPED
//   - `loadTruth()`                    -> truth fields, for the scorer only
// An algorithm module must only ever receive the sanitized object.

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));

/**
 * Resolve the lab root by *validating candidates against a known subdirectory*
 * rather than trusting one derivation. Under Nitro's bundler `import.meta.url`
 * can point into build output, so a fixed `../../` from the module is not
 * reliable on its own; `process.cwd()` covers `nuxt dev`/`nuxt start`, and an
 * explicit env override covers anything else.
 */
export const LAB_ROOT = (() => {
  const marker = path.join('server', 'utils', 'algorithms');
  const candidates = [
    process.env.BASELINE_LAB_ROOT,
    path.resolve(HERE, '..', '..'),
    process.cwd(),
  ].filter(Boolean);
  for (const c of candidates) {
    try {
      if (fs.existsSync(path.join(c, marker))) return c;
    } catch { /* try the next candidate */ }
  }
  return path.resolve(HERE, '..', '..');
})();
export const RESULTS_DIR = path.join(LAB_ROOT, 'results');
export const RUNS_DIR = path.join(RESULTS_DIR, 'runs');
export const SWEEPS_DIR = path.join(RESULTS_DIR, 'sweeps');

/** Resolve the IDD repo root (the parent of baseline-lab/ by default). */
export function repoRoot() {
  const configured = process.env.IDD_REPO_ROOT;
  const root = configured
    ? path.resolve(LAB_ROOT, configured)
    : path.resolve(LAB_ROOT, '..');
  return root;
}

export function repoPath(...parts) {
  return path.join(repoRoot(), ...parts);
}

export function exists(p) {
  try {
    fs.accessSync(p);
    return true;
  } catch {
    return false;
  }
}

export function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
  return dir;
}

export function readJson(file) {
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}

/**
 * Parse JSON, returning `fallback` instead of throwing. Reads can race a
 * concurrent writer, so callers that only need a best-effort view (the sweep
 * list, progress endpoints) use this.
 */
export function readJsonSafe(file, fallback = null) {
  try {
    return JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch {
    return fallback;
  }
}

/**
 * Write JSON atomically: serialise to a sibling temp file, then rename over the
 * target. A plain writeFileSync truncates first, so a concurrent reader (SSR
 * rendering the sweep list while a sweep is running) can observe a torn file and
 * fail to parse it. Rename is atomic on the same filesystem, so readers see
 * either the old or the new complete document — never a partial one.
 */
export function writeJson(file, value) {
  ensureDir(path.dirname(file));
  const body = JSON.stringify(value, null, 2);
  const tmp = `${file}.${process.pid}.${Date.now()}.tmp`;
  fs.writeFileSync(tmp, body, 'utf8');
  try {
    fs.renameSync(tmp, file);
  } catch {
    // Windows can refuse a rename while another handle holds the target open;
    // fall back to an in-place write so the sweep result is never lost.
    try { fs.rmSync(tmp, { force: true }); } catch { /* ignore */ }
    fs.writeFileSync(file, body, 'utf8');
  }
  return file;
}

// ---------------------------------------------------------------- contract

export const CASES_FILE = () => repoPath('scripts', 'benchmark', 'cases', 'benchmark_cases.json');
export const CAUSES_FILE = () => repoPath('scripts', 'benchmark', 'cases', 'tep_cause_table.json');
export const BRIEFS_DIR = () => repoPath('results', 'benchmark', 'briefs');
export const ARCHIVED_ANSWERS = () => repoPath('results', 'benchmark', 'baseline_fe_answers');
export const ARCHIVED_PROMPTS = () => repoPath('results', 'benchmark', 'baseline_fe_prompts');
export const FE_REPO = () => repoPath('baselines', 'FaultExplainer');
export const FE_TEP_DATA = () => repoPath('baselines', 'FaultExplainer', 'backend', 'data');

/**
 * Provenance of the vendored FaultExplainer tree.
 *
 * Upstream is vendored as plain files (see baselines/FaultExplainer/VENDOR.md),
 * so there is no `.git` to read a HEAD from. Prefer the live git metadata when
 * present (e.g. a developer re-cloned it), otherwise parse VENDOR.md — the pin
 * must stay visible in the audit either way.
 */
export function feProvenance() {
  const fe = FE_REPO();
  const out = { path: fe, cloned: exists(fe), commit: null, upstream: null, source: null, vendored: false };

  // 1) live git checkout, if someone replaced the vendored copy with a clone
  try {
    const head = fs.readFileSync(path.join(fe, '.git', 'HEAD'), 'utf8').trim();
    out.commit = head.startsWith('ref: ')
      ? fs.readFileSync(path.join(fe, '.git', head.slice(5).trim()), 'utf8').trim()
      : head;
    out.source = 'git';
    return out;
  } catch { /* vendored, not a checkout */ }

  // 2) vendored copy: read the recorded pin out of VENDOR.md
  const vendor = path.join(fe, 'VENDOR.md');
  if (exists(vendor)) {
    out.vendored = true;
    out.source = 'VENDOR.md';
    const text = fs.readFileSync(vendor, 'utf8');
    const commit = text.match(/\|\s*Commit\s*\|\s*`([0-9a-f]{7,40})`/i);
    const upstream = text.match(/\|\s*Upstream\s*\|\s*(\S+?)\s*\|/i);
    out.commit = commit ? commit[1] : null;
    out.upstream = upstream ? upstream[1] : null;
  }
  return out;
}
export const PCA_BASELINE = () => repoPath('results', 'benchmark', 'baseline_pca_rca.json');
export const IDD_BASELINES = () => repoPath('results', 'benchmark', 'baselines.json');
export const IDD_METRICS = () => repoPath('results', 'benchmark', 'metrics.json');

/**
 * The model identity the repository's ARCHIVED LLM baseline was produced with.
 * Surfaced so the lab can warn when a fresh execution uses a different model:
 * comparing a Claude run against a GLM-archived baseline is confounded, and a
 * results table that hides that would be misleading.
 */
export function archivedBaselineModel() {
  if (!exists(IDD_BASELINES())) return null;
  try {
    const doc = readJson(IDD_BASELINES());
    return {
      model: doc.model || null,
      protocol: doc.protocol || null,
      scoring: doc.scoring || null,
      source: 'results/benchmark/baselines.json',
    };
  } catch {
    return null;
  }
}

/** Fields that must never reach an algorithm implementation. */
const TRUTH_FIELDS = ['truth', 'keywords', 'literature_baseline', 'expect_type_set'];

export function loadCasesRaw() {
  const doc = readJson(CASES_FILE());
  return doc.cases || [];
}

// ------------------------------------------------- uploaded user datasets
//
// A user-uploaded dataset is addressed as `up_<uploadId>` so that every existing
// `loadCaseForAlgorithm` / `loadTruth` call site keeps working unchanged.
//
// Resolution lives HERE, in the dependency-free layer, and reads meta.json with
// plain fs. The store that *writes* uploads (server/utils/uploads.mjs) imports
// this module, so having paths.mjs import it back would create a cycle — and
// uploads.mjs touches `LAB_ROOT` at module-evaluation time, which would make
// that cycle throw a TDZ error rather than degrade gracefully.

export const UPLOADS_DIR = () => path.join(LAB_ROOT, 'uploads');
export const UPLOAD_PREFIX = 'up_';

export function isUploadCaseId(caseId) {
  return typeof caseId === 'string' && caseId.startsWith(UPLOAD_PREFIX);
}

export function uploadIdFromCaseId(caseId) {
  return isUploadCaseId(caseId) ? caseId.slice(UPLOAD_PREFIX.length) : null;
}

export function caseIdForUpload(uploadId) {
  return `${UPLOAD_PREFIX}${uploadId}`;
}

/** Read an upload's meta.json, or null when it does not exist. */
export function loadUploadMeta(uploadId) {
  if (!/^[A-Za-z0-9_-]{6,64}$/.test(String(uploadId || ''))) return null;
  const f = path.join(UPLOADS_DIR(), uploadId, 'meta.json');
  if (!exists(f)) return null;
  return readJsonSafe(f, null);
}

/** Absolute path of an upload's stored CSV. */
export function uploadDataFile(uploadId) {
  const f = path.join(UPLOADS_DIR(), uploadId, 'data.csv');
  if (!exists(f)) throw new Error(`uploaded data missing for ${uploadId}`);
  return f;
}

/**
 * Sanitized case definition for an uploaded dataset, in the exact shape the
 * algorithm context expects. Carries NO truth fields — there is no ground truth
 * for user data, and `loadTruth` says so explicitly.
 */
export function uploadCaseDef(uploadId) {
  const meta = loadUploadMeta(uploadId);
  if (!meta) throw new Error(`unknown upload: ${uploadId}`);
  const dataFile = uploadDataFile(uploadId);
  return {
    case_id: meta.case_id,
    dataset: 'custom',
    csv: `uploads/${uploadId}/data.csv`,
    csv_abs: dataFile,
    time_col: meta.time_col || 'row_index',
    control: false,
    process_description: meta.process_description || '',
    upload: {
      upload_id: meta.upload_id,
      label: meta.label,
      original_name: meta.original_name,
      rows: meta.rows,
      numeric_columns: meta.numeric_columns,
      columns: meta.columns,
      dropped_non_numeric: meta.dropped_non_numeric,
      calibration_fraction: meta.calibration_fraction,
      // Optional user-supplied domain knowledge. Both are what make the
      // TEP-scoped comparators usable on an arbitrary process:
      //   cause_list -> the FaultExplainer protocol's candidate list
      //   training   -> labelled examples for the supervised classifiers
      cause_list: meta.cause_list || null,
      training: meta.training || null,
      process_description: meta.process_description || '',
    },
  };
}

/**
 * Truth stub for uploaded data. `has_ground_truth: false` is what makes the
 * scorer report the run as UNSCORED instead of inventing a hit/miss.
 */
export function uploadTruthStub(uploadId) {
  const meta = loadUploadMeta(uploadId);
  if (!meta) throw new Error(`unknown upload: ${uploadId}`);
  return {
    case_id: meta.case_id,
    dataset: 'custom',
    control: false,
    has_ground_truth: false,
    truth: '',
    keywords: [],
    expect_type_set: [],
    literature_baseline: null,
    note:
      'User-uploaded data: no ground truth exists, so this run is reported as UNSCORED. '
      + 'Detection statistics and root-cause hypotheses are still produced and are genuine.',
  };
}

export function loadCase(caseId) {
  if (isUploadCaseId(caseId)) {
    const meta = loadUploadMeta(uploadIdFromCaseId(caseId));
    if (!meta) throw new Error(`unknown uploaded case_id: ${caseId}`);
    return { case_id: meta.case_id, dataset: 'custom', csv: `uploads/${meta.upload_id}/data.csv`, control: false };
  }
  const c = loadCasesRaw().find((x) => x.case_id === caseId);
  if (!c) throw new Error(`unknown case_id: ${caseId}`);
  return c;
}

/** Sanitized case definition — safe to hand to a diagnostic algorithm. */
export function loadCaseForAlgorithm(caseId) {
  if (isUploadCaseId(caseId)) return uploadCaseDef(uploadIdFromCaseId(caseId));
  const c = loadCase(caseId);
  const safe = { ...c };
  for (const f of TRUTH_FIELDS) delete safe[f];
  // `csv` is a repo-relative path; expose an absolute one for the loader.
  safe.csv_abs = repoPath(c.csv);
  return safe;
}

/** Truth-only view, for the scorer. Uploads have none — reported, not invented. */
export function loadTruth(caseId) {
  if (isUploadCaseId(caseId)) return uploadTruthStub(uploadIdFromCaseId(caseId));
  const c = loadCase(caseId);
  return {
    case_id: c.case_id,
    dataset: c.dataset,
    control: !!c.control,
    has_ground_truth: true,
    truth: c.truth || '',
    keywords: c.keywords || [],
    expect_type_set: c.expect_type_set || [],
    literature_baseline: c.literature_baseline || null,
  };
}

export function loadCauseTable() {
  return readJson(CAUSES_FILE());
}

export function loadBrief(caseId) {
  const f = path.join(BRIEFS_DIR(), `${caseId}.brief.json`);
  if (!exists(f)) return null;
  return readJson(f);
}

export function loadArchivedAnswers() {
  const dir = ARCHIVED_ANSWERS();
  if (!exists(dir)) return {};
  const out = {};
  for (const f of fs.readdirSync(dir)) {
    if (!f.endsWith('.json')) continue;
    const key = f.replace(/\.json$/, '');
    const dot = key.lastIndexOf('.');
    const caseId = key.slice(0, dot);
    const regime = key.slice(dot + 1);
    out[caseId] = out[caseId] || {};
    out[caseId][regime] = readJson(path.join(dir, f));
  }
  return out;
}

export function listCaseIds() {
  return loadCasesRaw().map((c) => c.case_id);
}
