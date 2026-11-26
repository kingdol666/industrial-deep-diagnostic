// Line Memory Service — 跨 run 产线记忆接线层（backend ↔ .claude/shared/scripts/line_memory.mjs）
//
// 职责边界：
//   - 核心算法（提取/挖掘/分级/检索/提案校验）全部在 shared 脚本里，本文件只做接线与路由支撑
//   - 完成钩子：仅 completed run 入库；任何失败都只告警、绝不扰动 run 终态
//   - 启动注入：按 scene 别名检索本线记忆，生成 prompt brief；payload 在 run 完成后落
//     00_input/context/line_memory.json 作为审计快照（run 目录在 spawn 时还不存在）
//   - 本体提案：确定性校验 → 分级（additive 自动 / correction 双佐证 / removal 人工）→
//     ontology_store.addVersion（带 parent_version + provenance），管线事件可追溯
import { existsSync, readFileSync, mkdirSync, writeFileSync, openSync, readSync, closeSync } from 'fs';
import { join } from 'path';

import { stmts } from '../db/database.mjs';
import { PROJECT_ROOT } from '../../../../config/loader.mjs';
import logger from '../utils/logger.mjs';
import { resolveRunDir } from './artifact-manifest.service.mjs';
import { requireRun } from './history.service.mjs';
import { canReuseFinding, getConfirmedContext, renderConfirmedContext } from './human-review.service.mjs';
import {
  defaultStoreDir, ensureStore, readRegistry, readConsensus, readFindings, readProposalLog,
  findLineByAlias, buildMemoryBrief, ingestRun, consolidate, mergeLines, overrideEntry,
  ingestProposals, decideProposal, readProposalsForRun, slugify,
} from '../../../../.claude/shared/scripts/line_memory.mjs';
import {
  addVersion, readAsset, listSceneVersions, entryProfile, appendPipelineEvent,
} from '../../../../.claude/shared/scripts/ontology_store.mjs';

/** runId → 启动时注入的 brief（完成后落盘审计） */
const briefByRun = new Map();

export function storeDir() {
  return defaultStoreDir();
}

function httpError(status, code, message) {
  const err = new Error(message);
  err.status = status;
  err.code = code;
  return err;
}

function rowRunDir(row) {
  if (!row || !row.workspace_path) return null;
  const dir = resolveRunDir(PROJECT_ROOT, row.workspace_path);
  return dir && existsSync(dir) ? dir : null;
}

// ── 列表 / 详情 / findings ───────────────────────────────────────────────

export function listLines() {
  ensureStore(storeDir());
  const reg = readRegistry(storeDir());
  const proposals = readProposalLog(storeDir());
  return Object.entries(reg.lines).map(([key, entry]) => {
    const consensus = readConsensus(storeDir(), key);
    const mine = proposals.filter((p) => p.line_key === key);
    return {
      line_key: key,
      name: entry.name,
      aliases: entry.aliases || [],
      created_at: entry.created_at || null,
      updated_at: entry.updated_at || null,
      stats: consensus ? consensus.stats : null,
      latest_state: consensus ? consensus.latest_state : null,
      consensus_generated_at: consensus ? consensus.generated_at : null,
      pending_proposals: mine.filter((p) => p.status === 'pending_approval' || p.status === 'pending_corroboration').length,
      proposals_total: mine.length,
    };
  }).sort((a, b) => String(b.consensus_generated_at || '').localeCompare(String(a.consensus_generated_at || '')));
}

export function getLineDetail(lineKey) {
  const key = slugify(lineKey);
  const reg = readRegistry(storeDir());
  const entry = reg.lines[key];
  if (!entry) throw httpError(404, 'LINE_NOT_FOUND', `产线不存在: ${lineKey}`);
  const consensus = readConsensus(storeDir(), key);
  const proposals = readProposalLog(storeDir()).filter((p) => p.line_key === key);
  return {
    line_key: key,
    name: entry.name,
    aliases: entry.aliases || [],
    consensus: consensus
      ? { generated_at: consensus.generated_at, contract_version: consensus.contract_version, stats: consensus.stats, latest_state: consensus.latest_state, entries: consensus.entries }
      : null,
    proposals,
  };
}

export function listLineFindings(lineKey, { limit = 50, offset = 0, subject = null, claim_type = null } = {}) {
  const key = slugify(lineKey);
  const reg = readRegistry(storeDir());
  if (!reg.lines[key]) throw httpError(404, 'LINE_NOT_FOUND', `产线不存在: ${lineKey}`);
  let rows = readFindings(storeDir(), key);
  if (subject) rows = rows.filter((f) => f.subject === subject);
  if (claim_type) rows = rows.filter((f) => f.claim_type === claim_type);
  rows.sort((a, b) => String(b.observed_at).localeCompare(String(a.observed_at)));
  const lim = Math.min(Math.max(Number(limit) || 50, 1), 500);
  const off = Math.max(Number(offset) || 0, 0);
  return { total: rows.length, limit: lim, offset: off, findings: rows.slice(off, off + lim) };
}

// ── 启动注入（execute 路径，引擎 spawn 前调用） ──────────────────────────

/**
 * 按 scene 别名检索本线记忆。返回 {lineKey,text,payload,hit,tried}；
 * 空记忆返回 {text:''}（调用方不注入）。
 */
export function buildStartMemory(row, { ontology = null } = {}) {
  if (!row) return null;
  briefByRun.delete(row.run_id);
  ensureStore(storeDir());
  const aliases = [row.scene_name, ontology?.scene_key].filter(Boolean);
  if (ontology?.source && existsSync(ontology.source)) {
    try {
      const o = JSON.parse(readFileSync(ontology.source, 'utf-8'));
      if (o?.scene?.name) aliases.push(o.scene.name);
    } catch { /* 可选来源 */ }
  }
  const hitAlias = aliases.find((alias) => findLineByAlias(storeDir(), alias));
  const hit = hitAlias ? findLineByAlias(storeDir(), hitAlias) : null;
  const reviewed = getConfirmedContext(row, hit?.entry?.aliases || []);
  let brief = null;
  if (hit) {
    const allowed = new Map();
    const projected = consolidate(storeDir(), hit.lineKey, {
      persist: false,
      filterFinding(f) {
        if (!allowed.has(f.run_id)) allowed.set(f.run_id, canReuseFinding(row, f.run_id));
        return allowed.get(f.run_id);
      },
    });
    brief = buildMemoryBrief(projected);
  }
  const text = [renderConfirmedContext(reviewed), brief?.text].filter(Boolean).join('\n\n');
  const response = { lineKey: hit?.lineKey ?? null, text, payload: brief?.payload ?? null, reviewed, hit: Boolean(text), tried: aliases };
  if (text) briefByRun.set(row.run_id, {
    collected_at: new Date().toISOString(), line_key: response.lineKey,
    text, payload: response.payload, reviewed, matched_alias: hitAlias,
  });
  return response;
}

export function getRunReviewContext(runId, viewer) {
  const row = requireRun(runId, viewer);
  if (row.deleted_at) throw httpError(404, 'RUN_NOT_FOUND', `Run not found: ${runId}`);
  const hit = findLineByAlias(storeDir(), row.scene_name);
  return getConfirmedContext(row, hit?.entry?.aliases || []);
}

function writeMemoryContext(runDir, brief) {
  try {
    const dir = join(runDir, '00_input', 'context');
    mkdirSync(dir, { recursive: true });
    writeFileSync(join(dir, 'line_memory.json'), JSON.stringify({
      contract_version: 'line-memory-brief/1.0',
      collected_at: brief.collected_at,
      line_key: brief.line_key,
      matched_alias: brief.matched_alias || null,
      stats: brief.payload ? brief.payload.stats : null,
      latest_state: brief.payload ? brief.payload.latest_state : null,
      entries: brief.payload ? brief.payload.entries : [],
      human_reviewed: brief.reviewed || [],
      injected_text: brief.text,
    }, null, 2));
  } catch (err) {
    logger.warn(`line-memory context snapshot failed: ${err.message}`, { context: 'LineMemory' });
  }
}

// ── 完成钩子（仅 completed） ─────────────────────────────────────────────

/**
 * 完成钩子入口：findings 入库 + 共性重算 + 本体提案分级生效。
 * 永不抛错（调用方以 try/catch 兜底，这里再自保一层）。
 */
export function ingestCompletedRun(runId) {
  try {
    const row = stmts.getRunById.get(runId);
    // Any terminal non-completed outcome drops the pending brief so failed /
    // stopped / expired runs can never leak into the in-memory map.
    if (!row || row.status !== 'completed') {
      briefByRun.delete(runId);
      return null;
    }
    const runDir = rowRunDir(row);
    if (!runDir) return null;

    const brief = briefByRun.get(runId);
    if (brief) {
      writeMemoryContext(runDir, brief);
      briefByRun.delete(runId);
    }

    const result = ingestRun({
      storeDir: storeDir(),
      runDir,
      runId: row.run_id,
      intent: row.analysis_intent,
      sceneKey: row.scene_name,
      sceneName: row.scene_name,
    });

    let proposals = null;
    try {
      proposals = ingestRunProposals(row, runDir);
    } catch (err) {
      logger.warn(`line-memory proposals failed for ${runId}: ${err.message}`, { context: 'LineMemory', runId });
    }
    logger.info(
      `line-memory ingested ${runId}: line=${result.lineKey} added=${result.findings_added} stats=${JSON.stringify(result.consensus && result.consensus.stats)}`,
      { context: 'LineMemory', runId },
    );
    return { ...result, proposals };
  } catch (err) {
    logger.warn(`line-memory ingest failed for ${runId}: ${err.message}`, { context: 'LineMemory', runId });
    return null;
  }
}

// ── 本体提案：读取 → 校验 → 分级 → 应用 ─────────────────────────────────

function readDataColumns(runDir) {
  for (const rel of ['00_input/preprocessed_data.csv', '00_input/data.csv']) {
    const abs = join(runDir, rel);
    if (!existsSync(abs)) continue;
    try {
      // Header only — read a bounded 64KB slice instead of the whole table
      // (a stability run's preprocessed CSV can be 18 MB).
      const fd = openSync(abs, 'r');
      const buf = Buffer.alloc(64 * 1024);
      let bytes = 0;
      try { bytes = readSync(fd, buf, 0, buf.length, 0); } finally { closeSync(fd); }
      const head = buf.subarray(0, bytes).toString('utf-8').split(/\r?\n/)[0] || '';
      const cols = head.split(',').map((c) => c.trim().replace(/^"|"$/g, '')).filter(Boolean);
      if (cols.length) return cols;
    } catch { /* 下一个候选 */ }
  }
  return null;
}

/**
 * Locate a parameter declaration across ontology shapes:
 *   diagnosis profile : signals[] / parameters[] arrays of {name,...}
 *   watch profile     : signals{bucket:[...]} object + parameter_groups{GROUP:[names]}
 *                       (stability/sentinel scenes — added 2026-11-03 after the
 *                        gap audit: the apply path was diagnosis-shape only)
 * @returns {{kind:string, list?:Array, item?:object, bucket?:string, groupName?:string}|null}
 */
function findSignalJson(ontology, target) {
  for (const key of ['signals', 'parameters']) {
    if (Array.isArray(ontology[key])) {
      const hit = ontology[key].find((s) => s && (s.name === target || s.id === target || s.column === target));
      if (hit) return { kind: 'array', list: ontology[key], item: hit };
    }
  }
  const sig = ontology.signals;
  if (sig && typeof sig === 'object' && !Array.isArray(sig)) {
    for (const [bucket, list] of Object.entries(sig)) {
      if (!Array.isArray(list)) continue;
      const hit = list.find((s) => s && (s.name === target || s.column === target || s.id === target));
      if (hit) return { kind: 'bucket', list, item: hit, bucket };
    }
  }
  const groups = ontology.parameter_groups;
  if (groups && typeof groups === 'object' && !Array.isArray(groups)) {
    for (const [gname, members] of Object.entries(groups)) {
      if (Array.isArray(members) && members.includes(target)) return { kind: 'group-object', list: members, item: null, groupName: gname };
    }
  }
  if (Array.isArray(groups)) {
    for (const g of groups) {
      if (g && Array.isArray(g.members) && g.members.includes(target)) {
        return { kind: 'group-array', list: g.members, item: null, groupName: g.id || g.name };
      }
    }
  }
  return null;
}

/** Group container handle: object map {GROUP:[names]} or array [{id,name,members[]}]. */
function findGroupJson(ontology, name) {
  const groups = ontology.parameter_groups;
  if (!name || !groups) return null;
  if (typeof groups === 'object' && !Array.isArray(groups)) {
    return Object.prototype.hasOwnProperty.call(groups, name)
      ? { kind: 'object', members: groups[name] }
      : null;
  }
  if (Array.isArray(groups)) {
    const g = groups.find((x) => x && (x.id === name || x.name === name));
    return g ? { kind: 'array', group: g, members: g.members || (g.members = []) } : null;
  }
  return null;
}

function ensureGroup(ontology, name) {
  const found = findGroupJson(ontology, name);
  if (found) return found;
  if (!ontology.parameter_groups || typeof ontology.parameter_groups !== 'object') ontology.parameter_groups = {};
  if (Array.isArray(ontology.parameter_groups)) {
    const g = { id: name, name, members: [] };
    ontology.parameter_groups.push(g);
    return { kind: 'array', group: g, members: g.members };
  }
  ontology.parameter_groups[name] = [];
  return { kind: 'object', members: ontology.parameter_groups[name] };
}

function removeFromAllGroups(ontology, target) {
  const groups = ontology.parameter_groups;
  if (!groups) return;
  if (typeof groups === 'object' && !Array.isArray(groups)) {
    for (const members of Object.values(groups)) {
      if (Array.isArray(members)) {
        const idx = members.indexOf(target);
        if (idx >= 0) members.splice(idx, 1);
      }
    }
    return;
  }
  if (Array.isArray(groups)) {
    for (const g of groups) {
      if (g && Array.isArray(g.members)) {
        const idx = g.members.indexOf(target);
        if (idx >= 0) g.members.splice(idx, 1);
      }
    }
  }
}

function unitOf(to) {
  if (to && typeof to === 'object') return to.unit ?? to.value ?? null;
  return to ?? null;
}

/**
 * 把一条 proposal change 应用到 ontology JSON（返回新对象，不改原值）。
 * Profile-aware: diagnosis arrays + watch-profile buckets/groups (2026-11-03).
 * 所有修订同时由调用方写入 ontology.memory_revisions 审计块。
 */
export function applyChangeToOntology(ontology, change) {
  const patched = JSON.parse(JSON.stringify(ontology));
  const target = String(change.target);
  const hit = findSignalJson(patched, target);
  const isWatchSignals = patched.signals && typeof patched.signals === 'object' && !Array.isArray(patched.signals);
  const isSceneTarget = ['__scene__', '__line__', 'scene'].includes(target);

  switch (change.op) {
    case 'add_missing_parameter': {
      if (hit) return { ok: false, error: `参数已存在: ${target}` };
      const to = change.to && typeof change.to === 'object' ? change.to : {};
      const decl = {
        name: target,
        ...(isWatchSignals ? { column: target, schema_role: 'predictor', role: 'parameter' } : { role: to.role || 'parameter' }),
        unit: unitOf(change.to) || null,
        physical_meaning: to.physical_meaning || null,
        knowledge_source: 'line_memory',
        confidence: 'LEARNED',
        provenance: { origin: 'line-memory', proposal_id: change.proposal_id || null, at: new Date().toISOString() },
      };
      if (isWatchSignals) {
        if (!Array.isArray(patched.signals.process_parameters)) patched.signals.process_parameters = [];
        patched.signals.process_parameters.push(decl);
      } else {
        if (!Array.isArray(patched.signals)) patched.signals = [];
        patched.signals.push(decl);
      }
      if (to.group) {
        const g = ensureGroup(patched, String(to.group));
        if (!g.members.includes(target)) g.members.push(target);
      }
      if (decl.unit) {
        if (!patched.metadata || typeof patched.metadata !== 'object') patched.metadata = {};
        if (!patched.metadata.units || typeof patched.metadata.units !== 'object') patched.metadata.units = {};
        patched.metadata.units[target] = decl.unit;
      }
      return { ok: true, patched };
    }
    case 'add_physical_meaning': {
      if (hit && hit.item) {
        hit.item.physical_meaning = String(change.to ?? '');
        return { ok: true, patched };
      }
      // No structured declaration (watch params may live only in groups): keep
      // the knowledge in a stable notes map that humans/agents can read.
      if (!patched.parameter_notes || typeof patched.parameter_notes !== 'object') patched.parameter_notes = {};
      patched.parameter_notes[target] = { ...(patched.parameter_notes[target] || {}), physical_meaning: String(change.to ?? '') };
      return { ok: true, patched };
    }
    case 'add_note': {
      const note = String(change.to ?? '');
      if (isSceneTarget) {
        // Scene-level knowledge note → ontology.limitations, which the
        // stability/sentinel brief projects verbatim (`limitations`), so the
        // next run actually reads it.
        if (!Array.isArray(patched.limitations)) patched.limitations = [];
        if (!patched.limitations.includes(note)) patched.limitations.push(note);
        return { ok: true, patched };
      }
      const group = findGroupJson(patched, target);
      if (group) {
        if (!patched.group_notes || typeof patched.group_notes !== 'object') patched.group_notes = {};
        patched.group_notes[target] = note;
        return { ok: true, patched };
      }
      if (hit && hit.item) {
        hit.item.notes = note;
        return { ok: true, patched };
      }
      if (!patched.parameter_notes || typeof patched.parameter_notes !== 'object') patched.parameter_notes = {};
      patched.parameter_notes[target] = { ...(patched.parameter_notes[target] || {}), note };
      return { ok: true, patched };
    }
    case 'add_class': {
      if (!Array.isArray(patched.memory_classes)) patched.memory_classes = [];
      patched.memory_classes.push({ class: String(change.to ?? target), targets: [target], at: new Date().toISOString() });
      return { ok: true, patched };
    }
    case 'add_group_member': {
      const group = (change.to && change.to.group) || (typeof change.to === 'string' ? change.to : null);
      if (!group) return { ok: false, error: 'add_group_member 缺少 to.group' };
      const g = ensureGroup(patched, String(group));
      if (!g.members.includes(target)) g.members.push(target);
      return { ok: true, patched };
    }
    case 'correct_unit': {
      const unit = unitOf(change.to);
      if (hit && hit.item) hit.item.unit = unit;
      // Authoritative learned override for every profile (exact key wins over
      // the wildcard entries e.g. "F_PS*" in metadata.units).
      if (!patched.metadata || typeof patched.metadata !== 'object') patched.metadata = {};
      if (!patched.metadata.units || typeof patched.metadata.units !== 'object') patched.metadata.units = {};
      patched.metadata.units[target] = unit;
      return { ok: true, patched };
    }
    case 'correct_group':
    case 'reclassify':
    case 'correct_stage': {
      const val = typeof change.to === 'object' ? (change.to.value ?? change.to[change.field || 'group'] ?? null) : change.to;
      if (change.op === 'correct_stage') {
        if (hit && hit.item) hit.item.stage = val;
        else return { ok: false, error: `参数不存在,无法修正阶段: ${target}` };
        return { ok: true, patched };
      }
      if (change.field && change.op === 'reclassify') {
        if (hit && hit.item) hit.item[change.field] = val;
        else return { ok: false, error: `参数不存在,无法修正字段: ${target}` };
        return { ok: true, patched };
      }
      // group move — works for object-map and array-of-groups shapes
      const group = String(val ?? '');
      if (!group) return { ok: false, error: 'correct_group 缺少目标组' };
      removeFromAllGroups(patched, target);
      const g = ensureGroup(patched, group);
      if (!g.members.includes(target)) g.members.push(target);
      if (hit && hit.item) hit.item.group = group;
      return { ok: true, patched };
    }
    case 'deprecate': {
      if (!hit) return { ok: false, error: `参数不存在,无法废弃: ${target}` };
      if (hit.item) hit.item.deprecated = true;
      if (!patched.parameter_notes || typeof patched.parameter_notes !== 'object') patched.parameter_notes = {};
      patched.parameter_notes[target] = { ...(patched.parameter_notes[target] || {}), deprecated: true };
      return { ok: true, patched };
    }
    case 'remove': {
      if (!hit) return { ok: false, error: `参数不存在,无法移除: ${target}` };
      if (hit.item && Array.isArray(hit.list)) {
        const idx = hit.list.indexOf(hit.item);
        if (idx >= 0) hit.list.splice(idx, 1);
      }
      removeFromAllGroups(patched, target);
      if (!Array.isArray(patched.memory_removed)) patched.memory_removed = [];
      patched.memory_removed.push({ target, at: new Date().toISOString(), op: change.op });
      return { ok: true, patched };
    }
    default:
      return { ok: false, error: `未知 op: ${change.op}` };
  }
}

/**
 * 应用一条提案 → ontology_store 新版本（parent_version 链 + provenance）。
 * @returns {{ok:boolean, scene_key?, version?, error?}}
 */
export function applyOntologyChange(record, change = record, runDir = null) {
  const sceneKey = record.scene_key;
  const versions = listSceneVersions(sceneKey);
  if (!versions.length) return { ok: false, error: `本体场景不存在: ${sceneKey}` };
  const latest = versions[0];
  const asset = readAsset(sceneKey, latest.version);
  if (!asset || asset.missing || !asset.ontology) return { ok: false, error: `最新版本不可读: ${sceneKey} v${latest.version}` };

  const result = applyChangeToOntology(asset.ontology, { ...change, proposal_id: record.proposal_id });
  if (!result.ok) return result;

  // 审计块：所有修订都写入 ontology.memory_revisions（即使字段未结构化也留痕）
  const ontology = result.patched;
  if (!ontology) return { ok: false, error: 'internal: patched ontology missing' };
  if (!Array.isArray(ontology.memory_revisions)) ontology.memory_revisions = [];
  ontology.memory_revisions.push({
    proposal_id: record.proposal_id,
    run_id: record.run_id,
    tier: record.tier,
    op: change.op,
    target: change.target,
    field: change.field ?? null,
    from: change.from ?? null,
    to: change.to ?? null,
    rationale: String(change.rationale || '').slice(0, 300),
    evidence_level: change.evidence_level || record.evidence_level || null,
    rule: record.tier === 'additive' ? 'auto_additive' : record.tier === 'correction' ? 'corroborated_correction' : 'human_approved',
    applied_at: new Date().toISOString(),
  });

  const added = addVersion({
    sceneKey,
    ontology,
    buildMode: 'edit',
    quality: 'validated',
    title: latest.title || sceneKey,
    tags: Array.isArray(latest.tags) ? latest.tags : [],
    notes: `line-memory 修订: ${change.op} ${change.target}`,
    origin: 'diagnosis',
    parentVersion: latest.version,
    profile: entryProfile(latest),
    // Attach the revision to the context fingerprint the RUN actually resolved
    // (from 01_ontology/ontology_coverage.json). Without this the revision
    // inherits the branch's old fp and can be shadowed by a sibling scene's
    // higher-version asset for the operator's real context (2026-11-03 audit).
    contextFp: record.context_fp || latest.context_fp || null,
    dataStage: latest.data_stage || null,
    provenance: {
      proposal_id: record.proposal_id,
      run_id: record.run_id,
      tier: record.tier,
      op: change.op,
      target: change.target,
      rule: record.tier === 'additive' ? 'auto_additive' : record.tier === 'correction' ? 'corroborated_correction' : 'human_approved',
    },
  });

  if (runDir) {
    try {
      appendPipelineEvent(runDir, {
        type: 'ontology_revised',
        scene_key: sceneKey,
        from_version: latest.version,
        to_version: added.version,
        proposal_id: record.proposal_id,
        op: change.op,
        target: change.target,
      });
    } catch { /* 事件是可选审计 */ }
  }
  return { ok: true, scene_key: sceneKey, version: added.version };
}

/** 完成钩子内的提案入库（读 05_review/ontology_proposals.json）。 */
export function ingestRunProposals(row, runDir) {
  const found = readProposalsForRun(runDir);
  if (!found) return null;
  const lineKey = findLineByAlias(storeDir(), row.scene_name)?.lineKey || slugify(row.scene_name);
  const dataColumns = readDataColumns(runDir);
  // The run's own context fingerprint — the revision must be reachable for the
  // next run of this operator context, so it is carried onto the new version.
  let contextFp = null;
  try {
    const cov = JSON.parse(readFileSync(join(runDir, '01_ontology', 'ontology_coverage.json'), 'utf-8'));
    contextFp = cov && typeof cov.context_fp === 'string' ? cov.context_fp : null;
  } catch { /* coverage is optional (diagnosis profile writes none) */ }
  const res = ingestProposals({
    storeDir: storeDir(),
    runDir,
    runId: row.run_id,
    lineKey,
    dataColumns,
    applyFn: (record, change) => applyOntologyChange({ ...record, context_fp: contextFp }, change, runDir),
  });
  if (res.records && res.records.length) {
    try {
      appendPipelineEvent(runDir, {
        type: 'ontology_proposals',
        file: found.path,
        total: res.records.length,
        applied: res.records.filter((r) => r.status === 'applied').length,
        pending: res.records.filter((r) => r.status.startsWith('pending')).length,
        invalid: res.records.filter((r) => r.status === 'invalid').length,
      });
    } catch { /* 可选 */ }
  }
  return res;
}

// ── 人工决策 / 合并 / 反证 ───────────────────────────────────────────────

export function decideProposalById(proposalId, action, actor = 'console') {
  try {
    const record = decideProposal({
      storeDir: storeDir(),
      proposalId,
      action,
      actor,
      applyFn: (rec) => applyOntologyChange(rec, rec, null),
    });
    return record;
  } catch (err) {
    const msg = String(err.message || err);
    if (/not found/i.test(msg)) throw httpError(404, 'PROPOSAL_NOT_FOUND', msg);
    if (/apply failed/i.test(msg)) throw httpError(422, 'PROPOSAL_APPLY_FAILED', msg);
    if (/unknown action/i.test(msg)) throw httpError(400, 'PROPOSAL_BAD_ACTION', msg);
    throw err;
  }
}

export function mergeLine(fromKey, intoKey) {
  try {
    return mergeLines({ storeDir: storeDir(), fromKey, intoKey });
  } catch (err) {
    if (/不存在/.test(err.message)) throw httpError(404, 'LINE_NOT_FOUND', err.message);
    throw httpError(400, 'LINE_MERGE_FAILED', err.message);
  }
}

export function refuteEntry(lineKey, entryKey, { reason = '', status = 'refuted' } = {}) {
  const key = slugify(lineKey);
  const reg = readRegistry(storeDir());
  if (!reg.lines[key]) throw httpError(404, 'LINE_NOT_FOUND', `产线不存在: ${lineKey}`);
  const consensus = overrideEntry({ storeDir: storeDir(), lineKey: key, entryKey, status, reason });
  return consensus;
}

export function consolidateLine(lineKey) {
  const key = slugify(lineKey);
  const reg = readRegistry(storeDir());
  if (!reg.lines[key]) throw httpError(404, 'LINE_NOT_FOUND', `产线不存在: ${lineKey}`);
  return consolidate(storeDir(), key);
}

// ── 本体版本链（UI 用） ─────────────────────────────────────────────────

export function ontologyVersionsForLine(lineKey) {
  const key = slugify(lineKey);
  const reg = readRegistry(storeDir());
  const entry = reg.lines[key];
  if (!entry) throw httpError(404, 'LINE_NOT_FOUND', `产线不存在: ${lineKey}`);
  const sceneCandidates = new Set([key, ...(entry.aliases || []).map((a) => slugify(a))]);
  const scenes = [];
  for (const scene of sceneCandidates) {
    if (!scene) continue;
    const versions = listSceneVersions(scene);
    if (!versions.length) continue;
    scenes.push({
      scene_key: scene,
      versions: versions.map((v) => ({
        version: v.version,
        quality: v.quality || null,
        origin: v.origin || null,
        build_mode: v.build_mode || null,
        parent_version: v.parent_version ?? null,
        title: v.title || null,
        created_at: v.created_at || null,
        content_fp: v.content_fp || null,
        built_from_run: v.built_from_run || null,
      })),
    });
  }
  return { line_key: key, scenes };
}
