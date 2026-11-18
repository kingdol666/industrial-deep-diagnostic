// PathGuard — the single choke point for turning user-supplied path fragments
// (route params, query params, upload filenames, JSON body fields) into
// filesystem paths that provably stay inside a base directory.
//
// A raw `join(base, input).startsWith(base)` check is NOT containment:
//   - sibling-prefix attack — base `/a/data`, input `../data-evil/x` joins to
//     `/a/data-evil/x`, which still string-starts-with `/a/data`;
//   - encoded traversal — `%2e%2e%2f` / `%252e%252e%252f` reach the join either
//     already decoded (Express decodes params) or get decoded further downstream
//     (browser/proxy/framework layers), so both raw and decoded forms must be
//     treated as hostile;
//   - absolute inputs — `join()` silently rebases some of them, `resolve()` does not.
//
// Everything that joins user input into a path must call resolveInside().

import { basename, isAbsolute, relative, resolve } from 'path';

const MAX_FILE_NAME_LENGTH = 200;
const FORBIDDEN_FILE_NAME_CHARS = /[<>:"|?*\x00-\x1f]/g;

// Reserved Windows device names (case-insensitive, with or without extension):
// `NUL` / `nul.txt` open the device, not a file; `CON`/`COM1`/`LPT1` behave the
// same. A component's device stem is everything before its FIRST dot.
const WINDOWS_DEVICE_NAMES = new Set([
  'CON', 'PRN', 'AUX', 'NUL',
  ...Array.from({ length: 9 }, (_, i) => `COM${i + 1}`),
  ...Array.from({ length: 9 }, (_, i) => `LPT${i + 1}`),
]);

/** Split a path fragment into components on either separator. */
function segmentsOf(form) {
  return form.split(/[\\/]+/);
}

/** Raised when user-supplied input would leave its allowed base directory. */
export class PathViolationError extends Error {
  constructor(message, { code = 'PATH_OUTSIDE_BASE' } = {}) {
    super(message);
    this.name = 'PathViolationError';
    this.status = 400;
    this.code = code;
  }
}

/**
 * Percent-decode up to `passes` times. A single decode is not enough: a
 * double-encoded `%252e%252e%252f` only becomes `../` after two passes, and a
 * malformed escape must not mask the checks that already ran on the raw form.
 */
function decodeRepeatedly(value, passes = 2) {
  let out = value;
  for (let i = 0; i < passes; i += 1) {
    try {
      const next = decodeURIComponent(out);
      if (next === out) break;
      out = next;
    } catch {
      break;
    }
  }
  return out;
}

/** Reject absolute paths, drive-relative paths and `..` segments in one form of the input. */
function assertSafeForm(form, label) {
  if (form.includes('\0')) {
    throw new PathViolationError(`Invalid ${label}: null byte in path`);
  }
  // Windows drive-relative paths (`C:foo`) escape the base once resolved against
  // the CWD of that drive, and path.isAbsolute() reports false for them.
  if (isAbsolute(form) || /^[a-zA-Z]:/.test(form)) {
    throw new PathViolationError(`Invalid ${label}: absolute paths are not allowed`);
  }
  const segments = segmentsOf(form);
  if (segments.some((segment) => segment === '..')) {
    throw new PathViolationError(`Invalid ${label}: parent directory traversal is not allowed`);
  }
  for (const segment of segments) {
    // `.` (and the already-rejected `..`) denote the directory itself, never a
    // name Windows could mangle.
    if (segment === '' || segment === '.' || segment === '..') continue;
    // win32 strips a trailing dot or space from every component BEFORE opening
    // it, so `.. ` / `evil.` silently become `..` / `evil` — a lexically clean
    // string must not be trusted for either. They cannot name a real file.
    if (/[. ]$/.test(segment)) {
      throw new PathViolationError(`Invalid ${label}: a path component ends with a dot or space (Windows strips it)`);
    }
    // `:` addresses an NTFS alternate data stream (`file.txt:stream`) or
    // rebases drive-relative (`C:foo`); neither is a legitimate component.
    if (segment.includes(':')) {
      throw new PathViolationError(`Invalid ${label}: ":" is not allowed in a path component`);
    }
    const deviceStem = segment.split('.')[0].toUpperCase();
    if (WINDOWS_DEVICE_NAMES.has(deviceStem)) {
      throw new PathViolationError(`Invalid ${label}: "${segment}" names a reserved Windows device`);
    }
  }
}

/**
 * Resolve `userInput` against `baseDir` and prove the result stays inside it.
 * Returns the resolved absolute path (never a path outside `baseDir`).
 * Throws PathViolationError (status 400, code PATH_OUTSIDE_BASE) otherwise.
 *
 * `''` / `.` resolve to the base dir itself and are allowed.
 */
export function resolveInside(baseDir, userInput, { label = 'path' } = {}) {
  if (typeof baseDir !== 'string' || baseDir.length === 0) {
    throw new PathViolationError('Invalid base directory');
  }
  if (typeof userInput !== 'string' || userInput.length === 0) {
    throw new PathViolationError(`Invalid ${label}: expected a non-empty string`);
  }

  const base = resolve(baseDir);
  const decoded = decodeRepeatedly(userInput);

  assertSafeForm(userInput, label);
  if (decoded !== userInput) assertSafeForm(decoded, label);

  const abs = resolve(base, decoded);
  const rel = relative(base, abs);
  if (rel.startsWith('..') || isAbsolute(rel)) {
    throw new PathViolationError(`Invalid ${label}: resolves outside the allowed directory`);
  }
  return abs;
}

/**
 * Containment predicate matching resolveInside's rule: is `absPath` inside
 * `baseDir` (the base itself counts as inside). For callers that hold an
 * already-resolved path and must test it against one of several roots.
 */
export function isInside(baseDir, absPath) {
  if (typeof baseDir !== 'string' || baseDir.length === 0) return false;
  if (typeof absPath !== 'string' || absPath.length === 0) return false;
  const rel = relative(resolve(baseDir), resolve(absPath));
  return rel === '' || (!rel.startsWith('..') && !isAbsolute(rel));
}

/**
 * Reduce an upload-supplied filename to a safe leaf name. Strips every
 * directory component (both separators), replaces forbidden/control characters
 * with `_`, collapses whitespace, strips the trailing dots/spaces Windows would
 * silently drop itself (which would land the write on a DIFFERENT name than the
 * one shown to the user) and caps the length. Returns `''` when nothing usable
 * remains (empty, `.` or `..`) so the caller can reject with a 400.
 */
export function sanitizeFileName(name) {
  if (typeof name !== 'string') return '';
  const leaf = basename(name.replace(/\\/g, '/'));
  let out = leaf
    .replace(FORBIDDEN_FILE_NAME_CHARS, '_')
    .replace(/[\\/]/g, '_')
    .trim()
    .replace(/\s+/g, ' ')
    .replace(/[. ]+$/, '');
  if (out.length > MAX_FILE_NAME_LENGTH) out = out.slice(0, MAX_FILE_NAME_LENGTH).replace(/[. ]+$/, '');
  if (out === '' || out === '.' || out === '..') return '';
  return out;
}
