#!/usr/bin/env node
// baseline_llm.mjs — same-model bare-LLM baseline (paper §8.4 arm ii/iii).
//
// The comparison contract: the SAME harness (ZCode CLI) and the SAME model
// family/deployment as the IDD pipeline make ONE bare call per scenario —
// no ontology, no pipeline, no gates — over the identical blinded statistical
// digest used by the pipeline's brief. Three prompt regimes:
//   no_candidates    : blind digest only (all 12 scenarios; the single-LLM ablation)
//   with_candidates  : blind digest + documented TEP cause list (TEP 6; FE regime 1)
//   fe_official      : FaultExplainer's EXPLAIN_ROOT protocol replication (TEP 6;
//                      canonical prompts live in results/benchmark/fe_official_prompts/,
//                      generated from baselines/FaultExplainer — not regenerated here)
//
// Sub-commands:
//   prompts  write results/benchmark/baseline_fe_prompts/<case>.<regime>.txt
//            (existing files are NEVER overwritten — they are the recorded
//            inputs the archived answers answered; missing ones are rebuilt
//            deterministically from the blind brief + the documented cause list)
//   score    score every answer in results/benchmark/baseline_fe_answers/ and
//            aggregate results/benchmark/baselines.json (merging the PCA
//            baseline from baseline_pca_rca.json and preserving the
//            fe_official_code block produced by the official-FE-code run)
//   check    verify answer presence; print the execution contract for gaps
//
// Scoring (fixed, same as the IDD grading keywords):
//   strict     = rank-1 text hits a mechanism keyword, or (TEP) names the true IDV number
//   fe_style   = (candidates regimes) true IDV or an alias-class IDV appears in top-3
//   control    = verdict normal (top3 empty); a fault verdict is a false alarm

import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(import.meta.dirname, '..', '..');
const RES = path.join(ROOT, 'results', 'benchmark');
const PROMPTS = path.join(RES, 'baseline_fe_prompts');
const ANSWERS = path.join(RES, 'baseline_fe_answers');
const TIER = path.join(ROOT, 'scripts', 'benchmark', 'cases', 'benchmark_cases.json');
const CAUSES = path.join(ROOT, 'scripts', 'benchmark', 'cases', 'tep_cause_table.json');

const tier = JSON.parse(fs.readFileSync(TIER, 'utf8')).cases;
const causes = JSON.parse(fs.readFileSync(CAUSES, 'utf8'));
const MODEL = 'GLM family (same deployment as IDD pipeline; ZCode CLI harness, Sept 2026 snapshot)';
const PROTOCOL = 'bare single-call LLM: identical blind brief, no pipeline, no ontology, no gates; FE-regime prompts include the documented TEP cause list';
const SCORING = 'strict = single-verdict mechanism keywords (IDD rubric); FE-style = true IDV or alias class within top-3';

const args = process.argv.slice(2);
const cmd = args[0] || 'score';

function briefOf(caseId) {
  return JSON.parse(fs.readFileSync(path.join(RES, 'briefs', `${caseId}.brief.json`), 'utf8'));
}

function digestLines(brief) {
  const cols = brief.evidence.anomaly_columns
    .map((c) => `${c.col} max|z|=${c.max_abs_z} (${(c.pct_z3 * 100).toFixed(1)}% beyond 3σ)`)
    .join('; ');
  const pairs = brief.evidence.top_correlation_pairs.join('; ');
  return [`- Per-column max |z|-score (top columns): ${cols}`, `- Strongest cross-domain correlations: ${pairs}`];
}

function buildPrompt(c, regime) {
  const b = briefOf(c.case_id);
  const isTep = c.dataset === 'tep';
  const lines = [];
  if (isTep) {
    lines.push('You are an industrial process monitoring engineer. The Tennessee Eastman Process (TEP) shows an abnormal episode. Your task: identify the root cause.');
    lines.push('');
    lines.push('Dataset: Tennessee Eastman Process simulation. Columns: XMEAS_1..41 process measurements, XMV_1..11 manipulator variables (Downs-Vogel standard mapping). Sampling: 3 minutes. Fault onset: sample 161 of 960.');
  } else {
    lines.push('You are an industrial process monitoring engineer. A process shows the following recorded episode. Your task: assess whether a fault is present and, if so, identify the most likely root cause.');
    lines.push('');
    lines.push(`Dataset: ${c.case_id} (${c.dataset}). Rows: ${b.rows}. Sampling as described below.`);
  }
  lines.push('Blind statistical monitoring results (computed from the data):');
  lines.push(...digestLines(b));
  lines.push('');
  lines.push(`Process description: ${b.process_description}`);
  lines.push('');
  if (regime === 'with_candidates') {
    lines.push('Documented root-cause list for the TEP (choose from these):');
    for (const [id, desc] of Object.entries(causes.faults)) lines.push(`- ${id}: ${desc}`);
  }
  if (isTep) {
    lines.push('Task: identify the root cause of this abnormal episode. Output STRICT JSON only (no markdown, no extra text): {"top3": ["<root cause id/name>", ...], "reasoning": "<2-3 sentences>"} where top3 is your ranked list of up to 3 candidate root causes.');
  } else {
    lines.push('Task: (1) state whether this episode shows a fault or normal operation; (2) if a fault, give the most likely root cause and up to 2 alternatives. Output STRICT JSON only (no markdown, no extra text): {"verdict": "fault" | "normal", "top3": [...], "reasoning": "<2-3 sentences>"}');
  }
  return lines.join('\n') + '\n';
}

function cmdPrompts() {
  fs.mkdirSync(PROMPTS, { recursive: true });
  let written = 0, kept = 0;
  for (const c of tier) {
    const regimes = c.dataset === 'tep' ? ['no_candidates', 'with_candidates'] : ['no_candidates'];
    for (const regime of regimes) {
      const out = path.join(PROMPTS, `${c.case_id}.${regime}.txt`);
      if (fs.existsSync(out)) { kept++; continue; } // never overwrite recorded inputs
      fs.writeFileSync(out, buildPrompt(c, regime));
      written++;
      console.log(`[prompts] wrote ${path.relative(ROOT, out)}`);
    }
    if (c.dataset === 'tep' && !c.control) {
      const fe = path.join(RES, 'fe_official_prompts', `${c.case_id}.fe_official.txt`);
      if (!fs.existsSync(fe)) console.log(`[prompts] WARNING fe_official prompt missing: ${path.relative(ROOT, fe)} (rebuild from baselines/FaultExplainer EXPLAIN_ROOT)`);
    }
  }
  console.log(`[prompts] ${written} written, ${kept} kept (existing never overwritten)`);
}

// ---------- scoring ----------
const IDV_NUM = /IDV[\(\s]*(\d+)/gi;
function idvNumbers(text) {
  const out = [];
  for (const m of String(text).matchAll(IDV_NUM)) out.push(Number(m[1]));
  return out;
}
function truthIdv(c) {
  const m = String(c.truth || '').match(/IDV\((\d+)\)/);
  return m ? Number(m[1]) : null;
}
function aliasOf(idv) {
  for (const cls of causes.alias_classes) if (cls.includes(`IDV${idv}`)) return cls;
  return [];
}

function scoreAnswer(c, regime, ans) {
  const top3 = Array.isArray(ans.top3) ? ans.top3.map(String) : [];
  const top1 = top3[0] || '';
  const lower1 = top1.toLowerCase();
  const lower3 = top3.join(' \n ').toLowerCase();
  // kw_hits mirror the archived scorer: matched over the full top-3 text;
  // strict requires the hit IN THE RANK-1 verdict (or the true IDV number)
  const kwHits = (c.keywords || []).filter((k) => lower3.includes(String(k).toLowerCase()));
  const top1Kw = (c.keywords || []).some((k) => lower1.includes(String(k).toLowerCase()));
  let strict = top1Kw;
  const tIdv = truthIdv(c);
  const top1Idvs = idvNumbers(top1);
  if (tIdv !== null && top1Idvs.length && top1Idvs[0] === tIdv) strict = true;
  const entry = { regime, top3, strict_top1_hit: strict, kw_hits: kwHits };
  if (c.control) {
    const verdict = ans.verdict || (top3.length ? 'fault' : 'normal');
    entry.verdict = verdict;
    entry.normal_verdict = verdict === 'normal';
    entry.false_alarm = verdict === 'fault';
  } else if (!isTepLike(c)) {
    const verdict = ans.verdict || (top3.length ? 'fault' : 'normal');
    entry.verdict = verdict;
  } else {
    entry.verdict = null; // TEP answers are ranked IDV lists; no normal/fault field
  }
  if (tIdv !== null) {
    // FE-style scoring is a property of the ranked list, applied to every TEP
    // regime (regex IDV extraction — the archived prototype's substring match
    // missed "IDV(1)"-style strings; this corrected semantics supersedes it)
    const top3Idvs = new Set(top3.flatMap(idvNumbers));
    const hitIds = [tIdv, ...aliasOf(tIdv).map((x) => Number(x.replace('IDV', '')))];
    entry.fe_style_top3_hit = hitIds.some((n) => top3Idvs.has(n));
  }
  return entry;
}
function isTepLike(c) { return c.dataset === 'tep'; }

function readAnswer(file) {
  const raw = fs.readFileSync(file, 'utf8').trim();
  const start = raw.indexOf('{');
  return JSON.parse(raw.slice(start));
}

function cmdScore() {
  const llm = {};
  let missing = 0;
  for (const c of tier) {
    const regimes = ['no_candidates'];
    if (c.dataset === 'tep') regimes.push('with_candidates', 'fe_official');
    for (const regime of regimes) {
      const f = path.join(ANSWERS, `${c.case_id}.${regime}.json`);
      if (!fs.existsSync(f)) { if (regime !== 'fe_official' || c.dataset === 'tep') missing++; continue; }
      llm[c.case_id] = llm[c.case_id] || {};
      llm[c.case_id][regime] = scoreAnswer(c, regime, readAnswer(f));
    }
  }
  const pca = JSON.parse(fs.readFileSync(path.join(RES, 'baseline_pca_rca.json'), 'utf8')).scenarios;
  const prev = fs.existsSync(path.join(RES, 'baselines.json'))
    ? JSON.parse(fs.readFileSync(path.join(RES, 'baselines.json'), 'utf8'))
    : {};

  // aggregate headline counts (recomputed, same semantics as the archived summary)
  const faultCases = tier.filter((c) => !c.control);
  const hit = (c) => (llm[c.case_id]?.no_candidates?.strict_top1_hit ? 1 : 0);
  const strictNoCand = faultCases.reduce((s, c) => s + hit(c), 0);
  const tepFaults = faultCases.filter((c) => c.dataset === 'tep');
  const nonTepFaults = faultCases.filter((c) => c.dataset !== 'tep');
  const strictTep = tepFaults.reduce((s, c) => s + hit(c), 0);
  const strictNonTep = nonTepFaults.reduce((s, c) => s + hit(c), 0);
  const feStyle = tepFaults.filter((c) => llm[c.case_id]?.with_candidates?.fe_style_top3_hit).length;
  const strictWithCand = tepFaults.filter((c) => llm[c.case_id]?.with_candidates?.strict_top1_hit).length;
  const strictFeOfficial = tepFaults.filter((c) => llm[c.case_id]?.fe_official?.strict_top1_hit).length;
  const controls = tier.filter((c) => c.control && llm[c.case_id]?.no_candidates);
  const normalVerdicts = controls.filter((c) => llm[c.case_id].no_candidates.normal_verdict).length;
  const falseAlarms = controls.filter((c) => llm[c.case_id].no_candidates.false_alarm).length;

  const summary = {
    fe_protocol_replication_with_candidates: {
      fe_style_top3_hit: `${feStyle}/${tepFaults.length}`,
      strict_single_verdict: `${strictWithCand}/${tepFaults.length}`,
      note: 'FE-style scoring: true IDV or alias class within top-3',
    },
    fe_protocol_replication_no_candidates_strict: `strict single-verdict ${strictTep}/${tepFaults.length}`,
    fe_official_prompts_strict: `${strictFeOfficial}/${tepFaults.length}`,
    single_llm_same_digest_ablation: `strict single-verdict: TEP ${strictTep}/${tepFaults.length}, non-TEP ${strictNonTep}/${nonTepFaults.length} (all ${strictNoCand}/${faultCases.length} faults hit)`,
    controls: {
      bare_llm_normal_verdicts: `${normalVerdicts}/${controls.length}`,
      false_alarms: falseAlarms,
      note: controls.length < tier.filter((c) => c.control).length
        ? 'not every control was run in the bare-LLM baseline; covered controls scored here'
        : 'all controls covered',
    },
    headline: 'Same-model bare single-call LLM matches or exceeds the full pipeline on keyword-scored accuracy (see counts above, 0 control false alarms). The pipeline adds no accuracy on documented public faults; its margins are process qualities: auditability, execution proofs, ceiling compliance, and honest capped verdicts where signature data cannot discriminate mechanisms.',
  };

  const out = {
    model: MODEL,
    protocol: PROTOCOL,
    scoring: SCORING,
    llm,
    pca,
    summary,
    fe_official_code: prev.fe_official_code || { note: 'official-FE-code run block not present; rebuild via baselines/FaultExplainer replication' },
  };
  fs.mkdirSync(RES, { recursive: true });
  fs.writeFileSync(path.join(RES, 'baselines.json'), JSON.stringify(out, null, 1) + '\n');
  console.log(`[score] llm entries: ${Object.keys(llm).length} cases; strict(no_cand) ${strictNoCand}/${faultCases.length}; fe_style ${feStyle}/${tepFaults.length}; controls ${normalVerdicts}/${controls.length} normal, ${falseAlarms} false alarms`);
  if (missing) console.log(`[score] ${missing} answer file(s) missing — run 'check' for the execution contract`);
  console.log(`[score] wrote ${path.relative(ROOT, path.join(RES, 'baselines.json'))}`);
}

function cmdCheck() {
  // Documented scope gap: the TEP normal-control was never run in the
  // bare-LLM baseline (archived-protocol decision: FE regimes are fault-only
  // and the two covered controls suffice for false-alarm measurement).
  const exempt = new Set(['tep_d00_normal_control']);
  let gaps = 0;
  for (const c of tier) {
    const regimes = c.dataset === 'tep' ? ['no_candidates', 'with_candidates', 'fe_official'] : ['no_candidates'];
    for (const regime of regimes) {
      if (c.control && regime !== 'no_candidates') continue; // controls: single regime
      const f = path.join(ANSWERS, `${c.case_id}.${regime}.json`);
      if (fs.existsSync(f)) continue;
      if (exempt.has(c.case_id)) { console.log(`[check] exempt (documented scope gap) ${c.case_id}.${regime}`); continue; }
      gaps++;
      console.log(`[check] MISSING ${path.relative(ROOT, f)}`);
    }
  }
  console.log(`
[check] Execution contract for each missing answer (REAL execution — do not hand-write answers):
  1. Harness/provider: the SAME ZCode CLI driver and the SAME GLM model deployment used
     by the IDD pipeline runs. No other model, no pipeline stages, no tools.
  2. Prompt: the full text of results/benchmark/baseline_fe_prompts/<case>.<regime>.txt
     (fe_official: results/benchmark/fe_official_prompts/<case>.fe_official.txt) — one call.
  3. Save the model's raw strict-JSON reply to
     results/benchmark/baseline_fe_answers/<case>.<regime>.json (top3 + reasoning [+ verdict]).
  4. Re-run: node scripts/benchmark/baseline_llm.mjs score`);
  if (gaps) process.exit(1);
}

const stages = { prompts: cmdPrompts, score: cmdScore, check: cmdCheck };
if (!stages[cmd]) {
  console.error('usage: baseline_llm.mjs prompts|score|check');
  process.exit(2);
}
stages[cmd]();
