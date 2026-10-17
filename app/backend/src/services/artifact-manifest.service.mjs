// DOE artifact manifest reader — ONE source for the tasks API and the external API.
//
// Contract: docs/plans/contracts/artifact_manifest.schema.json (§4 of the DOE
// plan). The analyzer writes <run_dir>/artifact_manifest.json at the end of a
// run; when that file is absent (older runs, a crashed run, a non-DOE intent)
// this module rebuilds the same payload by probing the contract paths so callers
// never have to care which produced it.
import { createHash } from 'node:crypto';
import { existsSync, readFileSync, statSync } from 'node:fs';
import { isAbsolute, join } from 'node:path';

/** The contract §4 artifact inventory: [kind, run-dir-relative path]. */
export const DOE_ARTIFACTS = [
  ['ontology', '01_ontology/ontology.json'],
  ['ontology_brief', '01_ontology/ontology_brief.json'],
  ['ontology_coverage', '01_ontology/ontology_coverage.json'],
  ['ontology_feedback', '01_ontology/ontology_feedback.json'],
  ['ontology_consistency', '02_analysis/ontology_consistency.json'],
  ['data_profile', '01_profile/data_profile.json'],
  ['analysis_plan', '01_profile/analysis_plan.md'],
  ['effect_table', '02_analysis/effect_table.json'],
  ['model', '02_analysis/model.json'],
  ['association_screen', '02_analysis/association_screen.json'],
  ['doe_conclusion', 'conclusions/doe_conclusion.json'],
  ['recommendations', 'conclusions/recommendations.json'],
  ['next_design', 'conclusions/next_design.json'],
  ['optimization_guidance', 'conclusions/optimization_guidance.json'],
  ['report', 'report.html'],
];

function sha256File(abs) {
  const h = createHash('sha256');
  h.update(readFileSync(abs));
  return h.digest('hex');
}

function contractVersionOf(abs) {
  if (!abs.endsWith('.json')) return null;
  try {
    const doc = JSON.parse(readFileSync(abs, 'utf8'));
    return typeof doc?.contract_version === 'string' ? doc.contract_version : null;
  } catch {
    return null;
  }
}

/** Resolve a run directory recorded as absolute or repo-relative. */
export function resolveRunDir(projectRoot, recorded) {
  if (!recorded) return null;
  return isAbsolute(recorded) ? recorded : join(projectRoot, recorded);
}

/**
 * Build the artifact manifest for a run directory.
 *
 * @param {string} runDir absolute run directory
 * @returns {{contract_version:string, artifacts:Array, missing:Array, source:string}}
 */
export function buildArtifactManifest(runDir) {
  if (!runDir || !existsSync(runDir)) {
    return { contract_version: '1.1', artifacts: [], missing: [], source: 'absent' };
  }

  const own = join(runDir, 'artifact_manifest.json');
  if (existsSync(own)) {
    try {
      const doc = JSON.parse(readFileSync(own, 'utf8'));
      if (Array.isArray(doc?.artifacts)) return { ...doc, source: 'analyzer' };
    } catch {
      // fall through to probing: a corrupt manifest is rebuilt, never trusted
    }
  }

  const artifacts = [];
  const missing = [];
  for (const [kind, rel] of DOE_ARTIFACTS) {
    const abs = join(runDir, rel);
    if (existsSync(abs)) {
      const st = statSync(abs);
      artifacts.push({
        kind,
        path: rel.split('\\').join('/'),
        url: null,
        sha256: sha256File(abs),
        schema_version: contractVersionOf(abs),
        bytes: st.size,
        produced_by: 'backend-probe',
      });
    } else if (kind === 'report' || kind === 'analysis_plan') {
      // report.html and the agent-authored plan are conditional by design
      continue;
    } else {
      missing.push({ kind, reason: `expected artifact absent: ${rel}` });
    }
  }
  return {
    contract_version: '1.1',
    schema_version: '1.1',
    run_dir: runDir,
    artifacts,
    missing,
    source: 'probe',
  };
}
