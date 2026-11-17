import { createApp } from 'vue';
import App from './App.vue';
import i18n from './i18n/index.js';

/**
 * F1 — 白屏兜底（最后一道防线）。
 *
 * Vue 全局错误处理覆盖两类 App.vue 根级 onErrorCaptured 够不到的情况：
 *   1. 根组件自身 setup/render 抛错（onErrorCaptured 只捕获后代）；
 *   2. 任何在 Vue 之外（如 i18n 初始化、异步 chunk 回调）冒泡上来的异常。
 *
 * 这里用纯 DOM 铺一层遮罩 —— 此时 Vue 可能已经挂不上任何东西了，模板兜底
 * （App.vue 的 .app-fatal）自然也没机会渲染，只有原始 DOM 还能工作。文案
 * 不走 i18n：i18n 本身出错时它还要能显示。
 */
function showFatalOverlay(err, info) {
  if (document.getElementById('app-fatal-overlay')) return; // 幂等：只铺一层
  const overlay = document.createElement('div');
  overlay.id = 'app-fatal-overlay';
  overlay.setAttribute('role', 'alert');
  overlay.style.cssText = [
    'position:fixed', 'inset:0', 'z-index:10000',
    'display:flex', 'align-items:center', 'justify-content:center',
    'padding:24px', 'background:#12130e', 'color:#e7e2d3',
    'font-family:"IBM Plex Mono","SF Mono",Consolas,monospace',
  ].join(';');

  const card = document.createElement('div');
  card.style.cssText = [
    'width:100%', 'max-width:460px', 'box-sizing:border-box',
    'background:#181912', 'border:1px solid rgba(212,93,61,0.34)',
    'border-radius:5px', 'padding:22px',
    'display:flex', 'flex-direction:column', 'gap:12px',
  ].join(';');

  const kicker = document.createElement('div');
  kicker.textContent = 'UI ERROR';
  kicker.style.cssText = 'font-size:9.5px;letter-spacing:0.18em;text-transform:uppercase;color:#d45d3d';

  const message = document.createElement('p');
  message.innerHTML = '界面渲染出错，已中止。<br>Something went wrong while rendering the UI.';
  message.style.cssText = 'margin:0;font-size:11.5px;line-height:1.55;color:#b9b4a4';

  const detail = document.createElement('pre');
  detail.textContent = [err?.message || String(err ?? ''), info ? `(${info})` : '']
    .filter(Boolean).join(' ');
  detail.style.cssText = [
    'margin:0', 'padding:8px 10px', 'max-height:160px', 'overflow:auto',
    'background:rgba(212,93,61,0.10)', 'border:1px solid rgba(212,93,61,0.34)',
    'border-radius:3px', 'color:#d45d3d', 'font-size:9.5px',
    'white-space:pre-wrap', 'word-break:break-word',
  ].join(';');

  const reload = document.createElement('button');
  reload.type = 'button';
  reload.textContent = '重新加载 · Reload';
  reload.style.cssText = [
    'align-self:flex-start', 'min-height:34px', 'padding:0 14px',
    'border:1px solid #d9a04a', 'border-radius:3px', 'background:#e8a33d',
    'color:#1a1408', 'font-size:11.5px', 'font-weight:600', 'cursor:pointer',
  ].join(';');
  reload.addEventListener('click', () => window.location.reload());

  card.append(kicker, message, detail, reload);
  overlay.append(card);
  document.body.append(overlay);
}

const app = createApp(App);

app.config.errorHandler = (err, _instance, info) => {
  console.error('[app.config.errorHandler]', info, err);
  showFatalOverlay(err, info);
};

app.use(i18n).mount('#app');
