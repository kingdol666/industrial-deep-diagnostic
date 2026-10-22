#!/usr/bin/env node
// Static skill / agent design audit — no diagnosis run, no engine spawn.
//
// Checks the architecture contract in AGENTS.md:
//   * 24 skills, each with SKILL.md + valid frontmatter (name matches dir,
//     description non-empty, body has sections);
//   * 16 OMP task agents, each with valid frontmatter and an initialization
//     section that loads a skill-side protocol/framework (or inline protocol);
//   * every JSON schema parses;
//   * script paths mentioned in SKILL.md resolve (skill dir or repo root);
//   * mirrors in sync (delegated to sync-harness-skills --check).
//
// Usage: node scripts/audit/skill-design.mjs
import { existsSync, readFileSync, readdirSync, statSync } from 'fs';
import { join, resolve } from 'path';

const ROOT = resolve(import.meta.dirname, '..', '..');
const SKILLS = join(ROOT, '.claude', 'skills');
const AGENTS = join(ROOT, '.omp', 'agents');

let failures = 0;
const problems = [];
function check(name, ok, detail = '') {
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? `  ${String(detail).slice(0, 200)}` : ''}`);
  if (!ok) { failures += 1; problems.push({ name, detail: String(detail || '') }); }
}

function parseFrontmatter(text) {
  const m = text.match(/^---\r?\n([\s\S]*?)\r?\n---/);
  if (!m) return null;
  const out = {};
  const lines = m[1].split(/\r?\n/);
  for (let i = 0; i < lines.length; i += 1) {
    const mm = lines[i].match(/^([A-Za-z_][\w-]*):\s*(.*)$/);
    if (!mm) continue;
    const key = mm[1];
    let value = mm[2].trim();
    // YAML block scalars (`description: >` / `|`) carry the text on the
    // following indented lines; join them instead of reporting length 1.
    if (value === '>' || value === '|' || value === '>-' || value === '|-') {
      const parts = [];
      let j = i + 1;
      while (j < lines.length && (/^\s+/.test(lines[j]) || lines[j].trim() === '')) {
        parts.push(lines[j].trim());
        j += 1;
      }
      value = parts.join(' ').trim();
      i = j - 1;
    }
    out[key] = value.replace(/^["']|["']$/g, '').trim();
  }
  return out;
}

function walk(dir, pred, acc = []) {
  if (!existsSync(dir)) return acc;
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    const st = statSync(p);
    if (st.isDirectory()) walk(p, pred, acc);
    else if (pred(p)) acc.push(p);
  }
  return acc;
}

// ── Skills ─────────────────────────────────────────────────────────────
const skillDirs = readdirSync(SKILLS).filter((d) => statSync(join(SKILLS, d)).isDirectory()).sort();
check('skill count = 24', skillDirs.length === 24, skillDirs.length);

const scriptRefMissing = [];
const schemaCount = { total: 0, bad: 0 };
for (const name of skillDirs) {
  const dir = join(SKILLS, name);
  const skillMd = join(dir, 'SKILL.md');
  if (!existsSync(skillMd)) { check(`skill ${name}: SKILL.md`, false, 'missing'); continue; }
  const text = readFileSync(skillMd, 'utf-8');
  const fm = parseFrontmatter(text);
  const body = text.replace(/^---[\s\S]*?---/, '');
  const headings = (body.match(/^#{2,3}\s+/gm) || []).length;
  const hasTriggers = /\b(Trigger|Triggers|Use when|触发|适用)\b/i.test(text);
  const hasBoundary = /\b(Negative boundary|Not for|Do NOT use|不适用|不用于)\b/i.test(text);
  check(`skill ${name}: frontmatter name matches dir`, fm?.name === name, fm?.name || 'no frontmatter');
  check(`skill ${name}: has description`, !!fm?.description && fm.description.length >= 40, (fm?.description || '').length);
  check(`skill ${name}: body has >=3 sections`, headings >= 3, headings);
  check(`skill ${name}: declares triggers`, hasTriggers, hasTriggers ? '' : 'no Trigger/Use when');
  if (!hasBoundary) {
    // Not every skill needs a negative boundary; only note it (not a failure).
    console.log(`  note  ${name}: no explicit negative boundary wording`);
  }

  for (const p of walk(dir, (f) => f.endsWith('.json') && /schemas?[\\/]/.test(f))) {
    schemaCount.total += 1;
    try { JSON.parse(readFileSync(p, 'utf-8')); } catch { schemaCount.bad += 1; }
  }

  // Script paths written as `scripts/foo.py` or `industrial-x/scripts/foo.py`.
  const refs = new Set((text.match(/(?:[\w.-]+\/)*scripts\/[\w./-]+\.(?:py|mjs|js|sh|ps1)/g) || []));
  for (const ref of refs) {
    // Runtime-variable prefixes are resolved by the agent at execution time,
    // not from the repository layout; only literal paths are checked.
    if (/^(SHARED_PATH|SKILL_PATH|SKILL_PATH_DATA_PROCESSOR|PROJECT_ROOT|RUN_DIR|DVSKILL_PATH)\b/.test(ref)) continue;
    const candidates = [
      join(dir, ref),
      join(ROOT, ref),
      join(SKILLS, ref),
      join(ROOT, '.claude', 'skills', ref),
      // `<shared>/scripts/...` in prose refers to the shared toolchain.
      join(ROOT, '.claude', 'shared', ref),
    ];
    if (!candidates.some((c) => existsSync(c))) scriptRefMissing.push(`${name}: ${ref}`);
  }
}
check('JSON schemas parse', schemaCount.bad === 0, `${schemaCount.total} files, ${schemaCount.bad} bad`);
check('SKILL.md script references resolve', scriptRefMissing.length === 0,
  scriptRefMissing.slice(0, 12).join(' | ') || `${scriptRefMissing.length} missing`);

// ── Agents ─────────────────────────────────────────────────────────────
const agentFiles = readdirSync(AGENTS).filter((f) => f.endsWith('.md')).sort();
check('agent count = 16', agentFiles.length === 16, agentFiles.length);

const protocolSkills = skillDirs.filter((d) => existsSync(join(SKILLS, d, 'references', 'agent-protocol.md')));
check('skill-side agent protocols exist (>=16)', protocolSkills.length >= 16, protocolSkills.length);

for (const file of agentFiles) {
  const name = file.replace(/\.md$/, '');
  const text = readFileSync(join(AGENTS, file), 'utf-8');
  const fm = parseFrontmatter(text);
  check(`agent ${name}: frontmatter name`, fm?.name === name, fm?.name || 'none');
  check(`agent ${name}: description`, !!fm?.description && fm.description.length >= 40, (fm?.description || '').length);
  check(`agent ${name}: model + tools`, !!fm?.model && !!fm?.tools, JSON.stringify({ model: fm?.model, tools: fm?.tools }));
  const loadsProtocol = /agent-protocol\.md/.test(text);
  const loadsSkillOrFramework = /(SKILL\.md|visual_analysis_framework\.md|protocol\.md|Required Reading)/.test(text);
  check(`agent ${name}: loads protocol/framework`, loadsProtocol || loadsSkillOrFramework,
    loadsProtocol ? 'agent-protocol.md' : (loadsSkillOrFramework ? 'skill/framework reading' : 'none'));
}

// ── Mirrors ────────────────────────────────────────────────────────────
// Delegated to the sync script (byte-level check); this audit only asserts
// the mirror directories exist so a missing mirror cannot pass silently.
check('mirror .agents/skills exists', existsSync(join(ROOT, '.agents', 'skills')));
check('mirror .hermes/skills exists', existsSync(join(ROOT, '.hermes', 'skills')));

console.log(`\n[RESULT] failures=${failures}`);
if (failures) {
  console.log('Problems:');
  for (const p of problems) console.log(`  - ${p.name}${p.detail ? `: ${p.detail}` : ''}`);
}
process.exit(failures ? 1 : 0);
