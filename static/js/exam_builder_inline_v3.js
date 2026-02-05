(() => {
  function parseIntSafe(value, fallback, minValue, maxValue) {
    let n = parseInt(String(value ?? ''), 10);
    if (!Number.isFinite(n)) n = fallback;
    if (minValue !== undefined && minValue !== null) n = Math.max(minValue, n);
    if (maxValue !== undefined && maxValue !== null) n = Math.min(maxValue, n);
    return n;
  }

  function parseFloatSafe(value, fallback, minValue, maxValue) {
    let n = parseFloat(String(value ?? ''));
    if (!Number.isFinite(n)) n = fallback;
    if (minValue !== undefined && minValue !== null) n = Math.max(minValue, n);
    if (maxValue !== undefined && maxValue !== null) n = Math.min(maxValue, n);
    return n;
  }

  function formatNum(n) {
    if (!Number.isFinite(n)) return '0';
    if (Number.isInteger(n)) return String(n);
    return String(n.toFixed(2)).replace(/\.?0+$/, '');
  }

  function isLoggedIn() {
    if (typeof LOGGED_IN === 'boolean') return LOGGED_IN;
    if (typeof window.LOGGED_IN === 'boolean') return window.LOGGED_IN;
    return true;
  }

  function setMsg(root, text, kind) {
    const el = root.querySelector('[data-inline-exam-msg]');
    if (!el) return;
    el.classList.toggle('error', kind === 'error');
    el.textContent = String(text || '');
  }

  const TEMPLATE_API = '/api/exams/templates';
  const TEMPLATE_SELECTED_KEY_PREFIX = 'sak:exam_template_selected_v1';
  const TEMPLATE_PICKER_STORE = new WeakMap();

  function normalizeTemplateConfig(raw) {
    if (!raw || typeof raw !== 'object') return null;
    const sourceRaw = String(raw.source || 'public').trim().toLowerCase();
    const source = sourceRaw === 'user_bank' ? 'user_bank' : 'public';
    const subject = String(raw.subject || 'all').trim() || 'all';
    const bank_id = raw.bank_id ? parseIntSafe(raw.bank_id, 0, 0, 1e9) : null;
    const duration = parseIntSafe(raw.duration, 60, 1, 1440);
    let targetTotal = parseIntSafe((raw.targetTotal ?? raw.total ?? raw.target_total), 0, 0, 300);
    const types = (raw.types && typeof raw.types === 'object') ? raw.types : {};
    const scores = (raw.scores && typeof raw.scores === 'object') ? raw.scores : {};
    if (!targetTotal) {
      targetTotal = Object.values(types).reduce((sum, val) => sum + parseIntSafe(val, 0, 0, 1000), 0);
      targetTotal = parseIntSafe(targetTotal, 0, 0, 300);
    }
    return {
      source,
      subject,
      bank_id: bank_id || null,
      duration,
      targetTotal,
      types,
      scores,
    };
  }

  function templateMatchesScope(cfg, scope) {
    if (!cfg || !scope) return false;
    if (cfg.source !== scope.source) return false;
    if (scope.source === 'user_bank') {
      return !!(scope.bank_id && cfg.bank_id && Number(cfg.bank_id) === Number(scope.bank_id));
    }
    // public：允许 subject=all 作为通用模板
    const sub = String(scope.subject || 'all').trim() || 'all';
    return cfg.subject === sub || cfg.subject === 'all';
  }

  function templateScopeKey(scope) {
    if (!scope) return `${TEMPLATE_SELECTED_KEY_PREFIX}:unknown`;
    if (scope.source === 'user_bank') {
      return `${TEMPLATE_SELECTED_KEY_PREFIX}:user_bank:${scope.bank_id || '0'}`;
    }
    return `${TEMPLATE_SELECTED_KEY_PREFIX}:public:${scope.subject || 'all'}`;
  }

  function loadSelectedTemplateId(scope) {
    try {
      return (localStorage.getItem(templateScopeKey(scope)) || '').trim();
    } catch (e) {
      return '';
    }
  }

  function saveSelectedTemplateId(scope, id) {
    try {
      const key = templateScopeKey(scope);
      const v = String(id || '').trim();
      if (!v) localStorage.removeItem(key);
      else localStorage.setItem(key, v);
    } catch (e) {}
  }

  function buildTemplateManageUrl(root, scope) {
    const explicit = String(root?.dataset?.templateManageUrl || '').trim();
    if (explicit) return explicit;
    try {
      if (scope.source === 'user_bank' && scope.bank_id) {
        return `/exams?tab=templates&source=user_bank&bank_id=${encodeURIComponent(String(scope.bank_id))}&lock=1`;
      }
      return `/exams?tab=templates&source=public&subject=${encodeURIComponent(String(scope.subject || 'all'))}&lock=1`;
    } catch (e) {
      return '/exams?tab=templates';
    }
  }

  function applyTemplateConfig(root, cfg) {
    if (!root || !cfg) return;

    const durationEl = root.querySelector('[data-inline-exam-duration]');
    const totalEl = root.querySelector('[data-inline-exam-total]');
    const desiredTotal = parseIntSafe(cfg.targetTotal, 0, 0, 300);
    if (durationEl) durationEl.value = String(parseIntSafe(cfg.duration, 60, 1, 1440));
    if (totalEl) totalEl.value = String(parseIntSafe(desiredTotal || 30, 30, 1, 300));

    const rows = Array.from(root.querySelectorAll('[data-inline-exam-types] .exam-types-row[data-qtype]'));
    const states = rows.map((row) => {
      const qtype = row.dataset.qtype || '';
      const cb = row.querySelector('.exam-type-enable');
      const countInput = row.querySelector('.exam-type-count');
      const scoreInput = row.querySelector('.exam-type-score');

      const cntRaw = (cfg.types && qtype && cfg.types[qtype] != null) ? cfg.types[qtype] : 0;
      const scRaw = (cfg.scores && qtype && cfg.scores[qtype] != null) ? cfg.scores[qtype] : 1;
      const count = parseIntSafe(cntRaw, 0, 0, 500);
      const score = parseFloatSafe(scRaw, 1, 0, 1000);

      return { row, qtype, cb, countInput, scoreInput, count, score };
    });

    // 先按模板原始配置写入
    states.forEach((s) => {
      if (s.cb) s.cb.checked = s.count > 0;
      if (s.countInput) s.countInput.value = String(s.count);
      if (s.scoreInput) s.scoreInput.value = String(s.score);
      syncRowEnabled(s.row);
    });

    let enabled = states.filter((s) => s.cb && s.cb.checked && s.count > 0);
    let assigned = enabled.reduce((sum, s) => sum + (Number.isFinite(s.count) ? s.count : 0), 0);
    const target = parseIntSafe(desiredTotal || assigned || 0, 0, 0, 300);

    // 兜底：模板题型不在当前范围内 → 选默认题型并均分
    if (target > 0 && (!enabled.length || assigned <= 0)) {
      const qtypesAll = states.map((s) => s.qtype).filter(Boolean);
      const preferred = ['单选题', '多选题', '判断题'];
      const picked = preferred.filter((t) => qtypesAll.includes(t));
      const fallbackPicked = picked.length ? picked : qtypesAll.slice(0, Math.min(3, qtypesAll.length));

      states.forEach((s) => {
        const on = fallbackPicked.includes(s.qtype);
        if (s.cb) s.cb.checked = on;
        if (s.countInput) s.countInput.value = '0';
        if (s.scoreInput && !s.scoreInput.value) s.scoreInput.value = '1';
        syncRowEnabled(s.row);
      });

      if (totalEl) totalEl.value = String(parseIntSafe(target, 30, 1, 300));
      autoDistribute(root);
      setMsg(root, '', '');
      updateSummary(root);
      return;
    }

    // 自动适配：当目标题量与可用题型不一致时，按权重比例缩放到 target
    if (target > 0 && enabled.length && assigned > 0 && assigned !== target) {
      const weights = enabled.map((s) => Math.max(0, parseIntSafe(s.count, 0, 0, 1000)));
      const wSum = weights.reduce((a, b) => a + b, 0);
      if (wSum > 0) {
        const rawCounts = weights.map((w) => (w / wSum) * target);
        const baseCounts = rawCounts.map((x) => Math.floor(x));
        let rem = target - baseCounts.reduce((a, b) => a + b, 0);

        const order = rawCounts
          .map((x, i) => ({ i, frac: x - baseCounts[i] }))
          .sort((a, b) => b.frac - a.frac);

        let pos = 0;
        while (rem > 0 && order.length) {
          baseCounts[order[pos % order.length].i] += 1;
          rem -= 1;
          pos += 1;
        }

        enabled.forEach((s, idx) => {
          const nextCount = parseIntSafe(baseCounts[idx], 0, 0, 500);
          s.count = nextCount;
          if (s.cb) s.cb.checked = nextCount > 0;
          if (s.countInput) s.countInput.value = String(nextCount);
          syncRowEnabled(s.row);
        });

        if (totalEl) totalEl.value = String(parseIntSafe(target, 30, 1, 300));
      }
    }

    setMsg(root, '', '');
    updateSummary(root);
  }

  async function fetchUserTemplatesForScope(scope) {
    const params = new URLSearchParams();
    params.set('source', scope.source || 'public');
    if (scope.source === 'public') {
      params.set('subject', String(scope.subject || 'all'));
    } else if (scope.source === 'user_bank' && scope.bank_id) {
      params.set('bank_id', String(scope.bank_id));
    }

    const resp = await fetch(`${TEMPLATE_API}?${params.toString()}`, { credentials: 'same-origin' });
    const js = await resp.json().catch(() => ({}));
    if (!resp.ok || !js || js.status !== 'success') {
      const msg = (js && js.message) ? js.message : '获取模板失败，请稍后重试。';
      throw new Error(msg);
    }
    return Array.isArray(js.data) ? js.data : [];
  }

  function setPickerLoading(st, loading, text) {
    if (!st || !st.el) return;
    st.loading = !!loading;
    if (st.el.trigger) {
      st.el.trigger.disabled = !!loading;
      st.el.trigger.setAttribute('aria-busy', loading ? 'true' : 'false');
      st.el.trigger.classList.toggle('is-loading', !!loading);
    }
    if (st.el.tip) {
      st.el.tip.textContent = text || '';
      st.el.tip.hidden = !st.el.tip.textContent;
    }
  }

  function updatePickerDisplay(st) {
    if (!st || !st.el) return;
    const picked = st.selected;
    if (!picked) {
      if (st.el.value) st.el.value.textContent = '不使用模板';
      if (st.el.meta) st.el.meta.textContent = '自由配置（保留当前设置）';
      return;
    }
    if (st.el.value) st.el.value.textContent = picked.title || '未命名模板';
    const badge = (picked.cfg && picked.cfg.source === 'public' && picked.cfg.subject === 'all') ? ' · 通用' : '';
    if (st.el.meta) st.el.meta.textContent = `${picked.cfg.duration} 分钟 · ${picked.cfg.targetTotal} 题${badge}`;
  }

  function closePickerModal(st) {
    if (!st || !st.modal) return;
    st.modal.overlay?.classList.remove('show');
    st.modal.overlay?.setAttribute('aria-hidden', 'true');
  }

  function renderPickerModalList(st) {
    if (!st || !st.modal) return;
    const list = st.modal.list;
    if (!list) return;
    list.innerHTML = '';

    const addItem = (item) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'exam-template-item';
      if (item && item.id && st.selected && String(st.selected.id) === String(item.id)) btn.classList.add('active');
      if (!item && !st.selected) btn.classList.add('active');

      const left = document.createElement('div');
      left.className = 'exam-template-item-main';
      const title = document.createElement('div');
      title.className = 'exam-template-item-title';
      title.textContent = item ? (item.title || '未命名模板') : '不使用模板';
      const meta = document.createElement('div');
      meta.className = 'exam-template-item-meta';
      if (!item) {
        meta.textContent = '自由配置（不套用云端模板）';
      } else {
        const badge = (item.cfg && item.cfg.source === 'public' && item.cfg.subject === 'all') ? ' · 通用' : '';
        meta.textContent = `${item.cfg.duration} 分钟 · ${item.cfg.targetTotal} 题${badge}`;
      }
      left.appendChild(title);
      left.appendChild(meta);

      const right = document.createElement('div');
      right.className = 'exam-template-item-right';
      right.textContent = (item && item.id) ? '应用' : '选择';

      btn.appendChild(left);
      btn.appendChild(right);
      btn.addEventListener('click', () => {
        if (!item) {
          st.selected = null;
          saveSelectedTemplateId(st.scope, '');
          updatePickerDisplay(st);
          closePickerModal(st);
          return;
        }
        st.selected = item;
        saveSelectedTemplateId(st.scope, item.id);
        updatePickerDisplay(st);
        applyTemplateConfig(st.root, item.cfg);
        closePickerModal(st);
      });

      list.appendChild(btn);
    };

    // 1) 不使用模板
    addItem(null);

    // 2) 可用模板
    if (!st.templates.length) {
      const empty = document.createElement('div');
      empty.className = 'exam-template-empty';
      empty.textContent = '暂无可用模板。可前往模板库创建。';
      list.appendChild(empty);
      return;
    }

    st.templates.forEach((tpl) => addItem(tpl));
  }

  function openPickerModal(st) {
    if (!st || !st.modal) return;
    renderPickerModalList(st);
    st.modal.overlay?.classList.add('show');
    st.modal.overlay?.setAttribute('aria-hidden', 'false');
  }

  function ensurePickerModal(st) {
    if (!st || st.modal) return;
    const overlay = document.createElement('div');
    overlay.className = 'exam-modal-overlay';
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-modal', 'true');
    overlay.setAttribute('aria-hidden', 'true');

    const modal = document.createElement('div');
    modal.className = 'exam-modal';

    const head = document.createElement('div');
    head.className = 'exam-modal-head';

    const title = document.createElement('div');
    title.className = 'exam-modal-title';
    title.textContent = '选择模板';

    const actions = document.createElement('div');
    actions.className = 'exam-modal-actions';

    const manage = document.createElement('a');
    manage.className = 'exam-btn';
    manage.href = st.manageUrl || '/exams?tab=templates';
    manage.textContent = '模板库';

    const refresh = document.createElement('button');
    refresh.className = 'exam-btn';
    refresh.type = 'button';
    refresh.textContent = '刷新';
    refresh.addEventListener('click', async () => {
      await loadTemplatesIntoPicker(st);
      renderPickerModalList(st);
    });

    const close = document.createElement('button');
    close.className = 'exam-btn';
    close.type = 'button';
    close.textContent = '关闭';
    close.addEventListener('click', () => closePickerModal(st));

    actions.appendChild(manage);
    actions.appendChild(refresh);
    actions.appendChild(close);
    head.appendChild(title);
    head.appendChild(actions);

    const list = document.createElement('div');
    list.className = 'exam-modal-list';

    modal.appendChild(head);
    modal.appendChild(list);
    overlay.appendChild(modal);

    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) closePickerModal(st);
    });

    document.body.appendChild(overlay);
    st.modal = { overlay, list };
  }

  async function loadTemplatesIntoPicker(st) {
    if (!st) return;
    setPickerLoading(st, true, '正在同步模板…');
    try {
      const raw = await fetchUserTemplatesForScope(st.scope);
      const list = (raw || []).map((t) => {
        const cfg = normalizeTemplateConfig(t && t.config ? t.config : {});
        if (!cfg) return null;
        if (!templateMatchesScope(cfg, st.scope)) return null;
        return {
          id: t.id,
          title: t.title || '未命名模板',
          cfg,
          updated_at: t.updated_at,
        };
      }).filter(Boolean);

      st.templates = list;
      st.loaded = true;

      const savedId = loadSelectedTemplateId(st.scope);
      const picked = savedId ? list.find((x) => String(x.id) === String(savedId)) : null;
      if (picked) {
        st.selected = picked;
        updatePickerDisplay(st);
        applyTemplateConfig(st.root, picked.cfg);
      } else {
        st.selected = null;
        if (savedId) saveSelectedTemplateId(st.scope, '');
        updatePickerDisplay(st);
      }

      setPickerLoading(st, false, st.templates.length ? '' : '暂无模板：可在“模板库”中创建');
    } catch (e) {
      st.templates = [];
      st.loaded = true;
      st.selected = null;
      updatePickerDisplay(st);
      setPickerLoading(st, false, (e && e.message) ? e.message : '获取模板失败，请稍后重试。');
    }
  }

  function initTemplatePicker(root) {
    const mount = root.querySelector('[data-inline-exam-template-picker]');
    if (!mount) return;
    const scope = getScope(root);
    const manageUrl = buildTemplateManageUrl(root, scope);

    const st = {
      root,
      scope,
      manageUrl,
      templates: [],
      loaded: false,
      loading: false,
      selected: null,
      el: {},
      modal: null,
    };
    TEMPLATE_PICKER_STORE.set(root, st);

    mount.innerHTML = '';
    const wrap = document.createElement('div');
    wrap.className = 'exam-template-picker';

    const row = document.createElement('div');
    row.className = 'exam-template-picker-row';

    const main = document.createElement('button');
    main.className = 'exam-template-picker-main';
    main.type = 'button';
    main.addEventListener('click', () => {
      if (st.loading) return;
      ensurePickerModal(st);
      openPickerModal(st);
    });
    const k = document.createElement('div');
    k.className = 'exam-template-picker-k';
    k.textContent = '考试模板';
    const v = document.createElement('div');
    v.className = 'exam-template-picker-v';
    v.textContent = '不使用模板';
    const meta = document.createElement('div');
    meta.className = 'exam-template-picker-meta';
    meta.textContent = '自由配置（保留当前设置）';
    main.appendChild(k);
    main.appendChild(v);
    main.appendChild(meta);

    const actions = document.createElement('div');
    actions.className = 'exam-template-picker-actions';

    const manageBtn = document.createElement('a');
    manageBtn.className = 'exam-btn';
    manageBtn.href = manageUrl || '/exams?tab=templates';
    manageBtn.textContent = '模板库';
    actions.appendChild(manageBtn);

    row.appendChild(main);
    row.appendChild(actions);

    const tip = document.createElement('div');
    tip.className = 'exam-template-picker-tip';
    tip.textContent = '';
    tip.hidden = true;

    wrap.appendChild(row);
    wrap.appendChild(tip);
    mount.appendChild(wrap);

    st.el = { value: v, meta, tip, trigger: main };

    loadTemplatesIntoPicker(st);
  }

  function setTemplateActive(root, activeBtn) {
    root.querySelectorAll('[data-inline-exam-template]').forEach((btn) => {
      btn.classList.toggle('active', btn === activeBtn);
    });
  }

  function syncRowEnabled(row) {
    const enabled = !!row.querySelector('.exam-type-enable')?.checked;
    const countInput = row.querySelector('.exam-type-count');
    const scoreInput = row.querySelector('.exam-type-score');
    if (countInput) countInput.disabled = !enabled;
    if (scoreInput) scoreInput.disabled = !enabled;
    row.style.opacity = enabled ? '1' : '0.6';
  }

  function getScope(root) {
    const source = String(root.dataset.source || 'public').trim().toLowerCase();
    const subject = String(root.dataset.subject || 'all');
    const bankIdRaw = String(root.dataset.bankId || '').trim();
    const bank_id = bankIdRaw ? parseIntSafe(bankIdRaw, 0, 0, 1e9) : null;
    return {
      source: source === 'user_bank' ? 'user_bank' : 'public',
      subject: subject || 'all',
      bank_id: bank_id || null,
      scopeLabel: String(root.dataset.scopeLabel || '').trim(),
    };
  }

  function collectConfig(root) {
    const scope = getScope(root);
    const targetTotal = parseIntSafe(root.querySelector('[data-inline-exam-total]')?.value, 30, 1, 300);
    const duration = parseIntSafe(root.querySelector('[data-inline-exam-duration]')?.value, 60, 1, 1440);

    const types = {};
    const scores = {};
    let assigned = 0;
    let totalScore = 0;

    root.querySelectorAll('[data-inline-exam-types] .exam-types-row[data-qtype]').forEach((row) => {
      const qtype = row.dataset.qtype || '';
      const enabled = !!row.querySelector('.exam-type-enable')?.checked;
      if (!enabled || !qtype) return;
      const count = parseIntSafe(row.querySelector('.exam-type-count')?.value, 0, 0, 500);
      const score = parseFloatSafe(row.querySelector('.exam-type-score')?.value, 1, 0, 1000);
      if (count <= 0) return;
      types[qtype] = count;
      scores[qtype] = score;
      assigned += count;
      totalScore += count * score;
    });

    return { ...scope, targetTotal, duration, types, scores, assigned, totalScore };
  }

  function updateSummary(root) {
    const cfg = collectConfig(root);
    const scopeText = cfg.scopeLabel || (cfg.source === 'user_bank' ? '个人题库' : `公共题库 · ${cfg.subject || '全部科目'}`);

    root.querySelector('[data-inline-exam-sum-scope]')?.replaceChildren(document.createTextNode(scopeText));
    root.querySelector('[data-inline-exam-sum-duration]')?.replaceChildren(document.createTextNode(`${cfg.duration} 分钟`));
    root.querySelector('[data-inline-exam-sum-assigned]')?.replaceChildren(document.createTextNode(`${cfg.assigned} 题`));
    root.querySelector('[data-inline-exam-sum-score]')?.replaceChildren(document.createTextNode(`${formatNum(cfg.totalScore)} 分`));

    root.querySelectorAll('[data-inline-exam-types] .exam-types-row[data-qtype]').forEach((row) => {
      const enabled = !!row.querySelector('.exam-type-enable')?.checked;
      const count = parseIntSafe(row.querySelector('.exam-type-count')?.value, 0, 0, 500);
      const score = parseFloatSafe(row.querySelector('.exam-type-score')?.value, 1, 0, 1000);
      const subtotal = enabled ? (count * score) : 0;
      const cell = row.querySelector('.exam-subtotal');
      if (cell) cell.textContent = formatNum(subtotal);
    });

    const typesBox = root.querySelector('[data-inline-exam-sum-types]');
    if (typesBox) {
      const items = Object.entries(cfg.types);
      if (!items.length) {
        typesBox.innerHTML = '<div class="muted" style="font-size:12px;">请选择题型并设置题数。</div>';
      } else {
        typesBox.innerHTML = '';
        items.forEach(([qtype, count]) => {
          const score = cfg.scores[qtype] ?? 1;
          const pill = document.createElement('div');
          pill.className = 'exam-type-pill';

          const l = document.createElement('div');
          l.className = 'l';
          l.textContent = qtype;

          const r = document.createElement('div');
          r.className = 'r';
          r.textContent = `${count} × ${formatNum(score)} = ${formatNum(count * score)}`;

          pill.appendChild(l);
          pill.appendChild(r);
          typesBox.appendChild(pill);
        });
      }
    }

    const startBtn = root.querySelector('[data-inline-exam-start]');
    if (startBtn) startBtn.disabled = cfg.assigned <= 0 || (cfg.source === 'user_bank' && !cfg.bank_id);
  }

  function applyTemplate(root, btn) {
    if (!root || !btn) return;
    const durationRaw = btn.dataset.duration;
    const totalRaw = btn.dataset.total;
    if (durationRaw && totalRaw) {
      const duration = parseIntSafe(durationRaw, 60, 1, 1440);
      const total = parseIntSafe(totalRaw, 30, 1, 300);
      const durationEl = root.querySelector('[data-inline-exam-duration]');
      const totalEl = root.querySelector('[data-inline-exam-total]');
      if (durationEl) durationEl.value = String(duration);
      if (totalEl) totalEl.value = String(total);
      autoDistribute(root);
    }
    setTemplateActive(root, btn);
    setMsg(root, '', '');
    updateSummary(root);
  }

  function autoDistribute(root) {
    const cfg = collectConfig(root);
    const total = parseIntSafe(cfg.targetTotal, 30, 1, 300);
    const rows = Array.from(root.querySelectorAll('[data-inline-exam-types] .exam-types-row[data-qtype]'));
    const enabledRows = rows.filter((r) => !!r.querySelector('.exam-type-enable')?.checked);

    if (!enabledRows.length) {
      setMsg(root, '请先勾选至少一种题型，再进行均分。', 'error');
      updateSummary(root);
      return;
    }

    const n = enabledRows.length;
    const base = Math.floor(total / n);
    let rem = total % n;

    enabledRows.forEach((row) => {
      const count = row.querySelector('.exam-type-count');
      if (!count) return;
      let v = base + (rem > 0 ? 1 : 0);
      if (rem > 0) rem -= 1;
      count.value = String(v);
    });

    setMsg(root, '', '');
    updateSummary(root);
  }

  function resetScores(root) {
    root.querySelectorAll('[data-inline-exam-types] .exam-types-row[data-qtype]').forEach((row) => {
      const score = row.querySelector('.exam-type-score');
      if (score) score.value = '1';
    });
    setMsg(root, '', '');
    updateSummary(root);
  }

  async function saveExamTemplate(root) {
    if (!isLoggedIn()) {
      window.location.href = '/login';
      return;
    }

    const cfg = collectConfig(root);
    if (cfg.source === 'user_bank' && !cfg.bank_id) {
      setMsg(root, '请选择个人题库。', 'error');
      return;
    }
    if (!cfg.types || !Object.keys(cfg.types).length) {
      setMsg(root, '请先设置题型与题量。', 'error');
      return;
    }

    const now = new Date();
    const stamp = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
    const title = (prompt('请输入模板名称', `自定义模板 ${stamp}`) || '').trim();
    if (!title) return;

    try {
      setMsg(root, '正在保存模板…', '');
      const resp = await fetch(TEMPLATE_API, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: title,
          config: {
            source: cfg.source,
            subject: cfg.subject,
            bank_id: cfg.bank_id,
            duration: cfg.duration,
            targetTotal: cfg.targetTotal,
            types: cfg.types,
            scores: cfg.scores,
          },
        }),
        credentials: 'same-origin',
      });
      const js = await resp.json().catch(() => ({}));
      if (!resp.ok || !js || js.status !== 'success') {
        setMsg(root, (js && js.message) ? js.message : '保存模板失败，请稍后再试。', 'error');
        return;
      }

      setMsg(root, '已保存为模板（云端同步）。', '');
      const st = TEMPLATE_PICKER_STORE.get(root);
      if (st) {
        await loadTemplatesIntoPicker(st);
      }
    } catch (e) {
      setMsg(root, '保存失败：网络异常。', 'error');
    }
  }

  function applyDefaultPresetIfEmpty(root) {
    if (root.dataset.presetApplied === '1') return;

    const cfg = collectConfig(root);
    if (cfg.assigned > 0) return;

    const qTypes = Array.from(root.querySelectorAll('[data-inline-exam-types] .exam-types-row[data-qtype]'))
      .map((r) => r.dataset.qtype || '')
      .filter(Boolean);
    if (!qTypes.length) return;

    root.dataset.presetApplied = '1';
    const preferred = ['单选题', '多选题', '判断题'];
    const picked = preferred.filter((t) => qTypes.includes(t));
    const fallbackPicked = picked.length ? picked : qTypes.slice(0, Math.min(3, qTypes.length));

    root.querySelectorAll('[data-inline-exam-types] .exam-types-row[data-qtype]').forEach((row) => {
      const qtype = row.dataset.qtype || '';
      const cb = row.querySelector('.exam-type-enable');
      const countInput = row.querySelector('.exam-type-count');
      const scoreInput = row.querySelector('.exam-type-score');
      if (cb) cb.checked = fallbackPicked.includes(qtype);
      if (countInput) countInput.value = '0';
      if (scoreInput) scoreInput.value = '1';
      syncRowEnabled(row);
    });

    autoDistribute(root);
    updateSummary(root);
  }

  async function startExam(root) {
    if (!isLoggedIn()) {
      window.location.href = '/login';
      return;
    }

    if (root.dataset.requireScopeAll === '1') {
      try {
        const s = (typeof state !== 'undefined') ? state : window.state;
        if (s && typeof s === 'object' && String(s.scope || 'all') !== 'all') {
          setMsg(root, root.dataset.requireScopeTip || '考试仅支持“全部”范围，请先切换范围。', 'error');
          return;
        }
      } catch (e) {}
    }

    const btn = root.querySelector('[data-inline-exam-start]');
    if (btn) {
      btn.disabled = true;
      btn.dataset.originalText = btn.dataset.originalText || (btn.textContent || '开始考试');
      btn.textContent = '创建中…';
    }
    setMsg(root, '正在创建考试…', '');

    try {
      const cfg = collectConfig(root);
      if (cfg.source === 'user_bank' && !cfg.bank_id) {
        setMsg(root, '请选择一个个人题库。', 'error');
        return;
      }
      if (cfg.assigned <= 0) {
        setMsg(root, '请至少设置一种题型的题数（大于 0）。', 'error');
        return;
      }

      const resp = await fetch('/api/exams/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source: cfg.source,
          subject: cfg.subject,
          bank_id: cfg.bank_id,
          duration: cfg.duration,
          types: cfg.types,
          scores: cfg.scores,
        }),
        credentials: 'same-origin',
      });
      const js = await resp.json().catch(() => ({}));

      if (!resp.ok || !js || js.status !== 'success' || !js.exam_id) {
        setMsg(root, (js && js.message) ? js.message : '创建考试失败，请稍后再试。', 'error');
        return;
      }

      const nextUrl = (cfg.source === 'user_bank' && cfg.bank_id)
        ? `/quiz?mode=exam&exam_id=${js.exam_id}&bank_id=${cfg.bank_id}`
        : `/quiz?mode=exam&exam_id=${js.exam_id}`;
      window.location.href = nextUrl;
    } catch (e) {
      setMsg(root, '创建考试失败，请检查网络或稍后重试。', 'error');
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.textContent = btn.dataset.originalText || '开始考试';
      }
      updateSummary(root);
    }
  }

  function initBuilder(root) {
    if (!root) return;
    if (root.dataset.inlineExamInit === '1') return;
    root.dataset.inlineExamInit = '1';

    root.querySelectorAll('[data-inline-exam-types] .exam-types-row[data-qtype]').forEach((row) => {
      const cb = row.querySelector('.exam-type-enable');
      const count = row.querySelector('.exam-type-count');
      const score = row.querySelector('.exam-type-score');
      if (cb) {
        cb.addEventListener('change', () => {
          syncRowEnabled(row);
          updateSummary(root);
        });
      }
      count?.addEventListener('input', () => updateSummary(root));
      score?.addEventListener('input', () => updateSummary(root));
      syncRowEnabled(row);
    });

    root.querySelector('[data-inline-exam-duration]')?.addEventListener('input', () => updateSummary(root));
    root.querySelector('[data-inline-exam-total]')?.addEventListener('input', () => updateSummary(root));

    root.querySelectorAll('[data-inline-exam-preset][data-duration][data-total]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const duration = parseIntSafe(btn.dataset.duration, 60, 1, 1440);
        const total = parseIntSafe(btn.dataset.total, 30, 1, 300);
        const durationEl = root.querySelector('[data-inline-exam-duration]');
        const totalEl = root.querySelector('[data-inline-exam-total]');
        if (durationEl) durationEl.value = String(duration);
        if (totalEl) totalEl.value = String(total);
        autoDistribute(root);
        updateSummary(root);
      });
    });

    root.querySelectorAll('[data-inline-exam-template]').forEach((btn) => {
      btn.addEventListener('click', () => applyTemplate(root, btn));
    });

    root.querySelector('[data-inline-exam-save-template]')?.addEventListener('click', () => saveExamTemplate(root));
    root.querySelector('[data-inline-exam-distribute]')?.addEventListener('click', () => autoDistribute(root));
    root.querySelector('[data-inline-exam-reset-scores]')?.addEventListener('click', () => resetScores(root));
    root.querySelector('[data-inline-exam-start]')?.addEventListener('click', () => startExam(root));
    root.querySelector('[data-inline-exam-close]')?.addEventListener('click', () => { root.hidden = true; });

    if (!root.querySelector('[data-inline-exam-types] .exam-types-row[data-qtype]')) {
      setMsg(root, '当前范围暂无题型数据。', 'error');
    }

    initTemplatePicker(root);
    applyDefaultPresetIfEmpty(root);
    updateSummary(root);
  }

  function toggleById(targetId) {
    const root = document.getElementById(targetId);
    if (!root) return;
    root.hidden = !root.hidden;
    if (!root.hidden) {
      initBuilder(root);
      try { root.scrollIntoView({ behavior: 'smooth', block: 'start' }); } catch (e) {}
    }
  }

  function initPage() {
    document.querySelectorAll('[data-inline-exam-builder]').forEach((root) => initBuilder(root));
    document.querySelectorAll('[data-inline-exam-toggle]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const id = String(btn.dataset.inlineExamToggle || '').trim();
        if (!id) return;
        toggleById(id);
      });
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initPage);
  } else {
    initPage();
  }
})();
