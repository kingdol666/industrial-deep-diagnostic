// Ontology Routes — 本体资产控制 API（管理 / 可视化 / 编辑 / 复用 / 采纳）
//
// 契约：与项目其余 API 一致 —— 成功 `{success:true, data}`，失败 `{success:false, code, error, details?}。
// 所有写操作最终经 ontology_store.mjs（唯一写入口），因此前端管理页、Agent skill、
// 管线 fast-reuse 三条路径共享同一份持久化与同一套 CP-2 判据。

import { Router } from 'express';
import {
  OntologyError, listAssets, getAsset, buildGraph, computeMetrics,
  diffOntologies, diffVersions, saveAsset, patchAsset, deleteVersion, deleteScene,
  cloneAsset, listCandidates, adoptCandidate, recommend, storeOverview,
} from '../services/ontology.service.mjs';
import {
  listStore, validateOntology, ONTOLOGY_SCHEMA_PATH, ONTOLOGY_MIN_BYTES, STORE_DIR,
} from '../../../../.claude/shared/scripts/ontology_store.mjs';
import { readFileSync } from 'fs';

const router = Router();

function fail(res, err) {
  if (err instanceof OntologyError) {
    return res.status(err.status).json({
      success: false, code: err.code, error: err.message,
      ...(err.details ? { details: err.details } : {}),
    });
  }
  return res.status(500).json({ success: false, code: 'ONTOLOGY_INTERNAL_ERROR', error: err.message });
}

function ok(res, data, status = 200) {
  return res.status(status).json({ success: true, data });
}

// ════════════════════════ 兼容：原始索引 ════════════════════════

// GET /api/ontology/store — 原样返回 store 索引（保留给既有调用方）
router.get('/store', (_req, res) => {
  try { ok(res, listStore()); } catch (err) { fail(res, err); }
});

// ════════════════════════ 列表 / 总览 ════════════════════════

// GET /api/ontology/assets?scene=&quality=&q= — 按场景聚合的资产列表
router.get('/assets', (req, res) => {
  try {
    ok(res, listAssets({
      scene: req.query.scene || undefined,
      quality: req.query.quality || undefined,
      q: req.query.q || undefined,
    }));
  } catch (err) { fail(res, err); }
});

// GET /api/ontology/overview — 总览统计（首页卡片）
router.get('/overview', (_req, res) => {
  try { ok(res, storeOverview()); } catch (err) { fail(res, err); }
});

// GET /api/ontology/schema — 本体 JSON Schema + 路径常量（编辑器用）
router.get('/schema', (_req, res) => {
  try {
    ok(res, {
      schema_path: ONTOLOGY_SCHEMA_PATH,
      min_bytes: ONTOLOGY_MIN_BYTES,
      store_dir: STORE_DIR,
      schema: JSON.parse(readFileSync(ONTOLOGY_SCHEMA_PATH, 'utf-8')),
    });
  } catch (err) { fail(res, err); }
});

// ════════════════════════ 单资产 ════════════════════════

// GET /api/ontology/assets/:scene/:version — 本体全文 + 校验 + 度量 + 图
// 带强 ETag（RFC 9110 §8.8.3 / §13）：客户端 PUT 时必须回传 If-Match，
// 否则编辑页就会成为与 Agent 并行的第二个静默事实源。
router.get('/assets/:scene/:version', (req, res) => {
  try {
    const asset = getAsset(req.params.scene, Number(req.params.version), {
      withGraph: req.query.graph !== '0',
      withMetrics: req.query.metrics !== '0',
    });
    const etag = asset.entry?.content_sha256 || null;
    if (etag) res.set('ETag', `"${etag}"`);
    res.set('Cache-Control', 'no-cache');
    ok(res, { ...asset, etag });
  } catch (err) { fail(res, err); }
});

// GET /api/ontology/assets/:scene/:version/graph?structure=&relationships=&knowledge=
router.get('/assets/:scene/:version/graph', (req, res) => {
  try {
    const { ontology, entry } = getAsset(req.params.scene, Number(req.params.version), { withGraph: false, withMetrics: false });
    const layers = {
      structure: req.query.structure !== '0',
      relationships: req.query.relationships !== '0',
      knowledge: req.query.knowledge === '1',
    };
    ok(res, { scene_key: req.params.scene, version: entry.version, graph: buildGraph(ontology, { layers }) });
  } catch (err) { fail(res, err); }
});

// GET /api/ontology/assets/:scene/:version/metrics
router.get('/assets/:scene/:version/metrics', (req, res) => {
  try {
    const { ontology, validation, entry } = getAsset(req.params.scene, Number(req.params.version), { withGraph: false, withMetrics: false });
    ok(res, { scene_key: req.params.scene, version: entry.version, metrics: computeMetrics(ontology, { validation }) });
  } catch (err) { fail(res, err); }
});

// GET /api/ontology/assets/:scene/:version/validate — 只读 CP-2 报告
router.get('/assets/:scene/:version/validate', (req, res) => {
  try {
    const asset = getAsset(req.params.scene, Number(req.params.version), { withGraph: false, withMetrics: false });
    ok(res, { scene_key: req.params.scene, version: asset.version, ...asset.validation });
  } catch (err) { fail(res, err); }
});

// GET /api/ontology/assets/:scene/:version/provenance
router.get('/assets/:scene/:version/provenance', (req, res) => {
  try {
    const asset = getAsset(req.params.scene, Number(req.params.version), { withGraph: false, withMetrics: false });
    ok(res, { scene_key: req.params.scene, version: asset.version, provenance: asset.provenance, entry: asset.entry });
  } catch (err) { fail(res, err); }
});

// GET /api/ontology/diff?scene=&from=&to= — 版本差异
router.get('/diff', (req, res) => {
  try {
    const { scene, from, to } = req.query;
    if (!scene || from === undefined || to === undefined) {
      throw new OntologyError(400, 'PARAMS_REQUIRED', 'scene, from, to 均为必填');
    }
    ok(res, diffVersions(scene, Number(from), Number(to)));
  } catch (err) { fail(res, err); }
});

// ════════════════════════ 写入 ════════════════════════

// PUT /api/ontology/assets/:scene/:version — 保存编辑，生成新版本（v+1）
// 前置条件（二者其一，否则 428）：
//   If-Match: "<sha256>"  （RFC 9110 §13.1 强比较）
//   body.expected_sha256
// 前置条件不匹配 → 409 CONTENT_CHANGED；base_version 落后 → 409 VERSION_CONFLICT。
// 客户端拿到 409 时**不得静默重试**：须呈现 base / mine / theirs 三方差异。
router.put('/assets/:scene/:version', (req, res) => {
  try {
    const body = req.body || {};
    const ontology = body.ontology ?? body.ontology_json ?? null;
    if (!ontology || typeof ontology !== 'object') {
      throw new OntologyError(400, 'ONTOLOGY_REQUIRED', '请求体必须包含 ontology 对象');
    }
    // If-Match 优先于 body（HTTP 语义是权威）；允许 `*` 表示"存在即可"
    const ifMatch = req.get('If-Match');
    let expectedSha256 = body.expected_sha256 || body.expectedSha256 || null;
    if (ifMatch && ifMatch.trim() !== '*') {
      expectedSha256 = ifMatch.replace(/^W\//, '').replace(/^"|"$/g, '');
    }
    const result = saveAsset({
      sceneKey: req.params.scene,
      ontology,
      baseVersion: Number(req.params.version),
      force: body.force === true,
      title: body.title ?? null,
      tags: body.tags ?? null,
      notes: body.notes ?? null,
      quality: body.quality ?? null,
      dataFile: body.dataFile ?? null,
      author: req.user?.username || null,
      expectedSha256,
    });
    if (result.deduped) {
      const entry = getAsset(req.params.scene, result.version, { withGraph: false, withMetrics: false }).entry;
      if (entry?.content_sha256) res.set('ETag', `"${entry.content_sha256}"`);
    } else {
      const asset = getAsset(req.params.scene, result.version, { withGraph: false, withMetrics: false });
      if (asset.entry?.content_sha256) res.set('ETag', `"${asset.entry.content_sha256}"`);
    }
    ok(res, result, result.created_new_version ? 201 : 200);
  } catch (err) { fail(res, err); }
});

// POST /api/ontology/assets — 新建场景（不依赖 run 目录）
router.post('/assets', (req, res) => {
  try {
    const body = req.body || {};
    const sceneKey = String(body.scene_key || body.sceneKey || '').trim();
    if (!sceneKey) throw new OntologyError(400, 'SCENE_REQUIRED', 'scene_key 必填');
    const ontology = body.ontology || scaffoldOntology(sceneKey, body);
    const result = saveAsset({
      sceneKey,
      ontology,
      baseVersion: null,
      force: body.force === true,
      title: body.title || sceneKey,
      tags: body.tags || [],
      notes: body.notes || '',
      dataFile: body.dataFile || null,
      author: req.user?.username || null,
    });
    ok(res, result, 201);
  } catch (err) { fail(res, err); }
});

// PATCH /api/ontology/assets/:scene/:version — 仅元数据（title/tags/notes/quality）
router.patch('/assets/:scene/:version', (req, res) => {
  try {
    ok(res, patchAsset(req.params.scene, Number(req.params.version), req.body || {}));
  } catch (err) { fail(res, err); }
});

// POST /api/ontology/assets/:scene/:version/clone — 克隆到新场景
router.post('/assets/:scene/:version/clone', (req, res) => {
  try {
    const body = req.body || {};
    ok(res, cloneAsset({
      sceneKey: req.params.scene,
      version: Number(req.params.version),
      targetScene: body.target_scene || body.targetScene,
      title: body.title,
      tags: body.tags,
    }), 201);
  } catch (err) { fail(res, err); }
});

// DELETE /api/ontology/assets/:scene/:version — 删除单个版本
router.delete('/assets/:scene/:version', (req, res) => {
  try { ok(res, deleteVersion(req.params.scene, Number(req.params.version))); } catch (err) { fail(res, err); }
});

// DELETE /api/ontology/scenes/:scene — 删除整个场景
router.delete('/scenes/:scene', (req, res) => {
  try { ok(res, deleteScene(req.params.scene)); } catch (err) { fail(res, err); }
});

// ════════════════════════ 校验 / 图 / 度量（对任意载荷） ════════════════════════

// POST /api/ontology/validate — 保存前校验草稿（不落盘）
router.post('/validate', (req, res) => {
  try {
    const payload = req.body?.ontology ?? req.body;
    if (payload === undefined || payload === null) {
      throw new OntologyError(400, 'ONTOLOGY_REQUIRED', '请求体必须包含 ontology 对象');
    }
    const result = validateOntology(payload);
    ok(res, { ...result, metrics: result.ok || typeof payload === 'object' ? computeMetrics(payload, { validation: result }) : null });
  } catch (err) { fail(res, err); }
});

// POST /api/ontology/graph — 对任意本体（含未保存草稿）做图投影
router.post('/graph', (req, res) => {
  try {
    const payload = req.body?.ontology ?? req.body;
    const layers = {
      structure: req.body?.layers?.structure !== false,
      relationships: req.body?.layers?.relationships !== false,
      knowledge: req.body?.layers?.knowledge === true,
    };
    ok(res, { graph: buildGraph(payload, { layers }) });
  } catch (err) { fail(res, err); }
});

// POST /api/ontology/metrics — 对任意本体做健康度量
router.post('/metrics', (req, res) => {
  try {
    const payload = req.body?.ontology ?? req.body;
    ok(res, { metrics: computeMetrics(payload) });
  } catch (err) { fail(res, err); }
});

// POST /api/ontology/diff — 对任意两份本体做差异（离线对比 / 导入预览）
router.post('/diff', (req, res) => {
  try {
    const { before, after } = req.body || {};
    if (!before || !after) throw new OntologyError(400, 'PARAMS_REQUIRED', 'before 与 after 均为必填');
    ok(res, { diff: diffOntologies(before, after) });
  } catch (err) { fail(res, err); }
});

// ════════════════════════ 复用推荐 / 候选采纳 ════════════════════════

// POST /api/ontology/recommend — {dataPath?, scene?} → 是否存在高度相关的可复用本体
router.post('/recommend', (req, res) => {
  try {
    ok(res, recommend({ dataPath: req.body?.dataPath || req.body?.data_path, scene: req.body?.scene }));
  } catch (err) { fail(res, err); }
});

// GET /api/ontology/candidates — run 目录中已构建的本体（含未入库）
router.get('/candidates', (req, res) => {
  try {
    ok(res, listCandidates({
      includeInStore: req.query.include_in_store !== '0',
      limit: req.query.limit ? Number(req.query.limit) : 200,
    }));
  } catch (err) { fail(res, err); }
});

// POST /api/ontology/adopt — 把 run 目录本体采纳入库
router.post('/adopt', (req, res) => {
  try {
    const body = req.body || {};
    if (!body.runDir && !body.runName && !body.run_dir && !body.run_name) {
      throw new OntologyError(400, 'PARAMS_REQUIRED', 'runDir 或 runName 必填');
    }
    ok(res, adoptCandidate({
      runDir: body.runDir || body.run_dir,
      runName: body.runName || body.run_name,
      scene: body.scene,
      title: body.title,
      tags: body.tags,
      notes: body.notes,
      quality: body.quality || 'unvalidated',
      dataFile: body.dataFile || body.data_file,
    }), 201);
  } catch (err) { fail(res, err); }
});

// ════════════════════════ 脚手架 ════════════════════════

/** 新建场景的最小可用本体骨架。
 *  必须同时满足 CP-2（schema 合法 + ≥1KB），否则「新建」按钮会立刻撞上 422 —— 
 *  因此这里刻意写入填充说明与结构提示，既是脚手架也是自文档。 */
function scaffoldOntology(sceneKey, { process_type, title, objectives } = {}) {
  const label = title || sceneKey;
  return {
    ontology_version: '1.1.0',
    created_at: new Date().toISOString(),
    provenance: {
      build_mode: 'manual',
      scene: sceneKey,
      created_via: 'web ontology manager',
      guidance: '本骨架由前端「新建本体」生成。请按实际工艺填写场景/设备/阶段，再逐列登记信号语义。'
        + 'CP-2 门禁要求：schema 合法且文件 ≥1KB；诊断管线只消费通过 CP-2 的本体。',
    },
    scene: {
      name: sceneKey,
      process_type: process_type || 'unspecified industrial process',
      production_goal: `为场景「${label}」建立可用于根因诊断的工艺本体`,
      equipment: [],
      stages: [],
      objectives: (Array.isArray(objectives) && objectives.length ? objectives : [`${label} 诊断目标`])
        .concat(['识别并区分采集层异常与工艺本体异常']),
    },
    signals: {
      inspection_signals: [],
      process_parameters: [],
      control_variables: [],
      events: [],
      metadata_columns: [],
    },
    signals_guidance: {
      inspection_signals: '检测/结果类信号：质量指标、终检尺寸等，通常作为诊断 target。',
      process_parameters: '过程参数：温度、压力、流量、速度等，通常作为 predictor。',
      control_variables: '控制量：设定值/输出值，role 固定为 control，需填 control_type。',
      events: '事件列：换批、启停、报警等离散取值列。',
      metadata_columns: '元数据列：timestamp / batch_id / product_code / operator。',
      required_fields: 'name, column, role（schema required）',
      recommended_fields: 'unit, physical_meaning, physical_meaning_confidence, normal_range, '
        + 'stage_ref, equipment_ref, governing_law, expected_data_behavior, observed_data_behavior, behavior_match',
    },
    relationships: [],
    relationships_guidance: {
      required_fields: 'from, to, type（causal | correlative | control | physical）',
      recommended_fields: 'strength, mechanism, governing_equation, predicted_functional_form, inferred',
      rule: 'from/to 必须是 signals 中已登记的 column，否则会被模型健康面板判为悬空关系（critical）。',
    },
    confounders: [],
    parameter_groups: {},
    physical_principles: [],
    known_failure_modes: [],
    discrepancy_signals: [],
    metadata: {
      units: {},
      sampling_rate: null,
      batch_id: null,
      timezone: null,
      start_time: null,
      end_time: null,
      created_by: 'web ontology manager',
    },
  };
}

export default router;
