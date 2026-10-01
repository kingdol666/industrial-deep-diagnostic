#!/usr/bin/env node
// experience_build.mjs — build the IDD-local tuning experience store + kb-ready summary.
//
// Inputs : 00_input/action_log.json (object | array | jsonl | directory)
//          06_experience/attribution/{action_log_id}.json  (tune_stats output)
//          00_input/fault_signature.json (optional, for fault_control_recipe)
//          alias map (optional; {"raw_id": "eng_01", ...})
// Outputs: 06_experience/tuning_experience.jsonl  (local experience store)
//          06_experience/accumulated/state.json   (feedback ledger + counters mirror)
//          06_experience/kb_summary.md            (kb-ready, handed to the AWS agent;
//                                                  IDD never connects to any external KB)
//
// Discipline (v1.4): IDD is a PURE ANALYSIS system. The local store admits ONLY
// entries whose attribution_status != not_estimable (E0 retro entries allowed as
// observation-grade). chunk_id = exp_{etype}_{regime_key[:8]}_{hash16}; the same
// action in the same regime is idempotent (replay = no-op), a DIFFERENT action_log
// with the same action signature in the same regime corroborates (+1). KB
// ingestion is AWS-side; this script produces the kb-ready summary only.
//
// Usage:
//   node experience_build.mjs build    --run-dir RUN_DIR [--action-log PATH] [--alias-map PATH]
//   node experience_build.mjs feedback --run-dir RUN_DIR --chunk-id ID
//        --result effective|ineffective|harmful|confirmed [--note "..."]

import fs from 'fs';
import path from 'path';
import crypto from 'crypto';
import { fileURLToPath } from 'url';

const SCRIPT_VERSION = 'experience_build/1.0';
const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const SCHEMA_DIR = path.join(SCRIPT_DIR, '..', 'schemas');
const REPO_ROOT = path.resolve(path.join(SCRIPT_DIR, '..', '..', '..', '..'));
const ENUMS_PATH = path.join(REPO_ROOT, '.claude', 'shared', 'schemas', 'closedloop_enums.json');

const j = (p) => { try { return JSON.parse(fs.readFileSync(p, 'utf-8')); } catch { return null; } };
const nowIso = () => new Date().toISOString();

// deterministic canonical JSON (sorted keys, no whitespace)
function canon(obj) {
  if (obj === null || typeof obj !== 'object') return JSON.stringify(obj ?? null);
  if (Array.isArray(obj)) return '[' + obj.map(canon).join(',') + ']';
  const keys = Object.keys(obj).filter((k) => obj[k] !== undefined).sort();
  return '{' + keys.map((k) => JSON.stringify(k) + ':' + canon(obj[k])).join(',') + '}';
}
const sha16 = (obj) => crypto.createHash('sha256').update(canon(obj)).digest('hex').slice(0, 16);

function parseArgs(argv) {
  const args = { _: [] };
  for (let i = 0; i < argv.length; i++) {
    if (argv[i].startsWith('--')) args[argv[i].slice(2)] = (i + 1 < argv.length && !argv[i + 1].startsWith('--')) ? argv[++i] : true;
    else args._.push(argv[i]);
  }
  return args;
}

function readJsonArg(p, base) {
  const abs = path.isAbsolute(p) ? p : path.join(base, p);
  return j(abs);
}

function loadActionLogs(p, base) {
  const abs = path.isAbsolute(p) ? p : path.join(base, p);
  if (!fs.existsSync(abs)) return [];
  const st = fs.statSync(abs);
  let raw = [];
  if (st.isDirectory()) {
    for (const f of fs.readdirSync(abs).filter((f) => f.endsWith('.json')).sort()) {
      raw = raw.concat(loadActionLogs(path.join(abs, f), base).map((x) => x.log));
    }
  } else {
    const text = fs.readFileSync(abs, 'utf-8');
    const s = text.trim();
    if (s.startsWith('[')) raw = JSON.parse(s);
    else if (s.startsWith('{')) raw = [JSON.parse(s)];
    else raw = s.split(/\r?\n/).filter(Boolean).map((l) => JSON.parse(l));
  }
  // normalize to array of logs; id derived deterministically when absent
  const out = [];
  const ts8 = (log) => (String(log.ts || '').replace(/\D/g, '').slice(0, 8)) || '00000000';
  for (const log of raw) {
    const id = log.action_log_id || (ts8(log) + sha16(log).slice(0, 8));
    out.push({ id, log });
  }
  out.sort((a, b) => String(a.log.ts || '').localeCompare(String(b.log.ts || '')));
  return out;
}

function aliasFor(rawId, aliasMap) {
  if (!rawId) return null;
  if (aliasMap && aliasMap[rawId]) return aliasMap[rawId];
  const n = 10 + (parseInt(sha16({ actor: rawId }).slice(0, 4), 16) % 89);
  return `eng_${n}`;
}

function regimeKeyOf(ctx) {
  const c = ctx || {};
  return `${c.product || '-'}|${c.machine || '-'}|${c.regime_label || '-'}`;
}

function regimeSlots(rk) {
  const [product, machine, label] = String(rk).split('|');
  return { product, machine, label };
}

function actionSummaryCn(actions) {
  return (actions || []).map((a) => {
    const from = (a.from === null || a.from === undefined) ? '∅' : String(a.from);
    return `${a.parameter}: ${from} → ${a.to} (${a.unit || 'unit?'})`;
  }).join('; ');
}

function deriveInvalidationNotes(entry) {
  const notes = [];
  const p = entry.payload || {};
  if (entry.retro_mined) notes.push('反推条目（step_detector 冷启动）：未经工程师确认前不得作为执行依据，仅参考');
  const ci = (p.effect || {}).ci95;
  if (Array.isArray(ci) && ci.length === 2 && !((ci[0] > 0) || (ci[1] < 0))) {
    notes.push('CI95 跨 0——效应方向未确立，仅作观察记录');
  }
  if (p.confound_detected === true) notes.push('存在未解混杂事件，效应可能并非本动作所致');
  if (p.attribution_status === 'truncated') notes.push('效果窗被截断，未观察到完全整定，效应量可能被低估');
  notes.push('超出该 regime_key 工况范围的应用未经本经验支持，不得直接外推');
  return notes;
}

function applicabilityNote(entry, report) {
  const notes = [];
  if (entry.retro_mined) {
    notes.push('retro-mined 反推条目（E0，仅参考 advisory-only）');
    return notes.join(' ');
  }
  const dtu = (((report || {}).segments || {}).dead_time_used);
  if (dtu === 0 || dtu === null || dtu === undefined) {
    notes.push('死区时间按 0 步缺省处理（若实际死区非零，基线段可能混入动作后影响）');
  } else {
    notes.push(`死区时间 ${dtu} 步`);
  }
  const tb = (((report || {}).segments || {}).effect || {}).truncated_by;
  if (tb) notes.push(`效果窗被 ${tb} 截断（未观察到完全整定）`);
  if ((entry.payload || {}).confound_detected === true) notes.push('存在混杂事件，效应归因降档（E0）');
  return notes.join(' ');
}

// ---------------------------------------------------------------- grading

function computeGrade(entry) {
  const p = entry.payload || {};
  const eff = p.effect || {};
  const ci = eff.ci95;
  const ciExcl0 = Array.isArray(ci) && ci.length === 2 && (ci[0] > 0 || ci[1] < 0);
  const weak = entry.retro_mined === true
    || (p.attribution_status != null && p.attribution_status !== 'estimable')
    || p.confound_detected === true;
  let grade = weak ? 'E0' : 'E1';
  let label = 'observation';
  const unconfirmed = p.confirm_status === 'unconfirmed';
  if (!weak && !unconfirmed && !entry.retro_mined
      && (entry.corroboration_count || 0) >= 2 && ciExcl0
      && p.confound_detected === false && p.attribution_status === 'estimable') {
    grade = 'E2';
    label = 'verified';
    if (entry.cross_regime_consistent === true) grade = 'E3';
  }
  // feedback gates: any refutation caps at E1; >=2 refutations demote verified
  if ((entry.refutation_count || 0) >= 1 && grade !== 'E0') { grade = 'E1'; label = 'observation'; }
  if ((entry.refutation_count || 0) >= 2) label = 'observation';
  if (grade === 'E0' && !entry.retro_mined) label = 'observation';
  return { grade, label };
}

function refreshCrossRegime(store) {
  const groups = new Map();
  for (const e of store) {
    if (e.retro_mined) continue;
    const sig = e.action_signature;
    if (!groups.has(sig)) groups.set(sig, []);
    groups.get(sig).push(e);
  }
  for (const [, group] of groups) {
    const byRegime = new Map();
    for (const e of group) {
      if (!byRegime.has(e.regime_key)) byRegime.set(e.regime_key, e);
      else byRegime.set(e.regime_key, null); // duplicate regime slot — ignore
    }
    const distinct = [...byRegime.entries()].filter(([, v]) => v !== null);
    let consistent = distinct.length >= 2;
    if (consistent) {
      const signs = new Set(distinct.map(([, e]) => Math.sign((((e.payload || {}).effect || {}).delta) ?? 0)));
      const allE2 = distinct.every(([, e]) => {
        const g = computeGrade(e).grade;
        return g === 'E2' || g === 'E3';
      });
      consistent = allE2 && signs.size === 1 && !signs.has(0);
    }
    for (const e of group) e.cross_regime_consistent = distinct.length >= 2 ? consistent : false;
  }
}

// ------------------------------------------------------------------ build

function paramDirectionsOf(actions) {
  // local-envelope direction map for signature matching (move direction per
  // parameter); kept OUT of payload.action_sequence — its items stay exactly at
  // the frozen schema surface (parameter/to/to_level/unit/step_order/expected_effect)
  const map = {};
  for (const a of actions || []) {
    let dir = 'unknown';
    if (a.from !== null && a.from !== undefined && a.to !== null && a.to !== undefined) {
      dir = a.to > a.from ? 'high' : (a.to < a.from ? 'low' : 'unknown');
    }
    map[String(a.parameter)] = dir;
  }
  return map;
}

function buildTuningEntry(id, log, report, aliasMap, retro) {
  const ctx = log.context || {};
  const rk = regimeKeyOf(ctx);
  const actions = (log.actions || []).map((a) => ({
    parameter: a.parameter, from: a.from ?? null, to: a.to, to_level: a.to_level ?? null,
    unit: a.unit, step_order: 1,
  })).map((a, i) => ({ ...a, step_order: i + 1 }));
  const sig = sha16({ etype: 'tuning_action_effect', params: actions.map((a) => [a.parameter, a.to, a.unit]) });
  const chunk = `exp_tuning_action_effect_${rk.slice(0, 8)}_${sha16({ etype: 'tuning_action_effect', regime_key: rk, params: actions.map((a) => [a.parameter, a.to, a.unit]) })}`;
  const eff = report ? (report.effect || null) : null;
  const entry = {
    experience_version: '1.0',
    experience_type: 'tuning_action_effect',
    regime_key: rk,
    payload: {
      action_summary: actionSummaryCn(log.actions),
      action_sequence: actions.map((a) => ({
        parameter: a.parameter, to: a.to, to_level: a.to_level, unit: a.unit,
        step_order: a.step_order,
        expected_effect: eff ? { delta: eff.delta, ci95: eff.ci95 } : null,
      })),
      effect: eff ? {
        metric: report.metric,
        delta: eff.delta,
        ci95: eff.ci95,
        n_eff: (eff.n_eff_hi != null && eff.n_eff_lo != null) ? Math.min(eff.n_eff_hi, eff.n_eff_lo) : null,
        direction_established: eff.direction_established ?? null,
      } : null,
      attribution_status: report ? report.attribution_status : null,
      confound_detected: report ? report.confound_detected : null,
      trajectory: (log.outcome || {}).observed_trajectory ?? null,
      applicability_note: null,
      lesson: null,
      confirm_status: null,
    },
    applicability: {
      factor_observed_ranges: null,
      system: ctx.machine ?? null,
      scenario_tags: [rk],
    },
    provenance: {
      actor_alias: aliasFor((log.actor || {}).actor_id, aliasMap),
      action_log_ids: [id],
      run_ids: [],
      batch_ids: [],
      regime_key: rk,
      attribution_version: report ? ((report.provenance || {}).script_version || null) : null,
      built_from: `industrial-tuning-memory/${SCRIPT_VERSION}`,
      judge_score: null,
      era: null,
    },
    confidence_label: 'observation',
    evidence_grade: report ? report.evidence_grade : 'E0',
    corroboration_count: 1,
    refutation_count: 0,
    cross_regime_consistent: false,
    invalidation_conditions: [],
    chunk_id: chunk,
    action_signature: sig,
    retro_mined: retro === true,
    param_directions: paramDirectionsOf(log.actions),
  };
  entry.payload.applicability_note = applicabilityNote(entry, report);
  entry.invalidation_conditions = deriveInvalidationNotes(entry);
  return entry;
}

function buildRecipeEntry(id, log, report, aliasMap, faultSignature) {
  const ctx = log.context || {};
  const rk = regimeKeyOf(ctx);
  const seq = (log.actions || []).map((a, i) => ({
    parameter: a.parameter, to: a.to, to_level: a.to_level ?? null, unit: a.unit,
    step_order: i + 1,
    expected_effect: report && report.effect ? { delta: report.effect.delta, ci95: report.effect.ci95 } : null,
  }));
  const faultParams = (faultSignature.anomalous_params || []).map((p) => [p.parameter, p.direction]);
  const params = seq.map((a) => [a.parameter, a.to, a.unit]).concat(faultParams);
  const sig = sha16({ etype: 'fault_control_recipe', params });
  const chunk = `exp_fault_control_recipe_${rk.slice(0, 8)}_${sha16({ etype: 'fault_control_recipe', regime_key: rk, params })}`;
  const entry = {
    experience_version: '1.0',
    experience_type: 'fault_control_recipe',
    regime_key: rk,
    payload: {
      action_summary: `故障处置处方：${actionSummaryCn(log.actions)}（触发源 ${((log.trigger || {}).ref_id) || 'n/a'}）`,
      effect: report && report.effect ? {
        metric: report.metric, delta: report.effect.delta, ci95: report.effect.ci95,
        n_eff: (report.effect.n_eff_hi != null && report.effect.n_eff_lo != null)
          ? Math.min(report.effect.n_eff_hi, report.effect.n_eff_lo) : null,
        direction_established: report.effect.direction_established ?? null,
      } : null,
      attribution_status: report ? report.attribution_status : null,
      confound_detected: report ? report.confound_detected : null,
      fault_signature: faultSignature,
      action_sequence: seq,
      applicability_note: null,
      lesson: null,
      confirm_status: null,
    },
    applicability: {
      factor_observed_ranges: null,
      system: ctx.machine ?? null,
      scenario_tags: [rk],
    },
    provenance: {
      actor_alias: aliasFor((log.actor || {}).actor_id, aliasMap),
      action_log_ids: [id],
      run_ids: [],
      batch_ids: [],
      regime_key: rk,
      attribution_version: report ? ((report.provenance || {}).script_version || null) : null,
      built_from: `industrial-tuning-memory/${SCRIPT_VERSION}`,
      judge_score: null,
      era: null,
    },
    confidence_label: 'observation',
    evidence_grade: report ? report.evidence_grade : 'E0',
    corroboration_count: 1,
    refutation_count: 0,
    cross_regime_consistent: false,
    invalidation_conditions: [],
    chunk_id: chunk,
    action_signature: sig,
    retro_mined: ((log.ingest_meta || {}).source === 'retro_mined'),
    param_directions: paramDirectionsOf(log.actions),
  };
  entry.payload.applicability_note = applicabilityNote(entry, report);
  entry.invalidation_conditions = deriveInvalidationNotes(entry);
  return entry;
}

function unconfirmedCheck(log, runDir) {
  // B13: aws_executor action without a recommendation_ref, or whose
  // recommendation lacks a received/executed ack, is unconfirmed and excluded
  // from corroboration promotion.
  if ((log.actor || {}).actor_type !== 'aws_executor') return null;
  const ref = log.recommendation_ref || null;
  if (!ref) return 'unconfirmed';
  const rec = j(path.join(runDir, 'conclusions', 'recommendation.json'));
  if (!rec || rec.recommendation_id !== ref) return 'unconfirmed';
  const ack = rec.ack || {};
  if (ack.status === 'received' || ack.status === 'executed') return 'confirmed';
  return 'unconfirmed';
}

function upsert(store, entry, id, runDir, state) {
  const existing = store.find((e) => e.chunk_id === entry.chunk_id);
  if (!existing) {
    store.push(entry);
    state.counters[entry.chunk_id] = { corroboration: 1, refutation: 0 };
    return 'created';
  }
  if ((existing.provenance.action_log_ids || []).includes(id)) return 'idempotent_noop';
  // a different action log with the same signature in the same regime corroborates
  existing.provenance.action_log_ids.push(id);
  existing.corroboration_count = (existing.corroboration_count || 1) + 1;
  state.counters[existing.chunk_id] = {
    corroboration: existing.corroboration_count,
    refutation: existing.refutation_count || 0,
  };
  return 'corroborated';
}

function writeStore(storePath, store) {
  const sorted = [...store].sort((a, b) => (a.chunk_id || '').localeCompare(b.chunk_id || ''));
  fs.writeFileSync(storePath, sorted.map((e) => JSON.stringify(e)).join('\n') + (sorted.length ? '\n' : ''), 'utf-8');
}

function writeState(statePath, state) {
  state.updated_at = nowIso();
  fs.writeFileSync(statePath, JSON.stringify(state, null, 2), 'utf-8');
}

// ------------------------------------------------------------- kb summary

function scenarioTitle(rk) {
  const { product, machine, label } = regimeSlots(rk);
  const fmt = (v, noun) => (v && v !== '-' ? `${noun} ${v}` : `${noun}未指定`);
  return `${fmt(product, '产品')} · ${fmt(machine, '机台')} · ${fmt(label, '工况')}`;
}

function fmtEffect(e) {
  if (!e || e.delta === null || e.delta === undefined) return '效应未量化（诚实空值）';
  const ci = Array.isArray(e.ci95) ? `CI95 = [${e.ci95.map((x) => Number(x).toFixed(4)).join(', ')}]` : 'CI95 = n/a';
  const dir = e.direction_established === true ? '方向已确立' : (e.direction_established === false ? '方向未确立' : '方向未知');
  return `Δ = ${Number(e.delta).toFixed(4)}（metric: ${e.metric || 'n/a'}），${ci}，n_eff = ${e.n_eff ?? 'n/a'}，${dir}`;
}

function buildKbSummary(runDirName, store) {
  const lines = [];
  lines.push('# 调优经验库 KB 交接摘要（kb-ready）');
  lines.push('');
  lines.push(`> 生成：industrial-tuning-memory experience_build.mjs · ${nowIso()} · RUN_DIR: ${runDirName}`);
  lines.push('> 交接路径：供 AWS Agent 经 rag-bridge kb_agent 场景化入库（按 regime_key 分库检索）；IDD 不直连任何知识库/外部服务。');
  lines.push('> 证据分级为建议强度（advisory）——是否下发、如何下发（dispatch policy）由 AWS 侧决定。');
  lines.push('> 隐私：本文档仅含人员别名（eng_NN），不含原始人员 ID。');
  lines.push('');
  const byRegime = new Map();
  for (const e of store) {
    if (!byRegime.has(e.regime_key)) byRegime.set(e.regime_key, []);
    byRegime.get(e.regime_key).push(e);
  }
  for (const [rk, entries] of [...byRegime.entries()].sort()) {
    lines.push(`## 场景：${scenarioTitle(rk)}（regime_key: \`${rk}\`）`);
    lines.push('');
    for (const e of entries.sort((a, b) => (a.chunk_id || '').localeCompare(b.chunk_id || ''))) {
      const g = computeGrade(e);
      const retroTag = e.retro_mined ? ' · retro 反推（仅参考）' : '';
      const etypeCn = e.experience_type === 'tuning_action_effect' ? '调参动作'
        : (e.experience_type === 'fault_control_recipe' ? '故障处置处方' : '优化配方');
      lines.push(`### [${g.grade}/${g.label}${retroTag}] ${etypeCn} — ${e.payload.action_summary || '(无摘要)'}`);
      lines.push(`- 效应：${fmtEffect(e.payload.effect)}`);
      lines.push(`- 归因状态：${e.payload.attribution_status ?? 'n/a'} · 混杂：${e.payload.confound_detected ? '有' : '无'}`);
      lines.push(`- 佐证/反证：${e.corroboration_count ?? 0} / ${e.refutation_count ?? 0} · 本地经验 ID：\`${e.chunk_id}\``);
      if (e.payload.applicability_note) lines.push(`- 适用注记：${e.payload.applicability_note}`);
      if (e.payload.lesson) lines.push(`- 经验教训：${e.payload.lesson}`);
      if ((e.invalidation_conditions || []).length) {
        lines.push(`- 失效条件：${e.invalidation_conditions.join('；')}`);
      }
      lines.push('');
    }
  }
  const nTuning = store.filter((e) => e.experience_type === 'tuning_action_effect').length;
  const nRecipe = store.filter((e) => e.experience_type === 'fault_control_recipe').length;
  const nOpt = store.filter((e) => e.experience_type === 'optimization_recipe').length;
  lines.push('## 汇总');
  lines.push(`- 条目总数 ${store.length}（tuning_action_effect ${nTuning} / fault_control_recipe ${nRecipe} / optimization_recipe ${nOpt}）`);
  lines.push('- 本文件由脚本确定性投影生成；效应数值全部来自 attribution_report（零 LLM）。');
  lines.push('');
  return lines.join('\n');
}

// ---------------------------------------------------------------- commands

function loadStore(runDir) {
  const p = path.join(runDir, '06_experience', 'tuning_experience.jsonl');
  if (!fs.existsSync(p)) return [];
  return fs.readFileSync(p, 'utf-8').split(/\r?\n/).filter(Boolean).map((l) => JSON.parse(l));
}

// B1: batch rejection — an invalid action_log rejects the whole ingest WITHOUT
// writing the store (the CLI analogue of the API's 400).
function validateActionLog(log, ENUMS) {
  const errs = [];
  const req = (cond, msg) => { if (!cond) errs.push(msg); };
  req(log && typeof log === 'object' && !Array.isArray(log), 'not a JSON object');
  if (!log || typeof log !== 'object') return errs;
  req(log.schema_version === '1.0', 'schema_version must be "1.0"');
  req(typeof log.ts === 'string' && log.ts.length > 0, 'missing ts');
  req(!!(log.actor && typeof log.actor.actor_id === 'string' && log.actor.actor_id.length),
    'missing actor.actor_id');
  req(!!(log.actor && (ENUMS.tuning_memory.actor_types || []).includes(log.actor.actor_type)),
    `bad actor_type ${log.actor && log.actor.actor_type}`);
  req(Array.isArray(log.actions) && log.actions.length >= 1 && log.actions.length <= 10,
    'actions must be an array of 1..10');
  for (const [i, a] of (log.actions || []).entries()) {
    req(!!(a && typeof a.parameter === 'string' && a.parameter.length), `actions[${i}] missing parameter`);
    req(!!(a && typeof a.to === 'number' && Number.isFinite(a.to)), `actions[${i}] missing numeric to`);
    req(!!(a && typeof a.unit === 'string' && a.unit.length), `actions[${i}] missing unit`);
  }
  req(!!(log.context && typeof log.context === 'object'), 'missing context');
  const bt = log.bundled_action ? log.bundled_action.bundle_reason : undefined;
  if (bt !== undefined) req(['coupled_move', 'recipe_change', 'single', null].includes(bt), `bad bundle_reason ${bt}`);
  const tt = log.trigger ? log.trigger.trigger_type : undefined;
  if (tt !== undefined) req((ENUMS.tuning_memory.trigger_types || []).includes(tt), `bad trigger_type ${tt}`);
  const ot = log.outcome ? log.outcome.observed_trajectory : undefined;
  if (ot !== undefined) req([...(ENUMS.tuning_memory.observed_trajectories || []), null].includes(ot), `bad observed_trajectory ${ot}`);
  const src = log.ingest_meta ? log.ingest_meta.source : undefined;
  if (src !== undefined) req(['api', 'csv_import', 'retro_mined', null].includes(src), `bad ingest_meta.source ${src}`);
  const cf = log.attribution_confounds;
  if (cf !== undefined) {
    req(Array.isArray(cf) && cf.every((c) => ['batch_change', 'environment', 'maintenance', 'other_action'].includes(c && c.type)),
      'bad attribution_confounds[].type');
  }
  return errs;
}

function loadState(runDir) {
  const p = path.join(runDir, '06_experience', 'accumulated', 'state.json');
  const s = j(p);
  if (s && s.version) return s;
  return { version: '1.0', updated_at: null, history: [], counters: {} };
}

function cmdBuild(args) {
  const runDir = path.resolve(args['run-dir']);
  if (!fs.existsSync(runDir)) { console.error(`run_dir not found: ${runDir}`); process.exit(2); }
  const ENUMS = j(ENUMS_PATH) || { tuning_memory: {} };
  const aliasMap = args['alias-map'] ? (readJsonArg(args['alias-map'], runDir) || {}) : {};
  const logs = loadActionLogs(args['action-log'] || '00_input/action_log.json', runDir);
  if (!logs.length) { console.error('no action logs found'); process.exit(2); }
  // B1: schema-level batch rejection (exit 3) — nothing is persisted on any error
  const rejects = [];
  for (const { id, log } of logs) {
    for (const err of validateActionLog(log, ENUMS)) rejects.push(`${id}: ${err}`);
  }
  if (rejects.length) {
    for (const r of rejects) console.error(`[experience_build] REJECT ${r}`);
    console.error(`[experience_build] ${rejects.length} validation error(s) — action_log batch rejected, nothing written`);
    process.exit(3);
  }
  const reportsDir = path.join(runDir, '06_experience', 'attribution');
  const faultSig = j(path.join(runDir, '00_input', 'fault_signature.json'));
  const store = loadStore(runDir);
  const state = loadState(runDir);
  const events = [];
  for (const { id, log } of logs) {
    const retro = ((log.ingest_meta || {}).source === 'retro_mined');
    let report = null;
    if (!retro) {
      report = j(path.join(reportsDir, `${id}.json`));
      if (!report) { events.push(`SKIP ${id}: no attribution report (run tune_stats first)`); continue; }
      if (report.attribution_status === 'not_estimable') {
        events.push(`SKIP ${id}: attribution_status=not_estimable (admission rule)`); continue;
      }
    }
    const entry = buildTuningEntry(id, log, report, aliasMap, retro);
    const confirm = unconfirmedCheck(log, runDir);
    if (confirm) entry.payload.confirm_status = confirm;
    const res = upsert(store, entry, id, runDir, state);
    events.push(`${res} ${id} -> ${entry.chunk_id}`);
    if (res === 'created') state.history.push({ ts: nowIso(), chunk_id: entry.chunk_id, result: 'build', note: null });
    const trig = log.trigger || {};
    if (trig.trigger_type === 'alert' && trig.ref_id && faultSig) {
      const recipe = buildRecipeEntry(id, log, report, aliasMap, faultSig);
      const rres = upsert(store, recipe, id, runDir, state);
      events.push(`${rres} ${id} (recipe) -> ${recipe.chunk_id}`);
      if (rres === 'created') state.history.push({ ts: nowIso(), chunk_id: recipe.chunk_id, result: 'build_recipe', note: null });
    }
  }
  refreshCrossRegime(store);
  for (const e of store) {
    const { grade, label } = computeGrade(e);
    e.evidence_grade = grade;
    e.confidence_label = label;
  }
  const expDir = path.join(runDir, '06_experience');
  fs.mkdirSync(path.join(expDir, 'accumulated'), { recursive: true });
  writeStore(path.join(expDir, 'tuning_experience.jsonl'), store);
  writeState(path.join(expDir, 'accumulated', 'state.json'), state);
  fs.writeFileSync(path.join(expDir, 'kb_summary.md'), buildKbSummary(path.basename(runDir), store), 'utf-8');
  for (const ev of events) console.log(`[experience_build] ${ev}`);
  console.log(`[experience_build] store=${store.length} entries; kb_summary.md written`);
  return 0;
}

function cmdFeedback(args) {
  const runDir = path.resolve(args['run-dir']);
  const chunk = args['chunk-id'];
  const result = args.result;
  const ENUMS = j(ENUMS_PATH) || { tuning_memory: { feedback_results: ['effective', 'ineffective', 'harmful', 'confirmed'] } };
  const allowed = ENUMS.tuning_memory.feedback_results;
  if (!chunk || !allowed.includes(result)) {
    console.error(`usage: feedback --run-dir DIR --chunk-id ID --result <${allowed.join('|')}> [--note ...]`);
    process.exit(2);
  }
  const store = loadStore(runDir);
  const entry = store.find((e) => e.chunk_id === chunk);
  if (!entry) { console.error(`chunk_id not found in local store: ${chunk}`); process.exit(1); }
  const state = loadState(runDir);
  if (result === 'effective') {
    entry.corroboration_count = (entry.corroboration_count || 0) + 1;
  } else if (result === 'ineffective' || result === 'harmful') {
    entry.refutation_count = (entry.refutation_count || 0) + 1;
  } else if (result === 'confirmed') {
    entry.payload.confirm_status = 'confirmed'; // retro ownership completion (E0 lock stays)
  }
  state.history.push({ ts: nowIso(), chunk_id: chunk, result, note: args.note || null });
  state.counters[chunk] = { corroboration: entry.corroboration_count || 0, refutation: entry.refutation_count || 0 };
  refreshCrossRegime(store);
  for (const e of store) {
    const { grade, label } = computeGrade(e);
    e.evidence_grade = grade;
    e.confidence_label = label;
  }
  const expDir = path.join(runDir, '06_experience');
  writeStore(path.join(expDir, 'tuning_experience.jsonl'), store);
  writeState(path.join(expDir, 'accumulated', 'state.json'), state);
  fs.writeFileSync(path.join(expDir, 'kb_summary.md'), buildKbSummary(path.basename(runDir), store), 'utf-8');
  console.log(`[experience_build] feedback ${result} applied to ${chunk}: `
    + `corroboration=${entry.corroboration_count} refutation=${entry.refutation_count} `
    + `grade=${entry.evidence_grade} label=${entry.confidence_label}`);
  return 0;
}

const args = parseArgs(process.argv.slice(2));
const cmd = args._[0];
if (cmd === 'build') process.exit(cmdBuild(args));
else if (cmd === 'feedback') process.exit(cmdFeedback(args));
else {
  console.error('usage: experience_build.mjs build|feedback --run-dir DIR ...');
  process.exit(2);
}
