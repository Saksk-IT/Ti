(function () {
  'use strict';

  var root = null;
  var toastStack = null;
  var activeDialog = null;

  function ensureRoot() {
    if (root) return root;
    root = document.createElement('div');
    root.className = 'app-dialog-root';
    document.body.appendChild(root);
    return root;
  }

  function ensureToastStack() {
    if (toastStack) return toastStack;
    toastStack = document.createElement('div');
    toastStack.className = 'app-dialog-toast-stack';
    document.body.appendChild(toastStack);
    return toastStack;
  }

  function toText(value) {
    if (value == null) return '';
    return String(value);
  }

  function getOptions(input, fallbackTitle) {
    if (input && typeof input === 'object' && !Array.isArray(input)) {
      return Object.assign({}, input);
    }
    return { message: toText(input), title: fallbackTitle || '提示' };
  }

  function getFocusable(container) {
    return Array.prototype.slice.call(container.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    )).filter(function (el) {
      return !el.disabled && el.offsetParent !== null;
    });
  }

  function removeActiveDialog() {
    if (activeDialog && activeDialog.overlay && activeDialog.overlay.parentNode) {
      activeDialog.overlay.parentNode.removeChild(activeDialog.overlay);
    }
    activeDialog = null;
  }

  function showDialog(opts) {
    var options = Object.assign({
      type: 'alert',
      title: '提示',
      message: '',
      confirmText: '确定',
      cancelText: '取消',
      closeOnOverlay: true,
      variant: 'primary',
      defaultValue: ''
    }, opts || {});

    ensureRoot();
    removeActiveDialog();

    var previousFocus = document.activeElement;
    var overlay = document.createElement('div');
    overlay.className = 'app-dialog-overlay';
    overlay.innerHTML = [
      '<section class="app-dialog-panel" role="dialog" aria-modal="true" aria-labelledby="appDialogTitle">',
      '  <header class="app-dialog-header">',
      '    <h2 class="app-dialog-title" id="appDialogTitle"></h2>',
      '    <button type="button" class="app-dialog-close" data-action="cancel" aria-label="关闭">',
      '      <svg viewBox="0 0 24 24" width="18" height="18" fill="none" aria-hidden="true">',
      '        <path d="M18 6 6 18M6 6l12 12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path>',
      '      </svg>',
      '    </button>',
      '  </header>',
      '  <div class="app-dialog-body">',
      '    <p class="app-dialog-message"></p>',
      '  </div>',
      '  <footer class="app-dialog-actions"></footer>',
      '</section>'
    ].join('');

    var panel = overlay.querySelector('.app-dialog-panel');
    var title = overlay.querySelector('.app-dialog-title');
    var message = overlay.querySelector('.app-dialog-message');
    var body = overlay.querySelector('.app-dialog-body');
    var actions = overlay.querySelector('.app-dialog-actions');

    title.textContent = toText(options.title || '提示');
    message.textContent = toText(options.message);

    var input = null;
    if (options.type === 'prompt') {
      input = document.createElement('input');
      input.className = 'app-dialog-input';
      input.type = options.inputType || 'text';
      input.value = toText(options.defaultValue);
      input.placeholder = toText(options.placeholder || '');
      body.appendChild(input);
    }

    function addButton(label, role, variant) {
      var button = document.createElement('button');
      button.type = 'button';
      button.className = 'app-dialog-button';
      button.textContent = label;
      button.dataset.action = role;
      if (role === 'confirm') button.dataset.role = 'primary';
      if (variant) button.dataset.variant = variant;
      actions.appendChild(button);
      return button;
    }

    if (options.type !== 'alert') {
      addButton(toText(options.cancelText || '取消'), 'cancel');
    }
    var confirmBtn = addButton(toText(options.confirmText || '确定'), 'confirm', options.variant === 'danger' ? 'danger' : '');

    return new Promise(function (resolve) {
      var settled = false;

      function finish(result) {
        if (settled) return;
        settled = true;
        document.removeEventListener('keydown', onKeydown, true);
        removeActiveDialog();
        if (previousFocus && typeof previousFocus.focus === 'function') {
          try { previousFocus.focus({ preventScroll: true }); } catch (e) { previousFocus.focus(); }
        }
        resolve(result);
      }

      function confirmValue() {
        if (options.type === 'prompt') return input ? input.value : '';
        return true;
      }

      function cancelValue() {
        if (options.type === 'confirm') return false;
        if (options.type === 'prompt') return null;
        return true;
      }

      function onKeydown(event) {
        if (event.key === 'Escape') {
          event.preventDefault();
          finish(cancelValue());
          return;
        }

        if (event.key !== 'Tab') return;
        var focusables = getFocusable(panel);
        if (!focusables.length) return;
        var first = focusables[0];
        var last = focusables[focusables.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      }

      overlay.addEventListener('click', function (event) {
        var action = event.target && event.target.closest ? event.target.closest('[data-action]') : null;
        if (action) {
          event.preventDefault();
          finish(action.dataset.action === 'confirm' ? confirmValue() : cancelValue());
          return;
        }
        if (options.closeOnOverlay && event.target === overlay) {
          finish(cancelValue());
        }
      });

      if (input) {
        input.addEventListener('keydown', function (event) {
          if (event.key === 'Enter') {
            event.preventDefault();
            finish(confirmValue());
          }
        });
      }

      document.addEventListener('keydown', onKeydown, true);
      root.appendChild(overlay);
      activeDialog = { overlay: overlay };

      window.setTimeout(function () {
        if (input) {
          input.focus();
          input.select();
        } else if (confirmBtn) {
          confirmBtn.focus();
        }
      }, 0);
    });
  }

  function alertDialog(input) {
    var options = getOptions(input, '提示');
    return showDialog(Object.assign({ type: 'alert', confirmText: '知道了' }, options));
  }

  function confirmDialog(input) {
    var options = getOptions(input, '确认操作');
    return showDialog(Object.assign({ type: 'confirm' }, options));
  }

  function promptDialog(message, defaultValue, options) {
    var opts = getOptions(message, '请输入');
    opts.defaultValue = defaultValue == null ? '' : defaultValue;
    return showDialog(Object.assign({ type: 'prompt' }, opts, options || {}));
  }

  function toast(message, type, timeout) {
    var text = toText(message);
    if (!text) return;
    var stack = ensureToastStack();
    var node = document.createElement('div');
    node.className = 'app-dialog-toast';
    node.dataset.type = type || 'info';
    node.textContent = text;
    stack.appendChild(node);
    window.requestAnimationFrame(function () { node.classList.add('show'); });
    window.setTimeout(function () {
      node.classList.remove('show');
      window.setTimeout(function () {
        if (node.parentNode) node.parentNode.removeChild(node);
      }, 180);
    }, timeout || 2600);
  }

  window.AppDialog = {
    alert: alertDialog,
    confirm: confirmDialog,
    prompt: promptDialog,
    toast: toast
  };

  window.appAlert = alertDialog;
  window.appConfirm = confirmDialog;
  window.appPrompt = promptDialog;
  window.appToast = toast;
})();
