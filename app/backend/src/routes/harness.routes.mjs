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
//
// NOTE: artifact/enhancement endpoints return 200 + null (not 404) when the
// run exists but lacks the specific file. The frontend fetches these
// proactively on every run open, so 404s created browser console noise.

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
    if (e instanceof HarnessNotSupportedError) return fail(res, 400, e.message);
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

/** GET /api/harness/:id/runs/:run/artifact/:kind
 *  Returns 200 + null when the run exists but the artifact file is absent
 *  (frontend probes proactively; 404 would create console noise). */
router.get('/:id/runs/:run/artifact/:kind', async (req, res) => {
  const h = resolve(res, req.params.id);
  if (!h) return;
  try {
    const art = await h.getArtifact(req.params.run, req.params.kind);
    ok(res, art || null);
  } catch (e) {
    if (e instanceof HarnessNotSupportedError) return fail(res, 400, e.message);
    fail(res, 500, e.message);
  }
});

/** GET /api/harness/:id/runs/:run/enhancement/:kind
 *  Returns 200 + null when the run exists but the enhancement file is absent. */
router.get('/:id/runs/:run/enhancement/:kind', async (req, res) => {
  const h = resolve(res, req.params.id);
  if (!h) return;
  try {
    const art = await h.getEnhancement(req.params.run, req.params.kind);
    ok(res, art || null);
  } catch (e) {
    if (e instanceof HarnessNotSupportedError) return fail(res, 400, e.message);
    fail(res, 500, e.message);
  }
});

/**
 * Rewrite relative asset URLs (src/href) in an HTML document so they resolve
 * against the workspace asset endpoint. Without this, images inside the
 * diagnostic-report.html (e.g. `03_figures/fig_xxx.png`) would 404 because the
 * iframe base URL is the harness html route, which has no static-file handler.
 */
function rewriteHtmlAssetUrls(html, runName) {
  if (!html || !runName) return html;
  const assetBase = `/api/files/workspace/asset/${encodeURIComponent(runName)}/`;
  // Rewrite src="..." and href="..." that are relative (not absolute/data/protocol).
  return html.replace(/\b(src|href)\s*=\s*"([^"]+)"/g, (match, attr, url) => {
    if (/^(?:[a-z]+:|\/\/|\/|data:|#)/i.test(url)) return match; // absolute, protocol-relative, root, data, hash
    return `${attr}="${assetBase}${url}"`;
  });
}

/** GET /api/harness/:id/runs/:run/html?mode=baseline|enhanced */
router.get('/:id/runs/:run/html', async (req, res) => {
  const h = resolve(res, req.params.id);
  if (!h) return;
  try {
    const html = await h.getHtml(req.params.run, req.query.mode || 'baseline');
    if (!html) return fail(res, 404, 'HTML report not found');
    res.type('html').send(rewriteHtmlAssetUrls(html, req.params.run));
  } catch (e) {
    if (e instanceof HarnessNotSupportedError) return fail(res, 400, e.message);
    fail(res, 500, e.message);
  }
});

export default router;
