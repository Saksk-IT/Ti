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
  var keywordTimer = null;
  var listEl = document.getElementById('joinedList');
  var emptyEl = document.getElementById('joinedEmptyState');
  var loadMoreEl = document.getElementById('joinedLoadMore');
  var scopeChipEl = document.getElementById('joinedScopeChip');
  var keywordEl = document.getElementById('joinedKeyword');
  var clearKeywordEl = document.getElementById('joinedClearKeyword');
  var overlayEl = document.getElementById('forumDrawerOverlay');
  var drawerEl = document.getElementById('forumDrawer');

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

  function fetchJson() {
    var params = new URLSearchParams();
    params.set('scope', state.scope);
    params.set('page', String(state.page));
    params.set('per_page', String(state.perPage));
    if (state.keyword) params.set('keyword', state.keyword);
    return fetch('/api/public/banks/joined?' + params.toString(), { credentials: 'same-origin' }).then(function (response) {
      return response.json().catch(function () { return {}; }).then(function (json) {
        if (!response.ok || !json || json.code !== 0) {
          throw new Error((json && json.message) || '加载失败');
        }
        return json.data || {};
      });
    });
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

  function renderScopeChip() {
    if (!scopeChipEl) return;
    var label = state.scope === 'public' ? '公开加入' : state.scope === 'shared' ? '分享加入' : '全部题库';
    if (state.scope === 'all') {
      scopeChipEl.innerHTML = '';
      return;
    }
    scopeChipEl.innerHTML = '<div class="plaza-scope-chip">' + esc(label) + '<button class="chip-close" onclick="resetJoinedScope()">&times;</button></div>';
  }

  function renderCounts(counts) {
    var set = function (id, value) {
      var el = document.getElementById(id);
      if (el) el.textContent = fmtCount(value);
    };
    set('joinedStatAll', counts.all);
    set('joinedStatPublic', counts.public);
    set('joinedStatShared', counts.shared);
    set('joinedStatPage', state.page);
    Array.prototype.slice.call(document.querySelectorAll('.sidebar-board-item[data-scope], #joinedTabs .forum-tab')).forEach(function (node) {
      var key = node.getAttribute('data-scope');
      node.classList.toggle('active', key === state.scope);
    });
    renderScopeChip();
    syncDrawerContent();
  }

  function renderCards(items, append) {
    if (!listEl) return;
    if (!append) listEl.innerHTML = '';
    if (!items || !items.length) return;
    var html = items.map(function (item) {
      var badges = ['<span class="plaza-badge joined">' + esc(item.relation === 'both' ? '公开 + 分享' : item.relation === 'shared' ? '分享加入' : '公开加入') + '</span>'];
      if (item.is_featured) badges.push('<span class="forum-badge forum-badge-feat">精华</span>');
      var coverUrl = String(item.cover_image || '').trim();
      var hasCover = !!coverUrl;
      var coverHtml = hasCover
        ? '<div class="forum-post-cover-thumb"><img src="' + esc(coverUrl) + '" alt="" loading="lazy"></div>'
        : window.renderBankDefaultCover(item.board && item.board.name, '智能题库');
      return '<a class="forum-post-card plaza-bank-card' + (hasCover ? ' has-uploaded-cover' : ' has-default-cover') + '" href="' + esc(item.detail_url) + '">' +
        '<div class="forum-post-header">' +
          '<div class="forum-avatar"></div>' +
          '<div class="forum-post-meta"><span class="forum-user-link">' + esc(item.owner_label || '匿名用户') + '</span><span class="forum-board-tag">' + esc((item.board && item.board.name) || '未分板块') + '</span></div>' +
        '</div>' +
        '<div class="forum-post-title">' + badges.join('') + '<span class="plaza-bank-title-text">' + esc(item.name) + '</span></div>' +
        '<div class="forum-post-preview">' + esc(item.description || '暂无题库简介') + '</div>' +
        '<div class="forum-post-stats">' +
          '<span><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5h16M7 16V8m5 8V4m5 12v-6"/></svg>' + fmtCount(item.question_count) + ' 题</span>' +
          '<span><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>' + fmtCount(item.participants_total) + ' 参与</span>' +
          '<span><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/></svg>' + fmtCount(item.answer_users_7d) + ' 活跃</span>' +
        '</div>' +
        '<div class="plaza-bank-time">' + esc(item.last_joined_at || '-') + '</div>' +
        coverHtml +
      '</a>';
    }).join('');
    listEl.insertAdjacentHTML('beforeend', html);
  }

  function updateEmptyAndLoadMore() {
    var hasItems = state.items.length > 0;
    var hasMore = state.items.length < state.total;
    if (emptyEl) emptyEl.style.display = hasItems ? 'none' : 'block';
    if (loadMoreEl) loadMoreEl.style.display = hasItems && hasMore ? 'block' : 'none';
  }

  function loadJoined(reset) {
    if (state.loading) return;
    state.loading = true;
    if (reset) {
      state.page = 1;
      state.items = [];
      if (listEl) listEl.innerHTML = '';
    }
    fetchJson().then(function (data) {
      var items = data.items || [];
      state.total = Number(data.total || 0) || 0;
      state.items = state.items.concat(items);
      renderCounts(data.relation_counts || {});
      renderCards(items, !reset);
      updateEmptyAndLoadMore();
    }).catch(function () {
      if (reset && listEl) listEl.innerHTML = '';
      if (emptyEl) {
        emptyEl.style.display = 'block';
        emptyEl.textContent = '加载失败，请稍后重试';
      }
      if (loadMoreEl) loadMoreEl.style.display = 'none';
    }).finally(function () {
      state.loading = false;
    });
  }

  window.setJoinedTab = function (el, scope) {
    state.scope = scope || 'all';
    loadJoined(true);
  };

  window.selectJoinedScope = function (el, scope) {
    state.scope = scope || 'all';
    closeDrawer();
    loadJoined(true);
  };

  window.resetJoinedScope = function () {
    state.scope = 'all';
    loadJoined(true);
  };

  window.loadMoreJoined = function () {
    if (state.loading || state.items.length >= state.total) return;
    state.page += 1;
    loadJoined(false);
  };

  if (keywordEl) {
    keywordEl.addEventListener('input', function () {
      state.keyword = String(keywordEl.value || '').trim();
      window.clearTimeout(keywordTimer);
      keywordTimer = window.setTimeout(function () {
        loadJoined(true);
      }, 250);
    });
  }

  if (clearKeywordEl) {
    clearKeywordEl.addEventListener('click', function () {
      state.keyword = '';
      if (keywordEl) keywordEl.value = '';
      loadJoined(true);
    });
  }

  loadJoined(true);
})();
