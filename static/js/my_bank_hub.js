(function () {
  var state = {
    scope: 'all',
    keyword: '',
    page: 1,
    perPage: 10,
    total: 0,
    items: [],
    loading: false
  };
  var boot = window.__MY_BANK_HUB__ || {};
  var keywordTimer = null;
  var toastTimer = null;
  var listEl = document.getElementById('myBankList');
  var emptyEl = document.getElementById('myBankEmptyState');
  var loadMoreEl = document.getElementById('myBankLoadMore');
  var scopeChipEl = document.getElementById('myBankScopeChip');
  var keywordEl = document.getElementById('myBankKeyword');
  var clearKeywordEl = document.getElementById('myBankClearKeyword');
  var overlayEl = document.getElementById('forumDrawerOverlay');
  var drawerEl = document.getElementById('forumDrawer');
  var createModalEl = document.getElementById('createBankModal');
  var createFormEl = document.getElementById('createBankForm');
  var createErrorEl = document.getElementById('createBankError');
  var createNameEl = document.getElementById('createBankName');
  var createDescEl = document.getElementById('createBankDescription');
  var createIsPublicEl = document.getElementById('createBankIsPublic');
  var createPublicSettingsEl = document.getElementById('createBankPublicSettings');
  var createPublicDescEl = document.getElementById('createBankPublicDescription');
  var createSubmitEl = document.getElementById('createBankSubmit');
  var toastEl = document.getElementById('myBankToast');

  function esc(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function fmtCount(value) {
    return new Intl.NumberFormat('zh-CN').format(Number(value || 0) || 0);
  }

  function normalizeKeyword(value) {
    return String(value || '').trim().replace(/\s+/g, ' ');
  }

  function syncDrawerContent() {
    var src = document.getElementById('sidebarContent');
    var dst = document.getElementById('drawerContent');
    if (!src || !dst) return;
    dst.innerHTML = src.innerHTML;
  }

  function setDrawer(open) {
    if (overlayEl) overlayEl.classList.toggle('open', !!open);
    if (drawerEl) drawerEl.classList.toggle('open', !!open);
  }

  window.openDrawer = function () {
    syncDrawerContent();
    setDrawer(true);
  };

  window.closeDrawer = function () {
    setDrawer(false);
  };

  function syncUrl() {
    var params = new URLSearchParams();
    if (state.scope && state.scope !== 'all') params.set('scope', state.scope);
    if (state.keyword) params.set('keyword', state.keyword);
    if (createModalEl && createModalEl.classList.contains('show')) params.set('create', '1');
    var next = window.location.pathname + (params.toString() ? ('?' + params.toString()) : '');
    window.history.replaceState({}, '', next);
  }

  function restoreStateFromUrl() {
    var params = new URLSearchParams(window.location.search || '');
    var scope = String(params.get('scope') || '').trim();
    if (/^(all|created|public|shared)$/.test(scope)) state.scope = scope;
    state.keyword = normalizeKeyword(params.get('keyword') || '');
    if (keywordEl) keywordEl.value = state.keyword;
  }

  function fetchJson() {
    var params = new URLSearchParams();
    params.set('scope', state.scope);
    params.set('page', String(state.page));
    params.set('per_page', String(state.perPage));
    if (state.keyword) params.set('keyword', state.keyword);
    return fetch('/user/banks/api/overview?' + params.toString(), { credentials: 'same-origin' }).then(function (response) {
      return response.json().catch(function () { return {}; }).then(function (json) {
        if (!response.ok || !json || json.code !== 0) {
          throw new Error((json && json.message) || '加载失败');
        }
        return json.data || {};
      });
    });
  }

  function deleteJson(url) {
    return fetch(url, { method: 'DELETE', credentials: 'same-origin', headers: { 'X-Requested-With': 'XMLHttpRequest' } }).then(function (response) {
      return response.json().catch(function () { return {}; }).then(function (json) {
        if (!response.ok || !json || json.code !== 0) {
          throw new Error((json && json.message) || ('请求失败(' + response.status + ')'));
        }
        return json;
      });
    });
  }

  function postJson(url, payload) {
    return fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
      body: JSON.stringify(payload || {})
    }).then(function (response) {
      return response.json().catch(function () { return {}; }).then(function (json) {
        if (!response.ok || !json || json.code !== 0) {
          throw new Error((json && json.message) || ('请求失败(' + response.status + ')'));
        }
        return json;
      });
    });
  }

  function setCreateError(message) {
    if (!createErrorEl) return;
    createErrorEl.textContent = message || '';
    createErrorEl.classList.toggle('show', !!message);
  }

  function toggleCreatePublicSettings() {
    if (!createPublicSettingsEl) return;
    var show = !!(createIsPublicEl && createIsPublicEl.checked);
    createPublicSettingsEl.hidden = !show;
  }

  function showToast(message) {
    if (!toastEl || !message) return;
    toastEl.textContent = message;
    toastEl.classList.add('show');
    window.clearTimeout(toastTimer);
    toastTimer = window.setTimeout(function () {
      toastEl.classList.remove('show');
    }, 1800);
  }

  function openCreateModal() {
    if (!createModalEl) return;
    createModalEl.classList.add('show');
    createModalEl.setAttribute('aria-hidden', 'false');
    setCreateError('');
    toggleCreatePublicSettings();
    syncUrl();
    if (createNameEl) window.setTimeout(function () { createNameEl.focus(); }, 0);
  }

  function closeCreateModal() {
    if (!createModalEl) return;
    createModalEl.classList.remove('show');
    createModalEl.setAttribute('aria-hidden', 'true');
    setCreateError('');
    syncUrl();
  }

  function renderCounts(counts) {
    var set = function (id, value) {
      var el = document.getElementById(id);
      if (el) el.textContent = fmtCount(value);
    };
    set('myBankStatAll', counts.all);
    set('myBankStatCreated', counts.created);
    set('myBankStatPublic', counts.public);
    set('myBankStatShared', counts.shared);

    Array.prototype.slice.call(document.querySelectorAll('.sidebar-board-item[data-scope], #myBankTabs .forum-tab')).forEach(function (node) {
      node.classList.toggle('active', node.getAttribute('data-scope') === state.scope);
    });

    syncDrawerContent();
  }

  function renderScopeChip() {
    if (!scopeChipEl) return;
    var labels = {
      created: '我创建的题库',
      public: '公开加入',
      shared: '分享加入'
    };
    if (!labels[state.scope]) {
      scopeChipEl.innerHTML = '';
      return;
    }
    scopeChipEl.innerHTML = '<div class="plaza-scope-chip">' + esc(labels[state.scope]) + '<button class="chip-close" onclick="resetMyBankScope()">&times;</button></div>';
  }

  function renderCards(items, append) {
    if (!listEl) return;
    if (!append) listEl.innerHTML = '';
    if (!items || !items.length) return;
    var html = items.map(function (item) {
      var badges = [];
      if (item.kind === 'created') {
        badges.push('<span class="plaza-badge joined">我创建的题库</span>');
        badges.push('<span class="plaza-badge ' + (item.visibility_label === '公开' ? 'user' : 'system') + '">' + esc(item.visibility_label) + '</span>');
      } else {
        badges.push('<span class="plaza-badge joined">' + esc(item.source_label || '已加入') + '</span>');
      }
      if (item.is_featured) badges.push('<span class="forum-badge forum-badge-feat">精华</span>');

      var actions = ['<a class="my-bank-card-link primary" href="' + esc(item.detail_url) + '">继续练习</a>'];
      if (item.kind === 'created') {
        actions.push('<a class="my-bank-card-link" href="' + esc(item.question_manage_url) + '">题目管理</a>');
        actions.push('<a class="my-bank-card-link" href="' + esc(item.edit_url || item.manage_url) + '">信息编辑</a>');
      } else {
        actions.push('<button type="button" class="my-bank-card-link" data-leave-source-type="' + esc(item.source_type || 'user') + '" data-leave-id="' + esc(item.id) + '">退出题库</button>');
      }

      var ownerText = item.kind === 'created' ? '我创建的题库' : esc(item.owner_label || '匿名用户');
      var boardText = esc((item.board && item.board.name) || '未分类');
      var timeText = esc(item.updated_at || item.last_joined_at || item.last_activity_at || '-');

      return '<article class="forum-post-card plaza-bank-card my-bank-card">' +
        '<div class="forum-post-header">' +
          '<div class="forum-avatar"></div>' +
          '<div class="forum-post-meta"><span class="forum-user-link">' + ownerText + '</span><span class="forum-board-tag">' + boardText + '</span></div>' +
        '</div>' +
        '<div class="forum-post-title">' + badges.join('') + '<span class="plaza-bank-title-text">' + esc(item.name) + '</span></div>' +
        '<div class="forum-post-preview">' + esc(item.description || '暂无题库简介') + '</div>' +
        '<div class="forum-post-stats">' +
          '<span><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5h16M7 16V8m5 8V4m5 12v-6"/></svg>' + fmtCount(item.question_count) + ' 题</span>' +
          '<span><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>' + fmtCount(item.participants_total) + ' 参与</span>' +
          '<span><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/></svg>' + fmtCount(item.answer_users_7d) + ' 活跃</span>' +
        '</div>' +
        '<div class="plaza-bank-time">' + timeText + '</div>' +
        '<div class="my-bank-card-actions">' + actions.join('') + '</div>' +
      '</article>';
    }).join('');
    listEl.insertAdjacentHTML('beforeend', html);
  }

  function renderEmptyState() {
    if (!emptyEl) return;
    if (state.items.length > 0) {
      emptyEl.style.display = 'none';
      emptyEl.innerHTML = '当前范围下还没有题库';
      return;
    }
    emptyEl.style.display = 'block';
    emptyEl.innerHTML = state.scope === 'created'
      ? '你还没有创建题库，先创建一个吧。'
      : '当前范围下还没有题库。';
  }

  function updateLoadMore() {
    renderEmptyState();
    if (!loadMoreEl) return;
    loadMoreEl.style.display = (state.items.length > 0 && state.items.length < state.total) ? 'block' : 'none';
  }

  function load(reset) {
    if (state.loading) return;
    state.loading = true;
    if (reset) {
      state.page = 1;
      state.items = [];
      if (listEl) listEl.innerHTML = '';
    }
    syncUrl();
    fetchJson().then(function (data) {
      var items = data.items || [];
      state.total = Number(data.total || 0) || 0;
      state.items = state.items.concat(items);
      renderCounts(data.counts || {});
      renderScopeChip();
      renderCards(items, !reset);
      updateLoadMore();
    }).catch(function (error) {
      if (reset && listEl) listEl.innerHTML = '';
      if (emptyEl) {
        emptyEl.style.display = 'block';
        emptyEl.textContent = (error && error.message) || '加载失败，请稍后重试';
      }
      if (loadMoreEl) loadMoreEl.style.display = 'none';
    }).finally(function () {
      state.loading = false;
    });
  }

  window.setMyBankTab = function (el, scope) {
    state.scope = scope || 'all';
    load(true);
  };

  window.selectMyBankScope = function (el, scope) {
    state.scope = scope || 'all';
    closeDrawer();
    load(true);
  };

  window.resetMyBankScope = function () {
    state.scope = 'all';
    load(true);
  };

  window.loadMoreMyBanks = function () {
    if (state.loading || state.items.length >= state.total) return;
    state.page += 1;
    load(false);
  };

  if (keywordEl) {
    keywordEl.addEventListener('input', function () {
      state.keyword = normalizeKeyword(keywordEl.value || '');
      window.clearTimeout(keywordTimer);
      keywordTimer = window.setTimeout(function () {
        load(true);
      }, 250);
    });
  }

  if (clearKeywordEl) {
    clearKeywordEl.addEventListener('click', function () {
      state.keyword = '';
      if (keywordEl) keywordEl.value = '';
      load(true);
    });
  }

  var openCreateBtn = document.getElementById('openCreateBank');
  var closeCreateBtn = document.getElementById('closeCreateBank');
  var createCancelBtn = document.getElementById('createBankCancel');

  if (closeCreateBtn) closeCreateBtn.addEventListener('click', closeCreateModal);
  if (createCancelBtn) createCancelBtn.addEventListener('click', closeCreateModal);
  if (createIsPublicEl) createIsPublicEl.addEventListener('change', toggleCreatePublicSettings);
  if (createModalEl) {
    createModalEl.addEventListener('click', function (event) {
      if (event.target === createModalEl) closeCreateModal();
    });
  }

  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape') {
      if (createModalEl && createModalEl.classList.contains('show')) {
        closeCreateModal();
      }
    }
  });

  if (createFormEl) {
    createFormEl.addEventListener('submit', function (event) {
      event.preventDefault();
      var name = normalizeKeyword(createNameEl && createNameEl.value);
      var description = normalizeKeyword(createDescEl && createDescEl.value);
      var isPublic = !!(createIsPublicEl && createIsPublicEl.checked);
      var publicDescription = normalizeKeyword(createPublicDescEl && createPublicDescEl.value);
      if (!name || name.length < 2 || name.length > 50) {
        setCreateError('题库名称需要 2-50 个字符');
        return;
      }
      if (description.length > 200) {
        setCreateError('题库描述不能超过 200 个字符');
        return;
      }
      if (publicDescription.length > 200) {
        setCreateError('公开简介不能超过 200 个字符');
        return;
      }

      setCreateError('');
      var oldText = createSubmitEl ? createSubmitEl.textContent : '创建';
      if (createSubmitEl) {
        createSubmitEl.disabled = true;
        createSubmitEl.textContent = '创建中...';
      }

      postJson('/user/banks/api', { name: name, description: description }).then(function (createRes) {
        var bankId = createRes && createRes.data && createRes.data.id;
        if (!bankId) throw new Error('创建失败：缺少题库ID');
        if (!isPublic) return null;
        return postJson('/user/banks/api/' + encodeURIComponent(bankId) + '/public', {
          is_public: true,
          public_description: publicDescription
        });
      }).then(function () {
        if (createFormEl) createFormEl.reset();
        toggleCreatePublicSettings();
        closeCreateModal();
        showToast('题库已创建');
        state.scope = 'created';
        load(true);
      }).catch(function (error) {
        setCreateError((error && error.message) || '创建失败');
      }).finally(function () {
        if (createSubmitEl) {
          createSubmitEl.disabled = false;
          createSubmitEl.textContent = oldText;
        }
      });
    });
  }

  document.addEventListener('click', function (event) {
    var leaveBtn = event.target && event.target.closest ? event.target.closest('[data-leave-source-type][data-leave-id]') : null;
    if (!leaveBtn) return;
    var sourceType = String(leaveBtn.getAttribute('data-leave-source-type') || 'user');
    var bankId = String(leaveBtn.getAttribute('data-leave-id') || '');
    if (!bankId) return;
    var ok = window.confirm('确定要退出该题库吗？退出后会从“我的题库”中移除。');
    if (!ok) return;
    leaveBtn.disabled = true;
    deleteJson('/api/public/banks/' + encodeURIComponent(sourceType) + '/' + encodeURIComponent(bankId) + '/join').then(function () {
      showToast('已退出题库');
      load(true);
    }).catch(function (error) {
      showToast((error && error.message) || '退出失败');
      leaveBtn.disabled = false;
    });
  });

  restoreStateFromUrl();
  Array.prototype.slice.call(document.querySelectorAll('#myBankTabs .forum-tab')).forEach(function (node) {
    node.classList.toggle('active', node.getAttribute('data-scope') === state.scope);
  });
  load(true);
})();
