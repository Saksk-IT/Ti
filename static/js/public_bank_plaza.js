(function () {
  var state = {
    tab: 'latest',
    boardId: '',
    boardName: '',
    keyword: '',
    page: 1,
    perPage: 10,
    total: 0,
    loading: false,
    items: []
  };
  var keywordTimer = null;
  var postsListEl = document.getElementById('postsList');
  var emptyStateEl = document.getElementById('emptyState');
  var loadMoreWrapEl = document.getElementById('loadMore');
  var sidebarBoardsEl = document.getElementById('sidebarBoards');
  var sidebarHotEl = document.getElementById('sidebarHotBanks');
  var activeBoardChipEl = document.getElementById('activeBoardChip');
  var keywordEl = document.getElementById('plazaKeyword');
  var clearKeywordEl = document.getElementById('plazaClearKeyword');
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

  function buildParams(extra) {
    var params = new URLSearchParams();
    if (state.boardId) params.set('board_id', state.boardId);
    if (state.keyword) params.set('keyword', state.keyword);
    Object.keys(extra || {}).forEach(function (key) {
      if (extra[key] !== '' && extra[key] != null) params.set(key, String(extra[key]));
    });
    return params.toString();
  }

  function fetchJson(path, extra) {
    var url = path;
    var query = buildParams(extra);
    if (query) url += '?' + query;
    return fetch(url, { credentials: 'same-origin' }).then(function (response) {
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

  function renderSummary(data) {
    var set = function (id, value) {
      var el = document.getElementById(id);
      if (el) el.textContent = fmtCount(value);
    };
    set('statBanks', data.total_banks);
    set('statQuestions', data.total_questions);
    set('statNewBanks', data.new_banks_7d);
    set('statActiveUsers', data.active_users_7d);
  }

  function renderBoards(items) {
    if (!sidebarBoardsEl) return;
    var html = ['<li class="sidebar-board-item' + (!state.boardId ? ' active' : '') + '" data-board-id="" data-board-name="全部">全部</li>'];
    (items || []).forEach(function (item) {
      html.push(
        '<li class="sidebar-board-item' + (String(item.id) === String(state.boardId) ? ' active' : '') +
        '" data-board-id="' + esc(item.id) + '" data-board-name="' + esc(item.name) + '">' + esc(item.name) + '</li>'
      );
    });
    sidebarBoardsEl.innerHTML = html.join('');
    syncDrawerContent();
  }

  function renderHot(items) {
    if (!sidebarHotEl) return;
    if (!items || !items.length) {
      sidebarHotEl.innerHTML = '<div class="sidebar-hot-item plaza-hot-item"><div class="hot-title">暂无热门题库</div><div class="hot-stats">切换板块后再看看</div></div>';
      syncDrawerContent();
      return;
    }
    sidebarHotEl.innerHTML = items.map(function (item) {
      return '<a class="sidebar-hot-item plaza-hot-item" href="' + esc(item.detail_url) + '">' +
        '<div class="hot-title">' + esc(item.name) + '</div>' +
        '<div class="hot-stats"><span>' + fmtCount(item.question_count) + ' 题</span><span>·</span><span>' + fmtCount(item.participants_total) + ' 参与</span></div>' +
      '</a>';
    }).join('');
    syncDrawerContent();
  }

  function renderActiveBoardChip() {
    if (!activeBoardChipEl) return;
    if (!state.boardId) {
      activeBoardChipEl.innerHTML = '';
      return;
    }
    activeBoardChipEl.innerHTML = '<div class="forum-active-board-chip">' + esc(state.boardName || '当前板块') + '<button class="chip-close" onclick="clearBoardSelection()">&times;</button></div>';
  }

  function renderCards(items, append) {
    if (!postsListEl) return;
    if (!append) postsListEl.innerHTML = '';
    if (!items || !items.length) return;
    var html = items.map(function (item) {
      var badges = [];
      badges.push('<span class="plaza-badge ' + (item.source_type === 'system' ? 'system' : 'user') + '">' + esc(item.source_label) + '</span>');
      if (item.is_featured) badges.push('<span class="forum-badge forum-badge-feat">精华</span>');
      if (item.relation && item.relation.is_joined) badges.push('<span class="plaza-badge joined">已加入</span>');
      var hasCover = !!item.cover_image;
      var coverHtml = hasCover
        ? '<div class="forum-post-cover-thumb"><img src="' + esc(item.cover_image) + '" alt=""></div>'
        : '<div class="plaza-bank-cover-fallback">' + esc((item.board && item.board.name) || item.source_label) + '</div>';
      return '<a class="forum-post-card plaza-bank-card' + (hasCover ? '' : ' no-cover') + '" href="' + esc(item.detail_url) + '">' +
        '<div class="forum-post-header">' +
          '<div class="forum-avatar"></div>' +
          '<div class="forum-post-meta"><span class="forum-user-link">' + esc(item.owner_label || '系统') + '</span><span class="forum-board-tag">' + esc((item.board && item.board.name) || '未分板块') + '</span></div>' +
        '</div>' +
        '<div class="forum-post-title">' + badges.join('') + '<span class="plaza-bank-title-text">' + esc(item.name) + '</span></div>' +
        '<div class="forum-post-preview">' + esc(item.description || '暂无题库简介') + '</div>' +
        '<div class="forum-post-stats">' +
          '<span><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5h16M7 16V8m5 8V4m5 12v-6"/></svg>' + fmtCount(item.question_count) + ' 题</span>' +
          '<span><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>' + fmtCount(item.participants_total) + ' 参与</span>' +
          '<span><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/></svg>' + fmtCount(item.answer_users_7d) + ' 活跃</span>' +
        '</div>' +
        '<div class="plaza-bank-time">' + esc(item.published_at || '-') + '</div>' +
        coverHtml +
      '</a>';
    }).join('');
    postsListEl.insertAdjacentHTML('beforeend', html);
  }

  function updateEmptyAndLoadMore() {
    var hasItems = Array.isArray(state.items) && state.items.length > 0;
    var hasMore = state.items.length < state.total;
    if (emptyStateEl) emptyStateEl.style.display = hasItems ? 'none' : 'block';
    if (loadMoreWrapEl) loadMoreWrapEl.style.display = hasItems && hasMore ? 'block' : 'none';
  }

  function loadSidebar() {
    return fetchJson('/api/public/banks/summary').then(function (summary) {
      renderSummary(summary || {});
      return Promise.all([
        fetchJson('/api/public/banks/boards'),
        fetchJson('/api/public/banks/hot', { limit: 5 })
      ]);
    }).then(function (values) {
      renderBoards((values[0] && values[0].items) || []);
      renderHot((values[1] && values[1].items) || []);
      renderActiveBoardChip();
    });
  }

  function loadList(reset) {
    if (state.loading) return Promise.resolve();
    state.loading = true;
    if (reset) {
      state.page = 1;
      state.items = [];
    }
    return fetchJson('/api/public/banks/list', {
      tab: state.tab,
      page: state.page,
      per_page: state.perPage
    }).then(function (data) {
      var items = data.items || [];
      state.total = Number(data.total || 0) || 0;
      if (reset) postsListEl.innerHTML = '';
      state.items = state.items.concat(items);
      renderCards(items, !reset);
      updateEmptyAndLoadMore();
    }).catch(function () {
      if (reset && postsListEl) postsListEl.innerHTML = '';
      if (emptyStateEl) {
        emptyStateEl.style.display = 'block';
        emptyStateEl.textContent = '加载失败，请稍后重试';
      }
      if (loadMoreWrapEl) loadMoreWrapEl.style.display = 'none';
    }).finally(function () {
      state.loading = false;
    });
  }

  window.setTab = function (el, tab) {
    state.tab = tab || 'latest';
    Array.prototype.slice.call(document.querySelectorAll('#forumTabs .forum-tab')).forEach(function (node) {
      node.classList.remove('active');
    });
    if (el) el.classList.add('active');
    loadSidebar().then(function () { return loadList(true); });
  };

  window.sidebarSelectBoard = function (el, boardId, boardName) {
    state.boardId = String(boardId || '');
    state.boardName = boardName || (el ? String(el.textContent || '').trim() : '');
    var all = document.querySelectorAll('.sidebar-board-item');
    Array.prototype.slice.call(all).forEach(function (node) { node.classList.remove('active'); });
    if (el) el.classList.add('active');
    closeDrawer();
    loadSidebar().then(function () { return loadList(true); });
  };

  window.clearBoardSelection = function () {
    state.boardId = '';
    state.boardName = '';
    loadSidebar().then(function () { return loadList(true); });
  };

  window.loadMore = function () {
    if (state.loading || state.items.length >= state.total) return;
    state.page += 1;
    loadList(false);
  };

  if (keywordEl) {
    keywordEl.addEventListener('input', function () {
      state.keyword = String(keywordEl.value || '').trim();
      window.clearTimeout(keywordTimer);
      keywordTimer = window.setTimeout(function () {
        loadSidebar().then(function () { return loadList(true); });
      }, 250);
    });
  }

  if (clearKeywordEl) {
    clearKeywordEl.addEventListener('click', function () {
      state.keyword = '';
      if (keywordEl) keywordEl.value = '';
      loadSidebar().then(function () { return loadList(true); });
    });
  }

  document.addEventListener('click', function (event) {
    var item = event.target && event.target.closest ? event.target.closest('.sidebar-board-item[data-board-id]') : null;
    if (!item || !document.getElementById('publicBankPlazaPage')) return;
    window.sidebarSelectBoard(item, item.getAttribute('data-board-id') || '', item.getAttribute('data-board-name') || '');
  });

  loadSidebar().then(function () { return loadList(true); });
})();
