(function () {
  var state = {
    scope: 'all',
    keyword: '',
    page: 1,
    perPage: 12
  };
  var seq = 0;
  var timer = null;
  var scopeLinksEl = document.getElementById('joinedScopeLinks');
  var keywordEl = document.getElementById('joinedKeyword');
  var clearKeywordEl = document.getElementById('joinedClearKeyword');
  var listEl = document.getElementById('joinedList');
  var feedbackEl = document.getElementById('joinedFeedback');
  var paginationEl = document.getElementById('joinedPagination');
  var filtersEl = document.getElementById('joinedActiveFilters');
  var countAllEl = document.getElementById('joinedCountAll');
  var countPublicEl = document.getElementById('joinedCountPublic');
  var countSharedEl = document.getElementById('joinedCountShared');
  var currentPageEl = document.getElementById('joinedCurrentPage');

  function escapeHtml(value) {
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

  function buildUrl() {
    var params = new URLSearchParams();
    params.set('scope', state.scope);
    params.set('page', String(state.page));
    params.set('per_page', String(state.perPage));
    if (state.keyword) params.set('keyword', state.keyword);
    return '/api/public/banks/joined?' + params.toString();
  }

  function fetchJson() {
    return fetch(buildUrl(), { credentials: 'same-origin' }).then(function (response) {
      return response.json().catch(function () { return {}; }).then(function (json) {
        if (!response.ok || !json || json.code !== 0) {
          throw new Error((json && json.message) || '加载失败');
        }
        return json.data || {};
      });
    });
  }

  function renderFilters() {
    if (!filtersEl) return;
    var scopeLabel = state.scope === 'public' ? '公开加入' : state.scope === 'shared' ? '分享加入' : '全部';
    var pills = ['<span class="pbf-filter-pill">范围：' + scopeLabel + '</span>'];
    if (state.keyword) pills.push('<span class="pbf-filter-pill">关键词：' + escapeHtml(state.keyword) + '</span>');
    filtersEl.innerHTML = pills.join('');
  }

  function renderHeader(data) {
    var counts = data.relation_counts || {};
    if (countAllEl) countAllEl.textContent = fmtCount(counts.all);
    if (countPublicEl) countPublicEl.textContent = fmtCount(counts.public);
    if (countSharedEl) countSharedEl.textContent = fmtCount(counts.shared);
    if (currentPageEl) currentPageEl.textContent = String(data.page || 1);
    if (scopeLinksEl) {
      Array.prototype.slice.call(scopeLinksEl.querySelectorAll('[data-scope]')).forEach(function (el) {
        el.classList.toggle('active', el.getAttribute('data-scope') === state.scope);
      });
    }
  }

  function setFeedback(message, isError) {
    if (!feedbackEl) return;
    feedbackEl.hidden = !message;
    feedbackEl.textContent = message || '';
    feedbackEl.style.color = isError ? '#ef4444' : '';
  }

  function renderCards(items) {
    if (!listEl) return;
    if (!items || !items.length) {
      listEl.innerHTML = '';
      setFeedback('当前范围下还没有已加入题库，先去题库广场挑一个感兴趣的题库吧。');
      return;
    }
    setFeedback('');
    listEl.innerHTML = items.map(function (item) {
      var relationLabel = item.relation === 'both' ? '公开 + 分享' : item.relation === 'shared' ? '分享加入' : '公开加入';
      var badges = [
        '<span class="pbf-badge joined">' + escapeHtml(relationLabel) + '</span>',
        '<span class="pbf-badge">' + escapeHtml((item.board && item.board.name) || '未分板块') + '</span>'
      ];
      if (item.is_featured) badges.push('<span class="pbf-badge featured">精华</span>');
      return '<article class="pbf-card">' +
        '<div class="pbf-card-top">' +
          '<div><h3 class="pbf-card-title">' + escapeHtml(item.name) + '</h3><div class="pbf-card-badges">' + badges.join('') + '</div></div>' +
        '</div>' +
        '<p class="pbf-card-sub">' + escapeHtml(item.description || '暂无题库简介。') + '</p>' +
        '<div class="pbf-card-meta">创建者：' + escapeHtml(item.owner_label || '匿名用户') + ' · 题量 ' + fmtCount(item.question_count) + '</div>' +
        '<div class="pbf-card-meta">总参与 ' + fmtCount(item.participants_total) + ' · 近 7 天活跃 ' + fmtCount(item.answer_users_7d) + '</div>' +
        '<div class="pbf-card-meta">最近加入 ' + escapeHtml(item.last_joined_at || '-') + ' · 最近活跃 ' + escapeHtml(item.last_activity_at || '-') + '</div>' +
        '<div class="pbf-card-actions"><span class="pbf-card-meta">已加入状态保留</span><a class="pbf-card-link" href="' + escapeHtml(item.detail_url) + '">继续练习</a></div>' +
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

  function load() {
    var current = ++seq;
    renderFilters();
    if (listEl) listEl.innerHTML = '<div class="pbf-card">正在加载已加入题库…</div>';
    fetchJson().then(function (data) {
      if (current !== seq) return;
      renderHeader(data);
      renderCards(data.items || []);
      renderPagination(data.total || 0);
    }).catch(function (error) {
      if (current !== seq) return;
      if (listEl) listEl.innerHTML = '';
      setFeedback((error && error.message) || '加载失败，请稍后重试', true);
      renderPagination(0);
    });
  }

  if (scopeLinksEl) {
    scopeLinksEl.addEventListener('click', function (event) {
      var target = event.target && event.target.closest ? event.target.closest('[data-scope]') : null;
      if (!target) return;
      state.scope = target.getAttribute('data-scope') || 'all';
      state.page = 1;
      load();
    });
  }
  if (keywordEl) {
    keywordEl.addEventListener('input', function () {
      state.keyword = String(keywordEl.value || '').trim();
      state.page = 1;
      window.clearTimeout(timer);
      timer = window.setTimeout(load, 250);
    });
  }
  if (clearKeywordEl) {
    clearKeywordEl.addEventListener('click', function () {
      state.keyword = '';
      state.page = 1;
      if (keywordEl) keywordEl.value = '';
      load();
    });
  }
  if (paginationEl) {
    paginationEl.addEventListener('click', function (event) {
      var target = event.target && event.target.closest ? event.target.closest('[data-page]') : null;
      if (!target || target.disabled) return;
      state.page = Math.max(1, Number(target.getAttribute('data-page') || 1) || 1);
      load();
      try { window.scrollTo({ top: 0, behavior: 'smooth' }); } catch (err) { window.scrollTo(0, 0); }
    });
  }

  load();
})();
