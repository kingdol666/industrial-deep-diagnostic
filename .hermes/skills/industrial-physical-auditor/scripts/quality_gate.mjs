#!/usr/bin/env node
// quality_gate.mjs — industrial-physical-auditor deterministic quality gate.
// Executor of pipeline CP-8 (final audit, ENDORSED) and the Step 5b pre-audit
// (05_review/optimizer_preflight.md). Zero dependencies (node builtins only).
//
// Usage: node quality_gate.mjs --run-dir <RUN_DIR> [--pre-audit]
//   default     FINAL mode  -> gates RUN_DIR/optimizer.md
//   --pre-audit PRE mode    -> gates RUN_DIR/05_review/optimizer_preflight.md
// Exit: 0 ok | 1 hard error (bad inputs / usage) | 2 undetermined (the audit
//       artifact is absent — the audit did not run) | 3 gate-fail
//
// Checks (all mechanical):
//   A1 artifact exists (else undetermined/exit 2)
//   A2 a recognized verdict is present (SKILL.md vocabulary):
//        FINAL: ENDORSED | CONDITIONAL | REJECTED
//        PRE:   PREFLIGHT_PASS | PREFLIGHT_NEEDS_REPAIR | PREFLIGHT_BLOCKED
//      (context lines 判定/结论/verdict/终审 rank first; then standalone token
//      lines; then any occurrence — the last ranked line wins; a line carrying
//      two conflicting tokens is ambiguous and fails)
//   A3 the recognized verdict is the PASS verdict — FINAL: ENDORSED (CP-8),
//      PRE: PREFLIGHT_PASS. CONDITIONAL/REJECTED/NEEDS_REPAIR/BLOCKED are
//      well-formed verdicts but stop the checkpoint (repair loop); the exact
//      verdict travels in the JSON `auditor_verdict` field for branching.
//   A4 required sections present — FINAL mirrors the repository's optimizer.md
//      content contract (pipeline-finalize.mjs §5d: audit overview /
//      statistical verification / physics verification / verdict); PRE checks
//      the protocol's verdict + mechanism/physics check + findings shape.
//   A5 (FINAL) evidence grounding: >= 3 grounding terms (pipeline-finalize §5d)
//   A6 (PRE, when repair is demanded) concrete repair_instruction content
//   Schema: a reviewer artifact schema would be validated here if one existed;
//      none exists (.claude/shared/schemas/ holds no optimizer/audit/preflight
//      schema and this skill has no schemas/ dir) — recorded as a note.
//
// Output: single machine-readable JSON verdict on stdout.

import { existsSync, readFileSync, readdirSync, statSync } from 'fs';
import { dirname, join, resolve } from 'path';
import { fileURLToPath } from 'url';

const HERE = dirname(fileURLToPath(import.meta.url));
const SKILL_DIR = resolve(HERE, '..');
const REPO_ROOT = resolve(HERE, '..', '..', '..', '..');
const SHARED_DIR = join(REPO_ROOT, '.claude', 'shared');

const args = process.argv.slice(2);
const argOf = (k) => {
  const i = args.indexOf(k);
  if (i >= 0) return args[i + 1];
  const pref = args.find((a) => a.startsWith(`${k}=`));
  return pref ? pref.slice(k.length + 1) : undefined;
};
const PRE = args.includes('--pre-audit');

const CHECKS = [];
const NOTES = [];
const check = (id, ok, detail = '') => CHECKS.push({ id, ok: !!ok, detail: String(detail) });
const note = (msg) => NOTES.push(msg);

function emit(verdict, exitCode, extra = {}) {
  const fails = CHECKS.filter((c) => !c.ok).map((c) => `${c.id}: ${c.detail || 'failed'}`);
  console.log(JSON.stringify({
    gate: 'physical_audit_quality_gate',
    mode: PRE ? 'pre-audit' : 'final',
    verdict,
    checks: CHECKS,
    fails,
    notes: NOTES,
    summary: `${CHECKS.filter((c) => c.ok).length}/${CHECKS.length} checks passed`,
    ...extra,
  }, null, 2));
  process.exit(exitCode);
}

// fail-closed: any unexpected error still emits a structured verdict
process.on('uncaughtException', (e) => {
  check('GATE', false, `unhandled error: ${e.message}`);
  emit('gate_fail', 3);
});

// ───────────────────────────── inputs ─────────────────────────────
const runDirArg = argOf('--run-dir') || (args[0] && !args[0].startsWith('--') ? args[0] : undefined);
if (!runDirArg) {
  console.error('Usage: node quality_gate.mjs --run-dir <RUN_DIR> [--pre-audit]');
  process.exit(1);
}
const RUN_DIR = resolve(runDirArg);
if (!existsSync(RUN_DIR) || !statSync(RUN_DIR).isDirectory()) {
  check('GATE', false, `run dir not found: ${RUN_DIR}`);
  emit('hard_error', 1, { run_dir: RUN_DIR, reason: 'run dir does not exist or is not a directory' });
}

const REL = PRE ? join('05_review', 'optimizer_preflight.md') : 'optimizer.md';
const ARTIFACT = join(RUN_DIR, REL);
const PASS_VERDICT = PRE ? 'PREFLIGHT_PASS' : 'ENDORSED';
const TOKENS = PRE
  ? ['PREFLIGHT_PASS', 'PREFLIGHT_NEEDS_REPAIR', 'PREFLIGHT_BLOCKED']
  : ['ENDORSED', 'CONDITIONAL', 'REJECTED'];

// ── A1: existence ─────────────────────────────────────────────────
if (!existsSync(ARTIFACT) || !statSync(ARTIFACT).isFile()) {
  console.log(JSON.stringify({
    gate: 'physical_audit_quality_gate',
    mode: PRE ? 'pre-audit' : 'final',
    verdict: 'undetermined',
    run_dir: RUN_DIR,
    artifact: REL,
    reason: `${REL} absent — the ${PRE ? 'pre-report (Step 5b)' : 'final (Step 7)'} audit did not run (or its output was removed)`,
    checks: [],
    fails: [],
    notes: NOTES,
  }, null, 2));
  process.exit(2);
}
const content = readFileSync(ARTIFACT, 'utf-8');
check('A1_artifact_exists', true, `${REL} (${statSync(ARTIFACT).size} bytes)`);

// ── A2: verdict recognition (tiered, deterministic) ───────────────
function findVerdict(text, tokens) {
  const lines = String(text).split(/\r?\n/);
  const ctxRe = /(判定|结论|verdict|总判定|终审|审计结论|preflight)/i;
  const tiers = [[], [], []];
  lines.forEach((line, i) => {
    const found = tokens.filter((t) => new RegExp(t, 'i').test(line));
    if (!found.length) return;
    const cleaned = line.replace(/[*_`#>：:]/g, ' ').trim();
    const words = cleaned.split(/\s+/).filter(Boolean);
    const isStandalone = words.length === 1 && tokens.some((t) => t.toLowerCase() === words[0].toLowerCase());
    const rec = { line: i + 1, tokens: found, text: line.trim().slice(0, 160) };
    tiers[ctxRe.test(line) ? 0 : isStandalone ? 1 : 2].push(rec);
  });
  const tier = tiers.findIndex((t) => t.length > 0);
  if (tier < 0) return null;
  const ranked = tiers[tier];
  const last = ranked[ranked.length - 1];
  const distinct = [...new Set(last.tokens)];
  const allDistinct = [...new Set(ranked.flatMap((r) => r.tokens))];
  return {
    verdict: distinct.length === 1 ? distinct[0].toUpperCase() : null,
    ambiguous: distinct.length > 1 ? last : null,
    line: last.line,
    line_text: last.text,
    tier,
    occurrences: ranked.length,
    conflicting: allDistinct.length > 1 ? allDistinct : null,
  };
}

const otherTokens = PRE
  ? ['ENDORSED', 'CONDITIONAL', 'REJECTED']
  : ['PREFLIGHT_PASS', 'PREFLIGHT_NEEDS_REPAIR', 'PREFLIGHT_BLOCKED'];
const hit = findVerdict(content, TOKENS);
let auditorVerdict = null;
if (!hit) {
  const wrongMode = otherTokens.filter((t) => new RegExp(t, 'i').test(content));
  check('A2_verdict_recognized', false,
    wrongMode.length
      ? `no ${PRE ? 'preflight' : 'final'} verdict token found — file carries the other mode's vocabulary (${wrongMode.join(', ')})`
      : `no verdict token found (expected one of: ${TOKENS.join(' | ')})`);
} else if (hit.ambiguous) {
  check('A2_verdict_recognized', false,
    `ambiguous verdict on line ${hit.ambiguous.line} (${hit.ambiguous.tokens.join(' + ')}): ${hit.ambiguous.text}`);
} else {
  auditorVerdict = hit.verdict;
  if (hit.conflicting) {
    note(`verdict tokens ${hit.conflicting.join(', ')} appear in the file; the last verdict line (line ${hit.line}, tier ${hit.tier}) was used: ${hit.verdict}`);
  }
  check('A2_verdict_recognized', true, `${hit.verdict} (line ${hit.line})`);
}

// ── A3: pass-verdict checkpoint semantics ─────────────────────────
if (auditorVerdict) {
  const ok = auditorVerdict === PASS_VERDICT;
  check('A3_verdict_is_pass', ok,
    ok ? auditorVerdict
       : `verdict ${auditorVerdict} is well-formed but not a pass — ${PRE ? 'pre-audit' : 'CP-8'} requires ${PASS_VERDICT} (repair loop)`);
} else {
  note('A3 skipped — no recognized verdict');
}

// ── A4: required sections ─────────────────────────────────────────
if (PRE) {
  const sections = [
    { name: 'verdict', re: [/verdict/i, /判定|结论|终审|预审计|PREFLIGHT_PASS|PREFLIGHT_NEEDS_REPAIR|PREFLIGHT_BLOCKED/] },
    { name: 'physics/mechanism check', re: [/physics|mechanism/i, /物理|机制/] },
    { name: 'findings', re: [/finding|issue/i, /发现|问题/] },
  ];
  const missing = sections.filter((s) => !s.re.some((r) => r.test(content))).map((s) => s.name);
  check('A4_sections_present', missing.length === 0,
    missing.length ? `missing sections: ${missing.join(', ')}` : sections.map((s) => s.name).join(' / '));
} else {
  // mirrors pipeline-finalize.mjs §5d optimizer.md content contract
  const lowered = content.toLowerCase();
  const sections = [
    { name: 'audit overview', re: [/audit overview/, /审计总览|独立验算|判定/] },
    { name: 'statistical verification', re: [/statistical verification/, /统计.*(核验|基础|验证|抽验|复算)/, /独立复算|数字抽验/] },
    { name: 'physics verification', re: [/physics verification/, /物理.*(核验|真实|验证|真相|链|机制)/] },
    { name: 'verdict', re: [/verdict/, /判定|终审|endorsed|conditional|rejected/] },
  ];
  const missing = sections.filter((s) => !s.re.some((r) => r.test(lowered))).map((s) => s.name);
  check('A4_sections_present', missing.length === 0,
    missing.length ? `missing sections: ${missing.join(', ')}` : sections.map((s) => s.name).join(' / '));
}

// ── A5: FINAL evidence grounding (mirrors pipeline-finalize §5d) ──
if (!PRE) {
  const terms = ['evidence', 'diagnosis', 'ontology', 'physics', 'visual', '数据', '诊断', '本体', '物理', '证据', '图像'];
  const lowered = content.toLowerCase();
  const distinct = terms.filter((t) => lowered.includes(t.toLowerCase())).length;
  check('A5_evidence_grounding', distinct >= 3, `${distinct} grounding terms (need >= 3)`);
}

// ── A6: PRE repair instructions when repair is demanded ───────────
if (PRE && auditorVerdict && auditorVerdict !== 'PREFLIGHT_PASS') {
  const hasRepair = /repair[_ ]?instruction|修复指令|整改指令|repair instruction/i.test(content);
  check('A6_repair_instructions', hasRepair,
    hasRepair ? 'repair_instruction content present'
              : `${auditorVerdict} demands concrete repair_instruction items — none found`);
}

// ── schema probe (report-only: no reviewer artifact schema exists today) ──
const schemaHits = [];
const skillSchemas = join(SKILL_DIR, 'schemas');
if (existsSync(skillSchemas)) {
  for (const f of readdirSync(skillSchemas)) if (f.endsWith('.json')) schemaHits.push(join(skillSchemas, f));
}
const sharedSchemas = join(SHARED_DIR, 'schemas');
if (existsSync(sharedSchemas)) {
  for (const f of readdirSync(sharedSchemas)) {
    if (/optimizer|auditor|audit_verdict|preflight|reviewer/i.test(f)) schemaHits.push(join(sharedSchemas, f));
  }
}
if (schemaHits.length === 0) {
  note('no reviewer artifact schema found (searched skill schemas/ + .claude/shared/schemas for optimizer/auditor/preflight/reviewer) — markdown contract checks only');
} else {
  note(`reviewer schema candidate(s) present but not applicable: ${schemaHits.join(', ')} (this skill emits markdown, no JSON companion artifact to validate)`);
}

// ── verdict ───────────────────────────────────────────────────────
const allOk = CHECKS.every((c) => c.ok);
emit(allOk ? 'ok' : 'gate_fail', allOk ? 0 : 3, {
  run_dir: RUN_DIR,
  artifact: REL,
  auditor_verdict: auditorVerdict,
});
