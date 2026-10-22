// Ontology directive contract — pure guard, no DB/engine imports.
//
// The diagnosis pipeline, the DOE profile and the watch-family profiles
// (stability-report / quick-screen) define ontology directives. The remaining
// specialist intents do not. Accepting their ontology fields and then
// ignoring them is a contract trap, so the API rejects the fields explicitly.
// `ontologyDataStage` / `ontologyDevOverride` are consumed by doe-analysis
// only (documented in docs/api.md — the guard accepts them for watch intents
// but the watch directive builders ignore them).
export const ONTOLOGY_FIELDS = [
  'ontologyMode', 'ontologyScene', 'ontologySource',
  'ontologyDataStage', 'ontologyDevOverride',
];

/** Analysis intents that actually consume ontology directives. */
export const ONTOLOGY_INTENTS = new Set(['deep-diagnosis', 'doe-analysis', 'stability-report', 'quick-screen']);

export function assertOntologyIntentSupported(analysisIntent, params = {}) {
  const hasOntologyFields = ONTOLOGY_FIELDS.some((key) =>
    params[key] !== undefined && params[key] !== null && params[key] !== '');
  if (hasOntologyFields && !ONTOLOGY_INTENTS.has(analysisIntent)) {
    const err = new Error(
      `Ontology parameters are not supported for analysisIntent=${analysisIntent}. ` +
      'Supported intents: deep-diagnosis, doe-analysis, stability-report, quick-screen.',
    );
    err.status = 400;
    err.code = 'ONTOLOGY_UNSUPPORTED_INTENT';
    throw err;
  }
}
