// Provider error classification — turns engine/LLM transport failures into a
// stable, user-meaningful category instead of an opaque blob.
//
// Motivation (measured 2026-10-22): OMP's provider rejected every chat turn
// with `Retry budget exhausted after 10 retries: 429 Budget has been exceeded
// … Current cost: 100.38, Max budget: 100.0`. The engine reported an assistant
// message with empty content and stopReason=error; nothing in the UI said
// "provider quota", so it looked like a platform bug.

const RULES = [
  // Quota first: the budget message also carries a 429, and "budget" is the
  // actionable fact (top up / switch key), not generic rate limiting.
  {
    code: 'provider_quota',
    label: 'provider 预算/配额已用尽',
    re: /budget\s+(?:has\s+been\s+exceeded|exceeded)|insufficient[_\s-]?quota|max\s+budget|credit\s+balance|余额不足|配额/i,
  },
  {
    code: 'provider_rate_limit',
    label: 'provider 限流（429）',
    re: /\b429\b|rate[_\s-]?limit|too many requests|retry budget exhausted/i,
  },
  {
    code: 'provider_auth',
    label: 'provider 鉴权失败（API key/权限）',
    re: /\b401\b|\b403\b|invalid[_\s-]?api[_\s-]?key|unauthorized|authentication/i,
  },
  {
    code: 'provider_unavailable',
    label: 'provider 暂时不可用',
    re: /\b5\d\d\b|overloaded|service\s+unavailable|econnreset|etimedout|handshake timeout/i,
  },
];

/**
 * Classify an error string. Returns `{ code, label, matched }` or null.
 * Pure and order-stable; safe to call on any engine error text.
 */
export function classifyProviderError(text) {
  const s = String(text || '');
  if (!s.trim()) return null;
  for (const rule of RULES) {
    const m = s.match(rule.re);
    if (m) return { code: rule.code, label: rule.label, matched: m[0].slice(0, 120) };
  }
  return null;
}

/** Prefix a failure message with its category so DB rows are queryable. */
export function tagProviderError(text) {
  const c = classifyProviderError(text);
  if (!c) return { text: String(text || ''), category: null };
  return { text: `[${c.code}] ${text}`, category: c };
}

const lastByHarness = new Map();

/** Record the most recent provider failure per harness (advisory health meta). */
export function recordProviderError(harness, text) {
  const c = classifyProviderError(text);
  if (!c) return null;
  const id = String(harness || '').trim().toLowerCase();
  lastByHarness.set(id, {
    ...c,
    harness: id,
    message: String(text || '').slice(0, 400),
    at: new Date().toISOString(),
  });
  return c;
}

export function getProviderError(harness) {
  return lastByHarness.get(String(harness || '').trim().toLowerCase()) || null;
}

/** Test hook. */
export function resetProviderErrors() {
  lastByHarness.clear();
}
