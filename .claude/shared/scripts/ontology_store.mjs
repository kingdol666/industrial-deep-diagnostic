#!/usr/bin/env node
// Ontology Store — 项目级本体资产管理（指纹 / 注册 / 复用 / 增量）。
//
// 设计目标：同一数据场景（列 schema 相同）的本体只构建一次，后续运行
// reuse（秒级拷贝 + CP-2 校验）或 extend（仅对新增列做增量构建）。
//
// 双模式：
//   CLI:    node ontology_store.mjs fingerprint|find|publish|reuse|stats|deprecate ...
//   import: import { computeFingerprint, findMatch, publish, reuse } from './ontology_store.mjs'
//
// 零依赖（对齐 validate.mjs 风格）；存储于 <PROJECT_ROOT>/data/ontology_store/。

import { createHash } from 'crypto';
import { spawnSync } from 'child_process';
import { existsSync, mkdirSync, readFileSync, writeFileSync, renameSync, copyFileSync, statSync, readdirSync, unlinkSync, rmdirSync, openSync, closeSync, readSync, writeSync } from 'fs';
import { join, dirname, resolve, basename, extname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
export const PROJECT_ROOT = resolve(__dirname, '..', '..', '..');
// Ontology-first Phase 1 (DOE): the store root is overridable via
// ONTOLOGY_STORE_DIR so `doe_ontology_prepare.py --store-dir <dir>` (and tests)
// can run against an isolated store without touching the project default.
// Unset → byte-identical legacy behaviour.
export const STORE_DIR = process.env.ONTOLOGY_STORE_DIR
  ? resolve(process.env.ONTOLOGY_STORE_DIR)
  : join(PROJECT_ROOT, 'data', 'ontology_store');
export const INDEX_PATH = join(STORE_DIR, 'index.json');
export const STORE_INDEX_VERSION = 1;
const MAX_VERSIONS_PER_SCENE = 10;

// Ontology profiles (P1-2): `diagnosis` is the legacy diagnosis pipeline
// profile; `doe` is the designed-experiment profile; `stability` / `sentinel`
// are the watch-family profiles (line stability report / data sentinel).
// Legacy index entries without a `profile` field are read as `diagnosis` —
// never re-written.
export const DEFAULT_PROFILE = 'diagnosis';
export const KNOWN_PROFILES = ['diagnosis', 'doe', 'stability', 'sentinel'];

/** Read an index entry's profile (legacy entries default to diagnosis). */
export function entryProfile(entry) {
  const p = entry && typeof entry.profile === 'string' ? entry.profile.trim() : '';
  return p || DEFAULT_PROFILE;
}

function normalizeProfile(profile) {
  const p = typeof profile === 'string' ? profile.trim() : '';
  return p || DEFAULT_PROFILE;
}

// ────────────────────────── 并发写锁 ──────────────────────────

// 后端长驻进程与 CLI 子进程共用同一 store：所有 read-modify-write 必须在
// 进程间串行，否则会互覆版本目录 / 丢 index entry。锁文件用 `wx` 独占创建，
// 内容只是诊断信息（pid + 时间）；进程崩溃留下的锁按 mtime 判陈旧。
const LOCK_PATH = join(STORE_DIR, '.lock');
const LOCK_RETRY_MS = 50;
// 同进程重入标记：publish → addVersion 会再次请求写锁，直接复用外层临界区
// （否则自锁死等）。
let storeLockHeld = false;

function sleepSync(ms) {
  Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms);
}

/**
 * Run `fn` inside the store's cross-process write lock.
 *
 * The lock is `<STORE_DIR>/.lock`, acquired with `openSync(..., 'wx')` (pid +
 * timestamp written inside). A waiter retries every 50ms until `timeoutMs`; a
 * lock file whose mtime is older than `staleMs` is treated as abandoned and
 * removed before re-attempting. Re-entrant within one process (module-level
 * marker) so nested public entry points never deadlock on themselves.
 * Read-only paths intentionally do NOT take this lock.
 */
export function withStoreLock(fn, { timeoutMs = 15000, staleMs = 30000 } = {}) {
  if (storeLockHeld) return fn();
  mkdirSync(STORE_DIR, { recursive: true });
  const deadline = Date.now() + timeoutMs;
  for (;;) {
    if (Date.now() >= deadline) {
      throw new Error(`ontology store lock timeout after ${timeoutMs}ms — lock file: ${LOCK_PATH}`);
    }
    try {
      const fd = openSync(LOCK_PATH, 'wx');
      try {
        writeSync(fd, JSON.stringify({ pid: process.pid, acquired_at: new Date().toISOString() }));
      } finally {
        closeSync(fd);
      }
      break;
    } catch (err) {
      if (err.code !== 'EEXIST') throw err;
      let stale = false;
      try {
        stale = Date.now() - statSync(LOCK_PATH).mtimeMs > staleMs;
      } catch { /* lock vanished between open and stat — retry immediately */ }
      if (stale) {
        try { unlinkSync(LOCK_PATH); } catch { /* another waiter won the race */ }
        continue;
      }
      sleepSync(LOCK_RETRY_MS);
    }
  }
  storeLockHeld = true;
  try {
    return fn();
  } finally {
    storeLockHeld = false;
    try { unlinkSync(LOCK_PATH); } catch { /* already removed */ }
  }
}

// CP-2 判据所用的唯一 schema（skill 协议 / 快路径 / 管理 API 三者必须同源）
export const ONTOLOGY_SCHEMA_PATH = join(
  PROJECT_ROOT, '.claude', 'skills', 'industrial-ontology-builder', 'schemas', 'ontology_schema.json',
);
// CP-2 下限：≥1KB
export const ONTOLOGY_MIN_BYTES = 1024;

// ────────────────────────── CSV 探测 ──────────────────────────

// 最小 CSV 头解析：支持引号包裹的逗号（双引号转义）。只解析表头 + 采样行。
function parseCsvLines(text, maxRows) {
  const rows = [];
  let row = [];
  let field = '';
  let inQuotes = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (inQuotes) {
      if (ch === '"') {
        if (text[i + 1] === '"') { field += '"'; i++; }
        else inQuotes = false;
      } else field += ch;
    } else if (ch === '"') {
      inQuotes = true;
    } else if (ch === ',') {
      row.push(field); field = '';
      if (maxRows && rows.length >= maxRows) break;
    } else if (ch === '\n' || ch === '\r') {
      if (ch === '\r' && text[i + 1] === '\n') i++;
      row.push(field); field = '';
      rows.push(row); row = [];
      if (maxRows && rows.length >= maxRows) break;
      // 跳过行首多余的连续换行
    } else {
      field += ch;
    }
  }
  if (!maxRows || rows.length < maxRows) {
    if (field !== '' || row.length > 0) { row.push(field); rows.push(row); }
  }
  return rows.filter(r => r.length > 1 || (r[0] || '').trim() !== '');
}

function inferType(values) {
  let sawNumber = 0, sawBool = 0, sawDate = 0, sawEmpty = 0, total = 0;
  const DATE_RE = /^\d{4}[-/]\d{1,2}[-/]\d{1,2}([ T]\d{2}:\d{2}(:\d{2})?)?$/;
  for (const raw of values) {
    const v = (raw ?? '').trim();
    if (v === '') { sawEmpty++; total++; continue; }
    total++;
    if (v !== '' && !isNaN(Number(v))) sawNumber++;
    else if (/^(true|false|yes|no|y|n)$/i.test(v)) sawBool++;
    else if (DATE_RE.test(v)) sawDate++;
  }
  const nonEmpty = Math.max(1, total - sawEmpty);
  if (sawNumber / nonEmpty >= 0.9) return 'number';
  if (sawDate / nonEmpty >= 0.9) return 'datetime';
  if (sawBool / nonEmpty >= 0.9) return 'boolean';
  return 'string';
}

/**
 * 计算数据文件（或数据文件夹）指纹。
 * 目录模式：取目录内最大的 CSV/TSV 做列指纹，文件名清单参与内容哈希。
 * @returns {{schema_fp, content_fp, columns: [{column,dtype,position}], row_sampled, file_size}}
 */
export function computeFingerprint(dataPath) {
  const abs = resolve(dataPath.startsWith('.') || !dataPath.match(/^([A-Za-z]:|\/|\\)/) ? join(PROJECT_ROOT, dataPath) : dataPath);
  if (!existsSync(abs)) throw new Error(`Data file not found: ${abs}`);
  if (statSync(abs).isDirectory()) return computeDirFingerprint(abs);
  return fingerprintFile(abs);
}

const DATA_EXTS = ['.csv', '.tsv'];
// Input guards: fingerprints only ever read a bounded head; a file beyond the
// hard cap is refused with an actionable error instead of being slurped.
const MAX_INPUT_BYTES = 200 * 1024 * 1024;     // 200MB hard input cap
const SAMPLE_BYTES = 2 * 1024 * 1024;          // 2MB streaming head sample
const HEAD_CHUNK_BYTES = 256 * 1024;

function assertInputSize(abs, size) {
  if (size > MAX_INPUT_BYTES) {
    throw new Error(`DATA_TOO_LARGE: ${abs} is ${size} bytes (>200MB); `
      + `fingerprint samples at most the first ${SAMPLE_BYTES} bytes — split the file`);
  }
}

/** Read at most SAMPLE_BYTES from the head of `abs` in fixed-size chunks. */
function readHeadBytes(abs, size) {
  const limit = Math.min(size, SAMPLE_BYTES);
  const fd = openSync(abs, 'r');
  try {
    const chunks = [];
    let read = 0;
    while (read < limit) {
      const buf = Buffer.allocUnsafe(Math.min(HEAD_CHUNK_BYTES, limit - read));
      const n = readSync(fd, buf, 0, buf.length, read);
      if (n <= 0) break;
      chunks.push(buf.subarray(0, n));
      read += n;
    }
    return Buffer.concat(chunks, read);
  } finally {
    closeSync(fd);
  }
}

function computeDirFingerprint(dir) {
  const files = readdirSync(dir)
    .filter(f => DATA_EXTS.includes(extname(f).toLowerCase()))
    .sort();
  if (files.length === 0) throw new Error(`No csv/tsv data file inside directory: ${dir}`);
  let best = null, bestSize = -1;
  for (const f of files) {
    const full = join(dir, f);
    const size = statSync(full).size;
    if (size > bestSize) { bestSize = size; best = full; }
  }
  assertInputSize(best, bestSize);
  const fp = fingerprintFile(best);
  // 目录指纹：文件清单参与哈希（同最大文件但清单不同 → 视为不同数据集）
  const listHash = createHash('sha256').update(files.join('|')).digest('hex');
  fp.content_fp = 'sha256:' + createHash('sha256')
    .update(fp.content_fp)
    .update(listHash)
    .digest('hex');
  fp.fingerprinted_file = best;
  fp.files_in_dir = files;
  return fp;
}

function fingerprintFile(abs) {
  const stat = statSync(abs);
  const size = stat.size;
  assertInputSize(abs, size);
  // 2MB 头部采样足以取表头与类型样本；流式分块读，绝不整文件读入。
  const head = readHeadBytes(abs, size).toString('utf-8');
  const rows = parseCsvLines(head, 501);
  if (rows.length === 0) throw new Error(`Empty or unparsable CSV: ${abs}`);
  const header = rows[0].map(h => h.trim());
  const sample = rows.slice(1, 501);
  const columns = header.map((column, position) => ({
    column,
    dtype: inferType(sample.map(r => r[position])),
    position,
  }));
  const schema_fp = 'sha256:' + createHash('sha256')
    .update(JSON.stringify(columns))
    .digest('hex');
  // 内容指纹：文件大小 + 头部内容哈希（同 schema 不同批次的检测提示，非精确）
  const content_fp = 'sha256:' + createHash('sha256')
    .update(String(size))
    .update(head.slice(0, 64 * 1024))
    .digest('hex');
  return { schema_fp, content_fp, columns, row_sampled: sample.length, file_size: size };
}

// ────────────────────────── DOE context 指纹 ──────────────────────────

/**
 * `context_fp` (P1-2 / contracts §9) — the semantic identity of a DOE analysis
 * context: sorted factor columns + declared ranges + units + response columns
 * + specs (lsl/usl/target/goal) + design type.
 *
 * Determinism contract: no dict-iteration-order dependence (every line set is
 * sorted), no wall clock, and the canonical number formatter below is mirrored
 * 1:1 by `canonical_number_token()` / `_context_fp()` in doe_ontology_prepare.py
 * so the Python and JS sides produce the SAME fingerprint for the same context.
 * A cross-language equality test pins this (tests/test_ontology_phase1.py).
 */
export const CONTEXT_FP_VERSION = 'doe-context-v1';
const CONTEXT_FP_ABS_CUTOFF = 1e15; // beyond this, toFixed()/f-string diverge

/** Canonical decimal token for ranges/specs ('' for absent, never 'null'). */
export function canonicalNumberToken(value) {
  if (value === null || value === undefined || value === '') return '';
  if (typeof value === 'boolean') return String(value);
  const n = Number(value);
  if (!Number.isFinite(n)) return String(value);
  if (Math.abs(n) >= CONTEXT_FP_ABS_CUTOFF) return String(n);
  let s = n.toFixed(9);
  if (s.indexOf('.') >= 0) s = s.replace(/0+$/, '').replace(/\.$/, '');
  if (s === '' || s === '-0') s = '0';
  return s;
}

function levelsToken(levels) {
  if (levels === null || levels === undefined || levels === '') return '';
  if (Array.isArray(levels)) return levels.map((v) => String(v)).join(',');
  return String(levels);
}

/**
 * Compute the stable DOE context fingerprint.
 * @param {object} ctx analysis_context-shaped object (factors/responses/design type)
 * @returns {string} `sha256:<hex>`
 */
export function computeContextFingerprint(ctx) {
  const factors = Array.isArray(ctx?.factors) ? ctx.factors : [];
  const responses = Array.isArray(ctx?.responses) ? ctx.responses : [];
  const factorLines = factors
    .map((f) => [
      'F',
      f?.col ?? f?.name ?? '',
      f?.type ?? '',
      f?.unit ?? '',
      canonicalNumberToken(f?.min),
      canonicalNumberToken(f?.max),
      levelsToken(f?.levels),
    ].join('|'))
    .sort();
  const responseLines = responses
    .map((r) => [
      'R',
      r?.col ?? r?.name ?? '',
      r?.unit ?? '',
      r?.goal ?? '',
      canonicalNumberToken(r?.lsl),
      canonicalNumberToken(r?.usl),
      canonicalNumberToken(r?.target),
    ].join('|'))
    .sort();
  const designType = ctx?.design_type_declared ?? ctx?.design_type
    ?? ctx?.design_region?.design_hull ?? '';
  const payload = [
    `v=${CONTEXT_FP_VERSION}`,
    `D|${designType === null || designType === undefined ? '' : String(designType)}`,
    ...factorLines,
    ...responseLines,
  ].join('\n');
  return 'sha256:' + createHash('sha256').update(payload, 'utf-8').digest('hex');
}

/**
 * Watch-family context fingerprint (`stability` / `sentinel` profiles) — the
 * semantic identity of a declared column contract: per-column role + unit +
 * declared spec band, plus optional declared operating windows.
 *
 * Mirrored 1:1 by `compute_watch_context_fp()` in
 * `.claude/shared/scripts/ontology_prepare_common.py`; a cross-language
 * equality test pins this (test_ontology_prepare_common.py).
 */
export const WATCH_CONTEXT_FP_VERSION = 'watch-context-v1';

export function computeWatchContextFingerprint(decl) {
  const cols = Array.isArray(decl?.columns) ? decl.columns : [];
  const wins = Array.isArray(decl?.windows) ? decl.windows : [];
  const colLines = cols
    .map((c) => [
      'C',
      c?.col ?? c?.name ?? '',
      c?.role ?? '',
      c?.unit ?? '',
      canonicalNumberToken(c?.lsl),
      canonicalNumberToken(c?.usl),
    ].join('|'))
    .sort();
  const winLines = wins
    .map((w) => [
      'W',
      w?.factor ?? w?.col ?? '',
      canonicalNumberToken(w?.lo),
      canonicalNumberToken(w?.hi),
    ].join('|'))
    .sort();
  const payload = [
    `v=${WATCH_CONTEXT_FP_VERSION}`,
    ...colLines,
    ...winLines,
  ].join('\n');
  return 'sha256:' + createHash('sha256').update(payload, 'utf-8').digest('hex');
}

// ────────────────────────── 注册表 ──────────────────────────

export function readIndex() {
  if (!existsSync(INDEX_PATH)) return { version: STORE_INDEX_VERSION, entries: [] };
  try {
    const idx = JSON.parse(readFileSync(INDEX_PATH, 'utf-8'));
    if (!Array.isArray(idx.entries)) return { version: STORE_INDEX_VERSION, entries: [] };
    return idx;
  } catch {
    return { version: STORE_INDEX_VERSION, entries: [] };
  }
}

export function writeIndex(idx) {
  mkdirSync(STORE_DIR, { recursive: true });
  const tmp = INDEX_PATH + '.tmp';
  writeFileSync(tmp, JSON.stringify(idx, null, 2));
  renameSync(tmp, INDEX_PATH);
}

export function listStore() {
  return readIndex();
}

/**
 * 查找可复用本体。
 *
 * P1-2 additions (all additive — the legacy diagnosis call keeps its exact
 * behaviour when no `profile`/`contextFp` is passed):
 *   - `profile` (default null → `diagnosis`): entries are matched only inside
 *     the same profile — a diagnosis lookup can never return a DOE asset and
 *     vice versa (OD-08).
 *   - `scene` + `profile` + `contextFp`: semantic DOE lookup. `profile+scene+
 *     context_fp` equal → `exact`; same scene with a different `context_fp` →
 *     `extend` (the scene_only path); otherwise `miss`. The data-schema
 *     fingerprint is not required in that mode, so a design-only run (no run
 *     table yet) can still hit.
 * @returns {{match:'exact'|'extend'|'miss', scene_key?, version?, ontology_path?, provenance_path?, reason?}}
 */
export function findMatch(dataPath, { scene, profile = null, contextFp = null } = {}) {
  const wantProfile = normalizeProfile(profile);
  const wantContextFp = typeof contextFp === 'string' && contextFp.trim() !== '' ? contextFp : null;
  // Semantic (DOE) mode: profile-scoped lookup by context fingerprint, with no
  // dependence on a data file existing yet.
  const semantic = wantProfile !== DEFAULT_PROFILE && wantContextFp !== null;
  const hasDataPath = typeof dataPath === 'string' && dataPath.trim() !== '';
  if (!hasDataPath && !semantic) {
    throw new Error('findMatch requires either a dataPath or profile+contextFp');
  }
  const fp = hasDataPath ? computeFingerprint(dataPath) : null;
  const idx = readIndex();
  const scoped = idx.entries
    .filter((e) => e.quality !== 'deprecated')
    .filter((e) => entryProfile(e) === wantProfile);
  const sceneScoped = scene ? scoped.filter((e) => e.scene_key === scene) : scoped;

  if (semantic) {
    const candidates = sceneScoped
      .filter((e) => (e.context_fp || null) === wantContextFp)
      .sort((a, b) => b.version - a.version);
    if (candidates.length > 0) {
      const best = candidates[0];
      return {
        match: 'exact',
        profile: wantProfile,
        scene_key: best.scene_key,
        version: best.version,
        context_fp: wantContextFp,
        ontology_path: join(STORE_DIR, best.path),
        provenance_path: join(STORE_DIR, dirname(best.path), 'provenance.json'),
        quality: best.quality,
        reuse_count: best.reuse_count || 0,
        content_match: fp ? best.content_fp === fp.content_fp : true,
        schema_fp: fp?.schema_fp ?? null,
        reason: 'profile+scene+context_fp match',
      };
    }
    if (sceneScoped.length > 0) {
      const best = sceneScoped.sort((a, b) => b.version - a.version)[0];
      return {
        match: 'extend',
        profile: wantProfile,
        scene_key: best.scene_key,
        version: best.version,
        context_fp: wantContextFp,
        stored_context_fp: best.context_fp || null,
        ontology_path: join(STORE_DIR, best.path),
        provenance_path: join(STORE_DIR, dirname(best.path), 'provenance.json'),
        schema_fp: fp?.schema_fp ?? null,
        reason: 'scene exists but context_fp differs — extend the stored ontology '
          + '(new columns / ranges / units / specs); exact reuse is not allowed',
      };
    }
    return {
      match: 'miss',
      profile: wantProfile,
      context_fp: wantContextFp,
      schema_fp: fp?.schema_fp ?? null,
      reason: 'no compatible ontology in store',
    };
  }

  const candidates = sceneScoped
    .filter((e) => e.schema_fp === fp.schema_fp)
    .sort((a, b) => b.version - a.version);
  if (candidates.length > 0) {
    const best = candidates[0];
    const contentMatch = best.content_fp === fp.content_fp;
    return {
      match: 'exact',
      scene_key: best.scene_key,
      version: best.version,
      ontology_path: join(STORE_DIR, best.path),
      provenance_path: join(STORE_DIR, dirname(best.path), 'provenance.json'),
      quality: best.quality,
      reuse_count: best.reuse_count || 0,
      content_match: contentMatch,
      schema_fp: fp.schema_fp,
      reason: contentMatch ? 'schema+content match' : 'schema match (content drifted — extend check advised)',
    };
  }
  // schema 未命中 → 若同 scene 存在近似 schema（列集合有交集），建议 extend
  if (scene) {
    const sceneEntries = sceneScoped;
    if (sceneEntries.length > 0) {
      const best = sceneEntries.slice().sort((a, b) => b.version - a.version)[0];
      return {
        match: 'extend',
        scene_key: best.scene_key,
        version: best.version,
        ontology_path: join(STORE_DIR, best.path),
        provenance_path: join(STORE_DIR, dirname(best.path), 'provenance.json'),
        schema_fp: fp.schema_fp,
        reason: 'scene exists but schema differs — incremental extend on new columns',
      };
    }
  }
  return { match: 'miss', schema_fp: fp.schema_fp, reason: 'no compatible ontology in store' };
}

// Version namespace (profile-scoped since 2026-10-21): the legacy layout
// `<scene>/vN` stays reserved for the default (diagnosis) profile — its next
// version number must therefore skip over ANY entry already living in that
// namespace, regardless of that entry's profile (legacy DOE assets share it).
// Non-default profiles publish to `<scene>/<profile>/vN`, and version
// numbering + pruning are scoped to (profile, scene) so a stability publish
// can never crowd out or delete a diagnosis/doe asset of the same scene.
function entryNamespace(entry) {
  const parts = String(entry?.path || '').split('/');
  // legacy shape: `<scene>/vN/ontology.json`; profile shape: `<scene>/<profile>/vN/ontology.json`
  if (parts.length === 3 && /^v\d+$/.test(parts[1])) return 'legacy';
  return parts.length >= 4 ? parts[1] : 'legacy';
}

function versionScopeEntries(idx, sceneKey, profile) {
  return idx.entries.filter((e) => {
    if (e.scene_key !== sceneKey) return false;
    if (profile === DEFAULT_PROFILE) return entryNamespace(e) === 'legacy';
    return entryProfile(e) === profile;
  });
}

function nextVersion(idx, sceneKey, profile = DEFAULT_PROFILE) {
  const max = versionScopeEntries(idx, sceneKey, profile)
    .reduce((m, e) => Math.max(m, e.version), 0);
  return max + 1;
}

function versionRelDir(sceneKey, version, profile) {
  if (profile === DEFAULT_PROFILE) return join(sceneKey, `v${version}`);
  return join(sceneKey, profile, `v${version}`);
}

function pruneVersions(idx, sceneKey, profile = DEFAULT_PROFILE) {
  const keep = new Set(['endorsed']);
  const entries = versionScopeEntries(idx, sceneKey, profile)
    .sort((a, b) => b.version - a.version);
  const live = entries.filter((e) => keep.has(e.quality));
  const removable = entries.filter((e) => !keep.has(e.quality)).slice(MAX_VERSIONS_PER_SCENE);
  for (const e of removable) {
    try {
      const dir = dirname(join(STORE_DIR, e.path));
      if (existsSync(dir)) rmRf(dir);
    } catch { /* ignore */ }
  }
  idx.entries = idx.entries.filter(e => !removable.includes(e));
  void live;
}

function rmRf(dir) {
  for (const entry of readdirSync(dir)) {
    const p = join(dir, entry);
    if (statSync(p).isDirectory()) rmRf(p);
    else { try { unlinkSync(p); } catch { /* ignore */ } }
  }
  try { rmdirSync(dir); } catch { /* ignore */ }
}

// ────────────────────────── 版本写入原语（publish / 在线编辑共用） ──────────────────────────

/** 本体结构摘要 —— 让列表页 O(1) 读取索引即可展示规模，无需逐个读 ontology.json。 */
export function summarizeOntology(ontology) {
  if (!ontology || typeof ontology !== 'object') return null;
  const arr = (v) => (Array.isArray(v) ? v.length : 0);
  const signals = ontology.signals || {};
  const rels = Array.isArray(ontology.relationships) ? ontology.relationships : [];
  const byRole = {};
  for (const key of ['inspection_signals', 'process_parameters', 'control_variables', 'events', 'metadata_columns']) {
    for (const s of Array.isArray(signals[key]) ? signals[key] : []) {
      const role = s?.role || key;
      byRole[role] = (byRole[role] || 0) + 1;
    }
  }
  const byRelType = {};
  for (const r of rels) {
    const type = r?.type || 'unspecified';
    byRelType[type] = (byRelType[type] || 0) + 1;
  }
  const confidences = {};
  for (const key of ['inspection_signals', 'process_parameters', 'control_variables']) {
    for (const s of Array.isArray(signals[key]) ? signals[key] : []) {
      const c = s?.physical_meaning_confidence || 'UNKNOWN';
      confidences[c] = (confidences[c] || 0) + 1;
    }
  }
  return {
    title: ontology?.scene?.name || null,
    process_type: ontology?.scene?.process_type || null,
    ontology_version: ontology?.ontology_version || null,
    equipment: arr(ontology?.scene?.equipment),
    stages: arr(ontology?.scene?.stages),
    objectives: arr(ontology?.scene?.objectives),
    signals: arr(signals.inspection_signals) + arr(signals.process_parameters)
      + arr(signals.control_variables) + arr(signals.events) + arr(signals.metadata_columns),
    signals_by_role: byRole,
    relationships: rels.length,
    relationships_by_type: byRelType,
    confounders: arr(ontology?.confounders),
    parameter_groups: ontology?.parameter_groups && typeof ontology.parameter_groups === 'object'
      ? Object.keys(ontology.parameter_groups).length : 0,
    physical_principles: arr(ontology?.physical_principles),
    known_failure_modes: arr(ontology?.known_failure_modes),
    discrepancy_signals: arr(ontology?.discrepancy_signals),
    excluded_columns: arr(ontology?.excluded_columns),
    semantic_confidence: confidences,
  };
}

/** 归一化本体输入：接受对象 / JSON 字符串 → {content, parsed}。 */
function normalizeOntologyInput(ontology) {
  let parsed;
  let content;
  if (typeof ontology === 'string') {
    content = ontology;
    parsed = JSON.parse(content);
  } else if (ontology && typeof ontology === 'object') {
    parsed = ontology;
    content = JSON.stringify(ontology, null, 2);
  } else {
    throw new Error('ontology payload must be a JSON object or string');
  }
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new Error('ontology payload must be a JSON object');
  }
  return { content, parsed };
}

function contentHashOf(content) {
  return 'sha256:' + createHash('sha256').update(content).digest('hex');
}

/**
 * 写入一个新的本体版本（唯一写入口 —— 保证 index 不变量）。
 *
 * dedup：同 scene 下内容哈希完全一致 → 复用既有版本并返回 `deduped: true`
 * （在线编辑器保存未改动的草稿时不会产生噪声版本）。
 *
 * P1-2 additions (additive): `profile` / `contextFp` / `dataStage` land on the
 * index entry; dedupe is scoped to the same profile (a DOE ontology can never
 * collapse onto a diagnosis entry), and a deduped legacy entry backfills the
 * new fields so it stays findable by the semantic lookup.
 *
 * The whole read-modify-write (dedupe probe → nextVersion → version dir →
 * index) runs inside withStoreLock; publish() delegates here and relies on the
 * re-entrant marker instead of taking a second lock.
 *
 * @returns {{scene_key, version, path, deduped?, summary}}
 */
export function addVersion(options) {
  return withStoreLock(() => addVersionUnlocked(options));
}

function addVersionUnlocked({
  sceneKey,
  ontology,
  buildMode = 'edit',
  quality = 'unvalidated',
  title = null,
  tags = [],
  notes = '',
  origin = 'user',
  parentVersion = null,
  inheritFrom = null,
  provenance = {},
  dataFile = null,
  runDir = null,
  updatedAt = null,
  profile = DEFAULT_PROFILE,
  contextFp = null,
  dataStage = null,
}) {
  const key = String(sceneKey || '').trim();
  if (!key || !/^[A-Za-z0-9._-]+$/.test(key)) {
    throw new Error(`invalid scene_key: ${JSON.stringify(sceneKey)} (allowed: A-Za-z0-9._-)`);
  }
  const wantProfile = normalizeProfile(profile);
  const wantContextFp = typeof contextFp === 'string' && contextFp.trim() !== '' ? contextFp.trim() : null;
  const { content, parsed } = normalizeOntologyInput(ontology);
  if (Buffer.byteLength(content, 'utf-8') < ONTOLOGY_MIN_BYTES) {
    throw new Error(`ontology too small (${Buffer.byteLength(content, 'utf-8')}B < ${ONTOLOGY_MIN_BYTES}B CP-2 floor)`);
  }

  const idx = readIndex();
  const hash = contentHashOf(content);
  const deduped = idx.entries.find((e) => {
    if (e.scene_key !== key) return false;
    if (entryProfile(e) !== wantProfile) return false;
    try {
      const p = join(STORE_DIR, e.path);
      return existsSync(p) && contentHashOf(readFileSync(p, 'utf-8')) === hash;
    } catch { return false; }
  });
  if (deduped) {
    // 指纹回填：旧条目可能在 dataFile 缺失时代入库（schema_fp=null），dedupe
    // 复用版本时若本次带 dataFile 则就地补算——否则该条目永远无法被
    // fast-reuse 命中（2026-10-13 fieldtest 实测）。
    let backfilled = false;
    if (!deduped.schema_fp && dataFile) {
      try {
        const fp = computeFingerprint(dataFile);
        deduped.schema_fp = fp.schema_fp;
        deduped.content_fp = fp.content_fp;
        deduped.fingerprinted_from = resolve(dataFile);
        deduped.fingerprinted_at = new Date().toISOString();
        backfilled = true;
      } catch { /* 指纹算不出就保持 null：publish 照常去重，reuse 继续 miss */ }
    }
    // P1-2 同样的回填契约：缺失 profile/context_fp 的旧条目按诊断缺省读取，
    // 一旦本次携带 DOE 语义指纹就补写 —— 否则该场景永远无法被 exact 命中。
    if (wantProfile !== DEFAULT_PROFILE && wantContextFp && (deduped.context_fp || null) !== wantContextFp) {
      if (!deduped.profile) { deduped.profile = wantProfile; backfilled = true; }
      if (!deduped.context_fp) { deduped.context_fp = wantContextFp; backfilled = true; }
      if (dataStage && !deduped.data_stage) { deduped.data_stage = dataStage; backfilled = true; }
      deduped.scene_key = deduped.scene_key || key;
    }
    if (backfilled) writeIndex(idx);
    return {
      scene_key: key, version: deduped.version, path: join(STORE_DIR, deduped.path),
      deduped: true, schema_fp: deduped.schema_fp || null,
      profile: entryProfile(deduped), context_fp: deduped.context_fp || null,
      summary: deduped.summary || summarizeOntology(parsed),
    };
  }

  const version = nextVersion(idx, key, wantProfile);
  const relDir = versionRelDir(key, version, wantProfile);
  const absDir = join(STORE_DIR, relDir);
  mkdirSync(absDir, { recursive: true });
  const absOntologyPath = join(absDir, 'ontology.json');
  writeFileSync(absOntologyPath, content);
  // 写入后回读校验 UTF-8 往返无损（避免编码损伤静默入库）
  JSON.parse(readFileSync(absOntologyPath, 'utf-8'));
  // schema.json 边车（若来源 run 生成过）随本体同版本入库，供 reuse 对齐产物
  if (runDir) {
    const sidecar = join(resolve(runDir), '01_ontology', 'schema.json');
    if (existsSync(sidecar)) copyFileSync(sidecar, join(absDir, 'schema.json'));
  }

  const now = updatedAt || new Date().toISOString();
  const entry = {
    scene_key: key,
    profile: wantProfile,
    context_fp: wantContextFp,
    data_stage: dataStage || null,
    version,
    schema_fp: inheritFrom?.schema_fp ?? null,
    content_fp: inheritFrom?.content_fp ?? null,
    fingerprinted_from: inheritFrom?.fingerprinted_from ?? null,
    build_mode: buildMode,
    origin,
    parent_version: parentVersion,
    built_from_run: provenance.built_from_run ?? inheritFrom?.built_from_run ?? null,
    title: title || parsed?.scene?.name || key,
    tags: Array.isArray(tags) ? tags.filter((t) => typeof t === 'string' && t.trim()).map((t) => t.trim()) : [],
    notes: typeof notes === 'string' ? notes : '',
    quality,
    created_at: now,
    updated_at: now,
    reuse_count: 0,
    content_sha256: hash,
    summary: summarizeOntology(parsed),
    path: relDir.split('\\').join('/') + '/ontology.json',
  };

  // 指纹补齐（保持 reuse 命中能力）：显式 dataFile > 继承 > run 目录推断
  if (dataFile) {
    try {
      const fp = computeFingerprint(dataFile);
      entry.schema_fp = fp.schema_fp;
      entry.content_fp = fp.content_fp;
      entry.fingerprinted_from = resolve(dataFile);
    } catch { /* keep inherited */ }
  }

  writeFileSync(join(absDir, 'provenance.json'), JSON.stringify({
    scene_key: key,
    profile: wantProfile,
    context_fp: wantContextFp,
    data_stage: dataStage || null,
    version,
    parent_version: parentVersion,
    origin,
    build_mode: buildMode,
    quality,
    built_from_run: entry.built_from_run,
    schema_fp: entry.schema_fp,
    content_sha256: entry.content_sha256,
    created_at: now,
    reuse_history: [],
    ...provenance,
  }, null, 2));

  idx.entries.push(entry);
  pruneVersions(idx, key, wantProfile);
  writeIndex(idx);
  return {
    scene_key: key, version, path: absOntologyPath, summary: entry.summary,
    profile: wantProfile, context_fp: wantContextFp,
  };
}

/**
 * 将 run 目录中通过 CP-2 的 ontology.json 发布入 store。
 * 委托 addVersion（唯一写入口）；指纹候选链：显式 dataFile > run_config.data_path
 * > input_manifest > 00_input 目录首个 csv/tsv。
 * P1-2: `profile`/`contextFp`/`dataStage` are forwarded to addVersion so a DOE
 * publish lands on the same index entry shape the semantic lookup reads.
 * @returns {{scene_key, version, path, schema_fp}}
 */
export function publish({
  runDir, scene, buildMode = 'full', quality = 'unvalidated', dataFile,
  profile = DEFAULT_PROFILE, contextFp = null, dataStage = null,
}) {
  const absRunDir = resolve(runDir);
  const ontologyPath = join(absRunDir, '01_ontology', 'ontology.json');
  if (!existsSync(ontologyPath)) throw new Error(`ontology.json not found under ${absRunDir}`);
  const content = readFileSync(ontologyPath, 'utf-8');
  if (Buffer.byteLength(content, 'utf-8') < ONTOLOGY_MIN_BYTES) {
    throw new Error(`ontology.json too small (${Buffer.byteLength(content, 'utf-8')}B < ${ONTOLOGY_MIN_BYTES}B CP-2 floor)`);
  }
  const parsed = JSON.parse(content); // must be valid JSON

  const manifestPath = join(absRunDir, 'run_manifest.json');
  let runId = basename(absRunDir);
  try {
    const manifest = JSON.parse(readFileSync(manifestPath, 'utf-8'));
    if (manifest.run_id) runId = manifest.run_id;
  } catch { /* ignore */ }

  // scene_key：显式指定 > 本体内 scene.name > run 目录名尾部
  let sceneKey = scene || parsed?.scene?.name || null;
  if (!sceneKey) {
    const m = basename(absRunDir).match(/_(\w+)$/);
    sceneKey = m ? m[1] : basename(absRunDir);
  }
  sceneKey = String(sceneKey).replace(/[^A-Za-z0-9._-]/g, '_');

  // 指纹候选链
  const candidateDataPaths = [];
  if (dataFile) candidateDataPaths.push(resolve(dataFile.startsWith('.') || !dataFile.match(/^([A-Za-z]:|\/|\\)/) ? join(PROJECT_ROOT, dataFile) : dataFile));
  try {
    const rcPath = join(absRunDir, '00_input', 'run_config.json');
    if (existsSync(rcPath)) {
      const rc = JSON.parse(readFileSync(rcPath, 'utf-8'));
      if (rc.data_path) candidateDataPaths.push(resolve(rc.data_path));
    }
  } catch { /* ignore */ }
  try {
    const inputManifestPath = join(absRunDir, '00_input', 'input_manifest.json');
    if (existsSync(inputManifestPath)) {
      const im = JSON.parse(readFileSync(inputManifestPath, 'utf-8'));
      const files = im.files || im.data_files || [];
      for (const f of Array.isArray(files) ? files : []) {
        const p = f?.path || f?.absolute_path || (typeof f === 'string' ? f : null);
        if (p) candidateDataPaths.push(resolve(p));
      }
    }
  } catch { /* ignore */ }
  try {
    const inputDir = join(absRunDir, '00_input');
    if (existsSync(inputDir)) {
      const dataExts = ['.csv', '.tsv', '.json', '.xlsx', '.parquet'];
      for (const f of readdirSync(inputDir)) {
        if (dataExts.includes(extname(f).toLowerCase())) candidateDataPaths.push(join(inputDir, f));
      }
    }
  } catch { /* ignore */ }

  const fps = [];
  for (const candidate of candidateDataPaths) {
    try {
      if (candidate && existsSync(candidate) && statSync(candidate).isFile() && /\.(csv|tsv)$/i.test(candidate)) {
        const fp = computeFingerprint(candidate);
        fps.push({ schema_fp: fp.schema_fp, content_fp: fp.content_fp, fingerprinted_from: candidate });
        break;
      }
    } catch { /* try next candidate */ }
  }

  const result = addVersion({
    sceneKey,
    ontology: content,
    buildMode,
    quality,
    origin: 'agent',
    provenance: { built_from_run: runId },
    inheritFrom: fps[0] || null,
    // 指纹传递契约：publish 必须把已指纹化的数据文件交给 addVersion ——
    // dedupe 复用旧版本时 addVersion 靠它回填 schema_fp，否则条目永远
    // schema_fp=null、fast-reuse 永不命中（2026-10-13 fieldtest 实测）。
    dataFile: fps[0]?.fingerprinted_from || dataFile || null,
    runDir: absRunDir,
    profile,
    contextFp,
    dataStage,
  });
  return {
    scene_key: result.scene_key,
    version: result.version,
    path: result.path,
    schema_fp: fps[0]?.schema_fp ?? null,
    profile: result.profile,
    context_fp: result.context_fp ?? null,
    ...(result.deduped ? { deduped: true } : {}),
  };
}

/**
 * 复用：拷贝 store 本体到 run 目录并写 pipeline 事件。
 */
export function reuse({ source, runDir }) {
  const src = resolve(source);
  if (!existsSync(src)) throw new Error(`Source ontology not found: ${src}`);
  const absRunDir = resolve(runDir);
  const ontologyDir = join(absRunDir, '01_ontology');
  mkdirSync(ontologyDir, { recursive: true });
  const dst = join(ontologyDir, 'ontology.json');
  copyFileSync(src, dst);
  // schema.json 边车与本体同源发布——复用时一并带上，保证 reuse 与 full 构建
  // 的 01_ontology/ 产物对齐（finalizer 把它列为 critical 工件）。
  const sidecarSrc = join(dirname(src), 'schema.json');
  if (existsSync(sidecarSrc)) copyFileSync(sidecarSrc, join(ontologyDir, 'schema.json'));

  // 更新 store 的 reuse 计数与 provenance 历史（读-改-写走写锁）
  withStoreLock(() => {
    const idx = readIndex();
    const entry = idx.entries.find(e => join(STORE_DIR, e.path) === src);
    if (!entry) return;
    entry.reuse_count = (entry.reuse_count || 0) + 1;
    const provPath = join(STORE_DIR, dirname(entry.path), 'provenance.json');
    try {
      const prov = JSON.parse(readFileSync(provPath, 'utf-8'));
      prov.reuse_history.push({ run_dir: basename(absRunDir), at: new Date().toISOString() });
      writeFileSync(provPath, JSON.stringify(prov, null, 2));
    } catch { /* ignore */ }
    writeIndex(idx);
  });
  return { copied_to: dst, bytes: statSync(dst).size };
}

export function deprecate(sceneKey, version) {
  return withStoreLock(() => {
    const idx = readIndex();
    const entry = idx.entries.find(e => e.scene_key === sceneKey && e.version === Number(version));
    if (!entry) throw new Error(`Entry not found: ${sceneKey} v${version}`);
    entry.quality = 'deprecated';
    entry.updated_at = new Date().toISOString();
    writeIndex(idx);
    return entry;
  });
}

// ────────────────────────── 资产管理原语（前端本体管理页 / 控制 API） ──────────────────────────

/** 按 scene+version 取索引条目（无则 null）。 */
export function getEntry(sceneKey, version) {
  return readIndex().entries.find(
    (e) => e.scene_key === sceneKey && e.version === Number(version),
  ) || null;
}

/** 列出某 scene 的全部版本（降序）。 */
export function listSceneVersions(sceneKey) {
  return readIndex().entries
    .filter((e) => e.scene_key === sceneKey)
    .sort((a, b) => b.version - a.version);
}

/**
 * 读取一个资产的完整内容：ontology + provenance + entry。
 * 若产物被外部删除（索引漂移），返回 `missing: true` 而不是抛错 —— 让列表页能如实展示坏条目。
 */
export function readAsset(sceneKey, version) {
  const entry = getEntry(sceneKey, version);
  if (!entry) return null;
  const absPath = join(STORE_DIR, entry.path);
  if (!existsSync(absPath)) return { entry, ontology: null, provenance: null, missing: true, absolute_path: absPath };
  const ontology = JSON.parse(readFileSync(absPath, 'utf-8'));
  let provenance = null;
  const provPath = join(STORE_DIR, dirname(entry.path), 'provenance.json');
  try { provenance = JSON.parse(readFileSync(provPath, 'utf-8')); } catch { /* optional */ }
  return {
    entry,
    ontology,
    provenance,
    missing: false,
    absolute_path: absPath,
    bytes: statSync(absPath).size,
  };
}

/** 元数据补丁（title/tags/notes/quality）——不产生新版本，仅改索引与 provenance。 */
export function updateEntry(sceneKey, version, patch = {}) {
  return withStoreLock(() => {
    const idx = readIndex();
    const entry = idx.entries.find((e) => e.scene_key === sceneKey && e.version === Number(version));
    if (!entry) throw new Error(`Entry not found: ${sceneKey} v${version}`);
    if (patch.title !== undefined) entry.title = String(patch.title || entry.scene_key);
    if (patch.tags !== undefined) {
      entry.tags = Array.isArray(patch.tags)
        ? patch.tags.filter((t) => typeof t === 'string' && t.trim()).map((t) => t.trim())
        : [];
    }
    if (patch.notes !== undefined) entry.notes = String(patch.notes || '');
    if (patch.quality !== undefined) {
      if (!['unvalidated', 'endorsed', 'deprecated', 'rejected'].includes(patch.quality)) {
        throw new Error(`invalid quality: ${patch.quality}`);
      }
      entry.quality = patch.quality;
    }
    // 场景重命名/重新打标 → 同步新版本号摘要标题
    entry.updated_at = new Date().toISOString();
    writeIndex(idx);
    try {
      const provPath = join(STORE_DIR, dirname(entry.path), 'provenance.json');
      if (existsSync(provPath)) {
        const prov = JSON.parse(readFileSync(provPath, 'utf-8'));
        prov.title = entry.title;
        prov.tags = entry.tags;
        prov.notes = entry.notes;
        prov.quality = entry.quality;
        prov.updated_at = entry.updated_at;
        writeFileSync(provPath, JSON.stringify(prov, null, 2));
      }
    } catch { /* provenance 是可选伴生文件 */ }
    return entry;
  });
}

/** 删除单个版本（索引 + 磁盘目录）；若场景目录随之变空，一并清除。 */
export function removeVersion(sceneKey, version, profile = null) {
  return withStoreLock(() => {
    const idx = readIndex();
    const v = Number(version);
    const candidates = idx.entries.filter((e) => e.scene_key === sceneKey && e.version === v);
    const entry = (profile
      ? candidates.find((e) => entryProfile(e) === normalizeProfile(profile))
      : (candidates.find((e) => entryNamespace(e) === 'legacy') || candidates[0]))
      || null;
    if (!entry) throw new Error(`Entry not found: ${sceneKey} v${v}`);
    const dir = dirname(join(STORE_DIR, entry.path));
    try { if (existsSync(dir)) rmRf(dir); } catch { /* ignore */ }
    idx.entries = idx.entries.filter((e) => e !== entry);
    writeIndex(idx);
    pruneEmptySceneDir(idx, sceneKey);
    return { removed: { scene_key: sceneKey, version: v } };
  });
}

/** 索引中已无该场景的版本 → 清理磁盘上残留的空目录（含孤立的 provenance）。 */
function pruneEmptySceneDir(idx, sceneKey) {
  if (idx.entries.some((e) => e.scene_key === sceneKey)) return;
  const dir = join(STORE_DIR, sceneKey);
  try {
    if (existsSync(dir) && readdirSync(dir).length === 0) rmdirSync(dir);
  } catch { /* ignore */ }
}

/** 删除整个场景（所有版本）。索引已空但磁盘有残留时，仍然清理并如实返回。 */
export function removeScene(sceneKey) {
  return withStoreLock(() => {
    const idx = readIndex();
    const doomed = idx.entries.filter((e) => e.scene_key === sceneKey);
    const dir = join(STORE_DIR, sceneKey);
    if (doomed.length === 0 && !existsSync(dir)) throw new Error(`Scene not found: ${sceneKey}`);
    idx.entries = idx.entries.filter((e) => e.scene_key !== sceneKey);
    writeIndex(idx);
    try { if (existsSync(dir)) rmRf(dir); } catch { /* ignore */ }
    return { removed_versions: doomed.map((e) => e.version).sort((a, b) => a - b) };
  });
}

/**
 * CP-2 校验（与 skill 协议、fast-reuse 同源）：
 *  1) ontology_schema.json draft-07 校验（spawn validate.mjs）
 *  2) 字节数 ≥ ONTOLOGY_MIN_BYTES
 * 接受磁盘路径或内存对象/字符串（内存载荷写入 store 内临时文件后校验，保证与落盘后一致）。
 * @returns {{ok, errors:[], warnings:[], report, bytes, schema}}
 */
export function validateOntology(payload, { schemaPath = ONTOLOGY_SCHEMA_PATH } = {}) {
  let target = null;
  let tmp = null;
  let bytes = 0;
  try {
    if (typeof payload === 'string' && existsSync(payload)) {
      target = resolve(payload);
      bytes = statSync(target).size;
    } else if (payload && typeof payload === 'object' && !Buffer.isBuffer(payload) && payload.__isPath !== true && typeof payload.path === 'string' && existsSync(payload.path)) {
      target = resolve(payload.path);
      bytes = statSync(target).size;
    } else {
      const { content } = normalizeOntologyInput(payload);
      bytes = Buffer.byteLength(content, 'utf-8');
      mkdirSync(STORE_DIR, { recursive: true });
      tmp = join(STORE_DIR, `.validate-${process.pid}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}.json`);
      writeFileSync(tmp, content);
      target = tmp;
    }

    const res = spawnSync(process.execPath, [VALIDATE_MJS, schemaPath, target], {
      encoding: 'utf-8', timeout: 30000, windowsHide: true,
    });
    let report = null;
    try { report = JSON.parse(res.stdout || 'null'); } catch { /* non-JSON output */ }
    const errors = [...(report?.errors || [])];
    const warnings = [...(report?.warnings || [])];
    if (res.status !== 0 && errors.length === 0) {
      errors.push({ path: '$', message: (res.stdout || res.stderr || `validate.mjs exit ${res.status}`).slice(-800), severity: 'error' });
    }
    if (bytes < ONTOLOGY_MIN_BYTES) {
      errors.push({ path: '$', message: `ontology ${bytes}B < ${ONTOLOGY_MIN_BYTES}B CP-2 floor`, severity: 'error' });
    }
    return {
      ok: errors.length === 0 && res.status === 0,
      errors,
      warnings,
      report,
      bytes,
      schema: schemaPath,
    };
  } finally {
    if (tmp) { try { unlinkSync(tmp); } catch { /* ignore */ } }
  }
}

/**
 * 复用推荐：给定数据路径/场景，返回 find 结果 + 该场景全部候选版本（供前端"选择复用版本"）。
 * 无数据路径时退化为「按场景列出全部资产」。
 *
 * P1-2: accepts `profile`/`contextFp`. When a lookup is actually possible
 * (dataPath given, or profile+scene+contextFp given) the result carries
 * `status` ∈ `exact` | `scene_only` | `miss` mapped from findMatch
 * (exact→exact, extend→scene_only, miss→miss); a pure listing returns
 * `status: null`. `candidates` stays unfiltered unless `profile` is given, so
 * the existing ontology management page keeps listing every scene.
 */
export function recommendReuse({ dataPath, scene, profile = null, contextFp = null } = {}) {
  const wantProfile = profile ? normalizeProfile(profile) : null;
  const idx = readIndex();
  const byScene = new Map();
  for (const e of idx.entries) {
    if (scene && e.scene_key !== scene) continue;
    if (wantProfile && entryProfile(e) !== wantProfile) continue;
    if (!byScene.has(e.scene_key)) byScene.set(e.scene_key, []);
    byScene.get(e.scene_key).push(e);
  }
  const candidates = [...byScene.entries()].map(([scene_key, entries]) => {
    entries.sort((a, b) => b.version - a.version);
    const latest = entries[0];
    return {
      scene_key,
      profile: entryProfile(latest),
      context_fp: latest.context_fp || null,
      data_stage: latest.data_stage || null,
      latest_version: latest.version,
      versions: entries.length,
      quality: latest.quality,
      title: latest.title || scene_key,
      tags: latest.tags || [],
      summary: latest.summary || null,
      reuse_count: entries.reduce((n, e) => n + (e.reuse_count || 0), 0),
      updated_at: latest.updated_at || latest.created_at || null,
      ontology_path: join(STORE_DIR, latest.path),
    };
  }).sort((a, b) => (b.updated_at || '').localeCompare(a.updated_at || ''));

  const hasSemanticLookup = !!scene && !!wantProfile && typeof contextFp === 'string' && contextFp.trim() !== '';
  if (!dataPath && !hasSemanticLookup) {
    return {
      mode: 'list', status: null, match: null, candidates, fingerprint: null,
      recommended_scene: candidates[0]?.scene_key || null,
    };
  }
  const found = findMatch(dataPath === undefined ? null : dataPath, {
    scene: scene || undefined,
    profile: wantProfile || undefined,
    contextFp: contextFp || undefined,
  });
  const status = found.match === 'exact' ? 'exact' : (found.match === 'extend' ? 'scene_only' : 'miss');
  return {
    mode: 'fingerprint',
    status,
    match: found,
    fingerprint: { schema_fp: found.schema_fp ?? null, key_columns: null },
    candidates,
    recommended_scene: found.scene_key || null,
  };
}

// ────────────────────────── 确定性快路径（plan v5 F1） ──────────────────────────

// CP-2 校验：spawn validate.mjs 子进程（纯 CLI，exit 0/1）。
const VALIDATE_MJS = join(__dirname, 'validate.mjs');

// CP-2 校验（快路径内部形态）：委托 validateOntology，保持单一判据。
function runCp2Validation(ontologyPath, schemaPath) {
  const res = validateOntology(ontologyPath, { schemaPath: schemaPath || ONTOLOGY_SCHEMA_PATH });
  if (res.ok) return { ok: true };
  return { ok: false, errors: res.errors.map((e) => `[${e.path}] ${e.message}`).join('\n').slice(-800) };
}

// 最小 clarification（AUTO_RESOLVED）——保持 CP-3 / 下游契约完整（评审确认该形态与 e2e 一致）。
function writeFastPathClarification(runDir, sceneKey, reason) {
  const p = join(resolve(runDir), '00_input', 'clarification_needed.json');
  const payload = {
    clarification_status: 'AUTO_RESOLVED',
    source: 'ontology_fastpath',
    scene_key: sceneKey || null,
    resolved_by: 'deterministic fast-reuse (plan v5 F1) — ontology reused verbatim from store, semantics pre-validated at publish time',
    reason: reason || null,
    generated_at: new Date().toISOString(),
  };
  mkdirSync(dirname(p), { recursive: true });
  writeFileSync(p, JSON.stringify(payload, null, 2));
  return p;
}

/**
 * 确定性快路径：find → reuse → CP-2（失败回滚）→ publish，单命令完成。
 * 门槛：findMatch.match === 'exact'（schema 精确命中）；content drift 仅作 advisory（评审 R4）。
 * 校验失败 → 回滚拷贝并返回 fastPath:false（调用方回退 LLM 子代理路径）。
 */
export function fastReuse({ dataPath, runDir, scene, schemaPath }) {
  const absRunDir = resolve(runDir);

  // 1. find（门槛：exact）
  const found = findMatch(dataPath, { scene: scene || undefined });
  if (found.match !== 'exact') {
    return { fastPath: false, reason: found.reason, match: found.match };
  }

  // 2. reuse（拷贝 store 本体到 run 目录）
  reuse({ source: found.ontology_path, runDir: absRunDir });
  const ontologyPath = join(absRunDir, '01_ontology', 'ontology.json');

  // 3. CP-2 校验（schema + ≥1KB）——失败回滚拷贝
  const cp2 = runCp2Validation(ontologyPath, schemaPath);
  if (!cp2.ok) {
    try { unlinkSync(ontologyPath); } catch { /* ignore */ }
    return { fastPath: false, reason: `CP-2 validation failed after reuse — rolled back: ${cp2.errors}`, match: 'exact' };
  }

  // 4. publish（幂等，内容相同会去重；评审确认安全）
  let published = null;
  try {
    published = publish({ runDir: absRunDir, scene: found.scene_key, buildMode: 'reuse', quality: 'unvalidated' });
  } catch (e) {
    // publish 失败不阻断快路径（本体已在 run 目录且 CP-2 已过）
    published = { error: e.message };
  }

  // 5. 最小 clarification（CP-3 契约）
  const clarificationPath = writeFastPathClarification(absRunDir, found.scene_key, found.reason);

  return {
    fastPath: true,
    reason: found.reason,
    content_match: found.content_match ? 'exact' : 'advisory-drift (schema-identical, different batch)',
    ontology_path: ontologyPath,
    scene_key: found.scene_key,
    store_version: found.version,
    published: published?.deduped ? 'deduped' : (published?.version ? `v${published.version}` : published?.error || 'skipped'),
    clarification_path: clarificationPath,
  };
}

// ────────────────────────── 事件写入 ──────────────────────────

export function appendPipelineEvent(runDir, event) {
  const path = join(resolve(runDir), '.pipeline_events.jsonl');
  const line = JSON.stringify({ timestamp: new Date().toISOString(), ...event });
  writeFileSync(path, line + '\n', { flag: 'a' });
}

// ────────────────────────── CLI ──────────────────────────

function cli() {
  const [cmd, ...args] = process.argv.slice(2);
  const arg = (name) => {
    const i = args.indexOf(`--${name}`);
    return i >= 0 ? args[i + 1] : undefined;
  };
  try {
    switch (cmd) {
      case 'fingerprint': {
        const fp = computeFingerprint(args[0]);
        console.log(JSON.stringify(fp, null, 2));
        break;
      }
      case 'find': {
        // Semantic (DOE) lookups carry no data file at all → accept --data and
        // tolerate the data path appearing after flags.
        const valueFlags = new Set(['scene', 'profile', 'context-fp', 'data']);
        const positional = [];
        for (let i = 0; i < args.length; i++) {
          const token = args[i];
          if (token.startsWith('--')) {
            if (!token.includes('=') && valueFlags.has(token.slice(2))) i++;
            continue;
          }
          positional.push(token);
        }
        const findTarget = positional[0] ?? arg('data') ?? null;
        const result = findMatch(findTarget, {
          scene: arg('scene'),
          profile: arg('profile'),
          contextFp: arg('context-fp'),
        });
        console.log(JSON.stringify(result, null, 2));
        break;
      }
      case 'context-fp': {
        // Semantic fingerprint of a context JSON file:
        //   - profile=doe / default: analysis_context shape (mirrored 1:1 by
        //     doe_ontology_prepare._context_fp)
        //   - profile=stability|sentinel: watch declaration shape
        //     {columns:[{col,role,unit,lsl,usl}], windows:[{factor,lo,hi}]}
        //     (mirrored 1:1 by ontology_prepare_common.compute_watch_context_fp)
        const ctxPath = arg('context');
        const ctxJson = arg('context-json');
        let ctx;
        if (ctxPath) ctx = JSON.parse(readFileSync(resolve(ctxPath), 'utf-8'));
        else if (ctxJson) ctx = JSON.parse(ctxJson);
        else throw new Error('context-fp requires --context <file> or --context-json <json>');
        const wantProfile = normalizeProfile(arg('profile'));
        const watch = wantProfile === 'stability' || wantProfile === 'sentinel';
        console.log(JSON.stringify(watch ? {
          context_fp: computeWatchContextFingerprint(ctx),
          version: WATCH_CONTEXT_FP_VERSION,
          profile: wantProfile,
        } : {
          context_fp: computeContextFingerprint(ctx),
          version: CONTEXT_FP_VERSION,
        }, null, 2));
        break;
      }
      case 'publish': {
        const result = publish({
          runDir: arg('run-dir'),
          scene: arg('scene'),
          buildMode: arg('build-mode') || 'full',
          quality: arg('quality') || 'unvalidated',
          // CLI 侧此前丢弃 dataFile —— publish() 支持但永远收不到，导致
          // run_config.data_path 也未填时 schema_fp 恒为 null，fast-reuse 永不命中。
          dataFile: arg('data-file'),
          profile: arg('profile'),
          contextFp: arg('context-fp'),
          dataStage: arg('data-stage'),
        });
        console.log(JSON.stringify(result, null, 2));
        break;
      }
      case 'reuse': {
        const result = reuse({ source: arg('source'), runDir: arg('run-dir') });
        console.log(JSON.stringify(result, null, 2));
        break;
      }
      case 'fast-reuse': {
        const result = fastReuse({
          dataPath: arg('data'),
          runDir: arg('run-dir'),
          scene: arg('scene'),
          schemaPath: arg('schema'),
        });
        console.log(JSON.stringify(result, null, 2));
        break;
      }
      case 'list': {
        const idx = listStore();
        console.log(JSON.stringify(idx, null, 2));
        break;
      }
      case 'show': {
        const asset = readAsset(args[0], arg('version'));
        if (!asset) throw new Error(`Asset not found: ${args[0]} v${arg('version')}`);
        console.log(JSON.stringify(asset, null, 2));
        break;
      }
      case 'save': {
        // 离线编辑落库：--scene <key> --file <edited.json> [--base-version N] [--title T] [--tags a,b]
        const file = arg('file');
        if (!file) throw new Error('--file <edited ontology.json> is required');
        const result = addVersion({
          sceneKey: arg('scene'),
          ontology: readFileSync(resolve(file), 'utf-8'),
          buildMode: arg('build-mode') || 'edit',
          quality: arg('quality') || 'unvalidated',
          title: arg('title') || null,
          tags: (arg('tags') || '').split(',').map((s) => s.trim()).filter(Boolean),
          notes: arg('notes') || '',
          origin: 'cli',
          parentVersion: arg('base-version') ? Number(arg('base-version')) : null,
          inheritFrom: arg('base-version') ? getEntry(arg('scene'), arg('base-version')) : null,
          dataFile: arg('data-file') || null,
        });
        console.log(JSON.stringify(result, null, 2));
        break;
      }
      case 'validate': {
        const payload = arg('file') || args[0];
        if (!payload) throw new Error('validate <path> | --file <path>');
        const result = validateOntology(payload, { schemaPath: arg('schema') });
        console.log(JSON.stringify(result, null, 2));
        if (!result.ok) process.exit(1);
        break;
      }
      case 'recommend': {
        console.log(JSON.stringify(recommendReuse({
          dataPath: arg('data'),
          scene: arg('scene'),
          profile: arg('profile'),
          contextFp: arg('context-fp'),
        }), null, 2));
        break;
      }
      case 'remove': {
        if (arg('version')) console.log(JSON.stringify(removeVersion(args[0], arg('version'), arg('profile')), null, 2));
        else console.log(JSON.stringify(removeScene(args[0]), null, 2));
        break;
      }
      case 'deprecate': {
        console.log(JSON.stringify(deprecate(args[0], arg('version')), null, 2));
        break;
      }
      case 'stats': {
        const idx = listStore();
        const byScene = {};
        const byProfile = {};
        for (const e of idx.entries) {
          const prof = entryProfile(e);
          byProfile[prof] = (byProfile[prof] || 0) + 1;
          byScene[e.scene_key] = byScene[e.scene_key] || { versions: 0, latest_version: 0, reuse_count: 0, quality: e.quality, profiles: {} };
          byScene[e.scene_key].versions++;
          byScene[e.scene_key].latest_version = Math.max(byScene[e.scene_key].latest_version, e.version);
          byScene[e.scene_key].reuse_count += e.reuse_count || 0;
          byScene[e.scene_key].profiles[prof] = (byScene[e.scene_key].profiles[prof] || 0) + 1;
          if (e.quality === 'endorsed') byScene[e.scene_key].quality = 'endorsed';
        }
        console.log(JSON.stringify({ store_dir: STORE_DIR, scenes: byScene, by_profile: byProfile, total_entries: idx.entries.length }, null, 2));
        break;
      }
      default:
        console.error('Usage: ontology_store.mjs <cmd> [args]');
        console.error('  -- 管线协议 --');
        console.error('  fingerprint <data.csv>');
        console.error('  find <data.csv> [--scene <key>] [--profile diagnosis|doe|stability|sentinel] [--context-fp <sha256:…>]');
        console.error('  context-fp --context <analysis_context.json> [--profile diagnosis|doe|stability|sentinel]');
        console.error('                                                  doe=语义指纹（与 doe_ontology_prepare 同源）；');
        console.error('                                                  stability|sentinel=watch 声明指纹（与 ontology_prepare_common 同源）');
        console.error('  publish --run-dir <RUN_DIR> [--scene <key>] [--build-mode full|extend|reuse|prior_knowledge] [--quality unvalidated|endorsed] [--profile diagnosis|doe|stability|sentinel] [--context-fp <sha256:…>] [--data-stage design_only|collected]');
        console.error('  reuse --source <ontology.json> --run-dir <RUN_DIR>');
        console.error('  fast-reuse --data <data.csv> --run-dir <RUN_DIR> [--scene <key>] [--schema <schema.json>]');
        console.error('  -- 资产管理（前端本体管理页同源） --');
        console.error('  list                                                  列出 store 索引');
        console.error('  show <scene> --version <N>                            读取单个资产');
        console.error('  save --scene <key> --file <edited.json> [--base-version N] [--title T] [--tags a,b] [--notes S]');
        console.error('  validate <path> | --file <path> [--schema <schema.json>]');
        console.error('  recommend [--data <data.csv>] [--scene <key>] [--profile diagnosis|doe|stability|sentinel] [--context-fp <sha256:…>]');
        console.error('  remove <scene> [--version <N>] [--profile <p>]         删版本或整场景');
        console.error('  deprecate <scene_key> --version <N>');
        console.error('  stats');
        process.exit(cmd ? 1 : 0);
    }
  } catch (e) {
    console.error(`ERROR: ${e.message}`);
    process.exit(1);
  }
}

const isDirectRun = process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if (isDirectRun) cli();
