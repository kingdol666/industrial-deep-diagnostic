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

/** Analysis intents whose result contract is the DOE artifact inventory. */
export const DOE_ARTIFACT_INTENTS = new Set(['doe-analysis']);

// Specialist artifact inventories (plan v2 Phase C2). Without these, a
// stability/quick-screen result reported applicable:false and its JSON/MD
// products were only findable by listing the directory by hand.
export const STABILITY_ARTIFACTS = [
  ['ontology', '01_ontology/ontology.json'],
  ['ontology_brief', '01_ontology/ontology_brief.json'],
  ['ontology_coverage', '01_ontology/ontology_coverage.json'],
  ['stability_report', 'line_report/stability_report.json'],
  ['stability_charts', 'line_report/charts.json'],
  ['stability_html', 'line_report/line_stability_report.html'],
  ['stability_md', 'line_report/line_stability_report.md'],
  ['report', 'report.md'],
];

export const SENTINEL_ARTIFACTS = [
  ['ontology', '01_ontology/ontology.json'],
  ['ontology_brief', '01_ontology/ontology_brief.json'],
  ['ontology_coverage', '01_ontology/ontology_coverage.json'],
  ['alert', 'sentinel/alert.json'],
  ['watch_report', 'sentinel/watch_report.md'],
  ['quick_screen_html', 'sentinel/quick_screen_report.html'],
  ['baseline', 'watch_baseline.json'],
  ['report', 'report.md'],
];

const SPECIALIST_INVENTORIES = {
  'stability-report': { items: STABILITY_ARTIFACTS, required: new Set(['stability_report', 'stability_html', 'stability_md']) },
  'quick-screen': { items: SENTINEL_ARTIFACTS, required: new Set(['alert', 'watch_report', 'quick_screen_html']) },
};

// Conditional-by-design artifacts: absent is not a failure.
const CONDITIONAL_KINDS = new Set(['report', 'analysis_plan', 'ontology_brief', 'ontology_coverage', 'baseline',
  'ontology', 'stability_charts']);

/**
 * Build the artifact manifest for a run directory.
 *
 * @param {string} runDir absolute run directory
 * @param {{analysisIntent?: string|null}} [options]
 *   The manifest is a DOE contract. For any other analysis intent the
 *   inventory is not applicable: returning 13 "missing DOE artifacts" on a
 *   quick-screen/stability result would be a false failure signal. Callers
 *   that omit the intent (legacy tests / direct service use) keep the DOE
 *   behaviour.
 * @returns {{contract_version:string, artifacts:Array, missing:Array, source:string,
 *            applicable:boolean, analysis_intent:string|null}}
 */
export function buildArtifactManifest(runDir, { analysisIntent = null } = {}) {
  const specialist = SPECIALIST_INVENTORIES[analysisIntent];
  const applicable = !analysisIntent || DOE_ARTIFACT_INTENTS.has(analysisIntent) || !!specialist;
  if (!applicable) {
    return {
      contract_version: '1.1',
      schema_version: '1.1',
      run_dir: runDir || null,
      analysis_intent: analysisIntent,
      applicable: false,
      artifacts: [],
      missing: [],
      source: 'not-applicable',
      note: `No artifact inventory is defined for analysisIntent=${analysisIntent}`,
    };
  }
  if (!runDir || !existsSync(runDir)) {
    return {
      contract_version: '1.1', schema_version: '1.1', run_dir: runDir || null,
      analysis_intent: analysisIntent, applicable: true,
      artifacts: [], missing: [], source: 'absent',
    };
  }

  const own = join(runDir, 'artifact_manifest.json');
  if (!specialist && existsSync(own)) {
    try {
      const doc = JSON.parse(readFileSync(own, 'utf8'));
      if (Array.isArray(doc?.artifacts)) {
        return {
          ...doc, analysis_intent: analysisIntent, applicable: true,
          source: 'analyzer',
        };
      }
    } catch {
      // fall through to probing: a corrupt manifest is rebuilt, never trusted
    }
  }

  const inventory = specialist ? specialist.items : DOE_ARTIFACTS;
  const required = specialist ? specialist.required : null;
  const artifacts = [];
  const missing = [];
  for (const [kind, rel] of inventory) {
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
    } else if (CONDITIONAL_KINDS.has(kind)) {
      // report.html / agent-authored plan / optional JSON sidecars are
      // conditional by design.
      if (required && required.has(kind)) {
        missing.push({ kind, reason: `required artifact absent: ${rel}` });
      }
      continue;
    } else {
      missing.push({ kind, reason: `expected artifact absent: ${rel}` });
    }
  }
  return {
    contract_version: '1.1',
    schema_version: '1.1',
    run_dir: runDir,
    analysis_intent: analysisIntent,
    applicable: true,
    artifacts,
    missing,
    source: 'probe',
  };
}
