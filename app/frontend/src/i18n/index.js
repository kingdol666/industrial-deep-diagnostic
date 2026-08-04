import { createI18n } from 'vue-i18n';
import zh from './zh.js';
import en from './en.js';

const STORAGE_KEY = 'idd.locale';
const SUPPORTED = ['zh', 'en'];

/**
 * Resolve the initial locale:
 * 1. localStorage override  2. navigator.language  3. fallback 'zh'
 */
function detectInitialLocale() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved && SUPPORTED.includes(saved)) return saved;
  } catch {}
  const nav = (navigator.language || '').toLowerCase();
  if (nav.startsWith('en')) return 'en';
  return 'zh';
}

const i18n = createI18n({
  legacy: false,
  locale: detectInitialLocale(),
  fallbackLocale: 'zh',
  messages: { zh, en },
});

/**
 * Switch locale and persist the choice.
 * @param {('zh'|'en')} locale
 */
export function setLocale(locale) {
  if (!SUPPORTED.includes(locale)) return;
  i18n.global.locale.value = locale;
  try {
    localStorage.setItem(STORAGE_KEY, locale);
  } catch {}
  document.documentElement.lang = locale;
}

/**
 * Toggle between zh and en.
 * @returns {('zh'|'en')} the new locale
 */
export function toggleLocale() {
  const next = i18n.global.locale.value === 'zh' ? 'en' : 'zh';
  setLocale(next);
  return next;
}

/** @returns {('zh'|'en')} */
export function getLocale() {
  return i18n.global.locale.value;
}

// Keep <html lang> in sync on first load
document.documentElement.lang = i18n.global.locale.value;

export default i18n;
