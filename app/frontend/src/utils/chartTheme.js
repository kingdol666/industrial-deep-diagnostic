/**
 * Chart theme bridge — resolves design-system tokens for ECharts options.
 *
 * ECharts options are plain JavaScript objects, so they cannot consume
 * `var(--token)` the way a stylesheet can: the canvas renderer needs a concrete
 * colour value. Without this bridge every chart re-declares its palette as
 * frozen literals (ECharts' stock blue `#5470c6`, light blue `#73c0de`, violet
 * `#9a60b4`), which is how a warm-graphite console ends up painting itself in a
 * cool default palette. Reading the tokens here keeps charts on the same palette
 * as the rest of the instrument, so a change in `global.css` carries through.
 *
 * The fallbacks mirror the `:root` values in `styles/global.css` so a chart
 * still renders on-palette even when the stylesheet has not been applied yet.
 */

const SERIES_TOKENS = ['--accent', '--cyan', '--green', '--purple', '--red', '--accent-bright'];
const SERIES_FALLBACK = ['#e8a33d', '#6ba8b8', '#8fbf6a', '#b889e0', '#d45d3d', '#f4b65a'];

/* Sequential cold-to-hot ramp in the instrument's own vocabulary: recessed well
 * at the cold end, cadmium rust at the hot end. Deliberately contains no blue. */
const HEAT_TOKENS = ['--well-2', '--surface2', '--yellow', '--accent', '--red'];
const HEAT_FALLBACK = ['#0a0b07', '#20211a', '#d4a93d', '#e8a33d', '#d45d3d'];

/**
 * Read a CSS custom property off `:root`.
 *
 * @param {string} name     token name, e.g. `--accent`
 * @param {string} fallback value used when the token is missing or empty
 * @returns {string} the trimmed token value, or `fallback`
 */
export function readToken(name, fallback) {
  if (typeof document === 'undefined') return fallback;
  const raw = getComputedStyle(document.documentElement).getPropertyValue(name);
  const value = (raw || '').trim();
  return value || fallback;
}

/** Series palette — amber first, then the sanctioned semantic hues. */
export function seriesPalette() {
  return SERIES_TOKENS.map((name, i) => readToken(name, SERIES_FALLBACK[i]));
}

/** Heatmap ramp — warm, blue-free, cold (recessed well) to hot (rust). */
export function heatRamp() {
  return HEAT_TOKENS.map((name, i) => readToken(name, HEAT_FALLBACK[i]));
}
