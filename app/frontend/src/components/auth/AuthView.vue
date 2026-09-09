<template>
  <div class="auth-page">
    <div class="auth-card">
      <div class="auth-brand">
        <div class="auth-mark">ID</div>
        <div class="auth-title">工业深度诊断系统</div>
        <div class="auth-sub">Industrial Deep Diagnostic · 统一身份认证</div>
      </div>

      <div class="auth-tabs" role="tablist">
        <button type="button" :class="{ active: mode === 'login' }" @click="switchMode('login')">登录</button>
        <button type="button" :class="{ active: mode === 'register' }" @click="switchMode('register')">注册</button>
      </div>

      <form class="auth-form" @submit.prevent="submit">
        <label class="auth-field">
          <span>用户名</span>
          <input v-model.trim="username" autocomplete="username" placeholder="3-32 位字母 / 数字 / _ / -" />
        </label>
        <label v-if="mode === 'register'" class="auth-field">
          <span>邮箱（可选）</span>
          <input v-model.trim="email" type="email" autocomplete="email" placeholder="name@example.com" />
        </label>
        <label class="auth-field">
          <span>密码</span>
          <input
            v-model="password"
            type="password"
            :autocomplete="mode === 'login' ? 'current-password' : 'new-password'"
            placeholder="至少 8 位，需同时包含字母和数字"
          />
        </label>

        <div v-if="error" class="auth-error">{{ error }}</div>

        <button class="auth-submit" type="submit" :disabled="loading">
          {{ loading ? '请稍候…' : (mode === 'login' ? '登 录' : '注册并登录') }}
        </button>
        <p class="auth-note">登录后可在「账户」中创建多个 API Token 用于程序化调用（明文仅显示一次）。</p>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { api, setToken, setStoredUser } from '../../api/index.js';

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

async function submit() {
  error.value = '';
  if (!username.value || !password.value) {
    error.value = '请输入用户名和密码';
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
    error.value = err.message || '操作失败';
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(160deg, #f6f8fb 0%, #eef2f7 100%);
  padding: 24px;
}
.auth-card {
  width: 380px;
  max-width: 100%;
  background: #ffffff;
  border: 1px solid #e5eaf1;
  border-radius: 14px;
  box-shadow: 0 10px 30px rgba(16, 42, 83, 0.08);
  padding: 28px 28px 22px;
}
.auth-brand { display: flex; flex-direction: column; align-items: center; gap: 6px; margin-bottom: 18px; }
.auth-mark {
  width: 44px; height: 44px; border-radius: 12px;
  background: #1f5eff; color: #fff; font-weight: 700; font-size: 18px;
  display: flex; align-items: center; justify-content: center;
}
.auth-title { font-size: 17px; font-weight: 700; color: #16233a; }
.auth-sub { font-size: 12px; color: #7b8698; }
.auth-tabs {
  display: grid; grid-template-columns: 1fr 1fr; gap: 4px;
  background: #f1f4f9; border-radius: 10px; padding: 4px; margin-bottom: 18px;
}
.auth-tabs button {
  border: 0; background: transparent; padding: 8px 0; border-radius: 8px;
  font-size: 13px; color: #5b6779; cursor: pointer;
}
.auth-tabs button.active { background: #fff; color: #16233a; font-weight: 600; box-shadow: 0 1px 3px rgba(16,42,83,.12); }
.auth-form { display: flex; flex-direction: column; gap: 12px; }
.auth-field { display: flex; flex-direction: column; gap: 5px; }
.auth-field span { font-size: 12px; color: #5b6779; }
.auth-field input {
  height: 38px; border: 1px solid #dfe5ee; border-radius: 8px; padding: 0 12px;
  font-size: 13px; color: #16233a; outline: none; background: #fff;
}
.auth-field input:focus { border-color: #1f5eff; box-shadow: 0 0 0 3px rgba(31, 94, 255, .12); }
.auth-error {
  background: #fdf0f0; border: 1px solid #f3c8c8; color: #b42323;
  border-radius: 8px; padding: 8px 10px; font-size: 12px;
}
.auth-submit {
  height: 40px; border: 0; border-radius: 8px; background: #1f5eff; color: #fff;
  font-size: 14px; font-weight: 600; cursor: pointer;
}
.auth-submit:disabled { opacity: .6; cursor: default; }
.auth-note { font-size: 11px; color: #93a0b3; line-height: 1.6; margin: 2px 0 0; }
</style>
