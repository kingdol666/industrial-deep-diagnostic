<template>
  <div class="settings-view" data-testid="settings-view">
    <!-- ── Account ─────────────────────────────────────────────── -->
    <section class="panel" data-testid="settings-account">
      <div class="panel-head">
        <span class="panel-icon">◇</span>
        <h2 class="panel-title">{{ $t('settings.accountTitle') }}</h2>
        <span class="head-pill" :class="authTypeClass">{{ authTypeLabel }}</span>
      </div>
      <div class="account-body">
        <div class="account-mark">{{ avatarLetter }}</div>
        <dl class="account-grid">
          <div class="account-field">
            <dt>{{ $t('settings.fieldUsername') }}</dt>
            <dd data-testid="settings-username">{{ account?.username || '—' }}</dd>
          </div>
          <div class="account-field">
            <dt>{{ $t('settings.fieldRole') }}</dt>
            <dd>
              <span class="role-pill" :class="account?.role === 'admin' ? 'is-admin' : 'is-user'">
                {{ account?.role === 'admin' ? $t('auth.roleAdmin') : $t('auth.roleUser') }}
              </span>
            </dd>
          </div>
          <div class="account-field">
            <dt>{{ $t('settings.fieldAuthType') }}</dt>
            <dd>{{ authTypeLabel }}</dd>
          </div>
        </dl>
      </div>
    </section>

    <!-- ── API Tokens ──────────────────────────────────────────── -->
    <section class="panel" data-testid="settings-tokens">
      <div class="panel-head">
        <span class="panel-icon">⌸</span>
        <h2 class="panel-title">{{ $t('settings.tokensTitle') }}</h2>
        <span class="head-pill head-count">{{ tokens.length }}</span>
      </div>

      <p class="tokens-intro">{{ $t('settings.tokensIntro') }}</p>

      <div class="usage-strip">
        <code class="usage-code">Authorization: Bearer idd_···</code>
        <span class="usage-sep">·</span>
        <span class="usage-text">{{ $t('settings.externalApiHint') }}</span>
        <code class="usage-code">/api/external/v1</code>
      </div>

      <!-- Create -->
      <form class="create-row" @submit.prevent="createToken">
        <input
          v-model.trim="newName"
          class="field-input name-input"
          data-testid="token-name-input"
          :placeholder="$t('settings.tokenNamePlaceholder')"
          maxlength="64"
        />
        <select v-model="newTtl" class="field-input ttl-select" data-testid="token-ttl-select" :aria-label="$t('settings.fieldExpires')">
          <option v-for="opt in ttlOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
        </select>
        <button
          class="btn btn-accent"
          type="submit"
          data-testid="token-create"
          :disabled="!newName || busy"
        >{{ busy ? $t('settings.creating') : $t('settings.createToken') }}</button>
      </form>

      <!-- One-time secret reveal -->
      <div v-if="freshToken" class="fresh" data-testid="token-fresh">
        <div class="fresh-head">
          <span class="fresh-label">{{ $t('settings.copyNow') }}</span>
          <button class="btn btn-ghost btn-sm" type="button" data-testid="token-copy" @click="copyFresh">
            {{ copied ? $t('settings.copied') : $t('settings.copy') }}
          </button>
          <button class="btn btn-ghost btn-sm" type="button" @click="freshToken = ''">{{ $t('settings.dismiss') }}</button>
        </div>
        <code class="fresh-value">{{ freshToken }}</code>
        <p class="fresh-note">{{ $t('settings.freshNote') }}</p>
      </div>

      <div v-if="error" class="error-banner" role="alert" data-testid="token-error">{{ error }}</div>

      <!-- List -->
      <div v-if="loading" class="loading-row"><span class="spinner" aria-hidden="true"></span></div>

      <p v-else-if="!tokens.length" class="empty-row" data-testid="token-empty">{{ $t('settings.emptyTokens') }}</p>

      <div v-else class="table-wrap">
        <table class="token-table">
          <thead>
            <tr>
              <th>{{ $t('settings.colName') }}</th>
              <th>{{ $t('settings.colPrefix') }}</th>
              <th>{{ $t('settings.colCreated') }}</th>
              <th>{{ $t('settings.colExpires') }}</th>
              <th>{{ $t('settings.colLastUsed') }}</th>
              <th>{{ $t('settings.colStatus') }}</th>
              <th class="th-action"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="tk in tokens" :key="tk.id" data-testid="token-row">
              <td class="td-name">{{ tk.name }}</td>
              <td><code class="mono">{{ tk.token_prefix }}…</code></td>
              <td class="td-time">{{ fmtTime(tk.created_at) }}</td>
              <td class="td-time">{{ tk.expires_at ? fmtTime(tk.expires_at) : $t('settings.neverExpires') }}</td>
              <td class="td-time">{{ tk.last_used_at ? fmtTime(tk.last_used_at) : $t('settings.neverUsed') }}</td>
              <td><span class="status-pill" :class="statusOf(tk).cls">{{ statusOf(tk).label }}</span></td>
              <td class="td-action">
                <button
                  v-if="!tk.revoked_at"
                  class="btn btn-danger btn-sm"
                  type="button"
                  data-testid="token-revoke"
                  @click="revoke(tk)"
                >{{ $t('settings.revoke') }}</button>
                <span v-else class="dash">—</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { api } from '../../api/index.js';
import { formatTime } from '../../utils/time.js';

const { t } = useI18n();

// Identity comes from the app shell (cookie session — /api/auth/me is the
// authority, App.vue owns the user object); there is no JS-readable stored user.
const props = defineProps({
  user: { type: Object, default: null },
});

const account = computed(() => props.user);
const authType = ref('');
const tokens = ref([]);
const newName = ref('');
// '' = 未选择（默认 30 天）；0 = 永不过期（后端 expires_in_days: null）
const newTtl = ref(30);
const freshToken = ref('');
const copied = ref(false);
const busy = ref(false);
const loading = ref(true);
const error = ref('');

// TTL 档位与 RAG 系统的 token 页保持同一组习惯值
const ttlOptions = computed(() => [
  { value: 7, label: t('settings.ttl7') },
  { value: 30, label: t('settings.ttl30') },
  { value: 90, label: t('settings.ttl90') },
  { value: 365, label: t('settings.ttl365') },
  { value: 0, label: t('settings.ttlNever') },
]);

const avatarLetter = computed(() => (account.value?.username || '?').charAt(0).toUpperCase());
const authTypeLabel = computed(() => {
  if (authType.value === 'api_token') return t('settings.authViaToken');
  if (authType.value === 'session') return t('settings.authViaSession');
  return '—';
});
const authTypeClass = computed(() => (authType.value === 'api_token' ? 'is-token' : 'is-session'));

// SQLite datetime('now') 是无时区标记的 UTC（'YYYY-MM-DD HH:MM:SS'），显式按 UTC 解析
function parseDbTime(ts) {
  if (!ts) return null;
  const s = String(ts);
  const d = new Date(s.includes('T') ? s : `${s.replace(' ', 'T')}Z`);
  return Number.isNaN(d.getTime()) ? null : d;
}

// 过期时间是未来时刻，必须显示绝对日期；formatTime 的相对表述只适用于过去
function fmtAbs(d) {
  return d.toLocaleString(undefined, { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

function fmtTime(ts) {
  const d = parseDbTime(ts);
  if (!d) return String(ts || '—');
  if (d.getTime() > Date.now()) return fmtAbs(d);
  return formatTime(String(ts));
}

function statusOf(tk) {
  if (tk.revoked_at) return { label: t('settings.statusRevoked'), cls: 'is-revoked' };
  const exp = parseDbTime(tk.expires_at);
  if (exp && exp.getTime() < Date.now()) return { label: t('settings.statusExpired'), cls: 'is-expired' };
  return { label: t('settings.statusActive'), cls: 'is-active' };
}

async function loadAccount() {
  try {
    const data = await api.authMe();
    authType.value = data.auth_type || '';
  } catch { /* 401 已由全局处理器接管 */ }
}

async function loadTokens() {
  loading.value = true;
  try {
    tokens.value = await api.listTokens();
  } catch (err) {
    error.value = err.message || t('settings.errLoad');
  } finally {
    loading.value = false;
  }
}

async function createToken() {
  if (!newName.value || busy.value) return;
  busy.value = true;
  error.value = '';
  freshToken.value = '';
  try {
    const body = { name: newName.value };
    // 0 → null（永不过期）；其余档位按天数
    body.expires_in_days = newTtl.value === 0 ? null : Number(newTtl.value);
    const data = await api.createToken(body);
    freshToken.value = data.token;
    copied.value = false;
    newName.value = '';
    await loadTokens();
  } catch (err) {
    error.value = err.message || t('settings.errCreate');
  } finally {
    busy.value = false;
  }
}

async function copyFresh() {
  try {
    await navigator.clipboard.writeText(freshToken.value);
    copied.value = true;
    setTimeout(() => { copied.value = false; }, 2000);
  } catch { /* 剪贴板被拒时明文仍可手动选中复制 */ }
}

async function revoke(tk) {
  if (!window.confirm(t('settings.revokeConfirm', { name: tk.name }))) return;
  try {
    await api.revokeToken(tk.id);
    if (freshToken.value) freshToken.value = '';
    await loadTokens();
  } catch (err) {
    error.value = err.message || t('settings.errRevoke');
  }
}

onMounted(() => {
  loadAccount();
  loadTokens();
});
</script>

<style scoped>
.settings-view {
  display: flex;
  flex-direction: column;
  gap: 18px;
  max-width: 980px;
}

/* ── Panels ──────────────────────────────────────────────── */
.panel {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  overflow: hidden;
}
.panel-head {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 13px 18px;
  border-bottom: 1px solid var(--border);
  background: var(--surface-soft);
}
.panel-icon {
  font-size: 15px;
  color: var(--accent);
  line-height: 1;
}
.panel-title {
  margin: 0;
  font-family: var(--font-display);
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 0.01em;
  color: var(--text);
}
.head-pill {
  margin-left: auto;
  font-family: var(--font-mono);
  font-size: 10.5px;
  padding: 2px 9px;
  border-radius: 999px;
  border: 1px solid var(--border-strong);
  color: var(--text2);
  white-space: nowrap;
}
.head-pill.is-session { color: var(--green); border-color: var(--green-border); background: var(--green-soft); }
.head-pill.is-token { color: var(--cyan); border-color: var(--cyan-border); background: var(--cyan-soft); }
.head-count { color: var(--accent); border-color: var(--border-accent); background: var(--accent-soft); }

/* ── Account ─────────────────────────────────────────────── */
.account-body {
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 18px;
}
.account-mark {
  width: 46px;
  height: 46px;
  border-radius: 10px;
  display: grid;
  place-items: center;
  flex-shrink: 0;
  font-family: var(--font-display);
  font-size: 20px;
  color: var(--accent);
  background: var(--accent-soft);
  border: 1px solid var(--border-accent);
}
.account-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(120px, 1fr));
  gap: 12px 24px;
  margin: 0;
  min-width: 0;
}
.account-field dt {
  font-family: var(--font-mono);
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-dim);
  margin-bottom: 4px;
}
.account-field dd {
  margin: 0;
  font-size: 13.5px;
  color: var(--text);
  overflow-wrap: anywhere;
}
.role-pill {
  display: inline-block;
  font-size: 11.5px;
  font-weight: 600;
  padding: 2px 10px;
  border-radius: 999px;
}
.role-pill.is-admin { color: var(--accent); background: var(--accent-soft); border: 1px solid var(--border-accent); }
.role-pill.is-user { color: var(--text2); background: var(--surface-muted); border: 1px solid var(--border-strong); }

/* ── Token intro / usage ─────────────────────────────────── */
.tokens-intro {
  margin: 0;
  padding: 14px 18px 0;
  font-size: 12.5px;
  line-height: 1.65;
  color: var(--text2);
}
.usage-strip {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin: 10px 18px 0;
  padding: 9px 12px;
  border-radius: 7px;
  background: var(--surface-soft);
  border: 1px solid var(--border);
}
.usage-code {
  font-family: var(--font-mono);
  font-size: 11.5px;
  color: var(--accent-bright);
  background: var(--surface);
  border: 1px solid var(--border-strong);
  border-radius: 5px;
  padding: 2px 7px;
  white-space: nowrap;
  overflow-wrap: anywhere;
}
.usage-sep { color: var(--text-dim); }
.usage-text { font-size: 12px; color: var(--text3); }

/* ── Create row ──────────────────────────────────────────── */
.create-row {
  display: flex;
  gap: 10px;
  align-items: stretch;
  padding: 14px 18px;
  flex-wrap: wrap;
}
.field-input {
  height: 36px;
  padding: 0 11px;
  border-radius: 7px;
  border: 1px solid var(--border-strong);
  background: var(--surface-soft);
  color: var(--text);
  font-family: var(--font-ui);
  font-size: 13px;
}
.field-input:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 2px var(--accent-soft);
}
.name-input { flex: 1 1 220px; min-width: 0; }
.ttl-select { flex: 0 0 150px; }
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 7px;
  border: 1px solid var(--border-strong);
  background: var(--surface-muted);
  color: var(--text);
  font-family: var(--font-ui);
  font-size: 12.5px;
  font-weight: 600;
  padding: 0 16px;
  height: 36px;
  cursor: pointer;
  transition: border-color 0.15s ease, background 0.15s ease;
}
.btn:disabled { opacity: 0.45; cursor: not-allowed; }
.btn-accent {
  background: var(--accent-soft-strong);
  border-color: var(--border-accent);
  color: var(--accent-bright);
}
.btn-accent:hover:not(:disabled) { border-color: var(--accent); }
.btn-ghost { background: transparent; }
.btn-sm { height: 26px; padding: 0 10px; font-size: 11.5px; }
.btn-danger { color: var(--red); border-color: var(--red-border); background: var(--red-soft); }
.btn-danger:hover { border-color: var(--red); }

/* ── Fresh secret ────────────────────────────────────────── */
.fresh {
  margin: 0 18px 6px;
  padding: 13px 14px;
  border-radius: 8px;
  background: var(--green-soft);
  border: 1px solid var(--green-border);
}
.fresh-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 9px;
  flex-wrap: wrap;
}
.fresh-label {
  font-size: 12.5px;
  font-weight: 700;
  color: var(--green);
  margin-right: auto;
}
.fresh-head .btn + .btn { margin-left: 6px; }
.fresh-value {
  display: block;
  font-family: var(--font-mono);
  font-size: 12.5px;
  color: var(--text);
  background: var(--surface);
  border: 1px solid var(--border-strong);
  border-radius: 6px;
  padding: 9px 11px;
  overflow-wrap: anywhere;
  user-select: all;
}
.fresh-note {
  margin: 8px 0 0;
  font-size: 11.5px;
  color: var(--text3);
}

/* ── Errors / loading / empty ────────────────────────────── */
.error-banner {
  margin: 10px 18px 0;
  padding: 9px 12px;
  border-radius: 7px;
  font-size: 12.5px;
  color: var(--red);
  background: var(--red-soft);
  border: 1px solid var(--red-border);
}
.loading-row { display: grid; place-items: center; padding: 34px; }
.spinner {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: 2px solid var(--border-strong);
  border-top-color: var(--accent);
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.empty-row {
  margin: 0;
  padding: 26px 18px 30px;
  text-align: center;
  font-size: 12.5px;
  color: var(--text3);
}

/* ── Token table ─────────────────────────────────────────── */
.table-wrap { overflow-x: auto; }
.token-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12.5px;
}
.token-table th {
  text-align: left;
  padding: 9px 14px;
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: var(--text-dim);
  background: var(--surface-soft);
  border-bottom: 1px solid var(--border);
  white-space: nowrap;
}
.token-table td {
  padding: 10px 14px;
  border-bottom: 1px solid var(--border);
  color: var(--text2);
  vertical-align: middle;
}
.token-table tbody tr:last-child td { border-bottom: none; }
.token-table tbody tr:hover { background: var(--accent-soft); }
.td-name {
  font-weight: 600;
  color: var(--text);
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.td-time { font-family: var(--font-mono); font-size: 11.5px; color: var(--text3); white-space: nowrap; }
.td-action { text-align: right; }
.th-action { width: 84px; }
.mono {
  font-family: var(--font-mono);
  font-size: 11.5px;
  color: var(--text2);
  background: var(--surface-soft);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 1px 6px;
}
.dash { color: var(--text-dim); }
.status-pill {
  display: inline-flex;
  align-items: center;
  font-size: 11px;
  font-weight: 700;
  padding: 2px 9px;
  border-radius: 999px;
  border: 1px solid transparent;
  white-space: nowrap;
}
.status-pill.is-active { color: var(--green); background: var(--green-soft); border-color: var(--green-border); }
.status-pill.is-expired { color: var(--yellow); background: var(--yellow-soft); border-color: var(--yellow-border); }
.status-pill.is-revoked { color: var(--red); background: var(--red-soft); border-color: var(--red-border); }

/* ── Narrow viewport ─────────────────────────────────────── */
@media (max-width: 760px) {
  .account-body { flex-direction: column; align-items: flex-start; }
  .account-grid { grid-template-columns: 1fr; }
  .ttl-select { flex: 1 1 100%; }
}
</style>
