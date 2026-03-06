(function () {
  var RECENT_KEY = 'public_bank_plaza_recent_v2';
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
  var searchMetaEl = document.getElementById('plazaSearchMeta');
  var searchRecentEl = document.getElementById('plazaSearchRecent');

  function esc(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function escapeRegExp(value) {
    return String(value || '').replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }

  function fmtCount(value) {
    return new Intl.NumberFormat('zh-CN').format(Number(value || 0) || 0);
  }

  function normalizeKeyword(value) {
    return String(value || '').trim().replace(/\s+/g, ' ');
  }

  function tokenizeKeyword(value) {
    return normalizeKeyword(value)
      .toLowerCase()
      .split(' ')
      .map(function (item) { return item.trim(); })
      .filter(Boolean)
      .slice(0, 4);
  }

  function highlightText(value) {
    var raw = String(value || '');
    var terms = tokenizeKeyword(state.keyword);
    if (!raw || !terms.length) return esc(raw);
    var pattern = new RegExp('(' + terms.map(escapeRegExp).join('|') + ')', 'ig');
    return raw.split(pattern).map(function (part) {
      if (!part) return '';
      var matched = terms.some(function (term) { return term === String(part).toLowerCase(); });
      return matched
        ? '<mark class="plaza-highlight">' + esc(part) + '</mark>'
        : esc(part);
    }).join('');
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

  function syncUrl() {
    var params = new URLSearchParams();
    if (state.tab && state.tab !== 'latest') params.set('tab', state.tab);
    if (state.boardId) params.set('board_id', state.boardId);
    if (state.keyword) params.set('keyword', state.keyword);
    var next = window.location.pathname + (params.toString() ? ('?' + params.toString()) : '');
    window.history.replaceState({}, '', next);
  }

  function restoreStateFromUrl() {
    var params = new URLSearchParams(window.location.search || '');
    var tab = String(params.get('tab') || '').trim();
    var boardId = String(params.get('board_id') || '').trim();
    var keyword = normalizeKeyword(params.get('keyword') || '');
    if (tab && /^(latest|hot|active|featured)$/.test(tab)) state.tab = tab;
    if (boardId) state.boardId = boardId;
    state.keyword = keyword;
    if (keywordEl) keywordEl.value = keyword;
  }

  function readRecentSearches() {
    try {
      var raw = window.localStorage.getItem(RECENT_KEY);
      var data = raw ? JSON.parse(raw) : [];
      return Array.isArray(data) ? data.filter(Boolean).slice(0, 6) : [];
    } catch (error) {
      return [];
    }
  }

  function rememberKeyword(keyword) {
    var current = normalizeKeyword(keyword);
    if (!current || current.length < 2) return;
    try {
      var next = [current].concat(readRecentSearches().filter(function (item) { return item !== current; })).slice(0, 6);
      window.localStorage.setItem(RECENT_KEY, JSON.stringify(next));
    } catch (error) {}
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
    var activeBoard = null;
    var html = ['<li class="sidebar-board-item' + (!state.boardId ? ' active' : '') + '" data-board-id="" data-board-name="全部">全部</li>'];
    (items || []).forEach(function (item) {
      if (String(item.id) === String(state.boardId)) activeBoard = item;
      html.push(
        '<li class="sidebar-board-item' + (String(item.id) === String(state.boardId) ? ' active' : '') +
        '" data-board-id="' + esc(item.id) + '" data-board-name="' + esc(item.name) + '">' + esc(item.name) + '</li>'
      );
    });
    sidebarBoardsEl.innerHTML = html.join('');
    state.boardName = activeBoard ? activeBoard.name : (state.boardId ? state.boardName : '');
    syncDrawerContent();
  }

  function renderHot(items) {
    if (!sidebarHotEl) return;
    if (!items || !items.length) {
      sidebarHotEl.innerHTML = '<div class="sidebar-hot-item plaza-hot-item"><div class="hot-title">暂无热门题库</div><div class="hot-stats">尝试清空关键词或切换板块</div></div>';
      syncDrawerContent();
      return;
    }
    sidebarHotEl.innerHTML = items.map(function (item) {
      return '<a class="sidebar-hot-item plaza-hot-item" href="' + esc(item.detail_url) + '">' +
        '<div class="hot-title">' + highlightText(item.name) + '</div>' +
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

  function renderSearchMeta() {
    if (!searchMetaEl) return;
    var summaryParts = [];
    if (state.keyword) {
      summaryParts.push('搜索');
      summaryParts.push('<strong>“' + esc(state.keyword) + '”</strong>');
    } else if (state.boardId) {
      summaryParts.push('当前板块');
      summaryParts.push('<strong>' + esc(state.boardName || '已选板块') + '</strong>');
    } else {
      summaryParts.push('当前共');
    }
    summaryParts.push('<strong>' + fmtCount(state.total) + '</strong>');
    summaryParts.push('个题库');

    var actions = [];
    if (state.keyword) actions.push('<button type="button" class="plaza-search-link" data-search-action="clear-keyword">清空关键词</button>');
    if (state.boardId) actions.push('<button type="button" class="plaza-search-link" data-search-action="clear-board">清空板块</button>');
    if (state.tab !== 'latest') actions.push('<button type="button" class="plaza-search-link" data-search-action="reset-tab">恢复默认排序</button>');

    searchMetaEl.innerHTML =
      '<div class="plaza-search-summary">' + summaryParts.join(' ') + '</div>' +
      '<div class="plaza-search-actions">' + actions.join('') + '</div>';
  }

  function renderRecentSearches() {
    if (!searchRecentEl) return;
    var recents = readRecentSearches();
    if (state.keyword || !recents.length) {
      searchRecentEl.hidden = true;
      searchRecentEl.innerHTML = '';
      return;
    }
    searchRecentEl.hidden = false;
    searchRecentEl.innerHTML = '<span class="plaza-search-recent-label">最近搜索</span>' + recents.map(function (item) {
      return '<button type="button" class="plaza-search-chip" data-recent-keyword="' + esc(item) + '">' + esc(item) + '</button>';
    }).join('');
  }

  function renderEmptyState() {
    if (!emptyStateEl) return;
    if (state.items.length > 0) {
      emptyStateEl.style.display = 'none';
      emptyStateEl.innerHTML = '当前条件下还没有题库';
      return;
    }
    var html = state.keyword
      ? '没有找到与“' + esc(state.keyword) + '”相关的题库。'
      : '当前条件下还没有题库。';
    var actions = [];
    if (state.keyword) actions.push('<button type="button" class="plaza-search-link" data-empty-action="clear-keyword">清空关键词</button>');
    if (state.boardId) actions.push('<button type="button" class="plaza-search-link" data-empty-action="clear-board">移除板块筛选</button>');
    if (state.tab !== 'latest') actions.push('<button type="button" class="plaza-search-link" data-empty-action="reset-tab">切回最新</button>');
    if (!actions.length) actions.push('<button type="button" class="plaza-search-link" data-empty-action="clear-all">重新查看全部题库</button>');
    html += '<div class="plaza-empty-actions">' + actions.join('') + '</div>';
    emptyStateEl.innerHTML = html;
    emptyStateEl.style.display = 'block';
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
          '<div class="forum-post-meta"><span class="forum-user-link">' + highlightText(item.owner_label || '系统') + '</span><span class="forum-board-tag">' + esc((item.board && item.board.name) || '未分板块') + '</span></div>' +
        '</div>' +
        '<div class="forum-post-title">' + badges.join('') + '<span class="plaza-bank-title-text">' + highlightText(item.name) + '</span></div>' +
        '<div class="forum-post-preview">' + highlightText(item.description || '暂无题库简介') + '</div>' +
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
    renderEmptyState();
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
    syncUrl();
    return fetchJson('/api/public/banks/list', {
      tab: state.tab,
      page: state.page,
      per_page: state.perPage
    }).then(function (data) {
      var items = data.items || [];
      state.total = Number(data.total || 0) || 0;
      if (reset && postsListEl) postsListEl.innerHTML = '';
      state.items = state.items.concat(items);
      if (state.keyword && state.page === 1 && state.total > 0) rememberKeyword(state.keyword);
      renderCards(items, !reset);
      renderSearchMeta();
      renderRecentSearches();
      updateEmptyAndLoadMore();
    }).catch(function () {
      state.total = 0;
      if (reset && postsListEl) postsListEl.innerHTML = '';
      if (emptyStateEl) {
        emptyStateEl.innerHTML = '加载失败，请稍后重试';
        emptyStateEl.style.display = 'block';
      }
      if (loadMoreWrapEl) loadMoreWrapEl.style.display = 'none';
      renderSearchMeta();
      renderRecentSearches();
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
    Array.prototype.slice.call(document.querySelectorAll('.sidebar-board-item')).forEach(function (node) {
      node.classList.remove('active');
    });
    if (el) el.classList.add('active');
    closeDrawer();
    loadSidebar().then(function () { return loadList(true); });
  };

  window.clearBoardSelection = function () {
    state.boardId = '';
    state.boardName = '';
    loadSidebar().then(function () { return loadList(true); });
  };

  window.clearKeywordSearch = function () {
    state.keyword = '';
    if (keywordEl) keywordEl.value = '';
    loadSidebar().then(function () { return loadList(true); });
  };

  window.loadMore = function () {
    if (state.loading || state.items.length >= state.total) return;
    state.page += 1;
    loadList(false);
  };

  if (keywordEl) {
    keywordEl.addEventListener('input', function () {
      state.keyword = normalizeKeyword(keywordEl.value || '');
      window.clearTimeout(keywordTimer);
      keywordTimer = window.setTimeout(function () {
        loadSidebar().then(function () { return loadList(true); });
      }, 250);
    });
    keywordEl.addEventListener('keydown', function (event) {
      if (event.key === 'Enter') {
        event.preventDefault();
        window.clearTimeout(keywordTimer);
        state.keyword = normalizeKeyword(keywordEl.value || '');
        loadSidebar().then(function () { return loadList(true); });
      } else if (event.key === 'Escape') {
        window.clearKeywordSearch();
      }
    });
  }

  if (clearKeywordEl) {
    clearKeywordEl.addEventListener('click', function () {
      window.clearKeywordSearch();
    });
  }

  document.addEventListener('click', function (event) {
    var boardItem = event.target && event.target.closest ? event.target.closest('.sidebar-board-item[data-board-id]') : null;
    if (boardItem && document.getElementById('publicBankPlazaPage')) {
      window.sidebarSelectBoard(boardItem, boardItem.getAttribute('data-board-id') || '', boardItem.getAttribute('data-board-name') || '');
      return;
    }

    var recentItem = event.target && event.target.closest ? event.target.closest('[data-recent-keyword]') : null;
    if (recentItem && document.getElementById('publicBankPlazaPage')) {
      state.keyword = normalizeKeyword(recentItem.getAttribute('data-recent-keyword') || '');
      if (keywordEl) keywordEl.value = state.keyword;
      loadSidebar().then(function () { return loadList(true); });
      return;
    }

    var searchAction = event.target && event.target.closest ? event.target.closest('[data-search-action], [data-empty-action]') : null;
    if (searchAction && document.getElementById('publicBankPlazaPage')) {
      var action = searchAction.getAttribute('data-search-action') || searchAction.getAttribute('data-empty-action') || '';
      if (action === 'clear-keyword') {
        window.clearKeywordSearch();
      } else if (action === 'clear-board') {
        window.clearBoardSelection();
      } else if (action === 'reset-tab') {
        state.tab = 'latest';
        Array.prototype.slice.call(document.querySelectorAll('#forumTabs .forum-tab')).forEach(function (node) {
          node.classList.toggle('active', node.getAttribute('data-tab') === 'latest');
        });
        loadSidebar().then(function () { return loadList(true); });
      } else if (action === 'clear-all') {
        state.keyword = '';
        state.boardId = '';
        state.boardName = '';
        state.tab = 'latest';
        if (keywordEl) keywordEl.value = '';
        Array.prototype.slice.call(document.querySelectorAll('#forumTabs .forum-tab')).forEach(function (node) {
          node.classList.toggle('active', node.getAttribute('data-tab') === 'latest');
        });
        loadSidebar().then(function () { return loadList(true); });
      }
    }
  });

  restoreStateFromUrl();
  Array.prototype.slice.call(document.querySelectorAll('#forumTabs .forum-tab')).forEach(function (node) {
    node.classList.toggle('active', node.getAttribute('data-tab') === state.tab);
  });
  loadSidebar().then(function () { return loadList(true); });
})();
