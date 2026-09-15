// Workspace-asset URL rewriting for HTML documents served to a browser.
//
// A generated report (`diagnostic-report.html`) references its figures with
// paths that are relative to the run directory — `<img src="03_figures/x.png">`.
// The document is served from a route that has no static-file handler of its
// own, so those relative URLs must be rewritten to the workspace asset
// endpoint before the HTML reaches the browser, otherwise every figure 404s.
//
// The rewritten URLs are then fetched by `<img>` / `<link>` tags, and a browser
// cannot attach an `Authorization` header to those. The global auth guard would
// therefore answer 401 and the report would render with all of its charts
// missing. Carrying the caller's own token through as a query parameter fixes
// that, reusing the `?token=` fallback the auth layer already sanctions for
// header-less callers (SSE / EventSource).

/** Build the public URL for an asset inside a run directory. */
export function assetUrlFor(runName, path, token) {
  const base = `/api/files/workspace/asset/${encodeURIComponent(runName)}/${path}`;
  return token ? `${base}${base.includes('?') ? '&' : '?'}token=${encodeURIComponent(token)}` : base;
}

/**
 * Rewrite every relative `src` / `href` in an HTML string to an absolute
 * workspace-asset URL, carrying `token` so header-less sub-resource requests
 * authenticate.
 *
 * Absolute URLs, protocol-relative URLs, root-relative paths, `data:` URIs and
 * bare fragments are left untouched — they already resolve, or are not ours.
 */
export function rewriteHtmlAssetUrls(html, runName, token) {
  if (!html || !runName) return html;
  const assetBase = `/api/files/workspace/asset/${encodeURIComponent(runName)}/`;
  const suffix = token ? `?token=${encodeURIComponent(token)}` : '';
  return html.replace(/\b(src|href)\s*=\s*"([^"]+)"/g, (match, attr, url) => {
    if (/^(?:[a-z]+:|\/\/|\/|data:|#)/i.test(url)) return match;
    return `${attr}="${assetBase}${url}${suffix}"`;
  });
}

/** Pull the caller's raw token off the request (Bearer header or `?token=`). */
export function callerToken(req) {
  const header = req.headers?.authorization;
  if (header && /^Bearer\s+/i.test(header)) return header.replace(/^Bearer\s+/i, '').trim();
  if (req.query?.token) return String(req.query.token).trim();
  return null;
}

/** True when the asset should be treated as a rewritable HTML document. */
export function isHtmlContentType(contentType) {
  return typeof contentType === 'string' && contentType.includes('text/html');
}
