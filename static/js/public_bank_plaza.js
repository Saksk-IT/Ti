(function () {
  var boot = window.__PUBLIC_BANK_PLAZA__ || {};
  var state = {
    tab: 'latest',
    boardId: '',
    keyword: '',
    page: 1,
    perPage: 12
  };
  var loadSeq = 0;
  var keywordTimer = null;
  var pageEl = document.getElementById('publicBankPlazaPage');
  var sidebarEl = document.getElementById('plazaSidebar');
  var overlayEl = document.getElementById('plazaOverlay');
  var drawerBtnEl = document.getElementById('plazaDrawerBtn');
  var keywordEl = document.getElementById('plazaKeyword');
  var clearKeywordEl = document.getElementById('plazaClearKeyword');
  var tabsEl = document.getElementById('plazaTabs');
  var listEl = document.getElementById('plazaList');
  var feedbackEl = document.getElementById('plazaListFeedback');
  var paginationEl = document.getElementById('plazaPagination');
  var boardsEl = document.getElementById('plazaBoards');
  var hotListEl = document.getElementById('plazaHotList');
  var summaryEl = document.getElementById('plazaSummary');
  var boardSummaryEl = document.getElementById('plazaBoardSummary');
  var activeFiltersEl = document.getElementById('plazaActiveFilters');
  var totalBanksEl = document.getElementById('plazaKpiBanks');
  var totalQuestionsEl = document.getElementById('plazaKpiQuestions');
  var totalNewEl = document.getElementById('plazaKpiNew');
  var totalActiveEl = document.getElementById('plazaKpiActive');

  function fmtCount(value) {
    var num = Number(value || 0) || 0;
    return new Intl.NumberFormat('zh-CN').format(num);
  }

  function escapeHtml(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function buildUrl(path, extra) {
    var params = new URLSearchParams();
    if (state.boardId) params.set('board_id', String(state.boardId));
    if (state.keyword) params.set('keyword', state.keyword);
    Object.keys(extra || {}).forEach(function (key) {
      if (extra[key] !== '' && extra[key] != null) params.set(key, String(extra[key]));
    });
    var query = params.toString();
    return path + (query ? '?' + query : '');
  }

  function setDrawer(open) {
    if (!pageEl) return;
    pageEl.classList.toggle('drawer-open', !!open);
  }

  function setFeedback(message, isError) {
    if (!feedbackEl) return;
    feedbackEl.hidden = !message;
    feedbackEl.textContent = message || '';
    feedbackEl.style.color = isError ? '#ef4444' : '';
  }

  function renderSummary(summary) {
    if (totalBanksEl) totalBanksEl.textContent = fmtCount(summary.total_banks);
    if (totalQuestionsEl) totalQuestionsEl.textContent = fmtCount(summary.total_questions);
    if (totalNewEl) totalNewEl.textContent = fmtCount(summary.new_banks_7d);
    if (totalActiveEl) totalActiveEl.textContent = fmtCount(summary.active_users_7d);
    if (!summaryEl) return;
    summaryEl.innerHTML = [
      ['系统题库', summary.source_breakdown && summary.source_breakdown.system],
      ['用户公开', summary.source_breakdown && summary.source_breakdown.user_public],
      ['板块数', summary.total_boards],
      ['命中结果', summary.total_banks]
    ].map(function (item) {
      return '<div class="pbf-summary-card"><small>' + escapeHtml(item[0]) + '</small><strong>' + fmtCount(item[1]) + '</strong></div>';
    }).join('');
  }

  function renderBoards(items) {
    if (!boardsEl) return;
    var cards = [
      '<button type="button" class="pbf-board-item' + (!state.boardId ? ' active' : '') + '" data-board-id="">' +
      '<strong>全部板块</strong><span>查看全部公开题库</span></button>'
    ];
    (items || []).forEach(function (item) {
      cards.push(
        '<button type="button" class="pbf-board-item' + (String(item.id) === String(state.boardId) ? ' active' : '') + '" data-board-id="' + escapeHtml(item.id) + '">' +
        '<strong>' + escapeHtml(item.name) + '</strong>' +
        '<span>' + fmtCount(item.bank_count) + ' 个题库</span>' +
        '</button>'
      );
    });
    boardsEl.innerHTML = cards.join('');
    if (boardSummaryEl) {
      var active = (items || []).find(function (item) { return String(item.id) === String(state.boardId); });
      boardSummaryEl.textContent = active ? active.name : '全部';
    }
  }

  function renderHot(items) {
    if (!hotListEl) return;
    if (!items || !items.length) {
      hotListEl.innerHTML = '<div class="pbf-hot-item"><strong>暂无数据</strong><p>当前筛选条件下还没有热门题库。</p></div>';
      return;
    }
    hotListEl.innerHTML = items.map(function (item, index) {
      return '<a class="pbf-hot-item" href="' + escapeHtml(item.detail_url) + '">' +
        '<small>TOP ' + (index + 1) + '</small>' +
        '<strong>' + escapeHtml(item.name) + '</strong>' +
        '<p>' + fmtCount(item.participants_total) + ' 参与 · ' + fmtCount(item.answer_users_7d) + ' 人近 7 天活跃</p>' +
        '</a>';
    }).join('');
  }

  function renderFilters() {
    if (!activeFiltersEl) return;
    var pills = [];
    if (state.keyword) pills.push('<span class="pbf-filter-pill">关键词：' + escapeHtml(state.keyword) + '</span>');
    if (state.boardId && boardSummaryEl) pills.push('<span class="pbf-filter-pill">板块：' + escapeHtml(boardSummaryEl.textContent || '全部') + '</span>');
    pills.push('<span class="pbf-filter-pill">视图：' + ({ latest: '最新', hot: '热门', active: '活跃', featured: '精华' }[state.tab] || '最新') + '</span>');
    activeFiltersEl.innerHTML = pills.join('');
  }

  function renderCards(items) {
    if (!listEl) return;
    if (!items || !items.length) {
      listEl.innerHTML = '';
      setFeedback('当前条件下没有匹配题库，试试切换板块或缩短关键词。');
      return;
    }
    setFeedback('');
    listEl.innerHTML = items.map(function (item) {
      var badges = [
        '<span class="pbf-badge">' + escapeHtml(item.source_label) + '</span>',
        '<span class="pbf-badge">' + escapeHtml((item.board && item.board.name) || '未分板块') + '</span>'
      ];
      if (item.is_featured) badges.push('<span class="pbf-badge featured">精华</span>');
      if (boot.logged_in && item.relation && item.relation.is_joined) {
        var relLabel = item.relation.joined_via === 'both' ? '公开 + 分享已加入' : item.relation.joined_via === 'shared' ? '分享加入' : '公开加入';
        badges.push('<span class="pbf-badge joined">' + escapeHtml(relLabel) + '</span>');
      }
      var cover = item.cover_image ? '<img class="pbf-card-cover" src="' + escapeHtml(item.cover_image) + '" alt="" />' : '';
      return '<article class="pbf-card">' +
        '<div class="pbf-card-top">' +
          '<div>' +
            '<h3 class="pbf-card-title">' + escapeHtml(item.name) + '</h3>' +
            '<div class="pbf-card-badges">' + badges.join('') + '</div>' +
          '</div>' + cover +
        '</div>' +
        '<p class="pbf-card-sub">' + escapeHtml(item.description || '暂无题库简介。') + '</p>' +
        '<div class="pbf-card-meta">创建者：' + escapeHtml(item.owner_label || '系统') + '</div>' +
        '<div class="pbf-card-meta">题量 ' + fmtCount(item.question_count) + ' · 总参与 ' + fmtCount(item.participants_total) + ' · 近 7 天活跃 ' + fmtCount(item.answer_users_7d) + '</div>' +
        '<div class="pbf-card-meta">发布时间 ' + escapeHtml(item.published_at || '-') + ' · 最近活跃 ' + escapeHtml(item.last_activity_at || '-') + '</div>' +
        '<div class="pbf-card-actions">' +
          '<span class="pbf-card-meta">热度 ' + fmtCount(item.hot_score.toFixed ? item.hot_score.toFixed(0) : item.hot_score) + '</span>' +
          '<a class="pbf-card-link" href="' + escapeHtml(item.detail_url) + '">进入题库</a>' +
        '</div>' +
      '</article>';
    }).join('');
  }

  function renderPagination(total) {
    if (!paginationEl) return;
    var totalPages = Math.max(1, Math.ceil((Number(total || 0) || 0) / state.perPage));
    if (totalPages <= 1) {
      paginationEl.innerHTML = '';
      return;
    }
    var html = [];
    html.push('<button class="pbf-page-btn" type="button" data-page="' + (state.page - 1) + '"' + (state.page <= 1 ? ' disabled' : '') + '>上一页</button>');
    for (var i = 1; i <= totalPages; i += 1) {
      if (i === 1 || i === totalPages || Math.abs(i - state.page) <= 2) {
        html.push('<button class="pbf-page-btn' + (i === state.page ? ' active' : '') + '" type="button" data-page="' + i + '">' + i + '</button>');
      } else if (Math.abs(i - state.page) === 3) {
        html.push('<span class="pbf-card-meta">…</span>');
      }
    }
    html.push('<button class="pbf-page-btn" type="button" data-page="' + (state.page + 1) + '"' + (state.page >= totalPages ? ' disabled' : '') + '>下一页</button>');
    paginationEl.innerHTML = html.join('');
  }

  function setActiveTab() {
    if (!tabsEl) return;
    Array.prototype.slice.call(tabsEl.querySelectorAll('button[data-tab]')).forEach(function (button) {
      button.classList.toggle('active', button.getAttribute('data-tab') === state.tab);
    });
  }

  function fetchJson(url) {
    return fetch(url, { credentials: 'same-origin' }).then(function (response) {
      return response.json().catch(function () { return {}; }).then(function (json) {
        if (!response.ok || !json || json.code !== 0) {
          throw new Error((json && json.message) || '加载失败');
        }
        return json.data || {};
      });
    });
  }

  function loadAll() {
    var seq = ++loadSeq;
    setActiveTab();
    renderFilters();
    if (listEl) listEl.innerHTML = '<div class="pbf-card">正在加载题库广场…</div>';
    Promise.all([
      fetchJson(buildUrl('/api/public/banks/summary')),
      fetchJson(buildUrl('/api/public/banks/boards')),
      fetchJson(buildUrl('/api/public/banks/hot', { limit: 5 })),
      fetchJson(buildUrl('/api/public/banks/list', { tab: state.tab, page: state.page, per_page: state.perPage }))
    ]).then(function (values) {
      if (seq !== loadSeq) return;
      renderSummary(values[0] || {});
      renderBoards((values[1] && values[1].items) || []);
      renderHot((values[2] && values[2].items) || []);
      renderCards((values[3] && values[3].items) || []);
      renderPagination(values[3] && values[3].total);
    }).catch(function (error) {
      if (seq !== loadSeq) return;
      if (listEl) listEl.innerHTML = '';
      renderHot([]);
      setFeedback((error && error.message) || '加载失败，请稍后重试', true);
      renderPagination(0);
    });
  }

  if (drawerBtnEl) drawerBtnEl.addEventListener('click', function () { setDrawer(true); });
  if (overlayEl) overlayEl.addEventListener('click', function () { setDrawer(false); });
  if (boardsEl) {
    boardsEl.addEventListener('click', function (event) {
      var target = event.target && event.target.closest ? event.target.closest('[data-board-id]') : null;
      if (!target) return;
      state.boardId = target.getAttribute('data-board-id') || '';
      state.page = 1;
      setDrawer(false);
      loadAll();
    });
  }
  if (tabsEl) {
    tabsEl.addEventListener('click', function (event) {
      var target = event.target && event.target.closest ? event.target.closest('[data-tab]') : null;
      if (!target) return;
      state.tab = target.getAttribute('data-tab') || 'latest';
      state.page = 1;
      loadAll();
    });
  }
  if (paginationEl) {
    paginationEl.addEventListener('click', function (event) {
      var target = event.target && event.target.closest ? event.target.closest('[data-page]') : null;
      if (!target || target.disabled) return;
      state.page = Math.max(1, Number(target.getAttribute('data-page') || 1) || 1);
      loadAll();
      try { window.scrollTo({ top: 0, behavior: 'smooth' }); } catch (err) { window.scrollTo(0, 0); }
    });
  }
  if (keywordEl) {
    keywordEl.addEventListener('input', function () {
      state.keyword = String(keywordEl.value || '').trim();
      state.page = 1;
      window.clearTimeout(keywordTimer);
      keywordTimer = window.setTimeout(loadAll, 250);
    });
  }
  if (clearKeywordEl) {
    clearKeywordEl.addEventListener('click', function () {
      state.keyword = '';
      state.page = 1;
      if (keywordEl) keywordEl.value = '';
      loadAll();
    });
  }

  loadAll();
})();
