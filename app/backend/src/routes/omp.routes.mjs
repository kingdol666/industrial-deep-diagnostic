// OMP Routes — REST bridge into native OMP harness outputs.
// Read-only: lists/reads workspace/diagnostic-runs artifacts produced by the
// OMP agent pipeline. The frontend selects this harness to browse runs that
// were executed by OMP (as opposed to the built-in Claude SDK engine).

import { Router } from 'express';
import logger from '../utils/logger.mjs';
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

// 生产错误面：500 级不把内部 message 泄给客户端（B4）；4xx 保持人话。
function failInternal(res, err, code) {
  logger.error(`[omp] ${err?.stack || err?.message || err}`, { context: 'OMP' });
  res.status(500).json({ success: false, code, error: 'OMP 服务内部错误，请查看后端日志后重试' });
}

/** GET /api/omp/health — OMP workspace availability */
router.get('/health', (req, res) => ok(res, ompHealth()));

// Run-scoped reads: the viewer (req.user) sees only their own runs (all for an
// admin; an unowned run dir is admin-only) — see services/tenancy.mjs.
function handle(res, fn, code) {
  try { return fn(); } catch (err) { return failInternal(res, err, code); }
}

/** GET /api/omp/runs — list all OMP pipeline runs (viewer-scoped) */
router.get('/runs', (req, res) => handle(res, () => ok(res, listOmpRuns(req.user)), 'OMP_LIST_FAILED'));

/** GET /api/omp/runs/:name — full run detail (manifest/status/events/artifacts) */
router.get('/runs/:name', (req, res) => handle(res, () => {
  const run = getOmpRun(req.params.name, req.user);
  if (!run) return fail(res, 404, `OMP run not found: ${req.params.name}`);
  return ok(res, run);
}, 'OMP_RUN_FAILED'));

/** GET /api/omp/runs/:name/summary — light enrichment for cards */
router.get('/runs/:name/summary', (req, res) => handle(res, () => {
  const summary = getOmpSummary(req.params.name, req.user);
  if (!summary) return fail(res, 404, `OMP run not found: ${req.params.name}`);
  return ok(res, summary);
}, 'OMP_SUMMARY_FAILED'));

/** GET /api/omp/runs/:name/artifact/:kind — baseline artifact content */
router.get('/runs/:name/artifact/:kind', (req, res) => handle(res, () => {
  const art = getOmpArtifact(req.params.name, req.params.kind, req.user);
  if (!art) return fail(res, 404, `Artifact '${req.params.kind}' not found in ${req.params.name}`);
  return ok(res, art);
}, 'OMP_ARTIFACT_FAILED'));

/** GET /api/omp/runs/:name/enhancement/:kind — enhancement artifact content */
router.get('/runs/:name/enhancement/:kind', (req, res) => handle(res, () => {
  const art = getOmpEnhancement(req.params.name, req.params.kind, req.user);
  if (!art) return fail(res, 404, `Enhancement artifact '${req.params.kind}' not found in ${req.params.name}`);
  return ok(res, art);
}, 'OMP_ENHANCEMENT_FAILED'));

/** GET /api/omp/runs/:name/html — raw HTML for iframe embedding */
router.get('/runs/:name/html', (req, res) => handle(res, () => {
  const art = getOmpArtifact(req.params.name, 'html', req.user);
  if (!art) return fail(res, 404, `HTML report not found in ${req.params.name}`);
  return res.type('html').send(art.content);
}, 'OMP_HTML_FAILED'));

/** GET /api/omp/runs/:name/enhancement/html — enhanced HTML for iframe */
router.get('/runs/:name/enhancement/html', (req, res) => handle(res, () => {
  const art = getOmpEnhancement(req.params.name, 'html', req.user);
  if (!art) return fail(res, 404, `Enhanced HTML not found in ${req.params.name}`);
  return res.type('html').send(art.content);
}, 'OMP_ENHANCED_HTML_FAILED'));

export default router;
