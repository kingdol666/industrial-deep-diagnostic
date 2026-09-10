// Ontology Service — 本体资产控制面（管理 / 可视化投影 / 质量度量 / 差异 / 采纳）。
//
// 分层：
//   ontology_store.mjs (shared)  ←  唯一写入口 + CP-2 判据（与 skill 协议同源）
//   ontology.service.mjs (此文件) ←  只读投影 + 业务编排（不直接写索引）
//   ontology.routes.mjs           ←  HTTP 控制 API
//
// 设计原则：
//  - 索引即事实源：列表页只读 index.json（O(1)），不逐个解析 ontology.json。
//  - 投影在服务端完成：图/度量/差异都是纯函数 → 可在 node:test 里直接断言（E2E 可验证）。
//  - 不猜测语义：无法解析的引用如实进入 `unresolved` / `issues`，不静默丢弃。

import { readdirSync, readFileSync, existsSync, statSync } from 'fs';
import { createHash } from 'crypto';
import { join, dirname, basename, resolve, relative, isAbsolute } from 'path';
import { PROJECT_ROOT } from '../../../../config/loader.mjs';
import {
  STORE_DIR, INDEX_PATH, ONTOLOGY_SCHEMA_PATH, ONTOLOGY_MIN_BYTES,
  readIndex, writeIndex, listStore, getEntry, readAsset, addVersion,
  updateEntry, removeVersion, removeScene, validateOntology, summarizeOntology,
  recommendReuse, computeFingerprint,
} from '../../../../.claude/shared/scripts/ontology_store.mjs';

const RUNS_DIR = join(PROJECT_ROOT, 'workspace', 'diagnostic-runs');

// ────────────────────────── 错误 ──────────────────────────

export class OntologyError extends Error {
  constructor(status, code, message, details) {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

// ────────────────────────── 资产读取 ──────────────────────────

/** 懒回填：老索引条目缺 summary / content_sha256 时补齐（只写索引，不动本体文件）。
 *
 *  content_sha256 同时是 HTTP 强 ETag 与并发前置条件的来源 —— 历史条目没有它，
 *  编辑页就会在保存时撞上 428。必须从磁盘内容重算，而不是留空。 */
function backfillIndex() {
  const idx = readIndex();
  let dirty = false;
  for (const e of idx.entries) {
    const abs = join(STORE_DIR, e.path);
    const exists = existsSync(abs);
    if (!e.summary && exists) {
      try {
        e.summary = summarizeOntology(JSON.parse(readFileSync(abs, 'utf-8')));
        dirty = true;
      } catch { /* 坏条目留给列表页按 missing 呈现 */ }
    }
    if (!e.content_sha256 && exists) {
      try {
        e.content_sha256 = 'sha256:' + createHash('sha256').update(readFileSync(abs, 'utf-8')).digest('hex');
        dirty = true;
      } catch { /* ignore */ }
    }
    if (e.updated_at === undefined) { e.updated_at = e.created_at || null; dirty = true; }
    if (e.title === undefined) { e.title = e.scene_key; dirty = true; }
    if (e.tags === undefined) { e.tags = []; dirty = true; }
    if (e.origin === undefined) { e.origin = e.built_from_run ? 'agent' : 'unknown'; dirty = true; }
  }
  if (dirty) writeIndex(idx);
  return idx;
}

/** 列表：按 scene 聚合，含每版本条目 + 落盘健康状态。 */
export function listAssets({ scene, quality, q } = {}) {
  const idx = backfillIndex();
  const scenes = new Map();
  const needle = q ? String(q).toLowerCase() : null;

  for (const e of idx.entries) {
    if (scene && e.scene_key !== scene) continue;
    if (quality && e.quality !== quality) continue;
    const abs = join(STORE_DIR, e.path);
    const present = existsSync(abs);
    const bytes = present ? statSync(abs).size : 0;
    const version = {
      scene_key: e.scene_key,
      version: e.version,
      title: e.title || e.scene_key,
      tags: e.tags || [],
      notes: e.notes || '',
      quality: e.quality,
      origin: e.origin || 'unknown',
      build_mode: e.build_mode,
      parent_version: e.parent_version ?? null,
      built_from_run: e.built_from_run || null,
      created_at: e.created_at || null,
      updated_at: e.updated_at || e.created_at || null,
      reuse_count: e.reuse_count || 0,
      schema_fp: e.schema_fp || null,
      fingerprinted_from: e.fingerprinted_from || null,
      summary: e.summary || null,
      bytes,
      present,
      path: e.path,
      absolute_path: abs,
    };
    if (!scenes.has(e.scene_key)) {
      scenes.set(e.scene_key, {
        scene_key: e.scene_key,
        title: version.title,
        tags: version.tags,
        latest_version: 0,
        version_count: 0,
        total_reuse: 0,
        qualities: {},
        origins: {},
        updated_at: null,
        summary: null,
        bytes: 0,
        broken: false,
        versions: [],
      });
    }
    const s = scenes.get(e.scene_key);
    s.versions.push(version);
    s.version_count++;
    s.total_reuse += version.reuse_count;
    s.qualities[version.quality] = (s.qualities[version.quality] || 0) + 1;
    s.origins[version.origin] = (s.origins[version.origin] || 0) + 1;
    s.bytes += version.bytes;
    if (!present) s.broken = true;
    if (version.version > s.latest_version) {
      s.latest_version = version.version;
      s.title = version.title;
      s.tags = version.tags;
      s.summary = version.summary;
    }
    if (!s.updated_at || (version.updated_at || '') > s.updated_at) s.updated_at = version.updated_at;
  }

  const list = [...scenes.values()];
  for (const s of list) s.versions.sort((a, b) => b.version - a.version);
  const filtered = needle
    ? list.filter((s) => s.scene_key.toLowerCase().includes(needle)
      || (s.title || '').toLowerCase().includes(needle)
      || s.tags.some((t) => t.toLowerCase().includes(needle))
      || (s.summary?.process_type || '').toLowerCase().includes(needle))
    : list;
  filtered.sort((a, b) => (b.updated_at || '').localeCompare(a.updated_at || ''));

  return {
    store_dir: STORE_DIR,
    index_path: INDEX_PATH,
    schema_path: ONTOLOGY_SCHEMA_PATH,
    min_bytes: ONTOLOGY_MIN_BYTES,
    scene_count: filtered.length,
    version_count: filtered.reduce((n, s) => n + s.version_count, 0),
    assets: filtered,
  };
}

/**
 * 确保索引条目带有 content_sha256（= HTTP 强 ETag = 并发前置条件的值）。
 * 历史条目没有该字段；从磁盘内容重算并持久化，否则编辑页保存时必然撞 428。
 * @returns {string|null}
 */
function ensureContentHash(entry) {
  if (!entry) return null;
  if (entry.content_sha256) return entry.content_sha256;
  const abs = join(STORE_DIR, entry.path);
  if (!existsSync(abs)) return null;
  try {
    const hash = 'sha256:' + createHash('sha256').update(readFileSync(abs, 'utf-8')).digest('hex');
    const idx = readIndex();
    const target = idx.entries.find((e) => e.scene_key === entry.scene_key && e.version === entry.version);
    if (target) { target.content_sha256 = hash; writeIndex(idx); }
    entry.content_sha256 = hash;
    return hash;
  } catch {
    return null;
  }
}

/** 单资产：本体 + provenance + 索引条目 + 校验 + 度量。 */
export function getAsset(sceneKey, version, { withGraph = true, withMetrics = true } = {}) {
  const asset = readAsset(sceneKey, version);
  if (!asset) throw new OntologyError(404, 'ONTOLOGY_NOT_FOUND', `本体资产不存在: ${sceneKey} v${version}`);
  if (asset.missing) {
    throw new OntologyError(410, 'ONTOLOGY_FILE_MISSING',
      `索引存在但本体文件缺失: ${asset.entry.path}（可删除该条目或重新发布）`);
  }
  const validation = validateOntology(asset.absolute_path);
  const etag = ensureContentHash(asset.entry);
  const out = {
    scene_key: sceneKey,
    version: Number(version),
    entry: asset.entry,
    ontology: asset.ontology,
    provenance: asset.provenance,
    absolute_path: asset.absolute_path,
    bytes: asset.bytes,
    store_dir: STORE_DIR,
    validation,
    etag,
  };
  if (withMetrics) out.metrics = computeMetrics(asset.ontology, { validation });
  if (withGraph) out.graph = buildGraph(asset.ontology);
  return out;
}

// ────────────────────────── 图投影（VOWL 风格的领域图） ──────────────────────────

// 分类调色板 —— 与前端暗色主题一致；语义：角色/实体类型各有稳定色。
export const GRAPH_PALETTE = {
  target: { color: '#f97362', symbol: 'circle', label: '目标量 (target)' },
  predictor: { color: '#4ea8f5', symbol: 'circle', label: '过程量 (predictor)' },
  confounder: { color: '#f5b544', symbol: 'circle', label: '混杂因子 (confounder)' },
  control: { color: '#31c9a8', symbol: 'roundRect', label: '控制量 (control)' },
  metadata: { color: '#8b93a7', symbol: 'rect', label: '元数据 (metadata)' },
  event: { color: '#b98cf0', symbol: 'diamond', label: '事件 (event)' },
  equipment: { color: '#6ee7b7', symbol: 'roundRect', label: '设备' },
  stage: { color: '#7aa2f7', symbol: 'roundRect', label: '工艺阶段' },
  principle: { color: '#c9a227', symbol: 'triangle', label: '物理原理' },
  failure_mode: { color: '#e06c9f', symbol: 'pin', label: '失效模式' },
  discrepancy: { color: '#ff6b6b', symbol: 'triangle', label: '差异信号' },
  group: { color: '#5b6b8c', symbol: 'rect', label: '参数组' },
};

const SIGNAL_BUCKETS = ['inspection_signals', 'process_parameters', 'control_variables', 'events', 'metadata_columns'];
const BUCKET_KIND = {
  inspection_signals: 'inspection',
  process_parameters: 'process',
  control_variables: 'control',
  events: 'event',
  metadata_columns: 'metadata',
};
const ROLE_COLOR_KEY = {
  target: 'target', predictor: 'predictor', confounder: 'confounder',
  control: 'control', metadata: 'metadata',
};
const REL_STRENGTH_WIDTH = { strong: 3.2, moderate: 2.2, weak: 1.4 };
const REL_STYLE = {
  causal: { color: '#f97362', label: '因果', dashed: false },
  correlative: { color: '#4ea8f5', label: '相关', dashed: true },
  control: { color: '#31c9a8', label: '控制', dashed: false },
  physical: { color: '#c9a227', label: '物理', dashed: false },
};

function signalRole(sig, bucket) {
  if (bucket === 'events') return 'event';
  if (bucket === 'metadata_columns') return 'metadata';
  return sig?.role || (bucket === 'control_variables' ? 'control' : 'predictor');
}

function shortLabel(text, max = 28) {
  const s = String(text ?? '').trim();
  return s.length > max ? `${s.slice(0, max - 1)}…` : s;
}

/**
 * 本体 → 归一化图（nodes / edges / categories / groups / unresolved）。
 *
 * 分三层，前端可独立开关（默认：核心语义网络）：
 *   structure   — scene / equipment / stages 骨架
 *   relationships — signals 之间的语义关系（因果/相关/控制/物理）
 *   knowledge   — 物理原理 / 失效模式 / 差异信号 / 混杂因子 / 参数组
 *
 * @param {object} ontology
 * @param {{layers?: {structure?:boolean, relationships?:boolean, knowledge?:boolean}}} [opts]
 */
export function buildGraph(ontology, opts = {}) {
  const layers = {
    structure: opts.layers?.structure !== false,
    relationships: opts.layers?.relationships !== false,
    knowledge: opts.layers?.knowledge === true,
  };
  const nodes = [];
  const edges = [];
  const groups = [];
  const unresolved = [];
  const usedCategories = new Set();
  const byId = new Map();
  const edgeKeys = new Set();

  const addNode = (node) => {
    if (byId.has(node.id)) return byId.get(node.id);
    byId.set(node.id, node);
    nodes.push(node);
    usedCategories.add(node.category);
    return node;
  };
  const addEdge = (edge) => {
    const key = `${edge.source}→${edge.target}:${edge.type}:${edge.relation || ''}`;
    if (edgeKeys.has(key)) return;
    edgeKeys.add(key);
    edges.push(edge);
  };

  if (!ontology || typeof ontology !== 'object') {
    return { nodes, edges, groups, categories: [], unresolved, layers, empty: true };
  }

  const signals = ontology.signals || {};
  const sceneId = 'scene::root';
  const sceneName = ontology?.scene?.name || 'scene';
  addNode({
    id: sceneId,
    label: sceneName,
    category: 'stage',
    kind: 'scene',
    detail: {
      process_type: ontology?.scene?.process_type || null,
      production_goal: ontology?.scene?.production_goal || null,
      ontology_version: ontology.ontology_version || null,
      objectives: ontology?.scene?.objectives || [],
    },
  });

  // ── 1. signals（核心节点） ──
  const signalIds = new Set();
  for (const bucket of SIGNAL_BUCKETS) {
    for (const sig of Array.isArray(signals[bucket]) ? signals[bucket] : []) {
      if (!sig) continue;
      const id = String(sig.column || sig.name || '').trim();
      if (!id) continue;
      const role = signalRole(sig, bucket);
      const category = ROLE_COLOR_KEY[role] || (bucket === 'events' ? 'event' : 'predictor');
      signalIds.add(id);
      addNode({
        id,
        label: sig.display_name ? `${id}\n${shortLabel(sig.display_name, 20)}` : id,
        name: sig.name || id,
        category,
        kind: 'signal',
        bucket,
        bucket_kind: BUCKET_KIND[bucket],
        role,
        symbol: GRAPH_PALETTE[category]?.symbol || 'circle',
        detail: {
          unit: sig.unit ?? null,
          physical_meaning: sig.physical_meaning ?? null,
          confidence: sig.physical_meaning_confidence ?? null,
          auto_inferred: sig.auto_inferred ?? null,
          governing_law: sig.governing_law ?? null,
          normal_range: sig.normal_range ?? null,
          target: sig.target ?? null,
          setpoint: sig.setpoint ?? null,
          behavior_match: sig.behavior_match ?? null,
          discrepancy_signal: sig.discrepancy_signal ?? null,
          knowledge_source: sig.knowledge_source ?? null,
          stage_ref: sig.stage_ref ?? null,
          equipment_ref: sig.equipment_ref ?? null,
          data_facts: sig.data_facts ?? null,
          description: sig.description ?? null,
        },
        refs: { stage: sig.stage_ref ?? null, equipment: sig.equipment_ref ?? null },
      });
    }
  }

  // ── 2. structure layer（equipment / stages / excluded columns） ──
  const stageIds = new Map();
  const equipmentIds = new Map();
  if (layers.structure) {
    for (const eq of Array.isArray(ontology?.scene?.equipment) ? ontology.scene.equipment : []) {
      const id = `equipment::${eq?.id || eq?.name || 'unnamed'}`;
      equipmentIds.set(eq?.id || eq?.name, id);
      const node = addNode({
        id, label: eq?.name || eq?.id || '设备', category: 'equipment', kind: 'equipment',
        symbol: GRAPH_PALETTE.equipment.symbol,
        detail: { type: eq?.type ?? null, function: eq?.function ?? null, location: eq?.location ?? null, manufacturer: eq?.manufacturer ?? null, model: eq?.model ?? null, evidence: eq?.evidence ?? null },
      });
      addEdge({ id: `${sceneId}~${id}`, source: sceneId, target: id, type: 'part_of', relation: 'scene', label: '包含', color: '#4b5563', width: 1, dashed: false });
    }
    const stages = (Array.isArray(ontology?.scene?.stages) ? ontology.scene.stages : [])
      .slice().sort((a, b) => (a?.sequence ?? 0) - (b?.sequence ?? 0));
    for (const st of stages) {
      const id = `stage::${st?.id || st?.name || 'unnamed'}`;
      stageIds.set(st?.id || st?.name, id);
      const node = addNode({
        id, label: st?.name || st?.id || '阶段', category: 'stage', kind: 'stage',
        symbol: GRAPH_PALETTE.stage.symbol, sequence: st?.sequence ?? null,
        detail: {
          typical_duration: st?.typical_duration ?? null,
          key_physics: st?.key_physics ?? null,
          governing_equations: st?.governing_equations ?? [],
          observed_behavior: st?.observed_behavior ?? null,
          confidence: st?.confidence ?? null,
        },
      });
      addEdge({ id: `${sceneId}~${id}`, source: sceneId, target: id, type: 'part_of', relation: 'scene', label: '包含', color: '#4b5563', width: 1, dashed: false });
      for (const kp of Array.isArray(st?.key_parameters) ? st.key_parameters : []) {
        if (signalIds.has(kp)) {
          addEdge({ id: `${id}~${kp}`, source: kp, target: id, type: 'member_of', relation: 'stage', label: '属于阶段', color: '#3d4a63', width: 1, dashed: true });
        }
      }
    }
    // 未在 stages 中登记的 stage_ref / equipment_ref → 建占位节点（如实呈现悬空引用）
    for (const n of nodes) {
      if (n.kind !== 'signal') continue;
      const { stage, equipment } = n.refs;
      if (stage && !stageIds.has(stage)) {
        const id = `stage::${stage}`;
        stageIds.set(stage, id);
        addNode({ id, label: `${stage} (未登记)`, category: 'stage', kind: 'stage', symbol: GRAPH_PALETTE.stage.symbol, unresolved_ref: true, detail: {} });
      }
      if (equipment && !equipmentIds.has(equipment)) {
        const id = `equipment::${equipment}`;
        equipmentIds.set(equipment, id);
        addNode({ id, label: `${equipment} (未登记)`, category: 'equipment', kind: 'equipment', symbol: GRAPH_PALETTE.equipment.symbol, unresolved_ref: true, detail: {} });
      }
      if (equipment && equipmentIds.has(equipment)) {
        addEdge({ id: `${equipmentIds.get(equipment)}~${n.id}`, source: equipmentIds.get(equipment), target: n.id, type: 'observes', relation: 'equipment', label: '采集', color: '#2f6f57', width: 1, dashed: true });
      }
      if (stage && stageIds.has(stage)) {
        addEdge({ id: `${stageIds.get(stage)}~${n.id}`, source: n.id, target: stageIds.get(stage), type: 'member_of', relation: 'stage', label: '属于阶段', color: '#3d4a63', width: 1, dashed: true });
      }
    }
  }

  // ── 3. relationships layer（语义边） ──
  if (layers.relationships) {
    for (const rel of Array.isArray(ontology.relationships) ? ontology.relationships : []) {
      if (!rel?.from || !rel?.to) continue;
      const style = REL_STYLE[rel.type] || { color: '#94a3b8', label: rel.type || '关系', dashed: true };
      const strength = REL_STRENGTH_WIDTH[rel.strength] || 1.8;
      const inferred = rel.inferred === true;
      const exists = (id) => signalIds.has(id) || byId.has(id);
      if (!exists(rel.from) || !exists(rel.to)) {
        unresolved.push({
          from: rel.from, to: rel.to, type: rel.type || null,
          reason: !exists(rel.from) ? 'source_not_a_signal' : 'target_not_a_signal',
        });
        continue;
      }
      addEdge({
        id: `rel::${rel.from}->${rel.to}`,
        source: rel.from,
        target: rel.to,
        type: rel.type || 'unspecified',
        relation: 'relationship',
        label: rel.type ? `${style.label}${rel.strength ? `·${rel.strength}` : ''}` : null,
        color: style.color,
        width: strength,
        dashed: inferred || style.dashed,
        arrow: true,
        detail: {
          strength: rel.strength ?? null,
          mechanism: rel.mechanism ?? null,
          governing_equation: rel.governing_equation ?? null,
          predicted_functional_form: rel.predicted_functional_form ?? null,
          time_lag: rel.time_lag ?? null,
          optimal_lag: rel.optimal_lag ?? null,
          lag_agreement: rel.lag_agreement ?? null,
          lag_discrepancy_note: rel.lag_discrepancy_note ?? null,
          lag_compensated_correlation: rel.lag_compensated_correlation ?? null,
          lag_detection_method: rel.lag_detection_method ?? null,
          data_direction_validated: rel.data_direction_validated ?? null,
          rag_validated: rel.rag_validated ?? null,
          inferred,
          evidence: rel.evidence ?? null,
          uncertainty: rel.uncertainty ?? null,
          stage2_queue: rel.stage2_queue ?? null,
        },
      });
    }
    // 混杂因子：变量 ↔ 其影响的信号（ontology 未显式给边，用 parameter_groups 反查；否则仅在 knowledge 层呈现）
    if (!layers.knowledge) {
      for (const c of Array.isArray(ontology.confounders) ? ontology.confounders : []) {
        const v = String(c?.variable || '').trim();
        const hit = [...signalIds].find((id) => v.includes(id));
        if (hit) addEdge({ id: `conf::${hit}`, source: hit, target: sceneId, type: 'confound', relation: 'confounder', label: '混杂', color: '#f5b544', width: 1.2, dashed: true, arrow: true, detail: { why: c?.why ?? null, controlled: c?.controlled ?? null } });
      }
    }
  }

  // ── 4. knowledge layer ──
  if (layers.knowledge) {
    for (const [i, p] of (Array.isArray(ontology.physical_principles) ? ontology.physical_principles : []).entries()) {
      const id = `principle::${i}`;
      addNode({
        id, label: shortLabel(p?.principle, 26), category: 'principle', kind: 'principle',
        symbol: GRAPH_PALETTE.principle.symbol,
        detail: { principle: p?.principle ?? null, equation: p?.equation ?? null, direction: p?.direction ?? null, parameters: p?.parameters ?? [] },
      });
      for (const col of Array.isArray(p?.parameters) ? p.parameters : []) {
        if (signalIds.has(col)) addEdge({ id: `${id}~${col}`, source: id, target: col, type: 'governs', relation: 'principle', label: '支配', color: '#c9a227', width: 1.4, dashed: true, arrow: true });
      }
    }
    for (const [i, m] of (Array.isArray(ontology.known_failure_modes) ? ontology.known_failure_modes : []).entries()) {
      const id = `failure::${i}`;
      addNode({
        id, label: shortLabel(m?.mode, 26), category: 'failure_mode', kind: 'failure_mode',
        symbol: GRAPH_PALETTE.failure_mode.symbol,
        detail: { mode: m?.mode ?? null, signature: m?.signature ?? null, relevance: m?.relevance ?? null, source: m?.source ?? null },
      });
      for (const col of signalIds) {
        if (String(m?.signature || '').includes(col) || String(m?.relevance || '').includes(col)) {
          addEdge({ id: `${id}~${col}`, source: id, target: col, type: 'manifests_as', relation: 'failure_mode', label: '表现为', color: '#e06c9f', width: 1.2, dashed: true, arrow: true });
        }
      }
    }
    for (const d of (Array.isArray(ontology.discrepancy_signals) ? ontology.discrepancy_signals : [])) {
      const id = `discrepancy::${d?.id || Math.random().toString(36).slice(2, 8)}`;
      addNode({
        id, label: `${d?.id || 'DS'} ${shortLabel(d?.type, 20)}`, category: 'discrepancy', kind: 'discrepancy',
        symbol: GRAPH_PALETTE.discrepancy.symbol,
        detail: { type: d?.type ?? null, severity: d?.severity ?? null, expectation: d?.ontology_expectation ?? null, observation: d?.data_observation ?? null, meaning: d?.diagnostic_meaning ?? null, columns: d?.columns ?? [] },
      });
      for (const col of Array.isArray(d?.columns) ? d.columns : []) {
        if (signalIds.has(col)) addEdge({ id: `${id}~${col}`, source: id, target: col, type: 'flags', relation: 'discrepancy', label: '标记', color: '#ff6b6b', width: 1.4, dashed: true, arrow: true });
      }
    }
    for (const c of (Array.isArray(ontology.confounders) ? ontology.confounders : [])) {
      const v = String(c?.variable || '').trim();
      const hit = [...signalIds].find((id) => v.includes(id));
      if (hit) addEdge({ id: `conf::${hit}`, source: hit, target: sceneId, type: 'confound', relation: 'confounder', label: '混杂', color: '#f5b544', width: 1.2, dashed: true, arrow: true, detail: { why: c?.why ?? null, controlled: c?.controlled ?? null } });
    }
    for (const [gname, members] of Object.entries(ontology.parameter_groups || {})) {
      const id = `group::${gname}`;
      addNode({ id, label: gname, category: 'group', kind: 'group', symbol: GRAPH_PALETTE.group.symbol, detail: { members: members || [] } });
      const memberIds = [];
      for (const col of Array.isArray(members) ? members : []) {
        if (signalIds.has(col)) {
          memberIds.push(col);
          addEdge({ id: `${id}~${col}`, source: id, target: col, type: 'groups', relation: 'parameter_group', label: '分组', color: '#5b6b8c', width: 1, dashed: true });
        }
      }
      groups.push({ id, label: gname, kind: 'parameter_group', members: memberIds });
    }
  }

  // parameter_groups 始终作为「组」输出（前端可用于着色/聚类，即使 knowledge 层关闭）
  if (!layers.knowledge) {
    for (const [gname, members] of Object.entries(ontology.parameter_groups || {})) {
      const memberIds = (Array.isArray(members) ? members : []).filter((c) => signalIds.has(c));
      if (memberIds.length) groups.push({ id: `group::${gname}`, label: gname, kind: 'parameter_group', members: memberIds });
    }
  }

  // ── 5. 派生标记：孤立节点 ──
  const degree = new Map();
  for (const e of edges) {
    degree.set(e.source, (degree.get(e.source) || 0) + 1);
    degree.set(e.target, (degree.get(e.target) || 0) + 1);
  }
  for (const n of nodes) n.degree = degree.get(n.id) || 0;

  const categories = [...usedCategories].map((c) => ({
    name: c,
    ...(GRAPH_PALETTE[c] || { color: '#94a3b8', symbol: 'circle', label: c }),
  }));

  const orphanSignals = nodes.filter((n) => n.kind === 'signal' && n.degree === 0).map((n) => n.id);
  const unresolvedRefs = nodes.filter((n) => n.unresolved_ref).map((n) => n.id);

  return {
    nodes,
    edges,
    groups,
    categories,
    unresolved,
    orphan_signals: orphanSignals,
    unresolved_refs: unresolvedRefs,
    layers,
    empty: nodes.length === 0,
  };
}

// ────────────────────────── 图算法（健康面板 / 影响分析） ──────────────────────────

/**
 * Tarjan 强连通分量 —— 因果子图必须是有向无环图；SCC 大小 > 1 即存在因果环
 * （要么是建模错误，要么是未显式处理的反馈回路）。
 * @returns {{id:string[], size:number}[]} 仅返回 size>1 的分量
 */
export function findCycles(nodeIds, edges) {
  const adj = new Map();
  for (const id of nodeIds) adj.set(id, []);
  for (const e of edges) {
    if (adj.has(e.source) && adj.has(e.target)) adj.get(e.source).push(e.target);
  }
  let index = 0;
  const idx = new Map();
  const low = new Map();
  const onStack = new Set();
  const stack = [];
  const cycles = [];

  const strongConnect = (v) => {
    idx.set(v, index);
    low.set(v, index);
    index++;
    stack.push(v);
    onStack.add(v);
    for (const w of adj.get(v) || []) {
      if (!idx.has(w)) {
        strongConnect(w);
        low.set(v, Math.min(low.get(v), low.get(w)));
      } else if (onStack.has(w)) {
        low.set(v, Math.min(low.get(v), idx.get(w)));
      }
    }
    if (low.get(v) === idx.get(v)) {
      const comp = [];
      let w;
      do {
        w = stack.pop();
        onStack.delete(w);
        comp.push(w);
      } while (w !== v);
      if (comp.length > 1) cycles.push({ id: comp, size: comp.length });
    }
  };
  for (const id of nodeIds) if (!idx.has(id)) strongConnect(id);
  return cycles;
}

/** 从某节点出发的 BFS 影响面（下游 / 上游），用于「影响分析」面板。 */
export function impactAnalysis(ontology, nodeId, { direction = 'downstream', maxDepth = 8 } = {}) {
  const edges = (Array.isArray(ontology?.relationships) ? ontology.relationships : [])
    .filter((r) => r?.from && r?.to)
    .map((r) => ({ source: r.from, target: r.to, type: r.type || 'unspecified' }));
  const adj = new Map();
  const push = (k, v) => { if (!adj.has(k)) adj.set(k, []); adj.get(k).push(v); };
  for (const e of edges) {
    if (direction === 'downstream') push(e.source, { id: e.target, via: e });
    else push(e.target, { id: e.source, via: e });
  }
  const seen = new Set([nodeId]);
  let frontier = [nodeId];
  const levels = [];
  for (let d = 0; d < maxDepth && frontier.length; d++) {
    const next = [];
    const hits = [];
    for (const cur of frontier) {
      for (const { id, via } of adj.get(cur) || []) {
        if (seen.has(id)) continue;
        seen.add(id);
        next.push(id);
        hits.push({ id, via: `${via.source}→${via.target}`, type: via.type });
      }
    }
    if (hits.length) levels.push({ depth: d + 1, nodes: hits });
    frontier = next;
  }
  return { root: nodeId, direction, levels, reachable: seen.size - 1 };
}

/** RFC 6901 转义：`~` → `~0` 先做，再 `/` → `~1`（顺序不可交换）。
 *  信号列名可能含 `/`（IRI 形态），不转义就会指错位置。 */
function escapePointerSegment(seg) {
  return String(seg).replace(/~/g, '~0').replace(/\//g, '~1');
}

/** `$.a.b[3].c`（validate.mjs 风格）→ `/a/b/3/c`（RFC 6901 JSON Pointer）。
 *  让校验错误与 RFC 6902 补丁共享同一坐标系：一条错误可以就地渲染为字段错误，
 *  也可以机械地转成一个修复补丁。 */
export function toJsonPointer(path) {
  const s = String(path ?? '');
  if (!s.startsWith('$')) return s;
  const rest = s.slice(1);
  if (!rest) return '';
  const segs = [];
  // 先按 `.` 切，再把每段里的 `[n]` 展开成独立段 —— 顺序不可颠倒，
  // 否则 `process_parameters[0]` 会被整体当成一段并被 `/` 转义成 `process_parameters~10`。
  for (const dotSeg of rest.split('.')) {
    if (dotSeg === '') continue;
    for (const part of dotSeg.split(/\[(\d+)\]/)) {
      if (part !== '') segs.push(part);
    }
  }
  return segs.map((seg) => `/${escapePointerSegment(seg)}`).join('');
}

// ────────────────────────── 质量度量（模型健康面板） ──────────────────────────

const ALL_BUCKETS = ['inspection_signals', 'process_parameters', 'control_variables', 'events', 'metadata_columns'];

/**
 * 计算本体模型健康度量。
 * 每条度量都可解释、可复算（见 `issues` —— 可执行的修复建议）。
 */
export function computeMetrics(ontology, { validation = null, graph = null } = {}) {
  if (!ontology || typeof ontology !== 'object') {
    return { available: false, reason: 'ontology is not an object' };
  }
  const signals = ontology.signals || {};
  const all = [];
  const seenColumns = new Map();
  const duplicates = [];
  for (const bucket of ALL_BUCKETS) {
    for (const s of Array.isArray(signals[bucket]) ? signals[bucket] : []) {
      if (!s) continue;
      const col = s.column || s.name;
      all.push({ ...s, __bucket: bucket });
      if (col) {
        if (seenColumns.has(col)) duplicates.push({ column: col, buckets: [seenColumns.get(col), bucket] });
        else seenColumns.set(col, bucket);
      }
    }
  }
  const numeric = all.filter((s) => s.__bucket !== 'events' && s.__bucket !== 'metadata_columns');
  const rels = Array.isArray(ontology.relationships) ? ontology.relationships : [];
  const sigCols = new Set(numeric.map((s) => s.column || s.name).filter(Boolean));
  const g = graph || buildGraph(ontology);

  const ratio = (n, d) => (d > 0 ? Math.round((n / d) * 1000) / 1000 : null);

  const knownSemantics = numeric.filter((s) => s.physical_meaning_confidence === 'KNOWN').length;
  const inferredSemantics = numeric.filter((s) => s.physical_meaning_confidence === 'INFERRED' || s.auto_inferred === true).length;
  const unknownSemantics = numeric.filter((s) => !s.physical_meaning_confidence || s.physical_meaning_confidence === 'UNKNOWN').length;
  const withMeaningText = numeric.filter((s) => String(s.physical_meaning || '').trim().length > 0).length;
  const withUnit = numeric.filter((s) => String(s.unit || '').trim().length > 0).length;
  const withGoverningLaw = numeric.filter((s) => String(s.governing_law || '').trim().length > 0).length;
  const withExpectedBehavior = numeric.filter((s) => String(s.expected_data_behavior || '').trim().length > 0).length;
  const withObservedBehavior = numeric.filter((s) => String(s.observed_data_behavior || '').trim().length > 0).length;
  const withRange = numeric.filter((s) => Array.isArray(s.normal_range) && s.normal_range.length === 2).length;
  const withEquipmentRef = numeric.filter((s) => String(s.equipment_ref || '').trim().length > 0).length;
  const withStageRef = numeric.filter((s) => String(s.stage_ref || '').trim().length > 0).length;

  const relTyped = rels.filter((r) => r?.type).length;
  const relWithMechanism = rels.filter((r) => String(r?.mechanism || '').trim().length > 0).length;
  const relWithEquation = rels.filter((r) => String(r?.governing_equation || '').trim().length > 0).length;
  const relInferred = rels.filter((r) => r?.inferred === true).length;
  const relValidatedByData = rels.filter((r) => r?.data_direction_validated === 'true').length;
  const relWithLag = rels.filter((r) => r?.optimal_lag?.steps !== undefined || String(r?.time_lag || '').trim().length > 0).length;

  const behavior = { CONSISTENT: 0, CONTRADICTED: 0, UNVERIFIED: 0, unspecified: 0 };
  for (const s of numeric) {
    if (s.behavior_match && behavior[s.behavior_match] !== undefined) behavior[s.behavior_match]++;
    else behavior.unspecified++;
  }
  const discrepancy = { HIGH: 0, MEDIUM: 0, LOW: 0, INFO: 0, unspecified: 0 };
  for (const d of Array.isArray(ontology.discrepancy_signals) ? ontology.discrepancy_signals : []) {
    const sev = String(d?.severity || '').toUpperCase();
    if (discrepancy[sev] !== undefined) discrepancy[sev]++;
    else discrepancy.unspecified++;
  }

  const possibleEdges = sigCols.size > 1 ? (sigCols.size * (sigCols.size - 1)) / 2 : 0;
  // 只统计真正连到信号节点的语义边
  const semanticEdges = g.edges.filter((e) => e.relation === 'relationship').length;
  const orphans = g.nodes.filter((n) => n.kind === 'signal' && n.degree === 0).map((n) => n.id);

  // ── 图拓扑：因果环 / 度分布 / 矛盾聚集（研究结论：这三项最能揭示模型结构错误） ──
  const causalEdges = rels
    .filter((r) => r?.from && r?.to && sigCols.has(r.from) && sigCols.has(r.to))
    .map((r) => ({ source: r.from, target: r.to, type: r.type || 'unspecified' }));
  const causalCycles = findCycles([...sigCols], causalEdges);
  const degrees = [...sigCols].map((id) => g.nodes.find((n) => n.id === id)?.degree || 0);
  const meanDegree = degrees.length ? degrees.reduce((a, b) => a + b, 0) / degrees.length : 0;
  const variance = degrees.length
    ? degrees.reduce((a, b) => a + (b - meanDegree) ** 2, 0) / degrees.length : 0;
  const sd = Math.sqrt(variance);
  const degreeOutliers = sd > 0
    ? [...sigCols].filter((id) => {
      const d = g.nodes.find((n) => n.id === id)?.degree || 0;
      return d > meanDegree + 2 * sd;
    })
    : [];

  // 矛盾聚集：CONTRADICTED 信号是否集中在同一 stage（聚集 → 阶段模型本身有问题）
  const contradicted = numeric.filter((s) => s.behavior_match === 'CONTRADICTED');
  const byStage = {};
  for (const s of contradicted) {
    const key = s.stage_ref || '(未绑定阶段)';
    byStage[key] = (byStage[key] || 0) + 1;
  }
  const contradictionClusters = Object.entries(byStage)
    .filter(([, n]) => n >= 2)
    .map(([stage, n]) => ({ stage, count: n }));
  const stageCounts = {};
  for (const s of numeric) {
    const key = s.stage_ref || '(未绑定阶段)';
    stageCounts[key] = (stageCounts[key] || 0) + 1;
  }

  const lagged = rels.filter((r) => r?.optimal_lag?.steps !== undefined || String(r?.time_lag || '').trim());
  const lagConsistent = lagged.filter((r) => r?.lag_agreement === 'consistent' || r?.optimal_lag?.consistent === true);
  const confoundersTotal = Array.isArray(ontology.confounders) ? ontology.confounders.length : 0;
  const confoundersControlled = (Array.isArray(ontology.confounders) ? ontology.confounders : [])
    .filter((c) => c?.controlled === true).length;
  const equationsChecked = (Array.isArray(ontology.physical_principles) ? ontology.physical_principles : [])
    .filter((p) => Array.isArray(p?.parameters) && p.parameters.length > 0);
  const equationsValid = equationsChecked.filter((p) => !p.equation || p.parameters.some((x) => String(p.equation).includes(x)));

  const metrics = {
    available: true,
    scale: {
      signals_total: all.length,
      numeric_signals: numeric.length,
      by_bucket: Object.fromEntries(ALL_BUCKETS.map((b) => [b, (Array.isArray(signals[b]) ? signals[b].length : 0)])),
      by_role: all.reduce((acc, s) => { const r = s.role || s.__bucket; acc[r] = (acc[r] || 0) + 1; return acc; }, {}),
      equipment: Array.isArray(ontology?.scene?.equipment) ? ontology.scene.equipment.length : 0,
      stages: Array.isArray(ontology?.scene?.stages) ? ontology.scene.stages.length : 0,
      relationships: rels.length,
      confounders: Array.isArray(ontology.confounders) ? ontology.confounders.length : 0,
      parameter_groups: Object.keys(ontology.parameter_groups || {}).length,
      physical_principles: Array.isArray(ontology.physical_principles) ? ontology.physical_principles.length : 0,
      known_failure_modes: Array.isArray(ontology.known_failure_modes) ? ontology.known_failure_modes.length : 0,
      discrepancy_signals: Array.isArray(ontology.discrepancy_signals) ? ontology.discrepancy_signals.length : 0,
      excluded_columns: Array.isArray(ontology.excluded_columns) ? ontology.excluded_columns.length : 0,
    },
    semantic_coverage: {
      known: knownSemantics, inferred: inferredSemantics, unknown: unknownSemantics,
      known_ratio: ratio(knownSemantics, numeric.length),
      described_ratio: ratio(withMeaningText, numeric.length),
      unit_ratio: ratio(withUnit, numeric.length),
      range_ratio: ratio(withRange, numeric.length),
      governing_law_ratio: ratio(withGoverningLaw, numeric.length),
      expected_behavior_ratio: ratio(withExpectedBehavior, numeric.length),
      observed_behavior_ratio: ratio(withObservedBehavior, numeric.length),
      equipment_binding_ratio: ratio(withEquipmentRef, numeric.length),
      stage_binding_ratio: ratio(withStageRef, numeric.length),
    },
    relationship_quality: {
      total: rels.length,
      typed_ratio: ratio(relTyped, rels.length),
      mechanism_ratio: ratio(relWithMechanism, rels.length),
      equation_ratio: ratio(relWithEquation, rels.length),
      data_validated_ratio: ratio(relValidatedByData, rels.length),
      lag_documented_ratio: ratio(relWithLag, rels.length),
      inferred_count: relInferred,
      inferred_ratio: ratio(relInferred, rels.length),
      density: possibleEdges > 0 ? Math.round((semanticEdges / possibleEdges) * 1000) / 1000 : null,
      semantic_edges: semanticEdges,
      by_type: rels.reduce((acc, r) => { const t = r?.type || 'unspecified'; acc[t] = (acc[t] || 0) + 1; return acc; }, {}),
    },
    consistency: {
      behavior,
      discrepancy,
      dangling_relationships: g.unresolved.length,
      orphan_signals: orphans.length,
      orphan_signal_columns: orphans.slice(0, 50),
      duplicate_columns: duplicates,
      unresolved_refs: g.unresolved_refs.length,
    },
  };

  // ── findings：SHACL sh:ValidationResult 形状的统一缺陷记录 ──
  // 契约 {code, severity, focusNode, path, value, sourceRule, message, hint, justification}
  // severity 三级 Critical/Important/Minor ↔ sh:Violation/sh:Warning/sh:Info（W3C SHACL 2017）。
  // 同一记录同时服务校验面板、健康面板与 API —— 一处产出，多处消费。
  const findings = [];
  const add = (severity, code, sourceRule, message, extra = {}) => findings.push({
    code, severity, sourceRule, message,
    focusNode: extra.focusNode ?? null,
    path: extra.path ?? null,
    pointer: extra.path ? toJsonPointer(extra.path) : null,
    value: extra.value ?? null,
    hint: extra.hint ?? null,
    justification: extra.justification ?? [],
  });

  if (g.unresolved.length > 0) {
    add('critical', 'DANGLING_RELATIONSHIP', 'referential-integrity',
      `${g.unresolved.length} 条关系的端点不是本体中的信号列`,
      {
        focusNode: g.unresolved[0].to,
        path: `relationships[${rels.findIndex((r) => r?.to === g.unresolved[0].to)}].to`,
        value: g.unresolved[0].to,
        hint: `检查 relationships[].from/to 是否与 signals 的 column 一致：${g.unresolved.slice(0, 3).map((u) => `${u.from}→${u.to}`).join(', ')}`,
        // 最小断言子集：把每条悬空关系本身列为致因（其余本体断言不足以蕴含该缺陷）
        justification: g.unresolved.slice(0, 5).map((u) => `relationships: ${u.from} → ${u.to} (${u.reason})`),
      });
  }
  if (duplicates.length > 0) {
    add('critical', 'DUPLICATE_COLUMN', 'consistency',
      `${duplicates.length} 个列在多个信号桶中重复登记`,
      {
        focusNode: duplicates[0].column,
        path: `signals.${duplicates[0].buckets[1]}`,
        value: duplicates[0].column,
        hint: duplicates.slice(0, 3).map((d) => `${d.column} (${d.buckets.join(' / ')})`).join('; '),
        justification: duplicates.slice(0, 5).map((d) => `${d.column} 同时登记于 ${d.buckets.join(' 与 ')}`),
      });
  }
  if (causalCycles.length > 0) {
    add('critical', 'CAUSAL_CYCLE', 'consistency',
      `因果子图存在 ${causalCycles.length} 个环（强连通分量）`,
      {
        focusNode: causalCycles[0].id[0],
        hint: '因果关系必须构成 DAG；出现环意味着建模错误或未显式处理的反馈回路',
        justification: causalCycles.slice(0, 3).map((c) => `环成员: ${c.id.join(' → ')}`),
      });
  }
  if (unknownSemantics > 0) {
    add('important', 'UNKNOWN_SEMANTICS', 'ontology-quality',
      `${unknownSemantics}/${numeric.length} 个数值信号的物理含义置信度为 UNKNOWN`,
      {
        focusNode: numeric.find((s) => !s.physical_meaning_confidence || s.physical_meaning_confidence === 'UNKNOWN')?.column || null,
        hint: '下游诊断结论的置信度会被 UNKNOWN 语义限制；建议补充 physical_meaning 或标注 INFERRED + inference_basis',
      });
  }
  if (orphans.length > 0) {
    add('minor', 'ORPHAN_SIGNAL', 'ontology-quality',
      `${orphans.length} 个信号没有任何关系边`,
      {
        focusNode: orphans[0],
        hint: `孤立信号无法参与因果推理：${orphans.slice(0, 5).join(', ')}`,
      });
  }
  if (rels.length > 0 && relWithMechanism < rels.length) {
    add('important', 'MISSING_MECHANISM', 'ontology-quality',
      `${rels.length - relWithMechanism}/${rels.length} 条关系缺少 mechanism 物理机制描述`,
      { focusNode: rels.find((r) => !String(r?.mechanism || '').trim())?.from || null, hint: 'mechanism 是诊断阶段排除竞争假设的依据' });
  }
  if (withEquipmentRef < numeric.length) {
    add('minor', 'UNBOUND_EQUIPMENT', 'ontology-quality',
      `${numeric.length - withEquipmentRef}/${numeric.length} 个信号未绑定设备 (equipment_ref)`,
      { focusNode: numeric.find((s) => !String(s.equipment_ref || '').trim())?.column || null, hint: '缺失设备绑定会削弱跨设备故障的区分能力' });
  }
  if (contradictionClusters.length > 0) {
    add('important', 'CONTRADICTION_CLUSTER', 'consistency',
      `${contradictionClusters.length} 个阶段的 CONTRADICTED 信号聚集（同一阶段 ≥2 个）`,
      {
        focusNode: contradictionClusters[0].stage,
        hint: '若矛盾集中于同一阶段，问题更可能出在阶段模型（key_physics / 传感器归属）而非单个信号',
        justification: contradictionClusters.map((c) => `阶段 ${c.stage}: ${c.count} 个 CONTRADICTED 信号`),
      });
  }
  if (confoundersTotal > 0 && confoundersControlled < confoundersTotal) {
    add('important', 'UNCONTROLLED_CONFOUNDER', 'consistency',
      `${confoundersTotal - confoundersControlled}/${confoundersTotal} 个混杂因子未标记为已控制`,
      { hint: '未控制的混杂因子等于未排除的竞争假设' });
  }
  if (lagged.length > 0 && lagConsistent.length < lagged.length) {
    add('minor', 'LAG_UNVERIFIED', 'consistency',
      `${lagged.length - lagConsistent.length}/${lagged.length} 条含时滞的关系未取得滞后一致性`,
      { hint: '时滞一致性是反假相关门禁（lag_agreement / optimal_lag.consistent）' });
  }
  if (degreeOutliers.length > 0) {
    add('minor', 'DEGREE_OUTLIER', 'ontology-quality',
      `${degreeOutliers.length} 个信号的连接度超过均值 +2σ`,
      {
        focusNode: degreeOutliers[0],
        hint: `高度中心节点可能过度声称解释力：${degreeOutliers.slice(0, 5).join(', ')}`,
      });
  }
  if (equationsChecked.length > 0 && equationsValid.length < equationsChecked.length) {
    add('minor', 'EQUATION_MISMATCH', 'ontology-quality',
      `${equationsChecked.length - equationsValid.length} 条物理原理的方程未引用其自身声明的参数`,
      { hint: '悬空方程意味着没有任何变量实例化它' });
  }
  if (behavior.CONTRADICTED > 0) {
    add('minor', 'BEHAVIOR_CONTRADICTED', 'consistency',
      `${behavior.CONTRADICTED} 个信号的观测行为与物理预期矛盾 (CONTRADICTED)`,
      {
        focusNode: contradicted[0]?.column || null,
        hint: '这是首选诊断信号，请确认 discrepancy_signal 已填写',
      });
  }
  if (rels.length > 0 && relInferred === rels.length) {
    add('minor', 'ALL_RELATIONSHIPS_INFERRED', 'ontology-quality',
      '全部关系均为推断 (inferred: true)，无数据方向验证',
      { hint: 'Stage-2 统计学分析应回填 data_direction_validated' });
  }
  if (validation && !validation.ok) {
    for (const e of validation.errors.slice(0, 25)) {
      add('critical', 'CP2_SCHEMA_INVALID', 'json-schema',
        `[${e.path}] ${e.message}`,
        { path: e.path, hint: `schema: ${ONTOLOGY_SCHEMA_PATH}` });
    }
    if (validation.errors.length > 25) {
      add('critical', 'CP2_SCHEMA_INVALID', 'json-schema',
        `另有 ${validation.errors.length - 25} 条 schema 错误未逐条列出`,
        { hint: '使用 /api/ontology/validate 获取完整报告' });
    }
  }
  if (validation && validation.bytes < ONTOLOGY_MIN_BYTES) {
    add('critical', 'BELOW_MIN_BYTES', 'cp2-gate',
      `本体仅 ${validation.bytes}B，低于 CP-2 下限 ${ONTOLOGY_MIN_BYTES}B`,
      { hint: '本体过小将无法支撑诊断管线' });
  }

  // ── 评分：加权可解释（不是玄学分数） ──
  const w = [
    { key: 'cp2', weight: 25, value: validation ? (validation.ok ? 1 : 0) : 1 },
    { key: 'no_dangling', weight: 15, value: g.unresolved.length === 0 && duplicates.length === 0 && causalCycles.length === 0 ? 1 : 0 },
    { key: 'semantics', weight: 20, value: ratio(knownSemantics * 1 + inferredSemantics * 0.5, Math.max(1, numeric.length)) ?? 0 },
    { key: 'described', weight: 10, value: ratio(withMeaningText, Math.max(1, numeric.length)) ?? 0 },
    { key: 'mechanism', weight: 10, value: ratio(relWithMechanism, Math.max(1, rels.length)) ?? 0 },
    { key: 'binding', weight: 10, value: ratio(withEquipmentRef + withStageRef, Math.max(1, numeric.length * 2)) ?? 0 },
    { key: 'no_orphans', weight: 10, value: numeric.length === 0 ? 0 : 1 - (orphans.length / numeric.length) },
  ];
  const score = Math.round(w.reduce((sum, x) => sum + x.weight * Math.max(0, Math.min(1, x.value)), 0));
  const grade = score >= 90 ? 'A' : score >= 80 ? 'B' : score >= 70 ? 'C' : score >= 60 ? 'D' : 'E';

  return {
    ...metrics,
    // 图拓扑（研究结论：环 / 度分布 / 矛盾聚集最能揭示模型结构错误）
    topology: {
      causal_cycles: causalCycles.map((c) => ({ size: c.size, members: c.id })),
      causal_cycle_count: causalCycles.length,
      mean_degree: Math.round(meanDegree * 100) / 100,
      degree_sd: Math.round(sd * 100) / 100,
      degree_outliers: degreeOutliers,
      contradiction_clusters: contradictionClusters,
      stage_signal_counts: stageCounts,
      relationship_richness: ratio(semanticEdges, semanticEdges + (g.edges.length - semanticEdges)) ?? null,
      attribute_richness: ratio(
        withMeaningText + withUnit + withRange + withGoverningLaw,
        Math.max(1, numeric.length),
      ),
    },
    // 统一缺陷契约（SHACL sh:ValidationResult 形状）
    findings,
    finding_counts: findings.reduce((acc, f) => { acc[f.severity] = (acc[f.severity] || 0) + 1; return acc; }, { critical: 0, important: 0, minor: 0 }),
    health: {
      score,
      grade,
      breakdown: w.map((x) => ({ key: x.key, weight: x.weight, value: Math.round(Math.max(0, Math.min(1, x.value)) * 100) / 100, points: Math.round(x.weight * Math.max(0, Math.min(1, x.value))) })),
    },
    computed_at: new Date().toISOString(),
  };
}

// ────────────────────────── 版本差异 ──────────────────────────

/** 深比较两个 JSON 值 → 字段级差异列表。 */
function diffValue(a, b, path, out, { maxDepth = 6 } = {}) {
  if (a === b) return;
  const ta = a === null ? 'null' : Array.isArray(a) ? 'array' : typeof a;
  const tb = b === null ? 'null' : Array.isArray(b) ? 'array' : typeof b;
  if (ta !== tb) {
    out.push({ path, kind: 'changed', before: a, after: b });
    return;
  }
  if (ta === 'object') {
    const keys = new Set([...Object.keys(a || {}), ...Object.keys(b || {})]);
    for (const k of keys) {
      diffValue(a?.[k], b?.[k], `${path}.${k}`, out, { maxDepth });
    }
    return;
  }
  if (ta === 'array') {
    const na = a.length; const nb = b.length;
    if (na !== nb) {
      out.push({ path, kind: 'length', before: `${na} 项`, after: `${nb} 项` });
    }
    const n = Math.max(na, nb);
    for (let i = 0; i < n && out.length < 500; i++) {
      diffValue(a[i], b[i], `${path}[${i}]`, out, { maxDepth });
    }
    return;
  }
  out.push({ path, kind: 'changed', before: a, after: b, depth: path.split('.').length });
}

/** 关键列表结构按「列名」对齐比较（数组顺序不应产生噪声差异）。 */
function keyedDiff(before, after, keyFn, label, out) {
  const mapA = new Map((Array.isArray(before) ? before : []).map((x) => [keyFn(x), x]));
  const mapB = new Map((Array.isArray(after) ? after : []).map((x) => [keyFn(x), x]));
  const added = [...mapB.keys()].filter((k) => k && !mapA.has(k));
  const removed = [...mapA.keys()].filter((k) => k && !mapB.has(k));
  const changed = [];
  for (const [k, vb] of mapB) {
    const va = mapA.get(k);
    if (!va) continue;
    if (JSON.stringify(va) === JSON.stringify(vb)) continue;
    const fields = [];
    diffValue(va, vb, `${label}[${k}]`, fields);
    changed.push({ key: k, fields: fields.filter((f) => f.kind !== 'length').slice(0, 40) });
  }
  out.push({ label, added, removed, changed });
}

/**
 * 两个版本的结构化差异：按列名对齐信号，按 from→to 对齐关系。
 * @returns {{summary, signals, relationships, scene, top_level, fields}}
 */
export function diffOntologies(before, after) {
  const out = [];
  const sigKey = (s) => String(s?.column || s?.name || '').trim();
  const relKey = (r) => `${r?.from || '?'}→${r?.to || '?'}`;
  keyedDiff(
    ALL_BUCKETS.flatMap((b) => (Array.isArray(before?.signals?.[b]) ? before.signals[b] : [])),
    ALL_BUCKETS.flatMap((b) => (Array.isArray(after?.signals?.[b]) ? after.signals[b] : [])),
    sigKey, 'signals', out,
  );
  keyedDiff(before?.relationships, after?.relationships, relKey, 'relationships', out);
  keyedDiff(before?.scene?.equipment, after?.scene?.equipment, (e) => String(e?.id || e?.name || ''), 'equipment', out);
  keyedDiff(before?.scene?.stages, after?.scene?.stages, (s) => String(s?.id || s?.name || ''), 'stages', out);
  keyedDiff(before?.confounders, after?.confounders, (c) => String(c?.variable || ''), 'confounders', out);
  keyedDiff(before?.physical_principles, after?.physical_principles, (p) => String(p?.principle || ''), 'physical_principles', out);
  keyedDiff(before?.known_failure_modes, after?.known_failure_modes, (m) => String(m?.mode || ''), 'known_failure_modes', out);
  keyedDiff(before?.discrepancy_signals, after?.discrepancy_signals, (d) => String(d?.id || ''), 'discrepancy_signals', out);

  const sceneFields = [];
  diffValue(before?.scene, after?.scene, 'scene', sceneFields);
  const topFields = [];
  diffValue(before?.metadata, after?.metadata, 'metadata', topFields);

  const topKeys = [...new Set([...Object.keys(before || {}), ...Object.keys(after || {})])];
  const topLevel = topKeys.map((k) => ({
    key: k,
    status: !(k in (before || {})) ? 'added' : !(k in (after || {})) ? 'removed' : 'present',
  }));

  const summary = {
    signals_added: out.find((o) => o.label === 'signals')?.added.length || 0,
    signals_removed: out.find((o) => o.label === 'signals')?.removed.length || 0,
    signals_changed: out.find((o) => o.label === 'signals')?.changed.length || 0,
    relationships_added: out.find((o) => o.label === 'relationships')?.added.length || 0,
    relationships_removed: out.find((o) => o.label === 'relationships')?.removed.length || 0,
    relationships_changed: out.find((o) => o.label === 'relationships')?.changed.length || 0,
    scene_fields_changed: sceneFields.length,
    metadata_fields_changed: topFields.length,
    // identical = 字节级一致；structurally_identical = 按列名对齐后无语义差异（仅顺序不同）
    identical: JSON.stringify(before) === JSON.stringify(after),
    structurally_identical: out.every((o) => o.added.length === 0 && o.removed.length === 0 && o.changed.length === 0)
      && sceneFields.length === 0 && topFields.length === 0
      && topLevel.every((t) => t.status === 'present'),
  };
  return { summary, sections: out, scene: sceneFields.slice(0, 200), metadata: topFields.slice(0, 200), top_level: topLevel };
}

/** 取两个版本的差异（store 内）。 */
export function diffVersions(sceneKey, fromVersion, toVersion) {
  const a = readAsset(sceneKey, fromVersion);
  const b = readAsset(sceneKey, toVersion);
  if (!a) throw new OntologyError(404, 'ONTOLOGY_NOT_FOUND', `缺少 ${sceneKey} v${fromVersion}`);
  if (!b) throw new OntologyError(404, 'ONTOLOGY_NOT_FOUND', `缺少 ${sceneKey} v${toVersion}`);
  return {
    scene_key: sceneKey,
    from: { version: Number(fromVersion), created_at: a.entry.created_at, origin: a.entry.origin },
    to: { version: Number(toVersion), created_at: b.entry.created_at, origin: b.entry.origin },
    diff: diffOntologies(a.ontology, b.ontology),
  };
}

// ────────────────────────── 保存（编辑 → 新版本） ──────────────────────────

/**
 * 保存在线编辑的本体。
 *
 * 安全不变式：
 *  1. 先 CP-2 校验，失败 → 409 且不落盘（除非 force=true，此时条目 quality 记 'rejected' 供人工复核）
 *  2. 乐观并发：base_version 与当前最新版本不一致 → 409（除非 force=true）
 *  3. 永不覆盖历史版本：写入 v(N+1)，继承 schema_fp 保证 reuse 仍可命中
 */
export function saveAsset({
  sceneKey, ontology, baseVersion = null, force = false,
  title = null, tags = null, notes = null, quality = null, dataFile = null, author = null,
  expectedSha256 = null,
}) {
  if (!sceneKey) throw new OntologyError(400, 'SCENE_REQUIRED', 'scene_key 必填');
  // 场景键即目录名：必须先校验，否则错误会在文件系统层以 SAVE_FAILED 的形式浮现
  if (!/^[A-Za-z0-9._-]{3,64}$/.test(String(sceneKey))) {
    throw new OntologyError(400, 'SCENE_INVALID',
      `scene_key 不合法: ${JSON.stringify(sceneKey)}（仅允许 A-Z a-z 0-9 . _ -，长度 3-64）`);
  }
  const versions = readIndex().entries.filter((e) => e.scene_key === sceneKey).map((e) => e.version);
  const latest = versions.length ? Math.max(...versions) : 0;

  if (baseVersion !== null && baseVersion !== undefined && Number(baseVersion) !== latest && !force) {
    throw new OntologyError(409, 'VERSION_CONFLICT',
      `版本冲突：你基于 v${baseVersion} 编辑，但当前最新为 v${latest}；请重新加载或强制保存`,
      { base_version: Number(baseVersion), latest_version: latest });
  }

  // 内容哈希守卫（研究结论 7：Agent 与人在同一文件上协作，编辑页不得成为第二个静默事实源）。
  //
  // 语义对齐 RFC 9110 §13（条件请求）/ RFC 6585 §3（428 Precondition Required）：
  //   - 编辑既有版本时缺少前置条件 → 428（让"丢失更新"在结构上不可能，而不只是"可检测"）
  //   - 前置条件与磁盘不符 → 409 CONTENT_CHANGED（客户端须重新加载或显式 force）
  //   - 冲突时绝不静默重试：UI 必须呈现三方视图（base / mine / theirs）
  const baseEntry = (baseVersion !== null && baseVersion !== undefined) ? getEntry(sceneKey, baseVersion) : null;
  if (baseEntry && !force && !expectedSha256) {
    // 缺前置条件时把当前有效哈希一并告知客户端，便于其直接重试而不是盲目刷新
    const current = ensureContentHash(baseEntry);
    throw new OntologyError(428, 'PRECONDITION_REQUIRED',
      `保存既有版本必须携带内容前置条件（If-Match 头或 expected_sha256）；请重新加载资产后再保存`,
      { base_version: Number(baseVersion), current_sha256: current });
  }
  if (expectedSha256 && baseEntry && !force) {
    const actual = ensureContentHash(baseEntry);
    if (actual && actual !== expectedSha256) {
      throw new OntologyError(409, 'CONTENT_CHANGED',
        `基线版本 v${baseVersion} 的磁盘内容已在加载后被改写（可能由 Agent 或另一会话写入）；请重新加载后再保存`,
        { expected: expectedSha256, actual, base_version: Number(baseVersion) });
    }
  }

  const validation = validateOntology(ontology);
  if (!validation.ok && !force) {
    throw new OntologyError(422, 'VALIDATION_FAILED',
      `CP-2 校验未通过（${validation.errors.length} 个错误），未保存`,
      { errors: validation.errors, warnings: validation.warnings, bytes: validation.bytes });
  }

  const base = baseEntry;
  let result;
  try {
    result = addVersion({
      sceneKey,
      ontology,
      buildMode: 'edit',
      quality: quality || (validation.ok ? 'unvalidated' : 'rejected'),
      title, tags: tags || [], notes: notes || '',
      origin: author ? `user:${author}` : 'user',
      parentVersion: base ? base.version : null,
      inheritFrom: base,
      dataFile,
      provenance: {
        edit_of_version: base ? base.version : null,
        validation: { ok: validation.ok, errors: validation.errors.length, warnings: validation.warnings.length },
      },
    });
  } catch (err) {
    throw new OntologyError(400, 'SAVE_FAILED', err.message);
  }

  const asset = readAsset(sceneKey, result.version);
  return {
    ...result,
    validation,
    created_new_version: !result.deduped,
    metrics: computeMetrics(asset.ontology, { validation }),
  };
}

// ────────────────────────── run 目录候选（Agent 构建的本体） ──────────────────────────

/**
 * 发现「已构建但未入库/已入库」的 run 目录本体。
 * 这是 Agent(skill) 产物进入前端的桥：context-builder 写 RUN_DIR/01_ontology/ontology.json，
 * 正常路径会 publish 入 store；publish 失败或历史遗留的 run 仍在此被看见并可一键采纳。
 */
export function listCandidates({ limit = 200, includeInStore = true } = {}) {
  if (!existsSync(RUNS_DIR)) {
    return { runs_dir: RUNS_DIR, candidates: [], total: 0 };
  }
  const idx = readIndex();
  const storeByHash = new Map();
  for (const e of idx.entries) {
    try {
      const abs = join(STORE_DIR, e.path);
      if (existsSync(abs)) storeByHash.set(e.content_sha256 || hashOf(abs), e);
    } catch { /* ignore */ }
  }

  const dirs = readdirSync(RUNS_DIR, { withFileTypes: true })
    .filter((d) => d.isDirectory())
    .map((d) => d.name);

  const candidates = [];
  for (const name of dirs) {
    const runDir = join(RUNS_DIR, name);
    const ontologyPath = join(runDir, '01_ontology', 'ontology.json');
    if (!existsSync(ontologyPath)) continue;
    const stat = statSync(ontologyPath);
    let ontology = null;
    let parseError = null;
    try { ontology = JSON.parse(readFileSync(ontologyPath, 'utf-8')); } catch (e) { parseError = e.message; }
    const manifest = tryReadJson(join(runDir, 'run_manifest.json'));
    const inStore = storeByHash.get(hashOf(ontologyPath));
    // scene_key 必须是文件系统/URL 安全的 ASCII；本体内 scene.name 可能是中文描述，
    // 此时回退到 run 目录名（去时间戳前缀与 _rN 后缀），原始名保留在 scene_name。
    const fromRunName = name.replace(/^\d{10,}_/, '').replace(/_r\d+$/, '') || name;
    const proposedScene = deriveSceneKey(ontology?.scene?.name) || deriveSceneKey(fromRunName) || 'scene';
    const candidate = {
      run_dir: runDir,
      run_name: name,
      run_id: manifest?.run_id || name,
      display_name: manifest?.name || manifest?.scene_name || name,
      ontology_path: ontologyPath,
      bytes: stat.size,
      mtime: stat.mtime.toISOString(),
      scene_name: ontology?.scene?.name || null,
      proposed_scene: proposedScene,
      scene_key_from_run: deriveSceneKey(fromRunName),
      process_type: ontology?.scene?.process_type || null,
      parse_error: parseError,
      validation: parseError ? null : validateOntology(ontologyPath),
      summary: ontology ? summarizeOntology(ontology) : null,
      in_store: inStore ? { scene_key: inStore.scene_key, version: inStore.version } : null,
      adoptable: !inStore && !parseError,
    };
    if (!includeInStore && candidate.in_store) continue;
    candidates.push(candidate);
  }
  candidates.sort((a, b) => b.mtime.localeCompare(a.mtime));
  return {
    runs_dir: RUNS_DIR,
    total: candidates.length,
    adoptable: candidates.filter((c) => c.adoptable).length,
    candidates: candidates.slice(0, limit),
  };
}

function hashOf(abs) {
  return 'sha256:' + createHash('sha256').update(readFileSync(abs, 'utf-8')).digest('hex');
}

/**
 * 采纳一个 run 目录本体进入 store（publish 语义 + 显式 scene/元数据）。
 */
export function adoptCandidate({ runDir, runName, scene, title, tags, notes, quality = 'unvalidated', dataFile }) {
  const dir = runDir
    ? (isAbsolute(runDir) ? runDir : resolve(PROJECT_ROOT, runDir))
    : join(RUNS_DIR, runName || '');
  const ontologyPath = join(dir, '01_ontology', 'ontology.json');
  if (!existsSync(ontologyPath)) {
    throw new OntologyError(404, 'ONTOLOGY_NOT_FOUND', `run 目录下没有 01_ontology/ontology.json: ${dir}`);
  }
  const content = readFileSync(ontologyPath, 'utf-8');
  let parsed;
  try { parsed = JSON.parse(content); } catch (e) {
    throw new OntologyError(422, 'ONTOLOGY_INVALID_JSON', `ontology.json 不是合法 JSON: ${e.message}`);
  }
  const runBase = basename(dir).replace(/^\d{10,}_/, '').replace(/_r\d+$/, '') || basename(dir);
  const sceneKey = (scene ? deriveSceneKey(scene) : null)
    || deriveSceneKey(parsed?.scene?.name)
    || deriveSceneKey(runBase)
    || 'scene';

  // 指纹候选链与 publish 一致
  let inheritFrom = null;
  const candidates = [];
  if (dataFile) candidates.push(isAbsolute(dataFile) ? dataFile : join(PROJECT_ROOT, dataFile));
  try {
    const im = tryReadJson(join(dir, '00_input', 'input_manifest.json'));
    for (const f of (im?.files || im?.data_files || [])) {
      const p = typeof f === 'string' ? f : (f?.path || f?.absolute_path);
      if (p) candidates.push(isAbsolute(p) ? p : join(PROJECT_ROOT, p));
    }
  } catch { /* ignore */ }
  for (const c of candidates) {
    try {
      if (existsSync(c) && statSync(c).isFile() && /\.(csv|tsv)$/i.test(c)) {
        const fp = computeFingerprint(c);
        inheritFrom = { schema_fp: fp.schema_fp, content_fp: fp.content_fp, fingerprinted_from: c };
        break;
      }
    } catch { /* next */ }
  }

  const result = addVersion({
    sceneKey,
    ontology: content,
    buildMode: 'adopt',
    quality,
    title: title || parsed?.scene?.name || sceneKey,
    tags: tags || [], notes: notes || '',
    origin: 'agent',
    provenance: { built_from_run: parsed?.provenance?.run_id || basename(dir), adopted_from_run_dir: dir },
    inheritFrom,
  });
  return { ...result, scene_key: sceneKey, source_run_dir: dir };
}

// ────────────────────────── 复用推荐（前端） ──────────────────────────

export function recommend({ dataPath, scene } = {}) {
  let abs = null;
  if (dataPath) {
    abs = isAbsolute(dataPath) ? dataPath : join(PROJECT_ROOT, dataPath);
    if (!existsSync(abs)) throw new OntologyError(404, 'DATA_NOT_FOUND', `数据路径不存在: ${dataPath}`);
  }
  const result = recommendReuse({ dataPath: abs || undefined, scene: scene || undefined });
  // 补充可读的列信息，帮助用户判断「是否与场景高度相关」
  let columns = null;
  if (abs) {
    try {
      const fp = computeFingerprint(abs);
      columns = fp.columns;
    } catch (e) {
      columns = { error: e.message };
    }
  }
  return { ...result, data_path: abs, columns };
}

// ────────────────────────── 元数据补丁 / 删除 / 克隆 ──────────────────────────

export function patchAsset(sceneKey, version, patch) {
  try {
    return updateEntry(sceneKey, version, patch);
  } catch (err) { throw translateStoreError(err, 'PATCH_FAILED'); }
}

/** store 原语抛出的是普通 Error；翻译成带 HTTP 语义的 OntologyError。 */
function translateStoreError(err, fallbackCode) {
  const msg = err?.message || String(err);
  if (/not found/i.test(msg)) return new OntologyError(404, 'ONTOLOGY_NOT_FOUND', msg);
  if (/invalid/i.test(msg)) return new OntologyError(422, 'ONTOLOGY_INVALID', msg);
  return new OntologyError(500, fallbackCode, msg);
}

export function deleteVersion(sceneKey, version) {
  try {
    return removeVersion(sceneKey, version);
  } catch (err) { throw translateStoreError(err, 'DELETE_FAILED'); }
}

export function deleteScene(sceneKey) {
  try {
    return removeScene(sceneKey);
  } catch (err) { throw translateStoreError(err, 'DELETE_FAILED'); }
}

/** 克隆一个版本到另一个 scene_key（用于「以此为模板新建场景」）。 */
export function cloneAsset({ sceneKey, version, targetScene, title, tags }) {
  const src = readAsset(sceneKey, version);
  if (!src || src.missing) throw new OntologyError(404, 'ONTOLOGY_NOT_FOUND', `缺少 ${sceneKey} v${version}`);
  const target = String(targetScene || '').trim();
  if (!target) throw new OntologyError(400, 'TARGET_SCENE_REQUIRED', 'target_scene 必填');
  if (readIndex().entries.some((e) => e.scene_key === target)) {
    throw new OntologyError(409, 'SCENE_EXISTS', `场景已存在: ${target}（请换一个 key 或先删除）`);
  }
  const onto = JSON.parse(JSON.stringify(src.ontology));
  if (onto.scene && typeof onto.scene === 'object') onto.scene.name = target;
  const result = addVersion({
    sceneKey: target,
    ontology: onto,
    buildMode: 'clone',
    quality: 'unvalidated',
    title: title || target,
    tags: tags || src.entry.tags || [],
    notes: `克隆自 ${sceneKey} v${version}`,
    origin: 'user',
    inheritFrom: src.entry,
    provenance: { cloned_from: { scene_key: sceneKey, version: Number(version) } },
  });
  return result;
}
// ────────────────────────── 统计总览 ──────────────────────────

export function storeOverview() {
  const listing = listAssets();
  const scenes = listing.assets;
  const totals = {
    scenes: listing.scene_count,
    versions: listing.version_count,
    reuse_total: scenes.reduce((n, s) => n + s.total_reuse, 0),
    bytes: scenes.reduce((n, s) => n + s.bytes, 0),
    signals: scenes.reduce((n, s) => n + (s.summary?.signals || 0), 0),
    relationships: scenes.reduce((n, s) => n + (s.summary?.relationships || 0), 0),
    broken_scenes: scenes.filter((s) => s.broken).map((s) => s.scene_key),
  };
  return {
    store_dir: STORE_DIR,
    index_path: INDEX_PATH,
    schema_path: ONTOLOGY_SCHEMA_PATH,
    min_bytes: ONTOLOGY_MIN_BYTES,
    totals,
    by_quality: scenes.reduce((acc, s) => {
      for (const [q, n] of Object.entries(s.qualities)) acc[q] = (acc[q] || 0) + n;
      return acc;
    }, {}),
    by_origin: scenes.reduce((acc, s) => {
      for (const [o, n] of Object.entries(s.origins)) acc[o] = (acc[o] || 0) + n;
      return acc;
    }, {}),
    latest_updated_at: scenes.map((s) => s.updated_at).filter(Boolean).sort().pop() || null,
    scenes: scenes.map((s) => ({
      scene_key: s.scene_key, title: s.title, latest_version: s.latest_version,
      version_count: s.version_count, total_reuse: s.total_reuse, updated_at: s.updated_at,
      summary: s.summary, broken: s.broken, tags: s.tags,
    })),
  };
}

function tryReadJson(p) {
  try { return existsSync(p) ? JSON.parse(readFileSync(p, 'utf-8')) : null; } catch { return null; }
}

/** 把任意候选名归一化为文件系统/URL 安全的 scene_key；不可用时返回 null。
 *  严格到可以安全地直接用作目录名：不含路径分隔符、不以点开头、不含 `..`。 */
export function deriveSceneKey(raw) {
  const s = String(raw ?? '').trim();
  if (!s) return null;
  const ascii = s
    .replace(/[^A-Za-z0-9._-]+/g, '_')
    .replace(/\.{2,}/g, '_')      // 折叠 '..'（路径回溯）
    .replace(/_{2,}/g, '_')
    .replace(/^[._-]+|[._-]+$/g, '');
  if (ascii.length < 3) return null;
  if (ascii.includes('..')) return null;
  return ascii.slice(0, 64);
}

export { STORE_DIR, INDEX_PATH, ONTOLOGY_SCHEMA_PATH, ONTOLOGY_MIN_BYTES, RUNS_DIR, relative, resolve };
