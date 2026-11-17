// CORS policy — explicit allowlist instead of the reflect-everything default.
//
// Before: app.use(cors())  → Access-Control-Allow-Origin: * for every caller.
// After:  only configured origins receive CORS headers. A non-listed browser
//         origin still reaches the API (CORS is a browser-side gate, the
//         middleware never blocks), but the response is unreadable to it.
//         Requests without an Origin header (curl, probes, server-to-server,
//         same-origin navigations) always pass untouched.
//
// Allowlist resolution: CORS_ORIGINS env (comma-separated) wins over
// config.server.cors_origins so production operators can pin origins without
// editing YAML.

/** Resolve the effective allowlist → string[] of origins. */
export function resolveAllowedOrigins({ env = process.env, config } = {}) {
  const raw = typeof env?.CORS_ORIGINS === 'string' ? env.CORS_ORIGINS.trim() : '';
  if (raw) {
    return raw.split(',').map((s) => s.trim()).filter(Boolean);
  }
  const configured = config?.server?.cors_origins;
  if (!Array.isArray(configured)) return [];
  return configured
    .filter((origin) => typeof origin === 'string' && origin.trim())
    .map((origin) => origin.trim());
}

/** Options object for the `cors` package. */
export function buildCorsOptions({ env = process.env, config } = {}) {
  const allowed = new Set(resolveAllowedOrigins({ env, config }));
  return {
    origin(origin, callback) {
      // No Origin header → not a cross-origin browser request.
      if (!origin) return callback(null, true);
      return callback(null, allowed.has(origin));
    },
  };
}
