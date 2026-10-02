#!/usr/bin/env node
// match_playbook.mjs — local signature matching against the IDD-local experience
// store, producing conclusions/recommendation.json (playbook hit or degradation),
// plus the ack subcommand for the execution-receipt chain.
//
// Matching (two-stage, plan §4.1):
//   1. hard filter with progressive relaxation: regime -> product -> machine -> generic
//   2. score = 0.5 * direction-hit + 0.3 * parameter Jaccard + 0.2 * regime-overlap
//      threshold 0.55 for playbook_hit
// Direction semantics (documented in resources/signature_matching.md):
//   fault_control_recipe entries record the FAULT direction (fault_signature);
//   tuning_action_effect entries record the APPLIED-MOVE direction (sign of to-from).
//   A hit means the recorded direction agrees with the query direction.
//
// v1.4: IDD is a PURE ANALYSIS system. evidence_grade is advisory strength only —
// dispatch policy ("autonomy") is decided exclusively by the AWS side and is
// NEVER written by this script (the autonomy_level field stays absent).
//
// Usage:
//   node match_playbook.mjs recommend --run-dir RUN_DIR [--signature 00_input/fault_signature.json]
//                                      [--out conclusions/recommendation.json] [--top 3]
//   node match_playbook.mjs ack --run-dir RUN_DIR --ack-file <ack-{ts}-{seq}.json>

import fs from 'fs';
import path from 'path';
import crypto from 'crypto';
import { fileURLToPath } from 'url';

const SCRIPT_VERSION = 'match_playbook/1.0';
const REPO_ROOT = path.resolve(path.join(path.dirname(fileURLToPath(import.meta.url)), '..', '..', '..', '..'));
const ENUMS_PATH = path.join(REPO_ROOT, '.claude', 'shared', 'schemas', 'closedloop_enums.json');

const j = (p) => { try { return JSON.parse(fs.readFileSync(p, 'utf-8')); } catch { return null; } };
const nowIso = () => new Date().toISOString();

function canon(obj) {
  if (obj === null || typeof obj !== 'object') return JSON.stringify(obj ?? null);
  if (Array.isArray(obj)) return '[' + obj.map(canon).join(',') + ']';
  const keys = Object.keys(obj).filter((k) => obj[k] !== undefined).sort();
  return '{' + keys.map((k) => JSON.stringify(k) + ':' + canon(obj[k])).join(',') + '}';
}

function parseArgs(argv) {
  const args = { _: [] };
  for (let i = 0; i < argv.length; i++) {
    if (argv[i].startsWith('--')) args[argv[i].slice(2)] = (i + 1 < argv.length && !argv[i + 1].startsWith('--')) ? argv[++i] : true;
    else args._.push(argv[i]);
  }
  return args;
}

function regimeSlots(rk) {
  const [product, machine, label] = String(rk || '-|-|-').split('|');
  return { product: product || null, machine: machine || null, label: label || null };
}

function entryParamDirections(entry) {
  // map: parameter -> {direction, source}
  // primary: local-envelope param_directions (move/fault direction per parameter,
  // written by experience_build); fallback: derive from action_sequence from/to
  const map = new Map();
  const add = (param, dir, src) => {
    if (!param) return;
    map.set(String(param), { direction: dir || 'unknown', source: src });
  };
  if (entry.experience_type === 'fault_control_recipe') {
    for (const p of ((entry.payload || {}).fault_signature || {}).anomalous_params || []) {
      add(p.parameter, p.direction, 'fault_signature');
    }
  }
  for (const [param, dir] of Object.entries(entry.param_directions || {})) {
    add(param, dir, 'param_directions');
  }
  for (const a of (entry.payload || {}).action_sequence || []) {
    if (map.has(String(a.parameter))) continue;
    let dir = 'unknown';
    if (a.from !== null && a.from !== undefined && a.to !== null && a.to !== undefined) {
      dir = a.to > a.from ? 'high' : (a.to < a.from ? 'low' : 'unknown');
    }
    add(a.parameter, dir, 'action_sequence');
  }
  return map;
}

function scoreEntry(query, entry) {
  const qParams = query.anomalous_params || [];
  const eMap = entryParamDirections(entry);
  let dirHits = 0;
  for (const p of qParams) {
    const rec = eMap.get(String(p.parameter));
    if (rec && rec.direction !== 'unknown' && p.direction !== 'unknown'
        && rec.direction === p.direction) dirHits += 1;
  }
  const dir = qParams.length ? dirHits / qParams.length : 0;
  const qSet = new Set(qParams.map((p) => String(p.parameter)));
  const eSet = new Set([...eMap.keys()]);
  let inter = 0;
  for (const p of qSet) if (eSet.has(p)) inter += 1;
  const union = new Set([...qSet, ...eSet]).size || 1;
  const jac = inter / union;
  const qr = query.regime || {};
  const es = regimeSlots(entry.regime_key);
  let condChecked = 0;
  let condHit = 0;
  for (const [qk, ek] of [[qr.product, es.product], [qr.machine, es.machine], [qr.regime_label, es.label]]) {
    if (qk === null || qk === undefined) continue;
    condChecked += 1;
    if (qk === ek) condHit += 1;
  }
  const cond = condChecked ? condHit / condChecked : 0;
  const score = Math.round((0.5 * dir + 0.3 * jac + 0.2 * cond) * 10000) / 10000;
  return { score, dir, jac, cond };
}

function scopeFilter(scope, queryRk, entries) {
  const qs = regimeSlots(queryRk);
  if (scope === 'regime') return entries.filter((e) => e.regime_key === queryRk);
  if (scope === 'product') return entries.filter((e) => qs.product && regimeSlots(e.regime_key).product === qs.product);
  if (scope === 'machine') return entries.filter((e) => qs.machine && regimeSlots(e.regime_key).machine === qs.machine);
  return entries;
}

function buildRecommendationId(rec) {
  const d = new Date();
  const p = (n, w = 2) => String(n).padStart(w, '0');
  const ts = `${d.getUTCFullYear()}${p(d.getUTCMonth() + 1)}${p(d.getUTCDate())}-${p(d.getUTCHours())}${p(d.getUTCMinutes())}${p(d.getUTCSeconds())}`;
  const nnn = parseInt(crypto.createHash('sha256').update(canon(rec)).digest('hex').slice(0, 6), 16) % 1000;
  return `REC-${ts}-${String(nnn).padStart(3, '0')}`;
}

function playbookOf(entry, sc) {
  const p = entry.payload || {};
  const expected = p.effect
    ? { delta: p.effect.delta, ci95: p.effect.ci95, metric: p.effect.metric,
        direction_established: p.effect.direction_established }
    : null;
  return {
    experience_id: entry.chunk_id,
    action_sequence: p.action_sequence || [],
    expected_effect: expected,
    // advisory strength only — dispatch authorization is an AWS-side concern
    evidence_grade: entry.evidence_grade || 'E0',
    corroboration_count: entry.corroboration_count ?? null,
    refutation_count: entry.refutation_count ?? null,
    provenance_alias: (entry.provenance || {}).actor_alias || null,
    invalidation_conditions: entry.invalidation_conditions || [],
    match_score: sc.score,
    // v1.4: the frozen contract keeps this field as the AWS-side dispatch-policy
    // carrier; IDD ALWAYS writes null (never sets a policy itself)
    autonomy_level: null,
  };
}

const DOE_HINT = '本地经验库无可用命中：建议 (1) 对该工况数据运行 industrial-doe-analyzer '
  + '观察模式分析以积累首个窗口经验；或 (2) 由 AWS 侧经 kb_agent 查询知识库宽知识后再决策。';

function cmdRecommend(args) {
  const runDir = path.resolve(args['run-dir']);
  if (!fs.existsSync(runDir)) { console.error(`run_dir not found: ${runDir}`); process.exit(2); }
  const ENUMS = j(ENUMS_PATH);
  const THRESH = 0.55;
  const sigPath = args.signature || '00_input/fault_signature.json';
  const sig = j(path.isAbsolute(sigPath) ? sigPath : path.join(runDir, sigPath));
  if (!sig || !Array.isArray(sig.anomalous_params) || !sig.anomalous_params.length) {
    console.error('fault_signature missing or has no anomalous_params'); process.exit(2);
  }
  const storePath = path.join(runDir, '06_experience', 'tuning_experience.jsonl');
  const store = fs.existsSync(storePath)
    ? fs.readFileSync(storePath, 'utf-8').split(/\r?\n/).filter(Boolean).map((l) => JSON.parse(l))
    : [];
  const qRk = `${(sig.regime || {}).product || '-'}|${(sig.regime || {}).machine || '-'}|${(sig.regime || {}).regime_label || '-'}`;

  const degradation = [];
  let hit = null;
  for (const scope of ENUMS.tuning_memory.match_scopes) { // regime -> product -> machine -> generic
    const pool = scopeFilter(scope, qRk, store);
    if (!pool.length) { degradation.push(`${scope}: 0 candidates`); continue; }
    const scored = pool.map((e) => ({ e, sc: scoreEntry(sig, e) }))
      .sort((a, b) => b.sc.score - a.sc.score || a.e.chunk_id.localeCompare(b.e.chunk_id));
    const best = scored[0];
    degradation.push(`${scope}: best ${best.sc.score.toFixed(4)} (${best.e.chunk_id})`);
    if (best.sc.score >= THRESH) {
      hit = { scope, scored };
      break;
    }
  }

  let status;
  let playbooks = [];
  let matchScope = null;
  let fallback = null;
  if (hit) {
    status = 'playbook_hit';
    matchScope = hit.scope;
    const topN = parseInt(args.top || '3', 10);
    playbooks = hit.scored.filter((s) => s.sc.score >= THRESH).slice(0, topN)
      .map((s) => playbookOf(s.e, s.sc));
    degradation.push(`-> playbook_hit @${hit.scope}`);
  } else {
    const allScored = store.map((e) => ({ e, sc: scoreEntry(sig, e) }))
      .sort((a, b) => b.sc.score - a.sc.score);
    const best = allScored[0] || null;
    if (best && best.sc.score > 0 && best.sc.dir > 0) {
      status = 'direction_only';
      playbooks = allScored.slice(0, parseInt(args.top || '3', 10))
        .filter((s) => s.sc.score > 0).map((s) => playbookOf(s.e, s.sc));
      degradation.push('-> direction_only (仅方向知识，未见完整 playbook)');
    } else if (store.length === 0) {
      status = 'no_playbook_hit';
      degradation.push('-> no_playbook_hit (本地经验库为空)');
      fallback = { doe_analyzer_hint: DOE_HINT };
    } else {
      status = 'fallback_generic';
      degradation.push('-> fallback_generic (参数重叠不足，回落 doe-analyzer 提示)');
      fallback = { doe_analyzer_hint: DOE_HINT };
    }
  }

  const rec = {
    contract_version: '1.0',
    recommendation_id: 'REC-PENDING',
    generated_at: nowIso(),
    source: {
      fault_signature: sig,
      trigger_alert_id: sig.source_ref || null,
      campaign_id: null,
    },
    recommendation_status: status,
    match_scope: matchScope,
    degradation_path: degradation,
    playbooks,
    final_setpoints: null, // optimizer convergence path only (Workstream C)
    fallback,
    ack: null, // filled by `ack` subcommand when the execution receipt arrives
    provenance: { script_version: SCRIPT_VERSION, authored_by: 'script' },
    // NOTE (v1.4): autonomy_level is intentionally ABSENT — IDD never sets a
    // dispatch policy; evidence grades above are advisory strength only.
  };
  rec.recommendation_id = buildRecommendationId(rec);

  const outPath = path.isAbsolute(args.out || 'conclusions/recommendation.json')
    ? args.out : path.join(runDir, args.out || 'conclusions/recommendation.json');
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  fs.writeFileSync(outPath, JSON.stringify(rec, null, 2), 'utf-8');
  console.log(`[match_playbook] ${status}${matchScope ? ` @${matchScope}` : ''} `
    + `playbooks=${playbooks.length} -> ${path.relative(runDir, outPath)}`);
  console.log('[match_playbook] evidence grades are advisory strength only — '
    + 'dispatch policy is AWS-side');
  return 0;
}

function cmdAck(args) {
  const runDir = path.resolve(args['run-dir']);
  const ackPath = path.isAbsolute(args['ack-file'] || '')
    ? args['ack-file'] : path.join(runDir, args['ack-file'] || '');
  const ack = j(ackPath);
  const ENUMS = j(ENUMS_PATH);
  if (!ack || !ack.recommendation_id || !ENUMS.ack.statuses.includes(ack.status)) {
    console.error(`ack file invalid (need {recommendation_id, status in ${ENUMS.ack.statuses.join('|')}}): ${ackPath}`);
    process.exit(2);
  }
  const recPath = path.join(runDir, 'conclusions', 'recommendation.json');
  const rec = j(recPath);
  if (!rec || rec.recommendation_id !== ack.recommendation_id) {
    console.error(`recommendation.json does not match ack.recommendation_id=${ack.recommendation_id}`);
    process.exit(1);
  }
  rec.ack = {
    status: ack.status,
    ack_at: nowIso(),
    executed_action_log_id: ack.executed_action_log_id || null,
    note: ack.note || null,
  };
  fs.writeFileSync(recPath, JSON.stringify(rec, null, 2), 'utf-8');
  console.log(`[match_playbook] ack ${ack.status} recorded for ${rec.recommendation_id}`);
  return 0;
}

const args = parseArgs(process.argv.slice(2));
const cmd = args._[0];
if (cmd === 'recommend') process.exit(cmdRecommend(args));
else if (cmd === 'ack') process.exit(cmdAck(args));
else {
  console.error('usage: match_playbook.mjs recommend|ack --run-dir DIR ...');
  process.exit(2);
}
