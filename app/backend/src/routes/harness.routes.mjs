// Harness Routes — engine-agnostic REST layer.
//
// /api/harness            → GET list of available engines (manifests)
// /api/harness/:id/health → engine availability + meta
// /api/harness/:id/runs   → run listing (runs-capable engines)
// /api/harness/:id/runs/:run → run detail
// /api/harness/:id/runs/:run/summary → light enrichment
// /api/harness/:id/runs/:run/artifact/:kind → artifact content
// /api/harness/:id/runs/:run/enhancement/:kind → enhancement artifact
// /api/harness/:id/runs/:run/html?mode=baseline|enhanced → raw HTML
//
// Every endpoint delegates to the Harness interface — adding an engine to
// registry.mjs makes it appear here and in the frontend automatically.

import { Router } from 'express';
import { listHarnesses, getHarness } from '../harness/registry.mjs';
import { HarnessNotFoundError, HarnessNotSupportedError } from '../harness/base.mjs';

const router = Router();

function ok(res, data) {
  res.json({ success: true, data });
}

function fail(res, status, message) {
  res.status(status).json({ success: false, error: message });
}

function resolve(res, id) {
  try {
    return getHarness(id);
  } catch (e) {
    if (e instanceof HarnessNotFoundError) {
      fail(res, 404, e.message);
      return null;
    }
    fail(res, 500, e.message);
    return null;
  }
}

/** GET /api/harness — list all engines */
router.get('/', (req, res) => ok(res, listHarnesses()));

/** GET /api/harness/:id/health */
router.get('/:id/health', async (req, res) => {
  const h = resolve(res, req.params.id);
  if (!h) return;
  try {
    ok(res, await h.health());
  } catch (e) {
    fail(res, 500, e.message);
  }
});

/** GET /api/harness/:id/runs */
router.get('/:id/runs', async (req, res) => {
  const h = resolve(res, req.params.id);
  if (!h) return;
  try {
    ok(res, await h.listRuns());
  } catch (e) {
    if (e instanceof HarnessNotSupportedError) return fail(res, 400, e.message);
    fail(res, 500, e.message);
  }
});

/** GET /api/harness/:id/runs/:run */
router.get('/:id/runs/:run', async (req, res) => {
  const h = resolve(res, req.params.id);
  if (!h) return;
  try {
    const run = await h.getRun(req.params.run);
    if (!run) return fail(res, 404, `Run not found: ${req.params.run}`);
    ok(res, run);
  } catch (e) {
    fail(res, 500, e.message);
  }
});

/** GET /api/harness/:id/runs/:run/summary */
router.get('/:id/runs/:run/summary', async (req, res) => {
  const h = resolve(res, req.params.id);
  if (!h) return;
  try {
    if (typeof h.getSummary !== 'function') return ok(res, null);
    const s = await h.getSummary(req.params.run);
    if (s === null) return fail(res, 404, `Run not found: ${req.params.run}`);
    ok(res, s);
  } catch (e) {
    fail(res, 500, e.message);
  }
});

/** GET /api/harness/:id/runs/:run/artifact/:kind */
router.get('/:id/runs/:run/artifact/:kind', async (req, res) => {
  const h = resolve(res, req.params.id);
  if (!h) return;
  try {
    const art = await h.getArtifact(req.params.run, req.params.kind);
    if (!art) return fail(res, 404, `Artifact '${req.params.kind}' not found`);
    ok(res, art);
  } catch (e) {
    fail(res, 500, e.message);
  }
});

/** GET /api/harness/:id/runs/:run/enhancement/:kind */
router.get('/:id/runs/:run/enhancement/:kind', async (req, res) => {
  const h = resolve(res, req.params.id);
  if (!h) return;
  try {
    const art = await h.getEnhancement(req.params.run, req.params.kind);
    if (!art) return fail(res, 404, `Enhancement artifact '${req.params.kind}' not found`);
    ok(res, art);
  } catch (e) {
    fail(res, 500, e.message);
  }
});

/** GET /api/harness/:id/runs/:run/html?mode=baseline|enhanced */
router.get('/:id/runs/:run/html', async (req, res) => {
  const h = resolve(res, req.params.id);
  if (!h) return;
  try {
    const html = await h.getHtml(req.params.run, req.query.mode || 'baseline');
    if (!html) return fail(res, 404, 'HTML report not found');
    res.type('html').send(html);
  } catch (e) {
    fail(res, 500, e.message);
  }
});

export default router;
