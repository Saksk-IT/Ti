(function () {
  'use strict';

  function $(sel, root) {
    return (root || document).querySelector(sel);
  }

  function $all(sel, root) {
    return Array.from((root || document).querySelectorAll(sel));
  }

  function safeFocus(el) {
    try {
      if (el && typeof el.focus === 'function') el.focus();
    } catch (e) {}
  }

  function clampSection(section, fallback) {
    const s = String(section || '').trim();
    const allow = new Set(['flow', 'import', 'xxt', 'pta', 'manage', 'word']);
    return allow.has(s) ? s : (fallback || 'flow');
  }

  function initGuide() {
    const overlay = $('#ubGuideOverlay');
    if (!overlay) return;
    const root = document.documentElement;

    if (overlay.parentNode !== document.body) {
      document.body.appendChild(overlay);
    }

    const modal = $('.ubg-modal', overlay);
    const tabs = $all('[data-ubg-tab]', overlay);
    const panes = $all('[data-ubg-pane]', overlay);
    const closeBtns = $all('[data-ubg-close]', overlay);
    const openBtns = $all('[data-ubg-open]').filter((el) => !overlay.contains(el));

    const content = $('#ubgContent', overlay);
    const manageLink = $('[data-ubg-link="manage"]', overlay);
    const wordLink = $('[data-ubg-link="word"]', overlay);

    let lastActive = 'flow';
    let lastFocus = null;

    function setActive(section) {
      const next = clampSection(section, lastActive);
      lastActive = next;
      tabs.forEach((b) => b.classList.toggle('active', b.getAttribute('data-ubg-tab') === next));
      panes.forEach((p) => p.classList.toggle('active', p.getAttribute('data-ubg-pane') === next));
      safeFocus(content);
      try {
        if (content) content.scrollTop = 0;
      } catch (e) {}
    }

    function showOverlay() {
      overlay.classList.add('show');
      overlay.setAttribute('aria-hidden', 'false');
      root.classList.add('user-banks-guide-open');
      document.body.style.overflow = 'hidden';
    }

    function hideOverlay() {
      overlay.classList.remove('show');
      overlay.setAttribute('aria-hidden', 'true');
      root.classList.remove('user-banks-guide-open');
      document.body.style.overflow = '';
      safeFocus(lastFocus);
    }

    function openGuide(section) {
      lastFocus = document.activeElement;
      showOverlay();
      setActive(section);
    }

    function closeGuide() {
      hideOverlay();
    }

    function bindDynamicLinks() {
      const root = document.querySelector('[data-ubm-bank-id]');
      const bankId = root ? String(root.getAttribute('data-ubm-bank-id') || '').trim() : '';
      if (!bankId) {
        if (manageLink) manageLink.classList.add('ubg-hide');
        if (wordLink) wordLink.classList.add('ubg-hide');
        return;
      }

      if (manageLink) {
        manageLink.href = `/user/banks/${encodeURIComponent(bankId)}`;
        manageLink.classList.remove('ubg-hide');
      }

      if (wordLink) {
        wordLink.href = `/user/banks/${encodeURIComponent(bankId)}/questions/import/word`;
        wordLink.classList.remove('ubg-hide');
      }
    }

    tabs.forEach((b) => {
      b.addEventListener('click', function () {
        setActive(b.getAttribute('data-ubg-tab'));
      });
    });

    closeBtns.forEach((b) => b.addEventListener('click', closeGuide));

    overlay.addEventListener('click', function (e) {
      if (e.target === overlay) closeGuide();
    });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && overlay.classList.contains('show')) closeGuide();
    });

    if (modal) {
      modal.addEventListener('click', function (e) {
        const btn = e.target && e.target.closest ? e.target.closest('[data-ubg-open]') : null;
        if (!btn) return;
        const sec = btn.getAttribute('data-ubg-open');
        setActive(sec);
      });
    }

    openBtns.forEach((b) => {
      b.addEventListener('click', function (e) {
        const sec = b.getAttribute('data-ubg-open') || b.getAttribute('data-ubg-guide') || 'flow';
        openGuide(sec);
        e.preventDefault();
      });
    });

    bindDynamicLinks();

    window.openUserBankGuide = openGuide;
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initGuide);
  } else {
    initGuide();
  }
})();
