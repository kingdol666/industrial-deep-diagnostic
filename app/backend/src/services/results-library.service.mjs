// Results Library — flat, structured management of COMPLETED analysis results.
//
// One row per completed run (result_id = run_id). Derived fields (summary /
// summary_json / metadata / score / verdict) are written by a single choke
// point — the completion hook in diagnosis.service — and refreshed by the
// idempotent startup backfill. User fields (description / tags) are only ever
// touched by PATCH. title / category / soft-delete are NOT stored here: every
// read JOINs diagnostic_runs so the run row stays the single source of truth.
//
// Two-level Agent API (plan 2026-10-25 §8):
//   GET /results            → flat summary cards (display_text = description || summary)
//   GET /results/:resultId  → full detail (summary_json + metadata + report_md + files)
// A row missing at read time is derived on the fly (`derived: true`) so the
// detail endpoint never 404s on a legitimately completed run.
import { existsSync, readFileSync, readdirSync, statSync } from 'fs';
import { isAbsolute, join, relative, resolve, basename } from 'path';

import { stmts } from '../db/database.mjs';
import { resolveRunDir, buildArtifactManifest } from './artifact-manifest.service.mjs';
import { enrichRunOutcome } from './intent-outcome.service.mjs';
import { engineSupportsSessionChat } from './session-integrity.service.mjs';
import { renameRun, setRunCategory } from './history.service.mjs';
import { PROJECT_ROOT } from '../../../../config/loader.mjs';
import logger from '../utils/logger.mjs';

export const RESULT_INTENTS = [
  'deep-diagnosis', 'stability-report', 'quick-screen',
  'doe-analysis', 'experience-mining', 'optimizer-campaign',
];
const SORTS = new Set(['created_desc', 'created_asc', 'score_desc']);
const LIST_DEFAULT_LIMIT = 50;
const LIST_MAX_LIMIT = 200;
const DESCRIPTION_MAX = 2000;
const TAGS_MAX = 16;
const TAG_MAX = 40;
const BRIEF_TEXT_MAX = 160;
const CONCLUSION_SECTION_MAX = 600;

function httpError(status, code, message) {
  const err = new Error(message);
  err.status = status;
  err.code = code;
  return err;
}

function readJson(absPath) {
  try {
    if (!absPath || !existsSync(absPath)) return null;
    return JSON.parse(readFileSync(absPath, 'utf-8'));
  } catch {
    return null;
  }
}

function asNumber(value) {
  if (value === null || value === undefined || value === '') return null;
  const n = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(n) ? n : null;
}

function trunc(s, n) {
  const str = String(s ?? '').trim();
  return str.length > n ? `${str.slice(0, n)}…` : str;
}

function parseSqliteMs(s) {
  if (!s) return null;
  const ms = Date.parse(`${String(s).replace(' ', 'T')}Z`);
  return Number.isFinite(ms) ? ms : null;
}

// ── Deterministic summary extraction (zero LLM, per intent) ─────────────────

const EMPTY_SUMMARY = { conclusion: '', key_numbers: {}, data_profile: null, artifacts: [], sources: {} };

function profileSentence(profile) {
  if (!profile) return '';
  const bits = [];
  if (profile.rows !== null && profile.rows !== undefined) {
    bits.push(`数据 ${profile.rows} 行`);
  }
  if (Array.isArray(profile.parameter_cols) && profile.parameter_cols.length) {
    bits.push(`${profile.parameter_cols.length} 参数入评`);
  }
  if (profile.time_range && profile.time_range[0]) {
    bits.push(`时段 ${profile.time_range[0]} ~ ${profile.time_range[1] ?? ''}`.trim());
  }
  return bits.length ? `${bits.join('，')}。` : '';
}

function summarizeStability(dir) {
  const rel = 'line_report/stability_report.json';
  const doc = readJson(join(dir, rel));
  const c = doc?.conclusion;
  if (!c || typeof c !== 'object') return null;
  const d = doc.data || {};
  const p = doc.period || {};
  const topConcern = /最需关注[：:]\s*([^。；;\s]+)/.exec(String(c.statement || ''))?.[1] ?? null;
  const keyNumbers = {
    score: asNumber(c.score),
    grade: c.grade ?? null,
    label: c.label ?? null,
    n_parameters_assessed: asNumber(c.n_parameters_assessed),
    n_findings: asNumber(c.n_findings),
    findings_by_severity: c.findings_by_severity ?? null,
    top_concern: topConcern,
  };
  const dataProfile = {
    rows: asNumber(d.n_rows_used),
    parameter_cols: Array.isArray(d.parameter_cols) ? d.parameter_cols : [],
    time_range: p.start ? [p.start, p.end ?? null] : null,
    sampling_interval_seconds: asNumber(d.sampling_interval_median_seconds),
    missing_rate: asNumber(d.missing_rate),
    sampled: d.sampled === true,
    sha256: d.sha256 ?? null,
  };
  const conclusion = trunc(c.statement, 300) || `稳定性评估 ${keyNumbers.score} 分（${keyNumbers.grade ?? '—'} 级 · ${keyNumbers.label ?? ''}`.trim();
  return {
    conclusion,
    key_numbers: keyNumbers,
    data_profile: dataProfile,
    artifacts: [rel, 'line_report/line_stability_report.html', 'report.md'].filter((r) => existsSync(join(dir, r))),
    sources: {
      score: `${rel}#conclusion.score`,
      statement: `${rel}#conclusion.statement`,
      rows: `${rel}#data.n_rows_used`,
      time_range: `${rel}#period`,
    },
  };
}

function summarizeQuickScreen(dir) {
  const rel = 'sentinel/alert.json';
  const doc = readJson(join(dir, rel));
  if (!doc || typeof doc !== 'object') return null;
  const alerts = Array.isArray(doc.alerts) ? doc.alerts.length : null;
  const cs = doc.checks_summary || {};
  const src = doc.source || {};
  const entries = Object.entries(cs.events_by_parameter || {});
  const topParam = entries.length
    ? entries.sort((a, b) => (b[1]?.alerts || 0) - (a[1]?.alerts || 0))[0][0].split('|').pop()
    : null;
  const keyNumbers = {
    status: doc.status ?? null,
    n_alerts: alerts,
    spc_n_triggered: asNumber(cs.spc?.n_triggered),
    multivariate_n_outliers: asNumber(cs.multivariate?.n_outliers),
    event_count: asNumber(cs.event_count),
    top_parameter: topParam,
  };
  const dataProfile = {
    rows: asNumber(src.n_rows),
    parameter_cols: null,
    time_range: src.window_start ? [src.window_start, src.window_end ?? null] : null,
    sha256: src.sha256 ? (String(src.sha256).startsWith('sha256:') ? src.sha256 : `sha256:${src.sha256}`) : null,
  };
  const parts = [`快筛状态 ${doc.status ?? '未知'}`];
  if (alerts !== null) parts.push(`${alerts} 条告警`);
  if (keyNumbers.spc_n_triggered !== null) parts.push(`SPC 判异 ${keyNumbers.spc_n_triggered}`);
  if (keyNumbers.multivariate_n_outliers !== null) parts.push(`多变量离群 ${keyNumbers.multivariate_n_outliers}`);
  if (topParam) parts.push(`告警最多参数 ${topParam}`);
  return {
    conclusion: `${parts.join('，')}。`,
    key_numbers: keyNumbers,
    data_profile: dataProfile,
    artifacts: [rel, 'sentinel/quick_screen_report.html', 'sentinel/watch_report.md'].filter((r) => existsSync(join(dir, r))),
    sources: {
      status: `${rel}#status`,
      n_alerts: `${rel}#alerts`,
      spc_n_triggered: `${rel}#checks_summary.spc.n_triggered`,
      rows: `${rel}#source.n_rows`,
    },
  };
}

function summarizeDoe(dir) {
  const rel = 'conclusions/doe_conclusion.json';
  const doc = readJson(join(dir, rel));
  if (!doc || typeof doc !== 'object') return null;
  const kf = Array.isArray(doc.key_findings) ? doc.key_findings[0] : null;
  const keyNumbers = {
    evidence_grade: doc.evidence_grade ?? null,
    design_type: doc.design_type ?? null,
    analysis_mode: doc.analysis_mode ?? null,
    n_key_findings: Array.isArray(doc.key_findings) ? doc.key_findings.length : 0,
    top_finding_id: kf?.id ?? null,
    top_finding_confidence: kf?.confidence ?? null,
  };
  const dp = readJson(join(dir, '01_profile/data_profile.json'));
  const dataProfile = dp ? {
    rows: asNumber(dp.n_rows ?? dp.n_rows_used ?? dp.n_runs),
    parameter_cols: Array.isArray(dp.factors) ? dp.factors : null,
    time_range: null,
    sha256: dp.sha256 ? String(dp.sha256).replace(/^sha256:?/, 'sha256:') : null,
  } : null;
  const modeLabel = doc.analysis_mode === 'designed' ? '设计试验数据' : (doc.analysis_mode === 'observational' ? '观测数据' : null);
  const bits = [`DOE 分析${modeLabel ? `（${modeLabel}）` : ''}`];
  if (doc.design_type) bits.push(`设计 ${doc.design_type}`);
  if (doc.evidence_grade) bits.push(`证据等级 ${doc.evidence_grade}`);
  if (keyNumbers.n_key_findings) bits.push(`${keyNumbers.n_key_findings} 项关键发现`);
  const conclusion = `${bits.join('，')}。${kf ? `首要发现：${trunc(kf.statement, 160)}` : ''}`;
  return {
    conclusion,
    key_numbers: keyNumbers,
    data_profile: dataProfile,
    artifacts: [rel, 'conclusions/recommendations.json', 'conclusions/next_design.json', 'report.html', 'report.md']
      .filter((r) => existsSync(join(dir, r))),
    sources: {
      evidence_grade: `${rel}#evidence_grade`,
      design_type: `${rel}#design_type`,
      top_finding: `${rel}#key_findings[0].statement`,
    },
  };
}

function summarizeExperience(dir) {
  const rel = 'conclusions/recommendation.json';
  const doc = readJson(join(dir, rel));
  if (!doc || typeof doc !== 'object') return null;
  const sig = doc.source?.fault_signature || {};
  const regime = sig.regime || {};
  const nPlaybooks = Array.isArray(doc.playbooks) ? doc.playbooks.length : null;
  const keyNumbers = {
    recommendation_status: doc.recommendation_status ?? null,
    match_scope: doc.match_scope ?? null,
    n_playbooks: nPlaybooks,
    product: regime.product ?? null,
    machine: regime.machine ?? null,
    regime_label: regime.regime_label ?? null,
    degraded_metric: sig.degraded_metric ?? null,
    top_anomalous_param: sig.anomalous_params?.[0]?.parameter ?? null,
  };
  const bits = [`经验推荐 ${doc.recommendation_status ?? '未知'}`];
  if (nPlaybooks !== null) bits.push(`命中 ${nPlaybooks} 个 playbook`);
  if (regime.product || regime.machine) bits.push(`工况 ${[regime.product, regime.machine].filter(Boolean).join('/')}`);
  if (sig.degraded_metric) bits.push(`劣化指标 ${sig.degraded_metric}`);
  if (keyNumbers.top_anomalous_param) bits.push(`首要异常参数 ${keyNumbers.top_anomalous_param}`);
  return {
    conclusion: `${bits.join('，')}。`,
    key_numbers: keyNumbers,
    data_profile: null,
    artifacts: [rel, 'report.md'].filter((r) => existsSync(join(dir, r))),
    sources: {
      recommendation_status: `${rel}#recommendation_status`,
      n_playbooks: `${rel}#playbooks`,
      degraded_metric: `${rel}#source.fault_signature.degraded_metric`,
    },
  };
}

function summarizeOptimizer(dir) {
  const rel = '01_state/optimizer_state.json';
  const doc = readJson(join(dir, rel));
  if (!doc || typeof doc !== 'object') return null;
  const budget = doc.budget || {};
  const inc = doc.incumbent || {};
  const keyNumbers = {
    phase: doc.phase ?? null,
    round_count: asNumber(doc.round_count),
    trial_count: asNumber(doc.trial_count),
    max_rounds: asNumber(budget.max_rounds),
    max_trials: asNumber(budget.max_trials),
    in_target: inc.in_target ?? null,
    predicted_D: asNumber(inc.predicted_D),
    campaign_id: doc.campaign_id ?? null,
  };
  const targetLabel = inc.in_target === true ? '当前最优已入目标窗'
    : inc.in_target === false ? '当前最优未入目标窗' : '当前最优目标窗状态未知';
  const dText = keyNumbers.predicted_D !== null ? `（期望 D=${Number(keyNumbers.predicted_D.toFixed(4))}）` : '';
  const roundText = keyNumbers.round_count !== null
    ? `第 ${keyNumbers.round_count}${keyNumbers.max_rounds !== null ? `/${keyNumbers.max_rounds}` : ''} 轮` : '';
  const conclusion = `寻优战役 ${doc.phase ?? '未知'}${roundText ? `，${roundText}` : ''}`
    + `${keyNumbers.trial_count !== null ? `，累计 ${keyNumbers.trial_count} 次试验` : ''}：${targetLabel}${dText}。`;
  return {
    conclusion,
    key_numbers: keyNumbers,
    data_profile: null,
    artifacts: [rel, 'report.md'].filter((r) => existsSync(join(dir, r))),
    sources: {
      phase: `${rel}#phase`,
      round_count: `${rel}#round_count`,
      in_target: `${rel}#incumbent.in_target`,
    },
  };
}

// deep-diagnosis: the Judge-scored pipeline's conclusion lives in report.md.
// Reuses the same section extractor as the tasks view (结论/总结/… headings).
function summarizeDeepDiagnosis(dir, run) {
  const rel = 'report.md';
  const abs = join(dir, rel);
  if (!existsSync(abs)) return null;
  let section = '';
  try {
    const md = readFileSync(abs, 'utf8');
    const sectionRe = /^##?\s*(结论|总结|最终结论|conclusion|summary)[^\n]*\n?([\s\S]*?)(?=\n##?\s|\s*$)/im;
    const sec = md.match(sectionRe);
    section = (sec ? (sec[2] || sec[1]) : md).trim();
  } catch {
    return null;
  }
  const conclusion = trunc(section.replace(/\n+/g, ' '), 240);
  return {
    conclusion: conclusion || '诊断报告已生成（详见 report.md）。',
    key_numbers: { score: asNumber(run?.score), verdict: run?.judge_verdict ?? null },
    data_profile: null,
    artifacts: [rel].filter((r) => existsSync(join(dir, r))),
    sources: { conclusion: `${rel}#结论`, score: 'diagnostic_runs.score' },
  };
}

/**
 * Deterministic, zero-LLM summary of a completed run's OWN artifacts.
 * Returns `{ summary, summary_json }`; extraction failure degrades to an
 * empty summary (the caller still writes the row — AC-10).
 */
export function summarizeRun(runDir, run) {
  const dir = !runDir ? null : (isAbsolute(runDir) ? runDir : resolve(PROJECT_ROOT, runDir));
  const intent = run?.analysis_intent || 'deep-diagnosis';
  let pack = null;
  try {
    if (dir && existsSync(dir)) {
      if (intent === 'stability-report') pack = summarizeStability(dir);
      else if (intent === 'quick-screen') pack = summarizeQuickScreen(dir);
      else if (intent === 'doe-analysis') pack = summarizeDoe(dir);
      else if (intent === 'experience-mining') pack = summarizeExperience(dir);
      else if (intent === 'optimizer-campaign') pack = summarizeOptimizer(dir);
      else pack = summarizeDeepDiagnosis(dir, run);
      // Generic fallback: the intent artifact may be absent (mock engine runs
      // never execute the skill scripts) while the run still wrote report.md —
      // its conclusion section is the run's OWN summary, honest to cite.
      if (!pack) {
        const fallback = summarizeDeepDiagnosis(dir, run);
        if (fallback) {
          fallback.sources = Object.fromEntries(
            Object.entries(fallback.sources).map(([k, v]) => [k === 'conclusion' ? 'report_fallback' : k, v]),
          );
          pack = fallback;
        }
      }
    }
  } catch (err) {
    logger.warn(`Summary extraction failed for ${run?.run_id}: ${err.message}`, { context: 'Results' });
    pack = null;
  }
  if (!pack) {
    // No parseable artifact at all. Say exactly that — an honest statement is
    // better than a blank card, and it never invents a conclusion.
    pack = {
      conclusion: dir
        ? '该运行未产出可解析的分析工件，无自动摘要；请查看运行日志与 report.md（如有）。'
        : '该运行没有 workspace 记录（未产出分析工件），无自动摘要。',
      key_numbers: {},
      data_profile: null,
      artifacts: [],
      sources: { conclusion: dir ? 'run_dir#no-parseable-artifacts' : 'diagnostic_runs.workspace_path#null' },
    };
  }
  const summary = [pack.conclusion, profileSentence(pack.data_profile)].filter(Boolean).join(' ');
  return {
    summary,
    summary_json: {
      conclusion: pack.conclusion || '',
      key_numbers: pack.key_numbers || {},
      data_profile: pack.data_profile ?? null,
      artifacts: pack.artifacts || [],
      sources: pack.sources || {},
    },
  };
}

// ── Result metadata (report / artifacts / duration / fingerprint) ───────────

function listHtmlFiles(runDir) {
  const out = [];
  const walk = (dir, depth) => {
    let entries;
    try { entries = readdirSync(dir, { withFileTypes: true }); } catch { return; }
    for (const e of entries) {
      if (out.length >= 8) return;
      if (e.name.startsWith('.') || e.name === 'node_modules') continue;
      const abs = join(dir, e.name);
      if (e.isDirectory()) {
        if (depth < 2) walk(abs, depth + 1);
      } else if (e.isFile() && e.name.toLowerCase().endsWith('.html')) {
        try {
          out.push({ path: relative(runDir, abs).split('\\').join('/'), bytes: statSync(abs).size });
        } catch { /* unreadable entry is skipped */ }
      }
    }
  };
  walk(runDir, 0);
  return out;
}

function genericArtifacts(runDir) {
  const candidates = [
    'report.md', 'report.html',
    'conclusions/doe_conclusion.json', 'conclusions/recommendation.json',
    'conclusions/next_design.json', '01_state/optimizer_state.json',
    'sentinel/alert.json', 'line_report/stability_report.json',
  ];
  const out = [];
  for (const rel of candidates) {
    const abs = join(runDir, rel);
    if (existsSync(abs)) {
      try {
        out.push({ kind: rel.split('/').pop().replace(/\.[^.]+$/, ''), path: rel, bytes: statSync(abs).size });
      } catch { /* skip */ }
    }
  }
  return out.slice(0, 12);
}

export function buildResultMetadata(run, runDir, summaryJson) {
  const dir = runDir && existsSync(runDir) ? runDir : null;
  const metadata = {
    workspace_path: run.workspace_path ? String(run.workspace_path).split('\\').join('/') : null,
    report_md: null,
    html: [],
    artifacts: [],
    duration_ms: null,
    engine: run.harness ?? null,
    model: run.model ?? null,
    data_fingerprint: summaryJson?.data_profile?.sha256 ?? null,
    ontology_hit: run.ontology_hit ?? null,
  };
  if (!dir) return metadata;
  if (run.report_path) {
    const abs = isAbsolute(run.report_path) ? run.report_path : join(PROJECT_ROOT, run.report_path);
    if (existsSync(abs)) {
      try { metadata.report_md = { path: String(run.report_path).split('\\').join('/'), bytes: statSync(abs).size }; } catch { /* skip */ }
    }
  } else {
    const abs = join(dir, 'report.md');
    if (existsSync(abs)) {
      try {
        metadata.report_md = {
          path: relative(PROJECT_ROOT, abs).split('\\').join('/'),
          bytes: statSync(abs).size,
        };
      } catch { /* skip */ }
    }
  }
  metadata.html = listHtmlFiles(dir);
  const manifest = buildArtifactManifest(dir, { analysisIntent: run.analysis_intent });
  if (manifest.applicable && Array.isArray(manifest.artifacts) && manifest.artifacts.length) {
    metadata.artifacts = manifest.artifacts.map((a) => ({ kind: a.kind, path: a.path, bytes: a.bytes ?? null })).slice(0, 16);
  } else {
    metadata.artifacts = genericArtifacts(dir);
  }
  const startMs = parseSqliteMs(run.created_at);
  const endMs = parseSqliteMs(run.completed_at);
  if (startMs !== null && endMs !== null && endMs >= startMs) metadata.duration_ms = endMs - startMs;
  return metadata;
}

// ── Write path: completion hook + backfill ─────────────────────────────────

/**
 * UPSERT the results row for a completed run. Never throws (AC-10: a summary
 * failure must not disturb the run's terminal state); returns the row or null.
 */
export function upsertResultFromRun(runId) {
  const run = stmts.getRunById.get(runId);
  if (!run || run.status !== 'completed') return null;
  const runDir = resolveRunDir(PROJECT_ROOT, run.workspace_path);
  let pack = { summary: '', summary_json: { ...EMPTY_SUMMARY } };
  let metadata = null;
  try {
    pack = summarizeRun(runDir, run);
    metadata = buildResultMetadata(run, runDir, pack.summary_json);
  } catch (err) {
    logger.warn(`Result summary build failed for ${runId}: ${err.message}`, { context: 'Results' });
    metadata = buildResultMetadata(run, null, null);
  }
  const effective = enrichRunOutcome(run);
  stmts.upsertResult.run({
    resultId: runId,
    runId,
    summary: pack.summary || '',
    summaryJson: JSON.stringify(pack.summary_json),
    metadata: JSON.stringify(metadata),
    intent: run.analysis_intent || 'deep-diagnosis',
    sceneName: run.scene_name ?? null,
    harness: run.harness ?? null,
    score: effective.score ?? null,
    verdict: effective.judge_verdict ?? null,
    userId: run.user_id ?? null,
    createdAt: run.created_at ?? null,
  });
  return stmts.getResultByRunId.get(runId);
}

/**
 * Idempotent startup backfill: insert a results row for every completed,
 * non-deleted run that has none. Insert-only by default — existing rows
 * (including user description/tags) are never rewritten. One narrow refresh
 * is allowed: a row with an EMPTY summary and no user description is
 * re-derived, so rows backfilled before a summarizer improvement (e.g. the
 * report.md fallback) catch up without any risk to user data.
 */
export function backfillResults() {
  const completed = stmts.getAllRuns.all().filter((r) => r.status === 'completed' && !r.deleted_at);
  let inserted = 0;
  let refreshed = 0;
  let skipped = 0;
  let failed = 0;
  for (const run of completed) {
    const existing = stmts.getResultByRunId.get(run.run_id);
    if (existing) {
      const emptySummary = !existing.summary || existing.summary === '';
      if (!emptySummary || existing.description) { skipped += 1; continue; }
      try {
        const row = upsertResultFromRun(run.run_id);
        if (row && row.summary) refreshed += 1; else skipped += 1;
      } catch (err) {
        failed += 1;
        logger.warn(`Backfill refresh failed for ${run.run_id}: ${err.message}`, { context: 'Results' });
      }
      continue;
    }
    try {
      const row = upsertResultFromRun(run.run_id);
      if (row) inserted += 1; else skipped += 1;
    } catch (err) {
      failed += 1;
      logger.warn(`Backfill failed for ${run.run_id}: ${err.message}`, { context: 'Results' });
    }
  }
  logger.info(
    `Results backfill: ${inserted} inserted, ${refreshed} refreshed, ${skipped} already present, ${failed} failed`,
    { context: 'Results' },
  );
  return { inserted, refreshed, skipped, failed };
}

// ── Read path: cards, detail, derive ───────────────────────────────────────

function parseJsonField(value, fallback) {
  try { return value ? JSON.parse(value) : fallback; } catch { return fallback; }
}

function buildCard(row, { brief = false } = {}) {
  const summaryJson = parseJsonField(row.summary_json, EMPTY_SUMMARY);
  const metadata = parseJsonField(row.metadata, {});
  const description = row.description ?? null;
  const displaySource = description || row.summary || '';
  return {
    result_id: row.result_id,
    title: row.title || row.name || row.result_id,
    description,
    display_text: brief ? trunc(displaySource, BRIEF_TEXT_MAX) : displaySource,
    intent: row.intent,
    scene: row.scene_name ?? null,
    harness: row.harness ?? null,
    score: row.score ?? null,
    verdict: row.verdict ?? null,
    category_id: row.category_id ?? null,
    tags: parseJsonField(row.tags, []),
    ...(brief ? {} : { key_numbers: summaryJson.key_numbers || {} }),
    has_report: !!(row.report_path || metadata.report_md),
    has_html: Array.isArray(metadata.html) && metadata.html.length > 0,
    created_at: row.result_created_at ?? null,
    completed_at: row.completed_at ?? null,
  };
}

function normalizeListParams(params = {}) {
  const intent = params.intent && RESULT_INTENTS.includes(params.intent) ? params.intent : null;
  if (params.intent && !intent) {
    throw httpError(400, 'RESULTS_QUERY_INVALID', `unknown intent: ${params.intent} (expected one of ${RESULT_INTENTS.join(', ')})`);
  }
  const sort = params.sort ? String(params.sort) : 'created_desc';
  if (!SORTS.has(sort)) {
    throw httpError(400, 'RESULTS_QUERY_INVALID', `unknown sort: ${sort} (created_desc | created_asc | score_desc)`);
  }
  const minScore = params.min_score !== undefined && params.min_score !== null && params.min_score !== ''
    ? Number(params.min_score) : null;
  if (minScore !== null && !Number.isFinite(minScore)) {
    throw httpError(400, 'RESULTS_QUERY_INVALID', 'min_score must be a number');
  }
  const limitRaw = Number(params.limit);
  const limit = Number.isFinite(limitRaw) && limitRaw > 0 ? Math.min(LIST_MAX_LIMIT, Math.trunc(limitRaw)) : LIST_DEFAULT_LIMIT;
  const offsetRaw = Number(params.offset);
  const offset = Number.isFinite(offsetRaw) && offsetRaw > 0 ? Math.trunc(offsetRaw) : 0;
  const tag = params.tag ? String(params.tag).trim() : null;
  return {
    intent,
    sort,
    minScore,
    limit,
    offset,
    tag,
    tagPattern: tag ? `%${JSON.stringify(tag).slice(1, -1)}%` : null, // exact JSON element match
    categoryId: params.category_id ? String(params.category_id) : null,
    scene: params.scene ? String(params.scene) : null,
    harness: params.harness ? String(params.harness) : null,
    q: params.q ? `%${String(params.q).trim()}%` : null,
    brief: params.brief === true || params.brief === 'true' || params.brief === '1',
  };
}

export function listResults(user, params = {}) {
  const p = normalizeListParams(params);
  const isAdmin = user?.role === 'admin' || !user?.id;
  const userId = isAdmin ? null : String(user.id);
  const sqlParams = {
    userId,
    intent: p.intent,
    categoryId: p.categoryId,
    scene: p.scene,
    harness: p.harness,
    minScore: p.minScore,
    tagPattern: p.tagPattern,
    q: p.q,
    sort: p.sort,
    limit: p.limit,
    offset: p.offset,
  };
  const rows = stmts.listResultsFiltered.all(sqlParams);
  const total = stmts.countResultsFiltered.get(sqlParams).n;
  return { total, limit: p.limit, offset: p.offset, brief: p.brief, results: rows.map((r) => buildCard(r, { brief: p.brief })) };
}

function htmlFileEntries(run, metadata) {
  const runName = run.workspace_path ? basename(String(run.workspace_path).split('\\').join('/')) : null;
  return (Array.isArray(metadata.html) ? metadata.html : []).map((h) => ({
    path: h.path,
    abs_path: run.workspace_path ? join(String(run.workspace_path).split('\\').join('/'), h.path) : null,
    bytes: h.bytes ?? null,
    url: runName ? `/api/files/workspace/asset/${runName}/${h.path}` : null,
  }));
}

function readReportMd(run, runDir) {
  const candidates = [];
  if (run.report_path) candidates.push(isAbsolute(run.report_path) ? run.report_path : join(PROJECT_ROOT, run.report_path));
  if (runDir) candidates.push(join(runDir, 'report.md'));
  for (const abs of candidates) {
    try {
      if (existsSync(abs)) return readFileSync(abs, 'utf-8');
    } catch { /* try next */ }
  }
  return null;
}

/** Detail view for a row-backed result. */
function detailFromRow(row, run, { includeMd }) {
  const summaryJson = parseJsonField(row.summary_json, EMPTY_SUMMARY);
  const metadata = parseJsonField(row.metadata, {});
  const runDir = resolveRunDir(PROJECT_ROOT, run.workspace_path);
  const reportMd = includeMd ? readReportMd(run, runDir) : null;
  const runName = run.workspace_path ? basename(String(run.workspace_path).split('\\').join('/')) : null;
  return {
    result_id: row.result_id,
    title: run.title || run.name || row.result_id,
    description: row.description ?? null,
    summary: row.summary || summaryJson.conclusion || '',
    summary_json: summaryJson,
    metadata,
    intent: row.intent,
    scene: row.scene_name ?? null,
    harness: row.harness ?? null,
    score: row.score ?? null,
    verdict: row.verdict ?? null,
    category_id: run.category_id ?? null,
    tags: parseJsonField(row.tags, []),
    report_md: reportMd,
    report_md_url: runName ? `/api/files/workspace/report/${runName}` : null,
    files: { html: htmlFileEntries(run, metadata) },
    run: {
      run_id: run.run_id,
      status: run.status,
      session_resumable: engineSupportsSessionChat(run.harness),
    },
    derived: false,
    created_at: row.created_at ?? run.created_at ?? null,
    completed_at: run.completed_at ?? null,
  };
}

/** Read-time fallback (AC-6): a completed run without a row still answers. */
export function deriveResultForApi(run, { includeMd } = {}) {
  const runDir = resolveRunDir(PROJECT_ROOT, run.workspace_path);
  const pack = summarizeRun(runDir, run);
  const metadata = buildResultMetadata(run, runDir, pack.summary_json);
  const effective = enrichRunOutcome(run);
  const rowLike = {
    result_id: run.run_id,
    description: null,
    summary: pack.summary,
    summary_json: JSON.stringify(pack.summary_json),
    tags: '[]',
    metadata: JSON.stringify(metadata),
    intent: run.analysis_intent || 'deep-diagnosis',
    scene_name: run.scene_name ?? null,
    harness: run.harness ?? null,
    score: effective.score ?? null,
    verdict: effective.judge_verdict ?? null,
    created_at: run.created_at ?? null,
  };
  return { ...detailFromRow(rowLike, run, { includeMd }), derived: true };
}

export function getResultDetail(resultId, { user = null, includeMd = true } = {}) {
  const run = stmts.getRunById.get(resultId);
  if (!run || run.deleted_at) {
    throw httpError(404, 'RESULT_NOT_FOUND', `Result not found: ${resultId}`);
  }
  const row = stmts.getResultByRunId.get(resultId);
  if (row) return detailFromRow(row, run, { includeMd });
  if (run.status !== 'completed') {
    throw httpError(404, 'RESULT_NOT_FOUND', `Result ${resultId} is not a completed analysis (status: ${run.status})`);
  }
  return deriveResultForApi(run, { includeMd });
}

// ── PATCH: user-editable fields only ───────────────────────────────────────

export function updateResult(resultId, patch, user = null) {
  if (!patch || typeof patch !== 'object') {
    throw httpError(400, 'RESULT_PATCH_INVALID', 'body must be a JSON object');
  }
  if ('summary' in patch || 'summary_json' in patch) {
    throw httpError(400, 'SUMMARY_READONLY', 'summary is system-managed and cannot be edited (edit description instead)');
  }
  const known = ['description', 'tags', 'title', 'category_id'];
  if (!known.some((k) => k in patch)) {
    throw httpError(400, 'RESULT_PATCH_INVALID', `provide at least one of ${known.join(', ')}`);
  }

  // Lazily create the row so editing a not-yet-backfilled legacy run works.
  let row = stmts.getResultByRunId.get(resultId);
  const run = stmts.getRunById.get(resultId);
  if (!run || run.deleted_at) {
    throw httpError(404, 'RESULT_NOT_FOUND', `Result not found: ${resultId}`);
  }
  if (!row && run.status !== 'completed') {
    throw httpError(404, 'RESULT_NOT_FOUND', `Result ${resultId} is not a completed analysis (status: ${run.status})`);
  }
  if (!row) row = upsertResultFromRun(resultId);
  if (!row) throw httpError(500, 'RESULT_UPSERT_FAILED', 'failed to materialize the result row');

  if (row.user_id && user?.id && user.role !== 'admin' && String(row.user_id) !== String(user.id)) {
    throw httpError(403, 'RESULT_FORBIDDEN', 'This result belongs to another user');
  }

  let nextDescription = row.description ?? null;
  if ('description' in patch) {
    const d = patch.description;
    if (d !== null) {
      if (typeof d !== 'string') throw httpError(400, 'RESULT_PATCH_INVALID', 'description must be a string or null');
      const clean = d.trim();
      if (clean.length > DESCRIPTION_MAX) {
        throw httpError(400, 'RESULT_PATCH_INVALID', `description must be ≤ ${DESCRIPTION_MAX} characters`);
      }
      nextDescription = clean || null;
    } else {
      nextDescription = null;
    }
  }

  let nextTags = parseJsonField(row.tags, []);
  if ('tags' in patch) {
    const t = patch.tags;
    if (!Array.isArray(t)) throw httpError(400, 'RESULT_PATCH_INVALID', 'tags must be an array of strings');
    if (t.length > TAGS_MAX) throw httpError(400, 'RESULT_PATCH_INVALID', `tags must hold ≤ ${TAGS_MAX} items`);
    const seen = new Set();
    nextTags = [];
    for (const item of t) {
      if (typeof item !== 'string') throw httpError(400, 'RESULT_PATCH_INVALID', 'tags must be an array of strings');
      const clean = item.trim();
      if (!clean) continue;
      if (clean.length > TAG_MAX) throw httpError(400, 'RESULT_PATCH_INVALID', `each tag must be ≤ ${TAG_MAX} characters`);
      if (!seen.has(clean)) { seen.add(clean); nextTags.push(clean); }
    }
  }

  // title / category live on the run row (single source of truth) — delegate
  // to the history service, which re-validates ownership and limits.
  if ('title' in patch) renameRun(resultId, patch.title, user);
  if ('category_id' in patch) setRunCategory(resultId, patch.category_id ?? null, user);

  stmts.updateResultUserFields.run({ resultId, description: nextDescription, tags: JSON.stringify(nextTags) });
  return getResultDetail(resultId, { user, includeMd: false });
}
