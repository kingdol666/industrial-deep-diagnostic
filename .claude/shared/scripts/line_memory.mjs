#!/usr/bin/env node
/**
 * Line Memory — 跨 run 产线记忆核心（确定性、零 LLM、零外部依赖）
 * ================================================================
 * 设计纪律（继承 tuning-memory / stats 的既有约定）：
 *   - 所有数字来自已通过 schema 验证的产物字段；提取器绝不臆造
 *   - 共性晋升规则完全确定性：独立性去重 + 计数/反证台账 + 时间衰减
 *   - 每条 finding 带 run_id 与工件 sha256 溯源；每条共识可回放到 run
 *
 * 存储布局（默认 data/line_memory，可用 LINE_MEMORY_DIR 覆盖）：
 *   lines.json                     线注册表（line_key → {name, aliases[]}）
 *   proposals.jsonl                本体修订提案台账（跨线，含状态）
 *   <line_key>/findings.jsonl      逐条结论（幂等追加）
 *   <line_key>/consensus.json      派生共性快照（不可手改，可重生）
 *   <line_key>/state.json          增量状态（已挖掘 run 集合）
 *   <line_key>/overrides.json      人工裁决（refute/unrefute，最高优先级）
 *
 * 独立性定义（防同一事件重复计数）：
 *   两次观测视为"同一事件"当且仅当：
 *     a) 都有数据窗且窗口重叠率 > 50%；或
 *     b) 无数据窗且观测时间相差 < 7 天（同 7 天桶）。
 *   独立观测数 = 事件簇数。
 *
 * 分级规则（用户裁决 2026-11-03）：
 *   independent >= 3 且无方向矛盾 → consensus
 *   independent == 2            → candidate
 *   independent == 1            → singleton（仅线索，注入时标注未成熟）
 *   同主体出现相反方向           → competing（双方永久保留，不合并）
 *   一方 independent>=2 且证据级严格更强（L 值更小），另一方 independent==1
 *   且证据更弱                  → 弱方 refuted（冻结降级，保留审计）
 *   last_seen 早于 staleDays     → stale 标记（保留但降权）
 */

import { existsSync, mkdirSync, readFileSync, writeFileSync, appendFileSync, readdirSync, statSync, renameSync } from 'node:fs';
import { dirname, join, resolve, relative, basename } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';

const __dirname = dirname(fileURLToPath(import.meta.url));
export const PROJECT_ROOT = resolve(__dirname, '..', '..', '..');

export const CONTRACT_VERSION = 'line-memory/1.0';
export const FINDING_CONTRACT = 'finding-record/1.0';
export const PROPOSAL_CONTRACT = 'ontology-proposal/1.0';

export const DEFAULT_STALE_DAYS = 90;
export const DEFAULT_MIN_INDEPENDENT = 3;
const INCIDENT_WINDOW_OVERLAP_RATIO = 0.5;
const INCIDENT_TIME_GAP_MS = 7 * 24 * 3600 * 1000;

const SEVERITY_RANK = { info: 0, warn: 1, high: 2, critical: 3 };
const GRADE_ORDER = { consensus: 0, candidate: 1, competing: 2, singleton: 3, refuted: 4 };

// ── Utilities ────────────────────────────────────────────────────────────

export function sha256(input) {
  return 'sha256:' + createHash('sha256').update(input).digest('hex');
}

export function sha256File(absPath) {
  try { return sha256(readFileSync(absPath)); } catch { return null; }
}

export function slugify(text) {
  return String(text || '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 64);
}

function readJson(absPath) {
  try { return JSON.parse(readFileSync(absPath, 'utf-8')); } catch { return null; }
}

function readJsonl(absPath) {
  try {
    return readFileSync(absPath, 'utf-8')
      .split('\n')
      .map((l) => l.trim())
      .filter(Boolean)
      .map((l) => { try { return JSON.parse(l); } catch { return null; } })
      .filter(Boolean);
  } catch { return []; }
}

function atomicWrite(absPath, content) {
  mkdirSync(dirname(absPath), { recursive: true });
  const tmp = absPath + '.tmp-' + process.pid;
  writeFileSync(tmp, content);
  try { renameSync(tmp, absPath); } catch { writeFileSync(absPath, content); }
}

function writeJson(absPath, obj) {
  atomicWrite(absPath, JSON.stringify(obj, null, 2));
}

function relPath(fromDir, absPath) {
  return relative(fromDir, absPath).replace(/\\/g, '/');
}

function evidenceNum(level) {
  const m = /^L([1-7])$/.exec(String(level || ''));
  return m ? Number(m[1]) : 7;
}

function severityRank(s) { return SEVERITY_RANK[s] ?? -1; }

export function defaultStoreDir() {
  return process.env.LINE_MEMORY_DIR
    ? resolve(process.env.LINE_MEMORY_DIR)
    : join(PROJECT_ROOT, 'data', 'line_memory');
}

// ── Store: registry / findings / consensus / state ───────────────────────

export function ensureStore(storeDir = defaultStoreDir()) {
  mkdirSync(storeDir, { recursive: true });
  const regPath = join(storeDir, 'lines.json');
  if (!existsSync(regPath)) {
    writeJson(regPath, { version: 1, generated_at: new Date().toISOString(), lines: {} });
  }
  return storeDir;
}

export function readRegistry(storeDir = defaultStoreDir()) {
  ensureStore(storeDir);
  const reg = readJson(join(storeDir, 'lines.json'));
  return reg && reg.lines ? reg : { version: 1, generated_at: null, lines: {} };
}

function writeRegistry(storeDir, reg) {
  reg.generated_at = new Date().toISOString();
  writeJson(join(storeDir, 'lines.json'), reg);
}

/**
 * 注册 / 更新一条产线。aliases 里的每个别名都可用于后续 line 解析。
 * @returns {{lineKey: string, entry: object}}
 */
export function registerLine(storeDir, { lineKey, name = null, aliases = [] }) {
  const key = slugify(lineKey);
  if (!key) throw new Error(`invalid line_key: ${JSON.stringify(lineKey)}`);
  const reg = readRegistry(storeDir);
  const now = new Date().toISOString();
  const prev = reg.lines[key] || { name: null, aliases: [], created_at: now };
  const aliasSet = new Set([...(prev.aliases || []), ...aliases.map((a) => String(a || '').trim()).filter(Boolean)]);
  const entry = {
    ...prev,
    line_key: key,
    name: name || prev.name || key,
    aliases: [...aliasSet].sort(),
    updated_at: now,
  };
  reg.lines[key] = entry;
  writeRegistry(storeDir, reg);
  return { lineKey: key, entry };
}

/** 通过别名（scene_key / scene_name / line_id 原文）反查已注册产线。 */
export function findLineByAlias(storeDir, alias) {
  const needle = String(alias || '').trim();
  if (!needle) return null;
  const reg = readRegistry(storeDir);
  const needleSlug = slugify(needle);
  for (const [key, entry] of Object.entries(reg.lines)) {
    if (key === needleSlug) return { lineKey: key, entry };
    if ((entry.aliases || []).includes(needle)) return { lineKey: key, entry };
    if ((entry.aliases || []).some((a) => slugify(a) === needleSlug)) return { lineKey: key, entry };
    if (slugify(entry.name) === needleSlug) return { lineKey: key, entry };
  }
  return null;
}

export function lineDir(storeDir, lineKey) {
  return join(storeDir, slugify(lineKey));
}

export function readFindings(storeDir, lineKey) {
  return readJsonl(join(lineDir(storeDir, lineKey), 'findings.jsonl'));
}

/**
 * 幂等追加 findings：以 finding_id 去重；已存在的跳过。
 * @returns {{added:number, skipped:number}}
 */
export function appendFindings(storeDir, lineKey, findings) {
  const dir = lineDir(storeDir, lineKey);
  mkdirSync(dir, { recursive: true });
  const file = join(dir, 'findings.jsonl');
  const existing = new Set(readJsonl(file).map((f) => f.finding_id));
  const fresh = [];
  for (const f of findings || []) {
    if (!f || !f.finding_id) continue;
    if (existing.has(f.finding_id)) continue;
    existing.add(f.finding_id);
    fresh.push(f);
  }
  if (fresh.length) appendFileSync(file, fresh.map((f) => JSON.stringify(f)).join('\n') + '\n');
  return { added: fresh.length, skipped: (findings || []).length - fresh.length };
}

export function readConsensus(storeDir, lineKey) {
  return readJson(join(lineDir(storeDir, lineKey), 'consensus.json'));
}

function writeConsensus(storeDir, lineKey, consensus) {
  writeJson(join(lineDir(storeDir, lineKey), 'consensus.json'), consensus);
}

export function readState(storeDir, lineKey) {
  return readJson(join(lineDir(storeDir, lineKey), 'state.json')) || { version: 1, mined_run_ids: [], last_consolidated: null };
}

function writeState(storeDir, lineKey, state) {
  writeJson(join(lineDir(storeDir, lineKey), 'state.json'), state);
}

export function readOverrides(storeDir, lineKey) {
  return readJson(join(lineDir(storeDir, lineKey), 'overrides.json')) || { version: 1, entries: {} };
}

export function writeOverrides(storeDir, lineKey, overrides) {
  writeJson(join(lineDir(storeDir, lineKey), 'overrides.json'), overrides);
}

// ── Line identity resolution ─────────────────────────────────────────────

/**
 * 从 run 产物解析稳定产线身份。优先级：
 *   1. line_report/stability_report.json 的 line.line_id（最权威）
 *   2. 00_input/report_context.json / 00_input/context/report_context.json 的 line_id
 *   3. 注册表别名命中（scene_key / scene_name）
 *   4. 01_ontology/ontology.json 的 scene.name / 数据自述里的线名
 *   5. 兜底：scene_name / scene_key 的 slug
 * @returns {{lineKey:string, lineName:string, aliases:string[], source:string}}
 */
export function resolveLineIdentity({ storeDir = defaultStoreDir(), runDir = null, sceneKey = null, sceneName = null } = {}) {
  const aliases = [];
  let lineIdRaw = null;
  let source = 'fallback';

  const pushAlias = (v) => { if (v && !aliases.includes(String(v))) aliases.push(String(v)); };
  pushAlias(sceneKey);
  pushAlias(sceneName);

  if (runDir) {
    const stability = readJson(join(runDir, 'line_report', 'stability_report.json'));
    if (stability && stability.line && stability.line.line_id) {
      lineIdRaw = String(stability.line.line_id);
      source = 'stability_report.line.line_id';
      pushAlias(lineIdRaw);
      if (stability.line.product) pushAlias(stability.line.product);
    }
    if (!lineIdRaw) {
      for (const p of ['00_input/report_context.json', '00_input/context/report_context.json']) {
        const ctx = readJson(join(runDir, p));
        if (ctx && ctx.line_id) {
          lineIdRaw = String(ctx.line_id);
          source = p + '.line_id';
          pushAlias(lineIdRaw);
          break;
        }
      }
    }
    if (!lineIdRaw) {
      const alert = readJson(join(runDir, 'sentinel', 'alert.json'));
      if (alert && alert.ontology && alert.ontology.line_id) {
        lineIdRaw = String(alert.ontology.line_id);
        source = 'sentinel/alert.json.ontology.line_id';
        pushAlias(lineIdRaw);
      }
    }
    if (!lineIdRaw) {
      const ontology = readJson(join(runDir, '01_ontology', 'ontology.json'));
      const sceneName2 = ontology && ontology.scene && ontology.scene.name;
      if (sceneName2) {
        pushAlias(sceneName2);
        if (!lineIdRaw && /[a-z0-9]/i.test(slugify(sceneName2))) {
          lineIdRaw = String(sceneName2);
          source = 'ontology.scene.name';
        }
      }
    }
  }

  // 先按别名反查已注册线（避免同线因 scene 后缀差异碎成多线）
  for (const alias of aliases) {
    const hit = findLineByAlias(storeDir, alias);
    if (hit) {
      return { lineKey: hit.lineKey, lineName: hit.entry.name || hit.lineKey, aliases, source: 'registry-alias:' + alias };
    }
  }

  const keySource = lineIdRaw || sceneKey || sceneName || '';
  let lineKey = slugify(keySource);
  if (!lineKey) lineKey = 'line-' + sha256(String(keySource || runDir || Date.now())).slice(7, 15);
  return { lineKey, lineName: lineIdRaw || sceneName || sceneKey || lineKey, aliases, source };
}

// ── Extraction (deterministic, per intent) ───────────────────────────────

function mkFinding(ctx, { subject, claim_type, direction = null, severity = null, confidence = null, evidence_level = 'L4', detail = '', payload = {}, window: dataWindow = null, sources = [], srcId = null }) {
  const findingId = 'F-' + String(ctx.runId).replace(/[^a-zA-Z0-9]/g, '').toLowerCase().slice(0, 12) + '-' +
    sha256([ctx.runId, subject, claim_type, direction || '-', (dataWindow && dataWindow.start) || '-', srcId || '-'].join('|')).slice(7, 15);
  return {
    contract_version: FINDING_CONTRACT,
    finding_id: findingId,
    line_key: ctx.lineKey,
    scene_key: ctx.sceneKey || null,
    intent: ctx.intent,
    run_id: ctx.runId,
    observed_at: ctx.observedAt,
    data_window: dataWindow,
    subject: String(subject || '__line__').slice(0, 120),
    claim_type: String(claim_type || 'finding').slice(0, 60),
    direction: direction === 'up' || direction === 'down' ? direction : null,
    severity: severity || null,
    confidence: Number.isFinite(Number(confidence)) ? Number(confidence) : null,
    evidence_level,
    detail: String(detail || '').slice(0, 600),
    payload,
    sources,
  };
}

function fileSource(runDir, absPath) {
  const sha = sha256File(absPath);
  return sha ? { path: relPath(runDir, absPath), sha256: sha } : null;
}

function looksLikeNumber(v) { return typeof v === 'number' && Number.isFinite(v); }

function extractStability(runDir, ctx) {
  const p = join(runDir, 'line_report', 'stability_report.json');
  const j = readJson(p);
  if (!j) return [];
  const src = fileSource(runDir, p);
  const sources = src ? [src] : [];
  const period = j.period || {};
  const window = (period.start || period.end) ? { start: period.start || null, end: period.end || null } : null;
  const out = [];

  for (const f of j.findings || []) {
    const claim = f.category === 'spc' ? 'spc_violation' : String(f.category || 'finding');
    const affected = Array.isArray(f.affected) && f.affected.length ? f.affected.slice(0, 8) : ['__line__'];
    for (const subject of affected) {
      out.push(mkFinding(ctx, {
        subject, claim_type: claim, severity: f.severity || null,
        confidence: f.confidence ?? null, evidence_level: 'L3',
        detail: [f.title, f.detail].filter(Boolean).join(' — '),
        payload: { artifact_finding_id: f.finding_id || null, evidence: Array.isArray(f.evidence) ? f.evidence.slice(0, 6) : null },
        window, sources, srcId: f.finding_id || null,
      }));
    }
  }

  for (const prm of j.parameters || []) {
    const d = prm.drift;
    if (!d || d.significant !== true) continue;
    const rel = Number(d.per_day_relative);
    const direction = rel > 0 ? 'up' : rel < 0 ? 'down' : null;
    out.push(mkFinding(ctx, {
      subject: prm.name || 'unknown', claim_type: 'drift', direction,
      severity: 'high', confidence: 85, evidence_level: 'L3',
      detail: `相对漂移 ${looksLikeNumber(rel) ? (rel * 100).toFixed(2) : '?'}%/天; mk_p=${d.mk_p ?? 'n/a'}; score=${prm.score ?? 'n/a'}`,
      payload: { per_day_relative: d.per_day_relative ?? null, slope_per_second: d.slope_per_second ?? null, score: prm.score ?? null },
      window, sources, srcId: 'drift:' + (prm.name || ''),
    }));
  }

  const c = j.conclusion;
  if (c && (c.score != null || c.statement)) {
    const grade = String(c.grade || '');
    const sev = grade === 'D' ? 'high' : grade === 'C' ? 'warn' : 'info';
    out.push(mkFinding(ctx, {
      subject: '__line__', claim_type: 'line_state', severity: sev, evidence_level: 'L3',
      detail: String(c.statement || '').slice(0, 400),
      payload: { score: c.score ?? null, grade: c.grade ?? null, label: c.label ?? null },
      window, sources, srcId: 'conclusion',
    }));
  }
  return out;
}

function extractQuickScreen(runDir, ctx) {
  const p = join(runDir, 'sentinel', 'alert.json');
  const j = readJson(p);
  if (!j) return [];
  const src = fileSource(runDir, p);
  const sources = src ? [src] : [];
  const winStart = j.source && j.source.window_start ? j.source.window_start : null;
  const winEnd = j.source && (j.source.window_end || j.source.window_end) ? (j.source.window_end || j.source.window_end) : null;
  const window = (winStart || winEnd) ? { start: winStart, end: winEnd } : null;
  const out = [];

  if (j.status) {
    out.push(mkFinding(ctx, {
      subject: '__line__', claim_type: 'line_state',
      severity: j.status === 'alert' ? 'warn' : 'info', evidence_level: 'L3',
      detail: `快筛状态 ${j.status}`,
      payload: { status: j.status, checks_summary: j.checks_summary || null },
      window, sources, srcId: 'status',
    }));
  }

  const groups = new Map();
  for (const a of j.alerts || []) {
    const contrib = a.evidence && Array.isArray(a.evidence.contributing_params) && a.evidence.contributing_params[0];
    const subject = a.parameter || (contrib && contrib.name) || '__line__';
    const claim = a.check_type === 'spc' ? 'spc_violation'
      : a.check_type === 'multivariate' ? 'multivariate_outlier'
        : a.check_type === 'window_projection' ? 'projection'
          : String(a.check_type || 'alert');
    const key = subject + '||' + claim;
    const g = groups.get(key) || { subject, claim, n: 0, severity: null, rules: new Set() };
    g.n += 1;
    if (severityRank(a.severity) > severityRank(g.severity)) g.severity = a.severity || g.severity;
    if (a.rule_name) g.rules.add(a.rule_name);
    groups.set(key, g);
  }
  for (const g of groups.values()) {
    out.push(mkFinding(ctx, {
      subject: g.subject, claim_type: g.claim, severity: g.severity, evidence_level: 'L3',
      detail: `${g.n} 条告警; 规则:${[...g.rules].slice(0, 4).join('/') || 'n/a'}`,
      payload: { n_alerts: g.n, rules: [...g.rules].slice(0, 8) },
      window, sources, srcId: 'group:' + g.subject + ':' + g.claim,
    }));
  }
  return out;
}

function extractDeepDiagnosis(runDir, ctx) {
  const dPath = join(runDir, '04_diagnostics', 'diagnosis.json');
  const cPath = join(runDir, '04_diagnostics', 'confidence.json');
  const d = readJson(dPath);
  const c = readJson(cPath);
  if (!d && !c) return [];
  const sources = [fileSource(runDir, dPath), fileSource(runDir, cPath)].filter(Boolean);
  const out = [];

  if (d && typeof d.primary_finding === 'string' && d.primary_finding.trim()) {
    out.push(mkFinding(ctx, {
      subject: '__line__', claim_type: 'diagnosis_conclusion', severity: 'info',
      confidence: c && Number.isFinite(Number(c.overall_confidence)) ? Number(c.overall_confidence) : null,
      evidence_level: 'L4',
      detail: d.primary_finding,
      payload: { diagnosis_type: d.diagnosis_type || null, four_condition_verdicts: d.four_condition_verdicts || null },
      sources, srcId: 'primary_finding',
    }));
  }
  const hyps = Array.isArray(d && d.hypotheses) ? d.hypotheses : [];
  for (const h of hyps.slice(0, 12)) {
    const hid = h.id || h.hypothesis_id || h.hypothesis || null;
    if (!hid) continue;
    const conf = c && c.confidence_breakdown && c.confidence_breakdown[hid] ? c.confidence_breakdown[hid].confidence_score : null;
    out.push(mkFinding(ctx, {
      subject: String(hid), claim_type: 'hypothesis', evidence_level: 'L4',
      confidence: Number.isFinite(Number(conf)) ? Number(conf) : null,
      detail: String(h.statement || h.summary || h.description || '').slice(0, 300),
      payload: { verdict: h.verdict || h.status || null },
      sources, srcId: 'hyp:' + hid,
    }));
  }
  return out;
}

function findFiles(root, predicate, maxDepth = 3, depth = 0, acc = []) {
  if (depth > maxDepth) return acc;
  let entries;
  try { entries = readdirSync(root, { withFileTypes: true }); } catch { return acc; }
  for (const e of entries) {
    const abs = join(root, e.name);
    if (e.isDirectory()) {
      if (['00_input', '01_ontology', '03_figures', 'node_modules', '.git'].includes(e.name)) continue;
      findFiles(abs, predicate, maxDepth, depth + 1, acc);
    } else if (predicate(e.name, abs)) {
      acc.push(abs);
    }
  }
  return acc;
}

function extractDoe(runDir, ctx) {
  const out = [];
  const effectFiles = findFiles(runDir, (n) => n === 'effect_table.json', 3);
  for (const p of effectFiles) {
    const j = readJson(p);
    if (!j) continue;
    const rows = Array.isArray(j) ? j : (Array.isArray(j.effects) ? j.effects : (Array.isArray(j.rows) ? j.rows : []));
    const sources = [fileSource(runDir, p)].filter(Boolean);
    for (const r of rows.slice(0, 40)) {
      const subject = r.factor || r.term || r.name || r.param || null;
      if (!subject) continue;
      const eff = looksLikeNumber(r.effect) ? r.effect : (looksLikeNumber(r.estimate) ? r.estimate : (looksLikeNumber(r.coef) ? r.coef : null));
      const sig = r.significant === true || (looksLikeNumber(r.p_value) && r.p_value < 0.05);
      out.push(mkFinding(ctx, {
        subject: String(subject), claim_type: 'factor_effect',
        direction: eff == null ? null : eff > 0 ? 'up' : eff < 0 ? 'down' : null,
        severity: sig ? 'high' : 'info', confidence: sig ? 85 : 60, evidence_level: 'L3',
        detail: `效应 ${eff == null ? '?' : eff}; p=${r.p_value ?? 'n/a'}; significant=${sig}`,
        payload: { effect: eff, p_value: r.p_value ?? null, significant: sig },
        sources, srcId: 'effect:' + subject,
      }));
    }
  }
  for (const p of findFiles(runDir, (n) => n === 'doe_conclusion.json', 3)) {
    const j = readJson(p);
    if (!j) continue;
    const text = j.summary || j.conclusion || j.statement || '';
    if (!text) continue;
    out.push(mkFinding(ctx, {
      subject: '__line__', claim_type: 'doe_conclusion', evidence_level: 'L3',
      detail: String(typeof text === 'string' ? text : JSON.stringify(text)).slice(0, 400),
      sources: [fileSource(runDir, p)].filter(Boolean), srcId: 'doe_conclusion',
    }));
  }
  return out;
}

function extractExperience(runDir, ctx) {
  const out = [];
  const dir = join(runDir, '06_experience', 'attribution');
  if (existsSync(dir)) {
    let files = [];
    try { files = readdirSync(dir).filter((n) => n.endsWith('.json')); } catch { files = []; }
    for (const name of files.slice(0, 40)) {
      const p = join(dir, name);
      const j = readJson(p);
      if (!j) continue;
      const eff = j.effect && looksLikeNumber(j.effect.delta) ? j.effect.delta : (looksLikeNumber(j.effect && j.effect.value) ? j.effect.value : null);
      out.push(mkFinding(ctx, {
        subject: String(j.target || j.parameter || (j.action && j.action.parameter) || j.action_log_id || '__line__').slice(0, 120),
        claim_type: 'tuning_action_effect',
        direction: eff == null ? null : eff > 0 ? 'up' : eff < 0 ? 'down' : null,
        severity: 'info', evidence_level: 'L2',
        detail: `归因状态 ${j.attribution_status || 'n/a'}; effect=${eff == null ? 'null' : eff}`,
        payload: { attribution_status: j.attribution_status || null, effect: eff },
        sources: [fileSource(runDir, p)].filter(Boolean), srcId: 'attr:' + name,
      }));
    }
  }
  const expFile = join(runDir, '06_experience', 'tuning_experience.jsonl');
  if (existsSync(expFile)) {
    const src = fileSource(runDir, expFile);
    for (const entry of readJsonl(expFile).slice(0, 60)) {
      const subject = entry.target || entry.parameter || entry.object || entry.action_id || null;
      if (!subject) continue;
      out.push(mkFinding(ctx, {
        subject: String(subject).slice(0, 120), claim_type: 'tuning_experience',
        evidence_level: 'L2', severity: 'info',
        detail: String(entry.claim || entry.summary || entry.statement || entry.entry_type || '').slice(0, 300),
        payload: { entry_type: entry.entry_type || null, evidence_grade: entry.evidence_grade || null },
        sources: src ? [src] : [], srcId: 'exp:' + (entry.chunk_id || subject),
      }));
    }
  }
  return out;
}

function extractOptimizer(runDir, ctx) {
  const out = [];
  const files = findFiles(runDir, (n) => n === 'campaign_state.json' || n === 'campaign_result.json' || n === 'optimizer_state.json', 3);
  for (const p of files) {
    const j = readJson(p);
    if (!j) continue;
    const converged = j.converged === true || j.status === 'converged';
    out.push(mkFinding(ctx, {
      subject: '__line__', claim_type: 'campaign_state',
      severity: converged ? 'info' : 'warn', evidence_level: 'L3',
      detail: `campaign ${converged ? '已收敛' : '未收敛'}; best=${JSON.stringify(j.best_recipe || j.best || {}).slice(0, 200)}`,
      payload: { converged, best_recipe: j.best_recipe || j.best || null, best_y: j.best_y ?? null },
      sources: [fileSource(runDir, p)].filter(Boolean), srcId: 'campaign',
    }));
  }
  return out;
}

function extractImprovement(runDir, ctx) {
  const p = join(runDir, 'advisory', 'advisory_actions.json');
  const j = readJson(p);
  if (!j) return [];
  const src = fileSource(runDir, p);
  const sources = src ? [src] : [];
  const out = [];

  for (const a of j.actions || []) {
    const g = a.expected_gain || {};
    const direction = a.direction === 'increase' ? 'up' : a.direction === 'decrease' ? 'down' : null;
    const severity = a.grade === 'A' ? 'high' : a.grade === 'B' ? 'warn' : 'info';
    out.push(mkFinding(ctx, {
      subject: a.lever_column || a.lever_param || 'unknown',
      claim_type: 'improvement_action',
      direction,
      severity,
      confidence: a.risk?.confidence_cap ?? 50,
      evidence_level: 'L3',
      detail: `[${a.grade}] ${a.lever_param} ${a.direction} → ${g.metric} `
        + `预期 ${looksLikeNumber(g.point) ? g.point : 'n/a'} `
        + `(95%CI ${JSON.stringify(g.ci95)})；${(a.grade_reasons || []).slice(0, 3).join('; ')}`,
      payload: {
        action_id: a.action_id || null,
        grade: a.grade || null,
        mechanism_status: a.mechanism_status || null,
        expected_gain: {
          metric: g.metric ?? null, point: g.point ?? null, ci95: g.ci95 ?? null,
          method: g.method ?? null, verified: g.verified ?? null,
        },
        magnitude: a.magnitude || null,
      },
      window: null,
      sources,
      srcId: a.action_id || null,
    }));
  }

  for (const c of j.goal?.conflicts || []) {
    out.push(mkFinding(ctx, {
      subject: c.lever || 'unknown',
      claim_type: 'goal_conflict',
      direction: null,
      severity: 'warn',
      confidence: 60,
      evidence_level: 'L5',
      detail: `目标冲突: ${c.target_a} 要求 ${c.direction_a} vs ${c.target_b} 要求 ${c.direction_b} — 需人工裁决`,
      payload: c,
      window: null,
      sources,
      srcId: `conflict:${c.lever}`,
    }));
  }
  return out;
}

const EXTRACTORS = {
  'stability-report': extractStability,
  'quick-screen': extractQuickScreen,
  'deep-diagnosis': extractDeepDiagnosis,
  'doe-analysis': extractDoe,
  'experience-mining': extractExperience,
  'optimizer-campaign': extractOptimizer,
  'improvement-advisory': extractImprovement,
};

/**
 * 从一个已完成的 run 提取 findings（不落盘）。缺失产物 → 空数组（不报错）。
 */
export function extractFindingsForRun({ runDir, runId, intent, sceneKey = null, sceneName = null, observedAt = null }) {
  if (!runDir || !existsSync(runDir)) return { lineKey: null, lineName: null, findings: [], identity: null };
  const identity = resolveLineIdentity({ runDir, sceneKey, sceneName });
  const extractor = EXTRACTORS[intent];
  const ctx = {
    runId, intent, sceneKey,
    lineKey: identity.lineKey,
    observedAt: observedAt || new Date().toISOString(),
  };
  const findings = extractor ? extractor(runDir, ctx) : [];
  return { lineKey: identity.lineKey, lineName: identity.lineName, aliases: identity.aliases, identitySource: identity.source, findings };
}

/**
 * 入库：提取 + 注册线 + 幂等追加 + 重新挖掘。
 * @returns {{lineKey, lineName, added, skipped, consensus, identitySource}}
 */
export function ingestRun({ storeDir = defaultStoreDir(), runDir, runId, intent, sceneKey = null, sceneName = null, observedAt = null, now = null }) {
  ensureStore(storeDir);
  const extracted = extractFindingsForRun({ runDir, runId, intent, sceneKey, sceneName, observedAt });
  if (!extracted.lineKey) return { lineKey: null, findings_added: 0, skipped: 0, consensus: null, empty: true };
  // A run whose artifacts yield no findings must not create an empty line.
  if (!extracted.findings.length) {
    return { lineKey: extracted.lineKey, lineName: extracted.lineName, findings_added: 0, skipped: 0, consensus: null, empty: true };
  }

  registerLine(storeDir, { lineKey: extracted.lineKey, name: extracted.lineName, aliases: extracted.aliases });
  const { added, skipped } = appendFindings(storeDir, extracted.lineKey, extracted.findings);
  const state = readState(storeDir, extracted.lineKey);
  if (!state.mined_run_ids.includes(runId)) state.mined_run_ids.push(runId);
  state.last_consolidated = now || new Date().toISOString();
  writeState(storeDir, extracted.lineKey, state);
  const consensus = consolidate(storeDir, extracted.lineKey, { now });
  return {
    lineKey: extracted.lineKey,
    lineName: extracted.lineName,
    findings_added: added,
    skipped,
    consensus,
    identitySource: extracted.identitySource,
  };
}

// ── Consolidation (deterministic) ────────────────────────────────────────

function parseWindow(w) {
  if (!w) return null;
  const s = Date.parse(w.start);
  const e = Date.parse(w.end);
  const out = {};
  if (Number.isFinite(s)) out.start = s;
  if (Number.isFinite(e)) out.end = e;
  if (out.start == null && out.end == null) return null;
  if (out.start == null) out.start = out.end;
  if (out.end == null) out.end = out.start;
  return out;
}

function sameIncident(a, b) {
  const wa = parseWindow(a.data_window);
  const wb = parseWindow(b.data_window);
  if (wa && wb) {
    const overlap = Math.min(wa.end, wb.end) - Math.max(wa.start, wb.start);
    const union = Math.max(wa.end, wb.end) - Math.min(wa.start, wb.start);
    if (union <= 0) return a.run_id === b.run_id;
    return overlap > 0 && overlap / union > INCIDENT_WINDOW_OVERLAP_RATIO;
  }
  const ta = Date.parse(a.observed_at);
  const tb = Date.parse(b.observed_at);
  if (Number.isFinite(ta) && Number.isFinite(tb)) return Math.abs(ta - tb) < INCIDENT_TIME_GAP_MS;
  return a.run_id === b.run_id;
}

/** 独立观测数 = 事件簇数（同一事件的多 run 只计 1）。 */
export function independentCount(observations) {
  const clusters = [];
  const sorted = [...observations].sort((x, y) => String(x.observed_at).localeCompare(String(y.observed_at)));
  for (const obs of sorted) {
    let placed = false;
    for (const cluster of clusters) {
      if (sameIncident(obs, cluster[0])) { cluster.push(obs); placed = true; break; }
    }
    if (!placed) clusters.push([obs]);
  }
  return clusters.length;
}

function computeSide(observations) {
  const sorted = [...observations].sort((x, y) => String(y.observed_at).localeCompare(String(x.observed_at)));
  const latest = sorted[0];
  const severity = sorted.reduce((best, o) => (severityRank(o.severity) > severityRank(best) ? o.severity : best), null);
  const evidenceLevel = sorted.reduce((best, o) => (evidenceNum(o.evidence_level) < evidenceNum(best) ? o.evidence_level : best), 'L7');
  const confidence = sorted.reduce((best, o) => Math.max(best, Number(o.confidence) || 0), 0) || null;
  return {
    observations: sorted,
    n: sorted.length,
    independent: independentCount(sorted),
    last_seen: latest ? latest.observed_at : null,
    severity,
    evidence_level: evidenceLevel,
    confidence,
    status: 'active',
    reasons: [],
  };
}

/**
 * 重新计算一条产线的 consensus.json（幂等、确定性）。
 * @param {object} opts {now, staleDays, minIndependent, overrides}
 */
export function consolidate(storeDir, lineKey, opts = {}) {
  const nowIso = opts.now || new Date().toISOString();
  const nowMs = Date.parse(nowIso);
  const staleDays = Number.isFinite(Number(opts.staleDays)) ? Number(opts.staleDays) : DEFAULT_STALE_DAYS;
  const minIndependent = Number.isFinite(Number(opts.minIndependent)) ? Number(opts.minIndependent) : DEFAULT_MIN_INDEPENDENT;
  const overrides = opts.overrides || readOverrides(storeDir, lineKey);
  const findings = readFindings(storeDir, lineKey);

  const groups = new Map();
  // `line_state` is a time series (one snapshot per run), not a stable claim:
  // it feeds `latest_state` only and must never be promoted to consensus.
  const nonMinable = new Set(['line_state']);
  for (const f of findings) {
    if (nonMinable.has(f.claim_type)) continue;
    const key = f.subject + '||' + f.claim_type;
    const g = groups.get(key) || { entry_key: key, subject: f.subject, claim_type: f.claim_type, byDirection: new Map() };
    const dirKey = f.direction || '-';
    const list = g.byDirection.get(dirKey) || [];
    list.push(f);
    g.byDirection.set(dirKey, list);
    groups.set(key, g);
  }

  const entries = [];
  for (const g of groups.values()) {
    const sides = [...g.byDirection.entries()].map(([direction, obs]) => ({ direction: direction === '-' ? null : direction, ...computeSide(obs) }));
    const conflicting = sides.length > 1 && sides.every((s) => s.independent >= 1);

    // refutation rule: independent>=2 + strictly stronger evidence (lower L) beats
    // a single-observation weaker evidence side.
    if (conflicting) {
      const strong = [...sides].sort((a, b) => b.independent - a.independent);
      const strongest = strong[0];
      for (const s of strong.slice(1)) {
        if (strongest.independent >= 2 && s.independent === 1 && evidenceNum(strongest.evidence_level) < evidenceNum(s.evidence_level)) {
          s.status = 'refuted';
          s.reasons.push(`被 ${strongest.direction || 'n/a'} 方向 (独立 ${strongest.independent} 次, ${strongest.evidence_level}) 反证`);
        }
      }
    }

    const liveSides = sides.filter((s) => s.status !== 'refuted');
    const totalIndependent = liveSides.reduce((n, s) => n + s.independent, 0);
    let grade;
    if (!liveSides.length) grade = 'refuted';
    else if (conflicting && liveSides.length > 1) grade = 'competing';
    else if (totalIndependent >= minIndependent) grade = 'consensus';
    else if (totalIndependent === 2) grade = 'candidate';
    else grade = 'singleton';

    const override = overrides && overrides.entries ? overrides.entries[g.entry_key] : null;
    if (override && override.status === 'refuted') grade = 'refuted';

    const lastSeen = sides.reduce((best, s) => (s.last_seen && (!best || s.last_seen > best) ? s.last_seen : best), null);
    const stale = lastSeen ? (nowMs - Date.parse(lastSeen)) > staleDays * 864e5 : false;
    const mechanisms = findings.filter((f) => f.subject === g.subject && f.claim_type === g.claim_type && f.payload && f.payload.mechanism).map((f) => f.payload.mechanism);
    const mechanism = mechanisms.length ? mechanisms.sort((a, b) => mechanisms.filter((m) => m === b).length - mechanisms.filter((m) => m === a).length)[0] : null;

    entries.push({
      entry_key: g.entry_key,
      subject: g.subject,
      claim_type: g.claim_type,
      grade,
      stale,
      independent: totalIndependent,
      corroboration: sides.reduce((n, s) => n + s.n, 0),
      mechanism,
      directions: sides.map((s) => ({
        direction: s.direction,
        status: s.status,
        observations: s.n,
        independent: s.independent,
        last_seen: s.last_seen,
        severity: s.severity,
        evidence_level: s.evidence_level,
        confidence: s.confidence,
        reasons: s.reasons,
      })),
      confidence: sides.reduce((best, s) => Math.max(best || 0, s.confidence || 0), 0) || null,
      first_seen: sides.reduce((best, s) => {
        const first = s.observations.length ? s.observations[s.observations.length - 1].observed_at : null;
        return first && (!best || first < best) ? first : best;
      }, null),
      last_seen: lastSeen,
      sources: sides.flatMap((s) => s.observations.map((o) => ({
        run_id: o.run_id, observed_at: o.observed_at, direction: o.direction || null, detail: o.detail, line_key: o.line_key,
      }))).slice(0, 40),
      narrative: buildNarrative(g.subject, g.claim_type, grade, sides, lastSeen),
      override: override || null,
    });
  }

  entries.sort((a, b) => {
    const ga = GRADE_ORDER[a.grade] ?? 9;
    const gb = GRADE_ORDER[b.grade] ?? 9;
    if (ga !== gb) return ga - gb;
    if (b.independent !== a.independent) return b.independent - a.independent;
    return String(b.last_seen || '').localeCompare(String(a.last_seen || ''));
  });

  const states = findings.filter((f) => f.claim_type === 'line_state').sort((a, b) => String(b.observed_at).localeCompare(String(a.observed_at)));
  const latestState = states.length ? {
    run_id: states[0].run_id,
    observed_at: states[0].observed_at,
    detail: states[0].detail,
    ...(states[0].payload || {}),
  } : null;

  const stats = {
    findings: findings.length,
    entries: entries.length,
    consensus: entries.filter((e) => e.grade === 'consensus').length,
    candidate: entries.filter((e) => e.grade === 'candidate').length,
    singleton: entries.filter((e) => e.grade === 'singleton').length,
    competing: entries.filter((e) => e.grade === 'competing').length,
    refuted: entries.filter((e) => e.grade === 'refuted').length,
    stale: entries.filter((e) => e.stale).length,
  };

  const consensus = {
    contract_version: CONTRACT_VERSION,
    generated_at: nowIso,
    line_key: slugify(lineKey),
    stats,
    latest_state: latestState,
    entries,
  };
  writeConsensus(storeDir, lineKey, consensus);
  return consensus;
}

function buildNarrative(subject, claimType, grade, sides, lastSeen) {
  const dirs = sides.map((s) => `${s.direction || '无方向'}(${s.independent} 次独立)`).join(' / ');
  const when = lastSeen ? `最近观测 ${String(lastSeen).slice(0, 10)}` : '无时间信息';
  return `${subject} 的 ${claimType}:${grade === 'consensus' ? '多次独立观测一致' : grade === 'competing' ? '存在方向竞争' : grade === 'refuted' ? '已被更强证据反证' : grade === 'candidate' ? '两次观测一致(候选)' : '单次观测(线索)'};方向:${dirs};${when}。`;
}

// ── Retrieval (consensus-first) ──────────────────────────────────────────

export function buildMemoryBrief(consensus, opts = {}) {
  const maxTokens = Number.isFinite(Number(opts.maxTokens)) ? Number(opts.maxTokens) : 600;
  const topConsensus = Number.isFinite(Number(opts.topConsensus)) ? Number(opts.topConsensus) : 8;
  const topCandidates = Number.isFinite(Number(opts.topCandidates)) ? Number(opts.topCandidates) : 4;
  const topSingletons = Number.isFinite(Number(opts.topSingletons)) ? Number(opts.topSingletons) : 4;
  if (!consensus || !Array.isArray(consensus.entries) || !consensus.entries.length) {
    return { text: '', payload: null };
  }
  const lineKey = consensus.line_key;
  const pick = (grade) => consensus.entries.filter((e) => e.grade === grade && !e.stale);
  const warnings = consensus.entries.filter((e) => (e.grade === 'competing' || e.grade === 'refuted' || e.stale) );
  const lines = [];
  const addLine = (tag, e) => {
    const dirs = e.directions.map((d) => `${d.direction || '—'}(${d.independent})`).join('/');
    const src = [...new Set(e.sources.map((s) => s.run_id))].slice(0, 4).join(',');
    lines.push(`[${tag}] ${e.subject} · ${e.claim_type} · 方向:${dirs} · 置信:${e.confidence ?? 'n/a'} · 来源:${src || 'n/a'}${e.mechanism ? ' · 机理:' + String(e.mechanism).slice(0, 60) : ''}`);
  };
  for (const e of pick('consensus').slice(0, topConsensus)) addLine(`共性·${e.independent}`, e);
  for (const e of pick('candidate').slice(0, topCandidates)) addLine('候选', e);
  for (const e of pick('singleton').slice(0, topSingletons)) addLine('线索', e);
  for (const e of warnings.slice(0, 4)) {
    const status = e.stale ? '陈旧' : e.grade === 'refuted' ? '已反证' : '竞争';
    const dirs = e.directions.map((d) => `${d.direction || '—'}(${d.independent}${d.status === 'refuted' ? ',反证' : ''})`).join('/');
    lines.push(`[警示·${status}] ${e.subject} · ${e.claim_type} · 方向:${dirs}${e.override && e.override.status === 'refuted' ? ' · 人工反证:' + String(e.override.reason || '').slice(0, 40) : ''}`);
  }
  if (!lines.length) return { text: '', payload: null };

  const header = [
    `## 产线记忆(跨 run 共识,先验级别 L5,仅供参考)`,
    `线:${lineKey} · 共性 ${consensus.stats.consensus} 条 / 候选 ${consensus.stats.candidate} 条 / 未成熟线索 ${consensus.stats.singleton} 条`,
    `纪律:以上为历史先验,必须用本次数据重新验证;先验与本次数据冲突时以本次数据为准,并在报告中标注"与历史记忆不一致";禁止直接复制旧结论。`,
  ].join('\n');

  let text = header + '\n' + lines.join('\n');
  const maxChars = Math.max(400, maxTokens * 2);
  if (text.length > maxChars) text = text.slice(0, maxChars - 20) + '\n…(记忆条目已截断)';

  return {
    text,
    payload: {
      line_key: lineKey,
      generated_at: consensus.generated_at,
      stats: consensus.stats,
      entries: consensus.entries
        .filter((e) => e.grade === 'consensus' || e.grade === 'candidate' || e.grade === 'singleton' || e.grade === 'competing' || e.grade === 'refuted' || e.stale)
        .slice(0, 24),
      latest_state: consensus.latest_state,
    },
  };
}

/**
 * 新 run 启动时的记忆检索入口：按别名找线 → 生成 brief。
 */
export function retrieveForRun({ storeDir = defaultStoreDir(), sceneKey = null, sceneName = null, lineId = null, maxTokens = 600 } = {}) {
  const candidates = [lineId, sceneKey, sceneName].filter(Boolean);
  let hit = null;
  for (const c of candidates) {
    hit = findLineByAlias(storeDir, c);
    if (hit) break;
  }
  if (!hit) return { lineKey: null, text: '', payload: null, hit: false };
  const consensus = readConsensus(storeDir, hit.lineKey);
  if (!consensus) return { lineKey: hit.lineKey, text: '', payload: null, hit: false };
  const brief = buildMemoryBrief(consensus, { maxTokens });
  return { lineKey: hit.lineKey, ...brief, hit: true };
}

// ── Ontology proposals (tiered) ──────────────────────────────────────────

export const ADDITIVE_OPS = ['add_missing_parameter', 'add_physical_meaning', 'add_class', 'add_note', 'add_group_member'];
export const CORRECTION_OPS = ['correct_unit', 'correct_group', 'correct_stage', 'reclassify'];
export const REMOVAL_OPS = ['deprecate', 'remove'];

export function proposalTier(op) {
  if (ADDITIVE_OPS.includes(op)) return 'additive';
  if (CORRECTION_OPS.includes(op)) return 'correction';
  if (REMOVAL_OPS.includes(op)) return 'removal';
  return 'invalid';
}

function proposalId(runId, p) {
  return 'OP-' + String(runId).replace(/[^a-zA-Z0-9]/g, '').toLowerCase().slice(0, 12) + '-' +
    sha256([runId, p.op, p.target, p.field || '-', JSON.stringify(p.to ?? null)].join('|')).slice(7, 15);
}

function changeFingerprint(sceneKey, p) {
  return sha256([sceneKey, p.op, p.target, p.field || '-', JSON.stringify(p.to ?? null)].join('|')).slice(7, 23);
}

/**
 * 读取 run 的提案文件（05_review/ontology_proposals.json 优先，其次 04_diagnostics）。
 */
export function readProposalsForRun(runDir) {
  for (const p of ['05_review/ontology_proposals.json', '04_diagnostics/ontology_proposals.json']) {
    const j = readJson(join(runDir, p));
    if (j) return { path: p, proposal: j };
  }
  return null;
}

/**
 * 确定性校验：参数存在性（若给出 dataColumns）、单位/内容长度、数量上限。
 * @returns {{ok:boolean, errors:string[], warnings:string[]}}
 */
export function validateProposal(proposal, { dataColumns = null } = {}) {
  const errors = [];
  const warnings = [];
  if (!proposal || typeof proposal !== 'object') return { ok: false, errors: ['proposal 不是对象'], warnings };
  if (proposal.contract_version !== PROPOSAL_CONTRACT) errors.push(`contract_version 必须为 ${PROPOSAL_CONTRACT}`);
  if (!proposal.scene_key || !/^[A-Za-z0-9._-]+$/.test(String(proposal.scene_key))) errors.push('scene_key 非法(仅允许 A-Za-z0-9._-)');
  const list = proposal.proposals;
  if (!Array.isArray(list) || !list.length) errors.push('proposals 为空');
  if (Array.isArray(list) && list.length > 10) errors.push(`proposals 超过上限 10 条(实际 ${list.length})`);
  const cols = Array.isArray(dataColumns) ? new Set(dataColumns) : null;
  for (const p of Array.isArray(list) ? list : []) {
    if (!p || typeof p !== 'object') { errors.push('提案条目不是对象'); continue; }
    if (!p.id || !p.op || !p.target || !p.rationale) errors.push(`提案 ${p.id || '?'} 缺少 id/op/target/rationale`);
    if (proposalTier(p.op) === 'invalid') errors.push(`提案 ${p.id || '?'} 的 op 非法: ${p.op}`);
    if (cols && !cols.has(String(p.target)) && !['add_note', 'add_class', 'add_group_member'].includes(p.op)) {
      errors.push(`提案 ${p.id || '?'} 的目标 "${p.target}" 不在本次数据列中`);
    }
    if (p.op === 'correct_unit') {
      const unit = p.to && typeof p.to === 'object' ? p.to.unit ?? p.to.value : p.to;
      if (!unit || typeof unit !== 'string' || unit.length > 40) errors.push(`提案 ${p.id || '?'} 的单位值非法`);
    }
    if (p.op === 'add_missing_parameter') {
      const to = p.to && typeof p.to === 'object' ? p.to : {};
      if (to.unit && (typeof to.unit !== 'string' || to.unit.length > 40)) errors.push(`提案 ${p.id || '?'} 的单位值非法`);
      if (to.role && !['parameter', 'setpoint', 'measured', 'inspection', 'group', 'time', 'unmapped'].includes(to.role)) warnings.push(`提案 ${p.id || '?'} role 非常规: ${to.role}`);
    }
    if (p.field && String(p.field).length > 60) errors.push(`提案 ${p.id || '?'} 的 field 过长`);
    if (String(p.rationale).length > 400) errors.push(`提案 ${p.id || '?'} 的 rationale 超过 400 字`);
  }
  return { ok: errors.length === 0, errors, warnings };
}

export function readProposalLog(storeDir = defaultStoreDir()) {
  return readJsonl(join(storeDir, 'proposals.jsonl'));
}

function writeProposalLog(storeDir, records) {
  atomicWrite(join(storeDir, 'proposals.jsonl'), records.map((r) => JSON.stringify(r)).join('\n') + (records.length ? '\n' : ''));
}

/**
 * 提案入库与分级裁决。
 *  - additive(校验通过) → 立即应用（调用方提供 applyFn）
 *  - correction → 攒独立佐证：同一 change_fp 在 >=2 个不同 run 出现才应用，否则 pending_corroboration
 *  - removal → 一律 pending_approval
 * @param {object} opts {storeDir, runDir, runId, lineKey, dataColumns, now, applyFn(record, change) => {ok, version?, error?}}
 */
export function ingestProposals({ storeDir = defaultStoreDir(), runDir, runId, lineKey = null, dataColumns = null, now = null, applyFn = null }) {
  ensureStore(storeDir);
  const found = readProposalsForRun(runDir);
  if (!found) return { found: false, records: [] };
  const validation = validateProposal(found.proposal, { dataColumns });
  const log = readProposalLog(storeDir);
  const existingIds = new Set(log.map((r) => r.proposal_id));
  const created = [];
  const createdAt = now || new Date().toISOString();

  for (const p of Array.isArray(found.proposal.proposals) ? found.proposal.proposals : []) {
    const id = proposalId(runId, p);
    if (existingIds.has(id)) continue; // 幂等
    const tier = proposalTier(p.op);
    const fp = changeFingerprint(found.proposal.scene_key, p);
    const corroboratingRuns = new Set(
      log.filter((r) => r.change_fp === fp && r.scene_key === found.proposal.scene_key && r.status !== 'rejected' && r.status !== 'invalid').map((r) => r.run_id)
    );
    corroboratingRuns.add(runId);

    let status;
    if (!validation.ok) status = 'invalid';
    else if (tier === 'additive') status = 'applied';
    else if (tier === 'correction') status = corroboratingRuns.size >= 2 ? 'applied' : 'pending_corroboration';
    else status = 'pending_approval';

    const record = {
      proposal_id: id,
      contract_version: PROPOSAL_CONTRACT,
      run_id: runId,
      line_key: lineKey,
      scene_key: found.proposal.scene_key,
      tier,
      op: p.op,
      target: p.target,
      field: p.field ?? null,
      from: p.from ?? null,
      to: p.to ?? null,
      rationale: String(p.rationale || '').slice(0, 400),
      confidence: Number.isFinite(Number(p.confidence)) ? Number(p.confidence) : null,
      evidence_level: p.evidence_level || 'L4',
      change_fp: fp,
      status,
      corroborating_runs: [...corroboratingRuns],
      validation: { ok: validation.ok, errors: validation.errors, warnings: validation.warnings },
      applied: null,
      created_at: createdAt,
      decided_at: null,
      decided_by: null,
      source_path: found.path,
    };

    if (status === 'applied' && applyFn) {
      try {
        const applied = applyFn(record, p);
        if (applied && applied.ok) record.applied = { scene_key: applied.scene_key || found.proposal.scene_key, version: applied.version ?? null, at: createdAt };
        else { record.status = 'apply_failed'; record.applied = { error: applied && applied.error ? String(applied.error) : 'unknown' }; }
      } catch (err) {
        record.status = 'apply_failed';
        record.applied = { error: String(err.message || err) };
      }
    }
    log.push(record);
    created.push(record);
  }

  if (created.length) writeProposalLog(storeDir, log);
  return { found: true, validation, records: created };
}

/** 人工批准 / 拒绝（removal 与 pending_corroboration 均可用）。 */
export function decideProposal({ storeDir = defaultStoreDir(), proposalId: id, action, actor = 'human', now = null, applyFn = null }) {
  const log = readProposalLog(storeDir);
  const record = log.find((r) => r.proposal_id === id);
  if (!record) throw new Error(`proposal not found: ${id}`);
  if (action === 'approve') {
    if (applyFn) {
      const applied = applyFn(record);
      if (!applied || !applied.ok) throw new Error('apply failed: ' + ((applied && applied.error) || 'unknown'));
      record.applied = { scene_key: applied.scene_key || record.scene_key, version: applied.version ?? null, at: now || new Date().toISOString() };
    }
    record.status = 'applied';
  } else if (action === 'reject') {
    record.status = 'rejected';
  } else {
    throw new Error(`unknown action: ${action}`);
  }
  record.decided_at = now || new Date().toISOString();
  record.decided_by = actor;
  writeProposalLog(storeDir, log);
  return record;
}

// ── Line merge (alias bridging) ──────────────────────────────────────────

/**
 * 把 fromKey 的 findings 合并进 intoKey（去重），注册别名并重算双方共识。
 */
export function mergeLines({ storeDir = defaultStoreDir(), fromKey, intoKey, now = null }) {
  const from = slugify(fromKey);
  const into = slugify(intoKey);
  if (!from || !into) throw new Error('fromKey/intoKey 必填');
  if (from === into) throw new Error('不能合并到自身');
  const reg = readRegistry(storeDir);
  if (!reg.lines[from]) throw new Error(`源产线不存在: ${from}`);
  if (!reg.lines[into]) throw new Error(`目标产线不存在: ${into}`);
  const findings = readFindings(storeDir, from).map((f) => ({ ...f, line_key: into }));
  const { added, skipped } = appendFindings(storeDir, into, findings);
  // 别名迁移
  reg.lines[into].aliases = [...new Set([...(reg.lines[into].aliases || []), from, ...(reg.lines[from].aliases || [])])].sort();
  reg.lines[into].updated_at = now || new Date().toISOString();
  delete reg.lines[from];
  writeRegistry(storeDir, reg);
  // 源目录归档（保留审计，不参与检索）
  try { writeJson(join(lineDir(storeDir, from), 'merged_into.json'), { into, merged_at: now || new Date().toISOString() }); } catch { /* ignore */ }
  const consensus = consolidate(storeDir, into, { now });
  return { into, added, skipped, consensus };
}

/** 人工反证 / 撤销反证（写入 overrides.json，最高优先级）。 */
export function overrideEntry({ storeDir = defaultStoreDir(), lineKey, entryKey, status, reason = '', actor = 'human', now = null }) {
  const overrides = readOverrides(storeDir, lineKey);
  if (status === 'refuted') {
    overrides.entries[entryKey] = { status: 'refuted', reason: String(reason).slice(0, 300), actor, at: now || new Date().toISOString() };
  } else {
    delete overrides.entries[entryKey];
  }
  writeOverrides(storeDir, lineKey, overrides);
  return consolidate(storeDir, lineKey, { now });
}

// ── CLI（回填 / 调试 / 运维） ─────────────────────────────────────────────

function cliMain(argv) {
  const [cmd, ...rest] = argv;
  const arg = (name, def = null) => {
    const i = rest.indexOf('--' + name);
    return i >= 0 ? rest[i + 1] : def;
  };
  const storeDir = resolve(arg('store-dir', defaultStoreDir()));
  ensureStore(storeDir);

  if (cmd === 'ingest') {
    const runDir = resolve(arg('run-dir'));
    const runId = arg('run-id') || basename(runDir);
    const intent = arg('intent', 'stability-report');
    const sceneKey = arg('scene', null);
    const observedAt = arg('observed-at', null);
    const r = ingestRun({ storeDir, runDir, runId, intent, sceneKey, observedAt });
    console.log(JSON.stringify({ line_key: r.lineKey, added: r.findings_added, skipped: r.skipped, stats: r.consensus && r.consensus.stats }, null, 2));
    return;
  }
  if (cmd === 'consolidate') {
    const lineKey = arg('line');
    const r = consolidate(storeDir, lineKey, { now: arg('now', null) });
    console.log(JSON.stringify(r.stats, null, 2));
    return;
  }
  if (cmd === 'retrieve') {
    const r = retrieveForRun({ storeDir, sceneKey: arg('scene'), sceneName: arg('name'), lineId: arg('line') });
    console.log(r.text || '(empty)');
    return;
  }
  if (cmd === 'list') {
    const reg = readRegistry(storeDir);
    for (const [key, entry] of Object.entries(reg.lines)) {
      const c = readConsensus(storeDir, key);
      console.log(key, '|', entry.name, '| stats:', c ? JSON.stringify(c.stats) : 'n/a');
    }
    return;
  }
  console.error('usage: node line_memory.mjs <ingest|consolidate|retrieve|list> [--run-dir ...] [--run-id ...] [--intent ...] [--line ...] [--scene ...] [--store-dir ...]');
  process.exitCode = 2;
}

const invokedDirectly = process.argv[1] && resolve(process.argv[1]) === resolve(fileURLToPath(import.meta.url));
if (invokedDirectly) cliMain(process.argv.slice(2));
