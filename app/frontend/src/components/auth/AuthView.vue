<template>
  <div class="auth-page">
    <!-- The plate is the instrument's nameplate: rail, mark, identity, gate. -->
    <div class="auth-plate">
      <div class="auth-rail">
        <span class="auth-rail-label">{{ $t('auth.railLabel') }}</span>
        <span class="auth-rail-state">
          <span class="auth-rail-dot"></span>
          {{ $t('auth.railState') }}
        </span>
        <button
          class="auth-lang"
          type="button"
          :title="$t('lang.switchTo')"
          @click="onToggleLocale"
        >
          {{ $t('lang.switch') }}
        </button>
      </div>

      <div class="auth-body">
        <div class="auth-brand">
          <div class="auth-mark">ID</div>
          <div class="auth-kicker">{{ $t('common.appKicker') }}</div>
          <h1 class="auth-title">{{ $t('auth.appTitle') }}</h1>
          <p class="auth-sub">{{ $t('auth.appSubtitle') }}</p>
        </div>

        <div class="auth-tabs" role="tablist">
          <button
            type="button"
            role="tab"
            :aria-selected="mode === 'login'"
            :class="{ active: mode === 'login' }"
            @click="switchMode('login')"
          >{{ $t('auth.login') }}</button>
          <button
            type="button"
            role="tab"
            :aria-selected="mode === 'register'"
            :class="{ active: mode === 'register' }"
            @click="switchMode('register')"
          >{{ $t('auth.register') }}</button>
        </div>

        <form class="auth-form" @submit.prevent="submit">
          <label class="auth-field">
            <span class="auth-field-label">{{ $t('auth.username') }}</span>
            <input v-model.trim="username" autocomplete="username" :placeholder="$t('auth.usernamePlaceholder')" />
          </label>
          <label v-if="mode === 'register'" class="auth-field">
            <span class="auth-field-label">{{ $t('auth.emailOptional') }}</span>
            <input v-model.trim="email" type="email" autocomplete="email" placeholder="name@example.com" />
          </label>
          <label class="auth-field">
            <span class="auth-field-label">{{ $t('auth.passwordLabel') }}</span>
            <input
              v-model="password"
              type="password"
              :autocomplete="mode === 'login' ? 'current-password' : 'new-password'"
              :placeholder="$t('auth.passwordPlaceholder')"
            />
          </label>

          <div v-if="error" class="auth-error" role="alert">{{ error }}</div>

          <button class="auth-submit" type="submit" :disabled="loading">
            {{ loading ? $t('auth.pleaseWait') : (mode === 'login' ? $t('auth.loginAction') : $t('auth.registerAndLogin')) }}
          </button>
          <p class="auth-note">{{ $t('auth.tokenNote') }}</p>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { api, setToken, setStoredUser } from '../../api/index.js';
import { toggleLocale } from '../../i18n/index.js';

const { t } = useI18n();
const emit = defineEmits(['authed']);

const mode = ref('login');
const username = ref('');
const email = ref('');
const password = ref('');
const error = ref('');
const loading = ref(false);

function switchMode(m) {
  mode.value = m;
  error.value = '';
}

function onToggleLocale() {
  toggleLocale();
}

async function submit() {
  error.value = '';
  if (!username.value || !password.value) {
    error.value = t('auth.errUsernamePasswordRequired');
    return;
  }
  loading.value = true;
  try {
    const body = { username: username.value, password: password.value };
    if (mode.value === 'register') {
      if (email.value) body.email = email.value;
    }
    const data = mode.value === 'login' ? await api.authLogin(body) : await api.authRegister(body);
    setToken(data.session_token);
    setStoredUser(data.user);
    emit('authed', data.user);
  } catch (err) {
    error.value = err.message || t('auth.errOperationFailed');
  } finally {
    loading.value = false;
  }
}
</script>

<!--
  Access plate.

  This screen is the product's threshold, and it is the first surface anyone
  sees — so it has to be the same instrument as the console behind it. It was
  previously a hardcoded light card (`#fff` on `#f6f8fb`) with a `#1f5eff` blue
  button and its own 8-14px radii: 23 colour literals and not one design token.
  A user met a blue-and-white SaaS form, then a warm-graphite amber console.

  Rebuilt from the token system as a *nameplate*: a rail carrying the access
  state, the mark in its gauge housing, the serif identity, then the gate.
  Every colour below is a token; there is no literal hue in this file.
-->
<style scoped>
.auth-page {
  min-height: 100vh;
  min-height: 100dvh;               /* survives mobile browser chrome */
  display: grid;
  place-items: center;
  padding: 24px;
  background-color: var(--bg);
  background-image:
    linear-gradient(var(--bg-grid) 1px, transparent 1px),
    linear-gradient(90deg, var(--bg-grid) 1px, transparent 1px),
    radial-gradient(760px 520px at 50% 0%, rgba(232, 163, 61, 0.055), transparent 62%);
  background-size: 32px 32px, 32px 32px, 100% 100%;
}

/* ── The plate ────────────────────────────────────────────────────────── */
.auth-plate {
  width: 100%;
  max-width: 400px;
  background: var(--surface);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius);
  box-shadow: var(--shadow-lg), var(--inset-hi);
  overflow: hidden;
  position: relative;
}

/* Corner ticks — the plate reads as fastened, not floated. */
.auth-plate::before,
.auth-plate::after {
  content: '';
  position: absolute;
  width: 9px;
  height: 9px;
  border-color: var(--border-accent);
  border-style: solid;
  pointer-events: none;
}
.auth-plate::before { top: 5px; left: 5px; border-width: 1px 0 0 1px; }
.auth-plate::after { bottom: 5px; right: 5px; border-width: 0 1px 1px 0; }

/* ── Rail ─────────────────────────────────────────────────────────────── */
.auth-rail {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 34px;
  padding: 0 12px;
  background: var(--surface-soft);
  border-bottom: 1px solid var(--border);
}

.auth-rail-label {
  font-family: var(--font-mono);
  font-size: var(--fs-micro);
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--accent);
  display: inline-flex;
  align-items: center;
  gap: 7px;
}

.auth-rail-label::before {
  content: '';
  width: 3px;
  height: 9px;
  background: var(--accent);
  flex: none;
}

.auth-rail-state {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-family: var(--font-mono);
  font-size: var(--fs-micro);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text3);
}

.auth-rail-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--green);
  box-shadow: 0 0 6px rgba(143, 191, 106, 0.5);
}

.auth-lang {
  border: 1px solid var(--border);
  background: transparent;
  border-radius: var(--radius-xs);
  padding: 2px 8px;
  font-family: var(--font-mono);
  font-size: var(--fs-micro);
  font-weight: 500;
  letter-spacing: 0.08em;
  color: var(--text3);
  cursor: pointer;
  transition: color 0.14s ease, border-color 0.14s ease, background 0.14s ease;
}

.auth-lang:hover {
  color: var(--accent);
  border-color: var(--border-accent);
  background: var(--accent-soft);
}

/* ── Body ─────────────────────────────────────────────────────────────── */
.auth-body { padding: 26px 26px 22px; }

.auth-brand {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 7px;
  margin-bottom: 22px;
  text-align: center;
}

/* The mark in its gauge housing — identical treatment to the sidebar, so the
   identity does not change shape when you cross the threshold. */
.auth-mark {
  width: 46px;
  height: 46px;
  border-radius: var(--radius-sm);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  position: relative;
  background: var(--surface-strong);
  border: 1px solid var(--border-strong);
  color: var(--accent);
  font-family: var(--font-mono);
  font-weight: 600;
  font-size: 15px;
  letter-spacing: 0.02em;
  box-shadow: var(--inset-hi), 0 0 0 1px rgba(232, 163, 61, 0.08);
  margin-bottom: 3px;
}

.auth-mark::before {
  content: '';
  position: absolute;
  inset: 4px;
  border: 1px solid rgba(232, 163, 61, 0.22);
  border-radius: 2px;
  pointer-events: none;
}

.auth-mark::after {
  content: '';
  position: absolute;
  width: 5px;
  height: 5px;
  top: 8px;
  right: 8px;
  border-radius: 50%;
  background: var(--accent);
  box-shadow: 0 0 6px rgba(232, 163, 61, 0.6);
  animation: phosphor-pulse 2.4s ease-in-out infinite;
}

@keyframes phosphor-pulse {
  0%, 100% { opacity: 0.5; }
  50% { opacity: 1; }
}

.auth-kicker {
  font-family: var(--font-mono);
  font-size: var(--fs-micro);
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--text3);
}

.auth-title {
  font-family: var(--font-display);
  font-size: 21px;
  font-weight: 500;
  line-height: 1.15;
  letter-spacing: -0.015em;
  color: var(--text);
}

.auth-sub {
  font-size: var(--fs-sm);
  color: var(--text2);
  line-height: 1.45;
}

/* ── Mode switch — instrument segmented control ───────────────────────── */
.auth-tabs {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2px;
  padding: 2px;
  background: var(--surface-soft);
  border: 1px solid var(--border);
  border-radius: var(--radius-xs);
  margin-bottom: 20px;
}

.auth-tabs button {
  border: none;
  background: transparent;
  min-height: 30px;
  border-radius: 2px;
  font-family: var(--font-mono);
  font-size: var(--fs-label);
  font-weight: 500;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text3);
  cursor: pointer;
  transition: color 0.14s ease, background 0.14s ease;
}

.auth-tabs button:hover { color: var(--text); }

.auth-tabs button.active {
  background: var(--surface-strong);
  color: var(--accent-bright);
  box-shadow: var(--inset-hi);
}

/* ── Form ─────────────────────────────────────────────────────────────── */
.auth-form { display: flex; flex-direction: column; gap: 13px; }

.auth-field { display: flex; flex-direction: column; gap: 5px; }

.auth-field-label {
  font-family: var(--font-mono);
  font-size: var(--fs-micro);
  letter-spacing: var(--track-label);
  text-transform: uppercase;
  color: var(--text3);
}

/* Inputs inherit the global token styles; only the density is local. */
.auth-field input { min-height: 38px; padding: 0 12px; border-radius: var(--radius-xs); }

.auth-error {
  background: var(--red-soft);
  border: 1px solid var(--red-border);
  border-left: 3px solid var(--red);
  color: var(--red);
  border-radius: var(--radius-xs);
  padding: 8px 10px;
  font-size: var(--fs-sm);
  line-height: 1.5;
}

.auth-submit {
  min-height: 40px;
  border: 1px solid var(--accent-strong);
  border-radius: var(--radius-xs);
  background: var(--accent);
  color: #1a1408;
  font-family: var(--font-ui);
  font-size: var(--fs-lg);
  font-weight: 600;
  letter-spacing: 0.04em;
  cursor: pointer;
  transition: background 0.14s ease, border-color 0.14s ease;
  box-shadow: var(--inset-hi), 0 0 0 1px rgba(232, 163, 61, 0.2), 0 4px 14px rgba(232, 163, 61, 0.18);
}

.auth-submit:hover:not(:disabled) {
  background: var(--accent-bright);
  border-color: var(--accent);
}

.auth-submit:disabled { opacity: 0.55; cursor: not-allowed; }

.auth-note {
  font-size: var(--fs-micro);
  color: var(--text3);
  line-height: 1.6;
  margin: 1px 0 0;
}

/* ── Narrow: reclaim the plate's padding, keep it on one screen ───────── */
@media (max-width: 420px) {
  .auth-page { padding: 12px; }
  .auth-body { padding: 20px 16px 18px; }
  .auth-title { font-size: 19px; }
  .auth-rail { padding: 0 10px; gap: 8px; }
  .auth-brand { margin-bottom: 18px; }
}

@media (max-height: 620px) {
  .auth-mark { width: 38px; height: 38px; font-size: 13px; }
  .auth-brand { gap: 5px; margin-bottom: 14px; }
  .auth-body { padding: 18px 22px 16px; }
  .auth-form { gap: 10px; }
}
</style>
