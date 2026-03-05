/* ─── Profile V2 — 抖音风格个人主页 JS ─── */
(function () {
  'use strict';

  const CFG = window.__UPF__ || {};
  const IS_SELF = CFG.isSelf;
  const UID = CFG.targetUserId;
  if (!UID) return;

  /* ── State ── */
  let profileData = null;
  let activeTab = 'works';
  let worksFilter = 'all';
  const tabState = {
    works:     { page: 0, hasMore: true, loading: false, loaded: false },
    favorites: { page: 0, hasMore: true, loading: false, loaded: false },
    likes:     { page: 0, hasMore: true, loading: false, loaded: false },
  };
  let modalType = '';
  let modalPage = 0;
  let modalHasMore = false;
  let modalLoading = false;

  /* ── DOM refs ── */
  const $ = (id) => document.getElementById(id);
  const skelEl      = $('upfSkeleton');
  const contentEl   = $('upfContent');
  const avatarEl    = $('upfAvatar');
  const avatarTextEl= $('upfAvatarText');
  const nameEl      = $('upfName');
  const sigEl       = $('upfSignature');
  const collegeEl   = $('upfCollege');
  const followingCntEl = $('upfFollowingCount');
  const followerCntEl  = $('upfFollowerCount');
  const likesRecvEl    = $('upfLikesReceived');
  const followBtnEl    = $('upfFollowBtn');
  const msgBtnEl       = $('upfMsgBtn');
  const tabFavEl       = $('upfTabFav');
  const tabLikeEl      = $('upfTabLike');
  const filterEl       = $('upfFilter');
  const privGearEl     = $('upfPrivacyGear');
  const privPanelEl    = $('upfPrivacyPanel');
  const privFavEl      = $('upfPrivFav');
  const privLikeEl     = $('upfPrivLike');
  const modalOverlay   = $('upfModalOverlay');
  const modalTitleEl   = $('upfModalTitle');
  const modalListEl    = $('upfModalList');
  const modalCloseEl   = $('upfModalClose');
  const ICON_COMMENT = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z"/></svg>';
  const ICON_HEART = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/></svg>';
  const ICON_QUESTIONS = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>';
  const ICON_USAGE = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="8.5" cy="7" r="4"/><path d="M20 8v6"/><path d="M23 11h-6"/></svg>';

  /* ── Helpers ── */
  function fmtCount(n) {
    if (n == null) return '-';
    n = Number(n);
    if (n >= 10000) return (n / 10000).toFixed(1) + 'w';
    if (n >= 1000) return (n / 1000).toFixed(1) + 'k';
    return String(n);
  }

  function fmtDateYmd(raw) {
    if (!raw) return '';
    var d = new Date(raw);
    if (Number.isNaN(d.getTime())) {
      return String(raw).slice(0, 10);
    }
    var y = d.getFullYear();
    var m = String(d.getMonth() + 1).padStart(2, '0');
    var day = String(d.getDate()).padStart(2, '0');
    return y + '-' + m + '-' + day;
  }

  function closeAllCardMenus() {
    document.querySelectorAll('.upf-card-owner-actions.open').forEach(function (el) {
      el.classList.remove('open');
    });
  }

  function canManageItem(item) {
    if (!IS_SELF || activeTab !== 'works' || !item) return false;
    return item.item_type === 'post' || item.item_type === 'bank';
  }

  function getManageConfig(item) {
    var isBank = item && item.item_type === 'bank';
    return {
      label: isBank ? '题库' : '帖子',
      editUrl: isBank ? ('/user/banks/' + item.id + '/edit') : ('/forum/post/' + item.id + '/edit'),
      deleteUrl: isBank ? ('/user/banks/api/' + item.id) : ('/api/forum/posts/' + item.id),
    };
  }

  function resetWorksList() {
    tabState.works = { page: 0, hasMore: true, loading: false, loaded: false };
    var grid = $('upfGridWorks');
    var loadMoreEl = $('upfLoadMoreWorks');
    if (grid) grid.innerHTML = '';
    if (loadMoreEl) loadMoreEl.textContent = '';
  }

  async function deleteManagedItem(item) {
    var config = getManageConfig(item);
    if (!window.confirm('确认删除该' + config.label + '？删除后不可恢复。')) return;
    try {
      var res = await fetch(config.deleteUrl, { method: 'DELETE', credentials: 'include' });
      var js = await res.json().catch(function () { return {}; });
      var ok = res.ok && (js.status === 'success' || js.success || js.code === 0);
      if (!ok) {
        alert((js && js.message) ? js.message : '删除失败');
        return;
      }
      resetWorksList();
      loadTabContent('works');
    } catch (e) {
      alert('删除失败，请稍后重试');
    }
  }

  async function api(url) {
    const res = await fetch(url, { credentials: 'include' });
    return res.json().catch(() => ({}));
  }

  async function apiPost(url, body) {
    const res = await fetch(url, {
      method: 'POST', credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    return res.json().catch(() => ({}));
  }

  /* ── Profile load ── */
  async function loadProfile() {
    const js = await api('/api/user/' + UID + '/profile');
    if (!js || js.status !== 'success' || !js.data) return;
    profileData = js.data;
    renderProfile();
    skelEl.style.display = 'none';
    contentEl.style.display = '';
    loadTabContent('works');
  }
  /* ── Render profile ── */
  function renderProfile() {
    const d = profileData;
    if (!d) return;

    // Avatar
    if (d.avatar) {
      avatarEl.style.backgroundImage = 'url(' + d.avatar + ')';
      avatarEl.style.backgroundSize = 'cover';
      avatarEl.style.backgroundPosition = 'center';
      if (avatarTextEl) avatarTextEl.style.display = 'none';
    } else {
      const letter = (d.username || 'U').charAt(0).toUpperCase();
      if (avatarTextEl) { avatarTextEl.textContent = letter; avatarTextEl.style.display = ''; }
    }

    nameEl.textContent = d.username || '-';
    sigEl.textContent = d.signature || '暂无签名';
    collegeEl.textContent = d.college ? '学院: ' + d.college : '';

    followingCntEl.textContent = fmtCount(d.following_count);
    followerCntEl.textContent = fmtCount(d.follower_count);
    likesRecvEl.textContent = fmtCount(d.total_likes_received);

    // Follow button (other user view)
    if (!IS_SELF && followBtnEl) {
      updateFollowBtn(d);
    }
    // Message button
    if (!IS_SELF && msgBtnEl) {
      msgBtnEl.href = '/chat?to=' + d.id;
    }

    // Privacy tabs
    if (!IS_SELF) {
      if (d.privacy.favorites === 'private' && tabFavEl) {
        tabFavEl.innerHTML = '收藏 <span class="upf-tab-lock">&#128274;</span>';
      }
      if (d.privacy.likes === 'private' && tabLikeEl) {
        tabLikeEl.innerHTML = '喜欢 <span class="upf-tab-lock">&#128274;</span>';
      }
    }

    // Privacy toggles (self view)
    if (IS_SELF && privFavEl) {
      privFavEl.checked = d.privacy.favorites !== 'private';
    }
    if (IS_SELF && privLikeEl) {
      privLikeEl.checked = d.privacy.likes !== 'private';
    }
  }

  function updateFollowBtn(d) {
    if (!followBtnEl) return;
    if (d.mutual) {
      followBtnEl.setAttribute('data-state', 'mutual');
      followBtnEl.textContent = '互相关注';
    } else if (d.i_follow) {
      followBtnEl.setAttribute('data-state', 'following');
      followBtnEl.textContent = '已关注';
    } else {
      followBtnEl.setAttribute('data-state', 'none');
      followBtnEl.textContent = '+ 关注';
    }
  }

  /* ── Follow toggle ── */
  async function toggleFollow() {
    if (!profileData || IS_SELF) return;
    const isFollowing = profileData.i_follow;
    const url = isFollowing ? '/api/user/unfollow' : '/api/user/follow';
    const js = await apiPost(url, { target_user_id: UID });
    if (js && (js.status === 'success' || js.success)) {
      profileData.i_follow = !isFollowing;
      if (!isFollowing && profileData.follows_me) profileData.mutual = true;
      else profileData.mutual = false;
      profileData.follower_count += isFollowing ? -1 : 1;
      followerCntEl.textContent = fmtCount(profileData.follower_count);
      updateFollowBtn(profileData);
    }
  }

  /* ── Tab switching ── */
  function switchTab(tab) {
    if (tab === activeTab) return;
    closeAllCardMenus();
    activeTab = tab;
    document.querySelectorAll('.upf-tab').forEach(function (el) {
      el.classList.toggle('active', el.getAttribute('data-tab') === tab);
    });
    document.querySelectorAll('.upf-panel').forEach(function (el) {
      el.classList.toggle('active', el.getAttribute('data-tab') === tab);
    });
    updateFilterVisibility();
    var st = tabState[tab];
    if (!st.loaded) loadTabContent(tab);
  }

  function updateFilterVisibility() {
    if (!filterEl) return;
    filterEl.classList.toggle('upf-filter-hidden', activeTab !== 'works');
  }

  /* ── Works sub-filter ── */
  function switchWorksFilter(type) {
    if (type === worksFilter) return;
    closeAllCardMenus();
    worksFilter = type;
    document.querySelectorAll('.upf-filter-btn').forEach(function (el) {
      el.classList.toggle('active', el.getAttribute('data-filter') === type);
    });
    // Reset works tab state
    resetWorksList();
    loadTabContent('works');
  }
  /* ── Load tab content ── */
  async function loadTabContent(tab) {
    var st = tabState[tab];
    if (st.loading || !st.hasMore) return;
    st.loading = true;

    var nextPage = st.page + 1;
    var urlMap = {
      works: '/api/user/' + UID + '/works?page=' + nextPage + '&per_page=12&type=' + worksFilter,
      favorites: '/api/user/' + UID + '/favorites?page=' + nextPage + '&per_page=12',
      likes: '/api/user/' + UID + '/likes?page=' + nextPage + '&per_page=12',
    };

    var gridEl = $('upfGrid' + tab.charAt(0).toUpperCase() + tab.slice(1));
    var loadMoreEl = $('upfLoadMore' + tab.charAt(0).toUpperCase() + tab.slice(1));

    var js = await api(urlMap[tab]);
    st.loading = false;
    st.loaded = true;

    // Privacy blocked
    if (js && js.code === 'PRIVATE') {
      if (gridEl) gridEl.innerHTML = '<div class="upf-private"><div class="upf-private-icon">&#128274;</div>该用户已将' + (tab === 'favorites' ? '收藏' : '喜欢') + '设为私密</div>';
      if (loadMoreEl) loadMoreEl.textContent = '';
      st.hasMore = false;
      return;
    }

    if (!js || js.status !== 'success' || !js.data) {
      st.hasMore = false;
      if (loadMoreEl) loadMoreEl.textContent = '加载失败';
      return;
    }

    var data = js.data;
    var items = data.items || [];
    st.page = nextPage;
    st.hasMore = !!data.has_more;

    if (items.length === 0 && st.page === 1) {
      if (gridEl) gridEl.innerHTML = '<div class="upf-empty"><div class="upf-empty-icon">&#128196;</div>暂无内容</div>';
    } else {
      items.forEach(function (item) {
        if (gridEl) gridEl.appendChild(renderCard(item));
      });
    }

    if (loadMoreEl) {
      loadMoreEl.textContent = st.hasMore ? '' : (items.length > 0 ? '没有更多了' : '');
    }
  }

  /* ── Render card ── */
  function renderCard(item) {
    var card = document.createElement('div');
    var isBank = item.item_type === 'bank';
    var coverUrl = String(item.cover_image || '').trim();
    var hasCover = !isBank && !!coverUrl;
    var showActions = canManageItem(item);
    var manageConfig = getManageConfig(item);
    var typeLabel = isBank ? '题库' : '帖子';
    var typeClass = isBank ? ' upf-card-type-bank' : ' upf-card-type-post';
    var titleText = escHtml(item.name || '无标题');
    var rawDesc = String(item.description || '').trim();
    var descText = escHtml(rawDesc || (isBank ? '暂无题库简介' : '暂无内容预览'));
    var stat1Label = String(item.stat1_label || '').trim();
    var stat2Label = String(item.stat2_label || '').trim();
    var stat1Text = escHtml(String(item.stat1 || 0) + (stat1Label ? ' ' + stat1Label : ''));
    var stat2Text = escHtml(String(item.stat2 || 0) + (stat2Label ? ' ' + stat2Label : ''));
    var dateText = escHtml(fmtDateYmd(item.created_at) || '--');
    var stat1Icon = isBank ? ICON_QUESTIONS : ICON_HEART;
    var stat2Icon = isBank ? ICON_USAGE : ICON_COMMENT;
    card.className = 'upf-card ' + (isBank ? 'upf-card-bank' : 'upf-card-post') + (hasCover ? ' upf-card-has-cover' : ' upf-card-no-cover');
    card.setAttribute('role', 'article');

    var actionHtml = '';
    if (showActions) {
      actionHtml = '<div class="upf-card-owner-actions">' +
        '<button type="button" class="upf-card-owner-toggle" title="' + manageConfig.label + '管理" aria-label="' + manageConfig.label + '管理">' +
          '<svg width="16" height="16" viewBox="0 0 24 24" fill="none"><circle cx="5" cy="12" r="1.6" fill="currentColor"/><circle cx="12" cy="12" r="1.6" fill="currentColor"/><circle cx="19" cy="12" r="1.6" fill="currentColor"/></svg>' +
        '</button>' +
        '<div class="upf-card-owner-menu">' +
          '<button type="button" data-action="edit">编辑</button>' +
          '<button type="button" class="danger" data-action="delete">删除</button>' +
        '</div>' +
      '</div>';
    }

    var coverHtml = hasCover
      ? ('<div class="upf-card-cover"><img src="' + escHtml(coverUrl) + '" alt="" loading="lazy"></div>')
      : '';

    card.innerHTML = actionHtml +
      '<div class="upf-card-head"><span class="upf-card-type' + typeClass + '">' + typeLabel + '</span></div>' +
      '<div class="upf-card-title">' + titleText + '</div>' +
      '<div class="upf-card-desc">' + descText + '</div>' +
      '<div class="upf-card-meta">' +
        '<span>' + stat1Icon + '<span>' + stat1Text + '</span></span>' +
        '<span>' + stat2Icon + '<span>' + stat2Text + '</span></span>' +
      '</div>' +
      '<div class="upf-card-time">' + dateText + '</div>' +
      coverHtml;

    card.addEventListener('click', function () {
      if (isBank) {
        window.location.href = '/user/banks/' + item.id + '/practice';
      } else {
        window.location.href = '/forum/post/' + item.id;
      }
    });

    if (showActions) {
      var ownerHost = card.querySelector('.upf-card-owner-actions');
      var toggleBtn = card.querySelector('.upf-card-owner-toggle');
      var editBtn = card.querySelector('[data-action="edit"]');
      var deleteBtn = card.querySelector('[data-action="delete"]');

      if (ownerHost) {
        ownerHost.addEventListener('click', function (event) {
          event.stopPropagation();
        });
      }
      if (toggleBtn && ownerHost) {
        toggleBtn.addEventListener('click', function (event) {
          event.stopPropagation();
          var shouldOpen = !ownerHost.classList.contains('open');
          closeAllCardMenus();
          if (shouldOpen) ownerHost.classList.add('open');
        });
      }
      if (editBtn) {
        editBtn.addEventListener('click', function (event) {
          event.stopPropagation();
          closeAllCardMenus();
          window.location.href = manageConfig.editUrl;
        });
      }
      if (deleteBtn) {
        deleteBtn.addEventListener('click', function (event) {
          event.stopPropagation();
          closeAllCardMenus();
          deleteManagedItem(item);
        });
      }
    }
    return card;
  }

  function escHtml(s) {
    var d = document.createElement('div');
    d.textContent = s || '';
    return d.innerHTML;
  }
  /* ── Follow/Follower modal ── */
  function openFollowModal(type) {
    modalType = type;
    modalPage = 0;
    modalHasMore = true;
    modalLoading = false;
    if (modalTitleEl) modalTitleEl.textContent = type === 'following' ? '关注列表' : '粉丝列表';
    if (modalListEl) modalListEl.innerHTML = '';
    if (modalOverlay) modalOverlay.classList.add('open');
    loadMoreFollowList();
  }

  function closeFollowModal() {
    if (modalOverlay) modalOverlay.classList.remove('open');
    modalType = '';
  }

  async function loadMoreFollowList() {
    if (modalLoading || !modalHasMore) return;
    modalLoading = true;
    var nextPage = modalPage + 1;
    var url = '/api/user/' + UID + '/' + modalType + '?page=' + nextPage + '&per_page=20';
    var js = await api(url);
    modalLoading = false;

    if (!js || js.status !== 'success' || !js.data) {
      modalHasMore = false;
      return;
    }

    var users = js.data.users || [];
    modalPage = nextPage;
    var total = js.data.total || 0;
    modalHasMore = (modalPage * 20) < total;

    if (users.length === 0 && modalPage === 1) {
      if (modalListEl) modalListEl.innerHTML = '<div class="upf-modal-empty">暂无</div>';
      return;
    }

    users.forEach(function (u) {
      if (modalListEl) modalListEl.appendChild(renderModalItem(u));
    });

    if (modalHasMore) {
      var moreEl = document.createElement('div');
      moreEl.className = 'upf-modal-load-more';
      moreEl.textContent = '加载更多';
      moreEl.addEventListener('click', function () {
        moreEl.remove();
        loadMoreFollowList();
      });
      if (modalListEl) modalListEl.appendChild(moreEl);
    }
  }

  function renderModalItem(u) {
    var item = document.createElement('div');
    item.className = 'upf-modal-item';

    var avatarHtml = '';
    if (u.avatar) {
      avatarHtml = '<div class="upf-modal-avatar"><img src="' + escHtml(u.avatar) + '" alt=""></div>';
    } else {
      var letter = (u.username || 'U').charAt(0).toUpperCase();
      avatarHtml = '<div class="upf-modal-avatar"><span class="upf-modal-avatar-text">' + letter + '</span></div>';
    }

    item.innerHTML = avatarHtml +
      '<div class="upf-modal-user-info">' +
        '<div class="upf-modal-username">' + escHtml(u.username || '-') + '</div>' +
      '</div>';

    // Click to visit profile
    item.style.cursor = 'pointer';
    item.addEventListener('click', function () {
      window.location.href = '/user/' + u.id;
    });
    return item;
  }

  /* ── Privacy settings (self only) ── */
  function togglePrivacyPanel() {
    if (privPanelEl) privPanelEl.classList.toggle('open');
  }

  async function savePrivacy() {
    if (!IS_SELF) return;
    var favVal = privFavEl && privFavEl.checked ? 'public' : 'private';
    var likeVal = privLikeEl && privLikeEl.checked ? 'public' : 'private';
    await apiPost('/api/profile/privacy', {
      privacy_favorites: favVal,
      privacy_likes: likeVal,
    });
  }

  /* ── IntersectionObserver for infinite scroll ── */
  function setupObserver(tab) {
    var loadMoreEl = $('upfLoadMore' + tab.charAt(0).toUpperCase() + tab.slice(1));
    if (!loadMoreEl) return;
    var observer = new IntersectionObserver(function (entries) {
      if (entries[0].isIntersecting && tabState[tab].hasMore && !tabState[tab].loading) {
        loadTabContent(tab);
      }
    }, { rootMargin: '200px' });
    observer.observe(loadMoreEl);
  }

  /* ── Event binding ── */
  function init() {
    // Tabs
    document.querySelectorAll('.upf-tab').forEach(function (el) {
      el.addEventListener('click', function () {
        switchTab(el.getAttribute('data-tab'));
      });
    });

    // Works sub-filter
    document.querySelectorAll('.upf-filter-btn').forEach(function (el) {
      el.addEventListener('click', function () {
        switchWorksFilter(el.getAttribute('data-filter'));
      });
    });

    // Follow button
    if (followBtnEl) followBtnEl.addEventListener('click', toggleFollow);

    // Stats → modal
    var statFollowing = $('upfStatFollowing');
    var statFollowers = $('upfStatFollowers');
    if (statFollowing) statFollowing.addEventListener('click', function () { openFollowModal('following'); });
    if (statFollowers) statFollowers.addEventListener('click', function () { openFollowModal('followers'); });

    // Modal close
    if (modalCloseEl) modalCloseEl.addEventListener('click', closeFollowModal);
    if (modalOverlay) modalOverlay.addEventListener('click', function (e) {
      if (e.target === modalOverlay) closeFollowModal();
    });

    // Privacy
    if (privGearEl) privGearEl.addEventListener('click', togglePrivacyPanel);
    if (privFavEl) privFavEl.addEventListener('change', savePrivacy);
    if (privLikeEl) privLikeEl.addEventListener('change', savePrivacy);

    // Close privacy panel on outside click
    document.addEventListener('click', function (e) {
      var target = e.target;
      if (!(target && target.closest && target.closest('.upf-card-owner-actions'))) {
        closeAllCardMenus();
      }
      if (privPanelEl && privPanelEl.classList.contains('open')) {
        if (!privPanelEl.contains(e.target) && e.target !== privGearEl) {
          privPanelEl.classList.remove('open');
        }
      }
    });

    // Infinite scroll observers
    setupObserver('works');
    setupObserver('favorites');
    setupObserver('likes');
    updateFilterVisibility();

    // Load profile
    loadProfile();
  }

  init();
})();
