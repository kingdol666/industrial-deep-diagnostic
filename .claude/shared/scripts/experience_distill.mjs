#!/usr/bin/env node
// experience_distill.mjs — Step 9.5 deterministic experience distiller.
//
// Extracts reusable diagnostic experience from a COMPLETED run's structured
// artifacts into 06_experience/experience_candidates.jsonl, for POST /accumulate.
//
// Discipline: extraction, not authoring (same rule as the benchmark suite —
// "scripts verify and score; they never author pipeline artifacts"). Every
// field below is copied/projected from structured JSON; no LLM involved.
// Entries are mode-level descriptions only — never raw data rows.
//
// Six entry types:
//   scene_fault_pattern     — column-role/scene shape → root-cause pattern (diagnosis.json)
//   method_efficacy         — which discriminative method actually separated hypotheses
//   repair_lesson           — judge deduction dimensions → next-run avoidance actions
//   artifact_signature      — sensor artifact morphologies seen in this run
//   param_physics_correction— ontology auto-resolutions that overrode guesses
//   negative_sample         — from failed runs (judge<90 or audit not ENDORSED)
//
// Usage: node experience_distill.mjs <run_dir> [--repo-root <path>]

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const runDir = path.resolve(process.argv[2] || '');
if (!fs.existsSync(runDir)) {
  console.error(`run_dir not found: ${runDir}`);
  process.exit(2);
}
const argIdx = process.argv.indexOf('--repo-root');
const REPO_ROOT = path.resolve(argIdx > 0 ? process.argv[argIdx + 1]
  : path.join(path.dirname(fileURLToPath(import.meta.url)), '..', '..', '..', '..'));

const j = p => { try { return JSON.parse(fs.readFileSync(path.join(runDir, p), 'utf-8')); } catch { return null; } };
const read = p => { try { return fs.readFileSync(path.join(runDir, p), 'utf-8'); } catch { return ''; } };

const diagnosis = j('04_diagnostics/diagnosis.json') || {};
const confidence = j('04_diagnostics/confidence.json') || {};
const judge = j('05_review/judge_feedback.json') || {};
const anomaly = j('02_processed/anomaly_report.json') || {};
const sensorAudit = j('02_processed/sensor_artifact_audit.json') || {};
const clarif = j('00_input/clarification_needed.json') || {};
const optimizerText = read('optimizer.md');

const manifest = j('run_manifest.json') || {};
const runId = diagnosis.run_id || manifest.run_id || path.basename(runDir);
const ts = String(runId).split('_')[0];
const sceneKey = String(runId).split('_').slice(1).join('_') || 'unknown';
const era = /^\d{9}$/.test(ts) && Number(ts) < 20260914 ? 'v1_pre_discipline' : '20260914+';
const judgeScore = judge.overall_score ?? null;

// benchmark-case marking (server enforces scene_fault_pattern rejection)
let benchScenes = new Set();
try {
  const bench = JSON.parse(fs.readFileSync(path.join(REPO_ROOT, 'scripts', 'benchmark', 'cases', 'benchmark_cases.json'), 'utf-8'));
  benchScenes = new Set((bench.cases || []).map(c => String(c.case_id || '').toLowerCase()));
} catch { /* repo layout without benchmark — no blacklist applies */ }
const isBenchScene = [...benchScenes].some(b => b && (sceneKey.toLowerCase().includes(b) || b.includes(sceneKey.toLowerCase())));

const entries = [];
const push = (type, payload, applicability, label) => {
  if (!payload) return;
  const hasContent = Object.values(payload).some(v => v != null && v !== '');
  if (!hasContent) return;
  entries.push({
    experience_id: null, // assigned server-side (deterministic hash)
    experience_type: type,
    payload,
    applicability: applicability || { scenario_genus: 'generic' },
    provenance: {
      run_id: runId, scene_key: sceneKey, era, judge_score: judgeScore,
      built_from: 'step_9_5_deterministic_distill_v1',
    },
    confidence_label: label || 'observation',
    corroboration_count: 1,
    refutation_count: 0,
    benchmark_case: isBenchScene || undefined,
  });
};

// ── 1. scene_fault_pattern: surviving root cause + its physical chain ──
const survivors = (diagnosis.hypotheses && (diagnosis.hypotheses.surviving || [])) || [];
for (const h of survivors.slice(0, 2)) {
  const chain = (h.physical_logic_chain || [])
    .map(l => (typeof l === 'string' ? l : l.link || l.description || ''))
    .filter(Boolean).slice(0, 4).join(' → ');
  push('scene_fault_pattern', {
    pattern: `${h.name || h.id || 'root cause'}：${String(h.root_physical_cause || '').slice(0, 600)}`,
    mechanism: chain.slice(0, 900) || h.mechanism_class || '',
    discriminating_evidence: (diagnosis.discriminability_matrix || [])
      .filter(r => Array.isArray(r.pair) && r.pair.includes(h.id))
      .map(r => r.discriminating_signal).filter(Boolean).slice(0, 2).join(' ； ').slice(0, 900),
    applicability_note: `mechanism_class=${h.mechanism_class || 'unknown'}`,
  }, { scenario_genus: 'generic' }, 'observation');
}

// ── 2. method_efficacy: discriminability rows with an available signal ──
const eff = (diagnosis.discriminability_matrix || [])
  .filter(r => r.discriminating_signal_available === true && r.discriminating_signal)
  .slice(0, 3);
for (const r of eff) {
  push('method_efficacy', {
    method: `判别矩阵 ${r.pair ? r.pair.join(' vs ') : ''}（classification=${r.classification || 'unknown'}）`,
    pattern: String(r.discriminating_signal).slice(0, 700),
    discriminating_evidence: String(r.cross_product_finding || r.discriminating_signal).slice(0, 500),
  }, { scenario_genus: 'generic' }, 'observation');
}

// ── 3. repair_lesson: judge warnings / blocking issues → avoidance actions ──
const lessons = [];
for (const w of (judge.warnings || []).slice(0, 5)) {
  const id = typeof w === 'object' ? (w.id || w.code || '') : '';
  const text = typeof w === 'object' ? (w.message || w.description || JSON.stringify(w)) : String(w);
  lessons.push({ lesson: `Judge 警告 ${id}: ${String(text).slice(0, 300)}`, correction: '下一 run 在对应步骤初版即规避该记账/引用问题' });
}
for (const b of (judge.blocking_issues || []).slice(0, 3)) {
  lessons.push({ lesson: `Judge 阻断项: ${String(typeof b === 'object' ? b.message || JSON.stringify(b) : b).slice(0, 300)}`, correction: '修复循环指令已给出一轮；重跑时在首次产出即满足该要求' });
}
for (const l of lessons.slice(0, 5)) push('repair_lesson', l, { scenario_genus: 'generic' }, 'observation');

// ── 4. artifact_signature: sensor artifact morphologies from the audit ──
const channels = sensorAudit.channels || {};
for (const [ch, info] of Object.entries(channels).slice(0, 5)) {
  if (info.floor_value != null && info.total_clamped > 0) {
    push('artifact_signature', {
      signature: `${ch} 下限钳位：floor=${info.floor_value}，全期钳位 ${info.total_clamped} 行（${info.clamped_pct_total}%）`,
      pattern: '连续等值钉在量程下限 + 后期占比激增 → 传感器积灰/量程截断，非过程真实下行；剔除后与其他通道互证不变才可作过程证据',
      discriminating_evidence: info.per_month ? `per_month 演化: ${Object.entries(info.per_month).slice(-2).map(([m, v]) => `${m}=${v.clamped_pct}%`).join(', ')}` : '',
    }, { scenario_genus: 'generic' }, 'observation');
  } else if (info.ceiling_value != null || info.saturation != null) {
    push('artifact_signature', {
      signature: `${ch} 上限饱和：${JSON.stringify(info).slice(0, 250)}`,
      pattern: '连续等值钉在量程上限 → 传感器饱和伪影；引用时声明量程截断',
      discriminating_evidence: '',
    }, { scenario_genus: 'generic' }, 'observation');
  }
}

// ── 5. param_physics_correction: ontology auto-resolutions ──
for (const q of (clarif.auto_resolved || []).slice(0, 5)) {
  push('param_physics_correction', {
    correction: `参数 ${q.parameter || q.column || '?'} 语义自动裁决: ${String(q.resolution || q.inferred_meaning || JSON.stringify(q)).slice(0, 400)}`,
    pattern: `inference_level=${q.inference_level || q.level || 'unknown'}`,
  }, { scenario_genus: 'generic' }, 'observation');
}

// ── 6. negative_sample: only from failed runs ──
const endorsed = /ENDORSED/.test(optimizerText);
if (judgeScore != null && (judgeScore < 90 || !endorsed)) {
  push('negative_sample', {
    misdiagnosis: `本 run judge=${judgeScore}，verdict=${judge.verdict || 'unknown'}，ENDORSED=${endorsed}`,
    actual: (judge.blocking_issues || []).map(b => String(typeof b === 'object' ? b.message || JSON.stringify(b) : b)).join(' ； ').slice(0, 500)
      || '见 judge_feedback.json blocking_issues',
    lesson: '该形态的产出曾未通过质量门——检索命中时应提前对照 blocking 维度自查',
  }, { scenario_genus: 'generic' }, 'negative');
}

// ── write ──
const outDir = path.join(runDir, '06_experience');
fs.mkdirSync(outDir, { recursive: true });
const outPath = path.join(outDir, 'experience_candidates.jsonl');
fs.writeFileSync(outPath, entries.map(e => JSON.stringify(e)).join('\n') + (entries.length ? '\n' : ''));
fs.writeFileSync(path.join(outDir, 'distill_meta.json'), JSON.stringify({
  run_id: runId, scene_key: sceneKey, era, judge_score: judgeScore,
  benchmark_case_scene: isBenchScene,
  entries: entries.reduce((m, e) => { m[e.experience_type] = (m[e.experience_type] || 0) + 1; return m; }, {}),
  total: entries.length, distiller_version: '1.0', generated_at: new Date().toISOString(),
}, null, 2));
console.log(`[experience_distill] ${entries.length} candidates → ${outPath}`);
console.log(`[experience_distill] by type: ${JSON.stringify(entries.reduce((m, e) => { m[e.experience_type] = (m[e.experience_type] || 0) + 1; return m; }, {}))}`);
