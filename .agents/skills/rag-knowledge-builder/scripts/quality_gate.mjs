#!/usr/bin/env node
// quality_gate.mjs — rag-knowledge-builder output-contract gate (house pattern).
//
// Usage: node quality_gate.mjs --run-dir <RUN_DIR>      (checks <RUN_DIR>/00_input)
//        node quality_gate.mjs --input-dir <DIR>        (checks DIR directly)
// Exit: 0 ok | 1 hard error (bad args / unreadable) | 2 undetermined (no rag
//       artifacts at all — the build did not run here) | 3 gate-fail
//
// The contract checked here is the ONE DOCUMENTED IN THE SKILL, not invented:
//  * output set from SKILL.md "Output contracts (all written to $run_dir/00_input/)"
//  * blocking structural rules from references/quality-verification-agent.md
//    Check 1 (rows marked "Blocking"): scene.name/domain_type non-empty,
//    domain_type != "generic", concepts.{target_concepts,related_concepts,
//    context_dimensions} exist, every concept has name/definition/
//    definition_confidence/broader_concept, every relationship has from/to/type/
//    mechanism
//  * audit-log shape from the same doc ("Verification Output" JSON: verdict +
//    checks + summary); verdict FAIL is itself a gate failure
//  * NL spec existence from SKILL.md ("DO NOT skip the natural-language spec")
//
// Checks (mechanical):
//   R1 the five documented build artifacts exist and parse (draft + nl spec +
//      structured data + scored chunks + audit log)
//   R2 draft structural blocking rules (Check 1)
//   R3 audit log: verdict in {PASS, CONDITIONAL, FAIL}; FAIL => gate-fail;
//      checks/summary objects present
//   R4 structured data: parseable, non-empty object
//   R5 scored chunks: chunks is a list; a legitimate zero-chunk build is a note
//      (documented degradation path "no results from KB -> evidence_gap")
//   R6 NL spec mechanical completeness proxy: >=200 chars and >=1 markdown heading
//   R7 (notes only) provenance coverage: concepts/entities/relationships
//      missing knowledge_source are counted and reported, never failed
//
// Zero dependencies (node builtins only).

import { existsSync, readFileSync, statSync } from 'fs';
import { join, resolve } from 'path';

const args = process.argv.slice(2);
const argOf = (k) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : undefined; };
const runDir = argOf('--run-dir');
const inputDirOpt = argOf('--input-dir');
if (!runDir && !inputDirOpt) {
  console.log(JSON.stringify({ gate: 'rag_kb_quality_gate', verdict: 'hard_error', reason: 'usage: --run-dir <RUN_DIR> or --input-dir <DIR>' }, null, 2));
  process.exit(1);
}
const INPUT_DIR = resolve(inputDirOpt || join(runDir, '00_input'));

const FAILS = [];
const NOTES = [];
const fail = (id, msg) => FAILS.push(`${id}: ${msg}`);
const note = (msg) => NOTES.push(msg);
process.on('uncaughtException', (e) => {
  console.log(JSON.stringify({ gate: 'rag_kb_quality_gate', verdict: 'gate_fail', fails: [...FAILS, `GATE: unhandled error: ${e.message}`], notes: NOTES }, null, 2));
  process.exit(3);
});

if (!existsSync(INPUT_DIR) || !statSync(INPUT_DIR).isDirectory()) {
  console.log(JSON.stringify({ gate: 'rag_kb_quality_gate', verdict: 'hard_error', reason: `input dir missing or not a directory: ${INPUT_DIR}` }, null, 2));
  process.exit(1);
}

const P = (f) => join(INPUT_DIR, f);
const DRAFT = 'rag_ontology_draft.json';
const NL_SPEC = 'rag_ontology_nl_spec.md';
const STRUCTURED = 'rag_structured_data.json';
const CHUNKS = 'rag_scored_chunks.json';
const AUDIT = 'rag_audit_log.json';
const CLARIFY = 'rag_clarification_needed.json';
const REQUIRED = [DRAFT, NL_SPEC, STRUCTURED, CHUNKS, AUDIT];
const MARKERS = [...REQUIRED, CLARIFY];

// ── R0 stage marker: nothing at all => the build did not run here ──────
if (!MARKERS.some((f) => existsSync(P(f)))) {
  console.log(JSON.stringify({ gate: 'rag_kb_quality_gate', verdict: 'undetermined', reason: `no rag_* artifacts in ${INPUT_DIR} — the knowledge-base build did not run here` }, null, 2));
  process.exit(2);
}

const readJson = (f) => {
  if (!existsSync(P(f))) { fail('R1', `${f} missing`); return null; }
  try { return JSON.parse(readFileSync(P(f), 'utf-8')); }
  catch (e) { fail('R1', `${f} unparseable: ${e.message}`); return null; }
};
const nonEmptyStr = (v) => typeof v === 'string' && v.trim().length > 0;

// ── R1 artifacts present + parseable ──────────────────────────────────
const draft = readJson(DRAFT);
const structured = readJson(STRUCTURED);
const chunksDoc = readJson(CHUNKS);
const audit = readJson(AUDIT);
if (!existsSync(P(NL_SPEC))) fail('R1', `${NL_SPEC} missing`);
else if (readFileSync(P(NL_SPEC), 'utf-8').trim() === '') fail('R1', `${NL_SPEC} is empty`);

// ── R2 draft structural blocking rules ────────────────────────────────
if (draft !== null) {
  if (!draft || typeof draft !== 'object' || Array.isArray(draft)) {
    fail('R2', `${DRAFT} is not an object`);
  } else {
    const scene = draft.scene;
    if (!scene || typeof scene !== 'object') fail('R2', 'scene object missing');
    else {
      if (!nonEmptyStr(scene.name)) fail('R2', 'scene.name is empty');
      if (!nonEmptyStr(scene.domain_type)) fail('R2', 'scene.domain_type is empty');
      else if (String(scene.domain_type).trim().toLowerCase() === 'generic') fail('R2', 'scene.domain_type is "generic" (blocking per verification doc)');
    }
    const concepts = draft.concepts;
    const groups = ['target_concepts', 'related_concepts', 'context_dimensions'];
    if (!concepts || typeof concepts !== 'object') {
      fail('R2', 'concepts object missing');
    } else {
      for (const g of groups) {
        if (!Array.isArray(concepts[g])) { fail('R2', `concepts.${g} missing or not a list`); continue; }
        concepts[g].forEach((c, i) => {
          if (!c || typeof c !== 'object') { fail('R2', `concepts.${g}[${i}] is not an object`); return; }
          for (const k of ['name', 'definition', 'definition_confidence']) {
            if (!nonEmptyStr(c[k])) fail('R2', `concepts.${g}[${i}] (${c.name || 'unnamed'}) missing ${k}`);
          }
          // broader_concept is a blocking hierarchy rule for concepts, not for
          // context dimensions (which are categorical fields, not IS-A concepts)
          if (g !== 'context_dimensions' && !nonEmptyStr(c.broader_concept)) {
            fail('R2', `concepts.${g}[${i}] (${c.name || 'unnamed'}) missing broader_concept`);
          }
        });
      }
    }
    if (!Array.isArray(draft.relationships)) {
      fail('R2', 'relationships list missing');
    } else {
      draft.relationships.forEach((r, i) => {
        if (!r || typeof r !== 'object') { fail('R2', `relationships[${i}] is not an object`); return; }
        for (const k of ['from', 'to', 'type', 'mechanism']) {
          if (!nonEmptyStr(r[k])) fail('R2', `relationships[${i}] (${r.id || r.name || 'unnamed'}) missing ${k}`);
        }
      });
    }
  }
}

// ── R3 audit log ──────────────────────────────────────────────────────
if (audit !== null) {
  if (!audit || typeof audit !== 'object' || Array.isArray(audit)) {
    fail('R3', `${AUDIT} is not an object`);
  } else {
    const verdict = audit.verdict;
    if (!['PASS', 'CONDITIONAL', 'FAIL'].includes(verdict)) fail('R3', `audit verdict "${verdict}" not in {PASS, CONDITIONAL, FAIL}`);
    else if (verdict === 'FAIL') fail('R3', 'audit recorded verdict FAIL — the build failed its own quality verification');
    else if (verdict === 'CONDITIONAL') note('audit verdict CONDITIONAL — accepted, consumer must read the conditions');
    if (!audit.checks || typeof audit.checks !== 'object') fail('R3', 'audit.checks object missing');
    if (!audit.summary || typeof audit.summary !== 'object') fail('R3', 'audit.summary object missing');
  }
}

// ── R4 structured data ────────────────────────────────────────────────
if (structured !== null) {
  if (!structured || typeof structured !== 'object' || Array.isArray(structured) || Object.keys(structured).length === 0) {
    fail('R4', `${STRUCTURED} is not a non-empty object`);
  }
}

// ── R5 scored chunks ──────────────────────────────────────────────────
if (chunksDoc !== null) {
  if (!chunksDoc || typeof chunksDoc !== 'object' || Array.isArray(chunksDoc)) {
    fail('R5', `${CHUNKS} is not an object`);
  } else {
    if (!nonEmptyStr(chunksDoc.status)) fail('R5', 'scored-chunks status is empty');
    if (!Array.isArray(chunksDoc.chunks)) fail('R5', 'scored-chunks .chunks is not a list');
    else if (chunksDoc.chunks.length === 0) note('zero scored chunks — legitimate only via the documented "no KB results -> evidence_gap" degradation path');
  }
}

// ── R6 NL spec mechanical completeness ────────────────────────────────
if (existsSync(P(NL_SPEC))) {
  const text = readFileSync(P(NL_SPEC), 'utf-8');
  if (text.trim().length < 200) fail('R6', `${NL_SPEC} shorter than 200 chars — "severely incomplete" per verification doc`);
  if (!/^#{1,6}\s/m.test(text)) fail('R6', `${NL_SPEC} has no markdown heading`);
}

// ── R7 provenance coverage (notes only) ───────────────────────────────
if (draft && typeof draft === 'object') {
  let missing = 0, total = 0;
  const bump = (item) => { total += 1; if (!item || typeof item !== 'object' || !nonEmptyStr(item.knowledge_source)) missing += 1; };
  const c = draft.concepts || {};
  for (const g of ['target_concepts', 'related_concepts', 'context_dimensions']) {
    if (Array.isArray(c[g])) c[g].forEach(bump);
  }
  if (Array.isArray(draft.entities)) draft.entities.forEach(bump);
  if (Array.isArray(draft.relationships)) draft.relationships.forEach(bump);
  if (total > 0 && missing > 0) note(`provenance: ${missing}/${total} concepts/entities/relationships lack knowledge_source (design principle 5)`);
}

// ── verdict ───────────────────────────────────────────────────────────
const verdict = FAILS.length ? 'gate_fail' : 'ok';
console.log(JSON.stringify({ gate: 'rag_kb_quality_gate', verdict, input_dir: INPUT_DIR, fails: FAILS.slice(0, 40), notes: NOTES }, null, 2));
process.exit(FAILS.length ? 3 : 0);
