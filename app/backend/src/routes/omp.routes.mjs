// OMP Routes — REST bridge into native OMP harness outputs.
// Read-only: lists/reads workspace/diagnostic-runs artifacts produced by the
// OMP agent pipeline. The frontend selects this harness to browse runs that
// were executed by OMP (as opposed to the built-in Claude SDK engine).

import { Router } from 'express';
import {
  ompHealth,
  listOmpRuns,
  getOmpRun,
  getOmpArtifact,
  getOmpEnhancement,
  getOmpSummary,
} from '../services/omp.service.mjs';

const router = Router();

function ok(res, data) {
  res.json({ success: true, data });
}

function fail(res, status, message) {
  res.status(status).json({ success: false, error: message });
}

/** GET /api/omp/health — OMP workspace availability */
router.get('/health', (req, res) => ok(res, ompHealth()));

/** GET /api/omp/runs — list all OMP pipeline runs */
router.get('/runs', (req, res) => ok(res, listOmpRuns()));

/** GET /api/omp/runs/:name — full run detail (manifest/status/events/artifacts) */
router.get('/runs/:name', (req, res) => {
  const run = getOmpRun(req.params.name);
  if (!run) return fail(res, 404, `OMP run not found: ${req.params.name}`);
  ok(res, run);
});

/** GET /api/omp/runs/:name/summary — light enrichment for cards */
router.get('/runs/:name/summary', (req, res) => {
  const summary = getOmpSummary(req.params.name);
  if (!summary) return fail(res, 404, `OMP run not found: ${req.params.name}`);
  ok(res, summary);
});

/** GET /api/omp/runs/:name/artifact/:kind — baseline artifact content */
router.get('/runs/:name/artifact/:kind', (req, res) => {
  const art = getOmpArtifact(req.params.name, req.params.kind);
  if (!art) return fail(res, 404, `Artifact '${req.params.kind}' not found in ${req.params.name}`);
  ok(res, art);
});

/** GET /api/omp/runs/:name/enhancement/:kind — enhancement artifact content */
router.get('/runs/:name/enhancement/:kind', (req, res) => {
  const art = getOmpEnhancement(req.params.name, req.params.kind);
  if (!art) return fail(res, 404, `Enhancement artifact '${req.params.kind}' not found in ${req.params.name}`);
  ok(res, art);
});

/** GET /api/omp/runs/:name/html — raw HTML for iframe embedding */
router.get('/runs/:name/html', (req, res) => {
  const art = getOmpArtifact(req.params.name, 'html');
  if (!art) return fail(res, 404, `HTML report not found in ${req.params.name}`);
  res.type('html').send(art.content);
});

/** GET /api/omp/runs/:name/enhancement/html — enhanced HTML for iframe */
router.get('/runs/:name/enhancement/html', (req, res) => {
  const art = getOmpEnhancement(req.params.name, 'html');
  if (!art) return fail(res, 404, `Enhanced HTML not found in ${req.params.name}`);
  res.type('html').send(art.content);
});

export default router;
