(function () {
  var boot = window.__PUBLIC_BANK_CARD__ || {};
  var titleEl = document.getElementById('bankCardTitle');
  var descEl = document.getElementById('bankCardDesc');
  var coverEl = document.getElementById('bankCardCover');
  var badgesEl = document.getElementById('bankCardBadges');
  var metaEl = document.getElementById('bankCardMeta');
  var richEl = document.getElementById('bankCardRich');
  var joinModeEl = document.getElementById('bankCardJoinMode');
  var joinNoteEl = document.getElementById('bankCardJoinNote');
  var actionsEl = document.getElementById('bankCardActions');
  var infoListEl = document.getElementById('bankCardInfoList');
  var current = null;

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
    var url = '/api/public/banks/card/' + encodeURIComponent(String(boot.source_type || 'user')) + '/' + encodeURIComponent(String(boot.bank_id || 0));
    return fetch(url, { credentials: 'same-origin' }).then(function (response) {
      return response.json().catch(function () { return {}; }).then(function (json) {
        if (!response.ok || !json || json.code !== 0) {
          throw new Error((json && json.message) || '加载失败');
        }
        return json.data || {};
      });
    });
  }

  function joinLabel(mode) {
    if (mode === 'member') return '会员加入';
    if (mode === 'paid') return '付费加入';
    if (mode === 'approval') return '申请加入';
    return '免费加入';
  }

  function render(data) {
    current = data || {};
    if (titleEl) titleEl.textContent = current.name || '未命名题库';
    if (descEl) descEl.textContent = current.description || '暂无题库简介';
    if (richEl) richEl.textContent = current.description || '暂无更详细的名片介绍。';
    if (coverEl) {
      if (current.cover_image) {
        coverEl.innerHTML = '<img src="' + esc(current.cover_image) + '" alt="">';
      } else {
        coverEl.textContent = current.name || '题库名片';
      }
    }
    if (badgesEl) {
      var badges = ['<span class="plaza-badge ' + (current.bank_type === 'system' ? 'system' : 'user') + '">' + esc(current.source_label || '') + '</span>'];
      if (current.is_featured) badges.push('<span class="forum-badge forum-badge-feat">精华</span>');
      if (current.relation && current.relation.is_joined) badges.push('<span class="plaza-badge joined">已加入</span>');
      if (current.allow_copy) badges.push('<span class="plaza-badge user">可复制</span>');
      badgesEl.innerHTML = badges.join('');
    }
    if (metaEl) {
      metaEl.innerHTML = [
        '<span class="app-pill">创建者 ' + esc(current.owner_label || '系统题库') + '</span>',
        '<span class="app-pill">板块 ' + esc((current.board && current.board.name) || '未分板块') + '</span>',
        '<span class="app-pill">题量 ' + fmtCount(current.question_count) + '</span>'
      ].join('');
    }
    if (joinModeEl) joinModeEl.textContent = joinLabel(current.join_mode || 'free');
    if (joinNoteEl) joinNoteEl.textContent = current.join_note || (current.join_mode === 'free' ? '确认加入后，该题库会进入“我的题库”。' : '当前加入方式预留给后续会员、付费或审批能力。');
    if (infoListEl) {
      infoListEl.innerHTML = [
        ['发布时间', current.published_at || '-'],
        ['最近活跃', current.last_activity_at || '-'],
        ['总参与人数', fmtCount(current.participants_total)],
        ['近 7 天活跃', fmtCount(current.answer_users_7d)],
        ['加入方式', joinLabel(current.join_mode || 'free')]
      ].map(function (item) {
        return '<div class="bank-card-info-item"><div class="k">' + esc(item[0]) + '</div><div class="v">' + esc(item[1]) + '</div></div>';
      }).join('');
    }
    renderActions();
  }

  function renderActions() {
    if (!actionsEl) return;
    var actions = [];
    var practiceUrl = current.practice_url || current.detail_url || '#';
    if (!boot.logged_in) {
      actions.push('<a class="bank-card-action-btn primary" href="/login?redirect=' + encodeURIComponent(window.location.pathname) + '">登录后加入</a>');
      actionsEl.innerHTML = actions.join('');
      return;
    }
    if (current.is_owner) {
      actions.push('<a class="bank-card-action-btn primary" href="' + esc(practiceUrl) + '">继续练习</a>');
      if (current.bank_type === 'user') actions.push('<a class="bank-card-action-btn" href="/user/banks/' + esc(current.id) + '/edit">编辑名片</a>');
      actionsEl.innerHTML = actions.join('');
      return;
    }
    if (current.relation && current.relation.is_joined) {
      actions.push('<a class="bank-card-action-btn primary" href="' + esc(practiceUrl) + '">已加入，继续练习</a>');
      actionsEl.innerHTML = actions.join('');
      return;
    }
    if ((current.join_mode || 'free') !== 'free') {
      actions.push('<button class="bank-card-action-btn" type="button" disabled>暂未开放 ' + esc(joinLabel(current.join_mode)) + '</button>');
      actions.push('<span class="bank-card-hint">后续可在这里接入会员、付费或审批流程。</span>');
      actionsEl.innerHTML = actions.join('');
      return;
    }
    actions.push('<button class="bank-card-action-btn primary" type="button" id="confirmJoinBtn">确认加入</button>');
    actions.push('<a class="bank-card-action-btn" href="/public/banks">返回题库广场</a>');
    actionsEl.innerHTML = actions.join('');
    var btn = document.getElementById('confirmJoinBtn');
    if (btn) btn.addEventListener('click', joinBank);
  }

  function joinBank() {
    var url = '/api/public/banks/' + encodeURIComponent(String(boot.source_type || 'user')) + '/' + encodeURIComponent(String(boot.bank_id || 0)) + '/join';
    fetch(url, { method: 'POST', credentials: 'same-origin', headers: { 'X-Requested-With': 'XMLHttpRequest' } }).then(function (response) {
      return response.json().catch(function () { return {}; }).then(function (json) {
        if (!response.ok || !json || json.code !== 0) {
          throw new Error((json && json.message) || '加入失败');
        }
        return json;
      });
    }).then(function () {
      return fetchJson();
    }).then(function (data) {
      render(data);
    }).catch(function (error) {
      window.alert((error && error.message) || '加入失败');
    });
  }

  fetchJson().then(render).catch(function (error) {
    if (titleEl) titleEl.textContent = '加载失败';
    if (descEl) descEl.textContent = (error && error.message) || '请稍后重试';
  });
})();
