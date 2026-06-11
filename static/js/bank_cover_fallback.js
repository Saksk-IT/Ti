(function () {
  function esc(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  window.renderBankDefaultCover = function (label, fallbackLabel) {
    var coverLabel = String(label || fallbackLabel || '智能题库').trim() || '智能题库';
    return '<div class="plaza-bank-cover-fallback" aria-hidden="true">' +
      '<div class="plaza-cover-emblem">' +
        '<svg viewBox="0 0 24 24" fill="none"><path d="M4.8 5.6c0-.9.7-1.6 1.6-1.6h4.1c1 0 1.9.4 2.5 1.1.6-.7 1.5-1.1 2.5-1.1h4.1c.9 0 1.6.7 1.6 1.6v12.2c0 .7-.6 1.2-1.3 1.1l-3.4-.5c-1.2-.2-2.4.1-3.4.8l-.8.5-.8-.5c-1-.7-2.2-1-3.4-.8l-3.4.5c-.7.1-1.3-.4-1.3-1.1V5.6Z" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/><path d="M12 5.5v13.2M7.5 8.2h2.6M7.5 11h2.6M15.9 8.2h2.6M15.9 11h2.6" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>' +
      '</div>' +
      '<div class="plaza-cover-copy">' +
        '<span class="plaza-cover-kicker">Sak AI</span>' +
        '<strong class="plaza-cover-title">智能题库</strong>' +
        '<span class="plaza-cover-board">' + esc(coverLabel) + '</span>' +
      '</div>' +
    '</div>';
  };
})();
