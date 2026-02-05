(function () {
  'use strict';

  function escapeHtml(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function toNum(v) {
    var n = Number(v || 0);
    return Number.isFinite(n) ? n : 0;
  }

  function fmtCount(v) {
    var n = toNum(v);
    try {
      return n.toLocaleString('zh-CN');
    } catch (e) {
      return String(n);
    }
  }

  function fmtDate(dateStr) {
    var s = String(dateStr || '');
    if (!s) return '—';
    if (/^\d{4}-\d{2}-\d{2}/.test(s)) return s.slice(0, 10);
    return s;
  }

  function debounce(fn, wait) {
    var t = null;
    return function () {
      var args = arguments;
      clearTimeout(t);
      t = setTimeout(function () {
        fn.apply(null, args);
      }, wait);
    };
  }

  var listEl = document.getElementById('plzList');
  var skeletonEl = document.getElementById('plzSkeleton');
  var paginationEl = document.getElementById('plzPagination');
  var kwEl = document.getElementById('plzKeyword');
  var sortEl = document.getElementById('plzSort');
  var typeSeg = document.getElementById('plzTypeSeg');
  var kpiTotalEl = document.getElementById('plzKpiTotal');
  var kpiPageEl = document.getElementById('plzKpiPage');
  var kpiFilterEl = document.getElementById('plzKpiFilter');

  var currentPage = 1;
  var perPage = 18;
  var currentSort = 'newest';
  var currentType = '';
  var loadSeq = 0;
  var lastTotal = 0;

  function setType(next) {
    currentType = (next == null ? '' : String(next)).trim();
    if (typeSeg) {
      Array.prototype.slice.call(typeSeg.querySelectorAll('button[data-type]')).forEach(function (btn) {
        var active = (btn.getAttribute('data-type') || '') === currentType;
        btn.classList.toggle('active', active);
        btn.setAttribute('aria-selected', active ? 'true' : 'false');
      });
    }
  }

  function setKpis(total) {
    if (kpiTotalEl) kpiTotalEl.textContent = fmtCount(total || 0);
    if (kpiPageEl) {
      var totalPages = Math.max(1, Math.ceil((total || 0) / perPage));
      kpiPageEl.textContent = currentPage + '/' + totalPages;
    }
    if (kpiFilterEl) {
      var t = currentType === 'system' ? '系统' : currentType === 'user' ? '用户公开' : '全部';
      var s = currentSort === 'popular' ? '最热' : currentSort === 'questions' ? '题量' : '最新';
      kpiFilterEl.textContent = t + ' · ' + s;
    }
  }

  function buildUrl() {
    var params = new URLSearchParams();
    params.set('page', String(currentPage));
    params.set('per_page', String(perPage));
    params.set('sort', String(currentSort));
    if (currentType) params.set('type', currentType);
    var kw = (kwEl && kwEl.value ? kwEl.value : '').trim();
    if (kw) params.set('keyword', kw);
    return '/api/public/banks?' + params.toString();
  }

  function renderEmpty(msg) {
    if (!listEl) return;
    listEl.className = 'plz-empty';
    listEl.innerHTML = escapeHtml(msg || '暂无数据');
  }

  function renderCards(banks) {
    if (!listEl) return;
    if (!banks || !banks.length) {
      renderEmpty('没有匹配的题库。试试更短的关键词，或切换筛选条件。');
      return;
    }

    var maxHeat = 0;
    banks.forEach(function (b) {
      var isSystem = b && b.bank_type === 'system';
      var heat = isSystem ? toNum(b.question_count) : toNum(b.use_count);
      if (heat > maxHeat) maxHeat = heat;
    });
    if (maxHeat <= 0) maxHeat = 1;

    listEl.className = 'plz-grid';
    listEl.innerHTML = banks
      .map(function (b) {
        var name = escapeHtml((b && b.name) || '未命名题库');
        var desc = ((b && b.description) || '').toString().trim();
        var descHtml = desc ? '<p class="plz-desc">' + escapeHtml(desc) + '</p>' : '';
        var qcnt = toNum(b && b.question_count);
        var isSystem = b && b.bank_type === 'system';
        var typePill = isSystem ? '<span class="plz-pill system">系统</span>' : '<span class="plz-pill user">用户</span>';
        var copyPill = b && b.allow_copy ? '<span class="plz-pill copy">可复制</span>' : '';
        var owner = escapeHtml(((b && b.owner_nickname) || (isSystem ? '系统管理员' : '匿名')).toString());
        var created = fmtDate((b && (b.public_at || b.created_at)) || '');
        var uses = !isSystem ? toNum(b && b.use_count) : 0;
        var heatVal = isSystem ? qcnt : uses;
        var heatPct = Math.round((heatVal / maxHeat) * 100);

        var url = isSystem
          ? '/subjects/' + encodeURIComponent(String(b.id))
          : '/user/banks/' + encodeURIComponent(String(b.id)) + '/practice';

        var meta = '';
        meta += '<span class="plz-pill">' + fmtCount(qcnt) + ' 题</span>';
        if (!isSystem) meta += '<span class="plz-pill">' + fmtCount(uses) + ' 人使用</span>';
        meta += '<span class="plz-pill">创建 ' + escapeHtml(created) + '</span>';

        return (
          '<a class="plz-card" href="' + url + '" aria-label="进入题库：' + name + '">' +
          '<div class="plz-top">' +
          '<div class="plz-name">' + name + '</div>' +
          '<div class="plz-badges">' + typePill + copyPill + '</div>' +
          '</div>' +
          '<div class="plz-owner">创建者：' + owner + '</div>' +
          descHtml +
          '<div class="plz-meta">' + meta + '</div>' +
          '<div class="plz-heat" aria-label="热度"><i style="width:' + heatPct + '%"></i></div>' +
          '</a>'
        );
      })
      .join('');
  }

  function renderPagination(total) {
    if (!paginationEl) return;
    var totalPages = Math.ceil((total || 0) / perPage);
    if (totalPages <= 1) {
      paginationEl.innerHTML = '';
      return;
    }

    function pageBtn(page, label, opts) {
      opts = opts || {};
      var disabled = !!opts.disabled;
      var active = !!opts.active;
      return (
        '<button class="plz-page-btn' +
        (active ? ' active' : '') +
        '" type="button" data-page="' +
        page +
        '"' +
        (disabled ? ' disabled' : '') +
        ' aria-label="' +
        escapeHtml(label) +
        '">' +
        escapeHtml(label) +
        '</button>'
      );
    }

    var html = '';
    html += pageBtn(currentPage - 1, '上一页', { disabled: currentPage <= 1 });

    for (var i = 1; i <= totalPages; i++) {
      var near = i >= currentPage - 2 && i <= currentPage + 2;
      if (i === 1 || i === totalPages || near) {
        html += pageBtn(i, String(i), { active: i === currentPage });
      } else if (i === currentPage - 3 || i === currentPage + 3) {
        html += '<span class="plz-ellipsis" aria-hidden="true">…</span>';
      }
    }

    html += pageBtn(currentPage + 1, '下一页', { disabled: currentPage >= totalPages });
    paginationEl.innerHTML = html;
  }

  async function load() {
    var seq = ++loadSeq;

    if (skeletonEl) skeletonEl.hidden = false;
    if (listEl) {
      listEl.className = '';
      listEl.innerHTML = '';
    }

    try {
      var res = await fetch(buildUrl(), { credentials: 'same-origin' });
      var js = await res.json().catch(function () {
        return {};
      });
      if (seq !== loadSeq) return;

      if (!res.ok || !js || js.code !== 0) throw new Error((js && js.message) || '加载失败');
      var data = js.data || {};
      var banks = data.banks || [];
      lastTotal = toNum(data.total);

      renderCards(banks);
      renderPagination(lastTotal);
      setKpis(lastTotal);
    } catch (e) {
      if (seq !== loadSeq) return;
      renderEmpty((e && e.message) ? e.message : '加载失败，请稍后重试');
      renderPagination(0);
      setKpis(0);
    } finally {
      if (seq === loadSeq && skeletonEl) skeletonEl.hidden = true;
    }
  }

  function goPage(page) {
    var totalPages = Math.max(1, Math.ceil((lastTotal || 0) / perPage));
    var next = Math.max(1, Math.min(Number(page || 1) || 1, totalPages));
    if (next === currentPage) return;
    currentPage = next;
    load();
    try {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch (e) {
      window.scrollTo(0, 0);
    }
  }

  if (kwEl) {
    kwEl.addEventListener(
      'input',
      debounce(function () {
        currentPage = 1;
        load();
      }, 250)
    );
  }

  if (sortEl) {
    sortEl.addEventListener('change', function () {
      currentSort = (sortEl.value || 'newest').trim();
      currentPage = 1;
      load();
    });
  }

  if (typeSeg) {
    typeSeg.addEventListener('click', function (e) {
      var btn = e.target && e.target.closest ? e.target.closest('button[data-type]') : null;
      if (!btn) return;
      setType(btn.getAttribute('data-type') || '');
      currentPage = 1;
      load();
    });
  }

  if (paginationEl) {
    paginationEl.addEventListener('click', function (e) {
      var btn = e.target && e.target.closest ? e.target.closest('button[data-page]') : null;
      if (!btn || btn.disabled) return;
      goPage(btn.getAttribute('data-page'));
    });
  }

  setType('');
  load();
})();
