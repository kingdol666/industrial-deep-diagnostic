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
//
// 并发契约（2026-10-17 加固）：
//   - 所有索引变更（addVersion / reuse 计数 / deprecate / updateEntry /
//     removeVersion / removeScene）在 withStoreLock() 跨进程写锁内完成
//     read-modify-write；两个并发 publish 不再算出同一个 nextVersion。
//   - 读路径（readIndex / findMatch / listStore / …）保持无锁：writeIndex 是
//     tmp+rename 原子替换，读到的永远是完整的一代索引。
//   - index.json 解析失败 / entries 非数组 → 备份为 index.json.corrupt-<ts>
//     并抛 OntologyStoreCorruptError（绝不静默当成空库，否则下一个写者会把
//     整库抹平成 {entries: []}）。

import { createHash } from 'crypto';
import { spawnSync } from 'child_process';
import { existsSync, mkdirSync, readFileSync, writeFileSync, renameSync, copyFileSync, statSync, readdirSync, unlinkSync, rmdirSync, openSync, closeSync, writeSync } from 'fs';
import { join, dirname, resolve, basename, extname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
export const PROJECT_ROOT = resolve(__dirname, '..', '..', '..');
// STORE_DIR 可用环境变量 ONTOLOGY_STORE_DIR 覆盖（并发测试 / 沙箱把 store 指到
// 隔离目录；模块加载时解析一次，因此必须在 import 前设置）。
export const STORE_DIR = process.env.ONTOLOGY_STORE_DIR
  ? resolve(process.env.ONTOLOGY_STORE_DIR)
  : join(PROJECT_ROOT, 'data', 'ontology_store');
export const INDEX_PATH = join(STORE_DIR, 'index.json');
// 跨进程写锁文件：与 index.json 同目录的点文件。它既不是 scene 目录也不是
// version 条目（索引里的条目只来自 index.json 的 entries[]），store 目录又位于
// 已 gitignore 的 /data/ 下（`.gitignore:193`）——无需额外忽略规则。
export const LOCK_PATH = join(STORE_DIR, '.index.lock');
export const STORE_INDEX_VERSION = 1;
const MAX_VERSIONS_PER_SCENE = 10;
const LOCK_STALE_MS = 30000;   // 锁 mtime 超过该时长 → 持有者视为已死，接管
const LOCK_TIMEOUT_MS = 10000; // 获取锁的最长等待
const LOCK_RETRY_MS = 25;      // 重试退避基数（附加随机抖动，避免活锁同步）

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
  const SAMPLE_BYTES = 2 * 1024 * 1024; // 2MB 头部采样足以取表头与类型样本
  const head = readFileSync(abs, { encoding: 'utf-8' }).slice(0, SAMPLE_BYTES);
  const rows = parseCsvLines(head, 501);
  if (rows.length === 0) throw new Error(`Empty or unparsable CSV: ${abs}`);
  const header = rows[0].map(h => h.trim());
  const sample = rows.slice(1, 501);
  // E-1H (07_hetero/preprocessed_data_hetero.csv) appends derived `HX-*` feature
  // columns at the tail. They are derived FROM the anchor columns, so including
  // them in schema_fp would make every hetero run miss the fast-reuse cache
  // (plan v1.1 D6). Base schema = non-HX prefix columns only; HX columns are
  // tracked separately as hetero_fp.
  const isHx = (name) => /^HX-/.test(name);
  const baseColumns = [];
  const hxColumns = [];
  header.forEach((column, position) => {
    const entry = { column, dtype: inferType(sample.map(r => r[position])), position };
    (isHx(column) ? hxColumns : baseColumns).push(entry);
  });
  const columns = baseColumns;
  const schema_fp = 'sha256:' + createHash('sha256')
    .update(JSON.stringify(baseColumns))
    .digest('hex');
  const hetero_fp = hxColumns.length
    ? 'sha256:' + createHash('sha256').update(JSON.stringify(hxColumns)).digest('hex')
    : null;
  // 内容指纹：文件大小 + 头部内容哈希（同 schema 不同批次的检测提示，非精确）
  const content_fp = 'sha256:' + createHash('sha256')
    .update(String(size))
    .update(head.slice(0, 64 * 1024))
    .digest('hex');
  return { schema_fp, content_fp, hetero_fp, columns, row_sampled: sample.length, file_size: size };
}

// ────────────────────────── 跨进程写锁 ──────────────────────────

/** index.json 损坏（解析失败 / entries 非数组）：原文件已备份，拒绝继续读写语义。 */
export class OntologyStoreCorruptError extends Error {
  constructor(message, { indexPath = INDEX_PATH, backupPath = null, cause = null } = {}) {
    super(message);
    this.name = 'OntologyStoreCorruptError';
    this.code = 'ONTOLOGY_STORE_CORRUPT';
    this.indexPath = indexPath;
    this.backupPath = backupPath;
    if (cause) this.cause = cause;
  }
}

/** 未能在超时内获得 store 写锁。 */
export class OntologyStoreLockError extends Error {
  constructor(message, { lockPath = LOCK_PATH, holder = null } = {}) {
    super(message);
    this.name = 'OntologyStoreLockError';
    this.code = 'ONTOLOGY_STORE_LOCK_TIMEOUT';
    this.lockPath = lockPath;
    this.holder = holder;
  }
}

// 同步睡眠（零依赖）：Atomics.wait 只阻塞当前线程，适合 CLI/短临界区。
const sleepBuffer = new Int32Array(new SharedArrayBuffer(4));
function sleepSync(ms) { Atomics.wait(sleepBuffer, 0, 0, ms); }

function timestampSuffix() {
  return new Date().toISOString().replace(/[:.]/g, '-'); // Windows 文件名安全
}

function readLockHolder() {
  try { return JSON.parse(readFileSync(LOCK_PATH, 'utf-8')); } catch { return null; }
}

// openSync('wx') 的可重试失败码：EEXIST 是正常竞争；Windows 上创建文件与
// 另一进程的 unlink 撞车时会以 EPERM/EACCES/EBUSY（pending delete）浮现，
// 语义同样是「别人正持有/刚释放」——必须重试，绝不能当致命错误抛出。
const LOCK_BUSY_ERRORS = new Set(['EEXIST', 'EPERM', 'EACCES', 'EBUSY', 'ENOTEMPTY']);

/** 原子创建锁文件（wx = 独占创建，已存在则 EEXIST）；内容 {pid, ts, nonce}。 */
function acquireLockFile(nonce) {
  mkdirSync(STORE_DIR, { recursive: true });
  let fd;
  try {
    fd = openSync(LOCK_PATH, 'wx');
  } catch (e) {
    if (LOCK_BUSY_ERRORS.has(e.code)) {
      throw Object.assign(new Error(`ontology store lock busy (${e.code}): ${LOCK_PATH}`), { code: 'EEXIST', cause: e });
    }
    throw e;
  }
  try {
    writeSync(fd, JSON.stringify({
      pid: process.pid,
      ts: new Date().toISOString(),
      nonce,
      op: process.argv[1] ? basename(process.argv[1]) : null,
    }));
  } catch (e) {
    // 写内容失败（磁盘满等）不要留下半个空锁把别人堵 30s
    try { closeSync(fd); } catch { /* ignore */ }
    try { unlinkSync(LOCK_PATH); } catch { /* ignore */ }
    throw e;
  }
  try { closeSync(fd); } catch { /* ignore */ }
}

/** 只释放自己的锁：持有者被判定陈旧并接管后，原持有者不得删掉新持有者的锁。 */
function releaseLockFile(nonce) {
  const holder = readLockHolder();
  if (holder && holder.nonce && holder.nonce !== nonce) return; // 已被接管
  for (let attempt = 0; attempt < 3; attempt += 1) {
    try { unlinkSync(LOCK_PATH); return; } catch {
      // Windows 上并发读/抢占可能瞬时拒绝 unlink —— 小退避后重试
      sleepSync(5);
    }
  }
}

/**
 * 跨进程独占写锁：openSync('wx') 原子创建 + 小步退避重试（上限 ~10s）；
 * 持有者崩溃留下的陈旧锁（mtime 超过 LOCK_STALE_MS）会被接管并打警告到
 * stderr；无论 fn 抛出与否，finally 必定释放。
 *
 * 只包住 store 侧的 read-modify-write 临界区 —— 不要在锁内跑长任务
 * （CSV 指纹、校验子进程、拷贝等都应在锁外完成）。
 */
export function withStoreLock(fn) {
  const nonce = `${process.pid}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
  const deadline = Date.now() + LOCK_TIMEOUT_MS;
  let staleWarned = false;
  for (;;) {
    try {
      acquireLockFile(nonce);
      break;
    } catch (e) {
      if (e.code !== 'EEXIST') throw e;
      let st = null;
      try { st = statSync(LOCK_PATH); } catch { /* 锁刚好被释放：立即重试 */ }
      if (st && Date.now() - st.mtimeMs > LOCK_STALE_MS) {
        if (!staleWarned) {
          staleWarned = true;
          console.error(`WARNING: stale ontology store lock at ${LOCK_PATH} (mtime ${new Date(st.mtimeMs).toISOString()} older than ${LOCK_STALE_MS}ms, holder: ${JSON.stringify(readLockHolder())}) — taking over`);
        }
        try { unlinkSync(LOCK_PATH); } catch { /* 抢占失败：稍后重试 */ }
        sleepSync(5);
        if (Date.now() >= deadline) {
          throw new OntologyStoreLockError(
            `cannot acquire store lock within ${LOCK_TIMEOUT_MS}ms (stale-lock takeover did not win): ${LOCK_PATH}`,
            { holder: readLockHolder() });
        }
        continue;
      }
      if (Date.now() >= deadline) {
        throw new OntologyStoreLockError(
          `cannot acquire store lock within ${LOCK_TIMEOUT_MS}ms: ${LOCK_PATH} (holder: ${JSON.stringify(readLockHolder())})`,
          { holder: readLockHolder() });
      }
      sleepSync(LOCK_RETRY_MS + Math.floor(Math.random() * LOCK_RETRY_MS));
    }
  }
  try {
    return fn();
  } finally {
    releaseLockFile(nonce);
  }
}

// ────────────────────────── 注册表 ──────────────────────────

/** 备份损坏的 index.json；内容一致则复用同一备份（读路径反复命中不刷屏）。 */
function backupCorruptIndex(raw) {
  mkdirSync(STORE_DIR, { recursive: true });
  let names = [];
  try { names = readdirSync(STORE_DIR).filter((f) => f.startsWith('index.json.corrupt-')); } catch { /* ignore */ }
  for (const name of names) {
    try {
      if (readFileSync(join(STORE_DIR, name), 'utf-8') === raw) return join(STORE_DIR, name);
    } catch { /* ignore */ }
  }
  const backupPath = join(STORE_DIR, `index.json.corrupt-${timestampSuffix()}`);
  writeFileSync(backupPath, raw);
  return backupPath;
}

/**
 * 读取 store 索引。
 *  - 文件不存在 → `{version, entries: []}`（首次运行，正常）。
 *  - 解析失败 / entries 非数组 → 备份原文件为 index.json.corrupt-<ISO ts> 并
 *    抛 OntologyStoreCorruptError（带 backupPath）。绝不静默返回空库：那会让
 *    下一个写者把损坏如实持久化，等于把整库清零。
 */
export function readIndex() {
  if (!existsSync(INDEX_PATH)) return { version: STORE_INDEX_VERSION, entries: [] };
  let raw;
  try {
    raw = readFileSync(INDEX_PATH, 'utf-8');
  } catch (e) {
    throw new OntologyStoreCorruptError(
      `ontology store index unreadable at ${INDEX_PATH}: ${e.message}. Refusing to continue — a silent empty index would drop every stored version on the next write.`,
      { cause: e });
  }
  let idx = null;
  try {
    idx = JSON.parse(raw);
  } catch (e) {
    const backupPath = backupCorruptIndex(raw);
    throw new OntologyStoreCorruptError(
      `ontology store index is not valid JSON: ${INDEX_PATH} (${e.message}). Original backed up to ${backupPath}; repair or restore a backup before writing.`,
      { backupPath, cause: e });
  }
  if (!idx || typeof idx !== 'object' || Array.isArray(idx) || !Array.isArray(idx.entries)) {
    const backupPath = backupCorruptIndex(raw);
    throw new OntologyStoreCorruptError(
      `ontology store index has no entries[] array: ${INDEX_PATH}. Original backed up to ${backupPath}; refusing to read it as an empty store.`,
      { backupPath });
  }
  return idx;
}

export function writeIndex(idx) {
  mkdirSync(STORE_DIR, { recursive: true });
  // 进程唯一 tmp 名：锁内调用之间本已串行，但绕过锁的直接调用（如后端
  // ontology.service 的索引回填）也不该在共享 tmp 上互相截断——曾经
  // A 写的 tmp 被 B 截断后再被 A rename，就会把半个索引换成正式文件。
  const tmp = `${INDEX_PATH}.${process.pid}-${Math.random().toString(36).slice(2, 8)}.tmp`;
  writeFileSync(tmp, JSON.stringify(idx, null, 2));
  renameSync(tmp, INDEX_PATH);
}

export function listStore() {
  return readIndex();
}

/**
 * 查找可复用本体。
 * @returns {{match:'exact'|'extend'|'miss', scene_key?, version?, ontology_path?, provenance_path?, reason?}}
 */
export function findMatch(dataPath, { scene } = {}) {
  const fp = computeFingerprint(dataPath);
  const idx = readIndex();
  const candidates = idx.entries
    .filter(e => e.schema_fp === fp.schema_fp && e.quality !== 'deprecated')
    .filter(e => !scene || e.scene_key === scene)
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
    const sceneEntries = idx.entries.filter(e => e.scene_key === scene && e.quality !== 'deprecated');
    if (sceneEntries.length > 0) {
      const best = sceneEntries.sort((a, b) => b.version - a.version)[0];
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

function nextVersion(idx, sceneKey) {
  const max = idx.entries
    .filter(e => e.scene_key === sceneKey)
    .reduce((m, e) => Math.max(m, e.version), 0);
  return max + 1;
}

function pruneVersions(idx, sceneKey) {
  const keep = new Set(['endorsed']);
  const entries = idx.entries
    .filter(e => e.scene_key === sceneKey)
    .sort((a, b) => b.version - a.version);
  const live = entries.filter(e => keep.has(e.quality));
  const removable = entries.filter(e => !keep.has(e.quality)).slice(MAX_VERSIONS_PER_SCENE);
  for (const e of removable) {
    try {
      const dir = join(STORE_DIR, e.scene_key, `v${e.version}`);
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
 * 并发：整段「读索引 → 定版本号 → 落盘 → 写索引」在 withStoreLock 内，
 * 两个并发 publish 不会算出同一个 nextVersion。指纹计算（读整个 CSV）在锁外。
 *
 * @returns {{scene_key, version, path, deduped?, summary}}
 */
export function addVersion({
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
  fingerprint = null,
}) {
  const key = String(sceneKey || '').trim();
  if (!key || !/^[A-Za-z0-9._-]+$/.test(key)) {
    throw new Error(`invalid scene_key: ${JSON.stringify(sceneKey)} (allowed: A-Za-z0-9._-)`);
  }
  const { content, parsed } = normalizeOntologyInput(ontology);
  if (Buffer.byteLength(content, 'utf-8') < ONTOLOGY_MIN_BYTES) {
    throw new Error(`ontology too small (${Buffer.byteLength(content, 'utf-8')}B < ${ONTOLOGY_MIN_BYTES}B CP-2 floor)`);
  }

  // 指纹是纯计算（不读索引）→ 锁外完成，别让整文件指纹拖住写锁。
  // 调用方（publish）可用 `fingerprint` 传预计算结果，避免重复读取。
  let fp = fingerprint;
  if (!fp && dataFile) {
    try { fp = computeFingerprint(dataFile); } catch { fp = null; /* keep inherited */ }
  }
  const hash = contentHashOf(content);

  return withStoreLock(() => {
    const idx = readIndex();
    const deduped = idx.entries.find((e) => {
      if (e.scene_key !== key) return false;
      try {
        const p = join(STORE_DIR, e.path);
        return existsSync(p) && contentHashOf(readFileSync(p, 'utf-8')) === hash;
      } catch { return false; }
    });
    if (deduped) {
      // 指纹回填：旧条目可能在 dataFile 缺失时代入库（schema_fp=null），dedupe
      // 复用版本时若本次带 dataFile 则就地补算——否则该条目永远无法被
      // fast-reuse 命中（2026-10-13 fieldtest 实测）。
      if (!deduped.schema_fp && dataFile && fp) {
        try {
          deduped.schema_fp = fp.schema_fp;
          deduped.content_fp = fp.content_fp;
          deduped.fingerprinted_from = fp.fingerprinted_from || resolve(dataFile);
          deduped.fingerprinted_at = new Date().toISOString();
          writeIndex(idx);
        } catch { /* 指纹算不出就保持 null：publish 照常去重，reuse 继续 miss */ }
      }
      return {
        scene_key: key, version: deduped.version, path: join(STORE_DIR, deduped.path),
        deduped: true, schema_fp: deduped.schema_fp || null,
        summary: deduped.summary || summarizeOntology(parsed),
      };
    }

    const version = nextVersion(idx, key);
    const relDir = join(key, `v${version}`);
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
    if (fp) {
      entry.schema_fp = fp.schema_fp;
      entry.content_fp = fp.content_fp;
      entry.fingerprinted_from = fp.fingerprinted_from || (dataFile ? resolve(dataFile) : null);
    }

    writeFileSync(join(absDir, 'provenance.json'), JSON.stringify({
      scene_key: key,
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
    pruneVersions(idx, key);
    writeIndex(idx);
    return { scene_key: key, version, path: absOntologyPath, summary: entry.summary };
  });
}

/**
 * 将 run 目录中通过 CP-2 的 ontology.json 发布入 store。
 * 委托 addVersion（唯一写入口）；指纹候选链：显式 dataFile > run_config.data_path
 * > input_manifest > 00_input 目录首个 csv/tsv。
 * @returns {{scene_key, version, path, schema_fp}}
 */
export function publish({ runDir, scene, buildMode = 'full', quality = 'unvalidated', dataFile }) {
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
    // 上面刚算过 → 以 `fingerprint` 传入，addVersion 不再重复读整文件。
    fingerprint: fps[0] || null,
    dataFile: fps[0]?.fingerprinted_from || dataFile || null,
    runDir: absRunDir,
  });
  return {
    scene_key: result.scene_key,
    version: result.version,
    path: result.path,
    schema_fp: fps[0]?.schema_fp ?? null,
    ...(result.deduped ? { deduped: true } : {}),
  };
}

/**
 * 复用：拷贝 store 本体到 run 目录并写 pipeline 事件。
 *
 * 拷贝（run 侧，与索引无关）在锁外；store 侧的 reuse_count / reuse_history
 * 读改写与 deprecate 等同属 mutator，进锁。
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

  // 更新 store 的 reuse 计数与 provenance 历史（锁内 read-modify-write）
  withStoreLock(() => {
    const idx = readIndex();
    const entry = idx.entries.find(e => join(STORE_DIR, e.path) === src);
    if (entry) {
      entry.reuse_count = (entry.reuse_count || 0) + 1;
      const provPath = join(STORE_DIR, dirname(entry.path), 'provenance.json');
      try {
        const prov = JSON.parse(readFileSync(provPath, 'utf-8'));
        prov.reuse_history.push({ run_dir: basename(absRunDir), at: new Date().toISOString() });
        writeFileSync(provPath, JSON.stringify(prov, null, 2));
      } catch { /* ignore */ }
      writeIndex(idx);
    }
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
export function removeVersion(sceneKey, version) {
  return withStoreLock(() => {
    const idx = readIndex();
    const v = Number(version);
    const entry = idx.entries.find((e) => e.scene_key === sceneKey && e.version === v);
    if (!entry) throw new Error(`Entry not found: ${sceneKey} v${v}`);
    const dir = join(STORE_DIR, entry.scene_key, `v${v}`);
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
 */
export function recommendReuse({ dataPath, scene } = {}) {
  const idx = readIndex();
  const byScene = new Map();
  for (const e of idx.entries) {
    if (scene && e.scene_key !== scene) continue;
    if (!byScene.has(e.scene_key)) byScene.set(e.scene_key, []);
    byScene.get(e.scene_key).push(e);
  }
  const candidates = [...byScene.entries()].map(([scene_key, entries]) => {
    entries.sort((a, b) => b.version - a.version);
    const latest = entries[0];
    return {
      scene_key,
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

  if (!dataPath) {
    return { mode: 'list', match: null, candidates, fingerprint: null, recommended_scene: candidates[0]?.scene_key || null };
  }
  const found = findMatch(dataPath, { scene: scene || undefined });
  return {
    mode: 'fingerprint',
    match: found,
    fingerprint: { schema_fp: found.schema_fp, key_columns: null },
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
        const result = findMatch(args[0], { scene: arg('scene') });
        console.log(JSON.stringify(result, null, 2));
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
        console.log(JSON.stringify(recommendReuse({ dataPath: arg('data'), scene: arg('scene') }), null, 2));
        break;
      }
      case 'remove': {
        if (arg('version')) console.log(JSON.stringify(removeVersion(args[0], arg('version')), null, 2));
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
        for (const e of idx.entries) {
          byScene[e.scene_key] = byScene[e.scene_key] || { versions: 0, latest_version: 0, reuse_count: 0, quality: e.quality };
          byScene[e.scene_key].versions++;
          byScene[e.scene_key].latest_version = Math.max(byScene[e.scene_key].latest_version, e.version);
          byScene[e.scene_key].reuse_count += e.reuse_count || 0;
          if (e.quality === 'endorsed') byScene[e.scene_key].quality = 'endorsed';
        }
        console.log(JSON.stringify({ store_dir: STORE_DIR, scenes: byScene, total_entries: idx.entries.length }, null, 2));
        break;
      }
      default:
        console.error('Usage: ontology_store.mjs <cmd> [args]');
        console.error('  -- 管线协议 --');
        console.error('  fingerprint <data.csv>');
        console.error('  find <data.csv> [--scene <key>]');
        console.error('  publish --run-dir <RUN_DIR> [--scene <key>] [--build-mode full|extend] [--quality unvalidated|endorsed]');
        console.error('  reuse --source <ontology.json> --run-dir <RUN_DIR>');
        console.error('  fast-reuse --data <data.csv> --run-dir <RUN_DIR> [--scene <key>] [--schema <schema.json>]');
        console.error('  -- 资产管理（前端本体管理页同源） --');
        console.error('  list                                                  列出 store 索引');
        console.error('  show <scene> --version <N>                            读取单个资产');
        console.error('  save --scene <key> --file <edited.json> [--base-version N] [--title T] [--tags a,b] [--notes S]');
        console.error('  validate <path> | --file <path> [--schema <schema.json>]');
        console.error('  recommend [--data <data.csv>] [--scene <key>]');
        console.error('  remove <scene> [--version <N>]                        删版本或整场景');
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
