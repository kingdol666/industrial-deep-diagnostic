#!/usr/bin/env node
// check-doc-numbers.mjs — documentation-truth guard (zero dependencies).
//
// 文档数字守卫：从仓库现实计算事实，再逐条比对「可信文档」里的数字断言。
// 任何不一致 → 打印 file:line → exit 1；全部一致 → exit 0。
//
// Facts computed from reality (never hardcoded):
//   skills   — directories under .claude/skills/ that contain SKILL.md
//   agents   — *.md files under .omp/agents/
//   hdDefs   — entries of HARNESS_DEFS (app/backend/src/harness/engines.mjs)
//   engines  — hdDefs + harness classes registered in harness/registry.mjs
//              (claude/omp are registered there; demo-harness is opt-in, not counted)
//   cliVerbs — verbs accepted by commands/cli.mjs (parsed from its router switch)
//   cliFlags — service/flag surface accepted by commands/cli.mjs
//
// Checks:
//   1. skill / agent / engine counts claimed in the docs match the computed facts
//      (README.md, README-zh.md, CLAUDE.md, AGENTS.md, docs/architecture/system-overview.md,
//       plus the HARNESS_DEFS/registry header comments in the backend source)
//   2. every skill and every agent is named in README.md and README-zh.md (the
//      "all skills / all agents" tables must stay complete)
//   3. AGENTS.md / CLAUDE.md document only `ind-diag` verbs + flags that
//      commands/cli.mjs actually accepts
//   4. the three retired shared-script names (stats.mjs / stats_validate.mjs /
//      artifact-check.mjs) neither exist as files nor appear as live scripts in
//      the docs (a line that says "retired" is allowed — historical mention)
//   5. no stale hardcoded backend-test count (116) remains in the docs —
//      the real count lives in CI output, not in prose
//
// Usage: node scripts/check-doc-numbers.mjs
// Exit:  0 = clean, 1 = mismatch(es), 2 = cannot compute facts (repo broken)

import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(import.meta.dirname, '..');
const problems = [];
const guardDocs = ['README.md', 'README-zh.md', 'CLAUDE.md', 'AGENTS.md', 'docs/architecture/system-overview.md'];
const fileCache = new Map();

function read(rel) {
  if (!fileCache.has(rel)) fileCache.set(rel, fs.readFileSync(path.join(ROOT, rel), 'utf8'));
  return fileCache.get(rel);
}
function docLines(rel) { return read(rel).split(/\r?\n/); }
function fail(msg) { problems.push(msg); }

// ─────────────────────── facts ───────────────────────

const SKILLS_DIR = path.join(ROOT, '.claude', 'skills');
if (!fs.existsSync(SKILLS_DIR)) { console.error('FATAL: .claude/skills missing'); process.exit(2); }
const skills = fs.readdirSync(SKILLS_DIR, { withFileTypes: true })
  .filter((d) => d.isDirectory() && fs.existsSync(path.join(SKILLS_DIR, d.name, 'SKILL.md')))
  .map((d) => d.name).sort();
const SKILL_COUNT = skills.length;

const AGENTS_DIR = path.join(ROOT, '.omp', 'agents');
if (!fs.existsSync(AGENTS_DIR)) { console.error('FATAL: .omp/agents missing'); process.exit(2); }
const agents = fs.readdirSync(AGENTS_DIR).filter((f) => f.endsWith('.md')).map((f) => f.replace(/\.md$/, '')).sort();
const AGENT_COUNT = agents.length;

const ENGINES_REL = 'app/backend/src/harness/engines.mjs';
const REGISTRY_REL = 'app/backend/src/harness/registry.mjs';
const enginesSrc = read(ENGINES_REL);
const hdBlock = enginesSrc.match(/export const HARNESS_DEFS = \[([\s\S]*?)\n\];/);
if (!hdBlock) { console.error(`FATAL: cannot locate HARNESS_DEFS block in ${ENGINES_REL}`); process.exit(2); }
const HARNESS_DEF_COUNT = (hdBlock[1].match(/^\s{2,}id:\s*'[a-z0-9-]+',/gm) || []).length;
if (HARNESS_DEF_COUNT === 0) { console.error(`FATAL: HARNESS_DEFS parsed as 0 entries (${ENGINES_REL})`); process.exit(2); }

const registrySrc = read(REGISTRY_REL);
const harnessArr = registrySrc.match(/const harnesses = \[([^\]]*)\];/);
if (!harnessArr) { console.error(`FATAL: cannot locate harnesses array in ${REGISTRY_REL}`); process.exit(2); }
const registryHarnesses = [...harnessArr[1].matchAll(/new\s+(\w+Harness)\(\)/g)].map((m) => m[1]);
const ENGINE_COUNT = HARNESS_DEF_COUNT + registryHarnesses.length;

const CLI_REL = 'commands/cli.mjs';
const cliSrc = read(CLI_REL);
const cliVerbs = new Set([...cliSrc.matchAll(/case '([a-z][a-z-]*)':/g)].map((m) => m[1]));
if (cliVerbs.size === 0) { console.error(`FATAL: cannot parse CLI verbs from ${CLI_REL}`); process.exit(2); }
const cliVerbsList = [...cliVerbs].join(', ');
const allServicesM = cliSrc.match(/const ALL_SERVICES = \[([^\]]*)\]/);
const cliFlags = new Set(['--all', '--detach']);
if (allServicesM) for (const m of allServicesM[1].matchAll(/'([a-z]+)'/g)) cliFlags.add(`--${m[1]}`);
const cliFlagsList = [...cliFlags].join(', ');

// ─────────────── count-claim scanning ───────────────
// Every occurrence of these phrases in the guarded docs must carry the real number.

const COUNT_CLAIMS = [
  // English skill claims
  { label: 'skill count', re: /(\d+)\s*standardized skills\b/g, expected: SKILL_COUNT, what: 'skills' },
  { label: 'skill count', re: /(\d+)\s*skill implementations?\b/g, expected: SKILL_COUNT, what: 'skills' },
  { label: 'skill count', re: /\((\d+) skills\)/g, expected: SKILL_COUNT, what: 'skills' },
  // English agent claims
  { label: 'agent count', re: /(\d+)\s*dedicated agents\b/g, expected: AGENT_COUNT, what: 'agents' },
  { label: 'agent count', re: /(\d+)\s*OMP agent definitions\b/g, expected: AGENT_COUNT, what: 'agents' },
  { label: 'agent count', re: /\((\d+) agents\)/g, expected: AGENT_COUNT, what: 'agents' },
  // Chinese claims
  { label: '技能数', re: /(\d+)\s*个标准化技能/g, expected: SKILL_COUNT, what: 'skills' },
  { label: '技能数', re: /(\d+)\s*个技能实现/g, expected: SKILL_COUNT, what: 'skills' },
  { label: '智能体数', re: /(\d+)\s*个专职智能体/g, expected: AGENT_COUNT, what: 'agents' },
  { label: '智能体数', re: /(\d+)\s*个\s*OMP\s*智能体定义/g, expected: AGENT_COUNT, what: 'agents' },
  // Engine total claims (docs)
  { label: 'engine count', re: /Engines-(\d+)/g, expected: ENGINE_COUNT, what: 'engines' },
  { label: 'engine count', re: /^### Multi-Harness Execution Engines \((\d+) engines\)$/gm, expected: ENGINE_COUNT, what: 'engines' },
  { label: 'engine count', re: /(?<![\w/])(\d+)-engine\b/g, expected: ENGINE_COUNT, what: 'engines' },
  { label: 'engine count', re: /(\d+) selectable engines\b/g, expected: ENGINE_COUNT, what: 'engines' },
  { label: 'engine count', re: /(\d+) harnesses\b/g, expected: ENGINE_COUNT, what: 'engines' },
  { label: 'engine count', re: /(\d+) execution engines\b/g, expected: ENGINE_COUNT, what: 'engines' },
  { label: 'engine count', re: /\((\d+) engines\)/g, expected: ENGINE_COUNT, what: 'engines' },
  { label: '引擎数', re: /(\d+) 个执行引擎/g, expected: ENGINE_COUNT, what: 'engines' },
  { label: '引擎数', re: /(\d+) 引擎任选/g, expected: ENGINE_COUNT, what: 'engines' },
  { label: '引擎数', re: /(\d+) 个 Harness/g, expected: ENGINE_COUNT, what: 'engines' },
  { label: '引擎数', re: /注册表（(\d+) 个）/g, expected: ENGINE_COUNT, what: 'engines' },
  // HARNESS_DEFS table size — README / README-zh backend tree
  { label: 'HARNESS_DEFS size', re: /HARNESS_DEFS: (\d+) engines \+ claude\/omp in registry = (\d+)/g, expected: [HARNESS_DEF_COUNT, ENGINE_COUNT], what: 'htable' },
  { label: 'HARNESS_DEFS 表大小', re: /HARNESS_DEFS：(\d+) 个引擎 \+ registry 中 claude\/omp = (\d+)/g, expected: [HARNESS_DEF_COUNT, ENGINE_COUNT], what: 'htable' },
];

const REQUIRED_SITES = [
  // Canonical claim sites — they must exist (so nobody silently deletes the claim
  // instead of fixing it). The numbers themselves are checked by COUNT_CLAIMS.
  { doc: 'README.md', re: /\*\*\d+ standardized skills × \d+ dedicated agents\*\*/ },
  { doc: 'README.md', re: /^### \d+ standardized skills$/m },
  { doc: 'README.md', re: /^### \d+ dedicated agents$/m },
  { doc: 'README.md', re: /# \d+ skill implementations \(single source\)/ },
  { doc: 'README.md', re: /# \d+ OMP agent definitions/ },
  { doc: 'README.md', re: /HARNESS_DEFS: \d+ engines \+ claude\/omp in registry = \d+/ },
  { doc: 'README-zh.md', re: /个标准化技能 × \d+ 个专职智能体/ },
  { doc: 'README-zh.md', re: /^### \d+ 个标准化技能$/m },
  { doc: 'README-zh.md', re: /^### \d+ 个专职智能体$/m },
  { doc: 'README-zh.md', re: /# \d+ 个技能实现（唯一技能源）/ },
  { doc: 'README-zh.md', re: /# \d+ 个 OMP 智能体定义/ },
  { doc: 'README-zh.md', re: /HARNESS_DEFS：\d+ 个引擎 \+ registry 中 claude\/omp = \d+/ },
  { doc: 'CLAUDE.md', re: /\d+ standardized skills .* × \d+ dedicated agents/ },
  { doc: 'AGENTS.md', re: /\d+ standardized skills .* × \d+ dedicated agents/ },
  { doc: 'AGENTS.md', re: /^### Multi-Harness Execution Engines \(\d+ engines\)$/m },
  { doc: 'AGENTS.md', re: /^### Skill System \(\d+ skills\)$/m },
  { doc: 'AGENTS.md', re: /^### Agent Roles \(\d+ agents\)$/m },
  { doc: 'docs/architecture/system-overview.md', re: /个 skill，唯一权威源/ },
];
for (const site of REQUIRED_SITES) {
  if (!site.re.test(read(site.doc))) {
    fail(`${site.doc}: required claim site missing — expected a line matching /${site.re.source}/`);
  }
}

for (const doc of guardDocs) {
  docLines(doc).forEach((text, i) => {
    for (const c of COUNT_CLAIMS) {
      const re = new RegExp(c.re.source, c.re.flags);
      let m;
      while ((m = re.exec(text))) {
        const got = m.slice(1).map(Number);
        const want = Array.isArray(c.expected) ? c.expected : [c.expected];
        for (let g = 0; g < got.length; g++) {
          if (got[g] !== want[g]) {
            const what = c.what === 'skills' ? 'skills' : c.what === 'agents' ? 'agents' : 'engines';
            fail(`${doc}:${i + 1}: ${c.label} says ${got[g]} but reality is ${want[g]} (${what})\n    ${text.trim()}`);
          }
        }
        if (m[0] === '') break;
      }
    }
  });
}

// Source-header claims (backend harness layer must describe itself truthfully)
{
  const m = enginesSrc.match(/HARNESS_DEFS — the (\d+)-engine definition table/);
  if (!m) fail(`${ENGINES_REL}: expected comment "HARNESS_DEFS — the <N>-engine definition table" not found`);
  else if (Number(m[1]) !== HARNESS_DEF_COUNT) fail(`${ENGINES_REL}: header comment says ${m[1]}-engine table but HARNESS_DEFS has ${HARNESS_DEF_COUNT} entries`);

  const r1 = registrySrc.match(/The (\d+) definition-table engines/);
  if (!r1) fail(`${REGISTRY_REL}: expected comment "The <N> definition-table engines" not found`);
  else if (Number(r1[1]) !== HARNESS_DEF_COUNT) fail(`${REGISTRY_REL}: comment says ${r1[1]} definition-table engines but HARNESS_DEFS has ${HARNESS_DEF_COUNT}`);

  const r2 = registrySrc.match(/(\d+) engines from the multi-harness architecture/);
  if (!r2) fail(`${REGISTRY_REL}: expected comment "<N> engines from the multi-harness architecture" not found`);
  else if (Number(r2[1]) !== ENGINE_COUNT) fail(`${REGISTRY_REL}: comment says ${r2[1]} registered engines but registry holds ${ENGINE_COUNT}`);
}

// ─────────── completeness: all skills & agents named in README tables ───────────

for (const doc of ['README.md', 'README-zh.md']) {
  const text = read(doc);
  const missingSkills = skills.filter((s) => !text.includes(`\`${s}\``));
  const missingAgents = agents.filter((a) => !text.includes(`\`${a}\``));
  if (missingSkills.length) fail(`${doc}: ${missingSkills.length} skill(s) not listed in the skill table: ${missingSkills.join(', ')} (must list all ${SKILL_COUNT})`);
  if (missingAgents.length) fail(`${doc}: ${missingAgents.length} agent(s) not listed in the agent table: ${missingAgents.join(', ')} (must list all ${AGENT_COUNT})`);
}

// ─────────── CLI verbs: docs must not document commands the CLI rejects ───────────

for (const doc of ['AGENTS.md', 'CLAUDE.md']) {
  docLines(doc).forEach((text, i) => {
    for (const m of text.matchAll(/\bind-diag\s+([A-Za-z][A-Za-z0-9-]*)/g)) {
      const verb = m[1];
      if (!cliVerbs.has(verb)) {
        fail(`${doc}:${i + 1}: documents "ind-diag ${verb}" but commands/cli.mjs accepts only: ${cliVerbsList}\n    ${text.trim()}`);
      }
    }
    const verbM = text.match(/\bind-diag\s+([a-z][a-z-]*)((?:\s+--[a-z-]+)*)/);
    if (verbM) {
      for (const f of (verbM[2].match(/--[a-z-]+/g) || [])) {
        if (!cliFlags.has(f)) fail(`${doc}:${i + 1}: unknown flag "${f}" for ind-diag (accepted: ${cliFlagsList})\n    ${text.trim()}`);
      }
    }
  });
}

// ─────────── retired scripts: names must be gone, or explicitly historical ───────────

const RETIRED = ['stats.mjs', 'stats_validate.mjs', 'artifact-check.mjs'];
function walkFiles(dir) {
  const out = [];
  if (!fs.existsSync(dir)) return out;
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const abs = path.join(dir, e.name);
    if (e.isDirectory()) { if (e.name !== '__pycache__') out.push(...walkFiles(abs)); }
    else out.push(abs);
  }
  return out;
}
const liveTrees = [path.join(ROOT, '.claude', 'shared', 'scripts'), path.join(ROOT, '.claude', 'skills')];
for (const name of RETIRED) {
  for (const tree of liveTrees) {
    for (const abs of walkFiles(tree)) {
      if (path.basename(abs) === name) {
        fail(`${path.relative(ROOT, abs)}: retired script exists again — remove it or restore the doc claims`);
      }
    }
  }
  for (const doc of guardDocs) {
    docLines(doc).forEach((text, i) => {
      if (text.includes(name) && !/retired|退役/i.test(text)) {
        fail(`${doc}:${i + 1}: references non-existent script "${name}" as if it were live (no such file under .claude/shared/scripts or .claude/skills)\n    ${text.trim()}`);
      }
    });
  }
}

// ─────────── stale hardcoded test counts must not exist anywhere in the docs ───────────

for (const doc of guardDocs) {
  docLines(doc).forEach((text, i) => {
    if (/\b116\b/.test(text)) {
      fail(`${doc}:${i + 1}: stale hardcoded test count "116" — the real count is printed by CI, not written in docs\n    ${text.trim()}`);
    }
    if (/\b45 cases\b/.test(text)) {
      fail(`${doc}:${i + 1}: stale hardcoded test count "45 cases" — drop the number or point at CI\n    ${text.trim()}`);
    }
  });
}

// ─────────────────────── report ───────────────────────

console.log('check-doc-numbers — documentation truth guard');
console.log(`  facts: ${SKILL_COUNT} skills · ${AGENT_COUNT} agents · ${HARNESS_DEF_COUNT} HARNESS_DEFS + ${registryHarnesses.length} registry (${registryHarnesses.join('/')}) = ${ENGINE_COUNT} engines`);
console.log(`  CLI verbs: ${cliVerbsList}`);
console.log(`  guarded docs: ${guardDocs.join(', ')}`);

if (problems.length) {
  console.error(`\nFAIL — ${problems.length} mismatch(es):\n`);
  for (const p of problems) console.error(`  ✗ ${p}\n`);
  process.exit(1);
}
console.log('\nOK — every count / command / script claim in the guarded docs matches reality.');
process.exit(0);
