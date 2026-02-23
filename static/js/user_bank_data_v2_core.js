(function () {
  'use strict';

  function clamp(val, min, max) {
    return Math.max(min, Math.min(max, val));
  }

  function getVar(name) {
    try {
      return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    } catch (err) {
      return '';
    }
  }

  function pickColor(hex, alpha) {
    var a = clamp(alpha == null ? 1 : alpha, 0, 1);
    if (!hex) return 'rgba(17,24,39,' + a + ')';
    var h = String(hex).trim();
    if (h.startsWith('rgb')) return h;
    if (!h.startsWith('#')) return h;
    var v = h.slice(1);
    if (v.length === 3) v = v[0] + v[0] + v[1] + v[1] + v[2] + v[2];
    if (v.length !== 6) return h;
    var r = parseInt(v.slice(0, 2), 16);
    var g = parseInt(v.slice(2, 4), 16);
    var b = parseInt(v.slice(4, 6), 16);
    return 'rgba(' + r + ',' + g + ',' + b + ',' + a + ')';
  }

  function toNum(v) {
    var n = Number(v || 0);
    return Number.isFinite(n) ? n : 0;
  }

  function fmtCount(v) {
    var n = toNum(v);
    try {
      return n.toLocaleString('zh-CN');
    } catch (err) {
      return String(n);
    }
  }

  function fmtPercent(v) {
    return toNum(v).toFixed(1) + '%';
  }

  function fmtDay(iso) {
    var s = String(iso || '');
    if (/^\d{4}-\d{2}-\d{2}/.test(s)) return s.slice(5, 10);
    return s;
  }

  function fmtDateTime(iso) {
    var s = String(iso || '');
    if (!s) return '—';
    if (/^\d{4}-\d{2}-\d{2}/.test(s)) return s.slice(0, 16).replace('T', ' ');
    return s;
  }

  function escapeHtml(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/\"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function shortText(value, maxLen) {
    var s = String(value == null ? '' : value);
    var n = maxLen == null ? 10 : Number(maxLen);
    if (!Number.isFinite(n)) n = 10;
    n = Math.max(0, Math.floor(n));
    if (n <= 0) return '';
    return s.length > n ? s.slice(0, n) + '…' : s;
  }

  function isCompactChart(chartId) {
    try {
      var el = document.getElementById(chartId);
      if (el && el.clientWidth && el.clientWidth < 420) return true;
    } catch (err) {}
    try {
      return !!(window.matchMedia && window.matchMedia('(max-width: 520px)').matches);
    } catch (err) {
      return false;
    }
  }

  function fmtDayLabel(v) {
    var s = String(v || '');
    if (/^\d{4}-\d{2}-\d{2}/.test(s)) return s.slice(5, 10);
    return s;
  }

  function parseLooseDate(s) {
    if (!s) return null;
    var str = String(s);
    var iso = str.includes('T') ? str : str.replace(' ', 'T');
    var d = new Date(iso);
    if (Number.isNaN(d.getTime())) return null;
    return d;
  }

  function daysSince(iso) {
    var d = parseLooseDate(iso);
    if (!d) return null;
    var diff = Date.now() - d.getTime();
    if (!Number.isFinite(diff)) return null;
    return Math.max(0, Math.floor(diff / 86400000));
  }

  function calcActiveDays(trend) {
    return (trend || []).filter(function (d) {
      return toNum(d.answered) > 0;
    }).length;
  }

  function calcRecentAnswered(trend, days) {
    var list = Array.isArray(trend) ? trend : [];
    if (!list.length) return 0;
    var slice = list.slice(Math.max(0, list.length - days));
    return slice.reduce(function (sum, item) {
      return sum + toNum(item.answered);
    }, 0);
  }

  function setText(id, value) {
    var el = document.getElementById(id);
    if (el) el.textContent = value == null ? '' : String(value);
  }

  function setBar(id, percent) {
    var el = document.getElementById(id);
    if (!el) return;
    var v = clamp(toNum(percent), 0, 100);
    el.style.width = v.toFixed(1) + '%';
  }

  var api = (function () {
    try {
      if (window.UserBankDataV2 && typeof window.UserBankDataV2 === 'object') return window.UserBankDataV2;
    } catch (err) {}
    return {};
  })();
  try {
    window.UserBankDataV2 = api;
  } catch (err) {}

  var root = null;
  var mode = 'user_bank';
  var bankId = null;
  var subjectName = '';
  var subtab = 'global';
  var windowDays = 30;
  var bankTotal = 0;
  var bankFavorites = 0;
  var bankMistakes = 0;

  var loadedKeyByTab = { global: '', mistakes: '', favorites: '' };
  var pendingCtx = null;
  var inflight = null;
  var themeObserver = null;
  var themeDirty = false;
  var resizeBound = false;

  function resolveRoot() {
    if (root) return root;
    root = document.querySelector('.ubdv2-shell');
    return root;
  }

  function isVisible(el) {
    try {
      return !!(el && el.getClientRects && el.getClientRects().length);
    } catch (err) {
      return false;
    }
  }

  function readContextFromDom() {
    var el = resolveRoot();
    var payload = window.__UBDV2__ || {};
    var modeAttr = null;
    var subj = null;
    try {
      modeAttr = payload.mode || (el ? el.getAttribute('data-ubdv2-mode') || el.getAttribute('data-mode') : null);
      subj = payload.subject_name || payload.subjectName || (el ? el.getAttribute('data-subject-name') : null);
    } catch (err) {
      modeAttr = payload.mode || null;
      subj = payload.subject_name || payload.subjectName || null;
    }
    return {
      mode: modeAttr,
      bank_id: payload.bank_id || (el ? el.getAttribute('data-bank-id') : null),
      subject_name: subj,
      subtab: payload.subtab || (el ? el.getAttribute('data-subtab') : null),
      window_days: payload.window_days || (el ? el.getAttribute('data-days') : null),
      bank_total: payload.bank_total,
      bank_favorites: payload.bank_favorites,
      bank_mistakes: payload.bank_mistakes,
      force: false,
    };
  }

  function normalizeContext(input) {
    input = input || {};

    var rawMode =
      input.mode != null
        ? input.mode
        : input.ubdv2_mode != null
          ? input.ubdv2_mode
          : input.data_mode != null
            ? input.data_mode
            : input.kind;
    var bid = input.bank_id != null ? input.bank_id : input.bankId;
    var subj =
      input.subject_name != null
        ? input.subject_name
        : input.subjectName != null
          ? input.subjectName
          : input.subject != null
            ? input.subject
            : input.subject_name_text;
    var st = input.subtab != null ? input.subtab : input.tab;
    var days = input.window_days != null ? input.window_days : (input.windowDays != null ? input.windowDays : input.days);

    var nextSubjectName = subj != null ? String(subj) : '';
    nextSubjectName = nextSubjectName.trim();

    var nextBankId = bid != null ? String(bid) : '';
    if (!nextBankId) nextBankId = '';

    var nextMode = String(rawMode || '').trim().toLowerCase();
    if (nextMode !== 'subject') nextMode = nextSubjectName ? 'subject' : 'user_bank';
    if (!nextSubjectName) nextMode = 'user_bank';

    var nextTab = String(st || '').trim().toLowerCase();
    if (nextTab !== 'mistakes' && nextTab !== 'favorites') nextTab = 'global';

    var nextDays = toNum(days);
    if (![7, 14, 30, 90].includes(nextDays)) nextDays = nextTab === 'global' ? 90 : 30;

    var ctx = {
      mode: nextMode,
      bank_id: nextBankId,
      subject_name: nextSubjectName,
      subtab: nextTab,
      window_days: nextDays,
      bank_total: input.bank_total != null ? toNum(input.bank_total) : (input.bankTotal != null ? toNum(input.bankTotal) : 0),
      bank_favorites: input.bank_favorites != null ? toNum(input.bank_favorites) : (input.bankFavorites != null ? toNum(input.bankFavorites) : 0),
      bank_mistakes: input.bank_mistakes != null ? toNum(input.bank_mistakes) : (input.bankMistakes != null ? toNum(input.bankMistakes) : 0),
      force: !!input.force,
    };

    return ctx;
  }

  var charts = {};

  function getChart(id) {
    if (!window.echarts) return null;
    var el = document.getElementById(id);
    if (!el) return null;
    if (!charts[id]) charts[id] = echarts.init(el);
    return charts[id];
  }

  function renderEmpty(chart, text) {
    if (!chart) return;
    chart.clear();
    chart.setOption({
      title: {
        text: text || '暂无数据',
        left: 'center',
        top: 'middle',
        textStyle: {
          color: getVar('--app-muted') || '#6b7280',
          fontSize: 12,
          fontWeight: 700,
        },
      },
    });
  }

  async function fetchJson(url) {
    var res = await fetch(url, { credentials: 'same-origin' });
    var js = await res.json().catch(function () {
      return {};
    });
    var ok = res.ok && js && (js.code === 0 || js.status === 'success');
    if (!ok) throw new Error((js && (js.message || js.msg)) || '请求失败');
    return js;
  }

  function renderAdvice(list, wrapId) {
    var wrap = document.getElementById(wrapId);
    if (!wrap) return;
    var items = Array.isArray(list) ? list : [];
    if (!items.length) {
      wrap.innerHTML = '<div class="ubdv2-muted">暂无建议</div>';
      return;
    }
    wrap.innerHTML = items
      .map(function (item) {
        var title = item && item.title ? String(item.title) : '建议';
        var content = item && item.content ? String(item.content) : '';
        return (
          '<div class="ubdv2-advice-item">' +
          '<div class="t">' +
          escapeHtml(title) +
          '</div>' +
          '<div class="c">' +
          escapeHtml(content) +
          '</div>' +
          '</div>'
        );
      })
      .join('');
  }

  // Split namespace for UBD v2
  var ns = window.UserBankDataV2NS || {};
  ns.api = api;
  ns.charts = charts;
  ns.helpers = {
    clamp: clamp,
    getVar: getVar,
    pickColor: pickColor,
    toNum: toNum,
    fmtCount: fmtCount,
    fmtPercent: fmtPercent,
    fmtDay: fmtDay,
    fmtDateTime: fmtDateTime,
    escapeHtml: escapeHtml,
    shortText: shortText,
    isCompactChart: isCompactChart,
    fmtDayLabel: fmtDayLabel,
    parseLooseDate: parseLooseDate,
    daysSince: daysSince,
    calcActiveDays: calcActiveDays,
    calcRecentAnswered: calcRecentAnswered,
    setText: setText,
    setBar: setBar
  };
  ns.resolveRoot = resolveRoot;
  ns.isVisible = isVisible;
  ns.readContextFromDom = readContextFromDom;
  ns.normalizeContext = normalizeContext;
  ns.getChart = getChart;
  ns.renderEmpty = renderEmpty;
  ns.fetchJson = fetchJson;
  ns.renderAdvice = renderAdvice;
  window.UserBankDataV2NS = ns;
})();
