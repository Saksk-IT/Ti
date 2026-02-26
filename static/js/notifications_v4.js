(() => {
  const TYPE_LABEL = { info: '信息', announcement: '公告', reminder: '提醒', warning: '警告' };
  const PAGE_SIZES = [10, 20, 50];

  let listData = [];
  let isLoading = false;
  let _notiFreshLoad = false;

  const state = {
    tab: 'unread',
    pageSize: 10,
    search: '',
    page: { unread: 1, read: 1 },
  };

  function qs(id) {
    return document.getElementById(id);
  }

  function notiSkeletonCard() {
    return '<div class="noti-card" style="pointer-events:none">' +
      '<div class="noti-cardTop"><div style="min-width:0;flex:1"><div class="noti-skel-row" style="width:45%;height:14px"></div><div class="noti-meta" style="margin-top:8px"><div class="noti-skel-row" style="width:48px;height:22px;border-radius:999px"></div><div class="noti-skel-row" style="width:80px;height:10px"></div></div></div></div>' +
      '<div style="margin-top:10px"><div class="noti-skel-row" style="width:90%;margin-bottom:6px"></div><div class="noti-skel-row" style="width:65%"></div></div>' +
      '<div class="noti-cardActions" style="margin-top:12px"><div class="noti-skel-row" style="width:72px;height:36px;border-radius:12px"></div></div>' +
      '</div>';
  }

  function esc(s) {
    const d = document.createElement('div');
    d.textContent = s == null ? '' : String(s);
    return d.innerHTML;
  }

  function normalizeType(t) {
    const raw = (t || 'info').toString().trim().toLowerCase();
    return TYPE_LABEL[raw] ? raw : 'info';
  }

  function fmtTime(s) {
    if (!s) return '';
    try {
      const m = String(s).match(
        /^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})(?::(\d{2}))?$/
      );
      let d;
      // 统一以北京时间为准：后端返回的 "YYYY-MM-DD HH:mm:ss" 视为本地（北京时间）时间
      if (m) d = new Date(+m[1], +m[2] - 1, +m[3], +m[4], +m[5], +(m[6] || 0));
      else d = new Date(s);
      return d.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch (e) {
      return String(s);
    }
  }

  function snippetText(s, maxLen) {
    const t = (s || '').toString().replace(/\s+/g, ' ').trim();
    if (!t) return '';
    if (t.length <= maxLen) return t;
    return t.slice(0, maxLen) + '…';
  }

  function getUrlTab() {
    try {
      const sp = new URLSearchParams(window.location.search || '');
      const t = (sp.get('tab') || '').trim().toLowerCase();
      if (t === 'read' || t === 'unread') return t;
    } catch (e) {}
    const h = (window.location.hash || '').replace('#', '').trim().toLowerCase();
    if (h === 'read' || h === 'unread') return h;
    return '';
  }

  function setUrlTab(tab) {
    try {
      const url = new URL(window.location.href);
      url.searchParams.set('tab', tab);
      url.hash = '';
      window.history.replaceState({}, '', url.toString());
    } catch (e) {}
  }

  function showAlert(msg) {
    const box = qs('alertBox');
    if (!box) return;
    box.textContent = msg || '发生错误';
    box.style.display = 'block';
  }

  function hideAlert() {
    const box = qs('alertBox');
    if (!box) return;
    box.style.display = 'none';
    box.textContent = '';
  }

  function matchesSearch(n, q) {
    const needle = (q || '').toString().trim().toLowerCase();
    if (!needle) return true;
    const hay = `${n?.title || ''} ${n?.content || ''}`.toLowerCase();
    return hay.includes(needle);
  }

  function getTabAllItems(tab) {
    return (listData || []).filter((n) => (tab === 'read' ? !!n.is_read : !n.is_read));
  }

  function getTabFilteredItems(tab) {
    const all = getTabAllItems(tab);
    const q = (state.search || '').trim().toLowerCase();
    if (!q) return all;
    return all.filter((n) => matchesSearch(n, q));
  }

  function getPaged(tab) {
    const items = getTabFilteredItems(tab);
    const total = items.length;
    const pageSize = state.pageSize;
    const totalPages = Math.max(1, Math.ceil(total / pageSize));
    let page = Number(state.page?.[tab] || 1);
    if (!Number.isFinite(page) || page < 1) page = 1;
    if (page > totalPages) page = totalPages;
    state.page[tab] = page;
    const start = (page - 1) * pageSize;
    return { items: items.slice(start, start + pageSize), total, page, totalPages };
  }

  function buildUnreadCard(n) {
    const type = normalizeType(n?.n_type);
    const badge = `<span class="noti-badge ${esc(type)}">${esc(TYPE_LABEL[type])}</span>`;
    const time = `<span class="noti-time">${esc(fmtTime(n?.created_at))}</span>`;

    return `
      <div class="noti-card unread" data-id="${esc(n?.id)}">
        <div class="noti-cardTop">
          <div style="min-width:0;">
            <h3 class="noti-cardTitle">${esc(n?.title || '通知')}</h3>
            <div class="noti-meta" style="margin-top:8px;">${badge}${time}</div>
          </div>
        </div>
        <div class="noti-contentText">${esc(n?.content || '')}</div>
        <div class="noti-cardActions">
          <button class="noti-btn noti-btn-primary" type="button" data-action="mark-read" data-id="${esc(
            n?.id
          )}">标记已读</button>
        </div>
      </div>
    `;
  }

  function buildReadDetails(n) {
    const type = normalizeType(n?.n_type);
    const badge = `<span class="noti-badge ${esc(type)}">${esc(TYPE_LABEL[type])}</span>`;
    const time = `<span class="noti-time">${esc(fmtTime(n?.created_at))}</span>`;
    const snippet = esc(snippetText(n?.content || '', 88) || '（无内容）');
    const full = esc(n?.content || '');

    return `
      <details class="noti-details" data-id="${esc(n?.id)}">
        <summary>
          <div class="noti-sumTop">
            <h3 class="noti-sumTitle">${esc(n?.title || '通知')}</h3>
            <div class="noti-meta">${badge}${time}</div>
          </div>
          <div class="noti-sumSnippet">${snippet}</div>
        </summary>
        <div class="noti-detailsBody">
          <div class="noti-contentText">${full}</div>
        </div>
      </details>
    `;
  }

  function renderPager(tab) {
    const pagerEl = qs(tab === 'read' ? 'readPager' : 'unreadPager');
    if (!pagerEl) return;

    const allCount = getTabAllItems(tab).length;
    const paged = getPaged(tab);

    if (isLoading || paged.total === 0 || paged.totalPages <= 1) {
      pagerEl.style.display = 'none';
      pagerEl.innerHTML = '';
      return;
    }

    const prevDisabled = paged.page <= 1 ? 'disabled' : '';
    const nextDisabled = paged.page >= paged.totalPages ? 'disabled' : '';
    pagerEl.style.display = 'flex';
    pagerEl.innerHTML = `
      <button class="noti-btn" type="button" data-action="page-prev" data-tab="${esc(
        tab
      )}" ${prevDisabled}>上一页</button>
      <div class="noti-pageInfo">
        第 ${paged.page} / ${paged.totalPages} 页 · 匹配 ${paged.total}/${allCount} 条
      </div>
      <button class="noti-btn" type="button" data-action="page-next" data-tab="${esc(
        tab
      )}" ${nextDisabled}>下一页</button>
    `;
  }

  function renderTab(tab) {
    const allCount = getTabAllItems(tab).length;
    const paged = getPaged(tab);
    const listEl = qs(tab === 'read' ? 'readList' : 'unreadList');
    const subEl = qs(tab === 'read' ? 'readSub' : 'unreadSub');

    if (subEl) {
      if (isLoading) subEl.textContent = '加载中…';
      else if (allCount === 0) subEl.textContent = '暂无';
      else if ((state.search || '').trim())
        subEl.textContent = `匹配 ${paged.total}/${allCount} 条 · 第 ${paged.page}/${paged.totalPages} 页`;
      else subEl.textContent = `共 ${allCount} 条 · 第 ${paged.page}/${paged.totalPages} 页`;
    }

    if (!listEl) return;
    if (isLoading) {
      listEl.className = 'noti-list';
      listEl.innerHTML = Array.from({length: 3}, notiSkeletonCard).join('');
      renderPager(tab);
      return;
    }

    if (allCount === 0) {
      listEl.innerHTML =
        tab === 'read'
          ? `<div class="noti-empty">暂无已读通知。处理未读后，这里会出现历史消息。</div>`
          : `<div class="noti-empty">暂无未读通知。你可以切换到“已读”查看历史消息。</div>`;
      renderPager(tab);
      return;
    }

    if (paged.total === 0) {
      listEl.innerHTML = `<div class="noti-empty">未找到匹配的通知。试试更短的关键词，或清除搜索条件。</div>`;
      renderPager(tab);
      return;
    }

    listEl.innerHTML = paged.items
      .map((n) => (tab === 'read' ? buildReadDetails(n) : buildUnreadCard(n)))
      .join('');
    if (_notiFreshLoad) {
      listEl.className = 'noti-list fade-in';
    }
    renderPager(tab);
  }

  function renderCounts() {
    const unread = getTabAllItems('unread').length;
    const read = getTabAllItems('read').length;

    qs('statUnread') && (qs('statUnread').textContent = String(unread));
    qs('statRead') && (qs('statRead').textContent = String(read));
    qs('pillUnread') && (qs('pillUnread').textContent = String(unread));
    qs('pillRead') && (qs('pillRead').textContent = String(read));

    const markAll = qs('btnMarkAllRead');
    if (markAll) {
      const isUnreadTab = state.tab === 'unread';
      markAll.style.display = isUnreadTab ? 'inline-flex' : 'none';
      markAll.disabled = !isUnreadTab || isLoading || unread === 0;
    }
  }

  function setTab(tab, opts) {
    const next = tab === 'read' ? 'read' : 'unread';
    state.tab = next;

    const uTab = qs('tabUnread');
    const rTab = qs('tabRead');
    uTab && uTab.classList.toggle('active', next === 'unread');
    rTab && rTab.classList.toggle('active', next === 'read');
    uTab && uTab.setAttribute('aria-selected', next === 'unread' ? 'true' : 'false');
    rTab && rTab.setAttribute('aria-selected', next === 'read' ? 'true' : 'false');

    const pU = qs('panelUnread');
    const pR = qs('panelRead');
    if (pU) pU.hidden = next !== 'unread';
    if (pR) pR.hidden = next !== 'read';

    if (!opts || opts.updateUrl !== false) setUrlTab(next);
    render();
  }

  function render() {
    renderCounts();
    renderTab('unread');
    renderTab('read');
    _notiFreshLoad = false;

    const clearBtn = qs('btnClearSearch');
    if (clearBtn) clearBtn.style.display = (state.search || '').trim() ? 'inline-flex' : 'none';
  }

  async function fetchList(opts) {
    hideAlert();
    isLoading = true;
    _notiFreshLoad = true;
    render();
    try {
      const res = await fetch('/api/notifications?include_dismissed=1&limit=200', {
        credentials: 'same-origin',
      });
      const js = await res.json().catch(() => ({}));
      if (!res.ok || js.status !== 'success') {
        const msg = (js && (js.message || js.error)) || `加载失败（HTTP ${res.status}）`;
        showAlert(msg);
        isLoading = false;
        render();
        return;
      }

      listData = (js.data || []).map((n) => {
        const nn = Object.assign({}, n || {});
        nn.is_read = !!nn.is_read;
        return nn;
      });
      isLoading = false;

      if (!opts || !opts.preserveTab) {
        const urlTab = getUrlTab();
        if (urlTab) setTab(urlTab, { updateUrl: false });
        else setTab((listData || []).some((n) => !n.is_read) ? 'unread' : 'read', { updateUrl: true });
      } else {
        render();
      }
    } catch (e) {
      isLoading = false;
      showAlert('网络异常：无法加载通知，请稍后重试。');
      render();
    }
  }

  async function markRead(nid, btnEl) {
    const id = Number(nid || 0);
    if (!id) return;
    hideAlert();
    if (btnEl) {
      btnEl.disabled = true;
      btnEl.textContent = '处理中…';
    }
    try {
      const res = await fetch(`/api/notifications/${encodeURIComponent(String(id))}/read`, {
        method: 'POST',
        credentials: 'same-origin',
      });
      const js = await res.json().catch(() => ({}));
      if (!res.ok || (js && js.status && js.status !== 'success')) {
        const msg = (js && (js.message || js.error)) || `操作失败（HTTP ${res.status}）`;
        showAlert(msg);
        await fetchList({ preserveTab: true });
        return;
      }
      listData = (listData || []).map((n) => (Number(n.id) === id ? Object.assign({}, n, { is_read: true }) : n));
      render();
    } catch (e) {
      showAlert('网络异常：标记已读失败，请稍后重试。');
    } finally {
      if (btnEl && document.contains(btnEl)) {
        btnEl.disabled = false;
        btnEl.textContent = '标记已读';
      }
    }
  }

  async function markAllRead() {
    if (isLoading) return;
    const unread = getTabAllItems('unread');
    if (unread.length === 0) return;
    if (!confirm(`将 ${unread.length} 条未读通知全部标记为已读？`)) return;

    const btn = qs('btnMarkAllRead');
    if (btn) {
      btn.disabled = true;
      btn.textContent = '处理中…';
    }
    try {
      let done = 0;
      for (const n of unread) {
        const id = Number(n?.id || 0);
        if (!id) continue;
        done += 1;
        if (btn) btn.textContent = `处理中 ${done}/${unread.length}`;

        const res = await fetch(`/api/notifications/${encodeURIComponent(String(id))}/read`, {
          method: 'POST',
          credentials: 'same-origin',
        });
        const js = await res.json().catch(() => ({}));
        if (!res.ok || (js && js.status && js.status !== 'success')) {
          const msg = (js && (js.message || js.error)) || `部分失败（HTTP ${res.status}）`;
          showAlert(msg);
          break;
        }
        listData = (listData || []).map((x) => (Number(x.id) === id ? Object.assign({}, x, { is_read: true }) : x));
        render();
      }
    } catch (e) {
      showAlert('网络异常：批量标记失败，请稍后重试。');
    } finally {
      if (btn) btn.textContent = '全部标记已读';
      await fetchList({ preserveTab: true });
    }
  }

  function setSearch(val) {
    state.search = (val || '').toString();
    state.page.unread = 1;
    state.page.read = 1;
    render();
  }

  function clearSearch() {
    const input = qs('searchInput');
    if (input) input.value = '';
    setSearch('');
    try {
      input?.focus();
    } catch (e) {}
  }

  function setPageSize(v) {
    const n = Number(v || 0);
    state.pageSize = PAGE_SIZES.includes(n) ? n : 10;
    state.page.unread = 1;
    state.page.read = 1;
    render();
  }

  function changePage(tab, delta) {
    const t = tab === 'read' ? 'read' : 'unread';
    const paged = getPaged(t);
    const next = Math.min(paged.totalPages, Math.max(1, paged.page + delta));
    state.page[t] = next;
    renderTab(t);
    renderPager(t);
  }

  function init() {
    qs('btnRefresh')?.addEventListener('click', () => fetchList({ preserveTab: true }));
    qs('btnMarkAllRead')?.addEventListener('click', markAllRead);

    qs('tabUnread')?.addEventListener('click', () => setTab('unread'));
    qs('tabRead')?.addEventListener('click', () => setTab('read'));

    qs('searchInput')?.addEventListener('input', (e) => setSearch(e?.target?.value));
    qs('searchInput')?.addEventListener('keydown', (e) => {
      if (e?.key === 'Escape') clearSearch();
    });
    qs('btnClearSearch')?.addEventListener('click', clearSearch);
    qs('pageSizeSelect')?.addEventListener('change', (e) => setPageSize(e?.target?.value));

    document.addEventListener('click', (e) => {
      const btn = e.target?.closest?.('button[data-action]');
      if (!btn) return;
      const act = btn.getAttribute('data-action');
      if (!act) return;
      if (act === 'mark-read') {
        const id = btn.getAttribute('data-id');
        markRead(id, btn);
        return;
      }
      if (act === 'page-prev' || act === 'page-next') {
        const tab = btn.getAttribute('data-tab') || state.tab;
        changePage(tab, act === 'page-prev' ? -1 : 1);
      }
    });

    const initTab = getUrlTab();
    if (initTab) state.tab = initTab;

    const initSize = Number(qs('pageSizeSelect')?.value || 10);
    state.pageSize = PAGE_SIZES.includes(initSize) ? initSize : 10;

    setTab(state.tab, { updateUrl: false });
    fetchList({ preserveTab: true });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
