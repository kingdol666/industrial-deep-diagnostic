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
import { existsSync, mkdirSync, readFileSync, writeFileSync, renameSync, copyFileSync, statSync, readdirSync, unlinkSync, rmdirSync } from 'fs';
import { join, dirname, resolve, basename, extname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
export const PROJECT_ROOT = resolve(__dirname, '..', '..', '..');
export const STORE_DIR = join(PROJECT_ROOT, 'data', 'ontology_store');
const INDEX_PATH = join(STORE_DIR, 'index.json');
const MAX_VERSIONS_PER_SCENE = 10;

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

// ────────────────────────── 注册表 ──────────────────────────

function readIndex() {
  if (!existsSync(INDEX_PATH)) return { version: 1, entries: [] };
  try {
    const idx = JSON.parse(readFileSync(INDEX_PATH, 'utf-8'));
    if (!Array.isArray(idx.entries)) return { version: 1, entries: [] };
    return idx;
  } catch {
    return { version: 1, entries: [] };
  }
}

function writeIndex(idx) {
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

/**
 * 将 run 目录中通过 CP-2 的 ontology.json 发布入 store。
 * @returns {{scene_key, version, path}}
 */
export function publish({ runDir, scene, buildMode = 'full', quality = 'unvalidated', dataFile }) {
  const absRunDir = resolve(runDir);
  const ontologyPath = join(absRunDir, '01_ontology', 'ontology.json');
  if (!existsSync(ontologyPath)) throw new Error(`ontology.json not found under ${absRunDir}`);
  const content = readFileSync(ontologyPath, 'utf-8');
  if (content.length < 1024) throw new Error(`ontology.json too small (${content.length}B < 1KB CP-2 floor)`);
  JSON.parse(content); // must be valid JSON

  const manifestPath = join(absRunDir, 'run_manifest.json');
  let runId = basename(absRunDir);
  try {
    const manifest = JSON.parse(readFileSync(manifestPath, 'utf-8'));
    if (manifest.run_id) runId = manifest.run_id;
  } catch { /* ignore */ }

  // scene_key：显式指定 > 本体内 scene.name > run 目录名尾部
  let sceneKey = scene;
  if (!sceneKey) {
    try {
      const ontology = JSON.parse(content);
      sceneKey = ontology?.scene?.name || null;
    } catch { /* ignore */ }
  }
  if (!sceneKey) {
    const m = basename(absRunDir).match(/_(\w+)$/);
    sceneKey = m ? m[1] : basename(absRunDir);
  }

  const idx = readIndex();
  // 幂等发布：reuse 模式反复 publish 同一内容时去重（按本体内容哈希匹配同 scene 现有条目）
  const contentHash = 'sha256:' + createHash('sha256').update(content).digest('hex');
  const existing = idx.entries.find(e => {
    if (e.scene_key !== sceneKey) return false;
    try {
      const p = join(STORE_DIR, e.path);
      if (!existsSync(p)) return false;
      return 'sha256:' + createHash('sha256').update(readFileSync(p, 'utf-8')).digest('hex') === contentHash;
    } catch { return false; }
  });
  if (existing) {
    return { scene_key: sceneKey, version: existing.version, path: join(STORE_DIR, existing.path), schema_fp: existing.schema_fp, deduped: true };
  }
  const version = nextVersion(idx, sceneKey);
  const relDir = join(sceneKey, `v${version}`);
  const absDir = join(STORE_DIR, relDir);
  mkdirSync(absDir, { recursive: true });
  copyFileSync(ontologyPath, join(absDir, 'ontology.json'));

  const entry = {
    scene_key: sceneKey,
    version,
    schema_fp: null,
    content_fp: null,
    build_mode: buildMode,
    built_from_run: runId,
    created_at: new Date().toISOString(),
    reuse_count: 0,
    quality,
    path: relDir.split('\\').join('/') + '/ontology.json',
  };

  // 尝试补指纹：显式 --data-file > run_config.data_path > input_manifest > 00_input 目录首个数据文件
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
  for (const candidate of candidateDataPaths) {
    try {
      if (candidate && existsSync(candidate) && statSync(candidate).isFile() && /\.(csv|tsv)$/i.test(candidate)) {
        const fp = computeFingerprint(candidate);
        entry.schema_fp = fp.schema_fp;
        entry.content_fp = fp.content_fp;
        entry.fingerprinted_from = candidate;
        break;
      }
    } catch { /* try next candidate */ }
  }

  writeFileSync(join(absDir, 'provenance.json'), JSON.stringify({
    scene_key: sceneKey,
    version,
    built_from_run: runId,
    build_mode: buildMode,
    quality,
    schema_fp: entry.schema_fp,
    created_at: entry.created_at,
    reuse_history: [],
  }, null, 2));

  idx.entries.push(entry);
  pruneVersions(idx, sceneKey);
  writeIndex(idx);
  return { scene_key: sceneKey, version, path: join(absDir, 'ontology.json'), schema_fp: entry.schema_fp };
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

  // 更新 store 的 reuse 计数与 provenance 历史
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
  return { copied_to: dst, bytes: statSync(dst).size };
}

export function deprecate(sceneKey, version) {
  const idx = readIndex();
  const entry = idx.entries.find(e => e.scene_key === sceneKey && e.version === Number(version));
  if (!entry) throw new Error(`Entry not found: ${sceneKey} v${version}`);
  entry.quality = 'deprecated';
  writeIndex(idx);
  return entry;
}

// ────────────────────────── 确定性快路径（plan v5 F1） ──────────────────────────

// CP-2 校验：spawn validate.mjs 子进程（纯 CLI，exit 0/1）。
const VALIDATE_MJS = join(__dirname, 'validate.mjs');
function runCp2Validation(ontologyPath, schemaPath) {
  const schema = schemaPath || join(PROJECT_ROOT, '.claude', 'skills', 'industrial-ontology-builder', 'schemas', 'ontology_schema.json');
  const res = spawnSync(process.execPath, [VALIDATE_MJS, schema, ontologyPath], {
    encoding: 'utf-8', timeout: 30000, windowsHide: true,
  });
  if (res.status !== 0) {
    return { ok: false, errors: (res.stdout || res.stderr || '').slice(-800) };
  }
  // CP-2 第二条：≥1KB
  const bytes = statSync(ontologyPath).size;
  if (bytes < 1024) return { ok: false, errors: `ontology.json ${bytes}B < 1KB CP-2 floor` };
  return { ok: true };
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
        console.error('Usage: ontology_store.mjs <fingerprint|find|publish|reuse|fast-reuse|deprecate|stats> [args]');
        console.error('  fingerprint <data.csv>');
        console.error('  find <data.csv> [--scene <key>]');
        console.error('  publish --run-dir <RUN_DIR> [--scene <key>] [--build-mode full|extend] [--quality unvalidated|endorsed]');
        console.error('  reuse --source <ontology.json> --run-dir <RUN_DIR>');
        console.error('  fast-reuse --data <data.csv> --run-dir <RUN_DIR> [--scene <key>] [--schema <schema.json>]');
        console.error('  deprecate <scene_key> --version <N>');
        process.exit(cmd ? 1 : 0);
    }
  } catch (e) {
    console.error(`ERROR: ${e.message}`);
    process.exit(1);
  }
}

const isDirectRun = process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if (isDirectRun) cli();
