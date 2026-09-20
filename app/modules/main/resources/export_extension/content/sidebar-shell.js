// SAK 题库导出助手统一扩展侧边栏壳层
(function () {
  'use strict';
  const SITE = 'http://localhost:5000';
  const loggedIn = /(?:token|session|auth|user)/i.test(Object.keys(localStorage || {}).join(',')) || /(?:session|token|auth)/i.test(document.cookie || '');
  const style = document.createElement('style');
  style.textContent = '#sak-extension-tab{position:fixed;right:0;top:22%;z-index:2147483646;width:42px;height:112px;border:0;border-radius:14px 0 0 14px;background:#4f46e5;color:#fff;box-shadow:0 8px 25px #0003;cursor:pointer;font:700 13px sans-serif;writing-mode:vertical-rl}#sak-extension-auth{margin:8px 0;padding:9px;border-radius:10px;background:#eef2ff;color:#3730a3;font:12px/1.6 sans-serif}#sak-extension-auth a{color:#4338ca;font-weight:700}';
  document.documentElement.appendChild(style);
  const tab = document.createElement('button'); tab.id = 'sak-extension-tab'; tab.textContent = '题库导出'; document.body.appendChild(tab);
  tab.onclick = () => { const trigger = document.querySelector('#pta-export-tool-v1 [data-el="fab"], #menu-trigger'); if (trigger) trigger.click(); };
  const timer = setInterval(() => {
    const panel = document.querySelector('#pta-export-tool-v1 .ptaexp-panel, #export-panel');
    if (!panel) return;
    clearInterval(timer);
    const auth = document.createElement('div'); auth.id = 'sak-extension-auth';
    auth.innerHTML = loggedIn ? '已检测到题库登录状态，可直接使用。' : `请先登录题库后使用。<a href="${SITE}/login?redirect=${encodeURIComponent(location.href)}" target="_blank">登录</a>　<a href="${SITE}/register" target="_blank">注册</a>`;
    panel.insertBefore(auth, panel.firstChild);
    if (!loggedIn) panel.querySelectorAll('button').forEach((b) => { if (!/关闭|回到顶部|打开题库/.test(b.textContent || '')) b.disabled = true; });
  }, 50);
})();
