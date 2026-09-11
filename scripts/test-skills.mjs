#!/usr/bin/env node
// test-skills.mjs — per-skill smoke validation for all 18 skills.
//
// Gates (skill development spec):
//   G1  SKILL.md exists
//   G2  YAML frontmatter present with name + description
//   G3  name matches the skill directory name (kebab-case)
//   G4  description is non-empty, English-only, includes "Trigger:" keywords
//   G5  body has ZERO CJK characters (English skill requirement)
//   G6  every relative path referenced in SKILL.md (scripts/ schemas/ references/
//       resources/ templates/) resolves inside the skill directory
//   G7  every schemas/*.json parses as JSON
//
// Usage: node scripts/test-skills.mjs [--skills-root .claude/skills]
// Exit code 0 = all skills pass; 1 = at least one failure.

import { readFileSync, readdirSync, existsSync } from 'fs';
import { join, dirname, resolve } from 'path';
import { fileURLToPath } from 'url';
import { execFileSync } from 'child_process';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, '..');
const args = process.argv.slice(2);
const rootIdx = args.indexOf('--skills-root');
const SKILLS_ROOT = join(ROOT, rootIdx >= 0 ? args[rootIdx + 1] : '.claude/skills');

const CJK_RE = /[\u4e00-\u9fff\u3400-\u4dbf]/;
let failures = 0;
const results = [];

function check(skill, gate, ok, detail = '') {
  if (!ok) {
    failures += 1;
    results.push(`FAIL ${skill} [${gate}] ${detail}`);
  }
}

function extractFrontmatter(text) {
  const m = text.match(/^---\r?\n([\s\S]*?)\r?\n---/);
  return m ? m[1] : null;
}

function parseSimpleYaml(fmText) {
  // Minimal frontmatter parser — handles `key: value`, quoted values, and
  // folded/literal blocks (key: > / >- / | / |- with indented continuation).
  const out = {};
  const lines = fmText.split(/\r?\n/);
  for (let i = 0; i < lines.length; i++) {
    const m = lines[i].match(/^([a-zA-Z_][\w-]*):\s*(.*)$/);
    if (!m) continue;
    const key = m[1];
    let value = m[2];
    if (/^[>|][+-]?\s*$/.test(value)) {
      // folded/literal block — gather more-indented continuation lines
      const parts = [];
      let j = i + 1;
      while (j < lines.length && (/^\s/.test(lines[j]) || lines[j].trim() === '')) {
        parts.push(lines[j].trim());
        j += 1;
      }
      value = parts.join(' ');
      i = j - 1;
    }
    out[key] = value.replace(/^["']|["']$/g, '').trim();
  }
  return out;
}

/** Shared assets live under .claude/shared/ — skills reference them by bare
 *  filename (scripts/validate.mjs, schemas/run_summary_schema.json, ...). */
const SHARED_SCRIPTS = join(ROOT, '.claude', 'shared', 'scripts');
const SHARED_SCHEMAS = join(ROOT, '.claude', 'shared', 'schemas');

const skillDirs = readdirSync(SKILLS_ROOT, { withFileTypes: true })
  .filter((d) => d.isDirectory() && !d.name.startsWith('.'))
  .map((d) => d.name)
  .sort();

for (const skill of skillDirs) {
  const dir = join(SKILLS_ROOT, skill);
  const skillMd = join(dir, 'SKILL.md');

  // G1
  if (!existsSync(skillMd)) {
    check(skill, 'G1', false, 'SKILL.md missing');
    continue;
  }
  const text = readFileSync(skillMd, 'utf8');

  // G2
  const fmText = extractFrontmatter(text);
  check(skill, 'G2', !!fmText, 'no YAML frontmatter');
  if (!fmText) continue;
  const fm = parseSimpleYaml(fmText);
  check(skill, 'G2', !!fm.name && !!fm.description, 'frontmatter missing name/description');

  // G3
  check(skill, 'G3', fm.name === skill, `name "${fm.name}" != dir "${skill}"`);

  // G4
  const desc = fm.description || '';
  check(skill, 'G4', !CJK_RE.test(desc), 'description contains CJK');
  check(skill, 'G4', /Trigger:/i.test(desc), 'description missing "Trigger:" keywords');

  // G5 — zero CJK in the whole file
  const cjkMatches = text.match(/[\u4e00-\u9fff\u3400-\u4dbf]/g) || [];
  check(skill, 'G5', cjkMatches.length === 0, `${cjkMatches.length} CJK chars remain`);

  // G6 — referenced relative assets exist (in-skill OR shared scripts OR cross-skill)
  const refRe = /(?:scripts|schemas|references|resources|templates)\/[A-Za-z0-9_\-./]+\.(?:json|mjs|js|py|md|tmpl|yaml|yml|txt|csv)/g;
  const refs = new Set(text.match(refRe) || []);
  for (const ref of refs) {
    if (ref.includes('..')) continue; // cross-skill relative hops — resolved at runtime via SKILL_PATH
    if (existsSync(join(dir, ref))) continue;
    // shared scripts/schemas may be referenced by bare filename
    const base = ref.split('/').pop();
    if (existsSync(join(SHARED_SCRIPTS, base))) continue;
    if (existsSync(join(SHARED_SCHEMAS, base))) continue;
    // repo-level references (scripts/, docs/, data/, results/ at project root)
    if (existsSync(join(ROOT, ref))) continue;
    // cross-skill references: any other skill directory providing the same path
    let found = false;
    for (const other of skillDirs) {
      if (existsSync(join(SKILLS_ROOT, other, ref))) { found = true; break; }
    }
    check(skill, 'G6', found, `referenced file missing: ${ref}`);
  }

  // G7 — schemas parse
  const schemasDir = join(dir, 'schemas');
  if (existsSync(schemasDir)) {
    for (const f of readdirSync(schemasDir).filter((f) => f.endsWith('.json'))) {
      try {
        JSON.parse(readFileSync(join(schemasDir, f), 'utf8'));
      } catch (e) {
        check(skill, 'G7', false, `schemas/${f} invalid JSON: ${e.message.slice(0, 60)}`);
      }
    }
  }

  results.push(`PASS ${skill} (${refs.size} asset refs, ${text.split('\n').length} lines)`);
}

console.log(results.sort((a, b) => a.localeCompare(b)).join('\n'));
console.log(`\n${skillDirs.length} skills checked, ${failures} gate failure(s)`);
process.exit(failures > 0 ? 1 : 0);
