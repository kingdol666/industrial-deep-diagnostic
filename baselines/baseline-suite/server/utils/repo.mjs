// repo.mjs — locate the IDD repository root and load ONLY truth-free inputs.
//
// Leakage contract (mirror of scripts/benchmark/check-leakage.mjs): this suite
// is a BASELINE system — it may read the blind briefs and the prepared data,
// never the truth fields of scripts/benchmark/cases/benchmark_cases.json. The
// case file is read exclusively to resolve {case_id, dataset, csv, control}
// routing facts; truth/keywords are stripped before any value leaves this
// module, and no code path below ever imports them.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const SUITE_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const REPO = path.resolve(SUITE_ROOT, '..', '..');

function exists(p) { try { fs.accessSync(p); return true; } catch { return false; } }

export function repoRoot() {
  if (!exists(path.join(REPO, 'scripts', 'benchmark'))) throw new Error('IDD repo root not found from suite');
  return REPO;
}

/** Truth-free routing facts per scenario. */
export function scenarioRouting() {
  const tier = JSON.parse(fs.readFileSync(path.join(REPO, 'scripts', 'benchmark', 'cases', 'benchmark_cases.json'), 'utf8'));
  return tier.cases.map((c) => ({ case_id: c.case_id, dataset: c.dataset, csv: c.csv, control: !!c.control }));
}

export function routingFor(caseId) {
  const hit = scenarioRouting().find((c) => c.case_id === caseId);
  if (!hit) throw new Error(`unknown scenario: ${caseId}`);
  return hit;
}

export function briefFor(caseId) {
  const p = path.join(REPO, 'results', 'benchmark', 'briefs', `${caseId}.brief.json`);
  return JSON.parse(fs.readFileSync(p, 'utf8'));
}

/** Public documented TEP cause list (Downs-Vogel / Chiang Table 10) — public knowledge, not truth. */
export function tepCauseTable() {
  return JSON.parse(fs.readFileSync(path.join(REPO, 'scripts', 'benchmark', 'cases', 'tep_cause_table.json'), 'utf8'));
}

export { SUITE_ROOT, REPO };
